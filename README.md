# Mechanism Generator

Open tools for describing motion requirements and developing inspectable mechanism
designs. The long-term aim is to help designers create purpose-built, synchronized
automation using open solvers, training code, and model weights.

**Current status: runnable four-bar research alpha with three-pose targets and OMTS v0.1 draft.**
The package includes the R2.5c/R2.5b solver, task validation, and a strict OMTS
adapter. Three Apache-2.0 proposal models are available as verified GitHub release
downloads. A task can now specify the output point's position and directed coupler
orientation at each of three target phases. This is a planar kinematic research
tool; prescribed timing/dwell, dynamics, collisions, and
synchronization remain future work.

## Generate a mechanism

After creating and activating a virtual environment, install from this checkout:

```sh
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install ".[engine]"
mechanism-models download --directory models
mechanism-generate --models-directory models --targets -6 2 -2 6 0.5 3.5 --branches both --device cpu --headless --output_root runs/demo
```

Python 3.12 is the tested engine environment. On Windows, choose a short checkout
and output location. Add `--quick` for a smaller search budget. For ordered targets, add
`--phase_mode ordered`; choose `--crank_direction positive`, `negative`, or `either`.
The default remains positive. Either runs two complete search budgets with separate
results and reviews. Assembly branch (`--branches`) is a separate choice. Read the
[engine guide](docs/engine.md) for installation, OMTS execution, and output details,
and the [model card](MODEL_CARD.md) for provenance, licensing, and limitations.

![One selected design from the three-point example](examples/results/three_point.png)

This illustrated candidate passed practical selection criteria, but did not meet
all preferred engineering thresholds. It is not a hardware-validated design.

To control the direction of the carried object as well as its position, try the
[three-pose guide](docs/three-pose.md). The first pose capability uses a tool frame
at output point P with its positive x-axis parallel to the directed coupler A to B.
The existing models propose geometry from positions; pose tasks also use a
deterministic geometric initializer and local refinement. No retraining is needed
to use this feature. See the [broader pose evaluation](docs/pose-corpus.md).

The [dimensioned tabletop-transfer case study](examples/tabletop-transfer/README.md)
records a practical brief that the released solver did not satisfy, including
independent millimetre checks and the measured reasons candidates were rejected.
A [controlled follow-up](examples/tabletop-transfer/Diagnosis.md) found a kinematic
candidate inside the original tolerances using an experimental geometric search.
Release **v0.1.0a7** integrates that search with
bounded angular-tolerance initialization and optional sampled panel screening.
See the [integration guide](docs/tolerance-and-panel.md) and its reproducible
tabletop example. Published inference weights remain unchanged.

## Train and refine proposal models

The full R2 â†’ R2.2 â†’ R2.3a â†’ R2.4 training sequence is packaged with historical
recipes, a synthetic data generator and verified starting weights. Start with a
small four-stage check:

```sh
mechanism-train chain --preset smoke --output runs/training-smoke
```

The [training guide](docs/training.md) covers full runs, warm starts, clean weight
exports and reproducibility limits. The smoke run checks the pipeline; it does
not replace the released proposal models or establish model quality.

## Share a run

Runs now prepare a local contribution bundle by default. Open
`contribution/review.html` inside the run directory to choose what to share,
inspect the outgoing data, and download a reviewed file. You can then attach it
to a GitHub submission for possible future solver and training improvements.
Sharing is voluntary, and local preparation sends no data. Read the
[contribution guide](docs/contributing-results.md) for the review and submission
steps, including what becomes public when you attach a file.

## Try the OMTS tools

Requires Python 3.10 or later. From a checkout of this repository, install into a
virtual environment. Activate it using the command for your platform:

```sh
python -m venv .venv
# Linux / macOS:
. .venv/bin/activate
```

```powershell
# Windows PowerShell, after creating .venv:
.\.venv\Scripts\Activate.ps1
```

Then run these commands on either platform:

```sh
python -m pip install -e ".[test]"
omts validate examples/omts/three_point.omts.yaml
omts adapt examples/omts/three_point.omts.yaml --output-dir generated/demo
python -m pytest
```

`python -m mechanism_generator.omts` can replace `omts` in these commands.

Validation checks both the JSON Schema and cross-field semantics. Adaptation
checks the narrower implementation profile and writes a run plan, per-task target
CSVs, and a portable Python runner. It refuses existing output directories.

**A valid document or prepared plan is not a solved mechanism.** No optimizer runs
during either command. The generated runner uses the installed engine and downloaded weights; see the [adapter guide](docs/r25c-adapter.md).

## Examples, with different purposes

| Example | Document validation | R2.5c adaptation |
|---|---|---|
| [Three-point four-bar](examples/omts/three_point.omts.yaml) | Passes | Prepares an independent cyclic four-bar run |
| [Three-pose four-bar](examples/omts/three_pose.omts.yaml) | Passes | Prepares three ordered positions and directed orientations |
| [Synchronized line](examples/omts/synchronized_line.omts.yaml) | Passes | Rejected: includes unsupported loads, dwell, and synchronization |

The adapter accepts normalized planar coordinates, exactly three target positions,
optional orientations on all three targets, optional cyclic ordering, hybrid
ground-link search, and the requirements listed in its
[profile](docs/r25c-adapter.md). Unsupported operational fields are rejected,
including unsupported soft constraints. They are never silently discarded.

## Project contents

- [OMTS draft specification](specs/omts/0.1/specification.md)
- [Normative schema](src/mechanism_generator/omts/schema.json), bundled with the package
- Shared schema/semantic validation, capability checks, and run preparation
- [Qualification terminology](docs/qualification.md) and [development roadmap](docs/roadmap.md)
- Focused regression tests and continuous integration for Windows and Linux

The public engine runs the research pipeline:
neural proposals Ã¢â€ â€™ local refinement Ã¢â€ â€™ physical/kinematic checks Ã¢â€ â€™ diverse designs.
Richer orientation paths, prescribed timing/dwell, dynamics, collision checks, and
multi-mechanism synchronization are future capabilities. Reproducible training and
broader evaluation support that development; released models remain ready to use.

## Contribute and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Code, specification, schema, examples, and
the three public model-weight exports are licensed under [Apache-2.0](LICENSE),
copyright 2026 Mechanismo-AI contributors. Training datasets are not included.
See [releases](https://github.com/Mechanismo-AI/mechanism-generator/releases) for
versioned model assets and checksums.
