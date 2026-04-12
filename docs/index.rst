.. GlyphX documentation master file

Welcome to GlyphX |version|
============================

**GlyphX** is a modern, SVG-first Python visualization library designed to replace
Matplotlib, Seaborn, and Plotly — with a cleaner API, richer interactivity, and
zero configuration required.

.. code-block:: python

   from glyphx import plot

   plot([1, 2, 3], [4, 5, 6], kind="line", title="My First Chart")
   # Auto-displays in Jupyter, opens browser in CLI — no .show() needed

.. code-block:: python

   # Full fluent API
   from glyphx import Figure
   from glyphx.series import LineSeries, BarSeries

   fig = (
       Figure(theme="dark")
       .set_title("Revenue vs Costs")
       .add(LineSeries(months, revenue, label="Revenue"))
       .add(LineSeries(months, costs, label="Costs", linestyle="dashed"))
       .tight_layout()
       .share("report.html")   # self-contained, zero-CDN output
   )

.. code-block:: python

   # Or go straight from a DataFrame
   import glyphx  # registers df.glyphx accessor

   df.glyphx.bar(x="month", y="revenue", hue="region", title="Revenue by Region")

.. code-block:: python

   # Full 3-D charts
   from glyphx import Figure3D, plot3d
   from glyphx.scatter3d import Scatter3DSeries

   fig = Figure3D(title="3D Scatter", theme="dark")
   fig.add(Scatter3DSeries(xs, ys, zs, c=zs, cmap="plasma"))
   fig.show()   # WebGL via Three.js; SVG fallback


Key Features
------------

- **SVG-first rendering** — crisp, scalable charts in every environment
- **Auto-display** — no ``plt.show()`` or ``.show()`` required
- **Method chaining** — every mutating method returns ``self``
- **DataFrame accessor** — ``df.glyphx.bar(x=..., y=..., hue=...)``
- **Natural language charts** — ``from_prompt("bar chart of sales by region", df=df)``
- **Linked interactive brushing** — ``Shift``\+drag filters all charts on a page
- **Self-contained shareable HTML** — ``fig.share()`` inlines all JS, works offline
- **25+ chart types** — including 3D scatter/surface/line/bar, raincloud, ECDF, treemap, and more
- **Automatic large-data downsampling** — M4 + LTTB pipeline, voxel thinning, grid
  decimation, and face culling keep SVG fast on datasets with millions of points
- **9 perceptually-uniform colormaps** — viridis, plasma, inferno, magma, cividis, and more
- **Statistical significance brackets** — built-in, no third-party plugin needed
- **PPTX export** — embed charts directly in PowerPoint slides
- **Full ARIA accessibility** — WCAG 2.1 AA, keyboard navigation, screen-reader descriptions
- **Full type annotations** — ``py.typed`` marker, mypy and pyright compatible
- **CLI tool** — ``glyphx plot data.csv --kind bar -o chart.html``
- **7 built-in themes** — including a correct Okabe-Ito colorblind-safe palette
- **Per-series downsampling control** — ``threshold=N`` and ``series.last_downsample_info``


Installation
------------

.. code-block:: bash

   pip install glyphx

   # Optional extras
   pip install "glyphx[pptx]"    # PowerPoint export
   pip install "glyphx[export]"  # PNG / JPG raster export
   pip install "glyphx[nlp]"     # Natural language chart generation


Project Links
-------------

- `GitHub Repository <https://github.com/kjkoeller/glyphx>`_
- `PyPI <https://pypi.org/project/glyphx/>`_
- `Issue Tracker <https://github.com/kjkoeller/glyphx/issues>`_


Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting_started
   usage
   customization
   advanced
   downsampling
   examples

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api_reference
