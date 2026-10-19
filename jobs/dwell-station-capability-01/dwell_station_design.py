#!/usr/bin/env python3
"""
dwell_station_design.py -- dwell-station-capability-01, Stage 1 capability design study.

Case study A (dwell station). The debate-adopted family is ONE x-axis cam with a
dwell arc at the station radius plus a PASSIVE y-guide at the carry plane (all
recorded poses are collinear at y = 50 mm; the cross-slide pair returns only
under a declared trigger). This script synthesizes the design, prices both
declared instances (direct follower; ideal-ratio lever at the recorded -06
lambda band), and emits the audit tables.

Pure standard-library Python. Deterministic (in-process double-run check).
Fail-closed on its own witnesses and assertions; wide-fail GATE readings are
reported data and still exit 0 (the -05 precedent: readings are data).

Units: lengths mm, interface angles degrees, derivatives per radian
(mm/rad, mm/rad^2). 1 normalized unit = 100 mm is used only to quote the
recorded four-bar reference numbers from the digest run of record.

Claim discipline: this script claims only what it computes. No OMTS
vocabulary anywhere in this file or its output.
"""

import math
import sys

EXIT_OK = 0
EXIT_FAIL_CLOSED = 2

# ---------------------------------------------------------------------------
# Frozen declarations (debate-adopted; see JOB.md for the debate record)
# ---------------------------------------------------------------------------

T1_X_MM = -130.0            # recorded task geometry, x-carry steps
STATION_X_MM = 0.0
T3_X_MM = 130.0
CARRY_Y_MM = 50.0           # carry plane: poses collinear, passive y-guide
HOLD_RADIUS_MM = 0.3        # station hold region radius (2D, frozen demand)
DEMAND_DWELL_DEG = 50.0     # held for >= 50 deg of crank cycle, crank turning

ROLLER_MM = 15.0
CURV_FLOOR_MM = 1.25 * ROLLER_MM          # 18.75 mm pitch-curve floor
PRESS_TARGET_DEG = 30.0                    # design pressure-angle target
PRESS_HARD_DEG = 45.0                      # hard ceiling
CAP_MAJOR_MM = 285.0                       # PLACEHOLDER cap, debate-declared, labeled

PROFILE_CLASS_MM = 0.10                    # working profile class
GUIDE_CLASS_MM = 0.10                      # passive-guide class (WC share)

GRID_DEG = 0.05                           # mirrors the digest grid
N_SAMPLES = 7200                          # unique samples; 360.0 deg wraps

LAMBDA_LO = 3.42105                       # recorded -06 lever ratio band
LAMBDA_HI = 3.87307

X_BUDGET_WC_MM = HOLD_RADIUS_MM - GUIDE_CLASS_MM          # 0.20 (WC split, frozen)
X_BUDGET_RSS_MM = math.sqrt(HOLD_RADIUS_MM**2 - GUIDE_CLASS_MM**2)  # ~0.2828 (reported)

# Recorded four-bar reference numbers (digest run of record, PR #63 outcome;
# run root runs/dwell-station-failure-01/.../2026-10-18_22-10-36_210120).
# Speeds in normalized units per degree; conversion to mm/rad: * 100 * (180/pi).
REC4B_STILL_NORM = 0.611071               # pool-min station radius (61.1071 mm)
REC4B_FREE_NORM = 0.278531                 # pool-min free radius (27.8531 mm)
REC4B_ST_SPEED_MIN = 2.118474e-02         # best station-window min speed
REC4B_ST_SPEED_MAX = 4.045675e-02
REC4B_FREE_SPEED_MIN = 9.940107e-03       # best free-window min speed
REC4B_FREE_SPEED_MAX = 1.737120e-02
NORM_DEG_TO_MM_RAD = 100.0 * (180.0 / math.pi)


def fail_closed(msg):
    print("STRUCTURAL FAILURE (fail-closed): %s" % msg)
    sys.exit(EXIT_FAIL_CLOSED)


# ---------------------------------------------------------------------------
# Synthesis: half-cosine motion phases over the grid
# ---------------------------------------------------------------------------

def build_phases(dwell_deg):
    """Cycle from T1: approach rise, dwell arc, depart rise, return fall.
    Allocation rule (frozen): dwell = 50 deg + duration allowance; the
    remainder is split proportional to stroke (130 : 130 : 260)."""
    rem = 360.0 - dwell_deg
    app = rem / 4.0          # stroke 130 of 520
    dep = rem / 4.0          # stroke 130 of 520
    ret = rem / 2.0          # stroke 260 of 520
    return {"dwell": dwell_deg, "app": app, "dep": dep, "ret": ret}


