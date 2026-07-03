# Speedrun — persistent memory (START HERE)

This `speedrun/` folder is the project's durable memory. It exists so that an AI
agent (or a human) returning with **zero prior context** can rebuild the full
"train of thought" and keep going without losing decisions.

> If you are an agent and your context was just reset: read these files in order
> before doing anything else.

## Read order

1. **`PLAN.md`** — the mission, the locked decisions, the phased build plan, and
   the strategy for working in a huge codebase with a limited context window.
2. **`JOURNAL.md`** — append-only decision log / narrative of what was done and
   _why_. The newest entry at the bottom is the current state of the world.
3. **`REPO-MAP.md`** — where things live in the Anki tree (navigation index so we
   never re-explore from scratch).
4. **`TOUCHED-UPSTREAM.md`** — ledger of every upstream Anki file we modify
   (this is also a required project deliverable + drives merge-difficulty notes).

> **Verifying the project?** Go to [`../verify/`](../verify/README.md) — one place
> with build, installer, test, latency, and sync artifacts, all reproducible with
> `bash verify/run-all.sh`.

## How to maintain these (do this as you work)

- After any meaningful decision or milestone, **append a dated entry to
  `JOURNAL.md`**. Never rewrite history; only append.
- When you learn where something lives in Anki, **add it to `REPO-MAP.md`**.
- When you edit a file that shipped with upstream Anki, **log it in
  `TOUCHED-UPSTREAM.md`** immediately.
- `PLAN.md` is the only "living" doc you may edit in place (to update status),
  but record _why_ the plan changed in `JOURNAL.md`.

## One-paragraph project summary

Fork Anki; build an MCAT study app as a **desktop app + phone companion that
share one Rust engine** and sync. Show **three separate scores** (memory,
performance, readiness), each with a range and a give-up rule. Make a **real
change in Anki's Rust code**. Add AI (card generation + checking) that is
traceable, evaluated on held-out data, and beats a simple baseline — and the app
must still score with AI off. Prove everything with re-runnable, held-out tests.
**Honesty over flattery: a confident number with no evidence behind it is an
automatic fail.**
