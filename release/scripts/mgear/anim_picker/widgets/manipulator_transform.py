"""Qt/Maya-free group-transform math shared by the on-canvas manipulators.

This is the tested geometry core behind both the background layer manipulator
(``background_manipulator``) and the picker item manipulator
(``item_manipulator``). It has no Qt or Maya dependency so the scale/rotate math
stays unit-testable without a running DCC.

Bounds are expressed as ``(x, y, w, h)`` where ``(x, y)`` is the min corner in
the view's centered scene space and ``w``/``h`` are positive. Rotation is in
degrees, positive counter-clockwise in that scene space.
"""

import math


HANDLE_IDS = ("bl", "br", "tl", "tr", "l", "r", "t", "b")

# Opposite handle used as the fixed anchor while scaling.
_OPPOSITE = {
    "bl": "tr",
    "tr": "bl",
    "br": "tl",
    "tl": "br",
    "l": "r",
    "r": "l",
    "b": "t",
    "t": "b",
}

_SCALES_X = ("bl", "br", "tl", "tr", "l", "r")
_SCALES_Y = ("bl", "br", "tl", "tr", "t", "b")


def handle_points(bounds):
    """Return a dict of handle id -> (x, y) for the given bounds.

    Args:
        bounds (tuple): ``(x, y, w, h)``.

    Returns:
        dict: handle id -> (x, y).
    """
    x, y, w, h = bounds
    return {
        "bl": (x, y),
        "br": (x + w, y),
        "tl": (x, y + h),
        "tr": (x + w, y + h),
        "l": (x, y + h / 2.0),
        "r": (x + w, y + h / 2.0),
        "b": (x + w / 2.0, y),
        "t": (x + w / 2.0, y + h),
    }


def scale_factors(bounds, handle_id, cursor_x, cursor_y, keep_aspect=False):
    """Compute the anchor and scale factors for a handle drag.

    Corner handles scale both axes, edge handles scale one; ``keep_aspect``
    forces a uniform factor. The anchor is the opposite handle's position.

    Args:
        bounds (tuple): original ``(x, y, w, h)`` at drag start.
        handle_id (str): one of ``HANDLE_IDS``.
        cursor_x (float): current cursor x in scene units.
        cursor_y (float): current cursor y in scene units.
        keep_aspect (bool, optional): keep the aspect ratio.

    Returns:
        tuple: ``(anchor_x, anchor_y, sx, sy)``.
    """
    x, y, w, h = bounds
    anchor_x, anchor_y = handle_points(bounds)[_OPPOSITE[handle_id]]

    scales_x = handle_id in _SCALES_X
    scales_y = handle_id in _SCALES_Y

    sx = abs(cursor_x - anchor_x) / w if (scales_x and w) else 1.0
    sy = abs(cursor_y - anchor_y) / h if (scales_y and h) else 1.0

    if keep_aspect:
        if scales_x and scales_y:
            sx = sy = max(sx, sy)
        elif scales_x:
            sy = sx
        elif scales_y:
            sx = sy

    return anchor_x, anchor_y, sx, sy


def rotate_delta(cx, cy, from_x, from_y, to_x, to_y):
    """Return the signed rotation (degrees) from one cursor point to another.

    Both points are taken relative to the pivot ``(cx, cy)``; the result is the
    angle swept from ``(from_x, from_y)`` to ``(to_x, to_y)``, positive
    counter-clockwise.

    Args:
        cx (float): pivot x.
        cy (float): pivot y.
        from_x (float): drag-start cursor x.
        from_y (float): drag-start cursor y.
        to_x (float): current cursor x.
        to_y (float): current cursor y.

    Returns:
        float: signed angle in degrees.
    """
    start = math.atan2(from_y - cy, from_x - cx)
    current = math.atan2(to_y - cy, to_x - cx)
    return math.degrees(current - start)


def rotate_point(x, y, cx, cy, deg):
    """Rotate a point about a pivot by ``deg`` degrees (CCW positive).

    Args:
        x (float): point x.
        y (float): point y.
        cx (float): pivot x.
        cy (float): pivot y.
        deg (float): rotation in degrees.

    Returns:
        tuple: the rotated ``(x, y)``.
    """
    rad = math.radians(deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    dx = x - cx
    dy = y - cy
    return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)
