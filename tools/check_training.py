"""Run two small four-stage chains and check state reproducibility and learning.

Uses the installed package (or an explicitly configured source PYTHONPATH).
This does not assert model quality or reproduce the full historical weights.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys


def equal(left, right):
    import torch
    if isinstance(left, torch.Tensor):
        return isinstance(right, torch.Tensor) and left.dtype == right.dtype and torch.equal(left, right)
    if isinstance(left, dict):
        return isinstance(right, dict) and left.keys() == right.keys() and all(equal(left[k], right[k]) for k in left)
    if isinstance(left, (tuple, list)):
        return isinstance(right, type(left)) and len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    if isinstance(left, float) and math.isnan(left):
        return isinstance(right, float) and math.isnan(right)
    return left == right


def check(output):
    from mechanism_generator.training.cli import STAGES, recipes
    from mechanism_generator.training.state import restricted_load, model_tensor_sha256
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    for name in ('first', 'second'):
        subprocess.run([sys.executable, '-m', 'mechanism_generator.training', 'chain',
                        '--preset', 'smoke', '--output', str(output/name)], env=env, check=True)
    summaries = [json.loads((output/name/'training-summary.json').read_text()) for name in ('first','second')]
    results = []
    for index, stage in enumerate(STAGES):
        checkpoints = [next((output/name/stage/recipes()[stage]['variant']).glob('*/terminal_state.pth'))
                       for name in ('first', 'second')]
        states = [restricted_load(path, map_location='cpu') for path in checkpoints]
        # Timestamp and artifact locations do not affect training. Safetensors
        # container metadata ordering can change a file hash without changing tensors.
        excluded = {'created_at', 'teacher_model_source', 'teacher_model_sha256'}
        numerical = [{k:v for k,v in state.items() if k not in excluded} for state in states]
        progressed = []
        changed = []
        for run_index, path in enumerate(checkpoints):
            with (path.parent/'epoch_metrics.csv').open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            progressed.append({int(row['epoch']) for row in rows} == {1, 2}
                              and any(float(row['grad_norm_max']) > 0 for row in rows))
            changed.append(any(model_tensor_sha256(restricted_load(candidate, map_location='cpu')['model_state_dict']) !=
                               summaries[run_index]['stages'][index]['initial_model_tensor_sha256']
                               for candidate in path.parent.glob('*.pth')))
        row = {'stage': stage, 'all_training_state_equal': equal(*numerical),
               'terminal_completed_epoch_index': states[0]['epoch'],
               'terminal_state_epoch': states[0]['state_epoch'],
               'two_epochs_exercised_with_nonzero_gradients': all(progressed),
               'changed_model_checkpoint_saved': all(changed),
               'terminal_model_changed': all(s['stages'][index]['initial_model_tensor_sha256'] !=
                                             s['stages'][index]['terminal_model_tensor_sha256'] for s in summaries),
               'terminal_model_tensor_sha256': summaries[0]['stages'][index]['terminal_model_tensor_sha256'],
               'trainer_sha256': summaries[0]['stages'][index]['trainer_sha256']}
        row['passed'] = row['all_training_state_equal'] and all(changed) and all(progressed)
        results.append(row)
    report = {'purpose': 'Two-epoch CPU setup and numerical reproducibility check; not a quality benchmark',
              'passed': all(row['passed'] for row in results), 'stages': results,
              'environment': summaries[0]['environment'], 'training_source_sha256': summaries[0]['training_source_sha256'],
              'seed': 101, 'epochs': 2, 'training_targets_per_stage': 64, 'development_targets': 32,
              'threads': 1, 'compared_state_exclusions': sorted(excluded)}
    (output/'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New short directory')
    args = parser.parse_args()
    report = check(args.output.resolve())
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
