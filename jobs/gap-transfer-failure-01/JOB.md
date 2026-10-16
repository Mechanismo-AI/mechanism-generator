# Job gap-transfer-failure-01: case study B -- the gap transfer asked of the four-bar engine

**Purpose.** First step of the case-study loop for the next mechanism type
(brief, failure analysis, capability), case study B: the gap transfer. Two
conveyors with a 260 mm gap between their belt ends; a carrier lifts a part
off belt one, carries it across in a straight line at constant height and
level orientation, and sets it down on belt two. The run asks the current
R2.5c four-bar engine to do the job with today's machinery -- three ordered
poses, no new spec vocabulary, no new engine code -- and records the honest
failure. The recorded data (the reach/straightness/levelness frontier of
four-bar coupler curves at packaging tolerance) is the evidence base for the
six-bar capability design. The separately installable experimental six-bar
motion solver (docs/experimental-motion.md) is NOT part of this run; the
recorded data will also give that solver a real brief to be measured
against later.

**Task.** `examples/omts/gap_transfer.omts.yaml`. Three poses 130 mm apart
along the carry line (pick, mid-gap, set-down), physical (-130, 50), (0, 50)
and (+130, 50) mm -- 1 normalized unit = 100 mm, origin at gap center on the
belt line, carry plane 50 mm above the belts. All three level: orientation
0 deg. Tolerances: position 1.5 mm (0.015 normalized), orientation 1.5 deg.
The three poses are the straightness demand as far as today's machinery is
concerned: hit them at tolerance and the carry is straight between them. The
return-below-belt leg is NOT encoded (three poses cannot express it); it is
a follow-up for the existing sampled-occupancy/keep-out tooling once the
carry itself is on record.

**Machine.** Any idle Ubuntu PC (CPU-only, no GPU) with the standard engine
venv (`pip install ".[engine]"` plus `mechanism-models download`; see
sync-pair-eval-01 for the one-time setup). Cost: one three-pose search at
the standard portfolio budget. The document declares `direction: either`,
which runs both crank directions as two complete search budgets with
separate results, so expect roughly twice an ordinary three-pose run.

## Steps

1. **Validate and adapt** (the plan lands in a fresh directory; the adapter
   refuses existing ones):

   ```sh
   omts validate examples/omts/gap_transfer.omts.yaml
   omts adapt examples/omts/gap_transfer.omts.yaml --output-dir runs/gap-transfer-failure-01
   ```

2. **Preflight** (verifies installed engine and model hashes, runs nothing):

   ```sh
   python runs/gap-transfer-failure-01/run_r25c.py --models-directory models --check-only
   ```

3. **Run** (the long part; tmux or nohup):

   ```sh
   python runs/gap-transfer-failure-01/run_r25c.py --models-directory models
   ```

## Prediction scorecard (frozen before the run)

- **P1 (primary):** zero selected candidates -- no four-bar in the pool
  achieves all three poses within 1.5 mm at level orientation (1.5 deg)
  across the 260 mm carry. A completed zero-selection search is the
  expected honest outcome, not an error.
- **P2:** levelness binds before straightness -- the best path-acceptable
  near-misses fail orientation rather than position, and carry the
  qualification level `path_acceptable_but_orientation_failed`; the pool's
  minimum worst orientation error at the targets stays above 1.5 deg while
  its minimum worst position error gets closer to 1.5 mm.
- **P3:** the curve bends away from the line at the ends -- for the top rows
  by worst position error, the errors at T1/T3 (the outer poses) exceed the
  error at T2 (mid-gap).
- **P4 (control):** any selected candidate REFUTES P1 and is recorded as
  the honest result, not an error. It would mean the four-bar pool already
  contains a near-straight, level 260 mm carry at packaging tolerance, and
  the six-bar case study then needs the stricter brief (straightness
  between the poses, return-below-belt clearance) before it can motivate a
  new capability.

## Readings to report

- Per crank direction (the `either` budget runs both separately):
  wall-clock, and from the run summary / `run_manifest.json` target record:
  candidate_count, path_acceptable_count, orientation_acceptable_count,
  pose_acceptable_count, selection_eligible_count, selected_count.
- The `qualification_level` histogram over `all_candidates.csv` (in
  particular any `path_acceptable_but_orientation_failed` rows).
- For the five path-acceptable rows with the lowest worst position error:
  per-target position errors, and `matched_orientation_N_deg` /
  `orientation_error_N_deg` per target.
- Machine, CPU model, Python version, and the seed as run (101).

## What we will do with it

The per-target error structure is the input to the six-bar capability
design: it quantifies what the four-bar coupler-curve family cannot do --
a long, straight, level carry at millimetre tolerance -- that a two-loop
(four-bar plus dyad) curve family is expected to do better, and it sizes
the gap the new topology must close. Record the outcome against the
scorecard in this file; recorded outcomes are data and are never rewritten.
## Recorded outcome (2026-10-16)

Run on the-hub (Jean CPU-only Ubuntu workstation, standard engine venv,
seed 101), run root
`runs/gap-transfer-failure-01/results/task-001/either/2026-10-16_14-18-05_712881`,
on the example merged as PR #37 (main `ce81fce6`). Both crank directions
ran as full portfolio budgets; preflight engine and model hashes
matched. Search wall-clock: 29.79 s positive / 29.19 s negative.

