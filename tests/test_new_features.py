"""
Tests for features added during the extended dev session:
  - GanttSeries
  - clustermap()
  - FacetGrid.map()
  - regplot() — OLS, polynomial, LOWESS, logistic
  - ChoroplethSeries
  - ScatterSeries sizes= / style=
  - hue= on BoxPlot / Histogram / Violin
  - threshold= kwarg on all series
  - ViolinPlotSeries hue colour rendering
  - to_vega_lite() / save_vega_lite()
  - Figure.render_responsive()
  - StackedBarSeries
  - BumpChartSeries
  - SparklineSeries / sparkline_svg()
  - FillBetweenSeries x-axis alignment in regplot
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import pytest_shim as pytest
sys.modules["pytest"] = pytest

import json, math, tempfile
import numpy as np
import pandas as pd

from glyphx import Figure
from glyphx.series import (
    LineSeries, BarSeries, ScatterSeries,
    BoxPlotSeries, HistogramSeries,
)

RNG = np.random.default_rng(42)


# ── threshold= on all series ──────────────────────────────────────────────────

def test_lineseries_threshold_kwarg():
    ls = LineSeries([1,2,3],[4,5,6], threshold=500)
    assert ls.threshold == 500

def test_scatterseries_threshold_kwarg():
    sc = ScatterSeries([1,2,3],[4,5,6], threshold=2000)
    assert sc.threshold == 2000

def test_boxplot_threshold_kwarg():
    bp = BoxPlotSeries([[1,2,3],[4,5,6]], threshold=100)
    assert bp.threshold == 100

def test_histogram_threshold_kwarg():
    hs = HistogramSeries([1,2,3,4,5], bins=3, threshold=50)
    assert hs.threshold == 50

def test_violin_threshold_kwarg():
    from glyphx.violin_plot import ViolinPlotSeries
    vs = ViolinPlotSeries([[1,2,3],[4,5,6]], threshold=200)
    assert vs.threshold == 200

def test_scatter3d_threshold_kwarg():
    from glyphx.scatter3d import Scatter3DSeries
    s3 = Scatter3DSeries([1],[2],[3], threshold=1000)
    assert s3.threshold == 1000

def test_surface3d_threshold_kwarg():
    from glyphx.surface3d import Surface3DSeries
    sf = Surface3DSeries([0,1],[0,1],[[0,1],[2,3]], threshold=100)
    assert sf.threshold == 100

def test_line3d_threshold_kwarg():
    from glyphx.line3d import Line3DSeries
    l3 = Line3DSeries([1,2],[3,4],[5,6], threshold=500)
    assert l3.threshold == 500

def test_threshold_default_none():
    ls = LineSeries([1,2,3],[4,5,6])
    assert ls.threshold is None


# ── ScatterSeries sizes= ──────────────────────────────────────────────────────

def test_scatter_sizes_stored():
    sizes = [3.0, 6.0, 9.0]
    sc = ScatterSeries([1,2,3],[4,5,6], sizes=sizes)
    assert sc.sizes == sizes

def test_scatter_sizes_renders():
    sizes = [4.0, 8.0, 12.0, 6.0, 10.0]
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries(list(range(5)), list(range(5)), sizes=sizes))
    svg = fig.render_svg()
    assert "<circle" in svg

def test_scatter_style_stored():
    styles = ["circle", "square", "circle"]
    sc = ScatterSeries([1,2,3],[4,5,6], style=styles)
    assert sc.style == styles


# ── hue= on statistical charts ────────────────────────────────────────────────

def test_boxplot_hue_rendering():
    data = [RNG.normal(i, 1, 40).tolist() for i in range(3)]
    bp = BoxPlotSeries(data, categories=["A","B","C"],
                       hue=["X","Y","X"], hue_colors=["#2563eb","#dc2626"])
    fig = Figure(auto_display=False); fig.add(bp)
    svg = fig.render_svg()
    assert "<rect" in svg

def test_boxplot_hue_applies_different_colors():
    data = [RNG.normal(0, 1, 40).tolist(), RNG.normal(2, 1, 40).tolist()]
    bp = BoxPlotSeries(data, categories=["A","B"],
                       hue=["G1","G2"], hue_colors=["#ff0000","#0000ff"])
    fig = Figure(auto_display=False); fig.add(bp)
    svg = fig.render_svg()
    assert "#ff0000" in svg
    assert "#0000ff" in svg

def test_histogram_hue_renders():
    data = RNG.normal(0, 1, 200).tolist()
    hue  = ["A"]*100 + ["B"]*100
    hs   = HistogramSeries(data, bins=15, hue=hue)
    fig  = Figure(auto_display=False); fig.add(hs)
    svg  = fig.render_svg()
    assert "<rect" in svg

def test_violin_hue_renders():
    from glyphx.violin_plot import ViolinPlotSeries
    data = [RNG.normal(i, 1, 50).tolist() for i in range(3)]
    vs   = ViolinPlotSeries(data, hue=["Ctrl","DrugA","DrugB"])
    fig  = Figure(auto_display=False); fig.add(vs)
    svg  = fig.render_svg()
    assert "<path" in svg


# ── Gantt chart ───────────────────────────────────────────────────────────────

def test_gantt_renders():
    from glyphx.gantt import GanttSeries
    from datetime import date
    tasks = [
        {"task": "Design", "start": date(2025,1,6), "end": date(2025,1,17),
         "group": "Ph1", "progress": 1.0},
        {"task": "Launch", "start": date(2025,3,1), "end": date(2025,3,1),
         "group": "Ph2", "milestone": True},
    ]
    fig = Figure(width=700, height=280, auto_display=False)
    fig.add(GanttSeries(tasks, group_colors={"Ph1":"#2563eb","Ph2":"#dc2626"}))
    svg = fig.render_svg()
    assert "<rect" in svg or "<polygon" in svg

def test_gantt_milestone_diamond():
    from glyphx.gantt import GanttSeries
    from datetime import date
    tasks = [{"task": "Go-Live", "start": date(2025,3,1), "end": date(2025,3,1),
              "milestone": True}]
    fig = Figure(width=600, height=200, auto_display=False)
    fig.add(GanttSeries(tasks))
    svg = fig.render_svg()
    assert "<polygon" in svg

def test_gantt_progress_bar():
    from glyphx.gantt import GanttSeries
    from datetime import date
    tasks = [{"task": "Dev", "start": date(2025,1,1), "end": date(2025,2,1),
              "progress": 0.6}]
    fig = Figure(width=600, height=180, auto_display=False)
    fig.add(GanttSeries(tasks))
    svg = fig.render_svg()
    assert "60%" in svg

def test_figure_gantt_shorthand():
    from datetime import date
    tasks = [{"task": "A", "start": date(2025,1,1), "end": date(2025,1,10)}]
    fig = Figure(width=600, height=200, auto_display=False)
    result = fig.gantt(tasks)
    assert result is fig   # returns self for chaining


# ── clustermap ────────────────────────────────────────────────────────────────

def test_clustermap_renders():
    from glyphx.clustermap import clustermap
    mat = RNG.normal(0, 1, (6, 5))
    df  = pd.DataFrame(mat, columns=[f"S{j}" for j in range(5)])
    fig = clustermap(df, cmap="viridis", title="Test")
    svg = fig.render_svg()
    assert "<svg" in svg
    assert "<rect" in svg

def test_clustermap_row_cluster():
    from glyphx.clustermap import clustermap
    mat = RNG.normal(0, 1, (5, 4))
    fig = clustermap(mat, row_cluster=True, col_cluster=False)
    svg = fig.render_svg()
    assert "polyline" in svg or "<line" in svg  # dendrogram

def test_clustermap_z_score():
    from glyphx.clustermap import clustermap
    mat = RNG.normal(0, 1, (4, 4))
    fig = clustermap(mat, z_score="row")
    assert "<svg" in fig.render_svg()

def test_clustermap_no_cluster():
    from glyphx.clustermap import clustermap
    mat = RNG.normal(0, 1, (3, 3))
    fig = clustermap(mat, row_cluster=False, col_cluster=False)
    assert "<svg" in fig.render_svg()


# ── FacetGrid ─────────────────────────────────────────────────────────────────

def test_facet_grid_scatter():
    from glyphx.facet_grid import FacetGrid
    df = pd.DataFrame({
        "species": ["A"]*30 + ["B"]*30,
        "x": RNG.normal(0, 1, 60).tolist(),
        "y": RNG.normal(0, 1, 60).tolist(),
    })
    g = FacetGrid(df, col="species", height=200, aspect=1.2)
    g.map("scatter", x="x", y="y")
    assert len(g._figs) == 2
    svg = g.render_svg()
    assert "<svg" in svg

def test_facet_grid_hist():
    from glyphx.facet_grid import FacetGrid
    df = pd.DataFrame({
        "group": ["G1"]*40 + ["G2"]*40 + ["G3"]*40,
        "val":   RNG.normal(0, 1, 120).tolist(),
    })
    g = FacetGrid(df, col="group", height=180, aspect=1.1)
    g.map("hist", x="val")
    assert len(g._figs) == 3

def test_facet_grid_hue():
    from glyphx.facet_grid import FacetGrid
    df = pd.DataFrame({
        "col":   ["X"]*40 + ["Y"]*40,
        "hue":   ["M","F"]*40,
        "x":     RNG.normal(0, 1, 80).tolist(),
        "y":     RNG.normal(0, 1, 80).tolist(),
    })
    g = FacetGrid(df, col="col", hue="hue", height=200, aspect=1.2)
    g.map("scatter", x="x", y="y")
    svg = g.render_svg()
    assert "<svg" in svg

def test_facet_grid_repr():
    from glyphx.facet_grid import FacetGrid
    df = pd.DataFrame({"c": ["A","B"], "v": [1, 2]})
    g = FacetGrid(df, col="c")
    assert "FacetGrid" in repr(g)


# ── regplot ───────────────────────────────────────────────────────────────────

def test_regplot_ols():
    from glyphx.regplot import regplot
    x = RNG.normal(0, 1, 60)
    y = 2*x + RNG.normal(0, 0.5, 60)
    fig = regplot(None, x_vals=x.tolist(), y_vals=y.tolist(), n_boot=20)
    assert "<circle" in fig.render_svg()

def test_regplot_ci_band_x_alignment():
    """CI band x-values should span the actual data range, not range(200)."""
    from glyphx.regplot import regplot
    from glyphx.fill_between import FillBetweenSeries
    x = np.linspace(10, 20, 30)
    y = 3*x + RNG.normal(0, 1, 30)
    fig = regplot(None, x_vals=x.tolist(), y_vals=y.tolist(), n_boot=20)
    for s, _ in fig.series:
        if isinstance(s, FillBetweenSeries):
            assert s.x[0] > 1, f"x[0]={s.x[0]} looks like range() not x_eval"
            assert s.x[0] >= 9.0, f"Expected ~10, got {s.x[0]}"
            break

def test_regplot_polynomial():
    from glyphx.regplot import regplot
    x = np.linspace(-2, 2, 40)
    y = x**2 + RNG.normal(0, 0.3, 40)
    fig = regplot(None, x_vals=x.tolist(), y_vals=y.tolist(), order=2, ci=0)
    assert "<circle" in fig.render_svg()

def test_regplot_lowess():
    from glyphx.regplot import regplot
    x = np.sort(RNG.normal(0, 1, 50))
    y = np.sin(x*2) + RNG.normal(0, 0.2, 50)
    fig = regplot(None, x_vals=x.tolist(), y_vals=y.tolist(), lowess=True)
    assert "<circle" in fig.render_svg()

def test_regplot_logistic():
    from glyphx.regplot import regplot
    x = RNG.normal(0, 1, 60)
    y = (x > 0).astype(float)
    fig = regplot(None, x_vals=x.tolist(), y_vals=y.tolist(), logistic=True)
    assert "<circle" in fig.render_svg()

def test_regplot_dataframe():
    from glyphx.regplot import regplot
    df = pd.DataFrame({"ht": [160,165,170,175,180,185],
                       "wt": [55,60,68,72,80,88]})
    fig = regplot(df, x="ht", y="wt", n_boot=10)
    assert fig.axes.xlabel == "ht"
    assert "<circle" in fig.render_svg()

def test_regplot_no_ci():
    from glyphx.regplot import regplot
    from glyphx.fill_between import FillBetweenSeries
    x = RNG.normal(0, 1, 40)
    y = x + RNG.normal(0, 0.5, 40)
    fig = regplot(None, x_vals=x.tolist(), y_vals=y.tolist(), ci=0)
    has_fill = any(isinstance(s, FillBetweenSeries) for s, _ in fig.series)
    assert not has_fill, "ci=0 should produce no CI band"


# ── ChoroplethSeries ─────────────────────────────────────────────────────────

def _minimal_geojson():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "RegA"},
         "geometry": {"type": "Polygon",
                      "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}},
        {"type": "Feature", "properties": {"name": "RegB"},
         "geometry": {"type": "Polygon",
                      "coordinates": [[[1,0],[2,0],[2,1],[1,1],[1,0]]]}},
    ]}

def test_choropleth_renders_paths():
    from glyphx.choropleth import ChoroplethSeries
    geo = _minimal_geojson()
    fig = Figure(width=500, height=300, auto_display=False)
    fig.add(ChoroplethSeries(geo, {"RegA": 42, "RegB": 87}, key="name"))
    svg = fig.render_svg()
    assert "<path" in svg

def test_choropleth_multipolygon():
    from glyphx.choropleth import ChoroplethSeries
    geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"iso": "US"},
         "geometry": {"type": "MultiPolygon",
                      "coordinates": [[[[0,0],[1,0],[1,1],[0,1],[0,0]]],
                                      [[[2,2],[3,2],[3,3],[2,3],[2,2]]]]}},
    ]}
    fig = Figure(width=500, height=300, auto_display=False)
    fig.add(ChoroplethSeries(geo, {"US": 55000}, key="iso"))
    assert "<path" in fig.render_svg()

def test_choropleth_missing_data_color():
    from glyphx.choropleth import ChoroplethSeries
    geo = _minimal_geojson()
    cs  = ChoroplethSeries(geo, {"RegA": 100}, key="name",
                            missing_color="#cccccc")
    assert cs.missing_color == "#cccccc"

def test_figure_choropleth_shorthand():
    from glyphx.choropleth import ChoroplethSeries
    geo = _minimal_geojson()
    fig = Figure(width=500, height=300, auto_display=False)
    result = fig.choropleth(geo, {"RegA": 42, "RegB": 87}, key="name")
    assert result is fig


# ── Vega-Lite export ──────────────────────────────────────────────────────────

def test_vega_lite_basic():
    from glyphx.vega_lite import to_vega_lite
    fig = Figure(auto_display=False).set_title("Test")
    fig.add(LineSeries([1,2,3],[4,5,6], label="L"))
    spec = to_vega_lite(fig)
    assert spec["$schema"].startswith("https://vega.github.io")
    assert spec["title"] == "Test"
    assert "line" in json.dumps(spec)

def test_vega_lite_save():
    from glyphx.vega_lite import save_vega_lite
    fig = Figure(auto_display=False)
    fig.add(BarSeries(["A","B"],[1,2]))
    with tempfile.NamedTemporaryFile(suffix=".vl.json", delete=False) as f:
        path = f.name
    try:
        save_vega_lite(fig, path)
        spec = json.load(open(path))
        assert "$schema" in spec
    finally:
        os.unlink(path)

def test_figure_to_vega_lite_method():
    fig = Figure(auto_display=False)
    fig.add(LineSeries([1,2,3],[4,5,6]))
    spec = fig.to_vega_lite()
    assert "$schema" in spec

def test_vega_lite_scatter():
    from glyphx.vega_lite import to_vega_lite
    x = RNG.normal(0,1,30).tolist()
    y = RNG.normal(0,1,30).tolist()
    c = RNG.normal(0,1,30).tolist()
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries(x, y, c=c, cmap="plasma"))
    spec = to_vega_lite(fig)
    j = json.dumps(spec)
    assert "point" in j
    assert "quantitative" in j


# ── render_responsive ─────────────────────────────────────────────────────────

def test_render_responsive_contains_css_vars():
    fig = Figure(auto_display=False)
    fig.add(LineSeries([1,2,3],[4,5,6]))
    svg = fig.render_responsive(dark_theme="dark")
    assert "--glyphx-bg" in svg
    assert "prefers-color-scheme" in svg

def test_render_responsive_is_valid_svg():
    fig = Figure(auto_display=False)
    fig.add(LineSeries([1,2,3],[4,5,6]))
    svg = fig.render_responsive()
    assert svg.startswith("<svg")
    assert svg.strip().endswith("</svg>")


# ── StackedBarSeries ──────────────────────────────────────────────────────────

def test_stacked_bar_renders():
    from glyphx.stacked_bar import StackedBarSeries
    fig = Figure(auto_display=False)
    fig.add(StackedBarSeries(
        x=["Q1","Q2","Q3"],
        series={"A":[1,2,3],"B":[4,5,6]},
    ))
    svg = fig.render_svg()
    assert "<rect" in svg

def test_stacked_bar_normalize():
    from glyphx.stacked_bar import StackedBarSeries
    fig = Figure(auto_display=False)
    fig.add(StackedBarSeries(
        x=["Q1","Q2"],
        series={"A":[10,20],"B":[30,40]},
        normalize=True,
    ))
    assert "<rect" in fig.render_svg()

def test_figure_stacked_bar_shorthand():
    fig = Figure(auto_display=False)
    result = fig.stacked_bar(x=["A","B"],
                              series={"X":[1,2],"Y":[3,4]})
    assert result is fig


# ── BumpChartSeries ───────────────────────────────────────────────────────────

def test_bump_chart_renders():
    from glyphx.bump_chart import BumpChartSeries
    fig = Figure(auto_display=False)
    fig.add(BumpChartSeries(
        x=["2020","2021","2022"],
        rankings={"Lib A":[1,2,1],"Lib B":[2,1,2]},
    ))
    svg = fig.render_svg()
    assert "<polyline" in svg or "<path" in svg or "<circle" in svg

def test_figure_bump_shorthand():
    fig = Figure(auto_display=False)
    result = fig.bump(x=["A","B"],
                      rankings={"X":[1,2],"Y":[2,1]})
    assert result is fig


# ── SparklineSeries ───────────────────────────────────────────────────────────

def test_sparkline_series_renders():
    from glyphx.sparkline import SparklineSeries
    fig = Figure(width=120, height=40, auto_display=False)
    fig.add(SparklineSeries([1.2, 1.8, 1.5, 2.3, 2.7, 3.1]))
    svg = fig.render_svg()
    assert "<polyline" in svg or "<path" in svg

def test_sparkline_svg_standalone():
    from glyphx.sparkline import sparkline_svg
    svg = sparkline_svg([1, 3, 2, 5, 4, 6], width=80, height=28)
    assert svg.startswith("<svg") or "<polyline" in svg

def test_sparkline_bar_kind():
    from glyphx.sparkline import sparkline_svg
    svg = sparkline_svg([1, 2, 3, 2, 1], kind="bar", width=80, height=28)
    assert "<rect" in svg or "<svg" in svg


def test_scatter_sizes_varying_radii():
    """sizes= must produce genuinely different r= values in SVG."""
    import re
    sizes = [4.0, 8.0, 16.0]
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1,2,3], [1,2,3], sizes=sizes))
    svg = fig.render_svg()
    radii = re.findall(r'<circle[^>]*r="([^"]+)"', svg)
    assert len(set(radii)) == 3, f"Expected 3 distinct radii, got: {radii}"


def test_scatter_style_mixed_shapes():
    """style= must produce both <circle> and <rect> elements."""
    styles = ["circle", "square", "circle", "square"]
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1,2,3,4], [1,2,3,4], style=styles, size=8))
    svg = fig.render_svg()
    assert "<circle" in svg, "Expected circle markers"
    assert "<rect"   in svg, "Expected square markers"


def test_scatter_default_size_unchanged():
    """When sizes= is None the default self.size must still be used."""
    import re
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1,2,3], [1,2,3], size=7))
    svg = fig.render_svg()
    radii = re.findall(r'<circle[^>]*r="([^"]+)"', svg)
    assert all(r == "7" for r in radii), f"Expected all radii=7, got {radii}"
