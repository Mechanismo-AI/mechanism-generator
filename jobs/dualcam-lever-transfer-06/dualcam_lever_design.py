#!/usr/bin/env python3
"""Stage 1 deterministic design script for job dualcam-lever-transfer-06.

Option B -- the debate-adopted successor to the recorded -05 Option A
wide fail: cam + linkage lever on the x axis. Two plate cams remain
axially stacked on one crank shaft. The y cam keeps its translating
roller follower verbatim (the -05 audit carried in unchanged: its
HELD record is the proof the y-axis cam is sound). On the x axis a
single pivoted slotted lever is interposed: the cam's roller
rides the lever's short arm, and the lever's radial slot engages
a pin fixed on the x cross-slide. The lever is parametrized in
full -- the pivot placement and the inter-arm angle between the
pin arm and the roller arm are design-script outputs under
declared constraints (the actor's adopted refinement), not hand
choices; the straight lever is the special case Delta = 0. The
slide stroke is the task stroke; the cam-side lift demand
shrinks by the effective lever ratio. No
search, no solver, no network: pure standard library, deterministic.

What it does, in order:

  A. Validates the frozen -02 task
     (jobs/sixbar-gap-transfer-02/gap_transfer_nostops.motion.json)
     against an independent analytic reconstruction of the loop and
     its two clamped-cubic-spline timing runs -- fail-closed at
     1e-9 normalized units. The task file is read, never modified;
     its SHA-256 is recorded as the byte-identity witness.
  B. Synthesizes cam y verbatim from -05 and cam x through the
     exact lever map: the cam profile is the pre-distorted image of
     the task-space demand (nothing is scaled by a first-order
     ratio); all continuity and derivative cost comparisons are
     evaluated in slide space.
  C. Runs the engineering audit: the oscillating-follower pressure
     angle, pitch-curve curvature with a geometric body-side test,
     the winding monotonicity condition, the lever-output (slot)
     pressure angle, the size cap, and the combined 600 mm
     envelope check. The pivot placement, short-arm length and
     inter-arm angle are chosen by a declared deterministic scan;
     the design outputs are recorded with their derivations, and
     the alpha-vs-A knee table is emitted so the A pick is
     visibly at the knee.
  D. Emits the family-cost table (the -01/-02/-04 recorded six-bar
     frontier and the recorded -05 Option A numbers embedded as
     data, labeled) with the lever's additions: reflected inertia,
     tolerance amplification, junction derivatives restated in
     slide space, per-unit-load shaft torque proxies, and the
     combined swept-envelope row.
  E. Witness-validates the "by construction" claims numerically:
     stop velocity audited at the slide (after the lever), the
     round-trip task reproduction through the emitted pitch curve
     and the lever, the dwell-circle curvature witness, and
     two-run determinism (the whole audit computed twice and
     compared byte-for-byte).

Exit code 0: every internal fail-closed check passed. The G2
verdicts are DATA, not failures -- a wide fail is a recorded result
and never an error exit (and per the frozen terminal branch, a
cam-x wide fail ends the variant chain: no further variant is
staged; the finding returns to the brief level). Exit code 1: an
internal check failed (task validation, a witness, determinism).

Conventions recorded up front (frozen in the JOB scorecard):

  - Physical frame: millimetres, origin at gap centre on the belt
    line, y up; 1 normalized unit = sqrt(75700) mm; sample
    positions centred on the twelve-sample centroid (0, +5) mm.
  - Lever geometry (declared design, general single pivoted lever
    -- one link, one pivot): pivot P = (Px, Py), pin line y = 0
    (the x-slide pin), short arm A, and a fixed inter-arm angle
    Delta from the pin arm to the roller arm (Delta = 0 is the
    straight lever of the brief's first-order reading; a nonzero
    Delta is a bell crank -- still a single pivoted lever). The
    pin-arm direction is psi(th) = atan2(-Py, x_s(th) - Px) with
    x_s the tool x coordinate (the slide position): the ray from
    the pivot at psi meets the pin line at
    x_s = Px - Py / tan(psi) exactly. The slot transmits force
    transverse to the lever ray, so the lever-output (slot)
    pressure angle is beta_out = atan(|x_s - Px| / |Py|), maximal
    at the stroke ends; the lever gate mirrors the cam branches
    (30 deg target / 45 deg hard), so the scan admits only pivots
    with (130 + |Px|) / |Py| <= tan(30 deg).
  - Short arm: the roller centre sits on the lever at radius A
    from the pivot, at the fixed inter-arm angle:
    C(th) = P + A (cos(psi + Delta), sin(psi + Delta)). The cam
    lift demand shrinks by the effective ratio
    lambda_eff(th) = L(th) / A with L = hypot(x_s - Px, Py) the
    pin-arm length (slide speed per roller speed), which varies
    over the stroke: the rocker map is nonlinear and the lever is
    not a linear gearbox. Exact synthesis is through this map,
    never a scaling.
  - Pitch curve, cam frame (shaft at the origin): the roller's
    relative position c = C - O, rotated back:
    w(th) = c(th) exp(-i th). The cam profile is the inward
    parallel curve at roller distance; the x dwell arcs (x_s
    constant) map to concentric pitch circles exactly.
  - Pressure angle, oscillating follower (derivation recorded):
    the cam material under the roller moves at i*c (unit crank
    rate), the roller centre at C', so the pitch-curve tangent in
    the fixed frame is T = C' - i c and the common normal is i T.
    With the force line along the normal,
    tan(alpha) = | |C'|^2 - Im(conj(c) C') | / | Re(conj(c) C') |,
    evaluated with atan2 (a radial-degenerate point reads 90 deg).
    Special-case check: for an in-line translating follower C' is
    along c, Im(conj(c) C') = 0 and Re(conj(c) C') = |c||C'|, so
    the formula reduces to |h'| / (r_base + h), the -05 cam
    convention -- one verified formula family for both cams. The
    angle is undefined at exactly zero follower velocity (the two
    stops, the two x dwells, two arc junctions); those grid points
    are masked, counted and reported.
  - Pitch-curve curvature: kappa = Im(conj(w') w'') / |w'|^3 with
    w' = (C' - i c) exp(-i th) and w'' = (C'' - 2 i C' - c)
    exp(-i th). The undercut gate is geometric, sign-free: the
    curvature centre is tested for lying on the shaft/body side
    (dot(centre - w, -w) > 0); a violation is a body-side
    |rho| < 1.25 x roller radius (18.75 mm). On the dwell circles
    the signed rho reads negative with the centre at the shaft
    (this parametrization's left normal); the dwell-circle
    witness checks that reading numerically.
  - Winding monotonicity: the roller must not outrun the cam
    rotation: Im(conj(c) C') / |c|^2 < 1 everywhere (the pitch
    curve stays single-valued in the cam frame).
  - Size cap and envelope (same lineage as -05): plate diameter
    <= 600 mm per plate; pitch major-radius cap 300 - r_roller =
    285 mm. Both plates are centred on the one shared crank
    shaft, declared at the plan-frame origin O = (0, 0) (the -05
    convention: the two cams are axially stacked on one shaft and
    share the plan view, and the y follower axis passes through
    the shaft). The combined plan-view bounding box of the swept
    components (the swept plate/roller discs about the shaft, the
    x-slide box [-150,150] x [-25,75], the pivot boss of radius
    20 mm inside the envelope, and the lever sweep including the
    pin range) must fit 600 x 600 mm simultaneously -- two cams
    that each fit can still collide.
  - Packaging convention (the -05 axial-stack convention,
    declared): the cam plates, the lever and the slides occupy
    separate parallel planes; the roller bridges to its cam plane
    on a declared stub. Plan-view overlap is therefore packaging,
    not interference. The first staging declaration's in-plane
    pivot-to-plate clearance screen is withdrawn, with its
    derivation and the withdrawal reason recorded in the JOB
    staging section (it was also mis-derived: the plate profile
    sits inside the pitch major by the roller radius).
  - Design scan (declared deterministic, no search in the solver
    sense): pivot placement P = (Px, Py) on the coarse grid
    Px in {-24, -12, 0, 12, 24} mm and Py in +-{225, ..., 275} mm
    step 5 (the beta_out gate admits |Px| <= 24; the pivot boss
    must sit inside the 600 mm square), short arm A on the
    60-200 mm grid step 10, and the inter-arm angle Delta
    bracketing the two analytic mid-radial orientations
    (P - O) . u_hat = -A at +- {0, 4, 8} deg. At each candidate
    the coarse 4 deg screen requires the winding condition, the
    285 mm cap, the slot-angle gate, the >= 60 mm base
    (tangent-length) bound and a 32 deg alpha workload bound (a
    bound, not a gate). Each A with a screened candidate is
    refined on the 1 deg grid (Px +- 6 mm at 1 mm, Py +- 6 mm at
    2 mm, Delta +- 3 deg at 0.25 deg) and evaluated on the full
    0.1 deg grid. The pick rule (frozen from the debate): the
    smallest effective ratio that meets the 30 deg target -- the
    largest A whose FINAL 0.1 deg audit holds the target with the
    hard constraints; A is ascended in 1 mm steps from the largest
    passing coarse A with warm-start refinement, each step gated
    by its own final audit. If no A meets the target, the best
    refined candidate is recorded for the branch decision. The
    knee table is emitted with the report. The staging history
    (the first declaration's straight lever with a hand-frozen
    pivot, falsified by the staging smoke reading) is recorded in
    the JOB.
"""

import hashlib
import json
import math
import sys

PI = math.pi
DEG = 180.0 / PI

# ---- frozen task constants (case study B, the -01/-02 records) ----
DIAG = math.sqrt(75700.0)          # 260 x 90 mm bounding-box diagonal
CENTROID = (0.0, 5.0)             # twelve-sample centroid (exact)
TASK_TOL = 1e-9                   # fail-closed tolerance, normalized
ARC15 = 15.0 * PI / 2.0           # 90 deg corner arc, 15 mm radius

