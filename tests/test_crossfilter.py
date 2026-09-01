"""
Cross-chart filtering: click a value in one chart, dim it everywhere else.

The markup half is checked without a browser; the behaviour half needs one,
because the bug that mattered here was a CSS specificity conflict that only
shows up once styles are actually computed.
"""

import pytest

from glyphx import Figure
from glyphx.figure import SubplotGrid

MONTHS = ["Jan", "Feb", "Mar", "Apr"]


def _chart(title, values, crossfilter=True):
    fig = Figure(width=420, height=300, auto_display=False, title=title)
    fig.bar(MONTHS, values)
    if crossfilter:
        fig.enable_crossfilter()
    return fig


# ---------------------------------------------------------------------------
# Opt-in marker
# ---------------------------------------------------------------------------

def test_crossfilter_is_off_by_default():
    fig = Figure(auto_display=False).bar(MONTHS, [1.0, 2.0, 3.0, 4.0])
    assert "data-glyphx-crossfilter" not in fig.render_svg()


def test_enable_crossfilter_marks_the_svg_root():
    assert 'data-glyphx-crossfilter="true"' in _chart("R", [1.0, 2.0, 3.0, 4.0]).render_svg()


def test_enable_crossfilter_chains_and_can_be_turned_back_off():
    fig = _chart("R", [1.0, 2.0, 3.0, 4.0])
    assert fig.enable_crossfilter(False) is fig
    assert "data-glyphx-crossfilter" not in fig.render_svg()


def test_join_key_is_present_on_every_drawn_element():
    """data-x is what the charts filter on; without it nothing can match."""
    svg = _chart("R", [1.0, 2.0, 3.0, 4.0]).render_svg()
    for month in MONTHS:
        assert f'data-x="{month}"' in svg


# ---------------------------------------------------------------------------
# Script delivery -- two separate assembly paths, both must ship it
# ---------------------------------------------------------------------------

def test_share_inlines_the_crossfilter_script(tmp_path):
    path = tmp_path / "one.html"
    _chart("R", [1.0, 2.0, 3.0, 4.0]).share(str(path))
    assert "glyphx-crossfilter-dim" in path.read_text(encoding="utf-8")


def test_subplotgrid_save_inlines_the_crossfilter_script(tmp_path):
    """
    SubplotGrid.render() builds its scripts through a different function
    than share() does, so adding the asset to one left the other without it.
    """
    path = tmp_path / "dash.html"
    grid = SubplotGrid(1, 2)
    grid.add(_chart("Revenue", [10.0, 20.0, 15.0, 25.0]), 0, 0)
    grid.add(_chart("Costs", [8.0, 12.0, 11.0, 19.0]), 0, 1)
    grid.save(str(path))

    html = path.read_text(encoding="utf-8")
    assert "glyphx-crossfilter-dim" in html
    assert html.count('data-glyphx-crossfilter="true"') == 2


def test_export_stays_self_contained(tmp_path):
    path = tmp_path / "one.html"
    _chart("R", [1.0, 2.0, 3.0, 4.0]).share(str(path))
    assert "script src=" not in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

def _dashboard(tmp_path):
    path = tmp_path / "dash.html"
    grid = SubplotGrid(1, 2)
    grid.add(_chart("Revenue", [10.0, 20.0, 15.0, 25.0]), 0, 0)
    grid.add(_chart("Costs", [8.0, 12.0, 11.0, 19.0]), 0, 1)
    grid.save(str(path))
    return path


@pytest.mark.browser
def test_clicking_filters_every_participating_chart(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(_dashboard(tmp_path).as_uri())
        page.wait_for_timeout(200)

        page.click('[data-x="Feb"]')
        page.wait_for_timeout(200)

        # Computed opacity, not class membership: interact.js sets *inline*
        # opacity on click, which overrides a class rule. Asserting on the
        # class alone passed while the rendering was visibly wrong.
        opacities = page.eval_on_selector_all("[data-x]", """els => els.map(e => ({
            x: e.getAttribute('data-x'),
            o: parseFloat(getComputedStyle(e).opacity)
        }))""")
        browser.close()

    assert len(opacities) == 8, "expected 4 bars in each of 2 charts"
    for entry in opacities:
        if entry["x"] == "Feb":
            assert entry["o"] == pytest.approx(1.0), "selected value must stay lit"
        else:
            assert entry["o"] < 0.5, f"{entry['x']} should be dimmed"


@pytest.mark.browser
def test_escape_and_reclick_both_clear_the_filter(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(_dashboard(tmp_path).as_uri())
        page.wait_for_timeout(200)

        def dimmed():
            return page.eval_on_selector_all(
                ".glyphx-crossfilter-dim", "els => els.length")

        page.click('[data-x="Feb"]'); page.wait_for_timeout(150)
        assert dimmed() == 6

        page.keyboard.press("Escape"); page.wait_for_timeout(150)
        assert dimmed() == 0

        page.click('[data-x="Mar"]'); page.wait_for_timeout(150)
        page.click('[data-x="Mar"]'); page.wait_for_timeout(150)
        assert dimmed() == 0, "clicking the same value again should clear"

        browser.close()


@pytest.mark.browser
def test_filter_change_is_announced_to_screen_readers(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(_dashboard(tmp_path).as_uri())
        page.wait_for_timeout(200)

        page.click('[data-x="Feb"]'); page.wait_for_timeout(150)
        message = page.eval_on_selector(
            "#glyphx-crossfilter-status", "e => e.textContent")
        live = page.eval_on_selector(
            "#glyphx-crossfilter-status", "e => e.getAttribute('aria-live')")
        browser.close()

    assert "Feb" in message
    assert live == "polite"


@pytest.mark.browser
def test_unmarked_charts_are_left_alone(tmp_path):
    """A page can mix filtered and independent charts."""
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    path = tmp_path / "mixed.html"
    grid = SubplotGrid(1, 2)
    grid.add(_chart("Filtered", [10.0, 20.0, 15.0, 25.0]), 0, 0)
    grid.add(_chart("Independent", [8.0, 12.0, 11.0, 19.0], crossfilter=False), 0, 1)
    grid.save(str(path))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(path.as_uri())
        page.wait_for_timeout(200)
        page.click('[data-x="Feb"]')
        page.wait_for_timeout(200)
        dimmed = page.eval_on_selector_all(
            ".glyphx-crossfilter-dim", "els => els.length")
        browser.close()

    assert dimmed == 3, "only the opted-in chart should dim (4 bars - 1 selected)"
