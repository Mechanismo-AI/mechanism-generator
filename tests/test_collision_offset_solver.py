"""The joint offset search composes relations over derived region events.

Fixture geometry (shared with test_collision_gating.py): with PARAMS the
gate's raw occupancy windows are TOP [88, 92.5], WRAP [359, 4] + [57, 65.5],
ORIGIN [0, 359.5]. The gate is anchored at hold (raw phase 30), so its
composed windows shift by -30: TOP [58, 62.5], ORIGIN [330, 359.5], WRAP
[329, 334] + [27, 35.5]. The default catcher is unanchored (composed =
raw), so its TOP window is [88, 92.5] with enters 88 and exits 92.5, and
grab sits at composed 120.

The zero-offset keepout gap between the two TOP windows is 25.5 deg. These
tests cover the solver side: sampled-occupancy composition, gap sweep for
cross-task derived relations, same-task invariance, margin ranking over
region slack, absolute recommendations, and the fail-closed preflights.
Occupancy is sampled, never certified; a passing assignment on a line with
derived relations is a sampled-occupancy verdict.
"""

import json

import pytest

from mechanism_generator.omts.line_verify import LineVerificationError, solve_offsets, verify_line


TASK_IDS = ["gate", "catcher"]
TARGETS = {"gate": ["hold", "release", "rest"], "catcher": ["grab", "carry", "park"]}
GEOMETRY_KEYS = ("l1", "l2", "l3", "l4", "S_ratio", "bar_length", "base_x", "base_y", "base_angle")
PARAMS = [4, 1.2, 4.5, 3, 0.5, 1.0, 0, 0, 0]


def _region(region_id, center, radius):
    return {"id": region_id, "shape": "circle", "center": list(center), "radius": radius}


TOP = _region("top", (0, 1.2), 0.05)
WRAP = _region("wrap", (1.1998172, 0.0209429), 0.05)
ORIGIN = _region("origin", (0, 0), 0.5)


def _model(thickness=0.0, steps=720, mode="hard"):
    return {"thickness": thickness, "steps": steps, "mode": mode}


def _row(row_id, phases, params=PARAMS, branch_sign=1):
    row = {"candidate_id": row_id, "branch_sign": branch_sign}
    row.update({f"phase_{index + 1}_deg": phase for index, phase in enumerate(phases)})
    row.update(dict(zip(GEOMETRY_KEYS, params)))
    return row


def _write_manifest(root, task, rows, crank="positive", status="completed"):
    run_dir = root / f"results/task-{TASK_IDS.index(task) + 1:03d}" / "r25c" / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_status": status,
        "targets": [{
            "label": task,
            "crank_direction": crank,
            "selected": [dict(row, rank=rank) for rank, row in enumerate(rows, start=1)],
        }],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_plan(root, line):
    plan = {
        "task_set_id": "pair",
        "runs": [
            {"task_id": task, "target_ids": TARGETS[task],
             "output_root": f"results/task-{TASK_IDS.index(task) + 1:03d}"}
            for task in TASK_IDS
        ],
        "line": line,
    }
    (root / "run_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    return root


def _line(regions=None, collision=None, relations=None, events=None,
          applied_offsets=None, phase_reference=None):
    line = {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": phase_reference or {"gate": "hold", "catcher": None},
        "events": events or [],
        "relations": relations or [],
        "verification": "pending_timeline_verification",
    }
    if regions is not None:
        line["regions"] = regions
    if collision is not None:
        line["collision"] = collision
    if applied_offsets is not None:
        line["applied_offsets"] = applied_offsets
    return line


def _occupies(task, region_id):
    return {"task": task, "region": region_id, "kind": "occupies_region"}


def _enters(task, region_id):
    return {"task": task, "region": region_id, "kind": "enters_region"}


def _disjoint(clearance=None, mode="hard", relation_id="zone_keepout"):
    relation = {
        "id": relation_id,
        "from": _occupies("gate", "top"),
        "to": _occupies("catcher", "top"),
        "type": "disjoint_windows",
        "mode": mode,
    }
    if clearance is not None:
        relation["clearance_deg"] = clearance
    return relation


def _pair(root, line, gate_rows=None, catcher_rows=None):
    _write_manifest(root, "gate", gate_rows if gate_rows is not None else [_row("g1", [30, 130, 250])])
    _write_manifest(root, "catcher", catcher_rows if catcher_rows is not None else [_row("c1", [120, 220, 20])])
    return _write_plan(root, line)


def _keepout_line(clearance, **kwargs):
    return _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=clearance)], **kwargs)


