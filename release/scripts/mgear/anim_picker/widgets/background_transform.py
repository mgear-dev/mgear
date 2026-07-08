"""Qt/Maya-free move/scale math for background layer manipulation.

These functions operate on any object exposing ``position`` ([cx, cy], the layer
center) and ``size`` ([w, h]) -- i.e. ``BackgroundLayer`` -- so the on-canvas
manipulator's group-transform math stays testable without a running DCC.

Bounds are expressed as ``(x, y, w, h)`` where ``(x, y)`` is the min corner in the
view's centered, Y-up scene space and ``w``/``h`` are positive.
"""


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


def union_bounds(layers):
    """Return the union bounds of the given layers, or None when empty.

    Args:
        layers (list): objects with ``position`` and ``size``.

    Returns:
        tuple: ``(x, y, w, h)`` or None.
    """
    if not layers:
        return None
    min_x = min(layer.position[0] - layer.size[0] / 2.0 for layer in layers)
    max_x = max(layer.position[0] + layer.size[0] / 2.0 for layer in layers)
    min_y = min(layer.position[1] - layer.size[1] / 2.0 for layer in layers)
    max_y = max(layer.position[1] + layer.size[1] / 2.0 for layer in layers)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


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


def move_layers(layers, dx, dy):
    """Translate each layer's center by (dx, dy) in place.

    Args:
        layers (list): objects with ``position``.
        dx (float): x delta in scene units.
        dy (float): y delta in scene units.
    """
    for layer in layers:
        layer.position = [layer.position[0] + dx, layer.position[1] + dy]


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


def scale_layers(layers, anchor_x, anchor_y, sx, sy, min_size=1.0):
    """Scale each layer about (anchor_x, anchor_y) by (sx, sy) in place.

    Sizes are clamped to ``min_size`` so a layer never collapses or flips.

    Args:
        layers (list): objects with ``position`` and ``size``.
        anchor_x (float): fixed anchor x.
        anchor_y (float): fixed anchor y.
        sx (float): x scale factor.
        sy (float): y scale factor.
        min_size (float, optional): minimum layer width/height.
    """
    for layer in layers:
        cx, cy = layer.position
        w, h = layer.size
        layer.position = [
            anchor_x + (cx - anchor_x) * sx,
            anchor_y + (cy - anchor_y) * sy,
        ]
        layer.size = [max(w * sx, min_size), max(h * sy, min_size)]
