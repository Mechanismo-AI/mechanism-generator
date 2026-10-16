#!/usr/bin/env python3
"""OMTS timeline animator (menu item E) for the corpus-07 occupancy classes.

Reads the corpus-07 engine trees (menu-B digest traversal), fail-closed
verifies every candidate row against the recorded zone-screen sidecars and
the recorded menu-B/menu-C tallies, picks one deterministic exemplar per
occupancy-class group, re-resolves each exemplar's occupancy in BOTH
base-angle frames (keeping the frame that reproduces the recorded
windows), re-validates assembly at every sampled phase, and writes a
self-contained HTML animator plus a JSON meta side-record.

Sampled, never certified: this is an explorer tool for the timing
structure of the occupancy classes; it makes no new physics claim.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants (recorded corpus facts; menu-B digest + menu-C class analysis)
# ---------------------------------------------------------------------------

CORPUS_ROOT = Path("runs/sync-corpus-07")
VARIANTS = tuple(f"corpus_pair_{index:02d}" for index in range(1, 7))
OUT_DIR = Path("runs/analysis/animation-e01")
HTML_NAME = "timeline_animator.html"
META_NAME = "anim_e_meta.json"

METHOD = "sampled_collision_geometry_v1"
DISCLAIMER = ("Sampled, not certified; no between-sample guarantee; not "
              "collision, thickness or machinery certification.")

# Engine run directories contain both target dirs (NNNN_label) and a
# contribution/ bundle dir (bundle.json + review.html, no CSVs). Only the
# engine target-dir naming pattern carries candidate CSVs.
TARGET_DIR_PATTERN = re.compile(r"\d{4,}_.+")

SIDECAR_KEYS = ("method", "task", "steps", "thickness", "carrier",
                "regions", "screen", "note", "disclaimer")
REGION_KEYS = ("id", "name", "notes", "shape", "min", "max", "center", "radius")
SCREEN_KEYS = ("region", "avoid", "max_total_width_deg", "max_windows",
               "mode", "notes")
SCREEN_MODES = ("hard", "soft", "report_only")
PARAM_NAMES = ("l1", "l2", "l3", "l4", "S_ratio", "bar_length",
               "base_x", "base_y", "base_angle")

# Recorded menu-B pre-dedup row tallies per (variant, task).
EXPECTED_TALLIES = {
    ("corpus_pair_01", "gate"): 42,
    ("corpus_pair_01", "catcher"): 38,
    ("corpus_pair_02", "gate"): 42,
    ("corpus_pair_02", "catcher"): 42,
    ("corpus_pair_03", "gate"): 42,
    ("corpus_pair_03", "catcher"): 42,
    ("corpus_pair_04", "gate"): 42,
    ("corpus_pair_04", "catcher"): 42,
    ("corpus_pair_05", "gate"): 41,
    ("corpus_pair_05", "catcher"): 42,
    ("corpus_pair_06", "gate"): 42,
    ("corpus_pair_06", "catcher"): 42,
}

# Recorded menu-C pooled occupancy-class counts.
EXPECTED_CLASS_COUNTS = {
    "never": 53,
    "quick_pass": 192,
    "drag_over_cap": 246,
    "full360": 8,
    "screen_geometry_invalid": 0,
}

# One deterministic exemplar per group (variant, task, class).
EXEMPLAR_GROUPS = (
    ("corpus_pair_06", "gate", "never"),
    ("corpus_pair_01", "catcher", "never"),
    ("corpus_pair_03", "catcher", "drag_over_cap"),
    ("corpus_pair_01", "gate", "drag_over_cap"),
    ("corpus_pair_02", "catcher", "quick_pass"),
    ("corpus_pair_01", "gate", "full360"),
)


class FailClosed(Exception):
    """Any missing file/column/field/mismatch aborts loudly."""


# ---------------------------------------------------------------------------
# Geometry kernel (mirrors engine zone_screen.py exactly, pure stdlib)
# ---------------------------------------------------------------------------

def _seg_point_distance(px, py, qx, qy, x, y):
    """Distance from point (x, y) to segment PQ."""
    dx, dy = qx - px, qy - py
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0:
        t = 0.0
    else:
        t = ((x - px) * dx + (y - py) * dy) / length_sq
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(x - (px + t * dx), y - (py + t * dy))


def _circle_region_distance(cx, cy, radius, px, py, qx, qy):
    """Distance from segment PQ to a circle region; 0.0 when it reaches it."""
    return max(0.0, _seg_point_distance(px, py, qx, qy, cx, cy) - radius)


def skeleton_phases(params, branch_sign, base_rad, steps):
    """Per-phase four-bar skeleton in the given frame.

    Mirrors zone_screen.screen(): O2 = (base_x, base_y), O4 = O2 + l1 in
    direction base, A = O2 + l2 in direction theta + base, B via the
    circle-circle construction, coupler point P = A + s(B - A) + bar * v.
    Returns a list of (ax, ay, bx, by, px, py, ux, uy) per phase, or None
    when any sampled phase is undefined or non-finite (occupancy is never
    guessed, exactly as the engine never guesses it).
    """
    l1, l2, l3, l4, s_ratio, bar, base_x, base_y, _ = params
    o2x, o2y = base_x, base_y
    o4x = o2x + l1 * math.cos(base_rad)
    o4y = o2y + l1 * math.sin(base_rad)
    phases = []
    for index in range(steps):
        theta = 2.0 * math.pi * index / steps
        ax = o2x + l2 * math.cos(theta + base_rad)
        ay = o2y + l2 * math.sin(theta + base_rad)
        dx = ax - o4x
        dy = ay - o4y
        distance = math.hypot(dx, dy)
        if distance <= 0.0 or distance > l3 + l4 or distance < abs(l3 - l4):
            return None
        unit_x = dx / distance
        unit_y = dy / distance
        along = (l4 * l4 - l3 * l3 + distance * distance) / (2.0 * distance)
        height_sq = l4 * l4 - along * along
        height = math.sqrt(height_sq if height_sq > 0.0 else 0.0)
        bx = o4x + along * unit_x + branch_sign * height * (-unit_y)
        by = o4y + along * unit_y + branch_sign * height * unit_x
        ux = (bx - ax) / l3
        uy = (by - ay) / l3
        vx = -uy
        vy = ux
        px = ax + s_ratio * (bx - ax) + bar * vx
        py = ay + s_ratio * (by - ay) + bar * vy
        if not all(math.isfinite(value) for value in (ax, ay, bx, by, px, py)):
            return None
        phases.append((ax, ay, bx, by, px, py, ux, uy))
    return phases


def occupancy_flags(region, params, branch_sign, base_rad, steps, thickness,
                    carrier):
    """Sampled occupancy of the circle region against all declared bodies.

    Mirrors zone_screen.screen()/_occupancy_flags: body segments are the
    crank O2-A, the coupler A-B, the rocker O4-B, plus the four carrier
    edges; a body reaches the region when any segment comes within
    `thickness` of the circle or the region anchor lies inside the carrier
    rectangle. Returns (flags, phases): flags is None when the candidate is
    invalid in this frame (bad parameters or undefined assembly), exactly
    as the engine records geometry_valid False with no windows.
    """
    values = [float(value) for value in params]
    if len(values) != 9 or not all(math.isfinite(v) for v in values):
        return None, None
    if any(v <= 0.0 for v in values[:4]) or branch_sign not in (-1, 1):
        return None, None
    phases = skeleton_phases(values, branch_sign, base_rad, steps)
    if phases is None:
        return None, None
    l1, l2, l3, l4, s_ratio, bar, base_x, base_y, _ = values
    o2x, o2y = base_x, base_y
    o4x = o2x + l1 * math.cos(base_rad)
    o4y = o2y + l1 * math.sin(base_rad)
    cx, cy = region["center"]
    radius = region["radius"]
    flags = []
    for ax, ay, bx, by, px, py, ux, uy in phases:
        vx = -uy
        vy = ux
        occupied = False
        for sx, sy, ex, ey in ((o2x, o2y, ax, ay), (ax, ay, bx, by),
                               (o4x, o4y, bx, by)):
            if _circle_region_distance(cx, cy, radius, sx, sy, ex, ey) <= thickness:
                occupied = True
                break
        if occupied is False and carrier is not None:
            width, depth = carrier
            corners = []
            for half_w, half_d in ((width / 2.0, depth / 2.0),
                                   (width / 2.0, -depth / 2.0),
                                   (-width / 2.0, -depth / 2.0),
                                   (-width / 2.0, depth / 2.0)):
                corners.append((px + half_w * ux + half_d * vx,
                                py + half_w * uy + half_d * vy))
            for edge in range(4):
                first = corners[edge]
                second = corners[(edge + 1) % 4]
                if _circle_region_distance(cx, cy, radius,
                                            first[0], first[1],
                                            second[0], second[1]) <= thickness:
                    occupied = True
                    break
            if occupied is False:
                dx = cx - px
                dy = cy - py
                if (abs(dx * ux + dy * uy) <= width / 2.0
                        and abs(dx * vx + dy * vy) <= depth / 2.0):
                    occupied = True
        flags.append(occupied)
    return flags, phases


def windows_from_flags(flags):
    """Contiguous True runs of the circular flag array, in degrees.

    Mirrors zone_screen._windows exactly, including the all-occupied
    single window and the wrap merge through zero.
    """
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


def window_width(start, end, step_deg):
    return (end - start) % 360.0 + step_deg


def window_total(windows, step_deg):
    return float(sum(window_width(start, end, step_deg) for start, end in windows))


def derive_class(geometry_valid, windows, total, step_deg, cap_deg):
    """Class derivation in the recorded order: invalid -> never -> full360
    -> quick (at or under the sidecar cap) -> drag."""
    if not geometry_valid:
        return "screen_geometry_invalid"
    if len(windows) == 0:
        return "never"
    if (len(windows) == 1
            and abs(windows[0][0]) <= 1e-9
            and abs(windows[0][1] - (360.0 - step_deg)) <= 1e-6
            and total >= 360.0 - step_deg / 2.0):
        return "full360"
    if total <= cap_deg + 1e-9:
        return "quick_pass"
    return "drag_over_cap"


# ---------------------------------------------------------------------------
# Sidecar parsing (fail-closed, exact-subset keys, mirrors the engine parser)
# ---------------------------------------------------------------------------

def _finite(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def parse_sidecar(path):
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FailClosed(f"zone screen sidecar must be readable JSON: {path} ({error}).")
    if not isinstance(document, dict):
        raise FailClosed(f"zone screen sidecar must be a JSON object: {path}.")
    unknown = sorted(set(document) - set(SIDECAR_KEYS))
    if unknown:
        raise FailClosed(f"zone screen sidecar has unsupported keys: {', '.join(unknown)}.")
    if document.get("method") != METHOD:
        raise FailClosed(f"zone screen sidecar method must be {METHOD!r}: {path}.")
    steps = document.get("steps")
    if (isinstance(steps, bool) or not isinstance(steps, int)
            or not 361 <= steps <= 72001):
        raise FailClosed(f"zone screen sampling requires an integer step count between 361 and 72001: {path}.")
    thickness = document.get("thickness")
    if not _finite(thickness) or thickness < 0:
        raise FailClosed(f"zone screen thickness must be a non-negative finite number: {path}.")
    carrier = None
    if "carrier" in document:
        raw = document["carrier"]
        if (not isinstance(raw, dict) or set(raw) != {"width", "depth"}
                or not all(_finite(value) and value > 0 for value in raw.values())):
            raise FailClosed(f"zone screen carrier needs positive finite width and depth: {path}.")
        carrier = (float(raw["width"]), float(raw["depth"]))
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise FailClosed(f"zone screen sidecar requires a non-empty regions list: {path}.")
    if len(raw_regions) != 1:
        raise FailClosed(f"this animator supports exactly one region per task, found {len(raw_regions)}: {path}.")
    region = raw_regions[0]
    if not isinstance(region, dict):
        raise FailClosed(f"zone screen region must be an object: {path}.")
    unknown = sorted(set(region) - set(REGION_KEYS))
    if unknown:
        raise FailClosed(f"zone screen region has unsupported keys: {', '.join(unknown)}: {path}.")
    region_id = region.get("id")
    if not isinstance(region_id, str) or not region_id:
        raise FailClosed(f"zone screen region needs a non-empty string id: {path}.")
    if region.get("shape") != "circle":
        raise FailClosed(f"this animator supports circle regions only, region {region_id!r} has shape {region.get('shape')!r}: {path}.")
    center = region.get("center")
    radius = region.get("radius")
    if (not isinstance(center, list) or len(center) != 2
            or not all(_finite(value) for value in center)
            or not _finite(radius) or radius <= 0):
        raise FailClosed(f"circle region {region_id!r} needs a two-component finite center and a positive radius: {path}.")
    raw_screen = document.get("screen")
    if not isinstance(raw_screen, list) or not raw_screen:
        raise FailClosed(f"zone screen sidecar requires a non-empty screen list: {path}.")
    if len(raw_screen) != 1:
        raise FailClosed(f"this animator supports exactly one screen entry per task, found {len(raw_screen)}: {path}.")
    entry = raw_screen[0]
    if not isinstance(entry, dict):
        raise FailClosed(f"zone screen entry must be an object: {path}.")
    unknown = sorted(set(entry) - set(SCREEN_KEYS))
    if unknown:
        raise FailClosed(f"zone screen entry has unsupported keys: {', '.join(unknown)}: {path}.")
    if entry.get("region") != region_id:
        raise FailClosed(f"zone screen entry references region {entry.get('region')!r}, expected {region_id!r}: {path}.")
    mode = entry.get("mode", "hard")
    if mode not in SCREEN_MODES:
        raise FailClosed(f"zone screen mode must be one of {SCREEN_MODES!r}: {path}.")
    if not any(key in entry for key in ("avoid", "max_total_width_deg", "max_windows")):
        raise FailClosed(f"zone screen entry for {region_id!r} requires at least one criterion: {path}.")
    if "max_total_width_deg" not in entry:
        raise FailClosed(f"this animator requires a max_total_width_deg criterion (the quick/drag cap), region {region_id!r}: {path}.")
    cap = entry["max_total_width_deg"]
    if not _finite(cap) or not 0 <= cap <= 360:
        raise FailClosed(f"zone screen max_total_width_deg must be a finite value within [0, 360]: {path}.")
    avoid = entry.get("avoid", False)
    if not isinstance(avoid, bool):
        raise FailClosed(f"zone screen avoid must be a boolean: {path}.")
    max_windows = entry.get("max_windows")
    if max_windows is not None:
        if isinstance(max_windows, bool) or not isinstance(max_windows, int) or max_windows < 0:
            raise FailClosed(f"zone screen max_windows must be a non-negative integer: {path}.")
    return {
        "path": str(path),
        "method": METHOD,
        "region_id": region_id,
        "region": {"center": [float(center[0]), float(center[1])], "radius": float(radius)},
        "steps": steps,
        "step_deg": 360.0 / steps,
        "thickness": float(thickness),
        "carrier": carrier,
        "mode": mode,
        "avoid": avoid,
        "cap": float(cap),
        "max_windows": max_windows,
        "task": document.get("task"),
    }


# ---------------------------------------------------------------------------
# Candidate row parsing and verification
# ---------------------------------------------------------------------------

def parse_bool(value, label):
    if value == "True":
        return True
    if value == "False":
        return False
    raise FailClosed(f"unknown boolean label {value!r} for {label}.")


def parse_floats(value, label):
    if value is None or value == "":
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise FailClosed(f"{label} must be a JSON list of numbers ({error}).")
    if not isinstance(parsed, list) or not all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            and math.isfinite(item) for item in parsed):
        raise FailClosed(f"{label} must be a JSON list of finite numbers.")
    return [float(item) for item in parsed]


def parse_float(value, label):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise FailClosed(f"{label} must be a number, got {value!r}.")
    if not math.isfinite(parsed):
        raise FailClosed(f"{label} must be a finite number, got {value!r}.")
    return parsed


def parse_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise FailClosed(f"{label} must be an integer, got {value!r}.")
    return parsed


def row_required_columns(sidecar):
    prefix = f"zone_screen_{sidecar['region_id']}"
    columns = ["candidate_id", "branch_sign", *PARAM_NAMES,
               "zone_screen_required", "zone_screen_method",
               "zone_screen_steps", "zone_screen_thickness",
               "zone_screen_geometry_valid", "zone_screen_acceptable",
               "zone_screen_disclaimer",
               f"{prefix}_windows", f"{prefix}_total_width_deg",
               f"{prefix}_acceptable",
               f"{prefix}_window_starts_deg", f"{prefix}_window_ends_deg"]
    return columns


def acceptable_recompute(sidecar, windows, total):
    """Mirror of the engine's hard-screen acceptable evaluation."""
    count = len(windows)
    entry_ok = True
    if sidecar["avoid"]:
        entry_ok = entry_ok and count == 0
    entry_ok = entry_ok and total <= sidecar["cap"] + 1e-9
    if sidecar["max_windows"] is not None:
        entry_ok = entry_ok and count <= sidecar["max_windows"]
    if sidecar["mode"] != "hard":
        return True
    return bool(entry_ok)


