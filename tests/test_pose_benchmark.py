"""Check the independent benchmark's geometry and fair paired comparisons."""
import importlib.util
import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
spec = importlib.util.spec_from_file_location("benchmark_pose", Path(__file__).parents[1] / "tools" / "benchmark_pose.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def reference_row(case):
    return {**case["reference"]["parameters"], "branch_sign": case["reference"]["branch_sign"],
            "candidate_id": "independent-reference", "selection_eligible": "False",
            **{f"phase_{i}_rad": value for i, value in enumerate(case["reference"]["phases_rad"], 1)}}


@pytest.mark.parametrize("case", benchmark.make_cases(), ids=lambda case: case["id"])
def test_reference_geometry_closes_links_and_meets_pose(case):
    reference = case["reference"]
    parameters = [reference["parameters"][name] for name in benchmark.PARAMETER_NAMES]
    geometry = benchmark.analytic_geometry(parameters, reference["phases_rad"], reference["branch_sign"])
    for first, second, expected in (("o2", "a", parameters[1]), ("a", "b", parameters[2]), ("b", "o4", parameters[3])):
        np.testing.assert_allclose(np.linalg.norm(geometry[first] - geometry[second], axis=1), expected, atol=1e-12)
    score = benchmark.score_candidate(reference_row(case), case)
    assert score["pose_within_tolerances"]
    assert not score["engine_selection_eligible"]  # A witness is not a discovered engine result.
    assert score["mean_position_error"] < 1e-12
    assert score["maximum_orientation_error_deg"] < 1e-12
    assert reference["full_cycle_assembly"] and reference["grashof"] and reference["crank_is_strictly_shortest"]
    assert reference["global_minimum_transmission_deg"] > 15.
    assert case["within_historical_position_box"]


def test_circular_residual_wraps_and_preserves_direction():
    np.testing.assert_allclose(benchmark.circular_error_deg([-179, 179, 180, 1], [179, -179, 0, 361]), [2, -2, -180, 0])


def test_position_success_does_not_hide_wrong_orientation():
    case = benchmark.make_cases()[0]
    case["target_orientations_deg"] = [angle + 30 for angle in case["target_orientations_deg"]]
    row = reference_row(case)
    row.update({"mean_error": "0", "maximum_orientation_error_deg": "0", "pose_acceptable": "True"})
    score = benchmark.score_candidate(row, case)
    assert score["mean_position_error"] < 1e-12
    assert score["maximum_orientation_error_deg"] == pytest.approx(30)
    assert not score["pose_within_tolerances"]


def test_invalid_circle_is_rejected_without_nonfinite_json():
    case = benchmark.make_cases()[0]
    row = reference_row(case)
    row["l3"] = .001
    score = benchmark.score_candidate(row, case)
    assert not score["target_assembly"] and not score["pose_within_tolerances"]
    assert score["mean_position_error"] is None
    json.dumps(score, allow_nan=False)


def test_global_transmission_is_not_a_sparse_grid_estimate():
    parameters = [6, 2, 5, 4, .45, 1, -3, -1, .15]
    result = benchmark.full_cycle_checks(parameters)
    dense = benchmark.analytic_geometry(parameters, np.linspace(0, 2 * np.pi, 10001), 1)
    assert result["global_minimum_transmission_deg"] == pytest.approx(dense["transmission_deg"].min(), abs=1e-9)
    parameters[2] = 2
    assert not benchmark.full_cycle_checks(parameters)["full_cycle_assembly"]


def test_paired_commands_differ_only_by_requested_orientation():
    case = benchmark.make_cases()[0]
    args = (Path("models"), Path("output"), "quick", 101)
    position = benchmark.build_command(case, "position", *args)
    pose = benchmark.build_command(case, "pose", *args)
    assert pose[:len(position)] == position
    assert pose[len(position)] == "--target_orientations_deg"
    assert "--orientation_tolerances_deg" in pose[len(position):]
    for name in benchmark.BUDGETS["quick"]:
        assert position.count(f"--{name}") == 1


def test_empty_and_failed_searches_remain_in_coverage_denominator():
    runs = [
        {"mode": "position", "status": "completed", "wall_runtime_seconds": 1., "selected": {"pose_match_and_engine_eligible_count": 0}},
        {"mode": "pose", "status": "completed", "wall_runtime_seconds": 2., "selected": {"pose_match_and_engine_eligible_count": 1}},
        {"mode": "pose", "status": "failed", "wall_runtime_seconds": 3.},
    ]
    result = benchmark.coverage(runs, 4)
    assert result["position"]["selected_pose_success_fraction"] == 0
    assert result["pose"]["selected_pose_success_fraction"] == .25
    assert result["pose"]["completed_cases"] == 1
    assert result["pose"]["total_wall_runtime_seconds"] == 5


def test_reference_pose_matches_do_not_count_as_engine_eligible_search_success():
    case = benchmark.make_cases()[0]
    summary = benchmark.summarize_scores([benchmark.score_candidate(reference_row(case), case)])
    assert summary["pose_match_count"] == 1
    assert summary["pose_match_and_engine_eligible_count"] == 0


def test_generate_only_writes_reproducible_cases_without_models(tmp_path):
    assert benchmark.main(["--output", str(tmp_path), "--generate-only"]) == 0
    report = json.loads((tmp_path / "benchmark.json").read_text())
    assert len(report["cases"]) == 4
    assert report["runs"] == []
    assert "Reference mechanisms" in " ".join(report["limitations"])
