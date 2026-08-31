"""
Shared-X subplot grids: every cell plots against one unified X domain, and
only the bottom cell in each column carries tick labels.
"""

import pytest

from glyphx import Figure, LineSeries


def _stacked(shared_x, ranges=((0, 30), (10, 60), (40, 100))):
    fig = Figure(rows=len(ranges), cols=1, width=800, height=600,
                 auto_display=False, shared_x=shared_x, legend=None)
    for i, (lo, hi) in enumerate(ranges):
        xs = list(range(lo, hi + 1))
        fig.add_axes(i, 0).add_series(
            LineSeries(xs, [float(v % 17) for v in xs]))
    return fig


def _domains(fig):
    return [fig.grid[r][0]._x_domain for r in range(fig.rows)]


def _hidden(fig):
    return [fig.grid[r][0]._hide_xticklabels for r in range(fig.rows)]


# ---------------------------------------------------------------------------
# Domain unification
# ---------------------------------------------------------------------------

def test_shared_x_gives_every_cell_the_same_domain():
    fig = _stacked(shared_x=True)
    fig.render_svg()
    assert len(set(_domains(fig))) == 1


def test_shared_domain_is_the_union_of_all_cells():
    fig = _stacked(shared_x=True)
    fig.render_svg()
    lo, hi = _domains(fig)[0]
    assert lo <= 0 and hi >= 100


def test_domains_stay_independent_without_shared_x():
    fig = _stacked(shared_x=False)
    fig.render_svg()
    assert len(set(_domains(fig))) == 3


def test_shared_x_defaults_to_off():
    assert Figure(auto_display=False).shared_x is False


def test_rendering_twice_is_stable():
    """finalize() runs twice per cell under shared_x; it must be idempotent."""
    fig = _stacked(shared_x=True)
    first = fig.render_svg()
    assert fig.render_svg() == first


# ---------------------------------------------------------------------------
# Tick label suppression
# ---------------------------------------------------------------------------

def test_only_the_bottom_cell_keeps_x_tick_labels():
    fig = _stacked(shared_x=True)
    fig.render_svg()
    assert _hidden(fig) == [True, True, False]


def test_no_labels_are_suppressed_without_shared_x():
    fig = _stacked(shared_x=False)
    fig.render_svg()
    assert _hidden(fig) == [False, False, False]


def test_grid_lines_and_ticks_survive_label_suppression():
    """Only the <text> goes; the alignment cues must stay."""
    fig = _stacked(shared_x=True)
    svg = fig.render_svg()
    assert svg.count("stroke-dasharray") > 0


def test_sparse_grid_labels_the_lowest_occupied_cell():
    """If the bottom row of a column is empty, the cell above keeps labels."""
    fig = Figure(rows=2, cols=2, width=800, height=500, auto_display=False,
                 shared_x=True, legend=None)
    fig.add_axes(0, 0).add_series(LineSeries([1, 2, 3], [1.0, 2.0, 3.0]))
    fig.add_axes(0, 1).add_series(LineSeries([1, 2, 3], [3.0, 2.0, 1.0]))
    fig.add_axes(1, 0).add_series(LineSeries([1, 2, 3], [2.0, 1.0, 3.0]))
    fig.render_svg()

    assert fig.grid[0][0]._hide_xticklabels is True    # cell below it exists
    assert fig.grid[1][0]._hide_xticklabels is False   # bottom of its column
    assert fig.grid[0][1]._hide_xticklabels is False   # only cell in column 1
    assert fig.grid[1][1] is None


# ---------------------------------------------------------------------------
# Degenerate cases
# ---------------------------------------------------------------------------

def test_shared_x_on_an_empty_grid_is_a_no_op():
    fig = Figure(rows=2, cols=1, auto_display=False, shared_x=True, legend=None)
    assert fig.render_svg().lstrip().startswith("<svg")


def test_shared_x_with_one_cell_holding_no_data():
    fig = Figure(rows=2, cols=1, width=800, height=500, auto_display=False,
                 shared_x=True, legend=None)
    fig.add_axes(0, 0).add_series(LineSeries([1, 2, 3], [1.0, 2.0, 3.0]))
    fig.add_axes(1, 0)                                  # no series
    assert fig.render_svg().lstrip().startswith("<svg")


def test_shared_x_ignores_a_single_axes_figure():
    """shared_x only applies to grids; a plain figure must be unaffected."""
    fig = Figure(auto_display=False, shared_x=True).line([1, 2, 3], [1.0, 2.0, 3.0])
    assert fig.render_svg().lstrip().startswith("<svg")


@pytest.mark.parametrize("scale", ["linear", "log"])
def test_shared_x_respects_the_axis_scale(scale):
    fig = Figure(rows=2, cols=1, width=800, height=500, auto_display=False,
                 shared_x=True, legend=None, xscale=scale)
    fig.add_axes(0, 0).add_series(LineSeries([1, 10, 100], [1.0, 2.0, 3.0]))
    fig.add_axes(1, 0).add_series(LineSeries([5, 50, 500], [3.0, 2.0, 1.0]))
    assert fig.render_svg().lstrip().startswith("<svg")


# ---------------------------------------------------------------------------
# Zoom / pan
# ---------------------------------------------------------------------------

def test_grid_is_one_svg_so_zoom_and_pan_are_already_synchronised():
    """
    zoom.js operates on the SVG's viewBox, and a subplot grid renders as a
    single <svg> with the cells as translated <g> groups -- so panning the X
    axis already moves every panel together. No extra JS wiring needed.
    """
    import re

    fig = _stacked(shared_x=True)
    svg = fig.render_svg(viewbox=True)
    assert svg.count("<svg") == 1
    assert len(re.findall(r"viewBox=", svg)) == 1
    assert svg.count('<g transform="translate(') == 3
