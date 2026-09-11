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

from typing import Any, TypedDict

import pandas as pd


class FigureOptions(TypedDict, total=False):
    """
    Presentation options every chart method accepts.

    Declared once and consumed through ``**kwargs`` by every chart method,
    rather than the same eight parameters being written out per method.
    Not applied as ``Unpack[FigureOptions]``: these methods also take
    ``hue`` and forward any remaining keywords to the series constructor,
    so the signature is genuinely open and declaring it closed would be
    inaccurate. That repetition had
    already drifted: ``auto_display`` was ``bool = True`` in three methods
    and ``bool | None = None`` in a fourth, and ``legend``, ``xlabel`` and
    ``ylabel`` were simply missing from several -- where ``**kwargs``
    swallowed them, so ``hist(legend="top-left")`` was accepted and
    silently ignored.
    """

    title: str | None
    theme: str | dict | None
    legend: str | bool | None
    width: int
    height: int
    xlabel: str | None
    ylabel: str | None
    auto_display: bool


#: Runtime view of the above, for splitting presentation kwargs from the
#: series-specific ones. A TypedDict has no runtime membership test.
_FIGURE_OPTION_KEYS = frozenset(FigureOptions.__annotations__)


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
        """Hold the frame this accessor was attached to."""
        self._df = df

    # Internal helpers

    def _col(self, name: str | None) -> list | None:
        """
        Return a column as a list, or ``None`` when ``name`` is ``None``.

        A name that is not in the frame raises rather than returning
        ``None``.  The two cases used to be indistinguishable, so
        ``df.glyphx.line(x="Month", y="revenue")`` -- a capitalisation typo --
        silently fell back to the row index and drew a 0, 1, 2 axis instead
        of the month names, with no indication anything was wrong.

        Raises:
            KeyError: If ``name`` is not a column, with the closest match
                and the available columns.
        """
        if name is None:
            return None
        if name not in self._df.columns:
            raise KeyError(self._unknown_column_message(name))
        return self._df[name].tolist()

    def _unknown_column_message(self, name) -> str:
        """Build a 'did you mean' message for an unknown column name."""
        import difflib

        available = [str(c) for c in self._df.columns]
        close = difflib.get_close_matches(str(name), available, n=1, cutoff=0.6)
        hint = f" Did you mean {close[0]!r}?" if close else ""
        return (f"Column {name!r} not found.{hint} "
                f"Available columns: {available}")

    def _check_column(self, name, role: str = "column"):
        """Validate an optional column name used outside :meth:`_col`."""
        if name is not None and name not in self._df.columns:
            raise KeyError(f"{role}: " + self._unknown_column_message(name))
        return name

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

    def _split_options(self, kwargs: dict) -> dict:
        """
        Pull the presentation options out of ``kwargs``, leaving the rest.

        Mutates ``kwargs`` so what remains is exactly the series-specific
        arguments, which get forwarded to the series constructor.
        """
        return {k: kwargs.pop(k) for k in list(kwargs) if k in _FIGURE_OPTION_KEYS}

    def _figure_for(self, kwargs: dict, xlabel: str | None = None,
                    ylabel: str | None = None, *,
                    width: int = 640, height: int = 480,
                    legend: str | bool | None = "top-right"):
        """
        Build the Figure for a chart method from its presentation kwargs.

        ``xlabel``/``ylabel`` are the column-derived fallbacks and
        ``width``/``height``/``legend`` the per-chart defaults -- pie and
        donut want a square canvas and no legend gutter, for instance. An
        option the caller passed always wins over any of them.

        Every chart method routes through here, so they all accept the same
        set and none can quietly drop one.
        """
        opts = self._split_options(kwargs)
        return self._fig(
            opts.get("title"),
            opts.get("theme"),
            opts.get("legend", legend),
            opts.get("width", width),
            opts.get("height", height),
            opts.get("xlabel") or xlabel,
            opts.get("ylabel") or ylabel,
            opts.get("auto_display", True),
        )

    # Chart methods

    def line(
        self,
        x: str | None = None,
        y: str | None = None,
        color: str | None = None,
        label: str | None = None,
        linestyle: str = "solid",
        yerr: str | None = None,
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
            :class:`~glyphx.Figure` - fully chainable.
        """
        from .series import LineSeries

        hue = kwargs.pop("hue", None)
        self._check_column(hue, "hue")
        fig = self._figure_for(kwargs, xlabel=x, ylabel=y)
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

        fig = self._figure_for(kwargs, xlabel=x, ylabel=y)

        self._check_column(effective_groupby, "hue/groupby")
        if effective_groupby and effective_groupby in self._df.columns:
            theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])
            num_col = str(y or self._df.select_dtypes("number").columns[0])

            if hue and not groupby and x and x in self._df.columns:
                # Hue mode with X column → one BarSeries per group (all x categories)
                # This gives each group its own .color and .label, matching the
                # Seaborn hue= API and enabling proper legend entries.
                hue_vals = list(self._df[hue].unique())
                for i, hv in enumerate(hue_vals):
                    mask   = self._df[hue] == hv
                    grp_df = self._df[mask].copy()
                    x_data = grp_df[x].tolist()
                    y_data = grp_df[num_col].tolist()
                    fig.add(BarSeries(
                        x_data, y_data,
                        color=theme_colors[i % len(theme_colors)],
                        label=str(hv),
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
        **kwargs: Any,
    ):
        """Create a scatter plot from DataFrame columns. Returns :class:`~glyphx.Figure`."""
        from .series import ScatterSeries

        fig = self._figure_for(kwargs, xlabel=x, ylabel=y)
        hue = kwargs.pop("hue", None)
        self._check_column(hue, "hue")
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
        **kwargs: Any,
    ):
        """Create a histogram of a numeric column. Returns :class:`~glyphx.Figure`."""
        from .series import HistogramSeries

        target = col or self._df.select_dtypes("number").columns[0]
        data   = self._df[target].dropna().tolist()

        fig = self._figure_for(kwargs, xlabel=target, ylabel="Count")
        fig.add(HistogramSeries(data, bins=bins, color=color, label=label or target))
        return fig

    def box(
        self,
        col: str | None = None,
        groupby: str | None = None,
        color: str | None = None,
        **kwargs: Any,
    ):
        """Create a box plot. Pass ``groupby`` for multi-box comparison. Returns :class:`~glyphx.Figure`."""
        from .series import BoxPlotSeries

        target = col or self._df.select_dtypes("number").columns[0]
        fig    = self._figure_for(kwargs, ylabel=target)

        self._check_column(groupby, "groupby")
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
        **kwargs: Any,
    ):
        """Create a pie chart. Returns :class:`~glyphx.Figure`."""
        from .series import PieSeries

        lbl_data = self._col(labels)
        val_data = self._col(values) or self._df.select_dtypes("number").iloc[:, 0].tolist()

        fig = self._figure_for(kwargs, width=480, height=480, legend=False)
        fig.add(PieSeries(val_data, labels=lbl_data, **kwargs))
        return fig

    def donut(
        self,
        labels: str | None = None,
        values: str | None = None,
        **kwargs: Any,
    ):
        """Create a donut chart. Returns :class:`~glyphx.Figure`."""
        from .series import DonutSeries

        lbl_data = [str(v) for v in (self._col(labels) or range(len(self._df)))]
        val_data = self._col(values) or self._df.select_dtypes("number").iloc[:, 0].tolist()

        fig = self._figure_for(kwargs, width=480, height=480, legend=False)
        fig.add(DonutSeries(val_data, labels=lbl_data, **kwargs))
        return fig

    def heatmap(
        self,
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

        fig = self._figure_for(kwargs)
        fig.add(HeatmapSeries(
            matrix,
            col_labels=num_df.columns.tolist(),
            row_labels=[str(i) for i in self._df.index.tolist()],
            **kwargs,
        ))
        return fig

    def stacked_bar(
        self,
        x: str,
        y: str,
        stack: str,
        normalize: bool = False,
        bar_width: float = 0.75,
        **kwargs: Any,
    ):
        """
        Stacked bar chart from a long-format DataFrame.

        Pivots ``stack`` into one sub-series per distinct value, summing
        ``y`` within each (``x``, ``stack``) pair.

        Negative values are supported: positive segments stack upward from
        zero and negative segments stack downward, so a category holding a
        mix shows both without the two cancelling out.

        Args:
            x (str): Column holding the category for each bar.
            y (str): Column holding the numeric value.
            stack (str): Column whose distinct values become stack segments.
            normalize (bool): Scale each bar to 100%.  Shares are computed
                from absolute values, so a bar holding +5 and -5 shows
                +50% and -50% rather than dividing by a zero total.
            bar_width (float): Fraction of the slot each bar fills.

        Returns:
            Figure: The rendered figure.

        Example::

            df.glyphx.stacked_bar(x="quarter", y="revenue", stack="segment")
        """
        from .stacked_bar import StackedBarSeries

        for col in (x, y, stack):
            if col not in self._df.columns:
                raise KeyError(
                    f"Column {col!r} not found. "
                    f"Available columns: {list(self._df.columns)}"
                )

        pivot = (
            self._df.pivot_table(
                index=x, columns=stack, values=y, aggfunc="sum", fill_value=0
            )
            .sort_index()
        )
        categories = [str(v) for v in pivot.index.tolist()]
        series = {
            str(name): [float(v) for v in pivot[name].tolist()]
            for name in pivot.columns
        }

        fig = self._figure_for(kwargs, xlabel=x, ylabel=y)
        fig.add(StackedBarSeries(
            x=categories,
            series=series,
            normalize=normalize,
            bar_width=bar_width,
            colors=fig.theme.get("colors"),
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
        Unified entry point - mirrors ``glyphx.plot()`` but operates on
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
