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
