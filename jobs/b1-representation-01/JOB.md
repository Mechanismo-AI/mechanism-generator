# Job b1-representation-01: the design-conditioned representation freeze
-- the ONE freeze document before any training of the new map (the
disease treatment; no run claimed)

## Why this job exists (the recorded mandate, carried)

- The B1 two-candidate decision (jobs/b1-admission-gate-01, the
  "The B1 two-candidate decision (2026-10-20)" section, frozen on
  main at PR #89) ruled BOTH, in order: (2) the warm-start
  transfer, landed complete -- freeze (PR #90), instrument (PR
  #91), and the run of record (merged sha 5eeaee79) recorded in
  the b1-warmstart-transfer-01 row; then (1) the
  design-conditioned representation as the next committed B1
  freeze through the full gate. The sequencing teeth name THIS
  document as that staging unless the owner overrides with a
  recorded reason; no override is recorded, and the teeth hold.
  This is (1) -- the disease treatment, never "one more
  warm-start experiment" (the tripwire's exact deferral shape).
- THE DISEASE, MEASURED THREE SEPARATE WAYS (the record this
  freeze treats): B2's DATA-LIMITED answer (the re-probe run of
  record -- the fallback wiring is a bandage, design coverage is
  the disease); the 885.0308x probe (groove_1, 90.0 deg, d=0.4 /
  C_y=0.25 -- the recorded design-shift case); the 17,930.5049x
  scale confirmation (the expansion run of record: extrapolation
  median 1.500000e-01 vs interpolation median 8.365633e-06,
  worst 0.2000693 units = 13.3380x the 0.015-unit tolerance; the
  extrapolation error IS the design offset itself). The PR #44
  initializer lineage, measured: the learned initialization's
  value survives design extrapolation even while the learned
  answer's accuracy does not (the AX2 16/16 datum) -- the
  treatment is the answer's accuracy, not the initialization.

## Claim-only-what-exists (declared at freeze)

- NO design-conditioned model has been trained, NO synthetic
  point for this job has been generated, NO measurement of the
  new map exists at this staging, and none is implied. This
  document freezes the representation, the coverage map, the
  split rule, the success criterion with its numeric bar, the
  frozen prediction, and the grade-only rule BEFORE any training
  run, per the frozen discipline. The instrument is the NEXT
  staging (the gate-then-run-staging pattern); it implements
  this document and may not amend it.

## Home and placement, declared (the decision left this to the
staging)

- This job lives at jobs/b1-representation-01/, on the B1 line,
  because B1 owns the supplier and the redesign passes through
  its full gate. The consuming context is untouched: case study
  C stays CLOSED at its recorded outcomes; the transfer datum
  stands as recorded with its supplier-version scoping -- if
  this representation lands, the transfer measurement re-runs on
  it before that datum carries forward (the transfer instrument
  already froze the protocol, so the re-measurement is cheap
  and comparable).

## The design-conditioned representation (frozen spec)

- THE DESIGN CHANNEL (d and C_y as INPUTS, not just groove
  identity): per groove, the frozen per-groove Fourier map (the
  trainer's own builder carried: [1, cos(k t), sin(k t)] for
  k = 1..24 -- 49 features) EXTENDED with the design channel:
  [d, C_y] plus the first-order products [d cos(k t), d sin(k t),
  C_y cos(k t), C_y sin(k t)] for k = 1..24 -- 98 added features,
  147 per groove. ONE model per groove (two models), trained
  ACROSS the TRAIN design cells -- a redesign of the feature
  map, exactly the future corpus decision the expansion
  recorded, now taken through this gate, never silently around
  it. The ridge is the trainer's own closed-form solve with
  RIDGE_LAMBDA=1e-08 carried; the trainer is imported read-only
  and the new feature builder lives in the instrument.
- WHY FIRST-ORDER (the lineage, from the measured record): the
  expansion measured the extrapolation error as the design
  offset itself (the d=0.4 cells at 1.0e-01 -- the demanded d
  minus the boundary model's d; the d=0.5 cells at 2.0e-01, the
  same). A design channel gated multiplicatively onto the angle
  basis carries exactly the term that cancels a design-offset
  error to first order. Higher-order design terms are NOT added
  at this freeze; a second-order channel is a future
  finding-driven candidate, staged through this same gate,
  never a silent addition.
- TRAINING DATA: the coverage map's TRAIN design cells (6):
  d in {0.1, 0.2, 0.3} x C_y in {0.0, 0.25}, at non-held-out
  sample indices (the gate's frozen split rule carried: 0-based
  per-cell sample index i is held out iff (i mod 5) == 4).
  Every training row is synthesized at run time through the
  pinned capability instrument's groove_point, consumed
  READ-ONLY under its pin -- never stored, never transcribed.

