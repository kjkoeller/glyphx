"""
GlyphX → Vega-Lite JSON export.

Converts a GlyphX :class:`~glyphx.Figure` to a Vega-Lite v5 specification
dict.  The spec can be used in Observable, any Vega-compatible tool, or
saved as a portable ``.vl.json`` file.

No Python plotting library currently produces Vega-Lite output — this
makes GlyphX the first to close the Python ↔ Observable interoperability gap.

    from glyphx import Figure
    from glyphx.series import LineSeries, BarSeries
    from glyphx.vega_lite import to_vega_lite
    import json

    fig = (Figure()
           .add(LineSeries(months, revenue, label="Revenue"))
           .add(BarSeries(months, costs,   label="Costs")))

    spec = to_vega_lite(fig)
    json.dump(spec, open("chart.vl.json","w"), indent=2)

    # Or use the Figure method directly
    fig.to_vega_lite("chart.vl.json")
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Series-level converters
# ---------------------------------------------------------------------------

def _series_to_layer(series, use_y2: bool = False) -> dict | None:
    """Convert a single GlyphX series to a Vega-Lite layer dict."""
    cls = series.__class__.__name__

    # Base data
    x_vals = getattr(series, "_numeric_x", series.x) if series.x else []
    y_vals = series.y or []

    if not x_vals or not y_vals:
        return None

    # Build inline data records
    x_raw   = series.x or x_vals   # prefer original labels for categorical
    records = []
    for x, y in zip(x_raw, y_vals):
        records.append({"x": x, "y": float(y) if isinstance(y, (int, float)) else y})

    if cls == "LineSeries":
        return {
            "data":   {"values": records},
            "mark":   {"type": "line",
                       "color": series.color,
                       "strokeWidth": getattr(series, "width", 2),
                       "strokeDash": _dash_to_vl(getattr(series, "linestyle", "solid"))},
            "encoding": {
                "x": {"field": "x", "type": _infer_type(x_raw), "title": ""},
                "y": {"field": "y", "type": "quantitative",
                      **({"axis": {"orient": "right"}} if use_y2 else {})},
            },
            **({"name": series.label} if series.label else {}),
        }

    if cls == "BarSeries":
        return {
            "data":   {"values": records},
            "mark":   {"type": "bar", "color": series.color},
            "encoding": {
                "x": {"field": "x", "type": _infer_type(x_raw), "title": ""},
                "y": {"field": "y", "type": "quantitative",
                      **({"axis": {"orient": "right"}} if use_y2 else {})},
            },
        }

    if cls == "ScatterSeries":
        enc: dict[str, Any] = {
            "x": {"field": "x", "type": "quantitative"},
            "y": {"field": "y", "type": "quantitative"},
            "color": {"value": series.color},
        }
        # colormap encoding
        c = getattr(series, "c", None)
        if c is not None:
            for i, rec in enumerate(records):
                if i < len(c):
                    rec["c"] = float(c[i])
            enc["color"] = {
                "field": "c", "type": "quantitative",
                "scale": {"scheme": _cmap_to_vl(getattr(series, "cmap", "viridis"))},
            }
        return {
            "data":     {"values": records},
            "mark":     {"type": "point", "size": getattr(series, "size", 5) ** 2},
            "encoding": enc,
        }

    if cls == "HistogramSeries":
        raw_data = getattr(series, "data", [])
        recs = [{"v": float(v)} for v in raw_data]
        return {
            "data":   {"values": recs},
            "mark":   {"type": "bar", "color": series.color},
            "encoding": {
                "x": {"field": "v", "type": "quantitative",
                      "bin": {"maxbins": len(x_raw)}, "title": ""},
                "y": {"aggregate": "count", "type": "quantitative"},
            },
        }

    # Fallback: generic point layer
    return {
        "data":     {"values": records},
        "mark":     {"type": "point", "color": series.color},
        "encoding": {
            "x": {"field": "x", "type": _infer_type(x_raw)},
            "y": {"field": "y", "type": "quantitative"},
        },
    }


def _dash_to_vl(style: str) -> list[int]:
    mapping = {
        "solid":    [],
        "dashed":   [6, 3],
        "dotted":   [2, 2],
        "longdash": [12, 4],
    }
    return mapping.get(style, [])


def _cmap_to_vl(cmap: str) -> str:
    """Map GlyphX colormap names to Vega-Lite scheme names."""
    mapping = {
        "viridis":  "viridis",
        "plasma":   "plasma",
        "inferno":  "inferno",
        "magma":    "magma",
        "cividis":  "cividis",
        "coolwarm": "blueorange",
        "rdbu":     "redblue",
        "spectral": "spectral",
        "greys":    "greys",
    }
    return mapping.get(cmap, "viridis")


def _infer_type(values: list) -> str:
    """Guess Vega-Lite field type from a list of values."""
    if not values:
        return "nominal"
    v = values[0]
    if isinstance(v, str):
        try:
            float(v)
            return "quantitative"
        except ValueError:
            pass
        import re
        if re.match(r"\d{4}-\d{2}-\d{2}", str(v)):
            return "temporal"
        return "nominal"
    if isinstance(v, (int, float)):
        return "quantitative"
    return "nominal"


# ---------------------------------------------------------------------------
# Figure-level converter
# ---------------------------------------------------------------------------

def to_vega_lite(
    fig,
    width:  int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """
    Convert a :class:`~glyphx.Figure` to a Vega-Lite v5 specification dict.

    The resulting specification can be:

    - Saved as a ``.vl.json`` file and opened in the Vega editor
    - Embedded in Observable notebooks
    - Rendered with ``altair`` (``alt.Chart.from_dict(spec)``)
    - Shared as a portable, renderer-agnostic chart format

    Args:
        fig:    GlyphX :class:`~glyphx.Figure` instance.
        width:  Override canvas width (defaults to ``fig.width``).
        height: Override canvas height (defaults to ``fig.height``).

    Returns:
        Vega-Lite v5 specification as a nested dict.

    Example::

        from glyphx import Figure
        from glyphx.series import LineSeries
        from glyphx.vega_lite import to_vega_lite
        import json

        fig = Figure().add(LineSeries(months, revenue, label="Revenue"))
        spec = to_vega_lite(fig)
        print(json.dumps(spec, indent=2))
    """
    W = width  or fig.width
    H = height or fig.height

    layers = []
    resolve: dict = {}

    for series, use_y2 in fig.series:
        layer = _series_to_layer(series, use_y2=use_y2)
        if layer is not None:
            if series.label:
                layer["name"] = series.label
            layers.append(layer)

    if len(layers) == 1:
        # Single layer — use flat spec
        spec = layers[0]
    else:
        spec = {"layer": layers}

    # Add dual-Y resolve if needed
    has_y2 = any(use_y2 for _, use_y2 in fig.series)
    if has_y2:
        spec["resolve"] = {"scale": {"y": "independent"}}

    # Top-level properties
    spec["$schema"] = "https://vega.github.io/schema/vega-lite/v5.json"
    spec["width"]   = W - 100    # leave room for axis labels
    spec["height"]  = H - 80
    spec["title"]   = fig.title or ""

    # Axis labels
    axes = fig.axes
    if getattr(axes, "xlabel", ""):
        for layer in (layers if "layer" in spec else [spec]):
            if "encoding" in layer and "x" in layer["encoding"]:
                layer["encoding"]["x"]["title"] = axes.xlabel
    if getattr(axes, "ylabel", ""):
        for layer in (layers if "layer" in spec else [spec]):
            if "encoding" in layer and "y" in layer["encoding"]:
                layer["encoding"]["y"]["title"] = axes.ylabel

    # Theme approximation
    theme_dict = fig.theme
    bg  = theme_dict.get("background", "#fff")
    tc  = theme_dict.get("text_color",  "#000")
    spec["config"] = {
        "background": bg,
        "title":      {"color": tc, "fontSize": 16},
        "axis":       {"labelColor": tc, "titleColor": tc, "gridColor": theme_dict.get("grid_color","#ddd")},
        "view":       {"stroke": "transparent"},
    }

    return spec


def save_vega_lite(fig, path: str | Path, **kwargs) -> None:
    """
    Serialize a figure's Vega-Lite spec to a JSON file.

    Args:
        fig:  GlyphX :class:`~glyphx.Figure`.
        path: Output path (conventionally ``.vl.json``).

    Example::

        from glyphx.vega_lite import save_vega_lite
        save_vega_lite(fig, "chart.vl.json")
    """
    spec = to_vega_lite(fig, **kwargs)
    Path(path).write_text(json.dumps(spec, indent=2), encoding="utf-8")
