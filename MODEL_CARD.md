# Mechanism Generator proposal models — research alpha

Version: `0.1.0a2`. Publisher: Mechanismo-AI. License: **Apache-2.0** for all three
weight exports; see [LICENSE](LICENSE) and [NOTICE](NOTICE).

These networks propose planar four-bar geometry from three target positions.
They are initialization models for local numerical refinement, not a complete
mechanism-design system. They do not generate language, images, or human profiles.

## Files and lineage

| Public file | Role | Training variant | State epoch | Parameters |
|---|---|---|---:|---:|
| `balanced.safetensors` | Balanced proposal | R2.4 StreamingTargetTraining | 98 | 1,846,280 |
| `path.safetensors` | Path specialist | R2.4 StreamingTargetTraining | 96 | 1,846,280 |
| `transmission.safetensors` | Transmission specialist | R2.3a WindowedFeasibilityController | 70 | 1,846,280 |

Files are approximately 7.4 MB each. The [machine-readable manifest](src/mechanism_generator/engine/models.json)
provides exact byte counts, SHA-256 hashes, original checkpoint names/hashes,
epochs, export verification, and versioned download locations. The models are
distributed as GitHub release assets, separately from the Python package.

## Architecture and inputs

All three use eight fully connected hidden layers of width 512, SiLU activations,
and an eight-output sigmoid head with the scaling implemented in `MechanismNN`.
Inputs are float32 tensors of shape `[batch, 6]`:
`[x1, y1, x2, y2, x3, y3]`. Outputs are
`[l2, l3, l4, S_ratio, bar_length, base_x, base_y, base_angle]`.
`S_ratio` locates the coupler attachment; `bar_length` offsets the point from the
coupler, and `base_angle` is in radians. The network's ground length is fixed at
6; the downstream optimizer may release it as a ninth geometry parameter.

The historical proposal domain is normalized x in `[-7, 1]`, y in `[1, 7]`.
The public engine does not automatically transform real-world units into this
domain. Ordered input positions and the separate refinement phase-order mode
must be chosen deliberately; the networks were not retrained for arbitrary poses,
timing constraints, or variable ground lengths.

## Training provenance and reproducibility limits

The checkpoints come from the project's synthetic planar-target research lineage.
R2.4 introduced fresh deterministic streams of 2,000 target triples per epoch,
with a fixed development set and a frozen teacher from the corrected-geometry
lineage. R2.3a used a windowed feasibility controller. The fixed development set
and previously examined random targets are development evidence, not untouched
final test sets.

Version 0.1.0a5 adds the complete R2 → R2.2 → R2.3a → R2.4 training source,
recorded recipes, synthetic data regeneration, and cleaned historical dependencies.
The R2 teacher is from state epoch 239; the R2.2 warm start is from epoch 148.
Their exact tensor and prediction parity was verified. See the
[training guide](docs/training.md) and [asset manifest](src/mechanism_generator/training/assets.json).
Small repeatability checks exercise the full chain. A fresh complete training run
has not been shown to reproduce the historical weights bit for bit. The three
released inference models remain unchanged.

## Export and verification

The original archives contained model tensors alongside optimizer, scheduler,
random-generator state, training metadata, and a local path. The public safetensors
files contain only 18 learned tensors each and an allowlisted public metadata
record: format, license, role, variant, state epoch, and original artifact hash.

Every tensor, dtype, and shape was checked against the source checkpoint. All
three exports produced exactly the same predictions as their originals on 128
deterministic in-domain triples per model (seed 9142026, CPU float32); maximum
absolute difference was zero. This is an export parity test, not a model-quality
benchmark. [Export tool](tools/export_models.py) and [manifest](src/mechanism_generator/engine/models.json)
record the conversion and verification. The converter uses a restricted,
hash-gated legacy loader; ordinary public inference accepts safetensors only.

The public solver and historical solver also matched exactly on 1,722 non-timing,
non-path CSV fields across 14 candidates in a reduced-budget comparison.
See [engine parity](docs/engine-parity.json). A separate full-budget three-point
run produced 42 candidates, 33 selection-eligible candidates, and 5 selected
designs; none met every preferred engineering threshold. This is one example,
not a claim of general success. See [example verification](docs/engine-smoke.json).

## Intended use and limitations

Use these models for research, education, and initial four-bar design exploration
with the accompanying geometry solver and qualification reports. Inspect the
resulting geometry, constraints, and application requirements before fabrication.

The models propose geometry from three planar positions. The accompanying engine
also supports optional directed coupler orientations at those same three target
phases, with optional cyclic ordering; see the [three-pose guide](docs/three-pose.md).
It does not establish intermediate orientations, velocity profiles, timing/dwell,
loads, torque, collision clearance, structural strength, fatigue,
manufacturability, or hardware safety. Out-of-domain targets and different task
scales can degrade proposals. Local optimization can miss valid solutions.
Selection eligibility and the historical `engineering_acceptable` label are
kinematic checks only; see [qualification](docs/qualification.md).

## Use

Follow the [engine guide](docs/engine.md) to install, download and verify the
models, and run a three-point task. Downloads are explicit, pinned to a release,
and checked by size and SHA-256. Missing or altered files stop the public command.
