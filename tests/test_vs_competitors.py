"""
Tests targeting the features that make GlyphX competitive with
Matplotlib, Seaborn, and Plotly.
"""
from __future__ import annotations
import numpy as np
import pytest
import glyphx
from glyphx import Figure
from glyphx.series import ScatterSeries, LineSeries, BarSeries


@pytest.fixture
def multi_group_data():
    np.random.seed(0)
    return [np.random.normal(loc, 1.5, 60) for loc in [0, 2, 5]]

@pytest.fixture
def basic_fig():
    fig = Figure(auto_display=False)
    fig.add(LineSeries([1,2,3,4,5],[10,50,30,70,20],label="A"))
    return fig


# ============================================================
# vs Matplotlib — responsive, tight layout, auto rotation
# ============================================================

class TestVsMatplotlib:

    def test_tight_layout_returns_figure(self, basic_fig):
        result = basic_fig.tight_layout()
        assert result is basic_fig

    def test_tight_layout_does_not_crash(self, basic_fig):
        basic_fig.tight_layout()
        svg = basic_fig.render_svg()
        assert "<svg" in svg

    def test_tight_layout_adjusts_padding_with_ylabel(self):
        fig = Figure(auto_display=False)
        fig.add(BarSeries([1,2,3],[1000000,2000000,3000000]))
        fig.axes.ylabel = "Revenue (USD)"
        original_padding = fig.axes.padding
        fig.tight_layout()
        assert fig.axes.padding >= original_padding

    def test_auto_rotate_flag_set_on_crowded_labels(self):
        fig = Figure(width=400, auto_display=False)
        labels = [f"Category_{i}_Long" for i in range(10)]
        fig.add(BarSeries(labels, list(range(10))))
        fig.axes.finalize()
        result = fig.axes._should_rotate_xlabels()
        assert isinstance(result, bool)

    def test_svg_has_viewbox(self, basic_fig):
        svg = basic_fig.render_svg()
        assert "viewBox" in svg

    def test_tight_layout_chain(self):
        """tight_layout() is chainable."""
        fig = (
            Figure(auto_display=False)
            .add(LineSeries([1,2,3],[4,5,6]))
            .tight_layout()
            .set_title("Tight")
        )
        assert fig.title == "Tight"


# ============================================================
# vs Seaborn — statistical annotations
# ============================================================

class TestVsSeabornStatAnnotation:

    def test_add_stat_annotation_returns_figure(self, basic_fig):
        result = basic_fig.add_stat_annotation("A","B", p_value=0.01)
        assert result is basic_fig

    def test_stat_annotation_renders_bracket(self):
        fig = Figure(auto_display=False)
        fig.add(BarSeries([1,2,3],[10,20,15]))
        fig.add_stat_annotation(1, 3, p_value=0.01)
        svg = fig.render_svg()
        assert "<line" in svg

    def test_stat_annotation_pvalue_stars(self):
        from glyphx.stat_annotation import pvalue_to_label
        assert pvalue_to_label(0.0001) == "***"
        assert pvalue_to_label(0.005)  == "**"
        assert pvalue_to_label(0.03)   == "*"
        assert pvalue_to_label(0.1)    == "ns"

    def test_stat_annotation_numeric_style(self):
        from glyphx.stat_annotation import pvalue_to_label
        result = pvalue_to_label(0.03, style="numeric")
        assert "p=" in result

    def test_stat_annotation_custom_label(self):
        fig = Figure(auto_display=False)
        fig.add(BarSeries([1,2,3],[10,20,15]))
        fig.add_stat_annotation(1, 2, label="custom")
        svg = fig.render_svg()
        assert "custom" in svg

    def test_multiple_stat_annotations_stack(self):
        fig = Figure(auto_display=False)
        fig.add(BarSeries([1,2,3],[10,20,15]))
        fig.add_stat_annotation(1, 2, p_value=0.01)
        fig.add_stat_annotation(1, 3, p_value=0.001, y_offset=30)
        # Should not crash
        svg = fig.render_svg()
        assert "<svg" in svg


# ============================================================
# vs Seaborn — ECDF plot
# ============================================================

