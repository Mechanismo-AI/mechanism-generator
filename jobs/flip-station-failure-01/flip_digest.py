#!/usr/bin/env python3
"""Case study C failure digest: the 180 deg flip demand scored on the
recorded four-bar traces of flip-station-failure-01.

Pure analysis: no repo changes, no solver, no network, no clocks, no
randomness -- run twice and diff (the report AND the corpus files) is
the determinism control. The kinematics is the parity-tested
four_bar_skeleton from src/mechanism_generator/omts/geometry.py at
main 11823908, embedded verbatim below (the dwell-station-failure-01
precedent). One unit boundary is adapted at the input, never inside
the kernel: the engine records base_angle in RADIANS
(r25b.decode_refinement_variables stores torch.remainder(raw[8], 2*pi)
and the torch kinematics applies it directly as radians), while the
embedded omts kernel takes degrees (geometry.four_bar_skeleton applies
math.radians(base_deg)); the digest converts base_angle radians ->
degrees at the boundary (the recorded menu-E/frame-sweep unit
observation). theta_deg is the engine's crank parameter, the same
angle space as the recorded matched phases, for both crank directions.

Orientation (the demand this case adds): per docs/three-pose.md, the
tool frame's positive x-axis is the directed coupler A -> B (A = the
input crank end, B = the output rocker end), so the coupler
orientation at a phase is atan2(B_y - A_y, B_x - A_x) of the
skeleton's own a and b, and orientation errors wrap the full turn
(a 180 deg demand reverses the directed axis and wraps to exactly
180 deg from either side).

Witness disclosure (the dwell precedent, stated plainly): the
reproduction witness covers the engine's recorded POSITION errors
(error_1..3 at the recorded phase_1..3_deg) only; per-row orientation
errors are not part of all_candidates.csv, so orientation is scored
on the rebuilt trace at the same recorded phases -- computed from the
same embedded kinematics, never transcribed.

The demand (pinned in jobs/flip-station-failure-01/JOB.md):

  handoff 1    (-1.3, 0.5) normalized = (-130, 50) mm, orientation 0 deg
  mid pose     (0.0, 0.5)   normalized = (0, 50) mm,   orientation 90 deg (vertical)
  handoff 2    (1.3, 0.5)   normalized = (+130, 50) mm, orientation 180 deg
  tolerance    position 0.015 normalized (1.5 mm), orientation 1.5 deg
  demanded     a 180 deg swing from handoff 1 to handoff 2, forced
               through the vertical at the mid pose
  grid         7200 unique samples per cycle (7201 closed), exactly
               0.05 deg per interval

Fail-closed: missing files, missing columns, a phase/error
reproduction mismatch, undefined assembly on a trace recorded as
full-cycle, or broken grid arithmetic aborts the whole run with the
full list of problems found.

Corpus emission (the case study's design requirement, not a
decoration): every candidate -- scored or excluded -- is emitted
through jobs/corpus_emitter.py as a machine-readable solution corpus
(JSON Lines + a CSV projection) inside the run root, with an explicit
units block and a pinned corpus_schema_version in every row. The
corpus is the recorded-outcome feed for the B1 admission-gate work
(docs/strategy.md): the flipper case study is designed as that work's
downstream consumer, and its recorded outcomes must be data rows, not
prose. Corpus files are recorded outcome -- the JOB.md outcome section
references them by the sha256 hashes this digest prints.

Usage: python3 jobs/flip-station-failure-01/flip_digest.py <run-root> <source-commit>

<run-root> is the fresh timestamped directory the engine run created
under runs/flip-station-failure-01/results/task-001/either/. The
digest scans it for all_candidates.csv files and requires exactly two,
one per crank direction. <source-commit> is the merged main commit the
run was executed at; it is recorded in every corpus row's provenance
(claim-only-what-exists: pass the recorded sha, never an invented
one).
"""
from __future__ import annotations

import csv
import hashlib
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus_emitter import CORPUS_SCHEMA_VERSION, UNITS_TEMPLATE, write_corpus

TARGETS = ((-1.3, 0.5), (0.0, 0.5), (1.3, 0.5))
TARGET_ORIENTATIONS = (0.0, 90.0, 180.0)
POSITION_TOL = 0.015              # 1.5 mm at 100 mm per normalized unit
ORIENTATION_TOL_DEG = 1.5
DEMANDED_SWING_DEG = 180.0
SAMPLES = 7200                   # unique samples per cycle (7201 closed)
STEP_DEG = 360.0 / SAMPLES      # exactly 0.05 deg
REPRO_TOL = 1e-6                 # normalized (1e-4 mm)
TASK_ID = "flip_station_failure_v1"
FAMILY = "four_bar"
SEED = 101
JOB_ID = "flip-station-failure-01"

