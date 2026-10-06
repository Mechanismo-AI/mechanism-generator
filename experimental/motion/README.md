# Experimental mechanism motion solver

A self-contained CPU solver for one planar six-bar family, with pose and first/second crank-angle derivative targets. This package is an experimental release candidate; it does not replace the released four-bar engine or its OMTS adapter.

The frozen candidate chooser passed a new synthetic 80-target paired screen: 78 strict successes versus 74 for the private research baseline, four gains and no losses. Every cohort reached at least 15/16. That screen is evidence for this fixed-phase, known-branch family, not proof of general mechanism design or hardware performance.

## Run the supplied example

From this directory, install into a separate Python 3.12 environment with the documented CPU dependencies:

```sh
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install numpy==2.5.1
python -m pip install .
mechanism-motion examples/normalized-motion.json --seed 580000050 --output result.json
```

`python -m mechanism_motion` provides the same interface. `--baseline` uses the original random fallback for comparison. `--threads` defaults to one CPU thread. The example is an already studied synthetic mounting-offset target; it is a reproducibility example, not a new evaluation. It qualifies in 150 refinement evaluations with the frozen chooser.

The solver performs no network access, training, uploads or automatic publication. It writes the requested result file atomically. A completed search can return `qualified: false`; this is a retained failed candidate, not an accepted mechanism.

## Input contract

The JSON object contains exactly five fields:

|Field|Shape|Meaning|
|---|---|---|
|`theta_rad`|12 numbers|Increasing phases `0, 2π/12, …, 11×2π/12`|
|`branches`|2 signs|Known assembly choices, each -1 or +1|
|`q`|12 × 3|`[x, y, directed orientation in radians]`|
|`v`|12 × 3|First derivatives of those quantities with respect to crank angle θ|
|`a`|12 × 3|Second derivatives with respect to θ|

Positions must be centered, with bounding-box diagonal equal to one. Spatial derivative values use that same normalized length unit. All input values must be finite. Arbitrary phase grids, unknown branches, extra fields and unnormalized tasks are rejected. The input does not accept generating geometry or witness parameters.

These derivatives do not prescribe an operating speed. Given a drive law with crank angular velocity ω and acceleration α, the chain rule gives output velocity `v × ω` and output acceleration `a × ω² + v × α`. Physical spatial units also require the chosen length scale. The current interface does not accept that drive law or rate payload capacity, motor requirements or collision clearance.

## Result and strict qualification

The result includes normalized mechanism geometry, phases, selected raw parameters, candidate/attempt diagnostics, qualification, model hashes and the refinement count. The mechanism graph is ground O-Q-R, crank O-A, rigid body A-B-D, rocker B-Q, output body D-C and rocker C-R; output body D-C carries the tool point and orientation.

Strict qualification retains the research checks: normalized position error at most 0.01, orientation error at most 1 degree, spatial first/second derivative errors at most 0.02/0.05, angular first/second derivative errors at most 2/5 degrees per corresponding crank-angle derivative. Full-cycle assembly, size bounds, transmission, constraint residual and regularity must also pass. Target samples alone are insufficient.

The original learned attempt and continuation/restart selector are preserved. When restart is permitted, the chooser ranks a random candidate and eight orientation-shifted learned candidates using initial diagnostics only. One selected fallback is refined. Both attempts together use at most 200 objective/gradient evaluations. Proposal generation and initial/final qualification add processing outside that count; no wall-time advantage is claimed.

## Assets and verification

The package includes clean proposal tensors and statistics, the frozen continuation selector and the frozen candidate chooser. `assets/manifest.json` records checksums and provenance hashes. Loading uses `weights_only=True`, validates the checksums and checks tensor dimensions, scales, finite values and feature schemas. No optimizer state, training examples, account identity or local study paths are exported in the inference assets.

The integration checks cover exact proposal/statistics tensor parity, eight stored screen cases, both baseline and chooser trajectories, initial candidate scores/rankings, strict qualification, 11 invalid-input/seed cases and the 200-evaluation cap. An installed wheel runs in isolated Python mode and reproduces the example without importing any historical research module. Archived verification artifacts are in evidence/. Only the currently recorded runtime was tested.

All code and included inference assets use Apache-2.0. This release candidate remains experimental. The existing four-bar engine and its published model files are unchanged.

See [MODEL-CARD.md](MODEL-CARD.md) for training provenance, model-only results, data splits and reproducibility limits.

## Portable verification and build

From the source package root, with the dependencies installed:

```text
python -m unittest discover -s tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
python -c "from setuptools.build_meta import build_sdist; build_sdist('dist')"
```

The tests need only this source package and its bundled fixtures. They check eight frozen cases under both policies, input rejection, input/output aliases, temporary-file safety and asset corruption/schema rejection. Exact parity was verified on the runtime in runtime-versions.json. To test an installed wheel rather than src, install it into your environment and set MOTION_TEST_INSTALLED=1 before running the same test command. No training, upload or publication occurs.

The CLI rejects output paths that identify the input, including existing hard links. Output is written through a unique temporary file in the destination directory and then replaced atomically. Inputs accept JSON numeric arrays of the documented shapes; strings, booleans, nulls and objects are rejected.
