"""
GlyphX swarm plot: categorical scatter with points nudged apart.
"""

from __future__ import annotations

from collections import defaultdict

from .series import BaseSeries
from .utils import svg_escape


class SwarmPlotSeries(BaseSeries):
    """
    Categorical scatter that offsets overlapping points sideways.

    Args:
        data (list[list]): One list of observations per category.
        categories (list | None): Category labels, one per inner list.
        color (str): Point fill colour.
        size (int): Point radius in pixels.
        jitter (int): Horizontal spacing between collided points.
        label (str | None): Legend label.
    """

    def __init__(self, data, categories=None, color="#1f77b4", size=4,
                 jitter=6, label=None):
        self.data = [list(group) for group in data]
        self.categories = (
            list(categories) if categories
            else [str(i) for i in range(len(self.data))]
        )
        self.size = size
        self.jitter = jitter

        # Slot centres for the categories, and the observed value range, so
        # compute_domain() can build scales. Previously this class carried
        # no .x/.y at all and crashed on ax.scale_y.
        positions = [i + 0.5 for i in range(len(self.data))]
        flat = [float(v) for group in self.data for v in group]
        y_range = [min(flat), max(flat)] if flat else []

        super().__init__(x=positions, y=y_range, color=color, label=label)
        self._x_categories = list(self.categories)
        self._numeric_x = positions

    def to_svg(self, ax, use_y2=False) -> str:
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        scale_x = ax.scale_x
        elements = []

        for i, values in enumerate(self.data):
            centre = scale_x(i + 0.5)

            # Group points that land on the same pixel row, then fan them out
            # symmetrically about the category centre.
            rows = defaultdict(list)
            for value in values:
                rows[round(scale_y(value), 1)].append(value)

            for _row_py, collided in rows.items():
                count = len(collided)
                for j, value in enumerate(collided):
                    offset = (j - (count - 1) / 2) * self.jitter
                    cx = centre + offset
                    cy = scale_y(value)
                    elements.append(
                        f'<circle class="glyphx-point {self.css_class}" '
                        f'cx="{cx}" cy="{cy}" r="{self.size}" fill="{self.color}" '
                        f'data-x="{svg_escape(str(self.categories[i]))}" '
                        f'data-y="{svg_escape(str(value))}"/>'
                    )
        return "\n".join(elements)
