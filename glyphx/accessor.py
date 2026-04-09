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

        fig = self._fig(title, theme, legend, width, height,
                        xlabel or x, ylabel or y, auto_display)
        hue = kwargs.pop("hue", None)
        if hue and hue in self._df.columns:
            theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])
            for i, (grp_val, grp_df) in enumerate(self._df.groupby(hue)):
                fig.add(LineSeries(
                    grp_df[x].tolist() if x else list(range(len(grp_df))),
                    grp_df[y].tolist() if y else grp_df.select_dtypes("number").iloc[:, 0].tolist(),
                    color=theme_colors[i % len(theme_colors)],
                    label=str(grp_val),
                    linestyle=linestyle,
                ))
        else:
            x_data = self._col(x) or list(range(len(self._df)))
            y_data = self._col(y) or self._df.select_dtypes("number").iloc[:, 0].tolist()
            err    = self._col(yerr)
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
        hue: str | None = None,
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

        Pass ``groupby`` or ``hue`` to create one series per unique group,
        each colored automatically from the theme palette.  ``hue`` splits
        by a column while keeping x/y semantics; ``groupby`` aggregates.

        Returns:
            :class:`~glyphx.Figure`
        """
        from .series import BarSeries

        # Resolve hue alias: hue splits without aggregation
        effective_groupby = hue or groupby or None

        fig = self._fig(title, theme, legend, width, height,
                        xlabel or x, ylabel or y, auto_display)

        if effective_groupby and effective_groupby in self._df.columns:
            from .grouped_bar import GroupedBarSeries
            theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])
            num_col = str(y or self._df.select_dtypes("number").columns[0])

            if hue and not groupby and x and x in self._df.columns:
                # Hue mode with X column → GroupedBarSeries (side-by-side bars)
                x_vals   = list(self._df[x].unique())
                hue_vals = list(self._df[hue].unique())
                # Build values[x_idx][hue_idx]
                values_matrix = []
                for xv in x_vals:
                    row = []
                    for hv in hue_vals:
                        mask = (self._df[x] == xv) & (self._df[hue] == hv)
                        val  = float(self._df[mask][num_col].mean()) if mask.any() else 0.0
                        row.append(val)
                    values_matrix.append(row)
                colors = [theme_colors[i % len(theme_colors)] for i in range(len(hue_vals))]
                fig.add(GroupedBarSeries(
                    groups=x_vals, categories=hue_vals,
                    values=values_matrix, group_colors=colors,
                ))
            elif hue and not groupby:
                # Hue without X → one aggregated bar per hue group
                agg_df = (
                    self._df.groupby(hue)[num_col]
                    .agg(agg).reset_index().sort_values(hue)
                )
                for i, row in enumerate(agg_df.itertuples(index=False)):
                    fig.add(BarSeries(
                        [str(getattr(row, hue))], [float(getattr(row, num_col))],
                        color=theme_colors[i % len(theme_colors)],
                        label=str(getattr(row, hue)),
                    ))
            else:
                # groupby aggregation mode
                agg_df = (
                    self._df.groupby(effective_groupby)[num_col]
                    .agg(agg).reset_index().sort_values(effective_groupby)
                )
                for i, row in enumerate(agg_df.itertuples(index=False)):
                    grp = getattr(row, effective_groupby)
                    val = getattr(row, num_col)
                    fig.add(BarSeries(
                        [str(grp)], [float(val)],
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

        fig = self._fig(title, theme, legend, width, height,
                        xlabel or x, ylabel or y, auto_display)
        hue = kwargs.pop("hue", None)
        if hue and hue in self._df.columns:
            theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])
            for i, (grp_val, grp_df) in enumerate(self._df.groupby(hue)):
                fig.add(ScatterSeries(
                    grp_df[x].tolist() if x else list(range(len(grp_df))),
                    grp_df[y].tolist() if y else grp_df.select_dtypes("number").iloc[:, 0].tolist(),
                    color=theme_colors[i % len(theme_colors)],
                    label=str(grp_val),
                    size=size, marker=marker,
                ))
        else:
            x_data = self._col(x) or list(range(len(self._df)))
            y_data = self._col(y) or self._df.select_dtypes("number").iloc[:, 0].tolist()
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
            x:    Column name for X axis (used for line/bar/scatter).
            y:    Column name for Y axis (used for line/bar/scatter).

        Returns:
            :class:`~glyphx.Figure`
        """
        method = getattr(self, kind, None)
        if method is None:
            raise ValueError(
                f"Unknown chart kind '{kind}'. "
                "Use: line, bar, scatter, hist, box, pie, donut, heatmap."
            )
        # hist() and box() use col= not x=/y=; pie/donut use labels=/values=
        # Route kwargs appropriately per chart type
        if kind in {"hist", "box"}:
            col = y or x
            return method(col=col, **kwargs)
        if kind in {"pie", "donut"}:
            return method(labels=x, values=y, **kwargs)
        return method(x=x, y=y, **kwargs)
