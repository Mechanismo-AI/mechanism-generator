# Job dualcam-lever-transfer-06: case study B family succession -- the Option B cam + lever design study (the dual-cam cross-slide with a pivoted lever on the x axis), deterministic (script, no solver run)

**Purpose.** The recorded -05 outcome engaged Option B under
the frozen decision rule: cam x failed wide -- arithmetically,
not by search -- and cam y held, the family's first HELD
engineering gate. This job is Option B's Stage 1: a deterministic
design study of the dual-cam cross-slide with a single pivoted
lever interposed on the x axis, synthesized and audited
analytically under the same frozen scorecard. No solver run, no
engine or spec change: the deliverable is the committed design
script, its fail-closed validation of the frozen task, the
engineering audit against the frozen G2 branches, the
family-cost table with the lever's additions, and a staging
disclosure that records where the first staging declaration was
falsified and re-derived. Staged by the lead chat per Jean's
governance statement (2026-10-18): the lead drafts and stages,
the actor and critic chats give feedback via the debate round,
Jean reviews, merges and decides. All feedback from the
2026-10-18 Option B debate round is adopted; the adopted
refinements are folded into the design and the scorecard below.

**The succession evidence (recorded data, never rewritten).**
The -05 record: Option A's x follower carries the full 260 mm
stroke, and at the frozen task's knot speeds it needs a pitch
major radius of 511.609 mm at the 30 deg target (389.97 mm at
the 45 deg gate) against the 285 mm cap -- no base circle the cap
allows can rescue it. Cam y HELD (worst pressure angle
25.8817 deg, required major radius 246.098 mm inside the cap)
and carries into Option B unchanged, as the proof the y-axis cam
is sound; its audit is the verbatim -05 code path. The frozen
rule: Option B under the same scorecard, never a fifth
gap-transfer linkage variant. To that rule this JOB adds the
terminal branch the critic required declared before the run: if
Option B itself fails wide, no further variant is staged; the
recorded finding returns to the brief level with Jean (task
renegotiation -- e.g. the envelope with the brief owner -- or a
different family). An undeclared terminal branch is how a
project ends up staging a fifth variant by accretion; it is
declared here, frozen.

**The design (Option B).** The y cam keeps its translating roller
follower verbatim. On the x axis a single pivoted slotted lever
is interposed: the cam's roller rides the lever's short arm, and
the lever's radial slot engages a pin fixed on the x cross-slide;
the tool point is the composition of the two slide coordinates,
exactly as in Option A. The lever is parametrized in full: pivot
P = (Px, Py), short arm A, and a fixed inter-arm angle Delta from
the pin arm to the roller arm (Delta = 0 is the straight lever of
the brief's first-order reading; a nonzero Delta is a bell crank
-- still one link, one pivot). Pivot placement and Delta are
design-script outputs under declared constraints (the actor's
adopted refinement), never hand choices. The cam lift demand
shrinks by the effective ratio lambda_eff = L/A, which varies
over the stroke: the rocker map is nonlinear, the lever is not a
linear gearbox (the actor's theme), and the exact synthesis
inverts it -- the cam profile is the pre-distorted image of the
task-space demand, and all continuity requirements and
derivative cost comparisons are evaluated in slide space (the
critic's point 1, adopted: C1 in cam space would map through the
rocker nonlinearity to a non-C1 slide velocity). The lever adds
one interface of its own, the slot on the pin: its pressure angle
beta_out = atan(|x_s - Px| / |Py|) has a declared gate mirroring
the cam branches (30 deg target / 45 deg hard; the actor's
proposal, seconded by the critic) -- uniform branches, clean
decision rule. G3 is audited at the slide, after the lever, where
the task-space claim lives. The three six-bar structural misses
remain features here exactly as in -05: the process stops are
zero-velocity instants of the clamped timing (exact 0 at
theta = 0 and 120 deg, machine-checked at the slide), the tool
orientation is 0 by construction (both slides translate), and
path straightness is inherited from the analytic path law; the
x cam's true coordinate dwell arcs (concentric pitch circles over
the descent and ascent carries) survive the lever map exactly,
witness-checked.

