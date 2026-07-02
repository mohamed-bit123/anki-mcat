// Copyright: MCAT Speedrun fork
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Practice-question content + attempt logging, and the gathering layer that
//! turns a real collection into [`crate::speedrun::scores`] inputs.
//!
//! ## Two kinds of content
//! * **Flashcards** — ordinary cards. They feed the **Memory** score.
//! * **Application questions** — notes tagged [`QUESTION_TAG`]. The user
//!   answers them like a mini practice test; each graded answer is logged and
//!   feeds the **Performance** (and therefore **Readiness**) score. Keeping
//!   them tagged keeps the two signals strictly separate, as the honesty rules
//!   require.
//!
//! An attempt is stored compactly inside the question card's `custom_data` JSON
//! under [`ATTEMPTS_KEY`] as `[[day, correct], ...]` (day = days since
//! collection creation), capped at [`MAX_ATTEMPTS_KEPT`]. `custom_data` already
//! syncs, so attempt history rides along to every device for free.

use std::collections::HashMap;

use serde_json::Value;

use crate::prelude::*;
use crate::scheduler::timing::SchedTimingToday;
use crate::search::Node;
use crate::search::SearchNode;
use crate::search::SortMode;
use crate::speedrun::queue::card_retrievability;
use crate::speedrun::queue::question_priority;
use crate::speedrun::queue::smoothed_accuracy;
use crate::speedrun::queue::QuestionPriorityInput;
use crate::speedrun::queue::DEFAULT_TOPIC_POINTS;
use crate::speedrun::queue::TOPIC_POINTS_CONFIG_KEY;
use crate::speedrun::scores::memory_score;
use crate::speedrun::scores::performance_score;
use crate::speedrun::scores::readiness_score;
use crate::speedrun::scores::CalibrationPoint;
use crate::speedrun::scores::CardMemoryInput;
use crate::speedrun::scores::MemoryScore;
use crate::speedrun::scores::PerformanceScore;
use crate::speedrun::scores::QuestionAttempt;
use crate::speedrun::scores::ReadinessScore;
use crate::speedrun::scores::ScoreConfig;

/// Notes carrying this tag are application questions, not flashcards.
pub const QUESTION_TAG: &str = "mcat-question";
/// `custom_data` key holding the compact attempt log.
pub const ATTEMPTS_KEY: &str = "spA";
/// Config key holding `[[projected, actual], ...]` from full-length tests.
pub const CALIBRATION_CONFIG_KEY: &str = "speedrunCalibration";
/// Cap on retained attempts per question (keeps `custom_data` small).
pub const MAX_ATTEMPTS_KEPT: usize = 50;

/// The three scores plus the config they were computed with.
pub struct SpeedrunScores {
    pub memory: MemoryScore,
    pub performance: PerformanceScore,
    pub readiness: ReadinessScore,
}

/// One application question with its computed weakness-weighted priority.
pub struct RankedQuestion {
    pub card_id: CardId,
    pub priority: f32,
    /// The question's topic (deck human name), for "why this surfaced" display.
    pub topic: String,
    pub attempts: u32,
}

impl From<&SpeedrunScores> for anki_proto::scheduler::SpeedrunScoresResponse {
    fn from(s: &SpeedrunScores) -> Self {
        use anki_proto::scheduler::speedrun_scores_response as pb;
        anki_proto::scheduler::SpeedrunScoresResponse {
            memory: Some(pb::Memory {
                known: s.memory.value.is_some(),
                value: s.memory.value.unwrap_or(0.0),
                studied_cards: s.memory.studied_cards as u32,
                total_cards: s.memory.total_cards as u32,
                topic_coverage: s.memory.topic_coverage,
                reason: s.memory.reason_withheld.clone().unwrap_or_default(),
            }),
            performance: Some(pb::Performance {
                known: s.performance.value.is_some(),
                value: s.performance.value.unwrap_or(0.0),
                attempts: s.performance.attempts as u32,
                effective_attempts: s.performance.effective_attempts,
                topics_covered: s.performance.topics_covered as u32,
                reason: s.performance.reason_withheld.clone().unwrap_or_default(),
            }),
            readiness: Some(pb::Readiness {
                known: s.readiness.projected.is_some(),
                projected: s.readiness.projected.unwrap_or(0.0),
                low: s.readiness.low.unwrap_or(0.0),
                high: s.readiness.high.unwrap_or(0.0),
                confidence: format!("{:?}", s.readiness.confidence).to_lowercase(),
                reason: s.readiness.reason_withheld.clone().unwrap_or_default(),
                calibration_note: s.readiness.calibration_note.clone(),
            }),
        }
    }
}

