import hashlib
import io
from importlib.resources import files
import pytest
from mechanism_generator.engine import models


def test_adapter_pins_the_installed_engine_and_model_set():
    from mechanism_generator.omts.adapter import capabilities
    profile = capabilities()
    for name, expected in profile["expected_engine_artifacts"].items():
        assert hashlib.sha256(files("mechanism_generator.engine").joinpath(name).read_bytes()).hexdigest() == expected
    assert profile["expected_artifacts"] == {item["file"]: item["sha256"] for item in models.manifest()["models"].values()}


@pytest.fixture
def miniature_model_set(monkeypatch):
    blob = b"fixture model bytes"
    profile = {"license": "Apache-2.0", "download_base": "https://example.invalid/release", "models": {
        "balanced": {"file": "balanced.safetensors", "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}}}
    monkeypatch.setattr(models, "manifest", lambda: profile)
    return blob


def test_verified_download_is_explicit_and_idempotent(tmp_path, monkeypatch, miniature_model_set):
    calls = []
    def open_url(url, timeout):
        calls.append(url)
        return io.BytesIO(miniature_model_set)
    monkeypatch.setattr(models, "urlopen", open_url)
    with pytest.raises(ValueError, match="Missing or mismatched"):
        models.verify(tmp_path)
    assert calls == []
    assert models.download(tmp_path) == models.verify(tmp_path)
    models.download(tmp_path)
    assert len(calls) == 1
    assert not list(tmp_path.glob(".download-*"))


@pytest.mark.parametrize("content", [b"wrong", b"oversized" * 100])
def test_corrupt_download_does_not_publish_partial_file(tmp_path, monkeypatch, miniature_model_set, content):
    monkeypatch.setattr(models, "urlopen", lambda *a, **k: io.BytesIO(content))
    with pytest.raises(ValueError):
        models.download(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_existing_mismatched_file_is_preserved(tmp_path, miniature_model_set):
    file = tmp_path / "balanced.safetensors"
    file.write_bytes(b"existing data")
    with pytest.raises(FileExistsError):
        models.download(tmp_path)
    assert file.read_bytes() == b"existing data"
