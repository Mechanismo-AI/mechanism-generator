# Changelog

## Unreleased — 0.1.0a1 foundation

- Add the OMTS 0.1.0 draft specification, packaged schema, and two annotated examples.
- Add shared document validation: schema, references, dimensions, ordering, bounds,
  angle units, duplicate keys, and finite values.
- Replace the experimental PowerShell-only adapter with strict capability checks,
  independent per-task configurations, portable run plans, and a Python runner.
- Reject unsupported modes, bounds, weights, units, and outputs instead of losing
  requirements. Propagate equal per-target tolerances, seeds, noise, branch/profile,
  and continuation settings.
- Disable reserved unqualified fixed representatives in generated research runs.
- Add Apache-2.0, contributor documentation, qualification notes, and test CI.

This imports and revises the August 2026 research OMTS draft. Previous bundle
checksums and build-time validation claims are not reused for the changed files.
The optimizer and model weights are outside this foundation release.
