# Case study C cam line re-stage -- the re-stage study freeze under the re-derived class gate (the dual-groove plate-cam flip carrier re-asked as a new study)

Staged 2026-10-21 per the cam class ruling's recorded consequence
(docs/cam-class-ruling-answer.md, merged PR #111, entries 87/89) and
Jean's explicit go -- the ruling's own words carried verbatim: "the
re-stage decision -- whether the cam line re-stages as a new study
under the new gate -- is the owner's explicit strategy decision,
never automatic" -- his call, made. Docs-only: no script, no run,
nothing built, no machine step before or after the merge. No
verdict is claimed by this document; no recorded outcome is
amended; the recorded capability outcome keeps its meaning
("failed the class gate as then defined").

## The lineage (both studies visible, per the ruling's own words)

- THE RECORDED STUDY (jobs/flip-station-capability-01/JOB.md, run
  recorded): the debate-folded dual-groove plate-cam flip carrier
  of the FIXED-PIVOT rigid-mount class -- deterministic Stage 1
  (exact dual-groove synthesis + pose witness, pressure-angle and
  curvature gates with dead-point rows, WC-L tolerance at both
  handoffs with the drive-reversal backlash channel,
  exact-rectangle part envelope, scored reciprocity row); honest
  FAIL recorded on two independent channels: (1) the C1a class
  catch, desk-caught pose-infeasible -- "the three demand centroid
  points (-1.3, 0.5), (0, 0.5), (1.3, 0.5) are colinear and
  distinct, and no fixed-pivot circle passes through three colinear
  points", the best-fit worst-pose residual 1.300000 units (130.00
  mm over the 1.5 mm tolerance); (2) the transmission gate AS THEN
  DEFINED (the 45 deg fixed-frame gate), the worst loaded-arc
  pressure angles 89.070 deg (groove_1) and 89.314 deg (groove_2).
