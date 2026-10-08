"""mgear.rigbits.shrinkwrap_io export / import test"""

import json
import logging

import pytest


def _evaluation_order(geometry):
    from mgear.core import deformer

    return list(reversed(deformer.get_deformer_stack(geometry)))


def _points(mesh):
    from maya import cmds

    flat = cmds.xform(mesh + ".vtx[*]", query=True, worldSpace=True, translation=True)
    return [flat[i : i + 3] for i in range(0, len(flat), 3)]


def _shrinkwrap_scene():
    """Two spheres shrink wrapped on a cube, with a driven envelope."""
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    cloth = cmds.polySphere(name="cloth", radius=1.5)[0]
    belt = cmds.polySphere(name="belt", radius=1.4)[0]
    target = cmds.polyCube(name="body", width=1.5, height=1.5, depth=1.5)[0]
    target_shape = cmds.listRelatives(target, shapes=True, fullPath=True)[0]
    ctl = cmds.createNode("transform", name="ctl")
    cmds.addAttr(ctl, longName="blend", minValue=0, maxValue=1, keyable=True)
    cmds.setAttr(ctl + ".blend", 0.9)

    sw = cmds.deformer([cloth, belt], type="shrinkWrap", name="sw1")[0]
    cmds.connectAttr(target_shape + ".worldMesh[0]", sw + ".targetGeom")
    cmds.connectAttr(ctl + ".blend", sw + ".envelope")
    cmds.setAttr(sw + ".projection", 4)
    cmds.setAttr(sw + ".offset", 0.05)
    cmds.setAttr(sw + ".falloff", 0.3)
    cmds.setAttr(sw + ".shapePreservationEnable", 1)
    deformer.set_deformer_weights(sw, 0, {3: 0.5, 10: 0.25})
    return cloth, belt, target, sw


def _stack_scene():
    """Sphere deformed by skinA, sw1, clB (evaluation order)."""
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="cloth")[0]
    target = cmds.polyCube(name="body")[0]
    joint = cmds.joint(name="j1")
    cmds.select(clear=True)
    cmds.skinCluster(joint, sphere, name="skinA")
    cmds.cluster(sphere, name="clB")
    sw = cmds.deformer(sphere, type="shrinkWrap", name="sw1")[0]
    target_shape = cmds.listRelatives(target, shapes=True, fullPath=True)[0]
    cmds.connectAttr(target_shape + ".worldMesh[0]", sw + ".targetGeom")
    deformer.move_deformer("sw1", sphere, after="skinA")
    assert _evaluation_order(sphere) == ["skinA", "sw1", "clB"]
    return sphere


