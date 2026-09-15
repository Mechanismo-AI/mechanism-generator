# Changelog

## 0.1.0a3 — local contribution review

- Prepare an offline contribution bundle after each completed target and run.
- Include numerical outcomes and optional task geometry, all candidates, settings,
  and model/engine hashes through a fixed field allowlist.
- Add an offline review page with exact export preview, selectable sections,
  explicit sharing permission, and a manual GitHub submission form.
- Add bundle validation and file fingerprints; no telemetry or automatic uploads.

Model weights remain the unchanged Apache-2.0 exports from v0.1.0a2. Regenerate
OMTS run plans after upgrading so their engine fingerprints match this release.

## 0.1.0a2 — four-bar research alpha

- Package the R2.5c/R2.5b engine with an explicit model downloader and verified CLI.
- Publish three Apache-2.0 inference-only safetensors exports with exact tensor and
  prediction parity, public provenance, and a model card.
- Restrict selected fixed references to eligible designs; disable unqualified fallback.
- Remove machine-specific directories from persisted path fields and fail on missing models.
- Update OMTS runners to check the installed public engine and cleaned model identities.
- Add geometry/gradient, ordering, qualification, download, and real optimizer tests.
- Record a current full-budget example and reduced-budget comparison with the originals.

The OMTS 0.1 draft and its narrow supported subset are unchanged. Regenerate old
run plans after upgrading. This is an inference/research release, not a complete
training reproduction release or engineering certification.

## Unreleased â€” 0.1.0a1 foundation

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
