# Phone ↔ Desktop sync — recording guide

The brief requires a **recording of a card reviewed on the phone showing up on
the desktop after sync** (Friday deliverable), and Sunday adds the conflict
beat: _"if both devices review the same card offline, the merge is correct and
documented."_ This page is the checklist for filming that; the plumbing is
automated by [`sync_demo.sh`](./sync_demo.sh).

Two ways to run it — pick one for the recording:

| path                                                   | account?           | internet? | reproducible by a grader |
| ------------------------------------------------------ | ------------------ | --------- | ------------------------ |
| **Self-hosted server** (recommended for the recording) | no                 | no        | yes — one command        |
| AnkiWeb                                                | free AnkiWeb login | yes       | needs your login         |

Both use the _same_ engine and sync protocol; the only difference is the server
URL the two apps point at.

## Option A — self-hosted (turnkey, no account)

```bash
verify/sync_demo.sh            # start the server + print the recipe
verify/sync_demo.sh --record   # additionally screen-record the emulator via adb
```

It stands up Anki's own sync server bound to `0.0.0.0` so both apps reach it:

- **Desktop** → `http://127.0.0.1:PORT/`
- **Emulator** → `http://10.0.2.2:PORT/` (the emulator's alias for the host)
- **Physical phone on the same Wi-Fi** → `http://<your-LAN-IP>:PORT/`

Login for both apps is `demo` / `demo`. Set the URL under **Preferences →
Syncing → Self-hosted sync server** (desktop) and **Settings → Sync → Custom
sync server** (AnkiDroid), then sync.

With `--record`, the emulator screen is captured with `adb screenrecord` and,
on `Ctrl-C`, pulled to `verify/artifacts/sync-demo-phone.mp4`. Record the
desktop half with your normal screen recorder (macOS `⇧⌘5`) so the demo video
shows both sides.

## Step-by-step: test sync (desktop ⇄ Android emulator)

The exact recipe, including the gotchas we hit.

1. **Start the server** and leave it running:

   ```bash
   cd /path/to/anki-mcat && verify/sync_demo.sh
   ```

   Wait for `sync server healthy on port 27713`. It serves **both** collection
   and media sync at the same base URL; login is `demo` / `demo`.

2. **Desktop** → **Tools → Preferences → Syncing → Self-hosted sync server** =
   `http://127.0.0.1:27713/`. Preferences has **no Save button** — just **close
   the window** to persist. Then click **Sync** (or press `Y`), log in
   `demo` / `demo`, and on the first sync choose **Upload** (seeds the server).

3. **Phone / emulator** → **Settings → Sync → Custom sync server**, set the
   single **base URL** = `http://10.0.2.2:27713/` (the emulator's alias for the
   host; a real phone on the same Wi-Fi uses `http://<your-Mac-LAN-IP>:27713/`).
   There is **no separate media-sync-URL field** in AnkiDroid — the one base URL
   covers collection _and_ media, so you're not missing anything. Then **Sync**,
   log in `demo` / `demo`, and on the first sync choose **Download** (pulls the
   desktop's collection down).

4. **The demo loop:** answer a practice question on the phone → tap **Sync** →
   tap **Sync** on the desktop → reopen **MCAT Speedrun** on each. The due
   counts and all three scores match.

### Gotchas (read these)

- **"Keep AnkiWeb or AnkiDroid?"** appears when the two collections diverged and
  a _full_ one-way sync is forced — it **overwrites** the other side, it does
  not merge. Keep the side with the work you want: **AnkiWeb** = the server
  (what the desktop uploaded, i.e. download to the phone); **AnkiDroid** = the
  phone's local copy (upload it, then Download on desktop). After this one-time
  reconcile, later syncs merge both ways automatically.
- **Scores are recomputed from the synced data, never stored** — so once both
  sides hold the same data they compute _identical_ Memory/Performance/Readiness.
  The panel recomputes when it (re)opens; if a number looks stale after a sync,
  just leave and re-enter the panel.
- **Both apps must run the same build.** An older APK ships an older engine and
  will compute _different_ scores from identical data (and won't show newer UI).
  If the phone disagrees with the desktop and the data is in sync, reinstall the
  current APK (see `speedrun/TESTING.md`). On an emulator that boots from a
  snapshot, reinstall after each cold boot or launch with `-no-snapshot`.
- **Server must be running.** Connection errors almost always mean the
  `verify/sync_demo.sh` terminal was closed, or the URL is missing the trailing
  `/`.

## Option B — AnkiWeb

Create one account at <https://ankiweb.net/account/register>, then log into it
on **both** apps (desktop **Sync** button / `Y`; AnkiDroid **Sync**). First
sync is a one-way reconcile — **Upload** on desktop, then **Download** on the
phone — after which every later sync merges automatically.

## What to film (narration checklist)

1. **Show it's one engine, two apps.** Desktop Anki window + the emulator side
   by side, both on the same MCAT deck.
2. **Phone → desktop (the required beat).** On the phone: answer a practice
   question / review a card, then tap **Sync**. On the desktop: click **Sync** —
   the due counts / answered question / stats update to reflect the phone's
   review. This is the shot the brief asks for.
3. **Desktop → phone (the reverse).** Review on the desktop, Sync, Sync the
   phone, show it appear there.
4. **Scores travel.** Open the MCAT Speedrun panel on both — the three scores
   (memory / performance / readiness) and per-topic strength match, because
   they're recomputed from the synced inputs, not stored.
5. **Offline, then reconnect.** Turn the emulator's network off (airplane mode
   or `adb shell svc data disable`), review a few cards, turn it back on, Sync —
   the offline reviews land with none lost.
6. **Same-card conflict.** Review the _same_ card on both devices while offline,
   then sync both. Anki's last-writer-wins rule picks a single clear winner and
   never double-counts. This is proven headlessly in
   [`conflict_check.py`](./conflict_check.py).

## Backing evidence (re-runnable, no devices needed)

- [`sync_check.py`](../speedrun/sync_check.py) — seeds a collection, logs
  practice attempts across topics, uploads to the self-hosted server, downloads
  into a fresh collection, and asserts per-topic strength, attempt logs, topic
  points, **and the three scores are byte-identical**. Artifact:
  [`artifacts/sync.txt`](./artifacts/sync.txt).
- [`conflict_check.py`](./conflict_check.py) — two devices make disjoint offline
  reviews + practice attempts, sync incrementally, and the merge is verified to
  lose/duplicate nothing; documents the same-card last-writer-wins edge case.
  Artifact: [`artifacts/conflict.md`](./artifacts/conflict.md).

Run both:

```bash
PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python speedrun/sync_check.py
PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/conflict_check.py
```
