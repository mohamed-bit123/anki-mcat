# The Rust engine change (brief §7a)

One page: what changed, why it belongs in Rust, the tests, the undo/corruption
proof, and how it reaches the phone. Touched-file ledger + merge risk lives in
[`TOUCHED-UPSTREAM.md`](TOUCHED-UPSTREAM.md).

## What changed

A new review order, **`REVIEW_CARD_ORDER_SPEEDRUN_POINTS_AT_STAKE`**, added to
Anki's scheduler. When selected, due reviews are reordered by **points at
stake = topic MCAT-yield × student weakness**, and then **interleaved across
topics** so no single subject dominates a session. It is a first-class
`ReviewCardOrder` enum value, wired through the queue builder, the storage sort,
and the FSRS simulator — the same seams Anki's own orders use.

- Enum + RPCs: `proto/anki/deck_config.proto`, `proto/anki/scheduler.proto`.
- Logic (all fork-owned modules): `rslib/src/speedrun/queue.rs`
  (`points_at_stake` scoring + `interleave_order`), called from
  `rslib/src/scheduler/queue/builder/mod.rs::build_queues`.
- Storage/simulator arms: `rslib/src/storage/card/mod.rs`,
  `rslib/src/scheduler/fsrs/simulator.rs`.
- Called from Python: `col._backend` RPCs (`speedrun_next_question`,
  `speedrun_record_attempt`, `speedrun_scores`, `speedrun_seed_builtin`).

## Why this belongs in Rust, not Python

1. **It runs inside the queue builder.** Card gathering, ordering, and the FSRS
   interval math already live in `rslib`. The order is applied where the queue
   is assembled; doing it in Python would mean pulling the gathered review set
   across the FFI boundary, reordering, and pushing it back every build — slow
   and fragile.
2. **One engine, two apps.** Because the change is in `rslib`, it ships
   unchanged to the desktop _and_ the Android build (compiled into the `.aar`).
   A Python-side reorder would not exist on the phone — violating the
   "share the engine, don't rewrite it" rule.
3. **Correctness + undo.** Reordering at the engine level keeps FSRS intervals
   valid and rides Anki's existing transaction/undo machinery. Attempt logging
   (`speedrun_record_attempt`) is a single atomic, undoable op.
4. **Speed at scale.** Sorting and the score queries stay in Rust/SQLite; the
   dashboard stays under target on 50k cards (see below).

## Tests (≥3 Rust unit + 1 Python + undo)

- **Rust unit tests: 40+ across `rslib/src/speedrun/`.** The change itself is
  covered in `queue.rs` (12 tests: e.g. `topic_points_scale_priority_linearly`,
  `weakness_breaks_ties_toward_harder_cards`,
  `interleave_never_repeats_a_topic_while_others_remain`,
  `interleave_leads_with_the_global_highest_priority`) plus 2 integration tests
  in `rslib/src/scheduler/queue/builder/mod.rs`.
- **Python end-to-end test** calling the change through the backend:
  `pylib/tests/test_speedrun.py::test_speedrun_points_at_stake_reorders_reviews`
  (sets the order, builds the queue via the real engine, asserts high-yield/weak
  cards come first). Plus `test_speedrun_scores.py`, `test_speedrun_seed.py`.
- Run: `cargo test -p anki speedrun::` and
  `pytest pylib/tests/test_speedrun*.py`. Captured in
  [`../verify/artifacts/tests-rust.txt`](../verify/artifacts/tests-rust.txt) and
  [`tests-python.txt`](../verify/artifacts/tests-python.txt).

## Undo works + no corruption

- **Undo**: `rslib/src/speedrun/content.rs::record_attempt_is_atomically_undoable`
  proves a single `undo()` reverts the _whole_ attempt (the attempt log entry
  **and** the concept-FSRS advance) as one atomic operation — no half-applied
  state. The queue reorder is read-only over the gathered set and does not alter
  answering/undo.
- **No corruption**: [`../verify/crash_test.py`](../verify/crash_test.py) SIGKILLs
  the process mid-write 20× and reopens with SQLite `pragma integrity_check` —
  **20/20 clean, no committed data lost**
  ([`crash.md`](../verify/artifacts/crash.md)).

## Ships to the phone

The identical `queue.rs`/builder/proto/storage/simulator edits are applied on the
mobile backend's `anki` submodule (v25.09.2) and compiled into the AnkiDroid
`.aar`; `SpeedrunActivity.kt` calls the same RPCs. See
[`TOUCHED-UPSTREAM.md`](TOUCHED-UPSTREAM.md) (mobile section).

## Merge difficulty

Real logic is confined to new `rslib/src/speedrun/` modules; upstream files get
only additive edits at unavoidable registration points (proto service + its Rust
impl, one enum value, one match arm each in storage/simulator, one `build_queues`
hook). Merge risk is **low** everywhere except the single builder hook
(**medium**, ~65 lines incl. tests). Full ledger in
[`TOUCHED-UPSTREAM.md`](TOUCHED-UPSTREAM.md).

## Speed on 50,000 cards

`verify/bench.py --cards 50000` → [`../verify/artifacts/latency-50k.md`](../verify/artifacts/latency-50k.md):
record_attempt p95 **0.47 ms**, next_question **7.7 ms**, scores refresh
**143 ms** (<500), cold dashboard first load **96 ms** (<1000), peak memory
**~82 MB**. All under target.
