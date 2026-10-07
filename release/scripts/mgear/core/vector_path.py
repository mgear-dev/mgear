"""Qt-free editing toolkit for normalized vector subpaths.

Works on the subpath format produced by ``mgear.core.svg_import``: a list of
subpaths, each a list of segments::

    ("M", x, y)                        start of the subpath
    ("L", x, y)                        straight segment
    ("C", x1, y1, x2, y2, x, y)        cubic Bezier segment
    ("Z",)                             closes the subpath

For editing, a subpath is viewed as a list of *nodes* (see ``to_nodes``). A
node is a dict ``{"anchor": (x, y), "in": (x, y) or None, "out": (x, y) or
None}`` where ``in`` / ``out`` are the curve handles of the segments entering
and leaving the anchor (None for a straight side). Nodes are addressed as
``(subpath_index, node_index)``; segment ``i`` runs from node ``i`` to node
``i + 1`` (wrapping to node 0 on a closed subpath).

Node type is not stored: it is derived from the handle geometry
(``node_type``). Every public operation returns new subpaths and leaves its
input unchanged. No Qt or Maya dependency, so everything is unit-testable in a
plain interpreter and reusable by any tool.
"""

import math

CORNER = "corner"
SMOOTH = "smooth"
SYMMETRIC = "symmetric"

# Distance under which two points are treated as the same point.
EPSILON = 1e-6

# Handle length ratio that approximates a quarter circle with one cubic.
KAPPA = 0.5522847498307936


#############################################
# POINT MATH
#############################################


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def _mul(a, s):
    return (a[0] * s, a[1] * s)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _length(a):
    return math.hypot(a[0], a[1])


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _normalize(a):
    length = _length(a)
    if length < EPSILON:
        return (0.0, 0.0)
    return (a[0] / length, a[1] / length)


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _same(a, b):
    return _distance(a, b) < EPSILON


#############################################
# NODES <-> SEGMENTS
#############################################


def _new_node(x, y):
    return {"anchor": (float(x), float(y)), "in": None, "out": None}


def _handle(anchor, point):
    """Return the handle point, or None when it sits on the anchor."""
    point = (float(point[0]), float(point[1]))
    return None if _same(anchor, point) else point


def copy_nodes(nodes):
    """Return a deep copy of a node list.

    Args:
        nodes (list): Node dicts.

    Returns:
        list: Independent copies of the nodes.
    """
    return [dict(node) for node in nodes]


def to_nodes(subpath):
    """Convert one subpath's segments to an editable node list.

    A closed subpath whose last point repeats its first is normalized so the
    repeated point is merged into node 0.

    Args:
        subpath (list): Segments of one subpath.

    Returns:
        tuple: (nodes, closed) with ``nodes`` a list of node dicts and
            ``closed`` a bool.
    """
    nodes = []
    closed = False
    for segment in subpath:
        command = segment[0]
        if command in ("M", "L"):
            nodes.append(_new_node(segment[1], segment[2]))
        elif command == "C":
            if not nodes:
                nodes.append(_new_node(segment[1], segment[2]))
            previous = nodes[-1]
            previous["out"] = _handle(previous["anchor"], segment[1:3])
            node = _new_node(segment[5], segment[6])
            node["in"] = _handle(node["anchor"], segment[3:5])
            nodes.append(node)
        elif command == "Z":
            closed = True
    if closed and len(nodes) > 1 and _same(nodes[0]["anchor"], nodes[-1]["anchor"]):
        last = nodes.pop()
        nodes[0]["in"] = last["in"]
    return nodes, closed


def _segment(start, end):
    """Return the segment tuple drawn from node ``start`` to node ``end``."""
    if start["out"] is None and end["in"] is None:
        return ("L",) + end["anchor"]
    c1 = start["out"] or start["anchor"]
    c2 = end["in"] or end["anchor"]
    return ("C",) + c1 + c2 + end["anchor"]


def from_nodes(nodes, closed):
    """Convert a node list back to subpath segments.

    Args:
        nodes (list): Node dicts.
        closed (bool): Whether the subpath is closed.

    Returns:
        list: Segments of one subpath (empty when there are no nodes).
    """
    if not nodes:
        return []
    subpath = [("M",) + nodes[0]["anchor"]]
    for index in range(1, len(nodes)):
        subpath.append(_segment(nodes[index - 1], nodes[index]))
    if closed:
        # A curved closing side needs an explicit segment; a straight one is
        # drawn by Z itself.
        if len(nodes) > 1 and (nodes[-1]["out"] or nodes[0]["in"]):
            subpath.append(_segment(nodes[-1], nodes[0]))
        subpath.append(("Z",))
    return subpath


def iter_segments(nodes, closed):
    """Yield every drawn segment of a node list.

    Args:
        nodes (list): Node dicts.
        closed (bool): Whether the subpath is closed.

    Yields:
        tuple: (index, p0, c1, c2, p3, is_line) where ``index`` is the start
            node and the points are the cubic control polygon.
    """
    count = len(nodes)
    total = count if closed and count > 1 else count - 1
    for index in range(max(total, 0)):
        start = nodes[index]
        end = nodes[(index + 1) % count]
        is_line = start["out"] is None and end["in"] is None
        yield (
            index,
            start["anchor"],
            start["out"] or start["anchor"],
            end["in"] or end["anchor"],
            end["anchor"],
            is_line,
        )


