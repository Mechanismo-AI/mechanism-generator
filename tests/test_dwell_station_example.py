import csv
import json
from pathlib import Path

from mechanism_generator.omts import load_document, validate_document
from mechanism_generator.omts.adapter import prepare_plan, write_plan

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "omts" / "dwell_station.omts.yaml"
GAP_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "omts" / "gap_transfer.omts.yaml"


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
    # and (+130, 50) mm on the case-B-mirrored layout -- the approach, the
    # station and the depart poses, all level. The station pose (0, 50) mm
    # is the point the dwell demand (not encoded in the document) is
    # scored against by the failure-analysis digest.
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


def test_instrument_matches_case_study_b():
    # Deliberate comparability: the dwell instrument is numerically
    # identical to the case study B gap transfer (same poses, tolerances,
    # search portfolio and seed); only the brief it serves changes. The
    # dwell reading therefore lands in the same units and geometry class
    # as the recorded six-bar frontier.
    dwell = load_document(EXAMPLE)["tasks"][0]
    gap = load_document(GAP_EXAMPLE)["tasks"][0]
    assert dwell["motion"]["targets"] == gap["motion"]["targets"]
    assert dwell["mechanism_search"] == gap["mechanism_search"]
    assert dwell["requirements"] == gap["requirements"]
    assert dwell["search"] == gap["search"]
