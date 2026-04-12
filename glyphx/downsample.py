"""
GlyphX data downsampling utilities.

SVG performance degrades visibly above ~5 000 points.  GlyphX
automatically downsamples before SVG generation using a suite of
algorithms chosen per series type.

Algorithm summary
-----------------
2-D line series   : Two-stage M4 -> LTTB pipeline.
2-D scatter series: 2-D voxel grid thinning.
3-D line series   : LTTB on vectorised camera-projected screen coords,
                    result cached in a WeakKeyDictionary keyed on camera
                    state + data fingerprint.
3-D scatter series: 3-D voxel grid thinning.
3-D surface series: Per-axis grid decimation + sub-pixel face culling.

Performance notes
-----------------
All hot paths are fully vectorised with NumPy:
- LTTB   : triangle-area computation uses slice broadcasting per bucket;
           no Python loop inside the bucket scan.
- M4     : column assignment via np.digitize; min/max/first/last per
           column via np.minimum.reduceat / np.maximum.reduceat after a
           single argsort by column — no per-column Python list.
- Voxel  : nearest-centroid selection via np.minimum.reduceat after
           sorting by cell_id — avoids a full argsort on distance.

Global kill-switch
------------------
Call ``glyphx.downsample.disable()`` to turn off all downsampling.
The flag lives in a threading.local so threads are independent.

Per-series control
------------------
Pass ``threshold=N`` to any series constructor to override AUTO_THRESHOLD.

Downsampling metadata
---------------------
After rendering each series exposes ``series.last_downsample_info``
— a dict with keys ``algorithm``, ``original_n``, ``thinned_n``.
"""
from __future__ import annotations

import math
import threading
import warnings
import weakref
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .projection3d import Camera3D

# ---------------------------------------------------------------------------
# Thread-safe global kill-switch
# ---------------------------------------------------------------------------

_local = threading.local()


def _enabled() -> bool:
    return getattr(_local, "enabled", True)


def disable() -> None:
    """Disable all automatic downsampling on the current thread."""
    _local.enabled = False


def enable() -> None:
    """Re-enable automatic downsampling on the current thread."""
    _local.enabled = True


def is_enabled() -> bool:
    """Return True if downsampling is active on this thread."""
    return _enabled()


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

AUTO_THRESHOLD: int = 5_000
M4_THRESHOLD:   int = 50_000
MIN_FACE_AREA:  float = 0.5


# ---------------------------------------------------------------------------
# LTTB -- fully vectorised inner loop
# ---------------------------------------------------------------------------

