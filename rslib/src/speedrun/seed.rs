// Copyright: MCAT Speedrun fork
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Built-in MCAT content (flashcards + application questions), seeded straight
//! into the collection by the shared engine so desktop and mobile ship the
//! *same* deck from one source of truth.
//!
//! Content is authored in two bundled tab-separated files compiled into the
//! binary via [`include_str!`], so scaling the bank up is just adding lines (no
//! Rust edits, no per-platform duplication):
//! * `mcat_flashcards.tsv` — `topic <TAB> front <TAB> back`
//! * `mcat_questions.tsv`   — `topic <TAB> stem <TAB> A <TAB> B <TAB> C <TAB> D
//!   <TAB> answer-letter <TAB> explanation`
//!
//! Flashcards land in per-topic subdecks under [`MCAT_DECK`] (e.g.
//! `MCAT::Biochemistry`) and feed the **Memory** score. Questions land under
//! [`PRACTICE_DECK`] (e.g. `MCAT Practice::Biochemistry`), tagged
//! [`QUESTION_TAG`], and feed **Performance**/**Readiness**. The engine treats a
//! card's deck as its topic, so this layout lets
//! [`crate::speedrun::queue::points_at_stake`] weight high-yield topics and lets
//! [`crate::speedrun::queue::interleave_order`] mix subjects.
//!
//! Seeding is idempotent per content type (it no-ops if the matching tag already
//! has cards), so callers can safely wire it to a "Set up MCAT" button.

use std::collections::HashMap;
use std::sync::Arc;

use anki_proto::deck_config::deck_config::config::NewCardGatherPriority;

use crate::deckconfig::DeckConfig;
use crate::deckconfig::ReviewCardOrder;
use crate::notetype::Notetype;
use crate::prelude::*;
use crate::search::SearchNode;
use crate::search::SortMode;
use crate::speedrun::queue::TOPIC_POINTS_CONFIG_KEY;

/// Marks every built-in flashcard so seeding stays idempotent and Memory
/// gathering (which is "everything that is not a question") still counts them.
pub const FLASHCARD_TAG: &str = "mcat-flashcard";
/// Marks application questions so they stay separate from flashcards.
pub const QUESTION_TAG: &str = "mcat-question";
/// Root deck for the built-in flashcards. Study this deck to interleave topics.
pub const MCAT_DECK: &str = "MCAT";
/// Root deck for the application questions.
pub const PRACTICE_DECK: &str = "MCAT Practice";
/// Notetype used for application questions (fields: Topic, Stem, A–D, Answer,
/// Explanation). Kept identical to what the desktop/mobile runners read.
pub const QUESTION_NOTETYPE: &str = "MCAT Practice Question";

const FLASHCARDS_TSV: &str = include_str!("mcat_flashcards.tsv");
const QUESTIONS_TSV: &str = include_str!("mcat_questions.tsv");

/// Split a bundled TSV into rows, skipping blank lines and `#` comments and
/// requiring at least `min_cols` columns per row.
fn parse_rows(tsv: &str, min_cols: usize) -> Vec<Vec<&str>> {
    tsv.lines()
        .map(|line| line.trim_end_matches('\r'))
        .filter(|line| !line.trim().is_empty() && !line.trim_start().starts_with('#'))
        .map(|line| line.split('\t').collect::<Vec<_>>())
        .filter(|cols| cols.len() >= min_cols)
        .collect()
}

/// Relative MCAT yield per subject, used to seed `speedrunTopicPoints` so the
/// points-at-stake order surfaces high-yield subjects first. Keys are the
/// lowercased deck human names the engine derives at review time.
fn builtin_topic_points() -> HashMap<String, f32> {
    [
        ("mcat::biochemistry", 5.0),
        ("mcat::biology", 4.0),
        ("mcat::psychology", 4.0),
        ("mcat::general chemistry", 3.0),
        ("mcat::physics", 3.0),
        ("mcat::sociology", 3.0),
        ("mcat::organic chemistry", 2.0),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_string(), v))
    .collect()
}

impl Collection {
    /// Seeds the built-in MCAT flashcards *and* application questions (each
    /// idempotent), configures the [`MCAT_DECK`] for interleaved study, and
    /// seeds high-yield topic points. Returns total cards + questions added.
    pub fn speedrun_seed_builtin(&mut self) -> Result<usize> {
        let cards = self.speedrun_seed_flashcards()?;
        let questions = self.speedrun_seed_questions()?;
        Ok(cards + questions)
    }

