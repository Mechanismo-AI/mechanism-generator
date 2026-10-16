#!/usr/bin/env python3
"""OMTS menu item C: transform-space map over menu-item-B's occupancy digest.

Reads runs/analysis/occupancy-digest-01/occupancy_digest.csv (the menu-B
digest output; run digest_b.py first) and maps every candidate into placement
space relative to the shared zone, colored by occupancy class. Writes a
self-contained HTML report (inline SVG, no dependencies, open in a browser):

  runs/analysis/transform-map-01/transform_map.html
  runs/analysis/transform-map-01/transform_map_meta.json

Coordinates:
  x = clear_min  (zone-edge clearance to nearest of O2/O4/ground segment)
  y = l2_over_l1 (crank ratio)
  alt pooled panel: y = transmission_min_deg
Panels: two pooled scatters + one per task, all on the SAME axis ranges so
placements are directly comparable across tasks.

Fail-closed: missing digest file, missing columns, unknown class labels, or
a malformed generated SVG abort loudly. Rows missing a coordinate are
excluded and counted everywhere, never silently dropped.
"""
import csv
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DIGEST = ROOT / "runs" / "analysis" / "occupancy-digest-01" / "occupancy_digest.csv"
OUTDIR = ROOT / "runs" / "analysis" / "transform-map-01"
CLASSES = ["never", "quick_pass", "drag_over_cap", "full360",
           "screen_geometry_invalid"]
COLORS = {
    "never": "#1f77b4",
    "quick_pass": "#2ca02c",
    "drag_over_cap": "#ff7f0e",
    "full360": "#d62728",
    "screen_geometry_invalid": "#7f7f7f",
}
REQ = ["corpus", "task_id", "target_dir", "candidate_id", "class",
       "clear_min", "l2_over_l1", "clear_to_O2", "clear_to_O4",
       "clear_to_segment", "grashof_margin", "transmission_min_deg",
       "width_deg"]


def die(msg):
    print("map_c: FAIL-CLOSED: %s" % msg, file=sys.stderr)
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


def fmt(v, nd=2):
    return "-" if v is None else ("%." + str(nd) + "f") % v


def med(vals):
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def spread(vals):
    return statistics.pstdev(vals) if len(vals) >= 2 else 0.0


def pad(lo, hi, frac=0.05):
    if hi <= lo:
        c = lo if lo is not None else 0.0
        return c - 0.5, c + 0.5
    m = (hi - lo) * frac
    return lo - m, hi + m


