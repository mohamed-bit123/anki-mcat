# Speedrun — Repo Navigation Map

Index of where things live in the Anki tree, so we navigate by lookup instead of
re-exploring. Add entries with `path` + a one-line note (and file:line anchors)
as you learn them. Keep it terse.

## Top-level layout (Anki @ b00308e55)

| Path                               | What it is                                                                                                                             |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `rslib/`                           | **Rust backend** — the real engine (scheduling, FSRS, DB, sync). Our Rust change goes here.                                            |
| `rslib/src/`                       | Rust source root.                                                                                                                      |
| `rslib/sync/`                      | Sync implementation (server/client) in Rust.                                                                                           |
| `rslib/proto/`, `rslib/proto_gen/` | Rust-side proto codegen + interface.                                                                                                   |
| `proto/anki/*.proto`               | **The cross-language contract.** Backend methods/messages. See list below.                                                             |
| `pylib/`                           | Thin Python layer over Rust (`import anki`).                                                                                           |
| `pylib/rsbridge/`                  | PyO3 wrapper exposing Rust to Python.                                                                                                  |
| `pylib/anki/_backend.py`           | Auto-exposes snake_case Python methods per protobuf RPC.                                                                               |
| `qt/aqt/`                          | PyQt desktop GUI (`import aqt`); embeds web views.                                                                                     |
| `qt/aqt/data/web/`                 | Built web assets copied from `ts/` at build time.                                                                                      |
| `qt/installer/`                    | Briefcase installer templates (mac/linux/windows).                                                                                     |
| `ts/`                              | Svelte/TypeScript frontend (reviewer, deck options, graphs).                                                                           |
| `ftl/`                             | Fluent translations. Edit `ftl/core` or `ftl/qt`. Submodules: core-repo, qt-repo.                                                      |
| `build/`                           | Build system (configure / ninja_gen / archives / runner).                                                                              |
| `justfile`                         | Task recipes (entrypoint for all build/test/lint).                                                                                     |
| `docs/`                            | Anki's own dev docs (architecture.md, build.md, development.md, ...).                                                                  |
| `out/`                             | **Auto-generated** build outputs; mostly ignore. `out/{pylib/anki,qt/_aqt,ts/lib/generated}` useful for cross-language generated code. |
| `Cargo.toml` / `Cargo.lock`        | Rust workspace root (add deps here, use `dep.workspace = true`).                                                                       |
| `rust-toolchain.toml`              | Pins Rust **1.92.0**.                                                                                                                  |

## proto/anki/ messages (the API surface)

`backend.proto`, `scheduler.proto` (scheduling/queue — relevant to our Rust
change), `cards.proto`, `collection.proto`, `config.proto`, `deck_config.proto`,
`decks.proto`, `notes.proto`, `notetypes.proto`, `search.proto`, `stats.proto`,
`sync.proto`, `tags.proto`, `card_rendering.proto`, `frontend.proto`,
`generic.proto`, `i18n.proto`, `image_occlusion.proto`, `import_export.proto`,
`links.proto`, `media.proto`, `ankidroid.proto`, `ankihub.proto`,
`ankiweb.proto`, `github.proto`.

> Our new API will live in a dedicated `proto/anki/speedrun.proto` (TBD) to keep
> a thin seam and easy upstream merges.

## Build / run facts (verified 2026-06-30)

- Host prereqs: `rustup`+`cargo` (Rust **1.92.0**, auto-selected via
  `rust-toolchain.toml`), `just`, and `n2` (`bash tools/install-n2`). Build
  downloads its own node/uv/protoc into `out/extracted/`.
- Always: `. "$HOME/.cargo/env"; export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"`.
- `just build` = `./ninja pylib qt`; first clean build ~89s here. Anki ver 26.05.
- Built Python venv: **`out/pyenv/bin/python`**.
- To run python against the built engine headlessly:
  `PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/python`. Generated code
  (buildinfo, proto, rsbridge) is in `out/pylib`/`out/qt`; source in `pylib`/`qt`
  (`tools/run.py` adds all four to sys.path).
- `just run` launches the Qt GUI (needs a display; not headless-friendly).

## Conventions (from AGENTS.md)

- Rust errors in rslib: `error/mod.rs` `AnkiError`/`Result` + `snafu`. Elsewhere:
  `anyhow` + context. Unwrapping in build scripts/tests is fine.
- Use `rslib/{process,io}` helpers for file/process ops.
- Rust deps: add to root workspace, `dep.workspace = true` in the crate.

## How to add a backend RPC (verified — the trivial-change recipe)

