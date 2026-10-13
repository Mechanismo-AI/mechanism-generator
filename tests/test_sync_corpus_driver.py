"""The sync-corpus driver: offsets are timeline composition, not search.

These tests pin the sync-corpus-04 behavior: per-variant applied_offsets
injection, exact reuse of prior engine results (offsets never change the
search), fallback to the engine when no reusable tree exists, and the
summary record. No engine is required: validate and adapt run in-process and
the engine subprocess is faked or asserted absent.
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVER_PATH = ROOT / "jobs" / "sync-corpus-01" / "corpus_run.py"

_spec = importlib.util.spec_from_file_location("corpus_run", DRIVER_PATH)
driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(driver)

TASK_PHASES = {"gate": [30, 130, 250], "catcher": [160, 220, 20]}
TASK_NUMBERS = {"gate": 1, "catcher": 2}


def _write_manifest(results_dir: Path, task: str, phases, crank="positive",
                    status="completed"):
    run_dir = results_dir / f"task-{TASK_NUMBERS[task]:03d}" / "r25c" \
        / "20260101_000000_000000_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_status": status,
        "targets": [{
            "label": task,
            "crank_direction": crank,
            "selected": [{
                "rank": rank, "candidate_id": row[0],
                **{f"phase_{i + 1}_deg": phase for i, phase in
                   enumerate(row[1])},
            } for rank, row in enumerate(phases, start=1)],
        }],
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest),
                                               encoding="utf-8")


def _pair_document(index: int = 3, offsets: dict | None = None) -> dict:
    base = driver.load_yaml(driver.BASE_DOCUMENT)
    document = driver.variant_document(base, index, 70, 1.1)
    if offsets is not None:
        document["synchronization"]["applied_offsets"] = offsets
    return document


@pytest.fixture
def fake_cli(monkeypatch):
    """Record subprocess commands; run validate/adapt in-process; the
    engine either raises (unexpected) or is handled by the provided callable."""
    from mechanism_generator.omts import load_document
    from mechanism_generator.omts.cli import main as cli_main
    from mechanism_generator.omts.validation import require_valid

    commands = []

    def check_call(command, cwd):
        command = list(command)
        commands.append(command)
        if "validate" in command:
            require_valid(load_document(command[command.index("validate") + 1]))
        elif "adapt" in command:
            cli_main(["adapt", command[command.index("adapt") + 1],
                      "--output-dir", command[command.index("--output-dir") + 1]])
        elif "mechanism_generator.engine" in command:
            engine_handler(command, cwd)
        else:
            raise RuntimeError(f"unexpected command: {command[:3]}")

    engine_handler = None

    def set_engine(handler):
        nonlocal engine_handler
        engine_handler = handler

    monkeypatch.setattr(driver, "check_call", check_call)
    return commands, set_engine


@pytest.mark.parametrize("text,expected", [
    ('{"corpus_pair_01": {"catcher": {"phase": 105}}}',
     {"corpus_pair_01": {"catcher": {"phase": 105}}}),
    ('{}', {}),
])
def test_offsets_file_parses(tmp_path, text, expected):
    path = tmp_path / "offsets.json"
    path.write_text(text, encoding="utf-8")
    assert driver.load_offsets(path) == expected


@pytest.mark.parametrize("text", [
    "not json",
    "[1, 2]",
    '{"corpus_pair_01": 5}',
    '"just a string"',
])
def test_malformed_offsets_files_are_rejected(tmp_path, text):
    path = tmp_path / "offsets.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        driver.load_offsets(path)


def _fake_source_results(root: Path, variant: str, catcher_phases=None):
    results = root / variant / "plan" / "results"
    _write_manifest(results, "gate", [("g1", TASK_PHASES["gate"])])
    _write_manifest(results, "catcher",
                   [("c1", catcher_phases or TASK_PHASES["catcher"])])
    return root


def test_reused_results_verify_with_offsets_without_engine(
        tmp_path, fake_cli):
    commands, _ = fake_cli
    source = _fake_source_results(tmp_path / "prior", "corpus_pair_03")
    document = _pair_document(offsets={"catcher": {"phase": 325}})
    out_dir = tmp_path / "runs" / "corpus_pair_03"
    out_dir.mkdir(parents=True)

    row = driver.run_variant(document, out_dir, models=tmp_path / "models",
                             quick=False, results_from=source)

    # raw grab phase 160 + offset 325 = 125: inside the [95, 145] handoff
    # window and lead 25 inside [10, 45] — no engine run needed.
    assert row["status"] == "verified"
    assert row["passing_combination_count"] == 1
    assert row["applied_offsets"] == {"catcher": pytest.approx(325.0)}
    assert row["results_reused"] is True
    assert row["selected_counts"] == {"gate": 1, "catcher": 1}
    assert all("mechanism_generator.engine" not in command
               for command in commands)
    assert any("validate" in command for command in commands)
    assert any("adapt" in command for command in commands)
    assert (out_dir / "plan" / "line_result.json").exists()


def test_reused_results_without_offsets_stay_failed(tmp_path, fake_cli):
    commands, _ = fake_cli
    source = _fake_source_results(tmp_path / "prior", "corpus_pair_03")
    document = _pair_document()  # no applied_offsets declaration
    out_dir = tmp_path / "runs" / "corpus_pair_03"
    out_dir.mkdir(parents=True)

    row = driver.run_variant(document, out_dir, models=tmp_path / "models",
                             quick=False, results_from=source)

    # Control: raw grab phase 160 is outside the window, and no offset was
    # declared, so the reused line must fail — reuse is not wishful.
    assert row["status"] == "failed"
    assert row["applied_offsets"] is None
    assert row["results_reused"] is True
    assert all("mechanism_generator.engine" not in command
               for command in commands)


def test_missing_reusable_results_fall_back_to_engine(tmp_path, fake_cli):
    commands, set_engine = fake_cli
    source = tmp_path / "prior"  # no corpus_pair_NN trees inside

    def engine_handler(command, cwd):
        output_root = command[command.index("--output_root") + 1]
        results_dir = Path(output_root).parent
        task = "gate" if "task-001" in output_root else "catcher"
        phases = {"gate": TASK_PHASES["gate"],
                  "catcher": [120, 220, 20]}[task]
        _write_manifest(results_dir, task, [("x1", phases)])

    set_engine(engine_handler)
    document = _pair_document(offsets={"catcher": {"phase": 5}})
    out_dir = tmp_path / "runs" / "corpus_pair_03"
    out_dir.mkdir(parents=True)

    row = driver.run_variant(document, out_dir, models=tmp_path / "models",
                             quick=False, results_from=source)

    engine_commands = [command for command in commands
                       if "mechanism_generator.engine" in command]
    assert len(engine_commands) == 2
    assert row["results_reused"] is False
    # grab 120 + offset 5 = 125: the engine fallback still composes offsets.
    assert row["status"] == "verified"
    assert row["applied_offsets"] == {"catcher": pytest.approx(5.0)}


def test_main_records_offsets_and_reuse_per_variant(
        tmp_path, fake_cli, monkeypatch, capsys):
    commands, _ = fake_cli
    models = tmp_path / "models"
    models.mkdir()
    source = tmp_path / "runs" / "sync-corpus-03"
    # pair 01: raw grab 20 + declared offset 105 = 125 -> verified.
    _fake_source_results(source, "corpus_pair_01",
                         catcher_phases=[20, 80, 220])
    # pair 02: no offsets entry; raw grab 120 lands in the window already.
    _fake_source_results(source, "corpus_pair_02",
                         catcher_phases=[120, 220, 20])
    offsets_path = tmp_path / "offsets.json"
    offsets_path.write_text(json.dumps({
        "corpus_pair_01": {"catcher": {"phase": 105}},
        "corpus_pair_02": {},
        "corpus_pair_03": {"catcher": {"phase": 333}},
    }), encoding="utf-8")
    output = tmp_path / "runs" / "sync-corpus-04"
    monkeypatch.setattr(driver.sys, "argv", [
        "corpus_run.py", "--count", "2", "--models", str(models),
        "--offsets", str(offsets_path), "--results-from", str(source),
        "--output-dir", str(output),
    ])

    assert driver.main() == 0
    rows = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert [row["task_set_id"] for row in rows] == \
        ["corpus_pair_01", "corpus_pair_02"]
    assert rows[0]["applied_offsets"] == {"catcher": pytest.approx(105.0)}
    assert rows[0]["results_reused"] is True
    assert rows[0]["status"] == "verified"
    assert rows[1]["applied_offsets"] is None
    assert rows[1]["results_reused"] is True
    assert rows[1]["status"] == "verified"
    # the entry outside the run is a warning, not an error
    out = capsys.readouterr().out
    assert "corpus_pair_03" in out and "ignored" in out
    assert all("mechanism_generator.engine" not in command
               for command in commands)
    # the injected document is what was validated and adapted
    import yaml
    doc = yaml.safe_load((output / "corpus_pair_01" / "document.omts.yaml")
                         .read_text(encoding="utf-8"))
    assert doc["synchronization"]["applied_offsets"] == \
        {"catcher": {"phase": 105}}