def test_keepout_repair_is_solved_and_verifies_end_to_end(tmp_path):
    # The keepout (clearance 30) fails at the zero-offset composition: the
    # TOP windows clear by only 25.5 deg. The solver re-times around it; the
    # widest attainable min-gap is (360 - 4.5 - 4.5) / 2 = 175.5 deg, so the
    # deepest margin is 175.5 - 30 = 145.5 deg (grid step 1: allow +/- 1.5).
    plan_dir = _pair(tmp_path, _keepout_line(30))
    proposal = solve_offsets(plan_dir, step_deg=1.0, top=3)
    assert proposal["status"] == "solved"
    assert proposal["best_passing_count"] == 1
    top = proposal["recommendations"][0]
    assert not (top["offsets"]["gate"] == 0.0 and top["offsets"]["catcher"] == 0.0)
    assert top["margin_deg"] == pytest.approx(145.5, abs=1.5)
    line = _keepout_line(30, applied_offsets=top["offsets"])
    _write_plan(plan_dir, line)
    result = verify_line(plan_dir)
    assert result["status"] == "verified"
    keepout = next(item for item in result["combinations"][0]["relations"]
                   if item["id"] == "zone_keepout")
    assert keepout["status"] == "pass"
    assert keepout["min_gap_deg"] == pytest.approx(175.5, abs=1.5)


def test_joint_only_solution_with_derived_relation(tmp_path):
    # The window event (release 100, grab 120 -> window [30, 70] +/- 5) has
    # joint-only solutions: no single-task offset can fix it, and the derived
    # keepout (clearance 10) must also hold. Single-task probes are empty;
    # the joint search composes the keepout over the sampled windows and
    # finds assignments where both tasks move together.
    events = [{
        "id": "handoff_window",
        "participants": [{"task": "gate", "target": "release"}, {"task": "catcher", "target": "grab"}],
        "window_deg": [30, 70], "tolerance_deg": 5, "mode": "hard",
    }]
    relations = [
        {"id": "release_before_grab",
         "from": {"task": "gate", "target": "release"},
         "to": {"task": "catcher", "target": "grab"},
         "type": "ordering", "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard"},
        _disjoint(clearance=10),
    ]
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=relations, events=events)
    plan_dir = _pair(tmp_path, line)
    probe = verify_line(plan_dir, probe=True, probe_step_deg=5.0)
    assert probe["status"] == "failed"
    by_task = {entry["task"]: entry for entry in probe["anchor_probe"]["tasks"]}
    assert by_task["gate"]["feasible_intervals_deg"] == []
    assert by_task["catcher"]["feasible_intervals_deg"] == []
    proposal = solve_offsets(plan_dir, step_deg=1.0, top=5)
    assert proposal["status"] == "solved"
    offsets = proposal["recommendations"][0]["offsets"]
    assert offsets["gate"] != 0.0 and offsets["catcher"] != 0.0
    line["applied_offsets"] = offsets
    _write_plan(plan_dir, line)
    assert verify_line(plan_dir)["status"] == "verified"


def test_margin_ranking_includes_region_slack(tmp_path):
    plan_dir = _pair(tmp_path, _keepout_line(30))
    proposal = solve_offsets(plan_dir, step_deg=1.0, top=10)
    assert proposal["status"] == "solved"
    margins = [entry["margin_deg"] for entry in proposal["recommendations"]]
    assert margins == sorted(margins, reverse=True)
    assert margins[0] == pytest.approx(145.5, abs=1.5)
    assert all(entry["passing_combinations"] == proposal["best_passing_count"]
               for entry in proposal["recommendations"])


def test_same_task_derived_relation_is_offset_invariant(tmp_path):
    # The gate's ORIGIN [330, 359.5] and WRAP [329, 334] + [27, 35.5]
    # windows overlap around 330; a per-task offset rotates both sides of a
    # same-task relation together, so no assignment can separate them.
    relation = {
        "id": "origin_wrap_keepout",
        "from": _occupies("gate", "origin"),
        "to": _occupies("gate", "wrap"),
        "type": "disjoint_windows", "mode": "hard",
    }
    line = _line(regions=[ORIGIN, WRAP], collision={"gate": _model(), "catcher": _model()},
                 relations=[relation])
    plan_dir = _pair(tmp_path, line)
    assert verify_line(plan_dir)["status"] == "failed"
    proposal = solve_offsets(plan_dir, step_deg=1.0)
    assert proposal["status"] == "infeasible"
    assert "recommendations" not in proposal


