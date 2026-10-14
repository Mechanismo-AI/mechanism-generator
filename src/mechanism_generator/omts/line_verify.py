"""Post-hoc verification of a prepared synchronization line (S4).

Reads a prepared run plan's line section and the achieved results of each
per-task R2.5c run, then checks every event and relation on the composed
timeline. This verifier never runs a solver and never modifies results.

Collision occupancy (G3): when the plan's line section records regions and
per-task collision body models, this verifier computes, for every selected
candidate and declared region, the sampled phases where the declared bodies
occupy the region -- raw windows in the task's own crank angle, plus composed
windows under the same anchoring and applied-offset rule as the timeline.
The section is data only: it is reported in `line_result.json` under
`collision` with the sampled-geometry method tag, never gates the verdict,
and its boundaries are sampled phases, not certified instants. Relations
over the derived region events gate the verdict from G5; until then the
adapter rejects them at plan time.

Composed-timeline rule: every task's `phase_reference` target is aligned at
master phase 0; tasks without a phase_reference contribute raw achieved
phases. A task's reference target is therefore always at phase 0 and cannot
itself sit inside a nonzero master-phase window.

Applied master-phase offsets (S5 v0.1): a line may declare
`applied_offsets` (per task, in degrees); they are recorded in the plan
line section by the adapter and this verifier composes with them, so a line
can be legitimately verified under a declared phasing. For an anchored task
the offset moves its reference target to the stated phase; realization of
the declared phasing (gear/crank choice) remains a build decision, recorded
via the document's `offset_realization` and echoed in `line_result.json`
(`recorded`, per-task records, `unrecorded_tasks`) — a build note that
never changes the verdict.

Ordering feasibility precheck: `line_result.json` reports, for each hard
cross-task ordering relation, the circular spread of the combinations'
achieved leads against the relation's band width, with `phasing_cannot_fix`
marking relations that no shared phasing can satisfy for every combination
(constant phasing shifts every combination's lead by the same amount, so the
family is rigid and slide-only). The precheck is a necessary-condition
diagnostic that never changes the verdict.

The optional anchor probe (`probe=True`; CLI: `omts verify-line
--probe-anchors`) is a diagnostic sweep toward S5: for each task in
isolation, it asks which constant master-phase offsets would make at least
one candidate combination satisfy every hard event and relation. It reuses
the same checks on shifted composed phases and never reruns the solver.
Probe offsets are relative to the declared composition and deliberately move
an anchored task's reference target away from its declared phase; they are
feasibility targets for joint search and gear/crank phasing choices, never
verified solutions, and probing never changes the baseline verdict of the run.

The joint offset solver (`solve_offsets`; CLI: `omts propose-offsets`) is the
S5 search step itself: it grid-searches per-task master-phase offsets jointly
over the existing per-task results and reports the assignments that maximize
the number of passing candidate combinations. Recommendations are absolute:
they replace any declared `applied_offsets`, because the solver composes
from raw achieved phases. The output is a proposal (`offsets_proposal.json`)
only — it never writes a verdict, and a human must declare the chosen
offsets in the document, then re-validate, re-adapt, and re-verify before a
line can be called verified under them.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

from .adapter import UnsupportedFeature
from .geometry import METHOD as COLLISION_METHOD, PARAM_NAMES, occupancy_windows


class LineVerificationError(ValueError):
    """The line cannot be verified from the available artifacts."""


def _load_plan(plan_dir: str | Path) -> dict:
    plan_dir = Path(plan_dir)
    plan = json.loads((plan_dir / "run_plan.json").read_text(encoding="utf-8"))
    if "line" not in plan:
        raise LineVerificationError("The plan contains no synchronization line; nothing to verify.")
    return plan


def _manifest_rows(plan: dict, plan_dir: Path, task_id: str) -> list[dict]:
    """Selected candidate rows of a task's latest completed positive-direction run."""
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
    return manifest["targets"][0].get("selected", [])


