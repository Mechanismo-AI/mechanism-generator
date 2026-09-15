"""Run the published research training recipes or a small setup check."""
from __future__ import annotations

import argparse
from importlib.resources import files
import json
import os
from pathlib import Path
import subprocess
import sys
import time

STAGES = ('r2', 'r22', 'r23a', 'r24')


def recipes():
    return json.loads(files(__package__).joinpath('recipes.json').read_text(encoding='utf-8'))['stages']


def _replace(arguments, key, value):
    if key in arguments:
        index = arguments.index(key)
        arguments[index + 1] = str(value)
    else:
        arguments.extend([key, str(value)])


def stage_arguments(stage, preset, output, development, teacher=None, initialize=None,
                    *, seed=101, device='cpu', epochs=None, points=None):
    args = list(recipes()[stage]['arguments'])
    for key, value in (('--seed', seed), ('--device', device), ('--checkpoint_root', output),
                       ('--run_label', preset)):
        _replace(args, key, value)
    if preset == 'smoke':
        for key, value in (('--num_epochs', 2), ('--num_points', 64),
                           ('--validation_samples', 32), ('--validation_batch_size', 32)):
            _replace(args, key, value)
    if epochs is not None:
        _replace(args, '--num_epochs', epochs)
    if points is not None:
        _replace(args, '--num_points', points)
    if stage != 'r2':
        if teacher is None or initialize is None:
            raise ValueError(f'{stage} requires teacher and initialization weights')
        args.extend(['--teacher_model', str(teacher), '--initialize_from_model', str(initialize),
                     '--validation_targets_file', str(development)])
    return args


