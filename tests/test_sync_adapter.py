from pathlib import Path

import pytest

from mechanism_generator.omts import DocumentError, load_document
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
    assert line["phase_reference"] == {"gate": "hold", "catcher": None}
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
    catcher = next(task for task in pair_document["tasks"] if task["id"] == "catcher")
    catcher["motion"]["cycle"]["period"] = 2.4  # consistent with ratio [1, 2] of the 1.2 s master cycle
    with pytest.raises(UnsupportedFeature, match="ratioed participation"):
        prepare_plan(pair_document)

def test_handoff_events_are_rejected(pair_document):
    pair_document["synchronization"]["events"][0]["type"] = "handoff"
    with pytest.raises(UnsupportedFeature, match="co_active"):
        prepare_plan(pair_document)

def test_window_relations_are_rejected(pair_document):
    # Build a *valid* contains relation first: both references are window
    # events (the semantic layer requires that), so the adapter itself must be
    # the layer that rejects the unsupported relation type. Dwell windows are
    # no alternative here: task-level dwell is itself outside the adapter's
    # target whitelist, which would fail the test for the wrong reason.
    sync = pair_document["synchronization"]
    sync["events"].append({
        "id": "carry_window",
        "type": "co_active",
        "participants": ["gate.release.reached", "catcher.carry.reached"],
        "window": {"phase_range": [110, 130]},
        "tolerance": {"phase": 5},
        "mode": "hard",
    })
    relation = sync["relations"][0]
    relation.pop("min_lead", None)
    relation.pop("max_lead", None)
    relation["type"] = "contains"
    relation["from"] = "carry_window"
    relation["to"] = "handoff_window"
    with pytest.raises(UnsupportedFeature, match="ordering and fixed_offset"):
        prepare_plan(pair_document)

def test_time_quantities_are_rejected(pair_document):
    pair_document["synchronization"]["relations"][0]["min_lead"] = {"time": 0.05}
    with pytest.raises(UnsupportedFeature, match="phase-quantified"):
        prepare_plan(pair_document)

def test_occurrence_index_is_rejected(pair_document):
    # occurrence_index is only expressible on a ratioed task; declare the
    # catcher's explicit 1:1 ratio (a ratioed declaration that still matches
    # the master period) so the document stays valid and the adapter's own
    # rejection is the one under test.
    pair_document["synchronization"]["participants"][1]["ratio"] = [1, 1]
    pair_document["synchronization"]["relations"][0]["occurrence_index"] = 0
    with pytest.raises(UnsupportedFeature, match="occurrence_index"):
        prepare_plan(pair_document)

def test_v01_synchronization_is_rejected(future_document):
    with pytest.raises(UnsupportedFeature):
        prepare_plan(future_document)

def test_v02_draft_example_remains_unadaptable(draft_document):
    with pytest.raises(UnsupportedFeature):
        prepare_plan(draft_document)

def test_reference_target_in_nonzero_window_is_rejected(pair_document):
    # Re-anchor the catcher at grab; the handoff window [100, 140] can never contain phase 0.
    catcher = next(task for task in pair_document["tasks"] if task["id"] == "catcher")
    catcher["motion"]["cycle"]["phase_reference"] = "grab"
    with pytest.raises(UnsupportedFeature, match="phase_reference target and is always at phase 0"):
        prepare_plan(pair_document)

def test_reference_target_in_window_passes_with_matching_offset(pair_document):
    # A declared applied offset moves the reference target into the window.
    catcher = next(task for task in pair_document["tasks"] if task["id"] == "catcher")
    catcher["motion"]["cycle"]["phase_reference"] = "grab"
    pair_document["synchronization"]["applied_offsets"] = {"catcher": {"phase": 120}}
    line = prepare_plan(pair_document)["line"]
    assert line["applied_offsets"] == {"catcher": 120.0}

def test_applied_offsets_are_recorded_in_line(pair_document):
    pair_document["synchronization"]["applied_offsets"] = {"catcher": {"phase": 25}}
    line = prepare_plan(pair_document)["line"]
    assert line["applied_offsets"] == {"catcher": 25.0}

def test_applied_offsets_time_quantity_is_rejected(pair_document):
    pair_document["synchronization"]["applied_offsets"] = {"catcher": {"time": 0.05}}
    with pytest.raises(UnsupportedFeature, match="phase-quantified"):
        prepare_plan(pair_document)

def test_applied_offsets_unknown_task_is_rejected(pair_document):
    # Validation rejects unknown offset tasks before the adapter's own
    # defense-in-depth check is reached; both layers fail closed.
    pair_document["synchronization"]["applied_offsets"] = {"ghost": {"phase": 5}}
    with pytest.raises(DocumentError, match="unknown task"):
        prepare_plan(pair_document)
