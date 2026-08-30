"""
GlyphX theme definitions.

Each theme is a dictionary with keys::

    colors       - ordered list of series colors
    axis_color   - stroke color for axis lines
    grid_color   - stroke color for grid lines
    font         - font-family string
    background   - canvas background fill
    text_color   - default text fill color
"""

#: Mapping of theme name to theme definition.  Each value is a dict with the
#: keys listed above; pass a name to ``Figure(theme=...)`` or ``set_theme()``.
themes = {
    "default": {
        "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                   "#8c564b", "#e377c2", "#7f7f7f"],
        "axis_color": "#333",
        "grid_color": "#ddd",
        "font": "sans-serif",
        "background": "#ffffff",
        "text_color": "#000000",
    },
    "dark": {
        "colors": ["#8ecae6", "#ffb703", "#219ebc", "#fb8500", "#d62828",
                   "#a8dadc", "#f4a261", "#e9c46a"],
        "axis_color": "#cccccc",
        "grid_color": "#444444",
        "font": "sans-serif",
        "background": "#1e1e1e",
        "text_color": "#ffffff",
    },
    # Okabe-Ito palette - actual scientific standard for colorblind safety.
    # Safe for deuteranopia, protanopia, and tritanopia.
    "colorblind": {
        "colors": ["#E69F00", "#56B4E9", "#009E73", "#F0E442",
                   "#0072B2", "#D55E00", "#CC79A7", "#000000"],
        "axis_color": "#000000",
        "grid_color": "#bbbbbb",
        "font": "sans-serif",
        "background": "#ffffff",
        "text_color": "#000000",
    },
    "monochrome": {
        "colors": ["#111111", "#333333", "#555555", "#777777",
                   "#999999", "#bbbbbb", "#dddddd"],
        "axis_color": "#111111",
        "grid_color": "#cccccc",
        "font": "sans-serif",
        "background": "#ffffff",
        "text_color": "#000000",
    },
    "pastel": {
        "colors": ["#aec7e8", "#ffbb78", "#98df8a", "#ff9896",
                   "#c5b0d5", "#c49c94", "#f7b6d2", "#c7c7c7"],
        "axis_color": "#444444",
        "grid_color": "#cccccc",
        "font": "sans-serif",
        "background": "#f9f9f9",
        "text_color": "#222222",
    },
    "warm": {
        "colors": ["#e63946", "#f4a261", "#e9c46a", "#2a9d8f",
                   "#264653", "#a8dadc", "#457b9d", "#1d3557"],
        "axis_color": "#5c3317",
        "grid_color": "#f0d9c8",
        "font": "Georgia, serif",
        "background": "#fff8f0",
        "text_color": "#3e1f00",
    },
    "ocean": {
        "colors": ["#03045e", "#0077b6", "#00b4d8", "#90e0ef",
                   "#caf0f8", "#48cae4", "#023e8a", "#0096c7"],
        "axis_color": "#023e8a",
        "grid_color": "#caf0f8",
        "font": "sans-serif",
        "background": "#f0f8ff",
        "text_color": "#03045e",
    },
}


# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------

#: Every key a complete theme defines.  A custom theme may supply any subset;
#: the rest are inherited from its base.
THEME_KEYS = frozenset({
    "colors", "axis_color", "grid_color", "font", "background", "text_color",
})

#: Names shipped with GlyphX.  register_theme() refuses to overwrite these.
BUILTIN_THEMES = frozenset(themes)


def list_themes() -> list[str]:
    """Names of every registered theme, built-in and custom.

    Returns:
        list[str]: Sorted theme names.

    Example::

        >>> from glyphx import list_themes
        >>> "dark" in list_themes()
        True
    """
    return sorted(themes)


