import os
import webbrowser
from pathlib import Path
from tempfile import NamedTemporaryFile
from IPython.display import SVG, display as jupyter_display
from .layout import Axes
from .utils import wrap_svg_with_template, write_svg_file


class Figure:
    def __init__(self, width=640, height=480, padding=50, title=None, theme=None, auto_display=True):
        self.width = width
        self.height = height
        self.padding = padding
        self.title = title
        self.theme = theme or {}
        self.auto_display = auto_display

        self.axes = Axes(width=self.width, height=self.height, padding=self.padding, theme=self.theme)
        self.series = []

    def add(self, series, use_y2=False):
        self.series.append((series, use_y2))
        self.axes.add_series(series, use_y2)

    def render_svg(self):
        self.axes.finalize()
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
        ]

        if self.title:
            svg_parts.append(
                f'<text x="{self.width / 2}" y="{self.padding / 2}" text-anchor="middle" font-size="16" font-weight="bold">{self.title}</text>'
            )

        svg_parts.append(self.axes.render_grid())
        svg_parts.append(self.axes.render_axes())

        for series, use_y2 in self.series:
            svg_parts.append(series.to_svg(self.axes, use_y2))

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def _display(self, svg_string):
        if os.environ.get("DISPLAY") is None:
            # CLI or IDE - write to temp file and open
            tmp_path = NamedTemporaryFile(delete=False, suffix=".html")
            html = wrap_svg_with_template(svg_string)
            tmp_path.write(html.encode("utf-8"))
            tmp_path.close()
            webbrowser.open(f"file://{tmp_path.name}")
        else:
            # Jupyter
            jupyter_display(SVG(svg_string))

    def show(self):
        svg = self.render_svg()
        self._display(svg)

    def save(self, filename="glyphx_output.svg"):
        svg = self.render_svg()
        write_svg_file(svg, filename)

    def plot(self):
        if self.auto_display:
            self.show()