<script>
document.addEventListener("DOMContentLoaded", function () {
  // Create a tooltip div that will follow the cursor
  const tooltip = document.createElement("div");
  tooltip.id = "glyphx-tooltip";

  // Style the tooltip for better visibility and aesthetics
  tooltip.style.position = "absolute";
  tooltip.style.background = "white";
  tooltip.style.border = "1px solid #ccc";
  tooltip.style.padding = "4px 8px";
  tooltip.style.borderRadius = "4px";
  tooltip.style.boxShadow = "0 2px 4px rgba(0,0,0,0.1)";
  tooltip.style.fontSize = "12px";
  tooltip.style.pointerEvents = "none";  // allows mouse events to pass through
  tooltip.style.display = "none";        // hidden by default

  // Add the tooltip to the page
  document.body.appendChild(tooltip);

  // Find all chart elements that support hover tooltips
  document.querySelectorAll(".glyphx-point").forEach(el => {
    // When mouse enters a point, build and show the tooltip
    el.addEventListener("mouseenter", e => {
      const x = el.getAttribute("data-x");
      const y = el.getAttribute("data-y");
      const label = el.getAttribute("data-label");
      const val = el.getAttribute("data-value");

      // Build tooltip content using available data
      tooltip.innerHTML =
        `${label ? "<b>" + label + "</b><br/>" : ""}` +
        `${x ? "x: " + x + "<br/>" : ""}` +
        `${y ? "y: " + y : ""}` +
        `${val ? "<br/>Value: " + val : ""}`;

      tooltip.style.display = "block";
    });

    // Update tooltip position as mouse moves
    el.addEventListener("mousemove", e => {
      tooltip.style.left = e.pageX + 10 + "px";
      tooltip.style.top = e.pageY + 10 + "px";
    });

    // Hide tooltip when mouse leaves the element
    el.addEventListener("mouseleave", e => {
      tooltip.style.display = "none";
    });
  });
});
</script>