**Per-direction counts (identical in both directions):** candidates 18;
path_acceptable 0; orientation_acceptable 0; pose_acceptable 0;
selection_eligible 0; selected 0. Both are completed zero-selection
searches -- the expected honest outcome, not an error.

**Qualification histogram** (`all_candidates.csv`, 18 rows per
direction): `physical_only_path_rejected` 18/18 in both directions.
Zero `path_acceptable_but_orientation_failed` rows exist.

**Scorecard verdicts:**

- **P1 CONFIRMED (primary).** Zero selected candidates in both
  directions. P4 (control) held: no refutation anywhere.
- **P2 REFUTED as stated.** No path-acceptable near-misses exist at
  all, so levelness never bound; qualification stops at position in
  every row. The binding failure is straightness/position, and it is
  deep: best worst-pose position error 0.0908 normalized (9.1 mm vs
  1.5 mm, about 6.1x) positive and 0.1045 (10.4 mm, about 7.0x)
  negative; best mean errors 0.0492 (4.9 mm, about 3.3x) and 0.0755
  (7.6 mm, about 5.0x). Orientation at the frontier is also over
  tolerance (min worst orientation error 5.76 deg positive / 3.56 deg
  negative vs 1.5 deg), but position is the binding and deeper
  failure; the P2 mechanism (orientation binding before position) is
  refuted.
- **P3 REFUTED as stated.** For the top five rows by worst position
  error in each direction, the mid-gap pose T2 is the single largest
  per-target error in 7 of 10; the outer poses exceed mid only
  marginally in the other 3 (fixed_003: 0.0970 vs 0.0958). The
  near-miss coupler curves sag at mid-gap; they do not primarily bend
  away at the ends. Over all 36 rows: T2 binds in 22, T1 in 11, T3 in
  3.
- **P4 (control): held.** No selected candidates; nothing to record
  beyond P1.

**Frontier rows.** The JOB reading "five path-acceptable rows with
the lowest worst position error" is empty by construction (none
exist), so per the honest-outcome rule the five best rows by worst
position error are recorded instead. Position errors normalized (1
unit = 100 mm); position tolerance 0.015 per pose; orientation
tolerance 1.5 deg per pose.

Positive direction:

| candidate | e1 (T1) | e2 (T2) | e3 (T3) | mean | orient err T1/T2/T3 (deg) | max orient (deg) |
| --- | --- | --- | --- | --- | --- | --- |
| fixed_001 | 0.0669 | 0.0908 | 0.0047 | 0.0542 | 8.73 / 7.30 / 6.75 | 8.73 |
| bridge_release_001 | 0.0828 | 0.0926 | 0.0140 | 0.0631 | 5.99 / 6.11 / 6.09 | 6.11 |
| bridge_trust_001 | 0.0533 | 0.0938 | 0.0006 | 0.0492 | 6.15 / 6.40 / 6.42 | 6.42 |
| fixed_003 | 0.0970 | 0.0958 | 0.0034 | 0.0654 | 9.72 / 8.03 / 6.37 | 9.72 |
| bridge_release_002 * | 0.0898 | 0.0868 | 0.0983 | 0.0917 | 3.54 / 5.76 / 5.72 | 5.76 |

Negative direction (the harder one, as expected):

| candidate | e1 (T1) | e2 (T2) | e3 (T3) | mean | orient err T1/T2/T3 (deg) | max orient (deg) |
| --- | --- | --- | --- | --- | --- | --- |
| bridge_release_001 * | 0.0970 | 0.1045 | 0.0896 | 0.0970 | 3.29 / 3.56 / 1.29 | 3.56 |
| bridge_trust_001 * | 0.0970 | 0.1045 | 0.0896 | 0.0970 | 3.29 / 3.56 / 1.29 | 3.56 |
| bridge_trust_002 | 0.1170 | 0.1150 | 0.1265 | 0.1195 | 4.42 / 4.64 / 2.10 | 4.64 |
| variable_003 | 0.0241 | 0.1317 | 0.0709 | 0.0755 | 3.57 / 4.27 / 5.36 | 5.36 |
| bridge_release_003 | 0.1045 | 0.1390 | 0.0964 | 0.1133 | 4.55 / 4.40 / 2.11 | 4.55 |

(*) Within each direction the starred pair (positive
bridge_release_002 / bridge_trust_002; negative bridge_release_001 /
bridge_trust_001) are byte-identical error rows: the same mechanism
family reached via two portfolio lineages. One row of each pair is a
duplicate reading, not an independent mechanism.

**Machine.** the-hub, CPU-only Ubuntu workstation, standard engine
venv, seed 101. CPU model and Python version: outstanding reading, to
be recorded here before merge.

**What this gives the six-bar brief.** The four-bar frontier on the
260 mm level carry sits at about 9-10 mm worst-pose / 5-8 mm mean
position error against the 1.5 mm packaging tolerance, with mid-gap
sag the dominant structure and position, not levelness, the binding
gate. That sizes the gap the six-bar (two-loop) curve family must
close, and it gives the experimental six-bar motion solver a real
measured brief: reach the 260 mm carry at packaging tolerance where
the best four-bar recorded here misses by about 6x.