GRID_N = 3600                     # 0.1 deg grid per cam
ROLLER_R = 15.0                   # first-cut roller radius (recorded)
CURV_MARGIN = 1.25                # rho >= 1.25 x roller radius
ENVELOPE = 600.0                  # compact-transfer benchmark envelope (mm)
PLATE_CAP = 300.0                 # plate radius cap = ENVELOPE / 2
RADIUS_CAP = PLATE_CAP - ROLLER_R # pitch major-radius cap (mm)
ALPHA_TARGET = 30.0               # deg, textbook target, all interfaces
ALPHA_HARD = 45.0                 # deg, hard branch threshold

# Loop segment boundary arc positions (mm).
S_CARRY_END = 260.0               # set-down stop T3 / descent start
S_DESC_END = 335.0                # descent line end, right arc start
S_RARC_END = S_DESC_END + ARC15   # right arc end / return line start
S_RET_END = S_RARC_END + 230.0    # return line end, left arc start
S_LARC_END = S_RET_END + ARC15    # left arc end / ascent line start
S_LOOP = S_LARC_END + 75.0        # closes at phase 0
# Twelve-sample arc positions (the -02 knot table).
KNOT_S = [0.0, 65.0, 130.0, 195.0, S_CARRY_END, 305.0,
          S_RARC_END, S_RARC_END + 57.5, S_RARC_END + 115.0,
          S_RARC_END + 172.5, S_RET_END, S_LARC_END + 30.0]

# ---- Option B lever constants (declared design, general lever) ----
# The single pivoted lever is parametrized in full: pivot P = (Px, Py),
# short arm A, and the fixed inter-arm angle Delta between the pin arm
# and the roller arm (Delta = 0 is the straight lever of the brief's
# first-order reading; a nonzero Delta is still one link, one pivot).
# Pivot placement and Delta are DESIGN-SCRIPT OUTPUTS (the actor's
# adopted refinement), scanned deterministically under declared
# constraints -- never hand choices.
SHAFT = (0.0, 0.0)               # shared crank shaft, plan-frame origin
PIN_LINE_Y = 0.0                  # the x-slide pin line
BOSS_R = 20.0                     # pivot boss radius (declared screen)
ENV_HALF = ENVELOPE / 2.0         # plan-view envelope half width (300 mm)
BASE_MIN = 60.0                   # x-cam min pitch radius (tangent length)
BETA_TARGET = 30.0                # lever-output slot angle target (deg)
SCAN_PX = [-24.0, -12.0, 0.0, 12.0, 24.0]     # coarse pivot x (mm)
SCAN_PY = [s * v for s in (1.0, -1.0)
           for v in (225.0 + 5.0 * k for k in range(11))]  # coarse pivot y
SCAN_A_COARSE = [float(a) for a in range(60, 201, 10)]     # short arm (mm)
DELTA_OFFS_DEG = (-8.0, -4.0, 0.0, 4.0, 8.0)  # bracket the analytic
COARSE_N = 90                     # 4 deg scan grid
REFINE_N = 360                    # 1 deg refinement grid
REFINE_PX = 6.0                   # refinement span in Px (step 1 mm)
REFINE_PY = 6.0                   # refinement span in Py (step 2 mm)
REFINE_D = 3.0                    # refinement span in Delta (step 0.25 deg)
ALPHA_SCREEN = 32.0               # coarse workload bound (NOT a gate)
SLIDE_BOX = (-150.0, 150.0, -25.0, 75.0)  # declared x-slide hardware box
PIN_TOL = 1e-6                    # round-trip witness, mm
DWELL_RHO_TOL = 1e-6              # dwell-circle witness, relative
# ---------------------------------------------------------------- geometry
def loop_state(s):
    """Position, unit tangent and curvature vector d2P/ds2 of the
    frozen -02 loop at arc position s (mm). C1 everywhere; the
    curvature vector jumps at the six junctions. Boundary tie: the
    LATER segment wins (the follower laws pin the carry side at
    the theta = 120 deg seam instead, matching the timing-run tie;
    both one-sided readings are reported in the junction table)."""
    if s < S_CARRY_END:
        return (-130.0 + s, 50.0), (1.0, 0.0), (0.0, 0.0)
    if s < S_DESC_END:
        return (130.0, 50.0 - (s - S_CARRY_END)), (0.0, -1.0), (0.0, 0.0)
    if s < S_RARC_END:
        phi = -(s - S_DESC_END) / 15.0
        c, sn = math.cos(phi), math.sin(phi)
        return ((115.0 + 15.0 * c, -25.0 + 15.0 * sn),
                (sn, -c), (-c / 15.0, -sn / 15.0))
    if s < S_RET_END:
        return (115.0 - (s - S_RARC_END), -40.0), (-1.0, 0.0), (0.0, 0.0)
    if s < S_LARC_END:
        phi = -PI / 2.0 - (s - S_RET_END) / 15.0
        c, sn = math.cos(phi), math.sin(phi)
        return ((-115.0 + 15.0 * c, -25.0 + 15.0 * sn),
                (sn, -c), (-c / 15.0, -sn / 15.0))
    return (-130.0, -25.0 + (s - S_LARC_END)), (0.0, 1.0), (0.0, 0.0)


def segment_of(s):
    """Segment index at arc position s (same tie rule as
    loop_state): 0 carry, 1 descent, 2 right arc, 3 return,
    4 left arc, 5 ascent."""
    if s < S_CARRY_END:
        return 0
    if s < S_DESC_END:
        return 1
    if s < S_RARC_END:
        return 2
    if s < S_RET_END:
        return 3
    if s < S_LARC_END:
        return 4
    return 5


# ---------------------------------------------------------------- timing
class ClampedSpline(object):
    """Clamped cubic spline through (t, y) knots with prescribed end
    slopes, in the moment (second-derivative) form."""

    def __init__(self, ts, ys, v0, vn):
        n = len(ts) - 1
        h = [ts[i + 1] - ts[i] for i in range(n)]
        d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n)]
        # Tridiagonal system for the moments M[0..n].
        lo = [0.0] * (n + 1)
        di = [0.0] * (n + 1)
        up = [0.0] * (n + 1)
        rhs = [0.0] * (n + 1)
        di[0], up[0] = 2.0, 1.0
        rhs[0] = 6.0 * (d[0] - v0) / h[0]
        for i in range(1, n):
            lo[i] = h[i - 1]
            di[i] = 2.0 * (h[i - 1] + h[i])
            up[i] = h[i]
            rhs[i] = 6.0 * (d[i] - d[i - 1])
        lo[n], di[n] = 1.0, 2.0
        rhs[n] = 6.0 * (vn - d[n - 1]) / h[n - 1]
        # Thomas algorithm.
        for i in range(1, n + 1):
            w = lo[i] / di[i - 1]
            di[i] -= w * up[i - 1]
            rhs[i] -= w * rhs[i - 1]
        m = [0.0] * (n + 1)
        m[n] = rhs[n] / di[n]
        for i in range(n - 1, -1, -1):
            m[i] = (rhs[i] - up[i] * m[i + 1]) / di[i]
        self.t, self.y, self.h, self.m = ts, ys, h, m

    def _piece(self, t):
        ts = self.t
        lo, hi = 0, len(ts) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if ts[mid] <= t:
                lo = mid
            else:
                hi = mid
        return lo

    def s(self, t):
        i = self._piece(t)
        h = self.h[i]
        tl, tr = self.t[i], self.t[i + 1]
        a, b = tr - t, t - tl
        mi, mj = self.m[i], self.m[i + 1]
        yi, yj = self.y[i], self.y[i + 1]
        return (mi * a ** 3 + mj * b ** 3) / (6.0 * h) \
            + (yi / h - mi * h / 6.0) * a \
            + (yj / h - mj * h / 6.0) * b

    def d1(self, t):
        i = self._piece(t)
        h = self.h[i]
        tl, tr = self.t[i], self.t[i + 1]
        a, b = tr - t, t - tl
        mi, mj = self.m[i], self.m[i + 1]
        return (-mi * a * a + mj * b * b) / (2.0 * h) \
            + (self.y[i + 1] - self.y[i]) / h - (mj - mi) * h / 6.0

    def d2(self, t):
        i = self._piece(t)
        h = self.h[i]
        a, b = self.t[i + 1] - t, t - self.t[i]
        return (self.m[i] * a + self.m[i + 1] * b) / h


TH_KNOTS = [k * PI / 6.0 for k in range(13)]
CARRY = ClampedSpline(TH_KNOTS[0:5], KNOT_S[0:5], 0.0, 0.0)
BOTTOM = ClampedSpline(TH_KNOTS[4:13], KNOT_S[4:13] + [S_LOOP], 0.0, 0.0)
TH_CARRY_END = TH_KNOTS[4]


def timing_state(th):
    """Arc position and derivatives of the frozen -02 timing law at
    crank angle th (rad). Tie at the set-down stop: the carry run
    wins (both runs give s = 260, s' = 0 there)."""
    if th <= TH_CARRY_END:
        return CARRY.s(th), CARRY.d1(th), CARRY.d2(th), "carry"
    return BOTTOM.s(th), BOTTOM.d1(th), BOTTOM.d2(th), "bottom"


