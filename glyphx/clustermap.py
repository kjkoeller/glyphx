"""
GlyphX clustermap -- hierarchically clustered heatmap with dendrograms.

The clustermap is Seaborn's most distinctive chart in bioinformatics and
machine learning.  Seaborn's ``sns.clustermap()`` requires scipy; GlyphX
implements the full pipeline (hierarchical clustering, dendrogram layout,
heatmap rendering) in pure NumPy -- no scipy, no matplotlib required.

    from glyphx.clustermap import clustermap

    fig = clustermap(
        df,                      # DataFrame or 2-D array
        cmap="viridis",
        row_cluster=True,
        col_cluster=True,
        title="Gene Expression",
    )
    fig.show()
"""
from __future__ import annotations

import math
import numpy as np
from typing import Any

from .figure   import Figure
from .series   import HeatmapSeries
from .colormaps import colormap_colors, apply_colormap
from .utils    import svg_escape, _format_tick


# ---------------------------------------------------------------------------
# Pure-NumPy hierarchical clustering (average linkage, Euclidean distance)
# ---------------------------------------------------------------------------

def _pdist(X: np.ndarray) -> np.ndarray:
    """Pairwise Euclidean distance matrix (nxn)."""
    n = len(X)
    D = np.zeros((n, n))
    for i in range(n):
        diff = X[i] - X   # broadcast
        D[i] = np.sqrt((diff ** 2).sum(axis=1))
    return D


def _average_linkage(D: np.ndarray) -> list[tuple]:
    """
    UPGMA (average linkage) hierarchical clustering.

    Returns a linkage list compatible with the Scipy/Matplotlib convention:
    ``[(left_id, right_id, distance, cluster_size), ...]``.
    """
    n    = len(D)
    dist = D.copy()
    np.fill_diagonal(dist, np.inf)

    # Cluster membership: initially each point is its own cluster
    members: list[list[int]] = [[i] for i in range(n)]
    active  = list(range(n))
    linkage = []
    next_id = n

    while len(active) > 1:
        # Find closest pair among active clusters
        min_d = np.inf
        ci, cj = -1, -1
        for ii in range(len(active)):
            for jj in range(ii + 1, len(active)):
                a, b = active[ii], active[jj]
                d    = dist[a, b]
                if d < min_d:
                    min_d = d
                    ci, cj = ii, jj

        ai, aj = active[ci], active[cj]
        merged  = members[ai] + members[aj]
        linkage.append((ai, aj, min_d, len(merged)))

        # Merge: update distances to the new cluster (average linkage)
        new_row = np.full(dist.shape[0] + 1, np.inf)
        for ak in active:
            if ak == ai or ak == aj:
                continue
            d_new = (dist[ai, ak] * len(members[ai]) +
                     dist[aj, ak] * len(members[aj])) / len(merged)
            new_row[ak] = d_new

        # Grow distance matrix
        old_size  = dist.shape[0]
        new_dist  = np.full((old_size + 1, old_size + 1), np.inf)
        new_dist[:old_size, :old_size] = dist
        new_dist[next_id, :old_size]   = new_row[:old_size]
        new_dist[:old_size, next_id]   = new_row[:old_size]
        dist = new_dist

        members.append(merged)
        active.remove(ai)
        active.remove(aj)
        active.append(next_id)
        next_id += 1

    return linkage


def _leaf_order(linkage: list[tuple], n_leaves: int) -> list[int]:
    """
    Traverse the linkage tree and return the leaf order (left-to-right DFS).
    """
    n       = n_leaves
    children: dict[int, tuple[int, int]] = {}
    for i, (a, b, *_) in enumerate(linkage):
        children[n + i] = (int(a), int(b))

    root = n + len(linkage) - 1

    def _dfs(node: int) -> list[int]:
        if node < n:
            return [node]
        l, r = children[node]
        return _dfs(l) + _dfs(r)

    return _dfs(root)


