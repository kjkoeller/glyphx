"""
Tests for input validation and axis-domain behaviour.

Covers the cases where GlyphX previously rendered something misleading
rather than failing: non-positive values on a log axis, mismatched x/y
lengths, and empty series.
"""

import re
import warnings
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from glyphx import Figure, LineSeries

SVG_NS = "{http://www.w3.org/2000/svg}"


def _polylines(svg: str) -> list:
    root = ET.fromstring(svg)
    return [
        el for el in root.iter(f"{SVG_NS}polyline")
        if (el.get("class") or "").startswith("series-")
    ]


# ---------------------------------------------------------------------------
# Log axes
# ---------------------------------------------------------------------------

def test_log_axis_masks_non_positive_values():
    """y=0 used to map to the same pixel as y=100."""
    with pytest.warns(UserWarning, match="non-positive"):
        fig = Figure(auto_display=False, yscale="log").line([1, 2, 3], [0, 10, 100])
        svg = fig.render_svg()

    y_min, y_max = fig.axes._y_domain
    assert y_min > 0, "log domain must stay strictly positive"
    assert y_max > y_min

    pts = _polylines(svg)[0].get("points").split()
    assert len(pts) == 2, "the masked point must not be drawn"


def test_log_axis_warning_names_the_axis_and_count():
    with pytest.warns(UserWarning) as record:
        Figure(auto_display=False, yscale="log").line([1, 2, 3], [0, -5, 100]).render_svg()
    msg = str(record[0].message)
    assert "2 non-positive" in msg
    assert "y-axis" in msg


def test_log_axis_does_not_warn_on_clean_data():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Figure(auto_display=False, yscale="log").line([1, 2, 3], [1, 10, 100]).render_svg()


def test_log_domain_padding_stays_positive():
    """Additive padding pushed a 1..100 domain down to -5.93."""
    fig = Figure(auto_display=False, yscale="log").line([1, 2, 3], [1, 10, 100])
    fig.render_svg()
    y_min, y_max = fig.axes._y_domain
    assert y_min > 0
    assert y_min < 1 and y_max > 100, "padding should still leave breathing room"


def test_log_axis_with_all_values_masked_still_renders():
    with pytest.warns(UserWarning):
        svg = Figure(auto_display=False, yscale="log").line([1, 2], [0, -1]).render_svg()
    ET.fromstring(svg)


# ---------------------------------------------------------------------------
# x/y length validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method", ["line", "bar", "scatter"])
def test_mismatched_lengths_raise(method):
    fig = Figure(auto_display=False)
    with pytest.raises(ValueError, match="same length"):
        getattr(fig, method)([1, 2, 3], [1.0, 2.0])


def test_mismatch_error_reports_both_lengths():
    with pytest.raises(ValueError) as exc:
        LineSeries([1, 2, 3, 4], [1.0, 2.0])
    assert "len(x)=4" in str(exc.value)
    assert "len(y)=2" in str(exc.value)


def test_mismatched_lengths_raise_for_arrays():
    with pytest.raises(ValueError, match="same length"):
        LineSeries(np.arange(5), np.arange(4.0))


def test_equal_lengths_are_accepted():
    LineSeries([1, 2, 3], [1.0, 2.0, 3.0])          # must not raise
    LineSeries(np.arange(3), np.arange(3.0))


def test_box_and_hist_are_not_length_validated():
    """These legitimately pass differently-shaped x and y."""
    ET.fromstring(Figure(auto_display=False).box([[1, 2, 3], [4, 5, 6]]).render_svg())
    ET.fromstring(Figure(auto_display=False).hist([1, 2, 3, 4, 5]).render_svg())


# ---------------------------------------------------------------------------
# Empty data
# ---------------------------------------------------------------------------

def test_empty_series_renders_an_empty_frame():
    """Previously raised AttributeError: 'Axes' object has no attribute 'scale_y'."""
    svg = Figure(auto_display=False).line([], []).render_svg()
    ET.fromstring(svg)
    assert "No data to display" in svg


def test_empty_figure_renders():
    ET.fromstring(Figure(auto_display=False).render_svg())