impl Collection {
    /// Records one graded answer to an application question, appending it to
    /// the card's `custom_data` attempt log.
    pub(crate) fn speedrun_record_attempt(&mut self, card_id: CardId, correct: bool) -> Result<()> {
        let today = self.timing_today()?.days_elapsed as i64;
        let mut card = self.storage.get_card(card_id)?.or_not_found(card_id)?;
        let deck_id = card.deck_id;

        let mut data: Value = if card.custom_data.is_empty() {
            Value::Object(Default::default())
        } else {
            serde_json::from_str(&card.custom_data)
                .unwrap_or_else(|_| Value::Object(Default::default()))
        };
        if !data.is_object() {
            data = Value::Object(Default::default());
        }
        let obj = data.as_object_mut().unwrap();
        let entries = obj
            .entry(ATTEMPTS_KEY)
            .or_insert_with(|| Value::Array(vec![]));
        let arr = match entries.as_array_mut() {
            Some(a) => a,
            None => {
                *entries = Value::Array(vec![]);
                entries.as_array_mut().unwrap()
            }
        };
        arr.push(Value::Array(vec![
            Value::from(today),
            Value::from(if correct { 1 } else { 0 }),
        ]));
        if arr.len() > MAX_ATTEMPTS_KEPT {
            let overflow = arr.len() - MAX_ATTEMPTS_KEPT;
            arr.drain(0..overflow);
        }

        card.custom_data = serde_json::to_string(&data)?;
        card.validate_custom_data()?;
        self.update_cards_maybe_undoable(vec![card], true)?;

        // Advance the concept's FSRS memory state (concept-level spacing).
        self.speedrun_update_concept(deck_id, correct, today)?;
        Ok(())
    }

