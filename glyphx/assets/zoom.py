zoom_js = """<script>
document.addEventListener("DOMContentLoaded", function () {
  const svgs = document.querySelectorAll("svg");
  svgs.forEach(svg => {
    let viewBox = svg.getAttribute("viewBox") || "0 0 " + svg.clientWidth + " " + svg.clientHeight;
    let [x, y, w, h] = viewBox.split(" ").map(Number);
    svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);

    let isPanning = false, startX = 0, startY = 0, origX = x, origY = y;

    svg.addEventListener("mousedown", e => {
      isPanning = true;
      startX = e.clientX;
      startY = e.clientY;
      origX = x;
      origY = y;
    });

    svg.addEventListener("mousemove", e => {
      if (!isPanning) return;
      const dx = (e.clientX - startX) * (w / svg.clientWidth);
      const dy = (e.clientY - startY) * (h / svg.clientHeight);
      svg.setAttribute("viewBox", `${origX - dx} ${origY - dy} ${w} ${h}`);
    });

    svg.addEventListener("mouseup", () => isPanning = false);
    svg.addEventListener("mouseleave", () => isPanning = false);

    svg.addEventListener("wheel", e => {
      e.preventDefault();
      const scale = e.deltaY < 0 ? 0.9 : 1.1;
      const mx = e.offsetX * (w / svg.clientWidth);
      const my = e.offsetY * (h / svg.clientHeight);
      x += mx * (1 - scale);
      y += my * (1 - scale);
      w *= scale;
      h *= scale;
      svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
    });
  });
});
</script>"""