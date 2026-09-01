"""
GlyphX layout module: Axes scaling, tick/grid rendering, and multi-figure grid layout.
"""

from __future__ import annotations

import datetime as _dt
import math
import warnings

# Datetime helpers

def _is_datetime(val) -> bool:
    """Return True if val is any date/datetime/Timestamp type."""
    try:
        import pandas as pd
        if isinstance(val, (pd.Timestamp, pd.DatetimeTZDtype)):
            return True
    except ImportError:
        pass
    return isinstance(val, (_dt.date, _dt.datetime))


def _to_timestamp(val) -> float:
    """Convert a datetime-like value to a float Unix timestamp (seconds)."""
    try:
        import pandas as pd
        if isinstance(val, pd.Timestamp):
            return val.timestamp()
    except ImportError:
        pass
    # Naive values are read as UTC, not local time.  datetime.timestamp()
    # applies the machine's zone to a naive value while _format_datetime_tick
    # formats in UTC, so the two disagreed by the local offset: a plain
    # date(2024, 1, 5) labelled itself "4 Jan" anywhere east of UTC, and
    # disagreed with a pandas Timestamp for the same wall clock on the same
    # axis (pandas already reads naive as UTC).
    if isinstance(val, _dt.datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=_dt.timezone.utc)
        return val.timestamp()
    if isinstance(val, _dt.date):
        return _dt.datetime(val.year, val.month, val.day,
                            tzinfo=_dt.timezone.utc).timestamp()
    return float(val)


def _format_datetime_tick(ts: float, span_seconds: float) -> str:
    """Format a Unix timestamp as a human-readable date label.

    Chooses the right granularity based on the total time span displayed.
    """
    # utcfromtimestamp() is deprecated from 3.12 and slated for removal.
    dt = _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc)
    if span_seconds <= 3 * 3600:          # ≤ 3 hours → HH:MM
        return dt.strftime("%H:%M")
    if span_seconds <= 3 * 86400:         # ≤ 3 days  → Mon 14:00
        return dt.strftime("%a %H:%M")
    if span_seconds <= 90 * 86400:        # ≤ 90 days → 15 Jan
        # Not "%-d": the no-pad flag is a glibc extension that MSVC rejects
        # with ValueError, so every date axis under 90 days crashed on
        # Windows.  (Windows spells it "%#d"; neither is portable.)
        return f"{dt.day} {dt.strftime('%b')}"
    if span_seconds <= 730 * 86400:       # ≤ 2 years → Jan 2024
        return dt.strftime("%b %Y")
    return dt.strftime("%Y")              # > 2 years → 2024


from .utils import SVG_PRECISION, _format_tick, has_data, is_finite, svg_label


