class Axes:
    """
    Axes container for chart layout, labeling, and coordinate scaling.

    Attributes:
        width (int): Total width of the axis frame in pixels.
        height (int): Total height of the axis frame in pixels.
        padding (int): Padding around plot area for axis labels/ticks.
        xlim (tuple or None): Optional (min, max) range for x-axis.
        ylim (tuple or None): Optional (min, max) range for y-axis.
        y2lim (tuple or None): Optional range for secondary y-axis (not rendered here).
        xlabel (str): Label text for x-axis.
        ylabel (str): Label text for y-axis.
        title (str): Title text to display above chart.
    """

    def __init__(self, width=400, height=300, padding=40,
                 xlim=None, ylim=None, y2lim=None, xlabel="", ylabel="", title=""):
        self.width = width
        self.height = height
        self.padding = padding
        self.xlim = xlim
        self.ylim = ylim
        self.y2lim = y2lim
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title

    def render_labels(self, svg):
        """
        Append text SVG elements for the title and axis labels.

        Args:
            svg (list[str]): List to which SVG <text> elements are appended.
        """
        if self.title:
            svg.append(
                f'<text x="{self.width / 2}" y="20" text-anchor="middle" font-size="16" font-weight="bold">{self.title}</text>'
            )

        if self.xlabel:
            svg.append(
                f'<text x="{self.width / 2}" y="{self.height - 5}" text-anchor="middle" font-size="12">{self.xlabel}</text>'
            )

        if self.ylabel:
            # Rotate 90 degrees counterclockwise around the axis center
            svg.append(
                f'<text x="15" y="{self.height / 2}" text-anchor="middle" font-size="12" '
                f'transform="rotate(-90 15,{self.height / 2})">{self.ylabel}</text>'
            )

    def scale_x(self, x):
        """
        Map a data x-value to a pixel x-position.

        Args:
            x (float): Data value along the x-axis

        Returns:
            float: Scaled x pixel value
        """
        min_x = self.xlim[0] if self.xlim else min(self._xdata)
        max_x = self.xlim[1] if self.xlim else max(self._xdata)
        return self.padding + (x - min_x) / (max_x - min_x) * (self.width - 2 * self.padding)

    def scale_y(self, y):
        """
        Map a data y-value to a pixel y-position (inverted axis).

        Args:
            y (float): Data value along the y-axis

        Returns:
            float: Scaled y pixel value
        """
        min_y = self.ylim[0] if self.ylim else min(self._ydata)
        max_y = self.ylim[1] if self.ylim else max(self._ydata)
        return self.height - self.padding - (y - min_y) / (max_y - min_y) * (self.height - 2 * self.padding)

    def add_series(self, series, use_y2=False):
        """Add a data series to determine bounds and prepare for layout."""
        self.series.append(series)
        for x, y in zip(series.x, series.y):
            self.xmin = min(self.xmin, x)
            self.xmax = max(self.xmax, x)
            if use_y2:
                self.y2min = min(self.y2min, y)
                self.y2max = max(self.y2max, y)
            else:
                self.ymin = min(self.ymin, y)
                self.ymax = max(self.ymax, y)

    def finalize(self):
        """Calculate final axis bounds and ticks based on added series."""
        self._calc_scales()

    def _calc_scales(self):
        """Precompute scale ranges for x and y axes."""
        self.xrange = self.xmax - self.xmin if self.xmax != self.xmin else 1
        self.yrange = self.ymax - self.ymin if self.ymax != self.ymin else 1
        self.y2range = self.y2max - self.y2min if self.y2max != self.y2min else 1

    def scale_y2(self, y):
        """Scale y-values to pixel position on the secondary axis."""
        return self.height - self.padding - (y - self.y2min) / self.y2range * (self.height - 2 * self.padding)

    def render_axes(self):
        """Render SVG elements for x, y, and y2 axes."""
        elements = [
            f'<line x1="{self.padding}" x2="{self.width - self.padding}" y1="{self.height - self.padding}" y2="{self.height - self.padding}" stroke="{self.theme.get("axis_color", "#000")}" />',  # x-axis
            f'<line x1="{self.padding}" x2="{self.padding}" y1="{self.padding}" y2="{self.height - self.padding}" stroke="{self.theme.get("axis_color", "#000")}" />',  # y-axis
            f'<line x1="{self.width - self.padding}" x2="{self.width - self.padding}" y1="{self.padding}" y2="{self.height - self.padding}" stroke="{self.theme.get("axis_color", "#000")}" />'  # y2-axis
        ]
        return "\n".join(elements)

    def render_grid(self):
        """Render horizontal and vertical gridlines based on ticks."""
        elements = []
        tick_color = self.theme.get("grid_color", "#ccc")
        for i in range(6):
            # Vertical grid lines
            x = self.padding + i * (self.width - 2 * self.padding) / 5
            elements.append(f'<line x1="{x}" x2="{x}" y1="{self.padding}" y2="{self.height - self.padding}" stroke="{tick_color}" stroke-dasharray="2,2"/>')
            # Horizontal grid lines
            y = self.padding + i * (self.height - 2 * self.padding) / 5
            elements.append(f'<line x1="{self.padding}" x2="{self.width - self.padding}" y1="{y}" y2="{y}" stroke="{tick_color}" stroke-dasharray="2,2"/>')
        return "\n".join(elements)