# Job dualcam-gap-transfer-05: case study B family succession -- the dual-cam cross-slide (Option A) design study, deterministic (script, no solver run)

**Purpose.** Case study B's task-family loop is closed by the
succession rule: the free-phase run (-04) missed F4 (best
worst-sample position 0.12570 normalized = 34.6 mm vs the 0.1000
bar), and with the no-bottom-stops run (-02) that makes two levers
that missed the position error on the six-bar family. This job is
the family successor's Stage 1: a deterministic design study of
the dual-cam cross-slide (Option A), synthesized and audited
analytically. No solver run, no search, no engine or spec change:
the deliverable is the committed design script, its fail-closed
validation of the frozen task, the engineering audit against the
frozen G2 branches, and the cam-vs-six-bar family-cost table.
Staged by the lead chat per Jean's governance statement
(2026-10-18): the lead drafts and stages, the actor and critic
chats give feedback, Jean reviews, merges and decides. All
feedback from the 2026-10-18 debate round is adopted; the
adopted refinements are listed in the scorecard below.

**The succession evidence (recorded data, never rewritten).** The
six-bar family's best worst-sample position across three task
variants barely moved and the third variant regressed: 0.1484
(-01, four stops), 0.1219 (-02, no bottom stops), 0.12570 (-04,
free phase) -- a plateau at 0.12-0.15 against the 0.01 gate and
the 0.005452 packaging overlay, with the per-lever attribution on
record: bottom stops removed in -02 (position still missed, worst
samples stayed at the process stops, D2 held 3/3), demand
prescription freed in -04 (position still missed; the most
violated demand per seed moved to acceleration 17.94-19.66x its
gate, and seed 580000051 to velocity 19.69x). Neither lever
carried the failure: it is the family's shape freedom, and the
recorded -01/-02/-04 frontier numbers are preserved in this JOB
and in the script's family-cost table so any future revisit (a
dwell six-bar among them) tests against recorded data, not against
a summary. Option C (dwell six-bar) is rejected today exactly
because it inherits that shape-freedom limit; a single grooved cam
does not apply (one dwell groove is one DOF; the loop needs two
coordinates); Option B (cam + linkage hybrid) is the declared
fallback and its trigger is frozen below.

