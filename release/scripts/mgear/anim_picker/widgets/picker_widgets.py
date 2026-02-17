from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import re
import copy
import uuid

from math import pi
from math import sin
from math import cos

import maya.cmds as cmds

from mgear.core import pyqt
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

# debugging
# from PySide2 import QtGui
# from PySide2 import QtCore
# from PySide2 import QtWidgets

from mgear.anim_picker.widgets import basic
from mgear.anim_picker.handlers import (
    __EDIT_MODE__,
    __SELECTION__,
    python_handlers,
    maya_handlers,
)
from mgear.core.six.moves import range

# constants -------------------------------------------------------------------
SCRIPT_DOC_HEADER = """
# Variable reference for custom script execution on pickers.
# Use the following variables in your code to access related data:
# __CONTROLS__ for picker item associated controls (will return sets and not content).
# __FLATCONTROLS__ for associated controls and control set content.
# __NAMESPACE__ for current picker namespace
# __INIT__ use 'if not' statement to avoid code execution on creation.
# __SELF__ to get access to the PickerItem() instace. (Change color, size, etc)

"""


# =============================================================================
# general functions
# =============================================================================
def select_picker_controls(picker_items, event, modifiers=None):
    if __EDIT_MODE__.get():
        return
    if modifiers:
        modifiers = modifiers
    else:
        modifiers = event.modifiers()
    modifier = None

    # Shift cases (toggle)
    if modifiers == QtCore.Qt.ShiftModifier:
        modifier = "shift"

    # Controls case
    if modifiers == QtCore.Qt.ControlModifier:
        modifier = "control"

    # Alt case (remove)
    if modifiers == QtCore.Qt.AltModifier:
        modifier = "alt"

    picker_controls = []
    for pItem in picker_items:
        picker_controls.extend(pItem.get_controls())
    maya_handlers.select_nodes(picker_controls, modifier=modifier)


