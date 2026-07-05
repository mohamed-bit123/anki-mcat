# MCAT Speedrun — Tester's Guide

How to build, run, and verify all three projects from scratch on a fresh machine.
This is a fork of Anki (desktop + shared Rust engine) plus a fork of AnkiDroid
(mobile) that reuses the same engine. Everything is additive — plain Anki/AnkiDroid
behavior still works; the MCAT features live behind a "MCAT Speedrun" screen.

## Repositories

| Purpose                                    | URL                                                 | Default branch |
| ------------------------------------------ | --------------------------------------------------- | -------------- |
| Desktop app + shared Rust engine           | https://github.com/mohamed-bit123/anki-mcat         | `main`         |
| Mobile engine (backend `.aar` / `rsdroid`) | https://github.com/mohamed-bit123/anki-mcat-backend | `main`         |
| Mobile app (AnkiDroid)                     | https://github.com/mohamed-bit123/ankidroid-mcat    | `main`         |

The backend repo's `anki` submodule points at the `mobile-backend-25.09.2` branch of
the desktop repo, so `git submodule update --init` resolves automatically.

> Engine versions differ by design: **desktop = anki 26.05**, **mobile = anki 25.09.2**
> (the version AnkiDroid `main` expects). Both carry the same additive MCAT engine code.

---

## Part 1 — Desktop (macOS / Linux)

### Prerequisites

- **Rust** (stable) via https://rustup.rs
- **Python 3.9+**
- **protoc** (Protocol Buffers compiler)
- A C toolchain (Xcode CLT on macOS, `build-essential` on Linux)
- Anki's build tooling is fetched by the repo itself (`just`, `n2`); install `just`
  with `cargo install just` if you don't have it.

### Build & run

```bash
git clone https://github.com/mohamed-bit123/anki-mcat.git
cd anki-mcat
# if n2 (the ninja-compatible build runner) is missing:
bash tools/install-n2
just run
```

`just run` builds the Rust engine + Python/Qt layers and launches the desktop GUI.
First build downloads a lot and can take 10–20 min; later builds are incremental.

### Verify the engine change (no GUI needed)

```bash
PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/python - <<'PY'
import tempfile, os
from anki.collection import Collection
col = Collection(os.path.join(tempfile.mkdtemp(), "t.anki2"))
print(col._backend.speedrun_ping())   # our custom Rust RPC
col.close()
PY
```

Expected output like: `speedrun: scheduler engine alive (anki 26.05)`.

### What to test in the GUI (Tools → MCAT Speedrun)

1. **Set up MCAT content** — seeds the built-in bank (idempotent): an `MCAT` deck with
   a subdeck per subject (flashcards, tagged `mcat-flashcard`) plus a practice-question
   bank (tagged `mcat-question`). Click again → nothing duplicates.
2. **Three honest scores** (Memory / Performance / Readiness). On a fresh profile,
   Performance & Readiness are **withheld** with a stated reason. The give-up rule:
   _every topic in the bank must have ≥3 graded attempts_ before predictions appear.
   Memory appears once you have enough reviewed flashcards.
3. **Start practice** — open-ended, **one question at a time**. Each question is chosen
   by concept-level FSRS (most-due concept, weighted by MCAT yield, interleaved across
   topics). A daily pacing label shows a recommended band (≈20–60/day, not enforced).
4. **"I don't know / I'm guessing"** button — records the attempt as not-known so a
   lucky guess can't inflate Performance/Readiness. Answer several questions "don't
   know" and confirm scores don't jump.
5. **Take timed test** — separate exam-block mode: pick subject/mixed, question count,
   optional timer; no per-question feedback until a summary + review at the end.
6. **Flashcard study** — study the `MCAT` deck and confirm topics are **interleaved**
   (consecutive cards from different subjects) and weak/high-yield cards come first
   (points-at-stake ordering).

### Optional: AI question generation (desktop)

The app is fully testable **without** this. To exercise it you need an OpenAI API key.

1. **Held-out evaluation (no app needed)** — proves generation quality offline:

```bash
OPENAI_API_KEY=sk-... python3 speedrun/ai_eval.py --subject Biochemistry --calib 15 --generate 10
```

Expect a verifier-calibration accuracy and a generation pass rate (both reported as N/M).
2. **In the app** — Tools → MCAT Speedrun → **Set up MCAT content** first (generation is
grounded in the built-in flashcards), then **Generate with AI**: pick a subject, paste the
key (stored locally only, or set `OPENAI_API_KEY`), and generate. New questions appear tagged
`mcat-ai` in `MCAT Practice::<subject>` and immediately feed the runner and scores. Verify:

- generated questions show a "Source: …" footer (traceability) in the explanation;
- turning off AI (no key) leaves everything else working.

> **Security:** never commit a key. The code reads it from `OPENAI_API_KEY` or the local Anki
> profile only. If a key was ever shared in plaintext, rotate it.

3. **Prompt-injection test (no key needed)** — proves a hostile deck (hidden/zero-width text,
   answer-key override, system-prompt exfiltration) cannot steer the generator:

```bash
out/pyenv/bin/python verify/prompt_injection.py --out verify/artifacts/prompt-injection.md
```

Expect **PASS**: injected/leaking items are dropped, a forced/wrong key fails the independent
verifier, and a benign control question still survives. Add `--use-ai` with `OPENAI_API_KEY`
for an additional live-model pass.

