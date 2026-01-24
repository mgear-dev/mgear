import maya.cmds as cmds
import mgear.pymaya as pm
from mgear.core import pyflow_widgets
from mgear.core import widgets as mwgt
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
import random
from functools import partial

from . import channel_master_utils as cmu


TABLE_STYLE = """
        QTableView {
           border: 0 solid transparent;
        }
        """

CHECKBOX_STYLE = """
        QCheckBox {
            background-color: #3C3C3C;
        }
        QWidget {
            background-color: #3C3C3C;
        }

        """


##################
# Helper functions
##################


def refresh_key_button_color(button, attr, current_time=False):
    """refresh the key button color based on the animation of a given attribute

    Args:
        button (QPushButton): The button to update the color
        attr (str): the attribute fullName
    """
    if cmu.channel_has_animation(attr):
        if cmu.value_equal_keyvalue(attr, current_time):
            if cmu.current_frame_has_key(attr):
                button.setStyleSheet(
                    "QPushButton {background-color: #ce5846;}"
                )
            else:
                button.setStyleSheet(
                    "QPushButton {background-color: #89bf72;}"
                )
        else:
            button.setStyleSheet("QPushButton {background-color: #ddd87c;}")

    else:
        button.setStyleSheet("QPushButton {background-color: #ABA8A6;}")


def random_color(min_val=0.01, max_val=0.6):
    r = random.uniform(min_val, max_val)
    g = random.uniform(min_val, max_val)
    b = random.uniform(min_val, max_val)
    color = QtGui.QColor()

    color.setRgbF(r, g, b)

    return color


###################################################
# Widgets
###################################################


class CheckBoxWidget(QtWidgets.QWidget):
    def __init__(self, val=False):
        super(CheckBoxWidget, self).__init__()

        # Create the QHBoxLayout
        layout = QtWidgets.QHBoxLayout(self)

        # Create the QCheckBox
        cbox = QtWidgets.QCheckBox()
        cbox.setStyleSheet(CHECKBOX_STYLE)
        layout.addWidget(cbox)

        # Set the layout properties
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        # Set the initial value of the QCheckBox
        if val:
            cbox.setChecked(True)

        # Set the widget style
        self.setStyleSheet(CHECKBOX_STYLE)

        # Set the widget layout
        self.setLayout(layout)

        self.setFocusPolicy(QtCore.Qt.NoFocus)


###################################################
# Channel Table Class
###################################################


