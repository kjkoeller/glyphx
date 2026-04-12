Examples
========

Basic Charts
------------

Line Chart — Multi-Series with Annotations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/Quick_Example.svg
   :alt: Multi-series line chart with legend and annotations
   :width: 760px
   :align: center

.. code-block:: python

   fig = (
       Figure(width=760, height=460)
       .set_title("Monthly Revenue vs Operating Costs  (2024)")
       .set_xlabel("Month").set_ylabel("USD ($M)")
       .add(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=3))
       .add(LineSeries(months, costs,   color="#dc2626", label="Costs",   linestyle="dashed"))
       .set_legend("top-left")
       .annotate("Peak Revenue", x="Dec", y=3.00, arrow=True, color="#2563eb")
       .tight_layout()
   )
   fig.show()

Scatter with Colormap Encoding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/basic_plotting.svg
   :alt: Scatter plot with viridis colormap
   :width: 760px
   :align: center

.. code-block:: python

   ScatterSeries(x, y, c=z_values, cmap="viridis", size=7)

Histogram — Bimodal Distribution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/histogram.svg
   :alt: Bimodal histogram
   :width: 760px
   :align: center

.. code-block:: python

   import numpy as np
   data = np.concatenate([np.random.normal(50,8,400), np.random.normal(78,6,200)])
   Figure().add(HistogramSeries(data.tolist(), bins=28, color="#0891b2")).show()

Pie and Donut Charts
~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/pie_chart.svg
   :alt: Pie chart
   :width: 500px
   :align: center

.. image:: examples/donut_chart.svg
   :alt: Donut chart
   :width: 500px
   :align: center

Heatmap — Correlation Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/heatmap.svg
   :alt: KPI correlation heatmap
   :width: 680px
   :align: center

Box Plot — Multi-Group
~~~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/box_plot.svg
   :alt: Multi-group box plot
   :width: 680px
   :align: center


New 2-D Chart Types
-------------------

Bubble Chart
~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.bubble import BubbleSeries

   fig = Figure().set_title("Market Cap vs Growth Rate")
   fig.add(BubbleSeries(x, y, sizes=market_cap, c=growth_rate,
                        cmap="plasma", label="Companies"))
   fig.show()

Sunburst Chart
~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.sunburst import SunburstSeries

   fig = Figure(width=600, height=600).set_title("Org Revenue Breakdown")
   fig.add(SunburstSeries(
       labels=["Total", "EMEA", "APAC", "Americas",
               "UK", "DE", "JP", "AU", "US", "CA"],
       parents=["",     "Total","Total","Total",
                "EMEA","EMEA","APAC","APAC","Americas","Americas"],
       values= [0,      0,      0,      0,
                420,    310,    280,    190,   850,       320],
   ))
   fig.show()

Parallel Coordinates
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.parallel_coords import ParallelCoordinatesSeries

   fig = Figure(width=900, height=500).set_title("Iris Dataset")
   fig.add(ParallelCoordinatesSeries(
       data=df[["sepal_length","sepal_width","petal_length","petal_width"]],
       labels=df["species"],
       cmap="viridis",
   ))
   fig.show()

Diverging Bar Chart
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.diverging_bar import DivergingBarSeries

   fig = Figure().set_title("YoY Growth by Region")
   fig.add(DivergingBarSeries(
       categories=["North","South","East","West","Central"],
       values=    [  12,    -8,     21,    -3,      15],
       color_pos="#2563eb",
       color_neg="#dc2626",
   ))
   fig.show()


3-D Charts
----------

3-D Scatter
~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure3D
   from glyphx.scatter3d import Scatter3DSeries
   import numpy as np

   rng = np.random.default_rng(42)
   xs = rng.normal(0, 1, 500)
   ys = rng.normal(0, 1, 500)
   zs = np.sin(xs) + np.cos(ys)

   fig = Figure3D(title="Gaussian Scatter", theme="dark",
                  azimuth=45, elevation=25)
   fig.add(Scatter3DSeries(xs, ys, zs, c=zs, cmap="plasma", size=4))
   fig.show()

