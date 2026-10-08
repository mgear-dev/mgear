"""mgear.rigbits.proximitywrap_io export / import test"""

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


def _max_delta(points_a, points_b):
    return max(abs(a - b) for pa, pb in zip(points_a, points_b) for a, b in zip(pa, pb))


def _proximity_scene():
    """Two meshes wrapped on two drivers, with a driven driver strength."""
    from maya import cmds
    from mgear.core import attribute
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    cloth = cmds.polySphere(name="cloth", radius=1.2)[0]
    belt = cmds.polyTorus(name="belt", radius=1.3, sectionRadius=0.1)[0]
    cmds.polyCube(name="bodyA", width=2, height=2, depth=2)
    cmds.polyCube(name="bodyB", width=1, height=1, depth=1)
    ctl = cmds.createNode("transform", name="ctl")
    cmds.addAttr(ctl, longName="strength", minValue=0, maxValue=1, keyable=True)
    cmds.setAttr(ctl + ".strength", 0.6)

    node = cmds.deformer([cloth, belt], type="proximityWrap", name="pw1")[0]
    deformer.add_proximity_wrap_drivers(node, ["bodyAShape", "bodyBShape"])
    cmds.setAttr(node + ".falloffScale", 1.5)
    cmds.setAttr(node + ".smoothInfluences", 2)
    attribute.set_ramp(node, "falloffRamp", [[0, 1, 1], [0.5, 0.4, 2], [1, 0, 1]])
    cmds.setAttr(node + ".drivers[0].driverStrength", 0.7)
    cmds.setAttr(node + ".drivers[0].driverFalloffEnd", 2.0)
    cmds.setAttr(node + ".drivers[0].driverWrapMode", 0)
    cmds.setAttr(node + ".drivers[0].driverOverrideFalloffRamp", True)
    attribute.set_ramp(
        node, "drivers[0].driverFalloffRamp", [[0, 1, 1], [0.3, 0.2, 1], [1, 0, 1]]
    )
    cmds.connectAttr(ctl + ".strength", node + ".drivers[1].driverStrength")
    deformer.set_deformer_weights(node, 0, {3: 0.5, 10: 0.25})

    # Move the drivers so the wrap deforms the meshes
    cmds.setAttr("bodyA.ty", 0.4)
    cmds.setAttr("bodyB.rz", 25)
    return cloth, belt, node


def _stack_scene():
    """Sphere deformed by skinA, pw1, clB (evaluation order)."""
    from maya import cmds
    from mgear.core import deformer

    cmds.file(new=True, force=True)
    sphere = cmds.polySphere(name="cloth")[0]
    cmds.polyCube(name="body")
    joint = cmds.joint(name="j1")
    cmds.select(clear=True)
    cmds.skinCluster(joint, sphere, name="skinA")
    cmds.cluster(sphere, name="clB")
    node = cmds.deformer(sphere, type="proximityWrap", name="pw1")[0]
    deformer.add_proximity_wrap_drivers(node, ["bodyShape"])
    deformer.move_deformer("pw1", sphere, after="skinA")
    assert _evaluation_order(sphere) == ["skinA", "pw1", "clB"]
    return sphere


