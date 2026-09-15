"""Synthetic target triples for preserved training recipes.

These targets are generated locally without an external dataset. The fixed
development set was reused during research; it is not an untouched test set.
Hashes describe contiguous float32 tensor bytes, not a torch.save container.
"""
import hashlib
import os
from pathlib import Path
import tempfile

import torch


DEVELOPMENT_TENSOR_SHA256 = "4636ea89d5210676c17fe66cf385008ab043ae876c04fdbfea72ad423e911b7f"
DEVELOPMENT_SEED_OFFSET = 3001
STREAM_SEED_OFFSET = 500000
STREAM_SEED_STRIDE = 104729
VERIFIED_TORCH_VERSION = "2.13.0+cpu"


def _integer(value: int, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _generate(seed: int, count: int) -> torch.Tensor:
    _integer(seed, "seed")
    _integer(count, "count", 1)
    if seed > 2**64 - 1:
        raise ValueError("Derived seed exceeds the torch.Generator seed range")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    r = torch.rand(count, 6, generator=generator, dtype=torch.float32, device="cpu")
    return torch.stack((r[:, 0] * 8 - 7, r[:, 1] * 6 + 1,
                        r[:, 2] * 8 - 7, r[:, 3] * 6 + 1,
                        r[:, 4] * 8 - 7, r[:, 5] * 6 + 1), dim=1)


def generate_development_targets(seed: int = 101, count: int = 512) -> torch.Tensor:
    """Generate (count, 6) targets using a private CPU RNG seeded at seed+3001."""
    return _generate(_integer(seed, "seed") + DEVELOPMENT_SEED_OFFSET, count)


def generate_stream_targets(index: int, seed: int = 101, count: int = 2000) -> torch.Tensor:
    """Generate R2.4 stream index (zero-based), independent of global RNG state.

    Each coordinate pair lies in x=[-7, 1), y=[1, 7). The trainer's separate
    shuffle generator uses the derived stream seed plus one.
    """
    derived = _integer(seed, "seed") + STREAM_SEED_OFFSET + STREAM_SEED_STRIDE * _integer(index, "index")
    return _generate(derived, count)


def tensor_sha256(tensor: torch.Tensor) -> str:
    """Hash contiguous CPU tensor bytes, matching the historical target hash."""
    if not isinstance(tensor, torch.Tensor):
        raise ValueError("Expected a torch tensor")
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def _validate_targets(tensor: torch.Tensor) -> torch.Tensor:
    if not isinstance(tensor, torch.Tensor) or tensor.dtype != torch.float32 or tensor.ndim != 2 or tensor.shape[1] != 6 or tensor.shape[0] < 1:
        raise ValueError("Targets must be a nonempty float32 tensor with shape (count, 6)")
    if not bool(torch.isfinite(tensor).all()):
        raise ValueError("Targets must contain finite values")
    return tensor.detach().cpu().contiguous()


def write_targets(path: str | Path, tensor: torch.Tensor) -> Path:
    """Write a tensor-only .pt file without overwriting an existing file."""
    tensor = _validate_targets(tensor)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".targets-", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            torch.save(tensor, output)
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination.resolve()


def load_targets(path: str | Path) -> torch.Tensor:
    """Load only a finite float32 target tensor through PyTorch's safe loader."""
    return _validate_targets(torch.load(Path(path), map_location="cpu", weights_only=True))
