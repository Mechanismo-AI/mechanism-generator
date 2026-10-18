# Experimental motion release candidate: 0.1.0.dev0

Add a separate CPU six-bar solver for twelve fixed-phase pose and crank-angle
derivative targets, with known assembly branches. Install this package separately
and use `mechanism-motion`; existing four-bar commands and OMTS behavior remain
unchanged.

Includes cleaned proposal tensors, frozen continuation and candidate selectors,
Apache-2.0 licensing, model provenance, an example and portable regression tests.
Input/output aliases are rejected and results are written atomically.

The frozen refined pipeline achieved 78/80 strict successes versus 74/80 for the
private experimental baseline on a same-family synthetic screen, with four gains
and no losses. Both used at most 200 refinement evaluations. Regression tests
reproduce eight stored cases under both policies; they are not new benchmark data.
The proposal network alone achieved zero strict passes in its 128-case validation.

This is experimental research software. Capacity, operating speed and collision
clearance are unrated or unchecked; there is no hardware validation. Exact
retraining requires original generators, training data and runner outside this
distribution. See MODEL-CARD.md for the complete scope.

Publication proposal: use a separate experimental prerelease and attach this
package's wheel and source archive. Keep the existing main-package release and
weight downloads unchanged. These notes are a draft, not a publication record.

Result units declarations, schema_version 2: emitted angular velocity and
acceleration errors now read in degrees per crank-angle derivative, matching
the 2/5 degree gates; computation stays radian-internal. Every result carries a
units block declaring the emitted unit of each error field, and the strict
limits are written in degrees in one place (the continuation module's LIMITS,
imported by qualification and the chooser). Scaled demands, scores, outcomes
and candidate choices are unchanged; the regression fixtures' stored angular
error values were converted with the same operation the solver applies, and
exact-parity re-anchoring on the recorded runtime is a pending machine step.
This is a convention declaration, not a solver change.

Per-sample error emission, schema_version 3: every result carries a per_sample block for the selected candidate, mapping each units-block key (position, orientation, spatial_velocity, spatial_acceleration, angular_velocity, angular_acceleration) to twelve per-sample errors in target sample order, with null entries where a value is non-finite. The per-sample values come from the same computation as the aggregate errors, so each aggregate is exactly the maximum of its per-sample column. This is an additive emission change: no score, gate, outcome, candidate choice or stored fixture value changes.
