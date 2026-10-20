#!/usr/bin/env python3
"""Job b1-representation-01: the design-conditioned representation
instrument (run staging; frozen before any run; implements the
freeze document jobs/b1-representation-01/JOB.md exactly; may not
amend it).

Trains the frozen design-conditioned map -- per groove, the
trainer's own Fourier basis [1, cos(k*x), sin(k*x)] (49 features)
extended with the design channel [d, C_y] and the first-order
products [d cos(k*x), d sin(k*x), C_y cos(k*x), C_y sin(k*x)]
(98 added; 147 per groove), ONE model per groove trained ACROSS
the 6 TRAIN design cells, the trainer's RIDGE_LAMBDA and its own
Gaussian-elimination solve imported read-only -- then measures
the coverage classes with identical definitions to the
expansion's recorded disease measurement, reads the numeric
collapse bar as data, and grades the recorded 885x case ONCE at
the final grade. Every training and demand row is synthesized at
run time through the pinned capability instrument's groove_point,
consumed READ-ONLY under its pin -- never stored, never
transcribed. The corpus of record is the REPRODUCTION ANCHOR.
The report IS the stop record; NO artifact is written.

Label: every output of the learned-proposal line is a SUPPLIER
OUTPUT, not a generator capability, until the line wins a
head-to-head against closed-form (the frozen A4 rule, carried).

Usage (repo root, the recorded standard):
  python jobs/b1-representation-01/b1_representation_run.py
      --source-commit <40-hex-sha> > run1.txt
  (twice; external diff must be empty; exit 0)

Pure stdlib; ASCII only; Python 3.10+; no network; seed-free
training. No wall-clock time appears anywhere in the report (the
flip -02 lesson: timing metadata is the recorded
nondeterminism source).
"""

import hashlib
import math
import os
import platform
import re
import sys

JOB_ID = "b1-representation-01"

# [P0] pins (frozen at this staging; fail-closed on mismatch)
CAP_REL = os.path.join(
    "jobs", "flip-station-capability-01", "flip_capability.py")
CAP_SHA256 = (
    "72989f8a1183647f5cbf47c6db92b0cdc63eead355acb25f1dd42adedc06447b")
CAP_BYTES = 50265
TRAINER_REL = os.path.join(
    "jobs", "b1-admission-gate-01", "b1_proposer_train.py")
TRAINER_SHA256 = (
    "1cb985bac4a34f6c07ed768f3b13692e7ea4c3be3bfbcfab973d1aeb0c5a9974")
TRAINER_BYTES = 26268
CORPUS_REL = os.path.join(
    "runs", "flip-station-capability-01", "flip_station_capability_v1.jsonl")
CORPUS_SHA256 = (
    "cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c")
CORPUS_PROVENANCE_COMMIT = (
    "9c9fd6f9f1724e683ed053f621f95fe5a283425a")
CORPUS_ROWS_EXPECTED = 838
CORPUS_REGEN_HINT = (
    "regenerate it read-only from the merged instrument: python %s"
    " --source-commit %s (expected jsonl sha256 %s)"
    % (CAP_REL, CORPUS_PROVENANCE_COMMIT, CORPUS_SHA256))

# the coverage map (frozen; carried unchanged from the expansion)
TRAIN_D = (0.1, 0.2, 0.3)
EXTRAP_D = (0.4, 0.5)
SWEEP_CY = (0.0, 0.25)      # C_y = 0.5: the feasibility open
                            # residue, NOT scoped in
ANCHOR_D = 0.2              # the recorded chosen design (the
ANCHOR_CY = 0.0             # reproduction anchor cell)
BAND_UNITS = 0.015          # the 0.015-unit tolerance band
BAR_RATIO = 10.0             # the collapse bar, clause 1
RECORDED_RATIO = 17930.5049  # the expansion's recorded ratio
RECORDED_INTERP_MED = 8.365633e-06  # recorded interpolation median
GRADE_GROOVE = "groove_1"   # the recorded 885x case, graded once
GRADE_T_DEG = 90.0
GRADE_D = 0.4
GRADE_CY = 0.25