class ChannelTable(QtWidgets.QTableWidget):

    sliderMoved = QtCore.Signal(int)

    def __init__(self, chan_config=None, namespace=None, parent=None):
        super(ChannelTable, self).__init__(parent)
        self._fixed_square = pyqt.dpi_scale(17)
        self.chan_config = chan_config
        self.trigger_value_update = True
        self.namespace = namespace
        self.track_widgets = []
        self.create_menu()
        self.setup_table()
        self.config_table()
        self.itemSelectionChanged.connect(self.auto_sync_graph_editor)
        # self.custom_signals = CustomSignals()

    def create_menu(self):
        self.menu = QtWidgets.QMenu(self)

        reset_value_action = QtWidgets.QAction("Reset Value to Default", self)
        reset_value_action.setIcon(pyqt.get_icon("mgear_rewind"))
        reset_value_action.triggered.connect(self.reset_value_slot)
        self.menu.addAction(reset_value_action)
        reset_creation_value_action = QtWidgets.QAction(
            "Reset to Creation Value", self
        )
        reset_creation_value_action.setIcon(pyqt.get_icon("mgear_rewind"))
        reset_creation_value_action.triggered.connect(
            self.reset_creation_value_slot
        )
        self.menu.addAction(reset_creation_value_action)
        self.menu.addSeparator()

        sync_graph_editor_action = QtWidgets.QAction(
            "Sync Selected with Graph Editor", self
        )
        sync_graph_editor_action.setIcon(pyqt.get_icon("mgear_activity"))
        sync_graph_editor_action.triggered.connect(self.sync_graph_editor)
        self.menu.addAction(sync_graph_editor_action)
        self.menu.addSeparator()

        select_attr_host_action = QtWidgets.QAction("Select Host", self)
        select_attr_host_action.setIcon(pyqt.get_icon("mgear_arrow-up"))
        select_attr_host_action.triggered.connect(self.select_host)
        self.menu.addAction(select_attr_host_action)
        self.menu.addSeparator()

        set_range_action = QtWidgets.QAction("Set Range", self)
        set_range_action.setIcon(pyqt.get_icon("mgear_sliders"))
        set_range_action.triggered.connect(self.set_range_slot)
        self.menu.addAction(set_range_action)
        self.menu.addSeparator()

        self.menu.addSeparator()
        set_color_action = QtWidgets.QAction("Set Color", self)
        set_color_action.setIcon(pyqt.get_icon("mgear_edit-2"))
        set_color_action.triggered.connect(self.set_color_slot)
        self.menu.addAction(set_color_action)

        auto_color_host_action = QtWidgets.QAction("Auto Color by Host", self)
        auto_color_host_action.setIcon(pyqt.get_icon("mgear_edit-3"))
        auto_color_host_action.triggered.connect(self.auto_color_host_slot)
        self.menu.addAction(auto_color_host_action)

        auto_color_axis_action = QtWidgets.QAction("Auto Color by Axis", self)
        auto_color_axis_action.setIcon(pyqt.get_icon("mgear_edit-3"))
        auto_color_axis_action.triggered.connect(self.auto_color_axis_slot)
        self.menu.addAction(auto_color_axis_action)

        clear_color_action = QtWidgets.QAction("Clear Color", self)
        clear_color_action.setIcon(pyqt.get_icon("mgear_x-octagon"))
        clear_color_action.triggered.connect(self.clear_color_slot)
        self.menu.addAction(clear_color_action)

    def set_color_slot(self, items=None, color=None):
        if not items:
            items = self.selectedItems()
        if items:
            if not color:
                color = QtWidgets.QColorDialog.getColor(
                    items[0].background().color(),
                    parent=self,
                    options=QtWidgets.QColorDialog.DontUseNativeDialog,
                )
            if not color.isValid():
                return

            for itm in items:
                itm.setBackground(color)
                attr_config = itm.data(QtCore.Qt.UserRole)
                attr_config["color"] = color.getRgbF()
                itm.setData(QtCore.Qt.UserRole, attr_config)

    def auto_color_host_slot(self):
        ctls = []
        ctls_colors = {}
        # for i in xrange(self.rowCount()):
        #     itm = self.item(i, 0)
        for itm in self.selectedItems():
            attr_config = itm.data(QtCore.Qt.UserRole)
            ctl = attr_config["ctl"]
            if ctl not in ctls:
                ctls.append(ctl)
                ctls_colors[ctl] = random_color()
            itm.setBackground(ctls_colors[ctl])
            attr_config["color"] = ctls_colors[ctl].getRgbF()
            itm.setData(QtCore.Qt.UserRole, attr_config)

    def auto_color_axis_slot(self):
        for itm in self.selectedItems():
            attr_config = itm.data(QtCore.Qt.UserRole)
            f_name = attr_config["fullName"]
            colors = [[0.8, 0.0, 0.1], [0.0, 0.57, 0.0], [0.0, 0.0, 0.75]]

            color = QtGui.QColor()
            if f_name.endswith("X"):
                color.setRgbF(*colors[0])
            elif f_name.endswith("Y"):
                color.setRgbF(*colors[1])
            elif f_name.endswith("Z"):
                color.setRgbF(*colors[2])
            else:
                continue

            itm.setBackground(color)
            attr_config["color"] = color.getRgbF()
            itm.setData(QtCore.Qt.UserRole, attr_config)

    def sync_graph_editor(self):
        items = self.selectedItems()
        attr_configs = []
        if items:
            for itm in items:
                ac = itm.data(QtCore.Qt.UserRole)
                attr_configs.append(ac)
        cmu.sync_graph_editor(attr_configs, self.namespace)

    def auto_sync_graph_editor(self):
        chan_mast = self.parent().parent().parent()
        if chan_mast.display_auto_sync_graph_action.isChecked():
            self.sync_graph_editor()

    def select_host(self):
        items = self.selectedItems()
        if items:
            ctls = []
            for itm in items:
                attr_config = itm.data(QtCore.Qt.UserRole)
                ctls.append(attr_config["ctl"])
            pm.select(ctls)

    def reset_value_slot(self):
        items = self.selectedItems()
        if items:
            for itm in items:
                attr_config = itm.data(QtCore.Qt.UserRole)
                cmu.reset_attribute(attr_config, self.namespace)

    def reset_creation_value_slot(self):
        # reset the value to the orinal value when the channel was created
        items = self.selectedItems()
        if items:
            for itm in items:
                attr_config = itm.data(QtCore.Qt.UserRole)
                cmu.reset_creation_value_attribute(attr_config, self.namespace)

    def clear_color_slot(self):
        items = self.selectedItems()
        if items:
            for itm in items:
                itm.setBackground(QtGui.QColor(43, 43, 43))

    def set_range_slot(self):
        items = self.selectedItems()
        if items:
            init_range = None
            for itm in items:
                attr = itm.data(QtCore.Qt.UserRole)
                if attr["type"] in cmu.ATTR_SLIDER_TYPES:
                    ch_item = self.cellWidget(itm.row(), 2)
                    if not init_range:
                        init_range = ch_item.getRange()
                        set_range_dialog = SetRangeDialog(init_range, self)
                        result = set_range_dialog.exec_()

                        if result != QtWidgets.QDialog.Accepted:
                            return
                    new_range = set_range_dialog.get_range()
                    ch_item.setRange(new_range[0], new_range[1])

                    # store new range
                    attr_config = itm.data(QtCore.Qt.UserRole)
                    attr_config["min"] = new_range[0]
                    attr_config["max"] = new_range[1]
                    itm.setData(QtCore.Qt.UserRole, attr_config)

    def setup_table(self):
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.setColumnCount(3)
        self.setStyleSheet(TABLE_STYLE)
        horizontal_header_view = self.horizontalHeader()
        vertical_header_view = self.verticalHeader()
        horizontal_header_view.setVisible(False)
        vertical_header_view.setVisible(False)
        vertical_header_view.setMinimumSectionSize(self._fixed_square)
        horizontal_header_view.setMinimumSectionSize(self._fixed_square)

        horizontal_header_view.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents
        )
        horizontal_header_view.setSectionResizeMode(
            2, QtWidgets.QHeaderView.Stretch
        )

    def contextMenuEvent(self, event):
        if self.selectedItems():

            self.menu.popup(QtGui.QCursor.pos())

    def namespace_sync(self, name):
        """Sync the attribute name with the current name space

        Args:
            name (str): attribute name

        Returns:
            str: namespace sync name
        """
        # If the channel master node has Namespace, this name space will
        # override any namespace stored in the channel
        if self.namespace and self.namespace not in name:
            name = pm.NameParser(name).stripNamespace().__str__()
            name = self.namespace + name

        return name

    def config_table(self):
        def value_update(attr_config, *args):
            """Update the attribute from the  channel value

            Args:
                ch (QWidget): The channel widget
                atttr_config (dict): attribute configuration data
                *args: the current value
            """
            if self.trigger_value_update:
                try:
                    cmds.setAttr(
                        self.namespace_sync(attr_config["fullName"]), args[0]
                    )

                    # refresh button color while value update
                    for i in range(self.rowCount()):
                        item = self.item(i, 0)
                        attr = item.data(QtCore.Qt.UserRole)
                        if self.namespace_sync(
                            attr["fullName"]
                        ) == self.namespace_sync(attr_config["fullName"]):
                            button = self.cellWidget(i, 1)
                            refresh_key_button_color(
                                button,
                                self.namespace_sync(attr_config["fullName"]),
                            )
                            break
                except RuntimeError:
                    fname = self.namespace_sync(attr_config["fullName"])
                    pm.displayWarning(
                        "Channel {} not Found.".format(fname)
                        + " Maybe the channel master"
                        + " contains not existing channels. "
                        + "Review Channel Master configuration"
                    )

        def open_undo_chunk():
            cmds.undoInfo(openChunk=True)

        def close_undo_chunk():
            cmds.undoInfo(closeChunk=True)

        if not self.chan_config:
            return

        i = 0
        for ch in self.chan_config["channels"]:
            at = self.chan_config["channels_data"][ch]
            at_name = self.namespace_sync(at["fullName"])
            try:
                val = cmds.getAttr(at_name)
            except ValueError:
                pm.displayWarning(
                    "{} not found. Maybe wrong NameSpace?".format(at_name)
                )
                continue

            if at["type"] in cmu.ATTR_SLIDER_TYPES:
                if at["type"] == "long":
                    Type = "int"
                else:
                    Type = "float"
                ch_ctl = pyflow_widgets.pyf_Slider(
                    self,
                    self.sliderMoved,
                    Type=Type,
                    defaultValue=val,
                    sliderRange=(at["min"], at["max"]),
                )
                ch_ctl.valueChanged.connect(self.updateHighlightedSliders)

                ch_ctl.setMaximumHeight(self._fixed_square)
                ch_ctl.setMinimumHeight(self._fixed_square)
                ch_ctl.sld.setMaximumHeight(self._fixed_square)
                ch_ctl.sld.setMinimumHeight(self._fixed_square)
                ch_ctl.input.setMaximumHeight(self._fixed_square)
                ch_ctl.input.setMinimumHeight(self._fixed_square)

                ch_ctl.valueChanged.connect(partial(value_update, at))
                ch_ctl.sliderPressed.connect(open_undo_chunk)
                ch_ctl.sliderReleased.connect(close_undo_chunk)
                slider = ch_ctl.findChild(pyflow_widgets.slider)
                slider.editingStart.connect(open_undo_chunk)
                slider.editingFinished.connect(close_undo_chunk)

            elif at["type"] == "bool":
                ch_ctl = CheckBoxWidget(val)
                cbox = ch_ctl.findChild(QtWidgets.QCheckBox)
                cbox.stateChanged.connect(self.updateHighlightedSliders)
                cbox.toggled.connect(partial(value_update, at))

            elif at["type"] == "enum":

                # we handle special naming for separators
                if at["niceName"] == "__________":
                    continue
                else:
                    ch_ctl = QtWidgets.QComboBox()
                    ch_ctl.addItems(at["items"])
                    ch_ctl.setCurrentIndex(val)
                    ch_ctl.setFocusPolicy(QtCore.Qt.NoFocus)
                    ch_ctl.currentIndexChanged.connect(
                        self.updateHighlightedSliders
                    )

                    ch_ctl.currentIndexChanged.connect(
                        partial(value_update, at)
                    )

            label_item = QtWidgets.QTableWidgetItem(at["niceName"] + "  ")
            if at["color"]:
                color = QtGui.QColor()
                color.setRgbF(*at["color"])
                label_item.setBackground(color)
            label_item.setData(QtCore.Qt.UserRole, at)
            label_item.setTextAlignment(QtCore.Qt.AlignRight)
            label_item.setToolTip(self.namespace_sync(at["fullName"]))
            label_item.setFlags(label_item.flags() ^ QtCore.Qt.ItemIsEditable)

            key_button = self.create_key_button(at)

            self.insertRow(i)
            self.setRowHeight(i, self._fixed_square)
            self.setItem(i, 0, label_item)
            self.setCellWidget(i, 1, key_button)
            self.setCellWidget(i, 2, ch_ctl)

            self.track_widgets.append([key_button, ch_ctl])

            i += 1

        self.setColumnWidth(1, self._fixed_square)

    def update_table(self):
        """update table usin from the stored channel configuration"""
        self.clear()
        for i in range(self.rowCount()):
            self.removeRow(0)

        for x in self.track_widgets:
            x[0].deleteLater()
            x[1].deleteLater()

        self.track_widgets = []

        self.config_table()

    def update_table_from_selection(self):
        """Update the  table with the channels of the selected object
        If multiple objects are selected. Only the las selected will be listed
        """
        cc, ns = cmu.get_table_config_from_selection()
        self.chan_config = cc
        self.namespace = ns
        self.update_table()

    def refresh_channels_values(self, current_time=False):
        """refresh the channel values of the table"""
        self.trigger_value_update = False
        for i in range(self.rowCount()):
            ch_item = self.cellWidget(i, 2)
            item = self.item(i, 0)
            attr = item.data(QtCore.Qt.UserRole)
            try:
                if current_time:
                    # Note: we can not set time to False because looks like
                    # having this flag force the evaluation on the animation
                    # curve and not in the current attribute value
                    val = cmds.getAttr(
                        self.namespace_sync(attr["fullName"]),
                        time=current_time,
                    )
                else:
                    val = cmds.getAttr(self.namespace_sync(attr["fullName"]))
                if attr["type"] in cmu.ATTR_SLIDER_TYPES:
                    ch_item.setValue(val)
                elif attr["type"] == "bool":
                    # if val:
                    cbox = ch_item.findChildren(QtWidgets.QCheckBox)[0]
                    cbox.setChecked(val)
                elif attr["type"] == "enum":
                    ch_item.setCurrentIndex(val)

                # refresh button color
                button_item = self.cellWidget(i, 1)
                refresh_key_button_color(
                    button_item,
                    self.namespace_sync(attr["fullName"]),
                    current_time,
                )
            except ValueError:
                pass

        self.trigger_value_update = True

    def get_channel_config(self, idx):
        item = self.item(idx, 0)
        config_data = item.data(QtCore.Qt.UserRole)
        return config_data

    def get_table_config(self):
        config_data = cmu.init_table_config_data()
        for i in range(self.rowCount()):
            chan_data = self.get_channel_config(i)
            # fullname = self.namespace_sync(chan_data["fullName"])
            # we don't want to store with namespace
            fullname = chan_data["fullName"]
            config_data["channels"].append(fullname)
            config_data["channels_data"][fullname] = chan_data

        return config_data

    def set_channel_config(self, config):
        # NOTE: using full name to set data. Check the dict data when create
        # for the first time.
        pass

    def set_table_config(self, config, namespace=None):
        self.chan_config = config
        self.namespace = namespace
        self.update_table()

    def set_channel_fullname(self, idx, fullName=True):
        """Set the channel Full Name

        Args:
            idx (int): Channel index
            fullName (bool, optional): If true will set the fullname
        """
        if fullName:
            key = "fullName"
        else:
            key = "niceName"
        item = self.item(idx, 0)
        txt = item.data(QtCore.Qt.UserRole)[key] + "  "
        item.setText(txt)

    def create_key_button(self, item_data):
        """Create a keyframing button

        Args:
            item_data (dict): Attribute channel configuration dictionary

        Returns:
            QPushButton: The keyframe button
        """
        button = mwgt.create_button(size=self._fixed_square)
        attr = self.namespace_sync(item_data["fullName"])
        refresh_key_button_color(button, attr)

        # right click menu
        pop_menu = QtWidgets.QMenu(button)

        next_key_action = QtWidgets.QAction("Next Keyframe", button)
        next_key_action.setIcon(pyqt.get_icon("mgear_arrow-right"))
        next_key_action.triggered.connect(partial(cmu.next_keyframe, attr))
        pop_menu.addAction(next_key_action)

        previous_key_action = QtWidgets.QAction("previous Keyframe", button)
        previous_key_action.setIcon(pyqt.get_icon("mgear_arrow-left"))
        previous_key_action.triggered.connect(
            partial(cmu.previous_keyframe, attr)
        )
        pop_menu.addAction(previous_key_action)

        pop_menu.addSeparator()

        remove_animation_action = QtWidgets.QAction("Remove Animation", button)
        remove_animation_action.setIcon(pyqt.get_icon("mgear_trash"))
        remove_animation_action.triggered.connect(
            partial(cmu.remove_animation, attr)
        )
        pop_menu.addAction(remove_animation_action)

        def context_menu(point):
            pop_menu.exec_(button.mapToGlobal(point))

        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(context_menu)

        def button_clicked():
            has_key = cmu.current_frame_has_key(attr)
            key_val = cmu.value_equal_keyvalue(attr)
            if has_key and key_val:
                cmu.remove_key(attr)

            else:
                cmu.set_key(attr)

            refresh_key_button_color(button, attr)

        button.clicked.connect(button_clicked)

        return button

    def get_selected_rows(self):
        selected_rows = set()
        for index in self.selectedIndexes():
            selected_rows.add(index.row())

        return selected_rows

    def get_fullname_from_selected_rows(self):
        attrs = set()
        for row in self.get_selected_rows():
            item = self.item(row, 0)
            attr = self.namespace_sync(
                item.data(QtCore.Qt.UserRole)["fullName"]
            )
            attrs.add(attr)
        return attrs

    def updateHighlightedSliders(self, value):
        """
        Update multiple sliders simultaneously, only if the sender's row is
        currently selected.

        Behaviour:
            - If multiple rows are selected, and you drag one slider:
                  all selected rows update together.
            - If you drag a slider on a row that is NOT selected:
                  only that one updates (solo edit), even if others are selected.

        This avoids destroying the multi-edit workflow, while allowing quick
        single-channel adjustments.
        """
        # -- If ChannelMaster has disabled slider updates globally, stop here
        if self.parent().parent().parent().doUpdateHighlightedSliders:

            selected_rows = self.get_selected_rows()
            sender = self.sender()

            # -- Find which row the sender widget belongs to
            sender_row = 0
            for row in range(self.rowCount()):
                widget = self.cellWidget(row, 2)
                if not widget:
                    continue

                # -- Direct match: the sender is the widget in this row
                if widget is sender:
                    sender_row = row
                    break

                # -- Checkbox widgets contain an inner QCheckBox, so check that as well
                checkbox = widget.findChild(QtWidgets.QCheckBox)
                if checkbox is sender:
                    sender_row = row
                    break

            # -- If the sender is not part of the selected rows, treat as solo edit
            # -- So only update this one row and do not propagate to others
            if sender_row is not None and sender_row not in selected_rows:
                return

            # -- For slider we need to connect the undo when mouse press event
            # -- For combobox and check box we do it here before the loop
            # -- This solution we need to undo 2 times to restore the previous values
            if isinstance(sender, (QtWidgets.QComboBox, QtWidgets.QCheckBox)):
                cmds.undoInfo(openChunk=True)

            # -- Update all selected rows
            for row in selected_rows:
                slider = self.cellWidget(row, 2)
                sender_type = type(sender)

                # -- For CheckBoxWidget, the real widget is inside
                if isinstance(slider, CheckBoxWidget):
                    slider_type = slider.findChild(QtWidgets.QCheckBox)
                else:
                    slider_type = slider

                # -- Only update widgets of the same type as the sender
                if slider != sender and isinstance(slider_type, sender_type):
                    # -- Handle combobox editing
                    if isinstance(slider, QtWidgets.QComboBox):
                        signal = slider.currentIndexChanged
                        set_value = slider.setCurrentIndex

                    # -- Handle checkbox editing
                    elif isinstance(slider, CheckBoxWidget):
                        checkbox = slider.findChild(QtWidgets.QCheckBox)
                        signal = checkbox.stateChanged
                        set_value = checkbox.setChecked

                        # -- Checkboxes emit 0/1/2, clamp to valid state
                        if value > 1:
                            value = 1

                    # -- Handle float/int slider widgets
                    elif isinstance(slider, pyflow_widgets.pyf_Slider):
                        signal = slider.valueChanged
                        set_value = slider.setValue

                    else:
                        signal = None

                    # -- If no compatible signal exists, skip...
                    if signal:
                        # -- Temporarily disconnect to avoid recursion
                        signal.disconnect(self.updateHighlightedSliders)
                        # -- Apply the UI update
                        # -- This is a callable variable
                        set_value(value)

                        # -- Update Maya attribute
                        item = self.item(row, 0)
                        attr_config = item.data(QtCore.Qt.UserRole)
                        cmds.setAttr(self.namespace_sync(attr_config["fullName"]), value)

                        # -- Reconnect after update
                        signal.connect(self.updateHighlightedSliders)

            # -- Close the undo chunk after the loop is finished
            if isinstance(sender, (QtWidgets.QComboBox, QtWidgets.QCheckBox)):
                cmds.undoInfo(closeChunk=True)


