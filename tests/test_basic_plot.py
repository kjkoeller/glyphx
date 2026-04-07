"""
Comprehensive GlyphX test suite.

All tests are flat functions (no classes).  Tests cover:
  - Every chart kind via plot()
  - Series constructors and SVG output
  - Bug regression tests (PieSeries.colors, DonutSeries.theme, BoxPlot positions, etc.)
  - Themes, including colorblind Okabe-Ito palette
  - Axis features: dual-Y, log scale, annotations, labels, categorical X
  - Error bars (LineSeries, BarSeries)
  - HeatmapSeries colorbar and row/col labels
  - BoxPlotSeries multi-box and outlier rendering
  - Figure.save() SVG and HTML paths
  - SubplotGrid.render()
  - utils: normalize, svg_escape, _format_tick, draw_legend
  - Edge cases: empty series, single point, equal values, XSS in labels
"""

import math
import os
import tempfile

import numpy as np
import pytest

# ── Module-level imports ────────────────────────────────────────────────────
from glyphx import Figure, plot, themes
from glyphx.layout import Axes, grid
from glyphx.series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries,
)
from glyphx.figure import SubplotGrid
from glyphx.utils import normalize, svg_escape, _format_tick, draw_legend


# ===========================================================================
# Helpers
# ===========================================================================

def _make_axes(width=600, height=400, padding=50, theme=None):
    from glyphx.themes import themes as _themes
    ax = Axes(width=width, height=height, padding=padding,
               theme=theme or _themes["default"])
    return ax


def _finalize_with(ax, *series_list):
    for s in series_list:
        ax.add_series(s)
    ax.finalize()
    return ax


# ===========================================================================
# plot() — high-level API
# ===========================================================================

def test_plot_line_returns_figure():
    fig = plot([1, 2, 3], [4, 5, 6], kind="line", auto_display=False)
    assert isinstance(fig, Figure)


def test_plot_line_svg_contains_polyline():
    fig = plot([1, 2, 3], [4, 5, 6], kind="line", auto_display=False)
    svg = fig.render_svg()
    assert "<svg" in svg
    assert "polyline" in svg


def test_plot_bar():
    fig = plot(["A", "B", "C"], [10, 20, 15], kind="bar", auto_display=False)
    svg = fig.render_svg()
    assert "<rect" in svg


def test_plot_scatter():
    fig = plot([1, 2, 3], [4, 5, 6], kind="scatter", auto_display=False)
    svg = fig.render_svg()
    assert "circle" in svg


def test_plot_hist():
    fig = plot(data=[1, 2, 2, 3, 3, 3, 4], kind="hist", auto_display=False)
    svg = fig.render_svg()
    assert "<rect" in svg


def test_plot_pie():
    fig = plot(data=[30, 40, 30], kind="pie", auto_display=False)
    svg = fig.render_svg()
    assert "<path" in svg


def test_plot_donut():
    fig = plot(data=[10, 20, 30], kind="donut", auto_display=False)
    svg = fig.render_svg()
    assert "<path" in svg


def test_plot_box():
    fig = plot(data=[1, 2, 3, 4, 5, 6, 7], kind="box", auto_display=False)
    svg = fig.render_svg()
    assert "<rect" in svg or "<line" in svg


def test_plot_heatmap():
    matrix = [[1, 2], [3, 4]]
    fig = plot(data=matrix, kind="heatmap", auto_display=False)
    svg = fig.render_svg()
    assert "<rect" in svg


def test_plot_unknown_kind_raises():
    with pytest.raises(ValueError, match="Unsupported kind"):
        plot([1, 2], [3, 4], kind="radar", auto_display=False)


def test_plot_no_data_raises():
    with pytest.raises(ValueError):
        plot(kind="hist", auto_display=False)


def test_plot_y_only_infers_x():
    fig = plot(y=[10, 20, 30], kind="line", auto_display=False)
    svg = fig.render_svg()
    assert "polyline" in svg


def test_plot_title_appears_in_svg():
    fig = plot([1, 2], [3, 4], kind="line", title="My Title", auto_display=False)
    svg = fig.render_svg()
    assert "My Title" in svg


