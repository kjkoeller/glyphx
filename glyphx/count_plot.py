"""
GlyphX count plot: a bar chart of category frequencies.
"""

from __future__ import annotations

from collections import Counter

from .series import BaseSeries
from .utils import svg_escape


class CountPlotSeries(BaseSeries):
    """
    Bar chart of how often each category appears.

    Counts the values itself, so it takes the raw column rather than
    pre-aggregated totals.
    """
    #: Bars are drawn from y=0, so the domain must include zero.
    zero_anchored = True

    """
    Bar chart of how often each category occurs.

    Args:
        data (list): Raw observations; one entry per occurrence.
        order (list | None): Explicit category order. Defaults to sorted unique.
        color (str): Bar fill colour.
        bar_width (float): Fraction of the category slot the bar occupies.
        label (str | None): Legend label.
    """

    def __init__(self, data, order=None, color="#1f77b4", bar_width=0.8, label=None):
        """Tally the values, honouring an explicit category order if one is given."""
        self.data = list(data)
        self.order = list(order) if order else sorted(set(self.data))
        self.bar_width = bar_width
        self._counts = Counter(self.data)

        # compute_domain() needs .x/.y to build scales. Without them Figure
        # sends this down the axis-free branch, finalize() never runs, and
        # to_svg() blows up on a missing ax.scale_y.
        counts = [float(self._counts[cat]) for cat in self.order]
        super().__init__(
            x=list(self.order),
            y=counts,
            color=color,
            label=label,
        )

    def to_svg(self, ax, use_y2=False) -> str:
        """Draw one bar per category, sized by its count."""
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        scale_x = ax.scale_x

        # compute_domain() maps categories onto _numeric_x slot centres.
        positions = getattr(self, "_numeric_x", None) or [
            i + 0.5 for i in range(len(self.order))
        ]

        n = max(len(self.order), 1)
        slot_px = (ax.width - 2 * ax.padding) / n
        width_px = slot_px * self.bar_width

        y0 = scale_y(0)
        elements = []
        for cat, pos in zip(self.order, positions):
            count = self._counts[cat]
            x_px = scale_x(pos)
            y_px = scale_y(count)
            top = min(y0, y_px)
            height = abs(y0 - y_px)
            elements.append(
                f'<rect class="{self.css_class}" x="{x_px - width_px / 2}" y="{top}" '
                f'width="{width_px}" height="{height}" fill="{self.color}" '
                f'data-label="{svg_escape(str(cat))}" data-y="{count}"/>'
            )
        return "\n".join(elements)
