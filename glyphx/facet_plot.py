from __future__ import annotations

from .facet_grid import FacetGrid


def facet_plot(df, x=None, y=None, kind="line", theme="default",
               row=None, col=None, hue=None, **kwargs) -> FacetGrid:
    """
    Build a :class:`~glyphx.facet_grid.FacetGrid` and draw one chart per cell.

    Shorthand for ``FacetGrid(df, ...).map(kind, x=x, y=y)``.

    Args:
        df:    Source DataFrame.
        x:     X-axis column name.
        y:     Y-axis column name; not needed for ``"hist"`` or ``"kde"``.
        kind:  Chart kind passed to :meth:`FacetGrid.map`.
        theme: GlyphX theme name.
        row:   Column to facet down the Y axis.
        col:   Column to facet across the X axis.
        hue:   Column to color-code within each cell.
        **kwargs: Forwarded to the series constructor.

    Returns:
        FacetGrid: the mapped grid, ready to ``.show()`` or ``.render_svg()``.
    """
    # kind is a FacetGrid.map() argument, not a FacetGrid() one -- passing it
    # to the constructor raised TypeError on every call, including the example
    # in docs/advanced.rst.  x and y were accepted and silently dropped.
    grid = FacetGrid(df, row=row, col=col, hue=hue, theme=theme)
    return grid.map(kind, x=x, y=y, **kwargs)
