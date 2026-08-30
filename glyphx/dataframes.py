"""
Dataframe-agnostic input handling.

GlyphX used to require pandas specifically: anything passed as ``data`` had
to be a ``pandas.DataFrame``, and column access went through pandas-only
APIs.  That excludes Polars, DuckDB, cuDF, Vaex, PyArrow, and Ibis, several
of which are now the default in their niches.

Rather than special-casing each library, this module goes through the
dataframe interchange protocol (``__dataframe__``, PEP-ish standard adopted
by pandas 1.5+, Polars, cuDF, Vaex, and PyArrow) with a small number of
faster paths for the libraries that expose a simpler column API.

The public surface is deliberately tiny:

    is_dataframe(obj)   -> bool
    column_names(df)    -> list[str]
    get_column(df, name)-> list
    to_columns(df)      -> dict[str, list]
"""

from __future__ import annotations

from typing import Any


def _has_pandas_api(obj: Any) -> bool:
    """True for pandas-like objects that support ``df[col].tolist()``."""
    return hasattr(obj, "columns") and hasattr(obj, "iloc")


def _is_arrow_table(obj: Any) -> bool:
    """True for a PyArrow Table, which names columns differently."""
    names = getattr(obj, "column_names", None)
    return names is not None and not callable(names) and hasattr(obj, "column")


def is_dataframe(obj: Any) -> bool:
    """
    Return True if ``obj`` is a dataframe GlyphX can read.

    Accepts anything implementing the dataframe interchange protocol, plus
    pandas-like objects and plain ``{column: values}`` mappings.

    Args:
        obj: Candidate object.

    Returns:
        bool: True if :func:`to_columns` can handle it.
    """
    if obj is None:
        return False
    if isinstance(obj, dict):
        # A mapping of column name -> sequence counts as a dataframe.
        return bool(obj) and all(
            hasattr(v, "__len__") and not isinstance(v, (str, bytes))
            for v in obj.values()
        )
    return (
        hasattr(obj, "__dataframe__")
        or _has_pandas_api(obj)
        or _is_arrow_table(obj)
    )


def column_names(df: Any) -> list[str]:
    """
    Return the column names of ``df`` in order.

    Args:
        df: A dataframe, or a ``{column: values}`` mapping.

    Returns:
        list[str]: Column names.

    Raises:
        TypeError: If ``df`` is not a recognised dataframe.
    """
    if isinstance(df, dict):
        return [str(k) for k in df]

    # PyArrow exposes names on .column_names; .columns holds the arrays.
    names = getattr(df, "column_names", None)
    if names is not None and not callable(names):
        return [str(c) for c in names]

    # pandas/polars: .columns is the names. Guard against libraries where
    # it holds column *objects* instead -- str() on those is unusable.
    columns = getattr(df, "columns", None)
    if columns is not None and all(isinstance(c, str) for c in columns):
        return [str(c) for c in columns]

    if hasattr(df, "__dataframe__"):
        return [str(c) for c in df.__dataframe__().column_names()]

    if columns is not None:
        return [str(c) for c in columns]

    raise TypeError(f"Not a dataframe: {type(df).__name__}")


def _resolve_key(df: Any, name: str) -> Any:
    """
    Map a stringified column name back to the key the frame actually holds.

    ``column_names()`` stringifies for display, so a frame with integer column
    labels -- what ``pd.read_csv(header=None)`` produces -- reports ``"0"``
    while indexing still requires ``0``.  Looking the string up directly
    raised KeyError on a column that was plainly listed as available.
    """
    if isinstance(df, dict):
        if name in df:
            return name
        return next((k for k in df if str(k) == name), name)

    columns = getattr(df, "columns", None)
    if columns is None:
        return name
    try:
        cols = list(columns)
    except TypeError:                       # not iterable; leave it alone
        return name
    if name in cols:
        return name
    return next((c for c in cols if str(c) == name), name)


def get_column(df: Any, name: str) -> list:
    """
    Return one column of ``df`` as a plain Python list.

    Args:
        df: A dataframe, or a ``{column: values}`` mapping.
        name (str): Column name.

    Returns:
        list: The column values.

    Raises:
        KeyError: If the column is not present. The message lists the
            columns that are, since a typo is the common cause.
        TypeError: If ``df`` is not a recognised dataframe.
    """
    available = column_names(df)
    if name not in available:
        raise KeyError(
            f"Column {name!r} not found. Available columns: {available}"
        )

    # A duplicated name makes df[name] return a 2-D frame, and iterating a
    # DataFrame yields its column *labels* -- so this silently plotted
    # ["a", "a"] as if it were data.  Refuse instead.
    if available.count(name) > 1:
        raise KeyError(
            f"Column {name!r} is ambiguous: the frame has "
            f"{available.count(name)} columns with that name. "
            f"Rename or de-duplicate them before plotting."
        )

    key = _resolve_key(df, name)

    if isinstance(df, dict):
        return list(df[key])

    column = None
    if _is_arrow_table(df):
        column = df.column(key)
    elif _has_pandas_api(df):
        column = df[key]
    elif hasattr(df, "__getitem__"):
        # Polars, cuDF, and most others support df[name] directly.
        try:
            column = df[key]
        except Exception:       # fall through to the interchange protocol
            column = None

    if column is not None:
        for attr in ("to_list", "tolist", "to_pylist"):
            converter = getattr(column, attr, None)
            if callable(converter):
                return list(converter())
        return list(column)

    # Interchange protocol: the universal fallback.
    interchange = df.__dataframe__()
    col = interchange.get_column_by_name(name)
    values: list = []
    for chunk in col.get_chunks():
        buffers = chunk.get_buffers()
        data_buffer, dtype = buffers["data"]
        values.extend(_buffer_to_list(data_buffer, dtype, chunk.size()))
    return values


def _buffer_to_list(buffer: Any, dtype: Any, size: int) -> list:
    """Materialise an interchange-protocol buffer via NumPy."""
    import ctypes

    import numpy as np

    kind, bit_width, _fmt, _endianness = dtype
    np_kind = {
        0: "i",   # int
        1: "u",   # uint
        2: "f",   # float
        20: "b",  # bool
    }.get(kind)
    if np_kind is None:
        raise TypeError(f"Unsupported interchange dtype kind: {kind}")

    np_dtype = np.dtype(f"{np_kind}{bit_width // 8}")
    ctypes_ptr = ctypes.cast(
        buffer.ptr, ctypes.POINTER(ctypes.c_byte * buffer.bufsize)
    )
    array = np.frombuffer(ctypes_ptr.contents, dtype=np_dtype, count=size)
    return array.tolist()


def to_columns(df: Any) -> dict[str, list]:
    """Every column of ``df`` as a plain Python list."""
    return {name: get_column(df, name) for name in column_names(df)}


def to_pandas(df: Any):
    """
    Convert any supported dataframe to a pandas DataFrame.

    Used by the composite helpers (pairplot, jointplot, facet_grid) that lean
    on pandas-specific operations such as ``groupby``.  Everything else
    should use :func:`get_column` and avoid the dependency.

    Args:
        df: Any supported dataframe.

    Returns:
        pandas.DataFrame: The same data.
    """
    import pandas as pd

    if isinstance(df, pd.DataFrame):
        return df
    # Prefer the library's own converter when it has one -- it preserves
    # dtypes better than a round trip through Python lists.
    converter = getattr(df, "to_pandas", None)
    if callable(converter):
        return converter()
    return pd.DataFrame(to_columns(df))
