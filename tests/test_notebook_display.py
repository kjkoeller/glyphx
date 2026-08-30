"""
Notebook display integration.

A figure should render when it is the last expression in a cell, the way
matplotlib and Plotly figures do. That means implementing the display
protocols Jupyter and marimo look for, and emitting a fragment rather than a
whole HTML document.
"""

from __future__ import annotations

import re

import pytest

from glyphx import Figure
from glyphx import notebook as nbmod


@pytest.fixture
def fig():
    return (
        Figure(auto_display=False, title="Inline")
        .line([1, 2, 3], [1.0, 2.0, 3.0], label="alpha")
        .line([1, 2, 3], [6.0, 5.0, 4.0], label="beta")
    )


# ---------------------------------------------------------------------------
# Display protocol
# ---------------------------------------------------------------------------

def test_figure_implements_repr_html(fig):
    """Without this, a bare `fig` in a cell prints <Figure object at 0x...>."""
    html = fig._repr_html_()
    assert "<svg" in html
    assert html.strip()


def test_repr_html_is_a_fragment_not_a_document(fig):
    """The host injects this into an existing page."""
    html = fig._repr_html_().lower()
    for tag in ("<html", "<head", "<body", "<!doctype"):
        assert tag not in html, f"{tag} must not appear in an inline fragment"


def test_repr_mimebundle_offers_html_and_svg(fig):
    bundle = fig._repr_mimebundle_()
    assert "text/html" in bundle
    assert "image/svg+xml" in bundle
    assert bundle["image/svg+xml"].lstrip().startswith("<svg")


def test_repr_mimebundle_honours_include_and_exclude(fig):
    assert set(fig._repr_mimebundle_(include={"text/html"})) == {"text/html"}
    assert "text/html" not in fig._repr_mimebundle_(exclude={"text/html"})


def test_repr_svg_is_a_bare_svg(fig):
    assert fig._repr_svg_().lstrip().startswith("<svg")


def test_fragment_initialises_only_its_own_chart(fig):
    """A document-wide scan would rebind charts in every earlier cell."""
    html = fig._repr_html_()
    chart_id = re.search(r'id="(glyphx-chart-[^"]+)"', html).group(1)
    assert f"glyphxInitChart('{chart_id}')" in html


def test_fragment_loads_the_script_only_once_per_page(fig):
    """Later cells reuse the function the first one defined."""
    html = fig._repr_html_()
    assert "if (!window.glyphxInitChart)" in html


def test_interactive_can_be_switched_off(fig):
    html = fig.to_html_fragment(interactive=False)
    assert "<svg" in html
    assert "<script" not in html


# ---------------------------------------------------------------------------
# show() must not render twice
# ---------------------------------------------------------------------------

def test_show_suppresses_the_duplicate_repr(fig, monkeypatch):
    """
    ``fig.show()`` returns self, so a cell ending in it would render the
    chart once from show() and again from the returned value.
    """
    monkeypatch.setattr(nbmod, "in_ipython_kernel", lambda: True)
    monkeypatch.setattr(nbmod, "in_marimo", lambda: False)

    displayed = []
    monkeypatch.setattr(Figure, "_current_execution", lambda self: ("test", 1))

    class _HTML:
        def __init__(self, data):
            self.data = data

    import sys
    import types

    module = types.ModuleType("IPython.display")
    module.HTML = _HTML
    module.display = lambda obj: displayed.append(obj)
    monkeypatch.setitem(sys.modules, "IPython.display", module)

    fig.show()
    assert len(displayed) == 1, "show() must display exactly once"
    assert fig._repr_html_() == "", "the returned figure must not render again"
    assert fig._repr_svg_() is None
    assert fig._repr_mimebundle_() == {"text/plain": ""}


def test_suppression_expires_with_the_execution(fig, monkeypatch):
    """The same figure shown again in a later cell must still render."""
    counter = {"n": 1}
    monkeypatch.setattr(
        Figure, "_current_execution", lambda self: ("test", counter["n"])
    )
    fig._shown_at = ("test", 1)
    assert fig._repr_html_() == ""

    counter["n"] = 2
    assert "<svg" in fig._repr_html_(), "a later cell must render normally"


def test_suppression_is_not_consumed_by_the_first_reader(fig, monkeypatch):
    """
    IPython asks several formatters in turn.

    Clearing the marker on the first read let the next formatter render the
    duplicate anyway.
    """
    monkeypatch.setattr(Figure, "_current_execution", lambda self: ("test", 1))
    fig._shown_at = ("test", 1)
    assert fig._repr_html_() == ""
    assert fig._repr_html_() == ""
    assert fig._repr_svg_() is None


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def test_environment_reports_script_outside_a_notebook():
    assert nbmod.environment() == "script"
    assert nbmod.in_notebook() is False


