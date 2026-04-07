"""
GlyphX v1.5 — Complete Example Suite
=====================================

Run this file to generate an HTML output for every feature:

    python examples.py

Each example saves a file to ./output/ and prints the filename.
Set OPEN=1 to auto-open each chart in your browser:

    OPEN=1 python examples.py

Requirements:
    pip install glyphx pandas numpy
    pip install "glyphx[pptx]"     # for PPTX export example
    pip install anthropic           # for from_prompt() example
"""

import os, math, warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
OPEN   = os.environ.get("OPEN") == "1"
OUTDIR = Path("./glyphx_output")
OUTDIR.mkdir(exist_ok=True)

import glyphx
from glyphx import Figure
from glyphx.series import (
    LineSeries, BarSeries, ScatterSeries,
    PieSeries, DonutSeries, HistogramSeries,
    BoxPlotSeries, HeatmapSeries,
)
from glyphx.ecdf         import ECDFSeries
from glyphx.raincloud    import RaincloudSeries
from glyphx.candlestick  import CandlestickSeries
from glyphx.waterfall    import WaterfallSeries
from glyphx.treemap      import TreemapSeries
from glyphx.streaming    import StreamingSeries
from glyphx.colormaps    import colormap_colors, apply_colormap, list_colormaps
from glyphx.stat_annotation import pvalue_to_label

np.random.seed(42)


def save(fig, name, fmt="html"):
    path = OUTDIR / f"{name}.{fmt}"
    fig.save(str(path))
    print(f"  ✓ {path}")
    if OPEN:
        import webbrowser
        webbrowser.open(f"file://{path.resolve()}")
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — BASIC CHART TYPES
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Basic Charts ──────────────────────────────────────────")

months  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
revenue = [120,135,98,170,145,190,210,175,230,205,260,300]
costs   = [80, 90, 65,100, 95,110,130,105,140,120,155,175]

# 1. Line chart — multi-series, dashed line, legend
(Figure(width=720, height=460)
    .set_title("Monthly Revenue vs Costs")
    .set_xlabel("Month").set_ylabel("USD (thousands)")
    .add(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=2.5))
    .add(LineSeries(months, costs, color="#dc2626", label="Costs", linestyle="dashed"))
    .set_legend("top-left")
    | save # <- pipe syntax is just a readable way to chain save
) if False else save(
    Figure(width=720, height=460)
    .set_title("Monthly Revenue vs Costs")
    .set_xlabel("Month").set_ylabel("USD (thousands)")
    .add(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=2.5))
    .add(LineSeries(months, costs, color="#dc2626", label="Costs", linestyle="dashed"))
    .set_legend("top-left"),
    "01_line"
)

# 2. Bar chart with error bars
products = ["Widget A","Widget B","Widget C","Widget D","Widget E"]
sales    = [4200, 3100, 5800, 2400, 6700]
errors   = [210,  155,  290,  120,  335]
save(
    Figure(width=640, height=440)
    .set_title("Product Sales Q3 (±SE)")
    .set_xlabel("Product").set_ylabel("Units Sold")
    .add(BarSeries(products, sales, color="#7c3aed", label="Units", yerr=errors)),
    "02_bar_with_errors"
)

# 3. Scatter plot with continuous color encoding
x = np.random.randn(100)
y = 0.7*x + np.random.randn(100)*0.5
z = np.sin(x) + np.cos(y)
save(
    Figure(width=640, height=460)
    .set_title("Scatter with Viridis Color Encoding")
    .set_xlabel("X").set_ylabel("Y")
    .add(ScatterSeries(x.tolist(), y.tolist(),
                       c=z.tolist(), cmap="viridis", size=7, label="sin(x)+cos(y)")),
    "03_scatter_colormap"
)

# 4. Pie chart
save(
    Figure(width=480, height=420)
    .set_title("Market Share 2024")
    .add(PieSeries(
        [38,25,18,11,8],
        labels=["GlyphX","Matplotlib","Plotly","Seaborn","Other"],
        colors=["#2563eb","#dc2626","#16a34a","#d97706","#9ca3af"],
    )),
    "04_pie"
)

