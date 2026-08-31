"""
Two additions: SubplotGrid.save() (the standalone grid had no save method at
all) and Axes.set_tick_wrap() (an alternative to auto-rotation for long
X-tick labels). Both surfaced the same pre-existing bug on the way in: tick
labels were interpolated into SVG unescaped.
"""

import pytest

from glyphx import Figure
from glyphx.figure import SubplotGrid
from glyphx.utils import wrap_tick_label

# ---------------------------------------------------------------------------
# wrap_tick_label
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label, max_chars, expected", [
    ("Q1", 10, ["Q1"]),
    ("New York City", 8, ["New York", "City"]),
    ("", 8, [""]),
])
def test_wrap_tick_label_basic_cases(label, max_chars, expected):
    assert wrap_tick_label(label, max_chars) == expected


def test_wrap_tick_label_hard_splits_an_overlong_word():
    lines = wrap_tick_label("Supercalifragilisticexpialidocious", 8)
    assert len(lines) <= 2
    assert all(len(line) <= 8 for line in lines[:-1])


def test_wrap_tick_label_truncates_with_ellipsis_beyond_max_lines():
    lines = wrap_tick_label("a b c d e f g h", 3, max_lines=2)
    assert len(lines) == 2
    assert lines[-1].endswith("\u2026")


def test_wrap_tick_label_never_exceeds_max_lines():
    for label in ["one two three four five six seven eight",
                  "asupercalifragilisticexpialidociousword" * 3, "x"]:
        assert len(wrap_tick_label(label, 4, max_lines=2)) <= 2


# ---------------------------------------------------------------------------
# set_tick_wrap
# ---------------------------------------------------------------------------

def test_tick_wrap_replaces_rotation():
    """Rotation only ever fires through tight_layout(); wrap must suppress
    it there rather than the two stacking."""
    labels = ["Product Engineering", "Sales & Marketing", "R&D"]

    rotated = Figure(width=500, auto_display=False)
    rotated.bar(labels, [10.0, 20.0, 15.0])
    rotated.tight_layout()
    assert "rotate(" in rotated.render_svg()

    wrapped = Figure(width=500, auto_display=False)
    wrapped.bar(labels, [10.0, 20.0, 15.0])
    wrapped.tight_layout().set_tick_wrap(True)
    svg = wrapped.render_svg()
    assert "rotate(" not in svg
    assert svg.count("<tspan") > 0


def test_tick_wrap_leaves_short_labels_alone():
    fig = Figure(width=900, auto_display=False)
    fig.bar(["Q1", "Q2", "Q3"], [1.0, 2.0, 3.0])
    fig.set_tick_wrap(True)
    assert "<tspan" not in fig.render_svg()


def test_tick_wrap_default_is_off():
    fig = Figure(width=200, auto_display=False)
    fig.bar(["A very long category label indeed"], [1.0])
    assert "<tspan" not in fig.render_svg()


# ---------------------------------------------------------------------------
# Tick-label escaping (found while building the above)
# ---------------------------------------------------------------------------

def test_custom_xtick_labels_are_escaped():
    """set_xticks(..., labels=[...]) interpolated its labels raw."""
    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.set_xticks([1, 2, 3], labels=["Ben & Co", "plain", "<b>bold</b>"])
    svg = fig.render_svg()
    assert "Ben &amp; Co" in svg
    assert "<b>bold</b>" not in svg


def test_custom_ytick_labels_are_escaped():
    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.set_yticks([1, 2, 3], labels=["A & B", "C", "D"])
    assert "A &amp; B" in fig.render_svg()


def test_wrapped_labels_are_escaped_per_line():
    """Wrapping happens before escaping, on the raw string, so an entity
    must not be split apart -- each tspan is escaped independently."""
    fig = Figure(width=400, auto_display=False)
    fig.bar(["Sales & Marketing Department"], [1.0])
    fig.set_tick_wrap(True)
    svg = fig.render_svg()
    assert "&amp;" in svg
    assert " & " not in svg.split("<tspan", 1)[1] if "<tspan" in svg else True