# Same values as geometry.PARAM_NAMES; the kinematics below is embedded
# verbatim and shares this tuple.
PARAM_NAMES = ("l1", "l2", "l3", "l4", "S_ratio",
               "bar_length", "base_x", "base_y", "base_angle")
REQUIRED_COLUMNS = set(PARAM_NAMES) | {
    "candidate_id", "branch_sign", "crank_direction",
    "qualification_level", "full_cycle_assembly",
    "error_1", "error_2", "error_3",
    "phase_1_deg", "phase_2_deg", "phase_3_deg",
}


def die(problems):
    print("flip_digest: FAIL-CLOSED:", file=sys.stderr)
    for problem in problems:
        print("  - %s" % problem, file=sys.stderr)
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Kinematics: embedded VERBATIM from
# src/mechanism_generator/omts/geometry.py at main 11823908 (parity-tested
# against engine/panel.py, which is parity-tested against the engine's Torch
# simulator). Do not modify independently: keep identical to the source
# module or re-copy from it.
# ---------------------------------------------------------------------------

PARAM_COUNT = 9


def _validated_params(params, branch_sign: int) -> list[float]:
    if branch_sign not in (-1, 1):
        raise ValueError("branch_sign must be -1 or 1.")
    values = [float(value) for value in params]
    if len(values) != PARAM_COUNT:
        raise ValueError(f"Parameters must be {PARAM_COUNT} values, got {len(values)}.")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Parameters must all be finite.")
    if any(value <= 0.0 for value in values[:4]):
        raise ValueError("Link lengths l1..l4 must be positive.")
    return values


def four_bar_skeleton(params, branch_sign: int, theta_deg: float, carrier=None):
    """World positions at one crank parameter value.

    Returns a dict with `o2`, `o4`, `a`, `b`, `p` (the coupler point)
    and `carrier_corners` (an empty tuple unless `carrier` is a
    `(width, depth)` pair), or `None` when the assembly is undefined at
    this phase. Undefined assembly is data, not an error.
    """
    l1, l2, l3, l4, s_ratio, bar, base_x, base_y, base_deg = _validated_params(params, branch_sign)
    base = math.radians(base_deg)
    o2 = (base_x, base_y)
    o4 = (base_x + l1 * math.cos(base), base_y + l1 * math.sin(base))
    angle = math.radians(theta_deg) + base
    a = (base_x + l2 * math.cos(angle), base_y + l2 * math.sin(angle))
    delta = (a[0] - o4[0], a[1] - o4[1])
    distance = math.hypot(delta[0], delta[1])
    if distance <= 0.0 or distance > l3 + l4 or distance < abs(l3 - l4):
        return None
    cx, cy = delta[0] / distance, delta[1] / distance
    along = (l4 * l4 - l3 * l3 + distance * distance) / (2.0 * distance)
    height = math.sqrt(max(0.0, l4 * l4 - along * along))
    # branch_sign selects the circle-intersection side, perpendicular to O4->A.
    b = (o4[0] + along * cx - branch_sign * height * cy,
         o4[1] + along * cy + branch_sign * height * cx)
    ux, uy = (b[0] - a[0]) / l3, (b[1] - a[1]) / l3
    vx, vy = -uy, ux
    p = (a[0] + s_ratio * (b[0] - a[0]) + bar * vx,
         a[1] + s_ratio * (b[1] - a[1]) + bar * vy)
    corners: tuple = ()
    if carrier is not None:
        width, depth = float(carrier[0]), float(carrier[1])
        if width <= 0.0 or depth <= 0.0:
            raise ValueError("Carrier dimensions must be positive.")
        corners = tuple(
            (p[0] + x * ux + y * vx, p[1] + x * uy + y * vy)
            for x, y in ((width / 2.0, depth / 2.0), (width / 2.0, -depth / 2.0),
                         (-width / 2.0, -depth / 2.0), (-width / 2.0, depth / 2.0))
        )
    return {"o2": o2, "o4": o4, "a": a, "b": b, "p": p, "carrier_corners": corners}