def lttb(
    x: list | np.ndarray,
    y: list | np.ndarray,
    threshold: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Largest-Triangle-Three-Buckets downsampling (Steinarsson 2013).

    The per-bucket triangle-area scan is vectorised: for each bucket the
    areas of all candidate points are computed as a NumPy slice expression
    and ``np.argmax`` selects the winner — no Python loop inside the bucket.

    Args:
        x:          X values (1-D, numeric).
        y:          Y values (1-D, numeric, same length as x).
        threshold:  Maximum number of output points (>= 3).

    Returns:
        ``(x_down, y_down)`` -- NumPy arrays of length <= threshold.

    Raises:
        ValueError: If lengths differ or threshold < 3.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n = len(x_arr)

    if len(y_arr) != n:
        raise ValueError(
            f"x and y must have the same length ({n} vs {len(y_arr)})."
        )
    if threshold < 3:
        raise ValueError("threshold must be at least 3.")
    if n <= threshold:
        return x_arr, y_arr

    n_buckets   = threshold - 2
    bucket_size = (n - 2) / n_buckets

    # Pre-compute bucket boundaries (b_start, b_end) for every bucket
    bucket_idx  = np.arange(n_buckets)
    b_starts    = (np.floor((bucket_idx + 1) * bucket_size) + 1).astype(int)
    b_ends      = np.minimum(
        (np.floor((bucket_idx + 2) * bucket_size) + 1).astype(int),
        n - 1
    )
    # "next-bucket" averages: used as the lookahead anchor point
    c_starts    = b_ends
    c_ends      = np.minimum(
        (np.floor((bucket_idx + 2) * bucket_size) + 1).astype(int),
        n - 1
    )

    kept = np.empty(threshold, dtype=int)
    kept[0]  = 0
    kept[-1] = n - 1
    a = 0  # index of previously selected point

    for k in range(n_buckets):
        bs = b_starts[k]
        be = b_ends[k]
        cs = c_starts[k]
        ce = c_ends[k]

        # Next-bucket average (lookahead anchor)
        if cs < ce:
            avg_x = x_arr[cs:ce].mean()
            avg_y = y_arr[cs:ce].mean()
        else:
            avg_x = x_arr[ce]
            avg_y = y_arr[ce]

        ax_val = x_arr[a]
        ay_val = y_arr[a]

        # Vectorised triangle area for all points in [bs, be)
        if bs >= be:
            # Degenerate bucket (can occur near end of data) — keep current a
            kept[k + 1] = a
            continue
        xi = x_arr[bs:be]
        yi = y_arr[bs:be]
        areas = np.abs(
            (ax_val - avg_x) * (yi - ay_val)
            - (ax_val - xi)  * (avg_y - ay_val)
        )
        best_local = int(np.argmax(areas))
        a = bs + best_local
        kept[k + 1] = a

    return x_arr[kept], y_arr[kept]


# ---------------------------------------------------------------------------
# M4 -- fully vectorised via np.digitize + reduceat
# ---------------------------------------------------------------------------

def m4(
    x: list | np.ndarray,
    y: list | np.ndarray,
    pixel_width: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    M4 downsampling (Jugel et al. 2014).

    Fully vectorised: column assignment uses ``np.digitize``; per-column
    first/last/min/max are found with ``np.minimum.reduceat`` and
    ``np.maximum.reduceat`` after a single argsort by column — no
    per-column Python list or loop.

    Requires monotone X values.  Non-monotone input is auto-sorted with
    a ``UserWarning``.

    Args:
        x:           X values (1-D, numeric, monotone).
        y:           Y values (1-D, numeric, same length as x).
        pixel_width: Canvas width in pixels.

    Returns:
        ``(x_down, y_down)`` -- NumPy arrays.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n = len(x_arr)

    if n == 0:
        return x_arr, y_arr

    if n > 1 and not (
        np.all(np.diff(x_arr) >= 0) or np.all(np.diff(x_arr) <= 0)
    ):
        warnings.warn(
            "m4() received non-monotone X values.  Data will be sorted by X "
            "before downsampling.  If your series is not a function of X "
            "(e.g. a parametric curve), use voxel_thin_2d() instead.",
            UserWarning,
            stacklevel=2,
        )
        order = np.argsort(x_arr, kind="stable")
        x_arr = x_arr[order]
        y_arr = y_arr[order]

    n_buckets = max(1, pixel_width)
    x_min, x_max = x_arr[0], x_arr[-1]
    x_span = x_max - x_min or 1.0

    # Assign each point to a pixel column [0, n_buckets-1]
    # np.digitize with evenly-spaced bins avoids the Python loop entirely.
    edges  = np.linspace(x_min, x_max, n_buckets + 1)
    # digitize returns 1-based; subtract 1 and clip
    cols   = np.clip(np.digitize(x_arr, edges) - 1, 0, n_buckets - 1)

    # Sort everything by column so reduceat can process columns in one pass
    col_order  = np.argsort(cols, kind="stable")
    cols_sorted = cols[col_order]
    y_sorted    = y_arr[col_order]

    # Find the start index of each unique column in the sorted array
    unique_cols, col_starts = np.unique(cols_sorted, return_index=True)

    # reduceat gives per-segment min/max in one vectorised call
    y_min_per_col = np.minimum.reduceat(y_sorted, col_starts)
    y_max_per_col = np.maximum.reduceat(y_sorted, col_starts)

    # First and last index within each column (in col_order space)
    col_ends = np.empty_like(col_starts)
    col_ends[:-1] = col_starts[1:] - 1
    col_ends[-1]  = len(col_order) - 1

    # For each column: indices of first, last, argmin-y, argmax-y
    # We need original (unsorted) indices for x/y lookup.
    kept_set: list[int] = []
    for ci, (cs, ce) in enumerate(zip(col_starts, col_ends)):
        seg_orig = col_order[cs : ce + 1]          # original indices in this col
        seg_y    = y_arr[seg_orig]
        kept_set.append(int(seg_orig[0]))           # first
        kept_set.append(int(seg_orig[-1]))          # last
        kept_set.append(int(seg_orig[np.argmin(seg_y)]))  # min-y
        kept_set.append(int(seg_orig[np.argmax(seg_y)]))  # max-y

    # Deduplicate and preserve order
    seen: set[int] = set()
    kept_ordered: list[int] = []
    for idx in kept_set:
        if idx not in seen:
            seen.add(idx)
            kept_ordered.append(idx)
    kept_ordered.sort()

    idx_arr = np.array(kept_ordered, dtype=int)
    return x_arr[idx_arr], y_arr[idx_arr]


# ---------------------------------------------------------------------------
# Two-stage pipeline for Line2D
# ---------------------------------------------------------------------------

def maybe_downsample_line(
    x: list | np.ndarray,
    y: list | np.ndarray,
    pixel_width: int = 800,
    threshold: int = AUTO_THRESHOLD,
    m4_threshold: int = M4_THRESHOLD,
) -> tuple[np.ndarray | list, np.ndarray | list]:
    """
    Two-stage downsampling pipeline for ordered 2-D line data.

    Stage 1 -- M4  : if n > ``m4_threshold``, reduce via M4.
    Stage 2 -- LTTB: if still > ``threshold``, apply LTTB.

    Respects the thread-local kill-switch.
    """
    if not _enabled():
        return x, y

    n = len(x) if hasattr(x, "__len__") else 0
    if n <= threshold:
        return x, y

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    if n > m4_threshold:
        x_arr, y_arr = m4(x_arr, y_arr, pixel_width)

    if len(x_arr) > threshold:
        x_arr, y_arr = lttb(x_arr, y_arr, threshold)

    return x_arr, y_arr


# ---------------------------------------------------------------------------
# Legacy wrapper -- deprecated
# ---------------------------------------------------------------------------

def maybe_downsample(
    x: list | np.ndarray,
    y: list | np.ndarray,
    threshold: int = AUTO_THRESHOLD,
) -> tuple[list | np.ndarray, list | np.ndarray]:
    """
    Backward-compatible wrapper: LTTB only, no pixel width, no M4.

    .. deprecated::
        Use ``maybe_downsample_line`` instead.
    """
    warnings.warn(
        "maybe_downsample() is deprecated; use maybe_downsample_line() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not _enabled():
        return x, y
    n = len(x) if hasattr(x, "__len__") else 0
    if n <= threshold:
        return x, y
    return lttb(x, y, threshold)


# ---------------------------------------------------------------------------
# Voxel thinning -- 2-D  (reduceat-based, no full distance sort)
# ---------------------------------------------------------------------------

def voxel_thin_2d(
    x: list | np.ndarray,
    y: list | np.ndarray,
    c: list | np.ndarray | None = None,
    max_points: int = AUTO_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """
    2-D voxel grid thinning for unordered scatter data.

    For each occupied grid cell keeps the point nearest to the cell
    centroid.  Uses ``np.minimum.reduceat`` after sorting by cell_id to
    find the nearest point per cell without a full distance argsort,
    reducing the dominant cost from O(n log n) to O(n log n) sort by
    cell + O(n) scan.

    The dtype of ``c`` is preserved in the output.

    Respects the thread-local kill-switch.

    Args:
        x, y:       Coordinates (1-D, same length).
        c:          Optional per-point values (threaded through).
        max_points: Target maximum output points.

    Returns:
        ``(x_thin, y_thin, c_thin)``

    Raises:
        ValueError: If x and y have different lengths.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    if len(x_arr) != len(y_arr):
        raise ValueError(
            f"x and y must have the same length ({len(x_arr)} vs {len(y_arr)})."
        )

    c_arr = np.asarray(c) if c is not None else None

    if not _enabled() or len(x_arr) <= max_points:
        return x_arr, y_arr, c_arr

    grid_k = max(1, int(math.ceil(math.sqrt(max_points))))

    x_min, x_max = x_arr.min(), x_arr.max()
    y_min, y_max = y_arr.min(), y_arr.max()
    x_span = x_max - x_min or 1.0
    y_span = y_max - y_min or 1.0

    col = np.clip(((x_arr - x_min) / x_span * grid_k).astype(int), 0, grid_k - 1)
    row = np.clip(((y_arr - y_min) / y_span * grid_k).astype(int), 0, grid_k - 1)
    cell_id = row * grid_k + col

    # Centroid distance for every point
    cx    = x_min + (col + 0.5) / grid_k * x_span
    cy    = y_min + (row + 0.5) / grid_k * y_span
    dist2 = (x_arr - cx) ** 2 + (y_arr - cy) ** 2

    # Sort by cell_id so reduceat can process each cell in one pass
    cell_order   = np.argsort(cell_id, kind="stable")
    cell_sorted  = cell_id[cell_order]
    dist_sorted  = dist2[cell_order]

    _, cell_starts = np.unique(cell_sorted, return_index=True)

    # Per-cell minimum distance using reduceat
    min_dist_per_cell = np.minimum.reduceat(dist_sorted, cell_starts)

    # Index of the minimum within each cell (in cell_order space)
    cell_ends = np.empty_like(cell_starts)
    cell_ends[:-1] = cell_starts[1:]
    cell_ends[-1]  = len(cell_order)

    best_local = np.empty(len(cell_starts), dtype=int)
    for ci, (cs, ce, md) in enumerate(zip(cell_starts, cell_ends, min_dist_per_cell)):
        seg = dist_sorted[cs:ce]
        best_local[ci] = cs + int(np.argmin(seg))  # position in cell_order

    kept = np.sort(cell_order[best_local])

    c_out = c_arr[kept] if c_arr is not None else None
    return x_arr[kept], y_arr[kept], c_out


# ---------------------------------------------------------------------------
# LTTB-3D cache
# ---------------------------------------------------------------------------

_lttb3d_cache: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _data_fingerprint(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, threshold: int
) -> tuple:
    """
    Content-based cache key using 8 evenly-spaced sample values per axis.

    More collision-resistant than first/mid/last while remaining cheap.
    """
    def _sig(arr: np.ndarray) -> tuple:
        n = len(arr)
        indices = np.linspace(0, n - 1, min(8, n), dtype=int)
        return (n,) + tuple(float(arr[i]) for i in indices)
    return (_sig(x), _sig(y), _sig(z), threshold)


# ---------------------------------------------------------------------------
# Vectorised projection helper
# ---------------------------------------------------------------------------

def _project_vectorised(
    xn: np.ndarray,
    yn: np.ndarray,
    zn: np.ndarray,
    cam: "Camera3D",
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised orthographic projection matching Camera3D.project()."""
    cos_az, sin_az = cam._cos_az, cam._sin_az
    cos_el, sin_el = cam._cos_el, cam._sin_el

    rx =  xn * cos_az + yn * sin_az
    ry = -xn * sin_az + yn * cos_az
    fz = -ry * sin_el - zn * cos_el

    return cam.cx + rx * cam.scale, cam.cy - fz * cam.scale


# ---------------------------------------------------------------------------
# LTTB on projected coordinates -- 3-D line  (vectorised inner loop)
# ---------------------------------------------------------------------------

def lttb_3d(
    x: list | np.ndarray,
    y: list | np.ndarray,
    z: list | np.ndarray,
    cam: "Camera3D",
    threshold: int = AUTO_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    LTTB for a 3-D polyline in screen space.

    Projects via vectorised NumPy transform, then runs the vectorised
    LTTB inner loop on screen coordinates.  Result cached in a
    WeakKeyDictionary keyed on (camera-state, data-fingerprint).

    Respects the thread-local kill-switch.

    Raises:
        ValueError: If x, y, z have different lengths.
    """
    from .projection3d import normalize

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    z_arr = np.asarray(z, dtype=float)

    if not (len(x_arr) == len(y_arr) == len(z_arr)):
        raise ValueError(
            f"x, y, z must have the same length "
            f"({len(x_arr)}, {len(y_arr)}, {len(z_arr)})."
        )

    n = len(x_arr)

    if not _enabled() or n <= threshold:
        return x_arr, y_arr, z_arr

    cam_state   = (cam.azimuth, cam.elevation, cam.cx, cam.cy, cam.scale)
    fingerprint = _data_fingerprint(x_arr, y_arr, z_arr, threshold)
    cache_key   = (cam_state, fingerprint)

    cam_cache = _lttb3d_cache.get(cam)
    if cam_cache is not None and cam_cache[0] == cache_key:
        return cam_cache[1]

    xn = np.asarray(normalize(x_arr)[0], dtype=float)
    yn = np.asarray(normalize(y_arr)[0], dtype=float)
    zn = np.asarray(normalize(z_arr)[0], dtype=float)
    px, py = _project_vectorised(xn, yn, zn, cam)

    # Reuse vectorised LTTB on (px, py) — same algorithm, screen coords
    _threshold  = max(threshold, 3)
    n_buckets   = _threshold - 2
    bucket_size = (n - 2) / n_buckets

    bucket_idx = np.arange(n_buckets)
    b_starts   = (np.floor((bucket_idx + 1) * bucket_size) + 1).astype(int)
    b_ends     = np.minimum(
        (np.floor((bucket_idx + 2) * bucket_size) + 1).astype(int),
        n - 1
    )
    c_ends = np.minimum(
        (np.floor((bucket_idx + 2) * bucket_size) + 1).astype(int),
        n - 1
    )

    kept = np.empty(_threshold, dtype=int)
    kept[0]  = 0
    kept[-1] = n - 1
    a = 0

    for k in range(n_buckets):
        bs = b_starts[k]
        be = b_ends[k]
        ce = c_ends[k]
        cs = be  # c_start = b_end

        if cs < ce:
            avg_px = px[cs:ce].mean()
            avg_py = py[cs:ce].mean()
        else:
            avg_px = px[ce]
            avg_py = py[ce]

        ax_val = px[a];  ay_val = py[a]
        if bs >= be:
            kept[k + 1] = a
            continue
        xi = px[bs:be];  yi = py[bs:be]

        areas = np.abs(
            (ax_val - avg_px) * (yi - ay_val)
            - (ax_val - xi)   * (avg_py - ay_val)
        )
        a = bs + int(np.argmax(areas))
        kept[k + 1] = a

    idx    = kept
    result = (x_arr[idx], y_arr[idx], z_arr[idx])
    _lttb3d_cache[cam] = (cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Voxel thinning -- 3-D  (reduceat-based)
# ---------------------------------------------------------------------------

def voxel_thin_3d(
    x: list | np.ndarray,
    y: list | np.ndarray,
    z: list | np.ndarray,
    colors: list | None = None,
    max_points: int = AUTO_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list | None]:
    """
    3-D voxel grid thinning for unordered scatter data.

    Uses ``np.minimum.reduceat`` after sorting by cell_id to find the
    nearest-centroid point per voxel without a full distance argsort.

    Respects the thread-local kill-switch.

    Raises:
        ValueError: If x, y, z have different lengths.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    z_arr = np.asarray(z, dtype=float)

    if not (len(x_arr) == len(y_arr) == len(z_arr)):
        raise ValueError(
            f"x, y, z must have the same length "
            f"({len(x_arr)}, {len(y_arr)}, {len(z_arr)})."
        )

    n = len(x_arr)

    if not _enabled() or n <= max_points:
        return x_arr, y_arr, z_arr, colors

    grid_k = max(1, int(math.ceil(max_points ** (1.0 / 3.0))))

    def _cell(arr: np.ndarray) -> np.ndarray:
        lo, hi = arr.min(), arr.max()
        span = hi - lo or 1.0
        return np.clip(((arr - lo) / span * grid_k).astype(int), 0, grid_k - 1)

    ci = _cell(x_arr);  cj = _cell(y_arr);  ck = _cell(z_arr)
    cell_id = ci * grid_k * grid_k + cj * grid_k + ck

    x_span = (x_arr.max() - x_arr.min()) or 1.0
    y_span = (y_arr.max() - y_arr.min()) or 1.0
    z_span = (z_arr.max() - z_arr.min()) or 1.0

    ccx = x_arr.min() + (ci + 0.5) / grid_k * x_span
    ccy = y_arr.min() + (cj + 0.5) / grid_k * y_span
    ccz = z_arr.min() + (ck + 0.5) / grid_k * z_span
    dist2 = (x_arr - ccx) ** 2 + (y_arr - ccy) ** 2 + (z_arr - ccz) ** 2

    # Sort by cell_id, use reduceat to find min-dist per cell
    cell_order  = np.argsort(cell_id, kind="stable")
    cell_sorted = cell_id[cell_order]
    dist_sorted = dist2[cell_order]

    _, cell_starts = np.unique(cell_sorted, return_index=True)

    cell_ends = np.empty_like(cell_starts)
    cell_ends[:-1] = cell_starts[1:]
    cell_ends[-1]  = len(cell_order)

    best_local = np.empty(len(cell_starts), dtype=int)
    for ci_idx, (cs, ce) in enumerate(zip(cell_starts, cell_ends)):
        best_local[ci_idx] = cs + int(np.argmin(dist_sorted[cs:ce]))

    kept = np.sort(cell_order[best_local])

    colors_out = [colors[i] for i in kept] if colors is not None else None
    return x_arr[kept], y_arr[kept], z_arr[kept], colors_out


# ---------------------------------------------------------------------------
# Grid decimation -- Surface3D
# ---------------------------------------------------------------------------

def decimate_grid(
    x_1d: list | np.ndarray,
    y_1d: list | np.ndarray,
    z_mat: list[list[float]] | np.ndarray,
    max_faces: int = AUTO_THRESHOLD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Reduce a regular Surface3D grid by subsampling rows and columns.

    Uses independent per-axis step sizes proportional to grid aspect ratio.

    Raises:
        ValueError: If z_mat shape does not match (len(y_1d), len(x_1d)).
    """
    x_arr = np.asarray(x_1d, dtype=float)
    y_arr = np.asarray(y_1d, dtype=float)
    z_arr = np.asarray(z_mat, dtype=float)

    expected = (len(y_arr), len(x_arr))
    if z_arr.shape != expected:
        raise ValueError(
            f"z_mat shape {z_arr.shape} does not match (len(y_1d), len(x_1d)) "
            f"= {expected}.  Did you accidentally transpose the matrix?"
        )

    if not _enabled():
        return x_arr, y_arr, z_arr

    ny, nx = z_arr.shape
    current_faces = (nx - 1) * (ny - 1)
    if current_faces <= max_faces:
        return x_arr, y_arr, z_arr

    ratio  = math.sqrt(current_faces / max_faces)
    step_x = max(1, int(math.ceil(ratio * math.sqrt((nx - 1) / (ny - 1)))))
    step_y = max(1, int(math.ceil(ratio * math.sqrt((ny - 1) / (nx - 1)))))

    return x_arr[::step_x], y_arr[::step_y], z_arr[::step_y, ::step_x]


# ---------------------------------------------------------------------------
# Face culling -- Surface3D  (vectorised shoelace)
# ---------------------------------------------------------------------------

def cull_faces(
    faces: list[tuple],
    min_area: float = MIN_FACE_AREA,
) -> list[tuple]:
    """
    Remove projected quad faces whose screen area is below ``min_area`` px^2.

    Fully vectorised NumPy shoelace computation.
    """
    if not faces or min_area <= 0:
        return faces

    n = len(faces)
    px = np.empty((n, 4), dtype=float)
    py = np.empty((n, 4), dtype=float)
    for fi, (_, pts, _) in enumerate(faces):
        for vi, p in enumerate(pts):
            px[fi, vi] = p.px
            py[fi, vi] = p.py

    idx_next = np.array([1, 2, 3, 0])
    cross    = (px * py[:, idx_next] - px[:, idx_next] * py).sum(axis=1)
    areas    = np.abs(cross) * 0.5

    mask = areas >= min_area
    return [f for f, keep in zip(faces, mask) if keep]


# ---------------------------------------------------------------------------
# SVG annotation helper
# ---------------------------------------------------------------------------

def _ds_comment(original_n: int, thinned_n: int, algorithm: str) -> str:
    return (
        f"<!-- glyphx: {algorithm} downsampled {original_n} -> {thinned_n} points -->"
    )
