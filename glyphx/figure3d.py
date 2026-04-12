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
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:100%; height:100%; overflow:hidden;
  background:{bg}; font-family:{font}; }}
canvas {{ display:block; }}
#tooltip {{
  position:fixed; pointer-events:none; display:none;
  background:rgba(0,0,0,0.75); color:#fff;
  padding:6px 10px; border-radius:4px; font-size:12px;
  max-width:240px; white-space:pre-line;
}}
#title {{
  position:fixed; top:12px; left:50%; transform:translateX(-50%);
  font-size:18px; font-weight:600; color:{tc}; pointer-events:none;
}}
#legend {{
  position:fixed; right:16px; top:50%; transform:translateY(-50%);
  background:rgba(0,0,0,0.4); border-radius:6px; padding:10px 14px;
  color:{tc}; font-size:12px; display:{legend_display};
}}
#controls {{
  position:fixed; bottom:10px; left:50%; transform:translateX(-50%);
  color:{tc}; font-size:11px; opacity:0.5; pointer-events:none;
}}
</style>
</head>
<body>
<div id="title">{title}</div>
<div id="tooltip"></div>
<div id="legend">{legend_html}</div>
<div id="controls">Drag to rotate &nbsp;·&nbsp; Scroll to zoom &nbsp;·&nbsp; Right-drag to pan</div>
<script src="{threejs_cdn}"></script>
<script>
const DATA = {data_json};
const THEME = {theme_json};
const LABELS = {labels_json};

// ── Scene setup ─────────────────────────────────────────────────────────────
const W = window.innerWidth, H = window.innerHeight;
const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(W, H);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(new THREE.Color(THEME.bg), 1);
document.body.appendChild(renderer.domElement);

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, W/H, 0.01, 1000);
const light1 = new THREE.DirectionalLight(0xffffff, 0.8);
light1.position.set(5, 8, 5);
scene.add(light1);
scene.add(new THREE.AmbientLight(0xffffff, 0.45));

// ── Orbit controls (pure JS, no CDN dependency) ───────────────────────────
let state = {{ theta:45, phi:55, r:6, tx:0, ty:0,
               drag:false, rdrag:false, lx:0, ly:0 }};

function updateCamera() {{
  const t = state.theta * Math.PI/180;
  const p = state.phi   * Math.PI/180;
  camera.position.set(
    state.r * Math.sin(p) * Math.cos(t) + state.tx,
    state.r * Math.cos(p) + state.ty,
    state.r * Math.sin(p) * Math.sin(t) + state.tx
  );
  camera.lookAt(state.tx, state.ty, 0);
}}

const cv = renderer.domElement;
cv.addEventListener('mousedown', e => {{
  if (e.button===0) state.drag=true;
  if (e.button===2) state.rdrag=true;
  state.lx=e.clientX; state.ly=e.clientY;
}});
cv.addEventListener('contextmenu', e => e.preventDefault());
window.addEventListener('mouseup',   () => {{ state.drag=false; state.rdrag=false; }});
window.addEventListener('mousemove', e => {{
  const dx=e.clientX-state.lx, dy=e.clientY-state.ly;
  state.lx=e.clientX; state.ly=e.clientY;
  if (state.drag) {{
    state.theta -= dx*0.4;
    state.phi    = Math.max(5, Math.min(175, state.phi - dy*0.4));
    updateCamera();
  }}
  if (state.rdrag) {{
    state.tx -= dx*0.01; state.ty += dy*0.01;
    updateCamera();
  }}
}});
cv.addEventListener('wheel', e => {{
  state.r = Math.max(0.5, state.r * (1 + e.deltaY*0.001));
  updateCamera();
}});
// Touch support
let touches = [];
cv.addEventListener('touchstart',  e=>{{ touches=[...e.touches]; }});
cv.addEventListener('touchmove', e=>{{
  e.preventDefault();
  if(e.touches.length===1) {{
    const dx=e.touches[0].clientX-touches[0].clientX;
    const dy=e.touches[0].clientY-touches[0].clientY;
    state.theta-=dx*0.5; state.phi=Math.max(5,Math.min(175,state.phi-dy*0.5));
    updateCamera();
  }}
  if(e.touches.length===2){{
    const d0=Math.hypot(touches[0].clientX-touches[1].clientX,touches[0].clientY-touches[1].clientY);
    const d1=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);
    state.r=Math.max(0.5,state.r*(d0/d1)); updateCamera();
  }}
  touches=[...e.touches];
}},{{passive:false}});
updateCamera();

