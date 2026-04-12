from __future__ import annotations

from typing import Any

"""
GlyphX utility functions: SVG helpers, display detection, legend rendering.
"""

import html
import os
import math
import tempfile
import webbrowser
from pathlib import Path


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------

def normalize(data):
    """
    Normalize a numeric array to the [0, 1] range.

    Args:
        data (array-like): List or NumPy array of values.

    Returns:
        np.ndarray: Values scaled to [0, 1].

    Raises:
        ValueError: If all values are equal (zero-width range).
    """
    import numpy as np
    arr = np.array(data, dtype=float)
    lo, hi = arr.min(), arr.max()
    if hi == lo:
        raise ValueError("normalize() requires data with non-zero range; all values are equal.")
    return (arr - lo) / (hi - lo)


def _format_tick(val, is_log: bool = False):
    """
    Format a numeric tick label intelligently.

    On log axes uses clean power-of-ten notation (1, 10, 100, 1k, 1M).
    On linear axes uses readable decimal notation.

    Args:
        val (float): Tick value.
        is_log (bool): Whether the axis is logarithmic.

    Returns:
        str: Human-readable label.
    """
    if val == 0:
        return "0"
    abs_val = abs(val)

    if is_log:
        # Clean log-scale labels: prefer 1/10/100/1k/1M/1B notation
        if abs_val >= 1e9:
            v = val / 1e9
            return f"{int(v)}B" if v == int(v) else f"{v:.1f}B"
        if abs_val >= 1e6:
            v = val / 1e6
            return f"{int(v)}M" if v == int(v) else f"{v:.1f}M"
        if abs_val >= 1e3:
            v = val / 1e3
            return f"{int(v)}k" if v == int(v) else f"{v:.1f}k"
        if val == int(val):
            return str(int(val))
        return f"{val:.2g}"

    # Linear axis
    if abs_val >= 1e9:
        v = val / 1e9
        return f"{int(v)}B" if v == int(v) else f"{v:.1f}B"
    if abs_val >= 1e6:
        v = val / 1e6
        return f"{int(v)}M" if v == int(v) else f"{v:.1f}M"
    if abs_val >= 1e3 and val == int(val):
        return f"{int(val):,}"
    if abs_val < 1e-3 and abs_val > 0:
        return f"{val:.2e}"
    if val == int(val):
        return str(int(val))
    if abs_val >= 100:
        return f"{val:.0f}"
    if abs_val >= 10:
        return f"{val:.1f}"
    return f"{val:.2f}"


# ---------------------------------------------------------------------------
# SVG escaping
# ---------------------------------------------------------------------------

def svg_escape(text):
    """
    Escape a string for safe embedding inside SVG text or attribute values.

    Args:
        text (str): Raw user-provided string.

    Returns:
        str: HTML-escaped string safe for SVG.
    """
    return html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# SVG/HTML wrapping
# ---------------------------------------------------------------------------

