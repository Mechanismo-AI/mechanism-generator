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

## The motion JSON desk derivation (staged; the frozen artifact is
flip_sixbar.motion.json in this directory)

- FORMAT (the S0 discipline, read from the actual validator at this
  staging, experimental/motion/src/mechanism_motion/targets.py):
  five fields exactly; twelve equally spaced increasing phases
  0..330 deg (atol 1e-10 against the solver's own grid); two known
  branch signs [-1, 1]; q/v/a each 12x3 finite [x, y, angle] rows;
  the centroid and unit-bounding-box-diagonal checks read the XY
  CHANNEL ONLY (p = q[:, :2], each to 1e-8) -- the angle channel
  enters inference as cos/sin features, so the pinned poses carry
  their absolute 0 / 90 / 180 deg values directly in the design
  frame; no mounting-angle convention is needed.
- POSITION CHANNEL (provenance, inherited verbatim, not re-derived):
  the recorded case-B layout loop of sixbar-gap-transfer-01 -- the
  same station layout this case study sits on -- taken from that
  recorded task artifact unchanged (the XY components of its q, v
  and a; the loop: the 260 mm carry at y = 50 mm over phases 0-4,
  the two inward half-ellipse turnarounds, the return at
  y = -40 mm, closing at phase 0). The three demand poses coincide
  with its carry phases: phase 0 (-130, 50) = pose 1, phase 2
  (0, 50) = pose 2, phase 4 (+130, 50) = pose 3 (mm; the brief's
  handoffs x = +/-1.3, y = 0.5 at 1 unit = 100 mm). The inherited
  honest-scope notes carry unchanged (the return plane and the
  inward bulges are a proposal; keep-out screening waits for a
  qualified candidate). Normalized scale: 1 unit = 275.1376 mm (the
  loop's bounding-box diagonal); the packaging overlay 1.5 mm =
  0.005452 normalized and the orientation overlay 1.5 deg (the
  brief's tolerances, the -01 recorded rescaling).
- ORIENTATION CHANNEL (this desk's own derivation; every value
  computed, none transcribed): the C2 motion program. The carry
  swing is ONE quintic smoothstep in psi over phases 0-4:
  psi(theta) = 180 deg * S5(theta / 120 deg) with
  S5(u) = 6u^5 - 15u^4 + 10u^3, pinning the three poses exactly
  (0 / 90 / 180 deg at phases 0 / 2 / 4) with zero angular rate AND
  zero angular acceleration at both handoff dwells (the declared
  dwell/rise allocation: full dwell at the handoffs, one continuous
  rise through the transit). The unwind is the mirrored quintic
  over the remaining 240 deg of crank, 180 deg back to 0 with zero
  rate and acceleration at the closing -- the cycle closes C2 from
  both sides at theta = 0 = 360 deg. The closure is the UNWIND, not
  a 360 deg continuation, by the minimal-demand rule: the traced
  coupler angle is a real number, the process demands exactly the
  180.000 deg part swing, and the unwind's net unwrapped rotation
  per cycle is zero; a 360 deg continuation would prescribe a full
  coupler revolution the process never asked for (the B2
  unwrapped-swing vocabulary, applied to what WE prescribe).
- DEMAND ARITHMETIC (computed, with derivations): the 180.000 deg
  swing occupies 120.000 deg of crank (phases 0-4): realized mean
  |dpsi/dtheta| = 1.500 deg/deg, 3.000x the full-cycle lower bound
  (0.5); the peak is 2.8125 deg/deg at theta = 60 deg (phase 2 --
  the through-vertical pose itself), 1.875x the realized mean.
  Unwind peak 1.40625 deg/deg at theta = 240 deg (phase 8). Peak
  angular acceleration 0.0703125 deg/deg^2 on the carry (at
  theta = 30 deg), 0.017578125 deg/deg^2 on the unwind. At the two
  bottom-join path stops (phases 6, 9) the angular rate is
  deliberately NOT zero (-0.791 / -1.236 deg/deg): the traced point
  is instantaneously stationary while the coupler rotates about it
  -- recorded as a design fact, not an oversight. The handoff dwells
  (phases 0, 4) have zero angular rate by construction.
- DESK VALIDATION against the actual validator: theta matches the
  solver's grid (max residual < 1e-10); branches [-1, 1]; q/v/a
  each 12x3, all finite; the inherited XY channel's centroid
  residual 3.701e-17 and bounding-box-diagonal residual exactly
  0, both under 1e-8 (the recorded -01 artifact passed them;
  re-verified here from the parsed samples). The angle channel was
  re-derived by independent central finite differences of the
  composed psi(theta) at all twelve phases (h = 1e-4 rad): max
  rate deviation 3.420e-8 rad/rad (O(h^2) truncation); max
  acceleration deviation 3.843e-4 rad/rad^2, localized exactly at
  phase 4 -- the carry/unwind segment junction, where the
  one-sided third-derivative jump makes the second central
  difference O(h) (7.584e-7 or less at every other phase; the
  junction is C2 by construction, so the analytic values are
  unaffected). The analytic sample values are exact by
  construction; the finite differences are the check, never the
  source.
- UNITS: the angle channel is radians (psi) per crank radian (v)
  and per crank radian squared (a) -- the solver's native features;
  the deg/deg and deg/deg^2 figures above are the same numbers in
  degree units.

## The S2-S4 audit script (staged; the frozen instrument is
flip_sixbar_audit.py in this directory)

- SCOPE (this job's own audit; the cam script's discipline carried:
  deterministic, pure stdlib, fail-closed, reads the solver's
  emission but never re-gates it). Consumes --task the frozen
  motion JSON, --result the schema-3 result file(s), and a 40-hex
  --source-commit; emits the report plus the corpus
  runs/flip-station-sixbar-01/flip_station_sixbar_v1.{jsonl,csv}
  (schema 1.1, units block + provenance on every row, unknown-kind
  refusal).
- S0: the validator's own rules re-applied fail-closed (five
  fields, uniform 12-phase grid, branches, 12x3 finite, centroid
  and unit-diagonal) plus the staging-integrity pins (the demand
  orientation pins at phases 0/2/4; the handoff dwells -- zero
  angular rate AND acceleration -- at the handoff phases 0/4 only;
  phase 2 is the through-vertical transit, deliberately NOT a
  dwell). Frame mapping DERIVED, never transcribed: the carry
  endpoints x = -130/+130 mm fix the scale, phase 0 the centroid,
  with fail-closed checks against the recorded 260 x 90 mm
  bounding box and the exact demand poses.
- S1: native consumption of the six-channel per-sample emission
  (read-only); the packaging overlay 1.5 mm / 1.5 deg at the
  demand phases; and a kinematics cross-check -- position and
  orientation errors recomputed by the script's own independent
  assembly at all twelve phases vs the emission, abort on
  disagreement (1e-4), None entries recorded as data.
- S2: the per-joint folded transmission angle arccos(|cos|) at B
  (A-B-Q) and C (D-C-R) on a 0.25 deg grid (1440 samples, a subset
  of the solver's own sweep): hard gate >= 40 deg, target >= 50 deg
  (the freeze correction); worst value + crank phase reported;
  edge-length self-check and cycle closure fail-closed; an
  undefined assembly is a loud ERROR, never a quiet pass.
- S3: the exact 100 x 5 mm part rectangle (identity mount, the B2
  seam declaration carried) swept at the same grid; the
  utilization/headroom table (the -06 precedent; rows are data, no
  size gate); linkage joint sweep and ground pivots; no keep-out
  gate (the Q4 deferral carries).
- S4: the analytic 4x4 constraint Jacobian over the five
  manufactured bar lengths (the attachment triangle, tool,
  ground pivots and mounting angle declared unpriced scope);
  sensitivities scale-invariant (mm/mm) with the orientation gain
  in deg/mm; worst case over the 32 sign corners (exact
  enumeration); scored at the handoff phases (0/4) vs the 1.5 mm /
  1.5 deg overlay, the through-vertical phase 2 recorded as data;
  the declared 0.1 mm manufactured-length class (the cam 0.1 mm
  clearance lineage, the -07 uniform-class precedent). A
  finite-difference self-check re-solves the exact assembly at
  every scored phase and aborts on disagreement; rank deficiency
  fails closed. The 5 deg sensitivity curve is compared against
  the frozen peak-location prediction honestly (CONFIRMED /
  REFUTED, data either way).
- S5: double-run determinism (compute twice, byte-identical);
  the instrument-modification count row (expected 0; read-only
  consumption of the solver and its emission); the changelog row.
- DESK VALIDATION (the honest record; every number computed this
  staging, none transcribed): the script's own finite-difference
  discipline caught five analytic bugs before this staging --
  (1) matrix scaling ops, (2) the missing LU pivot permutation,
  (3) the implicit-function-theorem rhs sign (J dX = -(dG/dL)),
  (4) the output chain's free-derivative convention, and (5) a
  projected-vs-free mixing between the constraint Jacobian's
  third row and its right-hand side (worst deviation 4.207e-01
  before the fix; the two forms differ by a row operation that is
  legal only applied to both). After the fixes: the analytic
  sensitivities match central differences of the exact re-solved
  assembly to 6.012e-10 over 20 configurations on three
  mechanisms including a near-toggle, against the 1e-6 tolerance.
  The end-to-end harness (the actual frozen task JSON plus two
  synthetic schema-3 fixtures) then caught one more: the handoff
  dwell pin was wrongly applied at the through-vertical phase 2
  (whose 2.8125 deg/deg rate is the recorded demand peak) instead
  of the handoff phases 0/4; fixed to HANDOFF_PHASES. After all
  fixes: end-to-end exit 0, double-run determinism IDENTICAL, a
  406-row corpus with sha256 (jsonl)
  cc215141160ceeb0c2561377b35e7f1a9dcae8b7d8573d09ca61b5cec41b5279
  and (csv)
  c7ed43282103421867fcc6dffbb604580de58416026f1c50b0416e0f91a22a1d;
  the in-run FD
  self-check max deviation 8.075e-10; the kinematics cross-check
  deviation exactly 0.000 against the harness emission. Six
  fail-closed paths verified loud (missing --source-commit, a
  39-char sha, a schema-2 result, a duplicate seed, a tampered
  task centroid, a tampered emission value): every one exits
  nonzero with a FAIL-CLOSED message, none a quiet pass.

## Machine step (the S1 run; the source commit is the merge that
carries this motion JSON AND the S2-S4 audit script)

- The S2-S4 audit script is staged (the section above); the
  machine step below follows THIS staging's merge, per the frozen
  spec above.
- the-hub, the motion venv, repo root:

  mechanism-motion jobs/flip-station-sixbar-01/flip_sixbar.motion.json --seed 580000050 --output runs/flip-station-sixbar-01/result-580000050.json
  mechanism-motion jobs/flip-station-sixbar-01/flip_sixbar.motion.json --seed 580000051 --output runs/flip-station-sixbar-01/result-580000051.json
  mechanism-motion jobs/flip-station-sixbar-01/flip_sixbar.motion.json --seed 580000052 --output runs/flip-station-sixbar-01/result-580000052.json

- then the audit, repo root, same venv (the merge sha of this
  staging's merge as the source commit):

  python3 jobs/flip-station-sixbar-01/flip_sixbar_audit.py --task jobs/flip-station-sixbar-01/flip_sixbar.motion.json --result runs/flip-station-sixbar-01/result-580000050.json --result runs/flip-station-sixbar-01/result-580000051.json --result runs/flip-station-sixbar-01/result-580000052.json --source-commit <40-hex merge sha>

- The audit emits its report plus the corpus
  runs/flip-station-sixbar-01/flip_station_sixbar_v1.{jsonl,csv}
  with sha256s regardless of verdict.

- Two runs byte-identical per the recorded standard (external diff
  empty; in-process check IDENTICAL); an empty second output is
  recorded as-run and rerun cleanly (the capability-01 precedent).
  Corpus emission with hashes regardless of verdict; the honest-fail
  branch valid with the corpus intact.

## Status

Task staged: the motion JSON derived and desk-validated; the S2-S4 audit script staged and desk-validated (six analytic/fail-closed bugs caught and fixed by its own FD and end-to-end harnesses before staging); the machine step (the three-seed run plus the audit) follows this staging's merge.
