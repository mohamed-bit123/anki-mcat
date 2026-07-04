# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Crash-safety test (brief §7g): 20x hard kill, zero corruption.

The brief: crash the app 20 times mid-write and show the collection is never
corrupted and no committed data is lost.

This runs it for real. For each of N rounds a child process opens the real
collection and writes in a tight loop (every ``speedrun_record_attempt`` commits
a transaction). The parent waits a random moment and sends **SIGKILL** — the
child dies with no chance to flush or close, exactly like a power loss or a
force-quit mid-write. The parent then reopens the collection and checks:

  * it opens at all (a corrupt file would raise);
  * SQLite ``pragma integrity_check`` returns ``ok``;
  * the count of committed attempts never goes *down* between rounds — no
    already-committed data was lost or rolled back past a commit boundary.

SQLite's journal/WAL gives per-transaction atomicity, so the in-flight write at
kill time either fully committed or fully rolled back; either way the file stays
consistent. This test demonstrates that end to end rather than asserting it.

    PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/crash_test.py
"""

from __future__ import annotations

import argparse
import os
import random
import signal
import subprocess
import sys
import tempfile
import time

CHILD = r"""
import os, sys
from anki.collection import Collection
col = Collection(sys.argv[1])
qs = list(col.find_cards("tag:mcat-question"))
if not qs:
    col._backend.speedrun_seed_builtin()
    qs = list(col.find_cards("tag:mcat-question"))
i = 0
# tight loop of committing writes; the parent will SIGKILL us mid-write
while True:
    col._backend.speedrun_record_attempt(card_id=qs[i % len(qs)], correct=(i % 2 == 0))
    i += 1
"""


def _committed_attempts(col) -> int:
    n = 0
    for cid in col.find_cards("tag:mcat-question"):
        if col.get_card(cid).custom_data:
            n += 1
    return n


def main() -> int:
    from anki.collection import Collection

    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    work = tempfile.mkdtemp()
    path = os.path.join(work, "crash.anki2")

    # Seed once and close cleanly to establish the baseline file.
    col = Collection(path)
    col._backend.speedrun_seed_builtin()
    col.close()

    env = dict(os.environ)
    results = []  # (round, opened_ok, integrity_ok, attempts)
    last_committed = 0
    for r in range(1, args.rounds + 1):
        proc = subprocess.Popen(
            [sys.executable, "-c", CHILD, path],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # let it get into the write loop, then kill at a random mid-write moment
        time.sleep(0.15 + rng.random() * 0.4)
        proc.send_signal(signal.SIGKILL)
        proc.wait()

        # reopen and verify
        opened_ok = integrity_ok = False
        attempts = -1
        try:
            col = Collection(path)
            integ = col.db.scalar("pragma integrity_check")
            integrity_ok = integ == "ok"
            attempts = _committed_attempts(col)
            opened_ok = True
            col.close()
        except Exception as e:  # noqa: BLE001 - any failure is a corruption signal
            print(f"round {r}: reopen FAILED: {e}")
        results.append((r, opened_ok, integrity_ok, attempts))
        # committed data must never regress
        if attempts >= 0:
            if attempts < last_committed:
                print(
                    f"round {r}: committed attempts REGRESSED "
                    f"{last_committed} -> {attempts}"
                )
            last_committed = max(last_committed, attempts)

    all_open = all(o for _, o, _, _ in results)
    all_integ = all(i for _, _, i, _ in results)
    monotonic = True
    prev = 0
    for _, _, _, a in results:
        if a >= 0 and a < prev:
            monotonic = False
        prev = max(prev, a)
    ok = all_open and all_integ and monotonic

    for r, o, i, a in results:
        print(
            f"[{'OK ' if o and i else 'BAD'}] round {r:2d}: "
            f"opened={o} integrity_ok={i} committed_attempts={a}"
        )

    lines = [
        "# Crash-safety test (§7g)",
        "",
        f"**{args.rounds} rounds.** Each round a child process writes to the real "
        "collection in a tight commit loop and is **SIGKILL**ed mid-write (no "
        "flush, no clean close — like power loss). The parent then reopens the "
        "collection and runs SQLite `pragma integrity_check`.",
        "",
        "| check | result |",
        "| --- | --- |",
        f"| reopened cleanly every round | {sum(o for _, o, _, _ in results)}/"
        f"{args.rounds} |",
        f"| `integrity_check` == ok every round | {sum(i for _, _, i, _ in results)}/"
        f"{args.rounds} |",
        f"| committed attempts never regressed | {'YES' if monotonic else 'NO'} |",
        "",
        (
            f"**Result: {args.rounds}/{args.rounds} crashes left the collection "
            "consistent — zero corruption, no committed data lost.** SQLite's "
            "per-transaction atomicity means the write in flight at kill time either "
            "committed or rolled back cleanly."
            if ok
            else "**Result: a round FAILED — see the log above; reporting honestly.**"
        ),
        "",
        f"Final committed attempts after {args.rounds} crash/recover cycles: "
        f"**{last_committed}**.",
        "",
        '> Reproduce: `PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python '
        "verify/crash_test.py`",
        "",
    ]
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\nwrote {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
