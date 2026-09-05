"""
GlyphX - SVG-first Python plotting library.

Beats Matplotlib, Seaborn, and Plotly across three axes:

  vs Matplotlib  → responsive layout, tight_layout, typed API, accessibility,
                   DataFrame accessor, method chaining
  vs Seaborn     → statistical annotations, ECDF, raincloud, perceptually-
                   uniform colormaps, continuous color encoding in scatter
  vs Plotly      → candlestick/OHLC, waterfall, treemap, streaming series,
                   synchronized crosshair - with zero server dependency

Quick-start::

    from glyphx import plot

    # Classic
    plot([1,2,3],[4,5,6], kind="bar", title="Revenue")

    # Chained
    (Figure().set_theme("dark").set_title("Rev")
             .add(LineSeries(x, y))
             .tight_layout()
             .share("report.html"))

    # DataFrame accessor
    df.glyphx.bar(x="month", y="revenue").add_stat_annotation("Jan","Mar",0.01)

"""

import contextlib as _contextlib
import importlib as _importlib
import importlib.abc as _importlib_abc  # noqa: F401  -- populates _importlib.abc
import importlib.util as _importlib_util  # noqa: F401  -- populates _importlib.util
import sys as _sys
import types as _types
from typing import TYPE_CHECKING as _TYPE_CHECKING

try:
    # Written at build time by setuptools_scm.
    from ._version import __version__
except ImportError:  # pragma: no cover - source checkout without an install
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    try:
        __version__ = _pkg_version("glyphx")
    except PackageNotFoundError:
        __version__ = "0.0.0.dev0"

# Core
from .colormaps import (
    apply_colormap,
    colormap_colors,
    get_colormap,
    list_colormaps,
)
from .figure import Figure, SubplotGrid
from .layout import Axes, grid
from .plot import plot

# Core series
from .series import (
    BarSeries,
    BoxPlotSeries,
    DonutSeries,
    HeatmapSeries,
    HistogramSeries,
    LineSeries,
    PieSeries,
    ScatterSeries,
)
from .themes import (
    get_theme,
    list_themes,
    register_theme,
    themes,
    unregister_theme,
)
from .utils import normalize

# Lazily loaded submodules
# Importing all ~50 chart modules up front cost ~0.5 s, most of it pandas via
# facet_grid, even if you only wanted a line chart. PEP 562 defers each one to
# first use; `from glyphx import TreemapSeries` still works.
_LAZY_ATTRS = {
    "AUTO_THRESHOLD": ".downsample",
    "Bar3DSeries": ".bar3d",
    "BubbleSeries": ".bubble",
    "BumpChartSeries": ".bump_chart",
    "CandlestickSeries": ".candlestick",
    "ChoroplethSeries": ".choropleth",
    "ContourSeries": ".contour",
    "CountPlotSeries": ".count_plot",
    "DivergingBarSeries": ".diverging_bar",
    "ECDFSeries": ".ecdf",
    "FacetGrid": ".facet_grid",
    "Figure3D": ".figure3d",
    "FillBetweenSeries": ".fill_between",
    "GanttSeries": ".gantt",
    "GroupedBarSeries": ".grouped_bar",
    "KDESeries": ".kde",
    "Line3DSeries": ".line3d",
    "ParallelCoordinatesSeries": ".parallel_coords",
    "RaincloudSeries": ".raincloud",
    "Scatter3DSeries": ".scatter3d",
    "SparklineSeries": ".sparkline",
    "StackedBarSeries": ".stacked_bar",
    "StatAnnotation": ".stat_annotation",
    "StreamingSeries": ".streaming",
    "SunburstSeries": ".sunburst",
    "Surface3DSeries": ".surface3d",
    "SwarmPlotSeries": ".swarm_plot",
    "TreemapSeries": ".treemap",
    "ViolinPlotSeries": ".violin_plot",
    "WaterfallSeries": ".waterfall",
    "apply_colormap": ".colormaps",
    "clustermap": ".clustermap",
    "colormap_colors": ".colormaps",
    "cull_faces": ".downsample",
    "decimate_grid": ".downsample",
    "ds_disable": (".downsample", "disable"),
    "ds_enable": (".downsample", "enable"),
    "ds_is_enabled": (".downsample", "is_enabled"),
    "facet_plot": ".facet_plot",
    "get_colormap": ".colormaps",
    "jointplot": ".jointplot",
    "list_colormaps": ".colormaps",
    "lmplot": ".lmplot",
    "lttb": ".downsample",
    "lttb_3d": ".downsample",
    "m4": ".downsample",
    "maybe_downsample": ".downsample",
    "maybe_downsample_line": ".downsample",
    "pairplot": ".pairplot",
    "plot3d": ".plot3d",
    "pvalue_to_label": ".stat_annotation",
    "regplot": ".regplot",
    "save_vega_lite": ".vega_lite",
    "sparkline_svg": ".sparkline",
    "to_vega_lite": ".vega_lite",
    "voxel_thin_2d": ".downsample",
    "voxel_thin_3d": ".downsample",
}


