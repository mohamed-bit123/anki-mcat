# MCAT Speedrun — latency artifact

Machine: Darwin arm64. Iterations/action: 300. Headless, freshly-seeded collection.
Targets from `speedrun/PLAN.md` §7 (report p50/p95/worst).

| action                                  | p50 (ms) | p95 (ms) | worst (ms) | mean (ms) | n   | vs target     |
| --------------------------------------- | -------- | -------- | ---------- | --------- | --- | ------------- |
| record_attempt (button-press ack)       | 0.37     | 0.63     | 1.46       | 0.41      | 300 | PASS (<50ms)  |
| next_question (next card after grading) | 0.57     | 0.76     | 1.37       | 0.60      | 300 | PASS (<100ms) |
| scores refresh (dashboard refresh)      | 1.20     | 1.52     | 2.47       | 1.25      | 300 | PASS (<500ms) |

One-time content seed (`speedrun_seed_builtin`, 105 questions + flashcards): **60 ms** (target < 5000 ms cold-start budget).

**Overall: PASS** (every gated action's p95 is under its target).

Reproduce: `PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/bench.py`
