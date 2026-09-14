import copy
import json
import math

import pytest
from jsonschema import Draft202012Validator

from mechanism_generator.omts import DocumentError, load_document, validate_document
from mechanism_generator.omts.validation import schema_document


def test_schema_and_both_examples_are_valid(task_document, future_document):
    Draft202012Validator.check_schema(schema_document())
    assert validate_document(task_document) == []
    assert validate_document(future_document) == []


@pytest.mark.parametrize("suffix,text", [
    (".json", '{"spec":"first","spec":"second"}'),
    (".yaml", 'spec: first\nspec: second\n'),
    (".yaml", '1: value\n'),
    (".yaml", 'value: &cycle [*cycle]\n'),
    (".yaml", 'value: .nan\n'),
    (".json", '{"value": Infinity}'),
    (".yaml", 'value: !!python/object/apply:os.system ["echo should-not-run"]'),
])
def test_ambiguous_or_non_json_inputs_are_rejected(tmp_path, suffix, text):
    path = tmp_path / ("task" + suffix)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(DocumentError):
        load_document(path)


def test_timestamp_metadata_and_utf8_bom(tmp_path, task_document):
    task_document["metadata"] = {"created_utc": "2026-09-14T12:00:00Z"}
    import yaml
    path = tmp_path / "task.yaml"
    path.write_text(yaml.safe_dump(task_document), encoding="utf-8-sig")
    assert validate_document(load_document(path)) == []
    path.write_text('metadata: {created_utc: 2026-09-14T12:00:00Z}', encoding="utf-8")
    assert isinstance(load_document(path)["metadata"]["created_utc"], str)


def test_duplicate_ids_unknown_references_and_dimensions(future_document):
    future_document["payloads"].append(copy.deepcopy(future_document["payloads"][0]))
    future_document["load_cases"][0]["payload_ref"] = "missing"
    target = future_document["tasks"][1]["motion"]["targets"][0]
    target["position"] = [1, 2, 3]
    target["load_case_ref"] = "missing"
    future_document["synchronization"]["events"][0]["participants"] = ["missing"]
    errors = "\n".join(validate_document(future_document))
    for fragment in ("duplicate ID", "payload_ref", "expected 2", "load_case_ref", "unknown task"):
        assert fragment in errors


def test_ground_bounds_and_initial_value(task_document):
    search = task_document["tasks"][0]["mechanism_search"]
    search["ground_link"] = {"mode": "optimize", "bounds": [9, 3], "initial_value": 12}
    errors = "\n".join(validate_document(task_document))
    assert "minimum must not exceed maximum" in errors
    assert "initial_value is outside bounds" in errors
    search["ground_link"] = {"mode": "fixed", "value": 6}
    search["bounds"] = {"l1": [7, 10], "l2": [-1, 3]}
    errors = "\n".join(validate_document(task_document))
    assert "outside l1 bounds" in errors
    assert "lengths must be positive" in errors


def test_order_and_fixed_timing_semantics(task_document):
    motion = task_document["tasks"][0]["motion"]
    motion["order_policy"] = "ordered"
    motion["targets"][0]["occurrence"]["order_index"] = 1
    assert any("every target" in error for error in validate_document(task_document))
    for target in motion["targets"]:
        target["occurrence"]["order_index"] = 1
    assert any("unique" in error for error in validate_document(task_document))
    motion["order_policy"] = "fixed_timing"
    assert any("fixed_timing requires" in error for error in validate_document(task_document))


def test_transmission_limits_follow_angle_units(task_document):
    task_document["units"]["angle"] = "rad"
    tx = task_document["tasks"][0]["requirements"]["transmission"]
    for key in ("min_at_targets", "min_global", "selection_min_at_targets", "selection_min_global"):
        tx[key] = math.pi / 4
    assert validate_document(task_document) == []
    tx["min_at_targets"] = 2
    assert any("exceeds" in error for error in validate_document(task_document))
    task_document["units"]["angle"] = "deg"
    tx["min_at_targets"] = 91
    assert any("exceeds" in error for error in validate_document(task_document))


def test_validation_does_not_mutate_or_crash_on_wrong_types(task_document):
    before = copy.deepcopy(task_document)
    assert validate_document(task_document) == []
    assert task_document == before
    for malformed in ([], None, 2, {"tasks": [None]}, {"spec": float("nan")}):
        assert validate_document(malformed)


def test_json_and_yaml_have_identical_meaning(tmp_path, task_document):
    path = tmp_path / "task.json"
    path.write_text(json.dumps(task_document), encoding="utf-8")
    assert load_document(path) == task_document
