# Regression fixtures

These eight synthetic tasks and frozen expected results are Apache-2.0, covered by the repository LICENSE. They were extracted from an already completed paired screen. They cover early success, all four chooser gains, both remaining failures and an additional orientation fallback. They contain no generating geometry in the solver inputs. Expected results contain solver diagnostics and geometry.

They are regression tests, not a new independent evaluation set. Exact numerical parity was verified on the runtime recorded in runtime-versions.json with MOTION_TEST_EXACT=1. Portable mode checks identical outcomes, choices and budgets, recomputes strict metrics, and compares initial candidate values within relative 1e-8 / absolute 1e-10. Final optimizer trajectories may differ across CPUs. Neither test mode changes production qualification tolerances.

PR-A (schema_version 2) converted the stored angular velocity and acceleration
error values from radians to degrees with the same operation the solver now
applies (np.degrees, one double multiplication by 180/pi). Every other stored
number, including all scores and ranking predictions, is unchanged from the
recorded screen extraction. The conversion preserves every scaled demand to
within one unit in the last place; no stored score changes. Re-anchoring
MOTION_TEST_EXACT=1 bit parity on the recorded runtime after this convention
change is a pending machine step; chooser ranking fields may recompute at the
last-ulp level because their features consume the degree-convention ratios.