**The frozen demand, byte-identical.** This job consumes
`jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json`
read-only. No task file is added, modified or copied by this job;
the script records the file's SHA-256 at run time as the
byte-identity witness, and its first act is a fail-closed
validation: an independent analytic reconstruction of the loop
and of the two clamped timing runs must reproduce all 36 sample
values of the frozen task to 1e-9 normalized units, or the script
exits nonzero. The -02 demand is reused byte-identical so the
family-cost comparison against the recorded six-bar frontier and
the -05 Option A record is apples-to-apples.

**The size cap, derived (unchanged lineage from -05), and the
combined envelope (the critic's point 4, adopted).** The
compact-transfer benchmark's 600 x 600 mm envelope (the
debate-declared anchor recorded in -05) gives plate diameter
<= 600 mm and the pitch major-radius cap 300 - 15 = 285 mm at the
first-cut roller radius. New in Option B: the size check is
combined, not per component -- the swept plate/roller discs about
the one shared shaft, the declared x-slide hardware box
([-150, 150] x [-25, 75] mm), the pivot boss (radius 20 mm,
inside the envelope) and the lever sweep including the pin range
must fit the 600 x 600 mm plan view simultaneously: two cams that
each fit can still collide. Both plates are centred on the shared
crank shaft, declared at the plan-frame origin O = (0, 0) (the
-05 convention: the two cams are axially stacked on one shaft and
share the plan view). Packaging is the -05 axial-stack
convention, declared: the plates, the lever and the slides occupy
separate parallel planes, so plan-view overlap is packaging, not
interference.

**The declared scan (frozen before the staging runs).** Coarse
4 deg grid: Px in {-24, -12, 0, 12, 24} mm, Py in
+- {225, ..., 275} mm step 5, short arm A 60-200 mm step 10, and
Delta bracketing the two analytic mid-radial orientations
((P - O) . u_hat = -A, the first-order pressure-angle optimum) at
+- {0, 4, 8} deg, so the pick is not welded to the analytic
estimate. Hard constraints at every candidate: the winding
monotonicity condition (< 1), the 285 mm cap, the slot-angle
gate, the >= 60 mm base (tangent-length) bound, and the pivot
boss inside the envelope; the coarse 32 deg alpha workload bound
is a bound, not a gate. Each A with a screened candidate is
refined on the 1 deg grid (Px +- 6 mm at 1 mm, Py +- 6 mm at
2 mm, Delta +- 3 deg at 0.25 deg) and evaluated on the full
0.1 deg grid. The pick rule, frozen from the debate: the
smallest effective ratio that meets the 30 deg target inside the
cap -- the largest A whose FINAL 0.1 deg audit holds the target
with the hard constraints; A is ascended in 1 mm steps from the
largest passing coarse A with warm-start refinement, each step
gated by its own final audit; if no A meets the target, the best
refined candidate is returned for the branch record
(best-recorded mode). The knee table is emitted so the A pick is
visibly at the knee, and the pick-at-the-edge flag records how
far the largest workable A sits above the declared range floor
(the actor's rule: a pick hugging a declared edge is flagged,
never silent).

**The script.** `dualcam_lever_design.py` in this directory
(71,860 bytes at staging): pure Python standard library (math,
json, hashlib, sys), no network, no packages, deterministic (no
time, no randomness). It runs in about 15 seconds including the
double determinism audit. Sections: [A] the fail-closed task
validation; [B] the analytic synthesis of both cams on a 0.1 deg
grid (3600 points per cam) with the dwell-arc map; [C] the
engineering audit -- the declared scan, the oscillating-follower
pressure angle, pitch-curve curvature with the geometric
body-side undercut test, the winding condition, the slot-angle
gate, the size cap, the combined envelope, the knee table and
the frozen branch verdicts; [D] the family-cost table with the
recorded -01/-02/-04 frontier and the -05 Option A record embedded
as data, plus the lever's additions; [E] the witnesses; [F] the
scorecard reading. Conventions recorded in the script docstring
and frozen here: the lever parametrization (pin-arm direction
psi(th) = atan2(-Py, x_s - Px), the ray meeting the pin line
exactly); the oscillating-follower pressure-angle derivation
(tan(alpha) from the pitch-curve tangent and the common normal,
with the -05 in-line translating follower as the verified special
case -- one formula family for both cams); the angle undefined at
exactly zero follower velocity, those grid points masked, counted
and reported; the curvature convention with the geometric
sign-free body-side test (the dwell circles read negative signed
rho with the centre at the shaft -- this parametrization's left
normal -- witness-checked, so a manufacturing-savvy reader is
invited to check the sign convention against the docstring, as
in -05); and the packaging convention above.

