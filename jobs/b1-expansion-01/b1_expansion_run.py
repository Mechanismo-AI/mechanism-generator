#!/usr/bin/env python3
"""Job b1-expansion-01: the Direction 2 synthetic expansion instrument
(run staging; frozen before any run; implements the freeze document
jobs/b1-expansion-01/JOB.md exactly; may not amend it).

Generates the frozen budget EXACTLY ONCE per run (deterministically:
the generation is analytic, so a rerun regenerates the identical
budget -- a stronger property than draw-once; no stochastic draw
exists anywhere in the generation), trains the frozen per-design-cell
supplier, and measures the three pre-declared comparison axes plus
the design-coverage classes. The corpus of record is the REPRODUCTION
ANCHOR: the regenerated d=0.2/C_y=0.0 cell must reproduce its recorded
groove_sample rows exactly or the instrument fails closed.

Label: every output of the learned-proposal line is a SUPPLIER
OUTPUT, not a generator capability, until the line wins a
head-to-head against closed-form (the frozen A4 rule, carried).

Usage (repo root, the recorded standard):
  python jobs/b1-expansion-01/b1_expansion_run.py \
      --source-commit <40-hex-sha> > run1.txt
  (twice; external diff must be empty; exit 0)

Pure stdlib; ASCII only; Python 3.10+; no network; deterministic.
No wall-clock time appears anywhere in the report (the flip -02
lesson: timing metadata is the recorded nondeterminism source).
"""

import hashlib
import json
import math
import os
import platform
import random
import re
import sys

JOB_ID = "b1-expansion-01"

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
CORPUS_JOB = "flip-station-capability-01"
CORPUS_ROWS_EXPECTED = 838
CORPUS_REGEN_HINT = (
    "regenerate it read-only from the merged instrument: python %s"
    " --source-commit %s (expected jsonl sha256 %s)"
    % (CAP_REL, CORPUS_PROVENANCE_COMMIT, CORPUS_SHA256))
WITNESS_TOL = 1e-9

# The frozen budget (the freeze document's numbers, verbatim)
SWEEP_D = [0.1, 0.2, 0.3, 0.4, 0.5]      # the recorded sweep
SWEEP_CY_ADMISSIBLE = [0.0, 0.25]        # C_y = 0.5 fails closed
SWEEP_CY_FAILCLOSED = 0.5
SPLIT_MOD = 5
SPLIT_REMAINDER = 4       # in-cell index i held out iff i % 5 == 4
BASELINE_SEEDS = [580000050, 580000051, 580000052]
HANDOFF_T_DEG = [0.0, 180.0]
TOL_POS_UNITS = 0.015     # 1.5 mm handoff tolerance, task-layer units
UNITS_PER_MM = 100.0

