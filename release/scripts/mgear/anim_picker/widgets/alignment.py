"""Qt/Maya-free align + distribute math for multi-selected picker items.

Given each item's scene bounding box as an ``(x0, y0, x1, y1)`` tuple (with
``x0 <= x1`` and ``y0 <= y1``), these pure functions return the per-item
``(dx, dy)`` offset to align an edge / center, or to evenly distribute the
items along an axis. The caller applies the offsets to the items. No Qt or
Maya dependency, so the geometry is unit-testable standalone (matching the
``overlay`` / ``silhouette`` pattern).

Note: the picker view is Y-flipped (scene ``+y`` draws *up* on screen), so
``top`` aligns the maximum-y edges (visually highest) and ``bottom`` the
minimum-y edges.
"""


ALIGN_MODES = (
    "left",
    "hcenter",
    "right",
    "top",
    "vcenter",
    "bottom",
)


def align_offsets(rects, mode):
    """Return per-rect ``(dx, dy)`` offsets to align ``rects`` by ``mode``.

    Args:
        rects (list): ``(x0, y0, x1, y1)`` scene bounding boxes.
        mode (str): one of ``ALIGN_MODES``.

    Returns:
        list: ``(dx, dy)`` per rect (only one axis is non-zero per mode).
    """
    if not rects:
        return []
    x0 = [r[0] for r in rects]
    y0 = [r[1] for r in rects]
    x1 = [r[2] for r in rects]
    y1 = [r[3] for r in rects]

    if mode == "left":
        target = min(x0)
        return [(target - r[0], 0.0) for r in rects]
    if mode == "right":
        target = max(x1)
        return [(target - r[2], 0.0) for r in rects]
    if mode == "hcenter":
        target = (min(x0) + max(x1)) / 2.0
        return [(target - (r[0] + r[2]) / 2.0, 0.0) for r in rects]
    if mode == "top":  # visually highest -> maximum y under the Y-flip
        target = max(y1)
        return [(0.0, target - r[3]) for r in rects]
    if mode == "bottom":
        target = min(y0)
        return [(0.0, target - r[1]) for r in rects]
    if mode == "vcenter":
        target = (min(y0) + max(y1)) / 2.0
        return [(0.0, target - (r[1] + r[3]) / 2.0) for r in rects]
    return [(0.0, 0.0) for _ in rects]


def distribute_offsets(rects, axis, gap=8.0):
    """Return per-rect ``(dx, dy)`` to lay ``rects`` out with even edge gaps.

    Works from the bounding boxes (sizes), not just the centers, so it also
    spreads items that are stacked on top of one another:

    - When the items span more room than their combined size, the outer edges
      of the extremes stay put and the items are re-spaced so the **gaps
      between their edges are equal** (a true "distribute spacing").
    - When the items overlap / are stacked (no room to spread within their
      current span), they are packed edge-to-edge with a fixed ``gap`` and the
      run is centered on the cluster, so a pile of items fans out into a neat
      row / column.

    Args:
        rects (list): ``(x0, y0, x1, y1)`` scene bounding boxes.
        axis (str): ``"h"`` (horizontal) or ``"v"`` (vertical).
        gap (float): fallback edge gap (pixels) used when packing stacked items.

    Returns:
        list: ``(dx, dy)`` per rect (identity offsets when fewer than 2 rects).
    """
    count = len(rects)
    if count < 2:
        return [(0.0, 0.0)] * count

    # Axis-aligned min / max edge indices in the (x0, y0, x1, y1) tuple.
    lo_index, hi_index = (0, 2) if axis == "h" else (1, 3)
    los = [r[lo_index] for r in rects]
    his = [r[hi_index] for r in rects]
    sizes = [his[i] - los[i] for i in range(count)]
    centers = [(los[i] + his[i]) / 2.0 for i in range(count)]

    order = sorted(range(count), key=lambda i: centers[i])
    total_size = sum(sizes)
    extent_lo = min(los)
    extent_hi = max(his)
    free = (extent_hi - extent_lo) - total_size

    if free > 0:
        # Room to spread: equal edge gaps within the current extent, keeping
        # the leftmost / rightmost outer edges fixed.
        use_gap = free / (count - 1)
        cursor = extent_lo
    else:
        # Stacked / overlapping: pack edge-to-edge with a fixed gap, centered
        # on the cluster so the pile fans out symmetrically.
        use_gap = gap
        run = total_size + use_gap * (count - 1)
        cursor = (extent_lo + extent_hi) / 2.0 - run / 2.0

    offsets = [(0.0, 0.0)] * count
    for index in order:
        delta = cursor - los[index]
        offsets[index] = (delta, 0.0) if axis == "h" else (0.0, delta)
        cursor += sizes[index] + use_gap
    return offsets


def scale_spread_offsets(rects, axis, factor):
    """Return per-rect ``(dx, dy)`` scaling the selection spread about center.

    Each item's center is moved away from (``factor`` > 1) or toward
    (``factor`` < 1) the selection's bounding-box center on ``axis``, scaling
    the spacing while keeping the arrangement. Backs the expand / contract
    fine-tune tools (repeat clicks nudge the spread step by step). Items at the
    center do not move; a single item (or none) is a no-op.

    Args:
        rects (list): ``(x0, y0, x1, y1)`` scene bounding boxes.
        axis (str): ``"h"`` (horizontal) or ``"v"`` (vertical).
        factor (float): spread multiplier (> 1 expands, < 1 contracts).

    Returns:
        list: ``(dx, dy)`` per rect.
    """
    count = len(rects)
    if count < 2:
        return [(0.0, 0.0)] * count
    lo_index, hi_index = (0, 2) if axis == "h" else (1, 3)
    centers = [(r[lo_index] + r[hi_index]) / 2.0 for r in rects]
    origin = (min(centers) + max(centers)) / 2.0
    offsets = []
    for center in centers:
        delta = (center - origin) * (factor - 1.0)
        offsets.append((delta, 0.0) if axis == "h" else (0.0, delta))
    return offsets