# =============================================================================
# classes
# =============================================================================
class CustomScriptEditDialog(QtWidgets.QDialog):
    """Custom python script window (used for custom picker item
    action and context menu)
    """

    __TITLE__ = "Custom script"

    def __init__(self, parent=None, cmd=None, item=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.cmd = cmd
        self.picker_item = item

        self.apply = False
        self.setup()

    def setup(self):
        """Build/Setup the dialog window"""
        self.setWindowTitle(self.__TITLE__)

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add cmd txt field
        self.cmd_widget = QtWidgets.QTextEdit()
        if self.cmd:
            text = self.cmd
        else:
            text = SCRIPT_DOC_HEADER
        self.cmd_widget.setText(text)
        newCursor = self.cmd_widget.textCursor()
        newCursor.movePosition(QtGui.QTextCursor.End)
        self.cmd_widget.setTextCursor(newCursor)
        self.main_layout.addWidget(self.cmd_widget)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = basic.CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = basic.CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

        run_btn = basic.CallbackButton(callback=self.run_event)
        run_btn.setText("Run")
        btn_layout.addWidget(run_btn)

        self.resize(500, 600)

    def accept_event(self):
        """Accept button event"""
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        """Cancel button event"""
        self.apply = False
        self.close()

    def run_event(self):
        """Run event button"""
        cmd_str = str(self.cmd_widget.toPlainText())

        if self.picker_item:
            python_handlers.safe_code_exec(
                cmd_str, env=self.picker_item.get_exec_env()
            )
        else:
            python_handlers.safe_code_exec(cmd_str)

    def get_values(self):
        """Return dialog window result values"""
        cmd_str = str(self.cmd_widget.toPlainText())

        return cmd_str, self.apply

    @classmethod
    def get(cls, cmd=None, item=None):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls(cmd=cmd, item=item)
        win.exec_()
        win.raise_()
        return win.get_values()


class CustomMenuEditDialog(CustomScriptEditDialog):
    """Custom python script window for picker item context menu"""

    __TITLE__ = "Custom Menu"

    def __init__(self, parent=None, name=None, cmd=None, item=None):

        self.name = name
        CustomScriptEditDialog.__init__(
            self, parent=parent, cmd=cmd, item=item
        )

    def setup(self):
        """Add name field to default window setup"""
        # Run default setup
        CustomScriptEditDialog.setup(self)

        # Add name line edit
        name_layout = QtWidgets.QHBoxLayout(self)

        label = QtWidgets.QLabel()
        label.setText("Name")
        name_layout.addWidget(label)

        self.name_widget = QtWidgets.QLineEdit()
        if self.name:
            self.name_widget.setText(self.name)
        name_layout.addWidget(self.name_widget)

        self.main_layout.insertLayout(0, name_layout)

    def accept_event(self):
        """Accept button event, check for name"""
        if not self.name_widget.text():
            QtWidgets.QMessageBox.warning(
                self, "Warning", "You need to specify a menu name"
            )
            return

        self.apply = True

        self.accept()
        self.close()

    def get_values(self):
        """Return dialog window result values"""
        name_str = str(self.name_widget.text())
        cmd_str = str(self.cmd_widget.toPlainText())

        return name_str, cmd_str, self.apply

    @classmethod
    def get(cls, name=None, cmd=None, item=None):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls(name=name, cmd=cmd, item=item)
        win.exec_()
        win.raise_()
        return win.get_values()


class SearchAndReplaceDialog(QtWidgets.QDialog):
    """Search and replace dialog window"""

    __SEARCH_STR__ = "_L"
    __REPLACE_STR__ = "_R"

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.apply = False
        self.setup()

    def setup(self):
        """Build/Setup the dialog window"""
        self.setWindowTitle("Search And Replace")

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add line edits
        self.search_widget = QtWidgets.QLineEdit()
        self.search_widget.setText(self.__SEARCH_STR__)
        self.main_layout.addWidget(self.search_widget)

        self.replace_widget = QtWidgets.QLineEdit()
        self.replace_widget.setText(self.__REPLACE_STR__)
        self.main_layout.addWidget(self.replace_widget)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = basic.CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = basic.CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

        ok_btn.setFocus()

    def accept_event(self):
        """Accept button event"""
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        """Cancel button event"""
        self.apply = False
        self.close()

    def get_values(self):
        """Return field values and button choice"""
        search_str = str(self.search_widget.text())
        replace_str = str(self.replace_widget.text())
        if self.apply:
            SearchAndReplaceDialog.__SEARCH_STR__ = search_str
            SearchAndReplaceDialog.__REPLACE_STR__ = replace_str
        return search_str, replace_str, self.apply

    @classmethod
    def get(cls):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls()
        win.exec_()
        win.raise_()
        return win.get_values()


class ItemOptionsWindow(QtWidgets.QMainWindow):
    """Child window to edit shape options"""

    __OBJ_NAME__ = "ctrl_picker_edit_window"
    __TITLE__ = "Picker Item Options"

    #  ----------------------------------------------------------------------
    # constructor
    def __init__(self, parent=None, picker_item=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.picker_item = picker_item

        # undo ----------------------------------------------------------------
        self.main_view = self.picker_item.scene().parent()
        self.tmp_picker_pos_info = {}
        self.tmp_picker_pos_info[picker_item.uuid] = [
            picker_item.x(),
            picker_item.y(),
            picker_item.rotation(),
        ]
        # undo ----------------------------------------------------------------

        # Define size
        self.default_width = 270
        self.default_height = 140

        # Run setup
        self.setup()

        # Other
        self.handles_window = None
        self.event_disabled = False

    def setup(self):
        """Setup window elements"""
        # Main window setting
        self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)
        self.resize(self.default_width, self.default_height)

        # Set size policies
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        # Create main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QHBoxLayout(self.main_widget)

        self.left_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.left_layout)

        self.right_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.right_layout)

        self.control_layout = QtWidgets.QVBoxLayout()
        self.control_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addLayout(self.control_layout)

        self.setCentralWidget(self.main_widget)

        # Add content
        self.add_main_options()
        self.add_position_options()
        self.add_rotation_options()
        self.add_color_options()
        self.add_scale_options()
        self.add_text_options()
        self.add_action_mode_field()
        self.add_target_control_field()
        self.add_custom_menus_field()

        # Add layouts stretch
        self.left_layout.addStretch()

        # Udpate fields
        self._update_shape_infos()
        self._update_position_infos()
        self._update_color_infos()
        self._update_text_infos()
        self._update_ctrls_infos()
        self._update_menus_infos()

    def closeEvent(self, *args, **kwargs):
        """Overwriting close event to close child windows too"""
        # Close child windows
        if self.handles_window:
            try:
                self.handles_window.close()
            except Exception:
                pass

        # undo ----------------------------------------------------------------
        current_position = [
            self.picker_item.x(),
            self.picker_item.y(),
            self.picker_item.rotation(),
        ]

        orig_position = self.tmp_picker_pos_info.get(
            self.picker_item.uuid, None
        )
        if orig_position is not None and orig_position != current_position:
            self.tmp_picker_pos_info[self.picker_item.uuid].extend(
                current_position
            )
            if self.main_view.undo_move_order_index in [-1]:
                self.main_view.undo_move_order.append(
                    copy.deepcopy(self.tmp_picker_pos_info)
                )
            else:
                self.main_view.undo_move_order = self.undo_move_order[
                    : self.main_view.undo_move_order_index
                ]
                self.main_view.undo_move_order.append(
                    copy.deepcopy(self.tmp_picker_pos_info)
                )
            self.undo_move_order_index = -1
            self.tmp_picker_pos_info = {}
        # undo ----------------------------------------------------------------

        QtWidgets.QMainWindow.closeEvent(self, *args, **kwargs)

    def _update_shape_infos(self):
        self.event_disabled = True
        self.handles_cb.setChecked(self.picker_item.get_edit_status())
        self.count_sb.setValue(self.picker_item.point_count)
        self.event_disabled = False

    def _update_position_infos(self):
        self.event_disabled = True
        position = self.picker_item.pos()
        self.pos_x_sb.setValue(position.x())
        self.pos_y_sb.setValue(position.y())
        self.event_disabled = False

    def _update_color_infos(self):
        self.event_disabled = True
        self._set_color_button(self.picker_item.get_color())
        self.alpha_sb.setValue(self.picker_item.get_color().alpha())
        self.event_disabled = False

    def _update_text_infos(self):
        self.event_disabled = True

        # Retrieve et set text field
        text = self.picker_item.get_text()
        if text:
            self.text_field.setText(text)

        # Set text color fields
        self._set_text_color_button(self.picker_item.get_text_color())
        self.text_alpha_sb.setValue(self.picker_item.get_text_color().alpha())
        self.event_disabled = False

    def _update_ctrls_infos(self):
        self._populate_ctrl_list_widget()

    def _update_menus_infos(self):
        self._populate_menu_list_widget()

    def add_main_options(self):
        """Add vertex count option"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Main Properties")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add edit check box
        func = self.handles_cb_event
        self.handles_cb = basic.CallbackCheckBoxWidget(callback=func)
        self.handles_cb.setText("Show handles")

        layout.addWidget(self.handles_cb)

        # Add point count spin box
        spin_layout = QtWidgets.QHBoxLayout()

        spin_label = QtWidgets.QLabel()
        spin_label.setText("Vtx Count")
        spin_layout.addWidget(spin_label)

        point_count = self.picker_item.edit_point_count
        self.count_sb = basic.CallBackSpinBox(
            callback=point_count, value=self.picker_item.point_count
        )
        self.count_sb.setMinimum(2)
        spin_layout.addWidget(self.count_sb)

        layout.addLayout(spin_layout)

        # Add handles position button
        handle_position = self.edit_handles_position_event
        handles_button = basic.CallbackButton(callback=handle_position)
        handles_button.setText("Handles Positions")
        layout.addWidget(handles_button)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_position_options(self):
        """Add position field for precise control positioning"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Position")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Get bary-center
        position = self.picker_item.pos()

        # Add X position spin box
        spin_layout = QtWidgets.QHBoxLayout()

        spin_label = QtWidgets.QLabel()
        spin_label.setText("X")
        spin_layout.addWidget(spin_label)

        edit_pos_event = self.edit_position_event
        self.pos_x_sb = basic.CallBackDoubleSpinBox(
            callback=edit_pos_event, value=position.x(), min=-9999
        )
        spin_layout.addWidget(self.pos_x_sb)

        layout.addLayout(spin_layout)

        # Add Y position spin box
        spin_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel()
        label.setText("Y")
        spin_layout.addWidget(label)

        self.pos_y_sb = basic.CallBackDoubleSpinBox(
            callback=edit_pos_event, value=position.y(), min=-9999
        )
        spin_layout.addWidget(self.pos_y_sb)

        layout.addLayout(spin_layout)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_rotation_options(self):
        """Add rotation group box options"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Rotation")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add alpha spin box
        spin_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(spin_layout)

        label = QtWidgets.QLabel()
        label.setText("Angle")
        spin_layout.addWidget(label)

        self.rotate_sb = QtWidgets.QDoubleSpinBox()
        self.rotate_sb.setValue(15)
        self.rotate_sb.setSingleStep(5)
        spin_layout.addWidget(self.rotate_sb)

        # Add rotate buttons
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        btn = basic.CallbackButton(callback=self.rotate_event, rotMinus=True)
        btn.setText("Rot-")
        btn_layout.addWidget(btn)

        btn = basic.CallbackButton(callback=self.reset_rotate_event)
        btn.setText("Reset")
        btn_layout.addWidget(btn)

        btn = basic.CallbackButton(callback=self.rotate_event, rotPlus=True)
        btn.setText("Rot+")
        btn_layout.addWidget(btn)

        # Add to main left layout
        self.left_layout.addWidget(group_box)

    def _set_color_button(self, color):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.color_button.setPalette(palette)
        self.color_button.setAutoFillBackground(True)

    def _set_text_color_button(self, color):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.text_color_button.setPalette(palette)
        self.text_color_button.setAutoFillBackground(True)

    def add_color_options(self):
        """Add color edition field for polygon"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Color options")

        # Add layout
        layout = QtWidgets.QHBoxLayout(group_box)

        # Add color button
        self.color_button = basic.CallbackButton(
            callback=self.change_color_event
        )

        layout.addWidget(self.color_button)

        # Add alpha spin box
        layout.addStretch()

        label = QtWidgets.QLabel()
        label.setText("Alpha")
        layout.addWidget(label)

        alpha_event = self.change_color_alpha_event
        alpha_value = self.picker_item.get_color().alpha()
        self.alpha_sb = basic.CallBackSpinBox(
            callback=alpha_event, value=alpha_value, max=255
        )
        layout.addWidget(self.alpha_sb)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_text_options(self):
        """Add text option fields"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Text options")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add Caption text field
        self.text_field = basic.CallbackLineEdit(self.set_text_event)
        layout.addWidget(self.text_field)

        # Add size factor spin box
        spin_layout = QtWidgets.QHBoxLayout()

        spin_label = QtWidgets.QLabel()
        spin_label.setText("Size factor")
        spin_layout.addWidget(spin_label)

        text_size = self.picker_item.get_text_size()
        value_sb = basic.CallBackDoubleSpinBox(
            callback=self.edit_text_size_event, value=text_size
        )
        spin_layout.addWidget(value_sb)

        layout.addLayout(spin_layout)

        # Add color layout
        color_layout = QtWidgets.QHBoxLayout(group_box)

        # Add color button
        color_event = self.change_text_color_event
        self.text_color_button = basic.CallbackButton(callback=color_event)

        color_layout.addWidget(self.text_color_button)

        # Add alpha spin box
        color_layout.addStretch()

        label = QtWidgets.QLabel()
        label.setText("Alpha")
        color_layout.addWidget(label)

        alpha_event = self.change_text_alpha_event
        alpha_value = self.picker_item.get_text_color().alpha()
        self.text_alpha_sb = basic.CallBackSpinBox(
            callback=alpha_event, value=alpha_value, max=255
        )
        color_layout.addWidget(self.text_alpha_sb)

        # Add color layout to group box layout
        layout.addLayout(color_layout)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_scale_options(self):
        """Add scale group box options"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Scale")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add edit check box
        self.worldspace_box = QtWidgets.QCheckBox()
        self.worldspace_box.setText("World space")

        layout.addWidget(self.worldspace_box)

        # Add alpha spin box
        spin_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(spin_layout)

        label = QtWidgets.QLabel()
        label.setText("Factor")
        spin_layout.addWidget(label)

        self.scale_sb = QtWidgets.QDoubleSpinBox()
        self.scale_sb.setValue(1.1)
        self.scale_sb.setSingleStep(0.05)
        spin_layout.addWidget(self.scale_sb)

        # Add scale buttons
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        btn = basic.CallbackButton(callback=self.scale_event, x=True)
        btn.setText("X")
        btn_layout.addWidget(btn)

        btn = basic.CallbackButton(callback=self.scale_event, y=True)
        btn.setText("Y")
        btn_layout.addWidget(btn)

        btn = basic.CallbackButton(callback=self.scale_event, x=True, y=True)
        btn.setText("XY")
        btn_layout.addWidget(btn)

        # Add to main left layout
        self.left_layout.addWidget(group_box)

    def add_action_mode_field(self):
        """Add custom action mode field group box"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Action Mode")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add default select mode radio button
        custom_mode = not self.picker_item.get_custom_action_mode()
        default_rad = basic.CallbackRadioButtonWidget(
            "default", self.mode_radio_event, checked=custom_mode
        )
        default_rad.setText("Default action (select)")
        default_rad.setToolTip(
            "Run default selection action on related controls"
        )
        layout.addWidget(default_rad)

        # Add custom action script radio button
        action_mode = self.picker_item.get_custom_action_mode()
        custom_rad = basic.CallbackRadioButtonWidget(
            "custom", self.mode_radio_event, checked=action_mode
        )
        custom_rad.setText("Custom action (script)")
        custom_rad.setToolTip("Change mode to run a custom action script")
        layout.addWidget(custom_rad)

        # Add edit custom script button
        custom_script = self.edit_custom_action_script
        custom_script_btn = basic.CallbackButton(callback=custom_script)
        custom_script_btn.setText("Edit Action script")
        custom_script_btn.setToolTip("Open custom action script edit window")
        layout.addWidget(custom_script_btn)

        self.control_layout.addWidget(group_box)

    def add_target_control_field(self):
        """Add target control association group box"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Control Association")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Init list object
        ctrl_name = self.edit_ctrl_name_event
        self.control_list = basic.CallbackListWidget(callback=ctrl_name)
        self.control_list.setToolTip(
            "Associated controls/objects that will be\
         selected when clicking picker item"
        )
        layout.addWidget(self.control_list)

        # Add buttons
        btn_layout1 = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout1)

        btn = basic.CallbackButton(callback=self.add_selected_controls_event)
        btn.setText("Add Selection")
        btn.setToolTip("Add selected controls to list")
        btn.setMinimumWidth(75)
        btn_layout1.addWidget(btn)

        btn = basic.CallbackButton(callback=self.remove_controls_event)
        btn.setText("Remove")
        btn.setToolTip("Remove selected controls")
        btn.setMinimumWidth(75)
        btn_layout1.addWidget(btn)

        btn = basic.CallbackButton(callback=self.search_replace_controls_event)
        btn.setText("Search & Replace")
        btn.setToolTip("Will search and replace all controls names")
        layout.addWidget(btn)

        self.control_layout.addWidget(group_box)

    def add_custom_menus_field(self):
        """Add custom menu management groupe box"""
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Custom Menus")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Init list object
        self.menus_list = basic.CallbackListWidget(
            callback=self.edit_menu_event
        )
        self.menus_list.setToolTip(
            "Custom action menus that will be accessible through right clicking the picker item in animation mode"
        )
        layout.addWidget(self.menus_list)

        # Add buttons
        btn_layout1 = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout1)

        btn = basic.CallbackButton(callback=self.new_menu_event)
        btn.setText("New")
        btn.setMinimumWidth(60)
        btn_layout1.addWidget(btn)

        btn = basic.CallbackButton(callback=self.remove_menus_event)
        btn.setText("Remove")
        btn.setMinimumWidth(60)
        btn_layout1.addWidget(btn)

        self.right_layout.addWidget(group_box)

    # =========================================================================
    # Events
    def handles_cb_event(self, value=False):
        """Toggle edit mode for shape"""
        self.picker_item.set_edit_status(value)

    def edit_handles_position_event(self):

        # Delete old window
        if self.handles_window:
            try:
                self.handles_window.close()
                self.handles_window.deleteLater()
            except Exception:
                pass

        # Init new window
        picker_item = self.picker_item
        self.handles_window = HandlesPositionWindow(
            parent=self, picker_item=picker_item
        )

        # Show window
        self.handles_window.show()
        self.handles_window.raise_()

    def edit_position_event(self, value=0):
        """Will move polygon based on new values"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        x = self.pos_x_sb.value()
        y = self.pos_y_sb.value()

        self.picker_item.setPos(QtCore.QPointF(x, y))

    def change_color_alpha_event(self, value=255):
        """Will edit the polygon transparency alpha value"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Get current color
        color = self.picker_item.get_color()
        color.setAlpha(value)

        # Update color
        self.picker_item.set_color(color)

    def change_color_event(self):
        """Will edit polygon color based on new values"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Open color picker dialog
        picker_color = self.picker_item.get_color()
        color = QtWidgets.QColorDialog.getColor(
            initial=picker_color, parent=self
        )

        # Abort on invalid color (cancel button)
        if not color.isValid():
            return

        # Update button color
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.color_button.setPalette(palette)

        # Edit new color alpha
        alpha = self.picker_item.get_color().alpha()
        color.setAlpha(alpha)

        # Update color
        self.picker_item.set_color(color)

    def rotate_event(self, rotMinus=None, rotPlus=None):
        """Will rotate polygon based on angle value from spin box"""
        # Get rotate angle value
        rotate_angle = self.rotate_sb.value()

        # Build kwargs
        kwargs = {"angle": 0.0}
        if rotMinus:
            kwargs["angle"] = rotate_angle
        if rotPlus:
            kwargs["angle"] = rotate_angle * -1

        # Apply rotation
        self.picker_item.rotate_shape(**kwargs)

    def reset_rotate_event(self):
        self.picker_item.reset_rotation()

    def scale_event(self, x=False, y=False):
        """Will scale polygon on specified axis based on scale factor
        value from spin box
        """
        # Get scale factor value
        scale_factor = self.scale_sb.value()

        # Build kwargs
        kwargs = {"x": 1.0, "y": 1.0}
        if x:
            kwargs["x"] = scale_factor
        if y:
            kwargs["y"] = scale_factor

        # Check space
        if self.worldspace_box.isChecked():
            kwargs["world"] = True

        # Apply scale
        self.picker_item.scale_shape(**kwargs)

    def set_text_event(self, text=None):
        """Will set polygon text to field"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        text = str(text)
        self.picker_item.set_text(text)

    def edit_text_size_event(self, value=1):
        """Will edit text size factor"""
        self.picker_item.set_text_size(value)

    def change_text_alpha_event(self, value=255):
        """Will edit the polygon transparency alpha value"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Get current color
        color = self.picker_item.get_text_color()
        color.setAlpha(value)

        # Update color
        self.picker_item.set_text_color(color)

    def change_text_color_event(self):
        """Will edit polygon color based on new values"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Open color picker dialog
        picker_color = self.picker_item.get_text_color()
        color = QtWidgets.QColorDialog.getColor(
            initial=picker_color, parent=self
        )

        # Abort on invalid color (cancel button)
        if not color.isValid():
            return

        # Update button color
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.text_color_button.setPalette(palette)

        # Edit new color alpha
        alpha = self.picker_item.get_text_color().alpha()
        color.setAlpha(alpha)

        # Update color
        self.picker_item.set_text_color(color)

    # =========================================================================
    # Custom action management
    def mode_radio_event(self, mode):
        """Action mode change event"""
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        if mode == "default":
            self.picker_item.custom_action = False

        elif mode == "custom":
            self.picker_item.custom_action = True

    def edit_custom_action_script(self):

        # Open input window
        action_script = self.picker_item.custom_action_script
        cmd, ok = CustomScriptEditDialog.get(
            cmd=action_script, item=self.picker_item
        )
        if not (ok and cmd):
            return

        self.picker_item.set_custom_action_script(cmd)

    # =========================================================================
    # Control management
    def _populate_ctrl_list_widget(self):
        """Will update/populate list with current shape ctrls"""
        # Empty list
        self.control_list.clear()

        # Populate node list
        controls = self.picker_item.get_controls()
        for i in range(len(controls)):
            item = basic.CtrlListWidgetItem(index=i)
            item.setText(controls[i])
            self.control_list.addItem(item)

    # if controls:
    # self.control_list.setCurrentRow(0)

    def edit_ctrl_name_event(self, item=None):
        """Double click event on associated ctrls list"""
        if not item:
            return

        # Open input window
        line_normal = QtWidgets.QLineEdit.Normal
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Ctrl name",
            "New name",
            mode=line_normal,
            text=str(item.text()),
        )
        if not (ok and name):
            return

        # Update influence name
        new_name = item.setText(name)
        if new_name:
            self.update_shape_controls_list()

        # Deselect item
        self.control_list.clearSelection()

    def add_selected_controls_event(self):
        """Will add maya selected object to control list"""
        self.picker_item.add_selected_controls()

        # Update display
        self._populate_ctrl_list_widget()

    def remove_controls_event(self):
        """Will remove selected item list from stored controls"""
        # Get selected item
        items = self.control_list.selectedItems()
        assert items, "no list item selected"

        # Remove item from list
        for item in items:
            self.picker_item.remove_control(item.node())

        # Update display
        self._populate_ctrl_list_widget()

    def search_replace_controls_event(self):
        """Will search and replace controls names for related picker item"""
        if self.picker_item.search_and_replace_controls():
            self._populate_ctrl_list_widget()

    def get_controls_from_list(self):
        """Return the controls from list widget"""
        ctrls = []
        for i in range(self.control_list.count()):
            item = self.control_list.item(i)
            ctrls.append(item.node())
        return ctrls

    def update_shape_controls_list(self):
        """Update shape stored control list"""
        ctrls = self.get_controls_from_list()
        self.picker_item.set_control_list(ctrls)

    # =========================================================================
    # Menus management
    def _add_menu_item(self, text=None):
        """Add a menu item to menu list widget"""
        item = QtWidgets.QListWidgetItem()
        item.index = self.menus_list.count()
        if text:
            item.setText(text)
        self.menus_list.addItem(item)
        return item

    def _populate_menu_list_widget(self):
        """Populate list widget with menu data"""
        # Empty list
        self.menus_list.clear()

        # Populate node list
        menus_data = self.picker_item.get_custom_menus()
        for i in range(len(menus_data)):
            self._add_menu_item(text=menus_data[i][0])

    def _update_menu_data(self, index, name, cmd):
        """Update custom menu data"""
        menu_data = self.picker_item.get_custom_menus()
        if index > len(menu_data) - 1:
            menu_data.append([name, cmd])
        else:
            menu_data[index] = [name, cmd]
        self.picker_item.set_custom_menus(menu_data)

    def edit_menu_event(self, item=None):
        """Double click event on associated menu list"""
        if not item:
            return

        name, cmd = self.picker_item.get_custom_menus()[item.index]

        # Open input window
        name, cmd, ok = CustomMenuEditDialog.get(
            name=name, cmd=cmd, item=self.picker_item
        )
        if not (ok and name and cmd):
            return

        # Update menu display name
        item.setText(name)

        # Update menu data
        self._update_menu_data(item.index, name, cmd)

        # Deselect item
        self.menus_list.clearSelection()

    def new_menu_event(self):
        """Add new custom menu btn event"""
        # Open input window
        name, cmd, ok = CustomMenuEditDialog.get(item=self.picker_item)
        if not (ok and name and cmd):
            return

        # Update menu display name
        item = self._add_menu_item(text=name)

        # Update menu data
        self._update_menu_data(item.index, name, cmd)

    def remove_menus_event(self):
        """Remove custom menu btn event"""
        # Get selected item
        items = self.menus_list.selectedItems()
        assert items, "no list item selected"

        # Remove item from list
        menu_data = self.picker_item.get_custom_menus()
        for i in range(len(items)):
            menu_data.pop(items[i].index - i)
        self.picker_item.set_custom_menus(menu_data)

        # Update display
        self._populate_menu_list_widget()


