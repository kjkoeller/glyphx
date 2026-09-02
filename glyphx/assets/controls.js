/*
 * GlyphX -- chart controls.
 *
 * Checkboxes, radio buttons, a search box and reset buttons that filter the
 * chart in the browser. Configured from Python:
 *
 *     fig.add_controls(checkboxes="region", search="customer")
 *
 * which emits a <div data-glyphx-controls='{...}'> beside the chart. There is
 * no server and no callback: every control narrows the set of visible
 * elements by matching against the data-* attributes already on them, the
 * same mechanism the cross-filter and detail panel use.
 *
 * Filters combine with AND, which is what a stack of controls reads as: tick
 * two regions and type a name, and you get that name within those regions.
 */
(function () {
  "use strict";

  var STYLE_ID = "glyphx-controls-style";
  var HIDDEN = "glyphx-filtered-out";

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = [
      ".glyphx-controls {",
      "  font: 13px/1.6 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;",
      "  border: 1px solid rgba(0,0,0,.12); border-radius: 8px;",
      "  padding: 12px 14px; min-width: 170px; background: #fff;",
      "}",
      ".glyphx-controls h4 { margin: 0 0 8px; font-size: 13px; }",
      ".glyphx-controls fieldset { border: 0; margin: 0 0 12px; padding: 0; }",
      ".glyphx-controls legend {",
      "  padding: 0; margin-bottom: 4px; color: #6b7280; font-size: 12px;",
      "}",
      ".glyphx-controls label {",
      "  display: flex; align-items: center; gap: 7px; cursor: pointer;",
      "  padding: 1px 0;",
      "}",
      ".glyphx-controls input[type=search] {",
      "  width: 100%; box-sizing: border-box; padding: 5px 8px;",
      "  border: 1px solid rgba(0,0,0,.2); border-radius: 6px; font: inherit;",
      "}",
      ".glyphx-controls button {",
      "  font: inherit; padding: 5px 10px; border-radius: 6px; cursor: pointer;",
      "  border: 1px solid rgba(0,0,0,.2); background: #fff;",
      "}",
      ".glyphx-controls button:hover { background: #f3f4f6; }",
      ".glyphx-controls .glyphx-controls-count {",
      "  color: #6b7280; font-size: 12px; margin-top: 4px;",
      "}",
      "." + HIDDEN + " { display: none; }",
      // Sit beside the chart when there is room, below on a narrow screen.
      // The template sets `svg { width: 100% }`, which takes the whole row
      // and pushes the panel onto the next line, so the SVG is given a flex
      // basis it can shrink from instead.
      ".glyphx-chart-area:has(.glyphx-controls) {",
      "  display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap;",
      "}",
      ".glyphx-chart-area:has(.glyphx-controls) > svg {",
      "  flex: 1 1 340px; min-width: 0; width: auto;",
      "}",
      ".glyphx-chart-area > .glyphx-controls { flex: 0 1 190px; }",
    ].join("\n");
    document.head.appendChild(style);
  }

  function config(panel) {
    try {
      return JSON.parse(panel.getAttribute("data-glyphx-controls")) || {};
    } catch (err) {
      return {};
    }
  }

  function charts(panel) {
    // Controls filter every chart in their own container, so a SubplotGrid
    // gets one panel driving the whole dashboard rather than one each.
    var scope = panel.closest(".glyphx-chart-area") || document;
    return Array.prototype.slice.call(scope.querySelectorAll("svg[data-glyphx]"));
  }

  function points(panel) {
    var out = [];
    charts(panel).forEach(function (svg) {
      out = out.concat(Array.prototype.slice.call(
        svg.querySelectorAll("[data-x]")));
    });
    return out;
  }

  function metaOf(el) {
    var raw = el.getAttribute("data-meta");
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (err) { return null; }
  }

  // Look a field up wherever it lives: in the point's metadata, in its own
  // data-* attributes, or as the series label. Callers should not have to
  // know which, and the answer differs per chart type.
  function valueOf(el, field) {
    var meta = metaOf(el);
    if (meta && meta[field] !== undefined) return String(meta[field]);
    var attr = el.getAttribute("data-" + field);
    if (attr !== null) return attr;
    if (field === "series" || field === "label") {
      return el.getAttribute("data-label") || "";
    }
    return null;
  }

  function distinct(panel, field) {
    var seen = [];
    points(panel).forEach(function (el) {
      var v = valueOf(el, field);
      if (v !== null && v !== "" && seen.indexOf(v) === -1) seen.push(v);
    });
    return seen.sort();
  }

  function labelled(text, input) {
    var label = document.createElement("label");
    label.appendChild(input);
    var span = document.createElement("span");
    span.textContent = text;          // values come from the plotted data
    label.appendChild(span);
    return label;
  }

  function build(panel) {
    var cfg = config(panel);
    panel.textContent = "";

    if (cfg.title) {
      var h = document.createElement("h4");
      h.textContent = cfg.title;
      panel.appendChild(h);
    }

    var state = { checkbox: {}, radio: {}, search: "" };
    panel.__glyphxState = state;

    if (cfg.checkboxes) {
      var values = distinct(panel, cfg.checkboxes);
      var fs = document.createElement("fieldset");
      var lg = document.createElement("legend");
      lg.textContent = cfg.checkbox_label || cfg.checkboxes;
      fs.appendChild(lg);
      // Everything starts ticked: a control panel that hides the data on
      // load looks broken.
      values.forEach(function (v) {
        state.checkbox[v] = true;
        var input = document.createElement("input");
        input.type = "checkbox";
        input.checked = true;
        input.value = v;
        input.addEventListener("change", function () {
          state.checkbox[v] = input.checked;
          apply(panel);
        });
        fs.appendChild(labelled(v, input));
      });
      panel.appendChild(fs);
    }

    if (cfg.radio) {
      var rvalues = distinct(panel, cfg.radio);
      var rfs = document.createElement("fieldset");
      var rlg = document.createElement("legend");
      rlg.textContent = cfg.radio_label || cfg.radio;
      rfs.appendChild(rlg);
      var name = "glyphx-radio-" + Math.random().toString(36).slice(2, 8);

      // An "All" option, or a radio group has no way back to unfiltered
      // once the reader picks one.
      ["All"].concat(rvalues).forEach(function (v, i) {
        var input = document.createElement("input");
        input.type = "radio";
        input.name = name;
        input.value = v;
        input.checked = i === 0;
        input.addEventListener("change", function () {
          state.radio[cfg.radio] = (v === "All") ? null : v;
          apply(panel);
        });
        rfs.appendChild(labelled(v, input));
      });
      state.radio[cfg.radio] = null;
      panel.appendChild(rfs);
    }

    if (cfg.search) {
      var sfs = document.createElement("fieldset");
      var slg = document.createElement("legend");
      slg.textContent = cfg.search_label || cfg.search;
      sfs.appendChild(slg);
      var box = document.createElement("input");
      box.type = "search";
      box.placeholder = cfg.placeholder || "Type to filter";
      box.addEventListener("input", function () {
        state.search = box.value.trim().toLowerCase();
        apply(panel);
      });
      sfs.appendChild(box);
      panel.appendChild(sfs);
      panel.__glyphxSearchBox = box;
    }

    if (cfg.reset !== false) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = cfg.reset_label || "Show all";
      btn.addEventListener("click", function () {
        panel.querySelectorAll("input[type=checkbox]").forEach(function (i) {
          i.checked = true;
          state.checkbox[i.value] = true;
        });
        panel.querySelectorAll("input[type=radio]").forEach(function (i) {
          i.checked = i.value === "All";
        });
        Object.keys(state.radio).forEach(function (k) { state.radio[k] = null; });
        if (panel.__glyphxSearchBox) panel.__glyphxSearchBox.value = "";
        state.search = "";
        apply(panel);
      });
      panel.appendChild(btn);
    }

    var count = document.createElement("div");
    count.className = "glyphx-controls-count";
    count.setAttribute("role", "status");
    count.setAttribute("aria-live", "polite");
    panel.appendChild(count);
    panel.__glyphxCount = count;

    apply(panel);
  }

  function matches(el, cfg, state) {
    if (cfg.checkboxes) {
      var v = valueOf(el, cfg.checkboxes);
      if (v !== null && state.checkbox[v] === false) return false;
    }
    var chosen = cfg.radio ? state.radio[cfg.radio] : null;
    if (chosen) {
      if (valueOf(el, cfg.radio) !== chosen) return false;
    }
    if (state.search && cfg.search) {
      var s = valueOf(el, cfg.search);
      if (s === null || s.toLowerCase().indexOf(state.search) === -1) return false;
    }
    return true;
  }

  function apply(panel) {
    var cfg = config(panel);
    var state = panel.__glyphxState;
    if (!state) return;

    var shown = 0, total = 0;
    points(panel).forEach(function (el) {
      total += 1;
      if (matches(el, cfg, state)) {
        el.classList.remove(HIDDEN);
        shown += 1;
      } else {
        el.classList.add(HIDDEN);
      }
    });

    if (panel.__glyphxCount) {
      panel.__glyphxCount.textContent =
        shown === total ? "Showing all " + total
                        : "Showing " + shown + " of " + total;
    }
  }

  function init() {
    var panels = document.querySelectorAll("[data-glyphx-controls]");
    if (!panels.length) return;
    ensureStyle();
    Array.prototype.forEach.call(panels, build);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
