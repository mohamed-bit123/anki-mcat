// Copyright: MCAT Speedrun fork
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Concept-level FSRS scheduling for application questions.
//!
//! Flashcards get spaced repetition for free (each card carries its own FSRS
//! memory state). Application questions can't be scheduled the same way: once
//! you've seen a specific MCAT question and its explanation, re-testing that
//! *exact* item measures memory of the item, not your ability to apply the
//! concept to a novel question — which is what the MCAT actually tests.
//!
//! So we run FSRS one level up, at the **concept** (subject/topic) rather than
//! the item. Each concept carries an FSRS [`MemoryState`]; answering any
//! question in that concept updates it (correct → `good`, incorrect → `again`).
//! Scheduling then asks *which concept is most due right now* (lowest FSRS
//! retrievability, weighted by MCAT yield) and serves one question from it,
//! preferring the least-recently-seen item so you don't re-drill the same
//! wording. When AI generation lands, "this concept is due" will instead pull a
//! freshly generated question — same scheduler, novel item, honest measurement.
//!
//! Because answering a concept immediately raises its retrievability, the next
//! call almost always picks a different concept: interleaving falls out of the
//! FSRS dynamics for free.

use std::collections::HashMap;

use fsrs::MemoryState;
use fsrs::FSRS;
use fsrs::FSRS5_DEFAULT_DECAY;
use serde::Deserialize;
use serde::Serialize;

use crate::prelude::*;
use crate::search::SearchNode;
use crate::search::SortMode;
use crate::speedrun::content::parse_attempts;
use crate::speedrun::content::RankedQuestion;
use crate::speedrun::content::QUESTION_TAG;

/// Collection-config key holding the per-concept FSRS state map
/// (`{concept_key: ConceptState}`), keyed by the lowercased subject/leaf name.
pub const CONCEPTS_CONFIG_KEY: &str = "speedrunConcepts";
/// FSRS desired retention used to schedule concept reviews.
pub const DESIRED_RETENTION: f32 = 0.9;
/// A gentle daily floor: below this you're unlikely to make steady progress.
pub const RECOMMENDED_DAILY_MIN: u32 = 20;
/// A soft daily ceiling: past this, added questions show diminishing returns and
/// risk crowding out spaced review of other material.
pub const RECOMMENDED_DAILY_MAX: u32 = 60;

/// Per-concept FSRS memory state plus light bookkeeping. Stored in config so it
/// syncs across devices for free.
#[derive(Serialize, Deserialize, Clone, Debug, Default)]
pub struct ConceptState {
    pub stability: f32,
    pub difficulty: f32,
    /// Days-since-collection-creation of the last answered question.
    pub last_day: i64,
    /// Scheduled next-review day (days since creation).
    pub due_day: i64,
    pub reps: u32,
    pub lapses: u32,
    /// False until the first answer, so unseen concepts schedule as fully due.
    pub seen: bool,
}

/// Relative MCAT yield per subject, keyed by lowercased leaf name. Used as the
/// concept scheduler's "points at stake" multiplier so high-yield subjects win
/// ties. Missing subjects default to 1.0.
fn builtin_subject_points(leaf_lower: &str) -> f32 {
    match leaf_lower {
        "biochemistry" => 5.0,
        "biology" => 4.0,
        "psychology" => 4.0,
        "general chemistry" => 3.0,
        "physics" => 3.0,
        "sociology" => 3.0,
        "organic chemistry" => 2.0,
        _ => 1.0,
    }
}

/// The single next question plus daily pacing info for an open-ended session.
pub struct NextQuestion {
    pub question: Option<RankedQuestion>,
    pub concept_retrievability: f32,
    pub answered_today: u32,
    pub recommended_min: u32,
    pub recommended_max: u32,
}

/// The leaf of a deck's human name, e.g. `MCAT Practice::Biology` → `Biology`.
fn deck_leaf(human_name: &str) -> &str {
    human_name.rsplit("::").next().unwrap_or(human_name).trim()
}

impl Collection {
    /// Updates the FSRS memory state for the concept a question belongs to, from
    /// one graded answer. Called by [`Collection::speedrun_record_attempt`].
    pub(crate) fn speedrun_update_concept(
        &mut self,
        deck_id: DeckId,
        correct: bool,
        today: i64,
    ) -> Result<()> {
        let (key, _display) = self.concept_for_deck(deck_id)?;
        let mut map: HashMap<String, ConceptState> = self.get_config_default(CONCEPTS_CONFIG_KEY);
        // `Some(&[])` selects the FSRS default parameters (None disables the
        // scheduler and makes next_states error).
        let fsrs = FSRS::new(Some(&[]))?;

        let previous = map.get(&key).cloned().unwrap_or_default();
        let (current, elapsed_days) = if previous.seen {
            (
                Some(MemoryState {
                    stability: previous.stability,
                    difficulty: previous.difficulty,
                }),
                (today - previous.last_day).max(0) as u32,
            )
        } else {
            (None, 0)
        };

        let next = fsrs.next_states(current, DESIRED_RETENTION, elapsed_days)?;
        let chosen = if correct { next.good } else { next.again };
        let interval_days = chosen.interval.round().max(1.0) as i64;

        let mut state = previous;
        state.stability = chosen.memory.stability;
        state.difficulty = chosen.memory.difficulty;
        state.last_day = today;
        state.due_day = today + interval_days;
        state.reps += 1;
        if !correct {
            state.lapses += 1;
        }
        state.seen = true;
        map.insert(key, state);
        self.set_config(CONCEPTS_CONFIG_KEY, &map)?;
        Ok(())
    }

