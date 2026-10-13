from pathlib import Path

import pytest

from mechanism_generator.omts import load_document
from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pair_document():
    return load_document(ROOT / "examples/omts/synchronized_pair.omts.yaml")


@pytest.fixture
def draft_document():
    return load_document(ROOT / "examples/omts/synchronized_line_v02_draft.omts.yaml")


def test_pair_example_prepares_with_line_section(pair_document):
    plan = prepare_plan(pair_document)
    assert [run["task_id"] for run in plan["runs"]] == ["gate", "catcher"]
    line = plan["line"]
    assert line["verification"] == "pending_timeline_verification"
    assert line["master_cycle_id"] == "line_shaft"
    assert line["phase_reference"] == {"gate": "hold", "catcher": "grab"}
    relation = line["relations"][0]
    assert relation["id"] == "release_before_grab"
    assert relation["from"] == {"task": "gate", "target": "release"}
    assert relation["min_lead_deg"] == 10
    assert relation["max_lead_deg"] == 45
    event = line["events"][0]
    assert event["window_deg"] == [100, 140]
    assert event["tolerance_deg"] == 5
    assert plan["omts_version"] == "0.2.0"


def test_sync_note_records_pending_verification(pair_document):
    assert any("timeline verification" in note for note in prepare_plan(pair_document)["notes"])


def test_plan_without_synchronization_has_no_line(task_document):
    plan = prepare_plan(task_document)
    assert "line" not in plan
    assert plan["omts_version"] == task_document["version"]


def test_ratioed_participation_is_rejected(pair_document):
    pair_document["synchronization"]["participants"][1]["ratio"] = [1, 2]
    with pytest.raises(UnsupportedFeature, match="ratioed participation"):
        prepare_plan(pair_document)


def test_handoff_events_are_rejected(pair_document):
    pair_document["synchronization"]["events"][0]["type"] = "handoff"
    with pytest.raises(UnsupportedFeature, match="co_active"):
        prepare_plan(pair_document)


def test_window_relations_are_rejected(pair_document):
    pair_document["synchronization"]["relations"][0]["type"] = "contains"
    with pytest.raises(UnsupportedFeature, match="ordering and fixed_offset"):
        prepare_plan(pair_document)


def test_time_quantities_are_rejected(pair_document):
    pair_document["synchronization"]["relations"][0]["min_lead"] = {"time": 0.05}
    with pytest.raises(UnsupportedFeature, match="phase-quantified"):
        prepare_plan(pair_document)


def test_occurrence_index_is_rejected(pair_document):
    pair_document["synchronization"]["relations"][0]["occurrence_index"] = 0
    with pytest.raises(UnsupportedFeature, match="occurrence_index"):
        prepare_plan(pair_document)


def test_v01_synchronization_is_rejected(future_document):
    with pytest.raises(UnsupportedFeature):
        prepare_plan(future_document)


def test_v02_draft_example_remains_unadaptable(draft_document):
    with pytest.raises(UnsupportedFeature):
        prepare_plan(draft_document)
