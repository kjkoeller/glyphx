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

    return html.replace("{{svg_content}}", svg_string).replace("{{extra_scripts}}", zoom_script)


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
