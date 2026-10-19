# dwell-station-capability-01 -- Stage 1 capability design study (case study A dwell station)

Status: run recorded (2026-10-19); see the Recorded outcome section.

## What this job is

Brief A closed its failure analysis with an honest zero-selection run (PRs
#61/#62/#63: the four-bar pool scored 36 candidates, zero pose-qualified;
stillness miss 203.69x, placement miss, zero cusps). The debate then picked the
dwell-station family BEFORE any capability spend. This job is that capability
step: it synthesizes the adopted family, prices both declared instances, and
emits the audit tables. It is a docs-and-script job: no engine, no search, no
candidate scoring -- a pure, deterministic, fail-closed arithmetic design study
(`dwell_station_design.py`, pure standard library, double-run determinism
check in-process, exit 0 on reported readings, exit 2 only on structural
failure of its own witnesses/assertions).

## Debate record (both rounds executed; all positions adopted)

Actor's five answers, adopted:

1. Task shape: ONE x-axis cam with a dwell arc at the station radius plus a
   PASSIVE y-guide at the carry plane. The recorded poses are collinear (T1,
   station, T3 all at y = 50 mm; the +-130 mm x-carry mirrors case B's
   x-carry), so the cross-slide pair is NOT forced and the cheaper
   decomposition is the Stage-1 default. The pair returns only under a
   declared trigger: line architecture demanding y-motion (return path or
   station clearance) -- the same scope line that keeps Geneva out. The +-
   130 mm mirroring is kept so the family-cost table is apples-to-apples
   against the four-bar frontier's recorded demand geometry. Honest
   consequence declared: the total x-stroke is still 260 mm -- this is NOT a
   smaller cam problem than case B; what is smaller is the timing problem.
2. Envelope: the 285 mm cap is a DEBATE-DECLARED, LABELED PLACEHOLDER -- no
   fake derivation (invented precision is the house anti-pattern). The -06
   lesson is institutionalized instead: the script MUST emit the
   envelope-utilization and headroom table at nominal (cap headroom,
   pressure-angle margin, curvature margin at the recorded design point), so
   a zero-headroom design is caught at design time, not in an endgame.
3. Scorecard specifics: the dwell witness is executed, not asserted
   (follower displacement exactly 0 across the arc, verified numerically on
   the emitted grid, boundaries included); the 0.3 mm WC-L row declares the
   budget split UP FRONT (x from profile class via sensitivity S, y from the
   passive-guide class, combined by a frozen rule: worst-case primary, RSS
   reported); synthesized timing is a declared design parameter recorded with
   its derivation; predictions frozen before the run of record (see below).
4. Spec stance: no OMTS vocabulary this round; claim-only-what-exists; the
   dwell-duration spec concept stays a recorded prediction for the
   capability-to-spec step.
5. Tolerance precedent: the T4 manufacturing-readiness classification is
   pre-declared identically (budget miss at nominal-passing geometry =
   manufacturing-readiness finding with terminal branches: zoning preferred,
   envelope renegotiation as fallback, never a fifth variant), and the
   datum-bias lever is pre-declared as a NAMED design lever (inward-biasing
   the dwell arc converts cap headroom into a calibratable datum offset), so
   its use would be honest rather than a post-hoc rescue.

Critic's three deltas, adopted:

1. Duration robustness is a tolerance channel the -07 machinery does not
   cover (it prices position, not duration): pre-declare design arc = 50 deg
   + a declared duration allowance, and a tolerance-to-duration row mapping
   profile class to guaranteed dwell width.
2. The dwell/rise crank-angle allocation is a design variable in tension --
   declare the rule, don't default it: minimum dwell meeting 50 deg + the
   duration allowance, remainder to rise/fall, split proportional to stroke,
   so margins are traceable to declared choices (the -06 lesson applied
   forward).
