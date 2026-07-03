# Speedrun — Master Plan

_Last meaningful update: 2026-06-30 (Phase 0 just starting; Anki cloned)._

## 0. Mission (the non-negotiables)

Build an MCAT prep app on a fork of Anki:

- **Two apps, one engine.** Desktop (Anki/Qt) + phone companion (AnkiDroid /
  iOS-FFI), both running the **same Rust backend** (`rslib`). They sync.
- **Three separate scores**, each with a range (never one blended number):
  - **Memory** — P(recall a taught fact now). FSRS already does this well.
  - **Performance** — P(correct on a _new, unseen_ exam-style question).
  - **Readiness** — projected MCAT score (472–528 scale) + range + confidence.
- **A real change in Anki's Rust code** (not just Python/Qt screens).
- **The honesty rule.** No readiness number unless we also show: the evidence,
  what data is missing, how accurate past predictions were, the likely range,
  and the single best next thing to study.
- **The give-up rule.** The app refuses to score without enough data. Our line
  (draft, revisit): _no readiness score until ≥200 graded reviews AND ≥50% topic
  coverage of the MCAT outline._
- **Held-out, re-runnable evaluation** for every model + AI output.
- **AGPL-3.0-or-later**, credit Anki (some parts BSD-3-Clause).
- Fabricated/misleading readiness numbers = **automatic fail**. Leaked test data
  = that score is **zero**. Untraceable AI = AI section is **zero**.

## 1. Exam: **MCAT** (locked)

- Total **472–528**; four sections each **118–132**.
- Huge fact base + reading passages. The hard part is **coverage** of the whole
  outline. A 10k-card deck that skips a high-weight section must NOT show "ready".

## 2. Locked decisions (owner: Mohamed)

- **FSRS stays as-is** for spacing/memory. We do not re-derive optimal gaps.
- **Stance: memory strongly drives readiness** (Willingham/Roediger/Bjork). We
  build the readiness model with topic mastery (memory) as the dominant input.
  This is allowed by the rubric — the automatic-fail is only for _fabricated_
  numbers with no evidence/uncertainty. So: memory→readiness is our _model_;
  "show the range + evidence" is the _presentation contract_. We satisfy both.
  We STILL measure performance separately (paraphrase test) so we can honestly
  **report the memory→performance gap** — finding the gap is small is a valid,
  strong result.
- **Rust change = points-at-stake / weakness-weighted review queue.** New review
  ordering = topic weight × student weakness, with interleaving. This is the SPOV
  ("order review by memory strength + value, interleave topics") implemented in
  the engine. New protobuf message, called from Python; ships to phone too.
- **Tested study feature = interleaving.** Pre-registered hypothesis:
  _"Interleaving related MCAT topics within a review session raises accuracy on
  new, mixed-topic questions, at equal study time, vs. blocked review."_
  Failure mode baked in (our own research says excessive alternation can hurt):
  "no difference / hurts at this alternation rate" is a real, gradeable result.

## 3. Anki architecture (how one engine powers two apps)

- `rslib/` — **Rust backend** (scheduling, FSRS, DB/collection, sync). The real
  engine; our Rust change lives here.
- `proto/anki/*.proto` — **the contract.** Every backend method callable by
  Python/TS/mobile is defined here. **This is our key seam: one new Rust method
  behind a new proto message becomes callable from desktop AND mobile.**
- `pylib/` — thin Python layer; `pylib/rsbridge` wraps Rust via PyO3.
- `qt/aqt/` — PyQt desktop GUI (embeds web views).
- `ts/` — Svelte/TS for reviewer, deck options, graphs (built into qt web).
- Mobile: **AnkiDroid** (Kotlin) runs `rslib` via `rsdroid` (JNI). iOS runs
  `rslib` via its C FFI. Sharing the engine this way is required; rewriting the
  scheduler in JS/Swift does NOT count.

## 4. Build commands (from AGENTS.md — use `just`, not raw ninja/run)

