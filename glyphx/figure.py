class Figure:
    def __init__(self, series=None, width=400, height=300, title=None):
        self.series = series or []
        self.width = width
        self.height = height
        self.title = title
        self.xlabel = ""
        self.ylabel = ""
        self._auto_display = True

    def add(self, series):
        self.series.append(series)

    def to_svg(self, viewbox=True):
        from .axes import Axes
        ax = Axes(self.width, self.height, xlabel=self.xlabel, ylabel=self.ylabel, title=self.title)

        # Inject data for scaling
        xvals, yvals = [], []
        for s in self.series:
            if hasattr(s, "x"): xvals.extend(s.x)
            if hasattr(s, "y") and s.y is not None: yvals.extend(s.y)
        ax._xdata, ax._ydata = xvals, yvals

        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}"']
        if viewbox:
            svg.append(f' viewBox="0 0 {self.width} {self.height}">')
        else:
            svg.append(">")
        svg.append('<rect width="100%" height="100%" fill="white"/>')
        ax.render_labels(svg)
        for s in self.series:
            svg.append(s.to_svg(ax))
        svg.append("</svg>")
        return "\n".join(svg)

    def save(self, filename):
        ext = filename.split(".")[-1]
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.to_svg())
        print(f"[glyphx] Saved: {filename}")