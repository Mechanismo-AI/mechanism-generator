# Job sixbar-gap-transfer-04: case study B -- the free-phase variant of the gap-transfer motion task

**Purpose.** The -03 record closed with R4: the binding prescription of
this task family is the phase-locked 30-degree grid itself, not the
stop timing (the best dwell cut the max sample acceleration by only
28.4% while between-sample peaks grew 1.47x), and that finding
unlocked the free-phase variant per the group ranking. This job is
that variant: the first standing candidate that aims at the binding
prescription directly. Both recorded solver runs also agree on what
to aim at: the spatial acceleration error is the binding aggregate
(46.0-54.8x its 0.05 gate in -01, 27.8-29.9x in -02), the worst
position samples sit at the two process stops (which cost 1.4-2.1x
the non-stop samples), and the prescribed stop acceleration is
488.82 mm/rad^2 = 1.7767 normalized. This job changes ONE thing: the
sample placement along the path is freed -- where the tool sits at
each of the nine non-pose crank phases -- and chosen by a committed
design script to minimize the scaled derivative demand the solver is
gated on. Task-only: this job changes no engine, package, or spec
code and runs nothing at staging time beyond the design script
itself.

**The declared split (frozen before the run, per the group's
requirement (a)).** The comparison to the recorded frontier stays
defined because everything that made -02 the diagnostic it was is
held fixed:

- **Fixed:** the 12x30-degree theta grid and the five-field input
  contract; `branches: [-1, +1]`; the -02 racetrack path unchanged
  (carry 260 mm at y = +50, descent and ascent along the belt-end
  planes, 15 mm radius corner arcs, the return line 40 mm below the
  belt line); the three carry poses T1/T2/T3 at phases 0/2/4 with
  their tolerances -- (-130, 50), (0, 50), (+130, 50) mm, exactly
  -02's rows; zero speed at the two process stops (phases 0 and 4,
  full stops); level orientation with zero angular derivatives at
  every sample; the timing structure (two clamped cubic runs with
  zero end slopes, the carry phases 0-4 and the bottom loop phases
  4-12 closing at phase 0) and its conventions (the vector-mean
  acceleration at the stops; the one-sided mean at any sample
  sitting exactly on a line/arc junction).
- **Moving:** the arc-length placements of the nine non-pose
  samples (phases 1, 3, 5-11), anywhere strictly between their pose
  neighbours on the path, monotone along the loop; with them the
  prescribed v and a at every non-stop sample and the one-sided
  accelerations that form the stop prescriptions.
- **Movable but NOT exercised, declared:** stop durations (the
  stops stay touch-and-go; a dwell would need a duplicated stop
  sample, which doubles the T1->T2 window mean, and -03 already
  refuted dwell relief at fixed phases) and any change to the path
  geometry itself.

**Task.** `gap_transfer_freephase.motion.json` in this directory,
in the solver's input contract (exactly five fields, 12 fixed
phases, two known branches, 12x3 q/v/a). Physical frame unchanged
from -01/-02: millimetres, origin at gap centre on the belt line, y
up. The normalization is the validator's own rule (twelve-sample
centroid at the origin, unit bounding-box diagonal, each to 1e-8);
the freed placements move the sample centroid to (+0.13, +5.98) mm,
and the bounding-box diagonal is unchanged at 275.1363 mm (260 mm x
90 mm; the carry poses fix the width, the return-line samples fix
the depth), so one normalized unit is the same physical scale as in
-02 and the recorded frontier comparisons stay in the same units.
Pose declarations are in millimetres in this file; normalized
coordinates are not directly comparable to -02's because the
centroid moved.

**Method (the design script, `free_phase_design.py`, is the
committed audit trail).** Pure standard-library Python (argparse,
json, math, os only; no numpy, no packages, any Python 3). The path
model and spline machinery are transcribed from the -03 script,
which carries the -02 audit trail. Fail-closed stages:

1. **Rebuild and validate.** The -02 baseline is rebuilt from the
   audit trail and validated against the merged -02 task JSON:
   sample positions to 1e-9 mm, all 36 velocity and all 36
   acceleration components to 1e-9 normalized. Staging residuals:
   positions 2.84e-14 mm, velocities 4.44e-16, accelerations
   6.16e-15 -- six orders inside the gates, identical to the -03
   script's recorded validation of the same construction.
