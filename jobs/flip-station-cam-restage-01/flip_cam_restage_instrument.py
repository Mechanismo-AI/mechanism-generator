#!/usr/bin/env python3
"""flip-station-cam-restage-01 -- the cam line re-stage Stage 1.

The deterministic design script per the -05/-06 pattern (the case-B
lineage), staged per this job's freeze and the cam class ruling's
Field 8 row (docs/cam-class-ruling-answer.md, PR #111). The
re-derived class gate is CONSUMED here, never re-derived.

Declared search classes (frozen BEFORE any synthesis runs; never
re-drawn after a run -- the staged-declaration discipline):

  F0  fixed-pivot rigid-mount (the recorded boundary class) --
      FAILS S1 by the recorded C1a arithmetic, carried from the
      recorded study (jobs/flip-station-capability-01), never
      re-litigated. This row IS the class boundary the other
      classes must exit or fail against.
  G1  dual-groove plate-cam carrier (the recorded study's own
      class; jobs/flip-station-capability-01; the case-B -05/-06
      exact construction carried) -- the frozen sweep re-graded
      under the re-derived gate; the recorded chosen design
      (d = 0.2, C_y = 0.0) re-graded as its own reference row,
      its recorded outcome keeping its meaning.
  C1  cam+lever pivoted-cradle composition (the case-B cam+lever
      class; jobs/dualcam-lever-transfer-06: a general pivoted
      lever) -- a carriage translates on the carry plane (a
      groove-cam channel, the -05 in-line translating pin
      follower pattern); the part rides a cradle pivoted ON the
      carriage (a MOVING pivot: exits C1a -- the centroid path
      is not a circle); the cradle is driven through a
      frame-pivoted lever whose radial slot engages a cradle pin
      (the -06 lever parametrization: pivot P, short arm A,
      inter-arm angle Delta; the -06 rocker inversion for the
      cam profile).

Graded rows (frozen in this JOB.md), per class:

  S1  pose feasibility: the three ordered poses at the recorded
      tolerances (1.5 mm / 1.5 deg), exact by construction,
      machine-verified witnesses.
  S2  the re-derived gate: pressure angle <= 73.300756 deg at
      the committed inputs (mu 0.10-0.15, SF 2) over the loaded
      arcs at EVERY transmitting pair (groove-pin, groove-
      roller, slot-pin); the gate arithmetic re-computed and
      checked fail-closed against the frozen six-digit values;
      the self-lock boundary (81.469234 deg at mu 0.15 /
      84.289407 deg at mu 0.10) reported alongside; efficiency
      as data (loss = mu * tan(alpha); the gate IS the 50
      percent loss boundary, checked).
  S3  curvature and dead-point rows: groove min radius >= 1.25 x
      pin/roller radius (the recorded precedent; pins the 4 mm
      commercial cam-pin class, the roller 15 mm, the -06
      first-cut radius lineage); dead-point bands excluded from
      the gates and recorded as data; fail-closed where the
      constraint pair degenerates.
  S4  WC-L tolerance at BOTH handoff poses, channels separate
      (the drive-reversal backlash channel priced): groove
      clearance 0.1 mm per side + profile 0.05 mm centerline
      class per channel; the slot wall at the same 0.1 mm
      clearance class; combined = their sum; min-norm linear
      maps; worst case over the clearance-sign corners; rank
      deficiency fails closed with the reason recorded;
      dead-point rows, never finite numbers.
  S5  the exact-rectangle part envelope at 0.25 deg pose samples
      (sampled, never certified) with the carriage, lever,
      cradle-pin and plate extents in one utilization table;
      the handoff stations carried; recorded data, not gated
      (no size demand is frozen by the brief); packaging per
      the -05 axial-stack convention.
  S6  the scored reciprocity row: the instrument modification
      count (modifications to the carried audit structure; 0
      expected, any delta named).

The wide-fail branch (pre-stated in the freeze): if no declared
class passes all rows, the honest all-fail IS the outcome; every
verdict prints as data; the gate is never relaxed.

Conventions (carried): 1 unit = 100 mm (task layer, cases A/B/C);
pure stdlib; ASCII only; deterministic (no clocks, no randomness,
sorted keys; run twice and diff -- byte-identical is the
control); fail-closed throughout; corpus emission additive
(schema 1.2 with a changelog row; units block + provenance on
every row; unknown row kinds refused; non-finite numbers
refused).

This script has never been executed at staging (syntax-compiled
only). No run, training, or automation is started by this file's
existence; the owner executes every run; the machine step in this
JOB.md is the run of record.

Usage:
  python flip_cam_restage_instrument.py --source-commit <40-hex>
"""

import hashlib
import json
import math
import os
import sys

JOB_ID = "flip-station-cam-restage-01"
CORPUS_SCHEMA_VERSION = "1.2"
CORPUS_MAJOR = "1"

# The frozen demand (carried from the recorded brief, read-only):
# three ordered poses, tolerances 1.5 mm position / 1.5 deg
# orientation at the handoffs.
DEMANDS = [
    {"x": -1.3, "y": 0.5, "phi_deg": 0.0},
    {"x": 0.0, "y": 0.5, "phi_deg": 90.0},
    {"x": 1.3, "y": 0.5, "phi_deg": 180.0},
]
TOL_POS_UNITS = 0.015    # 1.5 mm
TOL_ORI_DEG = 1.5

# The re-derived class gate (the ruling's Field 8 row, CONSUMED):
# gate tan(alpha) <= 1/(SF*mu) at the committed inputs; the binding
# end is mu = 0.15. The frozen six-digit values are checked against
# the re-computed arithmetic, fail-closed.
SF = 2.0
MU_LOOSE = 0.10
MU_BINDING = 0.15
GATE_LOOSE_FROZEN = 78.690068
GATE_BINDING_FROZEN = 73.300756
SELFLOCK_LOOSE_FROZEN = 84.289407
SELFLOCK_BINDING_FROZEN = 81.469234
GATE_DIGITS = 6

# Class G1: the recorded study's frozen sweep, carried unchanged.
SWEEP_D = [0.1, 0.2, 0.3, 0.4, 0.5]
SWEEP_CY = [0.0, 0.25, 0.5]
RECORDED_DESIGN = {"d": 0.2, "C_y": 0.0}

# Class C1: the declared scan (frozen BEFORE synthesis).
SCAN_PX = [-0.5, 0.0, 0.5]
SCAN_PY = [0.9, 1.1, 1.3]
SCAN_A = [0.15, 0.25, 0.35]
SCAN_DELTA = [-8.0, 0.0, 8.0]
SCAN_RP = [0.15, 0.25, 0.35]
SCAN_BETA = [0.0, 90.0, 180.0]

# Class C1 declared architecture constants (each with its reason,
# frozen here before synthesis):
# - the identity mount is FORCED by the demand: the cradle pivot
#   rides the centroid line y = 0.5 and the centroid coincides
#   with the pivot (mounting vector (0, 0), angle 0 deg, in the
#   cradle frame -- the recorded B2 field structure carried).
PIVOT_Y = 0.5
# - the channel-X pin offset in the carriage frame: 0.30 units
#   below the pivot line, clear of the part swing disc; in-plan
#   overlap is packaging, not interference (the -05 axial-stack
#   convention).
CARRIAGE_PIN_OFFSET = (0.0, -0.30)
# - both plate centers on the symmetry axis, 1.0 unit below the
#   carry plane: each groove stays an annulus, off the
#   rotation-axis neighborhood (a groove through the plate
#   center is not a member of this class).
PLATE_CENTER = (0.0, -1.0)
# - the lever pivot floor: candidates whose cradle-pin path comes
#   closer than this to the lever pivot fail the scan (the slot
#   degenerates); recorded as data, never a gate relaxation.
LEVER_PIN_FLOOR = 0.10

# Pin/roller classes (lineage carried): every groove pin is the
# 4 mm commercial cam-pin class (the recorded study's class); the
# lever roller is 15 mm (the -06 first-cut roller radius).
PIN_RADIUS = 0.04
ROLLER_RADIUS = 0.15
CURVATURE_FACTOR = 1.25

# WC-L channel classes (carried from the recorded study).
CLEARANCE_UNITS = 0.001    # 0.1 mm per side, groove backlash
PROFILE_UNITS = 0.0005     # 0.05 mm centerline profile class
SLOT_CLEARANCE_UNITS = 0.001  # 0.1 mm per side, the slot wall
                             # (the groove backlash class)

# Part model: exact in-plane rectangle 100 x 5 mm (carried).
PART_HALF_LONG = 0.5
PART_HALF_SHORT = 0.025

# Dead-point / window / rank conventions (carried).
DEAD_POINT_BAND_UNITS = 0.001
GATE_WINDOW_FRACTION = 0.01
RANK_EPS = 1e-12
EPS_GEOM = 1e-12
EPS_VALIDATE = 1e-9

# Emission grids (frozen, deterministic).
SCAN_STEP_DEG = 1.0        # class C1 coarse scan
FINE_STEP_DEG = 0.05       # finalist audit / class G1 sweep
WITNESS_STEP_DEG = 5.0     # witness grid
SENSITIVITY_STEP_DEG = 5.0  # emitted sensitivity rows
ENVELOPE_STEP_DEG = 0.25   # part-rectangle corner sampling
FD_STEP_DEG = 0.001        # FD self-check step
FD_TOL = 1e-5              # FD self-check tolerance (relative)

OUTPUT_DIR = os.path.join("runs", JOB_ID)
CORPUS_STEM = "flip_cam_restage_v1"


# ---------------------------------------------------------------------------
# Gate constants: re-computed, checked fail-closed against the frozen values.
# ---------------------------------------------------------------------------