    /// Orders application questions by the points-at-stake weakness weighting
    /// (highest priority first). This is the question analogue of the Phase 1
    /// review queue: flashcards rank on FSRS state, questions rank on applied
    /// accuracy, both scaled by topic points. Topic weakness is smoothed across
    /// all questions in the topic; per-question need favors unseen, recently
    /// missed, and stale questions.
    pub(crate) fn speedrun_next_questions(&mut self) -> Result<Vec<RankedQuestion>> {
        let timing = self.timing_today()?;
        let today = timing.days_elapsed as i64;
        let topic_points_cfg: HashMap<String, f32> =
            self.get_config_default(TOPIC_POINTS_CONFIG_KEY);
        let mut deck_names: HashMap<DeckId, String> = HashMap::new();

        let ids = self.search_cards(SearchNode::from_tag_name(QUESTION_TAG), SortMode::NoOrder)?;

        struct Row {
            card_id: CardId,
            deck_id: DeckId,
            topic_points: f32,
            attempts: Vec<(i64, bool)>,
        }
        let mut rows = Vec::with_capacity(ids.len());
        let mut topic_correct: HashMap<DeckId, f32> = HashMap::new();
        let mut topic_total: HashMap<DeckId, f32> = HashMap::new();
        for id in ids {
            let card = match self.storage.get_card(id)? {
                Some(c) => c,
                None => continue,
            };
            let points =
                self.topic_points_for_deck(card.deck_id, &topic_points_cfg, &mut deck_names)?;
            let attempts = parse_attempts(&card.custom_data);
            for (_, correct) in &attempts {
                *topic_total.entry(card.deck_id).or_default() += 1.0;
                if *correct {
                    *topic_correct.entry(card.deck_id).or_default() += 1.0;
                }
            }
            rows.push(Row {
                card_id: card.id,
                deck_id: card.deck_id,
                topic_points: points,
                attempts,
            });
        }

        let mut ranked: Vec<RankedQuestion> = rows
            .into_iter()
            .map(|r| {
                let correct = topic_correct.get(&r.deck_id).copied().unwrap_or(0.0);
                let total = topic_total.get(&r.deck_id).copied().unwrap_or(0.0);
                let topic_accuracy = smoothed_accuracy(correct, total);
                let n = r.attempts.len() as u32;
                let q_correct = r.attempts.iter().filter(|(_, c)| *c).count() as f32;
                let question_accuracy = if n > 0 { q_correct / n as f32 } else { 0.0 };
                let last_day = r.attempts.iter().map(|(d, _)| *d).max().unwrap_or(today);
                let days_since_last = (today - last_day).max(0) as f32;
                let priority = question_priority(&QuestionPriorityInput {
                    topic_points: r.topic_points,
                    topic_accuracy,
                    attempts: n,
                    question_accuracy,
                    days_since_last,
                });
                RankedQuestion {
                    card_id: r.card_id,
                    priority,
                    topic: deck_names.get(&r.deck_id).cloned().unwrap_or_default(),
                    attempts: n,
                }
            })
            .collect();

        ranked.sort_by(|a, b| {
            b.priority
                .partial_cmp(&a.priority)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.card_id.0.cmp(&b.card_id.0))
        });
        Ok(ranked)
    }

    /// Computes Memory, Performance and Readiness from the current collection.
    pub(crate) fn speedrun_compute_scores(&mut self) -> Result<SpeedrunScores> {
        let cfg = ScoreConfig::default();
        let timing = self.timing_today()?;
        let topic_points: HashMap<String, f32> = self.get_config_default(TOPIC_POINTS_CONFIG_KEY);
        let mut deck_names: HashMap<DeckId, String> = HashMap::new();

        let memory = self.gather_memory(&cfg, &timing, &topic_points, &mut deck_names)?;
        let performance = self.gather_performance(&cfg, &timing, &topic_points, &mut deck_names)?;
        let calibration = self.read_calibration();
        let readiness = readiness_score(&memory, &performance, &calibration, &cfg);

        Ok(SpeedrunScores {
            memory,
            performance,
            readiness,
        })
    }

    fn gather_memory(
        &mut self,
        cfg: &ScoreConfig,
        timing: &SchedTimingToday,
        topic_points: &HashMap<String, f32>,
        deck_names: &mut HashMap<DeckId, String>,
    ) -> Result<MemoryScore> {
        let ids = self.search_cards(
            Node::Not(Box::new(SearchNode::from_tag_name(QUESTION_TAG).into())),
            SortMode::NoOrder,
        )?;
        let mut inputs = Vec::with_capacity(ids.len());
        for id in ids {
            let card = match self.storage.get_card(id)? {
                Some(c) => c,
                None => continue,
            };
            let points = self.topic_points_for_deck(card.deck_id, topic_points, deck_names)?;
            inputs.push(CardMemoryInput {
                retrievability: card_retrievability(&card, timing),
                topic_points: points,
                topic_id: card.deck_id.0 as u32,
                studied: card.reps > 0,
            });
        }
        Ok(memory_score(&inputs, cfg))
    }

    fn gather_performance(
        &mut self,
        cfg: &ScoreConfig,
        timing: &SchedTimingToday,
        topic_points: &HashMap<String, f32>,
        deck_names: &mut HashMap<DeckId, String>,
    ) -> Result<PerformanceScore> {
        let today = timing.days_elapsed as i64;
        let ids = self.search_cards(SearchNode::from_tag_name(QUESTION_TAG), SortMode::NoOrder)?;
        let mut attempts = Vec::new();
        // Every distinct question topic (subdeck) in the bank — including ones
        // not yet attempted — so the give-up rule can require full coverage.
        let mut all_topics: std::collections::HashSet<u32> = std::collections::HashSet::new();
        for id in ids {
            let card = match self.storage.get_card(id)? {
                Some(c) => c,
                None => continue,
            };
            let points = self.topic_points_for_deck(card.deck_id, topic_points, deck_names)?;
            let topic_id = card.deck_id.0 as u32;
            all_topics.insert(topic_id);
            for (day, correct) in parse_attempts(&card.custom_data) {
                attempts.push(QuestionAttempt {
                    correct,
                    topic_id,
                    topic_points: points,
                    difficulty: 0.5,
                    age_days: (today - day).max(0) as f32,
                });
            }
        }
        Ok(performance_score(&attempts, all_topics.len(), cfg))
    }

    fn topic_points_for_deck(
        &mut self,
        deck_id: DeckId,
        topic_points: &HashMap<String, f32>,
        deck_names: &mut HashMap<DeckId, String>,
    ) -> Result<f32> {
        if !deck_names.contains_key(&deck_id) {
            let name = self
                .storage
                .get_deck(deck_id)?
                .map(|d| d.human_name().to_lowercase())
                .unwrap_or_default();
            deck_names.insert(deck_id, name);
        }
        let name = &deck_names[&deck_id];
        Ok(topic_points
            .get(name)
            .copied()
            .unwrap_or(DEFAULT_TOPIC_POINTS))
    }

    fn read_calibration(&self) -> Vec<CalibrationPoint> {
        let raw: Vec<[f32; 2]> = self.get_config_default(CALIBRATION_CONFIG_KEY);
        raw.into_iter()
            .map(|[projected, actual]| CalibrationPoint { projected, actual })
            .collect()
    }
}