def theta_of_s(s_target):
    """Crank angle (rad) at which the timing law reaches arc
    position s_target (s is monotone in theta)."""
    lo, hi = 0.0, 2.0 * PI
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if timing_state(mid)[0] < s_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------- task sample convention
def task_sample(i):
    """The -02 demand at phase i (12 phases, 30 deg apart), in mm
    units: position (mm), velocity (mm/rad), acceleration
    (mm/rad^2). Conventions per the -02 audit trail: stops are
    vector means of the two one-sided accelerations; the two
    junction phases are means of the line-side and arc-side
    one-sided accelerations."""
    th = TH_KNOTS[i]
    s, d1, d2, _ = timing_state(th)
    p, t, c = loop_state(s)
    v = (t[0] * d1, t[1] * d1)
    if i == 0 or i == 4:
        # Process stop: mean of deceleration into and acceleration
        # out of the stop, one-sided splines, one-sided tangents.
        if i == 0:
            t_in, s_in = (0.0, 1.0), BOTTOM.d2(2.0 * PI)
            t_out, s_out = (1.0, 0.0), CARRY.d2(0.0)
        else:
            t_in, s_in = (1.0, 0.0), CARRY.d2(TH_CARRY_END)
            t_out, s_out = (0.0, -1.0), BOTTOM.d2(TH_CARRY_END)
        a = (0.5 * (t_in[0] * s_in + t_out[0] * s_out),
             0.5 * (t_in[1] * s_in + t_out[1] * s_out))
    elif i == 6 or i == 10:
        # Line/arc junction: mean of the line-side and arc-side
        # one-sided accelerations (shared tangent and s'').
        c_line = (0.0, 0.0)
        c_arc = (0.0, 1.0 / 15.0)
        a = (t[0] * d2 + 0.5 * (c_line[0] + c_arc[0]) * d1 * d1,
             t[1] * d2 + 0.5 * (c_line[1] + c_arc[1]) * d1 * d1)
    else:
        a = (c[0] * d1 * d1 + t[0] * d2, c[1] * d1 * d1 + t[1] * d2)
    return p, v, a, s, d1, d2


# ------------------------------------------------------------ validation
def validate_task(task):
    """Fail-closed reconstruction check against the frozen task
    file. Returns the per-field worst absolute differences."""
    worst = {"q": 0.0, "v": 0.0, "a": 0.0, "theta": 0.0}
    for i in range(12):
        p, v, a, _, _, _ = task_sample(i)
        qn = ((p[0] - CENTROID[0]) / DIAG, (p[1] - CENTROID[1]) / DIAG)
        vn = (v[0] / DIAG, v[1] / DIAG)
        an = (a[0] / DIAG, a[1] / DIAG)
        for k in (0, 1):
            worst["q"] = max(worst["q"], abs(qn[k] - task["q"][i][k]))
            worst["v"] = max(worst["v"], abs(vn[k] - task["v"][i][k]))
            worst["a"] = max(worst["a"], abs(an[k] - task["a"][i][k]))
        worst["theta"] = max(worst["theta"],
                            abs(TH_KNOTS[i] - task["theta_rad"][i]))
        for k in (0, 1, 2):
            if task["q"][i][2] != 0 or task["v"][i][2] != 0 \
                    or task["a"][i][2] != 0:
                return None  # third component must be zero (planar task)
    return worst


# --------------------------------------------------------- cam synthesis
def follower_state(cam, th):
    """Follower displacement law h(th) with derivatives for cam 'x'
    or 'y' at crank angle th (rad), segmentwise exact. h = tool
    coordinate minus its travel minimum. Grid tie rules: at the
    theta = 120 deg seam the carry side wins (matching the timing
    run tie th <= 120 deg); at interior path boundaries the later
    segment wins; the junction table reports both sides."""
    s, d1, d2, _ = timing_state(th)
    if th <= TH_CARRY_END:
        p, t, c = loop_state_side(0, min(s, S_CARRY_END))
    else:
        p, t, c = loop_state(s)
    k = 0 if cam == "x" else 1
    off = 130.0 if cam == "x" else 40.0
    h = p[k] + off
    hp = t[k] * d1
    hpp = c[k] * d1 * d1 + t[k] * d2
    return h, hp, hpp, s


def follower_sided(cam, seg, th):
    """One-sided follower derivatives at a junction, evaluated on
    path segment `seg` with the spline run that meets it there:
    at the phase-0 seam the ascent side reads the bottom run at
    2*pi and the carry side the carry run at 0; at the phase-4
    seam the carry side reads the carry run and the descent side
    the bottom run; interior junctions read the bottom run (the
    spline is C2 across its interior knots)."""
    if th <= 1e-9:
        if seg == 5:
            s, d1, d2 = S_LOOP, BOTTOM.d1(2.0 * PI), BOTTOM.d2(2.0 * PI)
        else:
            s, d1, d2 = 0.0, CARRY.d1(0.0), CARRY.d2(0.0)
    elif th <= TH_CARRY_END + 1e-9:
        s = S_CARRY_END
        if seg == 0:
            d1, d2 = CARRY.d1(th), CARRY.d2(th)
        else:
            d1, d2 = BOTTOM.d1(th), BOTTOM.d2(th)
    else:
        s = timing_state(th)[0]
        d1, d2 = BOTTOM.d1(th), BOTTOM.d2(th)
    p, t, c = loop_state_side(seg, s)
    k = 0 if cam == "x" else 1
    off = 130.0 if cam == "x" else 40.0
    return p[k] + off, t[k] * d1, c[k] * d1 * d1 + t[k] * d2


def loop_state_side(seg, s):
    """loop_state restricted to a named segment (no tie rule)."""
    if seg == 0:
        return (-130.0 + s, 50.0), (1.0, 0.0), (0.0, 0.0)
    if seg == 1:
        return (130.0, 50.0 - (s - S_CARRY_END)), (0.0, -1.0), (0.0, 0.0)
    if seg == 2:
        phi = -(s - S_DESC_END) / 15.0
        c, sn = math.cos(phi), math.sin(phi)
        return ((115.0 + 15.0 * c, -25.0 + 15.0 * sn),
                (sn, -c), (-c / 15.0, -sn / 15.0))
    if seg == 3:
        return (115.0 - (s - S_RARC_END), -40.0), (-1.0, 0.0), (0.0, 0.0)
    if seg == 4:
        phi = -PI / 2.0 - (s - S_RET_END) / 15.0
        c, sn = math.cos(phi), math.sin(phi)
        return ((-115.0 + 15.0 * c, -25.0 + 15.0 * sn),
                (sn, -c), (-c / 15.0, -sn / 15.0))
    return (-130.0, -25.0 + (s - S_LARC_END)), (0.0, 1.0), (0.0, 0.0)


def polar_rho(r, hp, hpp):
    """Signed pitch-curve curvature radius, polar form (cam y)."""
    num = (r * r + hp * hp) ** 1.5
    den = r * r + 2.0 * hp * hp - r * hpp
    if den == 0.0:
        return float("inf")
    return num / den


# ------------------------------------------------------------- the audit
def audit_cam(cam, r_base):
    """Grid audit of one translating-follower cam at base radius
    r_base (mm) -- the verbatim -05 audit, used for the cam-y
    carry-in."""
    worst_alpha, worst_th = 0.0, 0.0
    worst_seg = 0
    rho_pos_min, rho_pos_th = float("inf"), 0.0
    rho_neg_min, rho_neg_th = 0.0, 0.0     # most negative (signed)
    peak_hpp, peak_hpp_th = 0.0, 0.0      # |h''| peak (junction demand)
    for k in range(GRID_N):
        th = 2.0 * PI * k / GRID_N
        h, hp, hpp, s = follower_state(cam, th)
        r = r_base + h
        alpha = math.degrees(math.atan(abs(hp) / r))
        if alpha > worst_alpha:
            worst_alpha, worst_th = alpha, th
            worst_seg = segment_of(s)
        rho = polar_rho(r, hp, hpp)
        if 0.0 < rho < rho_pos_min:
            rho_pos_min, rho_pos_th = rho, th
        if rho < rho_neg_min:
            rho_neg_min, rho_neg_th = rho, th
        if abs(hpp) > peak_hpp:
            peak_hpp, peak_hpp_th = abs(hpp), th
    return {
        "r_base": r_base, "worst_alpha": worst_alpha,
        "worst_alpha_theta": worst_th, "worst_alpha_seg": worst_seg,
        "rho_pos_min": rho_pos_min, "rho_pos_theta": rho_pos_th,
        "rho_neg_min": rho_neg_min, "rho_neg_theta": rho_neg_th,
        "peak_hpp": peak_hpp, "peak_hpp_theta": peak_hpp_th,
    }


def worst_alpha_at(cam, r_base):
    w = 0.0
    for k in range(GRID_N):
        th = 2.0 * PI * k / GRID_N
        h, hp, _, _ = follower_state(cam, th)
        w = max(w, math.degrees(math.atan(abs(hp) / (r_base + h))))
    return w


def required_base_for_angle(cam, target_deg):
    """Minimal base radius with worst pressure angle <= target
    (worst tan alpha is strictly decreasing in r_base: bisection
    is valid)."""
    lo, hi = 0.1, 5000.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if worst_alpha_at(cam, mid) <= target_deg:
            hi = mid
        else:
            lo = mid
    return hi


def required_base_for_curvature(cam):
    """Minimal base radius satisfying the undercut gate (min
    positive rho >= 1.25 x roller), coarse 5 mm scan then 0.5 mm
    downward refinement. Returns None if no r_base below 600 mm is
    needed (i.e. the gate already holds everywhere it can)."""
    def ok(rb):
        for k in range(GRID_N):
            th = 2.0 * PI * k / GRID_N
            h, hp, hpp, _ = follower_state(cam, th)
            rho = polar_rho(rb + h, hp, hpp)
            if 0.0 < rho < CURV_MARGIN * ROLLER_R:
                return False
        return True
    rb = 5.0
    while rb < 600.0 and not ok(rb):
        rb += 5.0
    if rb >= 600.0:
        return None
    best = rb
    cand = rb - 0.5
    while cand >= 0.5 and ok(cand):
        best = cand
        cand -= 0.5
    return best


# ------------------------------------------------- junctions and dwells
JUNCTIONS = [
    ("pick stop seam (phase 0): ascent | carry", 0.0, (5, 0)),
    ("set-down stop seam (phase 4): carry | descent", TH_CARRY_END, (0, 1)),
    ("descent/arc junction", theta_of_s(S_DESC_END), (1, 2)),
    ("arc/return junction (phase 6)", PI, (2, 3)),
    ("return/left-arc junction (phase 10)", 10.0 * PI / 6.0, (3, 4)),
    ("left-arc/ascent junction", theta_of_s(S_LARC_END), (4, 5)),
]


