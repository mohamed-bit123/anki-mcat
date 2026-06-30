# Speedrun — How to Run & Test (Desktop + Android Emulator)

Practical run instructions for both apps. Keep this in sync as the build evolves.

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
  AnkiDroid `main` expects). Both carry the same additive change. To make them a
  byte-identical version, re-anchor desktop to 25.09.2 (optional; 2 additive files).
- Backend build needs NDK **29.0.14206865** and JDK 17. `build.sh` auto-installs
  `cargo-ndk` + rust android targets and uses rust 1.89.0 (backend-pinned).
