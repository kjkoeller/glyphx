/*
 * GlyphX -- selection detail panel.
 *
 * A panel that fills itself in when a point is clicked, so the common case
 * ("click a point, show its details") needs no JavaScript from the caller.
 * Configured entirely from Python:
 *
 *     fig.add_detail_panel(fields=["customer", "region"])
 *
 * which emits a <div data-glyphx-detail-panel='{...}'> next to the chart.
 * This reads that config and subscribes to the `glyphx:select` event that
 * select.js already dispatches -- it is an ordinary consumer of the public
 * event, not a special case wired into the chart. Anything else on the page
 * can listen to the same event at the same time.
 */
(function () {
  "use strict";

  var STYLE_ID = "glyphx-detail-panel-style";

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = [
      ".glyphx-detail-panel {",
      "  font: 13px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;",
      "  border: 1px solid rgba(0,0,0,.12); border-radius: 8px;",
      "  padding: 12px 14px; min-width: 180px; background: #fff;",
      "}",
      ".glyphx-detail-panel[data-empty='true'] { color: #6b7280; }",
      ".glyphx-detail-panel dl { margin: 0; display: grid;",
      "  grid-template-columns: auto 1fr; gap: 4px 12px; }",
      ".glyphx-detail-panel dt { color: #6b7280; white-space: nowrap; }",
      ".glyphx-detail-panel dd { margin: 0; font-variant-numeric: tabular-nums; }",
      ".glyphx-detail-panel h4 { margin: 0 0 8px; font-size: 13px; }",
      // Put the panel beside the chart when there is room, and below it on
      // a narrow screen, without the caller writing any layout CSS. The
      // template sets `svg { width: 100% }`, which would take the whole row
      // and push the panel onto the next line, so the SVG is given a flex
      // basis it can shrink from instead.
      ".glyphx-chart-area:has(.glyphx-detail-panel) {",
      "  display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap;",
      "}",
      ".glyphx-chart-area:has(.glyphx-detail-panel) > svg {",
      "  flex: 1 1 340px; min-width: 0; width: auto;",
      "}",
      ".glyphx-chart-area > .glyphx-detail-panel { flex: 0 1 220px; }",
    ].join("\n");
    document.head.appendChild(style);
  }

  function config(panel) {
    try {
      return JSON.parse(panel.getAttribute("data-glyphx-detail-panel")) || {};
    } catch (err) {
      return {};
    }
  }

  // Text, never markup: the values come from the chart's own data, which is
  // whatever the caller plotted. Building innerHTML from it would make any
  // dataset containing a "<" an injection vector.
  function row(dl, term, value) {
    var dt = document.createElement("dt");
    dt.textContent = term;
    var dd = document.createElement("dd");
    dd.textContent = value;
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  function render(panel, detail) {
    var cfg = config(panel);
    panel.textContent = "";
    panel.setAttribute("data-empty", "false");

    if (cfg.title) {
      var heading = document.createElement("h4");
      heading.textContent = cfg.title;
      panel.appendChild(heading);
    }

    var dl = document.createElement("dl");
    var meta = (detail.meta && typeof detail.meta === "object") ? detail.meta : {};

    if (cfg.fields && cfg.fields.length) {
      // An explicit field list also fixes the order, which Object.keys()
      // would not guarantee across browsers for numeric-looking keys.
      cfg.fields.forEach(function (field) {
        // metadata first, then the point's own fields, then anything else
        // the chart type emitted (percent on a pie, q1/q2/q3 on a box plot).
        var value = meta[field];
        if (value === undefined && field === "x") value = detail.x;
        if (value === undefined && field === "y") value = detail.y;
        if (value === undefined && field === "label") value = detail.label;
        if (value === undefined && detail.data) value = detail.data[field];
        if (value === undefined) return;      // absent for this point
        row(dl, field, value);
      });
    } else {
      // No field list: show whatever the point carries, metadata first.
      Object.keys(meta).forEach(function (k) { row(dl, k, meta[k]); });
      if (!Object.keys(meta).length) {
        row(dl, "x", detail.x);
        row(dl, "y", detail.y);
        if (detail.label) row(dl, "series", detail.label);
      }
    }

    panel.appendChild(dl);
  }

  function clear(panel) {
    var cfg = config(panel);
    panel.textContent = cfg.empty || "Click a point to see its details.";
    panel.setAttribute("data-empty", "true");
  }

  function panels() {
    return Array.prototype.slice.call(
      document.querySelectorAll("[data-glyphx-detail-panel]")
    );
  }

  function init() {
    var found = panels();
    if (!found.length) return;
    ensureStyle();
    found.forEach(clear);

    document.addEventListener("glyphx:select", function (e) {
      panels().forEach(function (panel) { render(panel, e.detail); });
    });
    document.addEventListener("glyphx:deselect", function () {
      panels().forEach(clear);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
