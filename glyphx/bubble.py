"""
GlyphX BubbleSeries — scatter plot with a fourth size encoding variable.

A bubble chart is a scatter plot where each point has an additional
dimension encoded as circle area.  It beats Matplotlib's awkward
``scatter(s=size_array)`` interface, Seaborn (which has no bubble chart),
and Plotly's verbose ``go.Scatter(mode="markers", marker=dict(size=...))``.

    from glyphx import Figure
    from glyphx.bubble import BubbleSeries

    fig = Figure(title="GDP vs Life Expectancy", auto_display=False)
    fig.add(BubbleSeries(
        x=gdp,
        y=life_exp,
        size=population,           # raw values — auto-scaled to pixel radii
        color="#3b82f6",
        labels=country_names,      # shown in tooltip
        label="Countries",
    ))
    fig.show()
"""
from __future__ import annotations

import math
import numpy as np

from .series import BaseSeries
from .utils import svg_escape, _format_tick
from .colormaps import apply_colormap


class BubbleSeries(BaseSeries):
    """
    Scatter plot with circle area encoding a fourth variable.

    Unlike ``ScatterSeries(size=fixed_int)``, this accepts a *per-point*
    size array and scales radii so the smallest bubble is always
    ``min_radius`` pixels and the largest is ``max_radius`` pixels.

    Args:
        x:            X-axis values.
        y:            Y-axis values.
        size:         Per-point numeric values mapped to bubble area.
                      Can also be a fixed scalar to get uniform-sized
                      bubbles without the colormap overhead.
        color:        Flat fill color, or ``None`` when ``c=`` is used.
        c:            Per-point values for color encoding (colormap).
        cmap:         Colormap name (default ``"viridis"``).
        alpha:        Fill opacity 0–1 (default ``0.65``).
        min_radius:   Pixel radius of the smallest bubble (default 4).
        max_radius:   Pixel radius of the largest bubble (default 40).
        labels:       Per-point tooltip labels (list of str).
        label:        Legend label for the series.
        stroke:       Bubble outline color (default ``"#fff"``).
        stroke_width: Bubble outline width in pixels (default ``0.8``).
    """

    def __init__(
        self,
        x,
        y,
        size,
        color: str | None     = None,
        c=None,
        cmap: str             = "viridis",
        alpha: float          = 0.65,
        min_radius: float     = 4.0,
        max_radius: float     = 40.0,
        labels: list | None   = None,
        label: str | None     = None,
        stroke: str           = "#ffffff",
        stroke_width: float   = 0.8,
        title: str | None     = None,
    ) -> None:
        super().__init__(x=list(x), y=list(y), color=color or "#3b82f6",
                         label=label, title=title)
        self.c            = c
        self.cmap         = cmap
        self.alpha        = float(alpha)
        self.min_radius   = float(min_radius)
        self.max_radius   = float(max_radius)
        self.labels       = labels
        self.stroke       = stroke
        self.stroke_width = float(stroke_width)

        # Normalise size array to pixel radii
        size_arr = np.asarray(size, dtype=float)
        if size_arr.ndim == 0:
            # Scalar — uniform size
            self._radii = np.full(len(self.x), float(size_arr))
        else:
            s_min, s_max = size_arr.min(), size_arr.max()
            if s_max == s_min:
                self._radii = np.full(len(self.x),
                                      (self.min_radius + self.max_radius) / 2)
            else:
                # Scale by area (proportional to sqrt of value)
                norm = np.sqrt((size_arr - s_min) / (s_max - s_min))
                self._radii = (
                    self.min_radius
                    + norm * (self.max_radius - self.min_radius)
                )

        # Colour array (for colormap mode)
        if self.c is not None:
            c_arr       = np.asarray(self.c, dtype=float)
            c_min, c_max = c_arr.min(), c_arr.max()
            span = c_max - c_min or 1.0
            self._c_norm = ((c_arr - c_min) / span).tolist()
        else:
            self._c_norm = None

    # ------------------------------------------------------------------
    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y   # type: ignore
        x_vals   = getattr(self, "_numeric_x", self.x)
        elements: list[str] = []

        # Draw largest bubbles first so small ones aren't hidden
        order = np.argsort(self._radii)[::-1]

        for idx in order:
            x_val  = x_vals[idx]
            y_val  = self.y[idx]
            radius = float(self._radii[idx])

            px = ax.scale_x(x_val)   # type: ignore
            py = scale_y(y_val)

            # Colour
            if self._c_norm is not None:
                fill = apply_colormap(self._c_norm[idx], self.cmap)
            else:
                fill = self.color

            # Tooltip label
            point_label = (
                self.labels[idx]
                if self.labels and idx < len(self.labels)
                else (self.label or "")
            )
            tooltip = (
                f'data-x="{svg_escape(str(self.x[idx]))}" '
                f'data-y="{svg_escape(str(y_val))}" '
                f'data-label="{svg_escape(str(point_label))}" '
                f'data-size="{svg_escape(_format_tick(radius))}"'
            )

            elements.append(
                f'<circle class="glyphx-point {self.css_class}" '
                f'cx="{px:.2f}" cy="{py:.2f}" r="{radius:.2f}" '
                f'fill="{fill}" fill-opacity="{self.alpha}" '
                f'stroke="{self.stroke}" stroke-width="{self.stroke_width}" '
                f'{tooltip}/>'
            )

        # Colorbar if using c= encoding
        if self._c_norm is not None and self.c is not None:
            from .colormaps import render_colorbar_svg
            c_arr = np.asarray(self.c, dtype=float)
            elements.append(render_colorbar_svg(
                cmap=self.cmap,
                vmin=float(c_arr.min()),
                vmax=float(c_arr.max()),
                x=ax.width - 30,        # type: ignore
                y=ax.padding,           # type: ignore
                width=12,
                height=ax.height - 2 * ax.padding,   # type: ignore
                font=ax.theme.get("font", "sans-serif"),  # type: ignore
                text_color=ax.theme.get("text_color", "#000"),  # type: ignore
            ))


        return "\n".join(elements)

    def _size_legend(self, ax: object) -> str:
        """Render a small 3-bubble size guide in the bottom-right corner."""
        size_arr = np.asarray([self.min_radius, (self.min_radius + self.max_radius) / 2,
                                self.max_radius])
        x_base  = ax.width  - 60      # type: ignore
        y_base  = ax.height - 20      # type: ignore
        font    = ax.theme.get("font", "sans-serif")  # type: ignore
        tc      = ax.theme.get("text_color", "#000")  # type: ignore
        items: list[str] = []
        for r in size_arr:
            items.append(
                f'<circle cx="{x_base:.0f}" cy="{y_base - r:.0f}" '
                f'r="{r:.1f}" fill="none" stroke="{tc}" stroke-width="0.8" opacity="0.5"/>'
            )
            x_base += r * 2 + 6
        return "\n".join(items)