**The design (Option A).** Two plate cams on one crank shaft, each
with a translating roller follower; one cam drives the x
cross-slide, the other the y cross-slide; the tool point is the
composition of the two slide coordinates. The follower
displacement law is the tool coordinate minus its travel minimum:
h_x(theta) = x(theta) + 130 (lift 260 mm), h_y(theta) =
y(theta) + 40 (lift 90 mm), with x, y following the frozen -02
loop and its frozen clamped-cubic-spline timing law, so the pitch
curve of each cam is r(theta) = r_base + h(theta) in polar form
about the cam shaft, fully determined analytically. The three
six-bar misses are structural features here: the process stops
are zero-velocity instants of the clamped timing (follower
velocity exactly 0 at theta = 0 and 120 deg by construction); the
tool orientation is 0 by construction (both followers translate;
nothing rotates); path straightness is inherited from the analytic
path law rather than approximated by samples. Each cam also has
true coordinate dwell arcs (concentric pitch circles) while the
other coordinate moves: cam x dwells over theta 120.00-166.36 deg
(x = +130, the descent) and 313.64-360.00 deg (x = -130, the
ascent); cam y dwells over 0-120 deg (y = +50, the whole carry)
and 180-300 deg (y = -40, the whole return). C1 blending (the
critic's requirement, adopted) is not an afterthought knob: the
composed displacement laws are C1 by inheritance (the -02 path is
tangent-continuous end to end, the timing spline is C2 per piece
and C1 across the stop knots), and the six junctions where the
second derivative is one-sided are reported both-sided in the
audit's junction table. One honest correction to the brief's
wording, recorded up front: under the frozen -02 demand there is
NO finite dwell at the stops, because the task prescribes
nonzero accelerations at the stop samples (the vector-mean
convention, 488.82 mm/rad^2); the stops are zero-velocity
instants, not dwell intervals, and a dwell-prescribed task
variant is a demand change queued as an open question, not a
silent redesign of the demand.

**The frozen demand, byte-identical.** This job consumes
`jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json`
read-only. No task file is added, modified or copied by this job;
the script records the file's SHA-256 at run time as the
byte-identity witness, and its first act is a fail-closed
validation: an independent analytic reconstruction of the loop
(arc-length-parametrized lines and exact 15 mm corner arcs, the
same construction documented in the -02 audit trail) and of the
two clamped timing runs must reproduce all 36 sample values of
the frozen task to 1e-9 normalized units, or the script exits
nonzero. The -02 demand is reused byte-identical so the
family-cost comparison against the recorded six-bar frontier is
apples-to-apples.

**The size cap, derived (the actor's requirement, adopted: the
cap is the growth boundary of the decision rule, so it must have
lineage, not be a picked number).** Declared anchor: the
compact-transfer benchmark's 600 x 600 mm envelope, as declared
by the actor in the 2026-10-18 debate round; this figure was NOT
located in the repo records at staging time and is recorded here
as the debate-declared first-cut anchor, re-derivable against any
formal envelope spec (open question below). Derivation: the two
cams are axially stacked on one shaft and share the plan view, so
each cam plate must fit the envelope's footprint: plate diameter
<= 600 mm, and the pitch major-radius cap is 300 - r_roller mm.
With the first-cut roller radius r_roller = 15 mm (recorded knob,
common stock size): pitch major-radius cap 285 mm, hence the
cap-limited base circles r_base(x) = 285 - 260 = 25 mm and
r_base(y) = 285 - 90 = 195 mm. The slides, followers and guides
are assumed to fit the same envelope; a detailed layout is
beyond Stage 1's kinematic scope and is recorded as an assumption,
not a verification.

**The pre-declared G2 tension (the critic's point 2, adopted:
freeze the arithmetic into the scorecard so the reading is
anticipated data, not a surprise).** The x follower carries the
full 260 mm stroke, and a translating follower's pressure angle
goes as tan(alpha) = |h'| / (r_base + h). The -02 knot speeds
alone put |h'_x| at about 159.6 mm/rad on the carry (and about
102-112 mm/rad on the return, where h_x is small), so at the
cap-limited r_base = 25 mm the pressure angle is far over the 45
deg hard gate everywhere the x slide moves fast, and meeting even
the 45 deg gate needs a major radius in the 350-400 mm class --
beyond the 285 mm cap. The pressure-angle gate and the size cap
are in direct tension on this task, the narrow-fail branch
(grow the base circle within the cap) cannot rescue cam x because
the base circle is already at the cap, and the branch that fires
is the wide fail. This was declared before the audit; the audit's
grid maxima are the recorded values. The same arithmetic shows cam
y is comfortable (90 mm lift), which is why the verdicts are
per-cam.

**The script.** `dualcam_design.py` in this directory: pure
Python standard library (math, json, hashlib, sys, argparse), no
network, no packages, deterministic (no time, no randomness). It
runs in seconds. Sections: [A] the fail-closed task validation;
[B] the analytic synthesis of both follower laws on a 0.1 deg
grid (3600 points per cam) with the dwell-arc map; [C] the
engineering audit -- pressure angle per grid point, pitch-curve
curvature in the polar form, the required base circles for the 30
deg target and the 45 deg hard gate (bisection; the worst tan
alpha is strictly decreasing in r_base), and the frozen branch
verdicts at the cap-limited operating points; [D] the
cam-vs-six-bar family-cost table with the recorded frontier
embedded as data; [E] the witnesses. Conventions recorded in the
script docstring and frozen here: pressure angle for an in-line
translating follower; the polar curvature sign (kappa > 0 means
the curvature centre is on the shaft side) with the undercut gate
on positive rho (rho >= 1.25 x 15 mm = 18.75 mm) and negative rho
reported as manufacturing data, since the inward offset there
increases the profile radius; grid tie rules (carry side at the
theta = 120 deg seam, later segment at interior path boundaries)
with both one-sided readings in the junction table.

