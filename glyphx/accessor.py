"""
GlyphX pandas DataFrame accessor.

After importing ``glyphx``, every DataFrame gains a ``.glyphx`` accessor
that creates fully configured, chainable Figure objects directly from
column names::

    import pandas as pd
    import glyphx  # registers the accessor

    df = pd.read_csv("sales.csv")

    # One-liner bar chart
    df.glyphx.bar(x="month", y="revenue", title="Monthly Revenue").share("report.html")

    # Full chain
    (
        df.glyphx
          .line(x="date", y="price", theme="dark", label="Price")
          .set_ylabel("USD")
          .annotate("Peak", x="2024-10", y=5400)
          .share("price_chart.html")
    )
"""
from __future__ import annotations

from typing import Any

import pandas as pd


@pd.api.extensions.register_dataframe_accessor("glyphx")
class GlyphXAccessor:
    """
    Pandas DataFrame accessor that exposes the full GlyphX plotting API.

    Registered automatically when ``glyphx`` is imported.  Access via
    ``df.glyphx.<method>(...)``.

    All methods return a :class:`~glyphx.Figure` so results can be
    further customised via method chaining.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    # ── Internal helpers ─────────────────────────────────────────────────

    def _col(self, name: str | None) -> list | None:
        """Return column as list, or None if name is None / not in df."""
        if name is None or name not in self._df.columns:
            return None
        return self._df[name].tolist()

    def _fig(
        self,
        title: str | None,
        theme: str | dict | None,
        legend: str | bool | None,
        width: int,
        height: int,
        xlabel: str | None,
        ylabel: str | None,
        auto_display: bool,
    ):
        """Build a base Figure with common options pre-applied."""
        from .figure import Figure
        fig = Figure(
            title=title,
            theme=theme,
            legend=legend,
            width=width,
            height=height,
            auto_display=auto_display,
        )
        if xlabel:
            fig.axes.xlabel = xlabel
        if ylabel:
            fig.axes.ylabel = ylabel
        return fig

    # ── Chart methods ─────────────────────────────────────────────────────

    def line(
        self,
        x: str | None = None,
        y: str | None = None,
        color: str | None = None,
        label: str | None = None,
        linestyle: str = "solid",
        yerr: str | None = None,
        title: str | None = None,
        theme: str | dict | None = None,
        legend: str | bool | None = "top-right",
        width: int = 640,
        height: int = 480,
        xlabel: str | None = None,
        ylabel: str | None = None,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """
        Create a line chart from DataFrame columns.

        Args:
            x:     Column name for X axis.
            y:     Column name for Y axis.
            yerr:  Column name for Y error bars (optional).
            label: Legend label; defaults to the ``y`` column name.

        Returns:
            :class:`~glyphx.Figure` — fully chainable.
        """
        from .series import LineSeries

        x_data = self._col(x) or list(range(len(self._df)))
        y_data = self._col(y) or self._df.select_dtypes("number").iloc[:, 0].tolist()
        err    = self._col(yerr)

        fig = self._fig(title, theme, legend, width, height,
                        xlabel or x, ylabel or y, auto_display)
        fig.add(LineSeries(
            x_data, y_data,
            color=color,
            label=label or y,
            linestyle=linestyle,
            yerr=err,
            **kwargs,
        ))
        return fig

    def bar(
        self,
        x: str | None = None,
        y: str | None = None,
        color: str | None = None,
        label: str | None = None,
        yerr: str | None = None,
        groupby: str | None = None,
        agg: str = "sum",
        title: str | None = None,
        theme: str | dict | None = None,
        legend: str | bool | None = "top-right",
        width: int = 640,
        height: int = 480,
        xlabel: str | None = None,
        ylabel: str | None = None,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """
        Create a bar chart from DataFrame columns.

        Pass ``groupby`` to create grouped / aggregated bars.

        Returns:
            :class:`~glyphx.Figure`
        """
        from .series import BarSeries

        fig = self._fig(title, theme, legend, width, height,
                        xlabel or x, ylabel or y, auto_display)

        if groupby and groupby in self._df.columns:
            theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])
            num_col = y or self._df.select_dtypes("number").columns[0]
            agg_df  = (
                self._df.groupby(groupby)[num_col]
                .agg(agg)
                .reset_index()
            )
            for i, (grp, gdf) in enumerate(agg_df.groupby(groupby)):
                fig.add(BarSeries(
                    agg_df[groupby].tolist(),
                    agg_df[num_col].tolist(),
                    color=theme_colors[i % len(theme_colors)],
                    label=str(grp),
                ))
        else:
            x_data = self._col(x) or list(range(len(self._df)))
            y_data = self._col(y) or self._df.select_dtypes("number").iloc[:, 0].tolist()
            err    = self._col(yerr)
            fig.add(BarSeries(
                x_data, y_data,
                color=color,
                label=label or y,
                yerr=err,
                **kwargs,
            ))
        return fig

    def scatter(
        self,
        x: str | None = None,
        y: str | None = None,
        color: str | None = None,
        label: str | None = None,
        size: int = 5,
        marker: str = "circle",
        title: str | None = None,
        theme: str | dict | None = None,
        legend: str | bool | None = "top-right",
        width: int = 640,
        height: int = 480,
        xlabel: str | None = None,
        ylabel: str | None = None,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """Create a scatter plot from DataFrame columns. Returns :class:`~glyphx.Figure`."""
        from .series import ScatterSeries

        x_data = self._col(x) or list(range(len(self._df)))
        y_data = self._col(y) or self._df.select_dtypes("number").iloc[:, 0].tolist()

        fig = self._fig(title, theme, legend, width, height,
                        xlabel or x, ylabel or y, auto_display)
        fig.add(ScatterSeries(
            x_data, y_data,
            color=color, label=label or y,
            size=size, marker=marker,
            **kwargs,
        ))
        return fig

    def hist(
        self,
        col: str | None = None,
        bins: int = 10,
        color: str | None = None,
        label: str | None = None,
        title: str | None = None,
        theme: str | dict | None = None,
        width: int = 640,
        height: int = 480,
        xlabel: str | None = None,
        ylabel: str | None = None,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """Create a histogram of a numeric column. Returns :class:`~glyphx.Figure`."""
        from .series import HistogramSeries

        target = col or self._df.select_dtypes("number").columns[0]
        data   = self._df[target].dropna().tolist()

        fig = self._fig(title, theme, "top-right", width, height,
                        xlabel or target, ylabel or "Count", auto_display)
        fig.add(HistogramSeries(data, bins=bins, color=color, label=label or target))
        return fig

    def box(
        self,
        col: str | None = None,
        groupby: str | None = None,
        color: str | None = None,
        title: str | None = None,
        theme: str | dict | None = None,
        width: int = 640,
        height: int = 480,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """Create a box plot. Pass ``groupby`` for multi-box comparison. Returns :class:`~glyphx.Figure`."""
        from .series import BoxPlotSeries

        target = col or self._df.select_dtypes("number").columns[0]
        fig    = self._fig(title, theme, False, width, height, None, target, auto_display)

        if groupby and groupby in self._df.columns:
            groups = self._df[groupby].unique().tolist()
            arrays = [
                self._df[self._df[groupby] == g][target].dropna().tolist()
                for g in groups
            ]
            fig.add(BoxPlotSeries(arrays, categories=[str(g) for g in groups],
                                  color=color or "#1f77b4"))
        else:
            data = self._df[target].dropna().tolist()
            fig.add(BoxPlotSeries(data, color=color or "#1f77b4"))

        return fig

    def pie(
        self,
        labels: str | None = None,
        values: str | None = None,
        title: str | None = None,
        theme: str | dict | None = None,
        width: int = 480,
        height: int = 480,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """Create a pie chart. Returns :class:`~glyphx.Figure`."""
        from .series import PieSeries

        lbl_data = self._col(labels)
        val_data = self._col(values) or self._df.select_dtypes("number").iloc[:, 0].tolist()

        fig = self._fig(title, theme, False, width, height, None, None, auto_display)
        fig.add(PieSeries(val_data, labels=lbl_data, **kwargs))
        return fig

    def donut(
        self,
        labels: str | None = None,
        values: str | None = None,
        title: str | None = None,
        theme: str | dict | None = None,
        width: int = 480,
        height: int = 480,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """Create a donut chart. Returns :class:`~glyphx.Figure`."""
        from .series import DonutSeries

        lbl_data = [str(v) for v in (self._col(labels) or range(len(self._df)))]
        val_data = self._col(values) or self._df.select_dtypes("number").iloc[:, 0].tolist()

        fig = self._fig(title, theme, False, width, height, None, None, auto_display)
        fig.add(DonutSeries(val_data, labels=lbl_data, **kwargs))
        return fig

    def heatmap(
        self,
        title: str | None = None,
        theme: str | dict | None = None,
        width: int = 640,
        height: int = 480,
        auto_display: bool = True,
        **kwargs: Any,
    ):
        """
        Create a heatmap from the DataFrame's numeric values.

        The entire numeric portion of the DataFrame is treated as a 2-D
        matrix.  Column names become column labels; index values become
        row labels.

        Returns:
            :class:`~glyphx.Figure`
        """
        from .series import HeatmapSeries

        num_df = self._df.select_dtypes("number")
        matrix = num_df.values.tolist()

        fig = self._fig(title, theme, False, width, height, None, None, auto_display)
        fig.add(HeatmapSeries(
            matrix,
            col_labels=num_df.columns.tolist(),
            row_labels=[str(i) for i in self._df.index.tolist()],
            **kwargs,
        ))
        return fig

    def plot(
        self,
        kind: str = "line",
        x: str | None = None,
        y: str | None = None,
        **kwargs: Any,
    ):
        """
        Unified entry point — mirrors ``glyphx.plot()`` but operates on
        the DataFrame's columns.

        Args:
            kind: Chart type (same values as :func:`glyphx.plot`).
            x:    Column name for X axis.
            y:    Column name for Y axis.

        Returns:
            :class:`~glyphx.Figure`
        """
        method = getattr(self, kind, None)
        if method is None:
            raise ValueError(
                f"Unknown chart kind '{kind}'. "
                "Use: line, bar, scatter, hist, box, pie, donut, heatmap."
            )
        return method(x=x, y=y, **kwargs)
