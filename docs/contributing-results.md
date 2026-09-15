# Contribute results

Sharing useful runs helps improve the solver, qualification rules, and future
training. It is voluntary. You can use Mechanism Generator without reporting
results or publishing your work.

The engine prepares a contribution bundle on your computer by default. Preparing
and reviewing it do not transmit anything. You choose what to share, download a
reviewed file, and then submit it yourself through GitHub.

## Review a run

Each run contains a `contribution` folder with:

- `bundle.json`: the local contribution data.
- `review.html`: an offline page for choosing and reviewing the outgoing data.

The bundle is refreshed after each completed target and when the run finishes.
An interrupted run can therefore retain a bundle of its completed targets. A
failure before any target completes may leave no bundle. Add
`--no_contribution_bundle` to the engine command to disable automatic preparation.

You can also prepare a bundle from an existing R2.5c run directory:

```sh
mechanism-contribute prepare path/to/run
```

Use the directory containing `run_manifest.json`, rather than its parent output
directory. Older runs, including v0.1.0a2 runs, have an unknown completion status
when their manifest does not record it; preparing a bundle does not infer success.

Open `contribution/review.html` in your browser and follow these steps:

1. Choose the sections to include and inspect the exact outgoing JSON preview.
   You can add a pseudonym and a short description of your application.
2. Confirm that you have the right to share the selected material under
   Apache-2.0 and permit public reuse, including model training. Download
   `reviewed-contribution.json`.
3. Open the GitHub submission form from the review page. Attach the downloaded
   file, check the submission details and confirmations, and select **Create
   issue**. The form includes a SHA-256 digest identifying the exact downloaded
   file.

The local page has no external resources, uploads, or telemetry. Opening the
GitHub form contacts GitHub and sends the digest, but does not attach the bundle
or post an issue. **Attaching the file uploads it immediately, and that attachment
is public even before you create the issue.** Finish reviewing before attaching
anything. See [GitHub's attachment documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files).

Your GitHub account is associated with the issue. An optional pseudonym inside
the bundle does not hide that account. Do not attach the original run directory,
local `bundle.json`, or `review.html`: the reviewed download contains your chosen
subset, while the local files can contain sections you chose to omit.

## What the bundle contains

| Section | Contents | Can omit from the reviewed download? |
| --- | --- | --- |
| Outcome | Run completion status, whether each task requires orientation, and counts of candidates and qualification results | No |
| Task | Target positions and, for pose tasks, requested angles, angular tolerances, tool frame and geometric initialization diagnostics | Yes |
| Candidates | Candidate geometry and measured results, including requested and matched pose angles, tolerances, errors and rejected candidates | Yes |
| Settings | Selected solver settings and random seed | Yes |
| Provenance | Available engine and model identifiers and hashes | Yes |

The exporter selects recognized fields from run outputs. It does not collect raw
logs, machine paths, credentials, model files, training datasets, or arbitrary
files from the run directory. Geometry can still describe a confidential design;
inspect the preview even when it contains no names or file paths.

For pose runs, both Task and Candidate sections contain requested angle data.
Omit both sections to exclude those values. Search settings never contain target
angles or angular tolerances. The required outcome still identifies orientation
tasks and retains orientation-acceptable and pose-acceptable counts. This prevents
a failed pose search from appearing to be a successful position-only search when
the detailed geometry is withheld. Pose acceptance means that the candidate meets
both position and orientation requirements; the usual selection and engineering
gates still apply.

Geometric pose candidates retain their distinct `pose_geometry` source, exact-seed
or refined-child origin, sample index, and remapped parent reference. The optional
Task section reports the initializer's sample and candidate counts and recorded
work; Settings includes its configured budgets, and Provenance includes its source
fingerprint. These fields distinguish target-derived geometry from neural proposals
without exposing local paths or arbitrary checkpoint metadata.

Candidate failures and runs with no eligible designs are useful contributions.
They help expose limits that successful examples alone would miss. A reported
qualification is the solver's measurement, not independent validation or evidence
that a mechanism was built successfully.

The optional application description can explain intended use or link to code,
refined weights, or physical test evidence. It accepts up to 4,000 characters; the
pseudonym accepts up to 100. Linked materials need their own provenance and
license review. Linking a dataset or model does not establish permission to reuse
it, and this flow does not upload those materials.

## Check a bundle

The command below validates either a local bundle or a reviewed submission:

```sh
mechanism-contribute validate path/to/reviewed-contribution.json
```

Validation runs locally and does not submit the file. New bundles use the version 0.3
[contribution schema](../src/mechanism_generator/contributions/schema.json)
with explicit pose requirements, qualification counts, and geometric initialization
provenance. Existing versions remain supported using the unchanged
[0.1 schema](../src/mechanism_generator/contributions/schema-v0.1.json) and
[0.2 schema](../src/mechanism_generator/contributions/schema-v0.2.json).
Reviewing a bundle preserves its schema version. Validation checks count and
qualification consistency, including the pose gate when candidate details are
included. Valid structure does not establish correct results, ownership,
or suitability for training.

## How submissions become useful

Every submission starts with `validation_status: unreviewed`. Maintainers check
the file's digest and schema, inspect its provenance and sharing permissions,
reproduce results where practical, and assess data quality. Missing sections can
limit reproduction or training usefulness. Physical test evidence is reviewed
separately from simulated results.

Only a later, documented curation decision can include a contribution in a dataset
or training run. Submitting an issue does not automatically change the solver,
models, or any training dataset. Future curated releases should record accepted
sources, licenses, validation decisions, and changes so their results remain
traceable.

This release provides local preparation and manual submission. It has no automatic
sharing option. The existing Apache-2.0 license and the v0.1.0a2 model weights are
unchanged.
