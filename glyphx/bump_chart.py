"""
GlyphX BumpChartSeries — rank-over-time visualization.

Bump charts show how items change rank over time using smooth cubic
Bézier curves between rank positions.  Seaborn cannot produce them.
Plotly has no native bump chart.  Matplotlib requires manual assembly.

    from glyphx import Figure
    from glyphx.bump_chart import BumpChartSeries

    fig = Figure(width=800, height=500, auto_display=False)
    fig.add(BumpChartSeries(
        x=["2019","2020","2021","2022","2023"],
        rankings={
            "GlyphX":    [5, 4, 3, 1, 1],
            "Matplotlib": [1, 1, 1, 2, 2],
            "Plotly":    [3, 2, 2, 3, 3],
            "Seaborn":   [2, 3, 4, 4, 4],
            "Bokeh":     [4, 5, 5, 5, 5],
        },
    ))
    fig.show()
"""
from __future__ import annotations

import math
from .utils  import svg_escape
from .themes import themes as _themes
from .colormaps import colormap_colors


class BumpChartSeries:
    """
    Rank-over-time chart drawn with smooth Bézier curves.

    Lower rank number = higher position (rank 1 is at the top).

    Args:
        x:          Time-axis labels (columns).
        rankings:   ``{series_name: [rank_at_each_x]}`` mapping.
        colors:     Per-series colors.  Auto-assigned if None.
        line_width: Stroke width of each ribbon.
        dot_radius: Radius of the rank-position dots.
        show_labels: Draw series name at leftmost and rightmost position.
        label:      Legend label (unused; individual series labeled directly).
    """

    def __init__(
        self,
        x: list,
        rankings: dict[str, list[int]],
        colors: list[str] | None = None,
        line_width: float        = 3.0,
        dot_radius: float        = 6.0,
        show_labels: bool        = True,
        label: str | None        = None,
    ) -> None:
        self.x_labels    = list(x)
        self.rankings    = rankings
        self.line_width  = float(line_width)
        self.dot_radius  = float(dot_radius)
        self.show_labels = show_labels
        self.label       = label
        self.css_class   = f"series-{id(self) % 100000}"

        n_series = len(rankings)
        self.colors = colors or colormap_colors("viridis", max(n_series, 2))

        # Max rank across all series and all time points
        all_ranks = [r for ranks in rankings.values() for r in ranks]
        self._max_rank = max(all_ranks) if all_ranks else 5

        # BaseSeries stubs (axis-free)
        self.x = None
        self.y = None

    def to_svg(self, ax: object = None) -> str:   # type: ignore
        if ax is None:
            pad_x, pad_y = 80, 40
            w, h = 780, 480
            font, tc = "sans-serif", "#000"
        else:
            pad_x = getattr(ax, "padding", 50) + 30   # type: ignore
            pad_y = getattr(ax, "padding", 50)         # type: ignore
            w     = ax.width    # type: ignore
            h     = ax.height   # type: ignore
            font  = ax.theme.get("font", "sans-serif")  # type: ignore
            tc    = ax.theme.get("text_color", "#000")  # type: ignore

        n_periods = len(self.x_labels)
        n_ranks   = self._max_rank

        plot_w = w - 2 * pad_x
        plot_h = h - 2 * pad_y

        # Map period index → pixel x
        def px(period_i: int) -> float:
            if n_periods <= 1:
                return pad_x + plot_w / 2
            return pad_x + period_i * plot_w / (n_periods - 1)

        # Map rank → pixel y  (rank 1 = top)
        def py(rank: int) -> float:
            if n_ranks <= 1:
                return pad_y + plot_h / 2
            return pad_y + (rank - 1) * plot_h / (n_ranks - 1)

        elements: list[str] = []

        # Period label columns at top
        for i, period in enumerate(self.x_labels):
            elements.append(
                f'<text x="{px(i):.1f}" y="{pad_y - 10}" '
                f'text-anchor="middle" font-size="12" font-weight="600" '
                f'font-family="{font}" fill="{tc}">'
                f'{svg_escape(str(period))}</text>'
            )

        # Rank labels on left (1 = top)
        for rank in range(1, n_ranks + 1):
            elements.append(
                f'<text x="{pad_x - 10}" y="{py(rank) + 4:.1f}" '
                f'text-anchor="end" font-size="10" '
                f'font-family="{font}" fill="{tc}" opacity="0.5">#{rank}</text>'
            )

        # Horizontal reference lines for each rank
        for rank in range(1, n_ranks + 1):
            ry = py(rank)
            elements.append(
                f'<line x1="{pad_x}" x2="{pad_x + plot_w}" '
                f'y1="{ry:.1f}" y2="{ry:.1f}" '
                f'stroke="#ddd" stroke-width="1" stroke-dasharray="3,3"/>'
            )

        # Draw each series
        for series_i, (name, ranks) in enumerate(self.rankings.items()):
            color = self.colors[series_i % len(self.colors)]

            # Build smooth cubic Bézier path through rank positions
            pts = [(px(i), py(r)) for i, r in enumerate(ranks)]
            if len(pts) < 2:
                continue

            path_parts = [f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"]
            for j in range(len(pts) - 1):
                x0, y0 = pts[j]
                x1, y1 = pts[j + 1]
                # Horizontal control points for smooth S-curve
                cx_mid = (x0 + x1) / 2
                path_parts.append(
                    f"C {cx_mid:.2f},{y0:.2f} {cx_mid:.2f},{y1:.2f} {x1:.2f},{y1:.2f}"
                )

            path_d = " ".join(path_parts)
            elements.append(
                f'<path d="{path_d}" fill="none" stroke="{color}" '
                f'stroke-width="{self.line_width}" '
                f'class="glyphx-point {self.css_class}" '
                f'data-label="{svg_escape(name)}"/>'
            )

            # Dots at each position
            for i, (dot_x, dot_y) in enumerate(pts):
                rank_val = ranks[i]
                elements.append(
                    f'<circle cx="{dot_x:.2f}" cy="{dot_y:.2f}" '
                    f'r="{self.dot_radius}" fill="{color}" '
                    f'stroke="#fff" stroke-width="1.5" '
                    f'data-label="{svg_escape(name)}" data-rank="{rank_val}" '
                    f'data-period="{svg_escape(str(self.x_labels[i]))}"/>'
                )

            # Labels at start and end
            if self.show_labels:
                # Left label
                x_left = pts[0][0] - self.dot_radius - 4
                elements.append(
                    f'<text x="{x_left:.1f}" y="{pts[0][1] + 4:.1f}" '
                    f'text-anchor="end" font-size="11" '
                    f'font-family="{font}" fill="{color}" font-weight="600">'
                    f'{svg_escape(name)}</text>'
                )
                # Right label
                x_right = pts[-1][0] + self.dot_radius + 4
                elements.append(
                    f'<text x="{x_right:.1f}" y="{pts[-1][1] + 4:.1f}" '
                    f'text-anchor="start" font-size="11" '
                    f'font-family="{font}" fill="{color}" font-weight="600">'
                    f'{svg_escape(name)}</text>'
                )

        return "\n".join(elements)
