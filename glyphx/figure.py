import os
import webbrowser
from pathlib import Path
from tempfile import NamedTemporaryFile
from .layout import Axes
from .utils import wrap_svg_with_template, write_svg_file


class Figure:
    """
    The central class for creating and rendering visualizations in GlyphX.

    Supports grid layout, dynamic axis scaling, SVG rendering,
    and auto-display in Jupyter, CLI, or IDE.

    Attributes:
        width (int): Width of the figure in pixels.
        height (int): Height of the figure in pixels.
        padding (int): Space around the plot area.
        title (str): Optional title rendered at the top of the SVG.
        theme (dict): Optional theme styling dictionary.
        rows (int): Number of subplot rows.
        cols (int): Number of subplot columns.
        auto_display (bool): If True, automatically displays after plot().
    """
    def __init__(self, width=640, height=480, padding=50, title=None, theme=None,
                 rows=1, cols=1, auto_display=True):
        self.width = width
        self.height = height
        self.padding = padding
        self.title = title
        self.theme = theme or {}
        self.rows = rows
        self.cols = cols
        self.auto_display = auto_display

        # Grid stores subplot Axes references (None until created)
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]

        # Main axes for single plots (backward compatibility)
        self.axes = Axes(width=self.width, height=self.height, padding=self.padding, theme=self.theme)

        # List of (series, use_y2) tuples to render on plot
        self.series = []

    def add_axes(self, row=0, col=0):
        """
        Create or retrieve an Axes object for a specific grid position.

        Args:
            row (int): Grid row index.
            col (int): Grid column index.

        Returns:
            Axes: The axes at the specified location.
        """
        if self.grid[row][col] is None:
            ax = Axes(
                width=self.width // self.cols,
                height=self.height // self.rows,
                padding=self.padding,
                theme=self.theme
            )
            self.grid[row][col] = ax
        return self.grid[row][col]

    def add(self, series, use_y2=False):
        """
        Add a data series to the current plot.

        Args:
            series (BaseSeries): Any subclass implementing to_svg().
            use_y2 (bool): If True, use secondary Y-axis for this series.
        """
        self.series.append((series, use_y2))
        self.axes.add_series(series, use_y2)

    def render_svg(self):
        """
        Render the plot and return SVG string output.

        Returns:
            str: Complete SVG markup as a string.
        """
        self.axes.finalize()
        
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
        ]

        # Inject background if theme defines it
        bg_color = self.theme.get("background")
        if bg_color:
            svg_parts.append(f'<rect width="100%" height="100%" fill="{bg_color}" />')

        # Render optional title
        if self.title:
            svg_parts.append(
                f'<text x="{self.width / 2}" y="{self.padding / 2}" text-anchor="middle" font-size="16" font-weight="bold">{self.title}</text>'
            )

        # Draw grid lines and axes
        svg_parts.append(self.axes.render_grid())
        svg_parts.append(self.axes.render_axes())

        # Render each series
        for series, use_y2 in self.series:
            svg_parts.append(series.to_svg(self.axes, use_y2))

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def _display(self, svg_string):
        """
        Display logic for Jupyter, CLI, or IDE environments.

        Args:
            svg_string (str): SVG content to render or preview.
        """
        try:
            # Display in Jupyter notebook
            from IPython import get_ipython
            ip = get_ipython()
            if ip is not None and "IPKernelApp" in ip.config:
                from IPython.display import SVG, display as jupyter_display
                return jupyter_display(SVG(svg_string))
        except Exception:
            pass

        # Fallback to saving HTML and opening in system browser
        html = wrap_svg_with_template(svg_string)
        tmp_file = NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp_file.write(html)
        tmp_file.close()
        webbrowser.open(f"file://{tmp_file.name}")

    def show(self):
        """
        Render and display the chart immediately.
        """
        svg = self.render_svg()
        self._display(svg)

    def save(self, filename="glyphx_output.svg"):
        """
        Save the rendered SVG to a file.

        Args:
            filename (str): Output filename.
        """
        svg = self.render_svg()
        write_svg_file(svg, filename)

    def plot(self):
        """
        Shortcut for `.show()` when auto_display is True.
        Called automatically at end of unified plot().
        """
        if self.auto_display:
            self.show()

    def __repr__(self):
        """
        Custom REPL behavior (auto-show if enabled).
        """
        if self.auto_display:
            self.show()
        return f"<glyphx.Figure with {len(self.series)} series>"