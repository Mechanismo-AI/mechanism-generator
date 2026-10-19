# Case study C capability: the dual-groove plate-cam flip carrier (flip-station-capability-01) -- staged

Status: **Run recorded (2026-10-19); recorded outcome below.**

The capability step of case study C (the flipper), per the loop:
preceded by its debate round, folded below. Per the fold's Q1, the
cam-lever line stages first and the six-bar line is the recorded
alternative whose trigger fires exactly on the wide-fail branch (C5,
pre-declared below -- the case-B Option-chain pattern: primary,
documented fallback, declared trigger, no third variant without new
evidence). Alongside it, per the fold's Q4, B2's frozen answer schema
is committed (docs/b2-answer-schema.md) -- the ordering rule: B2's
schema commits first (this PR), and the capability step's mounting
declaration uses the same field structure, so B2's eventual answer
lands in a form this study already speaks.

## The demand (carried brief, frozen)

Unchanged from flip-station-failure-01:

- Part: 100 x 60 x 5 mm flat part; the 180 deg flip is an in-plane
  rotation of the 100 x 5 mm cross-section in the machine plane (the
  60 mm width out-of-plane, declared per the planar scope-control
  precedent). 1 normalized unit = 100 mm, the OMTS task-layer
  convention.
- Layout: symmetric handoffs at x = -130 and +130 mm on the carry
  plane y = 50 mm; mid pose at x = 0; orientations 0 / 90 / 180 deg.
- Tolerances: position 1.5 mm (0.015 normalized), orientation 1.5 deg,
  demanded at the handoffs.
- Mass ~31.5 g placeholder with lineage (recorded context, not a
  demand of this run); rate and capacity unrated, as in cases A/B.
- Consumption is read-only: this study consumes the demand, not the
  engine. The recorded failure corpus (36 scored rows, JSON Lines
  fbea95681d26883c9cf46eff9132ea07f31c3f5286baf0cd883671585d11e5c1)
  is the evidence base and B2's declared second data point; no
  search is run and no recorded row is rewritten.

## Fold record (the capability debate round)

Actor's round and critic's round (both relayed by Jean) were folded
by the boss. The fold:

1. Family line (Q1, actor, critic-endorsed, adopted): the failure
   data picks the family -- an orientation-coupled binding failure on
   the four-bar pool is exactly the demand class the oscillating
   cam-lever line claims structurally (the swing is the lever's own
   DOF). Cam-lever stages first; six-bar stays a live recorded
   alternative, not a dead one, with its trigger declared before the
   run (below). "Family-agnostic until the fold" would be deferral
   dressed as neutrality -- the evidence exists, so it is used.
2. Architecture fork (Q2, actor, critic-endorsed, adopted): settle
   the architecture INSIDE the cam family at the desk, before any
   gate freezes. The actor's three candidates: (i) direct
   oscillating roller follower (actor's frozen prediction:
   infeasible or envelope-exploding -- 180 deg of swing is not a
   translating-follower problem); (ii) groove/slot cam driving a
   flip-arm pin (predicted the feasible line; exact analytic
   synthesis, the -05/-06 pattern; pressure angle = groove tangent
   vs pin velocity); (iii) amplification stage (documented third;
   carries the cos-phi lever nonlinearity at full first-order
   strength). Requirements carried onto the derivation: the exact
   kinematic map (no search); the pressure-angle definition for the
   chosen architecture with its worst value over the cycle; the
   curvature gate analog re-derived (the 1.25x precedent value with
   its reason, never an inherited number); the envelope consumed by
   all of lever sweep, part sweep, cam plate and handoff stations
   with the mandatory utilization/headroom table; the motion program
   psi(theta) recorded as a declared synthesized freedom (the case-A
   precedent -- only the three poses are demanded); every gate a
   precedent-value re-derived with its reason.
