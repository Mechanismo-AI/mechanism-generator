# Exact-mode runtime anchor registry

This directory holds the bit-exact anchor sets for MOTION_TEST_EXACT=1, one
JSON file per runtime, named by fingerprint:

    <python>-<torch>-<build-digest>-<numpy>-<cpu-model>.json

The slug is built from the python version, torch version, torch build
digest, numpy version and CPU model (see tests/exact_anchors.py,
fingerprint_slug). Each file records the full fingerprint fields, the
generation timestamp, the git commit it was generated at, and per frozen
case (both chooser and baseline policies) every run's raw parameters and
metrics plus the chooser pool's initial_raw / before /
ranking_prediction.

Why a registry: the last-ulp path through Python, torch and numpy changes
with the interpreter version, the torch build and the CPU, so bit-frozen
anchor values are only meaningful relative to the runtime that produced
them. A 2026-10-18 attempt on a Python 3.14 machine (the original
recording runtime was Python 3.12.14, runtime-versions.json) found the raw
trajectories themselves diverge across runtimes -- from about 1e-14 at a
50-evaluation early stop to about 3e-3 at the full 200-evaluation budget
-- while every outcome-level check passed. Exact parity is therefore
per-runtime by design. runtime-versions.json stays as the provenance
record of the original recording runtime, and the regression fixtures'
embedded runs and pool remain the portable-check data and the provenance
of that runtime; no Python 3.12.14 anchor set is recorded here (the
pre-PR-A radian metric values are not bit-recoverable from the
degree-converted fixtures).

Workflow:

- Record a runtime: from experimental/motion, on a clean tree, run
  `python tests/exact_anchors.py --regen`. The set is committed and lands
  through a reviewed pull request; --regen refuses to overwrite an
  existing set without --replace (anchors are recorded data).
- Run exact mode: `MOTION_TEST_EXACT=1 python -m unittest discover -s
  tests -v` (from experimental/motion). A runtime without a recorded set
  fails closed with the regen command printed; a corrupt anchor file fails
  closed with a distinct message (a finding, not a re-record trigger).
- Drift measurement (the standing instrument for any change touching
  numerics): regenerate at the base commit and at the change, same
  machine, and diff the two JSONs -- `python tests/exact_anchors.py
  --output /tmp/anchors-<label>.json` at each commit. --output writes a
  comparison artifact outside the registry and never touches a recorded
  set. Per-PR BOUNDARY diffs, not span diffs: regenerate at a merge
  commit and at its parent, so nothing landing in between confounds the
  reading. At commits older than this script, write it into the tree as
  an untracked file (`git show <branch>:experimental/motion/tests/
  exact_anchors.py > experimental/motion/tests/exact_anchors.py`) so the
  clean-tree guard still holds. If a same-fingerprint pair still moves,
  report it as a finding; never re-anchor silently.

The tolerant outcome checks in tests/test_release.py remain the portable
gate; exact mode is opt-in and never gates the normal suite.
