# Job dwell-station-failure-01: case study A -- the hold-still labeling station asked of the four-bar engine

**Purpose.** First step of the case-study loop for case study A (brief,
failure analysis, capability): the dwell station. A continuous conveyor
passes a labeling station; while the machine keeps turning, the carried
point must hold still at the station -- within 0.3 mm of the station
point for at least 50 deg of the input cycle. The current OMTS draft
has no dwell vocabulary, so this run asks the R2.5c four-bar engine for
the job with today's machinery -- three ordered poses at packaging
tolerance, no new spec vocabulary, no new engine code -- and a
fail-closed digest scores the dwell demand on the recorded coupler
traces. Claim-only-what-exists: the document encodes the pose
instrument, the digest measures the dwell. The recorded data (the
hold-still frontier of four-bar coupler curves at the station) is the
evidence base for the dwell capability design. Anticipated spec
question, recorded as a prediction and not a commitment: the future
OMTS dwell vocabulary will need a duration concept (dwell refs
currently carry windows on events, per the sync spec's
task.target.reached|dwell machinery).

**Task.** `examples/omts/dwell_station.omts.yaml`. Three poses on the
case-B-mirrored symmetric layout: the approach, the station and the
depart poses at physical (-130, 50), (0, 50) and (+130, 50) mm -- 1
normalized unit = 100 mm, origin at the station on the carry line,
carry plane 50 mm above the conveyor. All three level: orientation
0 deg. Tolerances: position 1.5 mm (0.015 normalized), orientation 1.5
deg. The instrument is deliberately numerically identical to the case
study B gap transfer (same poses, tolerances, portfolio and seed 101;
only the brief it serves changes), so the dwell reading lands in the
same units and the same geometry class as the recorded six-bar
frontier, and the succession argument stays apples-to-apples.

**Declared layouts (chosen and not taken).** Chosen: the case-B-mirrored
symmetric layout (plus/minus 130 mm approach/depart around the
station), for comparability with the recorded case-B frontier. Not
taken: a station-centered layout with shorter travel -- an easier
pool -- because a failure reading on the harder, comparable layout is
the stronger result, and a pass on the easy layout paired with a fail
at case-B scale would itself be a size-scaling finding, which is
data. The symmetry of the chosen layout eases the pool in its own
direction: it admits pool members whose apex lands on the station by
symmetry. That easing is predicted to be swamped (apex holds are
expected in the several-mm class against a 0.3 mm demand), but it is
declared here so the reading protocol is frozen: if the D2 result
lands in the 3-10x branch below, the first question the reading must
ask is symmetry or capability, and the cheap sensitivity variant is
an asymmetric station offset (the -02 pattern), not a re-do.

**The dwell demand, pinned.** Station point: (0.0, 0.5) normalized =
(0, 50) mm -- the T2 pose. Hold radius: 0.3 mm = 0.003 normalized
(1 unit = 100 mm, the case-B convention; the six-bar bbox figure
~0.00109 is a different normalization and is NOT used here). Hold
window: at least 50 deg of the input cycle, continuous. Never scored:
drift. The demand is the maximum distance from the station over the
window; scoring "relative stillness" or drift from the window start
would flatter slow passes through the region and produce smaller
numbers. This note is frozen -- someone will be tempted later,
precisely because drift scores are smaller.

**Grid arithmetic, pinned.** 7201 closed samples = 7200 unique samples
per cycle = 7200 intervals of exactly 0.05 deg; 50 deg / 0.05 deg =
1000 intervals, so the 50-deg window is 1001 samples inclusive (start
and end). The digest asserts all of this at run time and aborts on
any off-by-one: a 1000-sample or 1001-interval window would shift
every candidate's score by half a sample step, and the instrument's
own tolerance must be tighter than the gap it measures.

**Machine.** Any idle Ubuntu PC (CPU-only, no GPU) with the standard
engine venv (`pip install ".[engine]"` plus `mechanism-models
download`; see sync-pair-eval-01 for the one-time setup). Cost: one
three-pose search at the standard portfolio budget. The document
declares `direction: either`, which runs both crank directions as two
complete search budgets with separate results (about 30 s per
direction on the-hub, by the case-B record), plus the digest: pure
standard library, seconds to a few minutes, any Python 3.9 or newer.

## Steps

1. **Validate and adapt** (the plan lands in a fresh directory; the
   adapter refuses existing ones):

   ```sh
   omts validate examples/omts/dwell_station.omts.yaml
   omts adapt examples/omts/dwell_station.omts.yaml --output-dir runs/dwell-station-failure-01
   ```

2. **Preflight** (verifies installed engine and model hashes, runs
   nothing):

   ```sh
   python runs/dwell-station-failure-01/run_r25c.py --models-directory models --check-only
   ```

