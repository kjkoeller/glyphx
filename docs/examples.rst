Examples
========

Line Chart
----------

.. code-block:: python

    plot([1, 2, 3], [4, 5, 6], kind="line")

Histogram
---------

.. code-block:: python

    from numpy import random
    data = random.normal(size=1000)
    plot(data=data, kind="hist", bins=20)

Facet Grid
----------

.. code-block:: python

    from glyphx import facet_plot
    facet_plot(df, x="value", col="species", kind="box")

JointPlot
---------

.. code-block:: python

    from glyphx import jointplot
    jointplot(df, x="A", y="B")

Custom Theme
------------

.. code-block:: python

    from glyphx import plot, themes
    plot([1,2,3], [4,5,6], theme=themes["dark"], kind="bar")