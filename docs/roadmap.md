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
   The other two constructed cases remain unresolved at those budgets. This
   narrow development evidence does not establish a general success rate.
5. **Next: reproducible training and broader research.** Review and publish
   training source, teacher dependencies, configurations, dataset provenance and
   licenses. Expand evaluation across tasks, search budgets, and seeds. Build
   datasets retaining several verified designs per task, with task-level separation
   between training and testing, then evaluate improved proposal models.
6. **Broader design capabilities.** Use measured failure cases to prioritize richer
   trajectories and orientation requirements, prescribed timing and dwell,
   additional mechanism types, dynamics, collisions, and synchronized tasks.

The current pose feature uses the existing position-input proposal weights with
additional local refinement. Orientation-conditioned model training remains future
work. Loads, manufacturability, and physical validation are outside the present
kinematic alpha. See the [three-pose guide](three-pose.md),
[engine guide](engine.md), and [model card](../MODEL_CARD.md) for the supported scope.
