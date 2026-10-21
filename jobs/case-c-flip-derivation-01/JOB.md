# Case study C flip re-entry, step 1 -- the desk-only swing-envelope amplitude derivation (an eight-bar's output member can swing >= 177.000 deg)

Staged 2026-10-21 per the strategy fold (continuity STATE-VOL-2.md
entry85: Option 1, the flip re-entry, desk-only derivation first; all
five critic deltas adopted) and Jean's go gating the staging.
Docs-only: no script, no run, nothing built, no machine step before
or after the merge. The desk work is this staging's own arithmetic and
geometry over the recorded demand and recorded linkage theory; no
verdict on the C task is claimed by this document, and no engine
commitment is made by it.

## The method (per the fold's freeze)

Desk-only, read-only; amplitude-only scope: can an eight-bar's output
member swing >= 177.000 deg -- the C demand's unwrapped swing floor
-- between the two handoff phases. The two-step structure per the
fold: amplitude now; pose-precision-at-amplitude the NEXT question,
never read into an amplitude pass. The honest inconclusive branch is
read before staging, never defaulted past. No runs; no engine
invoked; the derivation is class-level existence geometry, declared
honestly as such (no eight-bar engine exists -- this is NOT a claim
about any recorded parameterization).

## The recorded inputs (read-only, this staging's own reads)

- The C demand (jobs/flip-station-capability-01/JOB.md, the carried
  brief, frozen): the 180 deg face flip as three ordered poses
  0 / 90 / 180 deg, handoffs at x = -130 and +130 mm on the carry
  plane y = 50 mm, tolerances 1.5 mm position / 1.5 deg orientation
  at the handoffs.
- The swing floor (docs/b2-answer.md, Finding 1, verbatim): "the
  coupler must swing at least 180.000 - 1.500 - 1.500 = 177.000 deg,
  unwrapped, between the two handoff phases", with the recorded
  contrast, verbatim: "The pool's best free swing anywhere in any
  cycle (the recorded D3b, the unwrapped full-cycle coupler-angle
  range) is 156.452 deg -- a deficit of 20.548 deg below the
  minimum" -- the strongest shape-reachability evidence on record.
- The recorded six-bar all-fail (jobs/flip-station-sixbar-01/JOB.md):
  honest all-fail on all three seeds, the orientation/derivative
  channel binding as frozen, joint-C transmission hard-fail.
- The frozen eight-bar trigger (jobs/case-d-family-desk-01/JOB.md),
  verbatim: "fires at D's capability step, never mid-loop"; its input
  (i) is path shapes outside the six-bar parameterization's reachable
  classes, "NOT a near-miss".
- The cost-of-entry record (the same JOB, Candidate B): nothing
  recorded for the eight-bar; a new multi-loop position analysis,
  audit harness and run discipline built from zero. This derivation
  changes none of it.

## Step 1: the demand's amplitude floor

The floor is arithmetic from the recorded demand, quoted verbatim in
the inputs above: the part swing between the handoff poses is 180.000
deg demanded at 1.500 deg tolerance per pose, so the unwrapped swing
floor is 180.000 - 1.500 - 1.500 = 177.000 deg. THE AMPLITUDE
QUESTION: can an eight-bar's output member (the member carrying the
part, the rigid-mount class B2 diagnosed) swing through >= 177.000 deg
unwrapped between the two handoff phases? Amplitude only: nothing in
this pass reads pose precision, position tolerance, transmission
quality, envelope, or any other C gate.

## Step 2: the single-loop contrast (the four-bar bound)

The cheapest contrast is the single planar four-bar loop, driven by a
fully rotating crank (the recorded machine drive class). The chain,
visible end-to-end:

- The output rocker (length r, ground pivot P, crank pivot O, ground
  OP) reaches its angle extremes exactly where the crank and coupler
  align (the crank-coupler toggle, the rocker's zero-velocity
  configurations): there |OB| = c - a or c + a, with a the crank and
  c the coupler. Between toggles the rocker is confined to the band
  |OB| in [c - a, c + a] on its own circle.
- On the rocker's circle, |OB| runs as a single sinusoid in the
  rocker angle (one minimum toward O, one maximum away), so the band
  is either two arcs (when c - a > |OP - r|) or one contiguous arc
  through the near point (when c - a <= |OP - r|).
