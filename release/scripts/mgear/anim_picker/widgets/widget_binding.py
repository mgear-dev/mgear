"""Qt/Maya-free helpers for interactive picker widgets.

A picker item can be a plain *button* (the default) or an interactive
*widget* -- a checkbox, a 1D slider, or a 2D slider -- bound to a Maya
attribute and/or a script. This module holds the widget-type vocabulary, the
binding / script schema defaults, and the pure value-mapping math (normalize a
value into a ``[min, max]`` range and back). It has no Qt or Maya dependency,
so the mapping is unit-testable standalone, matching the pattern used by
``overlay``, ``mirror``, and ``manipulator_transform``.

The item stores two additive dictionaries alongside its ``widget`` type:

``binding``
    Which Maya attribute(s) the widget drives and over what range::

        {"attr": "node.attr", "min": 0.0, "max": 1.0,          # checkbox / 1D
         "attr_x": "node.tx", "min_x": -1.0, "max_x": 1.0,     # 2D X
         "attr_y": "node.ty", "min_y": -1.0, "max_y": 1.0,     # 2D Y
         "orientation": "horizontal", "recenter": False,
         "visibility_group": "", "visibility_invert": False}   # checkbox only

    A checkbox with a ``visibility_group`` is a group controller: toggling it
    shows / hides every item tagged with that group (``visibility_invert``
    flips the polarity). Both keys are optional, ignored by the other widgets.

``scripts``
    Optional per-state scripts run in addition to (or instead of) the
    attribute: ``on`` / ``off`` for a checkbox, ``value`` for a 1D slider,
    ``xy`` for a 2D slider.

All keys are optional; an absent attribute means "script only" and an absent
script means "attribute only".
"""


# Widget type vocabulary.
WIDGET_BUTTON = "button"
WIDGET_CHECKBOX = "checkbox"
WIDGET_SLIDER = "slider"
WIDGET_SLIDER2D = "slider2d"

WIDGET_TYPES = (
    WIDGET_BUTTON,
    WIDGET_CHECKBOX,
    WIDGET_SLIDER,
    WIDGET_SLIDER2D,
)

# 1D slider orientation.
ORIENT_HORIZONTAL = "horizontal"
ORIENT_VERTICAL = "vertical"


def is_interactive(widget_type):
    """Return True when ``widget_type`` is an interactive (non-button) widget.

    Args:
        widget_type (str): a value from ``WIDGET_TYPES``.

    Returns:
        bool: True for checkbox / slider / slider2d, False otherwise.
    """
    return bool(widget_type) and widget_type != WIDGET_BUTTON


def clamp(value, low, high):
    """Clamp ``value`` to the ``[low, high]`` range (order-insensitive)."""
    if low > high:
        low, high = high, low
    return max(low, min(high, value))


def normalize(value, low, high):
    """Return ``value``'s clamped 0..1 position within ``[low, high]``.

    Args:
        value (float): the value to normalize.
        low (float): range minimum.
        high (float): range maximum.

    Returns:
        float: 0.0 at ``low``, 1.0 at ``high`` (0.0 when the range is empty).
    """
    if high == low:
        return 0.0
    return clamp((value - low) / float(high - low), 0.0, 1.0)


def map_value(norm, low, high):
    """Map a 0..1 normalized value to the ``[low, high]`` range.

    Args:
        norm (float): normalized position (clamped to 0..1).
        low (float): range minimum.
        high (float): range maximum.

    Returns:
        float: the value at ``norm`` within the range.
    """
    return low + clamp(norm, 0.0, 1.0) * (high - low)


def track_bounds(left, right, top, bottom, inset=6.0):
    """Return the inset ``(x0, x1, y0, y1)`` slider-track bounds of a rect.

    Shared by the slider painter and the drag hit-test so the drawn handle and
    the cursor-to-value mapping use one inset convention (they must stay
    pixel-identical or the handle won't sit under the cursor).

    Args:
        left (float): rect left edge.
        right (float): rect right edge.
        top (float): rect top edge.
        bottom (float): rect bottom edge.
        inset (float, optional): pixels to inset the track from each edge.

    Returns:
        tuple: ``(x0, x1, y0, y1)`` inset track bounds.
    """
    return (left + inset, right - inset, top + inset, bottom - inset)


