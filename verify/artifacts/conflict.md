# Offline conflict merge (§7b)

Two devices reviewed overlapping cards **offline** (A=12 reviews, B=18 reviews on the same first cards) and practiced disjoint question sets, then synced through Anki's self-hosted server.

| check                                                  | result |
| ------------------------------------------------------ | ------ |
| reviews merged with no loss (union=30, A=30, B=30)     | PASS   |
| no double-counted reviews (counts == union size)       | PASS   |
| both devices converge to identical MCAT state + scores | PASS   |

- Union of all reviews from both devices: **30**. After the merge both devices hold exactly that many revlog rows — **0 lost, 0 double-counted** (revlog is append-only, keyed by ms id).
- B's merge sync completed as a normal incremental merge and finished with `required=NO_CHANGES` — no full-sync/overwrite was forced, so neither device's offline work was discarded wholesale.
- Practice attempts on _different_ cards merged cleanly — both devices converged to identical MCAT concept FSRS, topic points, attempt logs, and the three scores.
- **Documented edge case:** attempts live in each card's `custom_data` (one JSON field). Two offline edits to the _same_ question resolve last-writer-wins by card mod time — the losing device's concurrent same-card attempt is dropped. Reviews are unaffected (append-only revlog). Zero-loss for that rare case would require moving attempts to an append-only synced log.

> Reproduce: `PYTHONPATH="pylib:out/pylib" out/pyenv/bin/python verify/conflict_check.py`
