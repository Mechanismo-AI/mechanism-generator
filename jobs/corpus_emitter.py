#!/usr/bin/env python3
"""Shared corpus emitter: recorded case-study outcomes as
machine-readable solution-corpus rows.

Convention (adopted with the flipper brief, case study C): a case
study's recorded outcome is not only prose in a JOB.md -- every
candidate the engine recorded becomes a data row, so downstream
consumers grade recorded outcomes instead of narrative. The first
consumer is the B1 admission-gate work (docs/strategy.md): instruments
grade candidates through OMTS demands and recorded outcomes, so the
outcomes must exist as data. This module is the single writer, so
every corpus carries the same schema, units discipline and provenance
shape. The rows of one job are one batch: the batch declares its unit
convention in the units block of every row, and consumers pin against
corpus_schema_version and refuse to mix versions silently (the PR-A
result-units lesson, applied to the corpus).

A future retroactive emitter over the recorded case A/B runs (the
frame-sweep precedent: a pure transformation of existing recorded
data, no reruns, exact reuse) will use this same module and is its own
declared job; it is not built here.

Row shape (one JSON object per candidate; the CSV is the flat
projection of the same fields for eyeballing):

  corpus_schema_version  pinned version string; consumers pin here
  task_id                the OMTS task_set_id the row was graded under
  family                 mechanism family label, e.g. four_bar
  candidate_id           the engine's candidate identifier
  direction              crank direction tree, positive or negative
  branch_sign            assembly branch, -1 or 1
  parameters             named parameter vector, as the engine
                         recorded it (units stated in the units block)
  solution_status        scored / excluded:<reason>
  gates                  named gate values with pass/fail and margins,
                         plus declared diagnostic data rows
  verdict                the row's scorecard verdict, self-contained
  demand                 the demand points and tolerances the row was
                         graded against
  units                  explicit units block (position basis, angle
                         units, parameter notes)
  provenance             job, task id, seed, run id, source commit

Fail-closed: a row missing any required field, an empty parameter
vector, a wrong schema version, a non-numeric parameter, or a
NaN/inf anywhere aborts the whole emission before any file is
written -- partial corpus files are never produced. Determinism:
sorted keys, fixed column order, no clocks, no randomness -- run
twice and diff is byte-identical.

Pure stdlib, pure ASCII. Usage is by import from a case-study
digest (jobs/<job>/<job>_digest.py); there is no CLI.
"""
from __future__ import annotations

import csv
import json
import math
import sys

CORPUS_SCHEMA_VERSION = "1"

UNITS_TEMPLATE = {
    "position": "normalized",
    "position_basis": "1 normalized unit = 100 mm (the OMTS task-layer convention, cases A/B)",
    "angle": "deg",
    "note": "six-bar research-corpus layers normalize by the bbox diagonal;"
            " never mix bases without re-declaring the units block",
}

REQUIRED_FIELDS = (
    "corpus_schema_version", "task_id", "family", "candidate_id",
    "direction", "branch_sign", "parameters", "solution_status",
    "gates", "verdict", "demand", "units", "provenance",
)

CSV_COLUMNS = (
    "corpus_schema_version", "task_id", "family", "candidate_id",
    "direction", "branch_sign", "solution_status", "verdict",
    "parameters", "gates", "demand", "units", "provenance",
)


def die(problems):
    print("corpus_emitter: FAIL-CLOSED:", file=sys.stderr)
    for problem in problems:
        print("  - %s" % problem, file=sys.stderr)
    raise SystemExit(1)


def _finite_numbers(value, path, problems):
    """Walk a nested structure; every float must be finite."""
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            problems.append("%s: non-finite number" % path)
        return
    if isinstance(value, int):
        return
    if isinstance(value, dict):
        for key in sorted(value):
            _finite_numbers(value[key], "%s.%s" % (path, key), problems)
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _finite_numbers(item, "%s[%d]" % (path, index), problems)


def _require_mapping(value, path, problems):
    if not isinstance(value, dict):
        problems.append("%s: expected a mapping, got %s" % (path, type(value).__name__))
        return
    _finite_numbers(value, path, problems)


def check_rows(rows):
    """Fail-closed validation of every row before anything is written."""
    problems = []
    if not isinstance(rows, list) or not rows:
        die(["no corpus rows to emit (an empty corpus is a digest-level problem, never a silent file)"])
    for index, row in enumerate(rows):
        label = "row %d" % index
        if not isinstance(row, dict):
            problems.append("%s: expected a mapping" % label)
            continue
        for field in REQUIRED_FIELDS:
            if field not in row:
                problems.append("%s: missing field %s" % (label, field))
        if row.get("corpus_schema_version") != CORPUS_SCHEMA_VERSION:
            problems.append("%s: corpus_schema_version must be %r" % (label, CORPUS_SCHEMA_VERSION))
        for field in ("task_id", "family", "candidate_id", "solution_status", "verdict"):
            value = row.get(field)
            if not isinstance(value, str) or not value:
                problems.append("%s: %s must be a non-empty string" % (label, field))
        if row.get("direction") not in ("positive", "negative"):
            problems.append("%s: direction must be positive or negative" % label)
        if row.get("branch_sign") not in (-1, 1):
            problems.append("%s: branch_sign must be -1 or 1" % label)
        parameters = row.get("parameters")
        if not isinstance(parameters, dict) or not parameters:
            problems.append("%s: parameters must be a non-empty mapping" % label)
        elif not all(isinstance(key, str) for key in parameters):
            problems.append("%s: parameters keys must be strings" % label)
        else:
            for key in sorted(parameters):
                value = parameters[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    problems.append("%s: parameters.%s must be a number" % (label, key))
        for field in ("gates", "demand", "units", "provenance"):
            _require_mapping(row.get(field), "%s: %s" % (label, field), problems)
        _finite_numbers(row, label, problems)
    if problems:
        die(problems)
    return len(rows)


def _csv_cell(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def write_corpus(rows, jsonl_path, csv_path):
    """Validate every row, then write the JSONL corpus and its CSV
    projection. Returns the row count. Fail-closed: nothing is written
    unless every row passes check_rows first."""
    count = check_rows(rows)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", newline="") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            stream.write("\n")
    with csv_path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            writer.writerow([_csv_cell(row.get(column)) for column in CSV_COLUMNS])
    return count
