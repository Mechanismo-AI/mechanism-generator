"""Generate, run and compare a small frozen corpus of feasible three-pose tasks.

The original four-case benchmark is unchanged. This corpus separates development
from reserved evaluation by seed and file. Reference witnesses are stored in
separate files and are never loaded by the solver runner.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np

_spec = importlib.util.spec_from_file_location("pose_benchmark_reference", Path(__file__).with_name("benchmark_pose.py"))
benchmark = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(benchmark)

CORPUS_VERSION = "pose-corpus-v1"
SPLIT_SEEDS = {"development": 731204, "evaluation": 902617}
CASES_PER_SPLIT = 8
INITIALIZER_FIELDS = (
    "method", "enabled", "requested_samples", "requested_seed_count", "attempted_samples", "finite_dyads",
    "within_search_bounds", "full_cycle_robust_crank_shortest", "branch_and_order_consistent",
    "transmission_selection_floors", "returned_seeds", "evaluated_seed_count", "refined_candidate_count",
    "generation_runtime_seconds", "verification_runtime_seconds", "refinement_runtime_seconds", "source_sha256",
    "nominal_samples", "tolerance_samples", "nominal_returned_seeds", "tolerance_returned_seeds",
    "panel_pivot_pass_count", "panel_screened_count", "panel_passing_count",
)
DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / "examples" / "benchmarks" / CORPUS_VERSION
PROTOCOL = {
    "case_count_per_split": CASES_PER_SPLIT,
    "split_seeds": SPLIT_SEEDS,
    "tolerances": {"mean_position": .05, "maximum_position": .075, "orientation_deg": [2., 2., 2.]},
    "parameter_sampling": {
        "l1": 6., "l2": [1., 2.4], "l3": [4.4, 6.4], "l4": [3.5, 5.8],
        "S_ratio": [.05, .9], "bar_length": [.25, 1.8], "base_angle_rad": [-math.pi, math.pi],
        "assembly_branch": "Alternating +1/-1 by case index; four cases of each per split",
        "phases_rad": "Three uniform samples in [0,2pi), sorted; reject cyclic gaps outside [45,180] degrees",
        "translation": "Uniform over translations fitting every requested point inside x=[-6.8,.8], y=[1.2,6.8]",
    },
    "generation_filters": {
        "full_cycle_assembly": True, "grashof": True, "crank_strictly_shortest": True,
        "minimum_full_cycle_transmission_deg": 20.,
        "minimum_pairwise_target_distance": .75,
        "maximum_pairwise_target_distance_range": [2.5, 5.75],
        "maximum_target_width": 6.6, "maximum_target_height": 5.2,
        "minimum_coupler_orientation_span_deg": 8.,
        "reference_in_fixed_and_variable_solver_design_bounds": True,
    },
    "rounding": {"parameters_and_phases_decimals": 12, "requested_poses_decimals": 10},
    "generator": "Python random.Random with independent split seeds; analytic NumPy circle intersections",
    "selection_policy": "Accept the first eight cases satisfying only declared geometric conditions; never filter by solver outcome",
    "evaluation_policy": "Reserve evaluation outcomes until the implementation is frozen. If outcomes inform changes, treat this split as development and create a fresh evaluation corpus.",
    "scope": "A small constructed corpus, not a representative design population or a statistical guarantee",
}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def case_digest(case):
    return digest_bytes(json_bytes({key: value for key, value in case.items() if key != "case_sha256"}))


def in_design_bounds(parameters, points):
    """Check the documented a4 search bounds, without importing its engine."""
    p = np.asarray(parameters)
    xy = np.asarray(points)
    scale = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2).max()
    centroid = xy.mean(axis=0)
    return bool(.5 * scale < p[0] < 2.5 * scale
                and np.all(.05 * scale < p[1:4]) and np.all(p[1:4] < 3 * scale)
                and 0 < p[5] < 1.5 * scale
                and np.all(np.abs(p[6:8] - centroid) < 3 * scale))


def generate_split(split):
    """Produce tasks and separate feasibility witnesses; no learned model used."""
    rng = random.Random(SPLIT_SEEDS[split])
    cases, references = [], []
    attempts = 0
    while len(cases) < CASES_PER_SPLIT:
        attempts += 1
        if attempts > 100000:
            raise RuntimeError("Declared geometric filters exhausted the generation budget")
        parameters = [6., rng.uniform(1., 2.4), rng.uniform(4.4, 6.4), rng.uniform(3.5, 5.8),
                      rng.uniform(.05, .9), rng.uniform(.25, 1.8), 0., 0., rng.uniform(-math.pi, math.pi)]
        parameters = np.round(parameters, 12).tolist()
        phases = np.round(sorted(rng.uniform(0., 2 * math.pi) for _ in range(3)), 12)
        gaps = np.degrees(np.diff(np.r_[phases, phases[0] + 2 * math.pi]))
        if np.any(gaps < 45.) or np.any(gaps > 180.):
            continue
        cycle = benchmark.full_cycle_checks(parameters)
        if not all(cycle[key] for key in ("full_cycle_assembly", "grashof", "crank_is_strictly_shortest")):
            continue
        if cycle["global_minimum_transmission_deg"] < 20.:
            continue
        branch = 1 if len(cases) % 2 == 0 else -1
        geometry = benchmark.analytic_geometry(parameters, phases, branch)
        points = geometry["points"]
        separations = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
        width, height = np.ptp(points, axis=0)
        angle_span = np.ptp(np.unwrap(np.radians(geometry["orientations_deg"])))
        if (width > 6.6 or height > 5.2 or separations.max() < 2.5 or separations.max() > 5.75
                or separations[np.triu_indices(3, 1)].min() < .75 or math.degrees(angle_span) < 8.):
            continue
        minimum = np.array([rng.uniform(-6.8, .8 - width), rng.uniform(1.2, 6.8 - height)])
        parameters[6:8] = np.round(minimum - points.min(axis=0), 12).tolist()
        geometry = benchmark.analytic_geometry(parameters, phases, branch)
        if not in_design_bounds(parameters, geometry["points"]):
            continue
        identifier = f"{split}-{len(cases) + 1:03d}"
        case = {
            "id": identifier, "split": split,
            "target_points": np.round(geometry["points"], 10).tolist(),
            "target_orientations_deg": np.round(geometry["orientations_deg"], 10).tolist(),
            "tolerances": copy.deepcopy(PROTOCOL["tolerances"]),
            "within_historical_position_box": True,
        }
        case["case_sha256"] = case_digest(case)
        cases.append(case)
        references.append({
            "case_id": identifier, "case_sha256": case["case_sha256"],
            "parameters": dict(zip(benchmark.PARAMETER_NAMES, parameters)),
            "phases_rad": phases.tolist(), "branch_sign": branch,
            "target_minimum_transmission_deg": float(geometry["transmission_deg"].min()),
            **cycle,
        })
    return cases, references, attempts


def corpus_files():
    files, splits = {}, {}
    for split, seed in SPLIT_SEEDS.items():
        cases, references, attempts = generate_split(split)
        task_name, reference_name = f"{split}.tasks.json", f"{split}.references.json"
        files[task_name] = json_bytes({"schema_version": CORPUS_VERSION, "split": split, "cases": cases})
        files[reference_name] = json_bytes({"schema_version": CORPUS_VERSION, "split": split, "references": references})
        splits[split] = {
            "seed": seed, "case_count": len(cases), "generation_attempts": attempts,
            "tasks_file": task_name, "tasks_sha256": digest_bytes(files[task_name]),
            "references_file": reference_name, "references_sha256": digest_bytes(files[reference_name]),
            "cases": [{"id": case["id"], "sha256": case["case_sha256"]} for case in cases],
        }
    files["manifest.json"] = json_bytes({
        "schema_version": CORPUS_VERSION, "protocol": PROTOCOL, "splits": splits,
        "generator_sha256": digest_bytes(Path(__file__).read_bytes()),
        "analytic_evaluator_sha256": digest_bytes(Path(benchmark.__file__).read_bytes()),
        "generation_numpy_version": np.__version__,
    })
    return files


def write_corpus(output):
    files = corpus_files()
    for name, content in files.items():
        path = output / name
        if path.exists() and path.read_bytes() != content:
            raise ValueError("Refusing to replace a frozen corpus; use a new version/output directory")
    output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (output / name).write_bytes(content)
    return files


def load_tasks(corpus, split):
    """Read only the manifest and task file, never the reference witness file."""
    manifest_bytes = (corpus / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest["schema_version"] != CORPUS_VERSION:
        raise ValueError("Unsupported corpus version")
    metadata = manifest["splits"][split]
    raw = (corpus / f"{split}.tasks.json").read_bytes()
    if digest_bytes(raw) != metadata["tasks_sha256"]:
        raise ValueError("Task file does not match its frozen SHA256")
    content = json.loads(raw)
    cases = content["cases"]
    expected = {case["id"]: case["sha256"] for case in metadata["cases"]}
    if content["split"] != split or len(cases) != metadata["case_count"] or len(expected) != len(cases):
        raise ValueError("Corpus count/split mismatch")
    for case in cases:
        if case["split"] != split or case_digest(case) != case["case_sha256"] or expected.get(case["id"]) != case["case_sha256"]:
            raise ValueError("Case hash or split mismatch")
        if case["tolerances"] != PROTOCOL["tolerances"]:
            raise ValueError("Unexpected predeclared success thresholds")
    return cases, manifest, digest_bytes(manifest_bytes)


def solver_command(case, args, output):
    command = benchmark.build_command(case, "pose", args.models_directory.resolve(), output, args.budget, args.seed)
    command[0] = str(args.engine_python)
    if args.initializer_samples is not None:
        command.extend(["--pose_dyad_samples", str(args.initializer_samples)])
    if args.initializer_seeds is not None:
        command.extend(["--pose_dyad_seed_count", str(args.initializer_seeds)])
    if getattr(args, "tolerance_samples", None) is not None:
        command.extend(["--pose_tolerance_samples", str(args.tolerance_samples)])
    return command


def run_one(case, args, output):
    output.mkdir(parents=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", MPLCONFIGDIR=str(output / "mpl"))
    command = solver_command(case, args, output / "results")
    started = time.perf_counter()
    result = {"case_id": case["id"], "case_sha256": case["case_sha256"], "status": "failed"}
    try:
        with (output / "engine.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        if completed.returncode:
            result["failure"] = f"engine_exit_{completed.returncode}"
            return result
        manifests = list((output / "results").rglob("run_manifest.json"))
        if len(manifests) != 1:
            raise ValueError("Expected one run manifest")
        manifest = json.loads(manifests[0].read_text())
        if manifest.get("run_status") != "completed" or len(manifest["targets"]) != 1:
            raise ValueError("Expected one completed task")
        reports = [path for path in manifests[0].parent.rglob("all_candidates.csv") if path.parent.parent == manifests[0].parent]
        if len(reports) != 1:
            raise ValueError("Expected one portfolio report")
        scores = benchmark.read_scores(reports[0], case)
        selected = benchmark.read_scores(reports[0].with_name("selected_candidates.csv"), case)
        initializer = manifest["targets"][0].get("pose_initialization")
        result.update({
            "status": "completed", "selected": benchmark.summarize_scores(selected),
            "all_candidates_diagnostic": benchmark.summarize_scores(scores),
            "all_candidate_scores": scores, "selected_candidate_scores": selected,
            "model_identity": [{key: model[key] for key in ("role", "sha256")} for model in manifest["models"]],
            "engine_identity": {key: manifest[key] for key in ("variant", "script_sha256", "engine_sha256", "orientation_sha256", "pose_initialization_sha256", "panel_screening_sha256") if key in manifest},
            "effective_initializer_arguments": {key: manifest["arguments"][key] for key in ("pose_dyad_samples", "pose_dyad_seed_count", "pose_tolerance_samples") if key in manifest["arguments"]},
            "initializer_diagnostics": {key: initializer[key] for key in INITIALIZER_FIELDS if key in initializer} if initializer is not None else None,
        })
    except subprocess.TimeoutExpired:
        result["failure"] = "timeout"
    except (ValueError, KeyError, OSError):
        result["failure"] = "invalid_or_missing_result"
    finally:
        result["wall_runtime_seconds"] = time.perf_counter() - started
    return result


def summarize_runs(runs, requested_count):
    completed = [run for run in runs if run["status"] == "completed"]
    successes = sum(run["selected"]["pose_match_and_engine_eligible_count"] > 0 for run in completed)
    return {
        "requested_cases": requested_count, "attempted_cases": len(runs), "completed_cases": len(completed),
        "failed_cases": len(runs) - len(completed), "selected_pose_success_cases": successes,
        "selected_pose_success_fraction": successes / requested_count,
        "all_candidates": sum(run["all_candidates_diagnostic"]["candidate_count"] for run in completed),
        "selected_candidates": sum(run["selected"]["candidate_count"] for run in completed),
        "total_wall_runtime_seconds": sum(run["wall_runtime_seconds"] for run in runs),
    }


def run_corpus(args):
    cases, manifest, manifest_sha = load_tasks(args.corpus, args.split)
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("Output directory must be new or empty")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "pose-corpus-run-1", "corpus_version": CORPUS_VERSION,
        "corpus_manifest_sha256": manifest_sha, "task_file_sha256": manifest["splits"][args.split]["tasks_sha256"],
        "case_hashes": manifest["splits"][args.split]["cases"], "split": args.split,
        "engine_label": args.label, "run_status": "partial", "seed": args.seed,
        "budget": args.budget, "optimizer_budget_settings": benchmark.BUDGETS[args.budget],
        "requested_initializer_settings": {"pose_dyad_samples": args.initializer_samples, "pose_dyad_seed_count": args.initializer_seeds,
                                           "pose_tolerance_samples": getattr(args, "tolerance_samples", None)},
        "success_thresholds": PROTOCOL["tolerances"],
        "success_definition": "At least one selected, engine-eligible candidate independently meets both position and orientation tolerances and has full-cycle assembly",
        "common_configuration": {"model_roles": ["balanced", "path", "transmission"], "profile_matrix": "paired", "branches": "both", "phase_mode": "ordered", "device": "cpu", "dtype": "float64", "strict_qualification": True, "portfolio_guarantee_fixed_count": 0},
        "requested_model_identity": [{"role": role, "sha256": digest_bytes((args.models_directory / f"{role}.safetensors").read_bytes())} for role in ("balanced", "path", "transmission")],
        "evaluator_sha256": digest_bytes(Path(benchmark.__file__).read_bytes()),
        "runner_sha256": digest_bytes(Path(__file__).read_bytes()), "numpy_version": np.__version__,
        "limitations": [PROTOCOL["scope"], PROTOCOL["evaluation_policy"],
                        "Equal configured optimizer steps are not equal total compute: initializer samples and additional refinement seeds can add work",
                        "Engine labels describe intent; use recorded source/model hashes to establish implementation identity",
                        "Wall times are descriptive; hardware, concurrent work and initialization affect them",
                        "No strength, collision, manufacturability or physical validation"],
        "runs": [],
    }

    def save():
        report["summary"] = summarize_runs(report["runs"], len(cases))
        (args.output / "report.json").write_bytes(json_bytes(report))

    save()
    for case in cases:
        print(f"Running {args.label}: {case['id']}", flush=True)
        report["runs"].append(run_one(case, args, args.output.resolve() / "runs" / case["id"]))
        save()
    report["run_status"] = "completed"
    completed = [run for run in report["runs"] if run["status"] == "completed"]
    for identity in ("model_identity", "engine_identity"):
        report[f"consistent_{identity}"] = len({json.dumps(run[identity], sort_keys=True) for run in completed}) == 1 if completed else None
    save()
    print(json.dumps(report["summary"], indent=2))
    return int(report["summary"]["failed_cases"] > 0)


def compare_reports(baseline, candidate):
    """Refuse comparisons that changed tasks, thresholds, models or step budgets."""
    required_equal = ("corpus_version", "corpus_manifest_sha256", "task_file_sha256", "case_hashes", "split",
                      "seed", "optimizer_budget_settings", "success_thresholds", "common_configuration", "evaluator_sha256", "requested_model_identity")
    for key in required_equal:
        if baseline[key] != candidate[key]:
            raise ValueError(f"Cannot compare reports with different {key}")
    if any(report["run_status"] != "completed" for report in (baseline, candidate)):
        raise ValueError("Both reports must contain all attempted runs before comparison")
    for report in (baseline, candidate):
        expected = {case["id"]: case["sha256"] for case in report["case_hashes"]}
        actual = {run["case_id"]: run["case_sha256"] for run in report["runs"]}
        if actual != expected or len(actual) != len(report["runs"]):
            raise ValueError("Each frozen case must appear exactly once, including failures")
        identities = {json.dumps(run["engine_identity"], sort_keys=True) for run in report["runs"] if run["status"] == "completed"}
        if len(identities) > 1:
            raise ValueError("Engine source changed within a run")
    completed = [run for report in (baseline, candidate) for run in report["runs"] if run["status"] == "completed"]
    if len({json.dumps(run["model_identity"], sort_keys=True) for run in completed}) > 1:
        raise ValueError("Model hashes differ")
    results = {}
    for label, report in (("baseline", baseline), ("candidate", candidate)):
        diagnostics = [run["initializer_diagnostics"] for run in report["runs"] if run.get("initializer_diagnostics") is not None]
        totals = {key: sum(item.get(key, 0) for item in diagnostics) for key in INITIALIZER_FIELDS
                  if key not in ("method", "enabled", "source_sha256")} if diagnostics else None
        results[label] = {"label": report["engine_label"], "summary": report["summary"],
                          "initializer_settings": report["requested_initializer_settings"],
                          "initializer_diagnostic_totals": totals,
                          "engine_identities": [json.loads(value) for value in sorted({json.dumps(run["engine_identity"], sort_keys=True) for run in report["runs"] if run["status"] == "completed"})]}
    return {
        "schema_version": "pose-corpus-comparison-1", "split": baseline["split"],
        "task_file_sha256": baseline["task_file_sha256"], "case_hashes": baseline["case_hashes"],
        "configured_optimizer_budgets_equal": True,
        "equal_total_compute_claimed": False,
        "compute_note": "Initializer work and extra seeds may differ even when optimizer step settings match. Inspect per-run initializer counts and wall times.",
        "requested_model_identity": baseline["requested_model_identity"],
        **results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Create deterministic task/reference files and their frozen hashes")
    generate.add_argument("--output", type=Path, default=DEFAULT_CORPUS)
    run = commands.add_parser("run", help="Run every task in one split; witnesses are never read")
    run.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    run.add_argument("--split", choices=SPLIT_SEEDS, default="development")
    run.add_argument("--models-directory", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--label", required=True, help="Human-readable implementation label; recorded hashes establish identity")
    run.add_argument("--engine-python", type=Path, default=Path(sys.executable), help="Interpreter containing the engine under test; PYTHONPATH is inherited")
    run.add_argument("--budget", choices=benchmark.BUDGETS, default="standard")
    run.add_argument("--seed", type=int, default=101)
    run.add_argument("--timeout", type=float, default=900., help="Maximum seconds per task")
    run.add_argument("--initializer-samples", type=int, help="Explicit source-engine dyad sample count; omitted for a4")
    run.add_argument("--initializer-seeds", type=int, help="Explicit source-engine dyad seed count; omitted for a4")
    run.add_argument("--tolerance-samples", type=int, help="Explicit angular-tolerance dyad sample count; omitted for older engines")
    compare = commands.add_parser("compare", help="Compare two completed runs against the same frozen task split")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            write_corpus(args.output)
            print(f"Wrote {CASES_PER_SPLIT} development and {CASES_PER_SPLIT} reserved-evaluation cases with frozen hashes.")
            return 0
        if args.command == "run":
            if not math.isfinite(args.timeout) or args.timeout <= 0:
                parser.error("--timeout must be positive and finite")
            if any(value is not None and value < 0 for value in (args.initializer_samples, args.initializer_seeds, args.tolerance_samples)):
                parser.error("Initializer counts must be nonnegative")
            return run_corpus(args)
        result = compare_reports(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(json_bytes(result))
        print(f"Comparison: {args.output}")
        return 0
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