3. **Run** (the long part; tmux or nohup):

   ```sh
   python runs/dwell-station-failure-01/run_r25c.py --models-directory models
   ```

4. **Digest, twice, and diff** (the determinism control; `<run-root>`
   is the fresh timestamped directory step 3 created under
   `runs/dwell-station-failure-01/results/task-001/either/`):

   ```sh
   python3 jobs/dwell-station-failure-01/dwell_digest.py <run-root> > digest_run1.txt 2>&1; echo EXIT=$?
   python3 jobs/dwell-station-failure-01/dwell_digest.py <run-root> > digest_run2.txt 2>&1; echo EXIT=$?
   diff digest_run1.txt digest_run2.txt
   ```

   The diff must be empty; report the full stdout (digest_run1.txt).

## What the digest does (fail-closed, pure standard library)

`jobs/dwell-station-failure-01/dwell_digest.py` never runs a solver,
keeps no clocks and draws no randomness. It scans `<run-root>` for
`all_candidates.csv` files and aborts unless it finds exactly two, one
per crank direction (grouped by the rows' `crank_direction` column).
For every candidate row it:

- rebuilds the nine-value parameter vector from the recorded columns
  (l1, l2, l3, l4, S_ratio, bar_length, base_x, base_y, base_angle)
  and the assembly `branch_sign`;
- reproduces the engine's own record first: at each recorded matched
  phase (`phase_1_deg`/`phase_2_deg`/`phase_3_deg`) the rebuilt
  coupler point's distance to the corresponding target must equal the
  recorded `error_1`/`error_2`/`error_3` within 1e-6 normalized
  (1e-4 mm). A mismatch aborts the whole digest: the dwell metrics are
  only ever computed on traces that reproduce the recorded evidence.
  The kinematics is the parity-tested `four_bar_skeleton` from
  `src/mechanism_generator/omts/geometry.py`, embedded verbatim in the
  digest (pure math, no engine import, no network); theta_deg is the
  engine's own crank parameter, the same angle space as the recorded
  matched phases, for both crank directions;
- rebuilds the full-cycle coupler trace at the pinned grid (7200
  unique samples). A row whose recorded `full_cycle_assembly` is
  false is excluded from scoring and reported in its own class (the
  dwell question is undefined on an open trace); a row recorded true
  whose rebuild hits undefined assembly aborts the digest -- that
  would be a real inconsistency, never a quiet pass.

Then, per candidate -- all rows are scored, qualified or not: this is
a failure analysis, the pool is the data, and the qualification level
is reported per row:

- **Primary (the demand):** the best 50-deg window (1001 samples
  inclusive, all 7200 starts, wrap-aware) scored as the maximum
  distance from the STATION point. The pool-min of this number
  against the 0.003 demand is the headline.
- **Free-dwell diagnostic (scored, not gated):** the best 50-deg
  window anywhere, scored against its own center-sample anchor
  (declared convention: the anchor is the trace point at the window's
  center sample; the exact minimal-enclosing-circle radius is at most
  this, and the placement-vs-stopping question is answered
  identically). The gap between the free-dwell and station readings
  separates "the pool cannot stop anywhere" (both large) from "the
  pool stops but cannot place its apex at the station" (free small,
  station large) -- the most design-relevant output of the digest for
  the dual-cam-vs-six-bar question, because apex placement is a
  linkage-synthesis freedom while dwell duration is a coupler-curve
  property.
- **Window-width rows (data-only, both directions recorded):** the
  widest contiguous window meeting 0.003 at the station
  (interval-counted: a run of L samples covers L-1 intervals at
  0.05 deg; all-True would be the full 360.0), and the best-hold
  radius at exactly 50 deg (the primary row, restated). A candidate
  holding 0.29 mm for 48 deg is a different near-miss class than one
  holding 0.9 mm for 50 deg; the two classes point at different
  fixes.
- **Min-speed classification (data-only):** each best window's minimum
  speed is classified apex or cusp. Cusp = the carried point's
  velocity reaches zero with a direction reversal -- an exact
  instantaneous stop, a stronger dwell region than any apex; detected
  by speed below 1% of the candidate's median sample speed together
  with a velocity-direction reversal across the minimum. Cusp
  presence or absence in the pool is capability evidence, not color:
  cusp dwell is a real linkage-synthesis freedom, and it feeds the
  six-bar arc-riding line directly.
- **Drift rows (data, never scored):** the distance from the station
  at the best station window's start and end samples.

The digest prints the per-candidate table, the per-direction and pool
readings, the classification histogram, and the witness line. It
writes no files. Window metrics are direction-blind by construction:
the closed coupler curve is the same set of points whichever way the
crank turns; each reading is labeled with its row's `crank_direction`.

