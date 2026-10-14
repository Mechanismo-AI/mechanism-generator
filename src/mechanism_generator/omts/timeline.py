"""Composed timeline artifact for OMTS synchronized lines (G4).

The timeline artifact promised by section 8 of ``synchronization.md``: for
sampled master phases, each participating task's input crank phase and
sampled body poses per selected candidate -- the collision and animation
substrate. Composition follows the same anchoring and applied-offset rule
as the timeline verifier: an anchored task's ``phase_reference`` target
sits at master phase 0 (moved to its applied offset when one is declared),
and tasks without a reference contribute raw phases (then rotated by any
applied offset). The artifact is data-only: it never gates a verdict.
Undefined assembly at a sampled phase is an error, never a guessed pose.
"""

from __future__ import annotations

import json
from pathlib import Path

from .geometry import MAX_STEPS, METHOD, MIN_STEPS, PARAM_NAMES, four_bar_skeleton
from .line_verify import (
    LineVerificationError,
    _candidate_geometry,
    _manifest_rows,
    run_target_ids,
)

TIMELINE_VERSION = 1


def _participating(line: dict) -> set[str]:
    return (
        line["phase_reference"].keys()
        | {
            participant["task"]
            for event in line["events"]
            for participant in event["participants"]
        }
        | {
            relation[key]["task"]
            for relation in line["relations"]
            for key in ("from", "to")
        }
    )


def _carrier(line: dict, task: str) -> tuple | None:
    model = (line.get("collision") or {}).get(task) or {}
    if "carrier" not in model:
        return None
    return (model["carrier"]["width"], model["carrier"]["depth"])


def _pose(skeleton: dict) -> dict:
    def point(value) -> list:
        return [round(float(value[0]), 6), round(float(value[1]), 6)]

    return {
        "o2": point(skeleton["o2"]),
        "o4": point(skeleton["o4"]),
        "a": point(skeleton["a"]),
        "b": point(skeleton["b"]),
        "p": point(skeleton["p"]),
        "carrier_corners": [point(corner) for corner in skeleton["carrier_corners"]],
    }


def compose_timeline(plan_dir: str | Path, steps: int = 720) -> dict:
    """Compose the sampled timeline of a prepared plan; data-only.

    Reads the plan's line section and each task's latest completed
    positive-direction run manifest, and never reruns the solver.
    """
    if (isinstance(steps, bool) or not isinstance(steps, int)
            or not MIN_STEPS <= steps <= MAX_STEPS):
        raise LineVerificationError(
            f"Timeline sampling requires an integer step count between "
            f"{MIN_STEPS} and {MAX_STEPS}; got {steps!r}.")
    plan_dir = Path(plan_dir)
    plan = json.loads((plan_dir / "run_plan.json").read_text(encoding="utf-8"))
    if "line" not in plan:
        raise LineVerificationError(
            "The plan contains no synchronization line; no composed timeline exists.")
    line = plan["line"]
    offsets = line.get("applied_offsets") or {}
    participating = _participating(line)
    stray = set(offsets) - participating
    if stray:
        raise LineVerificationError(
            f"applied_offsets name non-participating task(s): {', '.join(sorted(stray))}.")
    tasks: dict = {}
    for task in sorted(participating):
        rows = _manifest_rows(plan, plan_dir, task)
        if not rows:
            raise LineVerificationError(
                f"Task '{task}' selected zero candidates; the timeline is never guessed.")
        target_ids = run_target_ids(plan, task)
        reference = line["phase_reference"].get(task)
        if reference is not None and reference not in target_ids:
            raise LineVerificationError(
                f"Task '{task}': phase_reference target '{reference}' is not one "
                f"of its recorded run targets.")
        reference_index = target_ids.index(reference) + 1 if reference is not None else None
        carrier = _carrier(line, task)
        candidates = []
        for row in rows:
            candidate_id = str(row["candidate_id"])
            params, branch_sign = _candidate_geometry(row, task)
            if reference is not None:
                raw = row.get(f"phase_{reference_index}_deg")
                if raw is None:
                    raise LineVerificationError(
                        f"Task '{task}': candidate '{candidate_id}' lacks "
                        f"phase_{reference_index}_deg.")
                reference_phase = float(raw)
            else:
                reference_phase = None
            shift = (
                offsets.get(task, 0.0) - reference_phase
                if reference_phase is not None else offsets.get(task, 0.0)
            )
            candidate = {
                "candidate_id": candidate_id,
                "parameters": dict(zip(PARAM_NAMES, [float(value) for value in params])),
                "branch_sign": branch_sign,
                "reference_phase_deg": (
                    None if reference_phase is None
                    else round(reference_phase % 360.0, 6)
                ),
                "shift_deg": round(shift, 6),
                "input_phase_deg": [],
                "poses": [],
            }
            for index in range(steps):
                master = 360.0 * index / steps
                theta = round((master - shift) % 360.0, 6) % 360.0
                skeleton = four_bar_skeleton(params, branch_sign, theta, carrier=carrier)
                if skeleton is None:
                    raise LineVerificationError(
                        f"Task '{task}', candidate '{candidate_id}': the assembly is "
                        f"undefined at master phase {master:g} deg (input phase "
                        f"{theta:g} deg); poses are never guessed.")
                candidate["input_phase_deg"].append(theta)
                candidate["poses"].append(_pose(skeleton))
            candidates.append(candidate)
        tasks[task] = {"candidates": candidates}
    return {
        "timeline_version": TIMELINE_VERSION,
        "method": METHOD,
        "task_set_id": plan["task_set_id"],
        "master_cycle_id": line["master_cycle_id"],
        "period": line["period"],
        "steps": steps,
        "sample_step_deg": round(360.0 / steps, 6),
        "phase_reference": line["phase_reference"],
        **({"applied_offsets": line["applied_offsets"]} if line.get("applied_offsets") else {}),
        "tasks": tasks,
        "note": (
            "Composed timeline (G4): for sampled master phases, each participating "
            "task's input crank phase and sampled body poses per selected candidate, "
            "composed with the same anchoring and applied-offset rule as "
            "omts verify-line. Data-only: this artifact never gates the verdict."
        ),
        "disclaimer": (
            "Sampled timeline, not certified: it proves nothing between samples, "
            "performs no occupancy or clearance checking, and is not collision, "
            "thickness, or machinery certification."
        ),
    }


def write_timeline(plan_dir: str | Path, timeline: dict) -> Path:
    """Write the compact timeline artifact next to the plan that composed it."""
    path = Path(plan_dir) / "timeline.json"
    path.write_text(json.dumps(timeline, separators=(",", ":")) + "\n", encoding="utf-8")
    return path
