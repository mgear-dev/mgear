"""Qt/Maya-free silhouette math for the *trace from selection* tool.

Tracing a control turns its 3D shape points into a flat picker button shaped
like the control's silhouette: project the world-space points onto a view
plane (front / side / top), reduce them to a 2D convex hull (the approximate
outline), and scale the whole traced set to fit the canvas. These three steps
are pure geometry with no Qt or Maya dependency, so they are unit-testable
standalone (the same pattern as ``overlay`` and ``mirror``); the Maya point
extraction lives in ``handlers.maya_handlers.get_shape_points``.

Plane mapping (Maya is Y-up):
    front -> world (x, y)
    side  -> world (z, y)
    top   -> world (x, z)
"""


PLANE_FRONT = "front"
PLANE_SIDE = "side"
PLANE_TOP = "top"

PLANES = (PLANE_FRONT, PLANE_SIDE, PLANE_TOP)


def project_to_plane(points, plane):
    """Project world-space 3D points onto a 2D view plane.

    Args:
        points (list): sequence of ``(x, y, z)`` world-space points.
        plane (str): one of ``PLANE_FRONT`` / ``PLANE_SIDE`` / ``PLANE_TOP``.

    Returns:
        list: ``(u, v)`` 2D points on the chosen plane.
    """
    result = []
    for point in points:
        x, y, z = point[0], point[1], point[2]
        if plane == PLANE_SIDE:
            result.append((z, y))
        elif plane == PLANE_TOP:
            result.append((x, z))
        else:  # front (default)
            result.append((x, y))
    return result


def _cross(origin, a, b):
    """2D cross product of vectors ``origin->a`` and ``origin->b``."""
    return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (
        b[0] - origin[0]
    )


def convex_hull_2d(points):
    """Return the convex hull of 2D points (counter-clockwise).

    Uses Andrew's monotone chain. Degenerate inputs are returned as-is: a
    single point stays one point, a collinear set collapses to its two
    extremes, and duplicate points are ignored.

    Args:
        points (list): sequence of ``(x, y)`` points.

    Returns:
        list: the hull vertices as ``(x, y)`` tuples, without repeating the
        first point at the end.
    """
    # Deduplicate and sort lexicographically (x, then y).
    pts = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(pts) <= 2:
        return pts

    # Build lower and upper hulls.
    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Concatenate, dropping each hull's last point (shared with the other).
    hull = lower[:-1] + upper[:-1]

    # A fully collinear set yields a degenerate hull; fall back to extremes.
    if len(hull) < 3:
        return [pts[0], pts[-1]]

    return hull


def bounding_box(points):
    """Return ``(min_x, min_y, max_x, max_y)`` of 2D points (None if empty)."""
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def fit_scale(bounds, target):
    """Return a uniform scale that fits ``bounds`` within ``target`` pixels.

    The scale maps the larger of the box's width / height to ``target`` so the
    traced set keeps its proportions. A zero-size box (a single point or a
    perfectly flat control) returns 1.0 rather than dividing by zero.

    Args:
        bounds (tuple): ``(min_x, min_y, max_x, max_y)`` in world units, or
            None.
        target (float): desired maximum span in canvas pixels.

    Returns:
        float: the uniform scale factor.
    """
    if not bounds:
        return 1.0
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    span = max(width, height)
    if span <= 0:
        return 1.0
    return float(target) / span


def centroid(points):
    """Return the average ``(x, y)`` of 2D points (``(0, 0)`` if empty)."""
    if not points:
        return (0.0, 0.0)
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    count = float(len(points))
    return (sx / count, sy / count)
