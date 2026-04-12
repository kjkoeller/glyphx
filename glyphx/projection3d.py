"""
GlyphX 3D projection utilities.

Shared orthographic projection engine used by both the SVG static
renderer and as a data-normalisation layer for the Three.js HTML renderer.
"""
from __future__ import annotations

import math
from typing import NamedTuple


class Projected(NamedTuple):
    px: float    # screen X pixel
    py: float    # screen Y pixel (SVG convention: positive = down)
    depth: float # depth value for painter's-algorithm sorting (larger = farther)


def normalize(values: list[float]) -> tuple[list[float], float, float]:
    """Return (normalised_to_minus1_plus1, min_val, max_val)."""
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    return [(v - lo) / span * 2 - 1 for v in values], lo, hi


class Camera3D:
    """
    Orthographic camera for projecting 3D data to 2D SVG.

    Angles follow the geographic convention:
      azimuth  — rotation around the vertical (Z) axis, degrees.
                 0° = looking from +Y; 90° = looking from +X.
      elevation — tilt above the horizontal plane, degrees.
                  0° = side view; 90° = top-down.

    The right-hand coordinate system uses:
      X → right, Y → into screen (depth), Z → up.
    """

    def __init__(
        self,
        azimuth:   float = 45.0,
        elevation: float = 30.0,
        cx: float  = 0.0,    # canvas centre x
        cy: float  = 0.0,    # canvas centre y
        scale: float = 1.0,  # pixels per normalised unit
    ) -> None:
        self.azimuth   = azimuth
        self.elevation = elevation
        self.cx        = cx
        self.cy        = cy
        self.scale     = scale
        self._update()

    def _update(self) -> None:
        az = math.radians(self.azimuth)
        el = math.radians(self.elevation)
        self._cos_az = math.cos(az)
        self._sin_az = math.sin(az)
        self._cos_el = math.cos(el)
        self._sin_el = math.sin(el)

    def project(self, x: float, y: float, z: float) -> Projected:
        """Project a normalised 3D point to 2D screen coordinates."""
        # Rotate around Z (azimuth)
        rx =  x * self._cos_az + y * self._sin_az
        ry = -x * self._sin_az + y * self._cos_az
        rz =  z

        # Tilt by elevation
        fx =  rx
        fy =  ry * self._cos_el - rz * self._sin_el   # depth axis
        fz = -ry * self._sin_el - rz * self._cos_el   # screen vertical (up=negative SVG)

        # Orthographic projection → pixel
        px = self.cx + fx * self.scale
        py = self.cy - fz * self.scale   # SVG Y is inverted

        return Projected(px, py, fy)  # fy = depth

    def project_all(
        self,
        xs: list[float],
        ys: list[float],
        zs: list[float],
    ) -> list[Projected]:
        """Project a batch of points."""
        return [self.project(x, y, z) for x, y, z in zip(xs, ys, zs)]


def axis_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    """Evenly spaced tick values in [lo, hi]."""
    return [lo + i * (hi - lo) / n for i in range(n + 1)]


def norm_to_data(norm: float, lo: float, hi: float) -> float:
    """Convert a [-1, 1] normalised value back to data space."""
    return lo + (norm + 1) / 2 * (hi - lo)


def _format_3d_tick(v: float) -> str:
    """Compact tick label for 3D axes."""
    if v == 0:
        return "0"
    abs_v = abs(v)
    if abs_v >= 1e6:
        return f"{v/1e6:.1f}M"
    if abs_v >= 1e3:
        return f"{v/1e3:.1f}k"
    if v == int(v):
        return str(int(v))
    if abs_v >= 100:
        return f"{v:.0f}"
    if abs_v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"
