"""
Bar and stacked-bar charts with negative values.

Bars are measured from zero, not from the bottom of the canvas.  That
distinction only shows up once a value goes negative, which is why these
cases had gone unnoticed: every existing bar test used positive data.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

import glyphx
from glyphx import Figure

TOL = 1.0   # pixel tolerance for baseline comparisons


def _bars(svg: str) -> list[dict]:
    """Extract the rendered bar rectangles with their data values."""
    bars = []
    for match in re.finditer(r"<rect class=\"glyphx-point[^>]*/>", svg):
        tag = match.group(0)
        y = re.search(r'\sy="([-\d.]+)"', tag)
        h = re.search(r'\sheight="([-\d.]+)"', tag)
        v = re.search(r'data-y="([^"]*)"', tag)
        if not (y and h):
            continue
        top, height = float(y.group(1)), float(h.group(1))
        bars.append({
            "top": top,
            "bottom": top + height,
            "height": height,
            "value": float(v.group(1)) if v and v.group(1) else None,
        })
    return bars


# ---------------------------------------------------------------------------
# Plain bar charts
# ---------------------------------------------------------------------------

def test_negative_bars_hang_below_the_zero_line():
    """
    Every bar used to be drawn from the bottom of the canvas.

    A -3 next to a +5 rendered as a stub sitting on the axis floor instead of
    descending from zero.
    """
    fig = Figure(auto_display=False).bar(["a", "b", "c"], [5.0, -3.0, 2.0])
    svg = fig.render_svg()
    ET.fromstring(svg)

    zero = fig.axes.scale_y(0)
    for bar in _bars(svg):
        if bar["value"] > 0:
            assert abs(bar["bottom"] - zero) < TOL, "positive bar must sit on zero"
            assert bar["top"] < zero
        else:
            assert abs(bar["top"] - zero) < TOL, "negative bar must hang from zero"
            assert bar["bottom"] > zero


def test_all_negative_bars_render():
    fig = Figure(auto_display=False).bar(["a", "b", "c"], [-2.0, -5.0, -1.0])
    svg = fig.render_svg()
    ET.fromstring(svg)

    zero = fig.axes.scale_y(0)
    bars = _bars(svg)
    assert len(bars) == 3
    for bar in bars:
        assert abs(bar["top"] - zero) < TOL
        assert bar["height"] > 0


def test_bar_heights_are_proportional_to_magnitude():
    fig = Figure(auto_display=False).bar(["a", "b"], [4.0, -2.0])
    bars = {b["value"]: b["height"] for b in _bars(fig.render_svg())}
    assert bars[4.0] == pytest.approx(bars[-2.0] * 2, rel=0.02)


def test_zero_is_inside_the_domain_for_bars():
    for values in ([5.0, 3.0], [-5.0, -3.0], [5.0, -3.0]):
        fig = Figure(auto_display=False).bar(["a", "b"], values)
        fig.render_svg()
        low, high = fig.axes._y_domain
        assert low <= 0 <= high, f"{values} produced a domain excluding zero"


def test_zero_baseline_is_drawn_when_data_crosses_zero():
    crossing = Figure(auto_display=False).bar(["a", "b"], [5.0, -3.0]).render_svg()
    positive = Figure(auto_display=False).bar(["a", "b"], [5.0, 3.0]).render_svg()
    assert "glyphx-zero-line" in crossing
    assert "glyphx-zero-line" not in positive, "the X axis already marks zero here"


def test_bar_with_a_zero_value_renders():
    svg = Figure(auto_display=False).bar(["a", "b", "c"], [5.0, 0.0, -2.0]).render_svg()
    ET.fromstring(svg)


# ---------------------------------------------------------------------------
# Stacked bars
# ---------------------------------------------------------------------------

def _stacked_fig(series, **kwargs):
    fig = Figure(auto_display=False)
    fig.add(glyphx.StackedBarSeries(["Q1", "Q2", "Q3"], series, **kwargs))
    return fig


def _segments(svg: str) -> list[dict]:
    out = []
    for match in re.finditer(r"<rect class=\"glyphx-point[^>]*/>", svg):
        tag = match.group(0)
        y = re.search(r'\sy="([-\d.]+)"', tag)
        h = re.search(r'\sheight="([-\d.]+)"', tag)
        cat = re.search(r'data-x="([^"]*)"', tag)
        val = re.search(r'data-value="([^"%]*)', tag)
        if not (y and h and cat):
            continue
        top = float(y.group(1))
        out.append({
            "cat": cat.group(1),
            "top": top,
            "bottom": top + float(h.group(1)),
            "value": float(val.group(1)) if val else None,
        })
    return out


def test_stacked_bars_diverge_around_zero():
    """Positives stack up from zero, negatives stack down from it."""
    fig = _stacked_fig({"a": [3.0, -2.0, 1.0],
                        "b": [2.0, 4.0, -3.0],
                        "c": [-1.0, 1.0, 2.0]})
    svg = fig.render_svg()
    ET.fromstring(svg)

    zero = fig.axes.scale_y(0)
    for seg in _segments(svg):
        if seg["value"] > 0:
            assert seg["bottom"] <= zero + TOL, "positive segment dips below zero"
        elif seg["value"] < 0:
            assert seg["top"] >= zero - TOL, "negative segment rises above zero"


def test_stacked_segments_do_not_overlap():
    """A single running total let a negative pull the stack back over itself."""
    fig = _stacked_fig({"a": [3.0, -2.0, 1.0],
                        "b": [2.0, 4.0, -3.0],
                        "c": [-1.0, 1.0, 2.0]})
    segments = _segments(fig.render_svg())

    from collections import defaultdict
    grouped = defaultdict(list)
    for seg in segments:
        grouped[(seg["cat"], seg["value"] >= 0)].append((seg["top"], seg["bottom"]))

    for key, spans in grouped.items():
        spans.sort()
        for (_, first_bottom), (second_top, _) in zip(spans, spans[1:]):
            assert first_bottom <= second_top + TOL, f"segments overlap in {key}"


def test_stacked_domain_covers_both_directions():
    fig = _stacked_fig({"a": [3.0, -2.0, 1.0], "b": [2.0, -4.0, -3.0]})
    fig.render_svg()
    low, high = fig.axes._y_domain
    assert low < 0 < high
    assert low <= -6.0, "domain must reach the summed negative extent"
    assert high >= 5.0, "domain must reach the summed positive extent"


def test_stacked_extent_sums_each_sign_separately():
    """The signed total cancels; each side has to be summed on its own."""
    fig = _stacked_fig({"up": [10.0, 0.0, 0.0], "down": [-10.0, 0.0, 0.0]})
    fig.render_svg()
    low, high = fig.axes._y_domain
    assert high >= 10.0 and low <= -10.0


def test_all_negative_stack():
    fig = _stacked_fig({"a": [-1.0, -2.0, -3.0], "b": [-2.0, -1.0, -1.0]})
    svg = fig.render_svg()
    ET.fromstring(svg)
    zero = fig.axes.scale_y(0)
    for seg in _segments(svg):
        assert seg["top"] >= zero - TOL


def test_normalized_stack_with_cancelling_values():
    """+5 and -5 sum to zero; dividing by that used to be a zero total."""
    fig = Figure(auto_display=False)
    series = glyphx.StackedBarSeries(["A"], {"up": [5.0], "down": [-5.0]},
                                     normalize=True)
    fig.add(series)
    ET.fromstring(fig.render_svg())
    assert sorted(series._mat.ravel().tolist()) == [-50.0, 50.0]


def test_normalized_stack_shares_use_absolute_totals():
    series = glyphx.StackedBarSeries(["A", "B"], {"x": [3.0, -1.0], "y": [1.0, -3.0]},
                                     normalize=True)
    Figure(auto_display=False).add(series).render_svg()
    assert abs(series._mat).sum(axis=0).tolist() == [100.0, 100.0]


def test_stacked_css_class_is_deterministic():
    """It was derived from id(self), so output changed on every run."""
    first = glyphx.StackedBarSeries(["A"], {"x": [1.0]}).css_class
    second = glyphx.StackedBarSeries(["A"], {"x": [1.0]}).css_class
    assert first == second
    assert re.fullmatch(r"series-[0-9a-f]+", first)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["stacked", "stacked_bar", "stackedbar"])
def test_plot_accepts_stacked_kinds(kind):
    """kind='stacked' also used to fail on string categories."""
    fig = glyphx.plot(x=["Q1", "Q2"], series={"a": [3.0, -2.0], "b": [2.0, 4.0]},
                      kind=kind, auto_display=False)
    ET.fromstring(fig.render_svg())


def test_unknown_kind_suggests_stacked_bar():
    with pytest.raises(ValueError, match="stacked"):
        glyphx.plot([1], [1.0], kind="stakced", auto_display=False)


@pytest.fixture
def long_df():
    return pd.DataFrame({
        "quarter": ["Q1"] * 3 + ["Q2"] * 3 + ["Q3"] * 3,
        "segment": ["Cloud", "AI", "Legacy"] * 3,
        "revenue": [3.0, 2.0, -1.0, -2.0, 4.0, 1.0, 1.0, -3.0, 2.0],
    })


def test_accessor_stacked_bar(long_df):
    fig = long_df.glyphx.stacked_bar(x="quarter", y="revenue", stack="segment")
    ET.fromstring(fig.render_svg())
    low, high = fig.axes._y_domain
    assert low < 0 < high


def test_accessor_stacked_bar_normalized(long_df):
    fig = long_df.glyphx.stacked_bar(x="quarter", y="revenue", stack="segment",
                                     normalize=True)
    ET.fromstring(fig.render_svg())


def test_accessor_stacked_bar_aggregates_duplicates(long_df):
    """Two rows for the same (category, stack) pair should sum, not collide."""
    doubled = pd.concat([long_df, long_df], ignore_index=True)
    single = long_df.glyphx.stacked_bar(x="quarter", y="revenue", stack="segment")
    double = doubled.glyphx.stacked_bar(x="quarter", y="revenue", stack="segment")
    single.render_svg()
    double.render_svg()
    assert double.axes._y_domain[1] == pytest.approx(
        single.axes._y_domain[1] * 2, rel=0.05
    )


def test_accessor_stacked_bar_reports_unknown_columns(long_df):
    with pytest.raises(KeyError, match="quarter"):
        long_df.glyphx.stacked_bar(x="quarter", y="revenue", stack="nope")
