# Requirements audit — living checklist

Maps every requirement in the Speedrun brief to its status in this repo, with
evidence. `[x]` met · `[~]` partial · `[ ]` missing. Update as items land.

Exam: **MCAT** (472–528, four 118–132 sections). AI off = fully functional.

## Hard limits (grade gates)

- [x] Real Rust change (else 50% cap) — `rslib/src/speedrun/queue.rs` (points-at-stake + interleave), proto enum + RPCs, called from Python/Kotlin.
- [~] Phone shares engine + syncs (else 70% cap) — shared `rslib`; round-trip verified (`verify/artifacts/sync.txt`); offline **conflict** rule (7b) → see `verify/conflict_check.py`.
- [x] Re-runnable test setup (else 60% cap) — `verify/run-all.sh`.
- [~] Held-out testing (else 60% cap) — AI verifier calibration done; memory calibration + held-out performance → see `verify/calibration.py`, `verify/performance_eval.py`.
- [~] Both apps run on clean device (else 50% cap) — wheels + debug APK; signed/notarized bundle + clean-install recording still needed (you).
- [x] No misleading readiness number (else FAIL) — `scores.rs` withholds + range/confidence/reasons.
- [x] Traceable AI source (else AI 0) — grounded on flashcards; provenance in tags + footer.
- [~] No leaked test data (else 0) — scanner → `verify/leakage.py`.

## Section 2 — rules

- [x] Real Rust change · [x] two apps one engine · [x] three scores with ranges · [x] give-up rule · [x] AI-off still scores · [x] AGPL + Anki credit.
- [~] Held-out, re-runnable model tests.
- [~] Study feature tested off/on (interleaving implemented; ablation → `verify/ablation.py`).
- [~] AI beats a simpler method (baseline → `verify/goldset.py`).

## Section 7 — concrete challenges

- [x] 7a Rust change + 3 unit tests + 1 Python test + touched-files note.
- [~] 7b Sync: round-trip ok; offline conflict → `verify/conflict_check.py`.
- [~] 7c Coverage vs **official outline** → `verify/coverage_map.py` + `speedrun/mcat_outline.tsv`.
- [ ] 7d Paraphrase test → `verify/paraphrase.py`.
- [ ] 7e Leakage check → `verify/leakage.py`.
- [ ] 7f AI gold set (50) + 3 counts + cutoff + baseline → `verify/goldset.py`.
- [ ] 7g Crash 20× zero corruption → `verify/crash_test.py`.
- [~] 7h Benchmark on **50k** cards → `verify/bench.py --cards 50000`.

## Section 9 (models) & 10 (speed)

- [ ] Step 1 memory calibration (Brier/log-loss + chart) → `verify/calibration.py`.
- [ ] Step 2 performance on held-out questions → `verify/performance_eval.py`.
- [~] Step 3 score mapping written up → `speedrun/models/`.
- [~] Speed p50/p95/worst (add 50k + cold-start/memory/sync).

## Section 12 — deliverables

- [~] Root `README.md` (exam/architecture/Rust note up front).
- [ ] Three model-description one-pagers → `speedrun/models/`.
- [ ] Demo video (you) · [~] Brainlift (research exists; format for repo).

---

_Progress log at the bottom of `JOURNAL.md`._