3-D Surface
~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure3D
   from glyphx.surface3d import Surface3DSeries
   import numpy as np

   x = np.linspace(-3, 3, 80)
   y = np.linspace(-3, 3, 80)
   Z = np.sin(np.sqrt(x[None,:]**2 + y[:,None]**2))

   fig = Figure3D(title="Sinc Surface", azimuth=30, elevation=35)
   fig.add(Surface3DSeries(x, y, Z, cmap="viridis", wireframe=True))
   fig.show()

3-D Line (Helix)
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure3D
   from glyphx.line3d import Line3DSeries
   import numpy as np

   t = np.linspace(0, 6 * np.pi, 1_000)
   fig = Figure3D(title="Helix")
   fig.add(Line3DSeries(np.cos(t), np.sin(t), t / (6 * np.pi),
                        color="#dc2626", width=2.5, label="Helix"))
   fig.show()

Contour Plot
~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure3D
   from glyphx.contour import ContourSeries
   import numpy as np

   x = np.linspace(-2, 2, 100)
   y = np.linspace(-2, 2, 100)
   Z = np.exp(-(x[None,:]**2 + y[:,None]**2))

   fig = Figure3D(title="Gaussian Contour")
   fig.add(ContourSeries(x, y, Z, levels=10, filled=True, cmap="coolwarm"))
   fig.show()

Large-Data 3-D (auto-downsampled)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GlyphX automatically downsamples 3-D series; the render stays fast regardless
of input size:

.. code-block:: python

   import numpy as np
   from glyphx import Figure3D
   from glyphx.scatter3d import Scatter3DSeries

   rng = np.random.default_rng(0)
   n = 500_000
   xs, ys, zs = rng.uniform(0, 1, n), rng.uniform(0, 1, n), rng.uniform(0, 1, n)

   fig = Figure3D(title="500k Points — auto-thinned")
   s3 = Scatter3DSeries(xs, ys, zs, cmap="plasma")
   fig.add(s3)
   fig.render_svg()

   print(s3.last_downsample_info)
   # {'algorithm': 'voxel-3D', 'original_n': 500000, 'thinned_n': 4913}


Themes
------

Dark Theme
~~~~~~~~~~~

.. image:: examples/dark_theme.svg
   :alt: Dark theme example
   :width: 760px
   :align: center

.. code-block:: python

   Figure(theme="dark")

Colorblind-Safe Theme
~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/colorblind_theme.svg
   :alt: Colorblind Okabe-Ito theme
   :width: 760px
   :align: center

.. code-block:: python

   Figure(theme="colorblind")   # Okabe-Ito palette

Line Styles
~~~~~~~~~~~

.. image:: examples/green_dashed_line.svg
   :alt: All four linestyles
   :width: 760px
   :align: center

.. code-block:: python

   LineSeries(x, y, linestyle="solid")
   LineSeries(x, y, linestyle="dashed")
   LineSeries(x, y, linestyle="dotted")
   LineSeries(x, y, linestyle="longdash")

Colormap Encoding
~~~~~~~~~~~~~~~~~

.. image:: examples/colormaps.svg
   :alt: Plasma colormap scatter encoding
   :width: 760px
   :align: center


Layout
------

2×2 Subplot Grid
~~~~~~~~~~~~~~~~

.. image:: examples/grid_layout.svg
   :alt: 2x2 subplot grid
   :width: 760px
   :align: center

.. code-block:: python

   fig = Figure(rows=2, cols=2, width=800, height=580)
   fig.add_axes(0,0).add_series(LineSeries(...))
   fig.add_axes(0,1).add_series(BarSeries(...))
   fig.add_axes(1,0).add_series(ScatterSeries(...))
   fig.add_axes(1,1).add_series(HistogramSeries(...))

Dual Y-Axis
~~~~~~~~~~~

.. image:: examples/dual_y.svg
   :alt: Dual Y-axis line and bar
   :width: 760px
   :align: center

.. code-block:: python

   fig.add(LineSeries(x, prices, label="Price (left)"))
   fig.add(BarSeries(x, volume, label="Volume (right)"), use_y2=True)


