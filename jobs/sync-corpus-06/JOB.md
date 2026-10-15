# Job sync-corpus-06: the capstone anchor-probe pass

**Purpose.** The follow-up to the sync-corpus-05 capstone: decide, per
variant, whether any per-task anchor offset can satisfy the authored
constraints and the shared-zone keep-out together. The G5 anchor probe
rotates a task's derived region windows and points along with its phases,
so sweeping each anchor across the whole master cycle reports the offset
intervals where at least one candidate combination passes everything.

**Key fact.** Two of them. The engine search is region-blind, so the
per-task engine results of the earlier corpus runs remain exact here:
with `--results-from runs/sync-corpus-03` only validate, adapt, and
verify run. And the probe sweeps on top of declared offsets, so this job
deliberately declares none: the driver runs without `--offsets`, and the
probe reports absolute offsets. (Corpus-05 ran with the corpus-04
offsets; a variant that verified there can fail at the offset-free
baseline because its passing combos depended on the applied offset.)

**Expected outcomes are data, not promises.** The probe is diagnostic:
probing never changes the verdict, and occupancy remains sampled, never
certified. A variant with a feasible interval shows phasing can repair
it; a variant with no feasible interval for either anchor shows the
keep-out conflict is structural to the candidate sets, and no re-timing
of one arm can fix it.

## Run

```sh
. .venv/bin/activate
python jobs/sync-corpus-01/corpus_run.py \
  --document examples/omts/collision_pair.omts.yaml \
  --results-from runs/sync-corpus-03 \
  --output-dir runs/sync-corpus-06
for v in 01 02 03 04 05 06; do
  python -m mechanism_generator.omts verify-line \
    --probe-anchors runs/sync-corpus-06/corpus_pair_$v/plan
done
```

The default probe step is 1 deg. The probe overwrites each variant's
`plan/line_result.json` with the probe version (verdict unchanged, data
only), which is why the output directory must be fresh. Variants with no
candidate combinations are skipped by the probe and recorded as such.

## Reporting back

Per variant: the baseline verdict, and per anchor the best
passing-combination count and the feasible offset intervals from the
`anchor_probe` section of `line_result.json` (the probe also prints them
to the console). The reading that matters: which variants have no
feasible interval for either anchor.

## Recorded outcome (maintainer-local run, 2026-10-15; sampled
occupancy, never certified)

Variant 01 (the identity transform) has a feasible catcher interval with
several passing combinations, and the corpus-04 applied offset sits inside
it; variants 02, 03, and 04 have no feasible offset for either anchor,
so their shared-zone conflicts are structural to the candidate sets;
variant 05 is skipped (no candidates); variant 06 (the negative control)
has no feasible offsets either. Read together with the corpus-05
per-combination record (every authored-passing combination in the
flipped variants overlaps the zone), this exhausts clearance tuning and
phasing there: search-time zone awareness is the remaining lever
(collision draft, section 6).
