# GlyphX

**A next-generation Python visualization library — SVG-first, interactive, and built to replace Matplotlib, Seaborn, and Plotly.**

[![CI](https://github.com/kjkoeller/glyphx/actions/workflows/ci_tests.yml/badge.svg)](https://github.com/kjkoeller/glyphx/actions/workflows/ci_tests.yml)
[![Documentation](https://readthedocs.org/projects/glyphx/badge/?version=latest)](https://glyphx.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://badge.fury.io/py/glyphx.svg)](https://badge.fury.io/py/glyphx)
[![Release](https://img.shields.io/github/v/release/kjkoeller/glyphx)](https://github.com/kjkoeller/glyphx/releases/)
[![License: MIT](https://img.shields.io/github/license/kjkoeller/glyphx)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)

GlyphX renders crisp, interactive SVG charts that work everywhere — Jupyter notebooks, CLI pipelines, FastAPI servers, and static HTML files — with zero configuration and no `plt.show()` required.

View the documentation page [here](https://glyphx.readthedocs.io/en/latest/index.html) for more detailed explanations of everything.

---

## Why GlyphX?

| Feature | GlyphX | Matplotlib | Seaborn | Plotly |
|---|---|---|---|---|
| Auto-display (no `show()`) | Everywhere | Notebooks only | Notebooks only | Notebooks only |
| Method chaining API | Yes | No | No | Partial |
| DataFrame accessor (`df.glyphx.*`) | Yes | No | Partial | No |
| Self-contained HTML size | Tens of KB | n/a | n/a | ~3 MB (inlines plotly.js) |
| Cross-chart click-to-filter | Yes, no server | No | No | Needs Dash |
| Linked interactive brushing | Yes, no server | No | No | Needs Dash |
| Streaming / real-time series | Yes, no server | No | No | Needs a server |
| Statistical significance brackets | Yes | No | Third-party | No |
| Raincloud plot | Yes | No | Third-party | No |
| Sunburst chart | Yes | No | No | Yes |
| Diverging bar | Yes | No | No | Yes |
| Candlestick / OHLC | Yes | Third-party | No | Yes |
| Waterfall / bridge chart | Yes | No | No | Yes |
| Treemap (squarified) | Yes | Third-party | No | Yes |
| Auto large-data downsampling | M4, LTTB and voxel | Rasterises instead | No | No |
| PPTX export | Yes | No | No | No |
| CLI tool (`glyphx plot data.csv`) | Yes | No | No | No |
| Full ARIA / WCAG 2.1 AA accessibility | Yes | No | No | Partial |
| `tight_layout()` | Automatic | Manual | Automatic | Automatic |

Matplotlib and Plotly are both mature and broadly capable; the rows above are
where GlyphX differs, not a general scorecard. Notably, both have things
GlyphX does not: Matplotlib ships 3-D plotting (`mpl_toolkits.mplot3d`), an
`ecdf` method, and type hints for most public APIs since 3.8, and Plotly's
`write_html` already produces a fully self-contained offline file — GlyphX's
is simply two orders of magnitude smaller.

---

## Installation

```bash
pip install glyphx

# Optional extras
pip install "glyphx[export]"  # PNG/JPG raster export   (resvg-py + pillow)
pip install "glyphx[cairo]"   # PDF export              (cairosvg)
pip install "glyphx[pptx]"    # PowerPoint export        (python-pptx + cairosvg)
pip install "glyphx[all]"     # Everything
```

**Requirements:** Python 3.10+ · NumPy ≥ 1.26 · pandas ≥ 2.1

---

## Quick Start

```python
from glyphx import plot

# One-liner — auto-displays in Jupyter, opens browser in CLI
plot([1, 2, 3], [4, 5, 6], kind="line", title="My First Chart")
```

```python
from glyphx import Figure
from glyphx.series import LineSeries, BarSeries

months  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
revenue = [120, 145, 132, 178, 159, 203]
costs   = [ 80,  90,  85, 105,  98, 115]

fig = (
    Figure(width=800, height=500)
    .set_title("Revenue vs Costs — H1")
    .set_theme("dark")
    .set_xlabel("Month")
    .set_ylabel("USD (thousands)")
    .add(LineSeries(months, revenue, color="#60a5fa", label="Revenue"))
    .add(LineSeries(months, costs,   color="#f87171", label="Costs", linestyle="dashed"))
    .add_stat_annotation("Jan", "Jun", p_value=0.004)
    .set_legend("top-left")
    .tight_layout()
)

fig.show()                     # Jupyter inline or browser tab
fig.save("chart.svg")          # SVG vector
fig.save("chart.html")         # Interactive HTML
fig.save("chart.png")          # Raster PNG  (requires cairosvg)
fig.save("chart.pptx")         # PowerPoint  (requires glyphx[pptx])
fig.share("report.html")       # Zero-CDN self-contained HTML
```

---

## Core APIs

### `plot()` — One-liner charts

The fastest path to any chart type. Mirrors pandas' `df.plot()`:

```python
from glyphx import plot

plot([1,2,3], [4,5,6],          kind="line",    title="Line")
plot(["A","B","C"], [10,20,15], kind="bar",     title="Bar")
plot([1,2,3], [4,5,6],          kind="scatter", title="Scatter")
plot(data=[30, 40, 30],          kind="pie",     labels=["A","B","C"])
plot(data=[30, 40, 30],          kind="donut",   labels=["A","B","C"])
plot(data=raw_values,            kind="hist",    bins=20)
plot(data=raw_values,            kind="box")
plot(data=matrix,                kind="heatmap")
```

### Method-Chaining API

Every method returns `self`. Build the entire chart in one expression:

```python
fig = (
    Figure(width=900, height=520, theme="warm")
    .set_title("Q3 Performance")
    .set_xlabel("Month").set_ylabel("Revenue ($M)")
    .set_legend("bottom-right")
    .add(LineSeries(x, revenue, label="Revenue"))
    .add(BarSeries(x, costs,   label="Costs"), use_y2=True)
    .annotate("Record High", x=10, y=5.4, arrow=True, color="#dc2626")
    .add_stat_annotation("Jan", "Jun", p_value=0.001)
    .vline(x=6, color="#888", linestyle="dashed")
    .hline(y=5.0, color="#888", linestyle="dotted")
    .tight_layout()
    .share("dashboard.html")
)
```

### Drop-in pandas backend

Existing `df.plot()` code becomes GlyphX with one line — no rewrite:

```python
import pandas as pd
pd.options.plotting.backend = "glyphx"

df.plot(x="month", y="revenue")            # returns a glyphx Figure
df.plot.bar(x="month", y=["revenue", "costs"])
df.plot.scatter(x="spend", y="revenue")
df.plot(x="month", y=["revenue", "costs"], subplots=True, sharex=True)
```

Supports `line`, `bar`, `area`, `scatter`, `hist`, `kde`/`density`, `box` and
`pie`, for both `DataFrame` and `Series`, plus the usual keyword arguments —
`figsize`, `title`, `xlabel`/`ylabel`, `legend`, `grid`, `logx`/`logy`,
`colormap`, `subplots`, `sharex`, `stacked`. Column resolution matches
matplotlib's: omit `x` and the index is used, omit `y` and every numeric
column is drawn.

Anything not supported — `hexbin`, `barh`, `ax=`, `secondary_y=` — raises
`NotImplementedError` naming exactly what is missing, rather than silently
dropping part of your call and handing back a chart that looks finished.

The one difference from matplotlib's backend is the return value: you get a
`glyphx.Figure`, not an `Axes`, so `.show()`, `.share()` and `.save()` are
available on it.

### DataFrame Accessor

Import `glyphx` once — every `pd.DataFrame` gains `.glyphx`:

```python
import pandas as pd
import glyphx           # registers accessor automatically

df = pd.read_csv("sales.csv")

# One-liner charts from column names
df.glyphx.line(x="date",     y="revenue", title="Daily Revenue")
df.glyphx.bar( x="product",  y="sales",   title="Sales by Product")
df.glyphx.scatter(x="spend", y="revenue")
df.glyphx.hist(col="response_time", bins=20)
df.glyphx.box(col="score", groupby="region")
df.glyphx.pie(labels="category",  values="share")
df.glyphx.donut(labels="segment", values="revenue")
df.glyphx.heatmap(title="Correlation Matrix")

# Groupby aggregation
df.glyphx.bar(groupby="region", y="revenue", agg="sum",
              title="Revenue by Region")

# Hue splitting — one BarSeries per unique region value, auto-colored
df.glyphx.bar(x="month", y="revenue", hue="region",
              title="Revenue by Month and Region")

# Full chain from the accessor
(df.glyphx
   .bar(x="month", y="revenue", auto_display=False)
   .set_theme("dark")
   .add_stat_annotation("Jan", "Jun", p_value=0.002)
   .share("report.html"))
```

## Chart Types

### Core charts

```python
from glyphx.series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries,
)

# Line — multiple linestyles, error bars
LineSeries(x, y,
    color="#2563eb",  label="Revenue",
    linestyle="dashed",          # solid | dashed | dotted | longdash | step
    width=2,
    yerr=error_values,           # symmetric Y error bars with caps
    xerr=x_error_values,         # symmetric X error bars
)

# Bar — error bars, per-bar color list
BarSeries(x, y,
    color="#7c3aed",  label="Units",
    bar_width=0.7,
    yerr=std_errors,
)

# Scatter — continuous color encoding
ScatterSeries(x, y,
    c=z_values,                  # per-point values → colormap
    cmap="viridis",              # any of 9 built-in colormaps
    size=6,
    marker="circle",             # circle | square
)

# Histogram
HistogramSeries(data, bins=20, color="#0891b2")

# Box plot — single or multi-group
BoxPlotSeries([group_a, group_b, group_c],
    categories=["Control", "Drug A", "Drug B"],
    box_width=24,
)

# Heatmap — colorbar, row/col labels, value overlay
HeatmapSeries(matrix,
    row_labels=row_names,
    col_labels=col_names,
    show_values=True,
    cmap=["#1e40af", "#f0f0f0", "#b91c1c"],  # custom diverging
)
```

### Statistical

```python
# ECDF — no bin-width choice needed, shows full distribution
from glyphx.ecdf import ECDFSeries
fig.add(ECDFSeries(data, label="Control",  complementary=False))
fig.add(ECDFSeries(data2, label="Treatment"))

# KDE — smooth density curve (no scipy required)
from glyphx.kde import KDESeries
fig.add(KDESeries(data, filled=True, alpha=0.20, label="Density"))

# Area / fill-between
from glyphx.fill_between import FillBetweenSeries
fig.add(FillBetweenSeries(x, y_lower, y_upper, color="#2563eb", alpha=0.25,
                          label="95% CI"))

# Raincloud — jitter + half-violin + box in one plot
from glyphx.raincloud import RaincloudSeries
fig.add(RaincloudSeries(
    data=[control, drug_a, drug_b],
    categories=["Control", "Drug A", "Drug B"],
    violin_width=35,
))

# Violin plot
from glyphx.violin_plot import ViolinPlotSeries
fig.add(ViolinPlotSeries([grp_a, grp_b], show_median=True, show_box=True))

# Statistical significance brackets (built-in, no extra package)
fig.add_stat_annotation("Control", "Drug A", p_value=0.001)          # → ***
fig.add_stat_annotation("Control", "Drug B", p_value=0.031, y_offset=30)  # stack
fig.add_stat_annotation("Drug A",  "Drug B", p_value=0.18,  style="numeric")
```

### Financial

```python
# Candlestick / OHLC
from glyphx.candlestick import CandlestickSeries
fig.add(CandlestickSeries(
    dates=["Mon", "Tue", "Wed", "Thu", "Fri"],
    open= [150, 153, 149, 155, 158],
    high= [155, 157, 153, 160, 162],
    low=  [148, 151, 146, 154, 156],
    close=[153, 149, 155, 158, 160],
))

# Waterfall / bridge chart
from glyphx.waterfall import WaterfallSeries
fig.add(WaterfallSeries(
    labels=["Q2 Revenue", "New Sales", "Upsell", "Churn", "Q3 Revenue"],
    values=[8_200_000, 2_100_000, 650_000, -420_000, None],  # None = auto-total
    show_values=True,
))
```

### Hierarchical

```python
# Treemap — squarified layout, area-proportional rectangles
from glyphx.treemap import TreemapSeries
fig.add(TreemapSeries(
    labels=["Cloud", "AI", "Mobile", "Security", "Data"],
    values=[4200,    3100, 2800,     2100,        1900],
    cmap="viridis",
    show_values=True,
))
```

### 3-D Charts

Use ``Figure3D`` for interactive Three.js WebGL output with an SVG fallback.
All 3-D series support per-series ``threshold=`` and expose
``last_downsample_info`` after rendering.

```python
from glyphx import Figure3D, plot3d
from glyphx.scatter3d import Scatter3DSeries
from glyphx.surface3d  import Surface3DSeries
from glyphx.line3d     import Line3DSeries
from glyphx.bar3d      import Bar3DSeries
from glyphx.contour    import ContourSeries
import numpy as np

# 3-D scatter with colormap
fig = Figure3D(title="Clusters", theme="dark", azimuth=45, elevation=30)
fig.add(Scatter3DSeries(xs, ys, zs, c=zs, cmap="plasma", size=4))
fig.show()   # WebGL interactive; .save("chart.html") for sharing

# 3-D surface — auto-decimated for large grids
x = np.linspace(-3, 3, 200)
y = np.linspace(-3, 3, 200)
Z = np.sin(np.sqrt(x[None,:]**2 + y[:,None]**2))
Figure3D().add(Surface3DSeries(x, y, Z, cmap="viridis", wireframe=True)).show()

# Helix polyline
t = np.linspace(0, 4*np.pi, 2000)
Figure3D().add(Line3DSeries(np.cos(t), np.sin(t), t/(4*np.pi))).show()

# One-liner
plot3d(xs, ys, zs, kind="scatter", title="Quick 3D")
plot3d(x, y, Z,   kind="surface", title="Quick Surface")
```

### New Chart Types (v1.5+)

```python
# Bubble — scatter with size encoding
from glyphx.bubble import BubbleSeries
fig.add(BubbleSeries(x, y, sizes=market_cap, c=growth, cmap="plasma"))

# Sunburst — multi-ring hierarchy
from glyphx.sunburst import SunburstSeries
fig.add(SunburstSeries(labels=[...], parents=[...], values=[...]))

# Parallel coordinates
from glyphx.parallel_coords import ParallelCoordinatesSeries
fig.add(ParallelCoordinatesSeries(data=df[cols], labels=df["species"]))

# Diverging bar
from glyphx.diverging_bar import DivergingBarSeries
fig.add(DivergingBarSeries(categories=[...], values=[12,-8,21,-3]))
```

### Streaming / Real-Time

```python
from glyphx.streaming import StreamingSeries

fig    = Figure(title="Live Sensor Feed")
stream = StreamingSeries(max_points=100, color="#7c3aed", label="Sensor")
fig.add(stream)

# Manual push
stream.push(42.0)
stream.push_many([41.5, 42.3, 43.1])

# Jupyter live mode — re-renders at target FPS, no server needed
with stream.live(fig, fps=10) as s:
    for reading in sensor_generator():
        s.push(reading)
```

---

## Large-Data Downsampling

GlyphX automatically keeps SVG files fast on large datasets.
All algorithms are fully vectorised with NumPy.

| Series type | Algorithm | Threshold |
|---|---|---|
| `LineSeries` | Two-stage M4 → LTTB | M4 at 50k pts; LTTB at 5k pts |
| `ScatterSeries` | 2-D voxel grid thinning | 5k pts |
| `Line3DSeries` | LTTB in screen space (camera-aware) | 5k pts |
| `Scatter3DSeries` | 3-D voxel grid thinning | 5k pts |
| `Surface3DSeries` | Grid decimation + face culling | 5k faces |

```python
# Per-series threshold override
from glyphx.series import LineSeries
ls = LineSeries(x, y, threshold=1_000)   # keep at most 1 000 points

# Inspect what happened after render
ls_info = ls.last_downsample_info
# {'algorithm': 'M4+LTTB', 'original_n': 200000, 'thinned_n': 1000}

# Global kill-switch (thread-local — safe for multi-threaded renderers)
import glyphx.downsample as ds
ds.disable()   # no downsampling on this thread
fig.render_svg()
ds.enable()

# Manual use of any algorithm
from glyphx.downsample import lttb, m4, voxel_thin_2d, lttb_3d, decimate_grid
x_down, y_down = lttb(x, y, threshold=2_000)
x_m4,   y_m4   = m4(x, y, pixel_width=800)
xt, yt, ct     = voxel_thin_2d(xs, ys, c=labels, max_points=5_000)
```

See the [Downsampling docs](https://glyphx.readthedocs.io/en/latest/downsampling.html)
for the full API, benchmark results, and the test suite.

---

## Interactivity

All charts rendered to HTML include:

| Interaction | How |
|---|---|
| **Tooltips** | Hover any data point |
| **Zoom** | Mouse wheel |
| **Pan** | Click and drag |
| **Reset zoom** | Double-click |
| **Linked brushing** | `Shift` + drag — filters all charts on the page |
| **Keyboard navigation** | `Tab` / `Arrow` keys between data points |
| **Legend toggle** | Click a legend item to show/hide its series |
| **Export** | SVG / PNG buttons in the toolbar |
| **Synchronized crosshair** | `fig.enable_crosshair()` |

### Linked Brushing

Hold `Shift` and drag a selection rectangle on any chart. All charts on the page with matching X values highlight together and dim non-matching points. Press `Escape` to clear.

```python
from glyphx.layout import grid

f1 = Figure(auto_display=False).add(ScatterSeries(x, y1, label="Sales"))
f2 = Figure(auto_display=False).add(LineSeries(x, y2, label="Revenue"))

html = grid([f1, f2], rows=1, cols=2)
open("dashboard.html", "w").write(html)
```

---

## Advanced Layout

```python
# Dual Y-axis
fig.add(LineSeries(x, prices, label="Price (left)"))
fig.add(BarSeries(x, volume, label="Volume (right)"), use_y2=True)
fig.set_ylabel("Price ($)").set_y2label("Volume (units)")

# Log-scale axes
fig = Figure(yscale="log")
fig = Figure(xscale="log", yscale="log")
```

Right-hand tick rows are derived from the left axis, so the two sets of
gridlines always coincide — including when `set_yticks()` gives the left axis
a non-default tick count. `set_tick_format()` applies to all three axes.

```python

# Subplot grid
fig = Figure(rows=2, cols=2, width=1000, height=700)
ax0 = fig.add_axes(0, 0);  ax0.add_series(LineSeries(x, y))
ax1 = fig.add_axes(0, 1);  ax1.add_series(BarSeries(cats, vals))
ax2 = fig.add_axes(1, 0);  ax2.add_series(ScatterSeries(x, y2))
ax3 = fig.add_axes(1, 1);  ax3.add_series(HistogramSeries(data))

# Reference lines
fig.vline(x=50,  color="#e11d48", linestyle="dashed")
fig.hline(y=3.5, color="#0284c7", linestyle="dotted")

# Text annotations with optional arrows
fig.annotate("Peak", x=10, y=5.4, arrow=True, color="#dc2626", font_size=12)
fig.annotate("Baseline", x=0, y=2.0, anchor="start")

# Auto tight layout (adjusts padding, rotates crowded X labels)
fig.tight_layout()

# Wrap long X labels onto a second line instead of rotating them
fig.bar(["Product Engineering", "Sales & Marketing", "R&D"], [10, 20, 15])
fig.tight_layout().set_tick_wrap()
```

### Shared X axis

Stacked panels that all plot against one X range — the standard layout for a
price/volume/indicator stack, or any set of series measured over the same
period:

```python
fig = Figure(rows=3, cols=1, width=820, height=640, shared_x=True)

fig.add_axes(0, 0).add_series(LineSeries(t, price))
fig.add_axes(1, 0).add_series(LineSeries(t, volume))
fig.add_axes(2, 0).add_series(LineSeries(t, rsi))
fig.show()
```

Every cell gets the union of all cells' X domains, so panels line up vertically
even when their series cover different spans. X tick labels are drawn only on
the lowest occupied cell in each column; grid lines and tick marks stay on all
of them, so the alignment is still readable. Sparse grids work — if a column's
bottom row is empty, the lowest cell that exists keeps its labels.

Zoom and pan are already synchronised: a subplot grid renders as one `<svg>`
with the cells as translated groups, and `zoom.js` works on the SVG viewBox,
so dragging moves every panel together.

### Inset axes

A small panel drawn on top of the main plot area, with its own independent
scales — for a zoomed detail view, or an overview thumbnail beside a zoomed
main chart:

```python
from glyphx import Figure, LineSeries

fig = Figure(width=820, height=520).line(x, y, label="full range")

inset = fig.inset_axes(0.55, 0.14, 0.38, 0.34)   # x, y, w, h as 0-1 fractions
inset.add_series(LineSeries(x[:45], y[:45]))
fig.show()
```

Position and size are fractions of the **figure canvas**, not the plot area, so
an inset stays where you put it regardless of how padding changes. The panel
inherits the parent's theme unless you pass `theme=`, gets a padding scaled to
its own size, and draws on an opaque background so the parent's grid lines
don't show through — pass `background="none"` for a transparent panel. Insets
render last and in the order added, so a later one overlaps an earlier one.

### Wrapping long tick labels

`set_tick_wrap()` is an alternative to GlyphX's default auto-rotation. Rotation
is compact but harder to read; wrapping keeps labels horizontal by splitting
them across up to two lines. Labels that already fit are left alone, and the
two are mutually exclusive — enabling wrap suppresses rotation for that axes.

---

## Colormaps

Nine perceptually-uniform colormaps:

| Name | Type | Best for |
|---|---|---|
| `viridis` | Sequential | Default continuous encoding |
| `plasma` | Sequential | High-contrast continuous |
| `inferno` | Sequential | Print-safe dark backgrounds |
| `magma` | Sequential | Heatmaps and density |
| `cividis` | Sequential | Deuteranopia-safe |
| `coolwarm` | Diverging | Correlation matrices |
| `rdbu` | Diverging | Positive / negative values |
| `spectral` | Multi-hue | Categorical ranges |
| `greys` | Sequential | Monochrome / print export |

```python
from glyphx.colormaps import apply_colormap, colormap_colors, list_colormaps

apply_colormap(0.75, "plasma")      # → "#eb5f34"
colormap_colors("viridis", 6)       # → list of 6 hex colors
list_colormaps()                    # → ["cividis", "coolwarm", ...]

# Color-encode scatter by a third variable
ScatterSeries(x, y, c=z_values, cmap="inferno")
```

---

## Themes

Seven built-in themes:

```python
Figure(theme="default")      # clean white background
Figure(theme="dark")         # charcoal background
Figure(theme="colorblind")   # Okabe-Ito palette — safe for all color vision types
Figure(theme="pastel")       # soft, presentation-friendly
Figure(theme="warm")         # earthy tones, Georgia serif font
Figure(theme="ocean")        # blue palette, light blue background
Figure(theme="monochrome")   # grayscale, print-safe

# Custom theme dict
Figure(theme={
    "colors":     ["#ff6b6b", "#4ecdc4", "#45b7d1"],
    "background": "#1a1a2e",
    "text_color": "#eeeeee",
    "axis_color": "#555555",
    "grid_color": "#333333",
    "font":       "Roboto, sans-serif",
})

# Mid-chain theme swap
fig.set_theme("dark")
```

### Registering your own theme

A theme dict works with `Figure(theme=...)`, but everything else — `df.glyphx.*`,
`facet_plot`, `clustermap`, `Figure3D`, the CLI — takes a theme *name*. Register
one and it works everywhere:

```python
from glyphx import register_theme, list_themes

register_theme(
    "acme",
    base="dark",                                   # inherit unspecified keys
    colors=["#e6194b", "#3cb44b", "#4363d8"],
    font="Inter, sans-serif",
)

Figure(theme="acme").line(x, y).show()
df.glyphx.scatter(x="a", y="b", theme="acme")

list_themes()          # ['acme', 'colorblind', 'dark', 'default', ...]
```

`register_theme` validates as it goes: a misspelled key (`colours`) or a bad
`colors` value is rejected with a message naming the problem, and built-in
names are protected from being overwritten. Unknown theme names now raise
rather than silently falling back to `default`:

```python
Figure(theme="darkk")
# ValueError: Unknown theme 'darkk'. Did you mean 'dark'? Available: ...
```

Series without an explicit `color=` cycle through the active theme's palette,
so a three-line chart on `colorblind` gets three distinguishable Okabe-Ito
colors rather than three identical blues. The same applies to the multi-color
types — pie, donut, grouped bar and stacked bar all take their slice and
segment colors from the active theme. Colormap-driven charts (treemap,
raincloud, bump) keep their `cmap`.

> **Accessibility note:** The `colorblind` theme uses the [Okabe-Ito palette](https://jfly.uni-koeln.de/color/) — the scientific standard for color-vision-deficiency-safe visualization. It is safe for deuteranopia, protanopia, and tritanopia.

---

## Export Options

```python
fig.save("chart.svg")          # SVG vector — scales to any size
fig.save("chart.html")         # interactive HTML with tooltips, zoom, export buttons
fig.save("chart.png")          # raster PNG  (requires: pip install "glyphx[export]")
fig.save("chart.jpg")          # raster JPG  (requires: pip install "glyphx[export]")
fig.save("chart.pptx")         # PowerPoint slide (requires: pip install "glyphx[pptx]")

# Self-contained HTML — all JS inlined, works fully offline
html_str = fig.share()                       # returns string
html_str = fig.share("report.html")          # also writes to disk
html_str = fig.share(title="Q3 Report")      # custom <title> tag
```

`fig.share()` inlines all JavaScript so the output works in:
email clients · Confluence · Notion · GitHub Pages · air-gapped environments

### Reacting to a clicked point

Clicking a point dispatches a `glyphx:select` event on `document`, so anything
else on the page can update itself — a detail panel, a table, an image, a
second chart, a request to your own endpoint. Clicking the same point again,
or pressing Escape, dispatches `glyphx:deselect`.

```python
fig.add(ScatterSeries(
    x, y,
    meta=[{"customer": "Acme", "orders": 42},
          {"customer": "Beta", "orders": 17}],
))
fig.share("chart.html")
```

```html
<div id="detail">Click a point</div>
<script>
  document.addEventListener('glyphx:select', (e) => {
    const { x, y, label, series, meta } = e.detail;
    detail.textContent = `${meta.customer} — ${meta.orders} orders`;
  });
</script>
```

`meta` is whatever you passed in Python, parsed back from JSON, so the listener
receives the structure you wrote rather than a flattened string.

#### A detail panel without writing JavaScript

For the common case — click a point, show its record — `add_detail_panel()`
does the wiring for you:

```python
fig.add(ScatterSeries(x, y, meta=records))
fig.add_detail_panel(["customer", "region", "tier"], title="Selected customer")
fig.share("chart.html")
```

The panel renders beside the chart, fills in on click, and returns to its
empty message on Escape or a second click. `fields` fixes the display order
and omits anything else; leave it out to show whatever each point carries.

It is an ordinary listener on the same `glyphx:select` event, so it composes
rather than competes — your own listeners still fire for the same click, and
cross-filtering still applies. Values render as text, never markup.

#### What each chart type reports

Every chart type answers a click with the values it is read for, so a pie
gives you a share and a candlestick gives you OHLC:

| Chart | `x` | `y` | also in `detail.data` |
|---|---|---|---|
| line, scatter, bar | category or position | value | |
| pie, donut | slice label | value | `percent` |
| treemap | tile label | value | `percent` |
| sunburst | node label | value | |
| box plot | category | median | `q1`, `q2`, `q3`, `median` |
| candlestick | date | close | `open`, `high`, `low`, `close` |
| stacked, grouped bar | category | segment value | |
| waterfall, diverging bar | step label | delta | |
| histogram | bin | count | |
| ECDF (`show_points=True`) | value | cumulative probability | |

`detail.data` carries every `data-` attribute the element has, so a listener
receives whatever that chart type knows about the thing that was clicked
rather than only the fields all types share. Any of those names can also go
straight into `add_detail_panel(fields=[...])`. The selected
point gets an outline rather than a colour change, since colour is data.

Events rather than a callback registry: any number of listeners can attach
without knowing about each other, and it composes with the rest — on a chart
with `enable_crossfilter()`, one click both filters the other charts and emits
the selection. Everything runs in the exported file; there is no server.

### Zoom and pan

Scroll to zoom, drag to pan, double-click empty space to reset. Axis labels
are redrawn for whatever region is visible, so a zoomed chart still tells you
what you are looking at — they are not static text that scrolls away with the
rest of the drawing.

Linear axes only; a log axis keeps its original ticks.

On a touch device, one finger pans and two pinch to zoom, anchored on the
midpoint between them. The toolbar wraps rather than overflowing a phone
screen, so a chart you share by email is usable on the device most people
will open it on.

A **Reset view** button appears in the toolbar as soon as the view moves, and
disappears once you are back to the default — so the way out is visible
exactly when it is wanted, rather than relying on knowing the double-click
gesture. It restores zoom, position and axis labels together, and resets every
chart on the page.

### Brushing

Shift and drag to select a region. Matching points stay lit, the rest fade,
and a readout shows what you selected — count, mean, sum and range — updating
live as the rectangle grows rather than only once you let go. Escape clears it.

Non-numeric values are skipped, so a categorical axis still reports a count.
The readout is an ARIA live region, so the numbers are announced rather than
being visual-only.

### Filter controls

Checkboxes, radio buttons and a search box that filter the chart in the
browser — no server, no callbacks:

```python
fig.add(ScatterSeries(x, y, meta=records))
fig.add_controls(checkboxes="region", radio="tier", search="customer",
                 title="Filter")
```

You name a *field*; GlyphX reads the distinct values out of the data and
builds one control per value. A field is found wherever it lives — in a
point's `meta`, in its own `data-` attributes (`percent` on a pie, `close` on
a candlestick), or as the series label via `"series"`.

Filters combine with AND, which is how a stack of controls reads: tick two
regions and type a name and you get that name within those regions. A running
"Showing 12 of 40" sits underneath and is announced to screen readers.

Checkboxes start ticked, and radio groups get an "All" option — a panel that
hides your data on load looks broken, and a radio group without "All" is a
one-way trip. `labels=` gives friendlier captions, `reset=False` drops the
"Show all" button.

### Cross-chart filtering

Click a bar, point or slice and every other opted-in chart on the page dims
everything that doesn't share that x value:

```python
revenue = Figure().bar(months, revenue).enable_crossfilter()
costs   = Figure().bar(months, costs).enable_crossfilter()

SubplotGrid(1, 2).add(revenue, 0, 0).add(costs, 0, 1).save("dashboard.html")
```

Click "Feb" in either chart and February stays lit in both while the other
months recede. Click it again, or press Escape, to clear.

This runs entirely inside the exported HTML — no server, no callback
round-trip, nothing leaving the page. Linked views in Plotly need Dash, and in
Bokeh need a Bokeh server; here it's a static file you can email.

Charts opt in individually, so a page can mix filtered and independent charts.
The x value is the join key, since `data-x` is already on every drawn element.
Filter changes are announced through an ARIA live region, and elements are
keyboard-reachable, so `Enter` and `Space` filter as well as clicking.

### Multi-figure export

`SubplotGrid` lays out several independent figures on one page, and now saves
directly:

```python
from glyphx import Figure
from glyphx.figure import SubplotGrid

sg = SubplotGrid(2, 2)
sg.add(revenue_fig, 0, 0)
sg.add(costs_fig,   0, 1)

sg.save("dashboard.html")          # composite page, all figures inline
sg.save("quarterly_review.pptx")   # one slide per figure, row-major order
```

Each PPTX slide is titled from that figure's own `title`. Empty grid cells are
skipped. Single-image formats (`.svg`, `.png`, `.pdf`) are rejected with a
pointer to saving each `Figure` individually — the grid's cells are separate
`<svg>` documents, so there is no one image to rasterise.

---

## CLI Tool

Plot any CSV, JSON, or Excel file from the terminal — no Python script needed:

```bash
# Basic
glyphx plot sales.csv --x month --y revenue --kind bar -o chart.html

# Full options
glyphx plot data.csv \
    --x date --y revenue \
    --kind line \
    --groupby region \
    --agg sum \
    --theme dark \
    --title "Monthly Revenue" \
    --xlabel "Date" --ylabel "Revenue ($M)" \
    --width 900 --height 500 \
    --no-legend \
    -o report.html \
    --open          # auto-open in browser after rendering

# Print version
glyphx version
```

**Supported inputs:** `.csv` `.tsv` `.json` `.jsonl` `.xlsx` `.xls`  
**Supported outputs:** `.svg` `.html` `.png` `.jpg` `.pptx`

---

## Accessibility

Every GlyphX chart meets **WCAG 2.1 AA** standards automatically:

- `role="img"` and `aria-labelledby` on every `<svg>` root
- `<title>` and `<desc>` landmark elements with auto-generated descriptions
- `tabindex="0"` and `role="graphics-symbol"` on every interactive data point
- `Tab` / `Arrow` keys navigate between data points
- `Enter` / `Space` triggers tooltips from keyboard
- `Escape` dismisses and blurs
- `focusable="false"` prevents focus stealing

```python
# Auto-generated plain-English description for screen readers
print(fig.to_alt_text())
# → 'Line chart titled "Monthly Revenue". X axis: Month. Y axis: USD.
#    Series "Revenue": 12 data points. Ranges from 98 (Mar) to 203 (Dec).'
```

---

## Type Annotations

GlyphX ships with a `py.typed` marker (PEP 561). All public APIs have complete type hints:

```python
from glyphx import Figure
from glyphx.series import LineSeries

fig: Figure     = Figure(width=640, height=480, theme="dark")
s:   LineSeries = LineSeries([1, 2, 3], [4, 5, 6], label="Revenue")
fig.add(s).set_title("Typed Chart").tight_layout().show()
```

Works with **mypy**, **pyright**, and all major IDEs out of the box.

---

## Comparison with Matplotlib

```python
# Matplotlib — 12 lines, and the output is a static image
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot(months, revenue, color="blue",  label="Revenue")
ax.plot(months, costs,   color="red",   label="Costs", linestyle="--")
ax.set_title("Revenue vs Costs")
ax.set_xlabel("Month")
ax.set_ylabel("USD")
ax.legend(loc="upper left")
plt.tight_layout()
plt.show()

# GlyphX — 7 lines, interactive, shareable
(Figure()
 .set_title("Revenue vs Costs")
 .set_xlabel("Month").set_ylabel("USD")
 .add(LineSeries(months, revenue, color="#2563eb", label="Revenue"))
 .add(LineSeries(months, costs, color="#dc2626", label="Costs", linestyle="dashed"))
 .set_legend("top-left").tight_layout()
 .share("report.html"))
```

## Comparison with Seaborn

```python
# Seaborn — significance brackets need a separate package
import seaborn as sns
from statannotations.Annotator import Annotator
ax = sns.barplot(data=df, x="group", y="score")
annotator = Annotator(ax, [("Control","Drug A")], data=df, x="group", y="score")
annotator.configure(test="t-test_ind", text_format="star")
annotator.apply_and_annotate()

# GlyphX — built-in, no extra package
(Figure()
 .add(BarSeries(["Control","Drug A","Drug B"], means, yerr=errors))
 .add_stat_annotation("Control", "Drug A", p_value=0.001)
 .add_stat_annotation("Control", "Drug B", p_value=0.031, y_offset=30)
 .show())
```

## Comparison with Plotly

```python
# Plotly — self-contained by default, but inlines ~3 MB of plotly.js
import plotly.express as px
fig = px.line(df, x="month", y="revenue")
fig.write_html("chart.html")            # ~3 MB, works offline
fig.write_html("chart.html", include_plotlyjs="cdn")   # ~40 KB, needs the CDN

# GlyphX — self-contained *and* small; there is no CDN variant to pick
fig.share("chart.html")                 # tens of KB, all JS inlined
```

Both produce a file you can open offline. The difference is that Plotly makes
you trade size against a CDN dependency, and GlyphX does not — its inlined
JavaScript is a few tens of KB rather than three megabytes.

---

## Full API Reference

### `Figure`

| Method | Returns | Description |
|---|---|---|
| `Figure(width, height, theme, rows, cols, legend, xscale, yscale)` | `Figure` | Create figure |
| `.add(series, use_y2=False)` | `Figure` | Add a series |
| `.line(x, y, ...)` | `Figure` | Shorthand LineSeries |
| `.bar(x, y, ...)` | `Figure` | Shorthand BarSeries |
| `.scatter(x, y, ...)` | `Figure` | Shorthand ScatterSeries |
| `.hist(data, ...)` | `Figure` | Shorthand HistogramSeries |
| `.box(data, ...)` | `Figure` | Shorthand BoxPlotSeries |
| `.heatmap(matrix, ...)` | `Figure` | Shorthand HeatmapSeries |
| `.pie(values, ...)` | `Figure` | Shorthand PieSeries |
| `.donut(values, ...)` | `Figure` | Shorthand DonutSeries |
| `.area(x, y1, y2, ...)` | `Figure` | Shorthand FillBetweenSeries |
| `.kde(data, ...)` | `Figure` | Shorthand KDESeries |
| `.ecdf(data, ...)` | `Figure` | Shorthand ECDFSeries |
| `.raincloud(data, ...)` | `Figure` | Shorthand RaincloudSeries |
| `.candlestick(dates, o, h, l, c)` | `Figure` | Shorthand CandlestickSeries |
| `.waterfall(labels, values, ...)` | `Figure` | Shorthand WaterfallSeries |
| `.treemap(labels, values, ...)` | `Figure` | Shorthand TreemapSeries |
| `.stream(max_points, ...)` | `StreamingSeries` | Add streaming series; returns stream |
| `.vline(x, ...)` | `Figure` | Vertical reference line |
| `.hline(y, ...)` | `Figure` | Horizontal reference line |
| `.set_title(text)` | `Figure` | Chart title |
| `.set_theme(name_or_dict)` | `Figure` | Apply theme |
| `.set_size(width, height)` | `Figure` | Resize canvas |
| `.set_xlabel(text)` | `Figure` | X-axis label |
| `.set_ylabel(text)` | `Figure` | Y-axis label |
| `.set_y2label(text)` | `Figure` | Right-hand Y-axis label (no-op without `use_y2` series) |
| `.set_legend(position)` | `Figure` | Legend position or `False` |
| `.set_tick_format(fn)` | `Figure` | Tick label formatter, applied to X, Y1 and Y2 |
| `.set_minor_ticks(n)` | `Figure` | Minor tick subdivisions |
| `.set_tick_wrap(enabled)` | `Figure` | Wrap long X tick labels instead of rotating |
| `.add_axes(row, col)` | `Axes` | Get / create subplot cell |
| `.inset_axes(x, y, w, h)` | `Axes` | Panel drawn over the plot area, own scales |
| `.annotate(text, x, y, ...)` | `Figure` | Text annotation with optional arrow |
| `.add_stat_annotation(x1, x2, p_value, ...)` | `Figure` | Significance bracket |
| `.tight_layout()` | `Figure` | Auto-adjust padding and rotate labels |
| `.enable_crosshair()` | `Figure` | Synchronized crosshair |
| `.to_alt_text()` | `str` | Screen-reader description |
| `.show()` | `Figure` | Display in Jupyter or browser |
| `.save(filename)` | `Figure` | Write SVG / HTML / PNG / JPG / PPTX |
| `.share(filename, title)` | `str` | Generate self-contained HTML |
| `.render_svg()` | `str` | Raw SVG string |

### DataFrame Accessor (`df.glyphx.*`)

| Method | Description |
|---|---|
| `.line(x, y, yerr, ...)` | Line chart |
| `.bar(x, y, groupby, agg, yerr, ...)` | Bar chart with optional groupby |
| `.scatter(x, y, ...)` | Scatter plot |
| `.hist(col, bins, ...)` | Histogram of a column |
| `.box(col, groupby, ...)` | Box plot, optional multi-group |
| `.pie(labels, values, ...)` | Pie chart |
| `.donut(labels, values, ...)` | Donut chart |
| `.heatmap(...)` | Heatmap from numeric columns |
| `.plot(kind, x, y, ...)` | Unified dispatcher |

All accessor methods return `Figure` for chaining.

An unrecognised column name raises `KeyError` naming the closest match, rather
than being silently ignored:

```python
df.glyphx.line(x="Month", y="revenue")
# KeyError: "Column 'Month' not found. Did you mean 'month'?
#            Available columns: ['month', 'revenue', 'region']"
```

Applies to `x`, `y`, `yerr`, `hue` and `groupby`. Omitting `x` is still valid
and falls back to the row index — only a name that doesn't exist is an error.

### CLI

| Command | Description |
|---|---|
| `glyphx plot <file> [options]` | Render a chart from a data file |
| `glyphx version` | Print version and exit |

---

## Running the Examples

```bash
git clone https://github.com/kjkoeller/glyphx
cd glyphx
pip install -e ".[all]"
python examples.py             # generates HTML files in ./glyphx_output/
OPEN=1 python examples.py      # also auto-opens each chart in browser
```

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

```bash
# Setup dev environment
git clone https://github.com/kjkoeller/glyphx
cd glyphx
pip install -e ".[all]"
pip install pytest pytest-cov

# Run the test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=glyphx --cov-report=term-missing
```

Please ensure all new chart types include:
- A series class with a `to_svg(ax)` method
- Tests in `tests/`
- A `to_alt_text()` compatible description
- An entry in `__init__.py` and `__all__`

---

## License

MIT License — © 2025 Kyle Koeller and GlyphX contributors.  
See [LICENSE](LICENSE) for the full text.