// ── Axis grid ────────────────────────────────────────────────────────────────
const axColor  = new THREE.Color(THEME.axis);
const gridColor= new THREE.Color(THEME.grid);
const textColor= THEME.tc;

function makeLine(p1, p2, col) {{
  const g = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(...p1), new THREE.Vector3(...p2)
  ]);
  const m = new THREE.LineBasicMaterial({{color:col}});
  return new THREE.Line(g, m);
}}

// Box edges at [-1,1]^3
const S = 1;
[[-S,-S,-S],[S,-S,-S]], [[-S,-S,-S],[-S,S,-S]], [[-S,-S,-S],[-S,-S,S]],
[[S,S,-S],[S,-S,-S]],   [[S,S,-S],[-S,S,-S]],   [[S,S,-S],[S,S,S]],
[[S,-S,S],[-S,-S,S]],   [[S,-S,S],[S,S,S]],      [[S,-S,S],[S,-S,-S]],
[[-S,S,S],[-S,-S,S]],   [[-S,S,S],[S,S,S]],      [[-S,S,S],[-S,S,-S]]
).forEach(([a,b]) => scene.add(makeLine(a, b, axColor)));

// Grid lines on the floor (Y = -1 plane)
const TICKS = 5;
for(let k=0;k<=TICKS;k++) {{
  const v = -S + k*(2*S/TICKS);
  scene.add(makeLine([v,-S,-S],[v,-S,S],gridColor));
  scene.add(makeLine([-S,-S,v],[S,-S,v],gridColor));
}}

// Axis tick labels using sprites
function makeLabel(text, pos, col) {{
  const canvas2 = document.createElement('canvas');
  canvas2.width=256; canvas2.height=64;
  const ctx = canvas2.getContext('2d');
  ctx.fillStyle = col;
  ctx.font='bold 32px sans-serif';
  ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(text, 128, 32);
  const tex = new THREE.CanvasTexture(canvas2);
  const mat = new THREE.SpriteMaterial({{map:tex, transparent:true}});
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.6, 0.15, 1);
  sprite.position.set(...pos);
  return sprite;
}}

// X axis ticks (on floor, front edge)
LABELS.x.forEach(t => scene.add(makeLabel(t.label,[t.norm,-S-0.12,-S-0.1],textColor)));
// Y axis ticks (on floor, left edge)
LABELS.y.forEach(t => scene.add(makeLabel(t.label,[-S-0.12,-S-0.12,t.norm],textColor)));
// Z axis ticks (left back edge)
LABELS.z.forEach(t => scene.add(makeLabel(t.label,[-S-0.25,t.norm,-S],textColor)));

// Axis name labels
scene.add(makeLabel(LABELS.xlabel, [0,-S-0.3,-S-0.2],textColor));
scene.add(makeLabel(LABELS.ylabel, [-S-0.3,-S-0.3,0],textColor));
scene.add(makeLabel(LABELS.zlabel, [-S-0.4,0,-S],textColor));

// ── Series rendering ────────────────────────────────────────────────────────
const tooltip = document.getElementById('tooltip');
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 0.06;
const mouse = new THREE.Vector2();
let hitObjects = [];

