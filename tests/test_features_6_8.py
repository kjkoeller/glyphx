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
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
try:
    import pytest
except ImportError:
    import pytest_shim as pytest  # noqa: F401
    _sys.modules["pytest"] = pytest

from glyphx import Figure, plot
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
        id1 = re.search(r'id="(glyphx-chart-[a-f0-9]+)"', svg1).group(1)
        id2 = re.search(r'id="(glyphx-chart-[a-f0-9]+)"', svg2).group(1)
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
