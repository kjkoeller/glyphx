"""
GlyphX DivergingBarSeries — horizontal bars radiating left (negative) and
right (positive) from a shared zero baseline.

Standard for survey results (agree/disagree), before/after comparisons,
sentiment analysis, and budget variance reports.  None of the three
major libraries have a native diverging bar — users must assemble it
manually from two horizontal bar charts.

    from glyphx import Figure
    from glyphx.diverging_bar import DivergingBarSeries

    categories = ["Feature A","Feature B","Feature C","Feature D","Feature E"]
    values     = [+42, -15, +63, -8, +29]

    fig = Figure(width=700, height=400, auto_display=False)
    fig.add(DivergingBarSeries(
        categories=categories,
        values=values,
        pos_color="#2563eb",     # positive → right
        neg_color="#dc2626",     # negative → left
        show_values=True,
    ))
    fig.show()
"""
from __future__ import annotations

import numpy as np

from .utils import svg_escape, _format_tick


class DivergingBarSeries:
    """
    Horizontal diverging bar chart.

    Args:
        categories:   Category labels (one per bar, rendered on Y axis).
        values:       Numeric values.  Positive → right; negative → left.
        pos_color:    Fill color for positive bars (default blue).
        neg_color:    Fill color for negative bars (default red).
        bar_height:   Fraction of available row height used by each bar (0–1).
        show_values:  Render the numeric value at the end of each bar.
        zero_line:    Draw a vertical reference line at zero.
        label:        Legend label.
    """

    def __init__(
        self,
        categories: list[str],
        values: list[float],
        pos_color:   str   = "#2563eb",
        neg_color:   str   = "#dc2626",
        bar_height:  float = 0.65,
        show_values: bool  = True,
        zero_line:   bool  = True,
        label: str | None  = None,
    ) -> None:
        if len(categories) != len(values):
            raise ValueError("categories and values must have the same length.")

        self.categories  = list(categories)
        self.values      = list(values)
        self.pos_color   = pos_color
        self.neg_color   = neg_color
        self.bar_height  = float(bar_height)
        self.show_values = show_values
        self.zero_line   = zero_line
        self.label       = label
        self.css_class   = f"series-{id(self) % 100000}"
        self.color       = pos_color   # for legend compatibility

        # x/y stubs (rendered as axis-free)
        self.x = None
        self.y = None

    def to_svg(self, ax: object = None) -> str:   # type: ignore[override]
        vals = np.asarray(self.values, dtype=float)

        if ax is None:
            pad_x, pad_y = 120, 50
            w, h = 640, 400
            font, tc, gc = "sans-serif", "#000", "#ddd"
        else:
            pad_x = getattr(ax, "padding", 50) * 2    # type: ignore
            # Use full padding on top so Figure title never overlaps chart area
            pad_y = getattr(ax, "padding", 50)         # type: ignore
            w     = ax.width   # type: ignore
            h     = ax.height  # type: ignore
            font  = ax.theme.get("font", "sans-serif")  # type: ignore
            tc    = ax.theme.get("text_color", "#000")  # type: ignore
            gc    = ax.theme.get("grid_color", "#ddd")  # type: ignore

        n        = len(self.categories)
        plot_w   = w - 2 * pad_x
        plot_h   = h - 2 * pad_y
        row_h    = plot_h / n
        bar_h    = row_h * self.bar_height

        abs_max  = max(abs(vals.max()), abs(vals.min())) or 1.0
        zero_x   = w / 2           # zero line is always centred
        scale    = (plot_w / 2) / abs_max

        elements: list[str] = []

        # Background grid lines (vertical)
        n_ticks = 4
        for k in range(-n_ticks, n_ticks + 1):
            gx  = zero_x + k * (plot_w / 2) / n_ticks
            val = k * abs_max / n_ticks
            elements.append(
                f'<line x1="{gx:.1f}" x2="{gx:.1f}" '
                f'y1="{pad_y}" y2="{pad_y + plot_h}" '
                f'stroke="{gc}" stroke-width="1" stroke-dasharray="3,3"/>'
            )
            if k != 0:
                elements.append(
                    f'<text x="{gx:.1f}" y="{pad_y - 4}" '
                    f'text-anchor="middle" font-size="9" '
                    f'font-family="{font}" fill="{tc}" opacity="0.6">'
                    f'{_format_tick(val)}</text>'
                )

        # Bars
        for i, (cat, val) in enumerate(zip(self.categories, vals)):
            cy      = pad_y + i * row_h + row_h / 2
            bar_y   = cy - bar_h / 2
            bar_w   = abs(val) * scale
            color   = self.pos_color if val >= 0 else self.neg_color
            bar_x   = zero_x if val >= 0 else zero_x - bar_w
            sign    = "+" if val > 0 else ""

            tooltip = (
                f'data-x="{svg_escape(cat)}" '
                f'data-value="{svg_escape(sign + _format_tick(val))}" '
                f'data-label="{svg_escape(self.label or cat)}"'
            )
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{bar_x:.1f}" y="{bar_y:.1f}" '
                f'width="{max(bar_w, 1):.1f}" height="{bar_h:.1f}" '
                f'fill="{color}" {tooltip}/>'
            )

            # Category label (left-aligned)
            elements.append(
                f'<text x="{pad_x - 6}" y="{cy + 4:.1f}" '
                f'text-anchor="end" font-size="11" '
                f'font-family="{font}" fill="{tc}">'
                f'{svg_escape(cat)}</text>'
            )

            # Value label at bar end
            if self.show_values:
                if val >= 0:
                    lx, anchor = bar_x + bar_w + 4, "start"
                else:
                    lx, anchor = bar_x - 4, "end"
                elements.append(
                    f'<text x="{lx:.1f}" y="{cy + 4:.1f}" '
                    f'text-anchor="{anchor}" font-size="10" '
                    f'font-family="{font}" fill="{color}" font-weight="600">'
                    f'{sign}{svg_escape(_format_tick(val))}</text>'
                )

        # Zero reference line
        if self.zero_line:
            elements.append(
                f'<line x1="{zero_x:.1f}" x2="{zero_x:.1f}" '
                f'y1="{pad_y}" y2="{pad_y + plot_h}" '
                f'stroke="{tc}" stroke-width="1.5"/>'
            )

        return "\n".join(elements)