def _validate(mapping, *, where: str) -> None:
    """Reject unknown keys and obviously malformed color lists."""
    unknown = set(mapping) - THEME_KEYS
    if unknown:
        import difflib
        hints = []
        for key in sorted(unknown):
            close = difflib.get_close_matches(key, THEME_KEYS, n=1)
            hints.append(f"{key!r}" + (f" (did you mean {close[0]!r}?)" if close else ""))
        raise ValueError(
            f"{where}: unknown theme key(s) {', '.join(hints)}. "
            f"Valid keys: {', '.join(sorted(THEME_KEYS))}."
        )

    colors = mapping.get("colors")
    if colors is not None:
        if isinstance(colors, str) or not hasattr(colors, "__iter__"):
            raise ValueError(f"{where}: 'colors' must be a list of color strings, "
                             f"got {type(colors).__name__}.")
        colors = list(colors)
        if not colors:
            raise ValueError(f"{where}: 'colors' must not be empty.")
        bad = [c for c in colors if not isinstance(c, str)]
        if bad:
            raise ValueError(f"{where}: 'colors' must contain only strings; "
                             f"found {type(bad[0]).__name__}.")


def register_theme(name: str, base: str = "default", **overrides) -> dict:
    """
    Register a named theme so it can be used anywhere a name is accepted.

    Custom themes work with ``Figure(theme=...)``, ``df.glyphx.*``,
    ``facet_plot``, ``clustermap``, ``Figure3D`` and the CLI -- all of which
    take a theme *name*, which previously meant a custom palette could only
    be used by passing a dict to :meth:`Figure.set_theme` and nowhere else.

    Args:
        name:       Name to register under. Must not collide with a built-in.
        base:       Existing theme to inherit unspecified keys from.
        **overrides: Any of ``colors``, ``axis_color``, ``grid_color``,
                    ``font``, ``background``, ``text_color``.

    Returns:
        dict: The fully resolved theme, also stored in the registry.

    Raises:
        ValueError: On a built-in name, an unknown base, an unknown key, or a
            malformed ``colors`` value.

    Example::

        from glyphx import Figure, register_theme

        register_theme(
            "acme",
            base="dark",
            colors=["#e6194b", "#3cb44b", "#4363d8"],
            font="Inter, sans-serif",
        )
        Figure(theme="acme").line(x, y).show()
    """
    if not isinstance(name, str) or not name:
        raise ValueError("Theme name must be a non-empty string.")
    if name in BUILTIN_THEMES:
        raise ValueError(
            f"{name!r} is a built-in theme and cannot be overwritten. "
            f"Pick another name, or pass base={name!r} to extend it."
        )
    if base not in themes:
        raise ValueError(f"Unknown base theme {base!r}. "
                         f"Available: {', '.join(list_themes())}.")

    _validate(overrides, where=f"register_theme({name!r})")

    resolved = dict(themes[base])
    resolved.update(overrides)
    if "colors" in resolved:
        resolved["colors"] = list(resolved["colors"])
    themes[name] = resolved
    return resolved


def unregister_theme(name: str) -> None:
    """Remove a custom theme. Built-ins cannot be removed.

    Raises:
        ValueError: If ``name`` is a built-in.
        KeyError:   If ``name`` is not registered.
    """
    if name in BUILTIN_THEMES:
        raise ValueError(f"{name!r} is a built-in theme and cannot be removed.")
    del themes[name]


def get_theme(spec=None) -> dict:
    """
    Resolve a theme name or dict into a complete theme dictionary.

    Args:
        spec: A registered theme name, a partial theme dict (missing keys are
            filled from ``"default"``), or ``None`` for the default.

    Returns:
        dict: A theme with every key in :data:`THEME_KEYS` populated.

    Raises:
        ValueError: If the name is not registered, or the dict is malformed.
            Previously an unknown name fell back to ``"default"`` silently, so
            a typo like ``theme="darkk"`` rendered a light chart with no
            indication anything was wrong.
    """
    if spec is None:
        return themes["default"]

    if isinstance(spec, dict):
        _validate(spec, where="get_theme(<dict>)")
        resolved = dict(themes["default"])
        resolved.update(spec)
        return resolved

    if not isinstance(spec, str):
        raise ValueError(f"Theme must be a name or a dict, got {type(spec).__name__}.")

    try:
        return themes[spec]
    except KeyError:
        import difflib
        close = difflib.get_close_matches(spec, themes, n=1)
        hint = f" Did you mean {close[0]!r}?" if close else ""
        raise ValueError(
            f"Unknown theme {spec!r}.{hint} "
            f"Available: {', '.join(list_themes())}. "
            f"Register your own with glyphx.register_theme()."
        ) from None