2. **Design search.** A deterministic multi-start coordinate descent
   (fixed start list, fixed scan order, fixed 65-point grids, no
   randomness) over the nine freed placements, minimizing the max
   over the twelve samples of the scaled derivative demand
   max(|v|/0.02, |a|/0.05) in the task's own normalization -- the
   solver's strict gates. The normalization is recomputed per
   candidate (freed placements move the centroid and would move the
   bounding box if the return line were abandoned; the objective
   pays for that honestly). Four declared starts (the -02 baseline
   placements, and three single-cubic-timing variants); moves are
   single-coordinate plus moves along the loop's mirror-symmetry
   pairs (carry 1/3, descent/ascent 5/11, post-corner 6/10, return
   7/9) -- the -02 placements sit on a minimax ridge that
   single-coordinate moves provably cannot slide along (every
   single move from them is worse; the staging probe of the ridge is
   what the pair moves are for). Two honesty caps, enforced as a
   penalty during descent and hard gates at the end: the
   between-sample fine-grid acceleration peak and peak speed stay
   within 1.10x the rebuilt -02 baseline values, and the timing law
   stays monotone along the loop. The winning placements are
   rounded to 0.1 mm, and free placements keep at least 0.5 mm
   clear of the line/arc junctions, where the prescription
   convention is discontinuous -- so the committed artifact does
   not depend on last-ulp search noise.
3. **Emit and cross-check.** The committed task JSON is emitted from
   the rounded design; the validator's own arithmetic is re-checked
   on the emitted rows (centroid zero and unit diagonal, each to
   1e-12); the composed trajectory is re-checked by independent
   central finite differences (h = 1e-3 rad): velocities agree to
   0.147 mm/rad and accelerations to 0.203 mm/rad^2 over all twelve
   samples (stops and corner-adjacent samples carry one-sided means
   by construction, as documented in the -02 audit trail).

**Staging-side verification (the frozen design).** The script was
run twice at staging time: both runs emit byte-identical task and
report files (the printed report differs only in the output-path
echo lines). Validation residuals as above. The search record, all
four starts on the table:

| start | start value | end value | outcome |
| --- | --- | --- | --- |
| -02 baseline (nudged 0.5 mm off the two junctions) | 35.48 | 27.07 | feasible, rounded to 27.07 |
| cubic carry | 33.84 | 27.07 | feasible, same endpoint 27.07 |
| cubic carry and loop | 506.3 (cap-violating) | 31.79 | infeasible after rounding, recorded |
| cubic loop | 502.5 (cap-violating) | 31.79 | infeasible after rounding, recorded |

Two starts converge to the same endpoint from opposite sides; the
two single-cubic-loop starts end in a worse basin and are recorded
as failures, not hidden. 23,298 objective evaluations, 5,017 peak
evaluations, 225 accepted moves in total. The committed placements
(mm along the path, phases 0-11):

0.0, 52.8, 130.0, 208.8, 260.0, 299.1, 359.1, 416.1, 473.6,
531.1, 588.0, 648.0

| Phase | theta (deg) | Tool point (mm) | Arc pos (mm) | Speed (mm/rad) | Accel (mm/rad^2) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | (-130.00, 50.00) | 0.00 | 0 (stop) | 360.91 | pick (T1); full stop [FIXED pose] |
| 1 | 30 | (-77.20, 50.00) | 52.80 | 148.97 | 17.51 | carry [freed] |
| 2 | 60 | (0.00, 50.00) | 130.00 | 148.97 | 17.51 | T2, mid-gap [FIXED pose] |
| 3 | 90 | (78.80, 50.00) | 208.80 | 148.97 | 17.51 | carry [freed] |
| 4 | 120 | (130.00, 50.00) | 260.00 | 0 (stop) | 346.76 | set-down (T3); full stop [FIXED pose] |
| 5 | 150 | (130.00, 10.90) | 299.10 | 113.95 | 14.77 | descent [freed] |
| 6 | 180 | (114.46, -40.00) | 359.10 | 112.01 | 22.16 | past the right corner join [freed] |
| 7 | 210 | (57.46, -40.00) | 416.10 | 108.36 | 8.22 | return [freed] |
| 8 | 240 | (-0.04, -40.00) | 473.60 | 110.57 | 0.21 | return [freed] |
| 9 | 270 | (-57.54, -40.00) | 531.10 | 108.25 | 9.07 | return [freed] |
| 10 | 300 | (-114.44, -40.00) | 588.00 | 111.88 | 22.92 | before the left corner join [freed] |
| 11 | 330 | (-130.00, 10.88) | 648.00 | 114.01 | 14.77 | ascent [freed] |

