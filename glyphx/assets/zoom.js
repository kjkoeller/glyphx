/**
 * GlyphX Zoom + Pan
 *
 * Mouse wheel  -> zoom (centred on cursor)
 * Mouse drag   -> pan  (only when Shift is NOT held -- Shift+drag = brush)
 */
(function () {
  const svgs = document.querySelectorAll('svg[data-glyphx]');
  if (!svgs.length) return;

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
    }, { passive: false });

    // Double-click resets zoom
    svg.addEventListener('dblclick', () => {
      const vb = svg.getAttribute('viewBox').split(' ').map(Number);
      // Reset to original (stored on first load)
      if (svg.dataset.originalViewBox) {
        svg.setAttribute('viewBox', svg.dataset.originalViewBox);
        viewBox = svg.dataset.originalViewBox.split(' ').map(Number);
      }
    });

    // Store original viewBox for reset
    svg.dataset.originalViewBox = viewBox.join(' ');
  });
})();
