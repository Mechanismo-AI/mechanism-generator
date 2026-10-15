# Job sync-corpus-05: the G5 capstone -- the pair sharing one zone

**Purpose.** The staged capstone exercise of the collision-geometry plan
(specs/omts/0.2/collision.md, section 7, item 5): rerun the synchronized
pair corpus with the pair sharing one keep-out zone, so the G5 line gating --
relations over derived region events -- is measured on real engine output.
The base document is `examples/omts/collision_pair.omts.yaml`: the
synchronized pair plus a circular `shared_zone` at the handoff, a collision
body model per task (link thickness 0.1, 720 samples), and a hard
`disjoint_windows` relation over `gate.occupies_region.shared_zone` and
`catcher.occupies_region.shared_zone` with `clearance: {phase: 10}`.

**Key fact.** The engine search is region-blind: regions and collision
bodies are post-hoc verification features, so the per-task engine results
of the earlier corpus runs are exact for this corpus too. With
`--results-from runs/sync-corpus-03` the whole corpus reuses those engine
trees and only validate, adapt, and verify run -- minutes, not hours. The
same offsets that corpus-04 reviewed are declared again, so the difference
between the corpus-04 and corpus-05 summaries is exactly the effect of the
keep-out relation.

**Expected outcomes are data, not promises.** A variant verifies only when
its combos pass the authored handoff and ordering constraints and every
sampled occupancy window pair clears the 10 deg keep-out. Failures,
touching windows, and even vacuously passing variants (an arm that never
reaches the transformed zone) are all legitimate results; occupancy is
sampled at 720 phases per task cycle and never certified. Variant 06 stays
the negative control: no offsets, expected unverified before and after the
zone.

## Run

```sh
. .venv/bin/activate
python jobs/sync-corpus-01/corpus_run.py \
  --document examples/omts/collision_pair.omts.yaml \
  --offsets jobs/sync-corpus-01/offsets-corpus-04.json \
  --results-from runs/sync-corpus-03 \
  --output-dir runs/sync-corpus-05
```

Output lands in `runs/sync-corpus-05/` with the corpus layout: per-variant
documents, plans, reused engine results, and `plan/line_result.json` (now
carrying the sampled occupancy section and the per-combo keep-out record
with its `min_gap_deg`), plus the `summary.json` comparison table.

A fresh engine pass (drop `--results-from`) is not required for the
capstone and costs hours; run one only if the reused trees are missing.

## Reporting back

Share `runs/sync-corpus-05/summary.json` plus each variant's
`line_result.json` collision section. The interesting readings: which
variants the keep-out flips from verified to failed, the recorded
`min_gap_deg` per combo, whether any candidate never occupies the zone at
all, and whether the negative control stayed unverified for the declared
reasons.
