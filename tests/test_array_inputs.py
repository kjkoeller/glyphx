"""
Regression tests for array-like input handling.

NumPy arrays and pandas Series raise ``ValueError`` from ``__bool__`` when
they contain more than one element, so any bare truthiness check on a
series' ``x``/``y`` attribute crashes for exactly the input types this
library declares as hard dependencies.  These tests pin the fix: every
public entry point must accept lists, ndarrays, and Series alike.
"""

import math
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import pytest

import glyphx
from glyphx import Figure, LineSeries
from glyphx.utils import as_seq, has_data

WRAPPERS = [list, np.array, pd.Series]
WRAPPER_IDS = ["list", "ndarray", "series"]


# ---------------------------------------------------------------------------
# has_data / as_seq helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("wrap", WRAPPERS, ids=WRAPPER_IDS)
def test_has_data_true_for_non_empty(wrap):
    assert has_data(wrap([1, 2, 3])) is True


@pytest.mark.parametrize("wrap", WRAPPERS, ids=WRAPPER_IDS)
def test_has_data_false_for_empty(wrap):
    assert has_data(wrap([])) is False


def test_has_data_handles_none_and_scalars():
    assert has_data(None) is False
    assert has_data(0) is False
    assert has_data(5) is True


@pytest.mark.parametrize("wrap", WRAPPERS, ids=WRAPPER_IDS)
def test_as_seq_returns_plain_list(wrap):
    out = as_seq(wrap([1, 2, 3]))
    assert isinstance(out, list)
    assert out == [1, 2, 3]


def test_as_seq_empty_inputs():
    assert as_seq(None) == []
    assert as_seq([]) == []
    assert as_seq(np.array([])) == []


# ---------------------------------------------------------------------------
# Chart rendering with every array type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["line", "bar", "scatter"])
@pytest.mark.parametrize("wrap", WRAPPERS, ids=WRAPPER_IDS)
def test_plot_accepts_array_like(kind, wrap):
    x = wrap([1, 2, 3])
    y = wrap([4.0, 5.0, 6.0])
    svg = glyphx.plot(x, y, kind=kind, auto_display=False).render_svg()
    assert svg.lstrip().startswith("<svg")
    ET.fromstring(svg)          # output must be well-formed XML


@pytest.mark.parametrize("wrap", WRAPPERS, ids=WRAPPER_IDS)
def test_figure_methods_accept_array_like(wrap):
    fig = Figure(auto_display=False)
    fig.line(wrap([1, 2, 3]), wrap([1.0, 4.0, 9.0]))
    fig.scatter(wrap([1, 2, 3]), wrap([2.0, 3.0, 4.0]))
    ET.fromstring(fig.render_svg())


def test_hist_and_pie_accept_ndarray():
    ET.fromstring(Figure(auto_display=False).hist(np.arange(50.0)).render_svg())
    ET.fromstring(
        Figure(auto_display=False)
        .pie(np.array([1.0, 2.0, 3.0]), labels=["a", "b", "c"])
        .render_svg()
    )


@pytest.mark.parametrize("wrap", WRAPPERS, ids=WRAPPER_IDS)
def test_series_repr_does_not_raise(wrap):
    text = repr(LineSeries(wrap([1, 2, 3]), wrap([4.0, 5.0, 6.0])))
    assert "LineSeries" in text
    assert "3 pts" in text


def test_dataframe_columns_end_to_end():
    df = pd.DataFrame({"month": [1, 2, 3], "revenue": [10.0, 20.0, 15.0]})
    svg = glyphx.plot(df["month"], df["revenue"], kind="line",
                      auto_display=False).render_svg()
    ET.fromstring(svg)


# ---------------------------------------------------------------------------
# Package surface
# ---------------------------------------------------------------------------

def test_all_names_are_importable():
    missing = [name for name in glyphx.__all__ if not hasattr(glyphx, name)]
    assert missing == [], f"declared in __all__ but not importable: {missing}"


def test_version_is_a_string():
    assert isinstance(glyphx.__version__, str)
    assert glyphx.__version__


# ---------------------------------------------------------------------------
# Missing values must render as gaps, never as invalid coordinates
# ---------------------------------------------------------------------------

BAD_VALUES = [
    pytest.param(float("nan"), id="nan"),
    pytest.param(np.nan, id="np-nan"),
    pytest.param(None, id="none"),
    pytest.param(float("inf"), id="inf"),
    pytest.param(float("-inf"), id="-inf"),
]


@pytest.mark.parametrize("bad", BAD_VALUES)
def test_missing_y_does_not_emit_invalid_coordinates(bad):
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, bad, 3.0]).render_svg()
    ET.fromstring(svg)
    assert "nan" not in svg.lower()
    assert "inf" not in svg.lower()


@pytest.mark.parametrize("bad", BAD_VALUES)
def test_missing_x_does_not_emit_invalid_coordinates(bad):
    svg = Figure(auto_display=False).line([1.0, bad, 3.0], [1.0, 2.0, 3.0]).render_svg()
    ET.fromstring(svg)
    assert "nan" not in svg.lower()


def test_missing_value_splits_the_line_into_two_segments():
    svg = Figure(auto_display=False).line(
        [1, 2, 3, 4, 5], [1.0, 2.0, float("nan"), 4.0, 5.0]
    ).render_svg()
    root = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    polylines = [
        el for el in root.iter(f"{ns}polyline")
        if (el.get("class") or "").startswith("series-")
    ]
    assert len(polylines) == 2, "gap should split the line into two polylines"
    assert all(el.get("points") for el in polylines)


def test_missing_value_is_excluded_from_the_axis_domain():
    """An infinity in the data must not stretch the Y axis."""
    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, float("inf"), 3.0])
    fig.render_svg()
    y_min, y_max = fig.axes._y_domain
    assert math.isfinite(y_min) and math.isfinite(y_max)
    assert y_max < 100
