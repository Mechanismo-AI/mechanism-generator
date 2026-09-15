import copy
import csv
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
pytest.importorskip("matplotlib")
pytest.importorskip("pandas")
from safetensors.torch import save_file

from mechanism_generator.engine import r25b, r25c


def known_pose(phase_mode="ordered"):
    """Independent equal-radius circle intersections, then a world transform.

    For ground 6, crank 2, coupler/follower 5, the upper intersections at
    crank phases 0, pi/2, pi are (4,sqrt(21)),
    (3+sqrt(1.5),1+3sqrt(1.5)), and (2,3), respectively.
    """
    args = r25b.build_parser().parse_args(["--phase_mode", phase_mode])
    base_angle = .4
    a = [(2., 0.), (0., 2.), (-2., 0.)]
    b = [(4., math.sqrt(21)), (3 + math.sqrt(1.5), 1 + 3 * math.sqrt(1.5)), (2., 3.)]
    xy, orientations = [], []
    for (ax, ay), (bx, by) in zip(a, b):
        dx, dy = bx - ax, by - ay
        px, py = ax + .5 * dx - dy / 5, ay + .5 * dy + dx / 5
        xy.extend([math.cos(base_angle) * px - math.sin(base_angle) * py - 3,
                   math.sin(base_angle) * px + math.cos(base_angle) * py + 2])
        orientations.append(math.degrees(math.atan2(dy, dx) + base_angle))
    args.target_orientations_deg = orientations
    args.orientation_tolerances_deg = [1e-6, 2e-6, 3e-6]
    params = torch.tensor([6., 2., 5., 5., .5, 1., -3., 2., base_angle], dtype=torch.float64)
    phases = torch.tensor([0., math.pi / 2, math.pi], dtype=torch.float64)
    target = torch.tensor(xy, dtype=torch.float64)
    raw = r25b.encode_refinement_variables(params, phases, target, phase_mode, args)
    start = r25b.StartSpec("analytic", "path", "accuracy", "analytic-fixture", None,
                          -1., 0, raw, params, phases)
    return args, target, start


def optimized_fixture(start):
    return {"start": start, "raw_selected": start.raw_initial.clone(), "mean_budget": .01,
            "point_budget": [.01] * 3, "selection_reason": "analytic-fixture",
            "acquired_mean_error": 0., "acquired_errors": [0.] * 3, "history_path": "fixture.csv"}


@pytest.mark.parametrize("phase_mode", ["ordered", "unordered"])
def test_same_phases_match_independent_world_position_and_orientation(phase_mode):
    args, target, start = known_pose(phase_mode)
    result = r25b.evaluate_selected_candidate(optimized_fixture(start), target, args)
    assert result["physical_feasible"]
    assert result["max_error"] < 1e-9
    assert result["orientation_acceptable"]
    assert result["max_orientation_error_deg"] < 1e-8
    for index in range(1, 4):
        assert result[f"matched_orientation_{index}_deg"] == pytest.approx(args.target_orientations_deg[index - 1], abs=1e-8)
    # Reverse the first directed orientation without changing the positions or
    # phases: a position-perfect mechanism must fail the requested pose.
    args.target_orientations_deg[0] += 180
    reversed_result = r25b.evaluate_selected_candidate(optimized_fixture(start), target, args)
    assert reversed_result["max_error"] < 1e-9
    assert not reversed_result["orientation_acceptable"]
    assert reversed_result["orientation_error_1_deg"] == pytest.approx(180, abs=1e-8)


@pytest.mark.parametrize("orientation", [None, False, True])
def test_qualification_never_selects_position_only_match_for_pose_task(orientation):
    fixture_path = Path(__file__).resolve().parents[1] / "examples/results/three_point_candidate.json"
    candidate = json.loads(fixture_path.read_text())
    args = r25c.build_parser().parse_args(["--target_orientations_deg", "0", "45", "90"])
    r25c.validate_args(r25c.build_parser(), args)
    if orientation is not None:
        candidate["orientation_acceptable"] = orientation
    qualification = r25b.apply_shared_candidate_qualification([candidate], args)
    assert candidate["path_acceptable"]
    assert candidate["pose_acceptable"] is (orientation is True)
    assert candidate["selection_eligible"] is (orientation is True)
    assert qualification["selection_eligible_count"] == int(orientation is True)
    pool, fallback = r25b.final_selection_pool([candidate], args)
    assert len(pool) == int(orientation is True)
    assert not fallback
    if orientation is not True:
        assert candidate["qualification_level"] == "path_acceptable_but_orientation_failed"


