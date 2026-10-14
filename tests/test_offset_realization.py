"""Offset realization (spec open question 6): recorded, never gated.

A line verified under declared `applied_offsets` stays verified whether or
not the document records how each offset is physically realized; the gap is
made visible in `line_result.json` instead.
"""
import json
from pathlib import Path

import pytest

from mechanism_generator.omts import DocumentError, load_document, validate_document
from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan
from mechanism_generator.omts.line_verify import verify_line


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pair_document():
    return load_document(ROOT / "examples/omts/synchronized_pair.omts.yaml")


@pytest.fixture
def offset_document(pair_document):
    # catcher offset 20 keeps the default passing line passing: grab 120 -> 140,
    # still inside the window [100, 140] (tolerance 5) with lead 40 in [10, 45].
    pair_document["synchronization"]["applied_offsets"] = {"catcher": {"phase": 20}}
    return pair_document


TASK_IDS = ["gate", "catcher"]
TARGETS = {"gate": ["hold", "release", "rest"], "catcher": ["grab", "carry", "park"]}


def _write_manifest(root, task, candidates, crank="positive"):
    run_dir = root / f"results/task-{TASK_IDS.index(task) + 1:03d}" / "r25c" / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_status": "completed",
        "targets": [{
            "label": task,
            "crank_direction": crank,
            "selected": [
                {"rank": rank, "candidate_id": row["id"],
                 **{f"phase_{i + 1}_deg": row["phases"][i] for i in range(3)}}
                for rank, row in enumerate(candidates, start=1)
            ],
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


def _verify(tmp_path, line):
    _write_manifest(tmp_path, "gate", [{"id": "g1", "phases": [30, 130, 250]}])
    _write_manifest(tmp_path, "catcher", [{"id": "c1", "phases": [120, 220, 20]}])
    return verify_line(_write_plan(tmp_path, line))


def _base_line():
    return {
        "master_cycle_id": "line_shaft",
        "period": 1.2,
        "phase_reference": {"gate": "hold", "catcher": None},
        "events": [{
            "id": "handoff_window", "participants": [
                {"task": "gate", "target": "release"}, {"task": "catcher", "target": "grab"}],
            "window_deg": [100, 140], "tolerance_deg": 5, "mode": "hard",
        }],
        "relations": [{
            "id": "release_before_grab", "from": {"task": "gate", "target": "release"},
            "to": {"task": "catcher", "target": "grab"}, "type": "ordering",
            "min_lead_deg": 10, "max_lead_deg": 45, "mode": "hard",
        }],
        "verification": "pending_timeline_verification",
    }


def _errors(document):
    return "\n".join(validate_document(document))


# -- document validation ------------------------------------------------------

def test_document_with_realization_validates(offset_document):
    offset_document["synchronization"]["offset_realization"] = {
        "catcher": {"method": "gear_train", "detail": "60:12 spur pair, tooth index 7"},
    }
    assert validate_document(offset_document) == []


def test_realization_for_task_without_declared_offset_is_rejected(pair_document):
    pair_document["synchronization"]["offset_realization"] = {
        "catcher": {"method": "crank_phase"},
    }
    assert "no applied offset" in _errors(pair_document)


def test_realization_unknown_task_is_rejected(offset_document):
    offset_document["synchronization"]["offset_realization"] = {
        "ghost": {"method": "coupling"},
    }
    assert "unknown task" in _errors(offset_document)


def test_realization_method_must_come_from_the_enum(offset_document):
    offset_document["synchronization"]["offset_realization"] = {
        "catcher": {"method": "set_screw", "detail": "12 deg"},
    }
    assert "offset_realization" in _errors(offset_document)


# -- adapter ------------------------------------------------------------------

def test_adapter_records_realization_in_line_section(offset_document):
    offset_document["synchronization"]["offset_realization"] = {
        "catcher": {"method": "gear_train", "detail": "60:12 spur pair, tooth index 7"},
    }
    line = prepare_plan(offset_document)["line"]
    assert line["applied_offsets"] == {"catcher": 20.0}
    assert line["offset_realization"] == {
        "catcher": {"method": "gear_train", "detail": "60:12 spur pair, tooth index 7"},
    }


def test_realization_without_declared_offset_fails_closed_at_validation(pair_document):
    pair_document["synchronization"]["offset_realization"] = {
        "catcher": {"method": "crank_phase"},
    }
    with pytest.raises(DocumentError, match="no applied offset"):
        prepare_plan(pair_document)


# -- verifier -----------------------------------------------------------------

def test_verified_line_echoes_realization_record(tmp_path):
    line = _base_line()
    line["applied_offsets"] = {"catcher": 20.0}
    line["offset_realization"] = {"catcher": {"method": "coupling", "detail": "keyway 20 deg"}}
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    assert result["offset_realization"] == {
        "recorded": True,
        "tasks": {"catcher": {"method": "coupling", "detail": "keyway 20 deg"}},
    }


def test_missing_realization_does_not_block_verified(tmp_path):
    line = _base_line()
    line["applied_offsets"] = {"catcher": 20.0}
    result = _verify(tmp_path, line)
    assert result["status"] == "verified"
    assert result["offset_realization"]["recorded"] is False
    assert result["offset_realization"]["unrecorded_tasks"] == ["catcher"]
    assert result["offset_realization"]["tasks"] == {}


def test_no_offsets_means_no_realization_summary(tmp_path):
    result = _verify(tmp_path, _base_line())
    assert result["status"] == "verified"
    assert "offset_realization" not in result