def synth(ph):
    """Return (d, dp, dpp, meta) arrays over the 7200-sample grid.
    d = cam-side displacement in mm, d(0)=0 at T1, dwell plateau at 130,
    max 260 at T3, back to 0 at cycle end. Derivatives per radian.
    Slide position = d - 130 (x in mm relative to station)."""
    dwell, app, dep, ret = ph["dwell"], ph["app"], ph["dep"], ph["ret"]
    # Grid bookkeeping (fail-closed assertions)
    if abs(N_SAMPLES * GRID_DEG - 360.0) > 1e-9:
        fail_closed("grid does not tile the cycle")
    if abs(app + dep + ret + dwell - 360.0) > 1e-9:
        fail_closed("phases do not sum to 360 deg")
    n_app = int(round(app / GRID_DEG))
    n_dwell = int(round(dwell / GRID_DEG))
    n_dep = int(round(dep / GRID_DEG))
    if (n_app + n_dep + n_dwell) != N_SAMPLES - int(round(ret / GRID_DEG)):
        fail_closed("phase sample counts do not tile the grid")

    d = [0.0] * N_SAMPLES
    dp = [0.0] * N_SAMPLES
    dpp = [0.0] * N_SAMPLES
    pi_over = math.pi

    # approach: [0, app), rise 0 -> 130
    T = math.radians(app)
    for i in range(n_app):
        u = (i * GRID_DEG) / app
        c = math.cos(pi_over * u)
        s = math.sin(pi_over * u)
        d[i] = 130.0 * (1.0 - c) / 2.0
        dp[i] = 130.0 * (pi_over / T) * s / 2.0
        dpp[i] = 130.0 * (pi_over / T) ** 2 * c / 2.0
    # dwell: [app, app+dwell], flat 130 (inclusive of both boundary samples)
    for i in range(n_app, n_app + n_dwell + 1):
        d[i] = 130.0
        dp[i] = 0.0
        dpp[i] = 0.0
    # depart: (app+dwell, app+dwell+dep], rise 130 -> 260
    Td = math.radians(dep)
    for i in range(n_app + n_dwell + 1, n_app + n_dwell + 1 + n_dep):
        th = i * GRID_DEG
        u = (th - (app + dwell)) / dep
        c = math.cos(pi_over * u)
        s = math.sin(pi_over * u)
        d[i] = 130.0 + 130.0 * (1.0 - c) / 2.0
        dp[i] = 130.0 * (pi_over / Td) * s / 2.0
        dpp[i] = 130.0 * (pi_over / Td) ** 2 * c / 2.0
    # return: (app+dwell+dep, 360), fall 260 -> 0 (u=1 lands on index 0 next cycle)
    Tr = math.radians(ret)
    n_ret = N_SAMPLES - (n_app + n_dwell + 1 + n_dep)
    for k in range(n_ret):
        i = n_app + n_dwell + 1 + n_dep + k
        th = i * GRID_DEG
        u = (th - (app + dwell + dep)) / ret
        c = math.cos(pi_over * u)
        s = math.sin(pi_over * u)
        d[i] = 260.0 - 260.0 * (1.0 - c) / 2.0
        dp[i] = -260.0 * (pi_over / Tr) * s / 2.0
        dpp[i] = -260.0 * (pi_over / Tr) ** 2 * c / 2.0

    meta = {
        "n_app": n_app, "n_dwell": n_dwell, "n_dep": n_dep, "n_ret": n_ret,
        "center_i": n_app + n_dwell // 2,
        "dwell_lo_i": n_app, "dwell_hi_i": n_app + n_dwell,
        "ph": ph,
    }
    return d, dp, dpp, meta


def slides_from_d(d):
    return [x - 130.0 for x in d]


# ---------------------------------------------------------------------------
# Audit primitives
# ---------------------------------------------------------------------------