def test_round_trip(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.core import attribute
    from mgear.core import deformer
    from mgear.rigbits import proximitywrap_io

    cloth, belt, node = _proximity_scene()
    before_points = _points(cloth)
    before_belt = _points(belt)
    before_node_ramp = attribute.get_ramp(node, "falloffRamp")
    before_driver_ramp = attribute.get_ramp(node, "drivers[0].driverFalloffRamp")
    before_weights = deformer.get_deformer_weights(node, 0)

    data = proximitywrap_io.export_proximitywraps(["pw1"], str(tmp_path / "cloth"))
    path = str(tmp_path / "cloth.pxw")
    with open(path) as f:
        assert json.load(f)["type"] == "proximitywrap_config"
    config = data["proximitywraps"][0]
    assert [d["transform"] for d in config["drivers"]] == ["|bodyA", "|bodyB"]
    assert {
        "source": "|ctl.strength",
        "destination": "drivers[1].driverStrength",
    } in config["connections"]
    destinations = [c["destination"] for c in config["connections"]]
    assert not any(
        "driverGeometry" in d or "driverBindGeometry" in d for d in destinations
    )

    cmds.delete("pw1")
    assert proximitywrap_io.import_proximitywraps(path) == ["pw1"]
    assert cmds.nodeType("pw1") == "proximityWrap"
    assert cmds.isConnected("bodyAShape.worldMesh[0]", "pw1.drivers[0].driverGeometry")
    assert cmds.isConnected("bodyBShape.worldMesh[0]", "pw1.drivers[1].driverGeometry")
    assert cmds.isConnected("ctl.strength", "pw1.drivers[1].driverStrength")
    assert cmds.getAttr("pw1.falloffScale") == pytest.approx(1.5)
    assert cmds.getAttr("pw1.smoothInfluences") == 2
    assert cmds.getAttr("pw1.drivers[0].driverStrength") == pytest.approx(0.7)
    assert cmds.getAttr("pw1.drivers[0].driverFalloffEnd") == pytest.approx(2.0)
    assert cmds.getAttr("pw1.drivers[0].driverWrapMode") == 0
    assert cmds.getAttr("pw1.drivers[0].driverOverrideFalloffRamp")
    for got, want in zip(attribute.get_ramp("pw1", "falloffRamp"), before_node_ramp):
        assert got == pytest.approx(want, abs=1e-5)
    for got, want in zip(
        attribute.get_ramp("pw1", "drivers[0].driverFalloffRamp"), before_driver_ramp
    ):
        assert got == pytest.approx(want, abs=1e-5)
    assert deformer.get_deformer_weights("pw1", 0) == {
        k: pytest.approx(v, abs=1e-5) for k, v in before_weights.items()
    }

    # Same deformation, and the wrap really deforms
    assert _max_delta(_points(cloth), before_points) < 1e-4
    assert _max_delta(_points(belt), before_belt) < 1e-4
    cmds.setAttr("pw1.envelope", 0)
    assert _max_delta(_points(cloth), before_points) > 1e-3


def test_missing_drivers(run_with_maya_standalone, setup_path, tmp_path, caplog):
    from maya import cmds
    from mgear.rigbits import proximitywrap_io

    cloth, belt, node = _proximity_scene()
    path = str(tmp_path / "drivers.pxw")
    proximitywrap_io.export_proximitywraps(["pw1"], path)

    # One driver missing: built with the other, its connection dropped
    cmds.delete("pw1", "bodyA")
    with caplog.at_level(logging.WARNING, logger="mgear.rigbits.proximitywrap_io"):
        assert proximitywrap_io.import_proximitywraps(path) == ["pw1"]
    assert "bodyA" in caplog.text
    assert cmds.getAttr("pw1.drivers", multiIndices=True) == [0]
    assert cmds.isConnected("bodyBShape.worldMesh[0]", "pw1.drivers[0].driverGeometry")
    assert cmds.isConnected("ctl.strength", "pw1.drivers[0].driverStrength")

    # No driver: skipped, nothing left behind
    cmds.delete("pw1", "bodyB")
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="mgear.rigbits.proximitywrap_io"):
        assert proximitywrap_io.import_proximitywraps(path) == []
    assert "No driver" in caplog.text
    assert not cmds.ls(type="proximityWrap")


