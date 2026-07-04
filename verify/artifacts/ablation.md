# Study-feature ablation — interleaving OFF vs ON (§8)

Feature under test: **interleaving** (pull across all topics), plus its **weakness-weighting** refinement — `rslib/src/speedrun/queue.rs`, interleave behaviour asserted in `rslib/src/speedrun/concepts.rs`. Equal study budget of **480 trials** across 6 topics (8 items each, heterogeneous difficulty); delayed test **21 days** after study. Mean of 200 simulated learners (spacing-effect forgetting model; labelled simulation, not a human trial).

**Hypothesis (pre-registered above in the docstring):** at equal study time, interleaving ON beats blocked practice on delayed recall; weakness-weighting further protects the hardest items.

| build (scheduler)             | overall recall | hardest-third recall |
| ----------------------------- | -------------: | -------------------: |
| interleaving OFF (blocked)    |          11.1% |                 3.5% |
| interleaving ON (round-robin) |          46.1% |                11.6% |
| interleaving ON + weakness    |          40.2% |                28.6% |

**Primary result: supported.** Turning interleaving ON lifts delayed recall from 11.1% to 46.1% (+35.0 pts) at identical study time — blocked practice lets early topics decay, interleaving spaces every item.

**Weakness-weighting** trades a little average recall to raise the hardest third from 11.6% to 28.6% — it spends the fixed budget on the items most at risk, which is what a readiness-driven queue should do.

> Reproduce: `out/pyenv/bin/python verify/ablation.py --out verify/artifacts/ablation.md`
