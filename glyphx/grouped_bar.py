from .series import BaseSeries

class GroupedBarSeries(BaseSeries):
    def __init__(self, groups, categories, values, group_colors=None, bar_width=0.8):
        self.groups = groups
        self.categories = categories
        self.values = values  # 2D list: [group][category]
        self.group_colors = group_colors or ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
        self.bar_width = bar_width

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        num_groups = len(self.groups)
        num_cats = len(self.categories)
        group_width = self.bar_width
        total_width = group_width * num_cats
        step = total_width / num_cats
        elements = []
        for i, group in enumerate(self.groups):
            base_x = ax.scale_x(i + 1)
            for j, category in enumerate(self.categories):
                val = self.values[i][j]
                cx = base_x - total_width / 2 + j * step + step / 2
                cy = scale_y(val)
                y0 = scale_y(0)
                h = abs(y0 - cy)
                top = min(y0, cy)
                fill = self.group_colors[j % len(self.group_colors)]
                elements.append(f'<rect x="{cx - step/2}" y="{top}" width="{step}" height="{h}" fill="{fill}" stroke="#000"/>')
        return "\n".join(elements)