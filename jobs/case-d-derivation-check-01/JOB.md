# Case study D derivation check -- the desk-only exact-synthesis capacity derivation (N = 4; the count rule fires at 7)

Staged 2026-10-21 per the merged D brief freeze (jobs/case-d-brief-01/
JOB.md, "The derivation check (brief-freeze, desk-only)" section,
frozen at continuity entry66 and merged at PR #103) and the standing
sequencing recorded in continuity entries 68-69 NEXT: this check is
the freeze's own next staged frozen step, its output frozen before
the digest stages. Docs-only: no script, no run, nothing built, no
machine step before or after the merge. The desk work is this
staging's own arithmetic over recorded counts; no verdict on D's
task is claimed by this document.

## The method (carried verbatim from the freeze)

Desk-only, read-only over the recorded synthesis precedent; the
derivation chain visible end-to-end; no runs; output frozen before
the digest stages. It answers three things: (1) the six-bar's
exact-synthesis capacity N for this demand class, positions and
timing pins counted separately; (2) whether the C2-class timing
program constrains beyond the position points; (3) the scoped
verdict in the recorded form. The inconclusive branch is read
before staging, never defaulted past.

## The recorded inputs (read-only, this staging's own reads)

- The freeze: jobs/case-d-brief-01/JOB.md -- the count rule
  (count = N + k, k = 3 frozen), the scoped claim form, the
  inconclusive branch, the operative cost clause, the trigger
  context.
- The desk comparison: jobs/case-d-family-desk-01/JOB.md -- the
  recorded parameterization (Candidate A), the demand class, the
  scoped claim's shape, the eight-bar trigger's input (i).
- Case B's -05 analytic lineage: jobs/dualcam-gap-transfer-05/
  JOB.md, read in full -- the recorded contrast: with the task
  timing frozen the cam profile is fully determined analytically
  (the 1e-9 fail-closed reproduction; Stage 2 NOT TRIGGERED as
  the family finding: analytic synthesis replacing search).
- Case B's -06 analytic lineage: jobs/dualcam-lever-transfer-06/
  JOB.md, read in full -- the exact lever-map synthesis (the
  profile as the pre-distorted image of the task-space demand),
  analytic synthesis replacing search on both axes. Fetch trail
  recorded honestly: three fetches under the path name
  dualcam-gap-transfer-06 failed (no such path); the record was
  read under its recorded directory name.
- B2's representation record: jobs/b1-representation-01/JOB.md --
  the closed-form world the endgame left (the flip-station cam
  family's exact, instant, free closed form; the endgame
  reading's three reopening axes, trigger (a) firing as a
  consequence of the D pick).
- The engine: experimental/motion/README.md -- the mechanism
  graph (ground O-Q-R; crank O-A; rigid body A-B-D; rocker B-Q;
  output body D-C carrying the tool point and orientation; rocker
  C-R), the numerical multi-loop position analysis, the input
  contract (12 phase-locked samples, q/v/a with orientation).
- The flip audit: jobs/flip-station-sixbar-01/JOB.md -- the S4
  priced scope (the five manufactured bar lengths priced; the
  attachment triangle, tool, ground pivots and mounting angle
  declared unpriced scope), the C2 program precedent (the quintic
  program pinning zero rate AND zero acceleration at declared
  windows), the recorded derivative all-fail at 27-41x gate.

## Step 1: the design freedom (counted from the record)

The recorded family parameterization, verbatim from the merged
desk comparison: l1-l4, S_ratio, bar_length, base_x, base_y,
base angle -- NINE continuous parameters -- with branch sign and
crank direction as DISCRETE configuration selectors (they choose
assembly and crank classes; they carry no continuous synthesis
freedom and are counted at zero). The flip audit's S4 confirms
the family's own priced scope: the five manufactured bar lengths
are the priced axes, with the attachment triangle, tool, ground
pivots and mounting angle declared unpriced scope -- carried by
the recorded parameters or fixed within the family, never extra
freedom the engine searches. The count is therefore OVER THE
RECORDED FAMILY, exactly as the scoped-claim discipline requires
-- never over all six-bars.

D = 9 continuous design parameters.

## Step 2: the demand accounting (positions and timing pins
counted separately; the chain visible)

