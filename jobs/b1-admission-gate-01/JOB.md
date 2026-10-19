# Job b1-admission-gate-01: the B1 admission gate -- the frozen
first-run gate for the learned-proposal line (gate freeze; no run
claimed)

## Why this job exists (the fired trigger and the fork, recorded)

- The strategy trigger FIRED (docs/strategy.md, frozen): condition
  (a) the flipper case study closed with its machine-readable
  solution corpora (flip-station-failure-01: 36 rows, schema 1,
  jsonl fbea9568 / csv 01dd9c06; flip-station-capability-01: the
  corpus of record, 838 rows, schema 1.1, jsonl sha256
  cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c,
  csv sha256
  4edb232c22d58fbab82aa83f3852eb04ec0a5e8544b8fd12ca4b5c08b7679401)
  and condition (b) B2 recorded its answer in its frozen schema
  (DATA-LIMITED, merged as PR #74, main 566b7c6). Both hold: past
  the tripwire, further harvesting is deferral, not
  evidence-gathering.
- The fork (the owner's relayed decision, recorded): the B1
  admission-gate work and the six-bar flip line BOTH proceed, B1
  staged FIRST, not an override. Two recorded rules live at once
  (the tripwire names B1; case C's C5 branch fired the six-bar
  alternative); parallel-with-B1-first honors both. The six-bar
  line's own next staging (the motion JSON desk derivation,
  flip-station-sixbar-01) runs in parallel; neither line waits on
  the other.
- This job freezes the gate the first learned-proposal run will be
  graded against: the operational form of the seven-item frozen
  minimum in docs/strategy.md. No item is amended, weakened, or
  silently extended; each becomes a graded admission row (A1-A7)
  with its required report cells.

## Claim-only-what-exists (declared at freeze)

- No training run, no trained artifact, no held-out score, and no
  head-to-head number exists at this staging, and none is implied.
  The rows below define what the FIRST run must REPORT and how it
  is graded -- nothing more. The instrument (training script,
  proposer architecture, run commands) is the run staging's work,
  declared and frozen there BEFORE any run, per the standing
  freeze-first discipline.

## The first-run design decisions (frozen at this desk)

- PARAMETER SPACE FIRST: the flip-station cam parameter space --
  the dual-groove plate-cam family swept and recorded in
  flip-station-capability-01. Reasons, recorded: it is the only
  recorded corpus at scale with exact ground truth on the same
  demands (analytic synthesis is the closed-form supplier for
  this family) and graded gate results as data rows; it is the
  strategy doc's ideal regime (small, bounded, exact ground
  truth). The six-bar space is SECOND, recorded honestly as not
  yet available: the six-bar flip line (flip-station-sixbar-01)
  has not run, so no six-bar flip corpus exists to train on.
  When one exists it enters through this same gate unchanged
  (the admission test), never by amendment. No case B row trains
  the first run (a different parameter space; mixing spaces is a
  2.0-scale decision, not a first-run freedom).
- CORPUS LINEAGE PIN: the training corpus is the corpus of record
  cited above, consumed read-only with its hashes. The schema
  reference in this gate pins the ADDITIVE-ONLY SUCCESSION RULE
  (schema >= 1.0 per the frozen succession rule), NEVER a version
  number: an additive 1.x bump (e.g. six-bar line additions)
  never invalidates this gate and creates no merge-order
  dependency between the lines (the fork's recorded coupling fix;
  the near-miss -- a version-number pin -- is recorded in the
  audit trail). A 2.0 meaning change fails closed: the gate
  re-stages before any run against it.
- TRAIN/HELD-OUT SPLIT (frozen rule; counts computed never
  transcribed): the training rows are the JSONL lines of the
  corpus of record in emission order, 0-based index i; a row is
  HELD OUT iff (i mod 5) == 4; all other rows train. The rule is
  frozen here so it cannot be tuned after any result exists; the
  exact held-out count is computed at the run and recorded as
  data. Held-out rows are never trained on; a leak is a recorded
  FAIL of the A2 provenance cell.
