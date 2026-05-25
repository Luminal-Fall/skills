import math
import pytest
import easing

ALL_FUNCTIONS = [
    easing.linear,
    easing.ease_in_quad,
    easing.ease_out_quad,
    easing.ease_in_out_quad,
    easing.ease_in_cubic,
    easing.ease_out_cubic,
    easing.ease_in_out_cubic,
    easing.ease_in_bounce,
    easing.ease_out_bounce,
    easing.ease_in_out_bounce,
    easing.ease_in_elastic,
    easing.ease_out_elastic,
    easing.ease_in_out_elastic,
    easing.ease_back_in,
    easing.ease_back_out,
    easing.ease_back_in_out,
]


class TestBoundaryValues:
    def test_all_return_zero_at_t_zero(self):
        for fn in ALL_FUNCTIONS:
            assert fn(0.0) == pytest.approx(0.0, abs=1e-9), (
                f"{fn.__name__}(0) = {fn(0.0)}, expected 0"
            )

    def test_all_return_one_at_t_one(self):
        for fn in ALL_FUNCTIONS:
            assert fn(1.0) == pytest.approx(1.0, abs=1e-9), (
                f"{fn.__name__}(1) = {fn(1.0)}, expected 1"
            )

    def test_linear_midpoint(self):
        assert easing.linear(0.5) == pytest.approx(0.5)

    def test_ease_in_quad_midpoint(self):
        assert easing.ease_in_quad(0.5) == pytest.approx(0.25)

    def test_ease_out_quad_midpoint(self):
        assert easing.ease_out_quad(0.5) == pytest.approx(0.75)

    def test_ease_in_cubic_midpoint(self):
        assert easing.ease_in_cubic(0.5) == pytest.approx(0.125)

    def test_ease_out_cubic_midpoint(self):
        assert easing.ease_out_cubic(0.5) == pytest.approx(0.875)


class TestElasticEdgeCases:
    def test_ease_in_elastic_at_zero_no_crash(self):
        # Guard branch: t == 0 → return 0 (avoids math.pow domain issues)
        assert easing.ease_in_elastic(0.0) == 0.0

    def test_ease_in_elastic_at_one_no_crash(self):
        assert easing.ease_in_elastic(1.0) == 1.0

    def test_ease_out_elastic_at_zero_no_crash(self):
        assert easing.ease_out_elastic(0.0) == 0.0

    def test_ease_out_elastic_at_one_no_crash(self):
        assert easing.ease_out_elastic(1.0) == 1.0

    def test_ease_in_out_elastic_at_zero_no_crash(self):
        assert easing.ease_in_out_elastic(0.0) == 0.0

    def test_ease_in_out_elastic_at_one_no_crash(self):
        assert easing.ease_in_out_elastic(1.0) == 1.0

    def test_elastic_midrange_returns_finite(self):
        for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
            assert math.isfinite(easing.ease_in_elastic(t))
            assert math.isfinite(easing.ease_out_elastic(t))
            assert math.isfinite(easing.ease_in_out_elastic(t))


class TestBounceContinuity:
    def test_ease_out_bounce_is_continuous_at_first_boundary(self):
        # At t = 1/2.75, both piecewise segments must agree
        t = 1 / 2.75
        segment1 = 7.5625 * t * t
        # Check the implementation matches segment1 value (boundary is non-inclusive for <)
        # Slightly below boundary uses first segment
        result_below = easing.ease_out_bounce(t - 1e-9)
        assert result_below == pytest.approx(segment1, abs=1e-4)

    def test_ease_out_bounce_is_continuous_at_second_boundary(self):
        t = 2 / 2.75
        result_below = easing.ease_out_bounce(t - 1e-9)
        result_above = easing.ease_out_bounce(t + 1e-9)
        assert result_below == pytest.approx(result_above, abs=1e-3)

    def test_ease_out_bounce_is_continuous_at_third_boundary(self):
        t = 2.5 / 2.75
        result_below = easing.ease_out_bounce(t - 1e-9)
        result_above = easing.ease_out_bounce(t + 1e-9)
        assert result_below == pytest.approx(result_above, abs=1e-3)

    def test_ease_in_out_bounce_is_symmetric_at_midpoint(self):
        # ease_in_out_bounce(0.5) should equal 0.5 for a symmetric function
        assert easing.ease_in_out_bounce(0.5) == pytest.approx(0.5, abs=0.01)


