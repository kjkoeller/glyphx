Examples
========

Basic Charts
------------

Line Chart — Multi-Series with Legend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import LineSeries

   months  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
   revenue = [120, 135, 98, 170, 145, 190, 210, 175, 230, 205, 260, 300]
   costs   = [80,  90,  65, 100,  95, 110, 130, 105, 140, 120, 155, 175]

   fig = (
       Figure(width=720, height=460)
       .set_title("Monthly Revenue vs Costs")
       .set_xlabel("Month").set_ylabel("USD (thousands)")
       .add(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=2.5))
       .add(LineSeries(months, costs, color="#dc2626", label="Costs", linestyle="dashed"))
       .set_legend("top-left")
       .tight_layout()
   )
   fig.show()

Bar Chart with Error Bars
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.series import BarSeries

   products = ["Widget A","Widget B","Widget C","Widget D","Widget E"]
   sales    = [4200, 3100, 5800, 2400, 6700]
   errors   = [210,  155,  290,  120,  335]

   fig = (
       Figure()
       .set_title("Product Sales Q3 (±SE)")
       .add(BarSeries(products, sales, color="#7c3aed", label="Units", yerr=errors))
   )
   fig.show()

Scatter with Colormap Encoding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import numpy as np
   from glyphx.series import ScatterSeries

   np.random.seed(42)
   x = np.random.randn(100)
   y = 0.7 * x + np.random.randn(100) * 0.5
   z = np.sin(x) + np.cos(y)     # third variable encoded as color

   fig = (
       Figure()
       .set_title("Scatter with Viridis Color Encoding")
       .add(ScatterSeries(x.tolist(), y.tolist(), c=z.tolist(), cmap="viridis", size=7))
   )
   fig.show()

Dual Y-Axis
~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import LineSeries, BarSeries

   months = ["Jan","Feb","Mar","Apr","May","Jun"]
   prices = [142, 148, 151, 145, 160, 158]
   volume = [2.1, 3.4, 1.8, 4.2, 2.9, 3.1]

   fig = Figure(width=720, height=460)
   fig.set_title("Stock Price & Volume")
   fig.add(LineSeries(months, prices, color="#2563eb", label="Price (left)", width=2))
   fig.add(BarSeries(months, volume, color="#d97706", label="Volume M (right)",
                     bar_width=0.5), use_y2=True)
   fig.legend_pos = "top-left"
   fig.show()

Heatmap — Correlation Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx.series import HeatmapSeries

   labels = ["Revenue","Traffic","Conv Rate","Bounce"]
   corr   = [
       [1.00, 0.85, 0.42, -0.31],
       [0.85, 1.00, 0.61, -0.18],
       [0.42, 0.61, 1.00,  0.23],
       [-0.31,-0.18, 0.23,  1.00],
   ]

   fig = Figure(width=600, height=440)
   fig.set_title("KPI Correlation Matrix")
   fig.add(HeatmapSeries(
       corr,
       row_labels=labels,
       col_labels=labels,
       show_values=True,
       cmap=["#1e40af","#93c5fd","#f0f0f0","#fca5a5","#b91c1c"],
   ))
   fig.show()


Statistical Charts
------------------

ECDF — Compare Two Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import numpy as np
   from glyphx import Figure
   from glyphx.ecdf import ECDFSeries

   ctrl  = np.random.normal(50, 12, 300)
   treat = np.random.normal(65, 9,  300)

   fig = (
       Figure()
       .set_title("ECDF: Control vs Treatment")
       .set_xlabel("Response Time (ms)")
       .set_ylabel("Cumulative Proportion")
       .set_legend("top-left")
       .add(ECDFSeries(ctrl.tolist(),  color="#3b82f6", label="Control"))
       .add(ECDFSeries(treat.tolist(), color="#ef4444", label="Treatment"))
   )
   fig.show()

Raincloud Plot
~~~~~~~~~~~~~~

.. code-block:: python

   import numpy as np
   from glyphx import Figure
   from glyphx.raincloud import RaincloudSeries

   groups = [
       np.random.normal(40,  8, 60),
       np.random.normal(55, 10, 60),
       np.random.normal(70,  7, 60),
   ]

   fig = (
       Figure(width=680, height=480)
       .set_title("Score Distribution by Treatment")
       .set_ylabel("Score")
       .add(RaincloudSeries(groups, categories=["Control","Low Dose","High Dose"]))
   )
   fig.show()

Statistical Significance Brackets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import BarSeries
   import numpy as np

   ctrl  = np.random.normal(45, 8, 60)
   drugA = np.random.normal(62, 7, 60)
   drugB = np.random.normal(58, 9, 60)
   means  = [ctrl.mean(), drugA.mean(), drugB.mean()]
   errors = [ctrl.std()/8, drugA.std()/8, drugB.std()/8]

   fig = (
       Figure()
       .set_title("Treatment Efficacy")
       .add(BarSeries(["Control","Drug A","Drug B"], means, yerr=errors,
                      color="#60a5fa", label="Mean Score"))
       .add_stat_annotation("Control", "Drug A", p_value=0.0003)
       .add_stat_annotation("Control", "Drug B", p_value=0.031, y_offset=30)
   )
   fig.show()


