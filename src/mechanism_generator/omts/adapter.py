"""Prepare a narrow, explicitly checked OMTS subset for the packaged R2.5c engine.

Every operational field is mapped, checked against a fixed supported value, or
rejected. Annotation fields do not influence synthesis. No optimizer is run here.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
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
    _only(cycle, "phase_start phase_end direction independent_variable period phase_reference", path + ".motion.cycle")
    for key, value in dict(phase_start=0, phase_end=360, independent_variable="phase").items():
        _fixed(cycle, key, value, path + ".motion.cycle")
    crank_direction = _choice(cycle, "direction", "positive", ("positive", "negative", "either"), path + ".motion.cycle")
    targets = motion["targets"]
    if len(targets) != 3:
        raise UnsupportedFeature(f"{path}.motion.targets: exactly three targets are required.")
    tolerances = []
    for i, target in enumerate(targets):
        tp = f"{path}.motion.targets[{i}]"
        _only(target, "id name position orientation occurrence tolerance mode notes", tp)
        _fixed(target, "mode", "hard", tp)
        occurrence = target.get("occurrence", {})
        _only(occurrence, "free order_index", tp + ".occurrence")
        _fixed(occurrence, "free", True, tp + ".occurrence")
        tolerance = target.get("tolerance", {})
        _only(tolerance, "position orientation", tp + ".tolerance")
        tolerances.append(tolerance.get("position"))
        if "orientation" in target:
            _only(target["orientation"], "type value", tp + ".orientation")
            _fixed(target["orientation"], "type", "planar_angle", tp + ".orientation")
            try:
                angle_is_finite = math.isfinite(target["orientation"]["value"])
            except OverflowError:
                angle_is_finite = False
            if not angle_is_finite:
                raise UnsupportedFeature(f"{tp}.orientation.value: must be representable as finite degrees.")
            angular_tolerance = tolerance.get("orientation", 5)
            if not 0 < angular_tolerance < 180:
                raise UnsupportedFeature(f"{tp}.tolerance.orientation: must be greater than 0 and less than 180 degrees.")
        elif "orientation" in tolerance:
            raise UnsupportedFeature(f"{tp}.tolerance.orientation: requires a target orientation.")
    pose_target_count = sum("orientation" in target for target in targets)
    if pose_target_count not in (0, 3):
        raise UnsupportedFeature(f"{path}.motion.targets: orientation must be supplied on all three targets, or omitted on all three.")
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
    _only(requirements, "path transmission assembly classification compactness panel collision", rp)
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
    panel = requirements.get("panel")
    if panel is not None:
        _only(panel, "bounds carrier_size pivot_clearance steps mode carrier_frame", rp + ".panel")
        _fixed(panel, "mode", "hard", rp + ".panel")
        _fixed(panel, "carrier_frame", "coupler_A_to_B", rp + ".panel")
        xmin, xmax, ymin, ymax = panel["bounds"]
        clearance = panel.get("pivot_clearance", 0)
        if xmin >= xmax or ymin >= ymax or 2 * clearance >= min(xmax - xmin, ymax - ymin):
            raise UnsupportedFeature(f"{rp}.panel: bounds and pivot clearance must leave a usable interior.")

    options = task.get("search", {})
    op = path + ".search"
    _only(options, "implementation_profile seed top_k perturbations_per_model parameter_noise phase_noise pose_initialization", op)
    _fixed(options, "implementation_profile", "r2.5c-fourbar", op)
    top_k = options.get("top_k", outputs.get("top_k", 5))
    if "top_k" in outputs and "top_k" in options and top_k != outputs["top_k"]:
        raise UnsupportedFeature(f"{op}.top_k conflicts with $.outputs.top_k; omit the global value for task-specific counts.")

    flags = {
        "--branches": branch,
        "--phase_mode": phase_mode,
        "--crank_direction": crank_direction,
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
    pose_fields = {}
    if "pose_initialization" in options and not pose_target_count:
        raise UnsupportedFeature(f"{op}.pose_initialization: requires three orientation targets.")
    if pose_target_count:
        initialization = options.get("pose_initialization", {})
        arguments.extend(["--pose_dyad_samples", str(initialization.get("nominal_samples", 4096)),
                          "--pose_tolerance_samples", str(initialization.get("tolerance_samples", 65536)),
                          "--pose_dyad_seed_count", str(initialization.get("seeds_per_branch", 6))])
        pose_fields = {
            "target_orientations_deg": [target["orientation"]["value"] for target in targets],
            "orientation_tolerances_deg": [target.get("tolerance", {}).get("orientation", 5) for target in targets],
        }
        for name, values in pose_fields.items():
            arguments.extend([f"--{name}", *(str(value) for value in values)])
    if panel is not None:
        arguments.extend(["--panel_bounds", *map(str, panel["bounds"]),
                          "--carrier_size", *map(str, panel["carrier_size"]),
                          "--panel_pivot_clearance", str(panel.get("pivot_clearance", 0)),
                          "--panel_steps", str(panel.get("steps", 7201))])
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
        **pose_fields,
        "targets_file": f"tasks/task-{index + 1:03d}/targets.csv",
        "output_root": f"results/task-{index + 1:03d}",
        "arguments": arguments,
    }


def _event_ref(value, task_target_ids: dict, path: str) -> dict:
    parts = str(value).split(".")
    if len(parts) == 3 and parts[1] in ("occupies_region", "enters_region", "exits_region"):
        raise UnsupportedFeature(f"{path}: derived region events are computed by the timeline verifier, not authored; relations over them are supported from G5.")
    if len(parts) != 3 or parts[2] != "reached":
        raise UnsupportedFeature(f"{path}: only target-reached event references ('task.target.reached') are supported.")
    task, target = parts[0], parts[1]
    if target not in task_target_ids.get(task, set()):
        raise UnsupportedFeature(f"{path}: unknown task or target '{value}'.")
    return {"task": task, "target": target}


def _sync_quantity(value, path: str) -> float:
    if not isinstance(value, dict) or set(value) != {"phase"}:
        raise UnsupportedFeature(f"{path}: only phase-quantified values such as {{'phase': 2}} are supported.")
    return value["phase"]


def data_task_reference(data: dict, task_id: str):
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    return None if task is None else task["motion"].get("cycle", {}).get("phase_reference")

def _collision_model(task: dict, index: int) -> dict | None:
    """Normalize a task's requirements.collision into a recordable body model."""
    collision = task.get("requirements", {}).get("collision")
    if collision is None:
        return None
    path = f"$.tasks[{index}].requirements.collision"
    _only(collision, "bodies steps mode", path)
    bodies = collision["bodies"]
    _only(bodies, "links carrier", path + ".bodies")
    links = bodies.get("links", {})
    _only(links, "thickness", path + ".bodies.links")
    model = {
        "thickness": float(links.get("thickness", 0.0)),
        "steps": collision.get("steps", 720),
        "mode": collision.get("mode", "hard"),
    }
    carrier = bodies.get("carrier")
    if carrier is not None:
        _only(carrier, "width depth", path + ".bodies.carrier")
        model["carrier"] = {"width": float(carrier["width"]), "depth": float(carrier["depth"])}
    return model


