def render_html(figures, title="glyphx Multi-Chart", inject_tooltip=True):
    """
    Render a list of glyphx Figures as a full responsive HTML page with interactivity.

    Args:
        figures (list): List of glyphx.Figure objects.
        title (str): Title for the HTML page.
        inject_tooltip (bool): If True, inject JavaScript for hover tooltips.

    Returns:
        str: Complete HTML document as a string.
    """
    from .assets.tooltip import tooltip_js
    from .assets.zoom import zoom_js
    from .assets.export import export_js

    # Render each figure to SVG (with viewBox for responsiveness)
    charts_html = "\n".join(
        f'<div class="glyphx-chart">{fig.to_svg(viewbox=True)}</div>' for fig in figures
    )

    # Build HTML string with embedded SVG and JS
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

# Added legend rendering support
def render_legend(draw, series_list, start_x=10, start_y=10, spacing=20):
    """
    Draws a simple legend for labeled series.

    Parameters:
        draw (ImageDraw.Draw): Drawing context.
        series_list (list): List of series objects with 'label' and 'color'.
        start_x (int): X-coordinate of the legend box.
        start_y (int): Y-coordinate of the legend box.
        spacing (int): Vertical spacing between legend entries.
    """
    y_offset = 0
    for series in series_list:
        label = getattr(series, 'label', None)
        color = getattr(series, 'color', 'black')
        if label:
            draw.rectangle(
                [start_x, start_y + y_offset, start_x + 10, start_y + 10 + y_offset],
                fill=color
            )
            draw.text((start_x + 15, start_y + y_offset), label, fill='black')
            y_offset += spacing
