import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("numpy")
from mechanism_generator.training import data


def test_development_targets_match_historical_tensor_digest_without_changing_rng():
    before = torch.random.get_rng_state().clone()
    targets = data.generate_development_targets()
    assert targets.shape == (512, 6)
    assert targets.dtype == torch.float32
    assert targets.device.type == "cpu"
    assert data.tensor_sha256(targets) == data.DEVELOPMENT_TENSOR_SHA256
    assert torch.equal(torch.random.get_rng_state(), before)
    assert ((targets[:, ::2] >= -7) & (targets[:, ::2] < 1)).all()
    assert ((targets[:, 1::2] >= 1) & (targets[:, 1::2] < 7)).all()


def test_stream_zero_matches_historical_digest_and_streams_are_independent():
    before = torch.random.get_rng_state().clone()
    first = data.generate_stream_targets(0)
    second = data.generate_stream_targets(1)
    assert data.tensor_sha256(first) == "fd1a400229fce8aa5025d2e19459f128449ddb41be038d00337d4fdb32aac4a7"
    assert not torch.equal(first, second)
    assert torch.equal(second, data.generate_stream_targets(1))
    assert torch.equal(torch.random.get_rng_state(), before)


@pytest.mark.parametrize("generator,kwargs", [
    (data.generate_development_targets, {"seed": -1}),
    (data.generate_development_targets, {"seed": True}),
    (data.generate_development_targets, {"seed": 2**64}),
    (data.generate_development_targets, {"count": 0}),
    (data.generate_development_targets, {"count": 1.5}),
    (data.generate_stream_targets, {"index": -1}),
    (data.generate_stream_targets, {"index": True}),
    (data.generate_stream_targets, {"index": 2**64}),
])
def test_invalid_generation_parameters_fail(generator, kwargs):
    with pytest.raises(ValueError):
        generator(**kwargs)


def test_targets_round_trip_with_weights_only_loader_and_refuse_overwrite(tmp_path):
    targets = data.generate_development_targets(count=32)
    output = tmp_path / "data" / "targets.pt"
    assert data.write_targets(output, targets) == output.resolve()
    assert torch.equal(data.load_targets(output), targets)
    assert torch.equal(torch.load(output, weights_only=True), targets)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        data.write_targets(output, data.generate_development_targets(seed=102, count=32))
    assert output.read_bytes() == original
    assert not list(output.parent.glob(".targets-*"))


@pytest.mark.parametrize("invalid", [torch.zeros(2, 5), torch.zeros(2, 6, dtype=torch.float64),
                                    torch.full((2, 6), float("nan")), {"targets": torch.zeros(2, 6)}])
def test_loaded_payload_must_be_a_finite_float32_target_tensor(tmp_path, invalid):
    path = tmp_path / "invalid.pt"
    torch.save(invalid, path)
    with pytest.raises(ValueError):
        data.load_targets(path)


def test_smaller_smoke_data_keeps_default_development_prefix():
    assert torch.equal(data.generate_development_targets(count=32), data.generate_development_targets()[:32])


@pytest.mark.parametrize("seed,count", [(101, 512), (717, 32)])
def test_wrapper_development_targets_match_r2_generation(seed, count):
    import ast
    from importlib.resources import files
    from typing import Optional
    from mechanism_generator.training import cli
    tree = ast.parse(files("mechanism_generator.training").joinpath("r2.py").read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "generate_target_point_triples")
    bounds = [node for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Tuple) and {name.id for name in target.elts if isinstance(name, ast.Name)}
                      in ({"X_MIN", "X_MAX"}, {"Y_MIN", "Y_MAX"}) for target in node.targets)]
    namespace = {"torch": torch, "Optional": Optional}
    exec(compile(ast.Module(body=[*bounds, function], type_ignores=[]), "<R2 target generation>", "exec"), namespace)
    args = cli.stage_arguments("r2", "historical", "output", "development.pt", seed=seed)
    assert args[args.index("--seed") + 1] == str(seed)
    # R2's validation_generator uses the declared seed plus 3001.
    generator = torch.Generator(device="cpu").manual_seed(seed + 3001)
    actual = namespace["generate_target_point_triples"](count, generator=generator)
    assert torch.equal(actual, data.generate_development_targets(seed=seed, count=count))
