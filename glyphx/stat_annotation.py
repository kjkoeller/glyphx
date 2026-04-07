"""
GlyphX Statistical Annotation layer.

Draw significance brackets between groups on bar, box, or violin charts::

    from glyphx import Figure
    from glyphx.series import BarSeries
    from glyphx.stat_annotation import StatAnnotation

    fig = Figure(auto_display=False)
    fig.add(BarSeries(["Control","Drug A","Drug B"], [45, 72, 68]))
    fig.add_stat_annotation("Control", "Drug A", p_value=0.002)
    fig.add_stat_annotation("Control", "Drug B", p_value=0.04)
    fig.show()

Works with both numeric and categorical X axes.
"""
from __future__ import annotations

from typing import Any

from .utils import svg_escape


# ---------------------------------------------------------------------------
# p-value → significance label
# ---------------------------------------------------------------------------

def pvalue_to_label(p: float, style: str = "stars") -> str:
    """
    Convert a p-value to a display label.

    Args:
        p:     The p-value (0–1).
        style: ``"stars"`` (default) or ``"numeric"``.

    Returns:
        ``"***"``, ``"**"``, ``"*"``, ``"ns"`` — or the formatted number.
    """
    if style == "numeric":
        if p < 0.001:
            return f"p={p:.2e}"
        return f"p={p:.3f}"

    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


# ---------------------------------------------------------------------------
# Annotation class
# ---------------------------------------------------------------------------

class StatAnnotation:
    """
    Significance bracket drawn between two groups on a chart.

    Attributes:
        x1:         First group label or numeric X value.
        x2:         Second group label or numeric X value.
        p_value:    The p-value for the test between the two groups.
        label:      Override text (defaults to significance stars).
        style:      ``"stars"`` or ``"numeric"``.
        color:      Line and text color.
        line_width: Bracket stroke width.
        tip_len:    Vertical tick length at each bracket end.
        y_offset:   Extra upward pixel shift (stacks multiple brackets).
    """

    def __init__(
        self,
        x1: Any,
        x2: Any,
        p_value: float = 0.05,
        label: str | None = None,
        style: str = "stars",
        color: str = "#222",
        line_width: float = 1.5,
        tip_len: float = 8.0,
        y_offset: float = 0.0,
    ) -> None:
        self.x1         = x1
        self.x2         = x2
        self.p_value    = p_value
        self.label      = label or pvalue_to_label(p_value, style)
        self.color      = color
        self.line_width = line_width
        self.tip_len    = tip_len
        self.y_offset   = y_offset

    def to_svg(self, ax: Any) -> str:
        """
        Render the bracket into SVG.

        Args:
            ax: A finalised :class:`~glyphx.layout.Axes` instance.

        Returns:
            SVG markup string, or empty string if the axes have no scale.
        """
        if ax.scale_x is None or ax.scale_y is None:
            return ""

        # ── Resolve x positions ───────────────────────────────────────────
        def resolve_x(val: Any) -> float:
            # Categorical lookup
            if isinstance(val, str):
                for s in ax.series:
                    cats = getattr(s, "_x_categories", None)
                    num  = getattr(s, "_numeric_x", None)
                    if cats and num:
                        for cat, nx in zip(cats, num):
                            if str(cat) == str(val):
                                return ax.scale_x(nx)
            return ax.scale_x(float(val))

        try:
            px1 = resolve_x(self.x1)
            px2 = resolve_x(self.x2)
        except (TypeError, ValueError):
            return ""

        # ── Bracket y position: just above the tallest bar / data point ───
        y_top_data = ax._y_domain[1] if ax._y_domain else 0
        base_py    = ax.scale_y(y_top_data) - 16 - self.y_offset
        tip_py     = base_py + self.tip_len

        mid_x = (px1 + px2) / 2
        lbl   = svg_escape(self.label)
        c     = self.color
        lw    = self.line_width

        # ── Font size: larger for stars, smaller for numeric ─────────────
        font_size = 16 if len(self.label) <= 3 else 11

        return "\n".join([
            # Left vertical tick
            f'<line x1="{px1}" x2="{px1}" y1="{tip_py}" y2="{base_py}" '
            f'stroke="{c}" stroke-width="{lw}"/>',
            # Horizontal bar
            f'<line x1="{px1}" x2="{px2}" y1="{base_py}" y2="{base_py}" '
            f'stroke="{c}" stroke-width="{lw}"/>',
            # Right vertical tick
            f'<line x1="{px2}" x2="{px2}" y1="{base_py}" y2="{tip_py}" '
            f'stroke="{c}" stroke-width="{lw}"/>',
            # Label
            f'<text x="{mid_x}" y="{base_py - 4}" text-anchor="middle" '
            f'font-size="{font_size}" fill="{c}">{lbl}</text>',
        ])
