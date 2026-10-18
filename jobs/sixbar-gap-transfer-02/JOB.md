# Job sixbar-gap-transfer-02: case study B diagnostic -- the no-bottom-stops variant of the gap-transfer motion task

**Purpose.** Direct follow-up to sixbar-gap-transfer-01, whose recorded
outcome (all three seeds `qualified: false`; best worst-sample position
error 0.1484 = 40.8 mm, 14.8x the solver's own 0.01 gate and 27.2x the
0.005452 packaging overlay) carried a per-sample reading: the stops
bind. The single worst position sample was one of the four full-stop
phases in 3/3 seeds, and the four stops averaged 1.6-2.0x the eight
non-stop samples; the one demand the family demonstrably reaches is
mid-gap levelness (0.14-1.05 deg at T2, inside the 1.5 deg packaging
orientation tolerance at that sample). This job asks the obvious
follow-up with the cheapest possible change: the carry and the two
PROCESS stops (pick T1, set-down T3) stay frozen exactly as in -01;
the two BOTTOM stops (phases 6 and 9, the 180 deg inward-turnaround
reversals) are removed and replaced by a smooth bottom join. If the
bottom stops carry the failure, the same seeds and budget should do
markedly better; if the process stops bind, they should not. Task-only:
this job changes no engine, package, or spec code and runs nothing at
staging time.

