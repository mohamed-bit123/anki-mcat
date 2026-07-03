# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Held-out evaluation harness for AI MCAT question generation.

This is the "prove yourself wrong" step for the AI features. It runs fully
offline of the app (only Python stdlib + your OpenAI key) and reports two
honest numbers:

1. **Verifier calibration** — how trustworthy is the independent answer-checker?
   We take a held-out sample of the *built-in* questions (whose correct answers
   are known ground truth), hide the answer key, and ask the checker model to
   answer them blind. Its accuracy vs. the known keys is the ceiling on how much
   we can trust the checker to police generated items.

2. **Generation pass rate** — of freshly generated questions (grounded in the
   built-in flashcards), what fraction survive the independent verifier? Low
   pass rates mean the generator (or model) needs work before you trust it.

Usage:
    OPENAI_API_KEY=sk-...  python3 speedrun/ai_eval.py \
        --subject Biochemistry --calib 20 --generate 10 [--model gpt-4o-mini]

Nothing here is committed with a key; the key comes from the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLASHCARDS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_flashcards.tsv"
QUESTIONS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_questions.tsv"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

GEN_SYSTEM = (
    "You are an MCAT item writer. You write rigorous, single-best-answer, "
    "application/reasoning questions grounded in the provided facts, with exactly "
    "one unambiguous correct option. Return ONLY JSON."
)
VERIFY_SYSTEM = (
    "You are a meticulous MCAT answer checker. Independently determine the single "
    "best answer WITHOUT being told the proposed key. Return ONLY JSON."
)


def chat(model: str, messages: list[dict], temperature: float) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Set OPENAI_API_KEY in the environment first.")
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"OpenAI error {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    return payload["choices"][0]["message"]["content"]


def load_rows(path: Path, min_cols: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= min_cols:
            rows.append(cols)
    return rows


def verify(model: str, stem: str, options: dict[str, str]) -> tuple[str, bool, str]:
    opts = "\n".join(f"{k}. {v}" for k, v in options.items())
    prompt = (
        f"Question:\n{stem}\n\nOptions:\n{opts}\n\n"
        'Return JSON: {"best_answer":"A"|"B"|"C"|"D","single_correct":true|false,'
        '"issue":str}.'
    )
    data = json.loads(
        chat(
            model,
            [
                {"role": "system", "content": VERIFY_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            0.0,
        )
    )
    return (
        str(data.get("best_answer", "")).strip().upper()[:1],
        bool(data.get("single_correct", False)),
        str(data.get("issue", "")).strip(),
    )


def run_calibration(model: str, n: int, subject: str | None) -> None:
    rows = load_rows(QUESTIONS_TSV, 8)
    if subject:
        rows = [r for r in rows if r[0].lower() == subject.lower()]
    if not rows:
        print("No held-out questions found for calibration.")
        return
    sample = random.sample(rows, min(n, len(rows)))
    correct = 0
    single = 0
    print(f"\n=== Verifier calibration on {len(sample)} held-out built-in questions ===")
    for r in sample:
        topic, stem, a, b, c, d, ans = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        options = {"A": a, "B": b, "C": c, "D": d}
        best, is_single, _issue = verify(model, stem, options)
        if is_single:
            single += 1
        if best == ans.strip().upper()[:1]:
            correct += 1
    print(f"Checker matched the known answer key: {correct}/{len(sample)} "
          f"({correct / len(sample) * 100:.0f}%)")
    print(f"Checker judged 'single correct answer': {single}/{len(sample)} "
          f"({single / len(sample) * 100:.0f}%)")
    print("Interpretation: the first number is how much you can trust the "
          "independent verifier to police generated items.")


def gen_prompt(subject: str, n: int, facts: list[str]) -> str:
    facts_block = "\n".join(f"[{i}] {f}" for i, f in enumerate(facts)) or "(none)"
    return (
        f"Subject: MCAT {subject}\n\nSOURCE FACTS:\n{facts_block}\n\n"
        f"Write {n} new MCAT-style single-best-answer questions grounded in these "
        f'facts. Return JSON {{"questions":[{{"stem":str,"options":'
        f'{{"A":str,"B":str,"C":str,"D":str}},"answer":"A".."D","explanation":str,'
        f'"source_fact_index":int}}]}}.'
    )


def run_generation(model: str, n: int, subject: str) -> None:
    fc = [r for r in load_rows(FLASHCARDS_TSV, 3) if r[0].lower() == subject.lower()]
    if not fc:
        print(f"No built-in flashcards for subject '{subject}' to ground on.")
        return
    facts = [f"{r[1]} -> {r[2]}" for r in fc][:40]
    content = chat(
        model,
        [
            {"role": "system", "content": GEN_SYSTEM},
            {"role": "user", "content": gen_prompt(subject, n, facts)},
        ],
        0.8,
    )
    items = json.loads(content).get("questions", [])
    print(f"\n=== Generation pass rate for {subject} ({len(items)} generated) ===")
    valid = 0
    passed = 0
    for it in items:
        stem = str(it.get("stem", "")).strip()
        options = {k: str(it.get("options", {}).get(k, "")).strip() for k in "ABCD"}
        answer = str(it.get("answer", "")).strip().upper()[:1]
        if not stem or not all(options.values()) or answer not in "ABCD":
            continue
        valid += 1
        best, single, issue = verify(model, stem, options)
        ok = single and best == answer
        if ok:
            passed += 1
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] key={answer} checker={best} single={single} "
              f"{('· ' + issue) if issue and not ok else ''}")
    if valid:
        print(f"\nStructurally valid: {valid}/{len(items)}")
        print(f"Independently verified: {passed}/{valid} "
              f"({passed / valid * 100:.0f}%)")
    else:
        print("No structurally valid questions were produced.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", default="Biochemistry",
                    help="MCAT subject to generate/calibrate on")
    ap.add_argument("--calib", type=int, default=15,
                    help="held-out built-in questions to test the verifier on")
    ap.add_argument("--generate", type=int, default=8,
                    help="new questions to generate and verify")
    ap.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    random.seed(args.seed)

    print(f"Model: {args.model}")
    if args.calib:
        run_calibration(args.model, args.calib, args.subject)
    if args.generate:
        run_generation(args.model, args.generate, args.subject)


if __name__ == "__main__":
    main()
