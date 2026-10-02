"""Panel-position dyads: free coupler angles, no requested orientations.
Adapted from pose_seeds; bounded geometric search with whole-cycle screening.
"""
from __future__ import annotations

import math
import time

import numpy as np

from . import panel

METHOD = "panel_position_free_angle_dyad_v1"
MAX_SAMPLES = 262144


def _radical_inverse(count, base):
    values = np.arange(1, count + 1)
    result = np.zeros(count, dtype=float)
    factor = 1. / base
    while np.any(values):
        result += (values % base) * factor
        values //= base
        factor /= base
    return result


def _circumcenter(points):
    """Stable relative-coordinate circumcenters for [sample, three, xy]."""
    q = points[:, 1] - points[:, 0]
    r = points[:, 2] - points[:, 0]
    det = 2 * (q[:, 0] * r[:, 1] - q[:, 1] * r[:, 0])
    defined = np.abs(det) > 1e-10
    safe_det = np.where(defined, det, 1.)
    q2, r2 = (q * q).sum(axis=1), (r * r).sum(axis=1)
    relative = np.column_stack(((q2 * r[:, 1] - r2 * q[:, 1]) / safe_det,
                                (q[:, 0] * r2 - r[:, 0] * q2) / safe_det))
    center = points[:, 0] + relative
    radius = np.linalg.norm(relative, axis=1)
    return center, radius, defined