def visible_handles(nodes, closed):
    """Return the handles that shape a drawn segment.

    The ``in`` handle of the first node and the ``out`` handle of the last
    node of an open subpath shape nothing and are skipped.

    Args:
        nodes (list): Node dicts.
        closed (bool): Whether the subpath is closed.

    Returns:
        list: (node_index, "in" / "out", point) tuples.
    """
    handles = []
    last = len(nodes) - 1
    for index, node in enumerate(nodes):
        for which in ("in", "out"):
            point = node[which]
            if point is None:
                continue
            if not closed and (
                (which == "in" and index == 0) or (which == "out" and index == last)
            ):
                continue
            handles.append((index, which, point))
    return handles


def _replace(subpaths, index, nodes, closed):
    """Return a copy of ``subpaths`` with subpath ``index`` rebuilt."""
    result = [list(sub) for sub in subpaths]
    result[index] = from_nodes(nodes, closed)
    return result


#############################################
# CURVE EVALUATION AND BOUNDS
#############################################


def cubic_point(p0, c1, c2, p3, t):
    """Evaluate a cubic Bezier at parameter ``t``.

    Args:
        p0 (tuple): Start point.
        c1 (tuple): First control point.
        c2 (tuple): Second control point.
        p3 (tuple): End point.
        t (float): Parameter in [0, 1].

    Returns:
        tuple: The (x, y) point.
    """
    mt = 1.0 - t
    a = mt * mt * mt
    b = 3.0 * mt * mt * t
    c = 3.0 * mt * t * t
    d = t * t * t
    return (
        a * p0[0] + b * c1[0] + c * c2[0] + d * p3[0],
        a * p0[1] + b * c1[1] + c * c2[1] + d * p3[1],
    )


def _split_cubic(p0, c1, c2, p3, t):
    """De Casteljau split; returns (p01, p012, p0123, p123, p23)."""
    p01 = _lerp(p0, c1, t)
    p12 = _lerp(c1, c2, t)
    p23 = _lerp(c2, p3, t)
    p012 = _lerp(p01, p12, t)
    p123 = _lerp(p12, p23, t)
    return p01, p012, _lerp(p012, p123, t), p123, p23


def _extrema_parameters(a, b, c, d):
    """Return the parameters in (0, 1) where one cubic coordinate peaks."""
    qa = -a + 3.0 * b - 3.0 * c + d
    qb = 2.0 * (a - 2.0 * b + c)
    qc = b - a
    roots = []
    if abs(qa) < EPSILON:
        if abs(qb) > EPSILON:
            roots.append(-qc / qb)
    else:
        disc = qb * qb - 4.0 * qa * qc
        if disc >= 0.0:
            root = math.sqrt(disc)
            roots.extend(((-qb + root) / (2.0 * qa), (-qb - root) / (2.0 * qa)))
    return [t for t in roots if 0.0 < t < 1.0]


def bounds(subpaths):
    """Return the exact bounding box of the drawn curves.

    Args:
        subpaths (list): Subpaths.

    Returns:
        tuple: (min_x, min_y, max_x, max_y), or None when there is no
            geometry.
    """
    points = []
    for subpath in subpaths:
        nodes, closed = to_nodes(subpath)
        points.extend(node["anchor"] for node in nodes)
        for _index, p0, c1, c2, p3, is_line in iter_segments(nodes, closed):
            if is_line:
                continue
            for axis in (0, 1):
                for t in _extrema_parameters(p0[axis], c1[axis], c2[axis], p3[axis]):
                    points.append(cubic_point(p0, c1, c2, p3, t))
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


#############################################
# TRANSFORMS
#############################################


def map_points(subpaths, fn, indices=None):
    """Apply ``fn`` to every coordinate pair of the chosen subpaths.

    Args:
        subpaths (list): Subpaths.
        fn (callable): Takes and returns an (x, y) tuple.
        indices (iterable, optional): Subpath indices to transform; all
            subpaths when None.

    Returns:
        list: New subpaths.
    """
    chosen = None if indices is None else set(indices)
    result = []
    for index, subpath in enumerate(subpaths):
        if chosen is not None and index not in chosen:
            result.append(list(subpath))
            continue
        new_subpath = []
        for segment in subpath:
            coords = segment[1:]
            mapped = []
            for i in range(0, len(coords), 2):
                mapped.extend(fn((coords[i], coords[i + 1])))
            new_subpath.append((segment[0],) + tuple(mapped))
        result.append(new_subpath)
    return result


def translate(subpaths, dx, dy, indices=None):
    """Return subpaths moved by (dx, dy).

    Args:
        subpaths (list): Subpaths.
        dx (float): X offset.
        dy (float): Y offset.
        indices (iterable, optional): Subpath indices to move; all when None.

    Returns:
        list: New subpaths.
    """
    return map_points(subpaths, lambda p: (p[0] + dx, p[1] + dy), indices)


def scale(subpaths, sx, sy, origin=(0.0, 0.0), indices=None):
    """Return subpaths scaled about ``origin``.

    Args:
        subpaths (list): Subpaths.
        sx (float): X scale.
        sy (float): Y scale.
        origin (tuple, optional): Fixed point of the scale.
        indices (iterable, optional): Subpath indices to scale; all when None.

    Returns:
        list: New subpaths.
    """
    ox, oy = origin
    return map_points(
        subpaths,
        lambda p: (ox + (p[0] - ox) * sx, oy + (p[1] - oy) * sy),
        indices,
    )


