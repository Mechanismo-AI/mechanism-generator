"""G5: relations over derived region events gate the line verdict.

Fixture geometry (verified against the G3 tests): with PARAMS the gate's raw
occupancy windows are TOP [88, 92.5], WRAP [359, 4] and [57, 65.5], ORIGIN
[0, 359.5], and FAR never occupied. The gate is anchored at hold (raw phase
30, so composed phases shift by -30: release sits at 100, TOP at
[58, 62.5], ORIGIN at [330, 329.5]). The default catcher is unanchored
(composed = raw), so its TOP window is [88, 92.5] with enters 88 and exits
92.5; anchoring the catcher at grab with raw phase 30 composes it to
[58, 62.5] as well.
"""

import json

import pytest

from mechanism_generator.omts.adapter import DocumentError, prepare_plan
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
FAR = _region("far", (50, 50), 1.0)


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


def _verify(root, line, gate_rows=None, catcher_rows=None, **kwargs):
    _write_manifest(root, "gate", gate_rows if gate_rows is not None else [_row("g1", [30, 130, 250])])
    _write_manifest(root, "catcher", catcher_rows if catcher_rows is not None else [_row("c1", [120, 220, 20])])
    _write_plan(root, line)
    return verify_line(root, **kwargs)


def _occupies(task, region_id):
    return {"task": task, "region": region_id, "kind": "occupies_region"}


def _enters(task, region_id):
    return {"task": task, "region": region_id, "kind": "enters_region"}


def _exits(task, region_id):
    return {"task": task, "region": region_id, "kind": "exits_region"}


def _disjoint(clearance=None, mode="hard", region_id="top"):
    relation = {
        "id": "zone_keepout",
        "from": _occupies("gate", region_id),
        "to": _occupies("catcher", region_id),
        "type": "disjoint_windows",
        "mode": mode,
    }
    if clearance is not None:
        relation["clearance_deg"] = clearance
    return relation


def _contains(margin=None, mode="hard", from_region="origin", to_region="origin"):
    relation = {
        "id": "zone_contains",
        "from": _occupies("gate", from_region),
        "to": _occupies("catcher", to_region),
        "type": "contains",
        "mode": mode,
    }
    if margin is not None:
        relation["margin_deg"] = margin
    return relation


def _single(result):
    assert result["combination_count"] == 1
    return result["combinations"][0]["relations"][0]


# -- disjoint_windows gates ---------------------------------------------------


def test_disjoint_windows_gap_gates_verdict(tmp_path):
    # Gate TOP [58, 62.5] and catcher TOP [88, 92.5]: disjoint, gap 25.5 deg.
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=10)])
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    relation = _single(result)
    assert relation["type"] == "disjoint_windows"
    assert relation["status"] == "pass"
    assert relation["clearance_deg"] == 10.0
    assert relation["min_gap_deg"] == 25.5
    assert relation["from_window_count"] == 1
    assert relation["to_window_count"] == 1


def test_disjoint_windows_clearance_violation_fails(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=30)])
    result = _verify(tmp_path, line)
    assert result["status"] == "failed"
    relation = _single(result)
    assert relation["status"] == "fail"
    assert relation["min_gap_deg"] == 25.5


def test_disjoint_windows_overlapping_windows_fail(tmp_path):
    # Anchoring the catcher at grab (raw 30) composes its TOP window to
    # [58, 62.5] -- identical to the gate's, so even clearance 0 fails.
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=0)],
                 phase_reference={"gate": "hold", "catcher": "grab"})
    result = _verify(tmp_path, line, catcher_rows=[_row("c1", [30, 130, 250])])
    assert result["status"] == "failed"
    relation = _single(result)
    assert relation["status"] == "fail"
    assert relation["min_gap_deg"] == 0.0


def test_disjoint_windows_vacuous_when_never_occupied(tmp_path):
    # The catcher never occupies FAR: no window pair exists, so the
    # keep-out is vacuously satisfied (and reported as such).
    line = _line(regions=[TOP, FAR], collision={"gate": _model(), "catcher": _model()},
                 relations=[{
                     "id": "zone_keepout",
                     "from": _occupies("gate", "top"),
                     "to": _occupies("catcher", "far"),
                     "type": "disjoint_windows",
                     "clearance_deg": 10.0,
                     "mode": "hard",
                 }])
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    relation = _single(result)
    assert relation["status"] == "pass"
    assert relation["from_window_count"] == 1
    assert relation["to_window_count"] == 0
    assert relation["min_gap_deg"] is None


