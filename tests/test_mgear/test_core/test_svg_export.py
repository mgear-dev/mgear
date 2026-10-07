"""mgear.core.svg_export test"""


def _centered(subpaths):
    # parse_svg re-centres on the bounding box; do the same for comparison.
    from mgear.core import svg_import

    minx, miny, maxx, maxy = svg_import._bounds(subpaths)
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    return svg_import._map_subpaths(subpaths, lambda x, y: (x - cx, y - cy))


def _assert_close(a, b, tol=1e-3):
    assert len(a) == len(b)
    for sub_a, sub_b in zip(a, b):
        assert [s[0] for s in sub_a] == [s[0] for s in sub_b]
        for seg_a, seg_b in zip(sub_a, sub_b):
            for va, vb in zip(seg_a[1:], seg_b[1:]):
                assert abs(va - vb) < tol, (seg_a, seg_b)


def test_round_trip_through_svg_import(setup_path):
    from mgear.core import svg_export
    from mgear.core import svg_import
    from mgear.core import vector_path

    # y-up geometry, as the anim picker stores it.
    original = [
        vector_path.rectangle(0.0, 0.0, 20.0, 10.0, radius=2.0),
        vector_path.ellipse(30.0, 5.0, 5.0, 5.0),
    ]
    layers = [
        {"name": "Body", "subpaths": original[:1], "mode": "fill"},
        {"name": "Dot", "subpaths": original[1:], "mode": "stroke", "stroke_width": 2},
    ]
    text = svg_export.to_svg(layers, flip_y=True)
    minx, miny, maxx, maxy = vector_path.bounds(original)
    extent = max(maxx - minx, maxy - miny)

    parsed, dropped, _mode = svg_import.parse_svg(text, size=extent, flip_y=True)
    assert dropped == []
    _assert_close(parsed, _centered(original))


def test_layer_attributes(setup_path):
    from mgear.core import svg_export
    from mgear.core import vector_path

    square = [vector_path.rectangle(0.0, 0.0, 4.0, 4.0)]
    text = svg_export.to_svg(
        [
            {"name": "A & B", "subpaths": square, "mode": "fill"},
            {"subpaths": square, "mode": "stroke", "stroke_width": 3.0},
            {"subpaths": square, "visible": False},
        ],
        color="#ff0000",
    )
    assert text.count("<g ") == 2
    assert 'id="A &amp; B"' in text
    assert 'fill="#ff0000"' in text and 'fill-rule="evenodd"' in text
    assert 'stroke-width="3"' in text
    assert "M 0 0 L 4 0 L 4 4 L 0 4 Z" in text


def test_layer_color_overrides_default(setup_path):
    from mgear.core import svg_export
    from mgear.core import vector_path

    square = [vector_path.rectangle(0.0, 0.0, 4.0, 4.0)]
    text = svg_export.to_svg(
        [
            {"subpaths": square, "mode": "fill", "color": "#00ff00"},
            {"subpaths": square, "mode": "stroke"},
        ],
        color="#ff0000",
    )
    assert 'fill="#00ff00"' in text
    assert 'stroke="#ff0000"' in text