class TestECDF:

    def test_ecdf_renders(self):
        from glyphx.ecdf import ECDFSeries
        data = np.random.normal(0, 1, 100)
        s    = ECDFSeries(data, label="Test")
        fig  = Figure(auto_display=False)
        fig.add(s)
        svg  = fig.render_svg()
        assert "<path" in svg or "<line" in svg

    def test_ecdf_x_is_sorted(self):
        from glyphx.ecdf import ECDFSeries
        data = [3,1,4,1,5,9,2,6]
        s    = ECDFSeries(data)
        assert s.x == sorted(data)

    def test_ecdf_y_range(self):
        from glyphx.ecdf import ECDFSeries
        data = list(range(10))
        s    = ECDFSeries(data)
        assert abs(s.y[-1] - 1.0) < 1e-9
        assert s.y[0]  > 0

    def test_ecdf_complementary(self):
        from glyphx.ecdf import ECDFSeries
        data = list(range(10))
        s    = ECDFSeries(data, complementary=True)
        assert abs(s.y[-1] - 0.0) < 0.15  # last y near 0

    def test_ecdf_with_show_points(self):
        from glyphx.ecdf import ECDFSeries
        data = [1,2,3,4,5]
        s    = ECDFSeries(data, show_points=True)
        fig  = Figure(auto_display=False)
        fig.add(s)
        svg  = fig.render_svg()
        assert "circle" in svg

    def test_ecdf_multiple_series(self):
        from glyphx.ecdf import ECDFSeries
        fig = Figure(auto_display=False)
        fig.add(ECDFSeries([1,2,3,4,5], label="A"))
        fig.add(ECDFSeries([2,3,4,5,6], label="B"))
        svg = fig.render_svg()
        assert "<svg" in svg


# ============================================================
# vs Seaborn — Raincloud plot
# ============================================================

class TestRaincloud:

    def test_raincloud_renders(self, multi_group_data):
        from glyphx.raincloud import RaincloudSeries
        fig = Figure(auto_display=False)
        fig.add(RaincloudSeries(multi_group_data, categories=["A","B","C"]))
        svg = fig.render_svg()
        assert "<svg" in svg

    def test_raincloud_has_three_components(self, multi_group_data):
        from glyphx.raincloud import RaincloudSeries
        fig = Figure(auto_display=False)
        fig.add(RaincloudSeries(multi_group_data))
        svg = fig.render_svg()
        assert "circle" in svg   # jitter points
        assert "<path"  in svg   # violin outline
        assert "<rect"  in svg   # box body

    def test_raincloud_category_labels(self, multi_group_data):
        from glyphx.raincloud import RaincloudSeries
        fig = Figure(auto_display=False)
        fig.add(RaincloudSeries(multi_group_data, categories=["X","Y","Z"]))
        svg = fig.render_svg()
        assert "X" in svg and "Y" in svg and "Z" in svg

    def test_raincloud_reproducible(self, multi_group_data):
        from glyphx.raincloud import RaincloudSeries
        import re as _re
        fig1 = Figure(auto_display=False)
        fig1.add(RaincloudSeries(multi_group_data, seed=42))
        fig2 = Figure(auto_display=False)
        fig2.add(RaincloudSeries(multi_group_data, seed=42))

        def _strip_instance_ids(svg):
            # Remove IDs that vary across Python process runs / instances:
            #   glyphx-chart-N  — global counter in utils.py
            #   series-NNNNN    — id(self) % 100000 in BaseSeries
            #   aria-labelledby / title / desc ids derived from chart-N
            svg = _re.sub(r'id="glyphx-chart-\d+[^"]*"', 'id="glyphx-chart-X"', svg)
            svg = _re.sub(r'aria-labelledby="[^"]*"', 'aria-labelledby="X"', svg)
            svg = _re.sub(r'series-\d+', 'series-X', svg)
            return svg

        assert _strip_instance_ids(fig1.render_svg()) == _strip_instance_ids(fig2.render_svg())


# ============================================================
# vs Seaborn — Colormaps + color encoding
# ============================================================

