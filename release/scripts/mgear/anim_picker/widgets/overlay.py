"""Qt/Maya-free anchor math for viewport-pinned picker items.

A pinned ("overlay" / HUD) picker item is placed by a viewport *anchor* -- one
of a 3x3 grid of screen regions (corners / edges / center) -- plus an inward
pixel *offset*. These pure functions convert an anchor + offset to a screen
point (and back), and snap a dropped point to its nearest grid cell, so the
placement logic lives in exactly one tested place with no Qt or Maya
dependency (the same pattern as ``mirror`` and ``manipulator_transform``).

An anchor is a two-character code ``<v><h>`` where ``v`` is the vertical band --
``t`` (top), ``m`` (middle), ``b`` (bottom) -- and ``h`` is the horizontal band
-- ``l`` (left), ``c`` (center), ``r`` (right). So ``"tl"`` is top-left,
``"mc"`` is the center, ``"br"`` is bottom-right.

The offset is measured *inward* from the anchor: from the top/left edge it grows
down/right, from the bottom/right edge it grows up/left, and from a middle /
center band it is a plain screen delta (down / right). This keeps a corner
button a fixed number of pixels from its corner as the viewport is resized.
"""


ANCHOR_CODES = (
    "tl",
    "tc",
    "tr",
    "ml",
    "mc",
    "mr",
    "bl",
    "bc",
    "br",
)

# Default placement for a freshly pinned item (top-left, a small inset).
DEFAULT_ANCHOR = "tl"
DEFAULT_OFFSET = (12, 12)

# Fractional position of each band's base line along the axis.
_V_BASE = {"t": 0.0, "m": 0.5, "b": 1.0}
_H_BASE = {"l": 0.0, "c": 0.5, "r": 1.0}

# Inward direction of the offset for each band (see module docstring).
_V_SIGN = {"t": 1.0, "m": 1.0, "b": -1.0}
_H_SIGN = {"l": 1.0, "c": 1.0, "r": -1.0}


def _split(anchor):
    """Return ``(v, h)`` band codes for ``anchor``, defaulting if invalid."""
    if (
        not anchor
        or len(anchor) != 2
        or anchor[0] not in _V_BASE
        or anchor[1] not in _H_BASE
    ):
        anchor = DEFAULT_ANCHOR
    return anchor[0], anchor[1]


def anchor_point(size, anchor, offset):
    """Return the screen point for an anchor + inward pixel offset.

    Args:
        size (tuple): viewport ``(width, height)`` in pixels.
        anchor (str): a two-character anchor code (see module docstring).
        offset (sequence): inward ``[dx, dy]`` pixel offset.

    Returns:
        tuple: the ``(x, y)`` screen point.
    """
    width, height = size
    v, h = _split(anchor)
    dx, dy = offset
    x = _H_BASE[h] * width + _H_SIGN[h] * dx
    y = _V_BASE[v] * height + _V_SIGN[v] * dy
    return (x, y)


def offset_from_anchor(size, anchor, point):
    """Return the inward offset of ``point`` from ``anchor`` (inverse of above).

    Args:
        size (tuple): viewport ``(width, height)`` in pixels.
        anchor (str): a two-character anchor code.
        point (sequence): the ``(x, y)`` screen point.

    Returns:
        tuple: the inward ``(dx, dy)`` pixel offset.
    """
    width, height = size
    v, h = _split(anchor)
    px, py = point
    dx = _H_SIGN[h] * (px - _H_BASE[h] * width)
    dy = _V_SIGN[v] * (py - _V_BASE[v] * height)
    return (dx, dy)


def nearest_anchor(size, point):
    """Return the anchor code of the 3x3 cell containing ``point``.

    Args:
        size (tuple): viewport ``(width, height)`` in pixels.
        point (sequence): the ``(x, y)`` screen point.

    Returns:
        str: the two-character anchor code of the nearest grid cell.
    """
    width, height = size
    px, py = point
    if px < width / 3.0:
        h = "l"
    elif px < 2.0 * width / 3.0:
        h = "c"
    else:
        h = "r"
    if py < height / 3.0:
        v = "t"
    elif py < 2.0 * height / 3.0:
        v = "m"
    else:
        v = "b"
    return v + h