##################
# set range dialog
##################


class SetRangeDialog(QtWidgets.QDialog):
    """
    Set range dialog
    """

    def __init__(self, init_range=None, parent=None):
        super(SetRangeDialog, self).__init__(parent)

        self.setWindowTitle("Set Range")
        flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        self.init_range = init_range

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.min_spinbox = QtWidgets.QDoubleSpinBox()
        self.min_spinbox.setFixedWidth(80)
        self.min_spinbox.setMinimum(-1000000)
        self.min_spinbox.setMaximum(1000000)
        self.max_spinbox = QtWidgets.QDoubleSpinBox()
        self.max_spinbox.setMinimum(-1000000)
        self.max_spinbox.setMaximum(1000000)
        self.max_spinbox.setFixedWidth(80)
        if self.init_range:
            self.min_spinbox.setValue(self.init_range[0])
            self.max_spinbox.setValue(self.init_range[1])

        self.ok_btn = QtWidgets.QPushButton("OK")

    def create_layout(self):
        wdg_layout = QtWidgets.QHBoxLayout()
        wdg_layout.addWidget(QtWidgets.QLabel("Min: "))
        wdg_layout.addWidget(self.min_spinbox)
        wdg_layout.addWidget(QtWidgets.QLabel("Max: "))
        wdg_layout.addWidget(self.max_spinbox)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(wdg_layout)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.ok_btn.clicked.connect(self.accept)

    def get_range(self):
        return [self.min_spinbox.value(), self.max_spinbox.value()]


