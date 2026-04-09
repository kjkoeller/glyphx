"""
GlyphX GroupedBarSeries — side-by-side bars for one value per group per category.
"""
from __future__ import annotations
import numpy as np
from .series import BaseSeries
from .utils import svg_escape, _format_tick


class GroupedBarSeries(BaseSeries):
    """
    Grouped bar chart: for each category on the X-axis, draws one bar per
    group side-by-side, each with a distinct color.

    Args:
        groups:       Category labels shown on the X-axis (outer grouping).
        categories:   Series / group names (inner grouping — one bar per name).
        values:       2-D list ``values[group_i][cat_j]``.
        group_colors: Color per category (inner group).  Auto-assigned if None.
        bar_width:    Fraction of the available slot used by all bars together (0–1).
        label:        Legend label (unused; individual category labels shown instead).
    """

    def __init__(
        self,
        groups: list,
        categories: list,
        values: list[list[float]],
        group_colors: list[str] | None = None,
        bar_width: float = 0.8,
        label: str | None = None,
    ) -> None:
        from .themes import themes as _themes
        default_colors = _themes["default"]["colors"]

        self.groups       = list(groups)
        self.categories   = list(categories)
        self.values       = values          # [n_groups][n_cats]
        self.group_colors = (group_colors or default_colors)[:len(categories)]
        self.bar_width    = float(bar_width)

        all_y = [v for row in values for v in row]
        y_min = min(0, min(all_y))
        y_max = max(all_y)

        # Use 1-indexed numeric x for the groups
        n = len(groups)
        super().__init__(
            x=list(range(1, n + 1)),
            y=[y_min, y_max],
            color=self.group_colors[0],
            label=label,
        )
        # Let render_grid use category names instead of raw numbers
        self._x_categories = list(groups)
        self._numeric_x    = list(range(1, n + 1))
        self.css_class     = f"series-{id(self) % 100000}"

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y   = ax.scale_y2 if use_y2 else ax.scale_y   # type: ignore
        n_groups  = len(self.groups)
        n_cats    = len(self.categories)
        if n_groups == 0 or n_cats == 0:
            return ""

        # Pixel width for the whole group slot (distance between group centres)
        if n_groups > 1:
            px_slot = ax.scale_x(2) - ax.scale_x(1)   # type: ignore
        else:
            px_slot = (ax.width - 2 * ax.padding) * 0.8  # type: ignore

        px_total = px_slot * self.bar_width
        px_bar   = px_total / n_cats
        y0       = scale_y(0)

        elements: list[str] = []

        for gi, gname in enumerate(self.groups):
            cx_group = ax.scale_x(gi + 1)   # type: ignore  group centre pixel

            for ci, (cat, color) in enumerate(zip(self.categories, self.group_colors)):
                val    = self.values[gi][ci]
                cy     = scale_y(val)
                h      = abs(cy - y0)
                top    = min(cy, y0)

                # Bar centre x within the group slot
                offset = (ci - (n_cats - 1) / 2) * px_bar
                bar_cx = cx_group + offset

                tooltip = (
                    f'data-x="{svg_escape(str(gname))}" '
                    f'data-label="{svg_escape(str(cat))}" '
                    f'data-value="{svg_escape(_format_tick(val))}"'
                )
                elements.append(
                    f'<rect class="glyphx-point {self.css_class}" '
                    f'x="{bar_cx - px_bar / 2:.1f}" y="{top:.1f}" '
                    f'width="{px_bar * 0.92:.1f}" height="{max(h, 1):.1f}" '
                    f'fill="{color}" stroke="#00000022" {tooltip}/>'
                )

        # Category color legend (right-side inline)
        font = ax.theme.get("font", "sans-serif")   # type: ignore
        tc   = ax.theme.get("text_color", "#000")   # type: ignore
        lx   = ax.width - ax.padding - 120           # type: ignore
        for ci, (cat, color) in enumerate(zip(self.categories, self.group_colors)):
            ly = ax.padding + ci * 18                # type: ignore
            elements.append(
                f'<rect x="{lx}" y="{ly}" width="12" height="12" fill="{color}"/>'
            )
            elements.append(
                f'<text x="{lx + 16}" y="{ly + 10}" font-size="11" '
                f'font-family="{font}" fill="{tc}">{svg_escape(str(cat))}</text>'
            )

        return "\n".join(elements)
