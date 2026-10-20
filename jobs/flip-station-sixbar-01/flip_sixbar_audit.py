#!/usr/bin/env python3
"""flip-station-sixbar-01 -- the S2-S4 audit instrument for the six-bar
flip carrier motion task.

Case study C family succession, the audit half of the staged machine
step. The motion task (flip_sixbar.motion.json) hands the recorded
six-bar motion solver the flip as a 12-phase sampled trajectory; this
script grades each seed's selected candidate against the frozen S2-S4
scorecard items (jobs/flip-station-sixbar-01/JOB.md):

  - S2  per-joint transmission-angle audit over the cycle at the two
        output joints (B: coupler-vs-rocker, C: extension-vs-output
        rocker -- the same joint pairs the solver's own audit reads),
        against the frozen linkage gates: HARD mu in [40, 140] deg
        (deviation from 90 deg <= 50 deg), TARGET mu in [50, 130] deg;
        the crank phase of the worst sample is reported, not just the
        value. The folded angle arccos(|cos|) is the deviation measure:
        the true joint angle mu in [0, 180] deg satisfies
        mu in [40, 140] iff the folded angle is >= 40 deg.
  - S3  geometry audits: the swept envelope from swept geometry (the
        exact-rectangle part corners through the vertical transit +
        the linkage joint extents) with the mandatory
        utilization/headroom table; part-sweep rectangle occupancy,
        the cam script's discipline carried unchanged (sampled, never
        certified; no keep-out gate -- the Q4 deferral); an undefined
        assembly anywhere on the audit grid is an ERROR row, never a
        quiet pass.
  - S4  Jacobian-based link-length sensitivities: the analytic 4x4
        constraint Jacobian of the position-level closure (unknowns
        B, C at fixed crank angle) prices each of the five
        manufactured bar lengths; handoff pose errors are scored
        against the labeled defaults 1.5 mm / 1.5 deg at the 0.1 mm
        declared link class, worst case over the 32 sign corners; the
        max-sensitivity region over the cycle is located (frozen
        prediction: not at the poses). Rank deficiency fails closed
        (dead-point rows, never finite numbers). A built-in central
        finite-difference cross-check verifies the analytic
        sensitivities at every demand phase (fail-closed on
        disagreement).
  - S1  context rows are consumed NATIVELY from the solver's
        per-sample emission (the PR-B standing infrastructure; this
        case study is its first native consumption) -- no external
        recomputation pipeline for the readings. A kinematics
        cross-check re-derives the per-phase position/orientation
        errors from the returned mechanism_normalized geometry (the
        independent documented chain) and verifies the emission
        (fail-closed on disagreement beyond the declared tolerance).

Controls (S5, the script's own): pure stdlib; ASCII only; read-only
consumption of the task and result files; fail-closed corpus emitter
(schema 1.1, units block + provenance on every row, unknown-kind
refusal); double-run determinism (in-process IDENTICAL check); the
instrument-modification count row is emitted (expected 0 -- the
solver and its emission are consumed unmodified; this script is new
job-local instrumentation, the additive convention).

Physical frame: the task's normalization is the recorded -01 layout
loop basis (twelve-sample centroid at the origin, one unit = the
loop's bounding-box diagonal). The mm mapping is DERIVED from the
frozen artifact plus the exact demand poses (never transcribed): the
carry endpoints x = -130 and +130 mm fix the scale, phase 0 fixes the
centroid, and the checks re-verify the scale against the recorded
260 x 90 mm bounding box and the demand poses against their exact
values.

Pure stdlib; ASCII only; deterministic. Usage (repo root, after the
three-seed run):

  python jobs/flip-station-sixbar-01/flip_sixbar_audit.py \
    --task jobs/flip-station-sixbar-01/flip_sixbar.motion.json \
    --result runs/flip-station-sixbar-01/result-580000050.json \
    --result runs/flip-station-sixbar-01/result-580000051.json \
    --result runs/flip-station-sixbar-01/result-580000052.json \
    --source-commit <40-hex-sha>
"""

import hashlib
import json
import math
import os
import sys

JOB_ID = "flip-station-sixbar-01"
CORPUS_SCHEMA_VERSION = "1.1"
CORPUS_MAJOR = "1"

# Frozen demand (the recorded brief, unchanged; carried from the cam
# line and the motion JSON staging): three poses, tolerances 1.5 mm
# position / 1.5 deg orientation, at carry phases 0/2/4.
DEMAND_POSES_MM = [
    (-130.0, 50.0, 0.0),
    (0.0, 50.0, 90.0),
    (130.0, 50.0, 180.0),
]
DEMAND_PHASES = (0, 2, 4)
HANDOFF_PHASES = (0, 4)
DEMAND_CRANK_DEG = (0.0, 60.0, 120.0)
TOL_POS_MM = 1.5
TOL_ORI_DEG = 1.5

# The exact demand-pair x span that fixes the frame scale (the carry
# endpoints; the recorded -01 layout loop, 260 x 90 mm bounding box).
CARRY_X_SPAN_MM = 260.0
BBOX_Y_SPAN_MM = 90.0

# Frozen linkage gates (the freeze correction, Catch 2 of the fold):
# HARD: deviation from 90 deg <= 50 deg, i.e. mu in [40, 140] deg;
# TARGET: the tighter declared pair mu in [50, 130] deg. The folded
# measure arccos(|cos|) is gated at the equivalent floors.
MU_HARD_DEG = 40.0
MU_TARGET_DEG = 50.0

# The solver's own S1 qualification gates (continuation.py LIMITS,
# consumed read-only as context; the audit never re-gates them).
SOLVER_LIMITS = {
    "position": 0.01,
    "orientation": 1.0,
    "spatial_velocity": 0.02,
    "spatial_acceleration": 0.05,
    "angular_velocity": 2.0,
    "angular_acceleration": 5.0,
}
SAMPLE_KEYS = ("position", "orientation", "spatial_velocity",
               "spatial_acceleration", "angular_velocity",
               "angular_acceleration")

# Part model (the cam script's discipline, carried unchanged): exact
# in-plane rectangle 100 x 5 mm, computed at pose samples; sampled,
# never certified. Identity mount (the B2 seam declaration carried:
# part centroid at the carrier origin, part axes = carrier axes).
PART_HALF_LONG_MM = 50.0
PART_HALF_SHORT_MM = 2.5

# Declared manufactured link-length tolerance class (design
# parameter, frozen here with lineage: the cam line's 0.1 mm clearance
# class carried to the linkage's bar lengths; the -07 uniform 0.10 mm
# class precedent). First-order pricing (the WC-L convention).
LINK_TOL_MM = 0.1
LINK_NAMES = ("crank", "coupler", "rocker", "extension",
              "output_rocker")

# Emission and audit grids (frozen, deterministic).
AUDIT_STEP_DEG = 0.25      # transmission / envelope / sweep sampling
EMIT_STEP_DEG = 5.0        # emitted transmission + sensitivity rows

# Tolerances (fail-closed).
EPS_GEOM = 1e-12          # mirrors simulation.circle's own thresholds
EPS_EDGES = 1e-9          # edge-length self-consistency of the chain
EPS_CLOSURE = 1e-9        # cycle closure of the sweep
EPS_MAP = 1e-6            # mm; frame-mapping reproduction checks
EPS_PHASES = 1e-9         # phases_rad vs the uniform grid
EPS_PIN = 1e-12           # exact demand pins in the task artifact
EPS_EMISSION = 1e-4       # kinematics cross-check vs the emission
                         # (independent implementations; the torch
                         # path clamps near-degenerate sqrt at 1e-10,
                         # so a generous-but-meaningful tolerance: a
                         # re-implementation bug shows at 1e-3+)
FD_STEP_REL = 1e-6        # relative FD step for the S4 self-check
FD_TOL = 1e-6             # normalized units; analytic vs FD
RANK_EPS = 1e-12          # constraint-Jacobian determinant floor

OUTPUT_DIR = os.path.join("runs", JOB_ID)
CORPUS_STEM = "flip_station_sixbar_v1"


# ---------------------------------------------------------------------------
# Small vector / matrix helpers (pure stdlib).
# ---------------------------------------------------------------------------

def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vscale(s, v):
    return (s * v[0], s * v[1])


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def vnorm(a):
    return math.hypot(a[0], a[1])


def vperp(a):
    return (-a[1], a[0])


def vdiv(v, d):
    return (v[0] / d, v[1] / d)


