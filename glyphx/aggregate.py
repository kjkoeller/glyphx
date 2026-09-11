"""
Automatic aggregation over repeated measurements.

``sns.lineplot()`` is the single feature that keeps a large part of the
scientific-Python world on seaborn: hand it raw repeated-measures data --
several y values per x, from several subjects or trials or runs -- and it
draws the mean per x with a bootstrapped confidence band around it, with no
manual ``groupby`` first. Without it a caller has to aggregate, compute an
interval, and assemble two series by hand before they can plot anything.

This provides the same thing:

    fig.aggregate_line(df, x="timepoint", y="score")
    fig.aggregate_line(df, x="timepoint", y="score", hue="treatment")

The estimator and the interval are both configurable, and ``ci=None`` gives
the aggregate line on its own.
"""

from __future__ import annotations

import numpy as np

#: Named estimators. A callable is accepted too, so anything reducing a
#: 1-D array to a scalar works without extending this map.
_ESTIMATORS = {
    "mean": np.mean,
    "median": np.median,
    "sum": np.sum,
    "min": np.min,
    "max": np.max,
    "count": len,
}


def _resolve_estimator(estimator):
    """Turn an estimator name into a callable, or pass a callable through."""
    if callable(estimator):
        return estimator
    try:
        return _ESTIMATORS[estimator]
    except KeyError:
        raise ValueError(
            f"Unknown estimator {estimator!r}. Use one of "
            f"{', '.join(sorted(_ESTIMATORS))}, or pass a callable that "
            f"reduces an array to a single number."
        ) from None


def _bootstrap_interval(values, estimator, ci, n_boot, rng):
    """
    Percentile bootstrap interval for one group's estimate.

    Resampling makes no distributional assumption, which matters because
    repeated-measures data is routinely skewed -- a normal-theory interval
    would be wrong in exactly the cases this is most used for.

    A single observation has no spread to resample, so its interval is the
    point itself rather than a fabricated width.
    """
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        point = float(estimator(values)) if len(values) else float("nan")
        return point, point

    draws = np.empty(n_boot)
    n = len(values)
    for i in range(n_boot):
        draws[i] = estimator(values[rng.integers(0, n, n)])
    half = (100 - ci) / 2
    return float(np.percentile(draws, half)), float(np.percentile(draws, 100 - half))


def _standard_error_interval(values, estimator, n_std):
    """
    Interval as the estimate plus or minus a multiple of the standard error.

    Cheaper than bootstrapping and what a reader expects from ``ci="se"``.
    """
    values = np.asarray(values, dtype=float)
    point = float(estimator(values))
    if len(values) < 2:
        return point, point
    se = float(np.std(values, ddof=1) / np.sqrt(len(values)))
    return point - n_std * se, point + n_std * se


def aggregate(x_values, y_values, *, estimator="mean", ci=95,
              n_boot=1000, n_std=1.0, seed=42):
    """
    Collapse repeated y values per x into an estimate and an interval.

    Args:
        x_values: The x of each observation. Repeats are the point: every
            observation sharing an x forms one group.
        y_values: The observed value for each.
        estimator: ``"mean"``, ``"median"``, ``"sum"``, ``"min"``, ``"max"``,
            ``"count"``, or any callable reducing an array to a scalar.
        ci: Confidence level 0-100 for a bootstrap interval, ``"sd"`` for one
            standard deviation, ``"se"`` for standard error, or ``None`` for
            no interval at all.
        n_boot: Bootstrap resamples when ``ci`` is a number.
        n_std: Multiplier for the ``"sd"`` and ``"se"`` intervals.
        seed: Fixed so a chart redrawn from the same data is identical --
            a band that shifted slightly on every render would make figures
            irreproducible.

    Returns:
        tuple: ``(xs, centre, lower, upper)``, sorted by x. ``lower`` and
        ``upper`` are ``None`` when ``ci`` is ``None``.

    Raises:
        ValueError: If the two inputs differ in length, or the estimator or
            ci is not recognised.
    """
    x_values = list(x_values)
    y_values = [float(v) for v in y_values]
    if len(x_values) != len(y_values):
        raise ValueError(
            f"x and y must be the same length; got {len(x_values)} and "
            f"{len(y_values)}."
        )
    if (ci is not None and not isinstance(ci, str)
            and not 0 < float(ci) < 100):
        raise ValueError(f"ci must be between 0 and 100, got {ci}.")
    if isinstance(ci, str) and ci not in ("sd", "se"):
        raise ValueError(
            f"ci={ci!r} is not recognised. Use a number for a bootstrap "
            f"interval, 'sd', 'se', or None."
        )

    estimator = _resolve_estimator(estimator)

    groups: dict = {}
    for xv, yv in zip(x_values, y_values):
        groups.setdefault(xv, []).append(yv)

    # Numeric x sorts numerically; categorical x keeps first-seen order,
    # since alphabetical would scramble things like Mon/Tue/Wed.
    keys = list(groups)
    if all(isinstance(k, (int, float)) and not isinstance(k, bool) for k in keys):
        keys.sort()

    rng = np.random.default_rng(seed)
    centre, lower, upper = [], [], []
    for key in keys:
        values = np.asarray(groups[key], dtype=float)
        centre.append(float(estimator(values)))
        if ci is None:
            continue
        if ci == "sd":
            point = float(estimator(values))
            spread = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            lo, hi = point - n_std * spread, point + n_std * spread
        elif ci == "se":
            lo, hi = _standard_error_interval(values, estimator, n_std)
        else:
            lo, hi = _bootstrap_interval(values, estimator, float(ci), n_boot, rng)
        lower.append(lo)
        upper.append(hi)

    if ci is None:
        return keys, centre, None, None
    return keys, centre, lower, upper