- Contiguity requires c + r <= a + OP. Strict Grashof with the crank
  the shortest link requires a + longest < (the sum of the other
  two); whichever link is longest, adding the two inequalities forces
  c + r < a + OP, so contiguity FAILS for every strict crank-rocker,
  with equality only at the special-Grashof change point (all four
  links colinear). A strict crank-rocker therefore always oscillates
  inside one two-arc band component, of arc length
  arccos(k2) - arccos(k1) < 180 deg strictly (the limit 180 needs the
  degenerate endpoints k1 = 1 and k2 = -1 simultaneously -- the
  colinear configuration again).
- This staging's own probes, recorded as data: a strict-Grashof
  crank-rocker nowhere near any degeneracy (a = 1, c = 4.4, r = 2,
  OP = 3.5; s + l = 5.4 < 5.5) swings 86.8 deg; the floor's swing
  appears only in the near-parallelogram neighborhood (a = 0.9998,
  c = 0.9999, r = 1, OP = 1; s + l = 1.9998 < 1.9999, still strict)
  at 178.0 deg -- links equal to within ~0.02 percent, five times
  tighter than the recorded 0.10 mm manufacturing class at the 100 mm
  part scale (~0.1 percent), with the change-point colinear pass AT
  each swing extreme.

THE SINGLE-LOOP READING: a crank-driven four-bar's output oscillates
strictly inside 180 deg, and the floor 177.000 deg is reachable only
inside the degenerate neighborhoods (the change-point family; the
near-parallelogram limit), where the assembly branch is indeterminate
at the colinear pass and the honest design discipline recorded on
this project (the dead-point rows precedent) refuses the claim.
Outside those neighborhoods, well-conditioned crank-rocker swings sit
far below (the probes: 86.8 deg at the well-conditioned end). One
honest note: a NON-Grashof four-bar (no fully rotating crank) can
oscillate an output past 180 deg, but its input oscillates too -- the
drive question merely relocates one composition stage upstream, and
the composition answer below covers it.

## Step 3: the loop-composition construction (the amplitude answer)

The eight-bar's defining freedom over the single loop is composed
oscillation: an output member pivoted on a CARRIER link that itself
oscillates, driven through its own loop. The absolute orientation
change of the output member between two phases is exactly

  delta(output, absolute) = delta(carrier) + delta(output relative to
  the carrier)

-- the additive composition identity for rigid-body rotations about a
moving pivot, visible end-to-end. Each composed stage is a
four-bar-class loop oscillating WELL inside the single-loop bound, far
from every degenerate neighborhood. Constructively: two stages each
swinging 88.500 deg compose 177.000 deg exactly; stages at the
well-conditioned probe's class (86.8 deg, with room to the ~120 deg
still-honest region) compose 180-240 deg. The eight-bar carries
three independent loops: two carry the composition, and the third
remains for the pose-precision machinery the NEXT step would freeze --
never read here.

ANSWER: YES -- an eight-bar's output member can swing >= 177.000 deg,
by the loop-composition construction with both composed stages
well-conditioned. The demand's swing floor sits at roughly half the
two-stage composed class envelope. NOT NEAR-REACH at the class level.

Two honest notes, recorded as data:

- The composition structure exists at TWO loops as well (a six-bar
  topology: output member pivoted on a moving carrier, tied by its
  own rod to ground). The recorded six-bar family's own output body
  already floats between two moving links (the recorded motion
  task's output body D-C, carried between body A-B-D and rocker
  C-R) -- so the recorded pool ceiling (156.452 deg) is a POOL datum
  over the frozen parameterization's searched ranges, never a
  topology bound, exactly as B2 recorded. Whether the RECORDED
  ranges compose to the floor is NOT claimed here.
- A full-rotation output member (a composed crank) trivially exceeds
  any swing amplitude, but the C demand's shape is out-and-back (the
  recorded return stroke, 0 -> 180 -> 0 per cycle); the relevant
  class is oscillation, and the answer above is the oscillation
  answer.

## Step 4: what this pass does NOT read (the two-step structure)

