# Flip station failure analysis (case study C, the flipper brief) -- staged

Status: **Staged; awaiting run.**

Case study C is the flipper: the next item of the amended ordering
(docs/strategy.md), and the first case study designed from the start as
the downstream consumer of the B1 admission-gate work. Its recorded
outcome must therefore exist as a machine-readable solution corpus, not
only as prose: the trigger's condition (a) is satisfied by this case
study's close regardless of the flip's verdict -- success or honest
analytic failure, either way with the corpus in the record.

## The brief (frozen)

- Part: 100 x 60 x 5 mm flat part. The 180 deg flip happens about a
  horizontal axis perpendicular to travel, which is an in-plane
  rotation of the part's 100 x 5 mm cross-section in the machine plane;
  the 60 mm width is out-of-plane, declared as such per the planar
  scope-control precedent. In-plane corner sweep radius about the
  centroid: sqrt(50^2 + 2.5^2) = 50.0624 mm (the folded correction; the
  first draft's ~58 mm was the 100 x 60 face diagonal -- an
  out-of-plane rotation model that contradicts the brief).
- Layout: symmetric handoffs at physical x = -130 and +130 mm, both on
  the carry plane at y = 50 mm (same height: a flip about the part's
  centroid swaps faces without moving the center); mid pose at x = 0.
  Normalization: 1 normalized unit = 100 mm, the OMTS task-layer
  convention declared by both recorded case A/B task documents
  (desk-checked in both yamls at staging; the bbox-diagonal basis is
  the six-bar research-corpus layer and is not mixed in).
- Orientations: 0 deg at handoff 1, 90 deg (vertical) at the mid pose,
  180 deg at handoff 2. The mid pose deliberately forces the flip
  through the vertical -- the four-bar's worst transmission window is
  the demand, not an accident.
- Tolerances: position 1.5 mm (0.015 normalized), orientation 1.5 deg.
- Mass: ~31.5 g, labeled placeholder with its derivation: a solid part
  of the declared dimensions (30 cm^3) at ABS nominal density 1.05
  g/cm^3 -- a placeholder with lineage is a derivation, not a picked
  number. Mass is recorded context for the later payload/grasp and
  force-closure residues; it is not a demand of this run.
- Rate and capacity: unrated, as in cases A/B.
- Search: the same portfolio and seed as cases A/B (seed 101) --
  deliberate comparability; the instrument is numerically identical to
  case B except for the orientation column of the demand.

## Scope (frozen)

- Single flipper mechanism at the three declared poses first. The
  transport + flip + transport line is a declared composition
  follow-up: the sync machinery stars on a stage where the flipper's
  family question is already closed. Handoff timing, grasp/release and
  handoff dwell are the line's business, unrated here.
- Payload-frame boundary: the part is modeled as rigidly mounted to
  the coupler point (centroid + orientation) and demanded at the
  handoff poses. Grasp compliance, release timing and dwell are out
  of scope. The rigid-mount convention is the same representation
  question the B2 generalization diagnosis (mounting-angle
  consistency on the four-bar niche) is diagnosing: this failure
  digest is B2's declared second data point, and B2's answer informs
  how the capability step declares the mounting offset. The two
  workstreams touch at that seam without either absorbing the other.
- Preview question for the capability step, noted now so it does not
  arrive mid-capability: a rigidly mounted 100 mm part sweeping a
  ~100 mm diameter disc in-plane is the dominant geometry of this
  design, and the case A/B collision machinery knows link capsules,
  carrier rectangles and pivot discs -- not payload bodies. The
  capability step's family design will need the part modeled as a
  collision body (or a declared deferral with trigger). Body
  geometry enters the framework before grasp mechanics do.

## Fold record (the opening debate round)

Actor's round (relayed by Jean) and critic's round (relayed by Jean)
were folded by the boss; both rounds largely endorsed the brief and
the instrument, with the critic's two factual catches adopted as
corrections. Nothing was withdrawn this round. The fold:

1. Corpus as design requirement (actor, critic-endorsed, adopted):
   the flipper's recorded outcomes must be a machine-readable
   solution corpus (parameter vectors, demand points, gate results as
   data rows), emitted from the first digest onward. The retroactive
   emitter over the recorded case A/B runs (frame-sweep precedent:
   pure transformation, no reruns) is declared as its own future job;
   it is not built here.