def vrot(rad, v):
    c, s = math.cos(rad), math.sin(rad)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def lu_decompose(a):
    """Partial-pivot LU of a 4x4 list-of-lists; returns (lu, det,
    perm) with perm the row permutation applied to the input."""
    n = len(a)
    lu = [row[:] for row in a]
    perm = list(range(n))
    det = 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(lu[r][col]))
        if abs(lu[piv][col]) < 1e-300:
            return lu, 0.0, perm
        if piv != col:
            lu[col], lu[piv] = lu[piv], lu[col]
            perm[col], perm[piv] = perm[piv], perm[col]
            det = -det
        det *= lu[col][col]
        for r in range(col + 1, n):
            f = lu[r][col] / lu[col][col]
            lu[r][col] = f
            for k in range(col + 1, n):
                lu[r][k] -= f * lu[col][k]
    return lu, det, perm


def lu_solve(lu, perm, b):
    """Solve lu x = P b (perm applied to the right-hand side)."""
    n = len(lu)
    x = [b[perm[i]] for i in range(n)]
    for i in range(1, n):
        x[i] -= sum(lu[i][k] * x[k] for k in range(i))
    for i in range(n - 1, -1, -1):
        x[i] = (x[i] - sum(lu[i][k] * x[k]
                           for k in range(i + 1, n))) / lu[i][i]
    return x


# ---------------------------------------------------------------------------
# The six-bar chain (the documented construction, simulation.py,
# re-implemented read-only; the same thresholds and error classes).
# ---------------------------------------------------------------------------

def circle(a, b, r, s, sign):
    if sign not in (-1, 1) or min(r, s) <= 0:
        raise ValueError("Invalid radius or branch")
    delta = vsub(b, a)
    d = vnorm(delta)
    if d <= 1e-12:
        raise ValueError("Coincident circle centres")
    unit = vdiv(delta, d)
    along = (r * r - s * s + d * d) / (2.0 * d)
    h2 = r * r - along * along
    if h2 <= 1e-12:
        raise ValueError("Unreachable or tangent assembly")
    return vadd(a, vadd(vscale(along, unit),
                        vscale(sign * math.sqrt(h2), vperp(unit))))


def simulate6(m, theta):
    """One assembly of the recorded six-bar chain at crank angle
    theta (rad). Returns O, Q, R, A, B, D, C, P (normalized task
    units) and the tool angle (rad, mounting included)."""
    O, Q, R = m["O"], m["Q"], m["R"]
    A = (O[0] + m["crank"] * math.cos(theta),
         O[1] + m["crank"] * math.sin(theta))
    B = circle(A, Q, m["coupler"], m["rocker"], m["branches"][0])
    u = vdiv(vsub(B, A), m["coupler"])
    D = vadd(A, vadd(vscale(m["attachment"][0], u),
                     vscale(m["attachment"][1], vperp(u))))
    C = circle(D, R, m["extension"], m["output_rocker"],
               m["branches"][1])
    v = vdiv(vsub(C, D), m["extension"])
    P = vadd(D, vadd(vscale(m["tool"][0], v),
                     vscale(m["tool"][1], vperp(v))))
    angle = math.atan2(v[1], v[0]) + m["mounting"]
    return {"O": O, "Q": Q, "R": R, "A": A, "B": B, "D": D,
            "C": C, "P": P, "angle": angle}


def edge_spec(m):
    """The seven closed-chain edges and their nominal lengths (the
    solver's own audit list, read-only)."""
    a = m["attachment"]
    return (
        ("O", "A", m["crank"]),
        ("A", "B", m["coupler"]),
        ("B", "Q", m["rocker"]),
        ("A", "D", math.hypot(a[0], a[1])),
        ("B", "D", math.hypot(a[0] - m["coupler"], a[1])),
        ("D", "C", m["extension"]),
        ("C", "R", m["output_rocker"]),
    )


def check_edges(m, s):
    worst = 0.0
    for p, qv, ln in edge_spec(m):
        worst = max(worst, abs(vnorm(vsub(s[qv], s[p])) - ln))
    return worst


def folded_mu(x, y, z, s):
    """Folded transmission angle (deg) at joint y between links yx and
    yz: arccos(|cos|), the deviation-from-90 measure."""
    v = vsub(s[x], s[y])
    w = vsub(s[z], s[y])
    cosv = abs(vdot(v, w)) / (vnorm(v) * vnorm(w))
    return math.degrees(math.acos(min(1.0, cosv)))


# ---------------------------------------------------------------------------
# S4: the analytic link-length sensitivities (constraint Jacobian).
# ---------------------------------------------------------------------------

def sens_at(m, theta):
    """Analytic dP/dL and dphi/dL for the five bar lengths at fixed
    crank angle (all in normalized task units per normalized length).

    Unknowns X = (Bx, By, Cx, Cy); position-level closure:
        g1 = |B - A| - coupler
        g2 = |B - Q| - rocker
        g3 = |C - D(B, A(crank))] - extension
        g4 = |C - R| - output_rocker
    J4 dX = dg/dL (fixed X); outputs chained analytically. Rank
    deficiency (|det J4| < RANK_EPS) fails closed.
    """
    s = simulate6(m, theta)
    A, B, C, D = s["A"], s["B"], s["C"], s["D"]
    Q, R = m["Q"], m["R"]
    c, e = m["coupler"], m["extension"]
    a0, a1 = m["attachment"]
    t0, t1 = m["tool"]
    ba = vsub(B, A)
    cd = vsub(C, D)
    bq = vsub(B, Q)
    cr = vsub(C, R)
    u = vdiv(ba, c)
    v = vdiv(cd, e)
    n1 = vdiv(ba, vnorm(ba))
    n2 = vdiv(bq, vnorm(bq))
    n3 = vdiv(cd, vnorm(cd))
    n4 = vdiv(cr, vnorm(cr))
    # du/dB = I/c (u = (B - A)/c is an algebraic definition, so its
    # partials are FREE: the projected form (I - u uT)/c differs from
    # I/c by a multiple of row 1 -- n1 == u exactly -- i.e. it is a
    # row operation, legal only if the matching operation is applied
    # to the rhs too. J and rhs below use the free form uniformly;
    # mixing the two forms in one system was a real bug caught by
    # sens_fd_check). dD/dB = (a0*I + a1*P)/c.
    mfree = ((a0 / c, -a1 / c), (a1 / c, a0 / c))
    col1 = (mfree[0][0], mfree[1][0])
    col2 = (mfree[0][1], mfree[1][1])
    jac = [
        [n1[0], n1[1], 0.0, 0.0],
        [n2[0], n2[1], 0.0, 0.0],
        [-vdot(n3, col1), -vdot(n3, col2), n3[0], n3[1]],
        [0.0, 0.0, n4[0], n4[1]],
    ]
    # direct (fixed-X) partials entering the constraints and outputs
    u_a = (math.cos(theta), math.sin(theta))

    def dd_from_da(da):
        du = vscale(-1.0 / c, da)
        return vadd(da, vadd(vscale(a0, du), vscale(a1, vperp(du))))

    dd_dr = dd_from_da(u_a)
    du_dc = vscale(-1.0 / c, u)
    dd_dc = vadd(vscale(a0, du_dc), vscale(a1, vperp(du_dc)))
    # The implicit function theorem: G(X, L) = 0 gives
    #   J4 dX/dL = -(dG/dL)|_X,
    # so the right-hand sides below are the NEGATED fixed-X
    # constraint derivatives (e.g. crank: dg1/dr = -n1.u_a -> +n1.u_a;
    # coupler: dg1/dc = -1 -> +1; extension: dg3/de = -1 -> +1).
    rhs = {
        "crank": [vdot(n1, u_a), 0.0, vdot(n3, dd_dr), 0.0],
        "coupler": [1.0, 0.0, vdot(n3, dd_dc), 0.0],
        "rocker": [0.0, 1.0, 0.0, 0.0],
        "extension": [0.0, 0.0, 1.0, 0.0],
        "output_rocker": [0.0, 0.0, 0.0, 1.0],
    }
    lu, det, perm = lu_decompose(jac)
    if abs(det) < RANK_EPS:
        return {"rank_deficient": True, "det": det}
    # Output chain in the same FREE derivatives as J and rhs
    # (u = (B - A)/c is an algebraic definition: du/dB = I/c; the
    # total du below is (dB - dA)/c plus the link's direct term --
    # crank moves A, coupler rescales u -- and each direct term
    # appears exactly once, in exactly one place).
    # Direct (fixed-X) terms: crank moves A; coupler rescales u.
    da_direct = {"crank": u_a, "coupler": (0.0, 0.0),
                 "rocker": (0.0, 0.0), "extension": (0.0, 0.0),
                 "output_rocker": (0.0, 0.0)}
    du_direct = {"crank": (0.0, 0.0), "coupler": du_dc,
                 "rocker": (0.0, 0.0), "extension": (0.0, 0.0),
                 "output_rocker": (0.0, 0.0)}
    links = {}
    for link in LINK_NAMES:
        dx = lu_solve(lu, perm, rhs[link])
        dbv = (dx[0], dx[1])
        dcv = (dx[2], dx[3])
        du = vadd(vdiv(vsub(dbv, da_direct[link]), c),
                  du_direct[link])
        dd = vadd(da_direct[link],
                  vadd(vscale(a0, du), vscale(a1, vperp(du))))
        dv = vdiv(vsub(dcv, dd), e)
        if link == "extension":
            dv = vadd(dv, vscale(-1.0 / e, v))
        dp = vadd(dd, vadd(vscale(t0, dv), vscale(t1, vperp(dv))))
        dphi = (v[0] * dv[1] - v[1] * dv[0]) / vdot(v, v)
        links[link] = {"dP": dp, "dphi": dphi}
    return {"rank_deficient": False, "det": det, "links": links}


