#!/usr/bin/env python3
"""Stage 1 deterministic analysis script for job
dualcam-profile-tolerance-07.

The queued Q1/Q3/Q2 round for case study B, as converged by the
actor/critic debate and staged under the frozen rule: the
profile-tolerance -> path-error mapping for the RECORDED -06
Option B design (the dual-cam cross-slide with the general
pivoted lever, HELD at the 30 deg engineering gate with the
envelope exactly consumed), with the force-closure question
folded in as data-only rows and the A-floor question redeclared
as data. No search, no solver, no network: pure standard
library, deterministic. The merged -06 module is imported
read-only; its recorded design is regenerated, never modified.

What it does, in order:

  A. Fail-closed reproduction of the recorded -06 outcome: the
     frozen -02 task is validated through the -06 module's own
     reconstruction (1e-9 normalized units) and its SHA-256 is
     checked against the recorded byte-identity witness; the
     Option B pick is regenerated with the -06 pick rule (the
     design scan runs ONCE -- its oracle cross-check is the
     stronger control) and cross-checked against the recorded
     -06 oracle: A, P exact, Delta exact at the recorded print
     precision, the audit floats within 5e-3 relative.
  B. The exact error map on the 0.1 deg grid (3600 points per
     cam): the first-order normal profile error -> task-space
     path error map through the ACTUAL lever geometry, never the
     sketched scalar lambda_eff:
       S_x(th) = L^2 / (|Py| * A * cos q),
         L = hypot(u - Px, Py) the pin-arm length, u the slide
             position, A the short arm, P = (Px, Py) the pivot,
         cos q = |f . n|, the roller constraint direction f
             (perpendicular to the lever arm) against the
             pitch-curve normal n = i T / |T| with T = C' - i c
             the fixed-frame pitch tangent;
       S_y(th) = hypot(r, h') / r = 1 / cos(alpha_y),
         r = 195 + h the -05 carry-in pitch radius.
     A normal profile error delta moves the constrained roller
     delta / cos(pressure angle) along its motion direction
     (first-order parallel-curve geometry), and the exact slot
     map turns roller motion into slide motion. By power balance
     the same S is the contact-normal force per unit slide force
     (reciprocity). The identity cos q = cos(alpha_x) is
     witnessed numerically at every moving grid point.
  C. An independent numerical re-contact witness: at 13 angles
     per cam the pitch curve is locally resampled to a 0.01 deg
     polyline, perturbed by delta_w along the normal and along
     the tangent, both signs, and the contact is RE-SOLVED by
     distance minimization on the perturbed polyline (the
     follower axis for cam y, the lever-arm circle for cam x),
     never through the analytic map. Gates: normal agreement
     within 1e-3 relative at every witness point; tangential
     residues <= 1e-4 mm (second order).
  D. The tolerance budgets under the frozen worst-case-linear
     convention: uniform tolerance class on both cams, per-angle
     channel sum S_x(th) + S_y(th), then max over the arc,
     times delta; knee curve over 0.01-0.50 mm, the working
     number 0.10 mm against the 1.5 mm packaging overlay, and
     the break-even delta*.
  E. The pre-declared cap-under-tolerance branch: a normal error
     grows the pitch major radius by up to itself (the normal is
     radial at the extremum), so the 285 mm cap is re-tested
     under tolerance. The classification is frozen: a breach is
     a manufacturing-readiness finding, never a family failure;
     the terminal branches are a local tolerance <= headroom on
     the major arcs, or envelope renegotiation with the brief
     owner; never a new variant.
  F. The frozen calibration stance: a dwell-arc radius error is
     a CONSTANT slide offset (systematic, calibratable by a
     slide-datum adjustment at assembly); both raw and
     residual-after-calibration are reportable, but the gate
     scores the RAW error -- calibration credit is not claimed
     before an adjustment procedure exists (spec-ahead-of-tree).
  G. Data-only force-closure rows (the folded Q2): contact-
     normal force per unit slide force = S (reciprocity),
     per-unit-mass spring criteria at unit crank rate, the
     dwell-jump one-sided maxima at the two stop seams (the
     preload criterion), and the -06 torque proxies carried in.
     Nothing here gates; the future gate shape is the
     dimensionless contact-maintenance criterion with declared
     masses and a rated speed.
  H. The A-floor redeclaration (Q3, as data): the 60 mm floor
     was the scan-range prior, never a gate; the feasible
     interval on the recorded 1 mm ascension is [76, 77) --
     A = 77 stops on the cap, not the angle (verified against
     the regenerated design); the recorded pick at the TOP of
     the interval MINIMIZES the exact amplification (S_x scales
     as 1/A at fixed pivot geometry; monotonicity verified);
     no silent redeclaration.
  I. The scorecard reading: predictions frozen before the run,
     verdicts for the outcome record. The staging readings are
     NOT the run of record: the machine run on the-hub after
     merge is.

Exit code 0: every internal fail-closed check passed. Exit
code 1: an internal check failed (task validation, the oracle
cross-check, a witness, a data-row verification, determinism).
A tolerance-budget miss is NOT an error exit: the outcome
classification is frozen above.
"""

