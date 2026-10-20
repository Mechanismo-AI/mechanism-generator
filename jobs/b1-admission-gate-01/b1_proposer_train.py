#!/usr/bin/env python3
"""Job b1-admission-gate-01: the B1 admission-gate first-run
instrument (run staging; frozen before any run).

Trains the declared proposer (per-groove Fourier-feature ridge
regression, closed-form solve, no stochastic component) on the
corpus of record (flip-station-capability-01) read-only, and
reports the frozen A1-A7 admission rows. No gate is amended and
no outcome is claimed at this staging; the script reports what
the first run does, as it runs.

Label: every output of the learned-proposal line is a SUPPLIER
OUTPUT, not a generator capability, until the line wins a
head-to-head against closed-form (the frozen A4 rule).

Usage (repo root, the recorded standard):
  python jobs/b1-admission-gate-01/b1_proposer_train.py \
      --source-commit <40-hex-sha> > run1.txt
  (twice; external diff must be empty; exit 0)

Pure stdlib; ASCII only; Python 3.10+; no network; deterministic.
"""

import hashlib
import json
import math
import os
import platform
import random
import re
import sys

JOB_ID = "b1-admission-gate-01"

# [P0] pins (frozen at this staging; fail-closed on mismatch)
INSTRUMENT_REL = os.path.join(
    "jobs", "flip-station-capability-01", "flip_capability.py")
INSTRUMENT_SHA256 = (
    "72989f8a1183647f5cbf47c6db92b0cdc63eead355acb25f1dd42adedc06447b")
INSTRUMENT_BYTES = 50265
CORPUS_REL = os.path.join(
    "runs", "flip-station-capability-01", "flip_station_capability_v1.jsonl")
CORPUS_SHA256 = (
    "cdac1413f61e9262d498142f72081fc3698924ab9df461c06a21b0854039be6c")
CORPUS_PROVENANCE_COMMIT = (
    "9c9fd6f9f1724e683ed053f621f95fe5a283425a")
CORPUS_JOB = "flip-station-capability-01"
CORPUS_ROWS_EXPECTED = 838
SCHEMA_OK = re.compile(r"^1\.[0-9]+$")

# frozen first-run architecture (declared, not tuned)
FOURIER_K = 24            # 1 + 2*K = 49 features
RIDGE_LAMBDA = 1e-8       # ridge on every diagonal, bias included
WITNESS_TOL = 1e-9        # reproduction witness tolerance, units

# frozen split rule (the gate JOB's frozen rule; counts computed)
SPLIT_MOD = 5
SPLIT_REMAINDER = 4       # 0-based JSONL index i held out iff i % 5 == 4

# frozen baseline seed set (A6; the learned model itself is seed-free)
BASELINE_SEEDS = [580000050, 580000051, 580000052]

# frozen OOD probe (A5; design shift, in-distribution angle)
OOD_GROOVE = "groove_1"
OOD_T_DEG = 90.0
OOD_D = 0.4
OOD_CY = 0.25

# presentations (of the frozen distance function; never gates)
TOL_POS_UNITS = 0.015     # 1.5 mm handoff tolerance, task-layer units
UNITS_PER_MM = 100.0      # 1 unit = 100 mm, task-layer

ARTIFACT_REL = os.path.join("runs", JOB_ID, "b1_proposer_v1.json")

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


def phi(t_deg):
    """Frozen feature map: [1, cos(k*x), sin(k*x)] for k = 1..K."""
    x = math.radians(t_deg)
    row = [1.0]
    for k in range(1, FOURIER_K + 1):
        row.append(math.cos(k * x))
    for k in range(1, FOURIER_K + 1):
        row.append(math.sin(k * x))
    return row