# ---------------------------------------------------------------------------
# Grid arithmetic guard (frozen in the JOB; an off-by-one here shifts
# every candidate's reading by half a sample step).
# ---------------------------------------------------------------------------

def check_grid():
    problems = []
    if SAMPLES * STEP_DEG != 360.0:
        problems.append("grid: %d samples at %r deg do not close the 360 deg cycle" % (SAMPLES, STEP_DEG))
    if STEP_DEG != 0.05:
        problems.append("grid: the sample step is %r deg, not exactly 0.05" % STEP_DEG)
    return problems


# ---------------------------------------------------------------------------
# Orientation arithmetic (docs/three-pose.md convention).
# ---------------------------------------------------------------------------

def wrap_deg(value):
    """Principal value in [-180, 180)."""
    return (value + 180.0) % 360.0 - 180.0


def orientation_error_deg(angle, target):
    """Wrap-to-180 magnitude: 179 and -179 are 2 deg apart, not 358."""
    return abs(wrap_deg(angle - target))


def spread_deg(first, second):
    """Magnitude of the wrapped difference between two orientations."""
    return abs(wrap_deg(second - first))


def coupler_orientation_deg(skeleton):
    """Directed coupler A -> B angle, CCW from world +x (three-pose.md)."""
    return math.degrees(math.atan2(skeleton["b"][1] - skeleton["a"][1],
                                   skeleton["b"][0] - skeleton["a"][0]))


def transmission_angle_deg(skeleton):
    """Angle at B between the coupler (B -> A) and the rocker (B -> O4)."""
    ba = (skeleton["a"][0] - skeleton["b"][0], skeleton["a"][1] - skeleton["b"][1])
    bo = (skeleton["o4"][0] - skeleton["b"][0], skeleton["o4"][1] - skeleton["b"][1])
    cosine = (ba[0] * bo[0] + ba[1] * bo[1]) / (math.hypot(*ba) * math.hypot(*bo))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


# ---------------------------------------------------------------------------
# Input reading (fail-closed).
# ---------------------------------------------------------------------------

def read_candidate_rows(root):
    files = sorted(root.rglob("all_candidates.csv"))
    if not files:
        die(["no all_candidates.csv found under %s" % root])
    problems = []
    by_direction = {}
    for path in files:
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            header = reader.fieldnames or []
            missing = REQUIRED_COLUMNS - set(header)
            if missing:
                problems.append("%s: missing columns %s" % (path, sorted(missing)))
                continue
            rows = list(reader)
        if not rows:
            problems.append("%s: no candidate rows" % path)
            continue
        directions = {str(row["crank_direction"]).strip() for row in rows}
        if len(directions) != 1:
            problems.append("%s: mixed crank_direction values %s" % (path, sorted(directions)))
            continue
        direction = directions.pop()
        if direction not in ("positive", "negative"):
            problems.append("%s: unexpected crank_direction %r" % (path, direction))
            continue
        if direction in by_direction:
            problems.append(
                "%s: a second %s direction tree (point the digest at the fresh run root)" % (path, direction))
            continue
        by_direction[direction] = (path, rows)
    if problems:
        die(problems)
    if set(by_direction) != {"positive", "negative"}:
        die(["expected exactly one positive and one negative all_candidates.csv, found directions %s"
             % sorted(by_direction)])
    return by_direction


def parse_bool(value, label, problems):
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    problems.append("%s: expected True/False, got %r" % (label, value))
    return None


# ---------------------------------------------------------------------------
# Scoring.
# ---------------------------------------------------------------------------

