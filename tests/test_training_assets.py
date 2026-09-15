import hashlib
import io
import json

import pytest

from mechanism_generator.engine import models
from mechanism_generator.training import assets


def test_packaged_training_assets_reuse_exact_public_transmission():
    profile = assets.load_manifest()
    transmission = models.manifest()["models"]["transmission"]
    assert set(profile["assets"]) == {"teacher", "warmstart_r22", "transmission"}
    for key in ("file", "sha256", "bytes", "source_sha256", "variant", "state_epoch"):
        assert profile["assets"]["transmission"][key] == transmission[key]
    assert profile["assets"]["transmission"]["url"].endswith("/v0.1.0a2/transmission.safetensors")
    assert profile["license"] == "Apache-2.0"
    assert profile["assets"]["teacher"]["state_epoch"] == 239
    assert profile["assets"]["warmstart_r22"]["state_epoch"] == 148


@pytest.fixture
def miniature_assets(tmp_path):
    blobs = {"teacher": b"teacher fixture", "warmstart_r22": b"warmstart fixture", "transmission": b"transmission fixture"}
    profile = {"assets": {role: {"file": role + ".safetensors", "bytes": len(blob),
                                "sha256": hashlib.sha256(blob).hexdigest(),
                                "url": "https://example.invalid/" + role + ".safetensors"}
                          for role, blob in blobs.items()}}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path, blobs


def test_download_is_explicit_verified_and_idempotent(tmp_path, monkeypatch, miniature_assets):
    profile, blobs = miniature_assets
    calls = []
    def open_url(url, timeout):
        calls.append(url)
        return io.BytesIO(blobs[url.rsplit("/", 1)[-1].removesuffix(".safetensors")])
    monkeypatch.setattr(assets, "urlopen", open_url)
    output = tmp_path / "weights"
    with pytest.raises(ValueError, match="Missing or mismatched"):
        assets.verify(output, manifest_path=profile)
    assert calls == []
    result = assets.download(output, manifest_path=profile)
    assert result == assets.verify(output, manifest_path=profile)
    assert set(result) == set(blobs)
    assert all(path.is_absolute() for path in result.values())
    assert len(calls) == 3
    assets.download(output, manifest_path=profile)
    assert len(calls) == 3
    assert not list(output.glob(".download-*"))


@pytest.mark.parametrize("content", [b"wrong", b"teacher fixturX", b"oversized" * 100])
def test_corrupt_or_oversized_download_is_not_published(tmp_path, monkeypatch, miniature_assets, content):
    profile, _ = miniature_assets
    monkeypatch.setattr(assets, "urlopen", lambda *a, **k: io.BytesIO(content))
    output = tmp_path / "weights"
    with pytest.raises(ValueError):
        assets.download(output, manifest_path=profile)
    assert not list(output.iterdir())


def test_existing_mismatched_asset_is_preserved(tmp_path, monkeypatch, miniature_assets):
    profile, _ = miniature_assets
    path = tmp_path / "teacher.safetensors"
    path.write_bytes(b"keep this")
    monkeypatch.setattr(assets, "urlopen", lambda *a, **k: pytest.fail("Unexpected network access"))
    with pytest.raises(FileExistsError):
        assets.download(tmp_path, manifest_path=profile)
    assert path.read_bytes() == b"keep this"


def test_concurrent_destination_is_not_overwritten(tmp_path, monkeypatch, miniature_assets):
    profile, blobs = miniature_assets
    output = tmp_path / "weights"
    def open_url(url, timeout):
        (output / "teacher.safetensors").write_bytes(b"concurrent writer")
        return io.BytesIO(blobs["teacher"])
    monkeypatch.setattr(assets, "urlopen", open_url)
    with pytest.raises(FileExistsError):
        assets.download(output, manifest_path=profile)
    assert (output / "teacher.safetensors").read_bytes() == b"concurrent writer"
    assert not list(output.glob(".download-*"))


@pytest.mark.parametrize("key,value", [("file", "../outside.safetensors"), ("sha256", "wrong"),
                                       ("bytes", True), ("url", "file:///tmp/private"),
                                       ("url", "https://user:secret@example.invalid/weights")])
def test_invalid_manifest_fails_before_download(tmp_path, monkeypatch, miniature_assets, key, value):
    path, _ = miniature_assets
    profile = json.loads(path.read_text())
    profile["assets"]["teacher"][key] = value
    path.write_text(json.dumps(profile))
    monkeypatch.setattr(assets, "urlopen", lambda *a, **k: pytest.fail("Unexpected network access"))
    with pytest.raises(ValueError):
        assets.download(tmp_path / "weights", manifest_path=path)
