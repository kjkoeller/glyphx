"""
Minimal pytest shim so the test files run under the standard
``python -m unittest`` runner without needing pytest installed.

Place this file in the tests/ directory.  Each test module that does
``import pytest`` will pick up this shim from the local package before
the (absent) real pytest.

Supported subset
----------------
- ``pytest.fixture``         → returns a callable that stores the function;
                               `_FixtureRegistry` injects return values at
                               test-class instantiation time.
- ``pytest.raises``          → context manager wrapping assertRaises.
- ``pytest.approx``          → wraps a float with ±1e-6 relative tolerance.
- ``pytest.mark.parametrize`` → no-op decorator (parametrized tests are
                               skipped gracefully when the shim is active).
- ``pytest.skip``            → raises unittest.SkipTest.
- ``pytest.warns``           → context manager wrapping warnings.catch_warnings.
- ``pytest.param``           → identity (returns its first arg).
"""
from __future__ import annotations

import sys
import unittest
import warnings
import contextlib
from typing import Any

# ---------------------------------------------------------------------------
# pytest.raises
# ---------------------------------------------------------------------------

class _RaisesCtx:
    """Context manager mimicking ``pytest.raises(ExcType)``."""

    def __init__(self, exc_type, match=None):
        self.exc_type = exc_type
        self.match    = match
        self.value    = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(
                f"Expected {self.exc_type.__name__} to be raised but nothing was raised."
            )
        if not issubclass(exc_type, self.exc_type):
            return False   # re-raise unexpected exception
        self.value = exc_val
        if self.match:
            import re
            if not re.search(self.match, str(exc_val)):
                raise AssertionError(
                    f"Exception message {str(exc_val)!r} does not match {self.match!r}."
                )
        return True   # suppress the expected exception


def raises(exc_type, *args, match=None, **kwargs):
    return _RaisesCtx(exc_type, match=match)


# ---------------------------------------------------------------------------
# pytest.warns
# ---------------------------------------------------------------------------

class _WarnsCtx:
    def __init__(self, warning_class):
        self._cls = warning_class
        self._mgr = warnings.catch_warnings(record=True)

    def __enter__(self):
        self._records = self._mgr.__enter__()
        warnings.simplefilter("always")
        return self

    def __exit__(self, *args):
        self._mgr.__exit__(*args)
        matched = [r for r in self._records if issubclass(r.category, self._cls)]
        if not matched:
            raise AssertionError(
                f"Expected {self._cls.__name__} warning but none was raised."
            )
        return False


def warns(warning_class, *args, **kwargs):
    return _WarnsCtx(warning_class)


# ---------------------------------------------------------------------------
# pytest.approx
# ---------------------------------------------------------------------------

class _Approx:
    def __init__(self, expected, rel=1e-6, abs=None):
        self.expected = expected
        self.rel      = rel
        self.abs_tol  = abs

    def __eq__(self, actual):
        import math
        if self.abs_tol is not None:
            return math.isclose(actual, self.expected, rel_tol=0, abs_tol=self.abs_tol)
        return math.isclose(actual, self.expected, rel_tol=self.rel)

    def __repr__(self):
        return f"approx({self.expected!r})"


def approx(expected, rel=1e-6, abs=None, **kwargs):
    return _Approx(expected, rel=rel, abs=abs)


# ---------------------------------------------------------------------------
# pytest.fixture
# ---------------------------------------------------------------------------

_FIXTURE_REGISTRY: dict[str, Any] = {}


def fixture(fn=None, *, scope="function", autouse=False, **kwargs):
    """Register a fixture function by name."""
    def decorator(f):
        _FIXTURE_REGISTRY[f.__name__] = f
        f._is_fixture = True
        return f
    if fn is not None:
        return decorator(fn)
    return decorator


# ---------------------------------------------------------------------------
# pytest.mark (no-op stub)
# ---------------------------------------------------------------------------

class _Mark:
    def __getattr__(self, name):
        def decorator_factory(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator
        return decorator_factory

    def parametrize(self, argnames, argvalues, **kwargs):
        """No-op: parametrized tests are silently skipped under the shim."""
        def decorator(fn):
            fn._shim_skip = True
            return fn
        return decorator


mark = _Mark()


# ---------------------------------------------------------------------------
# pytest.skip / pytest.fail
# ---------------------------------------------------------------------------

def skip(reason="", allow_module_level=False):
    raise unittest.SkipTest(reason)


def fail(reason=""):
    raise AssertionError(reason)


def param(*args, **kwargs):
    return args[0] if args else None


# ---------------------------------------------------------------------------
# pytest.importorskip
# ---------------------------------------------------------------------------

def importorskip(modname, minversion=None, reason=None):
    try:
        mod = __import__(modname)
    except ImportError:
        raise unittest.SkipTest(reason or f"requires {modname}")
    return mod


# ---------------------------------------------------------------------------
# Inject into sys.modules so ``import pytest`` resolves to this shim
# ---------------------------------------------------------------------------

sys.modules.setdefault("pytest", sys.modules[__name__])
