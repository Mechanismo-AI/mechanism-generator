# Experimental six-bar motion solver

The separately installable [motion package](../experimental/motion/README.md) adds
pose and first/second crank-angle derivative targets for one planar six-bar family.
Use a separate Python 3.12 environment and install from `experimental/motion` as
shown in its README. Installation of the main repository package alone does not
install this capability. It does not extend the existing three-pose OMTS adapter.

Try the supplied normalized JSON example with `mechanism-motion`. The contract
requires twelve equally spaced increasing crank phases, two known branch signs,
centered positions with unit bounding-box diagonal, and finite numeric arrays.
The result contains inspectable geometry, strict qualification, diagnostics and
an explicit experimental status. A completed run may report `qualified: false`.
Capacity, speed and collision clearance remain unrated or unchecked.

For a physical drive law, output velocity is `v × ω` and acceleration is
`a × ω² + v × α`, where ω and α are crank angular velocity and acceleration.
Spatial units also require a chosen length scale. The solver does not choose or
validate that drive law, load capacity or motor.

The [model card](../experimental/motion/MODEL-CARD.md) distinguishes the proposal
network's 0/128 unrefined strict passes from the refined pipeline's 78/80 synthetic
screen result. The comparator was a private six-bar research pipeline, not the
public four-bar engine. Full original retraining is not included in this package.
The supplied eight tasks are regression fixtures, not a new independent benchmark.

Run the package's portable unittest suite before modifying its frozen assets or
inference rules. The package performs no network access, uploads or training.

## Release candidate

Code, inference weights and synthetic fixtures use Apache-2.0. This addition is
prepared for an experimental release; it does not change the main package's
0.1.0a10 version, commands or existing model downloads. See the
[draft release notes](../experimental/motion/RELEASE-NOTES.md).
