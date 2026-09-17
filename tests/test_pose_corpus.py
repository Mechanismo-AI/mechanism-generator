import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")
spec = importlib.util.spec_from_file_location("pose_corpus", Path(__file__).parents[1] / "tools" / "pose_corpus.py")
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)


def test_generation_is_deterministic_and_split_tasks_are_distinct():
    first, second = corpus.corpus_files(), corpus.corpus_files()
    assert first == second
    development = json.loads(first["development.tasks.json"])["cases"]
    evaluation = json.loads(first["evaluation.tasks.json"])["cases"]
    assert len(development) == len(evaluation) == 8
    assert {case["case_sha256"] for case in development}.isdisjoint(case["case_sha256"] for case in evaluation)
    assert {tuple(np.asarray(case["target_points"]).ravel()) for case in development}.isdisjoint(tuple(np.asarray(case["target_points"]).ravel()) for case in evaluation)


@pytest.mark.parametrize("split", corpus.SPLIT_SEEDS)
def test_all_witnesses_independently_satisfy_declared_geometry_and_pose(split):
    cases, witnesses, _ = corpus.generate_split(split)
    assert [reference["branch_sign"] for reference in witnesses].count(1) == 4
    assert [reference["branch_sign"] for reference in witnesses].count(-1) == 4
    for case, witness in zip(cases, witnesses):
        parameters = [witness["parameters"][name] for name in corpus.benchmark.PARAMETER_NAMES]
        row = {**witness["parameters"], "candidate_id": "reference-only", "branch_sign": witness["branch_sign"],
               **{f"phase_{index}_rad": phase for index, phase in enumerate(witness["phases_rad"], 1)}}
        score = corpus.benchmark.score_candidate(row, case)
        assert score["pose_within_tolerances"] and not score["engine_selection_eligible"]
        assert score["mean_position_error"] < 1e-9 and score["maximum_orientation_error_deg"] < 1e-8
        assert score["grashof"] and score["crank_is_strictly_shortest"]
        assert score["global_minimum_transmission_deg"] >= 20
        assert corpus.in_design_bounds(parameters, case["target_points"])
        points = np.asarray(case["target_points"])
        assert np.all((-7 < points[:, 0]) & (points[:, 0] < 1))
        assert np.all((1 < points[:, 1]) & (points[:, 1] < 7))
        gaps = np.diff(np.r_[witness["phases_rad"], witness["phases_rad"][0] + 2 * np.pi])
        assert np.all(gaps > 0)


def test_runner_loads_no_reference_files_and_checks_case_hashes(tmp_path):
    corpus.write_corpus(tmp_path)
    for path in tmp_path.glob("*.references.json"):
        path.unlink()
    cases, manifest, _ = corpus.load_tasks(tmp_path, "development")
    assert len(cases) == 8 and "reference" not in cases[0]
    tasks = tmp_path / "development.tasks.json"
    original = json.loads(tasks.read_text())
    original["cases"][0]["target_points"][0][0] += .1
    tasks.write_text(json.dumps(original))
    with pytest.raises(ValueError, match="frozen SHA256"):
        corpus.load_tasks(tmp_path, "development")


def test_frozen_corpus_is_never_silently_replaced(tmp_path):
    corpus.write_corpus(tmp_path)
    (tmp_path / "development.tasks.json").write_text("changed")
    with pytest.raises(ValueError, match="frozen corpus"):
        corpus.write_corpus(tmp_path)


def test_solver_gets_only_requested_poses_and_explicit_initializer_controls(tmp_path):
    case = corpus.generate_split("development")[0][0]
    args = SimpleNamespace(models_directory=tmp_path, engine_python=Path("separate-python"), budget="quick", seed=101,
                           initializer_samples=None, initializer_seeds=None)
    command = corpus.solver_command(case, args, tmp_path / "out")
    assert command[0] == "separate-python"
    assert "--target_orientations_deg" in command and "--orientation_tolerances_deg" in command
    assert "--pose_dyad_samples" not in command and "--pose_dyad_seed_count" not in command
    assert not any("reference" in argument for argument in command)
    args.initializer_samples, args.initializer_seeds = 4096, 6
    enhanced = corpus.solver_command(case, args, tmp_path / "out")
    assert enhanced[:len(command)] == command
    assert enhanced[-4:] == ["--pose_dyad_samples", "4096", "--pose_dyad_seed_count", "6"]
    args.tolerance_samples = 65536
    assert corpus.solver_command(case, args, tmp_path / "out")[-2:] == ["--pose_tolerance_samples", "65536"]


