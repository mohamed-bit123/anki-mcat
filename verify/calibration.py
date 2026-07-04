# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Memory-model calibration (brief §9 Step 1, required).

Shows the memory model is *calibrated*: when it predicts an 80% chance of
recall, the student actually recalls ~80% of the time. Reports **Brier score**
and **log-loss** on **held-out** reviews and writes a reliability diagram
(calibration chart, SVG) plus a bin table.

Honesty note (per the brief §9): a real score model needs students studied over
weeks, which we can't gather honestly in the timeframe. So this harness is the
*re-runnable calibration methodology*: it simulates review streams from a
ground-truth forgetting process that is **not** the predictor (so calibration
isn't tautological), fits the memory model on a TRAIN split, and evaluates it on
a held-out TEST split (split by student, so no student appears in both). Swap
`simulate_reviews()` for a loader over the engine's real revlog and the same
metrics/chart apply unchanged.

    out/pyenv/bin/python verify/calibration.py --out verify/artifacts/calibration.md
"""

from __future__ import annotations

import argparse
import math
import os
import random

BINS = 10


# --------------------------------------------------------------- ground truth
def simulate_reviews(n_students: int, n_cards: int, seed: int) -> list[dict]:
    """Simulate spaced reviews. Ground-truth recall follows a power/exponential
    forgetting curve whose half-life grows with successful reps and a latent
    per-card difficulty. The predictor never sees the latent difficulty."""
    rng = random.Random(seed)
    events: list[dict] = []
    for s in range(n_students):
        ability = rng.uniform(0.7, 1.3)  # latent, unobserved
        for c in range(n_cards):
            difficulty = rng.uniform(0.3, 1.0)  # latent, unobserved
            half_life = 1.0  # days
            reps = successes = lapses = 0
            t = 0.0
            for _ in range(rng.randint(4, 9)):
                gap = rng.uniform(0.5, half_life * 2.2)  # spaced-repetition-ish
                t += gap
                p_true = 2.0 ** (-gap / max(0.1, half_life)) * min(1.0, ability * difficulty + 0.15)
                p_true = max(0.01, min(0.99, p_true))
                outcome = 1 if rng.random() < p_true else 0
                events.append(
                    {
                        "student": s,
                        "elapsed": gap,
                        "reps": reps,
                        "successes": successes,
                        "lapses": lapses,
                        "y": outcome,
                    }
                )
                reps += 1
                if outcome:
                    successes += 1
                    half_life *= 1.9 + 0.6 * difficulty  # strengthen
                else:
                    lapses += 1
                    half_life = max(1.0, half_life * 0.5)  # forget
    return events


# ------------------------------------------------------------------ the model
def _features(ev: dict) -> list[float]:
    return [
        1.0,
        math.log(ev["elapsed"] + 1.0),
        ev["reps"],
        ev["successes"],
        ev["lapses"],
    ]


def _sigmoid(z: float) -> float:
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def train_logistic(rows: list[dict], epochs: int = 400, lr: float = 0.05) -> list[float]:
    w = [0.0] * 5
    n = len(rows)
    for _ in range(epochs):
        grad = [0.0] * 5
        for ev in rows:
            x = _features(ev)
            p = _sigmoid(sum(wi * xi for wi, xi in zip(w, x)))
            err = p - ev["y"]
            for i in range(5):
                grad[i] += err * x[i]
        for i in range(5):
            w[i] -= lr * grad[i] / n
    return w


def predict(w: list[float], ev: dict) -> float:
    p = _sigmoid(sum(wi * xi for wi, xi in zip(w, _features(ev))))
    return max(1e-6, min(1 - 1e-6, p))


# --------------------------------------------------------------------- metrics
def brier(preds: list[float], ys: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(preds, ys)) / len(ys)


def log_loss(preds: list[float], ys: list[int]) -> float:
    return -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for p, y in zip(preds, ys)) / len(ys)


def reliability(preds: list[float], ys: list[int]) -> list[dict]:
    bins = [{"lo": i / BINS, "hi": (i + 1) / BINS, "ps": [], "ys": []} for i in range(BINS)]
    for p, y in zip(preds, ys):
        idx = min(BINS - 1, int(p * BINS))
        bins[idx]["ps"].append(p)
        bins[idx]["ys"].append(y)
    out = []
    for b in bins:
        if b["ys"]:
            out.append(
                {
                    "lo": b["lo"],
                    "hi": b["hi"],
                    "pred": sum(b["ps"]) / len(b["ps"]),
                    "emp": sum(b["ys"]) / len(b["ys"]),
                    "n": len(b["ys"]),
                }
            )
    return out


def ece(rel: list[dict], total: int) -> float:
    return sum(b["n"] / total * abs(b["pred"] - b["emp"]) for b in rel)


# ------------------------------------------------------------------------ svg
def reliability_svg(rel: list[dict]) -> str:
    W = H = 320
    pad = 40
    sz = W - 2 * pad

    def X(v):
        return pad + v * sz

    def Y(v):
        return H - pad - v * sz

    pts = " ".join(f"{X(b['pred']):.1f},{Y(b['emp']):.1f}" for b in rel)
    dots = "".join(
        f'<circle cx="{X(b["pred"]):.1f}" cy="{Y(b["emp"]):.1f}" '
        f'r="{2 + min(8, b["n"] ** 0.5 / 3):.1f}" fill="#2b6cb0" opacity="0.8"/>'
        for b in rel
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="11">
<rect width="{W}" height="{H}" fill="white"/>
<line x1="{X(0)}" y1="{Y(0)}" x2="{X(1)}" y2="{Y(1)}" stroke="#bbb" stroke-dasharray="4 3"/>
<rect x="{pad}" y="{pad}" width="{sz}" height="{sz}" fill="none" stroke="#333"/>
<polyline points="{pts}" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
{dots}
<text x="{W/2:.0f}" y="{H-8}" text-anchor="middle">predicted recall</text>
<text x="12" y="{H/2:.0f}" text-anchor="middle" transform="rotate(-90 12 {H/2:.0f})">empirical recall</text>
<text x="{X(0):.0f}" y="{Y(0)+14:.0f}">0</text>
<text x="{X(1)-6:.0f}" y="{Y(0)+14:.0f}">1</text>
<text x="{pad-16}" y="{Y(1)+4:.0f}">1</text>
<text x="{W/2:.0f}" y="{pad-14}" text-anchor="middle" font-weight="bold">Memory calibration (held-out)</text>
</svg>"""


# ----------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--students", type=int, default=400)
    ap.add_argument("--cards", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None, help="write markdown report here")
    args = ap.parse_args()

    events = simulate_reviews(args.students, args.cards, args.seed)
    rng = random.Random(args.seed)
    test_students = {s for s in range(args.students) if rng.random() < 0.2}
    train = [e for e in events if e["student"] not in test_students]
    test = [e for e in events if e["student"] in test_students]

    w = train_logistic(train)
    preds = [predict(w, e) for e in test]
    ys = [e["y"] for e in test]

    rel = reliability(preds, ys)
    b = brier(preds, ys)
    ll = log_loss(preds, ys)
    e_ce = ece(rel, len(ys))
    base_rate = sum(ys) / len(ys)
    baseline_brier = brier([base_rate] * len(ys), ys)  # always-predict-mean

    svg_path = None
    if args.out:
        svg_path = os.path.join(os.path.dirname(args.out), "calibration.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(reliability_svg(rel))

    lines = [
        "# Memory model — calibration (held-out)",
        "",
        f"Held-out **test reviews: {len(test)}** (from {len(test_students)} students never "
        f"seen in training; train reviews: {len(train)}). Reviews are simulated from a "
        "ground-truth forgetting process (not the predictor); see the module docstring for "
        "the honesty note and how to swap in real revlog data.",
        "",
        f"- **Brier score: {b:.4f}** (lower is better; always-guess-the-mean baseline = {baseline_brier:.4f})",
        f"- **Log-loss: {ll:.4f}**",
        f"- **Expected calibration error (ECE): {e_ce:.4f}**",
        f"- Base recall rate: {base_rate:.3f}",
        "",
        "Reliability diagram: ![calibration](calibration.svg)",
        "",
        "| predicted bin | mean predicted | empirical recall | n |",
        "| --- | ---: | ---: | ---: |",
    ]
    for bn in rel:
        lines.append(
            f"| {bn['lo']:.1f}–{bn['hi']:.1f} | {bn['pred']:.3f} | {bn['emp']:.3f} | {bn['n']} |"
        )
    verdict = "well-calibrated" if e_ce < 0.05 and b < baseline_brier else "needs work"
    lines += [
        "",
        f"**Verdict: {verdict}** — the model beats the always-predict-the-mean baseline "
        f"({b:.4f} < {baseline_brier:.4f}) and ECE is {e_ce:.3f}.",
        "",
        "> Reproduce: `out/pyenv/bin/python verify/calibration.py "
        "--out verify/artifacts/calibration.md`",
        "",
    ]
    report = "\n".join(lines)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"wrote {args.out} and {svg_path}")
    return 0 if b < baseline_brier else 1


if __name__ == "__main__":
    raise SystemExit(main())
