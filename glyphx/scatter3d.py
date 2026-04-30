"""
GlyphX Scatter3DSeries — 3D scatter plot.

Renders interactively via Three.js (HTML output) and as a static
orthographic SVG.  Supports a fourth variable encoded as color.
"""
from __future__ import annotations

import json
import math

import numpy as np

from .projection3d import Camera3D, normalize, _format_3d_tick
from .colormaps     import apply_colormap
from .downsample    import AUTO_THRESHOLD
from .utils         import svg_escape


class Scatter3DSeries:
    """
    3D scatter plot.

    Args:
        x, y, z:      Data coordinates (same length).
        color:        Flat hex fill color when ``c`` is not used.
        c:            Per-point numeric values for colormap encoding.
        cmap:         Colormap name (default ``"viridis"``).
        size:         Marker size in pixels / Three.js units.
        label:        Legend / tooltip label.
        alpha:        Point opacity 0–1.
    """

    def __init__(
        self,
        x, y, z,
        color:  str           = "#2563eb",
        c:      list | None   = None,
        cmap:   str           = "viridis",
        size:   float         = 5.0,
        label:  str | None    = None,
        alpha:  float         = 0.85,
        threshold=None) -> None:
        self.x                    = list(x)
        self.y                    = list(y)
        self.z                    = list(z)
        self.color                = color
        self.c                    = c
        self.cmap                 = cmap
        self.size                 = float(size)
        self.label                = label
        self.alpha                = float(alpha)
        self.threshold            = threshold
        self.last_downsample_info = None
        self.css_class            = f"series3d-{id(self) % 100000}"

        # Pre-compute per-point colors
        if c is not None:
            c_arr = np.asarray(c, dtype=float)
            lo, hi = c_arr.min(), c_arr.max()
            span = hi - lo or 1.0
            self._point_colors = [
                apply_colormap(float((v - lo) / span), cmap) for v in c_arr
            ]
        else:
            self._point_colors = [color] * len(self.x)

    def to_svg(self, cam: Camera3D,
               x_range: tuple, y_range: tuple, z_range: tuple) -> str:
        """Render as SVG circles with 3D voxel thinning for large datasets."""
        from .projection3d import normalize as _norm
        from .downsample import voxel_thin_3d, _ds_comment

        x_plot, y_plot, z_plot = self.x, self.y, self.z
        point_colors = list(self._point_colors)

        _thresh = self.threshold if self.threshold is not None else AUTO_THRESHOLD
        _ds_svg = ""
        if len(x_plot) > _thresh:
            _orig_n = len(x_plot)
            x_plot, y_plot, z_plot, point_colors = voxel_thin_3d(
                x_plot, y_plot, z_plot, colors=point_colors,
                max_points=_thresh,
            )
            _ds_svg = _ds_comment(_orig_n, len(x_plot), 'voxel-3D')
            self.last_downsample_info = {
                'algorithm': 'voxel-3D',
                'original_n': _orig_n,
                'thinned_n': len(x_plot),
            }
        else:
            self.last_downsample_info = None

        xn, xlo, xhi = _norm(x_plot)
        yn, ylo, yhi = _norm(y_plot)
        zn, zlo, zhi = _norm(z_plot)

        pts = [cam.project(x, y, z) for x, y, z in zip(xn, yn, zn)]
        # Sort back-to-front (painter's algorithm)
        order = sorted(range(len(pts)), key=lambda i: pts[i].depth)

        elements: list[str] = [_ds_svg] if _ds_svg else []
        x_list = list(x_plot); y_list = list(y_plot); z_list = list(z_plot)
        for i in order:
            p     = pts[i]
            col   = point_colors[i]
            x_raw = x_list[i]
            y_raw = y_list[i]
            z_raw = z_list[i]
            tip   = f"({_format_3d_tick(x_raw)}, {_format_3d_tick(y_raw)}, {_format_3d_tick(z_raw)})"
            if self.label:
                tip = f"{self.label}: {tip}"
            elements.append(
                f'<circle cx="{p.px:.1f}" cy="{p.py:.1f}" r="{self.size}" '
                f'fill="{col}" fill-opacity="{self.alpha}" '
                f'stroke="#fff" stroke-width="0.4" '
                f'data-label="{svg_escape(tip)}"/>'
            )
        return "\n".join(elements)

    def to_threejs_data(self) -> dict:
        """Serialise series data for the Three.js HTML renderer."""
        return {
            "type":   "scatter",
            "x":      self.x,
            "y":      self.y,
            "z":      self.z,
            "colors": self._point_colors,
            "size":   self.size,
            "alpha":  self.alpha,
            "label":  self.label or "",
        }
