# Job sync-corpus-01: synchronized-pair evaluation corpus

**Purpose.** Produce the first measured evidence base for OMTS v0.2
synchronization: a corpus of deterministic variants of
`examples/omts/synchronized_pair.omts.yaml`, each adapted, executed with the
real engine, and line-verified (S4). The output is a per-variant record of
candidate counts, runtimes, and verification outcomes — including failures and
zero-selection searches, which are data, not errors. These results feed the S5
design (which failure modes dominate) and the spec review.

**Machine.** Any idle CPU box, Python 3.12, engine installed as in the engine
guide ("pip install .[engine]", then "mechanism-models download --directory
models"). This branch only: `git clone -b omts-v02-sync-spec ...` or
`git fetch && git checkout omts-v02-sync-spec`.

**Sizing (8 hours).** Each variant runs two full three-target searches. On a
slow CPU expect roughly 30–60 minutes per task at full budget, so:

- smoke pass first: `corpus_run.py --count 2 --quick` (about 15–30 min total)
- then the real run: `corpus_run.py --count 6` (about 6–12 h; start before bed)

If the smoke pass is slow, drop to `--count 4`. The job is resumable per
variant: completed variants are skipped on rerun.

## Run

```sh
. .venv/bin/activate
python jobs/sync-corpus-01/corpus_run.py --count 2 --quick     # smoke
python jobs/sync-corpus-01/corpus_run.py --count 6             # overnight
```

Output lands in `runs/sync-corpus-01/`:

- `corpus_pair_NN/` — the variant document, prepared plan, per-task engine
  results, and `line_result.json` from the S4 verifier;
- `summary.json` — one row per variant: status, selected-candidate counts,
  combination and passing-combination counts, wall-clock times, errors.

## Reporting back

Share or commit `runs/sync-corpus-01/summary.json` plus each
`corpus_pair_NN/line_result.json` (engine result trees are large and
gitignored; keep them locally). Note the CPU model and Python version.
Interpretation happens next session: which relations never verify, whether
windows need widening, and what S5 must actually optimize.
