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

#: Function names that set upright, not italic. ``\sin x`` is a function
#: applied to a variable, and rendering the name in italic makes it read as
#: the product of three variables instead.
FUNCTION_NAMES: frozenset[str] = frozenset({
    "arccos", "arcsin", "arctan", "arg", "cos", "cosh", "cot", "coth",
    "csc", "deg", "det", "dim", "exp", "gcd", "hom", "inf", "injlim",
    "ker", "lg", "lim", "liminf", "limsup", "ln", "log", "max", "min",
    "Pr", "projlim", "sec", "sin", "sinh", "sup", "tan", "tanh",
    "argmax", "argmin", "sgn", "erf", "erfc", "median", "var", "cov",
    "corr", "diag", "tr", "rank", "span", "Var", "Cov", "Corr", "E",
})

#: Accents, as Unicode combining marks placed after the character they
#: modify. ``\hat{x}`` becomes "x" followed by U+0302, which the text
#: renderer composes into a single glyph.
ACCENTS: dict[str, str] = {
    "hat": "\u0302", "widehat": "\u0302",
    "bar": "\u0304", "overline": "\u0304",
    "vec": "\u20d7", "overrightarrow": "\u20d7",
    "tilde": "\u0303", "widetilde": "\u0303",
    "dot": "\u0307", "ddot": "\u0308", "dddot": "\u20db",
    "acute": "\u0301", "grave": "\u0300", "breve": "\u0306",
    "check": "\u030c", "mathring": "\u030a", "underline": "\u0332",
}

#: Blackboard-bold (``\mathbb``) for the capitals that have a dedicated
#: Unicode codepoint. R, N, Z, Q and C are the ones that actually come up.
BLACKBOARD: dict[str, str] = {
    "A": "\U0001d538", "B": "\U0001d539", "C": "\u2102", "D": "\U0001d53b",
    "E": "\U0001d53c", "F": "\U0001d53d", "G": "\U0001d53e", "H": "\u210d",
    "I": "\U0001d540", "J": "\U0001d541", "K": "\U0001d542", "L": "\U0001d543",
    "M": "\U0001d544", "N": "\u2115", "O": "\U0001d546", "P": "\u2119",
    "Q": "\u211a", "R": "\u211d", "S": "\U0001d54a", "T": "\U0001d54b",
    "U": "\U0001d54c", "V": "\U0001d54d", "W": "\U0001d54e", "X": "\U0001d54f",
    "Y": "\U0001d550", "Z": "\u2124",
}

#: Script / calligraphic (``\mathcal``).
CALLIGRAPHIC: dict[str, str] = {
    "A": "\U0001d49c", "B": "\u212c", "C": "\U0001d49e", "D": "\U0001d49f",
    "E": "\u2130", "F": "\u2131", "G": "\U0001d4a2", "H": "\u210b",
    "I": "\u2110", "J": "\U0001d4a5", "K": "\U0001d4a6", "L": "\u2112",
    "M": "\u2133", "N": "\U0001d4a9", "O": "\U0001d4aa", "P": "\U0001d4ab",
    "Q": "\U0001d4ac", "R": "\u211b", "S": "\U0001d4ae", "T": "\U0001d4af",
    "U": "\U0001d4b0", "V": "\U0001d4b1", "W": "\U0001d4b2", "X": "\U0001d4b3",
    "Y": "\U0001d4b4", "Z": "\U0001d4b5",
}

#: Fraktur (``\mathfrak``).
FRAKTUR: dict[str, str] = {
    "A": "\U0001d504", "B": "\U0001d505", "C": "\u212d", "D": "\U0001d507",
    "E": "\U0001d508", "F": "\U0001d509", "G": "\U0001d50a", "H": "\u210c",
    "I": "\u2111", "J": "\U0001d50d", "K": "\U0001d50e", "L": "\U0001d50f",
    "M": "\U0001d510", "N": "\U0001d511", "O": "\U0001d512", "P": "\U0001d513",
    "Q": "\U0001d514", "R": "\u211c", "S": "\U0001d516", "T": "\U0001d517",
    "U": "\U0001d518", "V": "\U0001d519", "W": "\U0001d51a", "X": "\U0001d51b",
    "Y": "\U0001d51c", "Z": "\u2128",
}

