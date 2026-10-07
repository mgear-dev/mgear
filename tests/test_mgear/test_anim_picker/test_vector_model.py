"""mgear.anim_picker.widgets.vector_model test"""


def _square(offset=0.0):
    o = offset
    return [("M", o, o), ("L", o + 4, o), ("L", o + 4, o + 4), ("L", o, o + 4), ("Z",)]


def test_single_default_layer_writes_legacy_keys(setup_path):
    from mgear.anim_picker.widgets import vector_model as vm

    layers = [vm.new_layer(subpaths=[_square()], mode=vm.MODE_STROKE, stroke_width=3.0)]
    data = vm.svg_from_layers(layers, name="icon")
    assert set(data) == {"name", "subpaths", "mode", "stroke_width"}
    assert data["mode"] == vm.MODE_STROKE and data["stroke_width"] == 3.0
    assert data["subpaths"] == [_square()]


def test_multi_layer_writes_layers_and_fallback(setup_path):
    from mgear.anim_picker.widgets import vector_model as vm

    layers = [
        vm.new_layer("Body", [_square()], vm.MODE_FILL),
        vm.new_layer("Outline", [_square(10)], vm.MODE_STROKE, 2.5),
        vm.new_layer("Hidden", [_square(20)], visible=False),
    ]
    data = vm.svg_from_layers(layers)
    assert len(data["layers"]) == 3
    # Fallback: visible geometry only, bottom layer's style.
    assert data["subpaths"] == [_square(), _square(10)]
    assert data["mode"] == vm.MODE_FILL

    restored = vm.layers_from_svg(data)
    assert restored == layers


def test_flag_or_rename_forces_layers_key(setup_path):
    from mgear.anim_picker.widgets import vector_model as vm

    for kwargs in ({"locked": True}, {"visible": False}, {"name": "Body"}):
        layer = vm.new_layer(subpaths=[_square()])
        layer.update(kwargs)
        assert "layers" in vm.svg_from_layers([layer])


def test_legacy_data_loads_as_one_layer(setup_path):
    from mgear.anim_picker.widgets import vector_model as vm

    legacy = {"name": "gear", "subpaths": [_square()], "mode": vm.MODE_FILL}
    layers = vm.layers_from_svg(legacy)
    assert len(layers) == 1
    assert layers[0]["subpaths"] == [_square()]
    assert layers[0]["stroke_width"] == vm.DEFAULT_STROKE_WIDTH
    # Re-saving legacy data keeps the legacy format.
    assert "layers" not in vm.svg_from_layers(layers, "gear")
    assert vm.layers_from_svg({}) == []


def test_document_snapshot_and_map(setup_path):
    from mgear.anim_picker.widgets import vector_model as vm

    doc = vm.VectorDocument.from_svg_data({"subpaths": [_square()], "mode": "fill"})
    doc.selected_subpaths = {(0, 0)}
    state = doc.snapshot()
    doc.layers[0]["subpaths"] = []
    doc.clear_selection()
    assert doc.is_empty()
    doc.restore(state)
    assert doc.layers[0]["subpaths"] == [_square()]
    assert doc.selected_subpaths == {(0, 0)}

    moved = vm.map_layers(doc.layers, lambda subs: [s[:1] for s in subs])
    assert moved[0]["subpaths"] == [[("M", 0, 0)]]
    assert doc.layers[0]["subpaths"] == [_square()]

    # A new document always has one layer to draw on.
    assert len(vm.VectorDocument().layers) == 1


def test_layer_colors(setup_path):
    from mgear.anim_picker.widgets import vector_model as vm

    # A colored single layer keeps its color through a save.
    layer = vm.new_layer(subpaths=[_square()], color="#ff0000")
    data = vm.svg_from_layers([layer])
    assert "layers" in data
    assert vm.layers_from_svg(data)[0]["color"] == "#ff0000"

    # Legacy data and new layers default to the item color.
    assert vm.layers_from_svg({"subpaths": [_square()]})[0]["color"] is None
    assert not vm.has_layer_colors([vm.new_layer()])

    cleared = vm.clear_layer_colors([layer])
    assert cleared[0]["color"] is None and layer["color"] == "#ff0000"
    assert "layers" not in vm.svg_from_layers(cleared)
