"""Import-order behaviour has to run in a fresh interpreter."""
import subprocess
import sys
import textwrap


def _run(code):
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)],
                          capture_output=True, text=True)

def test_importing_glyphx_does_not_import_pandas():
    r = _run("""
        import sys, glyphx
        assert "pandas" not in sys.modules, "pandas was imported eagerly"
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout

def test_accessor_registers_when_pandas_imported_after_glyphx():
    r = _run("""
        import glyphx, pandas as pd
        df = pd.DataFrame({"m": ["a", "b"], "v": [1, 2]})
        assert hasattr(df, "glyphx")
        assert df.glyphx.bar(x="m", y="v").render_svg().lstrip().startswith("<svg")
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout

def test_accessor_registers_when_pandas_imported_before_glyphx():
    r = _run("""
        import pandas as pd, glyphx
        df = pd.DataFrame({"m": ["a", "b"], "v": [1, 2]})
        assert hasattr(df, "glyphx")
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_submodule_import_does_not_shadow_the_exported_callable():
    """
    Seven exported names match their defining module (``regplot``,
    ``pairplot``, ...).  Importing the submodule binds it onto the package,
    normal attribute lookup then finds the module, and ``__getattr__`` is
    never consulted -- so ``glyphx.regplot`` silently became uncallable
    depending on import order.
    """
    r = _run("""
        import glyphx
        import glyphx.regplot          # binds the module onto the package
        assert callable(glyphx.regplot), type(glyphx.regplot)
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_internal_submodule_import_does_not_shadow_either():
    """``Figure.regplot`` does ``from .regplot import regplot`` internally."""
    r = _run("""
        import numpy as np, pandas as pd
        import glyphx
        from glyphx import Figure

        rng = np.random.default_rng(0)
        df = pd.DataFrame({"a": rng.normal(0, 1, 30)})
        df["b"] = 2 * df.a
        Figure(auto_display=False).regplot(df, x="a", y="b")

        assert callable(glyphx.regplot), type(glyphx.regplot)
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_every_shadowable_name_survives_its_submodule_import():
    r = _run("""
        import importlib, glyphx
        for name in sorted(glyphx._SHADOWABLE):
            importlib.import_module(f"glyphx.{name}")
            assert callable(getattr(glyphx, name)), name
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_submodules_remain_importable_in_their_own_right():
    """The guard must not break `from glyphx.regplot import regplot`."""
    r = _run("""
        import sys
        from glyphx.regplot import regplot
        assert callable(regplot)
        assert "glyphx.regplot" in sys.modules
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
