# Open Mechanism Task Specification (OMTS) v0.1

> **Draft 0.1.0 — repository foundation.** The normative schema is packaged at
> `src/mechanism_generator/omts/schema.json` with identifier `urn:mechanismo-ai:omts:0.1.0`.
> This specification describes future capabilities as well as present ones. The
> [adapter profile](../../../docs/r25c-adapter.md) defines the smaller implemented subset.
> The engine and model weights are not included in this foundation release.


**Status:** Draft for implementation and public review

**Canonical version string:** `0.1.0`

**Canonical document type:** `open-mechanism-task`
**Recommended file extensions:** `.omts.yaml`, `.omts.yml`, or `.omts.json`

## 1. Purpose

The Open Mechanism Task Specification defines a portable, machine-readable way to describe **what motion a machine must perform** without prematurely deciding **how the machine must perform it**.

An OMTS document can describe:

- target positions and orientations;
- ordered or unordered target states;
- cyclic or one-shot motion;
- dwell and oscillatory motion;
- target velocity, acceleration, and jerk;
- payloads and applied loads;
- workspace and keep-out geometry;
- allowed mechanism families and actuator count;
- path accuracy, transmission, assembly, compactness, and robustness requirements;
- multiple synchronized tasks sharing a common cycle or master shaft;
- requested outputs and validation level.

The intended workflow is:

```text
motion requirement
    -> mechanism proposal or topology search
    -> local refinement
    -> physics and qualification checks
    -> Pareto-ranked candidate portfolio
    -> CAD, simulation, and downstream engineering
```

OMTS is a **task contract**, not a mechanism file and not a safety certificate. It describes required motion and design constraints. A solver returns candidate mechanisms and a clear statement of which requirements were evaluated, passed, approximated, or unsupported.

## 2. Design principles

### 2.1 Task first, topology second

A designer should be able to specify the desired operation before choosing a four-bar, six-bar, cam, slider-crank, parallel mechanism, or robot.

### 2.2 Explicit units and coordinate frames

Every document declares its units and coordinate frame. Solvers must not guess whether a coordinate is in millimeters, inches, or normalized units.

### 2.3 Hard, soft, and report-only requirements

A requirement may be:

- `hard`: a candidate is unacceptable if the requirement fails;
- `soft`: the solver should improve the requirement and may trade it against other objectives;
- `report_only`: calculate and report the metric without using it to reject or optimize a candidate.

### 2.4 No silent feature loss

An implementation must declare its supported capabilities. Unsupported requirements must be handled according to `unsupported_feature_policy`, which should normally be `error`.

### 2.5 Portfolios instead of a single opaque answer

The default output should be a set of distinct Pareto candidates, such as:

- best path accuracy;
- best target transmission;
- best full-cycle conditioning;
- most compact;
- best assembly margin;
- lowest estimated energy or torque.

### 2.6 Qualification is layered

A candidate should be labeled by the level of analysis actually performed:

1. `kinematic_candidate`
2. `mechanically_screened`
3. `dynamically_evaluated`
4. `structurally_evaluated`
5. `prototype_validated`

A kinematically valid linkage must not be presented as a structurally certified machine.

## 3. Normative language

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

- A compliant OMTS v0.1 document **MUST** validate against the v0.1 JSON Schema.
- A solver **MUST** report unsupported capabilities.
- A solver **MUST NOT** silently ignore a hard constraint.
- A solver **SHOULD** preserve candidate lineage and qualification metrics.
- A solver **MAY** support extensions beyond v0.1.

## 4. Serialization and versioning

OMTS v0.1 uses a data model that can be serialized as YAML or JSON.

Every document begins with:

```yaml
spec: open-mechanism-task
version: 0.1.0
task_set_id: example_task_set
```

Versioning follows semantic intent:

- patch changes clarify text or repair schema defects without changing meaning;
- minor changes add backward-compatible fields or capabilities;
- major changes may alter field meaning or compatibility.

A v0.1 implementation should accept `0.1` and `0.1.0` as equivalent version identifiers.

## 5. Top-level object

