# Additional three-pose development and evaluation corpus

This corpus supplements the original [four development probes](pose-benchmark.json).
It does not replace those cases or change their success thresholds. It contains
eight additional development tasks and eight reserved evaluation tasks generated
from separate, predeclared seeds. It is a small constructed corpus, not a
representative sample of practical design problems.

## Measured recovery results

With the same requested poses, success thresholds, solver seed and configured
standard optimizer budgets, the frozen source with geometric initialization
produced the following results:

| Case set | Released v0.1.0a4 | Recovery-enabled source | Evidence |
| --- | ---: | ---: | --- |
| Original four development probes | 2 / 4 | 4 / 4 | [Original-case regression](pose-recovery-regression.json) |
| Additional eight development tasks | 0 / 8 | 8 / 8 | [Development comparison](pose-corpus-development.json) |
| Eight reserved evaluation tasks | 0 / 8 | 8 / 8 | [Reserved comparison](pose-corpus-evaluation.json) |

All 36 newly executed solver runs completed without execution failures. The
original-four baseline uses its existing published evidence. No failed or
no-solution case was removed from these comparisons. The initializer and engine
settings were frozen before reserved evaluation began and were not tuned against
those evaluation outcomes.

The source adds 4,096 geometric samples and up to six geometric seeds per task,
with additional seed refinement. Consequently this is an accuracy comparison at
matching optimizer **step settings**, not equal total compute. Reports retain
the initializer survivor counts, actual returned/refined counts and timings.
Several jobs ran concurrently; their wall times support no controlled speed claim.
These small constructed case sets establish these specific recovery results, not
a general success rate or engineering certification.

The frozen files are in
[`examples/benchmarks/pose-corpus-v1`](../examples/benchmarks/pose-corpus-v1/manifest.json).
The manifest records each task-file hash, individual case hash, reference-file
hash, generator version/hash and generation protocol. Development seed: `731204`;
reserved evaluation seed: `902617`. These seeds generate mechanisms and tasks;
the solver uses a separate seed, default `101`.

## Predeclared construction and scoring

The generator samples ground length 6, other link lengths, coupler-point location,
base rotation, assembly branch and three ordered input phases. Independent NumPy
circle intersections produce each requested position and directed coupler angle.
Translations keep positions strictly inside the historical proposal-model box
`-7 < x < 1`, `1 < y < 7`.

Only declared geometric conditions affect acceptance: full-cycle assembly,
Grashof/crank-shortest geometry, at least 20 degrees of full-cycle minimum
transmission, separated targets and valid solver design bounds. The first eight
accepted cases from each seed are retained. Solver outcomes never determine which
cases enter the corpus. The manifest gives all sampling bounds and filters.

Success requires at least one **selected, engine-eligible** candidate with:

- Mean position error at most **0.05** and maximum position error at most **0.075**.
- Absolute circular orientation error at most **2 degrees at every target**.
- Independently verified full-cycle assembly.

Both implementations face the same requested poses and thresholds. The independent
evaluator reconstructs positions and orientations from saved candidate parameters
and phases; it does not trust the solver's error columns. No-solution outcomes,
timeouts and failed solver runs remain in the denominator. A known feasible
reference does not count as a discovered solution.

Witness parameters live in separate `*.references.json` files. The runner reads
only the manifest and `*.tasks.json`; witnesses are never passed to the solver.
Reference feasibility is kinematic and does not establish strength, collision
safety or manufacturability.

## Keep evaluation separate

Use the development split while designing and tuning the method. Freeze source,
settings and model hashes before running the evaluation split. The command
defaults to development; evaluation requires `--split evaluation` explicitly.

These are publicly reproducible reserved cases, not secret test data. If evaluation
results influence further changes, treat that split as development and create a
fresh evaluation corpus before making a new reserved-evaluation claim. Keep the
failed original probes and all failed corpus cases in reports.

## Run one implementation

Install the normal engine dependencies and download the released model weights.
From a checkout, run:

```console
python tools/pose_corpus.py run --models-directory models --output corpus-a4-development --label v0.1.0a4 --split development --budget standard
```

The eight-task default uses all three released proposal models, paired profiles,
both assembly branches, ordered phases and the same pinned standard optimizer
budgets as the original benchmark. CPU runtime depends on hardware and initializer
work. `--budget quick` is useful for checking execution, but its results are a
different experiment and must not be compared with standard-budget results.

`--engine-python` can select an interpreter containing a separately installed
baseline. The child process inherits `PYTHONPATH`, so keep any source checkout out
of the baseline environment. Labels describe intent; the recorded engine/model
hashes establish what actually ran. Source-checkout testing can use its own
environment or an explicit `PYTHONPATH` pointing to that checkout's `src` directory.

For a source version implementing the geometric initializer, its controls can be
declared explicitly:

```console
python tools/pose_corpus.py run --models-directory models --output corpus-source-development --label source --split development --budget standard --initializer-samples 4096 --initializer-seeds 6
python tools/pose_corpus.py compare corpus-a4-development/report.json corpus-source-development/report.json --output corpus-development-comparison.json
```

Omit initializer flags for v0.1.0a4, which does not provide that feature. The
comparison checks that tasks, case hashes, thresholds, model hashes, solver seed,
evaluator and configured optimizer budgets match. It refuses missing or repeated
cases and source changes within one run. All cases remain in the denominator.

Matching optimizer step settings **does not mean equal total compute**. Extra
initialization samples and refinement seeds add work. Reports separately preserve
requested/effective initializer settings, candidate counts, generation/verification/
refinement times and per-stage survivor counts when available. Wall times are
descriptive; controlled speed claims require equivalent hardware and workload.

## Regenerate and audit

```console
python tools/pose_corpus.py generate --output regenerated-corpus
```

Generation uses no model weights. Repeated generation is deterministic in the
recorded numerical runtime; the checked-in task bytes and hashes are authoritative
when library/platform floating-point details differ. The tool refuses to silently
replace an existing corpus with different contents. Use a new version/directory
for a deliberate protocol change.

Each run writes `report.json` plus local solver outputs. Nothing uploads or posts
automatically. A comparison contains coverage, failures and the additional
initializer work; it does not turn this small corpus into a general performance
guarantee.