def parse_row(raw, sidecar, where):
    """Parse and fail-closed verify one CSV row; returns the row record."""
    prefix = f"zone_screen_{sidecar['region_id']}"
    if raw.get("candidate_id") in (None, ""):
        raise FailClosed(f"missing candidate_id in {where}.")
    candidate_id = raw["candidate_id"]
    label = f"{where} candidate {candidate_id}"
    if raw.get("zone_screen_required") != "True":
        raise FailClosed(f"zone_screen_required must be True for {label}.")
    if raw.get("zone_screen_method") != sidecar["method"]:
        raise FailClosed(f"zone_screen_method mismatch for {label}: "
                         f"{raw.get('zone_screen_method')!r} vs sidecar {sidecar['method']!r}.")
    steps = parse_int(raw.get("zone_screen_steps"), f"zone_screen_steps for {label}")
    if steps != sidecar["steps"]:
        raise FailClosed(f"zone_screen_steps mismatch for {label}: {steps} vs sidecar {sidecar['steps']}.")
    thickness = parse_float(raw.get("zone_screen_thickness"), f"zone_screen_thickness for {label}")
    if abs(thickness - sidecar["thickness"]) > 1e-9:
        raise FailClosed(f"zone_screen_thickness mismatch for {label}: {thickness} vs sidecar {sidecar['thickness']}.")
    if raw.get("zone_screen_disclaimer") in (None, ""):
        raise FailClosed(f"zone_screen_disclaimer must be non-empty for {label}.")
    geometry_valid = parse_bool(raw.get("zone_screen_geometry_valid"), f"zone_screen_geometry_valid for {label}")
    acceptable = parse_bool(raw.get("zone_screen_acceptable"), f"zone_screen_acceptable for {label}")
    branch_text = raw.get("branch_sign")
    # The engine stores branch_sign as a float in the candidate dict, so the
    # CSV serializes it as "1.0"/"-1.0"; older tooling wrote "1"/"-1". Both
    # exact labels are accepted; anything else aborts.
    if branch_text not in ("1", "-1", "1.0", "-1.0"):
        raise FailClosed(f"branch_sign must be 1 or -1 for {label}, got {branch_text!r}.")
    branch_sign = 1 if branch_text in ("1", "1.0") else -1
    params = []
    for name in PARAM_NAMES:
        params.append(parse_float(raw.get(name), f"{name} for {label}"))
    step_deg = sidecar["step_deg"]

    if not geometry_valid:
        for key in (f"{prefix}_windows", f"{prefix}_total_width_deg",
                    f"{prefix}_acceptable", f"{prefix}_window_starts_deg",
                    f"{prefix}_window_ends_deg"):
            if raw.get(key) not in (None, ""):
                raise FailClosed(f"{key} must be empty when geometry is invalid for {label}.")
        return {
            "candidate_id": candidate_id, "params": params,
            "branch_sign": branch_sign, "geometry_valid": False,
            "acceptable": acceptable, "windows": [], "total": 0.0,
            "cls": "screen_geometry_invalid",
        }

    # geometry_valid True: params must be engine-plausible.
    if any(value <= 0.0 for value in params[:4]):
        raise FailClosed(f"geometry_valid is True but l1..l4 are not all positive for {label}.")

    count = parse_int(raw.get(f"{prefix}_windows"), f"{prefix}_windows for {label}")
    if count < 0:
        raise FailClosed(f"{prefix}_windows must be non-negative for {label}.")
    starts = parse_floats(raw.get(f"{prefix}_window_starts_deg"), f"{prefix}_window_starts_deg for {label}")
    ends = parse_floats(raw.get(f"{prefix}_window_ends_deg"), f"{prefix}_window_ends_deg for {label}")
    if len(starts) != count or len(ends) != count:
        raise FailClosed(f"window start/end list lengths must equal the window count for {label}: "
                         f"{len(starts)}/{len(ends)} vs {count}.")
    windows = []
    for start, end in zip(starts, ends):
        if not (0.0 <= start < 360.0) or not (0.0 <= end < 360.0):
            raise FailClosed(f"window edges must lie in [0, 360) for {label}: ({start}, {end}).")
        windows.append((start, end))
    total_recorded = parse_float(raw.get(f"{prefix}_total_width_deg"), f"{prefix}_total_width_deg for {label}")
    total_recomputed = window_total(windows, step_deg)
    if abs(total_recomputed - total_recorded) > 1e-6:
        raise FailClosed(f"window width sum mismatch for {label}: recorded {total_recorded} "
                         f"vs recomputed {total_recomputed} from edges.")
    acceptable_recomputed = acceptable_recompute(sidecar, windows, total_recorded)
    if acceptable_recomputed != acceptable:
        raise FailClosed(f"zone screen acceptable mismatch for {label}: recorded {acceptable} "
                         f"vs recomputed {acceptable_recomputed} (windows {count}, total {total_recorded}, "
                         f"cap {sidecar['cap']}, avoid {sidecar['avoid']}, mode {sidecar['mode']}).")
    acceptable_region = parse_bool(raw.get(f"{prefix}_acceptable"), f"{prefix}_acceptable for {label}")
    if acceptable_region != acceptable_recomputed:
        raise FailClosed(f"per-region acceptable mismatch for {label}: recorded {acceptable_region} "
                         f"vs recomputed {acceptable_recomputed}.")
    cls = derive_class(True, windows, total_recorded, step_deg, sidecar["cap"])
    return {
        "candidate_id": candidate_id, "params": params,
        "branch_sign": branch_sign, "geometry_valid": True,
        "acceptable": acceptable, "windows": windows,
        "total": total_recorded, "cls": cls,
    }


