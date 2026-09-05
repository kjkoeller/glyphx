document.addEventListener("DOMContentLoaded", function () {
  // The shareable-HTML template already renders styled Download SVG / PNG
  // buttons in its toolbar. Injecting a second, unstyled row above the chart
  // gave every exported file two sets of controls doing the same thing, in
  // two different visual styles. When a toolbar is present, add only the one
  // format it lacks; otherwise render the full row as before, so a bare SVG
  // embedded in someone else's page still gets export controls.
  const toolbar = document.querySelector(".glyphx-toolbar");

  const buttons = document.createElement("div");
  buttons.style.marginBottom = "10px";

  // Helper function to create a styled button with a label and click handler
  function createButton(label, onclick) {
    const btn = document.createElement("button");
    btn.innerText = label;
    btn.style.marginRight = "8px";
    btn.onclick = onclick;
    return btn;
  }

  // Generic export function that converts SVG to image (PNG or JPEG) and triggers download
  function exportImage(type) {
    document.querySelectorAll("svg").forEach((svg, i) => {
      const svgData = new XMLSerializer().serializeToString(svg); // Convert SVG to string
      const canvas = document.createElement("canvas");
      canvas.width = svg.clientWidth;
      canvas.height = svg.clientHeight;
      const ctx = canvas.getContext("2d");
      const img = new Image();

      // When image loads, draw it on canvas and trigger download
      img.onload = () => {
        ctx.drawImage(img, 0, 0);
        const data = canvas.toDataURL("image/" + type);
        const a = document.createElement("a");
        a.href = data;
        a.download = `glyphx_chart_${i}.${type}`; // name the file
        a.click(); // initiate download
      };

      // Convert SVG string to base64-encoded image
      img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgData)));
    });
  }

  // Button for downloading raw SVG files
  const svgBtn = createButton("Download SVG", () => {
    document.querySelectorAll("svg").forEach((svg, i) => {
      const blob = new Blob([svg.outerHTML], {type: "image/svg+xml"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `glyphx_chart_${i}.svg`;
      a.click();
      URL.revokeObjectURL(url); // clean up memory
    });
  });

  // Buttons for exporting as PNG and JPG using canvas conversion
  const pngBtn = createButton("Download PNG", () => exportImage("png"));
  const jpgBtn = createButton("Download JPG", () => exportImage("jpeg"));

  if (toolbar) {
    // Match the toolbar's own button styling rather than the inline styles
    // used for the standalone row.
    jpgBtn.removeAttribute("style");
    jpgBtn.className = "glyphx-btn";
    const shortcuts = toolbar.querySelector(".glyphx-btn:last-child");
    toolbar.insertBefore(jpgBtn, shortcuts);
    return;
  }

  buttons.appendChild(svgBtn);
  buttons.appendChild(pngBtn);
  buttons.appendChild(jpgBtn);
  document.body.insertBefore(buttons, document.body.firstChild);
});
