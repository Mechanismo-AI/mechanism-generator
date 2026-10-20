# Evidence jobs

Each directory under `jobs` is a self-contained evidence job: a
`JOB.md` (for the queue, a `README.md`) with the purpose, the run
commands, and -- once executed -- the recorded outcome read against a
prediction scorecard written BEFORE the run. Failures,
zero-selection results, and refuted predictions are recorded as data,
not errors, and recorded outcomes are never rewritten. Corpus outputs
land in `runs/` (gitignored, maintainer-local).

| Job | Role | Status |
| --- | --- | --- |
| [sync-pair-eval-01](sync-pair-eval-01/JOB.md) | First end-to-end engine runs of the synchronized pair; produced the S4 verifier fixtures | Served; superseded by the corpus runs |
| [sync-corpus-01](sync-corpus-01/JOB.md) | The corpus driver (`corpus_run.py`) and the applied-offsets follow-up; shared by every later corpus | Driver in active use |
| [sync-corpus-05](sync-corpus-05/JOB.md) | G5 capstone: the pair sharing one keep-out zone (sampled-occupancy gating) | Run recorded |
| [sync-corpus-06](sync-corpus-06/JOB.md) | Anchor-probe pass: single-task offsets over the G5 pools | Run recorded |
| [sync-corpus-07](sync-corpus-07/JOB.md) | Z3 capstone: the screened corpus on fresh engine runs, against a frozen scorecard | Run recorded |
| [sync-corpus-08](sync-corpus-08/JOB.md) | Re-time probe over the screened pools plus the hand-declared 15/15 confirm; post-joint-search outcome appended | Run recorded |
| [corpus-occupancy-digest](corpus-occupancy-digest/JOB.md) | Menu-B digest: pooled occupancy classes over all 499 corpus-07 candidate rows; class-geometry story (zone placement, not link ratios) | Run recorded |
| [corpus-geometry-maps](corpus-geometry-maps/JOB.md) | Menu-C class-structure maps (transform space, scale-invariant, bearing axis); menu C closed: no static quick-vs-drag boundary | Run recorded |
| [corpus-timeline-animator](corpus-timeline-animator/JOB.md) | Menu-E exemplar occupancy timelines; screen-frame window reproduction | Run recorded |
| [corpus-frame-sweep](corpus-frame-sweep/JOB.md) | Corpus-wide base-angle frame sweep (menu-E follow-up): screen 499/499 vs plain 1/499 | Run recorded |
| [gap-transfer-failure-01](gap-transfer-failure-01/JOB.md) | Case study B failure analysis: the level 260 mm gap-transfer carry as three ordered poses at packaging tolerance, asked of the current four-bar engine | Run recorded |
| [sixbar-gap-transfer-01](sixbar-gap-transfer-01/JOB.md) | Case study B capability: the full gap-transfer carry cycle as a frozen 12-phase motion task for the experimental six-bar motion solver | Run recorded |
| [sixbar-gap-transfer-02](sixbar-gap-transfer-02/JOB.md) | Case study B diagnostic: the no-bottom-stops variant of the gap-transfer motion task (carry and process stops unchanged, smooth bottom joins) | Run recorded |
| [sixbar-gap-transfer-03](sixbar-gap-transfer-03/JOB.md) | Case study B diagnostic: the softened-timing recompute -- is the acceleration binding carried by the timing law or by the phase-locked grid? (script, no solver run) | Run recorded |
| [sixbar-gap-transfer-04](sixbar-gap-transfer-04/JOB.md) | Case study B: the free-phase variant -- sample placement freed (T1/T2/T3 poses, path and process stops fixed), chosen by the committed design script; the -03 R4 unlock aimed at the binding prescription, with the group's (a)/(b)/(c) requirements in the JOB | Run recorded |
| [dualcam-gap-transfer-05](dualcam-gap-transfer-05/JOB.md) | Case study B family succession: the dual-cam cross-slide (Option A) design study -- deterministic Stage 1 (fail-closed task validation at 1e-9, analytic profile synthesis on a 0.1 deg grid, pressure-angle/curvature audit with frozen G2 branches, cam-vs-six-bar family-cost table); script, no solver run | Run recorded |
| [dualcam-lever-transfer-06](dualcam-lever-transfer-06/JOB.md) | Case study B family succession: the Option B cam + lever design study -- the dual-cam cross-slide with a general pivoted lever on the x axis (pivot and inter-arm angle as declared scan outputs; exact lever-map synthesis, slide-space continuity, slot-angle gate mirroring the cam branches, combined swept-envelope row), deterministic Stage 1 under the frozen G2 branches; the staging disclosure records the falsified first declaration and the re-derivation; script, no solver run | Run recorded |
| [dualcam-profile-tolerance-07](dualcam-profile-tolerance-07/JOB.md) | Case study B: profile-tolerance -> path-error mapping for the recorded -06 Option B design (exact lever map, frozen WC-L convention; force-closure and A-floor data rows) | Run recorded |
| [dwell-station-failure-01](dwell-station-failure-01/JOB.md) | Case study A failure analysis: the hold-still labeling station -- the case-B-mirrored three-pose instrument, with the 0.3 mm / 50 deg dwell demand scored by a fail-closed digest over the recorded traces (declared layouts, symmetry direction, pinned grid arithmetic, Geneva decision axis) | Run recorded |
| [dwell-station-capability-01](dwell-station-capability-01/JOB.md) | Case study A capability: the debate-adopted one x-cam + passive y-guide dwell design -- deterministic Stage 1 (half-cosine synthesis on the digest grid, executed dwell witness, dual-instance pricing: direct follower vs ideal-ratio lever at the recorded -06 lambda band, required headroom/utilization table, WC/RSS tolerance knees with the duration channel, family-cost table vs the four-bar frontier); script, no solver run | Run recorded |
| [dwell-station-decision-01](dwell-station-decision-01/JOB.md) | Case study A capability-to-spec/decision: the folded actor+critic decision record (lever + tolerance zoning; direct + renegotiation the live fallback with its trigger) and the declared width amendment (frozen rule, provenance answered); deterministic instrument consuming the recorded -01 design read-only | Run recorded |
| [dwell-station-spec-01](dwell-station-spec-01/JOB.md) | Case study A spec side: the folded dwell-duration vocabulary draft (v0.1 section 9.6 clarification -- phase_span minimum semantics + phase_span_allowance; target-layer dwell_realization, recorded-never-gated with the required knee row; worked example from the recorded decision digits with provenance); docs-only S1 | Spec draft staged (S1) |
| [flip-station-failure-01](flip-station-failure-01/JOB.md) | Case study C failure analysis: the flipper brief -- the 180 deg face flip as three ordered poses with directed orientations (0/90/180 deg) on the case-B layout; the fail-closed digest scores position and orientation on the recorded traces and emits the machine-readable solution corpus (units block + schema version) this case study owes the B1 admission-gate work | Run recorded |
| [flip-station-capability-01](flip-station-capability-01/JOB.md) | Case study C capability: the debate-folded dual-groove plate-cam flip carrier (the fixed-pivot class desk-caught pose-infeasible -- three colinear centroid points) -- deterministic Stage 1 (exact dual-groove synthesis + pose witness, pressure-angle/curvature gates with dead-point rows, WC-L tolerance at both handoffs with the drive-reversal backlash channel, exact-rectangle part envelope, scored reciprocity row); wide-fail fires the pre-declared six-bar trigger; B2 answer schema committed alongside (docs/b2-answer-schema.md); script, no solver run | Run recorded |
| [flip-station-sixbar-01](flip-station-sixbar-01/JOB.md) | Case study C family succession (the fired trigger's recorded alternative): the debate-folded six-bar flip carrier motion task -- fold record + demand-translation spec (the motion JSON desk derivation staged: the case-B layout loop inherited from the recorded -01 task plus the C2 quintic orientation program pinning 0/90/180 deg at phases 0/2/4; the S2-S4 audit script staged and desk-validated: folded transmission gates, the swept-envelope table, the analytic link-length sensitivity rows with the FD self-check), S0-S5 scorecard with the corrected transmission gates and the scored instrument-modification row, honest all-fail prior with the plateau-breaker counter-branch; the cam class ruling's frozen answer schema committed alongside (docs/cam-class-ruling-schema.md); RUN RECORDED: honest all-fail on all three seeds, orientation/derivative channel binding as frozen, joint-C transmission hard-fail, the S4 peak-location prediction CONFIRMED, mod-count 0, one open determinism item (seed 580000050 run-2 differs at line 916 -- the solver's first recorded byte-level nondeterminism) | Run recorded; determinism item DIAGNOSED (the wall-clock "seconds" field -- timing metadata, not search nondeterminism; standard amended, confirming full diff pending) |
| [b1-admission-gate-01](b1-admission-gate-01/JOB.md) | The B1 line (the fired strategy trigger, first in order per the fork): the frozen admission gate for the first learned-proposal run -- the seven strategy.md items as graded rows A1-A7 (zero-modification, closed-form head-to-head with both numbers, determinism, supplier-output labeling, OOD control, initializer head-to-head, lineage with identity hashes) plus the frozen first-run design decisions (the flip-station cam space first on the 838-row corpus of record, the additive-only succession-rule schema pin, the frozen held-out split rule, the distance-from-closed-form headline metric). Run staged: the instrument b1_proposer_train.py (per-groove Fourier-feature ridge regression, exact closed-form solve, seed-free; corpus + instrument sha256 pins verified at run; reproduction witness; the frozen distance function, OOD probe with provenance, baseline seed set, A7 artifact order, frozen predictions P1-P4) staged before any run; rehearsal disclosed, no run claimed | Run recorded (2026-10-20) -- first admissible B1 run; honest loss to closed-form in-distribution, clear OOD degradation, beats random restart on every seed; SUPPLIER OUTPUT stands. Next-step decision frozen (2026-10-20): the fallback re-probe (Direction 1) with the synthetic budgeted expansion (Direction 2) committed behind it; re-probe instrument staged (2026-10-20): the script b1_fallback_reprobe.py (design gate, digit-for-digit reproduction check on the recorded supplier, B2-signature rubric; trainer imported read-only under its pin), rehearsal disclosed, fail-closed; re-probe RUN RECORDED (2026-10-20): design gate fired as frozen (FALLBACK: CLOSED-FORM exact on the mismatch branch; LEARNED in-distribution under the trained design), supplier reproduced digit for digit, B2-signature DATA-LIMITED (frozen prediction HELD) -- the fallback is a bandage, design coverage is the disease; SUPPLIER OUTPUT stands |
| [b1-expansion-01](b1-expansion-01/JOB.md) | The B1 line, Direction 2: the synthetic budgeted expansion freeze -- the ONE freeze document before any generation (budget: 7,200 coverage demands + 3,600 feasibility demands + 48 warm-start trials, drawn exactly once, stop condition stated; the gate's split rule within cells, whole design cells per the coverage map; the DESIGN AXIS EXPLICIT per the recorded re-probe redirect: the d >= 0.4 design cells are the extrapolation cells, the recorded 885x probe datum their precedent; pre-declared comparison axes with accuracy preordained; both-directions honesty; the design-conditioned representation recorded as the future corpus decision it is) | RUN RECORDED (2026-10-20) at the recorded standard (merged sha 0311587a; two redirected runs, diff empty, exit 0; pins matched, anchor 720/720): AX1 HELD (the LINE reported INFEASIBLE 3,600/3,600, never silent; learned-alone answered blind -- the wiring carries infeasibility); the coverage disease CONFIRMED at scale (extrapolation/interpolation median ratio 17,930x; worst 13.34x tolerance); the AX2 frozen lean REFUTED honestly (warm start won/tied 16/16 including the far cells, at ~a tenth the baseline oracle cost) -- the PR #44 redemption path measured; design-INTERPOLATION empty by construction; label SUPPLIER OUTPUT stands, the label-change event unfired; the design-conditioned representation remains the future corpus decision |
| [local-llm-queue](local-llm-queue/README.md) | A patient-clerk queue for a local small LLM (digests, labeling, first drafts) | Active tooling |

Recorded outcomes are data about the state of the tools when the run
happened. Where a later revision changed a capability -- e.g. the
joint offset search (PR #30) now composes relations over derived
region events, which `omts propose-offsets` refused before -- the job
files say so and point forward; earlier sections are never rewritten.

## Case study B closure (2026-10-19)

Case study B (the 260 mm gap transfer) is CLOSED with this record; the T4
terminal-branch decision in jobs/dualcam-profile-tolerance-07/JOB.md is
the closure event. Summary:

- Capability record: four-bar three-pose failure record
  (gap-transfer-failure-01: zero selections, position binding ~6-7x over
  tolerance) -> six-bar capability -01/-02/-03/-04 (all-fail; the stops
  bind, not the carry; the bottom stops were not the main carrier; the
  phase-locked grid binds; the free-phase lever cut derivative demand
  ~30% and the position error did not follow -- succession rule engaged)
  -> Option A dual-cam -05 (cam x wide fail by arithmetic, 72.6645 deg vs
  the 45 deg gate; cam y HELD, the family's first HELD engineering gate)
  -> Option B cam+lever -06 (both axes HELD at the 30 deg target inside
  the envelope; the envelope exactly consumed) -> tolerance map -07
  (T1-T7; a uniform 0.10 mm class stays inside the packaging overlay at
  2.54x; the T4 manufacturing-readiness finding) -> the T4 zoning
  decision. The family's answer to the brief is the Option B cam+lever
  design.
- Manufacturing-readiness record: tolerance zoning on the major arcs
  (cam x <= 0.05 mm class; cam y <= 0.05 mm class with the declared
  datum-bias rule bias = class + 0.02 mm), envelope renegotiation
  documented as the fallback with its trigger (a real installation or
  line measurement showing slack).
- Declared open residues, assigned to their future steps: force-closure /
  return-spring gate design (blocked on declared masses and a rated
  speed; the -07 T6 rows are its evidence base); payload/grasp modeling
  (a future-pick capability, e.g. the queued flipper case study);
  dynamics beyond the kinematic torque proxies; certification-level
  collision checking (sampled occupancy, never certified).
- The budget sweep stays the standing in-family candidate if the family
  question returns.
