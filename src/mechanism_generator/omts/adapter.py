"""Prepare a narrow, explicitly checked OMTS subset for the external R2.5c engine.

Every operational field is mapped, checked against a fixed supported value, or
rejected. Annotation fields do not influence synthesis. No optimizer is run here.
"""

from __future__ import annotations

import csv
import hashlib
import json
from importlib.resources import files
from pathlib import Path

from .validation import DocumentError, require_valid


class UnsupportedFeature(DocumentError):
    """Valid OMTS content that this adapter cannot faithfully implement."""


def capabilities() -> dict:
    return json.loads(files(__package__).joinpath("r25c_capabilities.json").read_text(encoding="utf-8"))


def _only(obj: dict, names: str, path: str) -> None:
    unsupported = sorted(set(obj) - set(names.split()))
    if unsupported:
        raise UnsupportedFeature(f"{path}.{unsupported[0]}: unsupported by the R2.5c adapter; remove it or use another implementation.")


def _fixed(obj: dict, key: str, expected, path: str):
    value = obj.get(key, expected)
    if value != expected:
        raise UnsupportedFeature(f"{path}.{key}: this adapter requires {expected!r}, received {value!r}.")
    return value


def _choice(obj: dict, key: str, default, choices, path: str):
    value = obj.get(key, default)
    if value not in choices:
        raise UnsupportedFeature(f"{path}.{key}: supported values are {choices!r}.")
    return value


