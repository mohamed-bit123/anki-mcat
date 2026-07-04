# Leakage check (§7e)

Train set: `rslib/src/speedrun/mcat_flashcards.tsv` (210 items). Test set: `rslib/src/speedrun/mcat_questions.tsv` (105 items). Leak threshold: shingle Jaccard/containment ≥ 0.8.

- **Flagged near-duplicates: 0**
- Highest similarity found between any test item and any train item: **0.667**

**Result: CLEAN — no test item leaks into training.**

> Reproduce: `out/pyenv/bin/python verify/leakage.py --out verify/artifacts/leakage.md`
