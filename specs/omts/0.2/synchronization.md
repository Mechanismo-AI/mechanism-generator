# OMTS v0.2 Synchronization Extension (Draft)

> **Draft 0.2.0-synchronization.** This document extends OMTS v0.1 section 16
> with the synchronization model proposed for v0.2. It is a specification draft
> for public review. No adapter in this repository implements these fields yet;
> the current R2.5c adapter continues to reject synchronization fields under
> `unsupported_feature_policy: error`.

**Status:** Draft; S2 (document validation), S3 (composed run plans), and S4
(timeline verification) are implemented for the preparable subset described
below, together with the anchor-probe diagnostic and applied master-phase
offsets (first S5 steps). Full S5 joint search is future work.

**Depends on:** OMTS v0.1 (`specs/omts/0.1/specification.md`)

## 1. Purpose

v0.1 synchronization can state that several tasks share a master cycle with
fixed pairwise phase offsets. It cannot state the relationships a real
automation brief contains: ratioed mechanisms (a Geneva indexing every fourth
cycle), free or bounded lead/lag between events, dwell containment, payload
handoffs, or temporal keep-out between mechanisms. This extension defines a
synchronization model that can express those relationships while preserving the
v0.1 principles: explicit units, no silent feature loss, and capability checking
separate from document validation.

## 2. Task cycle anchoring

Each task may declare what its phase zero is.

`yaml
motion:
  cycle:
    period: 1.2
    phase_reference: pick   # target id in the same task
`

`phase_reference` names a target whose occurrence defines that task's phase
zero. If omitted, phase zero is the master's phase zero, as in v0.1.

### Applied master-phase offsets (S5 v0.1)

`synchronization.applied_offsets` declares a task's master-phase offset — the
physical phasing of its input relative to the master shaft (a gear-tooth or
crank set-screw choice), as a unit-quantified value per task:

`yaml
synchronization:
  applied_offsets:
    catcher: {phase: 25}
`

A positive offset rotates the task's events later in the master cycle. For an
anchored task, the offset moves its `phase_reference` target to the stated
phase, deliberately relaxing the composed-timeline rule; for an unanchored
task, it rotates its raw phases. Documents validate with declared offsets, the
adapter records them in the plan line section, and the timeline verifier
composes with them — so a line can be legitimately verified under a declared
phasing. The declared phasing is part of the build contract: a verified line is
as-built only if the physical build realizes the offsets. The anchor probe
(`--probe-anchors`) reports feasible offset intervals; `applied_offsets` is
how a probe-chosen offset becomes first-class rather than diagnostic.

### Physical realization record (v0.2)

`synchronization.offset_realization` records how each declared offset is
physically realized — the build fact behind the phase number:

`yaml
synchronization:
  applied_offsets:
    catcher: {phase: 25}
  offset_realization:
    catcher:
      method: gear_train        # crank_phase | gear_train | coupling | other
      detail: 60:12 spur pair, tooth index 7
`

Each entry names a task that declares an `applied_offsets` entry (there is
nothing to realize otherwise) and carries a `method` from the fixed enum plus
an optional free-form `detail` (gear ratio and tooth index, crank keyway
angle, coupling orientation). The record is a build note, not a verification
input: the verifier checks composed phases, not hardware. Verification under
declared offsets is sufficient for v0.2, and a missing realization record
never blocks or downgrades a `verified` verdict — but the gap is surfaced
visibly: the adapter copies `offset_realization` into the plan line section,
and `line_result.json` echoes an `offset_realization` summary
(`recorded`, per-task records, and `unrecorded_tasks` when any declared
offset lacks a realization) so a reviewer can see whether the as-built record
exists before trusting the line as a build contract.

## 3. Ratioed participation

`yaml
synchronization:
  master_cycle_id: line_shaft
  period: 1.2
  participants:
    - task: transfer          # default ratio [1, 1]
    - task: indexer
      ratio: [1, 4]           # one indexer cycle per four master cycles
    - task: feeder
      ratio: [2, 1]           # two feeder cycles per master cycle
`

`ratio` is `[numerator, denominator]` — task cycles per master cycles —
and both entries must be positive integers. Relations that reference a ratioed
task may carry `occurrence_index` (0-based within one master cycle); omitted
means the relation applies to every occurrence.

## 4. Quantities are never bare numbers

All synchronization offsets, tolerances, windows, and margins are objects:

`yaml
offset: {phase: 60}
tolerance: {phase: 2}
`

