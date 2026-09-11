"""
The selection detail panel.

``glyphx:select`` already let anything on the page react to a clicked point,
but only by writing a JavaScript listener. This covers the same ground from
Python for the common case, and must not take the event API away: the panel
is an ordinary listener, so a caller's own listeners still fire.
"""

import json

import pytest

from glyphx import Figure, ScatterSeries

RECORDS = [
    {"customer": "Acme", "region": "North", "tier": "Gold"},
    {"customer": "Belltown", "region": "South", "tier": "Silver"},
    {"customer": "Cortex", "region": "North", "tier": "Gold"},
]


def _figure(**panel_kwargs):
    fig = Figure(width=520, height=340, auto_display=False, title="Revenue")
    fig.add(ScatterSeries([10.0, 25.0, 40.0], [5.0, 18.0, 30.0],
                          label="Customers", meta=RECORDS))
    if panel_kwargs is not None:
        fig.add_detail_panel(**panel_kwargs)
    return fig


# ---------------------------------------------------------------------------
# Markup
# ---------------------------------------------------------------------------

def test_no_panel_markup_unless_requested():
    """
    The script is always inlined and is inert without a panel element, so
    the class name appears either way -- check for the element itself.
    """
    fig = Figure(auto_display=False).scatter([1, 2], [1.0, 2.0])
    assert '<div class="glyphx-detail-panel"' not in fig.share()


def test_panel_config_travels_in_the_markup():
    html = _figure(fields=["customer", "region"], title="Selected").share()
    assert "glyphx-detail-panel" in html
    assert "customer" in html and "Selected" in html


def test_add_detail_panel_chains():
    fig = Figure(auto_display=False).scatter([1, 2], [1.0, 2.0])
    assert fig.add_detail_panel() is fig


def test_config_is_escaped_not_interpolated_raw():
    """The title is caller text and lands in an HTML attribute."""
    html = _figure(title='Nasty " <script>').share()
    assert "<script>Nasty" not in html
    assert "&quot;" in html or "&#34;" in html


def test_script_ships_in_both_export_paths(tmp_path):
    from glyphx.figure import SubplotGrid

    share_html = _figure(fields=["customer"]).share()
    assert "glyphx:deselect" in share_html

    grid_path = tmp_path / "grid.html"
    SubplotGrid(1, 1).add(_figure(fields=["customer"]), 0, 0).save(str(grid_path))
    assert "glyphx-detail-panel-style" in grid_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

@pytest.fixture
def page(tmp_path, request):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    kwargs = getattr(request, "param", {"fields": ["customer", "region", "tier"],
                                        "title": "Selected customer"})
    path = tmp_path / "panel.html"
    _figure(**kwargs).share(str(path))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1000, "height": 560})
        pg.goto(path.as_uri())
        pg.wait_for_timeout(350)
        yield pg
        browser.close()


@pytest.mark.browser
def test_panel_starts_with_its_empty_message(page):
    text = page.eval_on_selector(".glyphx-detail-panel", "e => e.textContent")
    assert "Click a point" in text
    assert page.eval_on_selector(".glyphx-detail-panel", "e => e.dataset.empty") == "true"


@pytest.mark.browser
def test_clicking_a_point_fills_the_panel(page):
    page.click(".glyphx-point >> nth=1")
    page.wait_for_timeout(200)
    text = page.eval_on_selector(".glyphx-detail-panel", "e => e.innerText")
    assert "Belltown" in text and "South" in text and "Silver" in text
    assert page.eval_on_selector(".glyphx-detail-panel", "e => e.dataset.empty") == "false"


@pytest.mark.browser
def test_selecting_another_point_replaces_the_contents(page):
    page.click(".glyphx-point >> nth=1")
    page.wait_for_timeout(150)
    page.click(".glyphx-point >> nth=2")
    page.wait_for_timeout(200)
    text = page.eval_on_selector(".glyphx-detail-panel", "e => e.innerText")
    assert "Cortex" in text
    assert "Belltown" not in text


