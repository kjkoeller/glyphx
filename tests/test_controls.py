"""
Filter controls: checkboxes, radios, a search box and a reset button.

Everything runs in the exported HTML. Values are read out of the data, so a
caller names a field rather than enumerating its values.
"""

import pytest

from glyphx import Figure, ScatterSeries

REGIONS = ["North", "South", "East", "West"]
TIERS = ["Gold", "Silver"]
RECORDS = [{"region": REGIONS[i % 4], "tier": TIERS[i % 2],
            "customer": f"Cust{i:02d}"} for i in range(40)]


def _figure(**kwargs):
    np = pytest.importorskip("numpy")
    rng = np.random.default_rng(7)
    fig = Figure(width=560, height=400, auto_display=False, title="Accounts")
    fig.add(ScatterSeries(rng.normal(50, 15, 40).tolist(),
                          rng.normal(100, 25, 40).tolist(),
                          label="Accounts", meta=RECORDS))
    if kwargs:
        fig.add_controls(**kwargs)
    return fig


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_no_markup_unless_requested():
    assert '<div class="glyphx-controls"' not in _figure().share()


def test_at_least_one_control_is_required():
    with pytest.raises(ValueError, match="at least one"):
        _figure().add_controls()


def test_add_controls_chains():
    fig = _figure()
    assert fig.add_controls(checkboxes="region") is fig


def test_config_is_escaped_in_the_attribute():
    html = _figure(search="customer", title='Nasty " <script>').share()
    assert "<script>Nasty" not in html


def test_script_ships_in_both_export_paths(tmp_path):
    from glyphx.figure import SubplotGrid

    assert "glyphx-filtered-out" in _figure(checkboxes="region").share()

    path = tmp_path / "grid.html"
    SubplotGrid(1, 1).add(_figure(checkboxes="region"), 0, 0).save(str(path))
    assert "glyphx-controls-style" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

@pytest.fixture
def page(tmp_path, request):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    kwargs = getattr(request, "param", dict(
        checkboxes="region", radio="tier", search="customer", title="Filter"))
    path = tmp_path / "controls.html"
    _figure(**kwargs).share(str(path))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1000, "height": 620})
        pg.goto(path.as_uri())
        pg.wait_for_timeout(400)
        yield pg
        browser.close()


def _visible(page):
    return page.eval_on_selector_all(
        "[data-x]", "els => els.filter(e => "
        "!e.classList.contains('glyphx-filtered-out')).length")


@pytest.mark.browser
def test_values_are_read_from_the_data(page):
    """The caller names a field; the values come from the points."""
    boxes = page.eval_on_selector_all(
        ".glyphx-controls input[type=checkbox]", "els => els.map(e => e.value)")
    assert sorted(boxes) == sorted(REGIONS)


@pytest.mark.browser
def test_everything_is_shown_on_load(page):
    """A control panel that hides the data on load looks broken."""
    assert _visible(page) == 40
    assert "all 40" in page.eval_on_selector(".glyphx-controls-count", "e => e.textContent")


@pytest.mark.browser
def test_unticking_a_checkbox_hides_that_group(page):
    page.uncheck(".glyphx-controls input[type=checkbox][value='North']")
    page.wait_for_timeout(200)
    assert _visible(page) == 30


@pytest.mark.browser
def test_radio_narrows_to_one_value(page):
    page.check(".glyphx-controls input[type=radio][value='Gold']")
    page.wait_for_timeout(200)
    assert _visible(page) == 20


@pytest.mark.browser
def test_radio_has_an_all_option_to_get_back(page):
    """Without it a radio group is a one-way trip."""
    page.check(".glyphx-controls input[type=radio][value='Gold']")
    page.wait_for_timeout(150)
    page.check(".glyphx-controls input[type=radio][value='All']")
    page.wait_for_timeout(200)
    assert _visible(page) == 40


@pytest.mark.browser
def test_search_filters_by_substring(page):
    page.fill(".glyphx-controls input[type=search]", "Cust1")
    page.wait_for_timeout(250)
    assert _visible(page) == 10          # Cust10 through Cust19


@pytest.mark.browser
def test_filters_combine_with_and(page):
    """Cust1* that are Gold and not North: indices 10, 14 and 18."""
    page.uncheck(".glyphx-controls input[type=checkbox][value='North']")
    page.check(".glyphx-controls input[type=radio][value='Gold']")
    page.fill(".glyphx-controls input[type=search]", "Cust1")
    page.wait_for_timeout(300)
    assert _visible(page) == 3


@pytest.mark.browser
def test_reset_button_clears_every_filter(page):
    page.uncheck(".glyphx-controls input[type=checkbox][value='North']")
    page.check(".glyphx-controls input[type=radio][value='Gold']")
    page.fill(".glyphx-controls input[type=search]", "Cust1")
    page.wait_for_timeout(250)
    page.click(".glyphx-controls button")
    page.wait_for_timeout(250)

    assert _visible(page) == 40
    assert page.eval_on_selector(".glyphx-controls input[type=search]", "e => e.value") == ""
    assert page.eval_on_selector(
        ".glyphx-controls input[type=radio][value='All']", "e => e.checked")


@pytest.mark.browser
def test_running_count_is_announced(page):
    page.uncheck(".glyphx-controls input[type=checkbox][value='North']")
    page.wait_for_timeout(200)
    count = page.query_selector(".glyphx-controls-count")
    assert "30 of 40" in count.text_content()
    assert count.get_attribute("aria-live") == "polite"


@pytest.mark.browser
def test_panel_sits_beside_the_chart(page):
    svg = page.eval_on_selector("svg[data-glyphx]", "e => e.getBoundingClientRect()")
    panel = page.eval_on_selector(".glyphx-controls", "e => e.getBoundingClientRect()")
    assert panel["left"] >= svg["right"] - 1


@pytest.mark.browser
@pytest.mark.parametrize("page", [dict(search="customer", reset=False)], indirect=True)
def test_reset_button_can_be_omitted(page):
    assert page.query_selector(".glyphx-controls button") is None


@pytest.mark.browser
@pytest.mark.parametrize("page", [dict(checkboxes="region",
                                       labels={"checkboxes": "Sales region"})],
                         indirect=True)
def test_labels_override_the_field_name(page):
    assert "Sales region" in page.eval_on_selector(".glyphx-controls", "e => e.innerText")