def _run_stage(stage, args, output, preset):
    from .assets import sha256
    from .state import export_weights, restricted_load, model_tensor_sha256
    start = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with (output / 'training.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-m', f'mechanism_generator.training.{stage}', *args],
                                stdout=log, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        raise RuntimeError(f'{stage} failed; see {output / "training.log"}')
    if '[FATAL]' in (output / 'training.log').read_text(encoding='utf-8', errors='replace'):
        raise RuntimeError(f'{stage} stopped after a fatal training condition; see {output / "training.log"}')
    runs = list((output / recipes()[stage]['variant']).iterdir())
    if len(runs) != 1:
        raise RuntimeError('Expected one training run directory')
    run = runs[0]
    terminal = restricted_load(run / 'terminal_state.pth', map_location='cpu')
    initial = restricted_load(run / 'initial_state.pth', map_location='cpu')
    selected = run / recipes()[stage]['selection']
    fallback = not selected.is_file()
    if fallback:
        if preset != 'smoke':
            raise RuntimeError(f'{stage} produced no required {selected.name}; inspect local training logs')
        selected = run / 'terminal_state.pth'
    exported = output / 'selected.safetensors'
    metadata = export_weights(selected, exported)
    path_flags = {'--checkpoint_root', '--validation_targets_file', '--teacher_model', '--initialize_from_model'}
    effective = {}
    dependencies = {}
    index = 0
    while index < len(args):
        key = args[index]
        value = args[index+1] if index+1 < len(args) and not args[index+1].startswith('--') else True
        index += 1 if value is True else 2
        if key in ('--teacher_model', '--initialize_from_model'):
            dependencies[key[2:]] = sha256(Path(value))
        if key not in path_flags:
            effective[key[2:]] = value
    summary = {'stage': stage, 'status': 'completed', 'preset': preset,
               'effective_arguments': effective, 'input_weight_sha256': dependencies,
               'completed_epoch': terminal['epoch'], 'state_epoch': terminal['state_epoch'],
               'elapsed_seconds': time.perf_counter()-start,
               'selected_checkpoint': selected.name, 'smoke_terminal_fallback': fallback,
               'export': exported.name, 'export_sha256': sha256(exported),
               'initial_model_tensor_sha256': model_tensor_sha256(initial['model_state_dict']),
               'terminal_model_tensor_sha256': model_tensor_sha256(terminal['model_state_dict']),
               'export_metadata': metadata, 'trainer_sha256': sha256(Path(__file__).with_name(stage+'.py'))}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(f'{stage}: completed; exported {selected.name} to {exported}', flush=True)
    return exported, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    assets = commands.add_parser('assets', help='Explicitly download or verify clean historical starting weights')
    assets.add_argument('operation', choices=('download', 'verify'))
    assets.add_argument('--directory', type=Path, default=Path('training-models'))
    data = commands.add_parser('data', help='Regenerate synthetic development data or one R2.4 stream')
    data.add_argument('--output', type=Path, required=True)
    data.add_argument('--stream-index', type=int)
    data.add_argument('--seed', type=int, default=101)
    data.add_argument('--count', type=int)
    export = commands.add_parser('export', help='Export a local training checkpoint as portable weights')
    export.add_argument('checkpoint', type=Path)
    export.add_argument('--output', type=Path, required=True)
    for name in ('run', 'chain'):
        command = commands.add_parser(name, help='Run one stage' if name=='run' else 'Run all four stages from random initialization')
        if name == 'run':
            command.add_argument('stage', choices=STAGES)
            command.add_argument('--assets-directory', type=Path)
            command.add_argument('--teacher', type=Path)
            command.add_argument('--initialize-from', type=Path)
        command.add_argument('--preset', choices=('smoke', 'historical'), default='smoke')
        command.add_argument('--output', type=Path, required=True, help='New output directory; use a short path on Windows')
        command.add_argument('--seed', type=int, default=101)
        command.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
        command.add_argument('--epochs', type=int, help='Override the recipe, marking this as a custom run')
        command.add_argument('--points', type=int, help='Override training target count')
    args = parser.parse_args(argv)
    try:
        if args.action == 'assets':
            from .assets import download, verify
            paths = (download if args.operation=='download' else verify)(args.directory)
            print(f'Verified {len(paths)} Apache-2.0 training dependencies.')
            return 0
        if args.action == 'export':
            from .state import export_weights
            export_weights(args.checkpoint, args.output)
            print(f'Exported portable model weights to {args.output}')
            return 0
        from .data import generate_development_targets, generate_stream_targets, write_targets, tensor_sha256
        if args.action == 'data':
            tensor = (generate_development_targets(seed=args.seed, count=512 if args.count is None else args.count) if args.stream_index is None
                      else generate_stream_targets(args.stream_index, seed=args.seed, count=2000 if args.count is None else args.count))
            write_targets(args.output, tensor)
            print(f'Wrote {len(tensor)} target triples; tensor SHA256 {tensor_sha256(tensor)}')
            return 0
        if args.epochs is not None and args.epochs < 1 or args.points is not None and args.points < 1:
            raise ValueError('Epochs and points must be positive')
        output = args.output.resolve()
        if output.exists():
            raise FileExistsError('Choose a new output directory')
        teacher = initialize = None
        if args.action == 'run' and args.stage == 'r2' and (args.teacher or args.initialize_from or args.assets_directory):
            raise ValueError('R2 starts from random initialization; dependency arguments are not supported')
        if args.action == 'run' and args.stage != 'r2':
            teacher, initialize = args.teacher, args.initialize_from
            if args.assets_directory:
                if teacher or initialize:
                    raise ValueError('Use assets-directory or explicit dependencies, not both')
                from .assets import verify
                dependencies = verify(args.assets_directory)
                teacher = dependencies['teacher']
                initialize = dependencies[{'r22':'teacher','r23a':'warmstart_r22','r24':'transmission'}[args.stage]]
            if teacher is None or initialize is None:
                raise ValueError('Supply assets-directory or both teacher and initialize-from')
            teacher, initialize = teacher.resolve(strict=True), initialize.resolve(strict=True)
        # A concurrent writer must not cause an existing run to be reused.
        output.mkdir(parents=True, exist_ok=False)
        development = output / 'development-targets.pt'
        tensor = generate_development_targets(seed=args.seed, count=32 if args.preset=='smoke' else 512)
        write_targets(development, tensor)
        import platform
        from importlib.metadata import version
        from .assets import sha256
        explicit_dependencies = args.action == 'run' and (args.teacher is not None or args.initialize_from is not None)
        report = {'preset': args.preset, 'custom': args.epochs is not None or args.points is not None or args.seed != 101 or args.device != 'cpu' or explicit_dependencies,
                  'seed': args.seed, 'device': args.device, 'threads': 1,
                  'environment': {'python': platform.python_version(), 'system': platform.system(),
                                  **{name: version(name) for name in ('torch','numpy','pandas','matplotlib','safetensors')}},
                  'training_source_sha256': {name: sha256(Path(__file__).with_name(name)) for name in
                                            ('cli.py','state.py','data.py','recipes.json')},
                  'development_count': len(tensor), 'development_tensor_sha256': tensor_sha256(tensor),
                  'stages': [], 'status': 'running'}
        report_path = output / 'training-summary.json'
        def save():
            report_path.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        save()
        for stage in STAGES if args.action == 'chain' else (args.stage,):
            stage_output = output / stage
            arguments = stage_arguments(stage, args.preset, stage_output, development, teacher, initialize,
                                        seed=args.seed, device=args.device, epochs=args.epochs, points=args.points)
            try:
                selected, summary = _run_stage(stage, arguments, stage_output, args.preset)
            except Exception:
                report['status'] = 'failed'; report['failed_stage'] = stage; save()
                raise
            report['stages'].append(summary); save()
            if args.action == 'chain':
                if stage == 'r2':
                    teacher = selected
                initialize = selected
        report['status'] = 'completed'; save()
        print(f'Training report: {report_path}')
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f'Training operation failed: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