2. Corner-sweep correction (critic catch #1, adopted): 50.0624 mm
   in-plane, not ~58 mm -- the actor's 58 mm figure was the 100 x 60
   face diagonal, which only sweeps for an out-of-plane rotation that
   contradicts the actor's own correct in-plane clarification. Two
   self-consistent numbers from different rotation models; the
   envelope derivation uses the corrected figure.
3. Normalization (critic catch #2, settled by desk-check): the actor's
   "1 unit = 100 mm" was labeled the case-B convention; the critic
   flagged that case B's six-bar research-corpus layer normalizes by
   the bbox diagonal. The desk-check found both task-layer yamls
   (case A dwell_station and case B gap_transfer) declare 1
   normalized unit = 100 mm -- the diagonal basis is the
   research-corpus layer. Resolution: 1 unit = 100 mm at the task
   layer (task-layer cross-comparability with A/B), and the critic's
   real requirement adopted in full anyway: every corpus row carries
   an explicit units block, and every corpus carries a pinned
   corpus_schema_version that consumers pin against (the PR-A
   result-units lesson). The rows also carry the demand-point units
   and the per-row scorecard verdict, per the critic's Q4 delta.
4. Single mechanism first, unambiguous (actor, critic-endorsed,
   adopted): opening with the line would confound family capability
   with composition.
5. Payload-frame boundary (actor, critic-endorsed, adopted), with the
   B2 seam connection and the part-body collision preview question
   (critic delta, adopted).
6. Mid pose at 90 deg (actor, critic-endorsed): the worst window as
   demand.
7. Mass placeholder with derivation (actor, critic-endorsed): ~31.5 g
   solid ABS nominal, within the actor's 30-40 g band.
8. Predictions D1-D4 frozen below, including the critic's third leg
   on the D3 diagnostic (at-pose vs anywhere vs demanded).
9. Sequencing note carried: B2's frozen answer schema is committed
   before B2 runs, and this digest's failure record is a declared
   input to B2 when it lands -- parallel work with a linkage, not a
   serialization.

## The instrument

`flip_digest.py` (this directory) scores the flip demand on the
recorded engine traces, with `jobs/corpus_emitter.py` as the shared
corpus writer:

- Kinematics: the parity-tested `four_bar_skeleton` embedded verbatim
  from src/mechanism_generator/omts/geometry.py at main 11823908
  (the dwell digest precedent), with the same base_angle
  radians -> degrees input boundary.
- Witness: the engine's recorded position errors (error_1..3 at
  phase_1..3_deg) must be reproduced within 1e-6 normalized for every
  row -- fail-closed. Disclosed plainly: the witness covers position
  only; orientation errors are not recorded per row in
  all_candidates.csv, so orientation is scored on the rebuilt trace at
  the same recorded phases (computed, never transcribed).
- Orientation convention: docs/three-pose.md -- directed coupler A to
  B, atan2 of the skeleton's own a and b, errors wrap the full turn
  (a 180 deg demand is exactly 180 from either side).
- Grid: 7200 unique samples per cycle, exactly 0.05 deg per interval,
  asserted at run time (off-by-one guard).
- Determinism: no clocks, no randomness, sorted keys -- run the digest
  twice and diff the reports AND the corpus files; byte-identical is
  the control.
- Fail-closed everywhere: missing files/columns, reproduction
  mismatch, undefined assembly on a full-cycle trace, broken grid
  arithmetic, or an invalid corpus row aborts the whole run.

## The corpus schema (the design requirement)

One row per candidate, scored or excluded, written by
jobs/corpus_emitter.py as JSON Lines plus a flat CSV projection:

- corpus_schema_version ("1"), task_id, family, candidate_id,
  direction, branch_sign.
- parameters: the named parameter vector as the engine recorded it
  (base_angle in radians -- engine convention, stated in the units
  block).
- solution_status: scored / excluded:<reason>.
- gates: per-target position and orientation errors with tolerances,
  margins and pass/fail, plus the declared diagnostic data rows
  (d3a, d3b, transmission angles).
- verdict: self-contained per row (pass_all_gates /
  fail:<class>-dominant / excluded:<reason>).
- demand: the three targets with positions, orientations, tolerances
  and the demanded swing.
- units: the explicit units block (position basis 1 unit = 100 mm,
  angle deg, parameter notes; the six-bar research-corpus diagonal
  basis called out as never-mixed-without-redeclaration).
- provenance: job, task id, seed (101), run id, source commit (the
  digest takes the merged main sha as its second argument;
  claim-only-what-exists).

The emitter is fail-closed (a row missing a field, a non-finite
number, or a wrong schema version aborts the whole emission before
anything is written) and its byte-identical two-run behavior is part
of the scorecard. Corpus files land inside the run root under
corpus/ and are recorded outcome: this JOB.md's outcome section will
reference them by the sha256 hashes the digest prints.

## Frozen prediction scorecard (written before the run)

- D1 (primary): zero selected candidates. Reason: three simultaneous
  pose+orientation demands including a 180 deg coupler swing is far
  outside the pool's demonstrated envelope (the case A/B failure
  records). Read as: candidates meeting all six gates (three
  position, three orientation) at the recorded matched phases: 0
  expected.
