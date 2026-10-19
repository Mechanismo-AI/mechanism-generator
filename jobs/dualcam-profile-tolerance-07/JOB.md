# Job dualcam-profile-tolerance-07: the profile-tolerance ->
path-error mapping for the recorded -06 Option B design

Case study B, family succession, the queued Q1/Q3/Q2 round as
converged by the actor/critic debate: the exact
profile-tolerance -> path-error map for the RECORDED dualcam
Option B design (the -06 HELD record: the dual-cam cross-slide
with the general pivoted lever, worst pressure angle 29.7366
deg, envelope exactly consumed -- the cam-y plate at its
300 mm cap), with the force-closure question folded in as
data-only rows and the A-floor question redeclared as data.
This job stages nothing new mechanically: the -06 design is
regenerated through its own pick rule and the mapping is
computed ON the recorded design. The -02 task and the merged
-06 module are consumed read-only.

The debate round this job executes (frozen before staging):

- Q1 (the mapping, first in the ranking): the normal
  profile-tolerance -> task-space path error map through the
  ACTUAL lever geometry, not the sketched scalar lambda_eff
  (3.42-3.87). The exact map is
    S_x(th) = L^2 / (|Py| * A * cos q),
  with L = hypot(u - Px, Py) the pin-arm length, u the slide
  position, A the short arm, P = (Px, Py) = (8, -260) the scan
  pick, and cos q = |f . n| the roller constraint direction f
  (perpendicular to the lever arm) against the pitch-curve
  normal n = i T / |T|, T = C' - i c the fixed-frame pitch
  tangent; and
    S_y(th) = hypot(r, h') / r = 1 / cos(alpha_y),
  r = 195 + h the -05 carry-in pitch radius. A normal profile
  error delta moves the constrained roller delta / cos(pressure
  angle) along its motion direction (first-order
  parallel-curve geometry); the exact slot map turns roller
  motion into slide motion; by power balance the same S is the
  contact-normal force per unit slide force (reciprocity).
- Q3 (the A-floor redeclaration): the 60 mm floor was the
  scan-range prior, never a gate; the feasible interval on the
  recorded 1 mm ascension is [76, 77); the pick at the TOP of
  the interval MINIMIZES the exact amplification (S_x scales
  as 1/A at fixed pivot geometry); no silent redeclaration.
- Q2 (force closure, folded in as data-only rows): contact-
  normal force per unit slide force = S (reciprocity);
  per-unit-mass spring criteria at unit crank rate; the
  dwell-jump one-sided maxima at the two stop seams (the
  preload criterion); nothing gated -- the future gate shape
  is the dimensionless contact-maintenance criterion with
  declared masses and a rated speed.

## The three declarations frozen before the run (the critic's
round, adopted)

1. Error-combination convention: WORST-CASE-LINEAR. The
   packaging overlay is a hard guarantee and WC is the
   conservative honest form for a two-channel sum. Uniform
   tolerance class on both cams; per-angle channel sum
   S_x(th) + S_y(th), then max over the arc, times delta.
   Declared before the run, not discovered in the reading.
2. Outcome classification, frozen with its terminal branch: a
   tolerance-budget miss at nominal-passing geometry is a
   MANUFACTURING-READINESS finding, never a family failure --
   the -06 HELD record stands as recorded data; a miss means
   the design at that tolerance class is not buildable inside
   the envelope. The branch options are then only: a
   tighter/local tolerance class (the knee curve says which),
   or envelope renegotiation with the brief owner; NEVER a new
   variant, per the frozen rule. The same classification covers
   the cap-under-tolerance branch (section [E]): a normal
   error grows the pitch major radius by up to itself, and the
   cap re-test under tolerance is part of the budget, not a
   new gate.
3. Calibration stance: a dwell-arc radius error maps to a
   constant slide offset -- systematic, in practice
   calibratable (slide-datum adjustment at assembly). The job
   reports both rows (raw error, and residual-after-
   calibration as a separate row), but the gate budget scores
   the RAW error: claiming calibration credit before an
   adjustment procedure exists would be spec-ahead-of-tree
   again.

## The gate region (frozen)

