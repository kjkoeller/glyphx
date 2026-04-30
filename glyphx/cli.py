"""
GlyphX command-line interface.

After installation, the ``glyphx`` command is available::

    glyphx plot sales.csv --x month --y revenue --kind bar --theme dark -o chart.html
    glyphx version

Use ``glyphx <command> --help`` for full argument documentation.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the appropriate sub-command."""
    parser = argparse.ArgumentParser(
        prog="glyphx",
        description="GlyphX — SVG-first Python plotting library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  glyphx plot sales.csv --x month --y revenue --kind bar -o chart.html\n"
            "  glyphx plot data.csv --y price --kind hist --bins 20\n"
            "  glyphx version\n"
        ),
    )

    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    _add_plot_parser(sub)
    _add_version_parser(sub)

    args = parser.parse_args(argv)
    return args.func(args)


# ---------------------------------------------------------------------------
# plot sub-command
# ---------------------------------------------------------------------------

def _add_plot_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "plot",
        help="Render a chart from a CSV / JSON / Excel file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Load tabular data and render a GlyphX chart.",
        epilog=(
            "Supported input formats : .csv  .tsv  .json  .jsonl  .xlsx  .xls\n"
            "Supported output formats: .svg  .html  .png  .jpg  .pptx\n"
        ),
    )

    # Input
    p.add_argument("file", help="Input data file (CSV, JSON, Excel, …)")
    p.add_argument("--sep",    default=",",     help="CSV/TSV delimiter (default: ',')")
    p.add_argument("--sheet",  default=0,       help="Excel sheet name or 0-based index")

    # Axes
    p.add_argument("--x",      metavar="COL",   help="Column name for X axis")
    p.add_argument("--y",      metavar="COL",   help="Column name for Y axis")
    p.add_argument("--groupby", metavar="COL",  help="Group data by this column")
    p.add_argument("--agg",    default="sum",
                   choices=["sum", "mean", "count", "max", "min"],
                   help="Aggregation function when --groupby is used (default: sum)")

    # Chart type
    p.add_argument("--kind", "-k", default="line",
                   choices=["line", "bar", "scatter", "hist", "box", "pie", "donut", "heatmap"],
                   help="Chart type (default: line)")
    p.add_argument("--bins",  type=int, default=10, help="Number of histogram bins (default: 10)")

    # Appearance
    p.add_argument("--title",  help="Chart title")
    p.add_argument("--theme",  default="default",
                   choices=["default", "dark", "colorblind", "pastel",
                             "warm", "ocean", "monochrome"],
                   help="Visual theme (default: default)")
    p.add_argument("--color",  help="Primary series colour (hex, e.g. #ff7f0e)")
    p.add_argument("--label",  help="Series legend label")
    p.add_argument("--xlabel", help="X-axis label")
    p.add_argument("--ylabel", help="Y-axis label")
    p.add_argument("--width",  type=int, default=800,  help="Canvas width in pixels (default: 800)")
    p.add_argument("--height", type=int, default=500,  help="Canvas height in pixels (default: 500)")
    p.add_argument("--no-legend", action="store_true", help="Hide the legend")

    # Output
    p.add_argument("-o", "--output", default="glyphx_chart.html",
                   help="Output file path (default: glyphx_chart.html)")
    p.add_argument("--open", action="store_true",
                   help="Open the output file in the default browser after saving")

    p.set_defaults(func=_cmd_plot)