def test_failed_and_empty_runs_remain_in_denominator():
    successful = {"status": "completed", "wall_runtime_seconds": 1.,
                  "selected": {"pose_match_and_engine_eligible_count": 1, "candidate_count": 1},
                  "all_candidates_diagnostic": {"candidate_count": 6}}
    empty = copy.deepcopy(successful)
    empty["selected"] = {"pose_match_and_engine_eligible_count": 0, "candidate_count": 0}
    failed = {"status": "failed", "wall_runtime_seconds": 2.}
    summary = corpus.summarize_runs([successful, empty, failed], 8)
    assert summary["selected_pose_success_fraction"] == 1 / 8
    assert summary["failed_cases"] == 1 and summary["completed_cases"] == 2


def minimal_report():
    return {
        "corpus_version": "v1", "corpus_manifest_sha256": "manifest", "task_file_sha256": "tasks", "case_hashes": [{"id": "case-1", "sha256": "casehash"}],
        "split": "development", "seed": 101, "optimizer_budget_settings": {"steps": 10},
        "success_thresholds": corpus.PROTOCOL["tolerances"], "common_configuration": {}, "evaluator_sha256": "evaluator",
        "run_status": "completed", "engine_label": "baseline", "summary": {}, "requested_initializer_settings": {},
        "requested_model_identity": [{"role": "balanced", "sha256": "same-weights"}],
        "runs": [{"case_id": "case-1", "case_sha256": "casehash", "status": "completed", "model_identity": [{"sha256": "same-weights"}], "engine_identity": {"engine_sha256": "baseline-code"}}],
    }


@pytest.mark.parametrize("field", ["task_file_sha256", "seed", "optimizer_budget_settings", "success_thresholds"])
def test_comparison_refuses_changed_tasks_thresholds_or_budgets(field):
    baseline = minimal_report()
    candidate = copy.deepcopy(baseline)
    candidate[field] = "changed"
    with pytest.raises(ValueError, match=field):
        corpus.compare_reports(baseline, candidate)


def test_comparison_reports_extra_initializer_compute_separately():
    baseline = minimal_report()
    candidate = copy.deepcopy(baseline)
    candidate["requested_initializer_settings"] = {"samples": 4096, "seeds": 6}
    candidate["runs"][0]["engine_identity"] = {"engine_sha256": "new-code"}
    comparison = corpus.compare_reports(baseline, candidate)
    assert comparison["configured_optimizer_budgets_equal"]
    assert not comparison["equal_total_compute_claimed"]
    assert comparison["candidate"]["initializer_settings"] != comparison["baseline"]["initializer_settings"]


def test_comparison_rejects_missing_and_repeated_cases():
    baseline = minimal_report()
    candidate = copy.deepcopy(baseline)
    candidate["runs"] = []
    with pytest.raises(ValueError, match="exactly once"):
        corpus.compare_reports(baseline, candidate)
    candidate["runs"] = baseline["runs"] * 2
    with pytest.raises(ValueError, match="exactly once"):
        corpus.compare_reports(baseline, candidate)


def test_comparison_retains_initializer_counts_and_times():
    baseline = minimal_report()
    candidate = copy.deepcopy(baseline)
    candidate["runs"][0]["initializer_diagnostics"] = {"attempted_samples": 4096, "returned_seeds": 6, "generation_runtime_seconds": .01}
    comparison = corpus.compare_reports(baseline, candidate)
    assert comparison["baseline"]["initializer_diagnostic_totals"] is None
    assert comparison["candidate"]["initializer_diagnostic_totals"]["attempted_samples"] == 4096
    assert comparison["candidate"]["initializer_diagnostic_totals"]["returned_seeds"] == 6