def junction_table(cam, r_base):
    rows = []
    for name, th, sides in JUNCTIONS:
        sa, sb = sides
        ha, hpa, hppa = follower_sided(cam, sa, th)
        hb, hpb, hppb = follower_sided(cam, sb, th)
        ra, rb_ = r_base + ha, r_base + hb
        row = {
            "name": name, "theta_deg": th * DEG,
            "h": ha,
            "alpha_a": math.degrees(math.atan(abs(hpa) / ra)),
            "alpha_b": math.degrees(math.atan(abs(hpb) / rb_)),
            "rho_a": polar_rho(ra, hpa, hppa),
            "rho_b": polar_rho(rb_, hpb, hppb),
            "hpp_a": hppa, "hpp_b": hppb,
        }
        rows.append(row)
    return rows


def dwell_arcs(cam):
    """theta ranges (deg) where the follower is stationary (its
    coordinate constant): the true dwell arcs of the pitch curve."""
    if cam == "x":
        return [("descent dwell (x = +130)", 120.0, theta_of_s(S_DESC_END) * DEG),
                ("ascent dwell (x = -130)", theta_of_s(S_LARC_END) * DEG, 360.0)]
    return [("carry dwell (y = +50)", 0.0, 120.0),
            ("return dwell (y = -40)", theta_of_s(S_RARC_END) * DEG,
             theta_of_s(S_RET_END) * DEG)]


# ---------------------------------------------------- six-bar frontier
SIXBAR_FRONTIER = {
    "-01 (capability, 4 stops)": {
        "best_worst_position": 0.1484,
        "accel_mult": "46.0-54.8x the 0.05 gate",
    },
    "-02 (no bottom stops)": {
        "best_worst_position": 0.1219,
        "accel_mult": "27.8-29.9x the 0.05 gate",
        "worst_orientation_deg": "7.65-9.96 (3 seeds)",
    },
    "-04 (free phase)": {
        "best_worst_position": 0.12570,
        "accel_mult": "17.94-19.66x the 0.05 gate",
    },
    "gates": {"position": 0.01, "packaging_overlay": 0.005452,
              "orientation_deg": 1.0},
}

# Recorded -05 Option A outcome, embedded as data, labeled (the
# succession evidence this job answers).
RECORD_05 = {
    "cam_x_verdict": "WIDE FAIL",
    "cam_x_worst_alpha": 72.6645,
    "cam_x_major_30": 511.609,
    "cam_x_major_45": 389.97,
    "cam_x_peak_hpp": 812.885,
    "cam_x_peak_hpp_norm": 2.95448,
    "cam_y_verdict": "HELD",
    "cam_y_worst_alpha": 25.8817,
    "cam_y_major_30": 246.098,
    "cap": RADIUS_CAP,
}


# ------------------------------------------- lever machinery (general)
def lever_psi_terms(u, up, upp, Px, Py):
    """Pin-arm angle state: psi = atan2(-Py, u - Px) (the pin arm
    from the pivot to the pin on the line y = 0) and its theta
    derivatives, from the exact slot map. The lever is rigid, so
    the roller arm swings with the same psi rate."""
    w = u - Px
    L2 = w * w + Py * Py
    psi1 = Py * up / L2
    psi2 = Py * (upp * L2 - 2.0 * w * up * up) / (L2 * L2)
    return psi1, psi2


def lever_centre(u, up, upp, Px, Py, A, Delta):
    """Roller centre and its theta derivatives for the general
    single pivoted lever: pivot (Px, Py), short arm A at the fixed
    inter-arm angle Delta from the pin arm (one link, one pivot;
    Delta = 0 is the straight lever)."""
    psi1, psi2 = lever_psi_terms(u, up, upp, Px, Py)
    om = math.atan2(-Py, u - Px) + Delta
    co, so = math.cos(om), math.sin(om)
    Cx = Px + A * co
    Cy = Py + A * so
    Cpx = -A * psi1 * so
    Cpy = A * psi1 * co
    Cppx = A * (-psi2 * so - psi1 * psi1 * co)
    Cppy = A * (psi2 * co - psi1 * psi1 * so)
    return Cx, Cy, Cpx, Cpy, Cppx, Cppy, psi1


class LeverGrid(object):
    """Precomputed x-slide states on a uniform theta grid. The
    task-side states are independent of the lever parameters, so
    every scan candidate reuses them."""

    def __init__(self, n):
        self.n = n
        self.th = [2.0 * PI * k / n for k in range(n)]
        self.cos = [math.cos(t) for t in self.th]
        self.sin = [math.sin(t) for t in self.th]
        self.u = []
        self.up = []
        self.upp = []
        self.seg = []
        for th in self.th:
            h, hp, hpp, s = follower_state("x", th)
            self.u.append(h - 130.0)
            self.up.append(hp)
            self.upp.append(hpp)
            self.seg.append(segment_of(s))
        self.mask = [p != 0.0 for p in self.up]
        self.masked = sum(1 for m in self.mask if m)


def eval_lever(g, Px, Py, A, Delta):
    """Evaluate one candidate on grid g: worst masked oscillating
    pressure angle about the shared shaft (at the origin), pitch
    major radius, worst winding value, lever-output slot angle,
    and the effective ratio range."""
    major2 = 0.0
    worst_alpha = 0.0
    worst_i = -1
    worst_wind = 0.0
    beta = 0.0
    lam_lo = float("inf")
    lam_hi = 0.0
    for i in range(g.n):
        u = g.u[i]
        Cx, Cy, Cpx, Cpy, _, _, _ = lever_centre(
            u, g.up[i], g.upp[i], Px, Py, A, Delta)
        r2 = Cx * Cx + Cy * Cy
        if r2 > major2:
            major2 = r2
        im = Cx * Cpy - Cy * Cpx
        re = Cx * Cpx + Cy * Cpy
        wind = im / r2 if r2 > 0.0 else math.inf
        if wind > worst_wind:
            worst_wind = wind
        if g.mask[i]:
            num = (Cpx * Cpx + Cpy * Cpy) - im
            al = math.degrees(math.atan2(abs(num), abs(re)))
            if al > worst_alpha:
                worst_alpha = al
                worst_i = i
        b = math.atan2(abs(u - Px), abs(Py))
        if b > beta:
            beta = b
        L = math.hypot(u - Px, -Py) / A
        if L < lam_lo:
            lam_lo = L
        if L > lam_hi:
            lam_hi = L
    major = math.sqrt(major2)
    d = {"Px": Px, "Py": Py, "A": A, "Delta": Delta,
         "major": major, "alpha": worst_alpha, "alpha_i": worst_i,
         "wind": worst_wind, "beta_rad": beta,
         "beta_deg": math.degrees(beta),
         "lambda_eff_min": lam_lo, "lambda_eff_max": lam_hi,
         "base_radius": math.sqrt(max(Px * Px + Py * Py - A * A,
                                       0.0))}
    d["hard_ok"] = (d["wind"] < 1.0
                    and major <= RADIUS_CAP
                    and d["beta_deg"] <= BETA_TARGET
                    and d["base_radius"] >= BASE_MIN
                    and abs(Py) + BOSS_R <= ENV_HALF + 1e-9)
    d["screen_ok"] = d["hard_ok"] and worst_alpha <= ALPHA_SCREEN
    return d


def delta_candidates(Px, Py, A):
    """The analytic mid-radial orientations: the roller arm's
    mid-sweep direction is set so the shaft lies on the tangent
    line of the roller arc at mid sweep -- (P - S). u_hat = -A,
    the first-order pressure-angle optimum (the tangent length
    sqrt(|P|^2 - A^2) is then the mid-sweep pitch radius). Two
    tangent solutions exist; the declared scan brackets each with
    DELTA_OFFS_DEG so the pick is not welded to the estimate."""
    Pm = math.hypot(Px, Py)
    if A >= Pm:
        return []
    angP = math.atan2(Py, Px)
    psi_mid = math.atan2(-Py, -Px)
    base = math.acos(-A / Pm)
    out = []
    for sgn in (1.0, -1.0):
        d0 = angP + sgn * base - psi_mid
        for off in DELTA_OFFS_DEG:
            out.append(d0 + math.radians(off))
    return out


def beta_gate_ok(Px, Py):
    """The lever-output slot angle can hold only if
    (130 + |Px|) / |Py| <= tan(30 deg)."""
    return (130.0 + abs(Px)) <= abs(Py) * math.tan(
        math.radians(BETA_TARGET)) + 1e-9


def coarse_scan(g):
    """The declared coarse scan over (Py, Px, A, Delta) on the
    4 deg grid. Returns {A: (key, design)} with the per-A best
    screened candidate (by alpha, then lexicographic ties)."""
    perA = {}
    for Py in SCAN_PY:
        if abs(Py) + BOSS_R > ENV_HALF + 1e-9:
            continue
        for Px in SCAN_PX:
            if not beta_gate_ok(Px, Py):
                continue
            for A in SCAN_A_COARSE:
                for Delta in delta_candidates(Px, Py, A):
                    d = eval_lever(g, Px, Py, A, Delta)
                    if d["screen_ok"]:
                        key = (d["alpha"], Px, Py, Delta)
                        cur = perA.get(A)
                        if cur is None or key < cur[0]:
                            perA[A] = (key, d)
    return perA