def _options(task: dict, index: int, outputs: dict) -> dict:
    path = f"$.tasks[{index}]"
    _only(task, "id name description motion mechanism_search requirements search", path)
    motion = task["motion"]
    _only(motion, "mode order_policy cycle targets", path + ".motion")
    _fixed(motion, "mode", "cyclic", path + ".motion")
    phase_mode = _choice(motion, "order_policy", "unordered", ("ordered", "unordered"), path + ".motion")
    cycle = motion.get("cycle", {})
    _only(cycle, "phase_start phase_end direction independent_variable", path + ".motion.cycle")
    for key, value in dict(phase_start=0, phase_end=360, direction="positive", independent_variable="phase").items():
        _fixed(cycle, key, value, path + ".motion.cycle")
    targets = motion["targets"]
    if len(targets) != 3:
        raise UnsupportedFeature(f"{path}.motion.targets: exactly three targets are required.")
    tolerances = []
    for i, target in enumerate(targets):
        tp = f"{path}.motion.targets[{i}]"
        _only(target, "id name position occurrence tolerance mode notes", tp)
        _fixed(target, "mode", "hard", tp)
        occurrence = target.get("occurrence", {})
        _only(occurrence, "free order_index", tp + ".occurrence")
        _fixed(occurrence, "free", True, tp + ".occurrence")
        tolerance = target.get("tolerance", {})
        _only(tolerance, "position", tp + ".tolerance")
        tolerances.append(tolerance.get("position"))
    if len(set(tolerances)) != 1:
        raise UnsupportedFeature(f"{path}.motion.targets: position tolerances must be identical on all targets, or omitted on all targets.")
    if phase_mode == "ordered" and "order_index" in targets[0].get("occurrence", {}):
        targets = sorted(targets, key=lambda target: target["occurrence"]["order_index"])

    search = task["mechanism_search"]
    sp = path + ".mechanism_search"
    _only(search, "allowed_topologies max_dof max_actuators ground_link assembly_branches profiles profile_matrix portfolio", sp)
    _fixed(search, "allowed_topologies", ["four_bar"], sp)
    _fixed(search, "max_dof", 1, sp)
    _fixed(search, "max_actuators", 1, sp)
    if set(search.get("profiles", ["accuracy", "balanced", "transmission"])) != {"accuracy", "balanced", "transmission"}:
        raise UnsupportedFeature(f"{sp}.profiles: all three profiles (accuracy, balanced, transmission) are required.")
    branches = search.get("assembly_branches", ["open"])
    if not branches:
        raise UnsupportedFeature(f"{sp}.assembly_branches: at least one branch is required.")
    branch = "both" if len(branches) == 2 else ("negative" if branches[0] == "open" else "positive")
    ground = search.get("ground_link", {"mode": "portfolio", "fixed_values": [6.0]})
    _only(ground, "mode fixed_values trust_fraction release", sp + ".ground_link")
    _fixed(ground, "mode", "portfolio", sp + ".ground_link")
    fixed_values = ground.get("fixed_values", [6.0])
    if len(fixed_values) != 1:
        raise UnsupportedFeature(f"{sp}.ground_link.fixed_values: exactly one fixed seed value is supported.")
    portfolio = search.get("portfolio", {})
    pp = sp + ".portfolio"
    _only(portfolio, "fixed_seed_count bridge_profile_matrix bridge_perturbations trust_fraction release_seed_count skip_release guarantee_fixed_count", pp)
    # Reserved fixed references can bypass eligibility in the historical engine.
    _fixed(portfolio, "guarantee_fixed_count", 0, pp)
    trust = portfolio.get("trust_fraction", ground.get("trust_fraction", 0.25))
    if "trust_fraction" in ground and trust != ground["trust_fraction"]:
        raise UnsupportedFeature(f"{pp}.trust_fraction conflicts with ground_link.trust_fraction.")
    skip_release = portfolio.get("skip_release", not ground.get("release", True))
    if "release" in ground and skip_release == ground["release"]:
        raise UnsupportedFeature(f"{pp}.skip_release conflicts with ground_link.release.")

    requirements = task.get("requirements", {})
    rp = path + ".requirements"
    _only(requirements, "path transmission assembly classification compactness", rp)
    path_req = requirements.get("path", {})
    _only(path_req, "max_mean_error max_point_error shared_mean_allowance shared_point_allowance mode", rp + ".path")
    _fixed(path_req, "mode", "hard", rp + ".path")
    mean_error = path_req.get("max_mean_error", 0.05)
    point_error = path_req.get("max_point_error", 0.075)
    if tolerances[0] is not None:
        point_error = min(point_error, tolerances[0])
    if mean_error <= 0 or point_error <= 0:
        raise UnsupportedFeature(f"{rp}.path: zero absolute error limits disable checks in R2.5c and cannot express exact-match requirements.")
    tx = requirements.get("transmission", {})
    _only(tx, "min_at_targets min_global selection_min_at_targets selection_min_global objective mode", rp + ".transmission")
    _fixed(tx, "mode", "soft", rp + ".transmission")
    _fixed(tx, "objective", "worst_target", rp + ".transmission")
    assembly = requirements.get("assembly", {})
    _only(assembly, "full_cycle_required min_margin mode", rp + ".assembly")
    for key, value in dict(full_cycle_required=True, min_margin=0.0, mode="hard").items():
        _fixed(assembly, key, value, rp + ".assembly")
    classification = requirements.get("classification", {})
    _only(classification, "grashof_required input_link_shortest follower_not_longest mode", rp + ".classification")
    for key, value in dict(grashof_required=True, input_link_shortest=True, mode="hard").items():
        _fixed(classification, key, value, rp + ".classification")
    compactness = requirements.get("compactness", {})
    _only(compactness, "mode", rp + ".compactness")
    _fixed(compactness, "mode", "report_only", rp + ".compactness")

    options = task.get("search", {})
    op = path + ".search"
    _only(options, "implementation_profile seed top_k perturbations_per_model parameter_noise phase_noise", op)
    _fixed(options, "implementation_profile", "r2.5c-fourbar", op)
    top_k = options.get("top_k", outputs.get("top_k", 5))
    if "top_k" in outputs and "top_k" in options and top_k != outputs["top_k"]:
        raise UnsupportedFeature(f"{op}.top_k conflicts with $.outputs.top_k; omit the global value for task-specific counts.")

    flags = {
        "--branches": branch,
        "--phase_mode": phase_mode,
        "--profile_matrix": search.get("profile_matrix", "cross"),
        "--fixed_ground_link_value": fixed_values[0],
        "--portfolio_fixed_seed_count": portfolio.get("fixed_seed_count", 3),
        "--portfolio_bridge_profile_matrix": portfolio.get("bridge_profile_matrix", "paired"),
        "--portfolio_bridge_perturbations": portfolio.get("bridge_perturbations", 0),
        "--portfolio_l1_trust_fraction": trust,
        "--portfolio_release_seed_count": portfolio.get("release_seed_count", 3),
        "--portfolio_guarantee_fixed_count": 0,
        "--max_mean_error": mean_error,
        "--max_point_error": point_error,
        "--shared_mean_allowance": path_req.get("shared_mean_allowance", 0.02),
        "--shared_point_allowance": path_req.get("shared_point_allowance", 0.05),
        "--target_transmission_deg": tx.get("min_at_targets", 35),
        "--global_transmission_floor_deg": tx.get("min_global", 15),
        "--minimum_target_transmission": tx.get("selection_min_at_targets", 15),
        "--minimum_global_transmission": tx.get("selection_min_global", 10),
        "--seed": options.get("seed", 101),
        "--top_k": top_k,
        "--perturbations_per_model": options.get("perturbations_per_model", 0),
        "--parameter_noise": options.get("parameter_noise", 0.18),
        "--phase_noise_deg": options.get("phase_noise", 4),
        "--device": "cpu",
        "--run_label": task["id"],
    }
    arguments = [str(value) for pair in flags.items() for value in pair]
    arguments.extend(["--headless", "--strict_qualification"])
    if "png" not in outputs.get("formats", ["json", "csv", "npz"]):
        arguments.append("--no_plots")
    if skip_release:
        arguments.append("--portfolio_skip_release")
    if classification.get("follower_not_longest", False):
        arguments.append("--enforce_follower_not_longest")
    return {
        "task_id": task["id"],
        "target_ids": [target["id"] for target in targets],
        "positions": [target["position"] for target in targets],
        "targets_file": f"tasks/task-{index + 1:03d}/targets.csv",
        "output_root": f"results/task-{index + 1:03d}",
        "arguments": arguments,
    }


