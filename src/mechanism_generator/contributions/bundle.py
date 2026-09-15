"""Project selected numerical results into a portable, offline review bundle.

The schema is also the field allowlist: unknown source fields are never copied.
This module deliberately has no network or engine dependencies.
"""
from __future__ import annotations

import csv
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator

from mechanism_generator import __version__

MAX_BYTES = 20 * 1024 * 1024
COUNT_FIELDS = (
    "candidate_count", "path_acceptable_count", "selection_eligible_count",
    "engineering_acceptable_count", "selected_count",
)
POSE_COUNTS = ("orientation_acceptable_count", "pose_acceptable_count")
POSE_TASK_FIELDS = ("target_orientations_deg", "orientation_tolerances_deg", "orientation_frame")
POSE_CANDIDATE_FIELDS = (
    "orientation_frame", "orientation_acceptable", "pose_acceptable",
    "max_orientation_error_deg", "mean_orientation_error_deg", "initial_max_orientation_error_deg",
    *(f"{prefix}_{index}_deg" for index in range(1, 4) for prefix in
      ("target_orientation", "orientation_tolerance", "matched_orientation", "orientation_error")),
)


def schema(version: str = "0.2") -> dict:
    if version not in ("0.1", "0.2"):
        raise ValueError("Unsupported contribution schema version")
    name = "schema-v0.1.json" if version == "0.1" else "schema.json"
    return json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def read_json(path: Path) -> dict:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Contribution input exceeds the 20 MiB limit")
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite numbers are not allowed in contributions")
    if isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)


