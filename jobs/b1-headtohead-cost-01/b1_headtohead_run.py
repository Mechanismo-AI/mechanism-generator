#!/usr/bin/env python3
"""Job b1-headtohead-cost-01: the Q5 endgame HEAD-TO-HEAD instrument
(run staging; frozen before any run; implements the freeze document
jobs/b1-headtohead-cost-01/JOB.md exactly; may not amend it).

The event the freeze froze: the learned supplier (representation 1.0,
consumed through the LINE) against the DIRECT ANALYTIC PATH -- the
STAGED flip-station capability script of record
(flip_capability.py AS STAGED: its declared design sweep and its
emitted corpus) -- at matched outcome quality on fresh demands.
Baseline (i), the measured oracle/restart search, is carried as the
RECORDED secondary row only (never re-measured here). Two currencies:
oracle calls and NEW-ANALYTIC-JOB event counts.

The fresh-demand split, frozen (drawn EXACTLY ONCE, READ from the
pinned corpus and instruments at run time, never transcribed):
  - IN-SCOPE class (4 demands): recorded-grid groove-point demands at
    the chosen design (the staged script's own emitted corpus), at
    plate-angle grid indices 4 and 89 -- the trainer's own held-out
    split (i %% 5 == 4): never trained on, and not among any recorded
    run's demand set (the transfer measured the handoff poses at
    t=0/180 only). The staged script answers these AS STAGED: the
    emitted corpus row itself (exact, 0 oracle calls, 0 new analytic
    jobs).
  - SCOPE-BOUNDARY class (8 demands): the same demand pattern at the
    two frozen MIDPOINT design cells -- ((0.1+0.2)/2, (0.0+0.25)/2)
    and ((0.2+0.3)/2, (0.0+0.25)/2) = (0.15, 0.125) and (0.25, 0.125)
    -- computed at run time from the supplier's frozen TRAIN cells,
    asserted OFF the staged script's declared sweep grid and not among
    the trained cells. These sit inside the representation run of
    record's VALIDATED interpolation span (the collapse bar's
    interpolation class), so the design-conditioned supplier answers
    them LEARNED through the LINE; the staged script AS STAGED does
    not parameterize them -- answering them analytically requires a
    NEW ANALYTIC JOB (one staged job per off-sweep cell; counted,
    NEVER staged by this instrument; engineering time, unmeasured,
    not translated into any number).

The scope predicate, frozen per the freeze's baseline naming: the
operative analytic baseline is the staged script's DECLARED
PARAMETERIZATION (its frozen sweep constants and emitted corpus), not
the family math's reach. The pre-declared counter-branch stands: if
the record's reader holds the closed-form function's mathematical
reach as controlling, the event is UNDERPOWERED on the scope axis --
an honest scope finding about the analytic path's reach, recorded,
never a re-draw.

Label-change permissions (written BEFORE the run, verbatim from the
freeze; nobody knows yet whether the run wins them): on a win, the
label changes to SUPPLIER OUTPUT (SCOPE-BOUNDARY COST CHANNEL)
authorizing exactly the scope-boundary cost claim scoped to
representation 1.0 and the measured classes -- nothing else; on a
no-win, SUPPLIER OUTPUT stands and the label-change event stays
defined and unfired. The label-change event itself, if any, is its
own later record.

Usage (repo root, the recorded standard):
  python jobs/b1-headtohead-cost-01/b1_headtohead_run.py
      --source-commit <40-hex-sha> > run1.txt
  (twice; external diff must be empty; exit 0)

Pure stdlib; ASCII only; Python 3.10+; no network; deterministic.
No wall-clock time appears anywhere in the report. The report IS
the stop record; NO artifact is written.
"""

import hashlib
import json
import math
import os
import platform
import re
import sys

JOB_ID = "b1-headtohead-cost-01"

# [P0] pins (the freeze's five carried pins, verbatim; fail-closed)
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
REPR_REL = os.path.join(
    "jobs", "b1-representation-01", "b1_representation_run.py")
REPR_SHA256 = (
    "5193b6b7a4adaacf169a5978cad53280298a0f2d0b842749e00236a7eba501e6")
