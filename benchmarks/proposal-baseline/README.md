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
