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

## Run staging (frozen before any run; 2026-10-20)

This section is the run staging the gate's machine-step spec named:
it carries the instrument and freezes every first-run decision
BEFORE any run, per the standing freeze-first discipline. No run is
claimed here, and none is implied; the first run is the owner's
machine step below.

- THE DECLARED TASK (honest scope): the groove solution map of the
  recorded cam space -- per groove, (groove id, plate angle) to
  the exact closed-form groove point (gx, gy) under the RECORDED
  chosen design (d=0.2 / C_y=0.0), 1 unit = 100 mm. The solution
  rows are the corpus's 720 groove_sample rows (emission indices
  27-746 of 838). This is a curve-fitting supplier on one recorded
  design of one recorded family -- not a general mechanism
  generator; the A4 label states exactly that.
- THE INSTRUMENT: jobs/b1-admission-gate-01/b1_proposer_train.py
  (pure stdlib, ASCII, Python 3.10+; its sha256 is recorded in the
  PR that carries this staging and verified by the fetch-back
  round trip).
- PROPOSER ARCHITECTURE (frozen): per-groove Fourier-feature ridge
  regression -- features [1, cos(k*x), sin(k*x)] for k=1..24 (49
  features; x = radians of the plate angle), ridge lambda 1e-8 on
  every diagonal (bias included), closed-form normal-equation solve
  by Gaussian elimination with partial pivoting. No stochastic
  component, no initialization (exact solve; seed-free by
  construction). DESIGN-INVARIANT: the training solution rows span
  the single chosen design, so design features are deliberately
  excluded (ill-conditioning avoided); growth to multi-design
  corpora is a future corpus decision, never an amendment here.
- THE SPLIT: the gate's frozen rule unchanged -- 0-based JSONL
  index i held out iff i mod 5 == 4; counts computed at the run,
  never transcribed. Non-solution held-out rows are counted and
  recorded as not scoreable for this task, never silently dropped.
- THE EXACT DISTANCE FUNCTION (frozen): Euclidean in task-layer
  units, per-row plus median (mean of the two central order
  statistics when even) plus worst over the held-out solution
  rows; presented also in mm and as a ratio to the 0.015-unit
  (1.5 mm) handoff tolerance -- presentations of the same
  function, never gates.
- A1 OPERATIONALIZED: corpus sha256 pin
  cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c
  and instrument sha256 pin
  72989f8a1183647f5cbf47c6db92b0cdc63eead355acb25f1dd42adedc06447b
  (50,265 bytes) verified at the run; a pin match IS the
  zero-modification evidence (mod count 0); any mismatch fails
  closed before a byte is trained.
- REPRODUCTION WITNESS (the PR #62 dwell-digest lesson applied
  forward): every groove_sample row is re-derived through the
  instrument's own groove_point before training (tolerance 1e-9,
  fail-closed); the chosen design is DISCOVERED from the corpus
  (the chosen=true sweep gate row, cross-checked against the
  design_parameter rows) -- nothing is hardcoded.
- OOD PROBE (A5, frozen with its provenance): groove_1 at plate
  angle 90.0 deg under design (d=0.4, C_y=0.25). Provenance,
  stated against the corpus: every training solution row carries
  the single chosen design d=0.2 / C_y=0.0, and the model is
  design-invariant, so the probe sits outside the training
  corpus's solution distribution in DESIGN; the angle is
  in-distribution, isolating the design shift. The probe design
  lies inside the recorded SWEEP_D x SWEEP_CY envelope but exists
  there only as a gate aggregate row (never sampled; that row is
  itself held out at index 14). Fallback: NONE is wired in the
  first run (frozen); behavior is recorded as-run. Frozen
  expectation (a prediction, never a gate): gross degradation,
  mirroring the PR #44 initializer OOD failure class.
- BASELINE SEED SET (A6): 580000050, 580000051, 580000052 -- a
  seeded random-restart supplier, uniform in the per-groove
  TRAIN-split bounding box, one restart per held-out row, draws
  in corpus order (Mersenne Twister via random.Random); the
  learned model itself is seed-free (declared above).
- A7 ORDER (code-enforced): the trained artifact is written to
  runs/b1-admission-gate-01/b1_proposer_v1.json and its sha256 is
  printed BEFORE any score is computed. The artifact embeds the
  run's source commit, so its identity hash is per-run by design
  (lineage), never a rehearsal constant.
- A4 READING: on a distance-to-closed-form metric the closed-form
  scores 0 by definition, so the learned line can at best tie --
  the SUPPLIER OUTPUT label stands and the label-change event
  remains defined (with its numbers) and unfired.
