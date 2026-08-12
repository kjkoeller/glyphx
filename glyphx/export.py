"""
Raster and PDF export backends.

SVG is GlyphX's native format, but people need PNGs for slides, papers, and
READMEs.  Historically that meant cairosvg, which links against system Cairo
and is a common installation failure on Windows and in slim containers.

This module tries the available backends in order of how likely they are to
be installed and to work, and raises a single actionable error listing every
option when none is present:

===========  ===================================  ==============  ===========
Backend      Install                              System deps     Formats
===========  ===================================  ==============  ===========
resvg        ``pip install glyphx[export]``       none (wheels)   PNG, JPEG
cairosvg     ``pip install glyphx[cairo]``        libcairo        PNG, PDF
playwright   ``pip install glyphx[browser]``      a browser       PNG, JPEG, PDF
===========  ===================================  ==============  ===========

resvg is preferred: it ships prebuilt wheels for every major platform, so it
works without a compiler or system libraries.
"""

from __future__ import annotations

import os
from collections.abc import Callable

#: Formats every backend is expected to understand.
RASTER_FORMATS = {".png", ".jpg", ".jpeg", ".webp"}
VECTOR_FORMATS = {".pdf"}


class ExportError(RuntimeError):
    """Raised when a figure cannot be exported in the requested format."""


class UnsupportedFormatError(ExportError, ValueError):
    """
    Raised for a file extension GlyphX cannot write.

    Inherits from both :class:`ExportError` and :class:`ValueError`: a bad
    extension is bad *input*, which callers have always caught as ValueError,
    whereas a missing backend is an environment problem and stays a plain
    ExportError (a RuntimeError).
    """


# Backend availability

def _have(module: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def available_backends() -> list[str]:
    """
    Return the export backends installed in this environment.

    Returns:
        list[str]: Backend names, best first.  Empty if none are installed.
    """
    found = []
    if _have("resvg_py"):
        found.append("resvg")
    if _have("cairosvg"):
        found.append("cairosvg")
    if _have("playwright"):
        found.append("playwright")
    return found


def _no_backend_error(ext: str) -> ExportError:
    return ExportError(
        f"Saving '{ext}' needs a rendering backend, and none is installed.\n"
        f"\n"
        f"  pip install 'glyphx[export]'    resvg -- prebuilt wheels, no system deps (recommended)\n"
        f"  pip install 'glyphx[cairo]'     cairosvg -- also does PDF, needs libcairo\n"
        f"  pip install 'glyphx[browser]'   playwright -- also does PDF, downloads a browser\n"
        f"\n"
        f"Or save the chart as .svg or .html, which need no extra packages."
    )


# Backends

def _render_resvg(svg: str, path: str, ext: str, dpi: int) -> None:
    import resvg_py

    if ext == ".pdf":
        raise ExportError("resvg cannot write PDF")

    png_bytes = bytes(resvg_py.svg_to_bytes(svg_string=svg, zoom=dpi / 96.0))

    if ext == ".png":
        with open(path, "wb") as fh:
            fh.write(png_bytes)
        return

    # resvg only emits PNG, so convert for the other raster formats rather
    # than writing PNG bytes under a .jpg name -- which is what the previous
    # cairosvg-only path did.
    try:
        import io

        from PIL import Image
    except ImportError:
        raise ExportError(
            f"Writing '{ext}' from the resvg backend needs Pillow "
            f"(pip install pillow), or save as .png instead."
        ) from None

    image = Image.open(io.BytesIO(png_bytes))
    if ext in {".jpg", ".jpeg"}:
        # JPEG has no alpha channel; composite onto white so transparent
        # chart backgrounds do not come out black.
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        image = background
    image.save(path)


def _render_cairosvg(svg: str, path: str, ext: str, dpi: int) -> None:
    import cairosvg

    scale = dpi / 96.0
    payload = svg.encode("utf-8")

    if ext == ".pdf":
        cairosvg.svg2pdf(bytestring=payload, write_to=path)
    elif ext == ".png":
        cairosvg.svg2png(bytestring=payload, write_to=path, scale=scale)
    else:
        raise ExportError(f"cairosvg cannot write '{ext}'")


def _render_playwright(svg: str, path: str, ext: str, dpi: int) -> None:
    from playwright.sync_api import sync_playwright

    html = f"<!doctype html><meta charset='utf-8'><body style='margin:0'>{svg}</body>"

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(device_scale_factor=dpi / 96.0)
            page.set_content(html)
            element = page.query_selector("svg")
            if ext == ".pdf":
                page.pdf(path=path, print_background=True)
            elif element is not None:
                element.screenshot(path=path)
            else:
                page.screenshot(path=path, full_page=True)
        finally:
            browser.close()


_BACKENDS: dict[str, Callable[[str, str, str, int], None]] = {
    "resvg": _render_resvg,
    "cairosvg": _render_cairosvg,
    "playwright": _render_playwright,
}

#: Which backends can produce which formats, best first.
_PREFERENCE: dict[str, tuple[str, ...]] = {
    ".png":  ("resvg", "cairosvg", "playwright"),
    ".jpg":  ("resvg", "playwright"),
    ".jpeg": ("resvg", "playwright"),
    ".webp": ("resvg", "playwright"),
    ".pdf":  ("cairosvg", "playwright"),
}


def render_to_file(svg: str, path: str, dpi: int = 96,
                   backend: str | None = None) -> str:
    """
    Rasterise ``svg`` to ``path``, choosing an available backend.

    Args:
        svg (str): The SVG document to convert.
        path (str): Output path; its extension selects the format.
        dpi (int): Target resolution. 96 is CSS-pixel scale; 192 is retina,
            300 is print.
        backend (str | None): Force a specific backend by name. Defaults to
            the best available one for the format.

    Returns:
        str: The backend that produced the file.

    Raises:
        ExportError: If the format is unsupported, or no backend can write it.
    """
    ext = os.path.splitext(path)[-1].lower()
    if ext not in _PREFERENCE:
        raise UnsupportedFormatError(
            f"Unsupported export format '{ext}'. "
            f"Supported: {', '.join(sorted(_PREFERENCE))}, plus .svg and .html."
        )

    if backend is not None:
        if backend not in _BACKENDS:
            raise ExportError(
                f"Unknown backend '{backend}'. "
                f"Choose from: {', '.join(sorted(_BACKENDS))}."
            )
        candidates: tuple[str, ...] = (backend,)
    else:
        installed = set(available_backends())
        candidates = tuple(b for b in _PREFERENCE[ext] if b in installed)

    if not candidates:
        installed = available_backends()
        if installed:
            raise ExportError(
                f"None of the installed backends ({', '.join(installed)}) can "
                f"write '{ext}'. Backends that can: "
                f"{', '.join(_PREFERENCE[ext])}."
            )
        raise _no_backend_error(ext)

    errors: list[str] = []
    for name in candidates:
        try:
            _BACKENDS[name](svg, path, ext, dpi)
            return name
        except ExportError as exc:
            errors.append(f"{name}: {exc}")
        except ImportError as exc:
            errors.append(f"{name}: not installed ({exc})")
        except Exception as exc:  # backend failed at runtime; try the next
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    detail = "\n  ".join(errors)
    raise ExportError(f"Could not write '{path}'. Backends tried:\n  {detail}")
