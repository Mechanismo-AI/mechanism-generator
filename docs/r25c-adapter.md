# R2.5c draft adapter

The adapter creates input files for the packaged four-bar research engine. It
does not install, import, download, or execute that engine during adaptation.
The foundation is useful for validating OMTS without any machine-learning runtime.

```sh
omts capabilities
omts adapt examples/omts/three_point.omts.yaml --output-dir generated/demo
```

Generated files include `run_plan.json`, `tasks/task-001/targets.csv` (and one CSV
for each additional task), and `run_r25c.py`. Existing output directories are
refused. All tasks pass document/capability checks before any files are created.

The plan contains argument arrays, relative paths, target order, the canonical
input hash, and expected research artifact hashes. It contains no resolved local
source path. Text annotations are not interpreted as execution settings. Review
your own input annotations and generated results before sharing them.

## Supported subset

| Task feature | Behavior |
|---|---|
| Units/frame | `normalized`, `deg`, `s`; right-handed planar XY, x right/y up |
| Motion | Exactly three hard position targets, optionally with all three planar orientations; free phases, unordered or ordered |
| Ordering | Listed order, or sorted by unique `order_index` supplied on every target |
| Cycle | Positive 0â€“360 degree phase cycle, without period/speed/time constraints |
| Topology | Four-bar, one degree of freedom, one actuator |
| Ground | Hybrid portfolio with one fixed seed; maps trust fraction and release controls |
| Profiles | All three accuracy/balanced/transmission profiles; paired or cross matrix |
| Branches | Open (`negative`), crossed (`positive`), or both |
| Path | Hard positive mean/point ceilings and shared path allowances |
| Position tolerance | Identical position tolerances on all three targets; combined with the global point ceiling using the smaller value |
| Orientation tolerance | Individual positive tolerances below 180 degrees; omitted values default to 5 degrees |
| Transmission | Soft `worst_target` goals plus separately mapped practical selection floors; degrees only |
| Assembly/class | Full-cycle assembly, Grashof, crank-shortest; optional follower-not-longest |
| Compactness | Report-only request; no custom thresholds or weights in this adapter |
| Panel | Optional hard sampled full-turn rectangle containment for link centrelines and a carrier centred on P; fixed-pivot edge clearance |
| Pose initialization | Separate nominal/tolerance sample budgets, each 0–262144, and 0–6 retained seeds per branch |
| Search | Per-task seed, top_k, perturbations, parameter noise, phase noise, continuation options |
| Outputs | JSON + CSV + NPZ together, optional PNG; histories and lineage included |

Each independent task gets its own command and CSV. Different requirements and
search settings across tasks are preserved. A global `outputs.top_k` and per-task
`search.top_k`, if both supplied, must agree. Omit the global field for different
per-task values. `top_k` limits the final selected portfolio, not diagnostic files.

See the [tolerance and panel guide](tolerance-and-panel.md) for the new
`search.pose_initialization` and `requirements.panel` fields, units, defaults,
limitations and a complete example. Other workspace/obstacle fields remain
unsupported; sampled panel containment does not implement collision constraints.

R2.5c evaluates three proposal roles: balanced, path, and transmission. Adapter
defaults are explicit in every generated argument array: fixed L1 seed 6, trust
fraction 0.25, three fixed/release seeds, paired bridges, no perturbations, seed
101, top_k 5, parameter noise 0.18, phase noise 4 degrees, and CPU execution. Default
path ceilings are 0.05 mean/0.075 per point, with shared allowances 0.02/0.05.
Transmission goals are 35/15 degrees (target/global), with selection floors 15/10.

## Three planar poses

Each pose combines the existing output-point position with the direction of the
coupler. Add `orientation: {type: planar_angle, value: ...}` to **all three** targets.
Set `tolerance.orientation` independently for each target; an omitted angular
tolerance defaults to 5 degrees. Tolerances must be finite, greater than zero,
and below 180 degrees. Angles may be any finite number of degrees: the engine
compares the shortest circular difference, so 179 and -179 degrees differ by
2 degrees. An angular tolerance without a target orientation is rejected.

The tool frame has its origin at output point **P**. Its positive x-axis points
from coupler joint **A** (attached to the input crank) toward **B** (attached to the
output rocker). The angle is measured counterclockwise from world +x in the
right-handed XY frame. This first pose capability has no adjustable mounting
angle between that frame and a workpiece. A target orientation is a directed
angle: reversing A to B by 180 degrees is a different pose.

