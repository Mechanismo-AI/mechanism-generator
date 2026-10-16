#!/usr/bin/env python3
"""Corpus-wide base-angle frame sweep over the corpus-07 zone-screening runs.

Menu E's P0 check reproduced the recorded occupancy windows for 6 exemplar
candidates in the "screen" base-angle frame (base = radians(base_angle)).
This sweep upgrades that observation from 6 exemplars to every candidate row:

  screen frame : base = radians(base_angle), exactly what the engine's
      zone_screen.screen() did -- decode_refinement_variables stores
      base_angle in radians via remainder(raw[8], 2*pi), and screen()
      applies math.radians() again. This is a recorded engine observation,
      not a claimed convention.
  plain frame  : base = base_angle as stored (radians), the frame the value
      would produce if used directly.

For every row of every task's all_candidates.csv, the per-region occupancy
windows are re-resolved from the row geometry, the branch sign, and the
task's zone_screen.json sidecar in both frames, and compared against the
recorded window lists (exact equality; boundaries are quantized at
360/steps degrees, so equal flags give identical floats through the CSV
round-trip).

The resolver mirrors src/mechanism_generator/engine/zone_screen.py::screen()
operation-for-operation in pure stdlib Python (no numpy), including the
circular window extraction, the all-occupied single window, wrap merging,
the carrier rectangle, and the fail-closed undefined-assembly rule.

Recorded constants are checked fail-closed before any comparison: per-task
row tallies, pooled occupancy-class counts, method, steps, thickness,
disclaimer, screen shape (one region, one hard max_total_width_deg entry).
Any structural anomaly aborts loudly with a nonzero exit and nothing is
written to the output directory.

This is sampled kinematic evidence only. It is not collision, thickness or
machinery certification, and it says nothing between samples.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

METHOD = "sampled_collision_geometry_v1"
DISCLAIMER = ("Sampled, not certified; no between-sample guarantee; not "
              "collision, thickness or machinery certification.")
MIN_STEPS = 361
MAX_STEPS = 72001
TWO_PI = 2.0 * math.pi

# ---- recorded corpus-07 constants (fail-closed anchors; do not tune) ----
CORPUS_ROOT = Path("runs/sync-corpus-07")
OUT_DIR = Path("runs/analysis/frame-sweep-01")
EXPECTED_STEPS = 720
EXPECTED_CAP = 60.0
VARIANTS = tuple(f"corpus_pair_{index:02d}" for index in range(1, 7))
TASK_IDS = ("catcher", "gate")
_TALLY_DEFAULT = 42
_TALLY_OVERRIDES = {("corpus_pair_01", "catcher"): 38, ("corpus_pair_05", "gate"): 41}
EXPECTED_TALLIES = {
    (variant, task): _TALLY_OVERRIDES.get((variant, task), _TALLY_DEFAULT)
    for variant in VARIANTS
    for task in TASK_IDS
}
EXPECTED_CLASS_COUNTS = {
    "never": 53,
    "quick_pass": 192,
    "drag_over_cap": 246,
    "full360": 8,
    "invalid": 0,
}

CLASS_ORDER = ("never", "quick_pass", "drag_over_cap", "full360", "invalid")


class SweepError(Exception):
    """Fail-closed abort: the corpus data violates a recorded invariant."""


# ======================================================================
# ===== geometry helpers (mirror zone_screen.py exactly, pure stdlib) ===
# ======================================================================

def _segment_point_distance(px, py, qx, qy, x, y):
    """Distance from point (x, y) to segment PQ."""
    dx, dy = qx - px, qy - py
    length_sq = dx * dx + dy * dy
    safe_sq = length_sq if length_sq > 0.0 else 1.0
    t = ((x - px) * dx + (y - py) * dy) / safe_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(x - (px + t * dx), y - (py + t * dy))


def _cross(ox, oy, ax, ay, bx, by):
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _segment_segment_distance(p1x, p1y, q1x, q1y, p2x, p2y, q2x, q2y):
    """Distance between moving segment P1Q1 and fixed segment P2Q2."""
    d1 = _cross(p2x, p2y, q2x, q2y, p1x, p1y)
    d2 = _cross(p2x, p2y, q2x, q2y, q1x, q1y)
    d3 = _cross(p1x, p1y, q1x, q1y, p2x, p2y)
    d4 = _cross(p1x, p1y, q1x, q1y, p2x, q2y)
    if d1 * d2 < 0.0 and d3 * d4 < 0.0:
        return 0.0
    return min(
        _segment_point_distance(p1x, p1y, q1x, q1y, p2x, p2y),
        _segment_point_distance(p1x, p1y, q1x, q1y, p2x, q2y),
        _segment_point_distance(p2x, p2y, q2x, q2y, p1x, p1y),
        _segment_point_distance(p2x, p2y, q2x, q2y, p1x, q1y),
    )


def _region_distance(region, px, py, qx, qy):
    """Distance from one body segment to a region; 0.0 when it reaches it."""
    if region["shape"] == "box":
        low, high = region["min"], region["max"]
        if ((low[0] <= px <= high[0] and low[1] <= py <= high[1])
                or (low[0] <= qx <= high[0] and low[1] <= qy <= high[1])):
            return 0.0
        edges = (
            (low[0], low[1], high[0], low[1]),
            (high[0], low[1], high[0], high[1]),
            (high[0], high[1], low[0], high[1]),
            (low[0], high[1], low[0], low[1]),
        )
        return min(_segment_segment_distance(px, py, qx, qy, *edge) for edge in edges)
    center = region["center"]
    value = _segment_point_distance(px, py, qx, qy, center[0], center[1]) - region["radius"]
    return value if value > 0.0 else 0.0


def _region_anchor(region):
    if region["shape"] == "box":
        low, high = region["min"], region["max"]
        return ((low[0] + high[0]) / 2.0, (low[1] + high[1]) / 2.0)
    return (region["center"][0], region["center"][1])


def _windows(flags):
    """Contiguous True runs of the circular flag array, in degrees."""
    count = len(flags)
    if count <= 0 or not any(flags):
        return []
    if all(flags):
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


def window_total_width(windows, steps):
    """Engine formula: sum((end - start) % 360 + step) over windows."""
    step_deg = 360.0 / steps
    return float(sum((end - start) % 360.0 + step_deg for start, end in windows))


def entry_pass(entry, window_count, total_width):
    ok = True
    if entry.get("avoid", False):
        ok = ok and window_count == 0
    if "max_total_width_deg" in entry:
        ok = ok and total_width <= entry["max_total_width_deg"]
    if "max_windows" in entry:
        ok = ok and window_count <= entry["max_windows"]
    return bool(ok)


def resolve(params, branch_sign, config, base):
    """Re-resolve per-region occupancy windows at an explicit base angle.

    Mirrors zone_screen.screen(parameters, branch_sign, config) with the
    only difference that the base angle is supplied directly instead of
    being computed as math.radians(parameters[8]).
    """
    steps = config["steps"]
    thickness = config["thickness"]
    carrier = config["carrier"]
    invalid = {"geometry_valid": False, "regions": {}, "acceptable": False}
    if len(params) != 9:
        return invalid
    for value in params:
        if not math.isfinite(value):
            return invalid
    l1, l2, l3, l4, s, bar, bx, by, _base_deg = params
    if l1 <= 0.0 or l2 <= 0.0 or l3 <= 0.0 or l4 <= 0.0:
        return invalid
    if branch_sign != 1.0 and branch_sign != -1.0:
        return invalid
    o2x, o2y = bx, by
    cos_b, sin_b = math.cos(base), math.sin(base)
    o4x = o2x + l1 * cos_b
    o4y = o2y + l1 * sin_b
    entries = []
    for entry in config["screen"]:
        region = config["regions"][entry["region"]]
        entries.append((entry, region, [False] * steps,
                        _region_anchor(region)))
    if not entries:
        return invalid
    two_pi = TWO_PI
    for i in range(steps):
        theta = two_pi * i / steps
        ax = o2x + l2 * math.cos(theta + base)
        ay = o2y + l2 * math.sin(theta + base)
        dx = ax - o4x
        dy = ay - o4y
        d = math.sqrt(dx * dx + dy * dy)
        if d <= 0.0 or d > l3 + l4 or d < abs(l3 - l4):
            return invalid
        ux = dx / d
        uy = dy / d
        along = (l4 * l4 - l3 * l3 + d * d) / (2.0 * d)
        h2 = l4 * l4 - along * along
        height = math.sqrt(h2) if h2 > 0.0 else 0.0
        bxp = o4x + along * ux + branch_sign * height * (-uy)
        byp = o4y + along * uy + branch_sign * height * ux
        ucx = (bxp - ax) / l3
        ucy = (byp - ay) / l3
        vcx = -ucy
        vcy = ucx
        cx = ax + s * (bxp - ax) + bar * vcx
        cy = ay + s * (byp - ay) + bar * vcy
        if carrier is not None:
            w2 = carrier[0] / 2.0
            d2 = carrier[1] / 2.0
            segments = (
                (o2x, o2y, ax, ay),
                (ax, ay, bxp, byp),
                (o4x, o4y, bxp, byp),
                (cx + w2 * ucx + d2 * vcx, cy + w2 * ucy + d2 * vcy,
                 cx + w2 * ucx - d2 * vcx, cy + w2 * ucy - d2 * vcy),
                (cx + w2 * ucx - d2 * vcx, cy + w2 * ucy - d2 * vcy,
                 cx - w2 * ucx - d2 * vcx, cy - w2 * ucy - d2 * vcy),
                (cx - w2 * ucx - d2 * vcx, cy - w2 * ucy - d2 * vcy,
                 cx - w2 * ucx + d2 * vcx, cy - w2 * ucy + d2 * vcy),
                (cx - w2 * ucx + d2 * vcx, cy - w2 * ucy + d2 * vcy,
                 cx + w2 * ucx + d2 * vcx, cy + w2 * ucy + d2 * vcy),
            )
        else:
            segments = (
                (o2x, o2y, ax, ay),
                (ax, ay, bxp, byp),
                (o4x, o4y, bxp, byp),
            )
        for value in segments:
            for coordinate in value:
                if not math.isfinite(coordinate):
                    return invalid
        for entry, region, flags, anchor in entries:
            hit = False
            for px, py, qx, qy in segments:
                if _region_distance(region, px, py, qx, qy) <= thickness:
                    hit = True
                    break
            if not hit and carrier is not None:
                ddx = anchor[0] - cx
                ddy = anchor[1] - cy
                if (abs(ddx * ucx + ddy * ucy) <= carrier[0] / 2.0
                        and abs(ddx * vcx + ddy * vcy) <= carrier[1] / 2.0):
                    hit = True
            if hit:
                flags[i] = True
    result = {"geometry_valid": True, "regions": {}, "acceptable": True}
    for entry, region, flags, _anchor in entries:
        windows = _windows(flags)
        total_width = window_total_width(windows, steps)
        ok = entry_pass(entry, len(windows), total_width)
        result["regions"][entry["region"]] = {
            "windows": windows,
            "total_width": total_width,
            "acceptable": ok,
        }
        if entry["mode"] == "hard" and not ok:
            result["acceptable"] = False
    return result


# ======================================================================
# ===== sidecar loading (mirrors zone_screen.configuration validation) ==
# ======================================================================

def _finite_number(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def load_sidecar(path):
    path = Path(path)
    if not path.is_file():
        raise SweepError(f"zone screen sidecar is not readable: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SweepError(f"zone screen sidecar must be readable JSON: {path} ({error})")
    if not isinstance(document, dict):
        raise SweepError(f"zone screen sidecar must be a JSON object: {path}")
    unknown = sorted(set(document) - set(
        "method task steps thickness carrier regions screen note disclaimer".split()))
    if unknown:
        raise SweepError(f"zone screen sidecar has unsupported keys: {', '.join(unknown)} ({path})")
    if document.get("method") != METHOD:
        raise SweepError(f"zone screen sidecar method must be {METHOD!r}: {path}")
    steps = document.get("steps")
    if (isinstance(steps, bool) or not isinstance(steps, int)
            or not MIN_STEPS <= steps <= MAX_STEPS):
        raise SweepError(f"zone screen sampling requires an integer step count between "
                         f"{MIN_STEPS} and {MAX_STEPS}: {path}")
    thickness = document.get("thickness")
    if not _finite_number(thickness) or thickness < 0:
        raise SweepError(f"zone screen thickness must be a non-negative finite number: {path}")
    carrier = None
    if "carrier" in document:
        raw = document["carrier"]
        if (not isinstance(raw, dict) or set(raw) != {"width", "depth"}
                or not all(_finite_number(value) and value > 0 for value in raw.values())):
            raise SweepError(f"zone screen carrier needs positive finite width and depth: {path}")
        carrier = (float(raw["width"]), float(raw["depth"]))
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise SweepError(f"zone screen sidecar requires a non-empty regions list: {path}")
    regions = {}
    for region in raw_regions:
        if not isinstance(region, dict):
            raise SweepError(f"each zone screen region must be an object: {path}")
        unknown = sorted(set(region) - set("id name notes shape min max center radius".split()))
        if unknown:
            raise SweepError(f"zone screen region has unsupported keys: {', '.join(unknown)} ({path})")
        region_id = region.get("id")
        if not isinstance(region_id, str) or not region_id:
            raise SweepError(f"each zone screen region needs a non-empty string id: {path}")
        if region_id in regions:
            raise SweepError(f"zone screen region '{region_id}' is declared more than once: {path}")
        shape = region.get("shape")
        if shape == "box":
            low, high = region.get("min"), region.get("max")
            if (not isinstance(low, list) or not isinstance(high, list)
                    or len(low) != 2 or len(high) != 2
                    or not all(_finite_number(value) for value in (*low, *high))):
                raise SweepError(f"box regions need two-component finite min and max: {path}")
            if low[0] >= high[0] or low[1] >= high[1]:
                raise SweepError(f"box region bounds must increase componentwise: {path}")
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
                raise SweepError(f"circle regions need a two-component finite center and a "
                                 f"positive radius: {path}")
            regions[region_id] = {
                "shape": "circle",
                "center": [float(center[0]), float(center[1])],
                "radius": float(radius),
            }
        else:
            raise SweepError(f"unsupported region shape: {shape!r} ({path})")
    raw_screen = document.get("screen")
    if not isinstance(raw_screen, list) or not raw_screen:
        raise SweepError(f"zone screen sidecar requires a non-empty screen list: {path}")
    screen = []
    seen = set()
    for entry in raw_screen:
        if not isinstance(entry, dict):
            raise SweepError(f"each zone screen entry must be an object: {path}")
        unknown = sorted(set(entry) - set(
            "region avoid max_total_width_deg max_windows mode notes".split()))
        if unknown:
            raise SweepError(f"zone screen entry has unsupported keys: {', '.join(unknown)} ({path})")
        region_id = entry.get("region")
        if not isinstance(region_id, str) or region_id not in regions:
            raise SweepError(f"zone screen entry references unknown region {region_id!r}: {path}")
        if region_id in seen:
            raise SweepError(f"zone screen region '{region_id}' is screened more than once: {path}")
        seen.add(region_id)
        mode = entry.get("mode", "hard")
        if mode not in ("hard", "soft", "report_only"):
            raise SweepError(f"zone screen mode must be hard, soft or report_only: {path}")
        record = {"region": region_id, "mode": mode}
        if "avoid" in entry:
            if not isinstance(entry["avoid"], bool):
                raise SweepError(f"zone screen avoid must be a boolean: {path}")
            record["avoid"] = entry["avoid"]
        if "max_total_width_deg" in entry:
            width = entry["max_total_width_deg"]
            if not _finite_number(width) or not 0 <= width <= 360:
                raise SweepError(f"zone screen max_total_width_deg must be a finite value "
                                 f"within [0, 360]: {path}")
            record["max_total_width_deg"] = float(width)
        if "max_windows" in entry:
            count = entry["max_windows"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise SweepError(f"zone screen max_windows must be a non-negative integer: {path}")
            record["max_windows"] = count
        if not any(key in record for key in ("avoid", "max_total_width_deg", "max_windows")):
            raise SweepError(f"zone screen entry for '{region_id}' requires at least one "
                             f"criterion: {path}")
        if "notes" in entry:
            record["notes"] = str(entry["notes"])
        screen.append(record)
    return {
        "method": METHOD,
        "sidecar": str(path),
        "task": document.get("task"),
        "steps": steps,
        "thickness": float(thickness),
        "carrier": carrier,
        "regions": regions,
        "screen": screen,
    }


# ======================================================================
# ===== corpus traversal and row parsing ================================
# ======================================================================

def find_target_dir(run_root, context):
    if not run_root.is_dir():
        raise SweepError(f"engine output root not found: {run_root} ({context})")
    completed = []
    for manifest_path in sorted(run_root.glob("r25c/*/run_manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SweepError(f"unreadable run manifest {manifest_path} ({error})")
        if manifest.get("run_status") == "completed":
            completed.append(manifest_path.parent)
    if not completed:
        raise SweepError(f"no completed r25c run under {run_root} ({context})")
    latest = completed[-1]
    target_dirs = sorted(
        child for child in latest.iterdir()
        if child.is_dir() and re.fullmatch(r"\d{4,}_.+", child.name)
    )
    if len(target_dirs) != 1:
        raise SweepError(
            f"expected exactly one target dir matching \\d{{4,}}_.+ in {latest} "
            f"({context}); found {[child.name for child in target_dirs]}")
    return target_dirs[0]


def _parse_bool(value, context):
    if value == "True":
        return True
    if value == "False":
        return False
    raise SweepError(f"expected exactly 'True' or 'False', got {value!r} ({context})")


def _parse_float(value, context):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise SweepError(f"expected a float, got {value!r} ({context})")
    if not math.isfinite(number):
        raise SweepError(f"expected a finite float, got {value!r} ({context})")
    return number


def _parse_int(value, context):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise SweepError(f"expected an integer, got {value!r} ({context})")


def _parse_window_list(value, context):
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        raise SweepError(f"window column must be a JSON-parseable list, got {value!r} ({context})")
    if not isinstance(data, list):
        raise SweepError(f"window column must be a list, got {value!r} ({context})")
    numbers = []
    for item in data:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise SweepError(f"window entries must be numbers, got {item!r} ({context})")
        number = float(item)
        if not math.isfinite(number):
            raise SweepError(f"window entries must be finite, got {item!r} ({context})")
        if not 0.0 <= number < 360.0:
            raise SweepError(f"window entries must lie in [0, 360), got {item!r} ({context})")
        numbers.append(number)
    return numbers


def read_rows(csv_path, config, region_id, context):
    """Parse and fail-closed-validate every candidate row of one task."""
    if not csv_path.is_file():
        raise SweepError(f"all_candidates.csv not found: {csv_path} ({context})")
    try:
        with csv_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fieldnames = reader.fieldnames
            raw_rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise SweepError(f"unreadable candidate CSV {csv_path} ({error})")
    if not fieldnames or not raw_rows:
        raise SweepError(f"candidate CSV is empty: {csv_path} ({context})")
    prefix = f"zone_screen_{region_id}"
    geometry_columns = ("l1", "l2", "l3", "l4", "S_ratio", "bar_length",
                        "base_x", "base_y", "base_angle")
    screen_columns = (
        "candidate_id", "branch_sign", "zone_screen_required", "zone_screen_method",
        "zone_screen_steps", "zone_screen_thickness", "zone_screen_geometry_valid",
        "zone_screen_acceptable", "zone_screen_disclaimer",
        f"{prefix}_windows", f"{prefix}_total_width_deg", f"{prefix}_acceptable",
        f"{prefix}_window_starts_deg", f"{prefix}_window_ends_deg",
    )
    missing = [name for name in geometry_columns + screen_columns if name not in fieldnames]
    if missing:
        raise SweepError(f"candidate CSV is missing required columns {missing}: {csv_path}")
    entry = config["screen"][0]
    cap = entry.get("max_total_width_deg")
    rows = []
    seen_ids = set()
    for line_number, raw in enumerate(raw_rows, start=2):
        where = f"{context} line {line_number}"
        candidate_id = (raw.get("candidate_id") or "").strip()
        if not candidate_id:
            raise SweepError(f"empty candidate_id ({where})")
        if candidate_id in seen_ids:
            raise SweepError(f"duplicate candidate_id {candidate_id!r} ({where})")
        seen_ids.add(candidate_id)
        if _parse_bool(raw["zone_screen_required"], where) is not True:
            raise SweepError(f"zone_screen_required must be True ({where})")
        if raw["zone_screen_method"] != METHOD:
            raise SweepError(f"zone_screen_method must be {METHOD!r} ({where})")
        if _parse_int(raw["zone_screen_steps"], where) != config["steps"]:
            raise SweepError(f"zone_screen_steps disagrees with the sidecar ({where})")
        if _parse_float(raw["zone_screen_thickness"], where) != config["thickness"]:
            raise SweepError(f"zone_screen_thickness disagrees with the sidecar ({where})")
        if raw["zone_screen_disclaimer"] != DISCLAIMER:
            raise SweepError(f"zone_screen_disclaimer does not match the engine string ({where})")
        if raw["branch_sign"] not in ("1", "-1", "1.0", "-1.0"):
            raise SweepError(f"branch_sign must be one of 1, -1, 1.0, -1.0, "
                             f"got {raw['branch_sign']!r} ({where})")
        branch_sign = float(raw["branch_sign"])
        params = [_parse_float(raw[name], where) for name in geometry_columns]
        geometry_valid = _parse_bool(raw["zone_screen_geometry_valid"], where)
        row = {
            "candidate_id": candidate_id,
            "branch_sign": branch_sign,
            "params": params,
            "base_angle": params[8],
            "geometry_valid": geometry_valid,
        }
        if not geometry_valid:
            row["class"] = "invalid"
            row["recorded"] = None
            rows.append(row)
            continue
        if any(value <= 0.0 for value in params[:4]):
            raise SweepError(f"link lengths must be positive when geometry is valid ({where})")
        if not 0.0 <= row["base_angle"] <= TWO_PI:
            raise SweepError(f"base_angle must lie in [0, 2*pi], got "
                             f"{row['base_angle']!r} ({where})")
        window_count = _parse_int(raw[f"{prefix}_windows"], where)
        if window_count < 0:
            raise SweepError(f"window count must be non-negative ({where})")
        total_width = _parse_float(raw[f"{prefix}_total_width_deg"], where)
        if total_width < 0.0:
            raise SweepError(f"total width must be non-negative ({where})")
        starts = _parse_window_list(raw[f"{prefix}_window_starts_deg"], where)
        ends = _parse_window_list(raw[f"{prefix}_window_ends_deg"], where)
        if len(starts) != window_count or len(ends) != window_count:
            raise SweepError(f"window list lengths disagree with the window count ({where})")
        recomputed_width = window_total_width(list(zip(starts, ends)), config["steps"])
        if recomputed_width != total_width:
            raise SweepError(f"recorded total_width {total_width!r} disagrees with the "
                             f"recorded windows ({recomputed_width!r}) ({where})")
        acceptable = _parse_bool(raw[f"{prefix}_acceptable"], where)
        overall_acceptable = _parse_bool(raw["zone_screen_acceptable"], where)
        if entry_pass(entry, window_count, total_width) != acceptable:
            raise SweepError(f"per-region acceptable flag disagrees with the sidecar "
                             f"criteria ({where})")
        if acceptable != overall_acceptable:
            raise SweepError(f"overall acceptable flag disagrees with the single hard "
                             f"entry ({where})")
        if window_count == 0:
            row_class = "never"
        elif window_count == 1 and total_width == 360.0:
            row_class = "full360"
        elif total_width <= cap:
            row_class = "quick_pass"
        else:
            row_class = "drag_over_cap"
        row["class"] = row_class
        row["recorded"] = {
            "windows": window_count,
            "total_width": total_width,
            "starts": starts,
            "ends": ends,
            "acceptable": acceptable,
        }
        rows.append(row)
    return rows


# ======================================================================
# ===== sweep driver ====================================================
# ======================================================================

def _compare(recorded, resolved_regions, region_id):
    """Exact window-list comparison of one frame against the recorded row."""
    if region_id not in resolved_regions:
        return False, None
    starts = [float(start) for start, _ in resolved_regions[region_id]["windows"]]
    ends = [float(end) for _, end in resolved_regions[region_id]["windows"]]
    if starts == recorded["starts"] and ends == recorded["ends"]:
        return True, 0.0
    delta = None
    if len(starts) == len(recorded["starts"]) and starts:
        delta = max(max(abs(a - b) for a, b in zip(starts, recorded["starts"])),
                    max(abs(a - b) for a, b in zip(ends, recorded["ends"])))
    return False, delta


def run_sweep(corpus_root, out_dir, *, expected_tallies, expected_class_counts,
              expected_cap, expected_steps, allowed_task_ids, label,
              expected_pairs=None):
    started = time.monotonic()
    corpus = Path(corpus_root)
    if not corpus.is_dir():
        raise SweepError(f"corpus root not found: {corpus}")
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise SweepError(f"output directory already exists (never overwrite): {out_dir}")
    expected_pairs = expected_pairs if expected_pairs is not None else set(expected_tallies)
    variant_dirs = sorted(
        child for child in corpus.iterdir()
        if child.is_dir() and re.fullmatch(r"corpus_pair_\d{2}", child.name))
    tallies = {}
    class_counts = Counter()
    per_class = {name: {"rows": 0, "screen_exact": 0, "plain_exact": 0}
                 for name in CLASS_ORDER}
    per_task = {}
    plain_exact_rows = []
    near_misses = []
    output_rows = []
    sidecar_count = 0
    for variant_dir in variant_dirs:
        variant = variant_dir.name
        plan_path = variant_dir / "plan" / "run_plan.json"
        if not plan_path.is_file():
            raise SweepError(f"run plan not found: {plan_path}")
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SweepError(f"unreadable run plan {plan_path} ({error})")
        if (not isinstance(plan, dict) or not isinstance(plan.get("runs"), list)
                or not plan["runs"]):
            raise SweepError(f"run plan has no runs: {plan_path}")
        for run in plan["runs"]:
            if not isinstance(run, dict):
                raise SweepError(f"run plan entry is not an object: {plan_path}")
            task_id = run.get("task_id")
            if task_id not in allowed_task_ids:
                raise SweepError(f"unexpected task_id {task_id!r} in {plan_path}")
            if "zone_screen_file" not in run:
                raise SweepError(f"run entry for {task_id!r} has no zone_screen_file "
                                 f"(unsreened corpus?): {plan_path}")
            if "output_root" not in run:
                raise SweepError(f"run entry for {task_id!r} has no output_root: {plan_path}")
            pair = (variant, task_id)
            if pair not in expected_pairs:
                raise SweepError(f"unexpected (variant, task) pair {pair}")
            if pair in tallies:
                raise SweepError(f"duplicate (variant, task) pair {pair}")
            context = f"{variant}/{task_id}"
            sidecar_path = variant_dir / "plan" / run["zone_screen_file"]
            config = load_sidecar(sidecar_path)
            sidecar_count += 1
            if len(config["regions"]) != 1 or len(config["screen"]) != 1:
                raise SweepError(f"expected exactly one region and one screen entry "
                                 f"({context})")
            entry = config["screen"][0]
            if entry["mode"] != "hard":
                raise SweepError(f"expected a hard screen entry ({context})")
            if entry.get("max_total_width_deg") != expected_cap:
                raise SweepError(f"sidecar cap {entry.get('max_total_width_deg')!r} != "
                                 f"expected {expected_cap!r} ({context})")
            if config["steps"] != expected_steps:
                raise SweepError(f"sidecar steps {config['steps']} != expected "
                                 f"{expected_steps} ({context})")
            region_id = entry["region"]
            run_root = variant_dir / "plan" / run["output_root"]
            target_dir = find_target_dir(run_root, context)
            rows = read_rows(target_dir / "all_candidates.csv", config, region_id, context)
            tallies[pair] = len(rows)
            task_stats = {"rows": len(rows), "screen_exact": 0, "plain_exact": 0}
            for row in rows:
                class_counts[row["class"]] += 1
                per_class[row["class"]]["rows"] += 1
                params = row["params"]
                branch = row["branch_sign"]
                if row["recorded"] is None:
                    # invalid rows carry no windows; both frames must agree
                    # the row is invalid, which is base-independent.
                    screen = resolve(params, branch, config, math.radians(row["base_angle"]))
                    plain = resolve(params, branch, config, row["base_angle"])
                    screen_exact = screen["geometry_valid"] is False
                    plain_exact = plain["geometry_valid"] is False
                    screen_delta = plain_delta = 0.0
                else:
                    screen = resolve(params, branch, config, math.radians(row["base_angle"]))
                    plain = resolve(params, branch, config, row["base_angle"])
                    if not screen["geometry_valid"]:
                        raise SweepError(
                            f"recorded geometry_valid True but the screen frame does not "
                            f"assemble: {row['candidate_id']} ({context})")
                    screen_exact, screen_delta = _compare(row["recorded"],
                                                          screen["regions"], region_id)
                    plain_exact, plain_delta = _compare(row["recorded"],
                                                        plain["regions"], region_id)
                row_result = {
                    "variant": variant,
                    "task": task_id,
                    "candidate_id": row["candidate_id"],
                    "class": row["class"],
                    "base_angle": row["base_angle"],
                    "windows": row["recorded"]["windows"] if row["recorded"] else "",
                    "total_width_deg": row["recorded"]["total_width"] if row["recorded"] else "",
                    "screen_exact": screen_exact,
                    "plain_exact": plain_exact,
                    "screen_delta_deg": "" if screen_exact else
                        ("" if screen_delta is None else repr(screen_delta)),
                    "plain_delta_deg": "" if plain_exact else
                        ("" if plain_delta is None else repr(plain_delta)),
                }
                output_rows.append(row_result)
                if screen_exact:
                    task_stats["screen_exact"] += 1
                if plain_exact:
                    task_stats["plain_exact"] += 1
                if plain_exact and row["class"] in ("quick_pass", "drag_over_cap", "full360"):
                    plain_exact_rows.append({
                        "variant": variant, "task": task_id,
                        "candidate_id": row["candidate_id"], "class": row["class"],
                        "base_angle": row["base_angle"],
                        "windows": row["recorded"]["windows"] if row["recorded"] else 0,
                    })
                if not screen_exact:
                    near_misses.append({
                        "variant": variant, "task": task_id,
                        "candidate_id": row["candidate_id"], "class": row["class"],
                        "screen_delta_deg": screen_delta,
                    })
                if screen_exact:
                    per_class[row["class"]]["screen_exact"] += 1
                if plain_exact:
                    per_class[row["class"]]["plain_exact"] += 1
            per_task[f"{variant}/{task_id}"] = task_stats
            print(f"  {context}: {len(rows)} rows, "
                  f"screen_exact {task_stats['screen_exact']}/{len(rows)}", flush=True)
    # ---- fail-closed tallies and class checks ----
    if tallies != expected_tallies:
        differences = {key: (tallies.get(key), expected_tallies.get(key))
                       for key in set(tallies) | set(expected_tallies)
                       if tallies.get(key) != expected_tallies.get(key)}
        raise SweepError(f"per-task row tallies disagree with the recorded constants: "
                         f"{sorted(differences.items())}")
    observed_classes = {name: class_counts.get(name, 0) for name in CLASS_ORDER}
    if observed_classes != expected_class_counts:
        raise SweepError(f"pooled occupancy classes disagree with the recorded constants: "
                         f"{observed_classes} != {expected_class_counts}")
    total_rows = sum(tallies.values())
    screen_exact_total = sum(1 for row in output_rows if row["screen_exact"])
    plain_exact_total = sum(1 for row in output_rows if row["plain_exact"])
    # ---- write outputs ----
    out_dir.mkdir(parents=True, exist_ok=False)
    csv_path = out_dir / "frame_sweep.csv"
    fieldnames = ["variant", "task", "candidate_id", "class", "base_angle", "windows",
                  "total_width_deg", "screen_exact", "plain_exact",
                  "screen_delta_deg", "plain_delta_deg"]
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    summary = {
        "label": label,
        "method": "frame_sweep_v1",
        "corpus_root": str(corpus),
        "frames": {
            "screen": "base = radians(base_angle) (engine zone_screen.screen behavior)",
            "plain": "base = base_angle as stored (radians)",
        },
        "engine_observation": (
            "decode_refinement_variables stores base_angle in radians via "
            "remainder(raw[8], 2*pi); zone_screen.screen() applies math.radians() "
            "again. Recorded as an engine observation, not a claimed convention."
        ),
        "resolver_mirrors": (
            "src/mechanism_generator/engine/zone_screen.py::screen(), pure stdlib, "
            "same operation order; engine files identical between f3ebca9a "
            "(the corpus-07 run commit) and 12badcb7 (PR #31 was docs-only)"
        ),
        "sidecars_parsed": sidecar_count,
        "total_rows": total_rows,
        "screen_exact": screen_exact_total,
        "plain_exact": plain_exact_total,
        "per_class": per_class,
        "per_task": per_task,
        "plain_exact_rows": plain_exact_rows,
        "screen_frame_mismatches": near_misses,
        "expected": {
            "tallies": {f"{variant}/{task}": count for (variant, task), count
                        in sorted(expected_tallies.items())},
            "class_counts": expected_class_counts,
            "steps": expected_steps,
            "cap_deg": expected_cap,
        },
        "disclaimer": DISCLAIMER,
        "runtime_seconds": round(time.monotonic() - started, 1),
    }
    (out_dir / "frame_sweep_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    by_class_lines = [
        f"  {name}: {per_class[name]['rows']} rows, "
        f"screen_exact {per_class[name]['screen_exact']}, "
        f"plain_exact {per_class[name]['plain_exact']}"
        for name in CLASS_ORDER
    ]
    report_lines = [
        f"# Frame sweep report: {label}",
        "",
        f"Corpus: {corpus}",
        f"Sidecars parsed: {sidecar_count}",
        f"Candidate rows: {total_rows} (tallies and pooled classes matched the "
        f"recorded constants)",
        "",
        "## Screen frame (base = radians(base_angle))",
        "",
        f"{screen_exact_total}/{total_rows} rows reproduce the recorded windows "
        f"exactly.",
        "",
        "## Plain frame (base = base_angle as stored; control)",
        "",
        f"{plain_exact_total}/{total_rows} rows match the recorded windows "
        f"exactly. Matches among rows with non-empty windows are listed in "
        f"frame_sweep_summary.json (plain_exact_rows); never-class rows can "
        f"match trivially when both frames leave the zone untouched, and "
        f"rows with base_angle near zero make the two frames nearly "
        f"identical by construction.",
        "",
        "## Per class",
        "",
        *by_class_lines,
        "",
        "## Honest disclosure",
        "",
        "- The screen-frame reproduction is a numerical consequence of the recorded",
        "  engine behavior (double radians conversion); it is not evidence that the",
        "  screen frame is the physically intended one.",
        "- Windows are sampled at 360/steps degrees; nothing is claimed between",
        f"  samples. {DISCLAIMER}",
        "- A row that fails to reproduce in the screen frame is reported as data",
        "  (screen_frame_mismatches), not silently dropped.",
        "",
    ]
    (out_dir / "frame_sweep_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    return summary


def main():
    print(f"Frame sweep over {CORPUS_ROOT} "
          f"(screen vs plain base-angle frames, all candidate rows)", flush=True)
    summary = run_sweep(
        CORPUS_ROOT, OUT_DIR,
        expected_tallies=EXPECTED_TALLIES,
        expected_class_counts=EXPECTED_CLASS_COUNTS,
        expected_cap=EXPECTED_CAP,
        expected_steps=EXPECTED_STEPS,
        allowed_task_ids=TASK_IDS,
        label="corpus-07 frame sweep (menu E follow-up)",
    )
    total = summary["total_rows"]
    print()
    print(f"sidecars parsed: {summary['sidecars_parsed']}/{len(EXPECTED_TALLIES)} PASS")
    print(f"rows read: {total} (tallies PASS {len(EXPECTED_TALLIES)}/{len(EXPECTED_TALLIES)})")
    counts = {name: summary["per_class"][name]["rows"] for name in CLASS_ORDER}
    print(f"pooled classes: " + ", ".join(f"{name} {counts[name]}" for name in CLASS_ORDER)
          + " PASS")
    print(f"screen frame: {summary['screen_exact']}/{total} rows reproduce recorded "
          f"windows exactly"
          + (" PASS" if summary["screen_exact"] == total else
             " -- see frame_sweep.csv (prediction was all rows)"))
    print(f"plain frame (control): {summary['plain_exact']}/{total} rows match")
    print(f"outputs: {OUT_DIR}/ (frame_sweep.csv, frame_sweep_summary.json, "
          f"frame_sweep_report.txt)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SweepError as error:
        print(f"ABORT: {error}", file=sys.stderr)
        raise SystemExit(2)
