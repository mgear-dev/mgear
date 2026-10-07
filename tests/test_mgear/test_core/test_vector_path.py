"""mgear.core.vector_path test"""

import copy
import math


def _close(a, b, tol=1e-6):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def _curve():
    # One open cubic subpath and one closed square.
    return [
        [("M", 0.0, 0.0), ("C", 2.0, 6.0, 8.0, 6.0, 10.0, 0.0)],
        [("M", 0.0, 0.0), ("L", 4.0, 0.0), ("L", 4.0, 4.0), ("L", 0.0, 4.0), ("Z",)],
    ]


def test_round_trip_nodes(setup_path):
    from mgear.core import vector_path as vp

    for subpath in _curve():
        nodes, closed = vp.to_nodes(subpath)
        assert vp.to_nodes(vp.from_nodes(nodes, closed)) == (nodes, closed)

    # A closed subpath repeating its start point merges into node 0.
    nodes, closed = vp.to_nodes(vp.ellipse(0.0, 0.0, 10.0, 5.0))
    assert closed and len(nodes) == 4


def test_insert_node_keeps_curve(setup_path):
    from mgear.core import vector_path as vp

    original = _curve()
    p0, c1, c2, p3 = (0.0, 0.0), (2.0, 6.0), (8.0, 6.0), (10.0, 0.0)
    t = 0.3
    result = vp.insert_node(original, 0, 0, t)
    nodes, _closed = vp.to_nodes(result[0])
    assert len(nodes) == 3
    first = [n for n in vp.iter_segments(nodes, False)]
    _i, a0, a1, a2, a3, _line = first[0]
    _i, b0, b1, b2, b3, _line = first[1]
    for i in range(11):
        s = i / 10.0
        assert _close(
            vp.cubic_point(a0, a1, a2, a3, s), vp.cubic_point(p0, c1, c2, p3, t * s)
        )
        assert _close(
            vp.cubic_point(b0, b1, b2, b3, s),
            vp.cubic_point(p0, c1, c2, p3, t + (1 - t) * s),
        )

    # Inserting on a straight side adds a handle-less node at the midpoint.
    result = vp.insert_node(original, 1, 0, 0.5)
    nodes, _closed = vp.to_nodes(result[1])
    assert len(nodes) == 5 and nodes[1]["anchor"] == (2.0, 0.0)
    assert nodes[1]["in"] is None and nodes[1]["out"] is None


def test_inputs_unchanged(setup_path):
    from mgear.core import vector_path as vp

    original = _curve()
    snapshot = copy.deepcopy(original)
    vp.insert_node(original, 0, 0, 0.5)
    vp.delete_nodes(original, [(1, 0)])
    vp.set_node_type(original, (1, 1), vp.SYMMETRIC)
    vp.move_anchors(original, [(1, 2)], 1.0, 1.0)
    vp.move_handle(original, (0, 1), "in", 5.0, 5.0, vp.SMOOTH)
    vp.split_at(original, (1, 2))
    vp.reverse_subpath(original, 0)
    vp.translate(original, 3.0, 3.0)
    assert original == snapshot


def test_reverse_twice_is_identity(setup_path):
    from mgear.core import vector_path as vp

    for index in (0, 1):
        normalized = [vp.from_nodes(*vp.to_nodes(sub)) for sub in _curve()]
        twice = vp.reverse_subpath(vp.reverse_subpath(normalized, index), index)
        assert twice == normalized


def test_node_types(setup_path):
    from mgear.core import vector_path as vp

    square = _curve()[1:]
    result = vp.set_node_type(square, (0, 1), vp.SYMMETRIC)
    node = vp.get_node(result, (0, 1))
    assert vp.node_type(node) == vp.SYMMETRIC
    v_in = (node["in"][0] - node["anchor"][0], node["in"][1] - node["anchor"][1])
    v_out = (node["out"][0] - node["anchor"][0], node["out"][1] - node["anchor"][1])
    assert abs(v_in[0] * v_out[1] - v_in[1] * v_out[0]) < 1e-9
    assert abs(math.hypot(*v_in) - math.hypot(*v_out)) < 1e-9

    corner = vp.set_node_type(result, (0, 1), vp.CORNER)
    node = vp.get_node(corner, (0, 1))
    assert node["in"] is None and node["out"] is None
    assert vp.node_type(node) == vp.CORNER

    # Dragging one handle of a smooth node keeps the other collinear.
    smooth = vp.set_node_type(square, (0, 1), vp.SMOOTH)
    moved = vp.move_handle(smooth, (0, 1), "out", 4.0, 8.0, vp.SMOOTH)
    assert vp.node_type(vp.get_node(moved, (0, 1))) in (vp.SMOOTH, vp.SYMMETRIC)


def test_primitives(setup_path):
    from mgear.core import vector_path as vp

    assert vp.bounds([vp.ellipse(0.0, 0.0, 10.0, 5.0)]) == (-10.0, -5.0, 10.0, 5.0)
    box = vp.bounds([vp.rectangle(0.0, 0.0, 20.0, 10.0, radius=4.0)])
    assert all(abs(a - b) < 1e-9 for a, b in zip(box, (0.0, 0.0, 20.0, 10.0)))
    nodes, closed = vp.to_nodes(vp.star(0.0, 0.0, 10.0, 5, 0.5))
    assert closed and len(nodes) == 10
    nodes, closed = vp.to_nodes(vp.regular_polygon(0.0, 0.0, 10.0, 6))
    assert closed and len(nodes) == 6
    nodes, closed = vp.to_nodes(vp.line(0.0, 0.0, 5.0, 5.0))
    assert not closed and len(nodes) == 2


