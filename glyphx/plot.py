from .figure import Figure
from .series import LineSeries, BarSeries, ScatterSeries

def plot(x, y=None, kind="line", **kwargs):
    if kind == "bar":
        series = BarSeries(x, y, **kwargs)
    elif kind == "scatter":
        series = ScatterSeries(x, y, **kwargs)
    else:
        series = LineSeries(x, y, **kwargs)
    fig = Figure()
    fig.add(series)
    return fig