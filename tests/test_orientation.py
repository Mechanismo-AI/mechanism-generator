import math

import pytest

torch = pytest.importorskip("torch")

from mechanism_generator.engine.orientation import (
    angle_difference,
    orientation_angles,
    orientation_metrics,
)


def direction_sim(degrees, *, dtype=torch.float64, translation=(0.0, 0.0), device="cpu"):
    angles = torch.deg2rad(torch.tensor(degrees, dtype=dtype, device=device))
    if angles.ndim == 1:
        angles = angles[None, :]
    ax = torch.full_like(angles, translation[0])
    ay = torch.full_like(angles, translation[1])
    return {
        "Ax": ax,
        "Ay": ay,
        "Bx": ax + 5 * torch.cos(angles),
        "By": ay + 5 * torch.sin(angles),
        "valid": torch.ones_like(angles, dtype=torch.bool),
    }


def test_world_frame_translation_and_rotation():
    sim = direction_sim([0, 90, -90, 180], translation=(17, -23))
    torch.testing.assert_close(
        orientation_angles(sim).abs(),
        torch.tensor([[0, math.pi / 2, math.pi / 2, math.pi]], dtype=torch.float64),
        atol=1e-14,
        rtol=1e-14,
    )
    original = direction_sim([-70, 15, 82])
    rotated = direction_sim([-70 + 31, 15 + 31, 82 + 31], translation=(-2, 7))
    difference = angle_difference(orientation_angles(rotated), orientation_angles(original))
    torch.testing.assert_close(difference, torch.full_like(difference, math.radians(31)))


def test_wraparound_uses_shortest_directed_arc_and_full_turns_match():
    result = orientation_metrics(direction_sim([179, -179, 17]), [-179, 179, 737], 2)
    torch.testing.assert_close(result["errors_deg"], torch.tensor([[2., 2., 0.]], dtype=torch.float64), atol=1e-12, rtol=0)
    torch.testing.assert_close(result["signed_errors_rad"][:, :2], torch.tensor([[math.radians(-2), math.radians(2)]], dtype=torch.float64))
    assert result["feasible"].item()
    reversed_axis = orientation_metrics(direction_sim([0]), [180], 5)
    assert reversed_axis["max_error_deg"].item() == pytest.approx(180)
    assert reversed_axis["penalty"].item() == pytest.approx(2)
    assert not reversed_axis["feasible"].item()


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_tolerance_boundary_and_zero_tolerance(dtype):
    result = orientation_metrics(direction_sim([[10, -10], [10.01, -10]], dtype=dtype), [0, 0], 10)
    assert result["feasible"].tolist() == [True, False]
    exact = orientation_metrics(direction_sim([0, 90], dtype=dtype), [360, -270], 0)
    assert exact["feasible"].item()


def test_batch_targets_and_mean_worst_penalty():
    result = orientation_metrics(direction_sim([[0, 90], [180, -90]]), [[0, 0], [180, -90]], 90)
    assert result["feasible"].tolist() == [True, True]
    torch.testing.assert_close(result["penalty"], torch.tensor([.75, 0.], dtype=torch.float64), atol=1e-14, rtol=0)
    assert result["mean_error_deg"][0].item() == pytest.approx(45)


@pytest.mark.parametrize("dtype,error,tolerance", [
    (torch.float32, 5e-7, 1e-12), (torch.float64, 5e-16, 1e-20),
])
def test_tiny_tolerance_has_no_absolute_acceptance_floor(dtype, error, tolerance):
    result = orientation_metrics(direction_sim([error], dtype=dtype), [0], tolerance)
    assert result["max_error_deg"].item() > tolerance
    assert not result["feasible"].item()


def test_each_target_must_meet_its_own_tolerance():
    sim = direction_sim([[2, 9, 19], [2, 9, 19]])
    per_target = orientation_metrics(sim, [0, 0, 0], [1, 10, 20])
    assert per_target["feasible"].tolist() == [False, False]
    per_row = orientation_metrics(sim, [0, 0, 0], [[2, 10, 20], [1, 10, 20]])
    assert per_row["feasible"].tolist() == [True, False]