def score_candidate(row, direction, problems):
    """Score one candidate row, or return an exclusion record."""
    candidate_id = str(row["candidate_id"])
    label = "candidate %s" % candidate_id
    values = []
    for name in PARAM_NAMES:
        try:
            values.append(float(row[name]))
        except (TypeError, ValueError):
            problems.append("%s: column %s is not a number" % (label, name))
            return None
    try:
        branch = int(float(row["branch_sign"]))
    except (TypeError, ValueError):
        problems.append("%s: branch_sign is not a number" % label)
        return None
    if branch not in (-1, 1):
        problems.append("%s: branch_sign %r is not -1 or 1" % (label, row["branch_sign"]))
        return None
    raw_values = list(values)

    # Unit boundary (engine recording convention, recorded finding): the
    # engine stores base_angle in RADIANS (decode_refinement_variables:
    # torch.remainder(raw[8], 2*pi)) and applies it directly in its torch
    # kinematics; the embedded omts kernel takes degrees. Convert at the
    # boundary so the rebuild matches the engine's recorded world geometry.
    # raw_values stays as the engine recorded it for the corpus rows.
    values[8] = math.degrees(values[8])

    # Reproduction witness (position errors only, disclosed above):
    # the rebuilt kinematics must reproduce the engine's own record at
    # the recorded matched phases, for every row. Orientation errors
    # are computed on the same rebuilt phases.
    position_errors = []
    orientation_errors = []
    matched_transmission = []
    for index in (1, 2, 3):
        try:
            theta = float(row["phase_%d_deg" % index])
            recorded = float(row["error_%d" % index])
        except (TypeError, ValueError):
            problems.append("%s: phase_%d_deg or error_%d is not a number" % (label, index, index))
            return None
        try:
            skeleton = four_bar_skeleton(values, branch, theta)
        except ValueError as exc:
            problems.append("%s: kinematics rejected the recorded parameters (%s)" % (label, exc))
            return None
        if skeleton is None:
            problems.append("%s: assembly is undefined at the recorded phase_%d_deg" % (label, index))
            return None
        target = TARGETS[index - 1]
        rebuilt = math.hypot(skeleton["p"][0] - target[0], skeleton["p"][1] - target[1])
        if abs(rebuilt - recorded) > REPRO_TOL:
            problems.append(
                "%s: target %d reproduction mismatch: rebuilt %.9f vs recorded %.9f (tolerance %g)"
                % (label, index, rebuilt, recorded, REPRO_TOL))
            return None
        position_errors.append(rebuilt)
        orientation_errors.append(
            orientation_error_deg(coupler_orientation_deg(skeleton), TARGET_ORIENTATIONS[index - 1]))
        matched_transmission.append(transmission_angle_deg(skeleton))

    full_cycle = parse_bool(row["full_cycle_assembly"], "%s: full_cycle_assembly" % label, problems)
    if full_cycle is None:
        return None
    record = {
        "candidate_id": candidate_id,
        "direction": direction,
        "branch_sign": branch,
        "qualification_level": str(row["qualification_level"]),
        "parameters": values,
        "parameters_raw": raw_values,
        "position_errors": position_errors,
        "orientation_errors": orientation_errors,
        "matched_transmission_deg": matched_transmission,
        "excluded": None,
    }
    if not full_cycle:
        record["excluded"] = "no_full_cycle_assembly"
        return record

    # Full-cycle trace at the pinned grid: coupler point and orientation.
    points = []
    orientations = []
    transmission_min = None
    for index in range(SAMPLES):
        theta = 360.0 * index / SAMPLES
        try:
            skeleton = four_bar_skeleton(values, branch, theta)
        except ValueError as exc:
            problems.append("%s: kinematics rejected the recorded parameters (%s)" % (label, exc))
            return None
        if skeleton is None:
            problems.append(
                "%s: recorded full_cycle_assembly but the rebuild is undefined at theta %.2f deg"
                " -- a real inconsistency, never a quiet pass" % (label, theta))
            return None
        points.append(skeleton["p"])
        orientations.append(coupler_orientation_deg(skeleton))
        angle = transmission_angle_deg(skeleton)
        if transmission_min is None or angle < transmission_min:
            transmission_min = angle

    # D3b: free swing anywhere -- the unwrapped coupler-angle range over
    # the full cycle (a coupler that fully rotates shows a range >= 360).
    unwrapped = [0.0]
    for index in range(1, SAMPLES):
        unwrapped.append(unwrapped[-1] + wrap_deg(orientations[index] - orientations[index - 1]))
    record["d3b_free_swing_deg"] = max(unwrapped) - min(unwrapped)
    record["d3b_closure_deg"] = wrap_deg(orientations[0] - orientations[-1])

    # D3a: best achievable swing at the demanded positions -- samples
    # within position tolerance of handoff 1 paired with samples within
    # tolerance of handoff 2, best wrapped spread. Declared upper-bound
    # convention: any near sample of one handoff against any near sample
    # of the other; simultaneity along the whole path is the gate rows'
    # business, not this diagnostic's.
    t1_near = [index for index in range(SAMPLES)
               if math.hypot(points[index][0] - TARGETS[0][0],
                             points[index][1] - TARGETS[0][1]) <= POSITION_TOL]
    t3_near = [index for index in range(SAMPLES)
               if math.hypot(points[index][0] - TARGETS[2][0],
                             points[index][1] - TARGETS[2][1]) <= POSITION_TOL]
    if t1_near and t3_near:
        record["d3a_swing_at_positions_deg"] = max(
            spread_deg(orientations[first], orientations[second])
            for first in t1_near for second in t3_near)
        record["d3a_near_samples"] = (len(t1_near), len(t3_near))
    else:
        record["d3a_swing_at_positions_deg"] = None
        record["d3a_near_samples"] = (len(t1_near), len(t3_near))

    # Transmission data: the worst angle over the cycle (the D2 window
    # evidence; the mid pose is where the prediction says it collapses).
    record["transmission_min_cycle_deg"] = transmission_min
    return record


