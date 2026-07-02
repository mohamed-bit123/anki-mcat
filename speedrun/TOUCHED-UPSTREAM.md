# Speedrun — Touched Upstream Files Ledger

Required deliverable + drives the merge-difficulty note. Log EVERY file that
shipped with upstream Anki and that we modify. New files we create (e.g. under
`speedrun/`, `rslib/src/speedrun/`, `proto/anki/speedrun.proto`) do NOT belong
here — only edits to pre-existing upstream files.

Goal: keep this list short. Prefer new modules + thin registration hooks.

| Upstream file | Why we touched it | Merge risk | Notes |
| --- | --- | --- | --- |
| `proto/anki/scheduler.proto` | Added `SpeedrunPing` RPC (Phase 0); Phase 2 added `SpeedrunRecordAttempt`, `SpeedrunScores`, and `SpeedrunNextQuestions` RPCs + their request/response messages; content phase added `SpeedrunSeedBuiltin` RPC (`generic.UInt32`); concept-FSRS phase added `SpeedrunNextQuestion` RPC + `SpeedrunNextQuestionResponse` message. | low | Purely additive rpc + message blocks. Conflict only if upstream edits the same trailing lines. |
| `rslib/src/scheduler/service/mod.rs` | Implemented `speedrun_ping()` (Phase 0); Phase 2 added `speedrun_record_attempt()`, `speedrun_scores()`, `speedrun_next_questions()`; content phase added `speedrun_seed_builtin()`; concept-FSRS phase added `speedrun_next_question()`, each delegating to inherent `Collection` methods. | low | Purely additive methods inside the impl block; mirror `studied_today`. |
| `rslib/src/speedrun/content.rs` (fork file) | Concept-FSRS phase: `speedrun_record_attempt` now also advances the concept's FSRS state; `parse_attempts` made `pub(crate)` for reuse by `concepts.rs`. | n/a | Fork-owned file, not upstream. |
| `qt/aqt/main.py` | Phase 2 UI: added a "MCAT Speedrun…" `QAction` to the Tools menu in `setupMenus`, plus an `on_speedrun()` method opening the dialog. | low | ~8 additive lines at known registration points; all heavy UI lives in the new `qt/aqt/speedrun.py`. |
| `proto/anki/deck_config.proto` | Added `REVIEW_CARD_ORDER_SPEEDRUN_POINTS_AT_STAKE = 13` to the `ReviewCardOrder` enum (Phase 1 real change). | low | Additive enum value; new tag number, no renumbering. |
| `rslib/src/lib.rs` | Registered `pub mod speedrun;`. | low | One line; new module is all our code. |
| `rslib/src/storage/card/mod.rs` | Added the new `ReviewCardOrder` arm in `review_order_sql` (gathers urgent-first; reuses the `RelativeOverdueness` subclause). | low | One match arm; forced by exhaustiveness. |
| `rslib/src/scheduler/queue/builder/mod.rs` | Call `speedrun_reorder_reviews` in `build_queues` when the new order is set, + the method itself (now: points-at-stake scoring THEN topic interleaving via `interleave_order`), + 2 integration tests. | medium | ~65 lines incl. tests; the only place that reaches into the gathered review vec. Confined to one `if` + one private method. |
| `rslib/src/scheduler/fsrs/simulator.rs` | Added the new `ReviewCardOrder` arm to the simulator's priority fn (urgency*weakness). | low | One match arm; forced by exhaustiveness. |

New files (all ours, not upstream edits): `rslib/src/speedrun/{mod,queue,scores,content,seed}.rs` (ranking + topic interleaving + three-score models + practice-question logging + built-in MCAT flashcards, 31 unit tests), `qt/aqt/speedrun.py` (desktop question-runner + score panel + "Set up MCAT content"), `pylib/tests/{test_speedrun,test_speedrun_scores,test_speedrun_seed}.py` (Python end-to-end tests). The interleaving + built-in flashcards live entirely in `queue.rs`/`seed.rs` plus the one additive builder hook above; no new upstream files were touched for the content phase.

### Phase 1 — mobile (separate repo: `anki-mcat-mobile/Anki-Android-Backend/anki`, v25.09.2)
Same change mirrored into the mobile backend's anki submodule (not tracked by this repo):
- `proto/anki/deck_config.proto`: `REVIEW_CARD_ORDER_SPEEDRUN_POINTS_AT_STAKE = 13` (matches desktop).
- `rslib/src/lib.rs`: `pub mod speedrun;`.
- `rslib/src/speedrun/{mod,queue}.rs`: copied verbatim from desktop.
- `rslib/src/storage/card/mod.rs`: new arm uses `build_retrievability_clauses(fsrs, timing, SqlSortOrder::Ascending)` (25.09.2 lacks the RelativeOverdueness subclause).
- `rslib/src/scheduler/fsrs/simulator.rs`: new arm (urgency*weakness) before `Added | ReverseAdded => None`.
- `rslib/src/scheduler/queue/builder/mod.rs`: identical `build_queues` hook + `speedrun_reorder_reviews`.
| `.gitignore` | Added `mobile/` so the nested AnkiDroid checkout isn't tracked by the fork. | low | Now stale: mobile checkouts were MOVED to `../anki-mcat-mobile/` (outside this repo) to avoid a yarn `.yarnrc.yml` config-bleed conflict (see JOURNAL 2026-06-30 Stage B). Harmless. |

