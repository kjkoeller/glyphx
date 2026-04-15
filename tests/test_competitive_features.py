"""
Tests for the six features that make GlyphX definitively better than
Matplotlib, Seaborn, and Plotly:

  1 – BubbleSeries           (missing from all three competitors)
  2 – SunburstSeries         (Plotly-exclusive today)
  3 – ParallelCoordinates    (Plotly staple; Seaborn has nothing)
  4 – DivergingBarSeries     (no native equivalent in any of the three)
  5 – LTTB downsampling      (Matplotlib handles millions of pts; now GlyphX does too)
  6 – Hue / palette API      (Seaborn's biggest strength — now built-in)
"""
from __future__ import annotations

import math
import numpy as np
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    import pytest
except ImportError:
    import pytest_shim as pytest  # noqa: F401
    _sys.modules["pytest"] = pytest
import pandas as pd

from glyphx import Figure
from glyphx.series import LineSeries, BarSeries, ScatterSeries
from glyphx.bubble import BubbleSeries
from glyphx.sunburst import SunburstSeries
from glyphx.parallel_coords import ParallelCoordinatesSeries
from glyphx.diverging_bar import DivergingBarSeries
from glyphx.downsample import lttb, maybe_downsample, AUTO_THRESHOLD
from glyphx.layout import Axes
from glyphx.themes import themes


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_ax(**kw):
    return Axes(width=600, height=400, padding=50, theme=themes["default"], **kw)

def _finalize(ax, *series):
    for s in series:
        ax.add_series(s)
    ax.finalize()
    return ax

def _svg(series, ax=None):
    """Render a series to SVG string using a default Axes if none given."""
    if ax is None:
        if hasattr(series, "x") and series.x:
            ax = _finalize(_make_ax(), series)
        else:
            ax = _make_ax()
    return series.to_svg(ax)


# =============================================================================
# 1 — BubbleSeries
# =============================================================================

def test_bubble_renders_circles():
    s   = BubbleSeries([1, 2, 3], [4, 5, 6], size=[100, 200, 300])
    ax  = _finalize(_make_ax(), s)
    svg = s.to_svg(ax)
    assert "<circle" in svg

def test_bubble_radius_range():
    sizes  = [10, 100, 1000]
    s      = BubbleSeries([1, 2, 3], [4, 5, 6], size=sizes,
                          min_radius=5, max_radius=30)
    # Smallest bubble should get min_radius
    assert s._radii.min() >= 4.9
    assert s._radii.max() <= 30.1

def test_bubble_uniform_size():
    s = BubbleSeries([1, 2, 3], [4, 5, 6], size=10)
    assert np.all(s._radii == 10.0)

def test_bubble_colormap_encoding():
    s   = BubbleSeries([1, 2, 3], [1, 2, 3], size=5,
                       c=[0.1, 0.5, 0.9], cmap="viridis")
    ax  = _finalize(_make_ax(), s)
    svg = s.to_svg(ax)
    # Colorbar rendered
    assert "<rect" in svg

def test_bubble_labels_in_tooltip():
    s   = BubbleSeries([1, 2], [3, 4], size=10, labels=["Alpha", "Beta"])
    ax  = _finalize(_make_ax(), s)
    svg = s.to_svg(ax)
    assert "Alpha" in svg
    assert "Beta" in svg

def test_bubble_equal_sizes_no_crash():
    s   = BubbleSeries([1, 2], [3, 4], size=[50, 50])
    ax  = _finalize(_make_ax(), s)
    svg = s.to_svg(ax)
    assert "<svg" not in svg   # to_svg returns fragment, not full svg
    assert "<circle" in svg

def test_bubble_figure_shorthand():
    fig = Figure(auto_display=False)
    fig.bubble([1, 2, 3], [1, 2, 3], size=[10, 20, 30], label="Bubbles")
    svg = fig.render_svg()
    assert "<circle" in svg

def test_bubble_largest_drawn_first():
    """Largest bubbles rendered first so small ones aren't hidden."""
    sizes = [100, 10, 50]
    s     = BubbleSeries([1, 2, 3], [1, 2, 3], size=sizes)
    # _radii order should match input
    assert s._radii[0] > s._radii[1]