| Field | Required | Purpose |
|---|---:|---|
| `spec` | yes | Must equal `open-mechanism-task`. |
| `version` | yes | OMTS version. |
| `task_set_id` | yes | Stable identifier for the document. |
| `name` | no | Human-readable title. |
| `description` | no | Human-readable purpose and context. |
| `capabilities_required` | no | Features an implementation must support. |
| `unsupported_feature_policy` | no | `error`, `warn`, or `ignore`; default should be `error`. |
| `units` | yes | Global unit system. |
| `coordinate_system` | yes | Shared frame and dimensionality. |
| `payloads` | no | Reusable payload definitions. |
| `load_cases` | no | Reusable force and moment definitions. |
| `tasks` | yes | One or more motion tasks. |
| `synchronization` | no | Relationships between tasks. |
| `outputs` | no | Requested candidate and export behavior. |
| `metadata` | no | Author, license, provenance, tags, and notes. |
| `extensions` | no | Namespaced experimental fields. |

## 6. Units

The top-level `units` object applies throughout the document unless a future extension explicitly overrides it.

Example:

```yaml
units:
  length: mm
  angle: deg
  time: s
  mass: kg
  force: N
  torque: N_m
```

For abstract or scale-free experiments, `length: normalized` is permitted. A normalized task should define how it will later be scaled for physical use.

Derived units are implied unless explicitly supplied:

- linear velocity: length / time;
- linear acceleration: length / time²;
- jerk: length / time³;
- angular velocity: angle / time;
- angular acceleration: angle / time².

## 7. Coordinate system

The coordinate system defines a shared frame for all tasks, payloads, loads, and obstacles.

```yaml
coordinate_system:
  frame_id: world
  dimension: 2
  handedness: right
  axes:
    x: right
    y: up
  origin_description: Lower-left corner of the machine base.
  gravity: [0.0, -9.80665]
```

The `dimension` is either 2 or 3. A solver must verify that vector lengths match the supported dimensionality. The v0.1 schema permits two- or three-element vectors so that a single schema can represent planar and spatial work; implementation-level validation should enforce internal consistency.

## 8. Tasks

Each task describes one end-effector or controlled output motion.

```yaml
tasks:
  - id: transfer_arm
    name: Pick-transfer-place motion
    motion: ...
    mechanism_search: ...
    requirements: ...
    workspace: ...
    actuation: ...
    search: ...
```

A task does not have to correspond to one physical mechanism. A multi-topology solver may decide that the task is best implemented by a linkage, cam, compound mechanism, or small multi-actuator system.

### 8.1 Motion mode

`motion.mode` is:

- `cyclic`: repeats continuously or on demand;
- `one_shot`: runs from a defined start to finish without assuming periodic closure.

### 8.2 Order policy

`motion.order_policy` is:

- `unordered`: targets may be reached at any phases;
- `ordered`: targets must occur in listed order, or increasing `order_index` order when every target supplies a unique index; exact timing may be free;
- `fixed_timing`: targets contain fixed phases, times, or allowable windows.

This distinction is important. Unordered point synthesis is useful for early geometry research, but real machine operations usually require ordered or timed target states.

### 8.3 Cycle

A cyclic task may define:

```yaml
cycle:
  period: 1.2
  phase_start: 0
  phase_end: 360
  direction: positive
  independent_variable: phase
  input_speed: 300
```

The independent variable is either `phase` or `time`. If `period` is omitted, a kinematic solver may treat the task as geometry-only.

## 9. Target states

A target state defines a required end-effector condition.

```yaml
- id: pickup
  position: [120.0, 70.0]
  orientation:
    type: planar_angle
    value: 0
  occurrence:
    phase: 70
    order_index: 0
  tolerance:
    position: 0.5
    orientation: 2
  velocity:
    magnitude: 0
    mode: hard
  payload_ref: workpiece
  load_case_ref: loaded_transfer
  mode: hard
```

### 9.1 Position

`position` is a two- or three-element vector in the declared length unit.

### 9.2 Orientation

OMTS v0.1 supports:

- `planar_angle`;
- `quaternion_wxyz`;
- `euler_xyz`.

A planar solver should accept only `planar_angle` and reject unsupported spatial orientation requirements.

### 9.3 Occurrence

A target may occur at:

- one phase;
- a phase range;
- one time;
- a time range;
- a free solver-selected occurrence.

Examples:

```yaml
occurrence:
  free: true
```

```yaml
occurrence:
  phase_range: [120, 150]
  order_index: 1
```

```yaml
occurrence:
  time: 0.42
```

### 9.4 Tolerances