# 5. Donut chart
save(
    Figure(width=480, height=420)
    .set_title("Budget Allocation")
    .add(DonutSeries(
        [35,25,20,12,8],
        labels=["Engineering","Marketing","Sales","Operations","Legal"],
        colors=colormap_colors("plasma", 5),
    )),
    "05_donut"
)

# 6. Histogram — bimodal distribution
data = np.concatenate([np.random.normal(50,8,400), np.random.normal(78,6,200)])
save(
    Figure(width=640, height=440)
    .set_title("Response Time Distribution (Bimodal)")
    .set_xlabel("Milliseconds").set_ylabel("Frequency")
    .add(HistogramSeries(data.tolist(), bins=30, color="#0891b2", label="Response Time")),
    "06_histogram"
)

# 7. Box plot — multi-group with outliers
groups = [np.random.normal(m, s, 80) for m, s in [(50,10),(65,8),(55,15),(72,6)]]
save(
    Figure(width=640, height=440)
    .set_title("Test Scores by Treatment Group")
    .set_ylabel("Score")
    .add(BoxPlotSeries(groups,
        categories=["Control","Drug A","Drug B","Drug C"],
        color="#7c3aed", box_width=28)),
    "07_boxplot"
)

# 8. Heatmap — correlation matrix
labels = ["Revenue","Traffic","Conv Rate","Bounce"]
corr   = np.array([[1.0,0.85,0.42,-0.31],[0.85,1.0,0.61,-0.18],
                   [0.42,0.61,1.0,0.23],[-0.31,-0.18,0.23,1.0]])
