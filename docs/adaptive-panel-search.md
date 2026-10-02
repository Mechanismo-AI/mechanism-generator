# Optional adaptive panel search

`--panel_position_adaptive` enables the standard `--panel_position_geometry`
branch and adds two bounded fallbacks. It is off by default. It supports unordered
position-only panel tasks with adjustable base spacing. Pose, ordered-motion,
fixed-ground and missing-panel tasks bypass adaptive work. This is a CLI option,
not an OMTS document setting.

The stages run in order:

1. Run the existing hybrid portfolio and standard 65,536-sample panel geometry.
   If any candidate qualifies, stop without additional sampling or optimization.
2. Try the same analytic construction with 262,144 samples and at most six new
   candidates. Stop if a candidate qualifies.
3. Rank near-misses from a 65,536-sample construction by panel/pivot shortfall.
   Retain up to six diverse parents. If a parent qualifies, stop. Otherwise refine
   them in order, stopping at the first qualifying result or after six attempts.

Each refinement has a hard limit of 400 Adam steps and 150 LBFGS objective
evaluations. Its objective includes target errors, panel and pivot clearances,
robustness and transmission floors. Panel optimization uses 361 phases; ordinary
final qualification uses the requested panel screen (7,201 phases by default).
Analytic whole-cycle transmission extrema also guide refinement. Several saved
snapshots are checked, and the best qualifying snapshot is retained when available.

All existing candidates and near-miss parents remain in the complete report;
refined children have distinct identifiers and parent references. Numerical
optimizer failure retains previously saved finite snapshots and cannot overwrite
an earlier solution. Every added candidate still faces the same shared path
reference, qualification, ranking, deduplication and export rules. No acceptance
threshold is relaxed.

`panel_adaptive_initialization.json` and the target manifest record the stopping
stage, sample/candidate counts, actual optimization work, failures, runtime and a
combined source fingerprint. The fingerprint covers the controller, standard and
near-miss samplers, and refinement module. Engine-wide source pins are also kept.
Contribution schema 0.8 preserves these diagnostics, the option and candidate
lineage; schemas 0.1–0.7 remain readable. Sharing remains local and voluntary.

Extra work is conditional, not free. A difficult task can use the entire budget
without finding a solution. The default path remains the existing engine unless
this option is supplied. Base spacing remains adjustable; model weights are unchanged.

This remains a kinematic research tool. Sampled zero-thickness containment does
not establish continuous clearance, collision freedom or physical durability.
See the accompanying validation report for measured selected-output results and
the limits of the constructed test corpus.