def _achieved_candidates(plan: dict, plan_dir: Path, task_id: str, target_ids: list[str]) -> dict:
    """Return {candidate_id: {target_id: anchored-unanchored achieved phase in deg}} for one task."""
    candidates: dict[str, dict[str, float]] = {}
    for row in _manifest_rows(plan, plan_dir, task_id):
        phases = {}
        for index, target_id in enumerate(target_ids, start=1):
            phase = row.get(f"phase_{index}_deg")
            if phase is None:
                raise LineVerificationError(f"Task '{task_id}': candidate {row.get('candidate_id')} lacks phase_{index}_deg.")
            phases[target_id] = float(phase) % 360.0
        candidates[str(row["candidate_id"])] = phases
    return candidates


def _candidate_geometry(row: dict, task_id: str) -> tuple[list[float], float]:
    """Candidate parameter vector in PARAM_NAMES order plus its assembly branch sign."""
    values = []
    for name in PARAM_NAMES:
        if name not in row:
            raise LineVerificationError(f"Task '{task_id}': manifest row lacks '{name}'.")
        values.append(float(row[name]))
    if "branch_sign" not in row:
        raise LineVerificationError(f"Task '{task_id}': manifest row lacks 'branch_sign'.")
    return values, float(row["branch_sign"])


def _collision_section(plan: dict, plan_dir: Path, line: dict, achieved: dict) -> dict | None:
    """Sampled region occupancy per task, candidate, and region (data only).

    Raw windows are computed in each task's own crank angle; composed windows
    apply the same anchoring and applied-offset rule as the timeline. The
    section never changes the verdict; relations over the derived events gate
    from G5.
    """
    regions = line.get("regions")
    if not regions:
        return None
    models = line.get("collision") or {}
    offsets = line.get("applied_offsets") or {}
    notes = []
    if not models:
        notes.append("No task declares a collision body model; no occupancy windows were computed.")
    unreported = sorted(set(models) - set(achieved))
    if unreported:
        notes.append("No achieved results for the task(s) with collision body models: " + ", ".join(unreported) + ".")
    tasks = {}
    for task in sorted(set(models) & set(achieved)):
        model = models[task]
        reference = line["phase_reference"].get(task)
        target_ids = run_target_ids(plan, task)
        if reference is not None and reference not in target_ids:
            raise LineVerificationError(f"Task '{task}': phase_reference target '{reference}' is not one of its recorded run targets.")
        reference_index = target_ids.index(reference) + 1 if reference is not None else None
        carrier = (model["carrier"]["width"], model["carrier"]["depth"]) if "carrier" in model else None
        candidates = []
        for row in _manifest_rows(plan, plan_dir, task):
            candidate_id = str(row["candidate_id"])
            if candidate_id not in achieved[task]:
                continue
            params, branch_sign = _candidate_geometry(row, task)
            if reference is not None:
                shift = offsets.get(task, 0.0) - float(row[f"phase_{reference_index}_deg"])
            else:
                shift = offsets.get(task, 0.0)
            region_entries = {}
            for region in regions:
                region_id = region["id"]
                try:
                    windows = occupancy_windows(params, branch_sign, region, model["steps"],
                                                thickness=model["thickness"], carrier=carrier)
                except ValueError as exc:
                    raise LineVerificationError(f"Task '{task}': candidate '{candidate_id}' region '{region_id}': {exc}") from exc
                region_entries[region_id] = {
                    "windows": windows,
                    "enters_deg": [window["start_deg"] for window in windows],
                    "exits_deg": [window["end_deg"] for window in windows],
                    "composed_windows": [
                        {"start_deg": (window["start_deg"] + shift) % 360.0,
                         "end_deg": (window["end_deg"] + shift) % 360.0}
                        for window in windows
                    ],
                    "composed_enters_deg": [(window["start_deg"] + shift) % 360.0 for window in windows],
                    "composed_exits_deg": [(window["end_deg"] + shift) % 360.0 for window in windows],
                }
            candidates.append({"id": candidate_id, "regions": region_entries})
        tasks[task] = {
            "steps": model["steps"],
            "mode": model["mode"],
            "thickness": model["thickness"],
            **({"carrier": model["carrier"]} if "carrier" in model else {}),
            "candidates": candidates,
        }
    section = {
        "method": COLLISION_METHOD,
        "regions": [region["id"] for region in regions],
        "tasks": tasks,
        "note": (
            "Data-only sampled occupancy (G3): raw windows are in each task's own crank angle; "
            "composed windows apply the same anchoring and applied-offset rule as the timeline. "
            "Relations over these derived events gate the verdict from G5; until then this section "
            "reports data and never changes the verdict. Window boundaries are sampled phases, "
            "not certified instants."
        ),
        "disclaimer": "Sampled occupancy, not certified: nothing is proven between samples; not collision, thickness, or machinery certification.",
    }
    if notes:
        section["notes"] = notes
    return section


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

    collision = _collision_section(plan, plan_dir, line, achieved)
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
                     note=None if passing else "No combination of selected candidates satisfies every hard event and relation.",
                     collision=collision)
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


