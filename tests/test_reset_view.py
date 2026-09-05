"""
A visible control for returning to the default zoom and position.

Resetting used to be a double-click on empty space and nothing else. There
was no button, and the toolbar hint did not mention it, so a user who zoomed
or panned had no visible way back.
"""

import pytest

from glyphx import Figure

pytestmark = pytest.mark.browser

VALUES = [float((i * 7) % 13) for i in range(1, 21)]


@pytest.fixture
def page(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    path = tmp_path / "reset.html"
    fig = Figure(width=640, height=440, auto_display=False, title="Signal")
    fig.line(list(range(1, 21)), VALUES)
    fig.share(str(path))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 820, "height": 700})
        pg.goto(path.as_uri())
        pg.wait_for_timeout(350)
        yield pg
        browser.close()


BTN = ".glyphx-reset-view"
SVG = "svg[data-glyphx]"


def _shown(page):
    if not page.query_selector(BTN):
        return False
    return page.eval_on_selector(BTN, "e => e.style.display !== 'none'")


def _view(page):
    return page.eval_on_selector(SVG, "e => e.getAttribute('viewBox')")


def _original(page):
    return page.eval_on_selector(SVG, "e => e.dataset.originalViewBox")


def _zoom(page, steps=3):
    page.mouse.move(400, 350)
    for _ in range(steps):
        page.mouse.wheel(0, -200)
        page.wait_for_timeout(60)


def _pan(page):
    page.mouse.move(400, 350)
    page.mouse.down()
    page.mouse.move(500, 420)
    page.mouse.up()
    page.wait_for_timeout(200)


# ---------------------------------------------------------------------------
# The button appears only when it is useful
# ---------------------------------------------------------------------------

def test_button_is_hidden_until_the_view_moves(page):
    assert not _shown(page)


def test_button_appears_after_zooming(page):
    _zoom(page)
    assert _shown(page)


def test_button_appears_after_panning(page):
    _pan(page)
    assert _view(page) != _original(page)
    assert _shown(page)


def test_button_hides_again_after_reset(page):
    _zoom(page)
    page.click(BTN)
    page.wait_for_timeout(300)
    assert not _shown(page)


# ---------------------------------------------------------------------------
# What it restores
# ---------------------------------------------------------------------------

def test_reset_restores_both_zoom_and_position(page):
    original = _original(page)
    _zoom(page)
    _pan(page)
    assert _view(page) != original

    page.click(BTN)
    page.wait_for_timeout(300)
    assert _view(page) == original


def test_reset_restores_the_axis_labels(page):
    def ticks():
        return page.eval_on_selector_all(
            ".glyphx-tick",
            "els => els.map(e => [e.textContent, e.getAttribute('x'), e.style.display])")

    before = ticks()
    _zoom(page)
    assert ticks() != before

    page.click(BTN)
    page.wait_for_timeout(300)
    assert ticks() == before


def test_zooming_after_reset_starts_from_the_restored_view(page):
    """
    resetAll() runs outside the per-chart closure that tracks the current
    viewBox. Without pushing the restored value back in, the next scroll
    would carry on from the pre-reset zoom and the chart would jump.
    """
    _zoom(page, steps=4)
    deep_width = float(_view(page).split()[2])
    page.click(BTN)
    page.wait_for_timeout(250)

    page.mouse.move(400, 350)
    page.mouse.wheel(0, -200)
    page.wait_for_timeout(200)
    assert float(_view(page).split()[2]) > deep_width


def test_double_click_still_resets(page):
    """The button is an addition, not a replacement for the gesture."""
    original = _original(page)
    _zoom(page)
    box = page.eval_on_selector(SVG, "e => e.getBoundingClientRect()")
    page.mouse.dblclick(box["x"] + box["width"] - 30, box["y"] + 30)
    page.wait_for_timeout(300)
    assert _view(page) == original


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

def test_button_matches_the_other_toolbar_controls(page):
    _zoom(page)
    cls = page.eval_on_selector(BTN, "e => e.className")
    assert "glyphx-btn" in cls


def test_button_is_labelled_in_plain_words(page):
    _zoom(page)
    assert page.eval_on_selector(BTN, "e => e.textContent.trim()") == "Reset view"
    assert page.eval_on_selector(BTN, "e => e.title")


def test_hint_mentions_how_to_reset(page):
    hint = page.eval_on_selector(".glyphx-toolbar span", "e => e.textContent").lower()
    assert "reset" in hint
