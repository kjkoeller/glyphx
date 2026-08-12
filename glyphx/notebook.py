"""
Notebook integration.

GlyphX figures should render when they are the last expression in a cell, the
way a matplotlib figure or a Plotly figure does, without anyone calling
``.show()``. That works through the display protocols the host understands:

* Jupyter, JupyterLab, VS Code, Colab, and nbconvert read ``_repr_html_`` and
  ``_repr_mimebundle_`` off the returned object.
* marimo reads ``_repr_html_`` too -- it does not use IPython at all, so an
  IPython-only code path silently falls through to opening a browser tab.

Both are covered by emitting an HTML fragment, so this module only has to
decide *what* to emit and to recognise where it is running.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

#: Marks the inline script so it is only sent to the front end once per page.
_ASSET_FLAG = "window.glyphxInitChart"


@lru_cache(maxsize=1)
def _notebook_js() -> str:
    """Return the inline notebook script, or an empty string if missing."""
    path = Path(__file__).parent / "assets" / "notebook.js"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:      # pragma: no cover - packaging accident
        return ""


def in_marimo() -> bool:
    """
    True when running inside a marimo notebook.

    marimo sets ``__name__`` on its cells and imports its own runtime; the
    presence of a running kernel context is the reliable signal.
    """
    if "marimo" not in sys.modules:
        return False
    try:
        from marimo._runtime.context import get_context

        get_context()
        return True
    except Exception:
        return False


def in_ipython_kernel() -> bool:
    """
    True inside a Jupyter/Colab/VS Code kernel, not a plain IPython terminal.

    A terminal REPL cannot render HTML, so it should still fall through to a
    browser tab.
    """
    if "IPython" not in sys.modules:
        return False
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is None:
            return False
        return type(ip).__name__ in {
            "ZMQInteractiveShell",       # Jupyter, JupyterLab, VS Code
            "Shell",                     # Google Colab
        }
    except Exception:
        return False


def in_notebook() -> bool:
    """True when a rich HTML display surface is available."""
    return in_marimo() or in_ipython_kernel()


def environment() -> str:
    """
    Return the display environment: ``marimo``, ``jupyter``, or ``script``.

    Useful for debugging a figure that is not showing up where expected.
    """
    if in_marimo():
        return "marimo"
    if in_ipython_kernel():
        return "jupyter"
    return "script"


def isolate_in_iframe(fragment: str, height: int, width: int | None = None) -> str:
    """
    Wrap an HTML fragment in a correctly sized ``srcdoc`` iframe.

    marimo sandboxes any ``_repr_html_`` output containing an inline
    ``<script>`` into an iframe of its own, at a fixed 400px height -- which
    clips anything taller, and every default GlyphX figure is 480px. Building
    the iframe here instead lets the height match the figure.

    marimo decides whether to wrap by looking for a literal ``"<script"`` in
    the string. Inside ``srcdoc`` the fragment is HTML-escaped, so the marker
    is not present and the output is not wrapped a second time.

    Args:
        fragment (str): The HTML to isolate.
        height (int): Figure height in pixels.
        width (int | None): Figure width, if a fixed width is wanted.

    Returns:
        str: An iframe element containing the fragment.
    """
    from html import escape

    # A little vertical slack for the iframe's own margins.
    box_height = int(height) + 20
    box_width = f"{int(width) + 20}px" if width else "100%"
    return (
        f'<iframe srcdoc="{escape(fragment, quote=True)}" '
        f'width="{box_width}" height="{box_height}" '
        f'style="border:none;max-width:100%" '
        f'sandbox="allow-scripts" '
        f'title="GlyphX chart"></iframe>'
    )


def inline_html(svg: str, chart_id: str, interactive: bool = True) -> str:
    """
    Wrap a rendered SVG as an HTML fragment for a notebook output cell.

    A fragment, not a document: no ``<html>`` or ``<body>``, since the host
    injects this into an existing page.

    Args:
        svg (str): The rendered ``<svg>`` element.
        chart_id (str): The SVG's ``id``, used to scope the initialiser.
        interactive (bool): Attach tooltips and legend toggling.

    Returns:
        str: An HTML fragment.
    """
    block = [
        '<div class="glyphx-output" style="max-width:100%;overflow:auto">',
        svg,
        "</div>",
    ]

    if interactive:
        script = _notebook_js()
        if script:
            block.append(
                "<script>\n"
                # Send the script itself only once per page; every later cell
                # reuses the function it defined.
                f"if (!{_ASSET_FLAG}) {{\n{script}\n}}\n"
                f"if ({_ASSET_FLAG}) {_ASSET_FLAG}({chart_id!r});\n"
                "</script>"
            )

    return "\n".join(block)