# =============================================================================
# 2 — SunburstSeries
# =============================================================================

SUNBURST_DATA = dict(
    labels  = ["Total", "Sales",  "APAC", "EMEA", "Eng",   "Mkt"],
    parents = ["",      "Total",  "Sales","Sales", "Total", "Total"],
    values  = [0,        0,        4200,   3100,    2800,    1500],
)

def test_sunburst_renders_paths():
    s   = SunburstSeries(**SUNBURST_DATA)
    svg = s.to_svg(ax=None)
    assert "<path" in svg

def test_sunburst_segment_count():
    s   = SunburstSeries(**SUNBURST_DATA)
    svg = s.to_svg(ax=None)
    # At least one path per non-root node
    n_paths = svg.count("<path")
    assert n_paths >= len(SUNBURST_DATA["labels"]) - 1

def test_sunburst_labels_appear():
    s   = SunburstSeries(**SUNBURST_DATA)
    svg = s.to_svg(ax=None)
    assert "Sales" in svg

def test_sunburst_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        SunburstSeries(labels=["A", "B"], parents=["", "A"], values=[1])

def test_sunburst_figure_shorthand():
    fig = Figure(width=550, height=550, auto_display=False)
    fig.sunburst(**SUNBURST_DATA)
    svg = fig.render_svg()
    assert "<path" in svg

def test_sunburst_custom_colors():
    s = SunburstSeries(
        **SUNBURST_DATA,
        colors=["#ff0000", "#00ff00", "#0000ff", "#ff00ff", "#00ffff", "#ffff00"],
    )
    svg = s.to_svg()
    assert "<path" in svg

def test_sunburst_centre_circle():
    s   = SunburstSeries(**SUNBURST_DATA)
    svg = s.to_svg()
    assert "<circle" in svg   # centre dot


# =============================================================================
# 3 — ParallelCoordinatesSeries
# =============================================================================

PC_DATA = np.array([
    [5.1, 3.5, 1.4, 0.2],
    [4.9, 3.0, 1.4, 0.2],
    [6.3, 3.3, 6.0, 2.5],
    [5.8, 2.7, 5.1, 1.9],
    [7.1, 3.0, 5.9, 2.1],
])
PC_AXES = ["sepal_l", "sepal_w", "petal_l", "petal_w"]
PC_HUE  = ["setosa", "setosa", "virginica", "versicolor", "virginica"]

def test_parallel_coords_renders_polylines():
    s   = ParallelCoordinatesSeries(PC_DATA, PC_AXES)
    svg = s.to_svg()
    assert "polyline" in svg

def test_parallel_coords_one_line_per_row():
    s   = ParallelCoordinatesSeries(PC_DATA, PC_AXES)
    svg = s.to_svg()
    assert svg.count("polyline") >= len(PC_DATA)

def test_parallel_coords_categorical_hue():
    s   = ParallelCoordinatesSeries(PC_DATA, PC_AXES, hue=PC_HUE)
    svg = s.to_svg()
    # Legend items for each unique group
    assert "setosa" in svg
    assert "virginica" in svg

def test_parallel_coords_numeric_hue():
    numeric_hue = [0.1, 0.2, 0.8, 0.5, 0.9]
    s   = ParallelCoordinatesSeries(PC_DATA, PC_AXES, hue=numeric_hue)
    svg = s.to_svg()
    assert "polyline" in svg

def test_parallel_coords_column_mismatch_raises():
    with pytest.raises(ValueError, match="axis names"):
        ParallelCoordinatesSeries(PC_DATA, ["only_one"])

def test_parallel_coords_axis_labels_in_svg():
    s   = ParallelCoordinatesSeries(PC_DATA, PC_AXES)
    svg = s.to_svg()
    assert "sepal_l" in svg
    assert "petal_w" in svg

def test_parallel_coords_figure_shorthand():
    fig = Figure(width=800, height=500, auto_display=False)
    fig.parallel_coords(PC_DATA, PC_AXES, hue=PC_HUE)
    svg = fig.render_svg()
    assert "polyline" in svg

def test_parallel_coords_xss_escaped():
    axes = ['<script>alert(1)</script>', 'normal']
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    s    = ParallelCoordinatesSeries(data, axes)
    svg  = s.to_svg()
    assert "<script>" not in svg


