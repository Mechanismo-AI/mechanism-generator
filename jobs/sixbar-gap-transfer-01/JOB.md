# Job sixbar-gap-transfer-01: case study B -- the gap-transfer cycle asked of the experimental six-bar motion solver

**Purpose.** Third step of the case-study loop for the six-bar (brief,
failure analysis, capability), case study B: the gap transfer. The failure
analysis (gap-transfer-failure-01) recorded the honest four-bar frontier
on the 260 mm level carry: zero selections at packaging tolerance, best
worst-pose position error about 6x over the 1.5 mm tolerance, mid-gap sag
the dominant structure. This job gives the separately installable
experimental six-bar motion solver (docs/experimental-motion.md) its
first real measured brief -- the full carry cycle, not just the three
poses: level carry across the gap at the packaging plane, inward
turnarounds inside the gap footprint, return below the belt line -- as
one closed 12-phase motion task. The outcome is recorded against the
scorecard below, frozen before the run. The experimental package is not
the main engine; this job changes no engine or spec code and runs
nothing at staging time.

**Task.** `gap_transfer.motion.json` in this directory, in the solver's
input contract: exactly five fields, 12 fixed phases, two known
branches, 12x3 position/velocity/acceleration samples. Physical frame:
millimetres, origin at gap centre on the belt line, y up; 1 normalized
unit = 275.14 mm (this task's bounding-box diagonal, 260 mm x 90 mm).
All 12 phases carry orientation 0 rad (level) with zero angular velocity
and acceleration: the parallel-carry demand, aimed directly at the
four-bar's recorded sag and levelness failures. T1/T2/T3 of the failure
analysis are phases 0/2/4.

The loop (a pick-and-place racetrack; the return leg below the belts):

- **Carry, phases 0-4:** (-130, 50), (-65, 50), (0, 50), (+65, 50),
  (+130, 50) mm -- the 260 mm carry in uniform 65 mm steps, 50 mm above
  the belt line.
- **Right turnaround, phases 5-6:** half-ellipse inward of the belt end,
  centre (+130, 5), semi-axes 20 mm inward x 45 mm: phase 5 (+110, 5),
  phase 6 (+130, -40). Stays inside the gap footprint.
- **Return, phases 7-9:** (+43.33, -40), (-43.33, -40), (-130, -40) mm
  -- uniform 86.67 mm steps, 40 mm below the belt line.
- **Left turnaround, phases 10-11, closing at phase 0:** the mirrored
  half-ellipse, sampled at equal arc thirds (computed numerically).

Timing: the crank turns uniformly; the sample timing s(theta) is the
clamped cubic spline through the twelve arc positions with zero speed
at the corners. The tool comes to a FULL STOP at four phases -- the two
carry ends (pick T1, set-down T3) and, a geometric consequence of the
inward turnarounds rather than a process demand, the two bottom joins
(phases 6 and 9). A corner with non-zero speed would demand a velocity
direction jump no smooth mechanism can produce; zero speed is the only
self-consistent prescription there, and it matches how a real carrier
dwells at pick and set-down. At each stop the prescribed acceleration is
the mean of the deceleration into the stop and the acceleration out of
it (collinear by construction). Mean arc per 30 deg step: carry 65 mm,
right turnaround 52.96, return 86.67 mm, left turnaround 35.30;
the carry runs slower than the return, as a carrier should.

| Phase | theta (deg) | Tool point (mm) | Arc pos (mm) | Speed (mm/rad) | Accel (mm/rad^2) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | (-130.00, 50.00) | 0.00 | 0 (stop) | 638.24 | pick (T1); full stop |
| 1 | 30 | (-65.00, 50.00) | 65.00 | 159.61 | 203.22 |  |
| 2 | 60 | (0.00, 50.00) | 130.00 | 106.41 | 0.00 | T2, mid-gap |
| 3 | 90 | (65.00, 50.00) | 195.00 | 159.61 | 203.22 |  |
| 4 | 120 | (130.00, 50.00) | 260.00 | 0 (stop) | 696.19 | set-down (T3); full stop |
| 5 | 150 | (110.00, 5.00) | 312.96 | 151.71 | 227.32 | turnaround apex |
| 6 | 180 | (130.00, -40.00) | 365.91 | 0 (stop) | 858.77 | full stop |
| 7 | 210 | (43.33, -40.00) | 452.58 | 198.63 | 379.35 |  |
| 8 | 240 | (-43.33, -40.00) | 539.25 | 198.63 | 379.35 |  |
| 9 | 270 | (-130.00, -40.00) | 625.91 | 0 (stop) | 800.82 | full stop |
| 10 | 300 | (-111.58, -12.56) | 661.22 | 80.91 | 173.38 |  |
| 11 | 330 | (-111.58, 22.56) | 696.52 | 80.91 | 173.38 |  |

**How the JSON was built** (the file is the frozen artifact; this is the
audit trail): the loop is arc-length-parametrized (ellipse arcs by
numerical quadrature; the left turnaround samples sit at equal arc
thirds); the timing is the clamped cubic spline above; v = T s' and
a = C s'^2 + T s'' with T the travel tangent and C the curvature
vector; positions are centred on the bounding box and scaled by its
diagonal. Sample values were re-checked by independent finite
differences of the composed trajectory: velocities agree to
2.4e-6 mm/rad, accelerations to
7.2e-2 mm/rad^2, the one-sided stop accelerations
to 3.0e-2 mm/rad^2, and sampled positions
reproduce the table to 1.4e-13 mm. Normalized
sample magnitudes: speeds up to 0.722 units/rad and
accelerations up to 3.121 units/rad^2 (the studied
synthetic example runs about 0.2-0.4 and 0.1-0.5) -- this task is
numerically demanding as well as geometrically.

**Honest scope.**

- The return plane at -40 mm and the 20 mm inward bulge are a PROPOSAL.
  Clearance to the conveyor frames below the belts is unverified;
  screening the loop against a keep-out zone is the existing
  sampled-occupancy tooling's job once a qualified candidate exists to
  screen.
- `branches: [-1, +1]` are the design's assembly choices, prescribed
  because the input contract rejects unknown branches.
- Twelve samples encode straightness and levelness at the samples
  only; continuous-path straightness between samples is a densification
  follow-up.
- No operating speed, drive law, payload capacity or motor is
  prescribed: v and a are per crank radian.

**Tolerance overlay.** The solver's strict qualification gate is 0.01
normalized position error. The packaging tolerance is 1.5 mm =
0.005452 normalized -- 1.83x tighter than the solver's own
gate. The scorecard therefore separates "the solver qualified it" (its
gate) from "the packaging overlay is met" (the brief's gate). For scale:
the four-bar frontier from gap-transfer-failure-01, rescaled to this
task's units, is 0.0330 worst pose (9.1 mm, positive
direction) and 0.0380 (10.4 mm, negative) -- the
six-bar must beat the recorded four-bar frontier by more than 6x to
reach packaging tolerance.

**Machine.** Any idle CPU PC (no GPU) with a separate Python 3.12
environment for the experimental package (experimental/motion/README.md).
Cost: one solver attempt per seed, at most 200 refinement evaluations
each -- minutes per seed, not hours.

## Steps

From the repository root, with the experimental environment active
(separate from the main engine venv):

1. Install once:

```sh
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install numpy==2.5.1
python -m pip install ./experimental/motion
```

2. Run the three seeds (the documented example seed plus its two
neighbours; all outcomes recorded):

```sh
mechanism-motion jobs/sixbar-gap-transfer-01/gap_transfer.motion.json --seed 580000050 --output runs/sixbar-gap-transfer-01/result-580000050.json
mechanism-motion jobs/sixbar-gap-transfer-01/gap_transfer.motion.json --seed 580000051 --output runs/sixbar-gap-transfer-01/result-580000051.json
mechanism-motion jobs/sixbar-gap-transfer-01/gap_transfer.motion.json --seed 580000052 --output runs/sixbar-gap-transfer-01/result-580000052.json
```

## Prediction scorecard (frozen before the run)

- **C1 (primary):** at least one of the three seeds returns
  `qualified: true` under the solver's own strict gates on this task.
  The task is far harder than the studied synthetic example (a long
  level carry, a closed loop, four full stops), so this is a genuine
  prediction, not a formality.
- **C2 (the brief's gate):** packaging overlay met -- the best
  candidate's worst position error over all 12 samples is at most
  0.005452 normalized (1.5 mm). C2 implies C1; a
  C1-without-C2 outcome would close most of the four-bar gap without
  reaching packaging tolerance and is a valuable recorded result.
- **C3 (structure):** no mid-gap sag -- for the best candidate, among
  the five carry samples (phases 0-4) the mid-gap phase 2 (T2) is NOT
  the single largest position error. If the sag persists in the
  two-loop family too, the sag is brief-inherent rather than
  topology-inherent; either reading is data.
- **C4 (control):** an all-`qualified: false` outcome is a valid
  recorded result, not an error. The follow-up reading is per-sample:
  if failures concentrate at the four stops, the carry demand may be
  within reach and the stops are the binding structure; if they
  concentrate on the carry, the two-loop family does not close the gap
  as instantiated. Either way the next iteration (free phases, larger
  refinement budget, task variants without the bottom stops) is
  designed from the recorded data, never by loosening a gate.

## Readings to report

- Per seed: `qualified`, the refinement/evaluation count, and for the
  best candidate: worst sample position error and which sample, worst
  orientation error, worst first/second derivative errors.
- For the best candidate overall: the position error profile over the
  five carry samples (phases 0-4), the C2 overlay verdict and the C3
  structure verdict.
- Machine, CPU, Python, torch and numpy versions.

## What we will do with it

The outcome sizes the six-bar motion family against the recorded
four-bar frontier on a real brief, and decides the branch: a C2 pass
motivates graduating the six-bar toward the main engine (spec
vocabulary, portfolio, adapter -- with keep-out screening of the
return loop first); a C1-only pass motivates iterating the task and
budget; an all-fail outcome feeds the free-phase and budget
iteration. Record the outcome against the scorecard in this file;
recorded outcomes are data and are never rewritten.
