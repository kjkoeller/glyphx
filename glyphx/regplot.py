"""
GlyphX regplot -- regression plot with multiple fit types.

Extends the basic lmplot stub to support polynomial, logistic, and LOWESS
regression with confidence intervals, closing the last major gap vs Seaborn's
regression plotting.

    from glyphx.regplot import regplot

    # Ordinary least squares (default)
    fig = regplot(df, x="bill_length", y="body_mass")

    # Polynomial degree-2
    fig = regplot(df, x="age", y="income", order=2)

    # LOWESS (locally weighted, no parametric assumption)
    fig = regplot(df, x="gdp", y="life_exp", lowess=True)

    # Logistic (binary Y)
    fig = regplot(df, x="score", y="pass_fail", logistic=True)
"""
from __future__ import annotations

import math
import numpy as np

from .figure  import Figure
from .series  import ScatterSeries, LineSeries
from .fill_between import FillBetweenSeries


def _lowess(x: np.ndarray, y: np.ndarray, frac: float = 0.3) -> tuple:
    """
    LOWESS (locally weighted scatterplot smoothing) -- pure NumPy.

    Args:
        x:    X values (sorted).
        y:    Y values.
        frac: Smoothing fraction (0-1).  Larger = smoother.

    Returns:
        ``(x_sorted, y_smooth)``
    """
    n   = len(x)
    r   = max(1, int(frac * n))
    order = np.argsort(x)
    xs, ys = x[order], y[order]
    yhat  = np.zeros(n)

    for i in range(n):
        dists    = np.abs(xs - xs[i])
        sorted_d = np.sort(dists)
        h        = sorted_d[min(r, n - 1)]
        if h == 0:
            h = 1e-10
        u       = np.clip(dists / h, 0, 1)
        w       = (1 - u ** 3) ** 3
        X       = np.vstack([np.ones(n), xs]).T
        WX      = w[:, None] * X
        WY      = w * ys
        try:
            beta  = np.linalg.lstsq(WX, WY, rcond=None)[0]
            yhat[i] = beta[0] + beta[1] * xs[i]
        except np.linalg.LinAlgError:
            yhat[i] = ys[i]

    return xs, yhat


def _logistic_fit(x: np.ndarray, y: np.ndarray, n_iter: int = 200
                  ) -> tuple[float, float]:
    """
    Fit logistic regression via gradient descent -- pure NumPy.

    Returns ``(intercept, slope)`` for σ(intercept + slope * x).
    """
    # Normalise x for numerical stability
    x_mu, x_std = x.mean(), x.std() + 1e-10
    xn = (x - x_mu) / x_std

    b0, b1 = 0.0, 0.0
    lr     = 0.1

    for _ in range(n_iter):
        p   = 1 / (1 + np.exp(-(b0 + b1 * xn)))
        err = p - y
        b0 -= lr * err.mean()
        b1 -= lr * (err * xn).mean()

    # Un-normalise
    b1_raw = b1 / x_std
    b0_raw = b0 - b1_raw * x_mu
    return b0_raw, b1_raw