# ---------------------------------------------------------------------------
# Corpus traversal (menu-B digest traversal)
# ---------------------------------------------------------------------------

def read_rows(csv_path, sidecar, variant, task_id, target_dir):
    try:
        with open(csv_path, newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            header = reader.fieldnames
            if not header:
                raise FailClosed(f"candidate CSV has no header: {csv_path}.")
            missing = [name for name in row_required_columns(sidecar) if name not in header]
            if missing:
                raise FailClosed(f"missing columns: {', '.join(missing)} in {csv_path}.")
            rows = []
            for raw in reader:
                where = f"{variant}/{task_id}/{target_dir}"
                rows.append(parse_row(raw, sidecar, where))
    except OSError as error:
        raise FailClosed(f"cannot read candidate CSV: {csv_path} ({error}).")
    return rows


def read_task(plan_dir, run, variant):
    for key in ("task_id", "output_root", "targets_file", "zone_screen_file"):
        if key not in run:
            raise FailClosed(f"run_plan entry is missing key {key!r} in {plan_dir}.")
    sidecar = parse_sidecar(Path(plan_dir) / run["zone_screen_file"])
    if sidecar["task"] is not None and sidecar["task"] != run["task_id"]:
        raise FailClosed(f"zone screen sidecar task {sidecar['task']!r} does not match "
                         f"run task_id {run['task_id']!r} in {plan_dir}.")
    results_root = Path(plan_dir) / run["output_root"]
    engine_root = results_root / "r25c"
    if not engine_root.is_dir():
        raise FailClosed(f"missing engine results directory: {engine_root}")
    run_dirs = sorted(entry for entry in engine_root.iterdir()
                      if entry.is_dir() and (entry / "run_manifest.json").is_file())
    if not run_dirs:
        raise FailClosed(f"no engine run directories with a run_manifest.json under {engine_root}")
    latest = run_dirs[-1]
    try:
        manifest = json.loads((latest / "run_manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FailClosed(f"run manifest must be readable JSON: {latest / 'run_manifest.json'} ({error}).")
    if manifest.get("run_status") != "completed":
        raise FailClosed(f"latest engine run is not completed (run_status="
                         f"{manifest.get('run_status')!r}): {latest}")
    target_dirs = sorted(entry for entry in latest.iterdir()
                         if entry.is_dir() and TARGET_DIR_PATTERN.fullmatch(entry.name))
    if not target_dirs:
        raise FailClosed(f"no target directories in the latest run: {latest}")
    rows = []
    for target_dir in target_dirs:
        csv_path = target_dir / "all_candidates.csv"
        if not csv_path.is_file():
            raise FailClosed(f"missing candidate CSV: {csv_path}")
        rows.extend(read_rows(csv_path, sidecar, variant, run["task_id"], target_dir.name))
    return rows, sidecar


def read_corpus(corpus_root):
    corpus_root = Path(corpus_root)
    tasks = {}
    sidecars = {}
    for variant in VARIANTS:
        plan_dir = corpus_root / variant / "plan"
        plan_path = plan_dir / "run_plan.json"
        if not plan_path.is_file():
            raise FailClosed(f"missing run plan: {plan_path}")
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FailClosed(f"run plan must be readable JSON: {plan_path} ({error}).")
        runs = plan.get("runs")
        if not isinstance(runs, list) or not runs:
            raise FailClosed(f"run plan has no runs list: {plan_path}")
        for run in runs:
            if not isinstance(run, dict):
                raise FailClosed(f"run plan entries must be objects: {plan_path}")
            task_id = run.get("task_id")
            key = (variant, task_id)
            if key in tasks:
                raise FailClosed(f"duplicate task in run plan: {key}")
            rows, sidecar = read_task(plan_dir, run, variant)
            tasks[key] = rows
            sidecars[key] = sidecar
    missing = sorted(set(EXPECTED_TALLIES) - set(tasks))
    extra = sorted(set(tasks) - set(EXPECTED_TALLIES))
    if missing or extra:
        raise FailClosed(f"corpus task set mismatch: missing {missing}, unexpected {extra}.")
    return tasks, sidecars


def cross_check(tasks):
    for key in sorted(EXPECTED_TALLIES):
        expected = EXPECTED_TALLIES[key]
        actual = len(tasks[key])
        if actual != expected:
            raise FailClosed(f"row tally mismatch for {key[0]}/{key[1]}: "
                             f"found {actual} rows, recorded menu-B tally is {expected}.")
    counts = {name: 0 for name in EXPECTED_CLASS_COUNTS}
    for rows in tasks.values():
        for row in rows:
            if row["cls"] not in counts:
                raise FailClosed(f"unknown occupancy class {row['cls']!r}.")
            counts[row["cls"]] += 1
    for name in sorted(EXPECTED_CLASS_COUNTS):
        expected = EXPECTED_CLASS_COUNTS[name]
        if counts[name] != expected:
            raise FailClosed(f"pooled class count mismatch for {name}: found {counts[name]}, "
                             f"recorded menu-C count is {expected}.")
    return counts


# ---------------------------------------------------------------------------
# Exemplars, frame resolution, phase arrays
# ---------------------------------------------------------------------------

def pick_exemplar(rows, cls, variant, task_id):
    group = [row for row in rows if row["cls"] == cls]
    if not group:
        raise FailClosed(f"exemplar group is empty: {variant}/{task_id}/{cls}.")
    # Deterministic selection: lower-median recorded total width per group,
    # ties broken by candidate_id.
    group.sort(key=lambda row: (row["total"], row["candidate_id"]))
    return group[len(group) // 2]


def resolve_frame(row, sidecar, variant, task_id):
    """Recompute occupancy in BOTH base-angle frames and keep the one that
    reproduces the recorded windows.

    The engine CSV stores base_angle in radians (decode_refinement_variables
    applies remainder(raw[8], 2*pi)), but zone_screen.screen() then applies
    math.radians() to that stored value, so the recorded windows live in a
    "screen" frame whose effective base is radians(base_angle); the engine
    path frame ("plain") uses base_angle directly as radians.
    """
    region = sidecar["region"]
    steps = sidecar["steps"]
    thickness = sidecar["thickness"]
    carrier = sidecar["carrier"]
    recorded = row["windows"]
    tolerance = 0.5 * sidecar["step_deg"]
    attempts = {}
    for name, base_rad in (("screen", math.radians(row["params"][8])),
                           ("plain", row["params"][8])):
        flags, phases = occupancy_flags(region, row["params"], row["branch_sign"],
                                        base_rad, steps, thickness, carrier)
        if flags is None:
            attempts[name] = "invalid assembly in this frame"
            continue
        windows = windows_from_flags(flags)
        attempts[name] = windows
        if len(windows) != len(recorded):
            continue
        if all(abs(computed[0] - rec[0]) <= tolerance
                and abs(computed[1] - rec[1]) <= tolerance
                for computed, rec in zip(windows, recorded)):
            return name, windows, phases
    raise FailClosed(
        f"neither candidate frame reproduces the recorded windows for "
        f"{variant}/{task_id}/{row['candidate_id']}: recorded {recorded}, "
        f"screen {attempts.get('screen')}, plain {attempts.get('plain')}.")


def exemplar_arrays(row, sidecar, phases, cap):
    """Per-phase display arrays, pivots and bounds for one exemplar."""
    steps = sidecar["steps"]
    ax = [round(phase[0], 3) for phase in phases]
    ay = [round(phase[1], 3) for phase in phases]
    bx = [round(phase[2], 3) for phase in phases]
    by = [round(phase[3], 3) for phase in phases]
    px = [round(phase[4], 3) for phase in phases]
    py = [round(phase[5], 3) for phase in phases]
    l1, l2, l3, l4, s_ratio, bar, base_x, base_y, _ = row["params"]
    base_rad = math.radians(row["params"][8]) if row["frame"] == "screen" else row["params"][8]
    o2 = (base_x, base_y)
    o4 = (base_x + l1 * math.cos(base_rad), base_y + l1 * math.sin(base_rad))
    cx, cy = sidecar["region"]["center"]
    radius = sidecar["region"]["radius"]
    xs = ax + bx + px + [o2[0], o4[0], cx - radius, cx + radius]
    ys = ay + by + py + [o2[1], o4[1], cy - radius, cy + radius]
    if sidecar["carrier"] is not None:
        width, depth = sidecar["carrier"]
        for index in range(steps):
            ux = (bx[index] - ax[index]) / l3
            uy = (by[index] - ay[index]) / l3
            vx = -uy
            vy = ux
            for half_w, half_d in ((width / 2.0, depth / 2.0),
                                   (width / 2.0, -depth / 2.0),
                                   (-width / 2.0, -depth / 2.0),
                                   (-width / 2.0, depth / 2.0)):
                xs.append(px[index] + half_w * ux + half_d * vx)
                ys.append(py[index] + half_w * uy + half_d * vy)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad_x = 0.04 * (max_x - min_x) + 0.1
    pad_y = 0.04 * (max_y - min_y) + 0.1
    bbox = [round(min_x - pad_x, 3), round(min_y - pad_y, 3),
            round(max_x + pad_x, 3), round(max_y + pad_y, 3)]
    return {
        "ax": ax, "ay": ay, "bx": bx, "by": by, "px": px, "py": py,
        "o2": [round(o2[0], 3), round(o2[1], 3)],
        "o4": [round(o4[0], 3), round(o4[1], 3)],
        "bbox": bbox,
    }


def build_exemplars(tasks, sidecars):
    exemplars = []
    frames = {}
    for variant, task_id, cls in EXEMPLAR_GROUPS:
        key = (variant, task_id)
        row = pick_exemplar(tasks[key], cls, variant, task_id)
        frame, windows, phases = resolve_frame(row, sidecars[key], variant, task_id)
        row["frame"] = frame
        row["frame_windows"] = windows
        display = exemplar_arrays(row, sidecars[key], phases, sidecars[key]["cap"])
        sidecar = sidecars[key]
        exemplar = {
            "variant": variant,
            "task": task_id,
            "cls": cls,
            "candidate_id": row["candidate_id"],
            "frame": frame,
            "branch_sign": row["branch_sign"],
            "params": {name: value for name, value in zip(PARAM_NAMES, row["params"])},
            "l3": row["params"][2],
            "steps": sidecar["steps"],
            "step_deg": sidecar["step_deg"],
            "cap": sidecar["cap"],
            "zone": {"cx": sidecar["region"]["center"][0],
                     "cy": sidecar["region"]["center"][1],
                     "r": sidecar["region"]["radius"]},
            "thickness": sidecar["thickness"],
            "carrier": (None if sidecar["carrier"] is None
                        else {"w": sidecar["carrier"][0], "d": sidecar["carrier"][1]}),
            "windows": [[round(start, 4), round(end, 4)] for start, end in row["windows"]],
            "total_width_deg": round(row["total"], 4),
            **display,
        }
        exemplars.append(exemplar)
        frames[frame] = frames.get(frame, 0) + 1
    return exemplars, frames


# ---------------------------------------------------------------------------
# HTML assembly
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OMTS timeline animator - corpus-07 occupancy classes (menu item E)</title>
<style>
:root { color-scheme: light; }
body { font-family: system-ui, sans-serif; margin: 0; background: #f6f7f9; color: #1c2430; }
header { padding: 14px 20px 4px; }
h1 { font-size: 18px; margin: 0; }
.sub { color: #5a6a80; font-size: 13px; margin-top: 2px; }
#controls { display: flex; gap: 14px; align-items: center; padding: 10px 20px;
            background: #eef1f6; border-top: 1px solid #dde3ec; border-bottom: 1px solid #dde3ec; }
#controls button { padding: 4px 14px; }
#scrub { flex: 1; }
#theta { font-variant-numeric: tabular-nums; min-width: 80px; }
#verdict { font-size: 12px; }
#verdict.ok { color: #1a7f37; }
#verdict.bad { color: #b42318; font-weight: bold; }
main { display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 14px; padding: 14px 20px; }
.panel { background: #fff; border: 1px solid #dde3ec; border-radius: 8px; padding: 10px 12px; }
.panel h2 { font-size: 13px; margin: 0 0 6px; font-weight: 600; }
.panel .meta { color: #5a6a80; font-size: 12px; margin-bottom: 6px; }
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 12px; }
.badge { padding: 1px 10px; border-radius: 10px; font-weight: 600; }
.badge.in { background: #b42318; color: #fff; }
.badge.out { background: #e6e9ef; color: #44526b; }
.dist { color: #44526b; font-variant-numeric: tabular-nums; }
.gauge-label { color: #5a6a80; }
footer { padding: 10px 20px 24px; color: #5a6a80; font-size: 12px; }
#fatal { display: none; position: fixed; inset: 0; background: rgba(255,255,255,0.96);
         z-index: 10; padding: 40px; font-size: 15px; color: #b42318; white-space: pre-wrap; }
</style>
</head>
<body>
<header>
  <h1>OMTS timeline animator (menu item E) - corpus-07 occupancy classes</h1>
  <div class="sub">one deterministic exemplar per class group; recorded windows; occupancy timing over the full crank turn</div>
</header>
<div id="controls">
  <button id="play" type="button">Pause</button>
  <input id="scrub" type="range" min="0" max="719" value="0" step="1">
  <span id="theta">theta 0.0 deg</span>
  <label>speed
    <select id="speed">
      <option value="30">30 steps/s</option>
      <option value="60">60 steps/s</option>
      <option value="120" selected>120 steps/s</option>
      <option value="360">360 steps/s</option>
    </select>
  </label>
  <span id="verdict" class="ok">verification: pending</span>
</div>
<main id="panels"></main>
<footer>method sampled_collision_geometry_v1 - sampled, not certified; no between-sample guarantee;
not collision, thickness or machinery certification. Explorer tool: no new physics claim;
the quick_pass / drag_over_cap boundary remains untested.</footer>
<div id="fatal"></div>
<script id="anim-data" type="application/json">__DATA__</script>
<script>
(function () {
"use strict";
var data = JSON.parse(document.getElementById("anim-data").textContent);
var panels = [];
var idx = 0;
var playing = true;
var speed = 120;
var lastT = null;
var fatal = document.getElementById("fatal");

function fail(message) {
  fatal.textContent = "ANIMATOR DATA VERIFICATION FAILED (fail closed): " + message;
  fatal.style.display = "block";
  playing = false;
  var verdict = document.getElementById("verdict");
  verdict.textContent = "verification: FAILED";
  verdict.className = "bad";
  throw new Error(message);
}

function segPointDistance(px, py, qx, qy, x, y) {
  var dx = qx - px, dy = qy - py;
  var sq = dx * dx + dy * dy;
  var t = sq <= 0 ? 0 : ((x - px) * dx + (y - py) * dy) / sq;
  if (t < 0) { t = 0; } else if (t > 1) { t = 1; }
  return Math.hypot(x - (px + t * dx), y - (py + t * dy));
}

function inWindows(thetaDeg, windows) {
  for (var w = 0; w < windows.length; w++) {
    var s = windows[w][0], e = windows[w][1];
    if (s <= e) {
      if (thetaDeg >= s && thetaDeg <= e) { return true; }
    } else {
      if (thetaDeg >= s || thetaDeg <= e) { return true; }
    }
  }
  return false;
}

function panelPoints(p, i) {
  var a = [p.ax[i], p.ay[i]];
  var b = [p.bx[i], p.by[i]];
  var c = [p.px[i], p.py[i]];
  var ux = (b[0] - a[0]) / p.l3, uy = (b[1] - a[1]) / p.l3;
  var vx = -uy, vy = ux;
  return { a: a, b: b, c: c, ux: ux, uy: uy, vx: vx, vy: vy };
}

function nearestDistance(p, i) {
  var pts = panelPoints(p, i);
  var cx = p.zone.cx, cy = p.zone.cy, r = p.zone.r;
  var segments = [
    [p.o2[0], p.o2[1], pts.a[0], pts.a[1]],
    [pts.a[0], pts.a[1], pts.b[0], pts.b[1]],
    [p.o4[0], p.o4[1], pts.b[0], pts.b[1]]
  ];
  if (p.carrier) {
    var w = p.carrier.w / 2, d = p.carrier.d / 2;
    var corners = [
      [pts.c[0] + w * pts.ux + d * pts.vx, pts.c[1] + w * pts.uy + d * pts.vy],
      [pts.c[0] + w * pts.ux - d * pts.vx, pts.c[1] + w * pts.uy - d * pts.vy],
      [pts.c[0] - w * pts.ux - d * pts.vx, pts.c[1] - w * pts.uy - d * pts.vy],
      [pts.c[0] - w * pts.ux + d * pts.vx, pts.c[1] - w * pts.uy + d * pts.vy]
    ];
    for (var k = 0; k < 4; k++) {
      segments.push([corners[k][0], corners[k][1], corners[(k + 1) % 4][0], corners[(k + 1) % 4][1]]);
    }
  }
  var best = Infinity;
  for (var s = 0; s < segments.length; s++) {
    var dist = Math.max(0, segPointDistance(segments[s][0], segments[s][1],
                                            segments[s][2], segments[s][3], cx, cy) - r);
    if (dist < best) { best = dist; }
  }
  return best;
}

function verifyPanel(p, number) {
  var minx = p.bbox[0], miny = p.bbox[1], maxx = p.bbox[2], maxy = p.bbox[3];
  var eps = 0.01;
  var arrays = [["ax", p.ax, "ay", p.ay], ["bx", p.bx, "by", p.by], ["px", p.px, "py", p.py]];
  for (var g = 0; g < arrays.length; g++) {
    var xs = arrays[g][1], ys = arrays[g][3];
    for (var i = 0; i < p.steps; i++) {
      if (xs[i] < minx - eps || xs[i] > maxx + eps || ys[i] < miny - eps || ys[i] > maxy + eps) {
        fail("panel " + number + ": embedded coordinates fall outside the embedded bounds at phase " + i);
      }
    }
  }
  var points = [p.o2, p.o4, [p.zone.cx - p.zone.r, p.zone.cy], [p.zone.cx + p.zone.r, p.zone.cy],
                [p.zone.cx, p.zone.cy - p.zone.r], [p.zone.cx, p.zone.cy + p.zone.r]];
  for (var q = 0; q < points.length; q++) {
    if (points[q][0] < minx - eps || points[q][0] > maxx + eps ||
        points[q][1] < miny - eps || points[q][1] > maxy + eps) {
      fail("panel " + number + ": zone or pivot geometry falls outside the embedded bounds");
    }
  }
  if (p.carrier) {
    var w = p.carrier.w / 2, d = p.carrier.d / 2;
    for (var j = 0; j < p.steps; j++) {
      var pts = panelPoints(p, j);
      var combos = [[w, d], [w, -d], [-w, -d], [-w, d]];
      for (var k = 0; k < 4; k++) {
        var x = pts.c[0] + combos[k][0] * pts.ux + combos[k][1] * pts.vx;
        var y = pts.c[1] + combos[k][0] * pts.uy + combos[k][1] * pts.vy;
        if (x < minx - eps || x > maxx + eps || y < miny - eps || y > maxy + eps) {
          fail("panel " + number + ": carrier corners fall outside the embedded bounds at phase " + j);
        }
      }
    }
  }
  if (p.steps !== data.meta.steps) {
    fail("panel " + number + ": step count mismatch vs meta");
  }
}

function buildPanel(p, number) {
  var panel = document.createElement("section");
  panel.className = "panel";
  var vb = p.bbox[0] + " " + p.bbox[1] + " " + (p.bbox[2] - p.bbox[0]) + " " + (p.bbox[3] - p.bbox[1]);
  var width = 460, height = 320;
  var sx = function (x) { return (x - p.bbox[0]) / (p.bbox[2] - p.bbox[0]) * width; };
  var sy = function (y) { return (y - p.bbox[1]) / (p.bbox[3] - p.bbox[1]) * height; };
  panel.innerHTML =
    "<h2>" + p.variant + " / " + p.task + " / " + p.cls + "</h2>" +
    "<div class='meta'>candidate " + p.candidate_id + " &middot; branch " + p.branch_sign +
    " &middot; frame " + p.frame + " &middot; total width " + p.total_width_deg.toFixed(1) +
    "&deg; vs cap " + p.cap + "&deg;</div>" +
    "<svg viewBox='" + vb + "' width='" + width + "' height='" + height + "' style='max-width:100%'>" +
    "<circle class='zone-fill' cx='" + p.zone.cx + "' cy='" + p.zone.cy + "' r='" + p.zone.r + "' fill='rgba(180,35,24,0)'/>" +
    "<circle cx='" + p.zone.cx + "' cy='" + p.zone.cy + "' r='" + p.zone.r + "' fill='none' stroke='#e08a00' stroke-width='" + (p.bbox[2]-p.bbox[0]) / 460 + "'/>" +
    "<polygon class='carrier' points='' fill='rgba(28,36,48,0.12)' stroke='#7c8aa0'/>" +
    "<line class='crank' x1='' y1='' x2='' y2='' stroke='#1c2430' stroke-width='" + (p.bbox[2]-p.bbox[0]) / 230 + "'/>" +
    "<line class='coupler' x1='' y1='' x2='' y2='' stroke='#1c2430' stroke-width='" + (p.bbox[2]-p.bbox[0]) / 230 + "'/>" +
    "<line class='rocker' x1='' y1='' x2='' y2='' stroke='#1c2430' stroke-width='" + (p.bbox[2]-p.bbox[0]) / 230 + "'/>" +
    "<circle class='pivot' cx='" + p.o2[0] + "' cy='" + p.o2[1] + "' r='" + (p.bbox[2]-p.bbox[0]) / 90 + "' fill='#1c2430'/>" +
    "<circle class='pivot' cx='" + p.o4[0] + "' cy='" + p.o4[1] + "' r='" + (p.bbox[2]-p.bbox[0]) / 90 + "' fill='#1c2430'/>" +
    "<circle class='p-point' cx='' cy='' r='" + (p.bbox[2]-p.bbox[0]) / 60 + "' fill='#0b6bcb'/>" +
    "</svg>" +
    "<svg class='timeline' viewBox='0 0 460 30' width='" + width + "' style='max-width:100%'>" +
    "<rect x='0' y='6' width='460' height='18' fill='#e6e9ef' stroke='#dde3ec'/>" +
    "<text x='0' y='29' font-size='8' fill='#5a6a80'>0</text>" +
    "<text x='225' y='29' font-size='8' fill='#5a6a80' text-anchor='middle'>180</text>" +
    "<text x='457' y='29' font-size='8' fill='#5a6a80' text-anchor='end'>360</text>" +
    "<line class='marker' x1='0' y1='2' x2='0' y2='28' stroke='#0b6bcb' stroke-width='1.5'/>" +
    "</svg>" +
    "<div class='row'>" +
    "<span class='badge out'>outside zone</span>" +
    "<span class='dist'></span>" +
    "<svg class='gauge' viewBox='0 0 460 22' width='" + width + "' style='max-width:100%'>" +
    "<rect x='0' y='2' width='460' height='12' fill='#e6e9ef' stroke='#dde3ec'/>" +
    "<rect class='gauge-fill' x='0' y='2' width='0' height='12' fill='" + (p.cls === "quick_pass" || p.cls === "never" ? "#1a7f37" : "#b42318") + "'/>" +
    "<line class='cap-tick' x1='" + (p.cap / 360 * 460) + "' y1='0' x2='" + (p.cap / 360 * 460) + "' y2='16' stroke='#1c2430' stroke-width='2'/>" +
    "</svg>" +
    "<span class='gauge-label'>total " + p.total_width_deg.toFixed(1) + "&deg; / cap " + p.cap + "&deg;</span>" +
    "</div>";
  document.getElementById("panels").appendChild(panel);
  var svg = panel.querySelector("svg");
  var timeline = panel.querySelector(".timeline");
  var refs = {
    p: p,
    zoneFill: panel.querySelector(".zone-fill"),
    crank: panel.querySelector(".crank"),
    coupler: panel.querySelector(".coupler"),
    rocker: panel.querySelector(".rocker"),
    carrier: panel.querySelector(".carrier"),
    pPoint: panel.querySelector(".p-point"),
    marker: timeline.querySelector(".marker"),
    badge: panel.querySelector(".badge"),
    dist: panel.querySelector(".dist"),
    sx: sx,
    sy: sy,
    width: width,
    height: height
  };
  // Static occupancy-window shading and the static cap gauge are set ONCE
  // at build time from the recorded data (never recomputed per frame).
  var tl = panel.querySelector(".timeline");
  var scale = 460 / 360;
  for (var w = 0; w < p.windows.length; w++) {
    var s = p.windows[w][0], e = p.windows[w][1];
    var rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    if (s <= e) {
      rect.setAttribute("x", s * scale);
      rect.setAttribute("width", (e - s) * scale);
    } else {
      rect.setAttribute("x", s * scale);
      rect.setAttribute("width", (360 - s) * scale);
    }
    rect.setAttribute("y", 6);
    rect.setAttribute("height", 18);
    rect.setAttribute("fill", "rgba(11,107,203,0.55)");
    tl.appendChild(rect);
    if (s > e) {
      var rect2 = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect2.setAttribute("x", 0);
      rect2.setAttribute("width", e * scale);
      rect2.setAttribute("y", 6);
      rect2.setAttribute("height", 18);
      rect2.setAttribute("fill", "rgba(11,107,203,0.55)");
      tl.appendChild(rect2);
    }
  }
  panel.querySelector(".gauge-fill").setAttribute("width",
    (Math.min(360, p.total_width_deg) / 360 * 460).toFixed(2));
  return refs;
}

function draw() {
  var thetaDeg = idx * data.meta.step_deg;
  document.getElementById("theta").textContent = "theta " + thetaDeg.toFixed(1) + " deg";
  document.getElementById("scrub").value = String(idx);
  for (var n = 0; n < panels.length; n++) {
    var refs = panels[n];
    var p = refs.p;
    var i = idx;
    var pts = panelPoints(p, i);
    refs.crank.setAttribute("x1", p.o2[0]); refs.crank.setAttribute("y1", p.o2[1]);
    refs.crank.setAttribute("x2", pts.a[0]); refs.crank.setAttribute("y2", pts.a[1]);
    refs.coupler.setAttribute("x1", pts.a[0]); refs.coupler.setAttribute("y1", pts.a[1]);
    refs.coupler.setAttribute("x2", pts.b[0]); refs.coupler.setAttribute("y2", pts.b[1]);
    refs.rocker.setAttribute("x1", p.o4[0]); refs.rocker.setAttribute("y1", p.o4[1]);
    refs.rocker.setAttribute("x2", pts.b[0]); refs.rocker.setAttribute("y2", pts.b[1]);
    refs.pPoint.setAttribute("cx", pts.c[0]); refs.pPoint.setAttribute("cy", pts.c[1]);
    if (p.carrier) {
      var w = p.carrier.w / 2, d = p.carrier.d / 2;
      var corners = [
        [pts.c[0] + w * pts.ux + d * pts.vx, pts.c[1] + w * pts.uy + d * pts.vy],
        [pts.c[0] + w * pts.ux - d * pts.vx, pts.c[1] + w * pts.uy - d * pts.vy],
        [pts.c[0] - w * pts.ux - d * pts.vx, pts.c[1] - w * pts.uy - d * pts.vy],
        [pts.c[0] - w * pts.ux + d * pts.vx, pts.c[1] - w * pts.uy + d * pts.vy]
      ];
      refs.carrier.setAttribute("points", corners.map(function (c) { return c[0].toFixed(3) + "," + c[1].toFixed(3); }).join(" "));
      refs.carrier.style.display = "";
    } else {
      refs.carrier.style.display = "none";
    }
    var occupied = inWindows(thetaDeg, p.windows);
    refs.zoneFill.setAttribute("fill", occupied ? "rgba(180,35,24,0.25)" : "rgba(180,35,24,0)");
    refs.badge.textContent = occupied ? "IN ZONE (recorded)" : "outside zone";
    refs.badge.className = "badge " + (occupied ? "in" : "out");
    refs.dist.textContent = "nearest body-zone edge: " + nearestDistance(p, i).toFixed(3) + " (diagnostic)";
    refs.marker.setAttribute("x1", (thetaDeg / 360 * 460).toFixed(2));
    refs.marker.setAttribute("x2", (thetaDeg / 360 * 460).toFixed(2));
  }
}

function frame(now) {
  if (lastT === null) { lastT = now; }
  var dt = (now - lastT) / 1000;
  lastT = now;
  if (playing) {
    idx = (idx + speed * dt) % data.meta.steps;
    idx = Math.floor(idx);
    draw();
  }
  requestAnimationFrame(frame);
}

function init() {
  var steps = data.meta.steps;
  for (var k = 0; k < data.panels.length; k++) {
    verifyPanel(data.panels[k], k + 1);
    panels.push(buildPanel(data.panels[k], k + 1));
  }
  document.getElementById("scrub").max = String(steps - 1);
  document.getElementById("scrub").addEventListener("input", function (event) {
    idx = parseInt(event.target.value, 10);
    draw();
  });
  document.getElementById("play").addEventListener("click", function () {
    playing = !playing;
    this.textContent = playing ? "Pause" : "Play";
  });
  document.getElementById("speed").addEventListener("change", function (event) {
    speed = parseInt(event.target.value, 10);
  });
  var verdict = document.getElementById("verdict");
  verdict.textContent = "verification: PASS (" + data.panels.length + " panels, bounds + steps)";
  draw();
  requestAnimationFrame(frame);
}

init();
})();
</script>
</body>
</html>
"""


def build_html(exemplars, frames, class_counts, steps, step_deg, cap):
    panels = []
    for exemplar in exemplars:
        panel = {
            "variant": exemplar["variant"],
            "task": exemplar["task"],
            "cls": exemplar["cls"],
            "candidate_id": exemplar["candidate_id"],
            "frame": exemplar["frame"],
            "branch_sign": exemplar["branch_sign"],
            "params": exemplar["params"],
            "l3": exemplar["l3"],
            "steps": exemplar["steps"],
            "step_deg": exemplar["step_deg"],
            "cap": exemplar["cap"],
            "zone": exemplar["zone"],
            "thickness": exemplar["thickness"],
            "carrier": exemplar["carrier"],
            "windows": exemplar["windows"],
            "total_width_deg": exemplar["total_width_deg"],
            "o2": exemplar["o2"],
            "o4": exemplar["o4"],
            "bbox": exemplar["bbox"],
            "ax": exemplar["ax"], "ay": exemplar["ay"],
            "bx": exemplar["bx"], "by": exemplar["by"],
            "px": exemplar["px"], "py": exemplar["py"],
        }
        panels.append(panel)
    payload = {
        "meta": {
            "generated_by": "runs/analysis/anim_e.py (menu item E)",
            "corpus": str(CORPUS_ROOT),
            "method": METHOD,
            "steps": steps,
            "step_deg": step_deg,
            "cap_deg": cap,
            "frames": frames,
            "pooled_class_counts": class_counts,
            "disclaimer": DISCLAIMER,
        },
        "panels": panels,
    }
    text = json.dumps(payload, separators=(",", ":"))
    text = text.replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__DATA__", text)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(corpus_root=CORPUS_ROOT, out_dir=OUT_DIR):
    corpus_root = Path(corpus_root)
    out_dir = Path(out_dir)
    tasks, sidecars = read_corpus(corpus_root)
    class_counts = cross_check(tasks)
    exemplars, frames = build_exemplars(tasks, sidecars)

    steps_set = {sidecar["steps"] for sidecar in sidecars.values()}
    cap_set = {sidecar["cap"] for sidecar in sidecars.values()}
    if len(steps_set) != 1 or len(cap_set) != 1:
        raise FailClosed(f"sidecars disagree on steps {sorted(steps_set)} or cap {sorted(cap_set)}.")
    steps = steps_set.pop()
    step_deg = 360.0 / steps
    cap = cap_set.pop()

    html = build_html(exemplars, frames, class_counts, steps, step_deg, cap)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / HTML_NAME
    meta_path = out_dir / META_NAME
    if html_path.exists():
        html_path.unlink()
    if meta_path.exists():
        meta_path.unlink()
    html_path.write_text(html, encoding="utf-8")
    meta = {
        "generated_by": "runs/analysis/anim_e.py (menu item E)",
        "corpus": str(corpus_root),
        "method": METHOD,
        "disclaimer": DISCLAIMER,
        "steps": steps,
        "step_deg": step_deg,
        "cap_deg": cap,
        "per_task_tallies": {f"{variant}/{task}": len(tasks[(variant, task)])
                             for (variant, task) in sorted(EXPECTED_TALLIES)},
        "pooled_class_counts": class_counts,
        "frames": frames,
        "exemplar_selection": "lower-median recorded total_width_deg per group, ties by candidate_id",
        "exemplars": [
            {
                "variant": e["variant"], "task": e["task"], "cls": e["cls"],
                "candidate_id": e["candidate_id"], "frame": e["frame"],
                "branch_sign": e["branch_sign"], "params": e["params"],
                "windows": e["windows"], "total_width_deg": e["total_width_deg"],
                "zone": e["zone"], "thickness": e["thickness"],
                "carrier": e["carrier"],
            }
            for e in exemplars
        ],
        "frame_note": ("base_angle is stored in radians by the engine "
                       "(decode_refinement_variables applies remainder(raw[8], 2*pi)), "
                       "but zone_screen.screen() applies math.radians() to the stored "
                       "value; recorded windows live in the screen frame "
                       "(base = radians(base_angle)). The animator recomputes each "
                       "exemplar in both frames and keeps the frame that reproduces "
                       "the recorded windows (recorded as an engine unit observation)."),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print("OMTS timeline animator (menu item E)")
    print(f"Corpus: {corpus_root} (6 variants x 2 tasks)")
    print(f"Sidecars: {len(sidecars)}/{len(sidecars)} parsed (method {METHOD}; "
          f"steps {steps}; cap {cap:g} deg)")
    print(f"Rows: {sum(len(rows) for rows in tasks.values())} candidates read "
          f"(latest engine runs only; contribution bundles and older runs skipped)")
    print(f"Cross-check vs recorded menu-B tallies: PASS ({len(EXPECTED_TALLIES)}/{len(EXPECTED_TALLIES)} tasks)")
    print("Pooled occupancy classes vs recorded menu-C counts: PASS ("
          + ", ".join(f"{name} {class_counts[name]}" for name in
                      ("never", "quick_pass", "drag_over_cap", "full360",
                       "screen_geometry_invalid")) + ")")
    print(f"Exemplars: {len(exemplars)}/{len(EXEMPLAR_GROUPS)} selected "
          f"(lower-median total_width_deg per group, ties by candidate_id)")
    print("Frame resolution: "
          + ", ".join(f"{name} {count}" for name, count in sorted(frames.items()))
          + " (screen frame = base radians(base_angle), the engine zone_screen convention)")
    print(f"Assembly re-validated: {steps}/{steps} phases ok ({len(exemplars)}/{len(exemplars)} exemplars)")
    print(f"Animation (open in a browser): {html_path}")
    print(f"Meta: {meta_path}")
    return {"class_counts": class_counts, "frames": frames, "exemplars": exemplars,
            "html_path": str(html_path), "meta_path": str(meta_path)}


def main():
    try:
        run()
    except FailClosed as error:
        print(f"FAIL-CLOSED ABORT: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
