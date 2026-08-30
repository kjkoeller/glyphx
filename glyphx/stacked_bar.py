"""
GlyphX StackedBarSeries - stacked and 100%-stacked bar charts.

Matplotlib requires manual ``bottom=`` accumulation across multiple
``ax.bar()`` calls.  Seaborn has no native stacked bar.  GlyphX handles
the entire stack computation internally.

    from glyphx import Figure
    from glyphx.stacked_bar import StackedBarSeries

    fig = Figure(auto_display=False)
    fig.add(StackedBarSeries(
        x=["Q1","Q2","Q3","Q4"],
        series={
            "Cloud":    [1.2, 1.5, 1.8, 2.1],
            "AI/ML":    [0.8, 1.0, 1.3, 1.6],
            "Mobile":   [0.5, 0.6, 0.7, 0.9],
        },
        normalize=False,   # True → 100% stacked
    ))
    fig.show()
"""
from __future__ import annotations

import numpy as np

from ._typing import AxesLike
from .series import BaseSeries
from .themes import themes as _themes
from .utils import stable_id, svg_escape


class StackedBarSeries(BaseSeries):
    #: Segments are measured from zero, so the domain must include it.
    zero_anchored = True

    """
    Stacked bar chart - multiple series stacked vertically per category.

    Args:
        x:          Category labels for the X-axis.
        series:     ``{label: [values]}`` mapping.  Order determines stack order
                    (first key is at the bottom).
        colors:     Per-series hex colors.  Falls back to the active theme palette.
        normalize:  If ``True``, bars are normalized to 100% (proportional stacking).
        bar_width:  Fraction of the available slot width per bar (0–1).
        label:      Legend label (not used; each sub-series has its own label).
    """

    def __init__(
        self,
        x: list,
        series: dict[str, list[float]],
        colors: list[str] | None  = None,
        normalize: bool           = False,
        bar_width: float          = 0.75,
        label: str | None         = None,
    ) -> None:
        self.categories = list(x)
        self.stacks     = series              # OrderedDict-stable in 3.7+
        self.normalize  = normalize
        self.bar_width  = float(bar_width)

        palette = _themes["default"]["colors"]
        self.colors = colors or palette

        # Pre-compute per-category totals for normalization
        names     = list(series.keys())
        n_cats    = len(x)
        n_stacks  = len(names)
        self._mat = np.zeros((n_stacks, n_cats))   # [stack_i, cat_j]
        for i, name in enumerate(names):
            self._mat[i] = series[name]

        if normalize:
            # Divide by the absolute total, not the signed one. A bar
            # holding +5 and -5 sums to zero, and dividing by that is either
            # a ZeroDivisionError or percentages with the wrong sign.
            totals = np.abs(self._mat).sum(axis=0)
            totals = np.where(totals == 0, 1, totals)
            self._mat = self._mat / totals * 100

        # Positive and negative segments accumulate away from zero
        # independently, so the extent of a bar is the sum of its positive
        # parts above the axis and the sum of its negative parts below it --
        # not the signed total, which cancels and understates both.
        pos_totals = np.clip(self._mat, 0, None).sum(axis=0)
        neg_totals = np.clip(self._mat, None, 0).sum(axis=0)
        y_max = float(pos_totals.max()) if pos_totals.size else 0.0
        y_min = float(neg_totals.min()) if neg_totals.size else 0.0

        super().__init__(
            x=list(x),
            y=[min(0.0, y_min), max(0.0, y_max)],
            color=self.colors[0],
            label=label,
        )
        # Register categorical x mapping for render_grid
        self._x_categories = list(x)
        self._numeric_x    = [i + 0.5 for i in range(n_cats)]

        # Derive the CSS class from content so repeated renders are
        # byte-identical; id(self) changes every run.
        self.css_class = "series-" + stable_id(
            "StackedBarSeries", label, tuple(self.categories),
            tuple(names), self._mat.shape, length=8,
        )

    def to_svg(self, ax: AxesLike, use_y2: bool = False) -> str:
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y
        elements: list[str] = []

        # Pixel slot width
        n_cats  = len(self.categories)
        if n_cats > 1:
            px_slot = ax.scale_x(1.5) - ax.scale_x(0.5)
        else:
            px_slot = (ax.width - 2 * ax.padding) * 0.8
        px_bar  = px_slot * self.bar_width

        names = list(self.stacks.keys())

        # TODO: segment labels. Skipped for now because a thin segment has
        # nowhere to put one and the leader-line logic to place it outside
        # the bar is a bigger job than it looks.
        for cat_j, cat in enumerate(self.categories):
            cx = ax.scale_x(cat_j + 0.5)

            # Two accumulators from zero, up and down. One running total
            # would let a negative pull the baseline back and draw the next
            # positive segment over an earlier one.
            cum_pos = 0.0
            cum_neg = 0.0

            for stack_i, name in enumerate(names):
                val = float(self._mat[stack_i, cat_j])
                if val >= 0:
                    base_v, top_v = cum_pos, cum_pos + val
                    cum_pos = top_v
                else:
                    base_v, top_v = cum_neg, cum_neg + val
                    cum_neg = top_v

                py_top = scale_y(top_v)
                py_bot = scale_y(base_v)
                h      = abs(py_bot - py_top)
                color  = self.colors[stack_i % len(self.colors)]

                if h < 0.5:        # skip invisibly thin segments
                    continue

                label_txt = f"{val:.1f}{'%' if self.normalize else ''}"
                tooltip = (
                    f'data-x="{svg_escape(str(cat))}" '
                    f'data-label="{svg_escape(name)}" '
                    f'data-value="{svg_escape(label_txt)}"'
                )
                elements.append(
                    f'<rect class="glyphx-point {self.css_class}" '
                    f'x="{cx - px_bar / 2:.1f}" y="{min(py_top, py_bot):.1f}" '
                    f'width="{px_bar:.1f}" height="{h:.1f}" '
                    f'fill="{color}" stroke="#fff" stroke-width="0.5" '
                    f'{tooltip}/>'
                )

        # Inline legend (right gutter handled by Figure, but add per-stack colors)
        # The caller's draw_legend handles the actual gutter legend;
        # we expose each stack as a labelled sub-series by registering them.
        return "\n".join(elements)

    # Expose stack names/colors so draw_legend can render them
    @property
    def _legend_entries(self) -> list[tuple[str, str]]:
        names = list(self.stacks.keys())
        return [(n, self.colors[i % len(self.colors)])
                for i, n in enumerate(names)]
