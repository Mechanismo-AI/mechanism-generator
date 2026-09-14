"""Shared schema and semantic validation for OMTS documents and adapters."""

from __future__ import annotations

import json
import math
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


class DocumentError(ValueError):
    """An unreadable, ambiguous, or invalid OMTS document."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Accept JSON-compatible YAML, without duplicate or overriding merge keys."""


UniqueKeyLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in values if tag != "tag:yaml.org,2002:timestamp"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str):
            raise DocumentError("Mapping keys must be strings.")
        if key in result:
            raise DocumentError(f"Duplicate mapping key: {key}")
        result[key] = value
    return result


def _yaml_mapping(loader, node):
    loader.flatten_mapping(node)
    return _unique_pairs(
        (loader.construct_object(key), loader.construct_object(value))
        for key, value in node.value
    )


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _yaml_mapping)


def _json_errors(value: Any, path: str = "$", ancestors: frozenset = frozenset()) -> list[str]:
    if isinstance(value, (dict, list)):
        if id(value) in ancestors:
            return [f"{path}: recursive aliases are not valid OMTS data."]
        ancestors = ancestors | {id(value)}
        pairs = value.items() if isinstance(value, dict) else enumerate(value)
        errors = []
        for key, child in pairs:
            if isinstance(value, dict) and not isinstance(key, str):
                errors.append(f"{path}: mapping keys must be strings.")
            errors.extend(_json_errors(child, f"{path}[{key!r}]", ancestors))
        return errors
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}: numbers must be finite."]
    if value is not None and not isinstance(value, (str, bool, int, float)):
        return [f"{path}: value is not JSON-compatible."]
    return []


def load_document(path: str | Path) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
        data = (json.loads(text, object_pairs_hook=_unique_pairs)
                if Path(path).suffix.lower() == ".json"
                else yaml.load(text, Loader=UniqueKeyLoader))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise DocumentError(str(exc)) from exc
    if not isinstance(data, dict):
        raise DocumentError("The OMTS root must be an object/mapping.")
    errors = _json_errors(data)
    if errors:
        raise DocumentError("\n".join(errors))
    return data


def schema_document() -> dict:
    return json.loads(files(__package__).joinpath("schema.json").read_text(encoding="utf-8"))


def _duplicates(items: list[dict], path: str, errors: list[str]) -> None:
    seen = set()
    for item in items:
        identifier = item["id"]
        if identifier in seen:
            errors.append(f"{path}: duplicate ID '{identifier}'.")
        seen.add(identifier)


