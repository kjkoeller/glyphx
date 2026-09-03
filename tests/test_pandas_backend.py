"""
GlyphX registered as a real pandas plotting backend.

``pd.options.plotting.backend = "glyphx"`` used to be accepted silently and
then crash on the first real call. Nothing was registered under the
``pandas_plotting_backends`` entry point, so pandas fell back to importing
the ``glyphx`` package directly and found its top-level ``glyphx.plot()``
convenience function by accident -- a different function with a colliding
signature. ``df.plot(x="x", y="y")`` called ``glyphx.plot(df, x=x, y=y,
kind=kind)``, and the positional ``df`` collided with ``glyphx.plot``'s own
``x`` parameter: ``TypeError: plot() got multiple values for argument 'x'``.

These tests need the package genuinely installed with its entry points
readable by ``importlib.metadata`` -- editing source alone does not update
installed entry-point metadata, so a plain ``pip install -e .`` re-run is
what makes the registration take effect.
"""

import pytest

pd = pytest.importorskip("pandas")

from importlib.metadata import entry_points

from glyphx import Figure
from glyphx.figure import SubplotGrid

_REGISTERED = any(
    ep.name == "glyphx"
    for ep in entry_points(group="pandas_plotting_backends")
)

pytestmark = pytest.mark.skipif(
    not _REGISTERED,
    reason="glyphx is not installed with its entry points readable "
           "(run `pip install -e .` from the repo root)",
)


@pytest.fixture(autouse=True)
def _use_glyphx_backend():
    original = pd.get_option("plotting.backend")
    pd.options.plotting.backend = "glyphx"
    yield
    pd.options.plotting.backend = original


@pytest.fixture
def df():
    return pd.DataFrame({
        "month": ["Jan", "Feb", "Mar", "Apr"],
        "revenue": [10.0, 25.0, 18.0, 40.0],
        "costs": [8.0, 12.0, 11.0, 19.0],
    })


# ---------------------------------------------------------------------------
# Registration itself
# ---------------------------------------------------------------------------

def test_entry_point_resolves_to_the_compatibility_module():
    import pandas.plotting._core as core
    module = core._get_plot_backend()
    assert module.__name__ == "glyphx.pandas_backend"


def test_the_originally_crashing_call_now_works(df):
    """The exact call that used to raise
    TypeError: plot() got multiple values for argument 'x'."""
    fig = df.plot(x="month", y="revenue")
    assert isinstance(fig, Figure)
    assert fig.render_svg().lstrip().startswith("<svg")


# ---------------------------------------------------------------------------
# DataFrame: column resolution
# ---------------------------------------------------------------------------

def test_no_arguments_plots_every_numeric_column_against_the_index(df):
    fig = df.plot()
    assert {s.label for s in fig.axes.series} == {"revenue", "costs"}
    assert fig.axes.series[0].x == [0, 1, 2, 3]


def test_x_given_y_omitted_uses_every_other_numeric_column(df):
    fig = df.plot(x="month")
    assert {s.label for s in fig.axes.series} == {"revenue", "costs"}
    assert fig.axes.series[0].x == ["Jan", "Feb", "Mar", "Apr"]


def test_y_as_a_list_draws_one_series_per_column(df):
    fig = df.plot(x="month", y=["revenue", "costs"])
    assert len(fig.axes.series) == 2
    assert fig.axes.series[0].x == ["Jan", "Feb", "Mar", "Apr"]


def test_integer_column_position_is_resolved(df):
    fig = df.plot(x=0, y=1)
    assert fig.axes.series[0].label == "revenue"


# ---------------------------------------------------------------------------
# kind=
# ---------------------------------------------------------------------------

def test_kind_bar_single_column(df):
    fig = df.plot.bar(x="month", y="revenue")
    assert fig.render_svg().lstrip().startswith("<svg")