Tolerance fields are nonnegative and use the document units.

```yaml
tolerance:
  position: 0.5
  orientation: 2
  phase: 1
  time: 0.01
  velocity: 10
  acceleration: 100
```

A hard target without an explicit tolerance should be treated according to the implementation profile; solvers should not assume zero tolerance unless documented.

### 9.5 Velocity, acceleration, and jerk

Each may be specified by vector, magnitude, direction, or bounds.

```yaml
velocity:
  magnitude: 500
  direction_angle: 0
  mode: soft
  weight: 1.0
```

```yaml
acceleration:
  max_magnitude: 4000
  mode: hard
```

The solver should distinguish geometry-dependent derivatives from the input drive law. For a one-degree-of-freedom mechanism:

```text
end-effector velocity = dP/dtheta * theta_dot
end-effector acceleration = d2P/dtheta2 * theta_dot^2
                            + dP/dtheta * theta_ddot
```

### 9.6 Dwell

A dwell can be defined by duration or phase span.

```yaml
dwell:
  phase_span: 25
  max_position_drift: 0.35
  max_orientation_drift: 1.5
  mode: hard
```

A dwell is not merely a low-speed point. It is a bounded interval over which the output remains within a specified neighborhood.

## 10. Motion primitives

Motion primitives express structured motion that is not adequately described by isolated target states.

Supported v0.1 primitive types are:

- `dwell`;
- `oscillation`;
- `linear_move`;
- `rotary_move`;
- `custom`.

Example oscillation:

```yaml
primitives:
  - id: settle_shake
    type: oscillation
    target_ref: process_dwell
    window:
      phase_range: [158, 178]
    axis: [1.0, 0.0]
    amplitude: 2.0
    frequency: 6.0
    cycles: 3
    waveform: sine
    mode: soft
```

This can represent shaking, agitation, vibration-assisted release, or small settling motions. A solver may implement the primitive with the main mechanism, a secondary mechanism, a cam, or an auxiliary actuator.

## 11. Path constraints and workspace

Path constraints shape the motion between targets. Workspace constraints define where the mechanism and end effector may exist.

Examples include:

- keep-in boxes or polygons;
- keep-out boxes or polygons;
- path corridors;
- maximum curvature;
- maximum path length;
- minimum obstacle clearance.

```yaml
path_constraints:
  - id: avoid_press
    type: keep_out_box
    min: [285.0, 0.0]
    max: [345.0, 120.0]
    mode: hard
```

```yaml
workspace:
  envelope_min: [90.0, 20.0]
  envelope_max: [450.0, 260.0]
  minimum_clearance: 10
```

Collision-free claims require an implementation that evaluates the mechanism links and moving bodies, not only the end-effector point.

## 12. Payloads and load cases

Payloads and load cases are reusable top-level objects.

```yaml
payloads:
  - id: workpiece
    mass: 0.25
    center_of_mass: [0.0, 0.0]
```

```yaml
load_cases:
  - id: transfer_loaded
    payload_ref: workpiece
    force: [0.0, -2.45]
    duty_fraction: 0.35
    mode: hard
```

Target states refer to them with `payload_ref` and `load_case_ref`.

In v0.1, these fields define the task contract even when a kinematic-only solver cannot evaluate them. A kinematic solver must report them as unsupported rather than declaring dynamic or structural suitability.

## 13. Mechanism search space

The `mechanism_search` object describes allowed implementation families and search freedoms.

```yaml
mechanism_search:
  allowed_topologies:
    - four_bar
    - watt_six_bar
    - stephenson_six_bar
  max_dof: 1
  max_actuators: 1
  ground_link: ...
  assembly_branches: [open, crossed]
  profiles: [accuracy, balanced, transmission, compactness]
  profile_matrix: cross
```

### 13.1 Allowed topologies

OMTS v0.1 enumerates common mechanism-family identifiers but also permits `custom`. An implementation should publish its own topology capability list.

### 13.2 Ground-link strategy

Ground-link strategy is:

- `fixed`;
- `optimize`;
- `portfolio`.

Examples:

```yaml
ground_link:
  mode: fixed
  value: 6
```

```yaml
ground_link:
  mode: optimize
  bounds: [3, 18]
  initial_value: 6
```

```yaml
ground_link:
  mode: portfolio
  fixed_values: [6]
  variable_bounds: [3, 18]
  trust_fraction: 0.25
  release: true
```

