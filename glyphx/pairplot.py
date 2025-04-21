from .figure import Figure
from .layout import Axes
from .plot import plot
import pandas as pd
from .series import HistogramSeries, ScatterSeries, LineSeries


def pairplot(df, hue=None, kind="scatter", theme="default", diag_kind="hist"):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    n = len(numeric_cols)
    fig = Figure(width=300 * n, height=300 * n, theme=theme)

    for i, ycol in enumerate(numeric_cols):
        for j, xcol in enumerate(numeric_cols):
            ax = fig.add_axes()
            ax.padding = 30
            sub_df = df[[xcol, ycol]]
            if hue:
                sub_df[hue] = df[hue]

            if i == j:
                if diag_kind == "kde":
                    from scipy.stats import gaussian_kde
                    import numpy as np
                    values = df[xcol].dropna()
                    kde = gaussian_kde(values)
                    x_vals = np.linspace(values.min(), values.max(), 100)
                    y_vals = kde(x_vals)
                    ax.add(LineSeries(x_vals, y_vals, color="#1f77b4"))

                if diag_kind == "hist":
                    ax.add(HistogramSeries(df[xcol], color="#1f77b4"))
                else:
                    ax.add(LineSeries(df[xcol], df[xcol]))
            else:
                ax.add(ScatterSeries(df[xcol], df[ycol], color="#1f77b4", label=hue if hue else None))

    return fig

    # Optional legend rendering (bottom-right)
    if hue:
        categories = df[hue].unique()
        legend_items = []
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
        for i, cat in enumerate(categories):
            color = colors[i % len(colors)]
            x = fig.width - 180
            y = fig.height - 40 - i * 20
            legend_items.append(f'<rect x="{x}" y="{y}" width="12" height="12" fill="{color}"/>')
            legend_items.append(f'<text x="{x + 20}" y="{y + 10}" font-size="12" fill="#000">{cat}</text>')

        def inject_legend(svg):
            parts = svg.split("</svg>")
            parts.insert(-1, "\n".join(legend_items))
            return "</svg>".join(parts)

        fig.to_svg = lambda: inject_legend(Figure.to_svg(fig))

    fig.show()
    return fig
