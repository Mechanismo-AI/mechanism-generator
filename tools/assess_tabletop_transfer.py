"""Independently assess the fixed tabletop-transfer example in millimetres.

Run from a source checkout; uses the NumPy circle geometry in benchmark_pose,
not the optimizer. Reads saved results and never runs or retrains a model.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import benchmark_pose as geometry

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/tabletop-transfer"


def assess(row, direction, brief):
    scale = brief["scale_mm_per_normalized_unit"]
    p = np.array([float(row[name]) for name in geometry.PARAMETER_NAMES])
    p[:4] *= scale
    p[5] *= scale
    p[6:8] = p[6:8] * scale + brief["origin_offset_mm"]
    phases = np.array([float(row[f"phase_{i}_rad"]) for i in (1, 2, 3)])
    branch = int(float(row["branch_sign"]))
    sign = 1 if direction == "positive" else -1
    at = geometry.analytic_geometry(p, phases, branch)
    cycle = geometry.full_cycle_checks(p)
    errors = np.linalg.norm(at["points"] - brief["targets_mm"], axis=1)
    angular = np.abs(geometry.circular_error_deg(at["orientations_deg"], brief["orientations_deg"]))
    gaps = (sign * (np.roll(phases, -1) - phases)) % (2 * math.pi)
    dense = geometry.analytic_geometry(p, np.linspace(0, 2 * math.pi, 7201), branch)
    angle = np.radians(dense["orientations_deg"])
    u = np.column_stack((np.cos(angle), np.sin(angle)))
    v = np.column_stack((-np.sin(angle), np.cos(angle)))
    half_width, half_height = np.array(brief["carrier_size_mm"]) / 2
    corners = np.concatenate([
        dense["points"] + x * u + y * v
        for x in (-half_width, half_width) for y in (-half_height, half_height)
    ])
    outline = np.vstack([dense["a"], dense["b"], corners, dense["o2"], dense["o4"]])
    low, high = outline.min(axis=0), outline.max(axis=0)
    panel = np.array([brief["panel_bounds_mm"][axis] for axis in ("x", "y")])
    fixed = np.vstack([dense["o2"], dense["o4"]])
    # The case study specifies 10 mm fixed-pivot edge clearance and the released
    # OMTS task specifies 15/10 degree target/global selection floors.
    checks = {
        "mean_position": bool(errors.mean() <= brief["mean_position_tolerance_mm"] + 1e-8),
        "maximum_position": bool(errors.max() <= brief["maximum_position_tolerance_mm"] + 1e-8),
        "orientation": bool(angular.max() <= brief["orientation_tolerance_deg"] + 1e-8),
        "target_assembly": bool(at["valid"].all()),
        "target_order": bool(abs(gaps.sum() - 2 * math.pi) < 1e-9 and min(gaps) > 0),
        "full_cycle_assembly": cycle["full_cycle_assembly"],
        "grashof": cycle["grashof"],
        "crank_shortest": cycle["crank_is_strictly_shortest"],
        "target_transmission": bool(at["transmission_deg"].min() >= 15 - 1e-7),
        "global_transmission": bool(cycle["global_minimum_transmission_deg"] >= 10 - 1e-7),
        "panel_fit": bool((low >= panel[:, 0]).all() and (high <= panel[:, 1]).all()),
        "pivot_clearance": bool((fixed >= panel[:, 0] + 10).all() and (fixed <= panel[:, 1] - 10).all()),
    }
    # Check the independent physical calculation against the saved engine result.
    np.testing.assert_allclose(
        [errors.mean(), errors.max(), angular.max()],
        [float(row["mean_error"]) * scale, float(row["max_error"]) * scale,
        float(row["max_orientation_error_deg"])], rtol=0, atol=1e-6,
    )
    if row.get("panel_required", "").lower() == "true":
        expected_panel = checks["panel_fit"] and checks["pivot_clearance"] and bool(dense["valid"].all())
        assert (row["panel_acceptable"].lower() == "true") == expected_panel
        if row["panel_geometry_valid"].lower() == "true":
            np.testing.assert_allclose(
                [low, high],
                np.array([[float(row["panel_envelope_x_min"]), float(row["panel_envelope_y_min"])],
                          [float(row["panel_envelope_x_max"]), float(row["panel_envelope_y_max"])]]) * scale + brief["origin_offset_mm"],
                rtol=0, atol=1e-6)
    return {
        "id": direction + "-" + row["candidate_id"], "direction": direction,
        "branch": branch, "parameters_mm": p.tolist(), "phases_rad": phases.tolist(),
        "position_errors_mm": errors.tolist(), "orientation_errors_deg": angular.tolist(),
        "mean_position_error_mm": float(errors.mean()),
        "maximum_position_error_mm": float(errors.max()),
        "maximum_orientation_error_deg": float(angular.max()),
        "achieved_points_mm": at["points"].tolist(),
        "achieved_orientations_deg": at["orientations_deg"].tolist(),
        "global_minimum_transmission_deg": cycle["global_minimum_transmission_deg"],
        "target_minimum_transmission_deg": float(at["transmission_deg"].min()),
        "envelope_min_mm": low.tolist(), "envelope_max_mm": high.tolist(),
        "phase_progress_deg": np.degrees((sign * (phases - phases[0])) % (2 * math.pi)).tolist(),
        "checks": checks, "failed_checks": [key for key, passed in checks.items() if not passed],
        "engine_selection_eligible": row["selection_eligible"].lower() == "true",
        "brief_passed": all(checks.values()),
        "pose_tolerance_ratio": max(float(errors.mean()) / brief["mean_position_tolerance_mm"],
                                    float(errors.max()) / brief["maximum_position_tolerance_mm"],
                                    float(angular.max()) / brief["orientation_tolerance_deg"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="Directory containing one either-direction run")
    parser.add_argument("--output", type=Path, required=True, help="New assessment JSON file")
    args = parser.parse_args()
    brief_path = EXAMPLE / "design-brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    manifests = sorted(args.results.rglob("run_manifest.json"))
    if len(manifests) != 2:
        parser.error("Expected exactly two run manifests, one per crank direction")
    expected = (np.array(brief["targets_mm"]) - brief["origin_offset_mm"]) / brief["scale_mm_per_normalized_unit"]
    records, identities, counts = [], [], {}
    for file in manifests:
        manifest = json.loads(file.read_text(encoding="utf-8"))
        direction = manifest["arguments"]["crank_direction"]
        if manifest["run_status"] != "completed" or len(manifest["targets"]) != 1:
            parser.error("Expected a completed single-task run in each direction")
        if direction not in ("positive", "negative") or direction in counts:
            parser.error("Expected one positive and one negative run")
        task = manifest["targets"][0]
        np.testing.assert_allclose(task["target_values"], expected.ravel(), rtol=0, atol=1e-12)
        np.testing.assert_allclose(task["target_orientations_deg"], brief["orientations_deg"], rtol=0, atol=1e-12)
        np.testing.assert_allclose(task["orientation_tolerances_deg"], [brief["orientation_tolerance_deg"]] * 3)
        folder = (file.parent / task["directory"]).resolve()
        if not folder.is_relative_to(file.parent.resolve()):
            parser.error("Target directory must stay inside its run directory")
        with (folder / "all_candidates.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != task["candidate_count"]:
            parser.error("Candidate count disagrees with the saved manifest")
        with (folder / "selected_candidates.csv").open(encoding="utf-8", newline="") as handle:
            selected_ids = {row["candidate_id"] for row in csv.DictReader(handle)}
        assert len(selected_ids) == task["selected_count"]
        for row in rows:
            record = assess(row, direction, brief)
            record["engine_selected"] = row["candidate_id"] in selected_ids
            if record["engine_selected"]:
                assert record["brief_passed"] and record["engine_selection_eligible"]
            records.append(record)
        counts[direction] = {"all": len(rows), "engine_selected": task["selected_count"],
                             "engine_eligible": sum(r["selection_eligible"].lower() == "true" for r in rows),
                             "pose_initializer": task["pose_initialization"]}
        identities.append({"direction": direction, "seed": manifest["seed"],
                           "engine_sha256": manifest["engine_sha256"], "portfolio_sha256": manifest["script_sha256"],
                           **{key: manifest[key] for key in ("orientation_sha256", "pose_initialization_sha256", "panel_screening_sha256") if key in manifest},
                           "models": [{k: model[k] for k in ("role", "sha256")} for model in manifest["models"]]})
    diagnostics = [min(group, key=lambda r: r["pose_tolerance_ratio"])
                   for direction in ("positive", "negative")
                   if (group := [r for r in records if r["direction"] == direction and not r["brief_passed"]])]
    report = {"brief_sha256": hashlib.sha256(brief_path.read_bytes()).hexdigest(),
              "unit_conversion_verified_by_independent_physical_geometry": True,
              "engine_counts": counts, "identity": identities, "all_candidate_assessments": records,
              "passing_candidates": sum(r["brief_passed"] and r["engine_selection_eligible"] for r in records),
              "diagnostic_rejected_candidates": diagnostics,
              "diagnostic_selection_rule": "Smallest worst pose-tolerance ratio per direction: max(mean position / 1 mm, maximum position / 1.5 mm, maximum angle / 3 deg). Excludes panel fit from ranking; does not qualify candidates.",
              "limitations": ["Panel fit samples 7201 phases; it is not analytic continuous containment.",
                              "Link centrelines and carrier corners only; no thickness, bearings, collisions, loads or manufacturing checks.",
                              "Orientation is constrained at three target phases only. No timing, dwell or speed requirement."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Assessed {len(records)} candidates; {report['passing_candidates']} meet the brief and engine eligibility.")


if __name__ == "__main__":
    main()