3. Part-body collision shape (Q3, adopted): the capability audit
   models the part as its exact in-plane rectangle (100 x 5 mm),
   computed by the capability script itself at pose samples --
   honest where a disc approximation would distort (a 58 mm disc
   around the centroid is massively conservative for a 100 x 5
   section and would corrupt the envelope and tolerance readings).
   Sampled, never certified (the sampling-honesty convention). The
   OMTS payload-body vocabulary is deferred with the recorded
   trigger "when a keep-out relation or the line composition gates
   on part occupancy"; the rectangle rows go into the corpus as
   data, so the spec step later lands the vocabulary against
   machine-readable evidence that already exists.
4. Mounting-offset declaration (Q4, adopted): commits alongside
   B2's answer schema, citing it, not behind it. Same field
   structure (mounting vector + angle + frame + lineage); if B2's
   diagnosis later amends the convention, the flipper's declaration
   is amended by a new recorded convention with lineage, never
   silently rewritten -- the outcome-data discipline applied to
   conventions.
5. Corpus succession (Q5, adopted, frozen before either event):
   additive-only. Additive fields or new row kinds (old readers can
   skip them) are schema 1.x, one recorded changelog row per
   addition; any change to an existing field's meaning, unit or
   name is schema 2.0; emitters and readers fail closed on unknown
   major versions. The PR-A rule (bump the moment meaning changes)
   applied to the corpus. This study's additions are a 1.1 bump,
   not a fork; every corpus file pins its version; this JOB's
   outcome section references files by their sha256 hashes.
6. Scorecard skeleton C1-C5 (Q6, adopted) with the critic's deltas
   folded in (below).

Critic deltas, adopted:

1. Drive-reversal backlash is a required budget channel, not an
   optional row. One flip per cycle means the output goes 0 -> 180
   (work stroke, part carried), reverses at the 180 handoff, returns
   180 -> 0 empty, reverses again at the 0 pick-up: both demanded
   poses sit at output-velocity zero and drive-direction reversal --
   where the pin crosses the groove's clearance and the contact edge
   switches. The pin-to-groove clearance maps to pose error at
   exactly the two poses where the brief demands 1.5 mm. Structural,
   not designable away by timing -- only by groove-width class or a
   positive-drive variant. C3 prices the backlash channel at both
   handoffs, channels kept separate. Frozen prediction: the
   backlash channel, not profile class, binds (groove width class
   is harder to hold tight than a milled profile).
