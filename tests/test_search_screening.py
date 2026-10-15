"""Z1+Z2: OMTS v0.2 search-time zone screening vocabulary, validation, and adapter."""

import json

import pytest

from mechanism_generator.omts import validate_document
from mechanism_generator.omts.adapter import prepare_plan, write_plan
from mechanism_generator.omts.geometry import (
    MAX_STEPS,
    MIN_STEPS,
    occupancy_summary,
    window_width,
)


def _task(task_id, target_id, phase, collision=True):
    task = {
        "id": task_id,
        "motion": {
            "mode": "cyclic",
            "order_policy": "unordered",
            "targets": [
                {"id": f"{target_id}-{suffix}", "position": [0.5 + 0.25 * suffix, 0.5]}
                for suffix in range(3)
            ],
        },
        "mechanism_search": {
            "allowed_topologies": ["four_bar"],
            "max_dof": 1,
            "max_actuators": 1,
        },
    }
    if collision:
        task["requirements"] = {
            "collision": {
                "bodies": {"links": {"thickness": 0.5}},
                "steps": 720,
                "mode": "hard",
            }
        }
    return task


def _screen_document():
    document = {
        "spec": "open-mechanism-task",
        "version": "0.2.0",
        "task_set_id": "screening-z1",
        "units": {"length": "normalized", "angle": "deg", "time": "s"},
        "coordinate_system": {"frame_id": "world", "dimension": 2, "handedness": "right"},
        "regions": [
            {"id": "shared_zone", "shape": "box", "min": [0, 0], "max": [1, 1]},
            {"id": "approach", "shape": "circle", "center": [0.5, 0.5], "radius": 0.2},
        ],
        "tasks": [_task("gate", "pick", 0.0), _task("catcher", "drop", 180.0)],
        "synchronization": {
            "participants": [{"task": "gate"}, {"task": "catcher"}],
            "relations": [
                {
                    "id": "zone_keepout",
                    "from": "gate.occupies_region.shared_zone",
                    "to": "catcher.occupies_region.shared_zone",
                    "type": "disjoint_windows",
                    "clearance": {"phase": 10},
                    "mode": "hard",
                }
            ],
        },
    }
    document["tasks"][0]["requirements"]["collision"]["screen"] = [
        {
            "region": "shared_zone",
            "max_total_width": {"phase": 30},
            "max_windows": 2,
            "mode": "hard",
        }
    ]
    return document


def test_valid_screen_document():
    assert validate_document(_screen_document()) == []


def test_screen_unknown_region():
    document = _screen_document()
    document["tasks"][0]["requirements"]["collision"]["screen"][0]["region"] = "ghost"
    errors = validate_document(document)
    assert any("unknown region 'ghost'" in error for error in errors)


def test_screen_entry_requires_a_criterion():
    document = _screen_document()
    document["tasks"][0]["requirements"]["collision"]["screen"] = [
        {"region": "shared_zone", "mode": "hard"}
    ]
    errors = validate_document(document)
    assert any("requires at least one criterion" in error for error in errors)


def test_screen_region_twice():
    document = _screen_document()
    screen = document["tasks"][0]["requirements"]["collision"]["screen"]
    screen.append({"region": "shared_zone", "avoid": True})
    errors = validate_document(document)
    assert any("screened more than once" in error for error in errors)


def test_screen_time_quantity_rejected():
    document = _screen_document()
    document["tasks"][0]["requirements"]["collision"]["screen"][0]["max_total_width"] = {"time": 5}
    errors = validate_document(document)
    assert any("requires a phase-quantified value" in error for error in errors)


def test_screen_phase_out_of_range():
    document = _screen_document()
    document["tasks"][0]["requirements"]["collision"]["screen"][0]["max_total_width"] = {"phase": 361}
    errors = validate_document(document)
    assert any("must be within [0, 360]" in error for error in errors)


def test_v01_rejects_screens():
    document = _screen_document()
    document["version"] = "0.1.0"
    document.pop("synchronization")
    errors = validate_document(document)
    assert any("collision bodies are a v0.2 collision feature" in error for error in errors)
    assert any("zone screens are a v0.2 collision feature" in error for error in errors)


def test_adapter_accepts_screen_and_writes_sidecar(tmp_path):
    plan = prepare_plan(_screen_document())
    gate_run = next(run for run in plan["runs"] if run["task_id"] == "gate")
    catcher_run = next(run for run in plan["runs"] if run["task_id"] == "catcher")
    assert gate_run["zone_screen_file"] == "tasks/task-001/zone_screen.json"
    sidecar = gate_run["zone_screen"]
    assert sidecar["method"] == "sampled_collision_geometry_v1"
    assert sidecar["task"] == "gate"
    assert sidecar["steps"] == 720
    assert sidecar["thickness"] == 0.5
    assert {"id": "shared_zone", "shape": "box", "min": [0, 0], "max": [1, 1]} in sidecar["regions"]
    assert sidecar["screen"] == [
        {"region": "shared_zone", "mode": "hard", "max_total_width_deg": 30.0, "max_windows": 2}
    ]
    assert "zone_screen" not in catcher_run
    assert "zone_screen_file" not in catcher_run
    assert any("screened per candidate" in note for note in plan["notes"])
    assert plan["line"]["collision"]["gate"]["screen"] == sidecar["screen"]
    write_plan(_screen_document(), tmp_path / "plan")
    written = json.loads((tmp_path / "plan" / gate_run["zone_screen_file"]).read_text(encoding="utf-8"))
    assert written == sidecar
    run_plan = json.loads((tmp_path / "plan" / "run_plan.json").read_text(encoding="utf-8"))
    gate_json = next(run for run in run_plan["runs"] if run["task_id"] == "gate")
    assert gate_json["zone_screen_file"] == gate_run["zone_screen_file"]
    assert "zone_screen" not in gate_json


def test_window_width_is_wrap_aware():
    steps = 720
    assert window_width({"start_deg": 100.0, "end_deg": 200.0}, steps) == pytest.approx(100.5)
    assert window_width({"start_deg": 350.0, "end_deg": 10.0}, steps) == pytest.approx(20.5)


def test_window_width_full_cycle_is_360():
    steps = 720
    full = {"start_deg": 0.0, "end_deg": 360.0 - 360.0 / steps}
    assert window_width(full, steps) == pytest.approx(360.0)


def test_occupancy_summary_empty():
    assert occupancy_summary([], 720) == {"windows": 0, "total_width_deg": 0.0}


def test_window_width_rejects_out_of_range_steps():
    for steps in (360, MAX_STEPS + 1, True, 720.0):
        with pytest.raises(ValueError):
            window_width({"start_deg": 0.0, "end_deg": 1.0}, steps)
    assert MIN_STEPS == 361
