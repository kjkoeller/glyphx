"""
generate_docs_figures.py
========================
Regenerates all SVG figures for the GlyphX documentation.

Usage (from repo root):
    python generate_docs_figures.py

Output: docs/examples/*.svg   (21 files, old PNGs can be deleted)
"""

import math
import numpy as np
from pathlib import Path

import glyphx
from glyphx import Figure
from glyphx.series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    HeatmapSeries, BoxPlotSeries,
)
from glyphx.ecdf        import ECDFSeries
from glyphx.raincloud   import RaincloudSeries
from glyphx.candlestick import CandlestickSeries
from glyphx.waterfall   import WaterfallSeries
from glyphx.treemap     import TreemapSeries
from glyphx.streaming   import StreamingSeries
from glyphx.colormaps   import colormap_colors
import pandas as pd

np.random.seed(42)

OUT = Path("docs/examples")
OUT.mkdir(parents=True, exist_ok=True)

W, H = 760, 460   # standard figure size


def save(fig, name):
    (OUT / f"{name}.svg").write_text(fig.render_svg())
    print(f"  {name}.svg")


months  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
revenue = [1.20,1.35,0.98,1.70,1.45,1.90,2.10,1.75,2.30,2.05,2.60,3.00]
costs   = [0.80,0.90,0.65,1.00,0.95,1.10,1.30,1.05,1.40,1.20,1.55,1.75]


# ─────────────────────────────────────────────────────────────────────────────
# BASIC CHARTS
# ─────────────────────────────────────────────────────────────────────────────
print("\nBasic charts")

# 1. Multi-series line with annotations
fig = (
    Figure(width=W, height=H, auto_display=False)
    .set_title("Monthly Revenue vs Operating Costs  (2024)")
    .set_xlabel("Month").set_ylabel("USD ($M)")
    .add(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=3))
    .add(LineSeries(months, costs,   color="#dc2626", label="Costs",   width=2, linestyle="dashed"))
    .set_legend("top-left")
    .annotate("Peak Revenue", x="Dec", y=3.00, arrow=True, color="#2563eb", font_size=11)
    .annotate("Q1 Dip",       x="Mar", y=0.98, arrow=True, color="#dc2626", font_size=11)
    .tight_layout()
)
save(fig, "Quick_Example")

# 2. Scatter + viridis colormap encoding
x = np.random.randn(200)
y = 0.65*x + np.random.randn(200)*0.6
z = np.sin(x*1.2) + np.cos(y*0.8) + np.random.randn(200)*0.2
save(
    Figure(width=W, height=H, auto_display=False)
    .set_title("Scatter with Continuous Colormap Encoding  (cmap='viridis')")
    .set_xlabel("Feature X").set_ylabel("Feature Y")
    .add(ScatterSeries(x.tolist(), y.tolist(), c=z.tolist(), cmap="viridis", size=7)),
    "basic_plotting",
)

# 3. Bimodal histogram
data = np.concatenate([np.random.normal(50,8,400), np.random.normal(78,6,200)])
save(
    Figure(width=W, height=H, auto_display=False)
    .set_title("Bimodal Histogram  —  HistogramSeries(bins=28)")
    .set_xlabel("Response Time (ms)").set_ylabel("Frequency")
    .add(HistogramSeries(data.tolist(), bins=28, color="#0891b2", label="Response Time")),
    "histogram",
)

# 4. Pie chart
fig = Figure(width=500, height=440, auto_display=False)
fig.set_title("Market Share 2024  —  PieSeries")
fig.add(PieSeries(
    [38, 25, 18, 11, 8],
    labels=["GlyphX","Matplotlib","Plotly","Seaborn","Other"],
    colors=colormap_colors("plasma", 5),
))
save(fig, "pie_chart")

# 5. Donut chart
fig = Figure(width=500, height=440, auto_display=False)
fig.set_title("Budget Allocation  —  DonutSeries")
fig.add(DonutSeries(
    [35, 25, 20, 12, 8],
    labels=["Engineering","Marketing","Sales","Operations","Legal"],
    colors=colormap_colors("viridis", 5),
))
save(fig, "donut_chart")

