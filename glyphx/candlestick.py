"""
GlyphX Candlestick / OHLC chart series.

Standard financial chart showing open, high, low, close for each period.

    from glyphx import Figure
    from glyphx.candlestick import CandlestickSeries

    fig = Figure(title="AAPL — Daily", auto_display=False)
    fig.add(CandlestickSeries(
        dates=["Mon","Tue","Wed","Thu","Fri"],
        open= [150, 153, 149, 155, 158],
        high= [155, 157, 153, 160, 162],
        low=  [148, 151, 146, 154, 156],
        close=[153, 149, 155, 158, 160],
    ))
    fig.show()
"""
from __future__ import annotations

import numpy as np

from .series import BaseSeries
from .utils import svg_escape


class CandlestickSeries(BaseSeries):
    """
    OHLC candlestick chart.

    Args:
        dates:          X-axis labels (e.g. date strings or numbers).
        open:           Opening prices.
        high:           High prices.
        low:            Low prices.
        close:          Closing prices.
        up_color:       Fill color when close ≥ open (bullish).
        down_color:     Fill color when close < open (bearish).
        candle_width:   Fraction of the available slot width (0–1).
        label:          Legend label.
    """

    def __init__(
        self,
        dates: list,
        open: list[float],   # noqa: A002
        high: list[float],
        low: list[float],
        close: list[float],
        up_color: str   = "#26a641",
        down_color: str = "#d73027",
        candle_width: float = 0.6,
        label: str | None = None,
    ) -> None:
        self.dates        = dates
        self.open_prices  = list(open)
        self.high_prices  = list(high)
        self.low_prices   = list(low)
        self.close_prices = list(close)
        self.up_color     = up_color
        self.down_color   = down_color
        self.candle_width = candle_width

        # Build x/y for Axes domain computation
        all_prices = self.high_prices + self.low_prices
        super().__init__(
            x=list(range(len(dates))),
            y=all_prices,
            color=up_color,
            label=label,
        )

        # Register as categorical
        self._x_categories = list(dates)
        self._numeric_x    = [i + 0.5 for i in range(len(dates))]

    def to_svg(self, ax: object, use_y2: bool = False) -> str:
        scale_y  = ax.scale_y2 if use_y2 else ax.scale_y  # type: ignore[union-attr]
        elements: list[str] = []

        # Candle body pixel width
        n       = len(self.dates)
        slot_px = (ax.width - 2 * ax.padding) / n      # type: ignore[union-attr]
        body_px      = slot_px * self.candle_width

        for i, (date, o, h, l, c) in enumerate(zip(
            self.dates,
            self.open_prices, self.high_prices,
            self.low_prices,  self.close_prices,
        )):
            cx    = ax.scale_x(i + 0.5)   # type: ignore[union-attr]
            is_up = c >= o
            color = self.up_color if is_up else self.down_color

            py_o = scale_y(o)
            py_h = scale_y(h)
            py_l = scale_y(l)
            py_c = scale_y(c)

            # Wick (high–low)
            elements.append(
                f'<line x1="{cx}" x2="{cx}" '
                f'y1="{py_h}" y2="{py_l}" '
                f'stroke="{color}" stroke-width="1.5"/>'
            )

            # Body (open–close)
            body_top = min(py_o, py_c)
            body_h   = max(abs(py_o - py_c), 1)    # at least 1px visible
            tooltip  = (
                f'data-x="{svg_escape(str(date))}" '
                f'data-label="{svg_escape(self.label or str(date))}" '
                f'data-value="O:{o} H:{h} L:{l} C:{c}"'
            )
            elements.append(
                f'<rect class="glyphx-point {self.css_class}" '
                f'x="{cx - body_px / 2}" y="{body_top}" '
                f'width="{body_px}" height="{body_h}" '
                f'fill="{color}" {tooltip}/>'
            )

        return "\n".join(elements)