class HandlesPositionWindow(QtWidgets.QMainWindow):
    """Whild window to edit picker item handles local positions"""

    __OBJ_NAME__ = "picker_item_handles_window"
    __TITLE__ = "Handles positions"

    __DEFAULT_WIDTH__ = 250
    __DEFAULT_HEIGHT__ = 300

    def __init__(self, parent=None, picker_item=None):
        QtWidgets.QMainWindow.__init__(self, parent=None)

        self.picker_item = picker_item

        # Run setup
        self.setup()

    def setup(self):
        """Setup window elements"""
        # Main window setting
        self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)
        self.resize(self.__DEFAULT_WIDTH__, self.__DEFAULT_HEIGHT__)

        # Create main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        self.setCentralWidget(self.main_widget)

        # Add content
        self.add_position_table()
        self.add_option_buttons()

        # Populate table
        self.populate_table()

    def add_position_table(self):
        self.table = QtWidgets.QTableWidget(self)

        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["X", "Y"])

        self.main_layout.addWidget(self.table)

    def add_option_buttons(self):
        """Add window option buttons"""
        # Refresh button
        self.refresh_button = basic.CallbackButton(callback=self.refresh_event)
        self.refresh_button.setText("Refresh")
        self.main_layout.addWidget(self.refresh_button)

    def refresh_event(self):
        """Refresh table event"""
        self.populate_table()

    def populate_table(self):
        """Populate table with X/Y handles position items"""
        # Clear table
        while self.table.rowCount():
            self.table.removeRow(0)

        # Abort if no pickeritem specified
        if not self.picker_item:
            return

        # Parse handles
        handles = self.picker_item.get_handles()
        for i in range(len(handles)):
            self.table.insertRow(i)
            spin_box = basic.CallBackDoubleSpinBox(
                callback=handles[i].setX, value=handles[i].x(), min=-999
            )
            self.table.setCellWidget(i, 0, spin_box)

            spin_box = basic.CallBackDoubleSpinBox(
                callback=handles[i].setY, value=handles[i].y(), min=-999
            )
            self.table.setCellWidget(i, 1, spin_box)

    def display_handles_index(self, status=True):
        """Display related picker handles index"""
        for handle in self.picker_item.get_handles():
            handle.enable_index_draw(status)

    def closeEvent(self, *args, **kwargs):
        self.display_handles_index(status=False)
        return QtWidgets.QMainWindow.closeEvent(self, *args, **kwargs)

    def show(self, *args, **kwargs):
        """Override default show function to display related picker
        handles index
        """
        self.display_handles_index(status=True)
        return QtWidgets.QMainWindow.show(self, *args, **kwargs)


