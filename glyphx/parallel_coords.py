"""
GlyphX ParallelCoordinatesSeries — high-dimensional data visualization.

Each row of data becomes a polyline drawn across a set of parallel
vertical axes, one axis per variable.  This beats Plotly's verbose
``go.Parcoords`` and Seaborn, which has no parallel coordinates at all.

    from glyphx import Figure
    from glyphx.parallel_coords import ParallelCoordinatesSeries
    import pandas as pd

    df = pd.read_csv("iris.csv")
    numeric_cols = ["sepal_length", "sepal_width", "petal_length", "petal_width"]

    fig = Figure(width=800, height=500, auto_display=False)
    fig.add(ParallelCoordinatesSeries(
        data=df[numeric_cols].values.tolist(),
        axes=numeric_cols,
        hue=df["species"].tolist(),       # color-code by a categorical column
        alpha=0.35,
    ))
    fig.show()
"""
from __future__ import annotations

import math
import numpy as np
from typing import Any

from .colormaps import colormap_colors, apply_colormap
from .utils import svg_escape, _format_tick, LEGEND_GUTTER


class ParallelCoordinatesSeries:
    """
    Parallel coordinates plot for high-dimensional data.

    Args:
        data:      2-D array-like (rows × variables).
        axes:      Column / variable names (length must match data columns).
        hue:       Per-row group labels for color coding.  When provided,
                   each unique value gets a distinct color from the theme
                   or ``cmap``.  Pass a numeric array to use a continuous
                   colormap instead.
        cmap:      Colormap name used when ``hue`` holds numeric values,
                   or when ``colors`` is not supplied (default ``"viridis"``).
        colors:    Explicit hex color per unique ``hue`` group (dict or list).
        alpha:     Line opacity 0–1 (default 0.45).  Lower values help
                   with overplotting.
        line_width: Stroke width (default 1.2).
        show_axes: Draw vertical axis lines and tick labels (default True).
        label:     Legend label (unused but kept for API consistency).
    """

    def __init__(
        self,
        data,
        axes: list[str],
        hue: list | None           = None,
        cmap: str                  = "viridis",
        colors: dict | list | None = None,
        alpha: float               = 0.45,
        line_width: float          = 1.2,
        show_axes: bool            = True,
        label: str | None          = None,
    ) -> None:
        self.matrix     = np.asarray(data, dtype=float)
        self.axes_names = list(axes)
        self.alpha      = float(alpha)
        self.line_width = float(line_width)
        self.show_axes  = show_axes
        self.label      = label
        self.css_class  = f"series-{id(self) % 100000}"
        self.cmap       = cmap
        self.hue        = hue

        n_rows, n_cols = self.matrix.shape
        if n_cols != len(axes):
            raise ValueError(
                f"data has {n_cols} columns but {len(axes)} axis names were given."
            )

        # Compute per-column min/max for normalisation
        self._col_min = self.matrix.min(axis=0)
        self._col_max = self.matrix.max(axis=0)
        self._col_range = np.where(
            self._col_max != self._col_min,
            self._col_max - self._col_min,
            1.0,
        )

        # Build per-row colour assignment
        if hue is None:
            self._row_colors = [apply_colormap(i / max(n_rows - 1, 1), cmap)
                                for i in range(n_rows)]
        else:
            hue_arr = np.asarray(hue)
            if np.issubdtype(hue_arr.dtype, np.number):
                # Continuous
                h_min, h_max = hue_arr.min(), hue_arr.max()
                span = h_max - h_min or 1.0
                self._row_colors = [
                    apply_colormap(float((v - h_min) / span), cmap)
                    for v in hue_arr
                ]
            else:
                # Categorical
                unique_groups = list(dict.fromkeys(str(v) for v in hue))
                if isinstance(colors, dict):
                    group_color = {k: v for k, v in colors.items()}
                elif isinstance(colors, list):
                    group_color = dict(zip(unique_groups, colors))
                else:
                    palette = colormap_colors(cmap, len(unique_groups))
                    group_color = dict(zip(unique_groups, palette))
                self._row_colors = [group_color.get(str(v), "#888") for v in hue]
                self._legend_items = group_color   # used for legend rendering

        # Unique groups for legend
        if hue is not None and not np.issubdtype(np.asarray(hue).dtype, np.number):
            self._groups = list(dict.fromkeys(str(v) for v in hue))
        else:
            self._groups = []

        # x/y stubs so Figure knows this is axis-free
        self.x = None
        self.y = None

    def to_svg(self, ax: object = None) -> str:   # type: ignore[override]
        if ax is None:
            pad_x, pad_y = 60, 50
            w, h = 740, 400
            font, tc = "sans-serif", "#000"
            grid_color = "#ddd"
        else:
            pad_x = ax.padding * 2    # type: ignore
            pad_y = ax.padding        # type: ignore
            w     = ax.width          # type: ignore
            h     = ax.height         # type: ignore
            font  = ax.theme.get("font", "sans-serif")  # type: ignore
            tc    = ax.theme.get("text_color", "#000")  # type: ignore
            grid_color = ax.theme.get("grid_color", "#ddd")  # type: ignore

        n_axes   = len(self.axes_names)
        n_rows   = self.matrix.shape[0]
        # Reserve right gutter for the legend so it never overlaps the axes
        _gutter  = LEGEND_GUTTER if self._groups else 0
        plot_w   = w - 2 * pad_x - _gutter
        plot_h   = h - 2 * pad_y
        ax_step  = plot_w / (n_axes - 1) if n_axes > 1 else plot_w

        # Axis X positions
        ax_x = [pad_x + i * ax_step for i in range(n_axes)]

        elements: list[str] = []

        # Vertical axis lines and tick labels
        if self.show_axes:
            TICKS = 5
            for j, (x_pos, name) in enumerate(zip(ax_x, self.axes_names)):
                # Axis line
                elements.append(
                    f'<line x1="{x_pos:.1f}" x2="{x_pos:.1f}" '
                    f'y1="{pad_y}" y2="{pad_y + plot_h}" '
                    f'stroke="{tc}" stroke-width="1.2" opacity="0.6"/>'
                )
                # Axis label
                elements.append(
                    f'<text x="{x_pos:.1f}" y="{pad_y - 8}" '
                    f'text-anchor="middle" font-size="12" '
                    f'font-family="{font}" fill="{tc}" font-weight="600">'
                    f'{svg_escape(name)}</text>'
                )
                # Tick labels
                col_min = self._col_min[j]
                col_rng = self._col_range[j]
                for k in range(TICKS + 1):
                    t   = k / TICKS
                    val = col_min + t * col_rng
                    y   = pad_y + plot_h - t * plot_h
                    elements.append(
                        f'<text x="{x_pos - 6:.1f}" y="{y + 3:.1f}" '
                        f'text-anchor="end" font-size="9" '
                        f'font-family="{font}" fill="{tc}" opacity="0.7">'
                        f'{_format_tick(val)}</text>'
                    )
                    elements.append(
                        f'<line x1="{x_pos - 3:.1f}" x2="{x_pos + 3:.1f}" '
                        f'y1="{y:.1f}" y2="{y:.1f}" '
                        f'stroke="{tc}" stroke-width="0.8" opacity="0.4"/>'
                    )

        # Data polylines (draw in reverse z-order so first rows are on top)
        for i in range(n_rows - 1, -1, -1):
            row   = self.matrix[i]
            color = self._row_colors[i]
            norm  = (row - self._col_min) / self._col_range     # [0, 1]
            pts   = " ".join(
                f"{ax_x[j]:.1f},{pad_y + plot_h - float(norm[j]) * plot_h:.1f}"
                for j in range(n_axes)
            )
            elements.append(
                f'<polyline class="glyphx-point {self.css_class}" '
                f'points="{pts}" fill="none" stroke="{color}" '
                f'stroke-width="{self.line_width}" opacity="{self.alpha}"/>'
            )

        # Categorical legend — always rendered in the right gutter
        if self._groups:
            legend_x = w - _gutter + 8 if _gutter else w - 110
            n_groups  = len(self._groups)
            total_h   = n_groups * 20
            legend_y  = (h - total_h) // 2   # vertically centred
            for k, grp in enumerate(self._groups):
                col = getattr(self, "_legend_items", {}).get(grp, "#888")
                gy  = legend_y + k * 20
                elements.append(
                    f'<rect x="{legend_x}" y="{gy}" width="12" height="12" '
                    f'fill="{col}" rx="2"/>'
                )
                elements.append(
                    f'<text x="{legend_x + 16}" y="{gy + 10}" '
                    f'font-size="11" font-family="{font}" fill="{tc}">'
                    f'{svg_escape(grp)}</text>'
                )

        return "\n".join(elements)
