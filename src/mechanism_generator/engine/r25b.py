#!/usr/bin/env python3
"""
V5.3-R2.5b Robust Transmission and Compactness Refiner

Purpose
-------
Extend R2.5a from a fixed-ground-link proof of concept into a scale-aware,
translation-invariant local mechanism designer.

For each target triple the script:

    target points
        -> three frozen neural proposal models
        -> optional proposal/profile cross-product
        -> Stage-A continuous path acquisition
        -> one shared target-wide path reference
        -> Stage-B robust worst-target transmission refinement
        -> optional variable-ground-link optimization
        -> compactness and swept-envelope evaluation
        -> robustness-margin verification
        -> qualified, deduplicated Pareto candidates

The proposal networks remain frozen and still emit the historical eight
parameters. The local refiner prepends an initial ground length and may optimize
it as a ninth mechanism parameter. All dimensional search bounds are derived
from the maximum pairwise target separation, so translating the same task no
longer changes the admissible link lengths.

R2.5b also separates proposal source from local objective. In the default
``cross`` profile matrix, every proposal model is refined under accuracy,
balanced, and transmission profiles. This tests whether, for example, an
accuracy-trained proposal becomes the best transmission design after local
optimization.

This is a kinematic research/design aid. It is not structural, fatigue,
controls, sanitation, or machinery-safety certification.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib

# Saving plots is the default. Avoid a GUI dependency unless explicitly asked.
_SHOW_REQUESTED = "--show_plots" in sys.argv
_HEADLESS = "--headless" in sys.argv or not _SHOW_REQUESTED
try:
    matplotlib.use("Agg" if _HEADLESS else "TkAgg")
except ImportError:
    matplotlib.use("Agg")
    _HEADLESS = True

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from .orientation import orientation_angles, orientation_metrics
from safetensors import safe_open
from safetensors.torch import load_file
from .provenance import public_data, set_run_root


VARIANT = "V5.3-R2.5b_RobustTransmissionAndCompactness-public-alpha"
PARENT_VARIANT = "V5.3-R2.5a_QualifiedCandidateSelection"
SCHEMA_VERSION = 3

# Historical proposal-domain constants. The proposal network was trained with
# L1=6 and the coordinate box below. Local refinement is no longer tied to that
# ground length or to origin-dependent link bounds.
X_MIN, X_MAX = -7.0, 1.0
Y_MIN, Y_MAX = 1.0, 7.0
PROPOSAL_L1_VALUE = 6.0
MIN_LEN = 1e-3
MIN_BAR_LEN = 0.1
ASSEMBLY_VALIDITY_TOL_REL = 1e-6
CENTER_DISTANCE_FLOOR_REL = 1e-4
D2_NUMERIC_FLOOR_REL = 1e-12
H2_NUMERIC_FLOOR_REL = 1e-8
DISTANCE_SQ_FLOOR = 1e-12
INVALID_DISTANCE = 20.0
DEFAULT_CLASS_MARGIN = 0.05

_possible_points = torch.tensor(
    [[X_MIN, Y_MIN], [X_MIN, Y_MAX], [X_MAX, Y_MIN], [X_MAX, Y_MAX]],
    dtype=torch.float64,
)
GLOBAL_MAX_LEN = 2.0 * torch.norm(_possible_points, dim=1).max().item()
TWO_PI = 2.0 * math.pi
MECHANISM_PARAM_DIM = 9
MECHANISM_RAW_DIM = 9

OUTPUT_PARAMETER_NAMES = (
    "l1",
    "l2",
    "l3",
    "l4",
    "S_ratio",
    "bar_length",
    "base_x",
    "base_y",
    "base_angle",
)

@dataclass(frozen=True)
class RefinementProfile:
    name: str
    # Stage A: position acquisition.
    stage_a_target_transmission_weight: float
    stage_a_global_transmission_weight: float
    # Stage B: preserve the acquired path while improving transmission.
    target_transmission_weight: float
    global_transmission_weight: float
    compactness_weight: float
    residual_position_weight: float
    path_constraint_weight: float
    point_guard_weight: float
    mean_path_allowance: float
    point_path_allowance: float
    ranking_transmission_weight: float
    ranking_global_weight: float
    ranking_compactness_weight: float


PROFILES: Dict[str, RefinementProfile] = {
    "accuracy": RefinementProfile(
        name="accuracy",
        stage_a_target_transmission_weight=0.05,
        stage_a_global_transmission_weight=0.05,
        target_transmission_weight=0.75,
        global_transmission_weight=0.30,
        compactness_weight=0.25,
        residual_position_weight=1.00,
        path_constraint_weight=3000.0,
        point_guard_weight=1500.0,
        mean_path_allowance=0.0025,
        point_path_allowance=0.0060,
        ranking_transmission_weight=0.45,
        ranking_global_weight=0.15,
        ranking_compactness_weight=0.015,
    ),
    "balanced": RefinementProfile(
        name="balanced",
        stage_a_target_transmission_weight=0.10,
        stage_a_global_transmission_weight=0.05,
        target_transmission_weight=8.00,
        global_transmission_weight=2.00,
        compactness_weight=1.00,
        residual_position_weight=0.20,
        path_constraint_weight=3500.0,
        point_guard_weight=1750.0,
        mean_path_allowance=0.0060,
        point_path_allowance=0.0120,
        ranking_transmission_weight=2.25,
        ranking_global_weight=0.35,
        ranking_compactness_weight=0.035,
    ),
    "transmission": RefinementProfile(
        name="transmission",
        stage_a_target_transmission_weight=0.20,
        stage_a_global_transmission_weight=0.10,
        target_transmission_weight=24.0,
        global_transmission_weight=5.00,
        compactness_weight=0.60,
        residual_position_weight=0.05,
        path_constraint_weight=5000.0,
        point_guard_weight=2500.0,
        mean_path_allowance=0.0150,
        point_path_allowance=0.0300,
        ranking_transmission_weight=5.00,
        ranking_global_weight=0.60,
        ranking_compactness_weight=0.025,
    ),
}

@dataclass
class ModelRole:
    role: str
    profile: str
    path: Path
    model: nn.Module
    checkpoint_variant: str
    checkpoint_epoch: Optional[int]
    checkpoint_sha256: str


@dataclass
class StartSpec:
    candidate_id: str
    model_role: str
    profile: str
    checkpoint_variant: str
    checkpoint_epoch: Optional[int]
    branch_sign: float
    perturbation_index: int
    raw_initial: torch.Tensor
    initial_params: torch.Tensor
    initial_phases: torch.Tensor


# ======================
# ===== CLI =====
# ======================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{VARIANT}: robustly refine four-bar mechanisms for one or more target triples",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--targets", type=float, nargs=6,
        metavar=("X1", "Y1", "X2", "Y2", "X3", "Y3"),
        help="One target triple as six numbers",
    )
    target_group.add_argument(
        "--targets_file", type=str,
        help="CSV with x1,y1,x2,y2,x3,y3 or target_x1,target_y1,...",
    )
    target_group.add_argument("--demo", action="store_true")

    parser.add_argument("--balanced_model", default="balanced.safetensors")
    parser.add_argument("--path_model", default="path.safetensors")
    parser.add_argument(
        "--transmission_model",
        default="transmission.safetensors",
    )
    parser.add_argument(
        "--model_roles", nargs="+",
        choices=("balanced", "path", "transmission"),
        default=("balanced", "path", "transmission"),
    )
    parser.add_argument(
        "--profile_matrix", choices=("paired", "cross"), default="cross",
        help="Paired uses each model's historical profile; cross tries every model under every profile",
    )
    parser.add_argument(
        "--branches", choices=("negative", "positive", "both"), default="negative",
    )
    parser.add_argument("--crank_direction", choices=("positive", "negative", "either"),
                        default="positive", help="Input crank rotation; either runs both directions with separate results.")
    parser.add_argument(
        "--phase_mode", choices=("unordered", "ordered"), default="unordered",
    )
    parser.add_argument(
        "--target_orientations_deg", type=float, nargs=3, default=None,
        metavar=("A1", "A2", "A3"),
        help="Optional directed coupler orientations at the three target positions, in world degrees (A to B)",
    )
    parser.add_argument(
        "--orientation_tolerances_deg", type=float, nargs=3, default=None,
        metavar=("T1", "T2", "T3"),
        help="Per-target angular tolerances in degrees; default 5 each when orientations are requested",
    )
    parser.add_argument("--perturbations_per_model", type=int, default=0)
    parser.add_argument("--parameter_noise", type=float, default=0.18)
    parser.add_argument("--phase_noise_deg", type=float, default=4.0)

    # Scale-aware local design space.
    parser.add_argument(
        "--ground_link_mode", choices=("optimize", "fixed"), default="optimize",
        help="Optimize L1 or hold it at --fixed_ground_link_value",
    )
    parser.add_argument("--fixed_ground_link_value", type=float, default=PROPOSAL_L1_VALUE)
    parser.add_argument("--ground_link_min_ratio", type=float, default=0.50)
    parser.add_argument("--ground_link_max_ratio", type=float, default=2.50)
    parser.add_argument("--moving_link_min_ratio", type=float, default=0.05)
    parser.add_argument("--moving_link_max_ratio", type=float, default=3.00)
    parser.add_argument("--bar_length_max_ratio", type=float, default=1.50)
    parser.add_argument("--base_search_radius_ratio", type=float, default=3.00)
    parser.add_argument("--minimum_target_scale", type=float, default=0.25)

    parser.add_argument("--adam_accuracy_steps", type=int, default=60)
    parser.add_argument("--adam_tradeoff_steps", type=int, default=100)
    parser.add_argument("--adam_lr", type=float, default=0.025)
    parser.add_argument("--lbfgs_steps", type=int, default=20)
    parser.add_argument("--lbfgs_lr", type=float, default=0.60)
    parser.add_argument("--grad_clip", type=float, default=100.0)
    parser.add_argument("--seed_phase_steps", type=int, default=721)
    parser.add_argument("--optimization_global_steps", type=int, default=181)
    parser.add_argument("--verification_steps", type=int, default=1441)
    parser.add_argument("--history_interval", type=int, default=10)

    # Robust target and global transmission objectives.
    parser.add_argument("--target_transmission_deg", type=float, default=35.0)
    parser.add_argument("--global_transmission_floor_deg", type=float, default=15.0)
    parser.add_argument("--worst_target_focus", type=float, default=0.90)
    parser.add_argument("--worst_target_temperature", type=float, default=0.02)
    parser.add_argument("--global_min_focus", type=float, default=0.50)
    parser.add_argument("--global_min_temperature", type=float, default=0.01)
    parser.add_argument("--global_top_fraction", type=float, default=0.05)

    # Physical and robustness constraints.
    parser.add_argument("--class_margin", type=float, default=DEFAULT_CLASS_MARGIN)
    parser.add_argument("--class_margin_ratio", type=float, default=0.01)
    parser.add_argument("--assembly_margin_ratio", type=float, default=0.01)
    parser.add_argument("--grashof_margin_ratio", type=float, default=0.01)
    parser.add_argument("--enforce_follower_not_longest", action="store_true")
    parser.add_argument("--assembly_weight", type=float, default=10000.0)
    parser.add_argument("--grashof_weight", type=float, default=2000.0)
    parser.add_argument("--class_weight", type=float, default=2000.0)
    parser.add_argument("--robustness_weight", type=float, default=750.0)
    parser.add_argument("--target_validity_weight", type=float, default=10000.0)
    parser.add_argument("--drift_weight", type=float, default=1e-5)

    # Compactness and swept-envelope objective. Ratios are relative to the
    # maximum pairwise target separation D.
    parser.add_argument("--compactness_weight", type=float, default=0.05)
    parser.add_argument("--compactness_max_link_ratio", type=float, default=2.00)
    parser.add_argument("--compactness_total_link_ratio", type=float, default=5.00)
    parser.add_argument("--compactness_sweep_radius_ratio", type=float, default=2.75)
    parser.add_argument("--compactness_sweep_area_ratio", type=float, default=12.0)
    parser.add_argument("--compactness_bar_ratio", type=float, default=1.00)
    parser.add_argument("--compactness_softness", type=float, default=0.15)
    parser.add_argument("--ranking_compactness_weight", type=float, default=0.03)
    parser.add_argument(
        "--engineering_max_link_ratio", type=float, default=0.0,
        help="Optional hard engineering compactness ceiling; 0 disables",
    )
    parser.add_argument(
        "--engineering_max_sweep_radius_ratio", type=float, default=0.0,
        help="Optional hard engineering sweep-radius ceiling; 0 disables",
    )

    # Shared final qualification.
    parser.add_argument("--max_mean_error", type=float, default=0.05)
    parser.add_argument("--max_point_error", type=float, default=0.075)
    parser.add_argument("--shared_mean_allowance", type=float, default=0.02)
    parser.add_argument("--shared_point_allowance", type=float, default=0.05)
    parser.add_argument("--minimum_target_transmission", type=float, default=15.0)
    parser.add_argument("--minimum_global_transmission", type=float, default=10.0)
    parser.add_argument("--strict_qualification", action="store_true")
    parser.add_argument("--allow_unqualified_fallback", action="store_true")

    parser.add_argument("--panel_bounds", type=float, nargs=4, metavar=("XMIN", "XMAX", "YMIN", "YMAX"))
    parser.add_argument("--carrier_size", type=float, nargs=2, metavar=("WIDTH", "HEIGHT"),
                        help="Rectangle centred on P, width parallel to coupler A-to-B; same units as targets")
    parser.add_argument("--panel_pivot_clearance", type=float, default=0.)
    parser.add_argument("--panel_steps", type=int, default=7201,
                        help="Full-turn sampled panel containment phases (361 to 72001); not a collision certificate")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--dedup_parameter_threshold", type=float, default=0.025)
    parser.add_argument("--dedup_curve_threshold", type=float, default=0.025)
    parser.add_argument("--output_root", default="refinement_runs")
    parser.add_argument("--run_label", default="")
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--dtype", choices=("float32", "float64"), default="float64")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no_plots", action="store_true")
    parser.add_argument("--show_plots", action="store_true")
    parser.add_argument("--quick", action="store_true")
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    from . import panel
    try:
        panel.configuration(args)
    except ValueError as error:
        parser.error(str(error))
    if args.target_orientations_deg is None:
        if args.orientation_tolerances_deg is not None:
            parser.error("Orientation tolerances require --target_orientations_deg")
    else:
        if not all(math.isfinite(value) for value in args.target_orientations_deg):
            parser.error("Target orientations must be finite")
        # Reduce before conversion to refinement dtype so large finite degree
        # values retain their direction and cannot overflow a float32 tensor.
        args.target_orientations_deg = [math.remainder(value, 360.0) for value in args.target_orientations_deg]
        if args.orientation_tolerances_deg is None:
            args.orientation_tolerances_deg = [5.0, 5.0, 5.0]
        if not all(math.isfinite(value) and 0 < value < 180 for value in args.orientation_tolerances_deg):
            parser.error("Orientation tolerances must be finite and strictly between 0 and 180 degrees")
    if args.perturbations_per_model < 0:
        parser.error("--perturbations_per_model must be non-negative")
    if args.parameter_noise < 0 or args.phase_noise_deg < 0:
        parser.error("Perturbation magnitudes must be non-negative")
    if min(args.adam_accuracy_steps, args.adam_tradeoff_steps, args.lbfgs_steps) < 0:
        parser.error("Optimization step counts must be non-negative")
    if args.adam_lr <= 0 or args.lbfgs_lr <= 0:
        parser.error("Optimizer learning rates must be positive")
    if min(args.seed_phase_steps, args.optimization_global_steps, args.verification_steps) < 5:
        parser.error("Simulation grids must contain at least five points")
    if not (0.0 < args.global_top_fraction <= 1.0):
        parser.error("--global_top_fraction must be in (0,1]")
    if not (0.0 <= args.worst_target_focus <= 1.0):
        parser.error("--worst_target_focus must be in [0,1]")
    if not (0.0 <= args.global_min_focus <= 1.0):
        parser.error("--global_min_focus must be in [0,1]")
    if args.worst_target_temperature <= 0 or args.global_min_temperature <= 0:
        parser.error("Soft-min temperatures must be positive")
    if args.target_transmission_deg <= 0 or args.target_transmission_deg >= 90:
        parser.error("--target_transmission_deg must be between 0 and 90")
    if args.global_transmission_floor_deg <= 0 or args.global_transmission_floor_deg >= 90:
        parser.error("--global_transmission_floor_deg must be between 0 and 90")
    if args.top_k < 1 or args.history_interval < 1:
        parser.error("--top_k and --history_interval must be positive")
    if args.fixed_ground_link_value <= MIN_LEN:
        parser.error("--fixed_ground_link_value must exceed MIN_LEN")
    positive_ratios = (
        args.ground_link_min_ratio, args.ground_link_max_ratio,
        args.moving_link_min_ratio, args.moving_link_max_ratio,
        args.bar_length_max_ratio, args.base_search_radius_ratio,
        args.minimum_target_scale,
    )
    if any(value <= 0 for value in positive_ratios):
        parser.error("Scale and design-space ratios must be positive")
    if args.ground_link_max_ratio <= args.ground_link_min_ratio:
        parser.error("Ground-link maximum ratio must exceed minimum ratio")
    if args.moving_link_max_ratio <= args.moving_link_min_ratio:
        parser.error("Moving-link maximum ratio must exceed minimum ratio")
    if args.max_mean_error <= 0 or args.max_point_error <= 0:
        parser.error("Absolute path ceilings must be positive")
    if args.shared_mean_allowance < 0 or args.shared_point_allowance < 0:
        parser.error("Shared path allowances must be non-negative")
    if args.minimum_target_transmission < 0 or args.minimum_global_transmission < 0:
        parser.error("Selection transmission floors must be non-negative")
    if args.minimum_target_transmission >= 90 or args.minimum_global_transmission >= 90:
        parser.error("Selection transmission floors must be below 90 degrees")
    if min(args.class_margin, args.class_margin_ratio, args.assembly_margin_ratio,
           args.grashof_margin_ratio, args.compactness_weight,
           args.ranking_compactness_weight) < 0:
        parser.error("Margins and compactness weights must be non-negative")
    compact_limits = (
        args.compactness_max_link_ratio, args.compactness_total_link_ratio,
        args.compactness_sweep_radius_ratio, args.compactness_sweep_area_ratio,
        args.compactness_bar_ratio, args.compactness_softness,
    )
    if any(value <= 0 for value in compact_limits):
        parser.error("Compactness targets and softness must be positive")

def sanitize_label(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-._") or "run"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def set_deterministic_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(requested: str) -> torch.device:
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("--device cuda was requested, but CUDA is unavailable")
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def torch_dtype(name: str) -> torch.dtype:
    return torch.float64 if name == "float64" else torch.float32


def json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, torch.Tensor):
        if value.ndim == 0:
            return value.detach().cpu().item()
        return value.detach().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(json_ready(public_data(data)), stream, indent=2, sort_keys=True)


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json_ready(public_data(row.get(key, ""), key)) for key in fieldnames})


def safe_logit(value: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    value = value.clamp(eps, 1.0 - eps)
    return torch.log(value) - torch.log1p(-value)


def circular_difference(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return torch.atan2(torch.sin(a - b), torch.cos(a - b))


def acute_angle_from_q(q: torch.Tensor) -> torch.Tensor:
    return torch.rad2deg(torch.asin(torch.sqrt(q.clamp(0.0, 1.0))))


def normalized_softmin(values: torch.Tensor, temperature: float) -> torch.Tensor:
    """Smooth minimum normalized so a constant vector returns that constant."""
    tau = torch.tensor(float(temperature), dtype=values.dtype, device=values.device)
    count = max(1, values.shape[-1])
    return -tau * (torch.logsumexp(-values / tau, dim=-1) - math.log(count))


def target_design_space(target: torch.Tensor, args: argparse.Namespace) -> Dict[str, torch.Tensor]:
    xy = target.reshape(3, 2)
    pairwise = torch.cdist(xy[None, :, :], xy[None, :, :])[0]
    scale = pairwise.max().clamp_min(float(args.minimum_target_scale))
    centroid = xy.mean(dim=0)
    ground_min = torch.maximum(
        torch.tensor(MIN_LEN, dtype=target.dtype, device=target.device),
        scale * float(args.ground_link_min_ratio),
    )
    ground_max = torch.maximum(
        ground_min + 1e-6,
        scale * float(args.ground_link_max_ratio),
    )
    moving_min = torch.maximum(
        torch.tensor(MIN_LEN, dtype=target.dtype, device=target.device),
        scale * float(args.moving_link_min_ratio),
    )
    moving_max = torch.maximum(
        moving_min + 1e-6,
        scale * float(args.moving_link_max_ratio),
    )
    bar_max = torch.maximum(
        torch.tensor(MIN_BAR_LEN + 1e-6, dtype=target.dtype, device=target.device),
        scale * float(args.bar_length_max_ratio),
    )
    base_radius = scale * float(args.base_search_radius_ratio)
    return {
        "scale": scale,
        "centroid": centroid,
        "ground_min": ground_min,
        "ground_max": ground_max,
        "moving_min": moving_min,
        "moving_max": moving_max,
        "bar_max": bar_max,
        "base_x_min": centroid[0] - base_radius,
        "base_x_max": centroid[0] + base_radius,
        "base_y_min": centroid[1] - base_radius,
        "base_y_max": centroid[1] + base_radius,
    }


def smooth_positive_part(value: torch.Tensor, softness: float) -> torch.Tensor:
    beta = max(float(softness), 1e-9)
    return torch.nn.functional.softplus(value / beta) * beta


# ======================
# ===== MODEL =====
# ======================
class MechanismNN(nn.Module):
    """V5.3/R2-R2.4 proposal network."""

    def __init__(self) -> None:
        super().__init__()
        current_dim = 6
        self.layers = nn.ModuleList()
        self.act = nn.SiLU()
        for hidden_dim in [512] * 8:
            self.layers.append(nn.Linear(current_dim, hidden_dim))
            current_dim = hidden_dim
        self.output_layer = nn.Linear(current_dim, 8)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        for layer in self.layers:
            x = self.act(layer(x))
        x = torch.sigmoid(self.output_layer(x))
        scaled_links = MIN_LEN + (GLOBAL_MAX_LEN - MIN_LEN) * x[:, :3]
        scaled_s = x[:, 3]
        scaled_bar = MIN_BAR_LEN + (GLOBAL_MAX_LEN - MIN_BAR_LEN) * x[:, 4]
        scaled_bx = X_MIN + (X_MAX - X_MIN) * x[:, 5]
        scaled_by = Y_MIN + (Y_MAX - Y_MIN) * x[:, 6]
        scaled_angle = TWO_PI * x[:, 7]
        return torch.cat(
            [
                scaled_links,
                scaled_s[:, None],
                scaled_bar[:, None],
                scaled_bx[:, None],
                scaled_by[:, None],
                scaled_angle[:, None],
            ],
            dim=1,
        )


def extract_state_dict(checkpoint: Any) -> Dict[str, torch.Tensor]:
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state = checkpoint["model_state_dict"]
    elif isinstance(checkpoint, dict):
        state = checkpoint
    else:
        raise TypeError("Checkpoint must be a dictionary or contain model_state_dict")
    if any(key.startswith("module.") for key in state):
        state = {key.removeprefix("module."): value for key, value in state.items()}
    return state


def load_model_role(
    role: str,
    profile: str,
    path: Path,
    device: torch.device,
) -> ModelRole:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix != ".safetensors":
        raise ValueError("Public inference accepts only .safetensors files")
    state = load_file(str(path), device="cpu")
    if any(not torch.isfinite(tensor).all() for tensor in state.values()):
        raise ValueError("Model contains non-finite parameters")
    model = MechanismNN()
    model.load_state_dict(state, strict=True)
    model.to(device=device, dtype=torch.float32)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    with safe_open(str(path), framework="pt", device="cpu") as checkpoint:
        metadata = checkpoint.metadata() or {}
    variant = metadata.get("variant", "unknown")
    state_epoch = int(metadata["state_epoch"]) if "state_epoch" in metadata else None
    return ModelRole(
        role=role,
        profile=profile,
        path=path.resolve(),
        model=model,
        checkpoint_variant=variant,
        checkpoint_epoch=state_epoch,
        checkpoint_sha256=sha256_file(path),
    )


def project_proposal_parameters(
    predicted: torch.Tensor,
    target: torch.Tensor,
    args: argparse.Namespace,
) -> torch.Tensor:
    """Convert one historical eight-parameter proposal to the R2.5b schema."""
    if predicted.ndim != 1 or predicted.numel() != 8:
        raise ValueError(f"predicted proposal must have shape [8], got {tuple(predicted.shape)}")
    space = target_design_space(target, args)
    if args.ground_link_mode == "fixed":
        l1 = torch.tensor(
            float(args.fixed_ground_link_value), dtype=target.dtype, device=target.device
        )
    else:
        l1 = torch.tensor(
            float(args.fixed_ground_link_value), dtype=target.dtype, device=target.device
        ).clamp(space["ground_min"], space["ground_max"])
    # Preserve the proposal network's historical post-processing for the initial
    # seed, then place that seed inside the broader translation-invariant local
    # design space. This avoids changing the meaning of the trained checkpoint
    # merely because R2.5b permits the local optimizer to explore longer links.
    target_xy = target.reshape(3, 2)
    legacy_max = torch.minimum(
        2.0 * torch.linalg.vector_norm(target_xy, dim=1).max(),
        torch.tensor(GLOBAL_MAX_LEN, dtype=target.dtype, device=target.device),
    )
    links = predicted[:3].to(dtype=target.dtype, device=target.device).clamp_min(MIN_LEN)
    links = torch.minimum(links, legacy_max).clamp(space["moving_min"], space["moving_max"])
    s_ratio = predicted[3].to(dtype=target.dtype, device=target.device).clamp(0.0, 1.0)
    legacy_bar_max = 0.5 * torch.max(
        torch.cat([
            torch.tensor([PROPOSAL_L1_VALUE], dtype=target.dtype, device=target.device),
            links,
        ])
    )
    bar = predicted[4].to(dtype=target.dtype, device=target.device).clamp_min(MIN_BAR_LEN)
    bar = torch.minimum(torch.minimum(bar, legacy_bar_max), space["bar_max"])
    base_x = predicted[5].to(dtype=target.dtype, device=target.device).clamp(
        space["base_x_min"], space["base_x_max"]
    )
    base_y = predicted[6].to(dtype=target.dtype, device=target.device).clamp(
        space["base_y_min"], space["base_y_max"]
    )
    base_angle = torch.remainder(
        predicted[7].to(dtype=target.dtype, device=target.device), TWO_PI
    )
    return torch.stack(
        [l1, links[0], links[1], links[2], s_ratio, bar, base_x, base_y, base_angle]
    )


# ======================
# ===== GEOMETRY =====
# ======================
def simulate_four_bar(
    params: torch.Tensor,
    theta: torch.Tensor,
    branch_sign: float,
    bar_angle_offset: float = math.pi / 2.0,
) -> Dict[str, torch.Tensor]:
    """Direct circle-circle solution for a batch of variable-L1 mechanisms.

    params: [B,9] = l1,l2,l3,l4,S_ratio,bar_length,base_x,base_y,base_angle
    theta:  [N]
    """
    if params.ndim != 2 or params.shape[1] != MECHANISM_PARAM_DIM:
        raise ValueError(
            f"params must have shape [B,{MECHANISM_PARAM_DIM}], got {tuple(params.shape)}"
        )
    if theta.ndim != 1:
        raise ValueError("theta must be one-dimensional")

    l1, l2, l3, l4 = params[:, 0], params[:, 1], params[:, 2], params[:, 3]
    s_ratio, bar_length = params[:, 4], params[:, 5]
    base_x, base_y, base_angle = params[:, 6], params[:, 7], params[:, 8]

    l1b, l2b, l3b, l4b, sb, barb = [
        value[:, None] for value in (l1, l2, l3, l4, s_ratio, bar_length)
    ]
    theta_b = theta[None, :]

    ax = l2b * torch.cos(theta_b)
    ay = l2b * torch.sin(theta_b)
    center_dx = ax - l1b
    center_dy = ay
    center_d2 = center_dx.square() + center_dy.square()

    scale_sq = torch.maximum(
        torch.maximum(torch.maximum(l1b.square(), l2b.square()), l3b.square()),
        torch.maximum(l4b.square(), center_d2),
    ).clamp_min(1.0)
    scale = torch.sqrt(scale_sq)
    center_distance = torch.sqrt(center_d2 + D2_NUMERIC_FLOOR_REL * scale_sq)
    center_floor = CENTER_DISTANCE_FLOOR_REL * scale
    center_safe = torch.maximum(center_distance, center_floor)
    assembly_tol = ASSEMBLY_VALIDITY_TOL_REL * scale

    outer_margin = l3b + l4b - center_distance
    inner_margin = center_distance - torch.abs(l3b - l4b)
    valid = (
        (l3b > MIN_LEN * 0.5)
        & (l4b > MIN_LEN * 0.5)
        & (center_distance > center_floor)
        & (outer_margin >= -assembly_tol)
        & (inner_margin >= -assembly_tol)
    )

    along_raw = (l4b.square() - l3b.square() + center_d2) / (2.0 * center_safe)
    h2_raw = l4b.square() - along_raw.square()
    h2_floor = H2_NUMERIC_FLOOR_REL * scale_sq
    h = torch.sqrt(torch.maximum(h2_raw, h2_floor))
    along = torch.minimum(torch.maximum(along_raw, -l4b), l4b)

    ux = center_dx / center_safe
    uy = center_dy / center_safe
    px_perp = -uy
    py_perp = ux
    bx = l1b + along * ux + float(branch_sign) * h * px_perp
    by = along * uy + float(branch_sign) * h * py_perp

    coupler_dx = bx - ax
    coupler_dy = by - ay
    coupler_norm = torch.sqrt(
        torch.maximum(
            coupler_dx.square() + coupler_dy.square(),
            D2_NUMERIC_FLOOR_REL * scale_sq,
        )
    )
    cux = coupler_dx / coupler_norm
    cuy = coupler_dy / coupler_norm
    offset_cos = math.cos(bar_angle_offset)
    offset_sin = math.sin(bar_angle_offset)
    oux = offset_cos * cux - offset_sin * cuy
    ouy = offset_sin * cux + offset_cos * cuy

    sx = ax + sb * coupler_dx
    sy = ay + sb * coupler_dy
    point_x = sx + barb * oux
    point_y = sy + barb * ouy

    cos_a = torch.cos(base_angle)[:, None]
    sin_a = torch.sin(base_angle)[:, None]

    def transform(x: torch.Tensor, y: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        return (
            cos_a * x - sin_a * y + base_x[:, None],
            sin_a * x + cos_a * y + base_y[:, None],
        )

    zero_x = torch.zeros_like(point_x)
    zero_y = torch.zeros_like(point_y)
    o4x_local = l1b.expand_as(point_x)
    o4y_local = torch.zeros_like(point_y)
    o2x, o2y = transform(zero_x, zero_y)
    axg, ayg = transform(ax, ay)
    bxg, byg = transform(bx, by)
    o4x, o4y = transform(o4x_local, o4y_local)
    pgx, pgy = transform(point_x, point_y)

    outer_violation = torch.relu(center_distance - (l3b + l4b))
    inner_violation = torch.relu(torch.abs(l3b - l4b) - center_distance)
    center_violation = torch.relu(center_floor - center_distance)
    sampled_violation = outer_violation + inner_violation + center_violation

    d_min = torch.abs(l1b - l2b)
    d_max = l1b + l2b
    full_scale = torch.maximum(
        torch.maximum(torch.maximum(l1b, l2b), l3b), l4b
    ).clamp_min(1.0)
    full_tol = ASSEMBLY_VALIDITY_TOL_REL * full_scale
    full_center_floor = CENTER_DISTANCE_FLOOR_REL * full_scale
    full_outer_margin = l3b + l4b - d_max
    full_inner_margin = d_min - torch.abs(l3b - l4b)
    full_center_margin = d_min - full_center_floor
    full_outer = torch.relu(-full_outer_margin)
    full_inner = torch.relu(-full_inner_margin)
    full_center = torch.relu(-full_center_margin)
    full_violation = full_outer + full_inner + full_center
    full_valid = (
        (full_outer <= full_tol)
        & (full_inner <= full_tol)
        & (full_center <= full_tol)
    )

    h2_nonnegative = h2_raw.clamp_min(0.0)
    tx_denominator = (l3b.square() * l4b.square()).clamp_min(DISTANCE_SQ_FLOOR)
    transmission_q = (center_d2 * h2_nonnegative / tx_denominator).clamp(0.0, 1.0)
    transmission_q = torch.where(valid, transmission_q, torch.zeros_like(transmission_q))

    return {
        "O2x": o2x, "O2y": o2y, "Ax": axg, "Ay": ayg,
        "Bx": bxg, "By": byg, "O4x": o4x, "O4y": o4y,
        "Px": pgx, "Py": pgy, "valid": valid,
        "transmission_q": transmission_q,
        "sampled_assembly_violation": sampled_violation,
        "full_cycle_assembly_violation": full_violation.squeeze(1),
        "full_cycle_valid": full_valid.squeeze(1),
        "full_outer_margin": full_outer_margin.squeeze(1),
        "full_inner_margin": full_inner_margin.squeeze(1),
        "full_center_margin": full_center_margin.squeeze(1),
        "outer_margin": outer_margin,
        "inner_margin": inner_margin,
        "h2_raw": h2_raw,
    }

def mechanism_constraint_tensors(
    params: torch.Tensor,
    target_scale: torch.Tensor,
    args: argparse.Namespace,
) -> Dict[str, torch.Tensor]:
    l1, l2, l3, l4 = params[:, 0], params[:, 1], params[:, 2], params[:, 3]
    links = torch.stack([l1, l2, l3, l4], dim=1)
    shortest, shortest_index = links.min(dim=1)
    longest, longest_index = links.max(dim=1)
    remaining = links.sum(dim=1) - shortest - longest
    grashof_margin = remaining - shortest - longest
    grashof_violation = torch.relu(-grashof_margin)

    crank_margins = torch.stack([l1 - l2, l3 - l2, l4 - l2], dim=1)
    effective_class_margin = torch.maximum(
        torch.tensor(float(args.class_margin), dtype=params.dtype, device=params.device),
        target_scale * float(args.class_margin_ratio),
    )
    crank_margin_violation = torch.relu(effective_class_margin - crank_margins)
    follower_margin = torch.maximum(l1, l3) - l4
    if args.enforce_follower_not_longest:
        follower_margin_violation = torch.relu(effective_class_margin - follower_margin)
        class_margin_violation = torch.cat(
            [crank_margin_violation, follower_margin_violation[:, None]], dim=1
        )
        exact_class = (shortest_index == 1) & (
            (longest_index == 0) | (longest_index == 2)
        )
    else:
        follower_margin_violation = torch.zeros_like(follower_margin)
        class_margin_violation = crank_margin_violation
        exact_class = shortest_index == 1

    return {
        "grashof_violation": grashof_violation,
        "grashof_margin": grashof_margin,
        "grashof_ok": grashof_violation <= 1e-7,
        "shortest_index": shortest_index,
        "longest_index": longest_index,
        "exact_class": exact_class,
        "crank_margin_min": crank_margins.min(dim=1).values,
        "follower_margin": follower_margin,
        "effective_class_margin": effective_class_margin,
        "class_margin_violation": class_margin_violation,
        "follower_margin_violation": follower_margin_violation,
    }


# ======================
# ===== PARAMETERIZATION =====
# ======================
def crank_direction_sign(args) -> int:
    direction = getattr(args, "crank_direction", "positive")
    if direction not in ("positive", "negative"):
        raise ValueError("A single search requires positive or negative crank direction")
    return -1 if direction == "negative" else 1


def encode_refinement_variables(
    params: torch.Tensor,
    phases: torch.Tensor,
    target: torch.Tensor,
    phase_mode: str,
    args: argparse.Namespace,
) -> torch.Tensor:
    params = params.to(dtype=target.dtype, device=target.device)
    phases = phases.to(dtype=target.dtype, device=target.device)
    space = target_design_space(target, args)

    if args.ground_link_mode == "optimize":
        ground_unit = (params[0] - space["ground_min"]) / (
            space["ground_max"] - space["ground_min"]
        )
    else:
        ground_unit = torch.tensor(0.5, dtype=params.dtype, device=params.device)
    moving_unit = (params[1:4] - space["moving_min"]) / (
        space["moving_max"] - space["moving_min"]
    )
    s_unit = params[4]
    bar_unit = (params[5] - MIN_BAR_LEN) / (space["bar_max"] - MIN_BAR_LEN)
    bx_unit = (params[6] - space["base_x_min"]) / (
        space["base_x_max"] - space["base_x_min"]
    )
    by_unit = (params[7] - space["base_y_min"]) / (
        space["base_y_max"] - space["base_y_min"]
    )
    raw = [
        safe_logit(ground_unit),
        *safe_logit(moving_unit).unbind(),
        safe_logit(s_unit),
        safe_logit(bar_unit),
        safe_logit(bx_unit),
        safe_logit(by_unit),
        params[8],
    ]
    base = torch.stack(raw)
    if phase_mode == "unordered":
        return torch.cat([base, phases])

    p0, p1, p2 = phases * crank_direction_sign(args)
    gaps = torch.stack(
        [
            torch.remainder(p1 - p0, TWO_PI),
            torch.remainder(p2 - p1, TWO_PI),
            torch.remainder(p0 - p2, TWO_PI),
        ]
    ).clamp_min(math.radians(0.25))
    gaps = TWO_PI * gaps / gaps.sum()
    gap_logits = torch.log(gaps / TWO_PI)
    return torch.cat([base, p0[None], gap_logits])


def decode_refinement_variables(
    raw: torch.Tensor,
    target: torch.Tensor,
    phase_mode: str,
    args: argparse.Namespace,
) -> Tuple[torch.Tensor, torch.Tensor]:
    space = target_design_space(target, args)
    if args.ground_link_mode == "optimize":
        l1 = space["ground_min"] + (
            space["ground_max"] - space["ground_min"]
        ) * torch.sigmoid(raw[0])
    else:
        l1 = torch.tensor(
            float(args.fixed_ground_link_value), dtype=raw.dtype, device=raw.device
        ) + 0.0 * raw[0]
    links = space["moving_min"] + (
        space["moving_max"] - space["moving_min"]
    ) * torch.sigmoid(raw[1:4])
    s_ratio = torch.sigmoid(raw[4])
    bar = MIN_BAR_LEN + (space["bar_max"] - MIN_BAR_LEN) * torch.sigmoid(raw[5])
    base_x = space["base_x_min"] + (
        space["base_x_max"] - space["base_x_min"]
    ) * torch.sigmoid(raw[6])
    base_y = space["base_y_min"] + (
        space["base_y_max"] - space["base_y_min"]
    ) * torch.sigmoid(raw[7])
    base_angle = torch.remainder(raw[8], TWO_PI)
    params = torch.stack(
        [l1, links[0], links[1], links[2], s_ratio, bar, base_x, base_y, base_angle]
    )

    if phase_mode == "unordered":
        phases = torch.remainder(raw[MECHANISM_RAW_DIM:MECHANISM_RAW_DIM + 3], TWO_PI)
    else:
        base_phase = raw[MECHANISM_RAW_DIM]
        gaps = torch.softmax(raw[MECHANISM_RAW_DIM + 1:MECHANISM_RAW_DIM + 4], dim=0) * TWO_PI
        phases = torch.stack(
            [base_phase, base_phase + gaps[0], base_phase + gaps[0] + gaps[1]]
        )
        phases = torch.remainder(phases * crank_direction_sign(args), TWO_PI)
    return params, phases


def normalized_parameter_vector(candidate: Dict[str, Any]) -> np.ndarray:
    values = np.asarray(candidate["parameters"], dtype=float)
    scale = max(float(candidate.get("target_scale", 1.0)), 1e-9)
    centroid_x = float(candidate.get("target_centroid_x", 0.0))
    centroid_y = float(candidate.get("target_centroid_y", 0.0))
    return np.asarray(
        [
            values[0] / scale, values[1] / scale, values[2] / scale, values[3] / scale,
            values[4], values[5] / scale,
            (values[6] - centroid_x) / scale,
            (values[7] - centroid_y) / scale,
            math.sin(values[8]), math.cos(values[8]),
        ],
        dtype=float,
    )


# ======================
# ===== TARGET INPUT =====
# ======================
def parse_targets_file(path: Path) -> List[Tuple[str, np.ndarray]]:
    frame = pd.read_csv(path)
    normalized = {str(column).strip().lower(): column for column in frame.columns}
    alternatives = [
        ("x1", "y1", "x2", "y2", "x3", "y3"),
        (
            "target_x1",
            "target_y1",
            "target_x2",
            "target_y2",
            "target_x3",
            "target_y3",
        ),
    ]
    selected: Optional[Tuple[str, ...]] = None
    for names in alternatives:
        if all(name in normalized for name in names):
            selected = names
            break
    if selected is None:
        if frame.shape[1] < 6:
            raise ValueError("Target CSV must contain at least six numeric columns")
        columns = list(frame.columns[:6])
    else:
        columns = [normalized[name] for name in selected]

    label_column = None
    for candidate in ("label", "name", "target_id", "id"):
        if candidate in normalized:
            label_column = normalized[candidate]
            break

    results: List[Tuple[str, np.ndarray]] = []
    for index, row in frame.iterrows():
        values = pd.to_numeric(row[columns], errors="raise").to_numpy(dtype=float)
        label = str(row[label_column]) if label_column is not None else f"target_{index + 1:04d}"
        results.append((sanitize_label(label), values))
    return results


def _collect_targets(args: argparse.Namespace) -> List[Tuple[str, np.ndarray]]:
    if args.targets is not None:
        return [("target_0001", np.asarray(args.targets, dtype=float))]
    if args.targets_file:
        return parse_targets_file(Path(args.targets_file))
    if args.demo:
        return [("demo", np.asarray([-5.5, 2.0, -3.0, 5.5, 0.0, 3.0], dtype=float))]

    if sys.stdin.isatty():
        print("Enter x1 y1 x2 y2 x3 y3, separated by spaces:")
        entered = input("> ").strip().replace(",", " ")
        parts = [part for part in entered.split() if part]
        if len(parts) != 6:
            raise ValueError("Exactly six numbers are required")
        return [("interactive", np.asarray([float(part) for part in parts], dtype=float))]
    raise ValueError("Provide --targets, --targets_file, or --demo")


def collect_targets(args: argparse.Namespace) -> List[Tuple[str, np.ndarray]]:
    targets = _collect_targets(args)
    if has_pose_targets(args) and len(targets) != 1:
        raise ValueError("Orientation arguments require one target triple per run; prepare separate OMTS runs for different tasks")
    return targets


# ======================
# ===== INITIAL PROPOSALS =====
# ======================
@torch.no_grad()
def predict_initial_params(
    role: ModelRole,
    target: torch.Tensor,
    args: argparse.Namespace,
) -> torch.Tensor:
    target32 = target.to(device=next(role.model.parameters()).device, dtype=torch.float32)
    predicted = role.model(target32[None, :])[0]
    predicted = torch.nan_to_num(predicted, nan=1.0, posinf=1.0, neginf=1.0)
    return project_proposal_parameters(
        predicted.to(device=target.device, dtype=target.dtype), target, args
    )


@torch.no_grad()
def seed_target_phases(
    params: torch.Tensor,
    target: torch.Tensor,
    branch_sign: float,
    steps: int,
    args: Optional[argparse.Namespace] = None,
) -> torch.Tensor:
    theta = torch.linspace(
        0.0, TWO_PI, int(steps) + 1,
        dtype=params.dtype, device=params.device,
    )[:-1]
    simulation = simulate_four_bar(params[None, :], theta, branch_sign)
    targets_xy = target.reshape(3, 2)
    squared = (
        (simulation["Px"][0][None, :] - targets_xy[:, 0, None]).square()
        + (simulation["Py"][0][None, :] - targets_xy[:, 1, None]).square()
    )
    if args is not None and has_pose_targets(args):
        desired = torch.deg2rad(torch.as_tensor(args.target_orientations_deg, dtype=params.dtype, device=params.device))
        actual = orientation_angles(simulation)[0]
        scale = target_design_space(target, args)["scale"]
        squared = squared + scale.square() * torch.sin((actual[None, :] - desired[:, None]) / 2).square()
    squared = torch.where(
        simulation["valid"][0][None, :],
        squared,
        torch.full_like(squared, INVALID_DISTANCE**2),
    )
    return theta[squared.argmin(dim=1)]


def build_starts(
    models: Sequence[ModelRole],
    target: torch.Tensor,
    args: argparse.Namespace,
    target_index: int,
) -> List[StartSpec]:
    branches = {
        "negative": (-1.0,), "positive": (1.0,), "both": (-1.0, 1.0),
    }[args.branches]
    starts: List[StartSpec] = []
    counter = 0
    for role_index, role in enumerate(models):
        initial_params = predict_initial_params(role, target, args)
        profile_names = (role.profile,) if args.profile_matrix == "paired" else tuple(PROFILES)
        for profile_index, profile_name in enumerate(profile_names):
            for branch_sign in branches:
                phases = seed_target_phases(
                    initial_params, target, branch_sign, args.seed_phase_steps, args
                )
                raw_base = encode_refinement_variables(
                    initial_params, phases, target, args.phase_mode, args
                )
                for perturbation_index in range(args.perturbations_per_model + 1):
                    counter += 1
                    generator = torch.Generator(device="cpu")
                    generator.manual_seed(
                        args.seed + target_index * 1_000_000 + role_index * 100_000
                        + profile_index * 10_000 + int((branch_sign + 1.0) * 1000)
                        + perturbation_index
                    )
                    raw = raw_base.detach().clone()
                    if perturbation_index > 0:
                        noise = torch.randn(raw.shape, generator=generator, dtype=torch.float64)
                        noise = noise.to(device=raw.device, dtype=raw.dtype)
                        raw[:MECHANISM_RAW_DIM] += (
                            float(args.parameter_noise) * noise[:MECHANISM_RAW_DIM]
                        )
                        phase_sigma = math.radians(args.phase_noise_deg)
                        phase_count = 3 if args.phase_mode == "unordered" else 4
                        raw[MECHANISM_RAW_DIM:MECHANISM_RAW_DIM + phase_count] += (
                            phase_sigma
                            * noise[MECHANISM_RAW_DIM:MECHANISM_RAW_DIM + phase_count]
                        )
                    decoded_params, decoded_phases = decode_refinement_variables(
                        raw, target, args.phase_mode, args
                    )
                    starts.append(
                        StartSpec(
                            candidate_id=f"start_{counter:03d}",
                            model_role=role.role,
                            profile=profile_name,
                            checkpoint_variant=role.checkpoint_variant,
                            checkpoint_epoch=role.checkpoint_epoch,
                            branch_sign=branch_sign,
                            perturbation_index=perturbation_index,
                            raw_initial=raw,
                            initial_params=decoded_params.detach(),
                            initial_phases=decoded_phases.detach(),
                        )
                    )
    return starts


# ======================
# ===== OBJECTIVE =====
# ======================
def transmission_objective_components(
    target_q: torch.Tensor,
    global_q: torch.Tensor,
    args: argparse.Namespace,
) -> Dict[str, torch.Tensor]:
    q_target = torch.tensor(
        math.sin(math.radians(args.target_transmission_deg)) ** 2,
        dtype=target_q.dtype, device=target_q.device,
    )
    target_shortfall = torch.relu(q_target - target_q)
    target_mean_penalty = target_shortfall.square().mean()
    target_softmin_q = normalized_softmin(target_q, args.worst_target_temperature)
    target_worst_penalty = torch.relu(q_target - target_softmin_q).square()
    target_penalty = (
        (1.0 - float(args.worst_target_focus)) * target_mean_penalty
        + float(args.worst_target_focus) * target_worst_penalty
    )

    q_global_floor = torch.tensor(
        math.sin(math.radians(args.global_transmission_floor_deg)) ** 2,
        dtype=global_q.dtype, device=global_q.device,
    )
    global_shortfall = torch.relu(q_global_floor - global_q).square()
    top_count = max(1, int(math.ceil(args.global_top_fraction * global_q.numel())))
    global_top_penalty = torch.topk(global_shortfall, k=top_count).values.mean()
    global_softmin_q = normalized_softmin(global_q, args.global_min_temperature)
    global_min_penalty = torch.relu(q_global_floor - global_softmin_q).square()
    global_penalty = (
        (1.0 - float(args.global_min_focus)) * global_top_penalty
        + float(args.global_min_focus) * global_min_penalty
    )
    return {
        "target_penalty": target_penalty,
        "target_mean_penalty": target_mean_penalty,
        "target_worst_penalty": target_worst_penalty,
        "target_softmin_q": target_softmin_q,
        "global_penalty": global_penalty,
        "global_top_penalty": global_top_penalty,
        "global_min_penalty": global_min_penalty,
        "global_softmin_q": global_softmin_q,
    }


def compactness_terms(
    params: torch.Tensor,
    simulation: Dict[str, torch.Tensor],
    target: torch.Tensor,
    args: argparse.Namespace,
) -> Dict[str, torch.Tensor]:
    space = target_design_space(target, args)
    scale = space["scale"].clamp_min(1e-9)
    centroid = space["centroid"]
    links = params[:4]
    max_link_ratio = links.max() / scale
    total_link_ratio = links.sum() / scale
    bar_ratio = params[5] / scale

    moving_x = torch.cat(
        [simulation["Ax"][0], simulation["Bx"][0], simulation["Px"][0]], dim=0
    )
    moving_y = torch.cat(
        [simulation["Ay"][0], simulation["By"][0], simulation["Py"][0]], dim=0
    )
    width = moving_x.max() - moving_x.min()
    height = moving_y.max() - moving_y.min()
    sweep_area_ratio = (width * height) / scale.square()
    sweep_diagonal_ratio = torch.sqrt(width.square() + height.square()) / scale
    sweep_radius_ratio = torch.sqrt(
        (moving_x - centroid[0]).square() + (moving_y - centroid[1]).square()
    ).max() / scale

    path_width = simulation["Px"][0].max() - simulation["Px"][0].min()
    path_height = simulation["Py"][0].max() - simulation["Py"][0].min()
    path_area_ratio = (path_width * path_height) / scale.square()

    def excess(value: torch.Tensor, limit: float) -> torch.Tensor:
        return smooth_positive_part(value - float(limit), args.compactness_softness)

    penalty = (
        excess(max_link_ratio, args.compactness_max_link_ratio).square()
        + 0.20 * excess(total_link_ratio, args.compactness_total_link_ratio).square()
        + 0.35 * excess(sweep_radius_ratio, args.compactness_sweep_radius_ratio).square()
        + 0.03 * excess(sweep_area_ratio, args.compactness_sweep_area_ratio).square()
        + 0.10 * excess(bar_ratio, args.compactness_bar_ratio).square()
    )
    score = (
        0.35 * max_link_ratio
        + 0.08 * total_link_ratio
        + 0.08 * bar_ratio
        + 0.25 * sweep_radius_ratio
        + 0.12 * sweep_diagonal_ratio
        + 0.02 * torch.sqrt(sweep_area_ratio.clamp_min(0.0))
    )
    return {
        "penalty": penalty,
        "score": score,
        "max_link_ratio": max_link_ratio,
        "total_link_ratio": total_link_ratio,
        "bar_length_ratio": bar_ratio,
        "sweep_width_ratio": width / scale,
        "sweep_height_ratio": height / scale,
        "sweep_area_ratio": sweep_area_ratio,
        "sweep_diagonal_ratio": sweep_diagonal_ratio,
        "sweep_radius_ratio": sweep_radius_ratio,
        "path_area_ratio": path_area_ratio,
    }


def robustness_terms(
    params: torch.Tensor,
    global_sim: Dict[str, torch.Tensor],
    constraints: Dict[str, torch.Tensor],
    target_scale: torch.Tensor,
    args: argparse.Namespace,
) -> Dict[str, torch.Tensor]:
    scale = target_scale.clamp_min(1e-9)
    assembly_margin = torch.minimum(
        torch.minimum(global_sim["full_outer_margin"][0], global_sim["full_inner_margin"][0]),
        global_sim["full_center_margin"][0],
    )
    assembly_margin_ratio = assembly_margin / scale
    grashof_margin_ratio = constraints["grashof_margin"][0] / scale
    crank_margin_ratio = constraints["crank_margin_min"][0] / scale
    follower_margin_ratio = constraints["follower_margin"][0] / scale
    assembly_shortfall = torch.relu(
        torch.tensor(float(args.assembly_margin_ratio), dtype=params.dtype, device=params.device)
        - assembly_margin_ratio
    )
    grashof_shortfall = torch.relu(
        torch.tensor(float(args.grashof_margin_ratio), dtype=params.dtype, device=params.device)
        - grashof_margin_ratio
    )
    class_required_ratio = torch.maximum(
        torch.tensor(float(args.class_margin_ratio), dtype=params.dtype, device=params.device),
        torch.tensor(float(args.class_margin), dtype=params.dtype, device=params.device) / scale,
    )
    crank_shortfall = torch.relu(class_required_ratio - crank_margin_ratio)
    if args.enforce_follower_not_longest:
        follower_shortfall = torch.relu(class_required_ratio - follower_margin_ratio)
    else:
        follower_shortfall = torch.zeros_like(follower_margin_ratio)
    penalty = (
        assembly_shortfall.square()
        + grashof_shortfall.square()
        + crank_shortfall.square()
        + follower_shortfall.square()
    )
    return {
        "penalty": penalty,
        "assembly_margin": assembly_margin,
        "assembly_margin_ratio": assembly_margin_ratio,
        "grashof_margin_ratio": grashof_margin_ratio,
        "crank_margin_ratio": crank_margin_ratio,
        "follower_margin_ratio": follower_margin_ratio,
        "class_required_ratio": class_required_ratio,
    }


def has_pose_targets(args: argparse.Namespace) -> bool:
    return getattr(args, "target_orientations_deg", None) is not None


def pose_tolerances(args: argparse.Namespace) -> List[float]:
    return getattr(args, "orientation_tolerances_deg", None) or [5.0, 5.0, 5.0]


def acquisition_key(metrics: Dict[str, torch.Tensor]) -> tuple:
    mean = float(metrics["mean_error"].detach().item())
    worst = float(metrics["max_error"].detach().item())
    if "orientation_feasible" not in metrics:
        return mean, worst
    if bool(metrics["orientation_feasible"].item()):
        return 0, mean, worst
    return 1, float(metrics["pose_acquisition_loss"].detach().item()), worst


def objective_terms(
    raw: torch.Tensor,
    raw_reference: torch.Tensor,
    target: torch.Tensor,
    branch_sign: float,
    phase_mode: str,
    profile: RefinementProfile,
    stage: str,
    args: argparse.Namespace,
    global_theta: torch.Tensor,
    mean_budget: Optional[torch.Tensor] = None,
    point_budget: Optional[torch.Tensor] = None,
) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
    params, phases = decode_refinement_variables(raw, target, phase_mode, args)
    phase_sim = simulate_four_bar(params[None, :], phases, branch_sign)
    target_xy = target.reshape(3, 2)
    matched = torch.stack([phase_sim["Px"][0], phase_sim["Py"][0]], dim=1)
    error_vectors = matched - target_xy
    squared_errors = error_vectors.square().sum(dim=1)
    errors = torch.sqrt(squared_errors + DISTANCE_SQ_FLOOR)
    position_loss = squared_errors.mean() + 0.5 * squared_errors.max()

    global_sim = simulate_four_bar(params[None, :], global_theta, branch_sign)
    transmission = transmission_objective_components(
        phase_sim["transmission_q"][0], global_sim["transmission_q"][0], args
    )
    space = target_design_space(target, args)
    constraints = mechanism_constraint_tensors(params[None, :], space["scale"], args)
    length_scale = params[:4].max().clamp_min(1.0)
    assembly_violation = global_sim["full_cycle_assembly_violation"][0] / length_scale
    grashof_violation = constraints["grashof_violation"][0] / length_scale
    class_violation = constraints["class_margin_violation"][0] / length_scale
    target_invalid_fraction = 1.0 - phase_sim["valid"][0].float().mean()
    robustness = robustness_terms(params, global_sim, constraints, space["scale"], args)
    compactness = compactness_terms(params, global_sim, target, args)

    base_physical_penalty = (
        args.assembly_weight * assembly_violation.square()
        + args.grashof_weight * grashof_violation.square()
        + args.class_weight * class_violation.square().mean()
        + args.target_validity_weight * target_invalid_fraction.square()
    )
    # Stage A should discover the best feasible path without prematurely
    # steering the shared reference toward large-margin geometry. Robustness is
    # introduced in Stage B, where it competes transparently with transmission
    # and compactness under the common path budget.
    robustness_weighted = (
        torch.zeros((), dtype=raw.dtype, device=raw.device)
        if stage == "accuracy"
        else args.robustness_weight * robustness["penalty"]
    )
    physical_penalty = base_physical_penalty + robustness_weighted
    drift_penalty = args.drift_weight * (
        raw[:MECHANISM_RAW_DIM] - raw_reference[:MECHANISM_RAW_DIM]
    ).square().mean()

    path_constraint = torch.zeros((), dtype=raw.dtype, device=raw.device)
    point_guard = torch.zeros((), dtype=raw.dtype, device=raw.device)
    compactness_weighted = torch.zeros((), dtype=raw.dtype, device=raw.device)
    if stage == "accuracy":
        objective = (
            position_loss
            + profile.stage_a_target_transmission_weight * transmission["target_penalty"]
            + profile.stage_a_global_transmission_weight * transmission["global_penalty"]
            + physical_penalty
            + drift_penalty
        )
    elif stage == "tradeoff":
        if mean_budget is None or point_budget is None:
            raise ValueError("Tradeoff stage requires mean and point budgets")
        path_excess = torch.relu(errors.mean() - mean_budget)
        point_excess = torch.relu(errors - point_budget)
        path_constraint = profile.path_constraint_weight * path_excess.square()
        point_guard = profile.point_guard_weight * point_excess.square().mean()
        compactness_weighted = (
            float(args.compactness_weight) * profile.compactness_weight
            * compactness["penalty"]
        )
        objective = (
            profile.residual_position_weight * position_loss
            + path_constraint + point_guard
            + profile.target_transmission_weight * transmission["target_penalty"]
            + profile.global_transmission_weight * transmission["global_penalty"]
            + compactness_weighted
            + physical_penalty + drift_penalty
        )
    else:
        raise ValueError(f"Unknown stage: {stage}")

    pose = None
    if has_pose_targets(args):
        pose = orientation_metrics(phase_sim, args.target_orientations_deg, pose_tolerances(args))
        # Translate angular mismatch into a scale-relative geometric loss.
        # The guard keeps Stage B from trading away a hard orientation tolerance.
        angular_loss = space["scale"].square() * pose["penalty"][0]
        tolerance = torch.as_tensor(pose_tolerances(args), dtype=raw.dtype, device=raw.device)
        excess = torch.relu(torch.deg2rad(pose["errors_deg"][0] - tolerance))
        angular_guard = 100.0 * space["scale"].square() * excess.square().mean()
        objective = objective + angular_loss
        if stage == "tradeoff":
            objective = objective + angular_guard

    target_q = phase_sim["transmission_q"][0]
    target_angles = acute_angle_from_q(target_q)
    global_q = global_sim["transmission_q"][0]
    metrics = {
        "params": params, "phases": phases, "matched": matched, "errors": errors,
        "mean_error": errors.mean(), "max_error": errors.max(),
        "position_loss": position_loss, "target_q": target_q,
        "target_angles": target_angles, "target_angle_mean": target_angles.mean(),
        "target_angle_min": target_angles.min(),
        "target_angle_softmin": acute_angle_from_q(transmission["target_softmin_q"]),
        "target_tx_penalty": transmission["target_penalty"],
        "target_tx_mean_penalty": transmission["target_mean_penalty"],
        "target_tx_worst_penalty": transmission["target_worst_penalty"],
        "global_tx_penalty": transmission["global_penalty"],
        "global_tx_top_penalty": transmission["global_top_penalty"],
        "global_tx_min_penalty": transmission["global_min_penalty"],
        "global_angle_min": acute_angle_from_q(global_q.min()),
        "global_angle_softmin": acute_angle_from_q(transmission["global_softmin_q"]),
        "assembly_violation": assembly_violation,
        "full_cycle_valid": global_sim["full_cycle_valid"][0],
        "grashof_violation": grashof_violation,
        "grashof_ok": constraints["grashof_ok"][0],
        "exact_class": constraints["exact_class"][0],
        "crank_margin_min": constraints["crank_margin_min"][0],
        "follower_margin": constraints["follower_margin"][0],
        "class_margin_violation": class_violation.mean(),
        "target_invalid_fraction": target_invalid_fraction,
        "robustness_penalty": robustness["penalty"],
        "robustness_weighted": robustness_weighted,
        "assembly_margin_ratio": robustness["assembly_margin_ratio"],
        "grashof_margin_ratio": robustness["grashof_margin_ratio"],
        "crank_margin_ratio": robustness["crank_margin_ratio"],
        "follower_margin_ratio": robustness["follower_margin_ratio"],
        "compactness_penalty": compactness["penalty"],
        "compactness_weighted": compactness_weighted,
        "compactness_score": compactness["score"],
        "max_link_ratio": compactness["max_link_ratio"],
        "total_link_ratio": compactness["total_link_ratio"],
        "sweep_radius_ratio": compactness["sweep_radius_ratio"],
        "sweep_area_ratio": compactness["sweep_area_ratio"],
        "physical_penalty": physical_penalty,
        "path_constraint": path_constraint, "point_guard": point_guard,
        "objective": objective,
    }
    if pose is not None:
        metrics.update(
            orientation_feasible=pose["feasible"][0],
            orientation_errors_deg=pose["errors_deg"][0],
            max_orientation_error_deg=pose["max_error_deg"][0],
            orientation_loss=angular_loss,
            pose_acquisition_loss=position_loss + angular_loss,
        )
    return objective, metrics


def metrics_are_physical(metrics: Dict[str, torch.Tensor]) -> bool:
    return bool(
        torch.isfinite(metrics["objective"]).item()
        and metrics["full_cycle_valid"].item()
        and metrics["grashof_ok"].item()
        and metrics["exact_class"].item()
        and metrics["target_invalid_fraction"].item() <= 1e-9
        and metrics["assembly_violation"].item() <= 1e-7
        and metrics["grashof_violation"].item() <= 1e-7
    )


def candidate_score_from_metrics(
    metrics: Dict[str, torch.Tensor],
    profile: RefinementProfile,
) -> float:
    return float(
        metrics["mean_error"].detach().item()
        + 0.35 * metrics["max_error"].detach().item()
        + profile.ranking_transmission_weight * metrics["target_tx_penalty"].detach().item()
        + profile.ranking_global_weight * metrics["global_tx_penalty"].detach().item()
        + profile.ranking_compactness_weight * metrics["compactness_score"].detach().item()
        + 10.0 * metrics["robustness_penalty"].detach().item()
        + 1000.0 * metrics["physical_penalty"].detach().item()
    )


def history_row(
    start: StartSpec,
    stage: str,
    step: int,
    lr: float,
    metrics: Dict[str, torch.Tensor],
    physical: bool,
    budget_feasible: Optional[bool],
) -> Dict[str, Any]:
    row = {
        "candidate_id": start.candidate_id,
        "model_role": start.model_role,
        "profile": start.profile,
        "branch_sign": start.branch_sign,
        "perturbation_index": start.perturbation_index,
        "stage": stage,
        "step": step,
        "lr": lr,
        "objective": metrics["objective"].detach().item(),
        "l1": metrics["params"][0].detach().item(),
        "mean_error": metrics["mean_error"].detach().item(),
        "max_error": metrics["max_error"].detach().item(),
        "target_angle_mean_deg": metrics["target_angle_mean"].detach().item(),
        "target_angle_min_deg": metrics["target_angle_min"].detach().item(),
        "target_angle_softmin_deg": metrics["target_angle_softmin"].detach().item(),
        "target_transmission_penalty": metrics["target_tx_penalty"].detach().item(),
        "target_transmission_mean_penalty": metrics["target_tx_mean_penalty"].detach().item(),
        "target_transmission_worst_penalty": metrics["target_tx_worst_penalty"].detach().item(),
        "global_angle_min_deg": metrics["global_angle_min"].detach().item(),
        "global_angle_softmin_deg": metrics["global_angle_softmin"].detach().item(),
        "global_transmission_penalty": metrics["global_tx_penalty"].detach().item(),
        "compactness_score": metrics["compactness_score"].detach().item(),
        "max_link_ratio": metrics["max_link_ratio"].detach().item(),
        "sweep_radius_ratio": metrics["sweep_radius_ratio"].detach().item(),
        "assembly_margin_ratio": metrics["assembly_margin_ratio"].detach().item(),
        "grashof_margin_ratio": metrics["grashof_margin_ratio"].detach().item(),
        "crank_margin_ratio": metrics["crank_margin_ratio"].detach().item(),
        "assembly_violation": metrics["assembly_violation"].detach().item(),
        "grashof_violation": metrics["grashof_violation"].detach().item(),
        "class_margin_violation": metrics["class_margin_violation"].detach().item(),
        "physical_feasible": physical,
        "budget_feasible": budget_feasible if budget_feasible is not None else "",
    }
    if "orientation_feasible" in metrics:
        row["orientation_acceptable"] = bool(metrics["orientation_feasible"].item())
        row["max_orientation_error_deg"] = float(metrics["max_orientation_error_deg"].detach().item())
    return row

def acquire_start_path(
    start: StartSpec,
    target: torch.Tensor,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    """Run Stage A only and retain the best physically valid path for one start."""
    profile = PROFILES[start.profile]
    raw_reference = start.raw_initial.detach().clone()
    raw = nn.Parameter(raw_reference.clone())
    global_theta = torch.linspace(
        0.0,
        TWO_PI,
        args.optimization_global_steps + 1,
        dtype=target.dtype,
        device=target.device,
    )[:-1]
    history: List[Dict[str, Any]] = []

    best_physical_state: Optional[torch.Tensor] = None
    best_physical_key = (float("inf"), float("inf"))
    best_any_state = raw.detach().clone()
    best_any_objective = float("inf")

    def consider(metrics: Dict[str, torch.Tensor]) -> bool:
        nonlocal best_physical_state, best_physical_key
        nonlocal best_any_state, best_any_objective
        objective_value = float(metrics["objective"].detach().item())
        if math.isfinite(objective_value) and objective_value < best_any_objective:
            best_any_objective = objective_value
            best_any_state = raw.detach().clone()
        physical = metrics_are_physical(metrics)
        if physical:
            key = acquisition_key(metrics)
            if key < best_physical_key:
                best_physical_key = key
                best_physical_state = raw.detach().clone()
        return physical

    with torch.no_grad():
        _, initial_metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "accuracy", args, global_theta
        )
        physical = consider(initial_metrics)
        history.append(
            history_row(start, "initial", 0, 0.0, initial_metrics, physical, None)
        )

    optimizer = torch.optim.Adam([raw], lr=args.adam_lr)
    for step in range(1, args.adam_accuracy_steps + 1):
        optimizer.zero_grad(set_to_none=True)
        objective, metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "accuracy", args, global_theta
        )
        if not torch.isfinite(objective):
            break
        physical = consider(metrics)
        objective.backward()
        if raw.grad is None or not torch.isfinite(raw.grad).all():
            break
        torch.nn.utils.clip_grad_norm_([raw], args.grad_clip)
        optimizer.step()
        if step == 1 or step % args.history_interval == 0 or step == args.adam_accuracy_steps:
            history.append(
                history_row(
                    start, "accuracy", step, optimizer.param_groups[0]["lr"],
                    metrics, physical, None
                )
            )

    with torch.no_grad():
        _, final_metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "accuracy", args, global_theta
        )
        consider(final_metrics)

    acquired_raw = best_physical_state if best_physical_state is not None else best_any_state
    raw.data.copy_(acquired_raw)
    with torch.no_grad():
        _, acquired_metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "accuracy", args, global_theta
        )

    result = {
        "start": start,
        "raw_reference": raw_reference,
        "raw_acquired": acquired_raw.detach().clone(),
        "history": history,
        "acquired_physical": metrics_are_physical(acquired_metrics),
        "acquired_mean_error": float(acquired_metrics["mean_error"].detach().item()),
        "acquired_max_error": float(acquired_metrics["max_error"].detach().item()),
        "acquired_errors": acquired_metrics["errors"].detach().clone(),
        "acquired_target_angle_min_deg": float(acquired_metrics["target_angle_min"].detach().item()),
        "acquired_global_angle_min_deg": float(acquired_metrics["global_angle_min"].detach().item()),
    }
    if has_pose_targets(args):
        result["acquired_pose_key"] = acquisition_key(acquired_metrics)
        result["acquired_orientation_acceptable"] = bool(acquired_metrics["orientation_feasible"].item())
    return result


def build_shared_path_reference(
    acquisitions: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    """Choose one common Stage-A path reference and budget for every start."""
    if not acquisitions:
        raise ValueError("No Stage-A acquisitions were produced")
    physical = [item for item in acquisitions if item["acquired_physical"]]
    pool = physical if physical else list(acquisitions)
    if has_pose_targets(args):
        compatible = [item for item in pool if item["acquired_orientation_acceptable"]]
        pool = compatible or pool
    reference = min(
        pool,
        key=lambda item: item["acquired_pose_key"] if has_pose_targets(args) else (item["acquired_mean_error"], item["acquired_max_error"]),
    )
    start: StartSpec = reference["start"]
    reference_errors = reference["acquired_errors"].detach().clone()
    shared_mean_budget = min(
        float(args.max_mean_error),
        float(reference["acquired_mean_error"] + args.shared_mean_allowance),
    )
    shared_point_budgets = torch.minimum(
        reference_errors + float(args.shared_point_allowance),
        torch.full_like(reference_errors, float(args.max_point_error)),
    )
    return {
        "basis": "best_physical_stage_a" if physical else "best_available_stage_a",
        "reference_candidate_id": start.candidate_id,
        "reference_model_role": start.model_role,
        "reference_profile": start.profile,
        "reference_branch_sign": start.branch_sign,
        "reference_perturbation_index": start.perturbation_index,
        "reference_acquired_mean_error": float(reference["acquired_mean_error"]),
        "reference_acquired_max_error": float(reference["acquired_max_error"]),
        "reference_acquired_errors": reference_errors.detach().cpu().tolist(),
        "shared_mean_budget": shared_mean_budget,
        "shared_point_budgets": shared_point_budgets.detach().cpu().tolist(),
        "max_mean_error": float(args.max_mean_error),
        "max_point_error": float(args.max_point_error),
        "shared_mean_allowance": float(args.shared_mean_allowance),
        "shared_point_allowance": float(args.shared_point_allowance),
        "physical_stage_a_count": len(physical),
        "total_stage_a_count": len(acquisitions),
    }


def optimize_start_with_shared_budget(
    acquired: Dict[str, Any],
    shared_reference: Dict[str, Any],
    target: torch.Tensor,
    args: argparse.Namespace,
    output_dir: Path,
) -> Dict[str, Any]:
    """Run Stage B using the same path-quality budget for all starts."""
    start: StartSpec = acquired["start"]
    profile = PROFILES[start.profile]
    raw_reference = acquired["raw_reference"].detach().clone()
    raw = nn.Parameter(acquired["raw_acquired"].detach().clone())
    global_theta = torch.linspace(
        0.0, TWO_PI, args.optimization_global_steps + 1,
        dtype=target.dtype, device=target.device
    )[:-1]
    mean_budget = torch.tensor(
        shared_reference["shared_mean_budget"], dtype=target.dtype, device=target.device
    )
    point_budget = torch.tensor(
        shared_reference["shared_point_budgets"], dtype=target.dtype, device=target.device
    )
    history: List[Dict[str, Any]] = list(acquired["history"])

    best_tradeoff_state: Optional[torch.Tensor] = None
    best_tradeoff_score = float("inf")
    best_physical_state: Optional[torch.Tensor] = (
        acquired["raw_acquired"].detach().clone() if acquired["acquired_physical"] else None
    )
    best_physical_key = (
        (acquired["acquired_mean_error"], acquired["acquired_max_error"])
        if acquired["acquired_physical"] else (float("inf"), float("inf"))
    )
    if has_pose_targets(args) and acquired["acquired_physical"]:
        best_physical_key = acquired["acquired_pose_key"]
    best_any_state = acquired["raw_acquired"].detach().clone()
    best_any_objective = float("inf")

    def consider(metrics: Dict[str, torch.Tensor]) -> Tuple[bool, bool]:
        nonlocal best_tradeoff_state, best_tradeoff_score
        nonlocal best_physical_state, best_physical_key
        nonlocal best_any_state, best_any_objective
        objective_value = float(metrics["objective"].detach().item())
        if math.isfinite(objective_value) and objective_value < best_any_objective:
            best_any_objective = objective_value
            best_any_state = raw.detach().clone()
        physical = metrics_are_physical(metrics)
        budget_feasible = bool(
            metrics["mean_error"].detach().item() <= mean_budget.item() + 1e-9
            and torch.all(metrics["errors"].detach() <= point_budget + 1e-9).item()
        )
        if has_pose_targets(args):
            budget_feasible = budget_feasible and bool(metrics["orientation_feasible"].item())
        if physical:
            key = acquisition_key(metrics)
            if key < best_physical_key:
                best_physical_key = key
                best_physical_state = raw.detach().clone()
            if budget_feasible:
                score = candidate_score_from_metrics(metrics, profile)
                if score < best_tradeoff_score:
                    best_tradeoff_score = score
                    best_tradeoff_state = raw.detach().clone()
        return physical, budget_feasible

    with torch.no_grad():
        _, starting_metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "tradeoff", args, global_theta, mean_budget, point_budget
        )
        physical, budget_feasible = consider(starting_metrics)
        history.append(
            history_row(
                start, "shared_budget_start", 0, 0.0, starting_metrics,
                physical, budget_feasible
            )
        )

    optimizer = torch.optim.Adam([raw], lr=args.adam_lr * 0.5)
    for step in range(1, args.adam_tradeoff_steps + 1):
        optimizer.zero_grad(set_to_none=True)
        objective, metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "tradeoff", args, global_theta, mean_budget, point_budget
        )
        if not torch.isfinite(objective):
            break
        physical, budget_feasible = consider(metrics)
        objective.backward()
        if raw.grad is None or not torch.isfinite(raw.grad).all():
            break
        torch.nn.utils.clip_grad_norm_([raw], args.grad_clip)
        optimizer.step()
        if step == 1 or step % args.history_interval == 0 or step == args.adam_tradeoff_steps:
            history.append(
                history_row(
                    start, "tradeoff", step, optimizer.param_groups[0]["lr"],
                    metrics, physical, budget_feasible
                )
            )

    with torch.no_grad():
        _, final_metrics = objective_terms(
            raw, raw_reference, target, start.branch_sign, args.phase_mode,
            profile, "tradeoff", args, global_theta, mean_budget, point_budget
        )
        consider(final_metrics)

    if best_tradeoff_state is not None:
        raw.data.copy_(best_tradeoff_state)
    elif best_physical_state is not None:
        raw.data.copy_(best_physical_state)
    else:
        raw.data.copy_(best_any_state)

    if args.lbfgs_steps > 0:
        lbfgs = torch.optim.LBFGS(
            [raw], lr=args.lbfgs_lr, max_iter=args.lbfgs_steps,
            max_eval=max(args.lbfgs_steps * 2, args.lbfgs_steps + 5),
            tolerance_grad=1e-10 if raw.dtype == torch.float64 else 1e-7,
            tolerance_change=1e-12 if raw.dtype == torch.float64 else 1e-9,
            history_size=min(50, max(10, args.lbfgs_steps)),
            line_search_fn="strong_wolfe",
        )

        def closure() -> torch.Tensor:
            lbfgs.zero_grad(set_to_none=True)
            objective, _ = objective_terms(
                raw, raw_reference, target, start.branch_sign, args.phase_mode,
                profile, "tradeoff", args, global_theta, mean_budget, point_budget
            )
            if torch.isfinite(objective):
                objective.backward()
            return objective

        try:
            lbfgs.step(closure)
            with torch.no_grad():
                _, polished_metrics = objective_terms(
                    raw, raw_reference, target, start.branch_sign, args.phase_mode,
                    profile, "tradeoff", args, global_theta, mean_budget, point_budget
                )
                physical, budget_feasible = consider(polished_metrics)
                history.append(
                    history_row(
                        start, "lbfgs", args.lbfgs_steps, args.lbfgs_lr,
                        polished_metrics, physical, budget_feasible
                    )
                )
        except (RuntimeError, ValueError) as exc:
            history.append({
                "candidate_id": start.candidate_id,
                "stage": "lbfgs_error",
                "step": 0,
                "error": str(exc),
            })

    if best_tradeoff_state is not None:
        selected_raw = best_tradeoff_state
        selection_reason = "best_shared_budget_tradeoff"
    elif best_physical_state is not None:
        selected_raw = best_physical_state
        selection_reason = "best_physical_path_no_shared_budget_tradeoff"
    else:
        selected_raw = best_any_state
        selection_reason = "best_available_objective"

    history_path = output_dir / f"history_{start.candidate_id}.csv"
    write_csv(history_path, history)
    return {
        "start": start,
        "raw_selected": selected_raw.detach().clone(),
        "raw_reference": raw_reference,
        "mean_budget": float(mean_budget.detach().item()),
        "point_budget": point_budget.detach().cpu().tolist(),
        "acquired_mean_error": float(acquired["acquired_mean_error"]),
        "acquired_errors": acquired["acquired_errors"].detach().cpu().tolist(),
        "shared_reference": shared_reference,
        "selection_reason": selection_reason,
        "history_path": str(history_path),
    }


# ======================
# ===== FINAL EVALUATION =====
# ======================
@torch.no_grad()
def evaluate_selected_candidate(
    optimized: Dict[str, Any],
    target: torch.Tensor,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    start: StartSpec = optimized["start"]
    raw = optimized["raw_selected"].to(device=target.device, dtype=target.dtype)
    params, phases = decode_refinement_variables(raw, target, args.phase_mode, args)
    phase_sim = simulate_four_bar(params[None, :], phases, start.branch_sign)
    target_xy = target.reshape(3, 2)
    matched = torch.stack([phase_sim["Px"][0], phase_sim["Py"][0]], dim=1)
    errors = torch.linalg.vector_norm(matched - target_xy, dim=1)
    target_q = phase_sim["transmission_q"][0]
    target_angles = acute_angle_from_q(target_q)

    theta_dense = torch.linspace(
        0.0, TWO_PI, args.verification_steps + 1,
        dtype=target.dtype, device=target.device,
    )[:-1]
    dense = simulate_four_bar(params[None, :], theta_dense, start.branch_sign)
    q_dense = dense["transmission_q"][0]
    tx = transmission_objective_components(target_q, q_dense, args)
    space = target_design_space(target, args)
    constraints = mechanism_constraint_tensors(params[None, :], space["scale"], args)
    robustness = robustness_terms(params, dense, constraints, space["scale"], args)
    compactness = compactness_terms(params, dense, target, args)

    initial_params = start.initial_params.to(device=target.device, dtype=target.dtype)
    initial_phases = start.initial_phases.to(device=target.device, dtype=target.dtype)
    initial_phase_sim = simulate_four_bar(initial_params[None, :], initial_phases, start.branch_sign)
    initial_matched = torch.stack(
        [initial_phase_sim["Px"][0], initial_phase_sim["Py"][0]], dim=1
    )
    initial_errors = torch.linalg.vector_norm(initial_matched - target_xy, dim=1)
    initial_target_angles = acute_angle_from_q(initial_phase_sim["transmission_q"][0])
    initial_dense = simulate_four_bar(initial_params[None, :], theta_dense, start.branch_sign)
    initial_global_angle_min = acute_angle_from_q(initial_dense["transmission_q"][0].min())

    physical_feasible = bool(
        dense["full_cycle_valid"][0].item()
        and constraints["grashof_ok"][0].item()
        and constraints["exact_class"][0].item()
        and phase_sim["valid"][0].all().item()
    )
    mean_budget = float(optimized["mean_budget"])
    point_budget = np.asarray(optimized["point_budget"], dtype=float)
    errors_np = errors.cpu().numpy()
    budget_feasible = bool(
        errors.mean().item() <= mean_budget + 1e-9
        and np.all(errors_np <= point_budget + 1e-9)
    )

    q15 = math.sin(math.radians(args.global_transmission_floor_deg)) ** 2
    q35 = math.sin(math.radians(args.target_transmission_deg)) ** 2
    top_count = max(1, int(math.ceil(args.global_top_fraction * q_dense.numel())))
    global_shortfall = torch.relu(
        torch.tensor(q15, dtype=target.dtype, device=target.device) - q_dense
    ).square()
    accuracy_score = float(errors.mean().item() + 0.35 * errors.max().item())
    compact_score = float(compactness["score"].item())
    balanced_score = float(
        accuracy_score + 2.25 * tx["target_penalty"].item()
        + 0.35 * tx["global_penalty"].item()
        + args.ranking_compactness_weight * compact_score
        + 5.0 * robustness["penalty"].item()
    )
    transmission_score = float(
        0.20 * accuracy_score + tx["target_penalty"].item()
        + 0.15 * tx["global_penalty"].item()
        + 0.01 * compact_score
    )
    profile = PROFILES[start.profile]
    profile_score = float(
        accuracy_score
        + profile.ranking_transmission_weight * tx["target_penalty"].item()
        + profile.ranking_global_weight * tx["global_penalty"].item()
        + profile.ranking_compactness_weight * compact_score
        + 5.0 * robustness["penalty"].item()
    )

    curve = torch.stack([dense["Px"][0], dense["Py"][0]], dim=1).cpu().numpy()
    params_np = params.cpu().numpy()
    phases_np = phases.cpu().numpy()
    target_angles_np = target_angles.cpu().numpy()
    centroid = space["centroid"].cpu().numpy()

    record: Dict[str, Any] = {
        "candidate_id": start.candidate_id,
        "model_role": start.model_role,
        "profile": start.profile,
        "checkpoint_variant": start.checkpoint_variant,
        "checkpoint_epoch": start.checkpoint_epoch,
        "branch_sign": start.branch_sign,
        "perturbation_index": start.perturbation_index,
        "selection_reason": optimized["selection_reason"],
        "ground_link_mode": args.ground_link_mode,
        "follower_not_longest_enforced": bool(args.enforce_follower_not_longest),
        "physical_feasible": physical_feasible,
        "local_path_budget_feasible": budget_feasible,
        "path_budget_feasible": budget_feasible,
        "acquired_mean_error": float(optimized["acquired_mean_error"]),
        "acquired_error_1": float(optimized["acquired_errors"][0]),
        "acquired_error_2": float(optimized["acquired_errors"][1]),
        "acquired_error_3": float(optimized["acquired_errors"][2]),
        "initial_mean_error": float(initial_errors.mean().item()),
        "initial_max_error": float(initial_errors.max().item()),
        "initial_target_angle_min_deg": float(initial_target_angles.min().item()),
        "initial_global_angle_min_deg": float(initial_global_angle_min.item()),
        "initial_full_cycle_assembly": bool(initial_dense["full_cycle_valid"][0].item()),
        "mean_error_improvement": float(initial_errors.mean().item() - errors.mean().item()),
        "max_error_improvement": float(initial_errors.max().item() - errors.max().item()),
        "target_angle_min_change_deg": float(target_angles.min().item() - initial_target_angles.min().item()),
        "mean_error": float(errors.mean().item()),
        "max_error": float(errors.max().item()),
        "error_1": float(errors[0].item()), "error_2": float(errors[1].item()), "error_3": float(errors[2].item()),
        "target_angle_mean_deg": float(target_angles.mean().item()),
        "target_angle_min_deg": float(target_angles.min().item()),
        "target_angle_softmin_deg": float(acute_angle_from_q(tx["target_softmin_q"]).item()),
        "target_angle_1_deg": float(target_angles[0].item()),
        "target_angle_2_deg": float(target_angles[1].item()),
        "target_angle_3_deg": float(target_angles[2].item()),
        "target_transmission_penalty": float(tx["target_penalty"].item()),
        "target_transmission_mean_penalty": float(tx["target_mean_penalty"].item()),
        "target_transmission_worst_penalty": float(tx["target_worst_penalty"].item()),
        "global_angle_min_deg": float(acute_angle_from_q(q_dense.min()).item()),
        "global_angle_softmin_deg": float(acute_angle_from_q(tx["global_softmin_q"]).item()),
        "global_angle_mean_deg": float(acute_angle_from_q(q_dense).mean().item()),
        "global_below_floor_fraction": float((q_dense < q15).float().mean().item()),
        "global_below_target_fraction": float((q_dense < q35).float().mean().item()),
        "global_transmission_penalty": float(tx["global_penalty"].item()),
        "global_transmission_top_penalty": float(tx["global_top_penalty"].item()),
        "global_transmission_min_penalty": float(tx["global_min_penalty"].item()),
        "full_cycle_assembly": bool(dense["full_cycle_valid"][0].item()),
        "full_cycle_assembly_violation": float(dense["full_cycle_assembly_violation"][0].item()),
        "sampled_assembly_success": float(dense["valid"][0].float().mean().item()),
        "grashof_ok": bool(constraints["grashof_ok"][0].item()),
        "grashof_violation": float(constraints["grashof_violation"][0].item()),
        "grashof_margin": float(constraints["grashof_margin"][0].item()),
        "exact_mechanism_class": bool(constraints["exact_class"][0].item()),
        "crank_margin_min": float(constraints["crank_margin_min"][0].item()),
        "follower_margin": float(constraints["follower_margin"][0].item()),
        "assembly_margin_ratio": float(robustness["assembly_margin_ratio"].item()),
        "grashof_margin_ratio": float(robustness["grashof_margin_ratio"].item()),
        "crank_margin_ratio": float(robustness["crank_margin_ratio"].item()),
        "follower_margin_ratio": float(robustness["follower_margin_ratio"].item()),
        "robustness_penalty": float(robustness["penalty"].item()),
        "target_scale": float(space["scale"].item()),
        "target_centroid_x": float(centroid[0]),
        "target_centroid_y": float(centroid[1]),
        "max_link_ratio": float(compactness["max_link_ratio"].item()),
        "total_link_ratio": float(compactness["total_link_ratio"].item()),
        "bar_length_ratio": float(compactness["bar_length_ratio"].item()),
        "sweep_width_ratio": float(compactness["sweep_width_ratio"].item()),
        "sweep_height_ratio": float(compactness["sweep_height_ratio"].item()),
        "sweep_area_ratio": float(compactness["sweep_area_ratio"].item()),
        "sweep_diagonal_ratio": float(compactness["sweep_diagonal_ratio"].item()),
        "sweep_radius_ratio": float(compactness["sweep_radius_ratio"].item()),
        "path_area_ratio": float(compactness["path_area_ratio"].item()),
        "compactness_penalty": float(compactness["penalty"].item()),
        "compactness_score": compact_score,
        "mean_path_budget": mean_budget,
        "point_budget_1": float(point_budget[0]), "point_budget_2": float(point_budget[1]), "point_budget_3": float(point_budget[2]),
        "accuracy_score": accuracy_score, "balanced_score": balanced_score,
        "transmission_score": transmission_score, "profile_score": profile_score,
        "crank_direction": getattr(args, "crank_direction", "positive"),
        "parameters": params_np.tolist(), "phases_rad": phases_np.tolist(),
        "phases_deg": np.degrees(phases_np).tolist(),
        "target_points": target_xy.cpu().numpy().tolist(),
        "matched_points": matched.cpu().numpy().tolist(),
        "curve": curve, "dense_theta": theta_dense.cpu().numpy(),
        "dense_simulation": {key: value[0].cpu().numpy() for key, value in dense.items() if key in {
            "O2x", "O2y", "Ax", "Ay", "Bx", "By", "O4x", "O4y", "Px", "Py", "valid", "transmission_q"
        }},
        "phase_simulation": {key: value[0].cpu().numpy() for key, value in phase_sim.items() if key in {
            "O2x", "O2y", "Ax", "Ay", "Bx", "By", "O4x", "O4y", "Px", "Py", "valid", "transmission_q"
        }},
        "history_path": optimized["history_path"],
    }
    for name, value in zip(OUTPUT_PARAMETER_NAMES, params_np):
        record[name] = float(value)
    for index, value in enumerate(phases_np, start=1):
        record[f"phase_{index}_rad"] = float(value)
        record[f"phase_{index}_deg"] = float(math.degrees(value))
    if has_pose_targets(args):
        pose = orientation_metrics(phase_sim, args.target_orientations_deg, pose_tolerances(args))
        initial_pose = orientation_metrics(initial_phase_sim, args.target_orientations_deg, pose_tolerances(args))
        record.update(
            orientation_required=True,
            orientation_frame="coupler_A_to_B",
            orientation_acceptable=bool(pose["feasible"][0].item()),
            max_orientation_error_deg=float(pose["max_error_deg"][0].item()),
            mean_orientation_error_deg=float(pose["mean_error_deg"][0].item()),
            initial_max_orientation_error_deg=float(initial_pose["max_error_deg"][0].item()),
        )
        for i in range(3):
            record[f"target_orientation_{i + 1}_deg"] = float(args.target_orientations_deg[i])
            record[f"orientation_tolerance_{i + 1}_deg"] = float(pose_tolerances(args)[i])
            record[f"matched_orientation_{i + 1}_deg"] = float(torch.rad2deg(pose["angles_rad"][0, i]).item())
            record[f"orientation_error_{i + 1}_deg"] = float(pose["errors_deg"][0, i].item())
    from . import panel
    panel_config = panel.configuration(args)
    if panel_config:
        record.update(panel.screen(params_np, start.branch_sign, panel_config))
    return record

def flat_candidate_row(candidate: Dict[str, Any]) -> Dict[str, Any]:
    excluded = {
        "parameters",
        "phases_rad",
        "phases_deg",
        "target_points",
        "matched_points",
        "curve",
        "dense_theta",
        "dense_simulation",
        "phase_simulation",
    }
    return {key: value for key, value in candidate.items() if key not in excluded}


def bidirectional_curve_chamfer(curve_a: np.ndarray, curve_b: np.ndarray) -> float:
    # Downsample for economical deduplication; these are already in the same global frame.
    max_points = 181
    if len(curve_a) > max_points:
        curve_a = curve_a[np.linspace(0, len(curve_a) - 1, max_points).astype(int)]
    if len(curve_b) > max_points:
        curve_b = curve_b[np.linspace(0, len(curve_b) - 1, max_points).astype(int)]
    diff = curve_a[:, None, :] - curve_b[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    return float(0.5 * (distances.min(axis=1).mean() + distances.min(axis=0).mean()))


def candidates_are_duplicates(
    candidate: Dict[str, Any],
    selected: Dict[str, Any],
    args: argparse.Namespace,
) -> bool:
    if candidate["branch_sign"] != selected["branch_sign"]:
        return False
    param_distance = np.linalg.norm(
        normalized_parameter_vector(candidate) - normalized_parameter_vector(selected)
    )
    if param_distance >= args.dedup_parameter_threshold:
        return False
    curve_distance = bidirectional_curve_chamfer(candidate["curve"], selected["curve"])
    return curve_distance < args.dedup_curve_threshold

def apply_shared_candidate_qualification(
    candidates: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
    shared_reference: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    physical = [candidate for candidate in candidates if candidate["physical_feasible"]]
    if not physical:
        for candidate in candidates:
            candidate.update({
                "shared_path_budget_feasible": False,
                "absolute_mean_error_acceptable": False,
                "absolute_point_errors_acceptable": False,
                "path_acceptable": False,
                "target_transmission_acceptable": False,
                "global_transmission_acceptable": False,
                "robustness_acceptable": False,
                "compactness_acceptable": False,
                "engineering_acceptable": False,
                "selection_eligible": False,
                "qualification_level": "not_physical",
            })
            if has_pose_targets(args):
                candidate["pose_acceptable"] = False
        return {
            "reference_candidate_id": None,
            "physical_candidate_count": 0,
            "path_acceptable_count": 0,
            "selection_eligible_count": 0,
            "engineering_acceptable_count": 0,
            "selection_fallback_used": False,
        }

    if shared_reference is not None:
        reference_id = str(shared_reference["reference_candidate_id"])
        reference_candidate = next(
            (candidate for candidate in candidates if str(candidate["candidate_id"]) == reference_id),
            min(physical, key=lambda item: item["mean_error"]),
        )
        reference_mean = float(shared_reference["reference_acquired_mean_error"])
        reference_errors = np.asarray(shared_reference["reference_acquired_errors"], dtype=float)
        shared_mean_budget = float(shared_reference["shared_mean_budget"])
        shared_point_budgets = np.asarray(shared_reference["shared_point_budgets"], dtype=float)
    else:
        reference_candidate = min(
            physical,
            key=lambda item: (
                float(item.get("acquired_mean_error", item["mean_error"])),
                max(float(item.get("acquired_error_1", item["error_1"])),
                    float(item.get("acquired_error_2", item["error_2"])),
                    float(item.get("acquired_error_3", item["error_3"]))),
            ),
        )
        reference_mean = float(reference_candidate.get("acquired_mean_error", reference_candidate["mean_error"]))
        reference_errors = np.asarray([
            reference_candidate.get("acquired_error_1", reference_candidate["error_1"]),
            reference_candidate.get("acquired_error_2", reference_candidate["error_2"]),
            reference_candidate.get("acquired_error_3", reference_candidate["error_3"]),
        ], dtype=float)
        shared_mean_budget = min(float(args.max_mean_error), reference_mean + float(args.shared_mean_allowance))
        shared_point_budgets = np.minimum(float(args.max_point_error), reference_errors + float(args.shared_point_allowance))

    path_count = robustness_count = selection_count = engineering_count = 0
    for candidate in candidates:
        errors = np.asarray([candidate["error_1"], candidate["error_2"], candidate["error_3"]], dtype=float)
        physical_ok = bool(candidate["physical_feasible"])
        shared_ok = bool(
            candidate["mean_error"] <= shared_mean_budget + 1e-12
            and np.all(errors <= shared_point_budgets + 1e-12)
        )
        absolute_mean_ok = candidate["mean_error"] <= args.max_mean_error + 1e-12
        absolute_points_ok = bool(np.all(errors <= args.max_point_error + 1e-12))
        path_ok = bool(physical_ok and shared_ok and absolute_mean_ok and absolute_points_ok)
        target_tx_ok = candidate["target_angle_min_deg"] + 1e-12 >= args.target_transmission_deg
        global_tx_ok = candidate["global_angle_min_deg"] + 1e-12 >= args.global_transmission_floor_deg
        robustness_ok = bool(
            candidate["assembly_margin_ratio"] + 1e-12 >= args.assembly_margin_ratio
            and candidate["grashof_margin_ratio"] + 1e-12 >= args.grashof_margin_ratio
            and candidate["crank_margin_ratio"] + 1e-12 >= max(
                args.class_margin_ratio,
                args.class_margin / max(candidate["target_scale"], 1e-9),
            )
            and (
                not args.enforce_follower_not_longest
                or candidate["follower_margin_ratio"] + 1e-12 >= max(
                    args.class_margin_ratio,
                    args.class_margin / max(candidate["target_scale"], 1e-9),
                )
            )
        )
        compactness_ok = bool(
            (args.engineering_max_link_ratio <= 0.0 or candidate["max_link_ratio"] <= args.engineering_max_link_ratio + 1e-12)
            and (args.engineering_max_sweep_radius_ratio <= 0.0 or candidate["sweep_radius_ratio"] <= args.engineering_max_sweep_radius_ratio + 1e-12)
        )
        orientation_ok = (not has_pose_targets(args)) or bool(candidate.get("orientation_acceptable", False))
        panel_ok = getattr(args, "panel_bounds", None) is None or bool(candidate.get("panel_acceptable", False))
        engineering_ok = bool(path_ok and orientation_ok and panel_ok and target_tx_ok and global_tx_ok and robustness_ok and compactness_ok)
        target_selection_ok = bool(
            args.minimum_target_transmission <= 0.0
            or candidate["target_angle_min_deg"] + 1e-12 >= args.minimum_target_transmission
        )
        global_selection_ok = bool(
            args.minimum_global_transmission <= 0.0
            or candidate["global_angle_min_deg"] + 1e-12 >= args.minimum_global_transmission
        )
        selection_ok = bool(path_ok and orientation_ok and panel_ok and target_selection_ok and global_selection_ok and robustness_ok and compactness_ok)
        if engineering_ok:
            level = "engineering_acceptable"
        elif selection_ok:
            level = "selection_acceptable"
        elif path_ok and not orientation_ok:
            level = "path_acceptable_but_orientation_failed"
        elif path_ok and not panel_ok:
            level = "path_acceptable_but_panel_failed"
        elif path_ok and not robustness_ok:
            level = "path_acceptable_but_robustness_failed"
        elif path_ok and not compactness_ok:
            level = "path_acceptable_but_compactness_failed"
        elif path_ok:
            level = "path_acceptable_but_selection_floor_failed"
        elif physical_ok:
            level = "physical_only_path_rejected"
        else:
            level = "not_physical"
        candidate.update({
            "shared_path_reference_candidate_id": reference_candidate["candidate_id"],
            "shared_path_reference_mean_error": reference_mean,
            "shared_path_reference_error_1": float(reference_errors[0]),
            "shared_path_reference_error_2": float(reference_errors[1]),
            "shared_path_reference_error_3": float(reference_errors[2]),
            "shared_mean_path_budget": shared_mean_budget,
            "shared_point_budget_1": float(shared_point_budgets[0]),
            "shared_point_budget_2": float(shared_point_budgets[1]),
            "shared_point_budget_3": float(shared_point_budgets[2]),
            "shared_path_budget_feasible": shared_ok,
            "absolute_mean_error_acceptable": absolute_mean_ok,
            "absolute_point_errors_acceptable": absolute_points_ok,
            "path_acceptable": path_ok,
            "target_transmission_acceptable": target_tx_ok,
            "global_transmission_acceptable": global_tx_ok,
            "robustness_acceptable": robustness_ok,
            "compactness_acceptable": compactness_ok,
            "engineering_acceptable": engineering_ok,
            "target_selection_floor_acceptable": target_selection_ok,
            "global_selection_floor_acceptable": global_selection_ok,
            "selection_eligible": selection_ok,
            "qualification_level": level,
            "path_budget_feasible": shared_ok,
        })
        if has_pose_targets(args):
            candidate["pose_acceptable"] = bool(path_ok and orientation_ok)
        path_count += int(path_ok)
        robustness_count += int(robustness_ok)
        selection_count += int(selection_ok)
        engineering_count += int(engineering_ok)

    return {
        "reference_candidate_id": reference_candidate["candidate_id"],
        "reference_model_role": reference_candidate["model_role"],
        "reference_profile": reference_candidate["profile"],
        "reference_branch_sign": reference_candidate["branch_sign"],
        "reference_acquired_mean_error": reference_mean,
        "reference_acquired_errors": reference_errors.tolist(),
        "shared_mean_budget": shared_mean_budget,
        "shared_point_budgets": shared_point_budgets.tolist(),
        "max_mean_error": args.max_mean_error,
        "max_point_error": args.max_point_error,
        "shared_mean_allowance": args.shared_mean_allowance,
        "shared_point_allowance": args.shared_point_allowance,
        "minimum_target_transmission": args.minimum_target_transmission,
        "minimum_global_transmission": args.minimum_global_transmission,
        "target_transmission_threshold_deg": args.target_transmission_deg,
        "global_transmission_threshold_deg": args.global_transmission_floor_deg,
        "ground_link_mode": args.ground_link_mode,
        "follower_not_longest_enforced": bool(args.enforce_follower_not_longest),
        "physical_candidate_count": len(physical),
        "path_acceptable_count": path_count,
        "robustness_acceptable_count": robustness_count,
        "selection_eligible_count": selection_count,
        "engineering_acceptable_count": engineering_count,
        "selection_fallback_used": False,
    }

def final_selection_pool(
    candidates: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], bool]:
    qualified = [candidate for candidate in candidates if candidate.get("selection_eligible", False)]
    if qualified:
        return qualified, False
    if not args.allow_unqualified_fallback or args.strict_qualification:
        return [], False
    physical = [candidate for candidate in candidates if candidate["physical_feasible"]]
    return (physical if physical else list(candidates)), True


def pareto_front(
    candidates: Sequence[Dict[str, Any]],
    args: Optional[argparse.Namespace] = None,
) -> List[Dict[str, Any]]:
    if args is None:
        feasible = [c for c in candidates if c.get("selection_eligible", c["physical_feasible"])]
    else:
        feasible, _ = final_selection_pool(candidates, args)
    front: List[Dict[str, Any]] = []
    for candidate in feasible:
        dominated = False
        for other in feasible:
            if other is candidate:
                continue
            no_worse = (
                other["mean_error"] <= candidate["mean_error"]
                and other["target_transmission_penalty"] <= candidate["target_transmission_penalty"]
                and other["compactness_score"] <= candidate["compactness_score"]
            )
            strictly_better = (
                other["mean_error"] < candidate["mean_error"]
                or other["target_transmission_penalty"] < candidate["target_transmission_penalty"]
                or other["compactness_score"] < candidate["compactness_score"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            front.append(candidate)
    return sorted(
        front,
        key=lambda item: (
            item["mean_error"], item["target_transmission_penalty"], item["compactness_score"]
        ),
    )


def select_diverse_candidates(
    candidates: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], bool]:
    pool, fallback_used = final_selection_pool(candidates, args)
    ordered: List[Dict[str, Any]] = []
    ordered_ids: set[str] = set()

    def append_candidate(candidate: Dict[str, Any]) -> None:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id not in ordered_ids:
            ordered.append(candidate)
            ordered_ids.add(candidate_id)

    def append_best(key: str, reverse: bool = False) -> None:
        if pool:
            append_candidate(sorted(pool, key=lambda item: item[key], reverse=reverse)[0])

    append_best("balanced_score")
    append_best("accuracy_score")
    append_best("target_transmission_penalty")
    append_best("target_angle_min_deg", reverse=True)
    append_best("global_angle_min_deg", reverse=True)
    append_best("compactness_score")
    append_best("assembly_margin_ratio", reverse=True)
    for candidate in pareto_front(pool):
        append_candidate(candidate)
    for candidate in sorted(pool, key=lambda item: item["balanced_score"]):
        append_candidate(candidate)

    selected: List[Dict[str, Any]] = []
    for candidate in ordered:
        if any(candidates_are_duplicates(candidate, existing, args) for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= args.top_k:
            break
    return selected, fallback_used


# ======================
# ===== EXPORT =====
# ======================
def save_candidate_artifacts(
    candidate: Dict[str, Any],
    rank: int,
    target_dir: Path,
    args: argparse.Namespace,
) -> None:
    prefix = f"candidate_{rank:02d}_{sanitize_label(str(candidate['candidate_id']))}"
    serializable = {key: value for key, value in candidate.items() if key not in {
        "curve", "dense_theta", "dense_simulation", "phase_simulation"
    }}
    write_json(target_dir / f"{prefix}.json", serializable)

    dense = candidate["dense_simulation"]
    phase = candidate["phase_simulation"]
    np.savez_compressed(
        target_dir / f"{prefix}.npz",
        target_points=np.asarray(candidate["target_points"], dtype=float),
        matched_points=np.asarray(candidate["matched_points"], dtype=float),
        parameters=np.asarray(candidate["parameters"], dtype=float),
        crank_direction=np.asarray(candidate.get("crank_direction", "positive")),
        phases_rad=np.asarray(candidate["phases_rad"], dtype=float),
        theta=np.asarray(candidate["dense_theta"], dtype=float),
        **{key: np.asarray(value) for key, value in candidate.items() if key.startswith(("panel_", "carrier_"))},
        **{f"dense_{key}": value for key, value in dense.items()},
        **{f"phase_{key}": value for key, value in phase.items()},
    )
    if args.no_plots:
        return

    targets = np.asarray(candidate["target_points"], dtype=float)
    matched = np.asarray(candidate["matched_points"], dtype=float)
    curve = np.asarray(candidate["curve"], dtype=float)
    fig, axis = plt.subplots(figsize=(10, 8))
    axis.plot(curve[:, 0], curve[:, 1], linewidth=1.4, label="Coupler path")
    axis.scatter(targets[:, 0], targets[:, 1], marker="x", s=100, label="Targets")
    axis.scatter(matched[:, 0], matched[:, 1], marker="o", s=45, label="Matched phases")
    for index in range(3):
        axis.plot(
            [targets[index, 0], matched[index, 0]],
            [targets[index, 1], matched[index, 1]],
            linestyle="--", linewidth=0.9,
        )
        axis.text(
            targets[index, 0], targets[index, 1],
            f" T{index + 1}\n e={candidate[f'error_{index + 1}']:.4g}\n"
            f" mu={candidate[f'target_angle_{index + 1}_deg']:.1f} deg",
            fontsize=8,
        )

    if candidate.get("orientation_required", False):
        arrow_length = max(float(candidate["target_scale"]) * 0.13, 0.1)
        for index in range(3):
            desired = math.radians(candidate[f"target_orientation_{index + 1}_deg"])
            actual = math.radians(candidate[f"matched_orientation_{index + 1}_deg"])
            for point, angle, color, label in (
                (targets[index], desired, "tab:orange", "Requested orientation"),
                (matched[index], actual, "tab:green", "Achieved orientation"),
            ):
                axis.quiver(point[0], point[1], arrow_length * math.cos(angle), arrow_length * math.sin(angle),
                            angles="xy", scale_units="xy", scale=1, color=color, width=0.006,
                            label=label if index == 0 else None)

    snapshot = phase
    i = 0
    axis.plot([snapshot["O2x"][i], snapshot["Ax"][i]], [snapshot["O2y"][i], snapshot["Ay"][i]], "-o", linewidth=2, label="Crank")
    axis.plot([snapshot["Ax"][i], snapshot["Bx"][i]], [snapshot["Ay"][i], snapshot["By"][i]], "-o", linewidth=2, label="Coupler")
    axis.plot([snapshot["Bx"][i], snapshot["O4x"][i]], [snapshot["By"][i], snapshot["O4y"][i]], "-o", linewidth=2, label="Follower")
    axis.plot([snapshot["O2x"][i], snapshot["O4x"][i]], [snapshot["O2y"][i], snapshot["O4y"][i]], "-o", linewidth=2, label="Ground")
    axis.plot([snapshot["Ax"][i], snapshot["Px"][i], snapshot["Bx"][i]], [snapshot["Ay"][i], snapshot["Py"][i], snapshot["By"][i]], linestyle=":", linewidth=1.3, label="Coupler triangle")

    axis.set_aspect("equal", adjustable="box")
    axis.grid(True, linestyle="--", alpha=0.4)
    axis.set_xlabel("X")
    axis.set_ylabel("Y")
    axis.set_title(
        f"{VARIANT} - Rank {rank} / {candidate['candidate_id']}\n"
        f"{candidate['model_role']} proposal / {candidate['profile']} profile / branch {candidate['branch_sign']:+.0f}\n"
        f"mean={candidate['mean_error']:.5f}, max={candidate['max_error']:.5f}, "
        f"worst target mu={candidate['target_angle_min_deg']:.2f} deg, global min={candidate['global_angle_min_deg']:.2f} deg\n"
        f"L1={candidate['l1']:.3f}, max-link/D={candidate['max_link_ratio']:.2f}, "
        f"sweep-radius/D={candidate['sweep_radius_ratio']:.2f}, {candidate.get('qualification_level', 'not_evaluated')}"
    )
    handles, labels = axis.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    axis.legend(unique.values(), unique.keys(), fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(target_dir / f"{prefix}.png", dpi=180)
    if args.show_plots and not _HEADLESS:
        plt.show(block=False)
    plt.close(fig)

def write_summary_markdown(
    target_dir: Path,
    target_values: np.ndarray,
    all_candidates: Sequence[Dict[str, Any]],
    selected: Sequence[Dict[str, Any]],
    elapsed: float,
    qualification: Dict[str, Any],
) -> None:
    target_scale = float(all_candidates[0]["target_scale"]) if all_candidates else float("nan")
    lines = [
        f"# {VARIANT} Results", "", "## Target points", "",
        f"- T1: ({target_values[0]:.6g}, {target_values[1]:.6g})",
        f"- T2: ({target_values[2]:.6g}, {target_values[3]:.6g})",
        f"- T3: ({target_values[4]:.6g}, {target_values[5]:.6g})", "",
        f"Target scale D (maximum pairwise separation): **{target_scale:.6g}**  ",
        f"Ground-link mode: **{qualification.get('ground_link_mode')}**  ",
        f"Follower-not-longest rule enforced: **{qualification.get('follower_not_longest_enforced')}**  ",
        f"Starts evaluated: **{len(all_candidates)}**  ",
        f"Physically valid: **{qualification.get('physical_candidate_count', 0)}**  ",
        f"Path acceptable: **{qualification.get('path_acceptable_count', 0)}**  ",
        f"Selection eligible: **{qualification.get('selection_eligible_count', 0)}**  ",
        f"Fully engineering acceptable: **{qualification.get('engineering_acceptable_count', 0)}**  ",
        f"Selected distinct candidates: **{len(selected)}**  ",
        f"Runtime: **{elapsed:.2f} s**", "",
        "## Shared path qualification", "",
        f"- Reference start: `{qualification.get('reference_candidate_id')}`",
        f"- Reference acquired mean error: {qualification.get('reference_acquired_mean_error')}",
        f"- Shared mean-error budget: {qualification.get('shared_mean_budget')}",
        f"- Shared point-error budgets: {qualification.get('shared_point_budgets')}",
        f"- Absolute mean-error ceiling: {qualification.get('max_mean_error')}",
        f"- Absolute point-error ceiling: {qualification.get('max_point_error')}", "",
        "## Selected candidates", "",
        "| Rank | Start | Proposal | Profile | Branch | L1 | Mean error | Worst target mu | Global min mu | Max link/D | Sweep radius/D | Assembly margin/D | Qualification |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, candidate in enumerate(selected, start=1):
        lines.append(
            f"| {rank} | `{candidate['candidate_id']}` | {candidate['model_role']} | {candidate['profile']} | "
            f"{candidate['branch_sign']:+.0f} | {candidate['l1']:.4f} | {candidate['mean_error']:.6f} | "
            f"{candidate['target_angle_min_deg']:.2f} deg | {candidate['global_angle_min_deg']:.2f} deg | "
            f"{candidate['max_link_ratio']:.3f} | {candidate['sweep_radius_ratio']:.3f} | "
            f"{candidate['assembly_margin_ratio']:.4f} | {candidate.get('qualification_level', 'not_evaluated')} |"
        )
    lines.extend([
        "", "## Interpretation", "",
        "- L1 is a local design variable when ground-link mode is `optimize`.",
        "- Dimensional bounds and compactness metrics are normalized by the translation-invariant target scale D.",
        "- The target-transmission loss emphasizes the weakest of the three target positions.",
        "- The global loss emphasizes the near-toggle tail and a smooth approximation of the true minimum.",
        "- `engineering_acceptable` requires path, preferred transmission goals, and configured robustness margins.",
        "- Compactness is a soft Pareto objective unless optional engineering ceilings are supplied.",
        "- This kinematic result is not structural or machinery certification.",
    ])
    (target_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ======================
# ===== MAIN =====
# ======================
def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_args(parser, args)
    if args.crank_direction == "either":
        parser.error("Use mechanism-generate (R2.5c) for either-direction searches")
    if args.allow_unqualified_fallback:
        parser.error("Unqualified fallback is disabled in the public alpha; inspect all_candidates.csv instead")

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

    set_deterministic_seed(args.seed)
    device = choose_device(args.device)
    refine_dtype = torch_dtype(args.dtype)
    targets = collect_targets(args)

    role_definitions = {
        "balanced": ("balanced", Path(args.balanced_model)),
        "path": ("accuracy", Path(args.path_model)),
        "transmission": ("transmission", Path(args.transmission_model)),
    }
    models: List[ModelRole] = []
    for role in args.model_roles:
        default_profile, path = role_definitions[role]
        loaded = load_model_role(role, default_profile, path, device)
        models.append(loaded)
        print(
            f"[MODEL] role={role} default_profile={default_profile} "
            f"variant={loaded.checkpoint_variant} state_epoch={loaded.checkpoint_epoch} file={path}"
        )
    if not models:
        raise RuntimeError("No proposal checkpoints could be loaded")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    label = sanitize_label(args.run_label) if args.run_label else "refinement"
    run_dir = Path(args.output_root) / "r25b" / f"{timestamp}_{label[:32]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    set_run_root(run_dir)
    source_path = Path(__file__).resolve()
    run_manifest: Dict[str, Any] = {
        "variant": VARIANT, "parent_variant": PARENT_VARIANT,
        "schema_version": SCHEMA_VERSION, "timestamp": timestamp,
        "device": str(device), "refinement_dtype": args.dtype, "seed": args.seed,
        "script": str(source_path), "script_sha256": sha256_file(source_path),
        "arguments": vars(args),
        "models": [
            {
                "role": role.role, "default_profile": role.profile,
                "path": str(role.path), "checkpoint_variant": role.checkpoint_variant,
                "checkpoint_epoch": role.checkpoint_epoch, "sha256": role.checkpoint_sha256,
            }
            for role in models
        ],
        "targets": [],
    }
    write_json(run_dir / "run_config.json", run_manifest)

    print(f"Using device: {device}; refinement dtype: {args.dtype}")
    print(
        f"Design mode: L1={args.ground_link_mode}; profile_matrix={args.profile_matrix}; "
        f"follower_rule={args.enforce_follower_not_longest}"
    )
    print(f"Run directory: {run_dir}")

    for target_index, (target_label, target_values) in enumerate(targets):
        target_start_time = time.time()
        target_dir = run_dir / f"{target_index + 1:04d}_{sanitize_label(target_label)}"
        target_dir.mkdir(parents=True, exist_ok=False)
        target = torch.tensor(target_values, dtype=refine_dtype, device=device)
        target_points_np = target_values.reshape(3, 2)
        if not np.isfinite(target_points_np).all():
            raise ValueError(f"Target {target_label} contains NaN or infinity")
        in_training_domain = bool(
            np.all((target_points_np[:, 0] >= X_MIN) & (target_points_np[:, 0] <= X_MAX))
            and np.all((target_points_np[:, 1] >= Y_MIN) & (target_points_np[:, 1] <= Y_MAX))
        )
        if not in_training_domain:
            print(
                f"[WARN] {target_label} lies outside the proposal networks' historical training domain; "
                "local refinement is scale-aware, but proposal quality may be lower."
            )
        space = target_design_space(target, args)
        write_json(target_dir / "target.json", {
            "label": target_label, "values": target_values.tolist(),
            "points": target_points_np.tolist(), "phase_mode": args.phase_mode,
            "crank_direction": args.crank_direction,
            "inside_proposal_training_domain": in_training_domain,
            "proposal_training_domain": {"x": [X_MIN, X_MAX], "y": [Y_MIN, Y_MAX], "historical_ground_link": PROPOSAL_L1_VALUE},
            "local_design_space": {
                "target_scale": space["scale"], "target_centroid": space["centroid"],
                "ground_link_mode": args.ground_link_mode,
                "ground_link_bounds": [space["ground_min"], space["ground_max"]],
                "moving_link_bounds": [space["moving_min"], space["moving_max"]],
                "bar_length_bounds": [MIN_BAR_LEN, space["bar_max"]],
                "base_x_bounds": [space["base_x_min"], space["base_x_max"]],
                "base_y_bounds": [space["base_y_min"], space["base_y_max"]],
            },
        })
        print(
            f"\n[TARGET {target_index + 1}/{len(targets)}] {target_label}: "
            f"{target_values.reshape(3, 2).tolist()} | D={space['scale'].item():.4f}"
        )

        starts = build_starts(models, target, args, target_index)
        print(
            f"[STARTS] {len(starts)} candidate refinements "
            f"({len(models)} models, profile_matrix={args.profile_matrix}, branches={args.branches})"
        )
        print("[PHASE 1/2] Acquiring the best physical path from every start")
        acquisitions: List[Dict[str, Any]] = []
        for start_number, start in enumerate(starts, start=1):
            acquisition_start = time.time()
            print(
                f"  [A {start_number:02d}/{len(starts):02d}] {start.candidate_id} "
                f"proposal={start.model_role} profile={start.profile} "
                f"branch={start.branch_sign:+.0f} perturb={start.perturbation_index}"
            )
            acquired = acquire_start_path(start, target, args)
            acquired["acquisition_runtime_seconds"] = time.time() - acquisition_start
            acquisitions.append(acquired)
            print(
                f"      acquired_mean={acquired['acquired_mean_error']:.6f} "
                f"acquired_max={acquired['acquired_max_error']:.6f} "
                f"target_mu_min={acquired['acquired_target_angle_min_deg']:.2f}deg "
                f"global_mu_min={acquired['acquired_global_angle_min_deg']:.2f}deg "
                f"physical={acquired['acquired_physical']}"
            )

        shared_reference = build_shared_path_reference(acquisitions, args)
        write_json(target_dir / "shared_path_reference.json", shared_reference)
        print(
            f"[SHARED PATH] reference={shared_reference['reference_candidate_id']} "
            f"mean={shared_reference['reference_acquired_mean_error']:.6f} "
            f"mean_budget={shared_reference['shared_mean_budget']:.6f}"
        )

        print("[PHASE 2/2] Robust transmission and compactness refinement under the common path budget")
        evaluated: List[Dict[str, Any]] = []
        for start_number, acquired in enumerate(acquisitions, start=1):
            start = acquired["start"]
            tradeoff_start = time.time()
            print(
                f"  [B {start_number:02d}/{len(acquisitions):02d}] {start.candidate_id} "
                f"proposal={start.model_role} profile={start.profile} "
                f"branch={start.branch_sign:+.0f} perturb={start.perturbation_index}"
            )
            optimized = optimize_start_with_shared_budget(
                acquired, shared_reference, target, args, target_dir
            )
            candidate = evaluate_selected_candidate(optimized, target, args)
            candidate["acquisition_runtime_seconds"] = acquired["acquisition_runtime_seconds"]
            candidate["tradeoff_runtime_seconds"] = time.time() - tradeoff_start
            candidate["runtime_seconds"] = candidate["acquisition_runtime_seconds"] + candidate["tradeoff_runtime_seconds"]
            evaluated.append(candidate)
            print(
                f"      mean={candidate['mean_error']:.6f} max={candidate['max_error']:.6f} "
                f"target_mu_min={candidate['target_angle_min_deg']:.2f}deg "
                f"global_mu_min={candidate['global_angle_min_deg']:.2f}deg "
                f"L1={candidate['l1']:.3f} maxL/D={candidate['max_link_ratio']:.2f} "
                f"sweepR/D={candidate['sweep_radius_ratio']:.2f} "
                f"physical={candidate['physical_feasible']}"
            )

        qualification = apply_shared_candidate_qualification(evaluated, args, shared_reference)
        qualification["stage_a_shared_reference"] = shared_reference
        selected, fallback_used = select_diverse_candidates(evaluated, args)
        qualification["selection_fallback_used"] = fallback_used
        front = pareto_front(evaluated, args)
        for rank, candidate in enumerate(selected, start=1):
            candidate["selected_rank"] = rank
            save_candidate_artifacts(candidate, rank, target_dir, args)

        path_acceptable = [c for c in evaluated if c.get("path_acceptable", False)]
        qualified = [c for c in evaluated if c.get("selection_eligible", False)]
        engineering = [c for c in evaluated if c.get("engineering_acceptable", False)]
        rejected = [c for c in evaluated if not c.get("selection_eligible", False)]
        write_json(target_dir / "selection_reference.json", qualification)
        write_csv(target_dir / "all_candidates.csv", [flat_candidate_row(c) for c in evaluated])
        write_csv(target_dir / "path_acceptable_candidates.csv", [flat_candidate_row(c) for c in path_acceptable])
        write_csv(target_dir / "qualified_candidates.csv", [flat_candidate_row(c) for c in qualified])
        write_csv(target_dir / "engineering_acceptable_candidates.csv", [flat_candidate_row(c) for c in engineering])
        write_csv(target_dir / "rejected_candidates.csv", [flat_candidate_row(c) for c in rejected])
        write_csv(target_dir / "selected_candidates.csv", [flat_candidate_row(c) for c in selected])
        write_csv(target_dir / "pareto_front.csv", [flat_candidate_row(c) for c in front])
        elapsed = time.time() - target_start_time
        write_summary_markdown(target_dir, target_values, evaluated, selected, elapsed, qualification)

        print(
            f"[QUALIFICATION] reference={qualification.get('reference_candidate_id')} "
            f"path_ok={qualification.get('path_acceptable_count', 0)}/{len(evaluated)} "
            f"selection_ok={qualification.get('selection_eligible_count', 0)}/{len(evaluated)} "
            f"engineering_ok={qualification.get('engineering_acceptable_count', 0)}/{len(evaluated)} "
            f"fallback={fallback_used}"
        )

        target_manifest = {
            "label": target_label, "directory": str(target_dir),
            "target_values": target_values.tolist(), "target_scale": float(space["scale"].item()),
            "start_count": len(starts),
            "physical_candidate_count": sum(bool(c["physical_feasible"]) for c in evaluated),
            "path_acceptable_count": sum(bool(c.get("path_acceptable", False)) for c in evaluated),
            "selection_eligible_count": sum(bool(c.get("selection_eligible", False)) for c in evaluated),
            "engineering_acceptable_count": sum(bool(c.get("engineering_acceptable", False)) for c in evaluated),
            "selected_count": len(selected), "pareto_count": len(front),
            "selection_reference": qualification, "runtime_seconds": elapsed,
            "selected": [{"rank": rank, **flat_candidate_row(candidate)} for rank, candidate in enumerate(selected, start=1)],
        }
        run_manifest["targets"].append(target_manifest)
        write_json(run_dir / "run_manifest.json", run_manifest)

        print(f"[TARGET COMPLETE] {elapsed:.2f}s | selected={len(selected)} | {target_dir}")
        if selected:
            best = selected[0]
            print(
                f"[BEST SELECTED] id={best['candidate_id']} mean={best['mean_error']:.6f}, "
                f"worst target transmission={best['target_angle_min_deg']:.2f}deg, "
                f"global minimum={best['global_angle_min_deg']:.2f}deg, L1={best['l1']:.3f}, "
                f"max-link/D={best['max_link_ratio']:.2f}, sweep-radius/D={best['sweep_radius_ratio']:.2f}, "
                f"qualification={best.get('qualification_level', 'not_evaluated')}"
            )

    write_json(run_dir / "run_manifest.json", run_manifest)
    print(f"\nR2.5b refinement complete. Artifacts: {run_dir}")
    if args.show_plots and not _HEADLESS:
        plt.show()
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
