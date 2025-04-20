import numpy as np
from collections import defaultdict

class SwarmPlotSeries:
    def __init__(self, data, categories=None, color="#1f77b4", size=4, jitter=6):
        self.data = data  # List of lists: one per category
        self.categories = categories or list(range(len(data)))
        self.color = color
        self.size = size
        self.jitter = jitter

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        scale_x = ax.scale_x
        elements = []

        for i, values in enumerate(self.data):
            y_buckets = defaultdict(list)
            for v in values:
                y = scale_y(v)
                y_buckets[y].append(v)

            for y_scaled, vlist in y_buckets.items():
                count = len(vlist)
                for j, v in enumerate(vlist):
                    offset = (j - count // 2) * self.jitter
                    cx = scale_x(i) + offset
                    cy = scale_y(v)
                    elements.append(f'<circle cx="{cx}" cy="{cy}" r="{self.size}" fill="{self.color}"/>')

        return "\n".join(elements)