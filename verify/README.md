# Verify — one place to check build, installer, test, and latency

Everything a reviewer needs to confirm the MCAT Speedrun fork works, in a single
folder. Every result below is reproducible with one command, and the captured
outputs live in [`artifacts/`](artifacts/).

## One command

```bash
bash verify/run-all.sh
```

Builds the engine, runs the MCAT Rust + Python test suites, the desktop↔mobile
sync round-trip, the offline-conflict and crash-safety tests, the held-out model
evals (memory calibration, performance, paraphrase, leakage), the study-feature
ablation, the outline-coverage map, the AI gold-set vs. baseline comparison, and
the latency benchmark — writing each result to `verify/artifacts/`. (Needs the
build prerequisites in [`../speedrun/TESTING.md`](../speedrun/TESTING.md). The AI
gold-set row needs `OPENAI_API_KEY`; without it the baselines still run.)

## What to look at

| Concern                    | How to reproduce                                                      | Artifact                                                                                                           | Latest result                                                               |
| -------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| **Build**                  | `just build`                                                          | [`artifacts/build.log`](artifacts/build.log), [`artifacts/build-proof.txt`](artifacts/build-proof.txt)             | ✅ builds; custom RPC live: `speedrun: scheduler engine alive (anki 26.05)` |
| **Installer**              | `just wheels`                                                         | [`artifacts/wheels.log`](artifacts/wheels.log)                                                                     | ✅ `anki-26.5` (15M, embeds Rust engine) + `aqt-26.5` (4.4M) wheels         |
| **Test**                   | `cargo test -p anki speedrun::` / `pytest pylib/tests/test_speedrun*` | [`artifacts/tests-rust.txt`](artifacts/tests-rust.txt), [`artifacts/tests-python.txt`](artifacts/tests-python.txt) | ✅ 32 Rust + 5 Python pass                                                  |
| **Latency**                | `python verify/bench.py`                                              | [`artifacts/latency.md`](artifacts/latency.md)                                                                     | ✅ all p95 far under target (see below)                                     |
| **Latency @ 50k (7h/§10)** | `python verify/bench.py --cards 50000`                                | [`artifacts/latency-50k.md`](artifacts/latency-50k.md)                                                             | ✅ scores refresh p95 143ms (<500), cold load 96ms (<1s), ~82 MB peak       |
| **Sync**                   | `python speedrun/sync_check.py`                                       | [`artifacts/sync.txt`](artifacts/sync.txt)                                                                         | ✅ scores/strength/attempts round-trip identical                            |
| **Conflict (7b)**          | `python verify/conflict_check.py`                                     | [`artifacts/conflict.md`](artifacts/conflict.md)                                                                   | ✅ offline reviews merge: 0 lost, 0 double-counted; state converges         |
| **Crash (7g)**             | `python verify/crash_test.py`                                         | [`artifacts/crash.md`](artifacts/crash.md)                                                                         | ✅ 20/20 SIGKILL mid-write → integrity ok, no data loss                     |
| **Memory calib (§9.1)**    | `python verify/calibration.py`                                        | [`artifacts/calibration.md`](artifacts/calibration.md)                                                             | ✅ Brier 0.216 < baseline; ECE 0.024 (well-calibrated)                      |
| **Performance (§9.2)**     | `python verify/performance_eval.py`                                   | [`artifacts/performance.md`](artifacts/performance.md)                                                             | ✅ 62.9% held-out, beats memory-only predictor                              |
| **Paraphrase (7d)**        | `python verify/paraphrase.py`                                         | [`artifacts/paraphrase.md`](artifacts/paraphrase.md)                                                               | ✅ ~11-pt memory→performance gap (bridge is real)                           |
| **Leakage (7e)**           | `python verify/leakage.py`                                            | [`artifacts/leakage.md`](artifacts/leakage.md)                                                                     | ✅ CLEAN — no test item leaks into training                                 |
| **Ablation (§8)**          | `python verify/ablation.py`                                           | [`artifacts/ablation.md`](artifacts/ablation.md)                                                                   | ✅ interleaving ON 46% vs OFF 11%; weakness lifts hardest third             |
| **Coverage (7c)**          | `python verify/coverage_map.py`                                       | [`artifacts/coverage.md`](artifacts/coverage.md)                                                                   | ✅ 29/31 (94%) of official AAMC content categories; gaps listed             |
| **AI gold set (7f)**       | `python verify/goldset.py --use-ai`                                   | [`artifacts/goldset.md`](artifacts/goldset.md)                                                                     | ✅ AI 100% vs vector 60% / keyword 36% (beats baselines, clears cutoff)     |

