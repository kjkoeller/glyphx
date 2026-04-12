"""
GlyphX StackedBarSeries — stacked and 100%-stacked bar charts.

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
from .series import BaseSeries
from .utils  import svg_escape, _format_tick
from .themes import themes as _themes


class StackedBarSeries(BaseSeries):
    """
    Stacked bar chart — multiple series stacked vertically per category.

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
        self.css_class  = f"series-{id(self) % 100000}"

        palette = _themes["default"]["colors"]
        self.colors = colors or palette

        # Pre-compute per-category totals for normalization
        names     = list(series.keys())
        n_cats    = len(x)
        n_stacks  = len(names)
        self._mat = np.zeros((n_stacks, n_cats))   # [stack_i, cat_j]
        for i, name in enumerate(names):
            self._mat[i] = series[name]

        totals = self._mat.sum(axis=0)             # total per category
        if normalize:
            # Avoid div-by-zero
            totals = np.where(totals == 0, 1, totals)
            self._mat = self._mat / totals * 100

        # BaseSeries x/y for domain
        y_max = float(self._mat.sum(axis=0).max())
        super().__init__(
            x=list(x),
            y=[0.0, y_max],
            color=self.colors[0],
            label=label,
        )
        # Register categorical x mapping for render_grid
        self._x_categories = list(x)
        self._numeric_x    = [i + 0.5 for i in range(n_cats)]

    def to_svg(self, ax: object, use_y2: bool = False) -> str:  # type: ignore
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y       # type: ignore
        y0       = scale_y(0)
        elements: list[str] = []

        font = ax.theme.get("font", "sans-serif")   # type: ignore
        tc   = ax.theme.get("text_color", "#000")   # type: ignore

        # Pixel slot width
        n_cats  = len(self.categories)
        if n_cats > 1:
            px_slot = ax.scale_x(1.5) - ax.scale_x(0.5)   # type: ignore
        else:
            px_slot = (ax.width - 2 * ax.padding) * 0.8    # type: ignore
        px_bar  = px_slot * self.bar_width

        names = list(self.stacks.keys())

        for cat_j, cat in enumerate(self.categories):
            cx      = ax.scale_x(cat_j + 0.5)   # type: ignore
            cumsum  = 0.0

            for stack_i, name in enumerate(names):
                val    = float(self._mat[stack_i, cat_j])
                top_v  = cumsum + val
                py_top = scale_y(top_v)
                py_bot = scale_y(cumsum)
                h      = abs(py_bot - py_top)
                color  = self.colors[stack_i % len(self.colors)]

                if h < 0.5:        # skip invisibly thin segments
                    cumsum = top_v
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
                cumsum = top_v

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
