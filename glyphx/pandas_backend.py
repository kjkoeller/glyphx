"""
GlyphX as a pandas plotting backend.

    pd.options.plotting.backend = "glyphx"
    df.plot(x="month", y="revenue")

Registered under the ``pandas_plotting_backends`` entry point (see
``pyproject.toml``), so the string above resolves here.

That registration matters more than it looks. Before this module existed,
pandas had nothing registered under that name, so it fell back to importing
the ``glyphx`` package directly and checking for a top-level ``.plot``
attribute -- found one, since ``glyphx.plot()`` is an unrelated convenience
function, and accepted the assignment with no error. The break only
surfaced on the first real call: ``df.plot(x="x", y="y")`` raised
``TypeError: plot() got multiple values for argument 'x'``, because pandas
calls ``module.plot(data, x=x, y=y, kind=kind, **kwargs)`` and that
positional ``data`` collided with ``glyphx.plot``'s own first parameter.
Silent acceptance followed by a crash on first use is worse than refusing
the assignment outright, since it fails at the exact moment someone is
trying you out.

Scope. For any backend other than its own, pandas hands over the raw data
and keyword arguments and steps aside entirely -- see
``pandas.plotting._core.PlotAccessor.__call__``, where everything past the
backend dispatch (x/y column resolution, the dataframe/series-kind split)
is matplotlib-only code that a third-party backend never benefits from and
must redo itself. This module covers the common cases (the kinds and
keyword arguments below) rather than that full surface, and raises for
anything it does not implement instead of silently ignoring part of the
call -- a chart that dropped ``xlim=`` without saying so would look
finished while quietly not being what was asked for.
"""

from __future__ import annotations

from typing import Any

#: kind= values this backend draws. hexbin has no equivalent in glyphx
#: (it is a 2-D density heatmap over continuous x/y, not a categorical
#: chart), and barh has no horizontal-bar series to map onto.
_SUPPORTED_KINDS = frozenset({
    "line", "bar", "hist", "box", "kde", "density", "area", "pie", "scatter",
})

#: Keyword arguments pandas may forward that this backend does not
#: implement. Rejected explicitly rather than silently accepted: a
#: DataFrame.plot(ax=existing_ax) call that quietly drew a *new* figure
#: instead of reusing the one given would be a worse outcome than an error.
_UNSUPPORTED_KWARGS = frozenset({
    "ax", "secondary_y", "table", "layout", "xticks", "yticks",
    "xlim", "ylim", "rot", "fontsize", "style", "sharey",
})


def _check_supported(kind: str, kwargs: dict) -> None:
    """Raise for a kind or keyword this backend does not implement."""
    if kind == "density":
        kind = "kde"
    if kind not in _SUPPORTED_KINDS:
        raise NotImplementedError(
            f"glyphx's pandas backend does not support kind={kind!r}. "
            f"Supported: {', '.join(sorted(_SUPPORTED_KINDS))}. Switch back "
            f"with pd.options.plotting.backend = 'matplotlib' for this call."
        )
    blocked = _UNSUPPORTED_KWARGS & kwargs.keys()
    if blocked:
        raise NotImplementedError(
            f"glyphx's pandas backend does not support: {', '.join(sorted(blocked))}. "
            f"Drop these arguments, or use "
            f"pd.options.plotting.backend = 'matplotlib' for this call."
        )
    if kwargs.get("use_index") is False:
        raise NotImplementedError(
            "glyphx's pandas backend always plots against the index when no "
            "x= is given; use_index=False is not supported."
        )


def _resolve_column(columns, value):
    """A column label as given, or an integer position resolved against
    ``columns`` -- matplotlib accepts both."""
    if isinstance(value, int) and not isinstance(value, bool) and value not in columns:
        return columns[value]
    return value


def _numeric_columns(df):
    """Column labels of every numeric column, in the frame's own order."""
    import pandas as pd
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def _coordinate_series(df, x, y):
    """
    Resolve (x, y) into ``(x_values, [(label, y_values), ...])`` for the
    coordinate-pair kinds: line, bar, area, scatter.

    Mirrors matplotlib's own resolution: an omitted x uses the index; an
    omitted y uses every remaining numeric column, so ``df.plot()`` with no
    arguments draws one series per numeric column against the index, the
    same as it always has.
    """
    columns = list(df.columns)
    if x is not None:
        x = _resolve_column(columns, x)
    if y is not None:
        y = ([_resolve_column(columns, v) for v in y] if isinstance(y, (list, tuple))
             else _resolve_column(columns, y))

    if x is not None and y is None:
        y_cols = [c for c in _numeric_columns(df) if c != x]
        return df[x].tolist(), [(str(c), df[c].tolist()) for c in y_cols]
    if y is not None:
        y_cols = y if isinstance(y, list) else [y]
        x_vals = df[x].tolist() if x is not None else df.index.tolist()
        return x_vals, [(str(c), df[c].tolist()) for c in y_cols]
    return df.index.tolist(), [(str(c), df[c].tolist()) for c in _numeric_columns(df)]


