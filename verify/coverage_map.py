# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Coverage vs. the official MCAT outline (brief §7c / §4 "% of exam covered").

The readiness score is only honest if it knows how much of the exam it has
actually seen. This maps the built-in bank against the **official AAMC MCAT
content outline** (``speedrun/mcat_outline.tsv``, one row per content category)
and reports, per section and overall, what fraction of content categories the
bank covers — plus the specific gaps, which are the "single best next thing to
build" the brief asks for.

Matching is keyword-based and therefore approximate (a category counts as
covered when at least ``--min-cards`` bank cards contain one of its outline
keywords); we label it as such rather than overclaiming. CARS is a skills
section with no content, so it is excluded from the content-coverage math.

    out/pyenv/bin/python verify/coverage_map.py --out verify/artifacts/coverage.md
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTLINE_TSV = ROOT / "speedrun" / "mcat_outline.tsv"
FLASHCARDS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_flashcards.tsv"
QUESTIONS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_questions.tsv"


def _rows(path: Path, min_cols: int) -> list[list[str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= min_cols:
            out.append(cols)
    return out


def _bank_texts() -> list[str]:
    texts = []
    for r in _rows(FLASHCARDS_TSV, 3):
        texts.append(f"{r[1]} {r[2]}".lower())
    for r in _rows(QUESTIONS_TSV, 7):
        texts.append(" ".join(r[1:6]).lower())
    return texts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--min-cards",
        type=int,
        default=3,
        help="bank cards matching a category's keywords to count it covered",
    )
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    outline = _rows(OUTLINE_TSV, 5)
    texts = _bank_texts()

    # section_code -> list of (code, name, covered_bool, hit_count)
    sections: dict[str, list] = {}
    section_names: dict[str, str] = {}
    for sec_code, sec_name, cat_code, cat_name, keywords in (
        (r[0], r[1], r[2], r[3], r[4]) for r in outline
    ):
        section_names[sec_code] = sec_name
        terms = [t.strip().lower() for t in keywords.split(",") if t.strip()]
        hits = 0
        for txt in texts:
            if any(re.search(r"\b" + re.escape(term), txt) for term in terms):
                hits += 1
        covered = hits >= args.min_cards
        sections.setdefault(sec_code, []).append((cat_code, cat_name, covered, hits))

    # CARS excluded from content coverage (skills section).
    content_secs = [s for s in sections if s != "CARS"]
    total = sum(len(sections[s]) for s in content_secs)
    covered_total = sum(1 for s in content_secs for _, _, c, _ in sections[s] if c)

    lines = [
        "# Coverage vs. the official MCAT outline (§7c)",
        "",
        f"Bank: **{len(texts)} cards** (flashcards + questions) matched by keyword "
        f"against the official AAMC content outline "
        f"(`speedrun/mcat_outline.tsv`, {total} content categories across "
        f"{len(content_secs)} content sections; CARS is skills-only and excluded). "
        "Keyword matching is approximate — a category counts as covered when at "
        f"least {args.min_cards} bank card(s) hit its outline terms.",
        "",
        f"## Overall content coverage: **{covered_total}/{total} "
        f"({covered_total / total * 100:.0f}%)**",
        "",
        "| section | covered / total | % |",
        "| --- | ---: | ---: |",
    ]
    for s in content_secs:
        cov = sum(1 for _, _, c, _ in sections[s] if c)
        tot = len(sections[s])
        lines.append(f"| {section_names[s]} | {cov}/{tot} | {cov / tot * 100:.0f}% |")

    gaps = [
        f"{code} {name}"
        for s in content_secs
        for code, name, c, _ in sections[s]
        if not c
    ]
    lines += [
        "",
        "### Gaps (next content to build)",
        "",
    ]
    if gaps:
        lines += [f"- {g}" for g in gaps]
    else:
        lines.append("- none — every content category has at least one bank card.")
    lines += [
        "",
        "This percentage is exactly what the readiness score reports as "
        '"% of the exam covered" and why it withholds a confident number until '
        "coverage is high — see `rslib/src/speedrun/scores.rs`.",
        "",
        "> Reproduce: `out/pyenv/bin/python verify/coverage_map.py "
        "--out verify/artifacts/coverage.md`",
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