DataFrame Accessor
------------------

.. image:: examples/pandas_example.svg
   :alt: Bar chart from DataFrame accessor
   :width: 760px
   :align: center

.. code-block:: python

   import glyphx  # registers df.glyphx

   # Basic
   df.glyphx.bar(x="month", y="revenue", title="Monthly Revenue")
   df.glyphx.bar(groupby="region", y="revenue", agg="sum")

   # Hue splitting — one series per region, auto-colored
   df.glyphx.bar(x="month", y="revenue", hue="region",
                 title="Revenue by Month and Region")


Statistical Charts
------------------

ECDF
~~~~

.. image:: examples/ecdf.svg
   :alt: ECDF comparing control and treatment
   :width: 760px
   :align: center

.. code-block:: python

   from glyphx.ecdf import ECDFSeries

   fig = (
       Figure()
       .add(ECDFSeries(ctrl.tolist(),  color="#3b82f6", label="Control"))
       .add(ECDFSeries(treat.tolist(), color="#ef4444", label="Treatment"))
   )

Raincloud Plot
~~~~~~~~~~~~~~

.. image:: examples/raincloud.svg
   :alt: Raincloud jitter + violin + box
   :width: 760px
   :align: center

.. code-block:: python

   from glyphx.raincloud import RaincloudSeries

   fig.add(RaincloudSeries(groups, categories=["Control","Low","High"], seed=42))

Significance Brackets
~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/stat_annotations.svg
   :alt: Significance brackets on bar chart
   :width: 640px
   :align: center

.. code-block:: python

   fig.add_stat_annotation("Control", "Drug A", p_value=0.0002)
   fig.add_stat_annotation("Control", "Drug B", p_value=0.028, y_offset=32)


Financial Charts
----------------

Candlestick OHLC
~~~~~~~~~~~~~~~~

.. image:: examples/candlestick.svg
   :alt: Candlestick OHLC chart
   :width: 700px
   :align: center

Waterfall Bridge Chart
~~~~~~~~~~~~~~~~~~~~~~~

.. image:: examples/waterfall.svg
   :alt: Waterfall revenue bridge
   :width: 720px
   :align: center

Treemap
~~~~~~~

.. image:: examples/treemap.svg
   :alt: Squarified treemap
   :width: 720px
   :align: center


Streaming Data
--------------

.. image:: examples/streaming.svg
   :alt: Live streaming sensor data
   :width: 760px
   :align: center

.. code-block:: python

   from glyphx.streaming import StreamingSeries

   stream = StreamingSeries(max_points=120, color="#2563eb", label="Sensor A")
   fig.add(stream)

   with stream.live(fig, fps=10) as s:
       for reading in sensor_generator():
           s.push(reading)


Downsampling Examples
---------------------

See also :doc:`downsampling` for the complete downsampling API reference.

Two-stage line pipeline (M4 + LTTB)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.downsample import maybe_downsample_line
   import numpy as np

   x = np.linspace(0, 1, 2_000_000)
   y = np.sin(x * 500) + np.random.normal(0, 0.1, len(x))

   x_down, y_down = maybe_downsample_line(x, y, pixel_width=800)
   print(f"{len(x):,} → {len(x_down):,} points")

Per-series threshold override
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import LineSeries

   x = list(range(100_000))
   y = [i**0.5 for i in x]

   # Keep at most 500 points for this series
   fig = Figure()
   fig.add(LineSeries(x, y, label="sqrt(x)", threshold=500))
   fig.show()

Inspect downsampling metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import ScatterSeries
   import numpy as np

   rng = np.random.default_rng(0)
   n = 50_000
   sc = ScatterSeries(rng.uniform(0,1,n).tolist(),
                      rng.uniform(0,1,n).tolist())
   Figure().add(sc).render_svg()

   info = sc.last_downsample_info
   print(f"Algorithm : {info['algorithm']}")
   print(f"Original  : {info['original_n']:,}")
   print(f"Thinned   : {info['thinned_n']:,}")
