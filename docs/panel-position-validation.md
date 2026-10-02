# Panel-position initialization: full-pipeline validation

This report evaluates the opt-in `--panel_position_geometry` branch against
released v0.1.0a8. It follows a separate private prototype study; none of the
prototype's development or evaluation tasks are reused here.

## Frozen protocol

Seed 2026100189 generated 16 distinct feasible mechanisms: twelve unordered panel
tasks (six tight panels, six roomier panels; two carrier sizes) and four unsupported
controls (position, ordered position, pose, ordered pose). The reference mechanism
files are separate and are never loaded by either solver arm. Position-only tasks
do not contain reference orientations. Both arms use the three published weights,
paired profiles, both assembly branches and standard optimization budgets.

The candidate adds 65,536 deterministic analytic samples and at most six preserved
parents, with no parent refinement. This is extra compute, not an equal-compute
comparison. Fixed, variable, trust and release stages and their shared path
reference are unchanged. Arms alternate execution order; two CPU workers use one
thread each. The gate was frozen before solver outcomes: at least four additional
selected successes, no losses, unchanged unsupported-task numerical records,
aggregate runtime ratio at most 1.30, and completed runs with tests passing.

## Results

- Panel successes: **0/12 baseline versus 11/12 candidate**.
- All selected successes: **4/16 versus 15/16**.
- Gains: 11; losses: 0.
- All four unsupported controls retain identical numerical candidate records.
- Summed run time: 586.02 seconds baseline, 593.12 seconds candidate; ratio 1.012.
- All 32 automatic local contribution bundles validate, including the new origin,
  setting and source fingerprint in schema 0.7. Historical schema 0.6 also validates.
- All 16 independent reference witnesses pass the task's qualification checks.
- Frozen gate: **passed**.

Success requires a **selected exported candidate**, not just an analytic proposal.
An independent NumPy evaluator checks actual-phase position errors, analytic
full-cycle assembly and transmission limits, requested order/orientation, and
7,201-sample panel/carrier containment. The ordinary engine qualification also
enforces its shared path budgets, robustness and configured compactness limits.

The numerical engine stayed frozen during the comparison. Release metadata and
documentation were updated afterward; packaged execution is checked separately.
The corpus and protocol are in `examples/benchmarks/panel-position-v1/`.

## Limits

This small constructed sample does not establish a general success rate. The
earlier prototype missed three known-feasible tight-panel tasks; this validation
does not claim to solve those. Sampled containment with zero-thickness links is
not continuous-clearance, collision, structural, or manufacturing certification.
Model weights are unchanged. Sharing remains local, reviewed and voluntary.
