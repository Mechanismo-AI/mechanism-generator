"""Z2: engine-side zone screening configuration, parity, and qualification."""

import argparse
import json

import pytest

pytest.importorskip("numpy")

from mechanism_generator.engine import zone_screen
from mechanism_generator.omts.geometry import occupancy_summary, occupancy_windows

STEPS = 361
PARAMS = (4.0, 1.0, 2.5, 2.5, 0.5, 0.5, 0.0, 0.0, 0.0)  # Grashof crank-rocker
BOX = {"id": "shared_zone", "shape": "box", "min": [0.5, -0.5], "max": [1.5, 0.5]}
FAR_CIRCLE = {"id": "approach", "shape": "circle", "center": [100.0, 100.0], "radius": 0.01}
EVERYWHERE = {"id": "everywhere", "shape": "box", "min": [-10.0, -10.0], "max": [10.0, 10.0]}


def _sidecar(tmp_path, screen, regions, steps=STEPS, thickness=0.0, carrier=None, name="zone"):
    document = {
        "method": zone_screen.METHOD,
        "task": "gate",
        "steps": steps,
        "thickness": thickness,
        "regions": regions,
        "screen": screen,
        "disclaimer": "sampled, never certified",
    }
    if carrier is not None:
        document["carrier"] = {"width": carrier[0], "depth": carrier[1]}
    path = tmp_path / f"zone_screen_{name}.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def _config(tmp_path, screen, regions, **kwargs):
    sidecar = _sidecar(tmp_path, screen, regions, **kwargs)
    return zone_screen.configuration(argparse.Namespace(zone_screen=sidecar))


def _kernel_windows(region, steps=STEPS, thickness=0.0, carrier=None):
    return occupancy_windows(list(PARAMS), 1, region, steps,
                             thickness=thickness, carrier=carrier)


def test_configuration_absent_when_flag_missing():
    assert zone_screen.configuration(argparse.Namespace(zone_screen=None)) is None


def test_configuration_rejects_bad_steps(tmp_path):
    with pytest.raises(ValueError, match="step count"):
        _config(tmp_path, [{"region": "shared_zone", "avoid": True}], [BOX], steps=360)


def test_configuration_rejects_unknown_region(tmp_path):
    with pytest.raises(ValueError, match="unknown region"):
        _config(tmp_path, [{"region": "ghost", "avoid": True}], [BOX])


def test_configuration_rejects_entry_without_criterion(tmp_path):
    with pytest.raises(ValueError, match="at least one criterion"):
        _config(tmp_path, [{"region": "shared_zone", "mode": "hard"}], [BOX])


def test_configuration_rejects_non_number_width(tmp_path):
    with pytest.raises(ValueError, match="within"):
        _config(tmp_path, [{"region": "shared_zone", "max_total_width_deg": {"time": 5}}], [BOX])


def test_configuration_rejects_width_above_360(tmp_path):
    with pytest.raises(ValueError, match="within"):
        _config(tmp_path, [{"region": "shared_zone", "max_total_width_deg": 361}], [BOX])


def test_parity_with_stdlib_kernel_box(tmp_path):
    config = _config(tmp_path, [{"region": "shared_zone", "mode": "report_only", "avoid": False}], [BOX])
    result = zone_screen.screen(PARAMS, 1, config)
    kernel = _kernel_windows({"shape": "box", "min": [0.5, -0.5], "max": [1.5, 0.5]})
    assert result["zone_screen_geometry_valid"] is True
    assert result["zone_screen_shared_zone_windows"] == len(kernel)
    assert result["zone_screen_shared_zone_total_width_deg"] == pytest.approx(
        occupancy_summary(kernel, STEPS)["total_width_deg"])
    engine_windows = sorted(zip(
        result["zone_screen_shared_zone_window_starts_deg"],
        result["zone_screen_shared_zone_window_ends_deg"]))
    kernel_windows = sorted((w["start_deg"], w["end_deg"]) for w in kernel)
    assert engine_windows == pytest.approx(kernel_windows)


