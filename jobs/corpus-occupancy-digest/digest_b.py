#!/usr/bin/env python3
"""OMTS menu item B: occupancy-width digest over corpus-07 fresh screened runs.

Pure analysis, no repo changes. For every pre-dedup candidate row recorded in
the corpus-07 run trees, classify the sampled occupancy of the shared zone:

  never                   total width <= 0 (zone never touched)
  quick_pass              width <= sidecar cap
  drag_over_cap           cap < width < 360
  full360                 width >= 360 (degenerate sweep)
  screen_geometry_invalid geometry invalid or width missing

and record the four-bar geometry behind each class (link ratios, Grashof
margin, zone clearances, transmission-angle extremes). Outputs:

  runs/analysis/occupancy-digest-01/occupancy_digest.csv   all rows
  runs/analysis/occupancy-digest-01/digest_summary.json     tallies + stats
  runs/analysis/occupancy-digest-01/digest_report.txt       same as stdout

Fail-closed: missing files, unreadable sidecars, non-circle zones, or missing
CSV columns abort the whole run with the full list of problems found.
"""
import csv
import json
import math
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

EPS = 1e-6
ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "runs" / "sync-corpus-07"
OUTDIR = ROOT / "runs" / "analysis" / "occupancy-digest-01"
CLASSES = ["never", "quick_pass", "drag_over_cap", "full360",
           "screen_geometry_invalid"]
TABLE_FEATURES = [
    ("width_deg", "width"), ("l2_over_l1", "l2/l1"),
    ("l3_over_l1", "l3/l1"), ("l4_over_l1", "l4/l1"),
    ("bar_over_l1", "bar/l1"), ("grashof_margin", "grashof"),
    ("clear_min", "clear_min"), ("transmission_min_deg", "trans_min"),
]