def test_kind_bar_multi_column_groups_by_category(df):
    fig = df.plot.bar(x="month", y=["revenue", "costs"])
    assert type(fig.axes.series[0]).__name__ == "GroupedBarSeries"


def test_kind_area_is_stacked_by_default(df):
    """matplotlib's DataFrame.plot.area() stacks by default; a caller
    relying on that must see the same shape here."""
    fig = df.plot.area(x="month")
    bottom, top = fig.axes.series[0], fig.axes.series[1]
    assert bottom.y2 == top.y1


def test_kind_area_stacked_false_does_not_stack(df):
    fig = df.plot.area(x="month", stacked=False)
    assert all(s.y1 == [0.0, 0.0, 0.0, 0.0] for s in fig.axes.series)


def test_kind_scatter_requires_x_and_y(df):
    with pytest.raises(ValueError, match="requires a single"):
        df.plot(kind="scatter")


def test_kind_scatter_plots_the_given_pair(df):
    fig = df.plot.scatter(x="revenue", y="costs")
    assert fig.axes.series[0].x == df["revenue"].tolist()


def test_kind_hist_one_series_per_column():
    frame = pd.DataFrame({"a": [1.0, 2.0, 2.0, 3.0], "b": [5.0, 5.0, 6.0, 7.0]})
    fig = frame.plot.hist()
    assert {s.label for s in fig.axes.series} == {"a", "b"}


def test_kind_kde_one_series_per_column():
    frame = pd.DataFrame({"a": [1.0, 2.0, 2.0, 3.0], "b": [5.0, 5.0, 6.0, 7.0]})
    fig = frame.plot.kde()
    assert len(fig.axes.series) == 2


def test_kind_box_one_box_per_column():
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0, 9.0], "b": [2.0, 3.0, 4.0, 5.0]})
    fig = frame.plot.box()
    assert fig.axes.series[0].categories == ["a", "b"]


def test_kind_pie_needs_exactly_one_column(df):
    """
    Reached via kind= rather than the .pie() accessor: pandas validates
    that path itself before any backend sees the call, raising its own
    "pie requires either y column or 'subplots=True'".
    """
    with pytest.raises(ValueError, match="exactly one column"):
        df.set_index("month").plot(kind="pie")


def test_kind_pie_values_and_labels_match_the_data(df):
    fig = df.set_index("month").plot.pie(y="revenue")
    pie = fig.axes.series[0]
    assert pie.values == [10.0, 25.0, 18.0, 40.0]
    assert pie.labels == ["Jan", "Feb", "Mar", "Apr"]


def test_density_is_an_alias_for_kde():
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})
    fig = frame.plot(kind="density")
    assert type(fig.axes.series[0]).__name__ == "KDESeries"


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------

def test_series_plot_uses_its_index_and_name():
    s = pd.Series([3.0, 1.0, 4.0, 1.0], index=["w", "x", "y", "z"], name="samples")
    fig = s.plot()
    assert fig.axes.series[0].x == ["w", "x", "y", "z"]
    assert fig.axes.series[0].label == "samples"


def test_series_scatter_is_rejected():
    with pytest.raises(ValueError, match="DataFrame"):
        pd.Series([1.0, 2.0]).plot(kind="scatter")


# ---------------------------------------------------------------------------
# subplots
# ---------------------------------------------------------------------------

def test_subplots_true_makes_one_row_per_series(df):
    fig = df.plot(x="month", y=["revenue", "costs"], subplots=True)
    assert (fig.rows, fig.cols) == (2, 1)


def test_subplots_with_sharex_shares_the_x_domain(df):
    fig = df.plot(x="month", y=["revenue", "costs"], subplots=True, sharex=True)
    assert fig.shared_x is True


def test_subplots_without_sharex_defaults_to_independent_axes(df):
    fig = df.plot(x="month", y=["revenue", "costs"], subplots=True)
    assert fig.shared_x is False


# ---------------------------------------------------------------------------
# Presentation kwargs
# ---------------------------------------------------------------------------

