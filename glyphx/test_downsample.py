"""
GlyphX downsampling test suite.

Runs correctness tests (unittest) and speed benchmarks (timeit) for every
downsampling algorithm.  No external dependencies beyond the stdlib and NumPy.

Usage:
    python test_downsample.py           # correctness + benchmarks
    python test_downsample.py --fast    # correctness only (skip benchmarks)
"""
from __future__ import annotations

import sys
import math
import time
import timeit
import unittest
import warnings
import threading
import numpy as np

# ---------------------------------------------------------------------------
# Bootstrap: point sys.path at the patched glyphx package
# ---------------------------------------------------------------------------

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
# The test file lives alongside downsample.py inside the glyphx package dir.
# Walk up one level to get the package root on the path.
sys.path.insert(0, os.path.dirname(_HERE))

from glyphx.downsample import (
    lttb, m4, maybe_downsample_line, maybe_downsample,
    voxel_thin_2d, voxel_thin_3d,
    lttb_3d, decimate_grid, cull_faces,
    enable, disable, is_enabled,
    AUTO_THRESHOLD, _lttb3d_cache, _data_fingerprint,
)
from glyphx.projection3d import Camera3D

RNG = np.random.default_rng(42)
FAST = "--fast" in sys.argv


# ===========================================================================
# Helpers
# ===========================================================================

def _cam(az=45, el=30):
    return Camera3D(azimuth=az, elevation=el, cx=320, cy=240, scale=200)


def _line(n):
    x = np.linspace(0, 1, n)
    y = np.sin(x * 50) + 0.1 * RNG.standard_normal(n)
    return x, y


def _scatter_2d(n):
    return RNG.uniform(0, 1, n), RNG.uniform(0, 1, n)


def _scatter_3d(n):
    return (RNG.uniform(0, 1, n), RNG.uniform(0, 1, n), RNG.uniform(0, 1, n))


def _helix(n):
    t = np.linspace(0, 4 * math.pi, n)
    return np.cos(t), np.sin(t), t / (4 * math.pi)


class FakePt:
    """Minimal stand-in for projection3d.Projected."""
    def __init__(self, px, py):
        self.px = px
        self.py = py


def _make_faces(n, size=10.0):
    """n quads, each size x size pixels."""
    faces = []
    for i in range(n):
        x0, y0 = float(i * size), 0.0
        pts = [FakePt(x0, y0), FakePt(x0 + size, y0),
               FakePt(x0 + size, size), FakePt(x0, size)]
        faces.append((float(i), pts, 1.0))
    return faces


# ===========================================================================
# Correctness tests
# ===========================================================================

class TestLTTB(unittest.TestCase):

    def test_output_length_exact(self):
        x, y = _line(20_000)
        xd, yd = lttb(x, y, 500)
        self.assertEqual(len(xd), 500)
        self.assertEqual(len(yd), 500)

    def test_first_last_preserved(self):
        x, y = _line(10_000)
        xd, yd = lttb(x, y, 300)
        self.assertAlmostEqual(float(xd[0]),  float(x[0]))
        self.assertAlmostEqual(float(xd[-1]), float(x[-1]))
        self.assertAlmostEqual(float(yd[0]),  float(y[0]))
        self.assertAlmostEqual(float(yd[-1]), float(y[-1]))

    def test_no_op_below_threshold(self):
        x, y = _line(100)
        xd, yd = lttb(x, y, 500)
        np.testing.assert_array_equal(xd, x)
        np.testing.assert_array_equal(yd, y)

    def test_raises_length_mismatch(self):
        with self.assertRaises(ValueError):
            lttb([1, 2, 3], [1, 2], 10)

    def test_raises_threshold_too_small(self):
        with self.assertRaises(ValueError):
            lttb([1, 2, 3, 4, 5], [1, 2, 3, 4, 5], 2)

    def test_threshold_3(self):
        x, y = _line(1_000)
        xd, yd = lttb(x, y, 3)
        self.assertEqual(len(xd), 3)

    def test_monotone_output(self):
        """Selected x values should be in ascending order (input is sorted)."""
        x, y = _line(10_000)
        xd, yd = lttb(x, y, 500)
        self.assertTrue(np.all(np.diff(xd) >= 0))

    def test_peaks_retained(self):
        """A pure sine wave's global max/min should survive downsampling."""
        x = np.linspace(0, 2 * math.pi, 50_000)
        y = np.sin(x)
        xd, yd = lttb(x, y, 200)
        self.assertGreater(float(yd.max()), 0.99)
        self.assertLess(float(yd.min()),   -0.99)


