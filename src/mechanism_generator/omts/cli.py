"""OMTS command-line interface; validation and adaptation share the same checks."""

import argparse
import json
import sys

from .adapter import capabilities, write_plan
from .validation import DocumentError, load_document, require_valid


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate OMTS drafts and prepare external R2.5c runs.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Check schema and cross-field semantics (no solver)")
    validate.add_argument("document")
    adapt = commands.add_parser("adapt", help="Prepare checked run files; does not run the solver")
    adapt.add_argument("document")
    adapt.add_argument("--output-dir", required=True, help="A new directory; existing paths are never overwritten")
    commands.add_parser("capabilities", help="Show the exact draft adapter capability profile")
    args = parser.parse_args(argv)
    try:
        if args.command == "capabilities":
            print(json.dumps(capabilities(), indent=2))
        else:
            data = load_document(args.document)
            if args.command == "validate":
                require_valid(data)
                print("VALID OMTS: schema and semantic checks passed. Solver support and feasibility are not evaluated.")
            else:
                path = write_plan(data, args.output_dir)
                print(f"PREPARED: {path} (not evaluated; requires the external research engine and weights)")
    except (DocumentError, OSError, RecursionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0
