# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Repeatable end-to-end proof that MCAT Speedrun data syncs desktop<->mobile.

The three scores are never stored — they are recomputed from data that lives in
Anki's synced structures:
  * per-topic "strength"  -> collection config map ``speedrunConcepts`` (FSRS)
  * practice attempt logs -> each question card's ``custom_data`` (key ``spA``)
  * topic points          -> config ``speedrunTopicPoints``
So if those inputs sync, both devices compute identical scores.

This script proves it against Anki's own self-hosted sync server: it seeds a
collection A, logs practice attempts across topics, uploads, downloads into a
fresh collection B, and asserts the concept strength, attempt logs, topic
points, and the three scores are identical. Exits non-zero on any mismatch.

Run it with the built engine on the path, e.g. from the repo root:

    PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python speedrun/sync_check.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import urllib.request

PORT = 27713
ENDPOINT = f"http://127.0.0.1:{PORT}/"


def _start_server(base: str) -> subprocess.Popen:
    env = dict(os.environ)
    env.update(
        SYNC_USER1="test:test",
        SYNC_HOST="127.0.0.1",
        SYNC_PORT=str(PORT),
        SYNC_BASE=base,
        RUST_LOG="error",
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", "from anki.syncserver import run_sync_server; run_sync_server()"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
            return proc
        except Exception:
            time.sleep(0.25)
    proc.terminate()
    raise SystemExit("sync server did not come up")


def _attempts_snapshot(col) -> dict:
    snap = {}
    for cid in col.find_cards("tag:mcat-question"):
        c = col.get_card(cid)
        if c.custom_data:
            snap[str(c.id)] = c.custom_data
    return snap


def main() -> int:
    from anki.collection import Collection

    work = tempfile.mkdtemp()
    server = _start_server(os.path.join(work, "syncbase"))
    try:
        pA = os.path.join(work, "A.anki2")
        pB = os.path.join(work, "B.anki2")

        # Collection A: seed + practice a spread of questions.
        a = Collection(pA)
        a._backend.speedrun_seed_builtin()
        for i, cid in enumerate(list(a.find_cards("tag:mcat-question"))[:24]):
            a._backend.speedrun_record_attempt(card_id=cid, correct=(i % 3 != 0))
        scores_a = str(a._backend.speedrun_scores())
        concepts_a = a.get_config("speedrunConcepts", {})
        points_a = a.get_config("speedrunTopicPoints", {})
        snap_a = _attempts_snapshot(a)
        auth = a.sync_login("test", "test", ENDPOINT)
        a.full_upload_or_download(auth=auth, server_usn=None, upload=True)
        a.close()

        # Collection B: fresh, pull from the server.
        b = Collection(pB)
        auth_b = b.sync_login("test", "test", ENDPOINT)
        b.full_upload_or_download(auth=auth_b, server_usn=None, upload=False)
        try:
            b.close()
        except Exception:
            pass
        b = Collection(pB)
        scores_b = str(b._backend.speedrun_scores())
        concepts_b = b.get_config("speedrunConcepts", {})
        points_b = b.get_config("speedrunTopicPoints", {})
        snap_b = _attempts_snapshot(b)
        b.close()

        checks = [
            ("per-topic strength (concept FSRS)", concepts_a == concepts_b),
            ("topic points", points_a == points_b),
            ("per-question attempt logs", snap_a == snap_b),
            ("three scores identical", scores_a == scores_b),
        ]
        ok = True
        for name, passed in checks:
            print(f"[{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        print(f"\nsynced {len(concepts_b)} concepts, {len(snap_b)} attempted questions")
        return 0 if ok else 1
    finally:
        server.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
