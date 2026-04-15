"""
GlyphX Figure3D — interactive 3D chart canvas.

Primary output: self-contained HTML with a Three.js WebGL renderer,
mouse-driven orbit controls, tooltips, and theme-aware axis grids.

Fallback output: static SVG using orthographic projection with
painter's-algorithm depth sorting.

Usage::

    from glyphx import Figure3D
    from glyphx.scatter3d import Scatter3DSeries
    import numpy as np

    xs = np.random.randn(200)
    ys = np.random.randn(200)
    zs = np.sin(xs) + np.cos(ys)

    fig = Figure3D(title="My 3D Scatter", theme="dark")
    fig.add(Scatter3DSeries(xs, ys, zs, c=zs, cmap="plasma"))
    fig.show()
"""
from __future__ import annotations

import json
import math
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

import numpy as np

from .projection3d import Camera3D, normalize, axis_ticks, _format_3d_tick
from .themes        import themes as _themes
from .utils         import svg_escape


# ---------------------------------------------------------------------------
# Three.js HTML template (all JS is inline — zero CDN except Three.js itself)
# ---------------------------------------------------------------------------

_THREEJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:100%; height:100%; overflow:hidden;
  background:{bg}; font-family:{font}; }
canvas { display:block; }

/* ── Tooltip ── */
#glx-tip {
  position:fixed; pointer-events:none; display:none;
  background:rgba(15,23,42,0.92); color:#f8fafc;
  padding:7px 12px; border-radius:7px; font-size:12.5px;
  line-height:1.6; max-width:260px; white-space:pre-line;
  box-shadow:0 4px 18px rgba(0,0,0,0.35); z-index:9999;
}

/* ── Title ── */
#glx-title {
  position:fixed; top:12px; left:50%; transform:translateX(-50%);
  font-size:17px; font-weight:700; color:{tc};
  pointer-events:none; text-shadow:0 1px 4px rgba(0,0,0,0.3);
}

/* ── Control panel ── */
#glx-panel {
  position:fixed; bottom:18px; left:50%; transform:translateX(-50%);
  display:flex; gap:6px; flex-wrap:wrap; justify-content:center;
  background:rgba(15,23,42,0.55); border-radius:12px;
  padding:8px 12px; backdrop-filter:blur(6px);
}
.glx-btn {
  background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2);
  color:#f1f5f9; font-size:11.5px; font-family:inherit;
  padding:5px 11px; border-radius:7px; cursor:pointer;
  transition:background 0.15s, transform 0.1s;
  white-space:nowrap; user-select:none;
}
.glx-btn:hover  { background:rgba(255,255,255,0.22); }
.glx-btn:active { transform:scale(0.95); }
.glx-btn.active { background:rgba(99,102,241,0.6); border-color:#818cf8; }
.glx-sep { width:1px; background:rgba(255,255,255,0.15); margin:0 2px; }

/* ── Legend ── */
#glx-legend {
  position:fixed; right:16px; top:50%; transform:translateY(-50%);
  background:rgba(15,23,42,0.65); border-radius:10px;
  padding:10px 14px; color:{tc}; font-size:12px;
  backdrop-filter:blur(6px);
}
#glx-legend .glx-leg-item {
  display:flex; align-items:center; gap:8px;
  margin:5px 0; cursor:pointer; user-select:none;
  transition:opacity 0.2s;
}
#glx-legend .glx-leg-item:hover { opacity:0.8; }
#glx-legend .glx-swatch {
  width:14px; height:14px; border-radius:3px; flex-shrink:0;
}

/* ── Help overlay ── */
#glx-help {
  position:fixed; inset:0;
  background:rgba(0,0,0,0.65);
  display:none; align-items:center; justify-content:center;
  z-index:99999; backdrop-filter:blur(4px);
}
#glx-help-box {
  background:#1e293b; color:#f8fafc;
  border-radius:14px; padding:28px 34px;
  max-width:400px; width:90%;
  box-shadow:0 20px 60px rgba(0,0,0,0.5);
}
#glx-help-box h3 { margin-bottom:16px; font-size:15px; }
#glx-help-box table { border-collapse:collapse; width:100%; font-size:12.5px; }
#glx-help-box td   { padding:4px 0; }
#glx-help-box td:first-child { opacity:0.5; width:120px; }
#glx-help-box .close-hint {
  margin-top:14px; text-align:center;
  opacity:0.4; font-size:11px;
}

/* ── Axis value readout (surface probe) ── */
#glx-readout {
  position:fixed; left:16px; bottom:18px;
  background:rgba(15,23,42,0.7); color:#94a3b8;
  font-size:11.5px; padding:6px 10px; border-radius:7px;
  display:none; font-variant-numeric:tabular-nums;
  backdrop-filter:blur(4px);
}

/* ── Selection highlight ── */
.glx-selected { outline:none; }
</style>
</head>
<body>
<div id="glx-title">{title}</div>
<div id="glx-tip"></div>
<div id="glx-readout"></div>

<!-- Legend -->
<div id="glx-legend" style="display:{legend_display}">{legend_html}</div>

