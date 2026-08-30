"""
GlyphX high-level ``plot()`` function - the fastest path to a chart.
"""

import numpy as np

from .bubble import BubbleSeries
from .bump_chart import BumpChartSeries
from .dataframes import get_column, is_dataframe
from .diverging_bar import DivergingBarSeries
from .figure import Figure
from .parallel_coords import ParallelCoordinatesSeries
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
from .sparkline import SparklineSeries
from .stacked_bar import StackedBarSeries
from .sunburst import SunburstSeries
from .utils import as_seq

# Chart kinds that don't use X/Y axes
_AXISFREE_KINDS = {"pie", "donut", "hist", "box", "heatmap", "sunburst",
                   "parallel", "diverging", "stacked", "stacked_bar",
                   "stackedbar", "bump", "sparkline"}

#: Kinds that take their data through keyword arguments (``series=``,
#: ``rankings=``) rather than the positional ``values``. Coercing ``values``
#: to float for these fails on the category labels in ``x``.
_KEYWORD_DATA_KINDS = {"stacked", "stacked_bar", "stackedbar", "bump"}

# Arguments forwarded to Figure rather than the series constructor
_FIGURE_KEYS = {"width", "height", "padding", "title", "theme",
                "auto_display", "legend", "xscale", "yscale"}