def test_figsize_sets_the_canvas_size(df):
    fig = df.plot(x="month", y="revenue", figsize=(8, 4))
    assert (fig.width, fig.height) == (800, 400)


def test_title_and_axis_labels(df):
    fig = df.plot(x="month", y="revenue", title="T", xlabel="M", ylabel="R")
    assert fig.title == "T"
    assert fig.axes.xlabel == "M"
    assert fig.axes.ylabel == "R"


def test_legend_false_hides_the_legend(df):
    """set_legend(False) stores None for hidden, so assert on the rendered
    output rather than the sentinel."""
    fig = df.plot(x="month", y=["revenue", "costs"], legend=False)
    assert fig.legend_pos is None
    assert "legend-label" not in fig.render_svg()


def test_legend_shows_for_multiple_columns_by_default(df):
    fig = df.plot(x="month", y=["revenue", "costs"])
    assert "legend-label" in fig.render_svg()


def test_legend_true_shows_it_for_a_single_column(df):
    fig = df.plot(x="month", y="revenue", legend=True)
    assert "legend-label" in fig.render_svg()


def test_grid_false_hides_the_grid(df):
    fig = df.plot(x="month", y="revenue", grid=False)
    assert fig.axes.show_grid is False


def test_logy_sets_a_log_y_axis(df):
    fig = df.plot(x="month", y="revenue", logy=True)
    assert fig.axes.yscale == "log"


def test_colormap_uses_glyphxs_own_palette(df):
    from glyphx.colormaps import colormap_colors
    fig = df.plot(x="month", y=["revenue", "costs"], colormap="viridis")
    assert [s.color for s in fig.axes.series] == colormap_colors("viridis", 2)


def test_unrecognised_colormap_name_raises(df):
    with pytest.raises(NotImplementedError, match="colormap"):
        df.plot(x="month", y="revenue", colormap="not_a_real_colormap")


# ---------------------------------------------------------------------------
# Explicit refusals: unsupported kinds and kwargs must fail loudly
# ---------------------------------------------------------------------------

def test_hexbin_is_rejected_with_a_clear_message(df):
    with pytest.raises(NotImplementedError, match="hexbin"):
        df.plot(x="revenue", y="costs", kind="hexbin")


def test_barh_is_rejected_with_a_clear_message(df):
    with pytest.raises(NotImplementedError, match="barh"):
        df.plot.barh(x="month", y="revenue")


@pytest.mark.parametrize("kwarg,value", [
    ("ax", object()), ("secondary_y", True), ("table", True),
    ("xlim", (0, 1)), ("style", "ro-"),
])
def test_unsupported_kwargs_are_rejected_not_ignored(df, kwarg, value):
    """
    Silently ignoring one of these would produce a chart that looks
    finished while quietly not doing part of what was asked.
    """
    with pytest.raises(NotImplementedError, match=kwarg):
        df.plot(x="month", y="revenue", **{kwarg: value})


def test_use_index_false_is_rejected(df):
    with pytest.raises(NotImplementedError, match="use_index"):
        df.plot(y="revenue", use_index=False)


# ---------------------------------------------------------------------------
# Real DOM output, not just non-crashing
# ---------------------------------------------------------------------------

def test_the_result_is_a_usable_figure(df, tmp_path):
    fig = df.plot(x="month", y="revenue")
    path = tmp_path / "out.html"
    fig.share(str(path))
    assert path.read_text(encoding="utf-8").strip()


def test_subplotgrid_still_works_independently_of_the_backend():
    """The backend must not interfere with GlyphX's own APIs."""
    a = Figure(auto_display=False).line([1, 2], [1.0, 2.0])
    b = Figure(auto_display=False).bar([1, 2], [2.0, 1.0])
    grid = SubplotGrid(1, 2).add(a, 0, 0).add(b, 0, 1)
    assert grid.render().lstrip().startswith("<!DOCTYPE") or "<svg" in grid.render()