class TestM4(unittest.TestCase):

    def test_output_at_most_4x_width(self):
        x, y = _line(100_000)
        xd, yd = m4(x, y, pixel_width=800)
        self.assertLessEqual(len(xd), 4 * 800)

    def test_first_last_preserved(self):
        x, y = _line(50_000)
        xd, yd = m4(x, y, pixel_width=800)
        self.assertAlmostEqual(float(xd[0]),  float(x[0]))
        self.assertAlmostEqual(float(xd[-1]), float(x[-1]))

    def test_empty_input(self):
        xd, yd = m4(np.array([]), np.array([]), 800)
        self.assertEqual(len(xd), 0)

    def test_non_monotone_warns_and_sorts(self):
        x = np.array([3., 1., 4., 1., 5., 9., 2., 6.])
        y = np.sin(x)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            xd, yd = m4(x, y, pixel_width=100)
        user_warns = [wx for wx in w if issubclass(wx.category, UserWarning)]
        self.assertEqual(len(user_warns), 1)
        self.assertIn("monotone", str(user_warns[0].message).lower())
        self.assertTrue(np.all(np.diff(xd) >= 0))

    def test_monotone_no_warning(self):
        x, y = _line(20_000)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            m4(x, y, pixel_width=800)
        user_warns = [wx for wx in w if issubclass(wx.category, UserWarning)]
        self.assertEqual(len(user_warns), 0)

    def test_min_max_preserved(self):
        x = np.linspace(0, 1, 100_000)
        y = np.sin(x * 100)
        xd, yd = m4(x, y, pixel_width=800)
        self.assertAlmostEqual(float(yd.max()), float(y.max()), places=3)
        self.assertAlmostEqual(float(yd.min()), float(y.min()), places=3)


class TestMaybeDownsampleLine(unittest.TestCase):

    def test_no_op_below_threshold(self):
        x, y = _line(1_000)
        xd, yd = maybe_downsample_line(x, y)
        np.testing.assert_array_equal(xd, x)

    def test_reduces_large_input(self):
        x, y = _line(200_000)
        xd, yd = maybe_downsample_line(x, y, pixel_width=800)
        self.assertLessEqual(len(xd), AUTO_THRESHOLD)

    def test_kill_switch(self):
        x, y = _line(200_000)
        disable()
        xd, yd = maybe_downsample_line(x, y)
        enable()
        self.assertEqual(len(xd), 200_000)

    def test_deprecated_wrapper_warns(self):
        x, y = _line(10_000)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            maybe_downsample(x, y)
        dep = [wx for wx in w if issubclass(wx.category, DeprecationWarning)]
        self.assertEqual(len(dep), 1)


class TestVoxelThin2D(unittest.TestCase):

    def test_reduces_large_cloud(self):
        x, y = _scatter_2d(30_000)
        xt, yt, ct = voxel_thin_2d(x, y)
        # Output may slightly exceed AUTO_THRESHOLD because occupied-cell
        # count depends on data distribution; allow 20% slack.
        self.assertLessEqual(len(xt), int(AUTO_THRESHOLD * 1.2))
        self.assertIsNone(ct)

    def test_no_op_below_threshold(self):
        x, y = _scatter_2d(100)
        xt, yt, ct = voxel_thin_2d(x, y)
        self.assertEqual(len(xt), 100)

    def test_c_threaded_same_length(self):
        x, y = _scatter_2d(20_000)
        c = RNG.uniform(0, 1, 20_000)
        xt, yt, ct = voxel_thin_2d(x, y, c=c)
        self.assertEqual(len(ct), len(xt))

    def test_c_dtype_preserved(self):
        x, y = _scatter_2d(20_000)
        c = np.arange(20_000, dtype=np.int32)
        xt, yt, ct = voxel_thin_2d(x, y, c=c)
        self.assertEqual(ct.dtype, np.int32)

    def test_raises_length_mismatch(self):
        with self.assertRaises(ValueError):
            voxel_thin_2d([1, 2, 3], [1, 2])

    def test_spatial_coverage(self):
        """Output should span roughly the same bounding box as input."""
        x, y = _scatter_2d(30_000)
        xt, yt, _ = voxel_thin_2d(x, y)
        self.assertAlmostEqual(float(xt.min()), float(x.min()), delta=0.05)
        self.assertAlmostEqual(float(xt.max()), float(x.max()), delta=0.05)

    def test_kill_switch(self):
        x, y = _scatter_2d(30_000)
        disable()
        xt, yt, _ = voxel_thin_2d(x, y)
        enable()
        self.assertEqual(len(xt), 30_000)