##################
# create Node dialog
##################


class NameDialog(QtWidgets.QDialog):
    """
    Name Dialog
    """

    def __init__(self, parent=None):
        super(NameDialog, self).__init__(parent)

        flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.name_lineEdit.installEventFilter(self)

    def create_widgets(self):
        self.name_label = QtWidgets.QLabel("Name: ")
        self.name_lineEdit = QtWidgets.QLineEdit()

        self.ok_btn = QtWidgets.QPushButton("OK")

    def create_layout(self):
        wdg_layout = QtWidgets.QHBoxLayout()
        wdg_layout.addWidget(self.name_label)
        wdg_layout.addWidget(self.name_lineEdit)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(wdg_layout)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        self.ok_btn.clicked.connect(self.accept)

    def get_name(self):
        return self.name_lineEdit.text()

    def eventFilter(self, obj, event):
        if (
            obj == self.name_lineEdit
            and event.type() == QtCore.QEvent.KeyPress
        ):
            key = event.key()
            if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
                self.accept()
                return True
        return


class CreateChannelMasterNodeDialog(NameDialog):
    """
    Create Channel Master nore dialog
    """

    def __init__(self, parent=None):
        super(CreateChannelMasterNodeDialog, self).__init__(parent)

        self.setWindowTitle("Node Name")


class CreateChannelMasterTabDialog(NameDialog):
    """
    Create new tab dialog
    """

    def __init__(self, parent=None):
        super(CreateChannelMasterTabDialog, self).__init__(parent)

        self.setWindowTitle("Tab Name")
