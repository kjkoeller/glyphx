"""GlyphX Line3DSeries — connected polyline in 3D space."""
from __future__ import annotations

from .projection3d import Camera3D, normalize, _format_3d_tick
from .utils         import svg_escape


class Line3DSeries:
    """
    3D line chart — a connected polyline through 3D coordinates.

    Args:
        x, y, z:     Path coordinates (same length, connected in order).
        color:       Line color.
        width:       Stroke width in pixels.
        linestyle:   ``"solid"``, ``"dashed"``, ``"dotted"``.
        label:       Legend label.
    """

    _DASH = {"solid": "", "dashed": "6,3", "dotted": "2,2"}

    def __init__(
        self, x, y, z,
        color:     str          = "#dc2626",
        width:     float        = 2.0,
        linestyle: str          = "solid",
        label:     str | None   = None,
        threshold: int | None   = None,
    ) -> None:
        self.x                   = list(x)
        self.y                   = list(y)
        self.z                   = list(z)
        self.color               = color
        self.width               = float(width)
        self.linestyle           = linestyle
        self.label               = label
        self.threshold           = threshold
        self.last_downsample_info = None
        self.css_class           = f"series3d-{id(self) % 100000}"

    def to_svg(self, cam: Camera3D,
               x_range, y_range, z_range) -> str:
        from .downsample import lttb_3d, AUTO_THRESHOLD, _ds_comment
        x_plot, y_plot, z_plot = self.x, self.y, self.z
        _ds_svg = ""
        _thresh = self.threshold if self.threshold is not None else AUTO_THRESHOLD
        if len(x_plot) > _thresh:
            _orig_n = len(x_plot)
            x_plot, y_plot, z_plot = lttb_3d(
                x_plot, y_plot, z_plot, cam, threshold=_thresh
            )
            _ds_svg = _ds_comment(_orig_n, len(x_plot), "LTTB-3D")
            self.last_downsample_info = {
                "algorithm": "LTTB-3D", "original_n": _orig_n, "thinned_n": len(x_plot)
            }
        else:
            self.last_downsample_info = None

        xn, *_ = normalize(x_plot)
        yn, *_ = normalize(y_plot)
        zn, *_ = normalize(z_plot)

        pts  = [cam.project(x, y, z) for x, y, z in zip(xn, yn, zn)]
        pts_str = " ".join(f"{p.px:.1f},{p.py:.1f}" for p in pts)
        dash = self._DASH.get(self.linestyle, "")
        return (_ds_svg + 
            f'<polyline points="{pts_str}" fill="none" '
            f'stroke="{self.color}" stroke-width="{self.width}" '
            f'stroke-dasharray="{dash}" '
            f'data-label="{svg_escape(self.label or "")}"/>'
        )

    def to_threejs_data(self) -> dict:
        return {
            "type":  "line",
            "x":     self.x,
            "y":     self.y,
            "z":     self.z,
            "color": self.color,
            "width": self.width,
            "label": self.label or "",
        }