def _collision_models(data: dict) -> dict:
    """Recorded collision body models keyed by task id (only tasks declaring one)."""
    models = {}
    for index, task in enumerate(data["tasks"]):
        model = _collision_model(task, index)
        if model is not None:
            models[task["id"]] = model
    return models


def _line(data: dict, collision_models: dict | None = None) -> dict | None:
    """Record preparable v0.2 synchronization; reject everything this adapter cannot verify later."""
    sync = data.get("synchronization")
    if not sync:
        return None
    path = "$.synchronization"
    _only(sync, "master_cycle_id period shared_input participants events relations applied_offsets offset_realization", path)
    if not str(data.get("version", "")).startswith("0.2"):
        raise UnsupportedFeature(f"{path}: v0.1 synchronization fields are not supported; express the line in a 0.2 document.")
    if "phase_relations" in sync:
        raise UnsupportedFeature(f"{path}.phase_relations: deprecated; use relations with event references.")
    _fixed(sync, "shared_input", True, path)
    task_target_ids = {task["id"]: {t["id"] for t in task["motion"]["targets"]} for task in data["tasks"]}
    for i, entry in enumerate(sync.get("participants", [])):
        pp = f"{path}.participants[{i}]"
        _only(entry, "task ratio", pp)
        if "ratio" in entry and tuple(entry["ratio"]) != (1, 1):
            raise UnsupportedFeature(f"{pp}.ratio: ratioed participation cannot be prepared; each task shares the master cycle 1:1.")
        if entry["task"] not in task_target_ids:
            raise UnsupportedFeature(f"{pp}.task: unknown task '{entry['task']}'.")
    applied_offsets = {}
    for task_id, quantity in sync.get("applied_offsets", {}).items():
        op = f"{path}.applied_offsets.{task_id}"
        if task_id not in task_target_ids:
            raise UnsupportedFeature(f"{op}: unknown task '{task_id}'.")
        applied_offsets[task_id] = float(_sync_quantity(quantity, op))
    offset_realization = {}
    for task_id, record in (sync.get("offset_realization") or {}).items():
        rp = f"{path}.offset_realization.{task_id}"
        if task_id not in task_target_ids:
            raise UnsupportedFeature(f"{rp}: unknown task '{task_id}'.")
        if task_id not in applied_offsets:
            raise UnsupportedFeature(f"{rp}: task '{task_id}' declares no applied offset to realize.")
        realization = {"method": record["method"]}
        if "detail" in record:
            realization["detail"] = str(record["detail"])
        offset_realization[task_id] = realization
    events = []
    for i, event in enumerate(sync.get("events", [])):
        ep = f"{path}.events[{i}]"
        _only(event, "id type participants window tolerance mode", ep)
        if event.get("type", "co_active") != "co_active":
            raise UnsupportedFeature(f"{ep}.type: only co_active events are supported; handoff and co_location need unsupported payload and load handling.")
        participants = event["participants"]
        if len(participants) != 2:
            raise UnsupportedFeature(f"{ep}.participants: exactly two reached-event references are supported.")
        window = event.get("window")
        if not isinstance(window, dict) or set(window) != {"phase_range"} or len(window["phase_range"]) != 2:
            raise UnsupportedFeature(f"{ep}.window: a phase_range window is required.")
        low, high = window["phase_range"]
        tolerance = 0.0
        if "tolerance" in event and isinstance(event["tolerance"], dict):
            tolerance = float(event["tolerance"].get("phase", 0.0))
        for participant in participants:
            ref = _event_ref(participant, task_target_ids, f"{ep}.participants")
            reference = data_task_reference(data, ref["task"])
            if reference == ref["target"]:
                offset = float(applied_offsets.get(ref["task"], 0.0)) % 360.0
                if not (low - tolerance <= offset <= high + tolerance):
                    raise UnsupportedFeature(f"{ep}: participant '{participant}' is task '{ref['task']}'s phase_reference target and is always at phase 0 plus its applied offset (here {offset:g}); it cannot appear in the window [{low}, {high}].")
        events.append({
            "id": event["id"],
            "participants": [_event_ref(p, task_target_ids, f"{ep}.participants") for p in participants],
            "window_deg": window["phase_range"],
            "tolerance_deg": _sync_quantity(event["tolerance"], f"{ep}.tolerance") if "tolerance" in event else None,
            "mode": event.get("mode", "hard"),
        })
    relations = []
    for i, relation in enumerate(sync.get("relations", [])):
        rp = f"{path}.relations[{i}]"
        _only(relation, "id from to type offset tolerance min_lead max_lead mode notes", rp)
        if relation["type"] not in ("ordering", "fixed_offset"):
            raise UnsupportedFeature(f"{rp}.type: only ordering and fixed_offset relations are supported; contains and disjoint_windows over derived region events are verified from G5.")
        record = {
            "id": relation["id"],
            "from": _event_ref(relation["from"], task_target_ids, f"{rp}.from"),
            "to": _event_ref(relation["to"], task_target_ids, f"{rp}.to"),
            "type": relation["type"],
            "mode": relation.get("mode", "hard"),
        }
        if relation["type"] == "ordering":
            record["min_lead_deg"] = _sync_quantity(relation["min_lead"], f"{rp}.min_lead")
            record["max_lead_deg"] = _sync_quantity(relation["max_lead"], f"{rp}.max_lead")
        else:
            record["offset_deg"] = _sync_quantity(relation["offset"], f"{rp}.offset")
            if "tolerance" in relation:
                record["tolerance_deg"] = _sync_quantity(relation["tolerance"], f"{rp}.tolerance")
        relations.append(record)
    line = {
        "master_cycle_id": sync.get("master_cycle_id"),
        "period": sync.get("period"),
        "phase_reference": {task["id"]: task["motion"].get("cycle", {}).get("phase_reference") for task in data["tasks"]},
        "events": events,
        "relations": relations,
        "verification": "pending_timeline_verification",
    }
    if applied_offsets:
        line["applied_offsets"] = applied_offsets
    if offset_realization:
        line["offset_realization"] = offset_realization
    if data.get("regions"):
        line["regions"] = data["regions"]
    if collision_models:
        line["collision"] = collision_models
    return line


