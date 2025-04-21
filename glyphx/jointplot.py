from .figure import Figure
from .layout import Axes
from .series import ScatterSeries, LineSeries, HistogramSeries
import numpy as np
from scipy.stats import gaussian_kde

def jointplot(df, x, y, kind="scatter", marginal="hist", theme="default", hue=None):
    fig = Figure(width=600, height=600, theme=theme)


    color_map = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    categories = df[hue].unique().tolist() if hue else [None]

    for i, cat in enumerate(categories):
        sub_df = df if cat is None else df[df[hue] == cat]
        c = color_map[i % len(color_map)]

        # Joint plot (scatter)
        if kind == "scatter":
            ax_main.add(ScatterSeries(sub_df[x], sub_df[y], color=c, label=str(cat)))
        
        # Marginal X
        if marginal == "hist":
            ax_top.add(HistogramSeries(sub_df[x], color=c))
        elif marginal == "kde":
            x_vals = sub_df[x].dropna()
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(x_vals)
            x_range = np.linspace(x_vals.min(), x_vals.max(), 100)
            y_vals = kde(x_range)
            ax_top.add(LineSeries(x_range, y_vals, color=c))

        # Marginal Y
        if marginal == "hist":
            ax_right.add(HistogramSeries(sub_df[y], color=c))
        elif marginal == "kde":
            y_vals = sub_df[y].dropna()
            kde = gaussian_kde(y_vals)
            x_range = np.linspace(y_vals.min(), y_vals.max(), 100)
            y_vals = kde(x_range)
            ax_right.add(LineSeries(x_range, y_vals, color=c))


    ax_main = fig.add_axes()
    if kind == "scatter":
        ax_main.add(ScatterSeries(df[x], df[y], color="#1f77b4"))
    elif kind == "kde":
        pass
    elif kind == "hexbin":
        import matplotlib.pyplot as plt
        import io
        buf = io.BytesIO()
        plt.hexbin(df[x], df[y], gridsize=20, cmap="Blues")
        plt.savefig(buf, format="svg")
        buf.seek(0)
        fig_hex = buf.read().decode("utf-8").split("<svg")[1].split("</svg>")[0]
        ax_main.to_svg = lambda ax=None: "<svg " + fig_hex + "</svg>"

        pass

    # Top marginal plot (x-axis)
    ax_top = fig.add_axes()
    if marginal == "hist":
        ax_top.add(HistogramSeries(df[x], color="#1f77b4"))
    elif marginal == "kde":
        x_vals = df[x].dropna()
        kde = gaussian_kde(x_vals)
        x_range = np.linspace(x_vals.min(), x_vals.max(), 100)
        y_vals = kde(x_range)
        ax_top.add(LineSeries(x_range, y_vals, color="#1f77b4"))

    # Right marginal plot (y-axis)
    ax_right = fig.add_axes()
    if marginal == "hist":
        ax_right.add(HistogramSeries(df[y], color="#1f77b4"))
    elif marginal == "kde":
        y_vals = df[y].dropna()
        kde = gaussian_kde(y_vals)
        x_range = np.linspace(y_vals.min(), y_vals.max(), 100)
        y_vals = kde(x_range)
        ax_right.add(LineSeries(x_range, y_vals, color="#1f77b4"))

    return fig

    # Layout arrangement into one SVG
    def to_svg():
        main_svg = ax_main.to_svg()
        top_svg = ax_top.to_svg()
        right_svg = ax_right.to_svg()

        svg = [
            '<svg width="700" height="700" xmlns="http://www.w3.org/2000/svg">',
            '<g transform="translate(100, 100)">', main_svg, '</g>',
            '<g transform="translate(100, 0)">', top_svg, '</g>',
            '<g transform="translate(500, 100)">', right_svg, '</g>',
            '</svg>'
        ]
        return "\n".join(svg)

    fig.to_svg = to_svg
    return fig

    if hue:
        legend_items = []
        for i, cat in enumerate(categories):
            c = color_map[i % len(color_map)]
            x = fig.width - 160
            y = fig.height - 40 - i * 20
            legend_items.append(f'<rect x="{x}" y="{y}" width="12" height="12" fill="{c}"/>')
            legend_items.append(f'<text x="{x + 20}" y="{y + 10}" font-size="12" fill="#000">{cat}</text>')

        def inject_legend(svg):
            parts = svg.split("</svg>")
            parts.insert(-1, "\n".join(legend_items))
            return "</svg>".join(parts)

        fig.to_svg = lambda: inject_legend(to_svg())
    else:
        fig.to_svg = to_svg
