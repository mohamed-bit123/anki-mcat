# Speedrun — Decision Journal (append-only)

Newest entry at the bottom = current state of the world. Never rewrite past
entries; only append. Each entry: what happened, why, and what's next.

---

## 2026-06-30 — Project kickoff, research review, Anki cloned

**Context / direction confirmed.** Project = "Speedrun": fork Anki, build an
MCAT desktop app + phone companion sharing one Rust engine, with three separate
scores (memory/performance/readiness), a real Rust change, AI with traceable
sources + held-out eval, and a strict honesty/give-up rule. Read the full brief
and confirmed understanding before touching files.

**Owner's research (Brainlift) reviewed.** Strong SPOV: the bottleneck isn't too
much content, it's an unstable memory system; retrieval accessibility (not
content completion or felt confidence) is the best readiness metric. Experts:
Dunlosky, Willingham, Roediger, Karpicke, Bjork. Key usable hooks:
- Bjork storage vs. retrieval strength maps onto FSRS (stability≈storage,
  retrievability≈retrieval) — gives us a cited conceptual bridge to readiness.
- Interleaving research (with the caveat that excessive alternation can hurt) →
  perfect pre-registered, falsifiable study-feature experiment.
- "Order review by how well you remember a topic, not textbook order" → directly
  motivates the points-at-stake Rust queue.
- Flagged gap: research is memory-heavy; need a transfer-of-learning source to
  ground the *performance* model in the Brainlift.

