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
  ground the _performance_ model in the Brainlift.

**Owner decisions (locked).**

- Keep FSRS as-is (trusted; don't re-derive spacing).
- Stance: memory directly drives readiness. Reconciled with rubric: that's our
  _model_; we still show ranges + evidence (presentation contract) and still
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
application exam, so applied questions are _required_ to (a) measure Performance
and (b) honestly calibrate Readiness. Readiness is therefore driven by applied
Performance, with Memory as a ceiling factor — memorization alone never yields a
readiness number.

**`rslib/src/speedrun/scores.rs` (pure, 10 tests):**

- Memory = topic-weighted mean FSRS retrievability over _studied_ cards + coverage.
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

- Three live score cards (Memory / Performance / Readiness) rendered _honestly_ —
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

---

## 2026-06-30 — Phase 2: weakness-weighted question selection

The practice runner originally just `random.shuffle`d questions — it ignored the
points-at-stake idea entirely. Fixed that by giving questions their own
weakness-weighted ranking, the application-question analogue of the Phase 1 review
queue. They can't reuse `points_at_stake` directly (questions are New cards with no
FSRS state), so they rank on _applied accuracy_ instead of retrievability.

**`question_priority` (new pure fn in `rslib/src/speedrun/queue.rs`, 6 new tests):**
`priority = topic_points × topic_weakness × need`, where

- `topic_weakness = 1 − smoothed_topic_accuracy` (floored at 0.1 so mastered
  topics still get occasional coverage),
- `smoothed_accuracy` uses a Bayesian prior (mean 0.6, strength 4) so one lucky/
  unlucky answer can't declare a topic mastered or hopeless,
- `need` = 1.0 for an unseen question, else `0.6·(1−question_accuracy) + 0.4·spacing`
  (spacing saturates at 14 days) — favors unseen, recently-missed, and stale.

**Engine method `Collection::speedrun_next_questions`** (`content.rs`, +1 test):
two passes over tagged questions — accumulate per-topic correct/total, then score
each question — sorted desc (card-id tiebreak for determinism). Exposed via a new
`SpeedrunNextQuestions` RPC (single-field response → Anki auto-unwraps it to the
repeated list on the Python side).

**UI:** seed questions now live in per-topic subdecks (`MCAT Practice::<Topic>`) so
the engine's deck=topic weighting actually differentiates them. Added a
"Weakness-weighted order (points at stake)" checkbox (default on; off = random for
the prove-yourself-wrong comparison) and the runner shows each question's priority.

**Proof (headless):** seed 12 → all unseen at priority 0.40 → master the top
question (4 correct) → it drops from rank 1 to **last (11/11)** and a fresh topic
surfaces. 23 Rust speedrun tests green; `just build` green.

---

## 2026-06-30 — Phase 2 (mobile): full parity on Android

Goal from the user: "make the mobile version just like the desktop one." Done —
all of Phase 2 (the three scores + practice runner + weakness-weighted ordering)
now runs on AnkiDroid through the same shared engine.

