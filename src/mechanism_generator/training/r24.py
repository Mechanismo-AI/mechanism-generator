#!/usr/bin/env python3
"""
V5.3-R2.4 Streaming Target Training

Distribution-coverage fork of V5.3-R2.3a_WindowedFeasibilityController.

R2.4 preserves the corrected circle-circle geometry, frozen R2 teacher path
budgets, detached target-region transmission objective, smooth mechanism-class
margins, fixed 512-target validation set, and feasible-frontier checkpointing.
It changes the training and engineering-recovery layer:

  * every training epoch receives a deterministic fresh Monte Carlo target set
    instead of revisiting one fixed 2,000-target tensor;
  * the frozen R2 teacher is evaluated on each fresh batch on demand, so every
    streamed target receives its own teacher-relative path budget;
  * fixed validation remains unchanged and therefore comparable with R2-R2.3a;
  * minor boundary misses adjust persistent constraint multipliers but do not
    trigger engineering rollback; rollback requires a material, repeated loss
    of engineering feasibility;
  * engineering recovery intentionally clears AdamW moments after restoring
    model weights because the adaptive constraint regime has changed, while
    keeping the optimizer object and LR scheduler attached; and
  * repeated engineering restores at the minimum LR stop once they fail to
    produce a new feasible frontier point.

This is epoch-streamed Monte Carlo training: ``--num_points`` means fresh
training targets per epoch. The script logs the deterministic stream seed and
target hash for every refresh.
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

EXPERIMENT_MODE = "R2.4"
IS_R1 = True
VARIANT = "V5.3-R2.4_StreamingTargetTraining"
PARENT_VARIANT = "V5.3-R2.3a_WindowedFeasibilityController"
BASELINE_SOURCE_SHA256 = "f02dd296743bf8da9c17681a76eb0bedaa924db13fb22eefc5e665ef243105d7"
PARENT_SOURCE_SHA256 = "4c0e89050196329fc833d081eeb4d56c98ea71216bfdf10437c31fc7847793ee"
CHECKPOINT_SCHEMA_VERSION = 10

# ======================
# ===== ARGUMENT PARSING =====
# ======================
parser = argparse.ArgumentParser(
    description=f"{VARIANT}: streaming-target constrained-transmission experiment",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("--seed", type=int, default=101, help="Master seed for reproducible R2.4 runs")
parser.add_argument("--load_checkpoint", type=str, default=None, help="Checkpoint to load before training")
parser.add_argument("--num_epochs", type=int, default=250, help="Total training epochs")
parser.add_argument("--num_points", type=int, default=2000, help="Fresh training target triples generated per stream refresh")
parser.add_argument(
    "--stream_refresh_interval",
    type=int,
    default=1,
    help="Generate a new deterministic training target tensor every N epochs",
)
parser.add_argument(
    "--stream_seed_offset",
    type=int,
    default=500_000,
    help="Seed namespace offset for deterministic streamed target tensors",
)
parser.add_argument(
    "--recovery_material_mean_budget_excess",
    type=float,
    default=0.005,
    help="Mean path-budget excess required for a path miss to count as material recovery evidence",
)
parser.add_argument(
    "--recovery_material_path_shortfall",
    type=float,
    default=0.02,
    help="Mechanism-feasible-fraction shortfall required for material recovery evidence",
)
parser.add_argument(
    "--recovery_material_target_shortfall",
    type=float,
    default=0.02,
    help="Target-guard feasible-fraction shortfall required for material recovery evidence",
)
parser.add_argument(
    "--recovery_material_path_excess_overage",
    type=float,
    default=0.005,
    help="Mean mechanism path-excess overage required for material recovery evidence",
)
parser.add_argument(
    "--recovery_material_point_excess_overage",
    type=float,
    default=0.005,
    help="Mean point-path excess overage required for material recovery evidence",
)
parser.add_argument(
    "--max_min_lr_recoveries_without_improvement",
    type=int,
    default=2,
    help="Stop after this many minimum-LR engineering restores without a new feasible frontier point",
)
parser.add_argument("--validation_samples", type=int, default=512, help="Fixed validation target triples")
parser.add_argument("--validation_interval", type=int, default=1, help="Validate every N epochs; R2 validates every epoch")
parser.add_argument("--validation_batch_size", type=int, default=128, help="Fixed-validation batch size")
parser.add_argument("--num_workers", type=int, default=0, help="DataLoader workers; zero is safest for notebooks/Windows")
parser.add_argument("--eval_samples", type=int, default=5000, help="Post-training random evaluation samples")
parser.add_argument("--checkpoint_root", type=str, default="checkpoints", help="Root directory for run artifacts")
parser.add_argument("--run_label", type=str, default="", help="Optional label appended to the run directory")
parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
parser.add_argument("--initial_lr", type=float, default=1.25e-5, help="Initial AdamW learning rate")
parser.add_argument(
    "--initialize_from_model",
    type=str,
    default=None,
    help="Load student model weights only, then start a fresh R2.4 optimizer/run",
)
parser.add_argument(
    "--teacher_model",
    type=str,
    default=None,
    help=(
        "Frozen R2 teacher checkpoint used to define per-target path budgets. "
        "Defaults to --initialize_from_model when omitted."
    ),
)
parser.add_argument(
    "--validation_targets_file",
    type=str,
    default=None,
    help="Optional .pt tensor [N,6] used instead of regenerating fixed validation targets",
)
parser.add_argument(
    "--transmission_target_weight",
    type=float,
    default=10.0,
    help="Maximum weight on the detached target-region transmission hinge",
)
parser.add_argument(
    "--transmission_global_weight",
    type=float,
    default=1.0,
    help="Maximum weight on the weak full-cycle anti-toggle hinge",
)
parser.add_argument(
    "--transmission_ramp_start",
    type=int,
    default=0,
    help="Zero-based epoch at which transmission training begins",
)
parser.add_argument(
    "--transmission_ramp_end",
    type=int,
    default=20,
    help="Zero-based epoch at which transmission weights reach their maxima",
)
parser.add_argument(
    "--transmission_temperature",
    type=float,
    default=0.05,
    help="Squared-distance soft-assignment temperature for target-hit frames",
)
parser.add_argument(
    "--path_tolerance",
    type=float,
    default=0.02,
    help="Allowed mean path-distance degradation per mechanism relative to the frozen teacher",
)
parser.add_argument(
    "--path_constraint_weight",
    type=float,
    default=100.0,
    help="Weight on squared path-budget excess",
)
parser.add_argument(
    "--point_path_tolerance",
    type=float,
    default=0.05,
    help="Larger per-target guard tolerance relative to the frozen teacher",
)
parser.add_argument(
    "--point_path_guard_weight",
    type=float,
    default=25.0,
    help="Weight on squared per-target guard excess",
)
parser.add_argument(
    "--global_top_fraction",
    type=float,
    default=0.05,
    help="Worst fraction of crank frames used by the global anti-toggle penalty",
)
parser.add_argument(
    "--scheduler_start_epoch",
    type=int,
    default=50,
    help="Zero-based epoch before which ReduceLROnPlateau is held",
)
parser.add_argument(
    "--scheduler_patience",
    type=int,
    default=35,
    help="Patience after scheduler release, measured on the feasibility-aware transmission metric",
)
parser.add_argument(
    "--initial_sim_steps",
    type=int,
    default=181,
    help="Initial training crank-angle resolution",
)
parser.add_argument(
    "--final_sim_steps",
    type=int,
    default=361,
    help="Final training crank-angle resolution",
)
parser.add_argument(
    "--sim_ramp_start",
    type=int,
    default=20,
    help="Zero-based epoch at which simulation-resolution ramp begins",
)
parser.add_argument(
    "--sim_ramp_end",
    type=int,
    default=100,
    help="Zero-based epoch at which final simulation resolution is reached",
)
parser.add_argument(
    "--checkpoint_min_path_feasible_fraction",
    type=float,
    default=0.70,
    help="Distribution guard: minimum fraction of mechanisms individually inside the teacher-relative mean path budget",
)
parser.add_argument(
    "--checkpoint_min_target_feasible_fraction",
    type=float,
    default=0.80,
    help="Distribution guard: minimum fraction of individual targets inside the wider pointwise guard",
)
parser.add_argument(
    "--checkpoint_max_path_excess_mean",
    type=float,
    default=0.01,
    help="Maximum mean mechanism-level path-budget excess for a primary checkpoint",
)
parser.add_argument(
    "--checkpoint_max_point_excess_mean",
    type=float,
    default=0.01,
    help="Maximum mean pointwise-guard excess for a primary checkpoint",
)
parser.add_argument(
    "--checkpoint_min_full_cycle_assembly",
    type=float,
    default=0.999,
    help="Minimum full-cycle assembly ratio for the primary transmission checkpoint",
)
parser.add_argument(
    "--checkpoint_adjacency_delta",
    type=float,
    default=2e-4,
    help="Maximum adjacency-penalty increase relative to the teacher baseline",
)
parser.add_argument(
    "--checkpoint_grashof_delta",
    type=float,
    default=1e-5,
    help="Maximum Grashof-penalty increase relative to the teacher baseline",
)
parser.add_argument(
    "--checkpoint_crank_delta",
    type=float,
    default=1e-5,
    help="Maximum crank-shortness-penalty increase relative to the teacher baseline",
)
parser.add_argument(
    "--class_margin",
    type=float,
    default=0.05,
    help="Absolute link-length margin used by smooth crank-rocker class constraints",
)
parser.add_argument(
    "--class_margin_weight",
    type=float,
    default=5.0,
    help="Base weight on smooth crank-shortest/follower-not-longest margins",
)
parser.add_argument(
    "--adaptive_constraint_growth",
    type=float,
    default=1.25,
    help="Gentle multiplier growth applied only to persistently violated groups",
)
parser.add_argument(
    "--adaptive_constraint_decay",
    type=float,
    default=0.85,
    help="Decay toward one after a stable feasible streak",
)
parser.add_argument(
    "--adaptive_constraint_max",
    type=float,
    default=16.0,
    help="Maximum adaptive multiplier for groups other than point-path",
)
parser.add_argument(
    "--adaptive_point_path_max",
    type=float,
    default=24.0,
    help="Separate cap for the pointwise path-guard multiplier",
)
parser.add_argument(
    "--adaptive_update_interval",
    type=int,
    default=5,
    help="Minimum epochs between adaptive multiplier updates",
)
parser.add_argument(
    "--multiplier_window_size",
    type=int,
    default=6,
    help="Validation-window length used to decide persistent group violations",
)
parser.add_argument(
    "--multiplier_violation_trigger",
    type=int,
    default=4,
    help="Required group violations inside the multiplier window before growth",
)
parser.add_argument(
    "--multiplier_decay_feasible_streak",
    type=int,
    default=5,
    help="Consecutive feasible validations required before multiplier decay",
)
parser.add_argument(
    "--feasibility_recovery_patience",
    type=int,
    default=4,
    help="Required infeasible observations inside the recovery window",
)
parser.add_argument(
    "--feasibility_recovery_window",
    type=int,
    default=6,
    help="Moving validation-window length used by engineering recovery",
)
parser.add_argument(
    "--feasibility_recovery_lr_factor",
    type=float,
    default=0.5,
    help="Learning-rate factor after engineering-feasibility recovery",
)
parser.add_argument(
    "--feasibility_recovery_cooldown",
    type=int,
    default=10,
    help="Epochs to hold the scheduler after engineering-feasibility recovery",
)
parser.add_argument(
    "--max_feasibility_recoveries",
    type=int,
    default=6,
    help="Maximum engineering-feasibility restores before stopping",
)
parser.add_argument(
    "--feasible_early_stop_patience",
    type=int,
    default=60,
    help="Stop after this many epochs without a new feasible-transmission checkpoint",
)
parser.add_argument(
    "--min_epochs_before_feasible_early_stop",
    type=int,
    default=75,
    help="Minimum completed epochs before feasible-frontier early stopping is allowed",
)
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
if args.stream_refresh_interval <= 0:
    parser.error("--stream_refresh_interval must be positive")
if args.stream_seed_offset < 0:
    parser.error("--stream_seed_offset must be non-negative")
for recovery_threshold_name in (
    "recovery_material_mean_budget_excess",
    "recovery_material_path_shortfall",
    "recovery_material_target_shortfall",
    "recovery_material_path_excess_overage",
    "recovery_material_point_excess_overage",
):
    if getattr(args, recovery_threshold_name) < 0:
        parser.error(f"--{recovery_threshold_name} must be non-negative")
if args.max_min_lr_recoveries_without_improvement < 0:
    parser.error("--max_min_lr_recoveries_without_improvement must be non-negative")
if args.validation_samples <= 0:
    parser.error("--validation_samples must be positive")
if args.validation_interval <= 0:
    parser.error("--validation_interval must be positive")
if args.initial_lr <= 0:
    parser.error("--initial_lr must be positive")
if args.initialize_from_model and args.load_checkpoint:
    parser.error("Use either --initialize_from_model or --load_checkpoint, not both")
if args.transmission_target_weight < 0 or args.transmission_global_weight < 0:
    parser.error("Transmission weights must be non-negative")
if args.transmission_ramp_start < 0 or args.transmission_ramp_end < 0:
    parser.error("Transmission ramp epochs must be non-negative")
if args.transmission_ramp_end < args.transmission_ramp_start:
    parser.error("--transmission_ramp_end must be >= --transmission_ramp_start")
if args.transmission_temperature <= 0:
    parser.error("--transmission_temperature must be positive")
if args.path_tolerance < 0:
    parser.error("--path_tolerance must be non-negative")
if args.path_constraint_weight < 0:
    parser.error("--path_constraint_weight must be non-negative")
if args.point_path_tolerance < 0 or args.point_path_guard_weight < 0:
    parser.error("Point-path tolerance and guard weight must be non-negative")
if args.checkpoint_max_path_excess_mean < 0 or args.checkpoint_max_point_excess_mean < 0:
    parser.error("Checkpoint mean-excess limits must be non-negative")
if not (0.0 < args.global_top_fraction <= 1.0):
    parser.error("--global_top_fraction must be in (0, 1]")
if args.scheduler_start_epoch < 0 or args.scheduler_patience < 1:
    parser.error("Scheduler start must be non-negative and patience must be positive")
if args.initial_sim_steps < 3 or args.final_sim_steps < 3:
    parser.error("Simulation step counts must be at least 3")
if args.final_sim_steps < args.initial_sim_steps:
    parser.error("--final_sim_steps must be >= --initial_sim_steps")
if args.sim_ramp_start < 0 or args.sim_ramp_end < args.sim_ramp_start:
    parser.error("Simulation ramp epochs are invalid")
if args.class_margin < 0 or args.class_margin_weight < 0:
    parser.error("Class margin and class-margin weight must be non-negative")
if args.adaptive_constraint_growth <= 1.0:
    parser.error("--adaptive_constraint_growth must be greater than 1")
if not (0.0 < args.adaptive_constraint_decay <= 1.0):
    parser.error("--adaptive_constraint_decay must be in (0, 1]")
if args.adaptive_constraint_max < 1.0:
    parser.error("--adaptive_constraint_max must be at least 1")
if args.adaptive_point_path_max < 1.0:
    parser.error("--adaptive_point_path_max must be at least 1")
if args.adaptive_update_interval < 1:
    parser.error("--adaptive_update_interval must be positive")
if args.multiplier_window_size < 1:
    parser.error("--multiplier_window_size must be positive")
if not (1 <= args.multiplier_violation_trigger <= args.multiplier_window_size):
    parser.error("--multiplier_violation_trigger must be between 1 and --multiplier_window_size")
if args.multiplier_decay_feasible_streak < 1:
    parser.error("--multiplier_decay_feasible_streak must be positive")
if args.feasibility_recovery_window < 1:
    parser.error("--feasibility_recovery_window must be positive")
if not (1 <= args.feasibility_recovery_patience <= args.feasibility_recovery_window):
    parser.error("--feasibility_recovery_patience must be between 1 and --feasibility_recovery_window")
if not (0.0 < args.feasibility_recovery_lr_factor <= 1.0):
    parser.error("--feasibility_recovery_lr_factor must be in (0, 1]")
if args.feasibility_recovery_cooldown < 0:
    parser.error("--feasibility_recovery_cooldown must be non-negative")
if args.max_feasibility_recoveries < 0:
    parser.error("--max_feasibility_recoveries must be non-negative")
if args.feasible_early_stop_patience < 1:
    parser.error("--feasible_early_stop_patience must be positive")
if args.min_epochs_before_feasible_early_stop < 0:
    parser.error("--min_epochs_before_feasible_early_stop must be non-negative")

for name in (
    "checkpoint_min_path_feasible_fraction",
    "checkpoint_min_full_cycle_assembly",
    "checkpoint_min_target_feasible_fraction",
):
    value = getattr(args, name)
    if not (0.0 <= value <= 1.0):
        parser.error(f"--{name} must be in [0, 1]")

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
STREAM_REFRESH_INTERVAL = args.stream_refresh_interval
STREAM_SEED_OFFSET = args.stream_seed_offset
RECOVERY_MATERIAL_MEAN_BUDGET_EXCESS = args.recovery_material_mean_budget_excess
RECOVERY_MATERIAL_PATH_SHORTFALL = args.recovery_material_path_shortfall
RECOVERY_MATERIAL_TARGET_SHORTFALL = args.recovery_material_target_shortfall
RECOVERY_MATERIAL_PATH_EXCESS_OVERAGE = args.recovery_material_path_excess_overage
RECOVERY_MATERIAL_POINT_EXCESS_OVERAGE = args.recovery_material_point_excess_overage
MAX_MIN_LR_RECOVERIES_WITHOUT_IMPROVEMENT = (
    args.max_min_lr_recoveries_without_improvement
)
X_MIN, X_MAX = -7.0, 1.0
Y_MIN, Y_MAX = 1.0, 7.0
L1_FIXED_VALUE = 6.0
MIN_LEN = 1e-3
MIN_BAR_LEN = 0.1
BAD_BATCH_LOG = "bad_batches_three_points.csv"

# --- Training Config ---
NUM_EPOCHS = args.num_epochs
BATCH_SIZE = 32
INITIAL_LR = args.initial_lr
WARMUP_EPOCHS = 0
ANNEALING_EPOCHS = 1000
TARGET_MEAN_DIST = -1.0

# --- Simulation Config ---
INITIAL_NUM_SIM_STEPS = args.initial_sim_steps
FINAL_NUM_SIM_STEPS = args.final_sim_steps
RAMP_START_EPOCH = args.sim_ramp_start
RAMP_END_EPOCH = args.sim_ramp_end
DEFAULT_NUM_SIM_STEPS = 361
VALIDATION_NUM_SIM_STEPS = 361

# --- Loss and Penalty Config ---
LAMBDA_GRASHOF = 0.05
LAMBDA_CRANK_SHORT = 0.05
LAMBDA_ADJACENCY = 0.05
LAMBDA_ASSEMBLY = 1.0

# R2 geometry configuration. The fixed branch sign reproduces the V5.3
# theta4 = alpha - phi assembly mode. R2.3 keeps R2.2 path/transmission training
# and adds active feasibility preservation.
ASSEMBLY_BRANCH_SIGN = -1.0
ASSEMBLY_VALIDITY_TOL_REL = 1e-6
CENTER_DISTANCE_FLOOR_REL = 1e-4
D2_NUMERIC_FLOOR_REL = 1e-12
H2_NUMERIC_FLOOR_REL = 1e-8
DISTANCE_SQ_FLOOR = 1e-12
INVALID_DISTANCE = 20.0
TRANSMISSION_TARGET_MIN_DEG = 35.0
TRANSMISSION_GLOBAL_FLOOR_DEG = 15.0
TRANSMISSION_TARGET_WEIGHT_MAX = args.transmission_target_weight
TRANSMISSION_GLOBAL_WEIGHT_MAX = args.transmission_global_weight
TRANSMISSION_RAMP_START_EPOCH = args.transmission_ramp_start
TRANSMISSION_RAMP_END_EPOCH = args.transmission_ramp_end
TRANSMISSION_SOFTMAX_TEMPERATURE = args.transmission_temperature
PATH_TOLERANCE = args.path_tolerance
PATH_CONSTRAINT_WEIGHT = args.path_constraint_weight
POINT_PATH_TOLERANCE = args.point_path_tolerance
POINT_PATH_GUARD_WEIGHT = args.point_path_guard_weight
GLOBAL_TRANSMISSION_TOP_FRACTION = args.global_top_fraction
SCHEDULER_START_EPOCH = args.scheduler_start_epoch
SCHEDULER_PATIENCE = args.scheduler_patience
CHECKPOINT_MIN_PATH_FEASIBLE_FRACTION = args.checkpoint_min_path_feasible_fraction
CHECKPOINT_MIN_TARGET_FEASIBLE_FRACTION = args.checkpoint_min_target_feasible_fraction
CHECKPOINT_MAX_PATH_EXCESS_MEAN = args.checkpoint_max_path_excess_mean
CHECKPOINT_MAX_POINT_EXCESS_MEAN = args.checkpoint_max_point_excess_mean
CHECKPOINT_MIN_FULL_CYCLE_ASSEMBLY = args.checkpoint_min_full_cycle_assembly
CHECKPOINT_ADJACENCY_DELTA = args.checkpoint_adjacency_delta
CHECKPOINT_GRASHOF_DELTA = args.checkpoint_grashof_delta
CHECKPOINT_CRANK_DELTA = args.checkpoint_crank_delta
CLASS_MARGIN = args.class_margin
CLASS_MARGIN_WEIGHT = args.class_margin_weight
ADAPTIVE_CONSTRAINT_GROWTH = args.adaptive_constraint_growth
ADAPTIVE_CONSTRAINT_DECAY = args.adaptive_constraint_decay
ADAPTIVE_CONSTRAINT_MAX = args.adaptive_constraint_max
ADAPTIVE_POINT_PATH_MAX = args.adaptive_point_path_max
ADAPTIVE_UPDATE_INTERVAL = args.adaptive_update_interval
MULTIPLIER_WINDOW_SIZE = args.multiplier_window_size
MULTIPLIER_VIOLATION_TRIGGER = args.multiplier_violation_trigger
MULTIPLIER_DECAY_FEASIBLE_STREAK = args.multiplier_decay_feasible_streak
FEASIBILITY_RECOVERY_PATIENCE = args.feasibility_recovery_patience
FEASIBILITY_RECOVERY_WINDOW = args.feasibility_recovery_window
FEASIBILITY_RECOVERY_LR_FACTOR = args.feasibility_recovery_lr_factor
FEASIBILITY_RECOVERY_COOLDOWN = args.feasibility_recovery_cooldown
MAX_FEASIBILITY_RECOVERIES = args.max_feasibility_recoveries
FEASIBLE_EARLY_STOP_PATIENCE = args.feasible_early_stop_patience
MIN_EPOCHS_BEFORE_FEASIBLE_EARLY_STOP = args.min_epochs_before_feasible_early_stop

BASE_LOSS_COMPONENT_KEYS = (
    "distance_loss",
    "grashof_penalty",
    "crank_shortness_penalty",
    "adjacency_penalty",
    "assembly_penalty",
)
R2_GEOMETRY_COMPONENT_KEYS = (
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
R22_PATH_COMPONENT_KEYS = (
    "teacher_distance_loss",
    "path_mean_degradation",
    "path_budget_mean",
    "path_constraint_penalty",
    "path_constraint_penalty_raw",
    "point_path_guard_penalty",
    "point_path_guard_penalty_raw",
    "path_excess_mean",
    "point_path_excess_mean",
    "path_excess_rms",
    "path_target_feasible_fraction",
    "path_mechanism_feasible_fraction",
    "path_max_excess",
)
R21_TRANSMISSION_COMPONENT_KEYS = (
    "transmission_penalty",
    "target_transmission_penalty_raw",
    "global_transmission_penalty_raw",
    "target_transmission_penalty_weighted",
    "global_transmission_penalty_weighted",
    "transmission_target_weight_effective",
    "transmission_global_weight_effective",
    "transmission_weight_ramp_fraction",
    "target_transmission_quality_mean",
    "target_transmission_angle_mean_deg",
    "target_transmission_min_angle_deg",
    "target_transmission_below_15deg_fraction",
    "target_transmission_below_35deg_fraction",
    "soft_target_transmission_quality_mean",
    "soft_target_transmission_angle_mean_deg",
    "soft_target_transmission_min_angle_deg",
    "soft_target_transmission_below_15deg_fraction",
    "soft_target_transmission_below_35deg_fraction",
    "target_soft_assignment_entropy",
    "target_soft_assignment_effective_frames",
)
R23_FEASIBILITY_COMPONENT_KEYS = (
    "adaptive_path_constraint_penalty",
    "adaptive_point_path_guard_penalty",
    "adaptive_assembly_penalty",
    "adaptive_grashof_penalty",
    "adaptive_crank_shortness_penalty",
    "smooth_crank_margin_penalty_raw",
    "smooth_follower_margin_penalty_raw",
    "smooth_class_margin_penalty_raw",
    "smooth_class_margin_penalty",
    "crank_shortest_margin_min",
    "follower_not_longest_margin",
    "class_exact_feasible_fraction",
    "class_design_margin_feasible_fraction",
    "path_constraint_multiplier",
    "point_path_guard_multiplier",
    "assembly_multiplier",
    "grashof_multiplier",
    "crank_multiplier",
    "class_margin_multiplier",
)
R21_EXTRA_COMPONENT_KEYS = (
    R22_PATH_COMPONENT_KEYS
    + R21_TRANSMISSION_COMPONENT_KEYS
    + R2_GEOMETRY_COMPONENT_KEYS
    + R23_FEASIBILITY_COMPONENT_KEYS
)
ALL_COMPONENT_KEYS = BASE_LOSS_COMPONENT_KEYS + R21_EXTRA_COMPONENT_KEYS


def transmission_ramp_fraction(epoch_index: int) -> float:
    """Smoothly ramp transmission training while validation stays full-weight."""
    if epoch_index < TRANSMISSION_RAMP_START_EPOCH:
        return 0.0
    if TRANSMISSION_RAMP_END_EPOCH <= TRANSMISSION_RAMP_START_EPOCH:
        return 1.0
    progress = (
        (epoch_index - TRANSMISSION_RAMP_START_EPOCH)
        / (TRANSMISSION_RAMP_END_EPOCH - TRANSMISSION_RAMP_START_EPOCH)
    )
    progress = min(1.0, max(0.0, float(progress)))
    # Smoothstep prevents an abrupt derivative/scale change at either endpoint.
    return progress * progress * (3.0 - 2.0 * progress)


def transmission_weights_for_epoch(epoch_index: int) -> Tuple[float, float, float]:
    fraction = transmission_ramp_fraction(epoch_index)
    return (
        TRANSMISSION_TARGET_WEIGHT_MAX * fraction,
        TRANSMISSION_GLOBAL_WEIGHT_MAX * fraction,
        fraction,
    )

# --- Stability and Recovery Config ---
RESET_BAD_PREDICTIONS = True
MAX_GRAD_NORM = 0.25
MIN_LR = 1e-6
MAX_LOSS_FACTOR = 10.0
ENABLE_LOSS_CLAMP = False
SPIKE_THRESHOLD = 2.5
VALIDATION_SPIKE_THRESHOLD = 2.5
SPIKE_MIN_EPOCH = 50
BASE_RESET_LR = INITIAL_LR * 5.0
GRACE_EPOCHS_AFTER_ROLLBACK = 10
PLATEAU_COOLDOWN_EPOCHS = 10
RECOVERY_LR_FACTOR = 0.5

# R2.4 retains the R1.1 instrumentation and hard-failure thresholds. A dead-gradient recovery
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
EARLY_STOP_PATIENCE = FEASIBLE_EARLY_STOP_PATIENCE
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
BEST_PATH_CHECKPOINT = RUN_DIR / "best_path.pth"
BEST_COMPOSITE_CHECKPOINT = RUN_DIR / "best_composite.pth"
# Legacy alias retained for recovery helpers and external analysis scripts.
BEST_VALIDATION_CHECKPOINT = BEST_COMPOSITE_CHECKPOINT
BEST_FEASIBLE_TRANSMISSION_CHECKPOINT = RUN_DIR / "best_feasible_transmission.pth"
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
TEACHER_VALIDATION_DISTANCES_PATH = RUN_DIR / "teacher_validation_target_distances.pt"
TEACHER_BASELINE_PATH = RUN_DIR / "teacher_validation_baseline.json"
SOURCE_HASH_PATH = RUN_DIR / "source_sha256.txt"
CONSTRAINT_HISTORY_PATH = RUN_DIR / "constraint_multiplier_history.csv"
STREAM_HISTORY_PATH = RUN_DIR / "streaming_target_history.csv"

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
        # R2.3 preserves the explicit R1.1 field ordering.
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


def stream_index_for_epoch(epoch_index: int) -> int:
    return max(0, int(epoch_index)) // STREAM_REFRESH_INTERVAL


def stream_seed_for_index(stream_index: int) -> int:
    # Large odd stride keeps adjacent stream tensors in clearly separated RNG
    # subsequences while remaining reproducible from only seed and epoch.
    return int(args.seed + STREAM_SEED_OFFSET + 104_729 * int(stream_index))


def tensor_sha256(tensor: torch.Tensor) -> str:
    contiguous = tensor.detach().cpu().contiguous()
    return hashlib.sha256(contiguous.numpy().tobytes()).hexdigest()


def refresh_streaming_targets(
    epoch_index: int,
    *,
    force: bool = False,
    reason: str = "epoch_stream",
) -> bool:
    """Create the deterministic Monte Carlo target set assigned to an epoch."""
    global training_target_points, current_stream_index, current_stream_seed
    global streaming_unique_targets_seen

    requested_stream_index = stream_index_for_epoch(epoch_index)
    if not force and requested_stream_index == current_stream_index:
        return False

    seed = stream_seed_for_index(requested_stream_index)
    local_generator = torch.Generator(device="cpu")
    local_generator.manual_seed(seed)
    training_target_points = generate_target_point_triples(
        NUM_POINTS, generator=local_generator
    ).contiguous()

    # Shuffle order is deterministic for the stream but independent of target
    # generation. Rebuilding each refresh avoids carrying stale sampler state.
    dataloader_generator.manual_seed(seed + 1)
    build_dataloader()

    current_stream_index = requested_stream_index
    current_stream_seed = seed
    streaming_unique_targets_seen = max(
        streaming_unique_targets_seen,
        (requested_stream_index + 1) * NUM_POINTS,
    )
    digest = tensor_sha256(training_target_points)
    append_csv(STREAM_HISTORY_PATH, {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": int(epoch_index) + 1,
        "stream_index": requested_stream_index,
        "stream_seed": seed,
        "samples": NUM_POINTS,
        "cumulative_unique_targets": streaming_unique_targets_seen,
        "target_sha256": digest,
        "target_mean": float(training_target_points.mean().item()),
        "target_std": float(training_target_points.std(unbiased=False).item()),
        "reason": reason,
    })
    print(
        f"[STREAM] epoch {int(epoch_index) + 1}: stream={requested_stream_index} "
        f"seed={seed} samples={NUM_POINTS} hash={digest[:12]}"
    )
    return True


def restart_dataloader(regenerate: bool = True, reason: str = "") -> None:
    """Compatibility helper; R2.4 normally refreshes targets at epoch start."""
    global training_target_points
    if regenerate:
        refresh_streaming_targets(
            max(0, current_state_epoch), force=True, reason=reason or "restart"
        )
        return
    build_dataloader()
    suffix = f" ({reason})" if reason else ""
    print(f"[INFO] DataLoader rebuilt without target regeneration{suffix}.")


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
        # Internal full-resolution tensor used by the R2.3 constrained transmission loss.
        "_transmission_q_by_frame": transmission_q_effective,
    }

    if return_diagnostics:
        return Px_final, Py_final, valid_assembly_mask, diagnostics
    return Px_final, Py_final, valid_assembly_mask


def compute_target_distances_for_params(
    predicted_params: torch.Tensor,
    target_points: torch.Tensor,
    num_sim_steps: int,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, Dict[str, torch.Tensor]]:
    """Simulate a batch and return [batch,3] hard-nearest target distances.

    This helper is shared by the trainable student and frozen teacher so the
    path budget is measured with the same geometry solver and angular grid.
    """
    l2, l3, l4 = predicted_params[:, 0], predicted_params[:, 1], predicted_params[:, 2]
    S_ratio = predicted_params[:, 3]
    bar_length = predicted_params[:, 4]
    base_x = predicted_params[:, 5]
    base_y = predicted_params[:, 6]
    base_angle = predicted_params[:, 7]
    l1 = torch.full_like(l2, L1_FIXED_VALUE)

    theta2_range = torch.linspace(
        0, 2 * math.pi, int(num_sim_steps), dtype=l2.dtype, device=l2.device
    )
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
    target_x = target_points[:, (0, 2, 4)]
    target_y = target_points[:, (1, 3, 5)]
    target_sqd = (
        (Px[:, None, :] - target_x[:, :, None]).square()
        + (Py[:, None, :] - target_y[:, :, None]).square()
    )
    target_sqd = torch.where(
        valid_mask[:, None, :],
        target_sqd,
        torch.full_like(target_sqd, invalid_distance_sq),
    )
    target_sqd = torch.nan_to_num(
        target_sqd,
        nan=invalid_distance_sq,
        posinf=invalid_distance_sq,
        neginf=invalid_distance_sq,
    )
    min_sqd, min_indices = torch.min(target_sqd, dim=2)
    min_sqd = torch.clamp(
        min_sqd,
        min=DISTANCE_SQ_FLOOR,
        max=invalid_distance_sq,
    )
    min_distances = torch.sqrt(min_sqd)
    return min_distances, min_indices, target_sqd, geometry


@torch.no_grad()
def compute_teacher_target_distances(
    target_points: torch.Tensor,
    num_sim_steps: int,
) -> torch.Tensor:
    """Return frozen-teacher hard-nearest distances for the same target batch."""
    teacher_was_training = teacher_model.training
    teacher_model.eval()
    teacher_output = teacher_model(target_points)
    teacher_output = torch.nan_to_num(
        teacher_output, nan=1.0, posinf=1.0, neginf=1.0
    )
    teacher_params = apply_dynamic_length_constraints(teacher_output, target_points)
    teacher_distances, _, _, _ = compute_target_distances_for_params(
        teacher_params, target_points, num_sim_steps
    )
    if teacher_was_training:
        teacher_model.train()
    return teacher_distances.detach()


def compute_mechanism_loss_batch(
    predicted_params,
    target_points,
    num_sim_steps: Optional[int] = None,
    target_transmission_weight: Optional[float] = None,
    global_transmission_weight: Optional[float] = None,
    teacher_target_distances: Optional[torch.Tensor] = None,
):
    """Teacher-constrained transmission objective with adaptive feasibility weights.

    Raw geometry/checkpoint metrics retain their fixed R2.2 definitions. The
    optimized loss uses adaptive multipliers and smooth mechanism-class margins
    so engineering violations have a directional gradient before the discrete
    crank-rocker gate is crossed.
    """
    l2, l3, l4 = predicted_params[:, 0], predicted_params[:, 1], predicted_params[:, 2]
    l1 = torch.full_like(l2, L1_FIXED_VALUE)

    if target_transmission_weight is None:
        target_transmission_weight = TRANSMISSION_TARGET_WEIGHT_MAX
    if global_transmission_weight is None:
        global_transmission_weight = TRANSMISSION_GLOBAL_WEIGHT_MAX
    target_transmission_weight = float(target_transmission_weight)
    global_transmission_weight = float(global_transmission_weight)

    steps = NUM_SIM_STEPS if num_sim_steps is None else int(num_sim_steps)
    min_distances, min_indices, target_sqd, geometry = compute_target_distances_for_params(
        predicted_params, target_points, steps
    )
    min_dist1, min_dist2, min_dist3 = (
        min_distances[:, 0], min_distances[:, 1], min_distances[:, 2]
    )
    loss_dist = torch.nan_to_num(
        min_distances.mean(dim=1),
        nan=INVALID_DISTANCE,
        posinf=INVALID_DISTANCE,
        neginf=INVALID_DISTANCE,
    )

    if teacher_target_distances is None:
        teacher_target_distances = compute_teacher_target_distances(target_points, steps)
    teacher_target_distances = torch.nan_to_num(
        teacher_target_distances.detach().to(
            device=min_distances.device, dtype=min_distances.dtype
        ),
        nan=INVALID_DISTANCE,
        posinf=INVALID_DISTANCE,
        neginf=INVALID_DISTANCE,
    )
    if teacher_target_distances.shape != min_distances.shape:
        raise ValueError(
            "teacher_target_distances must have shape "
            f"{tuple(min_distances.shape)}, got {tuple(teacher_target_distances.shape)}"
        )

    teacher_mean_distance = teacher_target_distances.mean(dim=1)
    student_mean_distance = min_distances.mean(dim=1)
    path_mean_degradation = student_mean_distance - teacher_mean_distance
    path_budget_per_mechanism = teacher_mean_distance + PATH_TOLERANCE
    path_excess = torch.relu(student_mean_distance - path_budget_per_mechanism)
    path_constraint_penalty_raw = path_excess.square()
    path_constraint_penalty = PATH_CONSTRAINT_WEIGHT * path_constraint_penalty_raw
    adaptive_path_constraint_penalty = (
        constraint_multipliers["path"] * path_constraint_penalty
    )

    point_path_budget = teacher_target_distances + POINT_PATH_TOLERANCE
    point_path_excess = torch.relu(min_distances - point_path_budget)
    point_path_guard_penalty_raw = point_path_excess.square().mean(dim=1)
    point_path_guard_penalty = POINT_PATH_GUARD_WEIGHT * point_path_guard_penalty_raw
    adaptive_point_path_guard_penalty = (
        constraint_multipliers["point_path"] * point_path_guard_penalty
    )
    path_target_feasible = point_path_excess <= 1e-9
    path_mechanism_feasible = path_excess <= 1e-9

    links = torch.stack([l1, l2, l3, l4], dim=1)
    shortest, shortest_idx = torch.min(links, dim=1)
    longest, longest_idx = torch.max(links, dim=1)
    sum_remaining = links.sum(dim=1) - shortest - longest

    grashof_violation = torch.relu(shortest + longest - sum_remaining)
    penalty_grashof = torch.nan_to_num(
        LAMBDA_GRASHOF * grashof_violation, nan=0.0, posinf=0.0
    )
    adaptive_grashof_penalty = constraint_multipliers["grashof"] * penalty_grashof

    penalty_crank_shortness = torch.nan_to_num(
        LAMBDA_CRANK_SHORT * torch.relu(l2 - shortest), nan=0.0, posinf=0.0
    )
    adaptive_crank_shortness_penalty = (
        constraint_multipliers["crank"] * penalty_crank_shortness
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

    # Smooth class margins supply the gradient the discrete adjacency test lacks.
    # The crank must remain shorter than l1/l3/l4, while l4 must remain below
    # max(l1,l3) so the existing crank-rocker convention is preserved.
    crank_comparators = torch.stack([l1, l3, l4], dim=1)
    crank_margins = crank_comparators - l2[:, None]
    crank_margin_violation = torch.relu(CLASS_MARGIN - crank_margins)
    smooth_crank_margin_penalty_raw = crank_margin_violation.square().mean(dim=1)

    follower_reference = torch.maximum(l1, l3)
    follower_margin = follower_reference - l4
    follower_margin_violation = torch.relu(CLASS_MARGIN - follower_margin)
    smooth_follower_margin_penalty_raw = follower_margin_violation.square()
    smooth_class_margin_penalty_raw = (
        smooth_crank_margin_penalty_raw + smooth_follower_margin_penalty_raw
    )
    smooth_class_margin_penalty = (
        CLASS_MARGIN_WEIGHT
        * constraint_multipliers["class_margin"]
        * smooth_class_margin_penalty_raw
    )
    crank_shortest_margin_min = crank_margins.min(dim=1).values
    class_exact_feasible = (crank_shortest_margin_min >= 0.0) & (follower_margin >= 0.0)
    class_design_margin_feasible = (
        (crank_shortest_margin_min >= CLASS_MARGIN)
        & (follower_margin >= CLASS_MARGIN)
    )

    assembly_penalty = LAMBDA_ASSEMBLY * (
        0.5 * geometry["sampled_assembly_violation"]
        + 0.5 * geometry["full_cycle_assembly_violation"]
    )
    assembly_penalty = torch.nan_to_num(
        assembly_penalty, nan=INVALID_DISTANCE, posinf=INVALID_DISTANCE
    )
    adaptive_assembly_penalty = (
        constraint_multipliers["assembly"] * assembly_penalty
    )

    # Recalculate the useful crank neighborhood every pass, but detach the
    # correspondence itself. Transmission gradients therefore flow through q
    # and the link lengths, not through target-frame reassignment.
    temperature = max(float(TRANSMISSION_SOFTMAX_TEMPERATURE), 1e-8)
    soft_weights = torch.softmax(-target_sqd.detach() / temperature, dim=2).detach()
    transmission_q_by_frame = geometry["_transmission_q_by_frame"]
    q_target_min = math.sin(math.radians(TRANSMISSION_TARGET_MIN_DEG)) ** 2
    q_global_floor = math.sin(math.radians(TRANSMISSION_GLOBAL_FLOOR_DEG)) ** 2

    target_shortfall_sq = torch.relu(
        q_target_min - transmission_q_by_frame
    ).square()
    target_penalty_by_target = (
        soft_weights * target_shortfall_sq[:, None, :]
    ).sum(dim=2)
    target_transmission_penalty_raw = target_penalty_by_target.mean(dim=1)

    global_shortfall_sq = torch.relu(
        q_global_floor - transmission_q_by_frame
    ).square()
    top_k = max(
        1,
        min(
            global_shortfall_sq.shape[1],
            int(math.ceil(GLOBAL_TRANSMISSION_TOP_FRACTION * global_shortfall_sq.shape[1])),
        ),
    )
    global_transmission_penalty_raw = torch.topk(
        global_shortfall_sq, k=top_k, dim=1, largest=True, sorted=False
    ).values.mean(dim=1)

    target_transmission_penalty_weighted = (
        target_transmission_weight * target_transmission_penalty_raw
    )
    global_transmission_penalty_weighted = (
        global_transmission_weight * global_transmission_penalty_raw
    )
    transmission_penalty = (
        target_transmission_penalty_weighted
        + global_transmission_penalty_weighted
    )

    hard_target_q = torch.gather(
        transmission_q_by_frame, dim=1, index=min_indices
    )
    hard_target_angle_deg = torch.rad2deg(
        torch.asin(torch.sqrt(hard_target_q.clamp(0.0, 1.0)))
    )
    soft_target_q = (
        soft_weights * transmission_q_by_frame[:, None, :]
    ).sum(dim=2)
    soft_target_angle_deg = torch.rad2deg(
        torch.asin(torch.sqrt(soft_target_q.clamp(0.0, 1.0)))
    )
    soft_assignment_entropy = -(
        soft_weights * torch.log(soft_weights.clamp_min(1e-12))
    ).sum(dim=2)

    total_loss = (
        adaptive_path_constraint_penalty
        + adaptive_point_path_guard_penalty
        + adaptive_grashof_penalty
        + adaptive_crank_shortness_penalty
        + penalty_adjacency
        + smooth_class_margin_penalty
        + adaptive_assembly_penalty
        + transmission_penalty
    )

    if TRANSMISSION_TARGET_WEIGHT_MAX > 0:
        ramp_fraction = target_transmission_weight / TRANSMISSION_TARGET_WEIGHT_MAX
    elif TRANSMISSION_GLOBAL_WEIGHT_MAX > 0:
        ramp_fraction = global_transmission_weight / TRANSMISSION_GLOBAL_WEIGHT_MAX
    else:
        ramp_fraction = 0.0

    q15 = math.sin(math.radians(15.0)) ** 2
    q35 = math.sin(math.radians(35.0)) ** 2
    components = {
        "distance_loss": loss_dist.mean().item(),
        "teacher_distance_loss": teacher_mean_distance.mean().item(),
        "path_mean_degradation": path_mean_degradation.mean().item(),
        "path_budget_mean": path_budget_per_mechanism.mean().item(),
        "path_constraint_penalty": path_constraint_penalty.mean().item(),
        "path_constraint_penalty_raw": path_constraint_penalty_raw.mean().item(),
        "point_path_guard_penalty": point_path_guard_penalty.mean().item(),
        "point_path_guard_penalty_raw": point_path_guard_penalty_raw.mean().item(),
        "adaptive_path_constraint_penalty": adaptive_path_constraint_penalty.mean().item(),
        "adaptive_point_path_guard_penalty": adaptive_point_path_guard_penalty.mean().item(),
        "path_excess_mean": path_excess.mean().item(),
        "point_path_excess_mean": point_path_excess.mean().item(),
        "path_excess_rms": torch.sqrt(path_excess.square().mean()).item(),
        "path_target_feasible_fraction": path_target_feasible.float().mean().item(),
        "path_mechanism_feasible_fraction": path_mechanism_feasible.float().mean().item(),
        "path_max_excess": torch.maximum(path_excess.max(), point_path_excess.max()).item(),
        "grashof_penalty": penalty_grashof.mean().item(),
        "adaptive_grashof_penalty": adaptive_grashof_penalty.mean().item(),
        "crank_shortness_penalty": penalty_crank_shortness.mean().item(),
        "adaptive_crank_shortness_penalty": adaptive_crank_shortness_penalty.mean().item(),
        "adjacency_penalty": penalty_adjacency.mean().item(),
        "smooth_crank_margin_penalty_raw": smooth_crank_margin_penalty_raw.mean().item(),
        "smooth_follower_margin_penalty_raw": smooth_follower_margin_penalty_raw.mean().item(),
        "smooth_class_margin_penalty_raw": smooth_class_margin_penalty_raw.mean().item(),
        "smooth_class_margin_penalty": smooth_class_margin_penalty.mean().item(),
        "crank_shortest_margin_min": crank_shortest_margin_min.mean().item(),
        "follower_not_longest_margin": follower_margin.mean().item(),
        "class_exact_feasible_fraction": class_exact_feasible.float().mean().item(),
        "class_design_margin_feasible_fraction": class_design_margin_feasible.float().mean().item(),
        "assembly_penalty": assembly_penalty.mean().item(),
        "adaptive_assembly_penalty": adaptive_assembly_penalty.mean().item(),
        "path_constraint_multiplier": float(constraint_multipliers["path"]),
        "point_path_guard_multiplier": float(constraint_multipliers["point_path"]),
        "assembly_multiplier": float(constraint_multipliers["assembly"]),
        "grashof_multiplier": float(constraint_multipliers["grashof"]),
        "crank_multiplier": float(constraint_multipliers["crank"]),
        "class_margin_multiplier": float(constraint_multipliers["class_margin"]),
        "transmission_penalty": transmission_penalty.mean().item(),
        "target_transmission_penalty_raw": target_transmission_penalty_raw.mean().item(),
        "global_transmission_penalty_raw": global_transmission_penalty_raw.mean().item(),
        "target_transmission_penalty_weighted": target_transmission_penalty_weighted.mean().item(),
        "global_transmission_penalty_weighted": global_transmission_penalty_weighted.mean().item(),
        "transmission_target_weight_effective": target_transmission_weight,
        "transmission_global_weight_effective": global_transmission_weight,
        "transmission_weight_ramp_fraction": float(ramp_fraction),
        "target_transmission_quality_mean": hard_target_q.mean().item(),
        "target_transmission_angle_mean_deg": hard_target_angle_deg.mean().item(),
        "target_transmission_min_angle_deg": hard_target_angle_deg.min(dim=1).values.mean().item(),
        "target_transmission_below_15deg_fraction": (hard_target_q < q15).float().mean().item(),
        "target_transmission_below_35deg_fraction": (hard_target_q < q35).float().mean().item(),
        "soft_target_transmission_quality_mean": soft_target_q.mean().item(),
        "soft_target_transmission_angle_mean_deg": soft_target_angle_deg.mean().item(),
        "soft_target_transmission_min_angle_deg": soft_target_angle_deg.min(dim=1).values.mean().item(),
        "soft_target_transmission_below_15deg_fraction": (soft_target_q < q15).float().mean().item(),
        "soft_target_transmission_below_35deg_fraction": (soft_target_q < q35).float().mean().item(),
        "target_soft_assignment_entropy": soft_assignment_entropy.mean().item(),
        "target_soft_assignment_effective_frames": torch.exp(soft_assignment_entropy).mean().item(),
        "total_loss": total_loss.mean().item(),
    }
    for key in R2_GEOMETRY_COMPONENT_KEYS:
        components[key] = geometry[key].mean().item()

    return total_loss.mean(), (
        min_dist1.mean().item(),
        min_dist2.mean().item(),
        min_dist3.mean().item(),
    ), components


# ======================
# ===== FIXED VALIDATION =====
# ======================
def evaluate_fixed_validation(
    model_to_evaluate: Optional[nn.Module] = None,
) -> Dict[str, float]:
    eval_model = model if model_to_evaluate is None else model_to_evaluate
    was_training = eval_model.training
    eval_model.eval()
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
            teacher_distances_cpu = fixed_validation_teacher_distances[
                start:start + args.validation_batch_size
            ]
            batch = batch_cpu.to(device)
            teacher_distances = teacher_distances_cpu.to(device)
            model_output = eval_model(batch)
            accumulate_output_stats(output_accumulator, model_output)
            raw_pred = torch.nan_to_num(model_output, nan=1.0, posinf=1.0, neginf=1.0)
            predicted_params = apply_dynamic_length_constraints(raw_pred, batch)
            loss, point_dists, components = compute_mechanism_loss_batch(
                predicted_params,
                batch,
                num_sim_steps=VALIDATION_NUM_SIM_STEPS,
                target_transmission_weight=TRANSMISSION_TARGET_WEIGHT_MAX,
                global_transmission_weight=TRANSMISSION_GLOBAL_WEIGHT_MAX,
                teacher_target_distances=teacher_distances,
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
        eval_model.train()
    if count == 0:
        raise RuntimeError("Fixed validation set is empty")
    result = {key: value / count for key, value in totals.items()}
    result["mean_distance"] = (result["p1"] + result["p2"] + result["p3"]) / 3.0
    result.update(finalize_output_stats(output_accumulator))
    return result


def validation_feasibility(metrics: Dict[str, float]) -> Tuple[bool, Dict[str, float]]:
    """Evaluate the engineering path/assembly/class gate for the primary checkpoint.

    The optimized hinge remains per mechanism, but checkpoint eligibility uses
    the intended aggregate path budget plus distribution and mean-excess guards.
    This avoids rejecting useful models because of tiny positive hinge values
    while still preventing a small number of severe path failures from hiding
    behind a good average.
    """
    teacher_adj = safe_float(teacher_validation_baseline.get("adjacency_penalty", 0.0), 0.0)
    teacher_grashof = safe_float(teacher_validation_baseline.get("grashof_penalty", 0.0), 0.0)
    teacher_crank = safe_float(teacher_validation_baseline.get("crank_shortness_penalty", 0.0), 0.0)

    mean_path_budget_excess = max(
        0.0,
        safe_float(metrics.get("mean_distance"), float("inf"))
        - safe_float(metrics.get("path_budget_mean"), float("-inf")),
    )
    path_shortfall = max(
        0.0,
        CHECKPOINT_MIN_PATH_FEASIBLE_FRACTION
        - safe_float(metrics.get("path_mechanism_feasible_fraction"), 0.0),
    )
    target_path_shortfall = max(
        0.0,
        CHECKPOINT_MIN_TARGET_FEASIBLE_FRACTION
        - safe_float(metrics.get("path_target_feasible_fraction"), 0.0),
    )
    path_excess_mean_overage = max(
        0.0,
        safe_float(metrics.get("path_excess_mean"), float("inf"))
        - CHECKPOINT_MAX_PATH_EXCESS_MEAN,
    )
    point_excess_mean_overage = max(
        0.0,
        safe_float(metrics.get("point_path_excess_mean"), float("inf"))
        - CHECKPOINT_MAX_POINT_EXCESS_MEAN,
    )
    assembly_shortfall = max(
        0.0,
        CHECKPOINT_MIN_FULL_CYCLE_ASSEMBLY
        - safe_float(metrics.get("full_cycle_assembly_ratio"), 0.0),
    )
    grashof_excess = max(
        0.0,
        safe_float(metrics.get("grashof_penalty"), float("inf"))
        - (teacher_grashof + CHECKPOINT_GRASHOF_DELTA),
    )
    crank_excess = max(
        0.0,
        safe_float(metrics.get("crank_shortness_penalty"), float("inf"))
        - (teacher_crank + CHECKPOINT_CRANK_DELTA),
    )
    adjacency_excess = max(
        0.0,
        safe_float(metrics.get("adjacency_penalty"), float("inf"))
        - (teacher_adj + CHECKPOINT_ADJACENCY_DELTA),
    )
    assembly_violation = max(
        0.0,
        safe_float(metrics.get("full_cycle_assembly_violation"), float("inf")),
    )
    diagnostics = {
        "checkpoint_mean_path_budget_excess": mean_path_budget_excess,
        "checkpoint_path_shortfall": path_shortfall,
        "checkpoint_target_path_shortfall": target_path_shortfall,
        "checkpoint_path_excess_mean_overage": path_excess_mean_overage,
        "checkpoint_point_excess_mean_overage": point_excess_mean_overage,
        "checkpoint_assembly_shortfall": assembly_shortfall,
        "checkpoint_grashof_excess": grashof_excess,
        "checkpoint_crank_excess": crank_excess,
        "checkpoint_adjacency_excess": adjacency_excess,
        "checkpoint_assembly_violation": assembly_violation,
    }
    feasible = all(value <= 1e-12 for value in diagnostics.values())
    return feasible, diagnostics

def base_validation_stability_metric(metrics: Dict[str, float]) -> float:
    """Physical validation objective with fixed weights and no adaptive multipliers.

    The metric is used only for numerical spike/catastrophe detection.  It
    cannot jump because the feasibility controller changed a multiplier, and
    it uses the final transmission weights even while the training ramp is in
    progress.
    """
    fixed_terms = (
        safe_float(metrics.get("distance_loss"), 0.0),
        safe_float(metrics.get("grashof_penalty"), 0.0),
        safe_float(metrics.get("crank_shortness_penalty"), 0.0),
        safe_float(metrics.get("adjacency_penalty"), 0.0),
        safe_float(metrics.get("assembly_penalty"), 0.0),
        safe_float(metrics.get("path_constraint_penalty"), 0.0),
        safe_float(metrics.get("point_path_guard_penalty"), 0.0),
        TRANSMISSION_TARGET_WEIGHT_MAX
        * safe_float(metrics.get("target_transmission_penalty_raw"), 0.0),
        TRANSMISSION_GLOBAL_WEIGHT_MAX
        * safe_float(metrics.get("global_transmission_penalty_raw"), 0.0),
        CLASS_MARGIN_WEIGHT
        * safe_float(metrics.get("smooth_class_margin_penalty_raw"), 0.0),
    )
    if not all(np.isfinite(value) for value in fixed_terms):
        return float("inf")
    return float(sum(fixed_terms))


def engineering_recovery_materiality(
    metrics: Dict[str, float],
) -> Tuple[bool, Dict[str, float]]:
    """Separate deployability gates from rollback-worthy deterioration.

    Small boundary misses still feed the adaptive multiplier windows. An
    engineering restore is reserved for a materially bad path distribution or
    a meaningful physical/class violation repeated across the recovery window.
    """
    _, diagnostics = validation_feasibility(metrics)
    material_terms = {
        "material_mean_budget_excess": max(
            0.0,
            diagnostics["checkpoint_mean_path_budget_excess"]
            - RECOVERY_MATERIAL_MEAN_BUDGET_EXCESS,
        ),
        "material_path_shortfall": max(
            0.0,
            diagnostics["checkpoint_path_shortfall"]
            - RECOVERY_MATERIAL_PATH_SHORTFALL,
        ),
        "material_target_shortfall": max(
            0.0,
            diagnostics["checkpoint_target_path_shortfall"]
            - RECOVERY_MATERIAL_TARGET_SHORTFALL,
        ),
        "material_path_excess_overage": max(
            0.0,
            diagnostics["checkpoint_path_excess_mean_overage"]
            - RECOVERY_MATERIAL_PATH_EXCESS_OVERAGE,
        ),
        "material_point_excess_overage": max(
            0.0,
            diagnostics["checkpoint_point_excess_mean_overage"]
            - RECOVERY_MATERIAL_POINT_EXCESS_OVERAGE,
        ),
        # Physical/class terms already represent excess beyond checkpoint
        # tolerances. Require another tolerance-sized step before treating the
        # miss as rollback-worthy; smaller misses strengthen multipliers only.
        "material_assembly_shortfall": max(
            0.0, diagnostics["checkpoint_assembly_shortfall"] - 5e-4
        ),
        "material_assembly_violation": max(
            0.0, diagnostics["checkpoint_assembly_violation"] - 1e-4
        ),
        "material_grashof_excess": max(
            0.0, diagnostics["checkpoint_grashof_excess"] - CHECKPOINT_GRASHOF_DELTA
        ),
        "material_crank_excess": max(
            0.0, diagnostics["checkpoint_crank_excess"] - CHECKPOINT_CRANK_DELTA
        ),
        "material_adjacency_excess": max(
            0.0,
            diagnostics["checkpoint_adjacency_excess"] - CHECKPOINT_ADJACENCY_DELTA,
        ),
    }
    material = any(value > 1e-12 for value in material_terms.values())
    # A dimensionless severity is used for logging, not thresholding.
    scales = {
        "material_mean_budget_excess": max(RECOVERY_MATERIAL_MEAN_BUDGET_EXCESS, 1e-12),
        "material_path_shortfall": max(RECOVERY_MATERIAL_PATH_SHORTFALL, 1e-12),
        "material_target_shortfall": max(RECOVERY_MATERIAL_TARGET_SHORTFALL, 1e-12),
        "material_path_excess_overage": max(RECOVERY_MATERIAL_PATH_EXCESS_OVERAGE, 1e-12),
        "material_point_excess_overage": max(RECOVERY_MATERIAL_POINT_EXCESS_OVERAGE, 1e-12),
        "material_assembly_shortfall": 5e-4,
        "material_assembly_violation": 1e-4,
        "material_grashof_excess": max(CHECKPOINT_GRASHOF_DELTA, 1e-12),
        "material_crank_excess": max(CHECKPOINT_CRANK_DELTA, 1e-12),
        "material_adjacency_excess": max(CHECKPOINT_ADJACENCY_DELTA, 1e-12),
    }
    severity = max(
        (material_terms[name] / scales[name] for name in material_terms),
        default=0.0,
    )
    material_terms["engineering_recovery_severity"] = float(severity)
    material_terms["engineering_recovery_material"] = 1.0 if material else 0.0
    return material, material_terms


def annotate_validation_metrics(metrics: Dict[str, float]) -> Dict[str, float]:
    annotated = dict(metrics)
    feasible, diagnostics = validation_feasibility(annotated)
    annotated.update(diagnostics)
    material, material_diagnostics = engineering_recovery_materiality(annotated)
    annotated.update(material_diagnostics)
    annotated["checkpoint_feasible"] = 1.0 if feasible else 0.0
    annotated["engineering_recovery_material"] = 1.0 if material else 0.0
    annotated["scheduler_metric"] = transmission_scheduler_metric(annotated)
    annotated["validation_stability_metric"] = base_validation_stability_metric(annotated)
    return annotated


def transmission_scheduler_metric(metrics: Dict[str, float]) -> float:
    """Target-transmission metric with feasibility barriers.

    A feasible state is scored only by raw target transmission penalty. Path,
    assembly, or mechanism-class violations add smooth barriers, so the
    scheduler cannot mistake an infeasible transmission improvement for useful
    progress.
    """
    target_metric = safe_float(
        metrics.get("target_transmission_penalty_raw"), float("inf")
    )
    feasible, diagnostics = validation_feasibility(metrics)
    if feasible:
        return float(target_metric)

    return float(
        target_metric
        + 100.0 * diagnostics["checkpoint_mean_path_budget_excess"]
        + 10.0 * diagnostics["checkpoint_path_shortfall"]
        + 10.0 * diagnostics["checkpoint_target_path_shortfall"]
        + 100.0 * diagnostics["checkpoint_path_excess_mean_overage"]
        + 100.0 * diagnostics["checkpoint_point_excess_mean_overage"]
        + 10.0 * diagnostics["checkpoint_assembly_shortfall"]
        + 100.0 * diagnostics["checkpoint_grashof_excess"]
        + 100.0 * diagnostics["checkpoint_crank_excess"]
        + 100.0 * diagnostics["checkpoint_adjacency_excess"]
        + 100.0 * diagnostics["checkpoint_assembly_violation"]
    )


CONSTRAINT_GROUPS = (
    "path",
    "point_path",
    "assembly",
    "grashof",
    "crank",
    "class_margin",
)


def multiplier_snapshot() -> Dict[str, float]:
    return {name: float(constraint_multipliers[name]) for name in CONSTRAINT_GROUPS}


def constraint_violation_groups(metrics: Dict[str, float]) -> Tuple[Dict[str, bool], Dict[str, float]]:
    _, diagnostics = validation_feasibility(metrics)
    groups = {
        "path": any(
            diagnostics[name] > 1e-12
            for name in (
                "checkpoint_mean_path_budget_excess",
                "checkpoint_path_shortfall",
                "checkpoint_path_excess_mean_overage",
            )
        ),
        "point_path": any(
            diagnostics[name] > 1e-12
            for name in (
                "checkpoint_target_path_shortfall",
                "checkpoint_point_excess_mean_overage",
            )
        ),
        "assembly": any(
            diagnostics[name] > 1e-12
            for name in (
                "checkpoint_assembly_shortfall",
                "checkpoint_assembly_violation",
            )
        ),
        "grashof": diagnostics["checkpoint_grashof_excess"] > 1e-12,
        "crank": diagnostics["checkpoint_crank_excess"] > 1e-12,
        "class_margin": diagnostics["checkpoint_adjacency_excess"] > 1e-12,
    }
    return groups, diagnostics


def constraint_multiplier_cap(name: str) -> float:
    if name == "point_path":
        return ADAPTIVE_POINT_PATH_MAX
    return ADAPTIVE_CONSTRAINT_MAX


def feasibility_window_counts() -> Tuple[int, int]:
    return len(feasibility_window), int(sum(feasibility_window))


def constraint_window_counts() -> Dict[str, int]:
    return {
        name: int(sum(constraint_violation_windows[name]))
        for name in CONSTRAINT_GROUPS
    }


def persistent_constraint_violation_groups() -> Dict[str, bool]:
    counts = constraint_window_counts()
    return {
        name: (
            len(constraint_violation_windows[name]) >= MULTIPLIER_WINDOW_SIZE
            and counts[name] >= MULTIPLIER_VIOLATION_TRIGGER
        )
        for name in CONSTRAINT_GROUPS
    }


def material_recovery_window_counts() -> Tuple[int, int]:
    return len(material_recovery_window), int(sum(material_recovery_window))


def engineering_recovery_window_ready() -> bool:
    observed, material_failures = material_recovery_window_counts()
    return (
        observed >= FEASIBILITY_RECOVERY_WINDOW
        and material_failures >= FEASIBILITY_RECOVERY_PATIENCE
    )


def clear_feasibility_windows() -> None:
    feasibility_window.clear()
    material_recovery_window.clear()
    for history in constraint_violation_windows.values():
        history.clear()


def record_feasibility_observation(
    feasible: bool,
    groups: Dict[str, bool],
    material_recovery_failure: bool,
) -> None:
    feasibility_window.append(0 if feasible else 1)
    material_recovery_window.append(1 if material_recovery_failure else 0)
    for name in CONSTRAINT_GROUPS:
        constraint_violation_windows[name].append(1 if groups.get(name, False) else 0)


def proposed_constraint_multipliers(
    metrics: Dict[str, float],
    *,
    allow_decay: bool,
    groups_override: Optional[Dict[str, bool]] = None,
) -> Tuple[Dict[str, float], Dict[str, bool], Dict[str, float]]:
    current_groups, diagnostics = constraint_violation_groups(metrics)
    groups = dict(groups_override) if groups_override is not None else current_groups
    proposed = multiplier_snapshot()
    for name in CONSTRAINT_GROUPS:
        if groups.get(name, False):
            proposed[name] = min(
                constraint_multiplier_cap(name),
                proposed[name] * ADAPTIVE_CONSTRAINT_GROWTH,
            )
        elif allow_decay:
            proposed[name] = max(1.0, proposed[name] * ADAPTIVE_CONSTRAINT_DECAY)
    return proposed, groups, diagnostics


def set_constraint_multipliers(values: Dict[str, float]) -> None:
    for name in CONSTRAINT_GROUPS:
        value = safe_float(values.get(name), constraint_multipliers[name])
        constraint_multipliers[name] = min(
            constraint_multiplier_cap(name),
            max(1.0, value),
        )


def log_constraint_state(
    epoch_number: int,
    reason: str,
    groups: Optional[Dict[str, bool]] = None,
) -> None:
    groups = groups or {name: False for name in CONSTRAINT_GROUPS}
    window_observed, window_infeasible = feasibility_window_counts()
    material_observed, material_failures = material_recovery_window_counts()
    violation_counts = constraint_window_counts()
    append_csv(CONSTRAINT_HISTORY_PATH, {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": epoch_number,
        "reason": reason,
        "infeasible_streak": consecutive_infeasible_epochs,
        "feasible_streak": consecutive_feasible_epochs,
        "feasibility_window_observed": window_observed,
        "feasibility_window_infeasible": window_infeasible,
        "feasibility_window_trigger": FEASIBILITY_RECOVERY_PATIENCE,
        "material_window_observed": material_observed,
        "material_window_failures": material_failures,
        "feasibility_recovery_count": feasibility_recovery_count,
        "min_lr_recoveries_without_primary_improvement": (
            min_lr_recoveries_without_primary_improvement
        ),
        "current_stream_index": current_stream_index,
        "current_stream_seed": current_stream_seed,
        "streaming_unique_targets_seen": streaming_unique_targets_seen,
        **{f"violated_{name}": bool(groups.get(name, False)) for name in CONSTRAINT_GROUPS},
        **{f"window_violations_{name}": violation_counts[name] for name in CONSTRAINT_GROUPS},
        **{f"multiplier_{name}": constraint_multipliers[name] for name in CONSTRAINT_GROUPS},
    })

def maybe_update_constraint_multipliers(
    metrics: Dict[str, float],
    epoch_index: int,
    *,
    force: bool = False,
    allow_decay: bool = True,
    reason: str = "validation_update",
) -> bool:
    global last_constraint_update_epoch
    if (
        not force
        and epoch_index - last_constraint_update_epoch < ADAPTIVE_UPDATE_INTERVAL
    ):
        return False

    if allow_decay:
        if consecutive_feasible_epochs < MULTIPLIER_DECAY_FEASIBLE_STREAK:
            return False
        groups = {name: False for name in CONSTRAINT_GROUPS}
    else:
        groups = persistent_constraint_violation_groups()
        if not any(groups.values()):
            return False

    proposed, groups, _ = proposed_constraint_multipliers(
        metrics,
        allow_decay=allow_decay,
        groups_override=groups,
    )
    before = multiplier_snapshot()
    if all(abs(proposed[name] - before[name]) <= 1e-12 for name in CONSTRAINT_GROUPS):
        return False
    multiplier_increased = any(
        proposed[name] > before[name] + 1e-12 for name in CONSTRAINT_GROUPS
    )
    set_constraint_multipliers(proposed)

    # A multiplier increase changes the constrained objective while keeping the
    # current model on the frontier. Preserve model weights, but discard Adam's
    # stale first/second moments so the next update reflects the new objective.
    cleared_optimizer_states = 0
    if multiplier_increased:
        cleared_optimizer_states = clear_adamw_moments()
        if hasattr(scheduler, "num_bad_epochs"):
            scheduler.num_bad_epochs = 0
        if hasattr(scheduler, "cooldown_counter"):
            scheduler.cooldown_counter = 0
        if hasattr(scheduler, "_last_lr"):
            scheduler._last_lr = [group["lr"] for group in optimizer.param_groups]

    last_constraint_update_epoch = epoch_index
    log_constraint_state(epoch_index + 1, reason, groups)
    log_event(
        epoch_index + 1,
        "constraint_multiplier_update",
        reason=reason,
        lr_before=current_lr(),
        lr_after=current_lr(),
        details=(
            f"before={json.dumps(before, sort_keys=True)}; "
            f"after={json.dumps(multiplier_snapshot(), sort_keys=True)}; "
            f"persistent_violations={json.dumps(groups, sort_keys=True)}; "
            f"window_counts={json.dumps(constraint_window_counts(), sort_keys=True)}; "
            f"feasibility_window={list(feasibility_window)}; "
            f"adam_moment_entries_cleared={cleared_optimizer_states}"
        ),
    )
    print(
        "[CONSTRAINTS] "
        + ", ".join(
            f"{name}={before[name]:.2f}->{constraint_multipliers[name]:.2f}"
            for name in CONSTRAINT_GROUPS
            if abs(before[name] - constraint_multipliers[name]) > 1e-12
        )
        + (
            f" | Adam states cleared={cleared_optimizer_states}"
            if multiplier_increased else ""
        )
    )
    return True


def clear_adamw_moments() -> int:
    """Clear AdamW momentum while preserving the optimizer object/param groups."""
    state_entries = len(optimizer.state)
    optimizer.state.clear()
    return state_entries


def recover_engineering_feasibility(
    metrics: Dict[str, float],
    epoch_index: int,
    pre_train_loss: float,
    pre_val_loss: float,
) -> bool:
    """Restore feasible model weights without rewinding the target stream.

    Numerical recovery remains fully coherent. Engineering recovery is
    intentionally different: the adaptive objective changed, so R2.4 restores
    only the best deployable model weights, preserves the live Monte Carlo
    stream and run timeline, clears Adam moments, and continues at a lower LR.
    """
    global feasibility_recovery_count, consecutive_infeasible_epochs
    global consecutive_feasible_epochs, scheduler_hold_until_epoch
    global feasibility_recovery_hold_until_epoch
    global grace_counter, stagnant_epoch_count
    global prev_epoch_loss, prev_val_loss, avg_epoch_loss, avg_epoch_distance
    global last_val_metrics, last_constraint_update_epoch
    global prev_train_stability_metric, prev_validation_stability_metric
    global min_lr_recoveries_without_primary_improvement

    if not BEST_FEASIBLE_TRANSMISSION_CHECKPOINT.exists():
        print("[FEASIBILITY] No feasible checkpoint is available for recovery.")
        return False

    live_lr = current_lr()
    live_recovery_count = feasibility_recovery_count
    groups = persistent_constraint_violation_groups()
    if not any(groups.values()):
        groups, _ = constraint_violation_groups(metrics)
    window_snapshot = list(feasibility_window)
    material_window_snapshot = list(material_recovery_window)
    violation_count_snapshot = constraint_window_counts()

    if last_constraint_update_epoch == epoch_index:
        proposed = multiplier_snapshot()
        _, diagnostics = validation_feasibility(metrics)
    else:
        proposed, groups, diagnostics = proposed_constraint_multipliers(
            metrics,
            allow_decay=False,
            groups_override=groups,
        )

    try:
        checkpoint = torch_load(
            BEST_FEASIBLE_TRANSMISSION_CHECKPOINT, map_location=device
        )
        if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
            raise KeyError("model_state_dict")
        model.load_state_dict(checkpoint["model_state_dict"])
    except Exception as exc:
        print(f"[FEASIBILITY] Failed to restore feasible model weights: {exc}")
        return False

    checkpoint_epoch = int(
        checkpoint.get("state_epoch", checkpoint.get("epoch", -1))
    )
    checkpoint_completed_epoch = int(checkpoint.get("epoch", -1))
    checkpoint_train_loss = safe_float(checkpoint.get("loss"), float("inf"))
    checkpoint_train_distance = safe_float(
        checkpoint.get("mean_distance"), float("inf")
    )
    checkpoint_val_loss = safe_float(
        checkpoint.get("val_loss"), float("inf")
    )
    checkpoint_lr = safe_float(checkpoint.get("lr"), live_lr)

    # Preserve or strengthen the current constraint regime. The checkpoint's
    # historic multipliers are deliberately not restored.
    merged = multiplier_snapshot()
    for name in CONSTRAINT_GROUPS:
        merged[name] = max(merged[name], proposed[name])
    set_constraint_multipliers(merged)

    # The objective regime changed, so stale Adam moments are inappropriate.
    # Keep the optimizer object/param groups to preserve scheduler attachment.
    cleared_optimizer_states = clear_adamw_moments()
    recovery_lr = max(
        MIN_LR,
        min(live_lr, checkpoint_lr) * FEASIBILITY_RECOVERY_LR_FACTOR,
    )
    for group in optimizer.param_groups:
        group["lr"] = recovery_lr
    clamp_lr(optimizer)

    if recovery_lr <= MIN_LR * (1.0 + 1e-9):
        min_lr_recoveries_without_primary_improvement += 1
    else:
        min_lr_recoveries_without_primary_improvement = 0

    if hasattr(scheduler, "_last_lr"):
        scheduler._last_lr = [group["lr"] for group in optimizer.param_groups]
    if hasattr(scheduler, "num_bad_epochs"):
        scheduler.num_bad_epochs = 0
    if hasattr(scheduler, "cooldown_counter"):
        scheduler.cooldown_counter = 0
    if not scheduler_is_attached():
        raise RuntimeError(
            "Engineering recovery detached the scheduler from the optimizer"
        )

    feasibility_recovery_count = live_recovery_count + 1
    last_constraint_update_epoch = epoch_index
    consecutive_infeasible_epochs = 0
    consecutive_feasible_epochs = 0
    clear_feasibility_windows()
    grace_counter = max(grace_counter, FEASIBILITY_RECOVERY_COOLDOWN)
    hold_until_epoch = epoch_index + FEASIBILITY_RECOVERY_COOLDOWN + 1
    scheduler_hold_until_epoch = max(scheduler_hold_until_epoch, hold_until_epoch)
    feasibility_recovery_hold_until_epoch = max(
        feasibility_recovery_hold_until_epoch, hold_until_epoch
    )
    stagnant_epoch_count = 0

    # Do not rewind current_state_epoch, the target stream, or random states.
    # The next loop iteration deterministically advances to its assigned fresh
    # target set. Training loss is only diagnostic under streaming.
    prev_epoch_loss = None
    prev_val_loss = checkpoint_val_loss
    prev_train_stability_metric = None
    prev_validation_stability_metric = None
    avg_epoch_loss = (
        checkpoint_train_loss if np.isfinite(checkpoint_train_loss)
        else pre_train_loss
    )
    avg_epoch_distance = (
        checkpoint_train_distance if np.isfinite(checkpoint_train_distance)
        else avg_epoch_distance
    )
    last_val_metrics = annotate_validation_metrics(evaluate_fixed_validation())

    label = "engineering_feasibility | model-only feasible restore"
    log_rollback_event(
        epoch_index + 1,
        pre_train_loss,
        checkpoint_train_loss,
        live_lr,
        recovery_lr,
        label,
        checkpoint_path=str(BEST_FEASIBLE_TRANSMISSION_CHECKPOINT),
        checkpoint_epoch=checkpoint_epoch,
        val_loss_before=pre_val_loss,
        checkpoint_val_loss=checkpoint_val_loss,
        lr_loaded=checkpoint_lr,
    )
    log_event(
        epoch_index + 1,
        "engineering_feasibility_recovery",
        reason=label,
        checkpoint=str(BEST_FEASIBLE_TRANSMISSION_CHECKPOINT),
        checkpoint_epoch=checkpoint_epoch,
        train_loss_before=pre_train_loss,
        val_loss_before=pre_val_loss,
        checkpoint_train_loss=checkpoint_train_loss,
        checkpoint_val_loss=checkpoint_val_loss,
        lr_before=live_lr,
        lr_loaded=checkpoint_lr,
        lr_after=recovery_lr,
        details=(
            f"recovery_count={feasibility_recovery_count}; "
            f"checkpoint_completed_epoch={checkpoint_completed_epoch}; "
            f"scheduler_hold_until_zero_based_epoch={scheduler_hold_until_epoch}; "
            f"feasibility_hold_until_zero_based_epoch="
            f"{feasibility_recovery_hold_until_epoch}; "
            f"multipliers={json.dumps(multiplier_snapshot(), sort_keys=True)}; "
            f"recovery_window={window_snapshot}; "
            f"material_recovery_window={material_window_snapshot}; "
            f"window_violation_counts={json.dumps(violation_count_snapshot, sort_keys=True)}; "
            f"optimizer_moment_entries_cleared={cleared_optimizer_states}; "
            f"stream_preserved_index={current_stream_index}; "
            f"stream_preserved_seed={current_stream_seed}; "
            f"stream_unique_targets_seen={streaming_unique_targets_seen}; "
            f"min_lr_recoveries_without_primary_improvement="
            f"{min_lr_recoveries_without_primary_improvement}; "
            f"diagnostics={json.dumps(diagnostics, sort_keys=True)}"
        ),
    )
    log_constraint_state(epoch_index + 1, "engineering_feasibility_recovery", groups)
    print(
        f"[FEASIBILITY RECOVERY] Restored model weights from state epoch "
        f"{checkpoint_epoch} without rewinding stream {current_stream_index} | "
        f"LR {live_lr:.2e}->{recovery_lr:.2e} | "
        f"recovery {feasibility_recovery_count}/{MAX_FEASIBILITY_RECOVERIES} | "
        f"Adam states cleared={cleared_optimizer_states}"
    )
    return True


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
        "current_stream_index": current_stream_index,
        "current_stream_seed": current_stream_seed,
        "streaming_unique_targets_seen": streaming_unique_targets_seen,
        "rng_state": capture_rng_state(),
        "recent_distances": list(recent_dist_deque),
        "recent_validation_distances": list(recent_val_dist_deque),
        "recent_transmission_metrics": list(recent_transmission_metric_deque),
        "feasibility_window": list(feasibility_window),
        "material_recovery_window": list(material_recovery_window),
        "constraint_violation_windows": {
            name: list(constraint_violation_windows[name]) for name in CONSTRAINT_GROUPS
        },
        "stagnant_epoch_count": stagnant_epoch_count,
        "consecutive_dead_gradient_epochs": consecutive_dead_gradient_epochs,
        "consecutive_dead_catastrophic_epochs": consecutive_dead_catastrophic_epochs,
        "current_state_epoch": current_state_epoch,
        "best_train_loss": best_loss,
        "best_validation_loss": best_val_loss,
        "best_validation_stability_metric": best_validation_stability_metric,
        "prev_train_stability_metric": prev_train_stability_metric,
        "prev_validation_stability_metric": prev_validation_stability_metric,
        "best_path_distance": best_path_distance,
        "best_feasible_transmission_penalty": best_feasible_transmission_penalty,
        "best_feasible_transmission_angle": best_feasible_transmission_angle,
        "epochs_since_primary_improvement": epochs_since_primary_improvement,
        "constraint_multipliers": multiplier_snapshot(),
        "consecutive_infeasible_epochs": consecutive_infeasible_epochs,
        "consecutive_feasible_epochs": consecutive_feasible_epochs,
        "feasibility_recovery_count": feasibility_recovery_count,
        "min_lr_recoveries_without_primary_improvement": (
            min_lr_recoveries_without_primary_improvement
        ),
        "last_constraint_update_epoch": last_constraint_update_epoch,
        "scheduler_hold_until_epoch": scheduler_hold_until_epoch,
        "feasibility_recovery_hold_until_epoch": (
            feasibility_recovery_hold_until_epoch
        ),
        "teacher_model_source": teacher_model_source,
        "teacher_model_sha256": teacher_model_sha256,
        "path_tolerance": PATH_TOLERANCE,
        "path_constraint_weight": PATH_CONSTRAINT_WEIGHT,
        "point_path_tolerance": POINT_PATH_TOLERANCE,
        "point_path_guard_weight": POINT_PATH_GUARD_WEIGHT,
        "checkpoint_min_path_feasible_fraction": CHECKPOINT_MIN_PATH_FEASIBLE_FRACTION,
        "checkpoint_min_target_feasible_fraction": CHECKPOINT_MIN_TARGET_FEASIBLE_FRACTION,
        "checkpoint_max_path_excess_mean": CHECKPOINT_MAX_PATH_EXCESS_MEAN,
        "checkpoint_max_point_excess_mean": CHECKPOINT_MAX_POINT_EXCESS_MEAN,
        "checkpoint_min_full_cycle_assembly": CHECKPOINT_MIN_FULL_CYCLE_ASSEMBLY,
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
        "val_target_transmission_penalty": safe_float(
            checkpoint.get("val_metrics", {}).get("target_transmission_penalty_raw"),
            float("inf"),
        ),
        "val_target_transmission_min_angle": safe_float(
            checkpoint.get("val_metrics", {}).get("target_transmission_min_angle_deg"),
            float("nan"),
        ),
        "val_path_feasible_fraction": safe_float(
            checkpoint.get("val_metrics", {}).get("path_mechanism_feasible_fraction"),
            float("nan"),
        ),
        "checkpoint_feasible": bool(
            checkpoint.get("val_metrics", {}).get("checkpoint_feasible", False)
        ),
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
    global best_path_distance, best_feasible_transmission_penalty
    global best_feasible_transmission_angle, epochs_since_primary_improvement
    global consecutive_infeasible_epochs, consecutive_feasible_epochs
    global feasibility_recovery_count, last_constraint_update_epoch
    global scheduler_hold_until_epoch, feasibility_recovery_hold_until_epoch
    global best_validation_stability_metric
    global prev_train_stability_metric, prev_validation_stability_metric
    global current_stream_index, current_stream_seed, streaming_unique_targets_seen
    global min_lr_recoveries_without_primary_improvement
    if not path or not Path(path).exists():
        print(f"[WARN] Cannot restore checkpoint - path is invalid: {path}")
        return False, None
    try:
        checkpoint = torch_load(Path(path), map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])

        if "optimizer_state_dict" not in checkpoint:
            raise KeyError("optimizer_state_dict is required for coherent R2.4 recovery")
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        if checkpoint.get("scheduler_state_dict") is not None:
            scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        else:
            # Old V5.3 checkpoints did not save scheduler state. Keep the same
            # optimizer object and recreate only the scheduler around it.
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, factor=0.5, patience=SCHEDULER_PATIENCE, min_lr=MIN_LR
            )
            print("[WARN] R2.4 checkpoint lacked scheduler state; scheduler recreated.")

        annealing_scheduler = None  # R1 intentionally disables cosine annealing.

        if checkpoint.get("training_target_points") is not None:
            training_target_points = checkpoint["training_target_points"].detach().cpu()

        restore_rng_state(checkpoint.get("rng_state"))
        build_dataloader()

        recent_dist_deque.clear()
        recent_dist_deque.extend(checkpoint.get("recent_distances", []))
        recent_val_dist_deque.clear()
        recent_val_dist_deque.extend(checkpoint.get("recent_validation_distances", []))
        recent_transmission_metric_deque.clear()
        recent_transmission_metric_deque.extend(
            checkpoint.get("recent_transmission_metrics", [])
        )
        feasibility_window.clear()
        feasibility_window.extend(checkpoint.get("feasibility_window", []))
        material_recovery_window.clear()
        material_recovery_window.extend(
            checkpoint.get("material_recovery_window", [])
        )
        restored_windows = checkpoint.get("constraint_violation_windows", {})
        for name in CONSTRAINT_GROUPS:
            constraint_violation_windows[name].clear()
            constraint_violation_windows[name].extend(restored_windows.get(name, []))
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
        best_validation_stability_metric = safe_float(
            checkpoint.get("best_validation_stability_metric"),
            best_validation_stability_metric,
        )
        prev_train_stability_metric = checkpoint.get(
            "prev_train_stability_metric", prev_train_stability_metric
        )
        prev_validation_stability_metric = checkpoint.get(
            "prev_validation_stability_metric", prev_validation_stability_metric
        )
        best_path_distance = safe_float(
            checkpoint.get("best_path_distance"), best_path_distance
        )
        best_feasible_transmission_penalty = safe_float(
            checkpoint.get("best_feasible_transmission_penalty"),
            best_feasible_transmission_penalty,
        )
        best_feasible_transmission_angle = safe_float(
            checkpoint.get("best_feasible_transmission_angle"),
            best_feasible_transmission_angle,
        )
        epochs_since_primary_improvement = int(
            checkpoint.get(
                "epochs_since_primary_improvement",
                epochs_since_primary_improvement,
            )
        )
        set_constraint_multipliers(
            checkpoint.get("constraint_multipliers", multiplier_snapshot())
        )
        consecutive_infeasible_epochs = int(
            checkpoint.get("consecutive_infeasible_epochs", 0)
        )
        consecutive_feasible_epochs = int(
            checkpoint.get("consecutive_feasible_epochs", 0)
        )
        feasibility_recovery_count = int(
            checkpoint.get("feasibility_recovery_count", feasibility_recovery_count)
        )
        min_lr_recoveries_without_primary_improvement = int(
            checkpoint.get(
                "min_lr_recoveries_without_primary_improvement",
                min_lr_recoveries_without_primary_improvement,
            )
        )
        current_stream_index = int(
            checkpoint.get("current_stream_index", current_stream_index)
        )
        current_stream_seed = int(
            checkpoint.get("current_stream_seed", current_stream_seed)
        )
        streaming_unique_targets_seen = int(
            checkpoint.get(
                "streaming_unique_targets_seen", streaming_unique_targets_seen
            )
        )
        last_constraint_update_epoch = int(
            checkpoint.get("last_constraint_update_epoch", last_constraint_update_epoch)
        )
        scheduler_hold_until_epoch = int(
            checkpoint.get("scheduler_hold_until_epoch", scheduler_hold_until_epoch)
        )
        feasibility_recovery_hold_until_epoch = int(
            checkpoint.get(
                "feasibility_recovery_hold_until_epoch",
                feasibility_recovery_hold_until_epoch,
            )
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

    add(candidate_record(
        BEST_FEASIBLE_TRANSMISSION_CHECKPOINT,
        "best feasible transmission",
        2,
    ))
    add(candidate_record(BEST_COMPOSITE_CHECKPOINT, "best composite", 2))
    add(candidate_record(BEST_PATH_CHECKPOINT, "best path", 3))

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
    global prev_train_stability_metric, prev_validation_stability_metric

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
            f"[RECOVERY] R2.4 found no eligible checkpoint ({reason}); "
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
            f"[RECOVERY] R2.4 restore failed; applied in-place LR backoff "
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
    prev_train_stability_metric = None
    prev_validation_stability_metric = None
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
            "R2.4 coherent restore: AdamW moments, scheduler, data, sampler/RNG "
            f"restored; no fresh data; plateau cooldown={grace_counter}"
        ),
    )
    print(
        f"[RECOVERY] R2.4 restored {selected['source']} checkpoint "
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
        "best_path_distance": best_path_distance,
        "best_feasible_transmission_penalty": best_feasible_transmission_penalty,
        "best_feasible_transmission_angle": best_feasible_transmission_angle,
        "epochs_since_primary_improvement": epochs_since_primary_improvement,
        "consecutive_infeasible_epochs": consecutive_infeasible_epochs,
        "consecutive_feasible_epochs": consecutive_feasible_epochs,
        "feasibility_recovery_count": feasibility_recovery_count,
        "feasibility_window_observed": feasibility_window_counts()[0],
        "feasibility_window_infeasible": feasibility_window_counts()[1],
        "feasibility_window_trigger": FEASIBILITY_RECOVERY_PATIENCE,
        "material_window_observed": material_recovery_window_counts()[0],
        "material_window_failures": material_recovery_window_counts()[1],
        "current_stream_index": current_stream_index,
        "current_stream_seed": current_stream_seed,
        "streaming_unique_targets_seen": streaming_unique_targets_seen,
        "min_lr_recoveries_without_primary_improvement": (
            min_lr_recoveries_without_primary_improvement
        ),
        **{f"constraint_window_violations_{name}": constraint_window_counts()[name] for name in CONSTRAINT_GROUPS},
        "validation_stability_metric": validation.get("validation_stability_metric", float("nan")),
        "scheduler_hold_until_epoch": scheduler_hold_until_epoch,
        "feasibility_recovery_hold_until_epoch": (
            feasibility_recovery_hold_until_epoch
        ),
        "feasibility_recovery_cooldown_active": (
            (epoch_number - 1) < feasibility_recovery_hold_until_epoch
        ),
        **{f"constraint_multiplier_{name}": constraint_multipliers[name] for name in CONSTRAINT_GROUPS},
        "validation_checkpoint_feasible": validation.get("checkpoint_feasible", float("nan")),
        "validation_scheduler_metric": validation.get("scheduler_metric", float("nan")),
        "scheduler_active": (epoch_number - 1) >= scheduler_hold_until_epoch,
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
        "catastrophic_validation_metric": instrumentation.get(
            "catastrophic_validation_metric", float("nan")
        ),
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
    print(
        "Mean worst target-hit transmission angle: "
        f"{metrics['target_transmission_min_angle_deg']:.2f} deg"
    )
    print(
        f"Target hits below {TRANSMISSION_TARGET_MIN_DEG:.0f} deg: "
        f"{metrics['target_transmission_below_35deg_fraction'] * 100:.2f}%"
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
recent_transmission_metric_deque = deque(maxlen=10)
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
best_validation_stability_metric = float("inf")
prev_train_stability_metric: Optional[float] = None
prev_validation_stability_metric: Optional[float] = None
best_path_distance = float("inf")
best_feasible_transmission_penalty = float("inf")
best_feasible_transmission_angle = float("-inf")
epochs_since_improvement = 0
epochs_since_val_improvement = 0
epochs_since_primary_improvement = 0
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
teacher_validation_baseline: Dict[str, float] = {}
scheduler_release_logged = False
constraint_multipliers: Dict[str, float] = {
    "path": 1.0,
    "point_path": 1.0,
    "assembly": 1.0,
    "grashof": 1.0,
    "crank": 1.0,
    "class_margin": 1.0,
}
consecutive_infeasible_epochs = 0
consecutive_feasible_epochs = 0
feasibility_recovery_count = 0
min_lr_recoveries_without_primary_improvement = 0
current_stream_index = -1
current_stream_seed = -1
streaming_unique_targets_seen = 0
feasibility_window = deque(maxlen=FEASIBILITY_RECOVERY_WINDOW)
material_recovery_window = deque(maxlen=FEASIBILITY_RECOVERY_WINDOW)
constraint_violation_windows: Dict[str, deque] = {
    name: deque(maxlen=MULTIPLIER_WINDOW_SIZE) for name in CONSTRAINT_GROUPS
}
last_constraint_update_epoch = -ADAPTIVE_UPDATE_INTERVAL
scheduler_hold_until_epoch = SCHEDULER_START_EPOCH
feasibility_recovery_hold_until_epoch = 0

if args.validation_targets_file:
    validation_source = Path(args.validation_targets_file)
    if not validation_source.exists():
        raise FileNotFoundError(f"Validation target file not found: {validation_source}")
    loaded_validation_targets = torch_load(validation_source, map_location="cpu")
    if isinstance(loaded_validation_targets, dict):
        for candidate_key in ("fixed_validation_targets", "validation_targets", "targets"):
            if candidate_key in loaded_validation_targets:
                loaded_validation_targets = loaded_validation_targets[candidate_key]
                break
    if not torch.is_tensor(loaded_validation_targets):
        raise TypeError("Validation target file must contain a torch.Tensor")
    if loaded_validation_targets.ndim != 2 or loaded_validation_targets.shape[1] != 6:
        raise ValueError(
            "Validation targets must have shape [N, 6], got "
            f"{tuple(loaded_validation_targets.shape)}"
        )
    fixed_validation_targets = loaded_validation_targets.detach().cpu().to(torch.float32).contiguous()
    print(
        f"[INFO] Loaded {len(fixed_validation_targets)} fixed validation targets "
        f"from {validation_source}"
    )
else:
    fixed_validation_targets = generate_target_point_triples(
        args.validation_samples, generator=validation_generator
    )
torch.save(fixed_validation_targets, VALIDATION_TARGETS_PATH)

training_target_points = torch.empty((0, 6), dtype=torch.float32)
refresh_streaming_targets(0, force=True, reason="initial_stream")
torch.save(training_target_points, INITIAL_TRAINING_TARGETS_PATH)

teacher_source_argument = args.teacher_model or args.initialize_from_model
if teacher_source_argument is None and args.load_checkpoint:
    resume_header = torch_load(Path(args.load_checkpoint), map_location="cpu")
    teacher_source_argument = resume_header.get("teacher_model_source")
if teacher_source_argument is None:
    raise ValueError(
        "R2.4 requires --teacher_model or --initialize_from_model so a frozen "
        "teacher can define the path budget."
    )
teacher_path = Path(teacher_source_argument)
if not teacher_path.exists():
    raise FileNotFoundError(f"Teacher checkpoint not found: {teacher_path}")
teacher_checkpoint = torch_load(teacher_path, map_location=device)
if isinstance(teacher_checkpoint, dict) and "model_state_dict" in teacher_checkpoint:
    teacher_state_dict = teacher_checkpoint["model_state_dict"]
    teacher_source_variant = teacher_checkpoint.get("variant")
    teacher_source_loss = safe_float(
        teacher_checkpoint.get(
            "val_loss",
            teacher_checkpoint.get("loss", teacher_checkpoint.get("train_loss")),
        )
    )
elif isinstance(teacher_checkpoint, dict):
    teacher_state_dict = teacher_checkpoint
    teacher_source_variant = None
    teacher_source_loss = float("nan")
else:
    raise TypeError("Teacher file must contain a checkpoint/state dictionary")
teacher_model = MechanismNN().to(device)
teacher_model.load_state_dict(teacher_state_dict)
teacher_model.eval()
for parameter in teacher_model.parameters():
    parameter.requires_grad_(False)
teacher_model_source = str(teacher_path.resolve())
teacher_model_sha256 = file_sha256(teacher_path)
print(
    f"[INFO] Loaded frozen teacher from {teacher_path} "
    f"(source variant={teacher_source_variant}, stored loss={teacher_source_loss:.6f})"
)
if teacher_source_variant not in ("V5.3-R2_GeometryFix", VARIANT):
    print(
        "[WARN] The recommended R2.4 teacher is the frozen "
        "V5.3-R2_GeometryFix best-validation checkpoint. "
        f"This file reports source variant={teacher_source_variant!r}."
    )

# The fixed validation teacher distances never change, so calculate them once.
teacher_validation_distance_chunks = []
with torch.no_grad():
    for start in range(0, len(fixed_validation_targets), args.validation_batch_size):
        teacher_batch = fixed_validation_targets[
            start:start + args.validation_batch_size
        ].to(device)
        teacher_validation_distance_chunks.append(
            compute_teacher_target_distances(
                teacher_batch, VALIDATION_NUM_SIM_STEPS
            ).cpu()
        )
fixed_validation_teacher_distances = torch.cat(
    teacher_validation_distance_chunks, dim=0
).contiguous()
torch.save(
    fixed_validation_teacher_distances,
    TEACHER_VALIDATION_DISTANCES_PATH,
)

model = MechanismNN().to(device)
model.apply(init_weights)
initialization_mode = "fresh_random"
initialization_source = None
initialization_source_variant = None
initialization_source_loss = float("nan")
if args.initialize_from_model:
    initialization_path = Path(args.initialize_from_model)
    if not initialization_path.exists():
        raise FileNotFoundError(f"Initialization checkpoint not found: {initialization_path}")
    initialization_checkpoint = torch_load(initialization_path, map_location=device)
    if isinstance(initialization_checkpoint, dict) and "model_state_dict" in initialization_checkpoint:
        initialization_state_dict = initialization_checkpoint["model_state_dict"]
        initialization_source_variant = initialization_checkpoint.get("variant")
        initialization_source_loss = safe_float(
            initialization_checkpoint.get(
                "val_loss",
                initialization_checkpoint.get("loss", initialization_checkpoint.get("train_loss")),
            )
        )
    elif isinstance(initialization_checkpoint, dict):
        initialization_state_dict = initialization_checkpoint
    else:
        raise TypeError("Initialization file must contain a checkpoint/state dictionary")
    model.load_state_dict(initialization_state_dict)
    initialization_mode = "model_only_fresh_optimizer"
    initialization_source = str(initialization_path.resolve())
    print(
        f"[INFO] Initialized R2.4 student weights from {initialization_path} "
        f"(source variant={initialization_source_variant}, stored loss={initialization_source_loss:.6f}); "
        "optimizer and scheduler start fresh."
    )
    if initialization_source_variant not in (
        "V5.3-R2.3a_WindowedFeasibilityController",
        "V5.3-R2.3_FeasibilityPreservingTransmission",
        "V5.3-R2.2_ConstrainedTransmission",
        VARIANT,
    ):
        print(
            "[WARN] The recommended R2.4 warm start is the selected "
            "V5.3-R2.3a best-feasible-transmission checkpoint. "
            f"This file reports source variant={initialization_source_variant!r}."
        )
optimizer = torch.optim.AdamW(model.parameters(), lr=INITIAL_LR, weight_decay=1e-5)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, factor=0.5, patience=SCHEDULER_PATIENCE, min_lr=MIN_LR
)
annealing_scheduler = None

teacher_validation_baseline = evaluate_fixed_validation(teacher_model)
teacher_validation_baseline = annotate_validation_metrics(
    teacher_validation_baseline
)
TEACHER_BASELINE_PATH.write_text(
    json.dumps(teacher_validation_baseline, indent=2, default=str),
    encoding="utf-8",
)
print(
    f"[TEACHER BASELINE] mean distance={teacher_validation_baseline['mean_distance']:.6f} | "
    f"target min transmission={teacher_validation_baseline['target_transmission_min_angle_deg']:.3f} deg | "
    f"target penalty={teacher_validation_baseline['target_transmission_penalty_raw']:.6f} | "
    f"path feasible={teacher_validation_baseline['path_mechanism_feasible_fraction']:.1%} | "
    f"full-cycle assembly={teacher_validation_baseline['full_cycle_assembly_ratio']:.1%}"
)

initial_validation = annotate_validation_metrics(evaluate_fixed_validation())
last_val_metrics = dict(initial_validation)
best_val_loss = initial_validation["loss"]
best_validation_stability_metric = initial_validation["validation_stability_metric"]
prev_validation_stability_metric = initial_validation["validation_stability_metric"]
best_val_mean_distance = initial_validation["mean_distance"]
best_path_distance = initial_validation["mean_distance"]
if bool(initial_validation.get("checkpoint_feasible", 0.0)):
    best_feasible_transmission_penalty = initial_validation[
        "target_transmission_penalty_raw"
    ]
    best_feasible_transmission_angle = initial_validation[
        "target_transmission_min_angle_deg"
    ]
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
    "num_points_per_stream_refresh": NUM_POINTS,
    "streaming_target_training": True,
    "stream_refresh_interval": STREAM_REFRESH_INTERVAL,
    "stream_seed_offset": STREAM_SEED_OFFSET,
    "batch_size": BATCH_SIZE,
    "initial_lr": INITIAL_LR,
    "min_lr": MIN_LR,
    "warmup_epochs": WARMUP_EPOCHS,
    "simulation_ramp": [INITIAL_NUM_SIM_STEPS, FINAL_NUM_SIM_STEPS, RAMP_START_EPOCH, RAMP_END_EPOCH],
    "fixed_validation_samples": len(fixed_validation_targets),
    "fixed_validation_steps": VALIDATION_NUM_SIM_STEPS,
    "enable_lr_boosts": ENABLE_LR_BOOSTS,
    "enable_cosine_annealing": ENABLE_COSINE_ANNEALING,
    "enable_periodic_data_refresh": ENABLE_PERIODIC_DATA_REFRESH,
    "recovery_lr_factor": RECOVERY_LR_FACTOR,
    "enable_loss_clamp": ENABLE_LOSS_CLAMP,
    "train_spike_validation_veto": True,
    "training_metric_spike_rollback_enabled": False,
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
    "transmission_target_min_degrees": TRANSMISSION_TARGET_MIN_DEG,
    "transmission_global_floor_degrees": TRANSMISSION_GLOBAL_FLOOR_DEG,
    "transmission_target_weight_max": TRANSMISSION_TARGET_WEIGHT_MAX,
    "transmission_global_weight_max": TRANSMISSION_GLOBAL_WEIGHT_MAX,
    "transmission_ramp_start_epoch": TRANSMISSION_RAMP_START_EPOCH,
    "transmission_ramp_end_epoch": TRANSMISSION_RAMP_END_EPOCH,
    "transmission_softmax_temperature_squared_distance": TRANSMISSION_SOFTMAX_TEMPERATURE,
    "transmission_validation_uses_full_weight": True,
    "hard_nearest_point_measurement_preserved": True,
    "raw_path_distance_in_optimized_objective": False,
    "teacher_relative_path_tolerance": PATH_TOLERANCE,
    "path_constraint_weight": PATH_CONSTRAINT_WEIGHT,
    "point_path_tolerance": POINT_PATH_TOLERANCE,
    "point_path_guard_weight": POINT_PATH_GUARD_WEIGHT,
    "soft_assignment_used_for_transmission_only": True,
    "soft_assignment_gradient_detached": True,
    "global_transmission_top_fraction": GLOBAL_TRANSMISSION_TOP_FRACTION,
    "scheduler_start_epoch": SCHEDULER_START_EPOCH,
    "scheduler_patience": SCHEDULER_PATIENCE,
    "scheduler_metric": "feasibility_aware_target_transmission_penalty_raw",
    "checkpoint_min_path_feasible_fraction": CHECKPOINT_MIN_PATH_FEASIBLE_FRACTION,
    "checkpoint_min_full_cycle_assembly": CHECKPOINT_MIN_FULL_CYCLE_ASSEMBLY,
    "checkpoint_min_target_feasible_fraction": CHECKPOINT_MIN_TARGET_FEASIBLE_FRACTION,
    "checkpoint_max_path_excess_mean": CHECKPOINT_MAX_PATH_EXCESS_MEAN,
    "checkpoint_max_point_excess_mean": CHECKPOINT_MAX_POINT_EXCESS_MEAN,
    "checkpoint_adjacency_delta": CHECKPOINT_ADJACENCY_DELTA,
    "checkpoint_grashof_delta": CHECKPOINT_GRASHOF_DELTA,
    "checkpoint_crank_delta": CHECKPOINT_CRANK_DELTA,
    "class_margin": CLASS_MARGIN,
    "class_margin_weight": CLASS_MARGIN_WEIGHT,
    "adaptive_constraint_growth": ADAPTIVE_CONSTRAINT_GROWTH,
    "adaptive_constraint_decay": ADAPTIVE_CONSTRAINT_DECAY,
    "adaptive_constraint_max": ADAPTIVE_CONSTRAINT_MAX,
    "adaptive_point_path_max": ADAPTIVE_POINT_PATH_MAX,
    "adaptive_update_interval": ADAPTIVE_UPDATE_INTERVAL,
    "multiplier_window_size": MULTIPLIER_WINDOW_SIZE,
    "multiplier_violation_trigger": MULTIPLIER_VIOLATION_TRIGGER,
    "multiplier_decay_feasible_streak": MULTIPLIER_DECAY_FEASIBLE_STREAK,
    "feasibility_recovery_patience": FEASIBILITY_RECOVERY_PATIENCE,
    "engineering_recovery_uses_material_failures": True,
    "recovery_material_mean_budget_excess": RECOVERY_MATERIAL_MEAN_BUDGET_EXCESS,
    "recovery_material_path_shortfall": RECOVERY_MATERIAL_PATH_SHORTFALL,
    "recovery_material_target_shortfall": RECOVERY_MATERIAL_TARGET_SHORTFALL,
    "recovery_material_path_excess_overage": (
        RECOVERY_MATERIAL_PATH_EXCESS_OVERAGE
    ),
    "recovery_material_point_excess_overage": (
        RECOVERY_MATERIAL_POINT_EXCESS_OVERAGE
    ),
    "engineering_recovery_resets_adam_moments": True,
    "max_min_lr_recoveries_without_improvement": (
        MAX_MIN_LR_RECOVERIES_WITHOUT_IMPROVEMENT
    ),
    "feasibility_recovery_window": FEASIBILITY_RECOVERY_WINDOW,
    "feasibility_recovery_lr_factor": FEASIBILITY_RECOVERY_LR_FACTOR,
    "feasibility_recovery_cooldown": FEASIBILITY_RECOVERY_COOLDOWN,
    "feasibility_recovery_has_independent_cooldown": True,
    "max_feasibility_recoveries": MAX_FEASIBILITY_RECOVERIES,
    "feasible_early_stop_patience": FEASIBLE_EARLY_STOP_PATIENCE,
    "min_epochs_before_feasible_early_stop": MIN_EPOCHS_BEFORE_FEASIBLE_EARLY_STOP,
    "teacher_model_source": teacher_model_source,
    "teacher_model_sha256": teacher_model_sha256,
    "teacher_source_variant": teacher_source_variant,
    "teacher_source_stored_loss": teacher_source_loss,
    "teacher_validation_baseline": teacher_validation_baseline,
    "initialization_mode": initialization_mode,
    "initialization_source": initialization_source,
    "initialization_source_variant": initialization_source_variant,
    "initialization_source_stored_loss": initialization_source_loss,
    "validation_targets_source": args.validation_targets_file,
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

# Initial state is also the exact teacher-relative baseline for this warm start.
save_checkpoint(
    INITIAL_STATE_PATH,
    state_epoch=0,
    completed_epoch=-1,
    train_loss=float("inf"),
    train_mean_distance=float("inf"),
    validation=initial_validation,
)
for initial_checkpoint in (BEST_PATH_CHECKPOINT, BEST_COMPOSITE_CHECKPOINT):
    save_checkpoint(
        initial_checkpoint,
        state_epoch=0,
        completed_epoch=-1,
        train_loss=float("inf"),
        train_mean_distance=float("inf"),
        validation=initial_validation,
    )
if bool(initial_validation.get("checkpoint_feasible", 0.0)):
    save_checkpoint(
        BEST_FEASIBLE_TRANSMISSION_CHECKPOINT,
        state_epoch=0,
        completed_epoch=-1,
        train_loss=float("inf"),
        train_mean_distance=float("inf"),
        validation=initial_validation,
    )
print(
    f"Initial fixed validation: composite={initial_validation['loss']:.6f}, "
    f"mean distance={initial_validation['mean_distance']:.6f}, "
    f"path feasible={initial_validation['path_mechanism_feasible_fraction']:.1%}, "
    f"full-cycle assembly={initial_validation['full_cycle_assembly_ratio']:.1%}, "
    f"target penalty={initial_validation['target_transmission_penalty_raw']:.6f}, "
    f"target min transmission={initial_validation['target_transmission_min_angle_deg']:.2f} deg"
)
log_constraint_state(0, "initial_state")

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
        last_val_metrics = annotate_validation_metrics(evaluate_fixed_validation())
        if prev_validation_stability_metric is None:
            prev_validation_stability_metric = last_val_metrics[
                "validation_stability_metric"
            ]
        best_validation_stability_metric = min(
            best_validation_stability_metric,
            last_val_metrics["validation_stability_metric"],
        )
    else:
        loaded, loaded_loss = load_checkpoint_c0(args.load_checkpoint)
        if not loaded:
            raise SystemExit(1)
        prev_epoch_loss = loaded_loss if np.isfinite(loaded_loss) else None
        last_val_metrics = annotate_validation_metrics(evaluate_fixed_validation())

# ======================
# ===== TRAINING LOOP =====
# ======================
for epoch in range(start_epoch, NUM_EPOCHS):
    epoch_start_time = time.time()
    bad_batch_logs_this_epoch = 0

    refresh_streaming_targets(epoch, reason="epoch_stream")

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
    (
        effective_target_transmission_weight,
        effective_global_transmission_weight,
        effective_transmission_ramp_fraction,
    ) = transmission_weights_for_epoch(epoch)
    epoch_loss = 0.0
    epoch_unclamped_loss = 0.0
    epoch_distance = 0.0
    num_batches = 0
    epoch_p1_dist = epoch_p2_dist = epoch_p3_dist = 0.0
    epoch_dist_loss = epoch_crank_short = epoch_grashof = 0.0
    epoch_adjacency = epoch_assembly = 0.0
    epoch_r2_components = {key: 0.0 for key in R21_EXTRA_COMPONENT_KEYS}
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
        teacher_batch_distances = compute_teacher_target_distances(
            batch_target_points, NUM_SIM_STEPS
        )
        loss, point_dists, loss_components = compute_mechanism_loss_batch(
            predicted_params,
            batch_target_points,
            target_transmission_weight=effective_target_transmission_weight,
            global_transmission_weight=effective_global_transmission_weight,
            teacher_target_distances=teacher_batch_distances,
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
            ENABLE_LOSS_CLAMP
            and prev_epoch_loss is not None
            and np.isfinite(prev_epoch_loss)
            and prev_epoch_loss > 1e-12
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
        for component_name in R21_EXTRA_COMPONENT_KEYS:
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
        print("[FATAL] R2.4 could not recover from a hard numerical failure.")
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
        last_val_metrics = annotate_validation_metrics(evaluate_fixed_validation())
    current_val_loss = last_val_metrics["loss"]
    current_val_distance = last_val_metrics["mean_distance"]
    current_transmission_metric = last_val_metrics["scheduler_metric"]
    current_validation_stability_metric = last_val_metrics[
        "validation_stability_metric"
    ]
    current_target_transmission_penalty = last_val_metrics[
        "target_transmission_penalty_raw"
    ]
    current_checkpoint_feasible = bool(
        last_val_metrics.get("checkpoint_feasible", 0.0)
    )
    current_state_epoch = epoch + 1
    last_completed_epoch = epoch

    avg_unclamped_loss = epoch_unclamped_loss / num_batches
    current_train_stability_metric = base_validation_stability_metric(avg_components)
    output_stats = finalize_output_stats(output_stats_accumulator)
    dead_gradient_epoch = grad_norm_max <= DEAD_GRADIENT_NORM_THRESHOLD
    if dead_gradient_epoch:
        consecutive_dead_gradient_epochs += 1
    else:
        consecutive_dead_gradient_epochs = 0

    if np.isfinite(best_validation_stability_metric):
        catastrophic_validation_threshold = max(
            best_validation_stability_metric * CATASTROPHIC_VALIDATION_FACTOR,
            best_validation_stability_metric + CATASTROPHIC_VALIDATION_ABS_DELTA,
        )
    else:
        catastrophic_validation_threshold = ABSOLUTE_PLATEAU_THRESHOLD
    catastrophic_validation = (
        np.isfinite(current_validation_stability_metric)
        and current_validation_stability_metric > catastrophic_validation_threshold
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
        "catastrophic_validation_metric": current_validation_stability_metric,
        "catastrophic_validation_threshold": catastrophic_validation_threshold,
        "dead_catastrophic_streak": consecutive_dead_catastrophic_epochs,
    })

    if current_validation_stability_metric < best_validation_stability_metric:
        best_validation_stability_metric = current_validation_stability_metric

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
    recent_transmission_metric_deque.append(current_transmission_metric)

    elapsed = time.time() - epoch_start_time
    print(
        f"Epoch {epoch + 1:4d}/{NUM_EPOCHS} | "
        f"TrainMeanDist: {avg_epoch_distance:.4f} | TrainLoss: {avg_epoch_loss:.6f} | "
        f"RawLoss: {avg_unclamped_loss:.6f} | "
        f"ValMeanDist: {current_val_distance:.4f} | ValComposite: {current_val_loss:.6f} | "
        f"ValBase: {current_validation_stability_metric:.6f} | "
        f"LR: {current_lr():.2e} | GradMax: {grad_norm_max:.3e} | "
        f"PathFeas T/V: {avg_components['path_mechanism_feasible_fraction']:.1%}/"
        f"{last_val_metrics['path_mechanism_feasible_fraction']:.1%} | "
        f"AsmFull T/V: {avg_components['full_cycle_assembly_ratio']:.1%}/"
        f"{last_val_metrics['full_cycle_assembly_ratio']:.1%} | "
        f"ValTxRaw: {current_target_transmission_penalty:.5f} | "
        f"ValMuTargetMin: {last_val_metrics['target_transmission_min_angle_deg']:.1f}deg | "
        f"SchedM: {current_transmission_metric:.5f} | "
        f"TxW: {effective_target_transmission_weight:.3f}/"
        f"{effective_global_transmission_weight:.3f} "
        f"({effective_transmission_ramp_fraction:.0%}) | "
        f"Clamp: {loss_clamped_batches / num_batches:.1%} | "
        f"Sat: {output_stats['output_saturated_fraction']:.1%} | Time: {elapsed:.2f}s"
    )

    # R2.4 retains hard-failure protection that bypasses cooldown and all ordinary plateau
    # logic. Two consecutive dead-gradient epochs are required, and fixed
    # validation must also be catastrophically worse than the best seen state.
    if consecutive_dead_catastrophic_epochs >= DEAD_GRADIENT_PATIENCE:
        event_label = "r1_1_dead_gradient_catastrophic_validation"
        print(
            f"[HARD FAILURE] GradMax <= {DEAD_GRADIENT_NORM_THRESHOLD:.1e} for "
            f"{consecutive_dead_catastrophic_epochs} catastrophic epochs; "
            f"BaseValMetric {current_validation_stability_metric:.6f} > threshold "
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
                f"adaptive_validation_loss={current_val_loss:.8f}; "
                f"base_validation_metric={current_validation_stability_metric:.8f}; "
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

    # Keep separate checkpoints because path accuracy, composite objective,
    # and feasible transmission quality are deliberately different goals.
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
            BEST_COMPOSITE_CHECKPOINT,
            state_epoch=epoch + 1,
            completed_epoch=epoch,
            train_loss=avg_epoch_loss,
            train_mean_distance=avg_epoch_distance,
            validation=last_val_metrics,
        )
        print(f"[INFO] Saved best composite checkpoint ({best_val_loss:.6f})")
    else:
        epochs_since_val_improvement += 1

    if current_val_distance < best_path_distance - EARLY_STOP_MIN_DELTA:
        best_path_distance = current_val_distance
        save_checkpoint(
            BEST_PATH_CHECKPOINT,
            state_epoch=epoch + 1,
            completed_epoch=epoch,
            train_loss=avg_epoch_loss,
            train_mean_distance=avg_epoch_distance,
            validation=last_val_metrics,
        )
        print(f"[INFO] Saved best path checkpoint ({best_path_distance:.6f})")

    primary_improved = False
    if current_checkpoint_feasible:
        better_penalty = (
            current_target_transmission_penalty
            < best_feasible_transmission_penalty - EARLY_STOP_MIN_DELTA
        )
        tied_penalty_better_angle = (
            abs(
                current_target_transmission_penalty
                - best_feasible_transmission_penalty
            ) <= EARLY_STOP_MIN_DELTA
            and last_val_metrics["target_transmission_min_angle_deg"]
            > best_feasible_transmission_angle + 1e-4
        )
        if better_penalty or tied_penalty_better_angle:
            best_feasible_transmission_penalty = current_target_transmission_penalty
            best_feasible_transmission_angle = last_val_metrics[
                "target_transmission_min_angle_deg"
            ]
            epochs_since_primary_improvement = 0
            min_lr_recoveries_without_primary_improvement = 0
            primary_improved = True
            save_checkpoint(
                BEST_FEASIBLE_TRANSMISSION_CHECKPOINT,
                state_epoch=epoch + 1,
                completed_epoch=epoch,
                train_loss=avg_epoch_loss,
                train_mean_distance=avg_epoch_distance,
                validation=last_val_metrics,
            )
            print(
                "[INFO] Saved best feasible-transmission checkpoint "
                f"(raw penalty={best_feasible_transmission_penalty:.6f}, "
                f"worst-target mean angle={best_feasible_transmission_angle:.3f} deg, "
                f"path feasible={last_val_metrics['path_mechanism_feasible_fraction']:.1%}, "
                f"target guard={last_val_metrics['path_target_feasible_fraction']:.1%}, "
                f"mean path delta={last_val_metrics['path_mean_degradation']:+.5f})"
            )
    if not primary_improved:
        epochs_since_primary_improvement += 1

    feasibility_recovery_cooldown_active = (
        epoch < feasibility_recovery_hold_until_epoch
    )
    current_violation_groups, _ = constraint_violation_groups(last_val_metrics)
    if feasibility_recovery_cooldown_active:
        # Do not let pre-recovery observations leak through the stabilization
        # window.  Recovery starts a genuinely fresh controller window.
        consecutive_infeasible_epochs = 0
        consecutive_feasible_epochs = 0
        clear_feasibility_windows()
    else:
        record_feasibility_observation(
            current_checkpoint_feasible,
            current_violation_groups,
            bool(last_val_metrics.get("engineering_recovery_material", 0.0)),
        )
        if current_checkpoint_feasible:
            consecutive_feasible_epochs += 1
            consecutive_infeasible_epochs = 0
        else:
            consecutive_infeasible_epochs += 1
            consecutive_feasible_epochs = 0

    event_label = ""
    window_observed, window_infeasible = feasibility_window_counts()
    material_observed, material_failures = material_recovery_window_counts()

    # Unlike numerical rollback, engineering recovery requires repeated
    # *material* deterioration inside a moving window. Minor gate misses feed
    # multiplier adaptation but do not rewind the model.
    if (
        not feasibility_recovery_cooldown_active
        and engineering_recovery_window_ready()
    ):
        at_min_lr = current_lr() <= MIN_LR * (1.0 + 1e-9)
        if (
            at_min_lr
            and min_lr_recoveries_without_primary_improvement
            >= MAX_MIN_LR_RECOVERIES_WITHOUT_IMPROVEMENT
        ):
            event_label = "engineering_recovery_min_lr_stalled"
            log_event(
                epoch + 1,
                event_label,
                val_loss_before=current_val_loss,
                lr_before=current_lr(),
                details=(
                    f"material_failures={material_failures}/{material_observed}; "
                    f"min_lr_recoveries_without_primary_improvement="
                    f"{min_lr_recoveries_without_primary_improvement}; "
                    f"best_feasible_penalty={best_feasible_transmission_penalty}"
                ),
            )
            log_epoch_metrics(
                epoch + 1, avg_epoch_loss, avg_epoch_distance,
                (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                avg_grad_norm, grad_norm_max, num_batches, elapsed,
                event=event_label,
                instrumentation=epoch_instrumentation,
            )
            print(
                "[EARLY STOP] Repeated engineering restores at the minimum LR "
                "did not improve the feasible frontier."
            )
            break
        if feasibility_recovery_count >= MAX_FEASIBILITY_RECOVERIES:
            event_label = "engineering_feasibility_recovery_limit"
            log_event(
                epoch + 1,
                event_label,
                val_loss_before=current_val_loss,
                lr_before=current_lr(),
                details=(
                    f"infeasible_streak={consecutive_infeasible_epochs}; "
                    f"window_infeasible={window_infeasible}/{window_observed}; "
                    f"material_failures={material_failures}/{material_observed}; "
                    f"recoveries={feasibility_recovery_count}; "
                    f"multipliers={json.dumps(multiplier_snapshot(), sort_keys=True)}"
                ),
            )
            log_epoch_metrics(
                epoch + 1, avg_epoch_loss, avg_epoch_distance,
                (avg_p1, avg_p2, avg_p3), avg_components, last_val_metrics,
                avg_grad_norm, grad_norm_max, num_batches, elapsed,
                event=event_label,
                instrumentation=epoch_instrumentation,
            )
            print(
                "[EARLY STOP] Engineering feasibility could not be maintained "
                f"after {feasibility_recovery_count} recoveries."
            )
            break
        failed_validation_metrics = dict(last_val_metrics)
        recovered = recover_engineering_feasibility(
            failed_validation_metrics,
            epoch,
            pre_train_loss=avg_epoch_loss,
            pre_val_loss=current_val_loss,
        )
        event_label = (
            "engineering_feasibility_recovery:recovered"
            if recovered
            else "engineering_feasibility_recovery:failed"
        )
        log_epoch_metrics(
            epoch + 1, avg_epoch_loss, avg_epoch_distance,
            (avg_p1, avg_p2, avg_p3), avg_components, failed_validation_metrics,
            avg_grad_norm, grad_norm_max, num_batches, elapsed,
            event=event_label,
            instrumentation=epoch_instrumentation,
        )
        if recovered:
            continue
        print("[FATAL] R2.4 could not restore engineering feasibility.")
        break

    # Only update ordinary multipliers when no engineering recovery is taking
    # place this epoch.  Recovery itself applies one growth step, so this
    # ordering prevents the R2.3 double-ratchet.
    if not feasibility_recovery_cooldown_active:
        if current_checkpoint_feasible:
            maybe_update_constraint_multipliers(
                last_val_metrics,
                epoch,
                allow_decay=True,
                reason="stable_feasibility_decay",
            )
        else:
            maybe_update_constraint_multipliers(
                last_val_metrics,
                epoch,
                allow_decay=False,
                reason="persistent_window_violation",
            )

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
        if epoch < scheduler_hold_until_epoch:
            stagnant_epoch_count = 0
        else:
            recent_tx_average = (
                sum(recent_transmission_metric_deque)
                / len(recent_transmission_metric_deque)
            )
            transmission_stagnant = current_transmission_metric >= recent_tx_average
            if transmission_stagnant:
                stagnant_epoch_count += 1
            else:
                stagnant_epoch_count = 0
            if stagnant_epoch_count >= PLATEAU_EPOCHS:
                if grace_counter > 0:
                    print(
                        f"[COOLDOWN] {grace_counter} epochs left; "
                        "transmission plateau notice suppressed"
                    )
                else:
                    print(
                        "[PLATEAU] Feasibility-aware transmission metric has "
                        "stagnated; no rollback. ReduceLROnPlateau remains the "
                        "LR authority."
                    )
                    log_event(
                        epoch + 1,
                        "transmission_plateau_no_rollback",
                        val_loss_before=current_val_loss,
                        lr_before=current_lr(),
                        details=(
                            f"scheduler_metric={current_transmission_metric:.8f}; "
                            f"target_penalty={current_target_transmission_penalty:.8f}; "
                            f"checkpoint_feasible={current_checkpoint_feasible}"
                        ),
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
        # Training metrics are sampled from a deliberately new target
        # distribution every epoch. A train-only jump is therefore diagnostic
        # and must never rewind the model. Fixed validation remains the stable
        # authority for numerical spike recovery.
        stream_train_metric_jump = (
            epoch >= SPIKE_MIN_EPOCH
            and prev_train_stability_metric is not None
            and np.isfinite(prev_train_stability_metric)
            and current_train_stability_metric
            > prev_train_stability_metric * SPIKE_THRESHOLD
        )
        validation_spike = (
            epoch >= SPIKE_MIN_EPOCH
            and prev_validation_stability_metric is not None
            and np.isfinite(prev_validation_stability_metric)
            and current_validation_stability_metric
            > prev_validation_stability_metric * VALIDATION_SPIKE_THRESHOLD
        )
        if stream_train_metric_jump:
            log_event(
                epoch + 1,
                "stream_train_metric_jump_no_rollback",
                train_loss_before=prev_epoch_loss,
                val_loss_before=prev_val_loss,
                checkpoint_train_loss=avg_epoch_loss,
                checkpoint_val_loss=current_val_loss,
                lr_before=current_lr(),
                details=(
                    f"base_train_before={prev_train_stability_metric}; "
                    f"base_train_after={current_train_stability_metric}; "
                    f"base_val_before={prev_validation_stability_metric}; "
                    f"base_val_after={current_validation_stability_metric}; "
                    f"stream_index={current_stream_index}; "
                    "training distribution changed by design"
                ),
            )
        if validation_spike:
            # Validation-spike protection remains immediate and bypasses all
            # ordinary cooldowns because the fixed set did not change.
            recovered = rollback_and_recover_r1(
                "validation_spike",
                pre_train_loss=avg_epoch_loss,
                pre_val_loss=current_val_loss,
                preferred_path=checkpoint_path,
            )
            event_label = (
                f"r1_validation_spike:{'recovered' if recovered else 'failed'}"
            )
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
    prev_train_stability_metric = current_train_stability_metric
    prev_validation_stability_metric = current_validation_stability_metric
    lr_before_scheduler = current_lr()
    if IS_R1:
        if epoch < scheduler_hold_until_epoch:
            if epoch == 0:
                log_event(
                    epoch + 1,
                    "scheduler_hold_started",
                    lr_before=current_lr(),
                    details=(
                        f"held through zero-based epoch {scheduler_hold_until_epoch - 1}; "
                        "objective ramp may proceed without LR starvation"
                    ),
                )
        else:
            if not scheduler_release_logged or epoch == scheduler_hold_until_epoch:
                scheduler_release_logged = True
                log_event(
                    epoch + 1,
                    "scheduler_released",
                    lr_before=current_lr(),
                    details=(
                        f"metric=feasibility_aware_target_transmission; "
                        f"patience={SCHEDULER_PATIENCE}"
                    ),
                )
                print(
                    f"[SCHEDULER] Released/released-after-recovery at epoch {epoch + 1}; monitoring "
                    "feasibility-aware target transmission penalty."
                )
            scheduler.step(current_transmission_metric)
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
            details=(
                f"scheduler_metric={current_transmission_metric:.8f}; "
                f"target_penalty={current_target_transmission_penalty:.8f}; "
                f"checkpoint_feasible={current_checkpoint_feasible}"
                if IS_R1 else ""
            ),
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

    stopping_counter = (
        epochs_since_primary_improvement if IS_R1 else epochs_since_improvement
    )
    feasible_stop_allowed = (
        (epoch + 1) >= MIN_EPOCHS_BEFORE_FEASIBLE_EARLY_STOP
        and epoch >= TRANSMISSION_RAMP_END_EPOCH
    )
    if stopping_counter >= EARLY_STOP_PATIENCE and (
        not IS_R1 or feasible_stop_allowed
    ):
        criterion = (
            "feasible target-transmission" if IS_R1 else "training loss"
        )
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
terminal_validation = annotate_validation_metrics(evaluate_fixed_validation())
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
    "constraint_multipliers": multiplier_snapshot(),
    "consecutive_infeasible_epochs": consecutive_infeasible_epochs,
    "consecutive_feasible_epochs": consecutive_feasible_epochs,
    "feasibility_recovery_count": feasibility_recovery_count,
    "feasibility_window": list(feasibility_window),
    "feasibility_window_infeasible": feasibility_window_counts()[1],
    "material_recovery_window": list(material_recovery_window),
    "material_recovery_window_failures": material_recovery_window_counts()[1],
    "current_stream_index": current_stream_index,
    "current_stream_seed": current_stream_seed,
    "streaming_unique_targets_seen": streaming_unique_targets_seen,
    "min_lr_recoveries_without_primary_improvement": (
        min_lr_recoveries_without_primary_improvement
    ),
    "constraint_violation_windows": {
        name: list(constraint_violation_windows[name]) for name in CONSTRAINT_GROUPS
    },
    "best_validation_stability_metric": best_validation_stability_metric,
    "prev_train_stability_metric": prev_train_stability_metric,
    "prev_validation_stability_metric": prev_validation_stability_metric,
    "scheduler_hold_until_epoch": scheduler_hold_until_epoch,
    "feasibility_recovery_hold_until_epoch": (
        feasibility_recovery_hold_until_epoch
    ),
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
    f"global min transmission={terminal_validation.get('transmission_min_angle_deg', float('nan')):.2f} deg | "
    f"target min transmission={terminal_validation.get('target_transmission_min_angle_deg', float('nan')):.2f} deg | "
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
        "evaluated_checkpoint_feasible": validation.get("checkpoint_feasible", float("nan")),
        "evaluated_scheduler_metric": validation.get("scheduler_metric", float("nan")),
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
    ("best_path_checkpoint", BEST_PATH_CHECKPOINT),
    ("best_composite_checkpoint", BEST_COMPOSITE_CHECKPOINT),
    ("best_feasible_transmission_checkpoint", BEST_FEASIBLE_TRANSMISSION_CHECKPOINT),
):
    metadata = inspect_checkpoint(checkpoint_candidate)
    if metadata is None:
        print(f"[STATE COMPARISON] {state_label}: checkpoint unavailable")
        continue
    state_loaded, _ = load_model_only(checkpoint_candidate)
    if not state_loaded:
        print(f"[STATE COMPARISON] {state_label}: load failed")
        continue
    state_validation = annotate_validation_metrics(evaluate_fixed_validation())
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

selected_best_path = BEST_FEASIBLE_TRANSMISSION_CHECKPOINT
if not selected_best_path.exists():
    selected_best_path = BEST_COMPOSITE_CHECKPOINT
if not selected_best_path.exists():
    selected_best_path = BEST_PATH_CHECKPOINT
if not selected_best_path.exists():
    selected_best_path = (
        BEST_TRAIN_CHECKPOINT
        if BEST_TRAIN_CHECKPOINT.exists()
        else TERMINAL_STATE_CHECKPOINT
    )

loaded, selected_train_loss = load_model_only(selected_best_path)
if loaded:
    final_validation = annotate_validation_metrics(evaluate_fixed_validation())
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
        "teacher_model_source": teacher_model_source,
        "teacher_model_sha256": teacher_model_sha256,
        "teacher_validation_baseline": teacher_validation_baseline,
    }, FINAL_MODEL_PATH)
    print(f"[INFO] Exported primary feasible-transmission model to {FINAL_MODEL_PATH}")
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
