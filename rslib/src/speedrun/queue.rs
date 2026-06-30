// Copyright: MCAT Speedrun fork
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Weakness-weighted "points at stake" review ordering.
//!
//! Anki normally orders due reviews by a single dimension (due date, interval,
//! retrievability, ...). For an exam like the MCAT we care about *which reviews
//! best defend the projected score right now*. We combine three signals into a
//! single priority:
//!
//! * **urgency** = `1 - retrievability` — how likely you are to fail the card
//!   *now*. A card you'll almost surely recall (R≈1) is barely worth a slot.
//! * **weakness** = `1 + difficulty` — cards you find hard (high FSRS difficulty
//!   or many lapses) are shakier knowledge and worth shoring up.
//! * **points at stake** = `topic_points` — how many MCAT points ride on the
//!   card's topic (high-yield topics score higher). Defaults to 1.0 when no
//!   topic weighting is configured, so the ordering still works on any deck.
//!
//! `priority = points_at_stake * urgency * weakness`; reviews are then sorted
//! highest-priority first. The function is intentionally pure so it can be unit
//! tested without a collection, and so the readiness model (a later phase) can
//! reuse the exact same number it shows the user as "evidence".

use crate::card::Card;
use crate::scheduler::timing::SchedTimingToday;

/// Per-deck-name MCAT points map, stored as collection config under this key.
/// e.g. `{"biochemistry": 3.0, "psychology": 1.5}`. Missing decks default to
/// [`DEFAULT_TOPIC_POINTS`].
pub const TOPIC_POINTS_CONFIG_KEY: &str = "speedrunTopicPoints";

/// Points assigned to a card whose topic has no explicit weighting.
pub const DEFAULT_TOPIC_POINTS: f32 = 1.0;

/// The three normalized signals that feed the points-at-stake priority.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ReviewPriorityInput {
    /// Probability of recalling the card right now, in `0.0..=1.0`.
    pub retrievability: f32,
    /// Normalized item difficulty / weakness, in `0.0..=1.0` (higher = weaker).
    pub difficulty: f32,
    /// MCAT points riding on this card's topic (>= 0.0).
    pub topic_points: f32,
}

/// Core ranking function. Higher output = study sooner. Pure and deterministic.
pub fn points_at_stake(input: &ReviewPriorityInput) -> f32 {
    let urgency = (1.0 - input.retrievability).clamp(0.0, 1.0);
    let weakness = 1.0 + input.difficulty.clamp(0.0, 1.0);
    input.topic_points.max(0.0) * urgency * weakness
}

/// Builds the priority input for a concrete card.
///
/// Uses the real FSRS retrievability/difficulty when memory state is available,
/// and falls back to interval/overdueness and lapse-count proxies otherwise, so
/// the ordering is meaningful with FSRS on *or* off.
pub(crate) fn review_priority_input_for_card(
    card: &Card,
    timing: &SchedTimingToday,
    topic_points: f32,
) -> ReviewPriorityInput {
    ReviewPriorityInput {
        retrievability: card_retrievability(card, timing),
        difficulty: card_difficulty(card),
        topic_points,
    }
}

pub(crate) fn card_retrievability(card: &Card, timing: &SchedTimingToday) -> f32 {
    if let Some(state) = card.memory_state {
        // Real FSRS forgetting curve.
        let elapsed_seconds = card.seconds_since_last_review(timing).unwrap_or_default();
        let fsrs = fsrs::FSRS::new(None).expect("default FSRS");
        fsrs.current_retrievability_seconds(
            state.into(),
            elapsed_seconds,
            card.decay.unwrap_or(fsrs::FSRS5_DEFAULT_DECAY),
        )
    } else {
        // SM-2 / no memory-state proxy: the more overdue relative to the
        // interval, the lower the estimated retrievability.
        let overdue_days = (timing.days_elapsed as i32 - card.due).max(0) as f32;
        let interval = card.interval.max(1) as f32;
        (1.0 / (1.0 + overdue_days / interval)).clamp(0.0, 1.0)
    }
}

