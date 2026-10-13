# OMTS v0.2 Synchronization Extension (Draft)

> **Draft 0.2.0-synchronization.** This document extends OMTS v0.1 section 16
> with the synchronization model proposed for v0.2. It is a specification draft
> for public review. No adapter in this repository implements these fields yet;
> the current R2.5c adapter continues to reject synchronization fields under
> `unsupported_feature_policy: error`.

**Status:** Draft for review; not implemented

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

```yaml
motion:
  cycle:
    period: 1.2
    phase_reference: pick   # target id in the same task
```

`phase_reference` names a target whose occurrence defines that task's phase
zero. If omitted, phase zero is the master's phase zero, as in v0.1.

## 3. Ratioed participation

```yaml
synchronization:
  master_cycle_id: line_shaft
  period: 1.2
  participants:
    - task: transfer          # default ratio [1, 1]
    - task: indexer
      ratio: [1, 4]           # one indexer cycle per four master cycles
    - task: feeder
      ratio: [2, 1]           # two feeder cycles per master cycle
```

`ratio` is `[numerator, denominator]` — task cycles per master cycles —
and both entries must be positive integers. Relations that reference a ratioed
task may carry `occurrence_index` (0-based within one master cycle); omitted
means the relation applies to every occurrence.

## 4. Quantities are never bare numbers

All synchronization offsets, tolerances, windows, and margins are objects:

```yaml
offset: {phase: 60}
tolerance: {phase: 2}
```

`phase` is in the document angle unit; `time` is in the document time unit.
Adapters must reject bare numeric values. The sign convention is fixed: an
`offset` is the phase of the referenced event measured from the referencing
event, positive in the cycle direction.

## 5. Events

A task exposes named events:

- `<task>.<target_id>.reached` — a point event at the target occurrence;
- `<task>.<target_id>.dwell` — the window event where the target declares a dwell;
- handoff and region events declared under `synchronization.events`.

```yaml
events:
  - id: part_handoff
    type: handoff          # co_active | handoff | co_location
    participants: [transfer.place.reached, clamp.grasp.reached]
    window: {phase_range: [145, 155]}
    tolerance: {phase: 2}
    payload_ref: workpiece
    mode: hard
```

`handoff` declares the payload being transferred and implies co-location and
co-timing. Kinematic adapters report handoff as unsupported; the contract
states the physical intent and capability checking decides who can enforce it.

## 6. Relations

`relations` replaces v0.1 `phase_relations`, which is deprecated in 0.2
and removed in 1.0. Relations connect events, not tasks.

```yaml
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
```

- `fixed_offset`: the `to` event must occur at `offset` after the `from`
  event, within `tolerance`.
- `ordering`: the `to` event must lead or lag the `from` event by between
  `min_lead` and `max_lead`; the exact value is a free design variable.
- `contains`: the `from` window must fully contain the `to` window with at
  least `margin` on both sides.
- `disjoint_windows`: the two windows must not overlap, with at least
  `clearance` between them.

## 7. Semantic validation additions

- Ratio entries must be positive integers.
- Every relation and event must reference existing tasks, targets, and events;
  unknown references are semantic errors.
- `ordering` requires `min_lead` not greater than `max_lead`.
- `contains` requires both endpoints to be windows, not point events.
- `phase_reference` targets must exist in the referenced task.
- A fixed-offset relation graph must not contain a cycle that makes the
  network over-constrained.
- Phase or time quantities must match the document `independent_variable`, or
  carry a unit the implementation supports.

## 8. Line-level result contract

A conforming composed result should include:

```yaml
line_result:
  master_cycle_id: line_shaft
  achieved_phase_zero: {transfer: pick, clamp: closed}
  verified_relations:
    - {id: clamp_before_press, achieved_lead: {phase: 42}, status: pass}
  verified_events:
    - {id: part_handoff, status: pass, co_location_error: 0.3}
  timeline_artifact: timeline.json
```

The timeline artifact is a machine-readable composed timeline: for sampled
master phases, each participating mechanism's input phase and output pose.
Downstream tooling can animate, collision-check, and export from it.

## 9. Implementation staging

1. **S1 — Specification draft.** This document.
2. **S2 — Document validation.** `omts validate` accepts v0.2
   synchronization fields, including ratios, unit objects, and event
   references.
3. **S3 — Composed run plans.** The adapter prepares independent per-task runs
   plus a post-hoc timeline verification step. No joint optimization.
4. **S4 — Timeline verifier.** Events and relations are checked against
   achieved per-task results; the adapter emits a line result and timeline.
5. **S5 — Joint search.** Free offsets and anchors become search variables.
   This is a research step and needs engine work.

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
