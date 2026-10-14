"""G4: composed timeline artifact (sampled input phases and body poses)."""

import json
from pathlib import Path

import pytest

from mechanism_generator.omts.cli import main
from mechanism_generator.omts.geometry import METHOD, four_bar_skeleton
from mechanism_generator.omts.line_verify import LineVerificationError
from mechanism_generator.omts.timeline import compose_timeline, write_timeline


TASK_IDS = ["gate", "catcher"]
TARGETS = {"gate": ["hold", "release", "rest"], "catcher": ["grab", "carry", "park"]}
GEOMETRY_KEYS = ("l1", "l2", "l3", "l4", "S_ratio", "bar_length", "base_x", "base_y", "base_angle")
PARAMS = [4, 1.2, 4.5, 3, 0.5, 1.0, 0, 0, 0]
UNDEFINED_PARAMS = [4, 3, 4.5, 3, 0.5, 1.0, 0, 0, 0]  # assembly is undefined at input phase 0


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


def _line(applied_offsets=None, collision=None, phase_reference=None):
    line = {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": phase_reference if phase_reference is not None
        else {"gate": "hold", "catcher": None},
        "events": [],
        "relations": [],
        "verification": "pending_timeline_verification",
    }
    if applied_offsets is not None:
        line["applied_offsets"] = applied_offsets
    if collision is not None:
        line["collision"] = collision
    return line


def _model(steps=720, carrier=None):
    model = {"thickness": 0.0, "steps": steps, "mode": "hard"}
    if carrier is not None:
        model["carrier"] = {"width": carrier[0], "depth": carrier[1]}
    return model


def _compose(root, line, gate_rows=None, catcher_rows=None, steps=720):
    _write_manifest(root, "gate", gate_rows if gate_rows is not None else [_row("g1", [30, 130, 250])])
    _write_manifest(root, "catcher", catcher_rows if catcher_rows is not None else [_row("c1", [120, 220, 20])])
    _write_plan(root, line)
    return compose_timeline(root, steps=steps)


def _candidate(timeline, task, candidate_id):
    return next(item for item in timeline["tasks"][task]["candidates"]
                if item["candidate_id"] == candidate_id)


def test_header_and_composition_defaults(tmp_path):
    timeline = _compose(tmp_path, _line())
    assert timeline["timeline_version"] == 1
    assert timeline["method"] == METHOD
    assert timeline["master_cycle_id"] == "line_shaft"
    assert timeline["period"] == 1.2
    assert timeline["steps"] == 720
    assert timeline["sample_step_deg"] == 0.5
    assert sorted(timeline["tasks"]) == ["catcher", "gate"]
    assert "applied_offsets" not in timeline
    gate = _candidate(timeline, "gate", "g1")
    assert gate["parameters"] == dict(zip(GEOMETRY_KEYS, PARAMS))
    assert gate["branch_sign"] == 1
    assert gate["reference_phase_deg"] == 30.0
    assert gate["shift_deg"] == -30.0
    # Master phase 0 puts the reference target at input phase 30.
    assert gate["input_phase_deg"][0] == 30.0
    assert gate["input_phase_deg"][10] == 35.0
    assert len(gate["input_phase_deg"]) == 720
    assert len(gate["poses"]) == 720


def test_unanchored_task_contributes_raw_phases(tmp_path):
    timeline = _compose(tmp_path, _line())
    catcher = _candidate(timeline, "catcher", "c1")
    assert catcher["reference_phase_deg"] is None
    assert catcher["shift_deg"] == 0.0
    assert catcher["input_phase_deg"][0] == 0.0
    assert catcher["input_phase_deg"][719] == 359.5
    assert all(len(pose) == 6 for pose in catcher["poses"])


def test_input_phases_wrap_through_zero(tmp_path):
    timeline = _compose(tmp_path, _line())
    gate = _candidate(timeline, "gate", "g1")
    # Master phase 330 deg is input phase (330 - (-30)) % 360 = 0.
    assert gate["input_phase_deg"][660] == 0.0
    assert gate["input_phase_deg"][661] == 0.5
    assert gate["input_phase_deg"][659] == 359.5


def test_applied_offsets_move_the_composition(tmp_path):
    timeline = _compose(tmp_path, _line(applied_offsets={"gate": 10}))
    assert timeline["applied_offsets"] == {"gate": 10}
    gate = _candidate(timeline, "gate", "g1")
    assert gate["shift_deg"] == -20.0
    assert gate["input_phase_deg"][0] == 20.0
    assert gate["reference_phase_deg"] == 30.0


def test_poses_match_the_geometry_kernel(tmp_path):
    timeline = _compose(tmp_path, _line())
    gate = _candidate(timeline, "gate", "g1")
    for index in (0, 99, 660):
        theta = gate["input_phase_deg"][index]
        skeleton = four_bar_skeleton(PARAMS, 1, theta)
        assert gate["poses"][index]["o2"] == [round(skeleton["o2"][0], 6), round(skeleton["o2"][1], 6)]
        assert gate["poses"][index]["a"] == [round(skeleton["a"][0], 6), round(skeleton["a"][1], 6)]
        assert gate["poses"][index]["p"] == [round(skeleton["p"][0], 6), round(skeleton["p"][1], 6)]
        assert gate["poses"][index]["carrier_corners"] == []


