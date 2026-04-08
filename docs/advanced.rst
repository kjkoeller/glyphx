Advanced Features
=================

Interactive Brushing
--------------------

Hold ``Shift`` and drag on any chart to draw a selection rectangle.
All ``glyphx-point`` elements sharing the same X values across **every chart
on the page** are highlighted; everything else dims to 10% opacity.

- ``Shift``\+drag — draw the selection
- ``Escape`` — clear the selection
- Click outside any chart — clear the selection

.. code-block:: python

   from glyphx import Figure
   from glyphx.layout import grid
   from glyphx.series import ScatterSeries, LineSeries

   f1 = Figure(); f1.add(ScatterSeries(x, y1, label="Sales"))
   f2 = Figure(); f2.add(LineSeries(x, y2, label="Revenue"))

   html = grid([f1, f2], rows=1, cols=2)
   open("linked_dashboard.html", "w").write(html)

A blue hint badge appears on all charts when ``Shift`` is held, so the
interaction is discoverable for users who haven't seen it before.


Synchronized Crosshair
-----------------------

Enable a vertical crosshair that syncs across all charts on the page:

.. code-block:: python

   fig.enable_crosshair()
   fig.share("report.html")

When the user moves their cursor over any chart, a dashed vertical line appears
at the same relative X position on every other chart, and the nearest data point's
tooltip is shown.


Self-Contained Shareable HTML
-------------------------------

``fig.share()`` generates a single ``.html`` file with all JavaScript inlined.
No CDN, no server, no external files — it works anywhere:

.. code-block:: python

   # Returns the HTML as a string
   html = fig.share()

   # Also writes to disk
   fig.share("report.html")

   # Custom page title
   fig.share("report.html", title="Q3 Revenue Report")

The output is tested in Gmail, Outlook Web, Confluence, Notion, GitHub Pages,
and offline (air-gapped) environments.


Statistical Charts
------------------

ECDF
~~~~

The empirical CDF shows the proportion of observations ≤ each value.
No bin-width choice required:

.. code-block:: python

   from glyphx import Figure
   from glyphx.ecdf import ECDFSeries

   fig = (
       Figure()
       .set_title("Response Time Distribution")
       .set_xlabel("ms").set_ylabel("Cumulative Proportion")
       .add(ECDFSeries(control_data,   label="Control",   color="#3b82f6"))
       .add(ECDFSeries(treatment_data, label="Treatment", color="#ef4444"))
   )
   fig.show()

Pass ``complementary=True`` to plot the survival function (1 − ECDF).


Raincloud Plot
~~~~~~~~~~~~~~

Combines three views of a distribution in one series:

- **Raw jittered points** (the "rain") — shows individual observations
- **Half-violin** (KDE density) — shows the shape
- **Box-and-whisker** — shows quantile summary

.. code-block:: python

   from glyphx.raincloud import RaincloudSeries

   fig = Figure()
   fig.add(RaincloudSeries(
       data=[control, low_dose, high_dose],
       categories=["Control", "Low Dose", "High Dose"],
       violin_width=35,
       seed=42,            # reproducible jitter
   ))
   fig.show()


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

Bullish candles (close ≥ open) are green by default; bearish candles are red.
Both colors are configurable via ``up_color=`` and ``down_color=``.


Waterfall / Bridge Chart
~~~~~~~~~~~~~~~~~~~~~~~~~

Pass ``None`` as a value to auto-compute the running total bar:

.. code-block:: python

   from glyphx.waterfall import WaterfallSeries

   fig = Figure().set_title("Q3 Revenue Bridge ($M)")
   fig.add(WaterfallSeries(
       labels=["Q2 Revenue","New Customers","Upsells","Churn","Discounts","Q3 Revenue"],
       values=[8.2, 2.1, 0.9, -0.6, -0.3, None],   # None = Σ of above
       show_values=True,
   ))
   fig.show()


Hierarchical Charts
-------------------

Treemap
~~~~~~~

