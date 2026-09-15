"""Restricted local training state and portable, tensor-only model exports."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile


def capture_numpy_state():
    import numpy as np
    import torch
    name, keys, position, has_gauss, cached = np.random.get_state()
    return (name, torch.from_numpy(keys.astype(np.int64)), int(position), int(has_gauss), float(cached))


def restore_numpy_state(state):
    import numpy as np
    name, keys, position, has_gauss, cached = state
    np.random.set_state((name, keys.cpu().numpy().astype(np.uint32), position, has_gauss, cached))


def restricted_load(path, map_location=None):
    """Never enable unrestricted pickle or add reconstruction globals."""
    import torch
    path = Path(path)
    if path.suffix.lower() == '.safetensors':
        from safetensors import safe_open
        from safetensors.torch import load_file
        with safe_open(str(path), framework='pt', device='cpu') as handle:
            metadata = handle.metadata() or {}
        result = {'model_state_dict': load_file(str(path), device=str(map_location or 'cpu'))}
        if 'variant' in metadata:
            result['variant'] = metadata['variant']
        for key in ('state_epoch', 'epoch'):
            if key in metadata:
                result[key] = int(metadata[key])
        return result
    return torch.load(path, map_location=map_location, weights_only=True)


def model_tensor_sha256(state):
    """Hash names, dtypes, shapes and bytes, independent of archive metadata."""
    digest = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        item = tensor.detach().cpu().contiguous()
        digest.update(json.dumps([name, str(item.dtype), list(item.shape)], separators=(',', ':')).encode())
        digest.update(b'\n')
        digest.update(item.numpy().tobytes())
    return digest.hexdigest()


def export_weights(checkpoint, output):
    """Export only model tensors and narrowly allowlisted model metadata."""
    import torch
    from safetensors.torch import save_file
    payload = restricted_load(checkpoint, map_location='cpu')
    state = payload['model_state_dict']
    if not isinstance(state, dict) or not state:
        raise ValueError('Checkpoint must contain a model state dictionary')
    shapes = {f'layers.{i}.weight': (512, 6 if i == 0 else 512) for i in range(8)}
    shapes.update({f'layers.{i}.bias': (512,) for i in range(8)})
    shapes.update({'output_layer.weight': (8, 512), 'output_layer.bias': (8,)})
    if set(state) != set(shapes):
        raise ValueError('Unexpected model architecture')
    clean = {}
    for name, value in state.items():
        if not isinstance(value, torch.Tensor) or tuple(value.shape) != shapes[name] or value.dtype != torch.float32 or not torch.isfinite(value).all():
            raise ValueError('Model tensors must have the expected shape, dtype and finite values')
        clean[name] = value.detach().cpu().contiguous().clone()
    from importlib.resources import files
    variants = {v['variant'] for v in json.loads(files(__package__).joinpath('recipes.json').read_text())['stages'].values()}
    variant = payload.get('variant')
    if variant not in variants:
        raise ValueError('Unrecognized training variant')
    epoch = payload.get('state_epoch', payload.get('epoch'))
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ValueError('Invalid checkpoint epoch')
    metadata = {'variant': variant, 'state_epoch': str(epoch), 'license': 'Apache-2.0',
                'format': 'mechanism-generator-model-v1', 'model_tensor_sha256': model_tensor_sha256(clean)}
    destination = Path(output)
    if destination.suffix != '.safetensors':
        raise ValueError('Export path must end in .safetensors')
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.model-', dir=destination.parent)
    os.close(descriptor)
    try:
        save_file(clean, temporary, metadata=metadata)
        # safetensors metadata maps can serialize in a different order on each
        # call. Canonicalize only the JSON header so equal tensors and metadata
        # produce identical portable files; preserve every tensor byte/offset.
        raw = Path(temporary).read_bytes()
        header_size = int.from_bytes(raw[:8], 'little')
        header = json.dumps(json.loads(raw[8:8 + header_size]), sort_keys=True,
                            separators=(',', ':')).encode()
        header += b' ' * ((-len(header)) % 8)
        Path(temporary).write_bytes(len(header).to_bytes(8, 'little') + header + raw[8 + header_size:])
        os.link(temporary, destination)  # Publish atomically without overwriting.
    finally:
        Path(temporary).unlink(missing_ok=True)
    return metadata
