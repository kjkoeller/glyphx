API Reference
=============

glyphx.plot
-----------

.. autofunction:: glyphx.plot


glyphx.plot3d
-------------

.. autofunction:: glyphx.plot3d


Figure
------

.. autoclass:: glyphx.Figure
   :members:
   :member-order: bysource


Figure3D
--------

.. autoclass:: glyphx.Figure3D
   :members:
   :member-order: bysource


Axes
----

.. autoclass:: glyphx.layout.Axes
   :members:


layout.grid
-----------

.. autofunction:: glyphx.layout.grid


SubplotGrid
-----------

.. autoclass:: glyphx.figure.SubplotGrid
   :members:


Core Series
-----------

.. autoclass:: glyphx.series.BaseSeries
   :members:

.. autoclass:: glyphx.series.LineSeries
   :members:

.. autoclass:: glyphx.series.BarSeries
   :members:

.. autoclass:: glyphx.series.ScatterSeries
   :members:

.. autoclass:: glyphx.series.HistogramSeries
   :members:

.. autoclass:: glyphx.series.BoxPlotSeries
   :members:

.. autoclass:: glyphx.series.HeatmapSeries
   :members:

.. autoclass:: glyphx.series.PieSeries
   :members:

.. autoclass:: glyphx.series.DonutSeries
   :members:


Statistical Series
------------------

.. autoclass:: glyphx.ecdf.ECDFSeries
   :members:

.. autoclass:: glyphx.raincloud.RaincloudSeries
   :members:

.. autoclass:: glyphx.violin_plot.ViolinPlotSeries
   :members:

.. autoclass:: glyphx.kde.KDESeries
   :members:

.. autoclass:: glyphx.fill_between.FillBetweenSeries
   :members:

.. autoclass:: glyphx.stat_annotation.StatAnnotation
   :members:

.. autofunction:: glyphx.stat_annotation.pvalue_to_label


Financial Series
----------------

.. autoclass:: glyphx.candlestick.CandlestickSeries
   :members:

.. autoclass:: glyphx.waterfall.WaterfallSeries
   :members:


Hierarchical Series
-------------------

.. autoclass:: glyphx.treemap.TreemapSeries
   :members:

.. autoclass:: glyphx.sunburst.SunburstSeries
   :members:


Streaming
---------

.. autoclass:: glyphx.streaming.StreamingSeries
   :members:


Advanced 2-D Series
-------------------

.. autoclass:: glyphx.bubble.BubbleSeries
   :members:

.. autoclass:: glyphx.parallel_coords.ParallelCoordinatesSeries
   :members:

.. autoclass:: glyphx.diverging_bar.DivergingBarSeries
   :members:

.. autoclass:: glyphx.grouped_bar.GroupedBarSeries
   :members:

.. autoclass:: glyphx.swarm_plot.SwarmPlotSeries
   :members:

.. autoclass:: glyphx.count_plot.CountPlotSeries
   :members:


3-D Series
----------

.. autoclass:: glyphx.scatter3d.Scatter3DSeries
   :members:

.. autoclass:: glyphx.surface3d.Surface3DSeries
   :members:

.. autoclass:: glyphx.line3d.Line3DSeries
   :members:

.. autoclass:: glyphx.bar3d.Bar3DSeries
   :members:

.. autoclass:: glyphx.contour.ContourSeries
   :members:


Downsampling
------------

.. automodule:: glyphx.downsample
   :members: lttb, m4, maybe_downsample_line, voxel_thin_2d, voxel_thin_3d,
             lttb_3d, decimate_grid, cull_faces,
             enable, disable, is_enabled,
             AUTO_THRESHOLD, M4_THRESHOLD, MIN_FACE_AREA

.. note::
   ``maybe_downsample()`` is deprecated; use ``maybe_downsample_line()`` instead.


DataFrame Accessor
------------------

.. autoclass:: glyphx.accessor.GlyphXAccessor
   :members:


Colormaps
---------

.. autofunction:: glyphx.colormaps.apply_colormap

.. autofunction:: glyphx.colormaps.colormap_colors

.. autofunction:: glyphx.colormaps.list_colormaps

.. autofunction:: glyphx.colormaps.get_colormap

.. autofunction:: glyphx.colormaps.render_colorbar_svg


Accessibility
-------------

.. autofunction:: glyphx.a11y.generate_alt_text

.. autofunction:: glyphx.a11y.inject_aria


Themes
------

.. autodata:: glyphx.themes.themes

.. autofunction:: glyphx.themes.register_theme

.. autofunction:: glyphx.themes.unregister_theme

.. autofunction:: glyphx.themes.get_theme

.. autofunction:: glyphx.themes.list_themes

Tick label wrapping
-------------------

.. autofunction:: glyphx.utils.wrap_tick_label

Available theme names: ``"default"``, ``"dark"``, ``"colorblind"``,
``"pastel"``, ``"warm"``, ``"ocean"``, ``"monochrome"``


Utilities
---------

.. autofunction:: glyphx.utils.normalize

.. autofunction:: glyphx.utils.svg_escape

.. autofunction:: glyphx.utils.wrap_svg_canvas

.. autofunction:: glyphx.utils.make_shareable_html

.. autofunction:: glyphx.utils.write_svg_file


Projection (3-D)
----------------

.. autoclass:: glyphx.projection3d.Camera3D
   :members:

.. autofunction:: glyphx.projection3d.normalize


Additional Chart Types (v1.6+)
-------------------------------

.. autoclass:: glyphx.gantt.GanttSeries
   :members:

.. autoclass:: glyphx.stacked_bar.StackedBarSeries
   :members:

.. autoclass:: glyphx.bump_chart.BumpChartSeries
   :members:

.. autoclass:: glyphx.sparkline.SparklineSeries
   :members:

.. autofunction:: glyphx.sparkline.sparkline_svg


FacetGrid
---------

.. autoclass:: glyphx.facet_grid.FacetGrid
   :members:
   :member-order: bysource


Regression Plot
---------------

.. autofunction:: glyphx.regplot.regplot


Choropleth Map
--------------

.. autoclass:: glyphx.choropleth.ChoroplethSeries
   :members:


Clustermap
----------

.. autofunction:: glyphx.clustermap.clustermap


Vega-Lite Export
----------------

.. autofunction:: glyphx.vega_lite.to_vega_lite

.. autofunction:: glyphx.vega_lite.save_vega_lite


Aggregation
-----------

Collapsing repeated measurements per x into an estimate and an interval,
which is what :meth:`glyphx.Figure.aggregate_line` draws.

.. autofunction:: glyphx.aggregate.aggregate


Math in labels
--------------

.. autofunction:: glyphx.mathtext.render

.. autofunction:: glyphx.mathtext.to_plain_text

.. autofunction:: glyphx.mathtext.contains_math

.. autofunction:: glyphx.mathtext.estimate_width


Export backends
---------------

.. autofunction:: glyphx.export.render_to_file

.. autofunction:: glyphx.export.available_backends


PDF writer
----------

The pure-Python PDF backend. It needs nothing beyond the standard library,
which is why ``.pdf`` works in a bare virtualenv or CI container with no
system libraries and no browser.

.. autofunction:: glyphx.pdf_writer.svg_to_pdf

.. autoclass:: glyphx.pdf_writer.UnsupportedSVGError


pandas backend
--------------

Registered under the ``pandas_plotting_backends`` entry point, so
``pd.options.plotting.backend = "glyphx"`` resolves here. Not called
directly -- see :meth:`glyphx.Figure.line` and the accessor below for
GlyphX's own APIs.

.. autofunction:: glyphx.pandas_backend.plot