@pytest.mark.parametrize("stage", ["accuracy", "tradeoff"])
def test_pose_objective_adds_finite_gradient_in_both_stages(stage):
    args, target, start = known_pose()
    args.target_orientations_deg = [value + 12 for value in args.target_orientations_deg]
    args.orientation_tolerances_deg = [1, 5, 20]
    raw = start.raw_initial.clone().requires_grad_()
    grid = torch.linspace(0, 2 * math.pi, 31, dtype=torch.float64)
    budgets = {} if stage == "accuracy" else {
        "mean_budget": torch.tensor(.01, dtype=torch.float64),
        "point_budget": torch.full((3,), .01, dtype=torch.float64),
    }

    def evaluate(value, options):
        return r25b.objective_terms(value, start.raw_initial, target, -1., "ordered",
                                   r25b.PROFILES["accuracy"], stage, options, grid, **budgets)

    pose_loss, metrics = evaluate(raw, args)
    position_args = copy.deepcopy(args)
    position_args.target_orientations_deg = None
    position_args.orientation_tolerances_deg = None
    position_loss, position_metrics = evaluate(raw, position_args)
    assert "orientation_feasible" not in position_metrics
    assert not metrics["orientation_feasible"].item()
    assert pose_loss > position_loss
    angular_difference = pose_loss - position_loss
    angular_difference.backward()
    assert torch.isfinite(raw.grad).all()
    assert torch.linalg.vector_norm(raw.grad).item() > 0
    # Validate the new differentiable contribution independently of the
    # pre-existing physical and transmission terms using finite differences.
    index = 8  # World-frame base rotation.
    step = 1e-6
    plus, minus = raw.detach().clone(), raw.detach().clone()
    plus[index] += step
    minus[index] -= step
    plus_delta = evaluate(plus, args)[0] - evaluate(plus, position_args)[0]
    minus_delta = evaluate(minus, args)[0] - evaluate(minus, position_args)[0]
    finite_difference = ((plus_delta - minus_delta) / (2 * step)).item()
    assert raw.grad[index].item() == pytest.approx(finite_difference, rel=2e-5, abs=1e-7)


def test_acquisition_keeps_pose_match_when_position_improvement_breaks_angle(monkeypatch):
    args, target, start = known_pose()
    target = target + torch.tensor([.05, 0.] * 3, dtype=torch.float64)
    args.adam_accuracy_steps = 8
    args.adam_lr = .001
    args.optimization_global_steps = 31
    args.history_interval = 1
    start.raw_initial = r25b.encode_refinement_variables(start.initial_params, start.initial_phases, target, "ordered", args)
    monkeypatch.setitem(r25b.PROFILES, "accuracy", replace(r25b.PROFILES["accuracy"],
                        stage_a_target_transmission_weight=0., stage_a_global_transmission_weight=0.))
    result = r25b.acquire_start_path(start, target, args)
    assert result["acquired_physical"]
    assert result["acquired_orientation_acceptable"]
    # A real Adam step improves the position-only fit but leaves the very
    # narrow requested angular tolerance; it must not replace the pose match.
    better_position_only = [row for row in result["history"]
                            if row["mean_error"] < result["acquired_mean_error"] - 1e-5
                            and not row["orientation_acceptable"]]
    assert better_position_only
    params, phases = r25b.decode_refinement_variables(result["raw_acquired"], target, "ordered", args)
    gaps = torch.remainder(torch.roll(phases, -1) - phases, 2 * math.pi)
    assert (gaps > 0).all()
    assert gaps.sum().item() == pytest.approx(2 * math.pi)
    torch.testing.assert_close(params, start.initial_params)


def test_shared_reference_uses_orientation_compatible_acquisition():
    args, _, start = known_pose()
    wrong = {"start": replace(start, candidate_id="better-position-wrong-angle"),
             "acquired_physical": True, "acquired_orientation_acceptable": False,
             "acquired_mean_error": .001, "acquired_max_error": .001,
             "acquired_errors": torch.full((3,), .001), "acquired_pose_key": (1, .0001, .001)}
    good = {"start": replace(start, candidate_id="valid-pose"),
            "acquired_physical": True, "acquired_orientation_acceptable": True,
            "acquired_mean_error": .02, "acquired_max_error": .03,
            "acquired_errors": torch.tensor([.01, .02, .03]), "acquired_pose_key": (0, .02, .03)}
    reference = r25b.build_shared_path_reference([wrong, good], args)
    assert reference["reference_candidate_id"] == "valid-pose"
    assert reference["reference_acquired_mean_error"] == .02


