# Coverage vs. the official MCAT outline (§7c)

Bank: **315 cards** (flashcards + questions) matched by keyword against the official AAMC content outline (`speedrun/mcat_outline.tsv`, 31 content categories across 3 content sections; CARS is skills-only and excluded). Keyword matching is approximate — a category counts as covered when at least 3 bank card(s) hit its outline terms.

## Overall content coverage: **29/31 (94%)**

| section                                                       | covered / total |    % |
| ------------------------------------------------------------- | --------------: | ---: |
| Biological and Biochemical Foundations                        |             8/9 |  89% |
| Chemical and Physical Foundations                             |            9/10 |  90% |
| Psychological, Social, and Biological Foundations of Behavior |           12/12 | 100% |

### Gaps (next content to build)

- 2B Structure and integrative functions of organ systems
- 5C Separation and purification methods

This percentage is exactly what the readiness score reports as "% of the exam covered" and why it withholds a confident number until coverage is high — see `rslib/src/speedrun/scores.rs`.

> Reproduce: `out/pyenv/bin/python verify/coverage_map.py --out verify/artifacts/coverage.md`
