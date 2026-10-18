#!/usr/bin/env python3
# Job sixbar-gap-transfer-04: the free-phase variant -- design script.
#
# The -03 record established that the binding prescription of the
# gap-transfer task family is the phase-locked 30-degree grid, not the
# stop timing (best dwell cut the max sample acceleration by only
# 28.4% while between-sample peaks grew).  Per that record's R4 and
# the group ranking, this job frees the SAMPLE PLACEMENT: the crank
# grid, the path and the three carry poses stay exactly as in -02;
# where the tool sits along the path at each of the nine non-pose
# samples is chosen by this script to minimize the scaled derivative
# demand the solver is gated on.
#
# Declared split (frozen before the run, per the group's requirement
# (a) for this variant):
# - FIXED: the 12x30-degree theta grid; branches [-1, +1]; the -02
#   racetrack path (carry 260 mm, 15 mm corner arcs, return 40 mm
#   below the belt line); the three carry poses T1/T2/T3 at phases
#   0/2/4 with their tolerances; zero speed at the two process stops
#   (phases 0 and 4); level orientation at every sample; the timing
#   structure (two clamped cubic runs, the carry phases 0-4 and the
#   bottom loop phases 4-12 closing at phase 0, zero end slopes, the
#   vector-mean acceleration conventions at the stops and at any
#   sample sitting exactly on a line/arc junction).
# - MOVING: the arc-length placements s of the nine non-pose samples
#   (phases 1, 3, 5-11), anywhere strictly between their pose
#   neighbours on the path, monotone along the loop; with them the
#   prescribed v and a at every non-stop sample and the one-sided
#   accelerations that form the stop prescriptions.
# - MOVABLE BUT NOT EXERCISED: stop durations (a dwell needs a
#   duplicated stop sample, which would double the T1->T2 window
#   mean; -03 already refuted dwell relief at fixed phases), and any
#   change to the path itself.  Declared, not silently assumed.
#
# Method.  The path model and the spline machinery are transcribed
# from the -03 script (softened_timing_recompute.py), which itself
# carries the -02 audit trail.  The design search is a deterministic
# multi-start coordinate descent (fixed start list, fixed scan order,
# fixed grids, no randomness) over the nine placements, minimizing
# the max over the twelve samples of the scaled derivative demand
# max(|v|/0.02, |a|/0.05) in the task's own normalization (the
# solver's strict gates; the normalization is recomputed per
# candidate because the freed placements move the twelve-sample
# centroid and bounding box).  Four declared starts (the -02
# baseline placements, and three single-cubic-timing variants) are
# each descended with single-coordinate moves plus moves along the
# loop's mirror-symmetry pairs (the carry pair 1/3, the descent and
# ascent pair 5/11, the post-corner pair 6/10, the return pair 7/9),
# because the -02 placements sit on a minimax ridge that
# single-coordinate moves cannot slide along.  Two honesty caps keep
# the freed timing from becoming a monstrosity: the between-sample
# fine-grid acceleration peak and peak speed must stay within 1.10x
# the -02 baseline values (computed by rebuilding the baseline here,
# not read from any record), and the timing law must stay monotone
# in progress along the loop; violations enter the descent surface as
# a penalty, and starts that never reach feasibility are recorded,
# not hidden.  The winning placements are rounded to 0.1 mm (free
# placements keep at least 0.5 mm clear of the line/arc junctions,
# where the prescription convention is discontinuous) before the
# task is emitted, so the committed artifact does not depend on
# last-ulp search noise.
#
# Task-side arithmetic only: no solver, no engine, no package code;
# the -02 record is read for validation and is never rewritten.
#
# Output: a printed report, a regenerated task JSON (default
# runs/sixbar-gap-transfer-04/regenerated-task.json) and a design
# report JSON (default
# runs/sixbar-gap-transfer-04/free-phase-design-report.json).  If the
# committed task file gap_transfer_freephase.motion.json sits next
# to this script, it is compared against the regeneration (1e-9
# gates plus a byte-identity verdict); the committed file stays the
# frozen artifact.

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
C_JUNCTION = (0.0, 1.0 / R_CORNER)  # arc-side curvature vector at both junctions