**Task.** `gap_transfer_nostops.motion.json` in this directory, in the
solver's input contract: exactly five fields, 12 fixed phases, two known
branches, 12x3 position/velocity/acceleration samples. Physical frame
unchanged from -01: millimetres, origin at gap centre on the belt line,
y up; 1 normalized unit = 275.14 mm (the same bounding-box diagonal,
260 mm x 90 mm; the twelve-sample bounding box is identical to -01's).
All 12 phases carry orientation 0 rad (level) with zero angular
velocity and acceleration. T1/T2/T3 remain phases 0/2/4.

The loop (the same pick-and-place racetrack; the return leg below the
belts):

- **Carry, phases 0-4:** (-130, 50), (-65, 50), (0, 50), (+65, 50),
  (+130, 50) mm -- identical to -01 sample for sample; the carry run's
  knots and timing are identical to -01's.
- **Descent, phase 5:** (+130, 5) mm -- 45 mm down the belt-end plane
  from the set-down point.
- **Right corner and return, phases 6-10:** a 15 mm radius corner arc
  turns the descent into the return line at (+115, -40), then the
  return in uniform 57.5 mm steps: (+57.5, -40), (0, -40), (-57.5,
  -40), (-115, -40) mm, 40 mm below the belt line.
- **Left corner and ascent, phase 11, closing at phase 0:** the
  mirrored 15 mm corner arc, then the ascent; phase 11 at (-130, 5)
  mm, 30 mm above the corner join.

Timing: the crank turns uniformly; the sample timing s(theta) is a
clamped cubic spline with zero speed at the two stops, built as two
runs (the carry, phases 0-4; the bottom loop, phases 4-12), the same
construction as -01. The tool comes to a FULL STOP at exactly two
phases -- pick T1 (phase 0) and set-down T3 (phase 4), both process
stops. The bottom path is now C1 (tangent-continuous) end to end, so
non-zero speed through the bottom is self-consistent; in -01 the 180
deg reversals were tangent-discontinuous and forced zero speed there.
At each stop the prescribed acceleration is the mean of the
deceleration into the stop and the acceleration out of it (the process
corners are 90 deg turns, so the mean is a genuine vector mean, not
collinear as in -01). Two samples sit exactly on line/arc junctions
(phases 6 and 10, speed non-zero): there the prescribed acceleration
is the mean of the line-side and arc-side one-sided accelerations --
the same convention -01 used at its zero-speed joins. Mean arc per
30 deg step: carry 65 mm, descent 45, 53.56 mm across each corner
join, return 57.5 -- the return now runs SLOWER than the carry
(57.5 vs 65 mm per step), a sample-allocation consequence of covering
a longer bottom path with the same twelve samples; in -01 the return
was the fast leg.

| Phase | theta (deg) | Tool point (mm) | Arc pos (mm) | Speed (mm/rad) | Accel (mm/rad^2) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | (-130.00, 50.00) | 0.00 | 0 (stop) | 488.82 | pick (T1); full stop |
| 1 | 30 | (-65.00, 50.00) | 65.00 | 159.61 | 203.22 |  |
| 2 | 60 | (0.00, 50.00) | 130.00 | 106.41 | 0.00 | T2, mid-gap |
| 3 | 90 | (65.00, 50.00) | 195.00 | 159.61 | 203.22 |  |
| 4 | 120 | (130.00, 50.00) | 260.00 | 0 (stop) | 488.82 | set-down (T3); full stop |
| 5 | 150 | (130.00, 5.00) | 305.00 | 115.64 | 101.45 | descent |
| 6 | 180 | (115.00, -40.00) | 358.56 | 102.18 | 351.57 | right corner join; mean accel |
| 7 | 210 | (57.50, -40.00) | 416.06 | 112.00 | 12.51 |  |
| 8 | 240 | (0.00, -40.00) | 473.56 | 108.73 | 0.00 |  |
| 9 | 270 | (-57.50, -40.00) | 531.06 | 112.00 | 12.51 |  |
| 10 | 300 | (-115.00, -40.00) | 588.56 | 102.18 | 351.57 | left corner join; mean accel |
| 11 | 330 | (-130.00, 5.00) | 642.12 | 115.64 | 101.45 | ascent; closes at phase 0 |

**How the JSON was built** (the file is the frozen artifact; this is
the audit trail): the loop is arc-length-parametrized (the two corner
joins are exact circular arcs, 15*pi/2 = 23.5619 mm each; no numerical
quadrature is needed on this loop); the timing is the clamped cubic
spline above; v = T s' and a = C s'^2 + T s'' with T the travel
tangent and C the curvature vector (C = 0 at every sample except the
two junction means); positions are scaled by the bounding-box diagonal
and centred on the twelve-sample centroid (exactly (0, +5) mm by
symmetry) -- the validator's actual rule (sample mean zero and unit
bounding-box diagonal, each to 1e-8). Sample values were re-checked by
independent central finite differences of the composed trajectory
(h = 1e-3 rad): velocities agree to 2.44e-1 mm/rad and
accelerations to 7.42e-1 mm/rad^2 over all twelve samples;
the interior samples agree to 1.29e-4 mm/rad and
3.88e-1 mm/rad^2, the stop samples to
3.83e-1 mm/rad^2 and the junction samples to
7.42e-1 mm/rad^2 (a central difference straddling a
direction change or a curvature jump returns the one-sided mean by
construction, which is exactly what is prescribed there). The -01
timing construction was re-derived and checked against the merged -01
task file before this one was built: positions reproduce to
1.19e-9 mm, velocities to 1.25e-9 mm/rad,
accelerations to 8.32e-9 mm/rad^2 over all twelve samples, and
both tasks' splines are C2 at every interior knot to
2.93e-12 mm/rad^2. Normalized sample
magnitudes: speeds up to 0.5801 units/rad and accelerations up to
1.7767 units/rad^2 -- numerically gentler than -01 (0.722 and
3.121), as expected with two stops instead of four.

**Honest scope.**

- The stop STRUCTURE is preserved (two full stops, zero speed,
  dwell-compatible) but the stop GEOMETRY is not: the process corners
  are 90 deg turns, not -01's collinear 180 deg reversals. Recorded
  confound: a D1 miss cannot cleanly separate "two stops are still too
  many" from "90 deg corners are harder than collinear reversals".
- The 15 mm corner radius and the descent along the belt-end plane are
  a PROPOSAL. Clearance to the conveyor frames below the belts is
  unverified; screening the loop against a keep-out zone remains the
  existing sampled-occupancy tooling's job once a qualified candidate
  exists to screen.
