import numpy as np
from .themes import themes
from .utils import describe_arc
import math

class BaseSeries:
    """
    Base class for all series types. Stores data and optional label/color/title.

    Attributes:
        x (list): X-axis values
        y (list): Y-axis values (if applicable)
        color (str): Color of the series
        label (str): Optional label for tooltips or legend
        title (str): Optional title displayed above the series
    """
    def __init__(self, x, y=None, color=None, label=None, title=None):
        self.x = x
        self.y = y
        self.color = color or "#1f77b4"
        self.label = label
        self.title = title


class LineSeries(BaseSeries):
    """
    Line chart series with optional line style and width.
    """
    def __init__(self, x, y, color=None, label=None, legend=None, linestyle="solid", width=2, title=None):
        super().__init__(x, y, color, label=label or legend, title=title)
        self.linestyle = linestyle
        self.width = width

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        dash = {"solid": "", "dashed": "6,3", "dotted": "2,2", "longdash": "10,5"}.get(self.linestyle, "")
        polyline = " ".join(f"{ax.scale_x(x)},{scale_y(y)}" for x, y in zip(self.x, self.y))

        svg_elements = []

        # 🔥 (NEW) If title is set, draw it above the series
        if self.title:
            mid_x = (ax.padding + ax.width - ax.padding) // 2
            svg_elements.append(
                f'<text x="{mid_x}" y="{ax.padding - 20}" text-anchor="middle" font-size="16" '
                f'font-family="{ax.theme.get("font", "sans-serif")}" fill="{ax.theme.get("text_color", "#000")}">{self.title}</text>'
            )

        # Draw the main polyline
        svg_elements.append(
            f'<polyline fill="none" stroke="{self.color}" stroke-width="{self.width}" stroke-dasharray="{dash}" points="{polyline}"/>'
        )

        # Draw points with tooltips
        tooltip_points = [
            f'<circle class="glyphx-point" cx="{ax.scale_x(x)}" cy="{scale_y(y)}" r="4" fill="{self.color}" '
            f'data-x="{x}" data-y="{y}" data-label="{self.label or ""}"/>'
            for x, y in zip(self.x, self.y)
        ]
        svg_elements.extend(tooltip_points)

        return "\n".join(svg_elements)


class BarSeries(BaseSeries):
    """
    Bar chart series with adjustable width per bar.
    """
    def __init__(self, x, y, color=None, label=None, legend=None, bar_width=0.8, title=None):
        super().__init__(x, y, color, label=label or legend, title=title)
        self.bar_width = bar_width

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        elements = []

        count = len(self.x)
        if count == 0:
            return ""

        # Visual bar width setup
        domain_width = ax._x_domain[1] - ax._x_domain[0]
        step = domain_width / count
        px_step = ax.scale_x(ax._x_domain[0] + step) - ax.scale_x(ax._x_domain[0])
        px_width = px_step * self.bar_width

        # Determine the actual baseline (not hardcoded to 0)
        y_domain = ax._y2_domain if use_y2 else ax._y_domain
        y_baseline_val = min(0, y_domain[0])  # always draw upward from min(0, ymin)
        y0 = scale_y(y_baseline_val)

        for i, (x, y) in enumerate(zip(self.x, self.y)):
            cx = ax.scale_x(x)
            cy = scale_y(y)
            h = abs(cy - y0)
            top = min(cy, y0)
            tooltip = f'data-x="{x}" data-y="{y}" data-label="{self.label or ""}"'
            elements.append(
                f'<rect class="glyphx-point" x="{cx - px_width / 2}" y="{top}" width="{px_width}" height="{h}" '
                f'fill="{self.color}" stroke="#000" {tooltip}/>'
            )

        if self.title:
            elements.append(
                f'<text x="{(ax.width) // 2}" y="20" text-anchor="middle" font-size="16" fill="{ax.theme.get("text_color", "#000")}" font-family="{ax.theme.get("font", "sans-serif")}">{self.title}</text>')

        return "\n".join(elements)


