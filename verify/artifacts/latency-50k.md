# MCAT Speedrun — latency artifact

Machine: Darwin arm64. Iterations/action: 300. Headless, freshly-seeded collection.
Targets from `speedrun/PLAN.md` §7 / brief §10 (report p50/p95/worst).

| action                                  | p50 (ms) | p95 (ms) | worst (ms) | mean (ms) | n   | vs target     |
| --------------------------------------- | -------- | -------- | ---------- | --------- | --- | ------------- |
| record_attempt (button-press ack)       | 0.36     | 0.52     | 1.84       | 0.38      | 300 | PASS (<50ms)  |
| next_question (next card after grading) | 7.76     | 15.37    | 57.16      | 8.69      | 300 | PASS (<100ms) |
| scores refresh (dashboard refresh)      | 97.76    | 169.57   | 789.23     | 106.99    | 300 | PASS (<500ms) |

Dashboard first load (cold, single sample): **102.2 ms** (PASS < 1000 ms).

Deck size benchmarked: **50,000 cards** (padded in 5.7s). Peak memory (maxrss): **72 MB**.

One-time content seed (`speedrun_seed_builtin`, 105 questions + flashcards): **54 ms** (target < 5000 ms cold-start budget).

**Overall: PASS** (every gated action's p95 is under its target).

Reproduce: `PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/bench.py [--cards 50000]`
