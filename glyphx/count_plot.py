from collections import Counter

class CountPlotSeries:
    def __init__(self, data, order=None, color="#1f77b4", bar_width=0.8):
        self.data = data
        self.order = order or sorted(set(data))
        self.color = color
        self.bar_width = bar_width

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        cx = ax.scale_x
        counts = Counter(self.data)
        elements = []
        n = len(self.order)
        width_px = (ax.width - 2 * ax.padding) * self.bar_width / n

        for i, cat in enumerate(self.order):
            count = counts[cat]
            x_pos = cx(i + 1)
            y = scale_y(count)
            y0 = scale_y(0)
            h = abs(y0 - y)
            top = min(y0, y)
            elements.append(f'<rect x="{x_pos - width_px/2}" y="{top}" width="{width_px}" height="{h}" fill="{self.color}" stroke="#000"/>')

        return "\n".join(elements)