"""
GlyphX FillBetweenSeries — shaded area between two lines or between
a line and a baseline (zero or a constant).

    from glyphx import Figure
    from glyphx.fill_between import FillBetweenSeries

    fig = Figure()
    fig.add(FillBetweenSeries(x, y_lower, y_upper,
                              color="#2563eb", label="95% CI"))
    fig.show()
"""
from __future__ import annotations

import numpy as np

from .series import BaseSeries, LineSeries
from .utils  import svg_escape


class FillBetweenSeries(BaseSeries):
    """
    Shaded area between two Y arrays (or between a line and a baseline).

    Args:
        x:          X values (shared by both bounds).
        y1:         Lower bound Y values, **or** the line when ``y2`` is a scalar.
        y2:         Upper bound Y values.  Pass a scalar (e.g. ``0``) to shade
                    between ``y1`` and a horizontal baseline.
        color:      Fill and line color (default: ``"#1f77b4"``).
        alpha:      Fill opacity 0–1 (default: ``0.25``).
        line_width: Width of the boundary lines in pixels.  ``0`` hides them.
        label:      Legend label.
        line_color: Color for boundary lines.  Defaults to ``color``.
    """

    def __init__(
        self,
        x,
        y1,
        y2,
        color: str          = "#1f77b4",
        alpha: float        = 0.25,
        line_width: int     = 1,
        label: str | None   = None,
        line_color: str | None = None,
    ) -> None:
        self.x1       = list(x)
        self.y1       = list(y1)
        # y2 can be a scalar baseline (e.g. 0) or a full array
        if np.isscalar(y2):
            self.y2 = [float(y2)] * len(self.y1)
        else:
            self.y2 = list(y2)

        self.alpha      = float(alpha)
        self.line_width = int(line_width)
        self.line_color = line_color or color
        self.css_class  = f"series-{id(self) % 100000}"

        # Domain: x spans full range; y spans both bounds
        all_y = self.y1 + self.y2
        super().__init__(
            x     = self.x1,
            y     = all_y,
            color = color,
            label = label,
        )

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y  # type: ignore[union-attr]
        x_vals  = getattr(self, "_numeric_x", self.x1)

        # Build a closed polygon: trace y2 forward, then y1 backward
        upper_pts = [f"{ax.scale_x(x)},{scale_y(y)}" for x, y in zip(x_vals, self.y2)]  # type: ignore[union-attr]
        lower_pts = [f"{ax.scale_x(x)},{scale_y(y)}" for x, y in reversed(list(zip(x_vals, self.y1)))]  # type: ignore[union-attr]
        polygon_points = " ".join(upper_pts + lower_pts)

        # Convert alpha to hex opacity suffix
        alpha_hex = format(round(self.alpha * 255), "02x")
        fill_color = self.color + alpha_hex  # e.g. "#2563eb40"

        elements = [
            f'<polygon class="{self.css_class}" '
            f'points="{polygon_points}" '
            f'fill="{fill_color}" stroke="none"/>'
        ]

        # Optional boundary lines
        if self.line_width > 0:
            for y_vals, label_sfx in [(self.y2, "-upper"), (self.y1, "-lower")]:
                pts = " ".join(
                    f"{ax.scale_x(x)},{scale_y(y)}"  # type: ignore[union-attr]
                    for x, y in zip(x_vals, y_vals)
                )
                elements.append(
                    f'<polyline class="{self.css_class}" fill="none" '
                    f'stroke="{self.line_color}" '
                    f'stroke-width="{self.line_width}" '
                    f'points="{pts}"/>'
                )

        return "\n".join(elements)
