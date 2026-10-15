"""The G5 capstone example: the synchronized pair sharing one keep-out zone.

The example (examples/omts/collision_pair.omts.yaml) is the synchronized
pair plus a circular shared_zone at the handoff, a collision body model per
task (thickness 0.1, 720 samples), and a hard disjoint_windows relation
over the two tasks' derived occupies_region windows (clearance 10 deg).

Fixture geometry (worked values, computed with the G1 kernel): with links
l1..l4 = [4, 1.2, 4.5, 3], S_ratio 0.5, bar 1.0, branch open, and the
example's thickness, the raw shared_zone occupancy windows are:

- gate g1 (base [4.0, -0.25]): [96.0, 137.0]; anchored at hold (raw hold
  phase 30), the composed window is [66.0, 107.0], and release sits at
  composed 100, inside the window;
- catcher c1 (base [4.5, 0.0]): [119.0, 151.0]; the catcher is unanchored,
  so composed = raw, and grab sits at composed 120, inside the window;
- catcher c2 (base [3.0, -0.5]): [66.0, 98.0], overlapping the gate's
  composed window: the keep-out must fail this combination.

The g1 x c1 windows clear each other by 12.0 deg (>= clearance 10), and the
authored handoff and ordering constraints pass (release 100, grab 120,
lead 20 in [10, 45]), so that combination verifies. g1 x c2 shares the
authored timing but overlaps the zone, so it must fail on the keep-out
alone. Occupancy is sampled, never certified; these tests exercise the
verifier pipeline over the real example document with synthetic engine
manifests, not the engine itself.
"""

import json

import pytest

from mechanism_generator.omts.adapter import prepare_plan, write_plan
from mechanism_generator.omts.line_verify import LineVerificationError, solve_offsets, verify_line
from mechanism_generator.omts.validation import load_document, require_valid

from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "omts" / "collision_pair.omts.yaml"
TASKS = ["gate", "catcher"]


def _row(candidate_id, phases, base):
    row = {
        "candidate_id": candidate_id,
        "branch_sign": 1,
        "l1": 4, "l2": 1.2, "l3": 4.5, "l4": 3, "S_ratio": 0.5, "bar_length": 1.0,
        "base_x": base[0], "base_y": base[1], "base_angle": 0.0,
    }
    row.update({f"phase_{index + 1}_deg": phase for index, phase in enumerate(phases)})
    return row


GATE_ROW = ("g1", [30, 130, 250], (4.0, -0.25))
CATCHER_ROWS = [
    ("c1", [120, 220, 20], (4.5, 0.0)),
    ("c2", [120, 220, 20], (3.0, -0.5)),
]


def _write_manifest(plan_dir, task, rows):
    run_dir = plan_dir / f"results/task-{TASKS.index(task) + 1:03d}" / "r25c" / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_status": "completed",
        "targets": [{
            "label": task,
            "crank_direction": "positive",
            "selected": [dict(_row(*row), rank=rank) for rank, row in enumerate(rows, start=1)],
        }],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _plan_with_results(tmp_path, catcher_rows):
    plan_dir = tmp_path / "plan"
    write_plan(load_document(EXAMPLE), plan_dir)
    _write_manifest(plan_dir, "gate", [GATE_ROW])
    _write_manifest(plan_dir, "catcher", catcher_rows)
    return plan_dir


def test_example_records_the_gating_line(tmp_path):
    document = load_document(EXAMPLE)
    require_valid(document)
    plan = prepare_plan(document)
    line = plan["line"]
    assert [region["id"] for region in line["regions"]] == ["shared_zone"]
    assert line["collision"]["gate"] == {"thickness": 0.1, "steps": 720, "mode": "hard"}
    keepout = [relation for relation in line["relations"]
               if relation["id"] == "zone_keepout"]
    assert keepout == [{
        "id": "zone_keepout",
        "from": {"task": "gate", "region": "shared_zone", "kind": "occupies_region"},
        "to": {"task": "catcher", "region": "shared_zone", "kind": "occupies_region"},
        "type": "disjoint_windows",
        "mode": "hard",
        "clearance_deg": 10,
    }]
    assert line["verification"] == "pending_timeline_verification"
    assert any("From G5, relations over derived region events gate the line verdict"
               in note for note in plan["notes"])


