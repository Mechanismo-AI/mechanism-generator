# Proposal baseline: do the learned models beat random starts?

The engine's only learned component is the proposal step, `r25b.predict_initial_params`.
Everything after it is the same for every proposal: phase seeding, refinement,
physical checks, and qualification. This benchmark swaps that single function
and compares three arms on the same tasks with the same start count and budget:

| Arm | Proposal source |
|---|---|
| `learned` | the published models, untouched |
| `random` | one random proposal per start, drawn from the engine's own design space and passed through the same projection |
| `random_pool` | the best of 128 random proposals, ranked by distance to the targets (cheap screening, no learning) |

Tasks are three-point, unordered, position-only targets, which is the published
models' home turf. Each task comes from a random valid crank-rocker that lies inside
the engine's design-space bounds, so every task is known to be solvable. The
witness mechanism is recorded in the corpus but is never given to the solver.

## Run it

From the repository root, with the engine installed and the models downloaded:

```sh
python benchmarks/proposal-baseline/bench.py smoke --models models     # 2 tasks, --quick; checks the harness
python benchmarks/proposal-baseline/bench.py corpus                    # freezes 60 tasks to corpus.json
python benchmarks/proposal-baseline/bench.py run --models models       # resumable; rerun to continue
python benchmarks/proposal-baseline/bench.py summarize
```

`run` uses one fewer worker than your CPU count by default (`--workers N` to
change), with one thread per worker. Results go to `runs/pb/`, with one small
JSON file per task and arm, plus logs and the full engine output.
`summarize` writes `runs/pb/summary.json`.

### Pose and ordered tasks

The same witness four-bars can produce pose tasks (three positions plus the
directed coupler orientation) and ordered tasks (three positions reached in crank
order). The analytic position starter does not support these task types, so compare
`learned`, `random`, and `random_pool`. Pose tasks already include the engine's
deterministic pose-geometry seeds in every arm. For pose tasks, the summary
also reports `pose_acceptable`, meaning position and orientation are both met.

```sh
python benchmarks/proposal-baseline/bench.py corpus --type pose
python benchmarks/proposal-baseline/bench.py run --models models --corpus benchmarks/proposal-baseline/corpus-pose.json --results runs/pb-pose --arms learned random random_pool
python benchmarks/proposal-baseline/bench.py summarize --results runs/pb-pose
```

Use `--type ordered`, `corpus-ordered.json`, and `runs/pb-ordered` for ordered tasks.

## Reading the result

A task counts as a success for an arm when the engine finds at least one
selection-eligible design, which is its own notion of "found a design". The
stricter engineering-acceptable count is reported too. The summary gives paired
wins and losses against `learned` and an exact two-sided sign test on those
discordant tasks.

If `random` or `random_pool` matches `learned`, the models are not pulling their
weight on their home task, and the learned line should be shelved until it can
earn its place. If `learned` clearly wins, that is a real, recorded asset worth keeping.

The `analytic_pool` arm was added after the first four arms had run. It uses no
learned proposals at all: `random_pool` starts plus the analytic position
starter (`--position_geometry`).

## Result (2026-10-23)

Corpus: 60 tasks, `corpus.json` sha256
`e1337a90fb5e0953eba3a3dae1c755bf789eddef39b4d9bf92203eb0bdca58e1`.
Full search settings (not `--quick`), `--branches both`, seed 101, run on one
12-core Linux machine. No arm crashed, and every arm took about 2 minutes per task.

| Arm | Tasks with a selection-eligible design | Engineering-acceptable | Median best mean error |
|---|---|---|---|
| `learned` (published models) | 28 / 60 | 9 / 60 | 0.00472 |
| `random` | 41 / 60 | 32 / 60 | 0.00949 |
| `random_pool` | 53 / 60 | 45 / 60 | 0.00269 |
| `geometric` (models + analytic starter) | 58 / 60 | 47 / 60 | 0.00557 |
| `analytic_pool` (no models) | **60 / 60** | **54 / 60** | 0.00275 |

