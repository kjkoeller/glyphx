"""
Guard: docs/examples/ must match what examples.py produces.

Twenty-one committed SVGs had silently gone stale. The worst was
colorblind_theme.svg, which still rendered every series in the default blue
because the theme palette never reached the series -- so the image
illustrating the accessibility feature was showing the bug it exists to
demonstrate, long after the bug itself was fixed.

Regenerating is one command; noticing it was needed was the hard part.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples.py"
OUTPUT = REPO / "docs" / "examples"


def _svg_snapshot():
    return {p.name: p.read_bytes() for p in sorted(OUTPUT.glob("*.svg"))}


@pytest.mark.slow
def test_committed_examples_match_a_fresh_run(tmp_path):
    """
    Re-runs examples.py and compares. Rendering is deterministic -- chart ids
    are content hashes, not UUIDs -- so a difference means the committed
    images are behind the code.
    """
    pytest.importorskip("pandas")
    before = _svg_snapshot()
    if not before:
        pytest.skip("no committed examples to compare against")

    backup = tmp_path / "backup"
    backup.mkdir()
    for name, data in before.items():
        (backup / name).write_bytes(data)

    try:
        result = subprocess.run(
            [sys.executable, str(EXAMPLES)],
            cwd=REPO, capture_output=True, text=True, timeout=600,
        )
        assert result.returncode == 0, f"examples.py failed:\n{result.stderr}"
        after = _svg_snapshot()

        stale = sorted(n for n in before if n in after and before[n] != after[n])
        missing = sorted(set(before) - set(after))
    finally:
        # Leave the tree exactly as it was, pass or fail.
        for name, data in before.items():
            (OUTPUT / name).write_bytes(data)
        for extra in set(_svg_snapshot()) - set(before):
            (OUTPUT / extra).unlink()

    assert not stale, (
        f"{len(stale)} committed example(s) are behind examples.py. "
        f"Run `python examples.py` and commit the result: {stale}"
    )
    assert not missing, f"examples.py no longer produces: {missing}"


def test_examples_script_covers_the_public_layout_and_theme_api():
    """
    New features kept shipping without an example. These are the ones with a
    visual result worth showing in the docs.
    """
    source = EXAMPLES.read_text(encoding="utf-8")
    expected = [
        "inset_axes",
        "shared_x",
        "set_tick_wrap",
        "set_y2label",
        "register_theme",
        "enable_crossfilter",
        "SubplotGrid",
        "set_tick_format",
    ]
    missing = [name for name in expected if name not in source]
    assert missing == [], f"examples.py has no example for: {missing}"