- The return runs slower than the carry (57.5 vs 65 mm per step):
  twelve samples must cover a longer bottom path. A real carrier
  usually returns faster; this is a sample-allocation consequence,
  not a design demand.
- `branches: [-1, +1]` are the design's assembly choices, prescribed
  because the input contract rejects unknown branches.
- Twelve samples encode straightness and levelness at the samples
  only; continuous-path straightness between samples is a
  densification follow-up.
- No operating speed, drive law, payload capacity or motor is
  prescribed: v and a are per crank radian.

**Tolerance overlay.** Unchanged from -01. The solver's strict
qualification gate is 0.01 normalized position error. The packaging
tolerance is 1.5 mm = 0.005452 normalized. For scale: the four-bar
frontier from gap-transfer-failure-01, rescaled to this task's units,
is 0.0330 worst pose; -01's six-bar best was 0.1484.

**Machine.** Any idle CPU PC (no GPU) with the separate experimental
motion environment (experimental/motion/README.md); the -01 run used
the-hub (Python 3.14, torch 2.13.0+cpu, numpy 2.5.1). Cost: one solver
attempt per seed, at most 200 refinement evaluations each -- minutes
per seed, not hours.

## Steps

From the repository root, with the experimental environment active
(separate from the main engine venv), the package already installed as
in sixbar-gap-transfer-01:

```sh
mechanism-motion jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json --seed 580000050 --output runs/sixbar-gap-transfer-02/result-580000050.json
mechanism-motion jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json --seed 580000051 --output runs/sixbar-gap-transfer-02/result-580000051.json
mechanism-motion jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json --seed 580000052 --output runs/sixbar-gap-transfer-02/result-580000052.json
```

The same three seeds as -01 (580000050/51/52); all outcomes recorded.

## Prediction scorecard (frozen before the run)

- **D1 (primary):** the best of the three seeds' selected candidates
  has worst-sample position error at most 0.0742 normalized (20.4 mm)
  -- half -01's best 0.1484. If the bottom stops carried the -01
  failure, removing them should at least halve the worst error; a
  result no better than -01 says the smooth bottom join costs the
  family as much as the bottom stops did.
- **D2 (structure):** every seed's single worst position sample is one
  of the two process stops (phase 0 or 4). If the worst sample moves
  to the smooth corners or the return, the binding structure is no
  longer the stops.
- **D3 (levelness):** the best candidate's phase 2 (T2) orientation
  error is within 1.5 deg -- the -01 mid-gap levelness near-pass
  (0.14-1.05 deg) should reproduce on the unchanged carry.
- **D4 (control):** an all-`qualified: false` outcome is a valid
  recorded result, not an error. The follow-up reading is per-sample,
  as in -01: process-stop failures vs smooth-corner failures separate
  "the stops bind" from "the family does not close the gap as
  instantiated". Either way the next iteration (free phases, larger
  refinement budget, per-sample emission in the result schema) is
  designed from the recorded data, never by loosening a gate.

## Readings to report

- Per seed: `qualified`, the evaluation count, and for the selected
  candidate: worst sample position error and which sample, worst
  orientation error, worst first/second derivative errors.
- For the best candidate overall: D1-D4 verdicts against this
  scorecard, and the per-sample position profile recomputed
  externally from the returned geometry as in -01 (the result schema
  still emits aggregates only).

## What we will do with it

The outcome decides whether -01's failure was carried by the bottom
stops. A D1 pass with D2 held points the next iteration at the
process stops themselves (a dwell-relaxed pick and set-down, or the
free-phase variant); a D1 miss with the worst errors spread over the
smooth bottom says the twelve-phase closed loop with derivative
demands is beyond the family at this budget regardless of stop count,
and motivates the free-phase and budget branch. Recorded outcomes are
data and are never rewritten.