fn card_difficulty(card: &Card) -> f32 {
    if let Some(state) = card.memory_state {
        // FSRS difficulty is 1.0-10.0; FsrsMemoryState::difficulty() normalizes.
        state.difficulty()
    } else {
        // Proxy: cards lapsed more often are weaker. Saturates at 8 lapses.
        (card.lapses as f32 / 8.0).clamp(0.0, 1.0)
    }
}

// --- Application-question ordering (the question analogue of points_at_stake) --
//
// Flashcards have FSRS memory state, so their queue uses retrievability +
// difficulty. Application questions are usually New cards with no FSRS state;
// what we *do* have is graded attempt history. So we rank them on the same
// philosophy ("spend the next slot where the most points ride and you're
// weakest") but read weakness from applied accuracy instead of FSRS.

/// Bayesian prior for smoothing per-topic applied accuracy: pretend we've seen
/// [`TOPIC_ACC_PRIOR_STRENGTH`] attempts at [`TOPIC_ACC_PRIOR_MEAN`] accuracy, so
/// a single lucky/unlucky answer can't declare a topic mastered or hopeless.
pub const TOPIC_ACC_PRIOR_MEAN: f32 = 0.6;
pub const TOPIC_ACC_PRIOR_STRENGTH: f32 = 4.0;

/// Days since last attempt at which spacing pressure on a question saturates.
pub const QUESTION_SPACING_DAYS: f32 = 14.0;

/// Smoothed accuracy in `0.0..=1.0` from raw correct/total counts.
pub fn smoothed_accuracy(correct: f32, total: f32) -> f32 {
    ((correct + TOPIC_ACC_PRIOR_MEAN * TOPIC_ACC_PRIOR_STRENGTH)
        / (total + TOPIC_ACC_PRIOR_STRENGTH))
        .clamp(0.0, 1.0)
}

/// Signals for ranking one application question (analogue of
/// [`ReviewPriorityInput`]).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct QuestionPriorityInput {
    /// MCAT points riding on this question's topic (>= 0.0).
    pub topic_points: f32,
    /// Smoothed *applied* accuracy for the whole topic, in `0.0..=1.0`.
    pub topic_accuracy: f32,
    /// Times this specific question has been attempted.
    pub attempts: u32,
    /// This question's own accuracy in `0.0..=1.0` (ignored when unseen).
    pub question_accuracy: f32,
    /// Days since this question was last attempted (ignored when unseen).
    pub days_since_last: f32,
}

/// Weakness-weighted priority for one application question. Higher = ask sooner.
///
/// `priority = topic_points * topic_weakness * need`, where
/// `topic_weakness = 1 - topic_accuracy` (floored at 0.1 so mastered topics still
/// get occasional coverage), and `need` is 1.0 for an unseen question, otherwise
/// blends how often you miss it (retrieval weakness) with how long it's been
/// (spacing).
pub fn question_priority(input: &QuestionPriorityInput) -> f32 {
    let topic_weakness = (1.0 - input.topic_accuracy.clamp(0.0, 1.0)).max(0.1);
    let need = if input.attempts == 0 {
        1.0
    } else {
        let spacing = (input.days_since_last / QUESTION_SPACING_DAYS).clamp(0.0, 1.0);
        (0.6 * (1.0 - input.question_accuracy.clamp(0.0, 1.0)) + 0.4 * spacing).clamp(0.0, 1.0)
    };
    input.topic_points.max(0.0) * topic_weakness * need
}

#[cfg(test)]
mod test {
    use super::*;

    fn input(retrievability: f32, difficulty: f32, topic_points: f32) -> ReviewPriorityInput {
        ReviewPriorityInput {
            retrievability,
            difficulty,
            topic_points,
        }
    }

    #[test]
    fn urgency_dominates_when_other_signals_equal() {
        // Same topic value and difficulty: the card you're about to forget
        // (low retrievability) must outrank the one you'll easily recall.
        let about_to_forget = points_at_stake(&input(0.2, 0.0, 1.0));
        let well_known = points_at_stake(&input(0.9, 0.0, 1.0));
        assert!(
            about_to_forget > well_known,
            "{about_to_forget} !> {well_known}"
        );
        // A perfectly-recalled card has zero points at stake.
        assert_eq!(points_at_stake(&input(1.0, 1.0, 5.0)), 0.0);
    }

