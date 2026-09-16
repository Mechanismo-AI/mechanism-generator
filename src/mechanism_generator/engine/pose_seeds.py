"""Three-pose initialization by circumcenters of moving-frame points.

For a chosen coupler length L, fraction s, and offset h, the moving joints have
local tool-frame coordinates A=(-sL,-h), B=((1-s)L,-h). Applying the three
requested rigid transforms gives three positions of each joint. Their respective
circumcenters are fixed pivots O2 and O4, so their radii define an exact pair of
revolute dyads. No reference mechanism or trained model is used.

This is the classical three-position rigid-body guidance construction; see
https://egyankosh.ac.in/bitstream/123456789/31867/1/Unit-7.pdf (section 7.4).
The bounded, deterministic sampling and screening below select candidates within
the packaged engine's parameterization and kinematic qualification constraints.
"""
from __future__ import annotations

import math
import time

import numpy as np

METHOD = "three_pose_dyad_v1"


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


def generate_pose_seeds(points, orientations, args, *, sample_count=4096, max_seeds=6):
    """Construct up to six diverse exact seeds from the requested poses alone.

    ``args`` supplies the existing engine's bounds, ordering, branch selection,
    and qualification thresholds. No model, witness geometry, random state, or
    optimized candidate is an input. Repeated/collinear dyads are rejected and
    can produce an empty result; the regular search remains available.
    """
    started = time.perf_counter()
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 0:
        raise ValueError("Pose dyad sample count must be a non-negative integer.")
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
    if not counters["enabled"]:
        counters["generation_runtime_seconds"] = time.perf_counter() - started
        return [], counters
    world = np.asarray(points, dtype=float)
    orientations = np.asarray(orientations, dtype=float)
    if world.shape != (3, 2) or orientations.shape != (3,):
        raise ValueError("Pose initialization requires three XY positions and three orientations.")
    if not np.isfinite(world).all() or not np.isfinite(orientations).all():
        raise ValueError("Pose initialization inputs must be finite.")
    scale = max(float(np.linalg.norm(world[:, None] - world[None, :], axis=-1).max()), args.minimum_target_scale)
    if not math.isfinite(scale):
        raise ValueError("Pose target span exceeds the numerical range.")
    centroid = world.mean(axis=0)
    points = (world - centroid) / scale
    angles = np.radians(np.remainder(orientations, 360.))
    direction = np.column_stack((np.cos(angles), np.sin(angles)))
    normal = np.column_stack((-np.sin(angles), np.cos(angles)))
    u = np.column_stack([_radical_inverse(samples, base) for base in (2, 3, 5)])
    moving_min = max(.001 / scale, args.moving_link_min_ratio)
    moving_max = max(moving_min + 1e-6 / scale, args.moving_link_max_ratio)
    l3 = moving_min + u[:, 0] * (moving_max - moving_min)
    s = .01 + .98 * u[:, 1]
    min_bar = .1 / scale
    max_bar = max(min_bar + 1e-6 / scale, args.bar_length_max_ratio)
    bar = min_bar + u[:, 2] * (max_bar - min_bar)
    a = points[None] - (s * l3)[:, None, None] * direction[None] - bar[:, None, None] * normal[None]
    b = a + l3[:, None, None] * direction[None]
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
    indices = np.flatnonzero(mask)
    parameters = np.column_stack((links*scale, s, bar*scale, o2*scale + centroid, base_angle))
    # Prefer the requested transmission goals, then transmission margin and size.
    preferred = (target_tx >= args.target_transmission_deg) & (global_tx >= args.global_transmission_floor_deg)
    ranking = sorted(indices, key=lambda i: (not preferred[i], -min(target_tx[i], global_tx[i]), links[i].sum(), i))
    selected = []
    features = np.column_stack((links, s, bar, o2))
    for index in ranking:
        if all(np.linalg.norm(features[index] - features[other]) > .1 for other in selected):
            selected.append(index)
        if len(selected) >= count:
            break
    result = [{'sample_index': int(i + 1), 'parameters': parameters[i].tolist(), 'phases_rad': phases[i].tolist(),
               'branch_sign': int(signs[i, 0]), 'target_transmission_deg': float(target_tx[i]),
               'global_transmission_deg': float(global_tx[i])} for i in selected]
    counters['returned_seeds'] = len(result)
    counters['generation_runtime_seconds'] = time.perf_counter() - started
    return result, counters