def _value_columns(df, y):
    """Resolve which columns to use for the value-only kinds: hist, kde, box."""
    if y is None:
        return _numeric_columns(df)
    columns = list(df.columns)
    y = ([_resolve_column(columns, v) for v in y] if isinstance(y, (list, tuple))
         else _resolve_column(columns, y))
    return y if isinstance(y, list) else [y]


def _apply_presentation(fig, kwargs: dict, *, default_legend: bool) -> None:
    """Title, labels, legend, grid, log scales and colour -- the kwargs
    that apply the same way regardless of chart kind."""
    if kwargs.get("title"):
        fig.set_title(kwargs["title"])
    if kwargs.get("xlabel"):
        fig.set_xlabel(kwargs["xlabel"])
    if kwargs.get("ylabel"):
        fig.set_ylabel(kwargs["ylabel"])

    legend = kwargs.get("legend", default_legend)
    fig.set_legend("top-right" if legend else False)

    if kwargs.get("grid") is False:
        fig.axes.show_grid = False
    if kwargs.get("logx"):
        fig.axes.xscale = "log"
    if kwargs.get("logy"):
        fig.axes.yscale = "log"


def _colors(kwargs: dict, n: int) -> list | None:
    """Map colormap= to glyphx's own palette machinery, by name."""
    name = kwargs.get("colormap")
    if not name:
        return None
    from .colormaps import colormap_colors, list_colormaps

    if name not in list_colormaps():
        raise NotImplementedError(
            f"colormap={name!r} is not one of glyphx's colormaps: "
            f"{', '.join(list_colormaps())}. Matplotlib-only colormap names "
            f"are not translated."
        )
    return colormap_colors(name, n)


def _figure(kwargs: dict, **overrides):
    """A Figure sized from figsize=, if given."""
    from . import Figure

    width, height = 640, 480
    if kwargs.get("figsize"):
        # matplotlib's figsize is inches at a nominal 100 dpi; there is no
        # true equivalent since glyphx has no dpi concept, but this keeps
        # the aspect ratio and rough scale a caller asked for.
        w_in, h_in = kwargs["figsize"]
        width, height = int(w_in * 100), int(h_in * 100)
    return Figure(width=width, height=height, auto_display=False, **overrides)


def plot(data, x=None, y=None, kind: str = "line", **kwargs: Any):
    """
    Entry point pandas calls for ``df.plot()`` / ``series.plot()`` and the
    ``df.plot.line()``-style accessors, once
    ``pd.options.plotting.backend = "glyphx"`` is set.

    Not meant to be called directly -- see :meth:`~glyphx.Figure.line` and
    friends, or the DataFrame accessor at :mod:`glyphx.accessor`, for
    GlyphX's own plotting APIs.

    Returns:
        Figure: ready to ``.show()``, ``.share()`` or ``.save()``. Also
        displays automatically in a notebook, the same as any other GlyphX
        figure -- matplotlib's backend returns an ``Axes`` instead, which is
        the one difference a caller migrating existing code will notice in
        the return value.
    """
    import pandas as pd

    kind = "kde" if kind == "density" else kind
    _check_supported(kind, kwargs)

    if isinstance(data, pd.Series):
        return _plot_series(data, kind, **kwargs)
    if isinstance(data, pd.DataFrame):
        return _plot_dataframe(data, x, y, kind, **kwargs)
    raise TypeError(
        f"glyphx's pandas backend expected a Series or DataFrame, got "
        f"{type(data).__name__}."
    )


def _plot_series(s, kind: str, **kwargs):
    """The Series path: one value per index entry, no x/y column resolution needed."""
    from . import BoxPlotSeries, HistogramSeries, KDESeries, LineSeries, PieSeries

    label = s.name if s.name is not None else ""
    fig = _figure(kwargs)

    if kind == "line":
        fig.add(LineSeries(s.index.tolist(), s.tolist(), label=label))
    elif kind == "bar":
        fig.add(_bar_series([(label, s.tolist())], [str(v) for v in s.index]))
    elif kind == "hist":
        fig.add(HistogramSeries(s.dropna().tolist(), label=label))
    elif kind == "kde":
        fig.add(KDESeries(s.dropna().tolist(), label=label))
    elif kind == "box":
        fig.add(BoxPlotSeries(data=[s.dropna().tolist()], categories=[label or "value"]))
    elif kind == "area":
        fig.add(_area_series([(label, s.tolist())], s.index.tolist(), kwargs))
    elif kind == "pie":
        fig.add(PieSeries(values=s.tolist(), labels=[str(v) for v in s.index],
                          colors=_colors(kwargs, len(s))))
    elif kind == "scatter":
        raise ValueError("kind='scatter' requires a DataFrame with x= and y=.")

    _apply_presentation(fig, kwargs, default_legend=False)
    return fig