class TestVoxelThin3D(unittest.TestCase):

    def test_reduces_large_cloud(self):
        x, y, z = _scatter_3d(30_000)
        xt, yt, zt, ct = voxel_thin_3d(x, y, z)
        # Allow 20% slack for the same reason as voxel_2d.
        self.assertLessEqual(len(xt), int(AUTO_THRESHOLD * 1.2))
        self.assertIsNone(ct)

    def test_colors_threaded(self):
        x, y, z = _scatter_3d(20_000)
        cols = [f"#{i:06x}" for i in range(20_000)]
        xt, yt, zt, ct = voxel_thin_3d(x, y, z, colors=cols)
        self.assertEqual(len(ct), len(xt))

    def test_raises_length_mismatch(self):
        with self.assertRaises(ValueError):
            voxel_thin_3d([1, 2, 3], [1, 2, 3], [1, 2])

    def test_no_op_below_threshold(self):
        x, y, z = _scatter_3d(100)
        xt, yt, zt, _ = voxel_thin_3d(x, y, z)
        self.assertEqual(len(xt), 100)


class TestLTTB3D(unittest.TestCase):

    def test_output_length(self):
        cam = _cam()
        x, y, z = _helix(20_000)
        xd, yd, zd = lttb_3d(x, y, z, cam, threshold=500)
        self.assertEqual(len(xd), 500)
        self.assertEqual(len(yd), 500)
        self.assertEqual(len(zd), 500)

    def test_no_op_below_threshold(self):
        cam = _cam()
        x, y, z = _helix(100)
        xd, yd, zd = lttb_3d(x, y, z, cam, threshold=500)
        self.assertEqual(len(xd), 100)

    def test_raises_length_mismatch(self):
        cam = _cam()
        with self.assertRaises(ValueError):
            lttb_3d([1, 2, 3], [1, 2, 3], [1, 2], cam)

    def test_cache_hit(self):
        cam = _cam()
        x, y, z = _helix(20_000)
        r1 = lttb_3d(x, y, z, cam, threshold=500)
        r2 = lttb_3d(x, y, z, cam, threshold=500)
        np.testing.assert_array_equal(r1[0], r2[0])
        self.assertIn(cam, _lttb3d_cache)

    def test_cache_miss_on_angle_change(self):
        cam = _cam()
        x, y, z = _helix(20_000)
        r1 = lttb_3d(x, y, z, cam, threshold=500)
        cam.azimuth = 135;  cam._update()
        r2 = lttb_3d(x, y, z, cam, threshold=500)
        self.assertFalse(np.array_equal(r1[0], r2[0]))

    def test_fingerprint_uses_8_samples(self):
        """Two arrays differing at a sampled index get different fingerprints."""
        n = 1_000
        # np.linspace(0, n-1, 8, dtype=int) gives sampled indices:
        # [0, 142, 285, 428, 571, 714, 857, 999]
        # Modify index 571 which is guaranteed to be sampled.
        x1 = np.linspace(0, 1, n)
        # Sampled indices for n=1000: [0,142,285,428,570,713,856,999]
        x2 = x1.copy();  x2[570] += 99.0
        y  = np.zeros(n)
        fp1 = _data_fingerprint(x1, y, y, 500)
        fp2 = _data_fingerprint(x2, y, y, 500)
        self.assertNotEqual(fp1, fp2)

    def test_kill_switch(self):
        cam = _cam()
        x, y, z = _helix(20_000)
        disable()
        xd, yd, zd = lttb_3d(x, y, z, cam, threshold=500)
        enable()
        self.assertEqual(len(xd), 20_000)


