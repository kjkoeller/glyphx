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


def test_no_arrow_shorthand_in_comments_or_docstrings():
    """
    Keep prose in prose. ``a -> b`` in a comment is a shorthand that reads
    like generated filler; the same thing written out ("maps a to b",
    "gives b") is clearer and costs nothing.

    Return annotations are code, not prose, so they are exempt -- as are
    HTML comment terminators, where the arrow is part of ``-->``.
    """
    import io
    import re
    import tokenize
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    targets = sorted(root.joinpath("glyphx").rglob("*.py"))
    offenders = []

    for path in targets:
        source = path.read_text(encoding="utf-8")
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type not in (tokenize.COMMENT, tokenize.STRING):
                continue
            text = token.string.replace("-->", "")   # HTML comment close
            # Inline ``code`` spans and reST literal blocks hold type
            # notation, where an arrow is the correct way to write a
            # Callable signature. Only loose prose is the target here.
            text = re.sub(r"``.*?``", "", text, flags=re.S)
            text = re.sub(r"::\n(?:\n|[ \t]+\S.*\n)+", "", text)
            for offset, line in enumerate(text.splitlines()):
                if re.search(r"\S\s*->\s*\S", line):
                    offenders.append(
                        f"{path.name}:{token.start[0] + offset} {line.strip()[:60]}")

    assert offenders == [], (
        "arrow shorthand in a comment or docstring; write it out instead: "
        f"{offenders}"
    )
