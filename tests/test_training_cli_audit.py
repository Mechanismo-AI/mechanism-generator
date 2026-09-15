from types import SimpleNamespace

import pytest

pytest.importorskip("torch")
for dependency in ("numpy", "pandas", "matplotlib", "safetensors"):
    pytest.importorskip(dependency)

from mechanism_generator.training import cli


def test_data_cli_rejects_zero_count_without_creating_file(tmp_path, capsys):
    output = tmp_path / "targets.pt"
    with pytest.raises(SystemExit) as error:
        cli.main(["data", "--count", "0", "--output", str(output)])
    assert error.value.code == 1
    assert "count" in capsys.readouterr().err
    assert not output.exists()


def test_fatal_trainer_log_cannot_report_success_even_with_zero_exit(tmp_path, monkeypatch):
    def failed_process(*args, **kwargs):
        kwargs["stdout"].write("[FATAL] Numerical recovery failed.\n")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(cli.subprocess, "run", failed_process)
    output = tmp_path / "stage"
    with pytest.raises(RuntimeError, match="fatal"):
        cli._run_stage("r2", [], output, "smoke")
    assert not (output / "selected.safetensors").exists()
    assert not (output / "summary.json").exists()


def test_chain_failure_is_recorded_without_advancing_to_next_stage(tmp_path, monkeypatch):
    import json
    stages = []
    def fail(stage, *args):
        stages.append(stage)
        raise RuntimeError("A training error")
    monkeypatch.setattr(cli, "_run_stage", fail)
    output = tmp_path / "chain"
    with pytest.raises(SystemExit) as error:
        cli.main(["chain", "--preset", "smoke", "--output", str(output)])
    assert error.value.code == 1
    report = json.loads((output / "training-summary.json").read_text())
    assert report["status"] == "failed"
    assert report["failed_stage"] == "r2"
    assert report["stages"] == []
    assert stages == ["r2"]


def test_r24_selects_historical_balanced_output_and_r23a_transmission():
    recipes = cli.recipes()
    assert recipes["r24"]["selection"] == "best_composite.pth"
    assert recipes["r23a"]["selection"] == "best_feasible_transmission.pth"


def test_r2_rejects_unused_dependencies_before_creating_output(tmp_path):
    output = tmp_path / 'run'
    with pytest.raises(SystemExit) as error:
        cli.main(['run', 'r2', '--output', str(output), '--teacher', 'unused.safetensors'])
    assert error.value.code == 1
    assert not output.exists()