class DefaultPolygon(QtWidgets.QGraphicsObject):
    """Default polygon class, with move and hover support"""

    __DEFAULT_COLOR__ = QtGui.QColor(0, 0, 0, 255)

    def __init__(self, parent=None):
        QtWidgets.QGraphicsObject.__init__(self, parent=parent)

        if parent:
            self.setParent(parent)

        # Hover feedback
        self.setAcceptHoverEvents(True)
        self._hovered = False

        # Init default
        self.color = self.__DEFAULT_COLOR__

    def hoverEnterEvent(self, event=None):
        """Lightens background color on mose over"""
        QtWidgets.QGraphicsObject.hoverEnterEvent(self, event)
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event=None):
        """Resets mouse over background color"""
        QtWidgets.QGraphicsObject.hoverLeaveEvent(self, event)
        self._hovered = False
        self.update()

    def boundingRect(self):
        """
        Needed override:
        Returns the bounding rectangle for the graphic item
        """
        return self.shape().boundingRect()

    def itemChange(self, change, value):
        """itemChange update behavior"""
        # Catch position update
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            # Force scene update to prevent "ghosts"
            # (ghost happen when the previous polygon is out of
            # the new bounding rect when updating)
            if self.scene():
                self.scene().update()

        # Run default action
        return QtWidgets.QGraphicsObject.itemChange(self, change, value)

    def get_color(self):
        """Get polygon color"""
        return QtGui.QColor(self.color)

    def set_color(self, color=None):
        """Set polygon color"""
        if not color:
            color = QtGui.QColor(0, 0, 0, 255)
        elif isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)

        msg = "input color '{}' is invalid".format(color)
        assert isinstance(color, QtGui.QColor), msg

        self.color = color
        self.update()

        return color


class PointHandle(DefaultPolygon):
    """Handle polygon object to move picker polygon cvs"""

    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 200)

    def __init__(self, x=0, y=0, size=8, color=None, parent=None, index=0):

        DefaultPolygon.__init__(self, parent)

        # Make movable
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        # Set values
        self.setPos(x, y)
        self.index = index
        self.size = size
        self.set_color()
        self.draw_index = False

        # Hide by default
        self.setVisible(False)

        # Add index element
        self.index = PointHandleIndex(parent=self, index=index)

    # =========================================================================
    # Default python methods
    # =========================================================================
    def _new_pos_handle_copy(self, pos):
        """Return a new PointHandle isntance with same attributes
        but different position
        """
        new_handle = PointHandle(
            x=pos.x(),
            y=pos.y(),
            size=self.size,
            color=self.color,
            parent=self.parentObject(),
        )
        return new_handle

    def _get_pos_for_input(self, other):
        if isinstance(other, PointHandle):
            return other.pos()
        return other

    def __add__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() + other
        return self._new_pos_handle_copy(new_pos)

    def __sub__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() - other
        return self._new_pos_handle_copy(new_pos)

    def __div__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() / other
        return self._new_pos_handle_copy(new_pos)

    def __mul__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() / other
        return self._new_pos_handle_copy(new_pos)

    # =========================================================================
    # QT OVERRIDES
    # =========================================================================
    def setX(self, value=0):
        """Override to support keyword argument for spin_box callback"""
        DefaultPolygon.setX(self, value)

    def setY(self, value=0):
        """Override to support keyword argument for spin_box callback"""
        DefaultPolygon.setY(self, value)

    # =========================================================================
    # Graphic item methods
    # =========================================================================
    def shape(self):
        """Return default handle square shape based on specified size"""
        path = QtGui.QPainterPath()
        # TODO some ints are being set to negative, make sure it survived the
        # pep8
        rectangle = QtCore.QRectF(
            QtCore.QPointF(-self.size / 2.0, self.size / 2.0),
            QtCore.QPointF(self.size / 2.0, -self.size / 2.0),
        )
        # path.addRect(rectangle)
        path.addEllipse(rectangle)
        return path

    def paint(self, painter, options, widget=None):
        """Paint graphic item"""
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Get polygon path
        path = self.shape()

        # Set node background color
        brush = QtGui.QBrush(self.color)
        if self._hovered:
            brush = QtGui.QBrush(self.color.lighter(500))

        # Paint background
        painter.fillPath(path, brush)

        border_pen = QtGui.QPen(QtGui.QColor(200, 200, 200, 255))
        painter.setPen(border_pen)

        # Paint Borders
        painter.drawPath(path)

        # if not edit_mode: return
        # Paint center cross
        cross_size = self.size / 2 - 2
        painter.setPen(QtGui.QColor(0, 0, 0, 180))
        painter.drawLine(-cross_size, 0, cross_size, 0)
        painter.drawLine(0, cross_size, 0, -cross_size)

    def mirror_x_position(self):
        """will mirror local x position value"""
        self.setX(-1 * self.x())

    def scale_pos(self, x=1.0, y=1.0):
        """Scale handle local position"""
        self.setPos(self.pos().x() * x, self.pos().y() * y)
        self.update()

    def enable_index_draw(self, status=False):
        self.index.setVisible(status)

    def set_index(self, index):
        self.index.setText(index)

    def get_index(self):
        return int(self.index.text())


