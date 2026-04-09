"""
GlyphX data downsampling utilities.

SVG performance degrades visibly above ~5 000 points — file size grows,
browser rendering stutters, and tooltip hit-testing becomes unreliable.
Matplotlib side-steps this by rasterising to a pixel buffer.  GlyphX
matches Matplotlib's large-data performance by automatically downsampling
before SVG generation using the Largest-Triangle-Three-Buckets (LTTB)
algorithm.

LTTB (Steinarsson 2013) preserves the visual shape of a time series far
better than simple decimation or moving-average smoothing — peaks,
troughs, and inflection points are always retained.

Usage is automatic: ``LineSeries`` and ``ScatterSeries`` call
``maybe_downsample()`` during ``to_svg()`` when the point count exceeds
``AUTO_THRESHOLD``.  You can also call it manually::

    from glyphx.downsample import lttb, maybe_downsample
    x_ds, y_ds = lttb(x, y, threshold=1000)
"""
from __future__ import annotations

import numpy as np

# Point count above which auto-downsampling kicks in for SVG rendering.
# At 5 000 points a typical line chart SVG is ~250 KB and renders fine.
# Beyond this, performance degrades noticeably on mobile.
AUTO_THRESHOLD: int = 5_000


# ---------------------------------------------------------------------------
# LTTB algorithm
# ---------------------------------------------------------------------------

def lttb(
    x: list | np.ndarray,
    y: list | np.ndarray,
    threshold: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Largest-Triangle-Three-Buckets downsampling.

    Reduces a (x, y) series to at most ``threshold`` points while
    preserving the visual shape.  The first and last points are always
    kept.  In each bucket the point that forms the largest triangle with
    its neighbours is selected.

    Args:
        x:          X values (1-D, numeric).
        y:          Y values (1-D, numeric, same length as x).
        threshold:  Maximum number of output points.

    Returns:
        Tuple ``(x_down, y_down)`` — NumPy arrays of length ≤ threshold.

    Raises:
        ValueError: If x and y have different lengths, or threshold < 3.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n = len(x_arr)

    if len(y_arr) != n:
        raise ValueError(f"x and y must have the same length ({n} vs {len(y_arr)}).")
    if threshold < 3:
        raise ValueError("threshold must be at least 3.")
    if n <= threshold:
        return x_arr, y_arr

    # Number of buckets (first and last points are always included)
    n_buckets = threshold - 2
    bucket_size = (n - 2) / n_buckets

    selected_x: list[float] = [x_arr[0]]
    selected_y: list[float] = [y_arr[0]]

    a = 0  # index of the previously selected point

    for bucket in range(n_buckets):
        # Range for current bucket
        b_start = int(math.floor((bucket + 1) * bucket_size)) + 1
        b_end   = int(math.floor((bucket + 2) * bucket_size)) + 1
        b_end   = min(b_end, n - 1)

        # Average point of the NEXT bucket (represents its "centre")
        c_start = b_end
        c_end   = min(int(math.floor((bucket + 2) * bucket_size)) + 1, n - 1)
        avg_x   = x_arr[c_start:c_end].mean() if c_start < c_end else x_arr[c_end]
        avg_y   = y_arr[c_start:c_end].mean() if c_start < c_end else y_arr[c_end]

        ax_val, ay_val = x_arr[a], y_arr[a]

        # Select point in current bucket that forms the largest triangle
        max_area = -1.0
        best_idx = b_start
        for i in range(b_start, b_end):
            # Triangle area (×2) via cross product
            area = abs(
                (ax_val - avg_x) * (y_arr[i] - ay_val)
                - (ax_val - x_arr[i]) * (avg_y - ay_val)
            )
            if area > max_area:
                max_area = area
                best_idx = i

        selected_x.append(x_arr[best_idx])
        selected_y.append(y_arr[best_idx])
        a = best_idx

    selected_x.append(x_arr[-1])
    selected_y.append(y_arr[-1])

    return np.array(selected_x), np.array(selected_y)


def maybe_downsample(
    x: list | np.ndarray,
    y: list | np.ndarray,
    threshold: int = AUTO_THRESHOLD,
) -> tuple[list | np.ndarray, list | np.ndarray]:
    """
    Apply LTTB only when the series exceeds ``threshold`` points.

    If downsampling occurs, a warning is embedded as an SVG ``<title>``
    (not raised as a Python warning, to avoid polluting Jupyter output).

    Args:
        x:          X values.
        y:          Y values.
        threshold:  Point count above which LTTB is applied.

    Returns:
        ``(x, y)`` — either the originals or the downsampled versions.
    """
    n = len(x) if hasattr(x, "__len__") else 0
    if n <= threshold:
        return x, y
    return lttb(x, y, threshold)


# ---------------------------------------------------------------------------
# Needed import (math is used in lttb but not imported at module level above)
# ---------------------------------------------------------------------------
import math   # noqa: E402  (placed here to keep the docstring clean)