    fn speedrun_seed_flashcards(&mut self) -> Result<usize> {
        let already =
            self.search_cards(SearchNode::from_tag_name(FLASHCARD_TAG), SortMode::NoOrder)?;
        if !already.is_empty() {
            return Ok(0);
        }

        let notetype = self
            .get_notetype_by_name("Basic")?
            .or_invalid("Basic notetype not found; cannot seed MCAT flashcards")?;

        let mut added = 0usize;
        for row in parse_rows(FLASHCARDS_TSV, 3) {
            let (topic, front, back) = (row[0], row[1], row[2]);
            let deck = self.get_or_create_normal_deck(&format!("{MCAT_DECK}::{topic}"))?;
            let mut note = notetype.new_note();
            note.set_field(0, front)?;
            note.set_field(1, back)?;
            note.tags.push(FLASHCARD_TAG.to_string());
            self.add_note(&mut note, deck.id)?;
            added += 1;
        }

        // Study the MCAT root with interleaved, weakness-weighted ordering.
        // Reviews use the points-at-stake interleave; new cards have no memory
        // signal yet, so we simply mix them across topics (RANDOM_CARDS) instead
        // of blocking one subject at a time, so even the first pass interleaves.
        let mut root = self.get_or_create_normal_deck(MCAT_DECK)?;
        let mut conf = DeckConfig {
            name: "MCAT".to_string(),
            ..Default::default()
        };
        conf.inner.review_order = ReviewCardOrder::SpeedrunPointsAtStake as i32;
        conf.inner.new_card_gather_priority = NewCardGatherPriority::RandomCards as i32;
        self.add_or_update_deck_config(&mut conf)?;
        root.normal_mut()?.config_id = conf.id.0;
        self.add_or_update_deck(&mut root)?;

        // Merge in high-yield topic points without clobbering any user choices.
        let mut points: HashMap<String, f32> = self.get_config_default(TOPIC_POINTS_CONFIG_KEY);
        for (key, value) in builtin_topic_points() {
            points.entry(key).or_insert(value);
        }
        self.set_config(TOPIC_POINTS_CONFIG_KEY, &points)?;

        Ok(added)
    }

    fn speedrun_seed_questions(&mut self) -> Result<usize> {
        let already =
            self.search_cards(SearchNode::from_tag_name(QUESTION_TAG), SortMode::NoOrder)?;
        if !already.is_empty() {
            return Ok(0);
        }

        let notetype = self.speedrun_question_notetype()?;
        let mut added = 0usize;
        // Column order matches the notetype fields: Topic, Stem, A, B, C, D,
        // Answer, Explanation.
        for row in parse_rows(QUESTIONS_TSV, 8) {
            let deck = self.get_or_create_normal_deck(&format!("{PRACTICE_DECK}::{}", row[0]))?;
            let mut note = notetype.new_note();
            for (idx, value) in row.iter().take(8).enumerate() {
                note.set_field(idx, *value)?;
            }
            note.tags.push(QUESTION_TAG.to_string());
            self.add_note(&mut note, deck.id)?;
            added += 1;
        }
        Ok(added)
    }

    /// Returns the MCAT question notetype, creating it if missing. Fields and
    /// templates match the desktop/mobile question runners.
    fn speedrun_question_notetype(&mut self) -> Result<Arc<Notetype>> {
        if let Some(nt) = self.get_notetype_by_name(QUESTION_NOTETYPE)? {
            return Ok(nt);
        }
        let mut nt = Notetype {
            name: QUESTION_NOTETYPE.to_string(),
            config: Notetype::new_config(),
            ..Default::default()
        };
        for field in ["Topic", "Stem", "A", "B", "C", "D", "Answer", "Explanation"] {
            nt.add_field(field);
        }
        nt.add_template("Card 1", "{{Stem}}", "{{Answer}}. {{Explanation}}");
        self.add_notetype(&mut nt, false)?;
        self.get_notetype_by_name(QUESTION_NOTETYPE)?
            .or_invalid("failed to create MCAT question notetype")
    }
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn seeding_is_idempotent_and_covers_content() -> Result<()> {
        let mut col = Collection::new();
        let flashcards = parse_rows(FLASHCARDS_TSV, 3).len();
        let questions = parse_rows(QUESTIONS_TSV, 8).len();
        assert!(flashcards > 100, "expected a large flashcard bank");
        assert!(questions > 50, "expected a large question bank");

        let first = col.speedrun_seed_builtin()?;
        assert_eq!(first, flashcards + questions);
        // Second run is a no-op (no duplicate cards).
        assert_eq!(col.speedrun_seed_builtin()?, 0);

        let tagged_cards =
            col.search_cards(SearchNode::from_tag_name(FLASHCARD_TAG), SortMode::NoOrder)?;
        assert_eq!(tagged_cards.len(), flashcards);
        let tagged_qs =
            col.search_cards(SearchNode::from_tag_name(QUESTION_TAG), SortMode::NoOrder)?;
        assert_eq!(tagged_qs.len(), questions);

        // Every subject that appears in the flashcard TSV produced a subdeck.
        for row in parse_rows(FLASHCARDS_TSV, 3) {
            let name = format!("{MCAT_DECK}::{}", row[0]);
            assert!(col.get_deck_id(&name)?.is_some(), "missing subdeck {name}");
        }
        Ok(())
    }
}
