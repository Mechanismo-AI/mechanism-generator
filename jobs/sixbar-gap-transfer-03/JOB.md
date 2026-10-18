# Job sixbar-gap-transfer-03: case study B diagnostic -- the softened-timing recompute

**Purpose.** Both recorded case study B runs agree on one number: the
spatial ACCELERATION error is the binding aggregate. In -01 it sat at
46.0-54.8x its 0.05 gate, in -02 at 27.8-29.9x, ahead of position and
orientation in every seed of both jobs; and both records put the worst
position samples at the two process stops (pick T1, set-down T3), with
the stops costing 1.6-2.1x the non-stop samples. The standing candidate
list names a dwell-relaxed pick and set-down as the cheapest stop
relief. Before staging any new task variant for the solver, this job
asks the task-side arithmetic question that decides which candidate is
worth a run: is the prescribed acceleration demand carried by the STOP
TIMING (the clamped-cubic dwell forced to zero speed at phases 0 and 4)
or by the PHASE-LOCKED GRID (twelve samples pinned to the 30-degree
crank grid, so the corner junctions land mid-window at whatever speed
that grid imposes)? The instrument is a script, not a solver run: it
reads the merged -02 task JSON, rebuilds and validates the recorded
timing construction, then recomputes the prescribed per-sample demands
under dwell-relaxed timing variants. Task-side arithmetic only: this
job changes no engine, package, or spec code, runs no solver, and
rewrites nothing in any recorded outcome. Selected as the next staged
item by the group (the critic's ranking: 1) this recompute, 2) the
result-schema units declaration, 3) per-sample emission, 4) the
free-phase variant only if this recompute shows the prescription
binds).

**Task.** `softened_timing_recompute.py` in this directory, pure
standard-library Python (argparse, json, math, os only; no numpy, no
packages, any Python 3). It reads the merged -02 task
`../sixbar-gap-transfer-02/gap_transfer_nostops.motion.json`
(`--task` to override) and writes
`runs/sixbar-gap-transfer-03/softened-timing-report.json`
(`--output` to override), plus a printed report.

**Method.** Three stages, each fail-closed:

1. **Rebuild and validate.** The -02 path model (the arc-length
   parametrized racetrack: carry 260 mm, 15 mm radius corner arcs,
   bounding-box diagonal 275.1363... mm, centroid exactly (0, +5) mm)
   and the recorded timing (two clamped cubic runs, the carry phases
   0-4 and the bottom loop phases 4-12 closing at phase 0, zero speed
   at the two stops) are reconstructed from the -02 JOB.md audit trail.
   Validation gates, abort on failure: the twelve sample positions
   reproduce the task JSON's to 1e-9 mm, and the rebuilt baseline
   reproduces all 36 velocity and all 36 acceleration components the
   JSON itself emits to 1e-9 normalized.
2. **Dwell variants.** The stop dwell is relaxed symmetrically: a
   dwell half-width delta around both stops (knots pulled in by delta,
   samples 0 and 4 forced to zero speed and zero acceleration -- a
   genuine dwell), for delta in {0 (the recorded baseline), 5, 10, 15}
   degrees. The sample POSITIONS never move: same path, same 30-degree
   grid; only the timing law changes. Per-sample v and a are
   recomputed with the same conventions as the -02 record (v = T s',
   a = C s'^2 + T s''; the vector-mean stop and junction prescriptions
   as documented there).
3. **Between-sample peaks and floors.** A fine grid (0.02 degree)
   tracks the between-sample prescribed acceleration peak per variant
   (the samples pin the prescription only AT the samples; the spline
   in between is what a densified demand would see), and mean-value
   floors are computed: each 30-degree window's mean speed, and the
   corner-junction centripetal demand at the junction window's mean
   speed -- a delta-independent property of the path on the fixed
   grid.

**Staging-side verification** (the audit trail; the design-time
prototype was an independent TypeScript transcription of the -02
arithmetic, later re-transcribed into this script; the script was then
run once at staging time against the merged -02 task JSON as a smoke
test). Validation residuals: sample positions 2.8e-14 mm, baseline
velocities 4.4e-16, baseline accelerations 6.2e-15 normalized -- six
orders inside the 1e-9 gates, agreeing with the design-time prototype
to 6.2e-15. Variant table (max sample |a| per phase, between-sample
fine-grid peak, max sample speed, speed swing vs the cycle-mean
speed):

| delta (deg) | max sample a (mm/rad^2) | normalized | at phase | between-sample peak (norm) | max sample speed (norm) | swing |
| --- | --- | --- | --- | --- | --- | --- |
| 0 (baseline) | 488.82 | 1.7767 | 4 (stop) | 2.9520 | 0.5801 | 1.56 |
| 5 | 350.17 | 1.2727 | 3 (carry) | 4.3545 | 0.6733 | 1.75 |
| 10 | 592.73 | 2.1543 | 1 (carry) | 6.8847 | 0.8272 | 2.05 |
| 15 | 1034.58 | 3.7603 | 1 (carry) | 12.1995 | 1.1075 | 2.56 |