def rotate(subpaths, degrees, origin=(0.0, 0.0), indices=None):
    """Return subpaths rotated counter-clockwise about ``origin``.

    Args:
        subpaths (list): Subpaths.
        degrees (float): Rotation angle.
        origin (tuple, optional): Center of rotation.
        indices (iterable, optional): Subpath indices to rotate; all when None.

    Returns:
        list: New subpaths.
    """
    angle = math.radians(degrees)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    ox, oy = origin

    def fn(p):
        x = p[0] - ox
        y = p[1] - oy
        return (ox + x * cos_a - y * sin_a, oy + x * sin_a + y * cos_a)

    return map_points(subpaths, fn, indices)


def flip(subpaths, horizontal=True, origin=(0.0, 0.0), indices=None):
    """Return subpaths mirrored about a vertical or horizontal line.

    Args:
        subpaths (list): Subpaths.
        horizontal (bool, optional): Mirror left-right when True, top-bottom
            when False.
        origin (tuple, optional): A point on the mirror line.
        indices (iterable, optional): Subpath indices to flip; all when None.

    Returns:
        list: New subpaths.
    """
    if horizontal:
        return scale(subpaths, -1.0, 1.0, origin, indices)
    return scale(subpaths, 1.0, -1.0, origin, indices)


#############################################
# HIT-TESTING
#############################################


def _closest_on_line(p0, p3, point):
    """Return (t, closest point) on segment p0-p3."""
    direction = _sub(p3, p0)
    length_sq = _dot(direction, direction)
    if length_sq < EPSILON:
        return 0.0, p0
    t = max(0.0, min(1.0, _dot(_sub(point, p0), direction) / length_sq))
    return t, _lerp(p0, p3, t)


def _closest_on_cubic(p0, c1, c2, p3, point, samples=32):
    """Return (t, closest point) on a cubic: sample, then refine."""
    best_t = 0.0
    best_d = None
    for i in range(samples + 1):
        t = float(i) / samples
        d = _distance(cubic_point(p0, c1, c2, p3, t), point)
        if best_d is None or d < best_d:
            best_t, best_d = t, d
    low = max(0.0, best_t - 1.0 / samples)
    high = min(1.0, best_t + 1.0 / samples)
    # Golden-section search on the bracketing interval.
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    for _ in range(30):
        a = high - ratio * (high - low)
        b = low + ratio * (high - low)
        da = _distance(cubic_point(p0, c1, c2, p3, a), point)
        db = _distance(cubic_point(p0, c1, c2, p3, b), point)
        if da < db:
            high = b
        else:
            low = a
    t = (low + high) / 2.0
    return t, cubic_point(p0, c1, c2, p3, t)


def hit_test(subpaths, x, y, tolerance, handle_nodes=None):
    """Find the nearest anchor, handle, or segment point to (x, y).

    Anchors take priority over handles, and handles over segments, so a
    node can always be picked even where its segments pass close by.

    Args:
        subpaths (list): Subpaths.
        x (float): Query x.
        y (float): Query y.
        tolerance (float): Maximum distance for a hit.
        handle_nodes (set, optional): ``(subpath, node)`` addresses whose
            handles are pickable; no handles when None.

    Returns:
        dict: ``{"kind": "anchor", "subpath", "node", "dist"}``,
            ``{"kind": "handle", "subpath", "node", "which", "dist"}``,
            ``{"kind": "segment", "subpath", "segment", "t", "point",
            "dist"}``, or None when nothing is within ``tolerance``.
    """
    point = (x, y)
    parsed = [to_nodes(subpath) for subpath in subpaths]

    best = None
    for si, (nodes, _closed) in enumerate(parsed):
        for ni, node in enumerate(nodes):
            d = _distance(node["anchor"], point)
            if d <= tolerance and (best is None or d < best["dist"]):
                best = {"kind": "anchor", "subpath": si, "node": ni, "dist": d}
    if best:
        return best

    for si, (nodes, closed) in enumerate(parsed):
        for ni, which, handle in visible_handles(nodes, closed):
            if handle_nodes is None or (si, ni) not in handle_nodes:
                continue
            d = _distance(handle, point)
            if d <= tolerance and (best is None or d < best["dist"]):
                best = {
                    "kind": "handle",
                    "subpath": si,
                    "node": ni,
                    "which": which,
                    "dist": d,
                }
    if best:
        return best

    for si, (nodes, closed) in enumerate(parsed):
        for index, p0, c1, c2, p3, is_line in iter_segments(nodes, closed):
            # The curve lies inside its control polygon: skip segments whose
            # box (grown by the tolerance) does not contain the point.
            xs = (p0[0], c1[0], c2[0], p3[0])
            ys = (p0[1], c1[1], c2[1], p3[1])
            if not (
                min(xs) - tolerance <= x <= max(xs) + tolerance
                and min(ys) - tolerance <= y <= max(ys) + tolerance
            ):
                continue
            if is_line:
                t, closest = _closest_on_line(p0, p3, point)
            else:
                t, closest = _closest_on_cubic(p0, c1, c2, p3, point)
            d = _distance(closest, point)
            if d <= tolerance and (best is None or d < best["dist"]):
                best = {
                    "kind": "segment",
                    "subpath": si,
                    "segment": index,
                    "t": t,
                    "point": closest,
                    "dist": d,
                }
    return best