**Staging disclosure (honesty note; three staging runs,
bracketed).** The first declaration was falsified by its own
staging run, and this JOB records the falsification as data.
Declaration 1: the straight lever (Delta = 0), the pivot
hand-frozen at P = (0, -240) mm, the shared shaft scanned in a
region (Ox in [-150, 150], Oy in [-60, 40] mm), and an in-plane
pivot-to-plate clearance screen |P - O| >= major + 35 mm.
Staging run 1 (Python 3.12.13) read "cam x: NO feasible design in
the declared scan region": the scan returned nothing, the frozen
terminal branch printed (on a staging artifact, not physics), and
the no-design report path then crashed with a KeyError (exit
nonzero). Three findings, all staging errors, not mechanism
physics: (a) the true straight-lever optimum from the staging
probe lies outside the declared shaft region (about 31.6 deg at
A = 70, with the shaft roughly 248 mm to the side); (b) the
critic's combined swept-envelope row (adopted) forces the shaft
near the envelope centre -- the swept disc about the shaft is the
plate at its operating radius, and a central shaft makes the
lever sweep tangential to the roller arc, alpha about 54-90 deg
-- so the straight lever with a central shaft is arithmetically
dead under the adopted packaging row; (c) the clearance screen
was mis-derived (the plate profile sits inside the pitch major by
the roller radius; the correct in-plane demand would have been
major + 5) and is unnecessary under the -05 axial-stack
convention. Re-derivation: the shaft fixed at the plan-frame
origin with both plates centred on it; the lever general (Delta
free); the pivot and Delta as scan outputs per the actor's
refinement; the mid-radial analytic orientation as the Delta
bracket; the >= 60 mm tangent-length base bound replacing the
mis-derived screen; and the combined bbox row carrying the
packaging check. Staging run 2 then read cam x HELD -- but the
ascension-stop verification (this staging pass, before any record
was written) caught a refinement artifact: the warm-start
baseline carried its alpha reading from the A it was last refined
at, anchoring the 1 mm ascension to a stale reading and printing
a constant "refined" column in the knee table. The fix re-reads
the warm start on the refinement grid at its own A before any
comparison; it found a strictly better design under the same
frozen gates: the pick moved from A = 72 (P = (18, -260),
Delta = -75.1485 deg, lambda_eff 3.611-4.155, beta_out 29.6499
deg, major 284.914 mm) to A = 76 (P = (8, -260),
Delta = -74.3985 deg, lambda_eff 3.421-3.873, beta_out 27.958 deg,
major 284.932 mm) -- smaller force/tolerance/inertia
amplification and more slot-angle headroom, and no gate touched.
Staging run 3 (the staged reading below) is the post-fix run;
runs 2 and 3 are bracketed here. The recorded machine step
remains the the-hub run; because the script is deterministic, the
the-hub output must reproduce the staged reading, and any
divergence is a finding to record, not noise.

**Staging smoke-test reading (2026-10-18, staging workstation,
Python 3.12.13).** Task file SHA-256 at staging:
591a562c33b7455476e20559fdd16f46bb0c1a3c4645d4a25048e4607e3a24d5.
Staging stdout SHA-256 (11,583 bytes):
98e288bb7515318c3c845369eb6aa0baa2bc427c3da96966845a8306fb75f9de;
two separate staging process runs byte-identical.

- [A] Task validation PASS: max |dq| = 5.551e-17, max |dv| =
  4.441e-16, max |da| = 6.051e-15, all far inside the 1e-9
  fail-closed tolerance; knot speeds reproduce the -02 record
  (159.61 / 106.406 / 115.636 / 102.176 / 112 / 108.725 mm/rad).
- [B]/[C] cam y (carry-in, verbatim -05): HELD -- worst pressure
  angle 25.8817 deg at theta 332 deg; required major radius
  246.098 mm (30 deg target), inside the 285 mm cap; curvature
  passes (min positive rho 98.3361 mm); peak |h''| 695.99
  mm/rad^2 (2.52962 normalized) at theta 300 deg.
