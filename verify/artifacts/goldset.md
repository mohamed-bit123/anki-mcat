# AI gold set vs. baselines (§7f)

Gold set: **50 held-out MCAT questions** with hand-authored answer keys (seed 11), grounded on the built-in flashcard bank per topic. Ship cutoff: **AI accuracy >= 80% and > both baselines.**

| method                          |   accuracy | wrong-answer rate |
| ------------------------------- | ---------: | ----------------: |
| keyword search (baseline)       |      36.0% |             64.0% |
| TF-IDF vector search (baseline) |      60.0% |             40.0% |
| **AI (gpt-4o-mini)**            | **100.0%** |              0.0% |

**Result: AI clears the cutoff and beats both baselines** — 100.0% vs the best simpler method at 60.0% (+40.0 pts), error rate 0.0%.

> Reproduce (baselines): `out/pyenv/bin/python verify/goldset.py --out verify/artifacts/goldset.md`\
> Reproduce (with AI): add `--use-ai` and set `OPENAI_API_KEY`.
