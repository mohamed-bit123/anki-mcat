# Speedrun — Repo Navigation Map

Index of where things live in the Anki tree, so we navigate by lookup instead of
re-exploring. Add entries with `path` + a one-line note (and file:line anchors)
as you learn them. Keep it terse.

## Top-level layout (Anki @ b00308e55)

| Path | What it is |
| --- | --- |
| `rslib/` | **Rust backend** — the real engine (scheduling, FSRS, DB, sync). Our Rust change goes here. |
| `rslib/src/` | Rust source root. |
| `rslib/sync/` | Sync implementation (server/client) in Rust. |
| `rslib/proto/`, `rslib/proto_gen/` | Rust-side proto codegen + interface. |
| `proto/anki/*.proto` | **The cross-language contract.** Backend methods/messages. See list below. |
| `pylib/` | Thin Python layer over Rust (`import anki`). |
| `pylib/rsbridge/` | PyO3 wrapper exposing Rust to Python. |
| `pylib/anki/_backend.py` | Auto-exposes snake_case Python methods per protobuf RPC. |
| `qt/aqt/` | PyQt desktop GUI (`import aqt`); embeds web views. |
| `qt/aqt/data/web/` | Built web assets copied from `ts/` at build time. |
| `qt/installer/` | Briefcase installer templates (mac/linux/windows). |
| `ts/` | Svelte/TypeScript frontend (reviewer, deck options, graphs). |
| `ftl/` | Fluent translations. Edit `ftl/core` or `ftl/qt`. Submodules: core-repo, qt-repo. |
| `build/` | Build system (configure / ninja_gen / archives / runner). |
| `justfile` | Task recipes (entrypoint for all build/test/lint). |
| `docs/` | Anki's own dev docs (architecture.md, build.md, development.md, ...). |
| `out/` | **Auto-generated** build outputs; mostly ignore. `out/{pylib/anki,qt/_aqt,ts/lib/generated}` useful for cross-language generated code. |
| `Cargo.toml` / `Cargo.lock` | Rust workspace root (add deps here, use `dep.workspace = true`). |
| `rust-toolchain.toml` | Pins Rust **1.92.0**. |

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

## To locate later (TODO anchors)
- [ ] Where the due/review **queue is built** (for the points-at-stake change).
- [ ] Where **proto services are registered** on the Rust side.
- [ ] Where the **reviewer** calls the backend to fetch/answer cards (qt + ts).
- [ ] Where **undo** is implemented (must prove undo still works after our change).
- [x] How **rsdroid**/`libanki` consumes `rslib` (Android engine sharing, Stage B) —
      DONE; see Mobile section above (`local_backend` → on-disk `.aar`).
