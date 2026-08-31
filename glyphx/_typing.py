"""
Structural types shared across the series modules.

Every ``Series.to_svg()`` takes the :class:`~glyphx.layout.Axes` it is being
drawn into.  Annotating that parameter as ``object`` made mypy reject every
attribute access on it, so the series modules carried ``ax: object`` plus a
trail of ``# type: ignore`` comments.  :class:`AxesLike` names the surface a
series actually uses instead, which keeps the annotation honest without
importing ``layout`` (and its Figure dependency) into every chart module.

The scale callables are non-optional here on purpose.  ``Axes`` sets them to
``None`` until :meth:`Axes.finalize` runs, but ``to_svg()`` is only ever called
after finalisation, so the contract a series can rely on is "the scales exist".
"""

from __future__ import annotations

from typing import Any, Protocol


class AxesLike(Protocol):
    """The part of ``Axes`` that series rendering depends on."""

    # Geometry
    width: Any
    height: Any
    padding: Any

    # Styling
    theme: Any

    # Content
    series: Any

    # Computed domains, populated by ``Axes.finalize()``
    _y_domain: Any
    _spines: Any

    def scale_x(self, value: Any, /) -> float:
        """Map a data-space x value to a pixel coordinate."""
        ...

    def scale_y(self, value: Any, /) -> float:
        """Map a data-space y value to a pixel coordinate on the primary axis."""
        ...

    def scale_y2(self, value: Any, /) -> float:
        """Map a data-space y value to a pixel coordinate on the secondary axis."""
        ...

    def add(self, series: Any, use_y2: bool = ...) -> Any:
        """Attach a series to this axes."""
        ...

    def set_xticks(self, ticks: Any, labels: Any = ...) -> Any:
        """Override the computed x tick positions."""
        ...