def xtick_label(v):
    s = "%.2f" % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def svg_scatter(points, xr, yr, xlabel, ylabel, title, sub, w=400, h=280):
    """points: list of (x, y, color, tip). xr/yr: (lo, hi) fixed ranges."""
    ML, MR, MT, MB = 62, 14, 30, 44
    def X(v): return ML + (v - xr[0]) / (xr[1] - xr[0]) * (w - ML - MR)
    def Y(v): return h - MB - (v - yr[0]) / (yr[1] - yr[0]) * (h - MT - MB)
    p = []
    p.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" font-family="sans-serif">' % (w, h, w, h))
    p.append('<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>'
             % (w, h))
    p.append('<text x="%d" y="16" font-size="13" font-weight="bold" '
             'fill="#222">%s</text>' % (ML, escape(title)))
    if sub:
        p.append('<text x="%d" y="16" font-size="11" fill="#666" '
                 'text-anchor="end">%s</text>' % (w - MR, escape(sub)))
    # grid + ticks
    for i in range(6):
        xv = xr[0] + (xr[1] - xr[0]) * i / 5.0
        yv = yr[0] + (yr[1] - yr[0]) * i / 5.0
        p.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" '
                 'stroke="#eeeeee" stroke-width="1"/>'
                 % (X(xv), MT, X(xv), h - MB))
        p.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" '
                 'stroke="#eeeeee" stroke-width="1"/>'
                 % (ML, Y(yv), w - MR, Y(yv)))
        p.append('<text x="%.1f" y="%d" font-size="10" fill="#555" '
                 'text-anchor="middle">%s</text>'
                 % (X(xv), h - MB + 14, escape(xtick_label(xv))))
        p.append('<text x="%d" y="%.1f" font-size="10" fill="#555" '
                 'text-anchor="end" dominant-baseline="middle">%s</text>'
                 % (ML - 6, Y(yv), escape(xtick_label(yv))))
    # axes
    p.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#999"/>'
             % (ML, MT, ML, h - MB))
    p.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#999"/>'
             % (ML, h - MB, w - MR, h - MB))
    p.append('<text x="%d" y="%d" font-size="11" fill="#333" '
             'text-anchor="middle">%s</text>'
             % ((ML + w - MR) // 2, h - 8, escape(xlabel)))
    p.append('<text x="12" y="%d" font-size="11" fill="#333" '
             'text-anchor="middle" transform="rotate(-90 12 %d)">%s</text>'
             % ((MT + h - MB) // 2, (MT + h - MB) // 2, escape(ylabel)))
    if not points:
        p.append('<text x="%d" y="%d" font-size="12" fill="#999" '
                 'text-anchor="middle">no data</text>'
                 % ((ML + w - MR) // 2, (MT + h - MB) // 2))
    for x, y, color, tip in points:
        p.append('<circle cx="%.2f" cy="%.2f" r="3" fill="%s" '
                 'fill-opacity="0.78" stroke="#333" stroke-width="0.5">'
                 '<title>%s</title></circle>' % (X(x), Y(y), color, escape(tip)))
    p.append("</svg>")
    return "".join(p)


def main():
    if not (ROOT / "pyproject.toml").is_file():
        die("expected repo root at %s (pyproject.toml not found)" % ROOT)
    if not DIGEST.is_file():
        die("menu-B digest not found at %s - run "
            "'python runs/analysis/digest_b.py' first" % DIGEST)

    with DIGEST.open(newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        missing = [c for c in REQ if c not in header]
        if missing:
            die("digest %s missing columns %s (regenerate it with digest_b.py)"
                % (DIGEST, missing))
        raw = list(reader)
    if not raw:
        die("digest %s has no data rows" % DIGEST)

    rows, excluded = [], Counter()
    for r in raw:
        klass = (r.get("class") or "").strip()
        if klass not in CLASSES:
            die("unknown class label %r in digest row candidate %s - digest "
                "and map_c disagree" % (klass, r.get("candidate_id")))
        cm = fnum(r.get("clear_min"))
        lr = fnum(r.get("l2_over_l1"))
        if cm is None or lr is None:
            excluded[klass] += 1
            continue
        rows.append({
            "corpus": r["corpus"], "task_id": r["task_id"],
            "target_dir": r.get("target_dir", ""),
            "candidate_id": r.get("candidate_id", ""),
            "class": klass, "clear_min": cm, "l2_over_l1": lr,
            "transmission_min_deg": fnum(r.get("transmission_min_deg")),
            "grashof_margin": fnum(r.get("grashof_margin")),
            "width_deg": fnum(r.get("width_deg")),
        })
    if not rows:
        die("no usable rows (all %d lacked clear_min or l2/l1)" % len(raw))
    if excluded:
        print("map_c: NOTE excluding %d rows without clear_min/l2_over_l1: %s"
              % (sum(excluded.values()),
                 ", ".join("%s %d" % (k, excluded[k]) for k in CLASSES
                           if excluded.get(k))),
              file=sys.stderr)

    # pooled ranges (fixed for every panel so tasks are comparable)
    xr = pad(min(r["clear_min"] for r in rows),
             max(r["clear_min"] for r in rows))
    yr = pad(min(r["l2_over_l1"] for r in rows),
             max(r["l2_over_l1"] for r in rows))
    trans = [r["transmission_min_deg"] for r in rows
             if r["transmission_min_deg"] is not None]
    tr = pad(min(trans), max(trans)) if trans else (0.0, 1.0)

    def tip(r):
        return ("%s / %s / %s | class=%s clear_min=%.3f l2/l1=%.3f "
                "trans_min=%s width=%s"
                % (r["corpus"], r["task_id"], r["candidate_id"], r["class"],
                   r["clear_min"], r["l2_over_l1"],
                   fmt(r["transmission_min_deg"]), fmt(r["width_deg"])))

    panels = []  # (svg_string, kind)
    pA = [(r["clear_min"], r["l2_over_l1"], COLORS[r["class"]], tip(r))
          for r in rows]
    panels.append((svg_scatter(
        pA, xr, yr, "clear_min (zone clearance)", "l2/l1 (crank ratio)",
        "Pooled: all tasks", "%d candidates" % len(rows), 760, 520), "pooled-A"))
    pB = [(r["clear_min"], r["transmission_min_deg"], COLORS[r["class"]],
           tip(r)) for r in rows if r["transmission_min_deg"] is not None]
    panels.append((svg_scatter(
        pB, xr, tr, "clear_min (zone clearance)",
        "transmission min (deg)", "Pooled: clearance vs transmission",
        "%d candidates" % len(pB), 760, 520), "pooled-B"))

    tasks = defaultdict(list)
    for r in rows:
        tasks[(r["corpus"], r["task_id"])].append(r)
    task_panels = []
    for key in sorted(tasks):
        rs = tasks[key]
        cnt = Counter(r["class"] for r in rs)
        sub = " ".join("%s %d" % (k, cnt.get(k, 0)) for k in CLASSES
                       if cnt.get(k, 0))
        pts = [(r["clear_min"], r["l2_over_l1"], COLORS[r["class"]], tip(r))
               for r in rs]
        title = "%s / %s" % key
        s = svg_scatter(pts, xr, yr, "clear_min", "l2/l1", title, sub,
                        400, 290)
        panels.append((s, "task %s/%s" % key))
        task_panels.append((key, s))

    # self-check: every generated SVG must parse as strict XML
    for s, kind in panels:
        try:
            ET.fromstring(s)
        except ET.ParseError as e:
            die("generated SVG (%s) is malformed: %s" % (kind, e))

    # stats
    per_class = {}
    for k in CLASSES:
        rs = [r for r in rows if r["class"] == k]
        if not rs:
            continue
        cms = [r["clear_min"] for r in rs]
        lrs = [r["l2_over_l1"] for r in rs]
        per_class[k] = {
            "n": len(rs),
            "clear_min_median": med(cms),
            "clear_min_range": [min(cms), max(cms)],
            "l2_over_l1_median": med(lrs),
            "l2_over_l1_range": [min(lrs), max(lrs)],
        }
    task_means = {("%s/%s" % k): {
        "n": len(rs),
        "tallies": {c: Counter(r["class"] for r in rs).get(c, 0)
                    for c in CLASSES},
        "clear_min_mean": statistics.mean(r["clear_min"] for r in rs),
        "clear_min_std": spread([r["clear_min"] for r in rs]),
        "l2_over_l1_mean": statistics.mean(r["l2_over_l1"] for r in rs),
    } for k, rs in sorted(tasks.items())}

    between = spread([m["clear_min_mean"] for m in task_means.values()])
    within = statistics.mean(m["clear_min_std"] for m in task_means.values())

    read_lines = ["Per-class placement stats (usable rows only):"]
    for k in CLASSES:
        s = per_class.get(k)
        if not s:
            continue
        read_lines.append(
            "  %-24s n=%-4d clear_min med %s (%s..%s) | l2/l1 med %s (%s..%s)"
            % (k, s["n"], fmt(s["clear_min_median"]),
               fmt(s["clear_min_range"][0]), fmt(s["clear_min_range"][1]),
               fmt(s["l2_over_l1_median"]), fmt(s["l2_over_l1_range"][0]),
               fmt(s["l2_over_l1_range"][1])))
    read_lines.append("Spread of per-task mean clear_min (between tasks): %.3f"
                      % between)
    read_lines.append("Mean of per-task clear_min std (within tasks): %.3f"
                      % within)
    read_lines.append("Per-task means (dominant class, mean clear_min):")
    for name, m in task_means.items():
        dom = max(m["tallies"], key=lambda c: m["tallies"][c])
        read_lines.append("  %-34s n=%-3d dominant %-16s mean clear %.3f"
                         % (name, m["n"], dom, m["clear_min_mean"]))
    reading = "\n".join(read_lines)

    # HTML
    legend = " ".join(
        '<span class="key"><span class="dot" style="background:%s"></span>'
        "%s</span>" % (COLORS[k], k) for k in CLASSES)
    task_html = "\n".join('<div class="panel">%s</div>' % s
                         for _, s in task_panels)
    excl_txt = ("Excluded %d of %d digest rows lacking clear_min/l2_over_l1: %s"
                % (sum(excluded.values()), len(raw),
                   ", ".join("%s %d" % (k, excluded[k]) for k in CLASSES
                             if excluded.get(k)) or "none"))
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>OMTS transform-space map (menu item C)</title>
<style>
 body { font-family: sans-serif; margin: 24px; color: #222; }
 h1 { font-size: 20px; } h2 { font-size: 15px; margin: 24px 0 8px; }
 .meta, .note { font-size: 12px; color: #555; max-width: 760px; }
 .note { background: #f6f6f6; padding: 8px 10px; border-left: 3px solid #999; }
 .legend { margin: 10px 0 4px; }
 .key { font-size: 12px; margin-right: 14px; }
 .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
        margin-right: 4px; vertical-align: middle; border: 1px solid #333; }
 .grid { display: flex; flex-wrap: wrap; gap: 6px; max-width: 1240px; }
 .panel { border: 1px solid #ddd; }
 pre { background: #f6f6f6; padding: 10px; font-size: 12px; }
</style></head><body>
<h1>OMTS transform-space map (menu item C)</h1>
<p class="meta">Source: runs/analysis/occupancy-digest-01/occupancy_digest.csv
(menu item B digest, corpus-07, __DATE__). __USABLE__. Hover any point for its
candidate identity. All panels share the same axis ranges.</p>
<p class="note">__EXCL__<br>Same honesty note as menu item B: classes are
SAMPLED occupancy of the shared zone at the recorded screen step - this is not
collision certification, and rows are pre-dedup.</p>
<div class="legend">__LEGEND__</div>
<h2>Pooled: clearance vs crank ratio</h2>
__PANELA__
<h2>Pooled: clearance vs transmission minimum</h2>
__PANELB__
<h2>Per-task panels (same axes as pooled)</h2>
<div class="grid">
__TASKS__
</div>
<h2>Auto-read (also printed to stdout)</h2>
<pre>__READING__</pre>
</body></html>
"""
    html = (html
            .replace("__DATE__", str(date.today()))
            .replace("__USABLE__", "%d usable candidates in %d tasks"
                     % (len(rows), len(tasks)))
            .replace("__EXCL__", excl_txt)
            .replace("__LEGEND__", legend)
            .replace("__PANELA__", panels[0][0])
            .replace("__PANELB__", panels[1][0])
            .replace("__TASKS__", task_html)
            .replace("__READING__", escape(reading)))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "transform_map.html").write_text(html)
    meta = {
        "date": str(date.today()),
        "source": "runs/analysis/occupancy-digest-01/occupancy_digest.csv",
        "usable_rows": len(rows),
        "digest_rows": len(raw),
        "excluded_by_class": {k: excluded.get(k, 0) for k in CLASSES},
        "axis_x": "clear_min", "axis_y": "l2_over_l1",
        "x_range": list(xr), "y_range": list(yr),
        "per_class": per_class, "per_task": task_means,
        "between_task_clear_std": between,
        "mean_within_task_clear_std": within,
        "note": "sampled occupancy classes, not collision certification",
    }
    (OUTDIR / "transform_map_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n")

    print("OMTS transform-space map (menu item C)")
    print("Source: menu-B digest, %d usable of %d rows; %s"
          % (len(rows), len(raw), excl_txt))
    print("")
    print(reading)
    print("")
    print("Report (open in a browser): "
          "runs/analysis/transform-map-01/transform_map.html")
    print("Stats/meta: runs/analysis/transform-map-01/transform_map_meta.json")


if __name__ == "__main__":
    main()
