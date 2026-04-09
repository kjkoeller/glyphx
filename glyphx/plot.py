"""
GlyphX high-level ``plot()`` function — the fastest path to a chart.
"""

import numpy as np

from .figure import Figure
from .series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries,
)
from .bubble          import BubbleSeries
from .sunburst        import SunburstSeries
from .parallel_coords import ParallelCoordinatesSeries
from .diverging_bar   import DivergingBarSeries

# Chart kinds that don't use X/Y axes
_AXISFREE_KINDS = {"pie", "donut", "hist", "box", "heatmap", "sunburst", "parallel", "diverging"}

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

    # Validate / coerce inputs
    if kind in _AXISFREE_KINDS:
        values = data if data is not None else (y if y is not None else x)
        if values is None:
            raise ValueError(f"[glyphx.plot] No data provided for kind='{kind}'.")
        if hasattr(values, "values"):   # unwrap pandas Series
            values = values.values
        # Heatmap requires its 2-D matrix structure — never flatten it.
        # Hist and box need a flat 1-D array.
        if kind not in {"pie", "donut", "heatmap"}:
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
        # y was supplied directly — infer x if it was not provided
        if x is None:
            x = list(range(len(y)))

    # Build Figure
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
        categories = kwargs.pop("categories", x or [])
        series     = DivergingBarSeries(categories=categories, values=values,
                                        **kwargs)
    else:
        raise ValueError(
            f"[glyphx.plot] Unsupported kind='{kind}'.  "
            "Choose from: line, bar, scatter, pie, donut, hist, box, heatmap, "
            "bubble, sunburst, parallel, diverging."
        )

    fig.add(series)
    fig.plot()
    return fig