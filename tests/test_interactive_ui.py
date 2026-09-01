"""
The interactive toolbar and gesture bindings, as a user meets them.

These are browser tests because the failures they guard against are all
things that look fine in the markup: literal placeholder tokens rendered as
button labels, two scripts writing the same hint line, and two handlers
claiming the same gesture.
"""

import pytest

from glyphx import Figure

pytestmark = pytest.mark.browser


@pytest.fixture
def chart(tmp_path):
    path = tmp_path / "chart.html"
    Figure(auto_display=False).bar(["a", "b", "c"], [1.0, 2.0, 3.0]).share(str(path))
    return path


@pytest.fixture
def page(chart):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 900, "height": 420})
        pg.goto(chart.as_uri())
        pg.wait_for_timeout(400)
        yield pg
        browser.close()


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def test_no_placeholder_tokens_reach_the_user(page):
    """The Share button read "[hex] Share" and the inspector "[chart] Data
    Point" -- icon placeholders that were never filled in."""
    body = page.eval_on_selector("body", "e => e.innerText")
    for token in ("[hex]", "[chart]", "[keyboard]"):
        assert token not in body, f"placeholder {token} visible to the user"


def test_toolbar_buttons_are_plainly_labelled(page):
    labels = page.eval_on_selector_all(".glyphx-btn", "els => els.map(e => e.textContent.trim())")
    assert "Download SVG" in labels
    assert "Download PNG" in labels
    assert not any(label.startswith("v ") for label in labels), \
        f"cryptic single-letter prefix in {labels}"


def test_export_controls_are_not_duplicated(page):
    """export.js injected its own unstyled row above a toolbar that already
    had the same buttons, so every export had two sets of controls."""
    labels = page.eval_on_selector_all("button", "els => els.map(e => e.textContent.trim())")
    for label in ("Download SVG", "Download PNG"):
        assert labels.count(label) == 1, f"{label!r} appears {labels.count(label)} times"


def test_added_format_matches_the_toolbar_styling(page):
    """The JPG button is injected by export.js; it should not look foreign."""
    classes = page.eval_on_selector_all(
        "button", "els => els.map(e => [e.textContent.trim(), e.className])")
    jpg = [c for label, c in classes if "JPG" in label]
    assert jpg and "glyphx-btn" in jpg[0]


# ---------------------------------------------------------------------------
# Discoverability
# ---------------------------------------------------------------------------

def test_hint_names_the_gestures_a_newcomer_needs(page):
    """
    interact.js overwrote the template's hint with one listing only
    highlight, inspect and isolate -- so zoom, pan and brush, the three
    gestures a first-time user reaches for, appeared nowhere on screen.
    """
    hint = page.eval_on_selector(".glyphx-toolbar span", "e => e.textContent").lower()
    assert "zoom" in hint
    assert "pan" in hint
    assert "shortcuts" in hint


def test_hint_reads_as_instructions_not_configuration(page):
    hint = page.eval_on_selector(".glyphx-toolbar span", "e => e.textContent")
    assert "=" not in hint, f"key=value syntax in user-facing hint: {hint!r}"


# ---------------------------------------------------------------------------
# Gestures
# ---------------------------------------------------------------------------

def test_scroll_zooms_the_chart(page):
    before = page.eval_on_selector("svg[data-glyphx]", "e => e.getAttribute('viewBox')")
    page.mouse.move(400, 300)
    page.mouse.wheel(0, -300)
    page.wait_for_timeout(200)
    after = page.eval_on_selector("svg[data-glyphx]", "e => e.getAttribute('viewBox')")
    assert before != after


def test_double_click_on_empty_space_resets_the_view(page):
    svg = "svg[data-glyphx]"
    original = page.eval_on_selector(svg, "e => e.dataset.originalViewBox")
    page.mouse.move(400, 300)
    page.mouse.wheel(0, -300)
    page.wait_for_timeout(200)
    assert page.eval_on_selector(svg, "e => e.getAttribute('viewBox')") != original

    page.mouse.dblclick(120, 350)
    page.wait_for_timeout(250)
    assert page.eval_on_selector(svg, "e => e.getAttribute('viewBox')") == original


def test_double_click_on_a_data_point_does_not_also_reset_the_view(page):
    """
    Both interact.js (isolate series) and zoom.js (reset view) fired on the
    same double-click, so focusing a series snapped the chart back to full
    extent in the same motion. Each gesture now means one thing.
    """
    svg = "svg[data-glyphx]"
    page.mouse.move(400, 300)
    page.mouse.wheel(0, -300)
    page.wait_for_timeout(200)
    zoomed = page.eval_on_selector(svg, "e => e.getAttribute('viewBox')")

    page.dblclick('[data-x="b"]')
    page.wait_for_timeout(250)
    assert page.eval_on_selector(svg, "e => e.getAttribute('viewBox')") == zoomed
