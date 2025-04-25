from .figure import Figure
from .series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries
)

import numpy as np

def plot(x=None, y=None, kind="line", data=None, legend="top-right", **kwargs):
    """
    Unified high-level plotting function inspired by matplotlib.pyplot.plot and seaborn.

    This is the fastest way to create a single chart. You specify the chart `kind`
    and provide `x` and `y` (or just `y`) and glyphx will handle layout, axis scaling,
    rendering, and interactive display/export.

    Parameters:
        x (list or None): x-axis values (not needed for pie, donut, hist, box, etc).
        y (list or None): y-axis values or raw data depending on chart kind.
        kind (str): Chart type. One of:
                    - "line", "bar", "scatter"
                    - "pie", "donut"
                    - "hist" (histogram)
                    - "box" (boxplot)
                    - "heatmap"
        data (list or None): Optional standalone data array used for charts like hist, box, etc.
        **kwargs: Additional keyword args forwarded to:
                  - Series constructors (e.g., `color`, `label`, `bins`)
                  - `Figure` (e.g., `title`, `width`, `theme`)

    Returns:
        glyphx.Figure: The figure object (automatically displayed unless auto_display is False).

    Example:
        plot([1, 2, 3], [4, 5, 6], kind="line", title="Line Chart")
        plot(y=[4, 5, 6], kind="bar", title="Bar Chart")
        plot(data=[1, 3, 2, 2, 1, 4], kind="hist")
    """
    kind = kind.lower()
    if kind in {"pie", "donut", "hist", "box", "heatmap"}:
        values = data if data is not None else y if y is not None else x
        if values is None:
            raise ValueError(f"[glyphx.plot] No data provided for kind '{kind}'")
    else:
        if y is None:
            if x is not None:
                y = x
                x = list(range(len(y)))
            else:
                raise ValueError(f"[glyphx.plot] x or y must be provided for kind '{kind}'")

    color = kwargs.pop("color", None)
    label = kwargs.pop("label", None)

    # Separate known Figure-only arguments
    # Pull optional figure arguments
    figure_keys = {"width", "height", "padding", "title", "theme", "auto_display", "legend"}
    figure_kwargs = {k: kwargs.pop(k) for k in list(kwargs) if k in figure_keys}

    # Pull axis label options
    xlabel = kwargs.pop("xlabel", None)
    ylabel = kwargs.pop("ylabel", None)

    fig = Figure(**figure_kwargs)

    # Set axis labels if provided
    fig.axes.xlabel = xlabel
    fig.axes.ylabel = ylabel

    # Determine the input values to use
    if kind in {"pie", "donut", "hist", "box", "heatmap"}:
        values = data if data is not None else y if y is not None else x
        if hasattr(values, "values"):  # pandas
            values = values.values
        values = np.asarray(values).flatten()
        if not np.issubdtype(values.dtype, np.number):
            raise TypeError(f"Histogram/Box/Heatmap input must be numeric. Got {values.dtype}")
        # values = data or y or x
        if values is None:
            raise ValueError(f"[glyphx.plot] `{kind}` chart requires `data` or `y` values.")
    else:
        # For line/bar/scatter style charts
        if y is None:
            y = x
            x = list(range(len(y)))

    # Construct the appropriate Series object
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
        print(series.values)
    elif kind == "hist":
        series = HistogramSeries(values, color=color, label=label, **kwargs)
    elif kind == "box":
        series = BoxPlotSeries(values, color=color, label=label, **kwargs)
    elif kind == "heatmap":
        series = HeatmapSeries(values, **kwargs)
    else:
        raise ValueError(f"[glyphx.plot] Unsupported chart kind: '{kind}'")

    # Add to figure and display
    fig.add(series)
    fig.plot()
    return fig
