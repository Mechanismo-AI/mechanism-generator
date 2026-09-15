"""Directed orientation of the four-bar coupler in the world XY plane.

The output frame is located at the coupler point P, with its positive x axis
parallel to A -> B. Translation of P does not change this orientation. There
is no separately optimized tool mounting angle in this convention.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import torch
from torch import Tensor


def angle_difference(actual_rad: Tensor, target_rad: Tensor) -> Tensor:
    """Return the signed shortest angular difference in [-pi, pi].

    Inputs follow PyTorch broadcasting rules. At exactly half a revolution
    either sign represents the same shortest distance; the absolute error is
    pi, so reversing the directed coupler axis is never treated as a match.
    """
    delta = actual_rad - target_rad
    return torch.atan2(torch.sin(delta), torch.cos(delta))


def _angle_state(sim: Mapping[str, Tensor]) -> tuple[Tensor, Tensor]:
    coordinates = [sim[key] for key in ("Ax", "Ay", "Bx", "By")]
    first = coordinates[0]
    if not isinstance(first, Tensor) or first.ndim != 2 or 0 in first.shape:
        raise ValueError("Orientation coordinates must have nonempty shape [batch, samples].")
    for coordinate in coordinates:
        if not isinstance(coordinate, Tensor) or not coordinate.is_floating_point():
            raise ValueError("Orientation coordinates must be floating-point tensors.")
        if coordinate.shape != first.shape:
            raise ValueError("Orientation coordinate shapes must match.")
        if coordinate.dtype != first.dtype or coordinate.device != first.device:
            raise ValueError("Orientation coordinates must share dtype and device.")

    ax, ay, bx, by = coordinates
    dx, dy = bx - ax, by - ay
    finite = torch.isfinite(dx) & torch.isfinite(dy)
    for coordinate in coordinates:
        finite = finite & torch.isfinite(coordinate)
    defined = finite & ((dx != 0) | (dy != 0))
    # atan2(0, 0) has undefined derivatives. Replacing undefined directions
    # before atan2 also keeps invalid geometry out of the optimizer's graph.
    safe_dx = torch.where(defined, dx, torch.ones_like(dx))
    safe_dy = torch.where(defined, dy, torch.zeros_like(dy))
    return torch.atan2(safe_dy, safe_dx), defined


def orientation_angles(sim: Mapping[str, Tensor]) -> Tensor:
    """Return world-frame A -> B angles in radians, with shape [batch, samples].

    Undefined or nonfinite directions use zero as a finite placeholder.
    Call :func:`orientation_metrics` when deciding validity or qualification;
    a placeholder angle must never qualify invalid geometry.
    """
    return _angle_state(sim)[0]


def orientation_metrics(
    sim: Mapping[str, Tensor],
    target_degrees: Tensor | Sequence[float],
    tolerance_degrees: float | Tensor | Sequence[float],
) -> dict[str, Tensor]:
    """Measure directed target orientation without changing position metrics.

    ``target_degrees`` has shape [samples] or [batch, samples]; tolerances may
    have either shape or be one scalar applying to every sample. ``sim['valid']``
    is the simulation's boolean assembly-validity tensor of that same shape.
    Angles, signed errors, absolute degree errors, and ``valid`` are per sample;
    means, maxima, ``feasible``, and ``penalty`` are per batch row.

    The differentiable penalty is mean plus worst squared half-angle sine
    (one quarter of squared unit-circle chord distance), ranging from 0 to 2.
    Its weight in the position/orientation objective belongs to the caller.
    Invalid samples have 180-degree error and maximal per-sample penalty, and
    cannot qualify even when the requested tolerance is 180 degrees.
    """
    angles, defined = _angle_state(sim)
    tolerance = torch.as_tensor(tolerance_degrees, dtype=angles.dtype, device=angles.device)
    if tolerance.shape not in (torch.Size([]), angles.shape, angles.shape[1:]):
        raise ValueError("Orientation tolerances must be scalar or have shape [samples] or [batch, samples].")
    if not (torch.isfinite(tolerance) & (tolerance >= 0) & (tolerance <= 180)).all():
        raise ValueError("Orientation tolerances must be finite and between 0 and 180 degrees.")
    assembly_valid = sim["valid"]
    if (
        not isinstance(assembly_valid, Tensor)
        or assembly_valid.dtype != torch.bool
        or assembly_valid.shape != angles.shape
        or assembly_valid.device != angles.device
    ):
        raise ValueError("Simulation validity must be a boolean tensor matching the coordinates.")
    target = torch.as_tensor(target_degrees, dtype=angles.dtype, device=angles.device)
    if target.shape not in (angles.shape, angles.shape[1:]):
        raise ValueError("Target orientations must have shape [samples] or [batch, samples].")
    if not torch.isfinite(target).all():
        raise ValueError("Target orientations must be finite.")
    # Reducing in degrees first improves numerical accuracy for full turns.
    target_rad = torch.deg2rad(torch.remainder(target, 360.0))
    valid = defined & assembly_valid
    signed_errors = angle_difference(angles, target_rad)
    signed_errors = torch.where(valid, signed_errors, torch.full_like(signed_errors, math.pi))
    errors_deg = torch.rad2deg(signed_errors.abs())
    max_error = errors_deg.amax(dim=1)
    chord_error = torch.sin(signed_errors / 2).square()
    penalty = chord_error.mean(dim=1) + chord_error.amax(dim=1)
    # A roundoff allowance makes an exactly-on-boundary target independent of
    # the trigonometric conversion's last few representable digits.
    roundoff = 8 * torch.finfo(angles.dtype).eps * tolerance
    return {
        "angles_rad": angles,
        "signed_errors_rad": signed_errors,
        "errors_deg": errors_deg,
        "mean_error_deg": errors_deg.mean(dim=1),
        "max_error_deg": max_error,
        "valid": valid,
        "feasible": (valid & (errors_deg <= tolerance + roundoff)).all(dim=1),
        "penalty": penalty,
    }
