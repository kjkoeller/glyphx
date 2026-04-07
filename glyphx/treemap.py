"""
GlyphX Treemap chart using the Squarified layout algorithm.

Treemaps show hierarchical data as nested rectangles, area-proportional
to value.  The squarification algorithm by Bruls et al. minimises aspect
ratios so rectangles are as square as possible.

    from glyphx import Figure
    from glyphx.treemap import TreemapSeries

    fig = Figure(width=700, height=500, auto_display=False)
    fig.add(TreemapSeries(
        labels=["Sales","R&D","Marketing","Operations","Legal"],
        values=[4200, 1800, 1200, 900, 400],
    ))
    fig.show()
"""
from __future__ import annotations

import math

from .colormaps import colormap_colors, apply_colormap
from .utils import svg_escape, _format_tick


# ---------------------------------------------------------------------------
# Squarification algorithm
# ---------------------------------------------------------------------------

def _worst_ratio(row: list[float], side: float) -> float:
    """Worst (max) aspect ratio in a current candidate row."""
    s = sum(row)
    if s == 0 or side == 0:
        return float("inf")
    return max(
        max(side * side * r / (s * s), (s * s) / (side * side * r))
        for r in row
    )


def _squarify(values: list[float], x: float, y: float,
              w: float, h: float) -> list[tuple[float, float, float, float]]:
    """
    Squarified treemap layout.

    Returns list of (x, y, w, h) rectangles in the same order as *values*.
    """
    if not values:
        return []

    if len(values) == 1 or w <= 0 or h <= 0:
        return [(x, y, w, h)]

    # Normalise values to area
    total    = sum(values)
    area     = w * h
    normed   = [v / total * area for v in values]

    rects: list[tuple[float, float, float, float]] = []
    _squarify_normed(normed, x, y, w, h, rects)
    return rects


def _squarify_normed(
    normed: list[float],
    x: float, y: float, w: float, h: float,
    rects: list[tuple[float, float, float, float]],
) -> None:
    """Recursive squarification on normalised areas."""
    if not normed:
        return
    if len(normed) == 1:
        rects.append((x, y, w, h))
        return

    side      = min(w, h)
    current   = []
    remaining = list(normed)

    while remaining:
        candidate = current + [remaining[0]]
        if not current or _worst_ratio(candidate, side) <= _worst_ratio(current, side):
            current.append(remaining.pop(0))
        else:
            break

    # Guard: ensure at least one item was consumed
    if not current:
        current.append(remaining.pop(0))

    row_sum = sum(current)

    if w <= h:
        # Stack along top, advance y
        row_h = row_sum / w
        cx    = x
        for val in current:
            cw = val / row_sum * w
            rects.append((cx, y, cw, row_h))
            cx += cw
        _squarify_normed(remaining, x, y + row_h, w, h - row_h, rects)
    else:
        # Stack along left, advance x
        row_w = row_sum / h
        cy    = y
        for val in current:
            ch = val / row_sum * h
            rects.append((x, cy, row_w, ch))
            cy += ch
        _squarify_normed(remaining, x + row_w, y, w - row_w, h, rects)


# ---------------------------------------------------------------------------
# Series class
# ---------------------------------------------------------------------------

class TreemapSeries:
    """
    Squarified treemap.

    Args:
        labels:         Category labels.
        values:         Numeric values (determines rectangle area).
        colors:         Per-label colors; if ``None``, uses ``cmap``.
        cmap:           Colormap name used when ``colors`` is not supplied.
        padding:        Gap between rectangles in pixels.
        show_values:    Overlay the numeric value in each rectangle.
        min_font:       Minimum font size; hides label if rect too small.
        label:          Legend label (unused but kept for API consistency).
    """

    def __init__(
        self,
        labels: list[str],
        values: list[float],
        colors: list[str] | None = None,
        cmap: str = "viridis",
        padding: float = 2.0,
        show_values: bool = True,
        min_font: int = 9,
        label: str | None = None,
    ) -> None:
        if len(labels) != len(values):
            raise ValueError(
                f"labels and values must be the same length "
                f"({len(labels)} vs {len(values)})."
            )

        # Sort descending (squarify works best on sorted input)
        paired        = sorted(zip(values, labels), reverse=True)
        self.values   = [v for v, _ in paired]
        self.labels   = [l for _, l in paired]
        self.cmap     = cmap
        self.padding  = padding
        self.show_values = show_values
        self.min_font = min_font
        self.label    = label
        self.css_class = f"series-{id(self) % 100000}"

        n = len(self.labels)
        if colors:
            # Re-sort colors to match sorted order
            orig_order = {l: c for l, c in zip([l for _, l in zip(values, labels)], colors or [])}
            self.colors = [orig_order.get(l, apply_colormap(0.5, cmap)) for l in self.labels]
        else:
            total = sum(self.values)
            self.colors = [apply_colormap(v / total, cmap) for v in self.values]

        # x/y stubs (treemap is axis-free)
        self.x = None
        self.y = None

    def to_svg(self, ax: object = None) -> str:   # type: ignore[override]
        """Render the treemap into SVG rectangles."""
        if ax is None:
            # Fallback dimensions
            plot_x, plot_y, plot_w, plot_h = 50, 50, 540, 380
            font   = "sans-serif"
            tc     = "#fff"
        else:
            pad    = getattr(ax, "padding", 50)
            plot_x = float(pad)
            plot_y = float(pad)
            plot_w = float(ax.width  - 2 * pad)   # type: ignore[union-attr]
            plot_h = float(ax.height - 2 * pad)   # type: ignore[union-attr]
            theme  = getattr(ax, "theme", {})
            font   = theme.get("font", "sans-serif")
            tc     = "#fff"   # white text looks good on colored rects

        rects    = _squarify(self.values, plot_x, plot_y, plot_w, plot_h)
        total    = sum(self.values)
        elements: list[str] = []

        for (rx, ry, rw, rh), lbl, val, color in zip(
            rects, self.labels, self.values, self.colors
        ):
            # Apply padding
            p      = self.padding
            rx, ry = rx + p, ry + p
            rw, rh = rw - 2 * p, rh - 2 * p

            if rw <= 0 or rh <= 0:
                continue

            pct     = val / total * 100
            tooltip = (
                f'data-label="{svg_escape(lbl)}" '
                f'data-value="{svg_escape(_format_tick(val))}"'
            )
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{rx:.1f}" y="{ry:.1f}" '
                f'width="{rw:.1f}" height="{rh:.1f}" '
                f'fill="{color}" rx="3" {tooltip}/>'
            )

            # Label — only if rect is large enough
            font_size = min(14, max(self.min_font, int(rh * 0.22)))
            if rw > 30 and rh > font_size * 2:
                elements.append(
                    f'<text x="{rx + rw / 2:.1f}" y="{ry + rh / 2:.1f}" '
                    f'text-anchor="middle" dominant-baseline="middle" '
                    f'font-size="{font_size}" font-family="{font}" '
                    f'fill="{tc}" font-weight="600">'
                    f'{svg_escape(lbl)}</text>'
                )
                if self.show_values and rh > font_size * 3.5:
                    val_size = max(self.min_font, font_size - 2)
                    elements.append(
                        f'<text x="{rx + rw / 2:.1f}" '
                        f'y="{ry + rh / 2 + font_size:.1f}" '
                        f'text-anchor="middle" font-size="{val_size}" '
                        f'font-family="{font}" fill="{tc}" opacity="0.85">'
                        f'{svg_escape(_format_tick(val))} ({pct:.1f}%)</text>'
                    )

        return "\n".join(elements)
