"""
GlyphX Raincloud Plot.

The raincloud combines three views of a distribution in one:
  • Raw jittered data points (the "rain")
  • A half-violin (KDE density curve)
  • A box-and-whisker summary

It is the modern replacement for the plain box plot — you see
every data point AND the full density shape AND quantile summary.

    from glyphx import Figure
    from glyphx.raincloud import RaincloudSeries

    fig = Figure(width=700, height=500, auto_display=False)
    fig.add(RaincloudSeries(
        data=[group_a, group_b, group_c],
        categories=["Control", "Drug A", "Drug B"],
    ))
    fig.show()
"""
from __future__ import annotations

import numpy as np

from .violin_plot import _numpy_kde
from .colormaps import colormap_colors
from .utils import svg_escape


class RaincloudSeries:
    """
    Raincloud plot: jitter + half-violin + box for each category.

    Args:
        data:           List of 1-D arrays, one per category.
        categories:     Category labels (same length as data).
        colors:         Per-category colors; cycles if fewer than categories.
        jitter_width:   Max horizontal pixel displacement of raw points.
        point_radius:   Radius of each jittered data point.
        violin_width:   Max pixel width of the half-violin.
        box_width:      Pixel width of the IQR box.
        seed:           Random seed for reproducible jitter.
        label:          Legend label for the series.
    """

    def __init__(
        self,
        data: list,
        categories: list[str] | None = None,
        colors: list[str] | None = None,
        jitter_width: float = 18.0,
        point_radius: float = 3.0,
        violin_width: float = 40.0,
        box_width: float = 10.0,
        seed: int = 42,
        label: str | None = None,
    ) -> None:
        self.datasets     = [np.asarray(d, dtype=float) for d in data]
        self.categories   = categories or [str(i) for i in range(len(data))]
        self.jitter_width = jitter_width
        self.point_radius = point_radius
        self.violin_width = violin_width
        self.box_width    = box_width
        self.seed         = seed
        self.label        = label
        self.css_class    = f"series-{id(self) % 100000}"

        n_cats = len(self.datasets)
        self.colors = (colors or colormap_colors("viridis", n_cats))[:n_cats]
        if len(self.colors) < n_cats:
            self.colors = (self.colors * ((n_cats // len(self.colors)) + 1))[:n_cats]

        # Expose x/y for domain computation — 0.5-indexed to align with grid label mapping
        self.x = [i + 0.5 for i in range(n_cats)]
        all_vals = np.concatenate(self.datasets)
        self.y   = [float(all_vals.min()), float(all_vals.max())]

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y  # type: ignore[union-attr]
        rng      = np.random.default_rng(self.seed)
        elements: list[str] = []

        for i, (arr, cat, color) in enumerate(
            zip(self.datasets, self.categories, self.colors)
        ):
            if len(arr) < 2:
                continue

            cx = ax.scale_x(i + 0.5)  # 0-indexed, matches domain x positions  # type: ignore[union-attr]

            # ── 1. Jittered raw points (left side) ───────────────────────
            jitter = rng.uniform(-self.jitter_width, 0, size=len(arr))
            for val, jit in zip(arr, jitter):
                py = scale_y(float(val))
                px = cx + jit - self.jitter_width * 0.5
                elements.append(
                    f'<circle class="glyphx-point {self.css_class}" '
                    f'cx="{px:.1f}" cy="{py:.1f}" r="{self.point_radius}" '
                    f'fill="{color}" fill-opacity="0.55" '
                    f'data-x="{svg_escape(cat)}" '
                    f'data-y="{val:.3g}" '
                    f'data-label="{svg_escape(self.label or cat)}"/>'
                )

            # ── 2. Half-violin (right side) ───────────────────────────────
            kde    = _numpy_kde(arr)
            y_vals = np.linspace(arr.min(), arr.max(), 100)
            dens   = kde(y_vals)
            max_d  = dens.max() or 1
            dens   = dens / max_d * self.violin_width

            right_pts = [(cx + d, scale_y(float(y))) for y, d in zip(y_vals, dens)]
            left_pts  = [(cx,     scale_y(float(y))) for y    in reversed(y_vals)]

            all_pts = right_pts + left_pts
            path    = "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in all_pts) + " Z"
            elements.append(
                f'<path d="{path}" fill="{color}" fill-opacity="0.35" '
                f'stroke="{color}" stroke-width="1.5"/>'
            )

            # ── 3. Box plot (centre) ──────────────────────────────────────
            q1          = float(np.percentile(arr, 25))
            q2          = float(np.median(arr))
            q3          = float(np.percentile(arr, 75))
            iqr         = q3 - q1
            w_lo        = float(max(arr.min(), q1 - 1.5 * iqr))
            w_hi        = float(min(arr.max(), q3 + 1.5 * iqr))
            hw          = self.box_width / 2

            box_top = min(scale_y(q1), scale_y(q3))
            box_h   = abs(scale_y(q3) - scale_y(q1))

            # Whiskers
            elements.append(
                f'<line x1="{cx}" x2="{cx}" '
                f'y1="{scale_y(w_lo)}" y2="{scale_y(q1)}" '
                f'stroke="{color}" stroke-width="1.5"/>'
            )
            elements.append(
                f'<line x1="{cx}" x2="{cx}" '
                f'y1="{scale_y(q3)}" y2="{scale_y(w_hi)}" '
                f'stroke="{color}" stroke-width="1.5"/>'
            )
            # IQR box
            elements.append(
                f'<rect x="{cx - hw}" y="{box_top}" '
                f'width="{self.box_width}" height="{box_h}" '
                f'fill="{color}" fill-opacity="0.6" '
                f'stroke="{color}" stroke-width="1.5"/>'
            )
            # Median line
            elements.append(
                f'<line x1="{cx - hw}" x2="{cx + hw}" '
                f'y1="{scale_y(q2)}" y2="{scale_y(q2)}" '
                f'stroke="#fff" stroke-width="2.5"/>'
            )
            # Category label — skip if _x_categories is set, grid handles it
            if not getattr(self, "_x_categories", None):
                elements.append(
                    f'<text x="{cx}" y="{ax.height - ax.padding + 16}" '  # type: ignore[union-attr]
                    f'text-anchor="middle" font-size="11" fill="#444">'
                    f'{svg_escape(cat)}</text>'
                )

        return "\n".join(elements)