def test_environment_detection_is_exclusive(monkeypatch):
    monkeypatch.setattr(nbmod, "in_marimo", lambda: True)
    monkeypatch.setattr(nbmod, "in_ipython_kernel", lambda: False)
    assert nbmod.environment() == "marimo"

    monkeypatch.setattr(nbmod, "in_marimo", lambda: False)
    monkeypatch.setattr(nbmod, "in_ipython_kernel", lambda: True)
    assert nbmod.environment() == "jupyter"


def test_detection_does_not_import_optional_packages(monkeypatch):
    """Probing must not drag IPython or marimo into a plain script."""
    import sys

    monkeypatch.delitem(sys.modules, "marimo", raising=False)
    monkeypatch.delitem(sys.modules, "IPython", raising=False)
    nbmod.in_marimo()
    nbmod.in_ipython_kernel()
    assert "marimo" not in sys.modules
    assert "IPython" not in sys.modules


# ---------------------------------------------------------------------------
# marimo iframe sizing
# ---------------------------------------------------------------------------

def test_marimo_output_is_wrapped_in_a_sized_iframe(fig, monkeypatch):
    """
    marimo sandboxes script-bearing HTML at a fixed 400px, which clips a
    480px chart. Building the iframe here matches it to the figure.
    """
    monkeypatch.setattr(nbmod, "in_marimo", lambda: True)
    html = fig.to_html_fragment()
    assert html.startswith("<iframe")
    assert f'height="{fig.height + 20}"' in html


def test_marimo_wrapper_avoids_a_second_sandbox(fig, monkeypatch):
    """
    marimo wraps when it finds a literal '<script' in the output.

    Inside srcdoc the fragment is escaped, so the marker is absent and the
    output is not double-wrapped.
    """
    monkeypatch.setattr(nbmod, "in_marimo", lambda: True)
    html = fig.to_html_fragment()
    assert "<script" not in html
    assert "&lt;script" in html


def test_iframe_sizing_helper():
    out = nbmod.isolate_in_iframe("<p>hi</p>", height=300, width=500)
    assert 'height="320"' in out
    assert 'width="520px"' in out
    assert "srcdoc=" in out


def test_non_marimo_output_is_not_iframed(fig):
    assert not fig.to_html_fragment().startswith("<iframe")


# ---------------------------------------------------------------------------
# End to end, in a real kernel
# ---------------------------------------------------------------------------

def _outputs(cells):
    """Flatten notebook outputs, failing loudly on execution errors."""
    results = []
    for index, cell in enumerate(cells):
        for out in cell.get("outputs", []):
            if out.output_type == "error":
                raise AssertionError(
                    f"cell {index} raised {out.ename}: {out.evalue}"
                )
            results.append((index, out))
    return results


@pytest.mark.slow
def test_renders_in_a_real_jupyter_kernel(tmp_path):
    """
    The display protocol is easy to get subtly wrong.

    IPython asks several formatters in turn and merges the results, which is
    exactly where the duplicate-render bug lived, so this drives a real
    kernel rather than calling the dunders directly.
    """
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")

    from pathlib import Path

    repo = str(Path(__file__).resolve().parent.parent)
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(
            f"import sys; sys.path.insert(0, {repo!r})\n"
            "import glyphx\nfrom glyphx import Figure"
        ),
        nbformat.v4.new_code_cell(
            "fig = Figure(auto_display=False, title='Inline')"
            ".line([1,2,3],[1.,2.,3.], label='a')\nfig"
        ),
        nbformat.v4.new_code_cell("fig.show()"),
        nbformat.v4.new_code_cell(
            "from glyphx.notebook import environment; print(environment())"
        ),
    ]

    client = nbclient.NotebookClient(nb, timeout=180, kernel_name="python3",
                                     resources={"metadata": {"path": str(tmp_path)}})
    client.execute()
    outputs = _outputs(nb.cells)

    # Cell 1: a bare figure renders through the display protocol.
    bare = [o for i, o in outputs if i == 1 and o.output_type == "execute_result"]
    assert bare, "a bare figure produced no output"
    assert "<svg" in bare[0]["data"].get("text/html", "")

    # Cell 2: show() renders exactly one chart, not two.
    charts = [
        o for i, o in outputs
        if i == 2 and "<svg" in o.get("data", {}).get("text/html", "")
    ]
    assert len(charts) == 1, f"show() produced {len(charts)} charts, expected 1"

    # Cell 3: the environment is detected as a notebook, not a script.
    streams = [o for i, o in outputs if i == 3 and o.output_type == "stream"]
    assert streams and streams[0]["text"].strip() == "jupyter"


@pytest.mark.slow
def test_marimo_formatter_accepts_the_figure():
    """marimo resolves a formatter from _repr_html_ and must find ours."""
    pytest.importorskip("marimo")
    from marimo._output.formatting import get_formatter

    figure = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0], label="a")
    formatter = get_formatter(figure)
    assert formatter is not None, "marimo could not format a GlyphX figure"

    mime, data = formatter(figure)
    assert mime == "text/html"
    assert "srcdoc" in data or "<svg" in data