`phase` is in the document angle unit; `time` is in the document time unit.
Adapters must reject bare numeric values. The sign convention is fixed: an
`offset` is the phase of the referenced event measured from the referencing
event, positive in the cycle direction.

## 5. Events

A task exposes named events:

- `<task>.<target_id>.reached` — a point event at the target occurrence;
- `<task>.<target_id>.dwell` — the window event where the target declares a dwell;
- handoff and region events declared under `synchronization.events`.

`yaml
events:
  - id: part_handoff
    type: handoff          # co_active | handoff | co_location
    participants: [transfer.place.reached, clamp.grasp.reached]
    window: {phase_range: [145, 155]}
    tolerance: {phase: 2}
    payload_ref: workpiece
    mode: hard
`

`handoff` declares the payload being transferred and implies co-location and
co-timing. Kinematic adapters report handoff as unsupported; the contract
states the physical intent and capability checking decides who can enforce it.

## 6. Relations

`relations` replaces v0.1 `phase_relations`, which is deprecated in 0.2
and removed in 1.0. Relations connect events, not tasks.

`yaml
relations:
  - id: transfer_leads_clamp
    from: transfer.pick.reached
    to: clamp.closed.reached
    type: fixed_offset
    offset: {phase: 60}
    tolerance: {phase: 2}
    mode: hard

  - id: clamp_before_press
    from: clamp.closed.reached
    to: press.land.reached
    type: ordering
    min_lead: {phase: 15}
    max_lead: {phase: 90}
    mode: hard

  - id: clamp_holds_during_weld
    from: weld.target.dwell
    to: clamp.closed.dwell
    type: contains
    margin: {phase: 5}
    mode: hard

  - id: sweep_clearance
    from: transfer.enters_north.reached
    to: press.in_north.dwell
    type: disjoint_windows
    clearance: {phase: 3}
    mode: hard
`

- `fixed_offset`: the `to` event must occur at `offset` after the `from`
  event, within `tolerance`.
- `ordering`: the `to` event must lead or lag the `from` event by between
  `min_lead` and `max_lead`; the exact value is a free design variable.
- `contains`: the `from` window must fully contain the `to` window with
  at least `margin` on both sides.
- `disjoint_windows`: the two windows must not overlap, with at least
  `clearance` between them.

## 7. Semantic validation additions

- Ratio entries must be positive integers.
- Every relation and event must reference existing tasks, targets, and events;
  unknown references are semantic errors.
- `ordering` requires `min_lead` not greater than `max_lead`.
- `contains` requires both endpoints to be windows, not point events.
- `phase_reference` targets must exist in the referenced task.
- `applied_offsets` keys must name declared tasks.
- `offset_realization` keys must name tasks that declare `applied_offsets`, and
  each `method` must be one of `crank_phase`, `gear_train`, `coupling`,
  `other`.
- A fixed-offset relation graph must not contain a cycle that makes the
  network over-constrained.
- Phase or time quantities must match the document `independent_variable`, or
  carry a unit the implementation supports.

## 8. Line-level result contract

A conforming composed result should include:

`yaml
line_result:
  master_cycle_id: line_shaft
  achieved_phase_zero: {transfer: pick, clamp: closed}
  verified_relations:
    - {id: clamp_before_press, achieved_lead: {phase: 42}, status: pass}
  verified_events:
    - {id: part_handoff, status: pass, co_location_error: 0.3}
  timeline_artifact: timeline.json
`

The timeline artifact is a machine-readable composed timeline: for sampled
master phases, each participating mechanism's input phase and output pose.
Downstream tooling can animate, collision-check, and export from it.

## 9. Implementation staging

1. **S1 — Specification draft.** This document.
2. **S2 — Document validation (implemented).** `omts validate` accepts v0.2
   synchronization fields, including ratios, unit objects, event references,
   and applied offsets, with the semantic checks of section 7.
3. **S3 — Composed run plans (implemented).** The adapter prepares independent
   per-task runs and records preparable synchronization in a `line` plan
   section with `verification: pending_timeline_verification`. Preparable
   means: 1:1 participants, `co_active` events with phase windows, `ordering`
   or `fixed_offset` relations between target-reached events with
   phase-quantified values, and phase-quantified `applied_offsets`. Ratioed
   participation, dwell/handoff references, and time-quantified values are
   rejected. No joint optimization.
