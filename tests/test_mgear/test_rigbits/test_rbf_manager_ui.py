"""RBF Manager 2 window tests, driven like a user would."""

import pytest

DRIVER_ATTRS = (
    "translateX",
    "translateY",
    "translateZ",
    "rotateX",
    "rotateY",
    "rotateZ",
)


@pytest.fixture
def rbf_window(qt_app, rig_plugins, monkeypatch):
    """An RBF Manager window in a new scene with a driver and 2 driven nodes.

    ``drv`` is the driver, ``drivenA`` and ``drivenB`` the driven nodes.
    Warning popups fail the test instead of blocking it. The table cells are
    plain line edits with the plug value, as Maya's attrControlGrp needs the
    Maya UI.

    Returns:
        RBFManagerUI: The window, closed after the test.
    """
    from maya import cmds

    from mgear.vendor.Qt import QtWidgets

    from mgear.rigbits.rbf_manager2 import rbf_manager_ui
    from mgear.rigbits.rbf_manager2 import widget

    def warning(parent, text):
        raise AssertionError("Warning popup: {}".format(text))

    def control_attr_widget(nodeAttr, label=""):
        edit = QtWidgets.QLineEdit(str(cmds.getAttr(nodeAttr)))
        return edit, "fake_attr_control"

    monkeypatch.setattr(widget, "genericWarning", warning)
    monkeypatch.setattr(widget, "getControlAttrWidget", control_attr_widget)
    cmds.file(new=True, force=True)
    for name in ("drv", "drivenA", "drivenB"):
        cmds.createNode("transform", name=name)
    window = rbf_manager_ui.RBFManagerUI(newSceneCallBack=False)
    window.initializePoseControlWidgets()
    yield window
    window.close()
    window.deleteLater()


def _select_items(list_widget, texts):
    """Select the list items with the given texts, clear the others."""
    list_widget.clearSelection()
    for index in range(list_widget.count()):
        item = list_widget.item(index)
        if item.text() in texts:
            item.setSelected(True)


def _add_driven(window, driven, driven_attr="translateY"):
    """Add an RBF node driving one attribute of ``driven``, as the UI does.

    The first call creates the setup with the translate and rotate
    attributes of ``drv`` as driver. Later calls add to the setup, keeping
    the driver attribute selection the window shows.
    """
    if not window.currentRBFSetupNodes:
        window.driverLineEdit.setText("drv")
        window.controlLineEdit.setText("drv")
        window.updateAttributeDisplay(window.driverAttributesWidget, "drv")
        _select_items(
            window.driverAttributesWidget,
            ["drv.{}".format(attr) for attr in DRIVER_ATTRS],
        )
    window.drivenLineEdit.setText(driven)
    window.updateAttributeDisplay(window.drivenAttributesWidget, driven)
    _select_items(window.drivenAttributesWidget, ["{}.{}".format(driven, driven_attr)])
    window.addRBFToSetup()


def _table_values(table):
    """The cell texts of a table widget, as rows of floats."""
    return [
        [
            round(float(table.item(row, column).text()), 4)
            for column in range(table.columnCount())
        ]
        for row in range(table.rowCount())
    ]


def _pose_values(cmds, rbf_node):
    """The driven pose values stored on an RBF node, as rows of floats."""
    rows = []
    for pose in cmds.getAttr("{}.poses".format(rbf_node), multiIndices=True):
        plug = "{}.poses[{}].poseValue".format(rbf_node, pose)
        indices = cmds.getAttr(plug, multiIndices=True) or []
        rows.append(
            [round(cmds.getAttr("{}[{}]".format(plug, index)), 4) for index in indices]
        )
    return rows


def _tab_nodes(window):
    """The tab widgets of the window and the RBF node each one shows."""
    tabs = window.rbfTabWidget
    return [
        (tabs.widget(index), str(tabs.widget(index).rbfNode))
        for index in range(tabs.count())
    ]


def test_update_pose_keeps_each_tab_values(rbf_window):
    """Update Pose shows each driven node's own values in its tab (#648)."""
    from maya import cmds

    window = rbf_window
    _add_driven(window, "drivenA")
    _add_driven(window, "drivenB")
    assert window.rbfTabWidget.count() == 2

    # a second pose, with a different value on each driven node
    cmds.setAttr("drv.translateX", 5.0)
    cmds.setAttr("drivenA.translateY", 1.0)
    cmds.setAttr("drivenB.translateY", 2.0)
    window.addPose()

    # Update Pose on the second pose, with the drivenA tab current
    window.rbfTabWidget.setCurrentIndex(0)
    window.driverPoseTableWidget.setCurrentCell(1, 0)
    window.rbfTabWidget.currentWidget().tableWidget.setCurrentCell(1, 0)
    cmds.setAttr("drv.translateX", 5.0)
    cmds.setAttr("drivenA.translateY", 3.0)
    cmds.setAttr("drivenB.translateY", 4.0)
    window.editPose()

    values = {}
    for tab, rbf_node in _tab_nodes(window):
        values[rbf_node] = _table_values(tab.tableWidget)
        assert values[rbf_node] == _pose_values(cmds, rbf_node)
    # the driven nodes got different values, so the tabs differ
    first, second = values.values()
    assert first[1] != second[1]


def _driver_attrs(cmds, rbf_node):
    """The driver attributes connected to an RBF node, in input order."""
    from mgear.rigbits.rbf_manager2 import rbf_manager_ui

    return rbf_manager_ui.sortRBF(rbf_node).getDriverNodeAttributes()


def test_driver_attr_order_kept(rbf_window):
    """The driver attributes keep their order once the setup exists (#643)."""
    from maya import cmds

    window = rbf_window
    _add_driven(window, "drivenA")
    listed = [
        window.driverAttributesWidget.item(index).text().split(".")[-1]
        for index in range(window.driverAttributesWidget.count())
    ]
    assert listed == list(DRIVER_ATTRS)

    # a second driven node uses the driver attributes of the setup
    cmds.setAttr("drv.translateX", 5.0)
    cmds.setAttr("drv.rotateZ", 30.0)
    window.addPose()
    _add_driven(window, "drivenB")
    nodes = [rbf_node for _, rbf_node in _tab_nodes(window)]
    assert len(nodes) == 2
    for rbf_node in nodes:
        assert list(_driver_attrs(cmds, rbf_node)) == list(DRIVER_ATTRS)

    # both nodes store the same pose inputs, in the driver attribute order
    inputs = []
    for rbf_node in nodes:
        plug = "{}.poses[1].poseInput".format(rbf_node)
        indices = cmds.getAttr(plug, multiIndices=True)
        inputs.append(
            [round(cmds.getAttr("{}[{}]".format(plug, i)), 4) for i in indices]
        )
    assert inputs[0] == inputs[1] == [5.0, 0.0, 0.0, 0.0, 0.0, 30.0]