**Engine port (backend `anki` submodule @ 25.09.2):** copied `speedrun/{mod,queue,
scores,content}.rs` **byte-identical** to desktop (verified by diff; the Phase-1
`queue.rs` was already identical apart from the Phase-2 additions). Added the three
RPCs (`SpeedrunRecordAttempt`, `SpeedrunScores`, `SpeedrunNextQuestions`) + messages
to `scheduler.proto` and their impls to `scheduler/service/mod.rs`. All Phase-2 APIs
(`search_cards`, `validate_custom_data`, `update_cards_maybe_undoable`,
`get_config_default`, `human_name`, …) exist in 25.09.2, so no adaptation was needed
(unlike Phase 1's `review_order_sql`). `./build.sh` → **BUILD SUCCESSFUL**; the
generated `GeneratedBackend.kt` now exposes `speedrunRecordAttempt(cardId, correct)`,
`speedrunScores(): SpeedrunScoresResponse`, and `speedrunNextQuestions():
List<…Question>` (single-field response auto-unwrapped, exactly like Python).

**AnkiDroid UI — new `SpeedrunActivity.kt`** (programmatic views, mirrors
`qt/aqt/speedrun.py`): three honest score cards, a "Weakness-weighted order" toggle,
seed button, and the question runner (stem + 4 options → grade → record attempt →
explanation → refresh scores). Creates the same "MCAT Practice Question" notetype and
the same 12 hand-authored seed questions in per-topic subdecks via the libanki
Kotlin API (`notetypes.new/newField/addField/newTemplate/add_template/add`,
`col.newNote/addNote`, `decks.id`, `note.setItem/addTag`). Reached via a new
"MCAT Speedrun" item in the DeckPicker overflow menu (`onOptionsItemSelected` →
`startActivity`), registered in `AndroidManifest.xml`.

**Proof (on the running emulator, driven via adb/uiautomator):**

- Opened the screen → 3 scores all **withheld with the engine's honest reasons**
  ("need 20 studied cards", "need 10 graded questions", "no applied evidence yet").
- Seeded 12 → started a set → first question shows **`priority 0.40`, Biochemistry
  first — identical to the desktop headless ranking**.
- Answered a question → feedback "Correct." + explanation; Performance went 0 → 1.
- Answered the full set (12 attempts) → **Performance flips to known: `16/100,
  7 topics`** (2/12 correct since I tapped "A" each time) and **Readiness projects
  `477`, range `472–492`, low confidence, "not yet calibrated"** — while **Memory
  stays withheld** (no studied flashcards). The honesty rules hold on-device.

Mobile now matches desktop. The same engine change + scores + ordering + honesty
rules ship on BOTH platforms. (APK: `AnkiDroid-full-arm64-v8a-debug.apk`, installed
on AVD `mcat`; entry point Tools-style overflow → "MCAT Speedrun".)

---

## 2026-07-01 — Built-in MCAT flashcards + topic interleaving (desktop + mobile)

**Direction.** Make this a self-contained MCAT app: ship built-in flashcards for
every MCAT subject, and have the flashcard _spacing methodology_ interleave topics
(pull from all subjects at once) on top of the existing memory-based points-at-stake
selection. Anki/FSRS is purely time-based, so interleaving is a scheduling/order
concern, not an FSRS change.

**Interleaving (real engine change, shared `rslib`).** New pure fn
`interleave_order` in `speedrun/queue.rs` (+3 tests): given each card's topic (deck)
and its `points_at_stake` priority, it emits the global-highest-priority card first,
then always the highest-priority card whose topic differs from the one just shown,
falling back to same-topic only when no other topic has cards left. Single-topic
input degenerates to plain priority-desc. Wired into `speedrun_reorder_reviews`
(`scheduler/queue/builder/mod.rs`): after scoring by points-at-stake we build
`InterleaveItem`s keyed on `current_deck_id` and reorder the gathered reviews via
`interleave_order`. So reviews are still weakest/highest-yield-first, but topics are
mixed instead of blocked. Both prior points-at-stake integration tests still pass
(single-deck + one-card-per-deck are interleave-invariant).

**Built-in content (single source of truth in the engine).** New `speedrun/seed.rs`:
56 original, high-yield cards across 7 subjects (Biochem, Bio, Gen Chem, Orgo,
Physics, Psych, Soc), authored once in Rust so desktop + mobile ship the _same_ deck
with zero duplication. `Collection::speedrun_seed_builtin` (idempotent — no-ops if any
`mcat-flashcard`-tagged card exists) creates per-topic subdecks `MCAT::<Topic>` (Basic
notetype), sets the `MCAT` root deck to the `SpeedrunPointsAtStake` review order **and**
`RANDOM_CARDS` new-card gather (so even the first pass mixes topics — new cards have no
memory signal to interleave on), and seeds high-yield `speedrunTopicPoints`
(biochem 5, bio/psych 4, gchem/phys/soc 3, orgo 2) without clobbering user values.
Exposed via new `SpeedrunSeedBuiltin` RPC (`generic.UInt32` count).

**Tests.** cargo: interleave (3) + seed idempotency/coverage (1) + existing 27 speedrun
tests all green. Python e2e (`pylib/tests/test_speedrun_seed.py`): seeding is
idempotent and, after turning the seeded cards into due reviews, the `MCAT` queue spans
≥5 topics with **zero consecutive same-topic cards across the first 14** — proving the
interleave runs end-to-end through the real engine + proto seam.

**UI.** Desktop `qt/aqt/speedrun.py`: "Set up MCAT flashcards" button → `speedrun_seed_builtin`
→ `mw.reset()` + info/tooltip. Mobile `SpeedrunActivity.kt`: matching button →
`CollectionManager.getBackend().speedrunSeedBuiltin()`.

**Mobile port + proof.** Applied the same `queue.rs`/builder/`service`/proto edits to the
backend `anki` submodule @ 25.09.2 and copied `seed.rs` byte-identical; `./build.sh`
→ AAR OK, `GeneratedBackend.kt` exposes `speedrunSeedBuiltin(): Int`. Rebuilt+installed
the APK. On the emulator: overflow → MCAT Speedrun → "SET UP MCAT FLASHCARDS" → the deck
list now shows an **`MCAT` deck expanding to all 7 subject subdecks, 8 cards each (56)**,
and studying it draws mixed topics. Same engine, same built-in deck, same interleaving on
both platforms.

**Note on scope.** "Solely MCAT" = shipped built-in MCAT content + made MCAT the focus;
did NOT delete the user's other decks (non-destructive).

---

## 2026-07-01 — Content bank scaled + seeding unified in the engine (desktop + mobile)

**Why.** User: the built-in bank was too small, and practice questions were still being
seeded from per-platform hardcoded lists (Python `SEED_QUESTIONS` on desktop, Kotlin
`SEED_QUESTIONS` on mobile). Goal: one large built-in bank, one source of truth, seeded
by the shared engine so desktop and mobile ship identical content. Questions stay
**topic-separated** from flashcards (Memory tracks recall per topic; Performance tracks
applied accuracy per topic — kept distinct on purpose per the honesty rules).

**Engine is now the single source of truth.** `rslib/src/speedrun/seed.rs` bundles two TSVs
via `include_str!` — `mcat_flashcards.tsv` (210 cards, 30 × 7 subjects) and
`mcat_questions.tsv` (105 questions, 15 × 7 subjects). `speedrun_seed_builtin` now seeds
BOTH: flashcards into `MCAT::<Topic>` (Basic notetype, `SpeedrunPointsAtStake` +
`RANDOM_CARDS`), and questions into `MCAT Practice::<Topic>` under a Rust-created
"MCAT Practice Question" notetype (fields Topic/Stem/A–D/Answer/Explanation, tagged
`mcat-question`). Idempotent; returns total added (315). To grow the bank later, just edit
the TSVs — no code changes.

**UIs collapsed to one button.** Desktop `qt/aqt/speedrun.py` and mobile
`SpeedrunActivity.kt` both now have a single **"Set up MCAT content"** button →
`speedrun_seed_builtin`. Removed the old dual-path seeders: deleted Python
`SEED_QUESTIONS`/`ensure_notetype`/`seed_demo_questions` and the "Seed demo questions"
button; deleted the Kotlin equivalents (`SEED_QUESTIONS`, `seedDemoQuestions`,
`ensureQuestionNotetype`, `onSeed`, componentN destructuring helpers, unused `Collection`
import).

**Verified.** cargo `speedrun::seed` green. Desktop: full build + 5 Python e2e tests pass;
headless seed → 315 added (210 flashcards + 105 questions, 7 subdecks each). Mobile:
copied `seed.rs` + both TSVs byte-identical to backend @ 25.09.2, rebuilt AAR (flashcard
text confirmed embedded in `librsdroid.so`), rebuilt+installed arm64 APK. On the emulator:
overflow → MCAT Speedrun shows only the single "SET UP MCAT CONTENT" button; tapping it
seeded a fresh collection to **315 notes / 315 cards (210 `mcat-flashcard` + 105
`mcat-question`)** — confirmed by pulling `collection.anki2`. Same engine, same bank, both
platforms.

---

## 2026-07-01 — Cleanup pass + timed practice-test mode (desktop)

**Cleanup (new-model review of all fork additions).** Removed a 1.3 GB stray
`target-speedrun/` scratch build dir and gitignored `/target-speedrun` + `/target-*`.
Deleted dead constants (`NOTETYPE_NAME`, `PRACTICE_DECK`, `FIELDS`) from
`qt/aqt/speedrun.py` (seeding is engine-side now; UI only needs the two tags). Fixed three
stale "Seed demo questions" strings (2 desktop, 1 mobile `SpeedrunActivity.kt`) to
"Set up MCAT content". Re-verified: desktop build + 5 Python e2e + 27 Rust speedrun unit
tests all green. Kept `_load_questions_random` — it's the toggle-off baseline, not dead.

**Timed test mode (desktop, pure Qt — no engine/proto changes).** Added two dialogs to
`qt/aqt/speedrun.py`: `TestSetupDialog` (subject scope incl. "All subjects (mixed)",
question count, optional timer defaulting to ~90 s/question) and `TestRunnerDialog`
(QStackedWidget: exam page + summary page). The runner shows one question at a time with
**no feedback until the end**, Previous/Next nav, a live countdown that auto-submits at
0:00, then a scored summary (overall %, per-subject breakdown, time used) and a full
answer-by-answer review with explanations. Honesty preserved: only _answered_ questions are
logged via the existing `speedrun_record_attempt` RPC (blanks are scored incorrect in the
test summary but never fed to Performance/Readiness). New "Take timed test" button sits next
to "Start practice set"; both gate on questions existing. Verified headlessly (offscreen
Qt): 10-q mixed test, answered 6 (4 right / 2 wrong) + 4 blank → exactly 6 attempts logged
to the engine, summary + review populated. No upstream files touched (all in our
`qt/aqt/speedrun.py`); no `TOUCHED-UPSTREAM.md` entry needed.

**Not yet done:** mobile parity for the timed test (would mirror into
`SpeedrunActivity.kt` + APK rebuild). Deferred as a follow-up.

---

## 2026-07-01 — Concept-level FSRS scheduling for questions + open-ended runner

**Why.** The practice runner previously ranked the whole question set once (weakness-
weighted "points at stake") and marched through it. Re-showing the _same_ MCAT item tests
memory of the item, not the ability to apply the concept to a novel question — which is what
the exam measures. So we moved spacing up one level: FSRS now schedules the **concept**
(subject/topic), not the item. This is also the seam AI generation will plug into later
("concept X is due" → generate a fresh question instead of re-serving one).

**Engine (`rslib/src/speedrun/concepts.rs`, NEW).** Each concept carries an FSRS
`MemoryState` stored in a collection-config map (`speedrunConcepts`, keyed by lowercased
deck leaf, e.g. `biology`). `speedrun_update_concept` runs the real `fsrs` crate on each
graded answer (correct → `good`, incorrect → `again`; `FSRS::new(Some(&[]))` selects the
default params — `None` disables next_states and panics). `speedrun_next_question` picks the
most-due concept and serves its least-recently-seen item. Priority blends three signals:
`urgency = 1-R` (real FSRS spacing across days) × MCAT-yield points, with a small urgency
floor and a `/(1+times_today)` divisor so a single session **rotates across concepts
instead of hammering the highest-yield one** once everything's been reviewed today (FSRS is
whole-day, so within-day it has no spacing signal left). Interleaving thus falls out of the
FSRS dynamics for free — verified distribution over 21 answers ≈ yield-proportional
(Biochem 5 / Bio 4 / Psych 4 / GChem 3 / Phys 2 / Soc 2 / Orgo 1) with only 1 consecutive
repeat. `speedrun_record_attempt` now also advances the concept state (derives concept from
the card's deck). Daily pacing: response carries `answered_today` + recommended band
(`RECOMMENDED_DAILY_MIN=20`, `MAX=60`); nothing is hard-blocked.

**Proto/seam.** Added `rpc SpeedrunNextQuestion` + `SpeedrunNextQuestionResponse`
(`has_question`, card/topic/priority/attempts, `concept_retrievability`, `answered_today`,
`recommended_min/max`). Old plural `SpeedrunNextQuestions` kept (still tested) but no longer
UI-driven. Service impl in `scheduler/service/mod.rs`.

**UI — open-ended, one at a time.** Both desktop (`qt/aqt/speedrun.py`) and mobile
(`SpeedrunActivity.kt`) rewritten: no fixed set size. "Start practice" fetches one question
via `speedrun_next_question`; after answering, "Next question" fetches the next. Shows a
daily label ("Today: N answered (recommended 20–60) — …"), a session counter, and a
per-question "why" (concept + FSRS recall %, or "new concept"). Removed the old
weighted/random batch loaders and the "Weakness-weighted order" checkbox (the flow is now
inherently scheduled). Timed-test mode (desktop) untouched — it still random-samples.

**Verified.** Rust: `speedrun::` 30/30 unit tests green (3 new concept tests incl.
within-day rotation). Desktop: full build, 5 Python e2e green, headless smoke shows
yield-proportional interleaving + daily counting. Mobile: fsrs 5.1.0 vs desktop 5.2.0 (same
major — API compatible); copied `concepts.rs` byte-identical, applied the 3 `content.rs`
edits + `mod.rs`/proto/service edits, rebuilt AAR (generated `speedrunNextQuestion()` Kotlin
binding present) + APK. On emulator: overflow → MCAT Speedrun → Set up → Start practice
served **Biochemistry · new concept**, answering it flipped the daily label to "1 answered"
and the session to "1 correct" with the correct explanation, and Next served **Biology ·
new concept** — same introduce-by-yield + interleave behavior as desktop.

---

## 2026-07-01 — Performance/Readiness give-up rule now requires FULL topic coverage

**Why.** The old gate showed a Performance number after just 10 total attempts — which
could all be one lucky subject. Per user: withhold predictions until **every** MCAT topic
has been hit at least 3 times, so a projection never rests on partial subject coverage.
(Iterated from a first "≥3 topics deep" cut to "all topics deep".)

**Change (`rslib/src/speedrun/scores.rs` + `content.rs`).** `ScoreConfig` gained
`performance_min_attempts_per_topic` (default 3); `performance_min_attempts` lowered to 8 as
a light floor. `performance_score(attempts, total_topics, cfg)` now takes the size of the
topic universe and withholds unless **all** `total_topics` have ≥3 graded attempts, with a
reason like _"Hit every topic at least 3 times before predictions — 6/7 topics tested in
depth so far."_ `content.rs::gather_performance` computes `total_topics` as the count of
distinct question subdecks in the bank (including unattempted ones); `topic_id` = subdeck id,
so coverage/depth are tracked per MCAT subject. Readiness cascades (it's gated on
Performance). UI unchanged — it already renders the withheld reason.

**Verified.** Rust: 32/32 `speedrun::` tests (new `performance_needs_every_topic_hit_to_depth`;
recency/range/etc. tests updated to pass `total_topics`). Desktop: rebuilt, 2 score e2e green.
Backend headless on the full seeded bank (7 subjects): 6/7 subjects hit 3× each → withheld
("6/7 topics tested in depth so far"), Readiness withheld; after the 7th subject → Performance

- Readiness both unlock. Mobile: copied `scores.rs`, applied the `content.rs` edit, rebuilt
  AAR + APK, reinstalled on emulator (same shared engine).

---

## 2026-07-01 — "I don't know / I'm guessing" button (both apps)

**Why.** Honesty: if a user guesses and happens to be right, that shouldn't inflate
Performance/Readiness. Give them an explicit way to say "I don't know" instead of guessing.

**Design (UI-only — no engine/proto change).** Added an "I don't know / I'm guessing" button
to the practice runner in both apps. Tapping it reveals the correct answer + explanation (so
you still learn) and logs the attempt via the existing `speedrun_record_attempt(card_id,
correct=false)`. Because it records as _not known_, it (a) counts against applied accuracy so
guessing can't inflate scores, and (b) advances that concept's FSRS state as an "again"
(concept comes back sooner) — the pedagogically correct outcome. It increments the session
"answered" and daily counters but never the "correct" counter. Desktop: `qt/aqt/speedrun.py`
(`on_dont_know`, orange "Marked ‘don't know’" feedback). Mobile: `SpeedrunActivity.kt`
(`onDontKnow`). The timed-test mode is intentionally left as-is (an exam simulates real
guessing; leaving a question blank there is already excluded from scoring).

**Verified.** Desktop offscreen smoke: button records `spA:[[0,0]]` (incorrect), session
stays 0 correct, honest feedback shown, Next enabled. Mobile on emulator: Start practice →
"I don't know" → session "1 answered • 0 correct", daily "2 answered", answer revealed,
Performance still gated. Same behavior both platforms.

---

## 2026-07-02 — Infinite AI question generation (desktop) + held-out eval

**Why.** Make the application-question bank effectively bottomless without hand-authoring,
while honoring the brief's AI rules: traceable sources, held-out evaluation, and the app must
stay fully usable with AI **off**.

**Design (desktop, Python/qt layer — no engine or proto change).** New `qt/aqt/speedrun_ai.py`:

- **Grounded (RAG-lite) generation.** For a chosen subject we pull that subject's built-in
  flashcards (`MCAT::<subject>`) as _source facts_, feed them to the model, and require each
  generated question to cite the fact index it tests. That makes sources **traceable** and
  curbs hallucination. Provenance (source fact + model + prompt version + verified flag) is
  stored via tags (`mcat-ai`, `mcat-ai-verified`) and a visible footer appended to the
  Explanation — **not** in `custom_data`, which Anki hard-caps at 100 bytes and reserves for
  the attempt log (`spA`). (Learned that cap the hard way in testing.)
- **Independent verifier (held-out style).** Optional second pass: a separate, temperature-0
  call answers the item _blind_ (not told the key); we keep it only if it independently lands
  on the same answer and judges the item single-correct. Failures are dropped.
- **Same pipeline as built-ins.** Accepted questions are ordinary `MCAT Practice Question`
  notes tagged `mcat-question` in `MCAT Practice::<subject>`, so the existing concept-FSRS
  scheduler and Performance/Readiness scoring pick them up with zero extra wiring.
- **Key never in the repo.** Read from `OPENAI_API_KEY` or the local Anki profile
  (`mw.pm.profile`, per-machine, not synced, not committed). Model defaults to `gpt-4o-mini`,
  overridable.

**UI (`qt/aqt/speedrun.py`).** "Generate with AI" button → `GenerateDialog` (subject, count,
model, masked key, verify toggle, auto-gen toggle). Generation runs on a background thread via
`mw.taskman.with_progress`; the collection is only touched on the main-thread callback.
Optional **auto top-up**: when a served concept drops below 3 unseen questions during practice,
a background batch of 5 is generated for it (off by default). Everything is gated so the app is
100% functional with no key.

**Held-out evaluation harness.** `speedrun/ai_eval.py` (stdlib-only, reads the bundled TSVs):
(1) **verifier calibration** — hides the answer key on a held-out sample of _built-in_ questions
and measures how often the checker recovers the known answer (trust ceiling for auto-policing);
(2) **generation pass rate** — generates a grounded batch and reports the fraction that survive
the independent verifier.

**Verified.** Live run (`gpt-4o-mini`, Biochemistry): verifier calibration **3/3** matched known
keys, generation **3/3** structurally valid and independently verified. Headless (built engine,
seeded bank): `insert_questions` adds a note with tags `[mcat-ai, mcat-ai-verified,
mcat-question]` in `MCAT Practice::Biochemistry`, Explanation carries the Source footer,
`unseen_count` 15→16, and `speedrun_next_question` still serves. `py_compile` + offscreen
`import aqt.speedrun` clean.

**Mobile.** Generated questions are standard synced objects (notes/cards), so they reach
AnkiDroid through Anki's normal collection sync — no on-device key needed (deliberately, to keep
the API key off the phone). On-device generation on Android is a possible later add.

