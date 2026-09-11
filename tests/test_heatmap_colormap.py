"""
Heatmap colour mapping: named colormaps, and pinning the range.

``cmap=`` means a colormap *name* on every other series that takes one, but
HeatmapSeries accepted only a list of hex stops, so a name was sliced
character by character and died in ``int(..., 16)``. None of the nine named
colormaps could be used on a heatmap at all.

Separately, every heatmap normalised over its own min and max. That makes
two panels incomparable, and puts a diverging colormap's neutral midpoint
wherever the data happens to straddle rather than at the value it marks.
"""

import re

import pytest

from glyphx import Figure, HeatmapSeries
from glyphx.colormaps import get_colormap, list_colormaps


def _cells(series, count):
    """Fill colours of the heatmap cells, excluding background and colorbar."""
    fig = Figure(auto_display=False)
    fig.add(series)
    return re.findall(
        r'<rect[^>]*fill="(#[0-9a-fA-F]{6})" stroke="#fff" stroke-width="0.5"',
        fig.render_svg())[:count]


# ---------------------------------------------------------------------------
# Named colormaps
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(list_colormaps()))
def test_every_named_colormap_works(name):
    """The bug: ValueError: invalid literal for int() with base 16: ''."""
    fig = Figure(auto_display=False)
    fig.add(HeatmapSeries([[1, 2], [3, 4]], cmap=name))
    assert fig.render_svg().lstrip().startswith("<svg")


def test_named_colormap_uses_that_ramp():
    stops = get_colormap("viridis")
    cells = _cells(HeatmapSeries([[0.0, 1.0]], cmap="viridis"), 2)
    assert cells[0] == stops[0]
    assert cells[1] == stops[-1]


def test_unknown_colormap_name_lists_the_alternatives():
    with pytest.raises(ValueError, match="Unknown colormap"):
        HeatmapSeries([[1, 2]], cmap="not_a_real_colormap")


def test_a_list_of_hex_stops_is_still_accepted():
    """The previous behaviour must keep working."""
    cells = _cells(HeatmapSeries([[0.0, 1.0]], cmap=["#000000", "#ffffff"]), 2)
    assert cells == ["#000000", "#ffffff"]


def test_default_ramp_is_unchanged_when_no_cmap_is_given():
    cells = _cells(HeatmapSeries([[0.0, 1.0]]), 2)
    assert cells[0] == "#fff7fb"


# ---------------------------------------------------------------------------
# center=
# ---------------------------------------------------------------------------

def test_center_puts_that_value_at_the_neutral_midpoint():
    stops = get_colormap("coolwarm")
    neutral = stops[len(stops) // 2]
    cells = _cells(HeatmapSeries([[-1.0, 0.0, 1.0]], cmap="coolwarm", center=0), 3)
    assert cells[1].lower() == neutral.lower()


def test_center_holds_on_asymmetric_data():
    """
    The case that matters: a correlation matrix spanning -0.2 to 1.0. Without
    centring, zero lands 17% up the ramp and mildly positive values render
    with the colour that reads as negative.
    """
    stops = get_colormap("coolwarm")
    neutral = stops[len(stops) // 2]
    cells = _cells(HeatmapSeries([[-0.2, 0.0, 1.0]], cmap="coolwarm", center=0), 3)
    assert cells[1].lower() == neutral.lower()


def test_without_center_zero_is_not_neutral_on_asymmetric_data():
    """Documents the default, so the difference centring makes is pinned."""
    stops = get_colormap("coolwarm")
    neutral = stops[len(stops) // 2]
    cells = _cells(HeatmapSeries([[-0.2, 0.0, 1.0]], cmap="coolwarm"), 3)
    assert cells[1].lower() != neutral.lower()


def test_center_keeps_the_extremes_symmetric():
    stops = get_colormap("coolwarm")
    cells = _cells(HeatmapSeries([[-1.0, 1.0]], cmap="coolwarm", center=0), 2)
    assert cells[0] == stops[0]
    assert cells[1] == stops[-1]


# ---------------------------------------------------------------------------
# vmin / vmax
# ---------------------------------------------------------------------------

def test_shared_range_makes_two_panels_comparable():
    """
    Without this each panel normalises over its own data, so the same value
    renders as a different colour in each and the two cannot be read
    side by side.
    """
    a = _cells(HeatmapSeries([[0.0, 5.0]], cmap="viridis", vmin=0, vmax=10), 2)
    b = _cells(HeatmapSeries([[0.0, 5.0, 10.0]], cmap="viridis", vmin=0, vmax=10), 3)
    assert a[1] == b[1]


def test_values_outside_a_pinned_range_clamp():
    """Otherwise the ramp index runs past the end of the stop list."""
    stops = get_colormap("viridis")
    cells = _cells(HeatmapSeries([[-99.0, 99.0]], cmap="viridis",
                                 vmin=0, vmax=1), 2)
    assert cells == [stops[0], stops[-1]]


def test_vmin_alone_leaves_vmax_from_the_data():
    fig = Figure(auto_display=False)
    fig.add(HeatmapSeries([[2.0, 4.0]], cmap="viridis", vmin=0))
    assert fig.render_svg().lstrip().startswith("<svg")


def test_a_flat_matrix_does_not_divide_by_zero():
    fig = Figure(auto_display=False)
    fig.add(HeatmapSeries([[3.0, 3.0], [3.0, 3.0]], cmap="viridis"))
    assert fig.render_svg().lstrip().startswith("<svg")