# 6. Heatmap — 5x5 correlation matrix
labels = ["Revenue","Traffic","Conv Rate","Bounce Rate","Avg Order"]
corr   = [
    [ 1.00,  0.82,  0.45, -0.37,  0.61],
    [ 0.82,  1.00,  0.58, -0.29,  0.44],
    [ 0.45,  0.58,  1.00, -0.12,  0.73],
    [-0.37, -0.29, -0.12,  1.00, -0.08],
    [ 0.61,  0.44,  0.73, -0.08,  1.00],
]
fig = Figure(width=680, height=520, auto_display=False)
fig.set_title("KPI Correlation Matrix  —  HeatmapSeries(show_values=True)")
fig.add(HeatmapSeries(
    corr, row_labels=labels, col_labels=labels,
    show_values=True,
    cmap=["#1e40af","#93c5fd","#f0f0f0","#fca5a5","#b91c1c"],
))
save(fig, "heatmap")

# 7. Multi-group box plot
groups = [np.random.normal(m,s,80) for m,s in [(50,10),(65,8),(55,15),(72,6),(60,11)]]
save(
    Figure(width=680, height=H, auto_display=False)
    .set_title("Multi-Group Box Plot  —  BoxPlotSeries")
    .set_ylabel("Test Score")
    .add(BoxPlotSeries(
        groups,
        categories=["Control","Drug A","Drug B","Drug C","Drug D"],
        color="#7c3aed", box_width=30,
    )),
    "box_plot",
)


# ─────────────────────────────────────────────────────────────────────────────
# THEMES
# ─────────────────────────────────────────────────────────────────────────────
print("Themes")

# 8. Dark theme
save(
    Figure(width=W, height=H, theme="dark", auto_display=False)
    .set_title("Dark Theme  —  Revenue vs Costs  (theme='dark')")
    .set_xlabel("Month").set_ylabel("USD ($M)")
    .add(LineSeries(months, revenue, color="#60a5fa", label="Revenue", width=3))
    .add(LineSeries(months, costs,   color="#f87171", label="Costs",   width=2, linestyle="dashed"))
    .set_legend("top-left")
    .tight_layout(),
    "dark_theme",
)

# 9. Colorblind-safe theme (Okabe-Ito)
save(
    Figure(width=W, height=H, theme="colorblind", auto_display=False)
    .set_title("Colorblind-Safe Theme  —  Okabe-Ito Palette  (theme='colorblind')")
    .set_xlabel("Month").set_ylabel("USD ($M)")
    .add(LineSeries(months, revenue, label="Revenue", width=2.5))
    .add(LineSeries(months, costs,   label="Costs",   width=2, linestyle="dashed"))
    .add(BarSeries(months, [r-c for r,c in zip(revenue,costs)], label="Margin", bar_width=0.4))
    .set_legend("top-left")
    .tight_layout(),
    "colorblind_theme",
)

# 10. All four linestyles
save(
    Figure(width=W, height=420, auto_display=False)
    .set_title("Line Styles  —  solid · dashed · dotted · longdash")
    .set_xlabel("Month").set_ylabel("Offset Value")
    .add(LineSeries(months, [v+0.20 for v in revenue], color="#16a34a", label="solid",    linestyle="solid",    width=2.5))
    .add(LineSeries(months, [v-0.20 for v in revenue], color="#2563eb", label="dashed",   linestyle="dashed",   width=2.5))
    .add(LineSeries(months, [v-0.60 for v in revenue], color="#dc2626", label="dotted",   linestyle="dotted",   width=2.5))
    .add(LineSeries(months, [v-1.00 for v in revenue], color="#d97706", label="longdash", linestyle="longdash", width=2.5))
    .set_legend("top-right")
    .tight_layout(),
    "green_dashed_line",
)

