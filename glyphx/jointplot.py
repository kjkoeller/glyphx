from __future__ import annotations

import numpy as np

from .figure import Figure
from .series import ScatterSeries, LineSeries, HistogramSeries
from .violin_plot import _numpy_kde


def jointplot(df, x: str, y: str, kind: str = "scatter",
              marginal: str = "hist", theme: str = "default",
              hue: str | None = None):
    fig   = Figure(width=600, height=600, theme=theme, auto_display=True)
    colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])

    ax_main  = fig.add_axes(0, 0)
    ax_top   = fig.add_axes(0, 1)
    ax_right = fig.add_axes(1, 0)

    categories = df[hue].unique().tolist() if hue else [None]

    for i, cat in enumerate(categories):
        sub  = df if cat is None else df[df[hue] == cat]
        c    = colors[i % len(colors)]
        lbl  = str(cat) if cat is not None else None

        x_vals = np.asarray(sub[x].dropna(), dtype=float)
        y_vals = np.asarray(sub[y].dropna(), dtype=float)

        if kind == "scatter":
            ax_main.add_series(ScatterSeries(x_vals.tolist(), y_vals.tolist(),
                                             color=c, label=lbl))
        elif kind == "kde":
            ax_main.add_series(ScatterSeries(x_vals.tolist(), y_vals.tolist(),
                                             color=c, label=lbl, size=3))

        if marginal == "hist":
            ax_top.add_series(HistogramSeries(x_vals.tolist(), color=c))
        elif marginal == "kde":
            kde     = _numpy_kde(x_vals)
            x_range = np.linspace(x_vals.min(), x_vals.max(), 100)
            ax_top.add_series(LineSeries(x_range.tolist(), kde(x_range).tolist(),
                                         color=c, label=lbl))

        if marginal == "hist":
            ax_right.add_series(HistogramSeries(y_vals.tolist(), color=c))
        elif marginal == "kde":
            kde     = _numpy_kde(y_vals)
            y_range = np.linspace(y_vals.min(), y_vals.max(), 100)
            ax_right.add_series(LineSeries(y_range.tolist(), kde(y_range).tolist(),
                                            color=c, label=lbl))

    return fig
