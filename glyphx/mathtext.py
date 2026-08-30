"""
LaTeX math in labels, rendered natively to SVG.

``$...$`` spans in titles, axis labels, tick labels, legend entries, and
annotations are converted into real SVG ``<tspan>`` markup.

Why not MathJax or a LaTeX install:

* MathJax does not typeset text inside an ``<svg>`` element. GlyphX used to
  load it and set ``data-has-math``, but the labels still showed a literal
  ``$E = mc^2$`` in every output format.
* Shelling out to ``latex`` would make the highest-value labels depend on a
  multi-gigabyte install that most environments do not have.
* Rasterising math to an image would lose the thing SVG output is for.

Rendering to tspans instead means math works identically in ``.svg``,
``.png``, ``.pdf``, and ``.html``, needs no dependencies, and stays real
text -- selectable, searchable, translatable, and readable by a screen
reader.

Supported subset::

    x^2  x^{10}  x_i  x_{max}  x_i^2      superscripts and subscripts
    \\alpha \\Omega \\pi                     Greek letters
    \\times \\leq \\approx \\infty \\pm        symbols and relations
    \\sum \\int \\partial \\nabla             operators
    \\sqrt{x}                              roots
    \\frac{a}{b}                           fractions, rendered inline as a/b
    \\mathrm{d}  \\text{ if }                upright text inside math

Variables are italicised the way TeX does; digits, operators, and
``\\mathrm`` stay upright. Anything unrecognised is passed through as
literal text rather than raising, so a label never costs someone a chart.
"""

from __future__ import annotations

import re

#: Recognised ``\name`` sequences and the character they render as.
SYMBOLS: dict[str, str] = {
    # lowercase Greek
    "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3", "delta": "\u03b4",
    "epsilon": "\u03b5", "varepsilon": "\u03b5", "zeta": "\u03b6", "eta": "\u03b7",
    "theta": "\u03b8", "vartheta": "\u03d1", "iota": "\u03b9", "kappa": "\u03ba",
    "lambda": "\u03bb", "mu": "\u03bc", "nu": "\u03bd", "xi": "\u03be",
    "pi": "\u03c0", "rho": "\u03c1", "sigma": "\u03c3", "varsigma": "\u03c2",
    "tau": "\u03c4", "upsilon": "\u03c5", "phi": "\u03c6", "varphi": "\u03d5",
    "chi": "\u03c7", "psi": "\u03c8", "omega": "\u03c9",
    # uppercase Greek
    "Gamma": "\u0393", "Delta": "\u0394", "Theta": "\u0398", "Lambda": "\u039b",
    "Xi": "\u039e", "Pi": "\u03a0", "Sigma": "\u03a3", "Upsilon": "\u03a5",
    "Phi": "\u03a6", "Psi": "\u03a8", "Omega": "\u03a9",
    # relations and operators
    "times": "\u00d7", "div": "\u00f7", "cdot": "\u22c5", "pm": "\u00b1",
    "mp": "\u2213", "leq": "\u2264", "le": "\u2264", "geq": "\u2265",
    "ge": "\u2265", "neq": "\u2260", "ne": "\u2260", "approx": "\u2248",
    "equiv": "\u2261", "sim": "\u223c", "propto": "\u221d", "ll": "\u226a",
    "gg": "\u226b",
    # symbols
    "infty": "\u221e", "partial": "\u2202", "nabla": "\u2207",
    "sum": "\u2211", "prod": "\u220f", "int": "\u222b", "sqrt": "\u221a",
    "degree": "\u00b0", "deg": "\u00b0", "angle": "\u2220",
    "perp": "\u22a5", "parallel": "\u2225", "therefore": "\u2234",
    "in": "\u2208", "notin": "\u2209", "subset": "\u2282", "cup": "\u222a",
    "cap": "\u2229", "forall": "\u2200", "exists": "\u2203",
    "rightarrow": "\u2192", "to": "\u2192", "leftarrow": "\u2190",
    "leftrightarrow": "\u2194", "Rightarrow": "\u21d2", "Leftarrow": "\u21d0",
    "ldots": "\u2026", "dots": "\u2026", "cdots": "\u22ef",
    "prime": "\u2032", "star": "\u22c6", "circ": "\u2218",
    "hbar": "\u210f", "ell": "\u2113", "Re": "\u211c", "Im": "\u2111",
    "aleph": "\u2135", "emptyset": "\u2205", "surd": "\u221a",
    # spacing
    "quad": "\u2003", "qquad": "\u2003\u2003", ",": "\u2009", ";": "\u2004",
    " ": " ",
}