# 11. Plasma colormap scatter
x8 = np.random.randn(180)
y8 = 0.6*x8 + np.random.randn(180)*0.7
z8 = x8**2 + y8**2
save(
    Figure(width=W, height=H, auto_display=False)
    .set_title("Plasma Colormap  —  ScatterSeries(c=values, cmap='plasma')")
    .set_xlabel("X").set_ylabel("Y")
    .add(ScatterSeries(x8.tolist(), y8.tolist(), c=z8.tolist(), cmap="plasma", size=8)),
    "colormaps",
)


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
print("Layout")

# 12. 2x2 subplot grid
fig = Figure(rows=2, cols=2, width=800, height=580, auto_display=False)
fig.title = "2x2 Subplot Grid  —  Figure(rows=2, cols=2)"

ax1 = fig.add_axes(0, 0)
ax1.add_series(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=2))
ax1.add_series(LineSeries(months, costs,   color="#dc2626", label="Costs", linestyle="dashed"))

ax2 = fig.add_axes(0, 1)
ax2.add_series(BarSeries(["Q1","Q2","Q3","Q4"], [350,420,390,510], color="#7c3aed", label="Sales"))

ax3 = fig.add_axes(1, 0)
xs = np.random.randn(80).tolist()
ys = (np.array(xs)*0.7 + np.random.randn(80)*0.5).tolist()
ax3.add_series(ScatterSeries(xs, ys, color="#16a34a", size=5))

ax4 = fig.add_axes(1, 1)
ax4.add_series(HistogramSeries(np.random.normal(50,12,300).tolist(), bins=18, color="#0891b2"))

save(fig, "grid_layout")

# 13. Dual Y-axis
volume = [2.1,3.4,1.8,4.2,2.9,3.1,2.4,1.9,3.8,2.7,4.5,3.2]
fig = Figure(width=W, height=H, auto_display=False)
fig.set_title("Dual Y-Axis  —  .add(series, use_y2=True)")
fig.axes.xlabel = "Month"
fig.add(LineSeries(months, revenue, color="#2563eb", label="Revenue ($M, left)", width=2.5))
fig.add(BarSeries(months, volume, color="#d97706", label="Volume M (right)", bar_width=0.5), use_y2=True)
fig.legend_pos = "top-left"
save(fig, "dual_y")


# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAME ACCESSOR
# ─────────────────────────────────────────────────────────────────────────────
print("DataFrame accessor")

df = pd.DataFrame({
    "month":   months,
    "revenue": revenue,
    "costs":   costs,
    "region":  ["North","South"] * 6,
})
save(
    df.glyphx
    .bar(x="month", y="revenue",
         title="Monthly Revenue  —  df.glyphx.bar(x='month', y='revenue')",
         auto_display=False)
    .set_xlabel("Month").set_ylabel("Revenue ($M)")
    .tight_layout(),
    "pandas_example",
)


# ─────────────────────────────────────────────────────────────────────────────
# STATISTICAL
# ─────────────────────────────────────────────────────────────────────────────
print("Statistical")

# 15. Significance brackets
np.random.seed(10)
ctrl  = np.random.normal(44, 8, 70)
drugA = np.random.normal(63, 7, 70)
drugB = np.random.normal(57, 9, 70)
means  = [ctrl.mean(), drugA.mean(), drugB.mean()]
errors = [ctrl.std()/math.sqrt(70)] * 3
save(
    Figure(width=640, height=H, auto_display=False)
    .set_title("Significance Brackets  —  fig.add_stat_annotation()")
    .set_xlabel("Treatment Group").set_ylabel("Outcome Score (mean ± SE)")
    .add(BarSeries(["Control","Drug A","Drug B"], means,
                   color="#60a5fa", label="Mean Score", yerr=errors))
    .add_stat_annotation("Control", "Drug A", p_value=0.0002)
    .add_stat_annotation("Control", "Drug B", p_value=0.028, y_offset=32),
    "stat_annotations",
)

