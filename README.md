# GlyphX

**A next-generation Python visualization library — SVG-first, interactive, and built to replace Matplotlib, Seaborn, and Plotly.**

[![CI](https://github.com/kjkoeller/glyphx/actions/workflows/ci_tests.yml/badge.svg)](https://github.com/kjkoeller/glyphx/actions/workflows/ci_tests.yml)
[![Documentation](https://readthedocs.org/projects/glyphx/badge/?version=latest)](https://glyphx.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://badge.fury.io/py/glyphx.svg)](https://badge.fury.io/py/glyphx)
[![Release](https://img.shields.io/github/v/release/kjkoeller/glyphx)](https://github.com/kjkoeller/glyphx/releases/)
[![License: MIT](https://img.shields.io/github/license/kjkoeller/glyphx)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)

GlyphX renders crisp, interactive SVG charts that work everywhere — Jupyter notebooks, CLI pipelines, FastAPI servers, and static HTML files — with zero configuration and no `plt.show()` required.

---

## Why GlyphX?

| Feature | GlyphX | Matplotlib | Seaborn | Plotly |
|---|:---:|:---:|:---:|:---:|
| Auto-display (no `show()`) | ✅ | ❌ | ❌ | ❌ |
| Method chaining API | ✅ | ❌ | ❌ | Partial |
| DataFrame accessor (`df.glyphx.*`) | ✅ | ❌ | Partial | ❌ |
| Natural language chart generation | ✅ | ❌ | ❌ | ❌ |
| Linked interactive brushing | ✅ | ❌ | ❌ | ✅ (needs server) |
| Self-contained shareable HTML | ✅ | ❌ | ❌ | ❌ |
| Statistical significance brackets | ✅ | ❌ | ❌ | ❌ |
| ECDF plot | ✅ | ❌ | ✅ | ❌ |
| Raincloud plot | ✅ | ❌ | ❌ | ❌ |
| 3-D scatter / surface / line / bar | ✅ (WebGL + SVG) | ❌ | ❌ | ✅ (WebGL) |
| Bubble chart | ✅ | ✅ | ❌ | ✅ |
| Sunburst chart | ✅ | ❌ | ❌ | ✅ |
| Parallel coordinates | ✅ | ❌ | ✅ | ✅ |
| Diverging bar | ✅ | ❌ | ❌ | ✅ |
| Auto large-data downsampling (SVG) | ✅ M4+LTTB+voxel | Rasterises | ❌ | ❌ |
| Perceptually-uniform colormaps | ✅ (9 built-in) | ✅ | ✅ | ✅ |
| Continuous color encoding (scatter) | ✅ | ✅ | ✅ | ✅ |
| Candlestick / OHLC | ✅ | ❌ | ❌ | ✅ |
| Waterfall / bridge chart | ✅ | ❌ | ❌ | ✅ |
| Treemap (squarified) | ✅ | ❌ | ❌ | ✅ |
| Streaming / real-time series | ✅ (no server) | ❌ | ❌ | ✅ (needs server) |
| Synchronized crosshair | ✅ | ❌ | ❌ | ✅ (needs server) |
| PPTX export | ✅ | ❌ | ❌ | ❌ |
| CLI tool (`glyphx plot data.csv`) | ✅ | ❌ | ❌ | ❌ |
| Full ARIA / WCAG 2.1 AA accessibility | ✅ | ❌ | ❌ | Partial |
| Full type annotations (`py.typed`) | ✅ | ❌ | ❌ | Partial |
| `tight_layout()` | ✅ auto | Manual | Auto | Auto |
| Log-scale axes | ✅ | ✅ | ✅ | ✅ |
| Dual Y-axis | ✅ | ✅ | ❌ | ✅ |
| Error bars (X and Y) | ✅ | ✅ | ✅ | ✅ |

---

## Installation

```bash
pip install glyphx

# Optional extras
pip install "glyphx[export]"  # PNG/JPG raster export   (cairosvg)
pip install "glyphx[pptx]"    # PowerPoint export        (python-pptx + cairosvg)
pip install "glyphx[nlp]"     # Natural language charts  (anthropic)
pip install "glyphx[all]"     # Everything
```

**Requirements:** Python 3.12+ · NumPy ≥ 1.26 · pandas ≥ 2.1

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

### Natural Language Charts

Describe a chart in plain English; GlyphX builds it.  
Requires `pip install "glyphx[nlp]"` and `ANTHROPIC_API_KEY`.

```python
from glyphx import from_prompt
import pandas as pd

df = pd.read_csv("sales.csv")

# GlyphX infers chart type, axis mapping, grouping, theme, and title
fig = from_prompt("bar chart of total revenue by region, dark theme", df=df)

# Without a DataFrame — generates illustrative sample data
fig = from_prompt("scatter plot showing a strong positive correlation")

# Complex intent
fig = from_prompt(
    "top 10 products by revenue this quarter, sorted descending",
    df=df,
)
```

---

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

# Log-scale axes
fig = Figure(yscale="log")
fig = Figure(xscale="log", yscale="log")

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
```

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

# Column and chart suggestions for any dataset
glyphx suggest data.csv

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
# Matplotlib — 12 lines, no interactivity, no shareable output
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
# Plotly — HTML has CDN dependency, breaks offline
import plotly.express as px
fig = px.line(df, x="month", y="revenue")
fig.write_html("chart.html")   # requires CDN at view time

# GlyphX — truly self-contained, works on a USB stick
fig.share("chart.html")        # all JS inlined, zero dependencies
```

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
| `.set_legend(position)` | `Figure` | Legend position or `False` |
| `.add_axes(row, col)` | `Axes` | Get / create subplot cell |
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

### CLI

| Command | Description |
|---|---|
| `glyphx plot <file> [options]` | Render a chart from a data file |
| `glyphx suggest <file>` | Recommend chart types for a dataset |
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

## Roadmap

The items below are planned for upcoming releases. Contributions and feedback on priority order are welcome — open a GitHub issue or discussion.

### ✅ v2.1 — Competitive Foundation (shipped)
- **BubbleSeries** — scatter with size encoding; missing from all three competitors
- **SunburstSeries** — multi-ring hierarchical chart; previously Plotly-exclusive
- **ParallelCoordinatesSeries** — high-dimensional data; Seaborn has nothing equivalent
- **DivergingBarSeries** — horizontal diverging bars; no native equivalent in any competitor
- **LTTB downsampling** — Largest-Triangle-Three-Buckets auto-downsampling for LineSeries; GlyphX now handles 100k+ point datasets without SVG degradation, matching Matplotlib's large-data performance
- **Hue / palette API** — `df.glyphx.bar(x="month", y="revenue", hue="region")` auto-splits into color-coded series with theme-aligned colors; closes Seaborn's biggest advantage
- **Fluent method chaining** — every Figure method returns `self`
- **DataFrame accessor** (`df.glyphx.*`) with `hue=` support
- **Natural language charts** (`from_prompt`) via Claude API
- **Statistical significance brackets** (`add_stat_annotation`)
- **Raincloud plot**, **ECDF**, **KDE**, **FillBetween**, **Candlestick**, **Waterfall**, **Treemap**, **Streaming**
- **PPTX export**, **CLI tool**, **ARIA accessibility**, **full type annotations**
- **LTTB downsampling** — Largest-Triangle-Three-Buckets auto-downsampling for `LineSeries` on datasets above 5 000 points; SVG stays fast where Matplotlib would rasterize

### v2.2 — Remaining Chart Gaps
- **Stacked bar chart** — `StackedBarSeries` with optional 100% percentage mode
- **Stacked area chart** — additive multi-series `FillBetweenSeries`
- **Bump chart** — rank-over-time (Seaborn cannot do this natively)
- **Forest plot** — meta-analysis standard; no native equivalent in any library
- **Alluvial / Sankey diagram** — flow between categorical states over time
- **ECDF with bootstrap confidence bands** — shading around the step function
- **Clustermap with dendrogram** — Seaborn's most distinctive chart in bioinformatics; hierarchically-clustered heatmap with tree diagrams on both axes
- **Regplot / lmplot completeness** — polynomial, logistic, LOWESS, and robust regression with CI shading; beat Seaborn's regression plotting

### v2.3 — Layout & Polish
- **Shared axis subplots** — `Figure(rows=2, shared_x=True)` so all subplots share a single X axis with synchronized zoom and pan
- **Inset axis** — `fig.inset_axes(x, y, width, height)` for zoomed detail panels inside a larger plot
- **Multi-line axis labels** — wrap long X-tick labels over two lines instead of forcing rotation
- **Custom tick formatters** — `fig.axes.set_tick_format(lambda v: f"${v:,.0f}")` for per-axis label control; beat Matplotlib's fine-grained axis API
- **Minor ticks** — configurable minor grid subdivisions between major ticks

### v2.4 — Interactivity & Export
- **Click-to-filter** — click a bar or slice to cross-filter all other charts on the same HTML page, with zero server dependency
- **Animated transitions** — SVG `<animate>` elements between data updates for streaming and dashboard refresh
- **PowerPoint multi-slide** — `SubplotGrid.save("deck.pptx")` exports each subplot to a separate slide
- **Chart diff** — `glyphx.diff(fig_v1, fig_v2)` produces an animated SVG showing what changed between two renders
- **VS Code extension** — live SVG preview panel that updates on file save; no browser tab switching

### v3.0 — Platform
- **Geographic / choropleth maps** — GeoJSON + SVG path rendering for country/region maps without external tile dependencies
- **React / Next.js component** — `<GlyphXChart>` web component with Python-serialized config
- **WebAssembly renderer** — full GlyphX in the browser via Pyodide; no Python server required
- **Collaborative dashboards** — multi-user real-time dashboards over WebSocket push, no Dash or Streamlit needed
- **Figma plugin** — export any GlyphX SVG to Figma as an editable vector layer

---

## License

MIT License — © 2025 Kyle Koeller and GlyphX contributors.  
See [LICENSE](LICENSE) for the full text.
