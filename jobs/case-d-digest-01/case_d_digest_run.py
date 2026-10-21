#!/usr/bin/env python3
"""case-d-digest-01 -- the failure-digest instrument for case study D
(the moving-station transfer: a continuous contour with pinned timing).

The staged machine step behind the merged D brief freeze
(jobs/case-d-brief-01/JOB.md, PR #103) and the merged derivation check
(jobs/case-d-derivation-check-01/JOB.md, PR #104: N = 4, the count
rule fires at 7 = N + k). This script consumes the recorded six-bar
motion solver's nine result files (three tasks x three seeds, the
fairness-gate configuration frozen in the brief) plus the three staged
task artifacts and the recorded example, and grades the frozen
scorecard (jobs/case-d-digest-01/JOB.md):

  - D1  POOL CAPABILITY: the demand task graded against ALL declared
        demands -- the seven pinned phases at the 0.10 mm class, the
        between-points contour channel at the same class, and the
        program channels under the solver's own strict qualification.
        The expected honest-failure shape is a recorded outcome,
        never a gate.
  - D2  BINDING-CHANNEL CLASSIFICATION: position-at-pins vs
        timing-derivative vs between-sample, each channel read as
        its worst error relative to its own reference (the class for
        position and between-sample, the solver gates for the
        derivative rows) -- which demand dominates.
  - D3  DEMAND-DENSITY DIAGNOSIS: the row that separates "family
        cannot do the task" from "demand density exceeds synthesis
        capacity", readable as the eight-bar trigger's evidence
        input; a density finding is NOT a demonstrated out-of-class
        finding and fires nothing by itself (the trigger's input (i)
        reads NOT FIRED from this digest unless shape
        reachability is demonstrated, which density data cannot).
  - AT-CAPACITY CONTROL (N = 4): the recorded example program with
        four pinned phases; the solver's qualified flag is the
        feasibility witness -- the derivation check's deferred
        capacity claim machine-verified, never asserted.
  - N+1 CONTROL (5 pinned points): the example program with a fifth
        pin moved by the declared offset; the first-point-beyond-
        capacity behavior recorded, never a gate.
  - INTERVAL CHANNEL: the between-points contour deviation on an 8x
        refinement grid (96 crank phases) via the documented chain,
        against the declared analytic contour: SAMPLED, NEVER
        CERTIFIED; an undefined assembly anywhere on the refinement
        grid is an ERROR row, never a quiet pass.
  - COST: objective evaluations counted TWICE (the analytic grade
        and the data-generation cost), supplier-version-scoped to
        the recorded engine; the freeze declares which number feeds
        which.
  - Frozen predictions P1-P4 with grading rules, graded at the run.

Controls (the script's own): pure stdlib; ASCII only; read-only
consumption of the task, example and result files; fail-closed
corpus emitter (schema 1.1, units block + provenance on every row,
unknown-kind refusal); double-run determinism (in-process IDENTICAL
check); the instrument-modification count row (expected 0 -- the
solver and its emission are consumed unmodified; this script is new
job-local instrumentation, the additive convention).

Physical frames, declared honestly: the demand task's normalization
is the ellipse loop's own 260 x 90 mm bounding-box diagonal (one
unit = 275.136... mm, computed here from the semiaxes, never
transcribed); the control tasks ride the recorded example's own
normalization (no mm mapping recorded -- their tolerances are the
solver's own gates; the demand-class tolerance is reported as data
only). The two bases are declared per row; never mix without
re-declaring.

Pure stdlib; ASCII only; deterministic. Usage (repo root, after the
nine-seed run):

  python jobs/case-d-digest-01/case_d_digest_run.py \
    --demand jobs/case-d-digest-01/demand_ellipse_7pin.motion.json \
    --control-a jobs/case-d-digest-01/control_a_capacity4.motion.json \
    --control-b jobs/case-d-digest-01/control_b_moved5th.motion.json \
    --example experimental/motion/examples/normalized-motion.json \
    --result demand=runs/case-d-digest-01/demand_ellipse_7pin-580000050.json \
    --result demand=runs/case-d-digest-01/demand_ellipse_7pin-580000051.json \
    --result demand=runs/case-d-digest-01/demand_ellipse_7pin-580000052.json \
    --result control_a=runs/case-d-digest-01/control_a_capacity4-580000050.json \
    --result control_a=runs/case-d-digest-01/control_a_capacity4-580000051.json \
    --result control_a=runs/case-d-digest-01/control_a_capacity4-580000052.json \
    --result control_b=runs/case-d-digest-01/control_b_moved5th-580000050.json \
    --result control_b=runs/case-d-digest-01/control_b_moved5th-580000051.json \
    --result control_b=runs/case-d-digest-01/control_b_moved5th-580000052.json \
    --source-commit <40-hex-sha>
"""

import hashlib
import json
import math
import os
import sys

JOB_ID = "case-d-digest-01"
CORPUS_SCHEMA_VERSION = "1.1"
CORPUS_MAJOR = "1"

# ---- the frozen demand (the D brief freeze + the derivation check) ----
# The path class: a closed ellipse loop, semiaxes 130 x 45 mm -- the
# case-B layout family's 260 x 90 mm bounding box, the recorded
# 0.10 mm-class packaging tolerance; declared distinct from case B's
# carry-with-stops and case C's swing.
ELLIPSE_A_X_MM = 130.0
ELLIPSE_A_Y_MM = 45.0
BBOX_X_SPAN_MM = 260.0
BBOX_Y_SPAN_MM = 90.0
TOL_CLASS_MM = 0.10

# The count rule's output (derivation check, merged PR #104):
# N = 4 (floor(9/2) timed points), k = 3 -> 7 pinned phases.
CAPACITY_N = 4
MARGIN_K = 3
DEMAND_PHASES = (0, 2, 3, 5, 7, 9, 10)
DEMAND_BRANCHES = (1.0, 1.0)
CONTROL_A_PHASES = (0, 3, 6, 9)          # N = 4 pinned phases
CONTROL_B_MOVED_PHASE = 1               # the N+1 = 5th pin
CONTROL_B_OFFSET = (0.05, 0.0)          # pre-move frame, normalized

# Zero declared derivative windows (W_v = W_a = 0): the effective
# capacity stays floor((9 - 0 - 0)/2) = 4; the row the brief requires
# the demand declaration to carry.
W_V = 0
W_A = 0

# The between-points channel: 8x the native grid, SAMPLED, NEVER
# CERTIFIED (frozen at the brief).
INTERVAL_REFINEMENT = 8
INTERVAL_GRID = 12 * INTERVAL_REFINEMENT  # 96 crank phases

# The recorded engine and the frozen seed set.
SOLVER_VERSION = "six-bar motion engine v0.1.0a11 (SIX-BAR-NOW)"
SEEDS = (580000050, 580000051, 580000052)

# The solver's own qualification gates (continuation.py LIMITS,
# consumed read-only as context; the digest never re-gates them;
# the fairness gate's acceptance rule IS this qualification).
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