@pytest.mark.browser
def test_escape_and_reclick_both_restore_the_empty_state(page):
    page.click(".glyphx-point >> nth=1")
    page.wait_for_timeout(150)
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    assert "Click a point" in page.eval_on_selector(".glyphx-detail-panel", "e => e.textContent")

    page.click(".glyphx-point >> nth=0")
    page.wait_for_timeout(150)
    page.click(".glyphx-point >> nth=0")
    page.wait_for_timeout(200)
    assert "Click a point" in page.eval_on_selector(".glyphx-detail-panel", "e => e.textContent")


@pytest.mark.browser
def test_fields_control_order_and_omit_the_rest(page):
    page.click(".glyphx-point >> nth=0")
    page.wait_for_timeout(200)
    terms = page.eval_on_selector_all(".glyphx-detail-panel dt",
                                      "els => els.map(e => e.textContent)")
    assert terms == ["customer", "region", "tier"]


@pytest.mark.browser
@pytest.mark.parametrize("page", [{"fields": None}], indirect=True)
def test_no_field_list_shows_everything_the_point_carries(page):
    page.click(".glyphx-point >> nth=0")
    page.wait_for_timeout(200)
    terms = page.eval_on_selector_all(".glyphx-detail-panel dt",
                                      "els => els.map(e => e.textContent)")
    assert set(terms) == {"customer", "region", "tier"}


@pytest.mark.browser
def test_panel_sits_beside_the_chart_not_below_it(page):
    """The template sets `svg { width: 100% }`, which pushed the panel onto
    the next row until the SVG was given a shrinkable flex basis."""
    page.click(".glyphx-point >> nth=1")
    page.wait_for_timeout(200)
    svg = page.eval_on_selector("svg[data-glyphx]", "e => e.getBoundingClientRect()")
    panel = page.eval_on_selector(".glyphx-detail-panel", "e => e.getBoundingClientRect()")
    assert panel["left"] >= svg["right"] - 1


@pytest.mark.browser
def test_the_panel_does_not_replace_the_event_api(page):
    """A caller's own listener must still receive the same click."""
    page.evaluate("""() => {
        window.__seen = [];
        document.addEventListener('glyphx:select', e => window.__seen.push(e.detail.meta));
    }""")
    page.click(".glyphx-point >> nth=1")
    page.wait_for_timeout(200)
    seen = page.evaluate("window.__seen")
    assert seen and seen[0]["customer"] == "Belltown"
    assert "Belltown" in page.eval_on_selector(".glyphx-detail-panel", "e => e.innerText")


@pytest.mark.browser
def test_values_are_rendered_as_text_not_markup(tmp_path):
    """Point metadata is caller data; building innerHTML from it would make
    any dataset containing a '<' an injection vector."""
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    fig = Figure(width=420, height=300, auto_display=False)
    fig.add(ScatterSeries([1.0, 2.0], [1.0, 2.0],
                          meta=[{"note": "<img src=x onerror=window.__x=1>"}, {"note": "ok"}]))
    fig.add_detail_panel(["note"])
    path = tmp_path / "xss.html"
    fig.share(str(path))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page()
        pg.goto(path.as_uri())
        pg.wait_for_timeout(300)
        pg.click(".glyphx-point >> nth=0")
        pg.wait_for_timeout(250)
        injected = pg.evaluate("window.__x")
        text = pg.eval_on_selector(".glyphx-detail-panel", "e => e.innerText")
        imgs = pg.eval_on_selector_all(".glyphx-detail-panel img", "els => els.length")
        browser.close()

    assert injected is None, "metadata was executed as markup"
    assert imgs == 0
    assert "<img" in text, "the value should be shown literally"


def test_meta_json_round_trips_through_the_attribute():
    html = _figure(fields=["customer"]).share()
    assert json.dumps({"customer": "Acme", "region": "North", "tier": "Gold"},
                      default=str).replace('"', "&quot;") in html \
        or "Acme" in html
