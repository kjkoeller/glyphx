"""
GlyphX perceptually-uniform colormaps.

Built-in scales designed for accuracy, not aesthetics:
  viridis, plasma, inferno, magma, cividis  — sequential, colorblind-safe
  coolwarm, rdbu                             — diverging
  spectral                                   — qualitative-ish rainbow

Usage::

    from glyphx.colormaps import apply_colormap, get_colormap, list_colormaps
    hex_color = apply_colormap(0.75, "viridis")

    # Color-encode a scatter plot
    ScatterSeries(x, y, c=z_values, cmap="plasma")
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Colormap definitions (hex color stops, low → high)
# ---------------------------------------------------------------------------
# All sequential maps are perceptually uniform (linearised luminance).
# Diverging maps are centred at neutral grey / white.

_MAPS: dict[str, list[str]] = {
    # ── Sequential ────────────────────────────────────────────────────────
    "viridis": [
        "#440154", "#472d7b", "#3b528b", "#2c728e", "#21918c",
        "#28ae80", "#5ec962", "#addc30", "#fde725",
    ],
    "plasma": [
        "#0d0887", "#5302a3", "#8b0aa5", "#b83289", "#db5c68",
        "#f48849", "#febd2a", "#f0f921",
    ],
    "inferno": [
        "#000004", "#320a5e", "#781c6d", "#bb3754", "#ed6925",
        "#fcb519", "#fcffa4",
    ],
    "magma": [
        "#000004", "#2c115f", "#721f81", "#b5367a", "#e55c30",
        "#fb8b09", "#fcfdbf",
    ],
    "cividis": [
        "#00224e", "#1f4579", "#3b6896", "#608aab", "#87a9bd",
        "#b2c8d1", "#dde9e2", "#fee838",
    ],
    # ── Diverging ─────────────────────────────────────────────────────────
    "coolwarm": [
        "#3b4cc0", "#6688ee", "#aab9f2", "#dddddd",
        "#f2a98b", "#d95533", "#b40426",
    ],
    "rdbu": [
        "#053061", "#2166ac", "#92c5de", "#f7f7f7",
        "#f4a582", "#d6604d", "#67001f",
    ],
    # ── Spectral (rainbow — avoid for quantitative data) ──────────────────
    "spectral": [
        "#9e0142", "#d53e4f", "#f46d43", "#fdae61", "#fee090",
        "#ffffbf", "#e6f598", "#abdda4", "#66c2a5", "#3288bd", "#5e4fa2",
    ],
    # ── Grayscale ─────────────────────────────────────────────────────────
    "greys": ["#ffffff", "#bdbdbd", "#636363", "#000000"],
}


def list_colormaps() -> list[str]:
    """Return names of all built-in colormaps."""
    return sorted(_MAPS.keys())


def get_colormap(name: str) -> list[str]:
    """
    Return the hex color stops for a named colormap.

    Args:
        name: Colormap name (case-insensitive).

    Raises:
        ValueError: If the name is not recognised.
    """
    key = name.lower()
    if key not in _MAPS:
        raise ValueError(
            f"Unknown colormap '{name}'. "
            f"Available: {', '.join(sorted(_MAPS))}."
        )
    return _MAPS[key]


# ---------------------------------------------------------------------------
# Color interpolation
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def apply_colormap(value: float, cmap: str | list[str] = "viridis") -> str:
    """
    Map a scalar in ``[0, 1]`` to a hex color string.

    Args:
        value: Normalised value between 0 and 1.
        cmap:  Colormap name or a custom list of hex stops.

    Returns:
        Hex color string (e.g. ``"#3b528b"``).
    """
    stops = cmap if isinstance(cmap, list) else get_colormap(cmap)
    value = max(0.0, min(1.0, float(value)))

    n = len(stops) - 1
    lo = min(int(value * n), n - 1)
    hi = lo + 1
    t  = value * n - lo

    r1, g1, b1 = _hex_to_rgb(stops[lo])
    r2, g2, b2 = _hex_to_rgb(stops[hi])

    return _rgb_to_hex(
        r1 + t * (r2 - r1),
        g1 + t * (g2 - g1),
        b1 + t * (b2 - b1),
    )


def colormap_colors(cmap: str, n: int) -> list[str]:
    """
    Sample ``n`` evenly-spaced colors from a colormap.

    Args:
        cmap: Colormap name.
        n:    Number of colors to return.

    Returns:
        List of hex color strings.
    """
    if n <= 1:
        return [apply_colormap(0.5, cmap)]
    return [apply_colormap(i / (n - 1), cmap) for i in range(n)]


# ---------------------------------------------------------------------------
# Colorbar SVG generator
# ---------------------------------------------------------------------------

def render_colorbar_svg(
    cmap: str | list[str],
    vmin: float,
    vmax: float,
    x: float,
    y: float,
    width: float,
    height: float,
    font: str = "sans-serif",
    text_color: str = "#000",
    steps: int = 24,
) -> str:
    """
    Generate an SVG colorbar strip with min/max labels.

    Args:
        cmap:       Colormap name or stops list.
        vmin, vmax: Data range.
        x, y:       Top-left corner of the bar in SVG units.
        width:      Width of the color strip.
        height:     Height of the color strip.
        font:       Font family for labels.
        text_color: Label fill color.
        steps:      Number of gradient rectangles.

    Returns:
        SVG markup string.
    """
    from .utils import _format_tick, svg_escape

    elements: list[str] = []
    step_h = height / steps

    for k in range(steps):
        norm  = 1 - k / (steps - 1)   # top = high value
        color = apply_colormap(norm, cmap)
        ry    = y + k * step_h
        elements.append(
            f'<rect x="{x}" y="{ry}" width="{width}" '
            f'height="{step_h + 0.5}" fill="{color}"/>'
        )

    # Border
    elements.append(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'fill="none" stroke="{text_color}" stroke-width="0.5" opacity="0.4"/>'
    )

    # Labels
    elements.append(
        f'<text x="{x + width + 4}" y="{y + 8}" '
        f'font-size="10" font-family="{font}" fill="{text_color}">'
        f'{svg_escape(_format_tick(vmax))}</text>'
    )
    elements.append(
        f'<text x="{x + width + 4}" y="{y + height}" '
        f'font-size="10" font-family="{font}" fill="{text_color}">'
        f'{svg_escape(_format_tick(vmin))}</text>'
    )

    return "\n".join(elements)
