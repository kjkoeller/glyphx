"""
GlyphX FacetGrid — small-multiples grid of the same chart type, faceted
by a categorical column.

Matches the Seaborn ``FacetGrid.map()`` API:

    from glyphx.facet_grid import FacetGrid

    g = FacetGrid(df, col="species", hue="sex", height=300, aspect=1.2)
    g.map("scatter", x="bill_length", y="bill_depth")
    g.show()

Each cell is a full GlyphX Figure rendered at ``height × aspect`` pixels.
The grid wraps into multiple rows when ``col_wrap`` is set.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .figure  import Figure
from .themes  import themes as _themes
from .colormaps import colormap_colors
from .utils   import svg_escape


class FacetGrid:
    """
    Small-multiples grid.

    Args:
        data:       Source DataFrame.
        col:        Column name to facet along the X axis.
        row:        Column name to facet along the Y axis (optional).
        hue:        Column name for color-coding within each cell (optional).
        height:     Pixel height of each cell.
        aspect:     Width/height ratio of each cell.
        col_wrap:   Wrap into a new row after this many columns.
        theme:      GlyphX theme name.
        sharex:     Share X-axis scale across all cells.
        sharey:     Share Y-axis scale across all cells.
        col_order:  Explicit ordering of column facets.
        row_order:  Explicit ordering of row facets.
        hue_order:  Explicit ordering of hue groups.
        palette:    Color palette for hue groups (list of hex strings).
    """

    def __init__(
        self,
        data,
        col:       str | None     = None,
        row:       str | None     = None,
        hue:       str | None     = None,
        height:    int            = 300,
        aspect:    float          = 1.4,
        col_wrap:  int | None     = None,
        theme:     str            = "default",
        sharex:    bool           = True,
        sharey:    bool           = True,
        col_order: list | None    = None,
        row_order: list | None    = None,
        hue_order: list | None    = None,
        palette:   list | None    = None,
    ) -> None:
        self._df        = data
        self._col       = col
        self._row       = row
        self._hue       = hue
        self._height    = height
        self._width     = int(height * aspect)
        self._col_wrap  = col_wrap
        self._theme     = theme
        self._sharex    = sharex
        self._sharey    = sharey
        self._figs:     list[tuple[Figure, str, str]] = []
        self._map_kind: str | None = None

        # Facet values
        self._col_vals = (col_order
                          if col_order
                          else list(data[col].unique()) if col else [None])
        self._row_vals = (row_order
                          if row_order
                          else list(data[row].unique()) if row else [None])
        self._hue_vals = (hue_order
                          if hue_order
                          else list(data[hue].unique()) if hue else [None])

        # Palette
        n_hue = len(self._hue_vals) if hue else 1
        self._palette = palette or colormap_colors("viridis", max(n_hue, 2))

    # ------------------------------------------------------------------
    def map(
        self,
        kind:    str,
        x:       str | None = None,
        y:       str | None = None,
        **kwargs,
    ) -> "FacetGrid":
        """
        Apply a chart type to each facet cell.

        Args:
            kind:    Chart kind (``"scatter"``, ``"line"``, ``"bar"``,
                     ``"hist"``, ``"kde"``, ``"box"``, ``"violin"``).
            x:       X-axis column name.
            y:       Y-axis column name (not needed for ``"hist"``/``"kde"``).
            **kwargs: Passed to the series constructor.

        Returns:
            ``self`` for chaining.

        Example::

            g = FacetGrid(df, col="species", hue="island")
            g.map("scatter", x="bill_length", y="flipper_length")
            g.map("hist", x="body_mass")
        """
        from .series       import (LineSeries, BarSeries, ScatterSeries,
                                   HistogramSeries, BoxPlotSeries)
        from .kde          import KDESeries
        from .violin_plot  import ViolinPlotSeries

        self._map_kind = kind
        self._figs = []

        theme_dict = _themes.get(self._theme, _themes["default"])

        for r_val in self._row_vals:
            for c_val in self._col_vals:
                # Build cell title
                parts = []
                if c_val is not None: parts.append(f"{self._col}={c_val}")
                if r_val is not None: parts.append(f"{self._row}={r_val}")
                cell_title = " | ".join(parts)

                fig = Figure(width=self._width, height=self._height,
                             auto_display=False, theme=self._theme)
                fig.set_title(cell_title)

                for hi, h_val in enumerate(self._hue_vals):
                    # Subset the data
                    sub = self._df.copy()
                    if c_val is not None:
                        sub = sub[sub[self._col] == c_val]
                    if r_val is not None:
                        sub = sub[sub[self._row] == r_val]
                    if h_val is not None and self._hue:
                        sub = sub[sub[self._hue] == h_val]

                    if sub.empty:
                        continue

                    color = self._palette[hi % len(self._palette)]
                    label = str(h_val) if h_val is not None else None

                    series = None
                    if kind == "scatter" and x and y:
                        series = ScatterSeries(
                            sub[x].tolist(), sub[y].tolist(),
                            color=color, label=label, **kwargs
                        )
                    elif kind == "line" and x and y:
                        series = LineSeries(
                            sub[x].tolist(), sub[y].tolist(),
                            color=color, label=label, **kwargs
                        )
                    elif kind == "bar" and x and y:
                        series = BarSeries(
                            sub[x].tolist(), sub[y].tolist(),
                            color=color, label=label, **kwargs
                        )
                    elif kind == "hist" and x:
                        series = HistogramSeries(
                            sub[x].dropna().tolist(),
                            color=color, label=label, **kwargs
                        )
                    elif kind == "kde" and x:
                        series = KDESeries(
                            sub[x].dropna().tolist(),
                            color=color, label=label, **kwargs
                        )
                    elif kind in ("box", "violin") and y:
                        grp_data = [sub[y].dropna().tolist()]
                        if kind == "box":
                            series = BoxPlotSeries(
                                grp_data, color=color, label=label, **kwargs
                            )
                        else:
                            series = ViolinPlotSeries(
                                grp_data, color=color, label=label, **kwargs
                            )

                    if series is not None:
                        fig.add(series)

                if x: fig.set_xlabel(x)
                if y: fig.set_ylabel(y)
                self._figs.append((fig, str(r_val), str(c_val)))

        return self

    # ------------------------------------------------------------------
    def render_svg(self) -> str:
        """Composite all cell figures into a single SVG grid."""
        if not self._figs:
            return '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

        n_total = len(self._figs)
        n_cols  = (self._col_wrap or len(self._col_vals)) or 1
        n_rows  = math.ceil(n_total / n_cols)

        gap       = 16
        title_h   = 40
        cell_w    = self._width
        cell_h    = self._height
        total_w   = n_cols * cell_w + (n_cols + 1) * gap
        total_h   = n_rows * cell_h + (n_rows + 1) * gap + title_h

        theme_dict = _themes.get(self._theme, _themes["default"])
        bg   = theme_dict.get("background", "#fff")
        tc   = theme_dict.get("text_color",  "#000")
        font = theme_dict.get("font", "sans-serif")

        parts = [
            f'<svg width="{total_w}" height="{total_h}" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {total_w} {total_h}">',
            f'<rect width="{total_w}" height="{total_h}" fill="{bg}"/>',
        ]

        # Hue legend at top right
        if self._hue and self._hue_vals[0] is not None:
            lx = total_w - 120
            ly = 8
            for hi, hv in enumerate(self._hue_vals):
                col = self._palette[hi % len(self._palette)]
                parts.append(
                    f'<rect x="{lx}" y="{ly + hi*16}" width="10" height="10" fill="{col}"/>'
                )
                parts.append(
                    f'<text x="{lx+14}" y="{ly + hi*16 + 9}" '
                    f'font-size="10" font-family="{font}" fill="{tc}">'
                    f'{svg_escape(str(hv))}</text>'
                )

        for idx, (fig, r_val, c_val) in enumerate(self._figs):
            row_i = idx // n_cols
            col_i = idx % n_cols
            tx = gap + col_i * (cell_w + gap)
            ty = title_h + gap + row_i * (cell_h + gap)

            inner_svg = fig.render_svg()
            # Extract inner content from the <svg> root
            import re
            body_match = re.search(r'<svg[^>]*>(.*)</svg>', inner_svg, re.DOTALL)
            if body_match:
                inner = body_match.group(1)
            else:
                inner = inner_svg

            parts.append(
                f'<g transform="translate({tx},{ty})">'
                f'<rect width="{cell_w}" height="{cell_h}" '
                f'fill="{bg}" rx="4" stroke="#eee" stroke-width="1"/>'
                + inner
                + '</g>'
            )

        parts.append("</svg>")
        return "\n".join(parts)

    def show(self) -> "FacetGrid":
        """Display in Jupyter or open in browser."""
        svg = self.render_svg()
        try:
            from IPython.display import SVG, display as jd
            jd(SVG(svg)); return self
        except Exception:
            pass
        import tempfile, webbrowser
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".svg", mode="w")
        tmp.write(svg); tmp.close()
        webbrowser.open(f"file://{tmp.name}")
        return self

    def save(self, path: str) -> "FacetGrid":
        """Save the composite SVG to a file."""
        from pathlib import Path
        Path(path).write_text(self.render_svg(), encoding="utf-8")
        return self

    def __repr__(self) -> str:
        return (f"<FacetGrid col={self._col!r} row={self._row!r} "
                f"hue={self._hue!r} cells={len(self._figs)}>")
