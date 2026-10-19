# OMTS v0.2 Dwell-Duration Vocabulary (Draft)

> **Draft 0.2.0-dwell-duration.** This document extends OMTS v0.1 section 9.6
> (Dwell) with the duration semantics and the realization record proposed for
> v0.2. It is a specification draft for public review. No adapter in this
> repository implements these fields yet; the current R2.5c adapter continues
> to reject dwell under `unsupported_feature_policy: error`.

**Status:** Draft (S1 — specification draft). Grounded in the recorded case
study A dwell-station record: `jobs/dwell-station-failure-01`,
`jobs/dwell-station-capability-01`, `jobs/dwell-station-decision-01`.

**Depends on:** OMTS v0.1 (`specs/omts/0.1/specification.md`); consistent with
the v0.2 synchronization extension
(`specs/omts/0.2/synchronization.md`).

## 1. Purpose

v0.1 section 9.6 states, verbatim:

> A dwell can be defined by duration or phase span.
>
> ```yaml
> dwell:
>   phase_span: 25
>   max_position_drift: 0.35
>   max_orientation_drift: 1.5
>   mode: hard
> ```
>
> A dwell is not merely a low-speed point. It is a bounded interval over which
> the output remains within a specified neighborhood.

The vocabulary exists; the semantics do not. v0.1 does not state whether
`phase_span` is a minimum or an exact span, has no allowance concept, and has
no record of how a realized dwell meets the demand. This draft clarifies the
demand semantics and adds the realization record. It adds no new relation
type and no new time vocabulary.

## 2. Demand semantics (clarification of v0.1 section 9.6)

- `phase_span` is the hard minimum dwell-interval width, in the document
  angle unit. A candidate meets the demand when its achieved dwell width is
  at least `phase_span` minus `phase_span_allowance`.
- `phase_span_allowance` (new, optional): nonnegative, in the document angle
  unit, default `0`. Validation rules: `phase_span_allowance >= 0`;
  `phase_span - phase_span_allowance >= 0`; `phase_span` must not exceed the
  applicable cycle period. An allowance of `0` means the demand is hard as
  stated — the recorded case study's rule (>= 50 deg, allowance 0.00).
- The fields live on the target's dwell declaration (the v0.1 section 9.6
  block), which is target-state vocabulary. They keep v0.1's bare-number,
  document-units convention (v0.1 sections 2.2, 6, and 9.4): the v0.2
  synchronization rule that quantities are never bare numbers
  (synchronization section 4) scopes to synchronization quantities and does
  not reach target-state fields.
- `max_position_drift` and `max_orientation_drift` already carry the
  neighborhood demand and are unchanged.
- The allowance is an authoring-time choice. Editing a demand after a
  recorded run re-runs the demand; recorded outcomes are data.

## 3. Units and the independent variable

- No new time vocabulary is added. The demand is phase-quantified when the
  document's `independent_variable` is phase (v0.1 section 8.3). Under a
  time-independent-variable document the same fields read in the document
  time unit per v0.1 section 6 and the synchronization extension's match
  rule (synchronization section 7: "Phase or time quantities must match the
  document `independent_variable`, or carry a unit the implementation
  supports"). An implementation supports the form matching the declared
  independent variable or rejects the document — a capability boundary,
  fail-closed.
- Time-quantified dwell duration and dwell references are rejected by the
  current tooling today: the synchronization extension's S3 preparable
  subset rejects dwell/handoff references and time-quantified values, and
  the v0.1 adapter profile rejects "timing/dwell" outright (v0.1 section
  20). That is a recorded capability boundary, not a vocabulary absence.
- Converting a phase demand to wall-clock time is a build fact (a declared
  crank-speed context), recorded at realization (section 5), never a spec
  promise.

## 4. Relation semantics (machinery unchanged)

- The unary width check is not a relation. It is a per-candidate
  requirement evaluated in the path/transmission class: semantic-shape plus
  capability-enforced, per v0.1 section 23's layered validation (schema,
  semantic, capability). None of the four synchronization relation types
  expresses "this window is wide enough," and none is added for it.
- Cross-task relations over dwell windows ride the existing machinery
  untouched: synchronization section 5 already exposes
  `<task>.<target_id>.dwell` as a window event where the target declares a
  dwell, and synchronization section 6's `contains` and `disjoint_windows`
  already operate on dwell windows — the extension's own worked example is
  `weld.target.dwell` to `clamp.closed.dwell`, type `contains`.
- Width is invariant under `applied_offsets` rotation (a rotated window
  keeps its width), so duration results compose with the S4/S5 machinery
  unchanged.