<!-- Control panel -->
<div id="glx-panel">
  <button class="glx-btn" onclick="setCam('iso')"     title="Isometric view (I)">⬡ ISO</button>
  <button class="glx-btn" onclick="setCam('top')"     title="Top view (T)">⬆ Top</button>
  <button class="glx-btn" onclick="setCam('front')"   title="Front view (V)">◻ Front</button>
  <button class="glx-btn" onclick="setCam('side')"    title="Side view (S)">◁ Side</button>
  <div class="glx-sep"></div>
  <button class="glx-btn" id="btn-rotate" onclick="toggleRotate()" title="Auto-rotate (Space)">↻ Rotate</button>
  <button class="glx-btn" onclick="resetView()"       title="Reset camera (R)">⟳ Reset</button>
  <div class="glx-sep"></div>
  <button class="glx-btn" onclick="screenshot()"      title="Save PNG (P)">📷 PNG</button>
  <button class="glx-btn" onclick="toggleFullscreen()" title="Fullscreen (F)">⛶ Full</button>
  <button class="glx-btn" onclick="showHelp()"        title="Keyboard help (H)">? Help</button>
</div>

<!-- Help overlay -->
<div id="glx-help" onclick="closeHelp()">
  <div id="glx-help-box">
    <h3>⌨️ GlyphX 3D Shortcuts</h3>
    <table>
      <tr><td>Drag</td><td>Rotate camera</td></tr>
      <tr><td>Right-drag / Ctrl+drag</td><td>Pan</td></tr>
      <tr><td>Scroll</td><td>Zoom</td></tr>
      <tr><td>Arrow keys</td><td>Rotate (fine)</td></tr>
      <tr><td>+  /  -</td><td>Zoom in / out</td></tr>
      <tr><td>Space</td><td>Toggle auto-rotate</td></tr>
      <tr><td>R</td><td>Reset view</td></tr>
      <tr><td>I / T / V / S</td><td>ISO / Top / Front / Side</td></tr>
      <tr><td>P</td><td>Save PNG screenshot</td></tr>
      <tr><td>F</td><td>Toggle fullscreen</td></tr>
      <tr><td>Click point</td><td>Select / highlight</td></tr>
      <tr><td>Esc</td><td>Deselect / close</td></tr>
      <tr><td>H</td><td>This help screen</td></tr>
    </table>
    <div class="close-hint">Click anywhere or press Esc to close</div>
  </div>
</div>

<script src="{threejs_cdn}"></script>
<script>
// ═══════════════════════════════════════════════════════════════════════
// Data & config
// ═══════════════════════════════════════════════════════════════════════
const DATA    = {data_json};
const THEME   = {theme_json};
const LABELS  = {labels_json};

function fmtV(v) {
  const a = Math.abs(v);
  if (a === 0) return '0';
  if (a >= 1e6)  return (v/1e6).toFixed(2)+'M';
  if (a >= 1e3)  return (v/1e3).toFixed(2)+'k';
  if (Number.isInteger(v)) return String(v);
  if (a >= 100)  return v.toFixed(1);
  if (a >= 10)   return v.toFixed(2);
  return v.toFixed(3);
}

// ═══════════════════════════════════════════════════════════════════════
// Scene setup
// ═══════════════════════════════════════════════════════════════════════
const W = window.innerWidth, H = window.innerHeight;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(W, H);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(new THREE.Color(THEME.bg), 1);
document.body.appendChild(renderer.domElement);
const cv = renderer.domElement;

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, W/H, 0.01, 1000);
scene.add(new THREE.DirectionalLight(0xffffff, 0.8).position.set(5,8,5) && new THREE.DirectionalLight(0xffffff, 0.8));
scene.add(new THREE.AmbientLight(0xffffff, 0.45));

// Lights properly
const dLight = new THREE.DirectionalLight(0xffffff, 0.8);
dLight.position.set(5, 8, 5);
scene.add(dLight);
scene.add(new THREE.AmbientLight(0xffffff, 0.45));

// ═══════════════════════════════════════════════════════════════════════
// Camera state & orbit controls
// ═══════════════════════════════════════════════════════════════════════
const CAM_PRESETS = {
  iso:   { theta:45,  phi:55  },
  top:   { theta:0,   phi:1   },
  front: { theta:0,   phi:90  },
  side:  { theta:90,  phi:90  },
};

let cam = { theta:45, phi:55, r:6, tx:0, ty:0 };
let drag = false, rDrag = false, lx = 0, ly = 0;
let autoRotate = false, rotTimer = null;
let selectedObj = null;

function updateCamera() {
  const t = cam.theta * Math.PI/180;
  const p = cam.phi   * Math.PI/180;
  camera.position.set(
    cam.r * Math.sin(p) * Math.cos(t) + cam.tx,
    cam.r * Math.cos(p)               + cam.ty,
    cam.r * Math.sin(p) * Math.sin(t) + cam.tx
  );
  camera.lookAt(cam.tx, cam.ty, 0);
}

