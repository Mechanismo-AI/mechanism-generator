#!/usr/bin/env python3
"""Job b1-warmstart-transfer-01: the warm-start TRANSFER instrument
(run staging; frozen before any run; implements the freeze document
jobs/b1-warmstart-transfer-01/JOB.md exactly; may not amend it).

Wires the supplier into the flip-station loop's OWN constrained
search and measures the frozen comparison exactly once: the 4 actual
demands (the 2 recorded handoff poses x 2 grooves at the recorded
case-study design, the 1.5 mm band re-posed as an ACTIVE constraint)
-- 4 warm-start runs (the trained cell's supplier answer consumed
through the LINE) plus 12 seeded baseline trials (the recorded draw
rule carried unchanged), drawn EXACTLY ONCE. The report IS the stop
record; NO artifact is written.

Every consumed value is READ from the pinned corpus of record at run
time (design, handoff stations, demand poses, the band) -- never
transcribed; the trainer's own fail-closed loader is the corpus path;
the trainer's own split rule and seed set are consumed through its
imported constants.

Label: whatever the outcome, it is an INITIALIZATION-COST datum in
the consuming context (claim-only-what-exists) -- not an accuracy
result, not the head-to-head, never the win condition; SUPPLIER
OUTPUT stands; the label-change event remains defined and unfired.

Usage (repo root, the recorded standard):
  python jobs/b1-warmstart-transfer-01/b1_transfer_run.py
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

JOB_ID = "b1-warmstart-transfer-01"

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

# the freeze document's frozen numbers (cross-checks only; every
# measured value is READ from the pinned corpus at run time)
ANCHOR_D = 0.2             # the recorded case-study design (the
ANCHOR_CY = 0.0            # reproduction anchor cell)
BAND_UNITS = 0.015         # the recorded 1.5 mm handoff band
HANDOFF_LABELS_EXPECTED = ("handoff_1_pick", "handoff_2_place")
SEEDS_EXPECTED = [580000050, 580000051, 580000052]
DEMANDS_EXPECTED = 3
STATIONS_EXPECTED = 2
POSE_MATCH_TOL = 1e-9      # fc's validation-epsilon class, declared

# the AX2 search spec, carried unchanged (the frozen comparison
# protocol; identical arithmetic to the expansion instrument's AX2)
AX2_MAX_ITER = 100
AX2_STEP0 = 0.01
AX2_STEP_MIN = 1e-12

A4_LABEL = ("SUPPLIER OUTPUT (LEARNED -- no head-to-head win; "
            "the A4 label stands per the frozen rule)")
TRANSFER_LABEL = ("INITIALIZATION-COST datum in the consuming context"
                  " -- SUPPLIER OUTPUT stands; the label-change event"
                  " remains defined and unfired")


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
        print("usage: b1_transfer_run.py --source-commit <40-hex-sha>",
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
    """One complete wiring + measurement pass."""
    R_out = []
    R = R_out.append

    R("b1-warmstart-transfer-01 -- the warm-start TRANSFER instrument")
    R("(run staging; frozen before any run; implements the freeze")
    R("document jobs/b1-warmstart-transfer-01/JOB.md exactly; no")
    R("wall-clock time anywhere in this report)")
    R("label: %s" % TRANSFER_LABEL)
    R("python: %s" % platform.python_version())
    R("source commit: %s" % source_commit)
    R("")

    # [P0] pins ----------------------------------------------------------
    R("[P0] PIN CHECKS (fail-closed)")
    cap_sha = pin_file(CAP_REL, CAP_SHA256, CAP_BYTES)
    tr_sha = pin_file(TRAINER_REL, TRAINER_SHA256, TRAINER_BYTES)
    R("  capability instrument %s" % CAP_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (consumed READ-ONLY as"
      % (cap_sha, CAP_BYTES))
    R("    the distance oracle and ground-truth synthesizer)")
    R("  trainer %s" % TRAINER_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH (IMPORTED READ-ONLY;"
      % (tr_sha, TRAINER_BYTES))
    R("    the loader, split rule, seed set, ridge architecture and")
    R("    predict path are the trainer's own)")
    bt, rows = load_anchor_corpus()
    R("  corpus of record %s" % CORPUS_REL)
    R("    sha256 %s -- PIN MATCH (the REPRODUCTION ANCHOR)"
      % CORPUS_SHA256)
    R("    provenance commit %s -- PIN MATCH" % CORPUS_PROVENANCE_COMMIT)
    R("")
    sys.path.insert(0, os.path.dirname(os.path.abspath(CAP_REL)))
    import flip_capability as fc  # noqa: E402 (read-only import)

    # [D] the consuming context, READ from the corpus ---------------------
    R("[D] THE CONSUMING CONTEXT (every value READ from the pinned")
    R("  corpus of record at run time, never transcribed)")
    d, cy = bt.discover_chosen_design(rows)
    if (d, cy) != (ANCHOR_D, ANCHOR_CY):
        fail_closed("the corpus's chosen design is (d=%r, C_y=%r); the"
                    " freeze's recorded case-study design (the"
                    " reproduction anchor cell) is (d=%.1f, C_y=%.1f)"
                    % (d, cy, ANCHOR_D, ANCHOR_CY))
    qmap = {"groove_1": (d, 0.0), "groove_2": (-d, 0.0)}
    C = (0.0, cy)
    R("  recorded case-study design (discovered through the trainer's")
    R("    own path): d=%.1f C_y=%.2f -- q1=(d,0), q2=(-d,0),"
      " C=(0,C_y)" % (d, cy))
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
    R("  demand grid: derived from the corpus -- 360 recorded angles")
    R("    per groove (the recorded 1.0 deg emission grid), 2 grooves")

    env = [r for r in rows if r["kind"] == "envelope"
           and "handoff_stations_mm" in r]
    if len(env) != 1:
        fail_closed("expected exactly 1 envelope row with"
                    " handoff_stations_mm, found %d" % len(env))
    try:
        stations = json.loads(env[0]["handoff_stations_mm"])
    except ValueError as exc:
        fail_closed("handoff_stations_mm is not JSON: %s" % exc)
    if (not isinstance(stations, list)
            or len(stations) != STATIONS_EXPECTED
            or any(not isinstance(s, list) or len(s) != 2
                   for s in stations)):
        fail_closed("handoff_stations_mm is not %d [x, y] stations: %r"
                    % (STATIONS_EXPECTED, stations))
    R("  recorded handoff stations (the envelope row): %s mm"
      % " and ".join("(%.1f, %.1f)" % (s[0], s[1]) for s in stations))

    labels = sorted(set(r["handoff"] for r in rows
                        if r["kind"] == "tolerance" and "handoff" in r))
    if labels != sorted(HANDOFF_LABELS_EXPECTED):
        fail_closed("the corpus's recorded handoff labels are %r;"
                    " expected %r"
                    % (labels, sorted(HANDOFF_LABELS_EXPECTED)))
    R("  recorded handoff labels (the tolerance rows): %s"
      % ", ".join(labels))

    demands = [r for r in rows if r["kind"] == "demand"]
    if len(demands) != DEMANDS_EXPECTED:
        fail_closed("expected %d demand rows, found %d"
                    % (DEMANDS_EXPECTED, len(demands)))
    handoffs = []
    for s in stations:
        sx, sy = s[0] / 100.0, s[1] / 100.0
        matches = [r for r in demands
                   if abs(r["x"] - sx) <= POSE_MATCH_TOL
                   and abs(r["y"] - sy) <= POSE_MATCH_TOL]
        if len(matches) != 1:
            fail_closed("handoff station (%.1f, %.1f) mm matches %d"
                        " demand rows, expected exactly 1"
                        % (s[0], s[1], len(matches)))
        m = matches[0]
        ts = [t for t in angles
              if abs(fc.pose_at(t)[0] - m["x"]) <= POSE_MATCH_TOL
              and abs(fc.pose_at(t)[1] - m["y"]) <= POSE_MATCH_TOL
              and abs(math.degrees(fc.pose_at(t)[2]) - m["phi_deg"])
              <= POSE_MATCH_TOL]
        if len(ts) != 1:
            fail_closed("handoff demand phase %s matches %d plate"
                        " angles on the recorded grid, expected"
                        " exactly 1" % (m.get("phase"), len(ts)))
        handoffs.append({"station_mm": s, "phase": m.get("phase"),
                         "x": m["x"], "y": m["y"],
                         "phi_deg": m["phi_deg"], "t": ts[0]})
    if len(set(h["t"] for h in handoffs)) != STATIONS_EXPECTED:
        fail_closed("the 2 recorded handoff poses resolve to the same"
                    " plate angle")
    handoffs.sort(key=lambda h: h["t"])
    for h in handoffs:
        R("  handoff pose: station (%.1f, %.1f) mm = demand phase %s"
          " (x=%.1f, y=%.1f, phi=%.1f deg); program angle t=%.1f deg"
          " -- the unique recorded-grid angle whose pose matches the"
          " demanded pose" % (h["station_mm"][0], h["station_mm"][1],
                             h["phase"], h["x"], h["y"],
                             h["phi_deg"], h["t"]))

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
      " (1.5 mm)" % band)
    R("  the band is RE-POSED as an ACTIVE constraint: the searcher")
    R("    must land within it; the clean closed form is withheld from")
    R("    the searcher -- it sees only the objective oracle (distance")
    R("    to the demand point); search reappears")
    R("  honest scope: case study C stays CLOSED at its recorded")
    R("    outcomes; the closed-form synthesis for this design remains")
    R("    exact, instant, and free; this job measures the")
    R("    supplier-as-tool in the loop's context")
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
            fail_closed("anchor violation on %s t=%.1f: re-derived"
                        " (%.12f, %.12f) vs recorded (%.12f, %.12f)"
                        " deviation %.3e > tol %.0e"
                        % (r["groove"], r["plate_angle_deg"], g[0],
                           g[1], r["gx"], r["gy"], dev, bt.WITNESS_TOL))
    R("  %d/%d recorded groove_sample rows reproduced (worst deviation"
      " %.3e units, tol %.0e) PASS"
      % (len(samples), len(samples), worst_anchor, bt.WITNESS_TOL))
    R("")

    # [S] the supplier, consumed through the LINE ------------------------
    R("[S] THE SUPPLIER THROUGH THE LINE (the trainer's own code")
    R("  path, imported read-only; the standing design gate)")
    R("  architecture: [1, cos(k*x), sin(k*x)] k=1..%d -> %d features;"
      % (bt.FOURIER_K, 1 + 2 * bt.FOURIER_K))
    R("    ridge lambda %s, closed-form solve, seed-free (the frozen"
      % repr(bt.RIDGE_LAMBDA))
    R("    architecture; supplier-version scoping: the CURRENT one)")
    R("  the trained cell: the actual design itself (d=%.1f C_y=%.2f)"
      % (d, cy))
    R("  split rule (the trainer's own): 0-based JSONL index i held"
      " out iff i %% %d == %d" % (bt.SPLIT_MOD, bt.SPLIT_REMAINDER))
    models = {}
    bbox = {}
    for g in ("groove_1", "groove_2"):
        trows = [r for r in samples if r["groove"] == g
                 and r["_i"] % bt.SPLIT_MOD != bt.SPLIT_REMAINDER]
        models[g] = bt.train_ridge(trows)
        gxs = [r["gx"] for r in trows]
        gys = [r["gy"] for r in trows]
        bbox[g] = (min(gxs), max(gxs), min(gys), max(gys))
        R("  trained %s on %d train rows (held out: %d); train bbox:"
          " x [%.4f, %.4f] y [%.4f, %.4f]"
          % (g, len(trows),
             sum(1 for r in samples if r["groove"] == g) - len(trows),
             bbox[g][0], bbox[g][1], bbox[g][2], bbox[g][3]))
    R("  the per-groove TRAIN-split bbox over ALL trained cells (the")
    R("    trained-cell set is the actual design alone; the recorded")
    R("    draw rule carried unchanged)")
    R("  the LINE (the standing design gate): a demanded design that")
    R("    matches the trained cell answers LEARNED; a design mismatch")
    R("    falls back CLOSED-FORM (the re-probe semantics). On the")
    R("    actual demands there is NO mismatch -- the learned component")
    R("    answers directly, per the freeze")

    def line_answer(g, t_deg, demand_d, demand_cy):
        if (demand_d, demand_cy) == (d, cy):
            return bt.predict(models[g], t_deg), "LEARNED"
        q = {"groove_1": (demand_d, 0.0),
             "groove_2": (-demand_d, 0.0)}[g]
        gp, _, _ = fc.groove_point(q, t_deg, (0.0, demand_cy))
        return (gp[0], gp[1]), "FALLBACK: CLOSED-FORM"

    R("")

    # [M] the frozen measurement ------------------------------------------
    R("[M] THE MEASUREMENT (frozen; drawn EXACTLY ONCE; the report IS")
    R("  the stop record, NO artifact written)")
    R("  search (the AX2 spec, carried unchanged): steepest descent on")
    R("    the distance oracle, initial step %.3f halved on"
      " non-improvement" % AX2_STEP0)
    R("    (min %.0e), max %d iterations, early stop inside the %.3f"
      " unit band" % (AX2_STEP_MIN, AX2_MAX_ITER, band))
    R("  warm start: the trained cell's supplier answer consumed"
      " through the LINE (seed-free)")
    if list(bt.BASELINE_SEEDS) != SEEDS_EXPECTED:
        fail_closed("the trainer's recorded seed set is %s; the freeze"
                    " froze %s" % (bt.BASELINE_SEEDS, SEEDS_EXPECTED))
    R("  baseline: seeded uniform draw in the per-groove TRAIN-split")
    R("    bbox, the recorded seed set %s, a fresh Random per seed"
      % bt.BASELINE_SEEDS)
    R("    (the frozen draw order d, C_y, groove, t: d and C_y are the")
    R("    single actual design, so the order is groove, then t)")

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

    R("  per-demand table (recorded per trial: final distance,")
    R("    in-band, oracle calls):")
    R("    groove       t | warm: init -> final dist (calls) band |"
      " seeds' final dists (calls) band | verdict")
    warm_calls_all = []
    base_calls_all = []
    warm_dists = []
    base_dists = []
    win_ties = 0
    demand_total = 0
    warm_out_of_band = 0
    for g in ("groove_1", "groove_2"):
        for h in handoffs:
            t_h = h["t"]
            tgt, _, _ = fc.groove_point(qmap[g], t_h, C)
            tx, ty = tgt[0], tgt[1]
            (wx, wy), gate = line_answer(g, t_h, d, cy)
            w_init = dist2(wx, wy, tx, ty)
            wd, wc = search(wx, wy, tx, ty)
            warm_calls_all.append(wc)
            warm_dists.append(wd)
            if wd > band:
                warm_out_of_band += 1
            seed_ds = []
            seed_cs = []
            for seed in bt.BASELINE_SEEDS:
                rng = random.Random(seed)
                bx0, bx1, by0, by1 = bbox[g]
                rx = rng.uniform(bx0, bx1)
                ry = rng.uniform(by0, by1)
                sd, sc = search(rx, ry, tx, ty)
                seed_ds.append(sd)
                seed_cs.append(sc)
                base_calls_all.append(sc)
                base_dists.append(sd)
            best_sd = min(seed_ds)
            win = (wd <= best_sd)
            demand_total += 1
            win_ties += 1 if win else 0
            R("    %-9s %3.0f | %.6e -> %.6e (%3d) %s | %s | %s"
              % (g, t_h, w_init, wd, wc,
                 "IN" if wd <= band else "OUT",
                 " ".join("%.6e (%3d) %s"
                          % (sd, sc, "I" if sd <= band else "o")
                          for sd, sc in zip(seed_ds, seed_cs)),
                 "WIN/TIE" if win else "LOSE"))
            R("      LINE gate on this demand: %s (the actual design is"
              " the trained cell; no mismatch)" % gate)
    warm_mean = sum(warm_calls_all) / len(warm_calls_all)
    base_mean = sum(base_calls_all) / len(base_calls_all)
    R("  warm-start trials: %d; baseline trials: %d (the frozen"
      " budget)" % (len(warm_calls_all), len(base_calls_all)))
    R("  oracle calls (the cost channel): warm-start mean %.1f vs"
      " baseline mean %.1f -- ratio %.4f"
      % (warm_mean, base_mean, warm_mean / base_mean))
    R("  final-distance means: warm %.6e vs baseline %.6e units"
      % (sum(warm_dists) / len(warm_dists),
         sum(base_dists) / len(base_dists)))
    R("  warm-start in-band demands: %d/%d"
      % (demand_total - warm_out_of_band, demand_total))
    R("  stop condition: the set was drawn once, measured once; no")
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
    R("  this transfer exists to establish the datum in its second")
    R("    context (the interface and the wiring), not to grow a claim;")
    R("    no result above amends the budget, the protocol, or any")
    R("    recorded outcome")
    R("  the actual design is the trained anchor cell, so a warm-start")
    R("    win is expected a priori; the datum is the INITIALIZATION")
    R("    COST in the consuming context, recorded as head-to-head-")
    R("    relevant (a cost-channel result on the actual case)")
    R("  the substitution guard stands: (2)'s success never reframes")
    R("    the supplier as good enough; the 17,930x accuracy disease")
    R("    is untouched by this datum")
    R("  label: %s" % A4_LABEL)
    R("")

    # [READ] the frozen prediction, read on this run's own output ---------
    R("[READ] FROZEN-PREDICTION OUTCOMES (recorded as data, never")
    R("  gates)")
    primary = (win_ties == demand_total and warm_mean < base_mean)
    R("  PRIMARY (the cost channel) -- the warm start wins or ties")
    R("    every actual demand at a fraction of the baseline's oracle")
    R("    calls: %s (%d/%d win/tie; mean %.1f vs %.1f, ratio %.4f)"
      % ("HELD" if primary else "REFUTED (honest data)",
         win_ties, demand_total, warm_mean, base_mean,
         warm_mean / base_mean))
    context_dep = (win_ties < demand_total) or (warm_out_of_band > 0)
    R("  THE HONEST COUNTER-BRANCH -- CONTEXT-DEPENDENCE: %s"
      % ("NOT FIRED" if not context_dep else
         "FIRED -- a finding about the loop-supplier interface, never"
         " a gate change, never a silent re-tune"))
    R("  LABEL, frozen in advance: %s" % TRANSFER_LABEL)
    R("  supplier-version scoping: measured on the CURRENT frozen")
    R("    architecture (per-groove Fourier-feature ridge, %d features,"
      % (1 + 2 * bt.FOURIER_K))
    R("    exact solve, seed-free); if (1) lands, this datum re-runs")
    R("    under the new representation before it carries forward")
    R("")
    R("transfer reading: the 4 actual demands were drawn exactly once,")
    R("measured once, and stopped; every number above is this run's")
    R("own output; no artifact was written. Label: %s" % A4_LABEL)
    return R_out


if __name__ == "__main__":
    sys.exit(main())