def test_plot_xlabel_ylabel():
    fig = plot([1, 2], [3, 4], kind="line", xlabel="Time", ylabel="Value",
               auto_display=False)
    svg = fig.render_svg()
    assert "Time" in svg
    assert "Value" in svg


# ===========================================================================
# LineSeries
# ===========================================================================

def test_line_series_svg():
    s  = LineSeries([1, 2, 3], [4, 5, 6], color="#ff0000", label="Test")
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "polyline" in svg
    assert "#ff0000" in svg


def test_line_series_dashed():
    s  = LineSeries([1, 2, 3], [1, 2, 3], linestyle="dashed")
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "stroke-dasharray" in svg
    assert "6,3" in svg


def test_line_series_error_bars_y():
    s  = LineSeries([1, 2, 3], [4, 5, 6], yerr=[0.5, 0.5, 0.5])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    # Each error bar has 3 lines (vertical + 2 caps)
    assert svg.count("<line") >= 3


def test_line_series_error_bars_x():
    s  = LineSeries([1, 2, 3], [4, 5, 6], xerr=[0.2, 0.2, 0.2])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert svg.count("<line") >= 3


def test_line_series_title():
    s  = LineSeries([1, 2], [1, 2], title="Sub Title")
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "Sub Title" in svg


# ===========================================================================
# BarSeries
# ===========================================================================

def test_bar_series_numeric_x():
    s  = BarSeries([1, 2, 3], [10, 20, 15])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<rect" in svg


def test_bar_series_categorical_x():
    s  = BarSeries(["A", "B", "C"], [10, 20, 15])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<rect" in svg


def test_bar_series_error_bars():
    s  = BarSeries([1, 2, 3], [10, 20, 15], yerr=[1, 2, 1])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<line" in svg


# ===========================================================================
# ScatterSeries
# ===========================================================================

def test_scatter_circle():
    s  = ScatterSeries([1, 2, 3], [4, 5, 6])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<circle" in svg


def test_scatter_square():
    s  = ScatterSeries([1, 2, 3], [4, 5, 6], marker="square")
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<rect" in svg


# ===========================================================================
# PieSeries — regression for self.colors bug
# ===========================================================================

def test_pie_series_renders():
    s = PieSeries([30, 40, 30], labels=["A", "B", "C"])
    ax = _make_axes()
    ax.width, ax.height = 400, 400
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    assert "<path" in svg


def test_pie_series_default_colors_not_empty():
    """BUG: was `self.colors = self.colors or [...]` — AttributeError."""
    s = PieSeries([10, 20, 30])
    assert len(s.colors) > 0


def test_pie_series_custom_colors():
    s = PieSeries([10, 20], colors=["#aabbcc", "#112233"])
    assert s.colors == ["#aabbcc", "#112233"]


def test_pie_series_zero_total_returns_empty():
    s  = PieSeries([0, 0, 0])
    ax = _make_axes()
    ax.width, ax.height = 400, 400
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    assert svg == ""


# ===========================================================================
# DonutSeries — regression for missing super().__init__ and self.theme
# ===========================================================================

def test_donut_series_has_label_attribute():
    """BUG: super().__init__ was never called → self.label AttributeError."""
    s = DonutSeries([10, 20, 30])
    assert hasattr(s, "label")
    assert hasattr(s, "color")
    assert hasattr(s, "x")
    assert hasattr(s, "y")


def test_donut_series_renders_without_ax():
    """BUG: self.theme was undefined → AttributeError on center hole."""
    s   = DonutSeries([10, 20, 30])
    svg = s.to_svg(ax=None)
    assert "<path" in svg
    assert "<circle" in svg  # centre hole


def test_donut_series_renders_with_ax():
    s   = DonutSeries([10, 20, 30], labels=["X", "Y", "Z"])
    ax  = _make_axes()
    ax.width, ax.height = 400, 400
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    assert "<path" in svg


def test_donut_series_zero_total_returns_empty():
    s   = DonutSeries([0, 0])
    svg = s.to_svg(ax=None)
    assert svg == ""


# ===========================================================================
# HistogramSeries
# ===========================================================================

def test_histogram_bins():
    data = list(range(50))
    s    = HistogramSeries(data, bins=5)
    assert len(s.x) == 5
    assert len(s.y) == 5