## The coverage map (frozen; carried unchanged from the
expansion)

- TRAIN (6 cells): d in {0.1, 0.2, 0.3} x C_y in {0.0, 0.25}.
  The recorded chosen design (d=0.2 / C_y=0.0) is among them
  and is the reproduction anchor cell.
- INTERPOLATION held-out: the (i mod 5) == 4 samples within the
  6 trained cells -- angle-axis interpolation inside trained
  designs. Design-INTERPOLATION stays EMPTY by construction on
  the recorded grid (both admissible C_y values trained; every
  interior d trained) -- recorded honestly, carried.
- EXTRAPOLATION held-out ENTIRE (4 cells -- the disease class):
  d in {0.4, 0.5} x C_y in {0.0, 0.25}; no training row, every
  sample a demand beyond the trained d range.
- FEASIBILITY-EXTRAPOLATION (5 cells: d in {0.1..0.5} x
  C_y = 0.5, fail-closed by construction): NOT this job's
  demand set. The feasibility channel under the new
  representation is a future decision, recorded here as an open
  residue, never silently scoped in.
- Demand grid: the recorded 360-sample per-groove angle grid
  (1.0 deg), 2 grooves, per design cell -- 720 demands per
  cell, exactly as the expansion froze.

## The success criterion (frozen; the numeric collapse bar
picked AT FREEZE TIME)

- THE MEASUREMENT, identical definitions to the expansion's
  recorded disease measurement so the collapse is directly
  comparable: class medians of distance-to-closed-form;
  INTERPOLATION = the held-out samples within the trained
  cells; EXTRAPOLATION = all samples of the 4 held-out design
  cells; the RATIO OF MEDIANS extrapolation/interpolation, plus
  the per-d sub-class medians (d=0.4, d=0.5) recorded as data so
  both directions are powered.
- THE NUMERIC COLLAPSE BAR (both clauses must hold): (1) the
  ratio of medians on the d >= 0.4 class must fall from the
  recorded 17,930.5049x to <= 10.0x; AND (2) the extrapolation
  class median must land INSIDE the 0.015-unit tolerance band
  (the band the loop actually uses; the recorded worst was
  13.3380x that band).
- THE BAR'S LINEAGE (recorded at freeze): 10.0x is three orders
  of magnitude below the scale confirmation (17,930.5049x) and
  just under two orders below the 885.0308x probe that named the
  disease; it collapses the disease to the line's own measured
  fraction class (the AX2 cost datum -- a tenth); clause (2)
  ties success to the recorded tolerance band itself: an
  in-band design-shift median is an answer the loop can use,
  not merely a smaller error. An unfalsifiable "toward" is
  never frozen; a MISS of either clause is a RECORDED FINDING
  about the feature-map approach (the first-order design
  channel as specified) -- never a waiver, never a silent
  re-tune, never a bar moved after the fact.
- BOTH-DIRECTIONS DISCIPLINE: the closed-form head-to-head stays
  honest in both directions -- the closed form is exact,
  instant, and free (the preordained axis, carried; accuracy
  powers nothing); every graded cell records the learned
  answer's distance-to-closed-form AND the closed-form check;
  a learned accuracy "win" is never claimed. The A4 SUPPLIER
  OUTPUT label and its label-change event carry unchanged and
  unfired; the label-change event is evaluated only against its
  recorded definition, never here.

## The frozen prediction (never a gate)

