def grid(figures, cols=2):
    html = "<div style='display: flex; flex-wrap: wrap; gap: 10px;'>"
    for fig in figures:
        html += f"<div style='flex: 1 1 calc(100% / {cols} - 10px)'>{fig.to_svg()}</div>"
    html += "</div>"
    return html