# Tolerances (fail-closed).
EPS_GEOM = 1e-12          # mirrors simulation.circle's own thresholds
EPS_EDGES = 1e-9          # edge-length self-consistency of the chain
EPS_PHASES = 1e-9          # phases vs the uniform grid
EPS_PIN = 1e-12           # analytic program reproduction in the tasks
EPS_SIMILARITY = 1e-12    # control B's similarity-transform residuals
EPS_MAP = 1e-6            # mm; frame-mapping reproduction checks
EPS_EMISSION = 1e-4       # kinematics cross-check vs the emission
                         # (independent implementations; the torch
                         # path clamps near-degenerate sqrt at 1e-10,
                         # so a generous-but-meaningful tolerance: a
                         # re-implementation bug shows at 1e-3+)

OUTPUT_DIR = os.path.join("runs", JOB_ID)
CORPUS_STEM = "case_d_digest_v1"


# ---------------------------------------------------------------------------
# Small vector helpers (pure stdlib).
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


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


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


# ---------------------------------------------------------------------------
# The demand program (analytic, recomputed here, never transcribed).
# ---------------------------------------------------------------------------

def frame_scale_mm():
    """One normalized unit of the demand task = the 260 x 90 mm
    bounding-box diagonal (computed from the declared semiaxes)."""
    return math.hypot(BBOX_X_SPAN_MM, BBOX_Y_SPAN_MM)


def tol_class_normalized():
    """The 0.10 mm class in the demand task's normalized units."""
    return TOL_CLASS_MM / frame_scale_mm()


def demand_q(theta):
    """The declared contour point (normalized) at crank phase
    theta: the ellipse (130 cos, 45 sin) mm over the frame scale."""
    s = frame_scale_mm()
    return (ELLIPSE_A_X_MM * math.cos(theta) / s,
            ELLIPSE_A_Y_MM * math.sin(theta) / s)


def demand_phi(theta):
    """The declared tool orientation (rad, data -- not pinned): the
    contour tangent, direction of travel."""
    return math.atan2(ELLIPSE_A_Y_MM * math.cos(theta),
                      -ELLIPSE_A_X_MM * math.sin(theta))


def demand_v(theta):
    s = frame_scale_mm()
    return (-ELLIPSE_A_X_MM * math.sin(theta) / s,
            ELLIPSE_A_Y_MM * math.cos(theta) / s)


def demand_a(theta):
    s = frame_scale_mm()
    return (-ELLIPSE_A_X_MM * math.cos(theta) / s,
            -ELLIPSE_A_Y_MM * math.sin(theta) / s)


def demand_omega(theta):
    """d phi / d theta (rad per crank rad), analytic."""
    sn, cs = math.sin(theta), math.cos(theta)
    return 5850.0 / (16900.0 * sn * sn + 2025.0 * cs * cs)


def demand_alpha(theta):
    """d omega / d theta (rad per crank rad squared), analytic."""
    sn, cs = math.sin(theta), math.cos(theta)
    f = 16900.0 * sn * sn + 2025.0 * cs * cs
    return -5850.0 * 29750.0 * sn * cs / (f * f)


# ---------------------------------------------------------------------------
# Corpus emission (schema 1.1, additive; job-local emitter following
# the shared conventions: units block + provenance on every row, JSON
# Lines primary + flat CSV projection, fail-closed on unknown kinds
# or missing blocks).
# ---------------------------------------------------------------------------

UNITS_BLOCK = {
    "position": "normalized task units (per-row basis field)",
    "position_basis": "two task bases ride this corpus: the demand"
                      " task (one unit = the 260 x 90 mm bounding-box"
                      " diagonal of the declared ellipse loop; the"
                      " frame_mapping row carries the computed mm"
                      " scale) and the example-family controls (one"
                      " unit = the recorded example's own bounding-box"
                      " diagonal; no mm mapping recorded); every row's"
                      " basis field says which; never mix the bases"
                      " without re-declaring this block",
    "angle": "deg",
}

