"""
Browser rendering tests.

Structural SVG assertions catch malformed output, but they cannot catch a
chart that parses fine and still renders wrong -- or an exported page whose
JavaScript dies on load.  These tests put every chart type through Chromium.

That distinction is not hypothetical.  Two shipped assets contained their own
``<script>`` tags, so the browser closed the block early and every script
after it died; tooltips, zoom, brushing, and keyboard accessibility were all
inert in exported HTML while every Python-side test passed.  Only a browser
sees that.

Requires playwright::

    pip install 'glyphx[browser]' && playwright install chromium

Skipped when playwright or its browser binary is unavailable, so the suite
still runs everywhere.
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_all_chart_types import CHART_FACTORIES, SERIES_3D_FACTORIES  # noqa: E402

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is not installed"
)

from glyphx.utils import make_shareable_html  # noqa: E402

CANVAS_TOLERANCE = 1.0   # sub-pixel rounding in getBBox

# Browser tests take ~35s. Deselect with `pytest -m "not browser"`.
pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def browser():
    """A single Chromium instance shared by every test in this module."""
    try:
        with playwright_api.sync_playwright() as pw:
            try:
                instance = pw.chromium.launch()
            except Exception as exc:       # browser binary not downloaded
                pytest.skip(f"chromium unavailable: {exc}")
            yield instance
            instance.close()
    except Exception as exc:
        pytest.skip(f"playwright unavailable: {exc}")


def _load(browser, html: str, tmp_path, name: str):
    """Render ``html`` in a fresh page and return (page, errors)."""
    path = tmp_path / f"{name}.html"
    path.write_text(html, encoding="utf-8")

    page = browser.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "console",
        lambda m: errors.append(m.text) if m.type == "error" else None,
    )
    page.goto(pathlib.Path(path).as_uri())
    page.wait_for_timeout(300)
    return page, errors


MEASURE_JS = """
() => {
  const svg = document.querySelector('svg[data-glyphx]');
  if (!svg) return null;
  const vb = svg.viewBox.baseVal;
  const base = svg.getBoundingClientRect();

  // Measure with getBoundingClientRect, not getBBox: getBBox ignores an
  // element's own transform, so a rotated Y-axis label reports its
  // pre-rotation box and looks like it hangs off the left edge.  Client
  // rects are in screen pixels and the template scales the SVG to its
  // container, so convert back into viewBox user units before comparing.
  const sx = vb.width / base.width, sy = vb.height / base.height;
  const box = el => {
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) return null;
    return {x: (r.left - base.left) * sx, y: (r.top - base.top) * sy,
            w: r.width * sx, h: r.height * sy};
  };

  const overflowing = [];
  svg.querySelectorAll('*').forEach(el => {
    const b = box(el);
    if (!b) return;
    if (b.x < -1 || b.y < -1 ||
        b.x + b.w > vb.width + 1 || b.y + b.h > vb.height + 1) {
      overflowing.push(el.tagName + '.' + (el.getAttribute('class') || '') +
        ' [' + [b.x, b.y, b.w, b.h].map(v => Math.round(v)).join(',') + ']');
    }
  });

  const drawn = svg.querySelectorAll(
    'rect,circle,path,polyline,polygon,line,text,ellipse').length;
  return {width: vb.width, height: vb.height, drawn, overflowing};
}
"""


@pytest.mark.parametrize("chart", sorted(CHART_FACTORIES))
def test_chart_renders_in_chromium_without_errors(browser, tmp_path, chart):
    html = make_shareable_html(CHART_FACTORIES[chart](), title=chart)
    page, errors = _load(browser, html, tmp_path, chart)
    try:
        assert errors == [], f"{chart}: JavaScript errors on load: {errors}"
        measured = page.evaluate(MEASURE_JS)
        assert measured is not None, f"{chart}: no GlyphX SVG in the document"
        assert measured["drawn"] > 0, f"{chart}: rendered an empty canvas"
    finally:
        page.close()


@pytest.mark.parametrize("chart", sorted(CHART_FACTORIES))
def test_chart_stays_inside_its_canvas(browser, tmp_path, chart):
    """
    Content drawn outside the viewBox is clipped and invisible.

    Two charts failed this when it was first written: count plots drew bars
    from a baseline outside the domain, and Gantt charts drew a month
    gridline from before their own padded start date.
    """
    html = make_shareable_html(CHART_FACTORIES[chart](), title=chart)
    page, _ = _load(browser, html, tmp_path, chart)
    try:
        measured = page.evaluate(MEASURE_JS)
        assert measured["overflowing"] == [], (
            f"{chart}: {len(measured['overflowing'])} element(s) outside the "
            f"{measured['width']}x{measured['height']} canvas: "
            f"{measured['overflowing'][:4]}"
        )
    finally:
        page.close()


def test_legend_toggle_hides_and_restores_a_series(browser, tmp_path):
    import re

    from glyphx import Figure

    fig = (
        Figure(auto_display=False)
        .line([1, 2, 3], [1.0, 2.0, 3.0], label="alpha")
        .line([1, 2, 3], [3.0, 2.0, 1.0], label="beta")
    )
    svg = fig.render_svg()
    targets = sorted(set(re.findall(r'data-target="([^"]+)"', svg)))
    assert len(targets) == 2

    page, errors = _load(browser, make_shareable_html(svg), tmp_path, "legend")
    try:
        assert errors == []

        def visible(css_class: str) -> int:
            return page.eval_on_selector_all(
                f'[class~="{css_class}"]:not([data-target])',
                "els => els.filter(e => e.getAttribute('visibility') !== 'hidden').length",
            )

        first, second = targets
        before = visible(first)
        assert before > 0

        page.click(f'.legend-label[data-target="{first}"]')
        page.wait_for_timeout(120)
        assert visible(first) == 0, "click did not hide the series"
        assert visible(second) > 0, "the other series must be untouched"
        assert page.get_attribute(
            f'.legend-label[data-target="{first}"]', "aria-pressed"
        ) == "false"

        page.click(f'.legend-label[data-target="{first}"]')
        page.wait_for_timeout(120)
        assert visible(first) == before, "second click did not restore the series"
    finally:
        page.close()


@pytest.mark.parametrize("key", ["Enter", " "])
def test_legend_toggle_works_from_the_keyboard(browser, tmp_path, key):
    import re

    from glyphx import Figure

    fig = Figure(auto_display=False).line([1, 2, 3], [1.0, 2.0, 3.0], label="alpha")
    svg = fig.render_svg()
    target = re.search(r'data-target="([^"]+)"', svg).group(1)

    page, _ = _load(browser, make_shareable_html(svg), tmp_path, f"kbd{key.strip()}")
    try:
        selector = f'.legend-icon[data-target="{target}"]'
        page.focus(selector)
        page.keyboard.press(key)
        page.wait_for_timeout(120)
        hidden = page.eval_on_selector_all(
            f'[class~="{target}"]:not([data-target])',
            "els => els.every(e => e.getAttribute('visibility') === 'hidden')",
        )
        assert hidden, f"{key!r} did not toggle the series"
    finally:
        page.close()


def test_exported_page_has_no_javascript_errors(browser, tmp_path):
    """Regression: nested <script> tags in assets killed every script."""
    from glyphx import Figure

    fig = Figure(auto_display=False).scatter([1, 2, 3], [1.0, 2.0, 3.0], label="pts")
    page, errors = _load(browser, make_shareable_html(fig.render_svg()),
                         tmp_path, "scripts")
    try:
        assert errors == [], f"exported page raised: {errors}"
    finally:
        page.close()


@pytest.mark.parametrize("chart", sorted(SERIES_3D_FACTORIES))
def test_3d_chart_page_loads(browser, tmp_path, chart):
    """
    3D charts need three.js from a CDN.

    Offline, the page must show the fallback notice rather than a blank
    white rectangle.  Online, three.js must load and initialise -- which
    also proves the Subresource Integrity hash matches what the CDN serves,
    since a mismatch makes the browser refuse the script entirely.
    """
    import glyphx

    fig = glyphx.Figure3D()
    fig.add(SERIES_3D_FACTORIES[chart]())
    page, _ = _load(browser, fig.render_html(), tmp_path, chart)
    try:
        page.wait_for_timeout(1500)
        loaded = page.evaluate("() => typeof THREE !== 'undefined'")
        if loaded:
            assert page.evaluate("() => !!document.querySelector('canvas')"), (
                f"{chart}: three.js loaded but no canvas was created"
            )
        else:
            assert page.evaluate(
                "() => document.body.innerText.includes('not be loaded')"
            ), f"{chart}: three.js unavailable and no fallback notice shown"
    finally:
        page.close()


# ---------------------------------------------------------------------------
# Element collision
# ---------------------------------------------------------------------------

#: Charts that draw their labels directly on top of their marks by design --
#: slice labels on a pie, axis values over the lines of a parallel-coordinates
#: plot.  Overlap there is the intended layout, not a defect.
LABELS_ON_MARKS = {
    "pie", "donut", "sunburst", "treemap", "heatmap",
    "parallel_coords", "gantt", "waterfall",
}

OVERLAP_JS = """
() => {
  const svg = document.querySelector('svg[data-glyphx]');
  if (!svg) return null;
  const all = [...svg.querySelectorAll('*')];
  const rect = el => {
    try {
      const r = el.getBoundingClientRect();
      return (r.width || r.height) ? r : null;
    } catch (e) { return null; }
  };
  const overlaps = (a, b) => {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return w > 0.5 && h > 0.5;
  };
  const fontSize = el => parseFloat(getComputedStyle(el).fontSize) || 0;

  const texts = all.filter(e => e.tagName === 'text' && e.textContent.trim());
  const legendEls = all.filter(
    e => /legend-(icon|label)/.test(e.getAttribute('class') || ''));
  const marks = all.filter(
    e => /series-|glyphx-point/.test(e.getAttribute('class') || ''));

  const maxFs = Math.max(0, ...texts.map(fontSize));
  const title = texts.find(t => fontSize(t) === maxFs && maxFs >= 16);
  const ticks = texts.filter(t => fontSize(t) <= 11.5 && !legendEls.includes(t));

  const markRects = marks.map(rect).filter(Boolean);
  const issues = [];

  // The legend must never sit on top of the data it describes.
  let n = 0;
  legendEls.map(rect).filter(Boolean).forEach(
    l => markRects.forEach(m => { if (overlaps(l, m)) n++; }));
  if (n) issues.push('legend overlaps ' + n + ' data mark(s)');

  // The title must not collide with the plot or the tick labels.
  if (title) {
    const tr = rect(title);
    let t = 0;
    markRects.forEach(m => { if (overlaps(tr, m)) t++; });
    ticks.forEach(k => { const r = rect(k); if (r && overlaps(tr, r)) t++; });
    if (t) issues.push('title overlaps ' + t + ' element(s)');
  }

  // Tick labels must not run into each other.
  const collided = [];
  for (let i = 0; i < ticks.length; i++) {
    for (let j = i + 1; j < ticks.length; j++) {
      const a = rect(ticks[i]), b = rect(ticks[j]);
      if (a && b && overlaps(a, b))
        collided.push(ticks[i].textContent + '/' + ticks[j].textContent);
    }
  }
  if (collided.length)
    issues.push('tick labels collide: ' + collided.slice(0, 3).join(', '));

  return {issues, ticksOverMarks: ticks.filter(k => {
    const r = rect(k);
    return r && markRects.some(m => overlaps(r, m));
  }).length};
}
"""


@pytest.mark.parametrize("chart", sorted(CHART_FACTORIES))
def test_chart_elements_do_not_collide(browser, tmp_path, chart):
    """
    Titles, legends, and tick labels must not sit on top of each other.

    Found two real defects when written: histogram bars were centred on bin
    centres while the X domain covered only those centres, so half of the
    outermost bar hung over the Y tick labels; and bump charts drew the "#N"
    rank label at the same x as the first series label.
    """
    html = make_shareable_html(CHART_FACTORIES[chart](), title=chart)
    page, _ = _load(browser, html, tmp_path, f"overlap-{chart}")
    try:
        found = page.evaluate(OVERLAP_JS)
        assert found is not None
        assert found["issues"] == [], f"{chart}: {found['issues']}"
        if chart not in LABELS_ON_MARKS:
            assert found["ticksOverMarks"] == 0, (
                f"{chart}: {found['ticksOverMarks']} tick label(s) sit on the data"
            )
    finally:
        page.close()


@pytest.mark.parametrize("position", [
    "top-right", "top-left", "bottom-right", "bottom-left",
    "top", "bottom", "left", "right", "outside-right",
])
def test_legend_never_covers_the_data(browser, tmp_path, position):
    """Every legend position, with a long title and both axis labels set."""
    from glyphx import Figure

    fig = Figure(auto_display=False, legend=position,
                 title="Quarterly Revenue by Region - FY2024")
    fig.line([1, 2, 3, 4, 5], [2.0, 4.0, 3.0, 5.0, 4.5], label="Northwest")
    fig.line([1, 2, 3, 4, 5], [5.0, 3.0, 4.0, 2.0, 3.5], label="Southeast")
    fig.set_xlabel("Fiscal Month")
    fig.set_ylabel("Revenue (millions USD)")

    page, errors = _load(browser, make_shareable_html(fig.render_svg()),
                         tmp_path, f"legend-{position}")
    try:
        assert errors == []
        found = page.evaluate(OVERLAP_JS)
        assert found["issues"] == [], f"legend={position}: {found['issues']}"
        measured = page.evaluate(MEASURE_JS)
        assert measured["overflowing"] == [], (
            f"legend={position}: {measured['overflowing']}"
        )
    finally:
        page.close()


def test_long_labels_do_not_break_the_bump_chart_gutter(browser, tmp_path):
    """The left gutter has to fit the rank labels and the longest name."""
    import glyphx

    fig = glyphx.Figure(auto_display=False).add(
        glyphx.BumpChartSeries(
            ["Q1", "Q2", "Q3"],
            {"Northwest Region": [1, 2, 3],
             "Southeast Division": [3, 1, 2],
             "Central": [2, 3, 1]},
        )
    )
    page, _ = _load(browser, make_shareable_html(fig.render_svg()),
                    tmp_path, "bump-long")
    try:
        assert page.evaluate(OVERLAP_JS)["issues"] == []
        assert page.evaluate(MEASURE_JS)["overflowing"] == []
    finally:
        page.close()


# ---------------------------------------------------------------------------
# Standalone .svg files
# ---------------------------------------------------------------------------

def test_saved_svg_file_opens_in_the_browser(browser, tmp_path):
    """
    A saved .svg must render when opened directly, not as an XML error page.

    Every file examples.py produced failed this: the titles contain em
    dashes, and Path.write_text() with no encoding used the platform codec,
    writing 0x97 instead of UTF-8.  Chromium reported
    "error on line 1 at column 313: Encoding error" and drew nothing.
    """
    from glyphx import Figure

    fig = Figure(auto_display=False, title="Market Share 2024  —  µ ± σ  °C")
    fig.line([1, 2, 3], [1.0, 2.0, 3.0], label="Revenue")

    out = tmp_path / "chart.svg"
    fig.save(str(out))

    page = browser.new_page()
    try:
        page.goto(out.resolve().as_uri())
        page.wait_for_timeout(250)

        assert not page.evaluate(
            "() => document.body && "
            "document.body.innerText.includes('This page contains the following errors')"
        ), "browser reported a parse error for the saved SVG"

        drawn = page.evaluate(
            "() => {const s = document.querySelector('svg'); "
            "return s ? s.querySelectorAll('*').length : 0;}"
        )
        assert drawn > 5, f"saved SVG rendered only {drawn} elements"
    finally:
        page.close()


def test_saved_svg_preserves_non_ascii_title_text(browser, tmp_path):
    from glyphx import Figure

    title = "Résumé — 温度 °C"
    fig = Figure(auto_display=False, title=title)
    fig.line([1, 2], [1.0, 2.0])
    out = tmp_path / "unicode.svg"
    fig.save(str(out))

    page = browser.new_page()
    try:
        page.goto(out.resolve().as_uri())
        page.wait_for_timeout(250)
        rendered = page.evaluate(
            "() => [...document.querySelectorAll('text')].map(t => t.textContent).join('|')"
        )
        assert "Résumé" in rendered and "温度" in rendered
    finally:
        page.close()
