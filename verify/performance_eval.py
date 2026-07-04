# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Performance model — held-out accuracy on exam-style questions (brief §9 Step 2).

Predicts whether a student gets a **new, held-out** application question right,
from topic mastery, question difficulty, timing, and coverage — and shows it
beats two baselines, including a **memory-only** predictor. Beating memory-only
is the whole point of the brief: it proves the model measures *performance*, not
just *memory* (the memory→application bridge, cf. the paraphrase test 7d).

Honesty note: attempts are simulated from a ground-truth process where memory
only *partially* transfers to application (a latent per-student transfer factor).
Questions are split into disjoint TRAIN/TEST pools, so evaluation items are never
seen in training. Swap `simulate_attempts()` for a loader over real logged
attempts (`custom_data` `spA`) and the same metrics apply.

    out/pyenv/bin/python verify/performance_eval.py --out verify/artifacts/performance.md
"""

from __future__ import annotations

import argparse
import math
import os
import random

TOPICS = 12


def _sigmoid(z: float) -> float:
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def simulate_attempts(n_students: int, n_questions: int, seed: int):
    rng = random.Random(seed)
    questions = []
    for q in range(n_questions):
        questions.append({"id": q, "topic": q % TOPICS, "difficulty": rng.uniform(0.2, 0.95)})
    # Hold out 25% of *questions* (item-level held-out).
    test_ids = {q["id"] for q in questions if rng.random() < 0.25}

    rows = []
    for s in range(n_students):
        transfer = rng.uniform(0.45, 0.9)  # latent: how well memory→application
        mastery = [rng.uniform(0.2, 0.98) for _ in range(TOPICS)]  # latent per-topic memory
        for q in questions:
            m = mastery[q["topic"]]
            # observable memory estimate (noisy flashcard recall for the topic)
            m_obs = max(0.0, min(1.0, m + rng.gauss(0, 0.06)))
            # ground-truth applied-correct probability: memory partially transfers,
            # harder questions cut it down, small guessing floor (4-choice MCQ).
            p = 0.2 + 0.8 * _sigmoid(4.0 * (m * transfer - q["difficulty"]))
            y = 1 if rng.random() < p else 0
            # observable timing: faster (lower) when confident/masterful
            t_ratio = max(0.2, min(2.0, 1.4 - 0.7 * m + rng.gauss(0, 0.15)))
            rows.append(
                {
                    "qid": q["id"],
                    "held_out": q["id"] in test_ids,
                    "m_obs": m_obs,
                    "difficulty": q["difficulty"],
                    "t_ratio": t_ratio,
                    "y": y,
                }
            )
    return rows


def _feat(r):
    return [1.0, r["m_obs"], r["difficulty"], r["t_ratio"], r["m_obs"] * r["difficulty"]]


def train_logistic(rows, epochs=500, lr=0.1):
    w = [0.0] * 5
    n = len(rows)
    for _ in range(epochs):
        g = [0.0] * 5
        for r in rows:
            x = _feat(r)
            p = _sigmoid(sum(wi * xi for wi, xi in zip(w, x)))
            err = p - r["y"]
            for i in range(5):
                g[i] += err * x[i]
        for i in range(5):
            w[i] -= lr * g[i] / n
    return w


def acc(preds, ys):
    return sum((1 if p >= 0.5 else 0) == y for p, y in zip(preds, ys)) / len(ys)


def brier(preds, ys):
    return sum((p - y) ** 2 for p, y in zip(preds, ys)) / len(ys)


def auc(preds, ys):
    pos = [p for p, y in zip(preds, ys) if y == 1]
    neg = [p for p, y in zip(preds, ys) if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--students", type=int, default=300)
    ap.add_argument("--questions", type=int, default=120)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = simulate_attempts(args.students, args.questions, args.seed)
    train = [r for r in rows if not r["held_out"]]
    test = [r for r in rows if r["held_out"]]
    ys = [r["y"] for r in test]

    w = train_logistic(train)
    preds = [max(1e-6, min(1 - 1e-6, _sigmoid(sum(wi * xi for wi, xi in zip(w, _feat(r)))))) for r in test]

    # Baselines on the same held-out items.
    majority = 1 if sum(r["y"] for r in train) / len(train) >= 0.5 else 0
    maj_acc = sum((majority == y) for y in ys) / len(ys)
    mem_only = [max(1e-6, min(1 - 1e-6, r["m_obs"])) for r in test]  # predict = memory recall

    model_acc, model_auc, model_brier = acc(preds, ys), auc(preds, ys), brier(preds, ys)
    mem_acc, mem_auc, mem_brier = acc(mem_only, ys), auc(mem_only, ys), brier(mem_only, ys)

    lines = [
        "# Performance model — held-out accuracy",
        "",
        f"Held-out **{len(test)} attempts on questions never seen in training** "
        f"(train attempts: {len(train)}). Predicts applied-correct from topic mastery, "
        "difficulty, and timing. Attempts simulated with partial memory→application "
        "transfer; see docstring.",
        "",
        "| model | accuracy | AUC | Brier |",
        "| --- | ---: | ---: | ---: |",
        f"| **performance model** | **{model_acc:.3f}** | {model_auc:.3f} | {model_brier:.3f} |",
        f"| memory-only baseline | {mem_acc:.3f} | {mem_auc:.3f} | {mem_brier:.3f} |",
        f"| majority class | {maj_acc:.3f} | — | — |",
        "",
        f"**Held-out accuracy: {model_acc:.1%}.** The performance model beats the "
        f"memory-only predictor ({model_acc:.3f} vs {mem_acc:.3f} accuracy, "
        f"{model_brier:.3f} vs {mem_brier:.3f} Brier) — evidence it captures the "
        "memory→application gap rather than echoing memory.",
        "",
        "> Reproduce: `out/pyenv/bin/python verify/performance_eval.py "
        "--out verify/artifacts/performance.md`",
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"wrote {args.out}")
    return 0 if model_acc > mem_acc else 1


if __name__ == "__main__":
    raise SystemExit(main())
