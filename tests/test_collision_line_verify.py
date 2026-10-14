"""G3: sampled occupancy wiring in the line verifier (data-only)."""

import json
from pathlib import Path

import pytest

from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan
from mechanism_generator.omts.geometry import METHOD
from mechanism_generator.omts.line_verify import LineVerificationError, verify_line


TASK_IDS = ["gate", "catcher"]
TARGETS = {"gate": ["hold", "release", "rest"], "catcher": ["grab", "carry", "park"]}
GEOMETRY_KEYS = ("l1", "l2", "l3", "l4", "S_ratio", "bar_length", "base_x", "base_y", "base_angle")
PARAMS = [4, 1.2, 4.5, 3, 0.5, 1.0, 0, 0, 0]  # reaches the fixture regions below
UNDEFINED_PARAMS = [4, 3, 4.5, 3, 0.5, 1.0, 0, 0, 0]  # assembly is undefined at theta 0


def _region(region_id, center, radius):
    return {"id": region_id, "shape": "circle", "center": list(center), "radius": radius}


TOP = _region("top", (0, 1.2), 0.05)        # partial window [88, 92.5]
WRAP = _region("wrap", (1.1998172, 0.0209429), 0.05)  # windows wrap through zero
SIDE = _region("side", (0.6, 0), 0.5)       # thickness changes occupancy
ORIGIN = _region("origin", (0, 0), 0.5)      # occupied at every sample
FAR = _region("far", (50, 50), 1.0)          # never occupied


def _model(thickness=0.0, steps=720, mode="hard", carrier=None):
    model = {"thickness": thickness, "steps": steps, "mode": mode}
    if carrier is not None:
        model["carrier"] = {"width": carrier[0], "depth": carrier[1]}
    return model


def _row(row_id, phases, params=PARAMS, branch_sign=1):
    row = {"candidate_id": row_id, "branch_sign": branch_sign}
    row.update({f"phase_{index + 1}_deg": phase for index, phase in enumerate(phases)})
    row.update(dict(zip(GEOMETRY_KEYS, params)))
    return row


def _write_manifest(root, task, rows, crank="positive", status="completed"):
    run_dir = root / f"results/task-{TASK_IDS.index(task) + 1:03d}" / "r25c" / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_status": status,
        "targets": [{
            "label": task,
            "crank_direction": crank,
            "selected": [dict(row, rank=rank) for rank, row in enumerate(rows, start=1)],
        }],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_plan(root, line):
    plan = {
        "task_set_id": "pair",
        "runs": [
            {"task_id": task, "target_ids": TARGETS[task],
             "output_root": f"results/task-{TASK_IDS.index(task) + 1:03d}"}
            for task in TASK_IDS
        ],
        "line": line,
    }
    (root / "run_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return root


def _line(regions=None, collision=None, relations=None, applied_offsets=None):
    line = {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": {"gate": "hold", "catcher": None},
        "events": [],
        "relations": relations or [],
        "verification": "pending_timeline_verification",
    }
    if regions is not None:
        line["regions"] = regions
    if collision is not None:
        line["collision"] = collision
    if applied_offsets is not None:
        line["applied_offsets"] = applied_offsets
    return line


def _verify(root, line, gate_rows=None, catcher_rows=None):
    _write_manifest(root, "gate", gate_rows if gate_rows is not None else [_row("g1", [30, 130, 250])])
    _write_manifest(root, "catcher", catcher_rows if catcher_rows is not None else [_row("c1", [120, 220, 20])])
    _write_plan(root, line)
    return verify_line(root)


def test_partial_window_reports_raw_windows(tmp_path):
    result = _verify(tmp_path, _line(regions=[TOP], collision={"gate": _model()}))
    section = result["collision"]
    assert section["method"] == METHOD
    assert section["regions"] == ["top"]
    assert set(section["tasks"]) == {"gate"}
    task = section["tasks"]["gate"]
    assert task["steps"] == 720
    assert task["mode"] == "hard"
    assert task["thickness"] == 0.0
    assert "carrier" not in task
    region = task["candidates"][0]["regions"]["top"]
    assert region["windows"] == [{"start_deg": 88.0, "end_deg": 92.5}]
    assert region["enters_deg"] == [88.0]
    assert region["exits_deg"] == [92.5]


def test_composed_windows_anchor_at_phase_reference(tmp_path):
    # gate holds at raw phase 30, so composed windows shift by -30 deg.
    result = _verify(tmp_path, _line(regions=[TOP], collision={"gate": _model()}))
    region = result["collision"]["tasks"]["gate"]["candidates"][0]["regions"]["top"]
    assert region["composed_windows"] == [{"start_deg": 58.0, "end_deg": 62.5}]
    assert region["composed_enters_deg"] == [58.0]
    assert region["composed_exits_deg"] == [62.5]


def test_composed_windows_include_declared_offsets(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model()}, applied_offsets={"gate": 10})
    result = _verify(tmp_path, line)
    region = result["collision"]["tasks"]["gate"]["candidates"][0]["regions"]["top"]
    assert region["composed_windows"] == [{"start_deg": 68.0, "end_deg": 72.5}]


