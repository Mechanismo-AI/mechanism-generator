#!/usr/bin/env python3
"""Generate, adapt, run, and verify a corpus of synchronized pair documents.

Deterministic variants of examples/omts/synchronized_pair.omts.yaml. Each
variant is validated, adapted, executed per-task with the installed engine,
and line-verified with the S4 verifier. Variants are independent; a failure
in one is recorded and does not stop the corpus. Completed variants are
skipped on rerun, so the job is resumable.

`--document` selects the base OMTS document for the variants (default: the
synchronized pair example). A base with regions and collision bodies (for
example `examples/omts/collision_pair.omts.yaml`) produces variants whose
region and body geometry transform with the targets.

`--offsets` declares per-variant synchronization applied_offsets (a
human-reviewed timeline decision, not a search parameter). `--results-from`
reuses a prior corpus run's engine result trees: applied offsets change only
the composed timeline, never the per-task engine search, so reused results
are exact rather than approximate.

This driver never modifies the repository and never uploads anything.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_DOCUMENT = ROOT / "examples" / "omts" / "synchronized_pair.omts.yaml"


def load_yaml(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_offsets(path: Path) -> dict:
    """Read {"corpus_pair_NN": {"task": {"phase": deg}}} from a JSON file.

    Only the file's shape is checked here: variant IDs must map to objects.
    The meaning of each offset entry is validated per document (unknown
    tasks, bad quantities) exactly as in a hand-edited document.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("offsets file must be a JSON object mapping variant IDs to applied_offsets objects")
    for variant, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(f"offsets entry for {variant!r} must be an object of applied_offsets")
    return data


def rotate_scale(points, angle_deg: float, scale: float):
    angle = math.radians(angle_deg)
    cos, sin = math.cos(angle), math.sin(angle)
    return [[round(scale * (cos * x - sin * y), 4), round(scale * (sin * x + cos * y), 4)] for x, y in points]


def variant_document(base: dict, index: int, angle: float, scale: float) -> dict:
    """Deterministic rotate/scale variant of the whole machine geometry.

    Target positions, region geometry, and declared collision body sizes all
    transform together, so a variant is the same machine viewed in a rotated,
    scaled world: circle regions transform exactly, box regions take the
    axis-aligned bounding box of their rotated corners (an envelope, larger
    than the rotated box), and collision thickness and carrier sizes scale
    with the variant. Occupancy timing per variant is whatever the transformed
    geometry produces; the driver never claims a variant is equivalent to its
    base.
    """
    document = json.loads(json.dumps(base))
    document["task_set_id"] = f"corpus_pair_{index:02d}"
    document["name"] = f"Synchronized pair corpus variant {index:02d}"
    for task in document["tasks"]:
        positions = [target["position"] for target in task["motion"]["targets"]]
        moved = rotate_scale(positions, angle, scale)
        for target, position in zip(task["motion"]["targets"], moved):
            target["position"] = position
        bodies = task.get("requirements", {}).get("collision", {}).get("bodies", {})
        links = bodies.get("links", {})
        if "thickness" in links:
            links["thickness"] = round(links["thickness"] * scale, 4)
        carrier = bodies.get("carrier")
        if carrier is not None:
            carrier["width"] = round(carrier["width"] * scale, 4)
            carrier["depth"] = round(carrier["depth"] * scale, 4)
    for region in document.get("regions", []):
        if region["shape"] == "circle":
            region["center"] = rotate_scale([region["center"]], angle, scale)[0]
            region["radius"] = round(region["radius"] * scale, 4)
        else:
            low, high = region["min"], region["max"]
            corners = rotate_scale([[low[0], low[1]], [high[0], low[1]],
                                    [high[0], high[1]], [low[0], high[1]]], angle, scale)
            region["min"] = [min(point[axis] for point in corners) for axis in (0, 1)]
            region["max"] = [max(point[axis] for point in corners) for axis in (0, 1)]
    return document