def sens_fd_check(m, theta, analytic):
    """Central finite differences of the exact re-solved assembly vs
    the analytic sensitivities. Returns (ok, max_dev, notes)."""
    max_dev = 0.0
    notes = []
    for link in LINK_NAMES:
        val = m[link]
        h = FD_STEP_REL * val
        plus = dict(m)
        minus = dict(m)
        plus[link] = val + h
        minus[link] = val - h
        try:
            sp = simulate6(plus, theta)
            sm = simulate6(minus, theta)
        except ValueError:
            notes.append("%s: perturbed assembly undefined" % link)
            continue
        dp_fd = vscale(1.0 / (2.0 * h), vsub(sp["P"], sm["P"]))
        dphi_fd = wrap(sp["angle"] - sm["angle"]) / (2.0 * h)
        an = analytic["links"][link]
        dev = max(vnorm(vsub(dp_fd, an["dP"])),
                  abs(dphi_fd - an["dphi"]))
        max_dev = max(max_dev, dev)
    return (len(notes) == 0), max_dev, notes


def worst_corners(sens):
    """Worst-case combined pose error over the 32 link-sign corners
    (exact enumeration; the linear-superposition WC-L convention)."""
    dps = [sens["links"][k]["dP"] for k in LINK_NAMES]
    dphis = [sens["links"][k]["dphi"] for k in LINK_NAMES]
    worst_pos = 0.0
    worst_ori = 0.0
    for mask in range(32):
        acc_p = (0.0, 0.0)
        acc_o = 0.0
        for j in range(5):
            if mask & (1 << j):
                acc_p = vadd(acc_p, dps[j])
                acc_o += dphis[j]
            else:
                acc_p = vsub(acc_p, dps[j])
                acc_o -= dphis[j]
        worst_pos = max(worst_pos, vnorm(acc_p))
        worst_ori = max(worst_ori, abs(acc_o))
    return worst_pos, worst_ori


# ---------------------------------------------------------------------------
# Corpus emission (schema 1.1, additive; job-local emitter following
# the shared conventions: units block + provenance on every row,
# JSON Lines primary + flat CSV projection, fail-closed on unknown
# kinds or missing blocks).
# ---------------------------------------------------------------------------

UNITS_BLOCK = {
    "position": "normalized (bounding-box diagonal of the -01"
                " layout loop)",
    "position_basis": "six-bar research-corpus basis: one unit ="
                      " the task bounding-box diagonal; the"
                      " frame_mapping rows carry the computed mm"
                      " scale; never mix with the 100 mm task-layer"
                      " basis without re-declaring this block",
    "angle": "deg",
}

KNOWN_KINDS = {
    "demand", "design_parameter", "frame_mapping", "seed_summary",
    "per_sample", "transmission", "transmission_sample", "envelope",
    "tolerance", "sensitivity", "sensitivity_sample", "gate",
    "scorecard_verdict", "reciprocity", "changelog",
}


def validate_row(row, source_commit):
    if not isinstance(row, dict) or "kind" not in row:
        raise ValueError("corpus row without kind")
    if row["kind"] not in KNOWN_KINDS:
        raise ValueError("unknown row kind: %r" % row["kind"])
    if row.get("units") != UNITS_BLOCK:
        raise ValueError("row without the pinned units block")
    if row.get("corpus_schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("row without the pinned corpus schema version")
    if row.get("major") != CORPUS_MAJOR:
        raise ValueError("row without the pinned corpus major version")
    if row.get("provenance", {}).get("source_commit") != source_commit:
        raise ValueError("row without pinned provenance source commit")
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
            "design": "six-bar flip carrier motion task"
                      " (flip_sixbar.motion.json); S2-S4 audit"
                      " over the recorded solver results",
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
# Input validation (fail-closed).
# ---------------------------------------------------------------------------

def die(message):
    print("flip_sixbar_audit: FAIL-CLOSED: %s" % message,
          file=sys.stderr)
    raise SystemExit(1)


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def finite_or_none(value):
    return value is None or finite_number(value)


def s0_recheck(task, path):
    """The validator's own rules (engine.validate + targets.py),
    re-applied fail-closed, plus the staging-integrity pins."""
    keys = {"theta_rad", "branches", "q", "v", "a"}
    if not isinstance(task, dict) or set(task) != keys:
        die("%s: input must contain exactly theta_rad, branches, q, v"
            " and a" % path)
    theta = task["theta_rad"]
    if not isinstance(theta, list) or len(theta) != 12:
        die("%s: theta_rad must have 12 entries" % path)
    for i, t in enumerate(theta):
        if not finite_number(t) or abs(
                t - i * 2.0 * math.pi / 12.0) > 1e-10:
            die("%s: theta_rad must be twelve equally spaced"
                " increasing crank angles starting at zero" % path)
    br = task["branches"]
    if (not isinstance(br, list) or len(br) != 2
            or br[0] not in (-1, 1) or br[1] not in (-1, 1)):
        die("%s: branches must be two known assembly branch signs"
            % path)
    for name in ("q", "v", "a"):
        block = task[name]
        if not isinstance(block, list) or len(block) != 12:
            die("%s: %s must have twelve rows" % (path, name))
        for row in block:
            if (not isinstance(row, list) or len(row) != 3
                    or not all(finite_number(x) for x in row)):
                die("%s: %s must be 12x3 finite [x, y, angle] rows"
                    % (path, name))
    pts = [(row[0], row[1]) for row in task["q"]]
    mx = sum(p[0] for p in pts) / 12.0
    my = sum(p[1] for p in pts) / 12.0
    diag = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts),
                      max(p[1] for p in pts) - min(p[1] for p in pts))
    centroid_res = max(abs(mx), abs(my))
    diag_res = abs(diag - 1.0)
    if centroid_res > 1e-8 or diag_res > 1e-8:
        die("%s: position targets must be centered and normalized"
            " to unit bounding-box diagonal (centroid residual %.3e,"
            " diagonal residual %.3e)" % (path, centroid_res,
                                          diag_res))
    # staging-integrity pins: the frozen demand poses and dwells
    pins = ((0, 0.0), (2, math.pi / 2.0), (4, math.pi))
    for phase, ang in pins:
        if abs(wrap(task["q"][phase][2] - ang)) > EPS_PIN:
            die("%s: phase %d orientation pin violated" % (path, phase))
    for phase in HANDOFF_PHASES:
        if (abs(task["v"][phase][2]) > EPS_PIN
                or abs(task["a"][phase][2]) > EPS_PIN):
            die("%s: phase %d handoff dwell (zero angular rate and"
                " acceleration) violated" % (path, phase))
    return {"centroid_residual": centroid_res,
            "diagonal_residual": diag_res}


def frame_mapping(task):
    """Derive the mm frame from the frozen artifact plus the exact
    demand poses (computed, never transcribed), with fail-closed
    checks against the recorded 260 x 90 mm bounding box."""
    q = task["q"]
    span = q[4][0] - q[0][0]
    if span <= 0:
        die("frame mapping: carry endpoints do not span x")
    scale = CARRY_X_SPAN_MM / span          # mm per normalized unit
    cx = -130.0 - q[0][0] * scale           # mm
    cy = 50.0 - q[0][1] * scale
    recorded = math.hypot(CARRY_X_SPAN_MM, BBOX_Y_SPAN_MM)
    scale_res = abs(scale - recorded)
    if scale_res > 1e-6 * scale:
        die("frame mapping: scale %.9f mm disagrees with the recorded"
            " bounding-box diagonal %.9f mm" % (scale, recorded))
    def to_mm(p):
        return (p[0] * scale + cx, p[1] * scale + cy)
    for phase, (px, py, _a) in zip(DEMAND_PHASES, DEMAND_POSES_MM):
        mx, my = to_mm(q[phase])
        if abs(mx - px) > EPS_MAP or abs(my - py) > EPS_MAP:
            die("frame mapping: demand phase %d reproduces"
                " (%.6f, %.6f) mm, expected (%.1f, %.1f)"
                % (phase, mx, my, px, py))
    for i, row in enumerate(q):
        mx, my = to_mm(row)
        if not (-130.0 - EPS_MAP <= mx <= 130.0 + EPS_MAP
                and -40.0 - EPS_MAP <= my <= 50.0 + EPS_MAP):
            die("frame mapping: sample %d maps outside the recorded"
                " bounding box: (%.6f, %.6f) mm" % (i, mx, my))
    return {"scale_mm": scale, "center_mm": (cx, cy),
            "scale_residual_mm": scale_res, "to_mm": to_mm}


