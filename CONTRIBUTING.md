# Contributing

This is an early research project. Issues describing reproducible task examples,
validation problems, and proposed capability definitions are welcome.

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
using project-relative paths. Large artifact distribution will be documented with
the first engine release.

Contributions to the repository are provided under its Apache-2.0 license. Only
submit material you have the right to contribute; preserve third-party attribution.
