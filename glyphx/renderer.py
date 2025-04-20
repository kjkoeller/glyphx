def render_html(figures, title="glyphx Multi-Chart", inject_tooltip=True):
    from .assets.tooltip import tooltip_js
from .assets.zoom import zoom_js
from .assets.export import export_js
    from .assets.zoom import zoom_js

    charts_html = "\n".join(f'<div class="glyphx-chart">{fig.to_svg(viewbox=True)}</div>' for fig in figures)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{
      font-family: sans-serif;
      padding: 20px;
    }}
    .glyphx-container {{
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
    }}
    .glyphx-chart {{
      flex: 1 1 100%;
      max-width: 100%;
    }}
    svg {{
      width: 100%;
      height: auto;
      border: 1px solid #ccc;
    }}
  </style>
</head>
<body>
  <h2>{title}</h2>
  <div class="glyphx-container">
    {charts_html}
  </div>
  <script>{tooltip_js}</script>
  <script>{zoom_js}</script>
<script>{export_js}</script>
</body>
</html>"""

    return html