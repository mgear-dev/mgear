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
from mgear.anim_picker.widgets.graphics import WidgetGraphic
from mgear.anim_picker.widgets.graphics import BackdropGraphic
from mgear.anim_picker.widgets.graphics import VectorGraphic
from mgear.anim_picker.widgets.dialogs.item_options import ItemOptionsWindow
from mgear.anim_picker.widgets.dialogs.search_replace_dialog import (
    SearchAndReplaceDialog,
)
from mgear.anim_picker.widgets.dialogs.copy_paste_dialog import DataCopyDialog
from mgear.anim_picker.widgets.item_model import PickerItemData
from mgear.anim_picker.widgets import mirror
from mgear.anim_picker.widgets import overlay
from mgear.anim_picker.widgets import widget_binding
from mgear.anim_picker.widgets import visibility
from mgear.core import svg_import
from mgear.anim_picker.handlers import __EDIT_MODE__
from mgear.anim_picker.handlers import __SELECTION__
from mgear.anim_picker.handlers import python_handlers
from mgear.anim_picker.handlers import maya_handlers
from mgear.anim_picker.handlers import widget_handlers


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

        # Backdrop container body (rounded / straight fill + title); replaces
        # the plain polygon when the item is a backdrop, hidden otherwise.
        self.backdrop_graphic = BackdropGraphic(parent=self)

        # Vector (curved) body imported from SVG; replaces the plain polygon
        # when the item is a vector shape, hidden otherwise.
        self.vector_graphic = VectorGraphic(parent=self)

        # Interactive-widget affordance (checkbox / slider); drawn above the
        # polygon and below the text, hidden unless the item is a widget.
        self.widget_graphic = WidgetGraphic(parent=self)

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

        # Viewport pin (optional HUD overlay): when pinned the item ignores the
        # canvas pan/zoom and is repositioned by the view to ``anchor`` +
        # ``offset`` (a 3x3 viewport anchor code + inward pixel offset). The
        # view records a per-item drag delta here while an offset drag is live.
        self.pinned = False
        self.anchor = overlay.DEFAULT_ANCHOR
        self.offset = list(overlay.DEFAULT_OFFSET)
        self._pin_drag_delta = (0.0, 0.0)
        # Screen scale baked into the pin transform so a pinned item keeps the
        # apparent size it had when pinned (rather than snapping to 1:1, which
        # looks tiny when the canvas was zoomed in). Captured at pin time and
        # persisted so a reload restores the size.
        self.pin_scale = 1.0

        # Interactive widget (optional): a non-button ``widget_type`` makes the
        # item a checkbox / slider bound to a Maya attribute (``binding``) and/
        # or per-state ``widget_scripts``. ``_widget_dragging`` is set while a
        # slider drag is live so the drag is grouped into one undo chunk.
        self.widget_type = widget_binding.WIDGET_BUTTON
        self.binding = {}
        self.widget_scripts = {}
        self._widget_dragging = False

        # Backdrop container (optional): a large rectangle behind the picker
        # items that moves everything geometrically inside it when dragged.
        self.backdrop = False

        # Visibility condition (optional): a channel-state / zoom-level test
        # that hides the item in animation mode until it passes. Empty means
        # always visible. Evaluated by the view on zoom / selection / time.
        self.visibility = {}

        # Vector (SVG) shape (optional): normalized subpaths imported from an
        # SVG. When set, the item is a curved shape (polygon hidden). Empty
        # means the item is a plain polygon.
        self.svg = {}

    def shape(self):
        path = QtGui.QPainterPath()

        # A vector item is hit-tested on its curved silhouette, not the polygon.
        if self.svg:
            path.addPath(self.vector_graphic.shape())
        elif self.polygon:
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
        # A pinned item is not moved in scene space: its drag updates its
        # viewport anchor / offset instead (the view snaps the anchor).
        if self.pinned:
            view = self.parent()
            if hasattr(view, "update_pin_drag"):
                view.update_pin_drag(self, event.scenePos())
            return
        self.setPos(event.scenePos() + self.cursor_delta)

    def mouseMoveEvent(self, event):
        gfx_event = event
        # A live slider drag (animation mode) updates the bound value.
        if self._widget_dragging:
            self._widget_mouse_drag(event)
            return
        if event.buttons() == QtCore.Qt.LeftButton and __EDIT_MODE__.get():
            if self.currently_selected:
                [
                    item.mouseMoveEvent_offset(event)
                    for item in self.currently_selected
                ]
            # The pressed item is moved by Qt (ItemIsMovable) when free, but a
            # pinned item is non-movable, so route its drag to an offset here.
            if self.pinned:
                self.mouseMoveEvent_offset(event)
                return
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
            # Backdrop move-together: dragging a backdrop (the pressed item or
            # any selected one) also drags every item whose center lies within
            # its rectangle, so items visually inside it -- including a nested
            # backdrop and its contents -- move as a group.
            movers = [self] + self.currently_selected
            for backdrop in [item for item in movers if item.backdrop]:
                for item in backdrop.contained_items():
                    if item is self or item in self.currently_selected:
                        continue
                    self.currently_selected.append(item)
                    item.get_delta_from_point(event.scenePos())
            # Prime the offset drag for any pinned item in the drag set (the
            # view records a per-item grab delta so the anchor tracks the
            # cursor without jumping to the item's origin).
            view = self.parent()
            if hasattr(view, "begin_pin_drag"):
                for item in [self] + self.currently_selected:
                    if item.pinned:
                        view.begin_pin_drag(item, event.scenePos())
            return DefaultPolygon.mousePressEvent(self, event)

        # Run selection on left mouse button event
        if event.buttons() == QtCore.Qt.LeftButton:
            # Interactive widget (checkbox / slider) handles its own press and
            # keeps the mouse grab for a drag; it is not a control selection.
            # Accepting the press makes the item the mouse grabber so the
            # slider drag receives the subsequent move / release events.
            if self.is_widget():
                event.accept()
                self._widget_mouse_press(event)
                return
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

    def mouseReleaseEvent(self, event):
        """Event called on mouse release (ends a live slider drag)."""
        if self._widget_dragging:
            self._widget_mouse_release(event)
            return
        super().mouseReleaseEvent(event)

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

        # Widget state vars (populated by widget interactions before exec;
        # present as defaults so a script can always reference them).
        env["__STATE__"] = None
        env["__VALUE__"] = None
        env["__X__"] = None
        env["__Y__"] = None

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

    def get_text_align(self):
        """Return the text placement (``center`` / top / bottom / left / right)."""
        return self.text.align

    def set_text_align(self, align):
        """Set the text placement, keeping the current offset."""
        self.text.set_alignment(align, self.text.offset)

    def get_text_offset(self):
        """Return the text gap (pixels) from the aligned edge."""
        return self.text.offset

    def set_text_offset(self, offset):
        """Set the text gap (pixels), keeping the current alignment."""
        self.text.set_alignment(self.text.align, offset)

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
        # Removing the last conditioned item must clear the view's visibility
        # gate, else it keeps iterating every item on each zoom / selection.
        if hasattr(view, "_recompute_conditional_flag"):
            view._recompute_conditional_flag()

    def get_delta_from_point(self, point):
        self.cursor_delta = self.pos() - point
        return self.cursor_delta

    # =========================================================================
    # Viewport pin (HUD overlay) ---
    def get_pinned(self):
        """Return True when the item is pinned to the viewport."""
        return self.pinned

    def set_pinned(self, state, capture_scale=True):
        """Pin / unpin the item to the viewport.

        A pinned item ignores the view transform so it draws at a constant
        screen size (like the point handles). To avoid the item snapping to its
        tiny 1:1 size when pinned (jarring when the canvas is zoomed in), the
        current view scale is baked into the transform so it keeps its apparent
        size; a compensating vertical flip keeps it upright despite the
        Y-flipped view. The view owns the item's *position* (see
        ``_update_pinned_items``); a pinned item is repositioned by an
        offset-drag rather than a free scene move, so it is made non-movable.

        Args:
            state (bool): pin when True, unpin when False.
            capture_scale (bool, optional): when pinning, sample the current
                view scale into ``pin_scale``; False keeps the existing value
                (used on load so a saved size is restored, not re-sampled).
        """
        self.pinned = bool(state)
        self.setFlag(
            QtWidgets.QGraphicsItem.ItemIgnoresTransformations, self.pinned
        )
        if self.pinned:
            if capture_scale:
                self.pin_scale = self._current_view_scale()
            # scale(s, -s): s preserves the apparent size, -s counters the
            # view's scale(1, -1) so the item is not vertically mirrored.
            self.setTransform(
                QtGui.QTransform().scale(self.pin_scale, -self.pin_scale)
            )
        else:
            self.setTransform(QtGui.QTransform())
        if __EDIT_MODE__.get():
            self.setFlag(
                QtWidgets.QGraphicsItem.ItemIsMovable, not self.pinned
            )

    def _current_view_scale(self):
        """Return the view's current uniform scale (1.0 when unavailable)."""
        view = self.parent()
        if view is None or not hasattr(view, "viewportTransform"):
            return 1.0
        scale = abs(view.viewportTransform().m11())
        return scale or 1.0

    def get_pin_scale(self):
        """Return the screen scale baked into the pin transform."""
        return self.pin_scale

    def set_pin_scale(self, scale):
        """Set the pin transform scale (re-applies when currently pinned)."""
        self.pin_scale = scale or 1.0
        if self.pinned:
            self.setTransform(
                QtGui.QTransform().scale(self.pin_scale, -self.pin_scale)
            )

    def get_anchor(self):
        """Return the item's 3x3 viewport anchor code."""
        return self.anchor

    def set_anchor(self, anchor):
        """Set the item's viewport anchor code (e.g. ``"tl"``)."""
        self.anchor = anchor

    def get_offset(self):
        """Return the item's inward ``[dx, dy]`` pixel offset."""
        return self.offset

    def set_offset(self, offset):
        """Set the item's inward ``[dx, dy]`` pixel offset."""
        self.offset = list(offset)

    # =========================================================================
    # Interactive widget (checkbox / slider) ---
    def is_widget(self):
        """Return True when the item is an interactive (non-button) widget."""
        return widget_binding.is_interactive(self.widget_type)

    def get_widget_type(self):
        """Return the item's widget type (button / checkbox / slider / ...)."""
        return self.widget_type

    def set_widget_type(self, widget_type):
        """Set the widget type and toggle the affordance visibility.

        Args:
            widget_type (str): a value from ``widget_binding.WIDGET_TYPES``.
        """
        self.widget_type = widget_type or widget_binding.WIDGET_BUTTON
        interactive = self.is_widget()
        self.widget_graphic.setVisible(interactive)
        # Give a freshly-typed widget a sane default range to drive, and seed
        # "just print" scripts so it works out of the box and logs its value.
        if interactive and not self.binding:
            self.binding = widget_binding.default_binding()
        if interactive and not self.widget_scripts:
            self.widget_scripts = widget_binding.default_scripts(
                self.widget_type
            )
        self.refresh_widget_state()
        self.update()

    def get_binding(self):
        """Return the widget's binding dict (attribute(s) + range)."""
        return self.binding

    def set_binding(self, binding):
        """Set the widget's binding dict and refresh the displayed value."""
        self.binding = dict(binding) if binding else {}
        self.refresh_widget_state()

    def get_widget_scripts(self):
        """Return the widget's per-state script dict."""
        return self.widget_scripts

    def set_widget_scripts(self, scripts):
        """Set the widget's per-state script dict."""
        self.widget_scripts = dict(scripts) if scripts else {}

    def _widget_is_horizontal(self):
        """Return True when a 1D slider is horizontal (its default)."""
        orientation = (self.binding or {}).get(
            "orientation", widget_binding.ORIENT_HORIZONTAL
        )
        return orientation == widget_binding.ORIENT_HORIZONTAL

    def _widget_norm_from_pos(self, pos):
        """Return the normalized value(s) for a cursor position.

        Maps ``pos`` (item-local) within the polygon's bounding rect to 0..1.
        Higher screen positions map to larger values (the view is Y-flipped).

        Args:
            pos (QPointF): cursor position in item-local coordinates.

        Returns:
            float or tuple: 0..1 for a 1D slider, ``(x, y)`` for a 2D slider.
        """
        rect = self.polygon.shape().boundingRect()
        x0, x1, y0, y1 = widget_binding.track_bounds(
            rect.left(), rect.right(), rect.top(), rect.bottom()
        )
        nx = 0.0 if x1 == x0 else (pos.x() - x0) / (x1 - x0)
        ny = 0.0 if y1 == y0 else (pos.y() - y0) / (y1 - y0)
        nx = widget_binding.clamp(nx, 0.0, 1.0)
        ny = widget_binding.clamp(ny, 0.0, 1.0)
        if self.widget_type == widget_binding.WIDGET_SLIDER2D:
            return (nx, ny)
        return nx if self._widget_is_horizontal() else ny

    def _widget_mouse_press(self, event):
        """Handle a widget press in animation mode."""
        if self.widget_type == widget_binding.WIDGET_CHECKBOX:
            self._widget_toggle()
            return
        # Slider: begin a single-undo drag and set the value from the press.
        self._widget_dragging = True
        cmds.undoInfo(openChunk=True)
        self._widget_mouse_drag(event)

    def _widget_mouse_drag(self, event):
        """Apply the value at the current cursor position during a drag."""
        self._apply_widget_value(self._widget_norm_from_pos(event.pos()))

    def _widget_mouse_release(self, event):
        """End a slider drag (optionally recentering a 2D slider)."""
        if self.widget_type == widget_binding.WIDGET_SLIDER2D and (
            self.binding or {}
        ).get("recenter"):
            self._apply_widget_value((0.5, 0.5))
        self._widget_dragging = False
        cmds.undoInfo(closeChunk=True)

    def _run_widget_script(self, key, extra_env):
        """Run the widget's script for ``key`` with extra exec-env vars.

        Args:
            key (str): script key (``on`` / ``off`` / ``value`` / ``xy``).
            extra_env (dict): widget-state vars merged into the exec env.
        """
        script = (self.widget_scripts or {}).get(key)
        if not script:
            return
        env = self.get_exec_env()
        env.update(extra_env)
        python_handlers.safe_code_exec(script, env=env)

    def _widget_toggle(self):
        """Toggle the checkbox: flip the bound bool attr and/or run a script."""
        binding = self.binding or {}
        attr = widget_handlers.resolve_attr(
            binding.get("attr"), self.get_namespace()
        )
        # One undo for the attribute flip + its script.
        with widget_handlers.undo_chunk():
            if attr:
                new_state = widget_handlers.toggle_attr(attr)
                if new_state is not None:
                    self.widget_graphic.checked = new_state
            else:
                # Script-only checkbox: flip the displayed state itself.
                self.widget_graphic.checked = not self.widget_graphic.checked
            state = self.widget_graphic.checked
            self._run_widget_script(
                "on" if state else "off", {"__STATE__": state}
            )
        self.widget_graphic.update()

    def _apply_widget_value(self, norm):
        """Write a normalized slider value to the bound attribute(s)/script.

        Args:
            norm (float or tuple): 0..1 for a 1D slider, ``(x, y)`` for 2D.
        """
        binding = self.binding or {}
        namespace = self.get_namespace()
        if self.widget_type == widget_binding.WIDGET_SLIDER2D:
            nx, ny = norm
            vx = widget_binding.map_value(
                nx, binding.get("min_x", -1.0), binding.get("max_x", 1.0)
            )
            vy = widget_binding.map_value(
                ny, binding.get("min_y", -1.0), binding.get("max_y", 1.0)
            )
            self.widget_graphic.value_xy = (nx, ny)
            attr_x = widget_handlers.resolve_attr(
                binding.get("attr_x"), namespace
            )
            attr_y = widget_handlers.resolve_attr(
                binding.get("attr_y"), namespace
            )
            if attr_x:
                widget_handlers.write_attr(attr_x, vx)
            if attr_y:
                widget_handlers.write_attr(attr_y, vy)
            self._run_widget_script("xy", {"__X__": vx, "__Y__": vy})
        else:
            value = widget_binding.map_value(
                norm, binding.get("min", 0.0), binding.get("max", 1.0)
            )
            self.widget_graphic.value = norm
            attr = widget_handlers.resolve_attr(binding.get("attr"), namespace)
            if attr:
                widget_handlers.write_attr(attr, value)
            self._run_widget_script("value", {"__VALUE__": value})
        self.widget_graphic.update()

    def refresh_widget_state(self):
        """Refresh the widget's displayed value from its bound attribute(s).

        Called on load and on the selection-change refresh so the widget
        reflects the rig. Reads only, never writes, and is safe when the target
        attribute is missing (the current / default display value is kept).
        """
        if not self.is_widget():
            return
        binding = self.binding or {}
        namespace = self.get_namespace()
        if self.widget_type == widget_binding.WIDGET_CHECKBOX:
            attr = widget_handlers.resolve_attr(binding.get("attr"), namespace)
            value = widget_handlers.read_attr(attr) if attr else None
            if value is not None:
                self.widget_graphic.checked = bool(value)
        elif self.widget_type == widget_binding.WIDGET_SLIDER:
            attr = widget_handlers.resolve_attr(binding.get("attr"), namespace)
            value = widget_handlers.read_attr(attr) if attr else None
            if value is not None:
                self.widget_graphic.value = widget_binding.normalize(
                    value, binding.get("min", 0.0), binding.get("max", 1.0)
                )
        elif self.widget_type == widget_binding.WIDGET_SLIDER2D:
            attr_x = widget_handlers.resolve_attr(
                binding.get("attr_x"), namespace
            )
            attr_y = widget_handlers.resolve_attr(
                binding.get("attr_y"), namespace
            )
            value_x = widget_handlers.read_attr(attr_x) if attr_x else None
            value_y = widget_handlers.read_attr(attr_y) if attr_y else None
            cur_x, cur_y = self.widget_graphic.value_xy
            if value_x is not None:
                cur_x = widget_binding.normalize(
                    value_x,
                    binding.get("min_x", -1.0),
                    binding.get("max_x", 1.0),
                )
            if value_y is not None:
                cur_y = widget_binding.normalize(
                    value_y,
                    binding.get("min_y", -1.0),
                    binding.get("max_y", 1.0),
                )
            self.widget_graphic.value_xy = (cur_x, cur_y)
        self.widget_graphic.update()

    # =========================================================================
    # Conditional visibility ---
    def get_visibility(self):
        """Return the item's visibility condition dict (empty when none)."""
        return self.visibility

    def set_visibility(self, condition):
        """Set (or clear) the item's visibility condition.

        Args:
            condition (dict): a ``widgets.visibility`` condition, or a falsy
                value to clear it (the item then stays always visible).
        """
        self.visibility = dict(condition) if condition else {}

    def has_visibility_condition(self):
        """Return True when the item carries a visibility condition."""
        return bool(self.visibility)

    def evaluate_visibility(self, zoom):
        """Show / hide the item for its condition at the current ``zoom``.

        Edit mode always shows the item so a condition can never block editing.
        A channel condition reads its attribute here (namespace applied, safe
        read); the pure show/hide decision is delegated to
        ``widgets.visibility``. A no-op decision (fail-open) keeps the item
        visible.

        Args:
            zoom (float): the view's current zoom scale.
        """
        if __EDIT_MODE__.get():
            self.setVisible(True)
            return
        condition = self.visibility
        if not condition:
            self.setVisible(True)
            return
        value = None
        if condition.get("mode") == visibility.VIS_CHANNEL:
            attr = widget_handlers.resolve_attr(
                condition.get("attr"), self.get_namespace()
            )
            value = widget_handlers.read_attr(attr) if attr else None
        self.setVisible(
            visibility.evaluate(condition, {"zoom": zoom, "value": value})
        )

    # =========================================================================
    # Vector (SVG) shape ---
    def is_vector_shape(self):
        """Return True when the item is a vector (SVG-imported) shape."""
        return bool(self.svg)

    def get_svg_shape(self):
        """Return the item's vector shape dict (empty when not a vector)."""
        return self.svg

    def set_svg_shape(self, svg):
        """Set (or clear) the item's vector shape.

        A vector shape swaps the plain polygon body for the curved
        ``vector_graphic`` (like the backdrop swap). Passing a falsy value
        reverts the item to its polygon.

        Args:
            svg (dict): ``{"subpaths": [...], "name": ...}`` from
                ``svg_import.parse_svg``, or a falsy value to clear it.
        """
        self.svg = dict(svg) if svg else {}
        subpaths = self.svg.get("subpaths", []) if self.svg else []
        # set_subpaths rebuilds the vector path and repaints the child.
        self.vector_graphic.set_subpaths(subpaths)
        self.vector_graphic.set_mode(
            self.svg.get("mode", svg_import.MODE_FILL) if self.svg else None
        )
        self.vector_graphic.set_stroke_width(self.svg.get("stroke_width", 2.0))
        # The polygon is kept as the fallback body; hide its drawing while the
        # vector graphic is shown (mirrors the backdrop swap). Handles stay
        # hidden for a vector item (no per-point editing in this version). A
        # vector body takes precedence over a backdrop (one visible body).
        self.polygon.setVisible(not self.svg)
        self.vector_graphic.setVisible(bool(self.svg))
        if self.svg:
            self.backdrop_graphic.setVisible(False)
        # The item's shape()/boundingRect derive from the vector path, so tell
        # the scene of the geometry change (the item itself paints nothing).
        self.prepareGeometryChange()

    def get_svg_subpaths(self):
        """Return the vector shape's subpaths (empty when not a vector)."""
        return self.svg.get("subpaths", []) if self.svg else []

    def set_svg_subpaths(self, subpaths):
        """Replace the vector shape's subpaths (scale / mirror bake here)."""
        if not self.svg:
            return
        self.svg["subpaths"] = subpaths
        self.vector_graphic.set_subpaths(subpaths)
        self.prepareGeometryChange()

    def get_svg_mode(self):
        """Return the vector render mode (``fill`` / ``stroke``)."""
        return self.svg.get("mode", svg_import.MODE_FILL) if self.svg else (
            svg_import.MODE_FILL
        )

    def set_svg_mode(self, mode):
        """Set the vector render mode (fill vs stroke)."""
        if not self.svg:
            return
        self.svg["mode"] = mode
        self.vector_graphic.set_mode(mode)

    def get_svg_stroke_width(self):
        """Return the vector stroke width (used in stroke mode)."""
        return self.svg.get("stroke_width", 2.0) if self.svg else 2.0

    def set_svg_stroke_width(self, width):
        """Set the vector stroke width (used in stroke mode)."""
        if not self.svg:
            return
        self.svg["stroke_width"] = width
        self.vector_graphic.set_stroke_width(width)

    # =========================================================================
    # Backdrop container ---
    def get_backdrop(self):
        """Return True when the item is a backdrop container."""
        return self.backdrop

    def set_backdrop(self, state):
        """Toggle backdrop mode (swaps the polygon body for the backdrop)."""
        self.backdrop = bool(state)
        # The backdrop graphic replaces the plain polygon fill; the polygon is
        # kept only as the (still hit-testable) shape, so hide its drawing.
        self.polygon.setVisible(not self.backdrop)
        self.backdrop_graphic.setVisible(self.backdrop)
        self.update()

    def get_backdrop_title(self):
        """Return the backdrop title text."""
        return self.backdrop_graphic.title

    def set_backdrop_title(self, title):
        """Set the backdrop title text."""
        self.backdrop_graphic.title = title or ""
        self.backdrop_graphic.update()

    def get_corner_radius(self):
        """Return the backdrop corner radius (0 = straight corners)."""
        return self.backdrop_graphic.corner_radius

    def set_corner_radius(self, radius):
        """Set the backdrop corner radius (0 = straight corners)."""
        self.backdrop_graphic.corner_radius = max(0.0, radius or 0.0)
        self.backdrop_graphic.update()

    def contained_items(self):
        """Return items whose center lies within this backdrop's rectangle.

        Used for backdrop move-together; the center-in-rect test naturally
        includes nested backdrops and their contents (anything visually inside
        the rectangle moves as a group).

        Returns:
            list: the contained PickerItems (empty when not a backdrop).
        """
        view = self.parent()
        if view is None or not hasattr(view, "get_picker_items"):
            return []
        my_rect = self.sceneBoundingRect()
        contained = []
        for item in view.get_picker_items():
            if item is self:
                continue
            if my_rect.contains(item.sceneBoundingRect().center()):
                contained.append(item)
        return contained

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
        """Mirror the item's shape on X (vector subpaths or handles)."""
        if self.svg:
            self.set_svg_subpaths(
                svg_import.scale_subpaths(self.get_svg_subpaths(), -1.0, 1.0)
            )
            return
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
        # Route selection to the vector body too (it draws its own border).
        if self.svg:
            self.vector_graphic.set_selected_state(state)

    def run_selection_check(self):
        """Will set selection state based on selection status"""
        self.set_selected_state(self.is_selected())
        # Reflect the bound attribute value on the selection-change refresh.
        if self.is_widget():
            self.refresh_widget_state()

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
            if model.text_align is not None:
                self.set_text_align(model.text_align)
            if model.text_offset is not None:
                self.set_text_offset(model.text_offset)

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

        # Viewport pin (optional, additive keys). Apply anchor / offset first so
        # the view can place the item on the next _update_pinned_items pass.
        if model.pinned:
            if model.anchor:
                self.set_anchor(model.anchor)
            if model.offset is not None:
                self.set_offset(model.offset)
            if model.pin_scale is not None:
                self.pin_scale = model.pin_scale
            # Restore the saved size instead of re-sampling the current zoom.
            self.set_pinned(True, capture_scale=False)

        # Interactive widget (optional, additive keys). Set the binding /
        # scripts first so ``set_widget_type`` can refresh the display value.
        if model.widget:
            self.set_binding(model.binding or {})
            self.set_widget_scripts(model.scripts or {})
            self.set_widget_type(model.widget)

        # Backdrop container (optional, additive keys). Set the title / corner
        # radius first, then enable so the graphic shows with them applied.
        if model.backdrop:
            if model.title is not None:
                self.set_backdrop_title(model.title)
            if model.corner_radius is not None:
                self.set_corner_radius(model.corner_radius)
            self.set_backdrop(True)

        # Visibility condition (optional, additive key).
        if model.visibility:
            self.set_visibility(model.visibility)

        # Vector (SVG) shape (optional, additive key).
        if model.svg:
            self.set_svg_shape(model.svg)

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
            model.text_align = self.get_text_align()
            model.text_offset = self.get_text_offset()

        model.item_id = self.item_id
        model.mirror_id = self.mirror_id

        if self.pinned:
            model.pinned = True
            model.anchor = self.anchor
            model.offset = list(self.offset)
            model.pin_scale = self.pin_scale

        if self.is_widget():
            model.widget = self.widget_type
            model.binding = dict(self.binding) if self.binding else None
            model.scripts = (
                dict(self.widget_scripts) if self.widget_scripts else None
            )

        if self.backdrop:
            model.backdrop = True
            model.title = self.get_backdrop_title()
            model.corner_radius = self.get_corner_radius()

        if self.visibility:
            model.visibility = dict(self.visibility)

        if self.svg:
            model.svg = dict(self.svg)

        return model.to_dict()
