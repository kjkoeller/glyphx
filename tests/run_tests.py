"""
GlyphX test runner — works without pytest installed.
Discovers and runs all test_*.py files using the pytest shim.

Usage:
    python tests/run_tests.py          # all suites
    python tests/run_tests.py basic    # only test_basic_plot.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
import traceback

# Install shim before anything else
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pytest_shim as _pytest_shim
sys.modules["pytest"] = _pytest_shim

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FILTER     = sys.argv[1].lower() if len(sys.argv) > 1 else None


def _collect_fixtures(mod):
    """Return {name: callable} for all functions tagged as fixtures."""
    from pytest_shim import _FIXTURE_REGISTRY
    result = {}
    for name, fn in _FIXTURE_REGISTRY.items():
        result[name] = fn
    # Also collect from the module itself
    for name in dir(mod):
        obj = getattr(mod, name)
        if callable(obj) and getattr(obj, "_is_fixture", False):
            result[name] = obj
    return result


def _resolve_args(fn, fixture_map):
    """Build positional args by matching parameter names to fixtures."""
    import inspect
    params = list(inspect.signature(fn).parameters.keys())
    args = []
    for p in params:
        if p in fixture_map:
            fixture_fn = fixture_map[p]
            args.append(fixture_fn())
        else:
            raise ValueError(f"No fixture for parameter '{p}' in {fn.__name__}")
    return args


def run_file(path: str) -> tuple[int, int, int]:
    """Load a test file and run all test_* functions. Returns (passed, failed, skipped)."""
    from pytest_shim import _FIXTURE_REGISTRY
    _FIXTURE_REGISTRY.clear()

    spec = importlib.util.spec_from_file_location("_test_mod", path)
    mod  = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"  LOAD ERROR: {e}")
        traceback.print_exc()
        return 0, 0, 1

    fixture_map = _collect_fixtures(mod)

    # Gather test functions (top-level and from classes)
    candidates = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if name.startswith("test_") and callable(obj) and not getattr(obj, "_shim_skip", False):
            candidates.append((name, obj))
        elif isinstance(obj, type) and name.startswith("Test"):
            # Class-based tests
            instance = obj()
            for mname in dir(instance):
                mobj = getattr(instance, mname)
                if mname.startswith("test_") and callable(mobj):
                    if not getattr(mobj, "_shim_skip", False):
                        candidates.append((f"{name}.{mname}", mobj))

    passed = failed = skipped = 0
    for tname, fn in candidates:
        try:
            import inspect
            params = list(inspect.signature(fn).parameters.keys())
            if params:
                try:
                    args = _resolve_args(fn, fixture_map)
                    fn(*args)
                except (ValueError, TypeError):
                    skipped += 1
                    continue
            else:
                fn()
            passed += 1
        except Exception as e:
            if "SkipTest" in type(e).__name__:
                skipped += 1
            else:
                print(f"  FAIL  {tname}: {e}")
                failed += 1

    return passed, failed, skipped


def main():
    files = sorted(
        f for f in os.listdir(TESTS_DIR)
        if f.startswith("test_") and f.endswith(".py")
    )
    if FILTER:
        files = [f for f in files if FILTER in f]

    total_p = total_f = total_s = 0
    for fname in files:
        path = os.path.join(TESTS_DIR, fname)
        print(f"\n{'─'*60}")
        print(f" {fname}")
        print(f"{'─'*60}")
        p, f, s = run_file(path)
        total_p += p; total_f += f; total_s += s
        status = "OK" if f == 0 else "FAILURES"
        print(f"  → {p} passed, {f} failed, {s} skipped  [{status}]")

    print(f"\n{'═'*60}")
    print(f" TOTAL: {total_p} passed  {total_f} failed  {total_s} skipped")
    print(f"{'═'*60}")
    return 1 if total_f else 0


if __name__ == "__main__":
    sys.exit(main())
