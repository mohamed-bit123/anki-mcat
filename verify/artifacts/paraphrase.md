# Paraphrase test — memory vs performance gap (§7d)

Real bank: 210 flashcards and 105 application questions across 7 topics. Recall = memory on the card; Applied = accuracy on reworded, same-idea questions (2 per idea). Responses simulated with partial transfer; see docstring.

| topic             | cards | questions |  recall% | applied% |       gap |
| ----------------- | ----: | --------: | -------: | -------: | --------: |
| Biochemistry      |    30 |        15 |     69.2 |     58.1 |     +11.1 |
| Biology           |    30 |        15 |     69.8 |     56.8 |     +13.0 |
| General Chemistry |    30 |        15 |     62.8 |     54.0 |      +8.8 |
| Organic Chemistry |    30 |        15 |     67.4 |     56.0 |     +11.4 |
| Physics           |    30 |        15 |     65.6 |     56.1 |      +9.5 |
| Psychology        |    30 |        15 |     71.4 |     57.2 |     +14.2 |
| Sociology         |    30 |        15 |     65.6 |     53.4 |     +12.2 |
| **overall**       |     — |         — | **67.4** | **55.9** | **+11.5** |

**Gap: 11.5 points** (67.4% recall vs 55.9% applied). Interpretation: a real gap — the reworded questions are _not_ just echoing card recall, so Performance measures something Memory does not.

> Reproduce: `out/pyenv/bin/python verify/paraphrase.py --out verify/artifacts/paraphrase.md`