def prepare_plan(data: dict) -> dict:
    """Validate the whole task set before preparing any output or command."""
    require_valid(data)
    _only(data, "spec version task_set_id name description capabilities_required unsupported_feature_policy units coordinate_system tasks outputs metadata", "$")
    _fixed(data, "unsupported_feature_policy", "error", "$")
    profile = capabilities()
    unknown = sorted(set(data.get("capabilities_required", [])) - set(profile["supports"]))
    if unknown:
        raise UnsupportedFeature(f"$.capabilities_required: unsupported capabilities: {', '.join(unknown)}")
    units = data["units"]
    _only(units, "length angle time mass force torque", "$.units")
    for key, value in dict(length="normalized", angle="deg", time="s", mass="kg", force="N", torque="N_m").items():
        _fixed(units, key, value, "$.units")
    frame = data["coordinate_system"]
    _only(frame, "frame_id dimension handedness axes origin_description", "$.coordinate_system")
    _fixed(frame, "dimension", 2, "$.coordinate_system")
    _fixed(frame, "handedness", "right", "$.coordinate_system")
    if "axes" in frame:
        _only(frame["axes"], "x y", "$.coordinate_system.axes")
        _fixed(frame["axes"], "x", "right", "$.coordinate_system.axes")
        _fixed(frame["axes"], "y", "up", "$.coordinate_system.axes")
    outputs = data.get("outputs", {})
    _only(outputs, "top_k formats include_lineage include_histories requested_validation_level", "$.outputs")
    formats = set(outputs.get("formats", ["json", "csv", "npz"]))
    if formats not in ({"json", "csv", "npz"}, {"json", "csv", "npz", "png"}):
        raise UnsupportedFeature("$.outputs.formats: R2.5c writes json, csv and npz together, with optional png.")
    _fixed(outputs, "include_lineage", True, "$.outputs")
    _fixed(outputs, "include_histories", True, "$.outputs")
    _fixed(outputs, "requested_validation_level", "kinematic_candidate", "$.outputs")
    runs = [_options(task, i, outputs) for i, task in enumerate(data["tasks"])]
    return {
        "plan_version": 1,
        "status": "prepared_not_evaluated",
        "task_set_id": data["task_set_id"],
        "omts_version": "0.1.0",
        "implementation": profile["implementation"],
        "adapter_version": profile["adapter_version"],
        "expected_artifacts": profile["expected_artifacts"],
        "input_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest(),
        "input_hash_format": "canonical JSON: sorted keys, compact separators, ASCII escapes, UTF-8",
        "runs": runs,
        "notes": [
            "One independent run per task; no synchronized synthesis.",
            "Preparation does not establish feasibility or meet any requested validation level.",
            "Interpret selection_eligible and qualification_level; raw candidate exports also include rejected designs.",
            "Default R2.5c objectives and scale-relative search bounds remain active; see the adapter profile.",
        ],
    }


def write_plan(data: dict, output: str | Path) -> Path:
    plan = prepare_plan(data)
    output = Path(output)
    # Never overwrite an existing plan, particularly after a failed adaptation.
    output.mkdir(parents=True, exist_ok=False)
    for run in plan["runs"]:
        target_file = output / run["targets_file"]
        target_file.parent.mkdir(parents=True)
        with target_file.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["label", "x1", "y1", "x2", "y2", "x3", "y3"])
            writer.writerow([run["task_id"], *(value for position in run["positions"] for value in position)])
    (output / "run_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    runner = files(__package__).joinpath("runner_template.py.txt").read_text(encoding="utf-8")
    (output / "run_r25c.py").write_text(runner, encoding="utf-8")
    return output / "run_plan.json"