def test_round_trip(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.core import deformer
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, target, sw = _shrinkwrap_scene()
    before_points = _points(cloth)
    before_attrs = {
        a: cmds.getAttr("sw1." + a)
        for a in ("projection", "offset", "falloff", "shapePreservationEnable")
    }
    before_weights = deformer.get_deformer_weights("sw1", 0)

    data = shrinkwrap_io.export_shrinkwraps(["sw1"], str(tmp_path / "cloth"))
    path = str(tmp_path / "cloth.shw")
    with open(path) as f:
        assert json.load(f)["type"] == "shrinkwrap_config"
    config = data["shrinkwraps"][0]
    assert config["target"]["transform"] == "|body"
    assert {"source": "|ctl.blend", "destination": "envelope"} in config["connections"]
    assert {
        "source": "|body|bodyShape.worldMesh[0]",
        "destination": "targetGeom",
        "source_parent": "|body",
    } in config["connections"]
    assert len(config["geometry"]) == 2

    cmds.delete("sw1")
    assert shrinkwrap_io.import_shrinkwraps(path) == ["sw1"]
    assert cmds.nodeType("sw1") == "shrinkWrap"
    assert cmds.isConnected("|body|bodyShape.worldMesh[0]", "sw1.targetGeom")
    assert cmds.isConnected("ctl.blend", "sw1.envelope")
    for attr, value in before_attrs.items():
        assert cmds.getAttr("sw1." + attr) == pytest.approx(value)
    assert deformer.get_deformer_weights("sw1", 0) == {
        k: pytest.approx(v, abs=1e-5) for k, v in before_weights.items()
    }
    for got, want in zip(_points(cloth), before_points):
        assert got == pytest.approx(want, abs=1e-4)

    # The shrink wrap really deforms: the driven envelope changes the shape
    cmds.setAttr("ctl.blend", 0)
    moved = max(
        abs(a - b)
        for got, want in zip(_points(cloth), before_points)
        for a, b in zip(got, want)
    )
    assert moved > 1e-3
    assert belt


def test_missing_target_and_driver(
    run_with_maya_standalone, setup_path, tmp_path, caplog
):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, target, sw = _shrinkwrap_scene()
    path = str(tmp_path / "missing.shw")
    shrinkwrap_io.export_shrinkwraps(["sw1"], path)

    # Missing driver: warning, stored value kept
    cmds.delete("sw1", "ctl")
    with caplog.at_level(logging.WARNING, logger="mgear.rigbits.shrinkwrap_io"):
        assert shrinkwrap_io.import_shrinkwraps(path) == ["sw1"]
    assert "not found" in caplog.text
    assert cmds.getAttr("sw1.envelope") == pytest.approx(0.9)

    # Missing target: skipped
    cmds.delete("sw1", target)
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="mgear.rigbits.shrinkwrap_io"):
        assert shrinkwrap_io.import_shrinkwraps(path) == []
    assert "Target" in caplog.text
    assert not cmds.ls(type="shrinkWrap")


