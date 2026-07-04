// Copyright: MCAT Speedrun fork
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! The three Speedrun scores — kept deliberately *separate* and *honest*.
//!
//! The mission requires three numbers that measure three different things and
//! are never silently blended:
//!
//! * **Memory** — how much of the material you have *studied* you currently
//!   retain (retrieval strength of facts). Driven by FSRS retrievability over
//!   your cards. Says nothing about material you haven't touched.
//! * **Performance** — how well you *apply* knowledge on **new exam-style
//!   questions** (not the flashcards you drilled). Driven by graded attempts on
//!   application items, recency- and topic-weighted.
//! * **Readiness** — a projected MCAT scaled score (472–528) with an explicit
//!   range and confidence. Driven primarily by applied Performance, with Memory
//!   as a supporting/ceiling factor, and calibrated against real full-length
//!   practice-test outcomes once they exist.
//!
//! ## Honesty rules (enforced here, not by the UI)
//! 1. **Give-up rule** — below a minimum amount of evidence a score is withheld
//!    (`value == None` with a `reason`) instead of shown as a number. For
//!    Performance this means *full topic coverage with depth*: a number is only
//!    shown once **every** topic in the question bank has been tested several
//!    times, so predictions never rest on partial subject coverage.
//! 2. **No readiness without application** — Readiness is *refused* when there
//!    is no Performance signal. Memorizing cards alone never produces a
//!    readiness number; that would be an unbacked claim.
//! 3. **Uncertainty is visible** — Readiness always reports a range that widens
//!    with less data, uneven topic coverage, and larger past-prediction error.
//! 4. **Prove yourself wrong** — `CalibrationPoint`s (projected vs. the user's
//!    actual full-length score) feed the range width and a displayed accuracy
//!    note, so the model is held to account.
//!
//! Everything here is pure and deterministic so it can be unit tested without a
//! collection and so the UI can show the exact same numbers as evidence.

use std::collections::HashMap;
use std::collections::HashSet;

/// Tunable thresholds and the percent-correct → scaled-score mapping.
///
/// The mapping anchors are an explicit, documented *assumption* (we have no
/// official AAMC conversion table); they are replaced/validated by calibration
/// against the user's real practice-test scores.
#[derive(Debug, Clone)]
pub struct ScoreConfig {
    /// Minimum studied cards before a Memory score is shown.
    pub memory_min_cards: usize,
    /// Minimum total graded attempts before a Performance score is shown (a
    /// light floor; the per-topic depth rule below is usually the binding one).
    pub performance_min_attempts: usize,
    /// A topic counts as "tested with depth" once it has at least this many
    /// graded attempts. **Every** topic in the question bank must reach this
    /// depth before a Performance (and therefore Readiness) score is shown, so
    /// predictions never rest on partial subject coverage.
    pub performance_min_attempts_per_topic: usize,
    /// Half-life (days) for recency-weighting Performance attempts.
    pub recency_half_life_days: f64,
    /// MCAT total scale bounds.
    pub mcat_min: f64,
    pub mcat_max: f64,
    /// Lower mapping anchor: `map_low_pct` correct → `map_low_score`.
    pub map_low_pct: f64,
    pub map_low_score: f64,
    /// Upper mapping anchor: `map_high_pct` correct → `map_high_score`.
    pub map_high_pct: f64,
    pub map_high_score: f64,
    /// z value for the Performance accuracy confidence interval (~80%).
    pub interval_z: f64,
    /// Score uncertainty (points) added to the range when the model has never
    /// been calibrated against a real practice test.
    pub uncalibrated_uncertainty: f64,
}