- The scored arc is the level-carry arc, crank angle
  theta in [0, 120] deg (the -01/-02 carry record), with the
  full cycle reported alongside.
- The budget is scored against the 1.5 mm packaging overlay
  (the -01 recorded gate).
- Working number: delta = 0.10 mm profile tolerance (both
  cams, uniform class); knee curve across 0.01-0.50 mm.
- Cap re-test: the 285 mm pitch major-radius cap is evaluated
  under tolerance as part of the budget (declaration 2).

## What the script does

Pure standard library, deterministic, no network, no solver.
`profile_tolerance_map.py` imports the merged -06 module
(`dualcam_lever_design`) read-only, regenerates the recorded
pick with the -06 pick rule (the scan runs once), and:

- [A] fail-closed reproduction of the recorded -06 outcome:
  the -02 task validated through the -06 module's own
  reconstruction at 1e-9 normalized units, its SHA-256 checked
  against the recorded byte-identity witness, and the
  regenerated pick cross-checked against the recorded -06
  oracle (A, P, Delta exact at the recorded print precision;
  audit floats within 5e-3 relative). A mismatch aborts
  fail-closed: the mapping is only ever computed on the
  recorded design.
- [B] the exact error map on the 0.1 deg grid (3600 points
  per cam), with the identity cos q = cos(alpha_x) witnessed
  numerically at every moving grid point.
- [C] an independent numerical re-contact witness: at 13
  angles per cam, the pitch curve locally resampled to a
  0.01 deg polyline, perturbed by delta_w = 0.02 mm along the
  normal and along the tangent, both signs, and the contact
  RE-SOLVED by distance minimization on the perturbed
  polyline (the follower axis for cam y, the lever-arm circle
  for cam x) -- never through the analytic map. Gates: normal
  agreement within 1e-3 relative at every witness point;
  tangential residues <= 1e-4 mm (second order).
- [D] the WC-L budgets: knee curve, the working number
  against the overlay, the break-even delta*.
- [E] the cap-under-tolerance table with the frozen
  classification and its terminal branch.
- [F] the calibration stance rows (raw gates).
- [G] the data-only force-closure rows (the folded Q2).
- [H] the A-floor redeclaration (Q3, data; the A = 77 stop
  and the 1/A monotonicity are verified against the
  regenerated design, fail-closed).
- [I] the scorecard reading: the predictions below, frozen
  before the run, with the staging readings quoted as
  predictions-supporting data only.

## Run

    python3 jobs/dualcam-profile-tolerance-07/profile_tolerance_map.py

Optional (the frozen -02 task is the default):

    --task jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json

Two-run determinism (the -06 run1/run2 pattern) is the machine
control: redirect twice and diff.

## Scorecard (frozen before the run)

T1 HELD: the regenerated pick and audit match the recorded -06
oracle (A, P, Delta exact; audit floats within 5e-3 relative).
Disclosed risk: cross-platform libm last-ulp noise flipping a
scan tie aborts fail-closed; the run of record is then the
machine of record (the-hub).

T2a S_x full-cycle max in [4.4, 5.6] -- ABOVE the sketched
lambda_eff range 3.42-3.87 by the factor (L/|Py|)/cos(alpha):
margin exhaustion recorded, not a gate failure.

T2b S_x carry max in [4.3, 5.2]; S_y = 1.000 exactly on the
carry (the carry IS the cam-y dwell; asserted); S_y full-cycle
max = 1.1115 (arithmetic from the recorded 25.8817 deg).
Staging note: the first draft of this prediction carried a
hand-arithmetic slip (1.1094), caught by the staging smoke run
and corrected BEFORE the scorecard was frozen in the JOB; the
machine run must measure 1/cos(25.8817 deg).

T2c numerical re-contact witness: normal agreement within
1e-3 relative at all witness points; tangential residues
<= 1e-4 mm (second order).

T3 WC-L at the working number 0.10 mm: carry error in
[0.50, 0.78] mm <= 1.5 mm overlay -> HELD with margin (~2x);
knee break-even delta* (carry) in [0.19, 0.30] mm. A miss is a
manufacturing-readiness finding per declaration 2, never a
family failure.

