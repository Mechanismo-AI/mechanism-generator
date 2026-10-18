# Regression fixtures

These eight synthetic tasks and frozen expected results are Apache-2.0, covered by the repository LICENSE. They were extracted from an already completed paired screen. They cover early success, all four chooser gains, both remaining failures and an additional orientation fallback. They contain no generating geometry in the solver inputs. Expected results contain solver diagnostics and geometry.

They are regression tests, not a new independent evaluation set. Exact numerical parity was verified on the runtime recorded in runtime-versions.json (Python 3.12.14) with MOTION_TEST_EXACT=1 at recording time; exact mode now compares against the runtime-fingerprinted anchor registry in evidence/runtime-anchors/ instead of these embedded trajectories. Portable mode checks identical outcomes, choices and budgets, recomputes strict metrics, and compares initial candidate values within relative 1e-8 / absolute 1e-10. Final optimizer trajectories may differ across CPUs. Neither test mode changes production qualification tolerances.

PR-A (schema_version 2) converted the stored angular velocity and acceleration
error values from radians to degrees with the same operation the solver now
applies (np.degrees, one double multiplication by 180/pi). Every other stored
number, including all scores and ranking predictions, is unchanged from the
recorded screen extraction. The conversion preserves every scaled demand to
within one unit in the last place; no stored score changes. A 2026-10-18
exact-mode attempt on a Python 3.14 machine answered the re-anchor question
instead: the raw trajectories themselves diverge across runtimes (last-ulp
differences compounding through refinement, about 1e-14 at a 50-evaluation
early stop to about 3e-3 at the full budget), not just the chooser ranking
fields -- exact parity is per-runtime by design, and the runtime-fingerprinted
anchor registry (evidence/runtime-anchors/) carries it forward.

PR-B (schema_version 3) adds the per_sample result block without touching these stored files: the portable tests recompute each run's per-sample columns live and require each column's maximum to equal the stored aggregate error exactly.

PR-C (the exact-mode runtime anchor registry) points MOTION_TEST_EXACT=1 at evidence/runtime-anchors/<fingerprint>.json instead of these stored files: exact mode fails closed on a runtime with no recorded anchor set and prints the regeneration command (tests/exact_anchors.py --regen, clean tree). These embedded runs and pool are unchanged and remain the portable-tolerance data plus the provenance of the original recording runtime.
