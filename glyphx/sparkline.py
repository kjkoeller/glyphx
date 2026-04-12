"""
GlyphX SparklineSeries — tiny inline charts for dashboards and tables.

A sparkline is a miniature line or bar chart, typically 60-120px wide and
20-40px tall, suitable for embedding beside KPI numbers in tables, cards,
and status dashboards.  Matplotlib has no sparkline primitive.
Plotly's require full Figure scaffolding.

    from glyphx.sparkline import sparkline_svg

    # Returns a raw SVG string — embed anywhere
    svg = sparkline_svg([1, 3, 2, 5, 4, 6], width=80, height=28, color="#2563eb")

    # Or as a Figure series for a standalone chart
    from glyphx import Figure
    from glyphx.sparkline import SparklineSeries
    fig = Figure(width=120, height=40, auto_display=False)
    fig.add(SparklineSeries([1,3,2,5,4,6], color="#2563eb"))
    fig.show()
"""
from __future__ import annotations

import math
from .series import BaseSeries
from .utils  import svg_escape


# ---------------------------------------------------------------------------
# Standalone helper — returns a raw SVG string with no Figure overhead
# ---------------------------------------------------------------------------

def sparkline_svg(
    data: list[float],
    width: int          = 80,
    height: int         = 28,
    color: str          = "#2563eb",
    kind: str           = "line",
    line_width: float   = 1.5,
    fill: bool          = True,
    fill_alpha: float   = 0.18,
    show_last_dot: bool = True,
    padding: int        = 2,
) -> str:
    """
    Render a compact sparkline and return raw SVG markup.

    Args:
        data:          Numeric values to plot.
        width:         Pixel width of the sparkline.
        height:        Pixel height.
        color:         Line / bar fill color.
        kind:          ``"line"`` or ``"bar"``.
        line_width:    Stroke width for line sparklines.
        fill:          Shade area under the line.
        fill_alpha:    Fill opacity (0–1).
        show_last_dot: Mark the last data point with a circle.
        padding:       Pixel margin around the chart area.

    Returns:
        Complete ``<svg>`` element as a string.
    """
    if not data or len(data) < 2:
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"></svg>'

    n     = len(data)
    lo    = min(data)
    hi    = max(data)
    span  = hi - lo or 1.0
    pw    = width  - 2 * padding
    ph    = height - 2 * padding

    def sx(i: int) -> float:
        return padding + i * pw / (n - 1)

    def sy(v: float) -> float:
        return padding + ph - (v - lo) / span * ph

    parts: list[str] = [
        f'<svg width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}">'
    ]

    if kind == "bar":
        bw = max(1, pw / n * 0.8)
        y0 = sy(max(lo, 0))
        for i, v in enumerate(data):
            bx  = sx(i)
            by  = sy(v)
            bh  = abs(by - y0)
            top = min(by, y0)
            parts.append(
                f'<rect x="{bx - bw/2:.1f}" y="{top:.1f}" '
                f'width="{bw:.1f}" height="{max(bh, 1):.1f}" '
                f'fill="{color}" fill-opacity="0.8"/>'
            )
    else:
        pts = " ".join(f"{sx(i):.2f},{sy(v):.2f}" for i, v in enumerate(data))

        if fill:
            poly_pts = (
                f"{sx(0):.2f},{sy(lo):.2f} "
                + pts
                + f" {sx(n-1):.2f},{sy(lo):.2f}"
            )
            parts.append(
                f'<polygon points="{poly_pts}" '
                f'fill="{color}" fill-opacity="{fill_alpha}" stroke="none"/>'
            )

        parts.append(
            f'<polyline points="{pts}" fill="none" '
            f'stroke="{color}" stroke-width="{line_width}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )

        if show_last_dot:
            lx, ly = sx(n - 1), sy(data[-1])
            parts.append(
                f'<circle cx="{lx:.2f}" cy="{ly:.2f}" r="{line_width + 1}" '
                f'fill="{color}"/>'
            )

    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Series wrapper for use inside a Figure
# ---------------------------------------------------------------------------

class SparklineSeries(BaseSeries):
    """
    Lightweight sparkline series.  Designed for very small canvases
    (width ≤ 200, height ≤ 60).  Omits axis lines, grid, and labels.

    Args:
        data:          Numeric values.
        color:         Line color.
        kind:          ``"line"`` or ``"bar"``.
        fill:          Shade area under the line.
        fill_alpha:    Fill opacity.
        line_width:    Stroke width.
        show_last_dot: Highlight the final data point.
        label:         Legend label.
    """

    def __init__(
        self,
        data: list[float],
        color: str          = "#2563eb",
        kind: str           = "line",
        fill: bool          = True,
        fill_alpha: float   = 0.18,
        line_width: float   = 1.5,
        show_last_dot: bool = True,
        label: str | None   = None,
    ) -> None:
        self.data          = list(data)
        self.kind          = kind
        self.fill          = fill
        self.fill_alpha    = fill_alpha
        self.line_width    = float(line_width)
        self.show_last_dot = show_last_dot
        self.css_class     = f"series-{id(self) % 100000}"

        n = len(data)
        super().__init__(
            x=list(range(n)),
            y=list(data),
            color=color,
            label=label,
        )

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y   # type: ignore
        x_vals  = getattr(self, "_numeric_x", self.x)
        n       = len(x_vals)
        if n < 2:
            return ""

        lo, hi = min(self.data), max(self.data)

        if self.kind == "bar":
            y0       = scale_y(max(lo, 0))
            pw       = (ax.width - 2 * ax.padding) / n    # type: ignore
            bw       = pw * 0.8
            elements = []
            for i, (x, v) in enumerate(zip(x_vals, self.data)):
                cx  = ax.scale_x(x)                       # type: ignore
                cy  = scale_y(v)
                bh  = abs(cy - y0)
                top = min(cy, y0)
                elements.append(
                    f'<rect x="{cx - bw/2:.1f}" y="{top:.1f}" '
                    f'width="{bw:.1f}" height="{max(bh, 1):.1f}" '
                    f'fill="{self.color}" fill-opacity="0.85"/>'
                )
            return "\n".join(elements)

        pts  = " ".join(
            f"{ax.scale_x(x):.2f},{scale_y(v):.2f}"   # type: ignore
            for x, v in zip(x_vals, self.data)
        )
        out: list[str] = []
        if self.fill:
            y_base = scale_y(max(lo, 0))
            x0, xn = ax.scale_x(x_vals[0]), ax.scale_x(x_vals[-1])   # type: ignore
            poly = f"{x0:.2f},{y_base:.2f} " + pts + f" {xn:.2f},{y_base:.2f}"
            out.append(
                f'<polygon points="{poly}" fill="{self.color}" '
                f'fill-opacity="{self.fill_alpha}" stroke="none"/>'
            )
        out.append(
            f'<polyline points="{pts}" fill="none" stroke="{self.color}" '
            f'stroke-width="{self.line_width}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        if self.show_last_dot:
            lx = ax.scale_x(x_vals[-1])                  # type: ignore
            ly = scale_y(self.data[-1])
            out.append(
                f'<circle cx="{lx:.2f}" cy="{ly:.2f}" '
                f'r="{self.line_width + 1}" fill="{self.color}"/>'
            )
        return "\n".join(out)
