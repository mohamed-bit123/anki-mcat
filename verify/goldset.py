# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""AI gold set + baseline comparison (brief §7f / §2, required).

The brief: *every AI output must be checked against a test set and beat a
simpler method (keyword or vector search)*, with the numbers reported before
students see anything — accuracy, wrong-answer rate, and a stated cutoff.

Task. Answer 50 held-out MCAT questions (single best answer) grounded only in
the built-in flashcard bank for the question's topic. We compare three methods
on the **same** 50-item gold set:

  * **keyword** baseline — pick the option with the most content-word overlap
    with the topic's source facts (a bag-of-words "look it up in my notes");
  * **vector** baseline — TF-IDF over the source facts, pick the option whose
    (stem+option) text has the highest cosine to any fact (retrieval answering);
  * **AI** — ``gpt-4o-mini`` answers the question, grounded on the same facts.

The gold set's answer keys are the hand-authored built-in keys — real ground
truth, held out from any generation. We report accuracy and wrong-answer rate
for each method and apply a **ship cutoff**: the AI arm is only acceptable if
its accuracy is >= ``--cutoff`` (default 0.80) *and* it beats both baselines.

The two baselines are deterministic and run offline, so a reviewer can
reproduce them with no key. The AI arm runs only when a key is available
(``OPENAI_API_KEY`` or the local ``~/.mcat_speedrun/openai_key`` file, never in
the repo); without one the script prints the baselines and notes the AI arm was
skipped.

    # baselines only (offline):
    out/pyenv/bin/python verify/goldset.py --out verify/artifacts/goldset.md
    # full comparison (uses your key):
    OPENAI_API_KEY=sk-... out/pyenv/bin/python verify/goldset.py --use-ai \
        --out verify/artifacts/goldset.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLASHCARDS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_flashcards.tsv"
QUESTIONS_TSV = ROOT / "rslib" / "src" / "speedrun" / "mcat_questions.tsv"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

_STOP = set(
    "the a an of to and or is are in on for with as by at from that this it its "
    "be which into during than then when what why how much many most more less "
    "will would can could may might do does you your they their them these those "
    "not no if but so we our us also each per via between within".split()
)


def _tok(text: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9]+", text.lower())
        if w not in _STOP and len(w) > 2
    ]


