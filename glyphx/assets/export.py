export_js = """<script>
document.addEventListener("DOMContentLoaded", function () {
  const buttons = document.createElement("div");
  buttons.style.marginBottom = "10px";

  function createButton(label, onclick) {
    const btn = document.createElement("button");
    btn.innerText = label;
    btn.style.marginRight = "8px";
    btn.onclick = onclick;
    return btn;
  }

  function exportImage(type) {
    document.querySelectorAll("svg").forEach((svg, i) => {
      const svgData = new XMLSerializer().serializeToString(svg);
      const canvas = document.createElement("canvas");
      canvas.width = svg.clientWidth;
      canvas.height = svg.clientHeight;
      const ctx = canvas.getContext("2d");
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0);
        const data = canvas.toDataURL("image/" + type);
        const a = document.createElement("a");
        a.href = data;
        a.download = `glyphx_chart_${i}.${type}`;
        a.click();
      };
      img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));
    });
  }

  const svgBtn = createButton("Download SVG", () => {
    document.querySelectorAll("svg").forEach((svg, i) => {
      const blob = new Blob([svg.outerHTML], {type: "image/svg+xml"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `glyphx_chart_${i}.svg`;
      a.click();
      URL.revokeObjectURL(url);
    });
  });

  const pngBtn = createButton("Download PNG", () => exportImage("png"));
  const jpgBtn = createButton("Download JPG", () => exportImage("jpeg"));

  buttons.appendChild(svgBtn);
  buttons.appendChild(pngBtn);
  buttons.appendChild(jpgBtn);
  document.body.insertBefore(buttons, document.body.firstChild);
});
</script>"""