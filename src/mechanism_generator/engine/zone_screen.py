"""Sampled per-candidate zone screening at qualification time (Z2).

This is the engine-side counterpart of the OMTS search-time zone screening
vocabulary (specs/omts/0.2/search_screening.md). For every candidate it
samples the same occupancy the stdlib kernel (omts/geometry.py) computes --
declared moving-body segments and an optional carrier rectangle against
declared regions over the full crank turn -- and reduces each region's
occupancy to window counts and arc widths. Hard screen entries exclude
failing candidates from selection eligibility; soft and report_only
entries record data only. The screen never gates the composed line
verdict: a pass is not a collision-free claim.

Conventions mirror omts/geometry.py exactly (parity-tested there): the
parameter vector is (l1, l2, l3, l4, S_ratio, bar_length, base_x, base_y,
base_angle), O2 is (base_x, base_y), O4 lies at ground length l1 in
direction base_angle, the world crank direction is theta + base_angle, and
occupancy flags are sampled at 360*i/steps degrees for i in 0..steps-1.
Undefined assembly at any sampled phase fails the candidate: occupancy is
never guessed, exactly as the kernel never guesses it.

This is a kinematic screen. It is not collision, thickness or machinery
certification, and it says nothing between samples.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

METHOD = "sampled_collision_geometry_v1"
MIN_STEPS = 361
MAX_STEPS = 72001
DISCLAIMER = ("Sampled, not certified; no between-sample guarantee; not "
              "collision, thickness or machinery certification.")
_MODES = ("hard", "soft", "report_only")
_CRITERIA = ("avoid", "max_total_width_deg", "max_windows")
_CONFIG_CACHE = {}


def _finite_number(value) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def configuration(args):
    """Parse and validate the --zone_screen sidecar; None when absent.

    The parsed configuration is memoized per (path, mtime, size) because
    this is called once per candidate. Every violation is a ValueError so
    the CLI converts it into a hard parser error (fail closed).
    """
    sidecar = getattr(args, "zone_screen", None)
    if sidecar is None:
        return None
    path = Path(sidecar)
    try:
        stat = path.stat()
        key = (str(path), stat.st_mtime_ns, stat.st_size)
    except OSError as error:
        raise ValueError(f"Zone screen sidecar is not readable: {sidecar} ({error}).")
    cached = _CONFIG_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Zone screen sidecar must be readable JSON: {error}.")
    if not isinstance(document, dict):
        raise ValueError("Zone screen sidecar must be a JSON object.")
    unknown = sorted(set(document) - set(
        "method task steps thickness carrier regions screen note disclaimer".split()))
    if unknown:
        raise ValueError(f"Zone screen sidecar has unsupported keys: {', '.join(unknown)}.")
    if document.get("method") != METHOD:
        raise ValueError(f"Zone screen sidecar method must be {METHOD!r}.")
    steps = document.get("steps")
    if (isinstance(steps, bool) or not isinstance(steps, int)
            or not MIN_STEPS <= steps <= MAX_STEPS):
        raise ValueError(f"Zone screen sampling requires an integer step count between {MIN_STEPS} and {MAX_STEPS}.")
    thickness = document.get("thickness")
    if not _finite_number(thickness) or thickness < 0:
        raise ValueError("Zone screen thickness must be a non-negative finite number.")
    carrier = None
    if "carrier" in document:
        raw = document["carrier"]
        if (not isinstance(raw, dict) or set(raw) != {"width", "depth"}
                or not all(_finite_number(value) and value > 0 for value in raw.values())):
            raise ValueError("Zone screen carrier needs positive finite width and depth.")
        carrier = (float(raw["width"]), float(raw["depth"]))
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise ValueError("Zone screen sidecar requires a non-empty regions list.")
    regions = {}
    for region in raw_regions:
        if not isinstance(region, dict):
            raise ValueError("Each zone screen region must be an object.")
        unknown = sorted(set(region) - set("id name notes shape min max center radius".split()))
        if unknown:
            raise ValueError(f"Zone screen region has unsupported keys: {', '.join(unknown)}.")
        region_id = region.get("id")
        if not isinstance(region_id, str) or not region_id:
            raise ValueError("Each zone screen region needs a non-empty string id.")
        if region_id in regions:
            raise ValueError(f"Zone screen region '{region_id}' is declared more than once.")
        shape = region.get("shape")
        if shape == "box":
            low, high = region.get("min"), region.get("max")
            if (not isinstance(low, list) or not isinstance(high, list)
                    or len(low) != 2 or len(high) != 2
                    or not all(_finite_number(value) for value in (*low, *high))):
                raise ValueError("Box regions need two-component finite min and max.")
            if low[0] >= high[0] or low[1] >= high[1]:
                raise ValueError("Box region bounds must increase componentwise.")
            regions[region_id] = {
                "shape": "box",
                "min": [float(low[0]), float(low[1])],
                "max": [float(high[0]), float(high[1])],
            }
        elif shape == "circle":
            center, radius = region.get("center"), region.get("radius")
            if (not isinstance(center, list) or len(center) != 2
                    or not all(_finite_number(value) for value in center)
                    or not _finite_number(radius) or radius <= 0):
                raise ValueError("Circle regions need a two-component finite center and a positive radius.")
            regions[region_id] = {
                "shape": "circle",
                "center": [float(center[0]), float(center[1])],
                "radius": float(radius),
            }
        else:
            raise ValueError(f"Unsupported region shape: {shape!r}.")
    raw_screen = document.get("screen")
    if not isinstance(raw_screen, list) or not raw_screen:
        raise ValueError("Zone screen sidecar requires a non-empty screen list.")
    screen = []
    seen = set()
    for entry in raw_screen:
        if not isinstance(entry, dict):
            raise ValueError("Each zone screen entry must be an object.")
        unknown = sorted(set(entry) - set("region avoid max_total_width_deg max_windows mode notes".split()))
        if unknown:
            raise ValueError(f"Zone screen entry has unsupported keys: {', '.join(unknown)}.")
        region_id = entry.get("region")
        if not isinstance(region_id, str) or region_id not in regions:
            raise ValueError(f"Zone screen entry references unknown region {region_id!r}.")
        if region_id in seen:
            raise ValueError(f"Zone screen region '{region_id}' is screened more than once.")
        seen.add(region_id)
        mode = entry.get("mode", "hard")
        if mode not in _MODES:
            raise ValueError(f"Zone screen mode must be one of {_MODES!r}.")
        record = {"region": region_id, "mode": mode}
        if "avoid" in entry:
            if not isinstance(entry["avoid"], bool):
                raise ValueError("Zone screen avoid must be a boolean.")
            record["avoid"] = entry["avoid"]
        if "max_total_width_deg" in entry:
            width = entry["max_total_width_deg"]
            if not _finite_number(width) or not 0 <= width <= 360:
                raise ValueError("Zone screen max_total_width_deg must be a finite value within [0, 360].")
            record["max_total_width_deg"] = float(width)
        if "max_windows" in entry:
            count = entry["max_windows"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("Zone screen max_windows must be a non-negative integer.")
            record["max_windows"] = count
        if not any(key in record for key in _CRITERIA):
            raise ValueError(f"Zone screen entry for '{region_id}' requires at least one criterion.")
        if "notes" in entry:
            record["notes"] = str(entry["notes"])
        screen.append(record)
    config = {
        "method": METHOD,
        "sidecar": str(path),
        "task": document.get("task"),
        "steps": steps,
        "thickness": float(thickness),
        "carrier": carrier,
        "regions": regions,
        "screen": screen,
    }
    _CONFIG_CACHE[key] = config
    return config


def _segment_point_distance(px, py, qx, qy, x, y):
    """Distance from point (x, y) to segment PQ; arrays broadcast."""
    dx, dy = qx - px, qy - py
    length_sq = dx * dx + dy * dy
    safe_sq = np.where(length_sq <= 0.0, 1.0, length_sq)
    t = np.clip(((x - px) * dx + (y - py) * dy) / safe_sq, 0.0, 1.0)
    return np.hypot(x - (px + t * dx), y - (py + t * dy))


def _cross(ox, oy, ax, ay, bx, by):
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _segment_segment_distance(p1x, p1y, q1x, q1y, p2x, p2y, q2x, q2y):
    """Distance between segments P1Q1 (arrays) and P2Q2 (scalars)."""
    d1 = _cross(p2x, p2y, q2x, q2y, p1x, p1y)
    d2 = _cross(p2x, p2y, q2x, q2y, q1x, q1y)
    d3 = _cross(p1x, p1y, q1x, q1y, p2x, p2y)
    d4 = _cross(p1x, p1y, q1x, q1y, q2x, q2y)
    crossing = (d1 * d2 < 0.0) & (d3 * d4 < 0.0)
    fallback = np.minimum.reduce((
        _segment_point_distance(p1x, p1y, q1x, q1y, p2x, p2y),
        _segment_point_distance(p1x, p1y, q1x, q1y, q2x, q2y),
        _segment_point_distance(p2x, p2y, q2x, q2y, p1x, p1y),
        _segment_point_distance(p2x, p2y, q2x, q2y, q1x, q1y),
    ))
    return np.where(crossing, 0.0, fallback)


def _region_distance(region, px, py, qx, qy):
    """Distance from one body segment to a region; 0.0 when it reaches it.

    Mirrors omts/geometry.py: box regions test both endpoints first, then
    the four edges; circle regions subtract the radius and clamp at zero.
    """
    if region["shape"] == "box":
        low, high = region["min"], region["max"]
        inside = (((px >= low[0]) & (px <= high[0]) & (py >= low[1]) & (py <= high[1]))
                  | ((qx >= low[0]) & (qx <= high[0]) & (qy >= low[1]) & (qy <= high[1])))
        edges = (
            (low[0], low[1], high[0], low[1]),
            (high[0], low[1], high[0], high[1]),
            (high[0], high[1], low[0], high[1]),
            (low[0], high[1], low[0], low[1]),
        )
        distance = np.minimum.reduce(
            tuple(_segment_segment_distance(px, py, qx, qy, *edge) for edge in edges)
        )
        return np.where(inside, 0.0, distance)
    center = region["center"]
    return np.maximum(0.0, _segment_point_distance(
        px, py, qx, qy, center[0], center[1]) - region["radius"])


def _region_anchor(region):
    if region["shape"] == "box":
        low, high = region["min"], region["max"]
        return ((low[0] + high[0]) / 2.0, (low[1] + high[1]) / 2.0)
    return (region["center"][0], region["center"][1])


def _occupancy_flags(region, segments, thickness, carrier, center, u, v, count):
    """Sampled occupancy of one region against all declared bodies.

    Mirrors omts/geometry.py: a body reaches the region when any segment
    comes within `thickness` (a full capsule radius) of it, or when the
    region's anchor point lies inside the declared carrier rectangle.
    """
    occupied = np.zeros(count, dtype=bool)
    for px, py, qx, qy in segments:
        hit = _region_distance(region, px, py, qx, qy) <= thickness
        occupied |= hit
    if carrier is not None:
        ax, ay = _region_anchor(region)
        dx, dy = ax - center[:, 0], ay - center[:, 1]
        inside_carrier = ((np.abs(dx * u[:, 0] + dy * u[:, 1]) <= carrier[0] / 2.0)
                          & (np.abs(dx * v[:, 0] + dy * v[:, 1]) <= carrier[1] / 2.0))
        occupied |= inside_carrier
    return occupied


def _windows(flags):
    """Contiguous True runs of the circular flag array, in degrees.

    Mirrors omts/geometry.py windows_from_flags exactly, including the
    all-occupied single window and wrap merging through zero.
    """
    count = len(flags)
    if count <= 0 or not flags.any():
        return []
    if flags.all():
        return [(0.0, 360.0 - 360.0 / count)]
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
    return [(360.0 * first / count, 360.0 * last / count) for first, last in runs]


def screen(parameters, branch_sign, config):
    """Fail closed on undefined assembly; otherwise return sampled metrics.

    Every candidate gets `zone_screen_acceptable` (all hard entries pass)
    plus per-region window data for every entry, in every mode. Soft and
    report_only entries never affect the acceptable flag. Undefined
    assembly at any sampled phase, or invalid parameters, leave
    geometry_valid and acceptable False with no windows recorded --
    occupancy is never guessed.
    """
    steps = config["steps"]
    result = {
        "zone_screen_required": True,
        "zone_screen_method": METHOD,
        "zone_screen_steps": steps,
        "zone_screen_thickness": config["thickness"],
        "zone_screen_geometry_valid": False,
        "zone_screen_acceptable": False,
        "zone_screen_disclaimer": DISCLAIMER,
    }
    p = np.asarray(parameters, dtype=float)
    if p.shape != (9,) or not np.isfinite(p).all() or np.any(p[:4] <= 0) or branch_sign not in (-1, 1):
        return result
    l1, l2, l3, l4, s, bar, bx, by, base_deg = (float(value) for value in p)
    base = math.radians(base_deg)
    theta = 2.0 * np.pi * np.arange(steps) / steps
    o2 = np.array([bx, by])
    o4 = o2 + l1 * np.array([math.cos(base), math.sin(base)])
    a = o2 + l2 * np.column_stack((np.cos(theta + base), np.sin(theta + base)))
    delta = a - o4
    distance = np.linalg.norm(delta, axis=1)
    if ((distance <= 0) | (distance > l3 + l4) | (distance < abs(l3 - l4))).any():
        return result
    unit = delta / distance[:, None]
    along = (l4 * l4 - l3 * l3 + distance * distance) / (2 * distance)
    height = np.sqrt(np.maximum(0.0, l4 * l4 - along * along))
    b = o4 + along[:, None] * unit + branch_sign * height[:, None] * np.column_stack((-unit[:, 1], unit[:, 0]))
    u = (b - a) / l3
    v = np.column_stack((-u[:, 1], u[:, 0]))
    center = a + s * (b - a) + bar * v
    carrier = config["carrier"]
    segments = [
        (np.full(steps, o2[0]), np.full(steps, o2[1]), a[:, 0], a[:, 1]),
        (a[:, 0], a[:, 1], b[:, 0], b[:, 1]),
        (np.full(steps, o4[0]), np.full(steps, o4[1]), b[:, 0], b[:, 1]),
    ]
    if carrier is not None:
        width, depth = carrier
        corners = [center + x * u + y * v for x, y in
                   ((width / 2.0, depth / 2.0), (width / 2.0, -depth / 2.0),
                    (-width / 2.0, -depth / 2.0), (-width / 2.0, depth / 2.0))]
        for index in range(4):
            first, second = corners[index], corners[(index + 1) % 4]
            segments.append((first[:, 0], first[:, 1], second[:, 0], second[:, 1]))
    if not all(np.isfinite(np.asarray(column)).all()
               for segment in segments for column in segment):
        return result
    result["zone_screen_geometry_valid"] = True
    hard_pass = True
    for entry in config["screen"]:
        region = config["regions"][entry["region"]]
        flags = _occupancy_flags(region, segments, config["thickness"],
                                 carrier, center, u, v, steps)
        windows = _windows(flags)
        step_deg = 360.0 / steps
        total_width = float(sum((end - start) % 360.0 + step_deg for start, end in windows))
        window_count = len(windows)
        entry_ok = True
        if entry.get("avoid", False):
            entry_ok = entry_ok and window_count == 0
        if "max_total_width_deg" in entry:
            entry_ok = entry_ok and total_width <= entry["max_total_width_deg"]
        if "max_windows" in entry:
            entry_ok = entry_ok and window_count <= entry["max_windows"]
        prefix = f"zone_screen_{entry['region']}"
        result[prefix + "_windows"] = window_count
        result[prefix + "_total_width_deg"] = total_width
        result[prefix + "_acceptable"] = bool(entry_ok)
        result[prefix + "_window_starts_deg"] = [float(start) for start, _ in windows]
        result[prefix + "_window_ends_deg"] = [float(end) for _, end in windows]
        if entry["mode"] == "hard" and not entry_ok:
            hard_pass = False
    result["zone_screen_acceptable"] = bool(hard_pass)
    return result
