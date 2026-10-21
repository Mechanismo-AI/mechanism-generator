# Case study D failure-digest instrument -- the staged analytic at-bat (case-d-digest-01)

Staged 2026-10-21 per the merged D brief freeze (jobs/case-d-brief-01/
JOB.md, PR #103) and the merged derivation check (jobs/
case-d-derivation-check-01/JOB.md, PR #104: N = 4, the count rule
fires at 7 = N + k, W_v = W_a = 0), the standing sequencing recorded
in continuity entries 70-71 NEXT. This staging IS the freeze's
instrument step: three task artifacts, the digest instrument script,
and this freeze record. NO RUN claimed: the owner executes every run;
nothing auto-runs at staging; the predictions below are frozen
BEFORE any run. No verdict on D's task is claimed by this document.

## Purpose

The failure digest runs FIRST (the brief's digest-first rule: the
analytic at-bat, before any learned supplier is measured; in a
no-ground-truth family its finds are the training corpus's only
honest source). This staging freezes the demand task, the two
control tasks, the fairness-gate configuration with reasons, the
scorecard wiring, and the predictions -- everything the owner's run
of record consumes, frozen before that run exists.

## The demand task (the derivation chain, visible end-to-end)

- THE CONTOUR: a closed ellipse loop, semiaxes 130 x 45 mm -- the
  case-B layout family's recorded 260 x 90 mm bounding box
  (envelope-with-lineage, the institutionalized -06 lesson;
  comparability the brief-A precedent). Declared distinct from case
  B's carry-with-stops and case C's swing; the task stands on task
  merits only.
- THE TIMING PROGRAM: uniform parametric transit in the crank phase
  (the parameter IS the crank angle, phase-locked by the engine's
  input contract; time IS a spec unit); pinned endpoints = the loop
  closure q(2 pi) = q(0); C2-class, ZERO declared derivative windows
  (W_v = W_a = 0) -> effective capacity floor((9 - 0 - 0) / 2) = 4 --
  the row the brief requires the demand declaration to carry.
