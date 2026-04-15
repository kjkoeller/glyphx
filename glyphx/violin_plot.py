"""
GlyphX ViolinPlotSeries — replaces scipy gaussian_kde with a pure-numpy implementation.
"""

import numpy as np


def _numpy_kde(data, bandwidth=None):
    """
    Gaussian KDE using NumPy only (no scipy required).

    Args:
        data (np.ndarray): 1-D input array.
        bandwidth (float | None): Scott's rule applied if None.

    Returns:
        callable: f(y_vals) → density array.
    """
    n  = len(data)
    h  = bandwidth or (n ** -0.2) * data.std(ddof=1)
    if h == 0:
        h = 1e-6

    def kde(y_vals):
        y  = np.asarray(y_vals)
        z  = (y[:, None] - data[None, :]) / h
        return np.exp(-0.5 * z ** 2).mean(axis=1) / (h * np.sqrt(2 * np.pi))

    return kde


class ViolinPlotSeries:
    """
    Violin plot: a KDE-smoothed distribution mirrored on both sides of a centre line.

    Requires no external dependencies beyond NumPy.

    Args:
        data (list of array-like): One array per category.
        positions (list | None): X-axis positions for each violin.
        color (str): Fill/stroke color.
        width (int): Maximum pixel half-width of the violin body.
        show_median (bool): Draw a horizontal median marker.
        show_box (bool): Overlay a thin IQR box inside the violin.
        label (str | None): Legend label.
    """

    def __init__(self, data, positions=None, color="#1f77b4",
                 width=50, show_median=True, show_box=True, label=None,
                 hue=None, hue_colors=None, cmap="viridis", categories=None):
        self.data        = data
        self.positions   = positions or list(range(len(data)))
        self.color       = color
        self.hue         = hue
        self.hue_colors  = hue_colors
        self.cmap_name   = cmap
        self.categories  = categories
        self.width       = width
        self.show_median = show_median
        self.show_box    = show_box
        self.label       = label
        self.css_class   = f"series-{id(self) % 100000}"

        # Expose x/y for Axes domain computation
        self.x = self.positions
        all_vals = np.concatenate([np.asarray(d) for d in data])
        self.y   = [float(all_vals.min()), float(all_vals.max())]

    def to_svg(self, ax, use_y2=False):
        from glyphx.colormaps import colormap_colors
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y
        elements = []

        # Resolve hue colour mapping before the loop
        _hue_colors = self.hue_colors
        _hue_map    = None
        if self.hue is not None:
            _hue_vals   = list(dict.fromkeys(str(h) for h in self.hue))
            _hue_colors = _hue_colors or colormap_colors(
                getattr(self, "cmap_name", "viridis"), max(len(_hue_vals), 2)
            )
            _hue_map = dict(zip(_hue_vals, _hue_colors))

        for i, values in enumerate(self.data):
            # Per-violin colour
            if _hue_map is not None and self.hue is not None and i < len(self.hue):
                _vc = _hue_map.get(str(self.hue[i]), self.color)
            elif _hue_colors is not None:
                _vc = list(_hue_colors)[i % len(list(_hue_colors))]
            else:
                _vc = self.color
            arr = np.asarray(values, dtype=float)
            if len(arr) < 2:
                continue

            kde    = _numpy_kde(arr)
            y_vals = np.linspace(arr.min(), arr.max(), 100)
            dens   = kde(y_vals)
            max_d  = dens.max() or 1
            dens   = dens / max_d * (self.width / 2)

            cx = ax.scale_x(self.positions[i])

            # Build mirrored violin path
            right_pts = [(cx + d, scale_y(y)) for y, d in zip(y_vals, dens)]
            left_pts  = [(cx - d, scale_y(y)) for y, d in reversed(list(zip(y_vals, dens)))]
            all_pts   = right_pts + left_pts

            path = "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in all_pts) + " Z"
            elements.append(
                f'<path d="{path}" fill="{_vc}" fill-opacity="0.4" '
                f'stroke="{_vc}" stroke-width="1" class="{self.css_class}"/>'
            )

            if self.show_box:
                q1  = float(np.percentile(arr, 25))
                q3  = float(np.percentile(arr, 75))
                top = min(scale_y(q1), scale_y(q3))
                h   = abs(scale_y(q3) - scale_y(q1))
                elements.append(
                    f'<rect x="{cx - 5}" y="{top}" width="10" height="{h}" '
                    f'fill="{_vc}" fill-opacity="0.5"/>'
                )

            if self.show_median:
                med = float(np.median(arr))
                elements.append(
                    f'<line x1="{cx - 7}" x2="{cx + 7}" '
                    f'y1="{scale_y(med)}" y2="{scale_y(med)}" '
                    f'stroke="{_vc}" stroke-width="2.5"/>'
                )

        return "\n".join(elements)