def test_histogram_svg():
    s  = HistogramSeries([1, 1, 2, 3, 3, 3], bins=3)
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<rect" in svg


# ===========================================================================
# BoxPlotSeries — regression for hardcoded center_x = ax.scale_x(0.5)
# ===========================================================================

def test_boxplot_single_array():
    s  = BoxPlotSeries([1, 2, 3, 4, 5, 6, 7])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<rect" in svg


def test_boxplot_multiple_arrays():
    """BUG: all boxes overlapped at ax.scale_x(0.5) — now uses actual positions."""
    data = [[1, 2, 3, 4], [5, 6, 7, 8], [2, 4, 6, 8]]
    s    = BoxPlotSeries(data, categories=["A", "B", "C"])
    ax   = _finalize_with(_make_axes(), s)
    svg  = s.to_svg(ax)
    # Three boxes → three IQR rects
    assert svg.count('glyphx-point') >= 3


def test_boxplot_outliers():
    # Values far outside IQR should produce circles
    data = [2, 2, 2, 2, 2, 100]
    s    = BoxPlotSeries(data)
    ax   = _finalize_with(_make_axes(), s)
    svg  = s.to_svg(ax)
    # Outlier rendered as circle
    assert "<circle" in svg


def test_boxplot_category_labels():
    s   = BoxPlotSeries([[1, 2, 3], [4, 5, 6]], categories=["Cat1", "Cat2"])
    ax  = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "Cat1" in svg
    assert "Cat2" in svg


# ===========================================================================
# HeatmapSeries — regression: no colorbar, no labels
# ===========================================================================

def test_heatmap_renders():
    s  = HeatmapSeries([[1, 2], [3, 4]])
    ax = _make_axes()
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    assert "<rect" in svg


def test_heatmap_has_colorbar():
    """BUG: no colorbar was rendered at all."""
    s   = HeatmapSeries([[1, 2], [3, 4]])
    ax  = _make_axes()
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    # Colorbar strip adds many small rects; check we have more than the 4 data cells
    assert svg.count("<rect") > 4


def test_heatmap_row_col_labels():
    s   = HeatmapSeries(
        [[1, 2], [3, 4]],
        row_labels=["Row0", "Row1"],
        col_labels=["Col0", "Col1"],
    )
    ax  = _make_axes()
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    assert "Row0" in svg
    assert "Col1" in svg


def test_heatmap_show_values():
    s   = HeatmapSeries([[10, 20], [30, 40]], show_values=True)
    ax  = _make_axes()
    ax.theme = themes["default"]
    svg = s.to_svg(ax)
    assert "10" in svg or "20" in svg


# ===========================================================================
# Axes / layout
# ===========================================================================

def test_axes_finalize_sets_scales():
    s  = LineSeries([1, 2, 3], [4, 5, 6])
    ax = _finalize_with(_make_axes(), s)
    assert callable(ax.scale_x)
    assert callable(ax.scale_y)


def test_axes_categorical_x_does_not_mutate_series():
    """BUG: compute_domain used to overwrite s.x in place."""
    s  = BarSeries(["A", "B", "C"], [1, 2, 3])
    ax = _finalize_with(_make_axes(), s)
    # Original x must be unchanged
    assert s.x == ["A", "B", "C"]
    # Numeric mapping stored separately
    assert hasattr(s, "_numeric_x")
    assert s._numeric_x == [0.5, 1.5, 2.5]


def test_axes_dual_y():
    s1 = LineSeries([1, 2, 3], [10, 20, 30], label="primary")
    s2 = LineSeries([1, 2, 3], [100, 200, 300], label="secondary")
    ax = _make_axes()
    ax.add_series(s1, use_y2=False)
    ax.add_series(s2, use_y2=True)
    ax.finalize()
    assert ax._y_domain is not None
    assert ax._y2_domain is not None


def test_axes_log_scale():
    s  = LineSeries([1, 10, 100], [1, 10, 100])
    ax = _make_axes()
    ax.yscale = "log"
    ax.add_series(s)
    ax.finalize()
    # Log scale: scale_y(100) should be above scale_y(1)
    assert ax.scale_y(100) < ax.scale_y(1)   # SVG Y is inverted


