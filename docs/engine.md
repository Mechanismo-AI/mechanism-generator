# Run the four-bar research alpha

The packaged engine combines the R2.5c hybrid portfolio and R2.5b numerical
refiner. Three frozen neural proposal models initialize fixed-ground and variable-
ground searches, followed by trust-region and release continuation, qualification,
deduplication, and ranking. Optional three-pose requests add directed coupler
orientation to the local search and qualification. Code and public weights use
Apache-2.0; the three released position-input proposal models are unchanged.

## Install and download

Use Python 3.12 for the tested engine environment. OMTS-only tools also support
Python 3.10. Create and activate a virtual environment as in the root README.
On Windows use a short checkout/output location, such as `C:\mg`: deep directory
trees can exceed Windows path limits during dependency installation or output.

From the repository checkout:

```sh
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install ".[engine]"
mechanism-models download --directory models
mechanism-models verify --directory models
```

The first command selects CPU-only PyTorch; no GPU is needed. The remaining tested
numerical versions were NumPy 2.5.1, pandas 3.0.5, matplotlib 3.11.1 and safetensors
0.8.0. The package declares compatible ranges; exact tested pins are in
[requirements-engine-cpu.txt](requirements-engine-cpu.txt).

The downloader fetches three files (about 22.2 MB total) from this repository's
versioned GitHub release. It verifies SHA-256 before placing each file, reuses
matching files, and refuses to overwrite mismatched files. It never runs during
ordinary import, OMTS validation, adaptation, or solver execution.

## Run a target triple

```sh
mechanism-generate --models-directory models --targets -6 2 -2 6 0.5 3.5 --branches both --device cpu --headless --output_root runs/demo
```

Add `--quick` for a smaller search budget. Add `--no_plots` to omit PNGs. A full
search may find fewer than the requested `--top_k`, including none. Both branches
are shown explicitly; the historical default considers the negative branch only.
For cyclic T1 → T2 → T3 ordering add `--phase_mode ordered`.

To request three poses, also provide `--target_orientations_deg` followed by three
world-frame angles. `--orientation_tolerances_deg` sets three individual angular
tolerances; omitting it uses 5 degrees each. Tolerances must be finite and strictly
between 0 and 180 degrees. Position and orientation are checked at the same
optimized phases. The tool frame is located at P with +x parallel to directed
coupler A to B; no independent mounting angle is optimized. See the
[three-pose example and guide](three-pose.md).

The CLI can be replaced by `python -m mechanism_generator.engine`.
`python -m mechanism_generator.engine.models` can replace `mechanism-models`.
Use `mechanism-generate --help` for search controls. The public command always
runs the hybrid engine and the pinned model set. Fixed-only/variable-only execution
and arbitrary model overrides are not exposed by that command.

## Execute an OMTS plan

```sh
omts adapt examples/omts/three_point.omts.yaml --output-dir runs/omts-plan
python runs/omts-plan/run_r25c.py --models-directory models --check-only
python runs/omts-plan/run_r25c.py --models-directory models
```

The runner checks exact installed engine and model hashes. Use the interpreter
where the engine is installed, and regenerate prepared plans after an engine
upgrade. The public model identities remain pinned to the existing exports.
The implementation-profile spelling `r2.5c-fourbar` remains accepted in input
documents; new run plans identify the packaged `r2.5c-public-alpha` implementation.
See the [adapter guide](r25c-adapter.md) for its deliberately narrower subset.

## Inspect results

Each run writes a manifest/config, per-stage optimization histories, all-candidate
CSV, qualification counts, selected-candidate CSV, Pareto and engineering subsets,
and JSON/NPZ/optional PNG for selected designs. Persisted path fields use artifact
names or paths relative to the run root; retain the whole run directory to follow
history references. User-supplied labels and input text are retained as supplied.

`selection_eligible` controls selected results. Unqualified fixed representatives
cannot bypass that rule, and unqualified fallback is disabled. All-candidate and
stage diagnostics remain available when nothing qualifies. Physical assembly is
not sufficient for selection; selection is not structural or dynamic certification.

For pose tasks, inspect `orientation_acceptable`, `pose_acceptable`, the requested
and matched angles, and per-target angular errors alongside the position metrics.
`path_acceptable` retains its position meaning. A candidate with acceptable
positions and a failed angle receives `path_acceptable_but_orientation_failed`
and cannot be selected. The [qualification guide](qualification.md) explains the
remaining transmission, robustness, and compactness checks.

The [example report](engine-smoke.json) records the v0.1.0a2 CPU full-budget run of
the three-point example: 42 candidates, 33 eligible, 5 selected, zero meeting all
preferred engineering thresholds. [The illustrated selected design](../examples/results/three_point.png)
is an example outcome rather than a guaranteed optimum.

## Baseline provenance and subsequent changes

Original source hashes are preserved in [source provenance](engine-source-provenance.json).
The v0.1.0a2 publication added package imports/entry points, safe model loading,
strict missing-model behavior, portable saved paths, shorter run directories, and
qualification-safe fixed representative selection. That publication retained the
underlying proposal, simulation, gradients, objectives, optimization schedules,
and deduplication calculations.

For v0.1.0a2, 49 R2.5b and 11 R2.5c function/class syntax trees matched their
originals unchanged. A reduced-budget run with all three real models, both
branches, Adam/L-BFGS and both continuations matched all compared geometry/quality fields exactly across
14 candidates. Runtime and history-file locations were excluded; details are in
[engine parity](engine-parity.json). This does not establish cross-platform bitwise
reproducibility or general mechanism-quality performance.

Subsequent development added local contribution bundles and optional three-pose
search. The latter changes phase seeding, refinement objectives, best-state
retention, and qualification when angles are requested. The original parity report
does not establish parity for those additions. The neural weights have not been
retrained, and their inputs remain the six position coordinates.

Run tests with `python -m pip install ".[engine,test]"` and `python -m pytest`.
Tests include analytical pose geometry, angular wraparound and gradients, cyclic
ordering, qualification regressions, model verification, safe loading, and a real small optimizer run using synthetic
test weights. Actual release-weight verification is separate from those fixtures.
The constructed position-versus-pose experiment is documented in the
[three-pose guide](three-pose.md); broad success-rate claims require broader evaluation.

The geometric-pose release also matched installed a4 exactly across 1,968
candidate fields (1,472 numeric) on the original point-only task at short budgets.
Both runs selected zero candidates, so this is a regression check rather than
evidence of search success ([report](pose-recovery-point-parity.json)).

The four-stage training source, historical recipes, clean teacher dependencies and
synthetic data generator are now included. See the [training guide](training.md)
and [model card](../MODEL_CARD.md) for the setup check and reproduction limits.
