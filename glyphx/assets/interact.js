/**
 * GlyphX 2D Interactivity -- Series Highlighting, Inspector, Keyboard
 *
 * Features added here (beyond tooltip.js / zoom.js / brush.js):
 *
 *   Click a point          -> highlight that series, dim all others (0.1 opacity)
 *   Double-click a point   -> isolate ONLY that series (hide all others completely)
 *   Escape                 -> reset all series to full opacity
 *   Click legend item      -> toggle that series visible / hidden
 *   Shift + click a point  -> open data inspector panel for that point
 *   F key                  -> toggle fullscreen on the chart card
 *   C key                  -> toggle synchronized crosshair on/off
 *   H key                  -> show keyboard shortcut help overlay
 *
 * Works with any series that has .glyphx-point elements and a css_class
 * attribute (set by GlyphX as data-series on each element group).
 */
(function () {
  'use strict';

  // -- State --------------------------------------------------------------
  let activeClass  = null;   // currently highlighted css_class
  let isIsolated   = false;  // double-click isolation mode
  let crosshairOn  = false;  // C key toggle
  let helpVisible  = false;

  // -- Inspector panel ----------------------------------------------------
  const inspector = document.createElement('div');
  inspector.id = 'glyphx-inspector';
  Object.assign(inspector.style, {
    position:     'fixed',
    right:        '20px',
    top:          '60px',
    width:        '220px',
    background:   'rgba(15,23,42,0.93)',
    color:        '#f8fafc',
    borderRadius: '10px',
    padding:      '14px 16px',
    fontSize:     '12.5px',
    lineHeight:   '1.7',
    zIndex:       '99998',
    display:      'none',
    boxShadow:    '0 8px 30px rgba(0,0,0,0.35)',
    backdropFilter: 'blur(4px)',
  });
  document.body.appendChild(inspector);

  function showInspector(el) {
    const attrs = {};
    ['data-x','data-y','data-label','data-value','data-q1','data-q2',
     'data-q3','data-size'].forEach(a => {
      const v = el.getAttribute(a);
      if (v !== null) attrs[a.replace('data-','')] = v;
    });
    let html = '<div style="font-weight:700;margin-bottom:8px;font-size:13px">[chart] Data Point</div>';
    Object.entries(attrs).forEach(([k, v]) => {
      html += `<div><span style="opacity:0.55;min-width:52px;display:inline-block">${k}</span><b>${v}</b></div>`;
    });
    html += '<div style="margin-top:10px;font-size:10.5px;opacity:0.4">Shift+click to pin . Esc to close</div>';
    inspector.innerHTML = html;
    inspector.style.display = 'block';
  }

  // -- Help overlay -------------------------------------------------------
  const helpOverlay = document.createElement('div');
  helpOverlay.id = 'glyphx-help';
  Object.assign(helpOverlay.style, {
    position: 'fixed', inset: '0',
    background: 'rgba(0,0,0,0.6)',
    display: 'none',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: '999999',
    backdropFilter: 'blur(3px)',
  });
  helpOverlay.innerHTML = `
    <div style="background:#1e293b;color:#f8fafc;border-radius:14px;
                padding:28px 34px;max-width:380px;width:90%;
                box-shadow:0 20px 60px rgba(0,0,0,0.5)">
      <div style="font-size:16px;font-weight:700;margin-bottom:16px">
        [keyboard] GlyphX Keyboard Shortcuts
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12.5px">
        <tr><td style="padding:4px 0;opacity:0.55;width:110px"><kbd>Click</kbd></td>
            <td>Highlight series</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Dbl-click</kbd></td>
            <td>Isolate series</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Shift+Click</kbd></td>
            <td>Open inspector</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Esc</kbd></td>
            <td>Reset / close</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>C</kbd></td>
            <td>Toggle crosshair</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>F</kbd></td>
            <td>Fullscreen</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>H</kbd></td>
            <td>Show this help</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Scroll</kbd></td>
            <td>Zoom</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Drag</kbd></td>
            <td>Pan</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Shift+Drag</kbd></td>
            <td>Brush / select</td></tr>
        <tr><td style="padding:4px 0;opacity:0.55"><kbd>Dbl-click</kbd></td>
            <td>Reset zoom</td></tr>
      </table>
      <div style="margin-top:16px;text-align:center;opacity:0.4;font-size:11px">
        Click anywhere or press Esc to close
      </div>
    </div>`;
  helpOverlay.addEventListener('click', () => closeHelp());
  document.body.appendChild(helpOverlay);

  function showHelp() { helpOverlay.style.display = 'flex'; helpVisible = true; }
  function closeHelp(){ helpOverlay.style.display = 'none'; helpVisible = false; }

  // -- Core: apply highlight state ----------------------------------------
  function applyHighlight() {
    document.querySelectorAll('.glyphx-point').forEach(el => {
      el.style.transition = 'opacity 0.18s, filter 0.18s';
      if (!activeClass) {
        el.style.opacity = '';
        el.style.filter  = '';
      } else {
        // Match any of the element's class tokens against activeClass
        const hit = el.classList.contains(activeClass);
        if (isIsolated) {
          el.style.opacity = hit ? '1' : '0';
          el.style.filter  = '';
        } else {
          el.style.opacity = hit ? '1'  : '0.10';
          el.style.filter  = hit ? '' : 'grayscale(80%)';
        }
      }
    });
  }

  function resetHighlight() {
    activeClass = null;
    isIsolated  = false;
    applyHighlight();
    inspector.style.display = 'none';
  }

  // -- Click / double-click on points ------------------------------------
  // Use event delegation on the document so dynamically injected points work
  let lastClick = 0;
  document.addEventListener('click', e => {
    const el = e.target.closest('.glyphx-point');
    if (!el) {
      // Clicked outside any point -- reset unless clicking inspector/help
      if (!inspector.contains(e.target) && !helpOverlay.contains(e.target)) {
        resetHighlight();
      }
      return;
    }

    // Shift+click -> inspector
    if (e.shiftKey) {
      showInspector(el);
      return;
    }

    // Detect double-click manually (150ms window)
    const now = Date.now();
    const cls = [...el.classList].find(c => c.startsWith('series') || c.startsWith('series3d'));

    if (now - lastClick < 300 && cls === activeClass) {
      // Double-click: toggle isolation
      isIsolated = !isIsolated;
      applyHighlight();
    } else {
      // Single click: highlight/unhighlight
      if (cls && cls === activeClass && !isIsolated) {
        resetHighlight();
      } else {
        activeClass = cls || null;
        isIsolated  = false;
        applyHighlight();
      }
    }
    lastClick = now;
  });

  // -- Legend item click -> toggle series visibility -----------------------
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.legend-icon, .legend-label').forEach(leg => {
      // Add a visible toggle indicator and pointer cursor
      leg.style.cursor = 'pointer';
      leg.title = 'Click to show/hide series . double-click to isolate';

      leg.addEventListener('click', e => {
        e.stopPropagation();
        const target = leg.dataset.target;
        if (!target) return;

        const pts = document.querySelectorAll('.' + target);
        if (!pts.length) return;

        // Check current state from first point
        const hidden = pts[0].style.opacity === '0' ||
                       pts[0].style.display === 'none';

        pts.forEach(pt => {
          pt.style.transition = 'opacity 0.18s';
          pt.style.opacity = hidden ? '1' : '0';
        });

        // Visual feedback on the legend item
        leg.style.opacity = hidden ? '1' : '0.35';
      });
    });
  });

  // -- Keyboard shortcuts -------------------------------------------------
  document.addEventListener('keydown', e => {
    // Don't steal keys from input fields
    if (['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) return;

    switch (e.key) {
      case 'Escape':
        if (helpVisible) { closeHelp(); break; }
        if (inspector.style.display !== 'none') { inspector.style.display = 'none'; break; }
        resetHighlight();
        break;

      case 'f': case 'F':
        if (!document.fullscreenElement) {
          const card = document.querySelector('.glyphx-card') ||
                       document.querySelector('.glyphx-wrapper') ||
                       document.documentElement;
          card.requestFullscreen && card.requestFullscreen();
        } else {
          document.exitFullscreen && document.exitFullscreen();
        }
        break;

      case 'c': case 'C':
        crosshairOn = !crosshairOn;
        // Signal crosshair.js if present
        document.querySelectorAll('svg[data-glyphx]').forEach(svg => {
          svg.dataset.crosshair = crosshairOn ? 'on' : 'off';
          if (!crosshairOn) {
            svg.querySelectorAll('.glyphx-crosshair').forEach(l => l.remove());
          }
        });
        if (typeof glyphxToast === 'function')
          glyphxToast(crosshairOn ? '+ Crosshair on' : 'Crosshair off');
        break;

      case 'h': case 'H':
        if (helpVisible) closeHelp(); else showHelp();
        break;
    }
  });

  // -- Add [?] help button to every toolbar -------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.glyphx-toolbar').forEach(tb => {
      const btn = document.createElement('button');
      btn.className = 'glyphx-btn';
      btn.textContent = '? Shortcuts';
      btn.title = 'Show keyboard shortcuts (H)';
      btn.addEventListener('click', showHelp);
      tb.appendChild(btn);
    });

    // Update toolbar hint
    document.querySelectorAll('.glyphx-toolbar span').forEach(s => {
      s.textContent = 'GlyphX . click=highlight . shift+click=inspect . dbl-click=isolate . H=shortcuts';
    });
  });

})();
