"""
Touch panning and pinch zoom.

Only mouse events were bound, so on a phone or tablet the chart was a static
image -- while still advertising ``cursor: grab``, promising a drag the
device could not perform.
"""

import pytest

from glyphx import Figure

pytestmark = pytest.mark.browser

VALUES = [float((i * 7) % 13) for i in range(1, 21)]
SVG = "svg[data-glyphx]"


@pytest.fixture
def mobile(tmp_path):
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    path = tmp_path / "touch.html"
    fig = Figure(width=640, height=440, auto_display=False, title="Signal")
    fig.line(list(range(1, 21)), VALUES)
    fig.share(str(path))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 390, "height": 780},
                              has_touch=True, is_mobile=True)
        pg.goto(path.as_uri())
        pg.wait_for_timeout(350)
        yield pg
        browser.close()


def _view(page):
    return [float(v) for v in page.eval_on_selector(SVG, "e => e.getAttribute('viewBox')").split()]


def _touch(page, points, kind="touchStart"):
    client = page.context.new_cdp_session(page)
    client.send("Input.dispatchTouchEvent",
                {"type": kind, "touchPoints": [{"x": x, "y": y} for x, y in points]})
    return client


def _centre(page):
    box = page.eval_on_selector(SVG, "e => e.getBoundingClientRect()")
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


# ---------------------------------------------------------------------------
# Gestures
# ---------------------------------------------------------------------------

def test_one_finger_pans(mobile):
    before = _view(mobile)
    cx, cy = _centre(mobile)
    client = mobile.context.new_cdp_session(mobile)
    client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": cx, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": cx - 60, "y": cy - 40}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    mobile.wait_for_timeout(250)

    after = _view(mobile)
    assert (after[0], after[1]) != (before[0], before[1]), "chart did not pan"
    assert after[2] == before[2], "panning must not change the zoom level"


def test_two_finger_pinch_zooms_in(mobile):
    before = _view(mobile)
    cx, cy = _centre(mobile)
    client = mobile.context.new_cdp_session(mobile)
    client.send("Input.dispatchTouchEvent", {"type": "touchStart",
        "touchPoints": [{"x": cx - 20, "y": cy}, {"x": cx + 20, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchMove",
        "touchPoints": [{"x": cx - 100, "y": cy}, {"x": cx + 100, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    mobile.wait_for_timeout(250)

    assert _view(mobile)[2] < before[2], "pinching outward should zoom in"


def test_pinching_together_zooms_out(mobile):
    cx, cy = _centre(mobile)
    client = mobile.context.new_cdp_session(mobile)
    client.send("Input.dispatchTouchEvent", {"type": "touchStart",
        "touchPoints": [{"x": cx - 100, "y": cy}, {"x": cx + 100, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchMove",
        "touchPoints": [{"x": cx - 20, "y": cy}, {"x": cx + 20, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    mobile.wait_for_timeout(250)

    assert _view(mobile)[2] > 640, "pinching inward should zoom out"


# ---------------------------------------------------------------------------
# Touch composes with the rest of the toolbar
# ---------------------------------------------------------------------------

def test_axis_labels_are_redrawn_after_a_pinch(mobile):
    cx, cy = _centre(mobile)
    client = mobile.context.new_cdp_session(mobile)
    client.send("Input.dispatchTouchEvent", {"type": "touchStart",
        "touchPoints": [{"x": cx - 20, "y": cy}, {"x": cx + 20, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchMove",
        "touchPoints": [{"x": cx - 120, "y": cy}, {"x": cx + 120, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    mobile.wait_for_timeout(250)

    visible = mobile.eval_on_selector_all(
        ".glyphx-tick", "els => els.filter(e => e.style.display !== 'none').length")
    assert visible >= 4, "a pinched chart lost its scale"


def test_reset_button_appears_after_a_touch_gesture(mobile):
    cx, cy = _centre(mobile)
    client = mobile.context.new_cdp_session(mobile)
    client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": cx, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": cx - 50, "y": cy}]})
    client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    mobile.wait_for_timeout(250)

    assert mobile.eval_on_selector(".glyphx-reset-view", "e => e.style.display !== 'none'")


def test_browser_gestures_are_claimed_by_the_chart(mobile):
    """Without touch-action: none the page scrolls instead and touchmove
    never fires often enough to be usable."""
    assert mobile.eval_on_selector(SVG, "e => getComputedStyle(e).touchAction") == "none"


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def test_toolbar_does_not_overflow_a_phone_screen(mobile):
    """The button row is wider than a phone; without wrapping the leftmost
    controls are cut off with no way to reach them."""
    overflowing = mobile.evaluate("""() => {
        const tb = document.querySelector('.glyphx-toolbar');
        const r = tb.getBoundingClientRect();
        return Array.from(tb.querySelectorAll('.glyphx-btn'))
          .filter(b => b.style.display !== 'none')
          .filter(b => { const x = b.getBoundingClientRect();
                         return x.left < r.left - 1 || x.right > r.right + 1; })
          .map(b => b.textContent.trim());
    }""")
    assert overflowing == [], f"cut off on a phone: {overflowing}"
