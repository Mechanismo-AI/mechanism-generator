"""Export the three hash-identified research checkpoints to inference-only files.

Install the project with its engine extra first. Originals are read-only inputs.
NumPy 2.x is required for this one-time legacy conversion. Public inference never
loads pickle checkpoints or needs these NumPy reconstruction allowlists.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from numpy._core.multiarray import _reconstruct
import torch
from safetensors.torch import load_file, save_file

from mechanism_generator.engine.r25b import MechanismNN, extract_state_dict

ORIGINALS = {
    "balanced": ("R2_4_best_composite.pth", "b383499ae463a31a26a671b58951e54daa43c3f7301452e698b5789d0582f665"),
    "path": ("R2_4_best_path.pth", "1d0c7e993ccf162aa67d2a28b7a43ff946b6d3a153a7968f1a1299e30fd014cd"),
    "transmission": ("R2_3a_warmstart_best_feasible_transmission.pth", "b035b26099e1dcd30e9f0b748b88eb9179a0a7922ed3bb95933b26948a53f60d"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-directory", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    for name, expected in ORIGINALS.values():
        if hashlib.sha256((args.source_directory / name).read_bytes()).hexdigest() != expected:
            parser.error(f"Original checkpoint identity mismatch: {name}")
    args.output_directory.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    generator = torch.Generator().manual_seed(9142026)
    points = torch.rand((128, 3, 2), generator=generator)
    points[:, :, 0] = points[:, :, 0] * 8 - 7
    points[:, :, 1] = points[:, :, 1] * 6 + 1
    targets = points.reshape(-1, 6)
    models = {}
    for role, (name, source_hash) in ORIGINALS.items():
        # Known, hash-gated originals contain a NumPy RNG array. Retain the
        # restricted loader and allow only its concrete reconstruction types.
        with torch.serialization.safe_globals([_reconstruct, np.ndarray, np.dtype, type(np.dtype(np.uint32))]):
            checkpoint = torch.load(args.source_directory / name, map_location="cpu", weights_only=True)
        state = {key: value.detach().cpu().contiguous().clone() for key, value in extract_state_dict(checkpoint).items()}
        if any(not torch.isfinite(value).all() for value in state.values()):
            raise ValueError(f"Non-finite tensors in {role}")
        original = MechanismNN().eval()
        original.load_state_dict(state, strict=True)
        metadata = {"format": "pt", "license": "Apache-2.0", "role": role,
                    "variant": str(checkpoint["variant"]), "state_epoch": str(checkpoint.get("state_epoch", checkpoint["epoch"])),
                    "source_sha256": source_hash}
        path = args.output_directory / f"{role}.safetensors"
        save_file(state, str(path), metadata=metadata)
        # Canonicalize only the JSON header for reproducible bytes. Tensor bytes
        # are untouched; all offsets remain relative to the end of the header.
        raw = path.read_bytes()
        header_size = int.from_bytes(raw[:8], "little")
        header = json.dumps(json.loads(raw[8:8 + header_size]), sort_keys=True, separators=(",", ":")).encode()
        header += b" " * ((-len(header)) % 8)
        path.write_bytes(len(header).to_bytes(8, "little") + header + raw[8 + header_size:])
        reloaded = load_file(str(path))
        assert state.keys() == reloaded.keys()
        assert all(torch.equal(value, reloaded[key]) and value.dtype == reloaded[key].dtype for key, value in state.items())
        exported = MechanismNN().eval()
        exported.load_state_dict(reloaded, strict=True)
        with torch.inference_mode():
            before, after = original(targets), exported(targets)
        assert torch.equal(before, after)
        models[role] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
                        "source_file": name, "source_sha256": source_hash, "variant": metadata["variant"], "state_epoch": int(metadata["state_epoch"]),
                        "parameters": sum(value.numel() for value in state.values()), "tensor_count": len(state),
                        "export_checks": {"exact_tensor_equality": True, "inference_cases": len(targets), "max_absolute_difference": float((before - after).abs().max())}}
        print(f"{role}: {path.stat().st_size} bytes; exact parameters and inference parity.")
    profile = {"version": "0.1.0a2", "license": "Apache-2.0", "format": "safetensors",
               "download_base": "https://github.com/Mechanismo-AI/mechanism-generator/releases/download/v0.1.0a2",
               "export_verification": {"device": "cpu", "torch": str(torch.__version__), "numpy": str(np.__version__), "seed": 9142026, "dtype": "float32"},
               "models": models}
    (args.output_directory / "models.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    (args.output_directory / "SHA256SUMS.txt").write_text(''.join(f"{item['sha256']}  {item['file']}\n" for item in models.values()), encoding="utf-8")


if __name__ == "__main__":
    main()