impl Default for ScoreConfig {
    fn default() -> Self {
        Self {
            memory_min_cards: 20,
            performance_min_attempts: 8,
            performance_min_attempts_per_topic: 3,
            recency_half_life_days: 21.0,
            mcat_min: 472.0,
            mcat_max: 528.0,
            // ~30% correct ≈ 486, ~90% correct ≈ 522 (≈500 at ~50%). Assumption.
            map_low_pct: 0.30,
            map_low_score: 486.0,
            map_high_pct: 0.90,
            map_high_score: 522.0,
            interval_z: 1.28,
            uncalibrated_uncertainty: 6.0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Confidence {
    Low,
    Medium,
    High,
}

/// Per-card input for the Memory score.
#[derive(Debug, Clone, Copy)]
pub struct CardMemoryInput {
    /// Current probability of recall, 0..=1 (FSRS retrievability).
    pub retrievability: f32,
    /// MCAT points on this card's topic (>= 0).
    pub topic_points: f32,
    /// Topic identifier (for coverage accounting).
    pub topic_id: u32,
    /// Whether the card has been studied enough to have a memory estimate.
    pub studied: bool,
}

/// One graded attempt on an application (exam-style) question.
#[derive(Debug, Clone, Copy)]
pub struct QuestionAttempt {
    pub correct: bool,
    pub topic_id: u32,
    pub topic_points: f32,
    /// Item difficulty 0..=1 (kept for context/calibration; not used to inflate
    /// the raw accuracy in v1).
    pub difficulty: f32,
    /// How long ago the attempt happened, in days (>= 0).
    pub age_days: f32,
}

/// A past projection checked against a real full-length practice-test score.
#[derive(Debug, Clone, Copy)]
pub struct CalibrationPoint {
    pub projected: f32,
    pub actual: f32,
}

#[derive(Debug, Clone)]
pub struct MemoryScore {
    /// 0..=100, or None when withheld (give-up rule).
    pub value: Option<f32>,
    pub studied_cards: usize,
    pub total_cards: usize,
    /// Fraction of known topics that have at least one studied card, 0..=1.
    pub topic_coverage: f32,
    pub reason_withheld: Option<String>,
}

#[derive(Debug, Clone)]
pub struct PerformanceScore {
    /// 0..=100 recency/topic-weighted accuracy, or None when withheld.
    pub value: Option<f32>,
    pub attempts: usize,
    /// Recency-weighted effective sample size.
    pub effective_attempts: f32,
    pub topics_covered: usize,
    pub reason_withheld: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ReadinessScore {
    /// Projected MCAT total 472..=528, or None when refused.
    pub projected: Option<f32>,
    pub low: Option<f32>,
    pub high: Option<f32>,
    pub confidence: Confidence,
    pub reason_withheld: Option<String>,
    /// Human-readable calibration status (always present).
    pub calibration_note: String,
}

/// Memory = topic-weighted mean retrievability over *studied* cards.
pub fn memory_score(cards: &[CardMemoryInput], cfg: &ScoreConfig) -> MemoryScore {
    let total_cards = cards.len();
    let studied: Vec<&CardMemoryInput> = cards.iter().filter(|c| c.studied).collect();
    let studied_cards = studied.len();

    let all_topics: HashSet<u32> = cards.iter().map(|c| c.topic_id).collect();
    let studied_topics: HashSet<u32> = studied.iter().map(|c| c.topic_id).collect();
    let topic_coverage = if all_topics.is_empty() {
        0.0
    } else {
        studied_topics.len() as f32 / all_topics.len() as f32
    };

    if studied_cards < cfg.memory_min_cards {
        return MemoryScore {
            value: None,
            studied_cards,
            total_cards,
            topic_coverage,
            reason_withheld: Some(format!(
                "Only {studied_cards} studied card(s); need {} before estimating retention.",
                cfg.memory_min_cards
            )),
        };
    }

    let mut weight_sum = 0.0f64;
    let mut weighted = 0.0f64;
    for c in &studied {
        let w = c.topic_points.max(0.0) as f64;
        // Guard against an all-zero-points set: fall back to unweighted.
        let w = if w == 0.0 { 1.0 } else { w };
        weight_sum += w;
        weighted += w * (c.retrievability.clamp(0.0, 1.0) as f64);
    }
    let value = if weight_sum > 0.0 {
        (weighted / weight_sum * 100.0) as f32
    } else {
        0.0
    };

    MemoryScore {
        value: Some(value),
        studied_cards,
        total_cards,
        topic_coverage,
        reason_withheld: None,
    }
}

/// Performance = recency- and topic-weighted accuracy on application questions.
///
/// `total_topics` is the number of distinct topics that exist in the question
/// bank (including any not yet attempted). Every one of them must be tested to
/// depth before a number is shown.
pub fn performance_score(
    attempts: &[QuestionAttempt],
    total_topics: usize,
    cfg: &ScoreConfig,
) -> PerformanceScore {
    let n = attempts.len();
    let mut per_topic: HashMap<u32, usize> = HashMap::new();
    for a in attempts {
        *per_topic.entry(a.topic_id).or_default() += 1;
    }
    let topics_covered = per_topic.len();
    let topics_with_depth = per_topic
        .values()
        .filter(|&&c| c >= cfg.performance_min_attempts_per_topic)
        .count();

    // Give-up rule: EVERY topic in the bank must be tested to depth (plus a
    // light overall floor) before showing an applied number.
    let full_coverage = total_topics > 0 && topics_with_depth >= total_topics;
    if !full_coverage || n < cfg.performance_min_attempts {
        let reason = if total_topics == 0 {
            "No application questions in the bank yet — set up MCAT content (or import \
             questions), then answer them."
                .to_string()
        } else if !full_coverage {
            format!(
                "Hit every topic at least {} times before predictions — {}/{} topics tested \
                 in depth so far.",
                cfg.performance_min_attempts_per_topic, topics_with_depth, total_topics
            )
        } else {
            format!(
                "Only {n} graded question(s); need {} before estimating applied performance.",
                cfg.performance_min_attempts
            )
        };
        return PerformanceScore {
            value: None,
            attempts: n,
            effective_attempts: 0.0,
            topics_covered,
            reason_withheld: Some(reason),
        };
    }

    let mut weight_sum = 0.0f64;
    let mut weighted_correct = 0.0f64;
    for a in attempts {
        let recency = 0.5f64.powf((a.age_days.max(0.0) as f64) / cfg.recency_half_life_days);
        let topic_w = a.topic_points.max(0.0) as f64;
        let topic_w = if topic_w == 0.0 { 1.0 } else { topic_w };
        let w = recency * topic_w;
        weight_sum += w;
        if a.correct {
            weighted_correct += w;
        }
    }
    let acc = if weight_sum > 0.0 {
        weighted_correct / weight_sum
    } else {
        0.0
    };

    PerformanceScore {
        value: Some((acc * 100.0) as f32),
        attempts: n,
        effective_attempts: weight_sum as f32,
        topics_covered,
        reason_withheld: None,
    }
}

/// Readiness = projected MCAT score with a range, gated on applied Performance.
pub fn readiness_score(
    memory: &MemoryScore,
    performance: &PerformanceScore,
    calibration: &[CalibrationPoint],
    cfg: &ScoreConfig,
) -> ReadinessScore {
    let calibration_note = calibration_note(calibration);

    // Honesty rule #2: no application signal → refuse to project.
    let perf_pct = match performance.value {
        Some(v) => (v / 100.0) as f64,
        None => {
            return ReadinessScore {
                projected: None,
                low: None,
                high: None,
                confidence: Confidence::Low,
                reason_withheld: Some(
                    "No applied-question evidence yet — take a practice set so Readiness can be \
                     backed by performance, not just memorization."
                        .to_string(),
                ),
                calibration_note,
            };
        }
    };

    // Memory acts as a ceiling factor in [0.8, 1.0]: weak retention caps how much
    // measured performance we trust to hold on test day. Unknown memory → neutral
    // 0.9 and lower confidence.
    let (mem_mult, mem_known) = match memory.value {
        Some(m) => (0.8 + 0.2 * (m as f64 / 100.0).clamp(0.0, 1.0), true),
        None => (0.9, false),
    };

    let effective_pct = (perf_pct * mem_mult).clamp(0.0, 1.0);
    let projected = map_pct_to_score(effective_pct, cfg);

    // Range: Wilson interval on the accuracy (sample size = raw attempts),
    // scaled by the same memory multiplier, mapped to score, then inflated by
    // calibration error (or a default when uncalibrated).
    let (lo_pct, hi_pct) = wilson_interval(perf_pct, performance.attempts, cfg.interval_z);
    let mut low = map_pct_to_score((lo_pct * mem_mult).clamp(0.0, 1.0), cfg);
    let mut high = map_pct_to_score((hi_pct * mem_mult).clamp(0.0, 1.0), cfg);

    let extra = calibration_uncertainty(calibration, cfg);
    low = (low - extra).max(cfg.mcat_min);
    high = (high + extra).min(cfg.mcat_max);

    let confidence = readiness_confidence(performance, mem_known, calibration);

    ReadinessScore {
        projected: Some(projected as f32),
        low: Some(low as f32),
        high: Some(high as f32),
        confidence,
        reason_withheld: None,
        calibration_note,
    }
}

fn map_pct_to_score(pct: f64, cfg: &ScoreConfig) -> f64 {
    let span_pct = (cfg.map_high_pct - cfg.map_low_pct).max(1e-6);
    let t = (pct - cfg.map_low_pct) / span_pct;
    let score = cfg.map_low_score + t * (cfg.map_high_score - cfg.map_low_score);
    score.clamp(cfg.mcat_min, cfg.mcat_max)
}

/// Wilson score interval for a binomial proportion. Returns (low, high) in
/// 0..=1.
fn wilson_interval(p: f64, n: usize, z: f64) -> (f64, f64) {
    if n == 0 {
        return (0.0, 1.0);
    }
    let n = n as f64;
    let z2 = z * z;
    let denom = 1.0 + z2 / n;
    let centre = p + z2 / (2.0 * n);
    let margin = z * (p * (1.0 - p) / n + z2 / (4.0 * n * n)).sqrt();
    (
        ((centre - margin) / denom).clamp(0.0, 1.0),
        ((centre + margin) / denom).clamp(0.0, 1.0),
    )
}

fn calibration_rmse(calibration: &[CalibrationPoint]) -> Option<f64> {
    if calibration.is_empty() {
        return None;
    }
    let sum_sq: f64 = calibration
        .iter()
        .map(|c| {
            let e = c.projected as f64 - c.actual as f64;
            e * e
        })
        .sum();
    Some((sum_sq / calibration.len() as f64).sqrt())
}

fn calibration_uncertainty(calibration: &[CalibrationPoint], cfg: &ScoreConfig) -> f64 {
    match calibration_rmse(calibration) {
        Some(rmse) => rmse,
        None => cfg.uncalibrated_uncertainty,
    }
}

fn calibration_note(calibration: &[CalibrationPoint]) -> String {
    match calibration_rmse(calibration) {
        Some(rmse) => format!(
            "Past projections were off by ±{:.0} points (n={}).",
            rmse,
            calibration.len()
        ),
        None => "Not yet calibrated to a full-length practice test.".to_string(),
    }
}

fn readiness_confidence(
    performance: &PerformanceScore,
    memory_known: bool,
    calibration: &[CalibrationPoint],
) -> Confidence {
    let n = performance.attempts;
    let coverage = performance.topics_covered;
    let calibrated = !calibration.is_empty();
    if n >= 50 && coverage >= 5 && memory_known && calibrated {
        Confidence::High
    } else if n >= 25 && coverage >= 3 && memory_known {
        Confidence::Medium
    } else {
        Confidence::Low
    }
}

#[cfg(test)]
mod test {
    use super::*;

    fn card(r: f32, points: f32, topic: u32, studied: bool) -> CardMemoryInput {
        CardMemoryInput {
            retrievability: r,
            topic_points: points,
            topic_id: topic,
            studied,
        }
    }

    fn attempt(correct: bool, topic: u32, age_days: f32) -> QuestionAttempt {
        QuestionAttempt {
            correct,
            topic_id: topic,
            topic_points: 1.0,
            difficulty: 0.5,
            age_days,
        }
    }

    fn many_attempts(n: usize, correct: usize, topics: u32) -> Vec<QuestionAttempt> {
        (0..n)
            .map(|i| attempt(i < correct, (i as u32) % topics.max(1), 0.0))
            .collect()
    }

    #[test]
    fn memory_withheld_below_minimum() {
        let cfg = ScoreConfig::default();
        let cards: Vec<_> = (0..5).map(|i| card(0.9, 1.0, i, true)).collect();
        let m = memory_score(&cards, &cfg);
        assert!(m.value.is_none());
        assert!(m.reason_withheld.is_some());
        assert_eq!(m.studied_cards, 5);
    }

    #[test]
    fn memory_is_topic_weighted_mean_retrievability() {
        let cfg = ScoreConfig::default();
        // 30 studied cards: high-points topic recalled well, low-points poorly.
        let mut cards = vec![];
        for i in 0..15 {
            cards.push(card(0.9, 3.0, i, true)); // high yield, strong
        }
        for i in 15..30 {
            cards.push(card(0.5, 1.0, i, true)); // low yield, weak
        }
        let m = memory_score(&cards, &cfg);
        let v = m.value.unwrap();
        // Weighted mean = (15*3*0.9 + 15*1*0.5)/(15*3+15*1) = (40.5+7.5)/60 = 0.8.
        assert!((v - 80.0).abs() < 0.5, "got {v}");
        assert_eq!(m.studied_cards, 30);
        assert!((m.topic_coverage - 1.0).abs() < 1e-6);
    }

    #[test]
    fn memory_coverage_reflects_unstudied_topics() {
        let cfg = ScoreConfig {
            memory_min_cards: 1,
            ..Default::default()
        };
        let cards = vec![
            card(0.9, 1.0, 1, true),
            card(0.9, 1.0, 2, false),
            card(0.9, 1.0, 3, false),
        ];
        let m = memory_score(&cards, &cfg);
        assert!((m.topic_coverage - 1.0 / 3.0).abs() < 1e-6);
    }

    #[test]
    fn performance_withheld_below_minimum() {
        let cfg = ScoreConfig::default();
        let p = performance_score(&many_attempts(5, 5, 2), 2, &cfg);
        assert!(p.value.is_none());
        assert_eq!(p.attempts, 5);
        assert!(p.reason_withheld.is_some());
    }

    #[test]
    fn performance_weights_recent_attempts_more() {
        let cfg = ScoreConfig::default();
        // Spread across 3 topics (to satisfy the depth gate). Recent correct,
        // old wrong -> above 50%.
        let mut recent_good = vec![];
        for t in 0..3 {
            for _ in 0..5 {
                recent_good.push(attempt(true, t, 0.0)); // today
            }
            for _ in 0..5 {
                recent_good.push(attempt(false, t, 120.0)); // long ago
            }
        }
        let p = performance_score(&recent_good, 3, &cfg).value.unwrap();
        assert!(p > 60.0, "recent-good should beat 50%, got {p}");

        // Mirror image: recent wrong, old right -> below 50%.
        let mut recent_bad = vec![];
        for t in 0..3 {
            for _ in 0..5 {
                recent_bad.push(attempt(false, t, 0.0));
            }
            for _ in 0..5 {
                recent_bad.push(attempt(true, t, 120.0));
            }
        }
        let p2 = performance_score(&recent_bad, 3, &cfg).value.unwrap();
        assert!(p2 < 40.0, "recent-bad should be below 50%, got {p2}");
    }

    #[test]
    fn performance_needs_every_topic_hit_to_depth() {
        let cfg = ScoreConfig::default();
        // Bank has 3 topics. Deep in only 2 of them -> withheld (partial cover).
        let mut two_of_three = vec![];
        for t in 0..2 {
            for _ in 0..10 {
                two_of_three.push(attempt(true, t, 0.0));
            }
        }
        let p = performance_score(&two_of_three, 3, &cfg);
        assert!(
            p.value.is_none(),
            "partial coverage must not unlock a score"
        );
        let reason = p.reason_withheld.unwrap();
        assert!(reason.contains("every topic"));
        assert!(
            reason.contains("2/3"),
            "reason should report coverage: {reason}"
        );

        // Third topic present but only 2 attempts (below depth) -> still withheld.
        let mut third_shallow = two_of_three.clone();
        third_shallow.push(attempt(true, 2, 0.0));
        third_shallow.push(attempt(true, 2, 0.0));
        assert!(performance_score(&third_shallow, 3, &cfg).value.is_none());

        // All 3 topics with >= 3 attempts -> unlocked.
        let mut third_deep = two_of_three;
        for _ in 0..3 {
            third_deep.push(attempt(true, 2, 0.0));
        }
        assert!(
            performance_score(&third_deep, 3, &cfg).value.is_some(),
            "every topic hit to depth should unlock Performance"
        );
    }

    #[test]
    fn readiness_refused_without_performance() {
        let cfg = ScoreConfig::default();
        let cards: Vec<_> = (0..100).map(|i| card(0.95, 1.0, i % 10, true)).collect();
        let mem = memory_score(&cards, &cfg);
        assert!(mem.value.is_some(), "memory should be known");
        let perf = performance_score(&[], 0, &cfg);
        let r = readiness_score(&mem, &perf, &[], &cfg);
        // Even with excellent memory, readiness must be refused.
        assert!(r.projected.is_none());
        assert!(r.reason_withheld.is_some());
    }

    #[test]
    fn readiness_range_widens_with_less_data() {
        let cfg = ScoreConfig::default();
        let mem = memory_score(
            &(0..100)
                .map(|i| card(0.9, 1.0, i % 10, true))
                .collect::<Vec<_>>(),
            &cfg,
        );

        let small = performance_score(&many_attempts(20, 10, 5), 5, &cfg);
        let large = performance_score(&many_attempts(200, 100, 5), 5, &cfg);
        let r_small = readiness_score(&mem, &small, &[], &cfg);
        let r_large = readiness_score(&mem, &large, &[], &cfg);

        let width = |r: &ReadinessScore| r.high.unwrap() - r.low.unwrap();
        assert!(
            width(&r_small) > width(&r_large),
            "small-n width {} should exceed large-n width {}",
            width(&r_small),
            width(&r_large)
        );
    }

    #[test]
    fn weaker_memory_lowers_readiness() {
        let cfg = ScoreConfig::default();
        let perf = performance_score(&many_attempts(60, 42, 6), 6, &cfg); // 70%
        let strong_mem = memory_score(
            &(0..50)
                .map(|i| card(0.98, 1.0, i % 10, true))
                .collect::<Vec<_>>(),
            &cfg,
        );
        let weak_mem = memory_score(
            &(0..50)
                .map(|i| card(0.40, 1.0, i % 10, true))
                .collect::<Vec<_>>(),
            &cfg,
        );
        let r_strong = readiness_score(&strong_mem, &perf, &[], &cfg)
            .projected
            .unwrap();
        let r_weak = readiness_score(&weak_mem, &perf, &[], &cfg)
            .projected
            .unwrap();
        assert!(
            r_strong > r_weak,
            "strong memory {r_strong} should project higher than weak {r_weak}"
        );
    }

    #[test]
    fn calibration_sets_note_and_confidence() {
        let cfg = ScoreConfig::default();
        let mem = memory_score(
            &(0..80)
                .map(|i| card(0.9, 1.0, i % 10, true))
                .collect::<Vec<_>>(),
            &cfg,
        );
        let perf = performance_score(&many_attempts(60, 42, 6), 6, &cfg);

        let uncal = readiness_score(&mem, &perf, &[], &cfg);
        assert!(uncal.calibration_note.contains("Not yet calibrated"));
        assert_ne!(uncal.confidence, Confidence::High);

        let cal = vec![
            CalibrationPoint {
                projected: 508.0,
                actual: 510.0,
            },
            CalibrationPoint {
                projected: 512.0,
                actual: 509.0,
            },
        ];
        let r = readiness_score(&mem, &perf, &cal, &cfg);
        assert!(r.calibration_note.contains("off by"));
        assert_eq!(r.confidence, Confidence::High);
    }

    #[test]
    fn projection_is_bounded_to_the_mcat_scale() {
        let cfg = ScoreConfig::default();
        let mem = memory_score(
            &(0..80)
                .map(|i| card(1.0, 1.0, i % 10, true))
                .collect::<Vec<_>>(),
            &cfg,
        );
        let perfect = performance_score(&many_attempts(100, 100, 6), 6, &cfg);
        let zero = performance_score(&many_attempts(100, 0, 6), 6, &cfg);
        let r_hi = readiness_score(&mem, &perfect, &[], &cfg);
        let r_lo = readiness_score(&mem, &zero, &[], &cfg);
        for r in [&r_hi, &r_lo] {
            let p = r.projected.unwrap();
            assert!((472.0..=528.0).contains(&p), "out of scale: {p}");
            assert!(r.low.unwrap() >= 472.0 && r.high.unwrap() <= 528.0);
        }
    }
}
