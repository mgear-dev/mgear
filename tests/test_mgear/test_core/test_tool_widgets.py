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


def test_settings_mixin_writes_file_once_per_burst(clean_settings):
    """A slider drag stores every value but writes the file once."""
    import time

    from mgear.vendor.Qt import QtCore
    from mgear.vendor.Qt import QtWidgets
    from mgear.core import pyqt

    class Tool(QtWidgets.QWidget, pyqt.SettingsMixin):
        SETTINGS_SYNC_DELAY = 20

        def __init__(self):
            super(Tool, self).__init__()
            pyqt.SettingsMixin.__init__(self)
            self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.slider.setRange(0, 100)
            self.user_settings = {_KEY_PREFIX + "burst": (self.slider, 0)}

    tool = Tool()
    tool.load_settings()
    syncs = []
    real_sync = tool.settings.sync
    tool.settings.sync = lambda: (syncs.append(1), real_sync())

    for value in range(1, 51):
        tool.slider.setValue(value)
    # Stored at once: another settings object of the process sees it
    assert int(pyqt.get_user_settings().value(_KEY_PREFIX + "burst")) == 50
    assert syncs == []

    deadline = time.time() + 2.0
    while not syncs and time.time() < deadline:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)
    assert syncs == [1]


def test_float_slider_spin_box(qt_app):
    from mgear.core import widgets

    widget = widgets.FloatSliderSpinBox("Damping", 0.0, 1.0, 0.5)
    changed = []
    committed = []
    widget.valueChanged.connect(changed.append)
    widget.valueCommitted.connect(committed.append)

    # Slider midpoint -> spin box value; a track change commits at once.
    widget.slider.setValue(widget.SLIDER_STEPS // 4)
    assert widget.value() == pytest.approx(0.25)
    assert changed[-1] == pytest.approx(0.25)
    assert committed == [pytest.approx(0.25)]

    # A drag commits only once, on release.
    del committed[:]
    widget.slider.setSliderDown(True)
    for position in (300, 600, 900):
        widget.slider.setValue(position)
    assert committed == []
    # setSliderDown(False) emits sliderReleased
    widget.slider.setSliderDown(False)
    assert committed == [pytest.approx(0.9)]

    # setValue does not emit.
    del changed[:]
    widget.setValue(0.1)
    assert widget.value() == pytest.approx(0.1)
    assert changed == []


def test_float_slider_spin_box_mixed_and_soft_max(qt_app):
    from mgear.core import widgets

    widget = widgets.FloatSliderSpinBox("", 0.0, 100.0, 1.0, soft_maximum=10.0)
    committed = []
    widget.valueCommitted.connect(committed.append)

    widget.setMixed(True)
    assert widget.isMixed()
    assert widget.spin_box.text() == widget.MIXED_TEXT
    assert committed == []

    # Typing a value clears the mixed state and commits it.
    widget.spin_box.setValue(0.3)
    assert not widget.isMixed()
    assert committed == [pytest.approx(0.3)]

    # A value above the soft maximum extends the slider range.
    widget.setValue(50.0)
    assert widget.slider.value() == widget.SLIDER_STEPS
    widget.setValue(25.0)
    assert widget.slider.value() == widget.SLIDER_STEPS // 2


def test_set_proxy_filter(qt_app):
    from mgear.core import pyqt
    from mgear.vendor.Qt import QtCore
    from mgear.vendor.Qt import QtGui

    model = QtGui.QStandardItemModel()
    for name in ("Tail_soft", "hair_stiff", "a(b"):
        model.appendRow(QtGui.QStandardItem(name))
    proxy = QtCore.QSortFilterProxyModel()
    proxy.setSourceModel(model)

    def visible():
        return [proxy.index(row, 0).data() for row in range(proxy.rowCount())]

    pyqt.set_proxy_filter(proxy, "tail")
    assert visible() == ["Tail_soft"]
    pyqt.set_proxy_filter(proxy, "ta*l")
    assert visible() == ["Tail_soft"]
    pyqt.set_proxy_filter(proxy, "tail", case_sensitive=True)
    assert visible() == []
    pyqt.set_proxy_filter(proxy, "a(b")
    assert visible() == ["a(b"]
    pyqt.set_proxy_filter(proxy, "")
    assert len(visible()) == 3


def test_set_smooth_scroll(qt_app):
    from mgear.core import pyqt
    from mgear.vendor.Qt import QtWidgets

    per_item = QtWidgets.QAbstractItemView.ScrollPerItem
    per_pixel = QtWidgets.QAbstractItemView.ScrollPerPixel
    view = QtWidgets.QListWidget()
    view.setHorizontalScrollMode(per_item)
    view.horizontalScrollBar().setSingleStep(1)

    pyqt.set_smooth_scroll(view, step=20)
    step = int(round(pyqt.dpi_scale(20)))
    assert view.verticalScrollMode() == per_pixel
    assert view.verticalScrollBar().singleStep() == step
    # Horizontal is left untouched by default.
    assert view.horizontalScrollMode() == per_item
    assert view.horizontalScrollBar().singleStep() == 1

    pyqt.set_smooth_scroll(view, step=20, horizontal=True)
    assert view.horizontalScrollMode() == per_pixel
    assert view.horizontalScrollBar().singleStep() == step


def test_custom_step_list_smooth_scroll(qt_app):
    from mgear.shifter import custom_step_widget
    from mgear.vendor.Qt import QtWidgets

    view = custom_step_widget.CustomStepListWidget()
    assert view.verticalScrollMode() == QtWidgets.QAbstractItemView.ScrollPerPixel


def test_custom_step_tab_list_heights(clean_settings):
    from mgear.core import pyqt
    from mgear.shifter import custom_step_widget as csw

    keys = (csw.PRE_LIST_HEIGHT_KEY, csw.POST_LIST_HEIGHT_KEY)
    for key in keys:
        clean_settings.remove(key)

    # Defaults, one grip per list.
    tab = csw.CustomStepTab()
    default = int(pyqt.dpi_scale(csw.LIST_HEIGHT))
    assert tab.preCustomStep_listWidget.maximumHeight() == default
    assert tab.postCustomStep_listWidget.maximumHeight() == default

    # A finished drag is saved and restored by the next tab.
    tab.preCustomStep_grip.set_target_height(320)
    tab.preCustomStep_grip.heightCommitted.emit(320)
    tab.postCustomStep_grip.set_target_height(1)
    tab.postCustomStep_grip.heightCommitted.emit(1)
    minimum = int(pyqt.dpi_scale(csw.LIST_MIN_HEIGHT))
    assert tab.postCustomStep_listWidget.maximumHeight() == minimum

    restored = csw.CustomStepTab()
    assert restored.preCustomStep_listWidget.maximumHeight() == 320
    assert restored.postCustomStep_listWidget.maximumHeight() == minimum


def test_collapsible_widget_signal(qt_app):
    from mgear.core import widgets

    section = widgets.CollapsibleWidget("Test", expanded=True, expandable=False)
    states = []
    section.expandedChanged.connect(states.append)
    section.set_expanded(False)
    section.set_expanded(False)
    section.on_header_clicked()
    assert states == [False, True]
    assert section.is_expanded()
    assert not section.is_expandable()


def test_height_grip(qt_app):
    from mgear.core import widgets
    from mgear.vendor.Qt import QtWidgets

    target = QtWidgets.QListWidget()
    grip = widgets.HeightGrip(target, minimum=50, maximum=300)
    heights = []
    grip.heightChanged.connect(heights.append)
    grip.set_target_height(120)
    assert target.minimumHeight() == target.maximumHeight() == 120
    grip.set_target_height(1000)
    assert target.maximumHeight() == 300
    grip.set_settings_value("80")
    assert grip.settings_value() == target.height()
    grip.set_settings_value("bad")
    assert heights == [120, 300, 80]


def test_logical_dpi_without_a_main_window(qt_app, monkeypatch):
    """Without Maya's main window (mayapy), the scale is the screen's: Qt 5
    gives a high DPI screen 144 DPI and sizes widgets by it. Before Qt runs
    it is 96, not kept."""
    import os

    from mgear.core import pyqt
    from mgear.vendor.Qt import QtWidgets

    monkeypatch.delenv(pyqt._LOGICAL_DPI_KEY, raising=False)
    monkeypatch.setattr(pyqt, "maya_main_window", lambda: None)
    screen = int(round(qt_app.primaryScreen().logicalDotsPerInchX()))
    assert pyqt.get_logicaldpi() == screen
    assert pyqt.dpi_scale(100) == 100 * max(1, min(screen / 96.0, 2))
    # no QApplication yet: 96, read again later
    monkeypatch.delenv(pyqt._LOGICAL_DPI_KEY)
    monkeypatch.setattr(QtWidgets.QApplication, "instance", staticmethod(lambda: None))
    assert pyqt.get_logicaldpi() == 96
    assert pyqt._LOGICAL_DPI_KEY not in os.environ


def test_pyqt_image_and_settings_helpers(clean_settings):
    from mgear.core import pyqt
    from mgear.vendor.Qt import QtGui
    from mgear.vendor.Qt import QtWidgets

    image = QtGui.QImage(200, 100, QtGui.QImage.Format_RGB32)
    square = pyqt.square_crop_image(image, 64)
    assert (square.width(), square.height()) == (64, 64)
    assert pyqt.square_crop_image(None, 64) is None
    badge = pyqt.text_badge("V", 32, QtGui.QColor(10, 20, 30))
    assert badge.width() == 32
    assert pyqt.text_width(QtWidgets.QLabel().fontMetrics(), "abc") > 0

    class Holder(pyqt.SettingsMixin):
        pass

    holder = Holder()
    holder.save_json_setting("pytest_json", {"a": [1, 2]})
    assert holder.load_json_setting("pytest_json", {}) == {"a": [1, 2]}
    assert holder.load_json_setting("pytest_json", []) == []
    holder.settings.setValue("pytest_json", "{bad")
    assert holder.load_json_setting("pytest_json", {}) == {}


def test_tristate_and_thumbnail_editor(qt_app):
    from mgear.core import widgets
    from mgear.vendor.Qt import QtGui

    box = widgets.TriStateCheckBox()
    committed = []
    box.valueCommitted.connect(committed.append)
    box.setMixed(True)
    assert box.isMixed()
    box.click()
    assert committed == [True] and not box.isMixed()
    box.setValue(False)
    assert box.value() is False and committed == [True]

    editor = widgets.ThumbnailEditor(size=64, image_size=32)
    assert editor.image() is None
    editor.set_image(QtGui.QImage(100, 50, QtGui.QImage.Format_RGB32))
    assert editor.image().width() == 32
    editor.clear()
    assert editor.image() is None


def test_height_grip_commit(qt_app):
    from mgear.core import widgets
    from mgear.vendor.Qt import QtWidgets

    target = QtWidgets.QListWidget()
    grip = widgets.HeightGrip(target, minimum=50, maximum=300)
    assert grip.settings_signal() is grip.heightCommitted


def test_vector_spin_box(qt_app):
    from mgear.core import widgets

    widget = widgets.VectorSpinBox(default=(0.0, 1.0, 0.0))
    committed = []
    widget.valueCommitted.connect(committed.append)
    widget.spin_boxes[1].setValue(2.0)
    assert committed == [(0.0, 2.0, 0.0)]

    widget.setMixed([True, False, True])
    assert widget.isMixed()
    assert widget.value() == (None, 2.0, None)
    widget.spin_boxes[0].setValue(5.0)
    assert committed[-1] == (5.0, 2.0, None)
    widget.setValue((1, 2, 3))
    assert widget.value() == (1.0, 2.0, 3.0) and not widget.isMixed()


def test_show_stacked_page(qt_app):
    from mgear.core import pyqt
    from mgear.vendor.Qt import QtWidgets

    stack = QtWidgets.QStackedWidget()
    small = QtWidgets.QLabel("small")
    big = QtWidgets.QLabel("big")
    big.setMinimumHeight(400)
    stack.addWidget(small)
    stack.addWidget(big)
    pyqt.show_stacked_page(stack, small)
    assert stack.currentWidget() is small
    assert stack.sizeHint().height() < 400
    assert big.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Ignored
