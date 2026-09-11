"""
Automatic aggregation over repeated measurements, with confidence bands.

The seaborn.lineplot() equivalent: raw repeated-measures data in, estimate
per x plus an interval out, with no manual groupby first. Statistics are
checked against hand-computed values rather than only for plausibility.
"""

import numpy as np
import pytest

from glyphx import Figure
from glyphx.aggregate import aggregate

# x=1 holds 10/20/30 (mean 20, sd 10), x=2 holds 40/50/60 (mean 50, sd 10).
XS = [1, 1, 1, 2, 2, 2]
YS = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------

def test_mean_is_the_default_estimator():
    keys, centre, _, _ = aggregate(XS, YS, ci=None)
    assert keys == [1, 2]
    assert centre == [20.0, 50.0]


@pytest.mark.parametrize("name, expected", [
    ("mean", [20.0, 50.0]),
    ("median", [20.0, 50.0]),
    ("sum", [60.0, 150.0]),
    ("min", [10.0, 40.0]),
    ("max", [30.0, 60.0]),
    ("count", [3.0, 3.0]),
])
def test_named_estimators(name, expected):
    _, centre, _, _ = aggregate(XS, YS, estimator=name, ci=None)
    assert centre == expected


def test_a_callable_estimator_is_accepted():
    _, centre, _, _ = aggregate(XS, YS, estimator=lambda v: float(np.ptp(v)),
                                ci=None)
    assert centre == [20.0, 20.0]


def test_unknown_estimator_names_the_alternatives():
    with pytest.raises(ValueError, match="Unknown estimator"):
        aggregate(XS, YS, estimator="geometric_mean")


# ---------------------------------------------------------------------------
# Intervals, against hand-computed values
# ---------------------------------------------------------------------------

def test_sd_interval_is_one_standard_deviation():
    """sd of [10, 20, 30] with ddof=1 is exactly 10."""
    _, centre, lower, upper = aggregate(XS, YS, ci="sd")
    assert (lower[0], centre[0], upper[0]) == (10.0, 20.0, 30.0)


def test_se_interval_is_the_standard_error():
    """se = 10 / sqrt(3) = 5.7735."""
    _, _, lower, upper = aggregate(XS, YS, ci="se")
    assert lower[0] == pytest.approx(20.0 - 10 / np.sqrt(3), abs=1e-3)
    assert upper[0] == pytest.approx(20.0 + 10 / np.sqrt(3), abs=1e-3)


def test_n_std_scales_the_interval():
    _, _, lower, upper = aggregate(XS, YS, ci="sd", n_std=2.0)
    assert (lower[0], upper[0]) == (0.0, 40.0)


def test_bootstrap_interval_brackets_the_estimate():
    _, centre, lower, upper = aggregate(XS, YS, ci=95, n_boot=2000)
    for lo, mid, hi in zip(lower, centre, upper):
        assert lo <= mid <= hi


def test_a_wider_interval_is_wider():
    _, _, lo95, hi95 = aggregate(XS, YS, ci=95, n_boot=2000)
    _, _, lo50, hi50 = aggregate(XS, YS, ci=50, n_boot=2000)
    assert (hi95[0] - lo95[0]) > (hi50[0] - lo50[0])


def test_ci_none_returns_no_interval():
    keys, centre, lower, upper = aggregate(XS, YS, ci=None)
    assert lower is None and upper is None


def test_a_single_observation_gets_no_fabricated_width():
    """One value has no spread to resample; inventing an interval would
    imply a precision the data does not have."""
    _, centre, lower, upper = aggregate([1, 2], [5.0, 7.0], ci=95)
    assert lower == centre == upper


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

def test_the_same_data_gives_the_same_band():
    """A band that shifted on every render would make figures
    irreproducible, which matters most for the papers this is aimed at."""
    first = aggregate(XS, YS, ci=95)
    second = aggregate(XS, YS, ci=95)
    assert first == second


def test_a_different_seed_gives_a_different_band():
    """
    Needs a realistic group size: three observations have only ten distinct
    resamples, so every seed lands on the same percentile and the test would
    fail on the data rather than on the behaviour.
    """
    rng = np.random.default_rng(0)
    xs = [1] * 40 + [2] * 40
    ys = list(rng.normal(20, 5, 40)) + list(rng.normal(50, 5, 40))
    assert aggregate(xs, ys, ci=95, seed=1)[2] != aggregate(xs, ys, ci=95, seed=2)[2]