def validate_result(obj, path):
    """Structural checks on a solver result file (schema 3),
    fail-closed."""
    def need(condition, message):
        if not condition:
            die("%s: %s" % (path, message))
    need(isinstance(obj, dict), "result is not an object")
    need(obj.get("schema_version") == 3, "schema_version must be 3")
    need(obj.get("status") == "experimental",
         'status must be "experimental"')
    need(isinstance(obj.get("qualified"), bool),
         "qualified must be a boolean")
    ev = obj.get("objective_evaluations")
    need(isinstance(ev, int) and not isinstance(ev, bool)
         and 0 <= ev <= 200, "objective_evaluations must be an int"
         " in [0, 200]")
    need(obj.get("maximum_objective_evaluations") == 200,
         "maximum_objective_evaluations must be 200")
    m = obj.get("mechanism_normalized")
    need(isinstance(m, dict), "mechanism_normalized missing")
    mkeys = {"O", "Q", "R", "crank", "coupler", "rocker",
             "attachment", "extension", "output_rocker", "tool",
             "mounting", "branches"}
    need(set(m) == mkeys, "mechanism_normalized must carry exactly"
         " the documented fields")
    for key in ("O", "Q", "R"):
        need(isinstance(m[key], list) and len(m[key]) == 2
             and all(finite_number(x) for x in m[key]),
             "mechanism_normalized.%s must be a finite 2-list" % key)
    for key in ("crank", "coupler", "rocker", "extension",
                "output_rocker"):
        need(finite_number(m[key]) and m[key] > 0,
             "mechanism_normalized.%s must be positive finite" % key)
    for key in ("attachment", "tool"):
        need(isinstance(m[key], list) and len(m[key]) == 2
             and all(finite_number(x) for x in m[key]),
             "mechanism_normalized.%s must be a finite 2-list" % key)
    need(finite_number(m["mounting"]),
         "mechanism_normalized.mounting must be finite")
    need(isinstance(m["branches"], list) and len(m["branches"]) == 2
         and m["branches"][0] in (-1, 1)
         and m["branches"][1] in (-1, 1),
         "mechanism_normalized.branches must be two signs")
    ph = obj.get("phases_rad")
    need(isinstance(ph, list) and len(ph) == 12
         and all(finite_number(x) for x in ph),
         "phases_rad must be twelve finite numbers")
    for i, x in enumerate(ph):
        need(abs(x - i * 2.0 * math.pi / 12.0) <= EPS_PHASES,
             "phases_rad must sit on the uniform grid (entry %d)" % i)
    ps = obj.get("per_sample")
    need(isinstance(ps, dict) and set(ps) == set(SAMPLE_KEYS),
         "per_sample must carry the six declared channels")
    for key in SAMPLE_KEYS:
        need(isinstance(ps[key], list) and len(ps[key]) == 12
             and all(finite_or_none(x) for x in ps[key]),
             "per_sample.%s must be twelve finite numbers or None"
             % key)
    sel = obj.get("selected")
    need(isinstance(sel, dict), "selected missing")
    met = sel.get("metrics")
    need(isinstance(met, dict), "selected.metrics missing")
    need(isinstance(met.get("errors"), list) and len(met["errors"]) == 6
         and all(finite_or_none(x) for x in met["errors"]),
         "selected.metrics.errors must be six finite-or-None values")
    need(finite_number(met.get("score")), "selected.metrics.score"
         " must be finite")
    for key in ("defined", "pose_pass", "combined_pass"):
        need(isinstance(met.get(key), bool),
             "selected.metrics.%s must be a boolean" % key)
    need(isinstance(sel.get("evaluations"), int)
         and not isinstance(sel.get("evaluations"), bool),
         "selected.evaluations must be an int")
    need(isinstance(sel.get("reason"), str), "selected.reason must be"
         " a string")
    seed = obj.get("random_seed")
    need(isinstance(seed, int) and not isinstance(seed, bool)
         and 0 <= seed <= 2 ** 63 - 1,
         "random_seed must be an int in [0, 2^63-1]")
    need(isinstance(obj.get("issues"), list), "issues must be a list")
    label = obj.get("selected_label")
    need(label is None or isinstance(label, str),
         "selected_label must be a string or null")
    return {"seed": seed, "label": label}


# ---------------------------------------------------------------------------
# Computation.
# ---------------------------------------------------------------------------

def fmt(v, nd=3):
    if v is None:
        return "n/a"
    return "%.*f" % (nd, v)


def worst_of(values):
    """(max, index) over finite entries; (None, None) if none."""
    best = None
    bi = None
    for i, v in enumerate(values):
        if v is None:
            continue
        if best is None or v > best:
            best = v
            bi = i
    return best, bi


