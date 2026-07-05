#!/usr/bin/env bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Turnkey phone<->desktop sync demonstration for the MCAT Speedrun fork.
#
# Stands up Anki's own self-hosted sync server (no AnkiWeb account, no internet)
# bound so that BOTH the desktop app and the Android emulator can reach it, then
# walks you through the required "review on the phone -> appears on the desktop"
# recording. `verify/sync_check.py` already proves the data round-trips
# programmatically; this makes the same thing recordable with the real apps.
#
# Usage:
#   verify/sync_demo.sh                 # start server + print the demo recipe
#   verify/sync_demo.sh --record        # also screen-record the emulator (adb)
#
# The emulator reaches the host loopback at the special address 10.0.2.2, so the
# phone points at http://10.0.2.2:PORT/ while the desktop points at
# http://127.0.0.1:PORT/ — both hit this one server. Ctrl-C to stop.
set -uo pipefail

PORT="${SYNC_PORT:-27713}"
USER="${SYNC_DEMO_USER:-demo}"
PASS="${SYNC_DEMO_PASS:-demo}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYENV="$ROOT/out/pyenv/bin/python"
BASE="$ROOT/verify/artifacts/sync-demo-base"
ART="$ROOT/verify/artifacts"
RECORD=0
[ "${1:-}" = "--record" ] && RECORD=1

[ -x "$PYENV" ] || { echo "error: $PYENV not found — build first (just run once)"; exit 1; }
mkdir -p "$BASE" "$ART"

ADB="$HOME/Library/Android/sdk/platform-tools/adb"
[ -x "$ADB" ] || ADB="$(command -v adb 2>/dev/null || true)"

SERVER_PID=""
REC_PID=""
cleanup() {
  echo
  echo "=== stopping demo ==="
  if [ -n "$REC_PID" ]; then
    kill "$REC_PID" 2>/dev/null
    "$ADB" shell pkill -INT screenrecord 2>/dev/null
    sleep 2
    "$ADB" pull /sdcard/sync-demo.mp4 "$ART/sync-demo-phone.mp4" 2>/dev/null \
      && echo "saved emulator recording -> $ART/sync-demo-phone.mp4"
  fi
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null
  echo "sync server stopped. Uploaded collection persists under:"
  echo "  $BASE"
}
trap cleanup INT TERM EXIT

# Best-effort LAN IP (also handy if recording from a physical phone).
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '<your-LAN-IP>')"

echo "=== starting self-hosted Anki sync server ==="
SYNC_USER1="$USER:$PASS" SYNC_HOST="0.0.0.0" SYNC_PORT="$PORT" \
  SYNC_BASE="$BASE" RUST_LOG="anki=info" \
  PYTHONPATH="$ROOT/pylib:$ROOT/out/pylib" \
  "$PYENV" -c "from anki.syncserver import run_sync_server; run_sync_server()" \
  >"$ART/sync-demo-server.log" 2>&1 &
SERVER_PID=$!

# Wait for health.
up=0
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then up=1; break; fi
  sleep 0.25
done
[ "$up" = 1 ] || { echo "error: sync server did not come up (see $ART/sync-demo-server.log)"; exit 1; }
echo "sync server healthy on port $PORT (user: $USER / pass: $PASS)"
echo

cat <<EOF
────────────────────────────────────────────────────────────────────────────
  RECORD THIS: phone -> desktop sync (self-hosted, no AnkiWeb needed)
────────────────────────────────────────────────────────────────────────────
Endpoints (same server):
  desktop        ->  http://127.0.0.1:$PORT/
  emulator       ->  http://10.0.2.2:$PORT/
  physical phone ->  http://$LAN_IP:$PORT/
Login for both apps:  user "$USER"  password "$PASS"

1) DESKTOP  (already-running Anki):
     Preferences -> Syncing -> "Self-hosted sync server" = http://127.0.0.1:$PORT/
     Close prefs, click Sync (or press Y), log in $USER/$PASS.
     First sync: choose **Upload to AnkiWeb** (pushes your MCAT collection up).

2) PHONE  (AnkiDroid on the emulator):
     Settings -> Sync -> Custom sync server: set BOTH the sync and media URLs to
       http://10.0.2.2:$PORT/
     Back out, tap Sync, log in $USER/$PASS, choose **Download** to pull the deck.

3) THE DEMO BEAT (record from here):
     On the PHONE: open the MCAT deck, review a card / answer a practice
       question, then tap Sync.
     On the DESKTOP: click Sync again. The review you just did on the phone now
       shows on the desktop (due counts / stats / the answered question update).

4) Also show the reverse: review on desktop -> Sync -> Sync phone -> it appears.

The three scores travel automatically: they are recomputed from synced inputs
(per-topic FSRS strength, per-question attempt logs, topic points). See
verify/SYNC-DEMO.md for the narration checklist and the offline/conflict beats.
────────────────────────────────────────────────────────────────────────────
EOF

if [ "$RECORD" = 1 ]; then
  if [ -z "${ADB:-}" ] || ! "$ADB" get-state >/dev/null 2>&1; then
    echo "note: --record given but no emulator/device is connected to adb; skipping screen capture."
  else
    echo "recording emulator screen (adb screenrecord, ~3 min max)... Ctrl-C when the demo is done."
    "$ADB" shell screenrecord --bit-rate 6000000 /sdcard/sync-demo.mp4 &
    REC_PID=$!
  fi
fi

echo
echo "server is running; press Ctrl-C to stop."
wait "$SERVER_PID"
