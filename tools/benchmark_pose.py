"""Small, reproducible position-versus-pose experiment with analytic references.

These four constructed cases are a regression benchmark, not a representative
sample of mechanism design problems. Both search modes are scored against the
same requested positions AND orientations by the NumPy evaluator in this file.
Reference parameters establish feasibility and are never supplied to the search.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np


PARAMETER_NAMES = ("l1", "l2", "l3", "l4", "S_ratio", "bar_length", "base_x", "base_y", "base_angle")
REFERENCES = (
    ("wide_sweep", [6, 2, 5, 4, .45, 1, -3, 2.5, .15], [25, 110, 245], 1),
    ("rotated_return", [6, 1.5, 5, 4.5, .65, .8, -3.5, 0, -.45], [15, 145, 285], -1),
    ("offset_tool", [6, 2.4, 5.7, 4.1, .25, 1.6, -2, 1, 1.1], [40, 165, 295], 1),
    ("angle_wrap", [6, 1.8, 4.8, 4.8, .7, .5, 1, 3, 2.5], [10, 130, 250], -1),
)
TOLERANCES = {"mean_position": .05, "maximum_position": .075, "orientation_deg": [2., 2., 2.]}
# Pin budgets here so a later change in solver defaults cannot silently change
# the amount of optimization in an old experiment. All counts apply to BOTH modes.
BUDGETS = {
    "quick": {
        "adam_accuracy_steps": 10, "adam_tradeoff_steps": 10, "lbfgs_steps": 3,
        "portfolio_bridge_accuracy_steps": 5, "portfolio_bridge_tradeoff_steps": 5,
        "portfolio_bridge_lbfgs_steps": 2, "portfolio_release_accuracy_steps": 5,
        "portfolio_release_tradeoff_steps": 5, "portfolio_release_lbfgs_steps": 2,
        "seed_phase_steps": 181, "optimization_global_steps": 91, "verification_steps": 721,
        "portfolio_fixed_seed_count": 2, "portfolio_release_seed_count": 2,
    },
    "standard": {
        "adam_accuracy_steps": 60, "adam_tradeoff_steps": 100, "lbfgs_steps": 20,
        "portfolio_bridge_accuracy_steps": 30, "portfolio_bridge_tradeoff_steps": 60,
        "portfolio_bridge_lbfgs_steps": 15, "portfolio_release_accuracy_steps": 20,
        "portfolio_release_tradeoff_steps": 50, "portfolio_release_lbfgs_steps": 12,
        "seed_phase_steps": 721, "optimization_global_steps": 181, "verification_steps": 1441,
        "portfolio_fixed_seed_count": 3, "portfolio_release_seed_count": 3,
    },
}


def circular_error_deg(actual, requested):
    """Signed shortest directed angular residual, in [-180, 180)."""
    return (np.asarray(actual) - np.asarray(requested) + 180.) % 360. - 180.


def analytic_geometry(parameters, phases_rad, branch_sign):
    """Solve circle intersections independently of the torch engine.

    Local O2=(0,0), O4=(l1,0); theta is measured about O2 in this
    local frame. Tool origin P=A+s(B-A)+bar*rotate90(unit(B-A)); its
    directed x axis is A->B. Invalid intersections remain NaN, never clamped
    into plausible geometry. Branch sign is relative to directed O4->A.
    """
    p = np.asarray(parameters, dtype=float)
    theta = np.asarray(phases_rad, dtype=float)
    if p.shape != (9,) or theta.ndim != 1 or not np.isfinite(p).all() or not np.isfinite(theta).all():
        raise ValueError("Expected nine finite parameters and a finite phase vector")
    if np.any(p[:4] <= 0) or branch_sign not in (-1, 1):
        raise ValueError("Link lengths must be positive and branch sign must be -1 or 1")
    l1, l2, l3, l4, s, bar, base_x, base_y, angle = p
    a = l2 * np.column_stack((np.cos(theta), np.sin(theta)))
    o4 = np.array([l1, 0.])
    delta = a - o4
    distance = np.linalg.norm(delta, axis=1)
    valid = (distance > 1e-12) & (distance <= l3 + l4) & (distance >= abs(l3 - l4))
    b = np.full_like(a, np.nan)
    unit = delta[valid] / distance[valid, None]
    along = (l4 * l4 - l3 * l3 + distance[valid] ** 2) / (2 * distance[valid])
    height = np.sqrt(np.maximum(0., l4 * l4 - along ** 2))
    b[valid] = o4 + along[:, None] * unit + branch_sign * height[:, None] * np.column_stack((-unit[:, 1], unit[:, 0]))
    coupler = b - a
    point = a + s * coupler + bar * np.column_stack((-coupler[:, 1], coupler[:, 0])) / l3
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    translation = np.array([base_x, base_y])
    coupler_world = coupler @ rotation.T
    # The acute transmission angle is determined by the triangle's side lengths.
    cosine = (l3 * l3 + l4 * l4 - distance ** 2) / (2 * l3 * l4)
    transmission = np.degrees(np.arccos(np.clip(np.abs(cosine), 0., 1.)))
    transmission[~valid] = 0.
    return {
        "a": a @ rotation.T + translation, "b": b @ rotation.T + translation,
        "o2": translation, "o4": o4 @ rotation.T + translation,
        "points": point @ rotation.T + translation,
        "orientations_deg": np.degrees(np.arctan2(coupler_world[:, 1], coupler_world[:, 0])),
        "valid": valid, "transmission_deg": transmission,
    }


def full_cycle_checks(parameters):
    """Analytic assembly bounds and minimum acute transmission over a full turn.

    O4--A distance spans [abs(l1-l2), l1+l2]. Transmission cosine is
    monotone in squared distance, so its greatest absolute value occurs at
    one of these endpoints. This avoids missing a narrow failure on a grid.
    These are kinematic checks; they do not certify strength or collision safety.
    """
    l1, l2, l3, l4 = np.asarray(parameters, dtype=float)[:4]
    near, far = abs(l1 - l2), l1 + l2
    assembly = bool(near > 1e-12 and near >= abs(l3 - l4) and far <= l3 + l4)
    cosines = (l3 * l3 + l4 * l4 - np.array([near, far]) ** 2) / (2 * l3 * l4)
    angle = float(np.degrees(np.arccos(np.clip(np.max(np.abs(cosines)), 0., 1.)))) if assembly else 0.
    links = sorted([l1, l2, l3, l4])
    return {
        "full_cycle_assembly": assembly,
        "global_minimum_transmission_deg": angle,
        "grashof": bool(links[0] + links[3] <= links[1] + links[2]),
        "crank_is_strictly_shortest": bool(l2 < min(l1, l3, l4)),
    }


def make_cases():
    cases = []
    for name, parameters, phases_deg, branch in REFERENCES:
        phases = np.radians(phases_deg)
        geometry = analytic_geometry(parameters, phases, branch)
        assert geometry["valid"].all()
        cases.append({
            "id": name,
            "target_points": geometry["points"].tolist(),
            "target_orientations_deg": geometry["orientations_deg"].tolist(),
            "tolerances": dict(TOLERANCES),
            "within_historical_position_box": bool(
                np.all((-7 < geometry["points"][:, 0]) & (geometry["points"][:, 0] < 1))
                and np.all((1 < geometry["points"][:, 1]) & (geometry["points"][:, 1] < 7))),
            "reference": {
                "parameters": dict(zip(PARAMETER_NAMES, parameters)),
                "phases_rad": phases.tolist(), "branch_sign": branch,
                "target_minimum_transmission_deg": float(geometry["transmission_deg"].min()),
                **full_cycle_checks(parameters),
            },
        })
    return cases


def score_candidate(row, case):
    """Recompute result quality without trusting the engine's error columns."""
    parameters = [float(row[name]) for name in PARAMETER_NAMES]
    phases = [float(row[f"phase_{i}_rad"]) for i in (1, 2, 3)]
    geometry = analytic_geometry(parameters, phases, float(row["branch_sign"]))
    cycle = full_cycle_checks(parameters)
    valid = bool(geometry["valid"].all())
    result = {
        "candidate_id": row["candidate_id"],
        "engine_selection_eligible": str(row.get("selection_eligible", "")).lower() == "true",
        "target_assembly": valid, **cycle,
        "mean_position_error": None, "maximum_position_error": None,
        "mean_orientation_error_deg": None, "maximum_orientation_error_deg": None,
        "orientation_errors_deg": None, "joint_normalized_error": None,
        "pose_within_tolerances": False,
        "target_minimum_transmission_deg": float(geometry["transmission_deg"].min()),
    }
    if valid:
        position = np.linalg.norm(geometry["points"] - case["target_points"], axis=1)
        angular = np.abs(circular_error_deg(geometry["orientations_deg"], case["target_orientations_deg"]))
        tolerance = case["tolerances"]
        joint = max(float(position.mean()) / tolerance["mean_position"],
                    float(position.max()) / tolerance["maximum_position"],
                    float(np.max(angular / tolerance["orientation_deg"])))
        result.update({
            "mean_position_error": float(position.mean()), "maximum_position_error": float(position.max()),
            "mean_orientation_error_deg": float(angular.mean()), "maximum_orientation_error_deg": float(angular.max()),
            "orientation_errors_deg": angular.tolist(), "joint_normalized_error": joint,
            "pose_within_tolerances": bool(joint <= 1. + 1e-9 and cycle["full_cycle_assembly"]),
        })
    return result


