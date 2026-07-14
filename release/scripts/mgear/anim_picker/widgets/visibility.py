"""Qt/Maya-free evaluation of a picker item's visibility condition.

A picker item can carry an optional *visibility condition* that decides whether
it is shown in animation mode. Two modes are supported:

``channel``
    Show only when a Maya attribute satisfies a comparison against a
    threshold::

        {"mode": "channel", "attr": "node.attr",
         "operator": ">=", "threshold": 0.5}

``zoom``
    Show only when the view zoom scale falls within an optional range (either
    bound may be omitted for an open-ended range)::

        {"mode": "zoom", "min_zoom": 1.5, "max_zoom": None}

This module holds only the pure decision: given a condition and a *context*
(the current zoom and, for a channel condition, the already-read attribute
value), it returns whether the item is visible. The Maya attribute read and the
Qt ``setVisible`` live in ``PickerItem`` / ``view``; this stays unit-testable
standalone, matching ``overlay``, ``alignment``, and ``widget_binding``.

Fail-open rule: an empty or malformed condition, or a channel condition whose
attribute could not be read (value is None), evaluates to *visible*. A
mis-authored condition must never hide a control with no obvious way to get it
back.
"""


# Visibility condition modes.
VIS_NONE = ""
VIS_ZOOM = "zoom"
VIS_CHANNEL = "channel"

# Comparison operators for a channel condition, in menu order.
OPERATORS = (
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
)

# Float tolerance for equality comparisons.
_EPSILON = 1e-6


def compare(value, operator, threshold):
    """Return the truth of ``value <operator> threshold`` numerically.

    Equality (``==`` / ``!=``) uses a small tolerance so float channel values
    compare sensibly. An unknown operator returns True (fail-open).

    Args:
        value (float): the left-hand value (e.g. an attribute value).
        operator (str): one of ``OPERATORS``.
        threshold (float): the right-hand value to compare against.

    Returns:
        bool: the comparison result.
    """
    try:
        value = float(value)
        threshold = float(threshold)
    except (TypeError, ValueError):
        return True
    if operator == "==":
        return abs(value - threshold) <= _EPSILON
    if operator == "!=":
        return abs(value - threshold) > _EPSILON
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    return True


def in_range(zoom, min_zoom, max_zoom):
    """Return True when ``zoom`` is within ``[min_zoom, max_zoom]``.

    Either bound may be None for an open-ended range; when both are None the
    range is unbounded and the result is always True.

    Args:
        zoom (float): the current view zoom scale.
        min_zoom (float): lower bound, or None for no lower bound.
        max_zoom (float): upper bound, or None for no upper bound.

    Returns:
        bool: whether ``zoom`` lies within the range.
    """
    if min_zoom is not None and zoom < min_zoom:
        return False
    if max_zoom is not None and zoom > max_zoom:
        return False
    return True


def evaluate(condition, context):
    """Return whether an item is visible for ``condition`` under ``context``.

    Args:
        condition (dict): the item's visibility condition, or a falsy value
            when the item has no condition.
        context (dict): ``{"zoom": float, "value": <attr value or None>}`` --
            ``value`` is the already-read channel attribute value (the Maya
            read happens in the caller), or None when there is no value / attr.

    Returns:
        bool: True to show the item, False to hide it. Fail-open: an empty or
        malformed condition, or a channel condition with no readable value,
        returns True.
    """
    if not condition:
        return True
    context = context or {}
    mode = condition.get("mode")

    if mode == VIS_CHANNEL:
        value = context.get("value")
        if value is None:
            return True
        return compare(
            value,
            condition.get("operator", ">="),
            condition.get("threshold", 0.0),
        )

    if mode == VIS_ZOOM:
        return in_range(
            context.get("zoom", 1.0),
            condition.get("min_zoom"),
            condition.get("max_zoom"),
        )

    # Unknown / VIS_NONE mode: fail open.
    return True
