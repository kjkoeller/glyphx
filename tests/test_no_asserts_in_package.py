"""
Guard: the shipped package must contain no ``assert`` statements.

``python -O`` strips asserts, so one used as a runtime check disappears in an
optimised build -- which is what Bandit's B101 flags. Test asserts are fine
(pytest is never run under -O) and are excluded from the scan in .codacy.yml;
this keeps the *package* side honest so the exclusion stays narrow.
"""

import ast
from pathlib import Path


def test_package_contains_no_assert_statements():
    package = Path(__file__).resolve().parent.parent / "glyphx"
    offenders = []

    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                offenders.append(f"{path.name}:{node.lineno}")

    assert offenders == [], (
        f"assert statements in shipped code (stripped by python -O; "
        f"raise a real exception instead): {offenders}"
    )


def test_every_definition_in_the_package_has_a_docstring():
    """
    Guard against the count creeping back up.

    Single-line docstrings are fine and deliberate -- PEP 257 endorses them
    for obvious functions, and padding a one-line setter into an Args block
    adds noise rather than information. What this checks is that a docstring
    exists at all.
    """
    import ast
    from pathlib import Path

    package = Path(__file__).resolve().parent.parent / "glyphx"
    missing = []

    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)) and ast.get_docstring(node) is None:
                missing.append(f"{path.name}:{node.lineno} {node.name}")

    assert missing == [], f"definitions without a docstring: {missing}"