def _realization_summary(line: dict) -> dict | None:
    """Visible build-record gap for declared offsets; never changes the verdict."""
    offsets = line.get("applied_offsets") or {}
    if not offsets:
        return None
    realization = line.get("offset_realization") or {}
    unrecorded = sorted(set(offsets) - set(realization))
    return {
        "recorded": not unrecorded,
        "tasks": {task: realization[task] for task in offsets if task in realization},
        **({"unrecorded_tasks": unrecorded} if unrecorded else {}),
    }


def _circular_spread(values: list[float]) -> float:
    """Shortest arc (deg) containing every value; 0.0 for fewer than two distinct values."""
    points = sorted({value % 360.0 for value in values})
    if len(points) <= 1:
        return 0.0
    gaps = [b - a for a, b in zip(points, points[1:])]
    gaps.append(points[0] + 360.0 - points[-1])
    return 360.0 - max(gaps)


def _ordering_feasibility(line: dict, combinations: list) -> dict | None:
    """Per-relation phasing feasibility for hard cross-task ordering relations.

    A constant per-task phasing shifts every candidate combination's achieved
    lead for a cross-task ordering relation by the same amount (the offset
    difference), so the lead family is rigid and slide-only: a shared phasing
    can satisfy the relation for every combination only when the combinations'
    leads fit inside one ordering band. The spread is measured circularly.
    `phasing_cannot_fix` is a necessary condition, not a sufficient one, and
    never changes the verdict. Same-task ordering relations are excluded:
    their leads are phasing-invariant and their per-combination statuses
    already report the exact outcome.
    """
    cross = [
        relation for relation in line["relations"]
        if relation["type"] == "ordering" and relation.get("mode", "hard") == "hard"
        and relation["from"]["task"] != relation["to"]["task"]
    ]
    if not cross or not combinations:
        return None
    entries = []
    for relation in cross:
        leads = [
            next(item["achieved_lead_deg"] for item in combo["relations"] if item["id"] == relation["id"])
            for combo in combinations
        ]
        band = relation["max_lead_deg"] - relation["min_lead_deg"]
        spread = _circular_spread(leads)
        entries.append({
            "id": relation["id"],
            "lead_spread_deg": round(spread, 6),
            "band_width_deg": round(band, 6),
            "phasing_cannot_fix": spread > band,
        })
    return {
        "relations": entries,
        "note": (
            "Per-relation phasing feasibility for hard cross-task ordering relations: constant "
            "per-task phasing shifts every combination's achieved lead by the same amount, so a "
            "shared phasing can satisfy the relation for every combination only when the leads' "
            "circular spread fits the ordering band. phasing_cannot_fix=true marks relations no "
            "offset assignment can satisfy for every combination (candidate-level change needed). "
            "A necessary-condition diagnostic that never changes the verdict; the authoritative "
            "search remains `omts propose-offsets`."
        ),
    }


