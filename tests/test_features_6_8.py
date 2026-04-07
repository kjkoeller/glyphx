"""
Tests for the three new GlyphX features:
  Feature 6  – Linked Brushing (SVG data-glyphx tags, brush.js present)
  Feature 7  – Natural Language chart generation (from_prompt)
  Feature 8 – Self-contained shareable HTML (fig.share())
"""

import json
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from glyphx import Figure, from_prompt, plot
from glyphx.series import LineSeries, BarSeries
from glyphx.utils import make_shareable_html, wrap_svg_canvas
from glyphx.nlp import _build_figure, _parse_json


# ============================================================
# Feature 6 — Linked Brushing
# ============================================================

class TestLinkedBrushing:

    def test_svg_has_data_glyphx_attribute(self):
        """Every rendered SVG must carry data-glyphx so brush.js can find it."""
        fig = Figure(auto_display=False)
        fig.add(LineSeries([1, 2, 3], [4, 5, 6]))
        svg = fig.render_svg()
        assert 'data-glyphx="true"' in svg

    def test_svg_has_unique_id(self):
        """Each SVG should have a unique glyphx-chart-N id."""
        fig1 = Figure(auto_display=False)
        fig1.add(LineSeries([1, 2], [3, 4]))
        fig2 = Figure(auto_display=False)
        fig2.add(BarSeries([1, 2], [5, 6]))
        svg1 = fig1.render_svg()
        svg2 = fig2.render_svg()
        id1 = re.search(r'id="(glyphx-chart-\d+)"', svg1).group(1)
        id2 = re.search(r'id="(glyphx-chart-\d+)"', svg2).group(1)
        assert id1 != id2

    def test_glyphx_points_have_data_x(self):
        """All interactive points must carry data-x for brushing cross-chart linking."""
        fig = Figure(auto_display=False)
        fig.add(LineSeries([10, 20, 30], [1, 2, 3], label="s"))
        svg = fig.render_svg()
        # Find all data-x values
        xs = re.findall(r'data-x="([^"]+)"', svg)
        assert len(xs) == 3
        assert "10" in xs and "20" in xs and "30" in xs

    def test_bar_series_has_data_x(self):
        fig = Figure(auto_display=False)
        fig.add(BarSeries(["A", "B", "C"], [10, 20, 30], label="b"))
        svg = fig.render_svg()
        xs = re.findall(r'data-x="([^"]+)"', svg)
        assert "A" in xs and "B" in xs

    def test_brush_js_exists(self):
        """brush.js must be present in the assets directory."""
        brush_path = Path(__file__).parent.parent / "glyphx" / "assets" / "brush.js"
        assert brush_path.exists(), "brush.js not found in assets"

    def test_brush_js_contains_shift_drag(self):
        """Brush should activate only on Shift+drag, not plain drag."""
        brush_js = (Path(__file__).parent.parent / "glyphx" / "assets" / "brush.js").read_text()
        assert "shiftKey" in brush_js

    def test_brush_js_applies_selection_across_charts(self):
        """Linked brushing must dim ALL .glyphx-point elements, not just one chart."""
        brush_js = (Path(__file__).parent.parent / "glyphx" / "assets" / "brush.js").read_text()
        assert "querySelectorAll('.glyphx-point')" in brush_js

    def test_zoom_js_skips_shift_drag(self):
        """zoom.js must yield to brush when Shift is held."""
        zoom_js = (Path(__file__).parent.parent / "glyphx" / "assets" / "zoom.js").read_text()
        assert "shiftKey" in zoom_js

    def test_html_output_includes_brush_js(self):
        """wrap_svg_with_template must embed brush.js in the output HTML."""
        from glyphx.utils import wrap_svg_with_template
        html = wrap_svg_with_template("<svg></svg>")
        assert "glyphx-brush" in html or "shiftKey" in html

    def test_escape_clears_selection_in_js(self):
        """Escape key must clear selection."""
        brush_js = (Path(__file__).parent.parent / "glyphx" / "assets" / "brush.js").read_text()
        assert "Escape" in brush_js

    def test_multiple_svgs_all_tagged(self):
        """grid() output must tag every SVG so all participate in brushing."""
        from glyphx.layout import grid
        f1 = Figure(auto_display=False)
        f1.add(LineSeries([1, 2, 3], [4, 5, 6]))
        f2 = Figure(auto_display=False)
        f2.add(BarSeries([1, 2, 3], [7, 8, 9]))
        html = grid([f1, f2], rows=1, cols=2)
        count = html.count('data-glyphx="true"')
        assert count >= 2


# ============================================================
# Feature 7 — Natural Language Chart Generation
# ============================================================

