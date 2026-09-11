/**
 * GlyphX Linked Brushing
 *
 * Hold Shift + drag on any chart to draw a selection rectangle.
 * All .glyphx-point elements sharing the same data-x values
 * across EVERY chart on the page are highlighted; others dim.
 *
 * Keyboard shortcuts:
 *   Shift + drag  -- draw selection
 *   Escape        -- clear selection
 *   Click outside -- clear selection
 */
(function () {
  'use strict';

  // -- State --------------------------------------------------------------
  let isBrushing = false;
  let startPt    = null;
  let activeSvg  = null;

  // -- Coordinate helper ---------------------------------------------------
  function svgPoint(svg, e) {
    const rect  = svg.getBoundingClientRect();
    const vb    = svg.viewBox.baseVal;
    const sx    = vb.width  / rect.width;
    const sy    = vb.height / rect.height;
    return {
      x: (e.clientX - rect.left) * sx,
      y: (e.clientY - rect.top)  * sy,
    };
  }

  function elementCenter(el) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'circle') {
      return { x: +el.getAttribute('cx'), y: +el.getAttribute('cy') };
    }
    try {
      const b = el.getBBox();
      return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
    } catch (_) { return null; }
  }

  // -- Selection application -----------------------------------------------
  function applySelection(selectedKeys) {
    document.querySelectorAll('.glyphx-point').forEach(el => {
      el.style.transition = 'opacity 0.12s, filter 0.12s';
      if (!selectedKeys || selectedKeys.size === 0) {
        el.style.opacity = '';
        el.style.filter  = '';
      } else {
        const key = el.getAttribute('data-x');
        const hit = key !== null && selectedKeys.has(key);
        el.style.opacity = hit ? '1'  : '0.1';
        el.style.filter  = hit ? '' : 'grayscale(100%)';
      }
    });
  }

  function clearSelection() {
    applySelection(null);
    document.querySelectorAll('.glyphx-brush-hint').forEach(h => {
      h.style.opacity = '0';
    });
    document.querySelectorAll('.glyphx-brush-stats').forEach(b => {
      b.style.opacity = '0';
    });
  }

  // -- Brush rectangle -----------------------------------------------------
  function ensureBrushRect(svg) {
    let r = svg.querySelector('.glyphx-brush-rect');
    if (r) return r;
    r = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    r.setAttribute('class',           'glyphx-brush-rect');
    r.setAttribute('fill',             'rgba(66,153,225,0.12)');
    r.setAttribute('stroke',           '#4299e1');
    r.setAttribute('stroke-width',     '1.5');
    r.setAttribute('stroke-dasharray', '5,3');
    r.setAttribute('rx',               '2');
    r.style.display       = 'none';
    r.style.pointerEvents = 'none';
    svg.appendChild(r);
    return r;
  }

  function updateBrushRect(r, x1, y1, x2, y2) {
    r.setAttribute('x',      Math.min(x1, x2));
    r.setAttribute('y',      Math.min(y1, y2));
    r.setAttribute('width',  Math.abs(x2 - x1));
    r.setAttribute('height', Math.abs(y2 - y1));
    r.style.display = '';
  }

  // -- Hint badge ----------------------------------------------------------
  function ensureHint(svg) {
    const parent = svg.parentElement;
    let hint = parent.querySelector('.glyphx-brush-hint');
    if (hint) return hint;

    if (getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }
    hint = document.createElement('div');
    hint.className = 'glyphx-brush-hint';
    hint.textContent = 'Brush mode: shift and drag to select, Esc to clear';
    Object.assign(hint.style, {
      position:      'absolute',
      top:           '8px',
      left:          '50%',
      transform:     'translateX(-50%)',
      background:    'rgba(66,153,225,0.92)',
      color:         '#fff',
      padding:       '4px 12px',
      borderRadius:  '12px',
      fontSize:      '11px',
      fontFamily:    'system-ui, sans-serif',
      letterSpacing: '0.02em',
      pointerEvents: 'none',
      opacity:       '0',
      transition:    'opacity 0.2s',
      whiteSpace:    'nowrap',
      zIndex:        '99',
      boxShadow:     '0 2px 6px rgba(0,0,0,0.2)',
    });
    parent.appendChild(hint);
    return hint;
  }

  // -- Selection statistics -------------------------------------------------
  //
  // Brushing used to select points and say nothing about them: everything
  // outside faded, and you were left counting dots by eye. The numbers are
  // already in data-y on every element, so summarising them is free.

  // Set when a brush drag finishes, so the click it generates is swallowed
  // before any other handler treats it as a plain click on the chart.
  let suppressNextClick = false;
  document.addEventListener('click', e => {
    if (!suppressNextClick) return;
    suppressNextClick = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);

  function ensureStats(svg) {
    const parent = svg.parentElement;
    let box = parent.querySelector('.glyphx-brush-stats');
    if (box) return box;

    if (getComputedStyle(parent).position === 'static') {
      parent.style.position = 'relative';
    }
    box = document.createElement('div');
    box.className = 'glyphx-brush-stats';
    box.setAttribute('role', 'status');
    box.setAttribute('aria-live', 'polite');
    Object.assign(box.style, {
      position:      'absolute',
      top:           '8px',
      right:         '8px',
      background:    'rgba(17,24,39,0.92)',
      color:         '#fff',
      padding:       '8px 12px',
      borderRadius:  '8px',
      fontSize:      '12px',
      fontFamily:    'system-ui, sans-serif',
      lineHeight:    '1.5',
      pointerEvents: 'none',
      opacity:       '0',
      transition:    'opacity 0.15s',
      zIndex:        '100',
      boxShadow:     '0 2px 8px rgba(0,0,0,0.25)',
      fontVariantNumeric: 'tabular-nums',
    });
    parent.appendChild(box);
    return box;
  }

  // Significant figures rather than fixed decimals: a selection spanning
  // 0.002 and one spanning 20000 both need to read sensibly.
  function fmt(v) {
    if (!isFinite(v)) return '--';
    const abs = Math.abs(v);
    if (abs === 0) return '0';
    if (abs >= 1000) return v.toFixed(0);
    if (abs >= 10) return v.toFixed(1);
    if (abs >= 1) return v.toFixed(2);
    return v.toPrecision(3);
  }

  function elementsInside(svg, bx, by, bw, bh) {
    const hits = [];
    svg.querySelectorAll('.glyphx-point').forEach(el => {
      const c = elementCenter(el);
      if (c && c.x >= bx && c.x <= bx + bw && c.y >= by && c.y <= by + bh) {
        hits.push(el);
      }
    });
    return hits;
  }

  function summarise(elements) {
    const ys = [];
    elements.forEach(el => {
      const raw = el.getAttribute('data-y');
      if (raw === null) return;
      const n = Number(raw);
      if (isFinite(n)) ys.push(n);          // categorical y is skipped
    });
    if (!ys.length) return { count: elements.length, numeric: 0 };

    let sum = 0, min = Infinity, max = -Infinity;
    ys.forEach(v => { sum += v; if (v < min) min = v; if (v > max) max = v; });
    return {
      count: elements.length,
      numeric: ys.length,
      sum: sum,
      mean: sum / ys.length,
      min: min,
      max: max,
    };
  }

  function renderStats(svg, stats) {
    const box = ensureStats(svg);
    if (!stats || !stats.count) { box.style.opacity = '0'; return; }

    const rows = [['selected', String(stats.count)]];
    if (stats.numeric) {
      rows.push(['mean', fmt(stats.mean)]);
      rows.push(['sum', fmt(stats.sum)]);
      rows.push(['range', fmt(stats.min) + ' to ' + fmt(stats.max)]);
    }
    // textContent per cell, never innerHTML: these values come from the
    // plotted data.
    box.textContent = '';
    rows.forEach(([term, value]) => {
      const line = document.createElement('div');
      const k = document.createElement('span');
      k.textContent = term + ': ';
      k.style.opacity = '0.65';
      const v = document.createElement('span');
      v.textContent = value;
      line.appendChild(k); line.appendChild(v);
      box.appendChild(line);
    });
    box.style.opacity = '1';
  }

  function hideStats() {
    document.querySelectorAll('.glyphx-brush-stats').forEach(b => {
      b.style.opacity = '0';
    });
  }

  // -- Wire a single chart SVG ---------------------------------------------
  function wireChart(svg) {
    svg.addEventListener('mousedown', e => {
      if (!e.shiftKey) return;
      e.preventDefault();
      e.stopPropagation();

      isBrushing = true;
      activeSvg  = svg;
      startPt    = svgPoint(svg, e);

      const r = ensureBrushRect(svg);
      updateBrushRect(r, startPt.x, startPt.y, startPt.x, startPt.y);
      svg.style.cursor = 'crosshair';
    });

    svg.addEventListener('mousemove', e => {
      if (!isBrushing || activeSvg !== svg) return;
      const cur = svgPoint(svg, e);
      const r   = ensureBrushRect(svg);
      updateBrushRect(r, startPt.x, startPt.y, cur.x, cur.y);

      // Update as the rectangle grows, so the numbers guide the drag
      // rather than only reporting on it afterwards.
      renderStats(svg, summarise(elementsInside(
        svg, +r.getAttribute('x'), +r.getAttribute('y'),
        +r.getAttribute('width'), +r.getAttribute('height'))));
    });

    svg.addEventListener('mouseup', e => {
      if (!isBrushing || activeSvg !== svg) return;
      isBrushing          = false;
      svg.style.cursor    = '';
      const r             = ensureBrushRect(svg);
      r.style.display     = 'none';

      const bx = +r.getAttribute('x');
      const by = +r.getAttribute('y');
      const bw = +r.getAttribute('width');
      const bh = +r.getAttribute('height');

      // Tiny drag = clear
      if (bw < 6 && bh < 6) { clearSelection(); hideStats(); return; }

      renderStats(svg, summarise(elementsInside(svg, bx, by, bw, bh)));

      // Collect data-x keys inside the brush on THIS chart
      const selected = new Set();
      svg.querySelectorAll('.glyphx-point').forEach(el => {
        const c = elementCenter(el);
        if (c && c.x >= bx && c.x <= bx + bw && c.y >= by && c.y <= by + bh) {
          const k = el.getAttribute('data-x');
          if (k !== null) selected.add(k);
        }
      });

      applySelection(selected.size ? selected : null);

      // A click event follows every mousedown/mouseup pair, and interact.js
      // handles clicks by resetting every point's opacity -- which wiped the
      // selection the instant it was applied, so brushing never actually
      // highlighted anything. Swallow that one click.
      suppressNextClick = true;
    });

    // Cancel if mouse leaves while dragging
    svg.addEventListener('mouseleave', () => {
      if (isBrushing && activeSvg === svg) {
        isBrushing = false;
        svg.style.cursor = '';
        ensureBrushRect(svg).style.display = 'none';
      }
    });
  }

  // -- Global keyboard handlers ---------------------------------------------
  document.addEventListener('keydown', e => {
    if (e.key === 'Shift') {
      document.querySelectorAll('svg[data-glyphx]').forEach(svg => {
        ensureHint(svg).style.opacity = '1';
      });
    }
    if (e.key === 'Escape') { clearSelection(); }
  });

  document.addEventListener('keyup', e => {
    if (e.key === 'Shift') {
      document.querySelectorAll('.glyphx-brush-hint').forEach(h => {
        h.style.opacity = '0';
      });
    }
  });

  // Click outside any chart clears selection (without Shift)
  document.addEventListener('click', e => {
    if (!e.shiftKey && !e.target.closest('svg[data-glyphx]')) {
      clearSelection();
    }
  });

  // -- Init ------------------------------------------------------------------
  function init() {
    document.querySelectorAll('svg[data-glyphx]').forEach(wireChart);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
