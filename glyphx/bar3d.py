"""GlyphX Bar3DSeries — 3D bar chart."""
from __future__ import annotations

import numpy as np
from .projection3d import Camera3D, normalize, _format_3d_tick
from .colormaps     import apply_colormap, colormap_colors
from .utils         import svg_escape


class Bar3DSeries:
    """
    3D bar chart — one rectangular bar per (x, y) grid cell, height = z.

    Args:
        x:     1-D X positions (bar centres).
        y:     1-D Y positions (bar centres).
        z:     2-D Z matrix (heights), shape (len(y), len(x)), or 1-D if
               x and y are already paired point arrays.
        dx:    Bar width along X (default: auto from grid spacing).
        dy:    Bar depth along Y (default: auto from grid spacing).
        cmap:  Colormap name for bar colours (mapped by height).
        alpha: Bar opacity.
        label: Legend label.
    """

    def __init__(
        self,
        x, y, z,
        dx:    float | None = None,
        dy:    float | None = None,
        cmap:  str          = "viridis",
        alpha: float        = 0.85,
        label: str | None   = None,
    ) -> None:
        self.x_1d  = list(x)
        self.y_1d  = list(y)
        self.cmap  = cmap
        self.alpha = float(alpha)
        self.label = label

        z_arr = np.asarray(z, dtype=float)
        if z_arr.ndim == 1:
            # Paired points (len(x) == len(y) == len(z))
            self.paired = True
            self.z_vals = z_arr.tolist()
        else:
            # Grid: z[j][i] = height at (x[i], y[j])
            self.paired = False
            self.z_mat  = z_arr.tolist()
            self.z_vals = z_arr.flatten().tolist()

        z_flat = np.asarray(self.z_vals)
        self._z_min  = float(z_flat.min())
        self._z_max  = float(z_flat.max())
        self._z_span = self._z_max - self._z_min or 1.0

        # Auto bar width from spacing
        self._dx = dx if dx else (self.x_1d[1] - self.x_1d[0]) * 0.7 if len(self.x_1d) > 1 else 0.5
        self._dy = dy if dy else (self.y_1d[1] - self.y_1d[0]) * 0.7 if len(self.y_1d) > 1 else 0.5

    def _bar_color(self, z_val: float) -> str:
        norm = (z_val - self._z_min) / self._z_span
        return apply_colormap(norm, self.cmap)

    def to_svg(self, cam: Camera3D, x_range, y_range, z_range) -> str:
        xn, xlo, xhi = normalize(self.x_1d)
        yn, ylo, yhi = normalize(self.y_1d)

        # Scale bar dims proportionally
        x_span = xhi - xlo or 1
        y_span = yhi - ylo or 1
        dx_n = self._dx / x_span
        dy_n = self._dy / y_span

        all_z = self.z_vals
        z_max = max(all_z)
        zn_scale = lambda z: z / (self._z_max or 1) * 1.8 - 0.9

        bars = []
        if self.paired:
            for i, (xi, yi, zi) in enumerate(zip(xn, yn, self.z_vals)):
                bars.append((xi, yi, zi, self._bar_color(zi)))
        else:
            nx, ny = len(self.x_1d), len(self.y_1d)
            for j in range(ny):
                for i in range(nx):
                    zi = self.z_mat[j][i]
                    bars.append((xn[i], yn[j], zi, self._bar_color(zi)))

        # Sort back-to-front
        def _bar_depth(b):
            return cam.project(b[0], b[1], 0).depth
        bars.sort(key=_bar_depth)

        elements: list[str] = []
        for bx, by, bz, col in bars:
            bz_n = zn_scale(bz)
            hw = dx_n / 2
            hd = dy_n / 2

            # 8 corners of the bar box
            corners_3d = [
                (bx-hw, by-hd, -0.9),  (bx+hw, by-hd, -0.9),
                (bx+hw, by+hd, -0.9),  (bx-hw, by+hd, -0.9),
                (bx-hw, by-hd, bz_n),  (bx+hw, by-hd, bz_n),
                (bx+hw, by+hd, bz_n),  (bx-hw, by+hd, bz_n),
            ]
            c = [cam.project(*pt) for pt in corners_3d]

            def face(indices, shade=1.0):
                pts = " ".join(f"{c[k].px:.1f},{c[k].py:.1f}" for k in indices)
                r, g, b_ = int(col[1:3],16), int(col[3:5],16), int(col[5:7],16)
                sr = min(255, int(r * shade))
                sg = min(255, int(g * shade))
                sb = min(255, int(b_ * shade))
                shaded = f"#{sr:02x}{sg:02x}{sb:02x}"
                return (f'<polygon points="{pts}" fill="{shaded}" '
                        f'fill-opacity="{self.alpha}" stroke="#fff" stroke-width="0.3"/>')

            elements.append(face([4,5,6,7], 1.0))   # top
            elements.append(face([0,1,5,4], 0.80))   # front
            elements.append(face([1,2,6,5], 0.65))   # right

        return "\n".join(elements)

    def to_threejs_data(self) -> dict:
        bars = []
        if self.paired:
            for xi, yi, zi in zip(self.x_1d, self.y_1d, self.z_vals):
                bars.append({"x": xi, "y": yi, "z": zi,
                             "color": self._bar_color(zi),
                             "dx": self._dx, "dy": self._dy})
        else:
            nx, ny = len(self.x_1d), len(self.y_1d)
            for j in range(ny):
                for i in range(nx):
                    zi = self.z_mat[j][i]
                    bars.append({"x": self.x_1d[i], "y": self.y_1d[j],
                                 "z": zi, "color": self._bar_color(zi),
                                 "dx": self._dx, "dy": self._dy})
        return {"type": "bar3d", "bars": bars, "alpha": self.alpha,
                "label": self.label or ""}
