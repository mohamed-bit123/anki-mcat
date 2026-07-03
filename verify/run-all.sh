#!/usr/bin/env bash
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# One-command verification for the MCAT Speedrun fork. Produces every artifact a
# reviewer needs — build, test, latency, sync — under verify/artifacts/.
#
# Usage (from repo root):
#   bash verify/run-all.sh
#
# Prerequisites: the engine must be buildable (see speedrun/TESTING.md). This
# script builds it, then runs the MCAT test suites, the sync round-trip, and the
# latency benchmark, capturing each to a text artifact.

set -u
cd "$(dirname "$0")/.."
ART="verify/artifacts"
mkdir -p "$ART"
PYENV="out/pyenv/bin/python"
export PYTHONPATH="pylib:qt:out/pylib:out/qt"

section() { echo; echo "==== $* ===="; }
have_engine() { [ -x "$PYENV" ] && [ -d "out/pylib/anki" ]; }

section "1/5 build engine (just build)"
if command -v just >/dev/null 2>&1; then
  just build 2>&1 | tee "$ART/build.log" | tail -n 3
else
  echo "just not found — skipping build (assuming out/ already built)" | tee "$ART/build.log"
fi

if ! have_engine; then
  echo "ERROR: built engine not found under out/. Run 'just build' first." >&2
  exit 1
fi

section "2/5 Rust engine tests (cargo test -p anki speedrun)"
cargo test -p anki speedrun:: --lib 2>&1 | tee "$ART/tests-rust.txt" | tail -n 4

section "3/5 Python end-to-end tests"
"$PYENV" -m pytest -q \
  pylib/tests/test_speedrun.py \
  pylib/tests/test_speedrun_scores.py \
  pylib/tests/test_speedrun_seed.py 2>&1 | tee "$ART/tests-python.txt" | tail -n 4

section "4/5 desktop<->mobile sync round-trip"
"$PYENV" speedrun/sync_check.py 2>&1 | tee "$ART/sync.txt" | tail -n 6

section "5/5 latency benchmark (p50/p95/worst vs targets)"
"$PYENV" verify/bench.py --iters 300 --out "$ART/latency.md" 2>&1 | tail -n 14

echo
echo "All artifacts written to $ART/"
ls -1 "$ART"