**Staging disclosure (honesty note).** The script was executed
once at staging time on the staging workstation (Python 3.12.13)
before this commit, for exactly the reason the actor gave:
construction proofs that are never executed are how spec text gets
ahead of the tree. The staging readings are recorded below. The
recorded machine step is the the-hub run, and because the script
is deterministic the the-hub output must reproduce the staging
readings; any divergence is a finding to record, not noise. The
brief's declared lean ("G2 UNCERTAIN, lean HELD at hard limit")
was REFUTED by the staging reading for cam x: it is a wide fail.
That lean-versus-reading delta is recorded as data, per the
standing rule that refuted predictions are recorded, never
rewritten.

**Staging smoke-test reading (2026-10-18, staging workstation,
Python 3.12.13).** Task file SHA-256 at staging:
591a562c33b7455476e20559fdd16f46bb0c1a3c4645d4a25048e4607e3a24d5.

- [A] Task validation PASS: worst reproduction error max |dq| =
  5.6e-17, max |dv| = 4.4e-16, max |da| = 6.1e-15, all far inside
  the 1e-9 fail-closed tolerance; knot speeds reproduce the -02
  record (159.61 / 106.41 / 115.64 / 102.18 / 112.00 / 108.73
  mm/rad).
- [C] cam x at r_base = 25 mm: worst pressure angle 72.66 deg at
  theta = 12 deg (carry rise); required base circle 251.61 mm for
  the 30 deg target (major radius 511.61 mm) and 129.97 mm for
  the 45 deg hard gate (major radius 389.97 mm), both far beyond
  the 285 mm cap; curvature PASSES at the cap-limited point (min
  positive rho = 25.0 mm on the ascent dwell circle, above the
  18.75 mm gate; most negative rho -4216.8 mm reported as data);
  the junction risk map puts the return/left-arc junction (phase
  10) at 68.62 deg both sides and the arc/return junction (phase
  6) at 20.73 deg. VERDICT: WIDE FAIL.
- [C] cam y at r_base = 195 mm: worst pressure angle 25.88 deg at
  theta = 332 deg (ascent); required base circle 156.10 mm for
  the 30 deg target (major radius 246.10 mm, inside the 285 mm
  cap with 38.9 mm of headroom); curvature PASSES (min positive
  rho 98.34 mm). VERDICT: HELD.
- [D] junction derivative demand, normalized: peak one-sided
  |h''| is 2.95448 units/rad^2 (cam x, at the set-down seam,
  carry side -- the deceleration into the stop) and 2.52962
  (cam y, at the phase-10 arc side), against the task's own
  prescribed peak 1.7767 (the vector-mean convention at the
  stops) and the six-bar's worst recorded acceleration ERROR
  1.403-1.494 in -02: the derivative cost indeed moves to the
  junctions, as the brief's G4 prediction said, and the cam must
  be manufactured to transmit a demand about 1.66x the smoothest
  reading of it.
- [E] witnesses: follower velocity exactly 0 at both stops, both
  cams; composed tool yaw 0 at all 3600 grid points; two
  independent in-process audit passes byte-identical; two separate
  process runs byte-identical at staging.

**Machine.** Any machine with Python 3.8 or newer (pure standard
library, no venv, no packages, no network); the script runs in
seconds. The recorded run machine is the-hub (any Python 3).

## Steps

From the repository root:

```sh
python3 jobs/dualcam-gap-transfer-05/dualcam_design.py
```

