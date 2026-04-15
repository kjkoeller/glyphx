"""
Test configuration — installs the pytest shim before any test module loads.
When pytest is unavailable, this shim handles fixtures, raises, and marks.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pytest_shim  # noqa: F401 — registers shim in sys.modules["pytest"]
