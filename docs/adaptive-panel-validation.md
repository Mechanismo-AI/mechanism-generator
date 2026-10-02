# Adaptive panel search: full-pipeline validation

This compares released a9 with `--panel_position_geometry` against the candidate
with `--panel_position_adaptive`. The adaptive option is off by default and implies
standard panel geometry. Existing qualification stops the fallback; otherwise it
tries 262,144 analytic samples, then at most six near-miss refinements with hard
400-step Adam and 150-evaluation LBFGS limits per start. Existing candidates and
parents remain in the report. Model weights are unchanged.

## Frozen comparison

Seed 2026100283 produced 24 fresh distinct constructed shapes: 20 tight-panel
tasks and four unsupported controls (position, ordered position, pose, ordered
pose). Witnesses were kept separate from solver inputs; position-only tasks do
not include witness orientations. Both arms run the full hybrid pipeline, paired
profiles, both branches and standard optimization limits, using the same published
weights. Two local CPU workers each use one thread; arm execution order alternates.
The candidate adds bounded compute only when existing candidates do not qualify.

The gate was frozen before outcomes: at least two additional selected successes,
zero losses, identical unsupported numerical records, completed runs and tests,
and aggregate runtime ratio no greater than 1.50.

## Results

- Panels: **20/20 candidate versus 16/20 baseline**.
- All tasks: **24/24 versus 20/24**.
- Gains: 4; losses: 0.
- All baseline candidate numerical records were retained; all four unsupported
  controls retained identical complete numerical candidate lists.
- Summed runtime: 1274.12 seconds baseline and
  1279.17 seconds candidate; ratio **1.004**.
- All 48 automatic local contribution bundles validated (baseline schema 0.7,
  candidate schema 0.8), including refined-parent references where present.
- All 24 separate witnesses pass qualification. The frozen gate passed.

Stopping stages: {"existing_qualified": 16, "larger_qualified": 4, "unsupported_task": 4}.

Success requires a selected exported candidate. A separate NumPy implementation
checks target-phase position errors, analytic full-cycle assembly and transmission,
requested order/orientation, and the sampled panel/carrier envelope. Ordinary
engine qualification additionally enforces its shared path reference, robustness,
compactness and requested pivot clearances. Candidate sample/optimization counters
were audited against the hard bounds; no thresholds were relaxed.

## Limits

This is a small constructed sample, not a general success-rate estimate. The
earlier prototype's 24/24 result is a separate experiment and is not substituted
for this full-pipeline result. Sampled zero-thickness containment does not certify
continuous clearance, collisions, structural strength or manufacturing tolerance.
Numerical source stayed frozen during this comparison; package metadata is updated
afterward, with package execution verified separately before publication.

The corpus and protocol are in `examples/benchmarks/adaptive-panel-v1/`.