def guaranteed_dwell_width_deg(slides, center_i, eff_budget):
    """Width (deg) of the contiguous run containing the dwell center where
    |slide| <= eff_budget. Width convention: (last - first) qualifying sample
    times GRID_DEG (endpoint samples inclusive). Returns 0.0 if the center
    itself does not qualify."""
    if eff_budget < 0.0 or abs(slides[center_i]) > eff_budget:
        return 0.0
    lo = center_i
    while lo > 0 and abs(slides[lo - 1]) <= eff_budget:
        lo -= 1
    hi = center_i
    while hi < N_SAMPLES - 1 and abs(slides[hi + 1]) <= eff_budget:
        hi += 1
    return (hi - lo) * GRID_DEG


def required_base_radius(c, cp, target_deg):
    """Minimal r_base such that max |c'|/r <= tan(target) over the grid."""
    t = math.tan(math.radians(target_deg))
    rb = max(cp_i / t - c_i for c_i, cp_i in zip(c, cp))
    return max(rb, 1e-9)


def max_pressure_deg(c, cp, rb):
    m = 0.0
    for c_i, cp_i in zip(c, cp):
        r = rb + c_i
        if r <= 0.0:
            return 90.0
        a = math.degrees(math.atan(abs(cp_i) / r))
        if a > m:
            m = a
    return m


def min_abs_rho(c, cp, cpp, rb):
    """Min over the grid of |rho| for the polar pitch curve
    rho = (r^2 + r'^2)^(3/2) / (r^2 + 2 r'^2 - r r'')."""
    best = float("inf")
    best_i = -1
    for i in range(N_SAMPLES):
        r = rb + c[i]
        rp = cp[i]
        rpp = cpp[i]
        num = (r * r + rp * rp) ** 1.5
        den = r * r + 2.0 * rp * rp - r * rpp
        if den == 0.0:
            rho = float("inf")
        else:
            rho = num / den
        ar = abs(rho)
        if ar < best:
            best = ar
            best_i = i
    return best, best_i


# ---------------------------------------------------------------------------
# Instance evaluation
# ---------------------------------------------------------------------------

