"""OMTS command-line interface; validation and adaptation share the same checks."""

import argparse
import json
import sys

from .adapter import capabilities, write_plan
from .line_verify import LineVerificationError, solve_offsets, verify_line
from .timeline import compose_timeline, write_timeline
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
    propose = commands.add_parser("propose-offsets",
                                  help="Joint master-phase offset search over existing results (S5; proposal only)")
    propose.add_argument("plan_dir", help="A directory written by: omts adapt")
    propose.add_argument("--step-deg", type=float, default=1.0,
                         help="Offset grid step in degrees (default: 1.0)")
    propose.add_argument("--top", type=int, default=5,
                         help="Number of recommended offset assignments to report (default: 5)")
    timeline = commands.add_parser("timeline",
                                   help="Write the composed timeline artifact (data-only; the verdict is unchanged)")
    timeline.add_argument("plan_dir", help="A directory written by: omts adapt")
    timeline.add_argument("--steps", type=int, default=720,
                          help="Master-phase samples per cycle (default: 720; sampled, not certified)")
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
        elif args.command == "propose-offsets":
            proposal = solve_offsets(args.plan_dir, step_deg=args.step_deg, top=args.top)
            print(f"OFFSETS PROPOSAL: {proposal['status']}; best {proposal['best_passing_count']} passing "
                  f"of {proposal['combination_count']} combinations across {proposal['assignments_with_best_count']} "
                  f"assignment(s) at {proposal['step_deg']:g} deg steps (offsets_proposal.json written)")
            for entry in proposal.get("recommendations", []):
                offsets = ", ".join(f"{task}: {value:g}" for task, value in entry["offsets"].items())
                print(f"  {entry['rank']}. {{{offsets}}} -> {entry['passing_combinations']} passing, "
                      f"margin {entry['margin_deg']:g} deg")
            if proposal.get("status") == "no_candidates":
                print("  (no candidate combinations to search)")
            print("Proposal only: declare the chosen offsets in the document's synchronization.applied_offsets, "
                  "then re-validate, re-adapt, and re-verify.")
        elif args.command == "timeline":
            artifact = compose_timeline(args.plan_dir, steps=args.steps)
            path = write_timeline(args.plan_dir, artifact)
            candidates = sum(len(entry["candidates"]) for entry in artifact["tasks"].values())
            print(f"TIMELINE WRITTEN: {path} ({len(artifact['tasks'])} tasks, {candidates} "
                  f"candidates, {artifact['steps']} samples; data-only, never gates the verdict)")
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
