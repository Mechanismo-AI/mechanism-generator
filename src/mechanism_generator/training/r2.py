#!/usr/bin/env python3
"""
V5.3-R2 Geometry Fix

Geometry-only fork of V5.3-R1.1_InstrumentedSafety.

R2 preserves the R1.1 network, output parameterization, target distribution,
hard nearest-point correspondence, optimizer, fixed validation set, coherent
rollback, terminal-state reporting, and safety instrumentation. It changes the
forward four-bar geometry and assembly objective only:

  * replaces the clamp-before-validity acos solver with direct circle-circle
    intersection;
  * keeps the same open/crossed assembly branch used by V5.3 (branch sign -1);
  * determines assembly validity from raw circle-intersection inequalities;
  * keeps invalid simulated coordinates finite and excludes them through a
    validity mask, avoiding NaN propagation through torch.where;
  * adds sampled and analytic full-cycle assembly violations with continuous
    gradients;
  * uses small numerical floors at the coincident-center and toggle
    singularities while preserving the hard nearest-point objective; and
  * logs transmission quality q = sin(mu)^2 and acute-equivalent transmission
    angles, with transmission loss weight fixed at zero in this revision.

Target-weighted transmission-angle training remains reserved for R2.1. The
soft nearest-point objective remains reserved for R3.
"""

from __future__ import annotations

# The historical trainers execute as scripts; importing them must not start a run.
if __name__ != "__main__":
    raise RuntimeError("Use mechanism-train or execute this trainer with python -m.")

from .state import restricted_load, capture_numpy_state, restore_numpy_state

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import re
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

# Select a non-interactive backend when requested or clearly headless.
# Some remote environments expose DISPLAY even though Tk is unavailable, so
# fall back to Agg rather than failing before argument parsing.
_HEADLESS = "--headless" in sys.argv or (os.name != "nt" and not os.environ.get("DISPLAY"))
import matplotlib
try:
    matplotlib.use("Agg" if _HEADLESS else "TkAgg")
except ImportError:
    _HEADLESS = True
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

EXPERIMENT_MODE = "R2"
IS_R1 = True
VARIANT = "V5.3-R2_GeometryFix"
PARENT_VARIANT = "V5.3-R1.1_InstrumentedSafety"
BASELINE_SOURCE_SHA256 = "f02dd296743bf8da9c17681a76eb0bedaa924db13fb22eefc5e665ef243105d7"
PARENT_SOURCE_SHA256 = "2d10f6763d64f74a3c0c854ce376c609a0b146d4f0f6071beec3f927704f8eab"
CHECKPOINT_SCHEMA_VERSION = 4

