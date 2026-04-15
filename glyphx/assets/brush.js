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
    hint.textContent = '[hex] Brush mode  .  Shift+drag to select  .  Esc to clear';
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
      if (bw < 6 && bh < 6) { clearSelection(); return; }

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
