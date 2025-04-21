import os
import webbrowser
from pathlib import Path
from tempfile import NamedTemporaryFile
from .layout import Axes
from .utils import wrap_svg_with_template, write_svg_file

class Figure:
    """
    Represents a complete chart figure, including axes, series, and rendering logic.

    This is the main class used to render SVG charts in glyphx. A Figure can be rendered
    directly to screen or exported as SVG/HTML.
    """

    def __init__(self, width=640, height=480, padding=50, title=None, theme=None, auto_display=True):
        """
        Initialize a new Figure.

        Args:
            width (int): Width of the figure in pixels.
            height (int): Height of the figure in pixels.
            padding (int): Padding around the edges for axes/grid labels.
            title (str): Optional chart title.
            theme (dict): Optional theme for styling (colors, fonts, etc.).
            auto_display (bool): Whether to automatically show the figure after creation.
        """
        self.width = width
        self.height = height
        self.padding = padding
        self.title = title
        self.theme = theme or {}
        self.auto_display = auto_display

        self.axes = Axes(width=self.width, height=self.height, padding=self.padding, theme=self.theme)
        self.series = []

    def add(self, series, use_y2=False):
        """
        Add a chart series (e.g. LineSeries, BarSeries) to the figure.

        Args:
            series: An instance of a Series class.
            use_y2 (bool): Whether to use a secondary Y-axis.
        """
        self.series.append((series, use_y2))
        self.axes.add_series(series, use_y2)

    def render_svg(self):
        """
        Render the figure to raw SVG content.

        Returns:
            str: SVG string representing the complete chart.
        """
        self.axes.finalize()
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">'
        ]

        # Add title if present
        if self.title:
            svg_parts.append(
                f'<text x="{self.width / 2}" y="{self.padding / 2}" '
                f'text-anchor="middle" font-size="16" font-weight="bold">{self.title}</text>'
            )

        # Add grid and axes
        svg_parts.append(self.axes.render_grid())
        svg_parts.append(self.axes.render_axes())

        # Add all data series
        for series, use_y2 in self.series:
            svg_parts.append(series.to_svg(self.axes, use_y2))

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def _display(self, svg_string):
        """
        Display the SVG chart either in Jupyter or via system browser.

        Args:
            svg_string (str): SVG content to display.
        """
        try:
            from IPython import get_ipython
            ip = get_ipython()
            if ip is not None and "IPKernelApp" in ip.config:
                from IPython.display import SVG, display as jupyter_display
                return jupyter_display(SVG(svg_string))
        except Exception:
            pass

        # Fallback to system browser if not in Jupyter
        html = wrap_svg_with_template(svg_string)
        tmp_file = NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
        tmp_file.write(html)
        tmp_file.close()
        webbrowser.open(f"file://{tmp_file.name}")

    def show(self):
        """
        Display the figure using appropriate output (Jupyter, browser).
        """
        svg = self.render_svg()
        self._display(svg)

    def save(self, filename="glyphx_output.svg"):
        """
        Save the SVG to a file.

        Args:
            filename (str): File path to save the SVG content to.
        """
        svg = self.render_svg()
        write_svg_file(svg, filename)

    def plot(self):
        """
        Trigger display of the figure if auto_display is enabled.
        """
        if self.auto_display:
            self.show()

    def __repr__(self):
        if self.auto_display:
            self.show()
        return f"<glyphx.Figure with {len(self.series)} series>"