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
