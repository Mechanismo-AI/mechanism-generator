#!/usr/bin/env python3
# Job sixbar-gap-transfer-03: the softened-timing recompute.
#
# Reads the merged sixbar-gap-transfer-02 task JSON, rebuilds the
# recorded timing construction, validates it against the task's own
# emitted samples, then recomputes the prescribed per-sample demands
# under dwell-relaxed timing variants (the "dwell-relaxed pick and
# set-down" candidate from the -01 record). Task-side arithmetic
# only: no solver, no engine, no package code; nothing about the -02
# record is rewritten. See JOB.md in this directory.
#
# Conventions (from the -02 JOB.md audit trail):
# - design frame: millimetres, origin at gap centre on the belt line,
#   y up; the JSON's normalized sample positions are
#   (point - (0, 5)) / 275.1363... (centroid exactly (0, +5) mm by
#   symmetry, bounding-box diagonal sqrt(260^2 + 90^2));
# - timing: two clamped cubic runs (the carry, phases 0-4; the bottom
#   loop, phases 4-12 closing at phase 0), zero speed at the two
#   process stops (phases 0 and 4);
# - prescribed acceleration at the stops = vector mean of the
#   one-sided (into / out of stop) accelerations; at the two line/arc
#   junction samples (phases 6 and 10) = mean of the line-side and
#   arc-side one-sided accelerations -- the timing is C2, so both
#   sides share the spline s'':  C_arc * s'^2 / 2 + T * s''.
#
# Output: a printed report and a JSON report file (default
# runs/sixbar-gap-transfer-03/softened-timing-report.json).

import argparse
import json
import math
import os

PI = math.pi
DEG = PI / 180.0

# ---------- path model (the -02 audit-trail geometry, mm) ----------
DIAG = math.sqrt(260.0 ** 2 + 90.0 ** 2)  # 275.1363... mm
CENTROID = (0.0, 5.0)
R_CORNER = 15.0
ARC = R_CORNER * PI / 2                    # 23.5619... mm
B = [0.0, 260.0, 335.0, 335.0 + ARC, 565.0 + ARC, 565.0 + 2.0 * ARC]
L = B[5] + 75.0                            # 687.1239... mm
S_SAMPLES = [0.0, 65.0, 130.0, 195.0, 260.0, 305.0,
             B[3], B[3] + 57.5, B[3] + 115.0, B[3] + 172.5,
             B[4], B[5] + 30.0]
C_JUNCTION = (0.0, 1.0 / R_CORNER)  # arc-side curvature vector at both junctions


def point(s):
    if s <= B[1]:
        return (-130.0 + s, 50.0)
    if s <= B[2]:
        return (130.0, 50.0 - (s - B[1]))
    if s <= B[3]:
        u = -(s - B[2]) / R_CORNER
        return (115.0 + R_CORNER * math.cos(u), -25.0 + R_CORNER * math.sin(u))
    if s <= B[4]:
        return (115.0 - (s - B[3]), -40.0)
    if s <= B[5]:
        u = -PI / 2.0 - (s - B[4]) / R_CORNER
        return (-115.0 + R_CORNER * math.cos(u), -25.0 + R_CORNER * math.sin(u))
    return (-130.0, -25.0 + (s - B[5]))


def tangent(s):
    if s <= B[1]:
        return (1.0, 0.0)
    if s <= B[2]:
        return (0.0, -1.0)
    if s < B[3]:
        u = -(s - B[2]) / R_CORNER
        return (math.sin(u), -math.cos(u))
    if s <= B[4]:
        return (-1.0, 0.0)
    if s < B[5]:
        u = -PI / 2.0 - (s - B[4]) / R_CORNER
        return (math.sin(u), -math.cos(u))
    return (0.0, 1.0)


def curv(s):
    """Curvature vector q_ss (points toward the arc centre on arcs)."""
    if B[2] < s < B[3]:
        u = -(s - B[2]) / R_CORNER
        return (-math.cos(u) / R_CORNER, -math.sin(u) / R_CORNER)
    if B[4] < s < B[5]:
        u = -PI / 2.0 - (s - B[4]) / R_CORNER
        return (-math.cos(u) / R_CORNER, -math.sin(u) / R_CORNER)
    return (0.0, 0.0)


