import math

import pytest

from mechanism_generator.omts import geometry

# Grashof four-bar used for hand-checked geometry: O2=(0,0), O4=(4,0).
P1 = [4.0, 1.0, 3.5, 2.5, 0.5, 0.0, 0.0, 0.0, 0.0]
NEAR_ORIGIN = {"shape": "circle", "center": [0.1, 0.0], "radius": 0.045}


def test_skeleton_matches_hand_computed_positions():
    skeleton = geometry.four_bar_skeleton(P1, 1, 0.0)
    assert skeleton is not None
    assert skeleton["o2"] == (0.0, 0.0)
    assert skeleton["o4"] == pytest.approx((4.0, 0.0))
    assert skeleton["a"] == pytest.approx((1.0, 0.0))
    # circle intersection: b is 2.5 from O4 and 3.5 from A, branch +1 side
    assert skeleton["b"] == pytest.approx((3.5, -math.sqrt(6.0)))
    assert skeleton["p"] == pytest.approx((2.25, -math.sqrt(6.0) / 2.0))
    mirrored = geometry.four_bar_skeleton(P1, -1, 0.0)
    assert mirrored["b"] == pytest.approx((3.5, math.sqrt(6.0)))


def test_skeleton_undefined_assembly_is_none_not_an_error():
    # crank tip meets the far pivot exactly: circle centers coincide
    degenerate = [2.0, 2.0, 3.5, 2.5, 0.5, 0.0, 0.0, 0.0, 0.0]
    assert geometry.four_bar_skeleton(degenerate, 1, 0.0) is None
    # A is 5 from O4 but the dyad reaches only 4
    out_of_reach = [4.0, 1.0, 2.0, 2.0, 0.5, 0.0, 0.0, 0.0, 0.0]
    assert geometry.four_bar_skeleton(out_of_reach, 1, 180.0) is None


def test_carrier_corners_use_coupler_frame():
    skeleton = geometry.four_bar_skeleton(P1, 1, 0.0, carrier=(2.0, 1.0))
    assert skeleton is not None
    corners = skeleton["carrier_corners"]
    assert len(corners) == 4
    # first corner: p + width/2 along A->B + depth/2 perpendicular
    expected = (2.25 + 1.0 * (2.5 / 3.5) + 0.5 * (math.sqrt(6.0) / 3.5),
                -math.sqrt(6.0) / 2.0 - 1.0 * (math.sqrt(6.0) / 3.5) + 0.5 * (2.5 / 3.5))
    assert corners[0] == pytest.approx(expected)
    assert geometry.four_bar_skeleton(P1, 1, 0.0)["carrier_corners"] == ()


def test_occupies_detects_crank_pass():
    assert geometry.occupies(P1, 1, NEAR_ORIGIN, 0.0) is True


def test_occupies_clear_when_bodies_stay_away():
    # theta 90: crank passes 0.1 from the region center, just outside radius
    # 0.045; coupler and rocker stay farther (hand-checked distances).
    assert geometry.occupies(P1, 1, NEAR_ORIGIN, 90.0) is False


def test_thickness_expands_occupancy():
    # crank distance to the circle center is 0.1; 0.045 + 0.06 reaches it.
    assert geometry.occupies(P1, 1, NEAR_ORIGIN, 90.0, thickness=0.06) is True
    assert geometry.occupies(P1, 1, NEAR_ORIGIN, 90.0, thickness=0.05) is False


def test_carrier_rectangle_occupies_regions():
    corner = geometry.four_bar_skeleton(P1, 1, 0.0, carrier=(2.0, 1.0))["carrier_corners"][0]
    region = {"shape": "circle", "center": corner, "radius": 0.05}
    assert geometry.occupies(P1, 1, region, 0.0, carrier=(2.0, 1.0)) is True
    # without the carrier the links stay 0.5 from that corner (hand-checked)
    assert geometry.occupies(P1, 1, region, 0.0) is False


def test_region_inside_carrier_is_occupied():
    # bar_length 1 lifts the coupler point 1.0 off every link centerline
    p2 = [4.0, 1.0, 3.5, 2.5, 0.5, 1.0, 0.0, 0.0, 0.0]
    carrier = (4.0, 3.0)
    skeleton = geometry.four_bar_skeleton(p2, 1, 0.0, carrier=carrier)
    inside = {"shape": "circle", "center": skeleton["p"], "radius": 0.05}
    assert geometry.occupies(p2, 1, inside, 0.0, carrier=carrier) is True
    assert geometry.occupies(p2, 1, inside, 0.0) is False


