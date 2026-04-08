Introduction
============

GlyphX is a next-generation Python plotting library built around three design principles:

1. **SVG-first** — every chart is a self-contained SVG document with interactive
   tooltips, zoom, pan, and export built in by default.

2. **Zero boilerplate** — charts auto-display wherever you are (Jupyter, CLI, IDE).
   No ``plt.show()``, no figure managers, no backend configuration.

3. **Chainable by design** — every mutating ``Figure`` method returns ``self``,
   so you can build, style, annotate, and export a chart in a single expression.


Why GlyphX?
-----------

GlyphX was built to address specific pain points with the existing ecosystem:

**vs Matplotlib** — Matplotlib is powerful but verbose. A simple annotated dual-axis chart
requires 10–15 lines of boilerplate. GlyphX does the same in one chained expression.
``tight_layout()`` is automatic, themes apply globally, and every chart is interactive
without extra configuration.

**vs Seaborn** — Seaborn has beautiful defaults but a limited chart set and no native
significance annotation (requiring the third-party ``statannotations`` package).
GlyphX ships raincloud plots, ECDF curves, and ``fig.add_stat_annotation()`` out of the box.

**vs Plotly** — Plotly's interactivity requires a CDN dependency or a running Dash server.
GlyphX's ``fig.share()`` produces a completely self-contained HTML file — no CDN,
no server, works offline and in air-gapped environments.


Architecture Overview
---------------------

::

   plot() / df.glyphx.* / from_prompt()
              │
              ▼
           Figure
         ┌──────────────────────┐
         │  Axes   ←  Series   │
         │  scale  ←  data     │
         │  grid   ←  SVG      │
         └──────────────────────┘
              │
              ▼
        render_svg()
              │
         ┌────┴────┐
         │ inject  │  (ARIA, tabindex, title/desc)
         │  aria   │
         └────┬────┘
              ▼
     show() / save() / share()

All chart output is plain SVG — renderable by any browser, email client, or
static file server without JavaScript until the interactive HTML wrapper is applied.