#: Explicit spacing commands, in em.
SPACING: dict[str, float] = {
    ",": 0.167, ":": 0.222, ";": 0.278, "!": -0.167,
    "quad": 1.0, "qquad": 2.0, " ": 0.25,
}

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
    # -- Greek variants -----------------------------------------------------
    "varrho": "\u03f1", "varpi": "\u03d6", "varkappa": "\u03f0",
    "digamma": "\u03dd", "varDelta": "\u0394", "varGamma": "\u0393",
    "varLambda": "\u039b", "varOmega": "\u03a9", "varPhi": "\u03a6",
    "varPi": "\u03a0", "varPsi": "\u03a8", "varSigma": "\u03a3",
    "varTheta": "\u0398", "varUpsilon": "\u03a5", "varXi": "\u039e",

    # -- Relations ----------------------------------------------------------
    "leqslant": "\u2a7d", "geqslant": "\u2a7e", "prec": "\u227a",
    "succ": "\u227b", "preceq": "\u2aaf", "succeq": "\u2ab0",
    "subseteq": "\u2286", "supset": "\u2283", "supseteq": "\u2287",
    "subsetneq": "\u228a", "supsetneq": "\u228b",
    "sqsubset": "\u228f", "sqsupset": "\u2290",
    "sqsubseteq": "\u2291", "sqsupseteq": "\u2292",
    "models": "\u22a8", "vdash": "\u22a2", "dashv": "\u22a3",
    "asymp": "\u224d", "cong": "\u2245", "simeq": "\u2243",
    "doteq": "\u2250", "ni": "\u220b", "owns": "\u220b",
    "nsubseteq": "\u2288", "nsupseteq": "\u2289", "nmid": "\u2224",
    "mid": "\u2223", "smile": "\u2323", "frown": "\u2322",
    "bowtie": "\u22c8", "lll": "\u22d8", "ggg": "\u22d9",
    "triangleq": "\u225c", "between": "\u226c", "ncong": "\u2247",
    "nsim": "\u2241", "nparallel": "\u2226", "lesssim": "\u2272",
    "gtrsim": "\u2273", "nless": "\u226e", "ngtr": "\u226f",
    "nleq": "\u2270", "ngeq": "\u2271", "equal": "=",

    # -- Binary operators ---------------------------------------------------
    "oplus": "\u2295", "ominus": "\u2296", "otimes": "\u2297",
    "oslash": "\u2298", "odot": "\u2299", "bigcirc": "\u25cb",
    "dagger": "\u2020", "ddagger": "\u2021", "amalg": "\u2a3f",
    "uplus": "\u228e", "sqcap": "\u2293", "sqcup": "\u2294",
    "vee": "\u2228", "wedge": "\u2227", "lor": "\u2228", "land": "\u2227",
    "setminus": "\u2216", "wr": "\u2240", "bullet": "\u2219",
    "ast": "\u2217", "diamond": "\u22c4", "triangleleft": "\u25c1",
    "triangleright": "\u25b7", "bigtriangleup": "\u25b3",
    "bigtriangledown": "\u25bd", "cdotp": "\u00b7", "boxplus": "\u229e",
    "boxminus": "\u229f", "boxtimes": "\u22a0", "boxdot": "\u22a1",
    "ltimes": "\u22c9", "rtimes": "\u22ca", "divideontimes": "\u22c7",
    "centerdot": "\u00b7", "intercal": "\u22ba",

    # -- Large operators ----------------------------------------------------
    "bigcup": "\u22c3", "bigcap": "\u22c2", "bigoplus": "\u2a01",
    "bigotimes": "\u2a02", "bigodot": "\u2a00", "bigvee": "\u22c1",
    "bigwedge": "\u22c0", "biguplus": "\u2a04", "bigsqcup": "\u2a06",
    "coprod": "\u2210", "oint": "\u222e", "iint": "\u222c",
    "iiint": "\u222d", "oiint": "\u222f",

    # -- Arrows -------------------------------------------------------------
    "uparrow": "\u2191", "downarrow": "\u2193", "updownarrow": "\u2195",
    "Uparrow": "\u21d1", "Downarrow": "\u21d3", "Updownarrow": "\u21d5",
    "nearrow": "\u2197", "searrow": "\u2198", "swarrow": "\u2199",
    "nwarrow": "\u2196", "mapsto": "\u21a6", "longmapsto": "\u27fc",
    "hookrightarrow": "\u21aa", "hookleftarrow": "\u21a9",
    "rightharpoonup": "\u21c0", "rightharpoondown": "\u21c1",
    "leftharpoonup": "\u21bc", "leftharpoondown": "\u21bd",
    "rightleftharpoons": "\u21cc", "leftrightharpoons": "\u21cb",
    "longrightarrow": "\u27f6", "longleftarrow": "\u27f5",
    "longleftrightarrow": "\u27f7", "Longrightarrow": "\u27f9",
    "Longleftarrow": "\u27f8", "Longleftrightarrow": "\u27fa",
    "Leftrightarrow": "\u21d4", "iff": "\u27fa", "implies": "\u27f9",
    "impliedby": "\u27f8", "gets": "\u2190", "rightsquigarrow": "\u21dd",
    "leadsto": "\u21dd", "twoheadrightarrow": "\u21a0",
    "rightarrowtail": "\u21a3", "circlearrowleft": "\u21ba",
    "circlearrowright": "\u21bb", "nrightarrow": "\u219b",
    "nleftarrow": "\u219a", "nLeftrightarrow": "\u21ce",

    # -- Miscellaneous symbols ----------------------------------------------
    "nexists": "\u2204", "complement": "\u2201", "varnothing": "\u2205",
    "top": "\u22a4", "bot": "\u22a5", "neg": "\u00ac", "lnot": "\u00ac",
    "flat": "\u266d", "natural": "\u266e", "sharp": "\u266f",
    "clubsuit": "\u2663", "diamondsuit": "\u2662", "heartsuit": "\u2661",
    "spadesuit": "\u2660", "wp": "\u2118", "imath": "\u0131",
    "jmath": "\u0237", "mho": "\u2127", "backslash": "\\",
    "vert": "|", "Vert": "\u2016", "langle": "\u27e8", "rangle": "\u27e9",
    "lceil": "\u2308", "rceil": "\u2309", "lfloor": "\u230a",
    "rfloor": "\u230b", "vdots": "\u22ee", "ddots": "\u22f1",
    "triangle": "\u25b3", "square": "\u25a1", "blacksquare": "\u25a0",
    "checkmark": "\u2713", "maltese": "\u2720", "S": "\u00a7",
    "P": "\u00b6", "copyright": "\u00a9", "pounds": "\u00a3",
    "euro": "\u20ac", "yen": "\u00a5", "celsius": "\u2103",
    "angstrom": "\u212b", "micro": "\u00b5", "permil": "\u2030",
    "bigstar": "\u2605", "circledS": "\u24c8", "Finv": "\u2132",
    "Game": "\u2141", "eth": "\u00f0", "hslash": "\u210f",
    "backprime": "\u2035", "varprime": "\u2032",

}

