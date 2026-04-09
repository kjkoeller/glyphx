"""
GlyphX Waterfall / Bridge chart.

Shows cumulative effect of sequentially introduced positive or negative values.
Essential for financial P&L analysis, budget variance, and change attribution.

    from glyphx import Figure
    from glyphx.waterfall import WaterfallSeries

    fig = Figure(title="Q3 Revenue Bridge", auto_display=False)
    fig.add(WaterfallSeries(
        labels=["Start", "Product A", "Product B", "Returns", "Total"],
        values=[1_000, +350, +210, -80, None],   # None = auto-total bar
    ))
    fig.show()
"""
from __future__ import annotations

from .series import BaseSeries
from .utils import svg_escape, _format_tick


class WaterfallSeries(BaseSeries):
    """
    Waterfall (bridge) chart.

    Args:
        labels:         Category labels.
        values:         Deltas to add at each step.  Pass ``None`` for the
                        last bar to auto-compute the running total.
        up_color:       Fill for positive bars.
        down_color:     Fill for negative bars.
        total_color:    Fill for the auto-total bar.
        bar_width:      Fraction of slot width used by each bar (0–1).
        connector:      Draw dashed connector lines between bars.
        show_values:    Print the delta value above each bar.
        label:          Legend label.
    """

    def __init__(
        self,
        labels: list[str],
        values: list[float | None],
        up_color:    str   = "#2ca02c",
        down_color:  str   = "#d62728",
        total_color: str   = "#1f77b4",
        bar_width:   float = 0.6,
        connector:   bool  = True,
        show_values: bool  = True,
        label: str | None  = None,
    ) -> None:
        self.labels      = labels
        self.raw_values  = values
        self.up_color    = up_color
        self.down_color  = down_color
        self.total_color = total_color
        self.bar_width   = bar_width
        self.connector   = connector
        self.show_values = show_values

        # Compute running totals and bar extents
        self._bases:  list[float] = []
        self._tops:   list[float] = []
        self._colors: list[str]   = []
        self._deltas: list[float] = []

        running = 0.0
        for v in values:
            if v is None:
                # Total bar — spans from 0 to current running total
                self._bases.append(0.0)
                self._tops.append(running)
                self._colors.append(total_color)
                self._deltas.append(running)
            else:
                base = running
                top  = running + v
                self._bases.append(min(base, top))
                self._tops.append(max(base, top))
                self._colors.append(up_color if v >= 0 else down_color)
                self._deltas.append(v)
                running += v

        # x/y for domain
        n    = len(labels)
        ymin = min(min(self._bases), 0)
        ymax = max(self._tops)

        super().__init__(
            x=list(range(n)),
            y=[ymin, ymax],
            color=up_color,
            label=label,
        )
        # Register as categorical so render_grid() draws x-axis labels
        self._x_categories = list(labels)
        self._numeric_x    = [i + 0.5 for i in range(n)]

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y   # type: ignore[union-attr]
        elements: list[str] = []

        n       = len(self.labels)
        slot_px = (ax.width - 2 * ax.padding) / n           # type: ignore[union-attr]
        body_px = slot_px * self.bar_width

        prev_top_py: float | None = None

        for i, (lbl, base, top, color, delta) in enumerate(zip(
            self.labels, self._bases, self._tops,
            self._colors, self._deltas,
        )):
            cx      = ax.scale_x(i + 0.5)   # type: ignore[union-attr]
            py_base = scale_y(base)
            py_top  = scale_y(top)
            bar_h   = abs(py_base - py_top)
            bar_y   = min(py_base, py_top)

            tooltip = (
                f'data-x="{svg_escape(lbl)}" '
                f'data-value="{svg_escape(_format_tick(delta))}" '
                f'data-label="{svg_escape(self.label or lbl)}"'
            )
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{cx - body_px / 2}" y="{bar_y}" '
                f'width="{body_px}" height="{max(bar_h, 1)}" '
                f'fill="{color}" {tooltip}/>'
            )

            # Connector dashed line from previous bar's top to this bar's base
            if self.connector and prev_top_py is not None:
                prev_cx = ax.scale_x(i - 1 + 0.5)   # type: ignore[union-attr]
                elements.append(
                    f'<line '
                    f'x1="{prev_cx + body_px / 2}" '
                    f'x2="{cx - body_px / 2}" '
                    f'y1="{prev_top_py}" y2="{prev_top_py}" '
                    f'stroke="#999" stroke-width="1" stroke-dasharray="3,3"/>'
                )

            prev_top_py = py_top

            # Delta label above bar
            if self.show_values:
                label_y = bar_y - 4
                sign    = "+" if delta > 0 else ""
                elements.append(
                    f'<text x="{cx}" y="{label_y}" text-anchor="middle" '
                    f'font-size="10" fill="{color}" font-weight="600">'
                    f'{sign}{svg_escape(_format_tick(delta))}</text>'
                )

        return "\n".join(elements)
