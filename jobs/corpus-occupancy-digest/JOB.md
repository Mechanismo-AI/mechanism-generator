# Job corpus-occupancy-digest: pooled occupancy-width digest over corpus-07

**Purpose.** Menu item B of the corpus evidence arc: one digest over every
candidate row of the corpus-07 screened runs (runs/sync-corpus-07), pooling
per-region occupancy windows into classes (never / quick_pass / drag_over_cap
/ full360 / invalid) and reading the class-geometry story: is occupancy class
set by zone placement relative to the pivots, or by link ratios?

**Run (maintainer-local, from the repo root).**

```sh
. .venv/bin/activate
python jobs/corpus-occupancy-digest/digest_b.py
```

Reads runs/sync-corpus-07; writes gitignored runs/analysis/occupancy-digest-01/
(occupancy_digest.csv, digest_summary.json, digest_report.txt). Fail-closed:
aborts on missing sidecars or columns rather than skipping rows.

## Prediction scorecard (written before the run)

- Tallies reproduce the recorded corpus-07 constants fail-closed: 12 tasks,
  per-task 42 rows except 01/catcher 38 and 05/gate 41; pooled never 53,
  quick_pass 192, drag_over_cap 246, full360 8, invalid 0.
- Prediction from the corpus-05 evidence: occupancy class is decided mainly
  by zone placement relative to the pivots; link ratios fine-tune within,
  not between, tasks. Falsifier: a class boundary that appears in
  link-ratio space across tasks.

## Recorded outcome (after the run, 2026-10-15)

Ran clean first time: 499 pre-dedup candidate rows, 12 tasks, zero invalid
rows, tallies and pooled classes PASS.

- Median zone clearance (zone edge to nearest of O2/O4/ground segment):
  never 1.44 / quick_pass 1.02 / drag_over_cap 0.92 / full360 0.06 --
  degenerates sit the zone on the pivot line.
- Median crank ratio l2/l1: never 0.58 vs drag_over_cap 0.40 (shorter cranks
  dwell, longer cranks overshoot).
- Every class median has negative Grashof margin: the corpus is dominated
  by non-Grashof double-rockers; full360 rows are links folding across a
  zone-on-pivot, not a rotating crank.
- Between-task class mixes are extreme (pair_02 gate 42/42 drag; pair_06
  gate 24/42 never; pair_01 gate 8 never + 7 full360): variant-level zone
  placement sets the mix; candidate-level link ratios only fine-tune.

Story confirmed. Follow-on jobs: corpus-geometry-maps (class axes),
corpus-timeline-animator (windows in time), corpus-frame-sweep (frame
reproduction).
