"""Sampled full-turn containment of link centrelines and an attached carrier.

The rectangular carrier is centred on P, with its width axis along A to B.
This is a kinematic screen, not a collision, thickness or continuous-envelope
certificate. All distances use the same world units as the target positions.
"""
from __future__ import annotations

import numpy as np

METHOD = "sampled_full_cycle_panel_v1"


def configuration(args):
    bounds = getattr(args, "panel_bounds", None)
    size = getattr(args, "carrier_size", None)
    clearance = getattr(args, "panel_pivot_clearance", 0.)
    steps = getattr(args, "panel_steps", 7201)
    if bounds is None and size is None:
        if clearance != 0 or steps != 7201:
            raise ValueError("Panel clearance and sampling settings require panel bounds and carrier size.")
        return None
    if bounds is None or size is None:
        raise ValueError("Panel bounds and carrier size must be supplied together.")
    if len(bounds) != 4 or len(size) != 2 or not np.isfinite([*bounds, *size, clearance]).all():
        raise ValueError("Panel geometry must have finite bounds, carrier size and clearance.")
    xmin, xmax, ymin, ymax = bounds
    if xmin >= xmax or ymin >= ymax or min(size) <= 0 or clearance < 0:
        raise ValueError("Panel bounds must increase, carrier dimensions must be positive and clearance non-negative.")
    if 2 * clearance >= min(xmax - xmin, ymax - ymin):
        raise ValueError("Fixed-pivot clearance leaves no usable panel interior.")
    if isinstance(steps, bool) or not isinstance(steps, int) or not 361 <= steps <= 72001:
        raise ValueError("Panel sampling requires an integer from 361 to 72001 phases.")
    return dict(method=METHOD, bounds=list(bounds), carrier_size=list(size),
                pivot_clearance=clearance, steps=steps, carrier_frame="coupler_A_to_B")


def pivot_clearances(parameters, config):
    """Vectorized minimum edge clearance of both fixed pivots."""
    p = np.asarray(parameters, dtype=float)
    o2 = p[..., 6:8]
    o4 = o2 + p[..., 0, None] * np.stack((np.cos(p[..., 8]), np.sin(p[..., 8])), axis=-1)
    pivots = np.stack((o2, o4), axis=-2)
    xmin, xmax, ymin, ymax = config["bounds"]
    low, high = np.array([xmin, ymin]), np.array([xmax, ymax])
    return np.minimum(pivots - low, high - pivots).min(axis=(-2, -1))


def screen(parameters, branch_sign, config):
    """Fail closed on undefined assembly; otherwise return a sampled envelope."""
    result = dict(panel_required=True, panel_acceptable=False, panel_method=METHOD,
                  panel_steps=config["steps"], panel_geometry_valid=False,
                  panel_x_min=config["bounds"][0], panel_x_max=config["bounds"][1],
                  panel_y_min=config["bounds"][2], panel_y_max=config["bounds"][3],
                  carrier_width=config["carrier_size"][0], carrier_height=config["carrier_size"][1],
                  panel_pivot_clearance_required=config["pivot_clearance"])
    p = np.asarray(parameters, dtype=float)
    if p.shape != (9,) or not np.isfinite(p).all() or np.any(p[:4] <= 0) or branch_sign not in (-1, 1):
        return result
    l1, l2, l3, l4, s, bar, bx, by, base = p
    theta = np.linspace(0., 2 * np.pi, config["steps"])
    o2 = np.array([bx, by])
    o4 = o2 + l1 * np.array([np.cos(base), np.sin(base)])
    a = o2 + l2 * np.column_stack((np.cos(theta + base), np.sin(theta + base)))
    delta = a - o4
    distance = np.linalg.norm(delta, axis=1)
    if (distance <= 0).any() or (distance > l3 + l4).any() or (distance < abs(l3 - l4)).any():
        return result
    unit = delta / distance[:, None]
    along = (l4 * l4 - l3 * l3 + distance * distance) / (2 * distance)
    height = np.sqrt(np.maximum(0., l4 * l4 - along * along))
    b = o4 + along[:, None] * unit + branch_sign * height[:, None] * np.column_stack((-unit[:, 1], unit[:, 0]))
    u = (b - a) / l3
    v = np.column_stack((-u[:, 1], u[:, 0]))
    center = a + s * (b - a) + bar * v
    width, depth = config["carrier_size"]
    # A rectangle is convex: endpoints bound each zero-thickness link segment.
    corners = [center + x * u + y * v for x in (-width / 2, width / 2) for y in (-depth / 2, depth / 2)]
    outline = np.vstack((o2, o4, a, b, *corners))
    if not np.isfinite(outline).all():
        return result
    low, high = outline.min(axis=0), outline.max(axis=0)
    xmin, xmax, ymin, ymax = config["bounds"]
    edge = float(min(low[0] - xmin, xmax - high[0], low[1] - ymin, ymax - high[1]))
    pivot = float(pivot_clearances(p, config))
    result.update(panel_geometry_valid=True, panel_edge_clearance=edge, panel_pivot_clearance=pivot,
                  panel_envelope_x_min=float(low[0]), panel_envelope_x_max=float(high[0]),
                  panel_envelope_y_min=float(low[1]), panel_envelope_y_max=float(high[1]),
                  panel_acceptable=bool(edge >= 0 and pivot >= config["pivot_clearance"]))
    return result
