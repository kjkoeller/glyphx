tooltip_js = """document.addEventListener("DOMContentLoaded", function () {
  const tooltip = document.createElement("div");
  tooltip.id = "glyphx-tooltip";
  tooltip.style.position = "absolute";
  tooltip.style.background = "white";
  tooltip.style.border = "1px solid #ccc";
  tooltip.style.padding = "4px 8px";
  tooltip.style.borderRadius = "4px";
  tooltip.style.boxShadow = "0 2px 4px rgba(0,0,0,0.1)";
  tooltip.style.fontSize = "12px";
  tooltip.style.pointerEvents = "none";
  tooltip.style.display = "none";
  document.body.appendChild(tooltip);

  document.querySelectorAll(".glyphx-point").forEach(el => {
    el.addEventListener("mouseenter", e => {
      const x = el.getAttribute("data-x");
      const y = el.getAttribute("data-y");
      const label = el.getAttribute("data-label");
      const val = el.getAttribute("data-value");
      tooltip.innerHTML = `${label ? "<b>" + label + "</b><br/>" : ""}${x ? "x: " + x + "<br/>" : ""}${y ? "y: " + y : ""}${val ? "Value: " + val : ""}`;
      tooltip.style.display = "block";
    });
    el.addEventListener("mousemove", e => {
      tooltip.style.left = e.pageX + 10 + "px";
      tooltip.style.top = e.pageY + 10 + "px";
    });
    el.addEventListener("mouseleave", e => {
      tooltip.style.display = "none";
    });
  });
});"""