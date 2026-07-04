# Performance model

**Question:** can you answer a _new_, exam-style question that uses a fact —
including questions you have never seen — rather than just recall the flashcard?
This is the harder bridge the brief calls out: memory ≠ application.

## Inputs

- Graded **attempts** on application questions (`mcat-question` items): correct/
  incorrect, topic id, topic points, age in days. Stored in each card's
  `custom_data` attempt log (`rslib/src/speedrun/content.rs`).

## Math

`performance_score` (`rslib/src/speedrun/scores.rs`) is a **recency- and
topic-weighted accuracy**:

```
weight_i   = 0.5^(age_days_i / 21) · topic_points_i     (21-day half-life)
performance = Σ (weight_i · correct_i) / Σ weight_i      (×100)
```

Recent attempts count more (skills drift); high-yield topics count more. It also
reports the recency-weighted **effective sample size** and topics covered.

## Give-up rule (strict)

A number is shown only when **every topic in the question bank has been tested to
depth** — at least `performance_min_attempts_per_topic = 3` graded attempts each
— plus a light overall floor of 8 attempts. Partial subject coverage never
unlocks a score (unit test `performance_needs_every_topic_hit_to_depth`).

## Evidence (held-out)

- `verify/performance_eval.py` → `verify/artifacts/performance.md`: held-out
  accuracy on exam-style questions, shown to **beat a memory-only predictor**
  (captures the application gap rather than echoing memory).
- `verify/paraphrase.py` → `verify/artifacts/paraphrase.md`: reworded, same-idea
  questions score meaningfully **lower** than flashcard recall (a real ~11-point
  memory→performance gap), proving Performance measures something Memory does
  not.