#: Wrapped in ``$...$``.
_MATH_SPAN = re.compile(r"(?<!\\)\$(.+?)(?<!\\)\$", re.DOTALL)

#: Superscript/subscript offsets, as a fraction of the surrounding font size.
_SCRIPT_SIZE = 0.72
# SVG baseline-shift raises the text for a positive length. These were the
# other way round, so every superscript rendered as a subscript and vice
# versa: x^2 put the 2 below the baseline and x_2 put it above.
_SUP_SHIFT = "0.42em"
_SUB_SHIFT = "-0.28em"


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
        """Emit any buffered plain text before switching to a math run."""
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

            # Function names set upright. Rendering "sin" in italic makes it
            # read as the product of three variables rather than a function.
            if name in FUNCTION_NAMES:
                flush()
                out.append(f'<tspan font-style="normal">{name}</tspan>')
                continue

            if name in ACCENTS:
                arg, index = _split_group(expr, index)
                flush()
                # A combining mark follows the character it modifies, so the
                # accent is appended rather than wrapped around.
                out.append(f"{_render_expr(arg, italic)}{ACCENTS[name]}")
                continue

            if name in ("mathbb", "mathcal", "mathfrak"):
                arg, index = _split_group(expr, index)
                flush()
                table = {"mathbb": BLACKBOARD, "mathcal": CALLIGRAPHIC,
                         "mathfrak": FRAKTUR}[name]
                # Only the capitals have dedicated codepoints; anything else
                # passes through so the label degrades to plain text rather
                # than to a box.
                out.append(_escape("".join(table.get(c, c) for c in arg)))
                continue

            if name in SPACING:
                flush()
                out.append(f'<tspan dx="{SPACING[name]:.3f}em"></tspan>')
                continue

            # \left( and \right) size delimiters in real TeX. There is no
            # sizing here, so the command is dropped and the delimiter it
            # introduces renders at its normal size -- better than printing
            # the word "left" into the middle of a label.
            if name in ("left", "right", "bigl", "bigr", "Bigl", "Bigr",
                        "biggl", "biggr", "Biggl", "Biggr", "big", "Big",
                        "bigg", "Bigg", "displaystyle", "textstyle",
                        "limits", "nolimits"):
                continue

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

            if name == "frac":
                numerator, index = _split_group(expr, index)
                denominator, index = _split_group(expr, index)
                flush()
                out.append(_stacked_fraction(numerator, denominator, italic))
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


#: Vertical offsets for a stacked fraction, in em. The numerator sits above
#: the baseline and the denominator below, so the whole fraction stays
#: centred on the surrounding text rather than hanging off it.
_FRAC_RISE = 0.55
_FRAC_DROP = 1.10

#: Rough advance width of one character, in em. Used to centre the two rows
#: of a fraction over each other; SVG text has no metrics API, and the same
#: 0.6 figure is what estimate_width() already assumes.
_EM_PER_CHAR = 0.6


