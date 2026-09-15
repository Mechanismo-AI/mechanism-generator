import copy
import json
import math
from pathlib import Path
import runpy

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
pytest.importorskip("matplotlib")
pytest.importorskip("pandas")

from mechanism_generator.engine import pose_seeds, r25b, r25c

ROOT = Path(__file__).resolve().parents[1]


def requested_case(name):
    report = json.loads((ROOT / "docs/pose-benchmark.json").read_text())
    case = next(item for item in report["cases"] if item["id"] == name)
    return {key: case[key] for key in ("id", "target_points", "target_orientations_deg", "tolerances")}


def pose_args(case, *extra):
    parser = r25c.build_parser()
    args = parser.parse_args(["--branches", "both", "--phase_mode", "ordered", *extra])
    args.target_orientations_deg = case["target_orientations_deg"]
    args.orientation_tolerances_deg = case["tolerances"]["orientation_deg"]
    r25c.validate_args(parser, args)
    return args


def reference_budget():
    return {"reference_candidate_id": "existing-reference", "reference_acquired_mean_error": .01,
            "reference_acquired_errors": [.01] * 3, "shared_mean_budget": .03,
            "shared_point_budgets": [.06] * 3}


@pytest.mark.parametrize("name", ["wide_sweep", "rotated_return", "offset_tool", "angle_wrap"])
def test_target_only_seeds_recover_all_original_probes(name):
    case = requested_case(name)
    args = pose_args(case)
    seeds, counts = pose_seeds.generate_pose_seeds(case["target_points"], case["target_orientations_deg"], args)
    assert len(seeds) == 6
    assert counts["attempted_samples"] == 4096
    assert counts["returned_seeds"] == 6
    evaluate = runpy.run_path(str(ROOT / "tools/benchmark_pose.py"))["score_candidate"]
    for seed in seeds:
        params = seed["parameters"]
        row = dict(zip(r25b.OUTPUT_PARAMETER_NAMES, params))
        row.update(candidate_id="geometric", branch_sign=seed["branch_sign"])
        row.update({f"phase_{i + 1}_rad": phase for i, phase in enumerate(seed["phases_rad"])})
        result = evaluate(row, case)
        assert result["pose_within_tolerances"]
        assert result["maximum_position_error"] < 1e-9
        assert result["maximum_orientation_error_deg"] < 1e-8
        assert result["grashof"] and result["crank_is_strictly_shortest"]
        gaps = np.remainder(np.roll(seed["phases_rad"], -1) - seed["phases_rad"], 2 * np.pi)
        assert gaps.sum() == pytest.approx(2 * np.pi)
        assert gaps.min() >= math.radians(.25)


def test_sampling_is_deterministic_and_does_not_consume_global_random_state():
    case = requested_case("wide_sweep")
    args = pose_args(case)
    np_before = np.random.get_state()
    torch_before = torch.random.get_rng_state().clone()
    first, first_counts = pose_seeds.generate_pose_seeds(case["target_points"], case["target_orientations_deg"], args)
    second, second_counts = pose_seeds.generate_pose_seeds(case["target_points"], case["target_orientations_deg"], args)
    assert first == second
    assert {key: value for key, value in first_counts.items() if not key.endswith("runtime_seconds")} == {
        key: value for key, value in second_counts.items() if not key.endswith("runtime_seconds")}
    np_after = np.random.get_state()
    assert np_before[0] == np_after[0] and np.array_equal(np_before[1], np_after[1])
    assert np_before[2:] == np_after[2:]
    assert torch.equal(torch_before, torch.random.get_rng_state())


def test_translation_preserves_seed_geometry_and_full_turns_are_equivalent():
    case = requested_case("rotated_return")
    args = pose_args(case)
    first, _ = pose_seeds.generate_pose_seeds(case["target_points"], case["target_orientations_deg"], args)
    shifted = np.asarray(case["target_points"]) + np.array([120., -33.])
    rotated = np.asarray(case["target_orientations_deg"]) + 720.
    second, _ = pose_seeds.generate_pose_seeds(shifted, rotated, args)
    assert [seed["sample_index"] for seed in first] == [seed["sample_index"] for seed in second]
    for before, after in zip(first, second):
        np.testing.assert_allclose(before["parameters"][:6], after["parameters"][:6], rtol=1e-10, atol=1e-10)
        np.testing.assert_allclose(np.array(before["parameters"])[6:8] + [120, -33], after["parameters"][6:8], atol=1e-10)
        np.testing.assert_allclose(before["phases_rad"], after["phases_rad"], atol=1e-10)


