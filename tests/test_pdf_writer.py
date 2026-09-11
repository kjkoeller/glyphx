"""
Dependency-free PDF export.

PDF used to need cairosvg (and the system libcairo behind it) or a headless
browser via Playwright -- neither present in a bare CI container or a fresh
virtualenv, which is exactly where a camera-ready PDF tends to be wanted.
Matplotlib's PDF backend is pure Python; this closes that gap.
"""

import re
import zlib

import pytest

from glyphx import Figure
from glyphx.export import available_backends
from glyphx.pdf_writer import UnsupportedSVGError, svg_to_pdf


def _content_stream(path):
    """The page's decompressed drawing operators."""
    raw = path.read_bytes()
    start = raw.index(b"stream\n") + len(b"stream\n")
    end = raw.index(b"\nendstream", start)
    return zlib.decompress(raw[start:end]).decode("latin-1")


@pytest.fixture
def chart():
    fig = Figure(width=640, height=440, auto_display=False, title="Revenue")
    fig.line([1, 2, 3, 4], [10.0, 25.0, 18.0, 40.0], label="Revenue")
    fig.bar([1, 2, 3, 4], [8.0, 12.0, 11.0, 19.0], label="Costs")
    fig.set_xlabel("Month").set_ylabel("USD")
    return fig


# ---------------------------------------------------------------------------
# No dependencies
# ---------------------------------------------------------------------------

def test_builtin_backend_is_always_available():
    """It is pure standard library, so it can never be missing."""
    assert "builtin" in available_backends()


def test_pdf_prefers_the_builtin_backend():
    from glyphx.export import _PREFERENCE
    assert _PREFERENCE[".pdf"][0] == "builtin"


def test_writer_imports_nothing_outside_the_standard_library():
    import ast
    from pathlib import Path

    import glyphx.pdf_writer as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])

    stdlib = {"math", "re", "xml", "zlib", "__future__"}
    assert imported <= stdlib, f"non-stdlib imports: {imported - stdlib}"


# ---------------------------------------------------------------------------
# Valid PDF
# ---------------------------------------------------------------------------

def test_save_pdf_writes_a_valid_file(chart, tmp_path):
    path = tmp_path / "chart.pdf"
    chart.save(str(path))
    raw = path.read_bytes()
    assert raw.startswith(b"%PDF-1.4")
    assert raw.rstrip().endswith(b"%%EOF")


def test_pdf_parses_in_an_independent_reader(chart, tmp_path):
    pypdf = pytest.importorskip("pypdf")
    path = tmp_path / "chart.pdf"
    chart.save(str(path))

    reader = pypdf.PdfReader(str(path))
    assert len(reader.pages) == 1
    box = reader.pages[0].mediabox
    assert (float(box.width), float(box.height)) == (640.0, 440.0)


def test_output_is_vector_with_selectable_text(chart, tmp_path):
    """
    Not a rasterised image in a wrapper: the text is real text, so it stays
    sharp at any zoom and can be searched and copied.
    """
    pypdf = pytest.importorskip("pypdf")
    path = tmp_path / "chart.pdf"
    chart.save(str(path))

    text = pypdf.PdfReader(str(path)).pages[0].extract_text()
    assert "Revenue" in text
    assert "Month" in text


def test_page_size_follows_the_figure(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    fig = Figure(width=300, height=200, auto_display=False)
    fig.line([1, 2], [1.0, 2.0])
    path = tmp_path / "small.pdf"
    fig.save(str(path))

    box = pypdf.PdfReader(str(path)).pages[0].mediabox
    assert (float(box.width), float(box.height)) == (300.0, 200.0)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def test_shapes_reach_the_content_stream(chart, tmp_path):
    path = tmp_path / "chart.pdf"
    chart.save(str(path))
    ops = _content_stream(path)
    assert " re " in ops, "no rectangles (bars) drawn"
    assert re.search(r"\bl\b", ops), "no lines drawn"
    assert "BT" in ops and "Tj" in ops, "no text drawn"


def test_arcs_become_bezier_curves(tmp_path):
    """
    PDF has no arc operator, so every pie, donut and sunburst slice depends
    on the A-command conversion.
    """
    from glyphx import PieSeries

    fig = Figure(width=400, height=400, auto_display=False)
    fig.add(PieSeries([45.0, 30.0, 25.0], labels=list("abc")))
    path = tmp_path / "pie.pdf"
    fig.save(str(path))

    ops = _content_stream(path)
    assert re.search(r"\bc\b", ops), "arcs were not converted to curves"


def test_rotated_text_uses_the_text_matrix(chart, tmp_path):
    """
    The Y axis label is rotated. Dropping the rotation placed it at the
    rotation origin unrotated, pushing it off the left edge -- it printed
    as "(thousands)" with the start cut off.
    """
    path = tmp_path / "chart.pdf"
    chart.save(str(path))
    assert " Tm" in _content_stream(path), "no text matrix emitted"


def test_bold_text_uses_the_bold_font(chart, tmp_path):
    path = tmp_path / "chart.pdf"
    chart.save(str(path))
    assert "/F2" in _content_stream(path), "title should use Helvetica-Bold"


@pytest.mark.parametrize("builder", [
    lambda f: f.line([1, 2, 3], [1.0, 2.0, 3.0]),
    lambda f: f.bar([1, 2, 3], [1.0, 2.0, 3.0]),
    lambda f: f.scatter([1.0, 2.0], [1.0, 2.0]),
    lambda f: f.pie([3.0, 2.0, 1.0], labels=list("abc")),
    lambda f: f.hist([1.0, 2.0, 2.0, 3.0]),
])
def test_common_chart_types_export(builder, tmp_path):
    fig = Figure(width=400, height=300, auto_display=False)
    builder(fig)
    path = tmp_path / "chart.pdf"
    fig.save(str(path))
    assert path.read_bytes().startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

def test_gradients_are_refused_not_silently_dropped(tmp_path):
    """
    A PDF quietly missing a gradient looks finished while being wrong, and
    the caller has no way to notice.
    """
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
           '<rect x="0" y="0" width="50" height="50" fill="url(#grad)"/></svg>')
    with pytest.raises(UnsupportedSVGError, match="gradient|paint server"):
        svg_to_pdf(svg, str(tmp_path / "x.pdf"))


def test_clip_paths_are_refused(tmp_path):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
           '<rect x="0" y="0" width="9" height="9" clip-path="url(#c)"/></svg>')
    with pytest.raises(UnsupportedSVGError, match="clip-path"):
        svg_to_pdf(svg, str(tmp_path / "x.pdf"))


def test_unknown_path_command_is_refused(tmp_path):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
           '<path d="M0,0 Q5,5 9,0" fill="#000"/></svg>')
    with pytest.raises(UnsupportedSVGError, match="path command"):
        svg_to_pdf(svg, str(tmp_path / "x.pdf"))


# ---------------------------------------------------------------------------
# Details
# ---------------------------------------------------------------------------

def test_non_latin1_text_does_not_crash_the_writer(tmp_path):
    """Base-14 fonts are Latin-1; embedding a Unicode font would mean
    shipping font files, which is the dependency this avoids."""
    fig = Figure(width=300, height=200, auto_display=False, title="温度 chart")
    fig.line([1, 2], [1.0, 2.0])
    path = tmp_path / "cjk.pdf"
    fig.save(str(path))
    assert path.read_bytes().startswith(b"%PDF")


def test_explicit_backend_selection_still_works(chart, tmp_path):
    path = tmp_path / "chart.pdf"
    chart.save(str(path), backend="builtin")
    assert path.read_bytes().startswith(b"%PDF")