- Pose precision: whether an output member AT >= 177.000 deg
  amplitude can also serve the three poses at tolerance (1.500 deg
  orientation per pose, the 90 deg mid pose, 1.5 mm position at the
  handoffs) is the NEXT question -- its own derivation, staged
  behind this one, never read into an amplitude pass. Amplitude
  answers existence, never precision.
- The other C gates (transmission, envelope, the handoff backlash
  channel, keep-outs): untouched by this pass.
- The trigger: the frozen eight-bar trigger is D-scoped -- "fires at
  D's capability step" -- and its input class is a confinement
  demonstration, never an amplitude construction. It is NOT FIRED by
  this document; the question it settles is recorded UNSETTLED on
  the input-class question, exactly as the fold recorded. A family
  build commitment requires the trigger's own declared amendment,
  never a reinterpretation.
- The authorization question: the fold's words carried -- the
  re-entry is the first option on any card that COULD create an
  authorized context; the authorization question resolves at the
  capability step's outcome, never before. This derivation
  manufactures no context; it records the amplitude datum only.
- Cost of entry: unchanged (the Candidate B record stands; nothing
  here stages or commits a build).

## Step 5: the near-reach placement

The class-level answer has margin: 177.000 deg at roughly half the
two-stage composed envelope. The placement guard stands per the fold
(delta 3's lesson): if the re-entry task is later designed at the
amplitude margin -- parameter ranges trimmed to just clear the floor
-- that choice must be made on task merits, never a difficulty tuned
to keep the supplier question alive. Recorded as the pre-standing
guard on this line.

## The honest inconclusive branch: read, NOT taken

The derivation is conclusive on its single question: the floor is
arithmetic from the recorded demand (177.000 deg, verbatim); the
single-loop contrast is the toggle-band argument with its degenerate
neighborhoods identified and probed; the composition is the additive
orientation identity plus a construction with both stages far from
degeneracy. No step defaulted past an ambiguity; the read precedes
the staging, as frozen.

## The wide-fail branch: pre-stated, NOT taken

Had the derivation returned NO (the composed class envelope below
the floor), the supplier consequence was pre-stated per the fold: the
supplier question is not reached again in this context, the supplier
triggers stay unfired -- (b) unfired -- and the flip demand would
record as amplitude-infeasible in the composed family classes. The
branch was read before staging; it did not fire.

## Honest scope of this check

- Class-level existence geometry, never a recorded-engine claim: the
  construction is topology plus parameter-range arithmetic; no
  eight-bar engine exists and none is committed by this document.
- The margin is an existence margin, never a design margin: ranges,
  branch signs, transmission, envelope and pose precision are
  build-time derivations, each behind its own freeze per the
  family-build pattern.
- The recorded pool ceiling (156.452 deg) keeps its meaning: a pool
  datum over the recorded parameterization's searched ranges; this
  derivation does not amend it.
- The demand's other rows are untouched; no verdict on the C task is
  claimed.
- The desk reads are exactly the fold's named record set (the carried
  brief, B2's Finding 1, the six-bar all-fail record, the frozen
  trigger text, the cost-of-entry record); no run, no solver
  execution, no corpus touch, no script.

## Sequencing

The strategy fold (entry85) -> THIS DERIVATION (step 1, amplitude) ->
Jean's merge -> step 2 (pose-precision-at-amplitude) and the re-entry
freeze (the task, the demand rows, the family decision on the record)
on Jean's go -> the capability step, where the authorization question
resolves. The owner executes every run; nothing auto-runs at staging.
On this staging's merge the merge records as its own continuity entry.

## Status

Derivation staged (2026-10-21, branch case-c-flip-derivation-01):
desk-only, docs-only, additions-only; no script staged, no run
claimed, nothing built, no machine step before or after the merge; no
recorded outcome amended. The amplitude answer is frozen above: YES --
an eight-bar's output member can swing >= 177.000 deg by the
loop-composition construction with margin; the single-loop contrast
(strictly inside 180 deg, the floor reachable only in the degenerate
neighborhoods) recorded with its probes; the trigger question
UNSETTLED, never fired; the authorization question parked exactly as
the fold recorded. NEXT: Jean reviews and merges; step 2
(pose-precision-at-amplitude) and the re-entry freeze follow on his
go.