The default task path is the frozen -02 file; `--task` points at
a copy if needed. The full stdout is the record (the outcome
section below will carry it verbatim).

## Prediction scorecard (frozen before the recorded run; the staging reading in brackets)

- **G1 (task synthesis): HELD by construction -- and
  machine-verified, never asserted** (the actor's requirement,
  adopted): the script must reproduce the frozen task to 1e-9
  fail-closed and witness that the composed follower laws emit
  the task samples. The trivial hold IS the finding: the cam
  family meets the position demand identically because it is
  synthesized from the same law. [staging: HELD, worst 6.1e-15]
- **G2 (PRIMARY engineering gate), explicit branches (the actor's
  refinement, seconded by the critic), per cam at the
  cap-limited operating point:**
  - worst pressure angle <= 30 deg -> G2 HELD;
  - > 30 deg and <= 45 deg -> NARROW FAIL: grow the base circle
    within the cap first; if the base circle is already at the
    cap, the recorded finding is "the envelope binds, not the
    synthesis";
  - > 45 deg -> WIDE FAIL.
  - Undercut gate alongside: min positive pitch-curve rho >=
    1.25 x roller radius (18.75 mm at the 15 mm first cut).
  - The margin distribution is reported, not just the worst
    value (the actor's addition): the junction table is the risk
    map, and "passed at 44.8 deg" is different information from
    "passed at 31 deg". [staging: cam x WIDE FAIL, worst 72.66
    deg, required major radius 511.61 mm (30 deg target) /
    389.97 mm (45 deg gate) vs cap 285 mm, curvature passes; cam
    y HELD, worst 25.88 deg, required major radius 246.10 mm <=
    cap 285 mm, curvature passes]
- **G3 (stop velocity): zero by construction, machine-checked**
  (the clamped timing pins s' = 0 at both stops; the script
  verifies and prints it). [staging: HELD, exact 0]
- **G4 (family-cost table): emitted by the script** with the
  actor's five additions and the critic's sixth, all adopted: part
  count and manufacturing complexity (two plate cams, two roller
  followers, two guided slides, return springs vs one six-bar of
  6 links and 7 pins); junction derivative discontinuities
  compared apples-to-apples in normalized units; the six-bar's
  recorded -01/-02/-04 frontier carried as data, not a summary;
  force closure (rise = pressure-angle problem, dwell/carry =
  static spring problem, the critic's dwell-load note); and the
  structural-attribution row (the three six-bar misses vs the
  three cam-family structural features), which is the argument of
  the succession turned into evidence. [staging: emitted]
- **G5 (control):** the task file consumed read-only with its
  SHA-256 recorded; two-run determinism byte-identical;
  all-unqualified-style honest outcomes impossible here by
  construction, but any divergence between the staging reading
  and the recorded run is a recorded finding. [staging: PASS]

**Decision rule (frozen in the brief before staging, restated
with the actor's explicit branches).** A confirmed G2 wide fail
on any cam -> Option B (cam + linkage) under the same scorecard;
a narrow fail -> base-circle growth within the cap first; neither
branch returns to a fifth gap-transfer linkage variant. The
staging reading puts cam x in the wide-fail branch: if the
recorded run confirms it, Option B -- a lever ratio reducing the
follower stroke, which is the only thing that reconciles the
pressure-angle gate with the envelope, and which is exactly why
Option B exists in the family -- is the engaged successor design,
pending Jean's merge decision on this PR. No gate is loosened
anywhere: 30/45 deg and the 1.25x curvature margin are untouched
(the actor's answer to Q1, seconded by the critic).

**Stage 2 (declared conditional, and expected never to fire).**
Stage 2 -- the seed protocol (580000050/51/52, 200-eval budget,
per_sample schema_version 3) -- exists only if Stage 1 leaves a
genuine search problem. With the task timing frozen the cam
profile is fully determined analytically; the roller radius and
base circle are audit knobs handled by G2's branches, not search
variables. The prediction, frozen: Stage 2 never triggers, and
its non-triggerment is itself a family finding (analytic
synthesis replacing search). If the audit shows junction spikes,
the response is design (blending, base circle), never search (the
critic's addendum, adopted).

## Readings to report

- The full script stdout from the-hub (the verbatim record), plus
  the python version line.
- The G1-G5 verdicts against this scorecard, with the per-cam G2
  branches and the required-base-circle numbers.
- Any divergence from the staging reading (expected none; the
  script is deterministic and was verified byte-identical across
  two process runs at staging).

## Honest scope

- No finite dwell at the stops exists under the frozen -02
  demand (nonzero prescribed stop accelerations, the vector-mean
  convention); the stops are zero-velocity instants and the true
  dwells are the coordinate dwell arcs listed above. A
  dwell-prescribed task variant is queued as an open question.
- The 600 x 600 mm envelope is the debate-declared anchor, not a
  repo record; the cap arithmetic is recorded so a formal
  envelope re-derives it. The layout assumption (slides,
  followers and guides fit the same envelope) is declared, not
  verified.
- The undercut sign convention is recorded (positive polar rho
  gates; negative rho is data); a manufacturing-savvy reader is
  invited to check it against the script docstring.
- The 0.1 deg grid and the exact analytic junction readings say
  nothing about a manufactured profile surface; the tolerance ->
  path-error mapping is deliberately deferred with its trigger
  recorded below.
- No operating speed, drive law, payload capacity or motor is
  prescribed; v and a are per crank radian; capacity and speed
  remain unrated, as throughout case study B.
- This job is task-side only: the experimental motion solver and
  the engine are untouched, and no solver run is staged.

## Open questions

- **Profile tolerance -> path-error mapping** (deferred by the
  lead, with the trigger the critic named, adopted): it becomes
  non-trivial the moment a G2 pass is claimed at a fine grid,
  because a 0.1 deg grid proof says nothing about a wire-EDM
  profile's real surface. Queued with that trigger recorded, not
  forgotten.
- A dwell-prescribed task variant (finite dwells at pick and
  set-down) if the cam family qualifies anywhere in the envelope
  conversation.
- A formal declared envelope to replace the debate-declared
  600 x 600 mm anchor.
- Option B's lever-ratio design (the wide-fail branch's successor
  design): same scorecard, same script pattern, one lever ratio
  and its pressure-angle arithmetic added.

## What we will do with it

The recorded run decides the Option A/B fork per the frozen
decision rule. A confirmed cam-x wide fail engages Option B under
the same scorecard; a cam-y pass is this task family's first HELD
engineering gate and is carried into Option B's design as the
proof that the y-axis cam is sound. Either way the -01/-02/-04
six-bar frontier stays recorded for a future revisit, the
succession evidence is now a table with lineage rather than an
assertion, and recorded outcomes are data and are never
rewritten.


## Recorded outcome (2026-10-18)

Run on the-hub by Jean, one invocation with defaults from the
repository root, right after the PR #54 merge (public main
a6dd0869 carries this JOB.md byte-identical at 19,317 bytes
pre-append). Python 3.14.4; the motion venv prompt was active
but the script is pure standard library and does not use it.
The full stdout was shared and is the verbatim record; the
verdicts below read it. The machine run reproduces the staging
smoke-test reading to every printed digit -- no divergence
exists anywhere in the shared output, which is itself the G5
prediction held.

**Scorecard verdicts (frozen before the run):**

- **G1 (task synthesis) HELD, machine-verified.** [A] PASS on the
  machine: max |dq| 5.551e-17, max |dv| 4.441e-16, max |da|
  6.051e-15 (the staging reading 5.6e-17 / 4.4e-16 / 6.1e-15 is
  the same values rounded), six orders inside the 1e-9 gate; the
  knot speed cross-check reproduces the -02 record (159.61 /
  106.406 / 115.636 / 102.176 / 112 / 108.725 mm/rad). The task
  SHA-256 matches the staging witness exactly. [E] the composed
  follower laws reproduce the task samples to the [A] tolerances
  and the tool yaw is 0 at all 3600 grid points: the trivial hold
  is machine-checked, as the scorecard required.
- **G2 (PRIMARY engineering gate): cam x WIDE FAIL, cam y HELD --
  identical to the staging reading, so the frozen prediction is
  confirmed.** Cam x at the cap-limited base circle 25 mm: worst
  pressure angle 72.6645 deg at theta 12 deg; required major
  radius 511.609 mm (30-deg target) / 389.97 mm (45-deg gate) vs
  the 285 mm cap; curvature passes (min positive rho 25.0 mm on
  the ascent dwell circle, above the 18.75 mm undercut gate; most
  negative rho -4216.84 mm reported as data). Cam y at base
  195 mm: worst pressure angle 25.8817 deg at theta 332 deg;
  required major radius 246.098 mm (30-deg target) and 174.26 mm
  (45-deg gate), both inside the cap; curvature passes (min
  positive rho 98.3361 mm). The pre-declared G2 tension fired
  exactly as declared: the base circle is already at the cap, so
  the narrow-fail branch cannot rescue cam x, and the recorded
  finding is "the envelope binds, not the synthesis". The brief's
  lean ("G2 UNCERTAIN, lean HELD") stands refuted for cam x,
  recorded before the run and confirmed by it.
- **G3 (stop velocity) HELD.** Follower |h'| exactly 0 at theta 0
  and 120 deg on both cams, machine-checked ([E]); level
  orientation identity at all grid points.
- **G4 (family-cost table) HELD (emitted).** [D] printed the
  extended table with the recorded -01/-02/-04 frontier and the
  structural-attribution rows. Peak one-sided |h''| on the
  machine: cam x 812.885 mm/rad^2 (2.95448 normalized) at
  theta 120 deg, cam y 695.99 (2.52962) at theta 300 deg --
  identical to staging, so the derivative-cost-at-the-junctions
  reading (about 1.66x the smoothest reading of the demand)
  stands.
- **G5 (control) HELD.** The -02 task consumed read-only with the
  same SHA-256 recorded; two independent full audits
  byte-identical on the machine (determinism PASS). No gate
  loosened; the frozen -02 demand untouched.

**Decision rule: ENGAGED as frozen.** The confirmed cam-x wide
fail engages Option B (the cam + linkage lever) under the same
scorecard, pending Jean's decision -- never a fifth gap-transfer
linkage variant. The cam-y pass is this task family's first HELD
engineering gate and carries into Option B's design as the proof
that the y-axis cam is sound.

**Stage 2: NOT TRIGGERED, as the frozen prediction stated.** No
genuine search problem remains: with the task timing frozen the
profile is fully determined analytically, and the failure is the
engineering gate (pressure angle vs the envelope), not the
synthesis. The non-triggerment is itself the family finding
declared in the JOB: analytic synthesis replacing search.

**Reading.** Option A's failure is arithmetic, not search: the
x stroke (260 mm) at the knot speeds the frozen task prescribes
cannot meet the pressure-angle gate inside the 600 x 600 mm
envelope at any base circle the cap allows. The lever ratio of
Option B is the only thing that reconciles the gate with the
envelope, which is exactly why Option B was declared the
fallback. The succession evidence is now complete with lineage:
the six-bar position plateau (0.1484 / 0.1219 / 0.12570), the
analytic Option A wide fail, and the Option B trigger, all on
record. Recorded outcomes are data and are never rewritten.

**Machine.** the-hub, Python 3.14.4, one invocation of
jobs/dualcam-gap-transfer-05/dualcam_design.py from the
repository root; the full stdout shared by Jean is the verbatim
record.
