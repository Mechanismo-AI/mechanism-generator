import copy
import json
import math

import pytest

torch = pytest.importorskip("torch")
from mechanism_generator.engine import r25b, r25c, pose_seeds
from mechanism_generator.omts.adapter import prepare_plan


@pytest.mark.parametrize("direction,sign", [("positive", 1), ("negative", -1)])
def test_ordered_physical_phases_roundtrip_and_gradients(direction, sign):
    args = r25c.build_parser().parse_args(["--crank_direction", direction])
    target = torch.tensor([-6., 2., -2., 6., .5, 3.5], dtype=torch.float64)
    params = torch.tensor([6., 2., 5., 4., .5, 1., -3., 2., .4], dtype=torch.float64)
    phases = torch.remainder(sign * torch.tensor([5.5, .4, 2.], dtype=torch.float64), 2*math.pi)
    raw = r25b.encode_refinement_variables(params, phases, target, "ordered", args).requires_grad_()
    decoded, result = r25b.decode_refinement_variables(raw, target, "ordered", args)
    torch.testing.assert_close(decoded, params)
    torch.testing.assert_close(result, phases)
    gaps = torch.remainder(sign * (torch.roll(result, -1) - result), 2*math.pi)
    assert gaps.sum().item() == pytest.approx(2*math.pi)
    result.sin().sum().backward()
    assert torch.isfinite(raw.grad).all()


@pytest.mark.parametrize("failure", [False, True])
def test_either_runs_both_and_preserves_failure(tmp_path, monkeypatch, failure):
    args = r25c.build_parser().parse_args(["--crank_direction", "either", "--output_root", str(tmp_path)])
    calls = []
    def search(child):
        calls.append(copy.deepcopy(child))
        if failure and child.crank_direction == "positive":
            raise RuntimeError("private path")
        return 0
    monkeypatch.setattr(r25c, "run_search", search)
    assert r25c.run_either_direction(args) == int(failure)
    assert [a.crank_direction for a in calls] == ["positive", "negative"]
    assert all(a.adam_accuracy_steps == args.adam_accuracy_steps for a in calls)
    assert args.crank_direction == "either"
    index = json.loads(next(tmp_path.rglob("direction_index.json")).read_text())
    assert index["run_status"] == ("partial" if failure else "completed")
    assert index["directions"]["negative"]["run_status"] == "completed"
    assert "private path" not in json.dumps(index)


@pytest.mark.parametrize("direction", ["positive", "negative", "either"])
def test_omts_maps_direction_without_reordering_targets(task_document, direction):
    task_document["tasks"][0]["motion"]["cycle"] = {"direction": direction}
    run = prepare_plan(task_document)["runs"][0]
    args = run["arguments"]
    assert args[args.index("--crank_direction") + 1] == direction
    assert run["target_ids"] == ["T1", "T2", "T3"]


def test_negative_pose_seeds_retain_requested_pose_order():
    from test_pose_seeds import requested_case, pose_args
    case = requested_case("wide_sweep")
    points = [case["target_points"][i] for i in (0, 2, 1)]
    angles = [case["target_orientations_deg"][i] for i in (0, 2, 1)]
    args = pose_args(case, "--crank_direction", "negative")
    seeds, _ = pose_seeds.generate_pose_seeds(points, angles, args)
    assert seeds
    for seed in seeds:
        phases = torch.tensor(seed["phases_rad"], dtype=torch.float64)
        gaps = torch.remainder(phases - torch.roll(phases, -1), 2*math.pi)
        assert gaps.sum().item() == pytest.approx(2*math.pi)
        sim = r25b.simulate_four_bar(torch.tensor([seed["parameters"]], dtype=torch.float64), phases, seed["branch_sign"])
        actual = torch.stack((sim["Px"].flatten(), sim["Py"].flatten()), dim=1)
        torch.testing.assert_close(actual, torch.tensor(points, dtype=torch.float64), atol=1e-8, rtol=1e-8)
