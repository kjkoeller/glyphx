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


# ---------------------------------------------------------------------------
# Shared presentation options
# ---------------------------------------------------------------------------

PRESENTATION_OPTIONS = {
    "title": "T",
    "theme": "dark",
    "legend": "top-left",
    "width": 900,
    "height": 700,
    "xlabel": "XL",
    "ylabel": "YL",
}


def _chart_methods(frame):
    return {
        "line":    lambda **k: frame.glyphx.line(x="month", y="revenue", **k),
        "bar":     lambda **k: frame.glyphx.bar(x="month", y="revenue", **k),
        "scatter": lambda **k: frame.glyphx.scatter(x="month", y="revenue", **k),
        "hist":    lambda **k: frame.glyphx.hist(col="revenue", **k),
        "box":     lambda **k: frame.glyphx.box(col="revenue", **k),
        "pie":     lambda **k: frame.glyphx.pie(labels="month", values="revenue", **k),
        "donut":   lambda **k: frame.glyphx.donut(labels="month", values="revenue", **k),
        "heatmap": lambda **k: frame.glyphx.heatmap(**k),
    }


@pytest.mark.parametrize("option, value", sorted(PRESENTATION_OPTIONS.items()))
def test_every_chart_method_accepts_every_presentation_option(df, option, value):
    """
    The eight presentation parameters were copy-pasted per method, and the
    copies had diverged: `legend` was missing from hist, and `legend`,
    `xlabel` and `ylabel` from box, pie, donut and heatmap. `**kwargs`
    swallowed them, so `hist(legend="top-left")` was accepted and silently
    ignored while `pie(ylabel=...)` raised a TypeError blaming PieSeries.
    """
    for name, call in _chart_methods(df).items():
        call(**{option: value, "auto_display": False})


def test_legend_option_takes_effect_rather_than_being_swallowed(df):
    fig = df.glyphx.hist(col="revenue", legend="top-left", auto_display=False)
    assert fig.legend_pos == "top-left"


def test_axis_label_options_take_effect_on_box(df):
    fig = df.glyphx.box(col="revenue", xlabel="Month", auto_display=False)
    assert fig.axes.xlabel == "Month"


def test_explicit_labels_beat_the_column_derived_defaults(df):
    fig = df.glyphx.line(x="month", y="revenue", xlabel="Period",
                         ylabel="USD", auto_display=False)
    assert (fig.axes.xlabel, fig.axes.ylabel) == ("Period", "USD")


def test_column_names_are_still_used_when_no_label_is_given(df):
    fig = df.glyphx.line(x="month", y="revenue", auto_display=False)
    assert (fig.axes.xlabel, fig.axes.ylabel) == ("month", "revenue")


@pytest.mark.parametrize("method", ["pie", "donut"])
def test_pie_and_donut_keep_their_square_canvas(df, method):
    """Sharing the options block must not flatten their 480x480 default."""
    fig = _chart_methods(df)[method](auto_display=False)
    assert (fig.width, fig.height) == (480, 480)


@pytest.mark.parametrize("method", ["pie", "donut"])
def test_explicit_size_overrides_the_per_chart_default(df, method):
    fig = _chart_methods(df)[method](width=900, height=300, auto_display=False)
    assert (fig.width, fig.height) == (900, 300)


def test_options_are_declared_in_exactly_one_place():
    """Guard against the block being copy-pasted back into a signature."""
    import ast
    from pathlib import Path

    from glyphx.accessor import _FIGURE_OPTION_KEYS

    source = Path(__file__).resolve().parent.parent / "glyphx" / "accessor.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue
        names = {a.arg for a in node.args.args + node.args.kwonlyargs}
        leaked = names & _FIGURE_OPTION_KEYS
        if leaked:
            offenders.append(f"{node.name} declares {sorted(leaked)}")

    assert offenders == [], (
        "presentation options belong in FigureOptions, not in a signature: "
        f"{offenders}"
    )