# 16. ECDF
ctrl_d  = np.random.normal(52, 14, 400)
treat_d = np.random.normal(67, 10, 400)
save(
    Figure(width=W, height=H, auto_display=False)
    .set_title("ECDF  —  No Bin-Width Required  —  ECDFSeries")
    .set_xlabel("Response Time (ms)").set_ylabel("Cumulative Proportion")
    .set_legend("top-left")
    .add(ECDFSeries(ctrl_d.tolist(),  color="#3b82f6", label="Control  (n=400)"))
    .add(ECDFSeries(treat_d.tolist(), color="#ef4444", label="Treatment  (n=400)")),
    "ecdf",
)

# 17. Raincloud
grps = [np.random.normal(m,s,70) for m,s in [(38,9),(55,11),(72,7),(48,13)]]
fig = (
    Figure(width=780, height=480, auto_display=False)
    .set_title("Raincloud Plot  —  Jitter + Half-Violin + Box  —  RaincloudSeries")
    .set_ylabel("Score")
)
fig.add(RaincloudSeries(
    grps,
    categories=["Control","Low Dose","High Dose","Combination"],
    violin_width=38, jitter_width=14, seed=42,
))
save(fig, "raincloud")


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL
# ─────────────────────────────────────────────────────────────────────────────
print("Financial")

# 18. Candlestick OHLC
np.random.seed(7)
days = ["Mon","Tue","Wed","Thu","Fri","Mon","Tue","Wed","Thu","Fri"]
p = [148.0]
for _ in range(9):
    p.append(round(p[-1] + np.random.normal(0, 3.2), 2))
o, cp = p[:-1], p[1:]
h = [round(max(a,b) + abs(np.random.normal(1, 0.8)), 2) for a,b in zip(o, cp)]
l = [round(min(a,b) - abs(np.random.normal(1, 0.8)), 2) for a,b in zip(o, cp)]
fig = (
    Figure(width=700, height=H, auto_display=False)
    .set_title("OHLC Candlestick Chart  —  CandlestickSeries")
    .set_xlabel("Trading Session").set_ylabel("Price (USD)")
)
fig.add(CandlestickSeries(days, o, h, l, cp, label="AAPL"))
save(fig, "candlestick")

# 19. Waterfall
fig = (
    Figure(width=720, height=H, auto_display=False)
    .set_title("Revenue Bridge  —  WaterfallSeries  (None = auto total)")
)
fig.add(WaterfallSeries(
    labels=["Q2 Revenue","New Logos","Expansions","Renewals","Churn","Discounts","Q3 Revenue"],
    values=[8.20, 2.10, 0.95, 0.65, -0.82, -0.38, None],
    show_values=True,
    up_color="#16a34a", down_color="#dc2626", total_color="#2563eb",
))
save(fig, "waterfall")

# 20. Treemap
fig = Figure(width=720, height=500, auto_display=False)
fig.set_title("Portfolio Allocation  —  TreemapSeries  (squarified layout)")
fig.add(TreemapSeries(
    labels=["Cloud Infra","AI / ML","Mobile","Security","Data Platform","Networking","IoT","AR/VR"],
    values=[4200, 3100, 2800, 2100, 1900, 1400, 900, 600],
    cmap="viridis", show_values=True,
))
save(fig, "treemap")


# ─────────────────────────────────────────────────────────────────────────────
# STREAMING
# ─────────────────────────────────────────────────────────────────────────────
print("Streaming")

fig = Figure(width=W, height=H, auto_display=False)
fig.set_title("Live Sensor Feed  —  StreamingSeries(max_points=120)")
stream_a = StreamingSeries(max_points=120, color="#2563eb", label="Sensor A")
stream_b = StreamingSeries(max_points=120, color="#dc2626", label="Sensor B")
fig.add(stream_a)
fig.add(stream_b)
t = np.linspace(0, 5*np.pi, 200)
for va, vb in zip(
    np.sin(t)*10 + np.random.randn(200)*1.2 + 28,
    np.cos(t)*8  + np.random.randn(200)*1.2 + 22,
):
    stream_a.push(float(va))
    stream_b.push(float(vb))
save(fig, "streaming")


print(f"\nDone — {len(list(OUT.glob('*.svg')))} SVGs written to {OUT}/")
