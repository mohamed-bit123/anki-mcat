# Speedrun — How to Run & Test (Desktop + Android Emulator)

Practical run instructions for both apps. Keep this in sync as the build evolves.

> **Just want to verify it works?** Run `bash verify/run-all.sh` (builds, tests,
> sync round-trip, latency) — see [`../verify/README.md`](../verify/README.md) for
> the one-place hub of build / installer / test / latency artifacts.

## One-time environment (already done on this machine)

- Rust 1.92.0 via rustup; `just`; `n2` (`bash tools/install-n2`).
- **JDK 17** at `~/jdk17/Contents/Home` (desktop Anki build).
- **JDK 21** at `~/jdk21/Contents/Home` (AnkiDroid — needs JDK 21–25).
- Android SDK at `~/Library/Android/sdk` (platform-tools, emulator, android-35,
  build-tools 35, arm64 system image). AVD named **`mcat`**.

Handy shell prelude (desktop work):

```bash
. "$HOME/.cargo/env"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

Handy shell prelude (Android work):

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export JAVA_HOME="$HOME/jdk21/Contents/Home"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
```

## A) Desktop (your laptop)

From the repo root (`/Users/mohamedshawgi/anki-mcat`):

```bash
. "$HOME/.cargo/env"; export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
just run
```

This builds pylib+qt and launches the Anki desktop GUI. Web views are served at
http://localhost:40000/_anki/pages/ .

Headless sanity check of the engine (no GUI), useful for testing backend calls:

```bash
PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/python - <<'PY'
import tempfile, os
from anki.collection import Collection
col = Collection(os.path.join(tempfile.mkdtemp(), "t.anki2"))
print(col._backend.speedrun_ping())   # our Rust change
col.close()
PY
```

Expected: `speedrun: scheduler engine alive (anki 26.05)`.

> **Build gotcha (pure-Rust edits).** `just build`/`just run` only relink the pylib
> Rust bridge when a _tracked_ input changes (proto, `Cargo.toml`, etc.). Editing only
> `rslib/src/**.rs` — or adding a new `.rs` file — may report "up to date" and ship a
> **stale** `.so`. Force a rebuild by touching a tracked input first:
> `touch rslib/Cargo.toml pylib/rsbridge/lib.rs && just build`. (Verify: run the headless
> smoke above and confirm new behavior appears.)

**MCAT Speedrun panel** (Tools → MCAT Speedrun). "Set up MCAT content" seeds the bank.
"Start practice" is now an **open-ended, one-question-at-a-time** runner: each question is
chosen by concept-level FSRS (`speedrun_next_question`) — the most-due concept, weighted by
MCAT yield, interleaved — with a daily pacing label (recommended 20–60/day, not enforced).
"Take timed test" is the separate exam-block mode.

## B) Android emulator (on your Mac, with a window)

> Headless (`-no-window`) boot is unreliable from automation; run it WITH a
> window. Easiest is Android Studio, but the CLI below works too.

1. Boot the emulator (opens a phone window):

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
emulator -avd mcat &
```

Wait until the Android home screen appears (first cold boot can take a few min).
Check it's ready: `adb devices` should list `emulator-5554  device`.

2. Install the AnkiDroid APK we built (arm64 matches the emulator):

```bash
adb install -r \
  "/Users/mohamedshawgi/anki-mcat-mobile/Anki-Android/AnkiDroid/build/outputs/apk/full/debug/AnkiDroid-full-arm64-v8a-debug.apk"