- PRIMARY (the disease's own structure): the first-order design
  channel cancels the design-offset error to first order, so
  the collapse is expected on the near extrapolation -- the
  d=0.4 sub-class, 0.1 beyond the trained edge (the recorded
  885.0308x case is a d=0.4 cell).
- THE HONEST COUNTER-BRANCHES: the d=0.5 cells are 0.2 beyond
  the trained edge and their second-order design dependence is
  untrained -- a miss there is a RECORDED FINDING about
  first-order conditioning at twice the distance (the
  second-order channel becomes the recorded future candidate,
  through this gate, never silently added). A miss on the
  d=0.4 sub-class as well is a finding about the feature-map
  approach itself. If the new map DEGRADES the interpolation
  class (a collapse bought by breaking the anchor), that is a
  recorded finding in the other direction; the anchor classes
  are never sacrificed for the bar.

## The grade-only recorded case (frozen)

- The recorded design-shift case -- groove_1, 90.0 deg,
  d=0.4 / C_y=0.25, the probe that named the disease -- is
  touched ONCE, at the FINAL GRADE, after all class measurement
  is complete; its distance-to-closed-form is recorded as data
  and the run STOPS. It is never an iteration target:
  iterating against the recorded case would be the
  retune-on-holdout anti-pattern.
- THE ITERATION SET (synthetic only): the interpolation
  held-out samples and the 4 extrapolation cells. Any future
  feature-map iteration happens on these cells only, and any
  change to any frozen number in this document re-stages THIS
  document before any new training run. The optional second
  synthetic design-shift iteration-scratch cell is NOT taken;
  the synthetic cells alone are the iteration set.

## Pins, determinism, stop condition (frozen)

- PINS, FAIL-CLOSED (carried): the capability instrument
  (sha256 72989f8a...06447b, 50,265 bytes) consumed READ-ONLY
  as the analytic ground-truth synthesizer; the trainer
  b1_proposer_train.py (sha256 1cb985ba...c5a9974, 26,268
  bytes) IMPORTED read-only (the loader, the split rule, the
  ridge solve and constants, the fail-closed corpus path); the
  corpus of record (cdac1413...39be6c, 838 rows) loaded through
  the trainer's fail-closed loader -- the REPRODUCTION ANCHOR:
  the regenerated d=0.2 / C_y=0.0 cell must reproduce the
  corpus's recorded solution rows exactly (tol 1e-9), or the
  instrument fails closed.
- DETERMINISM: seed-free training (the closed-form ridge
  solve; no stochastic draw anywhere); deterministic demand
  enumeration; no wall-clock anywhere (the flip -02 lesson);
  the report IS the stop record; NO artifact is written.
- STOP CONDITION: the budget is drawn EXACTLY ONCE -- the 6
  train cells at their train-split samples, the interpolation
  held-out samples, the 4 extrapolation cells at 720 demands
  each, the grade case touched once at the final grade --
  measured once, stopped. No extension, no regeneration, no
  re-split after any result exists; an underpowered or failed
  measurement is a recorded finding, never a budget re-open.

## Machine step (spec; NOT this staging)

- The NEXT staging is the representation instrument: the
  generation + training + measurement script implementing THIS
  document exactly, frozen before any run, with its own
  fail-closed pins, rehearsal disclosure, and fail-closed
  matrix -- the gate-then-run-staging pattern. The run of
  record is then the owner's machine step at the recorded
  standard (the-hub, motion venv, Python 3.14.4, repo root, the
  merged sha; two redirected runs, diff empty, exit 0; the
  report pasted back), read against the frozen sections of
  THIS document. Then the outcome staging closes the job.
- This staging carries NO script, trains NO model, generates
  NO point, and claims NO run. Docs-only: no machine step
  before or after this merge. The substitution guard stands:
  the transfer's success never reframed the supplier as good
  enough -- this freeze treats the measured disease.

## Status

Freeze staged (2026-10-20) -- the ONE design-conditioned
representation freeze document, frozen before any training of
the new map exists: the design channel (d and C_y as inputs
gated onto the frozen per-groove Fourier basis, 147 features
per groove, the trainer's ridge carried; a redesign through
the full gate), the coverage map carried unchanged from the
expansion (the 6 train cells, the interpolation held-out
samples, the 4 d >= 0.4 extrapolation cells as the disease
class; the feasibility cells an open residue), the success
criterion with the numeric collapse bar picked at freeze time
(ratio of medians <= 10.0x AND the extrapolation median inside
the 0.015-unit band; a miss is a recorded finding, never a
waiver), the frozen prediction with both honest
counter-branches, the grade-only rule on the recorded 885x
case (touched once, at the final grade; iteration on the
synthetic cells only), the fail-closed pins with the
reproduction anchor, determinism, and the stop condition. No
model trained, no point generated, no run claimed. The
instrument is the next staging. Docs-only: no machine step
before or after this merge.

## Post-record: the corpus decision (2026-10-20) -- LAND: the
representation is the standing supplier representation, version
1.0

This section is the decision record for the corpus decision this
document froze toward ("exactly the future corpus decision the
expansion recorded, now taken through this gate, never silently
around it"). It is docs-only: the decision, its boundaries, and
its consequences are recorded here; no script, no run, no
training, no measurement is claimed, and the recorded outcome is
final data, never rewritten.

- THE ROUND (recorded): the boss opening position (LAND) went to
  the recorded debate line after the PR #94 outcome; the actor
  and critic rounds returned unanimous LAND with no
  disagreements; the boss fold folded every delta in; the owner
  decided on the folded position. The debate record lives in the
  continuity log, entries 42-43.
- THE DECISION: LAND. The design-conditioned representation
  frozen above -- the 147-feature map (the frozen 49-feature
  Fourier basis [1, cos(k t), sin(k t)] for k = 1..24, plus
  [d, C_y] and the first-order products; one model per groove
  across the 6 train cells; RIDGE_LAMBDA=1e-08) -- becomes the
  STANDING SUPPLIER REPRESENTATION for the flip-station cam
  family, versioned at landing as FLIP-STATION CAM SUPPLIER
  REPRESENTATION 1.0 ("current" is not a version): the transfer
  re-run freeze cites "representation 1.0", and any future
  re-grade under the extension trigger below produces 2.0 --
  the corpus-schema succession rule applied to the supplier
  itself.
- THE BOUNDARIES AT LANDING (declared, carried from the freeze
  and the round): family and grid scope only -- the recorded
  dual-groove design sweep and the admissible cells; the
  C_y=0.5 feasibility cells remain an open residue, never
  silently scoped in. Feasibility stays carried by the
  design-gate wiring, never the function (AX1). First-order
  design channel only. Grade-only discipline maintained.
- THE EXTENSION TRIGGER (recorded at landing): the coverage
  claim is scoped to the recorded dual-groove design sweep and
  the admissible cells and does NOT silently travel. A new
  d/C_y cell class, a new groove family, or the feasibility
  cells entering scope requires a DECLARED RE-GRADE of the
  representation before it is consumed there -- the
  supplier-version-scoping discipline applied to the
  representation itself. The higher-order-terms open item is
  recorded with its trigger and never staged now: it fires only
  on a measured degradation the first-order design channel
  provably cannot explain; any such change re-stages through
  the full gate as 2.0.
- THE PIN (reconstructible; function-plus-data): future
  freezes cite the representation by a pin carrying BOTH
  identities -- the builder spec (the 49-feature Fourier basis,
  the [d, C_y] first-order products, RIDGE_LAMBDA=1e-08, the
  builder's identity hash) AND the training-row source hashes
  (file + hash + the exact cell set: the 6 train cells d in
  {0.1, 0.2, 0.3} x C_y in {0.0, 0.25} under the frozen split
  rule). The PR #58 standard: a future freeze can rebuild the
  representation from the pin alone -- the representation is
  function-plus-data, so both identities are required for a
  byte-identical rebuild. The 147-feature builder is the pinned
  trainer reference for future B1 runs, with lineage rows in
  future freezes.
- THE SUPPLIER-VERSION SCOPING DISCHARGE: the warm-start
  transfer datum re-runs under representation 1.0 as its own
  small freeze (the PR #90/#91 pattern; zero modification of
  existing instruments), RIDING BEHIND this landing as
  confirmation, never gating it -- the claims are independent
  (coverage/accuracy is graded by the run of record above;
  the re-run tests initialization cost under the new
  representation). Exact re-run first for attributability:
  same cells, same consuming context (2 handoff poses x 2
  grooves at d=0.2/C_y=0.0), only the supplier version
  changes; the report carries the old-vs-new comparison row
  explicitly (the recorded 16/16 at 22.0 vs 211.5 mean calls
  read against the new numbers, not inferred). Broader
  consumption is its own later freeze.
- THE ENDGAME READING (a prediction, never a verdict; both
  options live data): with the disease treated, the accuracy
  head-to-head may be structurally unreachable in an
  analytic-synthesis family where the closed form is exact,
  instant, and free. Recorded as a FALSIFIABLE PREDICTION with
  its reopening triggers named across three axes: (1) a future
  family without a closed form; (2) a constrained variant where
  the closed form stops being exact or instant (the warm-start
  transfer's consuming context); (3) scope honesty -- AX1 keeps
  feasibility in the wiring, so the unreachability claim is
  scoped to where the closed form exists. The endgame question
  takes its own round after the transfer re-run's answer
  exists; verdict framings stay rejected (the Direction 3
  precedent).
- SCORECARD LEDGER (the arc this closes): the measured-disease
  arc closes end to end -- three separate measurements named
  the disease (the B2 DATA-LIMITED answer, the 885.0308x
  probe, the 17,930.5049x scale confirmation), ONE freeze
  specified the treatment against all three, and ONE run of
  record confirmed it (the bar MET both clauses; the frozen
  PRIMARY HELD; no counter-branch fired; the recorded 885x
  case graded once, in band).
- LABELS UNCHANGED: SUPPLIER OUTPUT stands; the head-to-head
  win condition remains defined and unfired; the substitution
  guard is in force -- the landing is a supplier upgrade
  inside the framework, NEVER a reframe that the learned line
  "won".
- NEXT: the transfer re-run freeze under representation 1.0 is
  the next B1 staged item (a small freeze; the PR #90/#91
  pattern; prediction frozen before wiring). Docs-only: no
  machine step before or after this merge.
