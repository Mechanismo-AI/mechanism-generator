# Optional geometric starts: full-pipeline validation

Released baseline: **18/24** selected qualified results. Opt-in candidate: **22/24**. Gains: 4; losses: 0. Predeclared release gate passed: **True**.

| Task type | Baseline | Candidate |
|---|---:|---:|
| position | 12/16 | 16/16 |
| ordered | 2/2 | 2/2 |
| pose | 2/2 | 2/2 |
| ordered_pose | 2/2 | 2/2 |
| panel | 0/2 | 0/2 |

All eight unsupported-task regression probes had identical full candidate numerical records: **True**. This covers two each of ordered positions, poses, ordered poses, and panel-constrained positions.

## Controlled comparison

The frozen plan generated 24 distinct constructed feasible tasks with seed 2026100149: eight compact position tasks, eight ordinary position tasks and eight constraint regressions. No task was selected by solver performance. Feasibility witnesses were stored separately and never loaded by the solver. These tasks are fresh relative to the previous research-core experiment. Once inspected they become development evidence; they are not a population success estimate.

Both arms ran the full released hybrid sequence: fixed-ground proposals, independent variable-ground proposals, trust continuation, release continuation, and existing pose geometry when requested. Base spacing is adjustable in final design search. Fixed-ground stages remain complementary legacy initial searches; they are not a final task constraint. Both arms used three models, both assembly branches and paired profiles. The candidate opted into at most four replacements of non-balanced-model variable starts while retaining each slot's profile and branch. Balanced-model starts and all other stages remain available. Unsupported tasks bypass the allocation.

Both arms had identical configured refinement/continuation limits. Actual continuation selections and early stopping can differ because candidate outcomes differ. Within each primary fixed/variable stage the start count is unchanged. Full-pipeline path references are derived normally in each arm, unlike the shared fixed reference used by the earlier isolated-core experiment. The gate required at least two additional selected position successes, no lost successes, exact unsupported-path numerical parity, all runs complete, tests passing, and aggregate runtime ratio at most 1.30.

Measured aggregate runtime was 799.9s baseline and 804.5s candidate (ratio 1.006). Two local workers ran independent task pairs, with arm order alternated. These are workload observations with shared-machine noise, not a precise performance guarantee.

Success required at least one selected engine-eligible candidate plus independent NumPy verification of analytic whole-cycle geometry, Grashof/crank class, actual-phase position tolerances, hard transmission minima, and applicable orientation, cyclic order or sampled panel/carrier containment. Position limits remained 0.05 mean / 0.075 maximum; hard transmission remained 15 degrees at targets / 10 globally. Panel verification sampled 7201 phases and checked carrier corners and pivot clearance. These are kinematic results, not load, thickness, collision or hardware validation.

## Software and reproducibility

The numerical build was frozen for all 48 runs. Source hashes, pinned unchanged model hashes, task hashes, seeds, logs, manifests and per-candidate independent scores are retained. An OMTS fingerprint mismatch caught by the first test run was corrected in metadata only; numerical sources, tasks and budgets were unchanged.

The integrated numerical build passed 317 Python tests (five Windows symlink skips). A separate release-preparation copy adds contribution schema 0.6, old-schema compatibility, initializer provenance and offline review support; it passed 323 tests with the same five skips. Actual baseline and geometric run bundles validate, and the offline browser-review tests pass, including explicit consent/download behavior. Earlier preparation attempts caught stale version assertions and a Windows text-encoding issue; both were corrected in a clean UTF-8 preparation copy. No numerical benchmark build was altered by those packaging fixes.

The initializer is opt-in, off by default. No weights were retrained or replaced. The existing code/model licenses remain Apache-2.0. Release gate success means the candidate merits this bounded optional update; it does not establish superiority on arbitrary mechanism tasks. Publication status is tracked separately from this report.
