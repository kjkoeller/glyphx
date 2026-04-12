Large-Data Downsampling
=======================

GlyphX automatically downsamples large datasets before SVG generation to keep
file size small, browser rendering fast, and tooltip hit-testing reliable.
SVG performance degrades visibly above roughly 5 000 points; GlyphX handles
datasets with millions of points transparently.

All downsampling is implemented in :mod:`glyphx.downsample` and is fully
vectorised with NumPy.  Every algorithm can be called manually as well as
used automatically through the series classes.

.. contents::
   :local:
   :depth: 2


Algorithms
----------

GlyphX uses different algorithms depending on the series type, because each
has different structural assumptions about the data.

2-D Line — M4 + LTTB two-stage pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For ordered, axis-aligned line data GlyphX runs two stages automatically:

**Stage 1 — M4** fires when the point count exceeds ``M4_THRESHOLD``
(default 50 000).  For each pixel-wide column of the canvas it retains
four points: first, last, minimum-Y, and maximum-Y.  At the actual render
resolution this is visually lossless.  M4 requires monotone (sorted) X values
and is fully vectorised via ``np.digitize`` and ``np.minimum.reduceat``.

**Stage 2 — LTTB** (Largest-Triangle-Three-Buckets, Steinarsson 2013) fires
when the result still exceeds ``AUTO_THRESHOLD`` (default 5 000).  It selects
the point in each bucket whose triangle area with its neighbours is largest,
preserving peaks, troughs, and inflection points far better than simple
decimation.  The inner bucket scan is vectorised using NumPy slice expressions
and ``np.argmax``.

2-D Scatter — Voxel grid thinning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scatter data has no ordering assumption, so LTTB and M4 do not apply.
GlyphX divides the bounding box into a ``ceil(sqrt(max_points))²`` grid and
keeps the point nearest to each occupied cell centroid.  This preserves the
spatial distribution of the cloud.  The nearest-centroid selection uses
``np.minimum.reduceat`` after a single sort by cell ID — no full distance
argsort.

3-D Line — LTTB in screen space
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For a 3-D polyline, GlyphX first projects all points through the camera using
a vectorised NumPy matrix transform, then runs LTTB on the resulting 2-D
screen coordinates.  This means the camera angle determines which kinks are
visually significant — a bend that is invisible from the current viewpoint is
correctly discarded.  Results are cached per (camera-state, data-fingerprint)
pair in a ``WeakKeyDictionary`` so repeated renders at the same angle are free.

3-D Scatter — 3-D voxel grid thinning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Same principle as 2-D voxel thinning but in three dimensions.  The grid is
``ceil(cbrt(max_points))³``.  Per-point color lists are reindexed to match
the thinned output.

3-D Surface — Grid decimation + face culling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Surface3DSeries`` renders a regular M×N grid of quad faces.  GlyphX applies
two reductions:

1. **Grid decimation** — independent step sizes per axis (proportional to grid
   aspect ratio) reduce the grid so the quad count stays below
   ``AUTO_THRESHOLD``.  A 1 000×10 grid is decimated mostly along the long
   axis, not the short one.

2. **Face culling** — after decimation, quads whose projected screen area is
   below ``MIN_FACE_AREA`` (default 0.5 px²) are removed before the
   painter's-sort.  This is fully vectorised using the NumPy shoelace formula.


Thresholds and defaults
-----------------------

.. list-table::
   :widths: 30 15 55
   :header-rows: 1

   * - Constant
     - Default
     - Meaning
   * - ``AUTO_THRESHOLD``
     - 5 000
     - Point count above which LTTB and voxel thinning activate
   * - ``M4_THRESHOLD``
     - 50 000
     - Point count above which M4 fires as a first pass for line data
   * - ``MIN_FACE_AREA``
     - 0.5 px²
     - Minimum projected quad area below which surface faces are culled


Per-series threshold override
------------------------------

Every series constructor accepts a ``threshold`` keyword argument that overrides
``AUTO_THRESHOLD`` for that series only.  ``threshold=None`` (the default) uses
the module-level ``AUTO_THRESHOLD``.

.. code-block:: python

   from glyphx.series    import LineSeries, ScatterSeries
   from glyphx.line3d    import Line3DSeries
   from glyphx.scatter3d import Scatter3DSeries
   from glyphx.surface3d import Surface3DSeries

   # LineSeries: keep only 500 points instead of the default 5 000
   ls = LineSeries(x, y, threshold=500)

   # ScatterSeries: only thin when above 20 000 (looser than default)
   sc = ScatterSeries(x, y, threshold=20_000)

   # 3-D series
   l3 = Line3DSeries(x, y, z, threshold=1_000)
   s3 = Scatter3DSeries(x, y, z, threshold=2_000)
   sf = Surface3DSeries(x, y, Z, threshold=100)   # max faces


Inspecting downsampling after render
--------------------------------------

After ``to_svg()`` is called, each series exposes ``last_downsample_info`` — a
dict with keys ``algorithm``, ``original_n``, and ``thinned_n`` — or ``None``
if no downsampling occurred.

.. code-block:: python

   from glyphx.scatter3d import Scatter3DSeries
   from glyphx import Figure3D

   s3 = Scatter3DSeries(xs, ys, zs)
   fig = Figure3D()
   fig.add(s3)
   fig.render_svg()   # triggers to_svg internally

   info = s3.last_downsample_info
   if info:
       print(f"{info['algorithm']}: {info['original_n']} → {info['thinned_n']}")
   # e.g. "voxel-3D: 50000 → 4847"

