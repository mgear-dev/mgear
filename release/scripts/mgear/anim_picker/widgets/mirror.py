"""Qt/Maya-free mirror math for picker items.

Pure functions that reflect a picker item's data about a vertical symmetry axis
(scene ``x = axis_x``, default 0). They back both the one-shot Duplicate/Mirror
operations and the persistent live mirror relationships, so the reflection logic
lives in exactly one tested place -- the same pattern as ``manipulator_transform``.

Positions and handles are ``[x, y]``; colors are RGBA tuples/lists; rotation is in
degrees.
"""


def mirror_position(pos, axis_x=0.0):
    """Reflect a position about the vertical axis at ``axis_x``.

    Args:
        pos (list): ``[x, y]``.
        axis_x (float, optional): the mirror axis x (default 0).

    Returns:
        list: the mirrored ``[x, y]``.
    """
    return [2.0 * axis_x - pos[0], pos[1]]


def mirror_rotation(deg):
    """Reflect a rotation (degrees) about a vertical axis.

    A vertical mirror negates the rotation; the result is normalized to
    ``[0, 360)``.

    Args:
        deg (float): rotation in degrees.

    Returns:
        float: the mirrored rotation in degrees.
    """
    deg = deg % 360.0
    return (360.0 - deg) % 360.0


def mirror_handles(handles):
    """Reflect each handle's local x (shape mirror in the item frame).

    Args:
        handles (list): list of ``[x, y]``.

    Returns:
        list: mirrored list of ``[x, y]``.
    """
    return [[-handle[0], handle[1]] for handle in handles]


def mirror_color(rgba):
    """Swap the red and blue channels (left/right color convention).

    Args:
        rgba (sequence): ``[r, g, b, a]``.

    Returns:
        list: ``[b, g, r, a]``.
    """
    return [rgba[2], rgba[1], rgba[0], rgba[3]]
