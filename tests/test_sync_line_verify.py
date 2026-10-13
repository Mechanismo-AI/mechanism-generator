import json
from pathlib import Path

import pytest

from mechanism_generator.omts.line_verify import LineVerificationError, verify_line


TASK_IDS = ["gate", "catcher"]
TARGETS = {"gate": ["hold", "release", "rest"], "catcher": ["grab", "carry", "park"]}


def _write_manifest(root: Path, task: str, candidates: list[dict], crank="positive", status="completed"):
    run_dir = root / f"results/task-{TASK_IDS.index(task) + 1:03d}" / "r25c" / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True)
    manifest = {
        "run_status": status,
        "targets": [{
            "label": task,
            "crank_direction": crank,
            "selected": [
                {"rank": rank, "candidate_id": row["id"],
                 **{f"phase_{i + 1}_deg": row["phases"][i] for i in range(3)}}
                for rank, row in enumerate(candidates, start=1)
            ],
        }],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_plan(root: Path, line: dict) -> Path:
    plan = {
        "task_set_id": "pair",
        "runs": [
            {"task_id": task, "target_ids": TARGETS[task], "output_root": f"results/task-{TASK_IDS.index(task) + 1:03d}"}
            for task in TASK_IDS
        ],
        "line": line,
    }
    (root / "run_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return root


def _line():
    # gate is anchored at hold; catcher is unanchored (raw phases are master phases).
    return {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": {"gate": "hold", "catcher": None},
        "events": [{
            "id": "handoff_window", "participants": [
                {"task": "gate", "target": "release"}, {"task": "catcher", "target": "grab"}],
            "window_deg": [100, 140], "tolerance_deg": 5, "mode": "hard",
        }],
        "relations": [{
            "id": "release_before_grab", "from": {"task": "gate", "target": "release"},
            "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
            "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard",
        }],
        "verification": "pending_timeline_verification",
    }


def test_passing_line(tmp_path):
    # gate anchored at hold: release = 130 - 30 = 100. catcher unanchored: grab = 120.
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [120, 220, 20]}])
    _write_plan(tmp_path, _line())
    result = verify_line(tmp_path)
    assert result["status"] == "verified"
    assert result["passing_combination_count"] == 1
    combo = result["combinations"][0]
    # lead from release (100) to grab (120) is 20 deg, inside [10, 45].
    assert combo["relations"][0]["achieved_lead_deg"] == pytest.approx(20.0)
    assert combo["events"][0]["participant_phases_deg"] == [100.0, 120.0]
    assert combo["events"][0]["status"] == "pass"
    assert (tmp_path / "line_result.json").exists()


def test_failing_relation_and_event(tmp_path):
    # release anchored 100, grab at 160: lead 60 > 45 fails; grab outside [95, 145].
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    _write_plan(tmp_path, _line())
    result = verify_line(tmp_path)
    assert result["status"] == "failed"
    combo = result["combinations"][0]
    assert combo["relations"][0]["status"] == "fail"
    assert combo["events"][0]["status"] == "fail"


def test_multiple_candidates_best_combination_passes(tmp_path):
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}, {"id": "g2", "phases": [30, 90, 240]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [120, 220, 20]}])
    _write_plan(tmp_path, _line())
    result = verify_line(tmp_path)
    assert result["combination_count"] == 2
    assert result["status"] == "verified"


def test_zero_selected_candidates_is_recorded_not_raised(tmp_path):
    _write_manifest(tmp_path, "gate", [])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [120, 220, 20]}])
    _write_plan(tmp_path, _line())
    result = verify_line(tmp_path)
    assert result["status"] == "no_candidates"
    assert "not treated as an error" in result["note"]


def test_missing_manifest_raises(tmp_path):
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_plan(tmp_path, _line())
    with pytest.raises(LineVerificationError, match="catcher"):
        verify_line(tmp_path)


def test_non_positive_direction_rejected(tmp_path):
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}], crank="negative")
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [120, 220, 20]}])
    _write_plan(tmp_path, _line())
    with pytest.raises(LineVerificationError, match="positive"):
        verify_line(tmp_path)


def test_plan_without_line_raises(tmp_path, task_document):
    from mechanism_generator.omts.adapter import write_plan
    plan_dir = tmp_path / "plan"
    write_plan(task_document, plan_dir)
    with pytest.raises(LineVerificationError, match="no synchronization line"):
        verify_line(plan_dir)


def test_fixed_offset_with_tolerance(tmp_path):
    line = _line()
    line["relations"] = [{
        "id": "fixed", "from": {"task": "gate", "target": "release"},
        "to": {"task": "catcher", "target": "grab"}, "type": "fixed_offset",
        "offset_deg": 60, "tolerance_deg": 5, "mode": "hard",
    }]
    line["events"] = []
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [120, 220, 20]}])
    _write_plan(tmp_path, line)
    result = verify_line(tmp_path)
    # release anchored 100, grab 120 -> lead 20; circular distance to 60 is 40 > 5 -> fail
    assert result["combinations"][0]["relations"][0]["status"] == "fail"
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    result = verify_line(tmp_path)
    # release anchored 100, grab 160 -> lead 60, exactly the offset -> pass
    assert result["combinations"][0]["relations"][0]["status"] == "pass"
    assert result["status"] == "verified"
