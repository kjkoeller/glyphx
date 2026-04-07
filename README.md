# GlyphX

**A next-generation Python visualization library — SVG-first, interactive, and designed to replace Matplotlib, Seaborn, and Plotly.**

[![PyPI version](https://img.shields.io/pypi/v/glyphx.svg)](https://pypi.org/project/glyphx/)
[![Python](https://img.shields.io/pypi/pyversions/glyphx.svg)](https://pypi.org/project/glyphx/)
[![Documentation](https://readthedocs.org/projects/glyphx/badge/?version=latest)](https://glyphx.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

GlyphX renders crisp, interactive SVG charts that work everywhere — Jupyter notebooks, CLI pipelines, FastAPI servers, and static HTML files — with zero configuration and no `plt.show()` required.

---

## Why GlyphX?

| Feature | GlyphX | Matplotlib | Seaborn | Plotly |
|---|:---:|:---:|:---:|:---:|
| Auto-display (no show()) | ✅ | ❌ | ❌ | ❌ |
| Method chaining API | ✅ | ❌ | ❌ | Partial |
| DataFrame accessor (`df.glyphx.*`) | ✅ | ❌ | Partial | ❌ |
| Natural language chart generation | ✅ | ❌ | ❌ | ❌ |
| Linked interactive brushing | ✅ | ❌ | ❌ | ✅ (needs server) |
| Self-contained shareable HTML | ✅ | ❌ | ❌ | ❌ |
| Statistical significance brackets | ✅ | ❌ | ❌ | ❌ |
| ECDF plot | ✅ | ❌ | ✅ | ❌ |
| Raincloud plot | ✅ | ❌ | ❌ | ❌ |
| Perceptually-uniform colormaps | ✅ (9 built-in) | ✅ | ✅ | ✅ |
| Continuous color encoding in scatter | ✅ | ✅ | ✅ | ✅ |
| Candlestick / OHLC | ✅ | ❌ | ❌ | ✅ |
| Waterfall / bridge chart | ✅ | ❌ | ❌ | ✅ |
| Treemap (squarified) | ✅ | ❌ | ❌ | ✅ |
| Streaming / real-time series | ✅ (no server) | ❌ | ❌ | ✅ (needs server) |
| Synchronized crosshair | ✅ | ❌ | ❌ | ✅ (needs server) |
| PPTX export | ✅ | ❌ | ❌ | ❌ |
| CLI tool (`glyphx plot data.csv`) | ✅ | ❌ | ❌ | ❌ |
| Full ARIA accessibility | ✅ | ❌ | ❌ | Partial |
| Full type annotations (py.typed) | ✅ | ❌ | ❌ | Partial |
| tight_layout() | ✅ (auto) | Manual | Auto | Auto |

---

## Installation

```bash
pip install glyphx

# Optional extras
pip install "glyphx[pptx]"   # PowerPoint export (python-pptx + cairosvg)
pip install "glyphx[export]" # PNG/JPG export (cairosvg)
pip install "glyphx[nlp]"    # Natural language charts (anthropic)
pip install "glyphx[all]"    # Everything
```

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

# Fluent method-chaining API
fig = (
    Figure(width=800, height=500)
    .set_title("Revenue vs Costs")
    .set_theme("dark")
    .set_xlabel("Month")
    .set_ylabel("USD (thousands)")
    .add(LineSeries(months, revenue, color="#60a5fa", label="Revenue"))
    .add(LineSeries(months, costs,   color="#f87171", label="Costs", linestyle="dashed"))
    .set_legend("top-left")
    .tight_layout()
)

fig.show()                          # display in Jupyter / browser
fig.save("chart.svg")              # SVG
fig.save("chart.html")             # interactive HTML
fig.save("chart.png")              # raster (requires cairosvg)
fig.save("chart.pptx")             # PowerPoint slide (requires glyphx[pptx])
fig.share("report.html")           # self-contained, zero-CDN HTML
```

---

## Core APIs

### 1 — Unified `plot()` Function

The fastest path to any chart type. Arguments mirror pandas' `df.plot()`:

```python
from glyphx import plot

plot([1,2,3], [4,5,6], kind="line",    title="Line")
plot(["A","B","C"], [10,20,15], kind="bar",     title="Bar")
plot([1,2,3], [4,5,6], kind="scatter", title="Scatter")
plot(data=[30,40,30],  kind="pie",     labels=["A","B","C"])
plot(data=[30,40,30],  kind="donut",   labels=["A","B","C"])
plot(data=raw_values,  kind="hist",    bins=20)
plot(data=raw_values,  kind="box")
plot(data=matrix,      kind="heatmap")
```

### 2 — Method-Chaining API

Every mutating method returns `self`. Build the entire chart in a single expression:

```python
fig = (
    Figure(width=720, height=460, theme="warm")
    .set_title("Q3 Performance Dashboard")
    .set_size(900, 520)              # resize mid-chain
    .set_xlabel("Month")
    .set_ylabel("Revenue ($M)")
    .set_legend("bottom-right")
    .add(LineSeries(x, y, label="Revenue"))
    .add(BarSeries(x, costs, label="Costs"), use_y2=True)
    .annotate("Record High", x=10, y=5.4, arrow=True, color="#dc2626")
    .add_stat_annotation("Jan", "Jun", p_value=0.001)
    .tight_layout()
    .share("dashboard.html")
)
```

### 3 — DataFrame Accessor

Import `glyphx` once and every `pd.DataFrame` gains a `.glyphx` accessor:

```python
import pandas as pd
import glyphx  # registers the accessor automatically

df = pd.read_csv("sales.csv")

# One-liner charts directly from column names
df.glyphx.line(x="date",    y="revenue", title="Daily Revenue")
df.glyphx.bar( x="product", y="sales",   title="Sales by Product")
df.glyphx.scatter(x="spend", y="revenue")
df.glyphx.hist(col="response_time", bins=20)
df.glyphx.box(col="score", groupby="region")
df.glyphx.pie(labels="category", values="share")

# Groupby aggregation in one call
df.glyphx.bar(groupby="region", y="revenue", agg="sum",
              title="Revenue by Region")

# Full chain from the accessor
(df.glyphx
   .bar(x="month", y="revenue", label="Revenue", auto_display=False)
   .set_theme("dark")
   .set_xlabel("Month")
   .add_stat_annotation("Jan", "Jun", p_value=0.002)
   .share("monthly_report.html"))
```

### 4 — Natural Language Charts

Describe a chart in plain English and GlyphX builds it automatically.  
Requires `pip install "glyphx[nlp]"` and an `ANTHROPIC_API_KEY`.

```python
from glyphx import from_prompt
import pandas as pd

df = pd.read_csv("sales.csv")

# GlyphX infers chart type, column mappings, grouping, theme, and title
fig = from_prompt("bar chart of total revenue by region, dark theme", df=df)

# Works without a DataFrame too — generates illustrative sample data
fig = from_prompt("scatter plot showing a strong positive correlation")

# Complex queries
fig = from_prompt(
    "top 10 products by revenue this quarter, sorted descending",
    df=df,
)
```

---

## Interactivity

All charts rendered to HTML include:

| Interaction | How |
|---|---|
| **Tooltips** | Hover any data point |
| **Zoom** | Mouse wheel |
| **Pan** | Click + drag |
| **Reset zoom** | Double-click |
| **Linked brushing** | `Shift` + drag on any chart — filters all charts on the page |
| **Keyboard navigation** | `Tab` / `Arrow` keys move between data points |
| **Legend toggle** | Click a legend item to show/hide its series |
| **Export** | SVG / PNG buttons in the toolbar |
| **Share** | One-click copy of self-contained HTML to clipboard |

### Linked Brushing

Hold `Shift` and drag on any chart. All charts on the same HTML page sharing the same X values highlight matching points and dim everything else. Press `Escape` to clear.

```python
from glyphx import Figure
from glyphx.layout import grid
from glyphx.series import ScatterSeries, LineSeries

f1 = Figure().add(ScatterSeries(x, y1, label="Sales"))
f2 = Figure().add(LineSeries(x, y2, label="Revenue"))

# Both charts brush together
html = grid([f1, f2], rows=1, cols=2)
open("dashboard.html", "w").write(html)
```

### Synchronized Crosshair

```python
fig.enable_crosshair()  # vertical line syncs across all charts on the page
fig.share("report.html")
```

---

## Chart Types

### Basic

```python
from glyphx.series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries,
)

# Line — with error bars and linestyles
LineSeries(x, y,
    color="#2563eb", label="Revenue",
    linestyle="dashed",      # solid | dashed | dotted | longdash
    width=2,
    yerr=error_values,       # Y error bars with caps
    xerr=error_values,       # X error bars
)

# Bar — with error bars and groupby support
BarSeries(x, y,
    color="#7c3aed", label="Units",
    bar_width=0.7,
    yerr=std_errors,
)

# Scatter — with continuous color encoding
ScatterSeries(x, y,
    c=z_values,              # per-point color values
    cmap="viridis",          # any of 9 built-in colormaps
    size=6,
    marker="circle",         # circle | square
)

# Histogram
HistogramSeries(data, bins=20, color="#0891b2")

# Box plot — single or multi-group
BoxPlotSeries(data, categories=["A","B","C"], box_width=24)
BoxPlotSeries([group_a, group_b, group_c], categories=["A","B","C"])

# Heatmap — with colorbar, row/col labels, value overlay
HeatmapSeries(matrix,
    row_labels=row_names,
    col_labels=col_names,
    show_values=True,
    cmap=["#1e40af","#f0f0f0","#b91c1c"],
)
```

### Statistical (better than Seaborn)

```python
# ECDF — no bin-width choice needed
from glyphx.ecdf import ECDFSeries
ECDFSeries(data, label="Control", complementary=False)

# Raincloud — jitter + half-violin + box in one
from glyphx.raincloud import RaincloudSeries
RaincloudSeries(
    data=[control, drug_a, drug_b],
    categories=["Control","Drug A","Drug B"],
    violin_width=35,
)

# Statistical significance brackets
fig.add_stat_annotation(
    x1="Control", x2="Drug A",
    p_value=0.001,            # → "***"
    style="stars",            # stars | numeric
    y_offset=0,               # stack multiple brackets
)

# Violin plot
from glyphx.violin_plot import ViolinPlotSeries
ViolinPlotSeries(data=[grp_a, grp_b], show_median=True, show_box=True)
```

### Financial (better than Plotly)

```python
# Candlestick / OHLC
from glyphx.candlestick import CandlestickSeries
CandlestickSeries(
    dates=["Mon","Tue","Wed"],
    open= [150, 153, 149],
    high= [155, 157, 153],
    low=  [148, 151, 146],
    close=[153, 149, 155],
)

# Waterfall / bridge chart
from glyphx.waterfall import WaterfallSeries
WaterfallSeries(
    labels=["Q2 Revenue","New Sales","Churn","Q3 Revenue"],
    values=[8.2, 2.1, -0.6, None],   # None = auto-compute total bar
    show_values=True,
)
```

### Hierarchical

```python
# Treemap — squarified layout algorithm
from glyphx.treemap import TreemapSeries
TreemapSeries(
    labels=["Cloud","AI","Mobile","Security","Data"],
    values=[4200, 3100, 2800, 2100, 1900],
    cmap="viridis",
)
```

### Streaming / Real-Time

```python
from glyphx.streaming import StreamingSeries

fig = Figure().set_title("Live Sensor Feed")
stream = StreamingSeries(max_points=100, color="#7c3aed", label="Sensor")
fig.add(stream)

# Push values one at a time
stream.push(42.0)
stream.push(43.8)

# Or batch
stream.push_many([41, 42, 43, 44, 45])

# Jupyter live mode — re-renders at target FPS
with stream.live(fig, fps=10) as s:
    for reading in sensor_generator():
        s.push(reading)
```

### Advanced Layout

```python
# Dual Y-axis
fig.add(LineSeries(x, prices, label="Price (left)"))
fig.add(BarSeries(x, volume, label="Volume (right)"), use_y2=True)

# Subplot grid
fig = Figure(rows=2, cols=2, width=1000, height=700)
ax1 = fig.add_axes(0, 0)
ax1.add_series(LineSeries(x, y))
ax2 = fig.add_axes(0, 1)
ax2.add_series(BarSeries(cats, vals))

# Auto tight layout — adjusts padding and rotates crowded labels
fig.tight_layout()

# Annotations with arrows
fig.annotate("Peak", x=10, y=5.4, arrow=True, color="#dc2626", font_size=12)

# Log scale
Figure(yscale="log")
Figure(xscale="log")
```

---

## Colormaps

Nine perceptually-uniform colormaps, all colorblind-safe when used with the `colorblind` theme:

| Name | Type | Best for |
|---|---|---|
| `viridis` | Sequential | Default continuous encoding |
| `plasma` | Sequential | High-contrast continuous |
| `inferno` | Sequential | Print-safe dark backgrounds |
| `magma` | Sequential | Heatmaps and density |
| `cividis` | Sequential | Deuteranopia-safe |
| `coolwarm` | Diverging | Correlation matrices |
| `rdbu` | Diverging | Positive/negative values |
| `spectral` | Multi-hue | Categorical ranges |
| `greys` | Sequential | Monochrome export |

```python
from glyphx.colormaps import (
    apply_colormap,    # single value → hex color
    colormap_colors,   # n evenly-spaced colors
    list_colormaps,    # all available names
)

# Single value
color = apply_colormap(0.75, "plasma")   # "#eb5f34"

# N colors for a grouped bar chart
colors = colormap_colors("viridis", 6)

# Color-encode scatter points by a third variable
ScatterSeries(x, y, c=z_values, cmap="inferno")
```

---

## Themes

Seven built-in themes, including the scientifically correct Okabe-Ito colorblind palette:

```python
Figure(theme="default")      # clean white background
Figure(theme="dark")         # dark charcoal background
Figure(theme="colorblind")   # Okabe-Ito palette — safe for all types
Figure(theme="pastel")       # soft, presentation-friendly
Figure(theme="warm")         # earthy tones, Georgia serif font
Figure(theme="ocean")        # blue palette, light blue background
Figure(theme="monochrome")   # grayscale, print-safe

# Custom theme
Figure(theme={
    "colors":     ["#ff6b6b", "#4ecdc4", "#45b7d1"],
    "background": "#1a1a2e",
    "text_color": "#eee",
    "axis_color": "#555",
    "grid_color": "#333",
    "font":       "Roboto, sans-serif",
})
```

---

## Export Options

```python
fig.save("chart.svg")         # vector SVG
fig.save("chart.html")        # interactive HTML with tooltips, zoom, export buttons
fig.save("chart.png")         # raster PNG  (requires: pip install cairosvg)
fig.save("chart.jpg")         # raster JPG  (requires: pip install cairosvg)
fig.save("chart.pptx")        # PowerPoint  (requires: pip install "glyphx[pptx]")

# Self-contained HTML — zero external dependencies, works offline
html = fig.share()                    # returns HTML string
html = fig.share("report.html")      # also writes to disk
html = fig.share(title="Q3 Report")  # custom <title>
```

### Shareable HTML

`fig.share()` generates a single `.html` file with all JavaScript inlined. No CDN links, no server, no external files. Open it from a USB stick, email it, embed it in Confluence, paste it in Notion — it works everywhere.

---

## CLI Tool

Plot any CSV, JSON, or Excel file from the terminal:

```bash
# Basic usage
glyphx plot sales.csv --x month --y revenue --kind bar -o chart.html

# All options
glyphx plot data.csv \
    --x date \
    --y revenue \
    --kind line \
    --groupby region \
    --agg sum \
    --theme dark \
    --title "Monthly Revenue" \
    --xlabel "Date" \
    --ylabel "Revenue ($M)" \
    --width 900 \
    --height 500 \
    --no-legend \
    -o report.html \
    --open                # auto-open in browser

# Chart type suggestions for any dataset
glyphx suggest data.csv

# Version
glyphx version
```

Supported input formats: `.csv` `.tsv` `.json` `.jsonl` `.xlsx` `.xls`  
Supported output formats: `.svg` `.html` `.png` `.jpg` `.pptx`

---

## Accessibility

Every chart GlyphX renders meets WCAG 2.1 AA standards out of the box:

- `role="img"` and `aria-labelledby` on every `<svg>` root element  
- `<title>` and `<desc>` landmark elements with auto-generated descriptions  
- `tabindex="0"` and `role="graphics-symbol"` on every interactive data point  
- `Tab` / `Arrow` key navigation between data points  
- `Enter` / `Space` to trigger tooltips from keyboard  
- `Escape` to dismiss and blur  
- `focusable="false"` prevents SVG from stealing keyboard focus  

```python
# Auto-generated plain-English description for screen readers
alt = fig.to_alt_text()
# → 'Line chart titled "Monthly Revenue". X axis: Month. Y axis: USD.
#    Series "Revenue": 12 data points. Ranges from 98 (Mar) to 300 (Dec).'
```

---

## Type Annotations

GlyphX is fully typed (`py.typed` PEP 561 marker included). Works with mypy, pyright, and any IDE with type checking:

```python
from glyphx import Figure
from glyphx.series import LineSeries

fig: Figure = Figure(width=640, height=480)
s: LineSeries = LineSeries([1, 2, 3], [4, 5, 6], label="Revenue")
fig.add(s).set_title("Typed Chart").show()
```

---

## Comparison with Matplotlib

### Line Chart

```python
# Matplotlib
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
```

```python
# GlyphX — chains, shares, no plt.show()
(Figure()
 .set_title("Revenue vs Costs")
 .set_xlabel("Month").set_ylabel("USD")
 .add(LineSeries(months, revenue, color="#2563eb", label="Revenue"))
 .add(LineSeries(months, costs, color="#dc2626", label="Costs", linestyle="dashed"))
 .set_legend("top-left")
 .tight_layout()
 .share("report.html"))
```

### Subplot Grid

```python
# Matplotlib
import matplotlib.pyplot as plt
fig, axs = plt.subplots(2, 2, figsize=(10, 8))
axs[0,0].plot([1,2,3], [4,5,6])
axs[0,1].bar(["A","B","C"], [5,3,7])
axs[1,0].scatter([1,2,3], [4,5,6])
axs[1,1].pie([30,45,25], labels=["A","B","C"])
plt.tight_layout()
plt.show()
```

```python
# GlyphX
from glyphx import Figure
from glyphx.series import LineSeries, BarSeries, ScatterSeries, PieSeries

fig = Figure(rows=2, cols=2, width=900, height=640)
fig.add_axes(0,0).add_series(LineSeries([1,2,3],[4,5,6]))
fig.add_axes(0,1).add_series(BarSeries(["A","B","C"],[5,3,7]))
fig.add_axes(1,0).add_series(ScatterSeries([1,2,3],[4,5,6]))
fig.add_axes(1,1).add_series(PieSeries([30,45,25],labels=["A","B","C"]))
fig.show()
```

---

## Comparison with Seaborn

### Statistical Significance

```python
# Seaborn — requires separate statannotations package
import seaborn as sns
from statannotations.Annotator import Annotator

ax = sns.barplot(data=df, x="group", y="score")
annotator = Annotator(ax, [("Control","Drug A")], data=df, x="group", y="score")
annotator.configure(test="t-test_ind", text_format="star")
annotator.apply_and_annotate()
```

```python
# GlyphX — built-in, no extra package
(Figure()
 .add(BarSeries(["Control","Drug A","Drug B"], means, yerr=errors))
 .add_stat_annotation("Control", "Drug A", p_value=0.001)
 .add_stat_annotation("Control", "Drug B", p_value=0.031, y_offset=30)
 .show())
```

### Raincloud Plot

```python
# Seaborn — no native raincloud, requires ptitprince or manual assembly
import ptitprince as pt
pt.RainCloud(x="group", y="score", data=df, ax=ax)
```

```python
# GlyphX — one series, built-in
from glyphx.raincloud import RaincloudSeries

Figure().add(RaincloudSeries(
    data=[control, drug_a, drug_b],
    categories=["Control","Drug A","Drug B"],
)).show()
```

---

## Comparison with Plotly

### Shareable Output

```python
# Plotly — CDN dependency in exported HTML
import plotly.express as px
fig = px.line(df, x="month", y="revenue")
fig.write_html("chart.html")  # loads plotly.js from CDN — breaks offline
```

```python
# GlyphX — truly self-contained
fig.share("chart.html")  # all JS inlined, works with no internet connection
```

### Streaming — No Server Required

```python
# Plotly — requires Dash + a running server
import dash
app = dash.Dash(__name__)
# ... 50+ lines of Dash boilerplate ...
app.run_server()
```

```python
# GlyphX — works in a single Jupyter cell
from glyphx.streaming import StreamingSeries

stream = StreamingSeries(max_points=100)
fig = Figure().add(stream)

with stream.live(fig, fps=10) as s:
    for reading in sensor.stream():
        s.push(reading)
```

---

## Full Feature Reference

### Figure

| Method | Returns | Description |
|---|---|---|
| `Figure(width, height, theme, rows, cols, legend, xscale, yscale)` | `Figure` | Create a figure |
| `.add(series, use_y2=False)` | `Figure` | Add a series |
| `.set_title(text)` | `Figure` | Set chart title |
| `.set_theme(name_or_dict)` | `Figure` | Apply a theme |
| `.set_size(width, height)` | `Figure` | Resize canvas |
| `.set_xlabel(text)` | `Figure` | X-axis label |
| `.set_ylabel(text)` | `Figure` | Y-axis label |
| `.set_legend(position)` | `Figure` | Legend position or `False` |
| `.add_axes(row, col)` | `Axes` | Subplot grid cell |
| `.annotate(text, x, y, ...)` | `Figure` | Add text annotation |
| `.add_stat_annotation(x1, x2, p_value, ...)` | `Figure` | Significance bracket |
| `.tight_layout()` | `Figure` | Auto-adjust padding |
| `.enable_crosshair()` | `Figure` | Synchronized crosshair |
| `.to_alt_text()` | `str` | Screen-reader description |
| `.show()` | `Figure` | Display (Jupyter / browser) |
| `.save(filename)` | `Figure` | Save SVG/HTML/PNG/JPG/PPTX |
| `.share(filename, title)` | `str` | Self-contained HTML |
| `.render_svg()` | `str` | Raw SVG string |

### DataFrame Accessor (`df.glyphx.*`)

| Method | Description |
|---|---|
| `.line(x, y, ...)` | Line chart |
| `.bar(x, y, groupby, agg, ...)` | Bar chart with optional groupby |
| `.scatter(x, y, ...)` | Scatter plot |
| `.hist(col, bins, ...)` | Histogram |
| `.box(col, groupby, ...)` | Box plot |
| `.pie(labels, values, ...)` | Pie chart |
| `.donut(labels, values, ...)` | Donut chart |
| `.heatmap(...)` | Heatmap from numeric columns |
| `.plot(kind, x, y, ...)` | Unified dispatcher |

All accessor methods return `Figure` for chaining.

### CLI (`glyphx`)

| Command | Description |
|---|---|
| `glyphx plot <file> [options]` | Render a chart from a data file |
| `glyphx suggest <file>` | Recommend chart types for a dataset |
| `glyphx version` | Print version and exit |

### Colormaps

`viridis` `plasma` `inferno` `magma` `cividis` `coolwarm` `rdbu` `spectral` `greys`

```python
from glyphx.colormaps import apply_colormap, colormap_colors, list_colormaps
```

### Themes

`default` `dark` `colorblind` `pastel` `warm` `ocean` `monochrome`

---

## Running the Examples

```bash
git clone https://github.com/kjkoeller/glyphx
cd glyphx
pip install -e .
python examples.py            # generates ./glyphx_output/ with 34 HTML files
OPEN=1 python examples.py    # same, auto-opens each chart in browser
```

---

## License

MIT License — © 2025 Kyle Koeller and GlyphX contributors
