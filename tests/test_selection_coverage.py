"""
Every chart type should answer a click with its own values.

Selection binds to ``[data-x]``, so a type that never emits it is invisible
to the detail panel, cross-filtering and the tooltip. Pie, donut, treemap,
sunburst and box plots all drew ``glyphx-point`` elements -- they looked
clickable and had hover styling -- while carrying no values at all, so
clicking one did nothing.
"""

import re

import pytest

from glyphx import (
    BoxPlotSeries,
    CandlestickSeries,
    DivergingBarSeries,
    DonutSeries,
    ECDFSeries,
    Figure,
    GroupedBarSeries,
    PieSeries,
    StackedBarSeries,
    SunburstSeries,
    TreemapSeries,
    WaterfallSeries,
)


def _svg(series):
    fig = Figure(auto_display=False)
    fig.add(series)
    return fig.render_svg()


SERIES = {
    "pie": lambda: PieSeries([3.0, 2.0, 1.0], labels=list("abc")),
    "donut": lambda: DonutSeries([3.0, 2.0, 1.0], labels=list("abc")),
    "treemap": lambda: TreemapSeries(labels=list("abc"), values=[5.0, 3.0, 2.0]),
    "sunburst": lambda: SunburstSeries(labels=["r", "a", "b"], parents=["", "r", "r"],
                                       values=[10.0, 4.0, 6.0]),
    "boxplot": lambda: BoxPlotSeries([[1.0, 2.0, 3.0, 4.0, 9.0]], categories=["a"]),
    "waterfall": lambda: WaterfallSeries(["a", "b"], [5.0, -2.0]),
    "candlestick": lambda: CandlestickSeries(["d1"], [1.0], [3.0], [0.5], [2.0]),
    "diverging": lambda: DivergingBarSeries(["a", "b"], [3.0, -2.0]),
    "stacked": lambda: StackedBarSeries(["x", "y"], {"a": [1.0, 2.0], "b": [2.0, 1.0]}),
    "grouped": lambda: GroupedBarSeries(["g1", "g2"], ["a", "b"], [[1.0, 2.0], [2.0, 1.0]]),
    "ecdf": lambda: ECDFSeries([1.0, 2.0, 3.0, 4.0], show_points=True),
}


@pytest.mark.parametrize("name", sorted(SERIES))
def test_every_chart_type_emits_selectable_values(name):
    svg = _svg(SERIES[name]())
    assert "data-x=" in svg, f"{name} draws elements that carry no values"
    assert "data-y=" in svg


@pytest.mark.parametrize("name", sorted(SERIES))
def test_selectable_elements_are_also_focusable(name):
    """Keyboard users reach points by tab; selection must not be mouse-only."""
    svg = _svg(SERIES[name]())
    assert 'tabindex="0"' in svg


def test_line_bar_and_scatter_still_carry_values():
    fig = Figure(auto_display=False)
    fig.line(["a", "b"], [1.0, 2.0]).bar(["a", "b"], [2.0, 1.0]).scatter([1.0], [1.0])
    svg = fig.render_svg()
    assert svg.count("data-x=") >= 5


# ---------------------------------------------------------------------------
# Part-of-a-whole types carry their share
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["pie", "donut", "treemap"])
def test_part_of_whole_types_report_a_percentage(name):
    """A pie is read for "28%", not only for the raw value."""
    svg = _svg(SERIES[name]())
    assert "data-percent=" in svg


def test_percentages_are_the_share_of_the_total():
    svg = _svg(PieSeries([45.0, 30.0, 25.0], labels=list("abc")))
    pcts = sorted(float(v) for v in re.findall(r'data-percent="([\d.]+)"', svg))
    assert pcts == [25.0, 30.0, 45.0]


def test_pie_slice_reports_its_label_and_value():
    svg = _svg(PieSeries([45.0, 30.0, 25.0], labels=["Alpha", "Beta", "Gamma"]))
    assert 'data-x="Alpha"' in svg
    assert 'data-y="45.0"' in svg


def test_boxplot_reports_the_median_as_its_value():
    """Quartiles stay in data-q1/q2/q3; y is the number a box is read for."""
    svg = _svg(BoxPlotSeries([[1.0, 2.0, 3.0, 4.0, 9.0]], categories=["a"]))
    assert 'data-x="a"' in svg
    assert "data-median=" in svg
    assert "data-q1=" in svg and "data-q3=" in svg


def test_existing_tooltip_attribute_is_preserved():
    """accessibility.js, tooltip.js and notebook.js all read data-value."""
    assert "data-value=" in _svg(SERIES["pie"]())


# ---------------------------------------------------------------------------
# The event carries chart-specific fields
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_event_detail_exposes_chart_specific_values(tmp_path):
    """
    A pie has percent, a box plot has quartiles, a candlestick has OHLC. The
    event used to surface only x/y/label/meta, so a listener could not reach
    any of them.
    """
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    fig = Figure(width=460, height=340, auto_display=False)
    fig.pie([45.0, 30.0, 25.0], labels=["Alpha", "Beta", "Gamma"])
    path = tmp_path / "pie.html"
    fig.share(str(path))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(path.as_uri())
        page.wait_for_timeout(300)
        page.evaluate("""() => { window.__d = null;
            document.addEventListener('glyphx:select', e => window.__d = e.detail); }""")
        page.click(".glyphx-point >> nth=1")
        page.wait_for_timeout(250)
        detail = page.evaluate("window.__d")
        browser.close()

    assert detail["x"] == "Beta"
    assert detail["y"] == "30.0"
    assert detail["data"]["percent"] == "30.0"


@pytest.mark.browser
def test_detail_panel_can_show_a_chart_specific_field(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    fig = Figure(width=460, height=340, auto_display=False)
    fig.pie([45.0, 30.0, 25.0], labels=["Alpha", "Beta", "Gamma"])
    fig.add_detail_panel(["x", "y", "percent"], title="Selected slice")
    path = tmp_path / "pie_panel.html"
    fig.share(str(path))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(path.as_uri())
        page.wait_for_timeout(300)
        page.click(".glyphx-point >> nth=1")
        page.wait_for_timeout(250)
        text = page.eval_on_selector(".glyphx-detail-panel", "e => e.innerText")
        browser.close()

    assert "Beta" in text and "30.0" in text
    assert "percent" in text