class TestDecimateGrid(unittest.TestCase):

    def test_reduces_faces(self):
        x = np.linspace(0, 1, 300);  y = np.linspace(0, 1, 300)
        Z = RNG.random((300, 300))
        xd, yd, zd = decimate_grid(x, y, Z)
        faces = (len(xd) - 1) * (len(yd) - 1)
        self.assertLessEqual(faces, AUTO_THRESHOLD)

    def test_no_op_small_grid(self):
        x = np.linspace(0, 1, 50);  y = np.linspace(0, 1, 50)
        Z = RNG.random((50, 50))
        xd, yd, zd = decimate_grid(x, y, Z)
        self.assertEqual(len(xd), 50)

    def test_shape_mismatch_raises(self):
        x = np.linspace(0, 1, 5);  y = np.linspace(0, 1, 3)
        Z = np.zeros((5, 3))  # transposed — wrong shape
        with self.assertRaises(ValueError):
            decimate_grid(x, y, Z)

    def test_non_square_proportional(self):
        """Tall thin grid: x axis should barely be touched."""
        x = np.linspace(0, 1, 10);  y = np.linspace(0, 1, 1_000)
        Z = RNG.random((1_000, 10))
        xd, yd, zd = decimate_grid(x, y, Z)
        self.assertLessEqual(len(xd), 10)   # x untouched or barely touched
        self.assertLess(len(yd), 1_000)     # y decimated


class TestCullFaces(unittest.TestCase):

    def test_removes_tiny_faces(self):
        faces = [
            (1.0, [FakePt(0,0), FakePt(20,0), FakePt(20,20), FakePt(0,20)], 1.0),
            (0.5, [FakePt(0,0), FakePt(.1,0), FakePt(.1,.1), FakePt(0,.1)], 1.0),
        ]
        kept = cull_faces(faces)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0][0], 1.0)

    def test_keeps_all_large(self):
        faces = _make_faces(100, size=20.0)
        kept = cull_faces(faces)
        self.assertEqual(len(kept), 100)

    def test_empty_input(self):
        self.assertEqual(cull_faces([]), [])

    def test_min_area_zero_keeps_all(self):
        faces = _make_faces(10, size=0.01)
        kept = cull_faces(faces, min_area=0.0)
        self.assertEqual(len(kept), 10)

    def test_large_batch_vectorised(self):
        """50 000 faces should complete in under 500 ms."""
        faces = _make_faces(50_000, size=10.0)
        t0 = time.perf_counter()
        kept = cull_faces(faces)
        elapsed = time.perf_counter() - t0
        self.assertEqual(len(kept), 50_000)
        self.assertLess(elapsed, 0.5)


class TestThreadSafety(unittest.TestCase):

    def test_disable_is_per_thread(self):
        results = {}
        def worker():
            disable()
            results["worker"] = is_enabled()
        t = threading.Thread(target=worker)
        t.start();  t.join()
        self.assertFalse(results["worker"])
        self.assertTrue(is_enabled())  # main thread unaffected

    def test_enable_restore(self):
        disable()
        self.assertFalse(is_enabled())
        enable()
        self.assertTrue(is_enabled())


# ===========================================================================
# Speed benchmarks
# ===========================================================================

class SpeedBenchmark:
    """Lightweight benchmark runner using timeit."""

    def __init__(self):
        self.results: list[tuple[str, float, str]] = []

    def run(self, label: str, stmt, g: dict, number: int = 5, note: str = ""):
        t = timeit.timeit(stmt, number=number, globals=g)
        avg_ms = t / number * 1000
        self.results.append((label, avg_ms, note))
        print(f"  {label:<45} {avg_ms:8.1f} ms   {note}")

    def summary(self):
        print()
        print(f"{'Benchmark':<45} {'avg ms':>8}   note")
        print("-" * 70)
        for label, ms, note in self.results:
            print(f"  {label:<45} {ms:8.1f}   {note}")


