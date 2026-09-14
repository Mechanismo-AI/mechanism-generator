# OMTS 0.1.0 draft

Read the [specification](specification.md). The single normative schema lives in
[`src/mechanism_generator/omts/schema.json`](../../../src/mechanism_generator/omts/schema.json)
and is included in installed distributions. Its `$id` is an identifier, not a
network dependency; validation uses the packaged schema and internal references.

The accepted version alias `0.1` means draft `0.1.0`. Changes before the first
tagged release are tracked in the [changelog](../../../CHANGELOG.md).

Validate the [examples](../../../examples/omts/) with `omts validate`. General
document validation is separate from the [R2.5c adapter](../../../docs/r25c-adapter.md).
The synchronized-line example is deliberately outside that adapter's capabilities.
