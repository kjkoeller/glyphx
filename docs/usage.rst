Usage Guide
===========

Basic Plotting
--------------

Use ``plot()`` for the fastest path to any chart type:

.. code-block:: python

   from glyphx import plot

   # Line chart
   plot([1, 2, 3, 4], [5, 7, 3, 9], kind="line",
        color="#2563eb", label="Series A",
        xlabel="X Axis", ylabel="Y Axis", title="Line Chart")

   # Bar chart with categorical X axis
   plot(["Mon","Tue","Wed","Thu","Fri"], [42, 61, 38, 75, 53],
        kind="bar", color="#7c3aed", title="Daily Active Users")

   # Scatter plot with colormap encoding
   plot(x_data, y_data, kind="scatter",
        c=color_values, cmap="viridis", size=7)

   # Histogram from raw data
   import numpy as np
   plot(data=np.random.normal(50, 10, 500), kind="hist", bins=25)

   # Pie chart
   plot(data=[35, 28, 22, 15], kind="pie",
        labels=["Product A","Product B","Product C","Other"])

.. image:: examples/basic_plotting.svg
   :alt: Scatter plot with viridis continuous color encoding
   :width: 760px
   :align: center

.. image:: examples/histogram.svg
   :alt: Bimodal histogram
   :width: 760px
   :align: center


Method Chaining
---------------

Every mutating ``Figure`` method returns ``self``, enabling full fluent chains:

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import LineSeries, BarSeries

   fig = (
       Figure(width=800, height=500)
       .set_title("Revenue Dashboard")
       .set_theme("dark")
       .set_size(900, 520)
       .set_xlabel("Month")
       .set_ylabel("USD ($M)")
       .set_legend("top-left")
       .add(LineSeries(months, revenue, color="#60a5fa", label="Revenue", width=2.5))
       .add(LineSeries(months, costs, color="#f87171", label="Costs", linestyle="dashed"))
       .annotate("Record High", x=11, y=2.9, arrow=True, color="#fbbf24")
       .tight_layout()
       .share("dashboard.html")
   )

Chainable ``Figure`` methods:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Method
     - Description
   * - ``.add(series, use_y2=False)``
     - Add a series; bind to right Y-axis with ``use_y2=True``
   * - ``.set_title(text)``
     - Set chart title
   * - ``.set_theme(name_or_dict)``
     - Apply a named or custom theme
   * - ``.set_size(width, height)``
     - Resize canvas
   * - ``.set_xlabel(text)``
     - X-axis label
   * - ``.set_ylabel(text)``
     - Y-axis label
   * - ``.set_legend(position)``
     - Legend position or ``False`` to hide
   * - ``.annotate(text, x, y, ...)``
     - Add a text annotation with optional arrow
   * - ``.add_stat_annotation(x1, x2, p_value)``
     - Add a significance bracket
   * - ``.tight_layout()``
     - Auto-adjust padding and rotate crowded labels
   * - ``.enable_crosshair()``
     - Synchronized crosshair across all charts on the page
   * - ``.show()``
     - Display (Jupyter or browser)
   * - ``.save(filename)``
     - Save to ``.svg``, ``.html``, ``.png``, ``.jpg``, or ``.pptx``
   * - ``.share(filename, title)``
     - Self-contained, zero-CDN HTML


DataFrame Accessor
------------------

Import ``glyphx`` once and every ``pd.DataFrame`` gains a ``.glyphx`` namespace.
All methods return a ``Figure`` for further chaining:

.. code-block:: python

   import pandas as pd
   import glyphx          # registers the .glyphx accessor

   df = pd.read_csv("sales.csv")

   # Basic charts
   df.glyphx.line(x="date",    y="revenue", title="Daily Revenue")
   df.glyphx.bar( x="product", y="units",   title="Units by Product")
   df.glyphx.scatter(x="spend", y="conversions")
   df.glyphx.hist(col="response_time", bins=20)
   df.glyphx.box(col="score", groupby="treatment_group")
   df.glyphx.pie(labels="category", values="share")
   df.glyphx.heatmap()        # uses all numeric columns

   # Groupby aggregation in one call
   df.glyphx.bar(
       groupby="region",
       y="revenue",
       agg="sum",             # sum | mean | count | max | min
       title="Revenue by Region",
   )

   # Hue splitting — one BarSeries per unique hue value, auto-colored
   # Each group gets its own label (appears in the legend) and a distinct
   # color from the active theme palette.
   df.glyphx.bar(
       x="month",
       y="revenue",
       hue="region",          # splits into North / South series
       title="Revenue by Month and Region",
   )

   # Full chain from the accessor
   (df.glyphx
      .bar(x="month", y="revenue", label="Revenue", auto_display=False)
      .set_theme("colorblind")
      .add_stat_annotation("Jan", "Jun", p_value=0.001)
      .set_xlabel("Month")
      .set_ylabel("Revenue ($M)")
      .share("monthly_report.html"))

.. image:: examples/pandas_example.svg
   :alt: Bar chart generated via the DataFrame accessor
   :width: 760px
   :align: center

.. note::
   When both ``x=`` and ``hue=`` are provided, ``bar()`` produces one
   ``BarSeries`` per unique hue value filtered to its own rows.
   When only ``hue=`` is given (without ``x=``), it aggregates using ``agg=``
   and creates one bar per group.


3-D Charts
----------

Use ``Figure3D`` for interactive Three.js output with an SVG fallback:

