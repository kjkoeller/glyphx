"""
GlyphX KDESeries — standalone kernel density estimate curve.

Uses the pure-NumPy Gaussian KDE from violin_plot.py — no scipy required.

    from glyphx import Figure
    from glyphx.kde import KDESeries

    fig = Figure()
    fig.add(KDESeries(data, label="Control",  color="#3b82f6"))
    fig.add(KDESeries(data2, label="Treatment", color="#ef4444", filled=True))
    fig.show()
"""
from __future__ import annotations

import numpy as np

from .series   import BaseSeries
from .utils    import svg_escape
from .violin_plot import _numpy_kde


class KDESeries(BaseSeries):
    """
    Smooth kernel density estimate curve (no scipy required).

    Args:
        data:       1-D array of raw observations.
        n_points:   Number of evaluation points along the curve (default 200).
        filled:     If ``True``, shade the area under the curve.
        alpha:      Fill opacity when ``filled=True`` (default 0.20).
        color:      Line (and fill) color.
        width:      Line stroke width in pixels.
        label:      Legend label.
        bw_method:  Bandwidth: ``"silverman"`` (default) or a positive float
                    multiplier applied to the Silverman estimate.
    """

    def __init__(
        self,
        data,
        n_points: int        = 200,
        filled: bool         = False,
        alpha: float         = 0.20,
        color: str           = "#1f77b4",
        width: int           = 2,
        label: str | None    = None,
        bw_method: str | float = "silverman",
    ) -> None:
        arr = np.asarray(data, dtype=float)
        arr = arr[np.isfinite(arr)]

        h          = None if bw_method == "silverman" else float(bw_method)
        kde        = _numpy_kde(arr, bandwidth=h)
        x_range    = np.linspace(arr.min(), arr.max(), n_points)
        y_density  = kde(x_range)

        self.kde_x    = x_range.tolist()
        self.kde_y    = y_density.tolist()
        self.filled   = filled
        self.alpha    = float(alpha)
        self.width    = int(width)
        self.css_class = f"series-{id(self) % 100000}"

        super().__init__(
            x     = self.kde_x,
            y     = self.kde_y,
            color = color,
            label = label,
        )

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y  # type: ignore[union-attr]
        x_vals  = getattr(self, "_numeric_x", self.kde_x)

        pts = " ".join(
            f"{ax.scale_x(x):.2f},{scale_y(y):.2f}"  # type: ignore[union-attr]
            for x, y in zip(x_vals, self.kde_y)
        )

        elements = []

        if self.filled:
            # Close the polygon to x-axis (y=0)
            y0      = scale_y(0)  # type: ignore[union-attr]
            x_left  = ax.scale_x(x_vals[0])   # type: ignore[union-attr]
            x_right = ax.scale_x(x_vals[-1])  # type: ignore[union-attr]
            polygon_pts = f"{x_left},{y0} " + pts + f" {x_right},{y0}"
            elements.append(
                f'<polygon class="{self.css_class}" '
                f'points="{polygon_pts}" '
                f'fill="{self.color}" fill-opacity="{self.alpha}" stroke="none"/>'
            )

        elements.append(
            f'<polyline class="{self.css_class}" fill="none" '
            f'stroke="{self.color}" stroke-width="{self.width}" '
            f'points="{pts}"/>'
        )

        return "\n".join(elements)