Financial Charts
----------------

Candlestick OHLC
~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.candlestick import CandlestickSeries

   fig = Figure(width=660, height=460)
   fig.set_title("AAPL — Intraday OHLC")
   fig.add(CandlestickSeries(
       dates=["Mon","Tue","Wed","Thu","Fri"],
       open= [150, 153, 149, 155, 158],
       high= [155, 157, 153, 160, 162],
       low=  [148, 151, 146, 154, 156],
       close=[153, 149, 155, 158, 160],
   ))
   fig.show()

Waterfall Bridge Chart
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.waterfall import WaterfallSeries

   fig = Figure(width=680, height=460)
   fig.set_title("Q3 Revenue Bridge ($M)")
   fig.add(WaterfallSeries(
       labels=["Q2 Revenue","New Customers","Upsells","Churn","Discounts","Q3 Revenue"],
       values=[8.2, 2.1, 0.9, -0.6, -0.3, None],
       show_values=True,
   ))
   fig.show()

Treemap
~~~~~~~

.. code-block:: python

   from glyphx import Figure
   from glyphx.treemap import TreemapSeries

   fig = Figure(width=700, height=500)
   fig.set_title("Tech Portfolio Allocation ($M)")
   fig.add(TreemapSeries(
       labels=["Cloud","AI/ML","Mobile","Security","Data","Networking"],
       values=[4200, 3100, 2800, 2100, 1900, 1400],
       cmap="viridis",
       show_values=True,
   ))
   fig.show()


Streaming Data
--------------

.. code-block:: python

   import numpy as np
   from glyphx import Figure
   from glyphx.streaming import StreamingSeries

   fig    = Figure().set_title("Live Sensor Feed")
   stream = StreamingSeries(max_points=80, color="#7c3aed", label="Sensor")
   fig.add(stream)

   # Simulate 200 readings​​​​​​​​​​​​​​​​
   t = np.linspace(0, 6 * np.pi, 200)
   for val in np.sin(t) * 10 + np.random.randn(200) * 1.5 + 25:
       stream.push(float(val))

   fig.show()

   # Jupyter live mode
   # with stream.live(fig, fps=10) as s:
   #     for reading in sensor.stream():
   #         s.push(reading)


DataFrame Accessor
------------------

.. code-block:: python

   import pandas as pd
   import glyphx

   df = pd.DataFrame({
       "quarter": ["Q1 22","Q2 22","Q3 22","Q4 22","Q1 23","Q2 23","Q3 23","Q4 23"],
       "revenue": [1.2, 1.5, 1.3, 1.8, 2.1, 2.4, 2.2, 2.9],
       "region":  ["North","South","North","South","North","South","North","South"],
   })

   # Simple bar chart
   df.glyphx.bar(x="quarter", y="revenue", title="Quarterly Revenue")

   # Groupby aggregation
   df.glyphx.bar(groupby="region", y="revenue", agg="mean",
                 title="Avg Revenue by Region")

   # Full chain
   (df.glyphx
      .bar(x="quarter", y="revenue", label="Revenue", auto_display=False)
      .set_theme("dark")
      .set_xlabel("Quarter")
      .set_ylabel("Revenue ($B)")
      .add_stat_annotation("Q1 22", "Q1 23", p_value=0.004)
      .share("quarterly_report.html"))


Linked Brushing Dashboard
--------------------------

.. code-block:: python

   from glyphx import Figure
   from glyphx.layout import grid
   from glyphx.series import ScatterSeries, LineSeries

   x = list(range(1, 21))
   y1 = [v + 2 for v in x]
   y2 = [v ** 1.2 for v in x]

   f1 = Figure(legend=False)
   f1.set_title("Chart A — Shift+drag to brush")
   f1.add(ScatterSeries(x, y1, color="#2563eb", label="A", size=8))

   f2 = Figure(legend=False)
   f2.set_title("Chart B — linked selection")
   f2.add(ScatterSeries(x, y2, color="#dc2626", label="B", size=8))

   # Both charts share brushing — selecting points in one filters both
   html = grid([f1, f2], rows=1, cols=2)
   open("linked_dashboard.html", "w").write(html)


All Themes
----------

.. code-block:: python

   from glyphx import Figure
   from glyphx.series import LineSeries

   months  = ["Jan","Feb","Mar","Apr","May","Jun"]
   revenue = [120, 135, 98, 170, 145, 190]

   for theme_name in ["default","dark","colorblind","warm","ocean","pastel","monochrome"]:
       fig = (
           Figure(theme=theme_name)
           .set_title(f"Theme: {theme_name.title()}")
           .add(LineSeries(months, revenue, label="Revenue"))
       )
       fig.save(f"theme_{theme_name}.html")