- [B]/[C] cam x pick (scan output): A = 76 mm, P = (8, -260) mm,
  Delta = -74.3985 deg; lambda_eff = L/A in [3.42105, 3.87307]
  over the stroke; roller-arm swing -9.53595 -> 43.5595 deg;
  slot angle beta_out = 27.958 deg (gate <= 30 target / 45 hard);
  slot travel demand 34.3535 mm (pin-arm L in [260, 294.354] mm;
  pin size undeclared, forces unrated); dwell pitch radii
  284.932 mm (+130 dwell) and 216.997 mm (-130 dwell); base
  circle 216.997 mm; major radius 284.932 mm -- 0.068 mm inside
  the 285 mm cap.
- [C] cam x final 0.1 deg audit: worst pressure angle 29.7366 deg
  at theta 303.9 deg (the left-arc segment after the return
  junction, path segment 4); masked zero-velocity points 2672 of
  3600 (the two stops, the two x dwells, two arc junctions); min
  body-side |rho| 176.774 mm (undercut gate 18.75 mm; most
  negative signed rho -917.493 mm reported as data); peak
  slide-space |x_s''| 812.885 mm/rad^2 (2.95448 normalized --
  the -05 recorded task demand, unchanged by the lever); peak
  cam-space |C''| 193.927 mm/rad^2 (the pre-distorted profile
  demand: the profile is manufactured to this, not to the slide
  law); winding max 0.0623329 (< 1). VERDICT: HELD.
- [C] the knee (coarse -> refined -> final, final on the 0.1 deg
  grid): A = 60: 28.257 deg; A = 70: 29.230; A = 80: 30.2133;
  A = 90: 31.2691. The 1 mm ascension from A = 70: 71: 29.2840,
  72: 29.3435, 73: 29.4552, 74: 29.5228, 75: 29.6291, 76: 29.7366
  -- and A = 77 stops the ascension on the CAP, not the angle:
  its final alpha 29.9208 deg would still meet the 30 deg target,
  but its major radius 285.3791 mm breaches the 285 mm cap by
  0.3791 mm. The pick A = 76 is cap-limited at the top of the
  knee and holds the cap by 0.0678 mm; its angle headroom is
  0.2634 deg. The pick-at-the-edge flag: A = 76 sits 16 mm above
  the declared range floor 60 mm.
- [C] combined envelope: plan-view bbox exactly 600 x 600 mm
  (x [-300, 300], y [-300, 300]) -- the swept discs about the
  shared shaft, the slide box, the pivot boss and the lever sweep
  simultaneously; the binding component is the cam-y plate at its
  cap-limited operating radius 300 mm (cam-x plate 299.932 mm).
  The envelope is exactly consumed: Option B fits because the two
  plates share the plan view under the axial-stack convention,
  and nothing is left over.
- [D] lever additions (data; forces and masses unrated): reflected
  inertia lambda_eff^2 = 11.7036-15.0007; tolerance
  amplification lambda_eff = 3.42105-3.87307 at the slide (the
  -05 queued trigger is now ARMED -- see open questions);
  per-unit-load shaft torque proxies cam x peak |x_s'| = 170.25
  and cam y peak |h_y'| = 119.816 mm/rad; parts: 2 plate cams +
  2 roller followers + 1 pivoted slotted lever + pivot pin +
  2 guided slides + return springs vs one six-bar (6 links,
  7 pins).
- [E] witnesses: stop SLIDE velocity exactly 0 at theta 0 and
  120 deg (audited at the slide, after the lever); stop follower
  velocity exactly 0 on cam y; round-trip witness (emitted pitch
  curve -> rotation -> roller -> lever ray -> pin line -> slide)
  worst |pin_x - x_s| = 5.116e-13 mm over all 3600 grid points;
  task reproduction through the full chain worst |dq| = 3.886e-16
  normalized; dwell-circle curvature witness worst relative error
  3.990e-16; tool yaw 0 at all 3600 grid points; determinism PASS
  (two independent full audits byte-identical).

**Machine.** Any machine with Python 3.8 or newer (pure standard
library, no venv, no packages, no network). The recorded run
machine is the-hub (any Python 3).

## Steps

From the repository root:

```sh
python3 jobs/dualcam-lever-transfer-06/dualcam_lever_design.py
```

The default task path is the frozen -02 file; `--task` points at
a copy if needed. The full stdout is the record (the outcome
section, when the run happens, will carry it verbatim).

## Prediction scorecard (frozen before the recorded run; the staging reading in brackets)

