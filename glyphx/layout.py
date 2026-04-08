"""
GlyphX layout module: Axes scaling, tick/grid rendering, and multi-figure grid layout.
"""

import math
from .utils import _format_tick, svg_escape


class Axes:
    """
    Manages axis scaling, tick rendering, and series layout within a plot.

    Supports:
    - Dual Y-axes (primary and secondary)
    - Categorical X-axis labels
    - Linear and log-scale axes
    - Configurable tick counts and grid lines
    - Axis title / xlabel / ylabel labels

    Attributes:
        width (int): Plot area width in pixels.
        height (int): Plot area height in pixels.
        padding (int): Space from canvas edge to the plot area.
        show_grid (bool): Whether to render background grid lines.
        theme (dict): Color and font styling dictionary.
        xscale (str): ``"linear"`` or ``"log"``.
        yscale (str): ``"linear"`` or ``"log"``.
        series (list): Series on the primary Y-axis.
        y2_series (list): Series on the secondary Y-axis.
    """

    def __init__(
        self,
        width=600,
        height=400,
        padding=50,
        show_grid=True,
        theme=None,
        legend=None,
        xscale="linear",
        yscale="linear",
    ):
        self.width    = width
        self.height   = height
        self.padding  = padding
        self.show_grid = show_grid
        self.theme    = theme or {}
        self.legend_pos = legend
        self.xscale   = xscale
        self.yscale   = yscale

        self.title  = None
        self.xlabel = None
        self.ylabel = None

        self.series    = []
        self.y2_series = []

        # Computed domains (set by finalize())
        self._x_domain  = None
        self._y_domain  = None
        self._y2_domain = None

        # Categorical label mapping (populated by compute_domain)
        self._x_categories = None

    # ------------------------------------------------------------------
    # Series registration
    # ------------------------------------------------------------------

    def add(self, series, use_y2=False):
        """Proxy for add_series; allows Figure/Axes to share call syntax."""
        self.add_series(series, use_y2=use_y2)

    def add_series(self, series, use_y2=False):
        """
        Register a series on the primary or secondary Y-axis.

        Args:
            series (BaseSeries): Any series with ``.x`` and ``.y`` attributes.
            use_y2 (bool): If True, bind to the right-hand Y-axis.
        """
        if use_y2:
            self.y2_series.append(series)
        else:
            self.series.append(series)

    # ------------------------------------------------------------------
    # Domain computation (non-mutating)
    # ------------------------------------------------------------------

    def compute_domain(self, series_list):
        """
        Compute ``(x_domain, y_domain)`` from a list of series.

        Categorical string X-values are converted to numeric indices.
        The conversion is stored on the series as ``._numeric_x`` so the
        original ``series.x`` is **never mutated**.

        When multiple series each carry different categories (e.g. one bar
        per group from a groupby aggregation), all unique categories are merged
        into a single global ordering so each gets a distinct x position.

        Args:
            series_list (list): Series objects with ``.x`` and ``.y``.

        Returns:
            tuple: ``(x_domain, y_domain)`` each as ``(min, max)`` or
                   ``(None, None)`` if no valid data is found.
        """
        x_vals = []
        y_vals = []

        # Build a global category order across all categorical series so that
        # series each carrying a different single category (e.g. groupby bars)
        # receive unique, non-overlapping x positions.
        global_cats: list = []
        for s in series_list:
            if not hasattr(s, "x") or not s.x:
                continue
            if isinstance(s.x[0], str):
                for cat in s.x:
                    if cat not in global_cats:
                        global_cats.append(cat)

        cat_to_pos: dict = {cat: i + 0.5 for i, cat in enumerate(global_cats)}

        for s in series_list:
            if not hasattr(s, "x") or not hasattr(s, "y"):
                continue
            if not s.x or not s.y:
                continue

            # Handle categorical X: store numeric mapping without mutation
            if isinstance(s.x[0], str):
                s._numeric_x    = [cat_to_pos[cat] for cat in s.x]
                s._x_categories = list(s.x)
                numeric_x = s._numeric_x
            else:
                numeric_x = s.x

            x_vals.extend(numeric_x)
            y_vals.extend(s.y)

        if not x_vals or not y_vals:
            return None, None

        x_domain = (min(x_vals) - 0.5, max(x_vals) + 0.5)

        y_min = min(y_vals)
        y_max = max(y_vals)

        # Force bar-chart Y-axis to include zero
        if any(s.__class__.__name__ == "BarSeries" for s in series_list):
            y_min = min(0, y_min)
            y_max = max(0, y_max)

        # Guard: never pass equal min/max to log scale
        if y_min == y_max:
            y_min -= 1
            y_max += 1

        return x_domain, (y_min, y_max)

    # ------------------------------------------------------------------
    # Scale functions
    # ------------------------------------------------------------------

    def _scale_linear(self, domain_min, domain_max, range_min, range_max):
        """Return a callable that linearly maps domain → pixel range."""
        def scaler(value):
            if domain_max == domain_min:
                return (range_min + range_max) / 2
            return range_min + (value - domain_min) * (range_max - range_min) / (domain_max - domain_min)
        return scaler

    def _scale_log(self, domain_min, domain_max, range_min, range_max):
        """Return a callable that log-maps domain → pixel range."""
        if domain_min <= 0:
            domain_min = 1e-10  # guard against log(0)
        log_min = math.log10(domain_min)
        log_max = math.log10(max(domain_max, domain_min * 10))

        def scaler(value):
            if value <= 0:
                return range_max  # push non-positive values off canvas
            lv = math.log10(value)
            if log_max == log_min:
                return (range_min + range_max) / 2
            return range_min + (lv - log_min) * (range_max - range_min) / (log_max - log_min)
        return scaler

    def _make_scale(self, domain_min, domain_max, range_min, range_max, scale_type):
        if scale_type == "log":
            return self._scale_log(domain_min, domain_max, range_min, range_max)
        return self._scale_linear(domain_min, domain_max, range_min, range_max)

    def finalize(self):
        """
        Compute all scale functions after series have been registered.

        Must be called before any rendering method.
        """
        if self.series:
            self._x_domain, self._y_domain = self.compute_domain(self.series)
        if self.y2_series:
            _, self._y2_domain = self.compute_domain(self.y2_series)

        if self._x_domain and self._y_domain:
            self.scale_x = self._make_scale(
                self._x_domain[0], self._x_domain[1],
                self.padding, self.width - self.padding,
                self.xscale,
            )
            self.scale_y = self._make_scale(
                self._y_domain[0], self._y_domain[1],
                self.height - self.padding, self.padding,
                self.yscale,
            )
        else:
            self.scale_x = None
            self.scale_y = None

        if self._y2_domain:
            self.scale_y2 = self._make_scale(
                self._y2_domain[0], self._y2_domain[1],
                self.height - self.padding, self.padding,
                self.yscale,
            )
        else:
            self.scale_y2 = self.scale_y  # fallback

    # ------------------------------------------------------------------
    # SVG rendering
    # ------------------------------------------------------------------

    def render_axes(self):
        """
        Render X, Y, and (if y2_series exist) Y2 axis lines plus labels.

        Returns:
            str: SVG elements for axes.
        """
        if self._x_domain is None or self._y_domain is None:
            return ""

        elements = []
        stroke     = self.theme.get("axis_color", "#333")
        text_color = self.theme.get("text_color", "#000")
        font       = self.theme.get("font", "sans-serif")
        pad        = self.padding

        # X-axis line
        elements.append(
            f'<line x1="{pad}" y1="{self.height - pad}" '
            f'x2="{self.width - pad}" y2="{self.height - pad}" stroke="{stroke}" />'
        )
        # Y-axis line
        elements.append(
            f'<line x1="{pad}" y1="{pad}" '
            f'x2="{pad}" y2="{self.height - pad}" stroke="{stroke}" />'
        )

        if self.xlabel:
            elements.append(
                f'<text x="{self.width // 2}" y="{self.height - 10}" '
                f'text-anchor="middle" font-size="13" font-family="{font}" '
                f'fill="{text_color}">{svg_escape(self.xlabel)}</text>'
            )

        if self.ylabel:
            elements.append(
                f'<text x="15" y="{self.height // 2}" text-anchor="middle" '
                f'font-size="13" font-family="{font}" fill="{text_color}" '
                f'transform="rotate(-90, 15, {self.height // 2})">'
                f'{svg_escape(self.ylabel)}</text>'
            )

        if self.y2_series:
            elements.append(
                f'<line x1="{self.width - pad}" y1="{pad}" '
                f'x2="{self.width - pad}" y2="{self.height - pad}" stroke="{stroke}" />'
            )

        return "\n".join(elements)

    def render_grid(self, ticks=5):
        """
        Render tick marks, grid lines, and numeric labels.

        Categorical X-axes replace numeric labels with the original category names.

        Args:
            ticks (int): Number of major ticks per axis.

        Returns:
            str: SVG elements for grid and tick labels.
        """
        if not self.show_grid or self._x_domain is None or self._y_domain is None:
            return ""

        elements  = []
        stroke     = self.theme.get("grid_color", "#ddd")
        font       = self.theme.get("font", "sans-serif")
        text_color = self.theme.get("text_color", "#000")
        pad        = self.padding

        # Gather all category labels from every registered series.
        # Use the series._numeric_x positions (set by compute_domain) so that
        # labels align with where the series actually drew their elements.
        all_categories = {}
        for s in self.series:
            if hasattr(s, "_x_categories") and s._x_categories:
                numeric_x = getattr(s, "_numeric_x",
                                    [i + 0.5 for i in range(len(s._x_categories))])
                for pos, cat in zip(numeric_x, s._x_categories):
                    all_categories[pos] = cat

        # --- Y ticks (horizontal grid lines) ---
        for i in range(ticks + 1):
            t   = i / ticks
            y_v = self._y_domain[0] + t * (self._y_domain[1] - self._y_domain[0])
            y_p = self.scale_y(y_v)
            elements.append(
                f'<line x1="{pad}" x2="{self.width - pad}" y1="{y_p}" y2="{y_p}" '
                f'stroke="{stroke}" stroke-dasharray="3,3" />'
            )
            elements.append(
                f'<text x="{pad - 8}" y="{y_p + 4}" text-anchor="end" '
                f'font-size="11" font-family="{font}" fill="{text_color}">'
                f'{_format_tick(y_v)}</text>'
            )

        # --- X ticks (vertical grid lines) ---
        rotate  = getattr(self, "_auto_rotate", False)
        anchor  = "end" if rotate else "middle"
        rot_tfm = f"rotate(-40, {{x_p}}, {{y_label}})" if rotate else ""
        y_label_off = 16 if not rotate else 8

        if all_categories:
            for x_v, label in all_categories.items():
                x_p     = self.scale_x(x_v)
                y_label = self.height - pad + y_label_off
                rot     = rot_tfm.format(x_p=x_p, y_label=y_label) if rotate else ""
                transform = f'transform="{rot}"' if rot else ""
                elements.append(
                    f'<line y1="{pad}" y2="{self.height - pad}" x1="{x_p}" x2="{x_p}" '
                    f'stroke="{stroke}" stroke-dasharray="3,3" />'
                )
                elements.append(
                    f'<text x="{x_p}" y="{y_label}" text-anchor="{anchor}" '
                    f'font-size="11" font-family="{font}" fill="{text_color}" {transform}>'
                    f'{svg_escape(str(label))}</text>'
                )
        else:
            for i in range(ticks + 1):
                t       = i / ticks
                x_v     = self._x_domain[0] + t * (self._x_domain[1] - self._x_domain[0])
                x_p     = self.scale_x(x_v)
                y_label = self.height - pad + y_label_off
                rot     = rot_tfm.format(x_p=x_p, y_label=y_label) if rotate else ""
                transform = f'transform="{rot}"' if rot else ""
                elements.append(
                    f'<line y1="{pad}" y2="{self.height - pad}" x1="{x_p}" x2="{x_p}" '
                    f'stroke="{stroke}" stroke-dasharray="3,3" />'
                )
                elements.append(
                    f'<text x="{x_p}" y="{y_label}" text-anchor="{anchor}" '
                    f'font-size="11" font-family="{font}" fill="{text_color}" {transform}>'
                    f'{_format_tick(x_v)}</text>'
                )

        return "\n".join(elements)


    # ── Tight layout ────────────────────────────────────────────────────────

    def tight_layout(self) -> "Axes":
        """
        Auto-adjust padding so tick labels, axis labels, and titles
        don't clip or overlap.

        Estimates pixel widths of the longest tick labels and increases
        ``self.padding`` accordingly.  Also triggers auto-rotation of
        crowded X-axis labels.

        Returns ``self`` for chaining.
        """
        extra_left  = 0
        extra_bottom = 0

        if self._y_domain:
            # Longest y-tick label (approx. 7px per char)
            longest_y = max(
                len(_format_tick(self._y_domain[0])),
                len(_format_tick(self._y_domain[1])),
            )
            extra_left = max(0, longest_y * 7 + 8 - self.padding + 10)

        if self.ylabel:
            extra_left += 18

        if self.xlabel:
            extra_bottom += 18

        self.padding = max(self.padding, self.padding + max(extra_left, extra_bottom))

        if self._x_domain:
            self._auto_rotate = self._should_rotate_xlabels()

        return self

    def _should_rotate_xlabels(self, ticks: int = 5) -> bool:
        """Return True if x-axis labels would overlap at horizontal angle."""
        if self._x_domain is None:
            return False
        x_range = self._x_domain[1] - self._x_domain[0]
        if x_range == 0:
            return False
        plot_w         = self.width - 2 * self.padding
        tick_spacing   = plot_w / ticks
        # Check categorical labels first
        for s in self.series:
            cats = getattr(s, "_x_categories", None)
            if cats:
                max_len = max(len(str(c)) for c in cats)
                return max_len * 6.5 > tick_spacing * 0.85
        # Numeric labels
        max_len = max(
            len(_format_tick(self._x_domain[0] + i * x_range / ticks))
            for i in range(ticks + 1)
        )
        return max_len * 6.5 > tick_spacing * 0.85


# ---------------------------------------------------------------------------
# Multi-figure grid layout
# ---------------------------------------------------------------------------

def grid(figures, rows=1, cols=1, gap=20):
    """
    Arrange multiple Figure instances in a grid and return a single HTML page.

    Args:
        figures (list[Figure]): GlyphX Figure objects to arrange.
        rows (int): Number of rows in the grid.
        cols (int): Number of columns.
        gap  (int): Pixel margin around each subplot.

    Returns:
        str: Full HTML document with all SVGs embedded.
    """
    from .utils import wrap_svg_with_template

    svg_blocks = []
    idx = 0

    for _ in range(rows):
        row_parts = []
        for _ in range(cols):
            if idx < len(figures):
                svg = figures[idx].render_svg()
                row_parts.append(f'<div style="margin:{gap}px">{svg}</div>')
                idx += 1
        row_html = '<div style="display:flex">' + "".join(row_parts) + "</div>"
        svg_blocks.append(row_html)

    grid_html = "<div>" + "".join(svg_blocks) + "</div>"
    return wrap_svg_with_template(grid_html)