def test_solver_fail_closed_preflights(tmp_path):
    cases = [
        # derived relation, but the plan declares no regions
        (_line(collision={"gate": _model(), "catcher": _model()}, relations=[_disjoint()]),
         "require declared regions"),
        # ordering over an occupancy window (kind/type mismatch)
        (_line(regions=[TOP], collision={"gate": _model(), "catcher": _model()}, relations=[{
            "id": "bad_ordering", "from": _occupies("gate", "top"),
            "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
            "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard"}]),
         "is an occupancy window"),
        # derived region event as an event participant
        (_line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
               events=[{"id": "bad_event", "participants": [_occupies("gate", "top")],
                        "window_deg": [0, 10], "tolerance_deg": 0, "mode": "hard"}]),
         "cannot be event participants"),
        # derived relation whose task declares no collision body model
        (_line(regions=[TOP], collision={"catcher": _model()}, relations=[_disjoint()]),
         "declares no collision body model"),
    ]
    for index, (line, pattern) in enumerate(cases):
        plan_dir = _pair(tmp_path / f"case{index}", line)
        with pytest.raises(LineVerificationError, match=pattern):
            solve_offsets(plan_dir)


def test_absolute_semantics_with_derived_relations(tmp_path):
    # Recommendations compose from raw phases, so a declared catcher offset
    # must not shift the search: the proposals are identical with and
    # without the declaration, and both notes say the recommendations
    # replace declared offsets.
    def propose(root, declared):
        line = _keepout_line(30, applied_offsets={"catcher": 50.0} if declared else None)
        plan_dir = _pair(root, line)
        return solve_offsets(plan_dir, step_deg=1.0, top=3)

    plain = propose(tmp_path / "plain", declared=False)
    declared = propose(tmp_path / "declared", declared=True)
    assert plain["status"] == declared["status"] == "solved"
    assert declared["recommendations"] == plain["recommendations"]
    assert "replace" in declared["note"]
    assert "sampled-occupancy" in declared["note"]
    example = declared["applied_offsets_example"]
    assert set(example) == {task for task, deg in declared["recommendations"][0]["offsets"].items()
                            if deg != 0.0}
    assert all(set(quantity) == {"phase"} for quantity in example.values())


def test_solver_never_writes_a_verdict(tmp_path):
    plan_dir = _pair(tmp_path, _keepout_line(30))
    solve_offsets(plan_dir, step_deg=1.0)
    assert (plan_dir / "offsets_proposal.json").exists()
    assert not (plan_dir / "line_result.json").exists()


def test_no_candidates_with_collision_models_is_recorded(tmp_path):
    line = _keepout_line(10)
    plan_dir = _pair(tmp_path, line, gate_rows=[])
    proposal = solve_offsets(plan_dir)
    assert proposal["status"] == "no_candidates"
    assert "not treated as an error" in proposal["note"]
    assert "occupancy windows were sampled" in proposal["note"]
    assert "recommendations" not in proposal
    assert (plan_dir / "offsets_proposal.json").exists()


def test_mixed_cross_task_ordering_is_solved(tmp_path):
    # Ordering from the gate's release target (composed 100) to the
    # catcher's derived enters-top point (composed 88): the raw lead is 348,
    # outside [10, 45], so the line fails at zero offsets and only a joint
    # (here: catcher) re-time repairs it.
    relation = {
        "id": "enter_after_release",
        "from": {"task": "gate", "target": "release"},
        "to": _enters("catcher", "top"),
        "type": "ordering", "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard",
    }
    line = _line(regions=[TOP], collision={"catcher": _model()}, relations=[relation])
    plan_dir = _pair(tmp_path, line)
    assert verify_line(plan_dir)["status"] == "failed"
    proposal = solve_offsets(plan_dir, step_deg=1.0, top=5)
    assert proposal["status"] == "solved"
    offsets = proposal["recommendations"][0]["offsets"]
    relative = (offsets["catcher"] - offsets["gate"] + 180.0) % 360.0 - 180.0
    assert 22.0 - 1.5 <= relative <= 57.0 + 1.5
    line["applied_offsets"] = offsets
    _write_plan(plan_dir, line)
    assert verify_line(plan_dir)["status"] == "verified"