def run_benchmarks():
    print("\n" + "=" * 70)
    print("SPEED BENCHMARKS")
    print("=" * 70)
    bench = SpeedBenchmark()

    _g = {
        "lttb": lttb, "m4": m4,
        "maybe_downsample_line": maybe_downsample_line,
        "voxel_thin_2d": voxel_thin_2d, "voxel_thin_3d": voxel_thin_3d,
        "lttb_3d": lttb_3d, "decimate_grid": decimate_grid,
        "cull_faces": cull_faces,
    }

    # ── LTTB ────────────────────────────────────────────────────────────
    print("\n[LTTB]")
    for n in [10_000, 100_000, 500_000]:
        x, y = _line(n)
        g = dict(_g, _x=x.copy(), _y=y.copy())
        bench.run(f"lttb n={n:>7} -> 5k",
                  "lttb(_x, _y, 5000)", g, number=5,
                  note="vectorised inner loop")

    # ── M4 ──────────────────────────────────────────────────────────────
    print("\n[M4]")
    for n in [100_000, 1_000_000]:
        x, y = _line(n)
        g = dict(_g, _x=x.copy(), _y=y.copy())
        bench.run(f"m4 n={n:>8} pw=800",
                  "m4(_x, _y, 800)", g, number=5,
                  note="np.digitize + reduceat")

    # ── Two-stage pipeline ───────────────────────────────────────────────
    print("\n[maybe_downsample_line]")
    for n in [100_000, 500_000]:
        x, y = _line(n)
        g = dict(_g, _x=x.copy(), _y=y.copy())
        bench.run(f"pipeline n={n:>7}",
                  "maybe_downsample_line(_x, _y, 800)", g, number=5,
                  note="M4 then LTTB")

    # ── Voxel 2D ────────────────────────────────────────────────────────
    print("\n[voxel_thin_2d]")
    for n in [30_000, 200_000, 1_000_000]:
        x, y = _scatter_2d(n)
        g = dict(_g, _x=x.copy(), _y=y.copy())
        bench.run(f"voxel_2d n={n:>8}",
                  "voxel_thin_2d(_x, _y)", g, number=5,
                  note="reduceat nearest-centroid")

    # ── Voxel 3D ────────────────────────────────────────────────────────
    print("\n[voxel_thin_3d]")
    for n in [30_000, 200_000]:
        x, y, z = _scatter_3d(n)
        g = dict(_g, _x=x.copy(), _y=y.copy(), _z=z.copy())
        bench.run(f"voxel_3d n={n:>8}",
                  "voxel_thin_3d(_x, _y, _z)", g, number=5,
                  note="reduceat nearest-centroid")

    # ── LTTB 3D ─────────────────────────────────────────────────────────
    print("\n[lttb_3d]")
    for n in [10_000, 100_000]:
        x, y, z = _helix(n)
        g = dict(_g, _x=x.copy(), _y=y.copy(), _z=z.copy(), _cam=_cam())
        bench.run(f"lttb_3d n={n:>7} -> 5k",
                  "lttb_3d(_x, _y, _z, _cam, threshold=5000)", g, number=5,
                  note="vectorised projection + inner loop")

    # ── cull_faces ───────────────────────────────────────────────────────
    print("\n[cull_faces]")
    for n in [10_000, 50_000]:
        g = dict(_g, _faces=_make_faces(n))
        bench.run(f"cull_faces n={n:>6}",
                  "cull_faces(_faces)", g, number=10,
                  note="vectorised shoelace")

    # ── decimate_grid ────────────────────────────────────────────────────
    print("\n[decimate_grid]")
    for sz in [200, 500]:
        xg = np.linspace(0, 1, sz); yg = np.linspace(0, 1, sz)
        Z  = RNG.random((sz, sz))
        g  = dict(_g, _x=xg, _y=yg, _Z=Z)
        bench.run(f"decimate_grid {sz}x{sz}",
                  "decimate_grid(_x, _y, _Z)", g, number=20,
                  note="slice-based")

    bench.summary()


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    # Strip benchmark flag before passing to unittest
    argv = [a for a in sys.argv if a != "--fast"]

    print("=" * 70)
    print("CORRECTNESS TESTS")
    print("=" * 70)
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not FAST:
        run_benchmarks()

    sys.exit(0 if result.wasSuccessful() else 1)
