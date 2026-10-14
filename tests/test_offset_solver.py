import json
from pathlib import Path

import pytest

from mechanism_generator.omts.line_verify import LineVerificationError, solve_offsets, verify_line


TASK_IDS = ["gate", "catcher"]
TARGETS = {
    "gate": ["hold", "release", "rest"],
    "catcher": ["grab", "carry", "park"],
}


def _write_manifest(root: Path, task: str, candidates: list[dict], crank="positive", status="completed"):
    run_dir = root / f"results/task-{TASK_IDS.index(task) + 1:03d}" / "r25c" / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
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


def _line(window=(100, 140), tolerance=5, lead=(10, 45)):
    # gate is anchored at hold; catcher is unanchored (raw phases are master phases).
    return {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": {"gate": "hold", "catcher": None},
        "events": [{
            "id": "handoff_window", "participants": [
                {"task": "gate", "target": "release"}, {"task": "catcher", "target": "grab"}],
            "window_deg": list(window), "tolerance_deg": tolerance, "mode": "hard",
        }],
        "relations": [{
            "id": "release_before_grab", "from": {"task": "gate", "target": "release"},
            "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
            "min_lead_deg": lead[0], "max_lead_deg": lead[1], "mode": "hard",
        }],
        "verification": "pending_timeline_verification",
    }


def _failing_pair(tmp_path: Path):
    # gate anchored at hold: release = 100. catcher unanchored: grab = 160
    # (window [100,140]+/-5 and lead [10,45] both fail at zero offsets).
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    return _write_plan(tmp_path, _line())


def test_solver_recommends_offsets_that_verify_end_to_end(tmp_path):
    plan_dir = _failing_pair(tmp_path)
    proposal = solve_offsets(plan_dir, step_deg=1.0, top=5)
    assert proposal["status"] == "solved"
    assert proposal["best_passing_count"] == 1
    assert proposal["combination_count"] == 1
    assert (tmp_path / "offsets_proposal.json").exists()
    # The solver never writes a verdict.
    assert not (tmp_path / "line_result.json").exists()
    # Top recommendation composes to a valid line: declare it and verify.
    offsets = proposal["recommendations"][0]["offsets"]
    line = _line()
    line["applied_offsets"] = offsets
    _write_plan(plan_dir, line)
    result = verify_line(plan_dir)
    assert result["status"] == "verified"
    assert result["passing_combination_count"] == 1


def test_joint_solution_exists_where_single_task_probes_are_empty(tmp_path):
    # Open question 5: this line has joint-only solutions. Sweeping either task
    # alone cannot satisfy the window event (the other participant is fixed
    # outside [30,70]+/-5), but moving both tasks together can.
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    _write_plan(tmp_path, _line(window=(30, 70), tolerance=5))
    probe = verify_line(tmp_path, probe=True, probe_step_deg=5.0)
    assert probe["status"] == "failed"
    by_task = {entry["task"]: entry for entry in probe["anchor_probe"]["tasks"]}
    assert by_task["gate"]["feasible_intervals_deg"] == []
    assert by_task["catcher"]["feasible_intervals_deg"] == []
    proposal = solve_offsets(tmp_path, step_deg=1.0, top=5)
    assert proposal["status"] == "solved"
    assert proposal["best_passing_count"] == 1
    offsets = proposal["recommendations"][0]["offsets"]
    # Both tasks must move: no zero-offset recommendation can exist here.
    assert offsets["gate"] != 0.0 and offsets["catcher"] != 0.0
    line = _line(window=(30, 70), tolerance=5)
    line["applied_offsets"] = offsets
    _write_plan(tmp_path, line)
    assert verify_line(tmp_path)["status"] == "verified"


def test_infeasible_line_is_reported_without_recommendations(tmp_path):
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    # Windows force grab - release into [-65, -55]; ordering wants [-50, -15].
    _write_plan(tmp_path, _line(window=(350, 355), tolerance=0))
    proposal = solve_offsets(tmp_path)
    assert proposal["status"] == "infeasible"
    assert proposal["best_passing_count"] == 0
    assert "recommendations" not in proposal
    assert "applied_offsets_example" not in proposal


def test_zero_selected_candidates_is_recorded_not_raised(tmp_path):
    _write_manifest(tmp_path, "gate", [])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    _write_plan(tmp_path, _line())
    proposal = solve_offsets(tmp_path)
    assert proposal["status"] == "no_candidates"
    assert "not treated as an error" in proposal["note"]
    assert (tmp_path / "offsets_proposal.json").exists()


def test_recommendations_are_absolute_and_replace_declared_offsets(tmp_path):
    # A declared catcher offset of 325 must not shift the search: recommendations
    # compose from raw phases and replace the declared block wholesale.
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [160, 220, 20]}])
    line = _line()
    line["applied_offsets"] = {"catcher": 325.0}
    _write_plan(tmp_path, line)
    proposal = solve_offsets(tmp_path, step_deg=1.0, top=1)
    assert proposal["status"] == "solved"
    assert "replace" in proposal["note"]
    example = proposal["applied_offsets_example"]
    # Document-ready, unit-quantified entries for every nonzero offset.
    assert set(example) == {task for task, deg in proposal["recommendations"][0]["offsets"].items()
                            if deg != 0.0}
    assert all(set(quantity) == {"phase"} for quantity in example.values())
    # The example's degrees are exactly the top recommendation.
    top = proposal["recommendations"][0]["offsets"]
    for task, quantity in example.items():
        assert quantity["phase"] == pytest.approx(top[task])
    # Declared offsets are still composed by the verifier (unchanged behavior).
    assert verify_line(tmp_path)["status"] == "verified"


def test_recommendations_are_ranked_by_margin_then_offsets(tmp_path):
    plan_dir = _failing_pair(tmp_path)
    proposal = solve_offsets(plan_dir, step_deg=1.0, top=10)
    margins = [entry["margin_deg"] for entry in proposal["recommendations"]]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] >= margins[-1]
    assert all(entry["passing_combinations"] == proposal["best_passing_count"]
               for entry in proposal["recommendations"])


def test_more_than_two_participating_tasks_are_rejected(tmp_path):
    line = {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": {"gate": "hold", "catcher": None, "press": None},
        "events": [{
            "id": "three_way", "participants": [
                {"task": "gate", "target": "release"},
                {"task": "catcher", "target": "grab"},
                {"task": "press", "target": "tap"}],
            "window_deg": [10, 20], "tolerance_deg": 0, "mode": "hard",
        }],
        "relations": [],
    }
    plan = {"task_set_id": "triple", "runs": [], "line": line}
    (tmp_path / "run_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(LineVerificationError, match="two participating tasks"):
        solve_offsets(tmp_path)


def test_invalid_step_is_rejected(tmp_path):
    plan_dir = _failing_pair(tmp_path)
    for step in (0.0, -1.0, 361.0):
        with pytest.raises(LineVerificationError, match="Offset step"):
            solve_offsets(plan_dir, step_deg=step)


def test_cli_proposes_offsets_and_stays_a_proposal(tmp_path, capsys):
    from mechanism_generator.omts.cli import main
    plan_dir = _failing_pair(tmp_path)
    code = main(["propose-offsets", str(plan_dir), "--top", "3"])
    out = capsys.readouterr().out
    assert code == 0
    assert "OFFSETS PROPOSAL" in out
    assert "Proposal only" in out
    code = main(["propose-offsets", str(plan_dir), "--step-deg", "0"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Offset step" in captured.err
