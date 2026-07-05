# Memory model

**Question:** of the material you have _studied_, how much do you retain right
now? It says nothing about material you have never touched — that is Readiness's
coverage job, not Memory's.

## Inputs

- Per studied card: FSRS **retrievability** (probability of recall today, 0–1 —
  _retrieval strength_), FSRS **stability** in days (_storage strength_,
  resistance to forgetting), a **projected retrievability** (recall on the exam
  date if you stop reviewing today), the card's **topic points** (MCAT yield
  weight), and topic id.
- Source: Anki/FSRS memory state, computed by the shared Rust engine
  (`card_retrievability_at` / `card_stability_days` in `queue.rs`).

## Retrieval strength vs. storage strength (Bjork)

FSRS separates the two properties the Brainlift is built on: **retrieval
strength** (can you recall it _now_ — decays with time since last study) and
**storage strength** (how durable it is — FSRS stability). The Memory score's
headline number is retrieval strength now; alongside it the engine reports mean
**stability (days)** and, when an exam date is set, the topic-weighted
**projected recall on exam day** (`projected_recall`). Crammed knowledge (high
retrieval, low storage) and durable knowledge look identical on the headline
number but diverge on durability — which is exactly what the projection surfaces
and what feeds Readiness.

## Math

`memory_score` (`rslib/src/speedrun/scores.rs`) is the **topic-points-weighted
mean retrievability** over studied cards:

```
memory = Σ (points_i · retrievability_i) / Σ points_i        (×100)
```

Weighting by points means high-yield topics move the number more than trivia.
It also reports `topic_coverage` = fraction of known topics with ≥1 studied
card, which feeds Readiness's confidence.

## Give-up rule

Withheld (returns `None` + reason) until at least **20 studied cards**
(`memory_min_cards`). Below that there is not enough signal to estimate
retention honestly.

## Evidence (held-out)

`verify/calibration.py` → `verify/artifacts/calibration.md`: on held-out
reviews the predicted recall is compared to empirical recall (reliability
table + reliability diagram), scored with **Brier** and **log-loss** and an
**expected calibration error (ECE)**. The model beats the always-predict-the-
mean baseline and ECE ≈ 0.024, i.e. the probabilities mean what they say.
Swap the simulated reviews for real revlog data and the same script recomputes
the numbers.
