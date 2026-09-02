/*
 * GlyphX -- selection events.
 *
 * Clicking a data point dispatches a `glyphx:select` CustomEvent on
 * `document`, and clicking empty space dispatches `glyphx:deselect`. That is
 * the whole extension surface: anything on the page -- a detail panel, a
 * table, a second chart, an <img>, a fetch to your own endpoint -- can listen
 * and update itself.
 *
 *   document.addEventListener('glyphx:select', (e) => {
 *     const { x, y, label, series, meta, element } = e.detail;
 *     document.getElementById('detail').textContent = meta.customer;
 *   });
 *
 * `meta` is whatever was passed to the series as `meta=[...]` in Python,
 * parsed back from JSON, so the listener receives the same structure the
 * caller wrote rather than a flattened string.
 *
 * Events rather than a callback registry: any number of listeners can attach
 * without knowing about each other, they can be removed, and nothing here
 * needs to know what they do. No server, no callback round-trip -- this all
 * runs in the exported file.
 */
(function () {
  "use strict";

  var SELECTED_CLASS = "glyphx-selected";
  var selected = null;

  function ensureStyle() {
    if (document.getElementById("glyphx-select-style")) return;
    var style = document.createElement("style");
    style.id = "glyphx-select-style";
    // An outline rather than a fill change, so the point keeps its encoded
    // colour -- the colour is data, the selection is not.
    style.textContent =
      "." + SELECTED_CLASS + " { stroke: currentColor; stroke-width: 2.5px; " +
      "paint-order: stroke; }";
    document.head.appendChild(style);
  }

  function parseMeta(el) {
    var raw = el.getAttribute("data-meta");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (err) {
      // Malformed metadata should not take the whole page down; hand the
      // listener the raw string and let it decide.
      return raw;
    }
  }

  function seriesOf(el) {
    var cls = Array.prototype.find.call(el.classList, function (c) {
      return c.indexOf("series-") === 0 || c.indexOf("series3d-") === 0;
    });
    return cls || null;
  }

  function detailFor(el) {
    return {
      x: el.getAttribute("data-x"),
      y: el.getAttribute("data-y"),
      label: el.getAttribute("data-label"),
      series: seriesOf(el),
      meta: parseMeta(el),
      element: el,
    };
  }

  function clearSelection() {
    if (!selected) return;
    selected.classList.remove(SELECTED_CLASS);
    selected = null;
    document.dispatchEvent(new CustomEvent("glyphx:deselect"));
  }

  function select(el) {
    if (selected === el) {          // clicking the same point again clears
      clearSelection();
      return;
    }
    if (selected) selected.classList.remove(SELECTED_CLASS);
    selected = el;
    el.classList.add(SELECTED_CLASS);
    document.dispatchEvent(new CustomEvent("glyphx:select", {
      detail: detailFor(el),
    }));
  }

  // Capture phase, because crossfilter.js also claims plain clicks and calls
  // stopPropagation() there -- a bubble-phase listener would never run on a
  // chart with filtering enabled. Both are capture listeners on `document`,
  // and stopPropagation does not stop siblings on the same node, so the two
  // features compose: one click both filters and emits a selection.
  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;
    var el = e.target.closest("[data-x]");
    if (!el || !el.closest("svg[data-glyphx]")) {
      // A click on the chart background means "nothing is selected".
      if (e.target.closest && e.target.closest("svg[data-glyphx]")) {
        clearSelection();
      }
      return;
    }
    // Modified clicks belong to the inspector and the other interact.js
    // gestures; only a plain click is a selection.
    if (e.shiftKey || e.altKey || e.metaKey || e.ctrlKey) return;
    select(el);
  }, true);

  // Keyboard parity: points already carry tabindex="0".
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      clearSelection();
      return;
    }
    if (e.key !== "Enter" && e.key !== " ") return;
    var el = document.activeElement;
    if (!el || !el.getAttribute || el.getAttribute("data-x") === null) return;
    if (!el.closest("svg[data-glyphx]")) return;
    e.preventDefault();
    select(el);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureStyle);
  } else {
    ensureStyle();
  }
})();
