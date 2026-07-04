# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Leakage check (brief §7e).

Scans a "training" text set against a "test" set and flags any test item — or a
near-copy of one — that appears in training. Leaked test data makes a model look
smarter than it is, so this must come back **clean**.

Default scan for this repo: the built-in **flashcards** are the source facts the
AI generator is grounded on (its "training"); the built-in **questions** are the
held-out evaluation items. We verify no question is a near-duplicate of a source
fact (which would mean the "application" item is really just the memorized fact).
Point `--train`/`--test` at any two TSVs to reuse it (e.g., an AI training corpus
vs. the gold set from `verify/goldset.py`).

Similarity = token-shingle Jaccard + containment on normalized text; a pair is a
leak if either exceeds the threshold (default 0.8).

    out/pyenv/bin/python verify/leakage.py --out verify/artifacts/leakage.md
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLASHCARDS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_flashcards.tsv"
QUESTIONS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_questions.tsv"

_WORD = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def shingles(tokens: list[str], k: int = 3) -> set:
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment(a: set, b: set) -> float:
    """Fraction of the smaller set contained in the other (near-copy detector)."""
    if not a or not b:
        return 0.0
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return len(small & big) / len(small)


def load_texts(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        # join the meaningful text columns (skip the leading topic label)
        out.append(" ".join(cols[1:]) if len(cols) > 1 else cols[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(FLASHCARDS_TSV))
    ap.add_argument("--test", default=str(QUESTIONS_TSV))
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    train = [shingles(normalize(t)) for t in load_texts(Path(args.train))]
    test_texts = load_texts(Path(args.test))
    test = [shingles(normalize(t)) for t in test_texts]

    flags = []
    max_sim = 0.0
    for i, ts in enumerate(test):
        worst = 0.0
        worst_j = -1
        for j, tr in enumerate(train):
            sim = max(jaccard(ts, tr), containment(ts, tr))
            if sim > worst:
                worst, worst_j = sim, j
        max_sim = max(max_sim, worst)
        if worst >= args.threshold:
            flags.append((i, worst_j, worst, test_texts[i][:80]))

    clean = not flags
    lines = [
        "# Leakage check (§7e)",
        "",
        f"Train set: `{os.path.relpath(args.train, ROOT)}` ({len(train)} items). "
        f"Test set: `{os.path.relpath(args.test, ROOT)}` ({len(test)} items). "
        f"Leak threshold: shingle Jaccard/containment ≥ {args.threshold}.",
        "",
        f"- **Flagged near-duplicates: {len(flags)}**",
        f"- Highest similarity found between any test item and any train item: **{max_sim:.3f}**",
        "",
        f"**Result: {'CLEAN — no test item leaks into training.' if clean else 'LEAKS FOUND (below).'}**",
    ]
    if flags:
        lines += ["", "| test item | max sim | preview |", "| --- | ---: | --- |"]
        for i, _j, sim, prev in flags[:20]:
            lines.append(f"| #{i} | {sim:.3f} | {prev} |")
    lines += [
        "",
        "> Reproduce: `out/pyenv/bin/python verify/leakage.py "
        "--out verify/artifacts/leakage.md`",
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"wrote {args.out}")
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
