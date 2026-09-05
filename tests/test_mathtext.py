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
    """
    This asserted -0.42em, which *lowers* the text -- the constants were
    inverted, and the test locked that in while reading as if it checked
    the opposite. It now asserts the direction rather than a literal.
    """
    markup = render(r"$x^2$")
    _wrap(markup)
    shift = re.search(r'baseline-shift="([^"]+)"', markup).group(1)
    assert not shift.startswith("-")
    assert ">2<" in markup


def test_subscript_becomes_a_lowered_tspan():
    markup = render(r"$x_i$")
    _wrap(markup)
    shift = re.search(r'baseline-shift="([^"]+)"', markup).group(1)
    assert shift.startswith("-")


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


def test_frac_output_is_well_formed_svg():
    """Superseded test_frac_renders_inline: fractions now stack, so the
    literal "/" is gone. _wrap still checks the markup parses."""
    markup = render(r"$\frac{a}{b}$")
    _wrap(markup)
    assert "overline" in markup


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


# ---------------------------------------------------------------------------
# Stacked fractions
# ---------------------------------------------------------------------------

def test_frac_renders_stacked_not_inline():
    """
    \\frac used to come out as inline "a/b", which is readable but is not
    what a fraction looks like in a paper.
    """
    markup = render(r"$\frac{a}{b}$")
    assert "dy=" in markup, "no vertical stacking"
    assert "overline" in markup, "no fraction bar"


def test_frac_bar_sits_over_the_numerator():
    markup = render(r"$\frac{a}{b}$")
    numerator_span = markup.split("</tspan>")[0]
    assert "overline" in numerator_span
    assert numerator_span.rstrip().endswith("a"), numerator_span


def test_frac_rows_are_centred_over_each_other():
    """Uneven rows need a dx lead so the shorter one is centred."""
    markup = render(r"$\frac{abcd}{x}$")
    assert 'dx="0.000em"' not in markup.split("</tspan>")[1]


def test_frac_advances_the_pen_past_the_wider_row():
    """
    Without the trailing dx the rest of the label would overlap the
    fraction, because the pen stops wherever the denominator ended.
    """
    markup = render(r"$\frac{a}{bcde}$")
    assert markup.rstrip().endswith("</tspan>")
    tail = markup.split("<tspan")[-1]
    assert "dx=" in tail


def test_frac_still_reads_as_a_slash_for_screen_readers():
    """Markup is useless to a screen reader; the spoken form is unchanged."""
    assert to_plain_text(r"$\frac{dN}{dt}$") == "dN/dt"


def test_frac_width_is_one_row_not_the_slash_form():
    """
    Layout sizes gutters from this. Measuring "dN/dt" would reserve roughly
    double what a stacked fraction actually occupies.
    """
    assert estimate_width(r"$\frac{dN}{dt}$", 12) == estimate_width("dN", 12)


def test_nested_expressions_inside_a_fraction():
    markup = render(r"$\frac{x^2}{\sigma}$")
    assert "baseline-shift" in markup      # the superscript survived
    assert "\u03c3" in markup              # and the sigma


def test_fraction_inside_a_larger_label():
    markup = render(r"Rate $\frac{dN}{dt}$ over time")
    assert markup.startswith("Rate ")
    assert markup.endswith(" over time")


def test_multiple_fractions_in_one_label():
    markup = render(r"$\frac{a}{b}$ and $\frac{c}{d}$")
    assert markup.count("overline") == 2


# ---------------------------------------------------------------------------
# Script direction
# ---------------------------------------------------------------------------

def test_superscript_is_raised_and_subscript_lowered():
    """
    SVG baseline-shift raises for a positive length. The constants were the
    other way round, so every superscript in every chart rendered as a
    subscript: x^2 put the 2 below the baseline and x_2 put it above.
    """
    from glyphx.mathtext import _SUB_SHIFT, _SUP_SHIFT

    assert not _SUP_SHIFT.startswith("-"), "superscript must raise"
    assert _SUB_SHIFT.startswith("-"), "subscript must lower"


