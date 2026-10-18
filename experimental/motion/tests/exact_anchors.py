"""Runtime-fingerprinted exact anchor registry for the motion solver.

MOTION_TEST_EXACT=1 compares live optimizer trajectories bit-for-bit
against recorded anchors. Bit-level values only mean something relative
to the runtime that produced them: the last-ulp path through Python,
torch and numpy changes with the interpreter version, the torch build
and the CPU. Anchors therefore live in evidence/runtime-anchors/ as one
JSON file per runtime, named by fingerprint (python version, torch
version, torch build digest, numpy version, CPU model).

Exact mode (tests/test_release.py) loads the current runtime's anchor
set and fails closed on an unknown runtime (the regeneration command is
printed) or a corrupt anchor file (distinct message). The tolerant
outcome checks remain the portable gate; exact mode is an instrument,
never the gate.

Anchors are recorded data: --regen writes only the current runtime's
own file, refuses to overwrite without --replace, and refuses a dirty
tree (modified tracked files) because uncommitted changes would make
the recorded fingerprint a lie. Untracked files are allowed so this
script can be copied into older checkouts for per-PR boundary drift
measurements; use --output PATH there to write a comparison artifact
outside the registry.
"""
import argparse, hashlib, json, os, platform, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
if os.environ.get('MOTION_TEST_INSTALLED') != '1':
    sys.path.insert(0, str(ROOT / 'src'))
import torch
import numpy as np
from mechanism_motion import solve

torch.set_num_threads(1)
FIXTURES = ROOT / 'tests/fixtures'
REGISTRY = ROOT / 'evidence/runtime-anchors'


def _cpu_model():
    """CPU model string from /proc/cpuinfo, platform machine as fallback."""
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.machine() or 'unknown'


def _torch_build_digest():
    """Cheap digest of the torch build/config beyond the version string."""
    parts = [str(torch.__version__)]
    git_version = getattr(torch.version, 'git_version', None)
    if git_version is not None:
        parts.append(str(git_version))
    if hasattr(torch, '__config__') and hasattr(torch.__config__, 'show'):
        parts.append(torch.__config__.show())
    return hashlib.sha256('|'.join(parts).encode('utf-8')).hexdigest()[:12]


def fingerprint():
    """Full fingerprint fields of the current runtime."""
    return {
        'python': platform.python_version(),
        'torch': str(torch.__version__),
        'torch_build_digest': _torch_build_digest(),
        'numpy': str(np.__version__),
        'cpu_model': _cpu_model(),
    }


def fingerprint_slug(fields=None):
    """Filename-safe slug built from the fingerprint fields."""
    if fields is None:
        fields = fingerprint()
    raw = '-'.join([
        'py' + fields['python'],
        'torch' + fields['torch'],
        'b' + fields['torch_build_digest'],
        'numpy' + fields['numpy'],
        fields['cpu_model'],
    ])
    return ''.join(character if character.isalnum() else '-' for character in raw)


def anchor_path(fields=None):
    """Registry file path for a fingerprint."""
    return REGISTRY / (fingerprint_slug(fields) + '.json')


def load_current():
    """Load the current runtime's anchor set; fail closed both ways."""
    fields = fingerprint()
    path = anchor_path(fields)
    if not path.exists():
        raise FileNotFoundError(
            'No exact anchor set is recorded for this runtime ('
            + path.name + ').\n'
            'Exact mode fails closed on unknown runtimes. Record this runtime '
            'first (from experimental/motion, on a clean tree):\n'
            '    python tests/exact_anchors.py --regen\n'
            'The anchor set then lands through a reviewed pull request.')
    try:
        payload = json.loads(path.read_text())
    except ValueError as error:
        raise ValueError(
            'The anchor file ' + path.name + ' is corrupt (' + str(error)
            + '). Exact mode fails closed; confirm the corruption is not a '
            'finding before re-recording with python tests/exact_anchors.py '
            '--regen --replace.') from error
    if not isinstance(payload.get('cases'), dict) \
            or payload.get('fingerprint_slug') != path.stem \
            or payload.get('fingerprint') != fields:
        raise ValueError(
            'The anchor file ' + path.name + ' does not match the registry '
            'format or this runtime. Exact mode fails closed; treat as a '
            'finding, do not silently re-record.')
    return payload


