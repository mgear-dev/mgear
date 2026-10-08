"""mgear.core.deformer_io, node_remap.find_node and find_deformer_nodes test"""

import json
import logging

import pytest


def _evaluation_order(geometry):
    from mgear.core import deformer

    return list(reversed(deformer.get_deformer_stack(geometry)))


def _clustered_sphere():
    """Sphere deformed by clA, clB, clC (evaluation order)."""
    from maya import cmds

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="body")[0]
    for name in ("clA", "clB", "clC"):
        cmds.cluster(sphere, name=name)
    return sphere


def test_find_node(run_with_maya_standalone, setup_path, caplog):
    from maya import cmds
    from mgear.core import node_remap

    cmds.file(new=True, force=True)
    grp = cmds.createNode("transform", name="new_grp")
    cmds.createNode("transform", name="body", parent=grp)
    assert node_remap.find_node("|old_grp|body") == "|new_grp|body"
    assert node_remap.find_node("missing") is None
    assert node_remap.find_node(None) is None

    cmds.namespace(add="char")
    cmds.createNode("transform", name="char:head")
    assert node_remap.find_node("head") == "|char:head"

    other = cmds.createNode("transform", name="other_grp")
    cmds.createNode("transform", name="body", parent=other)
    with caplog.at_level(logging.WARNING, logger="mgear.core.node_remap"):
        assert node_remap.find_node("body") is None
    assert "Ambiguous" in caplog.text


def test_find_deformer_nodes(run_with_maya_standalone, setup_path):
    from mgear.core import deformer

    sphere = _clustered_sphere()
    assert deformer.find_deformer_nodes([sphere + ".vtx[3]"], "cluster") == [
        "clC",
        "clB",
        "clA",
    ]
    assert deformer.find_deformer_nodes(["clB", "missing", "clB"], "cluster") == ["clB"]
    assert deformer.find_deformer_nodes([sphere], "ffd") == []


