# Roadmap

The main product is a usable mechanism-design tool. Benchmarks, reproducible
training, and contribution tools make its development open to others while
released models let designers work without running training themselves.

1. **Published: repository foundation and OMTS draft.** Installable task validation,
   strict run preparation, examples, tests, and Apache-2.0 licensing.
2. **Published: four-bar engine and model weights.** Packaged R2.5c/R2.5b solver,
   cleaned inference exports, model card, checksums, and baseline execution checks.
3. **Published: voluntary contribution flow.** Local bundles, an offline review
   page, and manual submission let users share inspectable results for possible
   future solver and training improvements.
4. **Implemented and evaluated: three-pose design.** Specify
   three positions and directed orientations, refine them at common target phases,
   and reject candidates that fail the angular requirements. The implementation
   includes an OMTS example, analytical regression tests, and a reproducible
   position-versus-pose experiment. The executed OMTS example selected four designs
   that independently meet both position and orientation tolerances. A separate
   four-case comparison produced qualifying pose designs in two cases; the
   position-only search produced none meeting the same combined requirements.
   A subsequent geometric initializer addresses those search failures while
   retaining the same qualification gates; see the [broader evaluation](pose-corpus.md).
5. **Implemented: training reproduction and broader pose evaluation.** The full
   four-stage historical training chain, clean dependencies, synthetic data
   generator, recorded recipes and a repeatability check are packaged. A frozen
   corpus separates eight development tasks from eight reserved evaluation tasks.
   See the [training guide](training.md) for the distinction between a repeatable
   small run and reproducing historical model weights.
6. **Evaluated: additional proposal-model experiments.** Full local training and
   a frozen paired evaluation did not establish the required success-coverage gain
   for promoting the experimental weights. The published proposal models remain
   unchanged. Continue to establish full-run training baselines across seeds. Build datasets retaining several verified designs per
   task, with task-level separation between training and testing, then compare
   orientation-conditioned proposals against the geometric baseline. Preserve
   failed runs and additional compute in the comparison.
7. **Released: explicit crank direction.** Positive remains the default; negative
   and either-direction requests preserve target order and report actual direction
   in candidate and contribution exports. Assembly branch is independent.
8. **Evaluated: a dimensioned practical design brief.** The
   [tabletop-transfer case study](../examples/tabletop-transfer/README.md) produced
   no qualifying design from 36 candidates in two crank directions. Independent
   checks expose position, orientation and panel-envelope failures. A subsequent
   [controlled diagnosis](../examples/tabletop-transfer/Diagnosis.md) found one
   candidate within the original hard limits by sampling the allowed angle
   tolerances. Release v0.1.0a7 integrates
   [tolerance-aware initialization and sampled panel screening](tolerance-and-panel.md)
   with bounded budgets, preserved nominal seeds and final qualification gates.
   Next assess precision, diversity,
   runtime and dimensional sensitivity before generalizing gains.
9. **Broader design capabilities.** Use measured failure cases to prioritize richer
   trajectories and orientation requirements, prescribed timing and dwell,
   additional mechanism types, dynamics, collisions, and synchronized tasks.

The current pose feature combines existing position-input proposal weights,
geometric pose initialization and local refinement. Orientation-conditioned training remains future
work. Loads, manufacturability, and physical validation are outside the present
kinematic alpha. See the [three-pose guide](three-pose.md),
[engine guide](engine.md), and [model card](../MODEL_CARD.md) for the supported scope.