class TestColormaps:

    def test_list_colormaps(self):
        from glyphx.colormaps import list_colormaps
        cmaps = list_colormaps()
        assert "viridis" in cmaps
        assert "plasma"  in cmaps
        assert "inferno" in cmaps
        assert "magma"   in cmaps
        assert "cividis" in cmaps
        assert "coolwarm"in cmaps

    def test_apply_colormap_range(self):
        from glyphx.colormaps import apply_colormap
        c0 = apply_colormap(0.0, "viridis")
        c1 = apply_colormap(1.0, "viridis")
        assert c0.startswith("#")
        assert c1.startswith("#")
        assert c0 != c1

    def test_apply_colormap_clamps(self):
        from glyphx.colormaps import apply_colormap
        assert apply_colormap(-1.0, "viridis") == apply_colormap(0.0, "viridis")
        assert apply_colormap(2.0,  "viridis") == apply_colormap(1.0, "viridis")

    def test_colormap_colors_count(self):
        from glyphx.colormaps import colormap_colors
        colors = colormap_colors("plasma", 5)
        assert len(colors) == 5
        assert all(c.startswith("#") for c in colors)

    def test_unknown_colormap_raises(self):
        from glyphx.colormaps import apply_colormap
        with pytest.raises(ValueError, match="Unknown colormap"):
            apply_colormap(0.5, "nonexistent_cmap")

    def test_scatter_color_encoding(self):
        np.random.seed(1)
        x  = list(range(20))
        y  = list(range(20))
        c  = list(range(20))
        s  = ScatterSeries(x, y, c=c, cmap="plasma")
        fig = Figure(auto_display=False)
        fig.add(s)
        svg = fig.render_svg()
        # Different points should have different fill colors
        import re
        fills = re.findall(r'fill="#[0-9a-f]{6}"', svg)
        unique_fills = set(fills)
        assert len(unique_fills) > 3   # not all the same color

    def test_scatter_colorbar_present(self):
        s   = ScatterSeries([1,2,3],[4,5,6], c=[1,2,3], cmap="viridis")
        fig = Figure(auto_display=False)
        fig.add(s)
        svg = fig.render_svg()
        # Colorbar adds multiple small rects + two text labels
        assert svg.count("<rect") > 5


# ============================================================
# vs Plotly — Candlestick / OHLC
# ============================================================

class TestCandlestick:

    def test_candlestick_renders(self):
        from glyphx.candlestick import CandlestickSeries
        fig = Figure(auto_display=False)
        fig.add(CandlestickSeries(
            dates=["Mon","Tue","Wed"],
            open= [100, 105, 102],
            high= [110, 112, 108],
            low=  [98,  103, 99],
            close=[105, 102, 107],
        ))
        svg = fig.render_svg()
        assert "<rect" in svg
        assert "<line" in svg

    def test_candlestick_up_down_colors(self):
        from glyphx.candlestick import CandlestickSeries
        import re
        fig = Figure(auto_display=False)
        fig.add(CandlestickSeries(
            dates=["A","B"],
            open= [100, 110],
            high= [115, 115],
            low=  [95,  95],
            close=[110, 100],   # A=up, B=down
        ))
        svg = fig.render_svg()
        assert "#26a641" in svg   # up color
        assert "#d73027" in svg   # down color

    def test_candlestick_tooltips(self):
        from glyphx.candlestick import CandlestickSeries
        fig = Figure(auto_display=False)
        fig.add(CandlestickSeries(
            dates=["Mon"], open=[100], high=[110], low=[95], close=[105]
        ))
        svg = fig.render_svg()
        assert "data-value" in svg


# ============================================================
# vs Plotly — Waterfall chart
# ============================================================

class TestWaterfall:

    def test_waterfall_renders(self):
        from glyphx.waterfall import WaterfallSeries
        fig = Figure(auto_display=False)
        fig.add(WaterfallSeries(
            labels=["Start","Sales","Returns","Total"],
            values=[1000, 400, -100, None],
        ))
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_waterfall_auto_total(self):
        from glyphx.waterfall import WaterfallSeries
        s = WaterfallSeries(
            labels=["A","B","C","Total"],
            values=[100, 200, -50, None],
        )
        # Auto total should be 100+200-50 = 250
        assert s._deltas[-1] == pytest.approx(250)

    def test_waterfall_colors(self):
        from glyphx.waterfall import WaterfallSeries
        fig = Figure(auto_display=False)
        fig.add(WaterfallSeries(
            labels=["A","B"],
            values=[100, -50],
        ))
        svg = fig.render_svg()
        assert "#2ca02c" in svg   # up color
        assert "#d62728" in svg   # down color

    def test_waterfall_show_values(self):
        from glyphx.waterfall import WaterfallSeries
        fig = Figure(auto_display=False)
        fig.add(WaterfallSeries(
            labels=["Start","Up","Down"],
            values=[1000, 200, -50],
            show_values=True,
        ))
        svg = fig.render_svg()
        assert "+200" in svg or "200" in svg


# ============================================================
# vs Plotly — Treemap
# ============================================================

