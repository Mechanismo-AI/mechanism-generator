"""Run the packaged hybrid solver with the verified public model set."""
import argparse
from pathlib import Path
import sys

from .models import verify


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--models-directory", type=Path, default=Path("models"))
    known, remaining = parser.parse_known_args(arguments)
    if any(item.split("=", 1)[0] in {"--balanced_model", "--path_model", "--transmission_model", "--engine_script", "--ground_link_mode"} for item in remaining):
        parser.error("Use --models-directory for verified weights; the public command always runs the packaged hybrid engine.")
    try:
        from . import r25c
    except ImportError as error:
        parser.exit(1, f"Install the engine dependencies with pip install '.[engine]': {error}\n")
    if "--help" in remaining or "-h" in remaining:
        print("Public engine option: --models-directory FOLDER (default: models)\n")
        r25c.build_parser().print_help()
        return 0
    try:
        paths = verify(known.models_directory)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    previous = sys.argv
    sys.argv = ["mechanism-generate", *remaining, *[item for role, path in paths.items() for item in (f"--{role}_model", str(path))]]
    try:
        return r25c.main()
    finally:
        sys.argv = previous