def test_disjoint_occupancy_windows_verify_the_line(tmp_path):
    plan_dir = _plan_with_results(tmp_path, CATCHER_ROWS[:1])
    result = verify_line(plan_dir)

    assert result["status"] == "verified"
    assert result["combination_count"] == 1
    assert result["passing_combination_count"] == 1
    combination = result["combinations"][0]
    assert combination["candidates"] == {"gate": "g1", "catcher": "c1"}

    keepout = next(item for item in combination["relations"]
                   if item["id"] == "zone_keepout")
    assert keepout["status"] == "pass"
    assert keepout["min_gap_deg"] == 12.0
    assert keepout["clearance_deg"] == 10.0
    ordering = next(item for item in combination["relations"]
                    if item["id"] == "release_before_grab")
    assert ordering["status"] == "pass"
    assert ordering["achieved_lead_deg"] == 20.0

    collision = result["collision"]
    assert collision["method"] == "sampled_collision_geometry_v1"
    assert collision["regions"] == ["shared_zone"]
    by_candidate = {
        (task, candidate["id"]): data["shared_zone"]
        for task, entry in collision["tasks"].items()
        for candidate in entry["candidates"]
        for data in [candidate["regions"]]
    }
    # raw windows in each task's own crank angle; composed windows apply
    # the anchoring rule (the gate is anchored at hold, raw phase 30)
    assert by_candidate[("gate", "g1")]["windows"] == [{"start_deg": 96.0, "end_deg": 137.0}]
    assert by_candidate[("gate", "g1")]["composed_windows"] == [{"start_deg": 66.0, "end_deg": 107.0}]
    assert by_candidate[("catcher", "c1")]["windows"] == [{"start_deg": 119.0, "end_deg": 151.0}]
    assert by_candidate[("catcher", "c1")]["composed_windows"] == [{"start_deg": 119.0, "end_deg": 151.0}]
    assert by_candidate[("catcher", "c1")]["composed_enters_deg"] == [119.0]
    assert by_candidate[("catcher", "c1")]["composed_exits_deg"] == [151.0]
    assert "not certified" in collision["disclaimer"]
    assert (plan_dir / "line_result.json").exists()


def test_overlapping_occupancy_fails_the_combination_not_the_line(tmp_path):
    plan_dir = _plan_with_results(tmp_path, CATCHER_ROWS)
    result = verify_line(plan_dir)

    # one combination still satisfies every hard constraint, so the line
    # is verified with 1 of 2 combinations passing; the overlapping catcher
    # fails on the keep-out alone, with its overlap recorded as data
    assert result["status"] == "verified"
    assert result["combination_count"] == 2
    assert result["passing_combination_count"] == 1
    by_candidates = {tuple(sorted(combo["candidates"].items())): combo
                     for combo in result["combinations"]}
    overlap = by_candidates[(("catcher", "c2"), ("gate", "g1"))]
    assert overlap["status"] == "fail"
    keepout = next(item for item in overlap["relations"]
                   if item["id"] == "zone_keepout")
    assert keepout["status"] == "fail"
    assert keepout["min_gap_deg"] == 0.0
    # the authored timing still passes for the overlapping combination:
    # the keep-out is the only reason it fails
    ordering = next(item for item in overlap["relations"]
                    if item["id"] == "release_before_grab")
    assert ordering["status"] == "pass"
    assert all(item["status"] == "pass" for item in overlap["events"])


def test_overlapping_occupancy_alone_fails_the_line(tmp_path):
    plan_dir = _plan_with_results(tmp_path, CATCHER_ROWS[1:])
    result = verify_line(plan_dir)

    # with only the overlapping catcher selected, no combination passes
    assert result["status"] == "failed"
    assert result["passing_combination_count"] == 0
    keepout = next(item for item in result["combinations"][0]["relations"]
                   if item["id"] == "zone_keepout")
    assert keepout["min_gap_deg"] == 0.0


def test_joint_offset_search_refuses_the_derived_line(tmp_path):
    plan_dir = _plan_with_results(tmp_path, CATCHER_ROWS[:1])
    # fail-closed: offsets for lines with derived relations are declared
    # by hand and re-verified; the joint search does not compose them
    with pytest.raises(LineVerificationError, match="does not compose"):
        solve_offsets(plan_dir)
