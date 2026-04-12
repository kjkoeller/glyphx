"""
GlyphX plot3d() — quick 3D chart creation.
"""
from __future__ import annotations

def plot3d(x=None, y=None, z=None, kind="scatter", data=None,
           title="", theme="default", auto_display=True, **kwargs):
    """
    Unified 3D plotting function — the fast path to any 3D chart type.

    Args:
        x, y, z:      Data arrays.  For ``"surface"`` x and y are 1-D grid
                      arrays and z is a 2-D matrix.
        kind:         ``"scatter"``, ``"surface"``, ``"line"``, ``"bar3d"``.
        data:         Alias for z (useful for surface: ``plot3d(data=Z_matrix)``)
        title:        Chart title.
        theme:        Theme name.
        auto_display: Call ``.show()`` automatically.
        **kwargs:     Passed to the series constructor.

    Returns:
        :class:`~glyphx.Figure3D`

    Examples::

        import numpy as np
        from glyphx import plot3d

        # 3D scatter
        xs = np.random.randn(300)
        plot3d(xs, np.random.randn(300), np.random.randn(300), kind="scatter")

        # Surface
        x = np.linspace(-3, 3, 40)
        X, Y = np.meshgrid(x, x)
        Z = np.sin(np.sqrt(X**2 + Y**2))
        plot3d(x, x, Z, kind="surface", cmap="plasma", title="sin(r)")
    """
    import difflib
    from .figure3d import Figure3D

    kind = kind.lower()
    valid = ["scatter", "surface", "line", "bar3d"]
    if kind not in valid:
        close = difflib.get_close_matches(kind, valid, n=2, cutoff=0.5)
        hint  = f"  Did you mean: {close}?" if close else ""
        raise ValueError(f"[glyphx.plot3d] Unsupported kind='{kind}'.{hint}\n"
                         f"Valid: {', '.join(valid)}")

    fig = Figure3D(title=title, theme=theme)

    if kind == "scatter":
        fig.scatter(x, y, z or data or [], **kwargs)
    elif kind == "surface":
        _z = z if z is not None else data
        fig.surface(x, y, _z, **kwargs)
    elif kind == "line":
        fig.line3d(x, y, z, **kwargs)
    elif kind == "bar3d":
        fig.bar3d(x, y, z or data, **kwargs)

    if auto_display:
        fig.show()
    return fig