#############################################
# NODE OPERATIONS
#############################################


def insert_node(subpaths, subpath_index, segment_index, t):
    """Insert a node on a segment without changing the curve.

    Args:
        subpaths (list): Subpaths.
        subpath_index (int): Subpath holding the segment.
        segment_index (int): Segment index (from node ``segment_index``).
        t (float): Parameter in (0, 1) where the node is inserted.

    Returns:
        list: New subpaths.
    """
    nodes, closed = to_nodes(subpaths[subpath_index])
    count = len(nodes)
    start = nodes[segment_index]
    end = nodes[(segment_index + 1) % count]
    if start["out"] is None and end["in"] is None:
        new_node = _new_node(*_lerp(start["anchor"], end["anchor"], t))
    else:
        p01, p012, p0123, p123, p23 = _split_cubic(
            start["anchor"],
            start["out"] or start["anchor"],
            end["in"] or end["anchor"],
            end["anchor"],
            t,
        )
        start["out"] = _handle(start["anchor"], p01)
        end["in"] = _handle(end["anchor"], p23)
        new_node = {
            "anchor": p0123,
            "in": _handle(p0123, p012),
            "out": _handle(p0123, p123),
        }
    nodes.insert(segment_index + 1, new_node)
    return _replace(subpaths, subpath_index, nodes, closed)


def delete_nodes(subpaths, addresses):
    """Delete nodes, joining their neighbours directly.

    A subpath left with fewer than two nodes is removed.

    Args:
        subpaths (list): Subpaths.
        addresses (iterable): ``(subpath, node)`` addresses to delete.

    Returns:
        list: New subpaths.
    """
    by_subpath = {}
    for si, ni in addresses:
        by_subpath.setdefault(si, set()).add(ni)
    result = []
    for si, subpath in enumerate(subpaths):
        if si not in by_subpath:
            result.append(list(subpath))
            continue
        nodes, closed = to_nodes(subpath)
        nodes = [n for i, n in enumerate(nodes) if i not in by_subpath[si]]
        if len(nodes) >= 2:
            result.append(from_nodes(nodes, closed))
    return result


def node_type(node):
    """Return the type implied by a node's handles.

    Args:
        node (dict): A node dict.

    Returns:
        str: ``SYMMETRIC`` (collinear, equal length), ``SMOOTH`` (collinear)
            or ``CORNER``.
    """
    if node["in"] is None or node["out"] is None:
        return CORNER
    v_in = _sub(node["in"], node["anchor"])
    v_out = _sub(node["out"], node["anchor"])
    l_in = _length(v_in)
    l_out = _length(v_out)
    if l_in < EPSILON or l_out < EPSILON:
        return CORNER
    cross = (v_in[0] * v_out[1] - v_in[1] * v_out[0]) / (l_in * l_out)
    dot = _dot(v_in, v_out) / (l_in * l_out)
    if abs(cross) < 1e-3 and dot < 0.0:
        if abs(l_in - l_out) <= 1e-3 * max(l_in, l_out, 1.0):
            return SYMMETRIC
        return SMOOTH
    return CORNER


def get_node(subpaths, address):
    """Return a copy of the node at ``address``.

    Args:
        subpaths (list): Subpaths.
        address (tuple): (subpath, node).

    Returns:
        dict: The node dict.
    """
    nodes, _closed = to_nodes(subpaths[address[0]])
    return dict(nodes[address[1]])


def set_node_type(subpaths, address, kind):
    """Convert a node to corner, smooth, or symmetric.

    Corner removes the node's handles (a sharp point). Smooth and symmetric
    make the handles collinear through the anchor, creating them along the
    neighbours' direction when the node has none; symmetric also makes them
    the same length.

    Args:
        subpaths (list): Subpaths.
        address (tuple): (subpath, node).
        kind (str): ``CORNER``, ``SMOOTH`` or ``SYMMETRIC``.

    Returns:
        list: New subpaths.
    """
    si, ni = address
    nodes, closed = to_nodes(subpaths[si])
    node = nodes[ni]
    anchor = node["anchor"]
    if kind == CORNER:
        node["in"] = None
        node["out"] = None
        return _replace(subpaths, si, nodes, closed)

    count = len(nodes)
    has_prev = closed or ni > 0
    has_next = closed or ni < count - 1
    prev_anchor = nodes[(ni - 1) % count]["anchor"] if has_prev else anchor
    next_anchor = nodes[(ni + 1) % count]["anchor"] if has_next else anchor

    if node["in"] is not None and node["out"] is not None:
        direction = _normalize(_sub(node["out"], node["in"]))
        l_in = _distance(node["in"], anchor)
        l_out = _distance(node["out"], anchor)
    else:
        direction = _normalize(_sub(next_anchor, prev_anchor))
        l_in = _distance(prev_anchor, anchor) / 3.0
        l_out = _distance(next_anchor, anchor) / 3.0
        existing = node["out"] or node["in"]
        if existing is not None:
            length = _distance(existing, anchor)
            l_in = l_in or length
            l_out = l_out or length
    if direction == (0.0, 0.0):
        direction = (1.0, 0.0)
    if kind == SYMMETRIC:
        l_in = l_out = (l_in + l_out) / 2.0
    node["in"] = _handle(anchor, _sub(anchor, _mul(direction, l_in)))
    node["out"] = _handle(anchor, _add(anchor, _mul(direction, l_out)))
    return _replace(subpaths, si, nodes, closed)


