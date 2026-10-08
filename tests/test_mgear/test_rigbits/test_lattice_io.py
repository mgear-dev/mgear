"""mgear.rigbits.lattice_io export / import test"""

import json
import logging

import pytest


def _evaluation_order(geometry):
    from mgear.core import deformer

    return list(reversed(deformer.get_deformer_stack(geometry)))


def _sphere_with_stack():
    """Sphere deformed by skinA, ffd1, clB, clC (evaluation order)."""
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="body")[0]
    joint = cmds.joint(name="j1")
    cmds.select(clear=True)
    cmds.skinCluster(joint, sphere, name="skinA")
    cmds.cluster(sphere, name="clB")
    cmds.cluster(sphere, name="clC")
    cmds.lattice(sphere, frontOfChain=False, name="ffd1")
    deformer.move_deformer("ffd1", sphere, after="skinA")
    assert _evaluation_order(sphere) == ["skinA", "ffd1", "clB", "clC"]
    return sphere


def _delete_ffd():
    from mgear.core import deformer

    deformer.delete_lattice("ffd1")


def test_round_trip(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.core import deformer
    from mgear.rigbits import lattice_io

    cmds.file(new=True, force=True)
    rig = cmds.createNode("transform", name="rig_grp")
    cmds.setAttr(rig + ".ty", 2)
    sphere = cmds.polySphere(name="body")[0]
    ffd, lattice, base = cmds.lattice(
        sphere, divisions=(2, 3, 4), objectCentered=True, name="ffd1"
    )
    lattice = cmds.parent(lattice, rig)[0]
    base = cmds.parent(base, rig)[0]
    cmds.xform(lattice + ".pt[1][2][3]", objectSpace=True, translation=(1, 2, 3))
    cmds.setAttr(lattice + ".rz", 15)
    cmds.setAttr(base + ".visibility", False)
    cmds.setAttr(ffd + ".outsideLattice", 1)
    cmds.setAttr(ffd + ".localInfluenceS", 3)
    cmds.setAttr(ffd + ".envelope", 0.8)
    deformer.set_deformer_weights(ffd, 0, {3: 0.5, 10: 0.25})

    def snapshot():
        lat_tfm, _, base_tfm, _ = deformer.get_lattice_nodes("ffd1")
        return {
            "points": deformer.get_lattice_points(lat_tfm),
            "weights": deformer.get_deformer_weights("ffd1", 0),
            "lat_matrix": cmds.xform(lat_tfm, query=True, ws=True, matrix=True),
            "base_matrix": cmds.xform(base_tfm, query=True, ws=True, matrix=True),
            "lat_parent": cmds.listRelatives(lat_tfm, parent=True),
            "base_parent": cmds.listRelatives(base_tfm, parent=True),
            "base_vis": cmds.getAttr(base_tfm + ".visibility"),
            "attrs": [
                cmds.getAttr("ffd1." + a)
                for a in ("outsideLattice", "localInfluenceS", "envelope")
            ],
            "names": (lat_tfm, base_tfm),
        }

    before = snapshot()
    data = lattice_io.export_lattices(["ffd1"], str(tmp_path / "face"))
    path = tmp_path / "face.lat"
    assert path.exists()
    with open(str(path)) as f:
        assert json.load(f)["type"] == "lattice_config"
    assert data["lattices"][0]["order"] == "current"

    deformer.delete_lattice("ffd1")
    assert lattice_io.import_lattices(str(path)) == ["ffd1"]
    after = snapshot()

    assert after["names"] == before["names"]
    assert after["lat_parent"] == before["lat_parent"] == ["rig_grp"]
    assert after["base_parent"] == before["base_parent"]
    assert after["base_vis"] is False
    assert after["attrs"] == pytest.approx(before["attrs"])
    assert after["lat_matrix"] == pytest.approx(before["lat_matrix"], abs=1e-5)
    assert after["base_matrix"] == pytest.approx(before["base_matrix"], abs=1e-5)
    for got, want in zip(after["points"], before["points"]):
        assert got == pytest.approx(want, abs=1e-5)
    assert after["weights"] == {
        k: pytest.approx(v, abs=1e-5) for k, v in before["weights"].items()
    }


def test_single_undo_and_names(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io

    cmds.file(new=True, force=True)
    ffds = []
    for i in range(3):
        sphere = cmds.polySphere(name="ball{}".format(i))[0]
        ffds.append(cmds.lattice(sphere, name="lat{}_ffd".format(i))[0])
    path = str(tmp_path / "balls.lat")
    lattice_io.export_lattices(ffds, path)
    cmds.delete(cmds.ls(type="ffd"))

    cmds.undoInfo(state=True, infinity=True)
    created = lattice_io.import_lattices(path, names=["lat0_ffd", "lat2_ffd"])
    assert created == ["lat0_ffd", "lat2_ffd"]
    cmds.undo()
    assert not cmds.ls(type="ffd")


def test_two_shapes_under_one_transform(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.core import deformer
    from mgear.rigbits import lattice_io

    cmds.file(new=True, force=True)
    geo = cmds.polyCube(name="geo")[0]
    other = cmds.polyCube(name="other")[0]
    shape_b = cmds.listRelatives(other, shapes=True)[0]
    cmds.parent(shape_b, geo, shape=True, relative=True)
    cmds.delete(other)
    shapes = cmds.listRelatives(geo, shapes=True, fullPath=True)
    assert len(shapes) == 2

    ffd = cmds.lattice(shapes, name="ffd1")[0]
    deformer.set_deformer_weights(ffd, 0, {1: 0.1})
    deformer.set_deformer_weights(ffd, 1, {2: 0.2})
    expected = dict(
        (shape, deformer.get_deformer_weights(ffd, index))
        for index, shape in deformer.get_deformer_geometry(ffd)
    )
    path = str(tmp_path / "shapes.lat")
    lattice_io.export_lattices([ffd], path)
    deformer.delete_lattice(ffd)

    lattice_io.import_lattices(path)
    result = dict(
        (shape, deformer.get_deformer_weights("ffd1", index))
        for index, shape in deformer.get_deformer_geometry("ffd1")
    )
    assert set(result) == set(expected)
    for shape, weights in expected.items():
        assert result[shape] == {
            k: pytest.approx(v, abs=1e-5) for k, v in weights.items()
        }


def test_replace_removes_orphans(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="body")[0]
    ffd, lattice, base = cmds.lattice(sphere, name="ffd1")
    path = str(tmp_path / "orphan.lat")
    lattice_io.export_lattices([ffd], path)

    # Orphan lattice and base left behind by a broken setup
    cmds.delete(ffd)
    for name, shape_type in ((lattice, "lattice"), (base, "baseLattice")):
        if not cmds.objExists(name):
            orphan = cmds.createNode("transform", name=name)
            cmds.createNode(shape_type, parent=orphan)
    lattice_io.import_lattices(path)
    assert cmds.objExists("ffd1Base")
    assert cmds.objExists("ffd1Lattice")
    assert not cmds.ls("ffd1Base1", "ffd1Lattice1")

    # Replace an existing build
    lattice_io.import_lattices(path)
    assert cmds.ls(type="ffd") == ["ffd1"]
    assert not cmds.ls("ffd1Base1", "ffd1Lattice1")


def test_missing_geometry(run_with_maya_standalone, setup_path, tmp_path, caplog):
    from maya import cmds
    from mgear.rigbits import lattice_io

    cmds.file(new=True, force=True)
    a = cmds.polySphere(name="a_geo")[0]
    b = cmds.polySphere(name="b_geo")[0]
    cmds.lattice(a, name="a_ffd")
    cmds.lattice(b, name="b_ffd")
    path = str(tmp_path / "missing.lat")
    lattice_io.export_lattices(["a_ffd", "b_ffd"], path)

    cmds.delete(cmds.ls(type="ffd"))
    cmds.delete(a)
    with caplog.at_level(logging.WARNING, logger="mgear.rigbits.lattice_io"):
        assert lattice_io.import_lattices(path) == ["b_ffd"]
    assert "not found" in caplog.text


def test_order_modes(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.rigbits import lattice_io

    sphere = _sphere_with_stack()
    path = str(tmp_path / "order.lat")
    data = lattice_io.export_lattices(["ffd1"], path)
    assert data["lattices"][0]["geometry"][0]["deformer_stack"] == [
        "clC",
        "clB",
        "ffd1",
        "skinA",
    ]

    for order, expected in (
        (None, ["skinA", "ffd1", "clB", "clC"]),
        ("current", ["skinA", "ffd1", "clB", "clC"]),
        ("front", ["ffd1", "skinA", "clB", "clC"]),
        ("last", ["skinA", "clB", "clC", "ffd1"]),
        ({"ffd1": "front"}, ["ffd1", "skinA", "clB", "clC"]),
        ({"other": "front"}, ["skinA", "ffd1", "clB", "clC"]),
    ):
        lattice_io.import_lattices(path, order=order)
        assert _evaluation_order(sphere) == expected, order

    # Stored mode used by default
    lattice_io.export_lattices(["ffd1"], path, order="last")
    with open(path) as f:
        assert json.load(f)["lattices"][0]["order"] == "last"
    lattice_io.import_lattices(path, order="front")
    lattice_io.import_lattices(path)
    assert _evaluation_order(sphere) == ["skinA", "clB", "clC", "ffd1"]


def test_order_current_fallbacks(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.core import deformer
    from mgear.rigbits import lattice_io

    # ffd originally first, a skinCluster added later
    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="body")[0]
    cmds.lattice(sphere, name="ffd1")
    path = str(tmp_path / "first.lat")
    lattice_io.export_lattices(["ffd1"], path)
    deformer.delete_lattice("ffd1")
    joint = cmds.joint(name="j1")
    cmds.skinCluster(joint, sphere, name="skinA")
    lattice_io.import_lattices(path)
    assert _evaluation_order(sphere) == ["ffd1", "skinA"]

    # Lower deformers gone: falls back to last
    sphere = _sphere_with_stack()
    path = str(tmp_path / "gone.lat")
    lattice_io.export_lattices(["ffd1"], path)
    deformer.delete_lattice("ffd1")
    cmds.delete("skinA")
    lattice_io.import_lattices(path)
    assert _evaluation_order(sphere) == ["clB", "clC", "ffd1"]


def test_legacy_json(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io

    sphere = _sphere_with_stack()
    data = lattice_io.export_lattices(["ffd1"], str(tmp_path / "tmp.lat"))
    # Strip the keys the original snippet didn't write
    for config in data["lattices"]:
        config.pop("order")
        config["lattice"].pop("visibility")
        config["base"].pop("visibility")
        for geo in config["geometry"]:
            geo.pop("deformer_stack")
    path = str(tmp_path / "legacy.json")
    with open(path, "w") as f:
        json.dump(data, f)

    # Current without a stored stack falls back to last
    assert lattice_io.import_lattices(path) == ["ffd1"]
    assert _evaluation_order(sphere) == ["skinA", "clB", "clC", "ffd1"]
    assert cmds.objExists("ffd1Lattice")


def test_invalid_files_and_modes(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io

    path = str(tmp_path / "foreign.json")
    with open(path, "w") as f:
        json.dump({"type": "other"}, f)
    with pytest.raises(ValueError):
        lattice_io.load_file(path)

    sphere = _sphere_with_stack()
    path = str(tmp_path / "modes.lat")
    with pytest.raises(ValueError):
        lattice_io.export_lattices(["ffd1"], path, order="middle")
    lattice_io.export_lattices(["ffd1"], path)

    with pytest.raises(ValueError):
        lattice_io.import_lattices(path, order="middle")
    with open(path) as f:
        data = json.load(f)
    data["lattices"][0]["order"] = "middle"
    with open(path, "w") as f:
        json.dump(data, f)
    _delete_ffd()
    with pytest.raises(ValueError):
        lattice_io.import_lattices(path)
    # Nothing was built
    assert not cmds.ls(type="ffd")
    assert sphere


def test_ui_order_controls(qt_app, clean_settings, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io
    from mgear.rigbits.lattice_io import ui
    from mgear.vendor.Qt import QtGui
    from mgear.vendor.Qt import QtWidgets

    sphere = _sphere_with_stack()
    other = cmds.polySphere(name="other")[0]
    cmds.cluster(other, name="clO")
    cmds.lattice(other, frontOfChain=False, name="ffd2")
    path = str(tmp_path / "ui.lat")
    lattice_io.export_lattices(["ffd1"], path, order="front")
    data = lattice_io.load_file(path)
    data["lattices"] += lattice_io.export_lattices(["ffd2"], str(tmp_path / "tmp.lat"))[
        "lattices"
    ]
    with open(path, "w") as f:
        json.dump(data, f)

    dialog = ui.LatticeIOUI()
    try:
        assert dialog.export_order_combo.currentData() == "current"
        assert dialog.scene_list.count() == 2
        dialog.export_order_combo.setCurrentIndex(2)

        dialog.open_file(path)
        tree = dialog.file_tree
        assert tree.topLevelItemCount() == 2
        first = tree.itemWidget(tree.topLevelItem(0), 1)
        second = tree.itemWidget(tree.topLevelItem(1), 1)
        assert first.currentData() == "front"
        assert second.currentData() == "current"

        # Override the first row to Last
        first.setCurrentIndex(first.findData("last"))
        dialog.import_checked()
        assert _evaluation_order(sphere) == ["skinA", "clB", "clC", "ffd1"]
        assert _evaluation_order(other) == ["clO", "ffd2"]
        assert "Imported 2 lattice(s)" in dialog.log_output.toPlainText()
    finally:
        # The Maya mixin can't show windows in standalone: send the event
        QtWidgets.QApplication.sendEvent(dialog, QtGui.QCloseEvent())
    assert dialog.log_handler not in dialog.logger.handlers

    # Reopened: the export order is back to Current
    dialog = ui.LatticeIOUI()
    try:
        assert dialog.export_order_combo.currentData() == "current"
    finally:
        dialog.dockCloseEventTriggered()
    assert dialog.log_handler not in dialog.logger.handlers


def test_custom_step_template(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io
    from mgear.shifter import custom_step_templates

    names = dict(custom_step_templates.get_template_names())
    assert names["import_lattice_config"] == "Import Lattice Configuration"

    code = custom_step_templates.get_template_content(
        "import_lattice_config", "lattice_step"
    )
    namespace = {}
    exec(compile(code, "lattice_step.py", "exec"), namespace)
    step = namespace["CustomShifterStep"]({})
    step.setup()
    assert step.name == "lattice_step"
    assert step.order is None

    sphere = _sphere_with_stack()
    path = str(tmp_path / "step.lat")
    lattice_io.export_lattices(["ffd1"], path, order="last")
    _delete_ffd()

    step.lattice_path = path
    step.run()
    assert cmds.objExists("ffd1")
    assert _evaluation_order(sphere) == ["skinA", "clB", "clC", "ffd1"]

    step.order = "front"
    step.run()
    assert _evaluation_order(sphere) == ["ffd1", "skinA", "clB", "clC"]
