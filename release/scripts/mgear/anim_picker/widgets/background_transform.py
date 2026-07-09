"""Qt/Maya-free move/scale math for background layer manipulation.

These functions operate on any object exposing ``position`` ([cx, cy], the layer
center) and ``size`` ([w, h]) -- i.e. ``BackgroundLayer`` -- so the on-canvas
manipulator's group-transform math stays testable without a running DCC.

The generic handle geometry (``handle_points`` / ``scale_factors``) lives in the
shared ``manipulator_transform`` module and is re-exported here for backward
compatibility; this module keeps only the layer-specific helpers (union bounds,
move, scale).

Bounds are expressed as ``(x, y, w, h)`` where ``(x, y)`` is the min corner in the
view's centered, Y-up scene space and ``w``/``h`` are positive.
"""

from mgear.anim_picker.widgets.manipulator_transform import HANDLE_IDS
from mgear.anim_picker.widgets.manipulator_transform import handle_points
from mgear.anim_picker.widgets.manipulator_transform import scale_factors

# Re-exported so existing importers (background_manipulator) keep working.
__all__ = [
    "HANDLE_IDS",
    "handle_points",
    "scale_factors",
    "union_bounds",
    "move_layers",
    "scale_layers",
]


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


def move_layers(layers, dx, dy):
    """Translate each layer's center by (dx, dy) in place.

    Args:
        layers (list): objects with ``position``.
        dx (float): x delta in scene units.
        dy (float): y delta in scene units.
    """
    for layer in layers:
        layer.position = [layer.position[0] + dx, layer.position[1] + dy]


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