Floors: the corner-junction window's mean speed is 102.30 mm/rad, so a
sample sitting on the junction at that speed carries a centripetal
demand of 348.81 mm/rad^2 (1.2678 normalized) regardless of delta --
the dwell does not touch the junction demand.

**Prediction scorecard (frozen before the run).** The scorecard is
scored against Jean's machine run of the script, not against the
staging-side smoke test; the smoke test numbers above are on record so
the machine run is a reproduction, and a material disagreement is
itself a finding.

- **R1 (validation):** the script passes both validation gates on the
  machine (positions to 1e-9 mm, baseline v and a to 1e-9
  normalized) and the printed residuals agree with the staging-side
  values to well within the gates. A gate failure aborts loudly; any
  silent pass-around would be a defect.
- **R2 (primary, "timing law softenable at fixed phases"):** some
  delta in {5, 10, 15} reduces the max sample |a| by at least 40%
  against the baseline AND keeps the between-sample peak at or below
  2x the baseline's. Design-time prediction: REFUTED -- the best
  variant, delta = 5, cuts the max sample |a| by only 28.4% (350.17
  vs 488.82) while the between-sample peak rises to 1.47x baseline
  (4.3545 vs 2.9520), and delta = 10 and 15 are WORSE than the
  baseline at the samples themselves (592.73 and 1034.58, +21% and
  +112%): the dwell moves the deceleration into the neighbouring
  carry samples instead of removing it.
- **R3 (relocation reading):** under dwell, the worst prescribed
  samples leave the stops and land on the carry neighbours (phases 1
  and 3); the corner junctions ease slightly (351.6 -> 328.4 mm at
  delta = 5) but the between-sample peaks grow monotonically with
  delta (1.47x / 2.33x / 4.13x baseline); the speed swing grows
  (1.56 -> 2.56); the junction floor is delta-independent. Reading:
  dwell softening RELOCATES and AMPLIFIES demand; it does not remove
  it.
- **R4 (decision):** R2 refuted on the machine means the binding
  prescription is the phase-locked 30-degree grid, not the stop
  timing -- the samples pin the corners to mid-window travel where
  the speed is what the grid says, and no timing law on that grid
  relieves the acceleration. This unlocks the free-phase variant
  (sample phases free to place the corners at low-speed points),
  staged after the result-schema PRs per the group ranking. R2 held
  would instead point the next iteration at staging the dwell-relaxed
  task JSON for the solver.
- **R5 (control):** no gate is loosened, no recorded outcome is
  rewritten, the script only reads the merged -02 task. The -02
  record stays data.

**Honest scope.**

- The dwell widths {5, 10, 15} degrees are a probe ladder, not a
  design proposal; no dwell is proposed for any real machine.
- The between-sample peaks are fine-grid maxima of the PRESCRIBED
  spline (0.02 degree), not observations of the solver's actual
  between-sample behaviour -- the solver's path is not what is being
  measured here.
- The floors are mean-value arguments (a junction sample at the
  window-mean speed), honest as lower-bound reasoning, not proofs
  that any particular timing attains them.
- This job computes what the PRESCRIPTION demands; it says nothing
  about what the linkage family reaches. A demand-side reduction is
  necessary, not sufficient, for a solver-side improvement.
- The variants keep the sample positions fixed. A dwell-relaxed TASK
  variant (a new motion JSON with the recomputed v and a) is NOT
  staged by this job; this job only computes what that file would
  prescribe, so the next decision is made from data.

**Machine.** Any machine with any Python 3 (pure standard library; no
venv or packages required). Cost: seconds. the-hub is not needed but
is the natural place, since the -01 and -02 records were made there.

## Steps

From the repository root, with any Python 3:

```sh
python3 jobs/sixbar-gap-transfer-03/softened_timing_recompute.py
```

Defaults: `--task` resolves relative to the script
(`../sixbar-gap-transfer-02/gap_transfer_nostops.motion.json`),
`--output` relative to the working directory
(`runs/sixbar-gap-transfer-03/softened-timing-report.json`). Share the
printed report and the JSON file.

## Readings to report

- The two validation residual lines (R1), verbatim from the printed
  report.
- The variant table: max sample |a| and its phase, between-sample
  peak, max sample speed, swing, per delta (R2, R3).
- The floors line (R3).
- The R1-R5 verdicts against this scorecard.
- The Python version line of the machine used.

## What we will do with it

The outcome decides which standing candidate earns the next solver
run. R2 held would stage the dwell-relaxed task variant; R2 refuted
(the design-time reading) establishes that the phase-locked grid binds
the prescription, unlocking the free-phase variant after the
result-schema PRs (units declaration first, then per-sample emission)
per the group ranking -- so the acceleration demand can finally be
aimed at directly, with per-sample emission already in hand. Recorded
outcomes are data and are never rewritten.
