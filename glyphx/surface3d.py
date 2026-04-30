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
        threshold=None) -> None:
        self.x_1d                 = list(x)
        self.y_1d                 = list(y)
        self.z_mat                = [list(row) for row in z]
        self.cmap                 = cmap
        self.alpha                = float(alpha)
        self.wireframe            = wireframe
        self.wire_color           = wire_color
        self.label                = label
        self.threshold            = threshold
        self.last_downsample_info = None
        self.css_class            = f"series3d-{id(self) % 100000}"

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
        from .downsample import decimate_grid, cull_faces, _ds_comment, AUTO_THRESHOLD

        # Decimate grid before projection to keep face count manageable
        _thresh = self.threshold if self.threshold is not None else AUTO_THRESHOLD
        _orig_nx, _orig_ny = len(self.x_1d), len(self.y_1d)
        x_1d, y_1d, z_arr_dec = decimate_grid(
            self.x_1d, self.y_1d, self.z_mat, max_faces=_thresh
        )
        _orig_faces = (_orig_nx - 1) * (_orig_ny - 1)
        _new_faces  = (len(x_1d) - 1) * (len(y_1d) - 1)
        if _new_faces < _orig_faces:
            self.last_downsample_info = {
                'algorithm': 'grid-decimate',
                'original_n': _orig_faces,
                'thinned_n': _new_faces,
            }
        else:
            self.last_downsample_info = None
            x_1d = self.x_1d; y_1d = self.y_1d; z_arr_dec = self.z_mat

        import numpy as _np
        z_mat_use = [[float(v) for v in row] for row in z_arr_dec]

        nx = len(x_1d)
        ny = len(y_1d)

        # Normalise to [-1, 1]
        xn, xlo, xhi = normalize(x_1d)
        yn, ylo, yhi = normalize(y_1d)
        z_flat = [v for row in z_mat_use for v in row]
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
                z_vals = [z_mat_use[j][i],  z_mat_use[j][i+1],
                          z_mat_use[j+1][i+1], z_mat_use[j+1][i]]
                avg_z = sum(z_vals) / 4
                faces.append((depth, ps, avg_z))

        # Sub-pixel face culling then back-to-front sort
        faces = cull_faces(faces)
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
