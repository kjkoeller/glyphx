"""
GlyphX v1.5.0 — SVG-first Python plotting library.

Beats Matplotlib, Seaborn, and Plotly across three axes:

  vs Matplotlib  → responsive layout, tight_layout, typed API, accessibility,
                   DataFrame accessor, method chaining
  vs Seaborn     → statistical annotations, ECDF, raincloud, perceptually-
                   uniform colormaps, continuous color encoding in scatter
  vs Plotly      → candlestick/OHLC, waterfall, treemap, streaming series,
                   synchronized crosshair — with zero server dependency

Quick-start::

    from glyphx import plot, from_prompt

    # Classic
    plot([1,2,3],[4,5,6], kind="bar", title="Revenue")

    # Chained
    (Figure().set_theme("dark").set_title("Rev")
             .add(LineSeries(x, y))
             .tight_layout()
             .share("report.html"))

    # DataFrame accessor
    df.glyphx.bar(x="month", y="revenue").add_stat_annotation("Jan","Mar",0.01)

    # NLP  (pip install anthropic)
    from_prompt("top 10 products by revenue", df=df)
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("glyphx")
except PackageNotFoundError:
    # Package is not installed (e.g. running from source without install)
    __version__ = "unknown"

# ── Core ──────────────────────────────────────────────────────────────────
from .figure   import Figure, SubplotGrid
from .layout   import Axes, grid
from .themes   import themes
from .utils    import normalize
from .plot     import plot
from .nlp      import from_prompt
from .colormaps import (
    apply_colormap,
    colormap_colors,
    list_colormaps,
    get_colormap,
)

# ── Core series ───────────────────────────────────────────────────────────
from .series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    HeatmapSeries, BoxPlotSeries,
)

# ── Statistical / distribution ────────────────────────────────────────────
from .ecdf          import ECDFSeries
from .fill_between  import FillBetweenSeries
from .kde           import KDESeries
from .raincloud     import RaincloudSeries
from .stat_annotation import StatAnnotation, pvalue_to_label
from .violin_plot   import ViolinPlotSeries

# ── Financial ────────────────────────────────────────────────────────────
from .candlestick   import CandlestickSeries
from .waterfall     import WaterfallSeries

# ── Hierarchical ─────────────────────────────────────────────────────────
from .treemap       import TreemapSeries

# ── Streaming / real-time ────────────────────────────────────────────────
from .streaming     import StreamingSeries

# ── Advanced chart types ──────────────────────────────────────────────────
from .grouped_bar  import GroupedBarSeries
from .swarm_plot   import SwarmPlotSeries
from .count_plot   import CountPlotSeries

# ── Seaborn-style composites ──────────────────────────────────────────────
from .facet_plot   import facet_plot
from .pairplot     import pairplot
from .jointplot    import jointplot
from .lmplot       import lmplot

# ── Register pandas accessor (df.glyphx.*) ────────────────────────────────
from . import accessor as _accessor  # noqa: F401

__all__ = [
    # Core
    "Figure", "SubplotGrid", "Axes", "grid", "themes", "normalize",
    "plot", "from_prompt",
    # Colormaps
    "apply_colormap", "colormap_colors", "list_colormaps", "get_colormap",
    # Base series
    "LineSeries", "BarSeries", "ScatterSeries",
    "PieSeries", "DonutSeries", "HistogramSeries",
    "HeatmapSeries", "BoxPlotSeries",
    # Statistical
    "ECDFSeries", "RaincloudSeries", "ViolinPlotSeries",
    "StatAnnotation", "pvalue_to_label",
    # Financial
    "CandlestickSeries", "WaterfallSeries",
    # Hierarchical
    "TreemapSeries",
    # Streaming
    "StreamingSeries",
    # Advanced
    "GroupedBarSeries", "SwarmPlotSeries", "CountPlotSeries",
    # Composites
    "facet_plot", "pairplot", "jointplot", "lmplot",
]