# ---------------------------------------------------------------------------
# Ordering and validation
# ---------------------------------------------------------------------------

def test_numeric_x_is_sorted_numerically():
    keys, _, _, _ = aggregate([10, 2, 33, 2], [1.0, 2.0, 3.0, 4.0], ci=None)
    assert keys == [2, 10, 33]


def test_categorical_x_keeps_first_seen_order():
    """Alphabetising would scramble Mon/Tue/Wed."""
    keys, _, _, _ = aggregate(["Mon", "Tue", "Wed", "Mon"],
                              [1.0, 2.0, 3.0, 3.0], ci=None)
    assert keys == ["Mon", "Tue", "Wed"]


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError, match="same length"):
        aggregate([1, 2, 3], [1.0, 2.0])


@pytest.mark.parametrize("bad", [0, 100, -5, 150])
def test_out_of_range_ci_is_rejected(bad):
    with pytest.raises(ValueError, match="between 0 and 100"):
        aggregate(XS, YS, ci=bad)


def test_unknown_ci_string_is_rejected():
    with pytest.raises(ValueError, match="not recognised"):
        aggregate(XS, YS, ci="stderr")


# ---------------------------------------------------------------------------
# Figure.aggregate_line
# ---------------------------------------------------------------------------

@pytest.fixture
def frame():
    pd = pytest.importorskip("pandas")
    rng = np.random.default_rng(3)
    rows = [{"week": w, "score": 50 + s * w + rng.normal(0, 7), "arm": arm}
            for arm, s in (("Treatment", 5.0), ("Control", 1.5))
            for w in range(6) for _ in range(10)]
    return pd.DataFrame(rows)


def test_aggregate_line_draws_a_band_and_a_line(frame):
    fig = Figure(auto_display=False)
    fig.aggregate_line(frame, x="week", y="score")
    kinds = [type(s).__name__ for s in fig.axes.series]
    assert kinds == ["FillBetweenSeries", "LineSeries"]


def test_band_is_drawn_before_the_line(frame):
    """Otherwise the band covers the line it belongs to."""
    fig = Figure(auto_display=False)
    fig.aggregate_line(frame, x="week", y="score")
    assert type(fig.axes.series[0]).__name__ == "FillBetweenSeries"


def test_hue_splits_into_one_line_and_band_per_group(frame):
    fig = Figure(auto_display=False)
    fig.aggregate_line(frame, x="week", y="score", hue="arm")
    assert len(fig.axes.series) == 4
    labels = [s.label for s in fig.axes.series if s.label]
    assert set(labels) == {"Treatment", "Control"}


def test_each_band_matches_its_own_line_colour(frame):
    """
    Left to the theme, band and line take consecutive palette slots
    independently, so a group's band came out a different colour from its
    line.
    """
    fig = Figure(auto_display=False)
    fig.aggregate_line(frame, x="week", y="score", hue="arm")
    fig.render_svg()
    series = fig.axes.series
    assert series[0].color == series[1].color
    assert series[2].color == series[3].color
    assert series[0].color != series[2].color


def test_ci_none_draws_only_the_line(frame):
    fig = Figure(auto_display=False)
    fig.aggregate_line(frame, x="week", y="score", ci=None)
    assert [type(s).__name__ for s in fig.axes.series] == ["LineSeries"]


def test_works_without_a_dataframe():
    fig = Figure(auto_display=False)
    fig.aggregate_line(x=XS, y=YS, label="scores")
    assert fig.axes.series[1].label == "scores"


def test_label_defaults_to_the_y_column(frame):
    fig = Figure(auto_display=False)
    fig.aggregate_line(frame, x="week", y="score")
    assert fig.axes.series[1].label == "score"


def test_dataframe_without_columns_is_rejected(frame):
    with pytest.raises(ValueError, match="column names"):
        Figure(auto_display=False).aggregate_line(frame)


def test_aggregate_line_chains(frame):
    fig = Figure(auto_display=False)
    assert fig.aggregate_line(frame, x="week", y="score") is fig


def test_the_result_renders(frame):
    fig = Figure(auto_display=False, title="Recovery")
    fig.aggregate_line(frame, x="week", y="score", hue="arm")
    assert fig.render_svg().lstrip().startswith("<svg")