def solve_linear(m, v):
    """Deterministic Gaussian elimination with partial pivoting."""
    n = len(v)
    a = [list(m[i]) + [v[i]] for i in range(n)]
    for col in range(n):
        piv = col
        best = abs(a[col][col])
        for r in range(col + 1, n):
            mag = abs(a[r][col])
            if mag > best:
                best = mag
                piv = r
        if best <= 0.0:
            fail_closed("singular normal-equation system (col %d)" % col)
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
        prow = a[col]
        pval = prow[col]
        for r in range(col + 1, n):
            f = a[r][col] / pval
            if f != 0.0:
                rowr = a[r]
                for c in range(col, n + 1):
                    rowr[c] -= f * prow[c]
    w = [0.0] * n
    for i in range(n - 1, -1, -1):
        acc = a[i][n]
        for j in range(i + 1, n):
            acc -= a[i][j] * w[j]
        w[i] = acc / a[i][i]
    return w


def train_ridge(rows):
    """Closed-form ridge on the frozen feature map; no randomness."""
    nfeat = 1 + 2 * FOURIER_K
    xs = [phi(r["plate_angle_deg"]) for r in rows]
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
        m[i][i] += RIDGE_LAMBDA
    return {"w_gx": solve_linear(m, bgx), "w_gy": solve_linear(m, bgy)}


def predict(model, t_deg):
    p = phi(t_deg)
    gx = 0.0
    gy = 0.0
    for i, p_ in enumerate(p):
        gx += p_ * model["w_gx"][i]
        gy += p_ * model["w_gy"][i]
    return gx, gy


def dist2(lx, ly, cx, cy):
    return math.sqrt((lx - cx) * (lx - cx) + (ly - cy) * (ly - cy))


def load_corpus():
    if not os.path.isfile(CORPUS_REL):
        fail_closed(
            "corpus of record missing: %s -- regenerate it read-only "
            "from the merged instrument: python %s --source-commit %s "
            "(expected jsonl sha256 %s)"
            % (CORPUS_REL, INSTRUMENT_REL, CORPUS_PROVENANCE_COMMIT,
               CORPUS_SHA256))
    got = sha256_file(CORPUS_REL)
    if got != CORPUS_SHA256:
        fail_closed("corpus sha256 mismatch: got %s pinned %s"
                    % (got, CORPUS_SHA256))
    rows = []
    with open(CORPUS_REL, "r", encoding="ascii") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError as exc:
                fail_closed("corpus line %d is not JSON: %s" % (i, exc))
            r["_i"] = i
            rows.append(r)
    if len(rows) != CORPUS_ROWS_EXPECTED:
        fail_closed("corpus row count %d != expected %d"
                    % (len(rows), CORPUS_ROWS_EXPECTED))
    for r in rows:
        v = r.get("corpus_schema_version")
        if not isinstance(v, str) or not SCHEMA_OK.match(v):
            fail_closed("schema succession violation on row %d: %r "
                        "(accepts additive 1.x only; a meaning change "
                        "fails closed and the gate re-stages)" % (r["_i"], v))
        if r.get("major") != "1":
            fail_closed("major mismatch on row %d: %r"
                       % (r["_i"], r.get("major")))
        if r.get("job") != CORPUS_JOB:
            fail_closed("job mismatch on row %d: %r"
                       % (r["_i"], r.get("job")))
        prov = r.get("provenance") or {}
        if prov.get("source_commit") != CORPUS_PROVENANCE_COMMIT:
            fail_closed("provenance commit mismatch on row %d: %r"
                       % (r["_i"], prov.get("source_commit")))
    return rows