class ScatterSeries(BaseSeries):
    """
    Scatter chart series with adjustable size and marker type.
    """
    def __init__(self, x, y, color=None, label=None, legend=None, size=5, marker="circle", title=None):
        super().__init__(x, y, color, label=label or legend, title=title)
        self.size = size
        self.marker = marker

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        elements = []
        for x, y in zip(self.x, self.y):
            px = ax.scale_x(x)
            py = scale_y(y)
            tooltip = f'data-x="{x}" data-y="{y}" data-label="{self.label or ""}"'
            if self.marker == "square":
                elements.append(f'<rect class="glyphx-point" x="{px - self.size/2}" y="{py - self.size/2}" width="{self.size}" height="{self.size}" fill="{self.color}" {tooltip}/>')
            else:
                elements.append(f'<circle class="glyphx-point" cx="{px}" cy="{py}" r="{self.size}" fill="{self.color}" {tooltip}/>')

        if self.title:
            elements.append(
                f'<text x="{(ax.width) // 2}" y="20" text-anchor="middle" font-size="16" fill="{ax.theme.get("text_color", "#000")}" font-family="{ax.theme.get("font", "sans-serif")}">{self.title}</text>')

        return "\n".join(elements)


class PieSeries(BaseSeries):
    """
    Pie chart series for GlyphX.

    Attributes:
        values (list): The values corresponding to each pie slice.
        labels (list): Optional labels for each slice.
        label_position (str): Either 'inside' or 'outside' for label placement.
        radius (float): Radius of the pie chart.
    """
    def __init__(self, values, labels=None, colors=None, title=None, label_position="outside", radius=80):
        super().__init__(x=None, y=None, color=None, title=title)
        self.values = values
        self.labels = labels
        self.colors = self.colors or ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
        self.label_position = label_position
        self.radius = radius

    def to_svg(self, ax=None):
        """
        Render the PieSeries into SVG <path> elements with dynamic elbow line lengths.

        Args:
            ax (Axes or None): Optional Axes object for sizing.

        Returns:
            str: SVG markup for the pie chart slices and labels.
        """
        if not self.colors:
            self.colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

        elements = []
        total = sum(self.values)

        # Title
        if self.title:
            elements.append(
                f'<text x="{(ax.width) // 2}" y="20" text-anchor="middle" font-size="16" '
                f'fill="{ax.theme.get("text_color", "#000")}" font-family="{ax.theme.get("font", "sans-serif")}">'
                f'{self.title}</text>'
            )

        cx = (ax.width // 2) if ax else 320
        cy = (ax.height // 2) if ax else 240
        r = min(cx, cy) * 0.6  # Shrunk pie

        angle_start = 0

        for i, v in enumerate(self.values):
            angle_end = angle_start + (v / total) * 360
            mid_angle = (angle_start + angle_end) / 2
            rad = math.radians(mid_angle)

            path_data = describe_arc(cx, cy, r, angle_start, angle_end)
            tooltip = f'data-label="{self.labels[i]}" data-value="{v}"' if self.labels else ""

            elements.append(
                f'<path d="{path_data}" fill="{self.colors[i % len(self.colors)]}" stroke="#000" {tooltip}/>'
            )

            if self.labels:
                # Start at edge of pie
                start_x = cx + r * math.cos(rad)
                start_y = cy + r * math.sin(rad)

                # Dynamic elbow distance: longer when closer to vertical
                base_dist = r * 0.15  # Base distance
                dynamic_dist = base_dist + r * 0.2 * abs(math.sin(rad))  # sin() higher near vertical (90°, 270°)

                elbow_x = cx + (r + dynamic_dist) * math.cos(rad)
                elbow_y = cy + (r + dynamic_dist) * math.sin(rad)

                # Final label x shift
                label_shift = 30
                label_x = elbow_x + (label_shift if math.cos(rad) >= 0 else -label_shift)
                label_y = elbow_y

                # Lines
                elements.append(
                    f'<line x1="{start_x}" y1="{start_y}" x2="{elbow_x}" y2="{elbow_y}" stroke="black" stroke-width="1"/>'
                )
                elements.append(
                    f'<line x1="{elbow_x}" y1="{elbow_y}" x2="{label_x}" y2="{label_y}" stroke="black" stroke-width="1"/>'
                )

                # Label text
                text_anchor = "start" if math.cos(rad) >= 0 else "end"
                elements.append(
                    f'<text x="{label_x}" y="{label_y}" text-anchor="{text_anchor}" '
                    f'font-size="12" font-family="sans-serif" fill="#000">{self.labels[i]}</text>'
                )

            angle_start = angle_end

        return "\n".join(elements)


class DonutSeries(BaseSeries):
    """
    Donut (pie with hole) chart series with optional label callouts.

    Attributes:
        values (list): Numeric values for slices
        labels (list): Labels for each slice (optional)
        colors (list): List of colors (optional)
        show_labels (bool): Whether to show labels outside slices
        inner_radius_frac (float): Fractional inner hole size (default 0.5)
    """

    def __init__(self, values, labels=None, colors=None, show_labels=True, hover_animate=True, inner_radius_frac=0.5):
        self.values = values
        self.labels = labels or [str(i) for i in range(len(values))]
        self.colors = colors
        self.show_labels = show_labels
        self.hover_animate = hover_animate
        self.inner_radius_frac = inner_radius_frac

    def to_svg(self, ax=None):
        """
        Render the donut chart to SVG elements.

        Args:
            ax (Axes or None): Unused, included for compatibility.

        Returns:
            str: SVG markup string
        """
        import math

        total = sum(self.values)
        if total == 0:
            return ""

        cx = (ax.width // 2) if ax else 320
        cy = (ax.height // 2) if ax else 240
        max_radius = min(cx, cy) - 40  # Margin for label space

        outer_radius = max_radius
        inner_radius = outer_radius * self.inner_radius_frac

        elements = []
        angle_start = 0
        slices = []

        # Precompute slices
        for v, label in zip(self.values, self.labels):
            angle_span = (v / total) * 360
            slices.append((angle_start, angle_start + angle_span, v, label))
            angle_start += angle_span

        def create_slice(angle1, angle2, color, idx):
            x1 = cx + outer_radius * math.cos(math.radians(angle1))
            y1 = cy + outer_radius * math.sin(math.radians(angle1))
            x2 = cx + outer_radius * math.cos(math.radians(angle2))
            y2 = cy + outer_radius * math.sin(math.radians(angle2))
            large_arc = 1 if angle2 - angle1 > 180 else 0

            path = (
                f"M {x1},{y1} "
                f"A {outer_radius},{outer_radius} 0 {large_arc},1 {x2},{y2} "
                f"L {cx},{cy} Z"
            )
            color_style = self.colors[idx] if self.colors and idx < len(self.colors) else f"hsl({idx * 45 % 360},70%,50%)"
            animate_class = "glyphx-point" if self.hover_animate else ""

            return f'<path d="{path}" fill="{color_style}" class="{animate_class}" data-label="{slices[idx][3]}" data-value="{slices[idx][2]}"/>'

        def create_label(angle1, angle2, label_text):
            mid_angle = (angle1 + angle2) / 2
            label_radius = outer_radius + 20
            lx = cx + label_radius * math.cos(math.radians(mid_angle))
            ly = cy + label_radius * math.sin(math.radians(mid_angle))

            line_x = cx + outer_radius * math.cos(math.radians(mid_angle))
            line_y = cy + outer_radius * math.sin(math.radians(mid_angle))

            line = f'<line x1="{line_x}" y1="{line_y}" x2="{lx}" y2="{ly}" stroke="#333" />'
            text = f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="12" font-family="sans-serif">{label_text}</text>'
            return line + "\n" + text

        # Try to auto-fit: reduce outer radius if labels would overflow
        if self.show_labels:
            labels_wide = any(len(label) > 10 for label in self.labels)
            if labels_wide:
                outer_radius = max_radius * 0.75
            else:
                outer_radius = max_radius * 0.9
            inner_radius = outer_radius * self.inner_radius_frac

        # Create SVG paths
        for idx, (a1, a2, v, label) in enumerate(slices):
            elements.append(create_slice(a1, a2, color=self.colors[idx] if self.colors else None, idx=idx))
            if self.show_labels:
                elements.append(create_label(a1, a2, label))

        # Draw center hole
        elements.append(f'<circle cx="{cx}" cy="{cy}" r="{inner_radius}" fill="{self.theme.get("background", "#ffffff")}" />')

        return "\n".join(elements)



class HistogramSeries(BaseSeries):
    """
    Histogram chart for frequency distribution of numeric data.
    """
    def __init__(self, data, bins=10, color=None, label=None):
        hist, edges = np.histogram(data, bins=bins)
        x = [(edges[i] + edges[i+1]) / 2 for i in range(len(hist))]
        y = hist.tolist()
        super().__init__(x, y, color or "#1f77b4", label)
        self.edges = edges

    def to_svg(self, ax, use_y2=False):
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        elements = []
        width = (ax.scale_x(self.edges[1]) - ax.scale_x(self.edges[0])) * 0.9
        for x, y in zip(self.x, self.y):
            cx = ax.scale_x(x)
            cy = scale_y(y)
            y0 = scale_y(0)
            h = abs(y0 - cy)
            top = min(y0, cy)
            tooltip = f'data-x="{x}" data-y="{y}" data-label="{self.label or ""}"'
            elements.append(f'<rect class="glyphx-point" x="{cx - width/2}" y="{top}" width="{width}" height="{h}" fill="{self.color}" {tooltip}/>')
        return "\n".join(elements)


class BoxPlotSeries(BaseSeries):
    """
    Box plot series showing Q1, Q2, Q3 and whiskers.
    """
    def __init__(self, data, color="#1f77b4", label=None, width=20):
        self.data = np.array(data)
        self.color = color
        self.label = label
        self.width = width

    def to_svg(self, ax, use_y2=False):
        q1 = np.percentile(self.data, 25)
        q2 = np.percentile(self.data, 50)
        q3 = np.percentile(self.data, 75)
        iqr = q3 - q1
        whisker_low = max(min(self.data), q1 - 1.5 * iqr)
        whisker_high = min(max(self.data), q3 + 1.5 * iqr)
        center_x = ax.scale_x(0.5)
        scale_y = ax.scale_y2 if use_y2 else ax.scale_y
        tooltip = f'data-label="{self.label or ""}" data-q1="{q1}" data-q2="{q2}" data-q3="{q3}"'
        elements = [
            f'<line x1="{center_x}" x2="{center_x}" y1="{scale_y(whisker_low)}" y2="{scale_y(q1)}" stroke="{self.color}"/>',
            f'<line x1="{center_x}" x2="{center_x}" y1="{scale_y(q3)}" y2="{scale_y(whisker_high)}" stroke="{self.color}"/>',
            f'<rect class="glyphx-point" x="{center_x - self.width/2}" y="{scale_y(q3)}" width="{self.width}" height="{abs(scale_y(q3)-scale_y(q1))}" fill="{self.color}" fill-opacity="0.4" stroke="{self.color}" {tooltip}/>',
            f'<line x1="{center_x - self.width/2}" x2="{center_x + self.width/2}" y1="{scale_y(q2)}" y2="{scale_y(q2)}" stroke="{self.color}" stroke-width="2"/>'
        ]
        return "\n".join(elements)


class HeatmapSeries(BaseSeries):
    """
    Heatmap for 2D matrix data. Values are mapped to colors using a colormap.
    """
    def __init__(self, matrix, cmap=None, **kwargs):
        self.matrix = matrix
        self.cmap = cmap or ["#fff", "#ccc", "#999", "#666", "#333"]
        self.kwargs = kwargs

    def to_svg(self, ax, use_y2=False):
        import numpy as np
        svg = []
        rows, cols = len(self.matrix), len(self.matrix[0])
        cw = (ax.width - 2 * ax.padding) / cols
        ch = (ax.height - 2 * ax.padding) / rows
        flat = [v for row in self.matrix for v in row]
        vmin, vmax = min(flat), max(flat)
        for i, row in enumerate(self.matrix):
            for j, val in enumerate(row):
                norm = int((val - vmin) / (vmax - vmin) * (len(self.cmap) - 1))
                color = self.cmap[norm]
                x = ax.padding + j * cw
                y = ax.padding + i * ch
                svg.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="{color}" />')
        return "\n".join(svg)