def die(msg):
    print("digest_b: FAIL-CLOSED: %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def fnum(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fbool(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def as_point(c, where):
    if isinstance(c, dict):
        try:
            return float(c["x"]), float(c["y"])
        except (KeyError, TypeError, ValueError):
            die("%s: center dict missing numeric x/y" % where)
    if isinstance(c, (list, tuple)) and len(c) == 2:
        try:
            return float(c[0]), float(c[1])
        except (TypeError, ValueError):
            die("%s: center list not numeric" % where)
    die("%s: unsupported center format %r" % (where, c))


def seg_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def transmission_extremes(l1, l2, l3, l4):
    """Min/max transmission angle (deg) at the two collinear crank/ground
    positions. Returns (None, None) if links are missing or degenerate;
    an unreachable extreme (|cos|>1) is skipped, not clamped."""
    if None in (l1, l2, l3, l4) or l3 <= 0 or l4 <= 0:
        return None, None
    out = []
    for d in (abs(l1 - l2), l1 + l2):
        cos_mu = (l3 * l3 + l4 * l4 - d * d) / (2.0 * l3 * l4)
        if -1.0 - EPS <= cos_mu <= 1.0 + EPS:
            out.append(math.degrees(math.acos(max(-1.0, min(1.0, cos_mu)))))
    if not out:
        return None, None
    return min(out), max(out)


def grashof_margin(l1, l2, l3, l4):
    """(shortest + longest) - (other two). >0 Grashof, ==0 change point,
    <0 double-rocker (no link makes a full revolution)."""
    ls = [l1, l2, l3, l4]
    if None in ls or min(ls) <= 0:
        return None
    s, L = min(ls), max(ls)
    return (s + L) - (sum(ls) - s - L)


def load_sidecar(path, cache):
    if path in cache:
        return cache[path]
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        die("sidecar %s: unreadable (%s)" % (path, e))
    regions = data.get("regions") or []
    screen = data.get("screen") or []
    if not screen:
        die("sidecar %s: no screen entries" % path)
    ent = screen[0]
    rid = ent.get("region")
    reg = next((r for r in regions if r.get("id") == rid), None)
    if reg is None:
        die("sidecar %s: screen region %r not in regions" % (path, rid))
    if reg.get("shape") != "circle":
        die("sidecar %s: region %r shape %r, digest assumes circle"
            % (path, rid, reg.get("shape")))
    cx, cy = as_point(reg.get("center"), "sidecar %s" % path)
    r = fnum(reg.get("radius"))
    if r is None or r < 0:
        die("sidecar %s: bad radius %r" % (path, reg.get("radius")))
    cap = fnum(ent.get("max_total_width_deg"))
    if cap is None:
        die("sidecar %s: screen entry missing max_total_width_deg" % path)
    out = {"region": rid, "cx": cx, "cy": cy, "r": r, "cap": cap}
    cache[path] = out
    return out


def required_columns(rid):
    return ["candidate_id", "l1", "l2", "l3", "l4", "bar_length",
            "base_x", "base_y", "base_angle", "zone_screen_geometry_valid",
            "zone_screen_%s_total_width_deg" % rid,
            "zone_screen_%s_windows" % rid]


def make_row(corpus, task_id, target_dir, row, side):
    rid = side["region"]
    width = fnum(row.get("zone_screen_%s_total_width_deg" % rid))
    windows = (row.get("zone_screen_%s_windows" % rid) or "").strip()
    geom_ok = fbool(row.get("zone_screen_geometry_valid", ""))
    cap = side["cap"]
    if not geom_ok or width is None:
        klass = "screen_geometry_invalid"
    elif width >= 360.0 - EPS:
        klass = "full360"
    elif width <= 0.0:
        klass = "never"
    elif width <= cap:
        klass = "quick_pass"
    else:
        klass = "drag_over_cap"

    l1, l2 = fnum(row.get("l1")), fnum(row.get("l2"))
    l3, l4 = fnum(row.get("l3")), fnum(row.get("l4"))
    bar = fnum(row.get("bar_length"))
    bx, by = fnum(row.get("base_x")), fnum(row.get("base_y"))
    bang = fnum(row.get("base_angle"))
    ox = oy = c2 = c4 = cseg = None
    if None not in (l1, bx, by, bang):
        ox = bx + l1 * math.cos(math.radians(bang))
        oy = by + l1 * math.sin(math.radians(bang))
        c2 = math.hypot(side["cx"] - bx, side["cy"] - by) - side["r"]
        c4 = math.hypot(side["cx"] - ox, side["cy"] - oy) - side["r"]
        cseg = seg_distance(side["cx"], side["cy"], bx, by, ox, oy) - side["r"]
    clear_vals = [v for v in (c2, c4, cseg) if v is not None]
    tmin, _tmax = transmission_extremes(l1, l2, l3, l4)
    div = lambda x: (x / l1) if (l1 not in (None, 0) and x is not None) else None
    return {
        "corpus": corpus, "task_id": task_id, "target_dir": target_dir,
        "candidate_id": row.get("candidate_id"),
        "branch_sign": row.get("branch_sign"),
        "qualification_level": row.get("qualification_level"),
        "selection_eligible": row.get("selection_eligible"),
        "class": klass, "width_deg": width, "windows": windows,
        "l1": l1, "l2": l2, "l3": l3, "l4": l4, "bar_length": bar,
        "l2_over_l1": div(l2), "l3_over_l1": div(l3),
        "l4_over_l1": div(l4), "bar_over_l1": div(bar),
        "grashof_margin": grashof_margin(l1, l2, l3, l4),
        "clear_to_O2": c2, "clear_to_O4": c4, "clear_to_segment": cseg,
        "clear_min": min(clear_vals) if clear_vals else None,
        "transmission_min_deg": tmin,
        "S_ratio": fnum(row.get("S_ratio")),
        "max_link_ratio": fnum(row.get("max_link_ratio")),
        "sweep_radius_ratio": fnum(row.get("sweep_radius_ratio")),
        "target_angle_min_deg": fnum(row.get("target_angle_min_deg")),
        "global_angle_min_deg": fnum(row.get("global_angle_min_deg")),
    }


def stats_for(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"n": len(vals), "min": min(vals),
            "median": statistics.median(vals), "max": max(vals)}


def build_report(meta, tallies, class_counts, class_stats, n_rows):
    L = []
    L.append("OMTS occupancy-width digest (menu item B)")
    L.append("Corpus: runs/sync-corpus-07  (%d pre-dedup candidate rows, %d task(s))"
             % (n_rows, len(tallies)))
    L.append("Shared-zone screen cap(s): %s deg; region id(s): %s"
             % (meta["caps_deg"], meta["region_ids"]))
    L.append("Honesty note: widths are SAMPLED occupancy of the shared zone at")
    L.append("the recorded screen step - this is not collision certification,")
    L.append("and rows are pre-dedup (counts may differ from JOB.md tallies).")
    L.append("")
    L.append("Per-task tallies:")
    for key in sorted(tallies):
        c = tallies[key]
        total = sum(c.values())
        L.append("  %s / %s: never %d | quick_pass %d | drag_over_cap %d | "
                 "full360 %d | invalid %d  (%d rows)"
                 % (key[0], key[1], c["never"], c["quick_pass"],
                    c["drag_over_cap"], c["full360"],
                    c["screen_geometry_invalid"], total))
    L.append("")
    L.append("Pooled per-class medians (all variants, pre-dedup rows):")
    L.append("  %-24s %7s" % ("class", "n")
             + "".join(" %10s" % lbl for _, lbl in TABLE_FEATURES))
    for klass in CLASSES:
        s = class_stats.get(klass, {})
        cells = []
        for feat, _lbl in TABLE_FEATURES:
            st = s.get(feat)
            cells.append("%.2f" % st["median"] if st else "-")
        L.append("  %-24s %7d" % (klass, class_counts.get(klass, 0))
                 + "".join(" %10s" % c for c in cells))
    L.append("")
    L.append("Per-row data: runs/analysis/occupancy-digest-01/occupancy_digest.csv")
    L.append("Stats/meta:  runs/analysis/occupancy-digest-01/digest_summary.json")
    return "\n".join(L) + "\n"


def main():
    if not (ROOT / "pyproject.toml").is_file():
        die("expected repo root at %s (pyproject.toml not found)" % ROOT)
    if not CORPUS.is_dir():
        die("%s not found - run this on the-hub inside ~/mechanism-generator"
            % CORPUS)
    pairs = sorted(p for p in CORPUS.iterdir()
                   if p.is_dir() and p.name.startswith("corpus_pair_"))
    if not pairs:
        die("no corpus_pair_* dirs in %s" % CORPUS)

    problems = []
    rows = []
    sidecar_cache = {}

    for pair in pairs:
        plan = pair / "plan"
        rp = plan / "run_plan.json"
        if not rp.is_file():
            problems.append("%s: missing plan/run_plan.json" % pair.name)
            continue
        try:
            plan_data = json.loads(rp.read_text())
        except (OSError, json.JSONDecodeError) as e:
            problems.append("%s: run_plan.json unreadable (%s)" % (pair.name, e))
            continue
        pair_rows = 0
        for run in plan_data.get("runs", []):
            tid = run.get("task_id")
            out_root = run.get("output_root")
            zs = run.get("zone_screen_file")
            if not all((tid, out_root, zs)):
                problems.append("%s: run entry missing task_id/output_root/"
                                "zone_screen_file" % pair.name)
                continue
            side = load_sidecar(plan / zs, sidecar_cache)
            r25c = plan / out_root / "r25c"
            if not r25c.is_dir():
                problems.append("%s/%s: missing %s"
                                % (pair.name, tid, r25c.relative_to(ROOT)))
                continue
            run_dirs = sorted(d for d in r25c.iterdir() if d.is_dir())
            if not run_dirs:
                problems.append("%s/%s: no run dirs under r25c" % (pair.name, tid))
                continue
            run_dir = run_dirs[-1]  # same "latest run" choice as the driver
            tdirs = sorted(d for d in run_dir.iterdir()
                           if d.is_dir() and (d / "all_candidates.csv").is_file())
            if not tdirs:
                problems.append("%s/%s: no target dirs with all_candidates.csv "
                                "in run %s" % (pair.name, tid, run_dir.name))
                continue
            req = required_columns(side["region"])
            for td in tdirs:
                csv_path = td / "all_candidates.csv"
                with csv_path.open(newline="") as fh:
                    reader = csv.DictReader(fh)
                    header = reader.fieldnames or []
                    missing = [c for c in req if c not in header]
                    if missing:
                        problems.append("%s: missing columns %s"
                                        % (csv_path.relative_to(ROOT), missing))
                        continue
                    for row in reader:
                        rows.append(make_row(pair.name, tid, td.name, row, side))
                        pair_rows += 1
        print("  %s: %d rows" % (pair.name, pair_rows), file=sys.stderr)

    if problems:
        print("digest_b: FAIL-CLOSED - structural problems found:",
              file=sys.stderr)
        for p in problems:
            print("  - %s" % p, file=sys.stderr)
        raise SystemExit(1)
    if not rows:
        die("no candidate rows found at all")

    tallies = {}
    class_counts = Counter()
    class_stats = {k: {} for k in CLASSES}
    for r in rows:
        key = (r["corpus"], r["task_id"])
        tallies.setdefault(key, Counter())[r["class"]] += 1
        class_counts[r["class"]] += 1
        for feat, _lbl in TABLE_FEATURES:
            class_stats[r["class"]].setdefault(feat, []).append(r[feat])
    class_stats = {k: {f: stats_for(v) for f, v in feats.items()
                       if stats_for(v) is not None}
                   for k, feats in class_stats.items()}

    caps = sorted({s["cap"] for s in sidecar_cache.values()})
    regions = sorted({s["region"] for s in sidecar_cache.values()})
    meta = {
        "date": str(date.today()),
        "corpus_root": "runs/sync-corpus-07",
        "region_ids": regions,
        "caps_deg": caps,
        "note": "widths are sampled occupancy, not collision certification",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with (OUTDIR / "occupancy_digest.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = {
        "meta": meta,
        "class_counts": {k: class_counts.get(k, 0) for k in CLASSES},
        "per_task_tallies": {
            "%s/%s" % k: {c: v.get(c, 0) for c in CLASSES}
            for k, v in sorted(tallies.items())},
        "class_stats": class_stats,
    }
    (OUTDIR / "digest_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    report = build_report(meta, tallies, class_counts, class_stats, len(rows))
    (OUTDIR / "digest_report.txt").write_text(report)
    print(report, end="")


if __name__ == "__main__":
    main()