class TestGetEasing:
    def test_known_name_returns_correct_function(self):
        assert easing.get_easing("linear") is easing.linear

    def test_bounce_alias_returns_correct_function(self):
        assert easing.get_easing("bounce") is easing.ease_in_out_bounce

    def test_unknown_name_returns_linear(self):
        assert easing.get_easing("does_not_exist") is easing.linear

    def test_default_arg_returns_linear(self):
        assert easing.get_easing() is easing.linear

    def test_all_registered_names_are_callable(self):
        for name, fn in easing.EASING_FUNCTIONS.items():
            result = fn(0.5)
            assert isinstance(result, float), f"EASING_FUNCTIONS['{name}'](0.5) not float"


class TestInterpolate:
    def test_t_zero_returns_start(self):
        assert easing.interpolate(10, 90, 0.0, "linear") == pytest.approx(10.0)

    def test_t_one_returns_end(self):
        assert easing.interpolate(10, 90, 1.0, "linear") == pytest.approx(90.0)

    def test_linear_midpoint(self):
        assert easing.interpolate(0, 100, 0.5, "linear") == pytest.approx(50.0)

    def test_ease_in_quad_at_half(self):
        # ease_in_quad(0.5) = 0.25, so result = 0 + (100-0)*0.25 = 25
        assert easing.interpolate(0, 100, 0.5, "ease_in") == pytest.approx(25.0)

    def test_unknown_easing_falls_back_to_linear(self):
        assert easing.interpolate(0, 100, 0.5, "bogus") == pytest.approx(50.0)

    def test_negative_range(self):
        result = easing.interpolate(-100, 0, 0.5, "linear")
        assert result == pytest.approx(-50.0)


class TestApplySquashStretch:
    def test_vertical_compresses_height_expands_width(self):
        w, h = easing.apply_squash_stretch((1.0, 1.0), 1.0, direction="vertical")
        assert w == pytest.approx(1.5)
        assert h == pytest.approx(0.5)

    def test_horizontal_compresses_width_expands_height(self):
        w, h = easing.apply_squash_stretch((1.0, 1.0), 1.0, direction="horizontal")
        assert w == pytest.approx(0.5)
        assert h == pytest.approx(1.5)

    def test_both_compresses_both_dimensions(self):
        w, h = easing.apply_squash_stretch((1.0, 1.0), 1.0, direction="both")
        assert w == pytest.approx(0.7)
        assert h == pytest.approx(0.7)

    def test_zero_intensity_no_change(self):
        base = (2.0, 3.0)
        for direction in ("vertical", "horizontal", "both"):
            w, h = easing.apply_squash_stretch(base, 0.0, direction=direction)
            assert (w, h) == pytest.approx(base)

    def test_default_direction_is_vertical(self):
        w_vert, h_vert = easing.apply_squash_stretch((1.0, 1.0), 0.5, direction="vertical")
        w_def, h_def = easing.apply_squash_stretch((1.0, 1.0), 0.5)
        assert (w_def, h_def) == pytest.approx((w_vert, h_vert))


class TestCalculateArcMotion:
    def test_t_zero_returns_start(self):
        x, y = easing.calculate_arc_motion((0, 0), (100, 50), 20, 0.0)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)

    def test_t_one_returns_end(self):
        x, y = easing.calculate_arc_motion((0, 0), (100, 50), 20, 1.0)
        assert x == pytest.approx(100.0)
        assert y == pytest.approx(50.0)

    def test_arc_peaks_at_midpoint(self):
        # With start=(0,0) end=(100,0), height=10, y at t=0.5 should be -10
        # because arc_offset = 4*10*0.5*0.5 = 10 and y = 0 - 10 = -10
        x, y = easing.calculate_arc_motion((0, 0), (100, 0), 10, 0.5)
        assert x == pytest.approx(50.0)
        assert y == pytest.approx(-10.0)

    def test_arc_is_symmetric_around_midpoint(self):
        # For same start/end y, arc value at t and (1-t) should be equal
        start, end, height = (0, 0), (100, 0), 15
        for t in [0.1, 0.25, 0.4]:
            _, y1 = easing.calculate_arc_motion(start, end, height, t)
            _, y2 = easing.calculate_arc_motion(start, end, height, 1.0 - t)
            assert y1 == pytest.approx(y2)

    def test_zero_height_gives_linear_y(self):
        # With no arc, y should interpolate linearly between start and end
        x, y = easing.calculate_arc_motion((0, 10), (100, 50), 0, 0.5)
        assert y == pytest.approx(30.0)
