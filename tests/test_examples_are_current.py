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


# ---------------------------------------------------------------------------
# Cross-platform reproducibility
# ---------------------------------------------------------------------------

def test_geometry_is_rounded_so_output_is_platform_stable():
    """
    Coordinates come from numpy and libm, whose last bits differ between
    platforms: the same chart produced 28.600002002128278 on Linux and
    ...274 on Windows. Invisible at well under a pixel, but it made the
    committed examples fail a byte comparison on Windows CI only.
    """
    import re

    import numpy as np

    from glyphx import Figure

    xs = list(np.linspace(0, 120, 200))
    ys = [float(v) for v in np.sin(np.array(xs) / 9) * 10 + 40]
    svg = Figure(auto_display=False).line(xs, ys).render_svg()

    unrounded = re.findall(
        r'(?<![\w-])(?:x|y|cx|cy|x1|y1|x2|y2|d|points|width|height)'
        r'="[^"]*?\d\.\d{4,}', svg)
    assert unrounded == [], f"unrounded geometry survives: {unrounded[:3]}"


def test_rounding_leaves_data_attributes_alone():
    """
    data- attributes carry the values behind tooltips, selection and the
    detail panel. Rounding those would change what a reader is shown, and
    \\b alone would have done exactly that by matching the "y" in data-y.
    """
    from glyphx.utils import round_svg_geometry

    markup = ('<circle cx="28.600002002128278" data-y="28.600002002128278" '
              'data-x="1.23456789012"/>')
    out = round_svg_geometry(markup)
    assert 'cx="28.6"' in out
    assert 'data-y="28.600002002128278"' in out
    assert 'data-x="1.23456789012"' in out


def test_rounding_is_idempotent():
    """Re-rendering must not drift a second time."""
    from glyphx.utils import round_svg_geometry

    once = round_svg_geometry('<rect x="1.23456789" width="9.87654321"/>')
    assert round_svg_geometry(once) == once
