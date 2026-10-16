#!/usr/bin/env python3
"""OMTS transform-space map, menu item C.3: bearing axis.

Re-reads the corpus-07 engine result trees (the same traversal the menu-B
digest used) and adds the BEARING of the shared zone in each candidate's
own base frame: the direction from O2 to the zone center, relative to the
candidate's ground-link direction. Candidates within a variant differ by
rotate/scale transforms, so a candidate-relative bearing is the rotation-
invariant companion to C.2's clear_min/l1 scale invariance.

Question asked: does bearing separate the occupancy classes that clearance
could not? Pure analysis: no repository changes, nothing written outside
runs/analysis/transform-map-03/.

Honesty notes:
- Widths are SAMPLED occupancy at the sidecar step - this is not collision
  certification, and rows are pre-dedup (counts may differ from JOB.md).
- Bearing is a direction only: it says nothing about distance (that is the
  clearance axis) and nothing between occupancy samples.
- The script fails closed: any missing file, column, sidecar field, or
  tally mismatch against the recorded menu-B results aborts the run.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "runs" / "sync-corpus-07"
OUT_DIR = ROOT / "runs" / "analysis" / "transform-map-03"
DIGEST_CSV = ROOT / "runs" / "analysis" / "occupancy-digest-01" / "occupancy_digest.csv"
METHOD = "sampled_collision_geometry_v1"
CAP_TOL = 1e-6
CLASS_ORDER = ("never", "quick_pass", "drag_over_cap", "full360", "screen_geometry_invalid")
COLORS = {
    "never": "#1f6fb2",
    "quick_pass": "#2f9e5b",
    "drag_over_cap": "#d1493b",
    "full360": "#8a4fb8",
    "screen_geometry_invalid": "#9aa0a6",
}

# Occupancy tallies recorded from the menu-B run output (pre-dedup rows).
# C.3 traverses the same trees and must reproduce these exactly or fail.
EXPECTED_TALLIES = {
    "corpus_pair_01/catcher": dict(never=21, quick_pass=17, drag_over_cap=0, full360=0, screen_geometry_invalid=0),
    "corpus_pair_01/gate": dict(never=8, quick_pass=3, drag_over_cap=24, full360=7, screen_geometry_invalid=0),
    "corpus_pair_02/catcher": dict(never=0, quick_pass=22, drag_over_cap=20, full360=0, screen_geometry_invalid=0),
    "corpus_pair_02/gate": dict(never=0, quick_pass=0, drag_over_cap=42, full360=0, screen_geometry_invalid=0),
    "corpus_pair_03/catcher": dict(never=0, quick_pass=15, drag_over_cap=27, full360=0, screen_geometry_invalid=0),
    "corpus_pair_03/gate": dict(never=0, quick_pass=24, drag_over_cap=18, full360=0, screen_geometry_invalid=0),
    "corpus_pair_04/catcher": dict(never=0, quick_pass=0, drag_over_cap=41, full360=1, screen_geometry_invalid=0),
    "corpus_pair_04/gate": dict(never=0, quick_pass=22, drag_over_cap=20, full360=0, screen_geometry_invalid=0),
    "corpus_pair_05/catcher": dict(never=0, quick_pass=21, drag_over_cap=21, full360=0, screen_geometry_invalid=0),
    "corpus_pair_05/gate": dict(never=0, quick_pass=26, drag_over_cap=15, full360=0, screen_geometry_invalid=0),
    "corpus_pair_06/catcher": dict(never=0, quick_pass=24, drag_over_cap=18, full360=0, screen_geometry_invalid=0),
    "corpus_pair_06/gate": dict(never=24, quick_pass=18, drag_over_cap=0, full360=0, screen_geometry_invalid=0),
}


def fail(message: str):
    raise SystemExit("FAIL: " + message)


def parse_bool(value, where: str) -> bool:
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no", ""):
        return False
    fail("unparseable boolean %r at %s" % (value, where))


def wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def fold180(deg: float) -> float:
    """Angular distance from the pivot line: 0 = in line, 90 = broadside."""
    a = abs(wrap180(deg))
    return min(a, 180.0 - a)


def segment_distance(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def circular_mean(degrees):
    if not degrees:
        return None
    rad = math.radians
    sum_x = sum(math.cos(rad(d)) for d in degrees)
    sum_y = sum(math.sin(rad(d)) for d in degrees)
    if sum_x == 0.0 and sum_y == 0.0:
        return None
    return math.degrees(math.atan2(sum_y, sum_x))


def circular_concentration(degrees):
    if not degrees:
        return None
    rad = math.radians
    sum_x = sum(math.cos(rad(d)) for d in degrees)
    sum_y = sum(math.sin(rad(d)) for d in degrees)
    return math.hypot(sum_x, sum_y) / len(degrees)


def circular_separation(a, b):
    if a is None or b is None:
        return None
    return abs((a - b + 180.0) % 360.0 - 180.0)


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def scatter_svg(points, x0, x1, y0, y1, width, height, title, xlabel, ylabel):
    """Self-contained inline SVG scatter; verifies its own XML before use."""
    pad_l, pad_r, pad_t, pad_b = 56, 14, 30, 38

    def sx(value):
        return pad_l + (value - x0) / (x1 - x0) * (width - pad_l - pad_r)

    def sy(value):
        return height - pad_b - (value - y0) / (y1 - y0) * (height - pad_t - pad_b)

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
             % (width, height, width, height),
             '<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (width, height),
             '<text x="%d" y="18" font-family="Helvetica,Arial,sans-serif" font-size="13" fill="#222222">%s</text>'
             % (pad_l, esc(title))]
    x_ticks = [-180, -135, -90, -45, 0, 45, 90, 135, 180] if x1 - x0 > 200 else [0, 30, 60, 90]
    for tick in x_ticks:
        if not x0 <= tick <= x1:
            continue
        parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#dddddd" stroke-width="1"/>'
                     % (sx(tick), pad_t, sx(tick), height - pad_b))
        parts.append('<text x="%.1f" y="%d" font-family="Helvetica,Arial,sans-serif" font-size="10" fill="#555555" text-anchor="middle">%d</text>'
                     % (sx(tick), height - pad_b + 14, tick))
    for step in range(5):
        value = y0 + (y1 - y0) * step / 4.0
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#dddddd" stroke-width="1"/>'
                     % (pad_l, sy(value), width - pad_r, sy(value)))
        parts.append('<text x="%d" y="%.1f" font-family="Helvetica,Arial,sans-serif" font-size="10" fill="#555555" text-anchor="end">%.2f</text>'
                     % (pad_l - 5, sy(value) + 3, value))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333333" stroke-width="1"/>'
                 % (pad_l, pad_t, pad_l, height - pad_b))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333333" stroke-width="1"/>'
                 % (pad_l, height - pad_b, width - pad_r, height - pad_b))
    for point in points:
        x, y, color, diamond = point
        px, py = sx(x), sy(y)
        if diamond:
            parts.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" opacity="0.85"/>'
                         % (px, py - 4, px + 4, py, px, py + 4, px - 4, py, color))
        else:
            parts.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="%s" opacity="0.6"/>'
                         % (px, py, color))
    parts.append('<text x="%d" y="%d" font-family="Helvetica,Arial,sans-serif" font-size="11" fill="#333333" text-anchor="middle">%s</text>'
                 % ((pad_l + width - pad_r) // 2, height - 6, esc(xlabel)))
    parts.append('</svg>')
    svg = "\n".join(parts)
    ElementTree.fromstring(svg)  # fail closed on any malformed markup
    return svg


def read_sidecar(path: Path):
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail("zone screen sidecar must be readable JSON (%s): %s" % (path, error))
    if not isinstance(document, dict):
        fail("zone screen sidecar must be an object: %s" % path)
    if document.get("method") != METHOD:
        fail("zone screen sidecar method must be %r (%s)" % (METHOD, path))
    steps = document.get("steps")
    if not isinstance(steps, int) or isinstance(steps, bool):
        fail("zone screen sidecar needs an integer steps (%s)" % path)
    thickness = document.get("thickness")
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool) or thickness < 0:
        fail("zone screen sidecar needs a non-negative thickness (%s)" % path)
    regions = {}
    for region in document.get("regions") or []:
        if not isinstance(region, dict) or "id" not in region:
            fail("bad region entry in sidecar %s" % path)
        regions[region["id"]] = region
    if not regions:
        fail("sidecar %s declares no regions" % path)
    screen = document.get("screen")
    if not isinstance(screen, list) or not screen:
        fail("sidecar %s declares no screen entries" % path)
    if len(screen) != 1:
        fail("C.3 expects exactly one screen entry per sidecar, found %d (%s)" % (len(screen), path))
    entry = screen[0]
    region_id = entry.get("region")
    if region_id not in regions:
        fail("screen entry references unknown region %r (%s)" % (region_id, path))
    region = regions[region_id]
    if region.get("shape") != "circle":
        fail("C.3 requires circle regions (region %r is %r) in %s" % (region_id, region.get("shape"), path))
    center, radius = region.get("center"), region.get("radius")
    if (not isinstance(center, list) or len(center) != 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in center)
            or not isinstance(radius, (int, float)) or isinstance(radius, bool) or radius <= 0):
        fail("circle region %r needs a two-component center and positive radius (%s)" % (region_id, path))
    cap = entry.get("max_total_width_deg")
    if not isinstance(cap, (int, float)) or isinstance(cap, bool) or not 0 <= cap <= 360:
        fail("screen entry needs max_total_width_deg within [0, 360] (%s)" % path)
    return {"region_id": region_id, "cap": float(cap), "steps": steps,
            "thickness": float(thickness), "center": (float(center[0]), float(center[1])),
            "radius": float(radius)}


def classify(width_text, geometry_valid: bool, cap: float, where: str) -> str:
    if not geometry_valid:
        return "screen_geometry_invalid"
    if width_text is None or str(width_text).strip() == "":
        fail("geometry-valid row without a width value at %s" % where)
    width = float(width_text)
    if width >= 360.0 - CAP_TOL:
        return "full360"
    if width <= 0.0:
        return "never"
    if width <= cap:
        return "quick_pass"
    return "drag_over_cap"


def main() -> int:
    if not (ROOT / "pyproject.toml").is_file():
        fail("pyproject.toml not found under %s (script must live at runs/analysis/)" % ROOT)
    if not CORPUS.is_dir():
        fail("corpus directory not found: %s" % CORPUS)
    pairs = sorted(p for p in CORPUS.iterdir() if p.is_dir() and p.name.startswith("corpus_pair_"))
    if not pairs:
        fail("no corpus_pair_* directories under %s" % CORPUS)

    rows = []
    tallies = defaultdict(lambda: defaultdict(int))
    task_rows = defaultdict(list)
    pair_counts = defaultdict(int)
    caps_seen = []
    steps_seen = []
    region_ids_seen = []
    for pair_dir in pairs:
        plan_dir = pair_dir / "plan"
        plan_path = plan_dir / "run_plan.json"
        if not plan_path.is_file():
            fail("missing run plan: %s" % plan_path)
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            fail("unreadable run plan %s: %s" % (plan_path, error))
        runs = plan.get("runs")
        if not isinstance(runs, list) or not runs:
            fail("run plan %s has no runs list" % plan_path)
        for run in runs:
            for key in ("task_id", "output_root", "zone_screen_file"):
                if key not in run:
                    fail("run entry without %r in %s" % (key, plan_path))
            task_key = "%s/%s" % (pair_dir.name, run["task_id"])
            sidecar_path = plan_dir / run["zone_screen_file"]
            if not sidecar_path.is_file():
                fail("missing zone screen sidecar: %s" % sidecar_path)
            sidecar = read_sidecar(sidecar_path)
            caps_seen.append(sidecar["cap"])
            steps_seen.append(sidecar["steps"])
            region_id = sidecar["region_id"]
            region_ids_seen.append(region_id)
            cx, cy = sidecar["center"]
            radius = sidecar["radius"]
            run_root = plan_dir / run["output_root"] / "r25c"
            if not run_root.is_dir():
                fail("missing engine results directory: %s" % run_root)
            manifests = sorted(run_root.glob("*/run_manifest.json"))
            if not manifests:
                fail("no run_manifest.json under %s" % run_root)
            run_dir = manifests[-1].parent
            target_dirs = sorted(d for d in run_dir.iterdir()
                                 if d.is_dir() and (d / "all_candidates.csv").is_file())
            if not target_dirs:
                fail("no target directories with all_candidates.csv under %s" % run_dir)
            for target_dir in target_dirs:
                csv_path = target_dir / "all_candidates.csv"
                with csv_path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    header = reader.fieldnames or []
                    required = ["candidate_id", "l1", "l2", "l3", "l4", "base_x", "base_y",
                                "base_angle", "zone_screen_geometry_valid",
                                "zone_screen_%s_total_width_deg" % region_id,
                                "zone_screen_%s_windows" % region_id]
                    missing = [c for c in required if c not in header]
                    if missing:
                        fail("missing column(s) %s in %s" % (", ".join(missing), csv_path))
                    for record in reader:
                        where = "%s row candidate %s" % (csv_path, record.get("candidate_id"))
                        geometry_valid = parse_bool(record.get("zone_screen_geometry_valid"), where)
                        width_text = record.get("zone_screen_%s_total_width_deg" % region_id)
                        occupancy_class = classify(width_text, geometry_valid, sidecar["cap"], where)
                        tallies[task_key][occupancy_class] += 1
                        pair_counts[pair_dir.name] += 1
                        row = {
                            "pair": pair_dir.name,
                            "task": str(run["task_id"]),
                            "candidate_id": record.get("candidate_id"),
                            "occupancy_class": occupancy_class,
                            "total_width_deg": "" if occupancy_class == "screen_geometry_invalid"
                                               else str(float(width_text)),
                            "windows": record.get("zone_screen_%s_windows" % region_id, ""),
                            "qualification_level": record.get("qualification_level", ""),
                            "selection_eligible": record.get("selection_eligible", ""),
                            "bearing_abs_deg": "", "bearing_rel_deg": "", "bearing_fold_deg": "",
                            "clear_min": "", "clear_over_l1": "", "clear_source": "",
                        }
                        if occupancy_class != "screen_geometry_invalid":
                            l1 = float(record["l1"])
                            if not l1 > 0.0:
                                fail("non-positive l1 at %s" % where)
                            bx, by = float(record["base_x"]), float(record["base_y"])
                            base_angle = float(record["base_angle"])
                            o4x = bx + l1 * math.cos(math.radians(base_angle))
                            o4y = by + l1 * math.sin(math.radians(base_angle))
                            bearing_abs = math.degrees(math.atan2(cy - by, cx - bx))
                            bearing_rel = wrap180(bearing_abs - base_angle)
                            d_o2 = math.hypot(cx - bx, cy - by)
                            d_o4 = math.hypot(cx - o4x, cy - o4y)
                            d_seg = segment_distance(cx, cy, bx, by, o4x, o4y)
                            clearances = {"o2": d_o2 - radius, "o4": d_o4 - radius, "seg": d_seg - radius}
                            clear_source = min(clearances, key=clearances.get)
                            clear_min = clearances[clear_source]
                            row.update({
                                "l1": l1, "l2": record["l2"], "l3": record["l3"], "l4": record["l4"],
                                "base_x": bx, "base_y": by, "base_angle": base_angle,
                                "bearing_abs_deg": bearing_abs, "bearing_rel_deg": bearing_rel,
                                "bearing_fold_deg": fold180(bearing_rel),
                                "clear_min": clear_min, "clear_over_l1": clear_min / l1,
                                "clear_source": clear_source,
                            })
                        rows.append(row)
                        task_rows[task_key].append(row)

    # ---- fail-closed consistency against the recorded menu-B tallies ----
    expected_keys = set(EXPECTED_TALLIES)
    found_keys = set(tallies)
    if found_keys != expected_keys:
        fail("task keys do not match the recorded menu-B tasks.\n  missing: %s\n  extra: %s"
             % (sorted(expected_keys - found_keys) or "none",
                sorted(found_keys - expected_keys) or "none"))
    mismatched = []
    for key in sorted(expected_keys):
        observed = {c: tallies[key].get(c, 0) for c in CLASS_ORDER}
        if observed != EXPECTED_TALLIES[key]:
            mismatched.append("  %s: observed %s vs menu-B %s" % (key, observed, EXPECTED_TALLIES[key]))
    if mismatched:
        fail("occupancy tallies disagree with the recorded menu-B run:\n" + "\n".join(mismatched))
    digest_note = "not found (row-count cross-check skipped)"
    if DIGEST_CSV.is_file():
        with DIGEST_CSV.open(newline="", encoding="utf-8") as handle:
            digest_rows = sum(1 for _ in csv.reader(handle)) - 1
        if digest_rows != len(rows):
            fail("row count %d disagrees with menu-B digest CSV rows %d (%s)" % (len(rows), digest_rows, DIGEST_CSV))
        digest_note = "MATCH (%d rows)" % digest_rows

    # ---- stats ----
    def dominance(field):
        means = []
        within = []
        for key in sorted(task_rows):
            values = [r[field] for r in task_rows[key] if r.get(field, "") != ""]
            means.append(statistics.mean(values))
            within.append(statistics.pstdev(values) if len(values) > 1 else 0.0)
        between = statistics.pstdev(means)
        within_mean = statistics.mean(within)
        ratio = between / within_mean if within_mean > 0 else None
        return {"between_task": between, "within_task": within_mean,
                "dominance_ratio": ratio}

    fold_dominance = dominance("bearing_fold_deg")
    clear_dominance = dominance("clear_over_l1")

    per_class = {}
    for occupancy_class in CLASS_ORDER:
        members = [r for r in rows if r["occupancy_class"] == occupancy_class and r["bearing_rel_deg"] != ""]
        if not members:
            per_class[occupancy_class] = {"n": 0}
            continue
        folds = [r["bearing_fold_deg"] for r in members]
        rels = [r["bearing_rel_deg"] for r in members]
        clears = [r["clear_over_l1"] for r in members]
        per_class[occupancy_class] = {
            "n": len(members),
            "bearing_fold_median": statistics.median(folds),
            "bearing_fold_min": min(folds), "bearing_fold_max": max(folds),
            "bearing_rel_circular_mean": circular_mean(rels),
            "bearing_rel_circular_concentration": circular_concentration(rels),
            "clear_over_l1_median": statistics.median(clears),
        }

    per_task = {}
    for key in sorted(task_rows):
        members = [r for r in task_rows[key] if r["bearing_rel_deg"] != ""]
        counts = {c: tallies[key].get(c, 0) for c in CLASS_ORDER}
        dominant = max(CLASS_ORDER[:4], key=lambda c: counts[c])
        per_task[key] = {
            "n": len(task_rows[key]), "tallies": counts, "dominant_class": dominant,
            "bearing_fold_mean": statistics.mean(r["bearing_fold_deg"] for r in members) if members else None,
            "bearing_rel_circular_mean": circular_mean([r["bearing_rel_deg"] for r in members]),
            "clear_over_l1_mean": statistics.mean(r["clear_over_l1"] for r in members) if members else None,
        }

    counter = {}
    for key in ("corpus_pair_03/catcher", "corpus_pair_06/gate"):
        if key not in task_rows:
            continue
        counter[key] = {
            "dominant_class": per_task[key]["dominant_class"],
            "bearing_fold_mean": per_task[key]["bearing_fold_mean"],
            "bearing_rel_circular_mean": per_task[key]["bearing_rel_circular_mean"],
        }
    fold_gap = None
    circ_gap = None
    if len(counter) == 2:
        a, b = counter["corpus_pair_03/catcher"], counter["corpus_pair_06/gate"]
        if a["bearing_fold_mean"] is not None and b["bearing_fold_mean"] is not None:
            fold_gap = abs(a["bearing_fold_mean"] - b["bearing_fold_mean"])
        circ_gap = circular_separation(a["bearing_rel_circular_mean"],
                                       b["bearing_rel_circular_mean"])

    # ---- outputs ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_columns = ["pair", "task", "candidate_id", "occupancy_class", "total_width_deg", "windows",
                   "l1", "l2", "l3", "l4", "base_x", "base_y", "base_angle",
                   "bearing_abs_deg", "bearing_rel_deg", "bearing_fold_deg",
                   "clear_min", "clear_over_l1", "clear_source",
                   "qualification_level", "selection_eligible"]
    with (OUT_DIR / "bearing_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    valid_points = [(r["bearing_rel_deg"], r["clear_over_l1"],
                     COLORS[r["occupancy_class"]], r["occupancy_class"] == "full360")
                    for r in rows if r["bearing_rel_deg"] != ""]
    y_values = [p[1] for p in valid_points]
    y0, y1 = min(y_values), max(y_values)
    if y1 - y0 < 1e-9:
        y0, y1 = y0 - 0.1, y1 + 0.1
    pad = (y1 - y0) * 0.05
    y0, y1 = y0 - pad, y1 + pad

    pooled_rel = scatter_svg(valid_points, -180, 180, y0, y1, 640, 430,
                             "Pooled: bearing vs clearance (all tasks, pre-dedup)",
                             "bearing_rel: zone direction vs ground link (deg)",
                             "clear_min / l1")
    pooled_fold = scatter_svg([(r["bearing_fold_deg"], r["clear_over_l1"],
                               COLORS[r["occupancy_class"]], r["occupancy_class"] == "full360")
                              for r in rows if r["bearing_rel_deg"] != ""],
                             0, 90, y0, y1, 640, 430,
                             "Pooled: folded bearing (distance from pivot line) vs clearance",
                             "bearing_fold: angular distance from pivot line (deg)",
                             "clear_min / l1")
    task_svgs = []
    for key in sorted(task_rows):
        members = [r for r in task_rows[key] if r["bearing_rel_deg"] != ""]
        task_y0, task_y1 = y0, y1
        pts = [(r["bearing_rel_deg"], r["clear_over_l1"],
                COLORS[r["occupancy_class"]], r["occupancy_class"] == "full360")
               for r in members]
        task_svgs.append(scatter_svg(pts, -180, 180, task_y0, task_y1, 320, 235,
                                     "%s  (n=%d, dominant %s)" % (key, per_task[key]["n"], per_task[key]["dominant_class"]),
                                     "bearing_rel (deg)", "clear/l1"))
    legend = "".join(
        '<span style="margin-right:18px"><svg width="12" height="12" viewBox="0 0 12 12">'
        '<circle cx="6" cy="6" r="5" fill="%s"/></svg> %s</span>' % (COLORS[c], c)
        for c in CLASS_ORDER)
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>OMTS C.3 bearing map</title>
<style>
body { font-family: Helvetica, Arial, sans-serif; margin: 24px; color: #222; }
h1 { font-size: 20px; } h2 { font-size: 16px; margin-top: 28px; }
.note { background: #f6f3ea; border: 1px solid #e0d9c8; padding: 10px 14px; max-width: 900px; font-size: 13px; }
.grid { display: flex; flex-wrap: wrap; gap: 8px; }
</style></head><body>
<h1>OMTS transform-space map, menu item C.3: bearing axis</h1>
<p>%d pre-dedup candidate rows, %d tasks, corpus runs/sync-corpus-07.</p>
<div class="note"><b>Honesty note:</b> widths are SAMPLED occupancy of the shared
zone at the recorded screen step - this is not collision certification, and rows
are pre-dedup (counts may differ from JOB.md). Bearing is a direction only: it
says nothing about distance and nothing between samples. Full-360 rows are drawn
as purple diamonds.</div>
<div style="margin: 10px 0 4px">%s</div>
<h2>Pooled maps</h2>
%s
%s
<h2>Per-task maps (fixed axes for comparability)</h2>
<div class="grid">%s</div>
</body></html>
""" % (len(rows), len(task_rows), legend, pooled_rel, pooled_fold, "".join(task_svgs))
    (OUT_DIR / "bearing_map.html").write_text(html, encoding="utf-8")

    meta = {
        "menu": "C.3 bearing axis",
        "script": "runs/analysis/map_c3.py",
        "corpus": "runs/sync-corpus-07",
        "honesty_note": "sampled occupancy, not collision certification; pre-dedup rows; "
                        "bearing is a direction only",
        "region_ids": sorted(set(region_ids_seen)),
        "caps_deg": sorted(set(caps_seen)),
        "steps": sorted(set(steps_seen)),
        "rows_total": len(rows),
        "digest_cross_check": digest_note,
        "per_task": per_task,
        "per_class": per_class,
        "dominance": {"bearing_fold_deg": fold_dominance, "clear_over_l1": clear_dominance},
        "counterexample_03c_vs_06g": (
            {"pair_03_catcher": counter["corpus_pair_03/catcher"],
             "pair_06_gate": counter["corpus_pair_06/gate"],
             "fold_gap_deg": fold_gap, "circular_gap_deg": circ_gap}
            if len(counter) == 2
            else {"note": "counterexample tasks not present in this corpus"}),
    }
    with (OUT_DIR / "bearing_map_meta.json").open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2, sort_keys=True)
        handle.write("\n")

    # ---- stdout report ----
    caps = sorted(set(caps_seen))
    steps = sorted(set(steps_seen))
    print("OMTS transform-space map (menu item C.3, bearing axis)")
    print("Corpus: runs/sync-corpus-07  (%d pre-dedup candidate rows, %d task(s))"
          % (len(rows), len(task_rows)))
    print("Shared-zone screen cap(s): %s deg; sampling steps: %s" % (caps, steps))
    print("Honesty note: widths are SAMPLED occupancy of the shared zone at")
    print("the recorded screen step - not collision certification, and rows")
    print("are pre-dedup (counts may differ from JOB.md tallies).")
    print("Cross-check vs menu-B digest: %s" % digest_note)
    for pair in sorted(pair_counts):
        print("  %s: %d rows" % (pair, pair_counts[pair]))
    print("Cross-check vs recorded menu-B tallies: PASS (%d/%d tasks)"
          % (len(EXPECTED_TALLIES), len(EXPECTED_TALLIES)))
    print()
    print("Per-task bearing stats (dominant class, mean bearing_fold, circular mean bearing_rel):")
    for key in sorted(per_task):
        info = per_task[key]
        fold = info["bearing_fold_mean"]
        circ = info["bearing_rel_circular_mean"]
        print("  %-30s n=%-3d dominant %-16s fold mean %6s   circ mean %s deg"
              % (key, info["n"], info["dominant_class"],
                 "-" if fold is None else "%.2f" % fold,
                 "-" if circ is None else "%7.2f" % circ))
    print()
    print("Per-class bearing stats (valid rows only):")
    print("  %-22s %5s   %-26s %-16s %s" % ("class", "n", "fold med (range)", "circ mean", "clear/l1 med"))
    for occupancy_class in CLASS_ORDER:
        info = per_class[occupancy_class]
        if info["n"] == 0:
            print("  %-22s %5d   -" % (occupancy_class, 0))
            continue
        circ = info["bearing_rel_circular_mean"]
        conc = info["bearing_rel_circular_concentration"]
        print("  %-22s %5d   %6.2f (%5.2f..%5.2f)   %7.2f (R=%.2f)   %6.3f"
              % (occupancy_class, info["n"],
                 info["bearing_fold_median"], info["bearing_fold_min"], info["bearing_fold_max"],
                 circ, conc, info["clear_over_l1_median"]))
    print()
    fmt_ratio = lambda d: ("%.3f vs %.3f (ratio %.2fx)" % (d["between_task"], d["within_task"], d["dominance_ratio"])
                            if d["dominance_ratio"] is not None else "within-task spread is zero")
    print("Dominance (bearing_fold):   %s" % fmt_ratio(fold_dominance))
    print("Dominance (clear/l1):       %s   [C.2 reference: 0.135 vs 0.094, 1.44x]" % fmt_ratio(clear_dominance))
    print("Counterexample check (P2):")
    for key in sorted(counter):
        info = counter[key]
        print("  %-24s dominant %-16s fold mean %s   circ mean %s deg"
              % (key, info["dominant_class"],
                 "-" if info["bearing_fold_mean"] is None else "%.2f" % info["bearing_fold_mean"],
                 "-" if info["bearing_rel_circular_mean"] is None else "%.2f" % info["bearing_rel_circular_mean"]))
    print("  fold gap |03c-06g| = %s deg; circular separation = %s deg"
          % ("-" if fold_gap is None else "%.2f" % fold_gap,
             "-" if circ_gap is None else "%.2f" % circ_gap))
    print("Report (open in a browser): runs/analysis/transform-map-03/bearing_map.html")
    print("Per-row data:              runs/analysis/transform-map-03/bearing_rows.csv")
    print("Stats/meta:                runs/analysis/transform-map-03/bearing_map_meta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