def move_anchors(subpaths, addresses, dx, dy):
    """Move anchors, carrying their handles with them.

    Args:
        subpaths (list): Subpaths.
        addresses (iterable): ``(subpath, node)`` addresses to move.
        dx (float): X offset.
        dy (float): Y offset.

    Returns:
        list: New subpaths.
    """
    by_subpath = {}
    for si, ni in addresses:
        by_subpath.setdefault(si, set()).add(ni)
    offset = (dx, dy)
    result = [list(sub) for sub in subpaths]
    for si, chosen in by_subpath.items():
        nodes, closed = to_nodes(subpaths[si])
        for ni in chosen:
            node = nodes[ni]
            node["anchor"] = _add(node["anchor"], offset)
            for which in ("in", "out"):
                if node[which] is not None:
                    node[which] = _add(node[which], offset)
        result[si] = from_nodes(nodes, closed)
    return result


def move_handle(subpaths, address, which, x, y, constraint=None):
    """Move one curve handle, keeping the node type when asked.

    Args:
        subpaths (list): Subpaths.
        address (tuple): (subpath, node).
        which (str): ``"in"`` or ``"out"``.
        x (float): New handle x.
        y (float): New handle y.
        constraint (str, optional): ``SMOOTH`` keeps the opposite handle
            collinear, ``SYMMETRIC`` also mirrors its length; None or
            ``CORNER`` moves the handle alone.

    Returns:
        list: New subpaths.
    """
    si, ni = address
    nodes, closed = to_nodes(subpaths[si])
    node = nodes[ni]
    anchor = node["anchor"]
    node[which] = _handle(anchor, (x, y))
    other = "out" if which == "in" else "in"
    vector = _sub((x, y), anchor)
    length = _length(vector)
    if constraint in (SMOOTH, SYMMETRIC) and length > EPSILON:
        if constraint == SYMMETRIC:
            other_length = length
        elif node[other] is not None:
            other_length = _distance(node[other], anchor)
        else:
            other_length = 0.0
        if other_length > EPSILON:
            node[other] = _sub(anchor, _mul(vector, other_length / length))
    return _replace(subpaths, si, nodes, closed)


#############################################
# PATH OPERATIONS
#############################################


def is_closed(subpath):
    """Return True when the subpath is closed.

    Args:
        subpath (list): Segments of one subpath.

    Returns:
        bool: Closed state.
    """
    return any(segment[0] == "Z" for segment in subpath)


def is_endpoint(subpaths, address):
    """Return True when ``address`` is the first or last node of an open path.

    Args:
        subpaths (list): Subpaths.
        address (tuple): (subpath, node).

    Returns:
        bool: Endpoint state.
    """
    nodes, closed = to_nodes(subpaths[address[0]])
    return not closed and address[1] in (0, len(nodes) - 1)


def split_at(subpaths, address):
    """Break a subpath at a node.

    An open subpath becomes two open subpaths sharing that node position; a
    closed subpath becomes one open subpath that starts and ends there.

    Args:
        subpaths (list): Subpaths.
        address (tuple): (subpath, node).

    Returns:
        list: New subpaths.
    """
    si, ni = address
    nodes, closed = to_nodes(subpaths[si])
    result = [list(sub) for sub in subpaths]
    if closed:
        rotated = copy_nodes(nodes[ni:] + nodes[:ni])
        end = dict(nodes[ni])
        rotated[0]["in"] = None
        end["out"] = None
        rotated.append(end)
        result[si] = from_nodes(rotated, False)
        return result
    if ni <= 0 or ni >= len(nodes) - 1:
        return result
    first = copy_nodes(nodes[: ni + 1])
    second = copy_nodes(nodes[ni:])
    first[-1]["out"] = None
    second[0]["in"] = None
    result[si] = from_nodes(first, False)
    result.insert(si + 1, from_nodes(second, False))
    return result


def _reversed_nodes(nodes):
    """Return nodes in reverse order with in / out handles swapped."""
    return [
        {"anchor": node["anchor"], "in": node["out"], "out": node["in"]}
        for node in reversed(nodes)
    ]