import argparse
import hashlib
import json
import math
import os
import sys

PI = math.pi
DEG = 180.0 / PI

# ------------------------------------------------- frozen constants
DEFAULT_TASK = os.path.join("jobs", "sixbar-gap-transfer-02",
                            "gap_transfer_nostops.motion.json")
TASK_SHA_RECORDED = ("591a562c33b7455476e20559fdd16f46"
                     "bb0c1a3c4645d4a25048e4607e3a24d5")
TASK_TOL = 1e-9                   # fail-closed, normalized units
REL_ORACLE = 5e-3                 # audit-float oracle tolerance

CAM_Y_BASE = 195.0                # the -05 carry-in base radius (mm)
CAM_Y_LIFT = 90.0                 # the cam-y lift (mm), y = +50 carry
OVERLAY = 1.5                     # packaging overlay (mm), the -01 record
WORKING = 0.10                    # working number delta (mm)
KNEE_DELTAS = (0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)

WITNESS_N = 13                    # witness angles per cam
WITNESS_DELTA = 0.02              # witness perturbation (mm)
WITNESS_SPAN = 40                 # polyline half-window (samples)
WITNESS_STEP = 0.01 * PI / 180.0  # polyline resample (rad)
REL_GATE = 1e-3                   # normal re-contact gate, relative
TAN_GATE = 1e-4                   # tangential residue gate (mm)
DEGEN = 1e-12                     # cos q degeneracy screen

RADIUS_CAP = 285.0                # pitch major-radius cap (mm)
A_FLOOR = 60.0                    # the -06 scan-range floor (mm)

# The recorded -06 outcome, embedded as data, labeled (the oracle
# this script must reproduce fail-closed before it maps anything).
ORACLE = {
    "A": 76.0, "Px": 8.0, "Py": -260.0, "Delta_print": "-74.3985",
    "alpha": 29.7366, "major": 284.932, "beta_deg": 27.958,
    "wind": 0.0623329, "lambda_eff_min": 3.42105,
    "lambda_eff_max": 3.87307, "rho_body_min": 176.774,
    "peak_cpp": 193.927, "peak_xs2": 812.885, "peak_xs1": 170.25,
    "cam_y_alpha": 25.8817, "cam_y_peak_hp": 119.816,
}

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE),
                                "dualcam-lever-transfer-06"))
import dualcam_lever_design as lv  # noqa: E402  (read-only import)


def fail(msg):
    raise SystemExit("fail-closed: " + msg)


def relerr(x, ref):
    return abs(x - ref) / abs(ref)


def g6(x):
    return "%.6g" % x


# ----------------------------------------------------- the exact map
def sx_state(u, up, upp, Px, Py, A, Delta):
    """S_x, cos q, cos(alpha_x) (moving points) and the fixed-frame
    roller centre at one slide state -- the exact lever map."""
    Cx, Cy, Cpx, Cpy, _, _, _ = lv.lever_centre(
        u, up, upp, Px, Py, A, Delta)
    c = complex(Cx, Cy)
    cp = complex(Cpx, Cpy)
    T = cp - 1j * c
    n = 1j * T
    nn = abs(n)
    if nn <= 0.0:
        fail("pitch tangent degenerate at u = %.6g" % u)
    om = math.atan2(Cy - Py, Cx - Px)
    f = complex(-math.sin(om), math.cos(om))
    cq = abs((f.conjugate() * n).real) / nn
    if cq < DEGEN:
        fail("cos q degenerate at u = %.6g" % u)
    L = math.hypot(u - Px, Py)
    S = L * L / (abs(Py) * A * cq)
    ca = None
    if up != 0.0:
        im = Cx * Cpy - Cy * Cpx
        re = Cx * Cpx + Cy * Cpy
        num = (Cpx * Cpx + Cpy * Cpy) - im
        ca = math.cos(math.atan2(abs(num), abs(re)))
    return S, cq, ca, complex(Cx, Cy)


def sy_state(th):
    """S_y and the pitch radius at crank angle th (cam y)."""
    h, hp, _, _ = lv.follower_state("y", th)
    r = CAM_Y_BASE + h
    return math.hypot(r, hp) / r, r