    /// Chooses the next single application question by concept-level FSRS
    /// scheduling: the most-due concept (lowest retrievability × MCAT yield),
    /// then the least-recently-seen question within it. Also reports today's
    /// answered count and the recommended daily band for pacing.
    pub(crate) fn speedrun_next_question(&mut self) -> Result<NextQuestion> {
        let timing = self.timing_today()?;
        let today = timing.days_elapsed as i64;
        let fsrs = FSRS::new(Some(&[]))?;
        let concept_map: HashMap<String, ConceptState> =
            self.get_config_default(CONCEPTS_CONFIG_KEY);

        let ids = self.search_cards(SearchNode::from_tag_name(QUESTION_TAG), SortMode::NoOrder)?;

        // One candidate question per card, grouped under its concept.
        struct Cand {
            card_id: CardId,
            last_day: Option<i64>,
            attempts: u32,
        }
        struct Group {
            display: String,
            points: f32,
            retrievability: f32,
            /// Attempts in this concept *today*, for within-day rotation.
            times_today: u32,
            cands: Vec<Cand>,
        }
        let mut groups: HashMap<String, Group> = HashMap::new();
        let mut deck_cache: HashMap<DeckId, (String, String)> = HashMap::new();
        let mut answered_today = 0u32;

        for id in ids {
            let card = match self.storage.get_card(id)? {
                Some(c) => c,
                None => continue,
            };
            let (key, display) = match deck_cache.get(&card.deck_id) {
                Some(v) => v.clone(),
                None => {
                    let v = self.concept_for_deck(card.deck_id)?;
                    deck_cache.insert(card.deck_id, v.clone());
                    v
                }
            };
            let attempts = parse_attempts(&card.custom_data);
            let today_count = attempts.iter().filter(|(d, _)| *d == today).count() as u32;
            answered_today += today_count;
            let last_day = attempts.iter().map(|(d, _)| *d).max();

            let group = groups.entry(key.clone()).or_insert_with(|| {
                let state = concept_map.get(&key);
                let retrievability = match state {
                    Some(s) if s.seen => {
                        let elapsed_days = (today - s.last_day).max(0) as u32;
                        let elapsed_seconds = elapsed_days.saturating_mul(86_400);
                        fsrs.current_retrievability_seconds(
                            MemoryState {
                                stability: s.stability,
                                difficulty: s.difficulty,
                            },
                            elapsed_seconds,
                            FSRS5_DEFAULT_DECAY,
                        )
                    }
                    // Never studied → fully due, so new concepts get introduced.
                    _ => 0.0,
                };
                Group {
                    display,
                    points: builtin_subject_points(&key),
                    retrievability,
                    times_today: 0,
                    cands: Vec::new(),
                }
            });
            group.times_today += today_count;
            group.cands.push(Cand {
                card_id: card.id,
                last_day,
                attempts: attempts.len() as u32,
            });
        }

        // Priority blends three things so the schedule is right both across days
        // and within a single session:
        //   * urgency = 1 - R  → concepts genuinely due (from prior days, low R)
        //     dominate; this is the real FSRS spacing signal.
        //   * a small urgency floor so that when *everything* was just reviewed
        //     today (all R≈1, no spacing signal left) there's still a positive
        //     base to differentiate on.
        //   * / (1 + times_today) → each rep of a concept today lowers its next
        //     priority, so a session rotates across concepts (interleaving) and
        //     yields roughly yield-proportional coverage instead of hammering the
        //     single highest-yield subject.
        const URGENCY_FLOOR: f32 = 0.05;
        let best = groups
            .into_values()
            .map(|mut g| {
                let urgency = (1.0 - g.retrievability).clamp(0.0, 1.0).max(URGENCY_FLOOR);
                let priority = g.points.max(0.0) * urgency / (1.0 + g.times_today as f32);
                // Within the concept, least-recently-seen first (unseen before
                // any attempted), then fewest attempts, then stable by id.
                g.cands.sort_by(|a, b| {
                    let a_key = (a.last_day.is_some(), a.last_day.unwrap_or(i64::MIN), a.attempts, a.card_id.0);
                    let b_key = (b.last_day.is_some(), b.last_day.unwrap_or(i64::MIN), b.attempts, b.card_id.0);
                    a_key.cmp(&b_key)
                });
                (priority, g)
            })
            .max_by(|(pa, ga), (pb, gb)| {
                pa.partial_cmp(pb)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    // Deterministic tie-break: higher yield, then name.
                    .then(ga.points.partial_cmp(&gb.points).unwrap_or(std::cmp::Ordering::Equal))
                    .then(gb.display.cmp(&ga.display))
            });

        let (question, concept_retrievability) = match best {
            Some((priority, group)) => {
                let retr = group.retrievability;
                let question = group.cands.into_iter().next().map(|c| RankedQuestion {
                    card_id: c.card_id,
                    priority,
                    topic: group.display.clone(),
                    attempts: c.attempts,
                });
                (question, retr)
            }
            None => (None, 0.0),
        };

        Ok(NextQuestion {
            question,
            concept_retrievability,
            answered_today,
            recommended_min: RECOMMENDED_DAILY_MIN,
            recommended_max: RECOMMENDED_DAILY_MAX,
        })
    }

