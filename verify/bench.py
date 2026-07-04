# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Latency benchmark for the MCAT Speedrun engine actions.

Measures the hot-path engine RPCs against the speed targets in
``speedrun/PLAN.md`` (§7) and reports p50 / p95 / worst per action, with a
PASS/FAIL vs. the target. Runs fully headless on a freshly-seeded collection.

Run with the built engine on the path (from repo root):

    PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/bench.py

Options:
    --iters N     iterations per action (default 300)
    --cards N     pad the collection to N total cards before benchmarking
                  (e.g. --cards 50000 for the brief's §7h/§10 large-deck run)
    --out FILE    also write a Markdown report to FILE
"""

from __future__ import annotations

import argparse
import os
import resource
import statistics
import tempfile
import time

# action -> (p95 target in ms, human description). Targets mirror PLAN.md §7.
TARGETS = {
    "record_attempt (button-press ack)": (50.0, "grade one practice question"),
    "next_question (next card after grading)": (
        100.0,
        "pick the next question via concept-FSRS",
    ),
    "scores refresh (dashboard refresh)": (
        500.0,
        "recompute Memory/Performance/Readiness",
    ),
}
# Seeding is a one-time content-setup action; reported for context, no hard gate.
SEED_TARGET_MS = 5000.0


def _pct(samples_ms: list[float], q: float) -> float:
    s = sorted(samples_ms)
    if not s:
        return 0.0
    idx = min(len(s) - 1, int(round(q * (len(s) - 1))))
    return s[idx]


def _fmt_row(
    name: str, samples: list[float], target_ms: float | None
) -> tuple[str, bool]:
    p50 = _pct(samples, 0.50)
    p95 = _pct(samples, 0.95)
    worst = max(samples)
    mean = statistics.fmean(samples)
    if target_ms is None:
        verdict = "—"
        ok = True
    else:
        ok = p95 < target_ms
        verdict = f"{'PASS' if ok else 'FAIL'} (<{target_ms:.0f}ms)"
    row = (
        f"| {name} | {p50:.2f} | {p95:.2f} | {worst:.2f} | {mean:.2f} | "
        f"{len(samples)} | {verdict} |"
    )
    return row, ok


def _time_calls(fn, iters: int) -> list[float]:
    out = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000.0)
    return out


def _maxrss_mb() -> float:
    # ru_maxrss is bytes on macOS, kilobytes on Linux.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if os.uname().sysname == "Darwin" else rss / 1024


def _pad_to(col, target_cards: int) -> tuple[int, float]:
    """Bulk-add filler Basic notes until the collection has >= target_cards, so
    the hot-path RPCs are measured against a large deck. Returns (total, secs)."""
    existing = col.card_count()
    if target_cards <= existing:
        return existing, 0.0
    basic = col.models.by_name("Basic")
    deck_id = col.decks.id("Speedrun Bench Filler")
    t0 = time.perf_counter()
    n_new = target_cards - existing
    col.models.set_current(basic)
    for i in range(n_new):
        note = col.new_note(basic)
        note.fields[0] = f"bench front {i}"
        note.fields[1] = f"bench back {i}"
        col.add_note(note, deck_id)
    secs = time.perf_counter() - t0
    return col.card_count(), secs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--cards", type=int, default=0, help="pad collection to N cards")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from anki.collection import Collection

    path = os.path.join(tempfile.mkdtemp(), "bench.anki2")
    col = Collection(path)

    rows: list[str] = []
    all_ok = True

    # --- one-time: seed the full built-in bank -------------------------------
    t0 = time.perf_counter()
    col._backend.speedrun_seed_builtin()
    seed_ms = (time.perf_counter() - t0) * 1000.0

    # --- optional: pad to a large deck (§7h/§10) -----------------------------
    pad_secs = 0.0
    total_cards = col.card_count()
    if args.cards:
        total_cards, pad_secs = _pad_to(col, args.cards)

    qcards = list(col.find_cards("tag:mcat-question"))

    # Dashboard first load (cold): the first-ever scores computation, before any
    # cache is warm. §10 target: p95 < 1000 ms (single cold sample here).
    t0 = time.perf_counter()
    col._backend.speedrun_scores()
    first_load_ms = (time.perf_counter() - t0) * 1000.0

    # Warm the caches so we measure steady-state, not first-touch.
    for cid in qcards[:20]:
        col._backend.speedrun_record_attempt(card_id=cid, correct=True)
    col._backend.speedrun_scores()
    col._backend.speedrun_next_question()

    # --- record_attempt ------------------------------------------------------
    cyc = qcards or [0]
    counter = {"i": 0}

    def do_record():
        cid = cyc[counter["i"] % len(cyc)]
        counter["i"] += 1
        col._backend.speedrun_record_attempt(
            card_id=cid, correct=(counter["i"] % 2 == 0)
        )

    samples = _time_calls(do_record, args.iters)
    row, ok = _fmt_row(
        "record_attempt (button-press ack)",
        samples,
        TARGETS["record_attempt (button-press ack)"][0],
    )
    rows.append(row)
    all_ok = all_ok and ok

    # --- next_question -------------------------------------------------------
    samples = _time_calls(lambda: col._backend.speedrun_next_question(), args.iters)
    row, ok = _fmt_row(
        "next_question (next card after grading)",
        samples,
        TARGETS["next_question (next card after grading)"][0],
    )
    rows.append(row)
    all_ok = all_ok and ok

    # --- scores refresh ------------------------------------------------------
    samples = _time_calls(lambda: col._backend.speedrun_scores(), args.iters)
    row, ok = _fmt_row(
        "scores refresh (dashboard refresh)",
        samples,
        TARGETS["scores refresh (dashboard refresh)"][0],
    )
    rows.append(row)
    all_ok = all_ok and ok

    maxrss_mb = _maxrss_mb()
    col.close()

    first_load_ok = first_load_ms < 1000.0
    all_ok = all_ok and first_load_ok

    header = (
        "| action | p50 (ms) | p95 (ms) | worst (ms) | mean (ms) | n | vs target |\n"
        "|---|---|---|---|---|---|---|"
    )
    seed_line = (
        f"\nOne-time content seed (`speedrun_seed_builtin`, {len(qcards)} questions + "
        f"flashcards): **{seed_ms:.0f} ms** (target < {SEED_TARGET_MS:.0f} ms cold-start budget)."
    )
    deck_line = (
        f"\nDeck size benchmarked: **{total_cards:,} cards**"
        + (f" (padded in {pad_secs:.1f}s)." if pad_secs else " (built-in bank).")
        + f" Peak memory (maxrss): **{maxrss_mb:.0f} MB**."
    )
    first_load_line = (
        f"\nDashboard first load (cold, single sample): **{first_load_ms:.1f} ms** "
        f"({'PASS' if first_load_ok else 'FAIL'} < 1000 ms)."
    )
    report = "\n".join(
        [
            "# MCAT Speedrun — latency artifact",
            "",
            f"Machine: {os.uname().sysname} {os.uname().machine}. "
            f"Iterations/action: {args.iters}. Headless, freshly-seeded collection.",
            "Targets from `speedrun/PLAN.md` §7 / brief §10 (report p50/p95/worst).",
            "",
            header,
            *rows,
            first_load_line,
            deck_line,
            seed_line,
            "",
            f"**Overall: {'PASS' if all_ok else 'FAIL'}** "
            "(every gated action's p95 is under its target).",
            "",
            'Reproduce: `PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python '
            "verify/bench.py [--cards 50000]`",
        ]
    )

    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