def join(subpaths, first, second):
    """Join two endpoints of open subpaths.

    Two endpoints of the same subpath close it. Endpoints of different
    subpaths merge them into one open subpath (replacing the first one);
    coincident endpoints merge into one node, otherwise a straight or curved
    segment connects them. Invalid input returns an unchanged copy.

    Args:
        subpaths (list): Subpaths.
        first (tuple): (subpath, node) endpoint.
        second (tuple): (subpath, node) endpoint.

    Returns:
        list: New subpaths.
    """
    result = [list(sub) for sub in subpaths]
    if not (is_endpoint(subpaths, first) and is_endpoint(subpaths, second)):
        return result
    si, ni = first
    sj, nj = second
    if si == sj:
        if ni == nj:
            return result
        return close_subpath(subpaths, si)

    nodes_a, _closed = to_nodes(subpaths[si])
    nodes_b, _closed = to_nodes(subpaths[sj])
    if ni == 0:
        nodes_a = _reversed_nodes(nodes_a)
    if nj == len(nodes_b) - 1:
        nodes_b = _reversed_nodes(nodes_b)
    if _same(nodes_a[-1]["anchor"], nodes_b[0]["anchor"]):
        merged = {
            "anchor": nodes_a[-1]["anchor"],
            "in": nodes_a[-1]["in"],
            "out": nodes_b[0]["out"],
        }
        nodes = nodes_a[:-1] + [merged] + nodes_b[1:]
    else:
        nodes = nodes_a + nodes_b
    result[si] = from_nodes(nodes, False)
    del result[sj]
    return result


def close_subpath(subpaths, index):
    """Close an open subpath with a segment back to its start.

    Args:
        subpaths (list): Subpaths.
        index (int): Subpath index.

    Returns:
        list: New subpaths.
    """
    nodes, _closed = to_nodes(subpaths[index])
    return _replace(subpaths, index, nodes, True)


def open_subpath(subpaths, index):
    """Open a closed subpath by removing its closing segment.

    Args:
        subpaths (list): Subpaths.
        index (int): Subpath index.

    Returns:
        list: New subpaths.
    """
    nodes, _closed = to_nodes(subpaths[index])
    if nodes:
        nodes[0]["in"] = None
        nodes[-1]["out"] = None
    return _replace(subpaths, index, nodes, False)


def reverse_subpath(subpaths, index):
    """Reverse a subpath's direction without changing its shape.

    Args:
        subpaths (list): Subpaths.
        index (int): Subpath index.

    Returns:
        list: New subpaths.
    """
    nodes, closed = to_nodes(subpaths[index])
    return _replace(subpaths, index, _reversed_nodes(nodes), closed)


#############################################
# PRIMITIVES
#############################################


def rectangle(x, y, width, height, radius=0.0):
    """Build a closed rectangle subpath, optionally with rounded corners.

    Args:
        x (float): One corner x.
        y (float): One corner y.
        width (float): Width (may be negative).
        height (float): Height (may be negative).
        radius (float, optional): Corner radius, clamped to half the
            shorter side.

    Returns:
        list: Segments of one closed subpath.
    """
    x0, x1 = sorted((x, x + width))
    y0, y1 = sorted((y, y + height))
    r = max(0.0, min(radius, (x1 - x0) / 2.0, (y1 - y0) / 2.0))
    if r < EPSILON:
        return [("M", x0, y0), ("L", x1, y0), ("L", x1, y1), ("L", x0, y1), ("Z",)]
    k = KAPPA * r
    return [
        ("M", x0 + r, y0),
        ("L", x1 - r, y0),
        ("C", x1 - r + k, y0, x1, y0 + r - k, x1, y0 + r),
        ("L", x1, y1 - r),
        ("C", x1, y1 - r + k, x1 - r + k, y1, x1 - r, y1),
        ("L", x0 + r, y1),
        ("C", x0 + r - k, y1, x0, y1 - r + k, x0, y1 - r),
        ("L", x0, y0 + r),
        ("C", x0, y0 + r - k, x0 + r - k, y0, x0 + r, y0),
        ("Z",),
    ]


def ellipse(cx, cy, rx, ry):
    """Build a closed ellipse subpath from four cubic segments.

    Args:
        cx (float): Center x.
        cy (float): Center y.
        rx (float): X radius.
        ry (float): Y radius.

    Returns:
        list: Segments of one closed subpath.
    """
    kx = KAPPA * rx
    ky = KAPPA * ry
    return [
        ("M", cx + rx, cy),
        ("C", cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry),
        ("C", cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy),
        ("C", cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry),
        ("C", cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy),
        ("Z",),
    ]


def _ring(cx, cy, radii, start_angle):
    """Build a closed polygon through points at the given radii."""
    count = len(radii)
    segments = []
    for i, radius in enumerate(radii):
        angle = math.radians(start_angle + 360.0 * i / count)
        point = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
        segments.append(("M" if i == 0 else "L",) + point)
    segments.append(("Z",))
    return segments


def regular_polygon(cx, cy, radius, sides, start_angle=90.0):
    """Build a closed regular polygon subpath.

    Args:
        cx (float): Center x.
        cy (float): Center y.
        radius (float): Distance from center to each corner.
        sides (int): Number of sides (at least 3).
        start_angle (float, optional): Angle of the first corner in degrees.

    Returns:
        list: Segments of one closed subpath.
    """
    return _ring(cx, cy, [radius] * max(3, int(sides)), start_angle)


def star(cx, cy, radius, points, inner_ratio=0.5, start_angle=90.0):
    """Build a closed star subpath.

    Args:
        cx (float): Center x.
        cy (float): Center y.
        radius (float): Outer radius.
        points (int): Number of star points (at least 3).
        inner_ratio (float, optional): Inner radius as a fraction of
            ``radius``.
        start_angle (float, optional): Angle of the first point in degrees.

    Returns:
        list: Segments of one closed subpath with ``2 * points`` nodes.
    """
    inner = radius * inner_ratio
    radii = []
    for _ in range(max(3, int(points))):
        radii.extend((radius, inner))
    return _ring(cx, cy, radii, start_angle)


