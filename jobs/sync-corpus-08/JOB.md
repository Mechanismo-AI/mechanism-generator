# Job: sync-corpus-08 -- re-time probe over the screened corpus-07 pools

## Goal

Answer the follow-up question the corpus-07 capstone left open: can
offsets re-time the screened candidate pools? The anchor probe
(`omts verify-line --probe-anchors`) is pure post-processing over an
existing plan's results, so no engine rerun is needed -- and none is
possible: the corpus driver refuses `--results-from` for screened
documents, so the corpus-07 plans already contain the only screened
runs these pools will ever have.

## How to run (maintainer-local)

Probe copies of the corpus-07 plans; the probe overwrites
`plan/line_result.json`, so the corpus-07 plans stay pristine:

```
mkdir -p runs/sync-corpus-08/<variant>
cp -r runs/sync-corpus-07/<variant>/plan runs/sync-corpus-08/<variant>/plan
omts verify-line runs/sync-corpus-08/<variant>/plan --probe-anchors
```

Variants 02, 04, and 05 are skipped: they selected zero candidates
under the screen, so there is nothing to re-time.

## Prediction scorecard (written before the probe)

1. Variant 01 HAS feasible intervals: its verified state depends on
   the declared catcher offset, and the probe composes on top of
   declared offsets, so intervals around the declared pick are
   expected (they existed in the unscreened corpus-06 probe).
2. Variant 03 is the open question: the unscreened pools admitted
   no single-task offset for either anchor (corpus-06). Screening
   narrowed 03's pools but did not repair the line; the probe answers
   whether the NARROWED pools can be re-timed.
3. Variant 06: no feasible offsets (negative control; authored
   constraints fail far from any feasible offset band).

## Recorded outcome (after the probe, 2026-10-15)

Probed maintainer-local at a 1-degree step over copies of the
corpus-07 plan dirs:

- 01 (declared catcher 105): `LINE VERIFIED combinations=15
  passing=6`. Catcher feasible band [341..17] x6 in probe deltas
  (the probe composes on top of declared offsets) = absolute
  [86..122] -- identical to the unscreened corpus-06 band, but now
  carrying 6 passing combinations instead of 3: pool shaping
  doubled the passing combinations inside an unchanged feasible
  band. Gate (undeclared in 01, so its band is absolute): feasible
  offsets [359..22] x15 -- a small gate re-time ALONE admits all
  15 combinations with the catcher left at its declared offset.
  Scorecard 1: confirmed.
- 03 (declared catcher 333): `LINE FAILED combinations=25
  passing=0`; NO feasible offsets for either task in the screened
  pools. Combined with corpus-06 (no feasible offsets in the
  unscreened pools), single-task phasing is dead at both pool
  shapes for 03. Scorecard 2 resolves to "no" for single-task
  re-time.
- 06: no feasible offsets for either task. Scorecard 3: confirmed,
  negative control held.
- 02, 04, 05: skipped (zero selected candidates).

## Recorded confirm (2026-10-15, hand-declared)

The 01 upgrade path was confirmed end-to-end, maintainer-local, in a
scratch copy of variant 01's document (the corpus-07 plans stayed
pristine):

- gate `{phase: 10}` added to 01's declared offsets (mid-band in
  [359..22]) alongside the declared catcher 105;
- validate, adapt to a fresh plan dir, copy the corpus-07 variant-01
  `results/` tree in, `omts verify-line`;
- result: `LINE VERIFIED combinations=15 passing=15` -- the first
  fully passing line in the corpus series. The full chain for 01:
  3/15 passing (authored + keep-out, region-blind pools) -> 6/15
  (screened pools) -> 15/15 (screened pools + small gate re-time).
  No single lever sufficed; pool shaping and re-time together
  carried the line.

## Honesty notes

- The probe is a diagnostic: it changes no verdict and records
  feasible offset intervals as data; as ever, offsets break the
  reference-at-phase-zero rule unless physically realized.
- Occupancy is sampled, never certified (`sampled_collision_geometry_v1`
  in all artifacts); a verified line is verified against declared
  relations, not a collision-free claim.
- Only single-task offsets were probed by this job. At the time of
  the probe, joint offset search over derived relations was not
  implemented and `omts propose-offsets` refused such lines (the
  G5 fail-closed rule of that revision); the refusal was lifted when
  the joint search learned to compose derived region relations
  (PR #30). 03's "no feasible offsets" below is a statement about
  single-task offsets in the screened and unscreened pools; the joint
  question it left open is answered in the post-joint-search section.
## Post-joint-search outcome (2026-10-15, after PR #30)

The joint offset search that now composes relations over derived
region events (`omts propose-offsets`, PR #30) was run over COPIES of
the corpus-07 plan dirs (maintainer-local, runs/propose-07; the
corpus-07 plans stayed pristine) at a 1 deg grid:

- 01 solved 15/15 (585 assignments tie the best; top recommendation
  catcher 113 / gate 13, margin 13.26 deg): the joint search
  rediscovered the probe bands recorded above, with margins. No
  re-confirm was needed -- the hand-declared gate 10 re-time above
  already verified 15/15 inside the same band.
- 03 INFEASIBLE: 0 passing of 25 combinations, 0 assignments across
  the whole joint grid. Together with this job's single-task result
  (no feasible offset for either anchor in the screened pools) and
  corpus-06 (none in the unscreened pools), variant 03 is
  un-repairable by phasing at all. The question this job left open is
  answered: no.
- 06 solved 25/25 (18 assignments; top recommendation catcher 175 /
  gate 265, margin 7.69 deg): the negative control did NOT survive the
  wider search. Single-task sweeps (this job) found no feasible offset
  for either task, but clearing the fixed shared zone can require
  moving BOTH tasks at once, which no single-task probe can see. A
  hand-declared confirm (validate, adapt, corpus-07 results reused,
  verify-line) returned `LINE VERIFIED combinations=25
  passing=25` -- exactly the proposal. Variant 06 is reclassified: a
  negative control for declared/single-task phasing (it held across
  five corpora), but joint-repairable by two-task phasing.
- Lesson: a "structurally failed" verdict is relative to the phasing
  search space it was measured in; re-probe negative controls
  whenever the search space grows. Occupancy remains sampled, never
  certified.