- FROZEN PREDICTIONS (read at the run; never gates): P1 the
  learned model does not beat closed-form (metric definition;
  lean HELD); P2 median held-out distance < 0.015 units (lean
  HELD); P3 the OOD probe distance exceeds the worst held-out by
  at least an order of magnitude (lean HELD); P4 every baseline
  seed's median exceeds the learned median (lean HELD).
- MACHINE STEP (the owner's; the recorded standard): from the repo
  root, the motion venv, Python 3.10+:
  python jobs/b1-admission-gate-01/b1_proposer_train.py
  --source-commit <merged-40-hex-sha> > run1.txt (twice), then
  diff the pair -- empty and exit 0 is the record; paste the
  report back for the A1-A7 reading. If runs/flip-station-
  capability-01/ is absent, regenerate the corpus read-only first
  (python jobs/flip-station-capability-01/flip_capability.py
  --source-commit 9c9fd6f9f1724e683ed053f621f95fe5a283425a) and
  verify the jsonl sha256 against the pin above; the script also
  fails closed with exactly this instruction if the corpus is
  missing.
- STAGING REHEARSAL (disclosed; NOT the run of record): the corpus
  of record was regenerated from the merged instrument at staging
  and matched the pinned sha256 cdac1413 exactly (838 rows), so
  the instrument is validated against real corpus bytes. The
  script then ran twice on the regenerated corpus: byte-identical
  pair, exit 0, in-process check IDENTICAL. Rehearsal numbers
  (superseded by the run, disclosed for honesty): witness 720/720
  exact; 144 held-out solution rows (72 per groove; 23
  not-scoreable held-out rows counted and recorded); median
  held-out distance 8.322194e-06 units (0.0008 mm), worst
  5.650397e-05 units; baseline medians 1.051126e+00 / 1.170167e+00
  / 1.133789e+00 units; OOD probe distance 5.000776e-02 units
  (5.0008 mm; 885x the worst held-out) -- the frozen degradation
  expectation showed up in the rehearsal. All four frozen
  predictions' leans held in the rehearsal. The fail-closed paths
  were exercised at staging and all failed closed with exit 2
  (missing corpus; tampered corpus byte; tampered groove value
  under a relaxed pin, caught by the witness; chosen-design
  tamper, caught by the cross-check; schema 2.0, caught by the
  succession rule; tampered instrument byte; usage errors exit 1).
- CLAIMED: nothing. A first admissible run needs to be gradeable,
  not to win; the expected outcome is an honest loss to
  closed-form plus the OOD degradation datum, both as data.

## Recorded outcome (2026-10-20)

The run of record (the-hub, the motion venv, Python 3.14.4, repo
root, source commit cf1ad7e9d6d41e989225d0a70cc7796731c0efd9 --
the PR #81 merge): two redirected runs, external diff EMPTY, exit
0 both. Honest note, recorded as-run: the first attempt's run1.txt
was a stale leftover of the dualcam-lever-transfer-06 audit (an
earlier redirected run of a different job in the same working
tree); the clean rerun completed the pair, and the clean pair is
the record (the flip-station-capability-01 precedent). The report
reproduced the staging rehearsal to every printed digit -- the
deterministic prediction held exactly; the only per-run value is
the artifact hash, by design (it embeds the source commit).

Scorecard, read against the frozen sections above, numbers from
the run's own printed report:

- P0 PIN CHECKS: corpus sha256 cdac1413...39be6c and provenance
  9c9fd6f9...3425a PIN MATCH; instrument sha256 72989f8a...06447b
  PIN MATCH; schema succession accepted (additive 1.x, major 1).
- P1 CORPUS AND SPLIT (counts computed, never transcribed): 838
  rows; 720 groove_sample rows -- groove_1 288 train / 72 held
  out, groove_2 288 train / 72 held out; held-out total 167 (144
  solution rows; 23 not-scoreable kinds counted and recorded,
  never dropped).
- W WITNESS: 720/720 groove_sample rows re-derived exactly, worst
  deviation 0.000e+00 (tol 1e-9): PASS; the chosen design
  discovered from the corpus (d=0.2 / C_y=0.00), cross-checked.
- T/A7: trained per-groove Fourier ridge (49 features, lambda
  1e-8, exact solve, seed-free); the artifact
  runs/b1-admission-gate-01/b1_proposer_v1.json sha256
  ceebf162c8d11a5c97f042735b76465bf34e304039c2a74b660e8ebc41745678
  written and hashed BEFORE any score was computed (the A7 order).
- A2 CLOSED-FORM HEAD-TO-HEAD (both numbers per row in the
  report): median held-out distance 8.322194e-06 units (0.0008 mm;
  0.0006 x the 1.5 mm tolerance), worst 5.650397e-05 units
  (0.0057 mm; 0.0038 x). An honest loss to closed-form, recorded
  as data -- the expected first-run outcome.
- A6 INITIALIZER HEAD-TO-HEAD: baseline seeded random-restart
  medians 1.051126e+00 / 1.170167e+00 / 1.133789e+00 units (seeds
  580000050/51/52); the learned median (8.322194e-06) is below
  all three -- the learned supplier beats the random-restart
  baseline on every seed while losing to closed-form, exactly the
  supplier-grade picture the gate was built to surface.
- A5 OOD PROBE (design shift, frozen provenance): groove_1 at
  plate angle 90.0 deg under d=0.4 / C_y=0.25; closed-form
  (0.65000000, 0.00000000); learned (0.70000776, 0.00000005) --
  the design-invariant model answers the CHOSEN design's point.
  Probe distance 5.000776e-02 units (5.0008 mm; 3.3339 x
  tolerance), 885.0308 x the worst held-out distance; no fallback
  wired; gross degradation exactly as the frozen expectation
  predicted (the PR #44 OOD failure class, reproduced as data).
- A1 ZERO INSTRUMENT MODIFICATION: pin matches are the evidence;
  modification count 0. ADMISSION HOLDS.
- A3 DETERMINISM: seed-free exact solve (declared); external pair
  diff EMPTY, exit 0; in-process check IDENTICAL.
- A4 SUPPLIER-OUTPUT LABELING: the label stands (no head-to-head
  win; on the distance metric closed-form scores 0 by
  definition). The label-change event remains defined and unfired.
- Frozen predictions P1-P4: all HELD (P1 honest loss, metric
  definition; P2 median 8.322194e-06 < 0.015; P3 OOD ratio 885
  >= 10; P4 all three baseline medians exceed the learned).

ADMISSION VERDICT: the run is ADMISSIBLE (every A-row reported;
A1 holds). It is the B1 line's first admissible run: gradeable,
not a win -- an honest loss to closed-form in-distribution, a
clear OOD degradation datum, and a supplier that beats random
restart on every seed while losing to closed-form. Label: SUPPLIER
OUTPUT (LEARNED -- no head-to-head win).

Machine line: the-hub, Intel i5-10400T, Python 3.14.4, the motion
venv; the owner pasted the run report back and the numbers above
are the run's own printed output.

## B1-line next-step decision (2026-10-20): the fallback
re-probe frozen; Direction 2 committed with its disciplines;
Direction 3 adopted as labeling, its verdict framing rejected

- THE DECISION (the owner's relay of the actor/critic round; the
  recorded single-word answer: Direction 1, with Direction 2
  committed behind it): wire the OOD fallback and re-probe the
  frozen design-shift case FIRST; then the synthetic budgeted
  expansion; the recorded supplier run stays as data throughout
  and the case-study loop advances on its own queue.
- A BOSS CORRECTION, recorded for honesty (claim-only-what-
  exists): the round's "partial admission" framing is NOT the
  frozen text. The gate froze A5 as "the frozen OOD probe
  exercised with its fallback behavior recorded AS-IT-RUNS",
  and the run staging froze "Fallback: NONE is wired in the
  first run (frozen)" -- both were honored by the run of
  record. The first run is a COMPLETE admission; nothing is
  reopened. The round's spirit is still right: A5's purpose is
  a characterized fallback behavior, and the recorded datum is
  a NO-FALLBACK degradation. The fallback-equipped re-probe is
  therefore the line's NEXT STAGED ITEM -- a continuation the
  recorded OOD datum demands, not the completion of an
  incomplete admission.
- THE FALLBACK RE-PROBE FREEZE (frozen before any run; the
  instrument script is the NEXT staging after this merge, per
  the gate-then-run-staging pattern; NO script and NO run is
  claimed here):
  - FALLBACK SEMANTICS (frozen): a DESIGN GATE in front of the
    trained supplier. The demand carries its design (d, C_y) as
    declared context. If the demand's design is the trained
    design (d=0.2 / C_y=0.0, DISCOVERED from the corpus as at
    the first run, never hardcoded), the learned supplier
    answers and the output is labeled LEARNED. If the design
    differs, the supplier answers from the closed-form supplier
    (the instrument's own groove_point) and the output is
    labeled FALLBACK: CLOSED-FORM (design mismatch), the
    mismatch recorded. Both branches answer every demand;
    nothing is silently dropped. The fallback is a declared
    supplier behavior, never a gate value.
  - THE RE-PROBE (frozen): the SAME OOD probe as the first run
    (groove_1, plate angle 90.0 deg, design d=0.4 / C_y=0.25,
    provenance unchanged), run through the fallback-equipped
    supplier; the un-fallbacked learned answer is ALSO recorded
    and must match the first run's recorded answer digit for
    digit (a reproduction check on the supplier).
  - THE B2-SIGNATURE TEST (frozen rubric): classify the
    recorded design-shift failure against B2's diagnostic
    vocabulary: (a) REPRESENTATION-SCOPED -- an artifact of
    representation or convention, rescuable by a representation
    change (B2's case-B artifact class); (b) DATA-LIMITED -- a
    genuine coverage limit (B2's case-C answer class);
    (c) NEW SIGNATURE -- neither; a recorded finding either
    way. The classification records which representation the
    supplier actually uses against B2's answer. Frozen
    prediction (never a gate): (b) DATA-LIMITED -- the
    architecture is design-invariant BY FREEZE (design features
    deliberately excluded at the run staging), so no
    representation rescue exists to test; the design channel is
    absent from the function, a coverage limit by construction,
    matching B2's case-C class. If confirmed: the fallback
    wiring is a bandage and design coverage (Direction 2's
    growth, or a design-conditioned representation as a future
    corpus decision) is the disease. If refuted: a genuinely
    new failure mode, recorded as a finding that redirects
    Direction 2.
- DIRECTION 2, COMMITTED WITH ITS DISCIPLINES (frozen as
  requirements on the expansion freeze document; that document
  is staged only after the re-probe's answer exists -- the
  answer redirects the expansion):
  - SYNTHETIC ANALYTIC EXPANSION ONLY: exact ground truth from
    the parameter spaces (analytic synthesis), no new case
    studies or briefs; the fired tripwire's mandate is
    generation investment, never harvest.
  - ONE FREEZE DOCUMENT BEFORE ANY GENERATION (the critic's
    first delta, adopted): the expansion budget (declared
    synthetic demand count, coverage declaration across the
    parameter spaces, stated stop condition), the
    train/held-out split rule, and the coverage map -- which
    demand cells train, which are held out, and a declared
    interpolation-vs-extrapolation split among the held-out
    cells -- frozen as ONE document BEFORE the first synthetic
    point is generated. Reason recorded: with one generator
    drawing both splits, an after-the-fact split measures the
    generator's coherence, not the supplier's generalization
    (the retune-on-holdouts rule of the weights decision,
    extended to holdout creation).
  - PRE-DECLARED COMPARISON AXES (the critic's second delta,
    adopted): on the accuracy axis the head-to-head is
    preordained (closed-form synthesis is exact, instant, and
    free; a distance-only comparison could not come out
    otherwise), so the informative axes are named BEFORE the
    expansion is designed and the budget is allocated to power
    them. Declared axis candidates: feasibility prediction (on
    demands where the closed form is infeasible, does the
    supplier predict infeasibility -- the coverage question);
    constrained-variant warm-start (where constraints break
    the clean closed form and search reappears, does a learned
    initialization beat random restart -- the PR #44 failure
    mode's redemption path); cost under demand variety. The
    critic's frozen prediction, recorded: the supplier's honest
    value in this regime lives in the first two axes, not in
    accuracy.
  - BOTH-DIRECTIONS HONESTY: the expansion exists so the
    head-to-head is POWERED, not so it passes; a supplier that
    honestly loses to closed-form on a properly-powered
    head-to-head is a successful B1 outcome -- the framework
    graded a supplier; that is the product working. "Grow
    toward the head-to-head" may never become "train until we
    win" (the budget-with-stop-condition exists for exactly
    this).
- THE STANDING STATE (Direction 3's housekeeping adopted as
  labeling; its verdict framing rejected): the recorded
  supplier run stays as data, never rewritten; the grade stays
  open by design (admission item 4 working as frozen, not
  evidence of failure); one run is never a verdict in either
  direction (the -02 lesson: near-miss is not structural, and
  one run is not a verdict). The supplier line advances on its
  own queue (the fallback re-probe, then the budgeted
  expansion); the case-study loop advances on its own (the cam
  class ruling under its frozen schema; the six-bar line under
  its own recorded triggers) -- neither blocks nor waits on the
  other.

## Status

Run recorded (2026-10-20) -- the first admissible B1 run: an
honest loss to closed-form in-distribution (median 8.3e-06
units), a clear OOD degradation datum (885x the worst held-out),
and the learned supplier beats the random-restart baseline on
every seed; SUPPLIER OUTPUT stands. Next-step decision recorded
and frozen (2026-10-20, this staging): Direction 1 -- the
fallback re-probe (frozen above; the instrument script is the
next staging) -- with Direction 2 (the synthetic budgeted
expansion under its frozen disciplines) committed behind it; the
standing state is labeling, not a verdict. No script and no run
claimed here.
