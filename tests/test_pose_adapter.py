import copy
import csv
import json

import pytest

from mechanism_generator.omts import DocumentError, validate_document
from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan, write_plan


def add_pose(task, angles=(170, -170, 390), tolerances=(1, 5, 12)):
    for target, angle, tolerance in zip(task["motion"]["targets"], angles, tolerances):
        target["orientation"] = {"type": "planar_angle", "value": angle}
        if tolerance is not None:
            target.setdefault("tolerance", {})["orientation"] = tolerance


def three_arguments(run, flag):
    offset = run["arguments"].index(flag) + 1
    return [float(value) for value in run["arguments"][offset:offset + 3]]


def test_pose_preserves_angles_and_individual_tolerances(task_document):
    add_pose(task_document["tasks"][0])
    before = copy.deepcopy(task_document)
    run = prepare_plan(task_document)["runs"][0]
    assert three_arguments(run, "--target_orientations_deg") == [170, -170, 390]
    assert three_arguments(run, "--orientation_tolerances_deg") == [1, 5, 12]
    assert run["target_orientations_deg"] == [170, -170, 390]
    assert run["orientation_tolerances_deg"] == [1, 5, 12]
    assert task_document == before


def test_pose_defaults_only_omitted_angular_tolerances(task_document):
    add_pose(task_document["tasks"][0], tolerances=(None, 2, None))
    run = prepare_plan(task_document)["runs"][0]
    assert three_arguments(run, "--orientation_tolerances_deg") == [5, 2, 5]


def test_pose_order_reorders_positions_angles_tolerances_and_ids_together(task_document, tmp_path):
    task = task_document["tasks"][0]
    add_pose(task)
    task["motion"]["order_policy"] = "ordered"
    for target, index in zip(task["motion"]["targets"], (20, 30, 10)):
        target["occurrence"]["order_index"] = index
    output = tmp_path / "pose plan"
    plan_path = write_plan(task_document, output)
    run = json.loads(plan_path.read_text())["runs"][0]
    assert run["target_ids"] == ["T3", "T1", "T2"]
    assert run["positions"] == [[0.5, 3.5], [-6, 2], [-2, 6]]
    assert three_arguments(run, "--target_orientations_deg") == [390, 170, -170]
    assert three_arguments(run, "--orientation_tolerances_deg") == [12, 1, 5]
    with (output / run["targets_file"]).open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == ["label", "x1", "y1", "x2", "y2", "x3", "y3"]
    assert [float(value) for value in rows[1][1:]] == [0.5, 3.5, -6, 2, -2, 6]


def test_independent_pose_and_position_tasks_do_not_share_orientation_settings(task_document):
    first = task_document["tasks"][0]
    second = copy.deepcopy(first)
    second["id"] = "pose_second"
    position = copy.deepcopy(first)
    position["id"] = "position_only"
    add_pose(first, angles=(10, 20, 30), tolerances=(1, 2, 3))
    add_pose(second, angles=(-30, -20, -10), tolerances=(4, 5, 6))
    task_document["tasks"].extend([second, position])
    runs = prepare_plan(task_document)["runs"]
    assert three_arguments(runs[0], "--target_orientations_deg") == [10, 20, 30]
    assert three_arguments(runs[1], "--target_orientations_deg") == [-30, -20, -10]
    assert three_arguments(runs[0], "--orientation_tolerances_deg") == [1, 2, 3]
    assert three_arguments(runs[1], "--orientation_tolerances_deg") == [4, 5, 6]
    assert "--target_orientations_deg" not in runs[2]["arguments"]
    assert "--orientation_tolerances_deg" not in runs[2]["arguments"]
    assert "target_orientations_deg" not in runs[2]
    assert "orientation_tolerances_deg" not in runs[2]
    assert len({run["targets_file"] for run in runs}) == 3


@pytest.mark.parametrize("count", [1, 2])
def test_partial_pose_requests_are_rejected_before_writing(task_document, tmp_path, count):
    add_pose(task_document["tasks"][0])
    for target in task_document["tasks"][0]["motion"]["targets"][count:]:
        target.pop("orientation")
        target["tolerance"].pop("orientation")
    assert validate_document(task_document) == []
    with pytest.raises(UnsupportedFeature, match="all three targets"):
        write_plan(task_document, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_orphan_angular_tolerance_is_rejected(task_document):
    task_document["tasks"][0]["motion"]["targets"][0]["tolerance"]["orientation"] = 5
    with pytest.raises(UnsupportedFeature, match="requires a target orientation"):
        prepare_plan(task_document)


@pytest.mark.parametrize("tolerance", [0, -1, 180, 181, float("nan"), float("inf"), -float("inf")])
def test_invalid_angular_tolerances_are_rejected(task_document, tolerance):
    add_pose(task_document["tasks"][0], tolerances=(1, tolerance, 5))
    with pytest.raises(DocumentError):
        prepare_plan(task_document)


@pytest.mark.parametrize("angle", [float("nan"), float("inf"), -float("inf"), 10 ** 400])
def test_nonfinite_orientation_is_rejected(task_document, angle):
    add_pose(task_document["tasks"][0], angles=(0, angle, 90))
    with pytest.raises(DocumentError, match="finite"):
        prepare_plan(task_document)


def test_spatial_pose_stays_unsupported(task_document):
    task_document["coordinate_system"]["dimension"] = 3
    for target in task_document["tasks"][0]["motion"]["targets"]:
        target["position"].append(0)
        target["orientation"] = {"type": "quaternion_wxyz", "value": [1, 0, 0, 0]}
    assert validate_document(task_document) == []
    with pytest.raises(UnsupportedFeature, match="dimension"):
        prepare_plan(task_document)


def test_pose_capability_is_declared(task_document):
    task_document["capabilities_required"] = ["target_orientation"]
    add_pose(task_document["tasks"][0])
    assert prepare_plan(task_document)["runs"][0]["target_orientations_deg"] == [170, -170, 390]
