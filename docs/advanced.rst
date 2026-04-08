Advanced Features
=================

Interactive Brushing
--------------------

Hold ``Shift`` and drag on any chart to draw a selection rectangle.
All charts on the page sharing the same X values highlight matching
points and dim everything else.

.. code-block:: python

   from glyphx.layout import grid
   from glyphx.series import ScatterSeries

   f1 = Figure(); f1.add(ScatterSeries(x, y1, label="Sales"))
   f2 = Figure(); f2.add(ScatterSeries(x, y2, label="Revenue"))

   html = grid([f1, f2], rows=1, cols=2)
   open("linked_dashboard.html", "w").write(html)

- ``Shift``\+drag — draw the selection
- ``Escape`` — clear the selection


Synchronized Crosshair
-----------------------

.. code-block:: python

   fig.enable_crosshair()
   fig.share("report.html")


Self-Contained Shareable HTML
-------------------------------

.. code-block:: python

   fig.share("report.html")                    # writes to disk
   fig.share("report.html", title="Q3 Report") # custom page title
   html = fig.share()                           # returns string


Statistical Charts
------------------

ECDF
~~~~

.. code-block:: python

   from glyphx.ecdf import ECDFSeries

   fig = (
       Figure()
       .set_title("Response Time Distribution")
       .add(ECDFSeries(control_data,   label="Control",   color="#3b82f6"))
       .add(ECDFSeries(treatment_data, label="Treatment", color="#ef4444"))
   )
   fig.show()

.. image:: examples/ecdf.svg
   :alt: ECDF comparing control vs treatment groups
   :width: 760px
   :align: center


Raincloud Plot
~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.raincloud import RaincloudSeries

   fig = Figure()
   fig.add(RaincloudSeries(
       data=[control, low_dose, high_dose],
       categories=["Control", "Low Dose", "High Dose"],
       violin_width=35,
       seed=42,
   ))
   fig.show()

.. image:: examples/raincloud.svg
   :alt: Raincloud plot showing distribution by group
   :width: 760px
   :align: center


Box Plot
~~~~~~~~

.. code-block:: python

   from glyphx.series import BoxPlotSeries

   fig = Figure()
   fig.add(BoxPlotSeries(
       [control, drug_a, drug_b, drug_c],
       categories=["Control","Drug A","Drug B","Drug C"],
       box_width=30,
   ))
   fig.show()

.. image:: examples/box_plot.svg
   :alt: Multi-group box plot
   :width: 680px
   :align: center


Heatmap
~~~~~~~

.. code-block:: python

   from glyphx.series import HeatmapSeries

   fig = Figure()
   fig.add(HeatmapSeries(
       corr_matrix,
       row_labels=labels,
       col_labels=labels,
       show_values=True,
   ))
   fig.show()

.. image:: examples/heatmap.svg
   :alt: KPI correlation heatmap
   :width: 680px
   :align: center


Financial Charts
----------------

Candlestick / OHLC
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.candlestick import CandlestickSeries

   fig = Figure().set_title("AAPL — Daily OHLC")
   fig.add(CandlestickSeries(
       dates=["Mon","Tue","Wed","Thu","Fri"],
       open= [150, 153, 149, 155, 158],
       high= [155, 157, 153, 160, 162],
       low=  [148, 151, 146, 154, 156],
       close=[153, 149, 155, 158, 160],
   ))
   fig.show()

.. image:: examples/candlestick.svg
   :alt: OHLC candlestick chart
   :width: 700px
   :align: center


Waterfall / Bridge Chart
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.waterfall import WaterfallSeries

   fig = Figure().set_title("Q3 Revenue Bridge ($M)")
   fig.add(WaterfallSeries(
       labels=["Q2 Revenue","New Logos","Expansions","Churn","Discounts","Q3 Revenue"],
       values=[8.2, 2.1, 0.9, -0.8, -0.4, None],
       show_values=True,
   ))
   fig.show()

.. image:: examples/waterfall.svg
   :alt: Waterfall bridge chart
   :width: 720px
   :align: center


Hierarchical Charts
-------------------

Treemap
~~~~~~~

.. code-block:: python

   from glyphx.treemap import TreemapSeries

   fig = Figure(width=700, height=500)
   fig.add(TreemapSeries(
       labels=["Cloud","AI/ML","Mobile","Security","Data","Networking","IoT"],
       values=[4200, 3100, 2800, 2100, 1900, 1400, 900],
       cmap="viridis",
       show_values=True,
   ))
   fig.show()

.. image:: examples/treemap.svg
   :alt: Squarified treemap
   :width: 720px
   :align: center


Pie and Donut Charts
--------------------

.. code-block:: python

   from glyphx.series import PieSeries, DonutSeries
   from glyphx.colormaps import colormap_colors

   fig = Figure(width=500, height=440)
   fig.add(PieSeries([38,25,18,11,8],
       labels=["GlyphX","Matplotlib","Plotly","Seaborn","Other"],
       colors=colormap_colors("plasma", 5)))
   fig.show()

.. image:: examples/pie_chart.svg
   :alt: Pie chart with plasma colormap
   :width: 500px
   :align: center

.. image:: examples/donut_chart.svg
   :alt: Donut chart with viridis colormap
   :width: 500px
   :align: center


Streaming / Real-Time
---------------------

.. code-block:: python

   from glyphx.streaming import StreamingSeries

   fig = Figure().set_title("Live Sensor Feed")
   stream = StreamingSeries(max_points=100, color="#7c3aed", label="Sensor")
   fig.add(stream)

   # Push values one at a time
   stream.push(42.0)

   # Jupyter live mode — no server required
   with stream.live(fig, fps=10) as s:
       for reading in sensor_generator():
           s.push(reading)

.. image:: examples/streaming.svg
   :alt: Streaming real-time sensor feed
   :width: 760px
   :align: center


Accessibility
-------------

Every chart meets WCAG 2.1 AA standards:

- ``role="img"`` and ``aria-labelledby`` on the root ``<svg>`` element
- ``<title>`` and ``<desc>`` with auto-generated descriptions
- ``tabindex="0"`` and ``role="graphics-symbol"`` on every data point
- ``Tab`` / ``Arrow`` key navigation between data points
- ``Enter`` / ``Space`` to show tooltips from keyboard
- ``Escape`` to dismiss

.. code-block:: python

   alt = fig.to_alt_text()
   # 'Line chart titled "Monthly Revenue". X axis: Month. Y axis: USD.
   #  Series "Revenue": 12 data points. Ranges from 98 (Mar) to 300 (Dec).'


PPTX Export
-----------

Requires ``pip install "glyphx[pptx]"`` and the system ``libcairo`` library.

.. code-block:: python

   fig.save("chart.pptx")

.. note::
   On macOS: ``brew install cairo``.
   On Ubuntu/Debian: ``sudo apt-get install libcairo2``.


Violin Plots
------------

Pure-NumPy KDE — no scipy required:

.. code-block:: python

   from glyphx.violin_plot import ViolinPlotSeries

   fig = Figure()
   fig.add(ViolinPlotSeries(
       data=[group_a, group_b, group_c],
       show_median=True,
       show_box=True,
   ))
   fig.show()


Seaborn-Style Composite Plots
-------------------------------

.. code-block:: python

   from glyphx import pairplot, jointplot, lmplot, facet_plot

   pairplot(df)
   jointplot(df, x="a", y="b")
   lmplot(df, x="x", y="y")
   facet_plot(df, x="value", col="group", kind="hist")