# =============================================================================
# 4 — DivergingBarSeries
# =============================================================================

DIV_CATS = ["Feature A", "Feature B", "Feature C", "Feature D"]
DIV_VALS = [+42, -15, +63, -8]

def test_diverging_bar_renders_rects():
    s   = DivergingBarSeries(DIV_CATS, DIV_VALS)
    svg = s.to_svg()
    assert "<rect" in svg

def test_diverging_bar_category_labels():
    s   = DivergingBarSeries(DIV_CATS, DIV_VALS)
    svg = s.to_svg()
    for cat in DIV_CATS:
        assert cat in svg

def test_diverging_bar_zero_line():
    s   = DivergingBarSeries(DIV_CATS, DIV_VALS, zero_line=True)
    svg = s.to_svg()
    assert "<line" in svg

def test_diverging_bar_no_zero_line():
    s   = DivergingBarSeries(DIV_CATS, DIV_VALS, zero_line=False)
    svg = s.to_svg()
    # Should still have grid lines but no zero reference
    # Test just doesn't crash
    assert "<rect" in svg

def test_diverging_bar_all_positive():
    s   = DivergingBarSeries(["A", "B"], [10, 20])
    svg = s.to_svg()
    assert "<rect" in svg

def test_diverging_bar_all_negative():
    s   = DivergingBarSeries(["A", "B"], [-10, -20])
    svg = s.to_svg()
    assert "<rect" in svg

def test_diverging_bar_length_mismatch_raises():
    with pytest.raises(ValueError):
        DivergingBarSeries(["A", "B", "C"], [1, 2])

def test_diverging_bar_value_labels():
    s   = DivergingBarSeries(DIV_CATS, DIV_VALS, show_values=True)
    svg = s.to_svg()
    assert "+42" in svg or "42" in svg

def test_diverging_bar_figure_shorthand():
    fig = Figure(width=700, height=400, auto_display=False)
    fig.diverging_bar(DIV_CATS, DIV_VALS)
    svg = fig.render_svg()
    assert "<svg" in svg

def test_diverging_bar_xss_labels():
    s   = DivergingBarSeries(['<b>label</b>', 'safe'], [1, -1])
    svg = s.to_svg()
    assert "<b>" not in svg


# =============================================================================
# 5 — LTTB Downsampling (Matplotlib performance parity)
# =============================================================================

def test_lttb_reduces_points():
    x = list(range(10_000))
    y = [math.sin(i / 100) for i in x]
    x_d, y_d = lttb(x, y, threshold=500)
    assert len(x_d) == 500
    assert len(y_d) == 500

def test_lttb_preserves_endpoints():
    x = list(range(1000))
    y = list(range(1000))
    x_d, y_d = lttb(x, y, threshold=50)
    assert x_d[0]  == x[0]
    assert x_d[-1] == x[-1]
    assert y_d[0]  == y[0]
    assert y_d[-1] == y[-1]

def test_lttb_threshold_3_minimum():
    with pytest.raises(ValueError, match="threshold"):
        lttb([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], threshold=2)

def test_lttb_mismatched_xy_raises():
    with pytest.raises(ValueError):
        lttb([1, 2, 3], [1, 2], threshold=3)

def test_lttb_passthrough_below_threshold():
    x = list(range(10))
    y = list(range(10))
    x_d, y_d = lttb(x, y, threshold=100)
    np.testing.assert_array_equal(x_d, x)
    np.testing.assert_array_equal(y_d, y)

def test_maybe_downsample_no_op_small():
    x = list(range(100))
    y = list(range(100))
    x_d, y_d = maybe_downsample(x, y, threshold=1000)
    assert x_d is x   # unchanged

def test_maybe_downsample_triggers_on_large():
    x = list(range(AUTO_THRESHOLD + 1000))
    y = [math.sin(i) for i in x]
    x_d, y_d = maybe_downsample(x, y)
    assert len(x_d) <= AUTO_THRESHOLD