class Polygon(DefaultPolygon):
    """
    Picker controls visual graphic object
    (inherits from QtWidgets.QGraphicsObject rather
    than QtWidgets.QGraphicsItem for signal support)
    """

    __DEFAULT_COLOR__ = QtGui.QColor(200, 200, 200, 180)
    __DEFAULT_SELECT_COLOR__ = QtGui.QColor(230, 230, 230, 240)

    def __init__(self, parent=None, points=[], color=None):

        DefaultPolygon.__init__(self, parent=parent)
        self.points = points
        self.set_color(Polygon.__DEFAULT_COLOR__)

        self._edit_status = False
        self.selected = False

    def set_edit_status(self, status=False):
        self._edit_status = status
        self.update()

    def shape(self):
        """Override function to return proper "hit box",
        and compute shape only once.
        """
        path = QtGui.QPainterPath()

        # Polygon case
        if len(self.points) > 2:
            # Define polygon points for closed loop
            shp_points = []
            for handle in self.points:
                shp_points.append(handle.pos())
            shp_points.append(self.points[0].pos())

            # Draw polygon
            polygon = QtGui.QPolygonF(shp_points)

            # Update path
            path.addPolygon(polygon)

        # Circle case
        else:
            center = self.points[0].pos()
            radius = QtGui.QVector2D(
                self.points[0].pos() - self.points[1].pos()
            ).length()

            # Update path
            path.addEllipse(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
            )

        return path

    def paint(self, painter, options, widget=None):
        """Paint graphic item"""
        # Set render quality
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Get polygon path
        path = self.shape()

        # Background color
        color = QtGui.QColor(self.color)
        if self._hovered:
            color = color.lighter(130)
        brush = QtGui.QBrush(color)

        painter.fillPath(path, brush)

        # Add white layer color overlay on selected state
        if self.selected:
            color = QtGui.QColor(255, 255, 255, 50)
            brush = QtGui.QBrush(color)
            painter.fillPath(path, brush)

        # Border status feedback
        border_pen = QtGui.QPen(self.__DEFAULT_SELECT_COLOR__)
        border_pen.setWidthF(2)

        if self.selected:
            painter.setPen(border_pen)
            painter.drawPath(path)

        elif self._hovered:
            border_pen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(border_pen)
            painter.drawPath(path)

        # Stop her if not in edit mode
        if not self._edit_status:
            return

        # Paint center cross
        painter.setRenderHints(QtGui.QPainter.Antialiasing, False)
        painter.setPen(QtGui.QColor(0, 0, 0, 180))
        painter.drawLine(-5, 0, 5, 0)
        painter.drawLine(0, 5, 0, -5)

    def set_selected_state(self, state):
        """Will set border color feedback based on selection state"""
        # Do nothing on same state
        if state == self.selected:
            return

        # Change state, and update
        self.selected = state
        self.update()

    def set_color(self, color):
        # Run default method
        color = DefaultPolygon.set_color(self, color)

        # Store new color as default
        Polygon.__DEFAULT_COLOR__ = color


class PointHandleIndex(QtWidgets.QGraphicsSimpleTextItem):
    """Point handle index text element"""

    __DEFAULT_COLOR__ = QtGui.QColor(130, 50, 50, 255)

    def __init__(self, parent=None, scene=None, index=0):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Init defaults
        self.set_size()
        self.set_color(PointHandleIndex.__DEFAULT_COLOR__)
        self.setPos(QtCore.QPointF(-9, -14))
        self.setFlag(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)

        # Hide by default
        self.setVisible(False)

        self.setText(index)

    def set_size(self, value=8.0):
        """Set pointSizeF for text"""
        font = self.font()
        font.setPointSizeF(value)
        self.setFont(font)

    def set_color(self, color=None):
        """Set text color"""
        if not color:
            return
        brush = self.brush()
        brush.setColor(color)
        self.setBrush(brush)

    def setText(self, text):
        """Override default setText method to force unicode on int index input"""
        return QtWidgets.QGraphicsSimpleTextItem.setText(self, str(text))


class GraphicText(QtWidgets.QGraphicsSimpleTextItem):
    """Picker item text element"""

    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 255)

    def __init__(self, parent=None, scene=None):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Counter view scale
        self.scale_transform = QtGui.QTransform().scale(1, -1)
        self.setTransform(self.scale_transform)

        # Init default size
        self.set_size()
        self.set_color(GraphicText.__DEFAULT_COLOR__)

    def set_text(self, text):
        """
        Set current text
        (Will center text on parent too)
        """
        self.setText(text)
        self.center_on_parent()

    def get_text(self):
        """Return element text"""
        return str(self.text())

    def set_size(self, value=10.0):
        """Set pointSizeF for text"""
        font = self.font()
        font.setPointSizeF(value)
        self.setFont(font)
        self.center_on_parent()

    def get_size(self):
        """Return text pointSizeF"""
        return self.font().pointSizeF()

    def get_color(self):
        """Return text color"""
        return self.brush().color()

    def set_color(self, color=None):
        """Set text color"""
        if not color:
            return
        brush = self.brush()
        brush.setColor(color)
        self.setBrush(brush)

        # Store new color as default color
        GraphicText.__DEFAULT_COLOR__ = color

    def center_on_parent(self):
        """
        Center text on parent item
        (Since by default the text start on the bottom left corner)
        """
        center_pos = self.boundingRect().center()
        # self.setPos(-center_pos * self.scale_transform)
        scale_xy = QtCore.QPointF(center_pos.x(), center_pos.y() * -1)
        self.setPos(-scale_xy)