def test_parity_with_stdlib_kernel_circle_thickness_carrier(tmp_path):
    regions = [{"id": "coupler_zone", "shape": "circle", "center": [1.4, 0.9], "radius": 0.35}]
    carrier = (0.6, 0.4)
    config = _config(tmp_path, [{"region": "coupler_zone", "mode": "report_only", "avoid": False}],
                     regions, thickness=0.05, carrier=carrier)
    result = zone_screen.screen(PARAMS, 1, config)
    kernel = _kernel_windows(
        {"shape": "circle", "center": [1.4, 0.9], "radius": 0.35},
        thickness=0.05, carrier=carrier)
    assert result["zone_screen_coupler_zone_windows"] == len(kernel)
    assert result["zone_screen_coupler_zone_total_width_deg"] == pytest.approx(
        occupancy_summary(kernel, STEPS)["total_width_deg"])


def test_full_occupancy_is_one_window_of_exactly_360(tmp_path):
    config = _config(tmp_path, [{"region": "everywhere", "avoid": True, "mode": "hard"}], [EVERYWHERE])
    result = zone_screen.screen(PARAMS, 1, config)
    assert result["zone_screen_everywhere_windows"] == 1
    assert result["zone_screen_everywhere_total_width_deg"] == pytest.approx(360.0)
    assert result["zone_screen_everywhere_acceptable"] is False
    assert result["zone_screen_acceptable"] is False


def test_avoid_passes_when_never_occupied(tmp_path):
    config = _config(tmp_path, [{"region": "approach", "avoid": True, "mode": "hard"}], [FAR_CIRCLE])
    result = zone_screen.screen(PARAMS, 1, config)
    assert result["zone_screen_approach_windows"] == 0
    assert result["zone_screen_approach_acceptable"] is True
    assert result["zone_screen_acceptable"] is True


def test_soft_failure_stays_acceptable_but_recorded(tmp_path):
    config = _config(tmp_path, [{"region": "everywhere", "avoid": True, "mode": "soft"}], [EVERYWHERE])
    result = zone_screen.screen(PARAMS, 1, config)
    assert result["zone_screen_everywhere_acceptable"] is False
    assert result["zone_screen_acceptable"] is True


def test_hard_failure_excludes_but_soft_region_records(tmp_path):
    config = _config(tmp_path, [
        {"region": "everywhere", "avoid": True, "mode": "hard"},
        {"region": "approach", "avoid": True, "mode": "soft"},
    ], [EVERYWHERE, FAR_CIRCLE])
    result = zone_screen.screen(PARAMS, 1, config)
    assert result["zone_screen_acceptable"] is False
    assert result["zone_screen_approach_acceptable"] is True


def test_max_windows_criterion(tmp_path):
    far = _config(tmp_path, [{"region": "approach", "max_windows": 0, "mode": "hard"}], [FAR_CIRCLE])
    assert zone_screen.screen(PARAMS, 1, far)["zone_screen_acceptable"] is True
    everywhere = _config(tmp_path, [{"region": "everywhere", "max_windows": 0, "mode": "hard"}], [EVERYWHERE])
    result = zone_screen.screen(PARAMS, 1, everywhere)
    assert result["zone_screen_everywhere_windows"] == 1
    assert result["zone_screen_acceptable"] is False


def test_max_total_width_criterion(tmp_path):
    config = _config(tmp_path, [{"region": "shared_zone", "max_total_width_deg": 1.0, "mode": "hard"}], [BOX])
    result = zone_screen.screen(PARAMS, 1, config)
    assert result["zone_screen_acceptable"] is (
        result["zone_screen_shared_zone_total_width_deg"] <= 1.0)


