"""mgear.core.deformer stack order, weight map and lattice helpers test"""

import pytest


def _lattice_scene(divisions=(2, 3, 4)):
    from maya import cmds

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="sphere")[0]
    ffd, lattice, base = cmds.lattice(
        sphere, divisions=divisions, objectCentered=True, name="ffd1"
    )
    return sphere, ffd, lattice, base


def _evaluation_order(geometry):
    from mgear.core import deformer

    return list(reversed(deformer.get_deformer_stack(geometry)))


def test_get_deformer_stack_and_move(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="sphere")[0]
    joint = cmds.joint(name="j1")
    cmds.select(clear=True)
    cmds.skinCluster(joint, sphere, name="skinA")
    cmds.cluster(sphere, name="clB")
    cmds.cluster(sphere, name="clC")
    cmds.lattice(sphere, frontOfChain=False, name="ffd1")

    assert deformer.get_deformer_stack(sphere)[0] == "ffd1"
    assert _evaluation_order(sphere) == ["skinA", "clB", "clC", "ffd1"]

    deformer.move_deformer("ffd1", sphere, after="skinA")
    assert _evaluation_order(sphere) == ["skinA", "ffd1", "clB", "clC"]

    # Already in place: no change
    deformer.move_deformer("ffd1", sphere, after="skinA")
    assert _evaluation_order(sphere) == ["skinA", "ffd1", "clB", "clC"]

    deformer.move_deformer("ffd1", sphere)
    assert _evaluation_order(sphere) == ["ffd1", "skinA", "clB", "clC"]

    # After the last evaluated deformer: back to the top of the stack
    deformer.move_deformer("ffd1", sphere, after="clC")
    assert _evaluation_order(sphere) == ["skinA", "clB", "clC", "ffd1"]

    with pytest.raises(ValueError):
        deformer.move_deformer("ffd1", sphere, after="missing")
    with pytest.raises(ValueError):
        deformer.move_deformer("missing", sphere)