def test_annotation_arrow_marker_ids_are_unique_per_figure():
    """A static id="arrow" meant two figures with annotations sharing one
    HTML document had duplicate marker ids; url(#arrow) then resolves to
    whichever figure's marker comes first in the document."""
    fig1 = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0])
    fig1.annotate("peak", x=2, y=2, arrow=True)
    fig2 = Figure(auto_display=False).bar([1, 2, 3], [3.0, 2.0, 1.0])
    fig2.annotate("low", x=1, y=3, arrow=True)

    svg1, svg2 = fig1.render_svg(), fig2.render_svg()
    assert 'id="arrow"' not in svg1 and 'id="arrow"' not in svg2

    import re
    id1 = re.search(r'marker id="([^"]*)"', svg1).group(1)
    id2 = re.search(r'marker id="([^"]*)"', svg2).group(1)
    assert id1 != id2
    assert fig1.render_svg() == svg1, "re-rendering must stay byte-identical"


# ---------------------------------------------------------------------------
# SubplotGrid.save()
# ---------------------------------------------------------------------------

def _grid_with_two_figures():
    sg = SubplotGrid(1, 2)
    sg.add(Figure(auto_display=False, title="Revenue").line([1, 2], [1.0, 2.0]), 0, 0)
    sg.add(Figure(auto_display=False, title="Costs").bar([1, 2], [3.0, 4.0]), 0, 1)
    return sg


def test_save_html_matches_render(tmp_path):
    sg = _grid_with_two_figures()
    path = tmp_path / "dash.html"
    sg.save(str(path))
    assert path.read_text(encoding="utf-8") == sg.render()


def test_save_rejects_unsupported_extensions(tmp_path):
    sg = _grid_with_two_figures()
    with pytest.raises(ValueError, match="does not support"):
        sg.save(str(tmp_path / "dash.png"))


def test_save_pptx_requires_a_non_empty_grid(tmp_path):
    """
    Deliberately no importorskip: an empty grid is a caller error whether or
    not cairosvg is installed, so this must raise ValueError everywhere. The
    dependency check used to run first, turning a missing figure into a
    misleading "install cairosvg" RuntimeError on any machine without the
    optional extras -- which is every CI runner.
    """
    with pytest.raises(ValueError, match="empty"):
        SubplotGrid(1, 1).save(str(tmp_path / "empty.pptx"))


def test_save_pptx_writes_one_slide_per_figure_skipping_empty_cells(tmp_path):
    pptx = pytest.importorskip("pptx")
    pytest.importorskip("cairosvg")

    sg = SubplotGrid(2, 2)
    sg.add(Figure(auto_display=False, title="A").line([1, 2], [1.0, 2.0]), 0, 0)
    sg.add(Figure(auto_display=False, title="B").bar([1, 2], [3.0, 4.0]), 0, 1)
    sg.add(Figure(auto_display=False).scatter([1, 2], [2.0, 1.0]), 1, 1)  # (1,0) empty

    path = tmp_path / "deck.pptx"
    sg.save(str(path))

    prs = pptx.Presentation(str(path))
    assert len(prs.slides) == 3

    titled = []
    for slide in prs.slides:
        texts = [sh.text_frame.text for sh in slide.shapes
                if sh.has_text_frame and sh.text_frame.text]
        titled.append(texts[0] if texts else None)
    assert titled == ["A", "B", None]


def test_single_figure_pptx_export_is_unaffected(tmp_path):
    """The refactor that let SubplotGrid share the slide-builder must not
    change Figure.save()'s own single-slide output."""
    pptx = pytest.importorskip("pptx")
    pytest.importorskip("cairosvg")

    path = tmp_path / "single.pptx"
    Figure(auto_display=False, title="Solo").line([1, 2, 3], [1.0, 2.0, 3.0]).save(str(path))
    prs = pptx.Presentation(str(path))
    assert len(prs.slides) == 1