def summarize_scores(scores):
    valid = [record for record in scores if record["joint_normalized_error"] is not None]
    return {
        "candidate_count": len(scores),
        "engine_eligible_count": sum(record["engine_selection_eligible"] for record in scores),
        "pose_match_count": sum(record["pose_within_tolerances"] for record in scores),
        "pose_match_and_engine_eligible_count": sum(record["pose_within_tolerances"] and record["engine_selection_eligible"] for record in scores),
        "best_by_joint_error": min(valid, key=lambda record: record["joint_normalized_error"]) if valid else None,
    }


def build_command(case, mode, models, output, budget, seed):
    command = [sys.executable, "-m", "mechanism_generator.engine", "--models-directory", str(models),
               "--targets", *[repr(value) for xy in case["target_points"] for value in xy],
               "--model_roles", "balanced", "path", "transmission", "--profile_matrix", "paired",
               "--branches", "both", "--phase_mode", "ordered", "--seed", str(seed),
               "--device", "cpu", "--dtype", "float64", "--headless", "--no_plots",
               "--strict_qualification", "--portfolio_guarantee_fixed_count", "0",
               "--max_mean_error", str(case["tolerances"]["mean_position"]),
               "--max_point_error", str(case["tolerances"]["maximum_position"]),
               "--no_contribution_bundle", "--output_root", str(output)]
    for option, value in BUDGETS[budget].items():
        command.extend([f"--{option}", str(value)])
    if mode == "pose":
        command.extend(["--target_orientations_deg", *map(repr, case["target_orientations_deg"]),
                        "--orientation_tolerances_deg", *map(str, case["tolerances"]["orientation_deg"])])
    elif mode != "position":
        raise ValueError("Mode must be position or pose")
    return command


