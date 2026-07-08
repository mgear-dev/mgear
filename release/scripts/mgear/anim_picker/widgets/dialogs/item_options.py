"""Picker item options editor window.

Extracted from picker_widgets.py during the Phase 2 decomposition.
"""

import copy

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import basic
from mgear.anim_picker.widgets.dialogs.script_dialog import (
    CustomScriptEditDialog,
)
from mgear.anim_picker.widgets.dialogs.script_dialog import (
    CustomMenuEditDialog,
)
from mgear.anim_picker.widgets.dialogs.handles_window import (
    HandlesPositionWindow,
)


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