- A dwell window crossing phase 0 computes its width circularly
  (wrap-through-zero merge). Achieved width is a sampled-phase measurement,
  never a certified instant — the sampled-occupancy honesty convention.

## 5. Dwell realization record (v0.2)

`dwell_realization` records how each declared dwell demand is met. It
mirrors `synchronization.offset_realization` in shape and discipline —
recorded, never gated — at the target layer, because a dwell demand is
intra-task (the synchronization layer's purpose is relationships between
tasks):

```yaml
tasks:
  - id: station
    dwell_realization:
      hold_station:
        method: dwell_arc        # dwell_arc | linkage | other
        detail: concentric dwell arc, one x-cam + passive y-guide
        nominal_span: 53.20
        guaranteed_width: 53.80
        tolerance_class_mm: 0.05
        knee:
          class_mm: [0.05846, 0.05164]
          guaranteed_width: 53.20
          position_margin_mm: 0
          duration_margin_deg: 3.20
    motion:
      targets:
        - id: hold_station
          dwell:
            phase_span: 50
            phase_span_allowance: 0
            max_position_drift: 0.3
            mode: hard
```

- Keys name targets that declare a dwell demand (the `offset_realization`
  analog: there is nothing to realize otherwise).
- The record is a build note, never a verification input: it never gates or
  downgrades any verdict. A missing record is surfaced — the result echoes
  a `dwell_realization` summary with an unrecorded analog, so a reviewer
  can see whether the as-built record exists — never silently accepted.
- `method` is drafted from recorded practice only: `dwell_arc` (the case
  study A recorded family), `linkage`, `other`. The enum grows when a
  second family is recorded; families nothing has recorded are not
  enumerated.
- Within a declared record the knee row is required: the tolerance class,
  the guaranteed width at the knee, and both channel margins (position and
  duration). The recorded finding duration knee == position knee is what
  lets one row serve both channels; a class without its knee is the
  half-record that produced case study B's T4 archaeology.

## 6. Worked example (recorded digits)

The demand from the case study A record
(`jobs/dwell-station-decision-01`, section [C] of the run of record):

```yaml
dwell:
  phase_span: 50
  phase_span_allowance: 0.00
  max_position_drift: 0.3
  mode: hard
```

(document units: mm, deg)

The realization row of section 5 carries the recorded outcome: nominal span
53.20 deg; guaranteed width 53.80 deg (band-hi) / 54.60 deg (band-lo) at the
0.05 mm zoned class; 53.20 deg at the knee. The alternative-realization
data row: the direct-follower instance, guaranteed width 52.70 deg at the
0.10 mm working class.

Provenance of the nominal 53.20 deg: it is the declared width amendment of
the decision record (frozen rule: amended nominal width = zero-error
guaranteed width minus band-hi zoned-class width, rounded up to the 0.2 deg
cycle tile; reason: convert tolerance-driven erosion of the hold window
into nominal arc so the guarantee rests on the construction-exact arc),
confirmed on the machine run of record — a declared amendment, not a
computed restatement of the recorded nominal.

The demand fields map onto the capability instrument's metric directly: the
instrument's best-50-deg-window / max-distance-within measurement is an
evaluation of `phase_span` + `max_position_drift`.

## 7. Validation and versioning additions

- A `dwell_realization` key naming a target without a declared dwell is a
  semantic error, fail-closed.
- The allowance arithmetic of section 2 is semantic validation, not schema
  defaults.
- v0.1 documents with bare dwell declarations validate unchanged
  (versioned-documents precedent). The minimum-semantics clarification is
  normative from this draft forward; an implementation that treated v0.1
  `phase_span` as an exact span must disclose the difference, not silently
  pass (no silent feature loss).
- The R2.5c adapter rejects dwell today (v0.1 section 20); passing document
  validation never implies adapter acceptance.

## 8. Implementation staging

1. **S1 — Specification draft.** This document.
2. **S2 — Document validation.** (future) `omts validate` accepts
   `phase_span_allowance` and `dwell_realization` with the section 7 rules.
3. **S3 — Capability.** (future) dwell width evaluation over sampled
   phases in the path/transmission class: wrap-aware width, per-combination
   duration rows with achieved width and status, sampled-honesty reporting.

## 9. Open questions for review

1. Should `phase_span` minimum semantics be a clarification of v0.1 or an
   explicitly versioned change? (This draft: a clarification, recorded;
   v0.1 documents unchanged.)
2. Should `dwell_realization` echo into the result contract exactly as
   `offset_realization` echoes into `line_result.json`? (This draft: yes —
   the unrecorded-echo analog.)
3. Should the `dwell_realization` block sit at task level or document
   level? (This draft: task level, next to the targets it names.)