def wrap_svg_with_template(svg_string: str) -> str:
    """
    Wrap raw <svg> content in a responsive HTML template with interactivity.

    Includes:
    - Mouse-hover tooltip support
    - Export buttons (SVG, PNG)
    - Zoom/pan via mouse wheel + drag
    - Click-to-toggle legend

    Args:
        svg_string (str): Raw SVG markup string.

    Returns:
        str: Full HTML document with embedded SVG and JS.

    Raises:
        FileNotFoundError: If the HTML template asset is missing.
    """
    template_path = Path(__file__).parent / "assets" / "responsive_template.html"
    zoom_path = Path(__file__).parent / "assets" / "zoom.js"

    if not template_path.exists():
        raise FileNotFoundError(
            f"Missing responsive_template.html in assets folder: {template_path}"
        )

    html_content = template_path.read_text(encoding="utf-8")

    zoom_script = ""
    if zoom_path.exists():
        zoom_content = zoom_path.read_text(encoding="utf-8")
        zoom_script = f"<script>\n{zoom_content}\n</script>"

    legend_js = """
    <script>
    document.querySelectorAll('.legend-icon, .legend-label').forEach(el => {
      el.addEventListener('click', () => {
        const target = el.dataset.target;
        const elems = document.querySelectorAll('.' + target);
        elems.forEach(e => {
          e.style.display = e.style.display === 'none' ? '' : 'none';
        });
      });
    });
    </script>
    """

    # MathJax — inject only when the SVG contains $...$ math text
    mathjax_script = ""
    if 'data-has-math="true"' in svg_string:
        mathjax_script = (
            '<script>MathJax={tex:{inlineMath:[["$","$"]]}}</script>\n'
            '<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>\n'
        )

    brush_script = ""
    brush_path = Path(__file__).parent / "assets" / "brush.js"
    if brush_path.exists():
        brush_content = brush_path.read_text(encoding="utf-8")
        brush_script = f"<script>\n{brush_content}\n</script>"

    a11y_path = Path(__file__).parent / "assets" / "accessibility.js"
    a11y_script = ""
    if a11y_path.exists():
        a11y_content = a11y_path.read_text(encoding="utf-8")
        a11y_script = f"<script>\n{a11y_content}\n</script>"

    return (
        html_content
        .replace("{{svg_content}}", svg_string)
        .replace("{{extra_scripts}}", mathjax_script + zoom_script + brush_script + a11y_script + legend_js)
    )


def wrap_svg_canvas(svg_content: str, width: int = 640, height: int = 480,
                    has_math: bool = False) -> str:
    """
    Wrap raw SVG elements in a full <svg> root element.

    Each SVG gets a collision-resistant UUID id (no module-level counter
    that grows unboundedly in long-running Jupyter sessions).

    Args:
        svg_content (str): Inner SVG markup.
        width (int):       Canvas width in pixels.
        height (int):      Canvas height in pixels.
        has_math (bool):   When True, embeds a MathJax data attribute so
                           wrap_svg_with_template injects the CDN script.

    Returns:
        str: Complete SVG document string.
    """
    import itertools as _itertools
    # Monotonic integer counter so IDs are unique and match glyphx-chart-\d+
    if not hasattr(wrap_svg_canvas, "_counter"):
        wrap_svg_canvas._counter = _itertools.count(1)
    chart_id = f"glyphx-chart-{next(wrap_svg_canvas._counter)}"
    math_attr = ' data-has-math="true"' if has_math else ""
    return (
        f'<svg id="{chart_id}" data-glyphx="true"{math_attr} '
        f'width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}">{svg_content}</svg>'
    )


def write_svg_file(svg_string: str, filename: str, **kwargs):
    """
    Save a chart to file.  Supports .svg, .html, .png, and .jpg.

    PNG/JPG export requires the optional ``cairosvg`` package::

        pip install cairosvg

    Args:
        svg_string (str): Raw SVG content.
        filename (str): Output path.  Extension determines format.

    Raises:
        ValueError: For unsupported extensions.
        RuntimeError: If cairosvg is not installed when exporting raster images.
    """
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".html":
        content = wrap_svg_with_template(svg_string)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

    elif ext == ".svg":
        with open(filename, "w", encoding="utf-8") as f:
            f.write(svg_string)

    elif ext in {".png", ".jpg", ".jpeg"}:
        try:
            import cairosvg
        except ImportError:
            raise RuntimeError(
                "PNG/JPG export requires cairosvg.  Install it with:\n"
                "    pip install cairosvg"
            )
        # dpi may be passed as a keyword via write_svg_file(... dpi=192)
        _dpi = kwargs.get("dpi", 96)
        _scale = _dpi / 96.0   # cairosvg scale=2 doubles resolution
        cairosvg.svg2png(bytestring=svg_string.encode(),
                         write_to=filename, scale=_scale)

    else:
        raise ValueError(
            f"Unsupported file extension '{ext}'.  "
            "Use .svg, .html, .png, or .jpg."
        )


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def in_jupyter() -> bool:
    """Return True if executing inside a Jupyter kernel."""
    try:
        from IPython import get_ipython
        return "IPKernelApp" in get_ipython().config
    except Exception:
        return False


def in_cli_or_ide() -> bool:
    """Return True if NOT inside a Jupyter kernel."""
    return not in_jupyter()


