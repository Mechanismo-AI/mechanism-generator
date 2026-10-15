# Job sync-corpus-07: the Z3 capstone, search-time screening on fresh runs

**Purpose.** The closing step of the search-time zone screening arc
(specs/omts/0.2/search_screening.md, stage Z3): rerun the G5 capstone
corpus with the screen ON in the engine, on NEW engine runs, and read the
outcome against the prediction scorecard frozen in this file BEFORE the
run. Screening changes candidate selection, so no earlier engine result
tree is reused: the driver refuses `--results-from` for screened documents,
and the engine runs fresh for every variant.

**Base document.** `examples/omts/collision_pair_screened.omts.yaml`: the
G5 collision pair (shared circular handoff zone, per-task link-capsule
bodies, hard disjoint_windows keep-out with 10 deg clearance) plus a
search-time screen on both tasks, hard `max_total_width {phase: 60}`
against `shared_zone`. The screen says: an arm may pass through the
handoff zone, but its links must not drag through it. A candidate whose
sampled occupancy windows against the zone total more than 60 deg of the
cycle is excluded from `selection_eligible` at qualification time. The
screen shapes the search; it never gates the composed line verdict (the
G5 relation still does that, post-hoc), and a screen pass is never a
collision-free claim.

**Why 60 deg.** A design choice, recorded as such, not a derived constant.
The corpus-05 conflict shapes were overlapping occupancy bands roughly
73-94 deg wide in the flipped variants, while variant 01's
keep-out-passing candidates swept about 33-55 deg. A 60 deg cap admits
the quick-pass shapes and excludes the drags; two 60 deg windows plus two
10 deg clearances still fit in a 360 deg cycle with room to spare, so the
bound alone never makes disjoint interleaving impossible. The bound is
the same for both tasks, and screen thresholds are phase quantities, so
they travel unchanged through the variant transforms (the transform
touches geometry, not screens).

**Baseline.** Corpus-05 (same pair, no screen, corpus-04 offsets, reused
region-blind engine trees): 01 verified 3/15; 02, 03, 04 failed with every
combination's zone gap exactly 0.0 (outright overlap, not a clearance
miss); 05 no_candidates; 06 failed, all-vacuous (the negative control).
Corpus-06 (anchor probe): no per-anchor offset admits a passing
combination in 02, 03, or 04.

## Prediction scorecard (written before the run)

Per variant, predicted before any corpus-07 engine run. The run either
confirms or refutes, and either is data.

- **01 (identity transform): verified, passing count at most 3.** The
  candidates that passed authored + keep-out at the corpus-04 offsets
  swept the zone about 33-55 deg, under the cap. Risk recorded in
  advance: the corpus-05 digest showed a second gate family
  (`fixed_011`) sweeping about 80 deg on the far side of the cycle; if
  any of 01's three passing combinations used it, that combination's
  gate is screened out and 01 drops. A drop to failed would say the cap
  clipped a genuinely keep-out-compatible dragger: bound-tuning data, not
  a screening failure.
- **02, 03, 04 (the flipped variants): the open question this job
  answers.** Primary prediction: no_candidates in at least one task. The
  whole qualified pool sweeps wider than the cap, and the hard screen
  reports zero eligible candidates honestly, which extends the
  corpus-05/06 structural reading from the selected sets to the full
  pools. Alternative: sub-60-deg candidates existed all along, were
  merely out-ranked, and now get selected; new combinations appear and
  some pass authored + keep-out. Both outcomes are decisive. A verified
  variant here would be the first repair of a structurally-failed line by
  pool shaping, would be reported as a surprise, and would make spec
  open question 1 (ranking among passing candidates) live.
- **05: no_candidates, unchanged.** The catcher task qualifies zero
  candidates at all; a screen cannot create candidates.
- **06 (negative control): failed, unchanged.** The gate candidates
  never reach the transformed zone (empty windows), so the screen passes
  vacuously and cannot alter the verdict; the authored constraints fail
  far away. A changed verdict here would mean the screen changed engine
  behavior beyond exclusion, which would be a bug, not data.
