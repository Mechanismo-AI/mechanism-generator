"""Explicit download and verification of the optional training dependencies.

Reading the manifest and verifying local files never access the network.
"""
from importlib.resources import files
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen


def load_manifest(path: str | Path | None = None) -> dict:
    """Read the bundled dependency manifest, or an explicitly supplied file."""
    text = (Path(path).read_text(encoding="utf-8") if path is not None else
            files(__package__).joinpath("assets.json").read_text(encoding="utf-8"))
    profile = json.loads(text)
    if set(profile["assets"]) != {"teacher", "warmstart_r22", "transmission"}:
        raise ValueError("Training manifest must name teacher, warmstart_r22 and transmission")
    names = set()
    for entry in profile["assets"].values():
        name = entry["file"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.safetensors", name) or name in names:
            raise ValueError("Invalid or duplicate training asset filename")
        names.add(name)
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("Invalid training asset SHA256")
        if type(entry["bytes"]) is not int or entry["bytes"] <= 0:
            raise ValueError("Invalid training asset byte count")
        url = urlsplit(entry["url"])
        if url.scheme != "https" or not url.netloc or url.username or url.password or url.fragment:
            raise ValueError("Training asset downloads require an HTTPS URL without credentials")
    return profile


manifest = load_manifest


def sha256(path: str | Path) -> str:
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _matches(path: Path, entry: dict) -> bool:
    return path.is_file() and path.stat().st_size == entry["bytes"] and sha256(path) == entry["sha256"]


def verify(directory: str | Path, *, manifest_path: str | Path | None = None) -> dict[str, Path]:
    """Verify all three dependencies locally; return absolute paths by role."""
    directory = Path(directory)
    paths = {}
    for role, entry in load_manifest(manifest_path)["assets"].items():
        path = directory / entry["file"]
        if not _matches(path, entry):
            raise ValueError(f"Missing or mismatched {role} weights: {entry['file']}. "
                             "Run mechanism-train assets download --directory <folder>.")
        paths[role] = path.resolve()
    return paths


def download(directory: str | Path, *, manifest_path: str | Path | None = None) -> dict[str, Path]:
    """Download on explicit request; never replace an existing mismatched file."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for entry in load_manifest(manifest_path)["assets"].values():
        destination = directory / entry["file"]
        if destination.exists() or destination.is_symlink():
            if not _matches(destination, entry):
                raise FileExistsError(f"Refusing to replace mismatched weights: {destination.name}")
            continue
        descriptor, temporary_name = tempfile.mkstemp(prefix=".download-", dir=directory)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as output, urlopen(entry["url"], timeout=60) as response:
                count = 0
                while block := response.read(1024 * 1024):
                    count += len(block)
                    if count > entry["bytes"]:
                        raise ValueError(f"Unexpected download size for {destination.name}")
                    output.write(block)
            if not _matches(temporary, entry):
                raise ValueError(f"Downloaded weights failed verification: {destination.name}")
            # Publish only a complete verified file, without replacing a
            # destination created by another process during the download.
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return verify(directory, manifest_path=manifest_path)