**SECURITY.** The API key was shared in plaintext in chat during this work; it must be rotated.
No key is stored in the repo (env var / local profile only).

**Follow-up — visible AI mode switch.** Replaced the buried auto-gen checkbox with a clear
three-way switch + status dot in the panel: **Off** (bank only), **Manual** (button only),
**Auto** (background top-up = infinite). Stored in profile (`speedrun_ai_mode`), migrating the
old `speedrun_ai_autogen` bool → `auto`. Switching to Manual/Auto with no key prompts for one
(else snaps back to Off). Status dot shows grey Off / orange "no API key" / blue "manual" /
green "auto" with the active model. `_maybe_autogen` fires only in Auto. Clarified for the user
that "Start practice"/timed test never call the AI directly — they read the existing bank; only
the button and Auto top-up generate.

---

## 2026-07-03 — Sync proof, version-compat finding, and CI green-up

**Sync works for questions, per-topic strength, and all three scores — verified.** The scores
are never persisted; they're recomputed from synced structures (per-topic FSRS strength in
config `speedrunConcepts`, attempt logs in each question card's `custom_data` `spA`, topic
points in config). Added a repeatable end-to-end test `speedrun/sync_check.py`: spins up
Anki's own self-hosted sync server, seeds collection A + logs 24 attempts across topics,
uploads, downloads into a fresh collection B, and asserts concept strength, attempt logs,
topic points, and all three scores are identical. Result: all PASS.