The structure the search found is a trapezoidal carry: the speed
ramps to a flat 148.97 mm/rad across the entire mid-carry (samples
1/2/3 identical), easing both stop prescriptions (488.82 -> 360.91
and 346.76 mm/rad^2). The bottom loop keeps -02's shape with the
descent/ascent knots eased up to y = 10.9 mm and the two former
junction samples moved 0.54-0.56 mm off the corner joins onto the
line side.

**The frozen design against the -02 prescription** (all normalized
by the same 275.1363 mm diagonal):

| quantity | -02 | free-phase design | change |
| --- | --- | --- | --- |
| max scaled sample demand max(|v|/0.02, |a|/0.05) | 35.53x | 27.07x | -23.8% |
| max sample acceleration (the binding aggregate's demand) | 1.7767 (488.82 mm) | 1.3118 (360.91 mm) | -26.2% |
| max sample speed | 0.5801 | 0.5414 | -6.7% |
| worst prescribed sample | phases 0/4 (stops, 35.53x, tied) | phases 1/2/3 (speed, 27.07x, tied) | stops no longer worst |
| second-worst | phases 1/3 (speed, 29.01x) | phase 0 (stop, 26.24x) | near-tie at the top |
| between-sample fine-grid peak |a| (0.02 deg) | 2.9520 | 3.2114 | +8.8% (cap 3.2472) |
| between-sample fine-grid peak speed | 0.6188 | 0.5498 | -11.2% (cap 0.6807) |
| speed swing vs cycle mean | 1.56 | 1.38 | gentler |

**Prediction scorecard (frozen before the run).** The scorecard is
scored against Jean's machine run -- the design script once (a
reproduction), then the solver once per seed. The design facts above
are the committed artifact; the predictions below are about what
the machine and the solver will do.

- **F1 (reproduction):** the script passes both -02 validation gates
  on the machine (positions to 1e-9 mm, baseline v and a to 1e-9
  normalized), reports the same committed placements and design
  table as above, and the regenerated task agrees with the committed
  JSON to 1e-9 on every q/v/a entry (byte-identity is hoped for --
  the two staging runs were byte-identical -- but the gate is 1e-9,
  because libm last-ulp differences across machines are not
  promised). A gate failure aborts loudly.
