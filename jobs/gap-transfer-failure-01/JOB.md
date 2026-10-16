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
