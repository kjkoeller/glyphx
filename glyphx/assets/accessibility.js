/**
 * GlyphX Keyboard Accessibility
 *
 * Makes every .glyphx-point element fully keyboard-navigable:
 *
 *   Tab / Shift-Tab  — move focus through data points
 *   Enter / Space    — trigger the hover tooltip on the focused point
 *   Arrow keys       — move to the next/previous point within a series
 *   Escape           — dismiss tooltip and blur the active point
 *
 * Screen readers receive the aria-label built from data-x / data-y
 * attributes, so each point announces itself correctly.
 */
(function () {
  'use strict';

  const POINT_SEL = '.glyphx-point';

  // ── Build aria-label for a data point element ───────────────────────────
  function buildAriaLabel(el) {
    const x   = el.getAttribute('data-x');
    const y   = el.getAttribute('data-y');
    const lbl = el.getAttribute('data-label');
    const val = el.getAttribute('data-value');
    const q1  = el.getAttribute('data-q1');
    const q2  = el.getAttribute('data-q2');
    const q3  = el.getAttribute('data-q3');

    const parts = [];
    if (lbl) parts.push(lbl);
    if (q1)  parts.push(`Q1 ${(+q1).toFixed(2)}, median ${(+q2).toFixed(2)}, Q3 ${(+q3).toFixed(2)}`);
    else {
      if (x !== null) parts.push(`x: ${x}`);
      if (y !== null) parts.push(`y: ${y}`);
      if (val)        parts.push(`value: ${val}`);
    }
    return parts.join(', ') || 'Data point';
  }

  // ── Show / hide the shared GlyphX tooltip ───────────────────────────────
  function showTip(el) {
    const tip = document.getElementById('glyphx-tooltip');
    if (!tip) return;
    const lbl = el.getAttribute('data-label');
    const x   = el.getAttribute('data-x');
    const y   = el.getAttribute('data-y');
    const val = el.getAttribute('data-value');
    const q1  = el.getAttribute('data-q1');
    const q2  = el.getAttribute('data-q2');
    const q3  = el.getAttribute('data-q3');

    let html = '';
    if (lbl) html += `<div class="tt-label">${lbl}</div>`;
    if (q1)  html += `<div class="tt-row">Q1: ${(+q1).toFixed(3)}</div>
                      <div class="tt-row">Median: ${(+q2).toFixed(3)}</div>
                      <div class="tt-row">Q3: ${(+q3).toFixed(3)}</div>`;
    else {
      if (x !== null) html += `<div class="tt-row">x: ${x}</div>`;
      if (y !== null) html += `<div class="tt-row">y: ${y}</div>`;
      if (val)        html += `<div class="tt-row">value: ${val}</div>`;
    }

    tip.innerHTML = html || buildAriaLabel(el);
    tip.style.display = 'block';

    // Position near the focused element
    try {
      const rect = el.getBoundingClientRect();
      tip.style.left = (rect.right + 8) + 'px';
      tip.style.top  = (rect.top  - 4) + 'px';
    } catch (_) {}
  }

  function hideTip() {
    const tip = document.getElementById('glyphx-tooltip');
    if (tip) tip.style.display = 'none';
  }

  // ── Wire a single point element ─────────────────────────────────────────
  function wirePoint(el, allPoints) {
    // Stamp aria-label so screen readers announce values
    if (!el.getAttribute('aria-label')) {
      el.setAttribute('aria-label', buildAriaLabel(el));
    }

    el.addEventListener('focus', () => showTip(el));
    el.addEventListener('blur',  hideTip);

    el.addEventListener('keydown', e => {
      const idx = allPoints.indexOf(el);

      switch (e.key) {
        case 'Enter':
        case ' ':
          showTip(el);
          e.preventDefault();
          break;

        case 'ArrowRight':
        case 'ArrowDown': {
          e.preventDefault();
          const next = allPoints[idx + 1];
          if (next) next.focus();
          break;
        }

        case 'ArrowLeft':
        case 'ArrowUp': {
          e.preventDefault();
          const prev = allPoints[idx - 1];
          if (prev) prev.focus();
          break;
        }

        case 'Escape':
          hideTip();
          el.blur();
          break;
      }
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    const allPoints = Array.from(document.querySelectorAll(POINT_SEL));
    allPoints.forEach(el => wirePoint(el, allPoints));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
