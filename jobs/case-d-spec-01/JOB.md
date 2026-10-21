# case-d-spec-01: case study D spec side -- the OMTS continuous-path interval-channel vocabulary draft

Status: Spec draft staged (S1); docs-only

## Purpose

The spec-side step of the case study D loop, with the scoped capability
verdict (PR #107, merged) and the folded D decision round as its inputs.
All decision-round rounds (actor, critic, and the actor's convergence,
via Jean's relay) are folded here; the staged artifact is the S1
specification draft specs/omts/0.2/interval-channel.md. This job records
the fold, the desk-check citations, the critic's three deltas and their
discharge, and the provenance settlement. Docs-only: no schema, code, or
adapter change is claimed or staged.

## The fold (all rounds, where each landed)

- **Q1 fold:** the lean ENDORSED -- (i) D's spec-side step, then D closes
  behind it, on the case-A precedent (the spec-side step completed A
  end to end; strategy picks read closed loops, never half-open ones);
  the vocabulary lesson grounded in recorded data (the P4 refutation,
  the whole-trace binding, the interval channel nobody had gated).
  Option (iii) DECLINED explicitly and on principle: the parked
  capability lines are unfired with recorded triggers; staging them now
  would be preference advancing under a card, exactly what the trigger
  discipline exists to prevent.
- **Q2 fold, the actor's desk-check-first discipline executed on
  current main:** the shape is ALREADY EXPRESSIBLE -- v0.1 section 9.3
  (occurrence at one phase / phase range / one time / time range /
  free), section 9.4 (tolerances, document units, the
  implementation-profile rule), section 9.5 (velocity, acceleration,
  jerk by vector/magnitude/direction/bounds), section 10 (motion
  primitives for structured motion), section 11 ("Path constraints
  shape the motion between targets"); the recorded flip motion task
  (jobs/flip-station-sixbar-01) carried a twelve-phase sampled
  trajectory with a C2-class orientation program through the recorded
  engine's task validation. The suspicion CONFIRMED: most of the class
  is clarification, not new vocabulary. The GENUINE ADDITION is the
  interval channel: the between-samples gate first-class, the explicit
  pin-count-vs-whole-trace distinction, and the rule that demand
  declarations in this class pin the interval tolerance explicitly
  ("expressible, not implied"). The draft quotes the spec verbatim and
  cites sections throughout.
- **The critic's delta 1 (gate home), adopted in full:** the
  interval-channel vocabulary declares where its gate lives --
  validation checks structure, units, and pinned-sample consistency
  (v0.1 section 23's schema and semantic checks); the interval verdict
  happens at run/verify against per-sample emission; the adapter's
  current rejection is stated as the recorded boundary in the
  S-staging-note pattern (v0.1 section 20's "timing/dwell ...
  rejected"), never implied to be implemented. The demand/realization
  split precedent (offset_realization, dwell_realization) is the
  structural template: the interval tolerance is demand-side, its
  checking is trace-side, and the draft says both. The actor's
  adoption noted this is the one piece the case-A precedent does not
  automatically cover (the dwell block was clarification; the interval
  gate is additive) -- discharged in the draft's section 4.
- **The critic's delta 2 (the eight-bar consequence line), adopted in
  full with the actor's addition:** D's closure record carries the
  sentence verbatim in substance -- under the shape-reachability
  reading, a capacity-driven demand can never fire the
  family-extension trigger; an extension on density evidence requires
  the trigger's own declared amendment, never a reinterpretation -- and
  the strategy card's trigger-state row rides it so the next pick reads
  it at decision time, not archivally. NOT in this draft: it lands in
  D's closure record (its own docs-only PR after this merge) and on
  the strategy card; this job records the disposition.
- **The critic's delta 3 (the near-reach brief-design lesson), adopted
  with the actor's task-merits-first guard:** the (b)-context
  testability is a demand-difficulty design choice made at freeze --
  a beyond-capacity demand with a surviving capability line only
  exists in the family's near-reach (hard enough that exact synthesis
  stops covering it, not so far beyond that the pool dies whole);
  D's k = 3 margin wide-failed the pool by its own derivation's
  design. The guard: the task stands on task merits first; the pin
  count is DERIVED from the task's actual need; where the task need
  permits, the brief sits the demand in the near-reach band and states
  the testability consequence at freeze; never a difficulty tuned to
  keep the supplier question alive (manufactured pattern-demand
  selection is the inversion the guard exists to prevent; if a real
  task needs N + 3, the honest wide-fail is the correct outcome --
  data, not a defect). Lands in the disposition rows of D's closure
  record and on the strategy card; NOT in the vocabulary draft
  (supplier-agnostic by construction).
- **Q3 fold:** the supplier rows PARK with D's record; they do not
  ride the vocabulary (recorded honestly as not reached in this
  context -- axes defined and unfired, the (b)-context untested
  because no capability line survived to compare within; restating
  them in a docs-only framework PR would smuggle a supplier question
  into the one place it must not appear). ONE scope line in the draft
  (its section 4): the demand class is gradeable by existing recorded
  instruments, nothing more.
- **Q4 fold:** the vocabulary PR lands FIRST (this job), then the
  closure record as its own docs-only PR; D closes behind the
  spec-side merge per the lean's own sequencing, so the closure
  section reads MERGED vocabulary, never drafts (the PR #60 pattern:
  the close-out decision is the closure event). The closure record
  carries: the loop's full lineage (brief -> derivation check ->
  instrument -> run of record -> status cell -> the scoped verdict);
  the spec-side deliverable pointer; the parked lines with their
  triggers (the relaxed-class fallback with its owner-declaration
  trigger; the eight-bar on shape-reachability data only, still not
  fired); the supplier disposition per Q3; the eight-bar consequence
  line (delta 2); the near-reach lesson in the disposition rows
  (delta 3, guarded); and -- recorded as data, never as a family
  verdict -- the honest note that D's task demand stands unsolved at
  seven pins by the recorded family, the case-C shape.
- **Q5 fold:** the strategy round is the next event after D's closure
  merge; its card carries the frontier state after four closed loops
  (A: dwell -> spec; B: dual-cam with its tolerance story; C: flip,
  honest failure with corpus; D: path+timing vocabulary, boundary
  recorded, demand unsolved), the two honest unsolved tasks and the
  trigger states (delta 2's consequence line on the trigger-state
  row), the learned-supplier line's standing (endgame containment +
  D's not-reached disposition, triggers (a)/(b)/(c), no authorized
  context currently visible), the community pointer's discharge state,
  the deferred items' trigger states, and the delta 3 lesson with its
  guard; the framing note: after D, the framework has demonstrated
  the loop four times and the vocabulary has grown twice from it --
  the strategy question is fairly posed as where the next task comes
  from, not whether the loop works.

## Desk-check citations (verified on current main)

- v0.1 specification.md: sections 2.3 (hard/soft/report-only), 4
  (semantic versioning: patch clarifies without changing meaning,
  minor adds backward-compatible fields, major may alter meaning), 6
  (units; time: s; length: normalized permitted), 8.1-8.3 (motion
  mode, order policy, cycle), 9.3 (occurrence), 9.4 (tolerances; the
  implementation-profile rule), 9.5 (velocity, acceleration, jerk),
  9.6 (dwell -- the intra-task layer precedent), 10 (motion
  primitives), 11 (path constraints "shape the motion between
  targets"), 20 (the R2.5c adapter's "timing/dwell ... rejected"
  boundary; "Passing general OMTS validation does not imply
  acceptance by this adapter"), 23 (the three distinct checks; "A
  valid document with hard dynamic requirements must still be
  rejected by a kinematic-only adapter").
- 0.2/dwell-duration.md: the S1 clarification pattern; the
  sampled-window honesty convention ("a sampled-phase measurement,
  never a certified instant"); the authoring-time discipline.
- 0.2/synchronization.md: the S-staging-note pattern;
  synchronization.offset_realization (recorded, never gated).
- jobs/case-d-brief-01, jobs/case-d-derivation-check-01: the frozen
  brief (the between-points interval channel at a declared 8x
  refinement, sampled never certified; N + k derived, never picked)
  and the derivation check (N = 4; the count rule fires at 7).
- jobs/case-d-digest-01: the demand artifact
  (demand_ellipse_7pin.motion.json -- the twelve-phase program with
  per-sample q/v/a tables), the run of record, and the capability
  verdict section (PR #107).
- jobs/flip-station-sixbar-01: the recorded twelve-phase sampled
  trajectory with a C2-class orientation program carried through the
  recorded engine's task validation.

## Provenance settlement

The worked example's digits are the recorded case study D digits,
never restated: the twelve-phase program and per-sample tables from
the staged demand artifact; the 0.10 mm class (3.634562e-4 normalized,
the scale that puts the case-B 260 x 90 mm bounding box at semi-axes
0.4724930367201291 x 0.16355528194158314); the seven pinned phases at
7 = N + k (N = 4, k = 3) from the derivation check; the interval
channel's declared 8x refinement / 96 samples from the brief; and the
run-of-record outcome digits (worst pin residuals 0.407 / 0.281; the
interval channel failing alongside at 0.432 / 0.281; the P4 refutation
between_sample 1187.2 vs position_pins 1118.5 on seed 580000051, the
tie at 772.394 on seed 580000052; control A 3/3 at 150/200
evaluations, worst 0.001 vs the solver's own 0.01 gate; control B 3/3
fail, moved-pin residual 0.035 vs unmoved 0.011) from the recorded
run and the capability verdict section of jobs/case-d-digest-01.
The native instrument is the experimental six-bar motion engine's
PR-B per-sample emission, consumed unmodified (instrument
modification count 0 at the run of record).

## What the draft claims / does not claim

- Claims: one S1 specification draft -- the interval block and its
  semantics (whole-trace binding; the pin-count-vs-whole-trace
  distinction; expressible-not-implied tolerance pinning;
  sampled-never-certified honesty; the gate-home declaration with the
  adapter boundary recorded; one scope line); the recorded digits as
  the worked example with provenance; four open questions for review.
- Does not claim: no schema change landed (S2 is future); no interval
  evaluation capability (S3 is future; the R2.5c adapter rejects
  timing/dwell today); no timing vocabulary added (time is a spec
  unit; phase-quantified-natively with the adapter boundary recorded
  is the settled plank-4 form); no family capability beyond the
  recorded scoped verdict (the shape-reachability question stays
  open; family extensions governed by their own declared triggers,
  never by reinterpretation); no supplier question inside the draft.

## Machine step

None. Docs-only. Recorded outcomes are never rewritten; this draft is
a new record, staged for review.
