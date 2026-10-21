# OMTS v0.2 Continuous-Path Interval-Channel Vocabulary (Draft)

> **Draft 0.2.0-interval-channel.** This document extends OMTS v0.1
> with the interval-channel semantics proposed for v0.2, for the
> continuous-path-plus-timing demand class. It is a specification draft
> for public review. No adapter in this repository implements these
> fields yet; the current R2.5c adapter continues to reject timing/dwell
> fields under `unsupported_feature_policy: error`.

**Status:** Draft (S1 -- specification draft). Grounded in the recorded
case study D continuous-path-plus-timing record: `jobs/case-d-brief-01`,
`jobs/case-d-derivation-check-01`, `jobs/case-d-digest-01` (the run of
record and the recorded capability verdict, PRs #103-#107).

**Depends on:** OMTS v0.1 (`specs/omts/0.1/specification.md`); consistent
with the v0.2 dwell-duration (`specs/omts/0.2/dwell-duration.md`) and
synchronization (`specs/omts/0.2/synchronization.md`) extensions.

## 1. Purpose: the class, and what v0.1 already says

The continuous-path-plus-timing demand class is a motion demand declared
as a sampled trajectory program: pinned target states on a phase or time
grid, each with tolerances, plus a timing program over the same grid.
v0.1 already expresses the shape:

- Section 9.3 (Occurrence): a target may occur at "one phase", "a phase
  range", "one time", "a time range", or "a free solver-selected
  occurrence."
- Section 9.4 (Tolerances): "Tolerance fields are nonnegative and use
  the document units," including `phase` and `time` tolerances.
- Section 9.5 (Velocity, acceleration, and jerk): "Each may be specified
  by vector, magnitude, direction, or bounds."
- Section 10 (Motion primitives): "Motion primitives express structured
  motion that is not adequately described by isolated target states."
- Section 11 (Path constraints): "Path constraints shape the motion
  between targets."

A recorded precedent ran the shape end to end: the case study C flip
carrier motion task (`jobs/flip-station-sixbar-01`) carried a
twelve-phase sampled trajectory with a C2-class orientation timing
program through the recorded engine's task validation. Time is a spec
unit (section 6 declares `time: s`); this class is
phase-quantified-natively when the document's independent variable is
phase, with the adapter boundary recorded (section 20). This draft adds
no timing vocabulary.

What v0.1 does not say, and this class needs, is what the demand binds
on BETWEEN the declared samples. A sampled program declares finitely
many samples; a realized trace is continuous. The recorded case study D
run of record measured the binding channel of a continuous-path demand
to be between-sample, not position-at-pins: the frozen position-at-pins
prediction P4 was REFUTED on recorded data (seed 580000051 between_sample
1187.2 vs position_pins 1118.5; seed 580000052 tied at 772.394, the
worst between-sample deviation in the phase-7 pin neighborhood). The
interval channel makes those semantics first-class.

## 2. The interval channel

The interval channel is a named demand channel of the
continuous-path-plus-timing class.

1. **Whole-trace binding.** A demand in this class binds over the whole
   trace between and at the declared samples, never only at the declared
   samples. The channel is met by better traces, never by scoring only
   the pins: a candidate that meets every declared sample and deviates
   between them does not meet the demand.

2. **Pin count versus whole trace.** The pin count is a
   demand-declaration artifact; it records how many samples were
   declared, nothing more. The demand's density, and any capability
   verdict against it, bind on the whole trace. The recorded case study
   D datum -- seven pinned phases at 7 = N + k (N = 4, k = 3) at the
   0.10 mm class, with the recorded family covering N = 4 exactly
   (machine-verified, control A 3/3) -- shows a demand beyond capacity
   by density while the family covers its capacity count exactly. No
   pin-count arithmetic substitutes for a whole-trace verdict.

3. **Expressible, not implied.** A declaration in this class pins the
   interval tolerance explicitly. Section 9.4 states the standing rule:
   "A hard target without an explicit tolerance should be treated
   according to the implementation profile; solvers should not assume
   zero tolerance unless documented." The interval channel adds one
   clause to that honesty: an interval demand that is not declared is
   not checked, and an implementation must not report an interval
   verdict for a demand that does not declare one.

4. **Sampled, never certified.** An interval verdict is always a
   sampled verdict. The gate is evaluated on a declared finite sample
   grid between and at the declared samples; a pass on that grid is a
   sampled pass, never a certified continuum claim. The recorded case
   study D instrument evaluated the channel at a declared 8x
   refinement of the native grid (96 samples over the twelve-phase
   cyclic grid), and every verdict it emitted carried the label
   SAMPLED NEVER CERTIFIED. That label is normative in this class.

## 3. Declaration

The interval channel is declared on the task, next to its targets
(intra-task, the layer of the section 9.6 dwell block; open question 1):

```yaml
interval:
  tolerance: 3.634562e-4   # document length units; required, explicit
  refinement: 8            # samples per declared-sample interval
  mode: hard               # section 2.3 modes apply
```

Rules, stated rather than inferred:

- `tolerance` is nonnegative, uses the document units, and is REQUIRED
  for a hard interval demand; there is no default.
- `refinement` is a positive integer: the evaluated grid carries
  `refinement` samples per declared-sample interval of the cyclic or
  one-shot grid (the recorded precedent: 8 per interval, 96 samples
  over the twelve-phase cyclic grid).
- `mode` follows section 2.3 (hard, soft, report-only).
- Every emitted interval result rides with its grid declaration and
  tolerance; an interval result without its grid on the record is not a
  valid result.
- Editing a demand after a recorded run re-runs the demand; recorded
  outcomes are data (the dwell-duration draft's authoring-time
  discipline, unchanged).

## 4. Where the gate lives: validation versus verification

Section 23 states the standing split, verbatim:

> Validation and adaptation use three distinct checks:
>
> 1. **Schema validation** checks required fields, types, enums, and structure.
> 2. **Semantic validation** checks cross-references, vector dimensionality, unit consistency, target ordering, and bounds.
> 3. **Capability checking** determines whether a particular implementation can enforce the requested features. This is performed during adaptation, separately from general document validation.

The interval channel declares its home at each level:

- **Document validation** (schema + semantic) checks structure, units,
  and pinned-sample consistency: the interval block is present when
  claimed, `tolerance` is a nonnegative document-units quantity,
  `refinement` is a positive integer, and the block belongs to a task
  that declares pinned samples. Validation does not evaluate the gate.
  An interval tolerance is a demand that only a realized trace can be
  checked against: per section 23, "A valid document with hard dynamic
  requirements must still be rejected by a kinematic-only adapter. It
  is not an invalid task specification merely because the current
  engine cannot solve it."
- **The interval verdict happens at run/verify**, against per-sample
  emission: the realizing implementation emits its trace per sample
  (position, and where declared orientation, velocity, and acceleration
  per sample, in declared units), and the gate is evaluated on that
  emission over the declared grid. The interval tolerance is
  demand-side; its checking is trace-side -- the demand/realization
  split of `synchronization.offset_realization` and the target-layer
  `dwell_realization` record applied as the structural template, with
  the draft stating both sides.
- **The adapter boundary, stated honestly** (the S-staging-note
  pattern): no adapter in this repository implements these fields
  today. The current R2.5c adapter rejects timing/dwell under
  `unsupported_feature_policy: error` (section 20: "Fixed-only search,
  custom geometry bounds, per-target unequal position tolerances,
  custom objective weights, partial/spatial orientation, timing/dwell,
  dynamics, collision, synchronization, and higher validation levels
  are rejected."), and "Passing general OMTS validation does not imply
  acceptance by this adapter." The recorded native instrument is the
  experimental six-bar motion engine's per-sample emission (PR-B:
  positions, velocities, and accelerations emitted per sample under
  explicit unit declarations), consumed unmodified by the case study D
  failure digest (instrument modification count 0 at the run of
  record).
- **Scope, one line:** the demand class is gradeable by existing
  recorded instruments (per-sample emission plus a fail-closed digest
  over the emitted trace). This draft claims nothing about suppliers;
  no supplier question appears in it.

## 5. Versioning and grounding

Section 4 states the versioning rule, verbatim: "patch changes clarify
text or repair schema defects without changing meaning; minor changes
add backward-compatible fields or capabilities; major changes may alter
field meaning or compatibility." This draft is additive: it adds the
interval block and its semantics, changes no existing field's meaning,
and leaves v0.1 documents without the block validating unchanged. Any
future change that alters the meaning of existing vocabulary is a
major-version change, never a silent clarification.

Grounding splits by what the record measures. The whole-trace gate
semantics land as vocabulary now because a run measured them: the case
study D run of record confirmed P1/P2/P3 (pins unmet; the N = 4
at-capacity witness machine-verified; the N + 1 elevated-residual
behavior) and refuted P4 (position-at-pins binding) on recorded data.
The capability verdict is recorded scoped: the family covers N = 4
pinned phases exactly, the demand's density binds beyond, and the
seven-pin demand stands unsolved by the recorded family -- recorded as
data, never as a family verdict. Nothing anticipatory lands here: no
claim is made about which families can meet interval demands; the
shape-reachability question stays open; family extensions are governed
by their own declared triggers, never by reinterpretation.

## 6. Worked example: the recorded case study D digits

The recorded demand
(`jobs/case-d-digest-01/demand_ellipse_7pin.motion.json`) is a
twelve-phase sampled trajectory on the case-B 260 x 90 mm bounding-box
ellipse loop in normalized length units (the scale that puts the
bounding box at semi-axes 0.4724930367201291 x 0.16355528194158314, so
the 0.10 mm class is 3.634562e-4), with per-sample position, velocity,
and acceleration tables (the C2-class timing program; zero declared
derivative windows -- the scored channels were position at pins, the
interval channel, and density), and seven pinned phases at 7 = N + k
(N = 4, k = 3; the derivation check's derived count, never a picked
number). Declared in the vocabulary of this draft, its form (the first
recorded pinned phase shown; the staged artifact carries the full
program):

```yaml
spec: open-mechanism-task
version: 0.1.0
task_set_id: case_d_ellipse_carry
units:
  length: normalized
  angle: deg
  time: s
coordinate_system:
  frame_id: world
  dimension: 2
tasks:
  - id: ellipse_carry
    motion:
      mode: cyclic
      order_policy: fixed_timing
      cycle:
        period: 360
        independent_variable: phase
    targets:
      - id: pin_1
        position: [0.4724930367201291, 0.0]
        orientation:
          type: planar_angle
          value: 90
        occurrence:
          phase: 0
        tolerance:
          position: 3.634562e-4
      # ... six further pinned phases on the same twelve-phase grid;
      # the recorded program carries the per-sample q/v/a tables (the
      # C2-class timing program, the orientation column following the
      # path tangent) ...
    interval:
      tolerance: 3.634562e-4
      refinement: 8
      mode: hard
```

The recorded outcome, stated honestly and never as a family verdict:
at the run of record the seven pinned phases were not met on any
graded seed (worst pin residuals 0.407 and 0.281 vs the class), the
interval channel failed alongside (worst between-sample deviations
0.432 and 0.281 on the 96-sample 8x grid), the binding channel
measured between-sample, and the recorded family covers N = 4 pinned
phases exactly (control A qualified 3/3 at 150/200 evaluations, worst
0.001 vs the solver's own 0.01 gate; control B, the N + 1 probe,
failed 3/3 with the elevated moved-pin residual 0.035 vs unmoved
0.011). The demand stands unsolved at seven pins by the recorded
family; the scoped verdict, the refuted prediction, and the corpus are
recorded data (`jobs/case-d-digest-01/JOB.md`, the capability verdict
section).

## 7. Implementation staging

1. **S1 -- Specification draft.** This document.
2. **S2 -- Document validation.** (future) `omts validate` accepts the
   task-level `interval` block with the section 3 rules: tolerance
   present and nonnegative for hard mode, refinement a positive
   integer, the block on a task that declares pinned samples.
3. **S3 -- Interval evaluation.** (future) interval gate evaluation
   against per-sample emission on the declared grid, with
   sampled-honesty reporting: the grid, the tolerance, and the
   SAMPLED NEVER CERTIFIED label riding every verdict.

## 8. Open questions for review

1. Should the interval block sit at task level or document level?
   (This draft: task level, next to the targets it names -- the
   dwell precedent, intra-task demands stay intra-task.)
2. Should `refinement` be declared or left to the implementation
   profile? (This draft: declared -- a sampled verdict without its
   grid on the record is not an honest verdict.)
3. Should the pin-count-versus-density distinction carry into
   capability manifests? (This draft: no manifest change proposed;
   the distinction is demand-side semantics.)
4. Is the sampled-never-certified label normative vocabulary or
   adapter guidance? (This draft: normative in this class -- an
   interval verdict is always a sampled verdict.)
