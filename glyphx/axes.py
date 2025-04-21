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