## Prediction scorecard (frozen before the run)

- **D1 (primary):** no candidate achieves a 50-deg window within
  0.3 mm (0.003 normalized) of the station. Zero passes is the
  expected honest outcome, not an error.
- **D2:** the pool-min primary reading misses the demand by at least
  10x -- expected one to two orders: coupler-curve holds near apexes
  on case-B-scale geometry are in the several-mm class against the
  0.3 mm demand. Frozen alternative branch: a 3-10x miss is "closer
  than expected" -- read before staging the capability step, first
  question symmetry or capability (see the declared-layouts
  paragraph). No gate changes; this JOB pre-commits to reading a
  near-D2 result rather than defaulting past it.
- **D3:** the best windows sit at min-speed regions -- apexes and/or
  cusps (cusp-inclusive wording, frozen). The digest classifies
  which; a cusp worded "apex" would read as refuted when it is the
  same mechanism in its most extreme form.
- **D4 (control):** any candidate passing D1 is an honest refutation
  and is recorded as the result, not an error. It would mean the
  four-bar pool already contains a 0.3 mm / 50 deg dwell at the
  station, and the capability step then needs the stricter brief
  before it can motivate a new family.

## Readings to report

- Per crank direction: wall-clock, and from the run summary /
  `run_manifest.json` target record: candidate_count,
  path_acceptable_count, orientation_acceptable_count,
  pose_acceptable_count, selection_eligible_count, selected_count.
- The `qualification_level` histogram over `all_candidates.csv`.
- The digest's full stdout: the per-candidate table (primary radius,
  free-dwell radius and anchor, widest windows, classification, drift
  rows), the per-direction pool-min readings, the classification
  histogram, the D2 ratio against the 0.003 demand, and the witness
  line.
- Machine, CPU model, Python version, and the seed as run (101).
- Expected pool: identical to the case-B record (the document is
  numerically identical to gap_transfer and the search is seeded, so
  the same 18 candidates per direction are expected); a divergence
  from the recorded case-B frontier is data to record, not an error
  to hide.

## What we will do with it

The hold-still frontier is the input to the dwell capability design.
Leading hypothesis, recorded as a preview and not a commitment: the
dual-cam dwell-arc line -- dwell is exact by construction on the
dwell arcs, and the recorded -07 tolerance map already prices its
major arcs. Second: the six-bar arc-riding line, whose cusp/apex
freedom is exactly what this digest measures. The Geneva option is
NOT arbitratable by this digest and is recorded as decided by
line-architecture analysis, not by failure-run data: a Geneva is an
intermittent-motion line architecture (the whole conveyor indexes
station to station; every station dwells by construction), and a
strong D2 failure later must not be misread as eliminating it. Only
the four-bar / six-bar arc-riding line faces this digest's verdict.
Envelope note, the T4 lesson applied forward: brief A's envelope is
NOT inherited from case B. Case B's 600x600 mm envelope was
debate-declared -- a round number -- and its tolerance endgame came
down to zero headroom against it. This brief's envelope will be
declared WITH lineage at capability-freeze time (bench footprint,
station pitch on the line, or a debate-declared round number --
recorded as whichever it is) and derived rather than defaulted: a
labeling-station dwell needs less travel than case B's 260 mm carry,
so the family's zero-headroom precedent does not automatically
recur -- but only if the envelope is derived, not defaulted.

Record the outcome against the scorecard in this file; recorded
outcomes are data and are never rewritten.

## Staging disclosure (honesty notes)

- The example is numerically identical to the case-B gap transfer by
  design (comparability), and the engine run is a fresh run, not a
  result reuse: the recorded case-B run outputs live on the-hub and
  are data; this job re-runs the same deterministic search fresh and
  scores the dwell demand on its own traces. The identical-pool
  expectation is recorded above as a reading, not assumed.
- The dwell demand is not encoded in the OMTS document (no dwell
  vocabulary exists; the spec-banner incident rule, claim-only-
  what-exists). Everything the digest scores is declared in this JOB
  and computed from the recorded engine output.
- The digest's free-dwell anchor convention (center sample), cusp
  threshold (1% of median sample speed plus direction reversal) and
  reproduction tolerance (1e-6 normalized) are declared conventions,
  frozen here before the run; they are classification and witness
  rules, not gates.

## Machine steps after merge

1. `git pull` on the-hub.
2. Steps 1-4 above (validate, adapt, preflight, run; then the digest
   twice with `diff digest_run1.txt digest_run2.txt` empty); report
   the full stdout.
3. Readings to report back: exit codes; the run counts; the digest's
   witness line; the pool-min line with the D2 ratio and branch; the
   classification histogram; the Python version line.
