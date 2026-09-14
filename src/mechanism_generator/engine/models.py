"""Explicit download and hash verification of the versioned public weights."""
from importlib.resources import files
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen


def manifest() -> dict:
    return json.loads(files(__package__).joinpath("models.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(directory: str | Path) -> dict[str, Path]:
    directory = Path(directory)
    paths = {}
    for role, entry in manifest()["models"].items():
        path = directory / entry["file"]
        if not path.is_file() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"Missing or mismatched {role} weights: {entry['file']}. Run mechanism-models download --directory <folder>.")
        paths[role] = path.resolve()
    return paths


def download(directory: str | Path) -> dict[str, Path]:
    """Download only on request; never replace an existing mismatched file."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    profile = manifest()
    for entry in profile["models"].values():
        destination = directory / entry["file"]
        if destination.exists():
            if not destination.is_file() or sha256(destination) != entry["sha256"]:
                raise FileExistsError(f"Refusing to replace mismatched weights: {destination.name}")
            continue
        descriptor, temp_name = tempfile.mkstemp(prefix=".download-", dir=directory)
        temporary = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as output, urlopen(profile["download_base"] + '/' + entry["file"], timeout=60) as response:
                count = 0
                while block := response.read(1024 * 1024):
                    count += len(block)
                    if count > entry["bytes"]:
                        raise ValueError(f"Unexpected download size for {destination.name}")
                    output.write(block)
            if temporary.stat().st_size != entry["bytes"] or sha256(temporary) != entry["sha256"]:
                raise ValueError(f"Downloaded weights failed verification: {destination.name}")
            # Same-filesystem hard linking atomically publishes a complete file,
            # and refuses to replace a concurrent writer's destination.
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    return verify(directory)


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download", "verify"))
    parser.add_argument("--directory", type=Path, default=Path("models"))
    args = parser.parse_args(argv)
    try:
        paths = download(args.directory) if args.action == "download" else verify(args.directory)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Model operation failed: {error}\n")
    print(f"Verified {len(paths)} model files ({manifest()['license']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