class Axes:
    """
    Manages axis scaling, tick rendering, and series layout within a plot.

    Supports:
    - Dual Y-axes (primary and secondary)
    - Categorical X-axis labels
    - Linear and log-scale axes
    - Configurable tick counts and grid lines
    - Axis title / xlabel / ylabel labels

    Attributes:
        width (int): Plot area width in pixels.
        height (int): Plot area height in pixels.
        padding (int): Space from canvas edge to the plot area.
        show_grid (bool): Whether to render background grid lines.
        theme (dict): Color and font styling dictionary.
        xscale (str): ``"linear"`` or ``"log"``.
        yscale (str): ``"linear"`` or ``"log"``.
        series (list): Series on the primary Y-axis.
        y2_series (list): Series on the secondary Y-axis.
    """

    def __init__(
        self,
        width=600,
        height=400,
        padding=50,
        show_grid=True,
        theme=None,
        legend=None,
        xscale="linear",
        yscale="linear",
        precision=SVG_PRECISION,
    ):
        """
        Set up the plot area, scales and the various tick and span registries.

        Everything data-dependent -- the domains and the scale callables -- stays
        ``None`` until :meth:`finalize` runs, since none of it can be computed
        before the series are known.
        """
        self.width    = width
        self.height   = height
        self.padding  = padding
        self.show_grid = show_grid
        self.theme    = theme or {}
        self.legend_pos = legend
        self.xscale   = xscale
        self.yscale   = yscale
        # Decimal places kept in emitted pixel coordinates. Sub-pixel
        # precision beyond ~2 dp is invisible at any realistic display
        # density but inflates every path in the document.
        self.precision = precision

        self.title   = None
        self.xlabel  = None
        self.ylabel  = None
        self.y2label = None

        self.series    = []
        self.y2_series = []

        # Computed domains (set by finalize())
        self._x_domain  = None
        self._y_domain  = None
        self._y2_domain = None

        # Categorical label mapping (populated by compute_domain)
        self._x_categories = None

        # Custom tick overrides (Matplotlib parity)
        # When set, these override the auto-computed tick values in render_grid.
        self._xticks:       list | None        = None   # explicit x positions
        self._yticks:       list | None        = None   # explicit y positions
        self._xticklabels:  list[str] | None   = None   # override x labels
        self._yticklabels:  list[str] | None   = None   # override y labels
        self._tick_formatter = None                      # callable(value) → str
        self._minor_ticks:  int                = 0      # subdivisions between majors
        self._tick_wrap:    bool               = False   # wrap long x-labels, not rotate
        # Set by Figure.inset_axes() when this Axes is an inset panel; the
        # opaque fill behind it so the parent's grid does not show through.
        self._inset_background: str | None      = None
        # Set by Figure._apply_shared_x() on every cell of a shared-x grid:
        # the unified domain to use instead of this cell's own, and whether
        # to suppress X tick labels (all rows but the bottom one).
        self._x_domain_override: tuple | None   = None
        self._hide_xticklabels: bool            = False
        self._tick_length:  float              = 4.0    # tick mark length px
        self._minor_length: float              = 2.0    # minor tick length px

        # Spine visibility
        self._spines: dict[str, bool] = {
            "left": True, "right": True, "top": False, "bottom": True
        }

        # Shaded bands (axhspan / axvspan)
        self._hspans: list[dict] = []   # horizontal shaded regions
        self._vspans: list[dict] = []   # vertical shaded regions

    # Matplotlib-parity: custom ticks, formatters, spines, spans

    def set_xticks(self, ticks: list, labels: list[str] | None = None) -> Axes:
        """
        Set explicit X-axis tick positions.

        Args:
            ticks:  List of data-space positions where ticks should appear.
            labels: Optional list of strings to display instead of formatted values.
                    Must be the same length as ``ticks``.

        Returns:
            ``self`` for chaining.

        Example::

            ax.set_xticks([0, 25, 50, 75, 100])
            ax.set_xticks([1, 6, 12], labels=["Jan", "Jun", "Dec"])
        """
        self._xticks = list(ticks)
        if labels is not None:
            self._xticklabels = [str(l) for l in labels]
        return self

    def set_yticks(self, ticks: list, labels: list[str] | None = None) -> Axes:
        """
        Set explicit Y-axis tick positions.

        Args:
            ticks:  List of data-space positions.
            labels: Optional display labels (same length as ticks).

        Returns:
            ``self`` for chaining.

        Example::

            ax.set_yticks([0, 1_000_000, 2_000_000], labels=["$0", "$1M", "$2M"])
        """
        self._yticks = list(ticks)
        if labels is not None:
            self._yticklabels = [str(l) for l in labels]
        return self

    def set_xticklabels(self, labels: list[str]) -> Axes:
        """Override X-tick display strings without changing positions."""
        self._xticklabels = [str(l) for l in labels]
        return self

    def set_yticklabels(self, labels: list[str]) -> Axes:
        """Override Y-tick display strings without changing positions."""
        self._yticklabels = [str(l) for l in labels]
        return self

    def set_tick_format(self, formatter) -> Axes:
        """
        Apply a callable formatter to all numeric tick labels.

        The formatter receives a float and must return a string.  It applies
        to both X and Y axes (use ``set_xticklabels`` / ``set_yticklabels``
        to override one axis independently).

        Args:
            formatter: Callable ``(value: float) -> str``.

        Returns:
            ``self`` for chaining.

        Example::

            ax.set_tick_format(lambda v: f"${v:,.0f}")
            ax.set_tick_format(lambda v: f"{v:.1%}")
        """
        self._tick_formatter = formatter
        return self

    def set_y2label(self, label: str) -> Axes:
        """
        Label the secondary (right-hand) Y axis.

        Rendered rotated on the right edge, mirroring ``ylabel``. Only drawn
        when the axes actually has ``y2_series``, so setting it on a
        single-axis chart is a harmless no-op.

        Args:
            label: Text for the right-hand axis.

        Returns:
            ``self`` for chaining.
        """
        self.y2label = label
        return self

    def set_tick_wrap(self, enabled: bool = True) -> Axes:
        """
        Wrap long X-axis tick labels onto a second line instead of rotating.

        Rotation is GlyphX's automatic default once labels would overlap at
        horizontal angle (see ``_should_rotate_xlabels``); this is an
        explicit alternative for when rotated text is harder to read than
        two short lines -- category names and month/quarter labels are the
        common case. The two are mutually exclusive: enabling wrap suppresses
        auto-rotation for this axes.

        Args:
            enabled: ``True`` to wrap, ``False`` to restore the default
                (auto-rotate when labels would otherwise overlap).

        Returns:
            ``self`` for chaining.

        Example::

            ax.set_tick_wrap()   # "Product Engineering" wraps onto two lines
        """
        self._tick_wrap = enabled
        return self

    def set_minor_ticks(self, n: int, length: float = 2.0) -> Axes:
        """
        Draw ``n`` minor tick subdivisions between each pair of major ticks.

        Args:
            n:      Number of minor ticks between major ticks (e.g. 4 gives
                    5 equal sub-intervals).
            length: Minor tick length in pixels.

        Returns:
            ``self`` for chaining.

        Example::

            ax.set_minor_ticks(4)   # quarterly subdivisions on annual axis
        """
        self._minor_ticks  = int(n)
        self._minor_length = float(length)
        return self

    def set_tick_length(self, length: float) -> Axes:
        """Set the major tick mark length in pixels (default: 4)."""
        self._tick_length = float(length)
        return self

    def set_spine_visible(
        self,
        left:   bool = True,
        right:  bool = True,
        top:    bool = False,
        bottom: bool = True,
    ) -> Axes:
        """
        Control which axis spines (border lines) are visible.

        By default the top spine is hidden (matches Matplotlib's ``ax.spines``
        best-practice for clean scientific plots).

        Args:
            left:   Show left (Y) spine.
            right:  Show right (Y2) spine.
            top:    Show top spine.
            bottom: Show bottom (X) spine.

        Returns:
            ``self`` for chaining.

        Example::

            ax.set_spine_visible(top=False, right=False)  # clean minimal look
        """
        self._spines = {"left": left, "right": right, "top": top, "bottom": bottom}
        return self

    def axhspan(
        self,
        ymin: float,
        ymax: float,
        color: str   = "#ffff00",
        alpha: float = 0.20,
        label: str | None = None,
    ) -> Axes:
        """
        Add a horizontal shaded band spanning the full plot width.

        The band is drawn in data-space Y coordinates.  Values outside the
        current Y domain are clipped to the plot boundary.

        Args:
            ymin:  Lower Y data value of the band.
            ymax:  Upper Y data value of the band.
            color: Fill color.
            alpha: Fill opacity 0–1.
            label: Optional legend label.

        Returns:
            ``self`` for chaining.

        Example::

            ax.axhspan(90, 110, color="#22c55e", alpha=0.15, label="Normal range")
        """
        self._hspans.append(dict(ymin=ymin, ymax=ymax, color=color,
                                  alpha=alpha, label=label))
        return self

    def axvspan(
        self,
        xmin,
        xmax,
        color: str   = "#a855f7",
        alpha: float = 0.20,
        label: str | None = None,
    ) -> Axes:
        """
        Add a vertical shaded band spanning the full plot height.

        ``xmin`` / ``xmax`` may be numeric data values or category label
        strings (resolved to their numeric position).

        Args:
            xmin:  Left X data value of the band.
            xmax:  Right X data value of the band.
            color: Fill color.
            alpha: Fill opacity 0–1.
            label: Optional legend label.

        Returns:
            ``self`` for chaining.

        Example::

            ax.axvspan("Jul", "Sep", color="#f59e0b", alpha=0.15, label="Summer")
        """
        self._vspans.append(dict(xmin=xmin, xmax=xmax, color=color,
                                  alpha=alpha, label=label))
        return self

    def _render_spans(self) -> str:
        """Render all axhspan / axvspan regions as SVG rects."""
        if not self._hspans and not self._vspans:
            return ""
        if self.scale_x is None or self.scale_y is None:
            return ""

        pad      = self.padding
        plot_top = pad
        plot_bot = self.height - pad
        plot_lft = pad
        plot_rgt = self.width  - pad

        elements: list[str] = []

        # Horizontal bands
        for span in self._hspans:
            py_lo = max(plot_top, min(plot_bot, self.scale_y(span["ymax"])))
            py_hi = max(plot_top, min(plot_bot, self.scale_y(span["ymin"])))
            h     = py_hi - py_lo
            if h < 0.5:
                continue
            elements.append(
                f'<rect x="{plot_lft}" y="{py_lo:.1f}" '
                f'width="{plot_rgt - plot_lft}" height="{h:.1f}" '
                f'fill="{span["color"]}" fill-opacity="{span["alpha"]}" '
                f'stroke="none"/>'
            )

        # Vertical bands
        for span in self._vspans:
            def _resolve_x(v):
                """
                Turn a span boundary into a numeric x, resolving category names.

                ``axvspan("Feb", "Apr")`` is as valid as passing numbers, so a string is
                looked up against whatever categorical mapping the series registered.
                """
                if isinstance(v, str):
                    for s in self.series + self.y2_series:
                        cats = getattr(s, "_x_categories", None)
                        nxs  = getattr(s, "_numeric_x",   None)
                        if cats and nxs:
                            for cat, nx in zip(cats, nxs):
                                if str(cat) == str(v):
                                    return nx
                return float(v)

            try:
                px_lo = max(plot_lft, min(plot_rgt, self.scale_x(_resolve_x(span["xmin"]))))
                px_hi = max(plot_lft, min(plot_rgt, self.scale_x(_resolve_x(span["xmax"]))))
            except (TypeError, ValueError):
                continue

            w = px_hi - px_lo
            if abs(w) < 0.5:
                continue
            x_left = min(px_lo, px_hi)
            elements.append(
                f'<rect x="{x_left:.1f}" y="{plot_top}" '
                f'width="{abs(w):.1f}" height="{plot_bot - plot_top}" '
                f'fill="{span["color"]}" fill-opacity="{span["alpha"]}" '
                f'stroke="none"/>'
            )

        return "\n".join(elements)

    # Series registration

    def add(self, series, use_y2=False):
        """Proxy for add_series; allows Figure/Axes to share call syntax."""
        self.add_series(series, use_y2=use_y2)

    def add_series(self, series, use_y2=False):
        """
        Register a series on the primary or secondary Y-axis.

        Args:
            series (BaseSeries): Any series with ``.x`` and ``.y`` attributes.
            use_y2 (bool): If True, bind to the right-hand Y-axis.
        """
        if use_y2:
            self.y2_series.append(series)
        else:
            self.series.append(series)

    # Domain computation (non-mutating)

    def compute_domain(self, series_list):
        """
        Compute ``(x_domain, y_domain)`` from a list of series.

        Categorical string X-values are converted to numeric indices.
        The conversion is stored on the series as ``._numeric_x`` so the
        original ``series.x`` is **never mutated**.

        When multiple series each carry different categories (e.g. one bar
        per group from a groupby aggregation), all unique categories are merged
        into a single global ordering so each gets a distinct x position.

        Args:
            series_list (list): Series objects with ``.x`` and ``.y``.

        Returns:
            tuple: ``(x_domain, y_domain)`` each as ``(min, max)`` or
                   ``(None, None)`` if no valid data is found.
        """
        x_vals = []
        y_vals = []

        # Build a global category order across all categorical series so that
        # series each carrying a different single category (e.g. groupby bars)
        # receive unique, non-overlapping x positions.
        global_cats: list = []
        for s in series_list:
            if not hasattr(s, "x") or not has_data(s.x):
                continue
            if isinstance(s.x[0], str) and not _is_datetime(s.x[0]):
                for cat in s.x:
                    if cat not in global_cats:
                        global_cats.append(cat)

        cat_to_pos: dict = {cat: i + 0.5 for i, cat in enumerate(global_cats)}

        for s in series_list:
            if not hasattr(s, "x") or not hasattr(s, "y"):
                continue
            if not has_data(s.x) or not has_data(s.y):
                continue

            # Handle categorical X: store numeric mapping without mutation
            if isinstance(s.x[0], str):
                s._numeric_x    = [cat_to_pos[cat] for cat in s.x]
                s._x_categories = list(s.x)
                numeric_x = s._numeric_x
            elif _is_datetime(s.x[0]):
                # Convert datetime/Timestamp to float epoch seconds
                timestamps = [_to_timestamp(v) for v in s.x]
                s._numeric_x   = timestamps
                s._datetime_x  = True   # flag for tick formatter
                numeric_x = timestamps
            else:
                numeric_x = s.x

            # Missing values (None/NaN/inf) must not participate in the
            # domain: min()/max() would either raise TypeError or stretch
            # the axis to infinity. They are rendered as gaps instead.
            x_vals.extend(v for v in numeric_x if is_finite(v))
            y_vals.extend(v for v in s.y if is_finite(v))

            # Series whose marks have width -- histogram bars span a bin,
            # not a point -- report the extent they actually occupy. Using
            # only the centres lets half the outermost bar hang outside the
            # plot area and over the tick labels.
            extent = getattr(s, "x_extent", None)
            if extent:
                x_vals.extend(v for v in extent if is_finite(v))

        # A log axis is undefined at and below zero. Masking those values
        # (matplotlib's behaviour) keeps the axis range honest; leaving them
        # in silently collapses the real data into a fraction of the canvas.
        if self.xscale == "log":
            x_vals = self._mask_nonpositive(x_vals, "x")
        if self.yscale == "log":
            y_vals = self._mask_nonpositive(y_vals, "y")

        if not has_data(x_vals) or not has_data(y_vals):
            return None, None

        x_domain = (min(x_vals) - 0.5, max(x_vals) + 0.5)

        y_min = min(y_vals)
        y_max = max(y_vals)

        # Series drawn from a zero baseline need 0 inside the domain, or
        # their bars start at a pixel outside the canvas and get clipped.
        # Series opt in with `zero_anchored = True`; the name list is a
        # fallback for third-party series that predate the attribute.
        _zero_anchor_types = ("BarSeries", "HistogramSeries",
                               "BoxPlotSeries", "GroupedBarSeries",
                               "WaterfallSeries", "CountPlotSeries",
                               "StackedBarSeries", "DivergingBarSeries")
        _has_zero_anchor = any(
            getattr(s, "zero_anchored", False)
            or s.__class__.__name__ in _zero_anchor_types
            for s in series_list
        )
        # Bars measure from zero, so zero has to be in the domain whichever
        # way the data runs. Otherwise the baseline sits off-canvas and the
        # bars grow from the wrong edge.  Skipped on a log axis: zero has no
        # position there, and forcing it made y_min 0 and sent log10(0) into
        # a ValueError, so every bar chart on a log Y axis crashed.
        # _mask_nonpositive has already dropped non-positive values, so the
        # remaining bound is safe to take a logarithm of.
        if _has_zero_anchor and self.yscale != "log":
            y_min = min(y_min, 0.0)
            y_max = max(y_max, 0.0)

        _bottom_is_zero = _has_zero_anchor and y_min >= 0

        # Force zero-anchored series to include 0.  Not on a log axis: zero
        # has no position there, and anchoring to it drove y_min to 0 and
        # then log10(0) straight into a ValueError -- so every bar chart on
        # a log Y axis crashed rather than rendering.
        if _has_zero_anchor and self.yscale != "log":
            y_min = min(0, y_min)
            y_max = max(0, y_max)

        # Guard: never pass equal min/max
        if y_min == y_max:
            y_min -= 1
            y_max += 1

        # Add 7% breathing room so data never butts against the axis edge.
        # Bottom pad is skipped when the baseline is zero (bars, histograms).
        if self.yscale == "log":
            # Linear padding takes 1..100 down to -5.93, which log10() can't
            # represent. Pad in log space instead: a fixed fraction of a
            # decade at each end.
            log_lo, log_hi = math.log10(y_min), math.log10(y_max)
            if log_lo == log_hi:
                log_lo -= 0.5
                log_hi += 0.5
            log_pad = (log_hi - log_lo) * 0.07
            y_min = 10 ** (log_lo - log_pad)
            y_max = 10 ** (log_hi + log_pad)
        else:
            _span = y_max - y_min
            PAD   = 0.07
            y_max += _span * PAD
            if not _bottom_is_zero:
                y_min -= _span * PAD

        return x_domain, (y_min, y_max)

    # Scale functions

    def _scale_linear(self, domain_min, domain_max, range_min, range_max):
        """Return a callable that linearly maps domain → pixel range."""
        ndigits = self.precision

        def scaler(value):
            """
            Map one data value onto its pixel position.

            A zero-width domain would divide by zero, so a single-valued axis puts
            everything at the midpoint of the range rather than failing.
            """
            if domain_max == domain_min:
                return round((range_min + range_max) / 2, ndigits)
            return round(
                range_min
                + (value - domain_min) * (range_max - range_min) / (domain_max - domain_min),
                ndigits,
            )
        return scaler

    # TODO: symlog scale. Masking is right for a plain log axis but it
    # throws data away, and people plotting residuals want to see the
    # negatives.
    @staticmethod
    def _mask_nonpositive(values: list, axis: str) -> list:
        """
        Drop values that a log axis cannot represent, warning once.

        Args:
            values (list): Numeric values destined for a log axis.
            axis (str): ``"x"`` or ``"y"``, used in the warning message.

        Returns:
            list: Only the strictly positive values.
        """
        kept = [v for v in values if v > 0]
        dropped = len(values) - len(kept)
        if dropped:
            warnings.warn(
                f"{dropped} non-positive value(s) masked from the log-scaled "
                f"{axis}-axis; log10 is undefined at and below zero. "
                f"Use a linear scale to show them.",
                UserWarning,
                stacklevel=3,
            )
        return kept

    def _scale_log(self, domain_min, domain_max, range_min, range_max):
        """Return a callable that log-maps domain → pixel range."""
        if domain_min <= 0:
            domain_min = 1e-10  # guard against log(0)
        log_min = math.log10(domain_min)
        log_max = math.log10(max(domain_max, domain_min * 10))
        ndigits = self.precision

        def scaler(value):
            """
            Map one data value onto its pixel position on a log axis.

            Non-positive input has no logarithm, so it becomes NaN rather than a
            number -- that routes it through the same ``is_finite`` gates as missing
            data and leaves a gap, instead of silently pinning it to one end.
            """
            if value is None or value <= 0:
                # Undefined on a log axis. Returning NaN routes the value
                # through the same is_finite() gates that handle missing
                # data, so it becomes a gap rather than a point silently
                # placed at the wrong end of the axis.
                return math.nan
            lv = math.log10(value)
            if log_max == log_min:
                return round((range_min + range_max) / 2, ndigits)
            return round(
                range_min + (lv - log_min) * (range_max - range_min) / (log_max - log_min),
                ndigits,
            )
        return scaler

    def _make_scale(self, domain_min, domain_max, range_min, range_max, scale_type):
        """Return the linear or log scaler for this axis, whichever is configured."""
        if scale_type == "log":
            return self._scale_log(domain_min, domain_max, range_min, range_max)
        return self._scale_linear(domain_min, domain_max, range_min, range_max)

    def _assign_theme_colors(self) -> None:
        """Apply the theme palette to this axes' series. See utils."""
        from .utils import assign_theme_colors
        assign_theme_colors(list(self.series) + list(self.y2_series), self.theme)

    def finalize(self):
        """
        Compute all scale functions after series have been registered.

        Must be called before any rendering method.
        """
        self._assign_theme_colors()
        if self.series:
            self._x_domain, self._y_domain = self.compute_domain(self.series)
        if self.y2_series:
            _, self._y2_domain = self.compute_domain(self.y2_series)

        # A shared-x grid unifies the domain across cells, so this cell plots
        # against the whole grid's range rather than only its own data's.
        # Applied after compute_domain so re-finalising stays idempotent.
        if self._x_domain_override is not None:
            self._x_domain = self._x_domain_override

        if self._x_domain and self._y_domain:
            self.scale_x = self._make_scale(
                self._x_domain[0], self._x_domain[1],
                self.padding, self.width - self.padding,
                self.xscale,
            )
            self.scale_y = self._make_scale(
                self._y_domain[0], self._y_domain[1],
                self.height - self.padding, self.padding,
                self.yscale,
            )
        else:
            self.scale_x = None
            self.scale_y = None

        if self._y2_domain:
            self.scale_y2 = self._make_scale(
                self._y2_domain[0], self._y2_domain[1],
                self.height - self.padding, self.padding,
                self.yscale,
            )
        else:
            self.scale_y2 = self.scale_y  # fallback

    # SVG rendering

    def render_axes(self):
        """
        Render X, Y, and (if y2_series exist) Y2 axis lines plus labels.

        Returns:
            str: SVG elements for axes.
        """
        elements = []
        stroke     = self.theme.get("axis_color", "#333")
        text_color = self.theme.get("text_color", "#000")
        font       = self.theme.get("font", "sans-serif")
        pad        = self.padding

        # X-axis line
        elements.append(
            f'<line x1="{pad}" y1="{self.height - pad}" '
            f'x2="{self.width - pad}" y2="{self.height - pad}" stroke="{stroke}" />'
        )
        # Y-axis line
        elements.append(
            f'<line x1="{pad}" y1="{pad}" '
            f'x2="{pad}" y2="{self.height - pad}" stroke="{stroke}" />'
        )

        # No domain means no plottable data. Draw the empty frame with a
        # notice rather than returning nothing: a blank canvas is
        # indistinguishable from a rendering failure.
        if self._x_domain is None or self._y_domain is None:
            elements.append(
                f'<text x="{self.width // 2}" y="{self.height // 2}" '
                f'text-anchor="middle" font-size="13" font-family="{font}" '
                f'fill="{text_color}" opacity="0.55">No data to display</text>'
            )
            return "\n".join(elements)

        if self.xlabel:
            elements.append(
                f'<text x="{self.width // 2}" y="{self.height - 10}" '
                f'text-anchor="middle" font-size="13" font-family="{font}" '
                f'fill="{text_color}">{svg_label(self.xlabel)}</text>'
            )

        if self.ylabel:
            elements.append(
                f'<text x="15" y="{self.height // 2}" text-anchor="middle" '
                f'font-size="13" font-family="{font}" fill="{text_color}" '
                f'transform="rotate(-90, 15, {self.height // 2})">'
                f'{svg_label(self.ylabel)}</text>'
            )

        if self.y2label and self.y2_series:
            _y2x = self.width - 15
            elements.append(
                f'<text x="{_y2x}" y="{self.height // 2}" text-anchor="middle" '
                f'font-size="13" font-family="{font}" fill="{text_color}" '
                f'transform="rotate(90, {_y2x}, {self.height // 2})">'
                f'{svg_label(self.y2label)}</text>'
            )

        if self.y2_series:
            elements.append(
                f'<line x1="{self.width - pad}" y1="{pad}" '
                f'x2="{self.width - pad}" y2="{self.height - pad}" stroke="{stroke}" />'
            )

        return "\n".join(elements)

    def _tick_label_svg(self, x_p: float, y_label: float, label, *,
                        anchor: str, font: str, text_color: str,
                        transform: str = "", wrap_chars: float | None = None) -> str:
        """
        Build the ``<text>`` element for one X-axis tick label.

        Escapes ``label`` via :func:`svg_label` -- both call sites used to
        interpolate it raw, so a custom tick label containing ``&`` or an
        HTML tag (from ``set_xticks(..., labels=[...])``, or from any
        ``set_tick_format`` callback that formats untrusted data) landed in
        the SVG unescaped.

        When ``wrap_chars`` is given and ``self._tick_wrap`` is enabled, a
        label that would not fit at the current tick spacing is split across
        up to two ``<tspan>`` lines instead of the caller rotating it.
        Wrapping happens on the raw string, before escaping, so entities
        like ``&amp;`` are never split apart.
        """
        from .utils import svg_label, wrap_tick_label

        text = str(label)
        if self._tick_wrap and wrap_chars and len(text) > wrap_chars:
            lines = wrap_tick_label(text, wrap_chars, max_lines=2)
        else:
            lines = [text]

        if len(lines) == 1:
            body = svg_label(lines[0])
        else:
            tspans = "".join(
                f'<tspan x="{x_p}" dy="{"0" if i == 0 else "1.2em"}">'
                f'{svg_label(line)}</tspan>'
                for i, line in enumerate(lines)
            )
            body = tspans

        transform_attr = f'transform="{transform}"' if transform else ""
        return (
            f'<text x="{x_p}" y="{y_label}" text-anchor="{anchor}" '
            f'font-size="11" font-family="{font}" fill="{text_color}" {transform_attr}>'
            f'{body}</text>'
        )

    def render_grid(self, ticks=5):
        """
        Render tick marks, grid lines, and numeric labels.

        Categorical X-axes replace numeric labels with the original category names.

        Args:
            ticks (int): Number of major ticks per axis.

        Returns:
            str: SVG elements for grid and tick labels.
        """
        if not self.show_grid or self._x_domain is None or self._y_domain is None:
            return ""

        import math as _math

        elements   = []
        stroke     = self.theme.get("grid_color", "#ddd")
        font       = self.theme.get("font", "sans-serif")
        text_color = self.theme.get("text_color", "#000")
        pad        = self.padding

        # When the data crosses zero, draw the baseline darker than the other
        # gridlines. Bars above and below it are only readable against a
        # visible zero, and without one a diverging chart looks like an
        # ordinary chart with a strange axis.
        y_lo, y_hi = self._y_domain
        if y_lo < 0 < y_hi and self.scale_y is not None:
            zero_px = self.scale_y(0)
            elements.append(
                f'<line class="glyphx-zero-line" x1="{pad}" y1="{zero_px}" '
                f'x2="{self.width - pad}" y2="{zero_px}" '
                f'stroke="{self.theme.get("axis_color", "#333")}" '
                f'stroke-width="1" opacity="0.6"/>'
            )

        # Collect category labels for X axis from primary and Y2 series
        all_categories: dict = {}
        for s in list(self.series) + list(self.y2_series):
            if hasattr(s, "_x_categories") and s._x_categories:
                nx = getattr(s, "_numeric_x",
                             [i + 0.5 for i in range(len(s._x_categories))])
                for pos, cat in zip(nx, s._x_categories):
                    all_categories[pos] = cat

        # Helper: generate tick values for a numeric domain
        def _tick_vals(d_min: float, d_max: float, n: int, is_log: bool) -> list:
            """
            Choose tick positions for a domain.

            Log axes get 1/2/5 multiples of each decade, which is what reads
            naturally on a log scale; linear axes get ``n`` evenly spaced values.
            Falls back to even spacing if the log path yields nothing usable.
            """
            if is_log and d_min > 0:
                lo = int(_math.floor(_math.log10(d_min)))
                hi = int(_math.ceil(_math.log10(max(d_max, d_min * 10))))
                vals = [m * (10 ** e)
                        for e in range(lo, hi + 1)
                        for m in (1, 2, 5)
                        if d_min <= m * (10 ** e) <= d_max]
                return vals or [d_min + i * (d_max - d_min) / n for i in range(n + 1)]
            return [d_min + i * (d_max - d_min) / n for i in range(n + 1)]

        # Shaded spans (axhspan / axvspan) - drawn before grid so they sit behind
        _span_svg = self._render_spans()
        if _span_svg:
            elements.append(_span_svg)

        # Y1 ticks - left side, horizontal grid lines across full plot width
        # Use custom tick positions if set, otherwise auto-compute.
        def _fmt(val: float, label_override: str | None = None) -> str:
            """Format one Y tick, honouring an explicit label or a custom formatter."""
            if label_override is not None:
                return label_override
            if self._tick_formatter is not None:
                return str(self._tick_formatter(val))
            return _format_tick(val, is_log=(self.yscale == "log"))

        _y_tick_vals = (
            list(self._yticks)
            if self._yticks is not None
            else _tick_vals(self._y_domain[0], self._y_domain[1], ticks, self.yscale == "log")
        )
        _y_tick_lbls = self._yticklabels   # None → auto-format each

        for idx_y, y_v in enumerate(_y_tick_vals):
            if not (self._y_domain[0] <= y_v <= self._y_domain[1]):
                continue
            y_p     = self.scale_y(y_v)
            lbl_ovr = _y_tick_lbls[idx_y] if _y_tick_lbls and idx_y < len(_y_tick_lbls) else None
            # Grid line
            elements.append(
                f'<line x1="{pad}" x2="{self.width - pad}" y1="{y_p}" y2="{y_p}" '
                f'stroke="{stroke}" stroke-dasharray="3,3" />')
            # Tick mark on left spine
            elements.append(
                f'<line x1="{pad - self._tick_length}" x2="{pad}" '
                f'y1="{y_p}" y2="{y_p}" stroke="{text_color}" stroke-width="1"/>')
            # Label
            elements.append(
                f'<text x="{pad - self._tick_length - 4}" y="{y_p + 4}" text-anchor="end" '
                f'font-size="11" font-family="{font}" fill="{text_color}">'
                f'{svg_label(_fmt(y_v, lbl_ovr))}</text>'
            )

        # Minor Y ticks
        if self._minor_ticks > 0 and len(_y_tick_vals) >= 2:
            for j in range(len(_y_tick_vals) - 1):
                lo_v = _y_tick_vals[j]
                hi_v = _y_tick_vals[j + 1]
                step = (hi_v - lo_v) / (self._minor_ticks + 1)
                for k in range(1, self._minor_ticks + 1):
                    mv = lo_v + k * step
                    if not (self._y_domain[0] <= mv <= self._y_domain[1]):
                        continue
                    mp = self.scale_y(mv)
                    elements.append(
                        f'<line x1="{pad - self._minor_length}" x2="{pad}" '
                        f'y1="{mp}" y2="{mp}" stroke="{text_color}" '
                        f'stroke-width="0.7" opacity="0.5"/>')

        # Y2 ticks - right side, own independent scale, no extra grid lines.
        _has_y2 = (
            bool(self.y2_series)
            and self._y2_domain is not None
            and self.scale_y2 is not None
            and self.scale_y2 is not self.scale_y
        )
        if _has_y2:
            right_x = self.width - pad
            # Place a right-hand tick at each left-hand tick's pixel row,
            # by taking that tick's fraction through the Y1 domain and
            # reading the same fraction of the Y2 domain.  Generating the
            # two independently happened to line up for the default five
            # ticks, but drifted apart the moment set_yticks() gave Y1 a
            # different count -- leaving two sets of gridlines interleaved.
            y1_lo, y1_hi = self._y_domain
            y2_lo, y2_hi = self._y2_domain
            y1_span = (y1_hi - y1_lo) or 1.0
            _y2_tick_vals = [
                y2_lo + ((v - y1_lo) / y1_span) * (y2_hi - y2_lo)
                for v in _y_tick_vals
            ]
            for y2_v in _y2_tick_vals:
                y2_p = self.scale_y2(y2_v)
                # Tick mark on right axis line
                elements.append(
                    f'<line x1="{right_x}" x2="{right_x + 5}" '
                    f'y1="{y2_p}" y2="{y2_p}" '
                    f'stroke="{text_color}" stroke-width="1" opacity="0.6"/>')
                # Label to the right of the tick
                elements.append(
                    f'<text x="{right_x + 9}" y="{y2_p + 4}" text-anchor="start" '
                    f'font-size="11" font-family="{font}" fill="{text_color}" opacity="0.85">'
                    f'{svg_label(_fmt(y2_v))}</text>'
                )

        # X ticks - bottom, vertical grid lines
        plot_w      = self.width - 2 * pad
        rotate      = getattr(self, "_auto_rotate", False) and not self._tick_wrap
        anchor      = "end" if rotate else "middle"
        rot_tfm     = "rotate(-40, {x_p}, {y_label})" if rotate else ""
        y_label_off = 16 if not rotate else 8

        if all_categories:
            n_cats = max(1, len(all_categories))
            wrap_chars = (plot_w / n_cats) * 0.85 / 6.5
            for x_v, label in all_categories.items():
                x_p     = self.scale_x(x_v)
                y_label = self.height - pad + y_label_off
                rot     = rot_tfm.format(x_p=x_p, y_label=y_label) if rotate else ""
                elements.append(
                    f'<line y1="{pad}" y2="{self.height - pad}" '
                    f'x1="{x_p}" x2="{x_p}" '
                    f'stroke="{stroke}" stroke-dasharray="3,3" />')
                if not self._hide_xticklabels:
                    elements.append(self._tick_label_svg(
                        x_p, y_label, label, anchor=anchor, font=font,
                        text_color=text_color, transform=rot,
                        wrap_chars=wrap_chars))
        else:
            _has_dt = any(getattr(s, "_datetime_x", False) for s in self.series)
            _span   = (self._x_domain[1] - self._x_domain[0]) if _has_dt else 0
            _x_tick_vals = (
                list(self._xticks)
                if self._xticks is not None
                else _tick_vals(self._x_domain[0], self._x_domain[1],
                                ticks, self.xscale == "log")
            )
            _x_tick_lbls = self._xticklabels
            wrap_chars = (plot_w / max(1, len(_x_tick_vals) - 1)) * 0.85 / 6.5
            for idx_x, x_v in enumerate(_x_tick_vals):
                if not (self._x_domain[0] <= x_v <= self._x_domain[1]):
                    continue
                x_p     = self.scale_x(x_v)
                y_label = self.height - pad + y_label_off
                rot     = rot_tfm.format(x_p=x_p, y_label=y_label) if rotate else ""
                if _x_tick_lbls and idx_x < len(_x_tick_lbls):
                    tick_label = _x_tick_lbls[idx_x]
                elif self._tick_formatter is not None:
                    tick_label = str(self._tick_formatter(x_v))
                elif _has_dt:
                    tick_label = _format_datetime_tick(x_v, _span)
                else:
                    tick_label = _format_tick(x_v, is_log=(self.xscale == "log"))
                elements.append(
                    f'<line y1="{pad}" y2="{self.height - pad}" '
                    f'x1="{x_p}" x2="{x_p}" '
                    f'stroke="{stroke}" stroke-dasharray="3,3" />')
                # Tick mark on bottom spine
                elements.append(
                    f'<line x1="{x_p}" x2="{x_p}" '
                    f'y1="{self.height - pad}" y2="{self.height - pad + self._tick_length}" '
                    f'stroke="{text_color}" stroke-width="1"/>')
                if not self._hide_xticklabels:
                    elements.append(self._tick_label_svg(
                        x_p, y_label, tick_label, anchor=anchor, font=font,
                        text_color=text_color, transform=rot,
                        wrap_chars=wrap_chars))
            # Minor X ticks
            if self._minor_ticks > 0 and len(_x_tick_vals) >= 2:
                for j in range(len(_x_tick_vals) - 1):
                    lo_xv = _x_tick_vals[j]
                    hi_xv = _x_tick_vals[j + 1]
                    xstep = (hi_xv - lo_xv) / (self._minor_ticks + 1)
                    for k in range(1, self._minor_ticks + 1):
                        mxv = lo_xv + k * xstep
                        if not (self._x_domain[0] <= mxv <= self._x_domain[1]):
                            continue
                        mxp = self.scale_x(mxv)
                        by  = self.height - pad
                        elements.append(
                            f'<line x1="{mxp}" x2="{mxp}" '
                            f'y1="{by}" y2="{by + self._minor_length}" '
                            f'stroke="{text_color}" stroke-width="0.7" opacity="0.5"/>')

        return "\n".join(elements)


    # Tight layout

    def tight_layout(self) -> Axes:
        """
        Auto-adjust padding so tick labels, axis labels, and titles
        don't clip or overlap.

        Estimates pixel widths of the longest tick labels and increases
        ``self.padding`` accordingly.  Also triggers auto-rotation of
        crowded X-axis labels.

        Returns ``self`` for chaining.
        """
        extra_left  = 0
        extra_bottom = 0

        if self._y_domain:
            # Longest y-tick label (approx. 7px per char)
            longest_y = max(
                len(_format_tick(self._y_domain[0])),
                len(_format_tick(self._y_domain[1])),
            )
            extra_left = max(0, longest_y * 7 + 8 - self.padding + 10)

        if self.ylabel:
            extra_left += 18

        if self.xlabel:
            extra_bottom += 18

        self.padding = max(self.padding, self.padding + max(extra_left, extra_bottom))

        if self._x_domain:
            self._auto_rotate = self._should_rotate_xlabels()

        return self

    def _should_rotate_xlabels(self, ticks: int = 5) -> bool:
        """Return True if x-axis labels would overlap at horizontal angle."""
        if self._x_domain is None:
            return False
        x_range = self._x_domain[1] - self._x_domain[0]
        if x_range == 0:
            return False
        plot_w         = self.width - 2 * self.padding
        tick_spacing   = plot_w / ticks
        # Check categorical labels first
        for s in self.series:
            cats = getattr(s, "_x_categories", None)
            if cats:
                max_len = max(len(str(c)) for c in cats)
                return max_len * 6.5 > tick_spacing * 0.85
        # Numeric labels
        max_len = max(
            len(_format_tick(self._x_domain[0] + i * x_range / ticks))
            for i in range(ticks + 1)
        )
        return max_len * 6.5 > tick_spacing * 0.85


# Multi-figure grid layout

def grid(figures, rows=1, cols=1, gap=20):
    """
    Arrange multiple Figure instances in a grid and return a single HTML page.

    Args:
        figures (list[Figure]): GlyphX Figure objects to arrange.
        rows (int): Number of rows in the grid.
        cols (int): Number of columns.
        gap  (int): Pixel margin around each subplot.

    Returns:
        str: Full HTML document with all SVGs embedded.
    """
    from .utils import wrap_svg_with_template

    svg_blocks = []
    idx = 0

    for _ in range(rows):
        row_parts = []
        for _ in range(cols):
            if idx < len(figures):
                svg = figures[idx].render_svg()
                row_parts.append(f'<div style="margin:{gap}px">{svg}</div>')
                idx += 1
        row_html = '<div style="display:flex">' + "".join(row_parts) + "</div>"
        svg_blocks.append(row_html)

    grid_html = "<div>" + "".join(svg_blocks) + "</div>"
    return wrap_svg_with_template(grid_html)
