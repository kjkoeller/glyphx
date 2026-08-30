"""
Every public chart type must render well-formed SVG.

Fourteen chart types sat at 5-20% coverage: constructed by a smoke test,
never actually rendered. That is the gap the NaN-coordinate bug lived in --
the output looked plausible, started with ``<svg``, and was not valid XML.

So these tests parse the output rather than grepping it, and assert that no
non-finite value reached a coordinate attribute. One factory per chart type,
each producing the smallest input that exercises a real render path.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import glyphx
from glyphx import Figure

SVG_NS = "{http://www.w3.org/2000/svg}"

#: Attributes whose values are numeric coordinates or lengths.
_COORD_ATTRS = (
    "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
    "width", "height", "points", "d", "offset",
)

_BAD_NUMBER = re.compile(r"\b(?:nan|-?inf(?:inity)?)\b", re.IGNORECASE)


def assert_valid_svg(svg: str) -> ET.Element:
    """Parse the SVG and assert no coordinate carries a non-finite value."""
    assert svg and svg.lstrip().startswith("<svg"), "output is not an SVG document"
    root = ET.fromstring(svg)          # raises on malformed XML

    for el in root.iter():
        for attr in _COORD_ATTRS:
            value = el.get(attr)
            if value and _BAD_NUMBER.search(value):
                tag = el.tag.replace(SVG_NS, "")
                pytest.fail(f"<{tag} {attr}={value!r}> contains a non-finite coordinate")
    return root


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

X = [1, 2, 3, 4, 5]
Y = [2.0, 4.0, 3.0, 5.0, 4.5]
CATS = ["alpha", "beta", "gamma"]
VALS = [3.0, 7.0, 5.0]
SAMPLES = [1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 8.0]
GRID = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
DATES = ["2024-01-01", "2024-01-02", "2024-01-03"]


def _figure(series, **kwargs) -> str:
    return Figure(auto_display=False, **kwargs).add(series).render_svg()


# ---------------------------------------------------------------------------
# One factory per chart type.  Each returns a rendered SVG string.
# ---------------------------------------------------------------------------

CHART_FACTORIES: dict[str, callable] = {
    # Core
    "line":        lambda: _figure(glyphx.LineSeries(X, Y)),
    "bar":         lambda: _figure(glyphx.BarSeries(CATS, VALS)),
    "scatter":     lambda: _figure(glyphx.ScatterSeries(X, Y)),
    "pie":         lambda: _figure(glyphx.PieSeries(VALS, labels=CATS)),
    "donut":       lambda: _figure(glyphx.DonutSeries(VALS, labels=CATS)),
    "histogram":   lambda: _figure(glyphx.HistogramSeries(SAMPLES, bins=4)),
    "heatmap":     lambda: _figure(glyphx.HeatmapSeries(GRID)),
    "boxplot":     lambda: _figure(glyphx.BoxPlotSeries([SAMPLES, SAMPLES])),

    # Statistical
    "ecdf":        lambda: _figure(glyphx.ECDFSeries(SAMPLES)),
    "kde":         lambda: _figure(glyphx.KDESeries(SAMPLES)),
    "raincloud":   lambda: _figure(glyphx.RaincloudSeries([SAMPLES, SAMPLES])),
    "violin":      lambda: _figure(glyphx.ViolinPlotSeries([SAMPLES, SAMPLES])),
    "fill_between": lambda: _figure(glyphx.FillBetweenSeries(X, Y, [1.0] * 5)),
    "swarm":       lambda: _figure(glyphx.SwarmPlotSeries([SAMPLES, SAMPLES])),
    "count":       lambda: _figure(glyphx.CountPlotSeries(["a", "b", "a", "c"])),

    # Financial
    "candlestick": lambda: _figure(glyphx.CandlestickSeries(
        DATES, [1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [0.5, 1.5, 2.5], [3.0, 4.0, 5.0])),
    "waterfall":   lambda: _figure(glyphx.WaterfallSeries(CATS, [5.0, -2.0, 3.0])),

    # Hierarchical / part-to-whole
    "treemap":     lambda: _figure(glyphx.TreemapSeries(CATS, VALS)),
    "sunburst":    lambda: _figure(glyphx.SunburstSeries(
        ["root", "a", "b"], ["", "root", "root"], [10.0, 6.0, 4.0])),

    # Comparison
    "grouped_bar": lambda: _figure(glyphx.GroupedBarSeries(
        ["g1", "g2"], CATS, [[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]])),
    "stacked_bar": lambda: _figure(glyphx.StackedBarSeries(
        CATS, {"s1": [1.0, 2.0, 3.0], "s2": [3.0, 2.0, 1.0]})),
    "stacked_bar_diverging": lambda: _figure(glyphx.StackedBarSeries(
        CATS, {"s1": [3.0, -2.0, 1.0], "s2": [2.0, 4.0, -3.0],
               "s3": [-1.0, 1.0, 2.0]})),
    "stacked_bar_normalized": lambda: _figure(glyphx.StackedBarSeries(
        CATS, {"s1": [3.0, -2.0, 1.0], "s2": [2.0, 4.0, -3.0]}, normalize=True)),
    "bar_diverging": lambda: _figure(glyphx.BarSeries(CATS, [5.0, -3.0, 2.0])),
    "bar_all_negative": lambda: _figure(glyphx.BarSeries(CATS, [-2.0, -5.0, -1.0])),
    "math_labels": lambda: (
        Figure(auto_display=False, title=r"Energy $E = mc^2$")
        .line(X, Y, label=r"$\alpha$ decay")
        .set_xlabel(r"Time $t$ (s)")
        .set_ylabel(r"$\sigma_{x}$ (m)")
        .render_svg()
    ),
    "diverging_bar": lambda: _figure(glyphx.DivergingBarSeries(CATS, [5.0, -3.0, 2.0])),
    "bubble":      lambda: _figure(glyphx.BubbleSeries(X, Y, [10, 20, 30, 40, 50])),
    "bump":        lambda: _figure(glyphx.BumpChartSeries(
        CATS, {"a": [1, 2, 3], "b": [3, 1, 2]})),
    "parallel_coords": lambda: _figure(glyphx.ParallelCoordinatesSeries(
        [[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]], ["p", "q", "r"])),

    # Time / project
    "gantt":       lambda: _figure(glyphx.GanttSeries([
        {"task": "design", "start": "2024-01-01", "end": "2024-01-10"},
        {"task": "build",  "start": "2024-01-05", "end": "2024-01-20"},
    ])),

    # Compact
    "sparkline":   lambda: _figure(glyphx.SparklineSeries(SAMPLES)),

    # Field / density
    "contour":     lambda: _figure(glyphx.ContourSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], GRID, levels=3)),
}


@pytest.mark.parametrize("chart", sorted(CHART_FACTORIES))
def test_chart_renders_valid_svg(chart):
    assert_valid_svg(CHART_FACTORIES[chart]())


@pytest.mark.parametrize("chart", sorted(CHART_FACTORIES))
def test_chart_output_has_no_unresolved_placeholders(chart):
    """A missing theme key or format arg surfaces as a literal in the output."""
    svg = CHART_FACTORIES[chart]()
    assert 'fill="None"' not in svg
    assert 'stroke="None"' not in svg
    assert "{" not in svg, "an unfilled format placeholder reached the SVG"


# ---------------------------------------------------------------------------
# 3D chart types render through Figure3D, not Figure
# ---------------------------------------------------------------------------

def _figure3d(series) -> str:
    fig = glyphx.Figure3D()
    fig.add(series)
    return fig.render_svg()


CHART_3D_FACTORIES = {
    "scatter3d": lambda: _figure3d(glyphx.Scatter3DSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0])),
    "line3d": lambda: _figure3d(glyphx.Line3DSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0])),
    "bar3d": lambda: _figure3d(glyphx.Bar3DSeries(
        [1.0, 2.0], [1.0, 2.0], [3.0, 4.0])),
    "surface3d": lambda: _figure3d(glyphx.Surface3DSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], GRID)),
}


@pytest.mark.parametrize("chart", sorted(CHART_3D_FACTORIES))
def test_3d_chart_renders_valid_svg(chart):
    assert_valid_svg(CHART_3D_FACTORIES[chart]())


SERIES_3D_FACTORIES = {
    "scatter3d": lambda: glyphx.Scatter3DSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0]),
    "line3d": lambda: glyphx.Line3DSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0]),
    "bar3d": lambda: glyphx.Bar3DSeries([1.0, 2.0], [1.0, 2.0], [3.0, 4.0]),
    "surface3d": lambda: glyphx.Surface3DSeries(
        [1.0, 2.0, 3.0], [1.0, 2.0, 3.0], GRID),
}


@pytest.mark.parametrize("chart", sorted(SERIES_3D_FACTORIES))
def test_3d_chart_html_payload_is_valid_json(chart):
    """The WebGL path embeds data as JSON; NaN would make it unparseable."""
    import json

    fig = glyphx.Figure3D()
    fig.add(SERIES_3D_FACTORIES[chart]())
    html = fig.render_html()

    assert "NaN" not in html, "non-finite value reached the WebGL payload"
    assert "{threejs" not in html, "unfilled template placeholder"

    payload = re.search(r"const DATA\s*=\s*(\[.*?\]|\{.*?\});", html, re.DOTALL)
    assert payload, "could not locate the embedded DATA payload"
    json.loads(payload.group(1))     # raises if the payload is not valid JSON


# ---------------------------------------------------------------------------
# Composite helpers
# ---------------------------------------------------------------------------

def test_regplot_renders():
    import pandas as pd

    df = pd.DataFrame({"x": X, "y": Y})
    fig = glyphx.regplot(df, x="x", y="y")
    assert_valid_svg(fig.render_svg())


def test_regplot_accepts_raw_vectors():
    fig = glyphx.regplot(None, x_vals=X, y_vals=Y)
    assert_valid_svg(fig.render_svg())


def test_clustermap_renders():
    matrix = np.array(GRID, dtype=float)
    out = glyphx.clustermap(matrix)
    svg = out.render_svg() if hasattr(out, "render_svg") else out
    assert_valid_svg(svg)


def test_vega_lite_export_is_json_serialisable():
    import json

    fig = Figure(auto_display=False).line(X, Y)
    spec = glyphx.to_vega_lite(fig)
    text = json.dumps(spec)          # raises on NaN-free-ness violations below
    assert "NaN" not in text, "NaN is not valid JSON and breaks Vega-Lite"
    assert spec.get("$schema", "").startswith("https://vega.github.io/schema/vega-lite/")


# ---------------------------------------------------------------------------
# The same charts must survive missing values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [float("nan"), None, float("inf")])
def test_core_xy_charts_survive_missing_values(bad):
    for factory in (
        lambda: glyphx.LineSeries([1, 2, 3], [1.0, bad, 3.0]),
        lambda: glyphx.ScatterSeries([1, 2, 3], [1.0, bad, 3.0]),
    ):
        assert_valid_svg(_figure(factory()))


# Chart types deliberately not in the smoke matrix, with the reason.
_UNCOVERED_SERIES = {
    "StreamingSeries": "stateful; covered by tests/test_vs_competitors.py",
    "ChoroplethSeries": "needs a GeoJSON fixture",
    "HeatmapSeries": "covered above under 'heatmap'",
}


def test_no_series_type_is_silently_untested():
    """A new chart type must be added to the matrix or explicitly excused."""
    exported = {n for n in glyphx.__all__ if n.endswith("Series")}
    exercised = set()
    for factory in list(CHART_FACTORIES.values()) + list(SERIES_3D_FACTORIES.values()):
        source = factory.__code__.co_names
        exercised.update(n for n in exported if n in source)

    missing = exported - exercised - set(_UNCOVERED_SERIES)
    assert not missing, (
        f"these chart types have no smoke test: {sorted(missing)}. "
        f"Add a factory to CHART_FACTORIES, or list it in _UNCOVERED_SERIES "
        f"with a reason."
    )


def test_no_chart_emits_scientific_notation_coordinates():
    """SVG accepts 1e+21 but many renderers mishandle it; catch the drift early."""
    svg = _figure(glyphx.LineSeries(X, Y))
    assert not re.search(r'(?:cx|cy|x1|y1)="[^"]*e[+-]?\d', svg, re.IGNORECASE)


def test_precision_is_respected_across_chart_types():
    for name in ("line", "scatter", "bar"):
        svg = CHART_FACTORIES[name]()
        for value in re.findall(r'c[xy]="([\d.]+)"', svg):
            _, _, frac = value.partition(".")
            assert len(frac) <= 2, f"{name}: {value} exceeds the configured precision"

