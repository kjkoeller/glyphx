import os
import webbrowser
from pathlib import Path
from tempfile import NamedTemporaryFile
from .layout import Axes
from .utils import wrap_svg_with_template, write_svg_file, wrap_svg_canvas, draw_legend


class Figure:
    """
    A GlyphX Figure represents a complete chart canvas that can include one or more axes,
    multiple series, layout configuration, themes, and export options.

    Attributes:
        width (int): Canvas width
        height (int): Canvas height
        padding (int): Inner margin padding
        title (str): Optional chart title
        theme (dict): Theme styling for colors, fonts, etc.
        auto_display (bool): Whether to auto-render in notebook/CLI
        grid (list[list]): Optional grid for multi-axes support
    """
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
                 rows=1, cols=1, auto_display=True, legend="top-right"):
        self.width = width
        self.height = height
        self.padding = padding
        self.title = title
        from .themes import themes
        self.theme = themes.get(theme, themes['default']) if isinstance(theme, str) else (theme or themes['default'])
        self.rows = rows
        self.cols = cols
        self.auto_display = auto_display
        if legend in (False, None):
            self.legend_pos = None
        else:
            self.legend_pos = legend

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
            series (BaseSeries): Series to add.
            use_y2 (bool): Use secondary Y-axis.
        """
        self.series.append((series, use_y2))

        # Only add to axes if it's a chart that uses x/y
        if hasattr(series, "x") and hasattr(series, "y"):
            self.axes.add_series(series, use_y2)

    def render_svg(self, viewbox=False):
        """
        Render the plot and return SVG string output.

        Returns:
            str: Complete SVG markup as a string.
        """
        svg_parts = []

        # Draw background
        svg_parts.append(
            f'<rect width="{self.width}" height="{self.height}" fill="{self.theme.get("background", "#ffffff")}" />'
        )

        # Title
        if self.title:
            svg_parts.append(
                f'<text x="{self.width // 2}" y="30" text-anchor="middle" '
                f'font-size="20" font-family="{self.theme.get("font", "sans-serif")}" '
                f'fill="{self.theme.get("text_color", "#000")}">{self.title}</text>'
            )

        # Subplot grid
        if self.grid and any(any(cell for cell in row) for row in self.grid):
            cell_width = self.width // self.cols
            cell_height = self.height // self.rows
            for r, row in enumerate(self.grid):
                for c, ax in enumerate(row):
                    if ax:
                        ax.finalize()
                        group = f'<g transform="translate({c * cell_width}, {r * cell_height})">'
                        group += ax.render_axes()
                        group += ax.render_grid()
                        for series in ax.series:
                            group += series.to_svg(ax)

                        # 🔥 Per-Axes Legend
                        if getattr(ax, "legend_pos", None):
                            group += draw_legend(
                                ax.series,
                                position=ax.legend_pos,
                                font=self.theme.get("font", "sans-serif"),
                                text_color=self.theme.get("text_color", "#000"),
                                fig_width=ax.width,
                                fig_height=ax.height
                            )

                        group += '</g>'
                        svg_parts.append(group)

        # Single axes charts (line, bar, scatter)
        elif self.axes and self.series and any(
                hasattr(s, "x") and hasattr(s, "y") and getattr(s, "x", None) and getattr(s, "y", None)
                for s, _ in self.series
        ):
            if not self.axes.series:
                for s, use_y2 in self.series:
                    self.axes.add_series(s, use_y2)

            self.axes.finalize()
            svg_parts.append(self.axes.render_axes())
            svg_parts.append(self.axes.render_grid())
            for series, _ in self.series:
                svg_parts.append(series.to_svg(self.axes))

            # ✅ Global Legend for non-grid usage
            if self.legend_pos:
                legend_svg = draw_legend(
                    [s for (s, _) in self.series],
                    position=self.legend_pos,
                    font=self.theme.get("font", "sans-serif"),
                    text_color=self.theme.get("text_color", "#000"),
                    fig_width=self.width,
                    fig_height=self.height
                )
                svg_parts.append(legend_svg)

        # Standalone (e.g., PieSeries, DonutSeries)
        elif self.series:
            for series, _ in self.series:
                svg_parts.append(series.to_svg())

        return wrap_svg_canvas("\n".join(svg_parts), width=self.width, height=self.height)

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

# Added subplot layout handling
class SubplotGrid:
    """
    Simple 2D grid layout system for organizing subplots (axes) in rows and columns.
    """
    def __init__(self, rows, cols):
        """
        Create a subplot grid.

        Parameters:
            rows (int): Number of rows.
            cols (int): Number of columns.
        """
        self.rows = rows
        self.cols = cols
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]

    def add_axes(self, row, col, plot):
        """
        Assign a plot to a specific cell in the grid.

        Parameters:
            row (int): Row index.
            col (int): Column index.
            plot (Plot): Plot object to assign.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = plot

    def render(self):
        """
        Stub function to render each subplot (to be expanded for layout).
        """
        for r in range(self.rows):
            for c in range(self.cols):
                plot = self.grid[r][c]
                if plot:
                    print(f"Rendering subplot at ({r}, {c})")
