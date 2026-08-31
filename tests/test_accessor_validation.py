"""
DataFrame accessor column validation.

A misspelled column name used to be indistinguishable from an omitted one:
``_col()`` returned ``None`` for both, so ``df.glyphx.line(x="Month", ...)``
silently fell back to the row index and drew a 0, 1, 2 axis instead of the
month names. ``hue`` and ``groupby`` were simply ignored when unrecognised.
"""

import pytest

pd = pytest.importorskip("pandas")

import glyphx  # noqa: F401  -- registers the .glyphx accessor


@pytest.fixture
def df():
    return pd.DataFrame({
        "month":   ["Jan", "Feb", "Mar", "Jan"],
        "revenue": [10.0, 20.0, 15.0, 12.0],
        "region":  ["N", "S", "N", "S"],
    })


# ---------------------------------------------------------------------------
# Unknown names raise
# ---------------------------------------------------------------------------

def test_typo_in_x_raises_instead_of_falling_back_to_the_row_index(df):
    with pytest.raises(KeyError, match="not found"):
        df.glyphx.line(x="Month", y="revenue", auto_display=False)


def test_typo_in_y_raises(df):
    with pytest.raises(KeyError, match="not found"):
        df.glyphx.line(x="month", y="Revenue", auto_display=False)


def test_typo_in_yerr_raises(df):
    with pytest.raises(KeyError, match="not found"):
        df.glyphx.line(x="month", y="revenue", yerr="Err", auto_display=False)


def test_typo_in_hue_raises(df):
    """hue was silently ignored, so the chart drew ungrouped with no warning."""
    with pytest.raises(KeyError, match="hue"):
        df.glyphx.scatter(x="month", y="revenue", hue="Region",
                          auto_display=False)


def test_typo_in_groupby_raises(df):
    with pytest.raises(KeyError, match="not found"):
        df.glyphx.bar(x="month", y="revenue", groupby="Region",
                      auto_display=False)


def test_typo_in_box_groupby_raises(df):
    with pytest.raises(KeyError, match="groupby"):
        df.glyphx.box(col="revenue", groupby="Region", auto_display=False)


# ---------------------------------------------------------------------------
# Message quality
# ---------------------------------------------------------------------------

def test_error_suggests_the_closest_column(df):
    with pytest.raises(KeyError, match="Did you mean 'month'"):
        df.glyphx.line(x="Month", y="revenue", auto_display=False)


def test_error_lists_the_available_columns(df):
    with pytest.raises(KeyError) as exc:
        df.glyphx.line(x="nothing_like_it", y="revenue", auto_display=False)
    message = str(exc.value)
    assert "month" in message and "revenue" in message and "region" in message


def test_no_suggestion_when_nothing_is_close(df):
    with pytest.raises(KeyError) as exc:
        df.glyphx.line(x="zzzzzz", y="revenue", auto_display=False)
    assert "Did you mean" not in str(exc.value)


# ---------------------------------------------------------------------------
# Valid and omitted names still work
# ---------------------------------------------------------------------------

def test_omitted_x_still_falls_back_to_the_row_index(df):
    """Omitting x is legitimate; only an unknown name is an error."""
    fig = df.glyphx.line(y="revenue", auto_display=False)
    assert list(fig.axes.series[0].x) == [0, 1, 2, 3]


@pytest.mark.parametrize("call", [
    lambda d: d.glyphx.line(x="month", y="revenue", auto_display=False),
    lambda d: d.glyphx.scatter(x="month", y="revenue", hue="region",
                               auto_display=False),
    lambda d: d.glyphx.bar(x="month", y="revenue", auto_display=False),
    lambda d: d.glyphx.box(col="revenue", groupby="region", auto_display=False),
    lambda d: d.glyphx.hist(col="revenue", auto_display=False),
])
def test_valid_column_names_are_unaffected(df, call):
    assert call(df).render_svg().lstrip().startswith("<svg")


def test_correct_x_column_is_actually_plotted(df):
    fig = df.glyphx.line(x="month", y="revenue", auto_display=False)
    assert list(fig.axes.series[0].x) == ["Jan", "Feb", "Mar", "Jan"]
