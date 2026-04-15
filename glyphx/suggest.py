"""
GlyphX glyphx.suggest(df) -- AI-powered chart recommendation.

Inspects a DataFrame's column types, cardinality, and distribution
shape, then returns ranked chart suggestions with mini SVG previews.
No external dependencies -- the entire analysis runs in pure Python/NumPy.

    from glyphx import suggest
    import pandas as pd

    df = pd.read_csv("sales.csv")
    recs = suggest(df)          # list of Recommendation objects
    for rec in recs[:3]:
        print(rec.kind, rec.reason)
        rec.preview.show()      # render the mini preview
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Recommendation dataclass
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    """
    A single chart recommendation.

    Attributes:
        kind:      GlyphX chart kind string  (e.g. ``"line"``, ``"bar"``).
        score:     Confidence score 0-100.
        reason:    Human-readable explanation of why this chart suits the data.
        x_col:     Suggested X-axis column (or None).
        y_col:     Suggested Y-axis column (or None for univariate charts).
        hue_col:   Suggested hue/group column (or None).
        extra:     Additional kwargs to pass to the chart constructor.
        preview:   A :class:`~glyphx.Figure` rendered at 340x220 with
                   representative sample data.  Rendered lazily on first access.
    """
    kind:    str
    score:   float
    reason:  str
    x_col:   str | None        = None
    y_col:   str | None        = None
    hue_col: str | None        = None
    extra:   dict[str, Any]    = field(default_factory=dict)
    _df:     Any               = field(default=None, repr=False)
    _fig:    Any               = field(default=None, repr=False)

    @property
    def preview(self):
        """Render and cache a 340x220 mini preview figure."""
        if self._fig is None:
            self._fig = _render_preview(self)
        return self._fig

    def __repr__(self) -> str:
        return (f"<Recommendation kind={self.kind!r} score={self.score:.0f} "
                f"x={self.x_col!r} y={self.y_col!r}>")


# ---------------------------------------------------------------------------
# Column profiling helpers
# ---------------------------------------------------------------------------

def _is_datetime_col(col: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(col):
        return True
    if col.dtype == object:
        sample = col.dropna().head(20)
        hit = 0
        for v in sample:
            try:
                pd.to_datetime(str(v))
                hit += 1
            except Exception:
                pass
        return hit > len(sample) * 0.8
    return False


def _cardinality(col: pd.Series) -> int:
    return col.nunique()


def _is_numeric(col: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(col)


def _is_categorical(col: pd.Series, max_card: int = 20) -> bool:
    return not _is_numeric(col) and _cardinality(col) <= max_card


def _is_high_card_str(col: pd.Series) -> bool:
    return col.dtype == object and _cardinality(col) > 50


def _distribution_shape(col: pd.Series) -> str:
    """Rough shape classifier: 'normal', 'skewed', 'bimodal', 'uniform'."""
    vals = col.dropna().values.astype(float)
    if len(vals) < 10:
        return "unknown"
    q1, med, q3 = np.percentile(vals, [25, 50, 75])
    mean = vals.mean()
    std  = vals.std()
    if std == 0:
        return "constant"
    skew = (mean - med) / std
    if abs(skew) < 0.2:
        return "normal"
    if abs(skew) < 0.8:
        return "skewed"
    return "skewed"


def _has_trend(col: pd.Series) -> bool:
    """True if a numeric column has a monotone trend > 60% of the time."""
    vals = col.dropna().values.astype(float)
    if len(vals) < 5:
        return False
    diffs = np.diff(vals)
    up    = (diffs > 0).sum()
    down  = (diffs < 0).sum()
    n     = len(diffs)
    return max(up, down) / n > 0.6


# ---------------------------------------------------------------------------
# Main recommendation engine
# ---------------------------------------------------------------------------

def suggest(
    df: pd.DataFrame,
    max_rows:    int = 500,
    top_n:       int = 5,
) -> list[Recommendation]:
    """
    Analyse a DataFrame and return ranked chart recommendations.

    The engine scores candidate chart types against the column profiles
    and returns the top ``top_n`` recommendations, each with a mini
    preview figure generated from a sample of the data.

    Args:
        df:       Input DataFrame.
        max_rows: Cap for the internal sample used for analysis (default 500).
        top_n:    Maximum number of recommendations to return (default 5).

    Returns:
        List of :class:`Recommendation` objects sorted by descending score.

    Example::

        from glyphx import suggest
        recs = suggest(df)
        for rec in recs:
            print(f"{rec.kind:15s}  score={rec.score:.0f}  {rec.reason}")
            rec.preview.show()
    """
    if df.empty:
        return []

    # Sample for performance
    sample = df.sample(min(max_rows, len(df)), random_state=42) if len(df) > max_rows else df.copy()

    # Column profiles
    num_cols  = [c for c in sample.columns if _is_numeric(sample[c])]
    cat_cols  = [c for c in sample.columns if _is_categorical(sample[c])]
    dt_cols   = [c for c in sample.columns if _is_datetime_col(sample[c])]
    str_cols  = [c for c in sample.columns if sample[c].dtype == object]

    n_rows = len(sample)
    n_cols = len(sample.columns)
    recs: list[Recommendation] = []

    # -- Line chart -------------------------------------------------
    if dt_cols and num_cols:
        x = dt_cols[0]; y = num_cols[0]
        score = 85
        hue   = cat_cols[0] if cat_cols and _cardinality(sample[cat_cols[0]]) <= 6 else None
        if _has_trend(sample[y]):
            score = 92
        recs.append(Recommendation(
            kind="line", score=score, x_col=x, y_col=y, hue_col=hue,
            reason=f"'{x}' is a datetime axis and '{y}' shows a trend over time.",
            _df=sample,
        ))
    elif num_cols and n_rows >= 10 and _has_trend(sample[num_cols[0]]):
        y = num_cols[0]
        recs.append(Recommendation(
            kind="line", score=70, x_col=None, y_col=y,
            reason=f"'{y}' has a monotone trend -- a line chart shows it clearly.",
            _df=sample,
        ))

    # -- Bar chart --------------------------------------------------
    if cat_cols and num_cols:
        x = cat_cols[0]; y = num_cols[0]
        card = _cardinality(sample[x])
        score = max(30, 90 - card * 2)
        hue   = cat_cols[1] if len(cat_cols) > 1 and _cardinality(sample[cat_cols[1]]) <= 6 else None
        recs.append(Recommendation(
            kind="bar", score=score, x_col=x, y_col=y, hue_col=hue,
            reason=(f"'{x}' has {card} categories and '{y}' is numeric -- "
                    "a bar chart compares groups."),
            _df=sample,
        ))

    # -- Scatter chart ----------------------------------------------
    if len(num_cols) >= 2:
        x = num_cols[0]; y = num_cols[1]
        corr = abs(sample[[x, y]].dropna().corr().iloc[0, 1])
        score = 60 + int(corr * 30)
        c     = num_cols[2] if len(num_cols) > 2 else None
        hue   = cat_cols[0] if cat_cols and _cardinality(sample[cat_cols[0]]) <= 8 else None
        recs.append(Recommendation(
            kind="scatter", score=score, x_col=x, y_col=y,
            hue_col=hue,
            reason=(f"'{x}' and '{y}' are both numeric (r={corr:.2f}) -- "
                    "scatter reveals their relationship."),
            extra={"c": c} if c else {},
            _df=sample,
        ))

    # -- Histogram --------------------------------------------------
    if num_cols:
        col   = num_cols[0]
        shape = _distribution_shape(sample[col])
        score = 70 if shape in ("normal", "skewed") else 55
        recs.append(Recommendation(
            kind="hist", score=score, x_col=col, y_col=None,
            reason=(f"'{col}' is continuous ({shape} distribution) -- "
                    "a histogram shows its shape."),
            _df=sample,
        ))

    # -- Box plot ---------------------------------------------------
    if cat_cols and num_cols:
        x = cat_cols[0]; y = num_cols[0]
        card  = _cardinality(sample[x])
        score = 65 if card <= 10 else 45
        recs.append(Recommendation(
            kind="box", score=score, x_col=x, y_col=y,
            reason=(f"Comparing '{y}' distribution across {card} groups of '{x}'."),
            _df=sample,
        ))

    # -- Heatmap ----------------------------------------------------
    if len(num_cols) >= 3 and n_rows <= 200:
        score = 60
        recs.append(Recommendation(
            kind="heatmap", score=score, x_col=None, y_col=None,
            reason=(f"Multiple numeric columns ({len(num_cols)}) with ≤200 rows -- "
                    "a correlation heatmap reveals relationships."),
            _df=sample,
        ))

    # -- Pie / donut ------------------------------------------------
    if cat_cols and num_cols:
        x = cat_cols[0]; y = num_cols[0]
        card = _cardinality(sample[x])
        if 2 <= card <= 7:
            score = 60
            recs.append(Recommendation(
                kind="donut", score=score, x_col=x, y_col=y,
                reason=(f"'{x}' has {card} categories -- a donut shows part-to-whole."),
                _df=sample,
            ))

    # -- Bubble -----------------------------------------------------
    if len(num_cols) >= 3:
        x, y, s = num_cols[0], num_cols[1], num_cols[2]
        recs.append(Recommendation(
            kind="bubble", score=58, x_col=x, y_col=y,
            reason=(f"Three numeric dimensions -- bubble encodes '{s}' as size."),
            extra={"size": s},
            _df=sample,
        ))

    # -- ECDF -------------------------------------------------------
    if num_cols and n_rows >= 30:
        recs.append(Recommendation(
            kind="ecdf", score=52, x_col=num_cols[0], y_col=None,
            reason=(f"ECDF shows the full cumulative distribution of '{num_cols[0]}' "
                    "with no bin-width choice needed."),
            _df=sample,
        ))

    # -- Parallel coordinates ----------------------------------------
    if len(num_cols) >= 4:
        score = 65 if len(num_cols) <= 8 else 50
        hue   = cat_cols[0] if cat_cols else None
        recs.append(Recommendation(
            kind="parallel", score=score,
            reason=(f"{len(num_cols)} numeric columns -- parallel coordinates "
                    "reveals multi-dimensional patterns."),
            extra={"axes": num_cols[:8]},
            hue_col=hue,
            _df=sample,
        ))

    # Sort and truncate
    recs.sort(key=lambda r: r.score, reverse=True)
    return recs[:top_n]


# ---------------------------------------------------------------------------
# Preview renderer
# ---------------------------------------------------------------------------

def _render_preview(rec: Recommendation):
    """Build a 340x220 mini Figure from the recommendation."""
    from .figure import Figure
    from .series import (LineSeries, BarSeries, ScatterSeries,
                         HistogramSeries, BoxPlotSeries, HeatmapSeries,
                         PieSeries, DonutSeries)

    df    = rec._df
    kind  = rec.kind
    x_col = rec.x_col
    y_col = rec.y_col
    hue   = rec.hue_col

    fig = Figure(width=340, height=220, auto_display=False)
    title = kind.upper()
    if x_col:
        title += f" -- {x_col}"
        if y_col:
            title += f" x {y_col}"
    fig.set_title(title)

    try:
        SAMPLE = 80  # keep preview fast

        if kind == "line":
            sample = df[[x_col, y_col]].dropna().head(SAMPLE)
            x_vals = list(range(len(sample))) if _is_datetime_col(df[x_col]) else sample[x_col].tolist()
            if hue:
                colors = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed"]
                for i, (g, gdf) in enumerate(df.groupby(hue)):
                    s = gdf[[x_col, y_col]].dropna().head(SAMPLE)
                    fig.add(LineSeries(list(range(len(s))), s[y_col].tolist(),
                                       color=colors[i % len(colors)], label=str(g), width=1.5))
            else:
                fig.add(LineSeries(x_vals, sample[y_col].tolist(), color="#2563eb", width=1.5))

        elif kind == "bar":
            agg = df.groupby(x_col)[y_col].mean().reset_index().head(12)
            fig.add(BarSeries(agg[x_col].tolist(), agg[y_col].tolist(), color="#2563eb", bar_width=0.7))

        elif kind == "scatter":
            s = df[[x_col, y_col]].dropna().head(SAMPLE)
            c_col = rec.extra.get("c")
            c_vals = df[c_col].head(SAMPLE).tolist() if c_col and c_col in df else None
            fig.add(ScatterSeries(s[x_col].tolist(), s[y_col].tolist(),
                                   c=c_vals, cmap="viridis", size=4))

        elif kind == "hist":
            vals = df[x_col].dropna().tolist()
            fig.add(HistogramSeries(vals, bins=20, color="#2563eb"))

        elif kind == "box":
            groups = df[x_col].unique()[:6]
            datasets = [df[df[x_col] == g][y_col].dropna().tolist() for g in groups]
            fig.add(BoxPlotSeries(datasets, categories=[str(g) for g in groups],
                                   color="#7c3aed", box_width=18))

        elif kind == "heatmap":
            nums = [c for c in df.columns if _is_numeric(df[c])][:8]
            corr = df[nums].corr().values.tolist()
            fig.add(HeatmapSeries(corr, row_labels=nums, col_labels=nums,
                                   show_values=True,
                                   cmap=["#1e40af","#93c5fd","#f0f0f0","#fca5a5","#b91c1c"]))

        elif kind in ("pie", "donut"):
            agg = df.groupby(x_col)[y_col].sum().reset_index().head(7)
            cls = DonutSeries if kind == "donut" else PieSeries
            from .colormaps import colormap_colors
            fig.add(cls(agg[y_col].tolist(),
                        labels=agg[x_col].tolist(),
                        colors=colormap_colors("viridis", len(agg))))

        elif kind == "bubble":
            s_col = rec.extra.get("size", y_col)
            s = df[[x_col, y_col, s_col]].dropna().head(SAMPLE) if s_col else df[[x_col, y_col]].dropna().head(SAMPLE)
            from .bubble import BubbleSeries
            fig.add(BubbleSeries(s[x_col].tolist(), s[y_col].tolist(),
                                  size=s[s_col].tolist() if s_col in s else 10,
                                  color="#2563eb", alpha=0.65, min_radius=4, max_radius=28))

        elif kind == "ecdf":
            from .ecdf import ECDFSeries
            fig.add(ECDFSeries(df[x_col].dropna().head(200).tolist(), color="#2563eb"))

        elif kind == "parallel":
            from .parallel_coords import ParallelCoordinatesSeries
            axes = rec.extra.get("axes", [])[:6]
            s = df[axes].dropna().head(SAMPLE)
            fig.add(ParallelCoordinatesSeries(s.values.tolist(), axes=axes,
                                               alpha=0.35, cmap="viridis"))

    except Exception:
        pass  # Preview failure should never crash the caller

    return fig
