"""Prepare or validate contributions without transmitting anything."""
import argparse
import csv
import hashlib
from pathlib import Path
import sys

from .bundle import prepare_bundle, read_json, validate_bundle


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and review local community contributions; no automatic uploads.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Prepare an offline review page from an R2.5c run")
    prepare.add_argument("run_directory", type=Path)
    validate = commands.add_parser("validate", help="Check bundle structure and print its file fingerprint")
    validate.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            page = prepare_bundle(args.run_directory)
            print(f"Local review page: {page}")
            print("Open this page to choose what to share. Nothing has been uploaded.")
        else:
            bundle = read_json(args.file)
            validate_bundle(bundle)
            print(f"Valid {bundle['kind']} contribution; scientific results and sharing rights remain unreviewed.")
            print(f"SHA-256: {hashlib.sha256(args.file.read_bytes()).hexdigest()}")
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        print(f"Contribution preparation or validation failed ({type(exc).__name__}). Check the run files and schema; nothing was uploaded.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
