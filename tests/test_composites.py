"""
Composite chart helpers that build a figure out of several sub-plots.

These sat at 10-20% coverage: imported by a smoke test, never actually run
against a DataFrame. They are the entry points most likely to be used from a
notebook, and the most likely to break when the series layer changes
underneath them.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import pytest

import glyphx
from glyphx import Figure


@pytest.fixture
def df():
    rng = np.random.default_rng(0)
    n = 40
    return pd.DataFrame({
        "height": rng.normal(170, 8, n),
        "weight": rng.normal(70, 12, n),
        "age": rng.integers(20, 60, n).astype(float),
        "group": rng.choice(["a", "b"], n),
    })


def _svg_of(obj) -> str:
    return obj.render_svg() if hasattr(obj, "render_svg") else str(obj)


def _assert_renders(obj) -> str:
    svg = _svg_of(obj)
    assert svg.lstrip().startswith("<svg")
    ET.fromstring(svg)
    assert "nan" not in svg.lower()
    return svg


# ---------------------------------------------------------------------------
# Multi-panel helpers
# ---------------------------------------------------------------------------

def test_pairplot_renders(df):
    _assert_renders(glyphx.pairplot(df[["height", "weight", "age"]]))


def test_pairplot_with_hue(df):
    _assert_renders(glyphx.pairplot(df[["height", "weight", "group"]], hue="group"))


def test_pairplot_builds_a_real_grid(df):
    """
    Every cell needs its own Axes.

    ``fig.add_axes()`` with no arguments always hands back cell (0, 0), so the
    whole n-by-n grid used to be drawn on top of a single axes and the figure
    was an overplot rather than a pair grid.
    """
    fig = glyphx.pairplot(df[["height", "weight", "age"]])
    assert (fig.rows, fig.cols) == (3, 3)
    occupied = [ax for row in fig.grid for ax in row if ax is not None]
    assert len(occupied) == 9
    assert len({id(ax) for ax in occupied}) == 9


def test_pairplot_hue_produces_one_labelled_series_per_category(df):
    """The legend block used to sit after `return fig` and never ran."""
    fig = glyphx.pairplot(df[["height", "weight", "group"]], hue="group")
    off_diag = fig.grid[0][1]
    assert sorted(s.label for s in off_diag.series) == ["a", "b"]

    svg = _assert_renders(fig)
    assert svg.count('class="legend-label"') == 2


def test_pairplot_hue_values_are_escaped():
    frame = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [4.0, 3.0, 2.0, 1.0],
        "g": ["Ben & Co", "plain", "Ben & Co", "plain"],
    })
    svg = _assert_renders(glyphx.pairplot(frame, hue="g"))
    assert "Ben &amp; Co" in svg


def test_pairplot_kde_diagonal_has_no_stray_identity_line(df):
    """
    ``diag_kind="kde"`` fell through a second bare `if` into the else branch
    and drew LineSeries(x, x) on top of the density curve.
    """
    fig = glyphx.pairplot(df[["height", "weight"]], diag_kind="kde")
    assert len(fig.grid[0][0].series) == 1


@pytest.mark.parametrize("diag_kind", ["hist", "kde"])
def test_pairplot_diagonal_kinds(df, diag_kind):
    _assert_renders(
        glyphx.pairplot(df[["height", "weight"]], diag_kind=diag_kind)
    )


def test_jointplot_renders(df):
    _assert_renders(glyphx.jointplot(df, x="height", y="weight"))


@pytest.mark.parametrize("marginal", ["hist", "kde"])
def test_jointplot_marginals(df, marginal):
    _assert_renders(glyphx.jointplot(df, x="height", y="weight", marginal=marginal))


def test_lmplot_renders(df):
    _assert_renders(glyphx.lmplot(df, x="height", y="weight"))


def test_lmplot_higher_order_fit(df):
    _assert_renders(glyphx.lmplot(df, x="height", y="weight", order=2))


# ---------------------------------------------------------------------------
# Regression plot
# ---------------------------------------------------------------------------

def test_regplot_from_dataframe(df):
    _assert_renders(glyphx.regplot(df, x="height", y="weight"))


def test_regplot_from_vectors():
    _assert_renders(glyphx.regplot(None, x_vals=[1, 2, 3, 4], y_vals=[2.0, 4.0, 5.0, 8.0]))


def test_regplot_polynomial_order(df):
    _assert_renders(glyphx.regplot(df, x="height", y="weight", order=2))


def test_regplot_confidence_band_is_drawn(df):
    svg = _svg_of(glyphx.regplot(df, x="height", y="weight", ci=95))
    assert "<polygon" in svg or "<path" in svg, "expected a filled CI band"


# ---------------------------------------------------------------------------
# Vega-Lite export
# ---------------------------------------------------------------------------

def test_vega_lite_spec_is_valid_json():
    fig = Figure(auto_display=False).line([1, 2, 3], [4.0, 5.0, 6.0])
    spec = glyphx.to_vega_lite(fig)
    text = json.dumps(spec)
    assert "NaN" not in text, "NaN is not valid JSON and breaks Vega-Lite"
    assert spec["$schema"].startswith("https://vega.github.io/schema/vega-lite/")


def test_vega_lite_carries_the_data_values():
    fig = Figure(auto_display=False).line([1, 2, 3], [4.0, 5.0, 6.0])
    spec = glyphx.to_vega_lite(fig)
    text = json.dumps(spec)
    assert "4" in text and "6" in text


def test_vega_lite_skips_missing_values():
    fig = Figure(auto_display=False).line([1, 2, 3], [4.0, float("nan"), 6.0])
    spec = glyphx.to_vega_lite(fig)
    json.dumps(spec)          # must not raise, must not embed NaN


# ---------------------------------------------------------------------------
# Sparkline
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["line", "bar"])
def test_sparkline_kinds(kind):
    series = glyphx.SparklineSeries([1.0, 3.0, 2.0, 5.0, 4.0], kind=kind)
    _assert_renders(Figure(auto_display=False).add(series))


def test_sparkline_with_fill():
    series = glyphx.SparklineSeries([1.0, 3.0, 2.0, 5.0], fill=True)
    _assert_renders(Figure(auto_display=False).add(series))


def test_sparkline_single_value_does_not_divide_by_zero():
    series = glyphx.SparklineSeries([5.0, 5.0, 5.0])
    _assert_renders(Figure(auto_display=False).add(series))


# ---------------------------------------------------------------------------
# DataFrame accessor surface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method", ["line", "scatter", "bar"])
def test_accessor_methods_render(df, method):
    fig = getattr(df.glyphx, method)(x="height", y="weight")
    _assert_renders(fig)


def test_accessor_hist(df):
    _assert_renders(df.glyphx.hist(x="height"))


# ---------------------------------------------------------------------------
# Subplot grid bounds
# ---------------------------------------------------------------------------

def test_add_axes_outside_the_grid_explains_itself():
    """It used to surface as a bare IndexError from inside figure.py."""
    fig = Figure(auto_display=False)          # default 1x1
    with pytest.raises(IndexError, match=r"1x1 grid"):
        fig.add_axes(0, 1)


def test_add_axes_within_the_grid_works():
    fig = Figure(auto_display=False, rows=2, cols=2)
    assert fig.add_axes(1, 1) is not None
    assert fig.add_axes(1, 1) is fig.add_axes(1, 1), "should be cached, not recreated"


def test_jointplot_builds_a_2x2_grid(df):
    fig = glyphx.jointplot(df, x="height", y="weight")
    assert (fig.rows, fig.cols) == (2, 2)


def test_facet_plot_is_callable_at_all(df):
    """
    ``facet_plot`` forwarded ``kind=`` to ``FacetGrid()``, which has no such
    parameter, so every call raised TypeError -- including the example in
    docs/advanced.rst.  ``x`` and ``y`` were accepted and silently dropped.
    """
    grid = glyphx.facet_plot(df, x="height", y="weight", col="group", kind="scatter")
    _assert_renders(grid)


def test_facet_plot_maps_the_requested_kind(df):
    _assert_renders(glyphx.facet_plot(df, x="height", col="group", kind="hist"))


def test_figure_regplot_method(df):
    """``Figure.regplot`` passed ``y2=`` to ``add()``, whose parameter is
    ``use_y2`` -- TypeError on every call."""
    fig = Figure(auto_display=False).regplot(df, x="height", y="weight")
    _assert_renders(fig)
