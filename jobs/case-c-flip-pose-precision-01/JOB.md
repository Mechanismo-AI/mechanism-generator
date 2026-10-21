# Case study C flip re-entry, step 2 -- the desk-only pose-precision-at-amplitude derivation (an eight-bar's output member can serve the three ordered poses at tolerance)

Staged 2026-10-21 per the strategy fold (continuity STATE-VOL-2.md
entry85) and the step 1 freeze's own two-step structure
(jobs/case-c-flip-derivation-01/JOB.md, merged as PR #110, recorded at
entry88), on Jean's go. Docs-only: no script, no run, nothing built,
no machine step before or after the merge. The desk work is this
staging's own arithmetic and geometry over the recorded demand and
recorded linkage theory; no verdict on the C task is claimed by this
document, and no engine commitment is made by it.

## The method (per the step 1 freeze)

Desk-only, read-only; pose-precision-only scope -- the step 1 freeze's
own next question, verbatim: "whether an output member AT >= 177.000
deg amplitude can also serve the three poses at tolerance (1.500 deg
orientation per pose, the 90 deg mid pose, 1.5 mm position at the
handoffs)". The amplitude answer (step 1: YES by the loop-composition
construction, both stages well-conditioned) is carried as recorded
and never re-litigated here; nothing in this pass re-reads
amplitude. The honest inconclusive branch is read before staging,
never defaulted past. No runs; no engine invoked; the derivation is
class-level existence geometry, declared honestly as such (no
eight-bar engine exists -- this is NOT a claim about any recorded
parameterization).

## The recorded inputs (read-only, this staging's own reads)

- The C demand (jobs/flip-station-capability-01/JOB.md, the carried
  brief, frozen): the 180 deg face flip as three ordered poses
  0 / 90 / 180 deg; symmetric handoffs at x = -130 and +130 mm on
  the carry plane y = 50 mm; mid pose at x = 0; tolerances
  "position 1.5 mm (0.015 normalized), orientation 1.5 deg, demanded
  at the handoffs"; one flip per cycle -- the out stroke 0 -> 180
  deg with the part carried, reversal at the 180 handoff, return
  180 -> 0 deg empty, reversal at the 0 pick-up (the drive-reversal
  structure the brief records on its backlash channel).
- The step 1 answer (jobs/case-c-flip-derivation-01/JOB.md, merged,
  verbatim): "YES -- an eight-bar's output member can swing >=
  177.000 deg, by the loop-composition construction with both
  composed stages well-conditioned"; the additive composition
  identity; the construction's stages at 88.500 deg each; "the
  third remains for the pose-precision machinery the NEXT step
  would freeze -- never read here" -- this derivation is that step.
- The fixed-pivot class catch (the merged capability record, C1a,
  verbatim): "the three demand centroid points (-1.3, 0.5), (0, 0.5),
  (1.3, 0.5) are colinear and distinct, and no fixed-pivot circle
  passes through three colinear points"; the executed best fit --
  pivot (0.000000, 0.175000), mount (-0.975000, 0.000000), worst
  pose residual 1.300000 units (130.00 mm over the 1.5 mm
  tolerance). Normalized units: 1 unit = 100 mm.
- The B2 mount formula (docs/b2-answer.md): the part point is
  carrier point + R(theta + c) v -- "a mounting vector does not enter
  orientation"; at fixed orientation the rigid mount contributes no
  position play.
- The position pool datum (docs/b2-answer.md, Finding 1): position
  fails independently in the recorded pool (pool-best 11.65x
  tolerance; the D3a at-pose pairing none for every candidate) -- a
  POOL datum over the frozen parameterization, never a topology
  bound.

## Step 1: the question decomposed (three channels)