def test_occupancy_never_guesses_undefined_assembly():
    out_of_reach = [4.0, 1.0, 2.0, 2.0, 0.5, 0.0, 0.0, 0.0, 0.0]
    big = {"shape": "box", "min": [-10.0, -10.0], "max": [10.0, 10.0]}
    with pytest.raises(ValueError, match="undefined"):
        geometry.occupies(out_of_reach, 1, big, 180.0)


def test_windows_from_flags_wraps_through_zero():
    flags = [True] * 3 + [False] * 6 + [True] * 3
    assert geometry.windows_from_flags(flags) == [
        {"start_deg": 270.0, "end_deg": 60.0}]


def test_windows_from_flags_keeps_separate_runs():
    flags = [False, True, True, False, False, True, False]
    windows = geometry.windows_from_flags(flags)
    assert windows[0]["start_deg"] == pytest.approx(360.0 / 7.0)
    assert windows[0]["end_deg"] == pytest.approx(720.0 / 7.0)
    assert windows[1] == {"start_deg": pytest.approx(360.0 * 5 / 7.0),
                          "end_deg": pytest.approx(360.0 * 5 / 7.0)}


def test_windows_from_flags_full_cycle_and_empty():
    assert geometry.windows_from_flags([True] * 4) == [
        {"start_deg": 0.0, "end_deg": 270.0}]
    assert geometry.windows_from_flags([False] * 4) == []


def test_occupancy_windows_full_cycle():
    big = {"shape": "box", "min": [-10.0, -10.0], "max": [10.0, 10.0]}
    assert geometry.occupancy_windows(P1, 1, big, 720) == [
        {"start_deg": 0.0, "end_deg": 359.5}]


def test_occupancy_windows_empty_when_unreachable():
    far = {"shape": "box", "min": [9.0, 9.0], "max": [10.0, 10.0]}
    assert geometry.occupancy_windows(P1, 1, far, 720) == []


def test_occupancy_windows_validates_steps():
    big = {"shape": "box", "min": [-10.0, -10.0], "max": [10.0, 10.0]}
    for bad in (0, 360, 72002, True, 12.5):
        with pytest.raises(ValueError, match="step"):
            geometry.occupancy_windows(P1, 1, big, bad)


def test_region_validation_is_fail_closed():
    bad_regions = [
        {"shape": "blob"},
        {"shape": "box", "min": [0.0, 0.0], "max": [-1.0, 1.0]},
        {"shape": "box", "min": [0.0, 0.0], "max": [1.0]},
        {"shape": "circle", "center": [0.0, 0.0], "radius": 0.0},
        {"shape": "circle", "center": [0.0], "radius": 1.0},
    ]
    for region in bad_regions:
        with pytest.raises(ValueError):
            geometry.occupies(P1, 1, region, 0.0)


def test_parameter_and_branch_validation():
    for bad in ([1.0, 2.0], P1 + [1.0],
                [-4.0, 1.0, 3.5, 2.5, 0.5, 0.0, 0.0, 0.0, 0.0]):
        with pytest.raises(ValueError):
            geometry.four_bar_skeleton(bad, 1, 0.0)
    with pytest.raises(ValueError):
        geometry.four_bar_skeleton(P1, 0, 0.0)


def test_negative_thickness_rejected():
    with pytest.raises(ValueError, match="[Tt]hickness"):
        geometry.occupies(P1, 1, NEAR_ORIGIN, 0.0, thickness=-0.1)


def test_panel_screen_parity_on_envelope():
    np = pytest.importorskip("numpy")
    from types import SimpleNamespace

    from mechanism_generator.engine import panel

    args = SimpleNamespace(panel_bounds=[-100.0, 100.0, -100.0, 100.0],
                           carrier_size=[2.0, 1.0],
                           panel_pivot_clearance=0.0, panel_steps=721)
    config = panel.configuration(args)
    result = panel.screen(np.asarray(P1, dtype=float), 1, config)
    assert result["panel_geometry_valid"] is True

    xs, ys = [], []
    for index in range(config["steps"]):
        # panel samples linspace(0, 2*pi, steps), endpoint inclusive
        theta_deg = 360.0 * index / (config["steps"] - 1)
        skeleton = geometry.four_bar_skeleton(P1, 1, theta_deg, carrier=(2.0, 1.0))
        assert skeleton is not None
        for point in (skeleton["o2"], skeleton["o4"], skeleton["a"], skeleton["b"],
                      *skeleton["carrier_corners"]):
            xs.append(point[0])
            ys.append(point[1])
    assert min(xs) == pytest.approx(result["panel_envelope_x_min"], abs=1e-6)
    assert max(xs) == pytest.approx(result["panel_envelope_x_max"], abs=1e-6)
    assert min(ys) == pytest.approx(result["panel_envelope_y_min"], abs=1e-6)
    assert max(ys) == pytest.approx(result["panel_envelope_y_max"], abs=1e-6)
