import os
from pathlib import Path
import tempfile
import webbrowser

def normalize(data):
    """
    Normalize numeric array to 0–1 range.

    Args:
        data (array-like): List or NumPy array of values

    Returns:
        np.ndarray: Normalized values scaled to [0, 1]
    """
    import numpy as np
    arr = np.array(data)
    return (arr - arr.min()) / (arr.max() - arr.min())


def wrap_svg_with_template(svg_string: str) -> str:
    """
    Wrap raw <svg> content in a responsive HTML template with optional interactivity.

    Includes:
    - Mouse hover support
    - Export buttons
    - Zoom/pan (if zoom.js is found in assets)
    - Legend interactivity (click-to-toggle)

    Args:
        svg_string (str): Raw SVG markup string

    Returns:
        str: Full HTML document with embedded SVG and JS
    """
    template_path = Path(__file__).parent / "assets" / "responsive_template.html"
    zoom_path = Path(__file__).parent / "assets" / "zoom.js"

    if not template_path.exists():
        raise FileNotFoundError("Missing responsive_template.html in assets folder")

    html = template_path.read_text(encoding="utf-8")

    # Inject zoom script if available
    zoom_script = ""
    if zoom_path.exists():
        zoom_content = zoom_path.read_text(encoding="utf-8")
        zoom_script = f"<script>\n{zoom_content}\n</script>"

    # Inject legend toggle script
    legend_js = """
    <script>
    document.querySelectorAll('.legend-icon, .legend-label').forEach(el => {
      el.addEventListener('click', () => {
        const target = el.dataset.target;
        const elems = document.querySelectorAll(`.${target}`);
        elems.forEach(e => {
          e.style.display = e.style.display === 'none' ? '' : 'none';
        });
      });
    });
    </script>
    """

    return html.replace("{{svg_content}}", svg_string).replace("{{extra_scripts}}", zoom_script + legend_js)



def wrap_svg_canvas(svg_content: str, width: int = 640, height: int = 480) -> str:
    """
    Wrap raw SVG elements in a full <svg> canvas.

    Args:
        svg_content (str): Inner SVG markup (e.g., axes, series, labels).
        width (int): Canvas width in pixels.
        height (int): Canvas height in pixels.

    Returns:
        str: Complete SVG tag with given dimensions and viewBox.
    """
    return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{svg_content}</svg>"""


def write_svg_file(svg_string: str, filename: str):
    """
    Save SVG or HTML export (or convert to image) to file.

    Args:
        svg_string (str): Raw SVG content
        filename (str): Output filename with extension:
                        - .svg: plain vector
                        - .html: interactive viewer
                        - .png/.jpg: raster (via cairosvg)
    """
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".html":
        html = wrap_svg_with_template(svg_string)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    elif ext == ".svg":
        with open(filename, "w", encoding="utf-8") as f:
            f.write(svg_string)

    elif ext in {".png", ".jpg", ".jpeg"}:
        # Convert using optional external dependency
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg_string.encode(), write_to=filename)
        except ImportError:
            raise RuntimeError("To export as PNG/JPG, install cairosvg: pip install cairosvg")

    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def in_jupyter():
    """
    Detect if running inside a Jupyter Notebook.

    Returns:
        bool: True if in Jupyter environment
    """
    try:
        from IPython import get_ipython
        return "IPKernelApp" in get_ipython().config
    except Exception:
        return False


def in_cli_or_ide():
    """
    Detect if running in a non-Jupyter environment (CLI or IDE).

    Returns:
        bool: True if NOT in Jupyter
    """
    return not in_jupyter()


def render_cli(svg_string):
    """
    Render a raw SVG string to a temporary HTML file in browser (for CLI/IDE users).

    Args:
        svg_string (str): Raw SVG markup to embed in HTML
    """
    path = tempfile.mktemp(suffix=".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<html><body>{svg_string}</body></html>")
    webbrowser.open(f"file://{path}")


def draw_legend(series_list, position="top-right", font="sans-serif", text_color="#000",
                fig_width=640, fig_height=480, cell_width=None, cell_height=None):
    """
    Render a dynamic legend block for a list of series.

    Args:
        series_list (list): Series or (series, use_y2) tuples.
        position (str): Legend position (top-left, bottom-right, left, right, etc.).
        font (str): Font family for labels.
        text_color (str): Color for text.
        fig_width (int): Width of the figure (fallback if Axes width not provided).
        fig_height (int): Height of the figure.
        cell_width (int, optional): Width of subplot cell (overrides fig_width).
        cell_height (int, optional): Height of subplot cell (overrides fig_height).

    Returns:
        str: SVG group (<g>) element containing the legend.
    """
    # Normalize incoming series
    series_list = [s if not isinstance(s, tuple) else s[0] for s in series_list if getattr(s[0] if isinstance(s, tuple) else s, "label", None)]
    if not series_list:
        return ""

    # Size parameters
    spacing = 20      # Vertical space between legend items
    padding = 10      # Margin from edges
    icon_size = 12    # Size of color box
    text_padding = 6  # Space between icon and label

    # Choose working width/height (subplot cell or full figure)
    width = cell_width if cell_width else fig_width
    height = cell_height if cell_height else fig_height

    # Estimate longest label width (approx, 8px per char)
    max_label_len = max(len(s.label) for s in series_list)
    label_pixel_width = max_label_len * 8

    legend_width = icon_size + text_padding + label_pixel_width + 2 * padding
    legend_height = len(series_list) * spacing + 2 * padding

    # Default (top-left)
    x = padding
    y = padding

    if position == "top-right":
        x = width - legend_width - padding
        y = padding
    elif position == "bottom-right":
        x = width - legend_width - padding
        y = height - legend_height - padding
    elif position == "bottom-left":
        x = padding
        y = height - legend_height - padding
    elif position == "top-left":
        x = padding
        y = padding
    elif position == "top":
        x = (width - legend_width) // 2
        y = padding
    elif position == "bottom":
        x = (width - legend_width) // 2
        y = height - legend_height - padding
    elif position == "left":
        x = padding
        y = (height - legend_height) // 2
    elif position == "right":
        x = width - legend_width - padding
        y = (height - legend_height) // 2

    # Build SVG elements
    items = []
    for i, s in enumerate(series_list):
        class_name = getattr(s, "css_class", f"series-{i}")
        color = s.color or "#888"
        label = s.label
        cy = y + padding + i * spacing

        # Icon
        items.append(
            f'<rect x="{x}" y="{cy}" width="{icon_size}" height="{icon_size}" '
            f'fill="{color}" class="legend-icon" data-target="{class_name}" />'
        )

        # Label text
        items.append(
            f'<text x="{x + icon_size + text_padding}" y="{cy + icon_size - 2}" '
            f'font-size="12" font-family="{font}" fill="{text_color}" '
            f'class="legend-label" data-target="{class_name}">{label}</text>'
        )

    return '<g class="glyphx-legend">\n' + "\n".join(items) + '\n</g>'






