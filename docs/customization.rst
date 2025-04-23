Customization
=============

Themes
------

You can set a global or per-chart theme:

.. code-block:: python

    from glyphx import plot, themes

    plot([1, 2, 3], [4, 5, 6], theme=themes["dark"])

.. image:: examples/dark_theme.png
   :alt: Basic Plot
   :width: 680px
   :align: center

Colors & Styles
---------------

Set custom colors, widths, and line styles:

.. code-block:: python

    from glyphx import plot

    plot([1, 2, 3], [4, 6, 8], color="green", linestyle="dashed")

.. image:: examples/green_dashed_line.png
   :alt: Basic Plot
   :width: 680px
   :align: center

Grid Layouts
------------

Use `Figure` and `add_axes()` to manually control multi-plot layouts:

.. code-block:: python

    from glyphx import Figure

    fig = Figure(rows=2, cols=2)
    ax = fig.add_axes(0, 0)
    ax.add(LineSeries([1, 2], [3, 4]))
    fig.plot()
