/*
 * GlyphX -- notebook inline interactivity.
 *
 * The page-level assets (tooltip.js, zoom.js, brush.js, ...) assume a normal
 * document: they bind on DOMContentLoaded and scan the whole page. Neither
 * assumption holds inside a notebook. DOMContentLoaded has already fired by
 * the time a cell renders its output, so those handlers never run, and a
 * document-wide scan re-binds every chart in every earlier cell each time any
 * cell is re-executed, stacking duplicate listeners.
 *
 * So notebooks get this instead: one function, bound to a single chart, that
 * refuses to bind the same chart twice. It covers the interactions that make
 * sense in a cell -- hover tooltips, legend toggling, keyboard focus. Zoom,
 * pan, and linked brushing are page-level gestures that fight with notebook
 * scrolling; use fig.share("chart.html") for those.
 */
(function () {
  "use strict";

  if (window.glyphxInitChart) return;   // already loaded by an earlier cell

  var TOOLTIP_ID = "glyphx-notebook-tooltip";

  function tooltipElement() {
    var tip = document.getElementById(TOOLTIP_ID);
    if (tip) return tip;

    tip = document.createElement("div");
    tip.id = TOOLTIP_ID;
    tip.style.cssText = [
      "position:absolute", "display:none", "pointer-events:none",
      "background:#fff", "color:#111", "border:1px solid #ccc",
      "border-radius:4px", "padding:4px 8px", "font:12px sans-serif",
      "box-shadow:0 2px 6px rgba(0,0,0,0.15)", "z-index:9999"
    ].join(";");
    document.body.appendChild(tip);
    return tip;
  }

  function bindTooltips(root, tip) {
    root.querySelectorAll(".glyphx-point").forEach(function (el) {
      el.addEventListener("mouseenter", function () {
        var label = el.getAttribute("data-label");
        var x = el.getAttribute("data-x");
        var y = el.getAttribute("data-y");
        var value = el.getAttribute("data-value");
        var parts = [];
        if (label) parts.push("<b>" + label + "</b>");
        if (x) parts.push("x: " + x);
        if (y) parts.push("y: " + y);
        if (value) parts.push("value: " + value);
        tip.innerHTML = parts.join("<br/>");
        tip.style.display = parts.length ? "block" : "none";
      });
      el.addEventListener("mousemove", function (event) {
        tip.style.left = (event.pageX + 12) + "px";
        tip.style.top = (event.pageY + 12) + "px";
      });
      el.addEventListener("mouseleave", function () {
        tip.style.display = "none";
      });
    });
  }

  function seriesElements(root, target) {
    return Array.prototype.filter.call(
      root.querySelectorAll("." + target),
      function (el) { return !el.hasAttribute("data-target"); }
    );
  }

  function bindLegend(root) {
    root.querySelectorAll(".legend-icon, .legend-label").forEach(function (el) {
      var target = el.getAttribute("data-target");
      if (!target) return;

      el.setAttribute("role", "switch");
      el.setAttribute("tabindex", "0");
      el.setAttribute("aria-pressed", "true");
      el.style.cursor = "pointer";

      function toggle(event) {
        event.preventDefault();
        var els = seriesElements(root, target);
        var hidden = els.length > 0 && els[0].getAttribute("visibility") === "hidden";
        els.forEach(function (node) {
          if (hidden) node.removeAttribute("visibility");
          else node.setAttribute("visibility", "hidden");
        });
        root.querySelectorAll('[data-target="' + target + '"]').forEach(function (entry) {
          entry.setAttribute("opacity", hidden ? "1" : "0.35");
          entry.setAttribute("aria-pressed", hidden ? "true" : "false");
        });
      }

      el.addEventListener("click", toggle);
      el.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
          toggle(event);
        }
      });
    });
  }

  window.glyphxInitChart = function (chartId) {
    var root = document.getElementById(chartId);
    if (!root) return;
    // Re-running a cell replaces its output, but a chart shown twice in the
    // same output must not accumulate two sets of listeners.
    if (root.getAttribute("data-glyphx-bound") === "1") return;
    root.setAttribute("data-glyphx-bound", "1");

    bindTooltips(root, tooltipElement());
    bindLegend(root);
  };
})();
