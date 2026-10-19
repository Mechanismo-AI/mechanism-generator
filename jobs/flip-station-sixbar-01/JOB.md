# Job flip-station-sixbar-01: case study C family succession --
the six-bar flip carrier motion task (fold record + frozen gates)

Case study C, the fired trigger's recorded alternative. The cam
line's recorded wide-fail (flip-station-capability-01) fired the
pre-declared C5 trigger, and this job stages the six-bar motion
line's frozen brief: the fold record of the decision debate round,
the demand-translation spec, the frozen scorecard skeleton, and the
frozen predictions. The motion JSON desk derivation itself is
declared as the NEXT staging; it does not appear here, and no
derived-looking demand numbers appear before it runs.

The cam class ruling runs IN PARALLEL as its own desk round, with
its frozen answer schema committed alongside this job
(docs/cam-class-ruling-schema.md, the B2 pattern: the schema commits
before the ruling runs). Neither line waits on the other. The
discipline fence between the tracks: the ruling must be derivable
from family physics without reference to the failed design's numbers
-- its acceptance test is "would this ruling have been made at freeze
time if the architecture mismatch had been noticed then?"

## Why this job exists (the recorded trigger)

- The cam line's recorded outcome (jobs/flip-station-capability-01,
  merged as PR #73, main 42fc20f): G1 WIDE-FAIL exactly as frozen at
  the desk -- pressure angle 89.070/89.314 deg (best-found / chosen
  design) against the 45 deg class gate; dead-point alpha exactly
  90.000 deg; the a_G1 sweep over the recorded family 89.192-90.000
  deg, structural for every swept design (the shallow-spiral
  argument confirmed). C1/C2/C4 CONFIRMED, C3 PASS both handoffs,
  G2 PASS as predicted, C5 overall WIDE-FAIL.
- The pre-declared C5 trigger FIRES: the recorded alternative family
  (the six-bar motion solver line) proceeds.
- The capability corpus (read-only input to this line): 838 rows,
  schema 1.1; JSONL sha256
  cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c;
  CSV sha256
  4edb232c22d58fbab82aa83f3852eb04ec0a5e8544b8fd12ca4b5c08b7679401.