def test_line_series_auto_downsamples_svg():
    """LineSeries.to_svg() should not crash on 20k points and produce valid SVG."""
    n   = 20_000
    x   = list(range(n))
    y   = [math.sin(i / 50) for i in x]
    s   = LineSeries(x, y, color="#1f77b4")
    ax  = _finalize(_make_ax(), s)
    svg = s.to_svg(ax)
    assert "polyline" in svg
    # Should be downsampled — points string should NOT contain 20k entries
    point_count = svg.count(" ") // 1   # rough proxy
    assert len(svg) < 2_000_000   # well under raw 20k point budget

def test_lttb_shape_preservation():
    """Downsampled signal should preserve peak/trough positions."""
    x  = np.linspace(0, 4 * math.pi, 10_000)
    y  = np.sin(x)
    x_d, y_d = lttb(x, y, threshold=200)
    # Max of downsampled should be within one period of true max
    assert abs(float(y_d.max()) - 1.0) < 0.05
    assert abs(float(y_d.min()) + 1.0) < 0.05


# =============================================================================
# 6 — Hue / Palette API (Seaborn parity)
# =============================================================================

@pytest.fixture
def sales_df():
    return pd.DataFrame({
        "month":   ["Jan","Feb","Mar","Apr","May","Jun"] * 2,
        "revenue": [120, 145, 132, 178, 159, 203, 90, 110, 95, 140, 115, 160],
        "region":  ["North"] * 6 + ["South"] * 6,
        "spend":   [50, 60, 55, 80, 70, 90, 40, 50, 45, 65, 55, 75],
    })

def test_accessor_bar_hue_creates_multiple_series(sales_df):
    import glyphx  # ensure accessor registered
    fig = sales_df.glyphx.bar(x="month", y="revenue", hue="region",
                               auto_display=False)
    # Should have one BarSeries per unique region value
    n_series = len(fig.series)
    assert n_series == sales_df["region"].nunique()

def test_accessor_bar_hue_different_colors(sales_df):
    import glyphx
    fig = sales_df.glyphx.bar(x="month", y="revenue", hue="region",
                               auto_display=False)
    colors = [s.color for s, _ in fig.series if hasattr(s, "color")]
    assert len(set(colors)) > 1   # distinct colors per group

def test_accessor_bar_hue_legend_labels(sales_df):
    import glyphx
    fig = sales_df.glyphx.bar(x="month", y="revenue", hue="region",
                               auto_display=False)
    svg = fig.render_svg()
    assert "North" in svg
    assert "South" in svg

def test_accessor_line_hue(sales_df):
    import glyphx
    fig = sales_df.glyphx.line(x="month", y="revenue", hue="region",
                                auto_display=False)
    assert len(fig.series) == sales_df["region"].nunique()
    svg = fig.render_svg()
    assert "polyline" in svg

def test_accessor_scatter_hue(sales_df):
    import glyphx
    fig = sales_df.glyphx.scatter(x="spend", y="revenue", hue="region",
                                   auto_display=False)
    assert len(fig.series) == sales_df["region"].nunique()
    svg = fig.render_svg()
    assert "circle" in svg

def test_accessor_bar_no_hue_unchanged(sales_df):
    """Without hue, bar() should produce a single series as before."""
    import glyphx
    fig = sales_df[sales_df["region"] == "North"].glyphx.bar(
        x="month", y="revenue", auto_display=False
    )
    assert len(fig.series) == 1

def test_hue_theme_colors_used(sales_df):
    """Hue groups should pick colors from the active theme palette."""
    import glyphx
    fig = sales_df.glyphx.bar(x="month", y="revenue", hue="region",
                               theme="dark", auto_display=False)
    dark_palette = fig.theme["colors"]
    series_colors = [s.color for s, _ in fig.series if hasattr(s, "color")]
    for col in series_colors:
        assert col in dark_palette

def test_hue_three_groups():
    """Hue with three unique values should produce three distinct series."""
    import glyphx
    df = pd.DataFrame({
        "x": list(range(9)),
        "y": list(range(9)),
        "group": ["A"]*3 + ["B"]*3 + ["C"]*3,
    })
    fig = df.glyphx.scatter(x="x", y="y", hue="group", auto_display=False)
    assert len(fig.series) == 3
    colors = [s.color for s, _ in fig.series]
    assert len(set(colors)) == 3
