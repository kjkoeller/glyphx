"""
GlyphX Natural Language Chart Generation.

``glyphx.from_prompt()`` lets you describe a chart in plain English
and get back a fully rendered Figure — no axis wrangling, no theme
fiddling, no column juggling.

Requires the ``anthropic`` Python package::

    pip install anthropic

And an API key, either passed directly or via the ``ANTHROPIC_API_KEY``
environment variable.

Example::

    import pandas as pd
    from glyphx import from_prompt

    df = pd.read_csv("sales.csv")
    fig = from_prompt("bar chart of total revenue by region", df=df)
    fig.share("revenue_by_region.html")
"""

from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# JSON schema the LLM must return
_SCHEMA_DOC = """\
Return ONLY a JSON object (no markdown fences, no explanation) with this schema:

{
  "kind":      "line" | "bar" | "scatter" | "pie" | "donut" | "hist" | "box",
  "x":         "<column name or null>",
  "y":         "<column name or null>",
  "groupby":   "<column name or null>",
  "agg":       "sum" | "mean" | "count" | "max" | "min",
  "bins":      <integer, for hist only>,
  "title":     "<chart title or null>",
  "theme":     "default"|"dark"|"colorblind"|"pastel"|"warm"|"ocean"|"monochrome",
  "color":     "<hex color or null>",
  "label":     "<series label or null>",
  "xlabel":    "<x-axis label or null>",
  "ylabel":    "<y-axis label or null>",
  "sort_by":   "x" | "y" | null,
  "sort_desc": true | false,
  "top_n":     <integer or null — keep only top N rows after aggregation>,
  "reasoning": "<one-sentence explanation of your choices>"
}

Rules:
- kind must be one of the listed values
- x/y/groupby must be exact column names from the schema, or null
- agg defaults to "sum" when groupby is set
- bins defaults to 10
- theme defaults to "default"
- top_n is useful for "top 10 X by Y" queries
- sort_desc defaults to true when top_n is set, false otherwise
"""