def gate_constants():
    lo = MU_LOOSE
    bi = MU_BINDING
    gate_loose = math.degrees(math.atan(1.0 / (SF * lo)))
    gate_binding = math.degrees(math.atan(1.0 / (SF * bi)))
    lock_loose = math.degrees(math.atan(1.0 / lo))
    lock_binding = math.degrees(math.atan(1.0 / bi))
    if round(gate_loose, GATE_DIGITS) != GATE_LOOSE_FROZEN:
        raise ValueError("gate arithmetic mismatch at mu 0.10: "
                         "%.6f vs frozen %.6f -- the gate is "
                         "consumed, never re-derived"
                         % (gate_loose, GATE_LOOSE_FROZEN))
    if round(gate_binding, GATE_DIGITS) != GATE_BINDING_FROZEN:
        raise ValueError("gate arithmetic mismatch at mu 0.15: "
                         "%.6f vs frozen %.6f -- the gate is "
                         "consumed, never re-derived"
                         % (gate_binding, GATE_BINDING_FROZEN))
    if round(lock_loose, GATE_DIGITS) != SELFLOCK_LOOSE_FROZEN:
        raise ValueError("self-lock arithmetic mismatch at mu 0.10")
    if round(lock_binding, GATE_DIGITS) != SELFLOCK_BINDING_FROZEN:
        raise ValueError("self-lock arithmetic mismatch at mu 0.15")
    # The gate IS the 50 percent loss boundary: mu*tan(gate) = 1/SF.
    for mu, gate in ((lo, gate_loose), (bi, gate_binding)):
        loss = mu * math.tan(math.radians(gate))
        if abs(loss - 1.0 / SF) > 1e-9:
            raise ValueError("gate is not the 50 percent loss "
                             "boundary at mu %.2f" % mu)
    return {
        "gate_loose_deg": gate_loose,
        "gate_binding_deg": gate_binding,
        "selflock_loose_deg": lock_loose,
        "selflock_binding_deg": lock_binding,
        "sf": SF,
        "mu_loose": lo,
        "mu_binding": bi,
    }


# ---------------------------------------------------------------------------
# Shared math / motion program (carried from the recorded study).
# ---------------------------------------------------------------------------

def rot(angle_rad, v):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def rot90(v):
    return (-v[1], v[0])


def smoother(u):
    return 6.0 * u ** 5 - 15.0 * u ** 4 + 10.0 * u ** 3


def smoother_d1(u):
    return 30.0 * u ** 4 - 60.0 * u ** 3 + 30.0 * u ** 2


def smoother_d2(u):
    return 120.0 * u ** 3 - 180.0 * u ** 2 + 60.0 * u


def program_u(t_deg):
    """Program parameter u in [0, 1] for drive angle t (out-and-back).

    One drive turn per cycle: the forward (carry) arc is 0 -> 180
    deg, the return arc 180 -> 360 deg. The program is a
    synthesized design freedom (the recorded case-A precedent --
    only the three poses are demanded); declared and carried.
    """
    if t_deg < 0.0 or t_deg > 360.0:
        raise ValueError("drive angle out of [0, 360]")
    if t_deg <= 180.0:
        return t_deg / 180.0
    return (360.0 - t_deg) / 180.0


def pose_at(t_deg):
    """Carrier pose (x, y, phi_rad) at drive angle t (exact program)."""
    u = program_u(t_deg)
    s = smoother(u)
    return -1.3 + 2.6 * s, 0.5, math.pi * s


def pose_derivs(t_deg):
    """Pose and its first/second derivatives w.r.t. t (degrees)."""
    u = program_u(t_deg)
    s1 = smoother_d1(u)
    s2 = smoother_d2(u)
    du = 1.0 / 180.0 if t_deg <= 180.0 else -1.0 / 180.0
    x = -1.3 + 2.6 * smoother(u)
    y = 0.5
    phi = math.pi * smoother(u)
    xp = 2.6 * s1 * du
    xpp = 2.6 * s2 / (180.0 ** 2)
    phip = math.pi * s1 * du
    phipp = math.pi * s2 / (180.0 ** 2)
    return x, y, phi, xp, xpp, phip, phipp


def grid(step):
    out = []
    n = int(round(360.0 / step))
    for i in range(n):
        out.append(round(i * step, 10))
    return out


def pin_path(q, t_deg):
    """Point fixed in the carrier frame: world path + derivatives.

    Used for: the G1 groove pins (recorded), the C1 cradle pin
    (q = the cradle-frame pin offset).
    """
    x, y, phi, xp, xpp, phip, phipp = pose_derivs(t_deg)
    r = rot(phi, q)
    r90 = rot(phi + math.pi / 2.0, q)
    w = (x + r[0], y + r[1])
    wp = (xp + phip * r90[0], phip * r90[1])
    wpp = (xpp + phipp * r90[0] - phip * phip * r[0],
           phipp * r90[1] - phip * phip * r[1])
    return w, wp, wpp


def groove_from_path(w, wp, wpp, t_deg, C):
    """Groove curve g(t) = R(-Theta)(w(t) - C) and derivatives.

    g'  = R(-T)(w'  - c rot90(w - C)),   c = pi/180
    g'' = R(-T)(w'' - 2c rot90(w') - c^2 (w - C))
    (the recorded construction's closed form, carried; the last
    term carries the chain-rule minus from rot90^2 = -I;
    cross-checked against finite differences at run time.)
    """
    theta = math.radians(t_deg)
    c = math.pi / 180.0
    rel = (w[0] - C[0], w[1] - C[1])
    rel90 = rot90(rel)
    g = rot(-theta, rel)
    u1 = (wp[0] - c * rel90[0], wp[1] - c * rel90[1])
    gp = rot(-theta, u1)
    wp90 = rot90(wp)
    u2 = (wpp[0] - 2.0 * c * wp90[0] - c * c * rel[0],
          wpp[1] - 2.0 * c * wp90[1] - c * c * rel[1])
    gpp = rot(-theta, u2)
    return g, gp, gpp


# ---------------------------------------------------------------------------
# FD self-check (the family's FD discipline, carried): the analytic
# derivative machinery above is cross-checked against central
# differences at witness samples; fail-closed on mismatch.
# ---------------------------------------------------------------------------

def fd_check():
    """Cross-check analytic derivatives against central differences."""
    probe = [((0.2, 0.0), 30.0), ((0.2, 0.0), 100.0), ((-0.3, 0.0), 250.0)]
    h = FD_STEP_DEG
    for q, t in probe:
        w0, wp0, wpp0 = pin_path(q, t)
        wpm, _, _ = pin_path(q, t - h)
        wpp, _, _ = pin_path(q, t + h)
        fd1 = ((wpp[0] - wpm[0]) / (2.0 * h),
               (wpp[1] - wpm[1]) / (2.0 * h))
        fd2 = ((wpp[0] - 2.0 * w0[0] + wpm[0]) / (h * h),
               (wpp[1] - 2.0 * w0[1] + wpm[1]) / (h * h))
        for a, f in ((wp0, fd1), (wpp0, fd2)):
            for k in (0, 1):
                denom = max(1.0, abs(f[k]))
                if abs(a[k] - f[k]) / denom > FD_TOL:
                    raise ValueError(
                        "FD self-check mismatch: pin_path d%d at "
                        "q=%r t=%r: analytic %.3e vs fd %.3e"
                        % (1 if f is fd1 else 2, q, t, a[k], f[k]))
        C = PLATE_CENTER
        g0, gp0, gpp0 = groove_from_path(w0, wp0, wpp0, t, C)
        wm, _, _ = pin_path(q, t - h)
        wp2, _, _ = pin_path(q, t + h)
        gm, _, _ = groove_from_path(wm, (0, 0), (0, 0), t - h, C)
        gp2, _, _ = groove_from_path(wp2, (0, 0), (0, 0), t + h, C)
        fd1g = ((gp2[0] - gm[0]) / (2.0 * h),
                (gp2[1] - gm[1]) / (2.0 * h))
        fd2g = ((gp2[0] - 2.0 * g0[0] + gm[0]) / (h * h),
                (gp2[1] - 2.0 * g0[1] + gm[1]) / (h * h))
        for a, f in ((gp0, fd1g), (gpp0, fd2g)):
            for k in (0, 1):
                denom = max(1.0, abs(f[k]))
                if abs(a[k] - f[k]) / denom > FD_TOL:
                    raise ValueError(
                        "FD self-check mismatch: groove d at "
                        "q=%r t=%r: analytic %.3e vs fd %.3e"
                        % (q, t, a[k], f[k]))
    return True


# ---------------------------------------------------------------------------
# S1 boundary: the recorded C1a evidence (carried, never re-litigated).
# ---------------------------------------------------------------------------