def test_empty_series_alongside_populated_series_renders_the_data():
    fig = Figure(auto_display=False).line([], []).line([1, 2], [3.0, 4.0])
    svg = fig.render_svg()
    ET.fromstring(svg)
    assert "No data to display" not in svg
    assert fig.axes._y_domain is not None


def test_pie_still_routes_to_the_axis_free_branch():
    """Pie/donut/treemap pass x=None and must not gain an axes frame."""
    svg = Figure(auto_display=False).pie([1, 2, 3], labels=["a", "b", "c"]).render_svg()
    ET.fromstring(svg)
    assert "No data to display" not in svg


# ---------------------------------------------------------------------------
# Marker policy and coordinate precision
# ---------------------------------------------------------------------------

def test_small_series_keeps_per_point_markers():
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    assert svg.count("glyphx-point") == 3


def test_dense_series_suppresses_markers_by_default():
    n = LineSeries.MARKER_LIMIT + 50
    x = list(range(n))
    y = [float(v) for v in x]
    svg = Figure(auto_display=False).line(x, y).render_svg()
    assert "glyphx-point" not in svg
    assert _polylines(svg), "the line itself must still be drawn"


def test_markers_can_be_forced_on():
    n = LineSeries.MARKER_LIMIT + 10
    x = list(range(n))
    svg = Figure(auto_display=False).line(x, [float(v) for v in x], markers=True).render_svg()
    assert svg.count("glyphx-point") == n


def test_markers_can_be_forced_off():
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0], markers=False).render_svg()
    assert "glyphx-point" not in svg


def test_coordinates_are_rounded():
    """16 significant digits per coordinate is invisible and inflates the file."""
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    coords = re.findall(r"points=\"([^\"]+)\"", svg)
    assert coords, "expected a polyline"
    for value in coords[0].replace(",", " ").split():
        _, _, frac = value.partition(".")
        assert len(frac) <= 2, f"{value} carries more precision than requested"


# ---------------------------------------------------------------------------
# Lazy imports
# ---------------------------------------------------------------------------

def test_lazy_names_resolve():
    import glyphx
    assert glyphx.TreemapSeries.__name__ == "TreemapSeries"
    assert glyphx.ds_enable.__name__ == "enable"      # exported under an alias


def test_dir_lists_lazy_names():
    import glyphx
    names = dir(glyphx)
    assert "TreemapSeries" in names
    assert "Figure" in names


def test_unknown_attribute_raises_attribute_error():
    import glyphx
    with pytest.raises(AttributeError, match="no attribute"):
        _ = glyphx.NoSuchSeries  # noqa: B018 - access must trigger __getattr__


# ---------------------------------------------------------------------------
# 3D export integrity
# ---------------------------------------------------------------------------

def test_threejs_script_tag_is_integrity_pinned():
    from glyphx import Figure3D
    from glyphx.figure3d import _THREEJS_CDN, _THREEJS_SRI

    fig = Figure3D()
    fig.scatter([1, 2, 3], [1, 2, 3], [1, 2, 3])
    html = fig.render_html()

    assert _THREEJS_CDN in html
    assert f'integrity="{_THREEJS_SRI}"' in html
    assert 'crossorigin="anonymous"' in html
    assert _THREEJS_SRI.startswith("sha384-")


def test_threejs_url_is_version_pinned():
    """A floating 'latest' URL would invalidate the SRI hash on every release."""
    from glyphx.figure3d import _THREEJS_CDN, _THREEJS_VERSION

    assert _THREEJS_VERSION in _THREEJS_CDN
    assert "latest" not in _THREEJS_CDN


def test_3d_export_has_an_offline_fallback_message():
    from glyphx import Figure3D

    fig = Figure3D()
    fig.scatter([1, 2, 3], [1, 2, 3], [1, 2, 3])
    html = fig.render_html()
    assert 'typeof THREE === "undefined"' in html


def test_3d_html_leaves_no_unfilled_placeholders():
    from glyphx import Figure3D

    fig = Figure3D()
    fig.scatter([1, 2, 3], [1, 2, 3], [1, 2, 3])
    assert "{threejs" not in fig.render_html()


# ---------------------------------------------------------------------------
# Deterministic rendering
# ---------------------------------------------------------------------------