For example, one target can be written as:

```yaml
- id: T1
  position: [-6.0, 2.0]
  orientation: {type: planar_angle, value: 30}
  occurrence: {free: true}
  tolerance: {position: 0.075, orientation: 3}
  mode: hard
```

The adapter writes `--target_orientations_deg` and
`--orientation_tolerances_deg`, each followed by three values. It also records
these arrays in the plan. Positions, orientations, tolerances and target IDs are
reordered together when `order_index` is used. Independent tasks retain their
own settings; position-only tasks receive no orientation flags.

Position and orientation are checked at the **same three optimized target
phases**. A selected pose candidate must satisfy every requested angular
tolerance as well as the existing eligibility checks. These are target-only
constraints: they do not prescribe orientation between targets, motion speed,
timing or dwell. The released proposal networks still take positions as input;
the engine refines their proposals against the requested poses. Search can return
no eligible solution, and that does not establish that a task is impossible.

Pose candidates report `orientation_acceptable`, `pose_acceptable`,
`max_orientation_error_deg` and `mean_orientation_error_deg`, plus requested,
matched and error angles for each target. `path_acceptable` retains its positional
meaning; `pose_acceptable` requires both position and orientation acceptance.
Candidates that meet the path limits but miss an angular tolerance are marked
`path_acceptable_but_orientation_failed` and cannot be selected. The existing
`selection_eligible` and `engineering_acceptable` fields include the orientation
gate for pose tasks. This qualification still describes a kinematic candidate.

The research engine retains its normal optimizer schedules, profile-weighted
objectives, compactness optimization/ranking, and search bounds relative to
`D = max(maximum pairwise target separation, 0.25)`. Variable ground is searched
over 0.5Dâ€“2.5D, moving links over 0.05Dâ€“3D. A report-only compactness request adds
no requirement or custom objective; the engine's existing preferences remain.
These are heuristic search limits, not a claim to enumerate every valid mechanism.

## Rejections are intentional

The wider schema accepts many features this adapter cannot implement. It rejects
fixed-only/optimized-only ground modes, custom bounds, unequal per-target position tolerances,
hard transmission goals, custom weights, compactness constraints, custom Pareto
objectives, time/candidate budgets, non-normalized lengths, radians, reversed cycles,
partial or spatial orientation requests, timing/dwell, loads/dynamics, collisions, synchronization, extensions,
and unsupported output options. Only `unsupported_feature_policy: error` is accepted.

Zero path ceilings are rejected because zero disables those checks in the research
engine; silently using it for an exact-match request would invert the requirement.
Nonzero `guarantee_fixed_count` is rejected to avoid unqualified selected references.
Requests above `kinematic_candidate` are rejected. Read [qualification](qualification.md)
before interpreting any outputs.

## Execute with the public engine and weights

Install the engine extra and download the public weights as described in the
[engine guide](engine.md). Then execute the generated helper:

```sh
python generated/demo/run_r25c.py --models-directory models --check-only
python generated/demo/run_r25c.py --models-directory models
```

The helper checks installed engine source and model SHA-256 hashes before any
optimization. Use the Python environment in which the engine is installed. Its
own location anchors the plan, target and output paths; the model directory is
resolved from the invoking directory. Invocation uses argument arrays without a
command shell. No download happens during execution.

Regenerate plans after an engine update: the helper requires exact engine source
identities. `r2.5c-fourbar` remains the accepted input profile name; new plans
identify the public implementation. Three planar pose targets extend the prior
position-only subset without changing the existing model weights.
The model exports passed exact tensor and prediction parity checks, and current
numerical engine checks are documented in the engine guide.

From 0.1.0a5, prepared pose plans explicitly enable 4,096 deterministic geometric
samples and at most six retained seeds, in addition to the existing proposal and
refinement paths. The new `pose_seeds.py` is covered by source verification.
This adds search work; it does not relax position, orientation, transmission or
robustness checks. Point-only plans do not invoke geometric pose initialization.

## Crank direction

`motion.cycle.direction` accepts `positive` (default), `negative`, or `either`.
Negative means decreasing physical input angles in the right-handed XY frame.
Either permits either constant direction and runs both full search budgets with
separate result and contribution folders. Ordered occurrences retain their target
order in both directions. `bidirectional` remains unsupported: reversal within a
cycle is a different requirement. No timing or speed profile is inferred.
