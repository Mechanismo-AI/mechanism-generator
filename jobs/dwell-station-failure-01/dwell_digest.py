#!/usr/bin/env python3
"""Case study A failure digest: the hold-still demand scored on the
recorded four-bar traces of dwell-station-failure-01.

Pure analysis: no repo changes, no solver, no network, no clocks, no
randomness -- run twice and diff is the determinism control. The
kinematics is the parity-tested four_bar_skeleton from
src/mechanism_generator/omts/geometry.py at main 11823908, embedded
verbatim below. One unit boundary is adapted at the input, never inside
the kernel: the engine records base_angle in RADIANS
(r25b.decode_refinement_variables stores torch.remainder(raw[8], 2*pi)
and the torch kinematics applies it directly as radians), while the
embedded omts kernel takes degrees (geometry.four_bar_skeleton applies
math.radians(base_deg)); the digest converts base_angle radians ->
degrees at the boundary (the recorded menu-E/frame-sweep unit
observation). theta_deg is the engine's crank parameter, the same
angle space as the recorded matched phases, for both crank directions.

The demand (pinned in jobs/dwell-station-failure-01/JOB.md):

  station       (0.0, 0.5) normalized = (0, 50) mm (the T2 pose)
  hold radius   0.3 mm = 0.003 normalized (1 unit = 100 mm)
  hold window   >= 50 deg of the input cycle, continuous
  grid          7201 closed samples = 7200 unique samples per cycle =
                7200 intervals of exactly 0.05 deg; 50 deg = 1000
                intervals = 1001 samples inclusive (start and end)

Fail-closed: missing files, missing columns, a phase/error
reproduction mismatch, undefined assembly on a trace recorded as
full-cycle, or any off-by-one in the grid arithmetic aborts the whole
run with the full list of problems found. Drift is reported as data
and NEVER scored: scoring drift flatters slow passes through the
region and produces smaller numbers.

Usage: python3 jobs/dwell-station-failure-01/dwell_digest.py <run-root>

<run-root> is the fresh timestamped directory the engine run created
under runs/dwell-station-failure-01/results/task-001/either/. The
digest scans it for all_candidates.csv files and requires exactly two,
one per crank direction.
"""
from __future__ import annotations

import csv
import math
import sys
from collections import Counter, deque
from pathlib import Path

STATION = (0.0, 0.5)            # normalized = (0, 50) mm; the T2 pose
TARGETS = ((-1.3, 0.5), (0.0, 0.5), (1.3, 0.5))
HOLD_RADIUS = 0.003              # 0.3 mm at 100 mm per normalized unit
SAMPLES = 7200                   # unique samples per cycle (7201 closed)
STEP_DEG = 360.0 / SAMPLES      # exactly 0.05 deg
WINDOW_INTERVALS = 1000           # 50 deg at 0.05 deg per interval
WINDOW_SAMPLES = WINDOW_INTERVALS + 1  # 1001 samples inclusive
REPRO_TOL = 1e-6                 # normalized (1e-4 mm)
CUSP_SPEED_FRACTION = 0.01       # of the candidate's median sample speed

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
    print("dwell_digest: FAIL-CLOSED:", file=sys.stderr)
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
# every candidate's score by half a sample step).
# ---------------------------------------------------------------------------

def check_grid():
    problems = []
    if SAMPLES * STEP_DEG != 360.0:
        problems.append("grid: %d samples at %r deg do not close the 360 deg cycle" % (SAMPLES, STEP_DEG))
    if STEP_DEG != 0.05:
        problems.append("grid: the sample step is %r deg, not exactly 0.05" % STEP_DEG)
    if round(50.0 / STEP_DEG) != WINDOW_INTERVALS:
        problems.append("grid: 50 deg is not exactly %d intervals at %r deg" % (WINDOW_INTERVALS, STEP_DEG))
    if WINDOW_SAMPLES != WINDOW_INTERVALS + 1:
        problems.append("grid: the window spans %d samples, not intervals + 1" % WINDOW_SAMPLES)
    return problems


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