class TestFromPrompt:

    # ── JSON parsing ─────────────────────────────────────────────

    def test_parse_json_clean(self):
        raw = '{"kind": "bar", "x": "month", "y": "sales"}'
        cfg = _parse_json(raw)
        assert cfg["kind"] == "bar"

    def test_parse_json_strips_fences(self):
        raw = '```json\n{"kind": "line"}\n```'
        cfg = _parse_json(raw)
        assert cfg["kind"] == "line"

    def test_parse_json_strips_fences_no_lang(self):
        raw = '```\n{"kind": "scatter"}\n```'
        cfg = _parse_json(raw)
        assert cfg["kind"] == "scatter"

    def test_parse_json_invalid_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json("not json at all")

    # ── _build_figure without DataFrame ─────────────────────────

    def test_build_figure_line_no_df(self):
        cfg = {"kind": "line", "title": "Test"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        assert isinstance(fig, Figure)
        svg = fig.render_svg()
        assert "<svg" in svg

    def test_build_figure_bar_no_df(self):
        cfg = {"kind": "bar"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_build_figure_scatter_no_df(self):
        cfg = {"kind": "scatter"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "circle" in svg

    def test_build_figure_pie_no_df(self):
        cfg = {"kind": "pie"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "<path" in svg

    def test_build_figure_donut_no_df(self):
        cfg = {"kind": "donut"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "<path" in svg

    def test_build_figure_hist_no_df(self):
        cfg = {"kind": "hist", "bins": 8}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_build_figure_box_no_df(self):
        cfg = {"kind": "box"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "<svg" in svg

    # ── _build_figure with DataFrame ────────────────────────────

    def _sample_df(self):
        import pandas as pd
        return pd.DataFrame({
            "month":   ["Jan", "Feb", "Mar", "Apr", "May"],
            "sales":   [120, 135, 98, 170, 145],
            "region":  ["North", "South", "North", "South", "North"],
        })

    def test_build_figure_line_with_df(self):
        df  = self._sample_df()
        cfg = {"kind": "line", "x": "month", "y": "sales"}
        fig = _build_figure(cfg, df=df, auto_display=False)
        svg = fig.render_svg()
        assert "polyline" in svg

    def test_build_figure_bar_with_df(self):
        df  = self._sample_df()
        cfg = {"kind": "bar", "x": "month", "y": "sales"}
        fig = _build_figure(cfg, df=df, auto_display=False)
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_build_figure_scatter_with_df(self):
        import pandas as pd
        df  = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [4.0, 5.0, 6.0]})
        cfg = {"kind": "scatter", "x": "x", "y": "y"}
        fig = _build_figure(cfg, df=df, auto_display=False)
        svg = fig.render_svg()
        assert "circle" in svg

    def test_build_figure_groupby(self):
        df  = self._sample_df()
        cfg = {"kind": "bar", "groupby": "region", "y": "sales", "agg": "sum"}
        fig = _build_figure(cfg, df=df, auto_display=False)
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_build_figure_groupby_multi_series(self):
        df  = self._sample_df()
        cfg = {"kind": "line", "x": "month", "y": "sales", "groupby": "region"}
        fig = _build_figure(cfg, df=df, auto_display=False)
        # Should add one LineSeries per region
        assert len(fig.series) == 2

    def test_build_figure_top_n(self):
        import pandas as pd
        df  = pd.DataFrame({
            "product": [f"P{i}" for i in range(20)],
            "revenue": list(range(20)),
        })
        cfg = {"kind": "bar", "x": "product", "y": "revenue",
               "top_n": 5, "sort_by": "y", "sort_desc": True}
        fig = _build_figure(cfg, df=df, auto_display=False)
        # Should have exactly 5 bars
        from glyphx.series import BarSeries
        bar = next(s for s, _ in fig.series if isinstance(s, BarSeries))
        assert len(bar.x) == 5

    def test_build_figure_theme_applied(self):
        cfg = {"kind": "line", "theme": "dark"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        assert fig.theme.get("background") == "#1e1e1e"

    def test_build_figure_title_propagated(self):
        cfg = {"kind": "bar", "title": "My NLP Chart"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "My NLP Chart" in svg

    def test_build_figure_xlabel_ylabel(self):
        cfg = {"kind": "line", "xlabel": "Time", "ylabel": "Value"}
        fig = _build_figure(cfg, df=None, auto_display=False)
        svg = fig.render_svg()
        assert "Time" in svg
        assert "Value" in svg

    def test_build_figure_hist_with_df(self):
        import pandas as pd
        df  = pd.DataFrame({"score": list(range(100))})
        cfg = {"kind": "hist", "y": "score", "bins": 10}
        fig = _build_figure(cfg, df=df, auto_display=False)
        svg = fig.render_svg()
        assert "<rect" in svg

    def test_build_figure_pie_with_df(self):
        import pandas as pd
        df  = pd.DataFrame({"cat": ["A", "B", "C"], "val": [10, 20, 30]})
        cfg = {"kind": "pie", "x": "cat", "y": "val"}
        fig = _build_figure(cfg, df=df, auto_display=False)
        svg = fig.render_svg()
        assert "<path" in svg

    # ── from_prompt() API surface ────────────────────────────────

    def test_from_prompt_missing_anthropic_raises(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises((ImportError, TypeError)):
                from_prompt("bar chart", api_key="fake")

    def test_from_prompt_no_api_key_raises(self):
        # Ensure env var is absent
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            # Only raises if anthropic IS importable; skip otherwise
            try:
                import anthropic  # noqa: F401
            except ImportError:
                pytest.skip("anthropic not installed")
            with pytest.raises(ValueError, match="API key"):
                from_prompt("bar chart", api_key=None)

    def test_from_prompt_mocked_api(self):
        """Full from_prompt() call with mocked Anthropic response."""
        try:
            import anthropic  # noqa: F401
        except ImportError:
            pytest.skip("anthropic not installed")

        fake_config = {
            "kind": "bar", "x": "month", "y": "sales",
            "title": "Sales by Month", "theme": "default",
            "reasoning": "Bar chart suits monthly comparisons",
        }
        mock_text    = MagicMock()
        mock_text.text = json.dumps(fake_config)
        mock_resp    = MagicMock()
        mock_resp.content = [mock_text]
        mock_client  = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        import pandas as pd
        df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "sales": [100, 200, 150]})

        with patch("anthropic.Anthropic", return_value=mock_client):
            fig = from_prompt("bar chart of monthly sales", df=df,
                              api_key="test_key", auto_display=False)

        assert isinstance(fig, Figure)
        svg = fig.render_svg()
        assert "<rect" in svg
        assert "Sales by Month" in svg


# ============================================================
# Feature 8 — Self-Contained Shareable HTML
# ============================================================

class TestShareableHTML:

    def _basic_figure(self):
        fig = Figure(auto_display=False)
        fig.add(LineSeries([1, 2, 3], [4, 5, 6], label="test"))
        return fig

    # ── make_shareable_html() ────────────────────────────────────

    def test_make_shareable_html_returns_string(self):
        fig  = self._basic_figure()
        svg  = fig.render_svg()
        html = make_shareable_html(svg)
        assert isinstance(html, str)

    def test_shareable_html_is_valid_html(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg())
        assert "<!DOCTYPE html>" in html or "<!--" in html
        assert "<html" in html
        assert "</html>" in html

    def test_shareable_html_contains_svg(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg())
        assert "<svg" in html

    def test_shareable_html_has_no_external_cdn(self):
        """Zero external dependencies — no cdnjs, unpkg, jsdelivr, etc."""
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg())
        for cdn in ["cdnjs.cloudflare.com", "unpkg.com", "jsdelivr.net",
                    "ajax.googleapis.com", "cdn.jsdelivr.net"]:
            assert cdn not in html, f"CDN reference found: {cdn}"

    def test_shareable_html_inlines_zoom_js(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg())
        assert "viewBox" in html   # zoom.js uses viewBox

    def test_shareable_html_inlines_brush_js(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg())
        assert "shiftKey" in html  # brush.js checks Shift key

    def test_shareable_html_custom_title(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg(), title="Revenue Q3 2025")
        assert "Revenue Q3 2025" in html

    def test_shareable_html_has_metadata_comment(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg())
        assert "GlyphX self-contained export" in html

    def test_shareable_html_xss_in_title_escaped(self):
        fig  = self._basic_figure()
        html = make_shareable_html(fig.render_svg(), title='<script>alert(1)</script>')
        assert "<script>alert" not in html

    # ── Figure.share() ───────────────────────────────────────────

    def test_figure_share_returns_string(self):
        fig  = self._basic_figure()
        html = fig.share()
        assert isinstance(html, str)
        assert "<svg" in html

    def test_figure_share_saves_file(self, tmp_path):
        fig  = self._basic_figure()
        path = str(tmp_path / "shared.html")
        fig.share(path)
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "<svg" in content
        assert "<!DOCTYPE" in content or "<!--" in content

    def test_figure_share_uses_figure_title(self):
        fig  = Figure(title="My Dashboard", auto_display=False)
        fig.add(LineSeries([1, 2], [3, 4]))
        html = fig.share()
        assert "My Dashboard" in html

    def test_figure_share_works_without_filename(self):
        fig  = self._basic_figure()
        # Must not raise even without a filename argument
        html = fig.share()
        assert len(html) > 100

    def test_figure_share_no_cdn(self):
        fig  = self._basic_figure()
        html = fig.share()
        for cdn in ["cdnjs.cloudflare.com", "unpkg.com", "jsdelivr.net"]:
            assert cdn not in html

    def test_figure_share_has_tooltip_js(self):
        """Tooltip JS must be present in the shared output."""
        fig  = self._basic_figure()
        html = fig.share()
        # tooltip code shows data-x or data-y
        assert "glyphx-tooltip" in html or "data-x" in html

    def test_figure_share_has_download_buttons(self):
        fig  = self._basic_figure()
        html = fig.share()
        assert "Download SVG" in html or "glyphxDownload" in html

    def test_figure_share_roundtrip(self, tmp_path):
        """Save → read back → confirm SVG content intact."""
        fig  = Figure(title="RoundTrip", auto_display=False)
        fig.add(BarSeries(["A", "B", "C"], [1, 2, 3]))
        path = str(tmp_path / "rt.html")
        fig.share(path)
        content = open(path, encoding="utf-8").read()
        assert "RoundTrip" in content
        assert "<rect" in content  # bar rects present
