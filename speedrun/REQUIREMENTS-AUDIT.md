# Requirements audit — living checklist

Maps every requirement in the Speedrun brief to its status in this repo, with
evidence. `[x]` met · `[~]` partial · `[ ]` missing. Update as items land.

Exam: **MCAT** (472–528, four 118–132 sections). AI off = fully functional.

## Hard limits (grade gates)

- [x] Real Rust change (else 50% cap) — `rslib/src/speedrun/queue.rs` (points-at-stake + interleave), proto enum + RPCs, called from Python/Kotlin.
- [x] Phone shares engine + syncs (else 70% cap) — shared `rslib`; round-trip verified (`verify/artifacts/sync.txt`); offline **conflict** merge proven (`verify/conflict_check.py` → `artifacts/conflict.md`).
- [x] Re-runnable test setup (else 60% cap) — `verify/run-all.sh`.
- [x] Held-out testing (else 60% cap) — AI verifier calibration; memory calibration (`calibration.md`) + held-out performance (`performance.md`).
- [~] Both apps run on clean device (else 50% cap) — wheels + debug APK; signed/notarized bundle + clean-install recording still needed (you).
- [x] No misleading readiness number (else FAIL) — `scores.rs` withholds + range/confidence/reasons.
- [x] Traceable AI source (else AI 0) — grounded on flashcards; provenance in tags + footer.
- [x] No leaked test data (else 0) — scanner `verify/leakage.py` → `artifacts/leakage.md` (CLEAN).

## Section 2 — rules

- [x] Real Rust change · [x] two apps one engine · [x] three scores with ranges · [x] give-up rule · [x] AI-off still scores · [x] AGPL + Anki credit.
- [x] Held-out, re-runnable model tests (`verify/run-all.sh`, artifacts in `verify/artifacts/`).
- [x] Study feature tested off/on (interleaving; ablation `verify/ablation.py` → `artifacts/ablation.md`).
- [x] AI beats a simpler method (`verify/goldset.py` → `artifacts/goldset.md`: AI 100% vs vector 60% / keyword 36%).

## Section 7 — concrete challenges

- [x] 7a Rust change + 3 unit tests + 1 Python test + touched-files note.
- [x] 7b Sync: round-trip ok; offline conflict merge `verify/conflict_check.py` (reviews 0 lost / 0 double-counted; converges).
- [x] 7c Coverage vs **official outline** `verify/coverage_map.py` + `speedrun/mcat_outline.tsv` (29/31 = 94%, gaps listed).
- [x] 7d Paraphrase test `verify/paraphrase.py` → `artifacts/paraphrase.md` (~11-pt memory→performance gap).
- [x] 7e Leakage check `verify/leakage.py` → `artifacts/leakage.md` (CLEAN).
- [x] 7f AI gold set (50) + accuracy/wrong-rate + cutoff + baseline `verify/goldset.py` → `artifacts/goldset.md`.
- [x] 7g Crash 20× zero corruption `verify/crash_test.py` → `artifacts/crash.md` (20/20 integrity ok).
- [x] 7h Benchmark on **50k** cards `verify/bench.py --cards 50000` → `artifacts/latency-50k.md` (all p95 under target; ~82 MB).
- [x] §10 prompt-injection defense (hidden text / answer-key override / system-prompt leak) hardened in `qt/aqt/speedrun_ai.py` + `verify/prompt_injection.py` → `artifacts/prompt-injection.md` (all vectors neutralized; benign item survives).

## Section 9 (models) & 10 (speed)

- [x] Step 1 memory calibration (Brier/log-loss + chart) `verify/calibration.py` → `artifacts/calibration.md` (+ `calibration.svg`).
- [x] Step 2 performance on held-out questions `verify/performance_eval.py` → `artifacts/performance.md`.
- [x] Step 3 score mapping written up → `speedrun/models/` (memory/performance/readiness one-pagers).
- [x] Speed p50/p95/worst incl. **50k cards** + cold dashboard load + peak memory (~82 MB) → `artifacts/latency-50k.md`; sync round-trip < 5s in `artifacts/sync.txt`.

## Section 12 — deliverables

- [x] Root `README.md` (MCAT stated up front, build for both apps, architecture, Rust-change note → `RUST-CHANGE.md`, files touched → `TOUCHED-UPSTREAM.md`, AGPL + Anki credit).
- [x] Rust-change one-pager (§7a "why Rust not Python") → `speedrun/RUST-CHANGE.md`.
- [x] Three model-description one-pagers → `speedrun/models/` (memory, performance, readiness).
- [ ] Demo video (you) · [~] Brainlift (research exists; format for repo).

---

_Progress log at the bottom of `JOURNAL.md`._
