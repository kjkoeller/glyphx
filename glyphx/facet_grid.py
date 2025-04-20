import pandas as pd
from .figure import Figure
from .plot import plot

class FacetGrid:
    def __init__(self, df, row=None, col=None, hue=None, kind="line", theme="default", sharex=True, sharey=True):
        self.df = df
        self.row = row
        self.col = col
        self.hue = hue
        self.kind = kind
        self.theme = theme
        self.sharex = sharex
        self.sharey = sharey
        self.subplots = []

        self.row_vals = df[row].unique().tolist() if row else [None]
        self.col_vals = df[col].unique().tolist() if col else [None]


        # compute global axis limits if sharing
        global_xlim = (df.iloc[:, 0].min(), df.iloc[:, 0].max()) if sharex else None
        global_ylim = (df.iloc[:, -1].min(), df.iloc[:, -1].max()) if sharey else None

        for r in self.row_vals:
            row_plots = []
            for c in self.col_vals:
                subset = df.copy()
                if row:
                    subset = subset[subset[row] == r]
                if col:
                    subset = subset[subset[col] == c]

                fig = plot(subset, x=None, y=None, kind=kind, theme=theme, hue=hue)
                if self.sharex: fig.axes[0].xlim = global_xlim
                if self.sharey: fig.axes[0].ylim = global_ylim
                row_plots.append((fig, r, c))
            self.subplots.append(row_plots)

    def to_svg(self):
        parts = ['<svg width="1200" height="800" xmlns="http://www.w3.org/2000/svg">']
        offset_x = 0
        offset_y = 0
        w = 400
        h = 300

        for i, row in enumerate(self.subplots):
            for j, (fig, r_val, c_val) in enumerate(row):
                x_shift = j * w
                y_shift = i * h
                svg = fig.to_svg().replace('<svg', f'<g transform="translate({x_shift},{y_shift})"').replace('</svg>', '</g>')
                parts.append(svg)
        parts.append('</svg>')
        return "\n".join(parts)

    def _repr_svg_(self):
        return self.to_svg()