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
  results, and `plan/line_result.json` from the S4 verifier;
- `summary.json` — one row per variant: status, selected-candidate counts,
  combination and passing-combination counts, wall-clock times, errors.

## Reporting back

Share or commit `runs/sync-corpus-01/summary.json` plus each
`corpus_pair_NN/line_result.json` (engine result trees are large and
gitignored; keep them locally). Note the CPU model and Python version.
Interpretation happens next session: which relations never verify, whether
windows need widening, and what S5 must actually optimize.

## Follow-up sync-corpus-04: applied offsets, reused searches

**Purpose.** Measure whether the v0.2 `applied_offsets` mechanism turns the
corpus-03 failures into verified lines, without paying for six new engine
searches. The anchor probes (corpus-03) found feasible catcher-offset
intervals per variant; the offsets below are one human-reviewed pick inside
each interval.

**Key fact.** Applied offsets are a timeline composition, applied by the S4
verifier after the engine search. They never change the per-task search, so
the corpus-03 engine result trees can be reused verbatim via `--results-from`.
Only validate, adapt, and verify run again — minutes, not hours.

The offsets live in `offsets-corpus-04.json` (review them before running):

- `corpus_pair_01` catcher 105 (probed feasible interval 86–126),
- `corpus_pair_02` catcher 20 (interval 4–33; gate alternative 332–356),
- `corpus_pair_03` catcher 333 (interval 320–351; proven by hand in
  `plan-o333`, `LINE VERIFIED combinations=25 passing=5`),
- `corpus_pair_04` catcher 207 (intervals 195–219 and 325–343; first picked),
- `corpus_pair_05` no offset (corpus-03 had no candidates to re-time),
- `corpus_pair_06` no offset (negative control: must stay unverified).

## Run (sync-corpus-04)

```sh
. .venv/bin/activate
python jobs/sync-corpus-01/corpus_run.py \
  --offsets jobs/sync-corpus-01/offsets-corpus-04.json \
  --results-from runs/sync-corpus-03 \
  --output-dir runs/sync-corpus-04
```

Output lands in `runs/sync-corpus-04/` with the same layout as corpus-01,
except each variant's plan reuses the engine results copied from
`runs/sync-corpus-03` (summary rows record `applied_offsets` and
`results_reused: true`). If a variant's source results are missing, the
driver falls back to running the engine for that variant and says so.

**Expected.** 01, 02, 03, 04 verified with offsets; 05 recorded as
`no_candidates`; 06 recorded unverified (control). Any other outcome means
the composed-timeline reasoning is wrong somewhere, and that is exactly the
data this corpus exists to produce.