- NORMALIZATION (desk-verified): the 12-sample centroid at the
  origin, one unit = the loop's bounding-box diagonal
  D = sqrt(260^2 + 90^2) = 275.13632984395207 mm; desk residuals:
  centroid 2.3e-17, diagonal 0. q(theta) = (130 cos theta,
  45 sin theta) / D; the tool orientation = the contour tangent
  atan2(45 cos theta, -130 sin theta), carried as program DATA,
  never pinned (the derivation check's step 2: D's frozen demand
  does not pin orientation; a future variant that pins it reads its
  own capacity drop from the same arithmetic); v and a analytic per
  crank radian. The program's own angular rate peaks at
  5850 / 2025 = 2.888888888888889 rad per crank rad at phases 0 and
  6 (program data; the solver's gates read ERRORS, not magnitudes).
- THE PRECISION POINTS: 7 = N + k pinned phases (0, 2, 3, 5, 7, 9,
  10), positions at the 0.10 mm class = 3.6345618209240703e-4
  normalized (computed from the mm scale, never transcribed; the
  instrument recomputes it at the run). The first point beyond
  exact capacity is point 5; the demand carries three beyond
  capacity, so the density diagnosis has more than one to read.
- BRANCHES (+1, +1): the discrete assembly-configuration selector
  declared once here (carried at zero in the derivation's count; no
  recorded evidence prefers a sign pair; declared, never re-drawn).
- STAGED FILE: demand_ellipse_7pin.motion.json (3,680 bytes). The
  artifact reproduces the analytic program at all twelve phases
  (desk-verified; the instrument re-pins it fail-closed at the run).

## Control A (the at-capacity control row, N = 4)

The recorded example program VERBATIM
(experimental/motion/examples/normalized-motion.json, 3,725 bytes;
the staged file is byte-identical at staging, and the instrument pins
parsed-content equality against the repo example at the run) -- the
RECORDED known-feasible task, the engine's own example, the
feasibility witness the brief's control row demands. Four pinned
phases (0, 3, 6, 9) = N; the solver's qualified flag IS the
feasibility witness: the derivation check's deferred capacity claim
machine-verified, never asserted (the midpoint-digest pattern
applied to D's founding claim; cheap -- the same engine the digest
runs anyway). Tolerances: the solver's own gates (the fairness
gate's acceptance rule). The demand-class tolerance is reported as
DATA only (a different basis: the example's own normalization, no
recorded mm mapping).

## Control B (the N + 1 = 5 recorded behavior)

The example program with a FIFTH pin moved: phase 1's position
offset by the declared (0.05, 0.0) (pre-move frame), then
re-centered and re-normalized (the engine's contract requires it;
recorded honestly): new centroid (0.0041666666666665825,
-1.2027416100105862e-16), new bounding-box diagonal
1.0000000000000002 (scale 0.9999999999999998), and the moved pin's
ACTUAL post-normalization displacement 0.04999999999999999 -- all
recomputed by the instrument at the run (its recomputation is the
authoritative record). The derivative rows carry the original
program's values, scaled -- the position/derivative inconsistency
at the moved pin is part of the declared demand, recorded as such.
STAGED FILE: control_b_moved5th.motion.json (3,717 bytes). Five
pinned points sit three beyond the four the family covers exactly;
the first point beyond capacity is the moved pin. The behavior is
RECORDED, never a gate.

## The fairness gate (frozen at the brief; restated with reasons)

- SEARCH PROTOCOL: the engine's own frozen chooser + restart
  protocol, consumed unmodified. Reason: the strongest reasonable
  configuration available WITHOUT modifying the pinned solver;
  raising the cap or altering the acceptance rule would be a
  supplier change, and the mod-count row forbids it (a stronger
  config would be a different supplier; the digest's configuration
  IS the analytic baseline the endgame's core lesson demands).
- EVALUATION BUDGET: 200 objective evaluations
  (maximum_objective_evaluations, as pinned in the result schema).
- ACCEPTANCE: strict qualification (the solver's own gates; the
  emission's qualified flag).
- SEEDS 580000050/51/52; per-seed reporting; no pooling.
- PRE-COMMITMENT: any later warm-start comparison runs THIS
  configuration with only the initialization changed (the
  one-variable discipline, frozen at the brief, restated so the
  digest's cost number is its honest baseline; a weak config would
  be the staged-declaration error recommitted one level down).

## The instrument (scorecard wiring; the flip-audit pattern)

case_d_digest_run.py (76,316 bytes; pure stdlib; ASCII only;
deterministic; fail-closed): consumes the three task artifacts, the
recorded example (the control-A provenance pin) and the nine
results (three tasks x three seeds); re-applies the engine's own
task contract fail-closed (s0, all three tasks); re-implements the
documented six-bar chain read-only and cross-checks the per-sample
emission (1e-4); then grades:

- D1 POOL CAPABILITY: the demand against ALL declared demands -- the
  7 pins at the 0.10 mm class, the between-points contour channel
  at the same class, the program channels under strict
  qualification. Honest failure is a recorded outcome, never a
  gate.
- D2 BINDING-CHANNEL CLASSIFICATION: position-at-pins vs
  timing-derivative vs between-sample, each channel read as its
  worst error relative to its own reference (the class for position
  and between-sample; the solver gates for the derivative rows);
  orientation carried as data, never a declared demand.
- D3 DEMAND-DENSITY DIAGNOSIS: the row that separates "family
  cannot do the task" from "demand density exceeds synthesis
  capacity", readable as the eight-bar trigger's evidence input;
  the trigger's input (i) reads NOT FIRED from a density finding
  (capacity is density, not shape reachability; the trigger fires
  at the capability step only on a demonstrated out-of-class
  finding, never a near-miss); trigger context (b)-shaped, (a)
  unfired; a control-A anomaly is recorded honestly, never a gate.
- AT-CAPACITY CONTROL ROW (N = 4) and N+1 CONTROL (5 pinned
  points): as frozen above; the N+1 behavior recorded, never gated.
- INTERVAL CHANNEL: the between-points contour deviation on the
  8x refinement grid (96 crank phases) against the declared
  analytic contour; SAMPLED, NEVER CERTIFIED; an undefined assembly
  anywhere on the grid is an ERROR row, never a quiet pass.
- COST: objective evaluations counted TWICE -- the analytic grade
  (the demand task's three runs; feeds the supplier baseline) and
  the data-generation cost (all nine runs; feeds the corpus budget
  accounting) -- supplier-version-scoped to the engine v0.1.0a11
  (SIX-BAR-NOW); the per-demand cost is real, nonzero and measured
  in the pinned oracle-call currency (the recorded 207.5/22.0
  accounting class) -- the operative cost clause travels with the
  verdict.
- FROZEN PREDICTIONS P1-P4, graded at the run (below).
- Mod-count 0 reciprocity row; additive schema-1.1 corpus emitter
  (units + provenance + a per-row basis field on every row; the two
  bases declared separately; unknown-kind refusal; sha256 hashes;
  the corpus identity anchored at the first digest row, the case-C
  convention); double-run determinism IDENTICAL check. Corpus
  outputs land in runs/ (gitignored, maintainer-local).

## The frozen predictions (BEFORE the run; graded at the run; a refuted prediction is data, never an error)

- P1: the demand task's seven pinned phases are not all met at the
  0.10 mm class on any seed (the expected honest-failure shape: the
  demand sits three points beyond the derived capacity N = 4;
  recorded, never a gate). REASON: the class is 27.5x tighter than
  the solver's own position gate (0.01 normalized = the 2.75 mm
  class), and the count rule puts the demand unambiguously in the
  search regime.
- P2: control A (the recorded example program, four pinned phases
  = N) qualifies on all three seeds: the recorded feasibility
  witness reproduces and the derivation check's deferred
  at-capacity claim is machine-verified. REASON: the example is the
  engine's own recorded feasible task, run here at its own frozen
  configuration.
- P3: control B (the example program with a fifth pin moved by the
  declared offset, N + 1 = 5 pinned points) shows elevated residual
  at the moved pin or fails to qualify, on at least two of the
  three seeds -- the first-point-beyond-capacity behavior recorded,
  never a gate. REASON: five pinned points exceed capacity 4, and
  the moved pin additionally fights the program's own derivative
  rows.
- P4: the demand task's binding channel (D2) reads
  position-at-pins, not timing-derivative and not between-sample,
  on a majority of seeds (zero derivative windows declared; the
  density sits at the pins). REASON: the demand declares no
  derivative windows, so the pins carry the density.
- GRADING RULES (frozen with the texts in the instrument): P1
  CONFIRMED if no seed meets all seven pins at the class; P2
  CONFIRMED on 3/3 qualified; P3 CONFIRMED if fired on >= 2 seeds;
  P4 CONFIRMED if position_pins binds on >= 2 of 3 seeds; ERROR-only
  seeds read INCONCLUSIVE where declared.

## The run of record (the owner executes every run; nothing auto-runs)

Nine solver runs at the frozen fairness-gate configuration (the
engine's recorded CLI, repo root):

  mechanism-motion jobs/case-d-digest-01/demand_ellipse_7pin.motion.json --seed 580000050 --output runs/case-d-digest-01/demand_ellipse_7pin-580000050.json
  mechanism-motion jobs/case-d-digest-01/demand_ellipse_7pin.motion.json --seed 580000051 --output runs/case-d-digest-01/demand_ellipse_7pin-580000051.json
  mechanism-motion jobs/case-d-digest-01/demand_ellipse_7pin.motion.json --seed 580000052 --output runs/case-d-digest-01/demand_ellipse_7pin-580000052.json
  mechanism-motion jobs/case-d-digest-01/control_a_capacity4.motion.json --seed 580000050 --output runs/case-d-digest-01/control_a_capacity4-580000050.json
  mechanism-motion jobs/case-d-digest-01/control_a_capacity4.motion.json --seed 580000051 --output runs/case-d-digest-01/control_a_capacity4-580000051.json
  mechanism-motion jobs/case-d-digest-01/control_a_capacity4.motion.json --seed 580000052 --output runs/case-d-digest-01/control_a_capacity4-580000052.json
  mechanism-motion jobs/case-d-digest-01/control_b_moved5th.motion.json --seed 580000050 --output runs/case-d-digest-01/control_b_moved5th-580000050.json
  mechanism-motion jobs/case-d-digest-01/control_b_moved5th.motion.json --seed 580000051 --output runs/case-d-digest-01/control_b_moved5th-580000051.json
  mechanism-motion jobs/case-d-digest-01/control_b_moved5th.motion.json --seed 580000052 --output runs/case-d-digest-01/control_b_moved5th-580000052.json

then the instrument, run TWICE with an empty external diff:

  python jobs/case-d-digest-01/case_d_digest_run.py \
    --demand jobs/case-d-digest-01/demand_ellipse_7pin.motion.json \
    --control-a jobs/case-d-digest-01/control_a_capacity4.motion.json \
    --control-b jobs/case-d-digest-01/control_b_moved5th.motion.json \
    --example experimental/motion/examples/normalized-motion.json \
    --result demand=runs/case-d-digest-01/demand_ellipse_7pin-580000050.json \
    --result demand=runs/case-d-digest-01/demand_ellipse_7pin-580000051.json \
    --result demand=runs/case-d-digest-01/demand_ellipse_7pin-580000052.json \
    --result control_a=runs/case-d-digest-01/control_a_capacity4-580000050.json \
    --result control_a=runs/case-d-digest-01/control_a_capacity4-580000051.json \
    --result control_a=runs/case-d-digest-01/control_a_capacity4-580000052.json \
    --result control_b=runs/case-d-digest-01/control_b_moved5th-580000050.json \
    --result control_b=runs/case-d-digest-01/control_b_moved5th-580000051.json \
    --result control_b=runs/case-d-digest-01/control_b_moved5th-580000052.json \
    --source-commit <the merged main 40-hex sha at the run>

## Honest scope of this staging

- Desk arithmetic only: the task artifacts are DERIVED (the
  formulas recorded above), never transcribed; no solver run, no
  corpus touch, no recorded outcome amended; the instrument is
  syntax-compiled and NEVER RUN at staging (no solver results
  exist yet).
- Staging disclosure (the desk validation, honestly recorded): the
  instrument's own fail-closed pins were exercised at the desk
  against the three staged artifacts only -- the s0 contract
  re-checks PASS (demand centroid residual 2.3e-17, diagonal 0;
  control B centroid residual 2.4e-17, diagonal 0), the demand
  program's analytic pins reproduce at all twelve phases (worst
  residual at the 1e-17 level, under the 1e-12 pin), control B's
  similarity-transform residual 5.6e-17 with derivative residual 0,
  and the recomputed actual moved-pin offset reads 0.04999999999999996
  (the desk derivation's 0.04999999999999999 differs in the last
  ulp -- cross-implementation floating point, both recorded; the
  instrument's recomputation at the run is the authoritative one).
- The demand's orientation is program data, never pinned; the
  interval channel is sampled at 96 phases, never certified;
  control B's moved pin carries the original program's derivative
  rows (a recorded inconsistency, part of the declared demand).
- The demand basis (one unit = 275.13632984395207 mm) and the
  example-family basis (no recorded mm mapping) are declared per
  corpus row; cross-basis comparisons are data only. The 0.10 mm
  class tolerance lineage: the recorded packaging tolerance bands
  (case-B scale), worst-case-linear convention, declared with
  lineage at the freeze.
- Nothing here gates D's verdict: the honest-failure shape, the
  control behaviors and the refutation of any prediction are all
  recorded outcomes; the supplier comparison rides at D's
  CAPABILITY/DECISION step, never this failure step.

## Sequencing

Freeze (merged, PR #103) -> derivation check (merged, PR #104) ->
THIS INSTRUMENT -> the owner's run of record -> the outcome appended
to this JOB (additions-only, never rewritten). On this staging's
merge the merge records as its own continuity entry. The owner
executes every run; nothing auto-runs.

## Status

Instrument staged (2026-10-21, branch case-d-digest-01):
additions-only -- the three task artifacts (3,680 + 3,725 + 3,717
bytes), the instrument script (76,316 bytes) and this freeze
record; one new jobs/README.md row. No run claimed, nothing built,
no machine step run at staging beyond the disclosed desk validation
of the pins; no recorded outcome amended; predictions frozen above.
NEXT: the owner's browser merge, then the owner's run of record;
on the run's recording the D line reads its capability step with
the digest's corpus in hand.
