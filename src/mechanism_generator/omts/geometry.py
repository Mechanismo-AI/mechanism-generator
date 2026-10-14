"""Sampled collision geometry for OMTS line verification (G3 seed).

Pure-stdlib forward kinematics for recorded four-bar candidates, plus
region-occupancy sampling over the crank cycle. This module never runs a
solver, never modifies results, and never imports numpy or torch; it is
parity-tested against the engine's independent NumPy panel screening
(``engine/panel.py``), which is itself parity-tested against the engine's
Torch simulator.

Conventions match the engine exactly. A candidate is the nine-value
parameter vector ``(l1, l2, l3, l4, S_ratio, bar_length, base_x, base_y,
base_angle)`` recorded in run manifests, plus an assembly ``branch_sign``
(+1 crossed, -1 open). ``O2`` is ``(base_x, base_y)``; ``O4`` lies at
ground length ``l1`` in direction ``base_angle``. ``theta_deg`` is the
engine's crank parameter -- the same angle space as the achieved target
phases the timeline verifier composes -- and the world crank direction is
``theta_deg + base_angle``.

Occupancy is sampled, not certified: it says nothing between samples, checks
only the declared bodies (moving link centerlines, optional carrier
rectangle, declared thickness), and is not collision, thickness or machinery
certification. Undefined assembly at a sampled phase is an error, never a
quiet pass.
"""

from __future__ import annotations

import math

METHOD = "sampled_collision_geometry_v1"
PARAM_COUNT = 9
MIN_STEPS = 361
MAX_STEPS = 72001


def _validated_params(params, branch_sign) -> list[float]:
    if branch_sign not in (-1, 1):
        raise ValueError("branch_sign must be -1 or 1.")
    values = [float(value) for value in params]
    if len(values) != PARAM_COUNT:
        raise ValueError(f"Parameters must be {PARAM_COUNT} values, got {len(values)}.")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Parameters must all be finite.")
    if any(value <= 0.0 for value in values[:4]):
        raise ValueError("Link lengths l1..l4 must be positive.")
    return values


def four_bar_skeleton(params, branch_sign: int, theta_deg: float, carrier=None):
    """World positions at one crank parameter value.

    Returns a dict with `o2`, `o4`, `a`, `b`, `p` (the coupler point)
    and `carrier_corners` (an empty tuple unless `carrier` is a
    `(width, depth)` pair), or `None` when the assembly is undefined at
    this phase. Undefined assembly is data, not an error.
    """
    l1, l2, l3, l4, s_ratio, bar, base_x, base_y, base_deg = _validated_params(params, branch_sign)
    base = math.radians(base_deg)
    o2 = (base_x, base_y)
    o4 = (base_x + l1 * math.cos(base), base_y + l1 * math.sin(base))
    angle = math.radians(theta_deg) + base
    a = (base_x + l2 * math.cos(angle), base_y + l2 * math.sin(angle))
    delta = (a[0] - o4[0], a[1] - o4[1])
    distance = math.hypot(delta[0], delta[1])
    if distance <= 0.0 or distance > l3 + l4 or distance < abs(l3 - l4):
        return None
    cx, cy = delta[0] / distance, delta[1] / distance
    along = (l4 * l4 - l3 * l3 + distance * distance) / (2.0 * distance)
    height = math.sqrt(max(0.0, l4 * l4 - along * along))
    # branch_sign selects the circle-intersection side, perpendicular to O4->A.
    b = (o4[0] + along * cx - branch_sign * height * cy,
         o4[1] + along * cy + branch_sign * height * cx)
    ux, uy = (b[0] - a[0]) / l3, (b[1] - a[1]) / l3
    vx, vy = -uy, ux
    p = (a[0] + s_ratio * (b[0] - a[0]) + bar * vx,
         a[1] + s_ratio * (b[1] - a[1]) + bar * vy)
    corners: tuple = ()
    if carrier is not None:
        width, depth = float(carrier[0]), float(carrier[1])
        if width <= 0.0 or depth <= 0.0:
            raise ValueError("Carrier dimensions must be positive.")
        corners = tuple(
            (p[0] + x * ux + y * vx, p[1] + x * uy + y * vy)
            for x, y in ((width / 2.0, depth / 2.0), (width / 2.0, -depth / 2.0),
                         (-width / 2.0, -depth / 2.0), (-width / 2.0, depth / 2.0))
        )
    return {"o2": o2, "o4": o4, "a": a, "b": b, "p": p, "carrier_corners": corners}


def _segment_point_distance(px: float, py: float, qx: float, qy: float,
                            x: float, y: float) -> float:
    dx, dy = qx - px, qy - py
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0:
        return math.hypot(x - px, y - py)
    t = ((x - px) * dx + (y - py) * dy) / length_sq
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(x - (px + t * dx), y - (py + t * dy))


def _cross(ox, oy, ax, ay, bx, by):
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _segments_cross(p1, q1, p2, q2) -> bool:
    d1 = _cross(p2[0], p2[1], q2[0], q2[1], p1[0], p1[1])
    d2 = _cross(p2[0], p2[1], q2[0], q2[1], q1[0], q1[1])
    d3 = _cross(p1[0], p1[1], q1[0], q1[1], p2[0], p2[1])
    d4 = _cross(p1[0], p1[1], q1[0], q1[1], q2[0], q2[1])
    return d1 * d2 < 0.0 and d3 * d4 < 0.0


def _segment_segment_distance(p1, q1, p2, q2) -> float:
    if _segments_cross(p1, q1, p2, q2):
        return 0.0
    return min(
        _segment_point_distance(p1[0], p1[1], q1[0], q1[1], p2[0], p2[1]),
        _segment_point_distance(p1[0], p1[1], q1[0], q1[1], q2[0], q2[1]),
        _segment_point_distance(p2[0], p2[1], q2[0], q2[1], p1[0], p1[1]),
        _segment_point_distance(p2[0], p2[1], q2[0], q2[1], q1[0], q1[1]),
    )