def _bootstrap_ci(
    x: np.ndarray,
    y: np.ndarray,
    x_eval: np.ndarray,
    order:    int   = 1,
    n_boot:   int   = 100,
    ci:       float = 95,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap confidence interval for a polynomial regression line."""
    rng    = np.random.default_rng(42)
    n      = len(x)
    preds  = np.zeros((n_boot, len(x_eval)))

    for b in range(n_boot):
        idx    = rng.integers(0, n, n)
        coeffs = np.polyfit(x[idx], y[idx], order)
        preds[b] = np.polyval(coeffs, x_eval)

    lo  = np.percentile(preds, (100 - ci) / 2,      axis=0)
    hi  = np.percentile(preds, 100 - (100 - ci) / 2, axis=0)
    return lo, hi


def regplot(
    data,
    x:         str | None    = None,
    y:         str | None    = None,
    x_vals:    list | None   = None,
    y_vals:    list | None   = None,
    order:     int           = 1,
    lowess:    bool          = False,
    logistic:  bool          = False,
    ci:        int           = 95,
    n_boot:    int           = 100,
    scatter_kw: dict | None  = None,
    line_kw:    dict | None  = None,
    color:     str           = "#2563eb",
    alpha:     float         = 0.20,
    title:     str           = "",
    theme:     str           = "default",
    auto_display: bool       = False,
) -> Figure:
    """
    Regression plot: scatter + fitted curve + optional CI band.

    Supports OLS, polynomial, logistic, and LOWESS regression, all in
    pure NumPy.  Seaborn's ``regplot`` requires statsmodels for some modes;
    GlyphX has zero extra dependencies.

    Args:
        data:       DataFrame (use with ``x=`` and ``y=`` column names) or
                    ``None`` (use ``x_vals``/``y_vals`` directly).
        x, y:       Column names when ``data`` is a DataFrame.
        x_vals, y_vals: Raw numeric arrays when ``data`` is None.
        order:      Polynomial degree (1 = linear, 2 = quadratic, etc.)
        lowess:     Use LOWESS instead of polynomial.
        logistic:   Fit logistic curve (binary Y assumed).
        ci:         Confidence interval level (0-100).  0 disables CI band.
        n_boot:     Bootstrap samples for the CI band.
        scatter_kw: Extra kwargs for :class:`~glyphx.series.ScatterSeries`.
        line_kw:    Extra kwargs for :class:`~glyphx.series.LineSeries`.
        color:      Shared colour for scatter and fit line.
        alpha:      CI band fill opacity.
        title:      Chart title.
        theme:      GlyphX theme name.
        auto_display: Open immediately after creation.

    Returns:
        :class:`~glyphx.Figure` ready to ``.show()`` or ``.save()``.

    Examples::

        from glyphx.regplot import regplot

        # OLS
        regplot(df, x="height", y="weight")

        # Quadratic
        regplot(df, x="age", y="income", order=2, color="#dc2626")

        # LOWESS
        regplot(df, x="gdp", y="life_exp", lowess=True)

        # Logistic (binary outcome)
        regplot(df, x="dose", y="response", logistic=True)

        # No data frame
        import numpy as np
        x = np.random.randn(200)
        y = 2*x + np.random.randn(200)
        regplot(None, x_vals=x, y_vals=y, title="Correlation")
    """
    import pandas as _pd

    scatter_kw = scatter_kw or {}
    line_kw    = line_kw    or {}

    # Extract arrays
    if data is not None and x and y:
        arr_x = np.asarray(data[x], dtype=float)
        arr_y = np.asarray(data[y], dtype=float)
        xlabel, ylabel = x, y
    elif x_vals is not None and y_vals is not None:
        arr_x = np.asarray(x_vals, dtype=float)
        arr_y = np.asarray(y_vals, dtype=float)
        xlabel = ylabel = ""
    else:
        raise ValueError("Provide either (data, x=, y=) or (x_vals=, y_vals=).")

    # Remove NaN pairs
    mask  = np.isfinite(arr_x) & np.isfinite(arr_y)
    arr_x = arr_x[mask]
    arr_y = arr_y[mask]

    fig = Figure(width=700, height=480, auto_display=auto_display, theme=theme)
    if title:
        fig.set_title(title)
    fig.set_xlabel(xlabel).set_ylabel(ylabel)

    # -- Scatter ------------------------------------------------------------
    fig.add(ScatterSeries(
        arr_x.tolist(), arr_y.tolist(),
        color=color, size=4,
        label="Observations",
        **scatter_kw,
    ))

    # -- Regression line ----------------------------------------------------
    x_eval = np.linspace(arr_x.min(), arr_x.max(), 200)

    if lowess:
        xs, ys = _lowess(arr_x, arr_y, frac=0.3)
        fig.add(LineSeries(
            xs.tolist(), ys.tolist(),
            color=color, width=2, label="LOWESS",
            **line_kw,
        ))

    elif logistic:
        b0, b1 = _logistic_fit(arr_x, arr_y)
        y_eval = 1 / (1 + np.exp(-(b0 + b1 * x_eval)))
        fig.add(LineSeries(
            x_eval.tolist(), y_eval.tolist(),
            color=color, width=2, label="Logistic fit",
            **line_kw,
        ))

    else:
        # Polynomial OLS
        coeffs = np.polyfit(arr_x, arr_y, order)
        y_eval = np.polyval(coeffs, x_eval)

        # Fit annotation
        if order == 1:
            slope, intercept = coeffs
            corr = float(np.corrcoef(arr_x, arr_y)[0, 1])
            lbl  = f"y = {slope:.2g}x + {intercept:.2g}  (r={corr:.2f})"
        else:
            lbl = f"Degree-{order} polynomial"

        fig.add(LineSeries(
            x_eval.tolist(), y_eval.tolist(),
            color=color, width=2, label=lbl,
            **line_kw,
        ))

        # CI band
        if ci > 0 and len(arr_x) > 5:
            lo, hi = _bootstrap_ci(arr_x, arr_y, x_eval,
                                   order=order, n_boot=n_boot, ci=ci)
            fig.add(FillBetweenSeries(
                x_eval.tolist(), lo.tolist(), hi.tolist(),
                color=color, alpha=alpha,
                label=f"{ci}% CI",
            ))

    return fig