@pytest.mark.parametrize("tolerance", [[1], [[1], [2]], [1, float("nan")], [1, -2]])
def test_rejects_mismatched_or_nonfinite_tolerance_vectors(tolerance):
    with pytest.raises(ValueError, match="tolerances"):
        orientation_metrics(direction_sim([0, 0]), [0, 0], tolerance)


@pytest.mark.parametrize("invalid", ["assembly", "zero_length", "nonfinite"])
def test_invalid_geometry_cannot_qualify_and_metrics_remain_finite(invalid):
    sim = direction_sim([0, 0])
    if invalid == "assembly":
        sim["valid"][0, 1] = False
    elif invalid == "zero_length":
        sim["Bx"][0, 1] = sim["Ax"][0, 1]
        sim["By"][0, 1] = sim["Ay"][0, 1]
    else:
        sim["Bx"][0, 1] = float("nan")
    result = orientation_metrics(sim, [0, 0], 180)
    assert result["valid"].tolist() == [[True, False]]
    assert not result["feasible"].item()
    assert result["errors_deg"][0, 1].item() == pytest.approx(180)
    assert result["penalty"].item() == pytest.approx(1.5)
    assert all(torch.isfinite(value).all() for value in result.values())


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("device", ["cpu"] + (["cuda"] if torch.cuda.is_available() else []))
def test_gradients_preserve_dtype_device_and_follow_finite_difference(dtype, device):
    angles = torch.tensor([[.2, .7, 1.3]], dtype=dtype, device=device, requires_grad=True)

    def loss(theta):
        sim = {"Ax": torch.zeros_like(theta), "Ay": torch.zeros_like(theta),
               "Bx": 3 * torch.cos(theta), "By": 3 * torch.sin(theta),
               "valid": torch.ones_like(theta, dtype=torch.bool)}
        return orientation_metrics(sim, [0, 15, 30], 10)["penalty"]

    penalty = loss(angles)
    assert penalty.dtype == dtype and penalty.device == angles.device
    penalty.sum().backward()
    assert torch.isfinite(angles.grad).all()
    assert (angles.grad > 0).all()
    step = 1e-3 if dtype == torch.float32 else 1e-6
    plus, minus = angles.detach().clone(), angles.detach().clone()
    plus[0, 1] += step
    minus[0, 1] -= step
    numerical = ((loss(plus) - loss(minus)) / (2 * step)).item()
    assert angles.grad[0, 1].item() == pytest.approx(numerical, rel=2e-3, abs=1e-8)


def test_degenerate_coordinates_have_finite_gradients():
    bx = torch.tensor([[0., 1.]], dtype=torch.float64, requires_grad=True)
    by = torch.tensor([[0., 1.]], dtype=torch.float64, requires_grad=True)
    sim = {"Ax": torch.zeros_like(bx), "Ay": torch.zeros_like(by), "Bx": bx, "By": by,
           "valid": torch.ones_like(bx, dtype=torch.bool)}
    orientation_metrics(sim, [0, 0], 5)["penalty"].sum().backward()
    assert torch.isfinite(bx.grad).all() and torch.isfinite(by.grad).all()
    assert bx.grad[0, 0].item() == by.grad[0, 0].item() == 0


@pytest.mark.parametrize("tolerance", [-1, 181, float("inf"), float("nan")])
def test_rejects_invalid_tolerance(tolerance):
    with pytest.raises(ValueError, match="tolerance"):
        orientation_metrics(direction_sim([0]), [0], tolerance)


@pytest.mark.parametrize("targets", [[0], [[0], [90]], [0, float("nan")]])
def test_rejects_mismatched_or_nonfinite_targets(targets):
    with pytest.raises(ValueError, match="orientations"):
        orientation_metrics(direction_sim([0, 90]), targets, 5)


def test_rejects_missing_batch_axis_and_nonboolean_validity():
    sim = direction_sim([0, 90])
    sim["valid"] = sim["valid"].float()
    with pytest.raises(ValueError, match="validity"):
        orientation_metrics(sim, [0, 90], 5)
    with pytest.raises(ValueError, match="shape"):
        orientation_angles({key: value[0] for key, value in sim.items()})
