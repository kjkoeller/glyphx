"""
Inset axes: a small panel drawn on top of the main plot area, with its own
independent scales.
"""

import re

import pytest

import glyphx
from glyphx import Figure, LineSeries, ScatterSeries


def _fig(width=800, height=500, **kw):
    return Figure(width=width, height=height, auto_display=False, **kw)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def test_inset_is_positioned_and_sized_as_a_fraction_of_the_canvas():
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    inset = fig.inset_axes(0.58, 0.12, 0.36, 0.32)

    assert (inset.width, inset.height) == (800 * 0.36, 500 * 0.32)

    svg = fig.render_svg()
    translate = re.search(r'glyphx-inset" transform="translate\(([^)]*)\)', svg)
    assert translate, "inset group not emitted"
    x_px, y_px = (float(v) for v in translate.group(1).split(","))
    # Emitted coordinates are rounded to SVG_PRECISION, so compare loosely:
    # 800 * 0.58 is 463.99999999999994 in binary floating point.
    assert x_px == pytest.approx(800 * 0.58)
    assert y_px == pytest.approx(500 * 0.12)


def test_inset_coordinates_are_rounded_like_other_emitted_values():
    """Fractional arithmetic otherwise emits 463.99999999999994."""
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.inset_axes(0.58, 0.12, 0.36, 0.32)
    svg = fig.render_svg()
    assert "463.99999999999994" not in svg
    assert fig.render_svg() == svg, "re-render must be byte-identical"


def test_inset_padding_scales_down_from_the_figure_default():
    """The figure default of 50 would leave a small inset no plot area."""
    fig = _fig()
    inset = fig.inset_axes(0.6, 0.1, 0.25, 0.25)
    assert inset.padding < 50
    assert inset.padding >= 14
    assert inset.padding < min(inset.width, inset.height) / 2


def test_explicit_padding_is_respected():
    fig = _fig()
    assert fig.inset_axes(0.5, 0.1, 0.4, 0.4, padding=7).padding == 7


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bounds", [
    (0.6, 0.1, 0.5, 0.3),      # overflows the right edge
    (0.1, 0.8, 0.2, 0.5),      # overflows the bottom
    (-0.1, 0.1, 0.2, 0.2),     # negative origin
    (0.1, -0.1, 0.2, 0.2),
])
def test_inset_outside_the_canvas_is_rejected(bounds):
    with pytest.raises(ValueError, match="fit inside the canvas"):
        _fig().inset_axes(*bounds)


@pytest.mark.parametrize("bounds", [(0.1, 0.1, 0, 0.2), (0.1, 0.1, 0.2, -0.3)])
def test_non_positive_inset_size_is_rejected(bounds):
    with pytest.raises(ValueError, match="must be positive"):
        _fig().inset_axes(*bounds)


# ---------------------------------------------------------------------------
# Independence from the parent
# ---------------------------------------------------------------------------

def test_inset_has_its_own_scales_and_domain():
    fig = _fig().line(list(range(100)), [float(i) for i in range(100)])
    inset = fig.inset_axes(0.6, 0.1, 0.3, 0.3)
    inset.add_series(LineSeries([0, 1, 2], [0.0, 1.0, 2.0]))
    fig.render_svg()

    assert inset.scale_x is not None and inset.scale_y is not None
    assert inset._x_domain != fig.axes._x_domain


def test_inset_inherits_the_parent_theme_by_default():
    fig = _fig(theme="dark").line([1, 2, 3], [1.0, 2.0, 3.0])
    inset = fig.inset_axes(0.6, 0.1, 0.3, 0.3)
    inset.add_series(LineSeries([1, 2], [1.0, 2.0]))
    fig.render_svg()
    assert inset.series[0].color == glyphx.themes["dark"]["colors"][0]


def test_inset_can_override_the_theme():
    fig = _fig(theme="dark").line([1, 2, 3], [1.0, 2.0, 3.0])
    inset = fig.inset_axes(0.6, 0.1, 0.3, 0.3, theme="colorblind")
    inset.add_series(LineSeries([1, 2], [1.0, 2.0]))
    fig.render_svg()
    assert inset.series[0].color == glyphx.themes["colorblind"]["colors"][0]


def test_unknown_inset_theme_raises():
    with pytest.raises(ValueError, match="Unknown theme"):
        _fig().inset_axes(0.6, 0.1, 0.3, 0.3, theme="darkk")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def test_inset_draws_an_opaque_background_by_default():
    """Otherwise the parent's grid lines and series show through."""
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.inset_axes(0.6, 0.1, 0.3, 0.3)
    group = fig.render_svg().split('class="glyphx-inset"', 1)[1]
    assert "<rect" in group.split("</g>", 1)[0]
    assert 'opacity="0.9' not in group.split("</g>", 1)[0]


def test_inset_background_can_be_transparent():
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.inset_axes(0.6, 0.1, 0.3, 0.3, background="none")
    group = fig.render_svg().split('class="glyphx-inset"', 1)[1].split("</g>", 1)[0]
    assert "<rect" not in group


def test_multiple_insets_render_in_order():
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    first = fig.inset_axes(0.05, 0.55, 0.25, 0.35)
    second = fig.inset_axes(0.35, 0.55, 0.25, 0.35)
    first.add_series(LineSeries([1, 2], [1.0, 2.0]))
    second.add_series(ScatterSeries([1, 2, 3], [3.0, 1.0, 2.0]))

    svg = fig.render_svg()
    assert svg.count('class="glyphx-inset"') == 2
    positions = [m.start() for m in re.finditer(r'class="glyphx-inset"', svg)]
    assert positions == sorted(positions)


def test_inset_works_on_an_axis_free_figure():
    """Pie charts take a different branch of render_svg entirely."""
    fig = _fig()
    fig.pie([3, 2, 1], labels=list("abc"))
    inset = fig.inset_axes(0.05, 0.05, 0.3, 0.3)
    inset.add_series(LineSeries([1, 2, 3], [1.0, 2.0, 3.0]))
    assert 'class="glyphx-inset"' in fig.render_svg()


def test_empty_inset_renders_without_error():
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    fig.inset_axes(0.6, 0.1, 0.3, 0.3)
    assert fig.render_svg().lstrip().startswith("<svg")


def test_figure_without_insets_emits_no_inset_markup():
    fig = _fig().line([1, 2, 3], [1.0, 2.0, 3.0])
    assert "glyphx-inset" not in fig.render_svg()
