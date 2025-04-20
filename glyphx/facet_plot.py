from .facet_grid import FacetGrid

def facet_plot(df, x=None, y=None, kind="line", theme="default", row=None, col=None, hue=None):
    # Reuse plot() internally by FacetGrid
    grid = FacetGrid(df, row=row, col=col, hue=hue, kind=kind, theme=theme)
    return grid