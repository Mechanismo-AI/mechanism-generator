import csv
import json
from pathlib import Path

from mechanism_generator.omts import load_document, validate_document
from mechanism_generator.omts.adapter import prepare_plan, write_plan

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "omts" / "gap_transfer.omts.yaml"


def option(run, flag):
    return run["arguments"][run["arguments"].index(flag) + 1]


def three_arguments(run, flag):
    offset = run["arguments"].index(flag) + 1
    return [float(value) for value in run["arguments"][offset:offset + 3]]


def test_document_validates():
    assert validate_document(load_document(EXAMPLE)) == []


def test_physical_brief_is_pinned():
    targets = load_document(EXAMPLE)["tasks"][0]["motion"]["targets"]
    # 1 normalized unit = 100 mm: the poses are physical (-130, 50), (0, 50)
    # and (+130, 50) mm, 130 mm apart along the carry line, all level.
    assert [target["position"] for target in targets] == [[-1.3, 0.5], [0.0, 0.5], [1.3, 0.5]]
    assert [target["orientation"]["value"] for target in targets] == [0.0, 0.0, 0.0]


def test_packaging_tolerances_reach_the_engine():
    run = prepare_plan(load_document(EXAMPLE))["runs"][0]
    assert run["target_ids"] == ["T1", "T2", "T3"]
    assert option(run, "--phase_mode") == "ordered"
    # 1.5 mm at 100 mm per normalized unit.
    assert float(option(run, "--max_point_error")) == 0.015
    assert float(option(run, "--max_mean_error")) == 0.01
    assert three_arguments(run, "--target_orientations_deg") == [0.0, 0.0, 0.0]
    assert three_arguments(run, "--orientation_tolerances_deg") == [1.5, 1.5, 1.5]


def test_targets_csv_round_trips(tmp_path):
    plan_path = write_plan(load_document(EXAMPLE), tmp_path / "plan")
    run = json.loads(plan_path.read_text())["runs"][0]
    with (tmp_path / "plan" / run["targets_file"]).open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == ["label", "x1", "y1", "x2", "y2", "x3", "y3"]
    assert [float(value) for value in rows[1][1:]] == [-1.3, 0.5, 0.0, 0.5, 1.3, 0.5]
