# Optional geometric starts for position tasks

Version 0.1.0a8 adds `--position_geometry` to the public engine
command. It is off by default. Model weights are unchanged.

The hybrid engine already permits adjustable base spacing. Its legacy fixed-ground
stage supplies complementary candidates; final designs are not restricted to 6.

For unordered position tasks without panel constraints, the option replaces up to
four non-balanced-model starts in the independent variable-ground stage with
geometric starts. It preserves the number of starts, each slot's profile and
assembly branch, all balanced-model starts, and the other portfolio stages.
Different candidate outcomes can affect dynamic continuation selection and runtime.
In cross-profile mode it prefers balanced-profile slots. In paired mode it retains
the replaced path/transmission profile. No extra unlimited search branch is added.

Pose, ordered-motion and panel tasks retain their existing initialization. The
option is not currently an OMTS task setting. All candidates still face ordinary
qualification; a geometrically rotating seed is not automatically a useful design.

Run manifests record allocation counts, replaced slots, timing and source hashes.
Local contribution schema 0.6 preserves the initializer type, counts, setting and
fingerprint, with older 0.1–0.5 bundles remaining readable. Review and submission
remain local and voluntary; enabling this option uploads nothing.

Use the frozen full-pipeline validation report to assess readiness. Research-core
improvements alone do not establish production-pipeline improvement.

The frozen full-pipeline comparison selected qualifying designs for 22/24 tasks with the option, versus 18/24 without it. All four gains were compact position tasks. The eight pose/order/panel regression tasks retained identical candidate numbers and parameters. Both versions failed the two new panel cases; this option does not address them. See [the validation report](geometric-position-validation.md) and [summary](geometric-position-validation.json). This small constructed sample does not establish a general success rate.