class PickerItem(DefaultPolygon):
    """Main picker graphic item container"""

    def __init__(
        self, parent=None, point_count=4, namespace=None, main_window=None
    ):
        DefaultPolygon.__init__(self, parent=parent)
        self.point_count = point_count

        self.setPos(25, 30)

        # Make item movable
        if __EDIT_MODE__.get():
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
            self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)

        # Default vars
        self.namespace = namespace
        self.main_window = main_window
        self._edit_status = False
        self.edit_window = None

        # Add polygon
        self.polygon = Polygon(parent=self)

        # Add text
        self.text = GraphicText(parent=self)

        # Add handles
        self.handles = []
        self.set_handles(self.get_default_handles())

        # Controls vars
        self.controls = []
        self.custom_menus = []

        # Custom action
        self.custom_action = False
        self.custom_action_script = None

        # uuid & undo
        self.uuid = uuid.uuid4()

    def shape(self):
        path = QtGui.QPainterPath()

        if self.polygon:
            path.addPath(self.polygon.shape())

        # Stop here in default mode
        if not self._edit_status:
            return path

        # Add handles to shape
        for handle in self.handles:
            path.addPath(handle.mapToParent(handle.shape()))

        return path

    def paint(self, painter, *args, **kwargs):
        pass
        # for debug only
        # # Set render quality
        # painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # # Get polygon path
        # path = self.shape()

        # # Set node background color
        # brush = QtGui.QBrush(QtGui.QColor(0,0,200,255))

        # # Paint background
        # painter.fillPath(path, brush)

        # border_pen = QtGui.QPen(QtGui.QColor(0,200,0,255))
        # painter.setPen(border_pen)

        # # Paint Borders
        # painter.drawPath(path)

    def get_default_handles(self):
        """
        Generate default point handles coordinate for polygon
        (on circle)
        """
        unit_scale = 20
        handles = []

        # Circle case
        if self.point_count == 2:
            handle_a = PointHandle(x=0.0, y=0.0, parent=self, index=1)
            handle_b = PointHandle(
                x=1.0 * unit_scale, y=0.0, parent=self, index=2
            )
            handles = [handle_a, handle_b]

        else:
            # Define angle step
            angle_step = pi * 2 / self.point_count

            # Generate point coordinates
            for i in range(0, self.point_count):
                x = sin(i * angle_step + pi / self.point_count) * unit_scale
                y = cos(i * angle_step + pi / self.point_count) * unit_scale
                handle = PointHandle(x=x, y=y, parent=self, index=i + 1)
                handles.append(handle)

        return handles

    def edit_point_count(self, value=4):
        """
        Change/edit the number of points for the polygon
        (that will reset the shape)
        """
        # Update point count
        self.point_count = value

        # Reset points
        points = self.get_default_handles()
        self.set_handles(points)

    def get_handles(self):
        """Return picker item handles"""
        return self.handles

    def set_handles(self, handles=[]):
        """Set polygon handles points"""
        # Remove existing handles
        for handle in self.handles:
            handle.setParent(None)
            handle.deleteLater()

        # Parse input type
        new_handles = []
        # start index at 1 since table Widget raw are indexed at 1
        index = 1

        for handle in handles:
            if isinstance(handle, (list, tuple)):
                handle = PointHandle(
                    x=handle[0], y=handle[1], parent=self, index=index
                )
            elif hasattr(handle, "x") and hasattr(handle, "y"):
                handle = PointHandle(
                    x=handle.x(), y=handle.y(), parent=self, index=index
                )
            new_handles.append(handle)
            index += 1

        # Update handles list
        self.handles = new_handles
        self.polygon.points = new_handles

        # Set current visibility status
        for handle in self.handles:
            handle.setVisible(self.get_edit_status())

        # Set new point count
        self.point_count = len(self.handles)

    # =========================================================================
    # Mouse events ---
    def hoverEnterEvent(self, event=None):
        """Update tooltip on hoover with associated controls in edit mode"""
        if __EDIT_MODE__.get():
            text = "\n".join(self.get_controls())
            self.setToolTip(text)
        super(PickerItem, self).hoverEnterEvent(event)

    def mouseMoveEvent_offset(self, event):
        self.setPos(event.scenePos() + self.cursor_delta)

    def mouseMoveEvent(self, event):
        gfx_event = event
        if event.buttons() == QtCore.Qt.LeftButton and __EDIT_MODE__.get():
            if self.currently_selected:
                [
                    item.mouseMoveEvent_offset(event)
                    for item in self.currently_selected
                ]
        super(PickerItem, self).mouseMoveEvent(gfx_event)

    def mousePressEvent(self, event):
        """Event called on mouse press"""
        # Simply run default event in edit mode, and exit
        if __EDIT_MODE__.get():
            self.get_delta_from_point(event.pos())
            # this allows for maintaining offset while dragging multiple
            self.currently_selected = [
                item
                for item in self.parent().get_picker_items()
                if item.polygon.selected
            ]
            if self.currently_selected:
                if self in self.currently_selected:
                    self.currently_selected.remove(self)
                [
                    item.get_delta_from_point(event.scenePos())
                    for item in self.currently_selected
                ]
            return DefaultPolygon.mousePressEvent(self, event)

        # Run selection on left mouse button event
        if event.buttons() == QtCore.Qt.LeftButton:
            # Run custom script action
            if self.get_custom_action_mode():
                self.mouse_press_custom_action(event)
            # Run default selection action
            else:
                select_picker_controls([self], event, modifiers=None)

        # Set focus to maya window
        maya_window = pyqt.maya_main_window()
        if maya_window:
            maya_window.setFocus()

    def mouse_press_select_event(self, event, modifiers=None):
        """
        Default select event on mouse press.
        Will select associated controls
        """
        # Get keyboard modifier
        # Simply run default event in edit mode, and exit
        if __EDIT_MODE__.get():
            return
        if modifiers:
            modifiers = modifiers
        else:
            modifiers = event.modifiers()
        modifier = None

        # Shift cases (toggle)
        if modifiers == QtCore.Qt.ShiftModifier:
            modifier = "shift"

        # Controls case
        if modifiers == QtCore.Qt.ControlModifier:
            modifier = "control"

        # Alt case (remove)
        if modifiers == QtCore.Qt.AltModifier:
            modifier = "alt"

        # Call action
        self.select_associated_controls(modifier=modifier)

    def mouse_press_custom_action(self, event):
        """Custom script action on mouse press"""
        # Run custom action script with picker item environnement
        python_handlers.safe_code_exec(
            self.get_custom_action_script(), env=self.get_exec_env()
        )

    def mouseDoubleClickEvent(self, event):
        """Event called when mouse is double clicked"""
        if not __EDIT_MODE__.get():
            return

        self.edit_options()

    def contextMenuEvent(self, event):
        """Right click menu options"""
        # Context menu for edition mode
        if __EDIT_MODE__.get():
            self.edit_context_menu(event)

        # Context menu for default mode
        else:
            self.default_context_menu(event)

        # Force call release method
        # self.mouseReleaseEvent(event)
        return True

    def edit_context_menu(self, event):
        """Context menu (right click) in edition mode"""
        # Init context menu
        menu = QtWidgets.QMenu(self.parent())

        # Build edit context menu
        options_action = QtWidgets.QAction("Options", None)
        options_action.triggered.connect(self.edit_options)
        menu.addAction(options_action)

        handles_action = QtWidgets.QAction("Toggle handles", None)
        handles_action.triggered.connect(self.toggle_edit_status)
        menu.addAction(handles_action)

        menu.addSeparator()

        # Shape options menu
        shape_menu = QtWidgets.QMenu(menu)
        shape_menu.setTitle("Shape")

        move_action = QtWidgets.QAction("Move to center", None)
        move_action.triggered.connect(self.move_to_center)
        shape_menu.addAction(move_action)

        shp_mirror_action = QtWidgets.QAction("Mirror shape", None)
        shp_mirror_action.triggered.connect(self.mirror_shape)
        shape_menu.addAction(shp_mirror_action)

        color_mirror_action = QtWidgets.QAction("Mirror color", None)
        color_mirror_action.triggered.connect(self.mirror_color)
        shape_menu.addAction(color_mirror_action)

        menu.addMenu(shape_menu)

        move_back_action = QtWidgets.QAction("Move to back", None)
        move_back_action.triggered.connect(self.move_to_back)
        menu.addAction(move_back_action)

        move_front_action = QtWidgets.QAction("Move to front", None)
        move_front_action.triggered.connect(self.move_to_front)
        menu.addAction(move_front_action)

        menu.addSeparator()

        # Copy handling
        copy_action = QtWidgets.QAction("Copy", None)
        copy_action.triggered.connect(self.copy_event)
        menu.addAction(copy_action)

        paste_action = QtWidgets.QAction("Paste", None)
        if DataCopyDialog.__DATA__:
            paste_action.triggered.connect(self.past_event)
        else:
            paste_action.setEnabled(False)
        menu.addAction(paste_action)

        paste_options_action = QtWidgets.QAction("Paste Options", None)
        if DataCopyDialog.__DATA__:
            paste_options_action.triggered.connect(self.past_option_event)
        else:
            paste_options_action.setEnabled(False)
        menu.addAction(paste_options_action)

        menu.addSeparator()

        # Paste position actions
        paste_x_action = QtWidgets.QAction("Paste Pos X", None)
        if DataCopyDialog.__DATA__:
            paste_x_action.triggered.connect(self.past_x_event)
        else:
            paste_x_action.setEnabled(False)
        menu.addAction(paste_x_action)

        paste_y_action = QtWidgets.QAction("Paste Pos Y", None)
        if DataCopyDialog.__DATA__:
            paste_y_action.triggered.connect(self.past_y_event)
        else:
            paste_y_action.setEnabled(False)
        menu.addAction(paste_y_action)

        menu.addSeparator()

        # Duplicate options
        duplicate_action = QtWidgets.QAction("Duplicate", None)
        duplicate_action.triggered.connect(self.duplicate_selected)
        menu.addAction(duplicate_action)

        mirror_dup_action = QtWidgets.QAction("Duplicate/mirror", None)
        mirror_dup_action.triggered.connect(self.duplicate_and_mirror_selected)
        menu.addAction(mirror_dup_action)

        menu.addSeparator()

        # Delete
        remove_action = QtWidgets.QAction("Remove", None)
        remove_action.triggered.connect(self.remove_selected)
        menu.addAction(remove_action)

        menu.addSeparator()

        # Control association
        ctrls_menu = QtWidgets.QMenu(menu)
        ctrls_menu.setTitle("Ctrls Association")

        select_action = QtWidgets.QAction("Select", None)
        select_action.triggered.connect(self.select_associated_controls)
        ctrls_menu.addAction(select_action)

        select_all_action = QtWidgets.QAction("Select all", None)
        select_all_action.triggered.connect(
            self.select_all_associated_controls
        )
        ctrls_menu.addAction(select_all_action)

        replace_action = QtWidgets.QAction("Replace with selection", None)
        replace_action.triggered.connect(self.replace_controls_selection)
        ctrls_menu.addAction(replace_action)

        menu.addMenu(ctrls_menu)

        # Open context menu under mouse
        # offset position to prevent accidental mouse release on menu
        # OFFSET
        offseted_pos = event.pos() + QtCore.QPoint(5, 0)
        menu.exec_(offseted_pos)
        return True

    def default_context_menu(self, event):
        """Context menu (right click) out of edition mode (animation)"""
        # Init context menu
        menu = QtWidgets.QMenu(self.parent())

        # Add reset action
        # reset_action = QtWidgets.QAction("Reset", None)
        # reset_action.triggered.connect(self.active_control.reset_to_bind_pose)
        # menu.addAction(reset_action)

        # Add custom actions
        actions = self._get_custom_action_menus()
        for action in actions:
            menu.addAction(action)

        # Abort on empty menu
        if menu.isEmpty():
            return

        # Open context menu under mouse
        # offset position to prevent accidental mouse release on menu
        offseted_pos = event.pos() + QtCore.QPoint(5, 0)
        # scene_pos = self.mapToScene(offseted_pos)
        # view_pos = self.parent().mapFromScene(scene_pos)
        # screen_pos = self.parent().mapToGlobal(view_pos)
        menu.exec_(offseted_pos)

    def get_init_env(self):
        env = self.get_exec_env()
        env["__INIT__"] = True

        return env

    def get_exec_env(self):
        """
        Will return proper environnement dictionnary for eval execs
        (Will provide related controls as __CONTROLS__
        and __NAMESPACE__ variables)
        """
        # Init env
        env = {}

        # Add controls vars
        env["__CONTROLS__"] = self.get_controls()
        ctrls = self.get_controls()
        env["__FLATCONTROLS__"] = maya_handlers.get_flattened_nodes(ctrls)
        env["__NAMESPACE__"] = self.get_namespace()
        env["__SELF__"] = self
        env["__INIT__"] = False

        return env

    def _get_custom_action_menus(self):
        # Init action list to fix loop problem where qmenu only
        # show last action when using the same variable name ...
        actions = []

        # Define custom exec cmd wrapper
        def wrapper(cmd):
            def custom_eval(*args, **kwargs):
                python_handlers.safe_code_exec(cmd, env=self.get_exec_env())

            return custom_eval

        # Get active controls custom menus
        custom_data = self.get_custom_menus()
        if not custom_data:
            return actions

        # Build menu
        for i in range(len(custom_data)):
            actions.append(QtWidgets.QAction(custom_data[i][0], None))
            actions[i].triggered.connect(wrapper(custom_data[i][1]))

        return actions

    # =========================================================================
    # Edit picker item options ---
    def edit_options(self):
        """Open Edit options window"""
        # Delete old window
        if self.edit_window:
            try:
                self.edit_window.close()
                self.edit_window.deleteLater()
            except Exception:
                pass

        # Init new window
        self.edit_window = ItemOptionsWindow(
            parent=self.main_window, picker_item=self
        )

        # Show window
        self.edit_window.show()
        self.edit_window.raise_()

    def set_edit_status(self, status):
        """Set picker item edit status (handle visibility etc.)"""
        self._edit_status = status

        for handle in self.handles:
            handle.setVisible(status)

        self.polygon.set_edit_status(status)

    def get_edit_status(self):
        return self._edit_status

    def toggle_edit_status(self):
        """Will toggle handle visibility status"""
        self.set_edit_status(not self._edit_status)

    # =========================================================================
    # Properties methods ---
    def get_color(self):
        """Get polygon color"""
        return self.polygon.get_color()

    def set_color(self, color=None):
        """Set polygon color"""
        self.polygon.set_color(color)

    # =========================================================================
    # Text handling ---
    def get_text(self):
        return self.text.get_text()

    def set_text(self, text):
        self.text.set_text(text)

    def get_text_color(self):
        return self.text.get_color()

    def set_text_color(self, color):
        self.text.set_color(color)

    def get_text_size(self):
        return self.text.get_size()

    def set_text_size(self, size):
        self.text.set_size(size)

    # =========================================================================
    # Scene Placement ---
    def move_to_front(self):
        """Move picker item to scene front"""
        # Get current scene
        scene = self.scene()

        # Move to temp scene
        tmp_scene = QtWidgets.QGraphicsScene()
        tmp_scene.addItem(self)

        # Add to current scene (will be put on top)
        scene.addItem(self)

        # Clean
        tmp_scene.deleteLater()

    def move_to_back(self):
        """Move picker item to background level behind other items"""
        # Get picker Items
        picker_items = self.scene().get_picker_items()

        # Reverse list since items are returned front to back
        picker_items.reverse()

        # Move current item to front of list (back)
        picker_items.remove(self)
        picker_items.insert(0, self)

        # Move each item in proper oder to front of scene
        # That will add them in the proper order to the scene
        for item in picker_items:
            item.move_to_front()

    def move_to_center(self):
        """Move picker item to pos 0,0"""
        self.setPos(0, 0)

    def remove_selected(self):
        selected_pickers = self.scene().get_selected_items()
        if self not in selected_pickers:
            selected_pickers.append(self)
        [picker.remove() for picker in selected_pickers]

    def remove(self):
        self.scene().removeItem(self)
        self.setParent(None)
        self.deleteLater()

    def get_delta_from_point(self, point):
        self.cursor_delta = self.pos() - point
        return self.cursor_delta

    # =========================================================================
    # Ducplicate and mirror methods ---
    def mirror_position(self):
        """Mirror picker position (on X axis)"""
        self.setX(-1 * self.pos().x())

    def mirror_rotation(self, angle=None):
        """Mirror picker rotation angle"""
        if not angle:
            angle = self.rotation()

        if angle > 360:
            angle = angle - 360

        mirror_angle = abs(angle - 360)

        self.setRotation(mirror_angle)
        self.update()

    def mirror_shape(self):
        """Will mirror polygon handles position on X axis"""
        for handle in self.handles:
            handle.mirror_x_position()

    def mirror_color(self):
        """Will reverse red/bleu rgb values for the polygon color"""
        old_color = self.get_color()
        new_color = QtGui.QColor(
            old_color.blue(),
            old_color.green(),
            old_color.red(),
        )
        new_color.setAlpha(old_color.alpha())
        self.set_color(new_color)

    def duplicate_selected(self, *args, **kwargs):
        selected_pickers = self.scene().get_selected_items()
        if self not in selected_pickers:
            selected_pickers.append(self)
        new_pickers = []
        for picker in selected_pickers:
            new_picker = picker.duplicate()
            offset_x = (picker.boundingRect().width()) + 5
            new_pos = QtCore.QPointF(
                picker.pos().x() + offset_x, picker.pos().y()
            )
            new_picker.setPos(new_pos)
            new_pickers.append(new_picker)
        self.scene().select_picker_items(new_pickers)

    def duplicate(self, *args, **kwargs):
        """Will create a new picker item and copy data over."""
        # Create new picker item
        new_item = PickerItem()
        new_item.setParent(self.parent())
        self.scene().addItem(new_item)

        # Copy data over
        data = copy.deepcopy(self.get_data())
        new_item.set_data(data)

        return new_item

    def duplicate_and_mirror_selected(self):
        selected_pickers = self.scene().get_selected_items()
        if self not in selected_pickers:
            selected_pickers.append(self)

        search = None
        replace = None
        new_pickers = []
        for picker in selected_pickers:
            if picker.get_controls() and not search and not replace:
                search, replace, ok = SearchAndReplaceDialog.get()
                if not ok:
                    break
            new_picker = picker.duplicate_and_mirror(search, replace)
            new_pickers.append(new_picker)
        self.scene().select_picker_items(new_pickers)

    def duplicate_and_mirror(self, search=None, replace=None):
        """Duplicate and mirror picker item"""
        new_item = self.duplicate()
        new_item.mirror_color()
        new_item.mirror_position()
        new_item.mirror_shape()

        angle = self.rotation()
        new_item.mirror_rotation(angle)

        if self.get_controls():
            new_item.search_and_replace_controls(
                search=search, replace=replace
            )
        return new_item

    def paste_pos(self, x=True, y=False):
        """Paste the position x and y of a picker

        Args:
            x (bool, optional): if true paste X position
            y (bool, optional): if true paste Y position
        """
        selected_pickers = self.scene().get_selected_items()
        if self not in selected_pickers:
            selected_pickers.append(self)
        for picker in selected_pickers:
            DataCopyDialog.set_pos(picker, x, y)

    def copy_event(self):
        """Store pickerItem data for copy/paste support"""
        DataCopyDialog.get(self)

    def past_event(self):
        """Apply previously stored pickerItem data"""
        selected_pickers = self.scene().get_selected_items()
        if self not in selected_pickers:
            selected_pickers.append(self)
        for picker in selected_pickers:
            DataCopyDialog.set(picker)

    def past_x_event(self):
        """Paste X position"""
        self.paste_pos(x=True, y=False)

    def past_y_event(self):
        """Paste Y position"""
        self.paste_pos(x=False, y=True)

    def past_option_event(self):
        """Will open Paste option dialog window"""
        DataCopyDialog.options(self)

    # =========================================================================
    # Transforms ---
    def scale_shape(self, x=1.0, y=1.0, world=False):
        """Will scale shape based on axis x/y factors"""
        # Scale handles
        for handle in self.handles:
            handle.scale_pos(x, y)

        # Scale position
        if world:
            self.setPos(self.pos().x() * x, self.pos().y() * y)

        self.update()

    def rotate_shape(self, angle):
        """Rotate shape based on item center"""
        angle = self.rotation() + angle
        if angle > 360:
            angle = angle - 360

        self.setRotation(angle)
        self.update()

    def reset_rotation(self):
        """Reset rotation"""
        self.setRotation(0)
        self.update()

    # =========================================================================
    # Custom action handling ---
    def get_custom_action_mode(self):
        return self.custom_action

    def set_custom_action_mode(self, state):
        self.custom_action = state

    def set_custom_action_script(self, cmd):
        self.custom_action_script = cmd

    def get_custom_action_script(self):
        return self.custom_action_script

    # =========================================================================
    # Controls handling ---
    def get_namespace(self):
        """Will return associated namespace"""
        return self.namespace

    def set_control_list(self, ctrls=[]):
        """Update associated control list"""
        self.controls = ctrls

    def get_controls(self, with_namespace=True):
        """Return associated controls"""
        # Returned controls without namespace (as data stored)
        if not with_namespace:
            return self.controls

        # Get namespace
        namespace = self.get_namespace()

        # No namespace, return nodes
        if not namespace:
            return self.controls

        # Prefix nodes with namespace
        nodes = []
        for node in self.controls:
            nodes.append("{}:{}".format(namespace, node))

        return nodes

    def append_control(self, ctrl):
        """Add control to list"""
        self.controls.append(ctrl)

    def remove_control(self, ctrl):
        """Remove control from list"""
        if ctrl not in self.controls:
            return
        self.controls.remove(ctrl)

    def search_and_replace_controls(self, search=None, replace=None):
        """Will search and replace in associated controls names

        Args:
            search (str, optional): search string
            replace (str, optional): what to replace with

        Returns:
            Bool: if successful
        """
        # Open Search and replace dialog window
        ok = True
        if not search or not replace:
            search, replace, ok = SearchAndReplaceDialog.get()

        if not ok:
            return False

        # Parse controls
        node_missing = False
        controls = self.get_controls()[:]
        for i, ctrl in enumerate(controls):
            controls[i] = re.sub(search, replace, ctrl)
            if not cmds.objExists(controls[i]):
                node_missing = True

        # Print warning
        if node_missing:
            QtWidgets.QMessageBox.warning(
                self.parent(), "Warning", "Some target controls do not exist"
            )

        # Update list
        self.set_control_list(controls)

        return True

    def select_associated_controls(self, modifier=None):
        """Will select maya associated controls"""
        maya_handlers.select_nodes(self.get_controls(), modifier=modifier)

    def select_all_associated_controls(self, modifier=None):
        """Will select maya associated controls"""
        controls = []
        for picker in self.parent().scene().get_selected_items():
            controls.extend(picker.get_controls())
        maya_handlers.select_nodes(controls, modifier=modifier)

    def replace_controls_selection(self):
        """Will replace controls association with current selection"""
        self.set_control_list([])
        self.add_selected_controls()

    def add_selected_controls(self):
        """Add selected controls to control list"""
        # Get selection
        sel = cmds.ls(sl=True)

        # Add to stored list
        for ctrl in sel:
            if ctrl in self.get_controls():
                continue
            self.append_control(ctrl)

    def is_selected(self):
        """
        Will return True if a related control is currently selected
        (Only works with polygon that have a single associated maya_node)
        """
        # Get controls associated nodes
        controls = self.get_controls()

        # Abort if not single control polygon
        if not len(controls) == 1:
            return False

        # Check
        return __SELECTION__.is_selected(controls[0])

    def set_selected_state(self, state):
        """Will set border color feedback based on selection state"""
        self.polygon.set_selected_state(state)

    def run_selection_check(self):
        """Will set selection state based on selection status"""
        self.set_selected_state(self.is_selected())

    # =========================================================================
    # Custom menus handling ---
    def set_custom_menus(self, menus):
        """Set custom menu list for current poly data"""
        self.custom_menus = list(menus)

    def get_custom_menus(self):
        """Return current menu list for current poly data"""
        return self.custom_menus

    # =========================================================================
    # Data handling ---
    def set_data(self, data):
        """Set picker item from data dictionary"""
        # Set color
        if "color" in data:
            color = QtGui.QColor(*data["color"])
            self.set_color(color)

        # Set position
        if "position" in data:
            position = data.get("position", [0, 0])
            self.setPos(*position)

        # Set rotation
        if "rotation" in data:
            rotation = data.get("rotation")
            self.setRotation(rotation)

        # Set handles
        if "handles" in data:
            self.set_handles(data["handles"])

        # Set text
        if "text" in data:
            self.set_text(data["text"])
            self.set_text_size(data["text_size"])
            color = QtGui.QColor(*data["text_color"])
            self.set_text_color(color)

        # Set action mode
        if data.get("action_mode", False):
            self.set_custom_action_mode(True)
            self.set_custom_action_script(data.get("action_script", None))
            python_handlers.safe_code_exec(
                self.get_custom_action_script(), env=self.get_init_env()
            )

        # Set controls
        if "controls" in data:
            self.set_control_list(data["controls"])

        # Set custom menus
        if "menus" in data:
            self.set_custom_menus(data["menus"])

    def get_data(self):
        """Get picker item data in dictionary form"""
        # Init data dict
        data = {}

        # Add polygon color
        data["color"] = self.get_color().getRgb()

        # Add position
        data["position"] = [self.x(), self.y()]

        # Add rotation
        data["rotation"] = self.rotation()

        # Add handles datas
        handles_data = []
        for handle in self.handles:
            handles_data.append([handle.x(), handle.y()])
        data["handles"] = handles_data

        # Add mode data
        if self.get_custom_action_mode():
            data["action_mode"] = True
            data["action_script"] = self.get_custom_action_script()

        # Add controls data
        if self.get_controls():
            data["controls"] = self.get_controls(with_namespace=False)

        # Add custom menus data
        if self.get_custom_menus():
            data["menus"] = self.get_custom_menus()

        if self.get_text():
            data["text"] = self.get_text()
            data["text_size"] = self.get_text_size()
            data["text_color"] = self.get_text_color().getRgb()

        return data


