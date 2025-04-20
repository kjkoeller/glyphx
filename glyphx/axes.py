class Axes:
    def __init__(self, width=400, height=300, padding=40,
                 xlim=None, ylim=None, y2lim=None, xlabel="", ylabel="", title=""):
        self.width = width
        self.height = height
        self.padding = padding
        self.xlim = xlim
        self.ylim = ylim
        self.y2lim = y2lim
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title

    def render_labels(self, svg):
        if self.title:
            svg.append(f'<text x="{self.width/2}" y="20" text-anchor="middle" font-size="16" font-weight="bold">{self.title}</text>')
        if self.xlabel:
            svg.append(f'<text x="{self.width/2}" y="{self.height - 5}" text-anchor="middle" font-size="12">{self.xlabel}</text>')
        if self.ylabel:
            svg.append(f'<text x="15" y="{self.height/2}" text-anchor="middle" font-size="12" transform="rotate(-90 15,{self.height/2})">{self.ylabel}</text>')

    def scale_x(self, x):
        min_x = self.xlim[0] if self.xlim else min(self._xdata)
        max_x = self.xlim[1] if self.xlim else max(self._xdata)
        return self.padding + (x - min_x) / (max_x - min_x) * (self.width - 2 * self.padding)

    def scale_y(self, y):
        min_y = self.ylim[0] if self.ylim else min(self._ydata)
        max_y = self.ylim[1] if self.ylim else max(self._ydata)
        return self.height - self.padding - (y - min_y) / (max_y - min_y) * (self.height - 2 * self.padding)