# B2 answer: the mounting-angle representation-consistency diagnosis -- recorded (2026-10-19)

Status: **B2 run recorded; the machine-readable answer is
docs/b2-answer.json (answer-schema 1.1, additive changelog row inside).
This file is the desk reading.**

B2 (docs/strategy.md, the amended ordering; answer schema frozen at
docs/b2-answer-schema.md, merged with PR #72) ran as desk analysis,
read-only over the two declared data points. Nothing was rerun; no
recorded row was rewritten; no instrument was touched (the
reciprocity count is 0 trivially -- nothing executed against the
instruments).

## The frozen question (verbatim)

For the recorded failure corpora, are the binding rejections
attributable to the mounting-angle representation (a convention
artifact of the rigid coupler mount), or to the candidate data (the
pools' genuine capability limits), or both, or is the evidence
inconclusive?

## The re-representation class under test

A mounting declaration is a constant (vector, angle, frame, lineage)
over one rigid mount. The re-representation test is therefore: does
there exist a mounting vector v and a constant offset angle c such
that a rejected candidate, re-scored with the part mounted at
coupler point + R(theta + c) v and oriented at coupler orientation
+ c, serves the demand? Three hypotheses:

- H1: constant offset angle alone (v = (0,0)).
- H2: the full (v, c) class. v does not enter orientation, so every
  orientation conclusion under H1 survives H2 unchanged; v only
  adds play to the position gates.
- H3: non-rigid or time-varying mounting (a wrist, compliance, a
  decoupled part orientation). Out of class, recorded not tested:
  that is a new mechanism family (the capability-step question),
  not a re-representation of the four-bar niche. B2 diagnoses the
  convention, not the family line.

## Finding 1 -- case C: the binding rejection is invariant under the
full class (proven)

The recorded binding class is orientation-dominant 36/36. The demand
requires 180.000 deg of part swing between the handoff poses
(orientation 0 -> 180 deg through the 90 deg vertical mid pose) at
1.500 deg tolerance per pose. Under any c, the pose-to-pose
differences of the gate inequalities lose c entirely: the coupler
must swing at least 180.000 - 1.500 - 1.500 = 177.000 deg,
unwrapped, between the two handoff phases. A mounting vector does
not enter orientation at all. The pool's best free swing anywhere in
any cycle (the recorded D3b, the unwrapped full-cycle coupler-angle
range) is 156.452 deg -- a deficit of 20.548 deg below the minimum.
No mounting declaration in the rigid-mount class rescues any
candidate, pool-wide. Position fails independently (pool-best
11.65x tolerance; the D3a at-pose pairing is none for every
candidate), so the conjunction closes: case C's binding rejection is
attributable to the candidate data under the full (v, c) class.

This is the recorded live blocker the diagnosis was commissioned on
(docs/strategy.md), and it is not a convention artifact: the pool
genuinely cannot swing far enough.

## Finding 2 -- case B: the binding gate is proven for the pool's
best candidate; a scoped caveat is recorded

The binding gate is position (the recorded P2 refutation:
qualification stops at position in every row; best worst-pose
9.08 mm positive at 6.05x / 10.45 mm negative at 6.97x, computed
ratios that reproduce the recorded "about 6.1x / 7.0x").

The constant-offset test: passing all three position gates after
any common offset requires the per-target residuals to satisfy
|r_i - r_j| <= 2 x 1.5 mm = 3.00 mm for every pair, and the
recorded magnitudes bound |r_i - r_j| from below by |e_i - e_j|.
Computed over the ten recorded frontier rows, the pairwise spreads
are 8.61 / 7.86 / 9.32 / 9.36 / 10.76 / 4.26 mm for six rows --
each above the 3.00 mm threshold, proving no-rescue under a common
offset, including the positive-direction pool-best fixed_001
(6.69 / 9.08 / 0.47 mm). Four rows sit at or below the threshold
(1.15-1.49 mm: bridge_release_002+; bridge_release_001- /
bridge_trust_001-, a duplicate-lineage pair; bridge_trust_002-),
and the negative-direction pool-best is among them.

The scoped caveat, recorded honestly: the recorded outcome tables
carry per-target error magnitudes, not residual directions, so the
necessary condition cannot be completed for those four rows; and
under the full (v, c) class a nonzero mounting vector adds
pose-dependent corrections (rotational play bounded by the recorded
inter-pose orientation deviations from level -- worst pair bound
17.75 deg, fixed_003: 9.72 + 8.03 deg) that magnitudes alone
cannot resolve. The named follow-up: a direction-resolved
re-representation re-score over the recorded corpora, read-only
transformation, the frame-sweep precedent -- it would close the
remainder of the case B caveat. It cannot reopen case C (the swing
bound is exact and class-invariant) or the case B pool-best finding
(proven).

## Finding 3 -- the records do contain representation artifacts,
and they are non-binding

The case B orientation gate as scored is representation-scoped: a
constant mounting angle re-targets which coupler orientation
counts as level, and the frontier holds candidates at a
wrong-but-constant coupler angle (orientation spreads 0.12-2.54 deg
within the 3.00 deg threshold for 9 of 10 rows; e.g. bridge_trust_001
positive at 6.15 / 6.40 / 6.42 deg) whose orientation rejection is
a pure mounting-angle artifact. The diagnosis detects exactly what
it was built to detect -- and finds the artifacts non-binding:
every such row still fails the position gate, which binds deeper
pool-wide. The record also contains the genuine article (fixed_003
positive: orientation spread 3.35 deg over the threshold -- no
constant angle rescues it). This is the strongest internal check
the data offers: the method finds representation artifacts where
they exist and still returns data-limited, because they do not bind.

## The answer

**data-limited** -- exactly one value from the frozen closed enum,
recorded in docs/b2-answer.json with the evidence rows above, each
carrying its units block, its source hash (the case C corpus hashes
fbea9568... / 01dd9c06...; the case B record pinned by commit and
path under the additive locator field, its pre-emitter hash gap
disclosed, never papered over) and its method.

Per the frozen schema rule, recommended_convention is ABSENT
(present only for representation-limited or both): the rigid-mount
convention as scored needs no amendment from this diagnosis. The
mounting declaration field records the convention under diagnosis
with its lineage; the flip-station-capability-01 seam declaration
(identity mount in the carrier frame) stands unamended.

## Trigger bookkeeping

The strategy trigger (docs/strategy.md): condition (a) SATISFIED
(the flipper case study closed with its corpus in the record,
PR #70). Condition (b) -- "the generalization diagnosis has a
recorded answer in its frozen schema" -- is satisfied by this
document and docs/b2-answer.json ON MERGE of the PR that stages
them. When Jean merges, the strategy trigger FIRES: both
conditions hold, the "one more case study" argument is spent, and
the next staged item is the B1 admission-gate work unless Jean
explicitly overrides with a recorded reason.

Answer-schema succession note: the answer document declares
answer-schema 1.1 over the frozen 1.0 -- one additive field
(data_points[].locator) with its changelog row recorded inside the
document, per the frozen succession rule (additive = 1.x; any
change to an existing field's meaning, unit or name = 2.0). The
frozen question, the answer enum and the evidence-row shape are
unchanged.