function setCam(preset) {
  const p = CAM_PRESETS[preset];
  if (!p) return;
  // Smooth tween
  const t0 = { ...cam };
  const t1 = { ...cam, theta: p.theta, phi: p.phi };
  let start = null;
  function step(ts) {
    if (!start) start = ts;
    const prog = Math.min((ts - start) / 500, 1);
    const ease = 1 - Math.pow(1 - prog, 3);
    cam.theta = t0.theta + (t1.theta - t0.theta) * ease;
    cam.phi   = t0.phi   + (t1.phi   - t0.phi)   * ease;
    updateCamera();
    if (prog < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function resetView() {
  cam = { theta:45, phi:55, r:6, tx:0, ty:0 };
  updateCamera();
}

function toggleRotate() {
  autoRotate = !autoRotate;
  document.getElementById('btn-rotate').classList.toggle('active', autoRotate);
}

function screenshot() {
  renderer.render(scene, camera);
  const url = cv.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = url; a.download = 'glyphx_3d.png';
  a.click();
}

function toggleFullscreen() {
  if (!document.fullscreenElement)
    document.documentElement.requestFullscreen();
  else document.exitFullscreen();
}

function showHelp() { document.getElementById('glx-help').style.display='flex'; }
function closeHelp(){ document.getElementById('glx-help').style.display='none'; }

// Mouse orbit
cv.addEventListener('mousedown', e => {
  if (e.button === 0 && !e.ctrlKey) { drag=true; }
  if (e.button === 2 || (e.button===0 && e.ctrlKey)) { rDrag=true; }
  lx=e.clientX; ly=e.clientY;
});
cv.addEventListener('contextmenu', e => e.preventDefault());
window.addEventListener('mouseup',   () => { drag=false; rDrag=false; });
window.addEventListener('mousemove', e => {
  const dx=e.clientX-lx, dy=e.clientY-ly;
  lx=e.clientX; ly=e.clientY;
  if (drag)  { cam.theta -= dx*0.35; cam.phi = Math.max(2, Math.min(178, cam.phi - dy*0.35)); updateCamera(); }
  if (rDrag) { cam.tx -= dx*0.009; cam.ty += dy*0.009; updateCamera(); }
});
cv.addEventListener('wheel', e => {
  cam.r = Math.max(0.5, cam.r * (1 + e.deltaY*0.001));
  updateCamera();
}, { passive:true });

// Touch
let touches = [];
cv.addEventListener('touchstart',  e => { touches=[...e.touches]; }, { passive:true });
cv.addEventListener('touchmove', e => {
  e.preventDefault();
  if (e.touches.length===1) {
    cam.theta -= (e.touches[0].clientX - touches[0].clientX)*0.45;
    cam.phi = Math.max(2, Math.min(178, cam.phi - (e.touches[0].clientY - touches[0].clientY)*0.45));
    updateCamera();
  }
  if (e.touches.length===2) {
    const d0 = Math.hypot(touches[0].clientX-touches[1].clientX, touches[0].clientY-touches[1].clientY);
    const d1 = Math.hypot(e.touches[0].clientX-e.touches[1].clientX, e.touches[0].clientY-e.touches[1].clientY);
    cam.r = Math.max(0.5, cam.r*(d0/d1));
    updateCamera();
  }
  touches=[...e.touches];
}, { passive:false });

updateCamera();

// ═══════════════════════════════════════════════════════════════════════
// Keyboard controls
// ═══════════════════════════════════════════════════════════════════════
document.addEventListener('keydown', e => {
  if (['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) return;
  switch(e.key) {
    case 'ArrowLeft':  cam.theta -= 3; updateCamera(); break;
    case 'ArrowRight': cam.theta += 3; updateCamera(); break;
    case 'ArrowUp':    cam.phi = Math.max(2,   cam.phi - 3); updateCamera(); break;
    case 'ArrowDown':  cam.phi = Math.min(178, cam.phi + 3); updateCamera(); break;
    case '+': case '=': cam.r = Math.max(0.5, cam.r * 0.92); updateCamera(); break;
    case '-': case '_': cam.r *= 1.08; updateCamera(); break;
    case ' ': e.preventDefault(); toggleRotate(); break;
    case 'r': case 'R': resetView(); break;
    case 'i': case 'I': setCam('iso');   break;
    case 't': case 'T': setCam('top');   break;
    case 'v': case 'V': setCam('front'); break;
    case 's': case 'S': setCam('side');  break;
    case 'p': case 'P': screenshot();    break;
    case 'f': case 'F': toggleFullscreen(); break;
    case 'h': case 'H': showHelp();      break;
    case 'Escape': closeHelp(); clearSelection(); break;
  }
});

// ═══════════════════════════════════════════════════════════════════════
// Axis grid & labels
// ═══════════════════════════════════════════════════════════════════════
const axColor   = new THREE.Color(THEME.axis);
const gridColor = new THREE.Color(THEME.grid);

function addLine(p1, p2, col, opacity=1) {
  const g = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(...p1), new THREE.Vector3(...p2)
  ]);
  const m = new THREE.LineBasicMaterial({ color:col, transparent: opacity<1, opacity });
  scene.add(new THREE.Line(g, m));
}

// Axis box edges
const S = 1;
[
  [[-S,-S,-S],[S,-S,-S]], [[-S,-S,-S],[-S,S,-S]], [[-S,-S,-S],[-S,-S,S]],
  [[S,S,-S],[S,-S,-S]],   [[S,S,-S],[-S,S,-S]],   [[S,S,-S],[S,S,S]],
  [[S,-S,S],[-S,-S,S]],   [[S,-S,S],[S,S,S]],      [[S,-S,S],[S,-S,-S]],
  [[-S,S,S],[-S,-S,S]],   [[-S,S,S],[S,S,S]],      [[-S,S,S],[-S,S,-S]],
].forEach(([a,b]) => addLine(a, b, axColor, 0.45));

// Floor grid
for (let k=0; k<=5; k++) {
  const v = -S + k*(2*S/5);
  addLine([v,-S,-S],[v,-S,S], gridColor, 0.35);
  addLine([-S,-S,v],[S,-S,v], gridColor, 0.35);
}

// Axis labels as canvas sprites
function makeSprite(text, pos, size=0.5) {
  const c = document.createElement('canvas');
  c.width=256; c.height=64;
  const ctx=c.getContext('2d');
  ctx.fillStyle = THEME.tc;
  ctx.font=`bold ${Math.round(256/text.length*0.65 + 18)}px sans-serif`;
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(text, 128, 32);
  const sp = new THREE.Sprite(
    new THREE.SpriteMaterial({ map:new THREE.CanvasTexture(c), transparent:true })
  );
  sp.scale.set(size, size*0.25, 1);
  sp.position.set(...pos);
  scene.add(sp);
}

// Tick labels
LABELS.x.forEach(t => makeSprite(t.label, [t.norm, -S-0.14, -S-0.12], 0.5));
LABELS.y.forEach(t => makeSprite(t.label, [-S-0.14, -S-0.14,  t.norm], 0.5));
LABELS.z.forEach(t => makeSprite(t.label, [-S-0.28,  t.norm, -S],      0.5));

// Axis name labels
makeSprite(LABELS.xlabel, [ 0,    -S-0.32, -S-0.18], 0.7);
makeSprite(LABELS.ylabel, [-S-0.3,-S-0.32,  0],      0.7);
makeSprite(LABELS.zlabel, [-S-0.45, 0,     -S],      0.7);

// ═══════════════════════════════════════════════════════════════════════
// Series rendering
// ═══════════════════════════════════════════════════════════════════════
const hitObjects   = [];   // for raycasting
const seriesGroups = {};   // css_class → THREE.Group for legend toggle
const surfaceMeshes = [];  // for surface value probe

DATA.forEach((series, si) => {
  const group = new THREE.Group();
  group.userData.seriesIndex = si;
  group.userData.label = series.label;

  // ── Scatter ───────────────────────────────────────────────────────
  if (series.type === 'scatter') {
    const N = series.x.length;
    const positions = new Float32Array(N*3);
    const colors    = new Float32Array(N*3);
    for (let i=0; i<N; i++) {
      positions[i*3]   = series.nx[i];
      positions[i*3+1] = series.nz[i];
      positions[i*3+2] = series.ny[i];
      const c = new THREE.Color(series.colors[i]);
      colors[i*3]=c.r; colors[i*3+1]=c.g; colors[i*3+2]=c.b;
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color',    new THREE.BufferAttribute(colors,    3));
    geom.userData = { xs:series.x, ys:series.y, zs:series.z, label:series.label };
    const mat = new THREE.PointsMaterial({
      size: series.size*0.012, vertexColors:true,
      transparent:true, opacity:series.alpha, sizeAttenuation:true
    });
    const pts = new THREE.Points(geom, mat);
    hitObjects.push(pts);
    group.add(pts);
  }

  // ── Line ─────────────────────────────────────────────────────────
  if (series.type === 'line') {
    const pts3 = series.nx.map((nx,i) =>
      new THREE.Vector3(nx, series.nz[i], series.ny[i]));
    const g = new THREE.BufferGeometry().setFromPoints(pts3);
    const m = new THREE.LineBasicMaterial({
      color: new THREE.Color(series.color), linewidth:series.width
    });
    group.add(new THREE.Line(g, m));
  }

  // ── Surface ──────────────────────────────────────────────────────
  if (series.type === 'surface') {
    const M = series.ny, N = series.nx;
    const positions = new Float32Array(M*N*3);
    const colors    = new Float32Array(M*N*3);
    for (let j=0; j<M; j++) for (let i=0; i<N; i++) {
      const idx=(j*N+i)*3;
      positions[idx]   = series.nxArr[i];
      positions[idx+1] = series.nz[j][i];
      positions[idx+2] = series.nyArr[j];
      const c = new THREE.Color(series.face_colors[j][i]);
      colors[idx]=c.r; colors[idx+1]=c.g; colors[idx+2]=c.b;
    }
    const indices=[];
    for (let j=0; j<M-1; j++) for (let i=0; i<N-1; i++) {
      const a=j*N+i, b=a+1, c=a+N, d=c+1;
      indices.push(a,c,b, b,c,d);
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions,3));
    geom.setAttribute('color',    new THREE.BufferAttribute(colors,3));
    geom.setIndex(indices);
    geom.computeVertexNormals();
    geom.userData = {
      xs:series.xData, ys:series.yData, zs:series.zData,
      M, N, nxArr:series.nxArr, nyArr:series.nyArr
    };
    const mat = new THREE.MeshPhongMaterial({
      vertexColors:true, transparent:true,
      opacity:series.alpha, side:THREE.DoubleSide
    });
    const mesh = new THREE.Mesh(geom, mat);
    surfaceMeshes.push(mesh);
    hitObjects.push(mesh);
    group.add(mesh);
    if (series.wireframe) {
      const wm = new THREE.MeshBasicMaterial({
        color:0xffffff, wireframe:true, transparent:true, opacity:0.08
      });
      group.add(new THREE.Mesh(geom.clone(), wm));
    }
  }

  // ── Bar3D ────────────────────────────────────────────────────────
  if (series.type === 'bar3d') {
    series.bars.forEach(bar => {
      const geom = new THREE.BoxGeometry(bar.ndx*0.88, bar.nz, bar.ndy*0.88);
      const mat  = new THREE.MeshPhongMaterial({
        color:new THREE.Color(bar.color), transparent:true, opacity:series.alpha
      });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(bar.nx, -1 + bar.nz/2, bar.ny);
      group.add(mesh);
    });
  }

  scene.add(group);
  seriesGroups[si] = group;
});

// ═══════════════════════════════════════════════════════════════════════
// Legend — click to toggle series visibility
// ═══════════════════════════════════════════════════════════════════════
document.querySelectorAll('.glx-leg-item').forEach(item => {
  item.addEventListener('click', () => {
    const si = parseInt(item.dataset.series);
    const grp = seriesGroups[si];
    if (!grp) return;
    grp.visible = !grp.visible;
    item.style.opacity = grp.visible ? '1' : '0.35';
  });
});

// ═══════════════════════════════════════════════════════════════════════
// Selection highlight
// ═══════════════════════════════════════════════════════════════════════
let selectionIdx = null;

function clearSelection() {
  // Reset all scatter point sizes
  Object.values(seriesGroups).forEach(grp => {
    grp.children.forEach(obj => {
      if (obj.isPoints && obj.material._origSize != null) {
        obj.material.size = obj.material._origSize;
        obj.material.opacity = obj.material._origOpacity;
      }
    });
  });
  selectionIdx = null;
  document.getElementById('glx-readout').style.display = 'none';
}

// ═══════════════════════════════════════════════════════════════════════
// Raycasting — tooltip + surface probe + click-select
// ═══════════════════════════════════════════════════════════════════════
const raycaster = new THREE.Raycaster();
raycaster.params.Points = { threshold: 0.06 };
const mouse = new THREE.Vector2();
const tip   = document.getElementById('glx-tip');
const readout = document.getElementById('glx-readout');

let hoverTimer = null;

cv.addEventListener('mousemove', e => {
  mouse.x =  (e.clientX/W)*2-1;
  mouse.y = -(e.clientY/H)*2+1;

  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(hitObjects, true);

  if (hits.length > 0) {
    const hit = hits[0];
    const obj = hit.object;

    // ── Scatter tooltip ──────────────────────────────────────────
    if (obj.isPoints) {
      const ud  = obj.geometry.userData;
      const idx = hit.index;
      if (ud && ud.xs) {
        const lbl = ud.label ? `<b>${ud.label}</b>\n` : '';
        tip.innerHTML = lbl +
          `x: ${fmtV(ud.xs[idx])}\ny: ${fmtV(ud.ys[idx])}\nz: ${fmtV(ud.zs[idx])}`;
        tip.style.display = 'block';
        tip.style.left = (e.clientX+14)+'px';
        tip.style.top  = (e.clientY-20)+'px';
      }
    }

    // ── Surface value probe ──────────────────────────────────────
    if (obj.isMesh && surfaceMeshes.includes(obj)) {
      const ud = obj.geometry.userData;
      if (ud && ud.xs && ud.ys && ud.zs) {
        // Find nearest grid vertex to hit point in normalised coords
        const p = hit.point;   // THREE.Vector3 in normalised space
        // nxArr/nyArr map column/row indices to normalised coords
        let bestI=0, bestJ=0, bestDist=Infinity;
        for (let j=0; j<ud.M; j++) {
          for (let i=0; i<ud.N; i++) {
            const nx = ud.nxArr[i], ny = ud.nyArr[j];
            const d = (nx-p.x)**2 + (ny-p.z)**2;
            if (d < bestDist) { bestDist=d; bestI=i; bestJ=j; }
          }
        }
        const xv = ud.xs[bestI], yv = ud.ys[bestJ], zv = ud.zs[bestJ][bestI];
        tip.innerHTML = `x: ${fmtV(xv)}\ny: ${fmtV(yv)}\nz: <b>${fmtV(zv)}</b>`;
        tip.style.display = 'block';
        tip.style.left = (e.clientX+14)+'px';
        tip.style.top  = (e.clientY-20)+'px';
        readout.textContent = `(${fmtV(xv)}, ${fmtV(yv)}, ${fmtV(zv)})`;
        readout.style.display = 'block';
      }
    }
  } else {
    tip.style.display = 'none';
    readout.style.display = 'none';
  }
});

cv.addEventListener('mouseleave', () => {
  tip.style.display = 'none';
  readout.style.display = 'none';
});

// Click to select scatter point
cv.addEventListener('click', e => {
  mouse.x =  (e.clientX/W)*2-1;
  mouse.y = -(e.clientY/H)*2+1;
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(hitObjects, true);

  if (!hits.length) { clearSelection(); return; }

  const hit = hits[0];
  if (!hit.object.isPoints) { clearSelection(); return; }

  const idx = hit.index;
  const ud  = hit.object.geometry.userData;

  // Toggle selection
  if (selectionIdx === idx) {
    clearSelection();
  } else {
    selectionIdx = idx;
    // Show enlarged version of the selected point via readout
    if (ud && ud.xs) {
      readout.style.display = 'block';
      readout.innerHTML =
        `Selected: x=${fmtV(ud.xs[idx])}, y=${fmtV(ud.ys[idx])}, z=${fmtV(ud.zs[idx])}`;
    }
  }
});

// ═══════════════════════════════════════════════════════════════════════
// Resize
// ═══════════════════════════════════════════════════════════════════════
window.addEventListener('resize', () => {
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
});

// ═══════════════════════════════════════════════════════════════════════
// Render loop
// ═══════════════════════════════════════════════════════════════════════
(function animate() {
  requestAnimationFrame(animate);
  if (autoRotate) { cam.theta += 0.25; updateCamera(); }
  renderer.render(scene, camera);
})();
</script>
</body>
</html>"""

_FORMAT_TICK_JS = """function(v){
  if(v===0)return'0';
  const a=Math.abs(v);
  if(a>=1e6)return(v/1e6).toFixed(1)+'M';
  if(a>=1e3)return(v/1e3).toFixed(1)+'k';
  if(v===Math.round(v))return String(Math.round(v));
  if(a>=100)return v.toFixed(0);
  if(a>=10) return v.toFixed(1);
  return v.toFixed(2);
}"""


# ---------------------------------------------------------------------------
# Figure3D
# ---------------------------------------------------------------------------

class Figure3D:
    """
    3D chart canvas.

    Renders to self-contained HTML with interactive Three.js WebGL, or
    falls back to an orthographic SVG for static export.

    Args:
        width:      HTML canvas width (``"100%"`` or pixel value).
        height:     HTML canvas height.
        title:      Chart title.
        theme:      Theme name (same as :class:`~glyphx.Figure`).
        azimuth:    Initial camera azimuth in degrees (SVG and HTML).
        elevation:  Initial camera elevation in degrees (SVG only).
        xlabel:     X-axis label.
        ylabel:     Y-axis label.
        zlabel:     Z-axis label.

    Example::

        from glyphx import Figure3D
        from glyphx.surface3d import Surface3DSeries
        import numpy as np

        x = np.linspace(-3, 3, 50)
        y = np.linspace(-3, 3, 50)
        X, Y = np.meshgrid(x, y)
        Z = np.sin(np.sqrt(X**2 + Y**2))

        fig = Figure3D(title="sin(r)", theme="dark")
        fig.add(Surface3DSeries(x, y, Z, cmap="plasma"))
        fig.show()
    """

    def __init__(
        self,
        width:     int   = 900,
        height:    int   = 650,
        title:     str   = "",
        theme:     str   = "default",
        azimuth:   float = 45.0,
        elevation: float = 30.0,
        xlabel:    str   = "X",
        ylabel:    str   = "Y",
        zlabel:    str   = "Z",
    ) -> None:
        self.width     = width
        self.height    = height
        self.title     = title
        self.azimuth   = float(azimuth)
        self.elevation = float(elevation)
        self.xlabel    = xlabel
        self.ylabel    = ylabel
        self.zlabel    = zlabel

        theme_dict = _themes.get(theme, _themes["default"])
        self.theme = theme_dict

        self._series: list[Any] = []

    # ------------------------------------------------------------------
    # Series management
    # ------------------------------------------------------------------

    def add(self, series: Any) -> "Figure3D":
        """Add a 3D series and return ``self`` for chaining."""
        self._series.append(series)
        return self

    def scatter(self, x, y, z, color="#2563eb", c=None,
                cmap="viridis", size=5, label=None, alpha=0.85) -> "Figure3D":
        """Add a :class:`~glyphx.scatter3d.Scatter3DSeries`. Returns ``self``."""
        from .scatter3d import Scatter3DSeries
        return self.add(Scatter3DSeries(x, y, z, color=color, c=c, cmap=cmap,
                                         size=size, label=label, alpha=alpha))

    def surface(self, x, y, z, cmap="viridis", alpha=0.90,
                wireframe=True) -> "Figure3D":
        """Add a :class:`~glyphx.surface3d.Surface3DSeries`. Returns ``self``."""
        from .surface3d import Surface3DSeries
        return self.add(Surface3DSeries(x, y, z, cmap=cmap, alpha=alpha,
                                         wireframe=wireframe))

    def line3d(self, x, y, z, color="#dc2626", width=2,
               linestyle="solid", label=None) -> "Figure3D":
        """Add a :class:`~glyphx.line3d.Line3DSeries`. Returns ``self``."""
        from .line3d import Line3DSeries
        return self.add(Line3DSeries(x, y, z, color=color, width=width,
                                      linestyle=linestyle, label=label))

    def bar3d(self, x, y, z, cmap="viridis", alpha=0.85,
              label=None) -> "Figure3D":
        """Add a :class:`~glyphx.bar3d.Bar3DSeries`. Returns ``self``."""
        from .bar3d import Bar3DSeries
        return self.add(Bar3DSeries(x, y, z, cmap=cmap, alpha=alpha,
                                     label=label))

    def set_xlabel(self, label: str) -> "Figure3D":
        self.xlabel = label; return self

    def set_ylabel(self, label: str) -> "Figure3D":
        self.ylabel = label; return self

    def set_zlabel(self, label: str) -> "Figure3D":
        self.zlabel = label; return self

    def set_view(self, azimuth: float, elevation: float) -> "Figure3D":
        """Set the initial camera angle for SVG output."""
        self.azimuth = azimuth
        self.elevation = elevation
        return self

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _all_xyz(self):
        """Collect all X, Y, Z values across all series."""
        xs, ys, zs = [], [], []
        for s in self._series:
            if hasattr(s, "x"): xs.extend(s.x if s.x else [])
            if hasattr(s, "y"): ys.extend(s.y if s.y else [])
            if hasattr(s, "z"): zs.extend(s.z if s.z else [])
            if hasattr(s, "x_1d"): xs.extend(s.x_1d)
            if hasattr(s, "y_1d"): ys.extend(s.y_1d)
            if hasattr(s, "z_mat"):
                for row in s.z_mat:
                    zs.extend(row)
            if hasattr(s, "z_vals"): zs.extend(s.z_vals)
        return xs, ys, zs

    def render_svg(self) -> str:
        """Render a static orthographic SVG projection."""
        W, H   = self.width, self.height
        pad    = 60
        cx, cy = W // 2, H // 2
        scale  = min(W, H) * 0.34

        cam = Camera3D(azimuth=self.azimuth, elevation=self.elevation,
                       cx=cx, cy=cy, scale=scale)

        xs, ys, zs = self._all_xyz()
        if not xs: return f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg"></svg>'

        xn, xlo, xhi = normalize(xs)
        yn, ylo, yhi = normalize(ys)
        zn, zlo, zhi = normalize(zs)
        x_range = (xlo, xhi)
        y_range = (ylo, yhi)
        z_range = (zlo, zhi)

        bg    = self.theme.get("background", "#ffffff")
        tc    = self.theme.get("text_color",  "#000000")
        gc    = self.theme.get("grid_color",  "#cccccc")
        ac    = self.theme.get("axis_color",  "#333333")
        font  = self.theme.get("font", "sans-serif")

        parts: list[str] = [
            f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {W} {H}">',
            f'<rect width="{W}" height="{H}" fill="{bg}"/>',
        ]

        if self.title:
            parts.append(
                f'<text x="{W//2}" y="28" text-anchor="middle" '
                f'font-size="18" font-weight="bold" '
                f'font-family="{font}" fill="{tc}">'
                f'{svg_escape(self.title)}</text>'
            )

        # ── Axis box edges ────────────────────────────────────────────────
        box_corners = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                       (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]
        box_edges   = [(0,1),(1,2),(2,3),(3,0),
                       (4,5),(5,6),(6,7),(7,4),
                       (0,4),(1,5),(2,6),(3,7)]
        cp = [cam.project(*v) for v in box_corners]

        for a, b in box_edges:
            parts.append(
                f'<line x1="{cp[a].px:.1f}" y1="{cp[a].py:.1f}" '
                f'x2="{cp[b].px:.1f}" y2="{cp[b].py:.1f}" '
                f'stroke="{ac}" stroke-width="1" opacity="0.5"/>'
            )

        # ── Floor grid ────────────────────────────────────────────────────
        for k in range(6):
            v = -1 + k * 0.4
            for (ax1,bx1,ay1,by1) in [
                (v,-1,v,-1), (v, 1,v,-1),
                (-1,v,-1,v), (-1,v, 1,v),
            ]:
                pass  # simplified: draw X and Y grid lines on floor (Z=-1)
        for k in range(6):
            v = -1 + k * 0.4
            pa = cam.project(v, -1, -1); pb = cam.project(v, 1, -1)
            pc = cam.project(-1, v, -1); pd = cam.project(1, v, -1)
            for p1, p2 in [(pa, pb), (pc, pd)]:
                parts.append(
                    f'<line x1="{p1.px:.1f}" y1="{p1.py:.1f}" '
                    f'x2="{p2.px:.1f}" y2="{p2.py:.1f}" '
                    f'stroke="{gc}" stroke-width="0.6" opacity="0.5"/>'
                )

        # ── Tick labels ────────────────────────────────────────────────────
        NTICKS = 4
        for k in range(NTICKS + 1):
            t = -1 + k * 2 / NTICKS
            # X ticks
            data_v = xlo + (t + 1) / 2 * (xhi - xlo)
            p = cam.project(t, -1, -1)
            parts.append(
                f'<text x="{p.px:.1f}" y="{p.py + 14:.1f}" text-anchor="middle" '
                f'font-size="9" font-family="{font}" fill="{tc}">'
                f'{_format_3d_tick(data_v)}</text>'
            )
            # Y ticks
            data_v = ylo + (t + 1) / 2 * (yhi - ylo)
            p = cam.project(-1, t, -1)
            parts.append(
                f'<text x="{p.px - 6:.1f}" y="{p.py + 4:.1f}" text-anchor="end" '
                f'font-size="9" font-family="{font}" fill="{tc}">'
                f'{_format_3d_tick(data_v)}</text>'
            )
            # Z ticks
            data_v = zlo + (t + 1) / 2 * (zhi - zlo)
            p = cam.project(-1, -1, t)
            parts.append(
                f'<text x="{p.px - 6:.1f}" y="{p.py + 4:.1f}" text-anchor="end" '
                f'font-size="9" font-family="{font}" fill="{tc}">'
                f'{_format_3d_tick(data_v)}</text>'
            )

        # Axis labels
        for label, pos in [(self.xlabel, (0,-1.2,-1)),
                            (self.ylabel, (-1.2,0,-1)),
                            (self.zlabel, (-1.2,-1,0))]:
            if label:
                p = cam.project(*pos)
                parts.append(
                    f'<text x="{p.px:.1f}" y="{p.py:.1f}" text-anchor="middle" '
                    f'font-size="11" font-weight="600" '
                    f'font-family="{font}" fill="{tc}">'
                    f'{svg_escape(label)}</text>'
                )

        # ── Series ────────────────────────────────────────────────────────
        for s in self._series:
            if hasattr(s, "to_svg"):
                parts.append(s.to_svg(cam, x_range, y_range, z_range))

        parts.append("</svg>")
        return "\n".join(parts)

    def render_html(self) -> str:
        """Render a complete interactive HTML document with Three.js."""
        xs, ys, zs = self._all_xyz()
        if not xs:
            return "<html><body><p>No data.</p></body></html>"

        xn, xlo, xhi = normalize(xs)
        yn, ylo, yhi = normalize(ys)
        zn, zlo, zhi = normalize(zs)

        def nx(v): return (v - xlo) / (xhi - xlo) * 2 - 1
        def ny(v): return (v - ylo) / (yhi - ylo) * 2 - 1
        def nz(v): return (v - zlo) / (zhi - zlo) * 2 - 1

        # Normalise per series for Three.js (Y-up: swap y↔z for Three.js camera)
        data_list = []
        for s in self._series:
            d = s.to_threejs_data()
            if d["type"] == "scatter":
                d["nx"] = [nx(v) for v in s.x]
                d["ny"] = [ny(v) for v in s.y]
                d["nz"] = [nz(v) for v in s.z]
            elif d["type"] == "line":
                d["nx"] = [nx(v) for v in s.x]
                d["ny"] = [ny(v) for v in s.y]
                d["nz"] = [nz(v) for v in s.z]
            elif d["type"] == "surface":
                z_arr = np.asarray(s.z_mat, dtype=float)
                # Normalised grid arrays for Three.js geometry
                d["nxArr"] = [nx(v) for v in s.x_1d]
                d["nyArr"] = [ny(v) for v in s.y_1d]
                d["nz"]    = [[nz(float(v)) for v in row] for row in z_arr]
                d["nx"]    = len(s.x_1d)
                d["ny"]    = len(s.y_1d)
                # Raw data for surface value probe tooltip
                d["xData"] = s.x_1d
                d["yData"] = s.y_1d
                d["zData"] = s.z_mat
                from .colormaps import apply_colormap
                zmin, zmax = float(z_arr.min()), float(z_arr.max())
                span = zmax - zmin or 1
                d["face_colors"] = [
                    [apply_colormap((float(v)-zmin)/span, s.cmap) for v in row]
                    for row in z_arr
                ]
            elif d["type"] == "bar3d":
                sx = xhi - xlo or 1; sy = yhi - ylo or 1; sz = zhi - zlo or 1
                for bar in d["bars"]:
                    bar["nx"]  = nx(bar["x"])
                    bar["ny"]  = ny(bar["y"])
                    bar["nz"]  = nz(bar["z"])
                    bar["ndx"] = bar["dx"] / sx * 2
                    bar["ndy"] = bar["dy"] / sy * 2
            data_list.append(d)

        # Tick labels
        def make_ticks(lo, hi, n=4):
            return [{"norm": -1 + k*2/n,
                     "label": _format_3d_tick(lo + k*(hi-lo)/n)}
                    for k in range(n+1)]

        labels = {
            "x": make_ticks(xlo, xhi),
            "y": make_ticks(ylo, yhi),
            "z": make_ticks(zlo, zhi),
            "xlabel": self.xlabel,
            "ylabel": self.ylabel,
            "zlabel": self.zlabel,
        }

        # Legend HTML — uses glx-leg-item for click-to-toggle series
        legend_html = ""
        for si, s in enumerate(self._series):
            lbl = getattr(s, "label", None)
            if not lbl:
                continue
            col = getattr(s, "color", "#888")
            legend_html += (
                f'<div class="glx-leg-item" data-series="{si}" '
                f'title="Click to show/hide">'
                f'<div class="glx-swatch" style="background:{col}"></div>'
                f'<span>{svg_escape(lbl)}</span></div>'
            )
        legend_display = "block" if legend_html else "none"

        theme = self.theme
        subs = {
            "{title}":          svg_escape(self.title),
            "{bg}":             theme.get("background", "#ffffff"),
            "{tc}":             theme.get("text_color",  "#000000"),
            "{font}":           theme.get("font", "sans-serif"),
            "{threejs_cdn}":    _THREEJS_CDN,
            "{data_json}":      json.dumps(data_list),
            "{theme_json}":     json.dumps({
                "bg":   theme.get("background", "#ffffff"),
                "tc":   theme.get("text_color",  "#000"),
                "axis": theme.get("axis_color",  "#333"),
                "grid": theme.get("grid_color",  "#ccc"),
            }),
            "{labels_json}":    json.dumps(labels),
            "{legend_html}":    legend_html,
            "{legend_display}": legend_display,
            "{_format_tick_js}": _FORMAT_TICK_JS,
        }
        html = _HTML_TEMPLATE
        for key, val in subs.items():
            html = html.replace(key, val)
        return html

    # ------------------------------------------------------------------
    # Display / export
    # ------------------------------------------------------------------

    def show(self) -> "Figure3D":
        """Render and display.  Uses Jupyter if available, else browser."""
        html = self.render_html()
        try:
            from IPython import get_ipython
            ip = get_ipython()
            if ip and "IPKernelApp" in ip.config:
                from IPython.display import IFrame, display as jd
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".html", mode="w", encoding="utf-8"
                )
                tmp.write(html); tmp.close()
                jd(IFrame(f"file://{tmp.name}",
                           width=self.width, height=self.height))
                return self
        except Exception:
            pass
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".html", mode="w", encoding="utf-8"
        )
        tmp.write(html); tmp.close()
        webbrowser.open(f"file://{tmp.name}")
        return self

    def save(self, filename: str = "glyphx3d.html") -> "Figure3D":
        """
        Save the figure to disk.

        ``.html`` → interactive Three.js WebGL viewer (default)
        ``.svg``  → static orthographic SVG

        Returns ``self`` for chaining.
        """
        path = Path(filename)
        if path.suffix.lower() == ".svg":
            path.write_text(self.render_svg(), encoding="utf-8")
        else:
            path.write_text(self.render_html(), encoding="utf-8")
        return self

    def __repr__(self) -> str:
        kinds = [s.__class__.__name__ for s in self._series]
        return f"<glyphx.Figure3D [{', '.join(kinds)}] title={self.title!r}>"