```

Then open "AnkiDroid" from the emulator's app drawer.

3. See OUR Rust change run on the phone. On the deck list, a snackbar shows
   `speedrun: scheduler engine alive (anki 25.09.2)`. Or capture it via logcat:

```bash
adb logcat -d | grep SPEEDRUN
```

(The string comes from our `speedrun_ping()` in `rslib`, compiled into
`librsdroid.so`, called via the generated `Backend.speedrunPing()` binding.)

### Infinite AI question generation (desktop)

The panel has an **AI question generation** switch with a live status dot:

- **Off** — never calls the AI; the app runs entirely on the built-in bank.
- **Manual** — the **"Generate with AI"** button works; nothing runs on its own.
- **Auto** — additionally tops a subject up in the background when it drops below 3 unseen
  questions during practice (the "infinite" mode).

**"Generate with AI"** creates fresh application questions for a subject, grounded in that
subject's built-in flashcards (so each cites a source fact). They join the same bank
(`mcat-question` + `mcat-ai` tags, `MCAT Practice::<subject>` deck) and are scheduled/scored
exactly like the built-ins. An optional "double-check with an independent AI pass" drops
questions the checker can't independently confirm. Note: "Start practice"/"Take timed test"
draw from the existing bank — only Manual (button) and Auto (top-up) actually call the AI.

Key handling (never in the repo): set `OPENAI_API_KEY` in the environment, or paste the key
into the Generate dialog (stored only in the local Anki profile). Model defaults to
`gpt-4o-mini`; override via the dialog or `OPENAI_MODEL`. The app is fully usable with AI off.

Prove quality offline (held-out evaluation):

```bash
OPENAI_API_KEY=sk-... python3 speedrun/ai_eval.py --subject Biochemistry --calib 15 --generate 10
```

Reports (1) verifier calibration vs. known answers on held-out built-in questions and (2) the
independently-verified pass rate of freshly generated questions.

> Mobile: AI-generated questions are ordinary synced cards, so they reach AnkiDroid via normal
> AnkiWeb/collection sync — no API key on the phone.

### Verify desktop<->mobile sync (scores, per-topic strength, attempts)

The three scores aren't stored — they're recomputed from data that lives in synced
structures (per-topic FSRS strength in config `speedrunConcepts`, attempt logs in each
question card's `custom_data`, topic points in config). So they sync as long as those
inputs do. Prove it end-to-end against Anki's own sync server:

```bash
PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python speedrun/sync_check.py
```

It seeds a collection, logs practice attempts, uploads, downloads into a fresh
collection, and asserts the concept strength, attempt logs, topic points, and all three
scores match (exit 0 = all synced).

### Built-in MCAT flashcards + interleaving (desktop + mobile)

In the MCAT Speedrun screen (desktop Tools → MCAT Speedrun, or mobile overflow →
MCAT Speedrun) click **"Set up MCAT flashcards"**. This calls the shared engine's
`speedrun_seed_builtin` RPC once (idempotent) and:

- creates an **`MCAT` deck with a subdeck per subject** (`MCAT::Biochemistry`, …,
  7 subjects × 8 built-in cards = 56), all tagged `mcat-flashcard`;
- sets that deck to study with the **points-at-stake review order + interleaving**
  (reviews are weakest/high-yield-first but topics are mixed, never blocked) and
  **RANDOM_CARDS** new-card gather so the first pass also pulls from all topics;
- seeds high-yield topic points (biochem 5, bio/psych 4, gchem/phys/soc 3, orgo 2).
  Then just study the **`MCAT`** deck — it interleaves every subject. To watch the
  interleave end-to-end headlessly, run `pytest pylib/tests/test_speedrun_seed.py`.

### The full MCAT Speedrun screen on mobile (Phase 2 parity)

On the deck list, open the **overflow menu (⋮)** → **"MCAT Speedrun"**. This opens
`SpeedrunActivity`, the phone twin of the desktop Tools → MCAT Speedrun panel:

- Three honest score cards (Memory / Performance / Readiness) straight from the
  shared engine (`speedrunScores`); withheld scores show the engine's reason.
- "Seed demo questions" adds the 12-question starter bank (per-topic subdecks).
- "Start practice set" pulls the weakness-weighted order (`speedrunNextQuestions`),
  shows the priority, grades answers, logs them (`speedrunRecordAttempt`), and
  refreshes the scores after each answer.
  Same engine, same scores, same ordering, same honesty rules as desktop.

4. Rebuild the APK after Android code changes:

```bash
cd /Users/mohamedshawgi/anki-mcat-mobile/Anki-Android
export JAVA_HOME="$HOME/jdk21/Contents/Home"; export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$JAVA_HOME/bin:$PATH"
./gradlew :AnkiDroid:assembleFullDebug --console=plain
```

5. Rebuild the Rust backend `.aar` after engine (`rslib`) changes, then redo step 4:

```bash
cd /Users/mohamedshawgi/anki-mcat-mobile/Anki-Android-Backend
. "$HOME/.cargo/env"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export JAVA_HOME="$HOME/jdk17/Contents/Home"
export PATH="$JAVA_HOME/bin:$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
./build.sh            # arm64 only; prepend ALL_ARCHS=1 for every ABI
```

AnkiDroid picks up the rebuilt `.aar` automatically (`local_backend=true` in its
`local.properties`).

### Tip: run on your real iPhone? (later/bonus)

iOS is a stretch goal — no AnkiDroid-equivalent to fork; we'd build a Swift app
over `rslib` via C FFI. Android emulator is the primary mobile target for now.

## Status: OUR engine change now ships on Android (Stage B DONE)

The APK above is built against `rsdroid` rebuilt **from our fork** (anki 25.09.2 +
our additive `SpeedrunPing` RPC), wired via `local_backend=true`. Proof: our string
is in the APK's `librsdroid.so` (`grep -a`), the generated `Backend.speedrunPing()`
Kotlin binding exists, and the `DeckPicker` hook surfaces it on screen. So the same
engine change runs on BOTH desktop and phone.

### Mobile layout & versions (so you don't get confused later)

- Mobile checkouts live OUTSIDE this repo, at `/Users/mohamedshawgi/anki-mcat-mobile/`:
  `Anki-Android/` (the app) and `Anki-Android-Backend/` (builds `rsdroid`), as
  siblings. They were moved out of `anki-mcat/` because yarn merged this fork's
  `.yarnrc.yml` into the backend's older anki and broke the build (see JOURNAL).
- DESKTOP engine = anki **26.05**; MOBILE engine = anki **25.09.2** (the version
  AnkiDroid `main` expects). Both carry the same additive change.
- **Sync compatibility (verified):** the version _numbers_ differ but the
  sync-relevant versions are identical on both — sync protocol **v8–v11** and DB
  schema **v11–v18** (see `rslib/src/sync/version.rs` and
  `rslib/src/storage/upgrades/mod.rs`). Sync compatibility is gated on those, not
  the marketing version, so desktop<->mobile sync works without a downgrade. Prove
  it any time with `speedrun/sync_check.py` (below). No re-anchoring needed.
- Backend build needs NDK **29.0.14206865** and JDK 17. `build.sh` auto-installs
  `cargo-ndk` + rust android targets and uses rust 1.89.0 (backend-pinned).
