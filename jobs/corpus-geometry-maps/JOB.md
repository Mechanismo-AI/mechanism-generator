# Job corpus-geometry-maps: transform-space class structure (C, C.2, C.3)

**Purpose.** Menu item C of the corpus evidence arc: find a static-geometric
axis (if any) that separates the occupancy classes across the whole corpus.
Three passes: C v1, the raw transform-space map over the menu-B digest CSV;
C.2, the same with the scale-invariant axis clear/l1 (the variants are
rotate/scale transforms of one example, so absolute clearances mix task
scale with class); C.3, the bearing axis -- zone orientation in each
candidate's own base frame -- re-reading the corpus-07 trees because the
digest CSV lacks base_x/base_y/base_angle and the zone center. All
fail-closed (missing columns/sidecars abort; C.3 reproduces the menu-B
tallies or aborts); stdlib only; every generated SVG is XML-verified before
writing.

**Run (maintainer-local, from the repo root).**

```sh
python jobs/corpus-geometry-maps/map_c.py    # runs/analysis/transform-map-01/
python jobs/corpus-geometry-maps/map_c2.py  # runs/analysis/transform-map-02/
python jobs/corpus-geometry-maps/map_c3.py  # runs/analysis/transform-map-03/
**Block 3:**

```bash
cat > jobs/corpus-timeline-animator/JOB.md <<'EOF'
# Job corpus-timeline-animator: per-exemplar occupancy timelines

**Purpose.** Menu item E: for every corpus-07 task group, pick exemplar
candidates (lower-median total_width_deg per group, ties by candidate_id),
re-resolve their 720-phase occupancy from the recorded row geometry against
the task's zone_screen.json sidecar, and emit one self-contained HTML (SVG
animation plus meta JSON) so the temporal structure -- window placement,
dwell timing -- is inspectable without re-running the engine. Fail-closed:
recorded tallies/classes/steps/cap anchors; aborts on structural anomalies.

**Run (maintainer-local, from the repo root).**

```sh
python jobs/corpus-timeline-animator/anim_e.py  # runs/analysis/animation-e01/
**Block 4:**

```bash
cat > jobs/corpus-frame-sweep/JOB.md <<'EOF'
# Job corpus-frame-sweep: corpus-wide base-angle frame sweep

**Purpose.** The menu-E follow-up: upgrade the animator's 6-exemplar
screen-frame check to every candidate row. Each of the 499 corpus-07 rows
is re-resolved in both base-angle frames -- screen (base =
radians(base_angle), the recorded engine behavior) and plain (base as
stored; the control) -- and compared against the recorded window lists.
Recorded constants are checked fail-closed before any comparison: per-task
tallies (42 rows except 01/catcher 38 and 05/gate 41), pooled classes
(never 53, quick_pass 192, drag_over_cap 246, full360 8, invalid 0), steps
720, hard cap 60.0, method, disclaimer, screen shape. Any structural
anomaly aborts (exit 2) with nothing written. The resolver mirrors
src/mechanism_generator/engine/zone_screen.py::screen() operation-for-
operation in pure stdlib; the sweep was written from the engine source at
main 12badcb7 (engine files identical to f3ebca9a where corpus-07 ran; PR
#31 was docs-only).

**Run (maintainer-local, from the repo root).**

```sh
python jobs/corpus-frame-sweep/frame_sweep.py  # runs/analysis/frame-sweep-01/ (never overwrites; delete to rerun)
**Block 5:**

```bash
cat > jobs/README.md <<'EOF'
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
| [local-llm-queue](local-llm-queue/README.md) | A patient-clerk queue for a local small LLM (digests, labeling, first drafts) | Active tooling |

Recorded outcomes are data about the state of the tools when the run
happened. Where a later revision changed a capability -- e.g. the
joint offset search (PR #30) now composes relations over derived
region events, which `omts propose-offsets` refused before -- the job
files say so and point forward; earlier sections are never rewritten.