# ---------- clamped cubic spline (zero end slopes) ----------
def clamped_cubic(xs, ys):
    n = len(xs) - 1
    h = [xs[i + 1] - xs[i] for i in range(n)]
    lower = [0.0] * (n + 1)
    diag = [0.0] * (n + 1)
    upper = [0.0] * (n + 1)
    rhs = [0.0] * (n + 1)
    diag[0] = 2.0 * h[0]
    upper[0] = h[0]
    rhs[0] = 6.0 * ((ys[1] - ys[0]) / h[0] - 0.0)
    for i in range(1, n):
        lower[i] = h[i - 1]
        diag[i] = 2.0 * (h[i - 1] + h[i])
        upper[i] = h[i]
        rhs[i] = 6.0 * ((ys[i + 1] - ys[i]) / h[i] - (ys[i] - ys[i - 1]) / h[i - 1])
    lower[n] = h[n - 1]
    diag[n] = 2.0 * h[n - 1]
    rhs[n] = 6.0 * (0.0 - (ys[n] - ys[n - 1]) / h[n - 1])
    for i in range(1, n + 1):
        w = lower[i] / diag[i - 1]
        diag[i] -= w * upper[i - 1]
        rhs[i] -= w * rhs[i - 1]
    M = [0.0] * (n + 1)
    M[n] = rhs[n] / diag[n]
    for i in range(n - 1, -1, -1):
        M[i] = (rhs[i] - upper[i] * M[i + 1]) / diag[i]

    def ev(x):
        i = 0
        while i < n - 1 and x > xs[i + 1]:
            i += 1
        hh = h[i]
        a = xs[i + 1] - x
        b = x - xs[i]
        y = (M[i] * a ** 3 / 6.0 + M[i + 1] * b ** 3 / 6.0
             + (ys[i] - M[i] * hh * hh / 6.0) * a
             + (ys[i + 1] - M[i + 1] * hh * hh / 6.0) * b) / hh
        dy = (-M[i] * a * a / 2.0 + M[i + 1] * b * b / 2.0
              + (ys[i + 1] - ys[i])
              - (M[i + 1] - M[i]) * hh * hh / 6.0) / hh
        ddy = (M[i] * a + M[i + 1] * b) / hh
        return (y, dy, ddy)

    return ev


S_RUN1 = [0.0, 65.0, 130.0, 195.0, 260.0]
S_RUN2 = [260.0, 305.0, S_SAMPLES[6], S_SAMPLES[7], S_SAMPLES[8],
          S_SAMPLES[9], S_SAMPLES[10], S_SAMPLES[11], L]


def build(delta_deg):
    d = delta_deg * DEG
    t1 = [x * DEG for x in (delta_deg, 30.0, 60.0, 90.0, 120.0 - delta_deg)]
    t2 = [x * DEG for x in (120.0 + delta_deg, 150.0, 180.0, 210.0, 240.0,
                             270.0, 300.0, 330.0, 360.0 - delta_deg)]
    return (clamped_cubic(t1, S_RUN1), clamped_cubic(t2, S_RUN2), d)