def test_superscript_markup_shifts_upward():
    markup = render(r"$x^2$")
    shift = re.search(r'baseline-shift="([^"]+)"', markup).group(1)
    assert not shift.startswith("-")


def test_subscript_markup_shifts_downward():
    markup = render(r"$x_2$")
    shift = re.search(r'baseline-shift="([^"]+)"', markup).group(1)
    assert shift.startswith("-")


# ---------------------------------------------------------------------------
# Catalog breadth
# ---------------------------------------------------------------------------

def test_symbol_catalog_is_comprehensive():
    from glyphx.mathtext import SYMBOLS
    assert len(SYMBOLS) >= 300


@pytest.mark.parametrize("command, expected", [
    (r"\oplus", "\u2295"), (r"\otimes", "\u2297"), (r"\bigcup", "\u22c3"),
    (r"\bigcap", "\u22c2"), (r"\subseteq", "\u2286"), (r"\supseteq", "\u2287"),
    (r"\longrightarrow", "\u27f6"), (r"\Leftrightarrow", "\u21d4"),
    (r"\mapsto", "\u21a6"), (r"\uparrow", "\u2191"), (r"\varnothing", "\u2205"),
    (r"\langle", "\u27e8"), (r"\rangle", "\u27e9"), (r"\vdots", "\u22ee"),
    (r"\oint", "\u222e"), (r"\coprod", "\u2210"), (r"\wedge", "\u2227"),
    (r"\vee", "\u2228"), (r"\cong", "\u2245"), (r"\prec", "\u227a"),
])
def test_new_symbols_resolve(command, expected):
    assert expected in to_plain_text(f"${command}$")


@pytest.mark.parametrize("fn", ["sin", "cos", "tan", "log", "ln", "exp",
                                "max", "min", "lim", "det", "arg"])
def test_function_names_set_upright(fn):
    """
    Rendering "sin" in italic makes it read as the product of three
    variables rather than as a function.
    """
    markup = render(rf"$\{fn}(x)$")
    assert f'<tspan font-style="normal">{fn}</tspan>' in markup


def test_function_name_reads_as_itself_in_plain_text():
    assert to_plain_text(r"$\sin(x) + \log(y)$") == "sin(x) + log(y)"


@pytest.mark.parametrize("accent, mark", [
    ("hat", "\u0302"), ("bar", "\u0304"), ("vec", "\u20d7"),
    ("tilde", "\u0303"), ("dot", "\u0307"), ("ddot", "\u0308"),
])
def test_accents_apply_a_combining_mark(accent, mark):
    """A combining mark follows the character it modifies."""
    assert to_plain_text(rf"$\{accent}{{x}}$") == f"x{mark}"


@pytest.mark.parametrize("command, expected", [
    (r"\mathbb{R}", "\u211d"), (r"\mathbb{N}", "\u2115"),
    (r"\mathbb{Z}", "\u2124"), (r"\mathbb{Q}", "\u211a"),
    (r"\mathcal{L}", "\u2112"), (r"\mathcal{F}", "\u2131"),
    (r"\mathfrak{g}", "g"),
])
def test_alternate_alphabets(command, expected):
    assert to_plain_text(f"${command}$") == expected


def test_delimiter_sizing_commands_are_dropped_not_printed():
    """
    There is no delimiter sizing here, but printing the word "left" into the
    middle of a label would be worse than rendering it at normal size.
    """
    assert to_plain_text(r"$\left( x \right)$") == "( x )"
    assert "left" not in render(r"$\left( x \right)$")


def test_a_shorter_command_is_not_matched_inside_a_longer_one():
    r"""Plain substring replacement made \left match \le and print "≤ft"."""
    assert to_plain_text(r"$\left( a \le b \right)$") == "( a \u2264 b )"


def test_spacing_commands_render_as_space():
    assert "\u2003" in to_plain_text(r"$x \quad y$")


def test_a_full_statistics_expression_round_trips():
    expr = r"$\hat{\beta} = (X^T X)^{-1} X^T y$"
    plain = to_plain_text(expr)
    assert plain.startswith("\u03b2\u0302 =")
    assert "left" not in plain and "\\" not in plain