# Everything in _LAZY_ATTRS is resolved at runtime by the __getattr__ below,
# which no static analyser can see through: pyflakes reports every one of
# these as an undefined name in __all__, type checkers cannot check them,
# and editors offer no completion for `from glyphx import ECDFSeries`.
#
# Re-declaring them under TYPE_CHECKING is the documented fix for a PEP 562
# lazy module. The block is never executed, so nothing is imported eagerly
# and the startup cost the lazy map exists to avoid is unchanged -- but
# analysers, type checkers and IDEs now see real bindings.
#
# tests/test_lazy_imports.py fails if this drifts out of step with
# _LAZY_ATTRS, since the two have to list the same names to stay useful.
if _TYPE_CHECKING:  # pragma: no cover
    from .bar3d import Bar3DSeries
    from .bubble import BubbleSeries
    from .bump_chart import BumpChartSeries
    from .candlestick import CandlestickSeries
    from .choropleth import ChoroplethSeries
    from .clustermap import clustermap
    from .colormaps import apply_colormap, colormap_colors, get_colormap, list_colormaps
    from .contour import ContourSeries
    from .count_plot import CountPlotSeries
    from .diverging_bar import DivergingBarSeries
    from .downsample import (
        AUTO_THRESHOLD,
        cull_faces,
        decimate_grid,
        lttb,
        lttb_3d,
        m4,
        maybe_downsample,
        maybe_downsample_line,
        voxel_thin_2d,
        voxel_thin_3d,
    )
    from .downsample import (
        disable as ds_disable,
    )
    from .downsample import (
        enable as ds_enable,
    )
    from .downsample import (
        is_enabled as ds_is_enabled,
    )
    from .ecdf import ECDFSeries
    from .facet_grid import FacetGrid
    from .facet_plot import facet_plot
    from .figure3d import Figure3D
    from .fill_between import FillBetweenSeries
    from .gantt import GanttSeries
    from .grouped_bar import GroupedBarSeries
    from .jointplot import jointplot
    from .kde import KDESeries
    from .line3d import Line3DSeries
    from .lmplot import lmplot
    from .pairplot import pairplot
    from .parallel_coords import ParallelCoordinatesSeries
    from .plot3d import plot3d
    from .raincloud import RaincloudSeries
    from .regplot import regplot
    from .scatter3d import Scatter3DSeries
    from .sparkline import SparklineSeries, sparkline_svg
    from .stacked_bar import StackedBarSeries
    from .stat_annotation import StatAnnotation, pvalue_to_label
    from .streaming import StreamingSeries
    from .sunburst import SunburstSeries
    from .surface3d import Surface3DSeries
    from .swarm_plot import SwarmPlotSeries
    from .treemap import TreemapSeries
    from .vega_lite import save_vega_lite, to_vega_lite
    from .violin_plot import ViolinPlotSeries
    from .waterfall import WaterfallSeries


def __getattr__(name: str):
    """Import and cache a chart module the first time one of its names is used."""
    entry = _LAZY_ATTRS.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # Entries are either "module" or ("module", "attribute") when the exported
    # name differs from the one defined in the module (e.g. ds_enable).
    module, attr = entry if isinstance(entry, tuple) else (entry, name)
    import importlib
    value = getattr(importlib.import_module(module, __name__), attr)
    globals()[name] = value        # subsequent lookups skip __getattr__
    return value


def __dir__() -> list:
    """Include the lazily-exported names so tab-completion still finds them."""
    return sorted(set(globals()) | set(_LAZY_ATTRS))


# Seven exported names match the module that defines them: clustermap,
# facet_plot, jointplot, lmplot, pairplot, plot3d, regplot.  Importing a
# submodule binds it onto its package, so `import glyphx.regplot` -- or any
# internal `from .regplot import regplot`, which Figure.regplot does -- makes
# glyphx.regplot the *module*.  Normal lookup then succeeds and __getattr__ is
# never consulted, so the exported function silently becomes uncallable, and
# whether it does depends on import order.  Re-resolve on the way out.