def test_wrap_through_zero_windows(tmp_path):
    result = _verify(tmp_path, _line(regions=[WRAP], collision={"gate": _model()}))
    region = result["collision"]["tasks"]["gate"]["candidates"][0]["regions"]["wrap"]
    assert region["windows"] == [{"start_deg": 359.0, "end_deg": 4.0},
                                 {"start_deg": 57.0, "end_deg": 65.5}]


def test_always_occupied_window(tmp_path):
    result = _verify(tmp_path, _line(regions=[ORIGIN], collision={"gate": _model()}))
    region = result["collision"]["tasks"]["gate"]["candidates"][0]["regions"]["origin"]
    assert region["windows"] == [{"start_deg": 0.0, "end_deg": 359.5}]
    assert region["composed_windows"] == [{"start_deg": 330.0, "end_deg": 329.5}]


def test_never_occupied_window(tmp_path):
    result = _verify(tmp_path, _line(regions=[FAR], collision={"gate": _model()}))
    region = result["collision"]["tasks"]["gate"]["candidates"][0]["regions"]["far"]
    assert region["windows"] == []
    assert region["composed_windows"] == []
    assert region["enters_deg"] == []


def test_thickness_contrast_between_tasks(tmp_path):
    line = _line(regions=[SIDE],
                collision={"gate": _model(thickness=0.0), "catcher": _model(thickness=0.2)})
    result = _verify(tmp_path, line)
    tasks = result["collision"]["tasks"]
    assert tasks["gate"]["candidates"][0]["regions"]["side"]["windows"] == [
        {"start_deg": 304.0, "end_deg": 56.0}, {"start_deg": 64.0, "end_deg": 137.0}]
    assert tasks["catcher"]["candidates"][0]["regions"]["side"]["windows"] == [
        {"start_deg": 0.0, "end_deg": 359.5}]
    assert tasks["catcher"]["thickness"] == 0.2


def test_per_candidate_composition(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model()})
    result = _verify(tmp_path, line,
                     gate_rows=[_row("g1", [30, 130, 250]), _row("g2", [60, 160, 280])])
    by_id = {entry["id"]: entry for entry in result["collision"]["tasks"]["gate"]["candidates"]}
    assert by_id["g1"]["regions"]["top"]["composed_enters_deg"] == [58.0]
    assert by_id["g2"]["regions"]["top"]["composed_enters_deg"] == [28.0]


def test_undefined_assembly_is_an_error(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model()})
    with pytest.raises(LineVerificationError, match="undefined") as excinfo:
        _verify(tmp_path, line, gate_rows=[_row("g1", [30, 130, 250], params=UNDEFINED_PARAMS)])
    assert "g1" in str(excinfo.value)
    assert "top" in str(excinfo.value)


@pytest.mark.parametrize("missing", ["S_ratio", "branch_sign"])
def test_manifest_row_needs_candidate_geometry(tmp_path, missing):
    line = _line(regions=[TOP], collision={"gate": _model()})
    row = _row("g1", [30, 130, 250])
    row.pop(missing)
    with pytest.raises(LineVerificationError, match="lacks"):
        _verify(tmp_path, line, gate_rows=[row])


def test_no_collision_section_without_features(tmp_path):
    assert "collision" not in _verify(tmp_path, _line())
    # Collision body models without regions compute nothing either.
    assert "collision" not in _verify(tmp_path, _line(collision={"gate": _model()}))


def test_verdict_unchanged_with_collision_data(tmp_path):
    # The line fails its ordering relation (grab at 160: anchored release 100,
    # lead 60 > 45); the collision section reports data anyway.
    line = _line(regions=[TOP], collision={"gate": _model()}, relations=[{
        "id": "release_before_grab", "from": {"task": "gate", "target": "release"},
        "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
        "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard",
    }])
    result = _verify(tmp_path, line, catcher_rows=[_row("c1", [160, 220, 20])])
    assert result["status"] == "failed"
    assert result["collision"]["tasks"]["gate"]["candidates"][0]["regions"]["top"]["windows"] == [
        {"start_deg": 88.0, "end_deg": 92.5}]


