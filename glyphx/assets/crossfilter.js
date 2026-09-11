/*
 * GlyphX -- cross-chart filtering.
 *
 * Click a bar, point or slice in one chart and every other GlyphX chart on
 * the page dims everything that does not share that x value. Click the same
 * element again, or press Escape, to clear.
 *
 * The wiring is already in the markup: every drawn element carries data-x,
 * so the x value is the join key between charts. Nothing is sent anywhere
 * and no server is involved -- the charts on the page are the whole dataset.
 *
 * Deliberately scoped to data-x. Filtering on data-y would mean matching on
 * a measured value rather than a category, which is almost never what
 * someone means by "show me February".
 */
(function () {
  "use strict";

  var DIM_CLASS = "glyphx-crossfilter-dim";
  var DIM_OPACITY = "0.12";
  var active = null;               // currently selected data-x, or null

  // Charts opt in by carrying data-glyphx-crossfilter on their root <svg>.
  // Anything without it is left alone, so a page can mix filtered and
  // independent charts.
  function participatingRoots() {
    return Array.prototype.slice.call(
      document.querySelectorAll("svg[data-glyphx-crossfilter]")
    );
  }

  function ensureStyle() {
    if (document.getElementById("glyphx-crossfilter-style")) return;
    var style = document.createElement("style");
    style.id = "glyphx-crossfilter-style";
    // A class rather than an inline style, so a re-render or a host
    // stylesheet does not fight the toggle.
    style.textContent =
      "." + DIM_CLASS + " { opacity: " + DIM_OPACITY + "; " +
      "transition: opacity 120ms ease-out; }";
    document.head.appendChild(style);
  }

  function apply(value) {
    participatingRoots().forEach(function (root) {
      var elements = root.querySelectorAll("[data-x]");
      Array.prototype.forEach.call(elements, function (el) {
        if (value === null || el.getAttribute("data-x") === value) {
          el.classList.remove(DIM_CLASS);
        } else {
          el.classList.add(DIM_CLASS);
        }
      });
    });
    announce(value);
  }

  // Screen readers get told what happened; the visual change alone is not
  // an accessible signal.
  function announce(value) {
    var live = document.getElementById("glyphx-crossfilter-status");
    if (!live) {
      live = document.createElement("div");
      live.id = "glyphx-crossfilter-status";
      live.setAttribute("aria-live", "polite");
      live.setAttribute("role", "status");
      live.style.cssText =
        "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);";
      document.body.appendChild(live);
    }
    live.textContent = value === null
      ? "Filter cleared. All data shown."
      : "Filtered to " + value + " across all charts.";
  }

  function select(value) {
    active = (active === value) ? null : value;   // clicking again clears
    apply(active);
  }

  // Capture phase, and stop propagation once handled. interact.js binds a
  // click handler on document too, and its series-highlight sets *inline*
  // opacity, which beats a class rule -- so with both live the two fought:
  // the clicked chart stayed fully lit and the other went uniformly grey.
  // On a crossfilter chart a plain click means "filter", so interact.js
  // should not also see it. Modified clicks fall through untouched, which
  // keeps shift+click opening the inspector.
  document.addEventListener("click", function (e) {
    var el = e.target.closest ? e.target.closest("[data-x]") : null;
    if (!el) return;
    var root = el.closest("svg[data-glyphx-crossfilter]");
    if (!root) return;
    if (e.shiftKey || e.altKey || e.metaKey || e.ctrlKey) return;
    e.stopPropagation();
    select(el.getAttribute("data-x"));
  }, true);

  // Keyboard parity: elements are already focusable with tabindex="0".
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && active !== null) {
      active = null;
      apply(null);
      return;
    }
    if (e.key !== "Enter" && e.key !== " ") return;
    var el = document.activeElement;
    if (!el || !el.getAttribute || !el.getAttribute("data-x")) return;
    if (!el.closest("svg[data-glyphx-crossfilter]")) return;
    e.preventDefault();
    select(el.getAttribute("data-x"));
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureStyle);
  } else {
    ensureStyle();
  }
})();