@pytest.mark.parametrize("arguments, message", [
    (["--orientation_tolerances_deg", "5", "5", "5"], "require"),
    (["--target_orientations_deg", "0", "nan", "0"], "finite"),
    (["--target_orientations_deg", "0", "0", "0", "--orientation_tolerances_deg", "0", "5", "5"], "between"),
    (["--target_orientations_deg", "0", "0", "0", "--orientation_tolerances_deg", "5", "180", "5"], "between"),
    (["--target_orientations_deg", "0", "0", "0", "--orientation_tolerances_deg", "5", "nan", "5"], "finite"),
])
def test_cli_rejects_invalid_orientation_request(arguments, message, capsys):
    parser = r25c.build_parser()
    args = parser.parse_args(arguments)
    with pytest.raises(SystemExit) as exc:
        r25c.validate_args(parser, args)
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


def test_cli_defaults_tolerance_and_rejects_multiple_pose_tasks(tmp_path):
    targets_file = tmp_path / "targets.csv"
    targets_file.write_text("x1,y1,x2,y2,x3,y3\n-6,2,-2,6,0,3\n-5,2,-1,6,1,3\n")
    parser = r25c.build_parser()
    args = parser.parse_args(["--targets_file", str(targets_file), "--target_orientations_deg", "0", "90", "180"])
    r25c.validate_args(parser, args)
    assert args.orientation_tolerances_deg == [5.] * 3
    with pytest.raises(ValueError, match="one target triple"):
        r25b.collect_targets(args)


def test_cli_normalizes_full_turns_before_refinement_dtype_conversion():
    parser = r25c.build_parser()
    args = parser.parse_args(["--target_orientations_deg", "3600000001", "1e308", "730", "--dtype", "float32"])
    r25c.validate_args(parser, args)
    assert args.target_orientations_deg == [1., math.remainder(1e308, 360.), 10.]
    assert torch.isfinite(torch.tensor(args.target_orientations_deg, dtype=torch.float32)).all()


def test_tiny_pose_run_records_same_phase_errors_and_qualification(tmp_path):
    torch.manual_seed(42)
    path = tmp_path / "synthetic.safetensors"
    save_file(r25b.MechanismNN().state_dict(), str(path), metadata={"variant": "test-fixture", "state_epoch": "0"})
    output = tmp_path / "out"
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", MPLCONFIGDIR=str(tmp_path / "mpl"))
    arguments = [sys.executable, "-m", "mechanism_generator.engine.r25c", "--balanced_model", str(path), "--model_roles", "balanced",
                 "--targets", "-6", "2", "-2", "6", ".5", "3.5", "--target_orientations_deg", "0", "45", "90",
                 "--orientation_tolerances_deg", "1", "5", "10", "--phase_mode", "ordered",
                 "--profile_matrix", "paired", "--branches", "negative", "--perturbations_per_model", "0",
                 "--adam_accuracy_steps", "2", "--adam_tradeoff_steps", "2", "--lbfgs_steps", "0",
                 "--portfolio_fixed_seed_count", "0", "--portfolio_release_seed_count", "0", "--portfolio_skip_release",
                 "--portfolio_guarantee_fixed_count", "0", "--seed_phase_steps", "31", "--optimization_global_steps", "31",
                 "--verification_steps", "61", "--device", "cpu", "--headless", "--no_plots", "--no_contribution_bundle",
                 "--output_root", str(output)]
    result = subprocess.run(arguments, capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr
    manifests = list(output.rglob("run_manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    task = manifest["targets"][0]
    assert manifest["run_status"] == "completed"
    assert task["target_orientations_deg"] == [0., 45., 90.]
    assert task["orientation_tolerances_deg"] == [1., 5., 10.]
    assert task["orientation_frame"] == "coupler_A_to_B"
    root_csv = manifests[0].parent / task["directory"] / "all_candidates.csv"
    with root_csv.open(newline="") as stream:
        candidates = list(csv.DictReader(stream))
    assert candidates
    for row in candidates:
        assert row["orientation_required"] == "True"
        assert row["orientation_frame"] == "coupler_A_to_B"
        for index, tolerance in enumerate([1., 5., 10.], 1):
            assert float(row[f"orientation_tolerance_{index}_deg"]) == tolerance
            delta = math.radians(float(row[f"matched_orientation_{index}_deg"]) - float(row[f"target_orientation_{index}_deg"]))
            independent_error = abs(math.degrees(math.atan2(math.sin(delta), math.cos(delta))))
            assert float(row[f"orientation_error_{index}_deg"]) == pytest.approx(independent_error, abs=1e-8)
        if row["selection_eligible"] == "True":
            assert row["orientation_acceptable"] == row["path_acceptable"] == row["pose_acceptable"] == "True"
        if row["orientation_acceptable"] == "False":
            assert row["selection_eligible"] == "False"
    assert task["orientation_acceptable_count"] == sum(row["orientation_acceptable"] == "True" for row in candidates)
    assert task["pose_acceptable_count"] == sum(row["pose_acceptable"] == "True" for row in candidates)