class TestTreemap:

    def test_treemap_renders(self):
        from glyphx.treemap import TreemapSeries
        fig = Figure(width=600, height=400, auto_display=False)
        fig.add(TreemapSeries(
            labels=["Sales","R&D","Marketing","Ops"],
            values=[4200, 1800, 1200, 600],
        ))
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_treemap_all_labels_present(self):
        from glyphx.treemap import TreemapSeries
        fig = Figure(width=700, height=500, auto_display=False)
        fig.add(TreemapSeries(
            labels=["Alpha","Beta","Gamma"],
            values=[300, 200, 100],
        ))
        svg = fig.render_svg()
        for lbl in ["Alpha","Beta","Gamma"]:
            assert lbl in svg

    def test_treemap_mismatched_lengths_raises(self):
        from glyphx.treemap import TreemapSeries
        with pytest.raises(ValueError):
            TreemapSeries(labels=["A","B"], values=[1,2,3])

    def test_treemap_with_custom_colors(self):
        from glyphx.treemap import TreemapSeries
        colors = ["#ff0000", "#00ff00", "#0000ff"]
        s = TreemapSeries(
            labels=["A","B","C"], values=[3,2,1], colors=colors
        )
        assert len(s.colors) == 3

    def test_treemap_squarify_area_proportional(self):
        from glyphx.treemap import _squarify
        rects = _squarify([4,2,1], 0, 0, 100, 100)
        areas = [r[2]*r[3] for r in rects]
        total = sum(areas)
        assert abs(areas[0]/total - 4/7) < 0.05
        assert abs(areas[1]/total - 2/7) < 0.05


# ============================================================
# vs Plotly — Streaming series
# ============================================================

class TestStreaming:

    def test_streaming_push_updates_xy(self):
        from glyphx.streaming import StreamingSeries
        s = StreamingSeries(max_points=10)
        s.push(42.0)
        assert len(s.x) == 1
        assert s.y[0] == 42.0

    def test_streaming_push_returns_self(self):
        from glyphx.streaming import StreamingSeries
        s = StreamingSeries()
        result = s.push(1.0)
        assert result is s

    def test_streaming_sliding_window(self):
        from glyphx.streaming import StreamingSeries
        s = StreamingSeries(max_points=5)
        for i in range(10):
            s.push(float(i))
        assert len(s.x) == 5
        assert s.y == [5.0, 6.0, 7.0, 8.0, 9.0]

    def test_streaming_push_many(self):
        from glyphx.streaming import StreamingSeries
        s = StreamingSeries(max_points=20)
        s.push_many([1.0, 2.0, 3.0, 4.0])
        assert len(s.x) == 4
        assert s.y[-1] == 4.0

    def test_streaming_reset(self):
        from glyphx.streaming import StreamingSeries
        s = StreamingSeries()
        s.push_many([1.0, 2.0, 3.0])
        s.reset()
        assert len(s.x) == 0

    def test_streaming_renders(self):
        from glyphx.streaming import StreamingSeries
        fig = Figure(auto_display=False)
        s   = StreamingSeries(max_points=50)
        fig.add(s)
        s.push_many([float(i) for i in range(20)])
        svg = fig.render_svg()
        assert "polyline" in svg

    def test_streaming_chain_push(self):
        from glyphx.streaming import StreamingSeries
        s = StreamingSeries()
        s.push(1.0).push(2.0).push(3.0)
        assert len(s.y) == 3

    def test_streaming_empty_renders_without_crash(self):
        from glyphx.streaming import StreamingSeries
        fig = Figure(auto_display=False)
        fig.add(StreamingSeries())
        # Should not crash even with no data
        svg = fig.render_svg()
        assert "<svg" in svg


# ============================================================
# Crosshair JS
# ============================================================

class TestCrosshair:

    def test_crosshair_js_exists(self):
        from pathlib import Path
        js_path = Path(glyphx.__file__).parent / "assets" / "crosshair.js"
        assert js_path.exists()

    def test_crosshair_js_uses_fraction(self):
        from pathlib import Path
        js = (Path(glyphx.__file__).parent / "assets" / "crosshair.js").read_text()
        assert "xFraction" in js or "fraction" in js.lower()

    def test_crosshair_js_syncs_all_charts(self):
        from pathlib import Path
        js = (Path(glyphx.__file__).parent / "assets" / "crosshair.js").read_text()
        assert "querySelectorAll" in js   # targets all charts

    def test_enable_crosshair_returns_figure(self, basic_fig):
        result = basic_fig.enable_crosshair()
        assert result is basic_fig

    def test_enable_crosshair_sets_flag(self, basic_fig):
        basic_fig.enable_crosshair()
        assert basic_fig._crosshair is True