def validate_bundle(bundle: dict) -> None:
    """Validate structure and internal references, not scientific truth or rights."""
    _finite(bundle)
    version = bundle.get("schema_version") if isinstance(bundle, dict) else None
    errors = list(Draft202012Validator(schema(version)).iter_errors(bundle))
    if errors:
        # Do not echo submitted free text or unknown field contents in errors.
        raise ValueError("Contribution does not match its declared schema")
    tasks = bundle["core"]["tasks"]
    by_id = {task["task_id"]: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("Duplicate task identifiers")
    for task in tasks:
        if any(task[key] > task["candidate_count"] for key in COUNT_FIELDS[1:]):
            raise ValueError("Outcome count exceeds candidate count")
        if task["selected_count"] > task["selection_eligible_count"]:
            raise ValueError("Selected count exceeds eligible count")
        if task.get("orientation_required", False):
            if any(task[key] > task["candidate_count"] for key in POSE_COUNTS):
                raise ValueError("Pose outcome count exceeds candidate count")
            if task["pose_acceptable_count"] > min(task["path_acceptable_count"], task["orientation_acceptable_count"]):
                raise ValueError("Pose count exceeds position or orientation acceptance")
            if max(task["selected_count"], task["selection_eligible_count"], task["engineering_acceptable_count"]) > task["pose_acceptable_count"]:
                raise ValueError("Selected or qualified count exceeds pose acceptance")
        elif any(key in task for key in POSE_COUNTS):
            raise ValueError("Pose outcome counts require an orientation task")
    task_details = {task["task_id"]: task for task in bundle.get("task", [])}
    for section in ("task", "candidates"):
        seen = set()
        for task in bundle.get(section, []):
            identity = task["task_id"]
            if identity not in by_id or identity in seen:
                raise ValueError("Invalid or duplicate task reference")
            seen.add(identity)
            pose_required = by_id[identity].get("orientation_required", False)
            if section == "task":
                if pose_required and not all(key in task for key in POSE_TASK_FIELDS):
                    raise ValueError("Included pose task must retain its orientation requirements")
                if not pose_required and any(key in task for key in POSE_TASK_FIELDS):
                    raise ValueError("Orientation requirements contradict the recorded task type")
            if section == "candidates":
                items = task["items"]
                ids = {item["candidate_id"] for item in items}
                if len(ids) != len(items) or len(items) != by_id[identity]["candidate_count"]:
                    raise ValueError("Candidate identifiers or counts are inconsistent")
                flags = ["path_acceptable", "selection_eligible", "engineering_acceptable"]
                if pose_required:
                    flags.extend(["orientation_acceptable", "pose_acceptable"])
                for flag in flags:
                    if all(flag in item for item in items):
                        if sum(item[flag] for item in items) != by_id[identity][flag + "_count"]:
                            raise ValueError("Candidate qualification flags contradict outcome counts")
                for item in items:
                    if pose_required:
                        if item.get("orientation_required") is not True:
                            raise ValueError("Included pose candidates must retain their orientation requirements")
                        if item["pose_acceptable"] != (item["path_acceptable"] and item["orientation_acceptable"]):
                            raise ValueError("Pose acceptance contradicts position or orientation acceptance")
                        if (item["selection_eligible"] or item["engineering_acceptable"]) and not item["pose_acceptable"]:
                            raise ValueError("Qualified pose candidate fails its orientation or position gate")
                        details = task_details.get(identity)
                        if details:
                            for index in range(1, 4):
                                if (item[f"target_orientation_{index}_deg"] != details["target_orientations_deg"][index - 1]
                                        or item[f"orientation_tolerance_{index}_deg"] != details["orientation_tolerances_deg"][index - 1]):
                                    raise ValueError("Candidate and task orientation requirements disagree")
                    elif item.get("orientation_required", False) or any(key in item for key in POSE_CANDIDATE_FIELDS):
                        raise ValueError("Candidate orientation fields contradict the recorded task type")
                    for key in ("portfolio_parent_candidate_id", "shared_path_reference_candidate_id"):
                        if key in item and item[key] not in ids:
                            raise ValueError("Invalid candidate reference")
        if section in bundle and seen != set(by_id):
            raise ValueError("Included sections must cover every reported task")


def _project(source, properties, *, csv_values=False):
    result = {}
    if not isinstance(source, dict):
        raise ValueError("Expected a source record")
    for key, rule in properties.items():
        if key not in source:
            continue
        value = source[key]
        if csv_values:
            try:
                if rule.get("type") == "boolean":
                    value = {"True": True, "False": False, "true": True, "false": False}[value]
                elif rule.get("type") in ("number", "integer"):
                    value = float(value)
            except (ValueError, KeyError, TypeError):
                continue
        try:
            _finite(value)
        except ValueError:
            continue  # Failed candidates can have undefined metrics; omit those metrics.
        if Draft202012Validator(rule).is_valid(value):
            result[key] = value
    return result


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Run artifact must use a relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Run artifact points outside the selected run")
    return path


def build_bundle(run_directory: Path) -> dict:
    root = run_directory.resolve(strict=True)
    manifest = read_json(_inside(root, "run_manifest.json"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("targets"), list):
        raise ValueError("Expected an R2.5c run manifest")
    if "R2.5c" not in str(manifest.get("variant", "")):
        raise ValueError("Only R2.5c run manifests are supported")
    props = schema()["properties"]
    bundle = {
        "schema_version": "0.2", "kind": "local",
        "core": {"generator_version": __version__, "engine": "r2.5c",
                 "run_status": manifest.get("run_status", "unknown"),
                 "validation_status": "unreviewed", "tasks": []},
        "task": [], "candidates": [], "provenance": {"models": []},
        "settings": _project(manifest.get("arguments", {}), props["settings"]["properties"]),
    }
    candidate_props = props["candidates"]["items"]["properties"]["items"]["items"]["properties"]
    for index, target in enumerate(manifest["targets"], 1):
        identity = f"task-{index:04d}"
        pose_required = any(key in target for key in (*POSE_TASK_FIELDS, *POSE_COUNTS))
        core = {"task_id": identity, **{key: target[key] for key in COUNT_FIELDS},
                "orientation_required": pose_required}
        task_record = {"task_id": identity, "target_values": target["target_values"]}
        if pose_required:
            core.update({key: target[key] for key in POSE_COUNTS})
            task_record.update({key: target[key] for key in POSE_TASK_FIELDS})
        bundle["core"]["tasks"].append(core)
        bundle["task"].append(task_record)
        directory = _inside(root, target["directory"])
        source = _inside(root, str((directory / "all_candidates.csv").relative_to(root)))
        if source.stat().st_size > MAX_BYTES:
            raise ValueError("Candidate input exceeds the 20 MiB limit")
        with source.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        ids = {row["candidate_id"]: f"candidate-{i:04d}" for i, row in enumerate(rows, 1)}
        if len(ids) != len(rows):
            raise ValueError("Duplicate source candidate identifiers")
        items = []
        for row in rows:
            item = _project(row, candidate_props, csv_values=True)
            item["candidate_id"] = ids[row["candidate_id"]]
            for key in ("portfolio_parent_candidate_id", "shared_path_reference_candidate_id"):
                item.pop(key, None)
                if row.get(key) in ids:
                    item[key] = ids[row[key]]
            items.append(item)
        bundle["candidates"].append({"task_id": identity, "items": items})
    provenance = props["provenance"]["properties"]
    bundle["provenance"].update(_project({"engine_sha256": manifest.get("script_sha256"),
        "parent_engine_sha256": manifest.get("engine_sha256"),
        "orientation_sha256": manifest.get("orientation_sha256")}, provenance))
    for model in manifest.get("models", []):
        selected = _project(model, provenance["models"]["items"]["properties"])
        if set(selected) == {"role", "sha256"}:
            bundle["provenance"]["models"].append(selected)
    validate_bundle(bundle)
    return bundle


def _atomic_write(path: Path, content: str):
    # Refuse pre-existing symbolic links, including the contribution directory.
    if path.is_symlink():
        raise ValueError("Contribution output must not be a symbolic link")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_bundle(run_directory: Path) -> Path:
    """Write a local JSON bundle and standalone review page. Never upload or open UI."""
    root = run_directory.resolve(strict=True)
    bundle = build_bundle(root)
    encoded = json.dumps(bundle, ensure_ascii=True, indent=2, allow_nan=False) + "\n"
    if len(encoded.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Contribution bundle exceeds the 20 MiB limit")
    template = files(__package__).joinpath("review.html").read_text(encoding="utf-8")
    # JSON is data inside a script element. Prevent closing that element or HTML injection.
    page = template.replace("__BUNDLE_JSON__", encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    output = root / "contribution"
    if output.is_symlink() or output.resolve() != output:
        raise ValueError("Contribution output must not be a symbolic link or junction")
    output.mkdir(exist_ok=True)
    _atomic_write(output / "bundle.json", encoded)
    _atomic_write(output / "review.html", page)
    return output / "review.html"
