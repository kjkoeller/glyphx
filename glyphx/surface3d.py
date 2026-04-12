"""
GlyphX Surface3DSeries — 3D surface / mesh plot.

Renders a smooth coloured surface from a 2-D Z matrix defined over a
regular X×Y grid.  The SVG path uses the painter's algorithm: faces
sorted back-to-front so nearer faces always draw on top.
"""
from __future__ import annotations

import math
import numpy as np

from .projection3d import Camera3D, normalize, _format_3d_tick
from .colormaps     import apply_colormap
from .utils         import svg_escape


class Surface3DSeries:
    """
    3D surface plot — z = f(x, y) over a regular grid.

    Args:
        x:        1-D X grid values (length N).
        y:        1-D Y grid values (length M).
        z:        2-D Z matrix, shape (M, N).  ``z[j][i]`` is the height
                  at ``(x[i], y[j])``.
        cmap:     Colormap name (default ``"viridis"``).
        alpha:    Surface opacity 0–1.
        wireframe:If ``True``, draw grid lines over the surface.
        wire_color: Color of wireframe lines.
        label:    Legend / tooltip label.
    """

    def __init__(
        self,
        x, y, z,
        cmap:        str   = "viridis",
        alpha:       float = 0.90,
        wireframe:   bool  = True,
        wire_color:  str   = "#ffffff44",
        label:       str | None = None,
    ) -> None:
        self.x_1d      = list(x)
        self.y_1d      = list(y)
        self.z_mat     = [list(row) for row in z]   # M × N
        self.cmap      = cmap
        self.alpha     = float(alpha)
        self.wireframe = wireframe
        self.wire_color = wire_color
        self.label     = label
        self.css_class = f"series3d-{id(self) % 100000}"

        # Pre-compute face colours from Z values
        z_arr = np.asarray(z, dtype=float)
        self._z_min = float(z_arr.min())
        self._z_max = float(z_arr.max())
        self._z_span = self._z_max - self._z_min or 1.0

    def _face_color(self, z_val: float) -> str:
        norm = (z_val - self._z_min) / self._z_span
        return apply_colormap(norm, self.cmap)

    def to_svg(self, cam: Camera3D,
               x_range, y_range, z_range) -> str:
        """
        Render each grid quad as a coloured SVG polygon.

        Quads are sorted back-to-front by their average projected depth.
        """
        nx = len(self.x_1d)
        ny = len(self.y_1d)

        # Normalise to [-1, 1]
        xn, xlo, xhi = normalize(self.x_1d)
        yn, ylo, yhi = normalize(self.y_1d)
        z_flat = [v for row in self.z_mat for v in row]
        zn_flat, zlo, zhi = normalize(z_flat)
        z_norm = [zn_flat[j * nx + i] for j in range(ny) for i in range(nx)]

        def znv(j, i):
            return z_norm[j * nx + i]

        # Project all grid vertices
        verts: list[list] = []
        for j in range(ny):
            row = []
            for i in range(nx):
                p = cam.project(xn[i], yn[j], znv(j, i))
                row.append(p)
            verts.append(row)

        # Build quads (i, j) → (i+1, j) → (i+1, j+1) → (i, j+1)
        faces = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                ps = [verts[j][i], verts[j][i+1],
                      verts[j+1][i+1], verts[j+1][i]]
                depth = sum(p.depth for p in ps) / 4
                # Average Z value for colour
                z_vals = [self.z_mat[j][i],  self.z_mat[j][i+1],
                          self.z_mat[j+1][i+1], self.z_mat[j+1][i]]
                avg_z = sum(z_vals) / 4
                faces.append((depth, ps, avg_z))

        # Sort back-to-front
        faces.sort(key=lambda f: f[0])

        elements: list[str] = []
        for depth, ps, avg_z in faces:
            pts = " ".join(f"{p.px:.1f},{p.py:.1f}" for p in ps)
            col = self._face_color(avg_z)
            elements.append(
                f'<polygon points="{pts}" fill="{col}" '
                f'fill-opacity="{self.alpha}" stroke="none"/>'
            )
            if self.wireframe:
                elements.append(
                    f'<polygon points="{pts}" fill="none" '
                    f'stroke="{self.wire_color}" stroke-width="0.4"/>'
                )

        return "\n".join(elements)

    def to_threejs_data(self) -> dict:
        return {
            "type":       "surface",
            "x":          self.x_1d,
            "y":          self.y_1d,
            "z":          self.z_mat,
            "cmap":       self.cmap,
            "alpha":      self.alpha,
            "wireframe":  self.wireframe,
            "wire_color": self.wire_color,
            "label":      self.label or "",
        }
