"""
GlyphX series classes.

Each series class renders a specific chart type to SVG.
All series inherit from BaseSeries and implement ``to_svg(ax)``.
"""

import math
import numpy as np

from .themes import themes as _themes
from .utils import describe_arc, svg_escape, _format_tick


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseSeries:
    """
    Base class for all GlyphX series.

    Attributes:
        x (list): X-axis values.
        y (list): Y-axis values (``None`` for chart types that don't use axes).
        color (str): Primary color for this series.
        label (str | None): Legend / tooltip label.
        title (str | None): Per-series subtitle drawn above the chart area.
        css_class (str): CSS class applied to interactive SVG elements.
    """

    def __init__(self, x, y=None, color=None, label=None, title=None):
        self.x     = x
        self.y     = y
        self.color = color or "#1f77b4"
        self.label = label
        self.title = title
        self.css_class = f"series-{id(self) % 100000}"

    def __repr__(self) -> str:
        n     = len(self.x) if self.x else 0
        label = f" label={self.label!r}" if self.label else ""
        rng   = ""
        if self.x and n > 0:
            rng = f" x=[{self.x[0]}..{self.x[-1]}] ({n} pts)"
        return f"<{self.__class__.__name__}{label}{rng} color={self.color}>"


# ---------------------------------------------------------------------------
# Line chart
# ---------------------------------------------------------------------------