def _git(arguments):
    return subprocess.run(['git'] + arguments, cwd=REPO, capture_output=True,
                          text=True, check=True).stdout


def _require_clean_tree():
    """Refuse to record anchors on a tree with modified tracked files."""
    try:
        status = _git(['status', '--porcelain'])
    except (subprocess.CalledProcessError, OSError) as error:
        raise SystemExit('Could not verify a clean tree with git ('
                         + str(error) + '); anchors are never recorded '
                         'without that check.')
    dirty = [line for line in status.splitlines()
             if line.strip() and not line.startswith('??')]
    if dirty:
        raise SystemExit(
            'Refusing to record anchors on a dirty tree (uncommitted changes '
            'would make the recorded fingerprint a lie). Modified tracked '
            'files:\n' + '\n'.join(dirty))


def _collect():
    """Run every frozen case under both policies and record exact data."""
    cases = {}
    for path in sorted(FIXTURES.glob('case-*.json')):
        fixture = json.loads(path.read_text())
        entry = {}
        chooser_result = None
        for chooser in (True, False):
            result = solve(fixture['input'], fixture['seed'],
                           use_chooser=chooser)
            if chooser:
                chooser_result = result
            entry['chooser' if chooser else 'baseline'] = {
                'qualified': result['qualified'],
                'objective_evaluations': result['objective_evaluations'],
                'runs': [{'evaluations': run['evaluations'],
                          'raw': run['raw'],
                          'metrics': run['metrics']}
                         for run in result['runs']],
            }
        entry['selected_label'] = chooser_result['selected_label']
        entry['schema_version'] = chooser_result.get('schema_version')
        entry['pool'] = [{'initial_raw': item['initial_raw'],
                          'before': item['before'],
                          'ranking_prediction': item['ranking_prediction']}
                         for item in chooser_result['pool']]
        cases[str(fixture['case'])] = entry
    return cases


def _payload():
    fields = fingerprint()
    payload = {
        'fingerprint': fields,
        'fingerprint_slug': fingerprint_slug(fields),
        'generated_utc': datetime.now(timezone.utc).isoformat(
            timespec='seconds'),
        'git_commit': _git(['rev-parse', 'HEAD']).strip(),
    }
    payload['cases'] = _collect()
    return payload


def _write(path, payload, replace):
    if path.exists() and not replace:
        raise SystemExit(
            'Refusing to overwrite ' + str(path) + '; pass --replace if that '
            'is intended (anchors are recorded data).')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(payload, indent=2) + '\n')
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Runtime-fingerprinted exact anchor registry for '
                    'MOTION_TEST_EXACT=1.')
    parser.add_argument('--regen', action='store_true',
                        help='collect and record the current runtime '
                             'anchor set')
    parser.add_argument('--output', metavar='PATH',
                        help='write a comparison artifact to PATH instead '
                             'of the registry')
    parser.add_argument('--replace', action='store_true',
                        help='allow overwriting an existing output file')
    arguments = parser.parse_args(argv)
    fields = fingerprint()
    path = anchor_path(fields)
    if not (arguments.regen or arguments.output):
        print('runtime fingerprint: ' + fingerprint_slug(fields))
        for key in ('python', 'torch', 'torch_build_digest', 'numpy',
                    'cpu_model'):
            print('  ' + key + ': ' + str(fields[key]))
        print('anchor set: ' + str(path))
        print('status: ' + ('recorded' if path.exists() else 'NOT RECORDED'))
        print('exact mode will ' + ('compare against this set.'
              if path.exists()
              else 'fail closed until it is recorded.'))
        try:
            print('git commit: ' + _git(['rev-parse', 'HEAD']).strip())
        except (subprocess.CalledProcessError, OSError):
            print('git commit: unavailable')
        print('record it with: python tests/exact_anchors.py --regen')
        return 0
    _require_clean_tree()
    payload = _payload()
    target = Path(arguments.output) if arguments.output else path
    _write(target, payload, arguments.replace)
    print('wrote ' + str(target) + ' (' + str(len(payload['cases']))
          + ' cases, runtime ' + payload['fingerprint_slug'] + ')')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