def widest_true_run_deg(flags):
    """Widest circular run of True flags, in degrees.

    A run of L samples covers L-1 intervals; a single sample is a
    zero-width touch. All-True is the full closed cycle: 360.0.
    """
    count = len(flags)
    if not any(flags):
        return 0.0
    if all(flags):
        return 360.0
    runs = []
    start = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, count - 1))
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == count - 1:
        runs = [(runs[-1][0], runs[0][1] + count)] + runs[1:-1]
    return max(last - first for first, last in runs) * STEP_DEG


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

    # Unit boundary (engine recording convention, recorded finding): the
    # engine stores base_angle in RADIANS (decode_refinement_variables:
    # torch.remainder(raw[8], 2*pi)) and applies it directly in its torch
    # kinematics; the embedded omts kernel takes degrees. Convert at the
    # boundary so the rebuild matches the engine's recorded world geometry.
    values[8] = math.degrees(values[8])

    # Reproduction witness: the rebuilt kinematics must reproduce the
    # engine's own record at the recorded matched phases, for every row.
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

    full_cycle = parse_bool(row["full_cycle_assembly"], "%s: full_cycle_assembly" % label, problems)
    if full_cycle is None:
        return None
    record = {
        "candidate_id": candidate_id,
        "direction": direction,
        "qualification_level": str(row["qualification_level"]),
        "excluded": None,
    }
    if not full_cycle:
        record["excluded"] = "no_full_cycle_assembly"
        return record

    # Full-cycle trace at the pinned grid.
    points = []
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

    # Primary: best 50-deg window, scored as max distance from the station.
    dist_sq = [(x - STATION[0]) ** 2 + (y - STATION[1]) ** 2 for x, y in points]
    extended = dist_sq + dist_sq[:WINDOW_SAMPLES - 1]
    queue = deque()
    window_max = []
    for index, value in enumerate(extended):
        while queue and extended[queue[-1]] <= value:
            queue.pop()
        queue.append(index)
        if queue[0] <= index - WINDOW_SAMPLES:
            queue.popleft()
        if index >= WINDOW_SAMPLES - 1:
            window_max.append(extended[queue[0]])
    if len(window_max) != SAMPLES:
        problems.append("%s: window arithmetic produced %d starts (expected %d) -- off-by-one guard"
                        % (label, len(window_max), SAMPLES))
        return None
    best_start = 0
    for start in range(1, SAMPLES):
        if window_max[start] < window_max[best_start]:
            best_start = start
    record["station_radius"] = math.sqrt(window_max[best_start])
    record["station_window_start_deg"] = best_start * STEP_DEG

    # Drift rows: data, never scored.
    start_point = points[best_start]
    end_point = points[(best_start + WINDOW_INTERVALS) % SAMPLES]
    record["drift_start"] = math.hypot(start_point[0] - STATION[0], start_point[1] - STATION[1])
    record["drift_end"] = math.hypot(end_point[0] - STATION[0], end_point[1] - STATION[1])

    # Widest contiguous station window meeting the hold radius.
    flags = [value <= HOLD_RADIUS * HOLD_RADIUS for value in dist_sq]
    record["station_widest_deg"] = widest_true_run_deg(flags)

    # Free-dwell diagnostic: best 50-deg window anywhere, scored against
    # its own center-sample anchor (declared convention: the anchor is
    # the trace point at the window's center sample; the exact
    # minimal-enclosing-circle radius is at most this, and the
    # placement-vs-stopping question is answered identically). Pruned
    # scan: exact for the best window, deterministic throughout.
    half = WINDOW_INTERVALS // 2
    best = None  # (radius_sq, start, anchor_x, anchor_y)
    for start in range(SAMPLES):
        anchor = points[(start + half) % SAMPLES]
        worst = 0.0
        pruned = False
        for offset in range(WINDOW_SAMPLES):
            point = points[(start + offset) % SAMPLES]
            value = ((point[0] - anchor[0]) ** 2 + (point[1] - anchor[1]) ** 2)
            if value > worst:
                worst = value
                if best is not None and worst >= best[0]:
                    pruned = True
                    break
        if not pruned and (best is None or worst < best[0]):
            best = (worst, start, anchor[0], anchor[1])
    if best is None:
        problems.append("%s: the free-dwell scan found no window" % label)
        return None
    record["free_radius"] = math.sqrt(best[0])
    record["free_window_start_deg"] = best[1] * STEP_DEG
    record["free_anchor"] = (best[2], best[3])

    # Min-speed classification of both best windows (apex vs cusp).
    velocity_x = []
    velocity_y = []
    speed = []
    for index in range(SAMPLES):
        here = points[index]
        there = points[(index + 1) % SAMPLES]
        velocity_x.append(there[0] - here[0])
        velocity_y.append(there[1] - here[1])
        speed.append(math.hypot(there[0] - here[0], there[1] - here[1]))
    ordered = sorted(speed)
    median = 0.5 * (ordered[SAMPLES // 2 - 1] + ordered[SAMPLES // 2])

    def classify(start):
        index = min(range(start, start + WINDOW_SAMPLES),
                    key=lambda i: speed[i % SAMPLES]) % SAMPLES
        previous = (index - 1) % SAMPLES
        reversal = (velocity_x[previous] * velocity_x[index]
                    + velocity_y[previous] * velocity_y[index]) < 0.0
        is_cusp = reversal and speed[index] < CUSP_SPEED_FRACTION * median
        return ("cusp" if is_cusp else "apex"), speed[index] / STEP_DEG

    record["station_class"], record["station_min_speed"] = classify(best_start)
    record["free_class"], record["free_min_speed"] = classify(best[1])
    return record


# ---------------------------------------------------------------------------
# Report.
# ---------------------------------------------------------------------------

def fmt(value):
    return "%.6f" % value


def main(argv):
    if len(argv) != 2:
        die(["usage: python3 dwell_digest.py <run-root>"])
    root = Path(argv[1])
    if not root.is_dir():
        die(["run root %s is not a directory" % root])
    problems = check_grid()
    if problems:
        die(problems)
    by_direction = read_candidate_rows(root)

    lines = []
    lines.append("dwell_digest: case study A failure analysis (dwell-station-failure-01)")
    lines.append("run root: %s" % root)
    lines.append(
        "grid: %d unique samples at %r deg; window = %d intervals = %d samples = 50.00 deg (asserted at run time)"
        % (SAMPLES, STEP_DEG, WINDOW_INTERVALS, WINDOW_SAMPLES))
    lines.append("station: (%s, %s) normalized = (0, 50) mm" % (fmt(STATION[0]), fmt(STATION[1])))
    lines.append("hold radius: %s normalized = 0.3 mm" % fmt(HOLD_RADIUS))
    lines.append(
        "kinematics: four_bar_skeleton embedded verbatim from src/mechanism_generator/omts/geometry.py"
        " (main 11823908; engine-recorded base_angle converted radians -> degrees at the boundary);"
        " reproduction witness tolerance %g normalized" % REPRO_TOL)
    lines.append("drift: reported as data, never scored (frozen)")

    pool_scored = []
    pool_excluded = 0
    class_counts = Counter()
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
        lines.append("columns: st_radius/free_radius in normalized units (1 unit = 100 mm);"
                     " class = min-speed class of the best station/free window;"
                     " st_speed/free_speed = those windows' minimum speeds in normalized units per deg;"
                     " drift rows are data, never scored")
        lines.append("%-20s %-34s %10s %8s %10s %10s %8s %-24s %-12s %10s %10s %9s %9s" % (
            "candidate", "qualification", "st_radius", "st_mm", "widest_deg",
            "free_radius", "free_mm", "free_anchor", "class", "st_speed",
            "free_speed", "drift_in", "drift_out"))
        for record in records:
            if record["excluded"] is not None:
                lines.append("%-20s EXCLUDED: %s" % (record["candidate_id"], record["excluded"]))
                continue
            anchor = record["free_anchor"]
            lines.append("%-20s %-34s %10s %8.3f %10.3f %10s %8.3f (%s, %s) %-5s/%-5s %.6e %.6e %9s %9s" % (
                record["candidate_id"], record["qualification_level"],
                fmt(record["station_radius"]), 100.0 * record["station_radius"],
                record["station_widest_deg"],
                fmt(record["free_radius"]), 100.0 * record["free_radius"],
                fmt(anchor[0]), fmt(anchor[1]),
                record["station_class"], record["free_class"],
                record["station_min_speed"], record["free_min_speed"],
                fmt(record["drift_start"]), fmt(record["drift_end"])))
            class_counts["%s/%s" % (record["station_class"], record["free_class"])] += 1
        station_min = min(record["station_radius"] for record in scored)
        free_min = min(record["free_radius"] for record in scored)
        lines.append(
            "direction %s: scored %d, excluded %d; pool-min station radius %s (%.3f mm);"
            " pool-min free radius %s (%.3f mm)" % (
                direction, len(scored), len(excluded),
                fmt(station_min), 100.0 * station_min, fmt(free_min), 100.0 * free_min))
        pool_scored.extend(scored)
        pool_excluded += len(excluded)

    if not pool_scored:
        die(["no scorable candidates in either direction"])
    pool_station_min = min(record["station_radius"] for record in pool_scored)
    pool_free_min = min(record["free_radius"] for record in pool_scored)
    ratio = pool_station_min / HOLD_RADIUS
    if ratio >= 10.0:
        branch = "D2 as-predicted branch (>= 10x)"
    elif ratio >= 3.0:
        branch = "D2 READ-BEFORE-STAGING branch (3-10x): first question symmetry or capability"
    else:
        branch = "D2 UNEXPECTED NEAR-PASS branch (< 3x): read before any staging"
    passing = [record for record in pool_scored if record["station_radius"] <= HOLD_RADIUS]
    lines.append("")
    lines.append("POOL: scored %d, excluded %d" % (len(pool_scored), pool_excluded))
    lines.append("min-speed classification (station/free windows): %s" % ", ".join(
        "%s %d" % (name, class_counts[name]) for name in sorted(class_counts)))
    lines.append("pool-min station radius: %s normalized (%.3f mm) = %.2fx the 0.3 mm demand -> %s" % (
        fmt(pool_station_min), 100.0 * pool_station_min, ratio, branch))
    lines.append("pool-min free radius: %s normalized (%.3f mm); station/free gap: %s" % (
        fmt(pool_free_min), 100.0 * pool_free_min,
        "free < station: the pool stops somewhere but cannot place the apex at the station"
        if pool_free_min < pool_station_min else "free = station: the pool cannot stop anywhere"))
    lines.append("D1-relevant: candidates holding 0.3 mm for 50 deg at the station: %d%s" % (
        len(passing), "" if not passing else " (%s)"
        % ", ".join("%s/%s" % (r["direction"], r["candidate_id"]) for r in passing)))
    lines.append("witness: every row reproduced recorded error_1..3 at recorded phase_1..3_deg"
                 " within %g normalized (fail-closed)" % REPRO_TOL)
    report = "\n".join(lines) + "\n"
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
