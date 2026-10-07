"""mgear.core widgets, RecentFilesMenu and SettingsMixin test"""

import pytest

_KEY_PREFIX = "pytest_tool_widgets_"


def test_color_swatch(qt_app):
    from mgear.core import widgets

    swatch = widgets.ColorSwatchButton((1.0, 0.0, 0.0))
    emitted = []
    swatch.colorChanged.connect(emitted.append)

    swatch.set_color((0, 1, 0))
    assert swatch.color() == (0.0, 1.0, 0.0)
    assert emitted == [(0.0, 1.0, 0.0)]

    # Same color: no signal.
    swatch.set_color((0.0, 1.0, 0.0))
    assert len(emitted) == 1

    # Settings protocol: list out, list or string in, bad values ignored.
    assert swatch.settings_value() == [0.0, 1.0, 0.0]
    swatch.set_settings_value("0.2,0.4,0.6")
    assert swatch.color() == pytest.approx((0.2, 0.4, 0.6))
    swatch.set_settings_value("bad")
    assert swatch.color() == pytest.approx((0.2, 0.4, 0.6))
    assert swatch.settings_signal() is not None


def test_node_list_widget(qt_app):
    from maya import cmds
    from mgear.core import widgets

    cmds.file(new=True, force=True)
    rig = cmds.createNode("transform", name="rig")
    geo = cmds.createNode("transform", name="geo", parent=rig)
    cmds.createNode("transform", name="body", parent=geo)
    other = cmds.createNode("transform", name="other")
    cmds.createNode("transform", name="body", parent=other)

    node_list = widgets.NodeListWidget()
    changed = []
    node_list.nodesChanged.connect(lambda: changed.append(1))

    cmds.select("|rig|geo|body")
    node_list.add_selected()
    node_list.add_selected()
    assert node_list.nodes() == ["|rig|geo|body"]
    assert node_list.list_widget.item(0).text() == "body"

    cmds.select("|other|body")
    node_list.add_selected()
    assert node_list.nodes() == ["|rig|geo|body", "|other|body"]
    assert len(changed) == 2

    node_list.list_widget.item(0).setSelected(True)
    node_list.remove_selected()
    assert node_list.nodes() == ["|other|body"]

    node_list.set_nodes(["|a", "|b", "|a"])
    assert node_list.nodes() == ["|a", "|b"]

    # Settings protocol: QSettings returns a one-item list as a string.
    node_list.set_settings_value("|single")
    assert node_list.settings_value() == ["|single"]
    node_list.set_settings_value(None)
    assert node_list.nodes() == []


def test_recent_files_menu(clean_settings):
    import os
    from mgear.core import widgets

    key = _KEY_PREFIX + "recent"
    menu = widgets.RecentFilesMenu(key, max_entries=3, settings=clean_settings)
    assert menu.files() == []
    assert menu.actions()[0].text() == "(empty)"
    assert not menu.actions()[0].isEnabled()

    paths = [os.path.abspath("file_{}.bgh".format(i)) for i in range(4)]
    for path in paths:
        menu.add_file(path)
    assert menu.files() == paths[::-1][:3]

    menu.add_file(paths[2])
    assert menu.files()[0] == paths[2]
    assert len(menu.files()) == 3

    picked = []
    menu.fileTriggered.connect(picked.append)
    menu.actions()[0].trigger()
    assert picked == [paths[2]]

    # A new menu with the default settings reads the persisted list.
    assert widgets.RecentFilesMenu(key).files() == menu.files()
    menu.clear_files()
    assert menu.files() == []


def test_settings_mixin_round_trip(clean_settings):
    from mgear.vendor.Qt import QtCore
    from mgear.vendor.Qt import QtWidgets
    from mgear.core import pyqt
    from mgear.core import widgets

    class Tool(QtWidgets.QWidget, pyqt.SettingsMixin):
        def __init__(self):
            super(Tool, self).__init__()
            pyqt.SettingsMixin.__init__(self)
            self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.slider.setRange(0, 100)
            self.spin = QtWidgets.QSpinBox()
            self.dspin = QtWidgets.QDoubleSpinBox()
            self.toggle = QtWidgets.QPushButton()
            self.toggle.setCheckable(True)
            self.swatch = widgets.ColorSwatchButton()
            self.nodes = widgets.NodeListWidget()
            self.user_settings = {
                _KEY_PREFIX + "slider": (self.slider, 50),
                _KEY_PREFIX + "spin": (self.spin, 1),
                _KEY_PREFIX + "dspin": (self.dspin, 0.5),
                _KEY_PREFIX + "toggle": (self.toggle, True),
                _KEY_PREFIX + "color": (self.swatch, [1.0, 0.0, 0.0]),
                _KEY_PREFIX + "nodes": (self.nodes, []),
            }

    first = Tool()
    first.load_settings()
    assert first.slider.value() == 50
    assert first.toggle.isChecked()
    assert first.swatch.color() == (1.0, 0.0, 0.0)

    # Changing a value saves automatically through the connected signals.
    first.slider.setValue(42)
    first.spin.setValue(7)
    first.dspin.setValue(0.25)
    first.toggle.setChecked(False)
    first.swatch.set_color((0.2, 0.4, 0.6))
    first.nodes.set_nodes(["|a"])

    second = Tool()
    second.load_settings()
    assert second.slider.value() == 42
    assert second.spin.value() == 7
    assert second.dspin.value() == pytest.approx(0.25)
    assert not second.toggle.isChecked()
    assert second.swatch.color() == pytest.approx((0.2, 0.4, 0.6))
    assert second.nodes.nodes() == ["|a"]
