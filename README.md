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

## License

MIT License  
(c) 2025 GlyphX contributors