# ======================
# ===== ARGUMENT PARSING =====
# ======================
parser = argparse.ArgumentParser(
    description=f"{VARIANT}: corrected four-bar geometry experiment",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("--seed", type=int, default=101, help="Master seed for reproducible R2 runs")
parser.add_argument("--load_checkpoint", type=str, default=None, help="Checkpoint to load before training")
parser.add_argument("--num_epochs", type=int, default=10000, help="Total training epochs")
parser.add_argument("--num_points", type=int, default=10000, help="Training target triples")
parser.add_argument("--validation_samples", type=int, default=2048, help="Fixed validation target triples")
parser.add_argument("--validation_interval", type=int, default=1, help="Validate every N epochs; R2 validates every epoch")
parser.add_argument("--validation_batch_size", type=int, default=256, help="Fixed-validation batch size")
parser.add_argument("--num_workers", type=int, default=0, help="DataLoader workers; zero is safest for notebooks/Windows")
parser.add_argument("--eval_samples", type=int, default=5000, help="Post-training random evaluation samples")
parser.add_argument("--checkpoint_root", type=str, default="checkpoints", help="Root directory for run artifacts")
parser.add_argument("--run_label", type=str, default="", help="Optional label appended to the run directory")
parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
parser.add_argument("--headless", action="store_true", help="Use matplotlib Agg backend")
parser.add_argument("--no_plots", action="store_true", help="Do not display or save plots")
parser.add_argument("--skip_post_training", action="store_true", help="Skip plotting and final random evaluation")
parser.add_argument("--allow_nondeterministic", action="store_true", help="Allow nondeterministic CUDA kernels")
args, unknown_args = parser.parse_known_args()
if unknown_args:
    print(f"[WARN] Ignoring unrecognized arguments: {unknown_args}")

if args.num_epochs < 0:
    parser.error("--num_epochs must be non-negative")
if args.num_points <= 0:
    parser.error("--num_points must be positive")
if args.validation_samples <= 0:
    parser.error("--validation_samples must be positive")
if args.validation_interval <= 0:
    parser.error("--validation_interval must be positive")

# ======================
# ===== REPRODUCIBILITY =====
# ======================
def seed_everything(seed: int, deterministic: bool) -> None:
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
        if torch.backends.cudnn.is_available():
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False


DETERMINISTIC = not args.allow_nondeterministic
seed_everything(args.seed, deterministic=DETERMINISTIC)

if args.device == "cuda":
    if not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested, but CUDA is unavailable")
    device = torch.device("cuda")
elif args.device == "cpu":
    device = torch.device("cpu")
else:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Dedicated generators prevent validation and logging from perturbing training.
training_data_generator = torch.Generator(device="cpu")
training_data_generator.manual_seed(args.seed + 1001)
dataloader_generator = torch.Generator(device="cpu")
dataloader_generator.manual_seed(args.seed + 2001)
validation_generator = torch.Generator(device="cpu")
validation_generator.manual_seed(args.seed + 3001)
evaluation_generator = torch.Generator(device="cpu")
evaluation_generator.manual_seed(args.seed + 4001)

# ======================
# ===== CONFIGURATION =====
# ======================
# --- Data and Environment Config ---
NUM_POINTS = args.num_points
X_MIN, X_MAX = -7.0, 1.0
Y_MIN, Y_MAX = 1.0, 7.0
L1_FIXED_VALUE = 6.0
MIN_LEN = 1e-3
MIN_BAR_LEN = 0.1
BAD_BATCH_LOG = "bad_batches_three_points.csv"

# --- Training Config ---
NUM_EPOCHS = args.num_epochs
BATCH_SIZE = 32
INITIAL_LR = 1e-4
WARMUP_EPOCHS = 5
ANNEALING_EPOCHS = 1000
TARGET_MEAN_DIST = 0.02

# --- Simulation Config ---
INITIAL_NUM_SIM_STEPS = 73
FINAL_NUM_SIM_STEPS = 361
RAMP_START_EPOCH = 300
RAMP_END_EPOCH = 800
DEFAULT_NUM_SIM_STEPS = 361
VALIDATION_NUM_SIM_STEPS = 361

# --- Loss and Penalty Config ---
LAMBDA_GRASHOF = 0.05
LAMBDA_CRANK_SHORT = 0.05
LAMBDA_ADJACENCY = 0.05
LAMBDA_ASSEMBLY = 1.0

# R2 geometry configuration. The fixed branch sign reproduces the V5.3
# theta4 = alpha - phi assembly mode. Transmission is measured but not trained.
ASSEMBLY_BRANCH_SIGN = -1.0
ASSEMBLY_VALIDITY_TOL_REL = 1e-6
CENTER_DISTANCE_FLOOR_REL = 1e-4
D2_NUMERIC_FLOOR_REL = 1e-12
H2_NUMERIC_FLOOR_REL = 1e-8
DISTANCE_SQ_FLOOR = 1e-12
INVALID_DISTANCE = 20.0
TRANSMISSION_TARGET_MIN_DEG = 35.0
TRANSMISSION_GLOBAL_FLOOR_DEG = 15.0
LAMBDA_TRANSMISSION = 0.0

BASE_LOSS_COMPONENT_KEYS = (
    "distance_loss",
    "grashof_penalty",
    "crank_shortness_penalty",
    "adjacency_penalty",
    "assembly_penalty",
)
R2_EXTRA_COMPONENT_KEYS = (
    "transmission_penalty",
    "assembly_success_ratio",
    "full_cycle_assembly_ratio",
    "sampled_assembly_violation",
    "full_cycle_assembly_violation",
    "outer_assembly_violation",
    "inner_assembly_violation",
    "center_assembly_violation",
    "h2_negative_fraction",
    "h2_floor_fraction",
    "transmission_quality_mean",
    "transmission_quality_valid_mean",
    "transmission_quality_min",
    "transmission_min_angle_deg",
    "transmission_below_15deg_fraction",
    "transmission_below_35deg_fraction",
)
ALL_COMPONENT_KEYS = BASE_LOSS_COMPONENT_KEYS + R2_EXTRA_COMPONENT_KEYS

# --- Stability and Recovery Config ---
RESET_BAD_PREDICTIONS = True
MAX_GRAD_NORM = 0.25
MIN_LR = 1e-6
MAX_LOSS_FACTOR = 10.0
SPIKE_THRESHOLD = 2.5
VALIDATION_SPIKE_THRESHOLD = 2.5
SPIKE_MIN_EPOCH = 50
BASE_RESET_LR = INITIAL_LR * 5.0
GRACE_EPOCHS_AFTER_ROLLBACK = 10
PLATEAU_COOLDOWN_EPOCHS = 10
RECOVERY_LR_FACTOR = 0.5

# R2 retains the R1.1 instrumentation and hard-failure thresholds.  A dead-gradient recovery
# requires both an effectively zero epoch gradient and catastrophic fixed-
# validation degradation for consecutive epochs, so a genuine optimum is not
# rolled back merely because gradients become small.
DEAD_GRADIENT_NORM_THRESHOLD = 1e-12
DEAD_GRADIENT_PATIENCE = 2
CATASTROPHIC_VALIDATION_FACTOR = 3.0
CATASTROPHIC_VALIDATION_ABS_DELTA = 1.0
OUTPUT_SATURATION_EPS = 1e-4
OUTPUT_SATURATION_WARNING_FRACTION = 0.95

EARLY_RESET_EPOCHS = 20
MAX_CONSECUTIVE_RESETS = 3
ROLLBACK_HISTORY_SIZE = 100
ROLLBACK_DEPTHS = [50, 100]
REPEAT_ROLLBACK_LIMIT = 3
PLATEAU_MULT = 3.5
ABSOLUTE_PLATEAU_THRESHOLD = 5.0
PLATEAU_EPOCHS = 50
ONE_DEGREE_GRACE_EPOCHS = 15

# --- Early Stopping Config ---
EARLY_STOP_PATIENCE = 300
EARLY_STOP_MIN_DELTA = 1e-5

# --- LR Boost Config ---
LR_BOOST_START = 500
LR_BOOST_INTERVAL = 200
LR_BOOST_FACTOR = 1.5
LR_BOOST_DURATION = 5

# --- Dataloader Config ---
DATALOADER_RESTART_EPOCH = 1200

# --- Misc Config ---
MAX_BAD_BATCH_LOGS_PER_EPOCH = 5

# R1 removes competing LR/data controllers; C0 preserves them.
ENABLE_LR_BOOSTS = not IS_R1
ENABLE_COSINE_ANNEALING = not IS_R1
ENABLE_PERIODIC_DATA_REFRESH = not IS_R1

possible_points = torch.tensor([
    [X_MIN, Y_MIN],
    [X_MIN, Y_MAX],
    [X_MAX, Y_MIN],
    [X_MAX, Y_MAX],
], dtype=torch.float32)
GLOBAL_MAX_LEN = 2.0 * torch.norm(possible_points, dim=1).max().item()

# ======================
# ===== RUN DIRECTORIES =====
# ======================
def sanitize_label(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("_.-")


label = sanitize_label(args.run_label)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
RUN_ID = f"{timestamp}_seed{args.seed}" + (f"_{label}" if label else "")
CHECKPOINT_DIR = Path(args.checkpoint_root) / VARIANT
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR = CHECKPOINT_DIR / RUN_ID
RUN_DIR.mkdir(parents=True, exist_ok=False)

INITIAL_STATE_PATH = RUN_DIR / "initial_state.pth"
BEST_TRAIN_CHECKPOINT = RUN_DIR / "best_train_loss.pth"
BEST_VALIDATION_CHECKPOINT = RUN_DIR / "best_validation.pth"
TERMINAL_STATE_CHECKPOINT = RUN_DIR / "terminal_state.pth"
FINAL_MODEL_PATH = RUN_DIR / "best_model.pth"
ROLLBACK_LOG = RUN_DIR / "rollback_events.csv"
EVENT_LOG = RUN_DIR / "events.csv"
METRICS_LOG = RUN_DIR / "epoch_metrics.csv"
MODEL_COMPARISON_LOG = RUN_DIR / "model_state_comparison.csv"
MODEL_COMPARISON_JSON = RUN_DIR / "model_state_comparison.json"
TERMINAL_SUMMARY_PATH = RUN_DIR / "terminal_state_summary.json"
CONFIG_PATH = RUN_DIR / "config.json"
ENVIRONMENT_PATH = RUN_DIR / "environment.json"
VALIDATION_TARGETS_PATH = RUN_DIR / "fixed_validation_targets.pt"
INITIAL_TRAINING_TARGETS_PATH = RUN_DIR / "initial_training_targets.pt"
SOURCE_HASH_PATH = RUN_DIR / "source_sha256.txt"

print(f"Using device: {device}, GLOBAL_MAX_LEN={GLOBAL_MAX_LEN:.3f}")
print(f"Experiment: {VARIANT}")
print(f"Run directory: {RUN_DIR}")

# ======================
# ===== GENERIC UTILITIES =====
# ======================
def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def torch_load(path: Path | str, map_location: Any = None) -> Dict[str, Any]:
    """Load tensor-only public weights or restricted local training state."""
    return restricted_load(path, map_location=map_location)


def append_csv(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result


def current_lr() -> float:
    return float(optimizer.param_groups[0]["lr"])


def scheduler_is_attached() -> bool:
    return getattr(scheduler, "optimizer", None) is optimizer


def optimizer_step_summary() -> Tuple[float, float, float]:
    values = []
    for state in optimizer.state.values():
        step = state.get("step")
        if step is None:
            continue
        if torch.is_tensor(step):
            values.append(float(step.detach().cpu().item()))
        else:
            values.append(float(step))
    if not values:
        return 0.0, 0.0, 0.0
    return float(np.min(values)), float(np.mean(values)), float(np.max(values))


def log_event(
    epoch_number: int,
    event: str,
    reason: str = "",
    checkpoint: str = "",
    checkpoint_epoch: Any = "",
    train_loss_before: Any = "",
    val_loss_before: Any = "",
    checkpoint_train_loss: Any = "",
    checkpoint_val_loss: Any = "",
    lr_before: Any = "",
    lr_loaded: Any = "",
    lr_after: Any = "",
    details: str = "",
) -> None:
    step_min, step_mean, step_max = optimizer_step_summary()
    append_csv(EVENT_LOG, {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": epoch_number,
        "event": event,
        "reason": reason,
        "checkpoint": checkpoint,
        "checkpoint_epoch": checkpoint_epoch,
        "train_loss_before": train_loss_before,
        "val_loss_before": val_loss_before,
        "checkpoint_train_loss": checkpoint_train_loss,
        "checkpoint_val_loss": checkpoint_val_loss,
        "lr_before": lr_before,
        "lr_loaded": lr_loaded,
        "lr_after": lr_after,
        "live_lr_before_load": lr_before,
        "checkpoint_lr_after_load": lr_loaded,
        "recovery_lr_after_policy": lr_after,
        "optimizer_id": id(optimizer),
        "scheduler_optimizer_id": id(getattr(scheduler, "optimizer", None)),
        "scheduler_attached": scheduler_is_attached(),
        "optimizer_step_min": step_min,
        "optimizer_step_mean": step_mean,
        "optimizer_step_max": step_max,
        "details": details,
    })


def log_rollback_event(
    epoch_number: int,
    prev_loss: float,
    current_loss_value: float,
    lr_before: float,
    lr_after: float,
    reason: str,
    checkpoint_path: str = "",
    checkpoint_epoch: Any = "",
    val_loss_before: Any = "",
    checkpoint_val_loss: Any = "",
    lr_loaded: Any = "",
) -> None:
    """Write both legacy and unambiguous LR fields for recovery analysis."""
    append_csv(ROLLBACK_LOG, {
        "epoch": epoch_number,
        # Legacy columns retained so the existing PowerShell analysis still works.
        "prev_loss": prev_loss,
        "current_loss": current_loss_value,
        "lr_before": lr_before,
        "lr_after": lr_after,
        # R2 preserves the explicit R1.1 field ordering.
        "pre_rollback_train_loss": prev_loss,
        "loaded_checkpoint_train_loss": current_loss_value,
        "live_lr_before_load": lr_before,
        "checkpoint_lr_after_load": lr_loaded,
        "recovery_lr_after_policy": lr_after,
        "reason": reason,
        "checkpoint": checkpoint_path,
        "checkpoint_epoch": checkpoint_epoch,
        "pre_rollback_validation_loss": val_loss_before,
        "loaded_checkpoint_validation_loss": checkpoint_val_loss,
        # Legacy validation columns.
        "val_loss_before": val_loss_before,
        "checkpoint_val_loss": checkpoint_val_loss,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


def worker_seed_init(worker_id: int) -> None:
    worker_seed = torch.initial_seed() % (2**32)
    np.random.seed(worker_seed)
    random.seed(worker_seed)


# ======================
# ===== MODEL DEFINITION =====
# ======================
class MechanismNN(nn.Module):
    """Unchanged V5.3 network."""

    def __init__(self):
        super().__init__()
        current_dim = 6
        hidden_sizes = [512] * 8
        self.layers = nn.ModuleList()
        self.act = nn.SiLU()
        for hidden_dim in hidden_sizes:
            self.layers.append(nn.Linear(current_dim, hidden_dim))
            current_dim = hidden_dim
        self.output_layer = nn.Linear(current_dim, 8)

    def forward(self, x):
        for layer in self.layers:
            x = self.act(layer(x))
        x = torch.sigmoid(self.output_layer(x))
        scaled_links = MIN_LEN + (GLOBAL_MAX_LEN - MIN_LEN) * x[:, :3]
        scaled_S_ratio = x[:, 3]
        scaled_bar_length = MIN_BAR_LEN + (GLOBAL_MAX_LEN - MIN_BAR_LEN) * x[:, 4]
        scaled_base_x = X_MIN + (X_MAX - X_MIN) * x[:, 5]
        scaled_base_y = Y_MIN + (Y_MAX - Y_MIN) * x[:, 6]
        scaled_base_angle = 2 * math.pi * x[:, 7]
        return torch.cat([
            scaled_links,
            scaled_S_ratio.unsqueeze(1),
            scaled_bar_length.unsqueeze(1),
            scaled_base_x.unsqueeze(1),
            scaled_base_y.unsqueeze(1),
            scaled_base_angle.unsqueeze(1),
        ], dim=1)


OUTPUT_PARAMETER_NAMES = (
    "l2", "l3", "l4", "S_ratio", "bar_length", "base_x", "base_y", "base_angle"
)


def scaled_outputs_to_unit_interval(outputs: torch.Tensor) -> torch.Tensor:
    """Invert MechanismNN's deterministic output scaling without changing it."""
    return torch.cat([
        (outputs[:, 0:3] - MIN_LEN) / (GLOBAL_MAX_LEN - MIN_LEN),
        outputs[:, 3:4],
        (outputs[:, 4:5] - MIN_BAR_LEN) / (GLOBAL_MAX_LEN - MIN_BAR_LEN),
        (outputs[:, 5:6] - X_MIN) / (X_MAX - X_MIN),
        (outputs[:, 6:7] - Y_MIN) / (Y_MAX - Y_MIN),
        outputs[:, 7:8] / (2.0 * math.pi),
    ], dim=1)


def new_output_stats_accumulator() -> Dict[str, Any]:
    width = len(OUTPUT_PARAMETER_NAMES)
    return {
        "value_count": 0,
        "finite_count": 0,
        "nonfinite_count": 0,
        "near_low_count": 0,
        "near_high_count": 0,
        "exact_boundary_count": 0,
        "unit_min": float("inf"),
        "unit_max": float("-inf"),
        "max_abs_logit": 0.0,
        "dim_finite_count": [0] * width,
        "dim_saturated_count": [0] * width,
        "dim_near_low_count": [0] * width,
        "dim_near_high_count": [0] * width,
    }


def accumulate_output_stats(accumulator: Dict[str, Any], outputs: torch.Tensor) -> None:
    """Accumulate sigmoid-boundary statistics from scaled model outputs."""
    unit = scaled_outputs_to_unit_interval(outputs.detach())
    finite = torch.isfinite(unit)
    near_low = finite & (unit <= OUTPUT_SATURATION_EPS)
    near_high = finite & (unit >= 1.0 - OUTPUT_SATURATION_EPS)
    saturated = near_low | near_high
    exact_boundary = finite & ((unit <= 0.0) | (unit >= 1.0))

    accumulator["value_count"] += int(unit.numel())
    accumulator["finite_count"] += int(finite.sum().item())
    accumulator["nonfinite_count"] += int((~finite).sum().item())
    accumulator["near_low_count"] += int(near_low.sum().item())
    accumulator["near_high_count"] += int(near_high.sum().item())
    accumulator["exact_boundary_count"] += int(exact_boundary.sum().item())

    finite_values = unit[finite]
    if finite_values.numel() > 0:
        accumulator["unit_min"] = min(
            accumulator["unit_min"], float(finite_values.min().cpu().item())
        )
        accumulator["unit_max"] = max(
            accumulator["unit_max"], float(finite_values.max().cpu().item())
        )
        # The clamp is diagnostic only; it does not affect training.
        diagnostic_unit = finite_values.to(torch.float64).clamp(1e-12, 1.0 - 1e-12)
        abs_logit = torch.abs(torch.logit(diagnostic_unit))
        accumulator["max_abs_logit"] = max(
            accumulator["max_abs_logit"], float(abs_logit.max().cpu().item())
        )

    for index in range(unit.shape[1]):
        accumulator["dim_finite_count"][index] += int(finite[:, index].sum().item())
        accumulator["dim_saturated_count"][index] += int(saturated[:, index].sum().item())
        accumulator["dim_near_low_count"][index] += int(near_low[:, index].sum().item())
        accumulator["dim_near_high_count"][index] += int(near_high[:, index].sum().item())


def finalize_output_stats(accumulator: Dict[str, Any]) -> Dict[str, float]:
    value_count = max(1, int(accumulator["value_count"]))
    finite_count = max(1, int(accumulator["finite_count"]))
    result: Dict[str, float] = {
        "output_nonfinite_fraction": accumulator["nonfinite_count"] / value_count,
        "output_near_low_fraction": accumulator["near_low_count"] / finite_count,
        "output_near_high_fraction": accumulator["near_high_count"] / finite_count,
        "output_saturated_fraction": (
            accumulator["near_low_count"] + accumulator["near_high_count"]
        ) / finite_count,
        "output_exact_boundary_fraction": accumulator["exact_boundary_count"] / finite_count,
        "output_unit_min": (
            accumulator["unit_min"] if np.isfinite(accumulator["unit_min"]) else float("nan")
        ),
        "output_unit_max": (
            accumulator["unit_max"] if np.isfinite(accumulator["unit_max"]) else float("nan")
        ),
        "output_max_abs_logit": float(accumulator["max_abs_logit"]),
    }
    for index, name in enumerate(OUTPUT_PARAMETER_NAMES):
        denominator = max(1, accumulator["dim_finite_count"][index])
        result[f"output_{name}_saturated_fraction"] = (
            accumulator["dim_saturated_count"][index] / denominator
        )
        result[f"output_{name}_near_low_fraction"] = (
            accumulator["dim_near_low_count"][index] / denominator
        )
        result[f"output_{name}_near_high_fraction"] = (
            accumulator["dim_near_high_count"][index] / denominator
        )
    return result


def init_weights(module: nn.Module) -> None:
    if isinstance(module, nn.Linear):
        nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
        nn.init.constant_(module.bias, 0.0)


# ======================
# ===== DATA FUNCTIONS =====
# ======================
def generate_target_point_triples(
    num_samples: int,
    generator: Optional[torch.Generator] = None,
) -> torch.Tensor:
    rand_tensor = torch.rand(num_samples, 6, generator=generator)
    return torch.stack((
        rand_tensor[:, 0] * (X_MAX - X_MIN) + X_MIN,
        rand_tensor[:, 1] * (Y_MAX - Y_MIN) + Y_MIN,
        rand_tensor[:, 2] * (X_MAX - X_MIN) + X_MIN,
        rand_tensor[:, 3] * (Y_MAX - Y_MIN) + Y_MIN,
        rand_tensor[:, 4] * (X_MAX - X_MIN) + X_MIN,
        rand_tensor[:, 5] * (Y_MAX - Y_MIN) + Y_MIN,
    ), dim=1)


def build_dataloader() -> None:
    global dataset, dataloader
    dataset = TensorDataset(training_target_points)
    dataloader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=(device.type == "cuda"),
        generator=dataloader_generator,
        worker_init_fn=worker_seed_init if args.num_workers > 0 else None,
        persistent_workers=False,
    )


def restart_dataloader(regenerate: bool = True, reason: str = "") -> None:
    """C0 uses regenerate=True; R1 recovery never calls this."""
    global training_target_points
    if regenerate:
        training_target_points = generate_target_point_triples(
            NUM_POINTS, generator=training_data_generator
        )
    build_dataloader()
    suffix = f" ({reason})" if reason else ""
    print(f"[INFO] DataLoader restarted{' with fresh dataset' if regenerate else ''}{suffix}.")


# ======================================================================
# ===== SIMULATION AND LOSS FUNCTIONS -- R2 CORRECTED GEOMETRY =====
# ======================================================================
def apply_dynamic_length_constraints(
    predicted_lengths,
    target_points,
    min_len=MIN_LEN,
    global_max=GLOBAL_MAX_LEN,
):
    # Preserved from R1.1 so the geometry experiment changes only the solver
    # and assembly objective. The dynamic length cap can be studied separately.
    main_links = predicted_lengths[:, :3]
    dist1 = torch.norm(target_points[:, 0:2], dim=1)
    dist2 = torch.norm(target_points[:, 2:4], dim=1)
    dist3 = torch.norm(target_points[:, 4:6], dim=1)
    distances = torch.max(torch.max(dist1, dist2), dist3)
    per_sample_max = 2.0 * distances
    max_lengths = torch.min(per_sample_max, torch.full_like(per_sample_max, global_max))
    max_lengths_expanded = max_lengths.unsqueeze(1).expand_as(main_links)
    main_links = torch.clamp_min(main_links, min_len)
    main_links = torch.min(main_links, max_lengths_expanded)
    S_ratio = torch.clamp(predicted_lengths[:, 3], 0.0, 1.0)
    max_link_per_sample = torch.max(torch.stack([
        torch.full_like(main_links[:, 0], L1_FIXED_VALUE),
        main_links[:, 0],
        main_links[:, 1],
        main_links[:, 2],
    ], dim=1), dim=1).values
    max_bar_len = 0.5 * max_link_per_sample
    bar_length = torch.clamp_min(predicted_lengths[:, 4], MIN_BAR_LEN)
    bar_length = torch.min(bar_length, max_bar_len)
    base_x = torch.clamp(predicted_lengths[:, 5], X_MIN, X_MAX)
    base_y = torch.clamp(predicted_lengths[:, 6], Y_MIN, Y_MAX)
    base_angle = torch.remainder(predicted_lengths[:, 7], 2 * math.pi)
    return torch.stack([
        main_links[:, 0],
        main_links[:, 1],
        main_links[:, 2],
        S_ratio,
        bar_length,
        base_x,
        base_y,
        base_angle,
    ], dim=1)


def simulate_four_bar_coupler_point_torch_batch(
    l1,
    l2,
    l3,
    l4,
    theta2_range,
    S_ratio,
    bar_length,
    base_x,
    base_y,
    base_angle,
    bar_angle_offset=math.pi / 2,
    return_diagnostics: bool = False,
):
    """Solve a batched four-bar by direct circle-circle intersection.

    O2=(0,0), O4=(l1,0), and A is the crank endpoint. B is one of the two
    intersections of the circle centered at O4 with radius l4 and the circle
    centered at A with radius l3. ASSEMBLY_BRANCH_SIGN=-1 matches the branch
    used by the previous theta4 = alpha - phi implementation.

    Invalid configurations retain finite coordinates for numerical safety and
    are excluded by valid_assembly_mask. Continuous raw circle violations are
    returned for training.
    """
    l1, l2, l3, l4, S_ratio, bar_length = [
        value[:, None] for value in (l1, l2, l3, l4, S_ratio, bar_length)
    ]
    theta2 = theta2_range[None, :]

    Ax = l2 * torch.cos(theta2)
    Ay = l2 * torch.sin(theta2)

    # Vector from fixed follower pivot O4 to crank endpoint A.
    center_dx = Ax - l1
    center_dy = Ay
    center_d2 = center_dx.square() + center_dy.square()

    scale_sq = torch.maximum(
        torch.maximum(torch.maximum(l1.square(), l2.square()), l3.square()),
        torch.maximum(l4.square(), center_d2),
    ).clamp_min(1.0)
    scale = torch.sqrt(scale_sq)
    d_numeric_floor_sq = D2_NUMERIC_FLOOR_REL * scale_sq
    center_distance = torch.sqrt(center_d2 + d_numeric_floor_sq)
    center_distance_floor = CENTER_DISTANCE_FLOOR_REL * scale
    center_distance_safe = torch.maximum(center_distance, center_distance_floor)
    assembly_tolerance = ASSEMBLY_VALIDITY_TOL_REL * scale

    positive_length_mask = (l3 > MIN_LEN * 0.5) & (l4 > MIN_LEN * 0.5)
    center_valid_mask = center_distance > center_distance_floor
    outer_margin = l3 + l4 - center_distance
    inner_margin = center_distance - torch.abs(l3 - l4)
    valid_assembly_mask = (
        positive_length_mask
        & center_valid_mask
        & (outer_margin >= -assembly_tolerance)
        & (inner_margin >= -assembly_tolerance)
    )

    # Circle intersection measured from O4 along the O4->A unit vector.
    along_raw = (
        l4.square() - l3.square() + center_d2
    ) / (2.0 * center_distance_safe)
    h2_raw = l4.square() - along_raw.square()
    h2_floor = H2_NUMERIC_FLOOR_REL * scale_sq
    h = torch.sqrt(torch.maximum(h2_raw, h2_floor))

    # For invalid configurations, the raw intersection coordinate can become
    # arbitrarily large when the circle centers nearly coincide. Keep the
    # diagnostic/penalty based on along_raw, but bound the unused placeholder
    # coordinates so masked distance calculations cannot overflow.
    along_for_geometry = torch.minimum(
        torch.maximum(along_raw, -l4), l4
    )

    unit_x = center_dx / center_distance_safe
    unit_y = center_dy / center_distance_safe
    perp_x = -unit_y
    perp_y = unit_x

    Bx = l1 + along_for_geometry * unit_x + ASSEMBLY_BRANCH_SIGN * h * perp_x
    By = along_for_geometry * unit_y + ASSEMBLY_BRANCH_SIGN * h * perp_y

    delta_x_BA = Bx - Ax
    delta_y_BA = By - Ay
    coupler_norm_sq = delta_x_BA.square() + delta_y_BA.square()
    coupler_norm = torch.sqrt(
        torch.maximum(coupler_norm_sq, D2_NUMERIC_FLOOR_REL * scale_sq)
    )
    coupler_unit_x = delta_x_BA / coupler_norm
    coupler_unit_y = delta_y_BA / coupler_norm

    offset_cos = math.cos(bar_angle_offset)
    offset_sin = math.sin(bar_angle_offset)
    offset_unit_x = offset_cos * coupler_unit_x - offset_sin * coupler_unit_y
    offset_unit_y = offset_sin * coupler_unit_x + offset_cos * coupler_unit_y

    Sx = Ax + S_ratio * delta_x_BA
    Sy = Ay + S_ratio * delta_y_BA
    Px = Sx + bar_length * offset_unit_x
    Py = Sy + bar_length * offset_unit_y

    cos_a = torch.cos(base_angle)[:, None]
    sin_a = torch.sin(base_angle)[:, None]
    Px_final = cos_a * Px - sin_a * Py + base_x[:, None]
    Py_final = sin_a * Px + cos_a * Py + base_y[:, None]

    # Continuous sampled assembly violations in length units.
    outer_violation = torch.relu(center_distance - (l3 + l4))
    inner_violation = torch.relu(torch.abs(l3 - l4) - center_distance)
    center_violation = torch.relu(center_distance_floor - center_distance)
    sampled_point_violation = outer_violation + inner_violation + center_violation

    # Analytic full-cycle closure: d ranges from |l1-l2| to l1+l2.
    d_min = torch.abs(l1 - l2)
    d_max = l1 + l2
    full_scale = torch.maximum(
        torch.maximum(torch.maximum(l1, l2), l3), l4
    ).clamp_min(1.0)
    full_tolerance = ASSEMBLY_VALIDITY_TOL_REL * full_scale
    full_center_floor = CENTER_DISTANCE_FLOOR_REL * full_scale
    full_outer_violation = torch.relu(d_max - (l3 + l4))
    full_inner_violation = torch.relu(torch.abs(l3 - l4) - d_min)
    full_center_violation = torch.relu(full_center_floor - d_min)
    full_cycle_violation = (
        full_outer_violation + full_inner_violation + full_center_violation
    )
    full_cycle_valid = (
        (full_outer_violation <= full_tolerance)
        & (full_inner_violation <= full_tolerance)
        & (full_center_violation <= full_tolerance)
    )

    # Transmission quality q=sin(mu)^2, where mu is the acute-equivalent
    # transmission angle between coupler and follower. Invalid frames count as
    # q=0 for full-cycle diagnostics. No transmission loss is active in R2.
    h2_nonnegative = torch.clamp(h2_raw, min=0.0)
    transmission_denominator = (
        l3.square() * l4.square()
    ).clamp_min(DISTANCE_SQ_FLOOR)
    transmission_q = torch.clamp(
        center_d2 * h2_nonnegative / transmission_denominator,
        min=0.0,
        max=1.0,
    )
    transmission_q_effective = torch.where(
        valid_assembly_mask, transmission_q, torch.zeros_like(transmission_q)
    )
    valid_counts = valid_assembly_mask.sum(dim=1).clamp_min(1)
    transmission_q_valid_mean = (
        (transmission_q * valid_assembly_mask).sum(dim=1) / valid_counts
    )
    transmission_q_min = transmission_q_effective.min(dim=1).values
    transmission_angle_min_deg = torch.rad2deg(
        torch.asin(torch.sqrt(transmission_q_min.clamp(0.0, 1.0)))
    )
    q15 = math.sin(math.radians(TRANSMISSION_GLOBAL_FLOOR_DEG)) ** 2
    q35 = math.sin(math.radians(TRANSMISSION_TARGET_MIN_DEG)) ** 2

    diagnostics = {
        # Per-sample tensors; callers may average them over a batch.
        "assembly_success_ratio": valid_assembly_mask.float().mean(dim=1),
        "full_cycle_assembly_ratio": full_cycle_valid.float().squeeze(1),
        "sampled_assembly_violation": sampled_point_violation.mean(dim=1),
        "full_cycle_assembly_violation": full_cycle_violation.squeeze(1),
        "outer_assembly_violation": outer_violation.mean(dim=1),
        "inner_assembly_violation": inner_violation.mean(dim=1),
        "center_assembly_violation": center_violation.mean(dim=1),
        "h2_negative_fraction": (h2_raw < 0.0).float().mean(dim=1),
        "h2_floor_fraction": (h2_raw < h2_floor).float().mean(dim=1),
        "transmission_quality_mean": transmission_q_effective.mean(dim=1),
        "transmission_quality_valid_mean": transmission_q_valid_mean,
        "transmission_quality_min": transmission_q_min,
        "transmission_min_angle_deg": transmission_angle_min_deg,
        "transmission_below_15deg_fraction": (
            transmission_q_effective < q15
        ).float().mean(dim=1),
        "transmission_below_35deg_fraction": (
            transmission_q_effective < q35
        ).float().mean(dim=1),
    }

    if return_diagnostics:
        return Px_final, Py_final, valid_assembly_mask, diagnostics
    return Px_final, Py_final, valid_assembly_mask


def compute_mechanism_loss_batch(
    predicted_params,
    target_points,
    num_sim_steps: Optional[int] = None,
):
    """R2 objective: R1.1 distance/constraints plus corrected assembly loss."""
    l2, l3, l4 = predicted_params[:, 0], predicted_params[:, 1], predicted_params[:, 2]
    S_ratio = predicted_params[:, 3]
    bar_length = predicted_params[:, 4]
    base_x = predicted_params[:, 5]
    base_y = predicted_params[:, 6]
    base_angle = predicted_params[:, 7]
    l1 = torch.full_like(l2, L1_FIXED_VALUE)

    steps = NUM_SIM_STEPS if num_sim_steps is None else int(num_sim_steps)
    theta2_range = torch.linspace(0, 2 * math.pi, steps, dtype=l2.dtype, device=l2.device)
    Px, Py, valid_mask, geometry = simulate_four_bar_coupler_point_torch_batch(
        l1,
        l2,
        l3,
        l4,
        theta2_range,
        S_ratio,
        bar_length,
        base_x,
        base_y,
        base_angle,
        return_diagnostics=True,
    )

    invalid_distance_sq = INVALID_DISTANCE ** 2

    def min_dist(tx, ty):
        sqd = (Px - tx[:, None]).square() + (Py - ty[:, None]).square()
        sqd = torch.where(
            valid_mask,
            sqd,
            torch.full_like(sqd, invalid_distance_sq),
        )
        min_sqd = torch.min(sqd, dim=1).values
        min_sqd = torch.nan_to_num(
            min_sqd,
            nan=invalid_distance_sq,
            posinf=invalid_distance_sq,
            neginf=invalid_distance_sq,
        )
        min_sqd = torch.clamp(
            min_sqd,
            min=DISTANCE_SQ_FLOOR,
            max=invalid_distance_sq,
        )
        return torch.sqrt(min_sqd)

    min_dist1, min_dist2, min_dist3 = (
        min_dist(target_points[:, index], target_points[:, index + 1])
        for index in (0, 2, 4)
    )
    loss_dist = (min_dist1 + min_dist2 + min_dist3) / 3.0
    loss_dist = torch.nan_to_num(
        loss_dist,
        nan=INVALID_DISTANCE,
        posinf=INVALID_DISTANCE,
        neginf=INVALID_DISTANCE,
    )

    links = torch.stack([l1, l2, l3, l4], dim=1)
    shortest, shortest_idx = torch.min(links, dim=1)
    longest, longest_idx = torch.max(links, dim=1)
    sum_remaining = links.sum(dim=1) - shortest - longest

    grashof_violation = torch.relu(shortest + longest - sum_remaining)
    penalty_grashof = torch.nan_to_num(
        LAMBDA_GRASHOF * grashof_violation, nan=0.0, posinf=0.0
    )

    penalty_crank_shortness = torch.nan_to_num(
        LAMBDA_CRANK_SHORT * torch.relu(l2 - shortest), nan=0.0, posinf=0.0
    )

    adjacency_ok = (shortest_idx == 1) & ((longest_idx == 0) | (longest_idx == 2))
    penalty_adjacency = torch.where(
        adjacency_ok,
        torch.zeros_like(shortest),
        LAMBDA_ADJACENCY * torch.ones_like(shortest),
    )
    penalty_adjacency = torch.nan_to_num(
        penalty_adjacency, nan=0.0, posinf=0.0
    )

    # Half sampled closure violation and half exact full-cycle closure
    # violation. Both are in length units and remain differentiable outside
    # the feasible set. This replaces the old Boolean-ratio penalty.
    assembly_penalty = LAMBDA_ASSEMBLY * (
        0.5 * geometry["sampled_assembly_violation"]
        + 0.5 * geometry["full_cycle_assembly_violation"]
    )
    assembly_penalty = torch.nan_to_num(
        assembly_penalty, nan=INVALID_DISTANCE, posinf=INVALID_DISTANCE
    )

    # R2 logs transmission quality but deliberately does not optimize it.
    transmission_penalty = torch.zeros_like(loss_dist) * LAMBDA_TRANSMISSION

    total_loss = (
        loss_dist
        + penalty_grashof
        + penalty_crank_shortness
        + penalty_adjacency
        + assembly_penalty
        + transmission_penalty
    )

    components = {
        "distance_loss": loss_dist.mean().item(),
        "grashof_penalty": penalty_grashof.mean().item(),
        "crank_shortness_penalty": penalty_crank_shortness.mean().item(),
        "adjacency_penalty": penalty_adjacency.mean().item(),
        "assembly_penalty": assembly_penalty.mean().item(),
        "transmission_penalty": transmission_penalty.mean().item(),
        "total_loss": total_loss.mean().item(),
    }
    for key in R2_EXTRA_COMPONENT_KEYS:
        if key == "transmission_penalty":
            continue
        components[key] = geometry[key].mean().item()

    return total_loss.mean(), (
        min_dist1.mean().item(),
        min_dist2.mean().item(),
        min_dist3.mean().item(),
    ), components


# ======================
# ===== FIXED VALIDATION =====
# ======================
def evaluate_fixed_validation() -> Dict[str, float]:
    was_training = model.training
    model.eval()
    totals = {
        "loss": 0.0,
        "p1": 0.0,
        "p2": 0.0,
        "p3": 0.0,
        **{key: 0.0 for key in ALL_COMPONENT_KEYS},
    }
    output_accumulator = new_output_stats_accumulator()
    count = 0
    with torch.no_grad():
        for start in range(0, len(fixed_validation_targets), args.validation_batch_size):
            batch_cpu = fixed_validation_targets[start:start + args.validation_batch_size]
            if batch_cpu.numel() == 0:
                continue
            batch = batch_cpu.to(device)
            model_output = model(batch)
            accumulate_output_stats(output_accumulator, model_output)
            raw_pred = torch.nan_to_num(model_output, nan=1.0, posinf=1.0, neginf=1.0)
            predicted_params = apply_dynamic_length_constraints(raw_pred, batch)
            loss, point_dists, components = compute_mechanism_loss_batch(
                predicted_params,
                batch,
                num_sim_steps=VALIDATION_NUM_SIM_STEPS,
            )
            batch_size = batch.shape[0]
            totals["loss"] += loss.item() * batch_size
            totals["p1"] += point_dists[0] * batch_size
            totals["p2"] += point_dists[1] * batch_size
            totals["p3"] += point_dists[2] * batch_size
            for key in ALL_COMPONENT_KEYS:
                totals[key] += components[key] * batch_size
            count += batch_size
    if was_training:
        model.train()
    if count == 0:
        raise RuntimeError("Fixed validation set is empty")
    result = {key: value / count for key, value in totals.items()}
    result["mean_distance"] = (result["p1"] + result["p2"] + result["p3"]) / 3.0
    result.update(finalize_output_stats(output_accumulator))
    return result


# ======================
# ===== CHECKPOINT STATE =====
# ======================
def capture_rng_state() -> Dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": capture_numpy_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "training_data_generator": training_data_generator.get_state(),
        "dataloader_generator": dataloader_generator.get_state(),
    }


def restore_rng_state(state: Optional[Dict[str, Any]]) -> None:
    if not state:
        return
    if state.get("python") is not None:
        random.setstate(state["python"])
    if state.get("numpy") is not None:
        restore_numpy_state(state["numpy"])
    if state.get("torch_cpu") is not None:
        torch.set_rng_state(state["torch_cpu"].cpu())
    if torch.cuda.is_available() and state.get("torch_cuda") is not None:
        torch.cuda.set_rng_state_all([value.cpu() for value in state["torch_cuda"]])
    if state.get("training_data_generator") is not None:
        training_data_generator.set_state(state["training_data_generator"].cpu())
    if state.get("dataloader_generator") is not None:
        dataloader_generator.set_state(state["dataloader_generator"].cpu())


def checkpoint_payload(
    state_epoch: int,
    completed_epoch: int,
    train_loss: float,
    train_mean_distance: float,
    validation: Dict[str, float],
) -> Dict[str, Any]:
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "variant": VARIANT,
        "parent_variant": PARENT_VARIANT,
        "experiment_mode": EXPERIMENT_MODE,
        "baseline_source_sha256": BASELINE_SOURCE_SHA256,
        "parent_source_sha256": PARENT_SOURCE_SHA256,
        "state_epoch": state_epoch,
        "epoch": completed_epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "annealing_scheduler_state_dict": (
            annealing_scheduler.state_dict() if annealing_scheduler is not None else None
        ),
        "loss": train_loss,
        "mean_distance": train_mean_distance,
        "val_loss": validation.get("loss", float("inf")),
        "val_mean_distance": validation.get("mean_distance", float("inf")),
        "val_metrics": dict(validation),
        "num_sim_steps": NUM_SIM_STEPS,
        "lr": current_lr(),
        "training_target_points": training_target_points.detach().cpu(),
        "rng_state": capture_rng_state(),
        "recent_distances": list(recent_dist_deque),
        "recent_validation_distances": list(recent_val_dist_deque),
        "stagnant_epoch_count": stagnant_epoch_count,
        "consecutive_dead_gradient_epochs": consecutive_dead_gradient_epochs,
        "consecutive_dead_catastrophic_epochs": consecutive_dead_catastrophic_epochs,
        "current_state_epoch": current_state_epoch,
        "best_train_loss": best_loss,
        "best_validation_loss": best_val_loss,
        "last_epoch_instrumentation": dict(last_epoch_instrumentation),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def save_checkpoint(
    path: Path,
    state_epoch: int,
    completed_epoch: int,
    train_loss: float,
    train_mean_distance: float,
    validation: Dict[str, float],
) -> None:
    torch.save(
        checkpoint_payload(
            state_epoch=state_epoch,
            completed_epoch=completed_epoch,
            train_loss=train_loss,
            train_mean_distance=train_mean_distance,
            validation=validation,
        ),
        path,
    )


def inspect_checkpoint(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        checkpoint = torch_load(path, map_location="cpu")
    except Exception as exc:
        print(f"[WARN] Could not inspect checkpoint {path}: {exc}")
        return None
    return {
        "path": path,
        "epoch": int(checkpoint.get("state_epoch", checkpoint.get("epoch", -1))),
        "completed_epoch": int(checkpoint.get("epoch", -1)),
        "train_loss": safe_float(checkpoint.get("loss"), float("inf")),
        "train_mean_distance": safe_float(checkpoint.get("mean_distance"), float("inf")),
        "val_loss": safe_float(checkpoint.get("val_loss"), float("inf")),
        "val_mean_distance": safe_float(checkpoint.get("val_mean_distance"), float("inf")),
        "lr": safe_float(checkpoint.get("lr"), float("nan")),
    }


def reset_optimizer(lr: Optional[float] = None) -> None:
    """Baseline helper. R1 recovery intentionally does not call it."""
    global optimizer
    if lr is None:
        lr = INITIAL_LR
    optimizer = torch.optim.AdamW(
        filter(lambda parameter: parameter.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=1e-5,
    )
    clamp_lr(optimizer)
    print(f"[INFO] Optimizer reset with LR = {lr:.2e}")


def reset_model() -> None:
    model.apply(init_weights)
    print("[INFO] Model weights fully reset.")


def clamp_lr(target_optimizer) -> None:
    for group in target_optimizer.param_groups:
        if group["lr"] < MIN_LR:
            group["lr"] = MIN_LR
            print(f"[LR CLAMP] Clamped to {MIN_LR:.1e}")


def load_checkpoint_c0(path: Path | str, load_optimizer: bool = True) -> Tuple[bool, float]:
    """C0 deliberately reproduces V5.3 load semantics."""
    if not path or not Path(path).exists():
        print(f"[WARN] Cannot load checkpoint - path is invalid: {path}")
        return False, float("inf")
    try:
        checkpoint = torch_load(Path(path), map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        if load_optimizer and "optimizer_state_dict" in checkpoint:
            try:
                optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
            except (ValueError, KeyError) as exc:
                print(f"[WARN] Optimizer state mismatch ({exc}) - resetting optimizer.")
                reset_optimizer()
                restart_dataloader(regenerate=True, reason="C0 optimizer mismatch")
        elif load_optimizer:
            print("[WARN] No optimizer state - resetting optimizer.")
            reset_optimizer()
            restart_dataloader(regenerate=True, reason="C0 missing optimizer state")
        loaded_loss = safe_float(checkpoint.get("loss"), float("inf"))
        print(f"[INFO] Loaded checkpoint from {path} (loaded loss = {loaded_loss:.6f})")
        return True, loaded_loss
    except Exception as exc:
        print(f"[ERROR] Failed to load checkpoint {path}: {exc}")
        return False, float("inf")


def restore_checkpoint_r1(path: Path | str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Restore a coherent R1/R1.1/R2 state without replacing the optimizer."""
    global training_target_points, scheduler, annealing_scheduler
    global consecutive_dead_gradient_epochs, consecutive_dead_catastrophic_epochs
    global current_state_epoch, last_completed_epoch, last_epoch_instrumentation
    if not path or not Path(path).exists():
        print(f"[WARN] Cannot restore checkpoint - path is invalid: {path}")
        return False, None
    try:
        checkpoint = torch_load(Path(path), map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])

        if "optimizer_state_dict" not in checkpoint:
            raise KeyError("optimizer_state_dict is required for coherent R2 recovery")
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        if checkpoint.get("scheduler_state_dict") is not None:
            scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        else:
            # Old V5.3 checkpoints did not save scheduler state. Keep the same
            # optimizer object and recreate only the scheduler around it.
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, factor=0.5, patience=20, min_lr=MIN_LR
            )
            print("[WARN] R2 checkpoint lacked scheduler state; scheduler recreated.")

        annealing_scheduler = None  # R1 intentionally disables cosine annealing.

        if checkpoint.get("training_target_points") is not None:
            training_target_points = checkpoint["training_target_points"].detach().cpu()

        restore_rng_state(checkpoint.get("rng_state"))
        build_dataloader()

        recent_dist_deque.clear()
        recent_dist_deque.extend(checkpoint.get("recent_distances", []))
        recent_val_dist_deque.clear()
        recent_val_dist_deque.extend(checkpoint.get("recent_validation_distances", []))
        consecutive_dead_gradient_epochs = int(
            checkpoint.get("consecutive_dead_gradient_epochs", 0)
        )
        consecutive_dead_catastrophic_epochs = int(
            checkpoint.get("consecutive_dead_catastrophic_epochs", 0)
        )
        current_state_epoch = int(
            checkpoint.get(
                "current_state_epoch",
                checkpoint.get("state_epoch", checkpoint.get("epoch", 0)),
            )
        )
        last_completed_epoch = int(checkpoint.get("epoch", current_state_epoch - 1))
        last_epoch_instrumentation = dict(
            checkpoint.get("last_epoch_instrumentation", {})
        )

        if not scheduler_is_attached():
            raise RuntimeError("Scheduler is not attached to the active optimizer after restore")

        metadata = {
            "path": Path(path),
            "epoch": int(checkpoint.get("state_epoch", checkpoint.get("epoch", -1))),
            "completed_epoch": int(checkpoint.get("epoch", -1)),
            "train_loss": safe_float(checkpoint.get("loss"), float("inf")),
            "train_mean_distance": safe_float(checkpoint.get("mean_distance"), float("inf")),
            "val_loss": safe_float(checkpoint.get("val_loss"), float("inf")),
            "val_mean_distance": safe_float(checkpoint.get("val_mean_distance"), float("inf")),
            "val_metrics": checkpoint.get("val_metrics", {}),
            "lr": current_lr(),
            "dead_gradient_streak": consecutive_dead_gradient_epochs,
            "dead_catastrophic_streak": consecutive_dead_catastrophic_epochs,
        }
        print(
            f"[INFO] Coherently restored {path} "
            f"(state epoch {metadata['epoch']}, train loss {metadata['train_loss']:.6f}, "
            f"val loss {metadata['val_loss']:.6f})"
        )
        return True, metadata
    except Exception as exc:
        print(f"[ERROR] Failed coherent restore from {path}: {exc}")
        return False, None


def load_model_only(path: Path | str) -> Tuple[bool, float]:
    if not path or not Path(path).exists():
        return False, float("inf")
    try:
        checkpoint = torch_load(Path(path), map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        return True, safe_float(checkpoint.get("loss"), float("inf"))
    except Exception as exc:
        print(f"[ERROR] Failed to load model from {path}: {exc}")
        return False, float("inf")


def cleanup_old_rollbacks(run_dir: Path, keep_files: Iterable[str]) -> None:
    keep = set(keep_files)
    for checkpoint_path in run_dir.glob("rollback_epoch_*.pth"):
        if checkpoint_path.name not in keep:
            try:
                checkpoint_path.unlink()
            except Exception as exc:
                print(f"[CLEANUP ERROR] Could not delete {checkpoint_path}: {exc}")


def log_bad_batch(epoch_number, batch_idx, target_points, predicted_lengths, reason):
    global bad_batch_logs_this_epoch
    if bad_batch_logs_this_epoch >= MAX_BAD_BATCH_LOGS_PER_EPOCH:
        return
    dataframe = pd.DataFrame({
        "epoch": [epoch_number] * len(target_points),
        "batch_idx": [batch_idx] * len(target_points),
        "reason": [reason] * len(target_points),
        **{
            f"target_x{index + 1}": target_points[:, 2 * index].detach().cpu().numpy()
            for index in range(3)
        },
        **{
            f"target_y{index + 1}": target_points[:, 2 * index + 1].detach().cpu().numpy()
            for index in range(3)
        },
    })
    dataframe.to_csv(
        RUN_DIR / BAD_BATCH_LOG,
        mode="a",
        header=not (RUN_DIR / BAD_BATCH_LOG).exists(),
        index=False,
    )
    bad_batch_logs_this_epoch += 1


# ======================
# ===== RECOVERY LOGIC =====
# ======================
def rollback_and_recover_c0(reason: str) -> bool:
    """Exact behavioral control: preserve the V5.3 recovery defects."""
    global grace_counter, stagnant_epoch_count, global_repeat_to_best

    rolled_back = False
    rollback_type = None
    selected_path: Optional[Path] = None
    selected_epoch: Any = ""
    pre_loss = avg_epoch_loss
    post_loss = float("inf")

    # 1. Recent min-loss from the last ten records.
    if rollback_buffer:
        recent_records = list(rollback_buffer)[-10:]
        best_recent = min(recent_records, key=lambda record: record["train_loss"])
        repeat_count = rollback_repeat_counts.get(best_recent["epoch"], 0)
        if repeat_count < REPEAT_ROLLBACK_LIMIT and best_recent["train_loss"] < pre_loss * 0.95:
            loaded, loaded_loss = load_checkpoint_c0(best_recent["path"])
            if loaded:
                rolled_back = True
                selected_path = best_recent["path"]
                selected_epoch = best_recent["epoch"]
                rollback_type = (
                    f"recent min-loss (epoch {best_recent['epoch']}, "
                    f"loss {best_recent['train_loss']:.4f})"
                )
                post_loss = loaded_loss
                rollback_repeat_counts[best_recent["epoch"]] = repeat_count + 1

    # 2. Medium-depth.  Deliberately loads before the 5% acceptance check.
    if not rolled_back:
        tried_epochs = set()
        for depth in ROLLBACK_DEPTHS:
            target_epoch = max(0, epoch - depth)
            if target_epoch in tried_epochs:
                continue
            tried_epochs.add(target_epoch)
            target_path = RUN_DIR / f"rollback_epoch_{target_epoch}.pth"
            if target_path.exists():
                repeat_count = rollback_repeat_counts.get(target_epoch, 0)
                if repeat_count < REPEAT_ROLLBACK_LIMIT:
                    loaded, loaded_loss = load_checkpoint_c0(target_path)
                    if loaded and loaded_loss < pre_loss * 0.95:
                        rolled_back = True
                        selected_path = target_path
                        selected_epoch = target_epoch
                        rollback_type = f"medium rollback ({depth} epochs back)"
                        post_loss = loaded_loss
                        rollback_repeat_counts[target_epoch] = repeat_count + 1
                        break

    # 3. Best-train checkpoint.  Also deliberately loads before acceptance.
    if (
        not rolled_back
        and best_checkpoint_path is not None
        and global_repeat_to_best < REPEAT_ROLLBACK_LIMIT
    ):
        loaded, loaded_loss = load_checkpoint_c0(best_checkpoint_path)
        if loaded and loaded_loss < pre_loss * 0.95:
            rolled_back = True
            selected_path = Path(best_checkpoint_path)
            selected_epoch = "best"
            rollback_type = "best checkpoint"
            post_loss = loaded_loss
            global_repeat_to_best += 1

    if rolled_back:
        lr_from_loaded_checkpoint = current_lr()
        if epoch < EARLY_RESET_EPOCHS:
            safe_lr = INITIAL_LR * 2.0
        elif epoch < 500:
            safe_lr = max(lr_from_loaded_checkpoint * 1.5, MIN_LR)
        else:
            safe_lr = max(lr_from_loaded_checkpoint * 1.2, MIN_LR)

        # Deliberately discard the restored AdamW state and disconnect scheduler.
        reset_optimizer(lr=safe_lr)
        clamp_lr(optimizer)
        restart_dataloader(regenerate=True, reason="C0 rollback")
        grace_counter = GRACE_EPOCHS_AFTER_ROLLBACK

        label_text = f"{reason} | {rollback_type}"
        log_rollback_event(
            epoch + 1,
            pre_loss,
            post_loss,
            lr_from_loaded_checkpoint,
            safe_lr,
            label_text,
            checkpoint_path=str(selected_path or ""),
            checkpoint_epoch=selected_epoch,
            lr_loaded=lr_from_loaded_checkpoint,
        )
        log_event(
            epoch + 1,
            "rollback",
            reason=label_text,
            checkpoint=str(selected_path or ""),
            checkpoint_epoch=selected_epoch,
            train_loss_before=pre_loss,
            checkpoint_train_loss=post_loss,
            lr_before=lr_from_loaded_checkpoint,
            lr_loaded=lr_from_loaded_checkpoint,
            lr_after=safe_lr,
            details=(
                "C0 baseline semantics: optimizer replaced, data regenerated, "
                f"grace={grace_counter}; scheduler_attached={scheduler_is_attached()}"
            ),
        )
        print(
            f"[RECOVERY] C0 rollback complete ({rollback_type}) - "
            f"pre-loss {pre_loss:.6f} -> post-loss {post_loss:.6f} - "
            f"grace {grace_counter} epochs"
        )
        stagnant_epoch_count = 0
        return True

    print(f"[RECOVERY] No suitable checkpoint for rollback ({reason})")
    log_event(epoch + 1, "rollback_failed", reason=reason, train_loss_before=pre_loss)
    return False


def candidate_record(path: Path, source: str, priority: int) -> Optional[Dict[str, Any]]:
    record = inspect_checkpoint(path)
    if record is None:
        return None
    record["source"] = source
    record["priority"] = priority
    return record


def select_r1_checkpoint(
    reason: str,
    pre_train_loss: float,
    pre_val_loss: float,
    preferred_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Inspect/rank metadata first. No model mutation occurs in this function."""
    candidates = []
    seen = set()

    def add(record: Optional[Dict[str, Any]]) -> None:
        if record is None:
            return
        key = str(Path(record["path"]).resolve())
        if key in seen:
            return
        seen.add(key)
        candidates.append(record)

    if preferred_path is not None:
        add(candidate_record(preferred_path, "pre-epoch state", -1))

    for record in list(rollback_buffer)[-10:]:
        copied = dict(record)
        copied["source"] = "recent"
        copied["priority"] = 0
        add(copied)

    for depth in ROLLBACK_DEPTHS:
        target_epoch = max(0, epoch - depth)
        add(candidate_record(
            RUN_DIR / f"rollback_epoch_{target_epoch}.pth",
            f"{depth}-epoch depth",
            1,
        ))

    add(candidate_record(BEST_VALIDATION_CHECKPOINT, "best fixed validation", 2))

    hard_reason = reason in {
        "nonfinite_model_output",
        "nonfinite_loss",
        "nonfinite_gradient",
        "no_valid_batches",
        "early_bad_launch",
        "dead_gradient_catastrophic_validation",
    }
    eligible = []
    for record in candidates:
        repeat_key = str(Path(record["path"]).resolve())
        if rollback_repeat_counts.get(repeat_key, 0) >= REPEAT_ROLLBACK_LIMIT:
            continue
        train_loss = record["train_loss"]
        val_loss = record["val_loss"]
        if not (np.isfinite(train_loss) or np.isfinite(val_loss)):
            continue
        if hard_reason:
            eligible.append(record)
            continue
        train_improves = (
            np.isfinite(pre_train_loss)
            and np.isfinite(train_loss)
            and train_loss < pre_train_loss * 0.95
        )
        val_improves = (
            np.isfinite(pre_val_loss)
            and np.isfinite(val_loss)
            and val_loss < pre_val_loss * 0.98
        )
        if train_improves or val_improves:
            eligible.append(record)

    if not eligible:
        return None

    # Rank by the fixed validation score before loading anything. Training
    # loss is the fallback for legacy/initial checkpoints with no finite
    # validation score; source priority and recency break ties only.
    eligible.sort(key=lambda record: (
        record["val_loss"] if np.isfinite(record["val_loss"]) else (
            record["train_loss"] if np.isfinite(record["train_loss"]) else float("inf")
        ),
        record["train_loss"] if np.isfinite(record["train_loss"]) else float("inf"),
        record["priority"],
        -record["epoch"],
    ))
    return eligible[0]


def rollback_and_recover_r1(
    reason: str,
    pre_train_loss: float,
    pre_val_loss: float,
    preferred_path: Optional[Path] = None,
) -> bool:
    global grace_counter, stagnant_epoch_count, prev_epoch_loss, prev_val_loss
    global avg_epoch_loss, avg_epoch_distance, last_val_metrics, disable_warmup_after_recovery
    global consecutive_dead_gradient_epochs, consecutive_dead_catastrophic_epochs
    global current_state_epoch, last_completed_epoch, last_epoch_instrumentation

    selected = select_r1_checkpoint(
        reason=reason,
        pre_train_loss=pre_train_loss,
        pre_val_loss=pre_val_loss,
        preferred_path=preferred_path,
    )
    if selected is None:
        lr_before_failure = current_lr()
        recovery_lr = max(MIN_LR, lr_before_failure * RECOVERY_LR_FACTOR)
        for group in optimizer.param_groups:
            group["lr"] = recovery_lr
        clamp_lr(optimizer)
        if hasattr(scheduler, "_last_lr"):
            scheduler._last_lr = [group["lr"] for group in optimizer.param_groups]
        grace_counter = PLATEAU_COOLDOWN_EPOCHS
        stagnant_epoch_count = 0
        disable_warmup_after_recovery = True
        print(
            f"[RECOVERY] R2 found no eligible checkpoint ({reason}); "
            f"applied in-place LR backoff {lr_before_failure:.2e} -> {recovery_lr:.2e}"
        )
        log_rollback_event(
            epoch + 1,
            pre_train_loss,
            pre_train_loss,
            lr_before_failure,
            recovery_lr,
            f"{reason} | no eligible checkpoint; LR backoff only",
            val_loss_before=pre_val_loss,
            checkpoint_val_loss=pre_val_loss,
            lr_loaded="",
        )
        log_event(
            epoch + 1,
            "rollback_failed_lr_backoff",
            reason=reason,
            train_loss_before=pre_train_loss,
            val_loss_before=pre_val_loss,
            lr_before=lr_before_failure,
            lr_after=recovery_lr,
            details="No checkpoint met the recovery threshold; model/optimizer state kept.",
        )
        return False

    lr_before_failure = current_lr()
    loaded, metadata = restore_checkpoint_r1(selected["path"])
    if not loaded or metadata is None:
        recovery_lr = max(MIN_LR, lr_before_failure * RECOVERY_LR_FACTOR)
        for group in optimizer.param_groups:
            group["lr"] = recovery_lr
        clamp_lr(optimizer)
        if hasattr(scheduler, "_last_lr"):
            scheduler._last_lr = [group["lr"] for group in optimizer.param_groups]
        grace_counter = PLATEAU_COOLDOWN_EPOCHS
        stagnant_epoch_count = 0
        disable_warmup_after_recovery = True
        log_event(
            epoch + 1,
            "rollback_failed_lr_backoff",
            reason=f"{reason} | restore error",
            checkpoint=str(selected["path"]),
            lr_before=lr_before_failure,
            lr_after=recovery_lr,
            details="Checkpoint restore failed; retained current state and reduced LR.",
        )
        print(
            f"[RECOVERY] R2 restore failed; applied in-place LR backoff "
            f"{lr_before_failure:.2e} -> {recovery_lr:.2e}"
        )
        return False

    loaded_lr = current_lr()
    recovery_lr = max(MIN_LR, min(lr_before_failure, loaded_lr) * RECOVERY_LR_FACTOR)
    for group in optimizer.param_groups:
        group["lr"] = recovery_lr
    clamp_lr(optimizer)
    if hasattr(scheduler, "_last_lr"):
        scheduler._last_lr = [group["lr"] for group in optimizer.param_groups]

    if not scheduler_is_attached():
        raise RuntimeError("R2 recovery detached the scheduler from the optimizer")

    grace_counter = PLATEAU_COOLDOWN_EPOCHS
    stagnant_epoch_count = 0
    consecutive_dead_gradient_epochs = 0
    consecutive_dead_catastrophic_epochs = 0
    current_state_epoch = int(metadata["epoch"])
    last_completed_epoch = int(metadata.get("completed_epoch", current_state_epoch - 1))
    last_epoch_instrumentation = dict(
        metadata.get("last_epoch_instrumentation", last_epoch_instrumentation)
    )
    prev_epoch_loss = metadata["train_loss"]
    prev_val_loss = metadata["val_loss"]
    avg_epoch_loss = metadata["train_loss"]
    avg_epoch_distance = metadata["train_mean_distance"]
    if metadata.get("val_metrics"):
        last_val_metrics = dict(metadata["val_metrics"])
    else:
        last_val_metrics = {
            "loss": metadata["val_loss"],
            "mean_distance": metadata["val_mean_distance"],
        }
    disable_warmup_after_recovery = True

    repeat_key = str(Path(selected["path"]).resolve())
    rollback_repeat_counts[repeat_key] = rollback_repeat_counts.get(repeat_key, 0) + 1

    label_text = f"{reason} | {selected['source']}"
    log_rollback_event(
        epoch + 1,
        pre_train_loss,
        metadata["train_loss"],
        lr_before_failure,
        recovery_lr,
        label_text,
        checkpoint_path=str(selected["path"]),
        checkpoint_epoch=metadata["epoch"],
        val_loss_before=pre_val_loss,
        checkpoint_val_loss=metadata["val_loss"],
        lr_loaded=loaded_lr,
    )
    log_event(
        epoch + 1,
        "rollback",
        reason=label_text,
        checkpoint=str(selected["path"]),
        checkpoint_epoch=metadata["epoch"],
        train_loss_before=pre_train_loss,
        val_loss_before=pre_val_loss,
        checkpoint_train_loss=metadata["train_loss"],
        checkpoint_val_loss=metadata["val_loss"],
        lr_before=lr_before_failure,
        lr_loaded=loaded_lr,
        lr_after=recovery_lr,
        details=(
            "R2 coherent restore: AdamW moments, scheduler, data, sampler/RNG "
            f"restored; no fresh data; plateau cooldown={grace_counter}"
        ),
    )
    print(
        f"[RECOVERY] R2 restored {selected['source']} checkpoint "
        f"(state epoch {metadata['epoch']}) - train {pre_train_loss:.6f} -> "
        f"{metadata['train_loss']:.6f}, val {pre_val_loss:.6f} -> "
        f"{metadata['val_loss']:.6f}, LR {lr_before_failure:.2e} -> {recovery_lr:.2e}"
    )
    return True


# ======================
# ===== METRIC LOGGING =====
# ======================
def log_epoch_metrics(
    epoch_number: int,
    train_loss: float,
    train_mean_distance: float,
    point_distances: Tuple[float, float, float],
    components: Dict[str, float],
    validation: Dict[str, float],
    grad_norm_mean: float,
    grad_norm_max: float,
    num_batches: int,
    elapsed: float,
    event: str = "",
    instrumentation: Optional[Dict[str, Any]] = None,
) -> None:
    instrumentation = dict(instrumentation or {})
    row: Dict[str, Any] = {
        "epoch": epoch_number,
        "train_loss": train_loss,
        "train_optimized_loss": train_loss,
        "train_unclamped_loss": instrumentation.get("train_unclamped_loss", train_loss),
        "train_mean_distance": train_mean_distance,
        "train_p1_distance": point_distances[0],
        "train_p2_distance": point_distances[1],
        "train_p3_distance": point_distances[2],
        "distance_loss": components.get("distance_loss", float("nan")),
        "crank_shortness_penalty": components.get("crank_shortness_penalty", float("nan")),
        "grashof_penalty": components.get("grashof_penalty", float("nan")),
        "adjacency_penalty": components.get("adjacency_penalty", float("nan")),
        "assembly_penalty": components.get("assembly_penalty", float("nan")),
        "validation_loss": validation.get("loss", float("nan")),
        "validation_mean_distance": validation.get("mean_distance", float("nan")),
        "validation_p1_distance": validation.get("p1", float("nan")),
        "validation_p2_distance": validation.get("p2", float("nan")),
        "validation_p3_distance": validation.get("p3", float("nan")),
        "lr": current_lr(),
        "grad_norm_mean": grad_norm_mean,
        "grad_norm_max": grad_norm_max,
        "num_batches": num_batches,
        "num_sim_steps": NUM_SIM_STEPS,
        "grace_or_cooldown": grace_counter,
        "best_train_loss": best_loss,
        "best_validation_loss": best_val_loss,
        "optimizer_id": id(optimizer),
        "scheduler_optimizer_id": id(getattr(scheduler, "optimizer", None)),
        "scheduler_attached": scheduler_is_attached(),
        "elapsed_seconds": elapsed,
        "event": event,
        "loss_clamped_batches": instrumentation.get("loss_clamped_batches", 0),
        "loss_clamp_fraction": instrumentation.get("loss_clamp_fraction", 0.0),
        "max_unclamped_batch_loss": instrumentation.get(
            "max_unclamped_batch_loss", float("nan")
        ),
        "max_optimized_batch_loss": instrumentation.get(
            "max_optimized_batch_loss", float("nan")
        ),
        "zero_grad_batches": instrumentation.get("zero_grad_batches", 0),
        "zero_grad_batch_fraction": instrumentation.get("zero_grad_batch_fraction", 0.0),
        "clamped_zero_grad_batches": instrumentation.get("clamped_zero_grad_batches", 0),
        "dead_gradient_epoch": instrumentation.get("dead_gradient_epoch", False),
        "dead_gradient_streak": instrumentation.get(
            "dead_gradient_streak", consecutive_dead_gradient_epochs
        ),
        "catastrophic_validation": instrumentation.get("catastrophic_validation", False),
        "catastrophic_validation_threshold": instrumentation.get(
            "catastrophic_validation_threshold", float("nan")
        ),
        "dead_catastrophic_streak": instrumentation.get(
            "dead_catastrophic_streak", consecutive_dead_catastrophic_epochs
        ),
    }
    for key in ALL_COMPONENT_KEYS:
        row[key] = components.get(key, float("nan"))
        row[f"validation_{key}"] = validation.get(key, float("nan"))
    for key, value in instrumentation.items():
        if key.startswith("output_"):
            row[key] = value
    for key, value in validation.items():
        if key.startswith("output_"):
            row[f"validation_{key}"] = value
    append_csv(METRICS_LOG, row)


# ======================
# ===== EVALUATION / PLOTTING =====
# ======================
def evaluate_model_statistics(num_test_samples: int) -> None:
    model.eval()
    test_points = generate_target_point_triples(
        num_test_samples, generator=evaluation_generator
    ).to(device)
    weighted_totals = {"loss": 0.0, **{key: 0.0 for key in ALL_COMPONENT_KEYS}}
    count = 0
    batch_losses = []
    with torch.no_grad():
        for start in range(0, num_test_samples, BATCH_SIZE):
            batch_points = test_points[start:start + BATCH_SIZE]
            if batch_points.numel() == 0:
                continue
            raw_pred = torch.nan_to_num(
                model(batch_points), nan=1.0, posinf=1.0, neginf=1.0
            )
            batch_params = apply_dynamic_length_constraints(raw_pred, batch_points)
            loss, _, components = compute_mechanism_loss_batch(
                batch_params, batch_points, num_sim_steps=DEFAULT_NUM_SIM_STEPS
            )
            batch_size = batch_points.shape[0]
            batch_losses.append(loss.item())
            weighted_totals["loss"] += loss.item() * batch_size
            for key in ALL_COMPONENT_KEYS:
                weighted_totals[key] += components[key] * batch_size
            count += batch_size

    if count == 0:
        print("[WARN] No samples were evaluated.")
        return
    metrics = {key: value / count for key, value in weighted_totals.items()}
    losses_array = np.asarray(batch_losses)
    print("\nModel Test Evaluation")
    print(f"Samples tested: {count}")
    print(f"Mean Loss: {metrics['loss']:.6f}")
    print(f"Median batch loss: {np.median(losses_array):.6f}")
    print(f"Std Dev batch loss: {losses_array.std():.6f}")
    print(f"Max batch loss: {losses_array.max():.6f}")
    print(f"Sampled assembly validity: {metrics['assembly_success_ratio'] * 100:.2f}%")
    print(f"True full-cycle assembly: {metrics['full_cycle_assembly_ratio'] * 100:.2f}%")
    print(
        "Mean per-mechanism minimum transmission angle: "
        f"{metrics['transmission_min_angle_deg']:.2f} deg"
    )
    print(
        f"Frames below {TRANSMISSION_GLOBAL_FLOOR_DEG:.0f} deg: "
        f"{metrics['transmission_below_15deg_fraction'] * 100:.2f}%"
    )


def plot_training_metrics() -> None:
    if not total_loss_history:
        return
    epochs_axis = range(1, len(total_loss_history) + 1)
    epsilon = 1e-6
    figure = plt.figure(figsize=(14, 10))

    axis1 = figure.add_subplot(2, 2, 1)
    axis1.plot(epochs_axis, p1_history, label="P1 Distance")
    axis1.plot(epochs_axis, p2_history, label="P2 Distance")
    axis1.plot(epochs_axis, p3_history, label="P3 Distance")
    axis1.plot(epochs_axis, mean_dist_history, label="Mean Distance", linestyle="--")
    axis1.set_xlabel("Epoch")
    axis1.set_ylabel("Distance")
    axis1.set_title("Training distances")
    axis1.legend()

    axis2 = figure.add_subplot(2, 2, 2)
    axis2.plot(epochs_axis, [max(value, epsilon) for value in dist_loss_history], label="Distance")
    axis2.plot(epochs_axis, [max(value, epsilon) for value in crank_short_history], label="Crank short")
    axis2.plot(epochs_axis, [max(value, epsilon) for value in grashof_history], label="Grashof")
    axis2.plot(epochs_axis, [max(value, epsilon) for value in adjacency_history], label="Adjacency")
    axis2.plot(epochs_axis, [max(value, epsilon) for value in assembly_history], label="Assembly")
    axis2.plot(epochs_axis, [max(value, epsilon) for value in total_loss_history], label="Total", linewidth=2)
    axis2.set_yscale("log")
    axis2.set_title("Loss components")
    axis2.legend()

    axis3 = figure.add_subplot(2, 2, 3)
    axis3.plot(epochs_axis, [max(value, epsilon) for value in total_loss_history])
    axis3.set_yscale("log")
    axis3.set_title("Total training loss")
    if ROLLBACK_LOG.exists():
        try:
            rollback_frame = pd.read_csv(ROLLBACK_LOG)
            for rollback_epoch in rollback_frame["epoch"].values:
                axis3.axvline(rollback_epoch, linestyle="--", alpha=0.5)
        except Exception as exc:
            print(f"[WARN] Could not add rollback markers: {exc}")

    axis4 = figure.add_subplot(2, 2, 4)
    axis4.plot(epochs_axis, validation_loss_history, label="Fixed validation loss")
    axis4.plot(epochs_axis, validation_distance_history, label="Fixed validation mean distance")
    axis4.set_yscale("log")
    axis4.set_title("Fixed validation")
    axis4.legend()

    figure.suptitle(VARIANT)
    figure.tight_layout()
    output_path = RUN_DIR / "training_metrics.png"
    figure.savefig(output_path, dpi=150)
    if not args.headless:
        plt.show()
    plt.close(figure)
    print(f"[INFO] Training plot saved to {output_path}")


def plot_mechanism_vs_targets(target_points: torch.Tensor) -> None:
    model.eval()
    with torch.no_grad():
        target_batch = target_points.unsqueeze(0).to(device)
        predicted_params = model(target_batch)
        predicted_params = apply_dynamic_length_constraints(predicted_params, target_batch)
        l2, l3, l4 = predicted_params[:, 0], predicted_params[:, 1], predicted_params[:, 2]
        S_ratio = predicted_params[:, 3]
        bar_length = predicted_params[:, 4]
        base_x = predicted_params[:, 5]
        base_y = predicted_params[:, 6]
        base_angle = predicted_params[:, 7]
        l1 = torch.full_like(l2, L1_FIXED_VALUE)
        theta2_range = torch.linspace(0, 2 * math.pi, DEFAULT_NUM_SIM_STEPS, device=device)
        Px, Py, valid_mask = simulate_four_bar_coupler_point_torch_batch(
            l1, l2, l3, l4, theta2_range, S_ratio, bar_length,
            base_x, base_y, base_angle,
        )

    Px_np = Px.squeeze(0).cpu().numpy()
    Py_np = Py.squeeze(0).cpu().numpy()
    valid_np = valid_mask.squeeze(0).cpu().numpy().astype(bool)
    Px_np = np.where(valid_np, Px_np, np.nan)
    Py_np = np.where(valid_np, Py_np, np.nan)
    targets_np = target_batch.squeeze(0).cpu().numpy().reshape(3, 2)
    distances = []
    for tx, ty in targets_np:
        dists = np.sqrt((Px_np - tx) ** 2 + (Py_np - ty) ** 2)
        distances.append(float(np.nanmin(dists)))

    print("\nFinal distances to plotted targets:")
    for index, distance in enumerate(distances, 1):
        print(f"  Point {index}: {distance:.6f}")

    figure = plt.figure(figsize=(6, 6))
    axis = figure.add_subplot(1, 1, 1)
    axis.plot(Px_np, Py_np, label="Coupler Path")
    axis.scatter(targets_np[:, 0], targets_np[:, 1], marker="x", s=100, label="Target Points")
    for (tx, ty), distance in zip(targets_np, distances):
        axis.text(tx + 0.02, ty + 0.02, f"{distance:.4f}")
    axis.set_xlabel("X")
    axis.set_ylabel("Y")
    axis.set_title("Final Mechanism vs Target Points")
    axis.legend()
    axis.axis("equal")
    axis.grid(True, linestyle="--", alpha=0.6)
    output_path = RUN_DIR / "sample_mechanism.png"
    figure.savefig(output_path, dpi=150)
    if not args.headless:
        plt.show()
    plt.close(figure)
    print(f"[INFO] Mechanism plot saved to {output_path}")


# ======================
# ===== MAIN SETUP =====
# ======================
rollback_buffer = deque(maxlen=ROLLBACK_HISTORY_SIZE)
recent_dist_deque = deque(maxlen=10)
recent_val_dist_deque = deque(maxlen=10)
rollback_repeat_counts: Dict[Any, int] = {}
grace_counter = 0
boost_active = False
boost_end_epoch: Optional[int] = None
p1_history, p2_history, p3_history = [], [], []
dist_loss_history, crank_short_history = [], []
grashof_history, adjacency_history, assembly_history, total_loss_history = [], [], [], []
lr_history, mean_dist_history = [], []
validation_loss_history, validation_distance_history = [], []
best_loss = float("inf")
best_val_loss = float("inf")
best_val_mean_distance = float("inf")
epochs_since_improvement = 0
epochs_since_val_improvement = 0
prev_epoch_loss: Optional[float] = None
prev_val_loss: Optional[float] = None
best_checkpoint_path: Optional[Path] = None
one_degree_reached = False
one_degree_epoch_counter = 0
annealing_started = False
stagnant_epoch_count = 0
global_repeat_to_best = 0
consecutive_resets = 0
disable_warmup_after_recovery = False
avg_epoch_loss = float("inf")
avg_epoch_distance = float("inf")
NUM_SIM_STEPS = INITIAL_NUM_SIM_STEPS
bad_batch_logs_this_epoch = 0
consecutive_dead_gradient_epochs = 0
consecutive_dead_catastrophic_epochs = 0
current_state_epoch = 0
last_completed_epoch = -1
last_epoch_instrumentation: Dict[str, Any] = {}

fixed_validation_targets = generate_target_point_triples(
    args.validation_samples, generator=validation_generator
)
torch.save(fixed_validation_targets, VALIDATION_TARGETS_PATH)

training_target_points = generate_target_point_triples(
    NUM_POINTS, generator=training_data_generator
)
torch.save(training_target_points, INITIAL_TRAINING_TARGETS_PATH)
build_dataloader()

model = MechanismNN().to(device)
model.apply(init_weights)
optimizer = torch.optim.AdamW(model.parameters(), lr=INITIAL_LR, weight_decay=1e-5)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, factor=0.5, patience=20, min_lr=MIN_LR
)
annealing_scheduler = None

initial_validation = evaluate_fixed_validation()
last_val_metrics = dict(initial_validation)
best_val_loss = initial_validation["loss"]
best_val_mean_distance = initial_validation["mean_distance"]
prev_val_loss = initial_validation["loss"]

# Save configuration and environment before training.
script_path = Path(__file__).resolve()
script_hash = file_sha256(script_path)
SOURCE_HASH_PATH.write_text(
    f"script_sha256  {script_hash}\n"
    f"parent_sha256   {PARENT_SOURCE_SHA256}\n"
    f"baseline_sha256 {BASELINE_SOURCE_SHA256}\n",
    encoding="utf-8",
)

config = {
    "variant": VARIANT,
    "parent_variant": PARENT_VARIANT,
    "experiment_mode": EXPERIMENT_MODE,
    "seed": args.seed,
    "deterministic": DETERMINISTIC,
    "baseline_source_sha256": BASELINE_SOURCE_SHA256,
    "parent_source_sha256": PARENT_SOURCE_SHA256,
    "script_sha256": script_hash,
    "num_epochs": NUM_EPOCHS,
    "num_points": NUM_POINTS,
    "batch_size": BATCH_SIZE,
    "initial_lr": INITIAL_LR,
    "min_lr": MIN_LR,
    "warmup_epochs": WARMUP_EPOCHS,
    "simulation_ramp": [INITIAL_NUM_SIM_STEPS, FINAL_NUM_SIM_STEPS, RAMP_START_EPOCH, RAMP_END_EPOCH],
    "fixed_validation_samples": args.validation_samples,
    "fixed_validation_steps": VALIDATION_NUM_SIM_STEPS,
    "enable_lr_boosts": ENABLE_LR_BOOSTS,
    "enable_cosine_annealing": ENABLE_COSINE_ANNEALING,
    "enable_periodic_data_refresh": ENABLE_PERIODIC_DATA_REFRESH,
    "recovery_lr_factor": RECOVERY_LR_FACTOR,
    "train_spike_validation_veto": True,
    "dead_gradient_norm_threshold": DEAD_GRADIENT_NORM_THRESHOLD,
    "dead_gradient_patience": DEAD_GRADIENT_PATIENCE,
    "catastrophic_validation_factor": CATASTROPHIC_VALIDATION_FACTOR,
    "catastrophic_validation_abs_delta": CATASTROPHIC_VALIDATION_ABS_DELTA,
    "output_saturation_epsilon": OUTPUT_SATURATION_EPS,
    "output_saturation_warning_fraction": OUTPUT_SATURATION_WARNING_FRACTION,
    "geometry_solver": "direct_circle_circle_intersection",
    "assembly_branch_sign": ASSEMBLY_BRANCH_SIGN,
    "assembly_validity_tolerance_relative": ASSEMBLY_VALIDITY_TOL_REL,
    "center_distance_floor_relative": CENTER_DISTANCE_FLOOR_REL,
    "h2_numeric_floor_relative": H2_NUMERIC_FLOOR_REL,
    "assembly_penalty_weight": LAMBDA_ASSEMBLY,
    "transmission_loss_weight": LAMBDA_TRANSMISSION,
    "transmission_target_min_degrees_diagnostic": TRANSMISSION_TARGET_MIN_DEG,
    "transmission_global_floor_degrees_diagnostic": TRANSMISSION_GLOBAL_FLOOR_DEG,
    "hard_nearest_point_objective_preserved": True,
    "terminal_state_reporting": True,
    "command_line": sys.argv,
}
CONFIG_PATH.write_text(json.dumps(config, indent=2, default=str), encoding="utf-8")

environment = {
    "python": sys.version,
    "platform": platform.platform(),
    "torch": str(torch.__version__),
    "cuda_available": torch.cuda.is_available(),
    "torch_cuda": str(torch.version.cuda),
    "cudnn": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None,
    "device": str(device),
    "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
}
ENVIRONMENT_PATH.write_text(json.dumps(environment, indent=2, default=str), encoding="utf-8")

# Initial state is a matched starting point for seed-aligned C0/R1 runs.
save_checkpoint(
    INITIAL_STATE_PATH,
    state_epoch=0,
    completed_epoch=-1,
    train_loss=float("inf"),
    train_mean_distance=float("inf"),
    validation=initial_validation,
)
save_checkpoint(
    BEST_VALIDATION_CHECKPOINT,
    state_epoch=0,
    completed_epoch=-1,
    train_loss=float("inf"),
    train_mean_distance=float("inf"),
    validation=initial_validation,
)
print(
    f"Initial fixed validation: loss={initial_validation['loss']:.6f}, "
    f"mean distance={initial_validation['mean_distance']:.6f}, "
    f"full-cycle assembly={initial_validation['full_cycle_assembly_ratio']:.1%}, "
    f"min transmission={initial_validation['transmission_min_angle_deg']:.2f} deg"
)

start_epoch = 0
if args.load_checkpoint:
    if IS_R1:
        loaded, metadata = restore_checkpoint_r1(args.load_checkpoint)
        if not loaded or metadata is None:
            raise SystemExit(1)
        start_epoch = max(0, int(metadata["epoch"]))
        current_state_epoch = start_epoch
        last_completed_epoch = int(metadata.get("completed_epoch", start_epoch - 1))
        avg_epoch_loss = metadata["train_loss"]
        avg_epoch_distance = metadata["train_mean_distance"]
        prev_epoch_loss = metadata["train_loss"] if np.isfinite(metadata["train_loss"]) else None
        prev_val_loss = metadata["val_loss"] if np.isfinite(metadata["val_loss"]) else None
        last_val_metrics = evaluate_fixed_validation()
    else:
        loaded, loaded_loss = load_checkpoint_c0(args.load_checkpoint)
        if not loaded:
            raise SystemExit(1)
        prev_epoch_loss = loaded_loss if np.isfinite(loaded_loss) else None
        last_val_metrics = evaluate_fixed_validation()

# ======================
# ===== TRAINING LOOP =====
# ======================
for epoch in range(start_epoch, NUM_EPOCHS):
    epoch_start_time = time.time()
    bad_batch_logs_this_epoch = 0

    if epoch < RAMP_START_EPOCH:
        NUM_SIM_STEPS = INITIAL_NUM_SIM_STEPS
    elif epoch < RAMP_END_EPOCH:
        ramp_progress = (epoch - RAMP_START_EPOCH) / (RAMP_END_EPOCH - RAMP_START_EPOCH)
        NUM_SIM_STEPS = int(
            INITIAL_NUM_SIM_STEPS
            + (FINAL_NUM_SIM_STEPS - INITIAL_NUM_SIM_STEPS) * ramp_progress
        )
    else:
        NUM_SIM_STEPS = FINAL_NUM_SIM_STEPS

    if (
        ENABLE_COSINE_ANNEALING
        and NUM_SIM_STEPS == FINAL_NUM_SIM_STEPS
        and not one_degree_reached
    ):
        one_degree_reached = True
        one_degree_epoch_counter = 0
        annealing_started = True
        annealing_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=ANNEALING_EPOCHS, eta_min=MIN_LR
        )
        print(
            f"[INFO] 1-degree resolution reached at epoch {epoch + 1}; "
            f"starting cosine annealing over {ANNEALING_EPOCHS} epochs."
        )

    if epoch < WARMUP_EPOCHS and not (IS_R1 and disable_warmup_after_recovery):
        warmup_lr = INITIAL_LR * ((epoch + 1) / WARMUP_EPOCHS)
        for group in optimizer.param_groups:
            group["lr"] = warmup_lr
        clamp_lr(optimizer)

    if (
        ENABLE_LR_BOOSTS
        and epoch >= LR_BOOST_START
        and epoch % LR_BOOST_INTERVAL == 0
        and epoch != 0
    ):
        for group in optimizer.param_groups:
            group["lr"] *= LR_BOOST_FACTOR
        clamp_lr(optimizer)
        boost_active = True
        boost_end_epoch = epoch + LR_BOOST_DURATION
        print(f"[LR BOOST] Boosting LR to {current_lr():.2e} for {LR_BOOST_DURATION} epochs.")
        log_event(epoch + 1, "lr_boost_start", lr_after=current_lr())

    if ENABLE_LR_BOOSTS and boost_active and boost_end_epoch is not None and epoch >= boost_end_epoch:
        for group in optimizer.param_groups:
            group["lr"] /= LR_BOOST_FACTOR
        clamp_lr(optimizer)
        boost_active = False
        print(f"[LR BOOST END] Restoring LR to {current_lr():.2e}")
        log_event(epoch + 1, "lr_boost_end", lr_after=current_lr())

    # Pre-epoch checkpoint: the exact state to which an epoch-level failure can return.
    checkpoint_path = RUN_DIR / f"rollback_epoch_{epoch}.pth"
    checkpoint_train_loss = avg_epoch_loss if epoch > start_epoch or np.isfinite(avg_epoch_loss) else float("inf")
    checkpoint_train_distance = avg_epoch_distance if np.isfinite(avg_epoch_distance) else float("inf")
    save_checkpoint(
        checkpoint_path,
        state_epoch=epoch,
        completed_epoch=epoch - 1,
        train_loss=checkpoint_train_loss,
        train_mean_distance=checkpoint_train_distance,
        validation=last_val_metrics,
    )
    rollback_buffer.append({
        "path": checkpoint_path,
        "epoch": epoch,
        "completed_epoch": epoch - 1,
        "train_loss": checkpoint_train_loss,
        "train_mean_distance": checkpoint_train_distance,
        "val_loss": last_val_metrics.get("loss", float("inf")),
        "val_mean_distance": last_val_metrics.get("mean_distance", float("inf")),
    })

    if len(rollback_buffer) >= ROLLBACK_HISTORY_SIZE:
        keep_files = {Path(record["path"]).name for record in rollback_buffer}
        cleanup_old_rollbacks(RUN_DIR, keep_files)

    model.train()
    epoch_loss = 0.0
    epoch_unclamped_loss = 0.0
    epoch_distance = 0.0
    num_batches = 0
    epoch_p1_dist = epoch_p2_dist = epoch_p3_dist = 0.0
    epoch_dist_loss = epoch_crank_short = epoch_grashof = 0.0
    epoch_adjacency = epoch_assembly = 0.0
    epoch_r2_components = {key: 0.0 for key in R2_EXTRA_COMPONENT_KEYS}
    grad_norm_sum = 0.0
    grad_norm_max = 0.0
    loss_clamped_batches = 0
    zero_grad_batches = 0
    clamped_zero_grad_batches = 0
    max_unclamped_batch_loss = float("-inf")
    max_optimized_batch_loss = float("-inf")
    output_stats_accumulator = new_output_stats_accumulator()
    hard_failure_reason: Optional[str] = None

    for batch_idx, (batch_target_points,) in enumerate(dataloader):
        batch_target_points = batch_target_points.to(device)
        optimizer.zero_grad(set_to_none=True)

        model_output = model(batch_target_points)
        accumulate_output_stats(output_stats_accumulator, model_output)
        if not bool(torch.isfinite(model_output).all().item()):
            hard_failure_reason = "nonfinite_model_output"
            log_bad_batch(
                epoch + 1,
                batch_idx,
                batch_target_points,
                model_output,
                hard_failure_reason,
            )
            break

        raw_pred = torch.nan_to_num(
            model_output, nan=1.0, posinf=1.0, neginf=1.0
        )
        predicted_params = apply_dynamic_length_constraints(raw_pred, batch_target_points)
        loss, point_dists, loss_components = compute_mechanism_loss_batch(
            predicted_params, batch_target_points
        )

        if not torch.isfinite(loss):
            hard_failure_reason = "nonfinite_loss"
            log_bad_batch(
                epoch + 1,
                batch_idx,
                batch_target_points,
                predicted_params,
                hard_failure_reason,
            )
            break

        unclamped_loss_value = float(loss.detach().cpu().item())
        loss_was_clamped = False
        if (
            prev_epoch_loss is not None
            and np.isfinite(prev_epoch_loss)
            and unclamped_loss_value > prev_epoch_loss * MAX_LOSS_FACTOR
        ):
            clamp_limit = prev_epoch_loss * MAX_LOSS_FACTOR
            loss = torch.clamp(loss, max=clamp_limit)
            loss_was_clamped = True
            loss_clamped_batches += 1

        optimized_loss_value = float(loss.detach().cpu().item())
        loss.backward()
        grad_norm_tensor = torch.nn.utils.clip_grad_norm_(
            model.parameters(), max_norm=MAX_GRAD_NORM
        )
        grad_norm_value = float(grad_norm_tensor.detach().cpu().item())

        if not np.isfinite(grad_norm_value):
            optimizer.zero_grad(set_to_none=True)
            hard_failure_reason = "nonfinite_gradient"
            log_bad_batch(
                epoch + 1,
                batch_idx,
                batch_target_points,
                predicted_params,
                hard_failure_reason,
            )
            break

        if grad_norm_value <= DEAD_GRADIENT_NORM_THRESHOLD:
            zero_grad_batches += 1
            if loss_was_clamped:
                clamped_zero_grad_batches += 1

        optimizer.step()

        epoch_p1_dist += point_dists[0]
        epoch_p2_dist += point_dists[1]
        epoch_p3_dist += point_dists[2]
        epoch_dist_loss += loss_components["distance_loss"]
        epoch_crank_short += loss_components["crank_shortness_penalty"]
        epoch_grashof += loss_components["grashof_penalty"]
        epoch_adjacency += loss_components["adjacency_penalty"]
        epoch_assembly += loss_components["assembly_penalty"]
        for component_name in R2_EXTRA_COMPONENT_KEYS:
            epoch_r2_components[component_name] += loss_components[component_name]
        epoch_unclamped_loss += unclamped_loss_value
        epoch_loss += optimized_loss_value
        max_unclamped_batch_loss = max(max_unclamped_batch_loss, unclamped_loss_value)
        max_optimized_batch_loss = max(max_optimized_batch_loss, optimized_loss_value)
        epoch_distance += sum(point_dists) / 3.0
        grad_norm_sum += grad_norm_value
        grad_norm_max = max(grad_norm_max, grad_norm_value)
        num_batches += 1

    if hard_failure_reason is not None:
        elapsed = time.time() - epoch_start_time
        partial_instrumentation: Dict[str, Any] = finalize_output_stats(
            output_stats_accumulator
        )
        partial_instrumentation.update({
            "train_unclamped_loss": (
                epoch_unclamped_loss / num_batches if num_batches else float("inf")
            ),
            "loss_clamped_batches": loss_clamped_batches,
            "loss_clamp_fraction": loss_clamped_batches / max(1, num_batches),
            "max_unclamped_batch_loss": (
                max_unclamped_batch_loss if np.isfinite(max_unclamped_batch_loss)
                else float("nan")
            ),
            "max_optimized_batch_loss": (
                max_optimized_batch_loss if np.isfinite(max_optimized_batch_loss)
                else float("nan")
            ),
            "zero_grad_batches": zero_grad_batches,
            "zero_grad_batch_fraction": zero_grad_batches / max(1, num_batches),
            "clamped_zero_grad_batches": clamped_zero_grad_batches,
        })
        recovered = rollback_and_recover_r1(
            hard_failure_reason,
            pre_train_loss=float("inf"),
            pre_val_loss=float("inf"),
            preferred_path=checkpoint_path,
        )
        log_epoch_metrics(
            epoch + 1,
            float("inf"),
            float("inf"),
            (float("nan"),) * 3,
            {},
            last_val_metrics,
            grad_norm_sum / max(1, num_batches),
            grad_norm_max,
            num_batches,
            elapsed,
            event=f"{hard_failure_reason}:{'recovered' if recovered else 'failed'}",
            instrumentation=partial_instrumentation,
        )
        if recovered:
            continue
        print("[FATAL] R2 could not recover from a hard numerical failure.")
        break

    if num_batches == 0:
        elapsed = time.time() - epoch_start_time
        if IS_R1:
            recovered = rollback_and_recover_r1(
                "no_valid_batches",
                pre_train_loss=float("inf"),
                pre_val_loss=float("inf"),
                preferred_path=checkpoint_path,
            )
            empty_epoch_instrumentation = finalize_output_stats(
                output_stats_accumulator
            )
            log_epoch_metrics(
                epoch + 1,
                float("inf"),
                float("inf"),
                (float("nan"),) * 3,
                {},
                last_val_metrics,
                0.0,
                0.0,
                0,
                elapsed,
                event=f"no_valid_batches:{'recovered' if recovered else 'failed'}",
                instrumentation=empty_epoch_instrumentation,
            )
            if recovered:
                continue
        print(f"[WARN] Epoch {epoch + 1} had no completed batches; stopping.")
        break

    avg_epoch_loss = epoch_loss / num_batches
    avg_epoch_distance = epoch_distance / num_batches
    avg_p1 = epoch_p1_dist / num_batches
    avg_p2 = epoch_p2_dist / num_batches
    avg_p3 = epoch_p3_dist / num_batches
    avg_components = {
        "distance_loss": epoch_dist_loss / num_batches,
        "crank_shortness_penalty": epoch_crank_short / num_batches,
        "grashof_penalty": epoch_grashof / num_batches,
        "adjacency_penalty": epoch_adjacency / num_batches,
        "assembly_penalty": epoch_assembly / num_batches,
    }
    avg_components.update({
        key: value / num_batches for key, value in epoch_r2_components.items()
    })
    avg_grad_norm = grad_norm_sum / num_batches

    should_validate = IS_R1 or ((epoch + 1) % args.validation_interval == 0)
    if should_validate:
        last_val_metrics = evaluate_fixed_validation()
    current_val_loss = last_val_metrics["loss"]
    current_val_distance = last_val_metrics["mean_distance"]
    current_state_epoch = epoch + 1
    last_completed_epoch = epoch

    avg_unclamped_loss = epoch_unclamped_loss / num_batches
    output_stats = finalize_output_stats(output_stats_accumulator)
    dead_gradient_epoch = grad_norm_max <= DEAD_GRADIENT_NORM_THRESHOLD
    if dead_gradient_epoch:
        consecutive_dead_gradient_epochs += 1
    else:
        consecutive_dead_gradient_epochs = 0

    if np.isfinite(best_val_loss):
        catastrophic_validation_threshold = max(
            best_val_loss * CATASTROPHIC_VALIDATION_FACTOR,
            best_val_loss + CATASTROPHIC_VALIDATION_ABS_DELTA,
        )
    else:
        catastrophic_validation_threshold = ABSOLUTE_PLATEAU_THRESHOLD
    catastrophic_validation = (
        np.isfinite(current_val_loss)
        and current_val_loss > catastrophic_validation_threshold
    )
    if dead_gradient_epoch and catastrophic_validation:
        consecutive_dead_catastrophic_epochs += 1
    else:
        consecutive_dead_catastrophic_epochs = 0

    epoch_instrumentation: Dict[str, Any] = dict(output_stats)
    epoch_instrumentation.update({
        "train_unclamped_loss": avg_unclamped_loss,
        "loss_clamped_batches": loss_clamped_batches,
        "loss_clamp_fraction": loss_clamped_batches / num_batches,
        "max_unclamped_batch_loss": max_unclamped_batch_loss,
        "max_optimized_batch_loss": max_optimized_batch_loss,
        "zero_grad_batches": zero_grad_batches,
        "zero_grad_batch_fraction": zero_grad_batches / num_batches,
        "clamped_zero_grad_batches": clamped_zero_grad_batches,
        "dead_gradient_epoch": dead_gradient_epoch,
        "dead_gradient_streak": consecutive_dead_gradient_epochs,
        "catastrophic_validation": catastrophic_validation,
        "catastrophic_validation_threshold": catastrophic_validation_threshold,
        "dead_catastrophic_streak": consecutive_dead_catastrophic_epochs,
    })

    previous_saturation = safe_float(
        last_epoch_instrumentation.get("output_saturated_fraction", 0.0), 0.0
    )
    if (
        output_stats["output_saturated_fraction"]
        >= OUTPUT_SATURATION_WARNING_FRACTION
        and previous_saturation < OUTPUT_SATURATION_WARNING_FRACTION
    ):
        print(
            f"[SATURATION WARNING] {output_stats['output_saturated_fraction']:.1%} "
            f"of model outputs are within {OUTPUT_SATURATION_EPS:g} of a sigmoid boundary."
        )
        log_event(
            epoch + 1,
            "output_saturation_warning",
            train_loss_before=avg_epoch_loss,
            val_loss_before=current_val_loss,
            lr_before=current_lr(),
            details=(
                f"saturated_fraction={output_stats['output_saturated_fraction']:.8f}; "
                f"exact_boundary_fraction={output_stats['output_exact_boundary_fraction']:.8f}; "
                f"max_abs_logit={output_stats['output_max_abs_logit']:.6f}"
            ),
        )
    if loss_clamped_batches > 0:
        log_event(
            epoch + 1,
            "loss_clamp_active",
            train_loss_before=avg_unclamped_loss,
            checkpoint_train_loss=avg_epoch_loss,
            lr_before=current_lr(),
            details=(
                f"clamped_batches={loss_clamped_batches}/{num_batches}; "
                f"clamped_zero_grad_batches={clamped_zero_grad_batches}; "
                f"max_raw={max_unclamped_batch_loss:.8f}; "
                f"max_optimized={max_optimized_batch_loss:.8f}"
            ),
        )
    last_epoch_instrumentation = dict(epoch_instrumentation)

    p1_history.append(avg_p1)
    p2_history.append(avg_p2)
    p3_history.append(avg_p3)
    dist_loss_history.append(avg_components["distance_loss"])
    crank_short_history.append(avg_components["crank_shortness_penalty"])
    grashof_history.append(avg_components["grashof_penalty"])
    adjacency_history.append(avg_components["adjacency_penalty"])
    assembly_history.append(avg_components["assembly_penalty"])
    total_loss_history.append(avg_epoch_loss)
    lr_history.append(current_lr())
    mean_dist_history.append(avg_epoch_distance)
    validation_loss_history.append(current_val_loss)
    validation_distance_history.append(current_val_distance)
    recent_dist_deque.append(avg_epoch_distance)
    recent_val_dist_deque.append(current_val_distance)

    elapsed = time.time() - epoch_start_time
    print(
        f"Epoch {epoch + 1:4d}/{NUM_EPOCHS} | "
        f"TrainMeanDist: {avg_epoch_distance:.4f} | TrainLoss: {avg_epoch_loss:.6f} | "
        f"RawLoss: {avg_unclamped_loss:.6f} | "
        f"ValMeanDist: {current_val_distance:.4f} | ValLoss: {current_val_loss:.6f} | "
        f"LR: {current_lr():.2e} | GradMax: {grad_norm_max:.3e} | "
        f"AsmFull T/V: {avg_components['full_cycle_assembly_ratio']:.1%}/"
        f"{last_val_metrics['full_cycle_assembly_ratio']:.1%} | "
        f"ValMuMin: {last_val_metrics['transmission_min_angle_deg']:.1f}deg | "
        f"Clamp: {loss_clamped_batches / num_batches:.1%} | "
        f"Sat: {output_stats['output_saturated_fraction']:.1%} | Time: {elapsed:.2f}s"
    )

    # R2 retains hard-failure protection that bypasses cooldown and all ordinary plateau
    # logic. Two consecutive dead-gradient epochs are required, and fixed
    # validation must also be catastrophically worse than the best seen state.
    if consecutive_dead_catastrophic_epochs >= DEAD_GRADIENT_PATIENCE:
        event_label = "r1_1_dead_gradient_catastrophic_validation"
        print(
            f"[HARD FAILURE] GradMax <= {DEAD_GRADIENT_NORM_THRESHOLD:.1e} for "
            f"{consecutive_dead_catastrophic_epochs} catastrophic epochs; "
            f"ValLoss {current_val_loss:.6f} > threshold "
            f"{catastrophic_validation_threshold:.6f}. Restoring immediately."
        )
        log_event(
            epoch + 1,
            event_label,
            reason="dead_gradient_catastrophic_validation",
            train_loss_before=avg_epoch_loss,
            val_loss_before=current_val_loss,
            lr_before=current_lr(),
            details=(
                f"dead_gradient_streak={consecutive_dead_gradient_epochs}; "
                f"dead_catastrophic_streak={consecutive_dead_catastrophic_epochs}; "
                f"zero_grad_batches={zero_grad_batches}/{num_batches}; "
                f"saturation={output_stats['output_saturated_fraction']:.8f}; "
                f"loss_clamp_fraction={loss_clamped_batches / num_batches:.8f}"
            ),
        )
        recovered = rollback_and_recover_r1(
            "dead_gradient_catastrophic_validation",
            pre_train_loss=avg_epoch_loss,
            pre_val_loss=current_val_loss,
            preferred_path=checkpoint_path,
        )
        log_epoch_metrics(
            epoch + 1, avg_epoch_loss, avg_epoch_distance,
            (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
            avg_grad_norm, grad_norm_max, num_batches, elapsed,
            event=f"{event_label}:{'recovered' if recovered else 'failed'}",
            instrumentation=epoch_instrumentation,
        )
        if recovered:
            continue
        print("[FATAL] R2 could not recover from the dead-gradient state.")
        break

    # Best-by-training checkpoint preserves the R1 criterion for comparison.
    if avg_epoch_loss < best_loss - EARLY_STOP_MIN_DELTA:
        best_loss = avg_epoch_loss
        best_checkpoint_path = BEST_TRAIN_CHECKPOINT
        epochs_since_improvement = 0
        save_checkpoint(
            BEST_TRAIN_CHECKPOINT,
            state_epoch=epoch + 1,
            completed_epoch=epoch,
            train_loss=avg_epoch_loss,
            train_mean_distance=avg_epoch_distance,
            validation=last_val_metrics,
        )
        print(f"[INFO] Saved best training-loss checkpoint ({best_loss:.6f})")
    else:
        epochs_since_improvement += 1

    if current_val_loss < best_val_loss - EARLY_STOP_MIN_DELTA:
        best_val_loss = current_val_loss
        best_val_mean_distance = current_val_distance
        epochs_since_val_improvement = 0
        save_checkpoint(
            BEST_VALIDATION_CHECKPOINT,
            state_epoch=epoch + 1,
            completed_epoch=epoch,
            train_loss=avg_epoch_loss,
            train_mean_distance=avg_epoch_distance,
            validation=last_val_metrics,
        )
        print(f"[INFO] Saved best fixed-validation checkpoint ({best_val_loss:.6f})")
    else:
        epochs_since_val_improvement += 1

    event_label = ""

    if avg_epoch_distance <= TARGET_MEAN_DIST:
        event_label = "target_reached"
        log_epoch_metrics(
            epoch + 1, avg_epoch_loss, avg_epoch_distance,
            (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
            avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
            instrumentation=epoch_instrumentation,
        )
        print(
            f"[TARGET REACHED] MeanDist {avg_epoch_distance:.4f} <= "
            f"{TARGET_MEAN_DIST:.4f}; stopping training."
        )
        break

    if grace_counter > 0:
        grace_counter -= 1

    # ---------- Early bad-launch handling ----------
    if not IS_R1:
        early_bad_launch = (
            epoch < EARLY_RESET_EPOCHS
            and avg_epoch_loss > ABSOLUTE_PLATEAU_THRESHOLD
            and (prev_epoch_loss is None or avg_epoch_loss > prev_epoch_loss * 2.0)
        )
        if early_bad_launch:
            if consecutive_resets >= MAX_CONSECUTIVE_RESETS and best_checkpoint_path:
                print(
                    f"[EARLY RESET LIMIT] {consecutive_resets} consecutive resets; "
                    "falling back to best checkpoint."
                )
                load_checkpoint_c0(best_checkpoint_path)
                reset_optimizer(lr=INITIAL_LR * 2.0)
                restart_dataloader(regenerate=True, reason="C0 early-reset fallback")
                consecutive_resets = 0
                event_label = "c0_early_reset_best"
            else:
                print(
                    f"[EARLY RESET] Degenerate start (loss {avg_epoch_loss:.4f}); "
                    "resetting model, optimizer, and data."
                )
                reset_model()
                reset_optimizer(lr=INITIAL_LR * 2.0)
                restart_dataloader(regenerate=True, reason="C0 early reset")
                consecutive_resets += 1
                event_label = "c0_early_reset_full"
            grace_counter = GRACE_EPOCHS_AFTER_ROLLBACK
            stagnant_epoch_count = 0
            log_event(
                epoch + 1,
                event_label,
                train_loss_before=avg_epoch_loss,
                lr_after=current_lr(),
                details=f"scheduler_attached={scheduler_is_attached()}",
            )
            log_epoch_metrics(
                epoch + 1, avg_epoch_loss, avg_epoch_distance,
                (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
                instrumentation=epoch_instrumentation,
            )
            continue
        consecutive_resets = 0
    else:
        # Do not judge a launch until warm-up has completed. Restore the exact
        # pre-epoch state and lower LR; never randomize model/data here.
        early_bad_launch = (
            WARMUP_EPOCHS <= epoch < EARLY_RESET_EPOCHS
            and avg_epoch_loss > ABSOLUTE_PLATEAU_THRESHOLD
            and (prev_epoch_loss is None or avg_epoch_loss > prev_epoch_loss * 2.0)
        )
        if early_bad_launch:
            consecutive_resets += 1
            recovered = rollback_and_recover_r1(
                "early_bad_launch",
                pre_train_loss=avg_epoch_loss,
                pre_val_loss=current_val_loss,
                preferred_path=checkpoint_path,
            )
            event_label = f"r1_early_bad_launch:{'recovered' if recovered else 'failed'}"
            log_epoch_metrics(
                epoch + 1, avg_epoch_loss, avg_epoch_distance,
                (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
                instrumentation=epoch_instrumentation,
            )
            if recovered:
                continue
            if consecutive_resets >= MAX_CONSECUTIVE_RESETS:
                print("[FATAL] Repeated R2 early-launch recovery failures.")
                break
        else:
            consecutive_resets = 0

    # ---------- Plateau handling ----------
    if not IS_R1:
        is_plateau = False
        current_plateau_epochs = PLATEAU_EPOCHS if epoch >= 50 else 10000
        recent_average = sum(recent_dist_deque) / len(recent_dist_deque)
        mean_dist_stagnant = avg_epoch_distance >= recent_average
        if (
            mean_dist_stagnant
            or avg_epoch_loss > best_loss * PLATEAU_MULT
            or avg_epoch_loss > ABSOLUTE_PLATEAU_THRESHOLD
        ):
            stagnant_epoch_count += 1
            if stagnant_epoch_count >= current_plateau_epochs:
                is_plateau = True
        else:
            stagnant_epoch_count = 0

        if is_plateau:
            if grace_counter > 0:
                print(f"[GRACE] {grace_counter} epochs left; skipping plateau rollback")
            else:
                recovered = rollback_and_recover_c0("plateau")
                event_label = f"c0_plateau_rollback:{'recovered' if recovered else 'failed'}"
                log_epoch_metrics(
                    epoch + 1, avg_epoch_loss, avg_epoch_distance,
                    (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                    avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
                    instrumentation=epoch_instrumentation,
                )
                continue
    else:
        recent_val_average = sum(recent_val_dist_deque) / len(recent_val_dist_deque)
        validation_stagnant = current_val_distance >= recent_val_average
        if validation_stagnant:
            stagnant_epoch_count += 1
        else:
            stagnant_epoch_count = 0
        if stagnant_epoch_count >= PLATEAU_EPOCHS:
            if grace_counter > 0:
                print(f"[COOLDOWN] {grace_counter} epochs left; plateau notice suppressed")
            else:
                print(
                    "[PLATEAU] Fixed validation has stagnated; no rollback. "
                    "ReduceLROnPlateau remains the LR authority."
                )
                log_event(
                    epoch + 1,
                    "plateau_no_rollback",
                    val_loss_before=current_val_loss,
                    lr_before=current_lr(),
                )
                grace_counter = PLATEAU_COOLDOWN_EPOCHS
            stagnant_epoch_count = 0

    # ---------- Spike handling ----------
    if not IS_R1:
        if (
            epoch >= SPIKE_MIN_EPOCH
            and prev_epoch_loss is not None
            and np.isfinite(prev_epoch_loss)
            and avg_epoch_loss > prev_epoch_loss * SPIKE_THRESHOLD
        ):
            if grace_counter > 0:
                print(f"[GRACE] {grace_counter} epochs left; skipping spike rollback")
            else:
                recovered = rollback_and_recover_c0("spike")
                event_label = f"c0_spike_rollback:{'recovered' if recovered else 'failed'}"
                log_epoch_metrics(
                    epoch + 1, avg_epoch_loss, avg_epoch_distance,
                    (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                    avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
                    instrumentation=epoch_instrumentation,
                )
                continue
    else:
        train_spike = (
            epoch >= SPIKE_MIN_EPOCH
            and prev_epoch_loss is not None
            and np.isfinite(prev_epoch_loss)
            and avg_epoch_loss > prev_epoch_loss * SPIKE_THRESHOLD
        )
        validation_spike = (
            epoch >= SPIKE_MIN_EPOCH
            and prev_val_loss is not None
            and np.isfinite(prev_val_loss)
            and current_val_loss > prev_val_loss * VALIDATION_SPIKE_THRESHOLD
        )
        validation_improved = (
            train_spike
            and prev_val_loss is not None
            and np.isfinite(prev_val_loss)
            and np.isfinite(current_val_loss)
            and current_val_loss < prev_val_loss - EARLY_STOP_MIN_DELTA
        )
        if train_spike and validation_improved and not validation_spike:
            # A training-set jump can be caused by the discrete objective or a
            # data-distribution change. Do not discard a model that improved on
            # the fixed validation set; record the disagreement instead.
            event_label = "r1_train_spike_validation_improved_no_rollback"
            print(
                f"[SPIKE CHECK] Train loss rose {prev_epoch_loss:.6f} -> "
                f"{avg_epoch_loss:.6f}, but fixed validation improved "
                f"{prev_val_loss:.6f} -> {current_val_loss:.6f}; no rollback."
            )
            log_event(
                epoch + 1,
                event_label,
                train_loss_before=prev_epoch_loss,
                val_loss_before=prev_val_loss,
                checkpoint_train_loss=avg_epoch_loss,
                checkpoint_val_loss=current_val_loss,
                lr_before=current_lr(),
            )
        elif train_spike or validation_spike:
            reason = "train_and_validation_spike" if train_spike and validation_spike else (
                "train_spike" if train_spike else "validation_spike"
            )
            # Spike protection is always active; cooldown never suppresses it.
            recovered = rollback_and_recover_r1(
                reason,
                pre_train_loss=avg_epoch_loss,
                pre_val_loss=current_val_loss,
                preferred_path=checkpoint_path,
            )
            event_label = f"r1_{reason}:{'recovered' if recovered else 'failed'}"
            log_epoch_metrics(
                epoch + 1, avg_epoch_loss, avg_epoch_distance,
                (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
                instrumentation=epoch_instrumentation,
            )
            if recovered:
                continue

    # ---------- Scheduler ----------
    prev_epoch_loss = avg_epoch_loss
    prev_val_loss = current_val_loss
    lr_before_scheduler = current_lr()
    if IS_R1:
        scheduler.step(current_val_loss)
    else:
        scheduler.step(avg_epoch_loss)
        if annealing_started and annealing_scheduler is not None:
            annealing_scheduler.step()
    clamp_lr(optimizer)
    if current_lr() < lr_before_scheduler:
        log_event(
            epoch + 1,
            "scheduler_lr_reduction",
            lr_before=lr_before_scheduler,
            lr_after=current_lr(),
            val_loss_before=current_val_loss if IS_R1 else "",
            train_loss_before=avg_epoch_loss if not IS_R1 else "",
        )
        event_label = "scheduler_lr_reduction"

    if one_degree_reached:
        one_degree_epoch_counter += 1

    if (
        ENABLE_PERIODIC_DATA_REFRESH
        and (epoch + 1) % 200 == 0
        and epoch + 1 <= DATALOADER_RESTART_EPOCH
    ):
        restart_dataloader(regenerate=True, reason="C0 periodic refresh")
        log_event(epoch + 1, "periodic_data_refresh")
        event_label = "periodic_data_refresh"

    log_epoch_metrics(
        epoch + 1, avg_epoch_loss, avg_epoch_distance,
        (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
        avg_grad_norm, grad_norm_max, num_batches, elapsed, event=event_label,
        instrumentation=epoch_instrumentation,
    )

    stopping_counter = epochs_since_val_improvement if IS_R1 else epochs_since_improvement
    if stopping_counter >= EARLY_STOP_PATIENCE:
        criterion = "fixed validation" if IS_R1 else "training loss"
        print(
            f"[EARLY STOP] No {criterion} improvement for "
            f"{EARLY_STOP_PATIENCE} epochs; stopping."
        )
        break

# ======================
# ===== POST-TRAINING =====
# ======================
keep_files = {
    Path(record["path"]).name for record in rollback_buffer
}
cleanup_old_rollbacks(RUN_DIR, keep_files)

# Capture and evaluate the live terminal state before loading any selected
# checkpoint. This prevents a rescued earlier checkpoint from being mistaken
# for the state that actually existed when the loop ended.
terminal_validation = evaluate_fixed_validation()
terminal_train_loss = avg_epoch_loss if np.isfinite(avg_epoch_loss) else float("inf")
terminal_train_distance = (
    avg_epoch_distance if np.isfinite(avg_epoch_distance) else float("inf")
)
save_checkpoint(
    TERMINAL_STATE_CHECKPOINT,
    state_epoch=current_state_epoch,
    completed_epoch=last_completed_epoch,
    train_loss=terminal_train_loss,
    train_mean_distance=terminal_train_distance,
    validation=terminal_validation,
)
terminal_summary = {
    "variant": VARIANT,
    "state": "terminal_live_before_checkpoint_reload",
    "state_epoch": current_state_epoch,
    "completed_epoch": last_completed_epoch,
    "train_loss": terminal_train_loss,
    "train_mean_distance": terminal_train_distance,
    "fixed_validation": terminal_validation,
    "lr": current_lr(),
    "scheduler_attached": scheduler_is_attached(),
    "dead_gradient_streak": consecutive_dead_gradient_epochs,
    "dead_catastrophic_streak": consecutive_dead_catastrophic_epochs,
    "last_epoch_instrumentation": last_epoch_instrumentation,
    "checkpoint": str(TERMINAL_STATE_CHECKPOINT),
}
TERMINAL_SUMMARY_PATH.write_text(
    json.dumps(terminal_summary, indent=2, default=str), encoding="utf-8"
)
print(
    f"[TERMINAL LIVE STATE] epoch={current_state_epoch} | "
    f"train loss={terminal_train_loss:.6f} | "
    f"fixed-validation loss={terminal_validation['loss']:.6f} | "
    f"mean distance={terminal_validation['mean_distance']:.6f} | "
    f"LR={current_lr():.2e} | "
    f"full-cycle assembly={terminal_validation.get('full_cycle_assembly_ratio', float('nan')):.1%} | "
    f"min transmission={terminal_validation.get('transmission_min_angle_deg', float('nan')):.2f} deg | "
    f"saturation={terminal_validation.get('output_saturated_fraction', float('nan')):.1%}"
)

comparison_rows = []


def add_comparison_row(
    state_label: str,
    checkpoint_path: Path,
    metadata: Dict[str, Any],
    validation: Dict[str, float],
) -> None:
    row: Dict[str, Any] = {
        "state": state_label,
        "checkpoint": str(checkpoint_path),
        "state_epoch": metadata.get("epoch", ""),
        "completed_epoch": metadata.get("completed_epoch", ""),
        "stored_train_loss": metadata.get("train_loss", float("nan")),
        "stored_train_mean_distance": metadata.get("train_mean_distance", float("nan")),
        "stored_validation_loss": metadata.get("val_loss", float("nan")),
        "stored_validation_mean_distance": metadata.get("val_mean_distance", float("nan")),
        "evaluated_validation_loss": validation.get("loss", float("nan")),
        "evaluated_validation_mean_distance": validation.get("mean_distance", float("nan")),
        "stored_lr": metadata.get("lr", float("nan")),
    }
    for key, value in validation.items():
        if key.startswith("output_") or key in ALL_COMPONENT_KEYS:
            row[key] = value
    comparison_rows.append(row)


add_comparison_row(
    "terminal_live",
    TERMINAL_STATE_CHECKPOINT,
    {
        "epoch": current_state_epoch,
        "completed_epoch": last_completed_epoch,
        "train_loss": terminal_train_loss,
        "train_mean_distance": terminal_train_distance,
        "val_loss": terminal_validation["loss"],
        "val_mean_distance": terminal_validation["mean_distance"],
        "lr": current_lr(),
    },
    terminal_validation,
)

for state_label, checkpoint_candidate in (
    ("best_training_checkpoint", BEST_TRAIN_CHECKPOINT),
    ("best_validation_checkpoint", BEST_VALIDATION_CHECKPOINT),
):
    metadata = inspect_checkpoint(checkpoint_candidate)
    if metadata is None:
        print(f"[STATE COMPARISON] {state_label}: checkpoint unavailable")
        continue
    state_loaded, _ = load_model_only(checkpoint_candidate)
    if not state_loaded:
        print(f"[STATE COMPARISON] {state_label}: load failed")
        continue
    state_validation = evaluate_fixed_validation()
    add_comparison_row(
        state_label, checkpoint_candidate, metadata, state_validation
    )
    print(
        f"[STATE COMPARISON] {state_label} | state epoch={metadata['epoch']} | "
        f"stored train loss={metadata['train_loss']:.6f} | "
        f"evaluated val loss={state_validation['loss']:.6f} | "
        f"mean distance={state_validation['mean_distance']:.6f}"
    )

pd.DataFrame(comparison_rows).to_csv(MODEL_COMPARISON_LOG, index=False)
MODEL_COMPARISON_JSON.write_text(
    json.dumps(comparison_rows, indent=2, default=str), encoding="utf-8"
)
print(f"[INFO] State comparison saved to {MODEL_COMPARISON_LOG}")

selected_best_path = BEST_VALIDATION_CHECKPOINT
if not selected_best_path.exists():
    selected_best_path = (
        BEST_TRAIN_CHECKPOINT
        if BEST_TRAIN_CHECKPOINT.exists()
        else TERMINAL_STATE_CHECKPOINT
    )

loaded, selected_train_loss = load_model_only(selected_best_path)
if loaded:
    final_validation = evaluate_fixed_validation()
    torch.save({
        "variant": VARIANT,
        "parent_variant": PARENT_VARIANT,
        "baseline_source_sha256": BASELINE_SOURCE_SHA256,
        "parent_source_sha256": PARENT_SOURCE_SHA256,
        "source_checkpoint": str(selected_best_path),
        "model_state_dict": model.state_dict(),
        "train_loss": selected_train_loss,
        "fixed_validation": final_validation,
        "terminal_state_summary": terminal_summary,
        "state_comparison_csv": str(MODEL_COMPARISON_LOG),
        "seed": args.seed,
        "config": config,
    }, FINAL_MODEL_PATH)
    print(f"[INFO] Exported best-validation model to {FINAL_MODEL_PATH}")
    print(
        f"[EXPORTED MODEL] source={selected_best_path.name} | "
        f"fixed-validation loss={final_validation['loss']:.6f} | "
        f"mean distance={final_validation['mean_distance']:.6f}"
    )
else:
    print("[WARN] No checkpoint was available for final export.")

if not args.skip_post_training and loaded:
    if not args.no_plots:
        plot_training_metrics()
        sample_index = args.seed % len(training_target_points)
        plot_mechanism_vs_targets(training_target_points[sample_index])
    evaluate_model_statistics(args.eval_samples)

    print("\n[FINAL SUMMARY] Evaluating crank-rocker compliance on the current training set...")
    l1_const = torch.full((len(training_target_points),), L1_FIXED_VALUE, device=device)
    with torch.no_grad():
        training_points_device = training_target_points.to(device)
        preds = apply_dynamic_length_constraints(
            torch.nan_to_num(model(training_points_device), nan=1.0, posinf=1.0, neginf=1.0),
            training_points_device,
        )
        l2_vals, l3_vals, l4_vals = preds[:, 0], preds[:, 1], preds[:, 2]
        links_all = torch.stack([l1_const, l2_vals, l3_vals, l4_vals], dim=1)
        shortest, shortest_idx = torch.min(links_all, dim=1)
        longest, longest_idx = torch.max(links_all, dim=1)
        sum_remaining = links_all.sum(dim=1) - shortest - longest
        grashof_ok = (shortest + longest <= sum_remaining).float()
        adjacency_ok = ((shortest_idx == 1) & ((longest_idx == 0) | (longest_idx == 2))).float()
        grashof_pct = grashof_ok.mean().item() * 100
        crank_rocker_pct = (grashof_ok * adjacency_ok).mean().item() * 100
        mean_crank_len = l2_vals.mean().item()
        mean_grashof_violation = torch.relu(shortest + longest - sum_remaining).mean().item()

    print(
        f"[FINAL CRANK-ROCKER] Grashof OK: {grashof_pct:.1f}% | "
        f"Crank-Rocker OK: {crank_rocker_pct:.1f}% | "
        f"Mean Crank l2: {mean_crank_len:.3f} | "
        f"Mean Grashof Violation: {mean_grashof_violation:.4f}"
    )

print(f"Training complete. Artifacts: {RUN_DIR}")
