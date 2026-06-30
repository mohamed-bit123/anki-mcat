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
| `.gitignore` | Added `mobile/` so the nested AnkiDroid checkout isn't tracked by the fork. | low | Now stale: mobile checkouts were MOVED to `../anki-mcat-mobile/` (outside this repo) to avoid a yarn `.yarnrc.yml` config-bleed conflict (see JOURNAL 2026-06-30 Stage B). Harmless. |

## Mobile checkouts (separate repos, in `/Users/mohamedshawgi/anki-mcat-mobile/`)

Not part of this git repo, but tracked here for the merge-difficulty story.

| Repo / file | Why we touched it | Merge risk | Notes |
| --- | --- | --- | --- |
| `Anki-Android-Backend` @ `f9b78ba` (`0.1.64-anki25.09.2`), `anki` submodule `proto/anki/scheduler.proto` | Same additive `SpeedrunPing` RPC as desktop, on the 25.09.2 base used by the mobile backend. | low | Identical 3-line additive edit; re-apply on submodule bumps. |
| ⤷ `anki` submodule `rslib/src/scheduler/service/mod.rs` | Same additive `speedrun_ping()` impl. | low | Identical additive method. |
| `Anki-Android` `AnkiDroid/src/main/java/com/ichi2/anki/DeckPicker.kt` | Tagged hook in `onFinishedStartup()`: snackbar + `SPEEDRUN` log of `getBackend().speedrunPing()` — makes the engine change visible on the phone. | low | ~6 lines, clearly commented `// Speedrun (MCAT fork)`. Demo/proof only; remove or gate behind debug later. |
| `Anki-Android` `local.properties` | `local_backend=true` so AnkiDroid loads our locally-built `.aar` instead of the Maven one. | n/a | Untracked dev config, not committed upstream. |

## Merge-difficulty summary (update as the list grows)

Desktop: additive edits at the proto service + its Rust impl (the unavoidable seam
for any new backend RPC), plus a one-line `.gitignore`. Mobile: the same additive
engine edit on the 25.09.2 backend base, plus one tiny AnkiDroid UI hook (proof
only) and a dev-only `local.properties` flag. No upstream logic rewritten. Future
merges should be trivial. Strategy holds: confine real logic to new modules; touch
upstream only at registration points.
