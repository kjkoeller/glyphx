"""
GlyphX Accessibility helpers.

Generates plain-English alt text for SVG charts and provides
utilities for injecting ARIA attributes into rendered SVGs.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .figure import Figure


# Map class name → human-readable kind
_KIND_NAMES: dict[str, str] = {
    "lineseries":       "line",
    "barseries":        "bar",
    "scatterseries":    "scatter",
    "pieseries":        "pie",
    "donutseries":      "donut",
    "histogramseries":  "histogram",
    "boxplotseries":    "box plot",
    "heatmapseries":    "heatmap",
}


def generate_alt_text(fig: Figure) -> str:
    """
    Generate a plain-English description of a Figure for screen readers.

    The description covers chart type, title, axis labels, series count,
    data ranges, and notable values (min / max).

    Args:
        fig: A GlyphX :class:`Figure` instance.

    Returns:
        A human-readable string suitable for ``aria-label`` or ``<desc>``.
    """
    parts: list[str] = []

    # ── Chart kind ──────────────────────────────────────────────────────
    kinds: list[str] = []
    for s, _ in fig.series:
        raw  = type(s).__name__.lower()
        kind = _KIND_NAMES.get(raw, raw.replace("series", ""))
        kinds.append(kind)

    primary_kind = kinds[0] if kinds else "chart"

    # ── Title ────────────────────────────────────────────────────────────
    if fig.title:
        parts.append(f"{primary_kind.capitalize()} chart titled \"{fig.title}\".")
    else:
        parts.append(f"{primary_kind.capitalize()} chart.")

    # ── Axis labels ──────────────────────────────────────────────────────
    if getattr(fig.axes, "xlabel", None):
        parts.append(f"X axis: {fig.axes.xlabel}.")
    if getattr(fig.axes, "ylabel", None):
        parts.append(f"Y axis: {fig.axes.ylabel}.")

    # ── Series descriptions ───────────────────────────────────────────────
    for s, _ in fig.series:
        x_vals = getattr(s, "x", None)
        y_vals = getattr(s, "y", None)

        # Pie / donut special case
        values = getattr(s, "values", None)
        labels = getattr(s, "labels", None)
        if values is not None and labels is not None:
            total   = sum(values)
            biggest = max(zip(values, labels), key=lambda p: p[0])
            parts.append(
                f"Contains {len(values)} slices. "
                f"Largest: {biggest[1]} ({biggest[0]:.3g} of {total:.3g})."
            )
            continue

        if not x_vals or not y_vals:
            continue

        lbl = f'Series "{s.label}"' if getattr(s, "label", None) else "Series"

        # Count
        n = len(x_vals)
        parts.append(f"{lbl}: {n} data point{'s' if n != 1 else ''}.")

        # Range (numeric y only)
        try:
            numeric_y = [float(v) for v in y_vals]
            numeric_x = list(x_vals)
            mn  = min(numeric_y)
            mx  = max(numeric_y)
            # Use enumerate to find indices safely
            mn_idx = next(i for i, v in enumerate(numeric_y) if v == mn)
            mx_idx = next(i for i, v in enumerate(numeric_y) if v == mx)

            mn_x = numeric_x[mn_idx] if mn_idx < len(numeric_x) else "?"
            mx_x = numeric_x[mx_idx] if mx_idx < len(numeric_x) else "?"

            parts.append(
                f"Ranges from {mn:.3g} (at {mn_x}) "
                f"to {mx:.3g} (at {mx_x})."
            )
        except (TypeError, ValueError, StopIteration):
            pass

    return " ".join(parts) if parts else "Interactive chart."


def inject_aria(svg: str, title: str, desc: str, chart_id: str) -> str:
    """
    Inject ARIA attributes and landmark elements into a rendered SVG string.

    Changes made:
    - Adds ``role="img"`` and ``aria-labelledby`` to the root ``<svg>``
    - Prepends ``<title>`` and ``<desc>`` as the first children of the SVG
    - Adds ``tabindex="0"`` and ``role="graphics-symbol"`` to every
      ``.glyphx-point`` element for keyboard navigation

    Args:
        svg:       Raw SVG string from ``Figure.render_svg()``.
        title:     Short label (goes in ``<title>``).
        desc:      Longer description (goes in ``<desc>``).
        chart_id:  Unique chart ID already present on the ``<svg>`` element.

    Returns:
        The accessibility-enhanced SVG string.
    """
    from .utils import svg_escape

    title_id = f"{chart_id}-title"
    desc_id  = f"{chart_id}-desc"

    # ── 1. Add role + aria-labelledby to the opening <svg ...> tag ───────
    svg = re.sub(
        r"(<svg\b[^>]*)(>)",
        lambda m: (
            m.group(1)
            + f' role="img" focusable="false"'
            + f' aria-labelledby="{title_id} {desc_id}"'
            + m.group(2)
        ),
        svg,
        count=1,
    )

    # ── 2. Inject <title> and <desc> right after the opening <svg> tag ───
    landmark = (
        f'<title id="{title_id}">{svg_escape(title)}</title>'
        f'<desc id="{desc_id}">{svg_escape(desc)}</desc>'
    )
    svg = re.sub(r"(<svg\b[^>]*>)", r"\1" + landmark, svg, count=1)

    # ── 3. Add tabindex + role to every interactive point ─────────────────
    svg = re.sub(
        r'class="glyphx-point',
        'tabindex="0" role="graphics-symbol" class="glyphx-point',
        svg,
    )

    return svg
