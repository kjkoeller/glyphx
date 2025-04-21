Getting Started
===============

Installation
------------

Install GlyphX via pip:

.. code-block:: bash

    pip install glyphx

You can also install from source:

.. code-block:: bash

    git clone https://github.com/kjkoeller/glyphx.git
    cd glyphx
    pip install .

First Plot
----------

Here's how to create your first chart with GlyphX:

.. code-block:: python

    from glyphx import plot

    y = [3, 5, 2, 8, 7]
    plot(y, kind="line", title="Simple Line Chart")

This will automatically render in your Jupyter notebook, IDE, or open in a browser if run from CLI.

Available Plot Kinds
--------------------

- `line`
- `bar`
- `scatter`
- `hist`
- `pie`
- `donut`
- `heatmap`
- `box`