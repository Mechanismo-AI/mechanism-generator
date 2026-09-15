"""Convert the two hash-identified training dependencies to model-only weights.

Original research checkpoints are read-only inputs. This one-time export needs
NumPy 2.x; training uses safetensors without NumPy pickle reconstruction globals.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from numpy._core.multiarray import _reconstruct
import torch
from safetensors.torch import load_file, save_file

from mechanism_generator.engine.models import manifest as model_manifest
from mechanism_generator.engine.r25b import MechanismNN, extract_state_dict


ORIGINALS = {
    "teacher": {"source_file": "R2_teacher_best_validation.pth",
                "source_sha256": "5f1534d697ce950e473303f81358fb0423ceab289cd184d09c681ebcf24ecdb8",
                "file": "teacher.safetensors", "variant": "V5.3-R2_GeometryFix", "state_epoch": 239},
    "warmstart_r22": {"source_file": "R2_2_warmstart_best_feasible_transmission.pth",
                      "source_sha256": "67d90a31d98d42d2f2d9b4bf877cb34a06dfa510d333327b4902524c300c8900",
                      "file": "warmstart-r22.safetensors", "variant": "V5.3-R2.2_ConstrainedTransmission", "state_epoch": 148},
}
RELEASE_URL = "https://github.com/Mechanismo-AI/mechanism-generator/releases/download/v0.1.0a5"


def canonicalize_header(path: Path) -> None:
    """Make header ordering reproducible without changing tensor payloads."""
    raw = path.read_bytes()
    size = int.from_bytes(raw[:8], "little")
    header = json.dumps(json.loads(raw[8:8 + size]), sort_keys=True, separators=(",", ":")).encode()
    header += b" " * ((-len(header)) % 8)
    path.write_bytes(len(header).to_bytes(8, "little") + header + raw[8 + size:])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args(argv)
    # Verify every input before opening any checkpoint with the restricted loader.
    for entry in ORIGINALS.values():
        if hashlib.sha256((args.source_directory / entry["source_file"]).read_bytes()).hexdigest() != entry["source_sha256"]:
            parser.error(f"Original checkpoint identity mismatch: {entry['source_file']}")
    outputs = [entry["file"] for entry in ORIGINALS.values()] + ["assets.json", "TRAINING_SHA256SUMS.txt"]
    for name in outputs:
        if (args.output_directory / name).exists() or (args.output_directory / name).is_symlink():
            parser.error(f"Refusing to overwrite existing export: {name}")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    generator = torch.Generator(device="cpu").manual_seed(9142026)
    points = torch.rand((128, 3, 2), generator=generator, dtype=torch.float32)
    points[:, :, 0] = points[:, :, 0] * 8 - 7
    points[:, :, 1] = points[:, :, 1] * 6 + 1
    targets = points.reshape(-1, 6)
    entries = {}
    for role, entry in ORIGINALS.items():
        # Explicit NumPy RNG reconstruction types are permitted only here, for
        # known hash-verified research archives. No unrestricted pickle load.
        with torch.serialization.safe_globals([_reconstruct, np.ndarray, np.dtype, type(np.dtype(np.uint32))]):
            checkpoint = torch.load(args.source_directory / entry["source_file"], map_location="cpu", weights_only=True)
        if checkpoint["variant"] != entry["variant"] or checkpoint.get("state_epoch", checkpoint.get("epoch")) != entry["state_epoch"]:
            raise ValueError(f"Unexpected source metadata for {role}")
        state = {key: value.detach().cpu().contiguous().clone() for key, value in extract_state_dict(checkpoint).items()}
        if any(not bool(torch.isfinite(value).all()) for value in state.values()):
            raise ValueError(f"Non-finite model tensors for {role}")
        original = MechanismNN().eval()
        original.load_state_dict(state, strict=True)
        metadata = {"format": "pt", "license": "Apache-2.0", "role": role,
                    "variant": entry["variant"], "state_epoch": str(entry["state_epoch"]),
                    "source_sha256": entry["source_sha256"]}
        path = args.output_directory / entry["file"]
        save_file(state, str(path), metadata=metadata)
        canonicalize_header(path)
        loaded = load_file(str(path))
        if state.keys() != loaded.keys() or any(value.dtype != loaded[key].dtype or not torch.equal(value, loaded[key]) for key, value in state.items()):
            raise ValueError(f"Export changed tensors for {role}")
        exported = MechanismNN().eval()
        exported.load_state_dict(loaded, strict=True)
        with torch.inference_mode():
            before, after = original(targets), exported(targets)
        if not torch.equal(before, after):
            raise ValueError(f"Export changed inference for {role}")
        entries[role] = {**entry, "url": RELEASE_URL + "/" + path.name,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
                         "parameters": sum(value.numel() for value in state.values()), "tensor_count": len(state),
                         "export_checks": {"exact_tensor_equality": True, "inference_cases": len(targets), "max_absolute_difference": 0.0}}
        print(f"{role}: {path.stat().st_size} bytes; exact tensors and inference parity.")
    existing = model_manifest()
    entries["transmission"] = {**existing["models"]["transmission"],
                               "url": existing["download_base"] + "/" + existing["models"]["transmission"]["file"]}
    profile = {"version": "0.1.0a5", "license": "Apache-2.0", "format": "safetensors",
               "description": "Optional model-only dependencies for preserved training recipes; transmission reuses the published a2 asset.",
               "training_data": {"origin": "Synthetic target triples generated locally with private CPU PyTorch generators; no external dataset is required.",
                                  "development_data": "Repeatedly reused research development targets, not an untouched test set.",
                                  "development_tensor_sha256": "4636ea89d5210676c17fe66cf385008ab043ae876c04fdbfea72ad423e911b7f"},
               "export_verification": {"device": "cpu", "torch": str(torch.__version__), "numpy": str(np.__version__), "seed": 9142026, "dtype": "float32"},
               "assets": entries}
    (args.output_directory / "assets.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8", newline="\n")
    (args.output_directory / "TRAINING_SHA256SUMS.txt").write_text(
        "".join(f"{entry['sha256']}  {entry['file']}\n" for role, entry in entries.items() if role in ORIGINALS),
        encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
