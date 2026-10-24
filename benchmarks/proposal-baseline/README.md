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
They never beat the engine without them: `analytic_pool` loses no task to any
arm on either measure. The analytic starter also does better without the
learned starts than with them.

**Limits.** This is one synthetic corpus with one seed. The tasks are generated from
the same kind of design space that the random arms sample, which may favour
them. This result covers position-only tasks, not pose, ordered, panel, or real
briefs. It does not test the model weights on the data they were trained on.

**Implication.** A model-free start portfolio (`analytic_pool`) is the stronger
default for position tasks. It also removes the weights download from the
critical path. Making it the default is a separate change, and it should be
checked on the pose and ordered task types first.
