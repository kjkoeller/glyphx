<script>
(function() {
  // Select the first <svg> element on the page
  const svg = document.querySelector("svg");
  if (!svg) return;  // Exit if no SVG is found

  // Parse the initial viewBox attribute into numeric values: [x, y, width, height]
  let viewBox = svg.getAttribute("viewBox").split(" ").map(Number);

  // State variables for panning
  let isPanning = false;
  let start = { x: 0, y: 0 };
  let end = { x: 0, y: 0 };

  // Set default cursor for the SVG element
  svg.style.cursor = "grab";

  // Begin panning on mouse down
  svg.addEventListener("mousedown", (e) => {
    isPanning = true;
    start = { x: e.clientX, y: e.clientY };
    svg.style.cursor = "grabbing";
  });

  // Update the viewBox as the mouse moves during panning
  svg.addEventListener("mousemove", (e) => {
    if (!isPanning) return;

    end = { x: e.clientX, y: e.clientY };

    // Convert screen-space movement into SVG units
    const dx = (end.x - start.x) * (viewBox[2] / svg.clientWidth);
    const dy = (end.y - start.y) * (viewBox[3] / svg.clientHeight);

    // Adjust viewBox origin based on movement
    viewBox[0] -= dx;
    viewBox[1] -= dy;

    // Apply updated viewBox
    svg.setAttribute("viewBox", viewBox.join(" "));

    // Update starting point for next frame
    start = { ...end };
  });

  // End panning on mouse up
  svg.addEventListener("mouseup", () => {
    isPanning = false;
    svg.style.cursor = "grab";
  });

  // Cancel panning if mouse leaves the SVG area
  svg.addEventListener("mouseleave", () => {
    isPanning = false;
    svg.style.cursor = "grab";
  });

  // Zoom in/out on mouse wheel scroll
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();

    const zoomFactor = 1.1;
    const scale = e.deltaY > 0 ? zoomFactor : 1 / zoomFactor;

    const [x, y, w, h] = viewBox;

    // Compute new dimensions for the zoom
    const newW = w * scale;
    const newH = h * scale;

    // Determine mouse position as a fraction of the SVG size
    const mx = e.offsetX / svg.clientWidth;
    const my = e.offsetY / svg.clientHeight;

    // Adjust the viewBox origin to zoom around the mouse pointer
    const newX = x + mx * (w - newW);
    const newY = y + my * (h - newH);

    // Update the viewBox values
    viewBox = [newX, newY, newW, newH];
    svg.setAttribute("viewBox", viewBox.join(" "));
  });
})();
</script>