def _build_reference_figure():
    return (
        Figure(auto_display=False, title="Sales")
        .line([1, 2, 3], [1.0, 2.0, 3.0], label="alpha")
        .line([1, 2, 3], [3.0, 2.0, 1.0], label="beta")
    )


def test_rendering_is_reproducible_within_a_process():
    assert _build_reference_figure().render_svg() == _build_reference_figure().render_svg()


def test_rendering_is_reproducible_across_processes():
    """UUID-based ids made every render differ, defeating caching and diffs."""
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import hashlib
        from glyphx import Figure
        svg = (Figure(auto_display=False, title="Sales")
               .line([1, 2, 3], [1.0, 2.0, 3.0], label="alpha")
               .line([1, 2, 3], [3.0, 2.0, 1.0], label="beta")).render_svg()
        print(hashlib.sha256(svg.encode()).hexdigest())
    """)
    digests = set()
    for _ in range(3):
        result = subprocess.run([sys.executable, "-c", code],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        digests.add(result.stdout.strip())
    assert len(digests) == 1, "identical figures must render byte-identically"


def test_different_figures_get_different_ids():
    import re

    a = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    b = Figure(auto_display=False).line([1, 2, 3], [9.0, 8.0, 7.0]).render_svg()
    id_a = re.search(r'id="(glyphx-chart-[^"]+)"', a).group(1)
    id_b = re.search(r'id="(glyphx-chart-[^"]+)"', b).group(1)
    assert id_a != id_b


def test_identical_series_still_get_unique_classes():
    """Otherwise the legend would toggle both at once."""
    import re

    svg = (
        Figure(auto_display=False)
        .line([1, 2], [1.0, 2.0], label="a")
        .line([1, 2], [1.0, 2.0], label="a")
        .render_svg()
    )
    classes = set(re.findall(r"series-[0-9a-f]+(?:-\d+)?", svg))
    assert len(classes) == 2, f"expected two distinct classes, got {classes}"


def test_equal_figures_compare_equal():
    assert _build_reference_figure() == _build_reference_figure()


def test_different_figures_compare_unequal():
    other = Figure(auto_display=False).line([1, 2, 3], [5.0, 5.0, 5.0])
    assert _build_reference_figure() != other


# ---------------------------------------------------------------------------
# pandas index handling
# ---------------------------------------------------------------------------

def test_filtered_series_with_noncontiguous_index_renders():
    """
    A boolean-masked frame keeps the parent index, so ``df[df.g == "b"].x``
    might be indexed ``[1, 3]``.  The render path indexes coordinates
    positionally (``s.x[0]``), which on a pandas Series is a *label* lookup --
    this used to raise ``KeyError: 0`` from ``Axes.compute_domain``.
    """
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [4.0, 3.0, 2.0, 1.0],
        "g": ["a", "b", "a", "b"],
    })
    subset = frame[frame.g == "b"]
    assert list(subset.index) == [1, 3]

    svg = Figure(auto_display=False).scatter(subset.x, subset.y).render_svg()
    ET.fromstring(svg)


def test_series_index_is_dropped_at_construction():
    pd = pytest.importorskip("pandas")
    values = pd.Series([1.0, 2.0, 3.0], index=[10, 20, 30])
    series = LineSeries(values, values)
    assert not hasattr(series.x, "index")
    assert list(series.x) == [1.0, 2.0, 3.0]


def test_numeric_series_keeps_the_numpy_fast_path():
    """Large numeric input must not be turned into a Python list."""
    pd = pytest.importorskip("pandas")
    values = pd.Series(np.arange(500, dtype=float))
    assert isinstance(LineSeries(values, values).x, np.ndarray)


def test_datetime_series_still_gets_date_formatted_ticks():
    """
    to_numpy() on a datetime column yields datetime64 scalars, which the
    date-axis detection does not recognise; the conversion has to keep
    Timestamps for non-numeric dtypes.
    """
    pd = pytest.importorskip("pandas")
    stamps = pd.Series(pd.date_range("2024-01-01", periods=5, freq="D"))
    svg = Figure(auto_display=False).line(stamps, [1.0, 2.0, 3.0, 4.0, 5.0]).render_svg()
    assert re.search(r">\s*\d{1,2}\s+[A-Z][a-z]{2}\s*<", svg), "expected date tick labels"
