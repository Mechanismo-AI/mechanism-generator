#!/usr/bin/env python3
"""Generate, adapt, run, and verify a corpus of synchronized pair documents.

Deterministic variants of examples/omts/synchronized_pair.omts.yaml. Each
variant is validated, adapted, executed per-task with the installed engine,
and line-verified with the S4 verifier. Variants are independent; a failure
in one is recorded and does not stop the corpus. Completed variants are
skipped on rerun, so the job is resumable.

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


def rotate_scale(points, angle_deg: float, scale: float):
    angle = math.radians(angle_deg)
    cos, sin = math.cos(angle), math.sin(angle)
    return [[round(scale * (cos * x - sin * y), 4), round(scale * (sin * x + cos * y), 4)] for x, y in points]


def variant_document(base: dict, index: int, angle: float, scale: float) -> dict:
    document = json.loads(json.dumps(base))
    document["task_set_id"] = f"corpus_pair_{index:02d}"
    document["name"] = f"Synchronized pair corpus variant {index:02d}"
    for task in document["tasks"]:
        positions = [target["position"] for target in task["motion"]["targets"]]
        moved = rotate_scale(positions, angle, scale)
        for target, position in zip(task["motion"]["targets"], moved):
            target["position"] = position
    return document


def check_call(command, cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {command[:3]} ...\n{result.stdout}\n{result.stderr}")


def run_variant(document: dict, out_dir: Path, models: Path, quick: bool) -> dict:
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
    for run in plan["runs"]:
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
    return {
        "task_set_id": document["task_set_id"],
        "status": line_result["status"],
        "combination_count": line_result.get("combination_count"),
        "passing_combination_count": line_result.get("passing_combination_count"),
        "selected_counts": selected_counts,
        "task_times_seconds": task_times,
        "total_seconds": round(time.monotonic() - started, 1),
        "line_note": line_result.get("note"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=6, help="Number of variants (max 9)")
    parser.add_argument("--quick", action="store_true", help="Trim search budgets for a fast smoke pass")
    parser.add_argument("--models", type=Path, default=ROOT / "models")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs" / "sync-corpus-01")
    args = parser.parse_args()
    if not args.models.is_dir():
        parser.error(f"models directory not found: {args.models}; run mechanism-models download first.")
    base = load_yaml(BASE_DOCUMENT)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    count = max(1, min(args.count, 9))
    summary_path = args.output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else []
    done = {row["task_set_id"] for row in summary}
    angles = [0, 35, 70, 110, 150, 195, 240, 285, 330]
    scales = [1.0, 0.9, 1.1, 0.85, 1.15, 0.95, 1.05, 0.8, 1.2]
    failures = 0
    for index in range(1, count + 1):
        task_set_id = f"corpus_pair_{index:02d}"
        if task_set_id in done:
            print(f"skip {task_set_id} (already recorded)", flush=True)
            continue
        out_dir = args.output_dir / f"corpus_pair_{index:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        document = variant_document(base, index, angles[index - 1], scales[index - 1])
        print(f"running {task_set_id} (angle {angles[index - 1]}, scale {scales[index - 1]})", flush=True)
        try:
            row = run_variant(document, out_dir, args.models, args.quick)
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