REPR_BYTES = 29557
ORIG_REL = os.path.join(
    "jobs", "b1-warmstart-transfer-01", "b1_transfer_run.py")
ORIG_SHA256 = (
    "293a14ac5e3e11ea90727b5ec6542db2fed60e45bfa3af74a308f89d7ac945c6")
ORIG_BYTES = 25540
RERUN_REL = os.path.join(
    "jobs", "b1-warmstart-transfer-01", "b1_transfer_rerun.py")
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

# the freeze document's frozen numbers (cross-checks only; every
# measured value is READ from the pinned corpus at run time)
ANCHOR_D = 0.2             # the recorded case-study design (the
ANCHOR_CY = 0.0            # reproduction anchor cell)
BAND_UNITS = 0.015         # the recorded 1.5 mm handoff band

# the representation-1.0 coverage map (the supplier's training
# cells; carried unchanged from the representation job's freeze)
TRAIN_D = (0.1, 0.2, 0.3)
SWEEP_CY = (0.0, 0.25)
REPR_NFEAT = 147

# the frozen fresh-t rule: plate-angle grid 0-based indices 4 and 89
# (both satisfy the trainer's held-out split i % 5 == 4; never trained
# on; and are not the transfer's measured demands t=0/180)
HELD_OUT_IDX = (4, 89)

# the staged script's declared sweep (cross-checked against the
# pinned module at run time; the scope predicate's basis)
FC_SWEEP_D_EXPECTED = [0.1, 0.2, 0.3, 0.4, 0.5]
FC_SWEEP_CY_EXPECTED = [0.0, 0.25, 0.5]

# the recorded secondary row (baseline (i), carried as context only,
# never re-measured by this instrument)
REC_RUN = "PR #91 (the recorded transfer run of record)"
REC_RATIO = 0.0048
REC_WARM_CALLS_MEAN = 1.0
REC_BASE_CALLS_MEAN = 207.5
REC_AX2 = ("the recorded AX2 context datum (16/16 at mean 22.0 vs"
           " 211.5) -- context only, never this run's old side")

# the AX2 search spec, carried unchanged (the frozen comparison
# protocol; identical arithmetic to the recorded instruments)
AX2_MAX_ITER = 100
AX2_STEP0 = 0.01
AX2_STEP_MIN = 1e-12

STAND_LABEL = "SUPPLIER OUTPUT (the A4 label stands; the"
STAND_LABEL += " label-change event remains defined and unfired)"
WIN_LABEL = ("SUPPLIER OUTPUT (SCOPE-BOUNDARY COST CHANNEL) --"
             " authorizing exactly: the claim that the learned"
             " warm-start supplier answers fresh scope-boundary"
             " demands at matched outcome quality without a new"
             " analytic job, at the recorded cost ratio, scoped to"
             " representation 1.0 and the measured classes; recorded"
             " as its own label-change event with its own record."
             " Authorizing NOTHING ELSE: no accuracy claim in any"
             " class, no substitution reframe, no case-study C"
             " reopening, no broader-consumption claim beyond the"
             " frozen split")


class FailClosed(Exception):
    pass


