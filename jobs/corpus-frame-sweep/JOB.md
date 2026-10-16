# Job corpus-frame-sweep: corpus-wide base-angle frame sweep

**Purpose.** The menu-E follow-up: upgrade the animator's 6-exemplar
screen-frame check to every candidate row. Each of the 499 corpus-07 rows
is re-resolved in both base-angle frames -- screen (base =
radians(base_angle), the recorded engine behavior) and plain (base as
stored; the control) -- and compared against the recorded window lists.
Recorded constants are checked fail-closed before any comparison: per-task
tallies (42 rows except 01/catcher 38 and 05/gate 41), pooled classes
(never 53, quick_pass 192, drag_over_cap 246, full360 8, invalid 0), steps
720, hard cap 60.0, method, disclaimer, screen shape. Any structural
anomaly aborts (exit 2) with nothing written. The resolver mirrors
src/mechanism_generator/engine/zone_screen.py::screen() operation-for-
operation in pure stdlib; the sweep was written from the engine source at
main 12badcb7 (engine files identical to f3ebca9a where corpus-07 ran; PR
#31 was docs-only).

**Run (maintainer-local, from the repo root).**

```sh
python jobs/corpus-frame-sweep/frame_sweep.py  # runs/analysis/frame-sweep-01/ (never overwrites; delete to rerun)
```

## Prediction scorecard (written before the run)

- **P0:** screen_exact 499/499 expected. Risk recorded in advance: rare
  1-ulp boundary flips reported as near-misses, not hidden.
- **P1:** plain_exact near 0 among occupied rows. Honest control caveats
  pre-recorded: the 53 never rows may match trivially in both frames; the
  8 full360 rows may match both (huge regions); near-zero base_angle rows
  coincide by construction. These are honest control outcomes, not
  refutations.
- **P2:** tallies 12/12 plus pooled classes plus internal consistency
  (recorded widths recomputed from recorded windows; acceptable flags vs
  sidecar criteria).

Verification before delivery: 36/36 harness checks on a synthetic fixture
(13 rows, 2 variants x 2 tasks): 32 tampers each asserting the fail-closed
abort (sidecar validation, stale partial run with a later timestamp, decoy
target dir, contribution bundle decoy, row consistency, tally/class flips,
out-dir-exists), plus positives and a perf probe (about 2 ms per 720-step
resolve, so the corpus sweep takes seconds). Run twice, deterministic.

## Recorded outcome (after the run, 2026-10-16)

The maintainer run on the-hub: 12/12 sidecars PASS, 499 rows read (tallies
PASS 12/12), pooled classes PASS, **screen frame 499/499 exact with zero
near-misses** -- the 1-ulp risk did not materialize; the menu-E observation
is corpus-wide fact. Plain-frame control: **1/499** -- corpus_pair_04/
catcher variable_005, class full360 (base_angle 4.2282 rad = 242.3 deg):
the zone is occupied over the full cycle in both frames, exactly the
pre-recorded trivial case; the near-zero-base caveat never triggered.
Per-class plain exact: never 0/53, quick_pass 0/192, drag_over_cap 0/246,
full360 1/8 -- every discriminating row separates the frames. Outputs
runs/analysis/frame-sweep-01/ (frame_sweep.csv, frame_sweep_summary.json,
frame_sweep_report.txt).
