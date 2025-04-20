from .figure import Figure
from .layout import Axes
from .series import LineSeries, ScatterSeries
import numpy as np

def lmplot(df, x, y, theme="default", hue=None, order=1):
    fig = Figure()
    fig.set_theme(theme)
    ax = fig.add_axes()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    groups = df[hue].unique() if hue else [None]
    for i, group in enumerate(groups):
        sub = df if group is None else df[df[hue] == group]
        c = colors[i % len(colors)]
        ax.add(ScatterSeries(sub[x], sub[y], color=c))

        # Fit regression
        coeffs = np.polyfit(sub[x], sub[y], deg=order)
        f = np.poly1d(coeffs)
        x_vals = np.linspace(min(sub[x]), max(sub[x]), 100)
        y_vals = f(x_vals)
        ax.add(LineSeries(x_vals, y_vals, color=c))

    return fig