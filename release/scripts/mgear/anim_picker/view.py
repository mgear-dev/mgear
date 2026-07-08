"""Graphics view widget (picker canvas) for the anim picker.

Extracted from gui.py during the Phase 2 decomposition.
"""

import os
import copy
import json
from functools import partial

from maya import cmds
import mgear.pymaya as pm

import mgear
from mgear.core import attribute
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.scene import OrderedGraphicsScene
from mgear.anim_picker.constants import MAYA_OVERRIDE_COLOR
from mgear.anim_picker.constants import PICKER_EXTRACTION_NAME
from mgear.anim_picker.constants import ANIM_PICKER_RELATIVE_IMAGES
from mgear.anim_picker.constants import DEFAULT_RELATIVE_IMAGES_PATH
from mgear.anim_picker.widgets import basic
from mgear.anim_picker.widgets import picker_widgets
from mgear.anim_picker.handlers import __EDIT_MODE__


# module clipboard shared across views (copy/paste of picker items)
_CLIPBOARD = []


class GraphicViewWidget(QtWidgets.QGraphicsView):
    """Graphic view widget that display the "polygons" picker items"""

    __DEFAULT_SCENE_WIDTH__ = 6000
    __DEFAULT_SCENE_HEIGHT__ = 6000

    def __init__(self, namespace=None, main_window=None):
        QtWidgets.QGraphicsView.__init__(self)

        self.setScene(OrderedGraphicsScene(parent=self))

        self.namespace = namespace
        self.main_window = main_window
        self.setParent(self.main_window)

        # Scale view in Y for positive Y values (maya-like)
        self.scale(1, -1)

        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

        # Set selection mode
        self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemBoundingRect)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.scene_mouse_origin = QtCore.QPointF()
        self.drag_active = False
        self.pan_active = False
        self.zoom_active = False
        self.auto_frame_active = True

        # Disable scroll bars
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Set background color
        brush = QtGui.QBrush(QtGui.QColor(70, 70, 70, 255))
        self.setBackgroundBrush(brush)
        self.background_image = None
        self.background_image_path = None
        self.bg_ui = None

        self.fit_margin = 8

        # # undo list ---------------------------------------------------------
        self.undo_move_order = []
        self.undo_move_order_index = -1

    def get_center_pos(self):
        return self.mapToScene(
            QtCore.QPoint(self.width() / 2, self.height() / 2)
        )

    def mousePressEvent(self, event):
        self.modified_select = False
        self.item_selected = False
        self.__move_prompt = False
        QtWidgets.QGraphicsView.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.scene_mouse_origin = self.mapToScene(event.pos())
            # Get current viewport transformation
            transform = self.viewportTransform()
            scene_pos = self.mapToScene(event.pos())
            # Clear selection if no picker item below mouse
            picker_at = self.scene().picker_at(scene_pos, transform) or []
            if picker_at:
                if __EDIT_MODE__.get():
                    self.item_selected = True
                    # undo ---------------------------------------------------
                    self.__move_prompt = False
                    # open undo chunk
                    self.tmp_picker_pos_info = {}
                    pickers = self.scene().get_selected_items()
                    if picker_at not in pickers:
                        pickers.append(picker_at)
                    for picker in pickers:
                        pt = [picker.x(), picker.y(), picker.rotation()]
                        self.tmp_picker_pos_info[picker.uuid] = pt
                    # undo ---------------------------------------------------
                    if event.modifiers():
                        # this allows for shift selecting in edit
                        self.modified_select = False
                else:
                    self.modified_select = True
                    picker_widgets.select_picker_controls([picker_at], event)
            else:
                self.modified_select = False
                if not event.modifiers():
                    self.scene().clear_picker_selection()
                    cmds.select(cl=True)

        elif event.buttons() == QtCore.Qt.MouseButton.MiddleButton:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.pan_active = True
            self.scene_mouse_origin = self.mapToScene(event.pos())

        # zoom support added for the mouse, for those pen/tablet users
        elif (
            event.buttons() == QtCore.Qt.MouseButton.RightButton
            and event.modifiers() == QtCore.Qt.AltModifier
        ):
            self.zoom_active = True
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.scene_mouse_origin = self.mapToGlobal(event.pos())
            cursor_pos = QtGui.QVector2D(
                self.mapToGlobal(self.scene_mouse_origin)
            )
            screen = QtWidgets.QApplication.instance().primaryScreen()
            rect = screen.availableGeometry()
            self.top_left_pos = QtGui.QVector2D(rect.topLeft())
            self.zoom_delta = self.top_left_pos.distanceToPoint(cursor_pos)
            self.setTransformationAnchor(
                QtWidgets.QGraphicsView.AnchorViewCenter
            )

    def mouseMoveEvent(self, event):
        result = QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

        if (
            event.buttons() == QtCore.Qt.MouseButton.LeftButton
            and not self.item_selected
        ):
            self.drag_active = True

        # undo ---------------------------------------------------------------
        if (
            __EDIT_MODE__.get()
            and event.buttons() == QtCore.Qt.MouseButton.LeftButton
            and self.item_selected
        ):
            # confirm undo move chunck, a picker has been moved
            self.__move_prompt = True
        # undo ----------------------------------------------------------------

        if self.pan_active:
            current_center = self.get_center_pos()
            scene_paning = self.mapToScene(event.pos())

            new_center = current_center - (
                scene_paning - self.scene_mouse_origin
            )
            self.centerOn(new_center)

        if self.zoom_active:
            cursor_pos = QtGui.QVector2D(self.mapToGlobal(event.pos()))
            current_delta = self.top_left_pos.distanceToPoint(cursor_pos)

            factor = 1.05
            if current_delta < self.zoom_delta:
                factor = 0.95

            # Apply zoom
            self.scale(factor, factor)
            self.zoom_delta = current_delta

        return result

    def mouseReleaseEvent(self, event):
        """Overload to clear selection on empty area"""
        result = QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        if (
            not self.drag_active
            and event.button() == QtCore.Qt.MouseButton.LeftButton
            and not self.modified_select
        ):
            self.modified_select = False
            scene_pos = self.mapToScene(event.pos())

            # Get current viewport transformation
            transform = self.viewportTransform()

            # Clear selection if no picker item below mouse
            picker_at = self.scene().picker_at(scene_pos, transform) or []
            if not picker_at:
                if not event.modifiers():
                    self.scene().clear_picker_selection()
                    cmds.select(cl=True)
            elif picker_at and event.modifiers() == QtCore.Qt.AltModifier:
                picker_at.select_associated_controls()
                self.scene().select_picker_items([picker_at], event)
            else:
                self.scene().select_picker_items([picker_at], event)

        # add moved pickers to undo_move_order list ---------------------------
        if not self.drag_active and self.__move_prompt:
            for picker_uuid in list(self.tmp_picker_pos_info.keys()):
                picker = self.scene().get_picker_by_uuid(picker_uuid)
                if picker is None:
                    continue
                pt = [picker.x(), picker.y(), picker.rotation()]
                self.tmp_picker_pos_info[picker_uuid].extend(pt)
            if self.undo_move_order_index in [-1]:
                self.undo_move_order.append(
                    copy.deepcopy(self.tmp_picker_pos_info)
                )
            else:
                self.undo_move_order = self.undo_move_order[
                    : self.undo_move_order_index
                ]
                self.undo_move_order.append(
                    copy.deepcopy(self.tmp_picker_pos_info)
                )
            self.undo_move_order_index = -1
        self.__move_prompt = None
        self.tmp_picker_pos_info = {}
        # undo ----------------------------------------------------------------

        # Area selection
        if (
            self.drag_active
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            scene_drag_end = self.mapToScene(event.pos())

            sel_area = QtCore.QRectF(self.scene_mouse_origin, scene_drag_end)
            transform = self.viewportTransform()
            if not sel_area.size().isNull():
                items = self.scene().items(
                    sel_area,
                    QtCore.Qt.IntersectsItemShape,
                    QtCore.Qt.AscendingOrder,
                    deviceTransform=transform,
                )

                picker_items = []
                for item in items:
                    if not isinstance(item, picker_widgets.PickerItem):
                        continue
                    picker_items.append(item)
                if __EDIT_MODE__.get():
                    self.scene().select_picker_items(picker_items)
                    if event.modifiers() == QtCore.Qt.AltModifier:
                        ctrls = []
                        for x in picker_items:
                            ctrls.extend(x.get_controls())
                        cmds.select(cmds.ls(ctrls))
                else:
                    picker_widgets.select_picker_controls(picker_items, event)

        # Middle mouse view panning
        if (
            self.pan_active
            and event.button() == QtCore.Qt.MouseButton.MiddleButton
        ):
            current_center = self.get_center_pos()
            scene_drag_end = self.mapToScene(event.pos())

            new_center = current_center - (
                scene_drag_end - self.scene_mouse_origin
            )
            self.centerOn(new_center)
            self.pan_active = False
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        # zoom support added for the mouse, for those pen/tablet users
        if (
            self.zoom_active
            and event.button() == QtCore.Qt.MouseButton.RightButton
        ):
            self.zoom_active = False
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        self.drag_active = False
        return result

    def wheelEvent(self, event):
        """Wheel event to add zoom support"""
        if self.window().testAttribute(QtCore.Qt.WA_TransparentForMouseEvents):
            return False
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        # Run default event
        # QtWidgets.QGraphicsView.wheelEvent(self, event)

        # Define zoom factor
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 0.9

        # Apply zoom
        self.scale(factor, factor)

    # undo --------------------------------------------------------------------
    def undo_move(self):
        """go through (reversed) the undo_move_order list and move pickers
        back to their previously stored location
        """
        undo_len = len(self.undo_move_order)
        if undo_len == 0:
            return

        if self.undo_move_order_index == -1:
            self.undo_move_order_index = undo_len
        elif self.undo_move_order_index == 0:
            return
        if self.undo_move_order_index > 0:
            self.undo_move_order_index = self.undo_move_order_index - 1
        undo_items = self.undo_move_order[self.undo_move_order_index].items()
        for picker_uuid, undo_pos in undo_items:
            picker = self.scene().get_picker_by_uuid(picker_uuid)
            if not picker:
                continue
            picker.setPos(undo_pos[0], undo_pos[1])
            picker.setRotation(undo_pos[2])

    def redo_move(self):
        """go through the undo_move_order restoring picker locations"""
        undo_len = len(self.undo_move_order)
        if undo_len == 0:
            return

        if self.undo_move_order_index == -1:
            return
        if self.undo_move_order_index < undo_len:
            undo_index = self.undo_move_order[self.undo_move_order_index]
            for picker_uuid, undo_pos in undo_index.items():
                picker = self.scene().get_picker_by_uuid(picker_uuid)
                if not picker:
                    continue
                picker.setPos(undo_pos[3], undo_pos[4])
                picker.setRotation(undo_pos[5])
            self.undo_move_order_index = self.undo_move_order_index + 1
        else:
            self.undo_move_order_index = -1

    def keyPressEvent(self, event):
        """keyboard press event override for custom shortcuts

        Args:
            event (QtCore.QEvent): keyboard event
        """
        if __EDIT_MODE__.get():
            modifiers = event.modifiers()
            if (
                modifiers == QtCore.Qt.ControlModifier
                and event.key() == QtCore.Qt.Key_Z
            ):
                self.undo_move()
                event.accept()
            elif (
                modifiers == QtCore.Qt.ControlModifier
                and event.key() == QtCore.Qt.Key_Y
            ):
                self.redo_move()
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    # undo --------------------------------------------------------------------

    def contextMenuEvent(self, event, mapped_pos=None):
        """Right click menu options"""
        if event.modifiers() == QtCore.Qt.AltModifier:
            # alt may indicate zooming enabled so no menu
            return
        # Item area
        picker_item = [
            item for item in self.get_picker_items() if item._hovered
        ]
        if picker_item:
            # Run default method that call on childs
            mapped_pos = event.globalPos()
            evnt_type = QtGui.QContextMenuEvent.Mouse
            contextEvent = QtGui.QContextMenuEvent(evnt_type, mapped_pos)
            return picker_item[0].contextMenuEvent(contextEvent)

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Build Edit move options
        if __EDIT_MODE__.get():
            mapped_pos = self.mapToScene(event.pos())
            add_action = QtWidgets.QAction("Add Item", None)
            add_action.triggered.connect(
                partial(self.add_picker_item_gui, mapped_pos)
            )
            menu.addAction(add_action)

            add_action1 = QtWidgets.QAction("Add with selected", None)
            add_action1.triggered.connect(
                partial(self.add_picker_item_selected, mapped_pos)
            )
            menu.addAction(add_action1)

            add_action2 = QtWidgets.QAction("Add item per selected", None)
            add_action2.triggered.connect(
                partial(self.add_picker_item_per_selected, mapped_pos)
            )
            menu.addAction(add_action2)

            toggle_handles_action = QtWidgets.QAction(
                "Toggle all handles", None
            )
            func = self.toggle_all_handles_event
            toggle_handles_action.triggered.connect(func)
            menu.addAction(toggle_handles_action)

            menu.addSeparator()

            # this copy is currently only supported when not hovering a picker
            copy_action = QtWidgets.QAction("Copy (Multi)", None)
            copy_action.triggered.connect(self.copy_event)
            menu.addAction(copy_action)

            # this paste is only supported when not hovering
            paste_action = QtWidgets.QAction("Paste (Multi)", None)
            paste_action.triggered.connect(self.paste_event)
            menu.addAction(paste_action)

            menu.addSeparator()

            background_action = QtWidgets.QAction("Set background image", None)
            background_action.triggered.connect(self.set_background_event)
            menu.addAction(background_action)

            background_size_action = QtWidgets.QAction("Background Size", None)
            background_size_action.triggered.connect(self.background_options)
            menu.addAction(background_size_action)

            reset_background_action = QtWidgets.QAction(
                "Remove background", None
            )
            func = self.reset_background_event
            reset_background_action.triggered.connect(func)
            menu.addAction(reset_background_action)

            menu.addSeparator()

            msg = "Convert to nurbs curves"
            convert_picker_to_curves = QtWidgets.QAction(msg, None)
            func = self.convert_picker_to_curves
            convert_picker_to_curves.triggered.connect(func)
            menu.addAction(convert_picker_to_curves)

            msg = "Convert to picker data"
            convert_curves_to_picker = QtWidgets.QAction(msg, None)
            func = self.convert_curves_to_picker
            convert_curves_to_picker.triggered.connect(func)
            menu.addAction(convert_curves_to_picker)

            msg = "Delete picker nurbs curves"
            delete_extraction_grp = QtWidgets.QAction(msg, None)
            func = self.delete_extraction_grp
            delete_extraction_grp.triggered.connect(func)
            menu.addAction(delete_extraction_grp)

            menu.addSeparator()

        if __EDIT_MODE__.get_main():
            toggle_mode_action = QtWidgets.QAction("Toggle Mode", None)
            toggle_mode_action.triggered.connect(self.toggle_mode_event)
            menu.addAction(toggle_mode_action)

            menu.addSeparator()

        # Common actions
        reset_view_action = QtWidgets.QAction("Reset view", None)
        reset_view_action.triggered.connect(self.fit_scene_content)
        menu.addAction(reset_view_action)
        frame_selection_view_action = QtWidgets.QAction(
            "Frame Selection", None
        )
        frame_selection_view_action.triggered.connect(
            self.fit_selection_content
        )
        menu.addAction(frame_selection_view_action)

        auto_frame_selection_view_action = QtWidgets.QAction(
            "Auto Frame view", None
        )
        auto_frame_selection_view_action.setCheckable(True)
        auto_frame_selection_view_action.setChecked(self.auto_frame_active)
        auto_frame_selection_view_action.triggered.connect(
            self.set_auto_frame_view
        )
        menu.addAction(auto_frame_selection_view_action)

        # Open context menu under mouse
        menu.exec_(event.globalPos())

    def resizeEvent(self, *args, **kwargs):
        """Overload to force scale scene content to fit view"""
        # Fit scene content to view
        if self.auto_frame_active:
            self.fit_scene_content()

        # Run default resizeEvent
        return QtWidgets.QGraphicsView.resizeEvent(self, *args, **kwargs)

    def fit_scene_content(self):
        """Will fit scene content to view, by scaling it"""
        scene_rect = self.scene().get_bounding_rect(margin=self.fit_margin)
        self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)

    def set_auto_frame_view(self):
        """Enable auto fit when a resize event happens"""
        # Fit scene content to view
        if not self.auto_frame_active:
            self.fit_scene_content()
        self.auto_frame_active = not self.auto_frame_active

    def fit_selection_content(self):
        """Will fit the selected item to view, by scaling it"""
        scene_rect = self.scene().get_bounding_rect(
            margin=self.fit_margin, selection=True
        )
        if scene_rect:
            self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)

    def get_color_picker_override(self, picker, ctrl):
        """Get the maya override color and return picker equivelant

        Args:
            picker (PickerItem): pickeritem class
            ctrl (str): name of the control

        Returns:
            list: [R, G, B, Alpha]
        """
        node = ctrl
        if cmds.nodeType(ctrl) == "transform":
            node = cmds.listRelatives(ctrl, shapes=True)[0]
        if not cmds.getAttr("{}.overrideEnabled".format(node)):
            return [0, 0, 0, 255]
        if cmds.getAttr("{}.overrideRGBColors".format(node)):
            r_color = cmds.getAttr("{}.overrideColorR".format(node))
            g_color = cmds.getAttr("{}.overrideColorG".format(node))
            b_color = cmds.getAttr("{}.overrideColorB".format(node))
            return [r_color * 255, g_color * 255, b_color * 255, 255]
        else:
            override_index = cmds.getAttr("{}.overrideColor".format(node))
            color_rgb = MAYA_OVERRIDE_COLOR[override_index]
            return [color_rgb[0], color_rgb[1], color_rgb[2], 255]

    def add_picker_item(self, event=None):
        """Add new PickerItem to current view"""
        ctrl = picker_widgets.PickerItem(
            main_window=self.main_window, namespace=self.namespace
        )
        ctrl.setParent(self)
        self.scene().addItem(ctrl)

        # Move ctrl
        if event:
            ctrl.setPos(event.pos())
        else:
            ctrl.setPos(0, 0)

        return ctrl

    def add_picker_item_gui(self, mouse_pos=None):
        """Create picker item at the position of the mouse

        Args:
            mouse_pos (QPosition, optional): mouse position
        """
        ctrl = self.add_picker_item()
        ctrl.setPos(mouse_pos)

    def add_picker_item_selected(self, mouse_pos=None):
        """Add new PickerItem to current view"""
        ctrl = self.add_picker_item()
        data = {}
        selected = cmds.ls(sl=True) or []
        data["controls"] = selected
        ctrl.set_data(data)
        ctrl.set_selected_state(True)
        if selected:
            colors_rgb = self.get_color_picker_override(ctrl, selected[0])
            ctrl.set_color(color=colors_rgb)
        if mouse_pos:
            ctrl.setPos(mouse_pos)

        return ctrl

    def add_picker_item_per_selected(self, mouse_pos=None):
        """Add new PickerItem to current view"""
        selection = cmds.ls(sl=True) or []
        if not selection:
            return
        created_ctrls = []
        if mouse_pos:
            x_start = mouse_pos.x()
            y_start = mouse_pos.y()
        else:
            x_start = 0
            y_start = 0
        y_increment = -35
        for selected in selection:
            ctrl = self.add_picker_item()
            data = {}
            data["controls"] = [selected]
            data["position"] = [x_start, y_start]
            colors_rgb = self.get_color_picker_override(ctrl, selected)
            ctrl.set_color(color=colors_rgb)
            y_start = y_start + y_increment
            ctrl.set_data(data)
            ctrl.set_selected_state(True)
            created_ctrls.append(ctrl)

        return created_ctrls

    def copy_event(self):
        """reset the clipboard and populate the list with picker data for paste"""
        global _CLIPBOARD
        _CLIPBOARD = []
        selected_pickers = self.scene().get_selected_items()
        for picker in selected_pickers:
            _CLIPBOARD.append(picker.get_data())

    def paste_event(self):
        """create new anim pickers based off the data in the clipboard
        Make new pickers selected
        """
        global _CLIPBOARD
        [
            x.set_selected_state(False)
            for x in self.scene().get_selected_items()
        ]
        for data in _CLIPBOARD:
            ctrl = self.add_picker_item(event=None)
            ctrl.set_data(data)
            ctrl.set_selected_state(True)

    def toggle_all_handles_event(self, event=None):
        new_status = None
        for item in list(self.scene().items()):
            # Skip non picker items
            if not isinstance(item, picker_widgets.PickerItem):
                continue

            # Get first status
            if new_status is None:
                new_status = not item.get_edit_status()

            # Set item status
            item.set_edit_status(new_status)

    def toggle_mode_event(self, event=None):
        """Will toggle UI edition mode"""
        if not self.main_window:
            return

        # Check for possible data change/loss
        if __EDIT_MODE__.get():
            if not self.main_window.check_for_data_change():
                return

        # Toggle mode
        __EDIT_MODE__.toggle()

        # Reset size to default
        self.main_window.reset_default_size()
        self.main_window.refresh()

    def apply_background_fallback_logic(self, path):
        # test if the original path exists
        if os.path.exists(path):
            return path
        # check the data node for the "source_file_path" that is added when
        # pkr is loaded from file
        data = self.window().get_current_data_node().read_data_from_node()
        pkr_path = data.get("source_file_path", None)
        if not pkr_path or pkr_path is None:
            return path
        # looking in the neighboring directories for images dir
        pkr_dir = os.path.dirname(pkr_path)
        rel_path_token = os.environ.get(
            ANIM_PICKER_RELATIVE_IMAGES, DEFAULT_RELATIVE_IMAGES_PATH
        )
        base_name = os.path.basename(path)
        relative_image_path = os.path.realpath(
            os.path.join(pkr_dir, rel_path_token, base_name)
        )
        # only return if path exists
        if os.path.exists(relative_image_path):
            return relative_image_path
        else:
            return path

    def set_background(self, path=None):
        """Set tab index widget background image"""
        if not path:
            return
        path = os.path.abspath(r"{}".format(path))
        path = self.apply_background_fallback_logic(path)
        # Check that path exists
        if not (path and os.path.exists(path)):
            mgear.log(
                "anim_picker: background image not found: '{}'".format(path),
                mgear.sev_warning,
            )
            return

        self.background_image_path = path

        # Load image and mirror it vertically
        self.background_image = QtGui.QImage(path).mirrored(False, True)

        # Set scene size to background picture
        width = self.background_image.width()
        height = self.background_image.height()

        self.scene().set_size(width, height)

        # Update display
        self.fit_scene_content()

    def background_options(self):
        tabWidget = self.parent().parent()
        # Delete old window
        if self.bg_ui:
            try:
                self.bg_ui.close()
                self.bg_ui.deleteLater()
            except Exception:
                pass
        if not tabWidget.currentWidget().get_background(0):
            cmds.warning("Current view has no background!")
            return
        self.bg_ui = basic.BackgroundOptionsDialog(tabWidget, self)
        self.bg_ui.show()
        self.bg_ui.raise_()

    def set_background_event(self, event=None):
        """Set background image pick dialog window"""
        # Open file dialog
        img_dir = basic.get_images_folder_path()
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Pick a background", img_dir
        )

        # Filter return result (based on qt version)
        if isinstance(file_path, tuple):
            file_path = file_path[0]

        # Abort on cancel
        if not file_path:
            return

        # Set background
        self.set_background(file_path)

    def reset_background_event(self, event=None):
        """Reset background to default"""
        self.background_image = None
        self.background_image_path = None
        self.scene().set_default_size()

        # Update display
        self.fit_scene_content()

    def resize_background_image(
        self, width, height, keepAspectRatio=False, auto_update=True
    ):
        """resize the background image if one is set

        Args:
            width (int): desired width
            height (int): desired height
            keepAspectRatio (bool, optional): scale image to fit aspect ratio
            auto_update (bool, optional): update the scene view

        Returns:
            None: none
        """
        if not self.background_image:
            return

        current_width = self.background_image.size().width()
        current_height = self.background_image.size().height()
        if current_width == width and current_height == height:
            return

        if keepAspectRatio:
            if current_width != width:
                aspect_size = self.background_image.scaledToWidth(width).size()
                width, height = aspect_size.width(), aspect_size.height()
            elif current_height != height:
                aspect_size = self.background_image.scaledToHeight(
                    height
                ).size()
                width, height = aspect_size.width(), aspect_size.height()
        # TODO find if this is the most efficient way to achieve this
        self.background_image = self.background_image.scaled(width, height)

        if auto_update:
            self.scene().set_size(width, height)
            # Update display
            self.fit_scene_content()

    def set_background_width(self, width, keepAspectRatio=True):
        """convenience function for setting width on bg image

        Args:
            width (int): desired width
            keepAspectRatio (bool, optional): force aspect ration

        Returns:
            None: None
        """
        if not self.background_image:
            return
        current_height = self.background_image.size().height()
        self.resize_background_image(
            width, current_height, keepAspectRatio=keepAspectRatio
        )

    def set_background_height(self, height, keepAspectRatio=True):
        """convenience function for setting height on bg image

        Args:
            height (int): desired height
            keepAspectRatio (bool, optional): force aspect ration

        Returns:
            None: None
        """
        if not self.background_image:
            return
        current_width = self.background_image.size().width()
        self.resize_background_image(
            current_width, height, keepAspectRatio=keepAspectRatio
        )

    def get_background_size(self):
        """get bg image in Qt.QSize

        Returns:
            Qt.QSize: current size of bg
        """
        bg_image = self.get_background(0)
        if bg_image:
            return bg_image.size()
        else:
            return QtCore.QSize(0, 0)

    def get_background(self, index):
        """Return background for tab index"""
        return self.background_image

    def clear(self):
        """Clear view, by replacing scene with a new one"""
        old_scene = self.scene()
        self.setScene(OrderedGraphicsScene(parent=self))
        old_scene.deleteLater()

    def get_picker_items(self):
        """Return scene picker items in proper order (back to front)"""
        items = []
        for item in list(self.scene().items()):
            # Skip non picker graphic items
            if not isinstance(item, picker_widgets.PickerItem):
                continue

            # Add picker item to filtered list
            items.append(item)

        # Reverse list order (to return back to front)
        items.reverse()

        return items

    def get_data(self):
        """Return view data"""
        data = {}

        # Add background to data
        if self.background_image_path:
            bg_fp = r"{}".format(self.background_image_path)
            data["background"] = bg_fp
            data["background_size"] = self.get_background_size().toTuple()

        # Add items to data
        items = []
        for item in self.get_picker_items():
            items.append(item.get_data())
        if items:
            data["items"] = items

        return data

    def set_data(self, data):
        """Set/load view data"""
        self.clear()

        # Set backgraound picture
        background = data.get("background", None)
        background_size = data.get("background_size", None)
        if background:
            self.set_background(background)
            if background_size:
                self.resize_background_image(
                    background_size[0], background_size[1]
                )

        # Add items to view
        for item_data in data.get("items", []):
            item = self.add_picker_item()
            item.set_data(item_data)

    def drawBackground(self, painter, rect):
        """Default method override to draw view custom background image"""
        # Run default method
        result = QtWidgets.QGraphicsView.drawBackground(self, painter, rect)

        # Stop here if view has no background
        if not self.background_image:
            return result

        # Draw background image
        painter.drawImage(
            self.sceneRect(),
            self.background_image,
            QtCore.QRectF(self.background_image.rect()),
        )

        return result

    def drawForeground(self, painter, rect):
        """Default method override to draw origin axis in edit mode"""
        # Run default method
        result = QtWidgets.QGraphicsView.drawForeground(self, painter, rect)

        # Paint axis in edit mode
        if __EDIT_MODE__.get():
            self.draw_overlay_axis(painter, rect)

        return result

    def draw_overlay_axis(self, painter, rect):
        """Draw x and y origin axis"""
        # Set Pen
        pen = QtGui.QPen(
            QtGui.QColor(160, 160, 160, 120), 1, QtCore.Qt.DashLine
        )
        painter.setPen(pen)

        # Get event rect in scene coordinates
        # Draw x line
        if rect.y() < 0 and (rect.height() - rect.y()) > 0:
            x_line = QtCore.QLine(rect.x(), 0, rect.width() + rect.x(), 0)
            painter.drawLine(x_line)

        # Draw y line
        if rect.x() < 0 and (rect.width() - rect.x()) > 0:
            y_line = QtCore.QLineF(0, rect.y(), 0, rect.height() + rect.y())
            painter.drawLine(y_line)

    def convert_picker_to_curves(self):
        """Convert the pickernodes from the view into maya curves for easier
        editing.

        Returns:
            n/a: n/a

        http://forum.mgear-framework.com/t/sharing-a-couple-of-functions-i-wrote-for-anim-picker/1717
        """
        data = self.main_window.get_character_data()

        tab_index = self.main_window.tab_widget.currentIndex()
        tab_name = self.main_window.tab_widget.tabText(tab_index)

        tab = None
        # only focus on the current tab
        for _tab in data["tabs"]:
            if _tab["name"] == tab_name:
                tab = _tab
        if not tab:
            cmds.warning("No data in picker tab: {}".format(tab_name))
            return

        # lets not create multiple picker group nodes
        if pm.objExists(PICKER_EXTRACTION_NAME):
            grp = pm.PyNode(PICKER_EXTRACTION_NAME)
        else:
            grp = pm.group(em=True, n=PICKER_EXTRACTION_NAME)
            attribute.lockAttribute(grp)

        # Delete a previous extraction group for this tab, matched by the
        # stored tab name rather than the node name: Maya may rename the group
        # (e.g. "default" -> "default1", or spaces -> "_"), so the node name is
        # not a reliable key.
        for existing in grp.listRelatives() or []:
            if (
                pm.hasAttr(existing, "tabName")
                and existing.tabName.get() == tab["name"]
            ):
                pm.delete(existing)
        picker_grp = pm.group(em=True, n=tab["name"], p=grp)
        # Store the real tab name so the round-trip does not depend on the
        # (possibly Maya-mangled) group node name.
        attribute.addAttribute(picker_grp, "tabName", "string", tab["name"])
        picker_grp.sy >> picker_grp.sx
        attribute.lockAttribute(
            picker_grp, ["tz", "rx", "ry", "rz", "sx", "sz", "v"]
        )

        if "background" in tab["data"]:
            attribute.addAttribute(
                picker_grp,
                "backgroundAlpha",
                "float",
                0.5,
                minValue=0,
                maxValue=1,
            )
            attribute.addAttribute(
                picker_grp,
                "backgroundWidth",
                "long",
                tab["data"]["background_size"][0],
                minValue=1,
            )
            attribute.addAttribute(
                picker_grp,
                "backgroundHeight",
                "long",
                tab["data"]["background_size"][1],
                minValue=1,
            )
            ip = pm.imagePlane(n="{}_background".format(tab["name"]))
            ip[0].tz.set(-1)
            ip[0].overrideEnabled.set(1)
            ip[0].overrideDisplayType.set(2)
            pm.parent(ip[0], picker_grp)

            picker_grp.backgroundAlpha >> ip[1].alphaGain
            picker_grp.backgroundWidth >> ip[1].width
            picker_grp.backgroundHeight >> ip[1].height

            ip[1].imageName.set(tab["data"]["background"])

        if "items" in tab["data"]:
            for item in tab["data"]["items"]:
                handles = item["handles"]
                pos_x, pos_y = item["position"]
                rot_z = item["rotation"]

                if len(handles) > 2:
                    item_curve = pm.circle(
                        d=1, s=len(item["handles"]), ch=False
                    )[0]

                    for i, (x, y) in enumerate(handles):
                        item_curve.getShape().controlPoints[i].set(x, y, 0)
                    item_curve.getShape().controlPoints[i + 1].set(
                        handles[0][0], handles[0][1], 0
                    )

                # special case for circles
                elif len(handles) == 2:
                    item_curve = pm.curve(
                        p=[
                            [handles[0][0], handles[0][1], 0.0],
                            [handles[1][0], handles[1][1], 0.0],
                        ],
                        d=1,
                    )
                    poci = pm.createNode("pointOnCurveInfo")
                    item_curve.getShape().worldSpace >> poci.inputCurve
                    curve_len = pm.arclen(item_curve, ch=True)

                    display_curve = pm.circle(d=3, s=6, ch=False)[0]
                    pm.parent(display_curve, item_curve)
                    display_curve.getShape().overrideEnabled.set(1)
                    display_curve.getShape().overrideDisplayType.set(2)
                    display_curve.inheritsTransform.set(0)

                    curve_len.arcLength >> display_curve.sx
                    curve_len.arcLength >> display_curve.sy
                    curve_len.arcLength >> display_curve.sz
                    poci.position >> display_curve.t

                pm.parent(item_curve, picker_grp)

                q_color = QtGui.QColor(*item["color"])
                attribute.addColorAttribute(
                    item_curve, "color", q_color.getRgbF()[:3]
                )
                attribute.addAttribute(
                    item_curve,
                    "alpha",
                    "long",
                    item["color"][3],
                    minValue=0,
                    maxValue=255,
                )

                item_curve.t.set(pos_x, pos_y, 0)
                item_curve.rz.set(rot_z)
                item_curve.displayHandle.set(1)
                item_curve.getShape().dispCV.set(1)
                item_curve.overrideEnabled.set(1)
                item_curve.overrideRGBColors.set(1)
                item_curve.color >> item_curve.overrideColorRGB
                item_curve.scalePivot >> item_curve.selectHandle
                attribute.lockAttribute(
                    item_curve, ["tz", "rx", "ry", "sz", "v"]
                )

                # this will save all the data that is not needed for display
                # purposes to an attr
                ignore_list = ("position", "rotation", "handles", "color")
                item_data = {}

                for key in item.keys():
                    if key not in ignore_list:
                        item_data[key] = item[key]

                if item_data:
                    attribute.addAttribute(
                        item_curve, "itemData", "string", json.dumps(item_data)
                    )
                    item_curve.itemData.set(lock=True)

    def delete_extraction_grp(self):
        """delete extraction group"""
        try:
            pm.delete(PICKER_EXTRACTION_NAME)
        except Exception as e:
            mgear.log(
                "anim_picker: failed to delete extraction group: "
                "{}".format(e),
                mgear.sev_warning,
            )

    def convert_curves_to_picker(self):
        """get the information from the created picker curves and reset the
        information on the picker data node the anim picker operates on
        """
        grp = pm.PyNode(PICKER_EXTRACTION_NAME)
        new_data = {"tabs": []}

        for tab_grp in grp.listRelatives():
            # Recover the real tab name (the group node may have been renamed
            # by Maya, e.g. "default" -> "default1").
            if pm.hasAttr(tab_grp, "tabName"):
                tab_name = tab_grp.tabName.get()
            else:
                tab_name = tab_grp.name()
            new_data["tabs"].append({"name": tab_name})
            new_data["tabs"][-1]["data"] = {"items": []}
            bg_imagePlane = tab_grp.listRelatives(type="imagePlane", ad=True)

            if bg_imagePlane:
                image_name = bg_imagePlane[0].imageName.get()
                new_data["tabs"][-1]["data"]["background"] = image_name
                new_data["tabs"][-1]["data"]["background_size"] = [
                    bg_imagePlane[0].width.get(),
                    bg_imagePlane[0].height.get(),
                ]

            for item_curve in tab_grp.listRelatives():
                shape = item_curve.getShape()
                if shape is None or shape.type() == "imagePlane":
                    continue

                item_data = {}

                # color
                q_color = QtGui.QColor()
                q_color.setRgbF(*item_curve.color.get())
                q_color.setAlpha(item_curve.alpha.get())
                item_data["color"] = q_color.getRgb()

                # position and rotation
                item_piv = pm.dt.Point(
                    item_curve.getPivots(worldSpace=True)[0]
                )
                piv_offset = item_piv * item_curve.worldInverseMatrix.get()
                item_pos = item_piv * tab_grp.worldInverseMatrix.get()

                item_data["position"] = [item_pos.x, item_pos.y]
                item_data["rotation"] = item_curve.rz.get()

                # handles
                handles = []
                item_scale = [item_curve.sx.get(), item_curve.sy.get()]
                for cv in item_curve.cv:
                    x, y = cv.getPosition(space="object")[:2]
                    handles.append(
                        [
                            (x - piv_offset.x) * item_scale[0],
                            (y - piv_offset.y) * item_scale[1],
                        ]
                    )

                # if the first and last points are the same then ignore the
                # last one.
                if handles[0] == handles[-1]:
                    handles = handles[:-1]
                item_data["handles"] = handles

                if pm.hasAttr(item_curve, "itemData"):
                    item_data.update(json.loads(item_curve.itemData.get()))

                new_data["tabs"][-1]["data"]["items"].append(item_data)

        data_node = self.main_window.get_current_data_node()
        if not (data_node and data_node.exists()):
            return True
        data = self.main_window.get_character_data()
        # update original data to avoid deletion of the non edited tabs
        # Create a lookup dictionary for fast matching
        new_data_lookup = {d["name"]: d for d in new_data["tabs"] if "name" in d}

        # Surface converted tabs that don't match any current picker tab, so
        # the merge below does not silently drop their edited data.
        current_names = {
            d.get("name") for d in data.get("tabs", []) if "name" in d
        }
        for converted_name in new_data_lookup:
            if converted_name not in current_names:
                mgear.log(
                    "anim_picker: converted tab '{}' has no matching tab in "
                    "the current picker; its data was not applied".format(
                        converted_name
                    ),
                    mgear.sev_warning,
                )

        # Replace the matching dictionaries in data
        updated_data = {"tabs": []}
        updated_data["tabs"] = [
            new_data_lookup.get(d.get("name"), d) if "name" in d else d
            for d in data["tabs"]
        ]
        # Write through the DataNode chokepoint (JSON + version stamp +
        # lock handling all centralized in picker_node.py)
        data_node.set_data(updated_data)
        data_node.write_data(to_node=True)

        self.main_window.refresh()
