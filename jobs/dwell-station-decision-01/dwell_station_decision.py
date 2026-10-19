#!/usr/bin/env python3
"""
dwell_station_decision.py -- dwell-station-decision-01: the case study A
capability-to-spec/decision instrument (the decision round's folded record).

The decision (2026-10-19, relayed actor + critic rounds; Jean decides):
the LEVER instance line + tolerance zoning; the DIRECT + renegotiation
branch stays documented and live with its trigger (a real station footprint
measurement). This script executes the decision round's one blocking item --
restating the picked line's guaranteed dwell width at its zoned class --
through a DECLARED AMENDMENT of the recorded design: the recorded nominal
dwell arc is exactly 50.00 deg (the K2-derived allowance is 0.00), so
widening it is an amendment, never a restatement. The amendment takes the
declared-change discipline: frozen rule, reason, re-derived allocation, and
the headroom/curvature/junction table re-checked at the new pick.

Sections:
  [A] fail-closed reproduction of the recorded -01 oracle. The recorded
      design script is imported READ-ONLY from the sibling job directory,
      pinned by sha256 (public main b652b75e, the -01 run of record); its
      witnesses are recomputed and compared to the recorded values.
  [B] the declared width amendment under the frozen rule:
      w = (zero-error guaranteed width) - (zoned-class guaranteed width) of
      the un-biased recorded design at the WORST instance (band-hi), rounded
      UP to the 0.2 deg cycle-tiling multiple (never down: a bias must not
      under-deliver). Reason: the amendment converts tolerance-driven
      erosion of the hold window into nominal arc, so the >= 50 deg
      guarantee rests on the construction-exact arc, not on the rise
      margins (which vanish at the knee). The new nominal re-enters the
      frozen allocation rule (dwell arc + remainder proportional to
      stroke 130:130:260).
  [C] the restated duration guarantee (the blocking item): nominal vs
      guaranteed width at the zoned working class and at the knee, both
      lever instances; the demand check is fail-closed (the amendment
      exists to make it structural).
  [D] the re-checked headroom / curvature / junction table at the amended
      cycle (the -06 lesson: zero-headroom designs are caught at design
      time); the picked line's gates must remain HELD (fail-closed).
  [E] the tolerance derivation chain end to end, with the declared
      deferrals (pivot-joint class deferred with its trigger; the RSS
      convention reported alongside WC).
  [F] control.

Pure standard-library Python. Deterministic (in-process double-run check).
Fail-closed on its own witnesses and assertions; reported readings are data.
No OMTS vocabulary anywhere in this file or its output.
"""

import hashlib
import math
import os
import sys

EXIT_OK = 0
EXIT_FAIL_CLOSED = 2

# sha256 of the recorded design script at public main b652b75e (the -01 run
# of record consumed this exact file). Pinned so the consumption is provably
# read-only and byte-identical.
RECORDED_SHA256 = "0b4cbd63b2830f17c48e8eefd33d47a8dcb5f2aecafb532394c4b902f3a91406"

# The zoned working pick: a declared DEFAULT parameter, revisable at spec
# time with lineage. The BOUND is frozen at the recorded knees (see [E]).
ZONED_CLASS_MM = 0.05
# Cycle-tiling multiple: all four phase arcs must land on the 0.05 deg grid,
# so the dwell arc (and therefore the bias) must be a multiple of 0.2 deg.
TILE_DEG = 0.2


def fail_closed(msg):
    print("STRUCTURAL FAILURE (fail-closed): %s" % msg)
    sys.exit(EXIT_FAIL_CLOSED)


_HERE = os.path.dirname(os.path.abspath(__file__))
_SIBLING = os.path.join(_HERE, "..", "dwell-station-capability-01")

with open(os.path.join(_SIBLING, "dwell_station_design.py"), "rb") as _f:
    _got = hashlib.sha256(_f.read()).hexdigest()
if _got != RECORDED_SHA256:
    fail_closed("recorded design script sha256 mismatch: read-only consumption violated (got %s)" % _got)

sys.path.insert(0, _SIBLING)
import dwell_station_design as rec  # read-only, sha-pinned


def approx(name, got, want, tol):
    if abs(got - want) > tol:
        fail_closed("oracle mismatch: %s computed %.6f, recorded %.6f (tol %.6g)"
                    % (name, got, want, tol))