# ------------------------------------------------- witness machinery
def curve_sample(cam, th, d):
    """Roller centre C, unit normal n and unit tangent t of the
    pitch curve at crank angle th, fixed frame at rotation 0."""
    if cam == "y":
        h, hp, _, _ = lv.follower_state("y", th)
        r = CAM_Y_BASE + h
        C = complex(0.0, r)
        T = complex(r, hp)        # C' - iC with C = i r, C' = i hp
        nn = abs(T)
        return C, (1j * T) / nn, T / nn
    u, up, upp = d["u"](th)
    Cx, Cy, Cpx, Cpy, _, _, _ = lv.lever_centre(
        u, up, upp, d["Px"], d["Py"], d["A"], d["Delta"])
    c = complex(Cx, Cy)
    cp = complex(Cpx, Cpy)
    T = cp - 1j * c
    nn = abs(T)
    return c, (1j * T) / nn, T / nn


def perturbed_polyline(cam, th_w, delta, direction, d):
    """The pitch polyline around th_w, perturbed by delta along
    the normal ('n') or the tangent ('t'), held in the FIXED
    frame with the plate rotated to crank angle th_w."""
    pts = []
    for j in range(-WITNESS_SPAN, WITNESS_SPAN + 1):
        th_s = (th_w + j * WITNESS_STEP) % (2.0 * PI)
        C, n, t = curve_sample(cam, th_s, d)
        rot = complex(math.cos(th_w - th_s),
                      math.sin(th_w - th_s))
        e = n if direction == "n" else t
        pts.append(C * rot + delta * e * rot)
    return pts


def solve_axis_crossing(pts):
    """The polyline point on the follower axis (x = 0): bracket
    the crossing, refine linearly, keep the closest to the axis."""
    best = None
    for j in range(len(pts) - 1):
        x0, x1 = pts[j].real, pts[j + 1].real
        if x0 == 0.0:
            cand = pts[j]
        elif x0 * x1 < 0.0:
            t = -x0 / (x1 - x0)
            cand = pts[j] + t * (pts[j + 1] - pts[j])
        else:
            continue
        if best is None or abs(cand.real) < abs(best.real):
            best = cand
    if best is None:
        best = min(pts, key=lambda p: abs(p.real))
    return best


def solve_circle_crossing(pts, P, A, nominal):
    """The polyline point on the lever-arm circle |C - P| = A:
    bracket |C - P| - A sign changes, refine linearly, keep the
    crossing nearest the nominal contact."""
    cands = []
    for j in range(len(pts) - 1):
        g0 = abs(pts[j] - P) - A
        g1 = abs(pts[j + 1] - P) - A
        if g0 == 0.0:
            cands.append(pts[j])
        elif g0 * g1 < 0.0:
            t = -g0 / (g1 - g0)
            cands.append(pts[j] + t * (pts[j + 1] - pts[j]))
    if not cands:
        return min(pts, key=lambda p: abs(abs(p - P) - A))
    return min(cands, key=lambda p: abs(p - nominal))


def run_witness(d):
    """The re-contact witness: both cams, 13 angles, both signs,
    both directions. Returns the worst normal relative agreement
    and the worst tangential residue, per cam and overall."""
    out = {}
    for cam in ("x", "y"):
        worst_rel = 0.0
        worst_tan = 0.0
        for k in range(WITNESS_N):
            th_w = 2.0 * PI * k / WITNESS_N
            if cam == "y":
                S, r_w = sy_state(th_w)
                u_w = None
            else:
                u_w, up_w, upp_w = d["u"](th_w)
                S, _, _, C_nom = sx_state(
                    u_w, up_w, upp_w, d["Px"], d["Py"],
                    d["A"], d["Delta"])
            for sign in (1.0, -1.0):
                for direction in ("n", "t"):
                    pts = perturbed_polyline(
                        cam, th_w, sign * WITNESS_DELTA, direction, d)
                    if cam == "y":
                        c = solve_axis_crossing(pts)
                        disp = c.imag - r_w
                    else:
                        c = solve_circle_crossing(
                            pts, complex(d["Px"], d["Py"]),
                            d["A"], C_nom)
                        u_s = lv.lever_invert_pin(
                            c.real, c.imag, d["Px"], d["Py"],
                            d["Delta"])
                        disp = u_s - u_w
                    if direction == "n":
                        pred = S * WITNESS_DELTA
                        worst_rel = max(worst_rel,
                                        abs(abs(disp) - pred) / pred)
                    else:
                        worst_tan = max(worst_tan, abs(disp))
        out[cam] = (worst_rel, worst_tan)
    out["rel"] = max(out["x"][0], out["y"][0])
    out["tan"] = max(out["x"][1], out["y"][1])
    return out


