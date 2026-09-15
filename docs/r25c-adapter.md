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
| Motion | Exactly three hard position targets; free phases, unordered or ordered |
| Ordering | Listed order, or sorted by unique `order_index` supplied on every target |
| Cycle | Positive 0â€“360 degree phase cycle, without period/speed/time constraints |
| Topology | Four-bar, one degree of freedom, one actuator |
| Ground | Hybrid portfolio with one fixed seed; maps trust fraction and release controls |
| Profiles | All three accuracy/balanced/transmission profiles; paired or cross matrix |
| Branches | Open (`negative`), crossed (`positive`), or both |
| Path | Hard positive mean/point ceilings and shared path allowances |
| Target tolerance | Identical position tolerances on all three targets; combined with the global point ceiling using the smaller value |
| Transmission | Soft `worst_target` goals plus separately mapped practical selection floors; degrees only |
| Assembly/class | Full-cycle assembly, Grashof, crank-shortest; optional follower-not-longest |
| Compactness | Report-only request; no custom thresholds or weights in this adapter |
| Search | Per-task seed, top_k, perturbations, parameter noise, phase noise, continuation options |
| Outputs | JSON + CSV + NPZ together, optional PNG; histories and lineage included |

Each independent task gets its own command and CSV. Different requirements and
search settings across tasks are preserved. A global `outputs.top_k` and per-task
`search.top_k`, if both supplied, must agree. Omit the global field for different
per-task values. `top_k` limits the final selected portfolio, not diagnostic files.

R2.5c evaluates three proposal roles: balanced, path, and transmission. Adapter
defaults are explicit in every generated argument array: fixed L1 seed 6, trust
fraction 0.25, three fixed/release seeds, paired bridges, no perturbations, seed
101, top_k 5, parameter noise 0.18, phase noise 4 degrees, and CPU execution. Default
path ceilings are 0.05 mean/0.075 per point, with shared allowances 0.02/0.05.
Transmission goals are 35/15 degrees (target/global), with selection floors 15/10.

The frozen research engine retains its normal optimizer schedules, profile-weighted
objectives, compactness optimization/ranking, and search bounds relative to
`D = max(maximum pairwise target separation, 0.25)`. Variable ground is searched
over 0.5Dâ€“2.5D, moving links over 0.05Dâ€“3D. A report-only compactness request adds
no requirement or custom objective; the engine's existing preferences remain.
These are heuristic search limits, not a claim to enumerate every valid mechanism.

## Rejections are intentional

The wider schema accepts many features this adapter cannot implement. It rejects
fixed-only/optimized-only ground modes, custom bounds, unequal per-target tolerances,
hard transmission goals, custom weights, compactness constraints, custom Pareto
objectives, time/candidate budgets, non-normalized lengths, radians, reversed cycles,
orientation, timing/dwell, loads/dynamics, collisions, synchronization, extensions,
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

Regenerate foundation-era plans: the public engine and cleaned safetensors weights
have new identities. `r2.5c-fourbar` remains the accepted input profile name; new
plans identify the public implementation. The draft supported subset is unchanged.
The model exports passed exact tensor and prediction parity checks, and current
numerical engine checks are documented in the engine guide.