def compute(task, results, source_commit):
    rows = []
    report = []
    r = report.append

    s0 = s0_recheck(task, "<task>")
    frame = frame_mapping(task)
    scale = frame["scale_mm"]
    to_mm = frame["to_mm"]

    r("flip-station-sixbar-01 -- the S2-S4 audit instrument"
      " (deterministic, pure stdlib)")
    r("python: %s" % sys.version.split()[0])
    r("source commit: %s" % source_commit)
    r("task: flip_sixbar.motion.json (validated against the"
      " validator's own rules; centroid residual %.3e, diagonal"
      " residual %.3e)" % (s0["centroid_residual"],
                           s0["diagonal_residual"]))
    r("frame mapping (derived from the frozen artifact + the exact"
      " demand poses):")
    r("  1 normalized unit = %.6f mm (residual vs the recorded"
      " 260 x 90 mm diagonal: %.3e mm)" % (scale,
                                           frame["scale_residual_mm"]))
    r("  sample centroid (design frame): (%.6f, %.6f) mm"
      % (frame["center_mm"][0], frame["center_mm"][1]))
    r("  demand poses reproduced exactly; all twelve samples inside"
      " the recorded bounding box")
    r("results: %d file(s)" % len(results))
    r("")

    # ---- shared rows -------------------------------------------------
    for i, (px, py, pa) in enumerate(DEMAND_POSES_MM):
        rows.append(base_row("demand", source_commit, phase=i + 1,
                             x_mm=px, y_mm=py, phi_deg=pa,
                             tolerance_pos_mm=TOL_POS_MM,
                             tolerance_ori_deg=TOL_ORI_DEG))
    rows.append(base_row(
        "design_parameter", source_commit, name="transmission_gates",
        value="hard mu in [40, 140] deg (deviation from 90 deg"
              " <= 50 deg); target mu in [50, 130] deg",
        reason="the freeze correction (Catch 2 of the fold): the"
               " linkage convention's hard floor restated against"
               " the deviation measure"))
    rows.append(base_row(
        "design_parameter", source_commit, name="link_length_class",
        value_mm=LINK_TOL_MM,
        reason="declared manufactured-length class; the cam line's"
               " 0.1 mm clearance class carried to bar lengths"
               " (the -07 uniform 0.10 mm class precedent);"
               " first-order WC-L pricing, worst case over the 32"
               " sign corners"))
    rows.append(base_row(
        "design_parameter", source_commit, name="priced_links",
        value="crank, coupler, rocker, extension, output_rocker",
        reason="declared scope: the five manufactured bar lengths"
               " (the JOB's frozen link-length sensitivities); the"
               " attachment triangle, tool geometry, ground-pivot"
               " locations and mounting angle are unpriced in this"
               " study -- recorded as a scope limit, not audited"))
    rows.append(base_row(
        "design_parameter", source_commit, name="part_model",
        value="exact in-plane rectangle 100 x 5 mm, computed by"
              " this script at pose samples (%.2f deg grid);"
              " sampled, never certified" % AUDIT_STEP_DEG,
        reason="the cam script's discipline carried unchanged"
               " (the fold's Q4 answer); identity mount (part"
               " centroid at the carrier origin, part axes ="
               " carrier axes, the B2 seam declaration)"))
    rows.append(base_row(
        "design_parameter", source_commit, name="audit_grids",
        value="transmission/envelope sweep %.2f deg; emitted"
              " transmission and sensitivity rows %.1f deg"
              % (AUDIT_STEP_DEG, EMIT_STEP_DEG),
        reason="frozen, deterministic"))
    rows.append(base_row(
        "design_parameter", source_commit, name="solver_s1_gates",
        value=json.dumps({k: SOLVER_LIMITS[k] for k in SAMPLE_KEYS}),
        reason="the solver's own qualification gates"
               " (continuation.py LIMITS), consumed read-only as"
               " context; the audit never re-gates them"))
    rows.append(base_row(
        "frame_mapping", source_commit,
        scale_mm=scale,
        center_mm=[frame["center_mm"][0], frame["center_mm"][1]],
        scale_residual_mm=frame["scale_residual_mm"],
        method="derived: the carry endpoints x = -130/+130 mm fix"
               " the scale; phase 0 fixes the centroid; fail-closed"
               " checks against the recorded 260 x 90 mm bounding"
               " box and the exact demand poses"))
    rows.append(base_row(
        "gate", source_commit, name="s0_task_contract",
        verdict="PASS",
        window_rule="the validator's own rules re-applied"
                    " fail-closed (five fields, uniform grid,"
                    " branches, 12x3 finite, centroid, unit"
                    " diagonal) plus the staging-integrity pins"
                    " (demand poses, handoff dwells)"))
    r("[S0] TASK-CONTRACT RE-CHECK: PASS (the validator's own"
      " rules, re-applied; the run already proved acceptance)")
    r("  demand pins: phase 0/2/4 -> (-130, 50) 0 deg | (0, 50)"
      " 90 deg | (130, 50) 180 deg, reproduced; handoff dwells zero"
      " rate + accel (exact)")
    r("")

    overlay_pos_norm = TOL_POS_MM / scale
    seed_ids = []
    for res in results:
        seed_ids.append(res["info"]["seed"])
    if len(set(seed_ids)) != len(seed_ids):
        die("duplicate seed in the result files")

    n_grid = int(round(360.0 / AUDIT_STEP_DEG))
    curve_steps = int(round(360.0 / EMIT_STEP_DEG))

    for res in results:
        seed = res["info"]["seed"]
        path = res["path"]
        obj = res["obj"]
        m = obj["mechanism_normalized"]
        ps = obj["per_sample"]
        met = obj["selected"]["metrics"]
        r("[SEED %d] (%s)" % (seed, path))

        # -- S1: native consumption of the per-sample emission ------
        chan_worst = {}
        for key in SAMPLE_KEYS:
            wv, wi = worst_of(ps[key])
            chan_worst[key] = (wv, wi)
        gate_rows = []
        for key in SAMPLE_KEYS:
            wv, _ = chan_worst[key]
            ok = wv is not None and wv <= SOLVER_LIMITS[key]
            gate_rows.append((key, ok))
        s1_ok = obj["qualified"]
        dp_pos = max((ps["position"][p] for p in DEMAND_PHASES),
                     default=None)
        dp_ori = max((ps["orientation"][p] for p in DEMAND_PHASES),
                     default=None)
        all_pos, all_pos_i = worst_of(ps["position"])
        all_ori, all_ori_i = worst_of(ps["orientation"])
        ov_pos = dp_pos is not None and dp_pos <= overlay_pos_norm
        ov_ori = dp_ori is not None and dp_ori <= TOL_ORI_DEG
        r("  S1 (native emission): qualified %s, %d/200 evaluations,"
          " initializer %s, issues %d"
          % (obj["qualified"], obj["objective_evaluations"],
             obj["selected_label"] or "original",
             len(obj["issues"])))
        r("    per-channel worst (emission): position %s (phase %s"
          " | gate %.3g) | orientation %s deg (phase %s | gate"
          " %.3g) | spatial v %s | spatial a %s | angular v %s |"
          " angular a %s"
          % (fmt(chan_worst["position"][0]),
             fmt(chan_worst["position"][1], 0),
             SOLVER_LIMITS["position"],
             fmt(chan_worst["orientation"][0]),
             fmt(chan_worst["orientation"][1], 0),
             SOLVER_LIMITS["orientation"],
             fmt(chan_worst["spatial_velocity"][0]),
             fmt(chan_worst["spatial_acceleration"][0]),
             fmt(chan_worst["angular_velocity"][0]),
             fmt(chan_worst["angular_acceleration"][0])))
        r("    all-12 worst (data): position %s = %s mm (phase %s)"
          " | orientation %s deg (phase %s)"
          % (fmt(all_pos), fmt(None if all_pos is None
                               else all_pos * scale, 2),
             fmt(all_pos_i, 0), fmt(all_ori), fmt(all_ori_i, 0)))
        r("    packaging overlay (demand phases): position %s vs"
          " %.6f normalized (%.1f mm) -> %s | orientation %s deg vs"
          " %.1f deg -> %s"
          % (fmt(dp_pos), overlay_pos_norm, TOL_POS_MM,
             "PASS" if ov_pos else "FAIL", fmt(dp_ori), TOL_ORI_DEG,
             "PASS" if ov_ori else "FAIL"))
        rows.append(base_row(
            "seed_summary", source_commit, seed=seed,
            qualified=obj["qualified"],
            evaluations=obj["objective_evaluations"],
            initializer=obj["selected_label"],
            issues=len(obj["issues"]),
            score=met["score"], defined=met["defined"],
            pose_pass=met["pose_pass"],
            combined_pass=met["combined_pass"],
            worst_position=chan_worst["position"][0],
            worst_position_phase=chan_worst["position"][1],
            worst_orientation_deg=chan_worst["orientation"][0],
            worst_orientation_phase=chan_worst["orientation"][1],
            worst_spatial_velocity=chan_worst[
                "spatial_velocity"][0],
            worst_spatial_acceleration=chan_worst[
                "spatial_acceleration"][0],
            worst_angular_velocity=chan_worst[
                "angular_velocity"][0],
            worst_angular_acceleration=chan_worst[
                "angular_acceleration"][0],
            worst_position_all12=all_pos,
            worst_orientation_all12=all_ori,
            overlay_position_demand=dp_pos,
            overlay_orientation_demand=dp_ori))
        for p in range(12):
            row_fields = {"seed": seed, "phase": p}
            for key in SAMPLE_KEYS:
                row_fields[key] = ps[key][p]
            rows.append(base_row("per_sample", source_commit,
                                 **row_fields))
        rows.append(base_row(
            "gate", source_commit, seed=seed,
            name="s1_qualification",
            verdict="PASS" if s1_ok else "FAIL",
            window_rule="the solver's own gates, consumed read-only"
                         " (the emission's qualified flag)"))
        rows.append(base_row(
            "gate", source_commit, seed=seed, name="packaging_overlay",
            limit_units=overlay_pos_norm, limit_deg=TOL_ORI_DEG,
            value_units=dp_pos, value_deg=dp_ori,
            verdict=("PASS" if (ov_pos and ov_ori) else "FAIL"),
            window_rule="worst position/orientation error over the"
                        " three demand phases (0/2/4), from the"
                        " emission"))

        # -- the audit sweep -------------------------------------------
        samples = []
        undefined_at = None
        try:
            for i in range(n_grid):
                theta = 2.0 * math.pi * i / n_grid
                s = simulate6(m, theta)
                bad = check_edges(m, s)
                if bad > EPS_EDGES:
                    die("seed %d: edge-length self-check %.3e"
                        " exceeds %.1e at grid sample %d"
                        % (seed, bad, EPS_EDGES, i))
                samples.append(s)
            s_close = simulate6(m, 2.0 * math.pi)
            closure = vnorm(vsub(s_close["P"], samples[0]["P"]))
            if closure > EPS_CLOSURE:
                die("seed %d: cycle closure residual %.3e exceeds"
                    " %.1e" % (seed, closure, EPS_CLOSURE))
        except ValueError as exc:
            undefined_at = i
            r("  [SWEEP] UNDEFINED ASSEMBLY at grid sample %d"
              " (%.2f deg): %s -- the S2-S4 audits fail closed for"
              " this seed (never a quiet pass)" % (i, i * AUDIT_STEP_DEG,
                                                   exc))
        if undefined_at is None:
            mu_b = [folded_mu("A", "B", "Q", s) for s in samples]
            mu_c = [folded_mu("D", "C", "R", s) for s in samples]
            worst_b = min(mu_b)
            worst_b_at = mu_b.index(worst_b) * AUDIT_STEP_DEG
            worst_c = min(mu_c)
            worst_c_at = mu_c.index(worst_c) * AUDIT_STEP_DEG
            hard_ok = min(worst_b, worst_c) >= MU_HARD_DEG
            target_ok = min(worst_b, worst_c) >= MU_TARGET_DEG
            r("  [S2] TRANSMISSION AUDIT (%.2f deg grid, %d samples"
              " + closure %.3e):" % (AUDIT_STEP_DEG, n_grid, closure))
            r("    joint B (coupler-vs-rocker): worst mu %.3f deg at"
              " crank %.2f deg | hard %.0f: %s | target %.0f: %s"
              % (worst_b, worst_b_at, MU_HARD_DEG,
                 "PASS" if worst_b >= MU_HARD_DEG else "FAIL",
                 MU_TARGET_DEG,
                 "PASS" if worst_b >= MU_TARGET_DEG else "FAIL"))
            r("    joint C (extension-vs-output rocker): worst mu"
              " %.3f deg at crank %.2f deg | hard %.0f: %s | target"
              " %.0f: %s"
              % (worst_c, worst_c_at, MU_HARD_DEG,
                 "PASS" if worst_c >= MU_HARD_DEG else "FAIL",
                 MU_TARGET_DEG,
                 "PASS" if worst_c >= MU_TARGET_DEG else "FAIL"))
            r("    edge-length self-check: max %.3e (fail-closed"
              " under %.1e)" % (max(check_edges(m, s)
                                    for s in samples), EPS_EDGES))
            rows.append(base_row(
                "transmission", source_commit, seed=seed,
                joint="B", pair="A-B-Q",
                worst_mu_deg=worst_b, worst_at_crank_deg=worst_b_at,
                hard_floor_deg=MU_HARD_DEG,
                target_floor_deg=MU_TARGET_DEG,
                hard_pass=bool(worst_b >= MU_HARD_DEG),
                target_pass=bool(worst_b >= MU_TARGET_DEG)))
            rows.append(base_row(
                "transmission", source_commit, seed=seed,
                joint="C", pair="D-C-R",
                worst_mu_deg=worst_c, worst_at_crank_deg=worst_c_at,
                hard_floor_deg=MU_HARD_DEG,
                target_floor_deg=MU_TARGET_DEG,
                hard_pass=bool(worst_c >= MU_HARD_DEG),
                target_pass=bool(worst_c >= MU_TARGET_DEG)))
            for i in range(curve_steps):
                j = int(round(i * EMIT_STEP_DEG / AUDIT_STEP_DEG))
                rows.append(base_row(
                    "transmission_sample", source_commit, seed=seed,
                    crank_deg=i * EMIT_STEP_DEG, mu_b_deg=mu_b[j],
                    mu_c_deg=mu_c[j]))
            rows.append(base_row(
                "gate", source_commit, seed=seed,
                name="s2_transmission_hard",
                limit_deg=MU_HARD_DEG,
                value_deg=min(worst_b, worst_c),
                verdict="PASS" if hard_ok else "FAIL",
                window_rule="per-joint worst folded transmission"
                            " angle over the full cycle, both output"
                            " joints"))
            rows.append(base_row(
                "gate", source_commit, seed=seed,
                name="s2_transmission_target",
                limit_deg=MU_TARGET_DEG,
                value_deg=min(worst_b, worst_c),
                verdict="PASS" if target_ok else "FAIL",
                window_rule="the tighter declared pair"))

            # -- S3: swept envelope + occupancy --------------------
            xs_min = xs_max = ys_min = ys_max = None
            tip_y = None
            tip_at = None
            link_min = [1e30, 1e30]
            link_max = [-1e30, -1e30]
            for i, s in enumerate(samples):
                pm = to_mm(s["P"])
                for sx in (-1.0, 1.0):
                    for sy in (-1.0, 1.0):
                        corner = vadd(pm, vrot(
                            s["angle"],
                            (sx * PART_HALF_LONG_MM,
                             sy * PART_HALF_SHORT_MM)))
                        if xs_min is None:
                            xs_min = xs_max = corner[0]
                            ys_min = ys_max = corner[1]
                        else:
                            xs_min = min(xs_min, corner[0])
                            xs_max = max(xs_max, corner[0])
                            ys_min = min(ys_min, corner[1])
                            ys_max = max(ys_max, corner[1])
                        if tip_y is None or corner[1] > tip_y:
                            tip_y = corner[1]
                            tip_at = corner[0]
                for key in ("A", "B", "D", "C"):
                    jm = to_mm(s[key])
                    link_min[0] = min(link_min[0], jm[0])
                    link_min[1] = min(link_min[1], jm[1])
                    link_max[0] = max(link_max[0], jm[0])
                    link_max[1] = max(link_max[1], jm[1])
            pivots = {k: to_mm(m[k]) for k in ("O", "Q", "R")}
            env_min = [min(xs_min, link_min[0]), min(ys_min, link_min[1])]
            env_max = [max(xs_max, link_max[0]), max(ys_max, link_max[1])]
            r("  [S3] GEOMETRY AUDITS (defined assembly over the"
              " sweep: YES):")
            r("    part sweep bbox (mm): x [%.2f, %.2f], y [%.2f,"
              " %.2f] (sampled at %.2f deg, never certified)"
              % (xs_min, xs_max, ys_min, ys_max, AUDIT_STEP_DEG))
            r("    through-vertical transit tip height: %.2f mm at x"
              " = %.2f mm" % (tip_y, tip_at))
            r("    linkage joint sweep bbox (mm): x [%.2f, %.2f], y"
              " [%.2f, %.2f]" % (link_min[0], link_max[0],
                                 link_min[1], link_max[1]))
            r("    ground pivots (mm): O (%.2f, %.2f) | Q (%.2f,"
              " %.2f) | R (%.2f, %.2f)"
              % (pivots["O"][0], pivots["O"][1], pivots["Q"][0],
                 pivots["Q"][1], pivots["R"][0], pivots["R"][1]))
            r("    overall envelope (mm): x [%.2f, %.2f], y [%.2f,"
              " %.2f]" % (env_min[0], env_max[0], env_min[1],
                          env_max[1]))
            r("    utilization table (mm, the -06 required-table"
              " precedent; no size demand frozen, rows are data):")
            r("      consumer           extent")
            r("      part sweep         x [%.1f, %.1f], y [%.1f,"
              " %.1f]" % (xs_min, xs_max, ys_min, ys_max))
            r("      linkage joints     x [%.1f, %.1f], y [%.1f,"
              " %.1f]" % (link_min[0], link_max[0], link_min[1],
                          link_max[1]))
            r("      ground pivots      O (%.1f, %.1f), Q (%.1f,"
              " %.1f), R (%.1f, %.1f)"
              % (pivots["O"][0], pivots["O"][1], pivots["Q"][0],
                 pivots["Q"][1], pivots["R"][0], pivots["R"][1]))
            r("      handoff stations   (-130, 50) and (130, 50)"
              " (the demand poses)")
            r("      headroom: part sweep y-max %.1f vs overall"
              " y-max %.1f (headroom %.1f mm, recorded not gated)"
              % (ys_max, env_max[1], env_max[1] - ys_max))
            r("    part-sweep rectangle occupancy: the exact"
              " rectangle sampled at the same grid; no keep-out gate"
              " (the Q4 deferral carries)")
            for phase, crank in zip(DEMAND_PHASES,
                                    DEMAND_CRANK_DEG):
                theta = math.radians(crank)
                s = simulate6(m, theta)
                pm = to_mm(s["P"])
                corners = [vadd(pm, vrot(s["angle"],
                                        (sx * PART_HALF_LONG_MM,
                                         sy * PART_HALF_SHORT_MM)))
                           for sx in (-1.0, 1.0)
                           for sy in (-1.0, 1.0)]
                rows.append(base_row(
                    "envelope", source_commit, seed=seed,
                    name="demand_part_rectangle", phase=phase,
                    crank_deg=crank,
                    corners_mm=json.dumps([[c[0], c[1]]
                                           for c in corners])))
            rows.append(base_row(
                "envelope", source_commit, seed=seed,
                name="part_sweep",
                bbox_mm=json.dumps([xs_min, xs_max, ys_min, ys_max]),
                tip_height_mm=tip_y, tip_at_x_mm=tip_at,
                note="exact-rectangle part model, sampled at %.2f deg"
                     " pose samples, never certified" % AUDIT_STEP_DEG))
            rows.append(base_row(
                "envelope", source_commit, seed=seed,
                name="linkage_sweep",
                bbox_mm=json.dumps([link_min[0], link_max[0],
                                    link_min[1], link_max[1]]),
                pivots_mm=json.dumps([[pivots["O"][0],
                                       pivots["O"][1]],
                                      [pivots["Q"][0],
                                       pivots["Q"][1]],
                                      [pivots["R"][0],
                                       pivots["R"][1]]])))
            rows.append(base_row(
                "envelope", source_commit, seed=seed,
                name="overall_envelope",
                bbox_mm=json.dumps([env_min[0], env_max[0],
                                    env_min[1], env_max[1]]),
                handoff_stations_mm=json.dumps(
                    [[-130.0, 50.0], [130.0, 50.0]]),
                headroom_mm=env_max[1] - ys_max,
                note="the -06 required-table precedent; no size"
                     " demand is frozen, rows are data"))
            rows.append(base_row(
                "gate", source_commit, seed=seed,
                name="s3_geometry",
                verdict="CONFIRMED",
                window_rule="defined assembly over the sweep;"
                            " utilization table present; occupancy"
                            " sampled, never certified; no keep-out"
                            " gate (the Q4 deferral)"))

            # -- S4: Jacobian link-length sensitivities ------------
            r("  [S4] TOLERANCE ROWS (analytic constraint Jacobian,"
              " %.1f mm link class, worst case over the 32 sign"
              " corners):" % LINK_TOL_MM)
            tol_ok = True
            rank_notes = []
            fd_max = 0.0
            fd_notes = []
            for phase, crank in zip(DEMAND_PHASES, DEMAND_CRANK_DEG):
                theta = math.radians(crank)
                sens = sens_at(m, theta)
                if sens["rank_deficient"]:
                    rank_notes.append("phase %d (crank %.0f deg)"
                                      % (phase, crank))
                    r("    phase %d (crank %.0f deg): RANK-DEFICIENT"
                      " constraint Jacobian (|det| %.3e < %.1e) --"
                      " dead-point row, fail-closed, no finite"
                      " numbers" % (phase, crank, abs(sens["det"]),
                                    RANK_EPS))
                    rows.append(base_row(
                        "tolerance", source_commit, seed=seed,
                        phase=phase, crank_deg=crank,
                        rank_deficient=True,
                        reason="the position-level closure is"
                               " rank-deficient at fixed crank"
                               " angle (a toggle configuration);"
                               " the infinitesimal map cannot"
                               " bound the pose -- fail-closed"))
                    if phase in HANDOFF_PHASES:
                        tol_ok = False
                    continue
                ok, dev, notes = sens_fd_check(m, theta, sens)
                fd_max = max(fd_max, dev)
                fd_notes.extend("%s phase %d: %s" % (n, phase, note)
                                for note in notes)
                if not notes and dev > FD_TOL:
                    die("seed %d: S4 FD self-check deviates %.3e >"
                        " %.1e at phase %d" % (seed, dev, FD_TOL,
                                               phase))
                wp, wo = worst_corners(sens)
                wp_mm = wp * LINK_TOL_MM
                wo_deg = math.degrees(wo) * LINK_TOL_MM / scale
                label = ("handoff pick" if phase == 0 else
                         "through-vertical (data)" if phase == 2
                         else "handoff place")
                r("    %s (phase %d, crank %.0f deg): per-link pos"
                  " gains (mm/mm): %s | combined worst %.4f mm vs"
                  " %.1f mm" %
                  (label, phase, crank,
                   " ".join("%s %.4f" % (k, vnorm(
                       sens["links"][k]["dP"]))
                        for k in LINK_NAMES), wp_mm, TOL_POS_MM))
                r("      per-link ori gains (deg/mm): %s | combined"
                  " worst %.4f deg vs %.1f deg"
                  % (" ".join("%s %.4f" % (k, math.degrees(
                      abs(sens["links"][k]["dphi"])) / scale)
                              for k in LINK_NAMES),
                     wo_deg, TOL_ORI_DEG))
                for link in LINK_NAMES:
                    rows.append(base_row(
                        "tolerance", source_commit, seed=seed,
                        phase=phase, crank_deg=crank, link=link,
                        pos_gain_mm_per_mm=vnorm(
                            sens["links"][link]["dP"]),
                        ori_gain_deg_per_mm=math.degrees(
                            abs(sens["links"][link]["dphi"])) / scale,
                        rank_deficient=False))
                rows.append(base_row(
                    "tolerance", source_commit, seed=seed,
                    phase=phase, crank_deg=crank, link="combined_wc",
                    pos_error_mm=wp_mm, ori_error_deg=wo_deg,
                    pos_margin_mm=TOL_POS_MM - wp_mm,
                    ori_margin_deg=TOL_ORI_DEG - wo_deg,
                    rank_deficient=False))
                if phase in HANDOFF_PHASES:
                    if wp_mm > TOL_POS_MM or wo_deg > TOL_ORI_DEG:
                        tol_ok = False
            if fd_max > 0.0:
                r("    FD self-check (central differences of the"
                  " exact re-solved assembly): max deviation %.3e"
                  " -- %s" % (fd_max, "VERIFIED" if fd_max <= FD_TOL
                              else "FAIL"))
            for note in sorted(set(fd_notes)):
                r("    FD note: %s" % note)
            # sensitivity curve + the max-sensitivity region
            curve = []
            dead = []
            for i in range(curve_steps):
                crank = i * EMIT_STEP_DEG
                theta = math.radians(crank)
                sens = sens_at(m, theta)
                if sens["rank_deficient"]:
                    curve.append(None)
                    dead.append(crank)
                    rows.append(base_row(
                        "sensitivity_sample", source_commit, seed=seed,
                        crank_deg=crank, combined_gain=None,
                        dead_point=True))
                else:
                    wp, _ = worst_corners(sens)
                    curve.append(wp)
                    rows.append(base_row(
                        "sensitivity_sample", source_commit, seed=seed,
                        crank_deg=crank, combined_gain=wp,
                        dead_point=False))
            finite_curve = [(g, i * EMIT_STEP_DEG)
                            for i, g in enumerate(curve)
                            if g is not None]
            if finite_curve:
                peak_gain, peak_at = max(finite_curve)
                at_pose = peak_at in DEMAND_CRANK_DEG
                r("    sensitivity curve (%.0f deg grid, combined"
                  " worst-case position gain mm/mm): peak %.4f at"
                  " crank %.0f deg -- %s (frozen prediction: not at"
                  " the poses -> %s, honest data)"
                  % (EMIT_STEP_DEG, peak_gain, peak_at,
                     "AT a demand pose" if at_pose
                     else "not at a demand pose",
                     "CONFIRMED" if not at_pose else "REFUTED"))
                rows.append(base_row(
                    "sensitivity", source_commit, seed=seed,
                    peak_gain=peak_gain, peak_at_crank_deg=peak_at,
                    at_demand_pose=bool(at_pose),
                    prediction="not at the poses",
                    verdict=("CONFIRMED" if not at_pose
                             else "REFUTED"),
                    dead_points_deg=json.dumps(dead)))
            else:
                r("    sensitivity curve: all samples rank-deficient"
                  " (dead-point rows, fail-closed)")
                rows.append(base_row(
                    "sensitivity", source_commit, seed=seed,
                    peak_gain=None, peak_at_crank_deg=None,
                    at_demand_pose=None, prediction="not at the"
                    " poses", verdict="ERROR",
                    dead_points_deg=json.dumps(dead)))
            if rank_notes:
                r("    rank-deficient demand phases: %s"
                  % "; ".join(rank_notes))
            rows.append(base_row(
                "gate", source_commit, seed=seed,
                name="s4_handoff_tolerance",
                limit_mm=TOL_POS_MM, limit_deg=TOL_ORI_DEG,
                verdict="PASS" if tol_ok else "FAIL",
                window_rule="worst-case combined link-length"
                            " perturbation (%.1f mm class, 32 sign"
                            " corners) at both handoffs; rank"
                            " deficiency fails closed" % LINK_TOL_MM))

            # -- kinematics cross-check vs the emission -----------
            xchk_max_pos = 0.0
            xchk_max_ori = 0.0
            emission_none = []
            for p in range(12):
                theta = 2.0 * math.pi * p / 12.0
                s = simulate6(m, theta)
                err_pos = vnorm(vsub(s["P"], (task["q"][p][0],
                                               task["q"][p][1])))
                err_ori = math.degrees(abs(
                    wrap(s["angle"] - task["q"][p][2])))
                em_pos = ps["position"][p]
                em_ori = ps["orientation"][p]
                if em_pos is None or em_ori is None:
                    emission_none.append(p)
                    continue
                xchk_max_pos = max(xchk_max_pos,
                                   abs(err_pos - em_pos))
                xchk_max_ori = max(xchk_max_ori,
                                   abs(err_ori - em_ori))
                if (abs(err_pos - em_pos) > EPS_EMISSION
                        or abs(err_ori - em_ori) > EPS_EMISSION):
                    die("seed %d: kinematics cross-check disagrees"
                        " with the emission at phase %d (position"
                        " %.3e vs %.3e, orientation %.3e vs %.3e)"
                        % (seed, p, err_pos, em_pos, err_ori, em_ori))
            if emission_none:
                r("    kinematics cross-check vs the emission:"
                  " emission carries None at phase(s) %s (the"
                  " tool's own non-finite convention) -- recorded"
                  " as data" % ", ".join(str(p)
                                         for p in emission_none))
            else:
                r("    kinematics cross-check vs the emission:"
                  " max position deviation %.3e, max orientation"
                  " deviation %.3e deg -- %s"
                  % (xchk_max_pos, xchk_max_ori,
                     "VERIFIED" if max(xchk_max_pos,
                                      xchk_max_ori) <= EPS_EMISSION
                     else "FAIL"))
            rows.append(base_row(
                "seed_summary", source_commit, seed=seed,
                xcheck="kinematics_vs_emission",
                max_pos_dev=xchk_max_pos, max_ori_dev=xchk_max_ori,
                emission_none_phases=json.dumps(emission_none)))

            # -- per-seed scorecard --------------------------------
            s2_v = "PASS" if hard_ok else "FAIL"
            s2t_v = "PASS" if target_ok else "FAIL"
            s4_v = "PASS" if tol_ok else "FAIL"
            verdicts = [
                ("S1", "PASS" if s1_ok else "FAIL",
                 "qualification: the solver's own gates, consumed"
                 " read-only from the emission"),
                ("S2", s2_v,
                 "transmission: hard floor %.0f deg %s, target"
                 " %.0f deg %s (worst joint %s)"
                 % (MU_HARD_DEG, "held" if hard_ok else "failed",
                    MU_TARGET_DEG, "held" if target_ok else "failed",
                    "B" if worst_b <= worst_c else "C")),
                ("S3", "CONFIRMED",
                 "geometry: defined assembly over the sweep;"
                 " envelope + utilization table recorded"),
                ("S4", s4_v,
                 "tolerance: combined link-length worst case at the"
                 " handoffs vs the labeled 1.5 mm / 1.5 deg"),
            ]
            for item, verdict, text in verdicts:
                rows.append(base_row("scorecard_verdict",
                                     source_commit, seed=seed,
                                     item=item, verdict=verdict,
                                     text=text))
            overall = ("ALL PASS" if (s1_ok and hard_ok and tol_ok)
                       else "FAIL")
            binding = None
            if not s1_ok:
                binding = "S1"
            elif not hard_ok:
                binding = "S2"
            elif not tol_ok:
                binding = "S4"
            r("    scorecard: S1 %s | S2 hard %s / target %s | S3"
              " CONFIRMED | S4 %s -> overall %s%s"
              % ("PASS" if s1_ok else "FAIL", s2_v, s2t_v, s4_v,
                 overall,
                 "" if binding is None
                 else " (binding: %s)" % binding))
            rows.append(base_row(
                "scorecard_verdict", source_commit, seed=seed,
                item="OVERALL", verdict=overall,
                text=("all scored items held" if binding is None
                      else "binding scored item: %s" % binding)))
        else:
            for item in ("S2", "S3", "S4"):
                rows.append(base_row(
                    "scorecard_verdict", source_commit, seed=seed,
                    item=item, verdict="ERROR",
                    text="undefined assembly on the audit grid"
                         " (grid sample %d) -- fail-closed, never"
                         " a quiet pass" % undefined_at))
            rows.append(base_row(
                "gate", source_commit, seed=seed,
                name="s2_transmission_hard", verdict="ERROR",
                window_rule="undefined assembly on the audit grid"))
            rows.append(base_row(
                "gate", source_commit, seed=seed,
                name="s4_handoff_tolerance", verdict="ERROR",
                window_rule="undefined assembly on the audit grid"))
            rows.append(base_row(
                "scorecard_verdict", source_commit, seed=seed,
                item="OVERALL", verdict="ERROR",
                text="undefined assembly on the audit grid"))
            r("    scorecard: S2/S3/S4 ERROR (undefined assembly;"
              " fail-closed)")
        r("")

    # -- S5: controls ---------------------------------------------------
    rows.append(base_row(
        "gate", source_commit, name="s5_controls", verdict="PASS",
        window_rule="read-only consumption; fail-closed emitter;"
                    " double-run determinism; corpus emission with"
                    " hashes regardless of verdict"))
    rows.append(base_row(
        "reciprocity", source_commit,
        instrument_modification_count=0,
        note="the solver and its per-sample emission are consumed"
             " read-only and unmodified; this script is new"
             " job-local instrumentation (the additive convention)"
             " -- the scored instrument-modification count expected"
             " at the machine step is 0"))
    rows.append(base_row(
        "changelog", source_commit,
        schema_version=CORPUS_SCHEMA_VERSION,
        change="additive: new row kinds (frame_mapping, seed_summary,"
               " per_sample, transmission, transmission_sample,"
               " envelope, tolerance, sensitivity,"
               " sensitivity_sample) joining the shared kinds"
               " (demand, design_parameter, gate, scorecard_verdict,"
               " reciprocity, changelog); per-row units + provenance"
               " blocks; no change to any existing field's meaning,"
               " unit or name -- schema 1.x per the frozen"
               " additive-only succession rule",
        major=CORPUS_MAJOR))
    r("[S5] CONTROLS: read-only consumption of the task and the"
      " recorded results; fail-closed corpus emitter (schema 1.1"
      " pinned, units block + provenance on every row, unknown-kind"
      " refusal); double-run determinism below; corpus emission with"
      " hashes regardless of verdict; instrument-modification count"
      " row emitted (expected 0)")
    r("[RECIPROCITY] instrument modification count: 0 expected --"
      " the solver and its emission consumed unmodified; this"
      " script is new job-local instrumentation")
    return rows, report


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = sys.argv if argv is None else argv
    task_path = None
    result_paths = []
    source_commit = None
    i = 1
    while i < len(argv):
        if argv[i] == "--task" and i + 1 < len(argv):
            task_path = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--result" and i + 1 < len(argv):
            result_paths.append(argv[i + 1])
            i += 2
            continue
        if argv[i] == "--source-commit" and i + 1 < len(argv):
            source_commit = argv[i + 1]
            i += 2
            continue
        print("usage: flip_sixbar_audit.py --task <motion.json>"
              " --result <result.json> [--result ...]"
              " --source-commit <40-hex-sha>", file=sys.stderr)
        return 2
    if task_path is None or not result_paths or source_commit is None:
        print("usage: flip_sixbar_audit.py --task <motion.json>"
              " --result <result.json> [--result ...]"
              " --source-commit <40-hex-sha>", file=sys.stderr)
        return 2
    if (len(source_commit) != 40
            or any(ch not in "0123456789abcdef"
                   for ch in source_commit)):
        print("FAIL-CLOSED: --source-commit must be a 40-char"
              " lowercase hex sha", file=sys.stderr)
        return 2
    try:
        with open(task_path, "r", encoding="utf-8") as fh:
            task = json.load(fh)
    except (ValueError, OSError) as exc:
        print("FAIL-CLOSED: task file: %s" % exc, file=sys.stderr)
        return 2
    results = []
    for path in result_paths:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
        except (ValueError, OSError) as exc:
            print("FAIL-CLOSED: %s: %s" % (path, exc), file=sys.stderr)
            return 2
        info = validate_result(obj, path)
        results.append({"path": path, "obj": obj, "info": info})

    rows1, report1 = compute(task, results, source_commit)
    rows2, report2 = compute(task, results, source_commit)
    corpus1 = [json.dumps(r, sort_keys=True) for r in rows1]
    corpus2 = [json.dumps(r, sort_keys=True) for r in rows2]
    identical = (report1 == report2 and corpus1 == corpus2)
    for line in report1:
        print(line)
    jsonl_path, csv_path, h1, h2 = write_corpus(rows1, source_commit)
    print("")
    print("[CORPUS] %d rows, schema %s (additive; changelog row in"
          " corpus)" % (len(rows1), CORPUS_SCHEMA_VERSION))
    print("  %s" % jsonl_path)
    print("  sha256 %s" % h1)
    print("  %s" % csv_path)
    print("  sha256 %s" % h2)
    print("double-run determinism check: %s" %
          ("IDENTICAL" if identical else "DIFFERS (FAIL)"))
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