_SYSTEM_PROMPT = (
    "You are a data visualisation expert who configures GlyphX charts.\n"
    "Given a user's description and optional DataFrame schema, choose the best "
    "chart type, map columns to axes, select a fitting theme, and return the "
    "configuration as JSON.\n\n"
    + _SCHEMA_DOC
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def from_prompt(
    prompt: str,
    df=None,
    api_key: str = None,
    model: str = "claude-sonnet-4-20250514",
    auto_display: bool = True,
) -> "Figure":  # noqa: F821
    """
    Generate a GlyphX Figure from a plain-English description.

    Args:
        prompt (str): Natural language description of the desired chart,
                      e.g. ``"bar chart of monthly revenue grouped by region"``.
        df (pd.DataFrame | None): DataFrame to plot.  Column names, dtypes,
                                   and a sample are sent to the model so it
                                   can choose sensible x/y mappings.
        api_key (str | None): Anthropic API key.  Falls back to the
                               ``ANTHROPIC_API_KEY`` environment variable.
        model (str): Anthropic model name.
        auto_display (bool): Auto-render and show the figure when True.

    Returns:
        Figure: A fully configured and rendered GlyphX Figure.

    Raises:
        ImportError: If the ``anthropic`` package is not installed.
        ValueError: If no API key is found.
        json.JSONDecodeError: If the model returns unparseable JSON
                              (rarely happens; usually recoverable).

    Examples::

        # Simple — no data, just a chart type hint
        fig = from_prompt("show me a sample line chart of sin(x)", auto_display=False)

        # With a DataFrame
        import pandas as pd
        df = pd.DataFrame({"month": range(1,13), "sales": [120,135,98,...]})
        fig = from_prompt("line chart of sales over time", df=df)

        # Grouped bar
        fig = from_prompt(
            "top 5 products by total revenue, grouped by region",
            df=sales_df,
        )
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "Natural language chart generation requires the anthropic package.\n"
            "Install it with:  pip install anthropic"
        )

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "No Anthropic API key found.  Either pass api_key= or set the "
            "ANTHROPIC_API_KEY environment variable."
        )

    # Build the user message
    user_parts = [prompt]
    if df is not None:
        user_parts.append(_df_context(df))

    user_msg = "\n\n".join(user_parts)

    client   = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()
    config = _parse_json(raw)

    return _build_figure(config, df, auto_display=auto_display)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _df_context(df) -> str:
    """Format a DataFrame's schema and sample for the LLM."""
    try:
        sample = df.head(5).to_string(index=False)
    except Exception:
        sample = "(sample unavailable)"

    numeric_cols  = df.select_dtypes(include="number").columns.tolist()
    category_cols = df.select_dtypes(exclude="number").columns.tolist()

    return (
        f"DataFrame schema:\n"
        f"  Shape    : {df.shape[0]:,} rows × {df.shape[1]} columns\n"
        f"  Numeric  : {numeric_cols}\n"
        f"  Categorical: {category_cols}\n"
        f"  Dtypes   : {df.dtypes.to_dict()}\n\n"
        f"First 5 rows:\n{sample}"
    )


def _parse_json(raw: str) -> dict:
    """Strip markdown fences if present, then parse JSON."""
    # Remove ```json ... ``` fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw.strip())


def _coerce(df, col: str):
    """Return df[col].tolist(), or None if col is None / not in df."""
    if col is None or df is None:
        return None
    if col not in df.columns:
        return None
    return df[col].tolist()


def _build_figure(config: dict, df, auto_display: bool = True):
    """
    Translate a config dict returned by the LLM into a GlyphX Figure.

    Handles:
    - Aggregation (groupby + agg)
    - top_n filtering
    - Sorting
    - Multi-series (groupby without aggregation)
    - All supported chart kinds
    """
    import numpy as np
    from .figure import Figure
    from .series import (
        LineSeries, BarSeries, ScatterSeries,
        PieSeries, DonutSeries, HistogramSeries, BoxPlotSeries,
    )

    kind    = config.get("kind", "line").lower()
    title   = config.get("title")
    theme   = config.get("theme", "default")
    color   = config.get("color")
    label   = config.get("label")
    xlabel  = config.get("xlabel")
    ylabel  = config.get("ylabel")
    x_col   = config.get("x")
    y_col   = config.get("y")
    groupby = config.get("groupby")
    agg     = config.get("agg", "sum")
    bins    = int(config.get("bins") or 10)
    sort_by   = config.get("sort_by")
    sort_desc = bool(config.get("sort_desc", False))
    top_n     = config.get("top_n")

    fig = Figure(title=title, theme=theme, auto_display=False)
    fig.axes.xlabel = xlabel
    fig.axes.ylabel = ylabel

    # ── No DataFrame: generate illustrative sample data ──────────────────
    if df is None:
        fig = _build_sample_figure(kind, title, theme, color, label, fig)
        if auto_display:
            fig.show()
        return fig

    # ── Axis-free kinds (hist, box, pie, donut) ───────────────────────────
    if kind == "hist":
        col  = y_col or x_col or df.select_dtypes(include="number").columns[0]
        data = df[col].dropna().tolist()
        fig.add(HistogramSeries(data, bins=bins, color=color, label=label or col))
        if auto_display: fig.show()
        return fig

    if kind == "box":
        if groupby and groupby in df.columns:
            groups = df[groupby].unique().tolist()
            col    = y_col or df.select_dtypes(include="number").columns[0]
            arrays = [df[df[groupby] == g][col].dropna().tolist() for g in groups]
            fig.add(BoxPlotSeries(arrays, categories=[str(g) for g in groups],
                                  color=color or "#1f77b4"))
        else:
            col  = y_col or x_col or df.select_dtypes(include="number").columns[0]
            data = df[col].dropna().tolist()
            fig.add(BoxPlotSeries(data, color=color or "#1f77b4", label=label or col))
        if auto_display: fig.show()
        return fig

    if kind in {"pie", "donut"}:
        values, labels = _pie_data(df, x_col, y_col, agg)
        if kind == "pie":
            fig.add(PieSeries(values, labels=labels))
        else:
            fig.add(DonutSeries(values, labels=[str(l) for l in labels]))
        if auto_display: fig.show()
        return fig

    # ── Aggregation (groupby) → single or multi-series ───────────────────
    if groupby and groupby in df.columns:
        theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])

        if x_col and y_col and x_col in df.columns and y_col in df.columns:
            # Pivot: x = x_col, one series per groupby value
            for i, (grp_val, grp_df) in enumerate(df.groupby(groupby)):
                grp_color = theme_colors[i % len(theme_colors)]
                x_data    = grp_df[x_col].tolist()
                y_data    = grp_df[y_col].tolist()
                s         = _make_series(kind, x_data, y_data, grp_color, str(grp_val))
                if s: fig.add(s)
        else:
            # Aggregate y_col by groupby
            num_col  = y_col or df.select_dtypes(include="number").columns[0]
            agg_func = {"sum": "sum", "mean": "mean", "count": "count",
                        "max": "max", "min": "min"}.get(agg, "sum")
            agg_df   = df.groupby(groupby)[num_col].agg(agg_func).reset_index()
            agg_df.columns = [groupby, num_col]

            agg_df = _apply_sort_top(agg_df, groupby, num_col, sort_by, sort_desc, top_n)

            x_data = agg_df[groupby].tolist()
            y_data = agg_df[num_col].tolist()
            s      = _make_series(kind, x_data, y_data, color, label or f"{agg}({num_col})")
            if s: fig.add(s)

    # ── Simple x / y mapping ─────────────────────────────────────────────
    else:
        work_df = df.copy()
        if sort_by == "y" and y_col in work_df.columns:
            work_df = work_df.sort_values(y_col, ascending=not sort_desc)
        elif sort_by == "x" and x_col in work_df.columns:
            work_df = work_df.sort_values(x_col, ascending=not sort_desc)

        if top_n:
            work_df = work_df.head(int(top_n))

        x_data = _coerce(work_df, x_col) or list(range(len(work_df)))
        y_data = _coerce(work_df, y_col) or work_df.select_dtypes(include="number").iloc[:, 0].tolist()

        s = _make_series(kind, x_data, y_data, color, label or y_col)
        if s: fig.add(s)

    if auto_display:
        fig.show()
    return fig


