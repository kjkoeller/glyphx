"""
GlyphX ChoroplethSeries -- geographic choropleth map.

Renders SVG path-based choropleth maps from GeoJSON data.  No tile server,
no CDN dependency -- pure SVG paths projected from GeoJSON coordinates.

    from glyphx import Figure
    from glyphx.choropleth import ChoroplethSeries, load_world_geojson
    import json

    # Load GeoJSON (user-supplied)
    geo = json.load(open("world.geojson"))

    # Attach data: map feature property -> numeric value
    data = {"USA": 63000, "GBR": 42000, "DEU": 51000, "FRA": 45000}

    fig = Figure(width=900, height=500, auto_display=False)
    fig.add(ChoroplethSeries(geo, data, key="iso_a3", cmap="viridis",
                              label="GDP per capita"))
    fig.show()
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from .colormaps import apply_colormap, colormap_colors
from .utils     import svg_escape, _format_tick


# ---------------------------------------------------------------------------
# Mercator projection
# ---------------------------------------------------------------------------

def _mercator_xy(lon: float, lat: float) -> tuple[float, float]:
    """Convert (lon, lat) degrees to Mercator (x, y) in [-π, π]."""
    x = math.radians(lon)
    lat_r = math.radians(max(-85.05, min(85.05, lat)))
    y = math.log(math.tan(math.pi / 4 + lat_r / 2))
    return x, y


def _project_coords(
    coords: list,
    lon_min: float, lon_max: float,
    y_min:   float, y_max:   float,
    width:   float, height:  float,
    pad:     float = 10,
) -> list[tuple[float, float]]:
    """Project GeoJSON coordinate pairs to pixel (x, y)."""
    result = []
    plot_w = width  - 2 * pad
    plot_h = height - 2 * pad

    for pair in coords:
        try:
            lon, lat = float(pair[0]), float(pair[1])
        except (TypeError, IndexError):
            continue
        mx, my = _mercator_xy(lon, lat)
        px = pad + (mx - lon_min) / max(lon_max - lon_min, 1e-9) * plot_w
        py = pad + (y_max - my)   / max(y_max  - y_min,   1e-9) * plot_h
        result.append((px, py))
    return result


def _coord_bounds(features: list) -> tuple[float, float, float, float]:
    """Find mercator (x_min, x_max, y_min, y_max) across all features."""
    all_lons: list[float] = []
    all_ys:   list[float] = []

    def _walk(coords, depth=0):
        if not coords:
            return
        if isinstance(coords[0], (int, float)):
            try:
                mx, my = _mercator_xy(float(coords[0]), float(coords[1]))
                all_lons.append(mx); all_ys.append(my)
            except Exception:
                pass
        else:
            for sub in coords:
                _walk(sub, depth + 1)

    for feat in features:
        geo = feat.get("geometry") or {}
        _walk(geo.get("coordinates", []))

    if not all_lons:
        return -math.pi, math.pi, -2.0, 2.0
    return min(all_lons), max(all_lons), min(all_ys), max(all_ys)


def _coords_to_path(ring: list[tuple[float, float]]) -> str:
    """Convert a list of pixel (x,y) points to an SVG path 'd' string."""
    if not ring:
        return ""
    parts = [f"M {ring[0][0]:.2f},{ring[0][1]:.2f}"]
    for x, y in ring[1:]:
        parts.append(f"L {x:.2f},{y:.2f}")
    parts.append("Z")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# ChoroplethSeries
# ---------------------------------------------------------------------------

class ChoroplethSeries:
    """
    SVG-path choropleth map from GeoJSON.

    No tiles, no CDN -- renders as pure SVG paths projected via Mercator.

    Args:
        geojson:    GeoJSON FeatureCollection dict (``{"type":"FeatureCollection",
                    "features":[...]}``) or a list of feature dicts.
        data:       ``{feature_key: numeric_value}`` mapping.
        key:        GeoJSON feature property name that matches ``data`` keys.
        cmap:       Colormap name.
        missing_color: Fill color for features with no matching data entry.
        stroke:     Border stroke color.
        stroke_width: Border stroke width.
        alpha:      Fill opacity.
        label:      Legend / tooltip label.
        title:      Chart title (forwarded to Figure).
    """

    def __init__(
        self,
        geojson:         dict | list,
        data:            dict[str, float],
        key:             str              = "name",
        cmap:            str              = "viridis",
        missing_color:   str              = "#e0e0e0",
        stroke:          str              = "#ffffff",
        stroke_width:    float            = 0.4,
        alpha:           float            = 0.90,
        label:           str | None       = None,
        title:           str | None       = None,
    ) -> None:
        self.cmap          = cmap
        self.data          = data
        self.key           = key
        self.missing_color = missing_color
        self.stroke        = stroke
        self.stroke_width  = float(stroke_width)
        self.alpha         = float(alpha)
        self.label         = label
        self.title         = title
        self.css_class     = f"series-{id(self) % 100000}"

        # Extract feature list
        if isinstance(geojson, dict):
            self._features = geojson.get("features", [])
        else:
            self._features = list(geojson)

        # Value range
        vals = [v for v in data.values() if v is not None]
        self._vmin = min(vals) if vals else 0
        self._vmax = max(vals) if vals else 1
        self._vspan = (self._vmax - self._vmin) or 1

        # Axis stubs (axis-free series)
        self.x = None
        self.y = None

    def _feature_color(self, feature: dict) -> str:
        props = feature.get("properties") or {}
        k     = props.get(self.key)
        val   = self.data.get(k) if k is not None else None
        if val is None:
            return self.missing_color
        norm = (float(val) - self._vmin) / self._vspan
        return apply_colormap(norm, self.cmap)

    def to_svg(self, ax: object = None) -> str:  # type: ignore
        W = getattr(ax, "width",  800) if ax else 800
        H = getattr(ax, "height", 500) if ax else 500
        font = ax.theme.get("font", "sans-serif") if ax else "sans-serif"   # type: ignore
        tc   = ax.theme.get("text_color", "#000") if ax else "#000"         # type: ignore

        lon_min, lon_max, y_min, y_max = _coord_bounds(self._features)

        elements: list[str] = []

        def _render_ring(ring_coords, color):
            pts = _project_coords(ring_coords, lon_min, lon_max,
                                   y_min, y_max, W, H)
            return _coords_to_path(pts)

        for feat in self._features:
            geo   = feat.get("geometry") or {}
            color = self._feature_color(feat)
            props = feat.get("properties") or {}
            name  = props.get(self.key, "")
            val   = self.data.get(name)
            tip   = f'{svg_escape(str(name))}: {_format_tick(val)}' if val is not None else svg_escape(str(name))

            gtype = geo.get("type", "")
            coords = geo.get("coordinates", [])

            paths: list[str] = []
            if gtype == "Polygon":
                for ring in coords:
                    d = _render_ring(ring, color)
                    if d:
                        paths.append(d)
            elif gtype == "MultiPolygon":
                for poly in coords:
                    for ring in poly:
                        d = _render_ring(ring, color)
                        if d:
                            paths.append(d)

            if paths:
                combined = " ".join(paths)
                elements.append(
                    f'<path class="glyphx-point {self.css_class}" '
                    f'd="{combined}" '
                    f'fill="{color}" fill-opacity="{self.alpha}" '
                    f'stroke="{self.stroke}" stroke-width="{self.stroke_width}" '
                    f'data-label="{tip}"/>'
                )

        # Colorbar
        if self.data:
            cb_x  = W - 28
            cb_y  = H // 4
            cb_h  = H // 2
            steps = 40
            sh    = cb_h / steps
            for k in range(steps):
                norm = 1 - k / steps
                col  = apply_colormap(norm, self.cmap)
                elements.append(
                    f'<rect x="{cb_x}" y="{cb_y + k * sh:.1f}" '
                    f'width="12" height="{sh + 0.5:.1f}" fill="{col}"/>'
                )
            elements.append(
                f'<text x="{cb_x + 14}" y="{cb_y + 8}" '
                f'font-size="9" font-family="{font}" fill="{tc}">'
                f'{_format_tick(self._vmax)}</text>'
            )
            elements.append(
                f'<text x="{cb_x + 14}" y="{cb_y + cb_h}" '
                f'font-size="9" font-family="{font}" fill="{tc}">'
                f'{_format_tick(self._vmin)}</text>'
            )

        return "\n".join(elements)