- D2: the binding rejection class is orientation-coupled, most likely
  transmission collapse at the 90 deg vertical mid pose. Read as: the
  pool's binding class (orientation-dominant vs position-dominant, in
  tolerance units) plus the transmission-angle data at the mid-pose
  phase and the cycle minimum. Branches: as-predicted
  (orientation-dominant pool-wide); MIXED (position-dominant
  candidates exist -- read before staging); UNEXPECTED
  (position-coupled pool-wide -- read before staging).
- D3 (three-leg diagnostic): D3a = the pool's best achievable
  orientation swing at the demanded positions (samples within
  position tolerance of handoff 1 paired with samples within
  tolerance of handoff 2, best wrapped spread; declared upper-bound
  pairing, position tolerance only); D3b = the pool's best free
  swing anywhere (unwrapped full-cycle coupler-angle range); against
  the demanded 180 deg. Branches: family-limited (pool D3b < 180 --
  the pool cannot swing, the plateau question); placement-limited
  (pool D3b >= 180 but D3a does not reach 180 -- a coupler-curve
  property question); UNEXPECTED (D3a reaches the demand -- read
  before staging).
- D4 (control): any candidate passing all six gates refutes D1 and is
  the honest result -- recorded as data, never as an error.

Frozen conventions carried from cases A/B: stated branches; fail-closed
digest discipline; frozen predictions with reasons; per-seed no
pooling; negative control (D4); determinism byte-identical;
construction claims machine-verified; claim-only-what-exists; the
machine line recorded as-run; review card in the PR body; no CI
polling (Jean merges); outcomes data-never-rewritten. Plus the two new
corpus controls: the emitter is fail-closed, and the corpus files are
hashed into the outcome record.

## Machine step (in order, maintainer-local, after merge)

1. `omts validate examples/omts/flip_station.omts.yaml`
2. `omts adapt examples/omts/flip_station.omts.yaml --output-dir generated/flip-station-failure-01`
3. Preflight: read the prepared plan (targets CSV, arguments) against
   the pinned brief above before spending search budget.
4. Execute the prepared plan's generated runner (the engine run;
   crank direction either -- two complete search trees, fresh output
   root under runs/flip-station-failure-01/).
5. `python3 jobs/flip-station-failure-01/flip_digest.py <fresh-run-root> <merged-main-sha>`
6. Run the digest a second time on the same root and diff both
   reports and both corpus file pairs -- byte-identical is the
   determinism control.
7. `python -m pytest tests/test_flip_station_example.py` (the staging
   smoke test).
8. Record the outcome in this JOB.md against the frozen scorecard,
   referencing the corpus files by their sha256 hashes. The
   D1-D4 verdicts are read from the digest report; the engine's own
   selection counts are read from the run review and recorded
   alongside.

After this job closes with its corpus in the record AND B2 has a
recorded answer in its frozen schema, the strategy trigger fires (see
docs/strategy.md): the next staged item is B1 admission-gate work
unless Jean explicitly overrides with a recorded reason.
