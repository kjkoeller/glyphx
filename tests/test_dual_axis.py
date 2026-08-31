"""
Secondary Y axis: right-hand label, tick alignment with the left axis, and
log-scale handling for zero-anchored series.
"""

import re

import pytest

from glyphx import BarSeries, Figure, HistogramSeries, LineSeries


def _dual(**kw):
    fig = Figure(auto_display=False, **kw)
    fig.add(LineSeries([1, 2, 3, 4], [10.0, 25.0, 18.0, 40.0], label="L"))
    fig.add(BarSeries([1, 2, 3, 4], [100.0, 220.0, 180.0, 410.0], label="R"),
            use_y2=True)
    return fig


def _tick_rows(fig):
    """Pixel rows of the left and right tick labels, from the rendered SVG."""
    ax = fig.axes
    y1_vals = ax._yticks or [
        ax._y_domain[0] + i * (ax._y_domain[1] - ax._y_domain[0]) / 5
        for i in range(6)
    ]
    lo, hi = ax._y_domain
    span = (hi - lo) or 1.0
    y2_vals = [
        ax._y2_domain[0] + ((v - lo) / span) * (ax._y2_domain[1] - ax._y2_domain[0])
        for v in y1_vals
    ]
    return ([round(ax.scale_y(v), 4) for v in y1_vals],
            [round(ax.scale_y2(v), 4) for v in y2_vals])


# ---------------------------------------------------------------------------
# Tick alignment
# ---------------------------------------------------------------------------

def test_ticks_align_with_default_tick_counts():
    fig = _dual()
    fig.render_svg()
    left, right = _tick_rows(fig)
    assert left == right


def test_ticks_align_when_y1_has_custom_tick_positions():
    """
    The two axes used to generate ticks independently. That happened to line
    up at the default five, then drifted apart as soon as set_yticks() gave
    Y1 a different count, interleaving two sets of gridlines.
    """
    fig = _dual()
    fig.axes.set_yticks([10, 20, 30, 40])
    fig.render_svg()
    left, right = _tick_rows(fig)
    assert len(left) == 4
    assert left == right


def test_right_axis_draws_one_label_per_left_tick():
    fig = _dual()
    fig.axes.set_yticks([10, 20, 30, 40])
    svg = fig.render_svg()
    right_labels = re.findall(r'text-anchor="start"[^>]*opacity="0.85"', svg)
    assert len(right_labels) == 4


def test_tick_formatter_reaches_the_secondary_axis():
    """set_tick_format applied to X and Y1 but not Y2."""
    fig = _dual()
    fig.set_tick_format(lambda v: f"${v:,.0f}")
    svg = fig.render_svg()
    right = re.findall(r'opacity="0\.85">([^<]*)</text>', svg)
    assert right and all("$" in label for label in right)


# ---------------------------------------------------------------------------
# Secondary axis label
# ---------------------------------------------------------------------------

def test_set_y2label_renders_rotated_on_the_right():
    fig = _dual(width=800)
    fig.set_y2label("Volume")
    svg = fig.render_svg()
    assert "Volume" in svg
    # Anchored to the axes width, not the canvas width: the label belongs at
    # the edge of the plot area, inside the legend gutter.
    expected_x = fig.axes.width - 15
    assert f'transform="rotate(90, {expected_x}, ' in svg


def test_y2label_is_a_no_op_without_secondary_series():
    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.set_y2label("Nothing here")
    assert "Nothing here" not in fig.render_svg()


def test_y2label_is_escaped():
    fig = _dual()
    fig.set_y2label("Volume & Flow")
    assert "Volume &amp; Flow" in fig.render_svg()


def test_set_y2label_chains():
    fig = _dual()
    assert fig.set_ylabel("Price").set_y2label("Volume") is fig


# ---------------------------------------------------------------------------
# Log scale with zero-anchored series
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("series", [
    BarSeries([1, 2, 3], [10.0, 100.0, 1000.0]),
    HistogramSeries([1.0, 2.0, 2.0, 3.0, 3.0, 3.0]),
])
def test_zero_anchored_series_render_on_a_log_y_axis(series):
    """
    Bars measure from zero, so the domain was forced to include 0 -- and
    log10(0) raised ValueError, meaning every bar chart on a log Y axis
    crashed instead of rendering.
    """
    fig = Figure(auto_display=False, yscale="log")
    fig.add(series)
    assert fig.render_svg().lstrip().startswith("<svg")
    assert fig.axes._y_domain[0] > 0


def test_zero_anchored_series_render_on_a_log_secondary_axis():
    fig = Figure(auto_display=False, yscale="log")
    fig.add(LineSeries([1, 2, 3], [10.0, 100.0, 1000.0]))
    fig.add(BarSeries([1, 2, 3], [5.0, 50.0, 500.0]), use_y2=True)
    assert fig.render_svg().lstrip().startswith("<svg")
    assert fig.axes._y2_domain[0] > 0


def test_bars_are_still_zero_anchored_on_a_linear_axis():
    """The log guard must not change ordinary bar charts."""
    fig = Figure(auto_display=False)
    fig.add(BarSeries([1, 2, 3], [10.0, 20.0, 30.0]))
    fig.render_svg()
    assert fig.axes._y_domain[0] == 0