@pytest.mark.parametrize("knobs", [{"sample_count": 0}, {"max_seeds": 0}])
def test_zero_disables_all_sampling(knobs, monkeypatch):
    case = requested_case("wide_sweep")
    args = pose_args(case)
    def unexpected(*_):
        raise AssertionError("Disabled initialization sampled geometry")
    monkeypatch.setattr(pose_seeds, "_radical_inverse", unexpected)
    seeds, counts = pose_seeds.generate_pose_seeds(case["target_points"], case["target_orientations_deg"], args, **knobs)
    assert seeds == [] and not counts["enabled"] and counts["attempted_samples"] == 0


def test_repeated_and_collinear_dyads_return_empty_without_warnings():
    case = requested_case("wide_sweep")
    args = pose_args(case)
    with np.errstate(all="raise"):
        seeds, counts = pose_seeds.generate_pose_seeds([[0., 0.], [1., 0.], [2., 0.]], [0., 0., 0.], args)
    assert seeds == [] and counts["finite_dyads"] == 0
    seeds, _ = pose_seeds.generate_pose_seeds([[0., 0.]] * 3, [15., 15., 15.], args)
    assert seeds == []


@pytest.mark.parametrize("branch, sign", [("negative", -1), ("positive", 1)])
def test_seed_branch_filter_is_respected(branch, sign):
    case = requested_case("wide_sweep")
    args = pose_args(case, "--branches", branch)
    seeds, _ = pose_seeds.generate_pose_seeds(case["target_points"], case["target_orientations_deg"], args)
    assert all(seed["branch_sign"] == sign for seed in seeds)


@pytest.mark.parametrize("values", [[[0, 0]], [[0, 0], [1, 1], [float("nan"), 2]]])
def test_rejects_bad_pose_inputs(values):
    case = requested_case("wide_sweep")
    with pytest.raises(ValueError):
        pose_seeds.generate_pose_seeds(values, case["target_orientations_deg"], pose_args(case))


@pytest.mark.parametrize("options", [["--pose_dyad_samples", "-1"], ["--pose_dyad_seed_count", "7"], ["--pose_dyad_seed_count", "-1"]])
def test_cli_rejects_invalid_geometric_budgets(options):
    parser = r25c.build_parser()
    with pytest.raises(SystemExit):
        r25c.validate_args(parser, parser.parse_args(options))


@pytest.mark.parametrize("name", ["wide_sweep", "angle_wrap"])
def test_raw_seeds_and_refined_children_have_distinct_preserved_provenance(name, tmp_path):
    case = requested_case(name)
    args = pose_args(case, "--pose_dyad_seed_count", "2", "--adam_accuracy_steps", "2",
                     "--adam_tradeoff_steps", "2", "--lbfgs_steps", "0",
                     "--optimization_global_steps", "31", "--verification_steps", "61")
    target = torch.tensor(case["target_points"], dtype=torch.float64).flatten()
    lineage = {}
    budget = reference_budget()
    original_budget = copy.deepcopy(budget)
    exact, refined, diagnostic = r25c.run_pose_geometry(target, args, budget, tmp_path, lineage)
    assert budget == original_budget
    assert len(exact) == len(refined) == diagnostic["returned_seeds"] == 2
    r25b.apply_shared_candidate_qualification([*exact, *refined], args, budget)
    assert all(candidate["selection_eligible"] for candidate in exact)
    for seed, child in zip(exact, refined):
        assert seed["portfolio_origin"] == "pose_seed"
        assert seed["selection_reason"] == "preserved_geometric_seed"
        assert seed["model_role"] == child["model_role"] == "pose_geometry"
        assert seed["checkpoint_epoch"] is child["checkpoint_epoch"] is None
        assert seed["max_error"] < 1e-7
        assert child["portfolio_origin"] == "pose_refined"
        assert child["portfolio_parent_candidate_id"] == seed["candidate_id"]
        assert seed["generator_sample_index"] == child["generator_sample_index"]
        assert Path(seed["history_path"]).is_file()


