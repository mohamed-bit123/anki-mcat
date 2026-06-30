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
  "/Users/mohamedshawgi/anki-mcat/mobile/Anki-Android/AnkiDroid/build/outputs/apk/full/debug/AnkiDroid-full-arm64-v8a-debug.apk"
```
Then open "AnkiDroid" from the emulator's app drawer.

3. Rebuild the APK after Android code changes:
```bash
cd /Users/mohamedshawgi/anki-mcat/mobile/Anki-Android
export JAVA_HOME="$HOME/jdk21/Contents/Home"; export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$JAVA_HOME/bin:$PATH"
./gradlew :AnkiDroid:assembleFullDebug --console=plain
```

### Tip: run on your real iPhone? (later/bonus)
iOS is a stretch goal — no AnkiDroid-equivalent to fork; we'd build a Swift app
over `rslib` via C FFI. Android emulator is the primary mobile target for now.

## IMPORTANT caveat about "our engine" on Android (current status)
The AnkiDroid build above uses the **stock prebuilt Rust backend (`rsdroid`)**
pulled from Maven — which IS Anki's real Rust engine (so "shared engine" holds),
but it does NOT yet contain OUR Rust change (`speedrun_ping`, and later the
points-at-stake queue). To ship our Rust change to the phone we must rebuild
`rsdroid` from our fork (needs the Android NDK + rust android targets) and point
AnkiDroid at the local `.aar`. That's the next mobile milestone (Phase 0 final /
"Stage B"). Tracked in PLAN.md + JOURNAL.md.