.. code-block:: python

   from glyphx import Figure3D, plot3d
   from glyphx.scatter3d import Scatter3DSeries
   from glyphx.surface3d  import Surface3DSeries
   from glyphx.line3d     import Line3DSeries
   from glyphx.bar3d      import Bar3DSeries
   from glyphx.contour    import ContourSeries
   import numpy as np

   # Scatter — continuous color via colormap
   fig = Figure3D(title="Gaussian Clusters", theme="dark",
                  azimuth=45, elevation=30,
                  xlabel="X", ylabel="Y", zlabel="Z")
   fig.add(Scatter3DSeries(xs, ys, zs, c=zs, cmap="plasma",
                           size=4, label="Points"))
   fig.show()      # WebGL interactive viewer
   fig.save("scatter3d.html")

   # Surface — z = f(x, y) over a regular grid
   x = np.linspace(-3, 3, 60)
   y = np.linspace(-3, 3, 60)
   Z = np.sin(np.sqrt(x[None,:]**2 + y[:,None]**2))
   fig = Figure3D(title="Sinc Surface")
   fig.add(Surface3DSeries(x, y, Z, cmap="viridis",
                           wireframe=True, alpha=0.9))
   fig.show()

   # Polyline through 3-D space
   t = np.linspace(0, 4*np.pi, 500)
   fig = Figure3D(title="Helix")
   fig.add(Line3DSeries(np.cos(t), np.sin(t), t / (4*np.pi),
                        color="#dc2626", width=2))
   fig.show()

   # Bar3D
   fig = Figure3D(title="3D Bars")
   fig.add(Bar3DSeries(x_cats, y_cats, heights,
                       color="#2563eb", label="Sales"))
   fig.show()

   # Contour lines / filled contours
   fig = Figure3D(title="Contour")
   fig.add(ContourSeries(x, y, Z, levels=10, filled=True, cmap="coolwarm"))
   fig.show()

   # One-liner 3-D
   plot3d(xs, ys, zs, kind="scatter", title="Quick 3D Scatter")
   plot3d(x, y, Z, kind="surface", title="Quick Surface")

``Figure3D`` constructor parameters:

.. list-table::
   :widths: 25 15 60
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``width``
     - ``900``
     - Canvas width in pixels
   * - ``height``
     - ``650``
     - Canvas height in pixels
   * - ``title``
     - ``""``
     - Chart title
   * - ``theme``
     - ``"default"``
     - Theme name (same 7 options as 2-D Figure)
   * - ``azimuth``
     - ``45.0``
     - Initial camera azimuth in degrees
   * - ``elevation``
     - ``30.0``
     - Initial camera elevation in degrees
   * - ``xlabel``
     - ``"X"``
     - X-axis label
   * - ``ylabel``
     - ``"Y"``
     - Y-axis label
   * - ``zlabel``
     - ``"Z"``
     - Z-axis label


Dual Y-Axis
-----------

Bind any series to the secondary (right-hand) Y-axis with ``use_y2=True``:

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import LineSeries, BarSeries

   fig = Figure(width=800, height=480)
   fig.set_title("Price & Volume")
   fig.add(LineSeries(dates, prices, color="#2563eb", label="Price (left)"))
   fig.add(BarSeries(dates, volume, color="#d97706", label="Volume (right)"),
           use_y2=True)
   fig.show()

.. image:: examples/dual_y.svg
   :alt: Dual Y-axis line and bar chart
   :width: 760px
   :align: center


Auto Display
------------

GlyphX detects its runtime environment automatically:

- **Jupyter notebook** — renders inline as an SVG cell output
- **CLI / script** — writes a temporary HTML file and opens it in the default browser
- **IDE** — falls back to the browser viewer

To suppress auto-display (e.g. when building charts to export only):

.. code-block:: python

   fig = Figure(auto_display=False)
   fig.save("chart.html")   # explicit save, no auto-open


Export and Sharing
------------------

.. code-block:: python

   fig.save("chart.svg")        # vector SVG
   fig.save("chart.html")       # interactive HTML (zoom, pan, tooltips, export buttons)
   fig.save("chart.png")        # raster PNG  — requires: pip install "glyphx[export]"
   fig.save("chart.jpg")        # raster JPG  — requires: pip install "glyphx[export]"
   fig.save("chart.pptx")       # PowerPoint  — requires: pip install "glyphx[pptx]"

   # Self-contained HTML — zero external dependencies
   html = fig.share()                    # returns HTML string
   fig.share("report.html")             # also writes to disk
   fig.share("report.html", title="Q3") # custom <title> tag

``fig.share()`` inlines all JavaScript into a single file that works in email
clients, Confluence, Notion, GitHub Pages, and offline environments.


Log Scale
---------

Pass ``xscale`` or ``yscale`` to the ``Figure`` constructor:

.. code-block:: python

   fig = Figure(yscale="log")
   fig.add(LineSeries(x, y))
   fig.show()


Natural Language Chart Generation
----------------------------------

Requires ``pip install "glyphx[nlp]"`` and an ``ANTHROPIC_API_KEY`` environment variable.

.. code-block:: python

   from glyphx import from_prompt
   import pandas as pd

   df = pd.read_csv("sales.csv")

   fig = from_prompt("bar chart of total revenue by region, dark theme", df=df)
   fig = from_prompt("scatter plot showing a strong positive correlation")
   fig = from_prompt("top 10 products by revenue, sorted descending", df=df)


CLI Tool
--------

Plot any CSV, JSON, or Excel file directly from the terminal:

.. code-block:: bash

   glyphx plot sales.csv --x month --y revenue --kind bar -o chart.html
   glyphx plot data.csv --x date --y revenue --kind line --theme dark --open
   glyphx suggest data.csv
   glyphx version

Supported input formats: ``.csv`` ``.tsv`` ``.json`` ``.jsonl`` ``.xlsx`` ``.xls``

Supported output formats: ``.svg`` ``.html`` ``.png`` ``.jpg`` ``.pptx``
