"""Post-hoc verification of a prepared synchronization line (S4).

Reads a prepared run plan's line section and the achieved results of each
per-task R2.5c run, then checks every event and relation on the composed
timeline. This verifier never runs a solver and never modifies results.

Composed-timeline rule: every task's `phase_reference` target is aligned at
master phase 0; tasks without a phase_reference contribute raw achieved
phases. A task's reference target is therefore always at phase 0 and cannot
itself sit inside a nonzero master-phase window.

Applied master-phase offsets (S5 v0.1): a line may declare
`applied_offsets` (per task, in degrees); they are recorded in the plan
line section by the adapter and this verifier composes with them, so a line
can be legitimately verified under a declared phasing. For an anchored task
the offset moves its reference target to the stated phase; realization of
the declared phasing (gear/crank choice) remains a build decision.

The optional anchor probe (`probe=True`; CLI: `omts verify-line
--probe-anchors`) is a diagnostic sweep toward S5: for each task in
isolation, it asks which constant master-phase offsets would make at least
one candidate combination satisfy every hard event and relation. It reuses
the same checks on shifted composed phases and never reruns the solver.
Probe offsets are relative to the declared composition and deliberately move
an anchored task's reference target away from its declared phase; they are
feasibility targets for joint search and gear/crank phasing choices, never
verified solutions, and probing never changes the baseline verdict of the run.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

from .adapter import UnsupportedFeature


class LineVerificationError(ValueError):
    """The line cannot be verified from the available artifacts."""


def _load_plan(plan_dir: str | Path) -> dict:
    plan_dir = Path(plan_dir)
    plan = json.loads((plan_dir / "run_plan.json").read_text(encoding="utf-8"))
    if "line" not in plan:
        raise LineVerificationError("The plan contains no synchronization line; nothing to verify.")
    return plan


def _achieved_candidates(plan: dict, plan_dir: Path, task_id: str, target_ids: list[str]) -> dict:
    """Return {candidate_id: {target_id: anchored-unanchored achieved phase in deg}} for one task."""
    run = next((r for r in plan["runs"] if r["task_id"] == task_id), None)
    if run is None:
        raise LineVerificationError(f"Task '{task_id}' has no run in the plan.")
    roots = sorted((plan_dir / run["output_root"]).glob("r25c/*/run_manifest.json"))
    if not roots:
        raise LineVerificationError(f"Task '{task_id}': no completed run manifest under {run['output_root']}.")
    manifest = json.loads(roots[-1].read_text(encoding="utf-8"))
    if manifest.get("run_status") != "completed":
        raise LineVerificationError(f"Task '{task_id}': run status is {manifest.get('run_status')!r}, not 'completed'.")
    direction = manifest["targets"][0].get("crank_direction", "positive")
    if direction != "positive":
        raise LineVerificationError(f"Task '{task_id}': crank_direction {direction!r} is not supported by the timeline verifier yet; use a positive-direction run.")
    candidates: dict[str, dict[str, float]] = {}
    for row in manifest["targets"][0].get("selected", []):
        phases = {}
        for index, target_id in enumerate(target_ids, start=1):
            phase = row.get(f"phase_{index}_deg")
            if phase is None:
                raise LineVerificationError(f"Task '{task_id}': candidate {row.get('candidate_id')} lacks phase_{index}_deg.")
            phases[target_id] = float(phase) % 360.0
        candidates[str(row["candidate_id"])] = phases
    return candidates


def _anchored(phases: dict[str, float], reference: str | None, target: str) -> float:
    value = phases[target]
    if reference is not None:
        value = (value - phases[reference]) % 360.0
    return value


def _lead(a: float, b: float) -> float:
    """Phase of b measured from a, positive in cycle direction, in [0, 360)."""
    return (b - a) % 360.0


def _check_event(event: dict, anchored: dict) -> dict:
    phases = [anchored[participant["task"]][participant["target"]] for participant in event["participants"]]
    low, high = event["window_deg"]
    tolerance = event.get("tolerance_deg") or 0.0
    inside = all(low - tolerance <= phase <= high + tolerance for phase in phases)
    return {
        "id": event["id"],
        "mode": event.get("mode", "hard"),
        "participant_phases_deg": phases,
        "window_deg": [low, high],
        "status": "pass" if inside else "fail",
    }


def _check_relation(relation: dict, anchored: dict) -> dict:
    a = anchored[relation["from"]["task"]][relation["from"]["target"]]
    b = anchored[relation["to"]["task"]][relation["to"]["target"]]
    lead = _lead(a, b)
    if relation["type"] == "ordering":
        ok = relation["min_lead_deg"] <= lead <= relation["max_lead_deg"]
        detail = {"min_lead_deg": relation["min_lead_deg"], "max_lead_deg": relation["max_lead_deg"]}
    else:
        offset = relation["offset_deg"] % 360.0
        tolerance = relation.get("tolerance_deg", 0.0)
        ok = _lead(offset, lead) <= tolerance or _lead(lead, offset) <= tolerance
        detail = {"offset_deg": offset, "tolerance_deg": tolerance}
    return {
        "id": relation["id"],
        "type": relation["type"],
        "mode": relation.get("mode", "hard"),
        "achieved_lead_deg": round(lead, 6),
        **detail,
        "status": "pass" if ok else "fail",
    }


def _anchored_map(achieved: dict, line: dict, chosen: dict[str, str]) -> dict[str, dict[str, float]]:
    """Composed (anchored, applied-offset) phases in deg for one candidate combination."""
    offsets = line.get("applied_offsets") or {}
    return {
        task: {
            target: (_anchored(achieved[task][candidate], line["phase_reference"].get(task), target)
                     + offsets.get(task, 0.0)) % 360.0
            for target in achieved[task][candidate]
        }
        for task, candidate in chosen.items()
    }


def _shifted(anchored: dict, task: str, offset_deg: float) -> dict:
    """Copy of composed phases with one task rotated by offset_deg."""
    if not offset_deg:
        return anchored
    shifted = {name: dict(phases) for name, phases in anchored.items()}
    shifted[task] = {target: (phase + offset_deg) % 360.0 for target, phase in shifted[task].items()}
    return shifted


def _hard_pass(line: dict, anchored: dict) -> bool:
    """True when every hard event and relation passes for these composed phases."""
    for event in line["events"]:
        if event.get("mode", "hard") == "hard" and _check_event(event, anchored)["status"] != "pass":
            return False
    for relation in line["relations"]:
        if relation.get("mode", "hard") == "hard" and _check_relation(relation, anchored)["status"] != "pass":
            return False
    return True


def _positive_intervals(offsets: list[float], counts: list[int]) -> list[dict]:
    """Circular inclusive [from_deg, to_deg] intervals where counts are positive."""
    n = len(counts)
    runs: list[tuple[int, int]] = []
    start = None
    for index, count in enumerate(counts):
        if count > 0 and start is None:
            start = index
        elif count == 0 and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, n - 1))
    if not runs:
        return []
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == n - 1:
        first = runs.pop(0)
        last = runs.pop()
        runs.insert(0, (last[0], first[1]))

    def run_max(begin: int, end: int) -> int:
        if begin <= end:
            return max(counts[begin:end + 1])
        return max(counts[begin:] + counts[:end + 1])

    return [
        {"from_deg": offsets[begin], "to_deg": offsets[end], "max_passing_combinations": run_max(begin, end)}
        for begin, end in runs
    ]


def _probe_anchors(line: dict, achieved: dict, step_deg: float) -> dict:
    """Sweep per-task master-phase offsets and report feasible intervals (diagnostic)."""
    step_deg = float(step_deg)
    steps = int(round(360.0 / step_deg))
    offsets = [round(index * step_deg, 6) % 360.0 for index in range(steps)]
    task_ids = sorted(achieved)
    base = [
        _anchored_map(achieved, line, dict(zip(task_ids, combination)))
        for combination in itertools.product(*(sorted(achieved[task]) for task in task_ids))
    ]
    tasks = []
    for task in task_ids:
        counts = [
            sum(1 for anchored in base if _hard_pass(line, _shifted(anchored, task, offset)))
            for offset in offsets
        ]
        best = max(counts, default=0)
        tasks.append({
            "task": task,
            "passing_offsets_count": sum(1 for count in counts if count > 0),
            "best_passing_combinations": best,
            "best_offsets_deg": [offsets[index] for index, count in enumerate(counts) if count == best] if best else [],
            "feasible_intervals_deg": _positive_intervals(offsets, counts),
        })
    return {
        "step_deg": step_deg,
        "tasks": tasks,
        "note": (
            "Diagnostic master-phasing sweep for S5: each task's composed phases are rotated by every offset while all other tasks stay fixed. Feasible intervals list offsets where at least one candidate combination satisfies every hard event and relation. Offsets are feasibility targets for joint search and gear/crank phasing, not verified solutions; an offset applied to an anchored task moves its reference target away from its declared phase. The baseline verdict is unchanged."
        ),
    }


def verify_line(plan_dir: str | Path, probe: bool = False, probe_step_deg: float = 1.0) -> dict:
    plan_dir = Path(plan_dir)
    plan = _load_plan(plan_dir)
    line = plan["line"]
    participating = line["phase_reference"].keys() | {
        participant["task"]
        for event in line["events"]
        for participant in event["participants"]
    } | {
        relation[key]["task"]
        for relation in line["relations"]
        for key in ("from", "to")
    }
    stray = set(line.get("applied_offsets") or {}) - participating
    if stray:
        raise LineVerificationError(f"applied_offsets name non-participating task(s): {', '.join(sorted(stray))}.")
    achieved = {
        task: _achieved_candidates(plan, plan_dir, task, run_target_ids(plan, task))
        for task in sorted(participating)
    }
    empty = [task for task, candidates in achieved.items() if not candidates]
    if empty:
        result = _result(plan, line, combinations=[], status="no_candidates",
                         note=f"Zero selected candidates for: {', '.join(empty)}; a completed search selecting nothing is recorded, not treated as an error.")
        if probe:
            result["anchor_probe"] = {"status": "skipped", "note": "No candidate combinations to sweep."}
        _write(plan_dir, result)
        return result

    task_ids = sorted(achieved)
    combinations = []
    def walk(index: int, chosen: dict[str, str]) -> None:
        if index == len(task_ids):
            anchored = _anchored_map(achieved, line, chosen)
            events = [_check_event(event, anchored) for event in line["events"]]
            relations = [_check_relation(relation, anchored) for relation in line["relations"]]
            hard_ok = all(item["status"] == "pass" for item in events + relations if item["mode"] == "hard")
            soft_failed = [item["id"] for item in events + relations if item["mode"] == "soft" and item["status"] == "fail"]
            combinations.append({
                "candidates": dict(chosen),
                "events": events,
                "relations": relations,
                "status": "pass" if hard_ok else "fail",
                "soft_failures": soft_failed,
            })
            return
        for candidate in sorted(achieved[task_ids[index]]):
            chosen[task_ids[index]] = candidate
            walk(index + 1, chosen)
        chosen.pop(task_ids[index], None)

    walk(0, {})
    passing = [c for c in combinations if c["status"] == "pass"]
    status = "verified" if passing else "failed"
    result = _result(plan, line, combinations, status,
                     note=None if passing else "No combination of selected candidates satisfies every hard event and relation.")
    if probe:
        step = float(probe_step_deg)
        if not 0.0 < step <= 360.0:
            raise LineVerificationError(f"Probe step must be in (0, 360] deg; got {step}.")
        result["anchor_probe"] = _probe_anchors(line, achieved, step)
    _write(plan_dir, result)
    return result


def run_target_ids(plan: dict, task_id: str) -> list[str]:
    run = next(r for r in plan["runs"] if r["task_id"] == task_id)
    return run["target_ids"]


def _result(plan: dict, line: dict, combinations: list, status: str, note: str | None) -> dict:
    return {
        "line_verification_version": 1,
        "task_set_id": plan["task_set_id"],
        "master_cycle_id": line["master_cycle_id"],
        "period": line["period"],
        "status": status,
        "phase_reference": line["phase_reference"],
        **({"applied_offsets": line["applied_offsets"]} if line.get("applied_offsets") else {}),
        "combination_count": len(combinations),
        "passing_combination_count": sum(c["status"] == "pass" for c in combinations),
        "combinations": combinations,
        **({"note": note} if note else {}),
        "disclaimer": "Post-hoc timeline verification of kinematic results; not synchronization synthesis, dynamics, collision, or machinery certification.",
    }


def _write(plan_dir: Path, result: dict) -> None:
    (plan_dir / "line_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