pub(crate) fn parse_attempts(custom_data: &str) -> Vec<(i64, bool)> {
    if custom_data.is_empty() {
        return vec![];
    }
    let value: Value = match serde_json::from_str(custom_data) {
        Ok(v) => v,
        Err(_) => return vec![],
    };
    let arr = match value.get(ATTEMPTS_KEY).and_then(|v| v.as_array()) {
        Some(a) => a,
        None => return vec![],
    };
    arr.iter()
        .filter_map(|entry| {
            let pair = entry.as_array()?;
            let day = pair.first()?.as_i64()?;
            let correct = pair.get(1)?.as_i64()? != 0;
            Some((day, correct))
        })
        .collect()
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::card::CardType;

    fn add_flashcard(col: &mut Collection, deck: DeckId, reps: u32) -> CardId {
        let nt = col.get_notetype_by_name("Basic").unwrap().unwrap();
        let mut note = nt.new_note();
        note.set_field(0, "front").unwrap();
        col.add_note(&mut note, deck).unwrap();
        let mut card = col
            .storage
            .get_card_by_ordinal(note.id, 0)
            .unwrap()
            .unwrap();
        card.reps = reps;
        card.interval = 10;
        card.ctype = CardType::Review;
        let id = card.id;
        col.update_cards_maybe_undoable(vec![card], false).unwrap();
        id
    }

    fn add_question(col: &mut Collection, deck: DeckId) -> CardId {
        let nt = col.get_notetype_by_name("Basic").unwrap().unwrap();
        let mut note = nt.new_note();
        note.set_field(0, "stem").unwrap();
        note.tags.push(QUESTION_TAG.to_string());
        col.add_note(&mut note, deck).unwrap();
        col.storage
            .get_card_by_ordinal(note.id, 0)
            .unwrap()
            .unwrap()
            .id
    }

    #[test]
    fn attempts_round_trip_through_custom_data() {
        let mut col = Collection::new();
        let q = add_question(&mut col, DeckId(1));
        col.speedrun_record_attempt(q, true).unwrap();
        col.speedrun_record_attempt(q, false).unwrap();
        let card = col.storage.get_card(q).unwrap().unwrap();
        let attempts = parse_attempts(&card.custom_data);
        assert_eq!(attempts.len(), 2);
        assert!(attempts[0].1); // first correct
        assert!(!attempts[1].1); // second incorrect
    }

    #[test]
    fn questions_feed_performance_flashcards_feed_memory() {
        let mut col = Collection::new();
        // 25 studied flashcards -> Memory known.
        for _ in 0..25 {
            add_flashcard(&mut col, DeckId(1), 3);
        }
        // 12 questions across 3 topics (4 each), all correct -> Performance
        // known (satisfies the per-topic depth gate).
        for name in ["T1", "T2", "T3"] {
            let did = col.get_or_create_normal_deck(name).unwrap().id;
            for _ in 0..4 {
                let q = add_question(&mut col, did);
                col.speedrun_record_attempt(q, true).unwrap();
            }
        }
        let scores = col.speedrun_compute_scores().unwrap();
        assert!(scores.memory.value.is_some(), "memory should be known");
        assert!(
            scores.performance.value.is_some(),
            "performance should be known"
        );
        // Questions are excluded from Memory's studied set.
        assert_eq!(scores.memory.studied_cards, 25);
        assert_eq!(scores.performance.attempts, 12);
        // With applied evidence, readiness now projects.
        assert!(scores.readiness.projected.is_some());
    }

    #[test]
    fn next_questions_ranks_weak_and_unseen_first() {
        let mut col = Collection::new();
        let weak = col.get_or_create_normal_deck("Weak").unwrap().id;
        let strong = col.get_or_create_normal_deck("Strong").unwrap().id;

        // Strong topic: a question answered correctly several times.
        let strong_known = add_question(&mut col, strong);
        for _ in 0..3 {
            col.speedrun_record_attempt(strong_known, true).unwrap();
        }
        // Weak topic: a question answered wrong, plus an unseen one.
        let weak_missed = add_question(&mut col, weak);
        for _ in 0..3 {
            col.speedrun_record_attempt(weak_missed, false).unwrap();
        }
        let weak_unseen = add_question(&mut col, weak);

        let ranked = col.speedrun_next_questions().unwrap();
        let order: Vec<CardId> = ranked.iter().map(|r| r.card_id).collect();
        // The mastered strong-topic question must rank last.
        assert_eq!(*order.last().unwrap(), strong_known);
        // Both weak-topic questions outrank the mastered one.
        let pos = |c: CardId| order.iter().position(|&x| x == c).unwrap();
        assert!(pos(weak_missed) < pos(strong_known));
        assert!(pos(weak_unseen) < pos(strong_known));
    }

    #[test]
    fn readiness_refused_with_only_flashcards() {
        let mut col = Collection::new();
        for _ in 0..30 {
            add_flashcard(&mut col, DeckId(1), 3);
        }
        let scores = col.speedrun_compute_scores().unwrap();
        assert!(scores.memory.value.is_some());
        assert!(scores.performance.value.is_none());
        assert!(
            scores.readiness.projected.is_none(),
            "no applied questions -> no readiness"
        );
    }
}