def prepare_plan(data: dict) -> dict:
    """Validate the whole task set before preparing any output or command."""
    require_valid(data)
    _only(data, "spec version task_set_id name description capabilities_required unsupported_feature_policy units coordinate_system synchronization regions tasks outputs metadata", "$")
    _fixed(data, "unsupported_feature_policy", "error", "$")
    profile = capabilities()
    if data.get("version") not in profile["omts_versions"]:
        raise UnsupportedFeature(f"$.version: this adapter accepts OMTS versions {profile['omts_versions']}, received {data.get('version')!r}.")
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
    collision_models = _collision_models(data)
    line = _line(data, collision_models)
    if line is None and (data.get("regions") or collision_models):
        raise UnsupportedFeature("$.regions and $.tasks[].requirements.collision are recorded for the synchronization line; declare 'synchronization' or remove the collision features.")
    runs = [_options(task, i, outputs) for i, task in enumerate(data["tasks"])]
    notes = [
        "One independent run per task; no synchronized synthesis.",
        "Preparation does not establish feasibility or meet any requested validation level.",
        "Interpret selection_eligible and qualification_level; raw candidate exports also include rejected designs.",
        "Default R2.5c objectives and scale-relative search bounds remain active; see the adapter profile.",
    ]
    if line is not None:
        notes.append("Synchronization metadata is recorded for post-hoc timeline verification; no joint optimization or verification is performed by this plan.")
        if line.get("collision") or line.get("regions"):
            notes.append("Collision geometry (regions and per-task body models) is recorded for post-hoc sampled occupancy computation; the engine does not evaluate it.")
    plan = {
        "plan_version": 1,
        "status": "prepared_not_evaluated",
        "task_set_id": data["task_set_id"],
        "omts_version": data["version"],
        "implementation": profile["implementation"],
        "adapter_version": profile["adapter_version"],
        "expected_artifacts": profile["expected_artifacts"],
        "expected_engine_artifacts": profile["expected_engine_artifacts"],
        "input_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest(),
        "input_hash_format": "canonical JSON: sorted keys, compact separators, ASCII escapes, UTF-8",
        "runs": runs,
        "notes": notes,
    }
    if line is not None:
        plan["line"] = line
    return plan


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