Uses the Bruls et al. squarified algorithm to minimise aspect ratios:

.. code-block:: python

   from glyphx.treemap import TreemapSeries

   fig = Figure(width=700, height=500)
   fig.add(TreemapSeries(
       labels=["Cloud","AI/ML","Mobile","Security","Data","IoT"],
       values=[4200, 3100, 2800, 2100, 1900, 900],
       cmap="viridis",       # any built-in colormap
       show_values=True,
   ))
   fig.show()

Rectangle areas are proportional to values. Labels and percentages are hidden
automatically when a rectangle is too small to display them legibly.


Streaming / Real-Time
---------------------

``StreamingSeries`` maintains a sliding window of the most recent N data points:

.. code-block:: python

   from glyphx.streaming import StreamingSeries

   fig = Figure().set_title("Live Sensor Feed")
   stream = StreamingSeries(max_points=100, color="#7c3aed", label="Sensor")
   fig.add(stream)

   # Push values one at a time
   stream.push(42.0)

   # Push in bulk
   stream.push_many([41, 42, 43, 44, 45])

   # Reset the buffer
   stream.reset()

**Jupyter live mode** — re-renders at a target FPS with no server:

.. code-block:: python

   with stream.live(fig, fps=10) as s:
       for reading in sensor_generator():
           s.push(reading)

``with stream.live(fig)`` uses ``IPython.display.clear_output(wait=True)`` and
``display(SVG(...))`` on each frame — no Dash, no WebSocket, no running server.


Accessibility
-------------

Every chart GlyphX renders meets WCAG 2.1 AA standards:

- ``role="img"`` and ``aria-labelledby`` on the root ``<svg>`` element
- ``<title>`` and ``<desc>`` landmark elements with auto-generated text
- ``tabindex="0"`` and ``role="graphics-symbol"`` on every data point
- ``focusable="false"`` prevents the SVG root from stealing focus

**Keyboard navigation:**

- ``Tab`` / ``Shift``\+``Tab`` — move between data points
- ``Arrow`` keys — move to next/previous point within a series
- ``Enter`` / ``Space`` — show the tooltip for the focused point
- ``Escape`` — dismiss tooltip and blur

**Auto-generated alt text:**

.. code-block:: python

   alt = fig.to_alt_text()
   # → 'Line chart titled "Monthly Revenue". X axis: Month. Y axis: USD.
   #    Series "Revenue": 12 data points. Ranges from 98 (Mar) to 300 (Dec).'

The alt text is automatically embedded in the SVG ``<desc>`` element and
returned by ``fig.to_alt_text()`` for use in ``<img alt="">`` attributes.


PPTX Export
-----------

Requires ``pip install "glyphx[pptx]"`` (python-pptx + cairosvg + system libcairo).

.. code-block:: python

   fig.save("chart.pptx")

The chart is rasterised to PNG at 2× resolution and inserted as a full-slide
picture. If ``fig.title`` is set, it appears as a bold text box above the chart.

.. note::
   On macOS, install libcairo with ``brew install cairo``.
   On Ubuntu/Debian: ``sudo apt-get install libcairo2``.


Seaborn-Style Composite Plots
-------------------------------

GlyphX includes seaborn-compatible composite chart functions:

.. code-block:: python

   from glyphx import pairplot, jointplot, lmplot, facet_plot

   # Pairwise scatter matrix
   pairplot(df)

   # Scatter with marginal histograms
   jointplot(df, x="a", y="b")

   # Scatter with regression line
   lmplot(df, x="x", y="y")

   # Faceted grid split by a categorical column
   facet_plot(df, x="value", col="group", kind="hist")


Violin Plots
------------

GlyphX uses a pure-NumPy Gaussian KDE (no scipy required):

.. code-block:: python

   from glyphx.violin_plot import ViolinPlotSeries

   fig = Figure()
   fig.add(ViolinPlotSeries(
       data=[group_a, group_b, group_c],
       show_median=True,
       show_box=True,
   ))
   fig.show()
