"""
GlyphX theme definitions.

Each theme is a dictionary with keys:
  colors       – ordered list of series colors
  axis_color   – stroke color for axis lines
  grid_color   – stroke color for grid lines
  font         – font-family string
  background   – canvas background fill
  text_color   – default text fill color
"""

themes = {
    "default": {
        "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                   "#8c564b", "#e377c2", "#7f7f7f"],
        "axis_color": "#333",
        "grid_color": "#ddd",
        "font": "sans-serif",
        "background": "#ffffff",
        "text_color": "#000000",
    },
    "dark": {
        "colors": ["#8ecae6", "#ffb703", "#219ebc", "#fb8500", "#d62828",
                   "#a8dadc", "#f4a261", "#e9c46a"],
        "axis_color": "#cccccc",
        "grid_color": "#444444",
        "font": "sans-serif",
        "background": "#1e1e1e",
        "text_color": "#ffffff",
    },
    # Okabe-Ito palette — actual scientific standard for colorblind safety.
    # Safe for deuteranopia, protanopia, and tritanopia.
    "colorblind": {
        "colors": ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
                   "#0072B2", "#D55E00", "#CC79A7", "#000000"],
        "axis_color": "#000000",
        "grid_color": "#bbbbbb",
        "font": "sans-serif",
        "background": "#ffffff",
        "text_color": "#000000",
    },
    "monochrome": {
        "colors": ["#111111", "#333333", "#555555", "#777777",
                   "#999999", "#bbbbbb", "#dddddd"],
        "axis_color": "#111111",
        "grid_color": "#cccccc",
        "font": "sans-serif",
        "background": "#ffffff",
        "text_color": "#000000",
    },
    "pastel": {
        "colors": ["#aec7e8", "#ffbb78", "#98df8a", "#ff9896",
                   "#c5b0d5", "#c49c94", "#f7b6d2", "#c7c7c7"],
        "axis_color": "#444444",
        "grid_color": "#cccccc",
        "font": "sans-serif",
        "background": "#f9f9f9",
        "text_color": "#222222",
    },
    "warm": {
        "colors": ["#e63946", "#f4a261", "#e9c46a", "#2a9d8f",
                   "#264653", "#a8dadc", "#457b9d", "#1d3557"],
        "axis_color": "#5c3317",
        "grid_color": "#f0d9c8",
        "font": "Georgia, serif",
        "background": "#fff8f0",
        "text_color": "#3e1f00",
    },
    "ocean": {
        "colors": ["#03045e", "#0077b6", "#00b4d8", "#90e0ef",
                   "#caf0f8", "#48cae4", "#023e8a", "#0096c7"],
        "axis_color": "#023e8a",
        "grid_color": "#caf0f8",
        "font": "sans-serif",
        "background": "#f0f8ff",
        "text_color": "#03045e",
    },
}