KNOWN_KINDS = {
    "demand", "design_parameter", "frame_mapping", "gate",
    "seed_summary", "per_sample", "interval_channel", "control_row",
    "cost", "prediction", "scorecard_verdict", "reciprocity",
    "changelog",
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
            "design": "case study D failure digest (three staged"
                      " motion tasks x three seeds, the recorded"
                      " solver's own emission consumed read-only)",
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
    first = hashlib.sha256(lines[0].encode("ascii")).hexdigest()
    return jsonl_path, csv_path, h1, h2, first


# ---------------------------------------------------------------------------
# Input validation (fail-closed).
# ---------------------------------------------------------------------------

def die(message):
    print("case_d_digest_run: FAIL-CLOSED: %s" % message,
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


def s0_task(task, path, expect_branches):
    """The validator's own rules (engine.validate + targets.py),
    re-applied fail-closed, plus the task's declared branch pin."""
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
    if (br[0], br[1]) != expect_branches:
        die("%s: branches must equal the declared pin (%.1f, %.1f)"
            % (path, expect_branches[0], expect_branches[1]))
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
    return {"centroid_residual": centroid_res,
            "diagonal_residual": diag_res}


def demand_program_check(task, path):
    """The staged demand artifact must reproduce the declared
    analytic program exactly (all twelve phases, q/v/a columns;
    recomputed here, never transcribed)."""
    for i in range(12):
        th = i * 2.0 * math.pi / 12.0
        qx, qy = demand_q(th)
        vx, vy = demand_v(th)
        ax, ay = demand_a(th)
        row = task["q"][i]
        res = max(abs(row[0] - qx), abs(row[1] - qy),
                  abs(wrap(row[2] - demand_phi(th))))
        if res > EPS_PIN:
            die("%s: demand program row %d violates the analytic"
                " contour pin (residual %.3e)" % (path, i, res))
        row = task["v"][i]
        res = max(abs(row[0] - vx), abs(row[1] - vy),
                  abs(row[2] - demand_omega(th)))
        if res > EPS_PIN:
            die("%s: demand program row %d violates the analytic"
                " velocity pin (residual %.3e)" % (path, i, res))
        row = task["a"][i]
        res = max(abs(row[0] - ax), abs(row[1] - ay),
                  abs(row[2] - demand_alpha(th)))
        if res > EPS_PIN:
            die("%s: demand program row %d violates the analytic"
                " acceleration pin (residual %.3e)" % (path, i, res))
    return {"phases_checked": 12}


def demand_frame_check(task):
    """The mm frame, derived and fail-closed: each pinned phase's
    normalized position times the computed scale must reproduce the
    exact mm ellipse point; every sample inside the recorded
    bounding box."""
    s = frame_scale_mm()
    for p in DEMAND_PHASES:
        th = p * 2.0 * math.pi / 12.0
        mmx = task["q"][p][0] * s
        mmy = task["q"][p][1] * s
        ex = ELLIPSE_A_X_MM * math.cos(th)
        ey = ELLIPSE_A_Y_MM * math.sin(th)
        if abs(mmx - ex) > EPS_MAP or abs(mmy - ey) > EPS_MAP:
            die("frame mapping: demand phase %d reproduces"
                " (%.6f, %.6f) mm, expected (%.6f, %.6f)"
                % (p, mmx, mmy, ex, ey))
    for i, row in enumerate(task["q"]):
        mmx = row[0] * s
        mmy = row[1] * s
        if not (-ELLIPSE_A_X_MM - EPS_MAP <= mmx
                <= ELLIPSE_A_X_MM + EPS_MAP
                and -ELLIPSE_A_Y_MM - EPS_MAP <= mmy
                <= ELLIPSE_A_Y_MM + EPS_MAP):
            die("frame mapping: demand sample %d maps outside the"
                " recorded bounding box: (%.6f, %.6f) mm"
                % (i, mmx, mmy))
    return {"scale_mm": s}


def control_a_check(control_a, example, path):
    """Control A must be the recorded example program VERBATIM
    (parsed-content equality; the byte-identical staging is the
    JOB's record, this pin is the semantic one)."""
    if control_a != example:
        die("%s: control A must equal the recorded example program"
            " (parsed-content equality)" % path)
    return {"verbatim": True}


def control_b_check(control_b, control_a, path):
    """Control B must be the example program with the fifth pin
    moved by the declared offset, re-centered and re-normalized;
    verified by the similarity-transform invariants (fp-safe), and
    the actual post-normalization offset is recorded honestly."""
    qa = control_a["q"]
    qb = control_b["q"]
    moved = CONTROL_B_MOVED_PHASE
    off = CONTROL_B_OFFSET
    qmod = [list(p) for p in qa]
    qmod[moved][0] += off[0]
    qmod[moved][1] += off[1]
    cx = sum(p[0] for p in qmod) / 12.0
    cy = sum(p[1] for p in qmod) / 12.0
    xs = [p[0] - cx for p in qmod]
    ys = [p[1] - cy for p in qmod]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    resid = 0.0
    for i in range(12):
        for k in range(2):
            expect = (qmod[i][k] - (cx if k == 0 else cy)) / diag
            resid = max(resid, abs(qb[i][k] - expect))
    if resid > EPS_SIMILARITY:
        die("%s: control B violates the moved-pin similarity"
            " transform (residual %.3e)" % (path, resid))
    dresid = 0.0
    for name, src in (("v", control_a["v"]), ("a", control_a["a"])):
        for i in range(12):
            for k in range(3):
                if k < 2:
                    expect = src[i][k] / diag
                else:
                    expect = src[i][k]
                dresid = max(dresid,
                             abs(control_b[name][i][k] - expect))
    if dresid > EPS_SIMILARITY:
        die("%s: control B violates the derivative scaling"
            " invariant (residual %.3e)" % (path, dresid))
    # the actual post-normalization offset of the moved pin
    ox = (qa[moved][0] - cx) / diag
    oy = (qa[moved][1] - cy) / diag
    actual = math.hypot(qb[moved][0] - ox, qb[moved][1] - oy)
    return {"transform_residual": resid,
            "derivative_residual": dresid,
            "scale": 1.0 / diag,
            "centroid": (cx, cy),
            "actual_offset": actual}


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


TASK_LABELS = ("demand", "control_a", "control_b")


def load_group(results, label):
    group = [r for r in results if r["label"] == label]
    seeds = [r["info"]["seed"] for r in group]
    if sorted(seeds) != list(SEEDS):
        die("label %s must carry exactly the frozen seed set"
            " %s (got %s)" % (label, list(SEEDS), sorted(seeds)))
    if len(set(seeds)) != len(seeds):
        die("duplicate seed under label %s" % label)
    return {r["info"]["seed"]: r for r in group}


P1_TEXT = ("the demand task's seven pinned phases are not all met"
           " at the 0.10 mm class on any seed (the expected"
           " honest-failure shape: the demand sits three points"
           " beyond the derived capacity N = 4; recorded, never a"
           " gate)")
P1_RULE = ("CONFIRMED if no seed meets all seven pins at the class;"
           " REFUTED if at least one seed meets all seven;"
           " INCONCLUSIVE if every seed is ERROR-only")
P2_TEXT = ("control A (the recorded example program, four pinned"
           " phases = N) qualifies on all three seeds: the recorded"
           " feasibility witness reproduces and the derivation"
           " check's deferred at-capacity claim is machine-verified")
P2_RULE = ("CONFIRMED if the qualified flag is true on 3/3 seeds,"
           " else REFUTED")
P3_TEXT = ("control B (the example program with a fifth pin moved"
           " by the declared offset, N + 1 = 5 pinned points) shows"
           " elevated residual at the moved pin or fails to qualify,"
           " on at least two of the three seeds -- the"
           " first-point-beyond-capacity behavior recorded, never a"
           " gate")
P3_RULE = ("per seed: fired if not qualified or the moved-pin"
           " residual exceeds every unmoved-pin residual;"
           " CONFIRMED if fired on >= 2 seeds, else REFUTED")
P4_TEXT = ("the demand task's binding channel (D2) reads"
           " position-at-pins, not timing-derivative and not"
           " between-sample, on a majority of seeds (zero"
           " derivative windows declared; the density sits at the"
           " pins)")
P4_RULE = ("CONFIRMED if the D2 binding channel is position_pins on"
           " >= 2 of 3 seeds; REFUTED otherwise; INCONCLUSIVE if"
           " fewer than two seeds are gradable")


def compute(tasks, results, source_commit):
    rows = []
    report = []
    r = report.append

    tol_class = tol_class_normalized()
    scale_mm = frame_scale_mm()

    s0 = {}
    for label, path in (("demand", "demand"), ("control_a", "control-a"),
                        ("control_b", "control-b")):
        s0[label] = s0_task(
            tasks[label], "<%s>" % path,
            (1.0, 1.0) if label == "demand" else (-1.0, 1.0))
    demand_program_check(tasks["demand"], "<demand>")
    frame = demand_frame_check(tasks["demand"])
    control_a_check(tasks["control_a"], tasks["example"],
                    "<control-a>")
    cb_info = control_b_check(tasks["control_b"], tasks["control_a"],
                              "<control-b>")

    groups = {label: load_group(results, label)
              for label in TASK_LABELS}

    r("case-d-digest-01 -- the failure-digest instrument"
      " (deterministic, pure stdlib)")
    r("python: %s" % sys.version.split()[0])
    r("source commit: %s" % source_commit)
    r("engine: %s; fairness gate: the engine's own frozen chooser +"
      " restart protocol, 200-evaluation cap, acceptance = strict"
      " qualification; seeds %s; per-seed reporting; no pooling"
      % (SOLVER_VERSION, "/".join(str(s) for s in SEEDS)))
    r("demand task: the declared ellipse loop (semiaxes 130 x 45 mm,"
      " the 260 x 90 mm case-B bounding box), 7 = N + k pinned"
      " phases (N = 4, k = 3), W_v = W_a = 0 declared derivative"
      " windows -> effective capacity 4; branches (+1, +1)")
    r("  s0 re-check: centroid residual %.3e, diagonal residual"
      " %.3e; analytic program pins reproduced at all twelve phases"
      % (s0["demand"]["centroid_residual"],
         s0["demand"]["diagonal_residual"]))
    r("  frame mapping: 1 normalized unit = %.6f mm (computed from"
      " the declared semiaxes); pinned phases reproduce the exact"
      " mm ellipse points; all samples inside the recorded bounding"
      " box" % scale_mm)
    r("  0.10 mm class in normalized units: %.6e (computed, never"
      " transcribed)" % tol_class)
    r("control A: the recorded example program VERBATIM"
      " (parsed-content equality pinned); 4 pinned phases (0/3/6/9)"
      " = N")
    r("control B: the example program with the fifth pin (phase 1)"
      " moved by the declared offset (0.05, 0.0), re-centered and"
      " re-normalized; similarity residual %.3e, derivative"
      " residual %.3e; actual post-normalization offset %.17g"
      % (cb_info["transform_residual"],
         cb_info["derivative_residual"],
         cb_info["actual_offset"]))
    r("results: %d file(s) (%d per task)" % (len(results),
                                             len(results) // 3))
    r("")

    # ---- shared rows -------------------------------------------------
    for p in DEMAND_PHASES:
        th = p * 2.0 * math.pi / 12.0
        qx, qy = demand_q(th)
        rows.append(base_row(
            "demand", source_commit, task="demand",
            basis="demand_ellipse", phase=p,
            x_mm=qx * scale_mm, y_mm=qy * scale_mm,
            phase_rad=th, tolerance_pos_mm=TOL_CLASS_MM,
            channel="position pin at a pinned crank phase"
                    " (timing pin; time is a spec unit)"))
    for p in CONTROL_A_PHASES:
        rows.append(base_row(
            "demand", source_commit, task="control_a",
            basis="example_family", phase=p,
            x_norm=tasks["control_a"]["q"][p][0],
            y_norm=tasks["control_a"]["q"][p][1],
            phase_rad=p * 2.0 * math.pi / 12.0,
            tolerance_pos_units=SOLVER_LIMITS["position"],
            channel="at-capacity position pin (N = 4)"))
    for p in CONTROL_A_PHASES:
        rows.append(base_row(
            "demand", source_commit, task="control_b",
            basis="example_family", phase=p,
            x_norm=tasks["control_b"]["q"][p][0],
            y_norm=tasks["control_b"]["q"][p][1],
            phase_rad=p * 2.0 * math.pi / 12.0,
            tolerance_pos_units=SOLVER_LIMITS["position"],
            channel="n-plus-1 position pin (unmoved)"))
    mp = CONTROL_B_MOVED_PHASE
    rows.append(base_row(
        "demand", source_commit, task="control_b",
        basis="example_family", phase=mp,
        x_norm=tasks["control_b"]["q"][mp][0],
        y_norm=tasks["control_b"]["q"][mp][1],
        phase_rad=mp * 2.0 * math.pi / 12.0,
        tolerance_pos_units=SOLVER_LIMITS["position"],
        channel="n-plus-1 position pin (moved by the declared"
                " offset (0.05, 0.0) pre-move, re-centered,"
                " re-normalized)"))
    rows.append(base_row(
        "design_parameter", source_commit,
        name="fairness_gate_search_config",
        value="the engine's own frozen chooser + restart search"
              " protocol, consumed unmodified; objective-evaluation"
              " cap 200; acceptance = strict qualification (the"
              " solver's own gates, the emission's qualified flag)",
        reason="the brief's fairness gate: the digest's search"
               " configuration IS the analytic baseline; the"
               " engine's own committed protocol is the strongest"
               " reasonable configuration available without"
               " modifying the pinned solver -- raising the cap or"
               " altering the acceptance rule would be a supplier"
               " change (mod count 0 forbids it); any later"
               " warm-start comparison runs THIS configuration"
               " with only the initialization changed"))
    rows.append(base_row(
        "design_parameter", source_commit, name="seed_policy",
        value="seeds 580000050/51/52; per-seed reporting; no"
              " pooling",
        reason="the standing set, carried from the freeze"))
    rows.append(base_row(
        "design_parameter", source_commit, name="demand_derivation",
        value="N = 4 (floor(9/2) timed points); k = 3; count = 7"
              " pinned phases (0/2/3/5/7/9/10); W_v = W_a = 0"
              " declared derivative windows -> effective capacity"
              " floor((9 - 0 - 0)/2) = 4",
        reason="the merged derivation check (PR #104); the count"
               " rule's output, never a picked range"))
    rows.append(base_row(
        "design_parameter", source_commit, name="cost_currency",
        value="objective evaluations (oracle calls), the recorded"
              " 207.5/22.0 accounting class; counted TWICE -- the"
              " analytic grade (the demand task's three runs) and"
              " the data-generation cost (all nine runs) --"
              " supplier-version-scoped to %s" % SOLVER_VERSION,
        reason="the operative cost clause travels with the verdict:"
               " the per-demand cost is real, nonzero and measured"
               " in the pinned currency; the analytic-grade number"
               " feeds the supplier baseline (the pre-committed"
               " warm-start comparison), the data-generation number"
               " feeds the corpus budget accounting"))
    rows.append(base_row(
        "design_parameter", source_commit, name="interval_refinement",
        value="%dx the native grid = %d crank phases; SAMPLED,"
              " NEVER CERTIFIED" % (INTERVAL_REFINEMENT,
                                    INTERVAL_GRID),
        reason="the freeze's between-points channel, declared before"
               " the run so the channel's worst-case reading is not"
               " an artifact of where the refinement happened to"
               " land"))
    rows.append(base_row(
        "design_parameter", source_commit, name="demand_branches",
        value="(+1, +1)",
        reason="a discrete assembly-configuration selector declared"
               " once at staging (carried at zero in the"
               " derivation's count); no recorded evidence prefers"
               " a sign pair; declared, never re-drawn"))
    rows.append(base_row(
        "frame_mapping", source_commit, task="demand",
        basis="demand_ellipse", scale_mm=scale_mm,
        method="derived: the demand task's normalization is the"
               " declared ellipse loop's own 260 x 90 mm"
               " bounding-box diagonal; fail-closed checks"
               " reproduce the exact mm ellipse points at every"
               " pinned phase and keep all samples inside the"
               " recorded bounding box"))
    rows.append(base_row(
        "gate", source_commit, name="s0_task_contract",
        verdict="PASS",
        window_rule="the validator's own rules re-applied"
                    " fail-closed on all three tasks (five fields,"
                    " uniform grid, branches pinned per task, 12x3"
                    " finite, centroid, unit diagonal) plus the"
                    " demand program's analytic pins, control A's"
                    " verbatim pin and control B's similarity"
                    " transform"))
    rows.append(base_row(
        "gate", source_commit, name="control_a_provenance",
        verdict="PASS",
        window_rule="control A equals the recorded example program"
                    " (experimental/motion/examples/"
                    "normalized-motion.json) by parsed-content"
                    " equality"))
    rows.append(base_row(
        "gate", source_commit, name="control_b_derivation",
        verdict="PASS",
        window_rule="control B reproduces the example program with"
                    " the fifth pin moved by the declared offset,"
                    " re-centered and re-normalized (similarity"
                    " residual %.3e; actual post-normalization"
                    " offset %.17g)" % (cb_info["transform_residual"],
                                        cb_info["actual_offset"])))
    r("[S0] TASK-CONTRACT RE-CHECK: PASS on all three tasks (the"
      " validator's own rules, re-applied; the runs already proved"
      " acceptance)")
    r("  control A pinned verbatim to the recorded example; control"
      " B pinned by the similarity transform (actual offset %.17g,"
      " scale %.17g)" % (cb_info["actual_offset"], cb_info["scale"]))
    r("")

    # ---- per (task, seed) grading ------------------------------------
    demand_state = {}
    control_a_state = {}
    control_b_state = {}
    cost_rows = []

    for label in TASK_LABELS:
        for seed in SEEDS:
            res = groups[label][seed]
            obj = res["obj"]
            m = obj["mechanism_normalized"]
            ps = obj["per_sample"]
            met = obj["selected"]["metrics"]
            basis = "demand_ellipse" if label == "demand" \
                else "example_family"
            r("[%s | seed %d] (%s)" % (label, seed, res["path"]))

            # -- kinematics cross-check vs the emission ---------------
            xchk_max_pos = 0.0
            xchk_max_ori = 0.0
            emission_none = []
            undefined = None
            try:
                for p in range(12):
                    theta = 2.0 * math.pi * p / 12.0
                    s = simulate6(m, theta)
                    bad = check_edges(m, s)
                    if bad > EPS_EDGES:
                        die("%s seed %d: edge-length self-check"
                            " %.3e exceeds %.1e at phase %d"
                            % (label, seed, bad, EPS_EDGES, p))
                    if label == "demand":
                        err_pos = vnorm(vsub(s["P"], demand_q(theta)))
                        err_ori = math.degrees(abs(
                            wrap(s["angle"] - demand_phi(theta))))
                    else:
                        tq = tasks[label]["q"][p]
                        err_pos = vnorm(vsub(s["P"], (tq[0], tq[1])))
                        err_ori = math.degrees(abs(
                            wrap(s["angle"] - tq[2])))
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
                        die("%s seed %d: kinematics cross-check"
                            " disagrees with the emission at phase"
                            " %d (position %.3e vs %.3e, orientation"
                            " %.3e vs %.3e)"
                            % (label, seed, p, err_pos, em_pos,
                               err_ori, em_ori))
            except ValueError as exc:
                undefined = exc
            if emission_none:
                r("  kinematics cross-check vs the emission:"
                  " emission carries None at phase(s) %s (the"
                  " tool's own non-finite convention) -- recorded"
                  " as data"
                  % ", ".join(str(p) for p in emission_none))

            if undefined is not None:
                r("  UNDEFINED ASSEMBLY at a native phase (%s): the"
                  " grading fails closed for this seed (never a"
                  " quiet pass)" % undefined)
                rows.append(base_row(
                    "scorecard_verdict", source_commit, task=label,
                    basis=basis, seed=seed, item="GRADING",
                    verdict="ERROR",
                    text="undefined assembly at a native phase --"
                         " fail-closed, never a quiet pass"))
                if label == "demand":
                    demand_state[seed] = {"error": True}
                elif label == "control_a":
                    control_a_state[seed] = {"error": True}
                else:
                    control_b_state[seed] = {"error": True}
                continue

            xchk_ok = max(xchk_max_pos, xchk_max_ori) <= EPS_EMISSION
            r("  kinematics cross-check vs the emission: max"
              " position deviation %.3e, max orientation deviation"
              " %.3e deg -- %s"
              % (xchk_max_pos, xchk_max_ori,
                 "VERIFIED" if xchk_ok else "FAIL"))
            rows.append(base_row(
                "gate", source_commit, task=label, basis=basis,
                seed=seed, name="kinematics_vs_emission",
                verdict="PASS" if xchk_ok else "FAIL",
                max_pos_dev=xchk_max_pos, max_ori_dev=xchk_max_ori,
                window_rule="the documented chain re-implemented"
                            " read-only vs the per-sample emission"
                            " (independent implementations, %.1e"
                            " tolerance)" % EPS_EMISSION))

            chan_worst = {}
            for key in SAMPLE_KEYS:
                wv, wi = worst_of(ps[key])
                chan_worst[key] = (wv, wi)
            all_pos, all_pos_i = worst_of(ps["position"])
            all_ori, all_ori_i = worst_of(ps["orientation"])

            rows.append(base_row(
                "seed_summary", source_commit, task=label,
                basis=basis, seed=seed,
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
                    "angular_acceleration"][0]))
            for p in range(12):
                row_fields = {"task": label, "basis": basis,
                              "seed": seed, "phase": p}
                for key in SAMPLE_KEYS:
                    row_fields[key] = ps[key][p]
                rows.append(base_row("per_sample", source_commit,
                                     **row_fields))
            cost_rows.append(base_row(
                "cost", source_commit, task=label, basis=basis,
                seed=seed,
                scope="per_run",
                objective_evaluations=obj["objective_evaluations"],
                supplier_version=SOLVER_VERSION))

            r("  solver: qualified %s, %d/200 evaluations,"
              " initializer %s, issues %d"
              % (obj["qualified"], obj["objective_evaluations"],
                 obj["selected_label"] or "original",
                 len(obj["issues"])))
            r("  per-channel worst (emission): position %s (phase"
              " %s) | orientation %s deg (phase %s) | spatial v %s"
              " | spatial a %s | angular v %s | angular a %s"
              % (fmt(chan_worst["position"][0]),
                 fmt(chan_worst["position"][1], 0),
                 fmt(chan_worst["orientation"][0]),
                 fmt(chan_worst["orientation"][1], 0),
                 fmt(chan_worst["spatial_velocity"][0]),
                 fmt(chan_worst["spatial_acceleration"][0]),
                 fmt(chan_worst["angular_velocity"][0]),
                 fmt(chan_worst["angular_acceleration"][0])))

            if label == "demand":
                # -- D1: pins at the 0.10 mm class --------------------
                pin_vals = [ps["position"][p] for p in DEMAND_PHASES]
                pin_worst, pin_worst_p = worst_of(pin_vals)
                none_pins = [DEMAND_PHASES[i] for i, v
                             in enumerate(pin_vals) if v is None]
                pins_ok = (pin_worst is not None
                           and pin_worst <= tol_class)
                r("  D1 pins: worst %s (phase %s) vs class %.6e"
                  " (%.2f mm) -> %s"
                  % (fmt(pin_worst), fmt(pin_worst_p, 0), tol_class,
                     TOL_CLASS_MM, "PASS" if pins_ok else "FAIL"))
                if none_pins:
                    r("    emission carries None at pinned phase(s)"
                      " %s -- recorded as data"
                      % ", ".join(str(p) for p in none_pins))

                # -- the interval channel (8x refinement) -------------
                interval_worst = None
                interval_worst_th = None
                interval_ori_worst = None
                interval_error = None
                try:
                    for k in range(INTERVAL_GRID):
                        th = 2.0 * math.pi * k / INTERVAL_GRID
                        s = simulate6(m, th)
                        ex, ey = demand_q(th)
                        dev = vnorm(vsub(s["P"], (ex, ey)))
                        if interval_worst is None or \
                                dev > interval_worst:
                            interval_worst = dev
                            interval_worst_th = th
                        odev = math.degrees(abs(
                            wrap(s["angle"] - demand_phi(th))))
                        if interval_ori_worst is None or \
                                odev > interval_ori_worst:
                            interval_ori_worst = odev
                except ValueError as exc:
                    interval_error = exc
                if interval_error is not None:
                    r("  INTERVAL CHANNEL: UNDEFINED ASSEMBLY on the"
                      " refinement grid (%s) -- ERROR row, never a"
                      " quiet pass; SAMPLED, NEVER CERTIFIED"
                      % interval_error)
                    rows.append(base_row(
                        "interval_channel", source_commit, seed=seed,
                        basis="demand_ellipse",
                        verdict="ERROR",
                        refinement=INTERVAL_REFINEMENT,
                        grid=INTERVAL_GRID,
                        window_rule="undefined assembly on the"
                                    " refinement grid -- fail-closed"
                                    " (sampled, never certified)"))
                    interval_ok = False
                else:
                    interval_ok = (interval_worst is not None
                                   and interval_worst <= tol_class)
                    r("  INTERVAL CHANNEL (%dx grid, %d samples):"
                      " worst deviation %s (phase %.2f rad) vs class"
                      " %.6e -> %s | worst orientation deviation"
                      " %s deg (data, not pinned) | SAMPLED, NEVER"
                      " CERTIFIED"
                      % (INTERVAL_REFINEMENT, INTERVAL_GRID,
                         fmt(interval_worst), interval_worst_th,
                         tol_class, "PASS" if interval_ok else "FAIL",
                         fmt(interval_ori_worst)))
                    rows.append(base_row(
                        "interval_channel", source_commit, seed=seed,
                        basis="demand_ellipse",
                        verdict="PASS" if interval_ok else "FAIL",
                        refinement=INTERVAL_REFINEMENT,
                        grid=INTERVAL_GRID,
                        worst_deviation=interval_worst,
                        worst_phase_rad=interval_worst_th,
                        worst_orientation_deviation_deg=\
                            interval_ori_worst,
                        window_rule="max deviation of the candidate"
                                    " tool point vs the declared"
                                    " analytic contour over the 8x"
                                    " refinement grid (96 crank"
                                    " phases); SAMPLED, NEVER"
                                    " CERTIFIED; graded at the same"
                                    " 0.10 mm class"))

                d1_ok = bool(obj["qualified"]) and pins_ok \
                    and interval_ok
                rows.append(base_row(
                    "gate", source_commit, task="demand", seed=seed,
                    basis="demand_ellipse", name="d1_pool_capability",
                    verdict="PASS" if d1_ok else "FAIL",
                    value_units=pin_worst, limit_units=tol_class,
                    interval_worst=interval_worst,
                    window_rule="graded against ALL declared demands:"
                                " the 7 pinned phases at the 0.10 mm"
                                " class, the between-points contour"
                                " channel at the same class, and the"
                                " program channels under the"
                                " solver's strict qualification;"
                                " honest failure is a recorded"
                                " outcome, never a gate"))
                r("  D1 POOL CAPABILITY: qualified %s, pins %s,"
                  " interval %s -> %s (honest failure recorded,"
                  " never a gate)"
                  % (obj["qualified"],
                     "PASS" if pins_ok else "FAIL",
                     "PASS" if interval_ok else "FAIL",
                     "PASS" if d1_ok else "FAIL"))

                # -- D2: binding-channel classification ---------------
                ratios = {}
                if pin_worst is not None:
                    ratios["position_pins"] = pin_worst / tol_class
                if interval_worst is not None:
                    ratios["between_sample"] = \
                        interval_worst / tol_class
                deriv = []
                for key in ("spatial_velocity", "spatial_acceleration",
                            "angular_velocity", "angular_acceleration"):
                    wv = chan_worst[key][0]
                    if wv is not None:
                        deriv.append(wv / SOLVER_LIMITS[key])
                if deriv:
                    ratios["timing_derivative"] = max(deriv)
                binding = None
                if ratios:
                    binding = max(sorted(ratios), key=lambda k: ratios[k])
                rows.append(base_row(
                    "scorecard_verdict", source_commit, task="demand",
                    basis="demand_ellipse", seed=seed, item="D2",
                    verdict=binding if binding else "ERROR",
                    ratios=json.dumps(ratios, sort_keys=True),
                    worst_orientation_deg=all_ori,
                    text="binding-channel classification: each"
                         " channel read as its worst error relative"
                         " to its own reference (the 0.10 mm class"
                         " for position and between-sample, the"
                         " solver gates for the derivative rows);"
                         " orientation carried as program data,"
                         " never a declared demand"))
                r("  D2 BINDING CHANNEL: %s (ratios: %s)"
                  % (binding, json.dumps(ratios, sort_keys=True)))

                demand_state[seed] = {
                    "error": False,
                    "qualified": bool(obj["qualified"]),
                    "pins_ok": pins_ok,
                    "pin_worst": pin_worst,
                    "interval_ok": interval_ok,
                    "interval_worst": interval_worst,
                    "binding": binding,
                    "d1_ok": d1_ok,
                }

            elif label == "control_a":
                # -- the at-capacity control row (N = 4) --------------
                pin_vals = [ps["position"][p]
                            for p in CONTROL_A_PHASES]
                pin_worst, pin_worst_p = worst_of(pin_vals)
                pins_ok = (pin_worst is not None
                           and pin_worst
                           <= SOLVER_LIMITS["position"])
                r("  CONTROL A (N = 4 pins): worst %s (phase %s)"
                  " vs the solver's own gate %.3g -> %s | qualified"
                  " %s | vs the demand class %.6e as DATA: %s"
                  % (fmt(pin_worst), fmt(pin_worst_p, 0),
                     SOLVER_LIMITS["position"],
                     "PASS" if pins_ok else "FAIL", obj["qualified"],
                     tol_class,
                     "met" if (pin_worst is not None
                              and pin_worst <= tol_class)
                     else "not met"))
                rows.append(base_row(
                    "control_row", source_commit, task="control_a",
                    basis="example_family", seed=seed,
                    name="at_capacity_N4",
                    qualified=obj["qualified"],
                    pins=CONTROL_A_PHASES,
                    worst_pin=pin_worst,
                    worst_pin_phase=pin_worst_p,
                    gate_units=SOLVER_LIMITS["position"],
                    verdict="PASS" if (obj["qualified"] and pins_ok)
                    else "FAIL",
                    worst_pin_vs_demand_class=pin_worst,
                    demand_class_units=tol_class,
                    window_rule="the at-capacity control row: N = 4"
                                " pinned phases on the recorded"
                                " example program; the solver's"
                                " qualified flag is the feasibility"
                                " witness -- the derivation check's"
                                " deferred capacity claim"
                                " machine-verified, never asserted;"
                                " the demand-class comparison is"
                                " data only (different basis, no"
                                " recorded mm mapping)"))
                control_a_state[seed] = {
                    "error": False,
                    "qualified": bool(obj["qualified"]),
                    "pins_ok": pins_ok,
                    "pin_worst": pin_worst,
                }
                r("  AT-CAPACITY CONTROL (N = 4): %s -- the capacity"
                  " claim is machine-verified for this seed"
                  % ("PASS (qualified; the deferred N = 4 claim"
                     " witnessed)"
                     if (obj["qualified"] and pins_ok) else "FAIL"))

            else:
                # -- the N+1 control row (5 pinned points) ------------
                unmoved_vals = [ps["position"][p]
                                for p in CONTROL_A_PHASES]
                unmoved_worst, _ = worst_of(unmoved_vals)
                moved_val = ps["position"][CONTROL_B_MOVED_PHASE]
                qualified = bool(obj["qualified"])
                moved_elevated = (
                    moved_val is not None and unmoved_worst is not None
                    and moved_val > unmoved_worst)
                r("  CONTROL B (N + 1 = 5 pins): moved-pin residual"
                  " %s vs unmoved worst %s -> %s | qualified %s"
                  % (fmt(moved_val), fmt(unmoved_worst),
                     "ELEVATED" if moved_elevated else "not elevated",
                     qualified))
                rows.append(base_row(
                    "control_row", source_commit, task="control_b",
                    basis="example_family", seed=seed,
                    name="n_plus_1_moved5th",
                    qualified=qualified,
                    unmoved_pins=CONTROL_A_PHASES,
                    moved_pin=CONTROL_B_MOVED_PHASE,
                    declared_offset=list(CONTROL_B_OFFSET),
                    actual_offset=cb_info["actual_offset"],
                    moved_pin_residual=moved_val,
                    unmoved_worst=unmoved_worst,
                    verdict="RECORDED",
                    fired=bool((not qualified) or moved_elevated),
                    window_rule="the N+1 recorded behavior, never a"
                                " gate: five pinned points (three"
                                " beyond the four the family covers"
                                " exactly on the derivation's count"
                                " -- the first beyond capacity is"
                                " the moved pin); elevated residual"
                                " at the moved pin or failure to"
                                " qualify is the expected shape"))
                control_b_state[seed] = {
                    "error": False,
                    "qualified": qualified,
                    "moved_val": moved_val,
                    "unmoved_worst": unmoved_worst,
                    "moved_elevated": moved_elevated,
                }
                r("  N+1 CONTROL (5 pins): RECORDED (never a gate)")
            r("")

    # ---- D3: the demand-density diagnosis (per seed) ------------------
    for seed in SEEDS:
        ds = demand_state[seed]
        ca = control_a_state[seed]
        cb = control_b_state[seed]
        if ds.get("error") or ca.get("error") or cb.get("error"):
            rows.append(base_row(
                "scorecard_verdict", source_commit, task="demand",
                basis="demand_ellipse", seed=seed, item="D3",
                verdict="ERROR",
                text="an ERROR row upstream (undefined assembly)"
                     " -- the density diagnosis is not gradable for"
                     " this seed, fail-closed"))
            r("[D3 | seed %d] ERROR (upstream undefined assembly)"
              % seed)
            continue
        pins_met = ds["pins_ok"]
        ca_q = ca["qualified"] and ca["pins_ok"]
        if ca_q and not pins_met:
            reading = ("DEMAND DENSITY EXCEEDS SYNTHESIS CAPACITY:"
                       " the family covers N = 4 pinned phases"
                       " exactly (control A qualified on this seed)"
                       " while the demand's 7 = N + k pins are not"
                       " all met at the class -- the density, not"
                       " the family, binds")
        elif ca_q and pins_met:
            reading = ("DENSITY NOT BINDING ON THIS SEED: the demand"
                       " pins are met at the class while control A"
                       " qualifies -- recorded as data, never a"
                       " gate; the count rule's arithmetic is"
                       " untouched by a search regime landing"
                       " in-band at 7 points")
        else:
            reading = ("CONTROL-ANOMALY: the at-capacity witness did"
                       " not qualify on this seed (control A"
                       " unqualified) -- the density reading is"
                       " undermined for this seed and recorded as"
                       " data, never a gate")
        trigger = ("the eight-bar trigger's input (i) reads NOT"
                   " FIRED from this digest: a density finding is"
                   " not a demonstrated out-of-class finding"
                   " (capacity is density, not shape"
                   " reachability); the trigger fires at the"
                   " capability step only on a demonstrated"
                   " out-of-class finding, never a near-miss;"
                   " trigger context (b)-shaped (the closed form"
                   " stops being exact/instant at this demand"
                   " density), (a) unfired and honest")
        rows.append(base_row(
            "scorecard_verdict", source_commit, task="demand",
            basis="demand_ellipse", seed=seed, item="D3",
            verdict="DENSITY" if (ca_q and not pins_met) else
                    ("DATA" if ca_q else "CONTROL-ANOMALY"),
            pins_beyond_capacity=MARGIN_K,
            text=reading + "; " + trigger))
        r("[D3 | seed %d] %s" % (seed, reading))
        r("  trigger input (i): NOT FIRED (density is not shape"
          " reachability); context (b)-shaped, (a) unfired")

    # ---- the cost accounting (counted twice) ---------------------------
    analytic_grade = sum(groups["demand"][s]["obj"]
                         ["objective_evaluations"] for s in SEEDS)
    data_generation = sum(
        groups[label][s]["obj"]["objective_evaluations"]
        for label in TASK_LABELS for s in SEEDS)
    for row in cost_rows:
        rows.append(row)
    rows.append(base_row(
        "cost", source_commit, scope="analytic_grade",
        supplier_version=SOLVER_VERSION,
        objective_evaluations=analytic_grade,
        feeds="the supplier baseline: the pre-committed warm-start"
              " comparison runs the SAME configuration with only"
              " the initialization changed -- this number is its"
              " analytic baseline"))
    rows.append(base_row(
        "cost", source_commit, scope="data_generation",
        supplier_version=SOLVER_VERSION,
        objective_evaluations=data_generation,
        feeds="the corpus budget accounting (all nine runs): in a"
              " no-ground-truth family the digest's finds are the"
              " training corpus's only honest source"))
    r("")
    r("[COST] analytic grade (the demand task's three runs): %d"
      " objective evaluations -- feeds the supplier baseline"
      % analytic_grade)
    r("[COST] data generation (all nine runs): %d objective"
      " evaluations -- feeds the corpus budget accounting"
      % data_generation)
    r("  counted TWICE, supplier-version-scoped to %s; the"
      " per-demand cost is real, nonzero and measured in the"
      " pinned oracle-call currency" % SOLVER_VERSION)

    # ---- the frozen predictions, graded --------------------------------
    def pred(pid, text, rule, verdict):
        rows.append(base_row(
            "prediction", source_commit, id=pid, frozen_text=text,
            grading_rule=rule, verdict=verdict))

    gradable = [s for s in SEEDS if not demand_state[s].get("error")]
    p1_verdict = "INCONCLUSIVE"
    if gradable:
        any_met = any(demand_state[s]["pins_ok"] for s in gradable)
        p1_verdict = "REFUTED" if any_met else "CONFIRMED"
    pred("P1", P1_TEXT, P1_RULE, p1_verdict)

    ca_ok_count = sum(1 for s in SEEDS
                      if not control_a_state[s].get("error")
                      and control_a_state[s]["qualified"]
                      and control_a_state[s]["pins_ok"])
    p2_verdict = "CONFIRMED" if ca_ok_count == 3 else "REFUTED"
    pred("P2", P2_TEXT, P2_RULE, p2_verdict)

    cb_fired = 0
    for s in SEEDS:
        cb = control_b_state[s]
        if cb.get("error"):
            continue
        if (not cb["qualified"]) or cb["moved_elevated"]:
            cb_fired += 1
    p3_verdict = "CONFIRMED" if cb_fired >= 2 else "REFUTED"
    pred("P3", P3_TEXT, P3_RULE, p3_verdict)

    pos_binding = sum(1 for s in gradable
                      if demand_state[s]["binding"]
                      == "position_pins")
    if len(gradable) < 2:
        p4_verdict = "INCONCLUSIVE"
    else:
        p4_verdict = "CONFIRMED" if pos_binding >= 2 else "REFUTED"
    pred("P4", P4_TEXT, P4_RULE, p4_verdict)

    r("")
    r("[PREDICTIONS] frozen before the run, graded at the run:")
    r("  P1 %s -- %s" % (p1_verdict, P1_TEXT))
    r("  P2 %s -- %s" % (p2_verdict, P2_TEXT))
    r("  P3 %s -- %s" % (p3_verdict, P3_TEXT))
    r("  P4 %s -- %s" % (p4_verdict, P4_TEXT))
    r("  a refuted prediction is recorded as data, never an error;"
      " the frozen texts are never rewritten")

    # ---- controls (S5) --------------------------------------------------
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
               " per_sample, interval_channel, control_row, cost,"
               " prediction) joining the shared kinds (demand,"
               " design_parameter, gate, scorecard_verdict,"
               " reciprocity, changelog); per-row units + provenance"
               " blocks with a per-row basis field (the demand"
               " ellipse basis and the example-family basis"
               " declared separately); no change to any existing"
               " field's meaning, unit or name -- schema 1.x per"
               " the frozen additive-only succession rule",
        major=CORPUS_MAJOR))
    r("")
    r("[S5] CONTROLS: read-only consumption of the tasks, the"
      " example and the recorded results; fail-closed corpus"
      " emitter (schema 1.1 pinned, units block + provenance on"
      " every row, unknown-kind refusal); double-run determinism"
      " below; corpus emission with hashes regardless of verdict;"
      " instrument-modification count row emitted (expected 0)")
    r("[RECIPROCITY] instrument modification count: 0 expected --"
      " the solver and its emission consumed unmodified; this"
      " script is new job-local instrumentation")
    return rows, report


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = sys.argv if argv is None else argv
    paths = {}
    results = []
    source_commit = None
    i = 1
    while i < len(argv):
        if argv[i] in ("--demand", "--control-a", "--control-b",
                       "--example") and i + 1 < len(argv):
            paths[argv[i][2:]] = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--result" and i + 1 < len(argv):
            results.append(argv[i + 1])
            i += 2
            continue
        if argv[i] == "--source-commit" and i + 1 < len(argv):
            source_commit = argv[i + 1]
            i += 2
            continue
        print("usage: case_d_digest_run.py --demand <motion.json>"
              " --control-a <motion.json> --control-b <motion.json>"
              " --example <normalized-motion.json>"
              " --result <label=file> [--result ...]"
              " --source-commit <40-hex-sha>", file=sys.stderr)
        return 2
    need = ("demand", "control-a", "control-b", "example")
    if any(k not in paths for k in need) or not results \
            or source_commit is None:
        print("usage: case_d_digest_run.py --demand <motion.json>"
              " --control-a <motion.json> --control-b <motion.json>"
              " --example <normalized-motion.json>"
              " --result <label=file> [--result ...]"
              " --source-commit <40-hex-sha>", file=sys.stderr)
        return 2
    if (len(source_commit) != 40
            or any(ch not in "0123456789abcdef"
                   for ch in source_commit)):
        print("FAIL-CLOSED: --source-commit must be a 40-char"
              " lowercase hex sha", file=sys.stderr)
        return 2
    tasks = {}
    for key, label in (("demand", "demand"),
                      ("control-a", "control_a"),
                      ("control-b", "control_b"),
                      ("example", "example")):
        try:
            with open(paths[key], "r", encoding="utf-8") as fh:
                tasks[label] = json.load(fh)
        except (ValueError, OSError) as exc:
            print("FAIL-CLOSED: %s: %s" % (paths[key], exc),
                  file=sys.stderr)
            return 2
    parsed = []
    for spec in results:
        if "=" not in spec:
            print("FAIL-CLOSED: --result must be label=file"
                  " (got %r)" % spec, file=sys.stderr)
            return 2
        label, path = spec.split("=", 1)
        if label not in TASK_LABELS:
            print("FAIL-CLOSED: unknown result label %r (expected"
                  " one of demand, control_a, control_b)" % label,
                  file=sys.stderr)
            return 2
        try:
            with open(path, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
        except (ValueError, OSError) as exc:
            print("FAIL-CLOSED: %s: %s" % (path, exc), file=sys.stderr)
            return 2
        info = validate_result(obj, path)
        parsed.append({"label": label, "path": path, "obj": obj,
                       "info": info})
    if len(parsed) != 9:
        print("FAIL-CLOSED: exactly nine result files expected"
              " (three tasks x three seeds)", file=sys.stderr)
        return 2

    rows1, report1 = compute(tasks, parsed, source_commit)
    rows2, report2 = compute(tasks, parsed, source_commit)
    corpus1 = [json.dumps(r, sort_keys=True) for r in rows1]
    corpus2 = [json.dumps(r, sort_keys=True) for r in rows2]
    identical = (report1 == report2 and corpus1 == corpus2)
    for line in report1:
        print(line)
    jsonl_path, csv_path, h1, h2, hfirst = write_corpus(rows1,
                                                       source_commit)
    print("")
    print("[CORPUS] %d rows, schema %s (additive; changelog row in"
          " corpus)" % (len(rows1), CORPUS_SCHEMA_VERSION))
    print("  %s" % jsonl_path)
    print("  sha256 %s" % h1)
    print("  %s" % csv_path)
    print("  sha256 %s" % h2)
    print("  first-row sha256 %s (corpus identity anchored at the"
          " first digest row, the case-C convention)" % hfirst)
    print("double-run determinism check: %s" %
          ("IDENTICAL" if identical else "DIFFERS (FAIL)"))
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