4. **S4 — Timeline verifier (implemented).** `omts verify-line <plan-dir>`
   reads the plan line section and each task's completed run manifest,
   anchors achieved target phases to each task's `phase_reference`, applies
   declared `applied_offsets`, and checks every event and relation on every
   combination of selected candidates. It writes `line_result.json` with
   per-combination statuses and achieved leads. Only positive-direction runs
   are verifiable in this first version; zero-selection outcomes are recorded,
   not raised. The result also echoes the `offset_realization` build record
   when offsets are declared (`offset_realization.recorded` and
   `unrecorded_tasks` in `line_result.json`); the verdict itself never
   depends on it. Composed-timeline rule: every task's `phase_reference` target
   is aligned at master phase 0 (then moved to its applied offset when one is
   declared), and tasks without a reference contribute raw phases (then
   rotated by any applied offset).
5. **S5 — Joint search.** Free offsets and anchors become search variables.
   Its first steps are implemented: `omts verify-line --probe-anchors`
   rotates one task's composed phases across the full master cycle at a
   configurable step and reports, per task, the circular offset intervals
   where at least one candidate combination satisfies every hard event and
   relation. It uses already-computed results and never reruns the solver.
   Probe offsets are feasibility targets, not verified solutions.
   `applied_offsets` (section 2) is how a probe-chosen offset becomes
   first-class: declared offsets flow from document validation through the
   plan to the verdict, and the probe's feasible intervals become candidate
   values for them. The baseline verdict of an undeclared-offset run is
   unchanged by probing.
   The joint offset solver completes the staged step: `omts propose-offsets
   <plan-dir> [--step-deg N] [--top K]` grid-searches per-task master-phase
   offsets **jointly** (up to two participating tasks in this first version)
   over the existing per-task results and writes `offsets_proposal.json` with
   the assignments that maximize the number of passing candidate
   combinations, ranked by a constraint margin (the distance from the
   tightest constraint boundary) and with a document-ready
   `applied_offsets_example`. Recommendations are absolute: they are composed
   from raw achieved phases and replace any declared `applied_offsets`
   wholesale. The output is a proposal only — it never writes a verdict; a
   human declares the chosen offsets in the document, then re-validates,
   re-adapts, and re-verifies before the line is verified under them.

S3 and S4 require no new solver physics: each mechanism is still synthesized
independently, and synchronization is verified compositionally. This upgrades
the synchronized-line example from rejected to preparable and verifiable.

## 10. Open questions for review

1. Should `relations` fully deprecate `phase_relations`, or coexist until 1.0?
2. Is the `task.event` dot notation sufficient, or are path-fragment events
   (for example `transfer.enters_region.north`) needed for collision windows?
3. Do sweep and collision windows belong in v0.2, or wait for standard
   collision-body geometry already planned for v0.2?
4. For free `ordering` leads on fixed-timing tasks, does the existing ordered
   target-phase machinery leave the solver enough freedom for S4 to be useful
   before S5 exists?
5. Should the anchor probe's feasible intervals become an input to S5 joint
   search, or remain a human-facing diagnostic only?

   **Resolution (answered in v0.2):** the probe remains a human-facing
   diagnostic. The joint offset solver (`omts propose-offsets`) searches
   directly over composed phases on the offset grid rather than consuming
   probe intervals, because single-task probe intervals are an incomplete
   guide: joint-only solutions exist where every task's probe intervals are
   empty (both tasks must move together for the shared window event to
   pass), so restricting S5 to probe interval candidates would silently
   exclude solvable lines. Probe intervals are still useful to a human as a
   cheap first look and as a cross-check when they are non-empty.
6. Is verifying a line under declared `applied_offsets` sufficient for v0.2,
   or must the plan also record how the offset is physically realized (gear
   ratio and tooth index, crank keyway) before a line can be called verified?

   **Resolution (answered in v0.2):** verifying under declared
   `applied_offsets` is sufficient, and the realization is recorded, not
   gated. The verifier composes phases; it cannot inspect gears or keyways,
   so making realization a gate would either fail-closed on unverifiable
   claims or invite box-checking. Instead the document may declare
   `synchronization.offset_realization` (section 2): a per-task `method`
   (`crank_phase`, `gear_train`, `coupling`, `other`) plus free-form
   `detail`. Validation requires realization keys to name tasks with
   declared offsets; the adapter records them in the plan line section; and
   `line_result.json` echoes an `offset_realization` summary whose
   `unrecorded_tasks` makes any missing build record visible next to the
   verdict. The verdict is unchanged either way — the record closes the
   traceability gap without pretending the verifier can check hardware.
