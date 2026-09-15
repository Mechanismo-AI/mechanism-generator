# Contributing

This is an early research project. Issues describing reproducible task examples,
validation problems, and proposed capability definitions are welcome.

To share solver results, open the `contribution/review.html` page created in your
run directory. Choose what to include, review the exact outgoing data, download
the reviewed file, and submit it through the GitHub form. See the
[result contribution guide](docs/contributing-results.md) for the complete flow,
sharing permissions, and how submissions are evaluated. Preparing and reviewing
the local bundle do not transmit data. Contributing is voluntary.

Install from the repository using `python -m pip install -e ".[test]"`, then run
`python -m pytest`. Keep schema, semantic validation, examples, and adapter behavior
consistent. Add regression tests for changed requirement handling.

A new adapter feature must map each operational field to an actual engine behavior
or reject it with a useful explanation. Unsupported hard constraints must never be
silently dropped. Document defaults and distinguish requested behavior from
measured qualification.

Use a focused branch and pull request. Include the problem, resulting behavior,
and checks performed. Keep model binaries, private paths, credentials, personal
logs, and generated runs out of source commits. Share small reproducible examples
using project-relative paths. The three public model exports are distributed as
[release assets](https://github.com/Mechanismo-AI/mechanism-generator/releases).
Proposed model or dataset contributions need separate provenance and license
review; include a link and description rather than attaching raw training assets
to a result contribution.

Contributions to the repository are provided under its Apache-2.0 license. Only
submit material you have the right to contribute; preserve third-party attribution.