# ------------------------------------------------------- the mapping
def build(d):
    """The whole mapping, computed from the regenerated design:
    grid maps, maxima, witnesses, budgets, cap rows, force rows,
    A-floor verifications. Pure and deterministic."""
    Px, Py, A, Delta = d["Px"], d["Py"], d["A"], d["Delta"]
    g = d["grid"]
    n = lv.GRID_N

    sx_carry_max = 0.0
    sx_carry_th = 0.0
    sx_full_max = 0.0
    sx_full_th = 0.0
    sy_max = 0.0
    sy_max_th = 0.0
    sum_carry = 0.0
    sum_full = 0.0
    ident = 0.0
    peak_hppy = 0.0
    peak_hpy = 0.0
    major_y = 0.0
    for i in range(n):
        th = g.th[i]
        S, cq, ca, _ = sx_state(g.u[i], g.up[i], g.upp[i],
                                Px, Py, A, Delta)
        if ca is not None:
            ident = max(ident, abs(ca - cq))
        h, hp, hpp, _ = lv.follower_state("y", th)
        r = CAM_Y_BASE + h
        Sy = math.hypot(r, hp) / r
        peak_hppy = max(peak_hppy, abs(hpp))
        peak_hpy = max(peak_hpy, abs(hp))
        if r > major_y:
            major_y = r
        tot = S + Sy
        if S > sx_full_max:
            sx_full_max, sx_full_th = S, th
        if Sy > sy_max:
            sy_max, sy_max_th = Sy, th
        if tot > sum_full:
            sum_full = tot
        if th <= lv.TH_CARRY_END:
            if abs(Sy - 1.0) > 1e-12:
                fail("S_y not exactly 1 on the carry dwell")
            if S > sx_carry_max:
                sx_carry_max, sx_carry_th = S, th
            if tot > sum_carry:
                sum_carry = tot

    # dwell constants (up = upp = 0: the pitch curve is the dwell
    # circle about the shaft; the general formula covers it)
    S_dwell_plus, _, _, _ = sx_state(130.0, 0.0, 0.0, Px, Py, A, Delta)
    S_dwell_minus, _, _, _ = sx_state(-130.0, 0.0, 0.0, Px, Py, A, Delta)

    wit = run_witness(d)

    # budgets (WC-L, frozen convention)
    knee = [(delta, delta * sum_carry, delta * sum_full)
            for delta in KNEE_DELTAS]
    wc_working_carry = WORKING * sum_carry
    wc_working_full = WORKING * sum_full
    star_carry = OVERLAY / sum_carry
    star_full = OVERLAY / sum_full

    # cap under tolerance (the pre-declared branch)
    major_x = d["audit"]["major"]
    if abs(major_y - (CAM_Y_BASE + CAM_Y_LIFT)) > 1e-9:
        fail("cam-y major radius is not the carry dwell cap value")
    headroom_x = RADIUS_CAP - major_x
    headroom_y = RADIUS_CAP - major_y
    cap_rows = []
    for delta in KNEE_DELTAS:
        eff_x = major_x + delta
        eff_y = major_y + delta
        cap_rows.append((delta, eff_x, max(0.0, eff_x - RADIUS_CAP),
                         eff_y, max(0.0, eff_y - RADIUS_CAP)))

    # force-closure rows (data only)
    seams = ((0.0, (5, 0)), (lv.TH_CARRY_END, (0, 1)))
    jump_x = 0.0
    jump_y = 0.0
    for th, sides in seams:
        for seg in sides:
            jump_x = max(jump_x,
                         abs(lv.follower_sided("x", seg, th)[2]))
            jump_y = max(jump_y,
                         abs(lv.follower_sided("y", seg, th)[2]))

    # A-floor data verification (internal, fail-closed)
    g1 = lv.LeverGrid(lv.REFINE_N)
    cur = {"Px": Px, "Py": Py, "A": 77.0, "Delta": Delta}
    r77 = lv.refine_candidate(g1, cur)
    f77 = lv.eval_lever(g, r77["Px"], r77["Py"], 77.0, r77["Delta"])
    if not (f77["alpha"] <= lv.ALPHA_TARGET
            and f77["major"] > RADIUS_CAP):
        fail("A = 77 does not stop on the cap as recorded")
    prev = None
    for Ax in (60.0, 65.0, 70.0, 76.0):
        best = 0.0
        for i in range(n):
            th = g.th[i]
            if th > lv.TH_CARRY_END:
                break
            S, _, _, _ = sx_state(g.u[i], g.up[i], g.upp[i],
                                  Px, Py, Ax, Delta)
            if S > best:
                best = S
        if prev is not None and best >= prev:
            fail("S_x carry max not monotone decreasing in A")
        prev = best

    return {
        "sx_carry_max": sx_carry_max, "sx_carry_th": sx_carry_th,
        "sx_full_max": sx_full_max, "sx_full_th": sx_full_th,
        "sy_max": sy_max, "sy_max_th": sy_max_th,
        "ident": ident, "peak_hppy": peak_hppy, "peak_hpy": peak_hpy,
        "sum_carry": sum_carry, "sum_full": sum_full,
        "S_dwell_plus": S_dwell_plus, "S_dwell_minus": S_dwell_minus,
        "witness": wit,
        "knee": knee,
        "wc_working_carry": wc_working_carry,
        "wc_working_full": wc_working_full,
        "star_carry": star_carry, "star_full": star_full,
        "major_x": major_x, "major_y": major_y,
        "headroom_x": headroom_x, "headroom_y": headroom_y,
        "cap_rows": cap_rows,
        "jump_x": jump_x, "jump_y": jump_y,
    }