def evaluate_instance(name, S, d, dp, dpp, slides, meta):
    """S = slide displacement per unit profile error (=1 direct, =lambda lever).
    Cam-side arrays c = d / S for the lever (ideal-ratio model, declared
    simplification: the lever's own geometry audit is a follow-on job if this
    instance is picked)."""
    c = [x / S for x in d]
    cp = [x / S for x in dp]
    cpp = [x / S for x in dpp]
    max_c = max(c)

    rb30 = required_base_radius(c, cp, PRESS_TARGET_DEG)
    rb45 = required_base_radius(c, cp, PRESS_HARD_DEG)
    major30 = rb30 + max_c
    major45 = rb45 + max_c
    util30 = 100.0 * major30 / CAP_MAJOR_MM
    pmax = max_pressure_deg(c, cp, rb30)
    rho_min, rho_i = min_abs_rho(c, cp, cpp, rb30)

    # Tolerance knees (position; = duration knee, see finding below)
    knee_wc = X_BUDGET_WC_MM / S
    knee_rss = X_BUDGET_RSS_MM / S
    class_verdict_wc = "PASS" if PROFILE_CLASS_MM <= knee_wc else "FAIL"
    class_verdict_rss = "PASS" if PROFILE_CLASS_MM <= knee_rss else "FAIL"
    required_class_wc = knee_wc

    # Duration: guaranteed dwell width at the working class, and at the knee
    eff_work = X_BUDGET_WC_MM - S * PROFILE_CLASS_MM
    width_work = guaranteed_dwell_width_deg(slides, meta["center_i"], eff_work)
    width_nominal = guaranteed_dwell_width_deg(slides, meta["center_i"], X_BUDGET_WC_MM)

    return {
        "name": name, "S": S, "c": c, "cp": cp, "cpp": cpp,
        "rb30": rb30, "rb45": rb45, "major30": major30, "major45": major45,
        "util30": util30, "pmax": pmax, "rho_min": rho_min, "rho_i": rho_i,
        "knee_wc": knee_wc, "knee_rss": knee_rss,
        "class_wc": class_verdict_wc, "class_rss": class_verdict_rss,
        "req_class_wc": required_class_wc,
        "width_work": width_work, "width_nominal": width_nominal,
        "cap_headroom": CAP_MAJOR_MM - major30,
        "gate30": "PASS" if major30 <= CAP_MAJOR_MM else "WIDE-FAIL",
        "gate45": "PASS" if major45 <= CAP_MAJOR_MM else "WIDE-FAIL",
        "press_margin_hard": PRESS_HARD_DEG - pmax,
        "curv_margin": rho_min - CURV_FLOOR_MM,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report():
    L = []
    a = L.append
    a("dwell_station_design: case study A capability study (dwell-station-capability-01)")
    a("family: one x-axis cam + passive y-guide at the carry plane (debate-adopted)")
    a("")
    a("== frozen declarations ==")
    a("task geometry: T1/station/T3 x = %.1f / %.1f / %.1f mm at carry plane y = %.1f mm (poses collinear)" % (T1_X_MM, STATION_X_MM, T3_X_MM, CARRY_Y_MM))
    a("demand: hold inside %.3f mm at the station for >= %.2f deg of crank cycle while the crank keeps turning" % (HOLD_RADIUS_MM, DEMAND_DWELL_DEG))
    a("cam data: roller %.2f mm; pitch-curve curvature floor %.2f mm (1.25x roller)" % (ROLLER_MM, CURV_FLOOR_MM))
    a("pressure-angle: target %.1f deg, hard ceiling %.1f deg" % (PRESS_TARGET_DEG, PRESS_HARD_DEG))
    a("cap: %.1f mm major radius = DEBATE-DECLARED PLACEHOLDER (labeled, never derived)" % CAP_MAJOR_MM)
    a("classes: profile %.3f mm working; passive guide %.3f mm working" % (PROFILE_CLASS_MM, GUIDE_CLASS_MM))
    a("grid: %d unique samples at %.2f deg (mirrors the digest grid); wrap at 360.00 deg" % (N_SAMPLES, GRID_DEG))
    a("lever band: lambda = %.5f .. %.5f (recorded -06 ratio band; ideal-ratio model, declared simplification)" % (LAMBDA_LO, LAMBDA_HI))
    a("budget split (frozen, declared up front): WC x-budget = %.3f - %.3f = %.3f mm; RSS x-budget = sqrt(0.3^2 - 0.1^2) = %.4f mm (reported alongside)" % (HOLD_RADIUS_MM, GUIDE_CLASS_MM, X_BUDGET_WC_MM, X_BUDGET_RSS_MM))
    a("sensitivity rule: slide error = S * profile error; S = 1 (direct), S = lambda (lever). Guide class is the y share and is not multiplied.")
    a("")
    a("== duration allowance derivation (declared rule, fixed point) ==")
    a("rule: allowance = max(0, %.1f deg - guaranteed dwell width of the DIRECT instance at the working class)" % DEMAND_DWELL_DEG)
    allowance = 0.0
    iters = 0
    ph = None
    d = dp = dpp = meta = None
    while True:
        iters += 1
        if iters > 8:
            fail_closed("duration-allowance fixed point did not converge")
        ph = build_phases(DEMAND_DWELL_DEG + allowance)
        d, dp, dpp, meta = synth(ph)
        slides = slides_from_d(d)
        w = guaranteed_dwell_width_deg(slides, meta["center_i"], X_BUDGET_WC_MM - 1.0 * PROFILE_CLASS_MM)
        new_allowance = max(0.0, DEMAND_DWELL_DEG - w)
        a("  iter %d: dwell arc %.2f deg -> guaranteed width at working class %.2f deg -> allowance %.2f deg" % (iters, ph["dwell"], w, new_allowance))
        if abs(new_allowance - allowance) < 1e-12:
            break
        allowance = new_allowance
    a("converged: design dwell arc = %.2f deg (%.1f deg demand + %.2f deg declared duration allowance)" % (ph["dwell"], DEMAND_DWELL_DEG, allowance))
    a("asserted at run time: dwell arc = %d intervals = %d samples = %.2f deg" % (meta["n_dwell"], meta["n_dwell"] + 1, ph["dwell"]))
    a("")
    a("== cycle allocation (declared rule: remainder split proportional to stroke 130:130:260) ==")
    a("approach rise  -130 -> 0 mm : %8.2f deg (%d samples)" % (ph["app"], meta["n_app"]))
    a("dwell arc      hold at 0 mm : %8.2f deg (%d samples)" % (ph["dwell"], meta["n_dwell"] + 1))
    a("depart rise      0 -> +130 : %8.2f deg (%d samples)" % (ph["dep"], meta["n_dep"]))
    a("return fall     +130 -> -130: %8.2f deg (%d samples)" % (ph["ret"], meta["n_ret"]))
    a("motion program: half-cosine per moving phase (C1 in slide space at every junction; junction derivative peaks reported below)")
    slides = slides_from_d(d)
    j_dwell = 130.0 * (math.pi / math.radians(ph["app"])) ** 2 / 2.0
    j_ret = 260.0 * (math.pi / math.radians(ph["ret"])) ** 2 / 2.0
    a("junction slide acceleration peaks (analytic, mm/rad^2): %.2f at dwell junctions, %.2f at return junctions" % (j_dwell, j_ret))
    a("")
    a("== K1 witnesses (executed, not asserted; fail-closed) ==")
    wmax = 0.0
    for i in range(meta["dwell_lo_i"], meta["dwell_hi_i"] + 1):
        if abs(slides[i]) > wmax:
            wmax = abs(slides[i])
    if wmax != 0.0:
        fail_closed("dwell witness: max |slide| over the arc is not exactly zero")
    a("dwell witness: max |slide| over the %d-sample dwell arc (boundaries included) = %.6f mm -- exactly zero" % (meta["n_dwell"] + 1, wmax))
    # the last sample sits 0.05 deg short of the wrap; the half-cosine return
    # lands within its analytic end value 260*(pi*eps)^2/4 of T1 there
    wrap_bound = 260.0 * (math.pi * math.radians(GRID_DEG) / math.radians(ph["ret"])) ** 2 / 4.0
    if abs(d[0]) > 1e-12 or abs(d[N_SAMPLES - 1]) > 4.0 * wrap_bound:
        fail_closed("cycle wrap witness: d(0) / d(360-) not at T1")
    a("cycle wrap witness: d(0) = %.6f mm at T1; d(359.95 deg) = %.6f mm, within the analytic end value %.6f mm of the half-cosine return (grid construction; d is exactly 0 at the 360 deg wrap)" % (d[0], d[N_SAMPLES - 1], wrap_bound))
    if abs(max(d) - 260.0) > 1e-9:
        fail_closed("stroke witness: max displacement is not 260 mm")
    a("stroke witness: max displacement = %.6f mm (= 260 mm total x-stroke; honest consequence: NOT a smaller cam problem than case B, only a gentler timing problem)" % max(d))
    a("")
    a("== instances (both evaluated on the same family cycle) ==")
    inst = []
    inst.append(evaluate_instance("direct (S=1)", 1.0, d, dp, dpp, slides, meta))
    inst.append(evaluate_instance("lever (lambda=%.5f, band lo)" % LAMBDA_LO, LAMBDA_LO, d, dp, dpp, slides, meta))
    inst.append(evaluate_instance("lever (lambda=%.5f, band hi)" % LAMBDA_HI, LAMBDA_HI, d, dp, dpp, slides, meta))
    for r in inst:
        a("-- instance: %s --" % r["name"])
        a("   required base radius: %.2f mm at %.0f deg target, %.2f mm at %.0f deg hard" % (r["rb30"], PRESS_TARGET_DEG, r["rb45"], PRESS_HARD_DEG))
        a("   required major radius: %.2f mm at %.0f deg (%s vs %.1f mm placeholder cap, utilization %.1f%%); %.2f mm at %.0f deg (%s)" % (r["major30"], PRESS_TARGET_DEG, r["gate30"], CAP_MAJOR_MM, r["util30"], r["major45"], PRESS_HARD_DEG, r["gate45"]))
        a("   pressure angle at the %.0f deg design: max %.2f deg (margin %.2f deg to the %.0f deg hard ceiling)" % (PRESS_TARGET_DEG, r["pmax"], r["press_margin_hard"], PRESS_HARD_DEG))
        a("   pitch-curve min |rho|: %.2f mm at sample %d (floor %.2f mm; margin %.2f mm)" % (r["rho_min"], r["rho_i"], CURV_FLOOR_MM, r["curv_margin"]))
        a("   cap headroom at the %.0f deg design: %+.2f mm" % (PRESS_TARGET_DEG, r["cap_headroom"]))
        a("   tolerance knee (WC): %.4f mm profile class; (RSS): %.4f mm" % (r["knee_wc"], r["knee_rss"]))
        a("   working-class verdict: %s at %.3f mm (WC), %s (RSS); required class (WC guarantee) = %.4f mm" % (r["class_wc"], PROFILE_CLASS_MM, r["class_rss"], r["req_class_wc"]))
        a("   guaranteed dwell width: %.2f deg at the working class (nominal %.2f deg at zero profile error; demand %.2f deg)" % (r["width_work"], r["width_nominal"], DEMAND_DWELL_DEG))
        a("")
    a("== duration finding (recorded as a finding, not a gate) ==")
    a("the guaranteed-dwell width collapses discontinuously once S*delta > %.3f mm: at the knee the width is the flat arc itself (%.2f deg, slide exactly 0), beyond it the dwell center leaves the region and the width is 0. Duration knee == position knee for every instance: the duration demand adds no gate beyond the position demand, PROVIDED the profile class is inside the knee." % (X_BUDGET_WC_MM, ph["dwell"]))
    a("")
    a("== headroom / utilization table (required audit output; the -06 lesson institutionalized) ==")
    a("instance                        major_mm   util%   cap_head   pmax_deg   hard_margin   min_rho   rho_margin")
    for r in inst:
        a("%-30s %9.2f %6.1f %+10.2f %9.2f %12.2f %9.2f %11.2f" % (
            r["name"], r["major30"], r["util30"], r["cap_headroom"],
            r["pmax"], r["press_margin_hard"], r["rho_min"], r["curv_margin"]))
    a("all rows at the %.0f deg design point (bisected required base radius); a zero-headroom design is caught here at design time, not in an endgame" % PRESS_TARGET_DEG)
    a("")
    a("== family-cost table vs the recorded four-bar frontier ==")
    a("metric                          four-bar frontier (recorded)      cam family (this design)")
    a("station stillness               %.3f mm best of pool              0.000 mm (construction-exact, witnessed)" % (REC4B_STILL_NORM * 100.0))
    a("best quiet-region wander        %.3f mm (cannot place apex)       0.000 mm during the dwell arc" % (REC4B_FREE_NORM * 100.0))
    a("min window speed                %.1f - %.1f mm/rad (st/free)      0.000 mm/rad during the dwell arc" % (REC4B_FREE_SPEED_MIN * NORM_DEG_TO_MM_RAD, REC4B_ST_SPEED_MAX * NORM_DEG_TO_MM_RAD))
    a("junction acceleration           not recorded by the digest        %.1f mm/rad^2 dwell junctions, %.1f return (C1 blending, declared)" % (j_dwell, j_ret))
    a("recorded four-bar numbers quoted from the digest run of record (PR #63 outcome); no frontier acceleration exists to compare against -- reported as data, not scored")
    a("")
    a("== T4 manufacturing-readiness classification (pre-declared, carried over) ==")
    a("a budget miss at nominal-passing geometry = a manufacturing-readiness finding with terminal branches: zoning preferred, envelope renegotiation as fallback, never a fifth variant")
    a("reading key: DIRECT instance misses the envelope at the placeholder cap at BOTH 30 and 45 deg (envelope finding; zoning or renegotiation); LEVER instance fits the envelope with real margin but requires profile class 0.052-0.058 mm, tighter than the 0.10 mm working class and tighter than case B's 0.068 mm (tolerance finding)")
    a("datum-bias lever (pre-declared, named): inward-biasing the dwell arc converts cap headroom into a calibratable datum offset -- declared as a design lever up front, never a post-hoc rescue")
    a("the cap is a labeled placeholder, so the renegotiation branch has cleaner standing than case B's did; zoning still ranks first (changes nothing declared; the tight class lands on the easiest geometry)")
    a("")
    a("== control ==")
    a("cross-slide pair trigger (declared): returns ONLY if line architecture demands y-motion (return path or station clearance) -- same scope line that keeps Geneva out")
    a("dwell-duration spec concept: stays a recorded prediction for the capability-to-spec step; no OMTS vocabulary is used in this study")
    a("synthesized timing is a declared design parameter (datum-bias class of choice), recorded with its derivation above")
    a("wide-fail gate readings are data, never gate loosening; predictions were frozen before the run of record (see JOB.md)")
    a("")
    a("dwell-station-capability-01: report complete; exit 0 (readings are data)")
    return "\n".join(L) + "\n"


def main():
    r1 = build_report()
    r2 = build_report()
    if r1 != r2:
        print(r1)
        fail_closed("double-run determinism check: reports differ")
    sys.stdout.write(r1)
    sys.stdout.write("double-run determinism check: IDENTICAL\n")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