- The B2 answer (docs/b2-answer.md, merged as PR #74, main 566b7c6)
  is DATA-LIMITED and does not touch this line's gates. Its case C
  proof, recorded as context: the demanded 180.000 deg part swing
  requires at least 177.000 deg of unwrapped coupler swing after
  both 1.500 deg pose tolerances, and the recorded four-bar pool
  best free swing is 156.452 deg (deficit 20.548 deg), invariant
  under rigid mounts. The six-bar motion solver is a different
  instrument: it is asked the flip as a sampled-trajectory motion
  task, not as the four-bar pool's pose reach.

## The decision debate round (folded)

Actor's round (relay record, 2026-10-19):

- Q1 order: parallel tracks with a discipline fence. The trigger
  fired; the loop's momentum rule says the recorded alternative
  proceeds -- staging the six-bar line is not conditional on the
  ruling. The ruling is a legitimate question raised at the failure
  reading and gets its own desk round with a frozen answer schema.
  If the ruling re-rules the class, the cam line re-stages as a NEW
  study under the new class gate (a new frozen scorecard row, never
  a waiver of the recorded one). If it declines, the cam wide-fail
  is final for this case study. Either way the six-bar study is
  unaffected.
- Q2 the re-ruled class, if attempted: the friction/efficiency
  channel, not the fixed-frame pressure angle. A captured two-flank
  groove pin has no guide to jam; its binding modes are friction
  lock at the pin, flank wear, contact stress, and pin bending.
  Motion requires cos(alpha) > mu*sin(alpha): self-lock at
  alpha = 90 deg - arctan(mu); with a declared friction safety
  factor (usable-tangential-to-friction >= 2), the gate is
  tan(alpha) <= 1/(2*mu), with transmission efficiency reported as
  data (loss fraction per the same derivation). Two evidentiary
  legs: the first-principles pin-friction derivation in the JOB
  (desk, free), and standard references on positive-drive cam
  pressure angles cited as precedent -- the number must be
  derivable without ever seeing this design. Contact stress and pin
  bending are rated-force questions and stay behind the existing
  rated-force/payload trigger (no smuggled stress gate).
- Q3 six-bar demand translation: a new motion JSON in the recorded
  task format -- the flip as a sampled trajectory, positions +
  orientations over the cycle, the three poses pinned at declared
  phases, timing synthesized between them (the C2 motion program;
  psi(theta) is a declared design parameter, the case-A precedent).
  The acceleration-channel lesson from gap transfer applies and
  goes in the frozen predictions: a 180 deg swing in one cycle is a
  real |dpsi/dtheta| demand (mean ~0.5 deg/deg if spread over the
  full cycle, peak higher through the transit), and the recorded
  six-bar behavior on demanding derivatives is all-fail at 27-41x
  gate. Honest prior: fail, binding at the orientation/derivative
  channel through the vertical transit; counter-branch: a qualified
  candidate is the family's first recorded success and is recorded
  as exactly that.
- Q4 part-body collision deferral: carries unchanged to both lines;
  the trigger (line composition / a keep-out relation gating on
  part occupancy) is family-agnostic by construction -- the
  reciprocity principle doing its job. The in-plane exact-rectangle
  audit moves from the cam script's own audit to the six-bar
  script's own audit unchanged: same discipline, zero instrument
  modification.
- Q5 corpus succession: additive 1.x per the frozen rule; the
  six-bar rows (parameter vectors, joint transmission angles,
  per-sample errors, sensitivity rows) are additive fields, one
  changelog row per addition; any meaning change would be 2.0.
- Q6: the scorecard skeleton below (S0-S5), frozen before the
  instrument is built. One standing-infrastructure note: this is
  the first case study to consume PR-B's per-sample emission
  natively -- no external recomputation pipeline needed for the
  readings.

Critic's round (three catches, all adopted; endorsements recorded):

- Catch 1 (arithmetic, the round's most important): the actor's
  quoted "~55-60 deg" re-ruled gate does NOT fall out of the actor's
  own declared inputs (lubricated-steel mu 0.10-0.15, SF 2). Run
  the declared derivation: tan(alpha) <= 1/(2*mu) gives 78.69 deg at
  mu = 0.10 and 73.30 deg at mu = 0.15. The 55-60 deg figure
  corresponds to dry friction (mu ~ 0.3) or a much larger safety
  factor -- neither matches the stated lubricated-steel premise. In
  a class ruling the gate value must be the derivation's OUTPUT,
  never an input; whether the gate lands near 75 or near 58 deg
  could determine whether the recorded design passes under the new
  class, and a quoted value that does not match its own derivation
  is exactly the shape the fence exists to catch. Adopted rule:
  commit mu and SF first, each with lineage; let the gate value fall
  out as arithmetic; compute the recorded design's pass/fail under
  the new class publicly. Fold-time cross-check, recorded as data:
  at the declared inputs the honest gate is ~73-79 deg, and the
  recorded design's worst angles (89.070/89.314 deg) exceed it --
  the honest re-rule does not rescue the recorded design. The
  ruling still computes pass/fail with its own committed inputs.
- Catch 2 (freeze correction): the transmission-angle gates as
  stated contradicted the convention they cited. The linkage
  convention mu in [40, 140] deg means the HARD floor is 40 deg
  (deviation from 90 deg <= 50 deg); "40 deg target / 30 deg hard"
  is inconsistent with it. Fixed at freeze in S2 below: hard =
  deviation <= 50 deg, target = the tighter declared pair
  mu in [50, 130] deg.
- Catch 3 (two additions): (a) the instrument-modification count
  row carries to this study -- frozen last round as a
  per-case-study scored item testing the generator-agnostic
  principle, and the six-bar line is the harder test of it (a
  linkage family consuming instruments built around cams and an
  earlier four-bar niche); (b) the ruling's consequence is the
  owner's explicit decision, never automatic: the ruling's output
  is the class definition plus the computed pass/fail of the
  recorded design under it, and the re-stage choice is a strategy
  decision with both studies' lineages visible.
- Endorsed: the fence's acceptance test; the friction/efficiency
  channel as the correct physics for a captured two-flank pin (no
  guide to jam; self-lock at the pin is the binding mode; the
  fixed-frame pressure angle is the wrong proxy); the rated-force
  boundary; the honest-fail prior with its stated reason and the
  plateau-breaker counter-branch; the per-sample-emission point.

## The demand translation (frozen spec; the motion JSON itself is
the next staging)

- Instrument: the recorded six-bar motion solver (v0.1.0a11),
  consumed read-only. The task is a new motion JSON in the recorded
  task format.
- The flip as a sampled trajectory: positions + orientations over
  the cycle; the three poses pinned at declared phases -- handoffs
  x = +/-1.3, y = 0.5 (1 unit = 100 mm), orientations 0 / 90 / 180
  deg, tolerances 0.015 units (1.5 mm) / 1.5 deg (the recorded
  brief's numbers, unchanged).
- Timing synthesized between poses: the C2 motion program;
  psi(theta) is a declared design parameter (the case-A precedent).
  The dwell/rise allocation is a design freedom owned by the desk
  derivation and frozen before the run.
- Demand arithmetic, stated with its derivation so it cannot be
  tuned later: a 180.000 deg part swing spread over the full 360 deg
  crank cycle is a mean |dpsi/dtheta| of 0.5 deg/deg; the swing in
  fact occupies only part of the cycle, so the realized mean is
  higher and the peak higher again through the transit. The exact
  allocation is the desk derivation's declared output.
- S0 gates this: the motion JSON validates against the ACTUAL
  validator first (the sixbar-gap-transfer-01 lesson: the first run
  attempt was rejected at input validation on ambiguous README
  wording -- validate the centroid/diagonal gates before anything
  else).

## The frozen scorecard skeleton (S0-S5 + the mod-count row)

- S0 task-contract sanity: the motion JSON validates against the
  actual validator; a validation rejection is a recorded S0 FAIL of
  the staging, never a silent rewrite of the task.
- S1 qualification: the solver's own gates unchanged (position
  0.01 units, orientation 1 deg). Seeds 580000050/51/52, the
  200-eval standard protocol, per-seed reporting, no pooling.
  Initialization declared: any initializer behavior is recorded,
  not assumed (the chooser-restart caution from the strategy
  round).
- S2 transmission audit: per-joint worst transmission angle over
  the cycle against the frozen linkage gates -- HARD: deviation
  from 90 deg <= 50 deg (mu in [40, 140] deg); TARGET: the tighter
  declared pair mu in [50, 130] deg. The location (crank phase) is
  reported, not just the value. (Freeze correction recorded above.)
- S3 geometry audits: the envelope from swept geometry (the part
  corner arc through vertical + the linkage extents) with the
  mandatory utilization/headroom table; part-sweep rectangle
  occupancy (this script's own audit, the cam script's discipline
  unchanged); undefined-assembly = error, never a quiet pass.
- S4 tolerance rows: Jacobian-based link-length sensitivities ->
  handoff pose errors, scored against the labeled defaults
  1.5 mm / 1.5 deg; the max-sensitivity region located. Frozen
  prediction (refutable, with the precedent recorded): not at the
  poses. The cam round's own C3 refuted its mid-swing prediction
  (peak 81.6658 at t = 315 deg, the reversal approach; dead points
  at 90/270 as rows), so the specific location is a prediction to
  test, not a convention to inherit.
- S5 controls: two-run byte-identical determinism; read-only
  consumption of the recorded failure corpus; corpus emission with
  hashes regardless of verdict; the honest-fail branch valid with
  the corpus intact. INSTRUMENT-MODIFICATION COUNT: expected 0,
  scored (the reciprocity row; this study is its harder test).
  Per-sample emission consumed natively (PR-B standing
  infrastructure; first native consumption).

## Frozen predictions

- Lean ALL-FAIL. Binding channel: orientation-coupled derivative
  demands at the through-vertical transit. Reason: the recorded
  six-bar demanding-derivative record (all-fail at 27-41x gate,
  sixbar-gap-transfer-01 through -04).
- Counter-branch: a qualified candidate is the family's FIRST
  RECORDED six-bar qualification -- recorded as exactly that, the
  plateau-breaker. It is never read as a gate relaxation.
- S4 max-sensitivity region: not at the poses (the poses are the
  scored handoffs; the cam C3 precedent says the peak can sit at a
  reversal approach, not mid-swing -- the location is data).
- Q4 deferral carries: no part-body collision gate in this study;
  the trigger stands family-agnostic for both lines.

## Machine step (spec; lands with the motion JSON staging)

- the-hub, the motion venv, repo root; the source commit is the
  merge that carries the motion JSON and the audit script.
- Two runs, byte-identical (external diff empty; in-process check
  IDENTICAL). An empty second output is recorded as-run and rerun
  cleanly (the flip-station-capability-01 precedent: the first
  run-2 attempt left capability_run2.txt empty; the recorded
  determinism pair is run 1 + the clean rerun).
- Corpus emission with hashes regardless of verdict; the honest-fail
  branch valid with the corpus intact.

## Status

Staged; motion JSON desk derivation pending.