- **Cross-cutting:** `results_reused` must be false everywhere (the
  driver refuses reuse for screened documents); task times are real
  (fresh engine runs, plus the screen's per-candidate occupancy
  sampling); selected counts may drop where the screen excludes
  previously selected candidates, and combination counts change with
  them.

## Run (maintainer-local)

```sh
. .venv/bin/activate
python jobs/sync-corpus-01/corpus_run.py \
  --document examples/omts/collision_pair_screened.omts.yaml \
  --offsets jobs/sync-corpus-01/offsets-corpus-04.json \
  --output-dir runs/sync-corpus-07
```

Fresh output directory (the summary is resumable; completed variants are
skipped on rerun). No `--results-from`: the driver refuses it for
screened documents, fail closed. The corpus-04 offsets are declared so
the delta against corpus-05 is the screen and the fresh selection, not a
phasing change; if screening selects new candidates, a later probe pass
can re-time offsets for the new pools (a corpus-08 decision, not this
run's). Expect runtimes on the order of the corpus-03 fresh runs (about
two minutes per variant) plus the screen's per-candidate sampling:
minutes, not hours.

## Reporting back

Per variant: status, passing/combination counts, selected counts per
task, and for the no_candidates cases the engine's
`selection_eligible_count` together with how many candidates failed with
qualification level `path_acceptable_but_zone_screen_failed` (the
per-candidate exports record window counts and total widths). The
readings that matter: which of 02, 03, 04 (if any) verified; and whether
any zero-eligible report is an honest structural finding or narrow
candidates existed all along and were merely out-ranked.

## Recorded outcome (after the run, 2026-10-15)

Run executed maintainer-local at main 85d000a9: fresh engine runs,
results_reused false everywhere, about 837 s total. Read against the
frozen scorecard above: 5 of 6 verdict-level predictions confirmed;
01's count prediction (at most 3) was refuted in the favorable
direction.

- **01: verified 6/15 (predicted verified, at most 3).** The screen
  admitted gate candidates the region-blind search had out-ranked: 6
  of 15 combinations pass authored + keep-out versus the corpus-05
  baseline's 3/15. Pool shaping improved the line, not merely
  preserved it. Gate pool detail: 42 candidates, 11 screen survivors,
  all qualified, 5 selected; 7 candidates occupied the zone for the
  full 360 deg (degenerate always-in-zone designs), 8 never entered it.
- **02: no_candidates (predicted).** Gate zero, cap-caused: all 42
  gate candidates were engineering-acceptable and all 42 exceeded the
  60 deg cap (total widths about 69-108 deg). The structural reading
  extends from the selected set to the full pool.
- **03: failed 0/25 (the scorecard's open middle case).** Sub-60-deg
  candidates existed all along and were merely out-ranked: the screen
  left 24 of 42 gate candidates and 15 of 42 catcher candidates (9
  fully eligible); 5 x 5 were selected and no combination passes
  authored + keep-out. Pool shaping narrowed without repairing the
  line.
- **04: no_candidates (predicted).** Catcher zero, cap-caused: all 42
  catcher candidates exceeded the cap; 25 were path-acceptable (17
  failed the physical path upstream regardless).
- **05: no_candidates, unchanged (predicted).** 17 path rejections
  and 13 selection-floor failures upstream regardless; 12
  path-acceptable candidates were screen-blocked whose selection-floor
  status the qualification labels do not record, so the fresh pool's
  zero is upstream-leaning but not fully attributable either way. The
  verdict matches every prior corpus.
- **06: failed, unchanged (negative control held).** All 42 gate
  candidates passed the screen (24 never touch the zone; widest
  survivor 46.5 deg); the catcher pool narrowed and the verdict did
  not change.
- **Plumbing:** 12/12 per-task zone_screen.json sidecars written with
  the per-variant transformed zone geometry and the hard 60 deg cap;
  per-candidate window/width metrics and qualification labels are
  present and consistent with the selected counts.
- **Follow-up decision:** a corpus-08 anchor-probe pass over the new
  pools (whether offsets can re-time the screened pools), and/or
  closing the screening arc; recorded as data either way.
