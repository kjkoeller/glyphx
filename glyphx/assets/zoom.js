/**
 * GlyphX Zoom + Pan
 *
 * Mouse wheel  -> zoom (centred on cursor)
 * Mouse drag   -> pan  (only when Shift is NOT held -- Shift+drag = brush)
 */
(function () {
  const svgs = document.querySelectorAll('svg[data-glyphx]');
  if (!svgs.length) return;

  // ---- Axis relabelling ---------------------------------------------------
  //
  // Zooming rewrites the viewBox, which crops the whole drawing -- including
  // the tick labels, which are static text positioned for the original
  // domain. A few scroll steps in and the chart had no visible scale at all:
  // no numbers, no gridlines, no way to tell what you were looking at.
  //
  // The root carries the plot rectangle and the data domains, so the visible
  // region can be mapped back to data coordinates and the ticks redrawn for
  // whatever is actually on screen.

  function nums(svg, attr) {
    const raw = svg.getAttribute(attr);
    return raw ? raw.split(',').map(Number) : null;
  }

  // "Nice" round steps, so labels read 0.5 / 1 / 2 rather than 0.4713.
  function niceTicks(lo, hi, count) {
    if (!isFinite(lo) || !isFinite(hi) || hi <= lo) return [];
    const raw  = (hi - lo) / Math.max(1, count);
    const mag  = Math.pow(10, Math.floor(Math.log10(raw)));
    const norm = raw / mag;
    const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
    const out  = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) {
      out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
    }
    return out;
  }

  function format(v, span) {
    if (v === 0) return '0';
    const digits = span >= 100 ? 0 : span >= 10 ? 1 : span >= 1 ? 2 : 3;
    return v.toFixed(digits);
  }

  function snapshot(svg) {
    svg.querySelectorAll('.glyphx-tick').forEach(node => {
      if (node.dataset.origText === undefined) {
        node.dataset.origText = node.textContent;
        node.dataset.origX = node.getAttribute('x');
        node.dataset.origY = node.getAttribute('y');
        node.dataset.origAnchor = node.getAttribute('text-anchor') || '';
        node.dataset.origSize = node.getAttribute('font-size') || '11';
      }
    });
  }

  // Reset puts the original labels back verbatim rather than recomputing
  // them, so a zoom-and-reset round trip leaves the chart byte-identical.
  function restore(svg) {
    svg.querySelectorAll('.glyphx-tick').forEach(node => {
      if (node.dataset.origText === undefined) return;
      node.textContent = node.dataset.origText;
      node.setAttribute('x', node.dataset.origX);
      node.setAttribute('y', node.dataset.origY);
      node.setAttribute('font-size', node.dataset.origSize);
      if (node.dataset.origAnchor) {
        node.setAttribute('text-anchor', node.dataset.origAnchor);
      }
      node.style.display = '';
    });
  }

  // -- Reset control --------------------------------------------------------
  //
  // Resetting was a double-click on empty space and nothing else -- no
  // button, and the toolbar hint never mentioned it, so a user who zoomed in
  // had no visible way back. The button appears only once the view has
  // actually moved, which both keeps the toolbar quiet for people who never
  // zoom and makes the affordance show up exactly when it is wanted.

  function atDefault(svg) {
    return !svg.dataset.originalViewBox ||
           svg.getAttribute('viewBox') === svg.dataset.originalViewBox;
  }

  function resetAll() {
    document.querySelectorAll('svg[data-glyphx]').forEach(svg => {
      if (!svg.dataset.originalViewBox) return;
      svg.setAttribute('viewBox', svg.dataset.originalViewBox);
      restore(svg);
      if (svg.__glyphxSyncViewBox) svg.__glyphxSyncViewBox();
    });
    updateResetButton();
  }

  function resetButton() {
    const toolbar = document.querySelector('.glyphx-toolbar');
    if (!toolbar) return null;
    let btn = toolbar.querySelector('.glyphx-reset-view');
    if (btn) return btn;

    btn = document.createElement('button');
    btn.className = 'glyphx-btn glyphx-reset-view';
    btn.textContent = 'Reset view';
    btn.title = 'Back to the original zoom and position (or double-click the chart)';
    btn.style.display = 'none';
    btn.addEventListener('click', resetAll);
    toolbar.insertBefore(btn, toolbar.firstElementChild
      && toolbar.querySelector('.glyphx-btn'));
    return btn;
  }

  function updateResetButton() {
    const btn = resetButton();
    if (!btn) return;
    const moved = Array.prototype.slice
      .call(document.querySelectorAll('svg[data-glyphx]'))
      .some(svg => !atDefault(svg));
    btn.style.display = moved ? '' : 'none';
  }

  function relabel(svg) {
    snapshot(svg);
    const plot = nums(svg, 'data-plot');
    const dx   = nums(svg, 'data-domain-x');
    const dy   = nums(svg, 'data-domain-y');
    if (!plot || !dx || !dy) return;                  // nothing to work from
    if (svg.getAttribute('data-xscale') !== 'linear' ||
        svg.getAttribute('data-yscale') !== 'linear') return;   // log: leave alone

    const vb = svg.getAttribute('viewBox').split(' ').map(Number);
    const [px0, py0, px1, py1] = plot;
    const scale = vb[2] / (svg.dataset.originalViewBox
      ? Number(svg.dataset.originalViewBox.split(' ')[2]) : vb[2]);

    // Visible user-space window, intersected with the plot rectangle.
    const ux0 = Math.max(px0, vb[0]), ux1 = Math.min(px1, vb[0] + vb[2]);
    const uy0 = Math.max(py0, vb[1]), uy1 = Math.min(py1, vb[1] + vb[3]);
    if (ux1 <= ux0 || uy1 <= uy0) return;

    const toDataX = u => dx[0] + (u - px0) / (px1 - px0) * (dx[1] - dx[0]);
    const toDataY = u => dy[1] - (u - py0) / (py1 - py0) * (dy[1] - dy[0]);
    const toUserX = d => px0 + (d - dx[0]) / (dx[1] - dx[0]) * (px1 - px0);
    const toUserY = d => py0 + (dy[1] - d) / (dy[1] - dy[0]) * (py1 - py0);

    apply(svg, 'glyphx-xtick', niceTicks(toDataX(ux0), toDataX(ux1), 5),
          toUserX, 'x', vb, scale);
    apply(svg, 'glyphx-ytick', niceTicks(toDataY(uy1), toDataY(uy0), 5),
          toUserY, 'y', vb, scale);
  }

  function apply(svg, cls, values, toUser, axis, vb, scale) {
    const nodes = Array.prototype.slice.call(svg.querySelectorAll('.' + cls));
    if (!nodes.length) return;
    const span = values.length > 1 ? Math.abs(values[values.length - 1] - values[0]) : 1;

    nodes.forEach((node, i) => {
      if (i >= values.length) { node.style.display = 'none'; return; }
      node.style.display = '';
      const user = toUser(values[i]);
      // Pin the label to the edge of the *visible* window, not the original
      // canvas, or it sits off-screen the moment you pan away from it.
      if (axis === 'x') {
        node.setAttribute('x', user);
        node.setAttribute('y', vb[1] + vb[3] - 6 * scale);
      } else {
        node.setAttribute('y', user);
        node.setAttribute('x', vb[0] + 6 * scale);
        node.setAttribute('text-anchor', 'start');
      }
      // Counteract the viewBox scale so text stays a constant size.
      node.setAttribute('font-size', 11 * scale);
      node.textContent = format(values[i], span);
    });
  }

  svgs.forEach(svg => {
    let viewBox   = svg.getAttribute('viewBox').split(' ').map(Number);
    let isPanning = false;
    let startX    = 0, startY = 0;

    svg.style.cursor = 'grab';

    svg.addEventListener('mousedown', e => {
      // Leave Shift+drag to brush.js
      if (e.shiftKey || e.button !== 0) return;
      isPanning = true;
      startX    = e.clientX;
      startY    = e.clientY;
      svg.style.cursor = 'grabbing';
    });

    svg.addEventListener('mousemove', e => {
      if (!isPanning) return;
      const dx = (e.clientX - startX) * (viewBox[2] / svg.clientWidth);
      const dy = (e.clientY - startY) * (viewBox[3] / svg.clientHeight);
      viewBox[0] -= dx;
      viewBox[1] -= dy;
      svg.setAttribute('viewBox', viewBox.join(' '));
      relabel(svg);
      updateResetButton();
      startX = e.clientX;
      startY = e.clientY;
    });

    ['mouseup', 'mouseleave'].forEach(ev => {
      svg.addEventListener(ev, () => {
        if (isPanning) {
          isPanning = false;
          svg.style.cursor = 'grab';
        }
      });
    });

    svg.addEventListener('wheel', e => {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1.1 : 1 / 1.1;
      const [x, y, w, h] = viewBox;
      const nw = w * factor;
      const nh = h * factor;
      const mx = e.offsetX / svg.clientWidth;
      const my = e.offsetY / svg.clientHeight;
      viewBox = [x + mx * (w - nw), y + my * (h - nh), nw, nh];
      svg.setAttribute('viewBox', viewBox.join(' '));
      relabel(svg);
      updateResetButton();
    }, { passive: false });

    // Double-click on empty space resets the view. On a data point it means
    // "focus this series" instead (interact.js), so ignore those -- one
    // gesture doing both at once was the previous behaviour and read as a
    // glitch: the chart would isolate a series and jump back to full extent
    // in the same motion.
    svg.addEventListener('dblclick', (e) => {
      if (e.target.closest('[data-x], [data-label]')) return;
      if (svg.dataset.originalViewBox) {
        svg.setAttribute('viewBox', svg.dataset.originalViewBox);
        viewBox = svg.dataset.originalViewBox.split(' ').map(Number);
        restore(svg);
        updateResetButton();
      }
    });

    // Store original viewBox for reset
    svg.dataset.originalViewBox = viewBox.join(' ');
    // resetAll() runs outside this closure; without this the button would
    // reset the attribute while the next scroll kept zooming from the old
    // value, so the chart would jump.
    svg.__glyphxSyncViewBox = () => {
      viewBox = svg.getAttribute('viewBox').split(' ').map(Number);
    };
  });
})();
