# Mechanism Generator

Open tools for describing motion requirements and developing inspectable mechanism
designs. The long-term aim is to help designers create purpose-built, synchronized
automation using open solvers, training code, and model weights.

**Current status: repository foundation and OMTS v0.1 draft.** This package validates
motion task documents and prepares a restricted subset for an external four-bar
research engine. It does not include that engine, model weights, or a complete
mechanism-design application yet.

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
during either command. The generated runner requires separately supplied research
artifacts; see the [adapter guide](docs/r25c-adapter.md).

## Two examples, with different purposes

| Example | Document validation | R2.5c adaptation |
|---|---|---|
| [Three-point four-bar](examples/omts/three_point.omts.yaml) | Passes | Prepares an independent cyclic four-bar run |
| [Synchronized line](examples/omts/synchronized_line.omts.yaml) | Passes | Rejected: illustrates future poses, loads, dwell, and synchronization |

The adapter accepts normalized planar coordinates, exactly three target positions,
optional cyclic ordering, hybrid ground-link search, and the requirements listed
in its [profile](docs/r25c-adapter.md). Unsupported operational fields are rejected,
including unsupported soft constraints. They are never silently discarded.

## Project contents

- [OMTS draft specification](specs/omts/0.1/specification.md)
- [Normative schema](src/mechanism_generator/omts/schema.json), bundled with the package
- Shared schema/semantic validation, capability checks, and run preparation
- [Qualification terminology](docs/qualification.md) and [development roadmap](docs/roadmap.md)
- Focused regression tests and continuous integration for Windows and Linux

The first runnable engine release will package the existing research pipeline:
neural proposals → local refinement → physical/kinematic checks → diverse designs.
Orientation synthesis, prescribed timing/dwell, dynamics, collision checks, and
multi-mechanism synchronization are future capabilities.

## Contribute and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Code, specification, schema, and examples
are licensed under [Apache-2.0](LICENSE), copyright 2026 Mechanismo-AI contributors.
No model weights or datasets are distributed in this foundation release; future
artifacts will state their licenses explicitly.
