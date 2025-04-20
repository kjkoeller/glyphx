import os
from pathlib import Path

def normalize(data):
    import numpy as np
    arr = np.array(data)
    return (arr - arr.min()) / (arr.max() - arr.min())

def wrap_svg_with_template(svg_string: str) -> str:
    """
    Wrap raw <svg> content in a responsive HTML template with hover + export support.
    """
    template_path = Path(__file__).parent / "assets" / "responsive_template.html"
    if not template_path.exists():
        raise FileNotFoundError("Missing responsive_template.html in assets folder")

    html = template_path.read_text(encoding="utf-8")
    return html.replace("{{svg_content}}", svg_string)


def write_svg_file(svg_string: str, filename: str):
    """
    Write rendered SVG or HTML to a file.
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
        # Defer to external tools for conversion (e.g., CairoSVG)
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg_string.encode(), write_to=filename)
        except ImportError:
            raise RuntimeError("To export as PNG/JPG, install cairosvg: pip install cairosvg")
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