def test_axes_render_axes_returns_svg():
    s  = LineSeries([1, 2], [3, 4])
    ax = _finalize_with(_make_axes(), s)
    svg = ax.render_axes()
    assert "<line" in svg


def test_axes_render_grid_returns_svg():
    s  = LineSeries([1, 2], [3, 4])
    ax = _finalize_with(_make_axes(), s)
    svg = ax.render_grid()
    assert "<line" in svg or "<text" in svg


def test_axes_categorical_labels_in_grid():
    s  = BarSeries(["Jan", "Feb", "Mar"], [5, 10, 7])
    ax = _finalize_with(_make_axes(), s)
    svg = ax.render_grid()
    assert "Jan" in svg
    assert "Feb" in svg


# ===========================================================================
# Figure
# ===========================================================================

def test_figure_add_and_render():
    fig = Figure(auto_display=False)
    fig.add(LineSeries([1, 2, 3], [4, 5, 6]))
    svg = fig.render_svg()
    assert "<svg" in svg


def test_figure_subplot_grid():
    fig = Figure(rows=2, cols=2, auto_display=False)
    ax0 = fig.add_axes(0, 0)
    ax1 = fig.add_axes(0, 1)
    ax0.add_series(LineSeries([1, 2], [3, 4]))
    ax1.add_series(BarSeries([1, 2], [5, 6]))
    svg = fig.render_svg()
    assert "translate" in svg


def test_figure_annotate():
    fig = Figure(auto_display=False)
    s   = LineSeries([1, 2, 3], [4, 5, 6])
    fig.add(s)
    fig.annotate("peak", x=3, y=6, arrow=True)
    svg = fig.render_svg()
    assert "peak" in svg


def test_figure_annotate_no_arrow():
    fig = Figure(auto_display=False)
    fig.add(LineSeries([1, 2, 3], [1, 2, 3]))
    fig.annotate("label", x=2, y=2)
    svg = fig.render_svg()
    assert "label" in svg


def test_figure_save_svg(tmp_path):
    fig  = Figure(auto_display=False)
    fig.add(LineSeries([1, 2], [3, 4]))
    path = str(tmp_path / "out.svg")
    fig.save(path)
    assert os.path.exists(path)
    content = open(path).read()
    assert "<svg" in content


def test_figure_save_html(tmp_path):
    fig  = Figure(auto_display=False)
    fig.add(LineSeries([1, 2], [3, 4]))
    path = str(tmp_path / "out.html")
    fig.save(path)
    assert os.path.exists(path)
    content = open(path).read()
    assert "<html" in content.lower() or "<!DOCTYPE" in content or "<svg" in content


def test_figure_save_unsupported_ext(tmp_path):
    fig  = Figure(auto_display=False)
    with pytest.raises(ValueError, match="Unsupported"):
        fig.save(str(tmp_path / "out.xyz"))


def test_figure_theme_dark():
    fig = Figure(theme="dark", auto_display=False)
    fig.add(LineSeries([1, 2], [3, 4]))
    svg = fig.render_svg()
    assert "#1e1e1e" in svg   # dark background


def test_figure_theme_colorblind():
    """Colorblind theme must use Okabe-Ito palette, not grayscale."""
    from glyphx.themes import themes as _themes
    colors = _themes["colorblind"]["colors"]
    assert "#E69F00" in colors   # amber
    assert "#56B4E9" in colors   # sky blue


def test_figure_legend_position():
    fig = Figure(legend="bottom-left", auto_display=False)
    s   = LineSeries([1, 2, 3], [4, 5, 6], label="series-a")
    fig.add(s)
    svg = fig.render_svg()
    assert "series-a" in svg


def test_figure_no_legend():
    fig = Figure(legend=False, auto_display=False)
    s   = LineSeries([1, 2], [3, 4], label="hidden")
    fig.add(s)
    assert fig.legend_pos is None


# ===========================================================================
# SubplotGrid
# ===========================================================================

def test_subplot_grid_render():
    sg  = SubplotGrid(1, 2)
    f1  = Figure(auto_display=False)
    f1.add(LineSeries([1, 2], [3, 4]))
    f2  = Figure(auto_display=False)
    f2.add(BarSeries([1, 2], [5, 6]))
    sg.add(f1, 0, 0)
    sg.add(f2, 0, 1)
    html = sg.render()
    assert "<svg" in html


