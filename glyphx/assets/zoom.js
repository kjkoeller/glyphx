// Enable panning and zooming on the first <svg> element
(function() {
  const svg = document.querySelector("svg");
  if (!svg) return;

  // Parse initial viewBox into x, y, width, height
  let viewBox = svg.getAttribute("viewBox").split(" ").map(Number);

  let isPanning = false;
  let start = { x: 0, y: 0 };
  let end = { x: 0, y: 0 };

  svg.style.cursor = "grab";

  // Start panning
  svg.addEventListener("mousedown", (e) => {
    isPanning = true;
    start = { x: e.clientX, y: e.clientY };
    svg.style.cursor = "grabbing";
  });

  // Update viewBox while moving
  svg.addEventListener("mousemove", (e) => {
    if (!isPanning) return;

    end = { x: e.clientX, y: e.clientY };
    const dx = (end.x - start.x) * (viewBox[2] / svg.clientWidth);
    const dy = (end.y - start.y) * (viewBox[3] / svg.clientHeight);

    viewBox[0] -= dx;
    viewBox[1] -= dy;

    svg.setAttribute("viewBox", viewBox.join(" "));
    start = { ...end };
  });

  // End panning
  svg.addEventListener("mouseup", () => {
    isPanning = false;
    svg.style.cursor = "grab";
  });

  // Stop panning if mouse leaves area
  svg.addEventListener("mouseleave", () => {
    isPanning = false;
    svg.style.cursor = "grab";
  });

  // Mouse wheel zoom
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = 1.1;
    const scale = e.deltaY > 0 ? zoomFactor : 1 / zoomFactor;

    const [x, y, w, h] = viewBox;
    const newW = w * scale;
    const newH = h * scale;

    const mx = e.offsetX / svg.clientWidth;
    const my = e.offsetY / svg.clientHeight;

    const newX = x + mx * (w - newW);
    const newY = y + my * (h - newH);

    viewBox = [newX, newY, newW, newH];
    svg.setAttribute("viewBox", viewBox.join(" "));
  });
})();