- **F2 (design fact, scored by F1):** the committed design's max
  scaled sample demand is 27.07x the gates (76.2% of -02's 35.53x),
  and its max sample acceleration is 1.3118 (-26.2% vs -02's
  1.7767, the binding aggregate's demand). This is the demand-side
  lever this job exists to pull; whether the lever reaches the
  solver is F4's question, not this item's.
- **F3 (demand-side stop survival, the group's requirement (b),
  answered up front):** free placement DISSOLVES the stop dominance
  of the prescription -- the worst prescribed samples move off the
  stops onto the flat mid-carry speed plateau (phases 1/2/3 at
  27.07x) with the stops in a near-tie behind them (26.24x, 25.21x).
  The -01/-02 constant (stops worst by a wide margin) does NOT
  survive at the prescription level. Machine reproduction of the
  committed design confirms this item by construction; the
  solver-side question is F6.
- **F4 (primary, the decision item):** the best of the three seeds'
  selected candidates reaches a worst-sample position error at or
  below 0.1000 normalized (27.5 mm) -- a family-level improvement
  beyond -02's seed scatter (whose per-seed moves vs -01 were
  -17.9% / +1.4% / -39.5% with no family-level move). Design-time
  prediction: UNCERTAIN, lean REFUTED -- the demand-side cut is
  necessary, not sufficient (-03's scope note), the -02 halving
  attempt missed from a 28%-class demand cut at the samples
  (-01->-02 was a different lever but the lesson stands: the
  family's response was seed-scattered), and the critic's own
  honesty note weighs his priors against the recorded frontier. If
  F4 misses, the agreed succession rule engages: family succession
  (dwell/cam per the queued briefs), not a fourth task variant.
- **F5 (strong form):** the best seed's worst-sample position error
  at or below 0.0742 (20.4 mm), the -02 D1 halving bar. Design-time
  prediction: REFUTED (the same reasoning as F4, stated at the
  stronger bar).
- **F6 (solver-side stop survival, the group's requirement (b) at
  the solver level):** the single worst position sample remains one
  of the two process stops (phase 0 or 4) in at least two of the
  three seeds. Design-time prediction: HELD with a weakened margin
  -- the stops keep the tightest structure (zero speed, 90-degree
  process corners), but their prescription fell 26% while the
  mid-carry speed prescription rose 40% (106.41 -> 148.97 mm/rad at
  T2), so the -01/-02 stops-vs-non-stop gap (1.4-2.1x) should
  narrow. If the worst samples migrate to the mid-carry, that is
  the stop-relief reading landing, and is equally data.
- **F7 (binding aggregate):** the spatial acceleration error remains
  the most-violated scaled demand in all three seeds. Design-time
  prediction: HELD, weaker than in -02 -- the a-prescription fell
  26% while the v-prescription fell only 7%, so if the family's
  errors track the prescriptions, the gap narrows; a migration of
  the binding aggregate to the velocity error would be a first in
  this case study and is itself a finding, not a failure of the
  scorecard.
- **F8 (control):** the same three seeds 580000050/51/52, one
  solver attempt each, the standard 200-evaluation budget, the same
  initialization declarations as -01/-02; per-seed reporting read
  natively from the result schema's per_sample block (schema_version
  3) -- the first case-study run that needs no external
  recomputation pipeline. No gate is loosened; an all-`qualified:
  false` outcome is a valid recorded result; recorded outcomes are
  data and are never rewritten; the -01/-02/-03 records stay
  untouched.

**Honest scope.**

- The design search is a heuristic descent from four declared
  starts, not a proven optimum. Two starts reached the same
  endpoint (27.07x) from opposite sides; two ended in a worse basin
  (31.79x) and are recorded as infeasible-after-rounding failures.
  The plateau reading is supported by the convergence, not proved.
- The between-sample fine-grid acceleration peak is 3.2114
  normalized, +8.8% vs -02's 2.9520 and inside the declared 1.10x
  cap: part of the stop relief was bought with faster corner-arc
  traversal BETWEEN samples. The solver is gated at samples only --
  this is disclosed, not scored. The -03 junction floor (1.2678
  normalized at the junction window's mean speed) remains a
  mean-value argument, not an attained bound.
- Junction dodging is real and disclosed: -02's phases 6/10 sat
  exactly on the corner joins (one-sided-mean prescription, 351.57
  mm/rad^2); the free design keeps every sample at least 0.5 mm off
  the joins on the line side (22.16 and 22.92 mm/rad^2 there), and
  the joins are traversed between samples at ~112 mm/rad. The
  between-sample peak is where that demand now lives.
- The descent/ascent samples no longer witness the (130, 5) /
  (-130, 5) mm belt-approach poses (they sit at y = 10.90 / 10.88
  mm). The packaging requirements fixed for this variant are the
  three carry poses and their tolerances, per the declared split;
  nothing else is claimed to be witnessed.
- Stop durations are not exercised (declared above); the stops stay
  touch-and-go with the -02 vector-mean convention.
- The sample centroid moved to (+0.13, +5.98) mm, so the normalized
  coordinate frame is not -02's; the bounding-box diagonal is
  unchanged (275.1363 mm), so normalized magnitudes compare
  directly.
- A demand-side reduction is necessary, not sufficient: this job
  computes and prescribes; it says nothing about what the linkage
  family reaches. The solver run decides that, per the scorecard.
- Twelve samples encode straightness, levelness and derivative
  demands at the samples only; continuous-path behaviour between
  samples is a densification follow-up, as in -01/-02.
- No operating speed, drive law, payload capacity or motor is
  prescribed: v and a are per crank radian.

**Tolerance overlay.** Unchanged: the solver's strict qualification
gate is 0.01 normalized position error; the packaging tolerance is
1.5 mm = 0.005452 normalized. For scale: -01's best was 0.1484
worst pose, -02's best was 0.1219 (33.6 mm), and the four-bar
frontier rescaled to these units is 0.0330.

**Machine.** the-hub (the -01/-02/-03 machine), CPU-only, with the
experimental motion environment (experimental/motion/README.md) for
the solver runs; the design script needs any Python 3 and no
environment (pure standard library). Cost: the design script runs
in about a minute; the solver is minutes per seed as in -01/-02.

## Steps

From the repository root, any Python 3 (no venv needed):

```sh
python3 jobs/sixbar-gap-transfer-04/free_phase_design.py
```

This validates against the merged -02 task, re-runs the design
search deterministically, writes
`runs/sixbar-gap-transfer-04/regenerated-task.json` and
`runs/sixbar-gap-transfer-04/free-phase-design-report.json`, and
prints the design table plus the comparison against the committed
task (1e-9 gates). Check the F1/F2/F3 lines in its output.

Then, with the experimental motion environment active (separate
from the main engine venv), the package installed as in
sixbar-gap-transfer-01:

```sh
mechanism-motion jobs/sixbar-gap-transfer-04/gap_transfer_freephase.motion.json --seed 580000050 --output runs/sixbar-gap-transfer-04/result-580000050.json
mechanism-motion jobs/sixbar-gap-transfer-04/gap_transfer_freephase.motion.json --seed 580000051 --output runs/sixbar-gap-transfer-04/result-580000051.json
mechanism-motion jobs/sixbar-gap-transfer-04/gap_transfer_freephase.motion.json --seed 580000052 --output runs/sixbar-gap-transfer-04/result-580000052.json
```

The same three seeds as -01/-02/-03; all outcomes recorded.

## Readings to report

- The design script's validation line and committed-comparison
  verdict (F1), plus the Python version line of the machine.
- Per seed: `qualified`, the evaluation count, and from the
  per_sample block: the worst position error and its sample, the
  worst orientation error and its sample, the worst spatial v and a
  errors and their samples (read natively; no external
  recomputation this time).
- The stops-vs-non-stop position averages per seed, direct from the
  per_sample block (F6).
- The most-violated scaled demand per seed (F7).
- The F1-F8 verdicts against this scorecard.

## What we will do with it

The outcome decides the case-study loop's direction on the agreed
rule. F4 held (a real family-level improvement) points the next
iteration at the budget sweep against a frozen scorecard -- the
demand side is now aimed at, and budget is the remaining standing
candidate. F4 missed means the free-phase lever did not reach the
solver either, and the next honest step is family succession
(dwell/cam per the queued briefs), NOT a fourth task variant -- the
critic's rule, adopted by this chat before this job was staged.
Recorded outcomes are data and are never rewritten.


## Recorded outcome (2026-10-18)

Run on the-hub (the -01/-02/-03 machine), the design script under
Python 3.14.4, right after Jean merged PR #52 in the browser: the
same git pull that brought this job's files reports public main
moving 885cab2 -> c3a7118. One invocation of the design script with
defaults from the repository root, then the solver once per seed in
the experimental motion environment (the package installed as in
sixbar-gap-transfer-01). The full printed report and the three
result JSONs were shared; the verdicts below read them.

**Machine-honesty note.** The first three-seed attempt ran against
the motion venv's stale installed package: its result files came
back schema_version 1 with no per_sample block -- the install
predated PR-A's units declarations and PR-B's per-sample emission,
so pulling this job did not refresh the solver that ran.
`python -m pip install ./experimental/motion` refreshed the
package, the stale files were archived on the machine as
result-<seed>.stale-schema1.json, and the three seeds were re-run.
The stale attempt is recorded here as data, not hidden; the
compliant run below is what the scorecard is scored against: three
result files at schema_version 3 with native per_sample blocks --
the first case-study record read with no external recomputation
pipeline.

**Scorecard verdicts (frozen before the run):**

- **F1 (reproduction) HELD.** Validation residuals on the machine:
  positions 2.84e-14 mm, baseline v 4.44e-16, baseline a 6.16e-15
  -- identical to the staging-side values to every printed digit,
  six orders inside the 1e-9 gates. The search reproduced the
  committed placements exactly (23,298 objective evals, 5,017 peak
  evals, 225 accepted moves; winning start: the -02 baseline), and
  the committed-comparison line reads AGREE, max residual 0 over
  q/v/a, byte-identical -- the hoped-for byte-identity held on
  this machine. Python 3.14.4.
- **F2 (design fact) HELD, scored by F1.** Max scaled sample demand
  27.07x the gates (76.2% of -02's 35.53x), max sample acceleration
  1.3118 normalized: the committed design reproduced on the machine.
- **F3 (demand-side stop dissolution) HELD by construction.** The
  machine reproduction confirms the worst prescribed samples sit on
  the flat mid-carry speed plateau (phases 1/2/3 at 27.07x) with
  the stops in a near-tie behind (26.24x, 25.21x): the -01/-02
  constant (stops worst by a wide margin) did not survive free
  placement.
- **F4 (primary, decision item) REFUTED, as the frozen lean
  stated.** The best of the three seeds reaches a worst-sample
  position error of 0.12570 normalized (34.6 mm; seed 580000050,
  sample 10) -- above the 0.1000 bar (27.5 mm). The honest
  cross-read: -02's recorded best was 0.1219 (33.6 mm), so
  best-vs-best the free-phase variant moved +3.1% -- no
  family-level improvement. The 23.8% demand cut did not reach
  the solver's position error.
- **F5 (strong form) REFUTED, as the frozen prediction stated.**
  0.12570 is above the 0.0742 halving bar (the -02 D1 bar).
- **F6 (solver-side stop survival) HELD with the weakened margin,
  as the frozen prediction stated.** The single worst position
  sample sits at a process stop in 2 of the 3 seeds (seeds
  580000051 and 580000052, both at sample 4, the set-down T3);
  seed 580000050's worst migrated to sample 10 (the return line
  before the left corner join) -- the stop-relief reading landing,
  equally data, as the scorecard pre-stated. The stops-vs-non-stop
  position average gap narrowed to 1.43x / 1.26x / 1.94x from
  -01/-02's 1.4-2.1x.
- **F7 (binding aggregate) REFUTED as stated, through the
  pre-declared finding branch.** Spatial acceleration stayed the
  most-violated scaled demand in seeds 580000050 (17.94x its gate
  vs velocity's 14.54x) and 580000052 (19.35x vs 14.71x), but in
  seed 580000051 the velocity error is the most-violated demand:
  19.69x vs acceleration's 19.66x, a 0.034x (0.2%) margin -- the
  first binding-aggregate migration to the velocity error in this
  case study, declared in advance as a finding, not a scorecard
  failure. The pre-stated narrowing also holds: the acceleration
  demand fell to 17.94-19.66x its gate from -02's 27.8-29.9x.
- **F8 (control) HELD.** The same three seeds 580000050/51/52, one
  solver attempt each, the standard 200-evaluation budget, the
  same initialization declarations as -01/-02; per-seed reporting
  read natively from the result schema's per_sample block
  (schema_version 3). No gate loosened; the all-`qualified:
  false` outcome is recorded as valid data; the -01/-02/-03
  records stay untouched.

**Per-seed readings** (selected candidates; normalized, mm at
275.1363 mm per unit; samples 0 and 4 are the process stops):

| seed | selected init. | worst position (sample) | in mm | worst orientation deg (sample) | worst spatial v (sample) | worst spatial a (sample) | most-violated demand | stops vs non-stops |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 580000050 | random | 0.12570 (10) | 34.6 | 8.32 (11) | 0.29082 (5) | 0.89687 (4) | acceleration 17.94x | 1.43x |
| 580000051 | original | 0.18509 (4) | 50.9 | 0.88 (9) | 0.39384 (5) | 0.98288 (4) | velocity 19.69x (vs a 19.66x) | 1.26x |
| 580000052 | random | 0.13793 (4) | 38.0 | 9.63 (11) | 0.29420 (5) | 0.96757 (4) | acceleration 19.35x | 1.94x |

All three seeds unqualified at the standard 200-evaluation budget;
solver wall time about 8.1-8.5 s per seed.

**Reading.** The free-phase lever did exactly what it aimed at and
nothing more: the solver's spatial acceleration demand fell to
17.94-19.66x its gate from -02's 27.8-29.9x -- a real ~30% cut at
the binding aggregate, the lever this job existed to pull -- and
the position error did not follow: best-vs-best 0.12570 vs -02's
0.1219 (+3.1%). Two levers have now missed the position error on
this family (bottom-stop removal in -02, demand prescription in
-04), so the case study's position error is not carried by the
sample-level derivative demand or by the bottom stops. Seed
580000051 adds that the velocity demand is now within 0.2% of the
acceleration demand at the top -- the demand headroom the design
script bought at the samples is already being spent.

**Machine.** the-hub, Python 3.14.4 (design script, pure standard
library); the solver in the experimental motion environment, the
package refreshed from the merged tree at public main c3a7118;
runs from the repository root; three result files at
runs/sixbar-gap-transfer-04/result-580000050/51/52.json plus the
archived schema-1 first attempt.

**What this gives the next iteration.** F4 missed, so the agreed
succession rule engages: family succession (dwell/cam per the
queued briefs), NOT a fourth task variant of this family. The
budget sweep against a frozen scorecard remains the standing
in-family candidate if the family question returns. Recorded
outcomes are data and are never rewritten.