def line(x0, y0, x1, y1):
    """Build an open two-node line subpath.

    Args:
        x0 (float): Start x.
        y0 (float): Start y.
        x1 (float): End x.
        y1 (float): End y.

    Returns:
        list: Segments of one open subpath.
    """
    return [("M", x0, y0), ("L", x1, y1)]


def arrow_points(tip, toward, length, width=None):
    """Return the two barb points of an arrowhead pointing at ``tip``.

    Args:
        tip (tuple): (x, y) point of the arrow.
        toward (tuple): (x, y) point the arrow comes from; sets its direction.
        length (float): Distance from the tip to the base.
        width (float, optional): Base width; ``length * 0.8`` when None.

    Returns:
        tuple: (left, right) barb points, or None when ``tip`` and ``toward``
            coincide or ``length`` is not positive.
    """
    direction = _normalize(_sub(tip, toward))
    if direction == (0.0, 0.0) or length <= 0.0:
        return None
    half = (length * 0.8 if width is None else width) / 2.0
    base = _sub(tip, _mul(direction, length))
    normal = (-direction[1], direction[0])
    return _add(base, _mul(normal, half)), _sub(base, _mul(normal, half))


def _end_direction(p_end, candidates):
    """Return the first candidate point distinct from ``p_end``."""
    for point in candidates:
        if not _same(point, p_end):
            return point
    return candidates[-1]


def add_arrows(subpath, start=False, end=False, length=3.0, width=None):
    """Return an open subpath with arrowheads drawn as part of its own path.

    Each arrowhead is a small loop inside the subpath (tip -> barb -> barb ->
    tip) pointing along the path's tangent at that end, so the line and its
    arrows stay one subpath: it fills as a solid triangle on a fill layer and
    draws the line plus an outlined head on a stroke layer. Closed subpaths
    are returned unchanged.

    Args:
        subpath (list): Segments of one subpath.
        start (bool, optional): Add an arrowhead at the first point.
        end (bool, optional): Add an arrowhead at the last point.
        length (float, optional): Arrowhead length.
        width (float, optional): Arrowhead base width (see ``arrow_points``).

    Returns:
        list: Segments of the resulting subpath.
    """
    nodes, closed = to_nodes(subpath)
    if closed or len(nodes) < 2 or not (start or end):
        return [tuple(segment) for segment in subpath]
    segments = list(iter_segments(nodes, False))
    result = from_nodes(nodes, False)
    if end:
        _i, p0, c1, c2, p3, _line = segments[-1]
        barbs = arrow_points(p3, _end_direction(p3, (c2, c1, p0)), length, width)
        if barbs:
            result += [("L",) + barbs[0], ("L",) + barbs[1], ("L",) + tuple(p3)]
    if start:
        _i, p0, c1, c2, p3, _line = segments[0]
        barbs = arrow_points(p0, _end_direction(p0, (c1, c2, p3)), length, width)
        if barbs:
            tip = tuple(p0)
            result = [
                ("M",) + tip,
                ("L",) + barbs[0],
                ("L",) + barbs[1],
                ("L",) + tip,
            ] + result[1:]
    return result


#############################################
# CURVE FITTING
#############################################


def _turn_angle(a, b, c):
    """Return the turning angle at ``b`` in degrees (0 = straight)."""
    v1 = _normalize(_sub(b, a))
    v2 = _normalize(_sub(c, b))
    dot = max(-1.0, min(1.0, _dot(v1, v2)))
    return math.degrees(math.acos(dot))


def _chord_parameters(points):
    lengths = [0.0]
    for i in range(1, len(points)):
        lengths.append(lengths[-1] + _distance(points[i - 1], points[i]))
    total = lengths[-1] or 1.0
    return [length / total for length in lengths]


def _generate_bezier(points, params, tan1, tan2):
    """Least-squares cubic through ``points`` with fixed end tangents."""
    first = points[0]
    last = points[-1]
    c00 = c01 = c11 = x0 = x1 = 0.0
    for point, u in zip(points, params):
        mu = 1.0 - u
        b0 = mu * mu * mu
        b1 = 3.0 * u * mu * mu
        b2 = 3.0 * u * u * mu
        b3 = u * u * u
        a1 = _mul(tan1, b1)
        a2 = _mul(tan2, b2)
        c00 += _dot(a1, a1)
        c01 += _dot(a1, a2)
        c11 += _dot(a2, a2)
        tmp = _sub(point, _add(_mul(first, b0 + b1), _mul(last, b2 + b3)))
        x0 += _dot(a1, tmp)
        x1 += _dot(a2, tmp)
    det = c00 * c11 - c01 * c01
    seg_length = _distance(first, last)
    alpha1 = alpha2 = 0.0
    if abs(det) > EPSILON:
        alpha1 = (x0 * c11 - c01 * x1) / det
        alpha2 = (c00 * x1 - x0 * c01) / det
    floor = 1e-6 * seg_length
    if alpha1 < floor or alpha2 < floor:
        alpha1 = alpha2 = seg_length / 3.0
    return (
        first,
        _add(first, _mul(tan1, alpha1)),
        _add(last, _mul(tan2, alpha2)),
        last,
    )


