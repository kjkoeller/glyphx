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


def test_type_checking_block_matches_the_lazy_map():
    """
    The TYPE_CHECKING re-declarations exist so analysers, type checkers and
    IDEs can see the lazily-exported names -- pyflakes otherwise reports all
    53 as undefined names in __all__. That only holds while the block lists
    the same names _LAZY_ATTRS does, and nothing else keeps them in step.
    """
    import ast
    from pathlib import Path

    import glyphx

    source = Path(glyphx.__file__)
    tree = ast.parse(source.read_text(encoding="utf-8"))

    declared = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Name) and test.id == "_TYPE_CHECKING"):
            continue
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    declared.add(alias.asname or alias.name)

    lazy = set(glyphx._LAZY_ATTRS)
    assert declared == lazy, (
        f"TYPE_CHECKING block out of step with _LAZY_ATTRS.\n"
        f"  missing from the block: {sorted(lazy - declared)}\n"
        f"  in the block but not lazy: {sorted(declared - lazy)}"
    )


def test_no_undefined_names_in_dunder_all():
    """Every exported name must be visible to a static analyser."""
    import ast
    from pathlib import Path

    import glyphx

    tree = ast.parse(Path(glyphx.__file__).read_text(encoding="utf-8"))

    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            bound.add(node.name)

    undefined = [n for n in glyphx.__all__ if n not in bound]
    assert undefined == [], f"__all__ names a static checker cannot see: {undefined}"


def test_the_type_checking_block_does_not_make_imports_eager():
    """The whole point of the lazy map is that these are not imported."""
    r = _run("""
        import sys
        import glyphx
        loaded = {m for m in sys.modules if m.startswith("glyphx.")}
        eager = loaded & {"glyphx." + n for n in
                          ("ecdf", "raincloud", "treemap", "bar3d", "clustermap",
                           "choropleth", "gantt", "vega_lite", "figure3d")}
        assert not eager, f"imported eagerly: {sorted(eager)}"
        assert "pandas" not in sys.modules, "pandas was imported eagerly"
        print("ok")
    """)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
