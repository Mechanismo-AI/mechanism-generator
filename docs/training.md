# Reproduce and extend the training pipeline

The package now includes the four stages that produced the released proposal
models. Training uses synthetic triples of planar positions. It does not train
on orientations, contribution bundles, application data, or an external dataset.
The released inference weights remain the historical R2.3a/R2.4 weights.

## Start with a small setup check

Use a short checkout and output path on Windows. Install the engine dependencies:

```sh
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r docs/requirements-engine-cpu.txt ".[engine]"
mechanism-train chain --preset smoke --output runs/training-smoke
```

The smoke preset runs two epochs in each stage with 64 training triples and 32
fixed development triples. It starts R2 from random initialization and passes
each selected model to the next stage. It needs no model download. It verifies
the pipeline, not design quality. A selected checkpoint can remain the initial
state even when the terminal model has changed; the summary records both.
When a smoke stage has no qualifying checkpoint, its explicitly marked fallback
uses terminal weights. The historical preset stops instead of making that substitution.

For a repeatability check, run:

```sh
python tools/check_training.py --output runs/training-check
```

This executes two fresh chains and compares their complete terminal numerical
states, including model, optimizer, scheduler, random generators, target data,
and controller state. It excludes timestamps, the teacher file location and its
container hash. It also verifies two epochs of activity, nonzero gradients and a
saved model change in every stage. Safety recovery can restore an earlier terminal
state; that is recorded separately. The compact result is `verification.json`.
The [recorded CPU check](training-smoke.json) passed all four stages; R2.2 exercised
a recovery that restored its earlier model, and the report retains that outcome.

## Historical sequence

| Stage | Initialization | Frozen teacher | Selection passed onward |
|---|---|---|---|
| R2 GeometryFix | Random, seed 101 | None | Best fixed-development loss |
| R2.2 ConstrainedTransmission | R2 selection | Same R2 model | Best feasible transmission |
| R2.3a WindowedFeasibilityController | R2.2 selection | Same R2 model | Best feasible transmission |
| R2.4 StreamingTargetTraining | R2.3a selection | Same R2 model | Best composite; best path is also saved |

R2.1 and R2.3 are source ancestry, not extra execution dependencies. The
[packaged recipes](../src/mechanism_generator/training/recipes.json) preserve the
recorded command settings: seed 101, 2,000 training triples, 512 fixed development
triples, and up to 250 epochs per stage. The original stopping and recovery
controllers can end a run earlier. The wrapper detects fatal training conditions
even when the historical script returns a zero process status.

Run the full sequence from random initialization:

```sh
mechanism-train chain --preset historical --output runs/historical-chain
```

This is a substantial training job; the two-epoch setup check does not estimate
its quality or total cost. The command uses CPU with one numerical thread by
default. `--epochs`, `--points`, `--seed`, or `--device cuda` create a custom run,
recorded as such in the summary. Run directories must be new.

To start from the exact cleaned historical dependencies instead:

```sh
mechanism-train assets download --directory training-models
mechanism-train assets verify --directory training-models
mechanism-train run r24 --preset historical --assets-directory training-models --output runs/r24
```

Downloads are explicit and checked against the versioned
[asset manifest](../src/mechanism_generator/training/assets.json). It contains the
R2 teacher, the R2.2 warm start, and the existing R2.3a transmission model.
All three are Apache-2.0. `run r22` and `run r23a` choose their corresponding
dependencies from the same directory. For your own experiment, supply both
`--teacher model.safetensors` and `--initialize-from student.safetensors` instead.

## Synthetic data and separation

For seed 101, the 512 fixed development triples are generated with an independent
CPU generator seeded 3102. Uniform float32 draws are scaled to x in `[-7, 1]`
and y in `[1, 7]`. Their contiguous tensor bytes have SHA-256
`4636ea89d5210676c17fe66cf385008ab043ae876c04fdbfea72ad423e911b7f`.
Regeneration matched the historical tensor exactly. R2.4 stream index `i` uses
seed `101 + 500000 + 104729*i`; all 100 recorded historical stream digests matched
regeneration. No separately licensed external dataset is required.

```sh
mechanism-train data --output development-targets.pt
mechanism-train data --stream-index 0 --output stream-0.pt
```

The fixed set guides checkpoint selection, recovery and stopping. It is
development data, not an untouched test set. The pose corpus is a separate
kinematic search evaluation and is not training input. Future model-quality
comparisons need independent task splits and several training seeds.

## Artifacts and sharing

Each stage writes local checkpoints, metrics, environment details, configuration,
and a training log. These local records can contain machine paths. They are not
automatically submitted by the contribution flow. The wrapper writes
`training-summary.json` and per-stage `summary.json` with source hashes, dependency
hashes, effective settings, selected and terminal identities, and relative artifact
names. A successful stage also writes `selected.safetensors` containing model
tensors and a small allowlisted metadata record.

To export another checkpoint, choose its actual path inside the timestamped run:

```sh
mechanism-train export runs/r24/r24/V5.3-R2.4_StreamingTargetTraining/RUN/best_path.pth --output models/my-path.safetensors
```

Replace `RUN` with the created run directory. The public exporter accepts restricted
training states produced by this package; it does not enable arbitrary pickle
execution or convert unknown legacy archives. It verifies all 18 tensor names,
shapes, float32 dtypes and finite values, and refuses an existing destination.
Share the cleaned weights, reviewed summary and appropriate evaluation evidence,
not the whole local run directory.

The standard `mechanism-generate` command deliberately pins the released model
set. Use the research entry point to evaluate your own compatible weights:

```sh
python -m mechanism_generator.engine.r25c --balanced_model models/my-balanced.safetensors --path_model models/my-path.safetensors --transmission_model models/my-transmission.safetensors --targets -6 2 -2 6 0.5 3.5 --branches both --device cpu --headless --output_root runs/custom-models
```

Use R2.4 best composite for balanced, R2.4 best path for path, and R2.3a best
feasible transmission for transmission when following the historical recipe.
Every resulting design still needs the engine's normal independent qualification.

## What has and has not been reproduced

The source audit verified the exact historical initialization chain, dataset
generation and recorded command settings. The packaged trainers preserve all
numerical functions/classes except checkpoint loading and random-state
serialization. The latter stores NumPy state as primitives and a tensor so new
checkpoints support `weights_only=True`. A guard prevents importing a trainer
from starting a run. Source hashes and the audited changes are recorded in
[source provenance](../src/mechanism_generator/training/source_provenance.json).

The clean dependency exports match their original tensors and predictions exactly.
The repeatability check establishes small-run reproducibility in the recorded
environment. This release does not claim a fresh full four-stage run reproduces
the historical model bits, stopping epochs, or quality. The historical environment
record did not fully lock numerical libraries and threading; versions, hardware
and kernels can change results. Full checkpoint resume and cross-device numerical
identity have not been validated. The preserved trainer modules expose additional
research arguments through `python -m mechanism_generator.training.r24 --help`.

Training code, recipes, generated synthetic examples and clean public dependencies
are covered by the repository's Apache-2.0 license. Third-party libraries retain
their own licenses.