def refine_candidate(g, c):
    """The declared local refinement on grid g: Px +- 6 mm at
    1 mm, Py +- 6 mm at 2 mm, Delta +- 3 deg at 0.25 deg around
    the candidate. Hard constraints enforced throughout; the
    alpha workload bound is NOT applied here (the refinement may
    cross it). Deterministic lexicographic ties. The warm start
    is re-read on grid g at its own A before any comparison, so
    the baseline is never a stale alpha carried from the A the
    candidate was last refined at (a carried baseline would
    anchor the search to a design point evaluated at a different
    A, and would report that stale reading in the knee table)."""
    Px0, Py0, D0, A = c["Px"], c["Py"], c["Delta"], c["A"]
    best = eval_lever(g, Px0, Py0, A, D0)
    best_key = (best["alpha"], Px0, Py0, D0)
    for dPx in range(-6, 7):
        Px = Px0 + float(dPx)
        for dPy in range(-6, 7, 2):
            Py = Py0 + float(dPy)
            if not beta_gate_ok(Px, Py):
                continue
            if abs(Py) + BOSS_R > ENV_HALF + 1e-9:
                continue
            for k in range(-12, 13):
                Delta = D0 + k * math.radians(0.25)
                d = eval_lever(g, Px, Py, A, Delta)
                if d["hard_ok"]:
                    key = (d["alpha"], Px, Py, Delta)
                    if key < best_key:
                        best_key, best = key, d
    return best


def pick_design():
    """The declared deterministic pick, frozen before the run:

    1. coarse scan (4 deg grid, alpha workload bound 32 deg -- a
       bound, not a gate);
    2. per-A local refinement on the 1 deg grid for every A with a
       screened candidate, final 0.1 deg evaluation of each;
    3. the pick is the LARGEST A whose FINAL 0.1 deg audit holds
       the 30 deg target with the hard constraints (the smallest
       effective ratio lambda that meets the target -- the debate
       pick rule); A is ascended in 1 mm steps from the largest
       passing coarse A with warm-start refinement, each step
       gated by its own final audit;
    4. if no A meets the target, the best refined candidate by
       final-audit alpha (deterministic ties) is returned for the
       branch record -- mode "best-recorded".

    Returns (design_or_None, knee, mode)."""
    g4 = LeverGrid(COARSE_N)
    g1 = LeverGrid(REFINE_N)
    gf = LeverGrid(GRID_N)
    perA = coarse_scan(g4)
    knee = []
    refined = {}
    for A in sorted(perA):
        _, c = perA[A]
        row = {"A": A, "coarse_alpha": c["alpha"],
               "refined_alpha": None, "final_alpha": None,
               "Px": c["Px"], "Py": c["Py"],
               "Delta_deg": c["Delta"] * DEG}
        if c["alpha"] <= ALPHA_SCREEN:
            r = refine_candidate(g1, c)
            f = eval_lever(gf, r["Px"], r["Py"], A, r["Delta"])
            refined[A] = (r, f["alpha"])
            row.update({"refined_alpha": r["alpha"],
                        "final_alpha": f["alpha"],
                        "Px": r["Px"], "Py": r["Py"],
                        "Delta_deg": r["Delta"] * DEG})
        knee.append(row)
    if not refined:
        return None, knee, "no-screen-pass"
    passing = [A for A in sorted(refined)
               if refined[A][1] <= ALPHA_TARGET]
    if not passing:
        A_best = min(sorted(refined),
                     key=lambda A: (refined[A][1], A))
        pick = refined[A_best][0]
        return pick, knee, "best-recorded"
    A_hi = passing[-1]
    cur = refined[A_hi][0]
    A_cur = A_hi
    A_next_coarse = min([a for a in SCAN_A_COARSE if a > A_hi],
                        default=SCAN_A_COARSE[-1])
    while A_cur < A_next_coarse - 0.5:
        A_next = round(A_cur + 1.0, 6)
        cur["A"] = A_next
        r = refine_candidate(g1, cur)
        f = eval_lever(gf, r["Px"], r["Py"], A_next, r["Delta"])
        knee.append({"A": A_next, "coarse_alpha": None,
                     "refined_alpha": r["alpha"],
                     "final_alpha": f["alpha"],
                     "Px": r["Px"], "Py": r["Py"],
                     "Delta_deg": r["Delta"] * DEG})
        if f["alpha"] <= ALPHA_TARGET and f["hard_ok"]:
            cur, A_cur = r, A_next
        else:
            break
    cur["A"] = A_cur
    return cur, knee, "meets-target"


# ------------------------------------------------- full cam-x audit
def audit_lever(g, d):
    """Full 0.1 deg grid audit of the final cam-x design: the eval
    quantities plus pitch-curve curvature with the geometric
    body-side undercut test, the dwell-circle witness, dwell and
    base radii, the peak demands, and the combined envelope."""
    Px, Py, A, Delta = d["Px"], d["Py"], d["A"], d["Delta"]
    full = eval_lever(g, Px, Py, A, Delta)
    n = g.n
    rho_body_min = float("inf")
    rho_body_th = 0.0
    rho_signed_min = float("inf")
    rho_signed_th = 0.0
    peak_cpp = 0.0
    peak_cpp_th = 0.0
    dwell_err = 0.0
    min_r2 = float("inf")
    om_lo = float("inf")
    om_hi = -float("inf")
    Cx_lo, Cx_hi = float("inf"), -float("inf")
    Cy_lo, Cy_hi = float("inf"), -float("inf")
    x_dwell = dwell_arcs("x")
    for i in range(n):
        th = g.th[i]
        ct, st = g.cos[i], g.sin[i]
        u = g.u[i]
        Cx, Cy, Cpx, Cpy, Cppx, Cppy, _ = lever_centre(
            u, g.up[i], g.upp[i], Px, Py, A, Delta)
        r2 = Cx * Cx + Cy * Cy
        if r2 < min_r2:
            min_r2 = r2
        if Cx < Cx_lo:
            Cx_lo = Cx
        if Cx > Cx_hi:
            Cx_hi = Cx
        if Cy < Cy_lo:
            Cy_lo = Cy
        if Cy > Cy_hi:
            Cy_hi = Cy
        om = math.atan2(Cy - Py, Cx - Px)
        if om < om_lo:
            om_lo = om
        if om > om_hi:
            om_hi = om
        a1 = Cpx + Cy
        b1 = Cpy - Cx
        pre = a1 * ct + b1 * st
        pim = b1 * ct - a1 * st
        a2 = Cppx + 2.0 * Cpy - Cx
        b2 = Cppy - 2.0 * Cpx - Cy
        qre = a2 * ct + b2 * st
        qim = b2 * ct - a2 * st
        nw2 = pre * pre + pim * pim
        kp = (pre * qim - pim * qre) / (nw2 ** 1.5)
        rho = 1.0 / kp if kp != 0.0 else float("inf")
        wre = Cx * ct + Cy * st
        wim = Cy * ct - Cx * st
        dtest = (rho / math.sqrt(nw2)) * (pim * wre - pre * wim)
        if dtest > 0.0 and abs(rho) < rho_body_min:
            rho_body_min = abs(rho)
            rho_body_th = th
        if rho < rho_signed_min:
            rho_signed_min = rho
            rho_signed_th = th
        cpp = math.sqrt(Cppx * Cppx + Cppy * Cppy)
        if g.mask[i] and cpp > peak_cpp:
            peak_cpp = cpp
            peak_cpp_th = th
        if (not g.mask[i]) and th > 1e-9 and th < 2.0 * PI - 1e-9:
            td = th * DEG
            for _, lo, hi in x_dwell:
                if lo + 0.05 < td < hi - 0.05:
                    r = math.sqrt(r2)
                    err = abs(abs(rho) - r) / r
                    if err > dwell_err:
                        dwell_err = err
                    break
    full.update({
        "rho_body_min": rho_body_min, "rho_body_theta": rho_body_th,
        "rho_signed_min": rho_signed_min,
        "rho_signed_theta": rho_signed_th,
        "peak_cpp": peak_cpp, "peak_cpp_theta": peak_cpp_th,
        "dwell_err": dwell_err,
        "base_radius": math.sqrt(min_r2),
        "peak_xs2": max(abs(x) for x in g.upp),
        "peak_xs1": max(abs(x) for x in g.up),
        "alpha_theta": (g.th[full["alpha_i"]]
                        if full["alpha_i"] >= 0 else 0.0),
        "alpha_seg": (g.seg[full["alpha_i"]]
                      if full["alpha_i"] >= 0 else 0),
        "omega_min_deg": om_lo * DEG, "omega_max_deg": om_hi * DEG,
        "Cx_lo": Cx_lo, "Cx_hi": Cx_hi,
        "Cy_lo": Cy_lo, "Cy_hi": Cy_hi,
    })
    # Dwell pitch radii (exact, from the dwell x positions).
    rp = 0.0
    rm = 0.0
    for u in (130.0, -130.0):
        Cx, Cy, _, _, _, _, _ = lever_centre(
            u, 0.0, 0.0, Px, Py, A, Delta)
        if u > 0.0:
            rp = math.hypot(Cx, Cy)
        else:
            rm = math.hypot(Cx, Cy)
    full["dwell_r_plus"] = rp
    full["dwell_r_minus"] = rm
    # Pin-arm length range: the slot travel demand. The minimum
    # arm length sits at u = Px when the pivot x lies inside the
    # pin range, else at the nearer stroke end.
    if -130.0 <= Px <= 130.0:
        L_min = abs(Py)
    else:
        L_min = min(math.hypot(u - Px, -Py)
                   for u in (-130.0, 130.0))
    L_max = max(math.hypot(u - Px, -Py) for u in (-130.0, 130.0))
    full["L_min"] = L_min
    full["L_max"] = L_max
    full["slot_travel"] = L_max - L_min
    return full


