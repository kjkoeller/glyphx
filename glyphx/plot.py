from .figure import Figure
from .series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries
)


def plot(x=None, y=None, kind="line", **kwargs):
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

    fig = Figure(**kwargs)

    # Normalize input
    if kind in {"pie", "donut", "hist", "box", "heatmap"}:
        data = y if y is not None else x
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
        series = PieSeries(values=data, **kwargs)
    elif kind == "donut":
        series = DonutSeries(values=data, **kwargs)
    elif kind == "hist":
        series = HistogramSeries(data, color=color, label=label, **kwargs)
    elif kind == "box":
        series = BoxPlotSeries(data, color=color, label=label, **kwargs)
    elif kind == "heatmap":
        series = HeatmapSeries(data, **kwargs)
    else:
        raise ValueError(f"[glyphx.plot] Unsupported kind: {kind}")

    fig.add(series)
    fig.plot()
    return fig