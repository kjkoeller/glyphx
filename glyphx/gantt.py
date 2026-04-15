"""
GlyphX GanttSeries — project timeline / Gantt chart.

The only Python plotting library with a native Gantt chart is Plotly
(``px.timeline()``).  Matplotlib requires complex manual assembly.
Seaborn has nothing.

GlyphX's ``GanttSeries`` renders horizontal task bars from start-to-end
dates with optional colour-coding by group, milestone markers, and
dependency arrows — all as pure SVG with zero external dependencies.

    from glyphx import Figure
    from glyphx.gantt import GanttSeries
    from datetime import date

    tasks = [
        {"task": "Design",   "start": date(2025,1,6),  "end": date(2025,1,17),  "group": "Phase 1"},
        {"task": "Backend",  "start": date(2025,1,20), "end": date(2025,2,14),  "group": "Phase 2"},
        {"task": "Frontend", "start": date(2025,1,27), "end": date(2025,2,21),  "group": "Phase 2"},
        {"task": "Testing",  "start": date(2025,2,17), "end": date(2025,2,28),  "group": "Phase 3"},
        {"task": "Launch",   "start": date(2025,3,3),  "end": date(2025,3,3),   "group": "Phase 3",
         "milestone": True},
    ]

    fig = Figure(width=860, height=400, auto_display=False)
    fig.add(GanttSeries(tasks, group_colors={"Phase 1": "#2563eb",
                                              "Phase 2": "#16a34a",
                                              "Phase 3": "#dc2626"}))
    fig.show()
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np

from .series    import BaseSeries
from .colormaps import colormap_colors
from .utils     import svg_escape, _format_tick


def _to_date(v) -> date:
    """Coerce str / datetime / date to date."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                pass
    raise ValueError(f"Cannot parse date: {v!r}")


def _date_to_epoch(d: date) -> int:
    """Days since 1970-01-01 (consistent with pandas Timestamp.toordinal)."""
    return (d - date(1970, 1, 1)).days