def test_undefined_assembly_fails_closed(tmp_path):
    config = _config(tmp_path, [{"region": "shared_zone", "avoid": True, "mode": "hard"}], [BOX])
    result = zone_screen.screen((10.0, 1.0, 2.0, 2.0, 0.5, 0.5, 0.0, 0.0, 0.0), 1, config)
    assert result["zone_screen_geometry_valid"] is False
    assert result["zone_screen_acceptable"] is False
    assert "zone_screen_shared_zone_windows" not in result


def test_invalid_parameters_fail_closed(tmp_path):
    config = _config(tmp_path, [{"region": "shared_zone", "avoid": True, "mode": "hard"}], [BOX])
    bad = [
        (1.0, 1.0, 1.0),  # wrong shape
        (4.0, 1.0, 2.5, 2.5, 0.5, 0.5, float("nan"), 0.0, 0.0),
        (4.0, 0.0, 2.5, 2.5, 0.5, 0.5, 0.0, 0.0, 0.0),  # non-positive link
    ]
    for parameters in bad:
        result = zone_screen.screen(parameters, 1, config)
        assert result["zone_screen_acceptable"] is False
        assert result["zone_screen_geometry_valid"] is False
    assert zone_screen.screen(PARAMS, 2, config)["zone_screen_acceptable"] is False


def _qualification_args(zone_screen_flag):
    return argparse.Namespace(
        max_mean_error=0.05,
        max_point_error=0.075,
        shared_mean_allowance=0.02,
        shared_point_allowance=0.05,
        target_transmission_deg=35.0,
        global_transmission_floor_deg=15.0,
        minimum_target_transmission=15.0,
        minimum_global_transmission=10.0,
        assembly_margin_ratio=0.0,
        grashof_margin_ratio=0.0,
        class_margin_ratio=0.0,
        class_margin=0.0,
        enforce_follower_not_longest=False,
        engineering_max_link_ratio=0.0,
        engineering_max_sweep_radius_ratio=0.0,
        ground_link_mode="portfolio",
        target_orientations_deg=None,
        zone_screen=zone_screen_flag,
    )


def _candidate(candidate_id, zone_screen_acceptable):
    return {
        "candidate_id": candidate_id,
        "model_role": "path",
        "profile": "accuracy",
        "branch_sign": 1,
        "physical_feasible": True,
        "mean_error": 0.01,
        "error_1": 0.01,
        "error_2": 0.01,
        "error_3": 0.01,
        # 20 deg passes the selection floors (15/10) but not the engineering
        # transmission goal (35), so the zone screen is the only selection gate.
        "target_angle_min_deg": 20.0,
        "global_angle_min_deg": 20.0,
        "assembly_margin_ratio": 1.0,
        "grashof_margin_ratio": 1.0,
        "crank_margin_ratio": 1.0,
        "follower_margin_ratio": 1.0,
        "target_scale": 1.0,
        "max_link_ratio": 1.0,
        "sweep_radius_ratio": 1.0,
        "zone_screen_acceptable": zone_screen_acceptable,
    }


def test_qualification_excludes_hard_screen_failures():
    pytest.importorskip("torch")
    pytest.importorskip("matplotlib")
    pytest.importorskip("pandas")
    from mechanism_generator.engine import r25b
    failing = _candidate("failing", False)
    passing = _candidate("passing", True)
    args = _qualification_args("zone_screen.json")
    qualification = r25b.apply_shared_candidate_qualification([failing, passing], args)
    assert failing["selection_eligible"] is False
    assert failing["qualification_level"] == "path_acceptable_but_zone_screen_failed"
    assert passing["selection_eligible"] is True
    assert passing["qualification_level"] == "selection_acceptable"
    assert qualification["selection_eligible_count"] == 1
    unscreened_fail = _candidate("uns1", False)
    unscreened_pass = _candidate("uns2", True)
    r25b.apply_shared_candidate_qualification([unscreened_fail, unscreened_pass], _qualification_args(None))
    assert unscreened_fail["selection_eligible"] is True
    assert unscreened_pass["selection_eligible"] is True
