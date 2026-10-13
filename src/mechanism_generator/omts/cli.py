"""OMTS command-line interface; validation and adaptation share the same checks."""

import argparse
import json
import sys

from .adapter import capabilities, write_plan
from .line_verify import LineVerificationError, verify_line
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
    verify = commands.add_parser("verify-line", help="Verify a prepared line against achieved per-task results")
    verify.add_argument("plan_dir", help="A directory written by: omts adapt")
    verify.add_argument("--probe-anchors", action="store_true",
                        help="Diagnostic sweep: report per-task master-phase offsets that would satisfy every hard constraint (the verdict is unchanged)")
    verify.add_argument("--probe-step-deg", type=float, default=1.0,
                        help="Offset step in degrees for --probe-anchors (default: 1.0)")
    args = parser.parse_args(argv)
    try:
        if args.command == "capabilities":
            print(json.dumps(capabilities(), indent=2))
        elif args.command == "verify-line":
            result = verify_line(args.plan_dir, probe=args.probe_anchors, probe_step_deg=args.probe_step_deg)
            print(f"LINE {result['status'].upper()}: combinations={result['combination_count']} passing={result['passing_combination_count']} (line_result.json written)")
            probe = result.get("anchor_probe")
            if probe is not None:
                if probe.get("status") == "skipped":
                    print("ANCHOR PROBE: skipped (no candidate combinations)")
                else:
                    print(f"ANCHOR PROBE (step {probe['step_deg']:g} deg; diagnostic, verdict unchanged):")
                    for entry in probe["tasks"]:
                        intervals = ", ".join(
                            f"[{item['from_deg']:g}..{item['to_deg']:g}] x{item['max_passing_combinations']}"
                            for item in entry["feasible_intervals_deg"]
                        ) or "none"
                        print(f"  {entry['task']}: best {entry['best_passing_combinations']} passing combos; feasible offsets: {intervals}")
        else:
            data = load_document(args.document)
            if args.command == "validate":
                require_valid(data)
                print("VALID OMTS: schema and semantic checks passed. Solver support and feasibility are not evaluated.")
            else:
                path = write_plan(data, args.output_dir)
                print(f"PREPARED: {path} (not evaluated; run with the installed engine and downloaded weights)")
    except (DocumentError, LineVerificationError, OSError, RecursionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0
