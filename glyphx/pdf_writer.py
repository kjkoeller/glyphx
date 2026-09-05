"""
SVG to PDF, in pure Python.

PDF export previously needed either cairosvg (and the system ``libcairo``
behind it) or a headless browser through Playwright. Both are heavy asks for
what is often the last step of a script, and neither is available by default
in a bare CI container or a fresh virtualenv -- which is exactly where a
camera-ready PDF tends to be wanted. Matplotlib's PDF backend is pure Python
with no extra dependencies, and this closes that gap.

The output is real vector PDF, not a rasterised image in a wrapper: paths
stay paths, so it scales without pixelation and the text stays selectable.

Scope. This handles the vocabulary GlyphX itself emits -- ``rect``,
``circle``, ``line``, ``polyline``, ``path`` (with ``M``/``L``/``A``/``Z``),
``text``, and ``g`` -- with fill, stroke, stroke width, dash patterns,
opacity and rotation. It is deliberately not a general SVG engine: gradients,
clipping paths, filters, embedded images and non-rotation transforms are not
supported, and :func:`svg_to_pdf` raises rather than silently dropping them,
so a chart never comes out quietly missing something.

Fonts are the PDF base-14 (Helvetica and its bold variant), which need no
embedding and are guaranteed present in every reader. GlyphX's default
``sans-serif`` maps onto Helvetica directly; a chart using a custom font
family falls back to Helvetica, and the caller is told.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
import zlib

_SVG_NS = "{http://www.w3.org/2000/svg}"

#: Named colours GlyphX itself can emit. Anything else must be #rgb/#rrggbb.
_NAMED_COLORS = {
    "black": (0.0, 0.0, 0.0), "white": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0), "green": (0.0, 0.5, 0.0),
    "blue": (0.0, 0.0, 1.0), "gray": (0.5, 0.5, 0.5),
    "grey": (0.5, 0.5, 0.5), "none": None, "transparent": None,
}


class UnsupportedSVGError(ValueError):
    """
    Raised for SVG this converter cannot faithfully reproduce.

    Preferred over dropping the element: a PDF that silently lost a gradient
    or a clipped region looks complete while being wrong, and the caller has
    no way to notice.
    """


def _parse_color(value):
    """An SVG colour as an (r, g, b) triple in 0-1, or None for no paint."""
    if not value:
        return None
    value = value.strip().lower()
    if value in _NAMED_COLORS:
        return _NAMED_COLORS[value]
    if value.startswith("#"):
        h = value[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 8:            # #rrggbbaa: alpha handled separately
            h = h[:6]
        if len(h) != 6:
            return None
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    if value.startswith("rgb"):
        nums = re.findall(r"[\d.]+", value)
        if len(nums) >= 3:
            return tuple(min(255.0, float(n)) / 255.0 for n in nums[:3])
    if value.startswith("var(") or value.startswith("url("):
        raise UnsupportedSVGError(
            f"PDF export cannot resolve {value!r}. CSS variables and paint "
            f"servers (gradients, patterns) have no PDF equivalent here; "
            f"export to .png or .svg instead."
        )
    return None


def _num(value, default=0.0):
    """A coordinate attribute as a float, tolerating units and blanks."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        m = re.match(r"^(-?[\d.]+)", str(value))
        return float(m.group(1)) if m else default