def read_scores(path, case):
    if not path.exists():
        raise ValueError("Expected candidate report is missing")
    with path.open(encoding="utf-8", newline="") as stream:
        return [score_candidate(row, case) for row in csv.DictReader(stream)]


def run_case(case, mode, models, output, budget, seed, timeout):
    output.mkdir(parents=True)
    command = build_command(case, mode, models, output / "results", budget, seed)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", MPLCONFIGDIR=str(output / "mpl"))
    started = time.perf_counter()
    result = {"case_id": case["id"], "mode": mode, "status": "failed"}
    try:
        with (output / "engine.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        if completed.returncode:
            result["failure"] = f"engine_exit_{completed.returncode}"
            return result
        manifests = list((output / "results").rglob("run_manifest.json"))
        if len(manifests) != 1:
            raise ValueError("Expected exactly one run manifest")
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        if manifest.get("run_status") != "completed" or len(manifest["targets"]) != 1:
            raise ValueError("Expected one completed target")
        reports = list(manifests[0].parent.rglob("all_candidates.csv"))
        # Individual optimization stages also write all_candidates.csv; choose
        # the portfolio report paired with selected_candidates at target level.
        reports = [path for path in reports if path.parent.parent == manifests[0].parent]
        if len(reports) != 1:
            raise ValueError("Expected one portfolio candidate report")
        scores = read_scores(reports[0], case)
        selected = read_scores(reports[0].with_name("selected_candidates.csv"), case)
        result.update({
            "status": "completed", "selected": summarize_scores(selected),
            "all_candidates_diagnostic": summarize_scores(scores),
            "all_candidate_scores": scores, "selected_candidate_scores": selected,
            "model_identity": [{"role": model["role"], "sha256": model["sha256"]} for model in manifest["models"]],
            "engine_identity": {key: manifest[key] for key in ("variant", "script_sha256", "engine_sha256", "orientation_sha256") if key in manifest},
        })
    except subprocess.TimeoutExpired:
        result["failure"] = "timeout"
    except (ValueError, KeyError, OSError):
        result["failure"] = "invalid_or_missing_result"
    finally:
        result["wall_runtime_seconds"] = time.perf_counter() - started
    return result


def coverage(results, total_cases):
    summary = {}
    for mode in ("position", "pose"):
        runs = [run for run in results if run["mode"] == mode]
        completed = [run for run in runs if run["status"] == "completed"]
        successes = sum(run["selected"]["pose_match_and_engine_eligible_count"] > 0 for run in completed)
        summary[mode] = {"requested_cases": total_cases, "attempted_cases": len(runs),
                         "completed_cases": len(completed), "selected_pose_success_cases": successes,
                         "selected_pose_success_fraction": successes / total_cases,
                         "total_wall_runtime_seconds": sum(run["wall_runtime_seconds"] for run in runs)}
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-directory", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New/empty directory for reports and local solver logs")
    parser.add_argument("--budget", choices=BUDGETS, default="standard")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--cases", nargs="+", choices=[case[0] for case in REFERENCES])
    parser.add_argument("--timeout", type=float, default=900., help="Maximum seconds per solver run")
    parser.add_argument("--generate-only", action="store_true", help="Write analytic reference cases without running the engine")
    args = parser.parse_args(argv)
    if args.timeout <= 0 or not math.isfinite(args.timeout):
        parser.error("--timeout must be positive and finite")
    if not args.generate_only and args.models_directory is None:
        parser.error("--models-directory is required unless --generate-only is used")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("--output must be new or empty")
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [case for case in make_cases() if not args.cases or case["id"] in args.cases]
    report = {
        "schema_version": "pose-benchmark-1", "scope": "Four constructed development probes; not held-out cases or a broad performance estimate",
        "tool_frame": "Origin P; directed +x parallel to A->B; world-frame angles in degrees",
        "success_definition": "At least one selected, engine-eligible candidate independently meets BOTH position and orientation tolerances and has full-cycle assembly",
        "limitations": ["One seed per invocation; run additional seeds to study variability",
                        "No load, collision, manufacturability or physical validation",
                        "Same configured budgets, not equal wall time or objective evaluation counts",
                        "Reference mechanisms establish feasibility; search does not receive their parameters",
                        "All requested positions lie strictly inside the historical x=(-7,1), y=(1,7) box; orientations were not network inputs",
                        "offset_tool refers to the coupler point's geometric offset; no independent tool mounting angle is supported",
                        "Transmission and engine qualification are reported separately from pose matching"],
        "seed": args.seed, "budget": args.budget, "budget_settings": BUDGETS[args.budget],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "numpy_version": np.__version__, "cases": cases, "runs": [],
    }
    destination = args.output / "benchmark.json"

    def save():
        report["coverage"] = coverage(report["runs"], len(cases))
        destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

    save()
    if not args.generate_only:
        for case in cases:
            for mode in ("position", "pose"):
                print(f"Running {case['id']} / {mode}", flush=True)
                result = run_case(case, mode, args.models_directory.resolve(), args.output.resolve() / "runs" / case["id"] / mode,
                                  args.budget, args.seed, args.timeout)
                report["runs"].append(result)
                save()
                print(f"  {result['status']}: {result['wall_runtime_seconds']:.1f}s", flush=True)
        completed = [run for run in report["runs"] if run["status"] == "completed"]
        identities = {json.dumps(run["model_identity"], sort_keys=True) for run in completed}
        report["consistent_model_identity"] = len(identities) == 1 if completed else None
        engine_identities = {json.dumps(run["engine_identity"], sort_keys=True) for run in completed}
        report["consistent_engine_identity"] = len(engine_identities) == 1 if completed else None
        save()
    print(f"Benchmark report: {destination}")
    return int(any(run["status"] != "completed" for run in report["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
