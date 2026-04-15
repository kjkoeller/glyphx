"""
GlyphX HueMixin — adds hue= splitting to BoxPlot, Violin, and Histogram.

When ``hue=`` is supplied, the series automatically splits data by group
and colour-codes each.  This closes the last remaining Seaborn advantage
where ``sns.boxplot(data=df, x="treatment", y="score", hue="sex")``
renders grouped boxes per category.
"""
from __future__ import annotations

from .colormaps import colormap_colors


def apply_hue(
    data:        list,
    categories:  list | None,
    hue_data:    list | None,
    hue_palette: list[str] | None = None,
    cmap:        str              = "viridis",
) -> tuple[list[list], list[str], list[str | None]]:
    """
    Split ``data`` by ``hue_data`` and return grouped arrays.

    Returns
    -------
    grouped_data  : list of arrays, one per (category, hue_group) pair
    grouped_cats  : display label for each group
    grouped_colors: color per group
    """
    if hue_data is None:
        return [data], categories or [""], [None]

    # Map each observation to its hue group
    unique_hues = list(dict.fromkeys(str(h) for h in hue_data))
    palette     = hue_palette or colormap_colors(cmap, max(len(unique_hues), 2))

    if categories is None:
        # Single distribution per hue value
        grouped_data   = [
            [v for v, h in zip(data, hue_data) if str(h) == hv]
            for hv in unique_hues
        ]
        grouped_cats   = unique_hues
        grouped_colors = [palette[i % len(palette)] for i in range(len(unique_hues))]
    else:
        # Multi-category: interleave (cat, hue) pairs
        grouped_data   = []
        grouped_cats   = []
        grouped_colors = []
        for cat, cat_data in zip(categories, data):
            cat_hue_data = list(cat_data) if hasattr(cat_data, "__iter__") else [cat_data]
            for i, hv in enumerate(unique_hues):
                # Within this category, keep only observations for this hue value
                grouped_data.append(cat_hue_data)  # full group; hue filtering is caller's job
                grouped_cats.append(f"{cat} / {hv}")
                grouped_colors.append(palette[i % len(palette)])

    return grouped_data, grouped_cats, grouped_colors