# the -02 recorded placements (the baseline of this job)
S_BASELINE = [0.0, 65.0, 130.0, 195.0, 260.0, 305.0,
              B[3], B[3] + 57.5, B[3] + 115.0, B[3] + 172.5,
              B[4], B[5] + 30.0]

# the fixed pose placements (T1/T2/T3 at phases 0/2/4)
S_FIXED = {0: 0.0, 2: 130.0, 4: 260.0}
FREE_IDX = [1, 3, 5, 6, 7, 8, 9, 10, 11]
S_END = L  # run2 closes the loop at s = L == 0 (the same physical point as T1)

# the solver's strict derivative gates, normalized units
GATE_V = 0.02
GATE_A = 0.05


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


def region(s):
    if s <= B[1]:
        return "carry line"
    if s <= B[2]:
        return "descent line"
    if s < B[3]:
        return "right corner arc"
    if s <= B[4]:
        return "return line"
    if s < B[5]:
        return "left corner arc"
    return "ascent line"


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


T_RUN1 = [i * 30.0 * DEG for i in range(5)]        # 0..120 deg
T_RUN2 = [i * 30.0 * DEG for i in range(4, 13)]    # 120..360 deg


# ---------- prescription for a placement vector ----------
def prescription(S):
    """Per-sample prescribed v and a (mm units) for a placement vector S."""
    ev1 = clamped_cubic(T_RUN1, [S[0], S[1], S[2], S[3], S[4]])
    ev2 = clamped_cubic(T_RUN2, [S[4], S[5], S[6], S[7], S[8],
                                S[9], S[10], S[11], S_END])
    samples_v = []
    samples_a = []
    for i in range(12):
        th = i * 30.0 * DEG
        s = S[i]
        T = tangent(s)
        if i == 0:
            o = ev1(0.0)
            n2 = ev2(360.0 * DEG)
            # mean of (s''1_start along carry, 0) and (0, s''2_end along ascent)
            samples_v.append((0.0, 0.0))
            samples_a.append((o[2] / 2.0, n2[2] / 2.0))
            continue
        if i == 4:
            e1 = ev1(th)
            a2 = ev2(th)
            # mean of (s''1_end along carry, 0) and (0, -s''2_start along descent)
            samples_v.append((0.0, 0.0))
            samples_a.append((e1[2] / 2.0, -a2[2] / 2.0))
            continue
        ev = ev1 if i <= 3 else ev2
        o = ev(th)
        sp, spp = o[1], o[2]
        samples_v.append((T[0] * sp, T[1] * sp))
        if abs(s - B[3]) < 1e-9 or abs(s - B[4]) < 1e-9:
            # sample exactly on a line/arc junction: mean of the
            # one-sided line/arc accelerations (the -02 convention)
            ax = C_JUNCTION[0] * sp * sp / 2.0 + T[0] * spp
            ay = C_JUNCTION[1] * sp * sp / 2.0 + T[1] * spp
            samples_a.append((ax, ay))
            continue
        C = curv(s)
        samples_a.append((C[0] * sp * sp + T[0] * spp,
                          C[1] * sp * sp + T[1] * spp))
    return samples_v, samples_a, ev1, ev2


def normalize(S, samples_v, samples_a):
    """The task's own normalization: centroid and bbox diagonal of the
    twelve sample positions (the validator's actual rule)."""
    pts = [point(S[i]) for i in range(12)]
    cx = sum(p[0] for p in pts) / 12.0
    cy = sum(p[1] for p in pts) / 12.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    q = [[(pts[i][0] - cx) / diag, (pts[i][1] - cy) / diag, 0.0]
         for i in range(12)]
    v = [[samples_v[i][0] / diag, samples_v[i][1] / diag, 0.0]
         for i in range(12)]
    a = [[samples_a[i][0] / diag, samples_a[i][1] / diag, 0.0]
         for i in range(12)]
    return (cx, cy), diag, q, v, a