def fail_closed(msg):
    raise FailClosed(msg)


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


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
        print("usage: b1_headtohead_run.py --source-commit"
              " <40-hex-sha>", file=sys.stderr)
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
    """One complete wiring + measurement pass (the head-to-head)."""
    R_out = []
    R = R_out.append

    R("b1-headtohead-cost-01 -- the Q5 endgame HEAD-TO-HEAD instrument")
    R("(run staging; frozen before any run; implements the freeze")
    R("  document jobs/b1-headtohead-cost-01/JOB.md exactly; no")
    R("  wall-clock time anywhere in this report)")
    R("  the learned supplier (representation 1.0 through the LINE)")
    R("  vs the DIRECT ANALYTIC PATH (the staged flip-station")
    R("  capability script of record, AS STAGED) at matched outcome")
    R("  quality on fresh demands; baseline (i) carried as the")
    R("  recorded secondary row only")
    R("python: %s" % platform.python_version())
    R("source commit: %s" % source_commit)
    R("")

    # [P0] pins ----------------------------------------------------------
    R("[P0] PIN CHECKS (fail-closed; the freeze's five carried pins)")
    cap_sha = pin_file(CAP_REL, CAP_SHA256, CAP_BYTES)
    tr_sha = pin_file(TRAINER_REL, TRAINER_SHA256, TRAINER_BYTES)
    repr_sha = pin_file(REPR_REL, REPR_SHA256, REPR_BYTES)
    orig_sha = pin_file(ORIG_REL, ORIG_SHA256, ORIG_BYTES)
    R("  capability instrument %s" % CAP_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (the OPERATIVE ANALYTIC"
      % (cap_sha, CAP_BYTES))
    R("    BASELINE: the staged script of record, its declared sweep")
    R("    and emitted corpus; consumed READ-ONLY as the distance")
    R("    oracle and ground-truth synthesizer)")
    R("  trainer %s" % TRAINER_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (IMPORTED READ-ONLY;"
      % (tr_sha, TRAINER_BYTES))
    R("    the loader, split rule and solve path are the trainer's own)")
    R("  representation instrument %s" % REPR_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (IMPORTED READ-ONLY;"
      % (repr_sha, REPR_BYTES))
    R("    the frozen 147-feature design-conditioned builder:")
    R("    phi_ext / train_ridge_ext / predict_ext are the pinned")
    R("    builder's own)")
    R("  original transfer instrument %s" % ORIG_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (pinned READ-ONLY as"
      % (orig_sha, ORIG_BYTES))
    R("    a protocol source; never imported, never executed)")
    bt, rows = load_anchor_corpus()
    R("  corpus of record %s" % CORPUS_REL)
    R("    sha256 %s -- PIN MATCH (the REPRODUCTION ANCHOR)"
      % CORPUS_SHA256)
    R("    provenance commit %s -- PIN MATCH" % CORPUS_PROVENANCE_COMMIT)
    R("")
    sys.path.insert(0, os.path.dirname(os.path.abspath(CAP_REL)))
    import flip_capability as fc  # noqa: E402 (read-only import)
    sys.path.insert(0, os.path.dirname(os.path.abspath(REPR_REL)))
    import b1_representation_run as br  # noqa: E402 (read-only)

    # [D] the consuming context, READ from the corpus ---------------------
    R("[D] THE CONSUMING CONTEXT (every value READ from the pinned")
    R("  corpus and instruments at run time, never transcribed)")
    d, cy = bt.discover_chosen_design(rows)
    if (d, cy) != (ANCHOR_D, ANCHOR_CY):
        fail_closed("the corpus's chosen design is (d=%r, C_y=%r); the"
                    " freeze's recorded case-study design is (d=%.1f,"
                    " C_y=%.1f)" % (d, cy, ANCHOR_D, ANCHOR_CY))
    qmap = {"groove_1": (d, 0.0), "groove_2": (-d, 0.0)}
    C = (0.0, cy)
    R("  recorded case-study design (discovered through the trainer's")
    R("    own path): d=%.1f C_y=%.2f" % (d, cy))
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
    angles = grids["groove_1"]
    R("  demand grid: the corpus's own recorded 1.0 deg emission grid,")
    R("    360 angles per groove, 2 grooves")
    band_rows = [r for r in rows if r["kind"] == "gate"
                 and r.get("name") == "handoff_tolerance"]
    if len(band_rows) != 1:
        fail_closed("expected exactly 1 handoff_tolerance gate row,"
                    " found %d" % len(band_rows))
    band = band_rows[0]["limit_units"]
    if band != BAND_UNITS or band != bt.TOL_POS_UNITS:
        fail_closed("the recorded handoff band is %r units; the freeze"
                    " froze %.3f (and the trainer pins %.3f)"
                    % (band, BAND_UNITS, bt.TOL_POS_UNITS))
    R("  recorded band (the handoff_tolerance gate row): %.3f units"
      " (1.5 mm) -- the demand's outcome-quality standard; matched")
    R("    quality = both sides in-band; exactness recorded as data")
    R("")

    # [ANCHOR] reproduction anchor ----------------------------------------
    R("[ANCHOR] REPRODUCTION ANCHOR (the recorded cell re-derived")
    R("  through the pinned oracle must reproduce every recorded")
    R("  groove_sample row exactly)")
    worst_anchor = 0.0
    for r in samples:
        g, _, _ = fc.groove_point(qmap[r["groove"]],
                                  r["plate_angle_deg"], C)
        dev = dist2(g[0], g[1], r["gx"], r["gy"])
        worst_anchor = max(worst_anchor, dev)
        if dev > bt.WITNESS_TOL:
            fail_closed("anchor violation on %s t=%.1f: deviation %.3e"
                        " > tol %.0e" % (r["groove"], r["plate_angle_deg"],
                                         dev, bt.WITNESS_TOL))
    R("  %d/%d recorded groove_sample rows reproduced (worst deviation"
      " %.3e units, tol %.0e) PASS"
      % (len(samples), len(samples), worst_anchor, bt.WITNESS_TOL))
    R("")

    # [S] the supplier, consumed through the LINE ------------------------
    R("[S] THE SUPPLIER THROUGH THE LINE (representation 1.0; the")
    R("  standing design gate; the LINE wiring for THIS event declared")
    R("  at staging with its recorded basis)")
    if bt.FOURIER_K != 24:
        fail_closed("the trainer's FOURIER_K is %r; the freeze froze 24"
                    % bt.FOURIER_K)
    if bt.RIDGE_LAMBDA != 1e-8:
        fail_closed("the trainer's RIDGE_LAMBDA is %r; the freeze froze"
                    " 1e-08" % bt.RIDGE_LAMBDA)
    if bt.SPLIT_MOD != 5 or bt.SPLIT_REMAINDER != 4:
        fail_closed("the trainer's split rule is (mod %d, remainder %d);"
                    " the freeze froze (5, 4)"
                    % (bt.SPLIT_MOD, bt.SPLIT_REMAINDER))
    nfeat = 1 + 2 * bt.FOURIER_K + 2 + 4 * bt.FOURIER_K
    if nfeat != REPR_NFEAT:
        fail_closed("the extended map computes %d features; the freeze"
                    " froze 147" % nfeat)
    probe = br.phi_ext(0.0, ANCHOR_D, ANCHOR_CY, bt.FOURIER_K)
    if len(probe) != REPR_NFEAT:
        fail_closed("the pinned builder emits %d features; the freeze"
                    " froze 147" % len(probe))
    R("  architecture (representation 1.0): 49 Fourier features + the")
    R("    design channel [d, C_y] (2) + first-order products (96) =")
    R("    %d features per groove; ridge lambda %s, seed-free"
      % (nfeat, repr(bt.RIDGE_LAMBDA)))
    models = {}
    ntrain_per_cell = len(angles) - len(angles) // bt.SPLIT_MOD
    for g in ("groove_1", "groove_2"):
        trows = []
        for td in TRAIN_D:
            for tcy in SWEEP_CY:
                q = (td, 0.0) if g == "groove_1" else (-td, 0.0)
                for i, t in enumerate(angles):
                    if i % bt.SPLIT_MOD != bt.SPLIT_REMAINDER:
                        gg, _, _ = fc.groove_point(q, t, (0.0, tcy))
                        trows.append({"plate_angle_deg": t,
                                      "d": td, "cy": tcy,
                                      "gx": gg[0], "gy": gg[1]})
        models[g] = br.train_ridge_ext(bt, trows, bt.FOURIER_K,
                                       bt.RIDGE_LAMBDA)
        R("  trained %s on %d rows (%d cells x %d train samples per"
          " groove)" % (g, len(trows),
                        len(TRAIN_D) * len(SWEEP_CY), ntrain_per_cell))
    R("  the LINE, declared for THIS event (the wiring implements the")
    R("    freeze; the recorded basis: PR #95 merged -- representation")
    R("    1.0 LANDS as the supplier; the representation run of")
    R("    record's collapse bar MET on the interpolation class,")
    R("    median 8.365528e-06 units = 0.0006x the band): a demanded")
    R("    design among the supplier's %d TRAIN cells, or among the"
      % (len(TRAIN_D) * len(SWEEP_CY)))
    R("    frozen MIDPOINT cells inside the validated interpolation")
    R("    span, answers LEARNED through the design-conditioned map;")
    R("    any other demanded design falls back CLOSED-FORM (the")
    R("    re-probe semantics, carried)")

    # the frozen scope-boundary cells: the midpoint rule, computed at
    # run time from the supplier's frozen TRAIN cells (never
    # transcribed), asserted off the staged sweep and off the trained
    # cells
    if list(fc.SWEEP_D) != FC_SWEEP_D_EXPECTED:
        fail_closed("the staged script's declared SWEEP_D is %r; the"
                    " freeze cross-checked %r"
                    % (fc.SWEEP_D, FC_SWEEP_D_EXPECTED))
    if list(fc.SWEEP_CY) != FC_SWEEP_CY_EXPECTED:
        fail_closed("the staged script's declared SWEEP_CY is %r; the"
                    " freeze cross-checked %r"
                    % (fc.SWEEP_CY, FC_SWEEP_CY_EXPECTED))
    mid_cy = (SWEEP_CY[0] + SWEEP_CY[1]) / 2.0
    mid_cells = ((TRAIN_D[0] + TRAIN_D[1]) / 2.0,
                 (TRAIN_D[1] + TRAIN_D[2]) / 2.0)
    for md in mid_cells:
        if md in fc.SWEEP_D:
            fail_closed("midpoint cell d=%r IS on the staged script's"
                        " declared sweep -- the scope-boundary class"
                        " would be preordained" % md)
        if md in TRAIN_D:
            fail_closed("midpoint cell d=%r IS a trained cell" % md)
    if mid_cy in fc.SWEEP_CY:
        fail_closed("midpoint C_y=%r IS on the staged script's declared"
                    " sweep" % mid_cy)
    R("  the staged script's declared sweep (READ from the pinned")
    R("    module): d in %s x C_y in %s (%d cells); its emitted corpus"
      % (fc.SWEEP_D, fc.SWEEP_CY,
         len(fc.SWEEP_D) * len(fc.SWEEP_CY)))
    R("    covers the chosen design alone -- the staged script answers")
    R("    in-scope demands AS STAGED: its own emitted rows")
    R("  the frozen scope-boundary cells (the midpoint rule, computed")
    R("    from the supplier's TRAIN cells): (%.2f, %.3f) and (%.2f,"
      " %.3f) -- inside the supplier's validated interpolation span,"
      % (mid_cells[0], mid_cy, mid_cells[1], mid_cy))
    R("    OFF the staged script's declared sweep grid, not trained")
    R("    cells; answering them analytically requires a NEW ANALYTIC")
    R("    JOB per cell (counted, never staged here)")

    def line_answer(g, t_deg, demand_d, demand_cy):
        trained = (demand_d in TRAIN_D) and (demand_cy in SWEEP_CY)
        midp = (demand_cy == mid_cy) and (demand_d in mid_cells)
        if trained or midp:
            return br.predict_ext(models[g], t_deg, demand_d,
                                  demand_cy, bt.FOURIER_K), "LEARNED"
        q = {"groove_1": (demand_d, 0.0),
             "groove_2": (-demand_d, 0.0)}[g]
        gp, _, _ = fc.groove_point(q, t_deg, (0.0, demand_cy))
        return (gp[0], gp[1]), "FALLBACK: CLOSED-FORM"

    R("")

    # [M] the frozen measurement ------------------------------------------
    R("[M] THE MEASUREMENT (the fresh-demand split, frozen; drawn")
    R("  EXACTLY ONCE; the report IS the stop record, NO artifact")
    R("  written)")
    R("  demand pattern: a recorded-grid groove-point demand (design,")
    R("    groove, plate angle); the answer is the groove point at the")
    R("    demanded sample, landing inside the %.3f-unit band" % band)
    R("  the frozen fresh-t rule: plate-angle grid indices %s (both"
      % (HELD_OUT_IDX,))
    R("    satisfy the trainer's held-out split i %% %d == %d: never"
      % (bt.SPLIT_MOD, bt.SPLIT_REMAINDER))
    R("    trained on; not the transfer's measured demands t=0/180;")
    R("    nothing here re-grades any recorded outcome)")
    R("  IN-SCOPE class: the chosen design x 2 grooves x 2 held-out t")
    R("    = %d demands; the staged script answers AS STADED->AS"
      " STAGED: its emitted corpus row (exact, 0 calls, 0 new jobs)"
      % (2 * len(HELD_OUT_IDX)))
    R("  SCOPE-BOUNDARY class: 2 midpoint cells x 2 grooves x 2"
      " held-out t")
    R("    = %d demands; the staged script AS STAGED does not"
      % (2 * 2 * len(HELD_OUT_IDX)))
    R("    parameterize these cells -- answering them analytically")
    R("    requires a NEW ANALYTIC JOB per cell (counted, never")
    R("    staged; engineering time, unmeasured, not translated)")
    R("  search (the AX2 spec, carried unchanged): steepest descent on")
    R("    the distance oracle, initial step %.3f halved on"
      " non-improvement" % AX2_STEP0)
    R("    (min %.0e), max %d iterations, early stop inside the %.3f"
      " unit band" % (AX2_STEP_MIN, AX2_MAX_ITER, band))
    R("  the searcher is WITHHELD the closed form -- it sees only the")
    R("    distance oracle; the warm start comes from the supplier")

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
            if best <= band:
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

    # build the frozen demand set, READ at run time
    demands = []
    by_gt = {}
    for r in samples:
        by_gt[(r["groove"], r["plate_angle_deg"])] = (r["gx"], r["gy"])
    for idx in HELD_OUT_IDX:
        if idx % bt.SPLIT_MOD != bt.SPLIT_REMAINDER:
            fail_closed("frozen fresh-t index %d is NOT in the"
                        " trainer's held-out split -- the freeze's"
                        " freshness clause is violated" % idx)
        t = angles[idx]
        if t in (0.0, 180.0):
            fail_closed("frozen fresh-t index %d resolves to a"
                        " transfer-measured demand" % idx)
        for g in ("groove_1", "groove_2"):
            if (g, t) not in by_gt:
                fail_closed("no corpus row for %s at t=%r" % (g, t))
            demands.append({"cls": "IN-SCOPE", "g": g, "t": t,
                            "d": d, "cy": cy,
                            "target": by_gt[(g, t)],
                            "analytic": "STAGED: emitted corpus row"
                                       " (exact, 0 calls, 0 new jobs)"})
    for md in mid_cells:
        for idx in HELD_OUT_IDX:
            t = angles[idx]
            for g in ("groove_1", "groove_2"):
                q = (md, 0.0) if g == "groove_1" else (-md, 0.0)
                gp, _, _ = fc.groove_point(q, t, (0.0, mid_cy))
                demands.append({"cls": "SCOPE-BOUNDARY", "g": g,
                                "t": t, "d": md, "cy": mid_cy,
                                "target": (gp[0], gp[1]),
                                "analytic": "REQUIRES NEW ANALYTIC JOB"
                                           " (off the staged script's"
                                           " declared sweep; counted,"
                                           " never staged)"})
    if len(demands) != 12:
        fail_closed("the frozen demand set has %d demands; the freeze"
                    " froze 12" % len(demands))

    R("")
    R("  per-demand table (recorded per demand: final distance,")
    R("    in-band, oracle calls, the LINE gate, the analytic side):")
    R("    class           groove   t  design | warm: init -> final"
      " (calls) band gate | analytic side")
    rows_by_cls = {"IN-SCOPE": [], "SCOPE-BOUNDARY": []}
    for dm in demands:
        tx, ty = dm["target"]
        (wx, wy), gate = line_answer(dm["g"], dm["t"], dm["d"], dm["cy"])
        w_init = dist2(wx, wy, tx, ty)
        wd, wc = search(wx, wy, tx, ty)
        rec = {"dm": dm, "gate": gate, "wd": wd, "wc": wc,
               "in_band": wd <= band, "w_init": w_init}
        rows_by_cls[dm["cls"]].append(rec)
        R("    %-14s %-8s %3.0f (%.2f,%.3f) | %.6e -> %.6e (%3d) %s"
          " %s | %s"
          % (dm["cls"], dm["g"], dm["t"], dm["d"], dm["cy"],
             w_init, wd, wc,
             "IN" if wd <= band else "OUT", gate, dm["analytic"]))
    n_in = len(rows_by_cls["IN-SCOPE"])
    n_sb = len(rows_by_cls["SCOPE-BOUNDARY"])
    in_band_in = sum(1 for r in rows_by_cls["IN-SCOPE"] if r["in_band"])
    in_band_sb = sum(1 for r in rows_by_cls["SCOPE-BOUNDARY"]
                     if r["in_band"])
    learned_sb = sum(1 for r in rows_by_cls["SCOPE-BOUNDARY"]
                      if r["gate"] == "LEARNED")
    calls_all = [r["wc"] for r in
                 rows_by_cls["IN-SCOPE"] + rows_by_cls["SCOPE-BOUNDARY"]]
    calls_mean = sum(calls_all) / len(calls_all)
    R("")
    R("  CURRENCY 1 (oracle calls): the learned side's warm-start mean")
    R("    %.1f over %d demands (%.1f in-scope, %.1f scope-boundary)"
      % (calls_mean, len(calls_all),
         sum(r["wc"] for r in rows_by_cls["IN-SCOPE"]) / n_in,
         sum(r["wc"] for r in rows_by_cls["SCOPE-BOUNDARY"]) / n_sb))
    R("    SECONDARY ROW (baseline (i), the restart search, carried")
    R("    as the RECORDED context only, never re-measured: %s:"
      % REC_RUN)
    R("    warm %.1f vs baseline %.1f, ratio %.4f; %s"
      % (REC_WARM_CALLS_MEAN, REC_BASE_CALLS_MEAN, REC_RATIO, REC_AX2))
    R("  CURRENCY 2 (new-analytic-job event counts):")
    R("    learned side: %d new analytic jobs for %d/%d demands"
      % (0, len(demands), len(demands)))
    R("    analytic side: %d new jobs for the %d in-scope demands"
      " (answered by the staged corpus rows)"
      % (0, n_in))
    R("    analytic side: %d NEW ANALYTIC JOB EVENTS for the %d"
      " scope-boundary demands (one per off-sweep cell; engineering"
      % (len(mid_cells), n_sb))
    R("    time, unmeasured, not translated); %d/%d of all fresh"
      " demands answerable by the staged script as staged"
      % (n_in, len(demands)))
    R("    per-demand binary: the learned supplier answers %d/%d"
      " fresh demands without a new analytic job"
      % (len(demands), len(demands)))
    R("  stop condition: the split was drawn once, measured once; no")
    R("    extension, no regeneration, no re-draw; an underpowered or")
    R("    failed measurement is a recorded finding, never a budget")
    R("    re-open")
    R("")

    # [MOD] the mod-count row ---------------------------------------------
    R("[MOD] ZERO-MODIFICATION ROW (reciprocity in reverse; the")
    R("  pinned artifacts re-hashed after the measurement)")
    mods = 0
    for rel, sha, nbytes in ((CAP_REL, CAP_SHA256, CAP_BYTES),
                             (TRAINER_REL, TRAINER_SHA256,
                              TRAINER_BYTES),
                             (REPR_REL, REPR_SHA256, REPR_BYTES),
                             (ORIG_REL, ORIG_SHA256, ORIG_BYTES),
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

    # [H] both-directions honesty and the frozen labels -------------------
    R("[H] BOTH-DIRECTIONS HONESTY AND THE FROZEN LABELS")
    R("  the three-cell tie reading, PRE-DECLARED (frozen before the")
    R("    run): a TIE on in-scope demands records the division of")
    R("    labor measured -- analytic synthesis remains the winning")
    R("    supplier in-scope; the learned supplier wins the")
    R("    scope-boundary channel; a tie is NOT a null result")
    R("  an honest LOSS grades PASS: both numbers are in the table")
    R("  exactness is recorded as data (the analytic side's in-scope")
    R("    answers are exact; the learned side's are in-band) -- the")
    R("    accuracy clause stays recorded as structurally unreachable")
    R("    in this family, and the three-axis prediction stays live")
    R("  the substitution guard stands: no outcome here reframes the")
    R("    supplier as good enough; the 17,930x accuracy disease is")
    R("    untouched; case study C stays CLOSED at its recorded")
    R("    outcomes")
    R("  FRESHNESS, disclosed: the fresh-t rule sits in the trainer's")
    R("    own held-out split (never trained); the midpoint cells are")
    R("    off the staged sweep and off the trained cells; the")
    R("    representation run measured interpolation-class ACCURACY at")
    R("    its own frozen cells -- accuracy measurement is not supply")
    R("    rehearsal, and no recorded run has ever SUPPLIED an answer")
    R("    at these cells; nothing here re-grades any recorded")
    R("    outcome")
    R("  REHEARSAL, disclosed: this instrument is desk-validated")
    R("    against the pinned sources (the re-run instrument's")
    R("    structure, AX2 search code path, builder functions, the")
    R("    trainer's constants and fail-closed loader; the staged")
    R("    script's declared sweep constants) and syntax-compiled")
    R("    only; it has NEVER been executed at staging -- no run is")
    R("    claimed by the staging")
    R("  LABEL, frozen in advance (the freeze's own words): on a win")
    R("    the label changes to SUPPLIER OUTPUT (SCOPE-BOUNDARY COST")
    R("    CHANNEL) authorizing exactly the scope-boundary cost claim")
    R("    scoped to representation 1.0 and the measured classes --")
    R("    nothing else; the label-change event itself is its own")
    R("    later record; on a no-win, SUPPLIER OUTPUT stands")
    R("")

    # [READ] the frozen prediction, read on this run's own output ---------
    R("[READ] FROZEN-PREDICTION OUTCOMES (recorded as data, never")
    R("  gates)")
    primary = (in_band_sb == n_sb and learned_sb == n_sb)
    R("  PRIMARY (the restated clause, the declared amendment's")
    R("    operative win condition) -- on the scope-boundary class")
    R("    the learned supplier answers fresh demands in-band at")
    R("    matched outcome quality with ZERO new analytic jobs where")
    R("    the analytic path requires %d: %s (LEARNED %d/%d, in-band"
      % (len(mid_cells),
         "FIRED" if primary else "REFUTED (honest data)",
         learned_sb, n_sb))
    R("    %d/%d; learned new-analytic-jobs 0)")
    tie = (in_band_in == n_in)
    R("  THE IN-SCOPE CELL (the pre-declared tie reading) -- the")
    R("    learned supplier in-band %d/%d and the staged script exact"
      % (in_band_in, n_in))
    R("    on every in-scope demand: %s -- the division of labor"
      % ("TIE" if tie else "NOT A TIE (honest data; see"
                                  " counter-branch 1)"))
    R("    measured: analytic synthesis remains the winning supplier")
    R("    in-scope; the learned supplier wins the scope-boundary")
    R("    channel; NOT a null result")
    cb1 = (in_band_sb < n_sb) or (learned_sb < n_sb) or (not tie)
    R("  THE HONEST COUNTER-BRANCH 1 (portability): %s"
      % ("NOT FIRED" if not cb1 else
         "FIRED -- a PORTABILITY finding about the supplier at the"
         " measured cells/angles; recorded as data, never a gate"
         " change, never a silent re-tune"))
    R("  THE HONEST COUNTER-BRANCH 2 (the scope finding, pre-declared")
    R("    alternative reading): the scope predicate frozen here is")
    R("    the STAGED SCRIPT'S DECLARED PARAMETERIZATION (its frozen")
    R("    sweep constants and emitted corpus) per the freeze's")
    R("    baseline naming; the closed-form FUNCTION, when invoked")
    R("    directly, evaluates off-sweep designs exactly -- if the")
    R("    record's reader holds the math's reach as controlling, the")
    R("    event is UNDERPOWERED on the scope axis: an honest scope")
    R("    finding about the analytic path's reach, recorded, never a")
    R("    re-draw")
    R("  THE HONEST COUNTER-BRANCH 3 (wiring): the mod-count row is 0")
    R("    and every demanded design consumed the supplier through")
    R("    the LINE without modifying a pinned artifact: NOT FIRED (a")
    R("    nonzero mod-count FAILS CLOSED above)")
    R("  LABEL: %s"
      % (WIN_LABEL if primary else STAND_LABEL))
    R("")
    R("head-to-head reading: the %d fresh demands were drawn exactly"
      % len(demands))
    R("once, measured once, and stopped; every number above is this")
    R("run's own output; no artifact was written. The label-change")
    R("event, if this run wins it, is its own later record.")
    return R_out


if __name__ == "__main__":
    sys.exit(main())