def _load_rows(path: Path, min_cols: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= min_cols:
            rows.append(cols)
    return rows


def _facts_by_topic() -> dict[str, list[str]]:
    by: dict[str, list[str]] = {}
    for r in _load_rows(FLASHCARDS_TSV, 3):
        by.setdefault(r[0], []).append(f"{r[1]} {r[2]}")
    return by


# --- baselines --------------------------------------------------------------


def keyword_answer(stem: str, opts: dict[str, str], facts: list[str]) -> str:
    fact_words = Counter(w for f in facts for w in _tok(f))
    best, best_score = "A", -1.0
    for letter, text in opts.items():
        score = sum(fact_words.get(w, 0) for w in _tok(text))
        if score > best_score:
            best, best_score = letter, score
    return best


def _tfidf(facts: list[str]) -> tuple[list[dict[str, float]], dict[str, float]]:
    docs = [_tok(f) for f in facts]
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    n = len(docs) or 1
    idf = {w: math.log((1 + n) / (1 + df[w])) + 1.0 for w in df}
    vecs = []
    for d in docs:
        tf = Counter(d)
        vecs.append(
            {w: (c / len(d)) * idf.get(w, 0.0) for w, c in tf.items()} if d else {}
        )
    return vecs, idf


def _cos(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def vector_answer(stem: str, opts: dict[str, str], facts: list[str]) -> str:
    vecs, idf = _tfidf(facts)
    best, best_score = "A", -1.0
    for letter, text in opts.items():
        q = Counter(_tok(stem + " " + text))
        qvec = {w: (c / max(1, len(q))) * idf.get(w, 0.0) for w, c in q.items()}
        score = max((_cos(qvec, v) for v in vecs), default=0.0)
        if score > best_score:
            best, best_score = letter, score
    return best


# --- AI arm -----------------------------------------------------------------


def _api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key.strip()
    path = os.path.join(os.path.expanduser("~"), ".mcat_speedrun", "openai_key")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip() or None
    return None


def ai_answer(
    model: str, key: str, stem: str, opts: dict[str, str], facts: list[str]
) -> str:
    facts_block = "\n".join(f"- {f}" for f in facts[:30]) or "(none)"
    options = "\n".join(f"{k}. {v}" for k, v in opts.items())
    prompt = (
        f"Answer this MCAT question using the source facts and standard reasoning.\n\n"
        f"SOURCE FACTS:\n{facts_block}\n\nQuestion:\n{stem}\n\nOptions:\n{options}\n\n"
        'Return JSON: {"answer":"A"|"B"|"C"|"D"}.'
    )
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a careful MCAT test-taker. Return ONLY JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode())
    content = payload["choices"][0]["message"]["content"]
    return str(json.loads(content).get("answer", "")).strip().upper()[:1] or "A"


# --- harness ----------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="gold-set size")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument(
        "--cutoff", type=float, default=0.80, help="ship threshold for AI accuracy"
    )
    ap.add_argument(
        "--use-ai", action="store_true", help="also run the AI arm (needs a key)"
    )
    ap.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = _load_rows(QUESTIONS_TSV, 7)
    gold = rng.sample(rows, min(args.n, len(rows)))
    facts_by = _facts_by_topic()

    methods = ["keyword", "vector"]
    key = _api_key() if args.use_ai else None
    run_ai = bool(key)
    if run_ai:
        methods.append("ai")

    correct = {m: 0 for m in methods}
    for r in gold:
        topic, stem = r[0], r[1]
        opts = {"A": r[2], "B": r[3], "C": r[4], "D": r[5]}
        gold_key = r[6].strip().upper()[:1]
        facts = facts_by.get(topic, [])
        preds = {
            "keyword": keyword_answer(stem, opts, facts),
            "vector": vector_answer(stem, opts, facts),
        }
        if run_ai:
            try:
                preds["ai"] = ai_answer(args.model, key, stem, opts, facts)
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                KeyError,
                ValueError,
            ):
                preds["ai"] = "A"
        for m in methods:
            if preds[m] == gold_key:
                correct[m] += 1

    n = len(gold)
    acc = {m: correct[m] / n for m in methods}

    lines = [
        "# AI gold set vs. baselines (§7f)",
        "",
        f"Gold set: **{n} held-out MCAT questions** with hand-authored answer keys "
        f"(seed {args.seed}), grounded on the built-in flashcard bank per topic. "
        f"Ship cutoff: **AI accuracy >= {args.cutoff:.0%} and > both baselines.**",
        "",
        "| method | accuracy | wrong-answer rate |",
        "| --- | ---: | ---: |",
        f"| keyword search (baseline) | {acc['keyword'] * 100:.1f}% | "
        f"{(1 - acc['keyword']) * 100:.1f}% |",
        f"| TF-IDF vector search (baseline) | {acc['vector'] * 100:.1f}% | "
        f"{(1 - acc['vector']) * 100:.1f}% |",
    ]
    if run_ai:
        lines.append(
            f"| **AI ({args.model})** | **{acc['ai'] * 100:.1f}%** | "
            f"{(1 - acc['ai']) * 100:.1f}% |"
        )
    lines.append("")

    ok = True
    if run_ai:
        beats = acc["ai"] > acc["keyword"] and acc["ai"] > acc["vector"]
        meets = acc["ai"] >= args.cutoff
        ok = beats and meets
        best_base = max(acc["keyword"], acc["vector"])
        lines.append(
            (
                f"**Result: AI clears the cutoff and beats both baselines** — "
                f"{acc['ai'] * 100:.1f}% vs the best simpler method at "
                f"{best_base * 100:.1f}% (+{(acc['ai'] - best_base) * 100:.1f} pts), "
                f"error rate {(1 - acc['ai']) * 100:.1f}%."
                if ok
                else f"**Result: cutoff NOT cleared** (AI {acc['ai'] * 100:.1f}%, cutoff "
                f"{args.cutoff:.0%}, best baseline {best_base * 100:.1f}%) — "
                "reported honestly; the AI arm would be gated off until fixed."
            )
        )
    else:
        lines.append(
            "_AI arm skipped (no key found). The two baselines above are the "
            "offline-reproducible reference; run with `--use-ai` and a key set to "
            "produce the AI row and the beats-baseline verdict._"
        )
    lines += [
        "",
        "> Reproduce (baselines): `out/pyenv/bin/python verify/goldset.py "
        "--out verify/artifacts/goldset.md`  ",
        "> Reproduce (with AI): add `--use-ai` and set `OPENAI_API_KEY`.",
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"wrote {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