def generate(points, args, *, sample_count=65536, max_seeds=6):
    """Sample free tool-frame angles and geometry; screen whole-cycle panel fit."""
    if args.ground_link_mode != 'optimize' or args.phase_mode != 'unordered' or getattr(args, 'target_orientations_deg', None) is not None:
        raise ValueError('Panel-position initialization requires adjustable ground and unordered position-only targets.')
    if panel.configuration(args) is None:
        raise ValueError('Panel-position initialization requires an explicit panel and carrier.')
    started = time.perf_counter()
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or not 0 <= sample_count <= MAX_SAMPLES:
        raise ValueError(f"Pose dyad sample count must be an integer from 0 to {MAX_SAMPLES}.")
    if isinstance(max_seeds, bool) or not isinstance(max_seeds, int) or not 0 <= max_seeds <= 6:
        raise ValueError("Pose dyad seed count must be an integer between 0 and 6.")
    samples, count = sample_count, max_seeds
    counters = {
        "method": METHOD, "enabled": bool(samples and count),
        "requested_samples": samples, "requested_seed_count": count,
        "attempted_samples": 0, "finite_dyads": 0, "within_search_bounds": 0,
        "full_cycle_robust_crank_shortest": 0, "branch_and_order_consistent": 0,
        "transmission_selection_floors": 0, "returned_seeds": 0,
    }
    panel_config = panel.configuration(args)
    if panel_config:
        counters.update(panel_pivot_pass_count=0, panel_screened_count=0, panel_passing_count=0)
    if not counters["enabled"]:
        counters["generation_runtime_seconds"] = time.perf_counter() - started
        return [], counters
    world = np.asarray(points, dtype=float)
    if world.shape != (3, 2) or not np.isfinite(world).all():
        raise ValueError('Three finite XY positions are required.')
    scale = max(float(np.linalg.norm(world[:, None] - world[None, :], axis=-1).max()), args.minimum_target_scale)
    if not math.isfinite(scale):
        raise ValueError("Pose target span exceeds the numerical range.")
    centroid = world.mean(axis=0)
    points = (world - centroid) / scale
    # Independent free orientations are search variables, not task constraints.
    angles = 2*np.pi*np.column_stack([_radical_inverse(samples, base) for base in (7, 11, 13)])
    direction = np.stack((np.cos(angles), np.sin(angles)), axis=-1)
    normal = np.stack((-np.sin(angles), np.cos(angles)), axis=-1)
    u = np.column_stack([_radical_inverse(samples, base) for base in (2, 3, 5)])
    moving_min = max(.001 / scale, args.moving_link_min_ratio)
    moving_max = max(moving_min + 1e-6 / scale, args.moving_link_max_ratio)
    l3 = moving_min + u[:, 0] * (moving_max - moving_min)
    s = .01 + .98 * u[:, 1]
    min_bar = .1 / scale
    max_bar = max(min_bar + 1e-6 / scale, args.bar_length_max_ratio)
    bar = min_bar + u[:, 2] * (max_bar - min_bar)
    a = points[None] - (s * l3)[:, None, None] * direction - bar[:, None, None] * normal
    b = a + l3[:, None, None] * direction
    o2, l2, ok_a = _circumcenter(a)
    o4, l4, ok_b = _circumcenter(b)
    ground = o4 - o2
    l1 = np.linalg.norm(ground, axis=1)
    base_angle = np.arctan2(ground[:, 1], ground[:, 0])
    phases = (np.arctan2(a[:, :, 1] - o2[:, None, 1], a[:, :, 0] - o2[:, None, 0]) - base_angle[:, None]) % (2 * np.pi)
    delta_a = a - o4[:, None]
    delta_b = b - o4[:, None]
    crosses = delta_a[:, :, 0] * delta_b[:, :, 1] - delta_a[:, :, 1] * delta_b[:, :, 0]
    signs = np.sign(crosses)
    direction_sign = -1 if getattr(args, "crank_direction", "positive") == "negative" else 1
    gaps = (direction_sign * (np.roll(phases, -1, axis=1) - phases)) % (2 * np.pi)
    links = np.column_stack((l1, l2, l3, l4))
    sorted_links = np.sort(links, axis=1)
    grashof_margin = sorted_links[:, 1] + sorted_links[:, 2] - sorted_links[:, 0] - sorted_links[:, 3]
    crank_margin = np.minimum.reduce((l1 - l2, l3 - l2, l4 - l2))
    near, far = np.abs(l1 - l2), l1 + l2
    assembly_margin = np.minimum.reduce((l3 + l4 - far, near - np.abs(l3 - l4), near))
    with np.errstate(divide='ignore', invalid='ignore'):
        target_cosine = (l3[:, None]**2 + l4[:, None]**2 - (delta_a**2).sum(axis=2)) / (2*l3*l4)[:, None]
        target_tx = np.degrees(np.arccos(np.clip(np.abs(target_cosine), 0, 1))).min(axis=1)
        global_cosine = (l3[:, None]**2 + l4[:, None]**2 - np.column_stack((near, far))**2) / (2*l3*l4)[:, None]
        global_tx = np.degrees(np.arccos(np.clip(np.abs(global_cosine), 0, 1))).min(axis=1)
    counters['attempted_samples'] = samples
    mask = ok_a & ok_b & np.isfinite(links).all(axis=1)
    counters['finite_dyads'] = int(mask.sum())
    ground_min = max(.001 / scale, args.ground_link_min_ratio)
    ground_max = max(ground_min + 1e-6 / scale, args.ground_link_max_ratio)
    mask &= ((l1 > ground_min) & (l1 < ground_max)
             & (links[:, 1:] > moving_min).all(axis=1) & (links[:, 1:] < moving_max).all(axis=1)
             & (np.abs(o2) < args.base_search_radius_ratio).all(axis=1))
    counters['within_search_bounds'] = int(mask.sum())
    mask &= ((assembly_margin >= args.assembly_margin_ratio)
             & (grashof_margin >= args.grashof_margin_ratio)
             & (crank_margin >= max(args.class_margin / scale, args.class_margin_ratio)))
    if args.enforce_follower_not_longest:
        mask &= (np.maximum(l1, l3) - l4 >= max(args.class_margin / scale, args.class_margin_ratio))
    counters['full_cycle_robust_crank_shortest'] = int(mask.sum())
    mask &= ((signs != 0).all(axis=1) & (signs == signs[:, :1]).all(axis=1))
    if args.branches == 'negative':
        mask &= signs[:, 0] < 0
    elif args.branches == 'positive':
        mask &= signs[:, 0] > 0
    if args.phase_mode == 'ordered':
        mask &= np.abs(gaps.sum(axis=1) - 2*np.pi) < 1e-7
        mask &= gaps.min(axis=1) >= math.radians(.25)
    counters['branch_and_order_consistent'] = int(mask.sum())
    mask &= (target_tx >= args.minimum_target_transmission) & (global_tx >= args.minimum_global_transmission)
    counters['transmission_selection_floors'] = int(mask.sum())
    parameters = np.column_stack((links*scale, s, bar*scale, o2*scale + centroid, base_angle))
    if panel_config:
        mask &= panel.pivot_clearances(parameters, panel_config) >= panel_config["pivot_clearance"]
        counters["panel_pivot_pass_count"] = int(mask.sum())
    indices = np.flatnonzero(mask)
    # Prefer the requested transmission goals, then transmission margin and size.
    preferred = (target_tx >= args.target_transmission_deg) & (global_tx >= args.global_transmission_floor_deg)
    ranking = sorted(indices, key=lambda i: (not preferred[i], -min(target_tx[i], global_tx[i]), links[i].sum(), i))
    selected = []
    features = np.column_stack((links, s, bar, o2))
    for index in ranking:
        if panel_config:
            counters["panel_screened_count"] += 1
            if not panel.screen(parameters[index], int(signs[index, 0]), panel_config)["panel_acceptable"]:
                continue
            counters["panel_passing_count"] += 1
        if all(np.linalg.norm(features[index] - features[other]) > .1 for other in selected):
            selected.append(index)
        if len(selected) >= count:
            break
    result = [{'sample_index': int(i + 1), 'proposal_source': counters['method'], 'parameters': parameters[i].tolist(), 'phases_rad': phases[i].tolist(),
               'branch_sign': int(signs[i, 0]), 'target_transmission_deg': float(target_tx[i]),
               'global_transmission_deg': float(global_tx[i])} for i in selected]
    counters['returned_seeds'] = len(result)
    counters['generation_runtime_seconds'] = time.perf_counter() - started
    return result, counters