DATA.forEach(series => {{
  if (series.type === 'scatter') {{
    const positions = new Float32Array(series.x.length * 3);
    const colors    = new Float32Array(series.x.length * 3);
    series.x.forEach((x,i) => {{
      positions[i*3  ] = series.nx[i];
      positions[i*3+1] = series.nz[i];  // Y-up: swap y/z
      positions[i*3+2] = series.ny[i];
      const c = new THREE.Color(series.colors[i]);
      colors[i*3]=c.r; colors[i*3+1]=c.g; colors[i*3+2]=c.b;
    }});
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions,3));
    geom.setAttribute('color',    new THREE.BufferAttribute(colors,3));
    geom.userData = {{ xs:series.x, ys:series.y, zs:series.z,
                       label:series.label }};
    const mat = new THREE.PointsMaterial({{
      size: series.size * 0.012,
      vertexColors: true,
      transparent: true,
      opacity: series.alpha,
      sizeAttenuation: true,
    }});
    const pts = new THREE.Points(geom, mat);
    hitObjects.push(pts);
    scene.add(pts);
  }}

  if (series.type === 'line') {{
    const pts3 = series.nx.map((nx,i) =>
      new THREE.Vector3(nx, series.nz[i], series.ny[i]));
    const geom = new THREE.BufferGeometry().setFromPoints(pts3);
    const mat  = new THREE.LineBasicMaterial({{
      color: new THREE.Color(series.color),
      linewidth: series.width,
    }});
    scene.add(new THREE.Line(geom, mat));
  }}

  if (series.type === 'surface') {{
    const M=series.ny, N=series.nx;
    const positions=new Float32Array(M*N*3);
    const colors   =new Float32Array(M*N*3);
    for(let j=0;j<M;j++) for(let i=0;i<N;i++) {{
      const idx=(j*N+i)*3;
      positions[idx  ]=series.nx[i];
      positions[idx+1]=series.nz[j][i];
      positions[idx+2]=series.ny[j];
      const c=new THREE.Color(series.face_colors[j][i]);
      colors[idx]=c.r; colors[idx+1]=c.g; colors[idx+2]=c.b;
    }}
    const indices=[];
    for(let j=0;j<M-1;j++) for(let i=0;i<N-1;i++) {{
      const a=j*N+i, b=a+1, c=a+N, d=c+1;
      indices.push(a,c,b, b,c,d);
    }}
    const geom=new THREE.BufferGeometry();
    geom.setAttribute('position',new THREE.BufferAttribute(positions,3));
    geom.setAttribute('color',   new THREE.BufferAttribute(colors,3));
    geom.setIndex(indices);
    geom.computeVertexNormals();
    const mat=new THREE.MeshPhongMaterial({{
      vertexColors:true, transparent:true,
      opacity:series.alpha, side:THREE.DoubleSide,
    }});
    scene.add(new THREE.Mesh(geom,mat));
    if(series.wireframe) {{
      const wmat=new THREE.MeshBasicMaterial({{color:0xffffff,wireframe:true,transparent:true,opacity:0.15}});
      scene.add(new THREE.Mesh(geom.clone(),wmat));
    }}
  }}

  if (series.type === 'bar3d') {{
    series.bars.forEach(bar => {{
      const geom = new THREE.BoxGeometry(bar.ndx*0.9, bar.nz, bar.ndy*0.9);
      const mat  = new THREE.MeshPhongMaterial({{
        color: new THREE.Color(bar.color),
        transparent: true, opacity: series.alpha,
      }});
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(bar.nx, bar.nz/2 - 1 + bar.nz/2, bar.ny);
      scene.add(mesh);
    }});
  }}
}});

// ── Tooltip on hover ─────────────────────────────────────────────────────────
cv.addEventListener('mousemove', e => {{
  mouse.x = (e.clientX/W)*2-1;
  mouse.y = -(e.clientY/H)*2+1;
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(hitObjects);
  if (hits.length > 0) {{
    const obj  = hits[0].object;
    const idx  = hits[0].index;
    const ud   = obj.geometry.userData;
    if (ud && ud.xs) {{
      const lbl = ud.label ? ud.label+': ' : '';
      tooltip.textContent = lbl +
        `(${{{{{_format_tick_js}}}(ud.xs[idx])},` +
        ` ${{{{{_format_tick_js}}}(ud.ys[idx])},` +
        ` ${{{{{_format_tick_js}}}(ud.zs[idx])})`;
      tooltip.style.display='block';
      tooltip.style.left=(e.clientX+12)+'px';
      tooltip.style.top =(e.clientY-20)+'px';
    }}
  }} else {{
    tooltip.style.display='none';
  }}
}});
cv.addEventListener('mouseleave', () => tooltip.style.display='none');

// ── Resize ───────────────────────────────────────────────────────────────────
window.addEventListener('resize', () => {{
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth/window.innerHeight;
  camera.updateProjectionMatrix();
}});

// ── Render loop ──────────────────────────────────────────────────────────────
(function animate() {{
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}})();
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
                d["nx"] = [nx(v) for v in s.x_1d]
                d["ny"] = [ny(v) for v in s.y_1d]
                z_arr = np.asarray(s.z_mat, dtype=float)
                d["nz"] = [[nz(float(v)) for v in row] for row in z_arr]
                from .colormaps import apply_colormap
                zmin, zmax = float(z_arr.min()), float(z_arr.max())
                span = zmax - zmin or 1
                d["face_colors"] = [
                    [apply_colormap((float(v)-zmin)/span, s.cmap) for v in row]
                    for row in z_arr
                ]
                d["nx"] = len(s.x_1d)
                d["ny"] = len(s.y_1d)
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

        # Legend HTML
        legend_items = [s for s in self._series if getattr(s, "label", None)]
        legend_html = ""
        for s in legend_items:
            col = getattr(s, "color", "#888")
            legend_html += (
                f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
                f'<div style="width:14px;height:14px;border-radius:3px;'
                f'background:{col}"></div>'
                f'<span>{svg_escape(s.label)}</span></div>'
            )
        legend_display = "block" if legend_items else "none"

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