def test_zero_candidates_skips_collision_section(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model()})
    result = _verify(tmp_path, line, gate_rows=[])
    assert result["status"] == "no_candidates"
    assert "collision" not in result


def test_regions_without_models_report_a_note(tmp_path):
    result = _verify(tmp_path, _line(regions=[TOP]))
    section = result["collision"]
    assert section["tasks"] == {}
    assert any("No task declares a collision body model" in note for note in section["notes"])


def test_carrier_flows_through(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(carrier=(1.0, 0.5))})
    result = _verify(tmp_path, line)
    task = result["collision"]["tasks"]["gate"]
    assert task["carrier"] == {"width": 1.0, "depth": 0.5}
    assert task["candidates"][0]["regions"]["top"]["windows"] == [{"start_deg": 88.0, "end_deg": 92.5}]


# -- adapter: recording and the remaining fail-closed boundaries ----------------

def _document(relations=None):
    def _task(task_id, collision, reference=None):
        task = {
            "id": task_id,
            "motion": {
                "mode": "cyclic",
                "order_policy": "unordered",
                "targets": [
                    {"id": target_id, "position": [0.5 + 0.3 * index, 0.5]}
                    for index, target_id in enumerate(TARGETS[task_id])
                ],
            },
            "mechanism_search": {
                "allowed_topologies": ["four_bar"],
                "max_dof": 1,
                "max_actuators": 1,
            },
        }
        if reference is not None:
            task["motion"]["cycle"] = {"phase_reference": reference}
        task["requirements"] = {"collision": collision}
        return task

    document = {
        "spec": "open-mechanism-task",
        "version": "0.2.0",
        "task_set_id": "collision-g3",
        "units": {"length": "normalized", "angle": "deg", "time": "s"},
        "coordinate_system": {"frame_id": "world", "dimension": 2, "handedness": "right"},
        "regions": [{"id": "shared_zone", "shape": "box", "min": [0, 0], "max": [1, 1]}],
        "tasks": [
            _task("gate", {"bodies": {"links": {"thickness": 0.5}}}, reference="hold"),
            _task("catcher", {
                "bodies": {"links": {"thickness": 0.2}, "carrier": {"width": 1.0, "depth": 0.5}},
                "steps": 1441,
                "mode": "soft",
            }),
        ],
        "synchronization": {"participants": [{"task": "gate"}, {"task": "catcher"}]},
    }
    if relations is not None:
        document["synchronization"]["relations"] = relations
    return document


def test_adapter_records_regions_and_collision_models():
    plan = prepare_plan(_document())
    line = plan["line"]
    assert line["regions"] == [{"id": "shared_zone", "shape": "box", "min": [0, 0], "max": [1, 1]}]
    assert line["collision"]["gate"] == {"thickness": 0.5, "steps": 720, "mode": "hard"}
    assert line["collision"]["catcher"] == {
        "thickness": 0.2, "steps": 1441, "mode": "soft",
        "carrier": {"width": 1.0, "depth": 0.5},
    }
    assert any("post-hoc sampled occupancy" in note for note in plan["notes"])


def test_adapter_rejects_ordering_over_derived_region_events():
    document = _document(relations=[{
        "id": "enter_after_release",
        "from": "gate.release.reached",
        "to": "gate.enters_region.shared_zone",
        "type": "ordering",
        "min_lead": {"phase": 10},
        "mode": "hard",
    }])
    with pytest.raises(UnsupportedFeature, match="derived region events") as excinfo:
        prepare_plan(document)
    assert "G5" in str(excinfo.value)


def test_adapter_rejects_disjoint_windows_until_g5():
    # Bare relation shape: no clearance key, so the adapter's own key
    # whitelist is not the layer under test -- the relation type is.
    document = _document(relations=[{
        "id": "zone_keepout",
        "from": "gate.occupies_region.shared_zone",
        "to": "catcher.occupies_region.shared_zone",
        "type": "disjoint_windows",
    }])
    with pytest.raises(UnsupportedFeature, match="ordering and fixed_offset") as excinfo:
        prepare_plan(document)
    assert "G5" in str(excinfo.value)