def test_subplot_grid_out_of_range():
    sg = SubplotGrid(2, 2)
    f  = Figure(auto_display=False)
    with pytest.raises(IndexError):
        sg.add(f, 5, 5)


# ===========================================================================
# utils
# ===========================================================================

def test_normalize_range():
    result = normalize([0, 5, 10])
    np.testing.assert_allclose(result, [0.0, 0.5, 1.0])


def test_normalize_equal_values_raises():
    with pytest.raises(ValueError, match="non-zero range"):
        normalize([3, 3, 3])


def test_svg_escape_basic():
    assert svg_escape('<script>') == '&lt;script&gt;'
    assert svg_escape('"quote"') == '&quot;quote&quot;'
    assert svg_escape("O'Brien") == "O&#x27;Brien"


def test_svg_escape_safe_string_unchanged():
    assert svg_escape("hello world") == "hello world"


def test_format_tick_zero():
    assert _format_tick(0) == "0"


def test_format_tick_integer():
    assert _format_tick(42.0) == "42"


def test_format_tick_large():
    result = _format_tick(1_500_000)
    assert "e" in result or "E" in result   # scientific notation


def test_format_tick_small():
    result = _format_tick(0.000001)
    assert "e" in result or "E" in result


def test_format_tick_decimal():
    result = _format_tick(3.14159)
    assert "3.14" in result


def test_draw_legend_empty_returns_empty():
    result = draw_legend([])
    assert result == ""


def test_draw_legend_unlabelled_excluded():
    s = LineSeries([1, 2], [3, 4])   # no label
    result = draw_legend([s])
    assert result == ""


def test_draw_legend_with_labels():
    s   = LineSeries([1, 2], [3, 4], label="My Series")
    svg = draw_legend([s])
    assert "My Series" in svg
    assert "glyphx-legend" in svg


# ===========================================================================
# Security / XSS
# ===========================================================================

def test_xss_in_label_is_escaped():
    s  = LineSeries([1, 2], [3, 4], label='<script>alert(1)</script>')
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_xss_in_bar_x_label_is_escaped():
    s  = BarSeries(['<b>X</b>', 'Normal'], [1, 2])
    ax = _finalize_with(_make_axes(), s)
    svg = s.to_svg(ax)
    assert "<b>" not in svg
    assert "&lt;b&gt;" in svg


def test_xss_in_title_is_escaped():
    fig = Figure(title='<img src=x onerror=alert(1)>', auto_display=False)
    fig.add(LineSeries([1, 2], [3, 4]))
    svg = fig.render_svg()
    assert "<img" not in svg
    assert "&lt;img" in svg


# ===========================================================================
# Edge cases
# ===========================================================================

def test_single_point_line():
    fig = Figure(auto_display=False)
    s   = LineSeries([5], [5])
    fig.add(s)
    svg = fig.render_svg()
    assert "<svg" in svg   # must not crash


def test_large_dataset_line():
    x   = list(range(1000))
    y   = [math.sin(i / 10) for i in x]
    fig = Figure(auto_display=False)
    fig.add(LineSeries(x, y))
    svg = fig.render_svg()
    assert "polyline" in svg


def test_negative_values_bar():
    fig = Figure(auto_display=False)
    fig.add(BarSeries([1, 2, 3], [-5, 10, -3]))
    svg = fig.render_svg()
    assert "<rect" in svg


def test_all_themes_render():
    from glyphx.themes import themes as _themes
    for name in _themes:
        fig = Figure(theme=name, auto_display=False)
        fig.add(LineSeries([1, 2, 3], [4, 5, 6]))
        svg = fig.render_svg()
        assert "<svg" in svg, f"Theme '{name}' failed to render"


def test_grid_layout():
    f1 = Figure(auto_display=False)
    f1.add(LineSeries([1, 2], [3, 4]))
    f2 = Figure(auto_display=False)
    f2.add(BarSeries([1, 2], [5, 6]))
    html = grid([f1, f2], rows=1, cols=2)
    assert "<svg" in html