def test_empty_refinement_cannot_remove_exact_geometric_candidates(tmp_path, monkeypatch):
    case = requested_case("wide_sweep")
    args = pose_args(case, "--pose_dyad_seed_count", "1")
    target = torch.tensor(case["target_points"], dtype=torch.float64).flatten()
    monkeypatch.setattr(r25c, "run_acquisitions", lambda *args: [])
    monkeypatch.setattr(r25c, "run_tradeoff", lambda *args: [])
    budget = reference_budget()
    exact, refined, diagnostic = r25c.run_pose_geometry(target, args, budget, tmp_path, {})
    r25b.apply_shared_candidate_qualification(exact, args, budget)
    assert refined == [] and diagnostic["refined_candidate_count"] == 0
    selected, fallback = r25b.select_diverse_candidates(exact, args)
    assert len(selected) == 1 and selected[0]["selection_eligible"] and not fallback


def test_actual_geometric_result_survives_local_bundle_without_private_metadata(tmp_path):
    from mechanism_generator.contributions import bundle as contributions
    case = requested_case("wide_sweep")
    args = pose_args(case, "--pose_dyad_seed_count", "1", "--adam_accuracy_steps", "0",
                     "--adam_tradeoff_steps", "0", "--lbfgs_steps", "0",
                     "--optimization_global_steps", "31", "--verification_steps", "61")
    target = torch.tensor(case["target_points"], dtype=torch.float64).flatten()
    budget = reference_budget()
    target_dir = tmp_path / "target"
    exact, refined, diagnostics = r25c.run_pose_geometry(target, args, budget, target_dir / "history", {})
    candidates = [*exact, *refined]
    r25b.apply_shared_candidate_qualification(candidates, args, budget)
    private = "PRIVATE-PROVENANCE-MUST-NOT-LEAVE"
    diagnostics["private_path"] = private
    for candidate in candidates:
        candidate["checkpoint_variant"] = private
        candidate["notes"] = private
    r25b.write_csv(target_dir / "all_candidates.csv", [r25b.flat_candidate_row(row) for row in candidates])
    task = {
        "directory": "target", "label": private, "target_values": target.tolist(),
        "target_orientations_deg": args.target_orientations_deg,
        "orientation_tolerances_deg": args.orientation_tolerances_deg,
        "orientation_frame": "coupler_A_to_B", "candidate_count": len(candidates),
        "selected_count": 1, "pose_initialization": diagnostics,
    }
    for field in ("path_acceptable", "selection_eligible", "engineering_acceptable", "orientation_acceptable", "pose_acceptable"):
        task[field + "_count"] = sum(row[field] for row in candidates)
    manifest = {
        "variant": "R2.5c", "run_status": "completed", "targets": [task],
        "arguments": {"pose_dyad_samples": 4096, "pose_dyad_seed_count": 1, "private": private},
        "pose_initialization_sha256": diagnostics["source_sha256"], "models": [],
    }
    (tmp_path / "run_manifest.json").write_text(json.dumps(manifest))
    bundle = contributions.build_bundle(tmp_path)
    assert bundle["schema_version"] == "0.3"
    assert private not in json.dumps(bundle)
    assert "checkpoint_variant" not in json.dumps(bundle)
    assert bundle["provenance"]["pose_initialization_sha256"] == diagnostics["source_sha256"]
    assert bundle["settings"] == {"pose_dyad_samples": 4096, "pose_dyad_seed_count": 1}
    assert bundle["task"][0]["pose_initialization"]["attempted_samples"] == 4096
    parent, child = bundle["candidates"][0]["items"]
    assert parent["portfolio_origin"] == "pose_seed" and child["portfolio_origin"] == "pose_refined"
    assert child["portfolio_parent_candidate_id"] == parent["candidate_id"]
    assert parent["model_role"] == child["model_role"] == "pose_geometry"
    assert parent["generator_sample_index"] == child["generator_sample_index"]
    assert parent["proposal_source"] == "three_pose_dyad_v1"
    for field in ("model_role", "proposal_source", "generator_sample_index"):
        altered = copy.deepcopy(bundle)
        altered["candidates"][0]["items"][0].pop(field)
        with pytest.raises(ValueError):
            contributions.validate_bundle(altered)
    altered = copy.deepcopy(bundle)
    altered["task"][0]["pose_initialization"]["returned_seeds"] = 2
    with pytest.raises(ValueError, match="budget|counts"):
        contributions.validate_bundle(altered)
    submission = {key: value for key, value in bundle.items() if key not in ("task", "candidates", "provenance", "settings")}
    submission.update(kind="submission", contributor={"pseudonym": "", "application": ""},
                      consent={"terms_version": "1", "license": "Apache-2.0", "rights_confirmed": True,
                               "public_sharing_and_training": True})
    contributions.validate_bundle(submission)
    assert "pose_initialization" not in json.dumps(submission)