def fixed_pivot_evidence():
    """C1a: best-fit fixed pivot + rigid mount for the demand.

    Unknowns P=(px,py), m=(mx,my); pose i position = P + R(phi_i) m
    with phi_i in {0, 90, 180} deg -- linear in the unknowns. The
    exact solve of poses 1 and 3 gives P=(0,0.5), m=(-1.3,0); pose 2
    then misses by the full arm length. The least-squares residual
    over all three poses is the recorded infeasibility evidence.
    (Carried from the recorded study; never re-litigated.)
    """
    A = []
    b = []
    for d in DEMANDS:
        phi = math.radians(d["phi_deg"])
        r = rot(phi, (1.0, 0.0))
        r2 = rot(phi, (0.0, 1.0))
        A.append([1.0, 0.0, r[0], r[1]])
        b.append(d["x"])
        A.append([0.0, 1.0, r2[0], r2[1]])
        b.append(d["y"])
    M = [[sum(A[k][i] * A[k][j] for k in range(6)) for j in range(4)]
         for i in range(4)]
    rhs = [sum(A[k][i] * b[k] for k in range(6)) for i in range(4)]
    n = 4
    aug = [row[:] + [rhs[i]] for i, row in enumerate(M)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[piv][col]) < 1e-14:
            raise ValueError("singular normal system")
        aug[col], aug[piv] = aug[piv], aug[col]
        for r in range(col + 1, n):
            f = aug[r][col] / aug[col][col]
            for k in range(col, n + 1):
                aug[r][k] -= f * aug[col][k]
    sol = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = aug[i][n] - sum(aug[i][j] * sol[j] for j in range(i + 1, n))
        sol[i] = s / aug[i][i]
    px, py, mx, my = sol
    resid = 0.0
    worst = 0.0
    for d in DEMANDS:
        phi = math.radians(d["phi_deg"])
        r = rot(phi, (mx, my))
        err = math.hypot(px + r[0] - d["x"], py + r[1] - d["y"])
        resid += err * err
        worst = max(worst, err)
    return {
        "best_fit_pivot": [px, py],
        "best_fit_mount": [mx, my],
        "rms_residual_units": math.sqrt(resid / 3.0),
        "worst_pose_residual_units": worst,
        "exact_13_fit": {
            "pivot": [0.0, 0.5],
            "mount": [-1.3, 0.0],
            "pose2_residual_units": 1.3,
        },
    }


# ---------------------------------------------------------------------------
# Groove metrics over a path (one formula family, the recorded
# special cases: groove-pin, groove-roller). The driven point's
# world velocity IS the path velocity.
# ---------------------------------------------------------------------------

def groove_metrics_path(path_fn, C, step, gate_deg):
    """Per-groove metrics over the grid: curvature, closure, gate.

    path_fn(t) -> (w, wp, wpp). Pressure angle: the angle between
    the groove's world-frame normal and the driven point's world
    velocity (the recorded formula). Loaded carry arc 0 < t < 180;
    zero-velocity samples masked by the window fraction; dead-point
    bands (near extreme groove radius) excluded from the gate and
    recorded as data. Self-lock comparison and efficiency data are
    computed by the caller from alpha_gate.
    """
    ts = grid(step)
    samples = []
    max_speed = 0.0
    for t in ts:
        w, wp, _ = path_fn(t)
        max_speed = max(max_speed, math.hypot(wp[0], wp[1]))
    for t in ts:
        w, wp, wpp = path_fn(t)
        g, gp, gpp = groove_from_path(w, wp, wpp, t, C)
        speed = math.hypot(wp[0], wp[1])
        cross = gp[0] * gpp[1] - gp[1] * gpp[0]
        denom = (gp[0] ** 2 + gp[1] ** 2) ** 1.5
        if denom < 1e-18:
            raise ValueError("degenerate groove tangent at t=%r" % t)
        kappa = abs(cross) / denom
        r_curv = 1.0 / kappa if kappa > 0.0 else float("inf")
        if speed < EPS_GEOM:
            alpha = None
        else:
            gl = math.hypot(gp[0], gp[1])
            nx, ny = -gp[1] / gl, gp[0] / gl
            N = rot(math.radians(t), (nx, ny))
            cos_a = abs((N[0] * wp[0] + N[1] * wp[1]) /
                        (math.hypot(*N) * speed))
            cos_a = min(1.0, cos_a)
            alpha = math.degrees(math.acos(cos_a))
        samples.append({
            "t": t, "g": g, "gp": gp, "w": w, "wp": wp,
            "speed": speed, "r_curv": r_curv, "alpha": alpha,
            "gmag": math.hypot(g[0], g[1]),
            "n_world": None if alpha is None else
                       rot(math.radians(t), (-gp[1] / math.hypot(*gp),
                                            gp[0] / math.hypot(*gp))),
        })
    r_min = min(s["r_curv"] for s in samples)
    r_min_at = min(samples, key=lambda s: s["r_curv"])["t"]
    g_mag_max = max(s["gmag"] for s in samples)
    g_mag_min = min(s["gmag"] for s in samples)
    dead = [s for s in samples
            if abs(s["gmag"] - g_mag_max) < DEAD_POINT_BAND_UNITS
            or abs(s["gmag"] - g_mag_min) < DEAD_POINT_BAND_UNITS]
    dead_ts = sorted(set(round(s["t"], 2) for s in dead))
    gate_samples = [s for s in samples
                    if 0.0 < s["t"] < 180.0
                    and s["alpha"] is not None
                    and s["speed"] >= GATE_WINDOW_FRACTION * max_speed
                    and abs(s["gmag"] - g_mag_max) >=
                    DEAD_POINT_BAND_UNITS
                    and abs(s["gmag"] - g_mag_min) >=
                    DEAD_POINT_BAND_UNITS]
    if not gate_samples:
        raise ValueError("empty pressure-angle gate window")
    a_gate = max(s["alpha"] for s in gate_samples)
    a_gate_at = max(gate_samples, key=lambda s: s["alpha"])["t"]
    a_full = max(s["alpha"] for s in samples
                 if s["alpha"] is not None)
    a_full_at = max((s for s in samples if s["alpha"] is not None),
                    key=lambda s: s["alpha"])["t"]
    a_dead = max((s["alpha"] for s in dead if s["alpha"] is not None),
                 default=None)
    w_end = path_fn(360.0)
    g_end = groove_from_path(w_end[0], w_end[1], w_end[2], 360.0, C)
    closure = math.hypot(samples[0]["g"][0] - g_end[0][0],
                         samples[0]["g"][1] - g_end[0][1])
    return {
        "samples": samples, "r_min": r_min, "r_min_at": r_min_at,
        "alpha_gate": a_gate, "alpha_gate_at": a_gate_at,
        "alpha_full_cycle": a_full, "alpha_full_cycle_at": a_full_at,
        "alpha_dead_point": a_dead,
        "dead_point_count": len(dead), "dead_point_band_ts": dead_ts,
        "g_mag_max": g_mag_max, "g_mag_min": g_mag_min,
        "max_speed": max_speed, "closure": closure,
        "step": step,
    }


def efficiency_loss(mu, alpha_deg):
    """Efficiency as data: loss = mu * tan(alpha) (the ruling's
    own arithmetic). Reported, never gated."""
    return mu * math.tan(math.radians(alpha_deg))


# ---------------------------------------------------------------------------
# Class G1 machinery (the recorded study's construction, carried):
# two pins on the carrier riding two grooves in one plate.
# ---------------------------------------------------------------------------

def g1_groove_metrics(q, C, step, gate_deg):
    def path_fn(t):
        return pin_path(q, t)
    return groove_metrics_path(path_fn, C, step, gate_deg)


def constraint_row(q, t_deg, C):
    """Gradient of the pin-on-groove constraint w.r.t. (dx, dy, dphi).

    (Carried from the recorded study.)
    """
    g, gp, _ = groove_from_path(*pin_path(q, t_deg), t_deg, C)
    gl = math.hypot(gp[0], gp[1])
    if gl < EPS_GEOM:
        raise ValueError("zero groove tangent at t=%r" % t_deg)
    nx, ny = -gp[1] / gl, gp[0] / gl
    theta = math.radians(t_deg)
    _, _, phi, _, _, _, _ = pose_derivs(t_deg)
    e1 = rot(-theta, (1.0, 0.0))
    e2 = rot(-theta, (0.0, 1.0))
    er = rot(-theta, rot(phi + math.pi / 2.0, q))
    return [e1[0] * nx + e1[1] * ny,
            e2[0] * nx + e2[1] * ny,
            er[0] * nx + er[1] * ny]


def pair_map_ok(A):
    aa = [[sum(A[i][k] * A[j][k] for k in range(3)) for j in range(2)]
          for i in range(2)]
    det = aa[0][0] * aa[1][1] - aa[0][1] * aa[1][0]
    return abs(det) >= RANK_EPS


def min_norm_perturbation(A, delta):
    aa = [[sum(A[i][k] * A[j][k] for k in range(3)) for j in range(2)]
          for i in range(2)]
    det = aa[0][0] * aa[1][1] - aa[0][1] * aa[1][0]
    if abs(det) < RANK_EPS:
        raise ValueError("degenerate constraint pair")
    y = [(aa[1][1] * delta[0] - aa[0][1] * delta[1]) / det,
         (aa[0][0] * delta[1] - aa[1][0] * delta[0]) / det]
    return [sum(A[j][k] * y[j] for j in range(2)) for k in range(3)]


def worst_case_pose_error(A, bound):
    worst_pos = 0.0
    worst_ori = 0.0
    for s1 in (-1.0, 1.0):
        for s2 in (-1.0, 1.0):
            u = min_norm_perturbation(A, (s1 * bound, s2 * bound))
            worst_pos = max(worst_pos, math.hypot(u[0], u[1]))
            worst_ori = max(worst_ori, abs(math.degrees(u[2])))
    return worst_pos, worst_ori


def handoff_wc(q1, q2, C):
    """C3/S4 for class G1 at both handoff poses (carried convention).

    Rank deficiency at a handoff is a fail-closed outcome: the row
    is recorded with "rank_deficient": True and no finite numbers.
    """
    out = []
    rank_fail = False
    for label, t in (("handoff_1_pick", 0.0),
                     ("handoff_2_place", 180.0)):
        A = [constraint_row(q1, t, C), constraint_row(q2, t, C)]
        if not pair_map_ok(A):
            rank_fail = True
            out.append({
                "handoff": label, "channel": "rank_check",
                "rank_deficient": True,
                "reason": "two-groove constraint pair parallel at "
                          "the handoff (structural dead point); the "
                          "WC-L map cannot bound the pose -- "
                          "fail-closed",
            })
            continue
        pos_bl, ori_bl = worst_case_pose_error(A, CLEARANCE_UNITS)
        pos_pr, ori_pr = worst_case_pose_error(A, PROFILE_UNITS)
        out.append({
            "handoff": label, "channel": "clearance_backlash",
            "rank_deficient": False,
            "pos_units": pos_bl, "ori_deg": ori_bl,
        })
        out.append({
            "handoff": label, "channel": "profile_class",
            "rank_deficient": False,
            "pos_units": pos_pr, "ori_deg": ori_pr,
        })
        out.append({
            "handoff": label, "channel": "combined_wc_l",
            "rank_deficient": False,
            "pos_units": pos_bl + pos_pr,
            "ori_deg": ori_bl + ori_pr,
        })
    return out, rank_fail