T4 the cap-under-tolerance branch FIRES at any uniform WC
delta > 0.068 mm (cam-x major headroom 0.068 mm; cam-y
headroom 0.000 mm -- the carry dwell sits exactly at the cap):
a manufacturing-readiness finding; the terminal branches are a
local tolerance <= headroom on the major arcs or envelope
renegotiation with the brief owner; never a new variant. The
-06 HELD record stands.

T5 dwell-radius error = constant offset (S = 1 on the cam-y
carry dwell; S_x on the cam-x dwells reported): fully absorbed
by a slide-datum adjustment in the systematic case (residual
0); arbitrary errors get NO worst-case credit; the gate scores
raw.

T6 data-only force rows: contact-normal force per unit slide
force = S (reciprocity); per-unit-mass spring criteria at unit
crank rate (cam-y follower 0.696, roller 0.194, slide 0.813
N/kg per (rad/s)^2 class); dwell-jump one-sided maxima
reported; nothing gated (the future gate shape is noted, rated
forces need declared masses and speed).

T7 A-floor status redeclared as data: the 60 mm floor was the
scan-range prior, never a gate; the feasible interval is
[76, 77) on the recorded 1 mm ascension (A = 77 stops on the
cap, not the angle); 60 mm survives as the scan convention;
the recorded pick at the TOP of the interval MINIMIZES the
exact amplification (S_x scales as 1/A at fixed pivot
geometry).

## Machine steps after merge

1. `git pull` on the-hub.
2. `python3 jobs/dualcam-profile-tolerance-07/
   profile_tolerance_map.py > run1.txt 2>&1; echo EXIT=$?`
   then the same to run2.txt; `diff run1.txt run2.txt` must be
   empty; report the full stdout.
3. Readings to report back: exit code; the [A] reproduction
   lines; the [B] measured maxima; the [C] witness lines; the
   [D] WC-L line at the working number and delta*; the [E] cap
   table; the Python version line.

## Staging disclosure (honesty notes)

- The script was executed in full at staging (twice, byte
  identical; exit 0). The staging readings agree with the
  predictions above and are NOT the run of record: the machine
  run on the-hub after merge is. The recorded outcome section
  will quote the machine run only.
- The first staging run caught two staging-side defects
  before any push: a transcribed task-SHA constant with a
  dropped character (the computed hash matched the recorded
  value; the constant was wrong) and a hand-arithmetic slip in
  the T2b prediction (1.1094 vs the correct 1.1115 =
  1/cos(25.8817 deg)); both were corrected before the
  scorecard was frozen.
- Infrastructure disclosure: after the first staging was
  verified and before the branch push, the staging sandbox was
  lost to an execution-environment reset (the staged files
  were never pushed). The script and this JOB were then
  REBUILT from the frozen design record -- the map formulas,
  the frozen declarations, the gate region, the oracle
  constants and the prediction text above -- and re-staged.
  The rebuilt staging run reproduces the first staging's
  readings exactly in every section that is a deterministic
  function of the recorded design (sections [A], [B], [D],
  [E], [F], [G], [H] and the [I] measured line are
  byte-identical; first staging: S_x carry max 4.90651, full
  4.97529, S_y max 1.11148, WC-L(0.10) carry 0.590651 mm,
  delta* carry 0.253957 mm, headroom cam x 0.0678458 mm). The
  one section re-derived rather than recovered is the [C]
  witness's low digits: the rebuilt witness readings are
  2.864e-4 (cam x) / 5.967e-5 (cam y) relative on the normal
  direction and 1.522e-6 / 9.933e-7 mm tangential, against the
  first staging's 2.742e-4 and 2.567e-6 mm; the frozen gates
  (1e-3, 1e-4 mm) are unchanged and both readings PASS with
  margin. The prediction scorecard was re-frozen with the same
  text; nothing in it moved.
- The -02 task is consumed read-only (SHA-256 recorded in the
  run output); the -06 module is imported read-only and never
  modified; no gate loosened anywhere. Nothing in this job
  stages a new mechanism variant.

## Recorded outcome

(to be appended after the machine run on the-hub)