def test_disjoint_windows_is_per_candidate(tmp_path):
    # c1 anchored at grab overlaps the gate; c2 (grab at 200) sits at
    # [248, 252.5], disjoint with gap 165.5. Only the c2 combination passes.
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=0)],
                 phase_reference={"gate": "hold", "catcher": "grab"})
    result = _verify(tmp_path, line,
                     catcher_rows=[_row("c1", [30, 130, 250]), _row("c2", [200, 300, 100])])
    assert result["status"] == "verified"
    assert result["passing_combination_count"] == 1
    by_candidate = {combo["candidates"]["catcher"]: combo["relations"][0] for combo in result["combinations"]}
    assert by_candidate["c1"]["status"] == "fail"
    assert by_candidate["c2"]["status"] == "pass"
    assert by_candidate["c2"]["min_gap_deg"] == 165.5


def test_soft_disjoint_relation_does_not_gate(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=30, mode="soft")])
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    relation = _single(result)
    assert relation["status"] == "fail"
    assert result["combinations"][0]["soft_failures"] == ["zone_keepout"]


# -- contains gates ------------------------------------------------------------


def test_contains_identical_windows_pass_and_margin_fails(tmp_path):
    # Both ORIGIN windows compose to [330, 329.5]: contained with margin 0.
    # The default margin (undeclared) is 0.0.
    line = _line(regions=[ORIGIN], collision={"gate": _model(), "catcher": _model()},
                 relations=[_contains()],
                 phase_reference={"gate": "hold", "catcher": "grab"})
    result = _verify(tmp_path, line, catcher_rows=[_row("c1", [30, 130, 250])])
    assert result["status"] == "verified"
    relation = _single(result)
    assert relation["status"] == "pass"
    assert relation["margin_deg"] == 0.0
    line["relations"][0]["margin_deg"] = 5.0
    result = _verify(tmp_path / "margin", line, catcher_rows=[_row("c1", [30, 130, 250])])
    assert result["status"] == "failed"
    assert _single(result)["status"] == "fail"


def test_contains_fails_when_window_cannot_fit(tmp_path):
    # The catcher's ORIGIN window spans 359.5 deg; it cannot fit inside the
    # gate's 4.5 deg TOP window.
    line = _line(regions=[TOP, ORIGIN], collision={"gate": _model(), "catcher": _model()},
                 relations=[_contains(from_region="top", to_region="origin")],
                 phase_reference={"gate": "hold", "catcher": "grab"})
    result = _verify(tmp_path, line, catcher_rows=[_row("c1", [30, 130, 250])])
    assert result["status"] == "failed"
    assert _single(result)["status"] == "fail"


def test_contains_vacuous_when_to_is_empty_but_not_vice_versa(tmp_path):
    regions = [TOP, FAR]
    collision = {"gate": _model(), "catcher": _model()}
    # An empty `to` side is vacuously contained.
    line = _line(regions=regions, collision=collision,
                 relations=[_contains(from_region="top", to_region="far")])
    assert _verify(tmp_path, line)["status"] == "verified"
    # An empty `from` side cannot contain a nonempty `to` side.
    line = _line(regions=regions, collision=collision,
                 relations=[_contains(from_region="far", to_region="top")])
    result = _verify(tmp_path / "reverse", line)
    assert result["status"] == "failed"
    relation = _single(result)
    assert relation["status"] == "fail"
    assert relation["from_window_count"] == 0
    assert relation["to_window_count"] == 1


# -- ordering and fixed_offset over derived points -----------------------------


def test_ordering_over_derived_enter_point(tmp_path):
    # Composed release 100, catcher enters TOP at 88: lead 348.
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()}, relations=[{
        "id": "enter_after_release", "from": {"task": "gate", "target": "release"},
        "to": _enters("catcher", "top"), "type": "ordering",
        "min_lead_deg": 340, "max_lead_deg": 355, "mode": "hard",
    }])
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    relation = _single(result)
    assert relation["status"] == "pass"
    assert relation["achieved_leads_deg"] == [348.0]
    assert relation["achieved_lead_deg"] == 348.0
    line["relations"][0]["min_lead_deg"] = 10
    line["relations"][0]["max_lead_deg"] = 45
    result = _verify(tmp_path / "narrow", line)
    assert result["status"] == "failed"
    assert _single(result)["status"] == "fail"


def test_ordering_checks_all_occurrence_pairs(tmp_path):
    # The catcher enters WRAP at 359 and 57: leads 259 and 317 from
    # release (100). Both pairs must sit inside the band.
    line = _line(regions=[WRAP], collision={"gate": _model(), "catcher": _model()}, relations=[{
        "id": "wrap_enter_after_release", "from": {"task": "gate", "target": "release"},
        "to": _enters("catcher", "wrap"), "type": "ordering",
        "min_lead_deg": 250, "max_lead_deg": 320, "mode": "hard",
    }])
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    relation = _single(result)
    assert relation["status"] == "pass"
    assert relation["achieved_leads_deg"] == [259.0, 317.0]
    line["relations"][0]["min_lead_deg"] = 300
    result = _verify(tmp_path / "narrow", line)
    assert result["status"] == "failed"
    assert _single(result)["status"] == "fail"