def derive_recorded_design():
    """The recorded allowance fixed point, reproduced through the recorded
    script's own machinery (same rule, same iteration cap)."""
    allowance = 0.0
    iters = 0
    while True:
        iters += 1
        if iters > 8:
            fail_closed("duration-allowance fixed point did not converge")
        ph = rec.build_phases(rec.DEMAND_DWELL_DEG + allowance)
        d, dp, dpp, meta = rec.synth(ph)
        slides = rec.slides_from_d(d)
        w = rec.guaranteed_dwell_width_deg(
            slides, meta["center_i"],
            rec.X_BUDGET_WC_MM - 1.0 * rec.PROFILE_CLASS_MM)
        new = max(0.0, rec.DEMAND_DWELL_DEG - w)
        if abs(new - allowance) < 1e-12:
            return allowance, ph, d, dp, dpp, meta, slides
        allowance = new


def junction_peaks(ph):
    j_dwell = 130.0 * (math.pi / math.radians(ph["app"])) ** 2 / 2.0
    j_ret = 260.0 * (math.pi / math.radians(ph["ret"])) ** 2 / 2.0
    return j_dwell, j_ret


def dwell_witness(slides, meta):
    wmax = 0.0
    for i in range(meta["dwell_lo_i"], meta["dwell_hi_i"] + 1):
        if abs(slides[i]) > wmax:
            wmax = abs(slides[i])
    return wmax


