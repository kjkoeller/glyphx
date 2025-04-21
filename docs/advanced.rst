Advanced Features
=================

Facet Plots
-----------

Grid of plots split by categorical variables.

.. code-block:: python

    from glyphx import facet_plot
    fig = facet_plot(data, x="value", col="group", kind="hist")

Pair Plots
----------

Matrix of scatter/histogram plots for all numeric combinations.

.. code-block:: python

    from glyphx import pairplot
    pairplot(df)

Joint Plot
----------

A central scatter plot with marginal histograms.

.. code-block:: python

    from glyphx import jointplot
    jointplot(df, x="a", y="b")

LM Plot
-------

Regression line over scatter.

.. code-block:: python

    from glyphx import lmplot
    lmplot(df, x="x", y="y")

Hover + Export
--------------

Charts include built-in hover tooltips and export buttons for:
- SVG
- PNG
- JPG

Zoom & Pan
----------

Zoom and pan with mouse wheel and drag. Automatically included in HTML export.