    #[test]
    fn topic_points_scale_priority_linearly() {
        // Equal urgency and difficulty: doubling the topic's points doubles the
        // priority. This is what makes high-yield MCAT topics surface first.
        let low_yield = points_at_stake(&input(0.5, 0.0, 1.0));
        let high_yield = points_at_stake(&input(0.5, 0.0, 2.0));
        assert!((high_yield - 2.0 * low_yield).abs() < 1e-6);
    }

    #[test]
    fn weakness_breaks_ties_toward_harder_cards() {
        // Equal urgency and topic value: the harder (weaker) card wins, and the
        // weighting is bounded (difficulty saturates at 1.0, doubling priority).
        let hard = points_at_stake(&input(0.5, 1.0, 1.0));
        let easy = points_at_stake(&input(0.5, 0.0, 1.0));
        assert!(hard > easy, "{hard} !> {easy}");
        assert!((hard - 2.0 * easy).abs() < 1e-6);
        // Difficulty above the normalized range can't keep inflating priority.
        let clamped = points_at_stake(&input(0.5, 5.0, 1.0));
        assert!((clamped - hard).abs() < 1e-6);
    }

    fn q(topic_points: f32, topic_acc: f32, attempts: u32, q_acc: f32, days: f32) -> f32 {
        question_priority(&QuestionPriorityInput {
            topic_points,
            topic_accuracy: topic_acc,
            attempts,
            question_accuracy: q_acc,
            days_since_last: days,
        })
    }

    #[test]
    fn unseen_question_outranks_a_freshly_correct_one() {
        // Same topic: a question you've never seen should beat one you just
        // answered correctly today.
        let unseen = q(1.0, 0.6, 0, 0.0, 0.0);
        let just_aced = q(1.0, 0.6, 3, 1.0, 0.0);
        assert!(unseen > just_aced, "{unseen} !> {just_aced}");
    }

    #[test]
    fn weaker_topic_wins_when_question_need_is_equal() {
        // Identical (unseen) question need, but the topic you're worse at carries
        // more weakness, so its question surfaces first.
        let weak_topic = q(1.0, 0.3, 0, 0.0, 0.0);
        let strong_topic = q(1.0, 0.9, 0, 0.0, 0.0);
        assert!(weak_topic > strong_topic, "{weak_topic} !> {strong_topic}");
    }

    #[test]
    fn high_yield_topic_scales_priority() {
        // Equal weakness/need: doubling the topic's points roughly doubles it.
        let low = q(1.0, 0.5, 0, 0.0, 0.0);
        let high = q(2.0, 0.5, 0, 0.0, 0.0);
        assert!((high - 2.0 * low).abs() < 1e-6);
    }

    #[test]
    fn mastered_topic_still_gets_a_priority_floor() {
        // Even a perfectly-known topic keeps a small non-zero weakness so its
        // unseen questions eventually get covered.
        let mastered_unseen = q(1.0, 1.0, 0, 0.0, 0.0);
        assert!(mastered_unseen > 0.0, "{mastered_unseen} should be > 0");
    }

    #[test]
    fn staleness_revives_a_known_question() {
        // A question answered right but long ago should rank above the same
        // question answered right just now.
        let stale = q(1.0, 0.6, 2, 1.0, 30.0);
        let fresh = q(1.0, 0.6, 2, 1.0, 0.0);
        assert!(stale > fresh, "{stale} !> {fresh}");
    }

    #[test]
    fn smoothing_pulls_extremes_toward_the_prior() {
        // No data -> the prior mean exactly.
        assert!((smoothed_accuracy(0.0, 0.0) - TOPIC_ACC_PRIOR_MEAN).abs() < 1e-6);
        // One correct answer can't claim 100% mastery.
        let one_right = smoothed_accuracy(1.0, 1.0);
        assert!(one_right < 1.0 && one_right > TOPIC_ACC_PRIOR_MEAN);
        // One wrong answer can't claim 0% either.
        let one_wrong = smoothed_accuracy(0.0, 1.0);
        assert!(one_wrong > 0.0 && one_wrong < TOPIC_ACC_PRIOR_MEAN);
    }
}