def _stacked_fraction(numerator: str, denominator: str, italic: bool) -> str:
    """
    Render ``\\frac{a}{b}`` as a real stacked fraction.

    Previously this came out as inline ``a/b``, which is readable but is not
    what a fraction looks like in a paper. SVG ``<text>`` cannot contain a
    drawn rule, so the bar is an ``overline`` on the numerator, and the two
    rows are stacked with ``dy`` shifts and centred over each other with
    ``dx``.

    The horizontal arithmetic walks the text pen: after the numerator the
    pen has advanced past it, so the denominator needs a negative ``dx`` to
    come back and start under it, and a final positive ``dx`` puts the pen
    where the wider of the two rows ends -- otherwise the rest of the label
    would overlap the fraction.

    Args:
        numerator:   Expression above the bar.
        denominator: Expression below it.
        italic:      Whether variables render italic, as in the enclosing run.

    Returns:
        str: ``<tspan>`` markup for placing inside an SVG ``<text>``.
    """
    num_markup = _render_expr(numerator, italic)
    den_markup = _render_expr(denominator, italic)

    # Widths from the plain form: the markup is full of tags, and scripts
    # and commands do not occupy one character each.
    w_num = len(to_plain_text(f"${numerator}$")) * _EM_PER_CHAR
    w_den = len(to_plain_text(f"${denominator}$")) * _EM_PER_CHAR
    width = max(w_num, w_den)

    lead = (width - w_num) / 2                 # centre the numerator
    back = -(w_num + w_den) / 2                # pen back under the numerator
    tail = (width - w_den) / 2                 # advance past the wider row

    return (
        f'<tspan dy="-{_FRAC_RISE}em" dx="{lead:.3f}em" '
        f'text-decoration="overline">{num_markup}</tspan>'
        f'<tspan dy="{_FRAC_DROP}em" dx="{back:.3f}em">{den_markup}</tspan>'
        f'<tspan dy="-{_FRAC_RISE}em" dx="{tail:.3f}em"></tspan>'
    )


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
        """Strip the math markers, returning the expression as plain text."""
        expr = match.group(1)
        # Structural commands first: \sqrt is also in SYMBOLS, and replacing
        # it as a bare glyph would strip the parentheses off its argument.
        expr = re.sub(r"\\(?:mathrm|text|mathsf|mathbf|operatorname)\{([^}]*)\}",
                      r"\1", expr)
        expr = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"\1/\2", expr)
        expr = re.sub(r"\\sqrt\{([^}]*)\}", "\u221a(\\1)", expr)

        # Alphabet swaps and accents take an argument, so they run before the
        # bare-symbol pass.
        def _alphabet(match: re.Match) -> str:
            """Swap each letter for its blackboard, script or fraktur form."""
            table = {"mathbb": BLACKBOARD, "mathcal": CALLIGRAPHIC,
                     "mathfrak": FRAKTUR}[match.group(1)]
            return "".join(table.get(c, c) for c in match.group(2))

        expr = re.sub(r"\\(mathbb|mathcal|mathfrak)\{([^}]*)\}",
                      _alphabet, expr)
        expr = re.sub(r"\\(" + "|".join(ACCENTS) + r")\{([^}]*)\}",
                      lambda m: m.group(2) + ACCENTS[m.group(1)], expr)

        # Sizing and style commands carry no content of their own; the
        # delimiter after \left is kept, the word "left" is not.
        expr = re.sub(r"\\(?:left|right|[Bb]ig{1,2}[lr]?|displaystyle"
                      r"|textstyle|limits|nolimits)(?![A-Za-z])", "", expr)

        # One pass over every remaining command, longest name first and with
        # a letter lookahead. Replacing by plain substring made "\left" match
        # the shorter "\le" and come out as "≤ft".
        names = sorted(set(SYMBOLS) | set(FUNCTION_NAMES) | set(SPACING),
                       key=len, reverse=True)
        pattern = r"\\(" + "|".join(re.escape(n) for n in names) + r")(?![A-Za-z])"

        def _one(match: re.Match) -> str:
            """Resolve one command to its spoken text."""
            name = match.group(1)
            if name in SYMBOLS:
                return SYMBOLS[name]
            if name in FUNCTION_NAMES:
                return name
            return " "                    # spacing commands

        expr = re.sub(pattern, _one, expr)
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
    # A stacked fraction occupies the width of its wider row, not the width
    # of "a/b" -- measuring the plain form would reserve roughly double the
    # gutter a fraction actually needs.
    def _frac_width(match: re.Match) -> str:
        """Stand-in text as wide as the fraction's wider row."""
        numerator, denominator = match.group(1), match.group(2)
        return "x" * max(len(numerator), len(denominator))

    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", _frac_width, str(text))

    plain = to_plain_text(text)
    # Scripts render at ~72% size; treat them as a whole character anyway,
    # which errs toward reserving slightly too much room rather than clipping.
    plain = re.sub(r"[\^_]", "", plain)
    return len(plain) * font_size * 0.6