Paired wins on tasks where two arms disagree (exact two-sided sign test):

| Comparison | Selection-eligible | Engineering-acceptable |
|---|---|---|
| analytic_pool vs learned | 32–0 (p < 0.001) | 45–0 (p < 0.001) |
| analytic_pool vs geometric | 2–0 (p = 0.50) | 7–0 (p = 0.016) |
| analytic_pool vs random_pool | 7–0 (p = 0.016) | 10–1 (p = 0.012) |
| random_pool vs learned | 27–2 (p < 0.001) | 38–2 (p < 0.001) |
| random vs learned | 20–7 (p = 0.019) | 26–3 (p < 0.001) |

**Finding.** On their own home task (unordered three-point position synthesis),
the published proposal models perform worse than one random guess per start.
The engine without them is stronger: `analytic_pool` loses no task to
`learned` or `geometric`, and one task to `random_pool` (engineering-acceptable,
10–1). It was not compared head-to-head with `random`. The analytic starter also
does better without the learned starts than with them.

**Limits.** This is one synthetic corpus with one seed. The tasks are generated from
the same kind of design space that the random arms sample, which may favour
them. This result covers position-only tasks, not pose, ordered, panel, or real
briefs. It does not test the model weights on the data they were trained on.

**Implication.** A model-free start portfolio (`analytic_pool`) is the stronger
default for position tasks. It also removes the weights download from the
critical path. Making it the default is a separate change, and it should be
checked on the pose and ordered task types first.

## Ordered tasks (2026-10-23)

Corpus: 60 ordered three-point tasks, `corpus-ordered.json` sha256
`dba65f22a8f07b18406ff2b7302389f523c8c7484b94fe7e255409268523a41d`. Same settings as
the position run, with `--phase_mode ordered`. No arm crashed.

| Arm | Selection-eligible | Engineering-acceptable | Median best mean error |
|---|---|---|---|
| `learned` | 30 / 60 | 13 / 60 | 0.00637 |
| `random` | 30 / 60 | 20 / 60 | 0.00931 |
| `random_pool` | 54 / 60 | 42 / 60 | 0.00350 |

Against `learned`: `random` 14–14 on selection-eligible (p = 1.0), 14–7 on
engineering-acceptable (p = 0.19). `random_pool` 27–3 (p < 0.001) and 31–2 (p < 0.001).

**Finding.** On ordered tasks the published models match one random guess per start,
and a 128-sample random screen clearly beats them. This agrees with the position result.
The ordered run does not include `analytic_pool`, because the analytic starter supports
unordered positions only.

**Limits.** Same as the position result: one synthetic corpus, one seed, and tasks
drawn from the same design space the random arms sample.

## Pose tasks (2026-10-24)

Three-pose synthesis has an exact closed-form solution for any three poses (the
circumcentre construction in `pose_seeds.py`), and every arm includes those seeds.
So pose tasks test whether proposals add anything beyond the analytic construction.

Two corpora were run, both with `learned`, `random`, and `random_pool`, with no crashes:

- `corpus-pose.json` (sha256 `a9a72b2d…31d99af`), poses taken from witness four-bars: every
  arm solved 60/60, with identical median error (3.6e-12).
- `corpus-pose-free.json` (sha256 `b0b63e48…1c58dc7`), random positions and orientations
  with no witness: every arm solved the same 11/60 tasks (5/60 engineering-acceptable),
  with identical median error (2.6e-12). `solvable_by_any_arm` = 11. Most random pose
  triples admit no valid four-bar within the engine's limits.

Selected designs on the witness-free corpus, by start origin: 151 of 152 came from
`pose_geometry`. The other came from a `random_pool` start, which reuses a model slot
label. The learned models produced none.

**Finding.** On pose tasks the analytic construction does all the work. Proposals,
learned or random, never solved a task the construction missed. The models are not worse
here; they are redundant.