# ---------------------------------------------------------- render
def render(res):
    """Sections [B]-[H] as one text block, a pure function of the
    computed mapping (the determinism control compares two of
    these byte-for-byte)."""
    L = []
    L.append("[B] The exact error map (0.1 deg grid, %d points)"
             % lv.GRID_N)
    L.append("    S_x(th) = L^2 / (|Py| A cos q): L = hypot(u - Px,"
             " Py), cos q = |f . n| (the roller")
    L.append("      constraint direction against the pitch-curve"
             " normal); S_y(th) = hypot(r, h') / r = 1/cos(alpha_y),")
    L.append("      r = 195 + h (the -05 carry-in base circle); by"
             " reciprocity S is also the")
    L.append("      contact-normal force per unit slide force")
    L.append("    cam x: S_x carry max %s at %.1f deg, full-cycle"
             " max %s at %.1f deg"
             % (g6(res["sx_carry_max"]), res["sx_carry_th"] * DEG,
                g6(res["sx_full_max"]), res["sx_full_th"] * DEG))
    L.append("    cam y: S_y max %s at %.1f deg; on the carry arc"
             " S_y = 1.000 exactly"
             % (g6(res["sy_max"]), res["sy_max_th"] * DEG))
    L.append("      (the carry IS the cam-y dwell; asserted)")
    L.append("    identity witness cos q = cos(alpha_x) at every"
             " moving grid point: worst |diff| %.3e" % res["ident"])
    L.append("")
    wit = res["witness"]
    L.append("[C] Numerical re-contact witness (independent"
             " polyline re-solve, %d angles/cam, both signs,"
             " both directions)" % WITNESS_N)
    L.append("    the pitch curve locally resampled at 0.01 deg,"
             " perturbed by delta_w = %g mm along the normal and"
             " the tangent;" % WITNESS_DELTA)
    L.append("    contact re-solved by distance minimization on"
             " the perturbed polyline (follower axis for cam y,"
             " lever-arm circle for cam x)")
    L.append("    normal direction: worst relative agreement cam"
             " x %.3e, cam y %.3e (gate 1e-3)"
             % (wit["x"][0], wit["y"][0]))
    L.append("    tangential direction: worst slide residue cam x"
             " %.3e mm, cam y %.3e mm (gate 1e-4 mm; second order)"
             % (wit["x"][1], wit["y"][1]))
    L.append("")
    L.append("[D] Budgets (WC-L, frozen convention)")
    L.append("    convention (frozen before the run):"
             " worst-case-linear; uniform tolerance class on both"
             " cams;")
    L.append("      per-angle channel sum S_x(th) + S_y(th), then"
             " max over the arc, times delta (mm)")
    L.append("    knee curve (task-space path error, mm):")
    for delta, carry, full in res["knee"]:
        L.append("      delta %5g: carry %8g   full cycle %8g"
                  % (delta, carry, full))
    L.append("    WC-L at the working number: carry %s mm vs"
             " overlay %s mm -> %s"
             % (g6(res["wc_working_carry"]), g6(OVERLAY),
                "PASS" if res["wc_working_carry"] <= OVERLAY
                else "FAIL"))
    L.append("    break-even delta* (WC-L = overlay): carry %s mm,"
             " full cycle %s mm"
             % (g6(res["star_carry"]), g6(res["star_full"])))
    L.append("")
    L.append("[E] Cap under tolerance (the pre-declared branch)")
    L.append("    nominal major radii: cam x %s mm (headroom %s mm),"
             " cam y %s mm (headroom %s mm -- exactly at the cap)"
             % (g6(res["major_x"]), g6(res["headroom_x"]),
                g6(res["major_y"]), g6(res["headroom_y"])))
    L.append("    a normal error delta grows the major radius by up"
             " to delta (the normal is radial at the extremum):")
    for delta, eff_x, br_x, eff_y, br_y in res["cap_rows"]:
        L.append("      delta %5g: cam x effective major %10g"
                 " (breach %8g)   cam y %9g (breach %8g)"
                 % (delta, eff_x, br_x, eff_y, br_y))
    L.append("    reading: the branch FIRES at any uniform WC delta"
             " > %s mm (cam x) and > 0 (cam y): a"
             " manufacturing-readiness finding, never a family"
             " failure; terminal branches = local tolerance <="
             " headroom on the major arcs, or envelope"
             " renegotiation with the brief owner; never a new"
             " variant" % g6(res["headroom_x"]))
    L.append("")
    L.append("[F] Calibration stance (frozen: raw error gates)")
    L.append("    dwell-radius error = CONSTANT slide offset"
             " (systematic):")
    L.append("      cam-x dwells: S_x = %s (descent, u=+130), %s"
             " (ascent, u=-130)"
             % (g6(res["S_dwell_plus"]), g6(res["S_dwell_minus"])))
    L.append("      cam-y carry dwell: S_y = 1.000 (r = %s mm);"
             " return dwell: S_y = 1.000 (r = %s mm)"
             % (g6(CAM_Y_BASE + CAM_Y_LIFT), g6(CAM_Y_BASE)))
    L.append("    slide-datum adjustment at assembly absorbs the"
             " systematic dwell error entirely (residual 0 for the")
    L.append("      systematic case); arbitrary per-point errors get"
             " NO worst-case credit (the datum adds its own term);")
    L.append("      the gate scores the RAW error -- claiming"
             " calibration credit before an adjustment procedure"
             " exists would be spec-ahead-of-tree again")
    L.append("")
    L.append("[G] Force-closure rows (data-only; masses and speed"
             " unrated; per unit mass at unit crank rate)")
    L.append("    contact NORMAL force per unit slide force = S(th)"
             " (power-balance reciprocity): cam x max %s (carry max"
             " %s), cam y max %s"
             % (g6(res["sx_full_max"]), g6(res["sx_carry_max"]),
                g6(res["sy_max"])))
    L.append("    spring criteria per unit mass (N/kg per"
             " (rad/s)^2):")
    L.append("      cam-y follower %s (peak |h''| %s mm/rad^2)"
             % (g6(res["peak_hppy"] / 1000.0), g6(res["peak_hppy"])))
    L.append("      cam-x roller %s (peak |C''| %s mm/rad^2)"
             % (g6(ORACLE["peak_cpp"] / 1000.0),
                g6(ORACLE["peak_cpp"])))
    L.append("      x slide %s (peak |x_s''| %s mm/rad^2)"
             % (g6(ORACLE["peak_xs2"] / 1000.0),
                g6(ORACLE["peak_xs2"])))
    L.append("    dwell-jump case (one-sided |a| at the two stop"
             " seams, the preload criterion): cam x slide-space %s,"
             " cam y %s mm/rad^2"
             % (g6(res["jump_x"]), g6(res["jump_y"])))
    L.append("    torque proxies (carried in from -06): cam x %s,"
             " cam y %s mm/rad"
             % (g6(ORACLE["peak_xs1"]), g6(res["peak_hpy"])))
    L.append("    nothing here gates; the future gate shape is the"
             " dimensionless contact-maintenance criterion with")
    L.append("      declared masses and a rated speed")
    L.append("")
    L.append("[H] A-floor redeclaration (Q3, data)")
    L.append("    declared floor %s mm = the scan-range prior, never"
             " a gate; recorded pick A = %s mm; feasible interval"
             " [76, 77) on the recorded 1 mm ascension (A = 77 stops"
             " on the cap)"
             % (g6(A_FLOOR), g6(ORACLE["A"])))
    L.append("    S_x is 1/A at fixed pivot geometry; the recorded"
             " pick at the top of the feasible interval MINIMIZES"
             " the exact amplification")
    L.append("    %s mm survives as the scan convention (a"
             " conditional aspiration only); no silent"
             " redeclaration -- this is the recorded round"
             % g6(A_FLOOR))
    return "\n".join(L)


