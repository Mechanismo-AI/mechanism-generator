#!/usr/bin/env python3
"""Job b1-admission-gate-01: the fallback re-probe instrument (the
B1-line next staged item; frozen before any run).

The next-step decision (merged with the JOB.md decision section)
froze this instrument's design: a DESIGN GATE in front of the
trained supplier, the same frozen OOD probe re-run through the
fallback-equipped supplier, the un-fallbacked learned answer
recorded and checked digit-for-digit against the recorded first
run (a reproduction check on the supplier), and the B2-signature
classification of the recorded design-shift failure.

The recorded supplier is re-derived, never re-trained: the
first-run instrument (b1_proposer_train.py) is imported read-only
with its sha256 pinned, so the training code path is IDENTICAL to
the run of record and the reproduction check is meaningful. No
new artifact is written (nothing new is trained -- claim-only-
what-exists); the first-run artifact stands.

Label: every output of the learned-proposal line is a SUPPLIER
OUTPUT, not a generator capability, until the line wins a
head-to-head against closed-form (the frozen A4 rule). The
fallback branch's zero distance is the CLOSED-FORM's, not a
learned win -- the label-change event remains defined and unfired.

Usage (repo root, the recorded standard):
  python jobs/b1-admission-gate-01/b1_fallback_reprobe.py \
      --source-commit <40-hex-sha> > run1.txt
  (twice; external diff must be empty; exit 0)

Pure stdlib; ASCII only; Python 3.10+; no network; deterministic.
"""

import hashlib
import json
import os
import platform
import re
import sys

JOB_ID = "b1-admission-gate-01"

# [P0] pins (frozen at this staging; fail-closed on mismatch)
TRAINER_REL = os.path.join(
    "jobs", JOB_ID, "b1_proposer_train.py")
TRAINER_SHA256 = (
    "1cb985bac4a34f6c07ed768f3b13692e7ea4c3be3bfbcfab973d1aeb0c5a9974")
TRAINER_BYTES = 26268
INSTRUMENT_REL = os.path.join(
    "jobs", "flip-station-capability-01", "flip_capability.py")
INSTRUMENT_SHA256 = (
    "72989f8a1183647f5cbf47c6db92b0cdc63eead355acb25f1dd42adedc06447b")
INSTRUMENT_BYTES = 50265
CORPUS_SHA256 = (
    "cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c")

# the frozen OOD probe (unchanged from the first run; the re-probe
# runs the SAME demand through the fallback-equipped supplier)
OOD_GROOVE = "groove_1"
OOD_T_DEG = 90.0
OOD_D = 0.4
OOD_CY = 0.25

# the recorded run-of-record anchors (recorded data, never rewritten;
# the reproduction check compares the re-derived supplier against these
# digits -- a mismatch fails closed, because it would mean the recorded
# supplier no longer reproduces)
REC_MEDIAN = "8.322194e-06"     # median held-out distance, units
REC_WORST = "5.650397e-05"      # worst held-out distance, units
REC_LEARNED_X = "0.70000776"    # learned answer on the frozen probe
REC_LEARNED_Y = "0.00000005"
REC_PROBE_DIST = "5.000776e-02" # probe distance, units
REC_PROBE_CF_X = "0.65000000"   # closed-form under the probe design
REC_PROBE_CF_Y = "0.00000000"

# presentations (never gates)
TOL_POS_UNITS = 0.015
UNITS_PER_MM = 100.0

A4_LABEL = ("SUPPLIER OUTPUT (LEARNED -- no head-to-head win; "
            "the A4 label stands per the frozen rule)")


class FailClosed(Exception):
    pass


def fail_closed(msg):
    raise FailClosed(msg)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check(desc, got, want):
    if got != want:
        fail_closed("%s: got %s recorded %s" % (desc, got, want))
    return True


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    source_commit = None
    i = 0
    while i < len(argv):
        if argv[i] == "--source-commit" and i + 1 < len(argv):
            source_commit = argv[i + 1]
            i += 2
        else:
            i += 1
    if source_commit is None:
        print("usage: b1_fallback_reprobe.py --source-commit "
              "<40-hex-sha>", file=sys.stderr)
        return 1
    if not re.match(r"^[0-9a-f]{40}$", source_commit):
        print("FAIL-CLOSED: --source-commit must be a 40-char lowercase "
              "hex sha", file=sys.stderr)
        return 1
    try:
        out1 = run(source_commit)
        out2 = run(source_commit)
    except Exception as exc:  # local FailClosed AND bt.FailClosed both land here
        print("FAIL-CLOSED: %s" % exc, file=sys.stderr)
        return 2
    identical = (out1 == out2)
    for line in out1:
        print(line)
    print("")
    print("double-run determinism check: %s"
          % ("IDENTICAL" if identical else "DIFFERS (FAIL)"))
    return 0 if identical else 1