def plot(x=None, y=None, kind="line", data=None, legend="top-right", **kwargs):
    """
    Unified high-level plotting function.

    This is the quickest way to create a single chart.  Specify ``kind``
    plus ``x``/``y`` (or ``data`` for distribution charts) and GlyphX
    handles scaling, theming, rendering, and display automatically.

    Parameters
    ----------
    x : list or None
        X-axis values.  Not required for ``pie``, ``donut``, ``hist``,
        ``box``, or ``heatmap``.
    y : list or None
        Y-axis values or raw data for distribution charts.
    kind : str
        Chart type.  One of ``"line"``, ``"bar"``, ``"scatter"``,
        ``"pie"``, ``"donut"``, ``"hist"``, ``"box"``, ``"heatmap"``.
    data : list or None
        Explicit data array for ``hist`` / ``box`` / ``pie`` / ``donut``
        (takes priority over ``y``).
    legend : str
        Legend position (``"top-right"``, ``"top-left"``, etc.) or
        ``False`` to suppress.
    **kwargs
        Extra keyword arguments forwarded to the Series constructor
        (e.g. ``color``, ``label``, ``bins``, ``linestyle``) **or** to
        Figure (e.g. ``width``, ``height``, ``theme``, ``xscale``).

    Returns
    -------
    Figure
        The Figure object (auto-displayed unless ``auto_display=False``).

    Examples
    --------
    >>> plot([1, 2, 3], [4, 5, 6], kind="line", title="My Line")
    >>> plot(y=[4, 5, 6], kind="bar")
    >>> plot(data=[1, 3, 2, 2, 1, 4], kind="hist")
    """
    kind = kind.lower()

    # Separate Figure-level kwargs from series-level kwargs
    figure_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in _FIGURE_KEYS}
    figure_kwargs.setdefault("legend", legend)

    xlabel = kwargs.pop("xlabel", None)
    ylabel = kwargs.pop("ylabel", None)
    color  = kwargs.pop("color", None)
    label  = kwargs.pop("label", None)

    # When `data` is a dataframe, x/y/c may name columns in it. This works
    # for pandas, Polars, PyArrow, cuDF, and anything else implementing the
    # dataframe interchange protocol -- see glyphx.dataframes.
    if data is not None and is_dataframe(data):
        def _resolve(value):
            if isinstance(value, str):
                return get_column(data, value)
            return value

        x = _resolve(x)
        y = _resolve(y)
        for key in ("c", "size", "hue"):
            if isinstance(kwargs.get(key), str):
                kwargs[key] = get_column(data, kwargs[key])
        if xlabel is None and isinstance(kwargs.get("_x_name"), str):
            xlabel = kwargs.pop("_x_name")
        # Distribution kinds read from `data` directly; give them the column
        # rather than the whole frame.
        if kind in _AXISFREE_KINDS and y is None and x is not None:
            data = x

    # Validate / coerce inputs
    if kind in _AXISFREE_KINDS:
        values = data if data is not None else (y if y is not None else x)
        if values is None and kind not in _KEYWORD_DATA_KINDS:
            raise ValueError(f"[glyphx.plot] No data provided for kind='{kind}'.")
        if hasattr(values, "values"):   # unwrap pandas Series
            values = values.values
        # Heatmap requires its 2-D matrix structure - never flatten it.
        # Hist and box need a flat 1-D array.
        if kind not in {"pie", "donut", "heatmap"} | _KEYWORD_DATA_KINDS:
            values = np.asarray(values, dtype=float).flatten()
            if not np.issubdtype(values.dtype, np.number):
                raise TypeError(
                    f"kind='{kind}' requires numeric data; got {values.dtype}."
                )
    else:
        if y is None:
            if x is not None:
                y = x
                x = list(range(len(y)))
            else:
                raise ValueError(
                    f"[glyphx.plot] Provide x and/or y for kind='{kind}'."
                )
        # y was supplied directly - infer x if it was not provided
        if x is None:
            x = list(range(len(y)))

    fig = Figure(**figure_kwargs)
    fig.axes.xlabel = xlabel
    fig.axes.ylabel = ylabel

    # Build Series
    if kind == "line":
        series = LineSeries(x, y, color=color, label=label, **kwargs)
    elif kind == "bar":
        series = BarSeries(x, y, color=color, label=label, **kwargs)
    elif kind == "scatter":
        series = ScatterSeries(x, y, color=color, label=label, **kwargs)
    elif kind == "pie":
        series = PieSeries(values=values, **kwargs)
    elif kind == "donut":
        series = DonutSeries(values=values, **kwargs)
    elif kind == "hist":
        series = HistogramSeries(values, color=color, label=label, **kwargs)
    elif kind == "box":
        series = BoxPlotSeries(values, color=color or "#1f77b4", label=label, **kwargs)
    elif kind == "heatmap":
        series = HeatmapSeries(values, **kwargs)
    elif kind in ("stacked", "stacked_bar", "stackedbar"):
        # "stacked" was the original spelling; the others are what people
        # reach for first, so accept all three rather than sending them to
        # the did-you-mean error.
        x_data = as_seq(kwargs.pop("x", x))
        series_data = kwargs.pop("series", {})
        normalize = kwargs.pop("normalize", False)
        series = StackedBarSeries(x=x_data, series=series_data, normalize=normalize, **kwargs)
    elif kind == "bump":
        rankings = kwargs.pop("rankings", {})
        series = BumpChartSeries(x=as_seq(x), rankings=rankings, **kwargs)
    elif kind == "sparkline":
        series = SparklineSeries(data=values, color=color or "#2563eb", **kwargs)
    elif kind == "bubble":
        size = kwargs.pop("size", 10)
        series = BubbleSeries(x, y, size=size, color=color, label=label, **kwargs)
    elif kind == "sunburst":
        parents = kwargs.pop("parents", [])
        series  = SunburstSeries(labels=values, parents=parents, values=values, **kwargs)
    elif kind in ("parallel", "parallel_coords"):
        axes   = kwargs.pop("axes", [])
        series = ParallelCoordinatesSeries(data=values, axes=axes, **kwargs)
    elif kind == "diverging":
        categories = kwargs.pop("categories", as_seq(x))
        series     = DivergingBarSeries(categories=categories, values=values,
                                        **kwargs)
    else:
        # Fuzzy-match to help users who typo the kind name
        import difflib as _dl
        _valid = ["line", "bar", "scatter", "pie", "donut", "hist", "box",
                  "heatmap", "bubble", "sunburst", "parallel", "diverging",
                  "stacked", "stacked_bar", "bump", "sparkline"]
        _close = _dl.get_close_matches(kind, _valid, n=3, cutoff=0.5)
        _hint  = f"  Did you mean: {_close}?" if _close else ""
        raise ValueError(
            f"[glyphx.plot] Unsupported kind='{kind}'.{_hint}\n"
            f"Valid kinds: {', '.join(_valid)}."
        )

    fig.add(series)
    fig.plot()
    return fig