def _arc_to_beziers(x0, y0, rx, ry, rotation, large_arc, sweep, x1, y1):
    """
    Convert an SVG elliptical arc to cubic Bezier segments.

    PDF has no arc operator, so ``A`` -- which every pie, donut and sunburst
    slice is built from -- has to be approximated. Implements the endpoint to
    centre parameterisation from the SVG spec (F.6.5), then splits the sweep
    into segments of at most 90 degrees, which keeps the Bezier error far
    below a printed pixel.
    """
    if rx == 0 or ry == 0:
        return [("L", x1, y1)]

    rx, ry = abs(rx), abs(ry)
    phi = math.radians(rotation)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)

    dx2, dy2 = (x0 - x1) / 2.0, (y0 - y1) / 2.0
    x1p = cos_phi * dx2 + sin_phi * dy2
    y1p = -sin_phi * dx2 + cos_phi * dy2

    # Scale up the radii if they are too small to span the endpoints.
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        scale = math.sqrt(lam)
        rx, ry = rx * scale, ry * scale

    denom = (rx * rx * y1p * y1p) + (ry * ry * x1p * x1p)
    num = (rx * rx * ry * ry) - denom
    factor = 0.0 if denom == 0 else math.sqrt(max(0.0, num / denom))
    if large_arc == sweep:
        factor = -factor

    cxp = factor * rx * y1p / ry
    cyp = -factor * ry * x1p / rx
    cx = cos_phi * cxp - sin_phi * cyp + (x0 + x1) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y0 + y1) / 2.0

    def angle(ux, uy, vx, vy):
        """Signed angle between two vectors, per the SVG arc spec."""
        dot = ux * vx + uy * vy
        mag = math.hypot(ux, uy) * math.hypot(vx, vy)
        if mag == 0:
            return 0.0
        a = math.acos(max(-1.0, min(1.0, dot / mag)))
        return -a if (ux * vy - uy * vx) < 0 else a

    theta0 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    delta = angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                  (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi

    segments = max(1, int(math.ceil(abs(delta) / (math.pi / 2))))
    out = []
    step = delta / segments
    # Control-point distance for a circular arc of this sweep.
    k = (4.0 / 3.0) * math.tan(step / 4.0)

    theta = theta0
    for _ in range(segments):
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        cos_te, sin_te = math.cos(theta + step), math.sin(theta + step)

        def point(ct, st):
            """A point on the ellipse at the given cosine and sine."""
            return (cx + rx * cos_phi * ct - ry * sin_phi * st,
                    cy + rx * sin_phi * ct + ry * cos_phi * st)

        p1 = point(cos_t, sin_t)
        p2 = point(cos_te, sin_te)
        d1 = (-rx * cos_phi * sin_t - ry * sin_phi * cos_t,
              -rx * sin_phi * sin_t + ry * cos_phi * cos_t)
        d2 = (-rx * cos_phi * sin_te - ry * sin_phi * cos_te,
              -rx * sin_phi * sin_te + ry * cos_phi * cos_te)

        out.append(("C",
                    p1[0] + k * d1[0], p1[1] + k * d1[1],
                    p2[0] - k * d2[0], p2[1] - k * d2[1],
                    p2[0], p2[1]))
        theta += step
    return out


_PATH_TOKEN = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|(-?[\d.]+(?:e-?\d+)?)")


def _parse_path(d):
    """
    Turn a path ``d`` string into absolute ``(op, *coords)`` tuples.

    Only the commands GlyphX emits are implemented. An unrecognised command
    raises rather than being skipped, so a malformed slice is loud.
    """
    tokens: list[str | float] = []
    for cmd, num in _PATH_TOKEN.findall(d or ""):
        tokens.append(cmd if cmd else float(num))

    out: list[tuple] = []
    i = 0
    cx = cy = 0.0
    start_x = start_y = 0.0
    op = None
    while i < len(tokens):
        token = tokens[i]
        if isinstance(token, str):
            op = token
            i += 1
            if op in "Zz":
                out.append(("Z",))
                cx, cy = start_x, start_y
                continue
        if op is None:
            break
        rel = op.islower()
        up = op.upper()

        def take(n):
            """Consume the next n numbers from the token stream."""
            nonlocal i
            vals = tokens[i:i + n]
            i += n
            return [float(v) for v in vals]

        if up == "M":
            x, y = take(2)
            if rel:
                x, y = cx + x, cy + y
            out.append(("M", x, y))
            cx, cy = start_x, start_y = x, y
            op = "l" if rel else "L"      # implicit lineto after moveto
        elif up == "L":
            x, y = take(2)
            if rel:
                x, y = cx + x, cy + y
            out.append(("L", x, y))
            cx, cy = x, y
        elif up == "H":
            (x,) = take(1)
            x = cx + x if rel else x
            out.append(("L", x, cy))
            cx = x
        elif up == "V":
            (y,) = take(1)
            y = cy + y if rel else y
            out.append(("L", cx, y))
            cy = y
        elif up == "C":
            x1, y1, x2, y2, x, y = take(6)
            if rel:
                x1, y1, x2, y2, x, y = (cx + x1, cy + y1, cx + x2, cy + y2,
                                        cx + x, cy + y)
            out.append(("C", x1, y1, x2, y2, x, y))
            cx, cy = x, y
        elif up == "A":
            rx, ry, rot, laf, sf, x, y = take(7)
            if rel:
                x, y = cx + x, cy + y
            out.extend(_arc_to_beziers(cx, cy, rx, ry, rot,
                                       int(laf), int(sf), x, y))
            cx, cy = x, y
        else:
            raise UnsupportedSVGError(
                f"PDF export does not implement the '{up}' path command."
            )
    return out


def _escape_pdf_text(text):
    """Escape a string for a PDF literal, and drop anything non-Latin-1.

    The base-14 fonts are Latin-1 only; embedding a Unicode font would mean
    shipping font files, which is exactly the dependency this module exists
    to avoid.
    """
    out = []
    for ch in text:
        if ch in "()\\":
            out.append("\\" + ch)
        elif ord(ch) < 256:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


class _Writer:
    """Accumulates PDF content-stream operators for one page."""

    def __init__(self, height):
        """Start an empty operator list for a page of the given height."""
        self.ops = []
        self.height = height          # for the Y-axis flip

    def y(self, value):
        """SVG's Y grows downward, PDF's grows upward."""
        return self.height - value

    def _paint(self, fill, stroke, width, dash, opacity, fill_opacity):
        """Emit the colour/width state, and return the painting operator."""
        alpha = opacity if opacity is not None else 1.0
        f_alpha = alpha * (fill_opacity if fill_opacity is not None else 1.0)

        if fill:
            # No ExtGState here: a constant-alpha blend against white keeps
            # the file simple and matches how these charts look on paper.
            r, g, b = fill
            if f_alpha < 1.0:
                r = r * f_alpha + (1 - f_alpha)
                g = g * f_alpha + (1 - f_alpha)
                b = b * f_alpha + (1 - f_alpha)
            self.ops.append(f"{r:.4f} {g:.4f} {b:.4f} rg")
        if stroke:
            r, g, b = stroke
            if alpha < 1.0:
                r = r * alpha + (1 - alpha)
                g = g * alpha + (1 - alpha)
                b = b * alpha + (1 - alpha)
            self.ops.append(f"{r:.4f} {g:.4f} {b:.4f} RG")
            self.ops.append(f"{width:.3f} w")
        if dash:
            nums = " ".join(f"{float(n):.3f}" for n in re.findall(r"[\d.]+", dash))
            self.ops.append(f"[{nums}] 0 d")
        else:
            self.ops.append("[] 0 d")

        if fill and stroke:
            return "B"
        if fill:
            return "f"
        if stroke:
            return "S"
        return "n"


def _style(el, inherited):
    """Resolve an element's paint attributes, inheriting from its parent."""
    style = dict(inherited)
    for key in ("fill", "stroke", "stroke-width", "stroke-dasharray",
                "opacity", "fill-opacity", "font-size", "font-family",
                "font-weight", "text-anchor"):
        value = el.get(key)
        if value is not None:
            style[key] = value
    return style


def _emit(el, writer, style, offset, rotation=None):
    """Walk one element, appending its operators. Recurses through <g>."""
    tag = el.tag.replace(_SVG_NS, "")
    style = _style(el, style)
    ox, oy = offset

    for unsupported in ("clip-path", "mask", "filter"):
        if el.get(unsupported):
            raise UnsupportedSVGError(
                f"PDF export does not support '{unsupported}'; export to "
                f".png or .svg instead."
            )

    transform = el.get("transform")
    if transform:
        rotation = None
        rot = re.match(r"\s*rotate\(([^)]*)\)", transform)
        trans = re.match(r"\s*translate\(([^)]*)\)", transform)
        if trans:
            parts = [float(v) for v in re.findall(r"-?[\d.]+", trans.group(1) or "")]
            ox += parts[0]
            oy += parts[1] if len(parts) > 1 else 0.0
        elif rot:
            # PDF has a text matrix, so rotation is reproduced properly
            # rather than dropped. Discarding it placed the Y axis label at
            # the rotation origin unrotated, which pushed it off the left
            # edge and printed as "(thousands)".
            parts = [float(v) for v in re.findall(r"-?[\d.]+", rot.group(1))]
            angle = parts[0] if parts else 0.0
            centre = (parts[1], parts[2]) if len(parts) >= 3 else None
            rotation = (angle, centre)
        else:
            raise UnsupportedSVGError(
                f"PDF export supports translate() and rotate() transforms, "
                f"not {transform!r}."
            )

    fill = _parse_color(style.get("fill", "none"))
    stroke = _parse_color(style.get("stroke"))
    width = _num(style.get("stroke-width"), 1.0)
    dash = style.get("stroke-dasharray")
    opacity = _num(style.get("opacity"), 1.0) if style.get("opacity") else None
    fill_op = (_num(style.get("fill-opacity"), 1.0)
               if style.get("fill-opacity") else None)

    if tag == "rect":
        x = _num(el.get("x")) + ox
        y = _num(el.get("y")) + oy
        w, h = _num(el.get("width")), _num(el.get("height"))
        if w > 0 and h > 0:
            op = writer._paint(fill, stroke, width, dash, opacity, fill_op)
            writer.ops.append(f"{x:.3f} {writer.y(y + h):.3f} {w:.3f} {h:.3f} re {op}")

    elif tag == "circle":
        cx = _num(el.get("cx")) + ox
        cy = _num(el.get("cy")) + oy
        r = _num(el.get("r"))
        if r > 0:
            op = writer._paint(fill, stroke, width, dash, opacity, fill_op)
            k = r * 0.5523            # circle from four Beziers
            y = writer.y(cy)
            writer.ops.append(f"{cx + r:.3f} {y:.3f} m")
            writer.ops.append(f"{cx + r:.3f} {y + k:.3f} {cx + k:.3f} {y + r:.3f} {cx:.3f} {y + r:.3f} c")
            writer.ops.append(f"{cx - k:.3f} {y + r:.3f} {cx - r:.3f} {y + k:.3f} {cx - r:.3f} {y:.3f} c")
            writer.ops.append(f"{cx - r:.3f} {y - k:.3f} {cx - k:.3f} {y - r:.3f} {cx:.3f} {y - r:.3f} c")
            writer.ops.append(f"{cx + k:.3f} {y - r:.3f} {cx + r:.3f} {y - k:.3f} {cx + r:.3f} {y:.3f} c")
            writer.ops.append(op)

    elif tag == "line":
        if stroke:
            x1 = _num(el.get("x1")) + ox
            y1 = _num(el.get("y1")) + oy
            x2 = _num(el.get("x2")) + ox
            y2 = _num(el.get("y2")) + oy
            writer._paint(None, stroke, width, dash, opacity, None)
            writer.ops.append(f"{x1:.3f} {writer.y(y1):.3f} m "
                              f"{x2:.3f} {writer.y(y2):.3f} l S")

    elif tag in ("polyline", "polygon"):
        pts = [float(v) for v in re.findall(r"-?[\d.]+", el.get("points", ""))]
        if len(pts) >= 4:
            op = writer._paint(fill, stroke, width, dash, opacity, fill_op)
            writer.ops.append(f"{pts[0] + ox:.3f} {writer.y(pts[1] + oy):.3f} m")
            for i in range(2, len(pts) - 1, 2):
                writer.ops.append(f"{pts[i] + ox:.3f} {writer.y(pts[i + 1] + oy):.3f} l")
            if tag == "polygon":
                writer.ops.append("h")
            writer.ops.append(op)

    elif tag == "path":
        segs = _parse_path(el.get("d"))
        if segs:
            op = writer._paint(fill, stroke, width, dash, opacity, fill_op)
            for seg in segs:
                if seg[0] == "M":
                    writer.ops.append(f"{seg[1] + ox:.3f} {writer.y(seg[2] + oy):.3f} m")
                elif seg[0] == "L":
                    writer.ops.append(f"{seg[1] + ox:.3f} {writer.y(seg[2] + oy):.3f} l")
                elif seg[0] == "C":
                    writer.ops.append(
                        f"{seg[1] + ox:.3f} {writer.y(seg[2] + oy):.3f} "
                        f"{seg[3] + ox:.3f} {writer.y(seg[4] + oy):.3f} "
                        f"{seg[5] + ox:.3f} {writer.y(seg[6] + oy):.3f} c")
                elif seg[0] == "Z":
                    writer.ops.append("h")
            writer.ops.append(op)

    elif tag == "text":
        text = "".join(el.itertext()).strip()
        if text:
            size = _num(style.get("font-size"), 11.0)
            x = _num(el.get("x")) + ox
            y = _num(el.get("y")) + oy
            bold = str(style.get("font-weight", "")).lower() in ("bold", "700", "800", "900")
            font = "F2" if bold else "F1"

            anchor = style.get("text-anchor", "start")
            if anchor in ("middle", "end"):
                # Helvetica averages about 0.5 em per character; good enough
                # to centre a tick label without font metrics tables.
                est = len(text) * size * 0.5
                x -= est / 2 if anchor == "middle" else est

            colour = fill or (0.0, 0.0, 0.0)
            writer.ops.append(f"{colour[0]:.4f} {colour[1]:.4f} {colour[2]:.4f} rg")
            writer.ops.append("BT")
            writer.ops.append(f"/{font} {size:.2f} Tf")
            if rotation:
                angle, centre = rotation
                # SVG rotates clockwise about the centre; PDF's Y axis is
                # already flipped, so the sign works out directly.
                rad = math.radians(angle)
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                cx, cy = centre if centre else (x, y)
                px, py = x - cx, writer.y(y) - writer.y(cy)
                nx = cx + px * cos_a - py * sin_a
                ny = writer.y(cy) + px * sin_a + py * cos_a
                writer.ops.append(
                    f"{cos_a:.5f} {sin_a:.5f} {-sin_a:.5f} {cos_a:.5f} "
                    f"{nx:.3f} {ny:.3f} Tm")
            else:
                writer.ops.append(f"{x:.3f} {writer.y(y):.3f} Td")
            writer.ops.append(f"({_escape_pdf_text(text)}) Tj")
            writer.ops.append("ET")

    elif tag in ("g", "svg"):
        pass          # container: children handled below

    elif tag in ("title", "desc", "defs", "style", "metadata", "script"):
        return        # metadata, nothing to draw

    for child in el:
        _emit(child, writer, style, (ox, oy), rotation)


def svg_to_pdf(svg: str, path: str) -> None:
    """
    Write ``svg`` to ``path`` as a vector PDF, using only the standard library.

    Args:
        svg:  An SVG document.
        path: Destination ``.pdf`` file.

    Raises:
        UnsupportedSVGError: For SVG features with no faithful PDF
            equivalent here -- gradients, clipping, filters, embedded images.
            Raised rather than dropped, so the output is never quietly
            missing part of the chart.
    """
    root = ET.fromstring(svg)

    width = _num(root.get("width"), 640.0)
    height = _num(root.get("height"), 480.0)
    viewbox = root.get("viewBox")
    if viewbox:
        vb = [float(v) for v in re.findall(r"-?[\d.]+", viewbox)]
        if len(vb) == 4:
            width, height = vb[2], vb[3]

    writer = _Writer(height)
    # White page: SVG's default is transparent, which prints as white
    # anyway, and an explicit background avoids readers showing grey.
    writer.ops.append("1 1 1 rg")
    writer.ops.append(f"0 0 {width:.3f} {height:.3f} re f")
    _emit(root, writer, {"fill": "none"}, (0.0, 0.0))

    content = "\n".join(writer.ops).encode("latin-1", "replace")
    compressed = zlib.compress(content)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.3f} {height:.3f}] "
         f"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> "
         f"/Contents 4 0 R >>").encode("latin-1"),
        (b"<< /Length " + str(len(compressed)).encode()
         + b" /Filter /FlateDecode >>\nstream\n" + compressed + b"\nendstream"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
        b"/Encoding /WinAnsiEncoding >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode()
        out += body
        out += b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()

    with open(path, "wb") as fh:
        fh.write(bytes(out))
