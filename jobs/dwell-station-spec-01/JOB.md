# dwell-station-spec-01: case study A spec side — the OMTS dwell-duration vocabulary draft

Status: Spec draft staged (S1); docs-only

## Purpose

The spec-side step of the case study A loop, with the closed
dwell-station decision as its input. Both debate rounds (actor, then
critic, via Jean's relay) are folded here; the staged artifact is the
S1 specification draft `specs/omts/0.2/dwell-duration.md`. This job
records the fold, the desk-check citations, the blockers and their
discharge, and the provenance settlement. Docs-only: no schema, code,
or adapter change is claimed or staged.

## The fold (both rounds, where each landed)

- **The actor's desk-check headline, verified on current main:**
  v0.1 section 9.6 already contains the dwell-duration vocabulary,
  verbatim ("A dwell can be defined by duration or phase span"; the
  `dwell: {phase_span: 25, max_position_drift: 0.35,
  max_orientation_drift: 1.5, mode: hard}` block; "A dwell is not
  merely a low-speed point. It is a bounded interval over which the
  output remains within a specified neighborhood."). Claim-only-
  what-exists cuts both ways: the draft edit is a semantics
  clarification of existing vocabulary, not new vocabulary. ADOPTED —
  the draft quotes section 9.6 verbatim in its section 1 and presents
  itself as a clarification.
- **Plank 1 AMENDED (both rounds):** the demand+allowance pair lives on
  the target's section 9.6 dwell block, not on a sync dwell ref. The
  sync layer's purpose is relationships between tasks (sync section
  1); a dwell demand is intra-task, and putting it on the sync event
  would make an unsynchronized dwell inexpressible. The sync layer's
  section 5 `<task>.<target_id>.dwell` window event merely exposes the
  target-declared dwell for cross-task relations.
- **Plank 4 RESTATED (both rounds, forced by the verbatim quotes):**
  time IS a spec unit in OMTS — v0.1 section 6 declares `time: s`; the
  sync extension's section 4 states "time is in the document time
  unit"; section 7's match rule governs phase-or-time quantities. The
  correct statement: the dwell demand for this case is phase-quantified
  because the document's independent variable is phase; no new time
  vocabulary is added; under a time-independent-variable document the
  same block reads in the document time unit, and an implementation
  supports the form matching the declared independent variable or
  rejects the document — a capability boundary, fail-closed.
  Time-quantified dwell duration and dwell references are
  adapter-rejected today (sync S3's preparable subset; v0.1 section
  20's "timing/dwell" rejection). The crank-speed conversion statement
  is a realization/build fact, kept out of the spec draft's demand
  semantics (it appears only in the realization context).
- **Plank 6 REFERENCE FIX (actor):** "the public OMTS draft's section 4
  unit rules" was ambiguous — v0.1 section 4 is serialization and
  versioning. The unit rules are v0.1 section 6 (units) and section
  2.2 (explicit units), plus sync section 4 ("Quantities are never
  bare numbers"), which scopes to synchronization quantities. The
  target-layer dwell block keeps v0.1's bare-number, document-units
  convention (matching section 9.4 tolerances); importing the sync
  object form there would fork the unit convention between layers.
  ADOPTED — the draft names its quoted sections.
- **Q1 fold:** demand + allowance pair; the full window object
  (demand/nominal/guaranteed) REJECTED — nominal and guaranteed are
  realization (plank 2 stands). Allowance arithmetic frozen in the
  draft text, not inferred: achieved width >= phase_span -
  phase_span_allowance; allowance >= 0; demand - allowance >= 0;
  demand <= the applicable cycle period. Critic's discipline note
  adopted: the allowance is an authoring-time choice; editing a demand
  after a recorded run re-runs the demand (recorded outcomes are data).
- **Q2 fold:** no new time vocabulary (the plank-4 restatement is the
  whole answer); native phase for dwell because the machine cycle is
  the spec's independent variable.
- **Q3 fold:** "nearly free" CONFIRMED for the cross-task case by the
  spec's own example — sync section 6's worked `contains` example is
  `weld.target.dwell` to `clamp.closed.dwell`; dwell windows are
  already first-class window events (sync section 5) with
  contains/disjoint_windows riding untouched. The unary width check is
  NOT a relation (no fifth type; vocabulary bloat rejected) — it is a
  per-candidate requirement in the path/transmission class, per v0.1
  section 23's layered validation. The desk-check record in the draft's
  section 4 carries: the section 6 citation; the section 23 layering
  slot; offset-invariance of width (rotated windows keep width, so
  duration composes with S4/S5 unchanged); wrap-aware width
  computation (wrap-through-zero merge precedent); and the
  sampled-window honesty convention (achieved width is a
  sampled-phase measurement, never a certified instant).
- **Q4 fold:** `dwell_realization` mirrors `offset_realization`'s
  pattern and discipline exactly — recorded, never gated; keys name
  targets that declare a dwell demand; the result echoes a summary with
  an unrecorded analog — RELOCATED to the target layer (dwell is
  intra-task; offset_realization is sync-level because offsets are).
  Method enum drafted from recorded practice only: `dwell_arc` |
  `linkage` | `other` (the actor's `dwell_arc | other` widened by the
  critic's recorded-practice reading of the four-bar family;
  unrecorded families not enumerated). Knee row REQUIRED within a
  declared record (a class without its knee is the half-record that
  produced case B's T4 archaeology), compact per the duration-knee ==
  position-knee finding: class, guaranteed width at knee, both channel
  margins. The record itself stays optional and never gates.
- **Q5 fold:** the demand block and realization row are mechanical
  (exact field names/units in the draft's sections 5-6); the worked
  example digits come from the recorded run of record with one sentence
  mapping the demand fields onto the capability instrument's metric
  (best-50-deg-window / max-distance-within = phase_span +
  max_position_drift). Critic's versioning statement adopted: the
  allowance is a v0.2 addition on an existing v0.1-era declaration; the
  draft quotes the v0.1 dwell declaration verbatim and states that v0.1
  documents with bare dwell declarations validate unchanged
  (versioned-documents precedent, per the sync section 6 pattern).
- **Q6 blockers — all discharged in the staged draft:** (a) the
  plank-4 restatement is in the draft's section 3, so the PR contains
  the verbatim quotes and a text consistent with them; (b) the section
  references are precise (v0.1 sections 2.2/6/8.3/9.4/9.6/20/23; sync
  sections 1/4/5/6/7/9); (c) the section 9.6 discovery is folded — the
  draft quotes the existing block verbatim and clarifies rather than
  re-invents; (d) the example digits are taken from the recorded
  decision JOB and the run of record, with the provenance settled
  (below); (e) the adapter-boundary honesty note is in the draft's
  sections 3 and 7 (v0.1 section 20 "timing/dwell ... rejected" today;
  S3 rejects dwell references); (f) planks 2, 3, 5, 7 stand as
  written — the spec never promises nominal width, the desk-check
  record is in the draft, the width-bias amendment stays
  realization-side, and the PR is docs-only claiming nothing landed.

## Provenance settlement (the critic's blocker, discharged)

The worked example's nominal 53.20 deg is the DECLARED width amendment
of the decision record — not a computed restatement. The frozen rule
(amended nominal width = zero-error guaranteed width minus band-hi
zoned-class width, rounded UP to the 0.2 deg cycle tile; w = 3.20 deg)
and its reason (convert tolerance-driven erosion of the hold window
into nominal arc so the >= 50 deg guarantee rests on the
construction-exact arc, not on the rise margins, which vanish at the
knee) are recorded in jobs/dwell-station-decision-01/JOB.md section
[B] and were CONFIRMED on the machine run of record (S2 of the frozen
scorecard; zero divergence). The spec example may therefore enshrine
53.20 deg with that provenance line, which the draft's section 6
carries verbatim.

## Desk-check citations (verified on current main)

- v0.1 specification.md: sections 2.2, 4, 6 (`time: s`), 8.3, 9.4,
  9.6 (dwell block verbatim), 20 ("timing/dwell ... rejected"), 23
  (layered validation).
- 0.2/synchronization.md: section 1 (purpose: relationships between
  tasks), section 4 (bare numbers rejected; "time is in the document
  time unit"), section 5 (`<task>.<target_id>.dwell` window event),
  section 6 (`weld.target.dwell` to `clamp.closed.dwell` contains
  example; the four relation types), section 7 (the
  independent_variable match rule; offset_realization keys rule),
  section 9 (S3 preparable subset rejects dwell/handoff references and
  time-quantified values).

## What the draft claims / does not claim

- Claims: a clarification of v0.1 section 9.6 semantics (`phase_span`
  as hard minimum); one new optional demand field
  (`phase_span_allowance`, default 0, with frozen arithmetic); the
  target-layer `dwell_realization` record (recorded, never gated, knee
  row required); the recorded digits as the worked example with
  provenance; three open questions for review. S1 draft only.
- Does not claim: no schema change landed (S2 is future); no dwell
  evaluation capability (S3 is future; the adapter rejects dwell
  today); no machinery change (sync relations untouched); no
  certification (sampled-phase honesty throughout); no pivot-joint
  class (the case study A deferral stands with its trigger).

## Machine step

None. Docs-only. Recorded outcomes are never rewritten; this draft is
a new record, staged for review.