def binding_class(record):
    """Orientation- vs position-dominant, in tolerance units."""
    position_ratio = max(record["position_errors"]) / POSITION_TOL
    orientation_ratio = max(record["orientation_errors"]) / ORIENTATION_TOL_DEG
    return ("orientation" if orientation_ratio > position_ratio else "position",
            position_ratio, orientation_ratio)


# ---------------------------------------------------------------------------
# Corpus rows (jobs/corpus_emitter.py schema).
# ---------------------------------------------------------------------------

def corpus_row(record, run_id, source_commit):
    binding, position_ratio, orientation_ratio = binding_class(record)
    gates = {}
    for index in (1, 2, 3):
        error = record["position_errors"][index - 1]
        gates["position_%d" % index] = {
            "error": error, "tolerance": POSITION_TOL,
            "margin": POSITION_TOL - error, "pass": error <= POSITION_TOL,
        }
        error = record["orientation_errors"][index - 1]
        gates["orientation_%d" % index] = {
            "error": error, "tolerance": ORIENTATION_TOL_DEG,
            "margin": ORIENTATION_TOL_DEG - error, "pass": error <= ORIENTATION_TOL_DEG,
        }
    if record["excluded"] is not None:
        verdict = "excluded:%s" % record["excluded"]
    elif all(gates["position_%d" % index]["pass"] for index in (1, 2, 3)) and \
            all(gates["orientation_%d" % index]["pass"] for index in (1, 2, 3)):
        verdict = "pass_all_gates"
    else:
        verdict = "fail:%s-dominant" % binding
    if record["excluded"] is None:
        gates["d3a_swing_at_positions_deg"] = record["d3a_swing_at_positions_deg"]
        gates["d3a_near_samples"] = list(record["d3a_near_samples"])
        gates["d3b_free_swing_deg"] = record["d3b_free_swing_deg"]
        gates["d3b_closure_deg"] = record["d3b_closure_deg"]
        gates["transmission_min_cycle_deg"] = record["transmission_min_cycle_deg"]
    gates["transmission_at_matched_phases_deg"] = record["matched_transmission_deg"]
    units = dict(UNITS_TEMPLATE)
    units["parameters"] = ("named vector as the engine recorded it; base_angle in radians"
                            " (engine recording convention), converted to deg at the digest"
                            " input boundary; lengths and offsets in normalized units")
    units["orientation_error"] = "deg, wrap-to-180 magnitude (docs/three-pose.md)"
    return {
        "corpus_schema_version": CORPUS_SCHEMA_VERSION,
        "task_id": TASK_ID,
        "family": FAMILY,
        "candidate_id": record["candidate_id"],
        "direction": record["direction"],
        "branch_sign": record["branch_sign"],
        "parameters": dict(zip(PARAM_NAMES, record["parameters_raw"])),
        "solution_status": ("scored" if record["excluded"] is None
                            else "excluded:%s" % record["excluded"]),
        "gates": gates,
        "verdict": verdict,
        "demand": {
            "targets": [
                {"id": "T1", "position": [-1.3, 0.5], "orientation_deg": 0.0},
                {"id": "T2", "position": [0.0, 0.5], "orientation_deg": 90.0},
                {"id": "T3", "position": [1.3, 0.5], "orientation_deg": 180.0},
            ],
            "position_tolerance": POSITION_TOL,
            "orientation_tolerance_deg": ORIENTATION_TOL_DEG,
            "demanded_swing_deg": DEMANDED_SWING_DEG,
        },
        "units": units,
        "provenance": {
            "job": JOB_ID,
            "task_id": TASK_ID,
            "seed": SEED,
            "run_id": run_id,
            "source_commit": source_commit,
        },
    }