- Run desktop dev: `just run` (web views at http://localhost:40000/_anki/pages/)
- Build + all checks: `just check` (do before marking work done)
- Tests: `just test-rust`, `just test-py`, `just test-ts`, `just test-e2e`
- Fast Rust check: `cargo check`
- Format/lint: `just fmt`, `just fix-fmt`, `just lint`, `just fix-lint`
- Rust pinned to **1.92.0** (`rust-toolchain.toml`). Build downloads its own
  node/uv/protoc. Host prereqs we still need: **rustup/cargo** and **just**.

## 5. Phased plan (ordered to match deadlines)

### Phase 0 — Foundation (DO FIRST; teams die here)

- [x] Fork/clone Anki into workspace (HEAD recorded in JOURNAL).
- [x] Install host prereqs (rustup+cargo 1.92.0, just, n2), init ftl submodules.
- [x] Build desktop from source (`just build` ~89s); engine bridge verified.
- [x] Trivial Rust change surfacing in desktop (proves edit→build→call pipeline
      before investing in the real queue feature). `col._backend.speedrun_ping()`.
- [x] Build Rust backend for Android (`rsdroid`) from OUR fork + AnkiDroid loads it
      (`local_backend=true` → on-disk `.aar`). Needed NDK 29 + rust android targets.
- [x] Trivial Rust change surfacing on the phone too (shared-engine proof): our
      string is inside the APK's `librsdroid.so`, the generated
      `GeneratedBackend.speedrunPing()` Kotlin binding exists, and a tagged hook in
      `DeckPicker` shows it as a snackbar + `SPEEDRUN` logcat line. **PHASE 0 DONE.**

- [x] Real Rust change: points-at-stake/weakness-weighted queue. **DESKTOP +
      MOBILE DONE.** New `ReviewCardOrder::SpeedrunPointsAtStake` (proto enum,
      additive) + pure ranking module `rslib/src/speedrun/queue.rs` + reorder
      wired into the queue builder. 5 Rust tests (3 pure unit + 2 queue-level) +
      1 Python test, all green; existing queue tests still pass (undo-safe,
      opt-in, default behavior unchanged). Same change applied to mobile anki
      25.09.2 (SQL/sim arms adapted to that version); rsdroid `.aar` rebuilt,
      `speedrunTopicPoints` verified in `librsdroid.so`, APK reinstalled and the
      engine confirmed running on the emulator.

### Phase 1 — Wednesday (core, NO AI) — remaining

- [ ] MCAT review loop on a real deck.
- [ ] Memory model w/ honest display: range + give-up rule.
- [ ] Desktop installer runs on a clean machine.
- [ ] Phone builds/runs, loads MCAT deck, runs a real review on shared engine
      (two-way sync NOT required yet).
- Proof: commit hash, clean-build recording, test results, clean-install
  recording, phone review-session screen recording.

### Phase 2 — Friday (AI + sync)

- [ ] Two-way sync desktop<->phone (use Anki's sync; document conflict rule).
- [ ] Offline review then sync on reconnect.
- [ ] AI card generation + checker: traceable source, held-out eval
      (accuracy + wrong-answer rate + cutoff), beats keyword/vector baseline.
- [ ] App still scores with AI OFF.
- [ ] Phone shows all three scores with ranges + give-up rule.
- Proof: eval numbers + baseline comparison + phone→desktop sync recording.

### Phase 3 — Sunday (prove it + ship)

- [ ] Memory calibration: calibration chart + Brier/log-loss on held-out reviews.
- [ ] Performance model: accuracy on held-out exam-style questions.
- [ ] Score mapping written down, with a range.
- [ ] Interleaving experiment: 3 builds (full / ablation / plain Anki), equal
      study time, pre-registered metric, report null results.
- [ ] Leakage check (clean), crash×20 (zero corruption), `make bench` (p50/p95/
      worst), coverage map, paraphrase test (report gap), AI gold-set (50 Q&A).
- [ ] Signed desktop installer + phone build (signed APK / TestFlight/sideload).
- [ ] Both apps run with AI off and still score.
- Deliverables: public AGPL fork w/ Anki credit, exam stated up front, build
  instructions (both apps), architecture overview, Rust-change note,
  touched-files list, 3–5 min demo video, model descriptions (1 page each),
  Brainlift.

## 6. Specific challenges checklist (section 7 of brief)

- 7a Rust change (queue) + 3 Rust tests + 1 Python test + undo proof + why-Rust
  note + touched-files + works on phone.
- 7b Sync test: 10 offline phone + 10 offline desktop → merge all 20, none lost/
  double. Same card on both offline → conflict rule picks clear winner (written).
- 7c Coverage map: every MCAT outline topic, mark covered, % on dashboard,
  abstain below line.
- 7d Paraphrase test: 30 cards × 2 reworded Qs; compare recall vs reworded
  accuracy; report the gap (proves performance ≠ memory copy).
- 7e Leakage check script: flag any test item / near-copy in training; show clean.
- 7f AI card check: 50-pair gold set; generate 50 cards from one real source;
  report correct+useful / wrong / correct-but-bad-teaching; pre-set cutoff;
  block failures.
- 7g Crash×20 (zero corruption) + pull-network (AI off cleanly, app still scores).
- 7h `make bench`: load shared 50k deck; print p50/p95/worst per action.

## 7. Speed/reliability targets (report p50/p95/worst)

- Button press ack p95 < 50ms (desktop+phone).
- Next card after grading p95 < 100ms.
- Dashboard first load p95 < 1s; refresh p95 < 500ms (no UI freeze).
- Normal-session sync < 5s on normal connection.
- Memory on 50k cards under a stated limit (desktop + mid-range phone).
- Cold start < 5s desktop / < 4s phone. Never freeze UI > 100ms.
- Zero corrupted collections in crash test, both platforms.

## 8. Context-window / big-codebase strategy (why we can finish)

1. **Isolate our code** in owned modules (e.g. `rslib/src/speedrun/`,
   `proto/anki/speedrun.proto`, a dedicated Python module, a Svelte dashboard
   component). ~80% of work lives in files we authored & fully understand.
2. **Thin seams into upstream**: touch upstream only at registration points
   (register proto service, hook queue builder, add one menu entry). Fewer edits
   = smaller context footprint AND easier future merges (a graded deliverable).
3. **Durable memory docs** (this `speedrun/` folder) survive context resets.
4. **Navigate by index** (`REPO-MAP.md`) + targeted grep/semantic search; never
   bulk-read. Delegate broad "where is X" exploration to `explore` subagents so
   their context burns instead of ours.
5. **Tests + proto as the contract**: once a module has passing tests, trust the
   tests instead of re-reading internals.
6. **Layered build order** (Rust → proto → Python → UI → mobile), each layer
   independently testable; never hold the whole system in context at once.

## 9. Open questions / risks to revisit

- Exact MCAT deck source + license; coverage-map data source (official outline).
- Mobile path: AnkiDroid+rsdroid (Android, faster) first; iOS-FFI if time.
- Need a transfer-of-learning citation for the _performance_ model (Brainlift).
- Confirm conflict-resolution rule wording for sync (last-writer? higher-grade?).
- `make bench` harness + a synthetic 50k-card MCAT deck generator.
