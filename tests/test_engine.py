import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
pytest.importorskip("matplotlib")
pytest.importorskip("pandas")
from safetensors.torch import save_file
from mechanism_generator.engine import r25b, r25c, provenance


@pytest.mark.parametrize("branch", [-1, 1])
def test_circle_geometry_preserves_lengths_and_has_finite_gradients(branch):
    params = torch.tensor([[6., 2., 5., 4., .5, 1., -3., 2., .4]], dtype=torch.float64, requires_grad=True)
    theta = torch.linspace(0, 2 * math.pi, 181, dtype=torch.float64)
    sim = r25b.simulate_four_bar(params, theta, branch)
    assert sim["valid"].all()
    for x1, y1, x2, y2, expected in [("O2x", "O2y", "Ax", "Ay", 2.), ("Ax", "Ay", "Bx", "By", 5.), ("Bx", "By", "O4x", "O4y", 4.)]:
        length = torch.hypot(sim[x1] - sim[x2], sim[y1] - sim[y2])
        torch.testing.assert_close(length, torch.full_like(length, expected), atol=1e-6, rtol=1e-6)
    (sim["Px"].square().mean() + sim["Py"].square().mean()).backward()
    assert torch.isfinite(params.grad).all()


@pytest.mark.parametrize("mode", ["ordered", "unordered"])
def test_parameter_roundtrip_and_cyclic_order(mode):
    args = r25b.build_parser().parse_args([])
    target = torch.tensor([-6., 2., -2., 6., .5, 3.5], dtype=torch.float64)
    params = torch.tensor([6., 2., 5., 4., .5, 1., -3., 2., .4], dtype=torch.float64)
    phases = torch.tensor([5.5, .4, 2.], dtype=torch.float64)
    raw = r25b.encode_refinement_variables(params, phases, target, mode, args)
    decoded, result_phases = r25b.decode_refinement_variables(raw, target, mode, args)
    torch.testing.assert_close(decoded, params)
    torch.testing.assert_close(result_phases, phases)
    if mode == "ordered":
        gaps = torch.remainder(torch.roll(result_phases, -1) - result_phases, 2 * math.pi)
        assert (gaps > 0).all()
        assert abs(gaps.sum().item() - 2 * math.pi) < 1e-10


@pytest.mark.parametrize("case,level", [("benchmark_006", "path_acceptable_but_robustness_failed"), ("benchmark_014", "path_acceptable_but_selection_floor_failed")])
def test_unresolved_fixed_references_cannot_bypass_eligibility(case, level):
    args = r25c.build_parser().parse_args([])
    candidate = {"candidate_id": case, "portfolio_origin": "fixed", "selection_eligible": False, "qualification_level": level}
    assert r25c.ensure_fixed_representatives([], [candidate], args) == []
    assert r25c.ensure_fixed_representatives([candidate], [candidate], args) == []


def test_run_records_use_portable_paths_without_mutating_inputs(tmp_path):
    run = tmp_path / "private-profile" / "run"
    provenance.set_run_root(run)
    data = {"script": str(tmp_path / "private-profile" / "r25c.py"), "directory": str(run / "target1"),
            "history_path": str(run / "target1" / "history.csv"), "arguments": {"balanced_model": str(tmp_path / "balanced.safetensors")}}
    before = json.loads(json.dumps(data))
    r25b.write_json(run / "record.json", data)
    r25b.write_csv(run / "record.csv", [data])
    assert data == before
    for file in (run / "record.json", run / "record.csv"):
        assert "private-profile" not in file.read_text()
    result = json.loads((run / "record.json").read_text())
    assert result["history_path"] == "target1/history.csv"
    assert result["directory"] == "target1"


def test_public_loader_refuses_pickle_and_wrong_architecture(tmp_path):
    unsafe = tmp_path / "legacy.pth"
    unsafe.write_bytes(b"not a checkpoint")
    with pytest.raises(ValueError, match="safetensors"):
        r25b.load_model_role("balanced", "balanced", unsafe, torch.device("cpu"))
    wrong = tmp_path / "wrong.safetensors"
    save_file({"wrong": torch.zeros(1)}, str(wrong))
    with pytest.raises(RuntimeError):
        r25b.load_model_role("balanced", "balanced", wrong, torch.device("cpu"))


def test_tiny_optimizer_run_with_synthetic_weights(tmp_path):
    """Exercise real Adam/L-BFGS and artifact writing, without quality claims."""
    torch.manual_seed(42)
    path = tmp_path / "synthetic.safetensors"
    save_file(r25b.MechanismNN().state_dict(), str(path), metadata={"variant": "test-fixture", "state_epoch": "0"})
    output = tmp_path / "out"
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", MPLCONFIGDIR=str(tmp_path / "mpl"))
    arguments = [sys.executable, "-m", "mechanism_generator.engine.r25c", "--balanced_model", str(path), "--model_roles", "balanced",
                 "--targets", "-6", "2", "-2", "6", ".5", "3.5", "--profile_matrix", "paired", "--branches", "both",
                 "--adam_accuracy_steps", "2", "--adam_tradeoff_steps", "2", "--lbfgs_steps", "1",
                 "--portfolio_fixed_seed_count", "1", "--portfolio_release_seed_count", "1", "--portfolio_guarantee_fixed_count", "0",
                 "--portfolio_bridge_accuracy_steps", "1", "--portfolio_bridge_tradeoff_steps", "1", "--portfolio_bridge_lbfgs_steps", "1",
                 "--portfolio_release_accuracy_steps", "1", "--portfolio_release_tradeoff_steps", "1", "--portfolio_release_lbfgs_steps", "1",
                 "--seed_phase_steps", "31", "--optimization_global_steps", "31", "--verification_steps", "61",
                 "--device", "cpu", "--headless", "--no_plots", "--output_root", str(output)]
    result = subprocess.run(arguments, capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr
    manifests = list(output.rglob("run_manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text())
    assert len(manifest["targets"]) == 1
    for artifact in output.rglob("*.json"):
        assert str(tmp_path) not in artifact.read_text()
    for selected in output.rglob("selected_candidates.csv"):
        with selected.open(newline="") as stream:
            assert all(row["selection_eligible"] == "True" for row in csv.DictReader(stream))
