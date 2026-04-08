Customization
=============

Themes
------

GlyphX ships seven built-in themes. Pass the name as a string:

.. code-block:: python

   from glyphx import Figure

   Figure(theme="dark")
   Figure(theme="colorblind")   # Okabe-Ito palette — safe for all types
   Figure(theme="warm")
   Figure(theme="ocean")
   Figure(theme="pastel")
   Figure(theme="monochrome")
   Figure(theme="default")      # clean white (default)

.. image:: examples/dark_theme.svg
   :alt: Dark theme dual-series line chart
   :width: 760px
   :align: center

.. image:: examples/colorblind_theme.svg
   :alt: Colorblind-safe Okabe-Ito theme
   :width: 760px
   :align: center

.. list-table:: Built-in Themes
   :widths: 20 40 40
   :header-rows: 1

   * - Name
     - Background
     - Color Palette
   * - ``default``
     - White
     - Tableau-style
   * - ``dark``
     - Charcoal (#1e1e1e)
     - Muted blues and ambers
   * - ``colorblind``
     - White
     - **Okabe-Ito** — safe for deuteranopia, protanopia, tritanopia
   * - ``pastel``
     - Off-white (#f9f9f9)
     - Soft muted tones
   * - ``warm``
     - Cream (#fff8f0)
     - Earthy reds and greens, Georgia serif font
   * - ``ocean``
     - Light blue (#f0f8ff)
     - Deep blues and teals
   * - ``monochrome``
     - White
     - Greys only — print-safe

.. note::
   The ``colorblind`` theme uses the `Okabe-Ito palette
   <https://jfly.uni-koeln.de/color/>`_, the scientific standard for
   colorblind-accessible data visualization. Earlier versions used grayscale
   incorrectly — this was fixed in v1.5.0.


Custom Themes
~~~~~~~~~~~~~

Pass a dict with any subset of theme keys:

.. code-block:: python

   my_theme = {
       "colors":      ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4"],
       "background":  "#1a1a2e",
       "text_color":  "#eeeeee",
       "axis_color":  "#555",
       "grid_color":  "#333",
       "font":        "Roboto, sans-serif",
   }

   Figure(theme=my_theme)


Colors and Line Styles
----------------------

Pass ``color`` and ``linestyle`` directly to any series:

.. code-block:: python

   from glyphx.series import LineSeries

   LineSeries(x, y, color="#16a34a", linestyle="solid",    width=2.5)
   LineSeries(x, y, color="#2563eb", linestyle="dashed",   width=2.5)
   LineSeries(x, y, color="#dc2626", linestyle="dotted",   width=2.5)
   LineSeries(x, y, color="#d97706", linestyle="longdash", width=2.5)

.. image:: examples/green_dashed_line.svg
   :alt: All four linestyles showcased
   :width: 760px
   :align: center

Available ``linestyle`` values: ``"solid"``, ``"dashed"``, ``"dotted"``, ``"longdash"``


Colormaps
---------

Nine perceptually-uniform colormaps are built in:

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Name
     - Type
     - Best for
   * - ``viridis``
     - Sequential
     - Default continuous encoding
   * - ``plasma``
     - Sequential
     - High-contrast continuous data
   * - ``inferno``
     - Sequential
     - Print-safe on dark backgrounds
   * - ``magma``
     - Sequential
     - Heatmaps and density plots
   * - ``cividis``
     - Sequential
     - Deuteranopia-safe alternative to viridis
   * - ``coolwarm``
     - Diverging
     - Correlation matrices, positive/negative
   * - ``rdbu``
     - Diverging
     - Two-sided data centered at zero
   * - ``spectral``
     - Multi-hue
     - Categorical ranges (use sparingly)
   * - ``greys``
     - Sequential
     - Monochrome / print output

.. code-block:: python

   from glyphx.colormaps import apply_colormap, colormap_colors, list_colormaps
   from glyphx.series import ScatterSeries

   # Single value → hex color
   color = apply_colormap(0.75, "plasma")

   # N evenly-spaced colors
   colors = colormap_colors("viridis", 6)

   # Color-encode scatter points by a third variable
   ScatterSeries(x, y, c=z_values, cmap="plasma", size=8)

.. image:: examples/colormaps.svg
   :alt: Scatter plot with plasma colormap encoding
   :width: 760px
   :align: center


Annotations
-----------

Add text callouts in data-space coordinates:

.. code-block:: python

   fig.annotate(
       "Record High",
       x=11, y=2.9,
       arrow=True,
       color="#dc2626",
       font_size=12,
   )


Statistical Significance Brackets
----------------------------------

.. code-block:: python

   fig = (
       Figure()
       .add(BarSeries(["Control","Drug A","Drug B"], means, yerr=errors))
       .add_stat_annotation("Control", "Drug A", p_value=0.0003)
       .add_stat_annotation("Control", "Drug B", p_value=0.031, y_offset=30)
   )

.. image:: examples/stat_annotations.svg
   :alt: Bar chart with statistical significance brackets
   :width: 640px
   :align: center


Grid Layouts
------------

**Subplot grid on a single Figure:**

.. code-block:: python

   fig = Figure(rows=2, cols=2, width=1000, height=700)
   fig.add_axes(0, 0).add_series(LineSeries([1,2,3], [4,5,6]))
   fig.add_axes(0, 1).add_series(BarSeries(["A","B","C"], [5,3,7]))
   fig.add_axes(1, 0).add_series(ScatterSeries([1,2,3], [4,5,6]))
   fig.add_axes(1, 1).add_series(HistogramSeries(data, bins=15))
   fig.show()

.. image:: examples/grid_layout.svg
   :alt: 2x2 subplot grid
   :width: 760px
   :align: center

**Multiple Figures on one HTML page:**

.. code-block:: python

   from glyphx.layout import grid

   html = grid([f1, f2, f3], rows=1, cols=3)
   open("dashboard.html", "w").write(html)


Tight Layout
~~~~~~~~~~~~

.. code-block:: python

   fig = (
       Figure()
       .add(BarSeries(long_category_names, values))
       .tight_layout()
   )