def _max_error(points, bezier, params):
    max_dist = 0.0
    split = len(points) // 2
    for i in range(1, len(points) - 1):
        d = _distance(cubic_point(*(bezier + (params[i],))), points[i])
        if d > max_dist:
            max_dist, split = d, i
    return max_dist, split


def _reparameterize(points, bezier, params):
    """One Newton-Raphson step towards each point's closest parameter."""
    p0, c1, c2, p3 = bezier
    result = []
    for point, u in zip(points, params):
        d1 = _add(
            _add(
                _mul(_sub(c1, p0), 3.0 * (1 - u) ** 2),
                _mul(_sub(c2, c1), 6.0 * (1 - u) * u),
            ),
            _mul(_sub(p3, c2), 3.0 * u * u),
        )
        d2 = _add(
            _mul(_add(_sub(c2, _mul(c1, 2.0)), p0), 6.0 * (1 - u)),
            _mul(_add(_sub(p3, _mul(c2, 2.0)), c1), 6.0 * u),
        )
        diff = _sub(cubic_point(p0, c1, c2, p3, u), point)
        denominator = _dot(d1, d1) + _dot(diff, d2)
        if abs(denominator) < EPSILON:
            result.append(u)
        else:
            result.append(min(1.0, max(0.0, u - _dot(diff, d1) / denominator)))
    return result


def _fit_run(points, tan1, tan2, tolerance, out):
    """Recursively fit cubics to a run of points (Schneider)."""
    if len(points) == 2:
        dist = _distance(points[0], points[1]) / 3.0
        out.append(
            (
                points[0],
                _add(points[0], _mul(tan1, dist)),
                _add(points[1], _mul(tan2, dist)),
                points[1],
            )
        )
        return
    params = _chord_parameters(points)
    bezier = _generate_bezier(points, params, tan1, tan2)
    error, split = _max_error(points, bezier, params)
    if error < tolerance:
        out.append(bezier)
        return
    if error < tolerance * 4.0:
        for _ in range(8):
            params = _reparameterize(points, bezier, params)
            bezier = _generate_bezier(points, params, tan1, tan2)
            error, split = _max_error(points, bezier, params)
            if error < tolerance:
                out.append(bezier)
                return
    split = max(1, min(len(points) - 2, split))
    center = _normalize(_sub(points[split - 1], points[split + 1]))
    if center == (0.0, 0.0):
        center = _normalize(_sub(points[split - 1], points[split]))
    _fit_run(points[: split + 1], tan1, center, tolerance, out)
    _fit_run(points[split:], _mul(center, -1.0), tan2, tolerance, out)


def _is_straight(bezier, tolerance):
    """Return True when a cubic's handles lie on its chord."""
    p0, c1, c2, p3 = bezier
    for control in (c1, c2):
        _t, closest = _closest_on_line(p0, p3, control)
        if _distance(closest, control) > tolerance:
            return False
    return True


def fit_curves(points, tolerance=0.25, corner_angle=50.0, closed=False):
    """Fit a polyline with as few cubic and straight segments as possible.

    The polyline is first split at corners (turns sharper than
    ``corner_angle``); each run between corners is fitted with cubics
    within ``tolerance``, and fitted cubics that are effectively straight
    become lines. Used to turn the flattened output of path booleans back
    into editable curves.

    Args:
        points (list): (x, y) points of the polyline.
        tolerance (float, optional): Maximum distance between the fit and
            the points.
        corner_angle (float, optional): Turn in degrees above which a point
            is kept as a sharp corner.
        closed (bool, optional): Whether the polyline is a closed loop.

    Returns:
        list: Segments of one subpath (empty for fewer than two points).
    """
    pts = []
    for point in points:
        point = (float(point[0]), float(point[1]))
        if not pts or not _same(pts[-1], point):
            pts.append(point)
    if closed and len(pts) > 1 and _same(pts[0], pts[-1]):
        pts.pop()
    if len(pts) < 2:
        return []

    count = len(pts)
    if closed:
        corners = [
            i
            for i in range(count)
            if _turn_angle(pts[i - 1], pts[i], pts[(i + 1) % count]) > corner_angle
        ]
        if corners:
            start = corners[0]
            pts = pts[start:] + pts[:start]
            corners = [(c - start) % count for c in corners]
        else:
            corners = [0]
        pts = pts + [pts[0]]
        corners = sorted(set(corners)) + [len(pts) - 1]
    else:
        corners = [0]
        corners += [
            i
            for i in range(1, count - 1)
            if _turn_angle(pts[i - 1], pts[i], pts[i + 1]) > corner_angle
        ]
        corners.append(count - 1)

    segments = [("M",) + pts[0]]
    for a, b in zip(corners[:-1], corners[1:]):
        run = pts[a : b + 1]
        if len(run) == 2:
            segments.append(("L",) + run[1])
            continue
        tan1 = _normalize(_sub(run[1], run[0]))
        tan2 = _normalize(_sub(run[-2], run[-1]))
        beziers = []
        _fit_run(run, tan1, tan2, tolerance, beziers)
        for bezier in beziers:
            if _is_straight(bezier, tolerance):
                segments.append(("L",) + bezier[3])
            else:
                segments.append(("C",) + bezier[1] + bezier[2] + bezier[3])
    if closed:
        segments.append(("Z",))
    return segments