**Version alignment turned out unnecessary (no risky downgrade).** Investigated whether the
desktop (26.05) vs mobile (25.09.2) gap breaks sync. It doesn't: both use the identical sync
protocol range (v8–v11, `rslib/src/sync/version.rs`) and DB schema range (v11–v18,
`rslib/src/storage/upgrades/mod.rs`). Sync compatibility is gated on those, not the marketing
version, so no re-anchor is needed. Corrected the stale "re-anchor desktop to 25.09.2" note in
HOWTO-RUN.

**CI green-up.** The fork's inherited Anki CI was red. Root causes + fixes:

- **format** (`just fmt`): committed files weren't dprint/rustfmt-formatted → ran `just fix-fmt`.
- **clippy** (`just lint`): `content.rs::topic_points_for_deck` used `contains_key`+`insert`
  (`clippy::map_entry`) → switched to the `Entry` API (desktop + mobile copies).
- **mypy**: `speedrun.py` passed a bare `int` to `get_card` (wrap in `CardId`) and named an
  attribute `self.finished`, shadowing `QDialog.finished` (a Qt signal) → renamed to
  `self._finished`.
- **minilints** (`cargo run -p minilints`): requires the _latest commit's_ author email to be
  one that has edited `CONTRIBUTORS` (`git log -1 %ae` ∈ `git log %ae CONTRIBUTORS`). Fix = add
  the committing identity to `CONTRIBUTORS` in a commit authored by that email.

After fixes: `just fmt` clean; `just lint` clean (clippy/mypy/ruff/eslint/svelte/typescript);
32 Rust + 5 Python speedrun tests pass. (The only failing suite locally is
`qt/tests/test_installer.py`, which needs network to clone the briefcase app-template —
environmental, unrelated to our code, passes in real CI.)