def test_export_without_target(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, target, sw = _shrinkwrap_scene()
    other = cmds.polySphere(name="loose")[0]
    cmds.deformer(other, type="shrinkWrap", name="sw_empty")
    data = shrinkwrap_io.export_shrinkwraps(
        ["sw1", "sw_empty"], str(tmp_path / "t.shw")
    )
    assert [c["shrinkwrap"]["name"] for c in data["shrinkwraps"]] == ["sw1"]


def test_replace_and_undo(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, target, sw = _shrinkwrap_scene()
    path = str(tmp_path / "replace.shw")
    shrinkwrap_io.export_shrinkwraps(["sw1"], path)

    # Replace keeps meshes and the name
    assert shrinkwrap_io.import_shrinkwraps(path) == ["sw1"]
    assert cmds.ls(type="shrinkWrap") == ["sw1"]
    for node in (cloth, belt, target):
        assert cmds.objExists(node)

    cmds.delete("sw1")
    cmds.undoInfo(state=True, infinity=True)
    shrinkwrap_io.import_shrinkwraps(path)
    cmds.undo()
    assert not cmds.ls(type="shrinkWrap")


def test_order_modes(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io

    sphere = _stack_scene()
    path = str(tmp_path / "order.shw")
    shrinkwrap_io.export_shrinkwraps(["sw1"], path)

    for order, expected in (
        (None, ["skinA", "sw1", "clB"]),
        ("front", ["sw1", "skinA", "clB"]),
        ("last", ["skinA", "clB", "sw1"]),
        ({"sw1": "front"}, ["sw1", "skinA", "clB"]),
    ):
        shrinkwrap_io.import_shrinkwraps(path, order=order)
        assert _evaluation_order(sphere) == expected, order

    with pytest.raises(ValueError):
        shrinkwrap_io.import_shrinkwraps(path, order="middle")
    with pytest.raises(ValueError):
        shrinkwrap_io.export_shrinkwraps(["sw1"], path, order="middle")
    assert cmds.objExists("sw1")


def test_foreign_file(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import lattice_io
    from mgear.rigbits import shrinkwrap_io

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere()[0]
    cmds.lattice(sphere, name="ffd1")
    path = str(tmp_path / "lattice.lat")
    lattice_io.export_lattices(["ffd1"], path)
    with pytest.raises(ValueError):
        shrinkwrap_io.load_file(path)


def test_find_shrinkwrap_nodes(run_with_maya_standalone, setup_path):
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, target, sw = _shrinkwrap_scene()
    assert shrinkwrap_io.find_shrinkwrap_nodes([target]) == ["sw1"]
    assert shrinkwrap_io.find_shrinkwrap_nodes([cloth + ".vtx[2]"]) == ["sw1"]
    assert shrinkwrap_io.find_shrinkwrap_nodes(["sw1", "missing"]) == ["sw1"]
    assert shrinkwrap_io.find_shrinkwrap_nodes(["ctl"]) == ["sw1"]


def test_ui(qt_app, clean_settings, tmp_path):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io
    from mgear.rigbits.shrinkwrap_io import ui
    from mgear.vendor.Qt import QtGui
    from mgear.vendor.Qt import QtWidgets

    sphere = _stack_scene()
    path = str(tmp_path / "ui.shw")
    shrinkwrap_io.export_shrinkwraps(["sw1"], path, order="front")

    dialog = ui.ShrinkWrapIOUI()
    try:
        assert dialog.export_order_combo.currentData() == "current"
        assert dialog.scene_list.count() == 1
        assert "target: body" in dialog.scene_list.item(0).text()

        cmds.select("body")
        dialog.select_from_scene()
        assert dialog.scene_list.item(0).isSelected()

        dialog.open_file(path)
        tree = dialog.file_tree
        assert tree.topLevelItemCount() == 1
        assert tree.topLevelItem(0).text(2) == "body"
        combo = tree.itemWidget(tree.topLevelItem(0), 1)
        assert combo.currentData() == "front"
        combo.setCurrentIndex(combo.findData("last"))
        dialog.import_checked()
        assert _evaluation_order(sphere) == ["skinA", "clB", "sw1"]
        assert "Imported 1 shrink wrap(s)" in dialog.log_output.toPlainText()
    finally:
        # The Maya mixin can't show windows in standalone: send the event
        QtWidgets.QApplication.sendEvent(dialog, QtGui.QCloseEvent())
    assert dialog.log_handler not in dialog.logger.handlers


def test_custom_step_template(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io
    from mgear.shifter import custom_step_templates

    names = dict(custom_step_templates.get_template_names())
    assert names["import_shrinkwrap_config"] == "Import Shrink Wrap Configuration"
    code = custom_step_templates.get_template_content(
        "import_shrinkwrap_config", "sw_step"
    )
    namespace = {}
    exec(compile(code, "sw_step.py", "exec"), namespace)
    step = namespace["CustomShifterStep"]({})
    step.setup()
    assert step.name == "sw_step"
    assert step.order is None

    cloth, belt, target, sw = _shrinkwrap_scene()
    path = str(tmp_path / "step.shw")
    shrinkwrap_io.export_shrinkwraps(["sw1"], path)
    cmds.delete("sw1")
    step.shrinkwrap_path = path
    step.run()
    assert cmds.nodeType("sw1") == "shrinkWrap"
    assert cmds.isConnected("|body|bodyShape.worldMesh[0]", "sw1.targetGeom")


def test_renamed_target_shape(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, target, sw = _shrinkwrap_scene()
    path = str(tmp_path / "renamed.shw")
    shrinkwrap_io.export_shrinkwraps(["sw1"], path)
    cmds.delete("sw1")
    # A rebuilt rig often has a different shape name under the same mesh
    cmds.rename("|body|bodyShape", "bodyMeshShape")
    assert shrinkwrap_io.import_shrinkwraps(path) == ["sw1"]
    assert cmds.isConnected("|body|bodyMeshShape.worldMesh[0]", "sw1.targetGeom")