1. Add `rpc Foo(generic.Empty) returns (generic.String);` to the relevant
   service in `proto/anki/<area>.proto` (e.g. `SchedulerService` in
   `scheduler.proto`). `generic.Empty` input ⇒ the Rust method takes no arg.
2. Implement the snake_case method in the Rust impl of that service trait, e.g.
   `rslib/src/scheduler/service/mod.rs` →
   `impl crate::services::SchedulerService for Collection { fn foo(&mut self)
   -> Result<generic::String> {...} }`. `String -> generic::String` via `.into()`.
3. `just build` regenerates proto + recompiles (incremental ~11s here).
4. Call from Python: `col._backend.foo()` (auto-exposed, returns the unwrapped
   `str` for `generic.String`).

- The trait `crate::services::SchedulerService` is generated from the proto;
  adding an rpc makes the method REQUIRED, so the compiler enforces the impl.
- `crate::version::version()` returns the Anki version string ("26.05").

## Mobile (AnkiDroid + rsdroid) — location + facts

- **Lives OUTSIDE this repo** at `/Users/mohamedshawgi/anki-mcat-mobile/` as two
  sibling checkouts (moved out of `anki-mcat/` to avoid a `.yarnrc.yml` config-bleed
  build break — see JOURNAL 2026-06-30 Stage B):
  - `Anki-Android/` — the app. Task `:AnkiDroid:assembleFullDebug`
    (flavors play(default)/amazon/**full**). Needs **JDK 21–25** (Gradle 9.5.0).
    APK: `AnkiDroid/build/outputs/apk/full/debug/AnkiDroid-full-arm64-v8a-debug.apk`.
  - `Anki-Android-Backend/` — builds `rsdroid` (the JNI backend `.aar`) from an
    `anki` git submodule. Checked out at `f9b78ba` = `0.1.64-anki25.09.2`; submodule
    pinned at anki `3890e12c` (**25.09.2**) + our additive `SpeedrunPing`.
- **How AnkiDroid loads the engine:** `buildSrc/.../BackendDependencies.kt` →
  `local_backend=true` in `Anki-Android/local.properties` makes it use the on-disk
  `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`
  (+ `rsdroid-testing/build/libs/rsdroid-testing.jar`); else the Maven artifact
  `io.github.david-allison:anki-android-backend:<ver>` (catalog `ankiBackend`).
- **Backend build** (`Anki-Android-Backend/build.sh` = `cargo run -p build_rust`):
  anki `./ninja` web/proto assets → `cargo ndk` cross-compile `rslib` (arm64 only on
  M1; `ALL_ARCHS=1` = all 4 ABIs) → robolectric host JNI → `./gradlew assembleRelease`.
  Needs NDK **29.0.14206865**, JDK 17, rust 1.89.0 (backend-pinned, auto-fetched),
  `cargo-ndk@4.1.2` (auto-installed). First build ~6m, incremental ~90s.
- **Generated binding:** adding the RPC to the proto auto-produces
  `anki/backend/GeneratedBackend.speedrunPing(): String` in the `.aar` — call via
  `CollectionManager.getBackend().speedrunPing()` from AnkiDroid Kotlin.
- **Verify a `.so` contains an engine change:** `grep -a "<literal>" librsdroid.so`
  (NOT `strings`, which skips sections in the stripped lib → false negatives).
- DESKTOP engine = anki 26.05; MOBILE engine = anki 25.09.2 (kept apart so
  AnkiDroid's `libanki` Kotlin compiles against its expected API). Same additive
  change on both. Re-anchor desktop to 25.09.2 if a byte-identical engine is wanted.

## Android SDK (installed)

- `ANDROID_HOME=$HOME/Library/Android/sdk`. Packages: platform-tools 37,
  emulator 36.6.11, platforms;android-35, build-tools;35.0.0,
  system-images;android-35;google_apis;arm64-v8a. AVD named **`mcat`**.

## Review queue building (Phase 1 seam — FOUND)

- Builder: `rslib/src/scheduler/queue/builder/mod.rs`. `Collection::build_queues`
  = `QueueBuilder::new` → `gather_cards` → `build(learn_ahead_secs)`.
- Reviews land in `QueueBuilder.review: Vec<DueCard>` (`builder/mod.rs`), gathered
  by SQL via `gather_due_cards` (`builder/gathering.rs`) using `ReviewCardOrder`.
- The review-order → SQL mapping: `rslib/src/storage/card/mod.rs::review_order_sql`.
  New-card sort (in Rust) lives in `builder/sorting.rs` (`sort_new`); there is no
  default in-Rust review sort — reviews are pre-ordered by SQL.
- `DueCard` fields: id, note_id, mtime, due, current_deck_id, original_deck_id,
  kind, reps. Full memory state (stability/difficulty, lapses, decay) only on the
  full `Card` (load via `col.storage.get_card`).
- FSRS current retrievability in Rust: `fsrs::FSRS::new(None).current_retrievability_seconds(state.into(), card.seconds_since_last_review(&timing), card.decay.unwrap_or(FSRS5_DEFAULT_DECAY))` (pattern from `stats/graphs/retrievability.rs`).
- OUR change: `ReviewCardOrder::SpeedrunPointsAtStake` (proto `deck_config.proto`,
  value 13) + `Collection::speedrun_reorder_reviews` in `build_queues` + pure logic
  in `rslib/src/speedrun/queue.rs`. Other exhaustive matches that need an arm when
  adding a `ReviewCardOrder`: `review_order_sql` and `scheduler/fsrs/simulator.rs`.
- Deck config dict key for the order (Python/legacy JSON): `reviewOrder` (int).
- Topic **interleaving**: `interleave_order` in `rslib/src/speedrun/queue.rs` runs
  inside `speedrun_reorder_reviews` AFTER points-at-stake scoring — mixes topics
  (by `current_deck_id`) so no two consecutive reviews share a subject while others
  remain, keeping highest-priority first. Pure fn, 3 unit tests.
- Built-in **MCAT flashcards**: `rslib/src/speedrun/seed.rs` — 56 original cards over
  7 subjects, `Collection::speedrun_seed_builtin` (idempotent, tag `mcat-flashcard`)
  creates `MCAT::<Topic>` subdecks, sets the `MCAT` deck to points-at-stake review
  order + `RANDOM_CARDS` new-card gather, seeds high-yield `speedrunTopicPoints`.
  RPC `SpeedrunSeedBuiltin` (`generic.UInt32`); binding `speedrunSeedBuiltin(): Int`
  (Kotlin) / auto-unwrapped int (Python). UI buttons "Set up MCAT flashcards" on both.
- **Concept-level FSRS for questions**: `rslib/src/speedrun/concepts.rs` — per-concept
  FSRS `MemoryState` in config map `speedrunConcepts` (key = lowercased deck leaf).
  `Collection::speedrun_next_question` picks the most-due concept (urgency 1-R × MCAT
  yield, urgency floor + `/(1+times_today)` for within-day rotation) then its least-
  recently-seen item; `speedrun_update_concept` advances state on each attempt (called
  from `content.rs::speedrun_record_attempt`). Daily band consts `RECOMMENDED_DAILY_MIN`
  /`_MAX`. RPC `SpeedrunNextQuestion` → `SpeedrunNextQuestionResponse`; binding
  `speedrunNextQuestion()`. Drives the open-ended one-at-a-time runner in
  `qt/aqt/speedrun.py` (`load_next_question`) and `SpeedrunActivity.kt` (`loadNextQuestion`).
  FSRS gotcha: build with `FSRS::new(Some(&[]))` (default params) — `None` makes
  `next_states` panic. 5 concept-related unit tests.
- **AI question generation (desktop)**: `qt/aqt/speedrun_ai.py` — grounded generation +
  independent verifier + note insertion; UI in `qt/aqt/speedrun.py` ("Generate with AI"
  button, `GenerateDialog`, auto top-up in `_maybe_autogen`/`load_next_question`). Pure
  Python (no engine/proto change). Grounds on built-in flashcards
  (`source_facts(col, topic)`), dedups vs `existing_stems`, inserts standard
  `mcat-question`+`mcat-ai` notes into `MCAT Practice::<topic>` so the concept-FSRS scheduler
  - scores pick them up. Provenance = tags + Explanation footer (NOT `custom_data`; Anki caps
    it at 100 bytes, used by attempt log `spA`). Key from `OPENAI_API_KEY` or local profile —
    never committed. Held-out eval harness: `speedrun/ai_eval.py` (verifier calibration +
    generation pass rate; stdlib-only, reads bundled TSVs). Mobile gets AI questions via normal
    collection sync (no on-device key).

## To locate later (TODO anchors)

- [ ] Where **proto services are registered** on the Rust side.
- [ ] Where the **reviewer** calls the backend to fetch/answer cards (qt + ts).
- [ ] Where **undo** is implemented (must prove undo still works after our change).
- [x] How **rsdroid**/`libanki` consumes `rslib` (Android engine sharing, Stage B) —
      DONE; see Mobile section above (`local_backend` → on-disk `.aar`).