def variant(delta_deg):
    """Per-sample prescribed demands and between-sample peaks for one dwell width."""
    ev1, ev2, d = build(delta_deg)
    samples_v = []
    samples_a = []
    for i in range(12):
        th = i * 30.0 * DEG
        s = S_SAMPLES[i]
        T = tangent(s)
        if delta_deg > 0.0 and i in (0, 4):
            # inside the dwell: the tool is at rest through the sample
            samples_v.append((0.0, 0.0))
            samples_a.append((0.0, 0.0))
            continue
        if i == 0:
            o = ev1(th)
            n2 = ev2(360.0 * DEG)
            # mean of (s''1_start, 0) and (0, s''2_end)
            samples_v.append((0.0, 0.0))
            samples_a.append((o[2] / 2.0, n2[2] / 2.0))
            continue
        if i == 4:
            e1 = ev1(th)
            a2 = ev2(th)
            # mean of (s''1_end, 0) and (0, -s''2_start)
            samples_v.append((0.0, 0.0))
            samples_a.append((e1[2] / 2.0, -a2[2] / 2.0))
            continue
        ev = ev1(th) if i <= 3 else ev2(th)
        sp, spp = ev[1], ev[2]
        samples_v.append((T[0] * sp, T[1] * sp))
        if i in (6, 10):
            # mean of line-side and arc-side one-sided accelerations
            ax = C_JUNCTION[0] * sp * sp / 2.0 + T[0] * spp
            ay = C_JUNCTION[1] * sp * sp / 2.0 + T[1] * spp
            samples_a.append((ax, ay))
            continue
        C = curv(s)
        samples_a.append((C[0] * sp * sp + T[0] * spp,
                          C[1] * sp * sp + T[1] * spp))

    # between-sample peaks on a fine grid over the moving spans
    peak_a = 0.0
    peak_v = 0.0
    sum_slope = 0.0
    cnt = 0
    max_slope = 0.0
    step = 0.02 * DEG
    th = 0.0
    while th <= 2.0 * PI + 1e-12:
        th += step
        if delta_deg == 0.0:
            ev = ev1(min(th, 120.0 * DEG)) if th <= 120.0 * DEG + 1e-12 else ev2(th)
        else:
            in_dwell = (th <= delta_deg * DEG
                        or (120.0 - delta_deg) * DEG <= th <= (120.0 + delta_deg) * DEG
                        or th >= (360.0 - delta_deg) * DEG)
            if in_dwell:
                continue
            ev = ev1(th) if th < 120.0 * DEG else ev2(th)
        s, sp, spp = ev
        if s < -1e-9 or s > L + 1e-9 or sp <= 1e-9:
            continue
        T = tangent(s)
        C = curv(s)
        ax = C[0] * sp * sp + T[0] * spp
        ay = C[1] * sp * sp + T[1] * spp
        peak_a = max(peak_a, math.hypot(ax, ay))
        peak_v = max(peak_v, math.hypot(T[0] * sp, T[1] * sp))
        sum_slope += sp
        cnt += 1
        max_slope = max(max_slope, sp)
    return {
        "delta_deg": delta_deg,
        "samples_v": samples_v,
        "samples_a": samples_a,
        "max_sample_a": max(math.hypot(*a) for a in samples_a),
        "argmax_sample": max(range(12), key=lambda i: math.hypot(*samples_a[i])),
        "max_sample_v": max(math.hypot(*v) for v in samples_v),
        "between_peak_a": peak_a,
        "peak_v": peak_v,
        "speed_swing_vs_mean": (max_slope / (sum_slope / cnt)) if cnt else 0.0,
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_task = os.path.join(here, "..", "sixbar-gap-transfer-02",
                               "gap_transfer_nostops.motion.json")
    default_out = os.path.join("runs", "sixbar-gap-transfer-03",
                              "softened-timing-report.json")
    ap = argparse.ArgumentParser(description="sixbar-gap-transfer-03 softened-timing recompute")
    ap.add_argument("--task", default=default_task)
    ap.add_argument("--output", default=default_out)
    args = ap.parse_args()

    with open(args.task) as f:
        task = json.load(f)
    theta = task["theta_rad"]
    q = task["q"]
    v_json = task["v"]
    a_json = task["a"]

    # ---- validation 1: theta grid and sample positions ----
    pos_err = 0.0
    for i in range(12):
        if abs(theta[i] - i * 30.0 * DEG) > 1e-12:
            raise SystemExit("VALIDATION FAILED: theta grid is not the 30-degree grid")
        px = q[i][0] * DIAG + CENTROID[0]
        py = q[i][1] * DIAG + CENTROID[1]
        mx, my = point(S_SAMPLES[i])
        pos_err = max(pos_err, abs(px - mx), abs(py - my))
    if pos_err > 1e-9:
        raise SystemExit("VALIDATION FAILED: sample positions off the path model by %g mm" % pos_err)

    # ---- validation 2: baseline timing reproduces the emitted v/a ----
    base = variant(0.0)
    v_err = 0.0
    a_err = 0.0
    for i in range(12):
        v_err = max(v_err,
                    abs(base["samples_v"][i][0] / DIAG - v_json[i][0]),
                    abs(base["samples_v"][i][1] / DIAG - v_json[i][1]))
        a_err = max(a_err,
                    abs(base["samples_a"][i][0] / DIAG - a_json[i][0]),
                    abs(base["samples_a"][i][1] / DIAG - a_json[i][1]))
    if v_err > 1e-9 or a_err > 1e-9:
        raise SystemExit("VALIDATION FAILED: baseline timing v residual %g, a residual %g"
                         % (v_err, a_err))

    # ---- dwell variants ----
    deltas = [0.0, 5.0, 10.0, 15.0]
    variants = [variant(d) for d in deltas]

    # ---- mean-value floors (properties of the path on the fixed grid) ----
    window_mean_speeds = []
    for i in range(12):
        ds = (S_SAMPLES[(i + 1) % 12] - S_SAMPLES[i]) % L
        window_mean_speeds.append(ds / (30.0 * DEG))
    junction_window_ds = S_SAMPLES[6] - S_SAMPLES[5]
    junction_floor_mm = (1.0 / R_CORNER) * (junction_window_ds / (30.0 * DEG)) ** 2 / 2.0

    # ---- report ----
    rep = {
        "job": "sixbar-gap-transfer-03",
        "task": os.path.relpath(args.task) if os.path.isabs(args.task) else args.task,
        "validation": {
            "positions_max_residual_mm": pos_err,
            "baseline_v_max_residual_norm": v_err,
            "baseline_a_max_residual_norm": a_err,
            "gates": {"positions": 1e-9, "v": 1e-9, "a": 1e-9},
        },
        "diagonal_mm": DIAG,
        "loop_length_mm": L,
        "variants": [
            {
                "delta_deg": V["delta_deg"],
                "sample_a_mm": [round(math.hypot(*a), 3) for a in V["samples_a"]],
                "sample_v_mm": [round(math.hypot(*v), 3) for v in V["samples_v"]],
                "max_sample_a_mm": V["max_sample_a"],
                "max_sample_a_norm": V["max_sample_a"] / DIAG,
                "argmax_sample": V["argmax_sample"],
                "max_sample_v_mm": V["max_sample_v"],
                "between_peak_a_mm": V["between_peak_a"],
                "between_peak_a_norm": V["between_peak_a"] / DIAG,
                "peak_v_mm": V["peak_v"],
                "speed_swing_vs_mean": V["speed_swing_vs_mean"],
            }
            for V in variants
        ],
        "floors": {
            "window_mean_speeds_mm_per_rad": [round(x, 3) for x in window_mean_speeds],
            "junction_window_mean_speed_mm": junction_window_ds / (30.0 * DEG),
            "junction_demand_at_window_mean_mm": junction_floor_mm,
            "junction_demand_at_window_mean_norm": junction_floor_mm / DIAG,
        },
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(rep, f, indent=2)

    print("sixbar-gap-transfer-03: softened-timing recompute")
    print("task: %s" % args.task)
    print("validation: positions %.3g mm, baseline v %.3g, baseline a %.3g (gates 1e-9)"
          % (pos_err, v_err, a_err))
    print("diagonal %.4f mm, loop %.4f mm" % (DIAG, L))
    print()
    print("delta  max sample |a| mm (norm) @sample   between-peak |a| (norm)  "
          "max sample speed (norm)  peak speed  swing")
    for V in variants:
        print("%5.1f  %10.2f (%.4f) @%-2d      %10.2f (%.4f)      "
              "%10.2f (%.4f)     %8.2f   %.2f"
              % (V["delta_deg"],
                 V["max_sample_a"], V["max_sample_a"] / DIAG, V["argmax_sample"],
                 V["between_peak_a"], V["between_peak_a"] / DIAG,
                 V["max_sample_v"], V["max_sample_v"] / DIAG,
                 V["peak_v"], V["speed_swing_vs_mean"]))
    print()
    print("per-sample |a| (mm), phases 0-11:")
    for V in variants:
        print("delta %4.1f: %s" % (V["delta_deg"],
              " ".join("%7.1f" % math.hypot(*a) for a in V["samples_a"])))
    print()
    print("floors: junction window mean speed %.2f mm/rad, "
          "junction demand at that speed %.2f mm (%.4f normalized)"
          % (junction_window_ds / (30.0 * DEG), junction_floor_mm, junction_floor_mm / DIAG))
    print("report written to %s" % args.output)


if __name__ == "__main__":
    main()
