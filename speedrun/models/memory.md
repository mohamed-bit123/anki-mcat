# Memory model

**Question:** of the material you have _studied_, how much do you retain right
now? It says nothing about material you have never touched — that is Readiness's
coverage job, not Memory's.

## Inputs

- Per studied card: FSRS **retrievability** (probability of recall today, 0–1),
  the card's **topic points** (MCAT yield weight), and topic id.
- Source: Anki/FSRS memory state, computed by the shared Rust engine.

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
