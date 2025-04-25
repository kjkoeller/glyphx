class Axes:
    """
    Manages axis scaling, tick rendering, and series layout within a plot.

    Handles support for dual Y-axes (primary and secondary) and SVG grid/axis rendering.

    Attributes:
        width (int): Plot area width in pixels.
        height (int): Plot area height in pixels.
        padding (int): Padding from edges to axes.
        show_grid (bool): Whether to show background grid lines.
        theme (dict): Color and style theme dictionary.
        series (list): Series plotted on the primary Y-axis.
        y2_series (list): Series plotted on the secondary Y-axis.
    """
    def __init__(self, width=600, height=400, padding=50, show_grid=True, theme=None, legend=None):
        self.width = width
        self.height = height
        self.padding = padding
        self.show_grid = show_grid
        self.theme = theme or {}
        self.legend_pos = legend

        self.title = None
        self.xlabel = None
        self.ylabel = None

        self.series = []
        self.y2_series = []

        # Domains for scaling
        self._x_domain = None
        self._y_domain = None
        self._y2_domain = None

    def add(self, series, use_y2=False):
        """Proxy for add_series, allowing Figure/Axes to share syntax."""
        self.add_series(series, use_y2=use_y2)

    def add_series(self, series, use_y2=False):
        """
        Add a series to the primary or secondary Y-axis.

        Args:
            series (BaseSeries): Any series object with .x and .y
            use_y2 (bool): If True, assign to right-hand Y-axis
        """
        if use_y2:
            self.y2_series.append(series)
        else:
            self.series.append(series)

    def compute_domain(self, series_list):
        """
        Compute (min, max) for x and y values in the given series list.
        Handles numeric and categorical x-values, and forces y-axis to include 0 for bar charts.
        """
        x_vals = []
        y_vals = []

        for s in series_list:
            if not hasattr(s, 'x') or not hasattr(s, 'y'):
                continue

            # Convert categorical x-values (like ["A", "B", "C"]) into index + 0.5 for spacing
            if s.x and isinstance(s.x[0], str):
                s.categories = s.x
                s.x = [i + 0.5 for i in range(len(s.x))]

            if not s.x or not s.y:
                continue

            x_vals.extend(s.x)
            y_vals.extend(s.y)

        if not x_vals or not y_vals:
            return None, None

        x_domain = (min(x_vals) - 0.5, max(x_vals) + 0.5)
        y_min = min(y_vals)
        y_max = max(y_vals)

        # Ensure y-axis includes 0 for bar charts
        if any(s.__class__.__name__ == "BarSeries" for s in series_list):
            y_min = min(0, y_min)
            y_max = max(0, y_max)

        y_domain = (y_min, y_max)

        return x_domain, y_domain

    def _scale_linear(self, domain_min, domain_max, range_min, range_max):
        """
        Create a linear scaling function from domain to range.

        Handles zero-width domains by returning midpoint of range.
        """
        def scaler(value):
            if domain_max == domain_min:
                return (range_min + range_max) / 2
            return range_min + (value - domain_min) * (range_max - range_min) / (domain_max - domain_min)
        return scaler

    def finalize(self):
        """
        Finalize scale functions for rendering axes and series.

        Computes axis domains and prepares .scale_x, .scale_y, .scale_y2.
        Skips processing if series do not provide x/y coordinates.
        """
        if self.series:
            domain = self.compute_domain(self.series)
            if domain is not None:
                self._x_domain, self._y_domain = domain

        if self.y2_series:
            _, self._y2_domain = self.compute_domain(self.y2_series)

        # Only scale if domains are computed
        if self._x_domain and self._y_domain:
            self.scale_x = self._scale_linear(self._x_domain[0], self._x_domain[1],
                                              self.padding, self.width - self.padding)
            self.scale_y = self._scale_linear(self._y_domain[0], self._y_domain[1],
                                              self.height - self.padding, self.padding)
            self.scale_y2 = self._scale_linear(self._y2_domain[0], self._y2_domain[1],
                                               self.height - self.padding,
                                               self.padding) if self.y2_series else self.scale_y

    def render_axes(self):
        """
        Render X, Y, and optional Y2 axis lines in SVG.

        Returns:
            str: SVG elements for axes.
        """
        if self._x_domain is None or self._y_domain is None:
            return ""  # No axes for non-x/y plots

        elements = []
        stroke = self.theme.get("axis_color", "#333")
        text_color = self.theme.get("text_color", "#000")

        # X-axis
        elements.append(f'<line x1="{self.padding}" y1="{self.height - self.padding}" '
                        f'x2="{self.width - self.padding}" y2="{self.height - self.padding}" stroke="{stroke}" />')

        # Y-axis (left)
        elements.append(f'<line x1="{self.padding}" y1="{self.padding}" '
                        f'x2="{self.padding}" y2="{self.height - self.padding}" stroke="{stroke}" />')

        # Draw axis title centered below X
        if self.xlabel:
            elements.append(
                f'<text x="{(self.width) // 2}" y="{self.height - 20}" text-anchor="middle" font-size="14" fill="{text_color}">{self.xlabel}</text>'
            )

        # Draw axis title rotated for Y
        if self.ylabel:
            elements.append(
                f'<text x="20" y="{self.height // 2}" text-anchor="middle" font-size="14" fill="{text_color}" transform="rotate(-90, 15, {self.height // 2})">{self.ylabel}</text>'
            )

        # Y2-axis (right)
        if self.y2_series:
            elements.append(f'<line x1="{self.width - self.padding}" y1="{self.padding}" '
                            f'x2="{self.width - self.padding}" y2="{self.height - self.padding}" stroke="{stroke}" />')

        return "\n".join(elements)

    def render_grid(self, ticks=5):
        """
        Render X and Y grid lines + tick labels in SVG.

        Args:
            ticks (int): Number of major ticks.

        Returns:
            str: SVG elements for grid and labels.
        """
        if not self.show_grid:
            return ""

        if self._x_domain is None or self._y_domain is None:
            # No valid axis-based series, skip grid rendering
            return ""

        elements = []
        stroke = self.theme.get("grid_color", "#ddd")
        font = self.theme.get("font", "sans-serif")
        text_color = self.theme.get("text_color", "#000")

        # Horizontal lines and Y-tick labels
        for i in range(ticks + 1):
            y_val = self._y_domain[0] + i * (self._y_domain[1] - self._y_domain[0]) / ticks
            y_pos = self.scale_y(y_val)
            elements.append(
                f'<line x1="{self.padding}" x2="{self.width - self.padding}" y1="{y_pos}" y2="{y_pos}" '
                f'stroke="{stroke}" stroke-dasharray="3,3" />')
            elements.append(
                f'<text x="{self.padding - 10}" y="{y_pos + 4}" text-anchor="end" '
                f'font-size="12" font-family="{font}" fill="{text_color}">{round(y_val, 2)}</text>')

        # Vertical lines and X-tick labels
        for i in range(ticks + 1):
            x_val = self._x_domain[0] + i * (self._x_domain[1] - self._x_domain[0]) / ticks
            x_pos = self.scale_x(x_val)

            label = round(x_val, 2)

            # Override with categories if available
            if self.series and hasattr(self.series[0], "categories"):
                cat = self.series[0].categories
                idx = round(x_val)
                if 0 <= idx < len(cat):
                    label = cat[idx]

            # Use custom ticks when categories exist
            if self.series and hasattr(self.series[0], "categories"):
                categories = self.series[0].categories
                for i, label in enumerate(categories):
                    x_pos = self.scale_x(i + 0.5)  # match bar offset
                    elements.append(
                        f'<line y1="{self.padding}" y2="{self.height - self.padding}" x1="{x_pos}" x2="{x_pos}" '
                        f'stroke="{stroke}" stroke-dasharray="3,3" />')
                    elements.append(
                        f'<text x="{x_pos}" y="{self.height - self.padding + 16}" text-anchor="middle" '
                        f'font-size="12" font-family="{font}" fill="{text_color}">{label}</text>')
            else:
                # fallback to numeric ticks
                for i in range(ticks + 1):
                    x_val = self._x_domain[0] + i * (self._x_domain[1] - self._x_domain[0]) / ticks
                    x_pos = self.scale_x(x_val)
                    label = round(x_val, 2)
                    elements.append(
                        f'<line y1="{self.padding}" y2="{self.height - self.padding}" x1="{x_pos}" x2="{x_pos}" '
                        f'stroke="{stroke}" stroke-dasharray="3,3" />')
                    elements.append(
                        f'<text x="{x_pos}" y="{self.height - self.padding + 16}" text-anchor="middle" '
                        f'font-size="12" font-family="{font}" fill="{text_color}">{label}</text>')

        return "\n".join(elements)


def grid(figures, rows=1, cols=1, gap=20):
    """
    Arrange multiple Figures into a grid layout and return a single HTML page.

    Args:
        figures (list[Figure]): List of glyphx.Figure instances.
        rows (int): Number of grid rows.
        cols (int): Number of grid columns.
        gap (int): Margin spacing between subplots in pixels.

    Returns:
        str: Full HTML page as a string with embedded SVGs.
    """
    from .utils import wrap_svg_with_template

    svg_blocks = []
    idx = 0

    for r in range(rows):
        row = []
        for c in range(cols):
            if idx < len(figures):
                svg = figures[idx].render_svg()
                row.append(f'<div style="margin:{gap}px">{svg}</div>')
                idx += 1
        row_html = '<div style="display:flex">' + "".join(row) + '</div>'
        svg_blocks.append(row_html)

    grid_html = "<div>" + "".join(svg_blocks) + "</div>"
    return wrap_svg_with_template(grid_html)