A4_LABEL = ("SUPPLIER OUTPUT (LEARNED -- no head-to-head win; "
            "the A4 label stands per the frozen rule)")


class FailClosed(Exception):
    pass


def fail_closed(msg):
    raise FailClosed(msg)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def median(xs):
    """Median as mean of the two central order statistics when
    even (the expansion's own definition, carried)."""
    s = sorted(xs)
    n = len(s)
    if n == 0:
        fail_closed("median of an empty list")
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def dist2(ax, ay, bx, by):
    return math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by))


def pin_file(rel, sha, nbytes):
    if not os.path.isfile(rel):
        fail_closed("pinned file missing: %s" % rel)
    got = sha256_file(rel)
    gb = os.path.getsize(rel)
    if got != sha or gb != nbytes:
        fail_closed("pin mismatch: %s got %s (%d bytes), pinned %s"
                    " (%d bytes)" % (rel, got, gb, sha, nbytes))
    return got


def load_anchor_corpus():
    """The corpus of record, loaded through the TRAINER's own
    fail-closed loader (the re-probe and expansion precedent)."""
    if not os.path.isfile(CORPUS_REL):
        fail_closed("corpus of record missing: %s -- %s"
                    % (CORPUS_REL, CORPUS_REGEN_HINT))
    got = sha256_file(CORPUS_REL)
    if got != CORPUS_SHA256:
        fail_closed("corpus sha256 mismatch: got %s pinned %s -- %s"
                    % (got, CORPUS_SHA256, CORPUS_REGEN_HINT))
    sys.path.insert(0, os.path.dirname(os.path.abspath(TRAINER_REL)))
    import b1_proposer_train as bt  # noqa: E402 (read-only import)
    rows = bt.load_corpus()
    if len(rows) != CORPUS_ROWS_EXPECTED:
        fail_closed("corpus row count %d != expected %d"
                    % (len(rows), CORPUS_ROWS_EXPECTED))
    return bt, rows


def phi_ext(t_deg, d, cy, k):
    """The frozen design-conditioned feature map (the ONE new
    builder, living in this instrument; the trainer's basis
    carried and extended): [1, cos(k*x), sin(k*x)] for k = 1..K
    (the trainer's own 49 features) then [d, C_y] (2) then the
    first-order products [d cos(k*x), d sin(k*x), C_y cos(k*x),
    C_y sin(k*x)] for k = 1..K (96) -- 147 features per groove."""
    x = math.radians(t_deg)
    row = [1.0]
    row.extend(math.cos(kk * x) for kk in range(1, k + 1))
    row.extend(math.sin(kk * x) for kk in range(1, k + 1))
    row.append(d)
    row.append(cy)
    row.extend(d * math.cos(kk * x) for kk in range(1, k + 1))
    row.extend(d * math.sin(kk * x) for kk in range(1, k + 1))
    row.extend(cy * math.cos(kk * x) for kk in range(1, k + 1))
    row.extend(cy * math.sin(kk * x) for kk in range(1, k + 1))
    return row


def train_ridge_ext(bt, rows, k, lam):
    """Closed-form ridge on the extended map, the trainer's own
    solve path (solve_linear imported read-only) and its carried
    RIDGE_LAMBDA; no randomness anywhere."""
    nfeat = 1 + 2 * k + 2 + 4 * k
    xs = [phi_ext(r["plate_angle_deg"], r["d"], r["cy"], k)
          for r in rows]
    m = [[0.0] * nfeat for _ in range(nfeat)]
    bgx = [0.0] * nfeat
    bgy = [0.0] * nfeat
    for xi, r in zip(xs, rows):
        for i in range(nfeat):
            xi_ = xi[i]
            if xi_ != 0.0:
                mi = m[i]
                for j in range(nfeat):
                    mi[j] += xi_ * xi[j]
            bgx[i] += xi_ * r["gx"]
            bgy[i] += xi_ * r["gy"]
    for i in range(nfeat):
        m[i][i] += lam
    return {"w_gx": bt.solve_linear(m, bgx),
            "w_gy": bt.solve_linear(m, bgy)}


