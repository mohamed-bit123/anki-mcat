# MCAT Speedrun — a desktop + mobile study app built on Anki

**Exam: the MCAT** (scored **472–528**; four sections each **118–132**:
Bio/Biochem, Chem/Phys, Psych/Soc, and CARS). This is a fork of
[Anki](https://apps.ankiweb.net) that turns it into an MCAT-specific study tool
which measures three different things and is honest about what it does and does
not know.

> This is a fork of Anki. It is licensed **AGPL-3.0-or-later**, the same license
> as Anki, with full credit to Anki and its contributors (some components are
> BSD-3-Clause). See [License](#license). Upstream project:
> [ankitects/anki](https://github.com/ankitects/anki).

## What it does (three separate scores, never blended)

- **Memory** — the chance you recall a fact you have studied _right now_
  (FSRS retrievability, topic-points-weighted).
- **Performance** — the chance you get a _new_, exam-style question right,
  including ones you have never seen. This is the memory→application bridge.
- **Readiness** — a projected MCAT total (472–528) with a **range** and a
  confidence, gated on real applied evidence.

Every score is shown with its point estimate, likely range, **% of the exam
covered**, a confidence indicator, last-updated time, the main reasons, and a
**give-up rule** that withholds the number when there is not enough data.
Readiness is _refused_ entirely until there is applied-question evidence —
memorizing cards alone never produces a readiness number.

The give-up rules (stated, enforced in Rust — `rslib/src/speedrun/scores.rs`):

- **Memory**: withheld below 20 studied cards.
- **Performance**: withheld until **every topic in the question bank has ≥3
  graded attempts** (full-coverage-with-depth), plus a floor of 8 attempts.
- **Readiness**: refused whenever Performance is withheld; always clamped to
  472–528; range widens with less data and past-prediction error.

## Two apps, one engine

The desktop app (this repo) and the Android companion share the **same Rust
engine** (`rslib`) and sync through Anki's own sync protocol — reviews and MCAT
progress (per-topic strength, attempt logs, all three scores) flow both ways.

- **Desktop**: forked Anki (Rust `rslib` + Python/Qt).
- **Mobile**: [AnkiDroid fork](https://github.com/mohamed-bit123/ankidroid-mcat)
  on the [shared backend fork](https://github.com/mohamed-bit123/anki-mcat-backend)
  — the identical `rslib` engine change is compiled into the Android `.aar`, so
  the scores, give-up rule, and the Rust queue change are the same on the phone.

Scores are **recomputed from synced inputs**, never stored, so both devices
compute identical numbers. Sync round-trip and offline-conflict merges are
proven in [`verify/`](verify/).

## The real Rust engine change

A new review order — **points-at-stake, weakness-weighted, topic-interleaved** —
added inside Anki's Rust scheduler (not just the Python screens). Full write-up,
including why it belongs in Rust and not Python, the tests, undo/corruption
proof, and merge risk:

- **One-pager**: [`speedrun/RUST-CHANGE.md`](speedrun/RUST-CHANGE.md)
- **Touched upstream files + merge risk**:
  [`speedrun/TOUCHED-UPSTREAM.md`](speedrun/TOUCHED-UPSTREAM.md)
- Code: `rslib/src/speedrun/` (queue, scores, concepts, content, seed) +
  `proto/anki/*.proto` RPCs; 40+ Rust unit tests and Python end-to-end tests.

## AI (works fully with AI off)

The app is completely usable with **no AI and no key**. When enabled, AI
_generates_ MCAT questions grounded in the built-in flashcard bank
(retrieval-augmented), records provenance (source fact, model, prompt version)
on every item, and re-checks each with an independent verifier pass. What was
built, why, and what was skipped, plus the held-out eval and baseline
comparison, are in [`speedrun/HOWTO-RUN.md`](speedrun/HOWTO-RUN.md) and
[`verify/artifacts/goldset.md`](verify/artifacts/goldset.md) (AI 100% vs vector
60% / keyword 36% on a 50-item gold set). The API key is never committed.

## Build & run

- **Desktop + Mobile build/run/test instructions**:
  [`speedrun/TESTING.md`](speedrun/TESTING.md).
- **Architecture overview**: [`speedrun/REPO-MAP.md`](speedrun/REPO-MAP.md) and
  [`speedrun/PLAN.md`](speedrun/PLAN.md).
- Quick desktop build: `./ninja pylib qt` then `./run` (see
  [`docs/development.md`](docs/development.md) for prerequisites).

## Verify everything (one command)

```bash
bash verify/run-all.sh
```

Builds the engine and runs the Rust + Python tests, the sync round-trip, the
offline-conflict (§7b) and 20× crash-safety (§7g) tests, the held-out model
evals (memory calibration §9.1, performance §9.2, paraphrase §7d, leakage §7e),
the study-feature ablation (§8), the outline-coverage map (§7c), the AI
gold-set vs. baseline comparison (§7f), and the latency benchmark (§7h/§10,
incl. a **50,000-card** run: `verify/bench.py --cards 50000`). Every result is
captured under [`verify/artifacts/`](verify/artifacts/); the hub
[`verify/README.md`](verify/README.md) maps each requirement to its reproduce
command and latest result. Requirement-by-requirement status:
[`speedrun/REQUIREMENTS-AUDIT.md`](speedrun/REQUIREMENTS-AUDIT.md).

Latest 50k-card latency (Darwin arm64): record_attempt p95 **0.47 ms**,
next_question **7.7 ms**, scores refresh **143 ms**, cold dashboard load
**96 ms**, peak memory **~82 MB** — all under target.

## Model descriptions

One page each: [`speedrun/models/`](speedrun/models/) — memory, performance,
readiness (math + give-up rule + evidence).

## Brainlift

The learning-science thesis behind the app (SPOVs, expert sources, and a
principle→code map showing how each finding is implemented):
[`speedrun/BRAINLIFT.md`](speedrun/BRAINLIFT.md).

## License

Licensed under the **GNU AGPL, version 3 or later** — see [LICENSE](./LICENSE).
This is a fork of [Anki](https://apps.ankiweb.net)
([ankitects/anki](https://github.com/ankitects/anki)); all original Anki
copyright and the contributor list ([CONTRIBUTORS](./CONTRIBUTORS)) are
retained. Some Anki components are under BSD-3-Clause.