def test_order_and_files(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.core import deformer_io

    assert deformer_io.resolve_order(None, "a") == "current"
    assert deformer_io.resolve_order("front", "sw1", {"sw2": "last"}) == "front"
    assert deformer_io.resolve_order("front", "sw1", {"sw1": "last"}) == "last"
    assert deformer_io.resolve_order("front", "sw1", "last") == "last"
    with pytest.raises(ValueError):
        deformer_io.resolve_order("middle", "sw1")

    assert deformer_io.file_path("C:/tmp/a", ".lat") == "C:/tmp/a.lat"
    assert deformer_io.file_path("C:/tmp/a.json", ".lat") == "C:/tmp/a.json"

    path = str(tmp_path / "data.lat")
    data = deformer_io.write_file(path, "lattice_config", 1, "lattices", [{"a": 1}])
    assert data["lattices"] == [{"a": 1}]
    assert deformer_io.load_file(path, "lattice_config")["schema_version"] == 1
    with pytest.raises(ValueError):
        deformer_io.load_file(path, "shrinkwrap_config")
    with open(path, "w") as f:
        json.dump([1, 2], f)
    with pytest.raises(ValueError):
        deformer_io.load_file(path, "lattice_config")


def test_geometry_round_trip(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer
    from mgear.core import deformer_io

    cmds.file(new=True, force=True)
    grp = cmds.createNode("transform", name="geo_grp")
    a = cmds.polySphere(name="a_geo")[0]
    b = cmds.polyCube(name="b_geo")[0]
    cmds.parent(a, b, grp)
    cluster = cmds.cluster(["a_geo", "b_geo"], name="cl1")[0]
    deformer.set_deformer_weights(cluster, 0, {3: 0.5})
    deformer.set_deformer_weights(cluster, 1, {1: 0.25})

    entries = deformer_io.get_geometry_data(cluster)
    assert [e["index"] for e in entries] == [0, 1]
    assert entries[0]["transform"] == "|geo_grp|a_geo"
    assert entries[0]["weights"] == {3: 0.5}
    assert entries[0]["deformer_stack"] == ["cl1"]

    cmds.delete(cluster)
    cmds.parent(["|geo_grp|a_geo", "|geo_grp|b_geo"], world=True)
    targets, geo_map = deformer_io.resolve_geometry(entries)
    assert sorted(targets) == ["|a_geo|a_geoShape", "|b_geo|b_geoShape"]

    new = cmds.cluster(targets, name="cl1")[0]
    deformer_io.apply_geometry_data(new, geo_map)
    result = {
        shape: deformer.get_deformer_weights(new, index)
        for index, shape in deformer.get_deformer_geometry(new)
    }
    assert result["|a_geo|a_geoShape"] == {3: pytest.approx(0.5)}
    assert result["|b_geo|b_geoShape"] == {1: pytest.approx(0.25)}

    # Sparse restore: only the painted weights are stored on the new node
    stored = cmds.getAttr(new + ".weightList[0].weights", multiIndices=True)
    assert stored == [3]


def test_resolve_geometry_members(run_with_maya_standalone, setup_path, caplog):
    from maya import cmds
    from mgear.core import deformer_io

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="body")[0]
    entries = [{"shape": "|body|bodyShape", "transform": "|body"}]
    members = ["body.vtx[0:3]", "body.vtx[7]", "missing.vtx[1]"]
    targets, geo_map = deformer_io.resolve_geometry(entries, members)
    assert targets == ["|body.vtx[0:3]", "|body.vtx[7]"]
    assert list(geo_map) == ["|body|bodyShape"]

    with caplog.at_level(logging.WARNING):
        targets, geo_map = deformer_io.resolve_geometry(
            [{"shape": "|gone|goneShape", "transform": "|gone"}]
        )
    assert targets == [] and geo_map == {}
    assert "not found" in caplog.text
    assert sphere


def test_placements(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer
    from mgear.core import deformer_io

    sphere = _clustered_sphere()
    shape = cmds.listRelatives(sphere, shapes=True, fullPath=True)[0]
    deformer.move_deformer("clC", sphere, after="clA")
    assert _evaluation_order(sphere) == ["clA", "clC", "clB"]
    entries = deformer_io.get_geometry_data("clC")
    cmds.delete("clC")

    for mode, expected in (
        ("current", ["clA", "clC", "clB"]),
        ("front", ["clC", "clA", "clB"]),
        ("last", ["clA", "clB", "clC"]),
    ):
        _, geo_map = deformer_io.resolve_geometry(entries)
        positions, front = deformer_io.resolve_placements("clC", geo_map, mode)
        assert front == (mode == "front")
        node = cmds.cluster(sphere, name="clC", frontOfChain=front)[0]
        deformer_io.apply_placements(node, positions)
        assert _evaluation_order(sphere) == expected, mode
        cmds.delete(node)

    # Current with the lower deformer gone: last
    cmds.delete("clA")
    _, geo_map = deformer_io.resolve_geometry(entries)
    positions, _ = deformer_io.resolve_placements("clC", geo_map, "current")
    assert positions[shape] == ("last", None)


def test_attrs_and_connections(run_with_maya_standalone, setup_path, caplog):
    from maya import cmds
    from mgear.core import deformer_io

    sphere = _clustered_sphere()
    ctl = cmds.createNode("transform", name="ctl")
    cmds.addAttr(ctl, longName="blend", minValue=0, maxValue=1, keyable=True)
    cmds.connectAttr(ctl + ".blend", "clA.envelope")
    cmds.setAttr("clB.relative", 1)

    attrs = deformer_io.get_attrs("clB", ("relative", "envelope", "missingAttr"))
    assert attrs == {"relative": True, "envelope": 1.0}
    connections = deformer_io.get_input_connections("clA")
    assert {"source": "|ctl.blend", "destination": "envelope"} in connections
    destinations = [c["destination"] for c in connections]
    assert not any(
        "inputGeometry" in d or "originalGeometry" in d for d in destinations
    )

    cmds.delete("clA")
    new = cmds.cluster(sphere, name="clA")[0]
    connected = deformer_io.restore_input_connections(new, connections)
    assert "envelope" in connected
    assert cmds.isConnected("ctl.blend", new + ".envelope")
    # Connected plugs are skipped, the others set
    deformer_io.set_attrs(new, {"envelope": 0.2, "relative": True}, skip=connected)
    assert cmds.getAttr(new + ".relative")

    cmds.delete(ctl)
    with caplog.at_level(logging.WARNING):
        connected = deformer_io.restore_input_connections(new, connections)
    assert "envelope" not in connected
    assert "not found" in caplog.text


def test_deformer_format(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.core import deformer_io

    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)

    def collect(node, order):
        if node == "bad":
            raise RuntimeError("bad node")
        return {"node": {"name": node}, "order": order}

    def build(config, replace, order):
        name = config["node"]["name"]
        if name == "skip":
            return None
        return cmds.createNode("transform", name=name)

    fmt = deformer_io.DeformerFormat(
        file_type="test_config",
        ext=".tst",
        items_key="nodes",
        name_key="node",
        label="test node",
        collect=collect,
        build=build,
    )
    data = fmt.export(["a_node", "bad", "skip", "b_node"], str(tmp_path / "f"))
    path = str(tmp_path / "f.tst")
    assert [fmt.name(c) for c in fmt.items(data)] == ["a_node", "skip", "b_node"]
    assert fmt.load(path)["schema_version"] == 1
    with pytest.raises(ValueError):
        fmt.export(["a_node"], path, order="middle")

    # One undo step, names filter, skipped builds
    created = fmt.import_file(path)
    assert created == ["a_node", "b_node"]
    cmds.undo()
    assert not cmds.ls("a_node", "b_node")
    assert fmt.import_file(path, names=["b_node"]) == ["b_node"]

    # Stored and overridden order modes, checked before building
    assert fmt.resolve_order(fmt.items(data)[0], {"a_node": "last"}) == "last"
    with pytest.raises(ValueError):
        fmt.import_file(path, order="middle")


def test_ramps_remap_and_missing_attrs(run_with_maya_standalone, setup_path, caplog):
    from maya import cmds
    from mgear.core import attribute
    from mgear.core import deformer
    from mgear.core import deformer_io

    cmds.file(new=True, force=True)
    cloth = cmds.polySphere(name="cloth")[0]
    cmds.polyCube(name="bodyA")
    cmds.polyCube(name="bodyB")
    node = cmds.deformer(cloth, type="proximityWrap", name="pw1")[0]
    deformer.add_proximity_wrap_drivers(node, ["bodyAShape", "bodyBShape"])

    # Node and driver ramps round trip
    entries = [[0.0, 1.0, 1], [0.4, 0.3, 2], [1.0, 0.0, 1]]
    for attr in ("falloffRamp", "drivers[1].driverFalloffRamp"):
        attribute.set_ramp(node, attr, entries)
        stored = attribute.get_ramp(node, attr)
        assert [e[2] for e in stored] == [1, 2, 1]
        for got, want in zip(stored, entries):
            assert got[:2] == pytest.approx(want[:2], abs=1e-5)
        attribute.set_ramp(node, attr, [[0.5, 0.5, 1]])
        assert len(attribute.get_ramp(node, attr)) == 1

    # Connection remap to another driver index
    ctl = cmds.createNode("transform", name="ctl")
    cmds.addAttr(ctl, longName="strength", keyable=True)
    connections = [
        {"source": "|ctl.strength", "destination": "drivers[3].driverStrength"}
    ]
    connected = deformer_io.restore_input_connections(
        node, connections, remap={"drivers": {3: 1}}
    )
    assert connected == {"drivers[1].driverStrength"}
    assert cmds.isConnected("ctl.strength", node + ".drivers[1].driverStrength")

    # The element is gone: skipped, no new multi element created
    connected = deformer_io.restore_input_connections(
        node, connections, remap={"drivers": {0: 0}}
    )
    assert connected == set()
    assert cmds.getAttr(node + ".drivers", multiIndices=True) == [0, 1]

    # Missing attributes are logged and skipped
    with caplog.at_level(logging.INFO, logger="mgear.core.deformer_io"):
        deformer_io.set_attrs(node, {"falloffScale": 2.0, "notAnAttr": 1})
    assert cmds.getAttr(node + ".falloffScale") == pytest.approx(2.0)
    assert "notAnAttr" in caplog.text