- HEADLINE METRIC: distance from closed-form on held-out demands.
  For each held-out row, the proposal's answer on that row's
  demand is scored against the recorded closed-form solution on
  the same demand, in the corpus's declared units; the distance
  is reported per-row plus its median and worst over the held-out
  set, computed publicly by the existing instruments. The exact
  distance function is declared and frozen in the RUN STAGING
  (before any run) and may not change after any run exists; the
  A2 head-to-head table carries both numbers per the frozen
  minimum -- the metric never replaces the table.
- OOD PROBE: the run staging declares ONE out-of-distribution
  demand with its provenance (why it sits outside the training
  corpus's demand distribution, stated against the corpus, not
  asserted), frozen before the run. The recorded failure
  precedents it answers to: the learned initializer failure (the
  PR #44 record) and the chooser restarts (the six-bar runs).
  The learned component's fallback behavior on the probe is
  recorded AS-IT-RUNS; silence, degradation, and crash are all
  data, never errors.

## The frozen admission scorecard (A1-A7)

Each row is graded PASS / FAIL / NOT-REPORTED as data. The run is
ADMISSIBLE iff every row is reported and A1 holds. An admission
failure is a recorded finding about the line, never a silent
rewrite. A first admissible run does not need to win; it needs to
be gradeable.

- A1 ZERO INSTRUMENT MODIFICATION (the reciprocity/admission
  test): the proposal is graded by the existing instruments
  UNMODIFIED; the instrument-modification count row is expected 0
  and scored (the flip-station-capability-01 precedent). A
  nonzero count is a recorded finding about the instruments per
  the frozen principle, and the run is NOT admissible as a B1
  first run.
- A2 CLOSED-FORM HEAD-TO-HEAD: scored against the recorded
  analytic solutions on the SAME recorded demands (the held-out
  rows); BOTH numbers go in the table (learned and closed-form),
  per the frozen minimum. Beating or honestly losing to
  closed-form both grade PASS; hiding either number grades FAIL.
- A3 DETERMINISM CONTROL: fixed seeds declared before the run;
  declared initialization; byte-identical reruns (the recorded
  standard: two redirected runs, external diff EMPTY, exit 0, the
  in-process check recorded; the flip-station-capability-01
  precedent for a botched run-2: recorded as-run, rerun cleanly,
  the clean pair is the record).
- A4 SUPPLIER-OUTPUT LABELING: every output of the line is
  labeled a SUPPLIER OUTPUT, not a generator capability, until
  the line wins a head-to-head (beats closed-form on the headline
  metric over the held-out set, read off the A2 table). The label
  change is a recorded event with its numbers, never prose drift.
- A5 OOD CONTROL: the frozen OOD probe exercised with its
  fallback behavior recorded as-run.
- A6 INITIALIZER HEAD-TO-HEAD: the proposal is ALSO compared
  against the existing non-learned initialization on the same
  seeds; contribution is measured, not assumed (the recorded
  precedent: a learned component can be worse than random
  restart -- the chooser-restart finding).
- A7 LINEAGE RECORDING: the training corpus's provenance (which
  recorded runs, which families, with the corpus hashes) and the
  trained artifact's identity hash go in the record (the
  weights-recording precedent); the artifact hash is recorded
  before any score is read.

## Machine step (spec; NOT this staging)

- The run staging (the next staging on this line) carries the
  instrument: the training script and the proposer architecture
  declaration, the exact distance function, the OOD probe with
  its provenance, the seed set, and the run commands -- all
  frozen before any run.
- The run follows the recorded standard: the-hub, the motion venv,
  repo root; the source commit is the merge that carries the run
  staging; two redirected runs, byte-identical; the corpus
  consumed read-only; the artifact identity hash and the A1-A7
  rows recorded in the outcome, read against this frozen
  scorecard.
- This staging carries NO script and claims NO run. Docs-only: no
  machine step before or after this merge.

## Status

Gate frozen; run staging pending. Parallel line per the fork: the
flip-station-sixbar-01 motion JSON desk derivation.
