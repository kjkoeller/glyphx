from .figure import Figure
from .series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries
)
import numpy as np

def plot(x=None, y=None, kind="line", data=None, **kwargs):
    """
    Unified high-level plot entry point for all major chart types.

    Args:
        x (list | None): x values (optional for some kinds)
        y (list | None): y values or data, depending on kind
        kind (str): One of: line, bar, scatter, pie, donut, hist, box, heatmap
        **kwargs: Passed to the appropriate series constructor and Figure

    Returns:
        Figure: GlyphX Figure object (auto-displayed)
    """
    kind = kind.lower()
    color = kwargs.pop("color", None)
    label = kwargs.pop("label", None)

    # Separate known Figure-only arguments
    figure_keys = {"width", "height", "padding", "title", "theme", "auto_display"}
    figure_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in figure_keys}

    fig = Figure(**figure_kwargs)

    # Normalize input
    if kind in {"pie", "donut", "hist", "box", "heatmap"}:
        values = data if data is not None else y if y is not None else x
        if hasattr(values, "values"):  # pandas
            values = values.values
        values = np.asarray(values).flatten()
        if not np.issubdtype(values.dtype, np.number):
            raise TypeError(f"Histogram/Box/Heatmap input must be numeric. Got {values.dtype}")
    else:
        if y is None:
            y = x
            x = list(range(len(y)))

    # Series selection
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
        series = BoxPlotSeries(values, color=color, label=label, **kwargs)
    elif kind == "heatmap":
        series = HeatmapSeries(values, **kwargs)
    else:
        raise ValueError(f"[glyphx.plot] Unsupported kind: {kind}")

    fig.add(series)
    fig.plot()
    return fig