class LineSeries(BaseSeries):
    """
    Line chart series with optional error bars.

    Args:
        x (list): X values.
        y (list): Y values.
        color (str | None): Line/point color.
        label (str | None): Legend label.
        linestyle (str): ``"solid"``, ``"dashed"``, ``"dotted"``, or ``"longdash"``.
        width (int): Stroke width in pixels.
        title (str | None): Chart subtitle.
        yerr (list | None): Symmetric Y error bar values (same length as y).
        xerr (list | None): Symmetric X error bar values (same length as x).
    """

    _DASH = {
        "solid":    "",
        "dashed":   "6,3",
        "dotted":   "2,2",
        "longdash": "10,5",
    }

    def __init__(
        self,
        x,
        y,
        color=None,
        label=None,
        legend=None,
        linestyle="solid",
        width=2,
        title=None,
        yerr=None,
        xerr=None,
    ):
        super().__init__(x, y, color, label=label or legend, title=title)
        self.linestyle = linestyle
        self.width     = width
        self.yerr      = yerr
        self.xerr      = xerr

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        dash    = self._DASH.get(self.linestyle, "")

        # Use numeric X mapping if categorical was detected
        x_vals = getattr(self, "_numeric_x", self.x)

        elements = []

        if self.title:
            mid_x = (ax.padding + ax.width - ax.padding) // 2
            elements.append(
                f'<text x="{mid_x}" y="{ax.padding - 20}" text-anchor="middle" '
                f'font-size="16" font-family="{ax.theme.get("font", "sans-serif")}" '
                f'fill="{ax.theme.get("text_color", "#000")}">'
                f'{svg_escape(self.title)}</text>'
            )

        if self.linestyle == "step":
            step_pts = []
            prev_py = None
            for i, (x, y) in enumerate(zip(x_vals, self.y)):
                px, py = ax.scale_x(x), scale_y(y)
                if i == 0:
                    step_pts.append(f"{px},{py}")
                else:
                    step_pts.append(f"{px},{prev_py}")
                    step_pts.append(f"{px},{py}")
                prev_py = py
            points = " ".join(step_pts)
        else:
            points = " ".join(f"{ax.scale_x(x)},{scale_y(y)}" for x, y in zip(x_vals, self.y))

        elements.append(
            f'<polyline class="{self.css_class}" fill="none" stroke="{self.color}" '
            f'stroke-width="{self.width}" stroke-dasharray="{dash}" points="{points}"/>'
        )

        # Data points with tooltips
        for x, y in zip(x_vals, self.y):
            elements.append(
                f'<circle class="glyphx-point {self.css_class}" '
                f'cx="{ax.scale_x(x)}" cy="{scale_y(y)}" r="4" fill="{self.color}" '
                f'data-x="{svg_escape(str(x))}" data-y="{svg_escape(str(y))}" '
                f'data-label="{svg_escape(self.label or "")}"/>'
            )

        # Y error bars
        if self.yerr is not None:
            cap = 5
            for x, y, err in zip(x_vals, self.y, self.yerr):
                px, py = ax.scale_x(x), scale_y(y)
                py_lo  = scale_y(y - err)
                py_hi  = scale_y(y + err)
                elements.append(
                    f'<line x1="{px}" x2="{px}" y1="{py_lo}" y2="{py_hi}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )
                elements.append(
                    f'<line x1="{px - cap}" x2="{px + cap}" y1="{py_lo}" y2="{py_lo}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )
                elements.append(
                    f'<line x1="{px - cap}" x2="{px + cap}" y1="{py_hi}" y2="{py_hi}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )

        # X error bars
        if self.xerr is not None:
            cap = 5
            for x, y, err in zip(x_vals, self.y, self.xerr):
                px    = ax.scale_x(x)
                py    = scale_y(y)
                px_lo = ax.scale_x(x - err)
                px_hi = ax.scale_x(x + err)
                elements.append(
                    f'<line x1="{px_lo}" x2="{px_hi}" y1="{py}" y2="{py}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )
                elements.append(
                    f'<line x1="{px_lo}" x2="{px_lo}" y1="{py - cap}" y2="{py + cap}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )
                elements.append(
                    f'<line x1="{px_hi}" x2="{px_hi}" y1="{py - cap}" y2="{py + cap}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )

        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Bar chart
# ---------------------------------------------------------------------------

class BarSeries(BaseSeries):
    """
    Bar chart series with optional error bars.

    Args:
        x: X-axis labels/values.
        y: Bar heights.
        color: Fill color.
        label: Legend label.
        bar_width (float): Fraction of available slot width (0–1).
        title: Per-series subtitle.
        yerr: Symmetric Y error values.
    """

    def __init__(self, x, y, color=None, label=None, legend=None,
                 bar_width=0.8, title=None, yerr=None):
        super().__init__(x, y, color, label=label or legend, title=title)
        self.bar_width = bar_width
        self.yerr      = yerr

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        x_vals  = getattr(self, "_numeric_x", self.x)
        elements = []

        if not x_vals:
            return ""

        # Each categorical slot is exactly 1 unit wide in our coordinate system.
        # Using scale_x(start+1) - scale_x(start) gives the correct pixel width
        # per slot regardless of how many categories this particular series owns.
        x_start  = ax._x_domain[0]
        px_step  = ax.scale_x(x_start + 1) - ax.scale_x(x_start)
        px_width = px_step * self.bar_width

        y_domain = ax._y2_domain if use_y2 else ax._y_domain
        y0       = scale_y(min(0, y_domain[0]))

        for i, (x, y) in enumerate(zip(x_vals, self.y)):
            cx  = ax.scale_x(x)
            cy  = scale_y(y)
            h   = abs(cy - y0)
            top = min(cy, y0)

            orig_x = self.x[i] if hasattr(self.x[0], "__len__") or isinstance(self.x[0], str) else x
            tooltip = (
                f'data-x="{svg_escape(str(orig_x))}" '
                f'data-y="{svg_escape(str(y))}" '
                f'data-label="{svg_escape(self.label or "")}"'
            )
            bar_color = (
                self.color[i % len(self.color)]
                if isinstance(self.color, list)
                else self.color
            )
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{cx - px_width / 2}" y="{top}" width="{px_width}" height="{h}" '
                f'fill="{bar_color}" stroke="#00000033" {tooltip}/>' 
            )

            # Y error bars
            if self.yerr is not None:
                err = self.yerr[i]
                cap = 5
                py_lo = scale_y(y - err)
                py_hi = scale_y(y + err)
                elements.append(
                    f'<line x1="{cx}" x2="{cx}" y1="{py_lo}" y2="{py_hi}" '
                    f'stroke="#333" stroke-width="1.5"/>'
                )
                elements.append(
                    f'<line x1="{cx - cap}" x2="{cx + cap}" y1="{py_lo}" y2="{py_lo}" '
                    f'stroke="#333" stroke-width="1.5"/>'
                )
                elements.append(
                    f'<line x1="{cx - cap}" x2="{cx + cap}" y1="{py_hi}" y2="{py_hi}" '
                    f'stroke="#333" stroke-width="1.5"/>'
                )

        if self.title:
            elements.append(
                f'<text x="{ax.width // 2}" y="20" text-anchor="middle" font-size="16" '
                f'fill="{ax.theme.get("text_color", "#000")}" '
                f'font-family="{ax.theme.get("font", "sans-serif")}">'
                f'{svg_escape(self.title)}</text>'
            )

        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Scatter chart
# ---------------------------------------------------------------------------

class ScatterSeries(BaseSeries):
    """
    Scatter plot with configurable marker type, size, and continuous color encoding.

    Args:
        marker (str): ``"circle"`` or ``"square"``.
        size (int):   Marker radius / half-width in pixels.
        c (list | None): Per-point values for color encoding.  When set,
                         each point's color is determined by mapping this
                         value through ``cmap``.  Overrides ``color``.
        cmap (str):   Colormap name (default: ``"viridis"``).
                      See :func:`~glyphx.colormaps.list_colormaps` for options.
    """

    def __init__(self, x, y, color=None, label=None, legend=None,
                 size=5, marker="circle", title=None,
                 c=None, cmap="viridis"):
        super().__init__(x, y, color, label=label or legend, title=title)
        self.size   = size
        self.marker = marker
        self.c      = c       # per-point color values
        self.cmap   = cmap    # colormap name

    def _point_color(self, idx: int, total: int) -> str:
        """Return per-point color via colormap encoding or flat color."""
        if self.c is not None and idx < len(self.c):
            from .colormaps import apply_colormap
            import numpy as np
            c_arr = np.asarray(self.c, dtype=float)
            lo, hi = c_arr.min(), c_arr.max()
            norm = (c_arr[idx] - lo) / (hi - lo) if hi > lo else 0.5
            return apply_colormap(float(norm), self.cmap)
        return self.color

    def to_svg(self, ax, use_y2=False):
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y
        x_vals   = getattr(self, "_numeric_x", self.x)
        elements = []

        for i, (orig_x, x, y) in enumerate(zip(self.x, x_vals, self.y)):
            px      = ax.scale_x(x)
            py      = scale_y(y)
            color   = self._point_color(i, len(self.x))
            tooltip = (
                f'data-x="{svg_escape(str(orig_x))}" '
                f'data-y="{svg_escape(str(y))}" '
                f'data-label="{svg_escape(self.label or "")}"'
            )
            if self.marker == "square":
                elements.append(
                    f'<rect class="glyphx-point {self.css_class}" '
                    f'x="{px - self.size / 2}" y="{py - self.size / 2}" '
                    f'width="{self.size}" height="{self.size}" '
                    f'fill="{color}" {tooltip}/>'
                )
            else:
                elements.append(
                    f'<circle class="glyphx-point {self.css_class}" '
                    f'cx="{px}" cy="{py}" r="{self.size}" '
                    f'fill="{color}" {tooltip}/>'
                )

        # Colorbar for color-encoded scatter
        if self.c is not None:
            import numpy as np
            from .colormaps import render_colorbar_svg
            c_arr = np.asarray(self.c, dtype=float)
            elements.append(render_colorbar_svg(
                cmap=self.cmap,
                vmin=float(c_arr.min()),
                vmax=float(c_arr.max()),
                x=ax.width - 30,
                y=ax.padding,
                width=12,
                height=ax.height - 2 * ax.padding,
                font=ax.theme.get("font", "sans-serif"),
                text_color=ax.theme.get("text_color", "#000"),
            ))

        if self.title:
            elements.append(
                f'<text x="{ax.width // 2}" y="20" text-anchor="middle" font-size="16" '
                f'fill="{ax.theme.get("text_color", "#000")}" '
                f'font-family="{ax.theme.get("font", "sans-serif")}">'
                f'{svg_escape(self.title)}</text>'
            )

        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Pie chart
# ---------------------------------------------------------------------------

_DEFAULT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
]


class PieSeries(BaseSeries):
    """
    Pie chart series.

    Args:
        values (list): Numeric slice sizes.
        labels (list | None): Label for each slice.
        colors (list | None): Color per slice (cycles if fewer than slices).
        title (str | None): Chart title rendered above the pie.
        label_position (str): ``"outside"`` (default) or ``"inside"``.
        radius (float): Explicit radius in pixels; auto-computed if None.
    """

    def __init__(self, values, labels=None, colors=None, title=None,
                 label_position="outside", radius=None):
        # BaseSeries requires x; pie charts are axis-free.
        super().__init__(x=None, y=None, color=None, title=title)
        self.values         = values
        self.labels         = labels
        # BUG FIX: was `self.colors = self.colors or [...]` — self.colors didn't exist yet
        self.colors         = colors or _DEFAULT_COLORS
        self.label_position = label_position
        self.radius         = radius

    def to_svg(self, ax=None):
        elements = []
        total    = sum(self.values)
        if total == 0:
            return ""

        cx = (ax.width  // 2) if ax else 320
        cy = (ax.height // 2) if ax else 240
        r  = self.radius or min(cx, cy) * 0.55

        if self.title and ax:
            elements.append(
                f'<text x="{cx}" y="20" text-anchor="middle" font-size="16" '
                f'fill="{ax.theme.get("text_color", "#000")}" '
                f'font-family="{ax.theme.get("font", "sans-serif")}">'
                f'{svg_escape(self.title)}</text>'
            )

        angle_start = 0
        for i, v in enumerate(self.values):
            angle_end = angle_start + (v / total) * 360
            mid_angle = (angle_start + angle_end) / 2
            rad       = math.radians(mid_angle)

            path    = describe_arc(cx, cy, r, angle_start, angle_end)
            color   = self.colors[i % len(self.colors)]
            tooltip = ""
            if self.labels:
                tooltip = (
                    f'data-label="{svg_escape(str(self.labels[i]))}" '
                    f'data-value="{v}"'
                )

            elements.append(
                f'<path class="glyphx-point {self.css_class}" '
                f'd="{path}" fill="{color}" stroke="#fff" stroke-width="1" {tooltip}/>'
            )

            if self.labels:
                base_dist    = r * 0.15
                dynamic_dist = base_dist + r * 0.2 * abs(math.sin(rad))
                elbow_x      = cx + (r + dynamic_dist) * math.cos(rad)
                elbow_y      = cy + (r + dynamic_dist) * math.sin(rad)
                shift        = 30
                label_x      = elbow_x + (shift if math.cos(rad) >= 0 else -shift)
                label_y      = elbow_y

                start_x = cx + r * math.cos(rad)
                start_y = cy + r * math.sin(rad)

                elements.append(
                    f'<line x1="{start_x}" y1="{start_y}" x2="{elbow_x}" y2="{elbow_y}" '
                    f'stroke="#666" stroke-width="1"/>'
                )
                elements.append(
                    f'<line x1="{elbow_x}" y1="{elbow_y}" x2="{label_x}" y2="{label_y}" '
                    f'stroke="#666" stroke-width="1"/>'
                )
                anchor = "start" if math.cos(rad) >= 0 else "end"
                elements.append(
                    f'<text x="{label_x}" y="{label_y + 4}" text-anchor="{anchor}" '
                    f'font-size="12" font-family="sans-serif" fill="#000">'
                    f'{svg_escape(str(self.labels[i]))}</text>'
                )

            angle_start = angle_end

        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Donut chart
# ---------------------------------------------------------------------------

class DonutSeries(BaseSeries):
    """
    Donut (annular pie) chart series.

    Args:
        values (list): Numeric slice sizes.
        labels (list | None): Label per slice; auto-generated if None.
        colors (list | None): Color per slice.
        show_labels (bool): Draw callout labels outside the ring.
        hover_animate (bool): Add ``glyphx-point`` class for CSS hover.
        inner_radius_frac (float): Hole radius as fraction of outer radius.
    """

    def __init__(self, values, labels=None, colors=None,
                 show_labels=True, hover_animate=True, inner_radius_frac=0.5):
        # BUG FIX: super().__init__() was never called → self.label etc. missing
        super().__init__(x=None, y=None, color=None)
        self.values            = values
        self.labels            = labels or [str(i) for i in range(len(values))]
        self.colors            = colors or _DEFAULT_COLORS
        self.show_labels       = show_labels
        self.hover_animate     = hover_animate
        self.inner_radius_frac = inner_radius_frac

    def to_svg(self, ax=None):
        total = sum(self.values)
        if total == 0:
            return ""

        # BUG FIX: self.theme was never defined — use ax.theme or fallback
        bg_color = "#ffffff"
        if ax is not None and hasattr(ax, "theme"):
            bg_color = ax.theme.get("background", "#ffffff")

        cx         = (ax.width  // 2) if ax else 320
        cy         = (ax.height // 2) if ax else 240
        max_radius = min(cx, cy) - 40

        if self.show_labels:
            outer_radius = max_radius * (0.75 if any(len(l) > 10 for l in self.labels) else 0.9)
        else:
            outer_radius = max_radius

        inner_radius = outer_radius * self.inner_radius_frac

        elements    = []
        angle_start = 0
        slices      = []

        for v, label in zip(self.values, self.labels):
            span = (v / total) * 360
            slices.append((angle_start, angle_start + span, v, label))
            angle_start += span

        for idx, (a1, a2, v, label) in enumerate(slices):
            x1 = cx + outer_radius * math.cos(math.radians(a1))
            y1 = cy + outer_radius * math.sin(math.radians(a1))
            x2 = cx + outer_radius * math.cos(math.radians(a2))
            y2 = cy + outer_radius * math.sin(math.radians(a2))
            large_arc = 1 if a2 - a1 > 180 else 0

            path = (
                f"M {x1},{y1} "
                f"A {outer_radius},{outer_radius} 0 {large_arc},1 {x2},{y2} "
                f"L {cx},{cy} Z"
            )
            color_val    = self.colors[idx % len(self.colors)]
            hover_class  = f"glyphx-point {self.css_class}" if self.hover_animate else self.css_class

            elements.append(
                f'<path d="{path}" fill="{color_val}" class="{hover_class}" '
                f'data-label="{svg_escape(str(label))}" data-value="{v}"/>'
            )

            if self.show_labels:
                mid_angle = (a1 + a2) / 2
                lr        = outer_radius + 20
                lx = cx + lr * math.cos(math.radians(mid_angle))
                ly = cy + lr * math.sin(math.radians(mid_angle))
                lx0 = cx + outer_radius * math.cos(math.radians(mid_angle))
                ly0 = cy + outer_radius * math.sin(math.radians(mid_angle))
                elements.append(
                    f'<line x1="{lx0}" y1="{ly0}" x2="{lx}" y2="{ly}" stroke="#666"/>'
                )
                elements.append(
                    f'<text x="{lx}" y="{ly}" text-anchor="middle" '
                    f'font-size="11" font-family="sans-serif" fill="#000">'
                    f'{svg_escape(str(label))}</text>'
                )

        # Centre hole
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="{inner_radius}" fill="{bg_color}"/>'
        )

        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

class HistogramSeries(BaseSeries):
    """
    Frequency distribution histogram.

    Args:
        data (array-like): Raw numeric values.
        bins (int): Number of histogram bins.
        color: Bar fill color.
        label: Legend label.
    """

    def __init__(self, data, bins=10, color=None, label=None):
        hist, edges = np.histogram(data, bins=bins)
        x = [(edges[i] + edges[i + 1]) / 2 for i in range(len(hist))]
        y = hist.tolist()
        super().__init__(x, y, color or "#1f77b4", label)
        self.edges = edges

    def to_svg(self, ax, use_y2=False):
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y
        elements = []
        width    = (ax.scale_x(self.edges[1]) - ax.scale_x(self.edges[0])) * 0.95

        for x, y in zip(self.x, self.y):
            cx  = ax.scale_x(x)
            cy  = scale_y(y)
            y0  = scale_y(0)
            h   = abs(y0 - cy)
            top = min(y0, cy)
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{cx - width / 2}" y="{top}" width="{width}" height="{h}" '
                f'fill="{self.color}" stroke="#fff" '
                f'data-x="{x:.3g}" data-y="{y}" '
                f'data-label="{svg_escape(self.label or "")}"/>'
            )
        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Box plot
# ---------------------------------------------------------------------------

class BoxPlotSeries(BaseSeries):
    """
    Box-and-whisker plot.

    Supports a single array (one box) or a list of arrays (multiple boxes
    drawn at categorical X positions).

    Args:
        data (array-like or list of arrays): Input data.
        categories (list | None): Category labels for multiple boxes.
        color: Box fill color.
        label: Legend / tooltip label.
        box_width (int): Pixel width of each box.
    """

    def __init__(self, data, categories=None, color="#1f77b4",
                 label=None, box_width=20, width=None):
        # ``width`` kept for backward-compat; prefer box_width
        self.color      = color
        self.label      = label
        self.box_width  = width or box_width
        self.css_class  = f"series-{id(self) % 100000}"

        # Normalise: always store as list-of-arrays
        if isinstance(data[0], (list, np.ndarray)):
            self.datasets    = [np.asarray(d) for d in data]
            self.categories  = categories or [str(i) for i in range(len(data))]
        else:
            self.datasets   = [np.asarray(data)]
            self.categories = categories or [""]

        # BaseSeries x/y for domain computation
        all_vals  = np.concatenate(self.datasets)
        n         = len(self.datasets)
        positions = [i + 0.5 for i in range(n)]  # align with grid's i+0.5 label mapping
        super().__init__(
            x=positions,
            y=[float(all_vals.min()), float(all_vals.max())],
            color=color,
            label=label,
        )
        # Override y so domain covers full whisker range
        self.y = [float(all_vals.min()), float(all_vals.max())]

    def to_svg(self, ax, use_y2=False):
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y
        elements = []
        n        = len(self.datasets)

        for i, arr in enumerate(self.datasets):
            pos = i + 0.5   # 0-indexed half-slot, aligns with grid label positions
            cx  = ax.scale_x(pos)

            q1          = float(np.percentile(arr, 25))
            q2          = float(np.percentile(arr, 50))
            q3          = float(np.percentile(arr, 75))
            iqr         = q3 - q1
            whisker_lo  = float(max(arr.min(), q1 - 1.5 * iqr))
            whisker_hi  = float(min(arr.max(), q3 + 1.5 * iqr))
            outliers    = arr[(arr < whisker_lo) | (arr > whisker_hi)]

            hw = self.box_width / 2
            tooltip = (
                f'data-label="{svg_escape(str(self.categories[i]))}" '
                f'data-q1="{q1:.3g}" data-q2="{q2:.3g}" data-q3="{q3:.3g}"'
            )

            # Whiskers
            elements.append(
                f'<line x1="{cx}" x2="{cx}" '
                f'y1="{scale_y(whisker_lo)}" y2="{scale_y(q1)}" '
                f'stroke="{self.color}" stroke-width="1.5"/>'
            )
            elements.append(
                f'<line x1="{cx}" x2="{cx}" '
                f'y1="{scale_y(q3)}" y2="{scale_y(whisker_hi)}" '
                f'stroke="{self.color}" stroke-width="1.5"/>'
            )
            # Whisker caps
            for cap_y in (whisker_lo, whisker_hi):
                elements.append(
                    f'<line x1="{cx - hw}" x2="{cx + hw}" '
                    f'y1="{scale_y(cap_y)}" y2="{scale_y(cap_y)}" '
                    f'stroke="{self.color}" stroke-width="1.5"/>'
                )
            # IQR box
            box_top = min(scale_y(q1), scale_y(q3))
            box_h   = abs(scale_y(q3) - scale_y(q1))
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{cx - hw}" y="{box_top}" '
                f'width="{self.box_width}" height="{box_h}" '
                f'fill="{self.color}" fill-opacity="0.35" '
                f'stroke="{self.color}" stroke-width="1.5" {tooltip}/>'
            )
            # Median line
            elements.append(
                f'<line x1="{cx - hw}" x2="{cx + hw}" '
                f'y1="{scale_y(q2)}" y2="{scale_y(q2)}" '
                f'stroke="{self.color}" stroke-width="2.5"/>'
            )
            # Outlier dots
            for ov in outliers:
                elements.append(
                    f'<circle cx="{cx}" cy="{scale_y(float(ov))}" r="3" '
                    f'fill="none" stroke="{self.color}" stroke-width="1.5"/>'
                )
            # Category label below box — skip if _x_categories is set,
            # because render_grid() will draw the labels via the grid pass.
            if self.categories[i] and not getattr(self, "_x_categories", None):
                elements.append(
                    f'<text x="{cx}" y="{ax.height - ax.padding + 16}" '
                    f'text-anchor="middle" font-size="11" '
                    f'font-family="{ax.theme.get("font", "sans-serif")}" '
                    f'fill="{ax.theme.get("text_color", "#000")}">'
                    f'{svg_escape(str(self.categories[i]))}</text>'
                )

        return "\n".join(elements)


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

class HeatmapSeries(BaseSeries):
    """
    Heatmap for 2-D matrix data with a color-scale legend.

    Args:
        matrix (list[list[float]]): 2-D data grid (rows × cols).
        cmap (list[str] | None): Ordered list of hex colors (low → high).
        row_labels (list | None): Row labels shown on the Y-axis.
        col_labels (list | None): Column labels shown on the X-axis.
        show_values (bool): Render numeric value inside each cell.
    """

    def __init__(self, matrix, cmap=None, row_labels=None,
                 col_labels=None, show_values=False, **kwargs):
        self.matrix     = matrix
        self.cmap       = cmap or ["#fff7fb", "#d0d1e6", "#74a9cf", "#0570b0", "#023858"]
        self.row_labels = row_labels
        self.col_labels = col_labels
        self.show_values = show_values
        super().__init__(x=None, y=None)

    def _interp_color(self, norm_val):
        """Interpolate between cmap stops for a value in [0, 1]."""
        n = len(self.cmap) - 1
        lo_idx = min(int(norm_val * n), n - 1)
        hi_idx = lo_idx + 1
        t      = norm_val * n - lo_idx

        def hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        r1, g1, b1 = hex_to_rgb(self.cmap[lo_idx])
        r2, g2, b2 = hex_to_rgb(self.cmap[hi_idx])
        r = int(r1 + t * (r2 - r1))
        g = int(g1 + t * (g2 - g1))
        b = int(b1 + t * (b2 - b1))
        return f"#{r:02x}{g:02x}{b:02x}"

    def to_svg(self, ax, use_y2=False):
        svg     = []
        rows    = len(self.matrix)
        cols    = len(self.matrix[0])
        flat    = [v for row in self.matrix for v in row]
        vmin, vmax = min(flat), max(flat)
        v_range = vmax - vmin or 1

        pad = ax.padding
        cw  = (ax.width  - 2 * pad) / cols
        ch  = (ax.height - 2 * pad) / rows

        font       = ax.theme.get("font", "sans-serif")
        text_color = ax.theme.get("text_color", "#000")

        for i, row in enumerate(self.matrix):
            for j, val in enumerate(row):
                norm  = (val - vmin) / v_range
                color = self._interp_color(norm)
                x     = pad + j * cw
                y     = pad + i * ch
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" '
                    f'fill="{color}" stroke="#fff" stroke-width="0.5" '
                    f'data-value="{val:.3g}"/>'
                )
                if self.show_values:
                    svg.append(
                        f'<text x="{x + cw / 2}" y="{y + ch / 2 + 4}" '
                        f'text-anchor="middle" font-size="10" '
                        f'font-family="{font}" fill="{text_color}">'
                        f'{_format_tick(val)}</text>'
                    )

        # Column labels
        if self.col_labels:
            for j, lbl in enumerate(self.col_labels):
                cx = pad + (j + 0.5) * cw
                svg.append(
                    f'<text x="{cx}" y="{pad - 6}" text-anchor="middle" '
                    f'font-size="11" font-family="{font}" fill="{text_color}">'
                    f'{svg_escape(str(lbl))}</text>'
                )

        # Row labels
        if self.row_labels:
            for i, lbl in enumerate(self.row_labels):
                ry = pad + (i + 0.5) * ch + 4
                svg.append(
                    f'<text x="{pad - 6}" y="{ry}" text-anchor="end" '
                    f'font-size="11" font-family="{font}" fill="{text_color}">'
                    f'{svg_escape(str(lbl))}</text>'
                )

        # Color-scale legend (vertical strip, right edge)
        bar_x  = ax.width - 20
        bar_y  = pad
        bar_h  = ax.height - 2 * pad
        bar_w  = 12
        steps  = 20
        for k in range(steps):
            norm  = k / (steps - 1)
            color = self._interp_color(norm)
            ry    = bar_y + (1 - norm) * bar_h
            rh    = bar_h / steps + 1  # +1 avoids gaps
            svg.append(
                f'<rect x="{bar_x}" y="{ry}" '
                f'width="{bar_w}" height="{rh}" fill="{color}"/>'
            )

        # Legend min/max labels
        svg.append(
            f'<text x="{bar_x + bar_w + 2}" y="{bar_y + bar_h}" '
            f'font-size="10" font-family="{font}" fill="{text_color}">'
            f'{_format_tick(vmin)}</text>'
        )
        svg.append(
            f'<text x="{bar_x + bar_w + 2}" y="{bar_y + 10}" '
            f'font-size="10" font-family="{font}" fill="{text_color}">'
            f'{_format_tick(vmax)}</text>'
        )

        return "\n".join(svg)