2. No derived-looking numbers before the desk derivation runs. The
   arm length, the corner arcs, the transit-height tip position and
   the plate radius are derivation outputs with their derivations;
   nothing downstream quotes them before they exist. (The actor's
   "~130 mm corner arc" was exactly this error -- plausible
   orientation, but the derivation's job to say.)
3. Reciprocity is a scored item, not a closing note. The JOB and the
   report carry an explicit instrument-modification-count row,
   recorded at close: zero modifications = the generator-agnostic
   principle holds; any delta = each one named, family-specific hook
   or genuine gap. This capability step is that principle's first
   live test as defined -- the instruments (WC-L tolerance pattern,
   scorecard conventions, corpus emitter) grade an oscillating-cam
   design, a family none of them were built around. The strategy
   round's Q1 amendment gets its first recorded data point either
   way.

Boss desk-catch (the fold's resolution of Q2, stronger than either
round predicted): all three actor architectures -- direct roller,
single-groove arm, amplification stage -- are fixed-pivot rigid
mounts, and the demand defeats the whole class, not a member: the
three demand centroid points (-1.3, 0.5), (0, 0.5), (1.3, 0.5) are
colinear and distinct, and no fixed-pivot circle passes through
three colinear points. Exact poses-1+3 fit: pivot (0, 0.5), mount
(-1.3, 0); pose 2 misses by exactly 1.3 units (130 mm) -- far over
the 1.5 mm tolerance. The class is pose-infeasible (C1a, recorded
evidence), and the surviving line is the dual-groove plate-cam:
two pins on the carrier ride two closed grooves cut in one
continuously rotating plate; no fixed pivot; the part rigidly
mounted to the carrier; each groove is its pin's path transformed
into the plate frame, G(theta) = R(-theta) * pin(psi(theta)) --
exact analytic synthesis, the case-B -05/-06 pattern. If the two
grooves cross, they ride separate plate faces/layers (the dual-cam
-05 precedent; declared consequence, recorded as data, not a gate --
the brief froze no such demand).

Structural finding (frozen desk prediction): for this demand the
groove is a shallow spiral -- the groove's radial drift per plate
turn is an order below the plate's tangential rate -- so the
fixed-frame pressure angle runs near 90 deg over the carry arc,
with exact structural dead points at plate angles 90/270 deg for
EVERY design in the sweep (the groove locally circumferential,
transmitted power ~ the groove lead; the toggle-position analog for
groove cams). G1 is predicted to WIDE-FAIL structurally, and the
wide-fail fires the six-bar trigger per C5. The dead points are
passed through by the positive-drive constraint set and recorded as
dead-point rows, never as finite numbers.

## The instrument

`flip_capability.py` (this directory): deterministic analytic
Stage 1 -- no engine, no search. Pure stdlib, ASCII only,
deterministic (no clocks, no randomness, sorted keys); run twice
and diff -- byte-identical is the control; fail-closed throughout
(missing field, non-finite number, wrong schema version, unknown
row kind, off-grove pin, rank-deficient tolerance map -- all abort
the run).

- C1a: fixed-pivot class pose-infeasibility -- best-fit pivot and
  mount by least squares over the three poses, worst pose residual
  recorded; the colinearity argument printed; PASS = infeasibility
  evidenced, never asserted.
- C1b: dual-groove synthesis -- pin paths from the smootherstep
  out-and-back program, grooves as the plate-frame transforms,
  closure residuals, and every 5 deg grid pose reproduced by the
  pins-on-grooves construction (constraint residual < 1e-9).
- C2: pose witness -- the demand poses exact by construction at
  plate angles 0/90/180 deg, machine-verified < 1e-12 (the return
  arc revisits pose 2 at 270 deg); construction claims executed,
  never asserted.
- G1: pressure-angle gate over the loaded carry arc (0 < t < 180
  deg): the 45 deg cam-class precedent value re-derived for the
  groove architecture; zero-velocity samples and the structural
  dead-point bands excluded and recorded; the return arc is
  unloaded data; the full-cycle max (dead points included) recorded
  as data.
- G2: curvature gate -- groove min radius >= 1.25 x pin radius
  (4 mm commercial cam-pin class), precedent value re-derived with
  its reason.
- C3: WC-L tolerance budget at BOTH handoff poses, channels kept
  separate: clearance/backlash channel (0.1 mm per side, groove
  width class), profile channel (0.05 mm centerline class),
  combined = their sum; quasi-static settle at the program event,
  min-norm constraint map, worst case over the four clearance-sign
  corners; rank deficiency fails closed with a recorded reason.
  Plus the sensitivity curve on a 5 deg grid (per-unit-bound
  worst-case position gain), dead-point samples recorded as
  dead-point rows, never as finite numbers.
- C4: controls -- read-only demand consumption; fail-closed corpus
  emitter (schema 1.1 pinned, units block + provenance on every
  row, unknown-kind refusal); the envelope utilization table
  present; double-run determinism below.
- C5: frozen scorecard verdicts; every outcome recorded data; the
  wide-fail fires the pre-declared six-bar trigger.
- Envelope: the exact-rectangle part model at 0.25 deg pose samples
  (sampled, never certified); part sweep, plate, handoff stations
  in one utilization/headroom table -- recorded data, not gated (no
  size demand is frozen by the brief; the -06 required-table
  precedent).
- Reciprocity: the instrument-modification count row (0 expected).

## The frozen design space and pick rule

- Design parameters (declared, recorded as data rows): pin offset
  d in {0.1, 0.2, 0.3, 0.4, 0.5} units; plate-center height
  C_y in {0, 0.25, 0.5} units -- a 15-point sweep; pin radius 4 mm;
  plate center on the demand's symmetry axis (x = 0 by symmetry).
- Motion program psi(theta): smootherstep-quintic out-and-back, one
  plate turn per cycle (carry 0-180 deg, return 180-360 deg) -- a
  synthesized design freedom, declared per the case-A precedent;
  only the three poses are demanded.
- Pick rule: among tolerance+curvature-passing designs, the
  smallest G1 gate angle; tie-break larger d, then lower C_y; if
  none passes, the smallest G1 angle anyway -- the wide-fail is
  read on the scorecard, not on the pick.
- C_y = 0.5 rows fail closed: the two-groove constraint pair is
  exactly parallel at both handoffs (pins and plate center
  colinear -- the structural dead point); the tolerance gate fails
  closed with the reason recorded (the C3 map cannot bound the pose
  there).
- Mounting declaration (the B2 seam): part rigidly mounted to the
  carrier -- part centroid at carrier origin, part axes = carrier
  axes (identity mount: mounting vector (0, 0), angle 0 deg, in the
  carrier frame) -- field structure per docs/b2-answer-schema.md;
  amendable only by a new recorded convention with lineage.
- Geometry discipline (the critic's delta 2): the arm/corner arcs,
  the through-vertical transit tip height and the plate radius are
  derivation outputs printed with their derivations; no number
  downstream quotes them before the derivation produces them.

## Frozen prediction scorecard (written before the run)

- C1 (architecture fork): C1a -- the fixed-pivot class is
  pose-infeasible, with the desk construction as recorded evidence
  (predicted: worst pose residual far over tolerance; the
  colinearity argument). C1b -- the dual-groove synthesis closes
  (both grooves closed curves; grid poses reproduced). The actor's
  per-architecture predictions are superseded by the stronger
  class-level finding; recorded as such.
- C2 (pose witness): the three poses exact by construction,
  machine-verified on the emitted grid. Predicted: PASS.
- G1 (pressure angle): frozen desk prediction WIDE-FAIL -- the
  shallow-spiral argument; dead-point bands excluded and recorded,
  the dead-point alpha recorded as data (expected 90 deg at the
  structural dead points). The full-cycle max recorded.
- G2 (curvature): predicted PASS at small d, FAIL at large d (the
  groove corner radius shrinks with d); the 1.25x precedent value
  re-derived with its reason.
- C3 (tolerance at the handoffs): frozen critic prediction -- the
  backlash channel binds over the profile class (the drive-reversal
  story; the two channels kept separate in the report). Frozen
  actor prediction, refutable -- the sensitivity peak is mid-swing
  (through-vertical transit). Both read on the run; dead-point
  samples recorded as dead-point rows.
- C4 (controls): two-run byte-identical determinism; read-only
  demand; fail-closed emitter; utilization table present.
  Predicted: CONFIRMED.
- C5 (honest-fail branch): an all-fail or gate-wide-fail outcome is
  valid recorded data, the corpus exists regardless, and the
  six-bar alternative's trigger fires exactly on the wide-fail
  branch -- stated before the run, not after it.
- Reciprocity: instrument-modification count 0 expected; any delta
  named per modification (family-specific hook or genuine gap).
- Envelope and groove-crossing rows: recorded data, not gates.

## Machine step (in order, maintainer-local, after merge)

From the repo root (the corpus lands under
runs/flip-station-capability-01/, gitignored):

1. `python jobs/flip-station-capability-01/flip_capability.py --source-commit <merged-40-hex-sha> > capability_run1.txt`
2. Run it a second time with the same sha, redirected to
   `capability_run2.txt`.
3. `diff capability_run1.txt capability_run2.txt` -- expect EMPTY;
   exit 0 on both runs; each report ends with the in-process
   "double-run determinism check: IDENTICAL" line. Pure stdlib; any
   Python 3.8+.
4. Record the outcome in this JOB.md against the frozen scorecard,
   referencing the corpus files by the sha256 hashes the script
   prints.

This is a docs+script PR: there is no machine step before the
merge; the machine step above IS the recorded run.

## Staging disclosure (rehearsal, not the outcome)

Maintainer-local staging rehearsal (Python 3.12.13, placeholder
source commit 0x0000000000000000000000000000000000000001): exit 0.
The validation harness (47 checks: finite-difference checks against
the analytic first and second derivatives, groove closure and
on-groove checks, emitter and CSV round-trip checks) passes 47/47.
Disclosed plainly: during staging validation the harness caught and
fixed two real bugs in earlier drafts -- a missing sign flip in the
first derivatives on the return arc (t > 180 deg), and a chain-rule
error in the groove second derivative (+c^2 term where the chain
rule gives -c^2, which changed curvature values substantially).
Two process runs byte-identical; in-process double-run check
IDENTICAL. Rehearsal numbers, placeholder commit -- these are NOT
the recorded outcome; the recorded run re-executes everything on
the merged commit:

- C1a: best-fit pivot (0.000000, 0.175000), mount (-0.975000, 0),
  worst pose residual 1.300000 units.
- Chosen design (pick rule): d=0.2, C_y=0.0 (a_G1 89.314 deg,
  min_rad 0.1947 units).
- G1 WIDE-FAIL (89.070 deg / 89.314 deg gate angles; dead-point
  alpha 90.000 deg); G2 PASS (19.47 / 60.23 mm); groove crossings 4
  (data; separate plate faces consequence declared).
- Envelope: part sweep bbox x [-180.0, 180.0] y [-0.1, 100.1] mm;
  tip height 100.06 mm; plate radius 164.11 mm; headroom 64.1 mm
  (recorded, not gated).
- C3 PASS at both handoffs: backlash 0.6491 mm / 0.5179 deg,
  profile 0.3245 mm / 0.2589 deg, combined 0.9736 mm / 0.7768 deg
  vs 1.5 mm / 1.5 deg. Backlash-binds prediction CONFIRMED.
  Sensitivity peak 81.6658 at t = 315 deg -- NOT mid-swing: the
  actor's mid-swing prediction is REFUTED in the rehearsal (honest
  data; the recorded run re-reads it); dead points at t = 90/270
  recorded as dead-point rows.
- Overall rehearsal reading: WIDE-FAIL -- the six-bar trigger FIRES
  (the pre-declared C5 branch). Capability answer shape: the
  dual-groove plate serves the flip poses exactly and the tolerance
  budget reads on the scorecard, but the recorded gates fail
  structurally.
- Corpus: 838 rows, schema 1.1; rehearsal hashes JSON Lines
  df0023070fe207ad8e96750d0778005453d66db213e40cfebd9b7799009ebb7e,
  CSV f528cd96b508f57ed006dc3971c478615e53b8e03eb8648c41b1c037b7b8b2af.
  The recorded run's hashes will differ -- provenance embeds the
  merged commit.

## Corpus schema 1.1 (additive changelog)

Per the fold's Q5, this emitter declares schema 1.1 over the
flip-station-failure-01 corpus's schema 1: additive new row kinds
(design_parameter, architecture_evidence, groove_summary,
groove_sample, envelope, sensitivity, dead_point, reciprocity,
scorecard_verdict, changelog) plus per-row units and provenance
blocks; no change to any existing field's meaning, unit or name --
one changelog row recorded in the corpus itself. Succession frozen:
additive = 1.x; meaning/unit/name change = 2.0; emitters and readers
fail closed on unknown major versions.

## Trigger bookkeeping (frozen)

- Strategy trigger: condition (a) SATISFIED (PR #70,
  flip-station-failure-01: the honest analytic failure with its
  corpus in the record). Condition (b) -- B2's frozen answer schema
  -- is committed by this PR (docs/b2-answer-schema.md); it CLOSES
  on this PR's merge, after which B2 runs as desk analysis,
  read-only, citing its two data points by hash. The next staged
  item is B1 admission-gate work only after both conditions hold,
  unless Jean explicitly overrides with a recorded reason.
- Six-bar alternative trigger: fires exactly on the G1 wide-fail
  branch (C5, pre-declared above). In the rehearsal it fires; the
  recorded run reads it as data. The decision round takes the
  family question with the trigger state: a class ruling for
  positive-drive groove cams (a renegotiation question, named for
  the decision round, not assumed here) or the six-bar line per
  the fired trigger.
- Part-body vocabulary trigger: deferred with the recorded trigger
  "when a keep-out relation or the line composition gates on part
  occupancy"; the exact-rectangle rows are recorded data against
  the day the spec step lands the vocabulary.

## Recorded outcome (2026-10-19)

The machine step ran on the-hub (the motion venv, Python 3.14.4),
from the repo root, against merged main
9c9fd6f9f1724e683ed053f621f95fe5a283425a (the PR #72 merge). Run 1
clean (exit 0, report 156 lines). The first run-2 attempt left
capability_run2.txt empty (the run did not complete; the redirect
created the file and nothing wrote to it) -- recorded as-run, and
the rerun was clean (exit 0). The recorded determinism pair is run
1 plus the rerun: external diff EMPTY, exit 0; the in-process
double-run determinism check reads IDENTICAL in both reports. All
numbers below are the run's own printed digits.

- C1 CONFIRMED (architecture). C1a: the fixed-pivot rigid-mount
  class is pose-infeasible with the desk evidence executed, not
  asserted -- best-fit pivot (0.000000, 0.175000), mount
  (-0.975000, 0.000000), least-squares worst pose residual 1.300000
  units (130.00 mm) over the 1.5 mm tolerance; the exact poses-1+3
  fit (pivot (0, 0.5), mount (-1.3, 0)) misses pose 2 by exactly
  130 mm (the colinearity argument). C1b: the dual-groove synthesis
  closes -- both grooves closed curves (closure residuals
  3.554e-16 / 4.475e-16 units), every 5 deg grid pose reproduced by
  the pins-on-grooves construction (constraint residual < 1e-9).
- C2 CONFIRMED (pose witness): the three demand poses exact by
  construction at plate angles 0 / 90 / 180 deg, position and
  orientation error 0.0, machine-verified < 1e-12 (the return arc
  revisits pose 2 at 270 deg).
- G1 WIDE-FAIL (pressure angle), the frozen desk prediction read on
  the run: gate angles 89.070 deg (groove_1, t = 92.30) and
  89.314 deg (groove_2, t = 89.25) against the 45 deg cam-class
  gate over the loaded carry arc. The structural dead-point bands
  are excluded and recorded (712 / 548 samples); the dead-point
  alpha is exactly 90.000 deg (the toggle-position analog for
  groove cams, passed through by the positive-drive constraint
  set); the full-cycle max 90.000 deg at t = 90 is recorded as
  data. The shallow-spiral argument is CONFIRMED: the sweep's a_G1
  range is 89.192-90.000 deg -- the gate fails structurally for
  every design in the sweep, not marginally.
- G2 PASS (curvature), as predicted (PASS at small d, FAIL at large
  d across the sweep table): groove min radii 0.1947 units
  (19.47 mm, groove_1 at t = 241.40) and 0.6023 units (60.23 mm,
  groove_2 at t = 240.20) against the 0.0500-unit floor
  (5.00 mm = 1.25 x pin radius).
- Groove crossings: 4 (recorded data, not a gate; the declared
  consequence applies -- the two grooves ride separate plate
  faces/layers, the dual-cam -05 precedent).
- Envelope (recorded data, not gated; the -06 required-table
  precedent honored): part sweep bbox x [-180.0, 180.0] y [-0.1,
  100.1] mm; through-vertical transit tip height 100.06 mm at
  x = -4.11 mm; plate radius 164.11 mm; handoff stations (-130, 50)
  and (130, 50) mm; headroom 64.1 mm.
- C3 PASS (WC-L tolerance at both handoff poses), channels
  separate: clearance/backlash 0.6491 mm / 0.5179 deg; profile
  class 0.3245 mm / 0.2589 deg; combined 0.9736 mm / 0.7768 deg
  against 1.5 mm / 1.5 deg -- identical at both handoffs by
  symmetry. The critic's frozen prediction is CONFIRMED: the
  backlash channel binds over the profile class. The actor's
  mid-swing sensitivity prediction is REFUTED, recorded as honest
  data: the per-unit-bound worst-case position gain peaks at
  81.6658 at t = 315 deg (the return-arc reversal approach), not
  mid-swing; the dead points at t = 90/270 deg are recorded as
  dead-point rows, never as finite numbers.
- C4 CONFIRMED (controls): read-only demand; fail-closed corpus
  emitter (schema 1.1 pinned, units block + provenance on every
  row); utilization table present; double-run determinism
  (in-process IDENTICAL + external diff EMPTY).
- C5 overall reading: WIDE-FAIL -- the six-bar alternative trigger
  FIRES, exactly per the pre-declared branch. All outcomes are
  recorded data; nothing is rewritten.
- Reciprocity: instrument modification count 0 -- the strategy
  round's Q1 amendment (generator-agnostic instruments) gets its
  first recorded data point, clean: the instruments graded an
  oscillating-cam family they were not built around, unmodified.
- Chosen design (frozen pick rule, recorded as data): d = 0.2,
  C_y = 0.0 (a_G1 89.314 deg, min_rad 0.1947 units). The C_y = 0.5
  rows failed closed in the sweep exactly as declared (the
  structural dead point at both handoffs; the WC-L map cannot bound
  the pose there).

Corpus (the recorded outcome, referenced by hash):
runs/flip-station-capability-01/flip_station_capability_v1.jsonl
sha256 cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c
and flip_station_capability_v1.csv
sha256 4edb232c22d58fbab82aa83f3852eb04ec0a5e8544b8fd12ca4b5c08b7679401,
838 rows, schema 1.1 (additive; changelog row in corpus). The
staging rehearsal's numbers reproduced digit-for-digit on the
merged commit; only the corpus hashes differ, exactly as disclosed
(the provenance block embeds the source commit).

The capability answer, recorded as data: the dual-groove plate-cam
serves the flip poses exactly (C1b/C2) and the tolerance budget
reads on the scorecard (C3 PASS), but the recorded gates fail
structurally (G1 WIDE-FAIL: the shallow-spiral lead-angle finding
and its dead-point companions). The family question carries to the
decision round: a class ruling for positive-drive groove cams (a
renegotiation question, named not assumed) or the six-bar line per
the fired trigger.

Trigger bookkeeping (recorded):

- Six-bar alternative trigger: FIRES on this recorded wide-fail,
  exactly per the pre-declared C5.
- Strategy trigger: condition (a) SATISFIED (the flipper failure
  record, PR #70). Condition (b)'s precondition is now MET -- the
  B2 frozen answer schema is on main (merged with this job's
  staging, PR #72), so B2 MAY RUN as desk analysis, read-only,
  citing its two declared data points by hash. The strategy trigger
  fires when B2's answer is recorded in that schema; the next staged
  item is then B1 admission-gate work, unless Jean explicitly
  overrides with a recorded reason.
- Part-body vocabulary trigger: deferred, unchanged ("when a
  keep-out relation or the line composition gates on part
  occupancy"); this corpus's exact-rectangle rows are the recorded
  data for that day.

NEXT per the loop: case study C's decision debate round with the
fired trigger and the class-ruling question on its card; the B2
desk run in parallel.
