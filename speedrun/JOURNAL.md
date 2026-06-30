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

---

## 2026-06-30 — Stage B DONE: our Rust change runs on the phone (shared engine proven)

Committed Phase 0 desktop work as `74e84d2bc`, then did Stage B.

**How AnkiDroid consumes the engine (discovered):** AnkiDroid pulls `rsdroid` as a
Maven artifact (`io.github.david-allison:anki-android-backend`, version in
`gradle/libs.versions.toml` = `0.1.64-anki25.09.2`). `buildSrc/.../BackendDependencies.kt`
honors `local_backend=true` in AnkiDroid `local.properties`: when set it loads the
on-disk `../Anki-Android-Backend/rsdroid/build/outputs/aar/rsdroid-release.aar`
(+ `rsdroid-testing/build/libs/rsdroid-testing.jar`) instead of Maven. So integration
needs NO version edits — just build the `.aar` next to AnkiDroid and flip the flag.

**Version decision (important).** The backend `.aar` is built from an `anki` git
submodule. AnkiDroid `main` is written against the **anki 25.09.2** backend API
(`0.1.64-anki25.09.2`, an untagged Maven build = backend commit `f9b78ba`). Our
desktop fork is anki **26.05**. To avoid breaking AnkiDroid's `libanki` Kotlin
(API drift), the MOBILE engine is built at **anki 25.09.2** (+ our additive RPC),
while DESKTOP stays at 26.05. Both share `rslib` and carry the same additive
`SpeedrunPing` change, so "one engine" holds. If we ever want a byte-identical
engine version on both, re-anchor the desktop fork to 25.09.2 (cheap: our change is
2 additive files). Tracked as an option, not required.
- Tried backend tag `0.1.63-anki25.09.2` first → AnkiDroid `compileFullDebugKotlin`
  failed: `Unresolved reference 'MAX_INDIVIDUAL_MEDIA_FILE_SIZE'` (a `Backend`
  constant added in 0.1.64). Fix: checkout backend commit `f9b78ba`
  (`VERSION_NAME=0.1.64-anki25.09.2`); same anki submodule pin `3890e12c` (25.09.2),
  so our change stayed applied. Rebuilt → AnkiDroid compiles clean.

