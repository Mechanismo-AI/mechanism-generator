#!/bin/sh
# sync-pair-eval-01: adapt + run the synchronized pair example.
# Run from the repository root with the engine virtualenv active.
set -eu

OUT=runs/sync-pair-01

omts validate examples/omts/synchronized_pair.omts.yaml
omts adapt examples/omts/synchronized_pair.omts.yaml --output-dir "$OUT"
python "$OUT/run_r25c.py" --models-directory models --check-only
python "$OUT/run_r25c.py" --models-directory models "$@"

echo "Done. Collect from $OUT/results/task-00{1,2} for the S4 verifier."