def test_get_deformer_geometry(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    a = cmds.polyCube(name="a")[0]
    b = cmds.polyCube(name="b")[0]
    ffd = cmds.lattice([a, b])[0]
    assert deformer.get_deformer_geometry(ffd) == [
        (0, "|a|aShape"),
        (1, "|b|bShape"),
    ]


def test_deformer_weights(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    sphere, ffd, _, _ = _lattice_scene()
    assert deformer.get_deformer_weights(ffd, 0) == {}
    with pytest.raises(ValueError):
        deformer.get_deformer_weights(ffd, 5)

    cmds.setAttr("{}.weightList[0].weights[3]".format(ffd), 0.5)
    cmds.setAttr("{}.weightList[0].weights[7]".format(ffd), 0.5)
    weights = deformer.get_deformer_weights(ffd, 0)
    assert weights == {3: pytest.approx(0.5), 7: pytest.approx(0.5)}

    dense = deformer.get_deformer_weights(ffd, 0, sparse=False)
    assert len(dense) == 382
    assert dense[0] == 1.0
    assert dense[3] == pytest.approx(0.5)

    # Round trip, string keys and out of range indices
    deformer.set_deformer_weights(ffd, 0, {})
    assert deformer.get_deformer_weights(ffd, 0) == {}
    deformer.set_deformer_weights(ffd, 0, weights)
    assert deformer.get_deformer_weights(ffd, 0) == weights
    deformer.set_deformer_weights(ffd, 0, {"3": 0.25, "9999": 0.1})
    assert deformer.get_deformer_weights(ffd, 0) == {3: pytest.approx(0.25)}

    with pytest.raises(ValueError):
        deformer.set_deformer_weights(ffd, 4, {})


def test_deformer_weights_nurbs(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    surface = cmds.nurbsPlane(patchesU=2, patchesV=2)[0]
    ffd = cmds.lattice(surface)[0]
    deformer.set_deformer_weights(ffd, 0, {2: 0.3})
    assert deformer.get_deformer_weights(ffd, 0) == {2: pytest.approx(0.3)}


def test_find_ffd_and_lattice_nodes(run_with_maya_standalone, setup_path):
    from mgear.core import deformer

    sphere, ffd, lattice, base = _lattice_scene()
    assert deformer.get_ffd_nodes() == [ffd]
    assert deformer.find_ffd_nodes([sphere + ".vtx[3]"]) == [ffd]
    assert deformer.find_ffd_nodes([lattice]) == [ffd]
    assert deformer.find_ffd_nodes([base, ffd, "missing"]) == [ffd]

    lat_tfm, lat_shape, base_tfm, base_shape = deformer.get_lattice_nodes(ffd)
    assert lat_tfm == "|" + lattice
    assert lat_shape.startswith(lat_tfm + "|")
    assert base_tfm == "|" + base
    assert base_shape.startswith(base_tfm + "|")


def test_lattice_points(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    _, ffd, lattice, _ = _lattice_scene()
    cmds.xform(lattice + ".pt[1][2][3]", objectSpace=True, translation=(1, 2, 3))
    cmds.xform(lattice + ".pt[0][1][2]", objectSpace=True, translation=(4, 5, 6))
    assert deformer.get_lattice_divisions(lattice) == [2, 3, 4]

    points = deformer.get_lattice_points(lattice)
    assert len(points) == 24
    for s in range(2):
        for t in range(3):
            for u in range(4):
                expected = cmds.xform(
                    "{}.pt[{}][{}][{}]".format(lattice, s, t, u),
                    query=True,
                    objectSpace=True,
                    translation=True,
                )
                point = points[s * 12 + t * 4 + u]
                assert point == pytest.approx(expected, abs=1e-6)

    # Write then read, undo
    new_points = [[i * 0.1, i * 0.2, -i * 0.3] for i in range(24)]
    cmds.undoInfo(state=True, infinity=True)
    cmds.undoInfo(openChunk=True)
    deformer.set_lattice_points(lattice, [2, 3, 4], new_points)
    cmds.undoInfo(closeChunk=True)
    read = deformer.get_lattice_points(lattice, [2, 3, 4])
    for got, want in zip(read, new_points):
        assert got == pytest.approx(want, abs=1e-6)
    cmds.undo()
    assert deformer.get_lattice_points(lattice)[23] == pytest.approx([1, 2, 3])

    with pytest.raises(ValueError):
        deformer.set_lattice_points(lattice, [2, 3, 4], new_points[:-1])


def test_delete_lattice(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    sphere, ffd, lattice, base = _lattice_scene()
    deformer.delete_lattice(ffd)
    for node in (ffd, lattice, base):
        assert not cmds.objExists(node)
    assert cmds.objExists(sphere)


def _proximity_scene():
    from maya import cmds

    cmds.file(new=True, force=True)
    cloth = cmds.polySphere(name="cloth", radius=1.2)[0]
    body = cmds.polyCube(name="body")[0]
    return cloth, body


def test_create_proximity_wrap_backcompat(run_with_maya_standalone, setup_path):
    """Existing calls keep working exactly as before (custom steps, scripts)."""
    from maya import cmds
    import mgear.pymaya as pm
    from mgear.core import deformer

    # Positional call with the original parameters
    cloth, body = _proximity_scene()
    name = deformer.create_proximity_wrap(
        ["cloth"], ["body"], "cloth_pw", None, None, 2
    )
    assert name == "cloth_pw"
    assert cmds.nodeType(name) == "proximityWrap"
    assert cmds.isConnected(
        "bodyShape.worldMesh[0]", name + ".drivers[0].driverGeometry"
    )
    assert cmds.getAttr(name + ".smoothInfluences") == 2
    assert cmds.getAttr(name + ".wrapMode") == 1  # Maya default kept

    # Single pymaya nodes and default name
    cloth, body = _proximity_scene()
    name = deformer.create_proximity_wrap(pm.PyNode(cloth), pm.PyNode(body))
    assert name == "cloth_proximityWrap"
    assert cmds.getAttr(name + ".smoothInfluences") == 0


def test_create_proximity_wrap_wrap_mode(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    _proximity_scene()
    name = deformer.create_proximity_wrap("cloth", "body", wrap_mode="Snap")
    assert cmds.getAttr(name + ".wrapMode") == 2
    _proximity_scene()
    name = deformer.create_proximity_wrap("cloth", "body", wrap_mode=3)
    assert cmds.getAttr(name + ".wrapMode") == 3


def test_add_proximity_wrap_drivers(run_with_maya_standalone, setup_path):
    from maya import cmds
    from mgear.core import deformer

    cloth, body = _proximity_scene()
    cmds.polyCube(name="other")
    node = cmds.deformer(cloth, type="proximityWrap")[0]
    assert deformer.add_proximity_wrap_drivers(node, ["bodyShape", "otherShape"]) == [
        0,
        1,
    ]
    assert cmds.isConnected(
        "bodyShape.worldMesh[0]", node + ".drivers[0].driverGeometry"
    )
    assert cmds.isConnected(
        "otherShape.worldMesh[0]", node + ".drivers[1].driverGeometry"
    )
