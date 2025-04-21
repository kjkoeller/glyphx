
Usage
=====

Quick Example:

.. code-block:: python

   from glyphx import plot

   y = [2, 4, 6, 8, 10]
   plot(y, kind='line', title="Simple Line Chart")

More Examples:

* Bar chart: `plot(x=categories, y=values, kind='bar')`
* Pie chart: `plot(data=values, kind='pie')`
* Heatmap: `plot(data=matrix, kind='heatmap')`