**GOTCHA — directory nesting broke the yarn step.** First `./build.sh` failed at
anki's web-asset build: `Unrecognized ... setting: npmMinimalAgeGate` from
`/Users/mohamedshawgi/anki-mcat/.yarnrc.yml`. yarn walks UP the tree and merged our
desktop fork's (26.05) `.yarnrc.yml` into the backend's anki (25.09.2, older yarn
4.6.0) which rejects that key. **Fix: moved the mobile checkouts OUT of the desktop
fork** → `/Users/mohamedshawgi/anki-mcat-mobile/{Anki-Android,Anki-Android-Backend}`
(siblings, as AnkiDroid's `../Anki-Android-Backend` resolver expects). Also had to
`rm -rf anki/out` once (stale ninja graph baked the old absolute path) and re-run
the persistent shell with a valid cwd (the `mv` had pulled the shell's cwd out from
under it → `/bin/zsh ENOENT`).

**Build chain (all via `Anki-Android-Backend/build.sh` = `cargo run -p build_rust`):**
anki `./ninja` web/proto assets → `cargo ndk` cross-compile `rslib` for
`aarch64-linux-android` (arm64 only on M1 by default; `ALL_ARCHS=1` for all) →
robolectric host JNI → `./gradlew assembleRelease rsdroid-testing:build`. Needs
NDK **29.0.14206865** (`sdkmanager "ndk;29.0.14206865"`), rust android targets,
`cargo-ndk@4.1.2` (auto-installed). Backend pins rust **1.89.0** (rustup auto-fetched);
JDK 17/21/25 OK. First full build ~6m20s; incremental rebuilds ~90s.

**Proof our Rust change reaches the phone:**
- `grep -a "speedrun: scheduler engine alive"` ⇒ present in
  `Anki-Android/AnkiDroid/build/outputs/apk/full/debug/AnkiDroid-full-arm64-v8a-debug.apk`
  → `lib/arm64-v8a/librsdroid.so`. (Use `grep -a`, NOT `strings`: the stripped `.so`
  keeps the literal in a section `strings` skips by default → false negative.)
- `.aar` `classes.jar` → `anki/backend/GeneratedBackend` exposes
  `public java.lang.String speedrunPing()` (+ `speedrunPingRaw(byte[])`) — the proto
  change flowed into the Kotlin binding automatically.
- Added a tagged hook in `DeckPicker.onFinishedStartup()`:
  `showSnackbar(CollectionManager.getBackend().speedrunPing())` + `Timber.i("SPEEDRUN …")`.
  APK recompiled clean ⇒ the method is callable from AnkiDroid Kotlin. When the user
  boots the emulator + installs the APK, the deck list shows the engine string and
  it appears in `adb logcat | grep SPEEDRUN`.

**Phase 0 COMPLETE.** Same additive engine change proven on BOTH desktop (Python
`speedrun_ping()`) and mobile (APK `librsdroid.so` + `speedrunPing()` + on-screen).
Next: Phase 1 — the real points-at-stake / weakness-weighted review queue in `rslib`,
applied to both bases.

---

## 2026-06-30 — Phase 1 (desktop): points-at-stake review queue — the REAL change

The real engine change: a weakness-weighted "points at stake" review ordering.

**Where the queue is built (mapped):** `rslib/src/scheduler/queue/builder/`.
Reviews are gathered into `QueueBuilder.review: Vec<DueCard>` by SQL keyed on
`ReviewCardOrder` (`storage/card/mod.rs::review_order_sql`); new cards get an
in-Rust `sort_new()`. `Collection::build_queues` runs gather → `build()`. That's
the seam.

**Design — `rslib/src/speedrun/queue.rs` (pure, reusable):**
`priority = topic_points * urgency * weakness`, where
`urgency = 1 - retrievability` (P you'll fail it now), `weakness = 1 + difficulty`
(hard/lapsed cards count more), `topic_points` = MCAT points on the card's topic
(per-deck via `speedrunTopicPoints` collection config, default 1.0). Higher =
study first. The function is pure so the readiness model can later show the SAME
number as evidence. Feature extraction uses real FSRS retrievability/difficulty
when memory state exists, else interval/overdueness + lapse proxies (works FSRS
on or off).

**Integration:** added `ReviewCardOrder::SpeedrunPointsAtStake` (proto enum value
13, additive). When selected, `build_queues` calls `speedrun_reorder_reviews`,
which loads each gathered review card, computes priority, and stable-sorts desc
(tie-break by card id). Opt-in per deck; default behavior untouched. Two other
exhaustive matches forced arms: `review_order_sql` and the FSRS `simulator`.

**Tests (all green):** 3 pure unit tests (urgency dominates / topic points scale /
weakness breaks ties) + 2 queue-level integration tests (weakness promotes a
less-overdue lapsed card above a more-overdue easy one; high-yield deck via config
ranks first) + 1 Python test (`pylib/tests/test_speedrun.py`) that flips
`reviewOrder` 12↔13 and asserts the queue order changes through proto→Python. All
14 `scheduler::queue` tests still pass (no regressions). `cargo fmt` clean.

**Why Rust (one-liner for the writeup):** ranking the whole due set by a custom
multi-factor priority on every queue build is hot-path work over the card store;
doing it in the shared Rust engine means desktop AND mobile get identical behavior
from one implementation, instead of reimplementing (and drifting) in Python + Kotlin.

Remaining for Phase 1: apply the same change to the mobile backend's anki (25.09.2)
and rebuild the rsdroid .aar + APK so the queue change ships to the phone too.

---

## 2026-06-30 — Phase 1 (mobile): points-at-stake shipped to Android

Applied the identical change to the mobile backend anki (`anki-mcat-mobile/
Anki-Android-Backend/anki`, v25.09.2). Two version deltas vs desktop:
- 25.09.2 has **no** `ReviewCardOrder::RelativeOverdueness` (enum max = 11) and its
  `review_order_sql` uses `build_retrievability_clauses(fsrs, timing, SqlSortOrder)`.
  So the new SQL arm gathers via `build_retrievability_clauses(.., Ascending)`
  (most-forgettable first) instead of the desktop's RelativeOverdueness subclause.
- The simulator's fallback arm is `Added | ReverseAdded => None` (no
  RelativeOverdueness), so the new arm slots in before it.
Used proto value **13** to match desktop, so `reviewOrder = 13` means points-at-stake
on both platforms (mobile leaves 12 unused — proto allows the gap). The `speedrun/`
ranking module was copied over verbatim.

NOTE: host `cargo check` on the mobile tree fails in `rslib/src/sync/*` (async-
compression/tokio trait drift under host rust 1.92) — pre-existing and unrelated to
our code; the Android build pins rust 1.89.0 + the locked deps and builds clean.

Proof on phone:
- `./build.sh` (backend) → **BUILD SUCCESSFUL**; rslib cross-compiled for arm64.
- `grep -a speedrunTopicPoints librsdroid.so` → found (our Phase 1 config key is in
  the native lib), Phase 0 ping string still present.
- Rebuilt APK (`assembleFullDebug`), `adb install -r` the arm64 build, launched via
  `IntentHandler`; DeckPicker logged `SPEEDRUN speedrun: scheduler engine alive
  (anki 25.09.2)` — the rebuilt engine loads and runs on the emulator.

**Phase 1 core (the real engine change) is DONE on desktop AND mobile.** Next:
MCAT review loop on a real deck + the honest memory model (range + give-up rule).

---

## 2026-06-30 — Phase 2 (desktop): the three scores + practice-question loop

Built the three deliberately-separate, honest scores in the engine, plus the
application-question plumbing that feeds them.

**Opinion logged (practice tests vs flashcards):** they're complementary, not
alternatives. Flashcards = Memory (retrieval strength of facts); application
questions = Performance (transfer). Recall ≠ transfer, and the MCAT is an
application exam, so applied questions are *required* to (a) measure Performance
and (b) honestly calibrate Readiness. Readiness is therefore driven by applied
Performance, with Memory as a ceiling factor — memorization alone never yields a
readiness number.

**`rslib/src/speedrun/scores.rs` (pure, 10 tests):**
- Memory = topic-weighted mean FSRS retrievability over *studied* cards + coverage.
- Performance = recency- and topic-weighted accuracy on application questions.
- Readiness = projected MCAT 472–528 via a documented pct→score map, range from a
  Wilson interval (widens with less data) inflated by calibration error, plus a
  confidence level and calibration note.
- Honesty rules enforced in-engine: give-up below min evidence; **Readiness
  refused without Performance**; range widens w/ less data / no calibration; weak
  Memory caps Readiness.

**`rslib/src/speedrun/content.rs` (3 tests):** application questions = notes tagged
`mcat-question`; each graded answer is appended to the question card's
`custom_data` (`spA: [[day, correct]]`, capped 50, syncs for free). Gathering turns
the live collection into score inputs (flashcards→Memory, tagged questions→
Performance; topic = deck, points via the Phase 1 `speedrunTopicPoints` config;
calibration from `speedrunCalibration` config).

**Proto seam:** added `SpeedrunRecordAttempt` + `SpeedrunScores` RPCs (+ a
`SpeedrunScoresResponse` with `known`/`reason` fields so withheld scores stay
explicit). Verified end-to-end in Python (`pylib/tests/test_speedrun_scores.py`):
build flashcards + tagged questions, log attempts via the backend, read all three
scores; readiness is correctly refused when only flashcards exist.

18 Rust speedrun tests + 3 Python tests green. Remaining: mirror Phase 2 onto the
mobile backend, and build the UI — a question runner (take a practice set) and a
scores panel — on desktop (Svelte) and AnkiDroid.

---

## 2026-06-30 — Phase 2 (desktop UI): question runner + score panel

Added the desktop UI in `qt/aqt/speedrun.py` (PyQt, opened via **Tools → MCAT
Speedrun…**). Chose a PyQt dialog over a Svelte page: it runs in the real desktop
app today, talks straight to the same `SpeedrunScores`/`SpeedrunRecordAttempt`
RPCs, and avoids the ts build round-trip I can't visually verify. The Svelte
version can wrap the same RPCs later.

**What it does:**
- Three live score cards (Memory / Performance / Readiness) rendered *honestly* —
  when the engine withholds a score it shows `—` plus the engine's `reason`, not a
  fake number. Readiness shows projected + range (472–528) + confidence +
  calibration note.
- A practice runner: "Start practice set" loads `tag:mcat-question` notes, shows
  the stem + 4 options, grades the pick, records the attempt via the backend, shows
  the explanation, and refreshes all three scores after every answer.

**Notetype + seed:** `ensure_notetype()` creates an "MCAT Practice Question"
notetype (Topic/Stem/A–D/Answer/Explanation); `seed_demo_questions()` adds 12
original, hand-authored MCAT-style discretes so the loop is demoable on an empty
collection. Validated headless (offscreen Qt): seed 12 → scores withheld → 12
answers → Performance known (12 attempts), Readiness 522 (range 509.5–528, low
confidence, "not yet calibrated"). `just build` green; both edited files
py-compile clean.

**Question-bank sourcing (the honest plan):** real AAMC/UWorld/Kaplan banks are
copyrighted — we will NOT scrape or redistribute them. The bank comes from three
legitimate sources: (1) **user import** (the questions are plain notes of our
notetype, so standard Anki CSV/apkg import works, and users can bring content they
own); (2) **AI generation grounded in open-licensed sources** (OpenStax Bio/Chem/
Physics/Psych, CC-BY) with stored citations + a held-out eval — this is the
Phase 3 AI feature and the scalable source; (3) the small hand-authored seed set
for demos. All three produce identical tagged notes, so the runner + scoring are
source-agnostic.