T_LINES = [
    "T1 PREDICTED: HELD: the regenerated pick and audit match the"
    " recorded -06 oracle (A, P, Delta exact; audit floats within"
    " 5e-3 relative). Disclosed risk: cross-platform libm"
    " last-ulp noise flipping a scan tie aborts fail-closed; the"
    " run of record is then the machine of record (the-hub).",
    "T2a PREDICTED: S_x full-cycle max in [4.4, 5.6] -- ABOVE the"
    " sketched lambda_eff range 3.42-3.87 by the factor"
    " (L/|Py|)/cos(alpha): margin exhaustion recorded, not a"
    " gate failure.",
    "T2b PREDICTED: S_x carry max in [4.3, 5.2]; S_y = 1.000"
    " exactly on the carry (the carry IS the cam-y dwell;"
    " asserted); S_y full-cycle max = 1.1115 (arithmetic from the"
    " recorded 25.8817 deg). Staging note: the first draft of"
    " this prediction carried a hand-arithmetic slip (1.1094),"
    " caught by the staging smoke run and corrected BEFORE the"
    " scorecard was frozen in the JOB; the machine run must"
    " measure 1/cos(25.8817 deg).",
    "T2c PREDICTED: numerical re-contact witness: normal agreement"
    " within 1e-3 relative at all witness points; tangential"
    " residues <= 1e-4 mm (second order).",
    "T3 PREDICTED: WC-L at the working number 0.10 mm: carry error"
    " in [0.50, 0.78] mm <= 1.5 mm overlay -> HELD with margin"
    " (~2x); knee break-even delta* (carry) in [0.19, 0.30] mm. A"
    " miss is a manufacturing-readiness finding per declaration 2,"
    " never a family failure.",
    "T4 PREDICTED: the cap-under-tolerance branch FIRES at any"
    " uniform WC delta > 0.068 mm (cam-x major headroom 0.068 mm;"
    " cam-y headroom 0.000 mm -- the carry dwell sits exactly at"
    " the cap): a manufacturing-readiness finding; the terminal"
    " branches are a local tolerance <= headroom on the major arcs"
    " or envelope renegotiation with the brief owner; never a new"
    " variant. The -06 HELD record stands.",
    "T5 PREDICTED: dwell-radius error = constant offset (S = 1 on"
    " the cam-y carry dwell; S_x on the cam-x dwells reported):"
    " fully absorbed by a slide-datum adjustment in the systematic"
    " case (residual 0); arbitrary errors get NO worst-case"
    " credit; the gate scores raw.",
    "T6 PREDICTED: data-only force rows: contact-normal force per"
    " unit slide force = S (reciprocity); per-unit-mass spring"
    " criteria at unit crank rate (cam-y follower 0.696, roller"
    " 0.194, slide 0.813 N/kg per (rad/s)^2 class); dwell-jump"
    " one-sided maxima reported; nothing gated (the future gate"
    " shape is noted, rated forces need declared masses and"
    " speed).",
    "T7 PREDICTED: A-floor status redeclared as data: the 60 mm"
    " floor was the scan-range prior, never a gate; the feasible"
    " interval is [76, 77) on the recorded 1 mm ascension (A = 77"
    " stops on the cap, not the angle); 60 mm survives as the scan"
    " convention; the recorded pick at the TOP of the interval"
    " MINIMIZES the exact amplification (S_x scales as 1/A at"
    " fixed pivot geometry).",
]


