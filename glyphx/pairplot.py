import numpy as np

from .colormaps import colormap_colors
from .figure import Figure
from .series import HistogramSeries, LineSeries, ScatterSeries


def pairplot(df, hue=None, kind="scatter", theme="default", diag_kind="hist"):
    """
    Grid of pairwise scatter plots with univariate plots on the diagonal.

    Args:
        df: DataFrame; numeric columns become the grid axes.
        hue: Optional column name. Off-diagonal points are split by its
            values into one colored, labelled series per category, with a
            single legend on the first off-diagonal cell.
        kind: Reserved for future off-diagonal plot types.
        theme: Theme name passed to the enclosing Figure.
        diag_kind: ``"hist"`` or ``"kde"``.

    Returns:
        Figure: the assembled grid.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    n = len(numeric_cols)
    # rows/cols must be declared up front: add_axes() validates against the
    # grid, and the no-argument form always returns cell (0, 0) -- which is
    # why every cell used to be drawn on top of the same axes.
    fig = Figure(width=300 * n, height=300 * n, rows=n, cols=n, theme=theme)

    categories = list(dict.fromkeys(df[hue].dropna())) if hue else []
    hue_colors = colormap_colors("viridis", len(categories)) if categories else []
    legend_placed = False

    for i, ycol in enumerate(numeric_cols):
        for j, xcol in enumerate(numeric_cols):
            ax = fig.add_axes(i, j)
            ax.padding = 30

            if i == j:
                # elif, not a second if: with diag_kind="kde" the old code fell
                # into the else branch as well and drew a spurious y=x line on
                # top of the density curve.
                if diag_kind == "kde":
                    from .violin_plot import _numpy_kde
                    values = np.asarray(df[xcol].dropna(), dtype=float)
                    kde = _numpy_kde(values)
                    x_vals = np.linspace(values.min(), values.max(), 100)
                    ax.add(LineSeries(x_vals.tolist(), kde(x_vals).tolist(), color="#1f77b4"))
                elif diag_kind == "hist":
                    ax.add(HistogramSeries(df[xcol], color="#1f77b4"))
                else:
                    ax.add(LineSeries(df[xcol], df[xcol]))
            elif categories:
                for k, cat in enumerate(categories):
                    mask = df[hue] == cat
                    if not mask.any():
                        continue
                    # .to_numpy(): a boolean-masked Series keeps the original
                    # index, and the series coercion path indexes positionally.
                    ax.add(ScatterSeries(
                        df.loc[mask, xcol].to_numpy(),
                        df.loc[mask, ycol].to_numpy(),
                        color=hue_colors[k % len(hue_colors)],
                        label=str(cat),
                    ))
                if not legend_placed:
                    ax.legend_pos = "top-right"   # one legend for the grid
                    legend_placed = True
            else:
                ax.add(ScatterSeries(df[xcol], df[ycol], color="#1f77b4"))

    return fig