The frozen question splits into: the ORIENTATION channel (the three
ordered orientations 0 / 90 / 180 deg at 1.500 deg per pose); the
POSITION channel (1.5 mm at the two handoffs); and the TIMING (the
ordered out-and-back stroke, its reversals sitting exactly at the
handoff poses -- the brief's own structure). The rigid-mount formula
couples orientation and position once: the part point is pivot +
R(theta) v, so an orientation error e rotates the mount vector and
leaks |v| * e into the position channel; the leak arithmetic is
below. Tolerance scope per the step 1 freeze: orientation at all
three poses, position at the handoffs.

## Step 2: the moving pivot (the colinear catch exited)

The class that defeated the cam architectures is the FIXED-pivot
rigid mount (C1a above): a part-carrying member rotating about a
fixed ground pivot must place the three pose points on one circle,
and three colinear distinct points admit none. The composed
construction's part-carrying member is pivoted ON A MOVING CARRIER:
its pivot location at pose i is

  q_i = p_i - R(theta_i) v

-- a different point of a rich closed trajectory (the carrier
loop's coupler curve) at each pose. No circle constraint exists in
this class; the catch is exited structurally, never refuted (it
keeps its meaning for the fixed-pivot class exactly as recorded).

## Step 3: the position channel (the carrier-loop synthesis)

With a horizontal mount vector v = (v_x, 0) -- an admissible
mounting declaration in the B2 field structure, a design freedom
declared with lineage at build time -- the two demanded pivot
locations are

  q_1 = (-1.3 - v_x, 0.5)   and   q_3 = (+1.3 + v_x, 0.5)

-- a mirror pair about the demand's own symmetry axis (x = 0), on
the carry plane, directly from the brief's symmetric layout. The
position requirement therefore lands on the carrier loop alone: a
four-bar whose coupler point trajectory passes through the pair.
The classical path-generation count: a four-bar plus coupler point
carries roughly eight essential design dimensions; two precision
points at free phases are four scalar constraints; the problem is
underdetermined by four dimensions, and the well-conditioned
solution families are nonempty in general position (the two-point
demand sits far inside the classical three-to-five precision-point
capacity of the four-bar path problem). The passage is exact by
synthesis (the points ON the curve), leaving the full 1.5 mm
budget to the leak and manufacturing. The mid-pose pivot
q_2 = (0, 0.5 - v_x) sits on the symmetry axis by the same formula;
adding it as a third precision point is a construction convenience
(the mid pose's position is a shape statement of the demand, never
tolerance-gated), still inside the classical three-point class.

## Step 4: the orientation channel (precision at amplitude)

The composed orientation map is the step 1 identity: theta(output)
= theta(carrier) + theta(output relative to the carrier). Two
conditioning facts, one per pose class:

- The handoff poses sit at stroke reversal (the brief's structure,
  above). In the composed construction each stage's reversal is the
  ORDINARY crank-rocker toggle (the crank-coupler colinear
  configuration): the first-order gain d(theta_stage)/d(theta_crank)
  is exactly zero there -- the pose HOLDS against input-phase error
  at first order, with O(1) second-order curvature, and the
  assembly branch is never indeterminate (the crank rotates through;
  the rocker reverses -- the native stroke end of the recorded
  machine drive class). Step 1's record carried the contrast: the
  single-loop construction reaching the floor reverses AT the
  change points (all four links colinear, the near-parallelogram
  probe), where the assembly branch is indeterminate and the pose
  is not holdable. The composed stages reverse at their own
  well-separated toggles, each at 88.500 deg of its honest band,
  far from every change point.
- The mid pose (90 deg) sits at both stages' mid-range -- the
  best-conditioned configuration class, gains O(1) bounded away
  from zero and infinity; the 1.500 deg tolerance maps to O(1)
  input-phase precision.

The leak arithmetic: an orientation error e rotates the mount
vector, leaking |v| * e into position. At the worst e = 1.500 deg =
0.026180 rad, |v| <= 1.5 mm / 0.026180 = 57.296 mm (0.57296 units)
keeps the FULL orientation-error leak inside the position
tolerance; at the demand's 100 mm part scale a mount point within
~57 mm of the member's pivot is generic, and the recorded
manufacturing class (0.10 mm at 100 mm scale) sits far inside the
remaining budget. The build-time design splits the 1.5 mm between
the leak and manufacturing; both channels fit with margin.

## Step 5: the timing (the third loop)

The ordered stroke -- 0 -> 90 -> 180 out, reversal, 180 -> 0
return -- ties the two stages' drives to one schedule. Read
honestly: with the stages separately driven the phases are free
and the poses are served at the phases above; with the third loop
closing the topology to one drive (the recorded machine class),
the relative phase becomes the third loop's transmission profile
-- a finite-dimensional design element (one linkage loop's worth
of freedom) against finitely many phase constraints (the three
pose phases), underdetermined at the class level. The third loop
is the pose-precision machinery step 1 reserved; its actual
dimensions are build-time, behind the re-entry freeze.

ANSWER: YES -- at the class level an eight-bar's output member at
>= 177.000 deg composed amplitude serves the three ordered poses
at the recorded tolerances: the position channel through the
carrier-loop two-point path synthesis (the moving pivot exits the
colinear fixed-pivot catch; the exact passage leaves the budget to
the leak, inside at |v| <= 57.296 mm), the orientation channel
through the toggle-reversal conditioning (zero first-order gain at
the handoff poses, O(1) gains at the mid pose, no branch
indeterminacy anywhere on the pose set), the timing through the
third loop's phase-profile freedom. With margin. NEVER a build
claim.

## What this pass does NOT read

- The other C gates -- transmission quality under load, envelope,
  the drive-reversal backlash channel (for the linkage line a
  joint-clearance question, build-time), keep-outs, part
  occupancy -- untouched by this pass.
- The single-loop coupler-mount variant (the part on a four-bar
  coupler, a moving-pivot member of ONE loop): a different class
  from the recorded contrasts; not derived here; the composed
  construction is this derivation's object.
- The re-entry freeze (the task, the demand rows, the family
  decision on the record): the NEXT document, its own freeze; this
  derivation hands it the two desk answers (amplitude YES;
  pose-precision YES) as recorded inputs, never a task design.
- The trigger: the frozen eight-bar trigger is D-scoped and NOT
  FIRED by this document; the input-class question stays UNSETTLED;
  a family build commitment requires the trigger's own declared
  amendment, never a reinterpretation.
- The authorization question: parked exactly as the fold recorded;
  it resolves at the capability step's outcome, never before; this
  derivation manufactures no context.
- Cost of entry: unchanged (the Candidate B record stands; nothing
  here stages or commits a build).

## The near-reach placement guard (carried)

Step 1's guard stands unchanged: if the re-entry task is later
designed at the margin -- parameter ranges trimmed to just clear
the poses -- that choice must be made on task merits, never a
difficulty tuned to keep the supplier question alive. The margins
above are existence margins, never design margins.

## The honest inconclusive branch: read, NOT taken

The derivation is conclusive on its single question: the catch it
exits is the merged record's own executed arithmetic (C1a,
verbatim); the path-generation count is classical linkage theory;
the toggle conditioning is the recorded machine drive class's
native stroke end; the leak arithmetic is exact. No step defaulted
past an ambiguity; the read precedes the staging, as frozen.

## The wide-fail branch: pre-stated, NOT taken

Had the derivation returned NO -- the position channel
overdetermined in the moving-pivot class, or the reversal poses
unholdable -- the supplier consequence was pre-stated per the fold:
the supplier question is not reached again in this context, the
supplier triggers stay unfired -- (b) unfired -- and the flip
demand would record as pose-infeasible in the composed family
classes. The branch was read before staging; it did not fire.

## Honest scope of this check

- Class-level existence geometry, never a recorded-engine claim: no
  eight-bar engine exists and none is committed by this document.
- The margins are existence margins, never design margins: link
  dimensions, branch signs, transmission, envelope, backlash and
  keep-outs are build-time derivations, behind the re-entry freeze
  per the family-build pattern.
- The recorded pool ceiling (156.452 deg), the D3a position datum
  and the C1a catch keep their meanings exactly as recorded (pool
  and class data; this derivation exits the fixed-pivot class, it
  never refutes the catch).
- The demand's other rows are untouched; no verdict on the C task
  is claimed.
- The desk reads are exactly the record set above (the carried
  brief, step 1's merged answer, the C1a record, the B2 formula and
  Finding 1); no run, no solver execution, no corpus touch, no
  script.

## Sequencing

The strategy fold (entry85) -> step 1 (amplitude, PR #110,
entry88) -> THIS DERIVATION (step 2, pose precision at amplitude)
-> Jean's merge -> the re-entry freeze (the task, the demand rows,
the family decision on the record) on Jean's go -> the capability
step, where the authorization question resolves. The owner executes
every run; nothing auto-runs at staging. On this staging's merge
the merge records as its own continuity entry.

## Status

Derivation staged (2026-10-21, branch case-c-flip-pose-precision-01):
desk-only, docs-only, additions-only; no script staged, no run
claimed, nothing built, no machine step before or after the merge;
no recorded outcome amended. The pose-precision answer is frozen
above: YES at the class level -- the moving pivot exits the
colinear fixed-pivot catch; the position channel rides the
carrier-loop two-point synthesis with the leak inside at
|v| <= 57.296 mm; the orientation channel rides the toggle-reversal
conditioning (zero first-order gain at the handoff reversals,
O(1) at the mid pose); the timing rides the third loop's profile
freedom; the trigger question UNSETTLED, never fired; the
authorization question parked exactly as the fold recorded. NEXT:
Jean reviews and merges; the re-entry freeze follows on his go.