The portfolio mode is intended for nonconvex inverse-design problems where fixed and variable searches may find complementary solution families.

### 13.3 Assembly branches

For mechanisms with multiple closure branches, `assembly_branches` lists the permitted branches. The abstract names are `open` and `crossed`. An implementation may map these to its internal branch-sign convention.

### 13.4 Profiles and profile matrix

Profiles declare desired local objectives:

- `accuracy`;
- `balanced`;
- `transmission`;
- `compactness`;
- `energy`;
- `custom`.

`profile_matrix: cross` requests that every proposal source be refined under every listed profile. `paired` allows an implementation to match each proposal source to a preferred profile.

## 14. Requirements and qualification

### 14.1 Path

```yaml
path:
  max_mean_error: 0.05
  max_point_error: 0.075
  shared_mean_allowance: 0.02
  shared_point_allowance: 0.05
  mode: hard
```

The shared allowances are useful in multi-start local refinement. They allow all candidates to be judged relative to one common best-path reference rather than allowing each poor start to define its own permissive budget.

### 14.2 Transmission

```yaml
transmission:
  selection_min_at_targets: 15
  selection_min_global: 10
  min_at_targets: 35
  min_global: 15
  objective: worst_target
  mode: soft
```

This distinguishes:

- practical selection floors used to retain promising research candidates;
- preferred engineering goals used for stronger qualification.

The acute-equivalent transmission angle is typically reported in the range 0 to 90 degrees.

### 14.3 Assembly

```yaml
assembly:
  full_cycle_required: true
  min_margin: 0
  mode: hard
```

For a crank-rocker intended to rotate continuously, full-cycle assembly should normally be hard.

### 14.4 Classification

```yaml
classification:
  grashof_required: true
  input_link_shortest: true
  follower_not_longest: false
  mode: hard
```

Topology-specific rules belong here. The optional follower-not-longest rule is separate because it is not universally required and may unnecessarily constrain the design space.

### 14.5 Compactness

```yaml
compactness:
  max_link_ratio: 2.0
  max_sweep_radius_ratio: 2.75
  mode: soft
  weight: 0.25
```

Ratios are normally defined against a task scale such as the maximum pairwise target separation. A solver must report the exact normalization used.

### 14.6 Dynamics

```yaml
dynamics:
  max_speed: 900
  max_acceleration: 6000
  max_jerk: 60000
  cycle_time: 1.2
  mode: hard
```

Dynamic qualification requires a time or phase-speed law. A geometry-only solver cannot claim compliance.

### 14.7 Robustness

```yaml
robustness:
  parameter_tolerance_fraction: 0.002
  monte_carlo_samples: 200
  minimum_pass_fraction: 0.99
  mode: hard
```

This supports tolerance-aware and manufacturing-robust synthesis.

## 15. Actuation

The actuation object describes the expected input form.

```yaml
actuation:
  input_type: shared_master
  master_id: line_shaft
  phase_offset: 40
  nominal_speed: 300
```

Allowed input types include rotary, linear, shared master, manual, and custom.

The actuation specification is intentionally separate from mechanism topology. A four-bar, cam, or six-bar may all be driven from the same master shaft.

## 16. Synchronization

The top-level `synchronization` object coordinates multiple tasks.

```yaml
synchronization:
  master_cycle_id: line_shaft
  period: 1.2
  shared_input: true
  events:
    - id: process_handoff
      participants: [transfer, clamp]
      phase_range: [145, 155]
      tolerance: 2
      mode: hard
  phase_relations:
    - from_task: transfer
      to_task: clamp
      offset: 60
      tolerance: 2
      mode: hard
```

This is the foundation for synchronized manufacturing-line synthesis. A future solver can optimize several mechanisms and their phase offsets together while checking handoffs, dwell overlap, and collision timing.

## 17. Search controls

The task-level `search` object contains reproducibility and computation-budget settings.

```yaml
search:
  implementation_profile: r2.5c-fourbar
  seed: 101
  top_k: 5
  perturbations_per_model: 0
  parameter_noise: 0.18
  phase_noise: 4
  time_budget_seconds: 120
  candidate_budget: 50
```

These fields guide an implementation but do not change the physical meaning of the task.

## 18. Requested outputs

The top-level `outputs` object describes desired result behavior.