def lever_junction_table(d):
    """One-sided readings at the six junctions: the oscillating
    pressure angle where the follower velocity is nonzero on that
    side, pitch-curve rho both sides, and the slide-space x_s''
    both sides (the critic's task-space continuity requirement)."""
    Px, Py, A, Delta = d["Px"], d["Py"], d["A"], d["Delta"]
    rows = []
    for name, th, sides in JUNCTIONS:
        sa, sb = sides
        ct, st = math.cos(th), math.sin(th)
        row = {"name": name, "theta_deg": th * DEG, "sides": []}
        for seg in (sa, sb):
            h, hp, hpp = follower_sided("x", seg, th)
            u = h - 130.0
            Cx, Cy, Cpx, Cpy, Cppx, Cppy, _ = lever_centre(
                u, hp, hpp, Px, Py, A, Delta)
            im = Cx * Cpy - Cy * Cpx
            re = Cx * Cpx + Cy * Cpy
            if hp != 0.0:
                num = (Cpx * Cpx + Cpy * Cpy) - im
                alpha = math.degrees(math.atan2(abs(num), abs(re)))
            else:
                alpha = None
            a1 = Cpx + Cy
            b1 = Cpy - Cx
            pre = a1 * ct + b1 * st
            pim = b1 * ct - a1 * st
            a2 = Cppx + 2.0 * Cpy - Cx
            b2 = Cppy - 2.0 * Cpx - Cy
            qre = a2 * ct + b2 * st
            qim = b2 * ct - a2 * st
            kp = (pre * qim - pim * qre) / ((pre * pre
                                            + pim * pim) ** 1.5)
            rho = 1.0 / kp if kp != 0.0 else float("inf")
            row["sides"].append({"alpha": alpha, "rho": rho,
                                 "xs2": hpp})
        rows.append(row)
    return rows


def lever_invert_pin(Cx, Cy, Px, Py, Delta):
    """Slide pin position from a fixed-frame roller centre: the
    lever ray direction gives omega, the rigid inter-arm angle
    gives psi = omega - Delta, and the ray from the pivot at psi
    meets the pin line y = 0 at u = Px - Py cot(psi)."""
    om = math.atan2(Cy - Py, Cx - Px)
    psi = om - Delta
    return Px - Py * (math.cos(psi) / math.sin(psi))


def witness_roundtrip(g, d):
    """Round trip: emitted cam-frame pitch point -> rotation by
    +theta -> roller centre -> lever ray -> pin line -> slide
    position, compared with the synthesized x_s. Catches rotation
    and map-direction bugs; the error is pure float round-off."""
    Px, Py, A, Delta = d["Px"], d["Py"], d["A"], d["Delta"]
    worst = 0.0
    for i in range(g.n):
        th = g.th[i]
        ct, st = g.cos[i], g.sin[i]
        Cx, Cy, _, _, _, _, _ = lever_centre(
            g.u[i], g.up[i], g.upp[i], Px, Py, A, Delta)
        wre = Cx * ct + Cy * st
        wim = Cy * ct - Cx * st
        sre = wre * ct - wim * st
        sim = wre * st + wim * ct
        pin_x = lever_invert_pin(sre, sim, Px, Py, Delta)
        err = abs(pin_x - g.u[i])
        if err > worst:
            worst = err
    return worst


def witness_task_reproduction(d):
    """The composed tool point through the emitted cam-x pitch
    curve, the lever and the pin, plus the verbatim cam-y law,
    compared with the frozen task positions at the twelve phases
    (normalized). Velocities and accelerations inherit the [A]
    validation by the exact static lever map, so the position
    witness is the new chain."""
    Px, Py, A, Delta = d["Px"], d["Py"], d["A"], d["Delta"]
    worst_q = 0.0
    for i in range(12):
        th = TH_KNOTS[i]
        h, hp, hpp, _ = follower_state("x", th)
        u = h - 130.0
        Cx, Cy, _, _, _, _, _ = lever_centre(
            u, hp, hpp, Px, Py, A, Delta)
        ct, st = math.cos(th), math.sin(th)
        wre = Cx * ct + Cy * st
        wim = Cy * ct - Cx * st
        sre = wre * ct - wim * st
        sim = wre * st + wim * ct
        tool_x = lever_invert_pin(sre, sim, Px, Py, Delta)
        hy, _, _, _ = follower_state("y", th)
        tool_y = hy - 40.0
        p, _, _, _, _, _ = task_sample(i)
        qn = ((tool_x - CENTROID[0]) / DIAG,
              (tool_y - CENTROID[1]) / DIAG)
        for k in (0, 1):
            worst_q = max(worst_q,
                          abs(qn[k] - (p[k] - CENTROID[k]) / DIAG))
    return worst_q


# ------------------------------------------------------------ the report
def build_report(task_path, task_bytes, task):
    worst = validate_task(task)
    if worst is None:
        raise SystemExit("fail-closed: task third component nonzero")
    report = {"task_sha256": hashlib.sha256(task_bytes).hexdigest(),
              "task_validation": worst}

    # ---- cam y: the verbatim -05 carry-in audit ----
    r_cap_y = RADIUS_CAP - 90.0
    aud = audit_cam("y", r_cap_y)
    aud["lift"] = 90.0
    aud["cap_base"] = r_cap_y
    aud["dwell_arcs"] = dwell_arcs("y")
    aud["junctions"] = junction_table("y", r_cap_y)
    aud["required_base_30"] = required_base_for_angle("y", ALPHA_TARGET)
    aud["required_base_45"] = required_base_for_angle("y", ALPHA_HARD)
    aud["major_radius_30"] = aud["required_base_30"] + 90.0
    aud["major_radius_45"] = aud["required_base_45"] + 90.0
    if 0.0 < aud["rho_pos_min"] < CURV_MARGIN * ROLLER_R:
        aud["required_base_curv"] = required_base_for_curvature("y")
    else:
        aud["required_base_curv"] = None
    if aud["worst_alpha"] <= ALPHA_TARGET and \
            not (0.0 < aud["rho_pos_min"] < CURV_MARGIN * ROLLER_R):
        aud["g2_verdict"] = "HELD"
    elif aud["worst_alpha"] <= ALPHA_HARD and \
            not (0.0 < aud["rho_pos_min"] < CURV_MARGIN * ROLLER_R):
        aud["g2_verdict"] = "NARROW FAIL (>30 deg, <=45 deg)"
    else:
        aud["g2_verdict"] = "WIDE FAIL"
    aud["peak_hp"] = max(abs(follower_state("y", 2.0 * PI * k / GRID_N)[1])
                         for k in range(GRID_N))
    report["cam_y"] = aud

    # ---- cam x: the Option B lever design ----
    pick, knee, mode = pick_design()
    report["knee"] = knee
    report["pick_mode"] = mode
    report["stop_velocity"] = {
        "x_theta_0": abs(follower_state("x", 0.0)[1]),
        "x_theta_120": abs(follower_state("x", TH_CARRY_END)[1]),
        "y_theta_0": abs(follower_state("y", 0.0)[1]),
        "y_theta_120": abs(follower_state("y", TH_CARRY_END)[1])}
    report["level_orientation"] = (
        "identity: both slides translate; composed tool yaw is 0 "
        "at all %d grid points" % GRID_N)
    if pick is None:
        report["cam_x"] = {"scan_feasible": False,
                           "g2_verdict": "WIDE FAIL"}
        return report

    g_full = LeverGrid(GRID_N)
    full = audit_lever(g_full, pick)
    full["scan_feasible"] = True
    full["junctions"] = lever_junction_table(full)
    full["masked_points"] = g_full.masked
    # Combined plan-view swept envelope of the declared components
    # (z-stack declared: the plates, lever and slides occupy
    # separate parallel planes -- the -05 axial-stack convention,
    # so plan-view overlap is packaging, not interference).
    sweep_r = max(full["major"], r_cap_y + 90.0) + ROLLER_R
    xs = [-sweep_r, sweep_r, SLIDE_BOX[0], SLIDE_BOX[1],
          full["Px"] - BOSS_R, full["Px"] + BOSS_R,
          full["Cx_lo"], full["Cx_hi"], -130.0, 130.0]
    ys = [-sweep_r, sweep_r, SLIDE_BOX[2], SLIDE_BOX[3],
          full["Py"] - BOSS_R, full["Py"] + BOSS_R,
          full["Cy_lo"], full["Cy_hi"], 0.0]
    full["bbox"] = [min(xs), max(xs), min(ys), max(ys)]
    full["bbox_w"] = max(xs) - min(xs)
    full["bbox_h"] = max(ys) - min(ys)
    full["sweep_r"] = sweep_r
    full["plate_r_x"] = full["major"] + ROLLER_R
    full["plate_r_y"] = r_cap_y + 90.0 + ROLLER_R
    # Verdict at the frozen branches.
    curv_ok = not (full["rho_body_min"] < CURV_MARGIN * ROLLER_R)
    full["curv_ok"] = curv_ok
    full["wind_ok"] = full["wind"] < 1.0
    full["bbox_ok"] = (full["bbox_w"] <= ENVELOPE + 1e-9
                       and full["bbox_h"] <= ENVELOPE + 1e-9)
    full["beta_ok"] = full["beta_deg"] <= BETA_TARGET
    full["cap_ok"] = full["major"] <= RADIUS_CAP
    full["base_ok"] = full["base_radius"] >= BASE_MIN
    full["env_ok"] = abs(full["Py"]) + BOSS_R <= ENV_HALF + 1e-9
    side_ok = (curv_ok and full["wind_ok"] and full["bbox_ok"]
               and full["beta_ok"] and full["cap_ok"]
               and full["base_ok"] and full["env_ok"])
    full["side_ok"] = side_ok
    if full["alpha"] <= ALPHA_TARGET and side_ok:
        full["g2_verdict"] = "HELD"
    elif full["alpha"] <= ALPHA_HARD and side_ok:
        full["g2_verdict"] = "NARROW FAIL (>30 deg, <=45 deg)"
    else:
        full["g2_verdict"] = "WIDE FAIL"
    report["cam_x"] = full

    # ---- witnesses ----
    report["witness_pin"] = witness_roundtrip(g_full, full)
    report["witness_task_q"] = witness_task_reproduction(full)
    return report


def fmt(x):
    return "%.6g" % x


