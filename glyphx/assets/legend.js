/*
 * GlyphX -- interactive legend.
 *
 * Clicking (or pressing Enter/Space on) a legend entry hides or shows the
 * matching series. draw_legend() already stamps every icon and label with
 * data-target="series-N", which is the same class each series puts on its
 * own SVG elements, so the wiring is a class lookup.
 *
 * Hiding uses the "hidden" attribute plus a CSS class rather than an inline
 * style, so the toggle survives a re-render and does not fight any stylesheet
 * the host page applies.
 */
(function () {
  "use strict";

  var HIDDEN_CLASS = "glyphx-series-hidden";

  function seriesElements(root, target) {
    // Series elements carry the target class; legend entries carry
    // data-target and must not hide themselves.
    return Array.prototype.filter.call(
      root.querySelectorAll("." + target),
      function (el) {
        return !el.hasAttribute("data-target");
      }
    );
  }

  function legendEntries(root, target) {
    return root.querySelectorAll('[data-target="' + target + '"]');
  }

  function setHidden(root, target, hidden) {
    seriesElements(root, target).forEach(function (el) {
      if (hidden) {
        el.classList.add(HIDDEN_CLASS);
        el.setAttribute("visibility", "hidden");
      } else {
        el.classList.remove(HIDDEN_CLASS);
        el.removeAttribute("visibility");
      }
    });

    legendEntries(root, target).forEach(function (el) {
      // Dim the legend entry so the toggle state is visible, and expose it
      // to assistive tech.
      el.setAttribute("opacity", hidden ? "0.35" : "1");
      el.setAttribute("aria-pressed", hidden ? "false" : "true");
    });
  }

  function isHidden(root, target) {
    var els = seriesElements(root, target);
    return els.length > 0 && els[0].classList.contains(HIDDEN_CLASS);
  }

  function bind(root) {
    var entries = root.querySelectorAll(".legend-icon, .legend-label");
    if (!entries.length) return;

    entries.forEach(function (el) {
      var target = el.getAttribute("data-target");
      if (!target) return;

      // Make the entry operable without a mouse.
      el.setAttribute("role", "switch");
      el.setAttribute("tabindex", "0");
      el.setAttribute("aria-pressed", "true");
      el.style.cursor = "pointer";

      var label = el.textContent || target;
      el.setAttribute("aria-label", "Toggle series " + label);

      function toggle(event) {
        event.preventDefault();
        setHidden(root, target, !isHidden(root, target));
      }

      el.addEventListener("click", toggle);
      el.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
          toggle(event);
        }
      });
    });
  }

  function init() {
    var charts = document.querySelectorAll('svg[data-glyphx="true"]');
    if (charts.length) {
      Array.prototype.forEach.call(charts, bind);
    } else {
      bind(document);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
