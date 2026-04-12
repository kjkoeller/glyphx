"""
GlyphX SunburstSeries — multi-ring hierarchical pie chart.

A sunburst shows hierarchical data as concentric rings, each ring
representing one level of the hierarchy.  It is the natural companion
to the TreemapSeries and is currently a Plotly-exclusive feature.

    from glyphx import Figure
    from glyphx.sunburst import SunburstSeries

    fig = Figure(width=550, height=550, auto_display=False)
    fig.add(SunburstSeries(
        labels=["Total", "Sales", "APAC", "EMEA", "Engineering", "Marketing"],
        parents=["",      "Total","Sales", "Sales", "Total",       "Total"],
        values= [0,        0,      4200,    3100,    2800,          1500],
    ))
    fig.show()
"""
from __future__ import annotations

import math
from collections import defaultdict

from .colormaps import apply_colormap, colormap_colors
from .utils import svg_escape, _format_tick


class SunburstSeries:
    """
    Multi-ring sunburst chart.

    The root node (parent == ``""``) is drawn as the centre circle.
    Each subsequent ring represents one level of the hierarchy.

    Args:
        labels:         Node labels (unique identifiers).
        parents:        Parent label for each node.  Root node has ``""``.
        values:         Numeric value for each leaf node.  Internal nodes
                        can be 0 — their size is auto-summed from children.
        colors:         Per-label hex colors.  If ``None``, ``cmap`` is used.
        cmap:           Colormap for auto-coloring (default ``"viridis"``).
        inner_radius:   Inner radius of the first ring (default 40 px).
        ring_width:     Width of each ring in pixels (default 60).
        padding_angle:  Gap between segments in degrees (default 1.0).
        show_labels:    Render text inside each segment.
        min_label_arc:  Minimum arc length in px to show a label.
        label:          Legend label (unused but kept for API consistency).
    """

    def __init__(
        self,
        labels:        list[str],
        parents:       list[str],
        values:        list[float],
        colors:        list[str] | None = None,
        cmap:          str              = "viridis",
        inner_radius:  float            = 40.0,
        ring_width:    float            = 60.0,
        padding_angle: float            = 1.0,
        show_labels:   bool             = True,
        min_label_arc: float            = 14.0,
        label:         str | None       = None,
    ) -> None:
        if len(labels) != len(parents) or len(labels) != len(values):
            raise ValueError(
                "labels, parents, and values must all have the same length."
            )

        self.labels        = labels
        self.parents       = parents
        self.raw_values    = list(values)
        self.cmap          = cmap
        self.inner_radius  = float(inner_radius)
        self.ring_width    = float(ring_width)
        self.padding_angle = float(padding_angle)
        self.show_labels   = show_labels
        self.min_label_arc = float(min_label_arc)
        self.label         = label
        self.css_class     = f"series-{id(self) % 100000}"

        # Build tree
        self._children: dict[str, list[str]] = defaultdict(list)
        self._value:    dict[str, float]      = {}
        self._color:    dict[str, str]        = {}

        for lbl, par, val in zip(labels, parents, values):
            self._children[par].append(lbl)
            self._value[lbl] = float(val)

        # Find root
        self._root = next(lbl for lbl, par in zip(labels, parents) if par == "")

        # Sum internal node values bottom-up
        self._summed: dict[str, float] = {}
        self._sum_tree(self._root)

        # Assign colors to top-level children (auto or explicit)
        top_children = self._children.get(self._root, [])
        if colors:
            color_map = dict(zip(labels, colors))
            self._base_colors = {lbl: color_map.get(lbl, "#888") for lbl in top_children}
        else:
            palette = colormap_colors(cmap, max(len(top_children), 1))
            self._base_colors = dict(zip(top_children, palette))

        # x/y stubs (sunburst is axis-free)
        self.x = None
        self.y = None

    def _sum_tree(self, node: str) -> float:
        children = self._children.get(node, [])
        if not children:
            s = self._value.get(node, 0.0)
        else:
            s = sum(self._sum_tree(c) for c in children)
            if self._value.get(node, 0.0) > 0:
                s = self._value[node]  # explicit value overrides sum
        self._summed[node] = s
        return s

    def _get_color(self, node: str, parent: str) -> str:
        """Inherit/derive color from top-level ancestor."""
        if node in self._base_colors:
            return self._base_colors[node]
        if parent in self._base_colors:
            return self._base_colors[parent]
        # Walk up to find base color
        for top, col in self._base_colors.items():
            if self._is_descendant(node, top):
                # Lighten slightly for depth
                return col
        return "#888888"

    def _is_descendant(self, node: str, ancestor: str) -> bool:
        visited: set[str] = set()
        cur = node
        parent_map = dict(zip(self.labels, self.parents))
        while cur and cur not in visited:
            visited.add(cur)
            if cur == ancestor:
                return True
            cur = parent_map.get(cur, "")
        return False

    @staticmethod
    def _arc_path(cx: float, cy: float, r_inner: float, r_outer: float,
                  a_start: float, a_end: float) -> str:
        """SVG path for an annular sector (ring segment)."""
        def pt(r: float, a: float):
            rad = math.radians(a)
            return cx + r * math.cos(rad), cy + r * math.sin(rad)

        large = 1 if (a_end - a_start) > 180 else 0
        x1o, y1o = pt(r_outer, a_start)
        x2o, y2o = pt(r_outer, a_end)
        x1i, y1i = pt(r_inner, a_end)
        x2i, y2i = pt(r_inner, a_start)

        return (
            f"M {x1o:.2f},{y1o:.2f} "
            f"A {r_outer:.2f},{r_outer:.2f} 0 {large},1 {x2o:.2f},{y2o:.2f} "
            f"L {x1i:.2f},{y1i:.2f} "
            f"A {r_inner:.2f},{r_inner:.2f} 0 {large},0 {x2i:.2f},{y2i:.2f} "
            "Z"
        )

    def to_svg(self, ax: object = None) -> str:   # type: ignore[override]
        if ax is None:
            cx, cy = 275, 275
            font, tc = "sans-serif", "#000"
        else:
            cx = ax.width  // 2   # type: ignore
            cy = ax.height // 2   # type: ignore
            font = ax.theme.get("font", "sans-serif")  # type: ignore
            tc   = ax.theme.get("text_color", "#000")  # type: ignore

        elements: list[str] = []

        # Centre dot / root label
        cr = self.inner_radius * 0.6
        root_total = self._summed[self._root]
        root_lbl   = self.labels[self.labels.index(self._root)] if self._root in self.labels else ""
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="{cr:.1f}" '
            f'fill="#f0f0f0" stroke="#ccc" stroke-width="1"/>'
        )
        if root_lbl:
            elements.append(
                f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" '
                f'font-size="11" font-family="{font}" fill="{tc}" font-weight="600">'
                f'{svg_escape(root_lbl)}</text>'
            )

        # BFS to render rings level by level
        from collections import deque
        queue: deque[tuple[str, str, float, float, float, int]] = deque()
        # (node, parent, angle_start, angle_end, depth)
        top_children = self._children.get(self._root, [])
        angle_per_val = (360.0 - self.padding_angle * len(top_children)) / root_total if root_total else 0
        cur_angle = -90.0  # start at top

        for child in top_children:
            span = self._summed[child] * angle_per_val
            queue.append((child, self._root, cur_angle, cur_angle + span, 1))
            cur_angle += span + self.padding_angle

        while queue:
            node, parent, a_start, a_end, depth = queue.popleft()
            r_inner = self.inner_radius + (depth - 1) * self.ring_width
            r_outer = r_inner + self.ring_width - 1

            color = self._get_color(node, parent)

            # Slightly lighten for deeper levels
            if depth > 1:
                opacity = max(0.55, 1.0 - depth * 0.12)
                fill_attr = f'fill="{color}" fill-opacity="{opacity:.2f}"'
            else:
                fill_attr = f'fill="{color}"'

            path = self._arc_path(cx, cy, r_inner, r_outer, a_start, a_end)
            val  = self._summed[node]
            tooltip = (
                f'data-label="{svg_escape(node)}" '
                f'data-value="{svg_escape(_format_tick(val))}"'
            )
            elements.append(
                f'<path class="glyphx-point {self.css_class}" '
                f'd="{path}" {fill_attr} stroke="#fff" stroke-width="0.8" '
                f'{tooltip}/>'
            )

            # Label — only if arc is wide enough
            arc_len = math.radians(a_end - a_start) * (r_inner + r_outer) / 2
            if self.show_labels and arc_len >= self.min_label_arc:
                mid_rad = math.radians((a_start + a_end) / 2)
                mid_r   = (r_inner + r_outer) / 2
                lx = cx + mid_r * math.cos(mid_rad)
                ly = cy + mid_r * math.sin(mid_rad)
                font_sz = max(8, min(12, int(arc_len / 6)))
                # Truncate long labels
                display_lbl = node if len(node) <= 12 else node[:10] + "…"
                elements.append(
                    f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                    f'dominant-baseline="middle" font-size="{font_sz}" '
                    f'font-family="{font}" fill="#fff" '
                    f'transform="rotate({(a_start+a_end)/2+90},{lx:.1f},{ly:.1f})">'
                    f'{svg_escape(display_lbl)}</text>'
                )

            # Enqueue children
            children = self._children.get(node, [])
            if children and val > 0:
                child_angle_per = (
                    (a_end - a_start - self.padding_angle * len(children))
                    / val
                )
                cur = a_start
                for ch in children:
                    ch_span = self._summed[ch] * child_angle_per
                    queue.append((ch, node, cur, cur + ch_span, depth + 1))
                    cur += ch_span + self.padding_angle

        return "\n".join(elements)