def discover_chosen_design(rows):
    """The chosen design is discovered from the corpus, never assumed."""
    chosen = [r for r in rows
              if r.get("kind") == "gate" and r.get("name") == "sweep_design"
              and r.get("chosen") is True]
    if len(chosen) != 1:
        fail_closed("expected exactly one chosen sweep_design gate row, "
                    "found %d" % len(chosen))
    d = chosen[0]["pin_offset_d"]
    cy = chosen[0]["plate_center_cy"]
    dp = [r for r in rows
          if r.get("kind") == "design_parameter"
          and r.get("name") == "pin_offset_d"]
    pc = [r for r in rows
          if r.get("kind") == "design_parameter"
          and r.get("name") == "plate_center"]
    if len(dp) != 1 or len(pc) != 1:
        fail_closed("design_parameter cross-check rows missing")
    if dp[0]["value"] != d:
        fail_closed("chosen design d=%r contradicts design_parameter "
                    "pin_offset_d=%r" % (d, dp[0]["value"]))
    try:
        pcv = json.loads(pc[0]["value"])
    except ValueError as exc:
        fail_closed("plate_center not a JSON list: %s" % exc)
    if pcv != [0.0, cy]:
        fail_closed("chosen design C_y=%r contradicts design_parameter "
                    "plate_center=%r" % (cy, pcv))
    return float(d), float(cy)


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
        print("usage: b1_proposer_train.py --source-commit <40-hex-sha>",
              file=sys.stderr)
        return 1
    if not re.match(r"^[0-9a-f]{40}$", source_commit):
        print("FAIL-CLOSED: --source-commit must be a 40-char lowercase "
              "hex sha", file=sys.stderr)
        return 1
    try:
        out1 = run(source_commit)
        out2 = run(source_commit)
    except FailClosed as exc:
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
    """One complete training + report pass; returns the report lines."""
    R_out = []
    R = R_out.append

    R("b1-admission-gate-01 -- the B1 admission-gate first-run instrument")
    R("(run staging; frozen before any run)")
    R("label: %s" % A4_LABEL)
    R("python: %s" % platform.python_version())
    R("source commit: %s" % source_commit)
    R("")

    # [P0] pins ---------------------------------------------------------
    R("[P0] PIN CHECKS (fail-closed)")
    if not os.path.isfile(INSTRUMENT_REL):
        fail_closed("instrument missing: %s" % INSTRUMENT_REL)
    ibytes = os.path.getsize(INSTRUMENT_REL)
    isha = sha256_file(INSTRUMENT_REL)
    if ibytes != INSTRUMENT_BYTES or isha != INSTRUMENT_SHA256:
        fail_closed("instrument pin mismatch: %s %d bytes "
                    "(pinned %s %d bytes)"
                    % (isha, ibytes, INSTRUMENT_SHA256, INSTRUMENT_BYTES))
    rows = load_corpus()
    R("  instrument %s" % INSTRUMENT_REL)
    R("    sha256 %s (%d bytes) -- PIN MATCH" % (isha, ibytes))
    R("  corpus %s" % CORPUS_REL)
    R("    sha256 %s -- PIN MATCH" % CORPUS_SHA256)
    R("    provenance commit %s -- PIN MATCH" % CORPUS_PROVENANCE_COMMIT)
    R("    schema succession: additive 1.x accepted, major 1 confirmed")
    R("")

    # [P1] corpus + split ------------------------------------------------
    R("[P1] CORPUS AND THE FROZEN SPLIT (counts computed, never"
      " transcribed)")
    R("  rows: %d" % len(rows))
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    for k in sorted(kinds):
        R("    kind %-20s %d" % (k, kinds[k]))
    samples = [r for r in rows if r["kind"] == "groove_sample"]
    held = [r for r in rows if r["_i"] % SPLIT_MOD == SPLIT_REMAINDER]
    held_sol = [r for r in held if r["kind"] == "groove_sample"]
    held_nonsol = [r for r in held if r["kind"] != "groove_sample"]
    train = [r for r in samples if r["_i"] % SPLIT_MOD != SPLIT_REMAINDER]
    for g in ("groove_1", "groove_2"):
        R("  %s: %d sample rows; %d train, %d held out"
          % (g, sum(1 for r in samples if r["groove"] == g),
             sum(1 for r in train if r["groove"] == g),
             sum(1 for r in held_sol if r["groove"] == g)))
    R("  held-out rows total: %d (solution rows: %d; not-scoreable "
      "kinds: %d, counted and recorded, never dropped)"
      % (len(held), len(held_sol), len(held_nonsol)))
    nonsol_kinds = {}
    for r in held_nonsol:
        nonsol_kinds[r["kind"]] = nonsol_kinds.get(r["kind"], 0) + 1
    for k in sorted(nonsol_kinds):
        R("    not-scoreable kind %-20s %d"
          % (k, nonsol_kinds[k]))
    R("")

    # [W] reproduction witness -------------------------------------------
    R("[W] REPRODUCTION WITNESS (every groove_sample row re-derived"
      " through the instrument)")
    d, cy = discover_chosen_design(rows)
    R("  chosen design discovered from the corpus (gate row chosen=true,"
      " cross-checked against design_parameter rows):")
    R("    d=%.1f C_y=%.2f (q1=(d,0), q2=(-d,0), C=(0,C_y))" % (d, cy))
    sys.path.insert(0, os.path.dirname(os.path.abspath(INSTRUMENT_REL)))
    import flip_capability as fc  # noqa: E402  (read-only import)
    qmap = {"groove_1": (d, 0.0), "groove_2": (-d, 0.0)}
    worst_w = 0.0
    for r in samples:
        g, _, _ = fc.groove_point(qmap[r["groove"]],
                                  r["plate_angle_deg"], (0.0, cy))
        dev = dist2(g[0], g[1], r["gx"], r["gy"])
        if dev > worst_w:
            worst_w = dev
        if dev > WITNESS_TOL:
            fail_closed("witness violation on row %d (%s t=%.1f):"
                        " re-derived (%.12f, %.12f) vs recorded"
                        " (%.12f, %.12f), deviation %.3e > tol %.0e"
                        % (r["_i"], r["groove"], r["plate_angle_deg"],
                           g[0], g[1], r["gx"], r["gy"], dev, WITNESS_TOL))
    R("  %d/%d groove_sample rows re-derived exactly; worst deviation "
      "%.3e units (tol %.0e) PASS"
      % (len(samples), len(samples), worst_w, WITNESS_TOL))
    R("")

    # [T] training (exact; then the artifact hash BEFORE any score) ------
    R("[T] TRAINING (the frozen architecture; declared, not tuned)")
    R("  per-groove Fourier-feature ridge regression")
    R("    features: [1, cos(k*x), sin(k*x)] k=1..%d -> %d features,"
      " x = radians(plate_angle_deg)" % (FOURIER_K, 1 + 2 * FOURIER_K))
    R("    ridge lambda %.1e on every diagonal (bias included);"
      " closed-form" % RIDGE_LAMBDA)
    R("    Gaussian-elimination solve with partial pivoting --"
      " deterministic")
    R("    no initialization, no stochastic component, no seeds:"
      " exact solve (seed-free by construction)")
    R("    DESIGN-INVARIANT: the training solution rows span the single"
      " chosen design (d=%.1f/C_y=%.2f);" % (d, cy))
    R("      design features are deliberately excluded (ill-conditioning"
      " avoided); growth to")
    R("      multi-design corpora is a future corpus decision, never an"
      " amendment here")
    models = {}
    for g in ("groove_1", "groove_2"):
        models[g] = train_ridge([r for r in train if r["groove"] == g])
        R("  trained %s on %d rows" % (g, sum(1 for r in train
                                             if r["groove"] == g)))
    R("  artifact (the trained model) written before any score is"
      " computed")
    artifact = {
        "job": JOB_ID,
        "label": A4_LABEL,
        "model": "per-groove Fourier-feature ridge regression "
                 "(K=%d, %d features, lambda=%s, closed-form solve)"
                 % (FOURIER_K, 1 + 2 * FOURIER_K, repr(RIDGE_LAMBDA)),
        "feature_map": "[1, cos(k*x), sin(k*x)] k=1..%d,"
                       " x=radians(plate_angle_deg)" % FOURIER_K,
        "design_invariant": True,
        "chosen_design": {"d": d, "cy": cy},
        "split_rule": "0-based JSONL index i held out iff i %% %d == %d"
                      % (SPLIT_MOD, SPLIT_REMAINDER),
        "source_commit": source_commit,
        "corpus": {"path": CORPUS_REL, "sha256": CORPUS_SHA256,
                   "rows": len(rows),
                   "provenance_commit": CORPUS_PROVENANCE_COMMIT},
        "instrument": {"path": INSTRUMENT_REL, "sha256": INSTRUMENT_SHA256},
        "baseline_seeds": BASELINE_SEEDS,
    }
    for g in ("groove_1", "groove_2"):
        artifact[g] = models[g]
    os.makedirs(os.path.dirname(ARTIFACT_REL), exist_ok=True)
    with open(ARTIFACT_REL, "w", encoding="ascii") as fh:
        json.dump(artifact, fh, sort_keys=True, indent=1)
        fh.write("\n")
    art_sha = sha256_file(ARTIFACT_REL)
    R("  %s" % ARTIFACT_REL)
    R("    sha256 %s (recorded before any score is read -- the A7"
      " order)" % art_sha)
    R("")

    # [PRED] the frozen predictions (read at the run; never gates) ---------
    R("[PRED] FROZEN PREDICTIONS (frozen at staging; recorded here so"
      " the run carries them)")
    R("  P1 the learned model does not beat closed-form on the headline")
    R("     metric (on distance-to-closed-form the closed-form scores 0")
    R("     by definition; at best the learned model ties) -- lean: HELD")
    R("  P2 median held-out distance < %.3f units (the 1.5 mm handoff"
      " tolerance)" % TOL_POS_UNITS)
    R("     -- lean: HELD")
    R("  P3 the OOD probe distance exceeds the worst held-out distance")
    R("     by at least an order of magnitude -- lean: HELD")
    R("  P4 every baseline seed's median distance exceeds the learned"
      " median")
    R("     -- lean: HELD")
    R("")

    # [A2] held-out head-to-head table ------------------------------------
    R("[A2] CLOSED-FORM HEAD-TO-HEAD ON HELD-OUT ROWS (both numbers"
      " per row)")
    R("  label: %s" % A4_LABEL)
    R("  distance function (frozen): Euclidean in task-layer units")
    R("  per-row table: idx | groove | t_deg | learned (x, y) |"
      " closed-form (x, y) | units | mm | ratio-to-tol")
    dists = []
    for r in held_sol:
        lx, ly = predict(models[r["groove"]], r["plate_angle_deg"])
        dd = dist2(lx, ly, r["gx"], r["gy"])
        dists.append(dd)
        R("  %4d %s %6.1f  (%12.8f, %12.8f)  (%12.8f, %12.8f)"
          "  %.6e  %8.4f  %8.4f"
          % (r["_i"], r["groove"], r["plate_angle_deg"], lx, ly,
             r["gx"], r["gy"], dd, dd * UNITS_PER_MM,
             dd / TOL_POS_UNITS))
    med = median(dists)
    wor = max(dists)
    R("  median held-out distance: %.6e units (%.4f mm;"
      " %.4f x tolerance)" % (med, med * UNITS_PER_MM,
                             med / TOL_POS_UNITS))
    R("  worst  held-out distance: %.6e units (%.4f mm;"
      " %.4f x tolerance)" % (wor, wor * UNITS_PER_MM,
                             wor / TOL_POS_UNITS))
    R("  (mm and ratio are presentations of the same frozen function,"
      " never gates)")
    R("")

    # [A6] initializer head-to-head ----------------------------------------
    R("[A6] INITIALIZER HEAD-TO-HEAD (seeded random-restart supplier"
      " on the same held-out rows)")
    R("  label: %s" % A4_LABEL)
    R("  baseline: uniform in the per-groove TRAIN-split bounding box,"
      " one restart per held-out row, draws in corpus order")
    bbox = {}
    for g in ("groove_1", "groove_2"):
        gxs = [r["gx"] for r in train if r["groove"] == g]
        gys = [r["gy"] for r in train if r["groove"] == g]
        bbox[g] = (min(gxs), max(gxs), min(gys), max(gys))
        R("  %s train bbox: x [%.4f, %.4f] y [%.4f, %.4f]"
          % (g, bbox[g][0], bbox[g][1], bbox[g][2], bbox[g][3]))
    seed_medians = []
    for seed in BASELINE_SEEDS:
        rng = random.Random(seed)
        bd = []
        for r in held_sol:
            bx0, bx1, by0, by1 = bbox[r["groove"]]
            bx = rng.uniform(bx0, bx1)
            by = rng.uniform(by0, by1)
            bd.append(dist2(bx, by, r["gx"], r["gy"]))
        bmed = median(bd)
        bwor = max(bd)
        seed_medians.append(bmed)
        R("  seed %d: median %.6e units (%.4f mm); worst %.6e units"
          " (%.4f mm)" % (seed, bmed, bmed * UNITS_PER_MM, bwor,
                          bwor * UNITS_PER_MM))
    R("  learned median %.6e units vs baseline medians: %s"
      % (med, ", ".join("%.6e" % s for s in seed_medians)))
    for seed, bm in zip(BASELINE_SEEDS, seed_medians):
        R("  learned median < seed %d median: %s"
          % (seed, "YES" if med < bm else "NO"))
    R("")

    # [A5] OOD probe --------------------------------------------------------
    R("[A5] OOD PROBE (design shift; frozen with its provenance)")
    R("  label: %s" % A4_LABEL)
    R("  probe: %s at plate angle %.1f deg under design d=%.1f"
      " C_y=%.2f" % (OOD_GROOVE, OOD_T_DEG, OOD_D, OOD_CY))
    R("  provenance, stated against the corpus: every groove_sample"
      " training row")
    R("    carries the single chosen design d=%.1f C_y=%.2f; the probe's"
      " design differs," % (d, cy))
    R("    and the learned model is design-invariant (no design"
      " features), so the probe")
    R("    sits outside the training corpus's solution distribution in"
      " DESIGN. The angle")
    R("    %.1f deg is in-distribution, isolating the design shift. The"
      " probe design lies" % OOD_T_DEG)
    R("    inside the recorded SWEEP_D x SWEEP_CY envelope but exists"
      " there only as a")
    R("    gate aggregate row (never sampled; that row is itself held"
      " out at index 14).")
    R("  fallback: NONE is wired in the first run (frozen); behavior is"
      " recorded as-run.")
    R("  recorded precedents this probe answers: the learned"
      " initializer OOD failure (PR #44)")
    R("    and the chooser restarts.")
    g_ood, _, _ = fc.groove_point((OOD_D, 0.0), OOD_T_DEG, (0.0, OOD_CY))
    g_ind, _, _ = fc.groove_point(qmap[OOD_GROOVE], OOD_T_DEG, (0.0, cy))
    lx, ly = predict(models[OOD_GROOVE], OOD_T_DEG)
    ood_d = dist2(lx, ly, g_ood[0], g_ood[1])
    shift = dist2(g_ind[0], g_ind[1], g_ood[0], g_ood[1])
    R("  closed-form answer under the probe design: (%.8f, %.8f)"
      % (g_ood[0], g_ood[1]))
    R("  closed-form answer under the chosen design (in-distribution):"
      " (%.8f, %.8f)" % (g_ind[0], g_ind[1]))
    R("    the design shift moves the closed-form answer by %.6f units"
      " (%.2f mm)" % (shift, shift * UNITS_PER_MM))
    R("  learned answer (design-invariant model): (%.8f, %.8f)" % (lx, ly))
    R("  probe distance: %.6e units (%.4f mm; %.4f x tolerance)"
      % (ood_d, ood_d * UNITS_PER_MM, ood_d / TOL_POS_UNITS))
    R("  ratio to worst held-out distance: %.4f (%.6e / %.6e)"
      % (ood_d / wor, ood_d, wor))
    R("  frozen expectation (a prediction, never a gate): gross"
      " degradation, mirroring")
    R("    the PR #44 initializer OOD failure class.")
    R("")

    # [A1] instrument modification ------------------------------------------
    R("[A1] ZERO INSTRUMENT MODIFICATION (the reciprocity/admission"
      " test)")
    R("  the instrument was consumed read-only; its sha256 pin matched"
      " the merged file")
    R("  bit-for-bit -- instrument modification count: 0")
    R("")

    # [A4] supplier-output labeling ------------------------------------------
    R("[A4] SUPPLIER-OUTPUT LABELING")
    R("  headline metric: distance from closed-form on held-out"
      " demands. On this")
    R("  metric the closed-form scores 0 by definition, so the learned"
      " line can at")
    R("  best tie -- the win condition (strictly beating closed-form"
      " over the held-out")
    R("  set) is impossible on this metric and the SUPPLIER OUTPUT"
      " label stands.")
    R("  the label-change event remains defined exactly as frozen"
      " (with its numbers);")
    R("  no prose drift. Current label: %s" % A4_LABEL)
    R("")

    # [A3] determinism --------------------------------------------------------
    R("[A3] DETERMINISM CONTROL")
    R("  declared initialization: none -- exact closed-form solve,"
      " no stochastic")
    R("  component in the learned model; the baseline supplier's seeds"
      " are frozen at")
    R("  %s (Mersenne Twister via random.Random, independent"
      " instances)" % BASELINE_SEEDS)
    R("  in-process check: this script ran the full pass twice and"
      " compared the")
    R("  reports (verdict printed at the end of the output)")
    R("  external standard (the recorded one): two redirected runs,"
      " diff empty, exit 0")
    R("")

    # [A7] lineage -------------------------------------------------------------
    R("[A7] LINEAGE RECORDING")
    R("  training corpus: %s (the corpus of record), %d rows, schema"
      " 1.1" % (CORPUS_REL, len(rows)))
    R("    jsonl sha256 %s (pinned, verified at run)"
      % CORPUS_SHA256)
    R("    provenance: job %s, source commit %s"
      % (CORPUS_JOB, CORPUS_PROVENANCE_COMMIT))
    R("    family: dual-groove plate-cam flip carrier (the frozen"
      " first-run parameter space)")
    R("  instrument: %s sha256 %s (unmodified)" % (INSTRUMENT_REL,
                                                    INSTRUMENT_SHA256))
    R("  trained artifact: %s sha256 %s" % (ARTIFACT_REL, art_sha))
    R("    (written and hashed before any score was computed -- the"
      " frozen A7 order)")
    R("  run source commit: %s" % source_commit)
    R("")

    # [READ] frozen-prediction outcomes (data, never gates) --------------------
    R("[READ] FROZEN-PREDICTION OUTCOMES (recorded as data, never"
      " gates)")
    R("  P1 learned does not beat closed-form: %s (median distance"
      " %.6e units > 0," % ("HELD" if med > 0.0 else "REFUTED", med))
    R("     at best a tie on this metric)")
    R("  P2 median held-out distance < %.3f units: %s (%.6e units)"
      % (TOL_POS_UNITS,
         "HELD" if med < TOL_POS_UNITS else "REFUTED", med))
    R("  P3 OOD distance >= 10x worst held-out: %s (ratio %.4f)"
      % ("HELD" if ood_d >= 10.0 * wor else "REFUTED", ood_d / wor))
    p4 = all(med < bm for bm in seed_medians)
    R("  P4 every baseline seed median exceeds learned median: %s"
      % ("HELD" if p4 else "REFUTED"))
    R("")
    R("admission reading: every A-row above is reported; A1 holds"
      " (mod count 0).")
    R("The run is gradeable against the frozen scorecard; a first"
      " admissible run")
    R("does not need to win. Label: %s" % A4_LABEL)
    return R_out


if __name__ == "__main__":
    sys.exit(main())