def test_replace_undo_and_files(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import proximitywrap_io
    from mgear.rigbits import shrinkwrap_io

    cloth, belt, node = _proximity_scene()
    path = str(tmp_path / "replace.pxw")
    proximitywrap_io.export_proximitywraps(["pw1"], path)

    assert proximitywrap_io.import_proximitywraps(path) == ["pw1"]
    assert cmds.ls(type="proximityWrap") == ["pw1"]
    for mesh in (cloth, belt, "bodyA", "bodyB"):
        assert cmds.objExists(mesh)

    cmds.delete("pw1")
    cmds.undoInfo(state=True, infinity=True)
    proximitywrap_io.import_proximitywraps(path)
    cmds.undo()
    assert not cmds.ls(type="proximityWrap")

    with pytest.raises(ValueError):
        shrinkwrap_io.load_file(path)
    with pytest.raises(ValueError):
        proximitywrap_io.import_proximitywraps(path, order="middle")


def test_order_modes(run_with_maya_standalone, setup_path, tmp_path):
    from mgear.rigbits import proximitywrap_io

    sphere = _stack_scene()
    path = str(tmp_path / "order.pxw")
    proximitywrap_io.export_proximitywraps(["pw1"], path)
    for order, expected in (
        (None, ["skinA", "pw1", "clB"]),
        ("front", ["pw1", "skinA", "clB"]),
        ("last", ["skinA", "clB", "pw1"]),
    ):
        proximitywrap_io.import_proximitywraps(path, order=order)
        assert _evaluation_order(sphere) == expected, order


def test_find_proximitywrap_nodes(run_with_maya_standalone, setup_path):
    from mgear.rigbits import proximitywrap_io

    cloth, belt, node = _proximity_scene()
    assert proximitywrap_io.find_proximitywrap_nodes(["bodyB"]) == ["pw1"]
    assert proximitywrap_io.find_proximitywrap_nodes([cloth + ".vtx[1]"]) == ["pw1"]
    assert proximitywrap_io.find_proximitywrap_nodes(["ctl", "missing"]) == ["pw1"]


def test_ui(qt_app, clean_settings, tmp_path):
    from maya import cmds
    from mgear.rigbits import proximitywrap_io
    from mgear.rigbits.proximitywrap_io import ui
    from mgear.vendor.Qt import QtGui
    from mgear.vendor.Qt import QtWidgets

    sphere = _stack_scene()
    path = str(tmp_path / "ui.pxw")
    proximitywrap_io.export_proximitywraps(["pw1"], path, order="front")

    dialog = ui.ProximityWrapIOUI()
    try:
        assert dialog.export_order_combo.currentData() == "current"
        assert dialog.scene_list.item(0).text() == "pw1   (1 drivers, 1 geo)"
        cmds.select("body")
        dialog.select_from_scene()
        assert dialog.scene_list.item(0).isSelected()

        dialog.open_file(path)
        item = dialog.file_tree.topLevelItem(0)
        assert item.text(2) == "body"
        combo = dialog.file_tree.itemWidget(item, 1)
        assert combo.currentData() == "front"
        combo.setCurrentIndex(combo.findData("last"))
        dialog.import_checked()
        assert _evaluation_order(sphere) == ["skinA", "clB", "pw1"]
        assert "Imported 1 proximity wrap(s)" in dialog.log_output.toPlainText()
    finally:
        # The Maya mixin can't show windows in standalone: send the event
        QtWidgets.QApplication.sendEvent(dialog, QtGui.QCloseEvent())
    assert dialog.log_handler not in dialog.logger.handlers


def test_custom_step_template(run_with_maya_standalone, setup_path, tmp_path):
    from maya import cmds
    from mgear.rigbits import proximitywrap_io
    from mgear.shifter import custom_step_templates

    names = dict(custom_step_templates.get_template_names())
    assert names["import_proximitywrap_config"] == "Import Proximity Wrap Configuration"
    code = custom_step_templates.get_template_content(
        "import_proximitywrap_config", "pw_step"
    )
    namespace = {}
    exec(compile(code, "pw_step.py", "exec"), namespace)
    step = namespace["CustomShifterStep"]({})
    step.setup()
    assert step.name == "pw_step"
    assert step.order is None

    cloth, belt, node = _proximity_scene()
    path = str(tmp_path / "step.pxw")
    proximitywrap_io.export_proximitywraps(["pw1"], path)
    cmds.delete("pw1")
    step.proximitywrap_path = path
    step.run()
    assert cmds.nodeType("pw1") == "proximityWrap"
    assert cmds.getAttr("pw1.drivers", multiIndices=True) == [0, 1]