def print_report(rep, task_path, version):
    line = "-" * 64
    print("=" * 64)
    print("dualcam-lever-transfer-06 Stage 1 deterministic design audit")
    print("=" * 64)
    print("python: %s" % version)
    print("task file: %s" % task_path)
    print("task sha256: %s" % rep["task_sha256"])
    print()
    print("[A] Task validation (fail-closed, tol %.1e normalized units)"
          % TASK_TOL)
    w = rep["task_validation"]
    print("    max |dq| = %.3e   max |dv| = %.3e   max |da| = %.3e"
          % (w["q"], w["v"], w["a"]))
    ok = max(w["q"], w["v"], w["a"]) <= TASK_TOL
    print("    verdict: %s" % ("PASS" if ok else "FAIL"))
    print("    knot cross-check (mm): phase speeds",
          ", ".join(fmt(timing_state(TH_KNOTS[i])[1]) for i in range(12)))
    print()
    print("[B] Synthesis (0.1 deg grid, %d points per cam)" % GRID_N)
    a = rep["cam_y"]
    print("  cam y (carry-in from -05, translating roller follower):")
    print("    lift %s mm, cap-limited base circle %s mm"
          % (fmt(a["lift"]), fmt(a["cap_base"])))
    for name, lo, hi in a["dwell_arcs"]:
        print("    dwell arc: %s, theta %.2f -> %.2f deg"
              % (name, lo, hi))
    x = rep["cam_x"]
    if x.get("scan_feasible"):
        print("  cam x (Option B: oscillating roller follower on the")
        print("    pivoted slotted lever's short arm; general single")
        print("    pivoted lever -- pivot and inter-arm angle are")
        print("    scan outputs, not hand choices):")
        print("    lever pivot P = (%s, %s) mm (scan pick)"
              % (fmt(x["Px"]), fmt(x["Py"])))
        print("    pin line y = 0; inter-arm angle Delta = %s deg"
              " (0 deg = the straight lever)"
              % fmt(x["Delta"] * DEG))
        print("    short arm A = %s mm; lever ratio lambda_eff ="
              " L(u)/A in [%s, %s] over the stroke (the rocker map"
              % (fmt(x["A"]), fmt(x["lambda_eff_min"]),
                 fmt(x["lambda_eff_max"])))
        print("      is nonlinear; the lever is not a linear gearbox)")
        print("    roller arm direction swing %s -> %s deg over the"
              " cycle" % (fmt(x["omega_min_deg"]),
                          fmt(x["omega_max_deg"])))
        print("    lever-output slot angle beta_out = %s deg"
              " (gate: <= %s target, 45 hard; the lever gate"
              % (fmt(x["beta_deg"]), fmt(BETA_TARGET)))
        print("      mirrors the cam branches)")
        print("    slot travel demand %s mm (pin-arm L in [%s, %s]"
              " mm; pin size undeclared, forces unrated)"
              % (fmt(x["slot_travel"]), fmt(x["L_min"]),
                 fmt(x["L_max"])))
        print("    shared crank shaft O = (0, 0) (declared; both"
              " plates centred on it, the -05 convention)")
        print("    dwell pitch radii: +130 dwell %s mm; -130 dwell"
              " %s mm" % (fmt(x["dwell_r_plus"]),
                          fmt(x["dwell_r_minus"])))
        print("    base circle (min pitch radius) %s mm; major"
              " radius %s mm" % (fmt(x["base_radius"]),
                                 fmt(x["major"])))
    else:
        print("  cam x: NO feasible design in the declared scan region")
    print()
    print("[C] Engineering audit (frozen G2 branches)")
    print("    envelope %.0f x %.0f mm -> plate diameter <= %.0f mm"
          % (ENVELOPE, ENVELOPE, 2 * PLATE_CAP))
    print("    roller radius %s mm; pitch major-radius cap %s mm"
          % (fmt(ROLLER_R), fmt(RADIUS_CAP)))
    print("    branches: <=30 deg HELD; 30-45 narrow; >45 wide;"
          " undercut gate min body-side |rho| >= %s mm"
          % fmt(CURV_MARGIN * ROLLER_R))
    a = rep["cam_y"]
    print("  cam y @ r_base = %s mm (verbatim -05 audit):"
          % fmt(a["r_base"]))
    print("    worst pressure angle %s deg at theta %s deg "
          "(path segment %d)"
          % (fmt(a["worst_alpha"]), fmt(a["worst_alpha_theta"] * DEG),
             a["worst_alpha_seg"]))
    print("    min positive rho %s mm at theta %s deg; most negative "
          "rho %s mm at theta %s deg"
          % (fmt(a["rho_pos_min"]), fmt(a["rho_pos_theta"] * DEG),
             fmt(a["rho_neg_min"]), fmt(a["rho_neg_theta"] * DEG)))
    print("    peak |h''| %s mm/rad^2 (normalized %s) at theta %s deg"
          % (fmt(a["peak_hpp"]), fmt(a["peak_hpp"] / DIAG),
             fmt(a["peak_hpp_theta"] * DEG)))
    print("    required base for 30 deg: %s mm (major radius %s mm)"
          % (fmt(a["required_base_30"]), fmt(a["major_radius_30"])))
    print("    required base for 45 deg: %s mm (major radius %s mm)"
          % (fmt(a["required_base_45"]), fmt(a["major_radius_45"])))
    if a["required_base_curv"] is not None:
        print("    required base for curvature margin: %s mm"
              % fmt(a["required_base_curv"]))
    else:
        print("    curvature margin: no undercut violation on the grid")
    print("    junction one-sided readings (alpha deg / rho mm /"
          " h'' mm/rad^2):")
    for row in a["junctions"]:
        print("      %-48s th %6.2f  a %6.2f/%6.2f"
              "  rho %9s/%9s  hpp %8.1f/%8.1f"
              % (row["name"], row["theta_deg"], row["alpha_a"],
                 row["alpha_b"], fmt(row["rho_a"]), fmt(row["rho_b"]),
                 row["hpp_a"], row["hpp_b"]))
    print("    G2 VERDICT: %s (carry-in witness: the -05 HELD record,"
          " same code path)" % a["g2_verdict"])
    x = rep["cam_x"]
    if x.get("scan_feasible"):
        print("  cam x design scan (declared deterministic; coarse"
              " 4 deg grid, alpha workload bound %s deg -- a bound,"
              " not a gate; per-A refinement on the 1 deg grid; the"
              % fmt(ALPHA_SCREEN))
        print("    pick is gated by its own final 0.1 deg audit):")
        print("    pick mode: %s" % rep["pick_mode"])
        for row in rep["knee"]:
            if row["coarse_alpha"] is None:
                print("    (1 mm ascension) A=%5s mm: refined %s ->"
                      " final %s deg"
                      % (fmt(row["A"]), fmt(row["refined_alpha"]),
                         fmt(row["final_alpha"])))
            elif row["refined_alpha"] is None:
                print("    A=%5s mm: coarse %s deg (above the"
                      " workload bound; not refined)"
                      % (fmt(row["A"]), fmt(row["coarse_alpha"])))
            else:
                print("    A=%5s mm: coarse %s -> refined %s ->"
                      " final %s deg at P=(%s, %s), Delta %s deg"
                      % (fmt(row["A"]), fmt(row["coarse_alpha"]),
                         fmt(row["refined_alpha"]),
                         fmt(row["final_alpha"]), fmt(row["Px"]),
                         fmt(row["Py"]), fmt(row["Delta_deg"])))
        print("  cam x @ A = %s mm, P = (%s, %s), Delta = %s deg"
              " (final 0.1 deg grid audit):"
              % (fmt(x["A"]), fmt(x["Px"]), fmt(x["Py"]),
                 fmt(x["Delta"] * DEG)))
        print("    worst pressure angle %s deg at theta %s deg "
              "(path segment %d); masked zero-velocity points: %d of "
              "%d (stops, x dwells, two arc junctions)"
              % (fmt(x["alpha"]), fmt(x["alpha_theta"] * DEG),
                 x["alpha_seg"], x["masked_points"], GRID_N))
        print("    min body-side |rho| %s mm at theta %s deg; most "
              "negative signed rho %s mm at theta %s deg (geometric "
              "convention: dwell circles read negative, centre at the "
              "shaft)"
              % (fmt(x["rho_body_min"]), fmt(x["rho_body_theta"] * DEG),
                 fmt(x["rho_signed_min"]),
                 fmt(x["rho_signed_theta"] * DEG)))
        print("    peak |x_s''| (slide space) %s mm/rad^2 (normalized "
              "%s) -- the -05 recorded task demand, unchanged by the "
              "lever" % (fmt(x["peak_xs2"]), fmt(x["peak_xs2"] / DIAG)))
        print("    peak |C''| (cam space, pre-distorted) %s mm/rad^2 "
              "at theta %s deg"
              % (fmt(x["peak_cpp"]), fmt(x["peak_cpp_theta"] * DEG)))
        print("    winding max Im(conj(c)C')/|c|^2 = %s (< 1 required)"
              % fmt(x["wind"]))
        print("    lever-output slot angle beta_out = %s deg "
              "(<= %s): %s"
              % (fmt(x["beta_deg"]), fmt(BETA_TARGET),
                 "PASS" if x["beta_ok"] else "FAIL"))
        print("    combined envelope bbox: x [%s, %s] (width %s), "
              "y [%s, %s] (height %s) -- swept discs about the shared "
              "shaft, slide box, pivot boss and lever sweep "
              "simultaneously; z-stack declared (the -05 axial-stack "
              "convention: plan-view overlap is packaging, not "
              "interference)"
              % (fmt(x["bbox"][0]), fmt(x["bbox"][1]), fmt(x["bbox_w"]),
                 fmt(x["bbox"][2]), fmt(x["bbox"][3]), fmt(x["bbox_h"])))
        print("    binding envelope component: the cam-y plate at its "
              "cap-limited operating point (radius %s mm); cam-x "
              "plate radius %s mm"
              % (fmt(x["plate_r_y"]), fmt(x["plate_r_x"])))
        print("    junction one-sided readings (alpha deg where "
              "defined / rho mm / slide-space h'' mm/rad^2):")

        def _a(v):
            return ("%6.2f" % v) if v is not None else "  n/a "
        for row in x["junctions"]:
            sa, sb = row["sides"]
            print("      %-48s th %6.2f  a %s/%s"
                  "  rho %9s/%9s  h'' %8.1f/%8.1f"
                  % (row["name"], row["theta_deg"], _a(sa["alpha"]),
                     _a(sb["alpha"]), fmt(sa["rho"]), fmt(sb["rho"]),
                     sa["xs2"], sb["xs2"]))
        print("    G2 VERDICT: %s" % x["g2_verdict"])
        if x["g2_verdict"].startswith("WIDE"):
            print("    TERMINAL BRANCH ENGAGED (frozen rule): no "
                  "further variant is staged; the finding returns to "
                  "the brief level with Jean")
        elif x["g2_verdict"].startswith("NARROW"):
            print("    NARROW BRANCH (frozen rule): a narrow fail "
                  "goes to the debate channel for an A-step-down / "
                  "Delta re-pick before any further job stages")
    else:
        print("  cam x: scan infeasible in the declared region -- "
              "G2 VERDICT: %s" % x["g2_verdict"])
        print("    TERMINAL BRANCH ENGAGED (frozen rule): no further "
              "variant is staged; the finding returns to the brief "
              "level with Jean")
    print()
    print("[D] Family-cost table (cam+lever vs recorded six-bar "
          "frontier)")
    f = SIXBAR_FRONTIER
    print("    gates: position %s, packaging overlay %s, orientation "
          "%s deg"
          % (f["gates"]["position"], f["gates"]["packaging_overlay"],
             f["gates"]["orientation_deg"]))
    for job, d in f.items():
        if job == "gates":
            continue
        print("    %s: best worst-sample position %s; accel %s"
              % (job, d["best_worst_position"], d["accel_mult"]))
    print("    recorded -05 Option A outcome (embedded data): cam x "
          "%s (worst alpha %s deg; required major %s mm at 30 deg / "
          "%s mm at 45 deg vs cap %s mm); cam y %s (worst alpha %s "
          "deg, required major %s mm inside the cap)"
          % (RECORD_05["cam_x_verdict"],
             fmt(RECORD_05["cam_x_worst_alpha"]),
             fmt(RECORD_05["cam_x_major_30"]),
             fmt(RECORD_05["cam_x_major_45"]),
             fmt(RECORD_05["cap"]), RECORD_05["cam_y_verdict"],
             fmt(RECORD_05["cam_y_worst_alpha"]),
             fmt(RECORD_05["cam_y_major_30"])))
    print("    structural attribution:")
    print("      six-bar misses: stops bind (worst samples at the")
    print("        process stops in every -01/-02/-04 run); levelness")
    print("        seed-dependent (T2 0.50-2.51 deg vs 1.5 deg")
    print("        tolerance); path straightness beyond the 12 samples")
    print("        unproven")
    print("      cam+lever features: stop velocity zero by the clamped")
    print("        timing; level orientation by construction (both")
    print("        slides translate); straightness inherited from the")
    print("        analytic path law; the x cam's demand pre-distorted")
    print("        through the exact lever map, synthesized in task")
    print("        space (the critic's continuity requirement)")
    if x.get("scan_feasible"):
        print("      junction derivative cost, slide space (normalized):")
        print("        peak |x_s''| %s (cam x, unchanged task demand;"
              " -05 recorded %s); cam y peak %s (vs six-bar worst accel"
              " ERROR 1.403-1.494 in -02; the demand itself peaked at"
              " 1.7767)"
              % (fmt(x["peak_xs2"] / DIAG),
                 fmt(RECORD_05["cam_x_peak_hpp_norm"]),
                 fmt(rep["cam_y"]["peak_hpp"] / DIAG)))
        print("        the lever's own pre-distorted cam-space demand:")
        print("          peak |C''| %s mm/rad^2 (data; the profile is"
              % fmt(x["peak_cpp"]))
        print("          manufactured to this, not to the slide law)")
        print("      lever additions (debate-adopted, data rows;")
        print("        forces and masses unrated):")
        print("        reflected inertia: slide mass at the cam scales")
        print("          as lambda_eff^2 = %s - %s"
              % (fmt(x["lambda_eff_min"] ** 2),
                 fmt(x["lambda_eff_max"] ** 2)))
        print("        tolerance amplification: cam-x profile error x")
        print("          lambda_eff = %s - %s at the slide (ties to"
              % (fmt(x["lambda_eff_min"]),
                 fmt(x["lambda_eff_max"])))
        print("          the queued profile-tolerance -> path-error")
        print("          mapping; the trigger is now armed: a G2 pass")
        print("          at a fine grid makes it non-trivial)")
        print("        per-unit-load shaft torque proxies (energy")
        print("          method, kinematic only): cam x peak |x_s'| ="
              " %s mm/rad; cam y peak |h_y'| = %s mm/rad"
              % (fmt(x["peak_xs1"]), fmt(rep["cam_y"]["peak_hp"])))
        print("        combined swept-envelope row: [C] bbox check")
        print("          (both plates + lever + slide box + boss,")
        print("          simultaneously, not per component)")
        edge = x["A"] - SCAN_A_COARSE[0]
        print("        pick-at-the-edge flag (the actor's rule): the")
        print("          largest workable A = %s mm sits %s mm above"
              " the declared range floor %s mm -- the pick is"
              % (fmt(x["A"]), fmt(edge), fmt(SCAN_A_COARSE[0])))
        print("          flagged, not clean: a smaller A buys angle")
        print("          but buys lambda_eff force/tolerance/inertia")
        print("          amplification beyond the flagged zone; the")
        print("          A floor is a debate-channel question, not a")
        print("          silent redeclaration")
    print("      parts: 2 plate cams + 2 roller followers + 1 pivoted")
    print("        slotted lever + pivot pin + 2 slides with guides +")
    print("        return springs, vs one six-bar (6 links, 7 pins);")
    print("        force closure: rise = pressure-angle problem,")
    print("        dwell/carry = static spring problem (the lever's")
    print("        force-closure re-derivation with the dwell-jump")
    print("        case is queued with this record; forces unrated")
    print("        here)")
    print()
    print("[E] Witnesses")
    sv = rep["stop_velocity"]
    print("    stop SLIDE velocity |x_s'|, cam x (audited at the")
    print("      slide, after the lever): theta 0: %s; theta 120: %s"
          " (exact zero by construction)" % (fmt(sv["x_theta_0"]),
                                              fmt(sv["x_theta_120"])))
    print("    stop follower velocity |h_y'|, cam y: theta 0: %s; "
          "theta 120: %s (exact zero by construction)"
          % (fmt(sv["y_theta_0"]), fmt(sv["y_theta_120"])))
    if "witness_pin" in rep:
        print("    round trip (emitted pitch curve -> rotation ->")
        print("      roller -> lever ray -> pin line -> slide): worst")
        print("      |pin_x - x_s| = %.3e mm over all %d grid points"
              " (float round-off only)" % (rep["witness_pin"], GRID_N))
        print("    task reproduction through the full chain (cam-x")
        print("      profile + lever + cam-y law): worst |dq| = %.3e"
              " normalized at the twelve phases (<= 1e-9 fail-closed)"
              % rep["witness_task_q"])
        print("    dwell-circle curvature witness: worst relative "
              "error %.3e (the x dwell arcs are exact concentric "
              "circles)" % rep["cam_x"]["dwell_err"])
    print("    level orientation: %s" % rep["level_orientation"])
    print("    determinism: %s" % rep["determinism"])
    print()
    print("[F] Scorecard reading (data, not exit codes)")
    print("    G1 task synthesis: construction verified by [A]/[E]")
    print("    G2 verdicts: cam x %s; cam y %s (carry-in)"
          % (rep["cam_x"]["g2_verdict"], rep["cam_y"]["g2_verdict"]))
    print("    G3 stop velocity: zero by construction at the slide,")
    print("      machine-checked")
    print("    G4 family-cost table: [D]")
    print("    G5 control: task file read-only (sha256 above); two-run")
    print("      determinism: %s" % rep["determinism"])
    print("    terminal branch (frozen): a cam-x wide fail ends the")
    print("      variant chain -- no further variant is staged; the")
    print("      finding returns to the brief level with Jean")
    print(line)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(
        description="Stage 1 deterministic design audit for "
                    "dualcam-lever-transfer-06 (pure stdlib, no network)")
    ap.add_argument("--task", default="jobs/sixbar-gap-transfer-02/"
                    "gap_transfer_nostops.motion.json",
                    help="frozen -02 task JSON (read-only)")
    args = ap.parse_args(argv)
    with open(args.task, "rb") as fh:
        task_bytes = fh.read()
    task = json.loads(task_bytes.decode("utf-8"))
    rep1 = build_report(args.task, task_bytes, task)
    rep2 = build_report(args.task, task_bytes, task)
    same = json.dumps(rep1, sort_keys=True) == json.dumps(rep2,
                                                          sort_keys=True)
    rep1["determinism"] = ("PASS (two independent full audits are "
                           "byte-identical)" if same else
                           "FAIL (audits differ)")
    print_report(rep1, args.task, sys.version.split()[0])
    w = rep1["task_validation"]
    task_ok = max(w["q"], w["v"], w["a"]) <= TASK_TOL
    wit_ok = True
    if "witness_pin" in rep1:
        wit_ok = (rep1["witness_pin"] <= PIN_TOL
                  and rep1["witness_task_q"] <= TASK_TOL
                  and rep1["cam_x"]["dwell_err"] <= DWELL_RHO_TOL)
    if not task_ok or not same or not wit_ok:
        print("FAIL-CLOSED VIOLATION: see above")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