# ---------------------------------------------------------------------------
# Class C1 machinery: the cam+lever pivoted-cradle composition.
# ---------------------------------------------------------------------------

def c1_carriage_pin(t_deg):
    """Channel-X pin: fixed in the carriage frame (translation only)."""
    x, y, _, xp, xpp, _, _ = pose_derivs(t_deg)
    ox, oy = CARRIAGE_PIN_OFFSET
    w = (x + ox, y + oy)
    return w, (xp, 0.0), (xpp, 0.0)


def c1_lever_kin(q_pin, Pl, A, delta_deg, t_deg):
    """Lever angle psi(t) + derivatives; roller path + derivatives.

    The lever is frame-pivoted at Pl; its radial slot engages the
    cradle pin, so psi is the direction from Pl to the pin (the -06
    slotted-lever connection); the roller rides the lever's short
    arm at the fixed inter-arm angle Delta (the -06 parametrization).
    """
    w, wp, wpp = pin_path(q_pin, t_deg)
    dx, dy = w[0] - Pl[0], w[1] - Pl[1]
    dxp, dyp = wp[0], wp[1]
    dxpp, dypp = wpp[0], wpp[1]
    r2 = dx * dx + dy * dy
    if r2 < LEVER_PIN_FLOOR * LEVER_PIN_FLOOR:
        raise ValueError("cradle pin at the lever pivot (t=%r)"
                         % t_deg)
    psi = math.atan2(dy, dx)
    N = dx * dyp - dy * dxp
    Np = dx * dypp - dy * dxpp
    D = r2
    Dp = 2.0 * (dx * dxp + dy * dyp)
    psip = N / D
    psipp = (Np * D - N * Dp) / (D * D)
    ang = psi + math.radians(delta_deg)
    c, s = math.cos(ang), math.sin(ang)
    rw = (Pl[0] + A * c, Pl[1] + A * s)
    rwp = (-A * s * psip, A * c * psip)
    rwpp = (-A * c * psip * psip - A * s * psipp,
            -A * s * psip * psip + A * c * psipp)
    return {
        "psi": psi, "psip": psip, "psipp": psipp,
        "pin_w": w, "pin_wp": wp, "pin_wpp": wpp,
        "r_pin": math.sqrt(r2),
        "roller_w": rw, "roller_wp": rwp, "roller_wpp": rwpp,
    }


def c1_roller_path_fn(q_pin, Pl, A, delta_deg):
    def path_fn(t):
        k = c1_lever_kin(q_pin, Pl, A, delta_deg, t)
        return (k["roller_w"], k["roller_wp"], k["roller_wpp"])
    return path_fn


def c1_slot_metrics(q_pin, Pl, t_deg):
    """Slot-pair pressure angle at the cradle pin.

    The slot wall's force on the pin is normal to the slot axis;
    the pressure angle is the angle between that normal and the
    pin's world velocity. Dead sample: the pin velocity has no
    transverse component (motion purely along the slot) -- no
    transmission; recorded as data, never gated.
    """
    w, wp, _ = pin_path(q_pin, t_deg)
    dx, dy = w[0] - Pl[0], w[1] - Pl[1]
    r = math.hypot(dx, dy)
    if r < LEVER_PIN_FLOOR:
        raise ValueError("cradle pin at the lever pivot (t=%r)"
                         % t_deg)
    u = (dx / r, dy / r)
    n = (-u[1], u[0])
    speed = math.hypot(wp[0], wp[1])
    transverse = abs(n[0] * wp[0] + n[1] * wp[1])
    if speed < EPS_GEOM or transverse < GATE_WINDOW_FRACTION * speed:
        return {"t": t_deg, "beta_deg": None, "r": r, "dead": True}
    cos_b = min(1.0, transverse / speed)
    return {"t": t_deg, "beta_deg": math.degrees(math.acos(cos_b)),
            "r": r, "dead": False}


def c1_lever_wind_ok(q_pin, Pl, step):
    """The -06 winding analog: the lever must OSCILLATE (its
    direction may not complete a full turn over the cycle).

    psi is the direction from Pl to the cradle pin -- independent
    of A and Delta -- so the placeholder values below are exact.
    """
    ts = grid(step)
    psi_prev = None
    unwrapped = 0.0
    lo = None
    hi = None
    for t in ts:
        k = c1_lever_kin(q_pin, Pl, 0.05, 0.0, t)
        psi = k["psi"]
        if psi_prev is None:
            unwrapped = psi
            lo = hi = psi
        else:
            d = psi - psi_prev
            while d > math.pi:
                d -= 2.0 * math.pi
            while d < -math.pi:
                d += 2.0 * math.pi
            unwrapped += d
            lo = min(lo, unwrapped)
            hi = max(hi, unwrapped)
        psi_prev = psi
    return (hi - lo) < math.pi


def c1_handoff_map(q_pin, Pl, A, delta_deg, t_deg):
    """S4 for class C1: the handoff linear error map.

    Unknowns (dx_c, dphi, dpsi); error sources per channel:
      dX: the carriage groove shifted along its normal,
      dP: the lever groove shifted along its normal,
      dS: the slot transverse clearance.
    Linear system at the handoff configuration (carriage fixed at
    the settle event; the recorded quasi-static convention):
      n_car_x * dx_c = dX
      A * (n_lev . perp_psi) * dpsi = dP
      dphi = (dS + r*dpsi - (n_slot . e_x)*dx_c) / (n_slot . v_phi)
    Pose errors: position = |dx_c| (the identity mount: the
    centroid coincides with the cradle pivot, which follows the
    carriage); orientation = |dphi|. Rank deficiency fails closed
    with the reason recorded; dead points never emit numbers.
    """
    k = c1_lever_kin(q_pin, Pl, A, delta_deg, t_deg)
    w = k["pin_w"]
    dx, dy = w[0] - Pl[0], w[1] - Pl[1]
    r = k["r_pin"]
    u = (dx / r, dy / r)
    n_slot = (-u[1], u[0])
    _, _, phi, _, _, _, _ = pose_derivs(t_deg)
    v_phi = rot(phi + math.pi / 2.0, q_pin)
    # carriage groove normal (world) at t
    wc, wcp, wcpp = c1_carriage_pin(t_deg)
    gc, gcp, _ = groove_from_path(wc, wcp, wcpp, t_deg, PLATE_CENTER)
    gl = math.hypot(gcp[0], gcp[1])
    if gl < EPS_GEOM:
        raise ValueError("zero carriage-groove tangent at t=%r" % t_deg)
    nx, ny = -gcp[1] / gl, gcp[0] / gl
    n_car = rot(math.radians(t_deg), (nx, ny))
    # lever groove normal (world) at t
    gl2 = groove_from_path(k["roller_w"], k["roller_wp"],
                           k["roller_wpp"], t_deg, PLATE_CENTER)
    gl2p = gl2[1]
    gl2l = math.hypot(gl2p[0], gl2p[1])
    if gl2l < EPS_GEOM:
        raise ValueError("zero lever-groove tangent at t=%r" % t_deg)
    nx2, ny2 = -gl2p[1] / gl2l, gl2p[0] / gl2l
    n_lev = rot(math.radians(t_deg), (nx2, ny2))
    # per-unit-dpsi roller velocity direction (magnitude A)
    ang = k["psi"] + math.radians(delta_deg)
    perp = (-math.sin(ang), math.cos(ang))
    a_lev = A * (n_lev[0] * perp[0] + n_lev[1] * perp[1])
    n_car_x = n_car[0]
    n_slot_vphi = n_slot[0] * v_phi[0] + n_slot[1] * v_phi[1]
    n_slot_ex = n_slot[0]
    dpsi_dxc = -dy / (r * r)
    if abs(a_lev) < 1e-9:
        return {"rank_deficient": True,
                "reason": "lever groove normal perpendicular to the "
                          "roller arm's motion at the handoff (no "
                          "leverage); fail-closed"}
    if abs(n_car_x) < 1e-9:
        return {"rank_deficient": True,
                "reason": "carriage groove normal perpendicular to "
                          "the carriage motion at the handoff; "
                          "fail-closed"}
    if abs(n_slot_vphi) < 1e-9:
        return {"rank_deficient": True,
                "reason": "slot direction insensitive to cradle "
                          "rotation at the handoff (structural dead "
                          "point); fail-closed"}
    # per-channel gains (pose error per unit channel error)
    g_car_pos = abs(1.0 / n_car_x)
    g_car_ori = abs((n_slot_ex / n_car_x) / n_slot_vphi) * \
        (180.0 / math.pi)
    g_lev_pos = 0.0
    g_lev_ori = abs(r / (a_lev * n_slot_vphi)) * (180.0 / math.pi)
    g_slot_pos = 0.0
    g_slot_ori = abs(1.0 / n_slot_vphi) * (180.0 / math.pi)
    return {
        "rank_deficient": False,
        "g_carriage_pos": g_car_pos,
        "g_carriage_ori": g_car_ori,
        "g_lever_pos": g_lev_pos,
        "g_lever_ori": g_lev_ori,
        "g_slot_pos": g_slot_pos,
        "g_slot_ori": g_slot_ori,
        "dpsi_dxc": dpsi_dxc,
    }


