"""
Edge cases in the modules the suite barely reached.

Everything here was found by exercising ``dataframes``, ``regplot`` and
``choropleth`` with inputs the existing tests never produced.
"""

import numpy as np
import pytest

from glyphx import Figure
from glyphx.dataframes import column_names, get_column

# ---------------------------------------------------------------------------
# dataframes: column name handling
# ---------------------------------------------------------------------------

def test_integer_column_names_are_readable():
    """
    ``column_names()`` stringifies for display, so a frame from
    ``pd.read_csv(header=None)`` reported "0" while indexing still needed the
    integer ``0`` -- ``get_column(df, "0")`` raised KeyError on a column it
    had just listed as available.
    """
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame([[1, 2], [3, 4]])
    assert column_names(df) == ["0", "1"]
    assert get_column(df, "0") == [1, 3]
    assert get_column(df, "1") == [2, 4]


@pytest.mark.parametrize("label, key", [(1.5, "1.5"), (("x", "y"), "('x', 'y')")])
def test_non_string_column_labels_resolve(label, key):
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({label: [7, 8]})
    assert get_column(df, key) == [7, 8]


def test_duplicate_column_names_raise_instead_of_returning_labels():
    """
    ``df["a"]`` on a frame with two "a" columns returns a DataFrame, and
    iterating a DataFrame yields its column *labels* -- so this silently
    plotted ["a", "a"] as though it were the data.
    """
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame([[1, 2], [3, 4]], columns=["a", "a"])
    with pytest.raises(KeyError, match="ambiguous"):
        get_column(df, "a")


def test_missing_column_error_lists_what_is_available():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"alpha": [1], "beta": [2]})
    with pytest.raises(KeyError, match="alpha"):
        get_column(df, "gamma")


# ---------------------------------------------------------------------------
# regplot: degenerate fits
# ---------------------------------------------------------------------------

def _frame(xs, ys):
    pd = pytest.importorskip("pandas")
    return pd.DataFrame({"x": xs, "y": ys})


def test_regplot_rejects_a_single_point():
    """One point produced a fit line from nothing and printed r=nan."""
    from glyphx import regplot

    with pytest.raises(ValueError, match="at least 2"):
        regplot(_frame([1.0], [1.0]), x="x", y="y", auto_display=False)


def test_regplot_rejects_constant_x():
    from glyphx import regplot

    with pytest.raises(ValueError, match="slope is undefined"):
        regplot(_frame([2.0, 2.0, 2.0], [1.0, 2.0, 3.0]), x="x", y="y",
                auto_display=False)


def test_regplot_omits_r_when_y_is_constant_but_still_fits():
    """A flat line is a valid fit; only the correlation is undefined."""
    from glyphx import regplot

    svg = regplot(_frame([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]),
                  x="x", y="y", auto_display=False).render_svg()
    assert "nan" not in svg.lower()
    assert "(r=" not in svg


def test_regplot_reports_r_for_ordinary_data():
    from glyphx import regplot

    svg = regplot(_frame([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.5]),
                  x="x", y="y", auto_display=False).render_svg()
    assert "(r=0.99" in svg


def test_regplot_emits_no_numpy_warnings_on_degenerate_input():
    """
    A constant y made np.corrcoef divide by zero, so callers saw a stack of
    RuntimeWarnings from inside NumPy for an input GlyphX now handles.
    """
    import warnings

    from glyphx import regplot

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        regplot(_frame([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]),
                x="x", y="y", auto_display=False).render_svg()

    runtime = [str(w.message) for w in caught
               if issubclass(w.category, RuntimeWarning)]
    assert not runtime, f"NumPy warnings leaked to the caller: {runtime}"


# ---------------------------------------------------------------------------
# choropleth: real-world GeoJSON shapes
# ---------------------------------------------------------------------------

def _feature(geometry, name="X"):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": name}, "geometry": geometry}]}


_SQUARE = {"type": "Polygon",
           "coordinates": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]]}


@pytest.mark.parametrize("label, geojson", [
    ("null geometry",   _feature(None)),
    ("point",           _feature({"type": "Point", "coordinates": [5, 5]})),
    ("linestring",      _feature({"type": "LineString", "coordinates": [[0, 0], [5, 5]]})),
    ("3d coordinates",  _feature({"type": "Polygon",
                                  "coordinates": [[[0, 0, 120], [0, 10, 90],
                                                   [10, 10, 50], [0, 0, 120]]]})),
    ("polar latitude",  _feature({"type": "Polygon",
                                  "coordinates": [[[0, -90], [0, -80],
                                                   [10, -80], [10, -90], [0, -90]]]})),
    ("no features",     {"type": "FeatureCollection", "features": []}),
])
def test_choropleth_survives_awkward_geojson(label, geojson):
    from glyphx import ChoroplethSeries

    fig = Figure(auto_display=False)
    fig.add(ChoroplethSeries(geojson, {"X": 1.0}))
    assert fig.render_svg().lstrip().startswith("<svg")


def test_choropleth_maps_values_across_the_full_colormap():
    from glyphx import ChoroplethSeries
    from glyphx.colormaps import colormap_colors

    features = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": n},
         "geometry": {"type": "Polygon",
                      "coordinates": [[[i * 10, 0], [i * 10, 5],
                                       [i * 10 + 5, 5], [i * 10, 0]]]}}
        for i, n in enumerate(["low", "mid", "high"])]}

    fig = Figure(auto_display=False)
    fig.add(ChoroplethSeries(features,
                             {"low": 0.0, "mid": 50.0, "high": 100.0},
                             cmap="viridis"))
    svg = fig.render_svg()
    ramp = colormap_colors("viridis", 5)
    assert ramp[0] in svg and ramp[-1] in svg


def test_choropleth_escapes_feature_names():
    from glyphx import ChoroplethSeries

    fig = Figure(auto_display=False)
    fig.add(ChoroplethSeries(_feature(_SQUARE, name="Ben & Co"), {"Ben & Co": 1.0}))
    svg = fig.render_svg()
    assert "Ben &amp; Co" in svg


# ---------------------------------------------------------------------------
# sparkline: degenerate inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("values", [[], [5], [3, 3, 3, 3], [1, float("nan"), 3]])
def test_sparkline_handles_degenerate_series(values):
    from glyphx import sparkline_svg

    assert sparkline_svg(values).lstrip().startswith("<svg")


def test_dataframe_backends_agree():
    """pandas, polars and pyarrow must produce the same column values."""
    pd = pytest.importorskip("pandas")
    data = {"a": [1, 2, 3], "s": ["x", "y", "z"]}
    expected = {"a": [1, 2, 3], "s": ["x", "y", "z"]}

    frames = [pd.DataFrame(data)]
    pl = pytest.importorskip("polars")
    frames.append(pl.DataFrame(data))
    pa = pytest.importorskip("pyarrow")
    frames.append(pa.table(data))

    for frame in frames:
        assert column_names(frame) == ["a", "s"]
        for col, want in expected.items():
            assert list(get_column(frame, col)) == want, type(frame).__name__


def test_numpy_arrays_are_not_mistaken_for_dataframes():
    from glyphx.dataframes import is_dataframe

    assert not is_dataframe(np.zeros((2, 2)))
    assert not is_dataframe([[1, 2], [3, 4]])