class GanttSeries(BaseSeries):
    """
    Gantt / project timeline chart.

    Each task is one horizontal bar spanning from ``start`` to ``end``.
    Milestones (single-day events with ``"milestone": True``) are rendered
    as diamond markers instead of bars.

    Args:
        tasks:          List of task dicts, each with keys:

                        - ``"task"``      (str)  — display label
                        - ``"start"``     (date|str) — bar left edge
                        - ``"end"``       (date|str) — bar right edge
                        - ``"group"``     (str, optional) — colour group
                        - ``"milestone"`` (bool, optional) — diamond marker
                        - ``"tooltip"``   (str, optional) — custom tooltip text
                        - ``"progress"``  (float 0-1, optional) — fill fraction

        group_colors:   ``{group_name: hex_color}`` mapping.  Auto-assigned
                        from ``cmap`` if not provided.
        cmap:           Colormap for auto-assigned group colours.
        bar_height:     Pixel height of each task bar (default 18).
        row_padding:    Pixel gap between task rows (default 6).
        show_today:     Draw a vertical line at today's date.
        today_color:    Color of the today marker.
        show_grid:      Draw vertical date-grid lines.
        label:          Series legend label.
    """

    def __init__(
        self,
        tasks: list[dict[str, Any]],
        group_colors: dict[str, str] | None = None,
        cmap:         str                   = "viridis",
        bar_height:   int                   = 20,
        row_padding:  int                   = 6,
        show_today:   bool                  = True,
        today_color:  str                   = "#ef4444",
        show_grid:    bool                  = True,
        label:        str | None            = None,
    ) -> None:
        self.tasks       = tasks
        self.bar_height  = int(bar_height)
        self.row_padding = int(row_padding)
        self.show_today  = show_today
        self.today_color = today_color
        self.show_grid   = show_grid
        self.css_class   = f"series-{id(self) % 100000}"

        # Parse all dates
        self._starts = [_to_date(t["start"]) for t in tasks]
        self._ends   = [_to_date(t["end"])   for t in tasks]

        # Date range for the whole chart
        self._d_min = min(self._starts)
        self._d_max = max(self._ends)
        # Add 5% padding on each side
        span_days   = max((_to_date(t["end"]) - _to_date(t["start"])).days for t in tasks)
        pad         = max(3, int((_date_to_epoch(self._d_max) - _date_to_epoch(self._d_min)) * 0.04))
        self._d_min = date.fromordinal(self._d_min.toordinal() - pad)
        self._d_max = date.fromordinal(self._d_max.toordinal() + pad)

        # Colour assignment
        groups = list(dict.fromkeys(t.get("group", "") for t in tasks))
        groups = [g for g in groups if g]
        if group_colors:
            self._group_colors = dict(group_colors)
        elif groups:
            palette = colormap_colors(cmap, max(len(groups), 2))
            self._group_colors = dict(zip(groups, palette))
        else:
            self._group_colors = {}

        self._default_color = colormap_colors(cmap, 2)[0]

        # BaseSeries stubs — axis-free rendering
        super().__init__(x=None, y=None, color=self._default_color, label=label)

    # ------------------------------------------------------------------
    def to_svg(self, ax: object, use_y2: bool = False) -> str:  # type: ignore
        w     = getattr(ax, "width",   800)
        h     = getattr(ax, "height",  400)
        pad_l = getattr(ax, "padding", 50) + 80  # extra room for labels
        pad_r = getattr(ax, "padding", 50) + (130 if self._group_colors else 10)
        pad_t = getattr(ax, "padding", 50)
        pad_b = getattr(ax, "padding", 50)
        font  = ax.theme.get("font", "sans-serif")   # type: ignore
        tc    = ax.theme.get("text_color", "#000")   # type: ignore
        gc    = ax.theme.get("grid_color", "#ddd")   # type: ignore

        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        n_tasks  = len(self.tasks)
        row_h    = min(self.bar_height + self.row_padding,
                       plot_h // max(n_tasks, 1))
        bar_h    = max(8, row_h - self.row_padding)

        # Date → pixel
        epoch_min = _date_to_epoch(self._d_min)
        epoch_max = _date_to_epoch(self._d_max)
        span      = epoch_max - epoch_min or 1

        def dx(d: date) -> float:
            return pad_l + ((_date_to_epoch(d) - epoch_min) / span) * plot_w

        elements: list[str] = []

        # ── Grid lines (monthly) ─────────────────────────────────────
        if self.show_grid:
            cur = date(self._d_min.year, self._d_min.month, 1)
            while cur <= self._d_max:
                gx = dx(cur)
                elements.append(
                    f'<line x1="{gx:.1f}" x2="{gx:.1f}" '
                    f'y1="{pad_t}" y2="{h - pad_b}" '
                    f'stroke="{gc}" stroke-width="1" stroke-dasharray="3,3"/>'
                )
                # Month label
                elements.append(
                    f'<text x="{gx + 3:.1f}" y="{pad_t - 6}" '
                    f'font-size="9" font-family="{font}" fill="{tc}" opacity="0.6">'
                    f'{cur.strftime("%b %Y")}</text>'
                )
                # Advance to next month
                m = cur.month + 1
                y = cur.year + (m - 1) // 12
                cur = date(y, (m - 1) % 12 + 1, 1)

        # ── Task bars ────────────────────────────────────────────────
        for i, task in enumerate(self.tasks):
            row_y   = pad_t + i * row_h
            bar_y   = row_y + (row_h - bar_h) // 2
            start   = self._starts[i]
            end     = self._ends[i]
            x_start = dx(start)
            x_end   = dx(end)
            bar_w   = max(x_end - x_start, 4)

            group   = task.get("group", "")
            color   = self._group_colors.get(group, self._default_color)
            is_mile = task.get("milestone", False)
            prog    = task.get("progress")
            tip_txt = task.get("tooltip") or (
                f"{task['task']}: {start.isoformat()} → {end.isoformat()}"
            )

            # Task label on left
            label_x = pad_l - 6
            elements.append(
                f'<text x="{label_x:.1f}" y="{bar_y + bar_h//2 + 4:.1f}" '
                f'text-anchor="end" font-size="11" '
                f'font-family="{font}" fill="{tc}">'
                f'{svg_escape(str(task["task"]))}</text>'
            )

            if is_mile:
                # Diamond milestone marker
                cx = (x_start + x_end) / 2
                cy = bar_y + bar_h / 2
                r  = bar_h * 0.55
                pts = (f"{cx:.1f},{cy - r:.1f} {cx + r:.1f},{cy:.1f} "
                       f"{cx:.1f},{cy + r:.1f} {cx - r:.1f},{cy:.1f}")
                elements.append(
                    f'<polygon class="glyphx-point {self.css_class}" '
                    f'points="{pts}" fill="{color}" '
                    f'stroke="{color}" stroke-width="1.5" '
                    f'data-label="{svg_escape(tip_txt)}"/>'
                )
            else:
                # Bar
                elements.append(
                    f'<rect class="glyphx-point {self.css_class}" '
                    f'x="{x_start:.1f}" y="{bar_y}" '
                    f'width="{bar_w:.1f}" height="{bar_h}" '
                    f'fill="{color}" rx="3" '
                    f'data-label="{svg_escape(tip_txt)}"/>'
                )
                # Progress overlay (lighter fill up to progress fraction)
                if prog is not None:
                    prog_w = bar_w * max(0, min(1, float(prog)))
                    elements.append(
                        f'<rect x="{x_start:.1f}" y="{bar_y}" '
                        f'width="{prog_w:.1f}" height="{bar_h}" '
                        f'fill="#ffffff" fill-opacity="0.3" rx="3"/>'
                    )
                    # Progress label
                    elements.append(
                        f'<text x="{x_start + bar_w/2:.1f}" y="{bar_y + bar_h/2 + 4:.1f}" '
                        f'text-anchor="middle" font-size="9" '
                        f'font-family="{font}" fill="#fff" opacity="0.9">'
                        f'{int(float(prog)*100)}%</text>'
                    )

        # ── Today line ───────────────────────────────────────────────
        if self.show_today:
            today = date.today()
            if self._d_min <= today <= self._d_max:
                tx = dx(today)
                elements.append(
                    f'<line x1="{tx:.1f}" x2="{tx:.1f}" '
                    f'y1="{pad_t}" y2="{h - pad_b}" '
                    f'stroke="{self.today_color}" stroke-width="2" '
                    f'stroke-dasharray="6,3" opacity="0.85"/>'
                )
                elements.append(
                    f'<text x="{tx + 4:.1f}" y="{pad_t + 12}" '
                    f'font-size="9" font-family="{font}" '
                    f'fill="{self.today_color}" font-weight="600">Today</text>'
                )

        # ── Group legend ─────────────────────────────────────────────
        if self._group_colors:
            lx  = w - pad_r + 12
            ly  = pad_t
            for k, (grp, col) in enumerate(self._group_colors.items()):
                gy = ly + k * 20
                elements.append(
                    f'<rect x="{lx}" y="{gy}" width="12" height="12" '
                    f'fill="{col}" rx="2"/>'
                )
                elements.append(
                    f'<text x="{lx + 16}" y="{gy + 10}" font-size="11" '
                    f'font-family="{font}" fill="{tc}">'
                    f'{svg_escape(grp)}</text>'
                )

        return "\n".join(elements)
