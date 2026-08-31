"""
Theme registry and palette assignment.

Two behaviours are covered: registering a named custom theme so it works
anywhere a theme name is accepted, and the theme's ``colors`` list actually
reaching the series it colors.
"""

import pytest

import glyphx
from glyphx import (
    Figure,
    get_theme,
    list_themes,
    register_theme,
    unregister_theme,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Custom themes must not leak between tests."""
    before = set(glyphx.themes)
    yield
    for name in set(glyphx.themes) - before:
        del glyphx.themes[name]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registered_theme_works_by_name_everywhere():
    register_theme("acme", base="dark",
                   colors=["#e6194b", "#3cb44b"], font="Inter, sans-serif")
    svg = Figure(theme="acme", auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    assert "Inter, sans-serif" in svg
    assert "#e6194b" in svg


def test_register_inherits_unspecified_keys_from_base():
    register_theme("half", base="dark", colors=["#000000"])
    theme = get_theme("half")
    assert theme["background"] == glyphx.themes["dark"]["background"]
    assert theme["colors"] == ["#000000"]


def test_registered_theme_appears_in_list_themes():
    assert "acme" not in list_themes()
    register_theme("acme")
    assert "acme" in list_themes()
    unregister_theme("acme")
    assert "acme" not in list_themes()


def test_builtins_are_protected():
    with pytest.raises(ValueError, match="built-in"):
        register_theme("dark", colors=["#000000"])
    with pytest.raises(ValueError, match="built-in"):
        unregister_theme("default")


def test_unknown_base_is_rejected():
    with pytest.raises(ValueError, match="Unknown base theme"):
        register_theme("x", base="nope")


@pytest.mark.parametrize("bad", [
    {"colours": ["#000000"]},          # misspelled key
    {"colors": "#000000"},             # a string, not a list
    {"colors": []},                    # empty
    {"colors": [1, 2, 3]},             # not strings
])
def test_malformed_theme_definitions_are_rejected(bad):
    with pytest.raises(ValueError):
        register_theme("x", **bad)


# ---------------------------------------------------------------------------
# Unknown names used to fall back silently
# ---------------------------------------------------------------------------

def test_typo_in_theme_name_raises_instead_of_rendering_the_wrong_theme():
    """``themes.get(name, themes["default"])`` meant theme="darkk" produced a
    light chart with no indication anything was wrong."""
    with pytest.raises(ValueError, match="Unknown theme"):
        Figure(theme="darkk", auto_display=False)


def test_unknown_theme_error_suggests_the_closest_name():
    with pytest.raises(ValueError, match="Did you mean 'dark'"):
        get_theme("darkk")


def test_partial_dict_theme_is_filled_from_default():
    theme = get_theme({"colors": ["#ff0000"]})
    assert theme["colors"] == ["#ff0000"]
    assert theme["font"] == glyphx.themes["default"]["font"]


# ---------------------------------------------------------------------------
# Palette assignment
# ---------------------------------------------------------------------------

def _colors_of(theme, n=3):
    fig = Figure(theme=theme, auto_display=False)
    for i in range(n):
        fig.line([1, 2, 3], [float(i), 2.0, 3.0])
    fig.render_svg()
    return [s.color for s in fig.axes.series]


def test_series_cycle_through_the_theme_palette():
    """Every series defaulted to #1f77b4, so charts with several lines drew
    them all in the same color and no theme palette was ever used."""
    assert _colors_of("default") == glyphx.themes["default"]["colors"][:3]


def test_colorblind_theme_actually_uses_its_palette():
    assert _colors_of("colorblind") == glyphx.themes["colorblind"]["colors"][:3]


def test_palette_wraps_when_there_are_more_series_than_colors():
    register_theme("two", colors=["#111111", "#222222"])
    assert _colors_of("two", n=5) == ["#111111", "#222222",
                                      "#111111", "#222222", "#111111"]


def test_explicit_color_is_never_overridden():
    fig = Figure(auto_display=False)
    fig.line([1, 2, 3], [1.0, 2.0, 3.0], color="#ff0000")
    fig.line([1, 2, 3], [3.0, 2.0, 1.0])
    fig.render_svg()
    assert [s.color for s in fig.axes.series][0] == "#ff0000"


# ---------------------------------------------------------------------------
# Multi-color series
# ---------------------------------------------------------------------------

def _palette_of(series, theme, attr="colors"):
    fig = Figure(theme=theme, auto_display=False)
    fig.add(series)
    fig.render_svg()
    return getattr(fig.axes.series[0], attr)


def test_pie_uses_the_active_theme_palette():
    """
    Pie and donut hardcoded a copy of the light palette, so every theme --
    including colorblind -- drew the same slice colors.  They are also
    axis-free (x and y are None), so they never reach Axes.finalize() and
    the assignment has to happen before the render branches.
    """
    from glyphx import PieSeries

    expected = glyphx.themes["colorblind"]["colors"][:3]
    assert _palette_of(PieSeries([3, 2, 1], labels=list("abc")), "colorblind")[:3] == expected


def test_donut_uses_the_active_theme_palette():
    from glyphx import DonutSeries

    expected = glyphx.themes["dark"]["colors"][:3]
    assert _palette_of(DonutSeries([3, 2, 1], labels=list("abc")), "dark")[:3] == expected


def test_grouped_bar_uses_the_active_theme_palette():
    from glyphx import GroupedBarSeries

    series = GroupedBarSeries(["g1", "g2"], ["a", "b"], [[1, 2], [2, 1]])
    expected = glyphx.themes["colorblind"]["colors"][:2]
    assert _palette_of(series, "colorblind", attr="group_colors") == expected


def test_stacked_bar_uses_the_active_theme_palette():
    from glyphx import StackedBarSeries

    series = StackedBarSeries(["x", "y"], {"a": [1, 2], "b": [2, 1]})
    expected = glyphx.themes["colorblind"]["colors"][:2]
    assert _palette_of(series, "colorblind")[:2] == expected


def test_explicit_palette_is_never_overridden():
    from glyphx import PieSeries

    chosen = ["#111111", "#222222", "#333333"]
    series = PieSeries([3, 2, 1], labels=list("abc"), colors=chosen)
    assert _palette_of(series, "colorblind") == chosen


def test_colormap_driven_series_are_left_alone():
    """treemap, raincloud and bump chart pick colors from a colormap on
    purpose; the theme palette must not clobber them."""
    from glyphx import TreemapSeries

    series = TreemapSeries(labels=list("abc"), values=[5.0, 3.0, 2.0])
    before = list(series.colors)
    fig = Figure(theme="colorblind", auto_display=False)
    fig.add(series)
    fig.render_svg()
    assert series.colors == before


def test_assignment_is_idempotent():
    """render_svg() applies it, then Axes.finalize() applies it again."""
    fig = Figure(theme="dark", auto_display=False)
    fig.line([1, 2, 3], [1.0, 2.0, 3.0]).line([1, 2, 3], [3.0, 2.0, 1.0])
    first = [s.color for s in (fig.render_svg(), fig.axes.series)[1]]
    fig.render_svg()
    assert [s.color for s in fig.axes.series] == first