Model write-ups: [`../speedrun/models/`](../speedrun/models/) (memory, performance, readiness).

---

## Build

```bash
just build          # engine + Python/Qt layers
```

Proof the _custom_ engine change is in the built binary (not stock Anki):

```bash
PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/python -c \
 "from anki.collection import Collection; import tempfile,os; \
  c=Collection(os.path.join(tempfile.mkdtemp(),'t.anki2')); \
  print(c._backend.speedrun_ping())"
# -> speedrun: scheduler engine alive (anki 26.05)
```

Captured: [`artifacts/build.log`](artifacts/build.log),
[`artifacts/build-proof.txt`](artifacts/build-proof.txt).

## Installer

The reproducible, locally-buildable installable artifact is the pair of Python
wheels (the `anki` wheel carries the compiled Rust engine):

```bash
just wheels
ls out/wheels    # anki-26.5-*.whl, aqt-26.5-*.whl
```

Captured file listing: [`artifacts/wheels.log`](artifacts/wheels.log).

- **Desktop app bundle** (`.dmg`/`.exe`) is produced by the release tooling
  (`.github/workflows/release.yml`, briefcase). It needs network to fetch the
  briefcase app-template, so it's a CI/release-time artifact rather than a
  committed binary.
- **Mobile installer** is the AnkiDroid APK built from the mobile repo:
  `AnkiDroid/build/outputs/apk/full/debug/AnkiDroid-full-*-debug.apk`
  (built on top of the native `rsdroid` `.aar`). See
  [`../speedrun/TESTING.md`](../speedrun/TESTING.md) Part 2.

> Binaries (`.whl`, `.dmg`, `.apk`) are intentionally **not** committed to git.
> Ship them via GitHub Releases; this folder captures the build _evidence_ +
> exact commands so a reviewer can reproduce them.

## Test

```bash
cargo test -p anki speedrun::                              # 32 engine tests
PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/pytest \
  pylib/tests/test_speedrun.py \
  pylib/tests/test_speedrun_scores.py \
  pylib/tests/test_speedrun_seed.py                        # 5 end-to-end tests
```

These cover the honest-scoring give-up rules, concept-FSRS scheduling,
weakness-weighted ordering, attempt logging, and idempotent seeding. Captured:
[`artifacts/tests-rust.txt`](artifacts/tests-rust.txt),
[`artifacts/tests-python.txt`](artifacts/tests-python.txt).

## Latency

```bash
PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/bench.py
```

Measures the hot-path engine actions against the targets in
[`../speedrun/PLAN.md`](../speedrun/PLAN.md) §7 (report p50/p95/worst). Latest
run (Darwin arm64, 300 iterations/action):

| action                                  | p50 (ms) | p95 (ms) | worst (ms) | vs target     |
| --------------------------------------- | -------- | -------- | ---------- | ------------- |
| record_attempt (button-press ack)       | 0.37     | 0.63     | 1.46       | PASS (<50ms)  |
| next_question (next card after grading) | 0.57     | 0.76     | 1.37       | PASS (<100ms) |
| scores refresh (dashboard refresh)      | 1.20     | 1.52     | 2.47       | PASS (<500ms) |

One-time content seed: ~60 ms (well under the 5 s cold-start budget). Full
report: [`artifacts/latency.md`](artifacts/latency.md).

## Sync

```bash
PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python speedrun/sync_check.py
```

Round-trips a seeded, practiced collection through Anki's own sync server and
asserts per-topic strength, attempt logs, topic points, and all three scores are
identical on the second device. Captured: [`artifacts/sync.txt`](artifacts/sync.txt).
