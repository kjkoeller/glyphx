"""
LaTeX math in labels.

``$...$`` spans are rendered to native SVG tspans rather than handed to a
front-end typesetter, so these tests check the emitted markup directly and
assert that no raw LaTeX survives into any output.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from glyphx import Figure
from glyphx.mathtext import (
    contains_math,
    estimate_width,
    render,
    to_plain_text,
)


def _wrap(markup: str) -> ET.Element:
    """Parse rendered markup, which must be valid inside a <text> element."""
    return ET.fromstring(f"<text>{markup}</text>")


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,expected", [
    (r"$x$", True),
    (r"Energy $E = mc^2$", True),
    ("no math here", False),
    ("costs $5 to $10", True),        # ambiguous, but $...$ is the documented marker
    (r"costs \$5", False),
    ("", False),
    (None, False),
    (5, False),
])
def test_contains_math(label, expected):
    assert contains_math(label) is expected


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def test_plain_text_is_escaped_and_unchanged():
    assert render("5 < 10 & rising") == "5 &lt; 10 &amp; rising"


def test_superscript_becomes_a_raised_tspan():
    markup = render(r"$x^2$")
    _wrap(markup)
    assert 'baseline-shift="-0.42em"' in markup
    assert ">2<" in markup


def test_subscript_becomes_a_lowered_tspan():
    markup = render(r"$x_i$")
    _wrap(markup)
    assert 'baseline-shift="0.28em"' in markup


def test_braced_scripts_keep_all_characters():
    markup = render(r"$x^{10}$")
    _wrap(markup)
    assert ">10<" in markup


def test_combined_sub_and_superscript():
    markup = render(r"$x_i^2$")
    _wrap(markup)
    assert markup.count("baseline-shift") >= 2


@pytest.mark.parametrize("command,glyph", [
    (r"\alpha", "\u03b1"),
    (r"\Omega", "\u03a9"),
    (r"\pi", "\u03c0"),
    (r"\times", "\u00d7"),
    (r"\leq", "\u2264"),
    (r"\infty", "\u221e"),
    (r"\partial", "\u2202"),
    (r"\pm", "\u00b1"),
    (r"\approx", "\u2248"),
    (r"\rightarrow", "\u2192"),
])
def test_symbols_render_as_characters(command, glyph):
    markup = render(f"${command}$")
    _wrap(markup)
    assert glyph in markup


def test_variables_are_italicised_but_digits_are_not():
    markup = render(r"$x2$")
    assert '<tspan font-style="italic">x</tspan>' in markup
    assert '<tspan font-style="italic">2</tspan>' not in markup


def test_mathrm_stays_upright():
    markup = render(r"$\mathrm{d}x$")
    assert '<tspan font-style="normal">d</tspan>' in markup


def test_frac_renders_inline():
    markup = render(r"$\frac{a}{b}$")
    _wrap(markup)
    assert ">/<" in markup


def test_sqrt_parenthesises_its_argument():
    markup = render(r"$\sqrt{x}$")
    _wrap(markup)
    assert "\u221a" in markup
    assert ">(<" in markup and ">)<" in markup


def test_text_outside_math_is_preserved():
    markup = render(r"Energy $E$ over time")
    assert markup.startswith("Energy ")
    assert markup.endswith(" over time")


def test_escaped_dollar_is_literal():
    assert render(r"cost in \$USD") == "cost in $USD"


def test_unknown_command_does_not_raise():
    """A typo in a label must never cost someone their chart."""
    markup = render(r"$\notarealcommand{x}$")
    _wrap(markup)


def test_unbalanced_braces_do_not_raise():
    _wrap(render(r"$x^{2$"))
    _wrap(render(r"$\frac{a$"))


def test_markup_is_always_well_formed():
    for label in [r"$a^b_c$", r"$\alpha\beta\gamma$", r"$\frac{\sqrt{x}}{2}$",
                  r"$<>&$", r"$x^{y^{z}}$"]:
        _wrap(render(label))


def test_angle_brackets_inside_math_are_escaped():
    markup = render(r"$a < b$")
    assert "&lt;" in markup
    _wrap(markup)


# ---------------------------------------------------------------------------
# Spoken form
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("label,spoken", [
    (r"$\sigma_{x}$", "\u03c3_x"),
    (r"Energy $E = mc^2$", "Energy E = mc^2"),
    (r"$\frac{a}{b}$", "a/b"),
    (r"$\sqrt{x+1}$", "\u221a(x+1)"),
    (r"$\mathrm{d}x$", "dx"),
    ("plain", "plain"),
])
def test_to_plain_text(label, spoken):
    assert to_plain_text(label) == spoken


def test_estimate_width_ignores_markup():
    assert estimate_width(r"$\alpha$", 12) < estimate_width("alphabetical", 12)


# ---------------------------------------------------------------------------
# End to end through a figure
# ---------------------------------------------------------------------------

@pytest.fixture
def math_fig():
    fig = Figure(auto_display=False, title=r"Energy $E = mc^2$ over time")
    fig.line([1, 2, 3], [1.0, 2.0, 3.0], label=r"$\alpha$ decay")
    fig.set_xlabel(r"Time $t$ (s)")
    fig.set_ylabel(r"$\sigma_{x}$ (m)")
    return fig


def test_no_raw_latex_survives_into_the_svg(math_fig):
    """
    MathJax was loaded but never typeset SVG text, so labels showed the
    literal ``$E = mc^2$`` in every output format.
    """
    svg = math_fig.render_svg()
    ET.fromstring(svg)
    assert "$" not in svg


def test_math_renders_in_titles_labels_and_legend(math_fig):
    svg = math_fig.render_svg()
    assert "\u03c3" in svg, "Greek sigma missing from the Y label"
    assert "\u03b1" in svg, "Greek alpha missing from the legend"
    assert svg.count("<tspan") >= 4


def test_annotations_render_math():
    fig = Figure(auto_display=False)
    fig.line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.annotate(r"peak $\Delta y$", x=2, y=2)
    svg = fig.render_svg()
    ET.fromstring(svg)
    assert "\u0394" in svg
    assert "$" not in svg


def test_alt_text_uses_the_spoken_form(math_fig):
    """Markup is useless to a screen reader."""
    alt = math_fig.to_alt_text()
    assert "$" not in alt
    assert "\\sigma" not in alt
    assert "\u03c3_x" in alt


def test_tooltips_use_the_spoken_form(math_fig):
    svg = math_fig.render_svg()
    labels = re.findall(r'data-label="([^"]*)"', svg)
    assert labels
    for label in labels:
        assert "$" not in label
        assert "\\alpha" not in label


def test_math_survives_png_export(tmp_path, math_fig):
    """The whole point of rendering to tspans is format independence."""
    pytest.importorskip("resvg_py")
    out = tmp_path / "math.png"
    math_fig.save(str(out))
    assert out.read_bytes().startswith(b"\x89PNG")


def test_currency_labels_are_not_treated_as_math():
    fig = Figure(auto_display=False, title=r"Revenue in \$USD")
    fig.bar(["a", "b"], [1.0, 2.0])
    svg = fig.render_svg()
    ET.fromstring(svg)
    assert "USD" in svg
