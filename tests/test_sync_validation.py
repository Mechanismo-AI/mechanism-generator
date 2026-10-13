import copy
from pathlib import Path

import pytest

from mechanism_generator.omts import load_document, validate_document


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def v02_document():
    return load_document(ROOT / "examples/omts/synchronized_line_v02_draft.omts.yaml")


def _task(task_id, target_id, period, phase):
    return {
        "id": task_id,
        "motion": {
            "mode": "cyclic",
            "order_policy": "fixed_timing",
            "cycle": {"period": period},
            "targets": [{
                "id": target_id,
                "position": [0.0, 0.0],
                "occurrence": {"phase": phase},
            }],
        },
        "mechanism_search": {
            "allowed_topologies": ["four_bar"],
            "max_dof": 1,
            "max_actuators": 1,
        },
    }


def _v02_document():
    return {
        "spec": "open-mechanism-task",
        "version": "0.2.0",
        "task_set_id": "sync_unit",
        "units": {"length": "normalized", "angle": "deg", "time": "s"},
        "coordinate_system": {"frame_id": "world", "dimension": 2, "handedness": "right"},
        "synchronization": {
            "master_cycle_id": "line",
            "period": 1.0,
            "participants": [{"task": "alpha"}, {"task": "beta", "ratio": [1, 2]}],
            "events": [{
                "id": "hand",
                "type": "handoff",
                "participants": ["alpha.first.reached", "beta.second.reached"],
                "window": {"phase_range": [10, 20]},
                "tolerance": {"phase": 2},
            }],
            "relations": [{
                "id": "lead",
                "from": "alpha.first.reached",
                "to": "beta.second.reached",
                "type": "ordering",
                "min_lead": {"phase": 5},
                "max_lead": {"phase": 30},
                "mode": "hard",
            }],
        },
        "tasks": [_task("alpha", "first", 1.0, 30), _task("beta", "second", 2.0, 60)],
    }


def _errors(document):
    return "\n".join(validate_document(document))


def test_v02_example_file_validates(v02_document):
    assert validate_document(v02_document) == []


def test_minimal_v02_document_is_valid():
    assert validate_document(_v02_document()) == []


def test_v01_documents_still_validate(task_document, future_document):
    assert validate_document(task_document) == []
    assert validate_document(future_document) == []


def test_ratio_must_be_positive_integers():
    document = _v02_document()
    document["synchronization"]["participants"][1]["ratio"] = [0, 2]
    assert validate_document(document)


def test_unknown_phase_reference_is_rejected():
    document = _v02_document()
    document["tasks"][0]["motion"]["cycle"]["phase_reference"] = "missing"
    assert "phase_reference" in _errors(document)


def test_period_must_match_ratio():
    document = _v02_document()
    document["tasks"][1]["motion"]["cycle"]["period"] = 3.0
    assert "does not match the master period" in _errors(document)


def test_unknown_participant_task_is_rejected():
    document = _v02_document()
    document["synchronization"]["participants"][0]["task"] = "ghost"
    assert "unknown task" in _errors(document)


def test_ordering_lead_bounds():
    document = _v02_document()
    relation = document["synchronization"]["relations"][0]
    relation["min_lead"], relation["max_lead"] = {"phase": 40}, {"phase": 30}
    assert "min_lead must not exceed max_lead" in _errors(document)


def test_contains_requires_windows():
    document = _v02_document()
    relation = document["synchronization"]["relations"][0]
    relation["type"] = "contains"
    assert "requires a window event" in _errors(document)
    document["tasks"][0]["motion"]["targets"][0]["dwell"] = {"phase_span": 10}
    document["tasks"][1]["motion"]["targets"][0]["dwell"] = {"phase_span": 10}
    relation["from"], relation["to"] = "alpha.first.dwell", "beta.second.dwell"
    relation.pop("min_lead"), relation.pop("max_lead")
    relation["margin"] = {"phase": 2}
    assert validate_document(document) == []


def test_dwell_reference_requires_declared_dwell():
    document = _v02_document()
    document["synchronization"]["events"][0]["participants"] = ["alpha.first.dwell", "beta.second.reached"]
    assert "declares no dwell" in _errors(document)


def test_fixed_offset_cycle_is_overconstrained():
    document = _v02_document()
    document["synchronization"]["relations"] = [
        {"id": "a", "from": "alpha.first.reached", "to": "beta.second.reached",
         "type": "fixed_offset", "offset": {"phase": 30}, "tolerance": {"phase": 2}},
        {"id": "b", "from": "beta.second.reached", "to": "alpha.first.reached",
         "type": "fixed_offset", "offset": {"phase": 30}, "tolerance": {"phase": 2}},
    ]
    assert "must not form a cycle" in _errors(document)


def test_bare_tolerance_is_rejected_in_v02():
    document = _v02_document()
    document["synchronization"]["events"][0]["tolerance"] = 2
    assert "unit-quantified" in _errors(document)


def test_occurrence_index_requires_ratioed_task():
    document = _v02_document()
    relation = document["synchronization"]["relations"][0]
    relation["occurrence_index"] = 0
    assert "requires a ratioed participant task" in _errors(document)
    document["synchronization"]["participants"].append({"task": "alpha"})
    errors = _errors(document)
    assert "requires a ratioed participant task" not in errors
    document = _v02_document()
    document["synchronization"]["participants"][1] = {"task": "beta", "ratio": [2, 1]}
    document["tasks"][1]["motion"]["cycle"]["period"] = 0.5
    document["synchronization"]["relations"][0]["to"] = "beta.second.reached"
    document["synchronization"]["relations"][0]["occurrence_index"] = 2
    assert "occurrence(s)" in _errors(document)


def test_unknown_event_kind_is_rejected():
    document = _v02_document()
    document["synchronization"]["events"][0]["participants"] = ["alpha.first.hovered", "beta.second.reached"]
    assert "event kind" in _errors(document)


def test_v02_documents_cannot_be_adapted(v02_document):
    from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan
    with pytest.raises(UnsupportedFeature):
        prepare_plan(v02_document)