### Automated tests

```bash
# Python end-to-end (from repo root)
PYTHONPATH="pylib:qt:out/pylib:out/qt" out/pyenv/bin/pytest \
  pylib/tests/test_speedrun.py \
  pylib/tests/test_speedrun_scores.py \
  pylib/tests/test_speedrun_seed.py

# Rust unit/integration tests for the MCAT engine
cargo test -p anki speedrun

# End-to-end sync proof: uploads/downloads through Anki's own sync server and
# asserts per-topic strength, attempt logs, topic points, and all three scores
# survive the round-trip identically (exit 0 = all synced).
PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python speedrun/sync_check.py
```

> Sync note: desktop (anki 26.05) and mobile (anki 25.09.2) differ in version number but share
> the same sync protocol (v8–v11) and DB schema (v11–v18), which is what actually gates sync —
> so they interoperate without any downgrade.

---

## Part 2 — Mobile (Android emulator)

The mobile app uses a native Rust backend (`rsdroid`, an `.aar`) built from the backend
repo, consumed by the AnkiDroid app via `local_backend=true`.

### Prerequisites

- **JDK 17** (to build the Rust backend `.aar`)
- **JDK 21** (AnkiDroid app requires JDK 21–25)
- **Android SDK + NDK** (via Android Studio or `cmdline-tools`); create an **arm64**
  AVD (Apple Silicon) or x86_64 AVD (Intel/Linux). Android Studio is the easiest path.
- Rust with Android targets — the backend's `build.sh` auto-installs `cargo-ndk` and
  the needed `rustup target`s.

### Step 1 — Build the Rust backend `.aar`

```bash
git clone https://github.com/mohamed-bit123/anki-mcat-backend.git
cd anki-mcat-backend
git submodule update --init          # pulls the MCAT engine (anki 25.09.2 + our code)
export JAVA_HOME=<path-to-jdk17>
export ANDROID_HOME=<path-to-android-sdk>
export PATH="$JAVA_HOME/bin:$PATH"
./build.sh                           # arm64 only; prepend ALL_ARCHS=1 for every ABI
```

### Step 2 — Build the AnkiDroid APK

```bash
git clone https://github.com/mohamed-bit123/ankidroid-mcat.git Anki-Android
cd Anki-Android
# point the app at the locally-built backend .aar:
echo "local_backend=true" >> local.properties
export JAVA_HOME=<path-to-jdk21>
export ANDROID_HOME=<path-to-android-sdk>
export PATH="$JAVA_HOME/bin:$PATH"
./gradlew :AnkiDroid:assembleFullDebug --console=plain
```

> The two repos are expected to be siblings (`Anki-Android/` next to
> `Anki-Android-Backend/`) so the app finds the `.aar`. Keep the backend clone named
> `Anki-Android-Backend` beside the app clone.

### Step 3 — Install & run on the emulator

```bash
export ANDROID_HOME=<path-to-android-sdk>
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
emulator -avd <your-avd-name> &      # boot WITH a window (headless is flaky)
adb wait-for-device
adb install -r AnkiDroid/build/outputs/apk/full/debug/AnkiDroid-full-*-debug.apk
```

Open **AnkiDroid** from the app drawer.

### What to test on mobile

1. **Engine change is live** — on the deck list a snackbar shows
   `speedrun: scheduler engine alive (anki 25.09.2)`; or `adb logcat -d | grep SPEEDRUN`.
2. **Overflow menu (⋮) → "MCAT Speedrun"** opens the phone twin of the desktop panel:
   - Same three honest score cards, same withhold reasons.
   - **Set up MCAT content**, then **Start practice** — one question at a time via the
     same concept-FSRS scheduler, with the daily pacing label.
   - **"I don't know / I'm guessing"** button behaves like desktop.
3. **Parity check** — scores, ordering, and honesty rules should match the desktop app
   because both call the identical shared Rust engine.

---

## Quick sanity matrix

| Feature                                  | Desktop               | Mobile                 |
| ---------------------------------------- | --------------------- | ---------------------- |
| `speedrun_ping` engine RPC               | ✅ (headless snippet) | ✅ (snackbar / logcat) |
| Seed built-in MCAT bank                  | ✅                    | ✅                     |
| Three honest scores + give-up rule       | ✅                    | ✅                     |
| Concept-FSRS one-at-a-time runner        | ✅                    | ✅                     |
| "I don't know" button                    | ✅                    | ✅                     |
| Timed practice-test mode                 | ✅                    | (desktop only)         |
| Interleaved / points-at-stake flashcards | ✅                    | ✅ (same engine)       |

## Troubleshooting

- **Desktop rebuild "up to date" after editing only `.rs`**: touch a tracked input —
  `touch rslib/Cargo.toml pylib/rsbridge/lib.rs && just build`.
- **`git submodule update` fails on the backend**: confirm the submodule URL points to
  `mohamed-bit123/anki-mcat` (branch `mobile-backend-25.09.2`) in `.gitmodules`.
- **App can't find the backend**: ensure `local_backend=true` in `local.properties` and
  that `Anki-Android-Backend` is a sibling folder with a freshly built `.aar`.
- **First Anki desktop build fails on `n2`**: run `bash tools/install-n2` and retry.
