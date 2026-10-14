"""G2: validation of OMTS v0.2 collision regions and collision bodies."""

import pytest

from mechanism_generator.omts import validate_document
from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan


def _task(task_id, target_id, phase, collision=True):
    task = {
        "id": task_id,
        "motion": {
            "mode": "cyclic",
            "order_policy": "unordered",
            "targets": [
                {"id": target_id, "position": [0.5, 0.5], "occurrence": {"phase": phase}}
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


def _collision_document():
    return {
        "spec": "open-mechanism-task",
        "version": "0.2.0",
        "task_set_id": "collision-g2",
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


def test_valid_collision_document():
    assert validate_document(_collision_document()) == []


def test_unknown_region_reference():
    document = _collision_document()
    document["synchronization"]["relations"][0]["to"] = "catcher.occupies_region.ghost"
    errors = validate_document(document)
    assert any("unknown region 'ghost'" in error for error in errors)


def test_region_events_require_collision_bodies():
    document = _collision_document()
    document["tasks"][1] = _task("catcher", "drop", 180.0, collision=False)
    errors = validate_document(document)
    assert any("declares no collision body model" in error for error in errors)


def test_window_relation_over_region_point_event():
    document = _collision_document()
    document["synchronization"]["relations"][0]["from"] = "gate.enters_region.shared_zone"
    errors = validate_document(document)
    assert any("requires a window event" in error for error in errors)


def test_ordering_over_region_boundary_point_is_valid():
    document = _collision_document()
    document["synchronization"]["relations"] = [
        {
            "id": "enter_after_pick",
            "from": "gate.pick.reached",
            "to": "gate.enters_region.shared_zone",
            "type": "ordering",
            "min_lead": {"phase": 10},
            "mode": "hard",
        }
    ]
    assert validate_document(document) == []


def test_unknown_region_event_kind():
    document = _collision_document()
    document["synchronization"]["relations"][0]["from"] = "gate.sweeps_region.shared_zone"
    errors = validate_document(document)
    assert any("unknown task, target, or event" in error for error in errors)


def test_reserved_segment_in_target_id():
    document = _collision_document()
    document["tasks"][0]["motion"]["targets"][0]["id"] = "occupies_region.zone"
    errors = validate_document(document)
    assert any("reserved region-event segment" in error for error in errors)


def test_reserved_segment_in_authored_event_id():
    document = _collision_document()
    document["synchronization"]["events"] = [
        {"id": "gate.enters_region.shared_zone", "participants": ["gate.pick.reached"]}
    ]
    errors = validate_document(document)
    assert any("derived events are computed, not authored" in error for error in errors)


def test_region_id_colliding_with_target_event_kind():
    document = _collision_document()
    document["regions"][0]["id"] = "reached"
    errors = validate_document(document)
    assert any("collides with target event kinds" in error for error in errors)


def test_duplicate_region_ids():
    document = _collision_document()
    document["regions"].append(dict(document["regions"][0]))
    errors = validate_document(document)
    assert any("duplicate ID 'shared_zone'" in error for error in errors)


def test_v01_rejects_collision_features():
    document = _collision_document()
    document["version"] = "0.1.0"
    document.pop("synchronization")
    errors = validate_document(document)
    assert any("regions are a v0.2 collision feature" in error for error in errors)
    assert any("collision bodies are a v0.2 collision feature" in error for error in errors)


def test_nonplanar_document_rejects_collision_features():
    document = _collision_document()
    document["coordinate_system"]["dimension"] = 3
    for task in document["tasks"]:
        task["motion"]["targets"][0]["position"] = [0.5, 0.5, 0.0]
    document["regions"][0]["min"] = [0, 0, 0]
    document["regions"][0]["max"] = [1, 1, 1]
    document["regions"][1]["center"] = [0.5, 0.5, 0.5]
    errors = validate_document(document)
    assert any("regions are planar" in error for error in errors)
    assert any("collision bodies are planar" in error for error in errors)


def test_box_region_min_exceeds_max():
    document = _collision_document()
    document["regions"][0]["min"] = [2, 0]
    errors = validate_document(document)
    assert any("min must not exceed max" in error for error in errors)


def test_region_vector_component_count():
    document = _collision_document()
    document["regions"][0]["min"] = [0, 0, 0]
    errors = validate_document(document)
    assert any("expected 2 vector components" in error for error in errors)


def test_carrier_dimensions_must_be_positive():
    document = _collision_document()
    document["tasks"][0]["requirements"]["collision"]["bodies"]["carrier"] = {"width": 0, "depth": 1}
    errors = validate_document(document)
    assert errors
    assert any("carrier.width" in error for error in errors)


def test_collision_steps_below_minimum():
    document = _collision_document()
    document["tasks"][0]["requirements"]["collision"]["steps"] = 360
    errors = validate_document(document)
    assert errors
    assert any("steps" in error for error in errors)


def test_adapter_rejects_collision_features_without_synchronization():
    document = _collision_document()
    document.pop("synchronization")
    with pytest.raises(UnsupportedFeature) as excinfo:
        prepare_plan(document)
    assert "regions" in str(excinfo.value)
    assert "synchronization line" in str(excinfo.value)
