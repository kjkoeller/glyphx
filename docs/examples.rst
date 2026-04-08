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

   df.glyphx.bar(x="month", y="revenue", title="Monthly Revenue")
   df.glyphx.bar(groupby="region", y="revenue", agg="sum")


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
