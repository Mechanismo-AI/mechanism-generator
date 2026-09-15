#!/usr/bin/env python3
"""
V5.3-R2.5c Hybrid Ground-Link Portfolio Search

Purpose
-------
Run the fixed-ground and variable-ground R2.5b searches as complementary
portfolio branches, then continue strong fixed-ground candidates into the
variable-L1 design space.

For every target triple the portfolio performs:

    fixed L1 search
        + independent variable L1 search
        + trust-region variable continuation from strong fixed candidates
        + optional full-range release continuation
        -> one shared path-quality reference
        -> combined qualification, deduplication, Pareto ranking, and export

The fixed candidates are retained unchanged in the final pool. Therefore the
hybrid search cannot lose a useful fixed-L1 mechanism merely because a
nonconvex variable-L1 refinement enters a different basin.

This script is intentionally a wrapper around
the bundled ``r25b`` module. Public packaging changes are documented in
``docs/engine.md``; numerical refinement functions retain their research lineage.

This is a kinematic research/design aid. It is not structural, fatigue,
controls, sanitation, collision, or machinery-safety certification.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch


VARIANT = "V5.3-R2.5c_HybridGroundLinkPortfolio-public-alpha"
PARENT_VARIANT = "V5.3-R2.5b_RobustTransmissionAndCompactness"
SCHEMA_VERSION = 1


from . import r25b as ENGINE
from .provenance import set_run_root

ENGINE_PATH = Path(ENGINE.__file__).resolve()
ENGINE_VARIANT = str(getattr(ENGINE, "VARIANT", "unknown"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = ENGINE.build_parser()
    parser.prog = Path(__file__).name
    parser.description = (
        f"{VARIANT}: combine fixed-L1, variable-L1, and fixed-to-variable "
        "continuation searches into one qualified portfolio"
    )
    parser.add_argument(
        "--no_contribution_bundle", action="store_true",
        help="Skip local contribution bundle creation (bundles never upload automatically)",
    )
    parser.add_argument(
        "--portfolio_fixed_seed_count",
        type=int,
        default=3,
        help="Number of diverse fixed-L1 candidates used to seed trust-region continuation",
    )
    parser.add_argument(
        "--portfolio_bridge_profile_matrix",
        choices=("paired", "cross"),
        default="paired",
        help="Use each fixed candidate's profile or retry it under all three profiles",
    )
    parser.add_argument(
        "--portfolio_bridge_perturbations",
        type=int,
        default=0,
        help="Additional perturbations around each fixed-to-variable bridge seed",
    )
    parser.add_argument(
        "--portfolio_bridge_parameter_noise",
        type=float,
        default=0.08,
    )
    parser.add_argument(
        "--portfolio_bridge_phase_noise_deg",
        type=float,
        default=2.0,
    )
    parser.add_argument(
        "--portfolio_l1_trust_fraction",
        type=float,
        default=0.25,
        help="Initial bridge range is fixed L1 times (1 +/- this fraction)",
    )
    parser.add_argument("--portfolio_bridge_accuracy_steps", type=int, default=30)
    parser.add_argument("--portfolio_bridge_tradeoff_steps", type=int, default=60)
    parser.add_argument("--portfolio_bridge_lbfgs_steps", type=int, default=15)
    parser.add_argument(
        "--portfolio_release_seed_count",
        type=int,
        default=3,
        help="Number of trust-region candidates released into the full variable-L1 range",
    )
    parser.add_argument(
        "--portfolio_skip_release",
        action="store_true",
        help="Skip the full-range release continuation after the trust-region bridge",
    )
    parser.add_argument("--portfolio_release_accuracy_steps", type=int, default=20)
    parser.add_argument("--portfolio_release_tradeoff_steps", type=int, default=50)
    parser.add_argument("--portfolio_release_lbfgs_steps", type=int, default=12)
    parser.add_argument(
        "--portfolio_guarantee_fixed_count",
        type=int,
        default=1,
        help="Reserve up to this many eligible fixed-L1 representatives in the selected artifacts",
    )
    parser.add_argument(
        "--portfolio_stage_top_k",
        type=int,
        default=3,
        help="Number of stage-level champions written for fixed, variable, and bridge branches",
    )

    # Both modes always run. Keep the inherited argument accepted for backward
    # compatibility, but make its portfolio behavior explicit in help output.
    for action in parser._actions:
        if action.dest == "ground_link_mode":
            action.help = "Ignored by R2.5c; both fixed and optimize branches always run"
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    ENGINE.validate_args(parser, args)
    integer_nonnegative = (
        args.portfolio_fixed_seed_count,
        args.portfolio_bridge_perturbations,
        args.portfolio_release_seed_count,
        args.portfolio_guarantee_fixed_count,
    )
    if any(value < 0 for value in integer_nonnegative):
        parser.error("Portfolio counts must be non-negative")
    if args.portfolio_stage_top_k < 1:
        parser.error("--portfolio_stage_top_k must be positive")
    if not (0.0 < args.portfolio_l1_trust_fraction < 1.0):
        parser.error("--portfolio_l1_trust_fraction must be in (0,1)")
    if args.portfolio_bridge_parameter_noise < 0 or args.portfolio_bridge_phase_noise_deg < 0:
        parser.error("Portfolio perturbation magnitudes must be non-negative")
    step_values = (
        args.portfolio_bridge_accuracy_steps,
        args.portfolio_bridge_tradeoff_steps,
        args.portfolio_bridge_lbfgs_steps,
        args.portfolio_release_accuracy_steps,
        args.portfolio_release_tradeoff_steps,
        args.portfolio_release_lbfgs_steps,
    )
    if any(value < 0 for value in step_values):
        parser.error("Portfolio optimization step counts must be non-negative")
    if args.allow_unqualified_fallback:
        parser.error("Unqualified fallback is disabled in the public alpha; inspect all_candidates.csv instead")



def set_candidate_origin(
    candidate: Dict[str, Any],
    origin: str,
    parent_id: Optional[str] = None,
    lineage: Optional[str] = None,
) -> None:
    candidate["portfolio_origin"] = origin
    candidate["portfolio_parent_candidate_id"] = parent_id or ""
    candidate["portfolio_lineage"] = lineage or origin


def prefix_starts(
    starts: Sequence[Any],
    prefix: str,
    lineage_by_id: Dict[str, Dict[str, str]],
) -> List[Any]:
    renamed: List[Any] = []
    for index, start in enumerate(starts, start=1):
        original_id = str(start.candidate_id)
        start.candidate_id = f"{prefix}_{index:03d}"
        lineage_by_id[start.candidate_id] = {
            "origin": prefix,
            "parent_candidate_id": "",
            "lineage": f"{prefix}:{original_id}",
        }
        renamed.append(start)
    return renamed


def run_acquisitions(
    starts: Sequence[Any],
    target: torch.Tensor,
    stage_args: argparse.Namespace,
    stage_label: str,
) -> List[Dict[str, Any]]:
    acquisitions: List[Dict[str, Any]] = []
    if not starts:
        return acquisitions
    print(f"[{stage_label}] Stage A path acquisition ({len(starts)} starts)")
    for number, start in enumerate(starts, start=1):
        began = time.time()
        print(
            f"  [A {number:02d}/{len(starts):02d}] {start.candidate_id} "
            f"proposal={start.model_role} profile={start.profile} "
            f"branch={start.branch_sign:+.0f} perturb={start.perturbation_index}"
        )
        acquired = ENGINE.acquire_start_path(start, target, stage_args)
        acquired["acquisition_runtime_seconds"] = time.time() - began
        acquisitions.append(acquired)
        print(
            f"      mean={acquired['acquired_mean_error']:.6f} "
            f"max={acquired['acquired_max_error']:.6f} "
            f"target_mu_min={acquired['acquired_target_angle_min_deg']:.2f}deg "
            f"global_mu_min={acquired['acquired_global_angle_min_deg']:.2f}deg "
            f"physical={acquired['acquired_physical']}"
        )
    return acquisitions


def run_tradeoff(
    acquisitions: Sequence[Dict[str, Any]],
    shared_reference: Dict[str, Any],
    target: torch.Tensor,
    stage_args: argparse.Namespace,
    output_dir: Path,
    stage_label: str,
    lineage_by_id: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    evaluated: List[Dict[str, Any]] = []
    if not acquisitions:
        return evaluated
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{stage_label}] Stage B shared-budget refinement ({len(acquisitions)} starts)")
    for number, acquired in enumerate(acquisitions, start=1):
        start = acquired["start"]
        began = time.time()
        print(
            f"  [B {number:02d}/{len(acquisitions):02d}] {start.candidate_id} "
            f"proposal={start.model_role} profile={start.profile} "
            f"branch={start.branch_sign:+.0f} perturb={start.perturbation_index}"
        )
        optimized = ENGINE.optimize_start_with_shared_budget(
            acquired, shared_reference, target, stage_args, output_dir
        )
        candidate = ENGINE.evaluate_selected_candidate(optimized, target, stage_args)
        candidate["acquisition_runtime_seconds"] = acquired.get(
            "acquisition_runtime_seconds", 0.0
        )
        candidate["tradeoff_runtime_seconds"] = time.time() - began
        candidate["runtime_seconds"] = (
            candidate["acquisition_runtime_seconds"]
            + candidate["tradeoff_runtime_seconds"]
        )
        lineage = lineage_by_id.get(
            str(candidate["candidate_id"]),
            {"origin": stage_label, "parent_candidate_id": "", "lineage": stage_label},
        )
        set_candidate_origin(
            candidate,
            lineage["origin"],
            lineage.get("parent_candidate_id"),
            lineage.get("lineage"),
        )
        evaluated.append(candidate)
        print(
            f"      mean={candidate['mean_error']:.6f} "
            f"target_mu_min={candidate['target_angle_min_deg']:.2f}deg "
            f"global_mu_min={candidate['global_angle_min_deg']:.2f}deg "
            f"L1={candidate['l1']:.3f} maxL/D={candidate['max_link_ratio']:.2f} "
            f"sweepR/D={candidate['sweep_radius_ratio']:.2f} "
            f"physical={candidate['physical_feasible']}"
        )
    return evaluated


def candidate_pool_by_tier(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tiers = (
        [c for c in candidates if c.get("engineering_acceptable", False)],
        [c for c in candidates if c.get("selection_eligible", False)],
        [c for c in candidates if c.get("path_acceptable", False)],
        [c for c in candidates if c.get("physical_feasible", False)],
        list(candidates),
    )
    for tier in tiers:
        if tier:
            return tier
    return []


def choose_diverse_champions(
    candidates: Sequence[Dict[str, Any]],
    count: int,
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    if count <= 0:
        return []
    pool = candidate_pool_by_tier(candidates)
    if not pool:
        return []
    ordered: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def append(candidate: Dict[str, Any]) -> None:
        key = str(candidate["candidate_id"])
        if key not in seen:
            ordered.append(candidate)
            seen.add(key)

    metrics = (
        ("balanced_score", False),
        ("accuracy_score", False),
        ("target_angle_min_deg", True),
        ("global_angle_min_deg", True),
        ("compactness_score", False),
        ("assembly_margin_ratio", True),
    )
    for key, reverse in metrics:
        append(sorted(pool, key=lambda item: item[key], reverse=reverse)[0])
    for candidate in ENGINE.pareto_front(pool):
        append(candidate)
    for candidate in sorted(pool, key=lambda item: item["balanced_score"]):
        append(candidate)

    selected: List[Dict[str, Any]] = []
    for candidate in ordered:
        if any(ENGINE.candidates_are_duplicates(candidate, other, args) for other in selected):
            continue
        selected.append(candidate)
        if len(selected) >= count:
            break
    return selected


def make_bridge_args(
    args: argparse.Namespace,
    target: torch.Tensor,
    release: bool,
) -> argparse.Namespace:
    stage_args = copy.deepcopy(args)
    stage_args.ground_link_mode = "optimize"
    scale = float(ENGINE.target_design_space(target, args)["scale"].detach().item())
    fixed = float(args.fixed_ground_link_value)
    trust = float(args.portfolio_l1_trust_fraction)
    trust_lower = max(ENGINE.MIN_LEN, fixed * (1.0 - trust))
    trust_upper = max(trust_lower + 1e-6, fixed * (1.0 + trust))
    if release:
        # Full variable range, expanded when necessary so the fixed incumbent
        # and the trust-region continuation remain representable.
        broad_lower = scale * float(args.ground_link_min_ratio)
        broad_upper = scale * float(args.ground_link_max_ratio)
        lower = min(broad_lower, trust_lower)
        upper = max(broad_upper, trust_upper)
        stage_args.adam_accuracy_steps = args.portfolio_release_accuracy_steps
        stage_args.adam_tradeoff_steps = args.portfolio_release_tradeoff_steps
        stage_args.lbfgs_steps = args.portfolio_release_lbfgs_steps
    else:
        lower = trust_lower
        upper = trust_upper
        stage_args.adam_accuracy_steps = args.portfolio_bridge_accuracy_steps
        stage_args.adam_tradeoff_steps = args.portfolio_bridge_tradeoff_steps
        stage_args.lbfgs_steps = args.portfolio_bridge_lbfgs_steps
    stage_args.ground_link_min_ratio = lower / max(scale, 1e-12)
    stage_args.ground_link_max_ratio = upper / max(scale, 1e-12)
    return stage_args


def build_continuation_starts(
    seeds: Sequence[Dict[str, Any]],
    target: torch.Tensor,
    stage_args: argparse.Namespace,
    args: argparse.Namespace,
    prefix: str,
    target_index: int,
    lineage_by_id: Dict[str, Dict[str, str]],
    perturbations: int,
    parameter_noise: float,
    phase_noise_deg: float,
    cross_profiles: bool,
) -> List[Any]:
    starts: List[Any] = []
    counter = 0
    for seed_index, seed in enumerate(seeds, start=1):
        profile_names = tuple(ENGINE.PROFILES) if cross_profiles else (str(seed["profile"]),)
        params = torch.tensor(seed["parameters"], dtype=target.dtype, device=target.device)
        phases = torch.tensor(seed["phases_rad"], dtype=target.dtype, device=target.device)
        for profile_index, profile_name in enumerate(profile_names):
            raw_base = ENGINE.encode_refinement_variables(
                params, phases, target, args.phase_mode, stage_args
            )
            for perturbation_index in range(perturbations + 1):
                counter += 1
                raw = raw_base.detach().clone()
                if perturbation_index > 0:
                    generator = torch.Generator(device="cpu")
                    generator.manual_seed(
                        args.seed
                        + target_index * 1_000_000
                        + seed_index * 100_000
                        + profile_index * 10_000
                        + perturbation_index
                        + (700_000_000 if prefix.startswith("bridge_trust") else 800_000_000)
                    )
                    noise = torch.randn(
                        raw.shape, generator=generator, dtype=torch.float64
                    ).to(device=raw.device, dtype=raw.dtype)
                    raw[: ENGINE.MECHANISM_RAW_DIM] += (
                        float(parameter_noise) * noise[: ENGINE.MECHANISM_RAW_DIM]
                    )
                    phase_count = 3 if args.phase_mode == "unordered" else 4
                    raw[
                        ENGINE.MECHANISM_RAW_DIM : ENGINE.MECHANISM_RAW_DIM + phase_count
                    ] += math.radians(float(phase_noise_deg)) * noise[
                        ENGINE.MECHANISM_RAW_DIM : ENGINE.MECHANISM_RAW_DIM + phase_count
                    ]
                decoded_params, decoded_phases = ENGINE.decode_refinement_variables(
                    raw, target, args.phase_mode, stage_args
                )
                candidate_id = f"{prefix}_{counter:03d}"
                starts.append(
                    ENGINE.StartSpec(
                        candidate_id=candidate_id,
                        model_role=str(seed["model_role"]),
                        profile=profile_name,
                        checkpoint_variant=str(seed.get("checkpoint_variant", "unknown")),
                        checkpoint_epoch=seed.get("checkpoint_epoch"),
                        branch_sign=float(seed["branch_sign"]),
                        perturbation_index=perturbation_index,
                        raw_initial=raw,
                        initial_params=decoded_params.detach(),
                        initial_phases=decoded_phases.detach(),
                    )
                )
                lineage_by_id[candidate_id] = {
                    "origin": prefix,
                    "parent_candidate_id": str(seed["candidate_id"]),
                    "lineage": (
                        f"{prefix}<-{seed.get('portfolio_lineage', seed['candidate_id'])}"
                        f":profile={profile_name}:perturb={perturbation_index}"
                    ),
                }
    return starts


def ensure_fixed_representatives(
    selected: Sequence[Dict[str, Any]],
    fixed_candidates: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    final = [candidate for candidate in selected if candidate.get("selection_eligible", False)]
    eligible_fixed = [candidate for candidate in fixed_candidates if candidate.get("selection_eligible", False)]
    mandatory = choose_diverse_champions(
        eligible_fixed, args.portfolio_guarantee_fixed_count, args
    )
    for fixed in mandatory:
        if any(ENGINE.candidates_are_duplicates(fixed, item, args) for item in final):
            continue
        if len(final) < args.top_k:
            final.append(fixed)
            continue
        replace_index = next(
            (
                index
                for index in range(len(final) - 1, -1, -1)
                if final[index].get("portfolio_origin") != "fixed"
            ),
            None,
        )
        if replace_index is not None:
            final[replace_index] = fixed
    # Preserve the portfolio ordering while removing any new duplicates.
    deduped: List[Dict[str, Any]] = []
    for candidate in final:
        if any(ENGINE.candidates_are_duplicates(candidate, other, args) for other in deduped):
            continue
        deduped.append(candidate)
    return deduped[: args.top_k]


def summarize_origin(
    origin: str,
    candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    subset = [c for c in candidates if c.get("portfolio_origin") == origin]
    eligible = [c for c in subset if c.get("selection_eligible", False)]
    pool = eligible or [c for c in subset if c.get("path_acceptable", False)] or subset
    row: Dict[str, Any] = {
        "portfolio_origin": origin,
        "candidate_count": len(subset),
        "physical_count": sum(bool(c.get("physical_feasible", False)) for c in subset),
        "path_acceptable_count": sum(bool(c.get("path_acceptable", False)) for c in subset),
        "selection_eligible_count": sum(bool(c.get("selection_eligible", False)) for c in subset),
        "engineering_acceptable_count": sum(bool(c.get("engineering_acceptable", False)) for c in subset),
    }
    if pool:
        best_path = min(pool, key=lambda c: c["mean_error"])
        best_target = max(pool, key=lambda c: c["target_angle_min_deg"])
        best_global = max(pool, key=lambda c: c["global_angle_min_deg"])
        best_balanced = min(pool, key=lambda c: c["balanced_score"])
        row.update({
            "best_path_candidate_id": best_path["candidate_id"],
            "best_path_mean_error": best_path["mean_error"],
            "best_target_candidate_id": best_target["candidate_id"],
            "best_target_angle_min_deg": best_target["target_angle_min_deg"],
            "best_global_candidate_id": best_global["candidate_id"],
            "best_global_angle_min_deg": best_global["global_angle_min_deg"],
            "best_balanced_candidate_id": best_balanced["candidate_id"],
            "best_balanced_score": best_balanced["balanced_score"],
        })
    return row


def write_portfolio_summary(
    target_dir: Path,
    target_values: np.ndarray,
    candidates: Sequence[Dict[str, Any]],
    selected: Sequence[Dict[str, Any]],
    qualification: Dict[str, Any],
    origin_rows: Sequence[Dict[str, Any]],
    elapsed: float,
) -> None:
    lines = [
        f"# {VARIANT} Results",
        "",
        "## Target points",
        "",
        f"- T1: ({target_values[0]:.6g}, {target_values[1]:.6g})",
        f"- T2: ({target_values[2]:.6g}, {target_values[3]:.6g})",
        f"- T3: ({target_values[4]:.6g}, {target_values[5]:.6g})",
        "",
        f"Candidates evaluated: **{len(candidates)}**  ",
        f"Path acceptable: **{qualification.get('path_acceptable_count', 0)}**  ",
        f"Selection eligible: **{qualification.get('selection_eligible_count', 0)}**  ",
        f"Engineering acceptable: **{qualification.get('engineering_acceptable_count', 0)}**  ",
        f"Selected portfolio candidates: **{len(selected)}**  ",
        f"Runtime: **{elapsed:.2f} s**",
        "",
        "## Search branches",
        "",
        "| Origin | Candidates | Path OK | Selection OK | Engineering OK | Best path | Best target transmission | Best global minimum |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in origin_rows:
        lines.append(
            f"| {row['portfolio_origin']} | {row['candidate_count']} | "
            f"{row['path_acceptable_count']} | {row['selection_eligible_count']} | "
            f"{row['engineering_acceptable_count']} | "
            f"{row.get('best_path_mean_error', float('nan')):.6f} | "
            f"{row.get('best_target_angle_min_deg', float('nan')):.2f} deg | "
            f"{row.get('best_global_angle_min_deg', float('nan')):.2f} deg |"
        )
    lines.extend([
        "",
        "## Combined selected portfolio",
        "",
        "| Rank | Candidate | Origin | Parent | Proposal | Profile | Branch | L1 | Mean error | Worst target mu | Global min mu | Max link/D | Sweep radius/D | Qualification |",
        "|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for rank, candidate in enumerate(selected, start=1):
        lines.append(
            f"| {rank} | `{candidate['candidate_id']}` | {candidate.get('portfolio_origin', '')} | "
            f"{candidate.get('portfolio_parent_candidate_id', '')} | {candidate['model_role']} | "
            f"{candidate['profile']} | {candidate['branch_sign']:+.0f} | {candidate['l1']:.4f} | "
            f"{candidate['mean_error']:.6f} | {candidate['target_angle_min_deg']:.2f} deg | "
            f"{candidate['global_angle_min_deg']:.2f} deg | {candidate['max_link_ratio']:.3f} | "
            f"{candidate['sweep_radius_ratio']:.3f} | {candidate.get('qualification_level', '')} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Fixed-L1 candidates remain unchanged in the merged pool.",
        "- Independent variable-L1 candidates explore the broad scale-aware design space.",
        "- Bridge-trust candidates continue strong fixed designs inside a bounded L1 neighborhood.",
        "- Bridge-release candidates continue the strongest trust-region results into the full variable range.",
        "- At least the configured number of fixed representatives is reserved in the selected artifacts unless geometrically duplicated by another selected candidate.",
        "- The combined Pareto front is the production output; no single ground-link mode is assumed universally superior.",
        "- This is a kinematic result, not machinery certification.",
    ])
    if any(candidate.get("orientation_required", False) for candidate in candidates):
        lines.extend([
            "", "## Position and orientation", "",
            "Orientation is the directed coupler A-to-B angle in world XY, with the tool frame at P.",
            "Position and orientation are checked together at each selected target phase.",
            "Path-acceptable counts refer to position; selection also requires every angular tolerance.",
            "No orientation between target phases, timing, or dwell is prescribed.", "",
            "| Candidate | Orientation acceptable | Maximum angular error (deg) | Pose acceptable |", "|---|---|---:|---|",
        ])
        for candidate in selected:
            lines.append(f"| {candidate['candidate_id']} | {candidate['orientation_acceptable']} | "
                         f"{candidate['max_orientation_error_deg']:.4f} | {candidate['pose_acceptable']} |")
        if not selected:
            lines.append("No candidate passed all selection requirements. Inspect all_candidates.csv for failure details.")
    (target_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_local_contribution(run_dir: Path, args: argparse.Namespace) -> None:
    if args.no_contribution_bundle:
        return
    try:
        from mechanism_generator.contributions import prepare_bundle
        page = prepare_bundle(run_dir)
        print(f"[LOCAL CONTRIBUTION] Review what to share: {page} (nothing uploaded)")
    except Exception as exc:
        # Contribution packaging must never discard a successful numerical run.
        # Do not echo arbitrary source values in this warning.
        print(f"[CONTRIBUTION WARNING] Local bundle unavailable ({type(exc).__name__}); "
              "results remain saved. Retry with mechanism-contribute prepare.", file=sys.stderr)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)

    if args.quick:
        args.perturbations_per_model = 0
        args.profile_matrix = "paired"
        args.adam_accuracy_steps = min(args.adam_accuracy_steps, 20)
        args.adam_tradeoff_steps = min(args.adam_tradeoff_steps, 30)
        args.lbfgs_steps = min(args.lbfgs_steps, 8)
        args.seed_phase_steps = min(args.seed_phase_steps, 181)
        args.optimization_global_steps = min(args.optimization_global_steps, 91)
        args.verification_steps = min(args.verification_steps, 361)
        args.top_k = min(args.top_k, 3)
        args.portfolio_fixed_seed_count = min(args.portfolio_fixed_seed_count, 1)
        args.portfolio_release_seed_count = min(args.portfolio_release_seed_count, 1)
        args.portfolio_bridge_accuracy_steps = min(args.portfolio_bridge_accuracy_steps, 12)
        args.portfolio_bridge_tradeoff_steps = min(args.portfolio_bridge_tradeoff_steps, 18)
        args.portfolio_bridge_lbfgs_steps = min(args.portfolio_bridge_lbfgs_steps, 5)
        args.portfolio_release_accuracy_steps = min(args.portfolio_release_accuracy_steps, 8)
        args.portfolio_release_tradeoff_steps = min(args.portfolio_release_tradeoff_steps, 15)
        args.portfolio_release_lbfgs_steps = min(args.portfolio_release_lbfgs_steps, 4)

    ENGINE.set_deterministic_seed(args.seed)
    device = ENGINE.choose_device(args.device)
    refine_dtype = ENGINE.torch_dtype(args.dtype)
    targets = ENGINE.collect_targets(args)

    role_definitions = {
        "balanced": ("balanced", Path(args.balanced_model)),
        "path": ("accuracy", Path(args.path_model)),
        "transmission": ("transmission", Path(args.transmission_model)),
    }
    models: List[Any] = []
    for role in args.model_roles:
        default_profile, path = role_definitions[role]
        loaded = ENGINE.load_model_role(role, default_profile, path, device)
        models.append(loaded)
        print(
            f"[MODEL] role={role} default_profile={default_profile} "
            f"variant={loaded.checkpoint_variant} state_epoch={loaded.checkpoint_epoch} file={path}"
        )
    if not models:
        raise RuntimeError("No proposal checkpoints could be loaded")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    label = ENGINE.sanitize_label(args.run_label) if args.run_label else "hybrid-portfolio"
    run_dir = Path(args.output_root) / "r25c" / f"{timestamp}_{label[:32]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    set_run_root(run_dir)
    source_path = Path(__file__).resolve()
    run_manifest: Dict[str, Any] = {
        "variant": VARIANT,
        "parent_variant": PARENT_VARIANT,
        "schema_version": SCHEMA_VERSION,
        "run_status": "partial",
        "timestamp": timestamp,
        "device": str(device),
        "refinement_dtype": args.dtype,
        "seed": args.seed,
        "script": str(source_path),
        "script_sha256": sha256_file(source_path),
        "engine_script": str(ENGINE_PATH),
        "engine_variant": ENGINE_VARIANT,
        "engine_sha256": sha256_file(ENGINE_PATH),
        "orientation_sha256": sha256_file(ENGINE_PATH.with_name("orientation.py")),
        "arguments": vars(args),
        "models": [
            {
                "role": role.role,
                "default_profile": role.profile,
                "path": str(role.path),
                "checkpoint_variant": role.checkpoint_variant,
                "checkpoint_epoch": role.checkpoint_epoch,
                "sha256": role.checkpoint_sha256,
            }
            for role in models
        ],
        "targets": [],
    }
    ENGINE.write_json(run_dir / "run_config.json", run_manifest)

    print(f"Using device: {device}; refinement dtype: {args.dtype}")
    print(
        f"Portfolio: fixed L1={args.fixed_ground_link_value:g} + independent variable L1 "
        f"+ trust continuation (+ release={not args.portfolio_skip_release})"
    )
    print(f"Run directory: {run_dir}")

    fixed_args = copy.deepcopy(args)
    fixed_args.ground_link_mode = "fixed"
    variable_args = copy.deepcopy(args)
    variable_args.ground_link_mode = "optimize"

    for target_index, (target_label, target_values) in enumerate(targets):
        target_started = time.time()
        target_dir = run_dir / f"{target_index + 1:04d}_{ENGINE.sanitize_label(target_label)}"
        target_dir.mkdir(parents=True, exist_ok=False)
        stage_dirs = {
            "fixed": target_dir / "01_fixed_l1",
            "variable": target_dir / "02_variable_independent",
            "bridge_trust": target_dir / "03_bridge_trust",
            "bridge_release": target_dir / "04_bridge_release",
        }
        for path in stage_dirs.values():
            path.mkdir(parents=True, exist_ok=True)

        target = torch.tensor(target_values, dtype=refine_dtype, device=device)
        target_points = target_values.reshape(3, 2)
        if not np.isfinite(target_points).all():
            raise ValueError(f"Target {target_label} contains NaN or infinity")
        space = ENGINE.target_design_space(target, variable_args)
        print(
            f"\n[TARGET {target_index + 1}/{len(targets)}] {target_label}: "
            f"{target_points.tolist()} | D={float(space['scale'].item()):.4f}"
        )

        lineage_by_id: Dict[str, Dict[str, str]] = {}
        fixed_starts = prefix_starts(
            ENGINE.build_starts(models, target, fixed_args, target_index),
            "fixed",
            lineage_by_id,
        )
        variable_starts = prefix_starts(
            ENGINE.build_starts(models, target, variable_args, target_index),
            "variable",
            lineage_by_id,
        )
        print(
            f"[PORTFOLIO STARTS] fixed={len(fixed_starts)} independent-variable={len(variable_starts)}"
        )

        fixed_acq = run_acquisitions(
            fixed_starts, target, fixed_args, "FIXED"
        )
        variable_acq = run_acquisitions(
            variable_starts, target, variable_args, "VARIABLE"
        )
        shared_reference = ENGINE.build_shared_path_reference(
            [*fixed_acq, *variable_acq], args
        )
        ENGINE.write_json(target_dir / "shared_path_reference.json", shared_reference)
        print(
            f"[PORTFOLIO SHARED PATH] reference={shared_reference['reference_candidate_id']} "
            f"mean={shared_reference['reference_acquired_mean_error']:.6f} "
            f"budget={shared_reference['shared_mean_budget']:.6f}"
        )

        fixed_candidates = run_tradeoff(
            fixed_acq,
            shared_reference,
            target,
            fixed_args,
            stage_dirs["fixed"],
            "FIXED",
            lineage_by_id,
        )
        variable_candidates = run_tradeoff(
            variable_acq,
            shared_reference,
            target,
            variable_args,
            stage_dirs["variable"],
            "VARIABLE",
            lineage_by_id,
        )

        # Qualify the two independent branches before selecting fixed seeds.
        ENGINE.apply_shared_candidate_qualification(
            fixed_candidates, fixed_args, shared_reference
        )
        ENGINE.apply_shared_candidate_qualification(
            variable_candidates, variable_args, shared_reference
        )
        fixed_seeds = choose_diverse_champions(
            fixed_candidates, args.portfolio_fixed_seed_count, fixed_args
        )
        ENGINE.write_csv(
            target_dir / "fixed_seed_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in fixed_seeds],
        )
        print(
            "[BRIDGE SEEDS] "
            + (", ".join(str(c["candidate_id"]) for c in fixed_seeds) if fixed_seeds else "none")
        )

        trust_args = make_bridge_args(args, target, release=False)
        trust_starts = build_continuation_starts(
            fixed_seeds,
            target,
            trust_args,
            args,
            "bridge_trust",
            target_index,
            lineage_by_id,
            perturbations=args.portfolio_bridge_perturbations,
            parameter_noise=args.portfolio_bridge_parameter_noise,
            phase_noise_deg=args.portfolio_bridge_phase_noise_deg,
            cross_profiles=args.portfolio_bridge_profile_matrix == "cross",
        )
        trust_acq = run_acquisitions(
            trust_starts, target, trust_args, "BRIDGE TRUST"
        )
        trust_candidates = run_tradeoff(
            trust_acq,
            shared_reference,
            target,
            trust_args,
            stage_dirs["bridge_trust"],
            "BRIDGE TRUST",
            lineage_by_id,
        )
        ENGINE.apply_shared_candidate_qualification(
            trust_candidates, trust_args, shared_reference
        )

        release_candidates: List[Dict[str, Any]] = []
        if not args.portfolio_skip_release and trust_candidates:
            release_seeds = choose_diverse_champions(
                trust_candidates, args.portfolio_release_seed_count, trust_args
            )
            ENGINE.write_csv(
                target_dir / "bridge_release_seed_candidates.csv",
                [ENGINE.flat_candidate_row(c) for c in release_seeds],
            )
            release_args = make_bridge_args(args, target, release=True)
            release_starts = build_continuation_starts(
                release_seeds,
                target,
                release_args,
                args,
                "bridge_release",
                target_index,
                lineage_by_id,
                perturbations=0,
                parameter_noise=0.0,
                phase_noise_deg=0.0,
                cross_profiles=False,
            )
            release_acq = run_acquisitions(
                release_starts, target, release_args, "BRIDGE RELEASE"
            )
            release_candidates = run_tradeoff(
                release_acq,
                shared_reference,
                target,
                release_args,
                stage_dirs["bridge_release"],
                "BRIDGE RELEASE",
                lineage_by_id,
            )
            ENGINE.apply_shared_candidate_qualification(
                release_candidates, release_args, shared_reference
            )

        all_candidates = [
            *fixed_candidates,
            *variable_candidates,
            *trust_candidates,
            *release_candidates,
        ]
        portfolio_args = copy.deepcopy(args)
        portfolio_args.ground_link_mode = "portfolio"
        qualification = ENGINE.apply_shared_candidate_qualification(
            all_candidates, portfolio_args, shared_reference
        )
        qualification["stage_a_shared_reference"] = shared_reference
        qualification["portfolio_fixed_ground_link_value"] = float(
            args.fixed_ground_link_value
        )
        qualification["portfolio_origins"] = sorted(
            {str(c.get("portfolio_origin", "")) for c in all_candidates}
        )

        selected_base, fallback_used = ENGINE.select_diverse_candidates(
            all_candidates, portfolio_args
        )
        selected = ensure_fixed_representatives(
            selected_base, fixed_candidates, portfolio_args
        )
        qualification["selection_fallback_used"] = fallback_used
        qualification["fixed_representatives_reserved"] = sum(
            c.get("portfolio_origin") == "fixed" for c in selected
        )
        front = ENGINE.pareto_front(all_candidates, portfolio_args)
        fixed_front = ENGINE.pareto_front(fixed_candidates, fixed_args)
        variable_front = ENGINE.pareto_front(variable_candidates, variable_args)

        # Use the portfolio variant in plot titles generated by the engine.
        original_engine_variant = ENGINE.VARIANT
        ENGINE.VARIANT = VARIANT
        try:
            for rank, candidate in enumerate(selected, start=1):
                candidate["selected_rank"] = rank
                ENGINE.save_candidate_artifacts(
                    candidate, rank, target_dir, portfolio_args
                )
        finally:
            ENGINE.VARIANT = original_engine_variant

        path_ok = [c for c in all_candidates if c.get("path_acceptable", False)]
        qualified = [c for c in all_candidates if c.get("selection_eligible", False)]
        engineering = [c for c in all_candidates if c.get("engineering_acceptable", False)]
        rejected = [c for c in all_candidates if not c.get("selection_eligible", False)]

        origin_names = ("fixed", "variable", "bridge_trust", "bridge_release")
        origin_rows = [summarize_origin(name, all_candidates) for name in origin_names]
        ENGINE.write_json(target_dir / "selection_reference.json", qualification)
        ENGINE.write_json(target_dir / "portfolio_lineage.json", lineage_by_id)
        ENGINE.write_csv(
            target_dir / "portfolio_origin_summary.csv", origin_rows
        )
        ENGINE.write_csv(
            target_dir / "all_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in all_candidates],
        )
        ENGINE.write_csv(
            target_dir / "path_acceptable_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in path_ok],
        )
        ENGINE.write_csv(
            target_dir / "qualified_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in qualified],
        )
        ENGINE.write_csv(
            target_dir / "engineering_acceptable_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in engineering],
        )
        ENGINE.write_csv(
            target_dir / "rejected_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in rejected],
        )
        ENGINE.write_csv(
            target_dir / "selected_candidates.csv",
            [ENGINE.flat_candidate_row(c) for c in selected],
        )
        ENGINE.write_csv(
            target_dir / "pareto_front.csv",
            [ENGINE.flat_candidate_row(c) for c in front],
        )
        ENGINE.write_csv(
            target_dir / "fixed_pareto_front.csv",
            [ENGINE.flat_candidate_row(c) for c in fixed_front],
        )
        ENGINE.write_csv(
            target_dir / "variable_pareto_front.csv",
            [ENGINE.flat_candidate_row(c) for c in variable_front],
        )
        for origin, candidates in (
            ("fixed", fixed_candidates),
            ("variable", variable_candidates),
            ("bridge_trust", trust_candidates),
            ("bridge_release", release_candidates),
        ):
            stage_args = portfolio_args
            champions = choose_diverse_champions(
                candidates, args.portfolio_stage_top_k, stage_args
            )
            ENGINE.write_csv(
                target_dir / f"{origin}_champions.csv",
                [ENGINE.flat_candidate_row(c) for c in champions],
            )

        elapsed = time.time() - target_started
        write_portfolio_summary(
            target_dir,
            target_values,
            all_candidates,
            selected,
            qualification,
            origin_rows,
            elapsed,
        )

        target_manifest = {
            "label": target_label,
            "directory": str(target_dir),
            "target_values": target_values.tolist(),
            "target_scale": float(space["scale"].item()),
            "candidate_count": len(all_candidates),
            "origin_summary": origin_rows,
            "path_acceptable_count": len(path_ok),
            "selection_eligible_count": len(qualified),
            "engineering_acceptable_count": len(engineering),
            "selected_count": len(selected),
            "pareto_count": len(front),
            "selection_reference": qualification,
            "runtime_seconds": elapsed,
            "selected": [
                {"rank": rank, **ENGINE.flat_candidate_row(candidate)}
                for rank, candidate in enumerate(selected, start=1)
            ],
        }
        if ENGINE.has_pose_targets(args):
            target_manifest.update(
                target_orientations_deg=list(args.target_orientations_deg),
                orientation_tolerances_deg=ENGINE.pose_tolerances(args),
                orientation_frame="coupler_A_to_B",
                orientation_acceptable_count=sum(bool(c.get("orientation_acceptable", False)) for c in all_candidates),
                pose_acceptable_count=sum(bool(c.get("pose_acceptable", False)) for c in all_candidates),
            )
            print(f"[POSE QUALIFICATION] position-and-orientation={target_manifest['pose_acceptable_count']}/{len(all_candidates)}")
        run_manifest["targets"].append(target_manifest)
        ENGINE.write_json(run_dir / "run_manifest.json", run_manifest)
        write_local_contribution(run_dir, args)

        print(
            f"[PORTFOLIO QUALIFICATION] path_ok={len(path_ok)}/{len(all_candidates)} "
            f"selection_ok={len(qualified)}/{len(all_candidates)} "
            f"engineering_ok={len(engineering)}/{len(all_candidates)} "
            f"fixed_reserved={qualification['fixed_representatives_reserved']}"
        )
        print(
            f"[TARGET COMPLETE] {elapsed:.2f}s | candidates={len(all_candidates)} "
            f"selected={len(selected)} | {target_dir}"
        )
        if selected:
            best = selected[0]
            print(
                f"[BEST PORTFOLIO] id={best['candidate_id']} origin={best.get('portfolio_origin')} "
                f"mean={best['mean_error']:.6f}, "
                f"worst target transmission={best['target_angle_min_deg']:.2f}deg, "
                f"global minimum={best['global_angle_min_deg']:.2f}deg, "
                f"L1={best['l1']:.3f}, qualification={best.get('qualification_level')}"
            )

    run_manifest["run_status"] = "completed"
    ENGINE.write_json(run_dir / "run_manifest.json", run_manifest)
    write_local_contribution(run_dir, args)
    print(f"\nR2.5c hybrid portfolio complete. Artifacts: {run_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Portfolio search stopped by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