def _check_region(region) -> None:
    shape = region.get("shape")
    if shape == "box":
        low, high = region.get("min"), region.get("max")
        if (not isinstance(low, (list, tuple)) or not isinstance(high, (list, tuple))
                or len(low) != 2 or len(high) != 2):
            raise ValueError("Box regions need two-component min and max.")
        if not all(math.isfinite(float(value)) for value in (*low, *high)):
            raise ValueError("Region bounds must be finite.")
        if low[0] >= high[0] or low[1] >= high[1]:
            raise ValueError("Box region bounds must increase componentwise.")
    elif shape == "circle":
        center, radius = region.get("center"), region.get("radius")
        if not isinstance(center, (list, tuple)) or len(center) != 2:
            raise ValueError("Circle regions need a two-component center.")
        if not all(math.isfinite(float(value)) for value in center) or not math.isfinite(float(radius)):
            raise ValueError("Circle region values must be finite.")
        if float(radius) <= 0.0:
            raise ValueError("Circle region radius must be positive.")
    else:
        raise ValueError(f"Unsupported region shape: {shape!r}")


def _point_in_box(point, low, high) -> bool:
    return low[0] <= point[0] <= high[0] and low[1] <= point[1] <= high[1]


def _region_distance(region, segment) -> float:
    """Distance from a body segment to a region; 0.0 when it reaches it."""
    p, q = segment
    if region["shape"] == "box":
        low, high = region["min"], region["max"]
        if _point_in_box(p, low, high) or _point_in_box(q, low, high):
            return 0.0
        edges = (
            ((low[0], low[1]), (high[0], low[1])),
            ((high[0], low[1]), (high[0], high[1])),
            ((high[0], high[1]), (low[0], high[1])),
            ((low[0], high[1]), (low[0], low[1])),
        )
        return min(_segment_segment_distance(p, q, e1, e2) for e1, e2 in edges)
    center = region["center"]
    return max(0.0, _segment_point_distance(p[0], p[1], q[0], q[1],
                                             center[0], center[1]) - float(region["radius"]))


def _region_anchor(region):
    if region["shape"] == "box":
        low, high = region["min"], region["max"]
        return ((low[0] + high[0]) / 2.0, (low[1] + high[1]) / 2.0)
    return (float(region["center"][0]), float(region["center"][1]))


def _point_in_carrier(point, skeleton, carrier) -> bool:
    a, b, p = skeleton["a"], skeleton["b"], skeleton["p"]
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    vx, vy = -uy, ux
    width, depth = carrier
    dx, dy = point[0] - p[0], point[1] - p[1]
    return (abs(dx * ux + dy * uy) <= width / 2.0
            and abs(dx * vx + dy * vy) <= depth / 2.0)


def occupies(params, branch_sign: int, region, theta_deg: float,
             thickness: float = 0.0, carrier=None) -> bool:
    """True when any declared body reaches the region at this phase.

    Bodies are the moving link centerlines (crank, coupler, rocker), the
    carrier rectangle's edges when `carrier` is given, and the region's
    anchor point when it lies inside the carrier. `thickness` inflates
    every body by a capsule radius.
    """
    limit = float(thickness)
    if limit < 0.0:
        raise ValueError("Thickness must be non-negative.")
    _check_region(region)
    skeleton = four_bar_skeleton(params, branch_sign, theta_deg, carrier=carrier)
    if skeleton is None:
        raise ValueError(f"Assembly is undefined at theta {theta_deg} deg; occupancy is never guessed.")
    segments = [
        (skeleton["o2"], skeleton["a"]),
        (skeleton["a"], skeleton["b"]),
        (skeleton["o4"], skeleton["b"]),
    ]
    corners = skeleton["carrier_corners"]
    for index in range(len(corners)):
        segments.append((corners[index], corners[(index + 1) % len(corners)]))
    if any(_region_distance(region, segment) <= limit for segment in segments):
        return True
    if corners and _point_in_carrier(_region_anchor(region), skeleton,
                                      (float(carrier[0]), float(carrier[1]))):
        return True
    return False


def windows_from_flags(flags) -> list[dict]:
    """Contiguous True runs of a circular sample list, in degrees.

    `flags[i]` is the state at phase `360 * i / len(flags)`. Windows may
    wrap through zero. Returns `[{"start_deg": ..., "end_deg": ...}]`.
    """
    flags = [bool(flag) for flag in flags]
    count = len(flags)
    if count <= 0:
        raise ValueError("flags must not be empty.")
    if not any(flags):
        return []
    if all(flags):
        return [{"start_deg": 0.0, "end_deg": 360.0 - 360.0 / count}]
    runs = []
    start = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, count - 1))
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == count - 1:
        runs = [(runs[-1][0], runs[0][1])] + runs[1:-1]
    return [
        {"start_deg": 360.0 * first / count, "end_deg": 360.0 * last / count}
        for first, last in runs
    ]


def occupancy_windows(params, branch_sign: int, region, steps: int,
                      thickness: float = 0.0, carrier=None) -> list[dict]:
    """Sampled occupancy windows of one candidate against one region."""
    if (isinstance(steps, bool) or not isinstance(steps, int)
            or not MIN_STEPS <= steps <= MAX_STEPS):
        raise ValueError(f"Occupancy sampling requires an integer step count between {MIN_STEPS} and {MAX_STEPS}.")
    _check_region(region)
    flags = [
        occupies(params, branch_sign, region, 360.0 * index / steps,
                 thickness=thickness, carrier=carrier)
        for index in range(steps)
    ]
    return windows_from_flags(flags)