class State(object):
    """State object, for easy state handling"""

    def __init__(self, state, name=False):
        self.state = state
        self.name = name

    def __lt__(self, other):
        """Override for "sort" function"""
        return self.name < other.name

    def get(self):
        return self.state

    def set(self, state):
        self.state = state


class DataCopyDialog(QtWidgets.QDialog):
    """PickerItem data copying dialog handler"""

    __DATA__ = {}

    __STATES__ = []
    __DO_POS__ = State(False, "position")
    __STATES__.append(__DO_POS__)
    __DO_ROT__ = State(False, "rotation")
    __STATES__.append(__DO_ROT__)
    __DO_COLOR__ = State(True, "color")
    __STATES__.append(__DO_COLOR__)
    __DO_ACTION_MODE__ = State(True, "action_mode")
    __STATES__.append(__DO_ACTION_MODE__)
    __DO_ACTION_SCRIPT__ = State(True, "action_script")
    __STATES__.append(__DO_ACTION_SCRIPT__)
    __DO_HANDLES__ = State(True, "handles")
    __STATES__.append(__DO_HANDLES__)
    __DO_TEXT__ = State(True, "text")
    __STATES__.append(__DO_TEXT__)
    __DO_TEXT_SIZE__ = State(True, "text_size")
    __STATES__.append(__DO_TEXT_SIZE__)
    __DO_TEXT_COLOR__ = State(True, "text_color")
    __STATES__.append(__DO_TEXT_COLOR__)
    __DO_CTRLS__ = State(True, "controls")
    __STATES__.append(__DO_CTRLS__)
    __DO_MENUS__ = State(True, "menus")
    __STATES__.append(__DO_MENUS__)

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.apply = False
        self.setup()

    def setup(self):
        """Build/Setup the dialog window"""
        self.setWindowTitle("Copy/Paste")

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add data field options
        for state in self.__STATES__:
            label_name = state.name.capitalize().replace("_", " ")
            cb = basic.CallbackCheckBoxWidget(
                callback=self.check_box_event,
                value=state.get(),
                label=label_name,
                state_obj=state,
            )
            self.main_layout.addWidget(cb)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = basic.CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = basic.CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

    def check_box_event(self, value=False, state_obj=None):
        """Update state object value on checkbox state change event"""
        state_obj.set(value)

    def accept_event(self):
        """Accept button event"""
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        """Cancel button event"""
        self.apply = False
        self.close()

    @classmethod
    def options(cls, item=None):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls()
        win.exec_()
        win.raise_()

        if not win.apply:
            return
        # win.set(item)

    @staticmethod
    def set_pos(item=None, x=True, y=True):
        """Set the position date for a specific picker item

        Args:
            item (object, optional): picker object item
            x (bool, optional): if true will set X position
            y (bool, optional): if true will set Y position
        """
        # Sanity check
        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg
        assert DataCopyDialog.__DATA__, "No stored data to paste"

        keys = []
        keys.append("position")

        # Build valid data
        data = {}
        for key in keys:
            if key not in DataCopyDialog.__DATA__:
                continue
            data[key] = DataCopyDialog.__DATA__[key]

        # Get picker item data
        item_data = item.get_data()

        if x:
            data["position"][1] = item_data["position"][1]
        if y:
            data["position"][0] = item_data["position"][0]
        item.set_data(data)

    @staticmethod
    def set(item=None):
        """Set the data to specific picker item

        Args:
            item (object, optional): Picker object
        """
        # Sanity check
        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg
        assert DataCopyDialog.__DATA__, "No stored data to paste"

        # Filter data keys to copy
        keys = []
        for state in DataCopyDialog.__STATES__:
            if not state.get():
                continue
            keys.append(state.name)

        # Build valid data
        data = {}
        for key in keys:
            if key not in DataCopyDialog.__DATA__:
                continue
            data[key] = DataCopyDialog.__DATA__[key]

        # Get picker item data
        item.set_data(data)

    @staticmethod
    def get(item=None):
        """Will get and store data for specified item"""
        # Sanity check
        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg

        # Get picker item data
        data = item.get_data()

        # Store data
        DataCopyDialog.__DATA__ = data

        return data