- **G1 (task synthesis): HELD by construction -- and
  machine-verified, never asserted** (as in -05): the fail-closed
  1e-9 validation plus the chain witnesses (round trip through
  the emitted pitch curve and the lever; task reproduction at
  the twelve phases). The trivial hold IS the finding: the
  family meets the position demand identically because it is
  synthesized from the same law, now through the exact lever map.
  [staging: HELD, worst 6.1e-15; chain reproduction 3.9e-16]
- **G2 (PRIMARY engineering gate), per cam, the same frozen
  branches (<= 30 deg HELD; > 30 and <= 45 narrow; > 45 wide;
  undercut gate min body-side |rho| >= 1.25 x 15 = 18.75 mm), plus
  the lever's own interface:** the slot pressure angle beta_out
  has a declared gate mirroring the cam branches (30 deg target /
  45 deg hard). The margin distribution is reported, not just the
  worst value: the junction table is the risk map. [staging: cam x
  HELD, worst 29.7366 deg, major 284.932 mm <= cap 285 mm,
  body-side curvature passes (min |rho| 176.774 mm), beta_out
  27.958 deg PASS, winding 0.0623 < 1; cam y HELD (carry-in),
  worst 25.8817 deg, required major 246.098 mm]
- **The prediction, frozen as a band with named risk factors,
  never a margin gate (the critic's point 2, adopted):** lean HELD
  for cam x at the pick, boundary-honest -- the staged major
  radius holds the cap by under 0.1 mm, the worst pressure angle
  holds the target by under 0.3 deg, and the slot angle holds its
  target by about 2 deg. The named risks the machine run
  resolves: the 0.1 deg grid maxima are the recorded values (the
  worst-angle point sits in the left-arc segment after the
  masked return junction), the cap headroom is 0.068 mm, and the
  pick is flagged 16 mm above the declared A-range floor. NO
  percentage-margin gate is added: the decision rule runs purely
  on the declared gates (the cap, the 30/45 branches, the
  undercut margin, beta_out). After -05's arithmetic refutation
  of a point lean, the prediction names its own uncertainty
  instead of repeating the pattern.
- **G3 (stop velocity): zero by construction, machine-checked at
  the slide** (after the lever -- the task-space claim; zero at
  the cam contact implies zero at the slide through the smooth
  static lever map, but the audit belongs where the claim lives,
  and auditing there exercises the whole synthesis chain end to
  end -- the actor's answer, the critic's confirmation).
  [staging: HELD, exact 0 at the slide]
- **G4 (family-cost table): emitted with the debate's additions**,
  all adopted: part count and manufacturing complexity (including
  the bell-crank note: one link, one pivot, non-collinear arms);
  the junction derivative comparison restated in slide space (the
  task-space comparison the scorecard makes; the lever's map does
  not divide it out cleanly); the recorded -01/-02/-04 six-bar
  frontier and the -05 Option A record carried as data, not a
  summary; reflected inertia lambda_eff^2; tolerance
  amplification lambda_eff (with the -05 trigger now armed);
  per-unit-load shaft torque proxies (rated forces queued); the
  combined swept-envelope row (the critic's point 4 -- the row
  that falsified staging declaration 1); the pick-at-the-edge
  flag (the actor's rule); and the force-closure split (rise =
  pressure-angle problem, dwell/carry = static spring problem)
  with the lever's re-derivation, dwell-jump case included,
  queued with its trigger. [staging: emitted]
- **G5 (control):** the -02 task consumed read-only with its
  SHA-256 recorded; two-run determinism byte-identical; any
  divergence between the staged reading and the recorded run is a
  recorded finding. [staging: PASS]

**Decision rule (frozen before the run).** A confirmed cam-x HELD
closes the Option chain: the family's first HELD x-axis
engineering gate inside the envelope, and the two armed triggers
(the profile-tolerance -> path-error mapping; the
force-closure/spring re-derivation with the dwell-jump case) go
to the debate channel before any new job stages. A narrow fail
(30-45 deg at every reachable pick) goes to the debate channel as
a declared-scan question -- an A step-down or a Delta re-pick
within the declared scan, never a silent redeclaration. A wide
fail (> 45 deg) fires the terminal branch, frozen above: no
further variant is staged; the finding returns to the brief level
with Jean. No gate is loosened anywhere: 30/45 deg, the 1.25x
curvature margin, the 285 mm cap and the read-only -02 task are
untouched, and the -05 wide-fail record stays recorded data.

**Stage 2 (declared conditional, and expected never to fire).**
Stage 2 -- the solver seed protocol -- exists only if Stage 1
leaves a genuine search problem. The scan is deterministic
design-space narrowing under frozen gates, not a solver search;
with the pick recorded, the profile is fully determined
analytically on both axes. The prediction, frozen: Stage 2 never
triggers, and its non-triggerment is itself the family finding
(analytic synthesis replacing search, now on both axes).

## Readings to report

- The full script stdout from the-hub (the verbatim record),
  plus the python version line.
- The G1-G5 verdicts against this scorecard, with the per-cam G2
  branches, the slot-angle gate reading, the knee table and the
  ascension-stop reason (expected: cap-limited at A = 76 exactly
  as staged -- the size cap binds before the 30 deg angle target
  at the top of the knee).
- Any divergence from the staged reading (expected none; the
  script is deterministic and was verified byte-identical across
  two process runs at staging, stdout SHA-256 recorded above).

## Honest scope

- Forces, masses, spring rates and the return-spring sizing are
  unrated throughout, as in -05; the lever scales the contact
  force by lambda_eff for a given slide load and the reflected
  slide inertia at the cam by lambda_eff^2 (11.7036-15.0007,
  recorded as data). The force-closure re-derivation with the
  dwell-jump case is queued with its trigger.
- The profile tolerance -> path-error mapping is now ARMED: the
  -05 open question named its trigger (a fine-grid G2 pass), this
  job claims one, and the lever amplifies cam-x profile error by
  lambda_eff = 3.42-3.87 at the slide. The mapping is queued, not
  forgotten, and goes to the debate channel before any
  manufactured-profile claim.
- The 600 x 600 mm envelope is the debate-declared anchor, not a
  repo record; the combined bbox consumes it exactly (binding:
  the cam-y plate at 300 mm), and the fit exists only under the
  axial-stack convention (both plates share the plan view). A
  formal envelope spec re-derives the cap arithmetic; the layout
  assumption (slides, guides, springs fit the same envelope) is
  declared, not verified.
- The bell crank: Delta = -74.3985 deg means the lever's two arms
  are not collinear -- one link, one pivot, but a manufacturing
  and complexity row, not a new gate. The slot is radial in the
  lever; the pin size is undeclared (slot travel demand
  34.3535 mm) and the slot's own manufacturing tolerance is part
  of the queued tolerance item.
- The pressure-angle formula for the oscillating follower is
  derived and recorded in the script docstring, with the in-line
  translating follower (-05's convention) as its verified special
  case; the angle is undefined at exactly zero follower velocity,
  and those grid points are masked, counted and reported (2672 of
  3600 at the pick), never silently dropped.
- No operating speed, drive law, payload capacity or motor is
  prescribed; v and a are per crank radian; capacity and speed
  remain unrated, as throughout case study B.
- This job is task-side only: the experimental motion solver and
  the engine are untouched, and no solver run is staged.

## Open questions

- **Profile tolerance -> path-error mapping (ARMED by this job)**:
  lambda_eff 3.42-3.87 amplifies cam-x profile error at the
  slide; the -05 trigger (a fine-grid G2 pass) has fired. Queued
  for the debate channel.
- **Force-closure / spring re-derivation, dwell-jump case
  included**: contact force scales with lambda_eff, reflected
  inertia with lambda_eff^2; the combined shaft torque curve
  needs rated forces (the audit emits per-unit-load proxies
  only). Queued with its trigger.
- A formal declared envelope to replace the debate-declared
  600 x 600 mm anchor -- now with the sharper finding that the
  envelope is exactly consumed by the two plates' swept discs.
- The declared A-range floor (60 mm) and the flagged pick
  (A = 76, 16 mm above the floor): the floor is a debate-channel
  question, not a silent redeclaration.
- A dwell-prescribed task variant (carried from -05, unchanged).
- The six-bar frontier and the Option A record stay on the table
  for any future revisit; none of this rewrites them.

## What we will do with it

The recorded run decides per the frozen rule. A confirmed HELD
is the succession outcome the chain was built for: the dual-cam
family with one lever meets the frozen task inside the envelope at
the 30 deg target on both axes, and the project's next questions
(tolerance, forces) are engineering quantification of a sound
design, not family succession. The armed triggers go to the
debate channel before any new job stages; the recorded
-01/-02/-04/-05 evidence stays recorded data, and recorded
outcomes are never rewritten.
