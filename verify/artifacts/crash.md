# Crash-safety test (§7g)

**20 rounds.** Each round a child process writes to the real collection in a tight commit loop and is **SIGKILL**ed mid-write (no flush, no clean close — like power loss). The parent then reopens the collection and runs SQLite `pragma integrity_check`.

| check                               | result |
| ----------------------------------- | ------ |
| reopened cleanly every round        | 20/20  |
| `integrity_check` == ok every round | 20/20  |
| committed attempts never regressed  | YES    |

**Result: 20/20 crashes left the collection consistent — zero corruption, no committed data lost.** SQLite's per-transaction atomicity means the write in flight at kill time either committed or rolled back cleanly.

Final committed attempts after 20 crash/recover cycles: **105**.

> Reproduce: `PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/crash_test.py`