def _result(plan: dict, line: dict, combinations: list, status: str, note: str | None,
            collision: dict | None = None) -> dict:
    realization = _realization_summary(line)
    feasibility = _ordering_feasibility(line, combinations)
    return {
        "line_verification_version": 1,
        "task_set_id": plan["task_set_id"],
        "master_cycle_id": line["master_cycle_id"],
        "period": line["period"],
        "status": status,
        "phase_reference": line["phase_reference"],
        **({"applied_offsets": line["applied_offsets"]} if line.get("applied_offsets") else {}),
        **({"offset_realization": realization} if realization is not None else {}),
        **({"ordering_feasibility": feasibility} if feasibility is not None else {}),
        **({"collision": collision} if collision is not None else {}),
        "combination_count": len(combinations),
        "passing_combination_count": sum(c["status"] == "pass" for c in combinations),
        "combinations": combinations,
        **({"note": note} if note else {}),
        "disclaimer": "Post-hoc timeline verification of kinematic results; not synchronization synthesis, dynamics, collision, or machinery certification.",
    }


def _write(plan_dir: Path, result: dict) -> None:
    (plan_dir / "line_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def _window_mask(phase: float, low: float, high: float, tolerance: float, offsets: list[float]) -> set[int]:
    """Grid indices whose offset keeps the composed phase inside the window."""
    return {
        index for index, offset in enumerate(offsets)
        if low - tolerance <= (phase + offset) % 360.0 <= high + tolerance
    }


def _lead_holds(relation: dict, lead: float) -> bool:
    if relation["type"] == "ordering":
        return relation["min_lead_deg"] <= lead <= relation["max_lead_deg"]
    offset = relation["offset_deg"] % 360.0
    tolerance = relation.get("tolerance_deg", 0.0)
    return _lead(offset, lead) <= tolerance or _lead(lead, offset) <= tolerance


def _hard_margin(line: dict, anchored: dict) -> float | None:
    """Minimum per-constraint slack over hard checks, or None if any fails.

    Window slack is the distance to the tolerance-extended window boundary;
    ordering slack is the distance to the nearer lead bound; fixed_offset
    slack is the remaining tolerance to the target offset.
    """
    margin = None
    for event in line["events"]:
        if event.get("mode", "hard") != "hard":
            continue
        low, high = event["window_deg"]
        tolerance = event.get("tolerance_deg") or 0.0
        for participant in event["participants"]:
            phase = anchored[participant["task"]][participant["target"]]
            if not low - tolerance <= phase <= high + tolerance:
                return None
            slack = min(phase - (low - tolerance), (high + tolerance) - phase)
            margin = slack if margin is None else min(margin, slack)
    for relation in line["relations"]:
        if relation.get("mode", "hard") != "hard":
            continue
        a = anchored[relation["from"]["task"]][relation["from"]["target"]]
        b = anchored[relation["to"]["task"]][relation["to"]["target"]]
        lead = _lead(a, b)
        if relation["type"] == "ordering":
            if not relation["min_lead_deg"] <= lead <= relation["max_lead_deg"]:
                return None
            slack = min(lead - relation["min_lead_deg"], relation["max_lead_deg"] - lead)
        else:
            offset = relation["offset_deg"] % 360.0
            tolerance = relation.get("tolerance_deg", 0.0)
            if not (_lead(offset, lead) <= tolerance or _lead(lead, offset) <= tolerance):
                return None
            slack = tolerance - min(_lead(offset, lead), _lead(lead, offset))
        margin = slack if margin is None else min(margin, slack)
    return margin


def solve_offsets(plan_dir: str | Path, step_deg: float = 1.0, top: int = 5) -> dict:
    """Joint master-phase offset search over existing results (S5).

    Grid-searches constant per-task offsets (at `step_deg` increments) that
    maximize the number of candidate combinations satisfying every hard event
    and relation. Recommendations are absolute offsets: they are composed
    from raw achieved phases and replace any declared `applied_offsets`.
    Writes `offsets_proposal.json`; never writes or changes a verdict.
    """
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
    if not participating:
        raise LineVerificationError("The line has no participating tasks; there is nothing to solve.")
    if len(participating) > 2:
        raise LineVerificationError(
            f"Offset solving supports up to two participating tasks; this line has {len(participating)}."
        )
    achieved = {
        task: _achieved_candidates(plan, plan_dir, task, run_target_ids(plan, task))
        for task in sorted(participating)
    }
    empty = [task for task, candidates in achieved.items() if not candidates]
    if empty:
        result = _proposal(plan, line, status="no_candidates", step_deg=float(step_deg),
                           combination_count=0, best=0, maximizers=[], achieved=achieved,
                           top=top,
                           note=f"Zero selected candidates for: {', '.join(empty)}; a completed search selecting nothing is recorded, not treated as an error.")
        _write_proposal(plan_dir, result)
        return result

    step = float(step_deg)
    if not 0.0 < step <= 360.0:
        raise LineVerificationError(f"Offset step must be in (0, 360] deg; got {step}.")
    steps = int(round(360.0 / step))
    if not 1 <= steps <= 3600:
        raise LineVerificationError(f"Offset step {step} does not divide into a usable grid (1..3600 steps).")
    offsets = [round(index * step, 6) % 360.0 for index in range(steps)]

    # Absolute semantics: compose from raw phases; recommendations replace
    # whatever the document declared.
    base_line = {key: value for key, value in line.items() if key != "applied_offsets"}
    hard_events = [event for event in base_line["events"] if event.get("mode", "hard") == "hard"]
    hard_relations = [relation for relation in base_line["relations"]
                       if relation.get("mode", "hard") == "hard"]
    task_ids = sorted(achieved)
    combination_count = 1
    for task in task_ids:
        combination_count *= len(achieved[task])

    def raw_anchored(chosen: dict[str, str]) -> dict[str, dict[str, float]]:
        return _anchored_map(achieved, base_line, chosen)

    if len(task_ids) == 1:
        counts = [0] * steps
    else:
        counts = [[0] * steps for _ in range(steps)]

    for combination in itertools.product(*(sorted(achieved[task]) for task in task_ids)):
        chosen = dict(zip(task_ids, combination))
        anchored = raw_anchored(chosen)
        # Per-task allowed offset indices from hard window events.
        allowed: dict[str, set[int] | None] = {task: None for task in task_ids}
        dead = False
        for event in hard_events:
            low, high = event["window_deg"]
            tolerance = event.get("tolerance_deg") or 0.0
            for participant in event["participants"]:
                task = participant["task"]
                mask = _window_mask(anchored[task][participant["target"]], low, high, tolerance, offsets)
                allowed[task] = mask if allowed[task] is None else allowed[task] & mask
                if not allowed[task]:
                    dead = True
        # Same-task relations are offset-invariant: constant per combination.
        cross = []
        for relation in hard_relations:
            if relation["from"]["task"] == relation["to"]["task"]:
                if _check_relation(relation, anchored)["status"] != "pass":
                    dead = True
            else:
                cross.append(relation)
        if dead:
            continue
        # Difference constraint sets for cross-task relations: which index gaps
        # (offset_to - offset_from, in steps) satisfy the relation.
        diff_sets = []
        for relation in cross:
            a = anchored[relation["from"]["task"]][relation["from"]["target"]]
            b = anchored[relation["to"]["task"]][relation["to"]["target"]]
            raw_lead = (b - a) % 360.0
            diff_sets.append((
                relation["from"]["task"],
                {gap for gap in range(-(steps - 1), steps)
                 if _lead_holds(relation, (raw_lead + gap * step) % 360.0)},
            ))
        first, second = (task_ids + [None])[:2]
        first_allowed = allowed[first] if allowed[first] is not None else range(steps)
        if second is None:
            for index in first_allowed:
                counts[index] += 1
            continue
        second_allowed = allowed[second] if allowed[second] is not None else range(steps)
        for i in first_allowed:
            row = counts[i]
            for j in second_allowed:
                ok = True
                for from_task, gaps in diff_sets:
                    gap = j - i if from_task == first else i - j
                    if gap not in gaps:
                        ok = False
                        break
                if ok:
                    row[j] += 1

    if len(task_ids) == 1:
        best = max(counts, default=0)
        maximizers = [(index,) for index, count in enumerate(counts) if count == best] if best else []
    else:
        best = max((max(row) for row in counts), default=0)
        maximizers = [(i, j) for i, row in enumerate(counts) for j, count in enumerate(row)
                      if count == best] if best else []

    # Rank maximizers: deepest constraint margin first, then offsets ascending.
    margins: dict[tuple[int, ...], float] = {}
    for pair in maximizers:
        deltas = {task: offsets[index] for task, index in zip(task_ids, pair)}
        margin = None
        for combination in itertools.product(*(sorted(achieved[task]) for task in task_ids)):
            chosen = dict(zip(task_ids, combination))
            anchored = raw_anchored(chosen)
            shifted = {
                task: {target: (phase + deltas[task]) % 360.0 for target, phase in phases.items()}
                for task, phases in anchored.items()
            }
            slack = _hard_margin(base_line, shifted)
            if slack is not None:
                margin = slack if margin is None else max(margin, slack)
        margins[pair] = margin if margin is not None else 0.0
    ranked = sorted(maximizers, key=lambda pair: (-(margins[pair] or 0.0), pair))

    result = _proposal(plan, line, status="solved" if best else "infeasible", step_deg=step,
                       combination_count=combination_count, best=best, maximizers=ranked,
                       achieved=achieved, top=top, margins=margins, note=None)
    _write_proposal(plan_dir, result)
    return result


def _proposal(plan: dict, line: dict, status: str, step_deg: float, combination_count: int,
              best: int, maximizers: list, achieved: dict, top: int,
              margins: dict | None = None, note: str | None = None) -> dict:
    task_ids = sorted(achieved)
    steps = int(round(360.0 / step_deg)) if 0.0 < step_deg <= 360.0 else 0
    offsets = [round(index * step_deg, 6) % 360.0 for index in range(steps)]
    recommendations = []
    for pair in maximizers[:max(int(top), 1)]:
        deltas = {task: offsets[index] for task, index in zip(task_ids, pair)}
        recommendations.append({
            "offsets": deltas,
            "passing_combinations": best,
            "margin_deg": round((margins or {}).get(pair) or 0.0, 6),
            "rank": len(recommendations) + 1,
        })
    example = None
    if recommendations:
        example = {task: {"phase": delta} for task, delta in recommendations[0]["offsets"].items()
                   if delta != 0.0}
    result = {
        "offset_proposal_version": 1,
        "task_set_id": plan["task_set_id"],
        "master_cycle_id": line["master_cycle_id"],
        "status": status,
        "step_deg": step_deg,
        "combination_count": combination_count,
        "best_passing_count": best,
        "assignments_with_best_count": len(maximizers),
        **({"applied_offsets_example": example if example is not None else {}} if recommendations else {}),
        **({"recommendations": recommendations} if recommendations else {}),
        "note": note or (
            "Joint offset proposal: per-task master-phase offsets chosen by grid search over the existing per-task results; "
            "recommendations are absolute and replace any declared synchronization.applied_offsets. "
            "This is a proposal only — a human declares the chosen offsets in the document, then re-validates, re-adapts, and re-verifies; "
            "this file never changes the verdict of the run."
        ),
        "disclaimer": "Post-hoc offset search over kinematic results; not synchronization synthesis, dynamics, collision, or machinery certification.",
    }
    if note and status == "no_candidates":
        result["note"] = (
            f"{note} "
            "This is a proposal only and never changes the verdict of the run."
        )
    return result


def _write_proposal(plan_dir: Path, result: dict) -> None:
    (plan_dir / "offsets_proposal.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
