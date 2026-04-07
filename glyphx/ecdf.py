"""
GlyphX Empirical Cumulative Distribution Function (ECDF) plot.

The ECDF is the step-function version of a CDF — for each value x,
it shows the proportion of observations ≤ x.  Unlike histograms it
requires no bin-width choice and reveals the full distribution.

    from glyphx import Figure
    from glyphx.ecdf import ECDFSeries

    fig = Figure(auto_display=False)
    fig.add(ECDFSeries(control_data, label="Control", color="#1f77b4"))
    fig.add(ECDFSeries(treatment_data, label="Treatment", color="#ff7f0e"))
    fig.axes.xlabel = "Measurement"
    fig.axes.ylabel = "Cumulative proportion"
    fig.show()
"""
from __future__ import annotations

import numpy as np

from .series import BaseSeries
from .utils import svg_escape


class ECDFSeries(BaseSeries):
    """
    Empirical CDF rendered as a step function.

    Args:
        data:          Raw observations (1-D array-like).
        color:         Line color.
        label:         Legend label.
        show_points:   Draw a circle at each step.
        point_radius:  Radius of step-point circles.
        line_width:    Stroke width of the step line.
        complementary: If True, plot 1 − ECDF (survival function).
    """

    def __init__(
        self,
        data: list | np.ndarray,
        color: str | None = None,
        label: str | None = None,
        show_points: bool = False,
        point_radius: float = 3.0,
        line_width: float = 2.0,
        complementary: bool = False,
    ) -> None:
        arr = np.sort(np.asarray(data, dtype=float))
        n   = len(arr)
        ys  = np.arange(1, n + 1) / n

        if complementary:
            ys = 1 - ys

        super().__init__(
            x=arr.tolist(),
            y=ys.tolist(),
            color=color or "#1f77b4",
            label=label,
        )
        self.show_points  = show_points
        self.point_radius = point_radius
        self.line_width   = line_width
        self._raw         = arr

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        """Render the ECDF step function as SVG."""
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y  # type: ignore[union-attr]
        elements: list[str] = []

        # Build step-function path
        # For each (x_i, y_i), draw:
        #   horizontal segment from previous x to x_i at previous y
        #   vertical jump from previous y to y_i at x_i
        path_d: list[str] = []
        prev_px: float | None = None
        prev_py: float | None = None

        for x_val, y_val in zip(self.x, self.y):
            px = ax.scale_x(x_val)   # type: ignore[union-attr]
            py = scale_y(y_val)

            if prev_px is None:
                # Horizontal lead-in from left edge to first point
                path_d.append(f"M {ax.padding},{py}")  # type: ignore[union-attr]
                path_d.append(f"L {px},{py}")
            else:
                # Horizontal at previous y
                path_d.append(f"L {px},{prev_py}")
                # Vertical jump
                path_d.append(f"L {px},{py}")

            if self.show_points:
                elements.append(
                    f'<circle class="glyphx-point {self.css_class}" '
                    f'cx="{px}" cy="{py}" r="{self.point_radius}" '
                    f'fill="{self.color}" '
                    f'data-x="{svg_escape(str(x_val))}" '
                    f'data-y="{svg_escape(f"{y_val:.4f}")}" '
                    f'data-label="{svg_escape(self.label or "")}"/>'
                )
            prev_px, prev_py = px, py

        # Horizontal tail to right edge
        if prev_px is not None:
            path_d.append(
                f"L {ax.width - ax.padding},{prev_py}"  # type: ignore[union-attr]
            )

        if path_d:
            elements.insert(
                0,
                f'<path d="{" ".join(path_d)}" fill="none" '
                f'stroke="{self.color}" stroke-width="{self.line_width}" '
                f'class="{self.css_class}"/>',
            )

        return "\n".join(elements)