def check_call(command, cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {command[:3]} ...\n{result.stdout}\n{result.stderr}")


def run_variant(document: dict, out_dir: Path, models: Path, quick: bool,
                results_from: Path | None = None) -> dict:
    import yaml
    document_path = out_dir / "document.omts.yaml"
    document_path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    plan_dir = out_dir / "plan"
    if plan_dir.exists():
        shutil.rmtree(plan_dir)
    started = time.monotonic()
    check_call([sys.executable, "-m", "mechanism_generator.omts", "validate", str(document_path)], ROOT)
    check_call([sys.executable, "-m", "mechanism_generator.omts", "adapt", str(document_path),
                "--output-dir", str(plan_dir)], ROOT)
    plan = json.loads((plan_dir / "run_plan.json").read_text(encoding="utf-8"))
    task_times = {}
    selected_counts = {}
    results_reused = False
    reuse_root = (results_from / out_dir.name / "plan" / "results") if results_from else None
    if reuse_root is not None and reuse_root.is_dir():
        shutil.copytree(reuse_root, plan_dir / "results")
        results_reused = True
        print(f"  reused engine results from {reuse_root}", flush=True)
    elif reuse_root is not None:
        print(f"  no reusable results at {reuse_root}; falling back to the engine", flush=True)
    for run in plan["runs"]:
        if results_reused:
            task_times[run["task_id"]] = 0.0
        else:
            task_started = time.monotonic()
            command = [sys.executable, "-m", "mechanism_generator.engine",
                       "--models-directory", str(models), *run["arguments"],
                       "--targets_file", str(plan_dir / run["targets_file"]),
                       "--output_root", str(plan_dir / run["output_root"])]
            if quick:
                command.append("--quick")
            check_call(command, plan_dir)
            task_times[run["task_id"]] = round(time.monotonic() - task_started, 1)
        manifests = sorted((plan_dir / run["output_root"]).glob("r25c/*/run_manifest.json"))
        if manifests:
            manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
            selected_counts[run["task_id"]] = len(manifest["targets"][0].get("selected", []))
        else:
            selected_counts[run["task_id"]] = 0
    from mechanism_generator.omts.line_verify import LineVerificationError, verify_line
    try:
        line_result = verify_line(plan_dir)
    except LineVerificationError as exc:
        line_result = {"status": "error", "note": str(exc)}
    line_section = plan.get("line") or {}
    return {
        "task_set_id": document["task_set_id"],
        "status": line_result["status"],
        "combination_count": line_result.get("combination_count"),
        "passing_combination_count": line_result.get("passing_combination_count"),
        "selected_counts": selected_counts,
        "applied_offsets": line_section.get("applied_offsets"),
        "results_reused": results_reused,
        "task_times_seconds": task_times,
        "total_seconds": round(time.monotonic() - started, 1),
        "line_note": line_result.get("note"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", type=Path, default=BASE_DOCUMENT,
                        help="Base OMTS document for the variants "
                             "(default: examples/omts/synchronized_pair.omts.yaml)")
    parser.add_argument("--count", type=int, default=6, help="Number of variants (max 9)")
    parser.add_argument("--quick", action="store_true", help="Trim search budgets for a fast smoke pass")
    parser.add_argument("--models", type=Path, default=ROOT / "models")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / "sync-corpus-01")
    parser.add_argument("--offsets", type=Path, default=None,
                        help="JSON file mapping variant IDs to synchronization applied_offsets "
                             "(e.g. jobs/sync-corpus-01/offsets-corpus-04.json)")
    parser.add_argument("--results-from", type=Path, default=None,
                        help="Reuse a prior corpus run's engine results: offsets change only the "
                             "timeline, never the engine search, so per-task result trees are exact")
    args = parser.parse_args()
    # Resolve path arguments to absolute paths. The engine subprocess runs
    # with cwd=plan_dir, so a relative --output-dir would otherwise make the
    # engine look for targets.csv relative to the plan directory instead of
    # the repo root (FileNotFoundError on every variant).
    args.output_dir = args.output_dir.resolve()
    args.models = args.models.resolve()
    args.document = args.document.resolve()
    args.results_from = args.results_from.resolve() if args.results_from else None
    if not args.models.is_dir():
        parser.error(f"models directory not found: {args.models}; run mechanism-models download first.")
    base = load_yaml(args.document)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    count = max(1, min(args.count, 9))
    offsets_by_variant = load_offsets(args.offsets) if args.offsets else {}
    summary_path = args.output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else []
    done = {row["task_set_id"] for row in summary}
    angles = [0, 35, 70, 110, 150, 195, 240, 285, 330]
    scales = [1.0, 0.9, 1.1, 0.85, 1.15, 0.95, 1.05, 0.8, 1.2]
    planned_ids = {f"corpus_pair_{index:02d}" for index in range(1, count + 1)}
    for variant in sorted(set(offsets_by_variant) - planned_ids):
        print(f"note: offsets entry {variant!r} is outside this run (count={count}); ignored", flush=True)
    failures = 0
    for index in range(1, count + 1):
        task_set_id = f"corpus_pair_{index:02d}"
        if task_set_id in done:
            print(f"skip {task_set_id} (already recorded)", flush=True)
            continue
        out_dir = args.output_dir / f"corpus_pair_{index:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        document = variant_document(base, index, angles[index - 1], scales[index - 1])
        if offsets_by_variant.get(task_set_id):
            document["synchronization"]["applied_offsets"] = offsets_by_variant[task_set_id]
        print(f"running {task_set_id} (angle {angles[index - 1]}, scale {scales[index - 1]})"
              + (f", offsets {document['synchronization'].get('applied_offsets')}"
                 if offsets_by_variant.get(task_set_id) else ""), flush=True)
        try:
            row = run_variant(document, out_dir, args.models, args.quick,
                              results_from=args.results_from)
        except Exception as exc:  # recorded as data; the corpus continues.
            row = {"task_set_id": task_set_id, "status": "error", "note": str(exc)}
            failures += 1
        summary.append(row)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"  -> {row['status']} ({row.get('total_seconds', '?')} s)", flush=True)
    print(f"Done: {len(summary)} variants recorded in {summary_path}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
