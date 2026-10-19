# B2 answer schema -- the mounting-angle representation-consistency diagnosis (frozen before the run)

Status: **Frozen; B2 may not run before this schema is merged.**

B2 (docs/strategy.md, the amended ordering) is the generalization
diagnosis: whether the four-bar niche's mounting-angle
representation -- the part rigidly mounted to the coupler point
(centroid + orientation, angles wrapped over the full turn) -- is a
binding limitation on the recorded failure outcomes, or whether the
failures are data-limited (the pools genuinely cannot serve the
demands), or both, or inconclusive. B2 runs as desk analysis,
read-only over recorded data. This document freezes the ANSWER
schema so the answer cannot be shaped by the diagnosis: the
question, the enum, the evidence-row shape and the rules are all
committed before the first data row is read. With this file merged,
condition (b) of the strategy trigger closes and B2 may run.

## The frozen question

Stated once here, never reworded: for the recorded failure corpora,
are the binding rejections attributable to the mounting-angle
representation (a convention artifact of the rigid coupler mount),
or to the candidate data (the pools' genuine capability limits), or
both, or is the evidence inconclusive?

## The declared data points (read-only, cited by hash)

- Case study B: the gap-transfer-failure-01 record (four-bar
  three-pose failure; positions bound ~6-7x over tolerance), corpus
  per that JOB.md's recorded outcome.
- Case study C: the flip-station-failure-01 record (the flipper:
  orientation-dominant rejection across the pool, 36 scored rows,
  schema 1) -- JSON Lines
  fbea95681d26883c9cf46eff9132ea07f31c3f5286baf0cd883671585d11e5c1,
  flat CSV
  01dd9c068155b3ba0f20b1485c3d5846079fbaf37e4d17f0e3133684d64e7638.

B2 consumes these read-only. It does not rerun the engine, and it
never rewrites a recorded row.

## The answer schema (version 1.0)

The B2 answer is recorded as one machine-readable JSON document:

- `diagnosis_id`: "b2-mounting-angle-representation-consistency"
  (fixed string).
- `schema_version`: "1.0" -- pinned; emitters and readers fail
  closed on unknown major versions.
- `frozen_question`: verbatim from this document, this section.
- `data_points`: one entry per consumed corpus, each with
  {case_study, job_id, corpus_format, sha256, corpus_schema_version,
  rows, units_basis} -- the hash pins the exact bytes read.
- `representation_hypothesis`: the hypothesis under test, stated
  before the diagnosis reads the data: the rigid coupler mount
  (centroid + full-turn-wrapped orientation) is the only
  representation the recorded instruments could score, so
  representation-driven rejection cannot be excluded from the
  records without a re-representation test. Enum of concrete
  hypotheses tested, each with a stated test method.
- `answer`: exactly one of
  {representation-limited, data-limited, both, inconclusive}, with
  reasons. The enum is closed; `inconclusive` is a valid recorded
  answer, not an error.
- `evidence`: rows, each {claim, source_data_point (by sha256),
  units block, method} -- no number without its units block and its
  source hash; computed, never transcribed (the PR-A lesson).
- `recommended_convention`: present ONLY if the answer is
  representation-limited or both. Fields: {field structure,
  rationale, lineage: supersedes-what, amends-what-recorded-data}.
  Any convention change is a new recorded convention with lineage;
  recorded outcome data is never rewritten.
- `mounting_declaration` (the shared field structure, the seam
  flip-station-capability-01 declares against): {mounting_vector
  (2-tuple, explicit units), mounting_angle_deg, frame, lineage}.
  The capability step's declaration uses exactly this structure, so
  B2's answer lands in a form that study already speaks.
- `provenance`: {run date, method (desk, read-only), source
  commits of every consumed corpus, the B2 JOB.md reference}.

## Rules (frozen)

1. B2 runs only after this schema is merged (its condition-(b)
   close; the strategy trigger's (a) is already satisfied by the
   flipper failure record).
2. The diagnosis consumes recorded data read-only; it reruns
   nothing.
3. Every number in the answer carries a units block and its source
   hash.
4. The answer enum is closed; an inconclusive answer is valid
   recorded data.
5. If a recommended convention amends the mounting declaration used
   by flip-station-capability-01, that declaration is amended by a
   new recorded convention with lineage; the recorded corpus rows
   are never rewritten (the outcome-data discipline applied to
   conventions).
6. Schema succession follows the frozen corpus rule: additive
   fields are 1.x with a recorded changelog row; any change to an
   existing field's meaning, unit or name is 2.0; fail closed on
   unknown major versions.