save(
    Figure(width=620, height=440)
    .set_title("KPI Correlation Matrix")
    .add(HeatmapSeries(corr.tolist(), row_labels=labels, col_labels=labels,
        show_values=True,
        cmap=["#1e40af","#93c5fd","#f0f0f0","#fca5a5","#b91c1c"])),
    "08_heatmap"
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — ADVANCED FEATURES (method chaining, dual-Y, annotations)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Advanced Features ─────────────────────────────────────")

# 9. Dual Y-axis (line + bar on independent scales)
prices = [142,148,151,145,160,158,165,172,168,180,188,195]
volume = [2.1,3.4,1.8,4.2,2.9,3.1,2.4,1.9,3.8,2.7,4.5,3.2]
fig_dual = Figure(width=720, height=460)
fig_dual.set_title("Stock Price & Volume (Dual Y-Axis)")
fig_dual.axes.xlabel = "Month"
fig_dual.add(LineSeries(months, prices, color="#2563eb", label="Price (left)", width=2))
fig_dual.add(BarSeries(months, volume, color="#d97706",
             label="Volume M (right)", bar_width=0.5), use_y2=True)
fig_dual.legend_pos = "top-left"
save(fig_dual, "09_dual_y")

# 10. Method chaining — full chain from scratch
save(
    Figure(width=680, height=440)
    .set_title("Method Chaining Demo")
    .set_theme("dark")
    .set_size(680, 440)
    .set_xlabel("Quarter")
    .set_ylabel("Revenue ($M)")
    .set_legend("top-left")
    .add(LineSeries(["Q1","Q2","Q3","Q4","Q1","Q2","Q3","Q4"],
                    [1.2,1.5,1.3,1.8,2.1,2.4,2.2,2.9],
                    color="#a78bfa", label="2022–2023", width=2.5))
    .add(LineSeries(["Q1","Q2","Q3","Q4","Q1","Q2","Q3","Q4"],
                    [0.8,1.1,0.9,1.4,1.7,2.0,1.8,2.5],
                    color="#fb923c", label="Target", linestyle="dashed")),
    "10_method_chaining"
)

# 11. Annotations with arrows
x_ann = list(range(1,25))
y_ann = [20+10*math.sin(i/3)+i*0.8+np.random.randn()*2 for i in x_ann]
save(
    Figure(width=700, height=440)
    .set_title("Sales with Key Event Markers")
    .set_xlabel("Week").set_ylabel("Revenue ($K)")
    .add(LineSeries(x_ann, y_ann, color="#16a34a", label="Weekly Revenue", width=2))
    .annotate("Product Launch", x=8,  y=y_ann[7], arrow=True, color="#dc2626")
    .annotate("PR Campaign",    x=15, y=y_ann[14], arrow=True, color="#7c3aed")
    .annotate("Record High",   x=23, y=y_ann[22], arrow=True, color="#d97706"),
    "11_annotations"
)

# 12. Tight layout + auto-rotation
long_labels = ["Engineering Dept","Marketing Dept","Sales Dept",
               "Operations","Finance","Legal & Compliance","R&D Lab","HR & People"]
save(
    Figure(width=680, height=460)
    .set_title("Headcount by Department (Auto Tight Layout)")
    .set_ylabel("Headcount")
    .add(BarSeries(long_labels, [142,58,94,71,35,24,88,46]))
    .tight_layout(),   # ← auto-adjusts padding + rotates crowded labels
    "12_tight_layout"
)

# 13. Subplot grid
fig_grid = Figure(rows=2, cols=2, width=900, height=600)
fig_grid.title = "2×2 Subplot Grid"
ax1 = fig_grid.add_axes(0,0); ax1.add_series(LineSeries([1,2,3,4],[4,7,3,8]))
ax2 = fig_grid.add_axes(0,1); ax2.add_series(BarSeries(["A","B","C"],[10,25,15]))
ax3 = fig_grid.add_axes(1,0); ax3.add_series(ScatterSeries(
    np.random.randn(30).tolist(), np.random.randn(30).tolist()))
ax4 = fig_grid.add_axes(1,1)
ax4.add_series(HistogramSeries(np.random.normal(50,10,200).tolist(), bins=15))
save(fig_grid, "13_subplot_grid")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — DATAFRAME ACCESSOR
# ─────────────────────────────────────────────────────────────────────────────
print("\n── DataFrame Accessor ────────────────────────────────────")

df = pd.DataFrame({
    "quarter": ["Q1 22","Q2 22","Q3 22","Q4 22","Q1 23","Q2 23","Q3 23","Q4 23"],
    "revenue": [1.2,1.5,1.3,1.8,2.1,2.4,2.2,2.9],
    "costs":   [0.8,0.9,0.8,1.1,1.3,1.4,1.2,1.6],
    "region":  ["North","South","North","South","North","South","North","South"],
})

# 14. df.glyphx.bar — one-liner
save(
    df.glyphx.bar(
        x="quarter", y="revenue", label="Revenue",
        title="Quarterly Revenue", auto_display=False
    ).set_xlabel("Quarter").set_ylabel("Revenue ($B)"),
    "14_accessor_bar"
)

# 15. Groupby aggregation
save(
    df.glyphx.bar(
        groupby="region", y="revenue", agg="mean",
        title="Avg Revenue by Region", auto_display=False
    ),
    "15_accessor_groupby"
)

# 16. Scatter from DataFrame
df_scatter = pd.DataFrame({
    "x": np.random.randn(80),
    "y": np.random.randn(80),
    "size_metric": np.random.rand(80),
})
save(
    df_scatter.glyphx.scatter(
        x="x", y="y", title="Scatter from DataFrame", auto_display=False
    ).set_xlabel("X").set_ylabel("Y"),
    "16_accessor_scatter"
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — STATISTICAL (vs Seaborn)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Statistical Charts (vs Seaborn) ──────────────────────")

# 17. Statistical significance annotations
ctrl  = np.random.normal(45, 8, 60)
drugA = np.random.normal(62, 7, 60)
drugB = np.random.normal(58, 9, 60)
means  = [ctrl.mean(), drugA.mean(), drugB.mean()]
errors = [ctrl.std()/8, drugA.std()/8, drugB.std()/8]
save(
    Figure(width=620, height=460)
    .set_title("Treatment Efficacy (*** p<0.001, * p<0.05)")
    .set_xlabel("Group").set_ylabel("Outcome Score")
    .add(BarSeries(["Control","Drug A","Drug B"], means,
                   color="#60a5fa", label="Mean Score", yerr=errors))
    .add_stat_annotation("Control", "Drug A", p_value=0.0003)
    .add_stat_annotation("Control", "Drug B", p_value=0.031, y_offset=30),
    "17_stat_annotations"
)

# 18. ECDF — compare two distributions
ctrl_d  = np.random.normal(50, 12, 300)
treat_d = np.random.normal(65, 9, 300)
save(
    Figure(width=640, height=440)
    .set_title("ECDF: Response Time — Control vs Treatment")
    .set_xlabel("Response Time (ms)").set_ylabel("Cumulative Proportion")
    .set_legend("top-left")
    .add(ECDFSeries(ctrl_d.tolist(),  color="#3b82f6", label="Control"))
    .add(ECDFSeries(treat_d.tolist(), color="#ef4444", label="Treatment")),
    "18_ecdf"
)

# 19. Raincloud — the modern box plot replacement
groups_rc = [
    np.random.normal(40,  8, 60),
    np.random.normal(55, 10, 60),
    np.random.normal(70,  7, 60),
    np.random.normal(50, 14, 60),
]
save(
    Figure(width=680, height=480)
    .set_title("Raincloud: Score Distribution by Group")
    .set_ylabel("Score")
    .add(RaincloudSeries(
        groups_rc,
        categories=["Control","Low Dose","High Dose","Combo"],
        violin_width=38, jitter_width=16,
    )),
    "19_raincloud"
)

# 20. Colormaps showcase
print(f"  Available colormaps: {', '.join(list_colormaps())}")
save(
    Figure(width=640, height=460)
    .set_title("Scatter: Plasma Colormap Encoding")
    .set_xlabel("X").set_ylabel("Y")
    .add(ScatterSeries(
        np.random.randn(120).tolist(),
        np.random.randn(120).tolist(),
        c=np.random.rand(120).tolist(),
        cmap="plasma", size=7,
    )),
    "20_colormap_plasma"
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — FINANCIAL & HIERARCHICAL (vs Plotly)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Financial & Hierarchical (vs Plotly) ─────────────────")

# 21. Candlestick / OHLC
np.random.seed(7)
days = ["Mon","Tue","Wed","Thu","Fri","Mon","Tue","Wed","Thu","Fri"]
p = [150.0]
for _ in range(9):
    p.append(p[-1] + np.random.normal(0, 2.5))
o, c_prices = p[:-1], p[1:]
h = [max(o,c)+abs(np.random.normal(0,1.5)) for o,c in zip(o, c_prices)]
l = [min(o,c)-abs(np.random.normal(0,1.5)) for o,c in zip(o, c_prices)]
save(
    Figure(width=660, height=460)
    .set_title("AAPL — 2-Week Intraday OHLC")
    .set_xlabel("Session").set_ylabel("Price (USD)")
    .add(CandlestickSeries(days, o, h, l, c_prices, label="AAPL")),
    "21_candlestick"
)

# 22. Waterfall / bridge chart
save(
    Figure(width=680, height=460)
    .set_title("Q3 Revenue Bridge ($M)")
    .add(WaterfallSeries(
        labels=["Q2 Revenue","New Customers","Upsells","Renewals","Churn","Discounts","Q3 Revenue"],
        values=[8.2, 2.1, 0.9, 0.6, -0.8, -0.4, None],
        up_color="#16a34a", down_color="#dc2626", total_color="#2563eb",
        show_values=True,
    )),
    "22_waterfall"
)

# 23. Treemap — squarified layout
save(
    Figure(width=680, height=480)
    .set_title("Tech Investment Portfolio ($M)")
    .add(TreemapSeries(
        labels=["Cloud Infra","AI/ML Platform","Mobile Apps","Security",
                "Data Platform","Networking","IoT Devices","AR/VR"],
        values=[4200, 3100, 2800, 2100, 1900, 1400, 900, 600],
        cmap="viridis",
    )),
    "23_treemap"
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — STREAMING
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Streaming Series ──────────────────────────────────────")

# 24. Streaming — simulate 200 sensor readings
fig_stream = Figure(width=680, height=440)
fig_stream.set_title("Live Sensor Feed (200 readings, max_points=80)")
stream = StreamingSeries(max_points=80, color="#7c3aed", label="Sensor A")
stream2 = StreamingSeries(max_points=80, color="#fb923c", label="Sensor B")
fig_stream.add(stream)
fig_stream.add(stream2)

t = np.linspace(0, 6*np.pi, 200)
for val_a, val_b in zip(
    np.sin(t)*10 + np.random.randn(200)*1.5 + 25,
    np.cos(t)*8  + np.random.randn(200)*1.5 + 28,
):
    stream.push(float(val_a))
    stream2.push(float(val_b))

save(fig_stream, "24_streaming")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — LINKED BRUSHING + SHARING
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Linked Brushing & Sharing ─────────────────────────────")

# 25. Multi-chart page with linked brushing
from glyphx.layout import grid
x_shared = list(range(1,21))
y1 = [v + np.random.randn()*3 for v in x_shared]
y2 = [v**1.2 + np.random.randn()*4 for v in x_shared]

f1 = Figure(width=460, height=340, legend=False)
f1.set_title("Chart A — Shift+drag to brush")
f1.add(ScatterSeries(x_shared, y1, color="#2563eb", label="A", size=8))

f2 = Figure(width=460, height=340, legend=False)
f2.set_title("Chart B — Linked selection")
f2.add(ScatterSeries(x_shared, y2, color="#dc2626", label="B", size=8))

linked_html = grid([f1, f2], rows=1, cols=2)
p = OUTDIR / "25_linked_brushing.html"
p.write_text(linked_html)
print(f"  ✓ {p}  ← Shift+drag on either chart to see linked selection")

# 26. Self-contained shareable HTML
fig_share = (
    Figure(width=700, height=460)
    .set_title("Self-Contained Share Demo")
    .set_theme("dark")
    .add(LineSeries(months, revenue, color="#a78bfa", label="Revenue", width=2.5))
    .add(LineSeries(months, costs, color="#fb923c", label="Costs", linestyle="dashed"))
    .set_legend("top-left")
)
share_html = fig_share.share(str(OUTDIR / "26_shareable.html"),
                              title="Revenue Chart — GlyphX Share Demo")
print(f"  ✓ {OUTDIR / '26_shareable.html'}  ← Self-contained, zero CDN, share freely")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — THEMES
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Themes ────────────────────────────────────────────────")

for theme_name in ["dark","colorblind","warm","ocean","pastel","monochrome"]:
    save(
        Figure(width=600, height=380, theme=theme_name)
        .set_title(f"Theme: {theme_name.title()}")
        .set_xlabel("Month").set_ylabel("Value")
        .add(LineSeries(months[:8], revenue[:8], label="Revenue"))
        .add(BarSeries(months[:8], [c*1.2 for c in costs[:8]], label="Costs", bar_width=0.4)),
        f"27_theme_{theme_name}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — NLP (requires ANTHROPIC_API_KEY)
# ─────────────────────────────────────────────────────────────────────────────
print("\n── NLP Chart Generation (optional) ──────────────────────")

if os.environ.get("ANTHROPIC_API_KEY"):
    try:
        from glyphx import from_prompt
        df_nlp = pd.DataFrame({
            "month":   months,
            "revenue": revenue,
            "costs":   costs,
        })
        fig_nlp = from_prompt(
            "line chart of revenue and costs over months, dark theme",
            df=df_nlp, auto_display=False
        )
        save(fig_nlp, "28_from_prompt_nlp")
    except Exception as e:
        print(f"  ⚠ NLP example skipped: {e}")
else:
    print("  ⚠ Set ANTHROPIC_API_KEY to run the from_prompt() example")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — PPTX EXPORT (requires glyphx[pptx])
# ─────────────────────────────────────────────────────────────────────────────
print("\n── PPTX Export (optional) ────────────────────────────────")

try:
    import pptx, cairosvg  # noqa: F401
    fig_pptx = (
        Figure(width=720, height=460)
        .set_title("Revenue Dashboard")
        .set_theme("default")
        .add(LineSeries(months, revenue, color="#2563eb", label="Revenue", width=2.5))
        .add(LineSeries(months, costs, color="#dc2626", label="Costs", linestyle="dashed"))
        .set_legend("top-left")
    )
    fig_pptx.save(str(OUTDIR / "29_export.pptx"))
    print(f"  ✓ {OUTDIR / '29_export.pptx'}")
except ImportError:
    print("  ⚠ Install glyphx[pptx] for PowerPoint export: pip install 'glyphx[pptx]'")


# ─────────────────────────────────────────────────────────────────────────────
print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Done! All outputs saved to: {OUTDIR.resolve()}

  Open the gallery:
    open {OUTDIR}/01_line.html        # basic line chart
    open {OUTDIR}/25_linked_brushing.html  # shift+drag to brush
    open {OUTDIR}/26_shareable.html   # zero-CDN shareable

  Run with OPEN=1 to auto-open each file in your browser.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