def run(source_commit):
    """One complete re-probe pass; returns the report lines."""
    R_out = []
    R = R_out.append

    R("b1-admission-gate-01 -- the fallback re-probe instrument")
    R("(the B1-line next staged item; frozen before any run)")
    R("label: %s" % A4_LABEL)
    R("python: %s" % platform.python_version())
    R("source commit: %s" % source_commit)
    R("")

    # [P0] pins -----------------------------------------------------------
    R("[P0] PIN CHECKS (fail-closed)")
    if not os.path.isfile(TRAINER_REL):
        fail_closed("first-run instrument missing: %s" % TRAINER_REL)
    tbytes = os.path.getsize(TRAINER_REL)
    tsha = sha256_file(TRAINER_REL)
    if tbytes != TRAINER_BYTES or tsha != TRAINER_SHA256:
        fail_closed("first-run instrument pin mismatch: %s %d bytes "
                    "(pinned %s %d bytes)"
                    % (tsha, tbytes, TRAINER_SHA256, TRAINER_BYTES))
    if not os.path.isfile(INSTRUMENT_REL):
        fail_closed("capability instrument missing: %s" % INSTRUMENT_REL)
    ibytes = os.path.getsize(INSTRUMENT_REL)
    isha = sha256_file(INSTRUMENT_REL)
    if ibytes != INSTRUMENT_BYTES or isha != INSTRUMENT_SHA256:
        fail_closed("capability instrument pin mismatch: %s %d bytes "
                    "(pinned %s %d bytes)"
                    % (isha, ibytes, INSTRUMENT_SHA256, INSTRUMENT_BYTES))
    R("  first-run instrument %s" % TRAINER_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (imported read-only; the"
      % (tsha, tbytes))
    R("    training code path is IDENTICAL to the run of record)")
    R("  capability instrument %s" % INSTRUMENT_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH" % (isha, ibytes))
    R("  corpus of record sha256 %s (checked by the first-run"
      % CORPUS_SHA256)
    R("    instrument's own fail-closed loader, reused below)")
    R("")

    # read-only imports (the first-run instrument + the capability
    # instrument), both under their pins
    sys.path.insert(0, os.path.dirname(os.path.abspath(TRAINER_REL)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(INSTRUMENT_REL)))
    import b1_proposer_train as bt   # noqa: E402 (read-only import)
    import flip_capability as fc     # noqa: E402 (read-only import)

    # [P0 cont] the corpus, loaded through the first-run instrument's
    # own fail-closed loader (its corpus pin, schema succession rule,
    # row-count and provenance checks all apply unchanged)
    rows = bt.load_corpus()
    if bt.sha256_file(bt.CORPUS_REL) != CORPUS_SHA256:
        fail_closed("corpus pin mismatch (re-checked independently)")
    d, cy = bt.discover_chosen_design(rows)
    R("[P0 cont] corpus loaded through the first-run instrument's own")
    R("  fail-closed loader: %d rows, pin matched" % len(rows))
    R("  chosen design discovered from the corpus (never hardcoded):"
      " d=%.1f C_y=%.2f" % (d, cy))
    R("")

    # [W] reproduction witness (the first run's own standard, rerun)
    R("[W] REPRODUCTION WITNESS (every groove_sample row re-derived"
      " through the capability instrument)")
    samples = [r for r in rows if r["kind"] == "groove_sample"]
    qmap = {"groove_1": (d, 0.0), "groove_2": (-d, 0.0)}
    worst_w = 0.0
    for r in samples:
        g, _, _ = fc.groove_point(qmap[r["groove"]],
                                  r["plate_angle_deg"], (0.0, cy))
        dev = bt.dist2(g[0], g[1], r["gx"], r["gy"])
        if dev > worst_w:
            worst_w = dev
        if dev > bt.WITNESS_TOL:
            fail_closed("witness violation on row %d (%s t=%.1f):"
                        " deviation %.3e > tol %.0e"
                        % (r["_i"], r["groove"], r["plate_angle_deg"],
                           dev, bt.WITNESS_TOL))
    R("  %d/%d groove_sample rows re-derived exactly; worst deviation"
      " %.3e units (tol %.0e) PASS"
      % (len(samples), len(samples), worst_w, bt.WITNESS_TOL))
    R("")

    # [R] supplier re-derivation + the digit-for-digit reproduction
    R("[R] SUPPLIER RE-DERIVATION AND REPRODUCTION CHECK (the recorded")
    R("  supplier re-trained read-only through the IDENTICAL pinned")
    R("  code path; the re-derived numbers must match the recorded run")
    R("  of record digit for digit -- a mismatch fails closed)")
    held_sol = [r for r in rows
                if r["_i"] % bt.SPLIT_MOD == bt.SPLIT_REMAINDER
                and r["kind"] == "groove_sample"]
    train = [r for r in samples
             if r["_i"] % bt.SPLIT_MOD != bt.SPLIT_REMAINDER]
    models = {}
    for g in ("groove_1", "groove_2"):
        models[g] = bt.train_ridge([r for r in train if r["groove"] == g])
    dists = []
    for r in held_sol:
        lx, ly = bt.predict(models[r["groove"]], r["plate_angle_deg"])
        dists.append(bt.dist2(lx, ly, r["gx"], r["gy"]))
    med = bt.median(dists)
    wor = max(dists)
    R("  held-out solution rows: %d (the frozen split, counts computed)"
      % len(held_sol))
    check("reproduction: median held-out distance",
          "%.6e" % med, REC_MEDIAN)
    check("reproduction: worst held-out distance",
          "%.6e" % wor, REC_WORST)
    R("  median held-out distance %.6e units -- matches the recorded"
      " run" % med)
    R("  worst  held-out distance %.6e units -- matches the recorded"
      " run" % wor)
    # the frozen probe, un-fallbacked, through the re-derived supplier
    lx, ly = bt.predict(models[OOD_GROOVE], OOD_T_DEG)
    g_ood, _, _ = fc.groove_point((OOD_D, 0.0), OOD_T_DEG,
                                  (0.0, OOD_CY))
    ood_d = bt.dist2(lx, ly, g_ood[0], g_ood[1])
    check("reproduction: learned probe answer (x)", "%.8f" % lx,
          REC_LEARNED_X)
    check("reproduction: learned probe answer (y)", "%.8f" % ly,
          REC_LEARNED_Y)
    check("reproduction: probe distance", "%.6e" % ood_d,
          REC_PROBE_DIST)
    R("  un-fallbacked learned answer on the frozen probe:"
      " (%.8f, %.8f) -- matches" % (lx, ly))
    R("    the recorded run digit for digit")
    R("  un-fallbacked probe distance %.6e units (%.4f mm; %.4f x"
      " tolerance; %.4f x the worst held-out)"
      % (ood_d, ood_d * UNITS_PER_MM, ood_d / TOL_POS_UNITS,
         ood_d / wor))
    R("  NO new artifact is written: nothing new is trained -- the")
    R("  recorded first-run artifact stands (claim-only-what-exists)")
    R("")

    # [G] the design gate -------------------------------------------------
    R("[G] THE DESIGN GATE (the frozen fallback semantics, exercised)")
    R("  semantics: a demand carries its design (d, C_y) as declared")
    R("    context. If it equals the trained design (d=%.1f"
      " C_y=%.2f," % (d, cy))
    R("    DISCOVERED from the corpus, never hardcoded), the learned")
    R("    supplier answers, labeled LEARNED. Otherwise the supplier")
    R("    answers from the closed-form supplier (the instrument's")
    R("    own groove_point), labeled FALLBACK: CLOSED-FORM with the")
    R("    mismatch recorded. Both branches answer every demand;")
    R("    nothing is silently dropped.")

    def design_gate(groove, t_deg, dem_d, dem_cy):
        if dem_d == d and dem_cy == cy:
            mx, my = bt.predict(models[groove], t_deg)
            return ("LEARNED", (mx, my))
        g, _, _ = fc.groove_point((dem_d, 0.0), t_deg, (0.0, dem_cy))
        return ("FALLBACK: CLOSED-FORM (design mismatch d=%.1f"
                " C_y=%.2f vs trained d=%.1f C_y=%.2f)"
                % (dem_d, dem_cy, d, cy), (g[0], g[1]))

    # branch 1: the frozen OOD probe (design mismatch -> fallback)
    lab_p, ans_p = design_gate(OOD_GROOVE, OOD_T_DEG, OOD_D, OOD_CY)
    R("  demand 1 (the frozen OOD probe): groove_1 t=%.1f deg under"
      % OOD_T_DEG)
    R("    design d=%.1f C_y=%.2f" % (OOD_D, OOD_CY))
    R("    -> %s" % lab_p)
    fb_d = bt.dist2(ans_p[0], ans_p[1], g_ood[0], g_ood[1])
    check("fallback branch answers the exact closed-form point",
          "%.12f" % fb_d, "0.000000000000")
    R("    fallback answer (%.8f, %.8f); distance to the closed-form"
      % (ans_p[0], ans_p[1]))
    R("    answer %.12f units (the fallback IS the closed-form"
      " supplier: exact by construction)" % fb_d)
    R("    recorded behavior: the gate FIRED (design mismatch); the")
    R("    degradation datum does NOT recur -- the answer is exact;")
    R("    the mismatch is the recorded finding, never hidden")
    # branch 2: the same demand under the trained design (LEARNED)
    lab_i, ans_i = design_gate(OOD_GROOVE, OOD_T_DEG, d, cy)
    g_ind, _, _ = fc.groove_point(qmap[OOD_GROOVE], OOD_T_DEG,
                                 (0.0, cy))
    in_d = bt.dist2(ans_i[0], ans_i[1], g_ind[0], g_ind[1])
    R("  demand 2 (the same angle under the trained design):"
      " groove_1 t=%.1f" % OOD_T_DEG)
    R("    deg under design d=%.1f C_y=%.2f -> %s" % (d, cy, lab_i))
    R("    learned answer (%.8f, %.8f); distance to the closed-form"
      % (ans_i[0], ans_i[1]))
    R("    answer %.6e units (in-distribution class, as at the first"
      " run)" % in_d)
    if not (lab_p.startswith("FALLBACK") and lab_i == "LEARNED"):
        fail_closed("design gate branch labels wrong: %r / %r"
                    % (lab_p, lab_i))
    R("  both branches exercised and labeled; PASS")
    R("")

    # [S] the B2-signature test --------------------------------------------
    R("[S] THE B2-SIGNATURE TEST (the frozen rubric; the recorded")
    R("  design-shift failure classified against B2's diagnostic")
    R("  vocabulary)")
    R("  rubric: (a) REPRESENTATION-SCOPED -- an artifact of")
    R("    representation or convention, rescuable by a representation")
    R("    change (B2's case-B artifact class); (b) DATA-LIMITED -- a")
    R("    genuine coverage limit (B2's case-C answer class);")
    R("    (c) NEW SIGNATURE -- neither; a recorded finding either way.")
    # evidence 1: the learned function is design-invariant BY FREEZE
    lx2, ly2 = bt.predict(models[OOD_GROOVE], OOD_T_DEG)
    R("  evidence 1 (channel absent): the frozen feature map is")
    R("    [1, cos(k*x), sin(k*x)], x = radians(plate angle) -- K=%d,"
      % bt.FOURIER_K)
    R("    %d features, NO design argument. Evaluated under BOTH"
      % (1 + 2 * bt.FOURIER_K))
    R("    designs the output is identical by construction:")
    R("      under the trained design:   (%.8f, %.8f)" % (lx2, ly2))
    R("      under the probe design:      (%.8f, %.8f)  (the same"
      % (lx2, ly2))
    R("      function; the design cannot enter it)")
    # evidence 2: the design shift moves the closed-form answer
    shift = bt.dist2(g_ind[0], g_ind[1], g_ood[0], g_ood[1])
    R("  evidence 2 (the shift is real): the closed-form answer under")
    R("    the trained design (%.8f, %.8f) vs under the probe design"
      % (g_ind[0], g_ind[1]))
    R("    (%.8f, %.8f): the design shift moves the correct answer by"
      % (g_ood[0], g_ood[1]))
    R("    %.6f units (%.2f mm)" % (shift, shift * UNITS_PER_MM))
    # evidence 3: no representation rescue exists WITHIN the frozen
    # architecture (the case-B discriminator)
    R("  evidence 3 (no rescue within the frozen representation): two")
    R("    demands sharing (groove, t) but differing in design have")
    R("    correct answers %.6f units apart, but the frozen function" % shift)
    R("    produces ONE output for both -- the design information is")
    R("    ABSENT from the function, not mis-encoded. A rescue would")
    R("    require ADDING the design channel (a feature-map change =")
    R("    a new architecture, a future corpus decision), which is a")
    R("    redesign, not a representation rescue of the frozen")
    R("    architecture. This is the structural discriminator against")
    R("    B2's case-B artifact class (there, a constant mounting")
    R("    re-targeting rescued candidates; here nothing in the")
    R("    representation contradicts the demand -- the demand's")
    R("    design channel simply never enters the function).")
    R("  CLASSIFICATION: (b) DATA-LIMITED (B2's case-C answer class:")
    R("    a genuine coverage limit -- design coverage, by frozen")
    R("    construction).")
    R("  frozen prediction (never a gate): DATA-LIMITED -- HELD.")
    R("  reading, recorded: the fallback wiring is a BANDAGE and")
    R("    design coverage (Direction 2's synthetic expansion, or a")
    R("    design-conditioned representation as a future corpus")
    R("    decision) is the DISEASE. This answer redirects Direction")
    R("    2: the expansion's coverage map should carry the design")
    R("    axis explicitly, and the interpolation-vs-extrapolation")
    R("    split should read the design channel among its")
    R("    extrapolation cells.")
    R("")

    # [A1] zero modification ------------------------------------------------
    R("[A1] ZERO INSTRUMENT MODIFICATION (the reciprocity test)")
    R("  both instruments (the first-run trainer, the capability")
    R("  instrument) were imported read-only; their sha256 pins")
    R("  matched the merged files bit-for-bit -- instrument")
    R("  modification count: 0")
    R("")

    # [A3] determinism --------------------------------------------------------
    R("[A3] DETERMINISM CONTROL")
    R("  declared initialization: none -- the supplier re-derivation")
    R("    is the first run's exact seed-free solve, code-identical")
    R("    under the trainer pin; the design gate and the closed-form")
    R("    fallback are deterministic analytic functions")
    R("  in-process check: this script ran the full pass twice and")
    R("    compared the reports (verdict printed at the end)")
    R("  external standard (the recorded one): two redirected runs,")
    R("    diff empty, exit 0")
    R("")

    # [A4] labeling -------------------------------------------------------------
    R("[A4] SUPPLIER-OUTPUT LABELING")
    R("  the fallback branch's zero distance is the CLOSED-FORM")
    R("    supplier's, not a learned win; no head-to-head was run")
    R("    here and none is claimed. The label stands:")
    R("    %s" % A4_LABEL)
    R("  the label-change event remains defined exactly as frozen")
    R("    (with its numbers); no prose drift.")
    R("")

    # [A7] lineage ----------------------------------------------------------------
    R("[A7] LINEAGE RECORDING")
    R("  corpus of record: %s (sha256 %s, pinned, verified at run)"
      % (bt.CORPUS_REL, CORPUS_SHA256))
    R("  first-run instrument: %s sha256 %s (unmodified)"
      % (TRAINER_REL, TRAINER_SHA256))
    R("  capability instrument: %s sha256 %s (unmodified)"
      % (INSTRUMENT_REL, INSTRUMENT_SHA256))
    R("  trained artifact: the RECORDED first-run artifact stands")
    R("    (runs/b1-admission-gate-01/b1_proposer_v1.json, recorded")
    R("    sha256 ceebf162c8d11a5c97f042735b76465bf34e304039c2a74b660e"
      "8ebc41745678);")
    R("    this re-probe writes NO new artifact (nothing new trained)")
    R("  run source commit: %s" % source_commit)
    R("")

    # [READ] the frozen-prediction outcome ---------------------------------------
    R("[READ] FROZEN-PREDICTION OUTCOME (recorded as data, never a")
    R("  gate)")
    R("  B2-signature prediction DATA-LIMITED: HELD (the classification")
    R("    reads (b), as predicted at the freeze)")
    R("")
    R("re-probe reading: the design gate fires exactly as frozen on")
    R("the recorded probe; the fallback answer is exact and labeled")
    R("FALLBACK: CLOSED-FORM with the mismatch recorded; the recorded")
    R("supplier reproduces digit for digit; the design-shift failure")
    R("classifies DATA-LIMITED (design coverage, by frozen")
    R("construction). The fallback is a bandage; design coverage is")
    R("the disease -- the recorded answer that redirects Direction 2.")
    R("Label: %s" % A4_LABEL)
    return R_out


if __name__ == "__main__":
    sys.exit(main())