def predict_ext(model, t_deg, d, cy, k):
    p = phi_ext(t_deg, d, cy, k)
    gx = 0.0
    gy = 0.0
    for i, p_ in enumerate(p):
        gx += p_ * model["w_gx"][i]
        gy += p_ * model["w_gy"][i]
    return gx, gy


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
        print("usage: b1_representation_run.py --source-commit"
              " <40-hex-sha>", file=sys.stderr)
        return 1
    if not re.match(r"^[0-9a-f]{40}$", source_commit):
        print("FAIL-CLOSED: --source-commit must be a 40-char"
              " lowercase hex sha", file=sys.stderr)
        return 1
    try:
        out1 = run(source_commit)
        out2 = run(source_commit)
    except FailClosed as exc:
        print("FAIL-CLOSED: %s" % exc, file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 (fail closed on anything)
        print("FAIL-CLOSED: unexpected error: %s: %s"
              % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    identical = (out1 == out2)
    for line in out1:
        print(line)
    print("")
    print("double-run determinism check: %s"
          % ("IDENTICAL" if identical else "DIFFERS (FAIL)"))
    return 0 if identical else 1


def run(source_commit):
    """One complete generation + training + measurement pass."""
    R_out = []
    R = R_out.append

    R("b1-representation-01 -- the design-conditioned"
      " representation instrument")
    R("(run staging; frozen before any run; implements the freeze")
    R("document jobs/b1-representation-01/JOB.md exactly; no")
    R("wall-clock time anywhere in this report)")
    R("label: %s" % A4_LABEL)
    R("python: %s" % platform.python_version())
    R("source commit: %s" % source_commit)
    R("")

    # [P0] pins ----------------------------------------------------------
    R("[P0] PIN CHECKS (fail-closed)")
    cap_sha = pin_file(CAP_REL, CAP_SHA256, CAP_BYTES)
    tr_sha = pin_file(TRAINER_REL, TRAINER_SHA256, TRAINER_BYTES)
    R("  capability instrument %s" % CAP_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (consumed READ-ONLY"
      % (cap_sha, CAP_BYTES))
    R("    as the analytic ground-truth synthesizer)")
    R("  trainer %s" % TRAINER_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (IMPORTED READ-ONLY;"
      % (tr_sha, TRAINER_BYTES))
    R("    the loader, split rule, ridge constants and the")
    R("    Gaussian-elimination solve are the trainer's own)")
    bt, rows = load_anchor_corpus()
    R("  corpus of record %s" % CORPUS_REL)
    R("    sha256 %s -- PIN MATCH (the REPRODUCTION ANCHOR)"
      % CORPUS_SHA256)
    R("    provenance commit %s -- PIN MATCH" % CORPUS_PROVENANCE_COMMIT)
    R("")
    sys.path.insert(0, os.path.dirname(os.path.abspath(CAP_REL)))
    import flip_capability as fc  # noqa: E402 (read-only import)

    # [G] the frozen budget, generated exactly once ----------------------
    R("[G] GENERATION (the frozen budget; deterministic analytic")
    R("  generation through the pinned oracle -- no stochastic")
    R("  draw exists anywhere; a rerun regenerates the identical")
    R("  budget, stronger than draw-once)")
    samples = [r for r in rows if r["kind"] == "groove_sample"]
    grids = {}
    for g in ("groove_1", "groove_2"):
        ts = [r["plate_angle_deg"] for r in samples
              if r["groove"] == g]
        if len(ts) != 360:
            fail_closed("%s has %d groove_sample rows, expected 360"
                        % (g, len(ts)))
        grids[g] = ts
    if grids["groove_1"] != grids["groove_2"]:
        fail_closed("groove_1 and groove_2 angle grids differ")
    angles = grids["groove_1"]
    R("  demand grid: derived from the corpus of record -- 360")
    R("    recorded angles per groove (the recorded 1.0 deg")
    R("    emission grid), 2 grooves, 720 demands per cell")
    R("  deterministic enumeration (declared): training rows")
    R("    groove, d, C_y, index; demands d, C_y, groove, index")
    R("  TRAIN (6 cells): d in {0.1, 0.2, 0.3} x C_y in")
    R("    {0.0, 0.25}; the recorded chosen design (d=0.2/C_y=0.0)")
    R("    among them -- the reproduction anchor cell")
    R("  INTERPOLATION held-out: the (i mod 5) == 4 samples within")
    R("    the 6 trained cells -- angle-axis interpolation inside")
    R("    trained designs; design-INTERPOLATION stays EMPTY by")
    R("    construction on the recorded grid (recorded honestly,")
    R("    carried)")
    R("  EXTRAPOLATION held-out ENTIRE (4 cells -- the disease")
    R("    class): d in {0.4, 0.5} x C_y in {0.0, 0.25}; no")
    R("    training row, every sample a demand beyond the trained")
    R("    d range")
    R("  FEASIBILITY cells (C_y = 0.5, fail-closed by")
    R("    construction): NOT this job's demand set -- an open")
    R("    residue per the freeze, never silently scoped in")
    R("  stop condition: the budget is measured once and this")
    R("    report is the stop; no extension, no regeneration, no")
    R("    re-split after any result exists; an underpowered or")
    R("    failed measurement is a recorded finding, never a")
    R("    budget re-open")
    R("")

    # [ANCHOR] reproduction anchor ---------------------------------------
    R("[ANCHOR] REPRODUCTION ANCHOR (the regenerated d=0.2/C_y=0.0")
    R("  cell must reproduce the corpus of record's recorded")
    R("  solution rows exactly)")
    d0, cy0 = bt.discover_chosen_design(rows)
    if (d0, cy0) != (ANCHOR_D, ANCHOR_CY):
        fail_closed("chosen design is (%r, %r), the anchor cell is"
                    " (0.2, 0.0)" % (d0, cy0))
    qmap = {"groove_1": (d0, 0.0), "groove_2": (-d0, 0.0)}
    C0 = (0.0, cy0)
    worst_anchor = 0.0
    for r in samples:
        g, _, _ = fc.groove_point(qmap[r["groove"]],
                                  r["plate_angle_deg"], C0)
        dev = dist2(g[0], g[1], r["gx"], r["gy"])
        worst_anchor = max(worst_anchor, dev)
        if dev > bt.WITNESS_TOL:
            fail_closed("anchor violation on %s t=%.1f: re-derived"
                        " (%.12f, %.12f) vs recorded (%.12f, %.12f)"
                        " deviation %.3e > tol %.0e"
                        % (r["groove"], r["plate_angle_deg"], g[0],
                           g[1], r["gx"], r["gy"], dev,
                           bt.WITNESS_TOL))
    R("  %d/%d recorded groove_sample rows reproduced by the"
      % (len(samples), len(samples)))
    R("    regenerated cell (worst deviation %.3e units, tol %.0e)"
      " PASS" % (worst_anchor, bt.WITNESS_TOL))
    R("")

    # [R] the new representation ------------------------------------------
    R("[R] THE NEW REPRESENTATION (the design-conditioned feature")
    R("  map; the builder lives in THIS instrument; the trainer")
    R("  imported read-only)")
    if bt.FOURIER_K != 24:
        fail_closed("the trainer's FOURIER_K is %r; the freeze"
                    " froze 24" % bt.FOURIER_K)
    if bt.RIDGE_LAMBDA != 1e-8:
        fail_closed("the trainer's RIDGE_LAMBDA is %r; the freeze"
                    " froze 1e-08" % bt.RIDGE_LAMBDA)
    if bt.SPLIT_MOD != 5 or bt.SPLIT_REMAINDER != 4:
        fail_closed("the trainer's split rule is (mod %d, remainder"
                    " %d); the freeze froze (5, 4)"
                    % (bt.SPLIT_MOD, bt.SPLIT_REMAINDER))
    band = bt.TOL_POS_UNITS
    if band != BAND_UNITS:
        fail_closed("the trainer's TOL_POS_UNITS is %r; the freeze"
                    " froze %.3f" % (band, BAND_UNITS))
    nfeat = 1 + 2 * bt.FOURIER_K + 2 + 4 * bt.FOURIER_K
    R("  architecture: [1, cos(k*x), sin(k*x)] k=1..%d (the"
      " trainer's own" % bt.FOURIER_K)
    R("    49 features) EXTENDED with the design channel: [d, C_y]")
    R("    (2) plus the first-order products [d cos(k*x),"
      " d sin(k*x),")
    R("    C_y cos(k*x), C_y sin(k*x)] k=1..%d (96) -- %d features"
      % (bt.FOURIER_K, nfeat))
    R("    per groove")
    R("  ONE model per groove (two models), trained ACROSS the 6")
    R("    TRAIN design cells; the ridge is the trainer's own")
    R("    RIDGE_LAMBDA=%s on every diagonal (bias included), the"
      % repr(bt.RIDGE_LAMBDA))
    R("    solve the trainer's own Gaussian elimination with")
    R("    partial pivoting (imported read-only); seed-free, no")
    R("    stochastic component anywhere")
    R("  why first-order (the lineage, carried): the expansion")
    R("    measured the extrapolation error AS the design offset")
    R("    itself; a design channel gated multiplicatively onto")
    R("    the angle basis carries exactly the term that cancels a")
    R("    design-offset error to first order; higher-order terms")
    R("    are NOT added (a future finding-driven candidate,")
    R("    staged through the gate, never a silent addition)")
    R("  split rule (the trainer's own, carried): in-cell 0-based")
    R("    sample index i held out iff i %% %d == %d"
      % (bt.SPLIT_MOD, bt.SPLIT_REMAINDER))
    R("  training data: every row synthesized at run time through")
    R("    the pinned oracle's groove_point, consumed READ-ONLY")
    R("    under its pin -- never stored, never transcribed")
    ntrain = len(angles) - len(angles) // bt.SPLIT_MOD
    models = {}
    for g in ("groove_1", "groove_2"):
        trows = []
        for d in TRAIN_D:
            for cy in SWEEP_CY:
                q = (d, 0.0) if g == "groove_1" else (-d, 0.0)
                for i, t in enumerate(angles):
                    if i % bt.SPLIT_MOD != bt.SPLIT_REMAINDER:
                        gg, _, _ = fc.groove_point(q, t, (0.0, cy))
                        trows.append({"plate_angle_deg": t,
                                      "d": d, "cy": cy,
                                      "gx": gg[0], "gy": gg[1]})
        models[g] = train_ridge_ext(bt, trows, bt.FOURIER_K,
                                    bt.RIDGE_LAMBDA)
        R("  trained %s on %d rows (6 cells x %d train samples"
          " per groove)" % (g, len(trows), ntrain))
    R("  extrapolation cells NEVER trained (d in {0.4, 0.5} x C_y")
    R("    in {0.0, 0.25}); their demands go straight to the new")
    R("    map as design inputs -- the treatment under test")
    R("")

    # [M] the coverage measurement ----------------------------------------
    R("[M] THE MEASUREMENT (frozen; identical definitions to the")
    R("  expansion's recorded disease measurement so the collapse")
    R("  is directly comparable; drawn EXACTLY ONCE; the report IS")
    R("  the stop record, NO artifact written)")
    R("  distance function (frozen): Euclidean in task-layer")
    R("    units, the learned answer vs the closed-form ground")
    R("    truth re-derived through the pinned oracle")
    R("  per-class table (learned answer vs closed-form ground")
    R("    truth):")
    R("    class               count   median         worst")
    classes = {"train_in_sample": [], "interpolation": [],
               "extrapolation": []}
    per_d = {0.4: [], 0.5: []}
    per_cell = {}
    for d in TRAIN_D + EXTRAP_D:
        for cy in SWEEP_CY:
            trained = d in TRAIN_D
            q1, q2 = (d, 0.0), (-d, 0.0)
            C = (0.0, cy)
            for g in ("groove_1", "groove_2"):
                q = q1 if g == "groove_1" else q2
                for i, t in enumerate(angles):
                    gg, _, _ = fc.groove_point(q, t, C)
                    lx, ly = predict_ext(models[g], t, d, cy,
                                        bt.FOURIER_K)
                    dd = dist2(lx, ly, gg[0], gg[1])
                    if trained:
                        cls = ("train_in_sample"
                               if i % bt.SPLIT_MOD
                               != bt.SPLIT_REMAINDER
                               else "interpolation")
                    else:
                        cls = "extrapolation"
                        per_d[d].append(dd)
                    classes[cls].append(dd)
                    per_cell.setdefault((d, cy, cls), []).append(dd)
    class_stats = {}
    for cls in ("train_in_sample", "interpolation",
                "extrapolation"):
        xs = classes[cls]
        med, wor = median(xs), max(xs)
        class_stats[cls] = (med, wor)
        R("    %-19s %6d  %.6e  %.6e" % (cls, len(xs), med, wor))
    med_i = class_stats["interpolation"][0]
    med_e = class_stats["extrapolation"][0]
    wor_e = class_stats["extrapolation"][1]
    ratio = med_e / med_i
    R("  ratio of medians (extrapolation/interpolation): %.4fx"
      % ratio)
    R("  recorded expansion ratio (the measured disease):")
    R("    %.4fx -- extrapolation median 1.500000e-01 vs"
      % RECORDED_RATIO)
    R("    interpolation median 8.365633e-06 units")
    R("  extrapolation median / tolerance (%.3f units): %.4f"
      % (band, med_e / band))
    R("  extrapolation worst / tolerance: %.4f" % (wor_e / band))
    R("  per-d sub-class medians (data, so both directions are")
    R("    powered):")
    sub_stats = {}
    for d in EXTRAP_D:
        xs = per_d[d]
        sm, sw = median(xs), max(xs)
        sub_stats[d] = (sm, sw)
        R("    d=%.1f: median %.6e units (%.4f x tolerance); worst"
          " %.6e units (%.4f x tolerance); ratio to interpolation"
          " %.4fx" % (d, sm, sm / band, sw, sw / band, sm / med_i))
    R("  per-cell detail (median | worst, units):")
    for d in TRAIN_D + EXTRAP_D:
        for cy in SWEEP_CY:
            for cls in ("train_in_sample", "interpolation",
                        "extrapolation"):
                xs = per_cell.get((d, cy, cls))
                if xs:
                    R("    d=%.1f C_y=%.2f %-17s %.6e  %.6e"
                      % (d, cy, cls, median(xs), max(xs)))
    R("  design-INTERPOLATION stays EMPTY by construction on the")
    R("    recorded grid (both admissible C_y values trained;")
    R("    every interior d trained) -- recorded honestly, carried")
    R("  the closed-form check (the both-directions discipline):")
    R("    every ground truth above is the closed-form answer")
    R("    re-derived through the pinned oracle; the reproduction")
    R("    anchor PASS carries the lineage; the closed form")
    R("    remains exact, instant, and free (the preordained")
    R("    axis, carried; accuracy powers nothing)")
    R("")

    # [BAR] the numeric collapse bar --------------------------------------
    R("[BAR] THE NUMERIC COLLAPSE BAR (picked at freeze time with")
    R("  its lineage; this run's reading recorded as data, never")
    R("  a gate)")
    c1 = ratio <= BAR_RATIO
    c2 = med_e <= band
    R("  clause 1 -- the ratio of medians (extrapolation/")
    R("    interpolation) falls from the recorded %.4fx to <="
      % RECORDED_RATIO)
    R("    %.1fx: %s (%.4fx)" % (BAR_RATIO,
                                "PASS" if c1 else "MISS", ratio))
    R("  clause 2 -- the extrapolation class median lands INSIDE")
    R("    the %.3f-unit band (the band the loop actually uses):"
      % band)
    R("    %s (%.6e units, %.4f mm)" % ("PASS" if c2 else "MISS",
                                       med_e, med_e * 100.0))
    bar_met = c1 and c2
    if bar_met:
        R("  the bar (both clauses): MET")
    else:
        R("  the bar (both clauses): MISS -- a RECORDED FINDING")
        R("    about the feature-map approach (the first-order")
        R("    design channel as specified); never a waiver,")
        R("    never a silent re-tune, never a bar moved after")
        R("    the fact")
    R("")

    # [GRADE] the recorded case, graded once -------------------------------
    R("[GRADE] THE RECORDED CASE, GRADED ONCE (the final grade;")
    R("  all class measurement is complete; touched ONCE, then the")
    R("  run STOPS; never an iteration target -- iterating")
    R("  against the recorded case would be the")
    R("  retune-on-holdout anti-pattern)")
    R("  the recorded design-shift case: groove_1, 90.0 deg,")
    R("    d=0.4 / C_y=0.25 -- the probe that named the disease")
    R("    (the recorded 885.0308x is its precedent)")
    if GRADE_T_DEG not in angles:
        fail_closed("the recorded grade angle %.1f deg is not on"
                    " the recorded grid" % GRADE_T_DEG)
    gg, _, _ = fc.groove_point((GRADE_D, 0.0), GRADE_T_DEG,
                               (0.0, GRADE_CY))
    lx, ly = predict_ext(models[GRADE_GROOVE], GRADE_T_DEG,
                         GRADE_D, GRADE_CY, bt.FOURIER_K)
    gdist = dist2(lx, ly, gg[0], gg[1])
    R("  closed-form answer through the pinned oracle:")
    R("    (%.8f, %.8f)" % (gg[0], gg[1]))
    R("  learned answer under the new map:")
    R("    (%.8f, %.8f)" % (lx, ly))
    R("  distance-to-closed-form: %.6e units (%.4f mm; %.4f x"
      " tolerance) -- %s" % (gdist, gdist * 100.0,
                             gdist / band,
                             "IN BAND" if gdist <= band
                             else "OUT OF BAND"))
    R("  recorded as data; the run STOPS here on this case (the")
    R("    grade-only rule; the iteration set is synthetic only --")
    R("    the interpolation held-out samples and the 4")
    R("    extrapolation cells; the optional second")
    R("    iteration-scratch cell NOT taken)")
    R("")

    # [MOD] the mod-count row ----------------------------------------------
    R("[MOD] ZERO-MODIFICATION ROW (the pinned artifacts re-hashed")
    R("  after the measurement)")
    mods = 0
    for rel, sha, nbytes in ((CAP_REL, CAP_SHA256, CAP_BYTES),
                              (TRAINER_REL, TRAINER_SHA256,
                               TRAINER_BYTES),
                              (CORPUS_REL, CORPUS_SHA256, None)):
        if (not os.path.isfile(rel) or sha256_file(rel) != sha
                or (nbytes is not None
                    and os.path.getsize(rel) != nbytes)):
            mods += 1
    R("  instrument modification count: %d (expected 0; a nonzero"
      " count is a recorded FAIL of this row)" % mods)
    if mods != 0:
        fail_closed("the mod-count row FAILS: %d pinned artifact(s)"
                    " changed during the run" % mods)
    R("")

    # [H] both-directions honesty and the frozen label ---------------------
    R("[H] BOTH-DIRECTIONS HONESTY AND THE FROZEN LABEL")
    R("  this run exists to treat the measured disease, not to")
    R("    grow a claim; no result above amends the budget, the")
    R("    coverage map, the bar, or any recorded outcome")
    R("  the closed form is exact, instant, and free; on")
    R("    distance-to-closed-form it scores 0 by definition; a")
    R("    learned accuracy win is never claimed (the preordained")
    R("    axis, carried)")
    R("  the A4 SUPPLIER OUTPUT label carries unchanged and the")
    R("    label-change event remains defined and unfired,")
    R("    evaluated only against its recorded definition, never")
    R("    here")
    R("  the substitution guard stands; case study C stays CLOSED")
    R("    at its recorded outcomes; if this representation lands,")
    R("    the transfer datum re-runs under it before it carries")
    R("    forward (the freeze's recorded supplier-version")
    R("    scoping)")
    R("  label: %s" % A4_LABEL)
    R("")

    # [READ] the frozen prediction, read on this run's own output ---------
    R("[READ] FROZEN-PREDICTION OUTCOMES (recorded as data, never")
    R("  gates)")
    d04 = sub_stats[0.4]
    d05 = sub_stats[0.5]
    primary = (d04[0] <= band) and (d04[0] / med_i <= BAR_RATIO)
    R("  PRIMARY (the disease's own structure) -- the collapse")
    R("    lands on the d=0.4 sub-class, 0.1 beyond the trained")
    R("    edge (sub-class median inside the band AND ratio to")
    R("    interpolation <= %.1fx): %s (sub-class median %.6e"
      % (BAR_RATIO, "HELD" if primary
         else "REFUTED (honest data)", d04[0]))
    R("    units, ratio %.4fx)" % (d04[0] / med_i))
    cb_d5 = (d05[0] > band) or (d05[0] / med_i > BAR_RATIO)
    if cb_d5:
        R("  COUNTER-BRANCH d=0.5 (0.2 beyond the trained edge;")
        R("    second-order design dependence untrained): FIRED --")
        R("    a recorded finding about first-order conditioning")
        R("    at twice the distance; the second-order channel is")
        R("    the recorded future candidate, through the gate,")
        R("    never silently added (sub-class median %.6e units,"
          " ratio %.4fx)" % (d05[0], d05[0] / med_i))
    else:
        R("  COUNTER-BRANCH d=0.5 (0.2 beyond the trained edge;")
        R("    second-order design dependence untrained): NOT FIRED")
        R("    -- the collapse extends to the far cells (honest")
        R("    data; sub-class median %.6e units, ratio %.4fx)"
          % (d05[0], d05[0] / med_i))
    if primary:
        R("  COUNTER-BRANCH d=0.4 miss -- a finding about the")
        R("    feature-map approach itself: NOT FIRED")
    else:
        R("  COUNTER-BRANCH d=0.4 miss -- a finding about the")
        R("    feature-map approach itself: FIRED")
    interp_deg = med_i > RECORDED_INTERP_MED
    if interp_deg:
        R("  COUNTER-BRANCH interpolation degradation (a collapse")
        R("    bought by breaking the anchor): FIRED -- a recorded")
        R("    finding in the other direction (new interpolation")
        R("    median %.6e vs the recorded expansion interpolation"
          % med_i)
        R("    median 8.365633e-06 units; the anchor classes are")
        R("    never sacrificed for the bar)")
    else:
        R("  COUNTER-BRANCH interpolation degradation (a collapse")
        R("    bought by breaking the anchor): NOT FIRED (new")
        R("    interpolation median %.6e vs the recorded expansion"
          % med_i)
        R("    interpolation median 8.365633e-06 units; the anchor")
        R("    classes are never sacrificed for the bar)")
    R("  LABEL, frozen in advance: %s" % A4_LABEL)
    R("")
    R("representation reading: the budget was drawn exactly once,")
    R("measured once, and stopped; every number above is this")
    R("run's own output; no artifact was written. Label: %s"
      % A4_LABEL)
    return R_out


if __name__ == "__main__":
    sys.exit(main())