def render_cli(svg_string: str):
    """
    Write an SVG to a temporary HTML file and open it in the system browser.

    Uses NamedTemporaryFile to avoid the race condition in the deprecated
    ``tempfile.mktemp``.

    Args:
        svg_string (str): Raw SVG markup to embed.
    """
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".html", mode="w", encoding="utf-8"
    ) as f:
        f.write(f"<html><body>{svg_string}</body></html>")
        path = f.name
    webbrowser.open(f"file://{path}")


# ---------------------------------------------------------------------------
# Legend rendering
# ---------------------------------------------------------------------------

# Fixed gutter width reserved for outside-right legends.
# Must be wide enough for typical labels; figure.py uses this to shrink axes.
LEGEND_GUTTER = 130


def legend_pixel_width(series_list, padding=10, icon_size=12, text_gap=8):
    """Return the pixel width a legend block would occupy for the given series."""
    normalized = [
        (item[0] if isinstance(item, tuple) else item)
        for item in series_list
        if getattr(item[0] if isinstance(item, tuple) else item, "label", None)
    ]
    if not normalized:
        return 0
    max_label_len = max(len(s.label) for s in normalized)
    return icon_size + text_gap + max_label_len * 7 + 2 * padding


def draw_legend(
    series_list,
    position="top-right",
    font="sans-serif",
    text_color="#000",
    fig_width=640,
    fig_height=480,
    cell_width=None,
    cell_height=None,
):
    """
    Render a dynamic SVG legend block for a list of series.

    Only series with a non-empty ``.label`` attribute are included.

    Args:
        series_list (list): Series objects or ``(series, use_y2)`` tuples.
        position (str): One of top-right, top-left, bottom-right, bottom-left,
                        top, bottom, left, right.
        font (str): CSS font-family string.
        text_color (str): SVG fill color for label text.
        fig_width (int): Figure canvas width (used for positioning).
        fig_height (int): Figure canvas height.
        cell_width (int | None): Subplot cell width (overrides fig_width).
        cell_height (int | None): Subplot cell height (overrides fig_height).

    Returns:
        str: SVG ``<g>`` element containing the legend, or empty string if
             no labelled series exist.
    """
    # Unwrap (series, use_y2) tuples and keep only labelled series
    normalized = []
    for item in series_list:
        s = item[0] if isinstance(item, tuple) else item
        if getattr(s, "label", None):
            normalized.append(s)

    if not normalized:
        return ""

    spacing    = 22
    padding    = 10
    icon_size  = 12
    text_gap   = 8

    width  = cell_width  if cell_width  else fig_width
    height = cell_height if cell_height else fig_height

    # Estimate legend box dimensions using per-character width lookup.
    # Average proportional-font character width ≈ 7px at font-size 12.
    max_label_len   = max(len(s.label) for s in normalized)
    label_px_width  = max_label_len * 7
    legend_width    = icon_size + text_gap + label_px_width + 2 * padding
    legend_height   = len(normalized) * spacing + 2 * padding

    # Determine top-left corner of the legend box
    x = y = padding
    if position in ("outside-right", "right-of"):
        # Legend sits in the right margin (gutter) inside the full canvas.
        # figure.py shrinks the axes to LEGEND_GUTTER pixels narrower,
        # so the legend at x = width + gap never overlaps chart data.
        x = width + 8
        y = max(8, (height - legend_height) // 2)
    elif position == "top-right":
        x = width - legend_width - padding
    elif position == "bottom-right":
        x = width  - legend_width - padding
        y = height - legend_height - padding
    elif position == "bottom-left":
        y = height - legend_height - padding
    elif position == "top":
        x = (width - legend_width) // 2
    elif position == "bottom":
        x = (width - legend_width) // 2
        y = height - legend_height - padding
    elif position == "left":
        y = (height - legend_height) // 2
    elif position == "right":
        x = width  - legend_width - padding
        y = (height - legend_height) // 2
    # default / "top-left" → x=padding, y=padding (already set)

    items = []
    for i, s in enumerate(normalized):
        class_name = getattr(s, "css_class", f"series-{i}")
        color      = getattr(s, "color", "#888") or "#888"
        label      = svg_escape(s.label)
        cy         = y + padding + i * spacing

        items.append(
            f'<rect x="{x}" y="{cy}" width="{icon_size}" height="{icon_size}" '
            f'fill="{color}" class="legend-icon" data-target="{class_name}" />'
        )
        items.append(
            f'<text x="{x + icon_size + text_gap}" y="{cy + icon_size - 2}" '
            f'font-size="12" font-family="{font}" fill="{text_color}" '
            f'class="legend-label" data-target="{class_name}">{label}</text>'
        )

    return '<g class="glyphx-legend">\n' + "\n".join(items) + "\n</g>"


# ---------------------------------------------------------------------------
# Arc geometry (for pie charts)
# ---------------------------------------------------------------------------

def describe_arc(cx, cy, r, start_angle, end_angle):
    """
    Build an SVG arc path string for a pie/donut slice.

    Args:
        cx (float): Circle center X.
        cy (float): Circle center Y.
        r  (float): Radius.
        start_angle (float): Start angle in degrees.
        end_angle   (float): End angle in degrees.

    Returns:
        str: SVG ``d`` attribute value for a filled arc slice.
    """
    start_rad = math.radians(start_angle)
    end_rad   = math.radians(end_angle)

    x_start = cx + r * math.cos(start_rad)
    y_start = cy + r * math.sin(start_rad)
    x_end   = cx + r * math.cos(end_rad)
    y_end   = cy + r * math.sin(end_rad)

    large_arc = 1 if (end_angle - start_angle) > 180 else 0

    return (
        f"M {cx},{cy} "
        f"L {x_start},{y_start} "
        f"A {r},{r} 0 {large_arc},1 {x_end},{y_end} "
        "Z"
    )


# ---------------------------------------------------------------------------
# Self-contained / shareable HTML
# ---------------------------------------------------------------------------

def make_shareable_html(svg_string: str, title: str = "GlyphX Chart") -> str:
    """
    Build a fully self-contained HTML document with all JavaScript inlined.

    The output has zero external dependencies and renders correctly in:
    - Email clients (tested in Gmail, Outlook web)
    - Confluence / Notion embeds
    - GitHub Pages / static hosts
    - Air-gapped / offline environments

    Args:
        svg_string (str): Raw SVG markup.
        title (str): ``<title>`` tag value.

    Returns:
        str: Complete, standalone HTML document string.
    """
    import datetime

    assets_dir = Path(__file__).parent / "assets"

    def _read_js(name: str) -> str:
        p = assets_dir / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    tooltip_js = _read_js("tooltip.js")   # legacy path — already in template
    zoom_js    = _read_js("zoom.js")
    brush_js   = _read_js("brush.js")
    export_js  = _read_js("export.js")

    # Read template and replace placeholders
    template_path = assets_dir / "responsive_template.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template: {template_path}")

    html = template_path.read_text(encoding="utf-8")

    # Replace title
    html = html.replace("<title>GlyphX Chart</title>", f"<title>{html_escape(title)}</title>")

    # Inline all JS into {{extra_scripts}}
    a11y_js = _read_js("accessibility.js")
    inlined_scripts = "\n".join(filter(None, [
        f"<script>\n{zoom_js}\n</script>"  if zoom_js  else "",
        f"<script>\n{brush_js}\n</script>" if brush_js else "",
        f"<script>\n{a11y_js}\n</script>"  if a11y_js  else "",
        f"<script>\n{export_js}\n</script>" if export_js else "",
    ]))

    # Metadata comment
    meta = (
        f"<!-- GlyphX self-contained export\n"
        f"     Generated : {datetime.datetime.utcnow().isoformat(timespec='seconds')}Z\n"
        f"     Zero external dependencies — share freely\n-->\n"
    )

    html = (
        html
        .replace("{{svg_content}}",  svg_string)
        .replace("{{extra_scripts}}", inlined_scripts)
    )

    return meta + html


def html_escape(text: str) -> str:
    """Alias for ``html.escape`` for use within this module."""
    import html as _html
    return _html.escape(str(text))
