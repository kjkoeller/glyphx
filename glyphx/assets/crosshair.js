/**
 * GlyphX Synchronized Crosshair
 *
 * Move the mouse over any chart and a vertical crosshair line appears
 * on ALL glyphx charts simultaneously, positioned at the same relative
 * x-fraction of each chart's plot area.
 *
 * A shared tooltip at the top of each chart shows the x-axis value and
 * the y-value of the nearest data point in that chart.
 */
(function () {
  'use strict';

  const CHARTS_SEL = 'svg[data-glyphx]';

  // ── Helpers ─────────────────────────────────────────────────────────────

  /** Convert a MouseEvent to SVG-local coordinates. */
  function svgLocalX(svg, e) {
    const rect = svg.getBoundingClientRect();
    const vb   = svg.viewBox.baseVal;
    return (e.clientX - rect.left) * (vb.width / rect.width);
  }

  /** Return the plot-area x-fraction [0, 1] for a pixel x-position. */
  function xFraction(svg, localX) {
    const vb  = svg.viewBox.baseVal;
    // Use padding stored on SVG (or default 50)
    const pad = parseFloat(svg.dataset.padding || '50');
    const pw  = vb.width - 2 * pad;
    return Math.max(0, Math.min(1, (localX - pad) / pw));
  }

  /** Given a fraction, return the pixel x position in the plot area. */
  function fractionToX(svg, frac) {
    const vb  = svg.viewBox.baseVal;
    const pad = parseFloat(svg.dataset.padding || '50');
    return pad + frac * (vb.width - 2 * pad);
  }

  /** Find the .glyphx-point nearest to a given x-fraction on one chart. */
  function nearestPoint(svg, frac) {
    const vb  = svg.viewBox.baseVal;
    const pad = parseFloat(svg.dataset.padding || '50');
    const px  = pad + frac * (vb.width - 2 * pad);
    let best = null, bestDist = Infinity;

    svg.querySelectorAll('.glyphx-point').forEach(el => {
      let elX;
      if (el.tagName === 'circle') {
        elX = parseFloat(el.getAttribute('cx'));
      } else {
        const x = parseFloat(el.getAttribute('x') || '0');
        const w = parseFloat(el.getAttribute('width') || '0');
        elX = x + w / 2;
      }
      const dist = Math.abs(elX - px);
      if (dist < bestDist) { bestDist = dist; best = el; }
    });
    return best;
  }

  // ── Per-chart crosshair line ──────────────────────────────────────────────

  function ensureCrosshair(svg) {
    let line = svg.querySelector('.glyphx-crosshair');
    if (line) return line;
    line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('class', 'glyphx-crosshair');
    line.setAttribute('stroke', 'rgba(100,100,100,0.55)');
    line.setAttribute('stroke-width', '1');
    line.setAttribute('stroke-dasharray', '4,3');
    line.style.display       = 'none';
    line.style.pointerEvents = 'none';
    svg.appendChild(line);
    return line;
  }

  function showCrosshair(svg, frac) {
    const vb  = svg.viewBox.baseVal;
    const pad = parseFloat(svg.dataset.padding || '50');
    const px  = fractionToX(svg, frac);
    const line = ensureCrosshair(svg);

    line.setAttribute('x1', px);
    line.setAttribute('x2', px);
    line.setAttribute('y1', pad);
    line.setAttribute('y2', vb.height - pad);
    line.style.display = '';
  }

  function hideCrosshair(svg) {
    const line = svg.querySelector('.glyphx-crosshair');
    if (line) line.style.display = 'none';
  }

  // ── Global tooltip overlay ────────────────────────────────────────────────

  function updateTip(svg, frac) {
    const tip = document.getElementById('glyphx-tooltip');
    if (!tip) return;

    const pt = nearestPoint(svg, frac);
    if (!pt) { tip.style.display = 'none'; return; }

    const x   = pt.getAttribute('data-x');
    const y   = pt.getAttribute('data-y');
    const lbl = pt.getAttribute('data-label');

    let html = '';
    if (lbl) html += `<div class="tt-label">${lbl}</div>`;
    if (x !== null) html += `<div class="tt-row">x: ${x}</div>`;
    if (y !== null) html += `<div class="tt-row">y: ${y}</div>`;
    tip.innerHTML = html;
    tip.style.display = html ? 'block' : 'none';
  }

  // ── Wiring ────────────────────────────────────────────────────────────────

  function init() {
    const charts = Array.from(document.querySelectorAll(CHARTS_SEL));
    if (charts.length < 1) return;

    charts.forEach(svg => {
      svg.addEventListener('mousemove', e => {
        // Crosshair is only in the plot area
        const localX = svgLocalX(svg, e);
        const frac   = xFraction(svg, localX);
        if (frac < 0 || frac > 1) {
          charts.forEach(hideCrosshair);
          return;
        }
        // Sync to all charts
        charts.forEach(s => showCrosshair(s, frac));
        updateTip(svg, frac);

        // Position tooltip near cursor
        const tip = document.getElementById('glyphx-tooltip');
        if (tip) {
          tip.style.left = (e.clientX + 14) + 'px';
          tip.style.top  = (e.clientY + 14) + 'px';
        }
      });

      svg.addEventListener('mouseleave', () => {
        charts.forEach(hideCrosshair);
        const tip = document.getElementById('glyphx-tooltip');
        if (tip) tip.style.display = 'none';
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