def main(argv):
    ap = argparse.ArgumentParser(
        description="Profile-tolerance -> path-error map for the"
                    " recorded -06 Option B design (pure stdlib,"
                    " no network)")
    ap.add_argument("--task", default=DEFAULT_TASK,
                    help="frozen -02 task JSON (read-only)")
    args = ap.parse_args(argv)

    task_path = args.task
    if not os.path.exists(task_path):
        alt = os.path.join(REPO_ROOT, task_path)
        if os.path.exists(alt):
            task_path = alt
        else:
            fail("task file not found: %s" % args.task)
    with open(task_path, "rb") as fh:
        task_bytes = fh.read()
    task_sha = hashlib.sha256(task_bytes).hexdigest()
    if task_sha != TASK_SHA_RECORDED:
        fail("task sha256 %s does not match the recorded -02 "
             "byte-identity witness" % task_sha)
    task = json.loads(task_bytes.decode("utf-8"))
    worst = lv.validate_task(task)
    if worst is None:
        fail("task third component nonzero")
    if max(worst["q"], worst["v"], worst["a"]) > TASK_TOL:
        fail("task validation exceeds 1e-9 normalized units")

    # the recorded -06 design, regenerated (the scan runs ONCE)
    pick, _, mode = lv.pick_design()
    if pick is None:
        fail("the -06 scan is infeasible -- contradicts the record")
    if mode != "meets-target":
        fail("pick mode %s contradicts the recorded -06 outcome"
             % mode)
    g_full = lv.LeverGrid(lv.GRID_N)
    audit = lv.audit_lever(g_full, pick)

    # oracle cross-check (fail-closed)
    if pick["A"] != ORACLE["A"] or pick["Px"] != ORACLE["Px"] \
            or pick["Py"] != ORACLE["Py"]:
        fail("regenerated pick A/P does not match the record")
    if g6(pick["Delta"] * DEG) != ORACLE["Delta_print"]:
        fail("regenerated Delta print does not match the record")
    for key in ("alpha", "major", "beta_deg", "wind",
                "lambda_eff_min", "lambda_eff_max", "rho_body_min",
                "peak_cpp", "peak_xs2", "peak_xs1"):
        if relerr(audit[key], ORACLE[key]) > REL_ORACLE:
            fail("regenerated audit %s does not match the record"
                 % key)
    aud_y = lv.audit_cam("y", CAM_Y_BASE)
    if relerr(aud_y["worst_alpha"], ORACLE["cam_y_alpha"]) > REL_ORACLE:
        fail("regenerated cam-y audit does not match the record")

    def u_state(th):
        h, hp, hpp, _ = lv.follower_state("x", th)
        return h - 130.0, hp, hpp

    d = {"Px": pick["Px"], "Py": pick["Py"], "A": pick["A"],
         "Delta": pick["Delta"], "grid": g_full, "audit": audit,
         "u": u_state}

    res1 = build(d)
    res2 = build(d)
    txt1 = render(res1)
    txt2 = render(res2)
    same = txt1 == txt2
    if not same:
        print("FAIL-CLOSED VIOLATION: determinism (mapping differs)")
        return 1
    if res1["witness"]["rel"] > REL_GATE \
            or res1["witness"]["tan"] > TAN_GATE:
        print("FAIL-CLOSED VIOLATION: re-contact witness gate")
        return 1

    out = []
    out.append("=" * 64)
    out.append("dualcam-profile-tolerance-07 profile-tolerance ->"
               " path-error map")
    out.append("=" * 64)
    out.append("python: %s" % sys.version.split()[0])
    out.append("task file: %s" % task_path)
    out.append("task sha256: %s" % task_sha)
    out.append("")
    out.append("[A] Reproduction of the recorded -06 design"
               " (fail-closed)")
    out.append("    -02 task validation (the -06 module's own"
               " reconstruction): max |dq| %.3e, max |dv| %.3e,"
               " max |da| %.3e (tol 1e-9) -> PASS"
               % (worst["q"], worst["v"], worst["a"]))
    out.append("    task sha256 matches the recorded -02"
               " byte-identity witness -> PASS")
    out.append("    pick_design() regenerated (the design scan ran"
               " once): mode %s" % mode)
    out.append("      A = %s mm, P = (%s, %s) mm, Delta = %s deg"
               % (g6(pick["A"]), g6(pick["Px"]), g6(pick["Py"]),
                  g6(pick["Delta"] * DEG)))
    out.append("    oracle cross-check vs the recorded -06 outcome"
               " (A, P, Delta exact at the recorded print"
               " precision;")
    out.append("      audit floats within 5e-3 relative) -> PASS")
    out.append("      alpha %s deg at %.1f deg, major %s mm,"
               " beta_out %s deg, wind %s, lambda_eff %s-%s,"
               " rho_body %s mm,"
               % (g6(audit["alpha"]), audit["alpha_theta"] * DEG,
                  g6(audit["major"]), g6(audit["beta_deg"]),
                  g6(audit["wind"]),
                  g6(audit["lambda_eff_min"]),
                  g6(audit["lambda_eff_max"]),
                  g6(audit["rho_body_min"])))
    out.append("      peak |C''| %s and peak |x_s''| %s mm/rad^2,"
               " peak |x_s'| %s mm/rad"
               % (g6(audit["peak_cpp"]), g6(audit["peak_xs2"]),
                  g6(audit["peak_xs1"])))
    out.append("      cam y (base %s mm): worst alpha %s deg at"
               " %.1f deg -> the -06 record reproduced"
               % (g6(CAM_Y_BASE), g6(aud_y["worst_alpha"]),
                  aud_y["worst_alpha_theta"] * DEG))
    out.append("")
    out.append(txt1)
    out.append("")
    out.append("[I] Scorecard reading (predictions frozen before"
               " the run; verdicts for the outcome record)")
    for line in T_LINES:
        out.append("    " + line)
    out.append("    measured: S_x carry max %s, full %s; S_y max"
               " %s; WC-L(0.10) carry %s mm; delta* carry %s mm;"
               " headroom cam x %s mm, cam y %.3f mm"
               % (g6(res1["sx_carry_max"]), g6(res1["sx_full_max"]),
                  g6(res1["sy_max"]), g6(res1["wc_working_carry"]),
                  g6(res1["star_carry"]), g6(res1["headroom_x"]),
                  res1["headroom_y"]))
    out.append("    determinism: PASS (the whole mapping computed"
               " twice, byte-identical; the design scan ran once by"
               " declaration -- its oracle cross-check is the"
               " stronger check)")
    out.append("    control: the -02 task consumed read-only"
               " (sha256 above); the -06 module consumed read-only"
               " (imported, never modified); no gate loosened"
               " anywhere")
    out.append("-" * 64)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