## Mobile checkouts (separate repos, in `/Users/mohamedshawgi/anki-mcat-mobile/`)

Not part of this git repo, but tracked here for the merge-difficulty story.

| Repo / file | Why we touched it | Merge risk | Notes |
| --- | --- | --- | --- |
| `Anki-Android-Backend` @ `f9b78ba` (`0.1.64-anki25.09.2`), `anki` submodule `proto/anki/scheduler.proto` | Same additive `SpeedrunPing` RPC as desktop, on the 25.09.2 base used by the mobile backend. | low | Identical 3-line additive edit; re-apply on submodule bumps. |
| ⤷ `anki` submodule `rslib/src/scheduler/service/mod.rs` | Same additive `speedrun_ping()` impl. | low | Identical additive method. |
| `Anki-Android` `AnkiDroid/src/main/java/com/ichi2/anki/DeckPicker.kt` | Tagged hook in `onFinishedStartup()`: snackbar + `SPEEDRUN` log of `getBackend().speedrunPing()` — makes the engine change visible on the phone. | low | ~6 lines, clearly commented `// Speedrun (MCAT fork)`. Demo/proof only; remove or gate behind debug later. |
| `Anki-Android` `local.properties` | `local_backend=true` so AnkiDroid loads our locally-built `.aar` instead of the Maven one. | n/a | Untracked dev config, not committed upstream. |

### Phase 2 — mobile (full parity)
Backend `anki` submodule (25.09.2): same additive edits as desktop —
`proto/anki/scheduler.proto` (+RecordAttempt/Scores/NextQuestions RPCs & messages),
`rslib/src/scheduler/service/mod.rs` (+3 impls). New files copied byte-identical from
desktop: `rslib/src/speedrun/{scores,content}.rs` and the Phase-2 additions to
`queue.rs`/`mod.rs`. AnkiDroid app edits (`Anki-Android`):
| Repo / file | Why we touched it | Merge risk | Notes |
| --- | --- | --- | --- |
| `AnkiDroid/.../SpeedrunActivity.kt` (NEW) | The whole mobile Speedrun screen (score panel + question runner). All new code. | none | Not an upstream file. |
| `AnkiDroid/.../DeckPicker.kt` | One `when` arm in `onOptionsItemSelected` launching `SpeedrunActivity` (plus the Phase-0 ping hook). | low | ~5 additive lines. |
| `AnkiDroid/src/main/AndroidManifest.xml` | Register `SpeedrunActivity`. | low | One additive `<activity>` block. |
| `AnkiDroid/src/main/res/menu/deck_picker.xml` + `menu-xlarge/deck_picker.xml` | Add the "MCAT Speedrun" overflow item. | low | One additive `<item>` each. |

### Content phase — built-in flashcards + interleaving (desktop + mobile)
Desktop new file `rslib/src/speedrun/seed.rs` (built-in MCAT bank + idempotent
`speedrun_seed_builtin`) and additive edits to `queue.rs` (`interleave_order` + tests),
the builder hook (interleave step), `scheduler.proto` (+`SpeedrunSeedBuiltin`),
`scheduler/service/mod.rs` (+impl), and `qt/aqt/speedrun.py` ("Set up MCAT content").
Mobile backend `anki` submodule (25.09.2): same `queue.rs`/builder/proto/service edits;
`seed.rs` copied byte-identical. AnkiDroid `SpeedrunActivity.kt`: added a "Set up MCAT
content" button calling `getBackend().speedrunSeedBuiltin()` (no other upstream files).

### Content scale-up + seeding unified in the engine (desktop + mobile)
`seed.rs` now bundles two TSVs via `include_str!` — `mcat_flashcards.tsv` (210 cards) and
`mcat_questions.tsv` (105 questions) — and `speedrun_seed_builtin` seeds BOTH flashcards
(`MCAT::<Topic>`) and questions (`MCAT Practice::<Topic>`, Rust-created "MCAT Practice
Question" notetype), idempotent, returning 315. Both TSVs are new engine-owned files
(desktop + mobile, byte-identical). UI simplified to a single "Set up MCAT content" button
on both platforms; the old per-platform demo seeders were **deleted** — Python
`SEED_QUESTIONS`/`ensure_notetype`/`seed_demo_questions` + "Seed demo questions" button in
`qt/aqt/speedrun.py`, and the Kotlin `SEED_QUESTIONS`/`seedDemoQuestions`/
`ensureQuestionNotetype`/`onSeed` + componentN helpers in `SpeedrunActivity.kt`. Net effect:
one source of truth in the engine; both apps ship the same 315-item bank.

## Merge-difficulty summary (update as the list grows)

Desktop: additive edits at the proto service + its Rust impl (the unavoidable seam
for any new backend RPC), plus a one-line `.gitignore`. Mobile: the same additive
engine edit on the 25.09.2 backend base, plus one tiny AnkiDroid UI hook (proof
only) and a dev-only `local.properties` flag. No upstream logic rewritten. Future
merges should be trivial. Strategy holds: confine real logic to new modules; touch
upstream only at registration points.
