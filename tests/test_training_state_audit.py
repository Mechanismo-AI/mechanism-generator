"""Independent checks of safe state handling and portable model exports."""
import json
import pickle
import ast
from importlib.resources import files
import random
from types import SimpleNamespace
from typing import Any, Dict, Optional

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("pandas")
pytest.importorskip("matplotlib")
np = pytest.importorskip("numpy")
pytest.importorskip("safetensors")

from mechanism_generator.training import state


def test_numpy_rng_state_round_trips_through_restricted_checkpoint(tmp_path):
    original = np.random.get_state()
    try:
        np.random.seed(713)
        np.random.normal(size=3)  # Leave the cached Gaussian populated.
        payload = state.capture_numpy_state()
        expected_uniform = np.random.rand(12)
        expected_normal = np.random.normal(size=12)
        checkpoint = tmp_path / "rng.pt"
        torch.save({"rng": payload}, checkpoint)
        recovered = state.restricted_load(checkpoint, map_location="cpu")
        state.restore_numpy_state(recovered["rng"])
        assert np.array_equal(expected_uniform, np.random.rand(12))
        assert np.array_equal(expected_normal, np.random.normal(size=12))
    finally:
        np.random.set_state(original)


class _UnsafePayload:
    def __reduce__(self):
        return eval, ("1 + 1",)


def test_restricted_checkpoint_rejects_python_execution_without_globals(tmp_path):
    path = tmp_path / "unsafe.pt"
    torch.save(_UnsafePayload(), path)
    before = torch.serialization.get_safe_globals()
    with pytest.raises(pickle.UnpicklingError):
        state.restricted_load(path, map_location="cpu")
    assert torch.serialization.get_safe_globals() == before


@pytest.fixture
def model_payload():
    from mechanism_generator.engine.r25b import MechanismNN
    with torch.random.fork_rng():
        torch.manual_seed(715)
        model = MechanismNN().eval()
    return {"model_state_dict": model.state_dict(), "variant": "V5.3-R2.4_StreamingTargetTraining", "state_epoch": 4,
            "teacher_model_source": "private-machine-path", "notes": "private user notes", "optimizer_state_dict": {"unwanted": 5}}


def test_export_has_only_allowed_metadata_and_loads_in_public_inference(tmp_path, model_payload):
    from safetensors import safe_open
    from mechanism_generator.engine.r25b import MechanismNN, load_model_role
    checkpoint = tmp_path / "local.pth"
    torch.save(model_payload, checkpoint)
    output = tmp_path / "portable.safetensors"
    metadata = state.export_weights(checkpoint, output)
    with safe_open(str(output), framework="pt", device="cpu") as handle:
        assert handle.metadata() == metadata
    assert set(metadata) == {"variant", "state_epoch", "license", "format", "model_tensor_sha256"}
    assert "private" not in json.dumps(metadata)
    original = MechanismNN().eval()
    original.load_state_dict(model_payload["model_state_dict"])
    loaded = load_model_role("balanced", "r24", output, torch.device("cpu"))
    inputs = torch.rand(3, 6, generator=torch.Generator().manual_seed(6))
    with torch.inference_mode():
        assert torch.equal(original(inputs), loaded.model(inputs))
    roundtrip = state.restricted_load(output, map_location=torch.device("cpu"))
    assert roundtrip["variant"] == model_payload["variant"]
    assert roundtrip["state_epoch"] == 4
    assert state.model_tensor_sha256(roundtrip["model_state_dict"]) == metadata["model_tensor_sha256"]
    previous = output.read_bytes()
    repeated = tmp_path / "portable-again.safetensors"
    state.export_weights(checkpoint, repeated)
    assert repeated.read_bytes() == previous
    with pytest.raises(FileExistsError):
        state.export_weights(checkpoint, output)
    assert output.read_bytes() == previous
    assert not list(tmp_path.glob(".model-*"))


@pytest.mark.parametrize("field,value", [("variant", "private-path"), ("state_epoch", True), ("state_epoch", -1)])
def test_export_rejects_invalid_metadata_before_writing(tmp_path, model_payload, field, value):
    model_payload[field] = value
    checkpoint = tmp_path / "invalid.pth"
    torch.save(model_payload, checkpoint)
    output = tmp_path / "portable.safetensors"
    with pytest.raises(ValueError):
        state.export_weights(checkpoint, output)
    assert not output.exists()


def test_export_rejects_nonfinite_model_before_writing(tmp_path, model_payload):
    model_payload["model_state_dict"]["output_layer.bias"][0] = float("nan")
    checkpoint = tmp_path / "invalid.pth"
    torch.save(model_payload, checkpoint)
    output = tmp_path / "portable.safetensors"
    with pytest.raises(ValueError, match="finite"):
        state.export_weights(checkpoint, output)
    assert not output.exists()


@pytest.mark.parametrize("stage", ["r2", "r22", "r23a", "r24"])
def test_trainer_rng_restore_normalizes_device_mapped_states(stage):
    # Compile only the two state helpers; never execute a trainer's top-level run.
    tree = ast.parse(files("mechanism_generator.training").joinpath(stage + ".py").read_text())
    helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef)
               and node.name in {"capture_rng_state", "restore_rng_state"}]
    training_generator = torch.Generator().manual_seed(718)
    dataloader_generator = torch.Generator().manual_seed(719)
    namespace = {"torch": torch, "random": random, "Dict": Dict, "Optional": Optional, "Any": Any,
                 "capture_numpy_state": state.capture_numpy_state, "restore_numpy_state": state.restore_numpy_state,
                 "training_data_generator": training_generator, "dataloader_generator": dataloader_generator}
    exec(compile(ast.Module(body=helpers, type_ignores=[]), "<trainer RNG helpers>", "exec"), namespace)
    before = (random.getstate(), np.random.get_state(), torch.get_rng_state())
    def sample():
        return (random.random(), np.random.rand(4), torch.rand(4),
                torch.rand(4, generator=training_generator), torch.rand(4, generator=dataloader_generator))
    class DeviceMappedState:
        def __init__(self, tensor):
            self.tensor = tensor
        def cpu(self):
            return self.tensor
    try:
        captured = namespace["capture_rng_state"]()
        expected = sample()
        for key in ("torch_cpu", "training_data_generator", "dataloader_generator"):
            captured[key] = DeviceMappedState(captured[key])
        # Simulate CUDA-mapped saved state without requiring a GPU in CPU CI.
        captured["torch_cuda"] = [DeviceMappedState(torch.zeros(4, dtype=torch.uint8))]
        cuda_received = []
        namespace["torch"] = SimpleNamespace(set_rng_state=torch.set_rng_state, cuda=SimpleNamespace(
            is_available=lambda: True, set_rng_state_all=lambda states: cuda_received.extend(states)))
        namespace["restore_rng_state"](captured)
        actual = sample()
        assert expected[0] == actual[0]
        assert np.array_equal(expected[1], actual[1])
        assert all(torch.equal(left, right) for left, right in zip(expected[2:], actual[2:]))
        assert len(cuda_received) == 1
        assert isinstance(cuda_received[0], torch.Tensor) and cuda_received[0].device.type == "cpu"
    finally:
        random.setstate(before[0])
        np.random.set_state(before[1])
        torch.set_rng_state(before[2])