def objective(S):
    """Max over the twelve samples of the scaled derivative demand."""
    sv, sa, _, _ = prescription(S)
    pts = [point(S[i]) for i in range(12)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    j = 0.0
    for i in range(12):
        jv = math.hypot(sv[i][0], sv[i][1]) / diag / GATE_V
        ja = math.hypot(sa[i][0], sa[i][1]) / diag / GATE_A
        j = max(j, jv, ja)
    return j


def scan_peaks(S, ev1, ev2, step_deg):
    """Between-sample fine-grid peaks and monotonicity check over the
    two moving spans.  Returns (ok, peak_a_mm, peak_v_mm, swing)."""
    ok = True
    peak_a = 0.0
    peak_v = 0.0
    sum_slope = 0.0
    cnt = 0
    max_slope = 0.0
    step = step_deg * DEG
    th = 0.0
    while th <= 360.0 * DEG + 1e-12:
        if th < 120.0 * DEG:
            ev, lo, hi = ev1, -0.5, 260.5
        else:
            ev, lo, hi = ev2, 259.5, L + 0.5
        s, sp, spp = ev(th)
        if s < lo or s > hi:
            ok = False  # off the loop
        if sp < -1e-9:
            ok = False  # non-monotone timing
        if 0.0 <= s <= L and sp > 1e-9:
            T = tangent(s)
            C = curv(s)
            ax = C[0] * sp * sp + T[0] * spp
            ay = C[1] * sp * sp + T[1] * spp
            peak_a = max(peak_a, math.hypot(ax, ay))
            peak_v = max(peak_v, math.hypot(T[0] * sp, T[1] * sp))
            sum_slope += sp
            cnt += 1
            max_slope = max(max_slope, sp)
        th += step
    swing = (max_slope / (sum_slope / cnt)) if cnt else 0.0
    return ok, peak_a, peak_v, swing



MIN_GAP = 2.0
N_GRID = 65
EPS_ACCEPT = 1e-9
JUNCTION_BAND = 0.5     # free placements stay at least this far from the
                       # line/arc junctions, where the prescribed
                       # acceleration convention is discontinuous
SEARCH_STEP_DEG = 0.25
CAP_SLACK = 0.995       # search-time caps carry a small margin so the
                       # 0.02-degree final grid cannot overshoot
PEN_WEIGHT = 500.0


def bbox_diag(S):
    pts = [point(S[i]) for i in range(12)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def in_junction_band(v):
    return abs(v - B[3]) < JUNCTION_BAND or abs(v - B[4]) < JUNCTION_BAND


def placement_ok(S):
    """Structural constraints: fixed poses, strict ordering, min gaps,
    junction clearance for the freed samples."""
    prev = 0.0
    for i in range(12):
        if i in S_FIXED:
            if abs(S[i] - S_FIXED[i]) > 1e-12:
                return False
            prev = S[i]
            continue
        if S[i] <= prev + MIN_GAP:
            return False
        if i == 11 and S[i] >= S_END - MIN_GAP:
            return False
        if in_junction_band(S[i]):
            return False
        prev = S[i]
    return True


def nudge(S):
    """Deterministic repair into the structural constraints: clamp each
    freed placement between its neighbours, keeping the fixed poses."""
    out = list(S)
    for i in S_FIXED:
        out[i] = S_FIXED[i]
    prev = out[0]
    for i in range(1, 12):
        if i in S_FIXED:
            prev = out[i]
            continue
        lo = prev + MIN_GAP
        hi = out[i + 1] - MIN_GAP if i < 11 else S_END - MIN_GAP
        out[i] = min(max(out[i], lo), hi)
        prev = out[i]
    for i in FREE_IDX:
        v = out[i]
        if abs(v - B[3]) < JUNCTION_BAND:
            out[i] = B[3] + JUNCTION_BAND  # the return-line side
        elif abs(v - B[4]) < JUNCTION_BAND:
            out[i] = B[4] - JUNCTION_BAND  # the return-line side
    # a reverse pass restores strict ordering after the band pushes
    nxt = S_END - MIN_GAP
    for i in range(11, 0, -1):
        if i in S_FIXED:
            nxt = out[i]
            continue
        out[i] = min(out[i], nxt - MIN_GAP)
        nxt = out[i]
    return out


def penalized(S, cap_a_norm, cap_v_norm):
    """Objective plus honesty penalty; the descent surface."""
    sv, sa, ev1, ev2 = prescription(S)
    diag = bbox_diag(S)
    j = 0.0
    for i in range(12):
        j = max(j,
                math.hypot(sv[i][0], sv[i][1]) / diag / GATE_V,
                math.hypot(sa[i][0], sa[i][1]) / diag / GATE_A)
    ok, peak_a, peak_v, _ = scan_peaks(S, ev1, ev2, SEARCH_STEP_DEG)
    pen = 0.0
    if not ok:
        pen += 1e6
    pen += PEN_WEIGHT * max(0.0, peak_a / diag - cap_a_norm * CAP_SLACK)
    pen += PEN_WEIGHT * max(0.0, peak_v / diag - cap_v_norm * CAP_SLACK)
    return j + pen, j, peak_a / diag, peak_v / diag, ok


def coord_bounds(i, S):
    if i == 1:
        return S[0] + MIN_GAP, S[2] - MIN_GAP
    if i == 3:
        return S[2] + MIN_GAP, S[4] - MIN_GAP
    if i == 11:
        return S[10] + MIN_GAP, S_END - MIN_GAP
    return S[i - 1] + MIN_GAP, S[i + 1] - MIN_GAP


# the loop's mirror symmetries: the carry about its midpoint, the
# bottom loop about the phase-8 line (path-symmetric, so the
# objective is invariant under these maps)
MIRROR_RUN2 = 260.0 + S_END          # m(s) = 947.1239... - s
PAIR_MOVES = [
    (1, 3, lambda v: 260.0 - v),                 # carry pair
    (5, 11, lambda v: MIRROR_RUN2 - v),          # descent / ascent pair
    (6, 10, lambda v: MIRROR_RUN2 - v),          # post-corner pair
    (7, 9, lambda v: MIRROR_RUN2 - v),           # return pair
]


def cubic_knots_run1():
    T = 120.0 * DEG

    def s(t):
        x = t / T
        return 260.0 * (3.0 * x * x - 2.0 * x ** 3)

    return s(30.0 * DEG), s(90.0 * DEG)


def cubic_knots_run2():
    T = 240.0 * DEG

    def s(t):
        x = t / T
        return 260.0 + (S_END - 260.0) * (3.0 * x * x - 2.0 * x ** 3)

    return [s((i - 4) * 30.0 * DEG) for i in range(5, 12)]


def design_starts():
    c1a, c1b = cubic_knots_run1()
    c2 = cubic_knots_run2()
    starts = []
    starts.append(("baseline", list(S_BASELINE)))
    s = list(S_BASELINE)
    s[1], s[3] = c1a, c1b
    starts.append(("cubic carry", s))
    s = list(S_BASELINE)
    s[1], s[3] = c1a, c1b
    for k, i in enumerate(range(5, 12)):
        s[i] = c2[k]
    starts.append(("cubic carry and loop", s))
    s = list(S_BASELINE)
    for k, i in enumerate(range(5, 12)):
        s[i] = c2[k]
    starts.append(("cubic loop", s))
    return [(name, nudge(pl)) for name, pl in starts]


def design_search(cap_a_norm, cap_v_norm):
    """Deterministic multi-start coordinate descent on the penalized
    objective: fixed order, fixed grids, no randomness."""
    stats = {"objective_evals": 0, "peak_evals": 0, "accepted_moves": 0,
             "starts": []}
    best = None  # (J_rounded, S_rounded, start_name)
    for name, S0 in design_starts():
        S = list(S0)
        jp_cur, j_cur, pa, pv, ok = penalized(S, cap_a_norm, cap_v_norm)
        jp0 = jp_cur
        stats["objective_evals"] += 1
        stats["peak_evals"] += 1
        moves_here = 0
        rounds = 0

        def try_scan(spread):
            nonlocal S, jp_cur, j_cur, moves_here
            moved = False

            def consider(cand):
                nonlocal S, jp_cur, j_cur, moves_here
                stats["objective_evals"] += 1
                jc = objective(cand)
                if jc >= jp_cur:
                    return False  # cannot beat the penalized incumbent
                stats["peak_evals"] += 1
                jpc, _, _, _, _ = penalized(cand, cap_a_norm, cap_v_norm)
                if jpc < jp_cur - EPS_ACCEPT:
                    S = cand
                    jp_cur = jpc
                    j_cur = jc
                    moves_here += 1
                    stats["accepted_moves"] += 1
                    return True
                return False

            for i in FREE_IDX:
                lo, hi = coord_bounds(i, S)
                if spread is not None:
                    lo = max(lo, S[i] - spread)
                    hi = min(hi, S[i] + spread)
                    if hi - lo < 1e-9:
                        continue
                for k in range(N_GRID):
                    val = lo + (hi - lo) * k / (N_GRID - 1)
                    if in_junction_band(val):
                        continue
                    cand = list(S)
                    cand[i] = val
                    if consider(cand):
                        moved = True
            # mirror-pair moves slide along the symmetric ridges that
            # single-coordinate moves cannot cross
            for (i, j, mirror) in PAIR_MOVES:
                lo, hi = coord_bounds(i, S)
                if spread is not None:
                    lo = max(lo, S[i] - spread)
                    hi = min(hi, S[i] + spread)
                    if hi - lo < 1e-9:
                        continue
                for k in range(N_GRID):
                    val = lo + (hi - lo) * k / (N_GRID - 1)
                    if in_junction_band(val) or in_junction_band(mirror(val)):
                        continue
                    cand = list(S)
                    cand[i] = val
                    cand[j] = mirror(val)
                    if not placement_ok(cand):
                        continue
                    if consider(cand):
                        moved = True
            return moved

        while rounds < 80 and try_scan(None):
            rounds += 1
        spread = None
        r2 = 0
        first = True
        while r2 < 16:
            if first:
                # start the refinement from the coarse grid step
                lo0, hi0 = coord_bounds(1, S)
                spread = (hi0 - lo0) / (N_GRID - 1) * 2.0
                first = False
            if not try_scan(spread):
                break
            spread *= 0.5
            r2 += 1
        stats["starts"].append({
            "name": name,
            "start_placements_mm": [round(x, 6) for x in S0],
            "start_penalized": jp0,
            "end_penalized": jp_cur,
            "end_objective": j_cur,
            "accepted_moves_here": moves_here,
            "rounds": rounds,
            "refine_rounds": r2,
        })
        # round to the 0.1 mm grid, keep out of the junction bands
        S_round = []
        for i in range(12):
            if i in S_FIXED:
                S_round.append(S_FIXED[i])
                continue
            v = round(S[i] * 10.0) / 10.0
            if abs(v - B[3]) < JUNCTION_BAND:
                v = math.ceil((B[3] + JUNCTION_BAND) * 10.0) / 10.0
            elif abs(v - B[4]) < JUNCTION_BAND:
                v = math.floor((B[4] - JUNCTION_BAND) * 10.0) / 10.0
            S_round.append(v)
        for _ in range(3):
            if placement_ok(S_round):
                break
            S_round = nudge(S_round)
        sv, sa, ev1, ev2 = prescription(S_round)
        ok_f, peak_a, peak_v, _ = scan_peaks(S_round, ev1, ev2, 0.02)
        diag_r = bbox_diag(S_round)
        cap_ok = (peak_a / diag_r <= cap_a_norm and
                  peak_v / diag_r <= cap_v_norm)
        if not (placement_ok(S_round) and ok_f and cap_ok):
            stats["starts"][-1]["rounded"] = "infeasible after rounding"
            continue
        j_round = objective(S_round)
        stats["starts"][-1]["rounded"] = "feasible"
        stats["starts"][-1]["rounded_objective"] = j_round
        if best is None or j_round < best[0] - 1e-12:
            best = (j_round, list(S_round), name)
    if best is None:
        raise SystemExit("SEARCH FAILED: no start reached a feasible "
                         "rounded design")
    return best[1], best[0], best[2], stats


# ---------- validation against the -02 task (fail-closed) ----------
def validate_baseline(task):
    theta = task["theta_rad"]
    q = task["q"]
    v_json = task["v"]
    a_json = task["a"]
    pos_err = 0.0
    for i in range(12):
        if abs(theta[i] - i * 30.0 * DEG) > 1e-12:
            raise SystemExit("VALIDATION FAILED: theta grid is not the 30-degree grid")
        px = q[i][0] * DIAG + CENTROID[0]
        py = q[i][1] * DIAG + CENTROID[1]
        mx, my = point(S_BASELINE[i])
        pos_err = max(pos_err, abs(px - mx), abs(py - my))
    if pos_err > 1e-9:
        raise SystemExit("VALIDATION FAILED: sample positions off the path model by %g mm" % pos_err)
    sv, sa, _, _ = prescription(S_BASELINE)
    v_err = 0.0
    a_err = 0.0
    for i in range(12):
        v_err = max(v_err,
                    abs(sv[i][0] / DIAG - v_json[i][0]),
                    abs(sv[i][1] / DIAG - v_json[i][1]))
        a_err = max(a_err,
                    abs(sa[i][0] / DIAG - a_json[i][0]),
                    abs(sa[i][1] / DIAG - a_json[i][1]))
    if v_err > 1e-9 or a_err > 1e-9:
        raise SystemExit("VALIDATION FAILED: baseline timing v residual %g, a residual %g"
                         % (v_err, a_err))
    return pos_err, v_err, a_err


# ---------- independent finite-difference cross-check ----------
def fd_crosscheck(S):
    """Central differences of the composed trajectory (h = 1e-3 rad),
    the -02 audit-trail check.  Straddling a stop, a corner or a
    curvature jump returns a one-sided mean by construction, so the
    stop/junction/arc samples carry larger residuals by design."""
    h = 1e-3
    sv, sa, _, _ = prescription(S)
    ev1 = clamped_cubic(T_RUN1, [S[0], S[1], S[2], S[3], S[4]])
    ev2 = clamped_cubic(T_RUN2, [S[4], S[5], S[6], S[7], S[8],
                               S[9], S[10], S[11], S_END])
    dv_max = 0.0
    da_max = 0.0
    for i in range(12):
        th = i * 30.0 * DEG

        def pos_at(t):
            t = t % (360.0 * DEG)
            ev = ev1 if t <= 120.0 * DEG else ev2
            return point(ev(t)[0])

        pm, p0, pp = pos_at(th - h), pos_at(th), pos_at(th + h)
        vm = ((p0[0] - pm[0]) / h, (p0[1] - pm[1]) / h)
        vp = ((pp[0] - p0[0]) / h, (pp[1] - p0[1]) / h)
        am = ((vp[0] - vm[0]) / h, (vp[1] - vm[1]) / h)
        dv_max = max(dv_max,
                     abs((vm[0] + vp[0]) / 2.0 - sv[i][0]),
                     abs((vm[1] + vp[1]) / 2.0 - sv[i][1]))
        da_max = max(da_max,
                     abs(am[0] - sa[i][0]), abs(am[1] - sa[i][1]))
    return dv_max, da_max


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_baseline = os.path.join(here, "..", "sixbar-gap-transfer-02",
                                   "gap_transfer_nostops.motion.json")
    default_committed = os.path.join(here, "gap_transfer_freephase.motion.json")
    default_emit = os.path.join("runs", "sixbar-gap-transfer-04",
                                "regenerated-task.json")
    default_out = os.path.join("runs", "sixbar-gap-transfer-04",
                               "free-phase-design-report.json")
    ap = argparse.ArgumentParser(description="sixbar-gap-transfer-04 free-phase design")
    ap.add_argument("--baseline", default=default_baseline)
    ap.add_argument("--committed", default=default_committed)
    ap.add_argument("--emit", default=default_emit)
    ap.add_argument("--output", default=default_out)
    args = ap.parse_args()

    with open(args.baseline) as f:
        base_task = json.load(f)

    # ---- stage 1: rebuild and validate the -02 baseline ----
    pos_err, v_err, a_err = validate_baseline(base_task)
    sv0, sa0, ev1_0, ev2_0 = prescription(S_BASELINE)
    ok0, peak_a0, peak_v0, swing0 = scan_peaks(S_BASELINE, ev1_0, ev2_0, 0.02)
    base_j = objective(S_BASELINE)
    cap_a_norm = 1.10 * peak_a0 / DIAG
    cap_v_norm = 1.10 * peak_v0 / DIAG

    # ---- stage 2: the design search ----
    S_round, j_round, start_name, stats = design_search(cap_a_norm, cap_v_norm)
    sv, sa, ev1, ev2 = prescription(S_round)
    ok_f, peak_a, peak_v, swing = scan_peaks(S_round, ev1, ev2, 0.02)
    diag = bbox_diag(S_round)
    if not ok_f:
        raise SystemExit("DESIGN FAILED: the rounded design's timing law is "
                         "not monotone along the loop")
    if peak_a / diag > cap_a_norm or peak_v / diag > cap_v_norm:
        raise SystemExit("DESIGN FAILED: the rounded design exceeds the "
                         "between-sample honesty caps")
    (cx, cy), diag, q_rows, v_rows, a_rows = normalize(S_round, sv, sa)

    # validator arithmetic self-check
    mean_x = sum(r[0] for r in q_rows) / 12.0
    mean_y = sum(r[1] for r in q_rows) / 12.0
    qxs = [r[0] for r in q_rows]
    qys = [r[1] for r in q_rows]
    diag_norm = math.hypot(max(qxs) - min(qxs), max(qys) - min(qys))
    if abs(mean_x) > 1e-12 or abs(mean_y) > 1e-12 or abs(diag_norm - 1.0) > 1e-12:
        raise SystemExit("EMISSION FAILED: normalized samples off the "
                         "validator rule (centroid %g,%g diag %g)"
                         % (mean_x, mean_y, diag_norm))

    # ---- independent finite-difference cross-check ----
    dv_max, da_max = fd_crosscheck(S_round)

    # ---- stage 3: emit and compare ----
    task = {
        "theta_rad": [i * PI / 6.0 for i in range(12)],
        "branches": [-1, 1],
        "q": q_rows,
        "v": v_rows,
        "a": a_rows,
    }
    os.makedirs(os.path.dirname(args.emit) or ".", exist_ok=True)
    with open(args.emit, "w") as f:
        json.dump(task, f, indent=2)
        f.write("\n")

    committed_verdict = "not present"
    byte_verdict = "n/a"
    if os.path.exists(args.committed):
        with open(args.committed) as f:
            committed = json.load(f)
        worst = 0.0
        for key in ("q", "v", "a"):
            for i in range(12):
                for k in range(3):
                    worst = max(worst, abs(committed[key][i][k] - task[key][i][k]))
        theta_ok = all(abs(committed["theta_rad"][i] - task["theta_rad"][i]) < 1e-15
                       for i in range(12))
        committed_verdict = ("AGREE (max residual %.3g over q/v/a; theta %s)"
                             % (worst, "matches" if theta_ok else "DIFFERS"))
        if worst <= 1e-9 and theta_ok:
            with open(args.committed, "rb") as f:
                cbytes = f.read()
            with open(args.emit, "rb") as f:
                rbytes = f.read()
            byte_verdict = ("byte-identical" if cbytes == rbytes
                            else "differs in bytes (values agree to 1e-9)")
        else:
            byte_verdict = "DIFFERS (gate 1e-9 exceeded)"

    # ---- the printed report ----
    j_round = objective(S_round)
    print("sixbar-gap-transfer-04: free-phase design")
    print("baseline task: %s" % args.baseline)
    print("validation: positions %.3g mm, baseline v %.3g, baseline a %.3g (gates 1e-9)"
          % (pos_err, v_err, a_err))
    print("baseline: max scaled demand %.2fx gates, between-sample peak |a| %.4f norm, "
          "peak speed %.4f norm, swing %.2f"
          % (base_j, peak_a0 / DIAG, peak_v0 / DIAG, swing0))
    print("honesty caps: between-sample peak |a| <= %.4f norm, peak speed <= %.4f norm"
          % (cap_a_norm, cap_v_norm))
    print()
    print("design search: %d objective evals, %d peak evals, %d accepted moves; "
          "winning start: %s"
          % (stats["objective_evals"], stats["peak_evals"],
             stats["accepted_moves"], start_name))
    print("rounded placements (mm, 0.1 mm grid): %s"
          % " ".join("%.1f" % x for x in S_round))
    print()
    print("design: max scaled demand %.2fx gates (%.1f%% of baseline %.2fx)"
          % (j_round, 100.0 * j_round / base_j, base_j))
    print("design: between-sample peak |a| %.4f norm (cap %.4f), peak speed %.4f norm "
          "(cap %.4f), swing %.2f"
          % (peak_a / diag, cap_a_norm, peak_v / diag, cap_v_norm, swing))
    print("normalization: centroid (%.2f, %.2f) mm, bbox diagonal %.4f mm "
          "(baseline %.4f mm)"
          % (cx, cy, diag, DIAG))
    print("finite-difference cross-check: v %.3g mm/rad, a %.3g mm/rad^2 "
          "(stops/junctions/arc samples carry one-sided means by construction)"
          % (dv_max, da_max))
    print("committed task comparison: %s; %s" % (committed_verdict, byte_verdict))
    print()
    print("phase  theta  tool point (mm)     arc pos  region            "
          "|v| mm  |a| mm/rad2  |v| norm  |a| norm  scaled v  scaled a")
    for i in range(12):
        p = point(S_round[i])
        vv = math.hypot(sv[i][0], sv[i][1])
        aa = math.hypot(sa[i][0], sa[i][1])
        note = region(S_round[i])
        if i in S_FIXED:
            note += " [FIXED pose]"
        else:
            note += " [freed]"
        if i in (0, 4):
            note += " stop"
        if abs(S_round[i] - B[3]) < 1e-9 or abs(S_round[i] - B[4]) < 1e-9:
            note += " junction"
        print("%5d  %4d  (%8.2f,%7.2f)  %7.1f  %-32s %7.2f  %10.2f  %8.4f  %9.4f  %8.2f  %8.2f"
              % (i, i * 30, p[0], p[1], S_round[i], note,
                 vv, aa, vv / diag, aa / diag, vv / diag / GATE_V, aa / diag / GATE_A))

    # ---- the report JSON ----
    rep = {
        "job": "sixbar-gap-transfer-04",
        "baseline_task": args.baseline,
        "validation": {
            "positions_max_residual_mm": pos_err,
            "baseline_v_max_residual_norm": v_err,
            "baseline_a_max_residual_norm": a_err,
            "gates": {"positions": 1e-9, "v": 1e-9, "a": 1e-9},
        },
        "baseline": {
            "max_scaled_demand": base_j,
            "between_peak_a_norm": peak_a0 / DIAG,
            "peak_v_norm": peak_v0 / DIAG,
            "swing": swing0,
        },
        "honesty_caps": {
            "between_peak_a_norm": cap_a_norm,
            "peak_v_norm": cap_v_norm,
            "rule": "1.10x the rebuilt -02 baseline values",
        },
        "search": {
            "method": "deterministic multi-start coordinate descent on the "
                      "penalized objective: fixed start list (baseline; "
                      "cubic carry; cubic carry and loop; cubic loop), "
                      "single-coordinate moves plus mirror-pair moves "
                      "(1/3, 5/11, 6/10, 7/9), fixed scan order, 65-point "
                      "grids, 2 mm min gaps, 0.5 mm junction clearance, "
                      "0.25 deg peak grid, 0.995 cap slack during search",
            "objective_evals": stats["objective_evals"],
            "peak_evals": stats["peak_evals"],
            "accepted_moves": stats["accepted_moves"],
            "winning_start": start_name,
            "starts": stats["starts"],
        },
        "design": {
            "placements_mm": S_round,
            "rounding": "0.1 mm grid",
            "max_scaled_demand": j_round,
            "max_scaled_demand_vs_baseline_pct": 100.0 * j_round / base_j,
            "between_peak_a_norm": peak_a / diag,
            "peak_v_norm": peak_v / diag,
            "swing": swing,
            "centroid_mm": [cx, cy],
            "bbox_diagonal_mm": diag,
            "fd_crosscheck_v_mm": dv_max,
            "fd_crosscheck_a_mm": da_max,
            "committed_comparison": committed_verdict,
            "byte_verdict": byte_verdict,
            "per_phase": [
                {
                    "phase": i,
                    "theta_deg": i * 30,
                    "point_mm": list(point(S_round[i])),
                    "arc_pos_mm": S_round[i],
                    "region": region(S_round[i]),
                    "fixed_pose": i in S_FIXED,
                    "stop": i in (0, 4),
                    "junction": abs(S_round[i] - B[3]) < 1e-9 or abs(S_round[i] - B[4]) < 1e-9,
                    "v_mm": list(sv[i]),
                    "a_mm": list(sa[i]),
                    "v_norm_magnitude": math.hypot(sv[i][0], sv[i][1]) / diag,
                    "a_norm_magnitude": math.hypot(sa[i][0], sa[i][1]) / diag,
                    "scaled_v": math.hypot(sv[i][0], sv[i][1]) / diag / GATE_V,
                    "scaled_a": math.hypot(sa[i][0], sa[i][1]) / diag / GATE_A,
                }
                for i in range(12)
            ],
        },
    }
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(rep, f, indent=2)
        f.write("\n")
    print()
    print("regenerated task written to %s" % args.emit)
    print("report written to %s" % args.output)


if __name__ == "__main__":
    main()