# ---------------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------------

def fmt(value):
    return "%.6f" % value


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv):
    if len(argv) != 3:
        die(["usage: python3 flip_digest.py <run-root> <source-commit>"])
    root = Path(argv[1])
    source_commit = str(argv[2])
    if not root.is_dir():
        die(["run root %s is not a directory" % root])
    stripped = source_commit.strip().lower()
    if len(stripped) < 7 or len(stripped) > 40 or not all(
            character in "0123456789abcdef" for character in stripped):
        die(["source commit %r is not a git sha (pass the merged main commit the run"
             " was executed at; claim-only-what-exists)" % source_commit])
    source_commit = stripped
    problems = check_grid()
    if problems:
        die(problems)
    by_direction = read_candidate_rows(root)

    lines = []
    lines.append("flip_digest: case study C failure analysis (flip-station-failure-01)")
    lines.append("run root: %s" % root)
    lines.append("source commit: %s" % source_commit)
    lines.append("grid: %d unique samples at %r deg (asserted at run time)" % (SAMPLES, STEP_DEG))
    lines.append(
        "demand: handoffs (-130, 50) and (+130, 50) mm at orientations 0 and 180 deg,"
        " mid pose (0, 50) mm at 90 deg (vertical); tolerances 0.015 normalized (1.5 mm)"
        " and 1.5 deg; demanded swing 180 deg through vertical")
    lines.append(
        "kinematics: four_bar_skeleton embedded verbatim from src/mechanism_generator/omts/geometry.py"
        " (main 11823908; engine-recorded base_angle converted radians -> degrees at the boundary)")
    lines.append(
        "witness: recorded error_1..3 reproduced at phase_1..3_deg within %g normalized"
        " (fail-closed); orientation scored on the rebuilt trace at the same phases"
        " (disclosed, dwell precedent)" % REPRO_TOL)

    pool_scored = []
    pool_excluded = 0
    all_records = []
    for direction in ("positive", "negative"):
        path, rows = by_direction[direction]
        records = []
        for row in rows:
            record = score_candidate(row, direction, problems)
            if record is not None:
                records.append(record)
        if problems:
            die(problems)
        scored = [record for record in records if record["excluded"] is None]
        excluded = [record for record in records if record["excluded"] is not None]
        if not scored:
            die(["direction %s: no scorable candidates (all excluded or failed)" % direction])
        lines.append("")
        lines.append("== direction %s: %s (%d rows) ==" % (direction, path, len(rows)))
        histogram = Counter(record["qualification_level"] for record in records)
        lines.append("qualification: %s" % ", ".join(
            "%s %d" % (name, histogram[name]) for name in sorted(histogram)))
        lines.append("columns: pos_x/ori_x = max per-target error in tolerance units;"
                     " d3a = best T1-near to T3-near swing in deg (position tolerance only,"
                     " declared upper-bound pairing; none = a handoff unreached);"
                     " d3b = unwrapped full-cycle coupler-angle range in deg;"
                     " tx_mid/tx_min = transmission angle at the mid-pose phase / cycle minimum, deg")
        lines.append("%-20s %-34s %8s %8s %10s %10s %9s %9s %s" % (
            "candidate", "qualification", "pos_x", "ori_x", "d3a", "d3b",
            "tx_mid", "tx_min", "verdict"))
        for record in records:
            if record["excluded"] is not None:
                lines.append("%-20s EXCLUDED: %s" % (record["candidate_id"], record["excluded"]))
                continue
            binding, position_ratio, orientation_ratio = binding_class(record)
            verdict = ("pass_all_gates" if all(
                record["position_errors"][index] <= POSITION_TOL for index in range(3)) and all(
                record["orientation_errors"][index] <= ORIENTATION_TOL_DEG for index in range(3))
                else "fail:%s-dominant" % binding)
            d3a = record["d3a_swing_at_positions_deg"]
            lines.append("%-20s %-34s %8.2f %8.2f %10s %10.3f %9.2f %9.2f %s" % (
                record["candidate_id"], record["qualification_level"],
                position_ratio, orientation_ratio,
                "none" if d3a is None else "%.3f" % d3a,
                record["d3b_free_swing_deg"],
                record["matched_transmission_deg"][1],
                record["transmission_min_cycle_deg"], verdict))
        pool_scored.extend(scored)
        pool_excluded += len(excluded)
        all_records.extend(records)

    if not pool_scored:
        die(["no scorable candidates in either direction"])
    corpus_rows = [corpus_row(record, root.name, source_commit) for record in all_records]

    # Pool-level frozen readings.
    passing = [record for record in pool_scored
               if all(error <= POSITION_TOL for error in record["position_errors"])
               and all(error <= ORIENTATION_TOL_DEG for error in record["orientation_errors"])]
    binding_counts = Counter(binding_class(record)[0] for record in pool_scored)
    orientation_bound = binding_counts.get("orientation", 0)
    position_bound = binding_counts.get("position", 0)
    pool_d3a = [record["d3a_swing_at_positions_deg"] for record in pool_scored
                if record["d3a_swing_at_positions_deg"] is not None]
    pool_d3a_max = max(pool_d3a) if pool_d3a else None
    pool_d3b_max = max(record["d3b_free_swing_deg"] for record in pool_scored)
    pool_tx_mid_min = min(record["matched_transmission_deg"][1] for record in pool_scored)
    pool_tx_min = min(record["transmission_min_cycle_deg"] for record in pool_scored)

    if orientation_bound and not position_bound:
        d2_branch = "D2 as-predicted branch: orientation-coupled binding across the pool"
    elif orientation_bound and position_bound:
        d2_branch = "D2 MIXED branch: position-dominant candidates exist -- read before staging"
    else:
        d2_branch = "D2 UNEXPECTED branch: position-coupled binding pool-wide -- read before staging"
    if pool_d3b_max < DEMANDED_SWING_DEG:
        d3_branch = ("D3 as-predicted family-limited branch: pool-max free swing %.3f deg < 180 deg"
                     % pool_d3b_max)
    elif pool_d3a_max is None or pool_d3a_max < DEMANDED_SWING_DEG:
        d3_branch = ("D3 placement-limited branch: free swing reaches %.3f deg but the at-pose"
                     " swing does not reach 180 deg through the demanded positions" % pool_d3b_max)
    else:
        d3_branch = "D3 UNEXPECTED branch: at-pose swing reaches the demand -- read before staging"

    lines.append("")
    lines.append("POOL: scored %d, excluded %d" % (len(pool_scored), pool_excluded))
    lines.append("D1-relevant: candidates meeting all six gates at the recorded matched phases: %d%s"
                 % (len(passing), "" if not passing else " (%s)" % ", ".join(
                     "%s/%s" % (r["direction"], r["candidate_id"]) for r in passing)))
    lines.append("D2 binding class: orientation-dominant %d, position-dominant %d -> %s"
                 % (orientation_bound, position_bound, d2_branch))
    lines.append("D2 data: pool-min transmission angle at the mid-pose phase %.3f deg;"
                 " pool-min cycle transmission %.3f deg (the 90 deg vertical window evidence)"
                 % (pool_tx_mid_min, pool_tx_min))
    lines.append("D3 family leg: pool-max free swing (d3b) %.3f deg" % pool_d3b_max)
    lines.append("D3 placement leg: pool-max at-pose swing (d3a) %s" % (
        "none (no candidate reaches both handoffs within position tolerance)"
        if pool_d3a_max is None else "%.3f deg" % pool_d3a_max))
    lines.append(d3_branch)
    lines.append("D4 control: %d candidate(s) pass all gates -- any nonzero count refutes D1"
                 " and is the honest result" % len(passing))
    lines.append("witness: every row reproduced recorded error_1..3 at phase_1..3_deg"
                 " within %g normalized (fail-closed)" % REPRO_TOL)

    corpus_dir = root / "corpus"
    jsonl_path = corpus_dir / (TASK_ID + ".jsonl")
    csv_path = corpus_dir / (TASK_ID + ".csv")
    row_count = write_corpus(corpus_rows, jsonl_path, csv_path)
    lines.append("")
    lines.append("corpus: %d rows, schema version %s" % (row_count, CORPUS_SCHEMA_VERSION))
    lines.append("corpus: %s (sha256 %s)" % (jsonl_path, sha256_of(jsonl_path)))
    lines.append("corpus: %s (sha256 %s)" % (csv_path, sha256_of(csv_path)))
    lines.append("corpus: units block and provenance in every row; the files are recorded"
                 " outcome -- reference them in the JOB outcome by these hashes")
    report = "\n".join(lines) + "\n"
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