def _plot_dataframe(df, x, y, kind: str, **kwargs):
    """The DataFrame path: resolves x/y, then dispatches by kind."""
    from . import BoxPlotSeries, HistogramSeries, KDESeries, PieSeries

    subplots = bool(kwargs.get("subplots"))

    if kind in ("line", "bar", "area", "scatter"):
        if kind == "scatter":
            if x is None or y is None or isinstance(y, (list, tuple)):
                raise ValueError("kind='scatter' requires a single x= and y=.")
            x_vals, pairs = df[_resolve_column(list(df.columns), x)].tolist(), [
                (str(y), df[_resolve_column(list(df.columns), y)].tolist())]
        else:
            x_vals, pairs = _coordinate_series(df, x, y)

        if subplots:
            fig = _grid_figure(kwargs, len(pairs))
            colors = _colors(kwargs, len(pairs))
            for i, (label, y_vals) in enumerate(pairs):
                ax = fig.add_axes(i, 0)
                ax.add_series(_one_series(kind, x_vals, y_vals, label,
                                          colors[i] if colors else None))
            return fig

        fig = _figure(kwargs)
        if kind == "bar" and len(pairs) > 1:
            fig.add(_bar_series(pairs, [str(v) for v in x_vals],
                                colors=_colors(kwargs, len(pairs))))
        elif kind == "area":
            for series in _area_series(pairs, x_vals, kwargs):
                fig.add(series)
        else:
            colors = _colors(kwargs, len(pairs))
            for i, (label, y_vals) in enumerate(pairs):
                fig.add(_one_series(kind, x_vals, y_vals, label,
                                    colors[i] if colors else None))
        _apply_presentation(fig, kwargs, default_legend=len(pairs) > 1)
        return fig

    # Value-only kinds: hist, kde, box, pie -- x has no meaning here.
    columns = _value_columns(df, y)
    fig = _figure(kwargs)

    if kind == "hist":
        colors = _colors(kwargs, len(columns))
        for i, c in enumerate(columns):
            fig.add(HistogramSeries(df[c].dropna().tolist(), label=str(c),
                                    color=colors[i] if colors else None))
    elif kind == "kde":
        colors = _colors(kwargs, len(columns))
        for i, c in enumerate(columns):
            # KDESeries types color as str with its own default, so omit the
            # argument entirely rather than passing None through.
            extra = {"color": colors[i]} if colors else {}
            fig.add(KDESeries(df[c].dropna().tolist(), label=str(c), **extra))
    elif kind == "box":
        fig.add(BoxPlotSeries(data=[df[c].dropna().tolist() for c in columns],
                              categories=[str(c) for c in columns]))
    elif kind == "pie":
        if len(columns) != 1:
            raise ValueError(
                "kind='pie' needs exactly one column; pass y='column_name'."
            )
        col = columns[0]
        fig.add(PieSeries(values=df[col].tolist(),
                          labels=[str(v) for v in df.index],
                          colors=_colors(kwargs, len(df))))

    _apply_presentation(fig, kwargs, default_legend=len(columns) > 1)
    return fig


def _one_series(kind, x_vals, y_vals, label, color):
    """A single Line or Scatter series for one column."""
    from . import LineSeries, ScatterSeries
    cls = ScatterSeries if kind == "scatter" else LineSeries
    return cls(x_vals, y_vals, label=label, color=color)


def _bar_series(pairs, categories, colors=None):
    """A plain bar for one column, or a grouped bar across several."""
    from . import BarSeries, GroupedBarSeries

    if len(pairs) == 1:
        label, values = pairs[0]
        return BarSeries(categories, values, label=label,
                         color=colors[0] if colors else None)
    values = [[y_vals[i] for _, y_vals in pairs] for i in range(len(categories))]
    return GroupedBarSeries(groups=categories, categories=[label for label, _ in pairs],
                            values=values, group_colors=colors)


def _area_series(pairs, x_vals, kwargs):
    """
    One FillBetweenSeries per column, stacked cumulatively by default --
    matplotlib's ``DataFrame.plot.area`` stacks unless ``stacked=False``.
    """
    from . import FillBetweenSeries

    stacked = kwargs.get("stacked", True)
    out = []
    baseline = [0.0] * len(x_vals)
    for label, y_vals in pairs:
        top = y_vals if not stacked else [b + v for b, v in zip(baseline, y_vals)]
        out.append(FillBetweenSeries(x_vals, baseline if stacked else [0.0] * len(x_vals),
                                     top, label=label))
        if stacked:
            baseline = top
    return out


def _grid_figure(kwargs, n):
    """An n-row subplot grid, sharing the X axis when sharex= was given."""
    shared_x = bool(kwargs.get("sharex"))
    fig = _figure(kwargs, rows=n, cols=1, shared_x=shared_x)
    return fig
