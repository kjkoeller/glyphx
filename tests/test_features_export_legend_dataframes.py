"""
Tests for interactive legends, multi-backend export, and dataframe interop.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

import glyphx
from glyphx import Figure

# ---------------------------------------------------------------------------
# Interactive legend
# ---------------------------------------------------------------------------


@pytest.fixture
def two_series_fig():
    return (
        Figure(auto_display=False)
        .line([1, 2, 3], [1.0, 2.0, 3.0], label="alpha")
        .line([1, 2, 3], [3.0, 2.0, 1.0], label="beta")
    )


def test_legend_entries_target_their_series(two_series_fig):
    """The toggle works by class lookup, so the wiring has to line up."""
    svg = two_series_fig.render_svg()
    root = ET.fromstring(svg)

    targets = {
        el.get("data-target")
        for el in root.iter()
        if el.get("data-target")
    }
    assert targets, "legend entries must carry data-target"

    for target in targets:
        matching = [
            el for el in root.iter()
            if target in (el.get("class") or "").split()
            and not el.get("data-target")
        ]
        assert matching, f"no series elements carry the class {target!r}"


def test_legend_script_is_included_in_html_export(two_series_fig):
    html = glyphx.utils.make_shareable_html(two_series_fig.render_svg())
    assert "glyphx-series-hidden" in html, "legend.js was not inlined"


def test_legend_script_supports_keyboard_and_aria(two_series_fig):
    html = glyphx.utils.make_shareable_html(two_series_fig.render_svg())
    assert 'setAttribute("tabindex"' in html, "legend must be focusable"
    assert "aria-pressed" in html, "toggle state must be exposed to a11y tools"
    assert 'role", "switch"' in html or "'switch'" in html


def test_legend_script_does_not_hide_the_legend_itself(two_series_fig):
    """Legend entries share the target class; hiding them would be a bug."""
    html = glyphx.utils.make_shareable_html(two_series_fig.render_svg())
    assert 'hasAttribute("data-target")' in html


def test_legend_omitted_when_no_series_is_labelled():
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    assert "legend-icon" not in svg


# ---------------------------------------------------------------------------
# Export backends
# ---------------------------------------------------------------------------

from glyphx.export import (  # noqa: E402
    ExportError,
    UnsupportedFormatError,
    available_backends,
    render_to_file,
)

_BACKENDS = available_backends()
_needs_backend = pytest.mark.skipif(not _BACKENDS, reason="no export backend installed")


def test_available_backends_returns_a_list():
    assert isinstance(available_backends(), list)


@_needs_backend
@pytest.mark.parametrize("ext,magic", [
    (".png", b"\x89PNG"),
    (".jpg", b"\xff\xd8\xff"),
    (".webp", b"RIFF"),
])
def test_raster_export_writes_the_right_format(tmp_path, ext, magic):
    """`.jpg` used to be written as PNG bytes under a JPEG filename."""
    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0])
    out = tmp_path / f"chart{ext}"
    try:
        fig.save(str(out))
    except ExportError as exc:
        pytest.skip(f"no backend for {ext}: {exc}")
    assert out.read_bytes().startswith(magic)


@_needs_backend
def test_dpi_increases_output_size(tmp_path):
    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0])
    low, high = tmp_path / "low.png", tmp_path / "high.png"
    try:
        fig.save(str(low), dpi=96)
        fig.save(str(high), dpi=192)
    except ExportError as exc:
        pytest.skip(str(exc))
    assert high.stat().st_size > low.stat().st_size


def test_unsupported_extension_is_a_value_error(tmp_path):
    """Callers have always caught ValueError here; keep that contract."""
    fig = Figure(auto_display=False)
    with pytest.raises(ValueError, match="Unsupported"):
        fig.save(str(tmp_path / "chart.tiff"))
    with pytest.raises(ExportError):
        fig.save(str(tmp_path / "chart.tiff"))


def test_unknown_backend_is_rejected(tmp_path):
    fig = Figure(auto_display=False).line([1, 2], [1.0, 2.0])
    with pytest.raises(ExportError, match="Unknown backend"):
        fig.save(str(tmp_path / "chart.png"), backend="nope")


def test_missing_backend_error_lists_every_option(tmp_path, monkeypatch):
    monkeypatch.setattr("glyphx.export.available_backends", lambda: [])
    with pytest.raises(ExportError) as exc:
        render_to_file("<svg/>", str(tmp_path / "chart.png"))
    message = str(exc.value)
    for hint in ("glyphx[export]", "glyphx[cairo]", "glyphx[browser]", ".svg"):
        assert hint in message


def test_unsupported_format_error_is_both_types():
    assert issubclass(UnsupportedFormatError, ValueError)
    assert issubclass(UnsupportedFormatError, ExportError)


def test_svg_and_html_need_no_backend(tmp_path, monkeypatch):
    monkeypatch.setattr("glyphx.export.available_backends", lambda: [])
    fig = Figure(auto_display=False).line([1, 2], [1.0, 2.0])
    fig.save(str(tmp_path / "chart.svg"))
    fig.save(str(tmp_path / "chart.html"))
    assert (tmp_path / "chart.svg").exists()
    assert (tmp_path / "chart.html").exists()


# ---------------------------------------------------------------------------
# Dataframe interop
# ---------------------------------------------------------------------------

from glyphx.dataframes import (  # noqa: E402
    column_names,
    get_column,
    is_dataframe,
    to_columns,
    to_pandas,
)


def _frames() -> dict:
    """Every dataframe library available in this environment."""
    import pandas as pd

    frames = {"pandas": pd.DataFrame({"m": [1, 2, 3], "v": [4.0, 5.0, 6.0]}),
              "dict": {"m": [1, 2, 3], "v": [4.0, 5.0, 6.0]}}
    try:
        import polars as pl
        frames["polars"] = pl.DataFrame({"m": [1, 2, 3], "v": [4.0, 5.0, 6.0]})
    except ImportError:
        pass
    try:
        import pyarrow as pa
        frames["arrow"] = pa.table({"m": [1, 2, 3], "v": [4.0, 5.0, 6.0]})
    except ImportError:
        pass
    return frames


FRAMES = _frames()


@pytest.mark.parametrize("kind", sorted(FRAMES))
def test_is_dataframe_recognises_every_backend(kind):
    assert is_dataframe(FRAMES[kind])


@pytest.mark.parametrize("kind", sorted(FRAMES))
def test_column_names_are_strings(kind):
    assert column_names(FRAMES[kind]) == ["m", "v"]


@pytest.mark.parametrize("kind", sorted(FRAMES))
def test_get_column_returns_plain_lists(kind):
    values = get_column(FRAMES[kind], "v")
    assert isinstance(values, list)
    assert values == [4.0, 5.0, 6.0]


@pytest.mark.parametrize("kind", sorted(FRAMES))
def test_to_columns_round_trip(kind):
    assert to_columns(FRAMES[kind]) == {"m": [1, 2, 3], "v": [4.0, 5.0, 6.0]}


@pytest.mark.parametrize("kind", sorted(FRAMES))
def test_to_pandas_conversion(kind):
    import pandas as pd

    out = to_pandas(FRAMES[kind])
    assert isinstance(out, pd.DataFrame)
    assert list(out.columns) == ["m", "v"]


@pytest.mark.parametrize("kind", sorted(FRAMES))
@pytest.mark.parametrize("chart", ["line", "bar", "scatter"])
def test_plot_accepts_column_names_from_any_dataframe(kind, chart):
    svg = glyphx.plot(
        x="m", y="v", data=FRAMES[kind], kind=chart, auto_display=False
    ).render_svg()
    ET.fromstring(svg)


def test_missing_column_names_the_available_ones():
    with pytest.raises(KeyError) as exc:
        get_column(FRAMES["pandas"], "nope")
    assert "'m', 'v'" in str(exc.value)


def test_non_dataframe_inputs_are_rejected():
    assert not is_dataframe(None)
    assert not is_dataframe([1, 2, 3])
    assert not is_dataframe("abc")
    assert not is_dataframe({})


def test_raw_sequences_still_work_without_a_dataframe():
    """The adapter must not intercept ordinary list input."""
    svg = glyphx.plot([1, 2, 3], [4.0, 5.0, 6.0], kind="line",
                      auto_display=False).render_svg()
    ET.fromstring(svg)


# ---------------------------------------------------------------------------
# Asset hygiene
# ---------------------------------------------------------------------------

def test_no_js_asset_carries_its_own_script_tags():
    """
    Assets are inlined as ``<script>{js}</script>``.

    export.js and tooltip.js used to ship with their own wrapping tags, so
    the inner ``</script>`` closed the block early and every script after it
    on the page died silently -- tooltips, zoom, brushing, and keyboard
    accessibility were all dead in exported HTML.
    """
    from pathlib import Path

    import glyphx

    assets = Path(glyphx.__file__).parent / "assets"
    offenders = [
        p.name for p in assets.glob("*.js")
        if "<script" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"JS assets must not contain script tags: {offenders}"


def test_exported_html_has_no_nested_script_tags(two_series_fig):
    import re

    html = glyphx.utils.make_shareable_html(two_series_fig.render_svg())
    blocks = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    assert blocks, "expected inlined scripts"
    for block in blocks:
        assert "<script" not in block, "nested script tag would break the page"


def test_script_tag_stripper_is_idempotent():
    from glyphx.utils import _strip_script_tags

    assert _strip_script_tags("<script>\nfoo();\n</script>") == "foo();"
    assert _strip_script_tags("foo();") == "foo();"
    assert _strip_script_tags(_strip_script_tags("<script>foo();</script>")) == "foo();"


# ---------------------------------------------------------------------------
# File encoding
# ---------------------------------------------------------------------------

NON_ASCII_TITLE = "Market Share 2024  —  µ ± σ  °C  “quoted”"


def test_saved_svg_is_utf8_with_non_ascii_text(tmp_path):
    """
    Non-ASCII in a title must survive round-tripping to disk.

    examples.py wrote files with Path.write_text() and no encoding, which
    uses the platform's preferred codec -- cp1252 on a default Windows
    install.  The em dash in the example titles became byte 0x97, which is
    not valid UTF-8, so browsers refused every file with
    "error on line 1: Encoding error" and rendered nothing.
    """
    fig = Figure(auto_display=False, title=NON_ASCII_TITLE)
    fig.line([1, 2, 3], [1.0, 2.0, 3.0], label="Revenue")

    out = tmp_path / "chart.svg"
    fig.save(str(out))

    raw = out.read_bytes()
    raw.decode("utf-8")                      # raises if the codec was wrong
    assert "\u2014".encode() in raw, "em dash must be UTF-8 encoded"


def test_saved_svg_declares_its_encoding(tmp_path):
    """A standalone .svg is parsed as XML; state the encoding explicitly."""
    fig = Figure(auto_display=False, title=NON_ASCII_TITLE)
    fig.line([1, 2], [1.0, 2.0])
    out = tmp_path / "chart.svg"
    fig.save(str(out))

    raw = out.read_bytes()
    assert raw.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')


def test_saved_svg_parses_as_xml(tmp_path):
    import xml.etree.ElementTree as ET

    fig = Figure(auto_display=False, title=NON_ASCII_TITLE)
    fig.line([1, 2, 3], [1.0, 2.0, 3.0], label="Revenue")
    out = tmp_path / "chart.svg"
    fig.save(str(out))

    root = ET.fromstring(out.read_bytes())   # bytes, so the decl is honoured
    assert root.tag.endswith("svg")


def test_xml_declaration_is_not_duplicated(tmp_path):
    from glyphx.utils import write_svg_file

    declared = '<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>'
    out = tmp_path / "chart.svg"
    write_svg_file(declared, str(out))
    assert out.read_bytes().count(b"<?xml") == 1


def test_html_export_is_utf8(tmp_path):
    fig = Figure(auto_display=False, title=NON_ASCII_TITLE)
    fig.line([1, 2], [1.0, 2.0])
    out = tmp_path / "chart.html"
    fig.save(str(out))
    out.read_bytes().decode("utf-8")


def test_no_text_file_is_written_without_an_explicit_encoding():
    """
    Guard the whole repo against this bug class.

    Path.write_text / open(..., "w") without encoding= silently follows the
    machine's locale, so a file that is fine on Linux CI is corrupt on a
    contributor's Windows box.  Parsed with ast rather than a regex so
    docstring examples and webbrowser.open() are not counted.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    offenders = []

    for path in list(root.glob("*.py")) + list((root / "glyphx").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name not in {"write_text", "open"}:
                continue
            if name == "open" and isinstance(func, ast.Attribute):
                continue                      # webbrowser.open and friends
            # Mode is the second positional argument. Read it by position:
            # filtering to constants first drops open(path, "wb") to one
            # element and loses the mode entirely.
            mode = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            if name == "open" and isinstance(mode, str) and "b" in mode:
                continue                      # binary needs no encoding
            if any(kw.arg == "encoding" for kw in node.keywords):
                continue
            offenders.append(f"{path.name}:{node.lineno} {name}()")

    assert offenders == [], (
        f"text written without encoding=: {offenders}"
    )
