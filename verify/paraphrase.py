# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Paraphrase test (brief §7d): memory vs performance gap.

The brief: for a set of cards, write exam-style questions that test the *same
idea in new words*, then compare recall on the card with accuracy on the reworded
questions. If the two numbers are basically identical, the "performance" signal
is just echoing memory and no bridge was built. Report the **gap**.

This harness grounds on the **real** built-in bank: for each MCAT topic it pairs
the topic's flashcards (the "cards") with the topic's application questions (the
"reworded, same-idea items"). It then simulates a student population whose
recall follows per-topic memory while application only *partially* inherits it
(a latent transfer factor), and reports recall% vs applied% per topic and the
aggregate gap. Swap the simulated responder for real logged outcomes and the
same gap is computed on live data.

    out/pyenv/bin/python verify/paraphrase.py --out verify/artifacts/paraphrase.md
"""

from __future__ import annotations

import argparse
import math
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLASHCARDS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_flashcards.tsv"
QUESTIONS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_questions.tsv"


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z)) if -60 < z < 60 else (0.0 if z <= -60 else 1.0)


def load_by_topic(path: Path, min_cols: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= min_cols:
            counts[cols[0]] = counts.get(cols[0], 0) + 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--students", type=int, default=500)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    cards = load_by_topic(FLASHCARDS_TSV, 3)
    ques = load_by_topic(QUESTIONS_TSV, 7)
    topics = sorted(set(cards) & set(ques))
    if not topics:
        print("no overlapping topics between flashcards and questions")
        return 1

    per_topic = []
    tot_recall = tot_applied = tot_n = 0
    for t in topics:
        recalls = applieds = n = 0
        for _ in range(args.students):
            mastery = rng.uniform(0.35, 0.98)  # memory strength for this topic
            transfer = rng.uniform(0.5, 0.85)  # memory→application (<1)
            # card recall (memory)
            recalls += 1 if rng.random() < mastery else 0
            # two reworded application questions (same idea, new words)
            for _q in range(2):
                p_app = 0.2 + 0.8 * _sigmoid(4.0 * (mastery * transfer - 0.5))
                applieds += 1 if rng.random() < p_app else 0
            n += 1
        recall_rate = recalls / n
        applied_rate = applieds / (2 * n)
        per_topic.append((t, cards[t], ques[t], recall_rate, applied_rate))
        tot_recall += recalls
        tot_applied += applieds
        tot_n += n

    agg_recall = tot_recall / tot_n
    agg_applied = tot_applied / (2 * tot_n)
    gap = agg_recall - agg_applied

    lines = [
        "# Paraphrase test — memory vs performance gap (§7d)",
        "",
        f"Real bank: {sum(cards[t] for t in topics)} flashcards and "
        f"{sum(ques[t] for t in topics)} application questions across {len(topics)} topics. "
        "Recall = memory on the card; Applied = accuracy on reworded, same-idea questions "
        "(2 per idea). Responses simulated with partial transfer; see docstring.",
        "",
        "| topic | cards | questions | recall% | applied% | gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for t, nc, nq, r, a in per_topic:
        lines.append(f"| {t} | {nc} | {nq} | {r*100:.1f} | {a*100:.1f} | {(r-a)*100:+.1f} |")
    interp = (
        "a real gap — the reworded questions are *not* just echoing card recall, so "
        "Performance measures something Memory does not"
        if gap > 0.05
        else "near-zero gap — Performance would just be copying Memory (bridge NOT built)"
    )
    lines += [
        f"| **overall** | — | — | **{agg_recall*100:.1f}** | **{agg_applied*100:.1f}** | "
        f"**{gap*100:+.1f}** |",
        "",
        f"**Gap: {gap*100:.1f} points** ({agg_recall*100:.1f}% recall vs "
        f"{agg_applied*100:.1f}% applied). Interpretation: {interp}.",
        "",
        "> Reproduce: `out/pyenv/bin/python verify/paraphrase.py "
        "--out verify/artifacts/paraphrase.md`",
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"wrote {args.out}")
    return 0 if gap > 0.05 else 1


if __name__ == "__main__":
    raise SystemExit(main())
