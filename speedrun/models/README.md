# The three models

The MCAT Speedrun measures three different things and never blends them into
one number. Each has its own one-pager below: what it estimates, the exact
math, the give-up rule, and the held-out evidence that backs it.

| model                         | question it answers                                       | code                                              | evidence                                           |
| ----------------------------- | --------------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------- |
| [Memory](memory.md)           | Can you recall a fact you studied _right now_?            | `rslib/src/speedrun/scores.rs::memory_score`      | `verify/artifacts/calibration.md`                  |
| [Performance](performance.md) | Can you answer a _new_ exam-style question?               | `rslib/src/speedrun/scores.rs::performance_score` | `verify/artifacts/performance.md`, `paraphrase.md` |
| [Readiness](readiness.md)     | What MCAT score would you get today, and how sure are we? | `rslib/src/speedrun/scores.rs::readiness_score`   | `verify/artifacts/coverage.md`, calibration note   |

All three are pure, deterministic Rust functions (unit-tested in `scores.rs`)
so the desktop app, the phone app, and these docs report the exact same
numbers. The honesty rules — withhold below minimum evidence, refuse Readiness
without applied performance, always show a range, and hold past projections to
account — are enforced in the engine, not the UI.