def test_fixed_offset_over_derived_exit_point(tmp_path):
    # Composed release 100, catcher exits TOP at 92.5: lead 352.5.
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()}, relations=[{
        "id": "exit_offset", "from": {"task": "gate", "target": "release"},
        "to": _exits("catcher", "top"), "type": "fixed_offset",
        "offset_deg": 352.5, "tolerance_deg": 0.0, "mode": "hard",
    }])
    assert _verify(tmp_path, line)["status"] == "verified"
    line["relations"][0]["offset_deg"] = 0.0
    # Lead 352.5 is circularly 7.5 deg from offset 0: tolerance 10 passes,
    # tolerance 5 fails.
    line["relations"][0]["tolerance_deg"] = 10.0
    assert _verify(tmp_path / "loose", line)["status"] == "verified"
    line["relations"][0]["tolerance_deg"] = 5.0
    result = _verify(tmp_path / "wrong", line)
    assert result["status"] == "failed"
    assert _single(result)["status"] == "fail"


def test_ordering_over_never_occurring_event_is_an_error(tmp_path):
    line = _line(regions=[TOP, FAR], collision={"gate": _model(), "catcher": _model()}, relations=[{
        "id": "far_enter", "from": {"task": "gate", "target": "release"},
        "to": _enters("catcher", "far"), "type": "ordering",
        "min_lead_deg": 0, "max_lead_deg": 360, "mode": "hard",
    }])
    with pytest.raises(LineVerificationError, match="never occurs"):
        _verify(tmp_path, line)


# -- probe and solver interactions ---------------------------------------------


def test_probe_rotates_region_windows(tmp_path):
    # Clearance 40 cannot be met at the declared composition (gap 25.5), so
    # the baseline fails; rotating the catcher by +100 deg opens a gap of
    # 125.5. On the 1 deg grid the catcher's feasible interval is [15, 285].
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=40)])
    result = _verify(tmp_path, line, probe=True, probe_step_deg=1.0)
    assert result["status"] == "failed"
    probe_tasks = {entry["task"]: entry for entry in result["anchor_probe"]["tasks"]}
    catcher = probe_tasks["catcher"]
    assert catcher["feasible_intervals_deg"] == [
        {"from_deg": 15.0, "to_deg": 285.0, "max_passing_combinations": 1}]
    assert catcher["best_passing_combinations"] == 1


def test_solve_offsets_rejects_derived_relations(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=10)])
    _write_manifest(tmp_path, "gate", [_row("g1", [30, 130, 250])])
    _write_manifest(tmp_path, "catcher", [_row("c1", [120, 220, 20])])
    _write_plan(tmp_path, line)
    with pytest.raises(LineVerificationError, match="does not compose"):
        solve_offsets(tmp_path)


def test_ordering_feasibility_excludes_derived_relations(tmp_path):
    # The spread precheck's rigid-slide argument does not apply to
    # all-pairs derived leads, so such relations are excluded from it.
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()}, relations=[{
        "id": "enter_after_release", "from": {"task": "gate", "target": "release"},
        "to": _enters("catcher", "top"), "type": "ordering",
        "min_lead_deg": 340, "max_lead_deg": 355, "mode": "hard",
    }])
    assert "ordering_feasibility" not in _verify(tmp_path, line)


def test_ordering_feasibility_still_covers_target_relations(tmp_path):
    # A target-target ordering alongside a derived relation is still
    # prechecked (release 100 -> grab 120: lead 20 inside [10, 45]).
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()}, relations=[
        {"id": "grab_after_release", "from": {"task": "gate", "target": "release"},
         "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
         "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard"},
        _disjoint(clearance=10),
    ])
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    assert [entry["id"] for entry in result["ordering_feasibility"]["relations"]] == ["grab_after_release"]


# -- verifier fail-closed boundaries (hand-edited plans) -----------------------


def test_verifier_rejects_ordering_over_occupancy_window(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()}, relations=[{
        "id": "bad", "from": _occupies("gate", "top"),
        "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
        "min_lead_deg": 0, "max_lead_deg": 360, "mode": "hard",
    }])
    with pytest.raises(LineVerificationError, match="occupancy window"):
        _verify(tmp_path, line)


def test_verifier_rejects_contains_over_point_reference(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_contains(from_region="top", to_region="top")])
    line["relations"][0]["from"] = {"task": "gate", "target": "release"}
    with pytest.raises(LineVerificationError, match="point reference"):
        _verify(tmp_path, line)