def c1_handoff_rows(q_pin, Pl, A, delta_deg):
    """S4 rows for class C1 at both handoffs, channels separate."""
    out = []
    for label, t in (("handoff_1_pick", 0.0),
                     ("handoff_2_place", 180.0)):
        m = c1_handoff_map(q_pin, Pl, A, delta_deg, t)
        if m.get("rank_deficient"):
            out.append({"handoff": label, "channel": "rank_check",
                        "rank_deficient": True,
                        "reason": m["reason"]})
            continue
        car_bl_p = m["g_carriage_pos"] * CLEARANCE_UNITS
        car_bl_o = m["g_carriage_ori"] * CLEARANCE_UNITS
        car_pr_p = m["g_carriage_pos"] * PROFILE_UNITS
        car_pr_o = m["g_carriage_ori"] * PROFILE_UNITS
        lev_bl_o = m["g_lever_ori"] * CLEARANCE_UNITS
        lev_pr_o = m["g_lever_ori"] * PROFILE_UNITS
        slot_o = m["g_slot_ori"] * SLOT_CLEARANCE_UNITS
        out.append({"handoff": label,
                    "channel": "carriage_clearance_backlash",
                    "rank_deficient": False,
                    "pos_units": car_bl_p, "ori_deg": car_bl_o})
        out.append({"handoff": label, "channel": "carriage_profile",
                    "rank_deficient": False,
                    "pos_units": car_pr_p, "ori_deg": car_pr_o})
        out.append({"handoff": label,
                    "channel": "lever_groove_clearance_backlash",
                    "rank_deficient": False,
                    "pos_units": 0.0, "ori_deg": lev_bl_o})
        out.append({"handoff": label, "channel": "lever_groove_profile",
                    "rank_deficient": False,
                    "pos_units": 0.0, "ori_deg": lev_pr_o})
        out.append({"handoff": label, "channel": "slot_clearance",
                    "rank_deficient": False,
                    "pos_units": 0.0, "ori_deg": slot_o})
        out.append({"handoff": label, "channel": "combined_wc_l",
                    "rank_deficient": False,
                    "pos_units": car_bl_p + car_pr_p,
                    "ori_deg": lev_bl_o + lev_pr_o + slot_o})
    return out


# ---------------------------------------------------------------------------
# Part envelope (carried): the exact in-plane rectangle at pose samples.
# ---------------------------------------------------------------------------

def part_corners(t_deg):
    x, y, phi, _, _, _, _ = pose_derivs(t_deg)
    pts = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            c = (sx * PART_HALF_LONG, sy * PART_HALF_SHORT)
            r = rot(phi, c)
            pts.append((x + r[0], y + r[1]))
    return pts


def part_sweep_bbox():
    xs = []
    ys = []
    for t in grid(ENVELOPE_STEP_DEG):
        for p in part_corners(t):
            xs.append(p[0])
            ys.append(p[1])
    return min(xs), max(xs), min(ys), max(ys)


# ---------------------------------------------------------------------------
# Corpus emission (the recorded emitter conventions carried; schema
# 1.2 additive with a changelog row; fail-closed validation).
# ---------------------------------------------------------------------------

UNITS_BLOCK = {
    "position": "normalized task-layer units (1 unit = 100 mm)",
    "angle": "deg",
    "normalization_basis": "1 unit = 100 mm, task-layer (cases "
                           "A/B/C)",
}

KNOWN_KINDS = {
    "demand", "search_class_declaration", "architecture_evidence",
    "design_parameter", "gate", "groove_summary", "groove_sample",
    "tolerance", "sensitivity", "envelope", "scorecard_verdict",
    "class_verdict", "recorded_design_reference", "reciprocity",
    "changelog",
}