def default_binding():
    """Return a fresh binding dict with the schema's default ranges.

    Returns:
        dict: a binding populated with empty attributes and sane ranges.
    """
    return {
        "attr": "",
        "min": 0.0,
        "max": 1.0,
        "attr_x": "",
        "min_x": -1.0,
        "max_x": 1.0,
        "attr_y": "",
        "min_y": -1.0,
        "max_y": 1.0,
        "orientation": ORIENT_HORIZONTAL,
        "recenter": False,
        "visibility_group": "",
        "visibility_invert": False,
    }


# Default body shape (half sizes) per widget type, so a freshly created widget
# has a clean, type-appropriate proportion instead of the generic item shape.
_DEFAULT_HALF_SIZE = {
    WIDGET_CHECKBOX: (16.0, 9.0),
    WIDGET_SLIDER: (40.0, 8.0),
    WIDGET_SLIDER2D: (24.0, 24.0),
}


def default_handles(widget_type):
    """Return default rectangle corner handles for a widget type.

    Args:
        widget_type (str): a value from ``WIDGET_TYPES``.

    Returns:
        list: ``[[x, y], ...]`` corner handles (CCW), or None for a plain
        button (which keeps the generic item shape).
    """
    size = _DEFAULT_HALF_SIZE.get(widget_type)
    if not size:
        return None
    half_w, half_h = size
    return [
        [-half_w, -half_h],
        [half_w, -half_h],
        [half_w, half_h],
        [-half_w, half_h],
    ]


# Per-state script templates. A freshly created widget is seeded with these so
# it works out of the box (printing its value to the Script Editor) and doubles
# as an editable, self-documenting example. Keys: on/off (checkbox), value (1D
# slider), xy (2D slider).
SCRIPT_TEMPLATES = {
    "on": (
        "# Runs when the checkbox turns ON.\n"
        "# Available: __STATE__ (bool), __CONTROLS__, __NAMESPACE__, __SELF__.\n"
        "print('[anim_picker] checkbox ON ->', __STATE__)\n"
    ),
    "off": (
        "# Runs when the checkbox turns OFF.\n"
        "# Available: __STATE__ (bool), __CONTROLS__, __NAMESPACE__, __SELF__.\n"
        "print('[anim_picker] checkbox OFF ->', __STATE__)\n"
    ),
    "value": (
        "# Runs while dragging a 1D slider.\n"
        "# Available: __VALUE__ (float, mapped to min..max), __CONTROLS__, "
        "__SELF__.\n"
        "print('[anim_picker] slider value ->', __VALUE__)\n"
    ),
    "xy": (
        "# Runs while dragging a 2D slider.\n"
        "# Available: __X__ / __Y__ (floats), __CONTROLS__, __SELF__.\n"
        "print('[anim_picker] 2D slider ->', __X__, __Y__)\n"
    ),
}

# Which script keys apply to each widget type.
_TYPE_SCRIPT_KEYS = {
    WIDGET_CHECKBOX: ("on", "off"),
    WIDGET_SLIDER: ("value",),
    WIDGET_SLIDER2D: ("xy",),
}


def script_template(key):
    """Return the sample-snippet script for a widget script key (or "")."""
    return SCRIPT_TEMPLATES.get(key, "")


def default_scripts(widget_type):
    """Return the default per-state print scripts for a widget type.

    Args:
        widget_type (str): a value from ``WIDGET_TYPES``.

    Returns:
        dict: ``{state_key: script}`` seeded from ``SCRIPT_TEMPLATES``.
    """
    return {
        key: SCRIPT_TEMPLATES[key]
        for key in _TYPE_SCRIPT_KEYS.get(widget_type, ())
    }