- THE RE-DERIVED CLASS GATE (docs/cam-class-ruling-answer.md, the
  frozen schema's nine mandatory fields): re-rule at the committed
  inputs (mu 0.10-0.15 lubricated steel, SF 2, lineage per the
  schema's rule); self-lock at 84.289407 / 81.469234 deg; the gate
  tan(alpha) <= 1/(SF*mu) computes to 78.690068 deg (mu 0.10) /
  73.300756 deg (mu 0.15, the binding end); the gate IS the 50
  percent loss boundary (mu*tan(alpha) = 1/SF = 0.500). The
  recorded design applied publicly: 89.070 and 89.314 deg FAIL both
  committed gates (by 10.379932 and 15.623932 deg over the looser
  gate) and exceed both self-lock boundaries -- the honest re-rule
  does NOT rescue the recorded design.
- THIS STAGING: the re-stage as a NEW STUDY under the new gate.
  Prospective-only: the new scorecard row applies at THIS study,
  never retroactively; the recorded outcome is never rewritten.

## The frozen scorecard row (the ruling's Field 8, verbatim)

"A new frozen scorecard row for the positive-drive groove-cam
family applies PROSPECTIVELY at any future staging: pressure angle
<= 73.300756 deg at the committed inputs (mu 0.10-0.15, SF 2), the
self-lock boundary reported alongside, efficiency as data."

Read into this study's rows: the gate is the friction/efficiency
channel's; efficiency is reported as data, never gated; the
self-lock boundary (81.469234 deg at the binding mu) is reported
alongside every gate reading; contact stress and pin bending stay
behind the existing rated-force/payload trigger -- this study
smuggles no stress gate it cannot derive (the ruling's own fence).

## The task (frozen; carried from the recorded brief, on task merits)

The same C demand (jobs/flip-station-capability-01/JOB.md, the
carried brief, frozen): the 180 deg face flip as three ordered
poses 0 / 90 / 180 deg; symmetric handoffs at x = -130 and +130 mm
on the carry plane y = 50 mm; mid pose at x = 0; tolerances 1.5 mm
position / 1.5 deg orientation at the handoffs; one flip per cycle
(the out stroke carried, the return empty, the reversals at the
handoffs -- the drive-reversal structure the brief records on its
backlash channel). The task stands on the recorded demand's own
merits, never redesigned to fit the gate.

## The study question (frozen)

The C1a catch is a CLASS property, not a gate property: the
fixed-pivot rigid-mount class is pose-infeasible for this demand
(the executed arithmetic above), and no re-derived gate changes
it. The re-stage study therefore asks: does the POSITIVE-DRIVE
GROOVE-CAM FAMILY contain a flip-carrier design that (a) exits or
dissolves the C1a class boundary -- by an architecture class move
within the family's recorded precedents (e.g. the case-B cam+lever
class, jobs/dualcam-lever-transfer-06/JOB.md: a general pivoted
lever) or by another family class declared with lineage at the
instrument freeze -- and (b) meets the demand rows under the
re-derived gate? Each candidate class is declared with lineage
BEFORE its synthesis runs; the search class is never re-drawn
after a run (the staged-declaration discipline).

## The study's graded rows (frozen here; the audit structure carried)

- S1 POSE FEASIBILITY: the three ordered poses at the recorded
  tolerances (position 1.5 mm, orientation 1.5 deg at the
  handoffs); the C1a class boundary carried -- any fixed-pivot
  rigid-mount candidate fails this row by the recorded arithmetic,
  never re-litigated.
- S2 THE RE-DERIVED GATE: pressure angle <= 73.300756 deg at the
  committed inputs (mu 0.10-0.15, SF 2), evaluated over the loaded
  arcs; the self-lock boundary reported alongside; efficiency as
  data (loss = mu*tan(alpha), the ruling's own arithmetic).
- S3 CURVATURE AND DEAD-POINT ROWS: the family's own recorded
  gates, carried from the recorded study's audit structure.
- S4 WC-L TOLERANCE AT BOTH HANDOFFS with the drive-reversal
  backlash channel, carried from the recorded study.
- S5 THE EXACT-RECTANGLE PART ENVELOPE and keep-outs, carried.
- S6 THE SCORED RECIPROCITY ROW, carried (the family's own
  honesty row).

## The wide-fail branch (pre-stated, read before staging)

If no design in the declared search classes meets all rows, the
honest all-fail IS the outcome: the cam line records as
gate-honest-infeasible at the declared classes for this demand;
recorded as data, never an error; the supplier question is not
reached again in this context; the supplier triggers stay unfired
-- (b) unfired; recorded outcomes are never rewritten. The gate is
never relaxed to rescue a candidate; a gate change is its own
declared ruling (this study consumes the ruling's gate, it never
re-derives it). The honest inconclusive branch reads the same way:
no step defaults past an ambiguity, and the ambiguity itself is
recorded.

## Trigger bookkeeping

- Case study C stays closed with the flip unsolved (the ruling's
  own words: "This ruling does not reopen C"); this study is the
  cam line's own new study on the same recorded demand, the
  owner's explicit call, made, never automatic.
- The six-bar line stays as recorded (honest all-fail); the
  composed-family re-entry line (its own re-entry freeze staged in
  parallel on the owner's go, its own PR and job) is independent
  of this study; neither reads the other's outcomes.
- The frozen eight-bar trigger: UNSETTLED, never fired, untouched
  by this study (a cam study is not an eight-bar question).
- The supplier authorization question parked, resolving at a
  capability step's outcome, never before.
- No runs, training, or automation started; nothing built; the
  owner executes every run.

## Sequencing

The cam class ruling (PR #111, entries 87/89) -> Jean's explicit
re-stage call (made) -> THIS STUDY FREEZE -> Jean's merge -> the
Stage-1 instrument staging (the deterministic design script per
the -05/-06 pattern, the declared search classes with lineage, on
Jean's go) -> the owner's run of record -> the outcome recorded as
its own continuity entries. The owner executes every run; nothing
auto-runs at staging. On this staging's merge the merge records as
its own continuity entry.

## Status

Study freeze staged (2026-10-21, branch flip-station-cam-restage-01):
desk-only, docs-only, additions-only; no script staged, no run
claimed, nothing built, no machine step before or after the merge;
no recorded outcome amended. The task, the re-derived gate, the
graded rows and the wide-fail branch are frozen above; the
recorded study's outcome keeps its meaning; the ruling's Field 8
row carried verbatim; the C1a class boundary carried as the
recorded catch the declared search classes must exit or fail
against. NEXT: Jean reviews and merges; the Stage-1 instrument
staging follows on his go.

## The Stage-1 instrument (staged 2026-10-21, on Jean's go; never run at staging)

`flip_cam_restage_instrument.py` (this directory): the
deterministic design script per the -05/-06 pattern, staged on
the owner's go per this freeze's sequencing. Pure stdlib, ASCII
only, deterministic (no clocks, no randomness, sorted keys; run
twice and diff -- byte-identical is the control); fail-closed
throughout. Syntax-compiled only at staging, NEVER RUN: no run,
training, or automation is started by the staging; the owner
executes every run; the machine step below is the run of record.

The declared search classes (frozen here, declared BEFORE any
synthesis runs, never re-drawn after a run -- the
staged-declaration discipline):

- CLASS F0, the fixed-pivot rigid-mount class (the recorded
  boundary): graded by the C1a arithmetic carried from the
  recorded study -- any F0 candidate FAILS S1 by the recorded
  arithmetic, never re-litigated. This row IS the class boundary
  the declared classes must exit or fail against.
- CLASS G1, the dual-groove plate-cam carrier (the recorded
  study's own class, jobs/flip-station-capability-01, the case-B
  -05/-06 pattern): the recorded exact construction carried; the
  frozen sweep d x C_y re-graded under the re-derived gate; the
  recorded chosen design (d = 0.2, C_y = 0.0) re-graded as its
  own reference row, its recorded outcome keeping its meaning,
  never re-litigated. EXITS C1a by the recorded construction.
- CLASS C1, the cam+lever pivoted-cradle composition (the case-B
  cam+lever class, jobs/dualcam-lever-transfer-06: a general
  pivoted lever): the carriage translates on the carry plane (a
  groove-cam channel, the -05 in-line translating pin follower
  pattern); the part rides a cradle pivoted ON the carriage (a
  MOVING pivot -- the identity mount forced by the demand, the
  centroid at the pivot on the y = 0.5 line); the cradle is
  driven through a frame-pivoted lever whose radial slot engages
  a cradle pin (the -06 lever parametrization: pivot P, short
  arm A, inter-arm angle Delta; the -06 rocker inversion for
  the cam profile). EXITS C1a: the pivot translates, so the
  centroid path is not a circle -- the three colinear poses are
  met by construction. Declared scan (frozen before synthesis):
  Px in {-0.5, 0, 0.5}, Py in {0.9, 1.1, 1.3}, A in {0.15,
  0.25, 0.35}, Delta in {-8, 0, 8} deg, r_p in {0.15, 0.25,
  0.35}, beta_p in {0, 90, 180} deg (729 candidates); coarse
  1 deg scan, finalists audited on the 0.05 deg grid; the frozen
  pick rule: among all-rows-passing candidates the smallest
  worst pressure angle at the binding gate; tie-break larger
  r_p, then smaller |Delta|, then lower Py, then grid order; if
  none passes, the best is recorded with the wide-fail verdict
  -- the gate is never relaxed.

The graded rows, frozen above, implemented per class:

- S1 pose feasibility: the three ordered poses exact by
  construction, machine-verified (witness < 1e-12 at the program
  points); tolerances 1.5 mm / 1.5 deg carried.
- S2 the re-derived gate: pressure angle <= 73.300756 deg at the
  committed inputs (mu 0.10-0.15, SF 2), evaluated over the
  loaded arcs at EVERY transmitting pair (groove-pin,
  groove-roller, slot-pin); the gate arithmetic re-computed and
  checked fail-closed against the frozen six-digit values (the
  gate consumed, never re-derived); the self-lock boundary
  (81.469234 deg at mu 0.15 / 84.289407 deg at mu 0.10) reported
  alongside every gate reading; efficiency as data (loss =
  mu*tan(alpha); the gate IS the 50 percent loss boundary,
  checked: mu*tan(gate) = 1/SF = 0.500).
- S3 curvature and dead-point rows: groove min radius >= 1.25 x
  pin/roller radius (the recorded precedent; pins the 4 mm
  commercial cam-pin class, the roller 15 mm, the -06 first-cut
  radius lineage); dead-point bands excluded from the gates and
  recorded as data; the FD self-check discipline carried (the
  analytic derivative machinery cross-checked against finite
  differences, fail-closed).
- S4 WC-L at both handoffs, channels separate (the drive-reversal
  backlash channel kept separate): groove clearance 0.1 mm per
  side + profile 0.05 mm centerline class per channel; the slot
  wall priced at the same 0.1 mm clearance class; combined =
  their sum; the linear error maps declared per channel (carriage
  groove, lever groove, slot wall), worst case over the
  clearance-sign corners; rank deficiency fails closed with the
  reason recorded; dead points as rows, never finite numbers.
- S5 the exact-rectangle part envelope at 0.25 deg pose samples
  (sampled, never certified) with the carriage, lever,
  cradle-pin and plate extents in one utilization table; the
  handoff stations carried; recorded data, not gated (no size
  demand is frozen by the brief); packaging per the -05
  axial-stack convention.
- S6 the scored reciprocity row: the instrument modification
  count (modifications to the carried audit structure; 0
  expected, any delta named per modification).

The wide-fail branch is pre-stated above and implemented: an
honest all-fail IS the outcome; every verdict prints as data;
nothing is rewritten; the supplier question is not reached; the
gate is never relaxed.

Machine step (the run of record, maintainer-local, after the
merge; the corpus lands under runs/flip-station-cam-restage-01/,
gitignored):

1. `python jobs/flip-station-cam-restage-01/flip_cam_restage_instrument.py --source-commit <merged-40-hex-sha> > cam_restage_run1.txt`
2. A second run with the same sha, redirected to
   `cam_restage_run2.txt`.
3. `diff cam_restage_run1.txt cam_restage_run2.txt` -- expect
   EMPTY; exit 0; each report ends with the in-process
   "double-run determinism check: IDENTICAL" line. Pure stdlib;
   any Python 3.8+.
4. Record the outcome in this JOB.md against the frozen rows,
   referencing the corpus files by the sha256 hashes the script
   prints.

Staging disclosure (honesty note): this script has never been
executed -- syntax-compiled only (the entry55 precedent). Any
falsification at the run of record records as data, per the -06
staging-disclosure precedent.

## The instrument bug-fix (staged 2026-10-21; the owner's run
of record crashed fail-closed before any grading)

The owner's run of record at merged main 0c286766 (the PR
#116 merge) crashed honestly: the instrument aborts with a
TypeError inside fd_check (the FD self-check) before any
grading -- the probe passes a bare float where pin_path
requires a 2-vector pin offset (rot(phi, q) subscripts q[0],
q[1]). Exit 1 on both runs, the diff EMPTY (the crash
itself deterministic); the instrument reached NO graded row,
wrote NO corpus, recorded NO verdict; no recorded outcome is
amended. The crash is data -- the honest cost of the
never-run-at-staging discipline (the entry55 precedent:
syntax-compiled only at staging) -- recorded here, never
rewritten.

The fix (this staging; exactly one line of the instrument,
nothing else): the fd_check probe entries become pin offsets
-- ((0.2, 0.0), 30.0), ((0.2, 0.0), 100.0), (-0.3, 0.0),
250.0) -- preserving the probe's intent exactly (an x-offset
pin at zero y, the G1 pin convention). The fixed instrument
is syntax-compiled only at this staging, NEVER RUN (the
entry55 precedent stands); every graded row S1-S6, every
gate value, the declared search classes, the audit structure
and the corpus schema are unchanged; the S6 reciprocity
question is answered by this disclosure -- the fix touches
no carried audit structure, only the probe's value
representation. The run of record re-executes at THIS
fix's merged sha (--source-commit pinned there, never
0c286766); the outcome staging then records against the
frozen rows exactly as first frozen above.
