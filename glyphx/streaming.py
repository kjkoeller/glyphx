"""
GlyphX Streaming / Real-time series.

Accepts a Python generator or callable that yields new values,
and re-renders the chart in place - in Jupyter via IPython display,
or in any environment by returning the latest SVG string.

No server, no Dash, no external process.

    from glyphx import Figure
    from glyphx.streaming import StreamingSeries
    import random, time

    fig = Figure(title="Live Sensor", auto_display=False)
    stream = StreamingSeries(max_points=60, color="#1f77b4", label="Sensor A")
    fig.add(stream)

    # Jupyter: re-renders each iteration
    with stream.live(fig, fps=10) as s:
        for _ in range(200):
            s.push(random.gauss(50, 5))

    # Manual control
    stream.push(42.0)
    svg = fig.render_svg()
"""
from __future__ import annotations

import time
from collections import deque

import numpy as np

from ._typing import AxesLike
from .series import BaseSeries
from .utils import has_data, svg_escape


class StreamingSeries(BaseSeries):
    """
    Sliding-window line series for real-time / streaming data.

    Args:
        max_points:  Maximum number of data points kept in the window.
        color:       Line color.
        label:       Legend label.
        line_width:  Stroke width.
        show_points: Draw a dot at each data point.
    """

    def __init__(
        self,
        max_points: int = 100,
        color: str | None = None,
        label: str | None = None,
        line_width: float = 2.0,
        show_points: bool = False,
    ) -> None:
        """
        Set up the rolling buffer that backs the stream.

        ``max_points`` becomes the deque's ``maxlen``, so old samples fall off
        the front automatically and the series never grows without bound.
        """
        self._buffer: deque[float] = deque(maxlen=max_points)
        self.max_points = max_points
        self.line_width = line_width
        self.show_points = show_points
        self._tick = 0

        super().__init__(x=[], y=[], color=color or "#1f77b4", label=label)

    # Data push

    def push(self, value: float) -> StreamingSeries:
        """
        Append a new value to the stream.

        Updates ``self.x`` and ``self.y`` so the parent Figure re-renders
        correctly on the next ``fig.render_svg()`` call.

        Returns ``self`` for chaining::

            stream.push(42.0).push(43.5)

        Args:
            value: New data value.
        """
        self._buffer.append(float(value))
        self._tick += 1
        self.x = list(range(
            self._tick - len(self._buffer),
            self._tick,
        ))
        self.y = list(self._buffer)
        # Clear any cached categorical mapping
        for attr in ("_numeric_x", "_x_categories"):
            if hasattr(self, attr):
                delattr(self, attr)
        return self

    def push_many(self, values: list[float] | np.ndarray) -> StreamingSeries:
        """Push multiple values at once. Returns ``self``."""
        for v in values:
            self.push(float(v))
        return self

    def reset(self) -> StreamingSeries:
        """Clear the buffer and reset the tick counter. Returns ``self``."""
        self._buffer.clear()
        self._tick = 0
        self.x = []
        self.y = []
        return self

    # SVG rendering

    def to_svg(self, ax: AxesLike, use_y2: bool = False) -> str:
        """Draw the current buffer contents as a line."""
        if not has_data(self.x) or not has_data(self.y):
            return ""

        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y
        elements: list[str] = []

        points = " ".join(
            f"{ax.scale_x(x):.1f},{scale_y(y):.1f}"
            for x, y in zip(self.x, self.y)
        )
        elements.append(
            f'<polyline class="{self.css_class}" fill="none" '
            f'stroke="{self.color}" stroke-width="{self.line_width}" '
            f'points="{points}"/>'
        )

        if self.show_points:
            for x, y in zip(self.x, self.y):
                elements.append(
                    f'<circle class="glyphx-point {self.css_class}" '
                    f'cx="{ax.scale_x(x):.1f}" cy="{scale_y(y):.1f}" '
                    f'r="3" fill="{self.color}" '
                    f'data-x="{x}" data-y="{y:.3g}" '
                    f'data-label="{svg_escape(self.label or "")}"/>'
                )

        return "\n".join(elements)

    # Live display context manager

    def live(self, fig: object, fps: float = 10.0) -> _LiveContext:
        """
        Context manager for live display in Jupyter.

        Usage::

            with stream.live(fig, fps=10) as s:
                for value in sensor_generator():
                    s.push(value)

        Args:
            fig: The :class:`~glyphx.Figure` containing this series.
            fps: Target frames per second (throttles re-renders).

        Returns:
            Context manager that yields ``self``.
        """
        return _LiveContext(self, fig, fps)


class _LiveContext:
    """Internal context manager for ``StreamingSeries.live()``."""

    def __init__(self, stream: StreamingSeries, fig: object, fps: float) -> None:
        """Hold the stream, its figure, and the file to write each refresh to."""
        self._stream    = stream
        self._fig       = fig
        self._interval  = 1.0 / fps
        self._last_draw = 0.0

    def __enter__(self) -> _LiveContext:
        """Enter the live block. Returns ``self`` so it can be bound with ``as``."""
        return self

    def push(self, value: float) -> None:
        """Push a value and re-render if enough time has elapsed."""
        self._stream.push(value)
        now = time.monotonic()
        if now - self._last_draw >= self._interval:
            self._render()
            self._last_draw = now

    def _render(self) -> None:
        """
        Re-render the figure to disk, swallowing any error.

        A failed frame should not kill a long-running feed, so this keeps going
        and the next refresh gets another attempt.
        """
        try:
            from IPython.display import SVG, clear_output, display
            clear_output(wait=True)
            display(SVG(self._fig.render_svg()))
        except Exception:
            pass

    def __exit__(self, *_: object) -> None:
        """Render one final frame on the way out, so the file reflects the last data."""
        self._render()
