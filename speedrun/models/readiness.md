# Readiness model (score mapping)

**Question:** what MCAT total (472–528) would you get today, as a **range** with
a stated confidence — never a single confident number with nothing behind it.

## Inputs

- The **Performance** score (primary driver) and its raw attempt count.
- The **Memory** score (ceiling factor).
- **Calibration points**: past projections vs. the user's real full-length
  practice-test totals. Entered by the student after any full-length practice
  test via **"Record full-length score"** (desktop `qt/aqt/speedrun.py`; mobile
  `SpeedrunActivity.kt`), which calls the shared-engine RPC
  `SpeedrunRecordCalibration` (`rslib/src/speedrun/content.rs`). It is stored in
  collection config (`speedrunCalibration`), so calibration **syncs** across
  devices like every other score input, and both values are clamped to 472–528.

## Math

`readiness_score` (`rslib/src/speedrun/scores.rs`):

1. **Memory ceiling.** `mem_mult = 0.8 + 0.2·ceiling` ∈ [0.8, 1.0] — weak
   retention caps how much measured performance we trust to hold on test day.
   With a **target exam date** set, `ceiling = 0.5·recall_now + 0.5·recall_projected_to_exam`,
   where the projection decays each topic's retrievability forward to the exam
   using FSRS **stability** (storage strength). So durable knowledge projects
   higher and fragile, crammed knowledge (high retrieval / low storage) projects
   lower. Without an exam date, `ceiling = recall_now` (today-only). Unknown
   memory → neutral 0.9 and lower confidence.
2. **Effective accuracy** = `performance · mem_mult`.
3. **Point → scale map** (`map_pct_to_score`): linear between documented
   anchors — ~30% correct ≈ 486, ~90% ≈ 522 (≈500 at ~50%). These anchors are an
   explicit _assumption_ (no official AAMC conversion table); calibration
   replaces them with the user's real data.
4. **Range.** A **Wilson** interval on the accuracy (sample size = attempts),
   mapped through the same steps, then widened by calibration RMSE — or by a
   default ±6 points when never calibrated — **and by the durability gap**
   (`recall_now − recall_projected_to_exam`): fragile knowledge that won't hold
   to test day makes the outcome less certain, so the range widens. The range
   widens with less data, larger past error, and a bigger durability gap (unit
   tests `readiness_range_widens_with_less_data`,
   `exam_projection_penalizes_fragile_knowledge`).
5. **Confidence** (low/medium/high) from attempt count, topic coverage, whether
   memory is known, and whether calibrated.

## Give-up rule (hard)

Readiness is **refused** whenever Performance is withheld — memorizing cards
alone never produces a readiness number (unit test
`readiness_refused_without_performance`). The projection is always clamped to
472–528.

## Honesty display

Alongside the number the app shows: the range, the **% of the exam covered**
(`verify/coverage_map.py` → `verify/artifacts/coverage.md`), confidence, last-
updated time, the main drivers, a calibration note ("past projections off by ±N
points, n=…"), and the single best next topic to study.
