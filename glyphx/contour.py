"""
GlyphX ContourSeries — 2D filled contour plot (companion to Surface3D).

Renders isocontour bands on a regular grid, equivalent to
Matplotlib's ``ax.contourf()`` and ``ax.contour()``.  Works inside a
regular :class:`~glyphx.Figure` (not Figure3D).
"""
from __future__ import annotations

import math
import numpy as np

from .series    import BaseSeries
from .colormaps import apply_colormap, colormap_colors
from .utils     import svg_escape, _format_tick


class ContourSeries(BaseSeries):
    """
    2D filled contour plot — iso-lines and/or filled bands.

    Args:
        x:        1-D X grid values (length N).
        y:        1-D Y grid values (length M).
        z:        2-D Z matrix, shape (M, N).
        levels:   Number of contour levels, or an explicit list of Z values.
        cmap:     Colormap for fill bands.
        filled:   Draw filled colour bands between levels.
        lines:    Draw contour lines at each level.
        line_color: Color for contour lines when not filled.
        line_width: Contour line stroke width.
        alpha:    Fill opacity.
        label:    Legend label.
    """

    def __init__(
        self,
        x, y, z,
        levels:     int | list[float] = 10,
        cmap:       str               = "viridis",
        filled:     bool              = True,
        lines:      bool              = True,
        line_color: str               = "#ffffff88",
        line_width: float             = 0.8,
        alpha:      float             = 0.85,
        label:      str | None        = None,
    ) -> None:
        self.x_1d      = list(x)
        self.y_1d      = list(y)
        self.z_mat     = np.asarray(z, dtype=float)
        self.cmap      = cmap
        self.filled    = filled
        self.lines     = lines
        self.line_color = line_color
        self.line_width = float(line_width)
        self.alpha     = float(alpha)

        z_min, z_max = float(self.z_mat.min()), float(self.z_mat.max())
        if isinstance(levels, int):
            self._levels = [z_min + i * (z_max - z_min) / levels
                            for i in range(levels + 1)]
        else:
            self._levels = sorted(levels)

        # BaseSeries domain — X is x_1d, Y is y_1d for Axes scaling
        all_x = list(x) + list(x)
        all_y = list(y) + list(y)
        super().__init__(x=list(x), y=list(y), color="#000", label=label)

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        """Render filled contour bands using linear interpolation."""
        scale_x = ax.scale_x   # type: ignore
        scale_y = ax.scale_y   # type: ignore
        elements: list[str] = []

        nx = len(self.x_1d)
        ny = len(self.y_1d)

        # For each band between level[k] and level[k+1], shade cells
        n_bands = len(self._levels) - 1
        band_colors = colormap_colors(self.cmap, max(n_bands, 2))

        for band_idx in range(n_bands):
            lo = self._levels[band_idx]
            hi = self._levels[band_idx + 1]
            col = band_colors[band_idx % len(band_colors)]

            # Find grid cells that intersect this band
            for j in range(ny - 1):
                for i in range(nx - 1):
                    zs = [
                        float(self.z_mat[j,   i]),
                        float(self.z_mat[j,   i+1]),
                        float(self.z_mat[j+1, i+1]),
                        float(self.z_mat[j+1, i]),
                    ]
                    if max(zs) < lo or min(zs) > hi:
                        continue

                    # Compute pixel corners of this cell
                    xs = [scale_x(self.x_1d[i]),   scale_x(self.x_1d[i+1]),
                          scale_x(self.x_1d[i+1]),  scale_x(self.x_1d[i])]
                    ys = [scale_y(self.y_1d[j]),   scale_y(self.y_1d[j]),
                          scale_y(self.y_1d[j+1]),  scale_y(self.y_1d[j+1])]

                    if self.filled:
                        pts = " ".join(f"{px:.1f},{py:.1f}" for px,py in zip(xs,ys))
                        elements.append(
                            f'<polygon points="{pts}" fill="{col}" '
                            f'fill-opacity="{self.alpha}" stroke="none"/>'
                        )

        # Draw contour lines at each level using marching squares (simplified)
        if self.lines:
            for lv in self._levels[1:-1]:
                segs = self._marching_squares(lv, scale_x, scale_y)
                for x0, y0, x1, y1 in segs:
                    elements.append(
                        f'<line x1="{x0:.1f}" y1="{y0:.1f}" '
                        f'x2="{x1:.1f}" y2="{y1:.1f}" '
                        f'stroke="{self.line_color}" '
                        f'stroke-width="{self.line_width}"/>'
                    )

        # Colorbar
        if self.filled:
            elements.append(self._colorbar_svg(ax, band_colors))

        return "\n".join(elements)

    def _marching_squares(self, level: float, sx, sy) -> list[tuple]:
        """Simplified marching squares: return line segments at 'level'."""
        nx, ny = len(self.x_1d), len(self.y_1d)
        segs = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                # Cell corners: 0=BL, 1=BR, 2=TR, 3=TL
                z00 = float(self.z_mat[j,   i])
                z10 = float(self.z_mat[j,   i+1])
                z11 = float(self.z_mat[j+1, i+1])
                z01 = float(self.z_mat[j+1, i])

                px = [sx(self.x_1d[i]),   sx(self.x_1d[i+1]),
                      sx(self.x_1d[i+1]),  sx(self.x_1d[i])]
                py = [sy(self.y_1d[j]),   sy(self.y_1d[j]),
                      sy(self.y_1d[j+1]),  sy(self.y_1d[j+1])]

                def interp(za, zb, pa, pb):
                    if zb == za:
                        return ((pa[0]+pb[0])/2, (pa[1]+pb[1])/2)
                    t = (level - za) / (zb - za)
                    return (pa[0] + t*(pb[0]-pa[0]), pa[1] + t*(pb[1]-pa[1]))

                corners = list(zip(
                    [z00, z10, z11, z01],
                    [(px[0],py[0]),(px[1],py[1]),(px[2],py[2]),(px[3],py[3])]
                ))
                above = [z > level for z, _ in corners]
                code  = sum(1<<k for k, v in enumerate(above) if v)

                edges = {
                    0:[], 15:[], 1:[0,3], 14:[0,3], 2:[0,1], 13:[0,1],
                    3:[1,3], 12:[1,3], 4:[1,2], 11:[1,2], 5:[0,1,2,3],
                    10:[0,1,2,3], 6:[0,2], 9:[0,2], 7:[2,3], 8:[2,3],
                }
                edge_pairs = edges.get(code, [])
                edge_verts = [
                    (0,1), (1,2), (2,3), (3,0)
                ]
                pts = []
                for ei in edge_pairs:
                    a, b = edge_verts[ei]
                    za, pa = corners[a]
                    zb, pb = corners[b]
                    if (za > level) != (zb > level):
                        pts.append(interp(za, zb, pa, pb))
                if len(pts) == 2:
                    segs.append((pts[0][0], pts[0][1], pts[1][0], pts[1][1]))
        return segs

    def _colorbar_svg(self, ax, colors: list[str]) -> str:
        """Vertical colorbar strip on the right side."""
        from .utils import _format_tick
        bx = ax.width - 20    # type: ignore
        by = ax.padding        # type: ignore
        bh = ax.height - 2 * ax.padding  # type: ignore
        bw = 12
        steps = len(colors)
        step_h = bh / steps
        items = []
        for k, col in enumerate(reversed(colors)):
            ry = by + k * step_h
            items.append(
                f'<rect x="{bx}" y="{ry:.1f}" width="{bw}" '
                f'height="{step_h + 0.5:.1f}" fill="{col}"/>'
            )
        items.append(
            f'<text x="{bx + bw + 3}" y="{by + 8}" font-size="10" '
            f'fill="{ax.theme.get("text_color","#000")}">'   # type: ignore
            f'{_format_tick(self._levels[-1])}</text>'
        )
        items.append(
            f'<text x="{bx + bw + 3}" y="{by + bh}" font-size="10" '
            f'fill="{ax.theme.get("text_color","#000")}">'   # type: ignore
            f'{_format_tick(self._levels[0])}</text>'
        )
        return "\n".join(items)