The same property is available on ``LineSeries``, ``ScatterSeries``,
``Line3DSeries``, and ``Surface3DSeries``.

SVG comments are also embedded inline whenever downsampling occurs:

.. code-block:: xml

   <!-- glyphx: M4+LTTB downsampled 200000 -> 1631 points -->
   <!-- glyphx: voxel-2D downsampled 100000 -> 5041 points -->
   <!-- glyphx: grid-decimate (faces) downsampled 39601 -> 3481 points -->


Global kill-switch
------------------

Call ``disable()`` to turn off all downsampling on the current thread, for
example when generating publication-quality SVG exports where file size is not
a concern.  The kill-switch is stored in a ``threading.local`` so disabling on
one thread does not affect others.

.. code-block:: python

   import glyphx.downsample as ds

   ds.disable()
   # ... render high-fidelity charts ...
   ds.enable()

   # Check status
   print(ds.is_enabled())   # True / False

   # Thread safety: disabling in a worker thread does not affect the main thread
   import threading
   def worker():
       ds.disable()
       # render without downsampling on this thread only
   t = threading.Thread(target=worker)
   t.start()
   t.join()
   print(ds.is_enabled())   # still True on the main thread


Manual use of the downsampling API
------------------------------------

All functions are importable and callable directly:

.. code-block:: python

   from glyphx.downsample import (
       lttb,
       m4,
       maybe_downsample_line,
       voxel_thin_2d,
       voxel_thin_3d,
       lttb_3d,
       decimate_grid,
       cull_faces,
   )
   from glyphx.projection3d import Camera3D
   import numpy as np

   # LTTB — ordered 2-D line
   x = np.linspace(0, 1, 100_000)
   y = np.sin(x * 100)
   x_down, y_down = lttb(x, y, threshold=2_000)

   # M4 — pixel-aligned first pass
   x_m4, y_m4 = m4(x, y, pixel_width=800)

   # Two-stage pipeline (what LineSeries uses internally)
   x_pipe, y_pipe = maybe_downsample_line(x, y, pixel_width=800,
                                          threshold=5_000, m4_threshold=50_000)

   # Voxel thinning — 2-D scatter (unordered)
   xs = np.random.uniform(0, 1, 500_000)
   ys = np.random.uniform(0, 1, 500_000)
   c  = np.arange(500_000, dtype=np.int32)   # per-point class labels
   x_thin, y_thin, c_thin = voxel_thin_2d(xs, ys, c=c, max_points=5_000)
   # c_thin dtype is preserved as int32

   # Voxel thinning — 3-D scatter
   zs    = np.random.uniform(0, 1, 500_000)
   cols  = [f"#{i % 0xFFFFFF:06x}" for i in range(500_000)]
   x3, y3, z3, c3 = voxel_thin_3d(xs, ys, zs, colors=cols, max_points=5_000)

   # LTTB in 3-D screen space
   cam = Camera3D(azimuth=45, elevation=30, cx=320, cy=240, scale=200)
   t = np.linspace(0, 4 * np.pi, 100_000)
   lx, ly, lz = np.cos(t), np.sin(t), t / (4 * np.pi)
   lx_d, ly_d, lz_d = lttb_3d(lx, ly, lz, cam, threshold=2_000)

   # Grid decimation — 3-D surface
   x1 = np.linspace(-3, 3, 500)
   y1 = np.linspace(-3, 3, 500)
   Z  = np.sin(np.sqrt(x1[None,:]**2 + y1[:,None]**2))
   x_dec, y_dec, Z_dec = decimate_grid(x1, y1, Z, max_faces=5_000)

   # Face culling (called automatically by Surface3DSeries)
   faces_kept = cull_faces(faces, min_area=0.5)


Benchmark reference
--------------------

The table below shows approximate wall-clock times on a typical laptop
(measured with ``timeit``, 5 runs each).  All hot paths are fully vectorised.

.. list-table::
   :widths: 35 15 15 35
   :header-rows: 1

   * - Algorithm
     - Input
     - Output
     - Approx. time
   * - LTTB
     - 500 000 pts
     - 5 000 pts
     - ~35 ms
   * - M4
     - 1 000 000 pts
     - ~3 200 pts
     - ~75 ms
   * - M4 + LTTB pipeline
     - 500 000 pts
     - 5 000 pts
     - ~33 ms
   * - Voxel thin 2-D
     - 1 000 000 pts
     - ~5 000 pts
     - ~250 ms
   * - Voxel thin 3-D
     - 200 000 pts
     - ~5 000 pts
     - ~62 ms
   * - LTTB-3D
     - 100 000 pts
     - 5 000 pts
     - ~29 ms
   * - cull_faces (vectorised)
     - 50 000 faces
     - varies
     - ~53 ms
   * - decimate_grid
     - 500×500 grid
     - ~70×70 grid
     - < 1 ms


Running the test suite
-----------------------

The downsampling module ships with a self-contained test suite that covers both
correctness and performance.  It requires only the stdlib and NumPy:

.. code-block:: bash

   # Full suite — correctness tests + speed benchmarks
   python glyphx/test_downsample.py

   # Correctness tests only (faster)
   python glyphx/test_downsample.py --fast

The suite covers 47 cases across 8 test classes:

- Output length, first/last preservation, peak retention, monotonicity
- Empty inputs, length mismatch errors, dtype preservation
- Spatial coverage (voxel thinning)
- Cache hit/miss (LTTB-3D)
- Thread safety (kill-switch isolation)
- Deprecation warning (legacy wrapper)
- Performance ceiling (50 000 faces culled in under 500 ms)
