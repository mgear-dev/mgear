"""Qt/Maya-free layout math for the multi-tab tiled picker view.

`grid_shape` maps a tab count (and an optional fixed column count) to a
``(rows, cols)`` grid, driving the ``TiledPickerView`` Qt layout. Keeping it a
pure function -- no Qt or Maya -- lets it be unit-tested without a DCC, the same
pattern as ``overlay`` / ``mirror`` / ``manipulator_transform``.

The three tiled modes map onto it as:
    grid        columns=None  -> a near-square grid (ceil(sqrt(count)) columns)
    vertical    columns=1     -> one column, ``count`` rows
    horizontal  columns=count -> one row, ``count`` columns
"""

from math import ceil
from math import sqrt


def grid_shape(count, columns=None):
    """Return the ``(rows, cols)`` grid for ``count`` cells.

    Args:
        count (int): number of cells to lay out.
        columns (int, optional): fixed column count; when None a near-square
            grid is used (``ceil(sqrt(count))`` columns). Clamped to at least 1
            and at most ``count`` so there are no empty trailing columns.

    Returns:
        tuple: ``(rows, cols)`` -- ``(0, 0)`` when ``count`` is zero or less.
    """
    if count <= 0:
        return (0, 0)
    if columns is None:
        cols = int(ceil(sqrt(count)))
    else:
        cols = columns
    cols = max(1, min(int(cols), count))
    rows = int(ceil(count / float(cols)))
    return (rows, cols)
