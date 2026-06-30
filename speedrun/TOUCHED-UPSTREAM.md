# Speedrun — Touched Upstream Files Ledger

Required deliverable + drives the merge-difficulty note. Log EVERY file that
shipped with upstream Anki and that we modify. New files we create (e.g. under
`speedrun/`, `rslib/src/speedrun/`, `proto/anki/speedrun.proto`) do NOT belong
here — only edits to pre-existing upstream files.

Goal: keep this list short. Prefer new modules + thin registration hooks.

| Upstream file | Why we touched it | Merge risk | Notes |
| --- | --- | --- | --- |
| `proto/anki/scheduler.proto` | Added `SpeedrunPing` RPC to `SchedulerService` (Phase 0 pipeline-validation probe). | low | Purely additive: one rpc line at end of the service block. Conflict only if upstream edits the same trailing lines. |
| `rslib/src/scheduler/service/mod.rs` | Implemented `speedrun_ping()` for `SchedulerService for Collection`. | low | Purely additive method inside the impl block; mirrors `studied_today`. |
| `.gitignore` | Added `mobile/` so the nested AnkiDroid checkout isn't tracked by the fork. | low | One line. |

## Merge-difficulty summary (update as the list grows)

So far only additive edits at the proto service + its Rust impl (the unavoidable
seam for any new backend RPC), plus a one-line `.gitignore`. No upstream logic
rewritten. Future merges should be trivial. Strategy holds: confine real logic to
new modules; touch upstream only at registration points.
