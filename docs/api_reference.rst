API Reference
=============

glyphx.plot
-----------

.. autofunction:: glyphx.plot


glyphx.plot3d
-------------

.. autofunction:: glyphx.plot3d


glyphx.from_prompt
------------------

.. autofunction:: glyphx.nlp.from_prompt


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