def test_carrier_corners_flow_from_the_collision_model(tmp_path):
    timeline = _compose(tmp_path, _line(collision={"gate": _model(carrier=(1.0, 0.5))}))
    gate = _candidate(timeline, "gate", "g1")
    assert len(gate["poses"][0]["carrier_corners"]) == 4
    skeleton = four_bar_skeleton(PARAMS, 1, gate["input_phase_deg"][0], carrier=(1.0, 0.5))
    expected = [[round(x, 6), round(y, 6)] for x, y in skeleton["carrier_corners"]]
    assert gate["poses"][0]["carrier_corners"] == expected
    catcher = _candidate(timeline, "catcher", "c1")
    assert catcher["poses"][0]["carrier_corners"] == []


def test_candidates_with_different_branches_report_separate_poses(tmp_path):
    timeline = _compose(tmp_path, _line(), gate_rows=[
        _row("g1", [30, 130, 250]),
        _row("g2", [30, 130, 250], branch_sign=-1),
    ])
    candidates = timeline["tasks"]["gate"]["candidates"]
    assert [item["candidate_id"] for item in candidates] == ["g1", "g2"]
    assert candidates[0]["poses"][0] != candidates[1]["poses"][0]
    assert candidates[1]["branch_sign"] == -1


def test_undefined_assembly_is_an_error(tmp_path):
    with pytest.raises(LineVerificationError, match="undefined") as excinfo:
        _compose(tmp_path, _line(), gate_rows=[_row("g1", [30, 130, 250], params=UNDEFINED_PARAMS)])
    assert "gate" in str(excinfo.value)
    assert "g1" in str(excinfo.value)


def test_missing_geometry_field_is_an_error(tmp_path):
    gate_row = _row("g1", [30, 130, 250])
    gate_row.pop("S_ratio")
    with pytest.raises(LineVerificationError, match="lacks 'S_ratio'"):
        _compose(tmp_path, _line(), gate_rows=[gate_row])


def test_zero_selected_candidates_is_an_error(tmp_path):
    with pytest.raises(LineVerificationError, match="zero candidates"):
        _compose(tmp_path, _line(), gate_rows=[])


@pytest.mark.parametrize("steps", [360, 72002])
def test_step_count_is_validated(tmp_path, steps):
    with pytest.raises(LineVerificationError, match="step count"):
        _compose(tmp_path, _line(), steps=steps)


def test_plan_without_a_line_is_an_error(tmp_path):
    _write_manifest(tmp_path, "gate", [_row("g1", [30, 130, 250])])
    (tmp_path / "run_plan.json").write_text(json.dumps({"task_set_id": "pair", "runs": []}), encoding="utf-8")
    with pytest.raises(LineVerificationError, match="no synchronization line"):
        compose_timeline(tmp_path)


def test_non_positive_crank_is_an_error(tmp_path):
    _write_manifest(tmp_path, "gate", [_row("g1", [30, 130, 250])], crank="negative")
    _write_manifest(tmp_path, "catcher", [_row("c1", [120, 220, 20])])
    _write_plan(tmp_path, _line())
    with pytest.raises(LineVerificationError, match="crank_direction"):
        compose_timeline(tmp_path)


def test_unknown_reference_target_is_an_error(tmp_path):
    line = _line(phase_reference={"gate": "ghost", "catcher": None})
    with pytest.raises(LineVerificationError, match="not one of its recorded run targets"):
        _compose(tmp_path, line)


def test_stray_offsets_are_rejected(tmp_path):
    with pytest.raises(LineVerificationError, match="non-participating"):
        _compose(tmp_path, _line(applied_offsets={"ghost": 10}))


def test_write_timeline_round_trips_compact_json(tmp_path):
    timeline = _compose(tmp_path, _line())
    path = write_timeline(tmp_path, timeline)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert '"candidate_id":"g1"' in text
    assert json.loads(text) == timeline


def test_cli_writes_the_timeline_artifact(tmp_path, capsys):
    timeline = _compose(tmp_path, _line(), steps=400)
    write_timeline(tmp_path, timeline)
    assert main(["timeline", str(tmp_path), "--steps", "400"]) == 0
    artifact = json.loads((tmp_path / "timeline.json").read_text(encoding="utf-8"))
    assert artifact["steps"] == 400
    assert artifact["sample_step_deg"] == 0.9
    out = capsys.readouterr().out
    assert "TIMELINE WRITTEN" in out
    assert "400 samples" in out
    assert "data-only" in out


def test_cli_rejects_out_of_range_steps(tmp_path, capsys):
    _compose(tmp_path, _line())
    assert main(["timeline", str(tmp_path), "--steps", "360"]) == 1
    assert "step count" in capsys.readouterr().err
