# GlyphX

**A Better, Faster, and Simpler Python Visualization Library**

[![PyPI version](https://img.shields.io/pypi/v/glyphx.svg)](https://pypi.org/project/glyphx/)
[![Documentation Status](https://readthedocs.org/projects/glyphx/badge/?version=latest)](https://glyphx.readthedocs.io/en/latest/?badge=latest)

---

GlyphX is a modern alternative to `matplotlib.pyplot` with interactive, SVG-based charts that automatically display in:
- Jupyter notebooks
- CLI environments
- IDEs

It provides simplicity, high-quality rendering, built-in tooltips, zoom/pan, and export options — without ever needing `plt.show()`.

---

## Features

| Feature                    | GlyphX     | Matplotlib |
|----------------------------|------------|------------|
| Auto-display               | ✅          | ❌         |
| Interactive tooltips       | ✅          | ❌         |
| Zoom / pan (in browser)    | ✅          | ❌         |
| Built-in export buttons    | ✅ SVG/PNG/JPG | ❌         |
| Multi-plot grid layout     | ✅          | ✅         |
| Seaborn-style charts       | ✅ (`lmplot`, `pairplot`, etc.) | Partial     |
| Hover highlighting         | ✅          | ❌         |
| Colorblind-friendly mode   | ✅          | ❌         |
| Shared axes support        | ✅          | ✅         |
| Font & theme customization | ✅          | ✅         |

---

## Installation

```bash
pip install glyphx
```

---

## Quick Example

```python
from glyphx import plot

fig = plot(x=[1, 2, 3], y=[2, 4, 6], kind="line", label="Demo")
# No need for fig.show(); it auto-displays in Jupyter or saves via fig.save()
```

---

## Chart Types

- Line chart
- Bar chart (including grouped bars)
- Scatter plot
- Pie / Donut chart
- Box plot
- Histogram
- Swarm plot
- Violin plot
- Count plot
- lmplot, jointplot, pairplot
- Faceted charts (`FacetGrid`, `facet_plot`)

---

## Interactivity

All charts support:
- Mouseover tooltips
- Zoom / pan (mouse wheel + drag)
- Click-to-download buttons (SVG, PNG, JPG)

---

## Export Options

```python
fig.save("my_chart.png")
fig.save("my_chart.svg")
```

---

## Grid Layout

```python
from glyphx.layout import grid

charts = [plot(...), plot(...), plot(...)]
html = grid(charts, cols=2)
```

---

## Theming

```python
from glyphx.themes import themes
theme = themes["dark"]
```

---

## Comparison with Matplotlib

### 📈 Line Plot

<table>
  <tr><th>Matplotlib</th><th>GlyphX</th></tr>
  <tr>
    <td><img src="images/matplotlib_line.png" width="300"/></td>
    <td><img src="images/glyphx_line.png" width="300"/></td>
  </tr>
  <tr>
    <td><pre><code class="language-python">import matplotlib.pyplot as plt

plt.plot([1, 2, 3], [4, 5, 6])
plt.title("Simple Line Plot")
plt.xlabel("X Axis")
plt.ylabel("Y Axis")
plt.show()</code></pre></td>
    <td><pre><code class="language-python">from glyphx import plot

plot(x=[1, 2, 3], y=[4, 5, 6],
     kind="line", title="Simple Line Plot",
     xlabel="X Axis", ylabel="Y Axis")</code></pre></td>
  </tr>
</table>

### 📊 Bar Chart

<table>
  <tr><th>Matplotlib</th><th>GlyphX</th></tr>
  <tr>
    <td><img src="images/matplotlib_bar.png" width="300"/></td>
    <td><img src="images/glyphx_bar.png" width="300"/></td>
  </tr>
  <tr>
    <td><pre><code class="language-python">import matplotlib.pyplot as plt

plt.bar(["A", "B", "C"], [5, 3, 7])
plt.title("Bar Chart")
plt.xlabel("Categories")
plt.ylabel("Values")
plt.show()</code></pre></td>
    <td><pre><code class="language-python">from glyphx import plot

plot(x=["A", "B", "C"], y=[5, 3, 7],
     kind="bar", title="Bar Chart",
     xlabel="Categories", ylabel="Values")</code></pre></td>
  </tr>
</table>

### 🔵 Scatter Plot

<table>
  <tr><th>Matplotlib</th><th>GlyphX</th></tr>
  <tr>
    <td><img src="images/matplotlib_scatter.png" width="300"/></td>
    <td><img src="images/glyphx_scatter.png" width="300"/></td>
  </tr>
  <tr>
    <td><pre><code class="language-python">import matplotlib.pyplot as plt

plt.scatter([1, 2, 3, 4], [4, 1, 3, 5])
plt.title("Scatter Plot")
plt.xlabel("X Axis")
plt.ylabel("Y Axis")
plt.show()</code></pre></td>
    <td><pre><code class="language-python">from glyphx import plot

plot(x=[1, 2, 3, 4], y=[4, 1, 3, 5],
     kind="scatter", title="Scatter Plot",
     xlabel="X Axis", ylabel="Y Axis")</code></pre></td>
  </tr>
</table>

### 🥧 Pie Chart

<table>
  <tr><th>Matplotlib</th><th>GlyphX</th></tr>
  <tr>
    <td><img src="images/matplotlib_pie.png" width="300"/></td>
    <td><img src="images/glyphx_pie.png" width="300"/></td>
  </tr>
  <tr>
    <td><pre><code class="language-python">import matplotlib.pyplot as plt

labels = ["A", "B", "C"]
sizes = [30, 45, 25]
plt.pie(sizes, labels=labels)
plt.title("Pie Chart")
plt.show()</code></pre></td>
    <td><pre><code class="language-python">from glyphx import plot

plot(data=[30, 45, 25],
     kind="pie", labels=["A", "B", "C"],
     title="Pie Chart")</code></pre></td>
  </tr>
</table>

---

## Subplot Grid Example

<table>
  <tr>
    <td colspan="2"><img src="images/glyphx_sublpot.png" width="600"/></td>
  </tr>
  <tr>
    <td colspan="2"><pre><code class="language-python">from glyphx import Figure, series, themes

fig = Figure(rows=2, cols=2, theme=themes["dark"])

ax1 = fig.add_axes(0, 0)
ax1.add(series.LineSeries([1, 2], [3, 4], label="Line"))
ax1.legend_pos = "right"

ax2 = fig.add_axes(1, 0)
ax2.add(series.ScatterSeries([1, 2, 3, 4], [4, 1, 3, 5], label="Scatter"))
ax2.legend_pos = "right"

ax3 = fig.add_axes(0, 1)
ax3.add(series.BarSeries(x=["A", "B", "C"], y=[5, 3, 7], label="Bar"))
ax3.legend_pos = "right"

ax4 = fig.add_axes(1, 1)
ax4.add(series.PieSeries(values=[30, 45, 25], labels=["A", "B", "C"]))

fig.plot()</code></pre></td>
  </tr>
</table>

<table>
  <tr>
    <td colspan="2"><img src="images/matplotlib_sublpot.png" width="600"/></td>
  </tr>
  <tr>
    <td colspan="2"><pre><code class="language-python">import matplotlib.pyplot as plt
import numpy as np

fig, axs = plt.subplots(2, 2, figsize=(10, 8))

axs[0, 0].plot([1, 2], [3, 4])
axs[0, 0].set_title("Line")

axs[1, 0].scatter([1, 2, 3, 4], [4, 1, 3, 5])
axs[1, 0].set_title("Scatter")

axs[0, 1].bar(["A", "B", "C"], [5, 3, 7])
axs[0, 1].set_title("Bar")

axs[1, 1].pie([30, 45, 25], labels=["A", "B", "C"])
axs[1, 1].set_title("Pie")

plt.tight_layout()
plt.show()</code></pre></td>
  </tr>
</table>

---

## License

MIT License  
(c) 2025 GlyphX contributors
