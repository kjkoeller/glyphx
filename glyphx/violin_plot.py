import numpy as np
from scipy.stats import gaussian_kde

class ViolinPlotSeries:
    def __init__(self, data, positions=None, color="#1f77b4", width=50, show_median=True, show_box=True):
        self.data = data  # list of arrays, one per category
        self.positions = positions or list(range(len(data)))
        self.color = color
        self.width = width
        self.show_median = show_median
        self.show_box = show_box

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        center = ax.scale_x
        elements = []

        for i, values in enumerate(self.data):
            if len(values) < 2:
                continue
            kde = gaussian_kde(values)
            y_vals = np.linspace(min(values), max(values), 100)
            densities = kde(y_vals)
            densities = densities / densities.max() * (self.width / 2)

            path = ["M"]
            for y, d in zip(y_vals, densities):
                path.append(f"{center(self.positions[i]) + d},{scale_y(y)}")
            for y, d in zip(reversed(y_vals), reversed(densities)):
                path.append(f"{center(self.positions[i]) - d},{scale_y(y)}")
            path_str = " ".join(path) + " Z"
            elements.append(f'<path d="{path_str}" fill="{self.color}" fill-opacity="0.4" stroke="{self.color}" />')

            if self.show_box:
                q1 = np.percentile(values, 25)
                q3 = np.percentile(values, 75)
                h = abs(scale_y(q3) - scale_y(q1))
                top = min(scale_y(q3), scale_y(q1))
                elements.append(f'<rect x="{center(self.positions[i]) - 5}" y="{top}" width="10" height="{h}" fill="{self.color}" opacity="0.3"/>')

            if self.show_median:
                median = np.median(values)
                elements.append(f'<line x1="{center(self.positions[i]) - 5}" x2="{center(self.positions[i]) + 5}" y1="{scale_y(median)}" y2="{scale_y(median)}" stroke="{self.color}" stroke-width="2"/>')

        return "\n".join(elements)