**Owner decisions (locked).**
- Keep FSRS as-is (trusted; don't re-derive spacing).
- Stance: memory directly drives readiness. Reconciled with rubric: that's our
  *model*; we still show ranges + evidence (presentation contract) and still
  measure performance separately to report the gap. No conflict.

**Workspace state.** `/Users/mohamedshawgi/anki-mcat` was empty, not a git repo.
Host: macOS arm64. Present: git 2.44, Python 3.13.0, Node 24.11.1, Homebrew,
Xcode Command Line Tools. Missing (needed later): rustup/cargo, just, JDK +
Android SDK/NDK (AnkiDroid), full Xcode (iOS).

**Action: cloned Anki into the workspace as the fork.**
- `git clone https://github.com/ankitects/anki.git .`
- Upstream HEAD at clone time: **`b00308e551576f5a71593a80f377bc1d28c6612e`**
  ("fix(search): normalize whitespace in search query parser (#4853)").
- Submodules present (not yet inited): `ftl/core-repo`, `ftl/qt-repo`,
  `qt/installer/windows-template`.
- License confirmed AGPL-3.0-or-later (+ BSD-3 portions). Good.

**Learned about the build (from AGENTS.md / docs).**
- Use **`just`** recipes, NOT raw `./ninja` / `./run`. Key: `just run`,
  `just check`, `just test-rust|py|ts`, `cargo check`, `just fmt`/`just lint`.
- Build system (in `build/`) downloads its own node/uv/protoc; we just need
  rustup/cargo (Rust **1.92.0** pinned) + just on the host.
- Proto is the cross-language contract; `pylib/_backend.py` exposes snake_case
  methods per RPC. Confirms the "one Rust method → callable everywhere" seam.

**Set up persistent memory.** Created `speedrun/` with README, PLAN, JOURNAL,
REPO-MAP, TOUCHED-UPSTREAM so context resets don't lose the train of thought.

**Next up (Phase 0):**
1. Install rustup+cargo (1.92.0) and just; `git submodule update --init` for ftl.
2. First desktop build via `just run`; capture clean-build evidence + verify the
   app launches.
3. Then a trivial Rust change visible in desktop (and later phone) to validate
   the pipeline before real features.

---

## 2026-06-30 — Toolchain installed + first desktop build SUCCEEDS

**Toolchain.**
- `rustup` installed via the official script (not brew — see gotcha below).
  Rust **1.92.0** toolchain installed; rustup confirms it's active "because
  overridden by rust-toolchain.toml" in the repo. `cargo 1.92.0`.
- `just` **1.55.1**: brew install was blocked (see gotcha), so I downloaded the
  prebuilt binary to `~/.local/bin/just` (already on PATH).
- `n2` (ninja replacement) **0.1.0**: the first `just build` failed with
  "n2 and ninja missing" — fixed by running `bash tools/install-n2` (which does
  `cargo install --git .../n2 --rev 53ec691...`). Installs to `~/.cargo/bin/n2`.

**GOTCHA — Homebrew is partially broken on this machine.** Several brew lock
files under `/opt/homebrew/var/homebrew/locks/` (e.g. `ca-certificates`,
`certifi`) are owned by a DIFFERENT user account (`mohamedyshawgi`, note the
extra "y"), so `brew install` of anything depending on them fails with
"Permission denied" / a false "Another brew update process is already running".
Workaround: avoid brew for these; use official installers / prebuilt binaries.
(Fix would need sudo chown of those lock files — not done.)

**Submodules.** Inited `ftl/core-repo` + `ftl/qt-repo` (translations, required
for build). `qt/installer/mac-template` + `windows-template` left UNINITED — only
needed later for packaging the installer.

**BUILD SUCCEEDS.** `just build` (= `./ninja pylib qt`) → "Build succeeded in
88.87s" (after deps cached; downloads protoc/uv/node on first run). Commit still
at upstream `b00308e55`, Anki version reports **26.05**.

**Engine verified end-to-end (not just compiled).** Ran a headless check with
the built pyenv:
`PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/python` → `import anki`,
opened an in-memory `Collection`, got scheduler ver **2**, default deck listed,
closed cleanly. Confirms the **rslib ↔ rsbridge ↔ pylib** bridge works. This is
the seam our Rust change will ride.

**Key build/run facts learned (also in REPO-MAP):**
- Built Python venv: `out/pyenv/bin/python`. Generated code lives in
  `out/pylib` + `out/qt`; source in `pylib` + `qt`. Run scripts add all four to
  `sys.path` (see `tools/run.py`).
- `just run` launches the Qt GUI (needs a display — not headless-friendly on the
  agent). For verification prefer `just build` + the headless import above.
- Every build/cargo command needs PATH to include `~/.cargo/bin` and
  `~/.local/bin`; source `$HOME/.cargo/env` first.

**Phase 0 status:** clone ✓, toolchain ✓, desktop build ✓, engine bridge ✓.
**Next:** trivial Rust change (new proto method returning a string) wired through
to Python to validate the full edit→build→call pipeline before the real
points-at-stake queue. Then the Android/rsdroid build.

---

## 2026-06-30 — Trivial Rust change DONE + Android build environment up

**Decision:** mobile target = **Android via AnkiDroid + emulator** (user has an
iPhone but no Android device; emulator runs on the Mac and rubric allows it).
iOS kept as bonus. AnkiDroid runs Anki's real Rust backend (rsdroid), so the
"one shared engine" requirement is satisfied.

**Trivial Rust change (pipeline validation) — WORKS end to end.**
- Added `rpc SpeedrunPing(generic.Empty) returns (generic.String);` to
  `SchedulerService` in `proto/anki/scheduler.proto`.
- Implemented `speedrun_ping()` in
  `rslib/src/scheduler/service/mod.rs` (returns
  "speedrun: scheduler engine alive (anki <ver>)" via `crate::version::version()`).
- `just build` regenerated proto + recompiled in ~11s.
- Verified from Python: `col._backend.speedrun_ping()` →
  `'speedrun: scheduler engine alive (anki 26.05)'`. The edit→proto-regen→
  rebuild→call seam is proven. (Recipe saved in REPO-MAP.md.)
- Logged both edits in TOUCHED-UPSTREAM.md (additive, low merge risk).

**Android toolchain installed (host).**
- JDK 17 (`~/jdk17`) for desktop; **JDK 21** (`~/jdk21`) for AnkiDroid (it
  requires JDK 21–25, Gradle 9.5.0). Temurin tarballs (brew still broken).
- Android SDK at `~/Library/Android/sdk` via cmdline-tools `sdkmanager`:
  platform-tools 37, emulator 36.6.11, platforms;android-35, build-tools;35.0.0,
  system-images;android-35;google_apis;arm64-v8a. NDK deliberately skipped for
  now (only needed to rebuild rsdroid from our fork — Stage B).
- Created AVD **`mcat`** (pixel_6, arm64 google_apis).
- GOTCHA: process tools (`pgrep`/`pkill`) and the `yes|sdkmanager --licenses`
  pipe need to run OUTSIDE the sandbox (required_permissions ["all"]); inside the
  sandbox they hit "sysmond service not found" / SIGPIPE. For licenses use
  `for i in $(seq 1 60); do echo y; done | sdkmanager --licenses`.

**AnkiDroid built from source — APK produced.**
- Cloned `ankidroid/Anki-Android` (shallow) to `mobile/Anki-Android/`
  (git-ignored). Wrote `local.properties` with `sdk.dir`.
- `./gradlew :AnkiDroid:assembleFullDebug` → **BUILD SUCCESSFUL in 4m33s**.
  Flavors: play(default)/amazon/**full**. Output APKs at
  `AnkiDroid/build/outputs/apk/full/debug/` (per-ABI splits). The
  `AnkiDroid-full-arm64-v8a-debug.apk` (69MB) matches the emulator.
- NOTE: this APK uses the STOCK rsdroid backend from Maven — real Anki engine,
  but NOT yet our Rust change. Shipping our change to the phone = Stage B
  (rebuild rsdroid from fork w/ NDK).

**Emulator headless boot = flaky here.** The emulator initializes graphics
(Vulkan/SwiftShader) and starts its gRPC server, but the `-no-window` process
dies before adb sees a device (tried twice). Not worth chasing from automation —
the USER boots it WITH a window on their Mac (reliable). Build pipeline (the hard
part) is proven; booting is a UI concern. Wrote `speedrun/HOWTO-RUN.md` with
exact desktop + emulator run/install/test commands.

**Phase 0 status now:** desktop build ✓, engine bridge ✓, trivial Rust change ✓
(desktop), Android env ✓, AnkiDroid APK builds ✓. Remaining Phase 0: Stage B
(rebuild rsdroid from fork so our Rust change runs on the phone) — needs NDK +
rust android targets. Then start the real points-at-stake queue (Phase 1).