#: The only names that can be shadowed -- an exported symbol whose module has
#: the same name.  Kept as a frozenset so the check below is a cheap miss for
#: every other attribute.
_SHADOWABLE = frozenset(
    name for name, entry in _LAZY_ATTRS.items()
    if not isinstance(entry, tuple) and entry == f".{name}"
)


class _GlyphxModule(_types.ModuleType):
    """
    Module type that keeps lazy exports from being shadowed by submodules.

    See the comment above for the full story: importing ``glyphx.regplot``
    binds the module onto the package, which hides the function of the same
    name that ``__getattr__`` would otherwise supply.
    """
    def __getattribute__(self, name: str):
        """Re-resolve through ``__getattr__`` when a lookup returns a shadowing module."""
        value = _types.ModuleType.__getattribute__(self, name)
        if type(value) is _types.ModuleType and name in _SHADOWABLE:
            value = __getattr__(name)
        return value


_sys.modules[__name__].__class__ = _GlyphxModule


# Register the pandas accessor (df.glyphx.*).
# Importing it pulls in pandas: ~255 ms, more than the rest of GlyphX put
# together, paid whether or not you touch a DataFrame. Register now if pandas
# is already loaded, else hook its import. Either order ends up working.


def _register_pandas_accessor() -> None:
    """Import the accessor module, whose import registers ``df.glyphx``."""
    from . import accessor as _accessor  # noqa: F401


if "pandas" in _sys.modules:
    _register_pandas_accessor()
else:
    class _PandasImportHook(_importlib.abc.MetaPathFinder):
        """Runs the accessor registration right after pandas finishes loading."""

        def find_spec(self, fullname, path=None, target=None):
            """Claim only the ``pandas`` import, so every other module is untouched."""
            if fullname != "pandas":
                return None
            # Step aside so the real finders resolve pandas, then wrap the
            # loader so we run immediately after its module body executes.
            _sys.meta_path.remove(self)
            try:
                spec = _importlib.util.find_spec("pandas")
            except Exception:       # pragma: no cover - defensive
                return None
            finally:
                if self not in _sys.meta_path:
                    _sys.meta_path.insert(0, self)
            if spec is None or spec.loader is None:
                return None

            real_exec = spec.loader.exec_module

            def exec_module(module):
                """Let pandas finish importing, then register the ``.glyphx`` accessor."""
                real_exec(module)
                if self in _sys.meta_path:
                    _sys.meta_path.remove(self)
                # Never let a registration failure break `import pandas`.
                with _contextlib.suppress(Exception):  # pragma: no cover
                    _register_pandas_accessor()

            spec.loader.exec_module = exec_module
            return spec

    _sys.meta_path.insert(0, _PandasImportHook())


__all__ = [
    # Core
    "Figure", "SubplotGrid", "Axes", "grid", "themes", "normalize",
    "plot",
    # Theme registry
    "register_theme", "unregister_theme", "get_theme", "list_themes",
    # Colormaps
    "apply_colormap", "colormap_colors", "list_colormaps", "get_colormap",
    # Base series
    "LineSeries", "BarSeries", "ScatterSeries",
    "PieSeries", "DonutSeries", "HistogramSeries",
    "HeatmapSeries", "BoxPlotSeries",
    # Statistical
    "ECDFSeries", "RaincloudSeries", "ViolinPlotSeries",
    "FillBetweenSeries", "KDESeries",
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
    # New competitive features
    "BubbleSeries", "SunburstSeries",
    "ParallelCoordinatesSeries", "DivergingBarSeries",
    # Downsampling
    "lttb", "m4", "maybe_downsample", "maybe_downsample_line",
    "voxel_thin_2d", "voxel_thin_3d", "lttb_3d",
    "decimate_grid", "cull_faces",
    "ds_enable", "ds_disable", "ds_is_enabled", "AUTO_THRESHOLD",
    "StackedBarSeries", "BumpChartSeries", "GanttSeries",
    "clustermap", "FacetGrid", "regplot", "ChoroplethSeries",
    "to_vega_lite", "save_vega_lite",
    "SparklineSeries", "sparkline_svg",
    # 3D
    "Figure3D", "plot3d",
    "Scatter3DSeries", "Surface3DSeries",
    "Line3DSeries", "Bar3DSeries", "ContourSeries",
]