def _make_series(kind, x, y, color, label):
    """Instantiate the right series class."""
    from .series import LineSeries, BarSeries, ScatterSeries
    if kind == "bar":     return BarSeries(x, y, color=color, label=label)
    if kind == "scatter": return ScatterSeries(x, y, color=color, label=label)
    return LineSeries(x, y, color=color, label=label)  # default / "line"


def _pie_data(df, x_col, y_col, agg):
    """Extract (values, labels) for pie/donut from a DataFrame."""
    if x_col and y_col and x_col in df.columns and y_col in df.columns:
        grp = df.groupby(x_col)[y_col]
        fn  = {"sum": grp.sum, "mean": grp.mean, "count": grp.count,
               "max": grp.max, "min": grp.min}.get(agg, grp.sum)
        agg_df = fn().reset_index()
        return agg_df[y_col].tolist(), agg_df[x_col].tolist()
    if y_col and y_col in df.columns:
        return df[y_col].tolist(), list(range(len(df)))
    col = df.select_dtypes(include="number").columns[0]
    return df[col].tolist(), list(range(len(df)))


def _apply_sort_top(df, x_col, y_col, sort_by, sort_desc, top_n):
    if sort_by == "y" or top_n:
        df = df.sort_values(y_col, ascending=not sort_desc)
    elif sort_by == "x":
        df = df.sort_values(x_col, ascending=not sort_desc)
    if top_n:
        df = df.head(int(top_n))
    return df


def _build_sample_figure(kind, title, theme, color, label, fig):
    """Return a figure with illustrative data when no DataFrame is given."""
    import math
    from .series import LineSeries, BarSeries, ScatterSeries, PieSeries, DonutSeries, HistogramSeries, BoxPlotSeries

    color = color or "#1f77b4"

    if kind == "bar":
        fig.add(BarSeries(["A", "B", "C", "D", "E"], [23, 47, 31, 56, 38],
                          color=color, label=label or "Sample"))
    elif kind == "scatter":
        import random, math
        random.seed(42)
        x = [random.gauss(0, 1) for _ in range(60)]
        y = [v + random.gauss(0, 0.5) for v in x]
        fig.add(ScatterSeries(x, y, color=color, label=label or "Sample"))
    elif kind == "pie":
        fig.add(PieSeries([30, 25, 20, 15, 10],
                          labels=["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]))
    elif kind == "donut":
        fig.add(DonutSeries([30, 25, 20, 15, 10],
                            labels=["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]))
    elif kind == "hist":
        import random
        random.seed(0)
        data = [random.gauss(50, 15) for _ in range(200)]
        from .series import HistogramSeries
        fig.add(HistogramSeries(data, bins=15, color=color))
    elif kind == "box":
        import random
        random.seed(1)
        fig.add(BoxPlotSeries([random.gauss(50, 10) for _ in range(100)],
                              color=color, label=label or "Sample"))
    else:  # line (default)
        x = list(range(20))
        y = [math.sin(i * 0.4) * 10 + 20 for i in x]
        fig.add(LineSeries(x, y, color=color, label=label or "Sample"))

    return fig