def test_verifier_requires_collision_model_for_derived_relations(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model()},
                 relations=[_disjoint(clearance=10)])
    with pytest.raises(LineVerificationError, match="no collision body model"):
        _verify(tmp_path, line)


def test_verifier_rejects_unknown_region_in_derived_relation(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 relations=[_disjoint(clearance=10, region_id="ghost")])
    with pytest.raises(LineVerificationError, match="unknown region 'ghost'"):
        _verify(tmp_path, line)


def test_verifier_rejects_derived_event_participants(tmp_path):
    line = _line(regions=[TOP], collision={"gate": _model(), "catcher": _model()},
                 events=[{
                     "id": "derived_participant",
                     "participants": [_enters("gate", "top"), {"task": "catcher", "target": "grab"}],
                     "window_deg": [0, 360],
                     "tolerance_deg": None,
                     "mode": "hard",
                 }])
    with pytest.raises(LineVerificationError, match="cannot be event participants"):
        _verify(tmp_path, line)


# -- adapter: derived relations are recorded, incoherent ones rejected ---------


def _document(relations=None, events=None, catcher_collision=True):
    def _task(task_id, collision, reference=None):
        task = {
            "id": task_id,
            "motion": {
                "mode": "cyclic",
                "order_policy": "unordered",
                "targets": [
                    {"id": target_id, "position": [0.5 + 0.3 * index, 0.5]}
                    for index, target_id in enumerate(TARGETS[task_id])
                ],
            },
            "mechanism_search": {
                "allowed_topologies": ["four_bar"],
                "max_dof": 1,
                "max_actuators": 1,
            },
        }
        if reference is not None:
            task["motion"]["cycle"] = {"phase_reference": reference}
        if collision is not None:
            task["requirements"] = {"collision": collision}
        return task

    document = {
        "spec": "open-mechanism-task",
        "version": "0.2.0",
        "task_set_id": "collision-g5",
        "units": {"length": "normalized", "angle": "deg", "time": "s"},
        "coordinate_system": {"frame_id": "world", "dimension": 2, "handedness": "right"},
        "regions": [{"id": "shared_zone", "shape": "box", "min": [0, 0], "max": [1, 1]}],
        "tasks": [
            _task("gate", {"bodies": {"links": {"thickness": 0.5}}}, reference="hold"),
            _task("catcher", {"bodies": {"links": {"thickness": 0.2}}} if catcher_collision else None),
        ],
        "synchronization": {
            "participants": [{"task": "gate"}, {"task": "catcher"}],
        },
    }
    if relations is not None:
        document["synchronization"]["relations"] = relations
    if events is not None:
        document["synchronization"]["events"] = events
    return document


def test_adapter_rejects_ordering_over_occupancy_window():
    document = _document(relations=[{
        "id": "bad_ordering",
        "from": "gate.occupies_region.shared_zone",
        "to": "catcher.grab.reached",
        "type": "ordering",
        "min_lead": {"phase": 10},
        "max_lead": {"phase": 300},
    }])
    with pytest.raises(DocumentError, match="occupancy window"):
        prepare_plan(document)


def test_adapter_rejects_contains_over_point_references():
    document = _document(relations=[{
        "id": "bad_contains",
        "from": "gate.release.reached",
        "to": "catcher.grab.reached",
        "type": "contains",
    }])
    with pytest.raises(DocumentError, match="requires a window event"):
        prepare_plan(document)


def test_derived_reference_requires_collision_body_model():
    document = _document(relations=[{
        "id": "catcher_entry",
        "from": "gate.release.reached",
        "to": "catcher.enters_region.shared_zone",
        "type": "ordering",
        "min_lead": {"phase": 10},
        "max_lead": {"phase": 300},
    }], catcher_collision=False)
    with pytest.raises(DocumentError, match="no collision body model"):
        prepare_plan(document)


def test_derived_reference_requires_declared_region():
    document = _document(relations=[{
        "id": "ghost_entry",
        "from": "gate.release.reached",
        "to": "catcher.enters_region.ghost",
        "type": "ordering",
        "min_lead": {"phase": 10},
        "max_lead": {"phase": 300},
    }])
    with pytest.raises(DocumentError, match="unknown region 'ghost'"):
        prepare_plan(document)


def test_adapter_rejects_derived_event_participants():
    document = _document(events=[{
        "id": "zone_touch",
        "type": "co_active",
        "participants": ["gate.enters_region.shared_zone", "catcher.grab.reached"],
        "window": {"phase_range": [0, 360]},
    }])
    with pytest.raises(DocumentError, match="cannot be event participants"):
        prepare_plan(document)
