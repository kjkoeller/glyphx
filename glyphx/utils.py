from __future__ import annotations

"""
GlyphX utility functions: SVG helpers, display detection, legend rendering.
"""

import html
import math
import os
import tempfile
import webbrowser
from pathlib import Path

# Numeric helpers

#: Decimal places retained in emitted SVG pixel coordinates. Two is below
#: the resolution of any real display and typically cuts document size by a
#: third on point-dense charts.
SVG_PRECISION = 2


def stable_id(*parts, length: int = 12) -> str:
    """
    Return a short, deterministic id derived from ``parts``.

    Used for SVG element ids and CSS class names.  Identical input always
    yields the same id, so rendering the same figure twice produces
    byte-identical SVG.

    Args:
        *parts: Any values; their ``str()`` forms are hashed.
        length (int): Number of hex characters to return.

    Returns:
        str: A lowercase hex string of ``length`` characters.
    """
    import hashlib

    digest = hashlib.blake2b(
        "\x1f".join(str(p) for p in parts).encode("utf-8"),
        digest_size=max(1, length // 2 + 1),
    )
    return digest.hexdigest()[:length]


def has_data(value) -> bool:
    """
    Return True if ``value`` is a non-empty sequence or array.

    Plain truthiness cannot be used on NumPy arrays or pandas Series --
    their ``__bool__`` raises ``ValueError`` for length > 1 -- so every
    "is this series empty?" check in GlyphX goes through this helper.

    Args:
        value: Any object, typically a list, tuple, ndarray, or Series.

    Returns:
        bool: True if the object has a length greater than zero, or is
        truthy but has no length at all.
    """
    if value is None:
        return False
    try:
        return len(value) > 0
    except TypeError:
        return bool(value)


def check_xy_lengths(x, y, series_name: str) -> None:
    """
    Raise if paired X and Y data have different lengths.

    Silently zipping mismatched sequences truncates to the shorter one, so a
    typo drops data from the chart with no indication that anything is wrong.

    Args:
        x: X values.
        y: Y values.
        series_name (str): Class name, used in the error message.

    Raises:
        ValueError: If both are sized and their lengths differ.
    """
    try:
        len_x, len_y = len(x), len(y)
    except TypeError:
        return  # unsized input (e.g. a generator); nothing to compare
    if len_x != len_y:
        raise ValueError(
            f"{series_name}: x and y must be the same length "
            f"(got len(x)={len_x}, len(y)={len_y})."
        )


def is_finite(value) -> bool:
    """
    Return True if ``value`` is a real, plottable number.

    ``None``, NaN, and infinities are rejected so they never reach the SVG
    output, where they would produce invalid coordinates.  Non-numeric
    values (categorical X labels) are treated as plottable.

    Args:
        value: A candidate coordinate.

    Returns:
        bool: True if the value can be scaled to a pixel position.
    """
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    return True


def assign_theme_colors(series_list, theme) -> None:
    """
    Give un-colored series their color from the active theme's palette.

    Every series defaulted to ``#1f77b4`` (or, for pie/donut/grouped/stacked,
    to a hardcoded copy of the light palette) at construction time, before it
    knew which figure it belonged to.  The result was that no theme's
    ``colors`` list was ever used -- three lines on one chart came out
    identical, and ``theme="colorblind"`` produced the same colors as
    ``"default"``.

    A color the caller passed explicitly is always left alone.  Colormap-driven
    series (treemap, raincloud, bump chart) opt out by not declaring a palette
    attribute.  Safe to call more than once: assignment is by position, so a
    second pass produces the same result.

    Args:
        series_list: Series, or ``(series, use_y2)`` tuples.
        theme:       Theme dict; a missing or empty ``colors`` is a no-op.
    """
    palette = (theme or {}).get("colors")
    if not palette:
        return

    i = 0
    for entry in series_list:
        series = entry[0] if isinstance(entry, tuple) else entry

        attr = getattr(series, "_palette_attr", None)
        if attr and not getattr(series, "_explicit_palette", True):
            current = getattr(series, attr) or []
            setattr(series, attr,
                    [palette[k % len(palette)] for k in range(len(current))])
            continue

        if not hasattr(series, "color"):
            continue
        if getattr(series, "_explicit_color", True):
            continue
        series.color = palette[i % len(palette)]
        i += 1


def drop_index(value):
    """
    Strip the index from a pandas Series or Index, leaving the values.

    Everything in the rendering path indexes coordinates positionally --
    ``s.x[0]``, ``self.x[i]``, ``xs[-1]``.  On a pandas Series those are *label*
    lookups, so a filtered frame (``df[df.g == "b"]``, whose index might be
    ``[1, 3]``) raises ``KeyError: 0`` at render time rather than plotting.
    Converting once at construction makes every downstream access positional.

    Lists, tuples and NumPy arrays are returned untouched, so this costs
    nothing for the common cases and never copies a large array.

    Args:
        value: Candidate series data.

    Returns:
        The values as a NumPy array if ``value`` was pandas-indexed, else
        ``value`` unchanged.
    """
    if value is None:
        return None
    # Duck-typed rather than importing pandas: glyphx does not depend on it at
    # import time, and this also catches index-carrying pandas-likes.
    if not (hasattr(value, "to_numpy") and hasattr(value, "index")):
        return value
    try:
        # Numeric and boolean dtypes keep the NumPy fast path.  Anything else
        # -- datetime64, categorical, object -- goes to a Python list, because
        # to_numpy() on a datetime Series yields datetime64 scalars and the
        # date-axis detection only recognises datetime/Timestamp objects.
        kind = getattr(getattr(value, "dtype", None), "kind", "O")
        return value.to_numpy() if kind in "biufc" else value.tolist()
    except Exception:
        return value


def as_seq(value) -> list:
    """``value`` as a list, or ``[]`` if it is None or empty.

    Array-safe stand-in for the ``value or []`` idiom.
    """
    return list(value) if has_data(value) else []


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


# SVG escaping

def wrap_tick_label(label, max_chars, max_lines: int = 2) -> list:
    """
    Word-wrap a tick label to at most ``max_lines`` lines of roughly
    ``max_chars`` characters each.

    Character-count based, like every other width estimate in this codebase
    -- SVG text has no font-metrics API to query, so
    ``Axes._should_rotate_xlabels`` uses the same kind of estimate for its
    rotate-vs-not decision.  This is the wrap alternative: a label too long
    to fit at the current tick spacing goes to two lines instead of forcing
    every label on the axis to rotate.

    A single word longer than ``max_chars`` is hard-split rather than left
    to overflow one line.  If content remains after ``max_lines``, the last
    line is truncated with an ellipsis rather than silently dropped.

    Args:
        label:     Text to wrap. Non-strings are stringified first.
        max_chars: Approximate character budget per line.
        max_lines: Maximum lines to return.

    Returns:
        list[str]: One or more lines, never more than ``max_lines``.
    """
    max_chars = max(1, int(max_chars))
    words = str(label).split()
    if not words:
        return [str(label)]

    lines: list = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        while len(current) > max_chars:      # hard-split an overlong token
            lines.append(current[:max_chars])
            current = current[max_chars:]
    if current:
        lines.append(current)

    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    last = kept[-1]
    kept[-1] = (last[:max(0, max_chars - 1)] + "…"
               if len(last) >= max_chars else last + "…")
    return kept


def svg_label(text) -> str:
    """
    Prepare a user-supplied label for an SVG ``<text>`` element.

    Escapes the text, and renders any ``$...$`` span as real SVG markup via
    :mod:`glyphx.mathtext`.  Every label site goes through this so math works
    the same way in titles, axis labels, tick labels, legends, and
    annotations.

    Args:
        text: The label.

    Returns:
        str: Markup safe to place inside a ``<text>`` element.
    """
    from .mathtext import render

    return render("" if text is None else text)


def svg_escape(text):
    """Escape a string so it is safe inside SVG text or an attribute."""
    return html.escape(str(text), quote=True)


# SVG/HTML wrapping

def _strip_script_tags(js: str) -> str:
    """
    Remove any wrapping ``<script>`` tags from a JS asset.

    Assets are inlined as ``<script>{js}</script>``.  If the file already
    carries its own tags, the inner ``</script>`` closes the block early and
    the remainder of the file spills into the document as text -- which kills
    that script and every one after it.  Two shipped assets had this problem,
    so the loader now guards against it rather than trusting the files.

    Args:
        js (str): Raw asset contents.

    Returns:
        str: The JavaScript with any surrounding script tags removed.
    """
    import re as _re

    js = _re.sub(r"^\s*<script[^>]*>", "", js)
    js = _re.sub(r"</script>\s*$", "", js)
    return js.strip()


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
        zoom_content = _strip_script_tags(zoom_path.read_text(encoding="utf-8"))
        zoom_script = f"<script>\n{zoom_content}\n</script>"

    # Legend toggling lives in assets/legend.js so both export paths get the
    # same keyboard handling and ARIA state. The previous inline copy was
    # click-only, had no focus handling, and toggled inline display styles.
    legend_path = Path(__file__).parent / "assets" / "legend.js"
    legend_js = ""
    if legend_path.exists():
        legend_js = (
            "<script>\n"
            + _strip_script_tags(legend_path.read_text(encoding="utf-8"))
            + "\n</script>"
        )

    # Cross-chart filtering. Inert unless a chart on the page carries
    # data-glyphx-crossfilter, so it costs nothing when unused.
    xfilter_path = Path(__file__).parent / "assets" / "crossfilter.js"
    xfilter_js = ""
    if xfilter_path.exists():
        xfilter_js = (
            "<script>\n"
            + _strip_script_tags(xfilter_path.read_text(encoding="utf-8"))
            + "\n</script>"
        )

    # MathJax used to be injected when the SVG still held raw $...$ text.
    # It never worked: MathJax does not typeset inside an <svg> element, so
    # the labels showed the literal LaTeX in every format. Math is now
    # rendered to tspans in Python (glyphx/mathtext.py), which works in SVG,
    # PNG, PDF, and HTML alike, so no front-end typesetter is needed.
    mathjax_script = ""

    brush_script = ""
    brush_path = Path(__file__).parent / "assets" / "brush.js"
    if brush_path.exists():
        brush_content = _strip_script_tags(brush_path.read_text(encoding="utf-8"))
        brush_script = f"<script>\n{brush_content}\n</script>"

    interact_script = ""
    interact_path = Path(__file__).parent / "assets" / "interact.js"
    if interact_path.exists():
        interact_content = _strip_script_tags(interact_path.read_text(encoding="utf-8"))
        interact_script = f"<script>\n{interact_content}\n</script>"

    a11y_path = Path(__file__).parent / "assets" / "accessibility.js"
    a11y_script = ""
    if a11y_path.exists():
        a11y_content = _strip_script_tags(a11y_path.read_text(encoding="utf-8"))
        a11y_script = f"<script>\n{a11y_content}\n</script>"

    return (
        html_content
        .replace("{{svg_content}}", svg_string)
        .replace("{{extra_scripts}}", mathjax_script + zoom_script + brush_script
                 + interact_script + a11y_script + legend_js + xfilter_js)
    )


def wrap_svg_canvas(svg_content: str, width: int = 640, height: int = 480,
                    has_math: bool = False, crossfilter: bool = False) -> str:
    """
    Wrap raw SVG elements in a full <svg> root element.

    The chart id is a hash of the SVG content and canvas size, so the same
    figure always renders byte-identical output.  A UUID would be equally
    collision-resistant, but it made every render differ from the last --
    which defeats caching, makes diffs unreadable, and rules out golden-file
    tests.  Distinct charts still get distinct ids because distinct content
    hashes differently.

    Args:
        svg_content (str): Inner SVG markup.
        width (int):       Canvas width in pixels.
        height (int):      Canvas height in pixels.
        has_math (bool):   When True, embeds a MathJax data attribute so
                           wrap_svg_with_template injects the CDN script.
        crossfilter (bool): When True, marks the root so crossfilter.js
                           includes this chart. Charts without the marker
                           are left alone, so one page can mix filtered and
                           independent charts.

    Returns:
        str: Complete SVG document string.
    """
    chart_id  = f"glyphx-chart-{stable_id(svg_content, width, height)}"
    math_attr = ' data-has-math="true"' if has_math else ""
    xfilter_attr = ' data-glyphx-crossfilter="true"' if crossfilter else ""
    return (
        f'<svg id="{chart_id}" data-glyphx="true"{math_attr}{xfilter_attr} '
        f'width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}">{svg_content}</svg>'
    )



def wrap_svg_with_css_vars(svg_string: str, light_theme: dict, dark_theme: dict,
                            width: int = 640, height: int = 480) -> str:
    """
    Wrap an SVG in a ``<style>`` block that defines CSS custom properties
    for every theme colour, then swaps them automatically via
    ``@media (prefers-color-scheme: dark)``.

    The SVG itself uses ``var(--glyphx-bg)``, ``var(--glyphx-text)`` etc.
    so no Python re-render is needed when the user switches dark mode.

    Args:
        svg_string:   Raw SVG inner content (without the ``<svg>`` root).
        light_theme:  GlyphX theme dict for light mode.
        dark_theme:   GlyphX theme dict for dark mode.
        width, height: Canvas dimensions.

    Returns:
        Complete ``<svg>`` element with an embedded ``<style>`` block.
    """
    chart_id = f"glyphx-css-{stable_id(svg_string)[:10]}"

    def _props(theme: dict) -> str:
        """Render a theme dict as the CSS custom properties block."""
        mapping = {
            "--glyphx-bg":         theme.get("background", "#ffffff"),
            "--glyphx-text":       theme.get("text_color",  "#000000"),
            "--glyphx-grid":       theme.get("grid_color",  "#dddddd"),
            "--glyphx-axis":       theme.get("axis_color",  "#333333"),
            "--glyphx-accent":     theme.get("colors", ["#1f77b4"])[0],
        }
        return "; ".join(f"{k}: {v}" for k, v in mapping.items())

    light_props = _props(light_theme)
    dark_props  = _props(dark_theme)

    style = (
        f"<style>"
        f"#{chart_id} {{ {light_props} }} "
        f"@media (prefers-color-scheme: dark) {{ #{chart_id} {{ {dark_props} }} }} "
        f"#{chart_id} {{ background: var(--glyphx-bg); }}"
        f"</style>"
    )

    return (
        f'<svg id="{chart_id}" data-glyphx="true" data-responsive="true" '
        f'width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}">'
        + style
        + svg_string
        + "</svg>"
    )


def write_svg_file(svg_string: str, filename: str, **kwargs):
    """
    Save a chart to file.

    ``.svg`` and ``.html`` are written directly.  ``.png``, ``.jpg``,
    ``.webp``, and ``.pdf`` are delegated to :mod:`glyphx.export`, which
    picks whichever rendering backend is installed.

    Args:
        svg_string (str): Raw SVG content.
        filename (str): Output path.  Extension determines format.
        **kwargs: ``dpi`` (int) and ``backend`` (str) are forwarded to the
            raster/PDF backends.

    Raises:
        RuntimeError: If no backend can produce the requested format.
    """
    ext = os.path.splitext(filename)[-1].lower()

    if ext == ".html":
        content = wrap_svg_with_template(svg_string)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

    elif ext == ".svg":
        # A standalone .svg is parsed as XML, and XML defaults to UTF-8 only
        # when nothing says otherwise. Writing the declaration makes the
        # encoding explicit, so the file survives being re-saved by an editor
        # under a different codec and browsers never have to guess.
        with open(filename, "w", encoding="utf-8") as f:
            if not svg_string.lstrip().startswith("<?xml"):
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(svg_string)

    else:
        # Raster and PDF formats go through the backend chain in export.py,
        # which prefers resvg (prebuilt wheels, no system Cairo) and falls
        # back to cairosvg or playwright.
        # ExportError subclasses RuntimeError, and UnsupportedFormatError
        # additionally subclasses ValueError, so both propagate with the
        # exception types callers already catch.
        from .export import render_to_file

        render_to_file(svg_string, filename, dpi=kwargs.get("dpi", 96),
                       backend=kwargs.get("backend"))
        return




# Environment detection

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
    webbrowser.open(Path(path).as_uri())


# Legend rendering

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
    # Average proportional-font character width ~= 7px at font-size 12.
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
    # default / "top-left" -> x=padding, y=padding (already set)

    items = []
    for i, s in enumerate(normalized):
        class_name = getattr(s, "css_class", f"series-{i}")
        color      = getattr(s, "color", "#888") or "#888"
        label      = svg_label(s.label)
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


# Arc geometry (for pie charts)

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


# Self-contained / shareable HTML

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
        """Read one bundled JS asset from the package directory."""
        p = assets_dir / name
        if not p.exists():
            return ""
        return _strip_script_tags(p.read_text(encoding="utf-8"))

    zoom_js     = _read_js("zoom.js")
    brush_js    = _read_js("brush.js")
    interact_js = _read_js("interact.js")
    export_js   = _read_js("export.js")
    legend_js   = _read_js("legend.js")
    xfilter_js  = _read_js("crossfilter.js")

    # Read template and replace placeholders
    template_path = assets_dir / "responsive_template.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Missing template: {template_path}")

    html = template_path.read_text(encoding="utf-8")

    html = html.replace("<title>GlyphX Chart</title>", f"<title>{html_escape(title)}</title>")

    # Inline all JS into {{extra_scripts}}
    a11y_js = _read_js("accessibility.js")
    inlined_scripts = "\n".join(filter(None, [
        f"<script>\n{zoom_js}\n</script>"     if zoom_js     else "",
        f"<script>\n{brush_js}\n</script>"    if brush_js    else "",
        f"<script>\n{interact_js}\n</script>" if interact_js else "",
        f"<script>\n{a11y_js}\n</script>"     if a11y_js     else "",
        f"<script>\n{export_js}\n</script>"   if export_js   else "",
        f"<script>\n{legend_js}\n</script>"   if legend_js   else "",
        f"<script>\n{xfilter_js}\n</script>"  if xfilter_js  else "",
    ]))

    # Metadata comment
    meta = (
        f"<!-- GlyphX self-contained export\n"
        f"     Generated : {datetime.datetime.utcnow().isoformat(timespec='seconds')}Z\n"
        f"     Zero external dependencies -- share freely\n-->\n"
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
