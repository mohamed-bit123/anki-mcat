# Performance model — held-out accuracy

Held-out **7800 attempts on questions never seen in training** (train attempts: 28200). Predicts applied-correct from topic mastery, difficulty, and timing. Attempts simulated with partial memory→application transfer; see docstring.

| model                 |  accuracy |   AUC | Brier |
| --------------------- | --------: | ----: | ----: |
| **performance model** | **0.629** | 0.676 | 0.232 |
| memory-only baseline  |     0.570 | 0.594 | 0.268 |
| majority class        |     0.468 |     — |     — |

**Held-out accuracy: 62.9%.** The performance model beats the memory-only predictor (0.629 vs 0.570 accuracy, 0.232 vs 0.268 Brier) — evidence it captures the memory→application gap rather than echoing memory.

> Reproduce: `out/pyenv/bin/python verify/performance_eval.py --out verify/artifacts/performance.md`
