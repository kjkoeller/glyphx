"""
Selection events: clicking a point lets anything else on the page react.

`glyphx:select` and `glyphx:deselect` are the extension surface -- a detail
panel, a table, a second chart, or a request to your own endpoint can listen
without GlyphX knowing what any of them do. All inside the exported file.
"""

import pytest

from glyphx import Figure, ScatterSeries

META = [{"customer": "Acme & Co", "id": 1},
        {"customer": "Beta", "id": 2},
        {"customer": "Gamma", "id": 3}]


def _chart(tmp_path, crossfilter=False, meta=META):
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1, 2, 3], [1.0, 2.0, 3.0], meta=meta))
    if crossfilter:
        fig.enable_crossfilter()
    path = tmp_path / "chart.html"
    fig.share(str(path))
    return path


# ---------------------------------------------------------------------------
# Per-point metadata
# ---------------------------------------------------------------------------

def test_meta_is_emitted_per_point():
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1, 2, 3], [1.0, 2.0, 3.0], meta=META))
    assert fig.render_svg().count("data-meta=") == 3


def test_meta_is_escaped():
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1], [1.0], meta=[{"customer": "Acme & Co"}]))
    svg = fig.render_svg()
    assert "&amp;" in svg
    assert 'data-meta="{"' not in svg, "unescaped quotes would break the attribute"


def test_series_without_meta_emits_nothing_extra():
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1, 2], [1.0, 2.0]))
    assert "data-meta" not in fig.render_svg()


def test_short_meta_list_does_not_raise():
    """Fewer entries than points is a caller error, not a crash."""
    fig = Figure(auto_display=False)
    fig.add(ScatterSeries([1, 2, 3], [1.0, 2.0, 3.0], meta=[{"a": 1}]))
    assert fig.render_svg().count("data-meta=") == 1


# ---------------------------------------------------------------------------
# The event
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_clicking_a_point_lets_another_element_update(tmp_path):
    """The whole point: a panel elsewhere on the page reacts to the click."""
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 420})
        page.goto(_chart(tmp_path).as_uri())
        page.wait_for_timeout(300)

        page.evaluate("""() => {
            const panel = document.createElement('div');
            panel.id = 'detail';
            panel.textContent = 'none';
            document.body.appendChild(panel);
            document.addEventListener('glyphx:select', e => {
                panel.textContent = e.detail.meta.customer + '@' + e.detail.x;
            });
            document.addEventListener('glyphx:deselect', () => {
                panel.textContent = 'none';
            });
        }""")

        def panel():
            return page.eval_on_selector("#detail", "e => e.textContent")

        assert panel() == "none"
        page.click('circle[data-x="2"]'); page.wait_for_timeout(200)
        assert panel() == "Beta@2"
        page.click('circle[data-x="3"]'); page.wait_for_timeout(200)
        assert panel() == "Gamma@3"
        page.click('circle[data-x="3"]'); page.wait_for_timeout(200)
        assert panel() == "none", "clicking the same point again should deselect"
        browser.close()


@pytest.mark.browser
def test_only_one_point_is_marked_selected(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 420})
        page.goto(_chart(tmp_path).as_uri())
        page.wait_for_timeout(300)

        page.click('circle[data-x="1"]'); page.wait_for_timeout(150)
        page.click('circle[data-x="2"]'); page.wait_for_timeout(150)
        assert page.eval_on_selector_all(".glyphx-selected", "e => e.length") == 1

        page.keyboard.press("Escape"); page.wait_for_timeout(150)
        assert page.eval_on_selector_all(".glyphx-selected", "e => e.length") == 0
        browser.close()


@pytest.mark.browser
def test_selection_composes_with_crossfilter(tmp_path):
    """
    crossfilter.js claims plain clicks in the capture phase and calls
    stopPropagation, which stopped a bubble-phase listener from ever running.
    Both are capture listeners now, so one click filters *and* selects.
    """
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 420})
        page.goto(_chart(tmp_path, crossfilter=True).as_uri())
        page.wait_for_timeout(300)

        page.evaluate("""() => { window.__got = null;
            document.addEventListener('glyphx:select',
                                      e => { window.__got = e.detail.meta.customer; }); }""")
        page.click('circle[data-x="2"]'); page.wait_for_timeout(250)

        assert page.evaluate("window.__got") == "Beta", "select event did not fire"
        assert page.eval_on_selector_all(".glyphx-crossfilter-dim", "e => e.length") > 0, \
            "crossfilter stopped working"
        browser.close()


@pytest.mark.browser
def test_event_detail_carries_the_full_point(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 420})
        page.goto(_chart(tmp_path).as_uri())
        page.wait_for_timeout(300)

        page.evaluate("""() => { window.__d = null;
            document.addEventListener('glyphx:select', e => {
                window.__d = {x: e.detail.x, y: e.detail.y,
                              series: e.detail.series, id: e.detail.meta.id}; }); }""")
        page.click('circle[data-x="2"]'); page.wait_for_timeout(200)
        detail = page.evaluate("window.__d")
        browser.close()

    assert detail["x"] == "2"
    assert detail["y"] == "2.0"
    assert detail["id"] == 2
    assert detail["series"].startswith("series-")