```yaml
outputs:
  top_k: 5
  pareto_objectives:
    - path_error
    - target_transmission
    - global_transmission
    - compactness
  formats: [json, csv, npz, png]
  include_lineage: true
  include_histories: false
  requested_validation_level: mechanically_screened
```

A solver may return fewer candidates if insufficient qualified solutions exist, but it must say so explicitly.

## 19. Capability negotiation

An implementation should publish a capability manifest. Example:

```yaml
implementation: r2.5c-fourbar
supports:
  - planar_2d
  - cyclic_motion
  - exactly_three_targets
  - unordered_targets
  - ordered_targets
  - target_positions
  - target_orientation
  - four_bar
  - fixed_ground_link
  - variable_ground_link
  - hybrid_ground_link_portfolio
  - open_and_crossed_branches
  - path_error
  - transmission_angle
  - full_cycle_assembly
  - grashof
  - compactness_metrics
```

When an OMTS file requires capabilities outside that list, the implementation should follow `unsupported_feature_policy`.

Recommended behavior:

- `error`: stop before synthesis and list unsupported fields;
- `warn`: continue only if unsupported requirements are not hard, and include warnings in every result;
- `ignore`: only permits omission of non-hard unsupported features with explicit disclosure; it never authorizes silently dropping hard constraints. The foundation adapter accepts only `error`.

## 20. Current R2.5c adapter profile

The packaged adapter prepares independent three-target planar cyclic four-bar tasks
for the packaged, version-identified R2.5c research engine. It supports positions
alone or positions with planar orientations on all three targets, ordered/free
target phases, hybrid ground search, common hard path ceilings, soft transmission
goals, and report-only compactness. It only accepts normalized length units,
degrees, and a positive 0–360 degree cycle. It never performs synthesis itself.

For this implementation, each target tool frame is located at output point P,
with positive x directed from coupler joint A (on the input crank) toward joint B
(on the output rocker). Orientation is the counterclockwise angle from world +x
in the right-handed XY frame. There is no adjustable tool mounting angle. All
three targets must use `orientation.type: planar_angle`, or all must omit
orientation. Individual `tolerance.orientation` values may differ and default
to 5 degrees when omitted; each must be finite, greater than zero and below
180 degrees. The engine uses the shortest circular angular difference, at the
same optimized phase used to evaluate that target's position. An angular
tolerance without a target orientation is rejected. Reordering by `order_index`
preserves the pairing of position, orientation, tolerance and target ID.

The orientation constraints apply only at the three targets. They do not enforce
orientation during the intervening trajectory, timing or dwell, and a prepared
pose plan does not establish that an eligible mechanism exists.

The [exact profile](../../../docs/r25c-adapter.md) documents defaults, mapped fields,
rejections, the artifact identity contract, and known research-engine limitations.
The machine-readable manifest is `src/mechanism_generator/omts/r25c_capabilities.json`.
Passing general OMTS validation does not imply acceptance by this adapter.

Fixed-only search, custom geometry bounds, per-target unequal position tolerances,
custom objective weights, partial/spatial orientation, timing/dwell, dynamics, collision, synchronization,
and higher validation levels are rejected. A future adapter can support them
without reducing the broader specification.

## 21. Result contract

A conforming solver result should include, where applicable:

- input task-set ID and task ID;
- OMTS version;
- solver and model versions;
- seed and configuration;
- candidate ID and lineage;
- topology and mechanism parameters;
- target occurrence phases or times;
- target errors;
- target and global transmission metrics;
- assembly and classification results;
- compactness and workspace metrics;
- qualification level;
- supported and unsupported requirements;
- reasons for rejection;
- Pareto rank or selection rationale;
- artifact paths and checksums.

The result should distinguish:

- physical feasibility;
- path acceptability;
- practical selection eligibility;
- preferred engineering acceptability;
- achieved validation level.

## 22. Extensions

Experimental fields belong under an `extensions` object. Extension keys should use a namespace-like prefix to reduce collisions.

```yaml
extensions:
  org.example.thermal_environment:
    ambient_temperature: 80
    washdown_required: true
```

A future OMTS version may standardize widely used extensions.

## 23. Validation

The normative machine-readable schema is:

```text
src/mechanism_generator/omts/schema.json
```

Validation and adaptation use three distinct checks:

1. **Schema validation** checks required fields, types, enums, and structure.
2. **Semantic validation** checks cross-references, vector dimensionality, unit consistency, target ordering, and bounds.
3. **Capability checking** determines whether a particular implementation can enforce the requested features. This is performed during adaptation, separately from general document validation.

Examples of semantic errors that the JSON Schema alone may not catch:

- a 3D target in a 2D coordinate system;
- a target referencing an unknown payload;
- a phase range whose lower bound exceeds its upper bound;
- duplicate task IDs;
- a fixed ground-link value outside declared bounds;
- synchronization referencing an unknown task.

A valid document with hard dynamic requirements must still be rejected by a
kinematic-only adapter. It is not an invalid task specification merely because the
current engine cannot solve it.

## 24. v0.1 non-goals

OMTS v0.1 does not standardize:

- CAD geometry representation;
- finite-element models;
- material databases;
- joint-clearance or lubrication models;
- machine-safety certification;
- controls source code;
- PLC or robot program formats;
- a universal objective-weighting system;
- a universal mechanism topology ontology.

Those may be added through extensions or future versions.

## 25. Planned v0.2 topics

Likely v0.2 work includes:

- richer 2D and 3D orientation constraints;
- explicit drive-law and spline definitions;
- richer velocity, acceleration, and jerk profiles;
- standard collision-body geometry;
- topology plugin manifests;
- multi-mechanism synchronized optimization;
- standardized solver capability manifests;
- standardized result schemas;
- CAD and manufacturing export references;
- uncertainty and robustness distributions;
- dataset records for one-to-many generative training.

## 26. Minimal example

```yaml
spec: open-mechanism-task
version: 0.1.0
task_set_id: demo_three_point_four_bar
units:
  length: normalized
  angle: deg
  time: s
coordinate_system:
  frame_id: world
  dimension: 2
  handedness: right
tasks:
  - id: path_001
    motion:
      mode: cyclic
      order_policy: unordered
      targets:
        - id: T1
          position: [-6.0, 2.0]
          occurrence: {free: true}
        - id: T2
          position: [-2.0, 6.0]
          occurrence: {free: true}
        - id: T3
          position: [0.5, 3.5]
          occurrence: {free: true}
    mechanism_search:
      allowed_topologies: [four_bar]
      max_dof: 1
      max_actuators: 1
      ground_link:
        mode: portfolio
        fixed_values: [6.0]
        release: true
      assembly_branches: [open, crossed]
      profiles: [accuracy, balanced, transmission]
      profile_matrix: cross
    requirements:
      path:
        max_mean_error: 0.05
        max_point_error: 0.075
        mode: hard
      transmission:
        min_at_targets: 35
        min_global: 15
        objective: worst_target
        mode: soft
      assembly:
        full_cycle_required: true
        mode: hard
```

The compatible three-point example and the illustrative synchronized-line example are in `examples/omts/`. The latter passes document validation but is rejected by the adapter.

## Foundation validation clarifications

- JSON and YAML are accepted; duplicate mapping keys, non-finite numbers, non-string
  keys and cyclic aliases are rejected. YAML metadata dates are retained as strings.
- IDs must be unique within each collection. Target, payload, load-case, and task
  references are checked. Vectors follow the declared dimension.
- Ordered indices, when present, must be unique and supplied on every target.
  They cannot accompany `unordered`. Fixed timing requires a phase/time or window,
  not `free: true`.
- Bounds must be ordered; link-length bounds must be positive. A ground initial
  value must lie inside its bounds. Acute transmission limits use the declared
  angle units (90 degrees or pi/2 radians maximum).
- Target mode defaults to hard. JSON Schema defaults are documentation; validation
  does not mutate a document to insert them. An adapter must document its defaults.
- Schema and semantic validation describe the document. Capability checking is a
  separate step. Neither checks feasibility, certifies a machine, or solves motion.
- OMTS draft version `0.1` is accepted as an alias of `0.1.0`.

### Cycle direction clarification

The draft cycle direction vocabulary includes `positive` (increasing phase),
`negative` (decreasing phase), `either` (either constant direction is acceptable),
and `bidirectional` (direction reversal is permitted within the cycle). An adapter
must reject unsupported choices. The R2.5c adapter supports the first three;
it does not implement reversal within a cycle. Physical phases refer to targets
in their declared occurrence order, independently of input rotation direction.