D's frozen demand class: a continuous contour sampled at pinned
precision points, each point's demand = the tool position
(x_i, y_i) at a pinned crank phase theta_i (the declared C2
timing program's phase correspondence; time IS a spec unit).

The standard synthesis accounting, with auxiliary phases:

- A position-only point (phase free): the tool at (x_i, y_i) at
  SOME phase phi_i -- 2 scalar equations, 1 auxiliary unknown
  (the phase) -> net +1 constraint per point against D.
- A timing pin (the phase prescribed by the declared C2
  program): the auxiliary unknown is REMOVED -> net +2 per point.
  The timing pin is thus exactly ONE EXTRA DEMAND beyond the
  position demand, per point -- the freeze's counting rule,
  derived, not asserted.
- The parameterization carries no free crank-phase offset (the
  recorded list has none), so the phase pins are real demands,
  not absorbable by re-referencing the crank zero.
- An orientation pin would be net +1 per point (the solver's
  emission carries tool orientation); D's frozen demand does NOT
  pin orientation -- recorded; a future variant that pins it
  reads its own capacity drop from the same arithmetic.

## Step 3: the capacity N

Positions with timing pins on every point: 2N <= 9 -> N = 4
(floor(9/2); 4.5 rounds DOWN). At 5 timed points the design
system is strictly overdetermined (10 > 9): exact synthesis
cannot cover it on the recorded family -- arithmetic, not
preference. The phase-free contrast (2n <= 9 + n -> n <= 9,
an upper bound with the ordering/consistency demands uncounted
-- combinatorial, not scalar) is recorded as data; it is not
D's class.

## Step 4: the C2 program beyond the position points (answer 2)

The C2-class program's derivative content is a real demand in
the recorded consumption format (the input contract carries q/v/a
samples; the case C precedent's program pinned zero rate AND
zero acceleration at its declared windows):

- A velocity window at a pinned phase (the tool's spatial
  velocity vector per crank radian): net +2.
- An acceleration window: net +2.

With W_v velocity windows and W_a acceleration windows declared,
the effective timed-position capacity is floor((9 - 2*W_v -
2*W_a) / 2) -- STRICTLY BELOW 4 for any declared window: one
velocity window drops it to 3; one full endpoint pair (velocity
plus acceleration) drops it to 2; the case-C-style two-endpoint
pinning (velocity and acceleration at both windows) consumes 8 of
the 9 -> capacity 0, consistent with the recorded all-fail at
27-41x the derivative gates.

ANSWER: YES -- the C2-class timing program constrains beyond the
position points, twice over: the phase pins are themselves the
extra demand beyond position (capacity halves, from 9 phase-free
to 4), and the declared derivative windows consume further
capacity that no point count can absorb. The demand's declared
window count reads its own effective capacity from the
arithmetic above; the digest's demand declaration carries this
row.

## Step 5: the count rule fires

count = N + k = 4 + 3 = 7 pinned precision points with timing.
The first point beyond exact capacity is point 5; the demand
carries 3 points beyond capacity -- the density diagnosis (D3,
the eight-bar trigger's evidence input) has more than one point
beyond capacity to read, exactly as the freeze's margin rule
requires. The at-capacity control row is pinned at N = 4: an
N-point demand set with exact synthesis attempted and confirmed
feasible by the recorded solver, plus the N+1 recorded behavior
-- the capacity claim is machine-verified at the run, never
asserted by this document.

## The scoped verdict (answer 3, in the recorded form)

AT N+k = 7 PINNED POINTS WITH TIMING, NO EXACT SYNTHESIS COVERS
THE DEMAND CLASS ON THE RECORDED SIX-BAR FAMILY PARAMETERIZATION:
14 net design constraints against 9 continuous design
parameters, strictly overdetermined -- and deeper still once the
C2 program's declared derivative windows are counted per step 4.

NEVER "six-bars lack a closed form": the recorded contrast is
the analytic world the -05/-06 lineage demonstrates (with the
task timing frozen the profile is fully determined analytically;
the exact lever map; analytic synthesis replacing search on both
axes) and the recorded four-bar three-pose synthesis; six-bars
have exact treatment for analysis (the recorded numerical
loop-closure solve, deterministic given the parameters and branch
signs) and exact synthesis for FEWER points (at or below N = 4
the design system is finitely determined); the claim is scoped to
the demand class and the recorded family, exactly as the
no-closed-form claim was scoped at the endgame.

## The inconclusive branch: read, NOT taken

The derivation is conclusive on its three questions: the count
is arithmetic over the recorded parameterization (9, recorded
verbatim) and the recorded demand structure (net 2 per timed
point, derived in step 2). The one thing NOT derived at this
desk -- actual solvability/feasibility at N = 4 -- is not
claimed here at all: the freeze pins it to the at-capacity
control row's machine verification, and this check defers to
that pin. No step defaulted past an ambiguity; the read precedes
the staging, as frozen. The eight-bar trigger's input (i)
therefore reads NOT FIRED, NOT INCONCLUSIVE: the capacity count
is about demand DENSITY, not path-shape reachability (whether
the declared contour is inside the recorded parameterization's
reachable classes); that question stays untouched for the
failure digest, exactly as the trigger freezes -- it fires at
the capability step only on a demonstrated out-of-class finding,
never a near-miss.

## The operative cost clause + trigger context (travels with
the verdict)

The verdict confirms the operative reading: on this family at
this demand class the analytic supplier is search-and-grade --
covering 7 timed points exactly is impossible by arithmetic, so
the supplier's at-bat is numerical search over the 9-parameter
family with a real, nonzero per-demand cost in the pinned
oracle-call currency (the recorded 207.5/22.0 accounting class),
counted twice per the freeze. Trigger context (b)-shaped (the
closed form stops being exact/instant at this demand density),
(a) unfired and honest, exactly as the freeze expected. The
non-contest reading stands as declared: if the digest finds no
in-band candidates at any measured cost, the supplier rows are
still data about a well-posed contest whose cost axis was
honestly measured -- never a gate.

## Honest scope of this check

- The count is over the RECORDED family parameterization, never
  all six-bars (the scoped-claim discipline; the desk
  comparison's own criterion).
- The nine continuous parameters are the recorded list; any of
  the nine a future demand pins (e.g. a declared base placement)
  only DROPS the capacity, which strengthens the verdict at 7
  points a fortiori and re-fires the count rule from the new N.
- The parameter-count bound is a NECESSARY condition
  (overdetermination rules exact synthesis out); feasibility at
  N = 4 is the at-capacity control row's machine-verified claim,
  never this document's.
- The phase-free capacity 9 is an upper bound with the ordering
  and consistency demands uncounted; it is data, not D's class.
- The desk reads are exactly the freeze's named precedent set
  (the fetch trail recorded above); no run, no solver
  execution, no corpus touch, no script.

## Sequencing

Freeze (merged, PR #103) -> THIS CHECK -> the failure-digest
instrument (its fairness-gate search config already frozen in
the brief) -> the owner's run of record. The owner executes
every run; nothing auto-runs at staging. On this staging's merge
the merge records as its own continuity entry.

## Status

Derivation staged (2026-10-21, branch case-d-derivation-check-01):
desk-only, docs-only, additions-only; no script staged, no run
claimed, nothing built, no machine step before or after the
merge; no recorded outcome amended. The three answers are frozen
above: N = 4; the C2 program constrains beyond the position
points (strictly); the scoped verdict at 7 = N + k in the
recorded form. The inconclusive branch is read and not taken;
the eight-bar trigger's input (i) is not fired and not
inconclusive. NEXT: the failure-digest instrument stages behind
this check, then the owner's run of record.