def _cmd_plot(args: argparse.Namespace) -> int:
    """Execute the ``plot`` sub-command."""
    try:
        import pandas as pd
    except ImportError:
        _err("pandas is required: pip install pandas")
        return 1

    # ── Load data ─────────────────────────────────────────────────────────
    path = Path(args.file)
    if not path.exists():
        _err(f"File not found: {path}")
        return 1

    try:
        df = _load_file(path, sep=args.sep, sheet=args.sheet)
    except Exception as exc:
        _err(f"Could not load {path}: {exc}")
        return 1

    _info(f"Loaded {len(df):,} rows × {len(df.columns)} columns from {path.name}")

    # ── Build chart ───────────────────────────────────────────────────────
    from glyphx import Figure
    from glyphx.series import (
        LineSeries, BarSeries, ScatterSeries,
        HistogramSeries, BoxPlotSeries, PieSeries, DonutSeries, HeatmapSeries,
    )

    legend = False if args.no_legend else "top-right"
    fig = Figure(
        title=args.title,
        theme=args.theme,
        width=args.width,
        height=args.height,
        legend=legend,
        auto_display=False,
    )
    fig.axes.xlabel = args.xlabel or args.x
    fig.axes.ylabel = args.ylabel or args.y

    kind = args.kind.lower()

    if kind in {"hist", "box"}:
        target = args.y or args.x or df.select_dtypes("number").columns[0]
        data   = df[target].dropna().tolist()
        if kind == "hist":
            fig.add(HistogramSeries(data, bins=args.bins,
                                    color=args.color, label=args.label or target))
        else:
            fig.add(BoxPlotSeries(data, color=args.color or "#1f77b4",
                                  label=args.label or target))

    elif kind in {"pie", "donut"}:
        x_col = args.x
        y_col = args.y or df.select_dtypes("number").columns[0]
        labels_data = df[x_col].tolist() if x_col and x_col in df.columns else None
        values_data = df[y_col].tolist()
        if kind == "pie":
            fig.add(PieSeries(values_data, labels=labels_data))
        else:
            fig.add(DonutSeries(values_data,
                                labels=[str(l) for l in (labels_data or range(len(values_data)))]))

    elif kind == "heatmap":
        num_df = df.select_dtypes("number")
        fig.add(HeatmapSeries(
            num_df.values.tolist(),
            col_labels=num_df.columns.tolist(),
            row_labels=[str(i) for i in df.index.tolist()],
        ))

    elif args.groupby and args.groupby in df.columns:
        theme_colors = fig.theme.get("colors", ["#1f77b4", "#ff7f0e", "#2ca02c"])
        y_col = args.y or df.select_dtypes("number").columns[0]
        if args.x and args.x in df.columns:
            for i, (grp, gdf) in enumerate(df.groupby(args.groupby)):
                x_data = gdf[args.x].tolist()
                y_data = gdf[y_col].tolist()
                clr    = theme_colors[i % len(theme_colors)]
                fig.add(_series_for(kind, x_data, y_data, clr, str(grp)))
        else:
            agg_df = df.groupby(args.groupby)[y_col].agg(args.agg).reset_index()
            x_data = agg_df[args.groupby].tolist()
            y_data = agg_df[y_col].tolist()
            fig.add(_series_for(kind, x_data, y_data, args.color, args.label or y_col))

    else:
        x_data = df[args.x].tolist() if args.x and args.x in df.columns else list(range(len(df)))
        y_data = (df[args.y].tolist() if args.y and args.y in df.columns
                  else df.select_dtypes("number").iloc[:, 0].tolist())
        fig.add(_series_for(kind, x_data, y_data, args.color, args.label or args.y))

    # ── Save ──────────────────────────────────────────────────────────────
    out = args.output
    try:
        fig.save(out)
        _info(f"Saved → {out}")
    except Exception as exc:
        _err(f"Save failed: {exc}")
        return 1

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{Path(out).resolve()}")

    return 0


def _series_for(kind: str, x: list, y: list, color: str | None, label: str | None):
    from glyphx.series import LineSeries, BarSeries, ScatterSeries
    if kind == "bar":     return BarSeries(x, y, color=color, label=label)
    if kind == "scatter": return ScatterSeries(x, y, color=color, label=label)
    return LineSeries(x, y, color=color, label=label)


# ---------------------------------------------------------------------------

def _add_version_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("version", help="Show GlyphX version and exit.")
    p.set_defaults(func=_cmd_version)


def _cmd_version(args: argparse.Namespace) -> int:
    """Execute the ``version`` sub-command."""
    try:
        from importlib.metadata import version
        v = version("glyphx")
    except Exception:
        v = "unknown"
    print(f"GlyphX {v}")
    return 0
