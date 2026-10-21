# Case study C flip re-entry -- the capability instrument freeze (the composed-oscillation eight-bar; the graded rows' gate values frozen before any code)

Staged 2026-10-21 on Jean's go, his words carried verbatim:
"let's go" -- the instrument-freeze step of the re-entry sequencing
frozen at the task freeze (jobs/case-c-flip-reentry-freeze-01/
JOB.md, merged PR #113, entries 92/94): "the instrument freezes
(each build-time derivation behind its own freeze, the
family-build pattern) -> the capability step, where the
authorization question resolves." The owner's declared trigger
amendment is merged (jobs/case-d-family-desk-01/JOB.md, PR #115,
entries 96/98, his answer verbatim "Declare the amendment now"):
the composed-oscillation family build commitment is authorized
for the C-line re-entry capability step, instrument freezes
first. This document is that instrument freeze. Docs-only: no
script, no run, nothing built, no machine step before or after
the merge; no recorded outcome amended; no verdict on the C task
claimed.

## What this freeze does

It exercises the amendment's authorization exactly as recorded:
the build commitment is exercised at the NEXT staging (the
engine), which follows this freeze's merge. Before any code
exists, this freeze derives and freezes: the family
parameterization (the composed-oscillation eight-bar, carried
from the two merged desk answers as recorded inputs); the engine
spec (the multi-loop position analysis, audit harness and run
discipline built from zero, per the cost-of-entry record); the
declared design classes (frozen BEFORE any synthesis runs, the
staged-declaration discipline); and the gate value of every
graded row R1-R6 (each row a build-time derivation behind this
freeze, with lineage, per the task freeze's demand-rows rule).
Nothing here amends the task freeze: the wide-fail branch and
the near-reach placement guard are carried, not restated.

## The family (recorded inputs, carried verbatim from the task freeze)

The composed-oscillation class, both desk answers YES at the
class level (PR #110 amplitude, PR #112 pose precision; entries
86/88 and 90/91; class-level existence geometry, never build
claims; the margins existence margins, never design margins):
- The output member pivoted ON A MOVING CARRIER, driven through
  its own loop; the three independent loops (two carry the
  composition, the third the pose-precision machinery).
- The composition identity, verbatim: delta(output, absolute) =
  delta(carrier) + delta(output relative to the carrier); the
  construction's stages at 88.500 deg each.
- The moving pivot q_i = p_i - R(theta_i) * v, exiting the
  colinear fixed-pivot catch C1a (a coupler-curve point per
  pose; the catch keeps its meaning for the fixed-pivot class).
- The position channel: the carrier-loop two-point path
  synthesis (the mirror pair q_1 = (-1.3 - v_x, 0.5),
  q_3 = (+1.3 + v_x, 0.5); roughly 8 design dims vs 4
  constraints).
- The orientation channel: the toggle-reversal conditioning
  (zero first-order gain at the handoff reversals, O(1) at the
  mid pose, no branch indeterminacy).
- The leak bound |v| <= 57.296 mm at e = 1.500 deg, carried as
  the R2 budget-split input.
- The timing: the third loop's phase-profile freedom.

## The engine spec (built from zero; the cost-of-entry record)

Per the recorded cost of entry (Candidate B: nothing recorded
for the eight-bar; a new multi-loop position analysis, audit
harness and run discipline built from zero), the engine staging
implements exactly:
- The multi-loop position analysis: the three-loop composed
  mechanism solved per drive configuration; the assembly branch
  discipline (defined-assembly check per configuration;
  undefined assembly a loud ERROR, never silent -- the recorded
  convention); the full cycle on one drive rotation (the out
  stroke with the part carried, the reversal, the return, the
  pick-up reversal).
- The FD self-check REQUIRED at every analytic derivative row
  (the -05 lesson: the FD discipline caught five analytic
  Jacobian bugs before any run; the S0 lesson: validate against
  the actual frozen demand carried above, never a sketch).
- Determinism: pure stdlib; no clocks, no randomness, sorted
  keys; seed-free by construction; double-run byte-identical
  with the in-process "double-run determinism check: IDENTICAL"
  line; syntax-compiled only at staging, NEVER RUN at staging
  (the entry55 precedent).
- The audit harness: per-row witnesses; fail-closed on rank
  deficiency and on any analytic-check failure (the S4
  precedent); the reciprocity row (the scored
  instrument-modification count 0 expected; no other line's
  artifact consumed or modified; the engine self-contained on
  the demand carried in this freeze).
- The corpus emitter: schema 1.2 additive (the flip-station
  corpus convention); the new kinds declared at the engine
  staging, additive-only, fail-closed; the corpus under
  runs/case-c-flip-capability-01/ (gitignored, maintainer-
  local).
- The machine step after the ENGINE's merge (never this
  freeze's): two runs + diff, expect EMPTY, exit 0 on both,
  the in-process determinism line; the report pasted back and
  read against the frozen rows below.

## The declared design classes (frozen BEFORE any synthesis)

- D0, the recorded construction -- the deterministic primary:
  the desk-answer construction at parameters derived from the
  recorded inputs, never picked. The mirror-pair carrier
  synthesis at the recorded handoff poses; the mount vector v
  strictly inside the leak bound with the budget split declared
  (both numbers in the table: the synthesis residual and the
  orientation leak, their sum inside the 1.500 mm position
  budget); the toggle-reversal orientation conditioning; the
  third-loop phase profile pinned at the handoff reversals.
- The bounded fallback scan: if and only if D0 misses any
  graded row, the frozen bounded scan over the free dimensions
  (the ~4 free dims the 8-vs-4 accounting leaves). The exact
  grid values, the coarse scan, the finalist refinement and the
  frozen pick rule (smallest worst violation at the binding
  gate; declared tie-breaks; if none passes, the best records
  with the wide-fail verdict) are declared at the ENGINE
  staging, frozen before any run, with their task-merits
  lineage stated (the near-reach guard binds the grids: a range
  trimmed to just clear a row is its named violation).

## The graded rows (gate values frozen; each with lineage)

- R1 AMPLITUDE: swing >= 177.000 deg unwrapped between the
  handoff phases (the pick-up and the set-down); the floor
  arithmetic carried verbatim (180.000 - 1.500 - 1.500, B2
  Finding 1); the two-step structure never collapsed
  (amplitude answers existence, never precision). The
  per-stage composition recorded as data (the additive
  identity; the stages).
- R2 POSE PRECISION: orientation 1.500 deg at ALL THREE ordered
  poses (0 / 90 / 180 deg); position 1.500 mm (0.015
  normalized; 1 unit = 100 mm) at BOTH handoffs (x = +/-130 mm
  on the carry plane y = 50 mm); the leak bound |v| <= 57.296 mm
  at e = 1.500 deg carried as the budget-split input, its
  arithmetic on the record (at the bound the orientation leak
  alone consumes the full position budget: 57.296 mm x 0.026180
  rad = 1.500 mm; the design point sits strictly inside, the
  split declared at the engine staging with both numbers in the
  table); the pose witness tolerance < 1e-12 at the synthesis
  self-checks (the machine convention carried).
- R3 TRANSMISSION QUALITY UNDER LOAD: never read by either desk
  pass -- its gates freeze here, per the task freeze's own
  rule. The recorded 40-140 convention carried (the case C
  capability fold, PR #75): the transmission angle hard gate mu
  in [40, 140] deg (deviation from 90 deg <= 50 deg) at every
  loop joint pair through the whole cycle, sampled at the
  0.25 deg drive grid (the flip-line convention); the target
  band mu in [50, 130] deg reported as data, never a gate; the
  between-samples channel at 8x the native grid SAMPLED NEVER
  CERTIFIED (the case D convention); each of the three loops
  graded on its own row (the composed transmission never
  reduced to a single scalar); undefined assembly a loud
  ERROR.
- R4 ENVELOPE AND PART OCCUPANCY: the exact-rectangle part
  envelope carried (the 100 x 60 x 5 mm part as the exact
  rectangle, the recorded capability-study convention), swept
  at the drive grid; the keep-outs: the two handoff stations at
  x = +/-130 mm, the carry plane y = 50 mm; the mechanism
  envelope a LABELED PLACEHOLDER 600 x 600 mm with lineage
  (the recorded case-B class value; a placeholder by
  declaration, never a line measurement, never silently
  inherited -- the -06 lesson institutionalized); the REQUIRED
  headroom/utilization table emitted as data, never gated;
  utilization above 100 percent fires the declared
  renegotiation branch with its recorded trigger (a real
  installation or line measurement showing slack -- the T4
  fallback precedent), never a silent redesign.
- R5 THE DRIVE-REVERSAL BACKLASH CHANNEL: the linkage line's
  joint-clearance question, graded at BOTH handoff reversals
  (the 180 handoff and the 0 pick-up). The declared working
  class: pin-joint diametral clearance 0.10 mm at every
  revolute pair (a declared class with lineage to the recorded
  0.10 mm working classes of the flip-line studies; never a
  measured value -- the class-to-measured restatement is a
  future owner decision, never silent). Worst-case-linear
  combination DECLARED BEFORE THE RUN (the -07 convention);
  channels separate (position take-up, orientation take-up),
  combined = sum; the R2 tolerances (1.5 mm / 1.5 deg) the
  binding gates at the reversals (this row never relaxes
  them); fail-closed on rank deficiency (the S4 precedent).
  The frozen prediction: the channel BINDS at the reversals
  (the case C capability precedent: backlash-binds CONFIRMED at
  both handoffs, combined 0.9736 mm / 0.7768 deg vs 1.5 / 1.5);
  the honest counter-branch records as data either way.
- R6 TIMING: the ordered out-and-back stroke on one drive (the
  recorded machine drive class, one flip per cycle); the
  reversals PINNED at the handoff poses (the pose channel owns
  "when": each reversal coincides with its handoff pose within
  the R2 tolerances); the third loop's transmission profile
  graded: the reversal witnesses (the output's unwrapped
  velocity sign changes) at the pinned poses; monotonic between
  reversals; the exact crank phase values the engine's design
  freedom, recorded as data (the phase-profile freedom
  carried).

## The wide-fail branch (carried, not new)

Carried from the task freeze, read before the step: if the
capability step returns honest fail on any frozen row, the
outcome records as data, never an error -- the flip demand
records as family-infeasible at that row in the composed
classes; the supplier question is not reached again in this
context; the supplier triggers stay unfired, (b) unfired;
recorded outcomes are never rewritten. The honest inconclusive
branch reads the same way: no step defaults past an ambiguity,
and the ambiguity itself is recorded.

## The near-reach placement guard (carried, standing)

Carried unchanged from the task freeze: every design decision
on this line -- the D0 parameters, the scan grids, the phase
profile -- is made on task merits, never a difficulty tuned to
keep the supplier question alive. The guard binds this freeze's
successor stagings identically.

## Trigger and supplier bookkeeping

- The eight-bar trigger: UNSETTLED, never fired; the merged
  amendment (PR #115) is this staging's enabling record, never
  a new firing; its effect exactly and only as recorded.
- The authorization question: parked, resolving at the
  capability step's outcome, never before; this freeze
  manufactures no context.
- The recorded pool ceiling 156.452 deg keeps its meaning as a
  pool datum; the C1a catch keeps its meaning for the
  fixed-pivot class; case study C stays CLOSED with the flip
  unsolved.
- No runs, training, or automation started; nothing built; the
  owner executes every run.

## Sequencing

The task freeze (PR #113, merged, entries 92/94) -> the owner's
declared trigger amendment (PR #115, merged, entries 96/98) ->
THIS INSTRUMENT FREEZE (Jean's go) -> Jean's merge -> the ENGINE
STAGING (the multi-loop position analysis, audit harness and
run discipline implementing this freeze exactly; the declared
scan grids frozen at that staging before any run) -> Jean's
merge -> the owner's run of record (the capability step) -> the
outcome staging, where the authorization question resolves. The
cam line advances in parallel: its run of record (PR #116
merged, entries 97/99) is the owner's machine step there. Each
merge records as its own continuity entry, verified fail-closed
per its review card.

## Status

Instrument freeze staged (2026-10-21, branch
case-c-flip-capability-01): docs-only, additions-only; no
script, no run, nothing built; no machine step before or after
the merge; no recorded outcome amended. The family
parameterization, the engine spec, the declared classes and the
R1-R6 gate values are frozen above. NEXT: Jean reviews and
merges; the engine staging follows on this freeze's merge, then
his run of record (the capability step).