def build_report():
    L = []
    a = L.append
    a("dwell_station_decision: case study A capability-to-spec/decision (dwell-station-decision-01)")
    a("decision line: LEVER + tolerance zoning; direct + renegotiation documented as the live fallback with its trigger")
    a("read-only consumption: dwell_station_design.py sha256 %s (verified)" % RECORDED_SHA256)
    a("")

    # ------------------------------------------------------------------
    a("== [A] recorded-oracle reproduction (fail-closed) ==")
    allowance, ph, d, dp, dpp, meta, slides = derive_recorded_design()
    approx("duration allowance deg", allowance, 0.0, 1e-12)
    approx("approach arc deg", ph["app"], 77.50, 1e-9)
    approx("dwell arc deg", ph["dwell"], 50.00, 1e-9)
    approx("depart arc deg", ph["dep"], 77.50, 1e-9)
    approx("return arc deg", ph["ret"], 155.00, 1e-9)
    j_dwell, j_ret = junction_peaks(ph)
    approx("junction peak (dwell) mm/rad^2", j_dwell, 350.63, 0.005)
    approx("junction peak (return) mm/rad^2", j_ret, 175.32, 0.005)
    approx("dwell witness mm (recorded K1)", dwell_witness(slides, meta), 0.0, 0.0)
    approx("stroke witness mm (recorded K1)", max(d), 260.0, 1e-9)

    inst = [
        rec.evaluate_instance("direct (S=1)", 1.0, d, dp, dpp, slides, meta),
        rec.evaluate_instance("lever band-lo", rec.LAMBDA_LO, d, dp, dpp, slides, meta),
        rec.evaluate_instance("lever band-hi", rec.LAMBDA_HI, d, dp, dpp, slides, meta),
    ]
    direct, lo, hi = inst
    approx("direct major30 mm (K3)", direct["major30"], 464.44, 0.005)
    if direct["gate30"] != "WIDE-FAIL":
        fail_closed("oracle mismatch: direct gate30 is not WIDE-FAIL")
    approx("direct util30 %% (K3)", direct["util30"], 163.0, 0.05)
    approx("direct knee WC mm (K6)", direct["knee_wc"], 0.2000, 5e-5)
    approx("direct knee RSS mm (K6)", direct["knee_rss"], 0.2828, 5e-5)
    approx("direct guaranteed width at working class deg (K6)", direct["width_work"], 52.70, 0.005)
    approx("band-lo major30 mm (K4)", lo["major30"], 135.76, 0.005)
    approx("band-lo util30 %% (K4)", lo["util30"], 47.6, 0.05)
    approx("band-lo cap headroom mm (K4)", lo["cap_headroom"], 149.24, 0.005)
    approx("band-lo knee WC mm (K6)", lo["knee_wc"], 0.0585, 5e-5)
    approx("band-lo knee RSS mm (K6)", lo["knee_rss"], 0.0827, 5e-5)
    approx("band-lo guaranteed width at working class deg (K6)", lo["width_work"], 0.0, 1e-12)
    approx("band-hi major30 mm (K4)", hi["major30"], 119.92, 0.005)
    approx("band-hi util30 %% (K4)", hi["util30"], 42.1, 0.05)
    approx("band-hi cap headroom mm (K4)", hi["cap_headroom"], 165.08, 0.005)
    approx("band-hi knee WC mm (K6)", hi["knee_wc"], 0.0516, 5e-5)
    approx("band-hi knee RSS mm (K6)", hi["knee_rss"], 0.0730, 5e-5)
    approx("band-hi guaranteed width at working class deg (K6)", hi["width_work"], 0.0, 1e-12)
    wn_nom = rec.guaranteed_dwell_width_deg(slides, meta["center_i"], rec.X_BUDGET_WC_MM)
    approx("zero-error guaranteed width deg (instance-independent)", wn_nom, 53.80, 0.005)
    a("recorded oracle reproduced through the recorded machinery: allowance 0.00 deg; allocation 77.50/50.00/77.50/155.00 deg;")
    a("junction peaks %.2f / %.2f mm/rad^2; direct major %.2f mm WIDE-FAIL (163.0%%); lever majors %.2f / %.2f mm PASS;"
      % (j_dwell, j_ret, direct["major30"], lo["major30"], hi["major30"]))
    a("knees WC %.4f / %.4f / %.4f mm (direct / band-lo / band-hi); widths at the working class 52.70 / 0.00 / 0.00 deg -- all as recorded"
      % (direct["knee_wc"], lo["knee_wc"], hi["knee_wc"]))
    a("[A] PASS: the recorded -01 oracle reproduces fail-closed (no recorded value moved)")
    a("")

    # ------------------------------------------------------------------
    a("== [B] the declared width amendment (frozen rule, with its reason) ==")
    a("provenance (the critic's question, answered from the record): the recorded nominal dwell arc is exactly")
    a("50.00 deg (allowance 0.00 deg, reproduced in [A]) -- so restating the width is an AMENDMENT, not a restatement.")
    a("frozen rule: w = (zero-error guaranteed width) - (zoned-class guaranteed width) of the un-biased recorded")
    a("  design at the WORST instance (band-hi); w rounded UP to the %.1f deg cycle-tiling multiple (never down:" % TILE_DEG)
    a("  a bias must not under-deliver).")
    a("reason: the amendment converts tolerance-driven erosion of the hold window into nominal arc, so the")
    a("  >= 50 deg guarantee rests on the construction-exact arc, not on the rise margins, which vanish at the knee.")
    eff_hi_zoned = rec.X_BUDGET_WC_MM - rec.LAMBDA_HI * ZONED_CLASS_MM
    ww_hi_zoned = rec.guaranteed_dwell_width_deg(slides, meta["center_i"], eff_hi_zoned)
    w_raw = wn_nom - ww_hi_zoned
    w_bias = math.ceil(w_raw / TILE_DEG - 1e-9) * TILE_DEG
    if w_bias < w_raw - 1e-12:
        fail_closed("width bias rounded down (a bias must not under-deliver)")
    if w_bias <= 0.0:
        fail_closed("derived width bias is not positive")
    a("zero-error guaranteed width (un-biased): %.2f deg" % wn_nom)
    a("band-hi guaranteed width at the %.3f mm zoned class (un-biased): %.2f deg" % (ZONED_CLASS_MM, ww_hi_zoned))
    a("derived w_raw = %.2f - %.2f = %.2f deg -> w = %.2f deg (rounded up to the tile)" % (wn_nom, ww_hi_zoned, w_raw, w_bias))
    new_dwell = rec.DEMAND_DWELL_DEG + w_bias
    ph2 = rec.build_phases(new_dwell)
    d2, dp2, dpp2, meta2 = rec.synth(ph2)
    slides2 = rec.slides_from_d(d2)
    approx("amended dwell arc deg", ph2["dwell"], 53.20, 1e-9)
    approx("amended approach arc deg", ph2["app"], 76.70, 1e-9)
    approx("amended depart arc deg", ph2["dep"], 76.70, 1e-9)
    approx("amended return arc deg", ph2["ret"], 153.40, 1e-9)
    approx("amended dwell witness mm (K1-class)", dwell_witness(slides2, meta2), 0.0, 0.0)
    approx("amended stroke witness mm (K1-class)", max(d2), 260.0, 1e-9)
    if ZONED_CLASS_MM > lo["knee_wc"] or ZONED_CLASS_MM > hi["knee_wc"]:
        fail_closed("zoned working pick is outside a recorded knee (no WC guarantee exists)")
    a("amended cycle (frozen allocation rule re-entered): approach %.2f / dwell %.2f / depart %.2f / return %.2f deg"
      % (ph2["app"], ph2["dwell"], ph2["dep"], ph2["ret"]))
    j_dwell2, j_ret2 = junction_peaks(ph2)
    a("amended junction peaks: %.2f / %.2f mm/rad^2 (recorded: %.2f / %.2f; the price of the wider dwell arc: faster rises)"
      % (j_dwell2, j_ret2, j_dwell, j_ret))
    a("[B] PASS: the amendment is derived, not picked; the amended cycle passes the K1-class witnesses")
    a("")

    # ------------------------------------------------------------------
    a("== [C] the restated duration guarantee (the decision round's blocking item) ==")
    a("zoned working class %.3f mm (declared default, revisable at spec time with lineage; bound frozen at the knees)"
      % ZONED_CLASS_MM)
    w_knee = rec.guaranteed_dwell_width_deg(slides2, meta2["center_i"], 0.0)
    for nm, lam in (("band-lo", rec.LAMBDA_LO), ("band-hi", rec.LAMBDA_HI)):
        eff_work = rec.X_BUDGET_WC_MM - lam * ZONED_CLASS_MM
        w_work = rec.guaranteed_dwell_width_deg(slides2, meta2["center_i"], eff_work)
        if w_work < rec.DEMAND_DWELL_DEG:
            fail_closed("amended design fails the >= 50 deg demand at the zoned class (%s)" % nm)
        if w_knee < rec.DEMAND_DWELL_DEG:
            fail_closed("amended design fails the >= 50 deg demand at the knee")
        a("%s: nominal arc %.2f deg; guaranteed width at the zoned class %.2f deg; at the knee %.2f deg"
          % (nm, ph2["dwell"], w_work, w_knee))
    eff_direct_work = rec.X_BUDGET_WC_MM - 1.0 * rec.PROFILE_CLASS_MM
    w_direct_work = rec.guaranteed_dwell_width_deg(slides2, meta2["center_i"], eff_direct_work)
    a("(data, not the picked line: the direct instance on the amended cycle at the 0.10 mm working class: %.2f deg)"
      % w_direct_work)
    a("the >= 50 deg demand is met at EVERY profile class inside the knee: at the knee the margins vanish and the")
    a("guarantee is the construction-exact arc itself, %.2f deg = demand + %.2f deg of declared nominal margin"
      % (w_knee, w_knee - rec.DEMAND_DWELL_DEG))
    a("nominal-vs-guaranteed both reported (the actor's requirement); duration knee == position knee unchanged:")
    a("one tolerance realization serves both channels (the recorded finding, carried)")
    a("[C] PASS: the picked line's duration guarantee is a recorded number, fail-closed against the demand")
    a("")

    # ------------------------------------------------------------------
    a("== [D] re-checked headroom / curvature / junction table at the amended cycle ==")
    inst2 = [
        rec.evaluate_instance("direct (S=1)", 1.0, d2, dp2, dpp2, slides2, meta2),
        rec.evaluate_instance("lever band-lo", rec.LAMBDA_LO, d2, dp2, dpp2, slides2, meta2),
        rec.evaluate_instance("lever band-hi", rec.LAMBDA_HI, d2, dp2, dpp2, slides2, meta2),
    ]
    a("instance          major30_mm  util%    cap_head  gate30      major45_mm  gate45      pmax_deg  min_rho_mm  rho_margin")
    for r in inst2:
        a("%-16s %10.2f %6.1f %+9.2f  %-10s %10.2f  %-10s %9.2f %11.2f %11.2f" % (
            r["name"], r["major30"], r["util30"], r["cap_headroom"], r["gate30"],
            r["major45"], r["gate45"], r["pmax"], r["rho_min"], r["curv_margin"]))
    for r in inst2[1:]:
        if r["gate30"] != "PASS" or r["gate45"] != "PASS":
            fail_closed("amended cycle broke a picked-line gate: %s" % r["name"])
        if r["rho_min"] < rec.CURV_FLOOR_MM:
            fail_closed("amended cycle broke the curvature floor: %s" % r["name"])
    d2r = inst2[0]
    if d2r["gate30"] != "WIDE-FAIL":
        fail_closed("oracle expectation: the direct instance must still wide-fail the placeholder cap")
    a("the picked line (both lever instances) remains HELD at the 30 deg target AND the 45 deg hard gate, above the")
    a("curvature floor, with the headroom table re-checked at the amended pick (the -06 lesson, applied to ourselves)")
    a("[D] PASS: no recorded gate moved on the amended cycle; the direct line's wide-fail stands as data")
    a("")

    # ------------------------------------------------------------------
    a("== [E] tolerance derivation chain (visible end to end) and declared deferrals ==")
    a("chain: 0.3 mm hold region -> frozen WC split (passive guide class %.3f mm) -> x-budget %.3f mm"
      % (rec.GUIDE_CLASS_MM, rec.X_BUDGET_WC_MM))
    a("       -> S = lambda amplification -> required profile class (WC) = x-budget / lambda = the recorded knees:")
    a("          %.5f mm (band-lo) / %.5f mm (band-hi) -- the frozen bound; a property of the recorded design"
      % (lo["knee_wc"], hi["knee_wc"]))
    a("       -> working pick %.3f mm (declared default, revisable at spec time with lineage, guided by the knee curve;"
      % ZONED_CLASS_MM)
    a("          inside both knees, fail-closed in [B])")
    a("RSS convention reported alongside: x-budget sqrt(0.3^2 - 0.1^2) = %.4f mm; knees %.4f / %.4f mm (recorded)"
      % (rec.X_BUDGET_RSS_MM, lo["knee_rss"], hi["knee_rss"]))
    a("DEFERRED, declared, never silent: the pivot-joint class. The lever adds a pivot (clearance/backlash) and a")
    a("  roller-pin fit whose error term sits in the position budget like the guide's class does. Its share is not")
    a("  priced here; the deferral trigger is payload/grasp modeling, where rated forces and joint selection arrive")
    a("  together. The 0.3 mm region is NOT proven against profile error alone.")
    a("radial datum-bias lever (case-B lineage): recorded-and-unfired here -- its case-B trigger was zero cap")
    a("  headroom and the lever line has %+.2f / %+.2f mm; nothing to convert. Angular width-bias: FIRED, as the"
      % (lo["cap_headroom"], hi["cap_headroom"]))
    a("  declared amendment in [B], nominal-vs-guaranteed both reported in [C]. The two bias levers stay distinct.")
    a("class-to-spec mapping mirrors the offset_realization precedent: RECORDED, NEVER GATED -- the spec speaks in")
    a("  demand units (0.3 mm, 50 deg); the profile class is a realization record attached at build time.")
    a("")

    # ------------------------------------------------------------------
    a("== [F] control ==")
    a("cross-slide pair trigger (pinned): the pair returns ONLY if line architecture demands y-motion; the passive")
    a("  y-guide suffices for the single-axis task, and its class enters the 0.3 mm budget via the frozen split rule")
    a("  (visible in the budget, not just in prose).")
    a("fallback branch (live, with trigger): DIRECT + envelope renegotiation, triggered by a real station footprint")
    a("  measurement showing room. Physical realism on the record: the direct 464.44 mm major is a ~930 mm diameter")
    a("  plate; renegotiation would rescue the envelope, not the plate physics.")
    a("the recorded -01 outcome and its frozen K1-K8 scorecard are untouched; the recorded design was consumed")
    a("  read-only (sha256 witness at the top of this report).")
    a("the dwell-duration spec concept stays a recorded prediction for the spec step (claim-only-what-exists);")
    a("  no OMTS vocabulary is used in this study.")
    a("")
    a("dwell-station-decision-01: report complete; exit 0 (readings are data)")
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