def _all_finite(x):
    if isinstance(x, float):
        return math.isfinite(x)
    if isinstance(x, dict):
        return all(_all_finite(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return all(_all_finite(v) for v in x)
    return True


def validate_row(row, source_commit):
    if not isinstance(row, dict) or "kind" not in row:
        raise ValueError("corpus row without kind")
    if row["kind"] not in KNOWN_KINDS:
        raise ValueError("unknown row kind: %r" % row["kind"])
    if row.get("units") != UNITS_BLOCK:
        raise ValueError("row without the pinned units block")
    if row.get("corpus_schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("row without the pinned corpus schema "
                         "version")
    if row.get("major") != CORPUS_MAJOR:
        raise ValueError("row without the pinned corpus major "
                         "version")
    if row.get("provenance", {}).get("source_commit") != source_commit:
        raise ValueError("row without pinned provenance source "
                         "commit")
    if not _all_finite(row):
        raise ValueError("non-finite number in corpus row")
    if not all(ord(ch) < 128
               for ch in json.dumps(row, sort_keys=True,
                                    ensure_ascii=False)):
        raise ValueError("non-ASCII corpus row")


def base_row(kind, source_commit, **fields):
    row = {
        "kind": kind,
        "job": JOB_ID,
        "corpus_schema_version": CORPUS_SCHEMA_VERSION,
        "major": CORPUS_MAJOR,
        "units": UNITS_BLOCK,
        "provenance": {
            "source_commit": source_commit,
            "design": fields.pop("_design",
                                 "cam line re-stage Stage 1 "
                                 "instrument"),
        },
    }
    row.update(fields)
    return row


def write_corpus(rows, source_commit):
    for r in rows:
        validate_row(r, source_commit)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    jsonl_path = os.path.join(OUTPUT_DIR, CORPUS_STEM + ".jsonl")
    csv_path = os.path.join(OUTPUT_DIR, CORPUS_STEM + ".csv")
    lines = [json.dumps(r, sort_keys=True) for r in rows]
    with open(jsonl_path, "w", encoding="ascii") as fh:
        fh.write("\n".join(lines) + "\n")
    columns = set()
    flat_rows = []
    for r in rows:
        flat = {}
        for k in sorted(r):
            v = r[k]
            if isinstance(v, (dict, list)):
                flat[k] = json.dumps(v, sort_keys=True)
            else:
                flat[k] = v
        flat_rows.append(flat)
        columns.update(flat.keys())
    cols = sorted(columns)
    with open(csv_path, "w", encoding="ascii") as fh:
        fh.write(",".join(cols) + "\n")
        for flat in flat_rows:
            cells = []
            for c in cols:
                s = str(flat.get(c, ""))
                if "," in s or '"' in s:
                    s = '"' + s.replace('"', '""') + '"'
                cells.append(s)
            fh.write(",".join(cells) + "\n")
    h1 = hashlib.sha256(open(jsonl_path, "rb").read()).hexdigest()
    h2 = hashlib.sha256(open(csv_path, "rb").read()).hexdigest()
    return jsonl_path, csv_path, h1, h2


# ---------------------------------------------------------------------------
# Computation.
# ---------------------------------------------------------------------------

def fmt_alpha(a):
    return "n/a" if a is None else "%.3f" % a


def pose_witness():
    """S1 witness: the three demand poses exact at 0/90/180 deg."""
    errs = []
    for d, t in zip(DEMANDS, (0.0, 90.0, 180.0)):
        x, y, phi = pose_at(t)
        errs.append(max(abs(x - d["x"]), abs(y - d["y"]),
                        abs(math.degrees(phi) - d["phi_deg"])))
    return max(errs)


def evaluate_g1_candidate(d, cy, gate, step):
    """Class G1 candidate: metrics + WC-L, per the recorded pick rule."""
    q1, q2 = (d, 0.0), (-d, 0.0)
    C = (0.0, cy)
    try:
        m1 = g1_groove_metrics(q1, C, step, gate["gate_binding_deg"])
        m2 = g1_groove_metrics(q2, C, step, gate["gate_binding_deg"])
    except ValueError as e:
        return {"failed_closed": True, "reason": str(e)}
    a_g1 = max(m1["alpha_gate"], m2["alpha_gate"])
    min_rad = min(m1["r_min"], m2["r_min"])
    curv_pass = min_rad >= CURVATURE_FACTOR * PIN_RADIUS
    tol_rows, rank_fail = handoff_wc(q1, q2, C)
    tol_pass = (not rank_fail) and all(
        r.get("pos_units", 0.0) <= TOL_POS_UNITS and
        r.get("ori_deg", 0.0) <= TOL_ORI_DEG
        for r in tol_rows if r.get("channel") == "combined_wc_l")
    gate_pass = a_g1 <= gate["gate_binding_deg"]
    return {
        "failed_closed": False, "d": d, "C_y": cy,
        "a_g1": a_g1, "min_rad": min_rad,
        "closure": max(m1["closure"], m2["closure"]),
        "dead_1": m1["dead_point_count"], "dead_2": m2["dead_point_count"],
        "alpha_dead": max((x for x in (m1["alpha_dead_point"],
                        m2["alpha_dead_point"]) if x is not None),
                        default=None),
        "gate_pass": gate_pass, "curv_pass": curv_pass,
        "tol_pass": tol_pass, "tol_rows": tol_rows,
        "all_pass": gate_pass and curv_pass and tol_pass,
        "g_mag_max": max(m1["g_mag_max"], m2["g_mag_max"]),
        "metrics": (m1, m2),
    }


def evaluate_c1_candidate(Px, Py, A, delta, rp, beta, gate, step):
    """Class C1 candidate: both groove channels + the slot pair."""
    Pl = (Px, Py)
    q_pin = (rp * math.cos(math.radians(beta)),
             rp * math.sin(math.radians(beta)))
    try:
        if not c1_lever_wind_ok(q_pin, Pl, max(step, 5.0)):
            return {"failed_closed": True,
                    "reason": "lever winding: the lever direction "
                              "completes a full turn (not an "
                              "oscillation)"}
        # pin-floor check over the grid
        for t in grid(max(step, 5.0)):
            w, _, _ = pin_path(q_pin, t)
            if math.hypot(w[0] - Pl[0], w[1] - Pl[1]) < \
                    LEVER_PIN_FLOOR:
                return {"failed_closed": True,
                        "reason": "cradle-pin path enters the lever "
                                  "pivot floor (%.2f units)"
                                  % LEVER_PIN_FLOOR}
        m_car = groove_metrics_path(c1_carriage_pin, PLATE_CENTER,
                                    step, gate["gate_binding_deg"])
        roll_fn = c1_roller_path_fn(q_pin, Pl, A, delta)
        m_lev = groove_metrics_path(roll_fn, PLATE_CENTER, step,
                                    gate["gate_binding_deg"])
        slot_rows = [c1_slot_metrics(q_pin, Pl, t)
                     for t in grid(step)]
        slot_live = [s for s in slot_rows
                     if (not s["dead"]) and 0.0 < s["t"] < 180.0]
        if not slot_live:
            return {"failed_closed": True,
                    "reason": "empty slot gate window"}
        beta_max = max(s["beta_deg"] for s in slot_live)
    except ValueError as e:
        return {"failed_closed": True, "reason": str(e)}
    a_worst = max(m_car["alpha_gate"], m_lev["alpha_gate"],
                  beta_max)
    r_floor_pin = CURVATURE_FACTOR * PIN_RADIUS
    r_floor_roll = CURVATURE_FACTOR * ROLLER_RADIUS
    curv_pass = (m_car["r_min"] >= r_floor_pin and
                 m_lev["r_min"] >= r_floor_roll)
    tol_rows = c1_handoff_rows(q_pin, Pl, A, delta)
    rank_fail = any(r.get("rank_deficient") for r in tol_rows)
    tol_pass = (not rank_fail) and all(
        r.get("pos_units", 0.0) <= TOL_POS_UNITS and
        r.get("ori_deg", 0.0) <= TOL_ORI_DEG
        for r in tol_rows if r.get("channel") == "combined_wc_l")
    gate_pass = a_worst <= gate["gate_binding_deg"]
    r_pin_lo = min(s["r"] for s in slot_rows)
    r_pin_hi = max(s["r"] for s in slot_rows)
    return {
        "failed_closed": False, "Px": Px, "Py": Py, "A": A,
        "delta": delta, "r_p": rp, "beta": beta,
        "a_car": m_car["alpha_gate"], "a_lev": m_lev["alpha_gate"],
        "beta_slot": beta_max, "a_worst": a_worst,
        "min_rad_car": m_car["r_min"], "min_rad_lev": m_lev["r_min"],
        "closure": max(m_car["closure"], m_lev["closure"]),
        "dead_car": m_car["dead_point_count"],
        "dead_lev": m_lev["dead_point_count"],
        "dead_slot": sum(1 for s in slot_rows if s["dead"]),
        "r_pin_range": [r_pin_lo, r_pin_hi],
        "gate_pass": gate_pass, "curv_pass": curv_pass,
        "tol_pass": tol_pass, "tol_rows": tol_rows,
        "all_pass": gate_pass and curv_pass and tol_pass,
        "g_mag_max_car": m_car["g_mag_max"],
        "g_mag_max_lev": m_lev["g_mag_max"],
    }


def compute(source_commit):
    rows = []
    report = []
    R = report.append

    gate = gate_constants()
    fd_check()

    R("flip-station-cam-restage-01 -- the cam line re-stage Stage 1")
    R("deterministic design instrument per the -05/-06 pattern;")
    R("no engine, no search; the re-derived gate CONSUMED, never")
    R("re-derived")
    R("python: %s" % sys.version.split()[0])
    R("source commit: %s" % source_commit)
    R("")
    R("DEMAND (frozen brief, carried read-only): three poses,")
    R("  tolerances 1.5 mm / 1.5 deg at the handoffs")
    R("  (-1.3, 0.5) @ 0 deg | (0, 0.5) @ 90 deg | (1.3, 0.5) @"
      " 180 deg")
    for i, d in enumerate(DEMANDS, 1):
        rows.append(base_row("demand", source_commit, phase=i,
                             x=d["x"], y=d["y"],
                             phi_deg=d["phi_deg"]))

    # -- the re-derived gate, printed with its arithmetic ----------
    R("")
    R("[S2 GATE] the re-derived class gate (the ruling's Field 8")
    R("  row, consumed): pressure angle <= %.6f deg (mu %.2f," %
      (gate["gate_binding_deg"], gate["mu_binding"]))
    R("  binding) / <= %.6f deg (mu %.2f); self-lock %.6f deg"
      % (gate["gate_loose_deg"], gate["mu_loose"],
         gate["selflock_binding_deg"]))
    R("  (mu %.2f) / %.6f deg (mu %.2f), reported alongside;"
      % (gate["mu_binding"], gate["selflock_loose_deg"],
         gate["mu_loose"]))
    R("  efficiency as data (loss = mu*tan(alpha); the gate IS")
    R("  the 50 percent loss boundary: mu*tan(gate) = 1/SF ="
      " %.3f)" % (1.0 / SF))
    R("  gate constant check: PASS (re-computed against the frozen")
    R("  six-digit values, fail-closed)")
    rows.append(base_row(
        "gate", source_commit, gate="re_derived_class_gate",
        gate_binding_deg=gate["gate_binding_deg"],
        gate_loose_deg=gate["gate_loose_deg"],
        selflock_binding_deg=gate["selflock_binding_deg"],
        selflock_loose_deg=gate["selflock_loose_deg"],
        sf=SF, mu_binding=gate["mu_binding"],
        mu_loose=gate["mu_loose"],
        loss_at_gate=0.5, checked_against_frozen=True))

    # -- the declared search classes (BEFORE any synthesis) ---------
    classes = [
        {"class": "F0", "name": "fixed-pivot rigid-mount",
         "lineage": "the recorded boundary class "
                    "(jobs/flip-station-capability-01)",
         "expectation": "FAILS S1 by the recorded C1a arithmetic, "
                        "never re-litigated"},
        {"class": "G1", "name": "dual-groove plate-cam carrier",
         "lineage": "jobs/flip-station-capability-01; the case-B "
                    "-05/-06 exact construction carried",
         "expectation": "re-graded under the re-derived gate; the "
                        "recorded chosen design re-graded as its "
                        "own reference row"},
        {"class": "C1", "name": "cam+lever pivoted-cradle "
                                "composition",
         "lineage": "jobs/dualcam-lever-transfer-06 (the case-B "
                    "cam+lever class: a general pivoted lever)",
         "expectation": "the declared scan graded under the "
                        "re-derived gate"},
    ]
    R("")
    R("[CLASSES] DECLARED SEARCH CLASSES (frozen BEFORE any")
    R("  synthesis runs; never re-drawn after a run):")
    for c in classes:
        R("  %s %s" % (c["class"], c["name"]))
        R("    lineage: %s" % c["lineage"])
        R("    expectation: %s" % c["expectation"])
        rows.append(base_row("search_class_declaration",
                              source_commit, **c))

    # -- S1 boundary: class F0 --------------------------------------
    ev = fixed_pivot_evidence()
    R("")
    R("[F0] FIXED-PIVOT RIGID-MOUNT CLASS (the recorded boundary):")
    R("  best-fit pivot (%.6f, %.6f), mount (%.6f, %.6f)"
      % (ev["best_fit_pivot"][0], ev["best_fit_pivot"][1],
         ev["best_fit_mount"][0], ev["best_fit_mount"][1]))
    R("  least-squares worst pose residual %.6f units (%.2f mm) >"
      % (ev["worst_pose_residual_units"],
         ev["worst_pose_residual_units"] * 100.0))
    R("  the %.3f mm tolerance -- the three demand centroid points"
      % (TOL_POS_UNITS * 100.0))
    R("  (-1.3, 0.5), (0, 0.5), (1.3, 0.5) are colinear and")
    R("  distinct, and no fixed-pivot circle passes through three")
    R("  colinear points (the recorded arithmetic, never")
    R("  re-litigated). S1 verdict: FAIL (infeasibility evidenced)")
    rows.append(base_row("architecture_evidence", source_commit,
                         evidence="fixed_pivot_class_pose_infeasible",
                         best_fit_pivot=ev["best_fit_pivot"],
                         best_fit_mount=ev["best_fit_mount"],
                         rms_residual_units=ev["rms_residual_units"],
                         worst_pose_residual_units=ev[
                             "worst_pose_residual_units"],
                         exact_13_fit=ev["exact_13_fit"],
                         _design="class F0"))

    wit_err = pose_witness()
    R("")
    R("[S1] POSE WITNESS (shared program, both architectures):")
    R("  the three demand poses exact by construction at 0 / 90 /")
    R("  180 deg; witness max error %.3e (< 1e-12 demanded)" %
      wit_err)
    if wit_err >= 1e-12:
        raise ValueError("pose witness failed: %.3e" % wit_err)
    rows.append(base_row("scorecard_verdict", source_commit,
                         row="S1_pose_witness",
                         witness_error=wit_err,
                         verdict="PASS", _design="shared"))

    # -- class G1 ---------------------------------------------------
    R("")
    R("[G1] DUAL-GROOVE PLATE-CAM CARRIER (the recorded class,")
    R("  re-graded under the re-derived gate; frozen sweep d x")
    R("  C_y, pick rule carried: among tolerance+curvature-passing")
    R("  designs the smallest gate angle; tie-break larger d, then")
    R("  lower C_y; if none passes, smallest anyway -- the")
    R("  wide-fail is read on the scorecard, not on the pick):")
    R("  d / C_y          a_gate    min_rad   gate curv tol")
    g1_rows = []
    for d in SWEEP_D:
        for cy in SWEEP_CY:
            cand = evaluate_g1_candidate(d, cy, gate, FINE_STEP_DEG)
            g1_rows.append(cand)
            if cand["failed_closed"]:
                R("  d=%.1f C_y=%.2f  FAILED CLOSED: %s"
                  % (d, cy, cand["reason"]))
                continue
            R("  d=%.1f C_y=%.2f  %7.3f  %8.4f  %-4s %-4s %-4s" %
              (d, cy, cand["a_g1"], cand["min_rad"],
               "PASS" if cand["gate_pass"] else "FAIL",
               "PASS" if cand["curv_pass"] else "FAIL",
               "PASS" if cand["tol_pass"] else "FAIL"))
            rows.append(base_row(
                "design_parameter", source_commit,
                design_class="G1", d=d, C_y=cy,
                a_gate_deg=cand["a_g1"],
                min_rad_units=cand["min_rad"],
                closure_residual=cand["closure"],
                dead_point_samples=[cand["dead_1"],
                                    cand["dead_2"]],
                gate_pass=cand["gate_pass"],
                curv_pass=cand["curv_pass"],
                tol_pass=cand["tol_pass"],
                efficiency_loss_binding=efficiency_loss(
                    gate["mu_binding"], cand["a_g1"]),
                efficiency_loss_loose=efficiency_loss(
                    gate["mu_loose"], cand["a_g1"]),
                selflock_exceeded=bool(
                    cand["a_g1"] > gate["selflock_binding_deg"]),
                _design="class G1"))
    g1_live = [c for c in g1_rows if not c["failed_closed"]]
    g1_pass = [c for c in g1_live if c["all_pass"]]
    g1_pick = None
    if g1_pass:
        g1_pick = sorted(g1_pass, key=lambda c: (c["a_g1"], -c["d"],
                                                 c["C_y"]))[0]
    elif g1_live:
        g1_pick = sorted(g1_live,
                         key=lambda c: (c["a_g1"], -c["d"],
                                        c["C_y"]))[0]
    if g1_pick is None:
        R("  G1 verdict: FAILED CLOSED at every sweep candidate")
        rows.append(base_row("class_verdict", source_commit,
                             design_class="G1",
                             verdict="FAILED_CLOSED",
                             _design="class G1"))
    else:
        R("  chosen (frozen pick rule): d=%.1f C_y=%.2f, a_gate"
          " %.3f deg" % (g1_pick["d"], g1_pick["C_y"],
                         g1_pick["a_g1"]))
        R("  G1 verdict: %s" %
          ("PASS (all rows)" if g1_pick["all_pass"] else
           "WIDE-FAIL (the honest all-fail is the outcome; the"
           " gate is never relaxed)"))
        rows.append(base_row("class_verdict", source_commit,
                             design_class="G1",
                             pick=g1_pick["a_g1"],
                             pick_d=g1_pick["d"],
                             pick_C_y=g1_pick["C_y"],
                             verdict="PASS" if g1_pick["all_pass"]
                             else "WIDE-FAIL", _design="class G1"))
    # the recorded chosen design, re-graded as its own reference row
    ref = evaluate_g1_candidate(RECORDED_DESIGN["d"],
                               RECORDED_DESIGN["C_y"], gate,
                               FINE_STEP_DEG)
    if ref["failed_closed"]:
        R("  recorded design reference row: FAILED CLOSED: %s"
          % ref["reason"])
    else:
        R("  recorded design reference (d=0.2, C_y=0.0, its")
        R("  recorded outcome keeping its meaning): a_gate %.3f deg"
          % ref["a_g1"])
        R("  vs the re-derived gate %.6f deg -- %s" %
          (gate["gate_binding_deg"],
           "PASS" if ref["gate_pass"] else "FAIL (recorded as"
           " data, never re-litigated)"))
        rows.append(base_row(
            "recorded_design_reference", source_commit,
            design_class="G1", d=RECORDED_DESIGN["d"],
            C_y=RECORDED_DESIGN["C_y"],
            a_gate_deg=ref["a_g1"],
            gate_pass=ref["gate_pass"],
            note="the recorded study's chosen design re-graded "
                 "under the re-derived gate; its recorded "
                 "outcome keeps its meaning",
            _design="class G1"))
    if g1_pick is not None:
        for r_ in g1_pick["tol_rows"]:
            rows.append(base_row("tolerance", source_commit,
                                 design_class="G1",
                                 pick_d=g1_pick["d"],
                                 pick_C_y=g1_pick["C_y"],
                                 handoff=r_["handoff"],
                                 channel=r_["channel"],
                                 rank_deficient=r_.get(
                                     "rank_deficient", False),
                                 pos_units=r_.get("pos_units"),
                                 ori_deg=r_.get("ori_deg"),
                                 reason=r_.get("reason"),
                                 _design="class G1"))
        for r_ in g1_pick["tol_rows"]:
            if r_.get("channel") == "combined_wc_l":
                R("  WC-L at the handoffs (combined): pos %.4f mm /"
                  " ori %.4f deg vs 1.5 mm / 1.5 deg -- %s" %
                  (r_["pos_units"] * 100.0, r_["ori_deg"],
                   "PASS" if r_["pos_units"] <= TOL_POS_UNITS and
                   r_["ori_deg"] <= TOL_ORI_DEG else "FAIL"))
                R("  (channels separate in the tolerance rows; the")
                R("  drive-reversal backlash channel priced at both")
                R("  handoffs)")

    # -- class C1 ---------------------------------------------------
    R("")
    R("[C1] CAM+LEVER PIVOTED-CRADLE COMPOSITION (the -06 class;")
    R("  declared scan frozen before synthesis; coarse %.1f deg"
      % SCAN_STEP_DEG)
    R("  scan, finalists audited on the %.2f deg grid; pick rule:"
      % FINE_STEP_DEG)
    R("  among all-rows-passing candidates the smallest worst")
    R("  pressure angle at the binding gate; tie-break larger")
    R("  r_p, then smaller |Delta|, then lower Py, then grid")
    R("  order; if none passes, the best is recorded with the")
    R("  wide-fail verdict -- the gate is never relaxed)")
    c1_coarse = []
    for Px in SCAN_PX:
        for Py in SCAN_PY:
            for A in SCAN_A:
                for delta in SCAN_DELTA:
                    for rp in SCAN_RP:
                        for beta in SCAN_BETA:
                            cand = evaluate_c1_candidate(
                                Px, Py, A, delta, rp, beta, gate,
                                SCAN_STEP_DEG)
                            cand["_key"] = (Px, Py, A, delta, rp,
                                            beta)
                            c1_coarse.append(cand)
    c1_live = [c for c in c1_coarse if not c["failed_closed"]]
    c1_fail = [c for c in c1_coarse if c["failed_closed"]]
    R("  coarse scan: %d candidates, %d graded, %d failed closed"
      % (len(c1_coarse), len(c1_live), len(c1_fail)))
    for c in c1_fail[:10]:
        R("    failed closed: Px=%.1f Py=%.1f A=%.2f Delta=%.0f"
          " r_p=%.2f beta=%.0f: %s" %
          (c["_key"][0], c["_key"][1], c["_key"][2], c["_key"][3],
           c["_key"][4], c["_key"][5], c["reason"]))
    if len(c1_fail) > 10:
        R("    ... %d more failed-closed rows in the corpus"
          % (len(c1_fail) - 10))
    for c in c1_fail:
        rows.append(base_row(
            "design_parameter", source_commit, design_class="C1",
            Px=c["_key"][0], Py=c["_key"][1], A=c["_key"][2],
            delta_deg=c["_key"][3], r_p=c["_key"][4],
            beta_deg=c["_key"][5], failed_closed=True,
            reason=c["reason"], _design="class C1"))
    coarse_pass = [c for c in c1_live if c["all_pass"]]
    if coarse_pass:
        finalists = sorted(coarse_pass,
                           key=lambda c: (c["a_worst"],
                                          -c["r_p"],
                                          abs(c["delta"]), c["Py"],
                                          c["_key"]))[:10]
    else:
        finalists = sorted(c1_live,
                            key=lambda c: (c["a_worst"],
                                           -c["r_p"],
                                           abs(c["delta"]), c["Py"],
                                           c["_key"]))[:10]
    R("  finalists audited on the %.2f deg grid: %d" %
      (FINE_STEP_DEG, len(finalists)))
    c1_final = []
    for c in finalists:
        Px, Py, A, delta, rp, beta = c["_key"]
        fine = evaluate_c1_candidate(Px, Py, A, delta, rp, beta,
                                     gate, FINE_STEP_DEG)
        fine["_key"] = c["_key"]
        c1_final.append(fine)
        if fine["failed_closed"]:
            R("    Px=%.1f Py=%.1f A=%.2f Delta=%.0f r_p=%.2f"
              " beta=%.0f: FAILED CLOSED: %s" %
              (Px, Py, A, delta, rp, beta, fine["reason"]))
            continue
        R("    Px=%.1f Py=%.1f A=%.2f Delta=%+.0f r_p=%.2f"
          " beta=%.0f: a_car %.3f a_lev %.3f beta %.3f | curv"
          " %s tol %s -- %s" %
          (Px, Py, A, delta, rp, beta, fine["a_car"],
           fine["a_lev"], fine["beta_slot"],
           "PASS" if fine["curv_pass"] else "FAIL",
           "PASS" if fine["tol_pass"] else "FAIL",
           "PASS (all rows)" if fine["all_pass"] else "FAIL"))
        rows.append(base_row(
            "design_parameter", source_commit, design_class="C1",
            Px=Px, Py=Py, A=A, delta_deg=delta, r_p=rp,
            beta_deg=beta, a_car_deg=fine["a_car"],
            a_lev_deg=fine["a_lev"], beta_slot_deg=fine[
                "beta_slot"],
            a_worst_deg=fine["a_worst"],
            min_rad_car=fine["min_rad_car"],
            min_rad_lev=fine["min_rad_lev"],
            closure_residual=fine["closure"],
            r_pin_range=fine["r_pin_range"],
            gate_pass=fine["gate_pass"],
            curv_pass=fine["curv_pass"],
            tol_pass=fine["tol_pass"],
            efficiency_loss_binding=efficiency_loss(
                gate["mu_binding"], fine["a_worst"]),
            efficiency_loss_loose=efficiency_loss(
                gate["mu_loose"], fine["a_worst"]),
            selflock_exceeded=bool(
                fine["a_worst"] > gate["selflock_binding_deg"]),
            _design="class C1"))
    c1_f_live = [c for c in c1_final if not c["failed_closed"]]
    c1_f_pass = [c for c in c1_f_live if c["all_pass"]]
    if c1_f_pass:
        c1_pick = sorted(c1_f_pass,
                         key=lambda c: (c["a_worst"], -c["r_p"],
                                        abs(c["delta"]), c["Py"],
                                        c["_key"]))[0]
    elif c1_f_live:
        c1_pick = sorted(c1_f_live,
                         key=lambda c: (c["a_worst"], -c["r_p"],
                                        abs(c["delta"]), c["Py"],
                                        c["_key"]))[0]
    else:
        c1_pick = None
    if c1_pick is not None:
        R("  chosen (frozen pick rule): Px=%.1f Py=%.1f A=%.2f"
          " Delta=%+.0f r_p=%.2f beta=%.0f, a_worst %.3f deg" %
          (c1_pick["Px"], c1_pick["Py"], c1_pick["A"],
           c1_pick["delta"], c1_pick["r_p"], c1_pick["beta"],
           c1_pick["a_worst"]))
        R("  C1 verdict: %s" %
          ("PASS (all rows)" if c1_pick["all_pass"] else
           "WIDE-FAIL (the honest all-fail is the outcome; the"
           " gate is never relaxed)"))
        rows.append(base_row(
            "class_verdict", source_commit, design_class="C1",
            pick_a_worst=c1_pick["a_worst"], pick_Px=c1_pick["Px"],
            pick_Py=c1_pick["Py"], pick_A=c1_pick["A"],
            pick_delta=c1_pick["delta"], pick_r_p=c1_pick["r_p"],
            pick_beta=c1_pick["beta"],
            verdict="PASS" if c1_pick["all_pass"] else
            "WIDE-FAIL", _design="class C1"))
        for r_ in c1_pick["tol_rows"]:
            rows.append(base_row("tolerance", source_commit,
                                 design_class="C1",
                                 pick_Px=c1_pick["Px"],
                                 pick_Py=c1_pick["Py"],
                                 handoff=r_["handoff"],
                                 channel=r_["channel"],
                                 rank_deficient=r_.get(
                                     "rank_deficient", False),
                                 pos_units=r_.get("pos_units"),
                                 ori_deg=r_.get("ori_deg"),
                                 reason=r_.get("reason"),
                                 _design="class C1"))
        for r_ in c1_pick["tol_rows"]:
            if r_.get("rank_deficient"):
                R("  WC-L at %s: RANK DEFICIENT (fail-closed): %s" %
                  (r_["handoff"], r_["reason"]))
            elif r_.get("channel") == "combined_wc_l":
                R("  WC-L at %s (combined): pos %.4f mm / ori"
                  " %.4f deg vs 1.5 mm / 1.5 deg -- %s" %
                  (r_["handoff"], r_["pos_units"] * 100.0,
                   r_["ori_deg"],
                   "PASS" if r_["pos_units"] <= TOL_POS_UNITS and
                   r_["ori_deg"] <= TOL_ORI_DEG else "FAIL"))
        R("  (channels separate in the tolerance rows: carriage")
        R("  groove, lever groove, slot wall; the drive-reversal")
        R("  backlash priced at both handoffs)")

    # -- S5 envelope -------------------------------------------------
    x0, x1, y0, y1 = part_sweep_bbox()
    R("")
    R("[S5 ENVELOPE] exact-rectangle part model at %.2f deg pose"
      % ENVELOPE_STEP_DEG)
    R("  samples (sampled, never certified; recorded data, not")
    R("  gated -- no size demand is frozen by the brief):")
    R("  part sweep bbox x [%.4f, %.4f] y [%.4f, %.4f] units"
      % (x0, x1, y0, y1))
    R("  (mm: x [%.1f, %.1f], y [%.1f, %.1f])" %
      (x0 * 100.0, x1 * 100.0, y0 * 100.0, y1 * 100.0))
    R("  handoff stations at (-130, 50) mm and (130, 50) mm (the")
    R("  demand points); packaging per the -05 axial-stack")
    R("  convention (in-plan overlap is packaging, not")
    R("  interference)")
    env = {"part_sweep_bbox_units": [x0, x1, y0, y1],
           "handoff_stations_mm": [[-130.0, 50.0], [130.0, 50.0]]}
    if g1_pick is not None:
        plate_r = g1_pick["g_mag_max"] + PIN_RADIUS
        env["g1_plate_radius_units"] = plate_r
        R("  class G1 additions (data): plate radius %.2f units"
          " (max groove centerline + %.2f wall class), plate"
          % (plate_r, PIN_RADIUS))
        R("  center on the demand symmetry axis at x = 0")
    if c1_pick is not None:
        Pl = (c1_pick["Px"], c1_pick["Py"])
        lev_r = max(c1_pick["r_pin_range"][1] + 0.06, c1_pick["A"])
        env["lever_sweep"] = {
            "center_units": list(Pl), "radius_units": lev_r}
        env["c1_plate_radius_units"] = {
            "channel_x": c1_pick["g_mag_max_car"] + PIN_RADIUS,
            "channel_p": c1_pick["g_mag_max_lev"] + PIN_RADIUS}
        R("  class C1 additions (data): lever sweep centered (%.1f,"
          " %.1f) radius %.2f units; carriage box x [-1.45, 1.45]"
          % (Pl[0], Pl[1], lev_r))
        R("  y [0.44, 0.56] (declared hardware box); plate radii")
        R("  %.2f (channel x) / %.2f units (channel p), centers at"
          % (c1_pick["g_mag_max_car"] + PIN_RADIUS,
             c1_pick["g_mag_max_lev"] + PIN_RADIUS))
        R("  (0, -1.0), grooves annular (the declared class)")
    rows.append(base_row("envelope", source_commit, **env))

    # -- S6 reciprocity ----------------------------------------------
    R("")
    R("[S6 RECIPROCITY] instrument modification count: 0 (the")
    R("  graded rows S1-S6 are the recorded study's audit")
    R("  structure, carried; the gate is the ruling's, consumed;")
    R("  any delta would be named per modification)")
    rows.append(base_row("reciprocity", source_commit,
                         instrument_modification_count=0,
                         definition="modifications to the carried "
                                    "audit structure; 0 expected"))

    # -- the wide-fail branch reading --------------------------------
    any_pass = (g1_pick is not None and g1_pick["all_pass"]) or \
               (c1_pick is not None and c1_pick["all_pass"])
    R("")
    R("[READING] wide-fail branch (pre-stated in the freeze): if")
    R("  no declared class passes all rows, the honest all-fail IS")
    R("  the outcome: recorded as data, never an error; the")
    R("  supplier question is not reached; the supplier triggers")
    R("  stay unfired; the gate is never relaxed. Overall: %s" %
      ("A CLASS PASSES ALL ROWS" if any_pass else
       "WIDE-FAIL at the declared classes"))
    rows.append(base_row("scorecard_verdict", source_commit,
                         row="overall_wide_fail_branch",
                         any_class_all_pass=any_pass,
                         verdict="PASS" if any_pass else
                         "WIDE-FAIL"))

    rows.append(base_row(
        "changelog", source_commit,
        schema_from="1.1 (the recorded study's emitter)",
        schema_to=CORPUS_SCHEMA_VERSION,
        adds=sorted(["search_class_declaration", "class_verdict",
                     "recorded_design_reference"]),
        note="additive; no existing field's meaning, unit or name "
             "changed"))
    return rows, report


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    source_commit = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--source-commit":
            if i + 1 >= len(args):
                print("FAIL-CLOSED: --source-commit needs a value",
                      file=sys.stderr)
                return 2
            source_commit = args[i + 1]
            i += 2
        else:
            print("FAIL-CLOSED: unknown argument %r" % a,
                  file=sys.stderr)
            return 2
    if not isinstance(source_commit, str) or \
            len(source_commit) != 40 or \
            any(ch not in "0123456789abcdef" for ch in source_commit):
        print("FAIL-CLOSED: --source-commit must be a 40-char "
              "lowercase hex sha", file=sys.stderr)
        return 2

    rows1, report1 = compute(source_commit)
    rows2, report2 = compute(source_commit)
    corpus1 = [json.dumps(r, sort_keys=True) for r in rows1]
    corpus2 = [json.dumps(r, sort_keys=True) for r in rows2]
    identical = (report1 == report2 and corpus1 == corpus2)
    for line in report1:
        print(line)
    jsonl_path, csv_path, h1, h2 = write_corpus(rows1, source_commit)
    print("")
    print("[CORPUS] %d rows, schema %s (additive; changelog row in"
          " corpus)" % (len(rows1), CORPUS_SCHEMA_VERSION))
    print("  %s" % os.path.join(OUTPUT_DIR, CORPUS_STEM + ".jsonl"))
    print("  sha256 %s" % h1)
    print("  %s" % os.path.join(OUTPUT_DIR, CORPUS_STEM + ".csv"))
    print("  sha256 %s" % h2)
    print("double-run determinism check: %s" %
          ("IDENTICAL" if identical else "DIFFERS (FAIL)"))
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