def semantic_errors(data: dict) -> list[str]:
    """Cross-field checks, called only after structural schema validation."""
    errors: list[str] = []
    dimension = data["coordinate_system"]["dimension"]
    angle_limit = 90 if data["units"]["angle"] == "deg" else math.pi / 2
    tasks = data["tasks"]
    task_ids = {task["id"] for task in tasks}
    payloads = data.get("payloads", [])
    loads = data.get("load_cases", [])
    payload_ids = {item["id"] for item in payloads}
    load_ids = {item["id"] for item in loads}
    _duplicates(tasks, "$.tasks", errors)
    _duplicates(payloads, "$.payloads", errors)
    _duplicates(loads, "$.load_cases", errors)

    def reference(obj, key, allowed, path):
        if key in obj and obj[key] not in allowed:
            errors.append(f"{path}.{key}: unknown reference '{obj[key]}'.")

    def ordered_range(value, path, positive=False, nonnegative=False):
        if value[0] > value[1]:
            errors.append(f"{path}: minimum must not exceed maximum.")
        if positive and value[0] <= 0:
            errors.append(f"{path}: lengths must be positive.")
        if nonnegative and value[0] < 0:
            errors.append(f"{path}: time must be nonnegative.")

    def walk(obj, path):
        if isinstance(obj, list):
            for i, child in enumerate(obj):
                walk(child, f"{path}[{i}]")
        elif isinstance(obj, dict):
            for key, child in obj.items():
                # Metadata and extensions have no standard geometric semantics.
                if key in ("extensions", "metadata"):
                    continue
                if key in ("position", "center_of_mass", "force", "moment", "application_point",
                           "gravity", "axis", "vector", "envelope_min", "envelope_max", "min", "max"):
                    if isinstance(child, list) and len(child) != dimension:
                        errors.append(f"{path}.{key}: expected {dimension} vector components.")
                if key == "points":
                    for point in child:
                        if len(point) != dimension:
                            errors.append(f"{path}.points: expected {dimension} vector components.")
                if key in ("phase_range", "time_range"):
                    ordered_range(child, f"{path}.{key}", nonnegative=key == "time_range")
                walk(child, f"{path}.{key}")
            for low, high in (("envelope_min", "envelope_max"), ("min", "max")):
                if low in obj and high in obj and isinstance(obj[low], list) and isinstance(obj[high], list):
                    if len(obj[low]) != len(obj[high]) or any(a > b for a, b in zip(obj[low], obj[high])):
                        errors.append(f"{path}: {low} must not exceed {high}.")
            if "min_magnitude" in obj and "max_magnitude" in obj and obj["min_magnitude"] > obj["max_magnitude"]:
                errors.append(f"{path}: min_magnitude must not exceed max_magnitude.")
            if "free" in obj and obj["free"] is not True:
                errors.append(f"{path}.free must be true; specify phase/time to constrain occurrence.")

    walk(data, "$")
    for i, load in enumerate(loads):
        reference(load, "payload_ref", payload_ids, f"$.load_cases[{i}]")
    for i, task in enumerate(tasks):
        path = f"$.tasks[{i}]"
        motion = task["motion"]
        targets = motion["targets"]
        _duplicates(targets, path + ".motion.targets", errors)
        target_ids = {target["id"] for target in targets}
        for j, target in enumerate(targets):
            tp = f"{path}.motion.targets[{j}]"
            reference(target, "payload_ref", payload_ids, tp)
            reference(target, "load_case_ref", load_ids, tp)
            occurrence = target.get("occurrence", {})
            if motion["order_policy"] == "fixed_timing" and not any(k in occurrence for k in ("phase", "phase_range", "time", "time_range")):
                errors.append(f"{tp}: fixed_timing requires a phase/time or window.")
            orientation = target.get("orientation", {})
            if dimension == 2 and orientation and orientation["type"] != "planar_angle":
                errors.append(f"{tp}.orientation: a planar task requires planar_angle.")
            if dimension == 3 and orientation.get("type") == "planar_angle":
                errors.append(f"{tp}.orientation: a spatial task requires a 3D orientation.")
            if orientation.get("type") == "quaternion_wxyz":
                if not math.isclose(math.hypot(*orientation["value"]), 1.0, abs_tol=1e-6):
                    errors.append(f"{tp}.orientation: quaternion must have unit norm.")
        indices = [target.get("occurrence", {}).get("order_index") for target in targets]
        if any(index is not None for index in indices):
            if any(index is None for index in indices) or len(set(indices)) != len(indices):
                errors.append(f"{path}.motion: order_index must be unique and present on every target when used.")
            if motion["order_policy"] == "unordered":
                errors.append(f"{path}.motion: order_index conflicts with unordered targets.")
        primitives = motion.get("primitives", [])
        _duplicates(primitives, path + ".motion.primitives", errors)
        for j, primitive in enumerate(primitives):
            reference(primitive, "target_ref", target_ids, f"{path}.motion.primitives[{j}]")
        _duplicates(motion.get("path_constraints", []), path + ".motion.path_constraints", errors)
        _duplicates(task.get("workspace", {}).get("obstacles", []), path + ".workspace.obstacles", errors)
        search = task["mechanism_search"]
        ground = search.get("ground_link", {})
        for key in ("bounds", "variable_bounds"):
            if key in ground:
                ordered_range(ground[key], f"{path}.mechanism_search.ground_link.{key}", positive=True)
        if "bounds" in ground and "initial_value" in ground:
            if not ground["bounds"][0] <= ground["initial_value"] <= ground["bounds"][1]:
                errors.append(f"{path}.mechanism_search.ground_link: initial_value is outside bounds.")
        for key, value in search.get("bounds", {}).items():
            ordered_range(value, f"{path}.mechanism_search.bounds.{key}", positive=key in ("l1", "l2", "l3", "l4", "bar_length"))
        if ground.get("mode") == "fixed" and "l1" in search.get("bounds", {}):
            lo, hi = search["bounds"]["l1"]
            if not lo <= ground["value"] <= hi:
                errors.append(f"{path}.mechanism_search: fixed ground value is outside l1 bounds.")
        tx = task.get("requirements", {}).get("transmission", {})
        for key in ("min_at_targets", "min_global", "selection_min_at_targets", "selection_min_global"):
            if tx.get(key, 0) > angle_limit:
                errors.append(f"{path}.requirements.transmission.{key}: exceeds {angle_limit:g} {data['units']['angle']}.")
    sync = data.get("synchronization", {})
    _duplicates(sync.get("events", []), "$.synchronization.events", errors)
    for i, event in enumerate(sync.get("events", [])):
        for participant in event["participants"]:
            if participant not in task_ids:
                errors.append(f"$.synchronization.events[{i}]: unknown task '{participant}'.")
    for i, relation in enumerate(sync.get("phase_relations", [])):
        for key in ("from_task", "to_task"):
            reference(relation, key, task_ids, f"$.synchronization.phase_relations[{i}]")
    return errors


def validate_document(data: Any) -> list[str]:
    errors = _json_errors(data)
    if errors:
        return errors
    validator = Draft202012Validator(schema_document(), format_checker=FormatChecker())
    errors = [f"{error.json_path}: {error.message}" for error in validator.iter_errors(data)]
    return sorted(errors) if errors else semantic_errors(data)


def require_valid(data: dict) -> None:
    errors = validate_document(data)
    if errors:
        raise DocumentError("Invalid OMTS document:\n" + "\n".join(errors))
