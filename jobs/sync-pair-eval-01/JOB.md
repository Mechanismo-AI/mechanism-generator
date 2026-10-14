# Job sync-pair-eval-01: first engine runs of the synchronized pair

**Purpose.** Produce real achieved per-task results for
`examples/omts/synchronized_pair.omts.yaml` so the S4 timeline verifier can be
designed and tested against actual run artifacts instead of assumed formats.
This is the first end-to-end execution of a document containing a v0.2
synchronization line.

**Machine.** Any idle Ubuntu PC (CPU-only, no GPU). Python 3.12 recommended.
Expect roughly the cost of two ordinary three-target searches (one per task);
use `--quick` for a first smoke pass, then full budgets.

## One-time setup (per machine)

```sh
git clone -b omts-v02-sync-spec https://github.com/Mechanismo-AI/mechanism-generator.git
cd mechanism-generator
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install ".[engine]"
mechanism-models download --directory models
mechanism-models verify --directory models
```

## Steps

1. **Validate and adapt the pair document** (records the line section):

   ```sh
   omts validate examples/omts/synchronized_pair.omts.yaml
   omts adapt examples/omts/synchronized_pair.omts.yaml --output-dir runs/sync-pair-01
   ```

2. **Preflight check** (verifies installed engine and model hashes, runs nothing):

   ```sh
   python runs/sync-pair-01/run_r25c.py --models-directory models --check-only
   ```

3. **Run both tasks** (in tmux or with nohup; this is the long part):

   ```sh
   python runs/sync-pair-01/run_r25c.py --models-directory models
   ```

   Note: `run_r25c.py` accepts no budget flags. For budget-controlled or
   corpus runs, use the driver in `jobs/sync-corpus-01/corpus_run.py`,
   which calls the engine directly per run.

4. **Collect for S4** — from each run directory (`results/task-001` for gate,
   `results/task-002` for catcher), keep at minimum:
   - the selected-candidate CSV/JSON (achieved target phases per candidate);
   - the manifest/config;
   - `direction_index.json` if present;
   - the whole run directory if convenient.

   The S4 verifier needs, per candidate: which phases each target was achieved
   at, and the candidate's qualification status, so relations like
   `release_before_grab` (ordering, 10-45 deg lead) and the
   `handoff_window` event (phase 100-140, tolerance 5 deg) can be checked
   against real numbers.

## Reporting back

- Note wall-clock runtime per task, Python/OS versions, and CPU model.
- Copy `run_plan.json` plus the collected artifacts to the "Mechanism
  Generator" work chat, or commit them under `runs/sync-pair-01/` (gitignored
  by default) and share a summary.
- A completed search legitimately selects zero candidates; report that too —
  it is data, not failure.

## What we will do with it

S4 reads the plan's `line` section plus these achieved results and emits a
`line_result` (verified relations/events with achieved lead values and
status) and a machine-readable composed timeline. This job's outputs become
the S4 fixtures.