3. Carry the junction blending requirement into the synthesis spec: C1 in
   slide space at every junction (dwell-to-rise junctions are where this
   design's derivative cost lands), junction derivative peaks reported.

Staging disclosure (recorded here BEFORE the run of record, -05/-07
precedent): desk arithmetic at staging found that the actor's prediction (a)
as stated holds ONLY for the lever instance. The DIRECT follower requires
roughly 464 mm major radius at the 30 deg target (wide fail vs the 285 mm
placeholder; still wide fail at 45 deg), while the LEVER instance fits
(roughly 120-136 mm) but pays lambda in profile class (roughly 0.052-0.058
mm, tighter than case B's 0.068 mm). The frozen predictions below are
therefore restated per instance, and the trade itself is the capability
finding. The staging smoke test (same code as the run of record) confirmed
these numbers; its reading is pasted in a section below.

## Frozen declarations (echoed by the script at run time)

- Task geometry: T1/station/T3 x = -130/0/+130 mm at carry plane y = 50 mm
  (poses collinear). Demand: hold inside 0.3 mm at the station for >= 50 deg
  of crank cycle while the crank keeps turning.
- Family: one x-axis cam + passive y-guide; pair trigger as declared above.
- Motion program: half-cosine per moving phase; C1 in slide space at every
  junction (junction slide-velocity zero by construction; acceleration peaks
  reported as data).
- Allocation rule (declared, not defaulted): design dwell arc = 50 deg +
  duration allowance, where allowance = max(0, 50 deg - guaranteed dwell
  width of the DIRECT instance at the working class), derived by fixed
  point; the remainder is split proportional to stroke 130:130:260, so
  approach = depart = rem/4 and return = rem/2.
- Grid: 7200 unique samples at 0.05 deg (mirrors the digest grid); wrap at
  360.00 deg; dwell arc asserted at run time as 1000 intervals = 1001
  samples = 50.00 deg (at the converged allowance).
- Cam data: roller 15 mm; pitch-curve curvature floor 18.75 mm (1.25x
  roller); pressure-angle target 30 deg, hard ceiling 45 deg.
- Cap: 285 mm major radius = LABELED PLACEHOLDER (debate-declared; never
  derived).
- Classes: profile 0.10 mm working; passive guide 0.10 mm working. Budget
  split frozen up front: WC x-budget = 0.3 - 0.1 = 0.20 mm; RSS x-budget =
  sqrt(0.3^2 - 0.1^2) = 0.2828 mm (reported alongside WC as data).
- Sensitivity: slide error = S * profile error; S = 1 (direct instance),
  S = lambda (lever instance). The lever is an IDEAL-RATIO model at the
  recorded -06 lambda band 3.42105..3.87307 -- a declared simplification;
  the lever's own geometry audit is a follow-on job if that instance is
  picked. Guide class is the y share and is not multiplied.
- Duration rule: guaranteed dwell width = the contiguous run containing the
  dwell center where |slide| <= (x-budget - S*delta); collapses to 0
  discontinuously once S*delta exceeds the x-budget (the dwell center leaves
  the region). Recorded as a finding, not a gate.
- Recorded four-bar reference numbers are quoted verbatim from the digest
  run of record (PR #63 outcome; run root
  runs/dwell-station-failure-01/.../2026-10-18_22-10-36_210120) and are
  used only in the family-cost table.

## Frozen scorecard

- K1 validity/witnesses: dwell witness EXECUTED (max |slide| over the
  dwell arc, boundaries included, exactly 0.000000 mm); stroke witness
  (260.000000 mm); cycle-wrap witness; in-process double-run determinism
  check IDENTICAL; grid/phase arithmetic asserted fail-closed. Predicted:
  HELD by construction.
- K2 allocation/allowance: allocation table emitted with the declared
  rule; duration allowance derived by fixed point. Predicted: allowance
  0.00 deg (guaranteed width at the working class exceeds the 50 deg
  demand on the direct instance), approach = depart = 77.50 deg, return
  155.00 deg.
- K3 direct pressure gate: predicted WIDE-FAIL at the placeholder --
  required major about 464 mm at 30 deg (utilization about 163%, cap
  headroom about -179 mm) and about 359 mm at 45 deg (still wide). An
  envelope finding for the direct instance, disclosed at staging.
- K4 lever pressure gate: predicted HELD at 30 deg with real margin --
  required major 120-136 mm across the lambda band (42-48% utilization;
  +149 to +165 mm cap headroom); also passes at the 45 deg hard ceiling.
  Structural reason: synthesized timing freedom (gentler timing -> lower
  peak dx/dtheta) AND the lever divides the cam-side rate by lambda.
- K5 curvature: predicted HELD with large margin -- min |rho| across
  instances 42-163 mm vs the 18.75 mm floor.
- K6 tolerance and duration: direct knee 0.2000 mm WC / 0.2828 mm RSS ->
  the 0.10 mm working class PASSES with 2.0x WC margin (the
  concentric-dwell-arc easy-geometry case); lever knees 0.0516-0.0585 mm
  WC / 0.0730-0.0827 mm RSS -> the 0.10 mm working class FAILS both
  conventions; the lever's required class (WC guarantee) is 0.052-0.058 mm,
  tighter than case B's 0.068 mm. Duration: guaranteed width at the
  working class 52.70 deg (direct) vs 0.00 deg (lever, working class
  outside the knee); duration knee == position knee for every instance
  (collapse finding); nominal zero-error width 53.80 deg; allowance 0.00
  deg.
- K7 headroom/utilization table: EMITTED per instance (major, utilization,
  cap headroom, max pressure angle with margin to the hard ceiling, min
  |rho| with margin) at the 30 deg design point. Required audit output.
- K8 control/family-cost: pair trigger echoed; no OMTS vocabulary
  anywhere; T4 classification pre-declared; datum-bias lever pre-declared;
  family-cost table vs the recorded four-bar frontier: stillness 61.107 mm
  vs 0.000 mm construction-exact; quiet-region wander 27.853 mm (unplaced)
  vs 0.000 mm during the arc; min window speeds 57-232 mm/rad vs 0.000
  mm/rad during the arc; junction accelerations 350.6 / 175.3 mm/rad^2
  (C1 blending, declared) with NO recorded frontier counterpart -- data,
  not scored.

## Predictions frozen before the run of record (restated per instance)

- (a) Pressure angle HELD at the 30 deg target with real margin -- LEVER
  instance (see K4). DIRECT instance wide-fails the placeholder cap
  (K3, envelope finding). Staging disclosure recorded above.
- (b) Profile class loose -- DIRECT instance only (0.10 mm working class
  inside the 0.200 mm knee, 2.0x margin). The LEVER instance requires
  0.052-0.058 mm (tolerance finding, K6).
- (c) Stage 2 never fires -- arithmetic again: the capability answer is
  the K3/K4/K6 trade itself; no search, no refinement, no second stage.

## Staging smoke-test reading (staging machine, 2026-10-19; the machine run
after merge is the run of record)

    dwell_station_design: case study A capability study (dwell-station-capability-01)
    family: one x-axis cam + passive y-guide at the carry plane (debate-adopted)
    budget split: WC x-budget = 0.300 - 0.100 = 0.200 mm; RSS x-budget = 0.2828 mm
    duration allowance: iter 1: dwell arc 50.00 deg -> guaranteed width at working class 52.70 deg -> allowance 0.00 deg
    converged: design dwell arc = 50.00 deg; asserted: 1000 intervals = 1001 samples = 50.00 deg
    allocation: approach 77.50 / dwell 50.00 / depart 77.50 / return 155.00 deg; half-cosine, C1 at every junction
    junction slide acceleration peaks: 350.63 mm/rad^2 at dwell junctions, 175.32 at return junctions
    K1 witnesses: dwell max |slide| = 0.000000 mm (exactly zero); stroke 260.000000 mm; wrap within analytic end value
    -- instance: direct (S=1) --
       required major radius: 464.44 mm at 30 deg (WIDE-FAIL vs 285.0 placeholder, utilization 163.0%); 359.37 mm at 45 deg (WIDE-FAIL)
       pressure angle at the 30 deg design: max 30.00 deg (margin 15.00 deg to the 45 deg hard ceiling)
       pitch-curve min |rho|: 163.27 mm (floor 18.75; margin 144.52 mm)
       cap headroom: -179.44 mm
       tolerance knee (WC): 0.2000 mm; (RSS): 0.2828 mm -> working class 0.100 mm: PASS (WC), PASS (RSS)
       guaranteed dwell width: 52.70 deg at the working class (nominal 53.80 deg)
    -- instance: lever (lambda=3.42105, band lo) --
       required major radius: 135.76 mm at 30 deg (PASS, utilization 47.6%); 105.05 mm at 45 deg (PASS)
       pressure angle at the 30 deg design: max 30.00 deg (margin 15.00 deg)
       pitch-curve min |rho|: 47.72 mm (margin 28.97 mm); cap headroom: +149.24 mm
       tolerance knee (WC): 0.0585 mm; (RSS): 0.0827 mm -> working class 0.100 mm: FAIL (WC), FAIL (RSS)
       guaranteed dwell width: 0.00 deg at the working class (nominal 53.80 deg)
    -- instance: lever (lambda=3.87307, band hi) --
       required major radius: 119.92 mm at 30 deg (PASS, utilization 42.1%); 92.79 mm at 45 deg (PASS)
       pitch-curve min |rho|: 42.15 mm (margin 23.40 mm); cap headroom: +165.08 mm
       tolerance knee (WC): 0.0516 mm; (RSS): 0.0730 mm -> working class 0.100 mm: FAIL (WC), FAIL (RSS)
       guaranteed dwell width: 0.00 deg at the working class
    duration finding: width collapses to 0 once S*delta > 0.200 mm; duration knee == position knee for every instance
    headroom table: emitted (see K7); family-cost table: emitted (see K8)
    double-run determinism check: IDENTICAL; exit 0

## Machine step (after merge; the run of record)

Run from the repo root, one command at a time:

    python3 jobs/dwell-station-capability-01/dwell_station_design.py > design_run1.txt 2>&1
    python3 jobs/dwell-station-capability-01/dwell_station_design.py > design_run2.txt 2>&1
    diff design_run1.txt design_run2.txt && echo DIFF-EMPTY
    cat design_run1.txt

Expected: DIFF-EMPTY; exit 0; last line "double-run determinism check:
IDENTICAL". Paste design_run1.txt back for the K1-K8 scorecard reading.

## Claims and not-claims

- This job claims only what its own script computes on the frozen
  declarations above. It is not an engine run: no candidates, no selection,
  no scoring of mechanisms. No OMTS vocabulary.
- The four-bar reference numbers are quoted verbatim from the digest run of
  record (PR #63 outcome); they are context, not a re-scoring.
- The cap is a labeled placeholder: utilization/headroom readings against it
  are readings, not verdicts about a real envelope.
- The lever instance is an ideal-ratio sensitivity model, not a lever
  geometry design; if the lever is picked, its own geometry audit is a
  follow-on job.
- Wide-fail gate readings are data; no gate was loosened; the predictions
  were frozen before the run of record (the staging disclosure above is
  part of the frozen record).
- Honest instrument note (the PR #62 lesson, applied to ourselves): the
  staging smoke test runs the SAME arithmetic as the run of record, so it
  can catch code defects and nondeterminism but CANNOT catch a wrong frozen
  declaration -- it is self-consistent by construction. The declarations
  were desk-checked line-by-line against the debate record and the digest
  conventions instead (units: mm and degrees at interfaces, derivatives per
  radian; no engine data enters this job, so the base_angle
  radians-vs-degrees class of bug has no surface here).

## Recorded outcome (2026-10-19)

**Merged and run (the run of record):** PR #64 merged by Jean in the
browser (public main 193a112a, the merge of branch
dwell-station-capability-01 over c960b433). The design script then ran
twice on the-hub from the repo root after git pull: external diff EMPTY
(DIFF-EMPTY), exit 0, last line "double-run determinism check:
IDENTICAL". The pasted report is identical to the staging smoke-test
reading TO EVERY PRINTED DIGIT -- zero divergence; the deterministic
prediction held exactly. (Python version not captured this run; the
script is pure standard library and version-independent by design. The
self-consistency limitation stands as disclosed above: the smoke test
ran the same arithmetic and could not have caught a wrong declaration,
only code defects and nondeterminism.)

**Scorecard verdicts (frozen above; all read on the machine run):**

- **K1 HELD**, as predicted by construction: dwell witness max |slide| =
  0.000000 mm over the 1001-sample arc (boundaries included); stroke
  witness 260.000000 mm; cycle-wrap witness d(359.95 deg) = 0.000067 mm
  within the analytic end value; grid arithmetic asserted (1000
  intervals = 1001 samples = 50.00 deg); determinism IDENTICAL both
  in-process and across the two external runs.
- **K2 CONFIRMED:** the fixed point converged in one iteration; the
  declared duration allowance is 0.00 deg exactly as predicted;
  allocation 77.50 / 50.00 / 77.50 / 155.00 deg as declared; junction
  slide acceleration peaks 350.63 / 175.32 mm/rad^2 reported as data.
- **K3 CONFIRMED at the predicted WIDE-FAIL:** required major 464.44 mm
  at the 30 deg target (163.0% of the 285 mm labeled placeholder; cap
  headroom -179.44 mm) and 359.37 mm at the 45 deg hard ceiling (still
  wide). The envelope finding for the direct instance stands.
- **K4 CONFIRMED at the predicted HELD:** required major 135.76 mm
  (lambda 3.42105; 47.6% utilization) and 119.92 mm (lambda 3.87307;
  42.1%) at 30 deg, +149.24 / +165.08 mm cap headroom; also passes at
  45 deg (105.05 / 92.79 mm). Max pressure angle exactly 30.00 deg at
  the design point in every instance (15.00 deg margin to the hard
  ceiling).
- **K5 CONFIRMED HELD:** min |rho| 163.27 / 47.72 / 42.15 mm vs the
  18.75 mm floor (margins +144.52 / +28.97 / +23.40 mm), all at the
  dwell-entry junction sample 1549.
- **K6 CONFIRMED:** direct knees 0.2000 mm WC / 0.2828 mm RSS, so the
  0.10 mm working class PASSES at 2.0x WC margin; lever knees 0.0585 /
  0.0516 mm WC (0.0827 / 0.0730 RSS), so the 0.10 mm working class
  FAILS both conventions; the lever's required class (WC guarantee) is
  0.052-0.058 mm -- tighter than case B's 0.068 mm. Duration: guaranteed
  width 52.70 deg (direct) / 0.00 deg (lever, the working class outside
  the knee) at the working class; nominal 53.80 deg; duration knee ==
  position knee with the collapse behavior exactly as recorded; derived
  allowance 0.00 deg. No new gate, per the frozen finding.
- **K7 EMITTED:** the headroom/utilization table is present and
  identical to the staging reading. **K8 EMITTED:** family-cost table
  (stillness 61.107 mm vs 0.000 mm construction-exact; quiet-region
  wander 27.853 mm vs 0.000 mm; window speeds 57.0-231.8 mm/rad vs
  0.000 mm/rad during the arc; junction accelerations 350.6 / 175.3
  mm/rad^2 declared, no recorded frontier counterpart) and the control
  rows (pair trigger, no OMTS vocabulary -- verified in the output,
  T4 classification, datum-bias lever).

**The capability reading (the round's answer, read on the run of
record):** the adopted family is feasible in two flavors with a declared
trade. The DIRECT instance is tolerance-easy (the 0.10 mm working class
sits inside a 0.200 mm knee at 2.0x margin -- the concentric-dwell-arc
easy-geometry case) but envelope-wide (464.44 mm major needed; the
labeled placeholder fails at both 30 and 45 deg). The LEVER instance is
envelope-easy with real pressure margin (120-136 mm major, 42-48%
utilization) but pays lambda in profile class (0.052-0.058 mm needed vs
the 0.10 mm working class, and tighter than case B's 0.068 mm). Per the
pre-declared T4 classification, both readings are manufacturing-readiness
findings with the pre-declared terminal branches; the labeled placeholder
gives the renegotiation branch cleaner standing than case B's cap had,
and zoning still ranks first for the lever's tight class (the tight class
lands on the concentric dwell arc, the easiest geometry). The datum-bias
lever and the cross-slide pair trigger stand as pre-declared; the
dwell-duration spec concept stays a recorded prediction for the
capability-to-spec step.

**Status:** this JOB is complete -- run recorded, scorecard read,
nothing pending. Recorded outcomes are data and are never rewritten.
Next per the case-study loop: the capability-to-spec/decision step (a
debate round), carrying the K3/K4/K6 trade, the T4 terminal branches,
the datum-bias lever, the pair trigger, and the dwell-duration
prediction.
