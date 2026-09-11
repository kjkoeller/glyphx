"""
Axis labels must survive zooming.

Zoom rewrites the SVG's ``viewBox``, which crops the whole drawing --
including tick labels, which are static text positioned for the original
domain. A few scroll steps in and the chart had no visible scale at all: no
numbers, no reference, no way to tell what was on screen. The labels are now
redrawn for whatever region is actually visible.
"""

import re

import pytest

from glyphx import Figure

VALUES = [float((i * 7) % 13) for i in range(1, 21)]


@pytest.fixture
def chart(tmp_path):
    path = tmp_path / "zoom.html"
    fig = Figure(width=640, height=480, auto_display=False, title="Signal")
    fig.line(list(range(1, 21)), VALUES)
    fig.share(str(path))
    return path


@pytest.fixture
def page(chart):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 760, "height": 760})
        pg.goto(chart.as_uri())
        pg.wait_for_timeout(350)
        yield pg
        browser.close()


def _visible_ticks(page):
    return page.eval_on_selector_all(
        ".glyphx-tick",
        "els => els.filter(e => e.style.display !== 'none').map(e => e.textContent)")


def _zoom_in(page, steps=4):
    page.mouse.move(380, 350)
    for _ in range(steps):
        page.mouse.wheel(0, -200)
        page.wait_for_timeout(60)


# ---------------------------------------------------------------------------
# Markup the JavaScript depends on
# ---------------------------------------------------------------------------

def test_tick_labels_are_tagged_and_carry_their_value():
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    assert "glyphx-xtick" in svg and "glyphx-ytick" in svg
    assert "data-tick=" in svg


def test_axis_geometry_is_published_on_the_root():
    """Without the plot rect and domains there is no way to map a zoomed
    viewBox back to data coordinates."""
    svg = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0]).render_svg()
    for attr in ("data-plot=", "data-domain-x=", "data-domain-y=",
                 "data-xscale=", "data-yscale="):
        assert attr in svg, f"missing {attr}"


def test_geometry_matches_the_padding_and_domain():
    fig = Figure(width=640, height=480, auto_display=False)
    fig.line([1, 2, 3], [1.0, 2.0, 3.0])
    svg = fig.render_svg()
    plot = re.search(r'data-plot="([^"]+)"', svg).group(1).split(",")
    pad = fig.axes.padding
    assert [float(v) for v in plot] == [pad, pad, fig.axes.width - pad,
                                        fig.axes.height - pad]


def test_no_geometry_emitted_for_an_empty_figure():
    assert "data-plot=" not in Figure(auto_display=False).render_svg()


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_labels_remain_after_zooming(page):
    """The bug: six scroll steps left the chart with no numbers at all."""
    _zoom_in(page, steps=6)
    assert len(_visible_ticks(page)) >= 4


@pytest.mark.browser
def test_labels_update_to_the_visible_range(page):
    before = _visible_ticks(page)
    _zoom_in(page)
    after = _visible_ticks(page)
    assert before != after, "labels stayed on the original domain"


@pytest.mark.browser
def test_labels_stay_inside_the_chart_area(page):
    """Pinned to the visible window, not the original canvas, or they sit
    off-screen as soon as you pan away."""
    _zoom_in(page)
    outside = page.evaluate("""() => {
        const svg = document.querySelector('svg[data-glyphx]');
        const r = svg.getBoundingClientRect();
        return Array.from(svg.querySelectorAll('.glyphx-tick'))
          .filter(e => e.style.display !== 'none')
          .filter(e => { const b = e.getBoundingClientRect();
              return b.left < r.left - 1 || b.right > r.right + 1
                  || b.top < r.top - 1 || b.bottom > r.bottom + 1; })
          .map(e => e.textContent);
    }""")
    assert outside == [], f"labels rendered outside the chart: {outside}"


@pytest.mark.browser
def test_both_axes_are_still_labelled_after_zooming(page):
    _zoom_in(page)
    counts = page.evaluate("""() => ({
        x: document.querySelectorAll('.glyphx-xtick:not([style*="none"])').length,
        y: document.querySelectorAll('.glyphx-ytick:not([style*="none"])').length,
    })""")
    assert counts["x"] >= 2 and counts["y"] >= 2


@pytest.mark.browser
def test_label_text_stays_a_readable_size(page):
    """The viewBox scales everything, so text would balloon without the
    inverse scale applied to it."""
    _zoom_in(page, steps=6)
    sizes = page.eval_on_selector_all(
        ".glyphx-tick", "els => els.map(e => parseFloat(e.getAttribute('font-size')))")
    assert all(2 < s < 40 for s in sizes if s), sizes


@pytest.mark.browser
def test_reset_restores_the_original_labels_exactly(page):
    """Restore replays the snapshot rather than recomputing, so a
    zoom-and-reset round trip leaves the chart as it started."""
    def snapshot():
        return page.eval_on_selector_all(
            ".glyphx-tick",
            "els => els.map(e => [e.textContent, e.getAttribute('x'),"
            " e.getAttribute('y'), e.style.display])")

    before = snapshot()
    _zoom_in(page)
    assert snapshot() != before

    box = page.eval_on_selector("svg[data-glyphx]", "e => e.getBoundingClientRect()")
    page.mouse.dblclick(box["x"] + box["width"] - 30, box["y"] + 30)
    page.wait_for_timeout(350)
    assert snapshot() == before