def test_exact_bounds_of_curve(setup_path):
    from mgear.core import vector_path as vp

    # The curve peaks at y = 4.5 while its control points reach y = 6.
    min_x, min_y, max_x, max_y = vp.bounds(_curve()[:1])
    assert (min_x, min_y, max_x) == (0.0, 0.0, 10.0)
    assert abs(max_y - 4.5) < 1e-9


def test_hit_test(setup_path):
    from mgear.core import vector_path as vp

    subpaths = [vp.line(0.0, 0.0, 10.0, 0.0)]
    hit = vp.hit_test(subpaths, 5.0, 0.5, 1.0)
    assert hit["kind"] == "segment" and abs(hit["t"] - 0.5) < 1e-6
    assert vp.hit_test(subpaths, 5.0, 3.0, 1.0) is None
    assert vp.hit_test(subpaths, 0.2, 0.1, 1.0)["kind"] == "anchor"

    # Handles are only pickable for the listed nodes.
    curve = _curve()[:1]
    assert vp.hit_test(curve, 2.0, 6.0, 0.5) is None
    hit = vp.hit_test(curve, 2.0, 6.0, 0.5, handle_nodes={(0, 0)})
    assert hit["kind"] == "handle" and hit["which"] == "out"


def test_path_operations(setup_path):
    from mgear.core import vector_path as vp

    square = _curve()[1:]
    opened = vp.split_at(square, (0, 2))
    assert not vp.is_closed(opened[0])
    nodes, _closed = vp.to_nodes(opened[0])
    assert len(nodes) == 5 and nodes[0]["anchor"] == nodes[-1]["anchor"]

    lines = [vp.line(0.0, 0.0, 5.0, 0.0), vp.line(5.0, 0.0, 5.0, 5.0)]
    joined = vp.join(lines, (0, 1), (1, 0))
    assert len(joined) == 1
    assert len(vp.to_nodes(joined[0])[0]) == 3

    closed = vp.join(joined, (0, 0), (0, 2))
    assert vp.is_closed(closed[0])
    assert not vp.is_closed(vp.open_subpath(closed, 0)[0])

    # Deleting down to one node removes the subpath.
    assert vp.delete_nodes([vp.line(0, 0, 1, 1)], [(0, 0)]) == []


def test_fit_curves(setup_path):
    from mgear.core import vector_path as vp

    # A finely sampled circle comes back as a few cubics.
    points = [
        (10.0 * math.cos(2 * math.pi * i / 64), 10.0 * math.sin(2 * math.pi * i / 64))
        for i in range(64)
    ]
    fitted = vp.fit_curves(points, tolerance=0.05, closed=True)
    cubics = [s for s in fitted if s[0] == "C"]
    assert 2 <= len(cubics) <= 8
    for point in points:
        assert vp.hit_test([fitted], point[0], point[1], 0.1) is not None

    # A straight run stays one line; a polygon keeps its corners.
    straight = vp.fit_curves([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])
    assert straight == [("M", 0.0, 0.0), ("L", 3.0, 0.0)]
    square = vp.fit_curves([(0, 0), (4, 0), (4, 4), (0, 4)], closed=True)
    assert [s[0] for s in square] == ["M", "L", "L", "L", "L", "Z"]


def test_add_arrows(setup_path):
    from mgear.core import vector_path as vp

    line = vp.line(0.0, 0.0, 10.0, 0.0)
    arrowed = vp.add_arrows(line, end=True, length=4.0)
    # One open subpath: the shaft to the tip, then the head loop back to it.
    assert arrowed == [
        ("M", 0.0, 0.0),
        ("L", 10.0, 0.0),
        ("L", 6.0, 1.6),
        ("L", 6.0, -1.6),
        ("L", 10.0, 0.0),
    ]
    assert not vp.is_closed(arrowed)
    assert vp.bounds([arrowed]) == (0.0, -1.6, 10.0, 1.6)

    both = vp.add_arrows(line, start=True, end=True, length=4.0)
    assert both[0] == ("M", 0.0, 0.0) and both[3] == ("L", 0.0, 0.0)
    assert both[-1] == ("L", 10.0, 0.0) and len(both) == 8

    # A curved end follows the curve's tangent (its last handle).
    curve = [("M", 0.0, 0.0), ("C", 0.0, 5.0, 10.0, 5.0, 10.0, 0.0)]
    head = vp.add_arrows(curve, end=True, length=2.0)
    assert head[-3][2] > 0.0 and head[-2][2] > 0.0  # barbs sit above the tip

    # Closed shapes and arrows-off are returned unchanged.
    square = vp.rectangle(0.0, 0.0, 4.0, 4.0)
    assert vp.add_arrows(square, end=True) == square
    assert vp.add_arrows(line) == line