#: Wrapped in ``$...$``.
_MATH_SPAN = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$", re.DOTALL)

#: Superscript/subscript offsets, as a fraction of the surrounding font size.
_SCRIPT_SIZE = 0.72
_SUP_SHIFT = "-0.42em"
_SUB_SHIFT = "0.28em"


def contains_math(text: object) -> bool:
    """True if ``text`` has a ``$...$`` span in it."""
    return isinstance(text, str) and bool(_MATH_SPAN.search(text))


def _escape(text: str) -> str:
    """Escape XML special characters in a text run."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _split_group(source: str, index: int) -> tuple[str, int]:
    """
    Read the argument that follows a script or command marker.

    Handles ``{...}`` groups with nesting, a single ``\\command``, or a bare
    character.

    Args:
        source (str): The expression being parsed.
        index (int): Position just after the marker.

    Returns:
        tuple[str, int]: The argument text and the position after it.
    """
    if index >= len(source):
        return "", index

    if source[index] == "{":
        depth = 0
        for pos in range(index, len(source)):
            if source[pos] == "{":
                depth += 1
            elif source[pos] == "}":
                depth -= 1
                if depth == 0:
                    return source[index + 1:pos], pos + 1
        return source[index + 1:], len(source)   # unbalanced; take the rest

    if source[index] == "\\":
        match = re.match(r"\\([A-Za-z]+|.)", source[index:])
        if match:
            return match.group(0), index + len(match.group(0))

    return source[index], index + 1


def _render_expr(expr: str, italic: bool = True) -> str:
    """
    Convert one math expression into SVG tspan markup.

    Args:
        expr (str): Content between the dollar signs.
        italic (bool): Italicise single-letter variables, as TeX does.

    Returns:
        str: SVG markup.
    """
    out: list[str] = []
    plain: list[str] = []

    def flush() -> None:
        if plain:
            out.append(_escape("".join(plain)))
            plain.clear()

    index = 0
    while index < len(expr):
        char = expr[index]

        # -- commands
        if char == "\\":
            match = re.match(r"\\([A-Za-z]+|[,;\s])", expr[index:])
            if not match:
                plain.append(expr[index + 1:index + 2])
                index += 2
                continue

            name = match.group(1)
            index += len(match.group(0))

            if name in ("mathrm", "text", "mathsf", "operatorname"):
                arg, index = _split_group(expr, index)
                flush()
                out.append(
                    f'<tspan font-style="normal">{_escape(arg)}</tspan>'
                )
                continue

            if name in ("mathbf", "bf"):
                arg, index = _split_group(expr, index)
                flush()
                out.append(
                    f'<tspan font-weight="bold">{_render_expr(arg, italic)}</tspan>'
                )
                continue

            # FIXME: no overbar on the radical. Drawing one means emitting a
            # <path> next to the <text>, and we'd need the rendered width of
            # the argument to size it, which we don't have here.
            if name == "sqrt":
                arg, index = _split_group(expr, index)
                flush()
                # An overbar would need a drawn path; parenthesising keeps the
                # meaning unambiguous with plain text.
                inner = _render_expr(arg, italic)
                out.append(f"\u221a<tspan>(</tspan>{inner}<tspan>)</tspan>")
                continue

            # TODO: stacked fractions. Needs a rule and two shifted rows,
            # which won't sit on a single text baseline without pushing the
            # surrounding label around. Inline a/b until someone asks.
            if name == "frac":
                numerator, index = _split_group(expr, index)
                denominator, index = _split_group(expr, index)
                flush()
                # Rendered inline as a/b: a stacked fraction needs a rule and
                # two shifted rows, which cannot align on a single text
                # baseline without breaking the surrounding layout.
                out.append(
                    f"{_render_expr(numerator, italic)}"
                    f'<tspan font-style="normal">/</tspan>'
                    f"{_render_expr(denominator, italic)}"
                )
                continue

            if name in SYMBOLS:
                plain.append(SYMBOLS[name])
                continue

            plain.append(name)          # unknown command: show its name
            continue

        # -- scripts
        if char in "^_":
            arg, index = _split_group(expr, index + 1)
            flush()
            shift = _SUP_SHIFT if char == "^" else _SUB_SHIFT
            out.append(
                f'<tspan baseline-shift="{shift}" '
                f'font-size="{_SCRIPT_SIZE:.2f}em">'
                f"{_render_expr(arg, italic)}</tspan>"
            )
            # Return to the baseline so following text is not shifted too.
            out.append(
                '<tspan baseline-shift="0" font-size="1em"></tspan>'
            )
            continue

        # -- ordinary characters
        if italic and char.isalpha() and char.isascii():
            flush()
            out.append(f'<tspan font-style="italic">{_escape(char)}</tspan>')
            index += 1
            continue

        plain.append(char)
        index += 1

    flush()
    return "".join(out)


def render(text: str) -> str:
    """
    Render a label, converting any ``$...$`` spans to SVG markup.

    Text outside the math spans is escaped and left alone, so mixed labels
    such as ``"Energy $E = mc^2$ over time"`` work.

    Args:
        text (str): The label.

    Returns:
        str: Markup safe to place inside an SVG ``<text>`` element.
    """
    if not isinstance(text, str):
        text = str(text)

    if not contains_math(text):
        return _escape(text).replace(r"\$", "$")

    out: list[str] = []
    position = 0
    for match in _MATH_SPAN.finditer(text):
        out.append(_escape(text[position:match.start()]))
        out.append(_render_expr(match.group(1)))
        position = match.end()
    out.append(_escape(text[position:]))
    return "".join(out).replace(r"\$", "$")


def to_plain_text(text: str) -> str:
    """
    Convert a label to a spoken form for alt text and ARIA descriptions.

    Markup is useless to a screen reader, so ``$\\sigma_{x}$`` becomes
    ``σ_x`` rather than a pile of tspans.

    Args:
        text (str): The label.

    Returns:
        str: Plain text with commands resolved to characters.
    """
    if not isinstance(text, str):
        return str(text)

    def _plain(match: re.Match) -> str:
        expr = match.group(1)
        # Structural commands first: \sqrt is also in SYMBOLS, and replacing
        # it as a bare glyph would strip the parentheses off its argument.
        expr = re.sub(r"\\(?:mathrm|text|mathsf|mathbf|operatorname)\{([^}]*)\}",
                      r"\1", expr)
        expr = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"\1/\2", expr)
        expr = re.sub(r"\\sqrt\{([^}]*)\}", "\u221a(\\1)", expr)
        for name, char in sorted(SYMBOLS.items(), key=lambda kv: -len(kv[0])):
            expr = expr.replace("\\" + name, char)
        expr = expr.replace("{", "").replace("}", "")
        return expr

    return _MATH_SPAN.sub(_plain, text).replace(r"\$", "$")


def estimate_width(text: str, font_size: float) -> float:
    """
    Approximate the rendered width of a label in pixels.

    Layout code sizes gutters and legends before anything is drawn, and a
    math label's width is not its character count -- scripts are smaller and
    commands collapse to one glyph.

    Args:
        text (str): The label.
        font_size (float): Font size in pixels.

    Returns:
        float: Estimated width in pixels.
    """
    plain = to_plain_text(text)
    # Scripts render at ~72% size; treat them as a whole character anyway,
    # which errs toward reserving slightly too much room rather than clipping.
    plain = re.sub(r"[\^_]", "", plain)
    return len(plain) * font_size * 0.6