    /// `(lowercased key, display leaf)` for a deck, e.g.
    /// `MCAT Practice::Biology` → `("biology", "Biology")`.
    fn concept_for_deck(&mut self, deck_id: DeckId) -> Result<(String, String)> {
        let name = self
            .storage
            .get_deck(deck_id)?
            .map(|d| d.human_name())
            .unwrap_or_default();
        let leaf = deck_leaf(&name).to_string();
        Ok((leaf.to_lowercase(), leaf))
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::card::CardType;

    fn add_question(col: &mut Collection, deck: &str) -> CardId {
        let did = col.get_or_create_normal_deck(deck).unwrap().id;
        let nt = col.get_notetype_by_name("Basic").unwrap().unwrap();
        let mut note = nt.new_note();
        note.set_field(0, "stem").unwrap();
        note.tags.push(QUESTION_TAG.to_string());
        col.add_note(&mut note, did).unwrap();
        let mut card = col.storage.get_card_by_ordinal(note.id, 0).unwrap().unwrap();
        card.ctype = CardType::New;
        let id = card.id;
        col.update_cards_maybe_undoable(vec![card], false).unwrap();
        id
    }

    #[test]
    fn deck_leaf_takes_the_last_segment() {
        assert_eq!(deck_leaf("MCAT Practice::Biology"), "Biology");
        assert_eq!(deck_leaf("Biology"), "Biology");
    }

    #[test]
    fn answering_raises_concept_retrievability_and_interleaves() {
        let mut col = Collection::new();
        // Two concepts, one question each.
        let bio = add_question(&mut col, "MCAT Practice::Biology");
        let _phys = add_question(&mut col, "MCAT Practice::Physics");

        // First pick is the highest-yield unseen concept (Biology > Physics).
        let first = col.speedrun_next_question().unwrap();
        let q1 = first.question.unwrap();
        assert_eq!(q1.card_id, bio);
        assert_eq!(first.answered_today, 0);
        assert_eq!(first.recommended_min, RECOMMENDED_DAILY_MIN);

        // Answer the Biology question correctly; its concept is no longer due.
        col.speedrun_record_attempt(bio, true).unwrap();

        // Next pick must now be the *other* concept (interleaving falls out of
        // the FSRS dynamics — Biology's retrievability just jumped).
        let second = col.speedrun_next_question().unwrap();
        let q2 = second.question.unwrap();
        assert_ne!(q2.topic, "Biology", "should interleave to a different concept");
        assert_eq!(second.answered_today, 1);
    }

    #[test]
    fn within_day_practice_rotates_across_concepts() {
        // Once every concept has been answered today (FSRS says nothing is due
        // again today), continued practice must still spread across concepts
        // instead of hammering the highest-yield one.
        let mut col = Collection::new();
        for subject in ["Biochemistry", "Biology", "Physics"] {
            for _ in 0..3 {
                add_question(&mut col, &format!("MCAT Practice::{subject}"));
            }
        }
        // Answer 12 questions in a row, always correct.
        let mut served = Vec::new();
        for _ in 0..12 {
            let q = col.speedrun_next_question().unwrap().question.unwrap();
            served.push(q.topic.clone());
            col.speedrun_record_attempt(q.card_id, true).unwrap();
        }
        // All three concepts must appear, and no single concept may dominate the
        // whole session.
        let distinct: std::collections::HashSet<_> = served.iter().collect();
        assert_eq!(distinct.len(), 3, "all concepts should be practiced: {served:?}");
        for subject in ["Biochemistry", "Biology", "Physics"] {
            let n = served.iter().filter(|t| *t == subject).count();
            assert!(n <= 6, "{subject} dominated the session ({n}/12): {served:?}");
        }
    }

    #[test]
    fn concept_state_persists_and_counts_daily() {
        let mut col = Collection::new();
        let q = add_question(&mut col, "MCAT Practice::Chemistry");
        col.speedrun_record_attempt(q, true).unwrap();

        let map: HashMap<String, ConceptState> = col.get_config_default(CONCEPTS_CONFIG_KEY);
        let state = map.get("chemistry").expect("concept state stored");
        assert!(state.seen);
        assert_eq!(state.reps, 1);
        assert!(state.stability > 0.0);
        assert!(state.due_day > state.last_day, "should schedule into the future");

        let next = col.speedrun_next_question().unwrap();
        assert_eq!(next.answered_today, 1);
    }
}