# Axis 2 search (the constrained-variant re-pose; deterministic)
AX2_MAX_ITER = 100
AX2_STEP0 = 0.01
AX2_STEP_MIN = 1e-12

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
    """Median as mean of the two central order statistics when even."""
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
    fail-closed loader (the re-probe precedent: the validation path
    is the trainer's, imported read-only under its pin)."""
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


def angle_grid(rows):
    """The recorded per-groove angle sampling, DERIVED from the corpus
    of record (never assumed); the demand grid of every design cell."""
    samples = [r for r in rows if r["kind"] == "groove_sample"]
    grids = {}
    for g in ("groove_1", "groove_2"):
        ts = [r["plate_angle_deg"] for r in samples if r["groove"] == g]
        if len(ts) != 360:
            fail_closed("%s has %d groove_sample rows, expected 360"
                        % (g, len(ts)))
        grids[g] = ts
    if grids["groove_1"] != grids["groove_2"]:
        fail_closed("groove_1 and groove_2 angle grids differ")
    return grids["groove_1"], samples


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
        print("usage: b1_expansion_run.py --source-commit <40-hex-sha>",
              file=sys.stderr)
        return 1
    if not re.match(r"^[0-9a-f]{40}$", source_commit):
        print("FAIL-CLOSED: --source-commit must be a 40-char lowercase"
              " hex sha", file=sys.stderr)
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

    R("b1-expansion-01 -- the Direction 2 synthetic expansion instrument")
    R("(run staging; frozen before any run; implements the freeze")
    R("document jobs/b1-expansion-01/JOB.md exactly; no wall-clock time")
    R("anywhere in this report)")
    R("label: %s" % A4_LABEL)
    R("python: %s" % platform.python_version())
    R("source commit: %s" % source_commit)
    R("")

    # [P0] pins ----------------------------------------------------------
    R("[P0] PIN CHECKS (fail-closed)")
    cap_sha = pin_file(CAP_REL, CAP_SHA256, CAP_BYTES)
    tr_sha = pin_file(TRAINER_REL, TRAINER_SHA256, TRAINER_BYTES)
    R("  capability instrument %s" % CAP_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (consumed READ-ONLY)"
      % (cap_sha, CAP_BYTES))
    R("  trainer %s" % TRAINER_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (IMPORTED READ-ONLY; the"
      % (tr_sha, TRAINER_BYTES))
    R("    ridge architecture, feature map and split rule are the")
    R("    trainer's own code path)")
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
    R("  generation -- no stochastic draw exists; a rerun regenerates")
    R("  the identical budget, stronger than draw-once)")
    angles, samples = angle_grid(rows)
    R("  demand grid: derived from the corpus of record -- 360 angles")
    R("    per groove (the recorded 1.0 deg emission grid), 2 grooves")
    R("  coverage demands: %d admissible design cells x 720 = %d"
      % (len(SWEEP_D) * len(SWEEP_CY_ADMISSIBLE),
         len(SWEEP_D) * len(SWEEP_CY_ADMISSIBLE) * 720))
    R("  feasibility demands: %d fail-closed cells (C_y=%.1f) x 720 = %d"
      % (len(SWEEP_D), SWEEP_CY_FAILCLOSED, len(SWEEP_D) * 720))
    R("  warm-start demands: 4 held-out cells x 2 grooves x 2 handoff"
      " poses = 16")
    R("    x %d baseline seeds = %d baseline trials (the frozen budget)"
      % (len(BASELINE_SEEDS), 16 * len(BASELINE_SEEDS)))
    R("  stop condition: the budget is measured once and this report")
    R("    is the stop; no extension, no regeneration, no re-split")
    R("")

    # [ANCHOR] reproduction anchor ---------------------------------------
    R("[ANCHOR] REPRODUCTION ANCHOR (the regenerated d=0.2/C_y=0.0 cell")
    R("  must reproduce the corpus of record's recorded solution rows)")
    d0, cy0 = bt.discover_chosen_design(rows)
    if (d0, cy0) != (0.2, 0.0):
        fail_closed("chosen design is (%r, %r), the anchor cell is"
                    " (0.2, 0.0)" % (d0, cy0))
    qmap = {"groove_1": (d0, 0.0), "groove_2": (-d0, 0.0)}
    worst_anchor = 0.0
    for r in samples:
        g, _, _ = fc.groove_point(qmap[r["groove"]],
                                  r["plate_angle_deg"], (0.0, cy0))
        dev = dist2(g[0], g[1], r["gx"], r["gy"])
        worst_anchor = max(worst_anchor, dev)
        if dev > WITNESS_TOL:
            fail_closed("anchor violation on %s t=%.1f: regenerated"
                        " (%.12f, %.12f) vs recorded (%.12f, %.12f)"
                        " deviation %.3e > tol %.0e"
                        % (r["groove"], r["plate_angle_deg"], g[0],
                           g[1], r["gx"], r["gy"], dev, WITNESS_TOL))
    R("  %d/%d recorded groove_sample rows reproduced by the"
      % (len(samples), len(samples)))
    R("    regenerated cell (worst deviation %.3e units, tol %.0e)"
      " PASS" % (worst_anchor, WITNESS_TOL))
    R("")

    # [T] training (frozen architecture, one fit per trained cell) -------
    R("[T] TRAINING (the frozen per-groove Fourier-feature ridge,")
    R("  the trainer's own code path, one fit per TRAINED design cell)")
    R("  architecture: [1, cos(k*x), sin(k*x)] k=1..%d -> %d features;"
      % (bt.FOURIER_K, 1 + 2 * bt.FOURIER_K))
    R("    ridge lambda %s, closed-form solve, seed-free"
      % repr(bt.RIDGE_LAMBDA))
    R("  coverage growth, never an architecture change; the design")
    R("    channel stays absent from the feature map (the recorded")
    R("    disease, carried as data)")
    gt = {}   # ground truth: (d, cy, groove, i) -> (gx, gy)
    models = {}  # (d, cy) -> {groove: model}
    for d in SWEEP_D:
        for cy in SWEEP_CY_ADMISSIBLE:
            q1, q2 = (d, 0.0), (-d, 0.0)
            C = (0.0, cy)
            for g in ("groove_1", "groove_2"):
                q = q1 if g == "groove_1" else q2
                for i, t in enumerate(angles):
                    gg, _, _ = fc.groove_point(q, t, C)
                    gt[(d, cy, g, i)] = (gg[0], gg[1])
    trained_cells = [(d, cy) for d in (0.1, 0.2, 0.3)
                     for cy in SWEEP_CY_ADMISSIBLE]
    for (d, cy) in trained_cells:
        cell_models = {}
        for g in ("groove_1", "groove_2"):
            trows = [{"plate_angle_deg": t, "gx": gt[(d, cy, g, i)][0],
                      "gy": gt[(d, cy, g, i)][1]}
                     for i, t in enumerate(angles)
                     if i % SPLIT_MOD != SPLIT_REMAINDER]
            cell_models[g] = bt.train_ridge(trows)
        models[(d, cy)] = cell_models
        R("  trained cell d=%.1f C_y=%.2f on %d rows per groove"
          % (d, cy, len(angles) - len(angles) // SPLIT_MOD))
    R("  held-out design cells (never trained): d in {0.4, 0.5} x"
      " C_y in {0.0, 0.25} -- 4 cells")
    R("  the measured learned component for an extrapolation demand is")
    R("    the BOUNDARY model (the trained cell with the same C_y and")
    R("    the largest trained d = 0.3); the supplier LINE's answer is")
    R("    the standing design gate's (FALLBACK: CLOSED-FORM on the")
    R("    design mismatch, the re-probe semantics)")
    R("")

    # [C] the coverage measurement (the design axis, explicit) ----------
    R("[C] DESIGN-COVERAGE MEASUREMENT (the frozen distance function,")
    R("  Euclidean in task-layer units; classes per the freeze's")
    R("  coverage map)")
    classes = {"train_in_sample": [], "interpolation": [],
               "extrapolation": []}
    per_cell = {}
    for (d, cy) in [(d, cy) for d in SWEEP_D
                    for cy in SWEEP_CY_ADMISSIBLE]:
        trained = (d, cy) in models
        for g in ("groove_1", "groove_2"):
            for i, t in enumerate(angles):
                gx, gy = gt[(d, cy, g, i)]
                if trained:
                    mkey = (d, cy)
                    cls = ("train_in_sample"
                           if i % SPLIT_MOD != SPLIT_REMAINDER
                           else "interpolation")
                else:
                    mkey = (0.3, cy)
                    cls = "extrapolation"
                lx, ly = bt.predict(models[mkey][g], t)
                dd = dist2(lx, ly, gx, gy)
                classes[cls].append(dd)
                per_cell.setdefault((d, cy, cls), []).append(dd)
    R("  per-class table (learned component vs closed-form ground"
      " truth):")
    R("    class               count   median         worst")
    class_stats = {}
    for cls in ("train_in_sample", "interpolation", "extrapolation"):
        xs = classes[cls]
        med, wor = median(xs), max(xs)
        class_stats[cls] = (med, wor)
        R("    %-19s %6d  %.6e  %.6e" % (cls, len(xs), med, wor))
    med_e, wor_e = class_stats["extrapolation"]
    med_i, wor_i = class_stats["interpolation"]
    R("  extrapolation median / interpolation median: %.4f"
      % (med_e / med_i))
    R("  extrapolation worst / interpolation worst: %.4f"
      % (wor_e / wor_i))
    R("  extrapolation worst / tolerance (%.3f units): %.4f"
      % (TOL_POS_UNITS, wor_e / TOL_POS_UNITS))
    R("  per-cell detail (median | worst, units):")
    for d in SWEEP_D:
        for cy in SWEEP_CY_ADMISSIBLE:
            for cls in ("train_in_sample", "interpolation",
                        "extrapolation"):
                xs = per_cell.get((d, cy, cls))
                if xs:
                    R("    d=%.1f C_y=%.2f %-17s %.6e  %.6e"
                      % (d, cy, cls, median(xs), max(xs)))
    R("  the design-INTERPOLATION class is EMPTY by construction on")
    R("    the recorded grid (both admissible C_y values trained;")
    R("    every interior d point trained) -- interpolation is carried")
    R("    by the angle axis alone, recorded honestly per the freeze")
    R("  the frozen re-probe probe (groove_1, 90.0 deg, d=0.4/C_y=0.25)")
    R("    sits in the extrapolation class; its cell's demand at that")
    R("    angle is among the %d measured above" % len(classes[
        "extrapolation"]))
    R("")

    # [AX1] feasibility prediction ----------------------------------------
    R("[AX1] FEASIBILITY PREDICTION (the 3,600 fail-closed demands;")
    R("  does the supplier LINE predict infeasibility, or answer")
    R("  anyway?)")
    R("  the LINE: demand design != any trained design -> the standing")
    R("    design gate -> FALLBACK: CLOSED-FORM -> the closed-form")
    R("    supplier is the design's own recorded synthesis, whose")
    R("    tolerance gate fails closed on the rank-deficient handoff")
    R("    pair -> INFEASIBLE reported with the recorded reason")
    line_infeasible = 0
    for d in SWEEP_D:
        q1, q2 = (d, 0.0), (-d, 0.0)
        C = (0.0, SWEEP_CY_FAILCLOSED)
        tol_rows, rank_fail = fc.handoff_wc(q1, q2, C)
        if not rank_fail:
            fail_closed("cell d=%.1f C_y=%.1f did NOT fail closed as"
                        " recorded -- the fail-closed precedent is"
                        " violated; refusing to measure" % (d,
                                                            SWEEP_CY_FAILCLOSED))
        reason = [r["reason"] for r in tol_rows
                  if r.get("rank_deficient")][0]
        line_infeasible += 720
        R("  cell d=%.1f C_y=%.1f: rank-deficient at both handoffs"
          " (fail-closed)" % (d, SWEEP_CY_FAILCLOSED))
        R("    recorded reason: %s" % reason.replace("\n", " "))
        R("    LINE verdict on all 720 demands: INFEASIBLE"
          " (reported, never silent)")
    R("  LINE infeasibility predictions: %d/%d (the wiring carries"
      % (line_infeasible, len(SWEEP_D) * 720))
    R("    infeasibility through, exactly as the frozen lean)")
    R("  the learned component ALONE: trained on the boundary cell")
    R("    d=0.3/C_y=0.25 (nearest trained design space point); it")
    R("    cannot see the design channel and answers anyway:")
    blind = models[(0.3, 0.25)]
    answered = 0
    for d in SWEEP_D:
        for g in ("groove_1", "groove_2"):
            for i, t in enumerate(angles):
                lx, ly = bt.predict(blind[g], t)
                if math.isfinite(lx) and math.isfinite(ly):
                    answered += 1
    R("    %d/%d demands answered with finite (x, y) points;"
      % (answered, len(SWEEP_D) * 720))
    R("    infeasibility predictions from the learned component alone:"
      " 0")
    R("    -- the same recorded disease: the design information is")
    R("    absent from the function; the fallback wiring, not the")
    R("    learned component, carries infeasibility")
    R("")

    # [AX2] constrained-variant warm-start --------------------------------
    R("[AX2] CONSTRAINED-VARIANT WARM-START (the PR #44 redemption")
    R("  path; 16 handoff demands from the 4 held-out cells, the 1.5 mm")
    R("  tolerance band re-posed as the active constraint: land within")
    R("  %.3f units of the demand point; the clean closed form is" % TOL_POS_UNITS)
    R("  withheld from the searcher -- it sees only the objective")
    R("  oracle (distance to the demand point); search reappears)")
    R("  search: deterministic steepest descent on the oracle, step")
    R("    %.3f halved on non-improvement (min %.0e), max %d"
      " iterations" % (AX2_STEP0, AX2_STEP_MIN, AX2_MAX_ITER))
    R("  initializations: (a) WARM START = the boundary model's"
      " (d=0.3, same")
    R("    C_y) learned answer at the demand's angle; (b) RANDOM")
    R("    RESTART = seeded uniform in the per-groove TRAIN-split")
    R("    bounding box (the A6 precedent), the 3 recorded seeds")
    # train-split bbox per groove, over ALL trained cells (the line's
    # knowledge; extrapolation cells are unseen)
    bbox = {}
    for g in ("groove_1", "groove_2"):
        gxs, gys = [], []
        for (d, cy) in trained_cells:
            for i in range(len(angles)):
                if i % SPLIT_MOD != SPLIT_REMAINDER:
                    gx, gy = gt[(d, cy, g, i)]
                    gxs.append(gx)
                    gys.append(gy)
        bbox[g] = (min(gxs), max(gxs), min(gys), max(gys))

    def search(x0, y0, tx, ty):
        """Deterministic steepest descent on the oracle; returns
        (final distance, oracle calls)."""
        calls = [0]

        def oracle(x, y):
            calls[0] += 1
            return dist2(x, y, tx, ty)

        x, y = x0, y0
        best = oracle(x, y)
        step = AX2_STEP0
        for _ in range(AX2_MAX_ITER):
            if best <= TOL_POS_UNITS:
                break
            improved = False
            for dx, dy in ((step, 0.0), (-step, 0.0),
                           (0.0, step), (0.0, -step)):
                nx, ny = x + dx, y + dy
                v = oracle(nx, ny)
                if v < best:
                    x, y, best = nx, ny, v
                    improved = True
                    break
            if not improved:
                step /= 2.0
                if step < AX2_STEP_MIN:
                    break
        return best, calls[0]

    R("  per-demand table: cell | groove | t | warm: dist (calls) |"
      " seeds' dist")
    near_wins = 0
    near_total = 0
    far_wins = 0
    far_total = 0
    warm_calls_all = []
    base_calls_all = []
    for d in (0.4, 0.5):
        for cy in SWEEP_CY_ADMISSIBLE:
            for g in ("groove_1", "groove_2"):
                for t in HANDOFF_T_DEG:
                    i = angles.index(t)
                    tx, ty = gt[(d, cy, g, i)]
                    wx, wy = bt.predict(models[(0.3, cy)][g], t)
                    wd, wc = search(wx, wy, tx, ty)
                    warm_calls_all.append(wc)
                    seed_ds = []
                    seed_cs = []
                    for seed in BASELINE_SEEDS:
                        rng = random.Random(seed)
                        bx0, bx1, by0, by1 = bbox[g]
                        # draw order frozen: d, cy, groove, t, seed
                        rx = rng.uniform(bx0, bx1)
                        ry = rng.uniform(by0, by1)
                        sd, sc = search(rx, ry, tx, ty)
                        seed_ds.append(sd)
                        seed_cs.append(sc)
                        base_calls_all.append(sc)
                    best_sd = min(seed_ds)
                    win = (wd <= best_sd)
                    if d == 0.4:
                        near_total += 1
                        near_wins += 1 if win else 0
                    else:
                        far_total += 1
                        far_wins += 1 if win else 0
                    R("    d=%.1f C_y=%.2f %s t=%3.0f  %.6e (%3d) |"
                      " %s  %s"
                      % (d, cy, g, t, wd, wc,
                         " ".join("%.6e" % s for s in seed_ds),
                         "WIN/TIE" if win else "LOSE"))
    R("  near cells (d=0.4): warm start wins or ties the best seed on"
      " %d/%d" % (near_wins, near_total))
    R("  far cells (d=0.5): warm start wins or ties the best seed on"
      " %d/%d" % (far_wins, far_total))
    R("  warm-start trials: %d; baseline trials: %d (the frozen"
      " budget)" % (len(warm_calls_all), len(base_calls_all)))
    R("  (per-demand seed draws are ordered d, cy, groove, t, seed --"
      " the draw order is frozen at this staging so the trials are")
    R("  reproducible bit-for-bit)")
    R("")

    # [AX3] cost under demand variety --------------------------------------
    R("[AX3] COST UNDER DEMAND VARIETY (deterministic evaluation-call")
    R("  counts; wall-clock time is EXCLUDED by freeze -- the flip -02")
    R("  lesson: timing metadata is the recorded nondeterminism source)")
    R("  per-demand evaluation calls, by method:")
    R("    learned answer: 1 predict call (training amortized: %d"
      " ridge fits" % (len(trained_cells) * 2))
    R("      total, excluded from per-demand cost)")
    R("    closed-form answer: 1 groove_point call")
    R("    warm-start search (16 trials): mean %.1f oracle calls"
      " (min %d, max %d)" % (sum(warm_calls_all) / len(warm_calls_all),
                             min(warm_calls_all),
                             max(warm_calls_all)))
    R("    baseline search (48 trials): mean %.1f oracle calls"
      " (min %d, max %d)" % (sum(base_calls_all) /
                             len(base_calls_all),
                             min(base_calls_all),
                             max(base_calls_all)))
    R("  feasibility demands: LINE cost = 1 rank check per design")
    R("    (amortized over its 720 demands) + 1 gate read; learned-")
    R("    alone cost = 1 predict call -- the LINE's infeasibility")
    R("    report is CHEAP and CORRECT; the learned-alone answer is")
    R("    cheap and blind. Both recorded as data; the accuracy axis")
    R("    is preordained and powers nothing.")
    R("")

    # [H] honesty and labeling ---------------------------------------------
    R("[H] BOTH-DIRECTIONS HONESTY (the frozen clause)")
    R("  the expansion exists so the head-to-head is POWERED, not so")
    R("  it passes; a supplier that honestly loses to closed-form on")
    R("  a properly-powered head-to-head is a successful B1 outcome.")
    R("  on the accuracy axis the closed form scores 0 by definition")
    R("  (preordained, powering nothing); no result above amends the")
    R("  budget, the split, or the coverage map. Label: %s" % A4_LABEL)
    R("  the label-change event remains defined exactly as frozen and")
    R("  unfired; the design-conditioned representation is the FUTURE")
    R("  CORPUS DECISION the re-probe recorded -- this run measures")
    R("  design coverage and does not take it.")
    R("")

    # [READ] frozen-axis-prediction outcomes -------------------------------
    R("[READ] FROZEN-AXIS-PREDICTION OUTCOMES (recorded as data,")
    R("  never gates)")
    R("  AX1 the line reports infeasibility through the fallback's")
    R("    fail-closed wiring: %s (%d/%d)"
      % ("HELD" if line_infeasible == len(SWEEP_D) * 720 else
         "REFUTED", line_infeasible, len(SWEEP_D) * 720))
    lean2 = (near_wins == near_total and far_wins < far_total)
    R("  AX2 the warm start wins/ties on the near cells and degrades")
    R("    on the far cells: %s (near %d/%d, far %d/%d)"
      % ("HELD" if lean2 else "REFUTED (honest data)",
         near_wins, near_total, far_wins, far_total))
    R("  CRITIC the supplier's honest value lives in AX1/AX2, not in")
    R("    accuracy or cost: read on the two axis tables above --")
    R("    recorded as data, the critic's frozen prediction")
    R("  COVERAGE (the re-probe's recorded disease, measured at scale:")
    R("    the extrapolation class degrades vs the interpolation class")
    R("    -- ratio of medians %.4f): %s" % (med_e / med_i,
                                            "CONFIRMED" if med_e > med_i
                                            else "REFUTED"))
    if med_e > med_i:
        R("    the design channel is the disease; the design-")
        R("    conditioned representation is the recorded candidate for")
        R("    the future corpus decision")
    else:
        R("    honest data")
    R("")
    R("expansion reading: the budget was drawn exactly once, measured")
    R("once, and stopped; every number above is this run's own output.")
    R("Label: %s" % A4_LABEL)
    return R_out


if __name__ == "__main__":
    sys.exit(main())
