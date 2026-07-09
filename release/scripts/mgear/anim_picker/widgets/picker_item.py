"""Picker item graphic object and selection helper.

Extracted from picker_widgets.py during the Phase 2 decomposition.
"""

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

from mgear.anim_picker.widgets.graphics import DefaultPolygon
from mgear.anim_picker.widgets.graphics import PointHandle
from mgear.anim_picker.widgets.graphics import Polygon
from mgear.anim_picker.widgets.graphics import GraphicText
from mgear.anim_picker.widgets.dialogs.item_options import ItemOptionsWindow
from mgear.anim_picker.widgets.dialogs.search_replace_dialog import (
    SearchAndReplaceDialog,
)
from mgear.anim_picker.widgets.dialogs.copy_paste_dialog import DataCopyDialog
from mgear.anim_picker.widgets.item_model import PickerItemData
from mgear.anim_picker.widgets import mirror
from mgear.anim_picker.handlers import __EDIT_MODE__
from mgear.anim_picker.handlers import __SELECTION__
from mgear.anim_picker.handlers import python_handlers
from mgear.anim_picker.handlers import maya_handlers


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

        # Persistent mirror link (optional): item_id is a stable id minted when
        # the item is first linked; mirror_id is the partner's item_id.
        self.item_id = None
        self.mirror_id = None

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
        super().hoverEnterEvent(event)

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
        super().mouseMoveEvent(gfx_event)

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
        """Surface the inline editor bound to this item.

        Replaces the per-item modal for the common path (6a): the docked panel
        edits the whole selection inline. Falls back to the legacy
        ``ItemOptionsWindow`` only when no inline panel is available.
        """
        panel = getattr(self.main_window, "edit_panel", None)
        if panel is None:
            self._open_options_modal()
            return

        # Bind the panel to this item, keeping any existing multi-selection.
        if not self.polygon.selected:
            self.scene().select_picker_items([self])
        panel.sync()
        panel.setVisible(True)
        panel.raise_()
        panel.setFocus()

    def _open_options_modal(self):
        """Open the legacy single-item options modal (fallback only)."""
        if self.edit_window:
            try:
                self.edit_window.close()
                self.edit_window.deleteLater()
            except Exception:
                pass

        self.edit_window = ItemOptionsWindow(
            parent=self.main_window, picker_item=self
        )
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
        # Break any mirror link so the partner is not left pointing at a
        # deleted item.
        view = self.parent()
        if self.mirror_id and hasattr(view, "unlink_mirror"):
            view.unlink_mirror(self)
        self.scene().removeItem(self)
        self.setParent(None)
        self.deleteLater()

    def get_delta_from_point(self, point):
        self.cursor_delta = self.pos() - point
        return self.cursor_delta

    # =========================================================================
    # Ducplicate and mirror methods ---
    def mirror_position(self, axis_x=0.0):
        """Mirror picker position about the vertical axis at ``axis_x``."""
        pos = mirror.mirror_position([self.pos().x(), self.pos().y()], axis_x)
        self.setX(pos[0])

    def mirror_rotation(self, angle=None):
        """Mirror picker rotation angle"""
        if not angle:
            angle = self.rotation()
        self.setRotation(mirror.mirror_rotation(angle))
        self.update()

    def mirror_shape(self):
        """Will mirror polygon handles position on X axis"""
        handles = [[handle.x(), handle.y()] for handle in self.handles]
        self.set_handles(mirror.mirror_handles(handles))

    def mirror_color(self):
        """Will reverse red/bleu rgb values for the polygon color"""
        new_color = mirror.mirror_color(self.get_color().getRgb())
        self.set_color(QtGui.QColor(*new_color))

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

        # A duplicate is an independent item: never inherit the source's
        # stable id or mirror link (those are re-established by explicit
        # linking, e.g. Duplicate & Mirror).
        new_item.item_id = None
        new_item.mirror_id = None

        return new_item

    def duplicate_and_mirror_selected(self):
        """Duplicate + mirror the selection.

        Returns:
            list: ``(source, new)`` pairs, so callers (e.g. the toolbar
            command) can link each pair as a persistent mirror relationship.
        """
        selected_pickers = self.scene().get_selected_items()
        if self not in selected_pickers:
            selected_pickers.append(self)

        search = None
        replace = None
        pairs = []
        for picker in selected_pickers:
            if picker.get_controls() and not search and not replace:
                search, replace, ok = SearchAndReplaceDialog.get()
                if not ok:
                    break
            new_picker = picker.duplicate_and_mirror(search, replace)
            pairs.append((picker, new_picker))
        self.scene().select_picker_items([new for _, new in pairs])
        return pairs

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
        """Set picker item from data dictionary.

        Values are parsed through the Qt-free ``PickerItemData`` model, while
        the per-key presence checks are preserved so partial data (as sent by
        copy/paste) only updates the keys it carries.
        """
        model = PickerItemData.from_dict(data)

        # Set color
        if "color" in data:
            self.set_color(QtGui.QColor(*model.color))

        # Set position
        if "position" in data:
            self.setPos(*model.position)

        # Set rotation
        if "rotation" in data:
            self.setRotation(model.rotation)

        # Set handles
        if "handles" in data:
            self.set_handles(model.handles)

        # Set text (read size/color from the dict to preserve the exact
        # legacy behavior when a partial paste carries "text" alone)
        if "text" in data:
            self.set_text(data["text"])
            self.set_text_size(data["text_size"])
            self.set_text_color(QtGui.QColor(*data["text_color"]))

        # Set action mode
        if model.action_mode:
            self.set_custom_action_mode(True)
            self.set_custom_action_script(model.action_script)
            python_handlers.safe_code_exec(
                self.get_custom_action_script(), env=self.get_init_env()
            )

        # Set controls
        if "controls" in data:
            self.set_control_list(model.controls)

        # Set custom menus
        if "menus" in data:
            self.set_custom_menus(model.menus)

        # Mirror link (optional, additive keys)
        if model.item_id:
            self.item_id = model.item_id
        if model.mirror_id:
            self.mirror_id = model.mirror_id

    def get_data(self):
        """Get picker item data in dictionary form.

        Reads the item state into the Qt-free ``PickerItemData`` model and
        serializes it back to the schema dict.
        """
        model = PickerItemData()
        model.color = self.get_color().getRgb()
        model.position = [self.x(), self.y()]
        model.rotation = self.rotation()
        model.handles = [[handle.x(), handle.y()] for handle in self.handles]

        if self.get_custom_action_mode():
            model.action_mode = True
            model.action_script = self.get_custom_action_script()

        if self.get_controls():
            model.controls = self.get_controls(with_namespace=False)

        if self.get_custom_menus():
            model.menus = self.get_custom_menus()

        if self.get_text():
            model.text = self.get_text()
            model.text_size = self.get_text_size()
            model.text_color = self.get_text_color().getRgb()

        model.item_id = self.item_id
        model.mirror_id = self.mirror_id

        return model.to_dict()