def _dendrogram_svg(
    linkage:   list[tuple],
    n_leaves:  int,
    leaf_order: list[int],
    orient:    str,    # "left" or "top"
    x0: float, y0: float,
    plot_w: float, plot_h: float,
    color: str = "#555",
    line_width: float = 1.2,
) -> str:
    """
    Render a dendrogram as SVG polylines.

    ``orient="top"`` draws the tree growing downward (column dendrogram).
    ``orient="left"`` draws the tree growing rightward (row dendrogram).
    """
    n         = n_leaves
    pos_map   = {leaf: i for i, leaf in enumerate(leaf_order)}
    max_height = max(d for _, _, d, _ in linkage) if linkage else 1.0
    cluster_pos: dict[int, float] = {i: i + 0.5 for i in range(n)}

    elements: list[str] = []

    def _leaf_px(leaf: int) -> float:
        """Pixel position of a leaf along the axis."""
        rank = pos_map.get(leaf, leaf)
        if orient == "top":
            return x0 + (rank / n) * plot_w
        else:
            return y0 + (rank / n) * plot_h

    def _height_px(height: float) -> float:
        """Pixel position for a given linkage height."""
        norm = height / max_height if max_height > 0 else 0
        if orient == "top":
            return y0 + norm * plot_h
        else:
            return x0 + norm * plot_w

    current_id = n
    for left, right, height, _ in linkage:
        h_px = _height_px(height)

        lp = cluster_pos.get(left,  left  if left  < n else left)
        rp = cluster_pos.get(right, right if right < n else right)

        lx = _leaf_px(lp) if left  < n else cluster_pos.get(left,  0)
        rx = _leaf_px(rp) if right < n else cluster_pos.get(right, 0)

        # Recalculate using leaf positions correctly
        def _node_px(node_id: int) -> float:
            if node_id < n:
                return _leaf_px(node_id)
            return cluster_pos.get(node_id, 0)

        lp_px = _node_px(left)
        rp_px = _node_px(right)
        mid   = (lp_px + rp_px) / 2

        if orient == "top":
            # Horizontal segments at height h_px, vertical connectors
            lh_px = cluster_pos.get(left + 10000, y0)   # previous height
            rh_px = cluster_pos.get(right + 10000, y0)
            elements.append(
                f'<polyline points="{lp_px:.1f},{lh_px:.1f} '
                f'{lp_px:.1f},{h_px:.1f} '
                f'{rp_px:.1f},{h_px:.1f} '
                f'{rp_px:.1f},{rh_px:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{line_width}"/>'
            )
            cluster_pos[current_id]           = mid
            cluster_pos[current_id + 10000]   = h_px
        else:
            # orient = "left"
            lh_px = cluster_pos.get(left  + 10000, x0)
            rh_px = cluster_pos.get(right + 10000, x0)
            elements.append(
                f'<polyline points="{lh_px:.1f},{lp_px:.1f} '
                f'{h_px:.1f},{lp_px:.1f} '
                f'{h_px:.1f},{rp_px:.1f} '
                f'{rh_px:.1f},{rp_px:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{line_width}"/>'
            )
            cluster_pos[current_id]           = mid
            cluster_pos[current_id + 10000]   = h_px

        current_id += 1

    return "\n".join(elements)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clustermap(
    data,
    row_labels:   list[str] | None = None,
    col_labels:   list[str] | None = None,
    cmap:         str               = "viridis",
    row_cluster:  bool              = True,
    col_cluster:  bool              = True,
    standard_scale: str | None      = None,  # "row", "col", or None
    z_score:      str | None        = None,  # "row", "col", or None
    show_values:  bool              = False,
    figsize:      tuple[int,int]    = (720, 640),
    title:        str               = "",
    dendrogram_ratio: float         = 0.15,
    line_color:   str               = "#555",
    theme:        str               = "default",
) -> Figure:
    """
    Hierarchically clustered heatmap with row and column dendrograms.

    Equivalent to ``seaborn.clustermap()`` but implemented in pure NumPy --
    no scipy, no matplotlib required.

    Args:
        data:             2-D numeric array or pandas DataFrame.
        row_labels:       Labels for rows (inferred from DataFrame index if None).
        col_labels:       Labels for columns (inferred from DataFrame columns if None).
        cmap:             Colormap name (default ``"viridis"``).
        row_cluster:      Cluster and reorder rows (default True).
        col_cluster:      Cluster and reorder columns (default True).
        standard_scale:   ``"row"`` or ``"col"`` -- scale each row/column to [0,1].
        z_score:          ``"row"`` or ``"col"`` -- z-score normalise each row/column.
        show_values:      Overlay the numeric value in each cell.
        figsize:          ``(width, height)`` in pixels.
        title:            Chart title.
        dendrogram_ratio: Fraction of figure width/height used by dendrograms.
        line_color:       Dendrogram line colour.
        theme:            GlyphX theme name.

    Returns:
        :class:`~glyphx.Figure` containing the clustered heatmap and
        dendrograms rendered as SVG.

    Example::

        import pandas as pd
        from glyphx.clustermap import clustermap

        df = pd.read_csv("gene_expression.csv", index_col=0)
        fig = clustermap(df, cmap="coolwarm", z_score="row",
                         title="Gene Expression Heatmap")
        fig.show()
        fig.save("clustermap.html")
    """
    import pandas as pd

    # Coerce to numpy
    if isinstance(data, pd.DataFrame):
        if row_labels is None:
            row_labels = [str(i) for i in data.index]
        if col_labels is None:
            col_labels = [str(c) for c in data.columns]
        mat = data.values.astype(float)
    else:
        mat = np.asarray(data, dtype=float)

    n_rows, n_cols = mat.shape
    if row_labels is None:
        row_labels = [str(i) for i in range(n_rows)]
    if col_labels is None:
        col_labels = [str(j) for j in range(n_cols)]

    # Preprocessing
    if z_score == "row":
        mu  = mat.mean(axis=1, keepdims=True)
        sig = mat.std(axis=1, keepdims=True) + 1e-10
        mat = (mat - mu) / sig
    elif z_score == "col":
        mu  = mat.mean(axis=0, keepdims=True)
        sig = mat.std(axis=0, keepdims=True) + 1e-10
        mat = (mat - mu) / sig

    if standard_scale == "row":
        lo = mat.min(axis=1, keepdims=True)
        hi = mat.max(axis=1, keepdims=True) + 1e-10
        mat = (mat - lo) / (hi - lo)
    elif standard_scale == "col":
        lo = mat.min(axis=0, keepdims=True)
        hi = mat.max(axis=0, keepdims=True) + 1e-10
        mat = (mat - lo) / (hi - lo)

    # Clustering
    row_order = list(range(n_rows))
    col_order = list(range(n_cols))
    row_linkage: list = []
    col_linkage: list = []

    if row_cluster and n_rows > 1:
        D           = _pdist(mat)
        row_linkage = _average_linkage(D)
        row_order   = _leaf_order(row_linkage, n_rows)

    if col_cluster and n_cols > 1:
        D           = _pdist(mat.T)
        col_linkage = _average_linkage(D)
        col_order   = _leaf_order(col_linkage, n_cols)

    # Reorder matrix and labels
    mat_r      = mat[np.ix_(row_order, col_order)]
    row_lbl_r  = [row_labels[i] for i in row_order]
    col_lbl_r  = [col_labels[j] for j in col_order]

    # Build figure as raw SVG (Figure wraps it as axis-free)
    W, H       = figsize
    dend_w     = int(W * dendrogram_ratio)  # row dendrogram width (left)
    dend_h     = int(H * dendrogram_ratio)  # col dendrogram height (top)
    title_h    = 32 if title else 0
    label_w    = max(max(len(l) for l in row_lbl_r) * 6, 60)
    label_h    = max(max(len(l) for l in col_lbl_r) * 6, 40)
    colorbar_w = 18

    heat_x = dend_w + label_w
    heat_y = title_h + dend_h
    heat_w = W - heat_x - colorbar_w - 8
    heat_h = H - heat_y - label_h

    cell_w = heat_w / n_cols
    cell_h = heat_h / n_rows

    vmin, vmax = float(mat_r.min()), float(mat_r.max())
    span = vmax - vmin or 1.0

    from .themes import themes as _themes
    theme_dict = _themes.get(theme, _themes["default"])
    bg   = theme_dict.get("background", "#fff")
    tc   = theme_dict.get("text_color",  "#000")
    font = theme_dict.get("font", "sans-serif")

    parts: list[str] = [
        f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{bg}"/>',
    ]

    # Title
    if title:
        parts.append(
            f'<text x="{W//2}" y="22" text-anchor="middle" '
            f'font-size="15" font-weight="bold" '
            f'font-family="{font}" fill="{tc}">{svg_escape(title)}</text>'
        )

    # -- Heatmap cells -------------------------------------------------
    for ri in range(n_rows):
        for ci in range(n_cols):
            v    = float(mat_r[ri, ci])
            norm = (v - vmin) / span
            col  = apply_colormap(norm, cmap)
            cx   = heat_x + ci * cell_w
            cy   = heat_y + ri * cell_h
            parts.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" '
                f'width="{cell_w:.1f}" height="{cell_h:.1f}" '
                f'fill="{col}" '
                f'data-row="{svg_escape(row_lbl_r[ri])}" '
                f'data-col="{svg_escape(col_lbl_r[ci])}" '
                f'data-value="{v:.3g}"/>'
            )
            if show_values and cell_w > 24 and cell_h > 14:
                txt_col = "#fff" if norm < 0.6 else "#000"
                parts.append(
                    f'<text x="{cx + cell_w/2:.1f}" y="{cy + cell_h/2 + 4:.1f}" '
                    f'text-anchor="middle" font-size="9" '
                    f'font-family="{font}" fill="{txt_col}">'
                    f'{_format_tick(v)}</text>'
                )

    # -- Row labels (right side of row dendrogram, left of heatmap) ---
    for ri, lbl in enumerate(row_lbl_r):
        cy = heat_y + ri * cell_h + cell_h / 2
        parts.append(
            f'<text x="{heat_x - 4:.1f}" y="{cy + 4:.1f}" '
            f'text-anchor="end" font-size="10" '
            f'font-family="{font}" fill="{tc}">{svg_escape(lbl)}</text>'
        )

    # -- Column labels (below heatmap) --------------------------------
    for ci, lbl in enumerate(col_lbl_r):
        cx = heat_x + ci * cell_w + cell_w / 2
        cy = heat_y + heat_h + 4
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" '
            f'text-anchor="start" font-size="10" '
            f'font-family="{font}" fill="{tc}" '
            f'transform="rotate(45,{cx:.1f},{cy:.1f})">'
            f'{svg_escape(lbl)}</text>'
        )

    # -- Row dendrogram (left panel, growing rightward) ---------------
    if row_cluster and row_linkage:
        parts.append(_dendrogram_svg(
            row_linkage, n_rows, list(range(n_rows)),
            orient="left",
            x0=dend_w * 0.05, y0=heat_y,
            plot_w=dend_w * 0.90, plot_h=heat_h,
            color=line_color,
        ))

    # -- Column dendrogram (top panel, growing downward) --------------
    if col_cluster and col_linkage:
        parts.append(_dendrogram_svg(
            col_linkage, n_cols, list(range(n_cols)),
            orient="top",
            x0=heat_x, y0=title_h + dend_h * 0.05,
            plot_w=heat_w, plot_h=dend_h * 0.90,
            color=line_color,
        ))

    # -- Colorbar -----------------------------------------------------
    cb_x  = heat_x + heat_w + 6
    cb_y  = heat_y
    n_steps = 50
    step_h  = heat_h / n_steps
    for k in range(n_steps):
        norm = 1 - k / n_steps
        col  = apply_colormap(norm, cmap)
        parts.append(
            f'<rect x="{cb_x}" y="{cb_y + k * step_h:.1f}" '
            f'width="{colorbar_w - 2}" height="{step_h + 0.5:.1f}" '
            f'fill="{col}"/>'
        )
    parts.append(
        f'<text x="{cb_x + colorbar_w}" y="{cb_y + 10}" '
        f'font-size="9" font-family="{font}" fill="{tc}">'
        f'{_format_tick(vmax)}</text>'
    )
    parts.append(
        f'<text x="{cb_x + colorbar_w}" y="{cb_y + heat_h}" '
        f'font-size="9" font-family="{font}" fill="{tc}">'
        f'{_format_tick(vmin)}</text>'
    )

    parts.append("</svg>")

    # Wrap in an axis-free Figure
    fig = Figure(width=W, height=H, auto_display=False, theme=theme)
    fig.title = ""   # already in SVG

    # Inject raw SVG via a custom series stub
    class _RawSVG:
        x = None; y = None; label = None; color = "#000"
        css_class = "clustermap"
        def to_svg(self, ax=None, use_y2=False): return "\n".join(parts[2:-1])

    fig._raw_svg = "\n".join(parts)
    fig._clustermap = True
    # Override render_svg to return our pre-built SVG
    _orig_render = fig.render_svg
    def _render_patched():
        return fig._raw_svg
    import types
    fig.render_svg = types.MethodType(lambda self: self._raw_svg, fig)

    return fig
