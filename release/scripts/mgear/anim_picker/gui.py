from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# python
import os
import copy
import json
from functools import partial

# dcc
from maya import cmds
import mgear.pymaya as pm

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# mgear
import mgear
from mgear.core import pyqt
from mgear.core import attribute
from mgear.core import callbackManager


from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore

# from mgear.vendor.Qt import QtOpenGL
from mgear.vendor.Qt import QtCompat
from mgear.vendor.Qt import QtWidgets

# debugging
# from PySide2 import QtGui
# from PySide2 import QtCore
# from PySide2 import QtOpenGL
# from PySide2 import QtWidgets

# module
from . import menu
from . import version
from . import picker_node
from .widgets import basic
from .widgets import picker_widgets
from .widgets import overlay_widgets

from .handlers import __EDIT_MODE__
from .handlers import __SELECTION__

# constants -------------------------------------------------------------------
try:
    _CLIPBOARD
except NameError as e:
    _CLIPBOARD = []

ANIM_PICKER_TITLE = "动画选择器 {ap_version} | mGear {m_version}"

# maya color index
MAYA_OVERRIDE_COLOR = {
    0: [48, 48, 48],
    1: [0, 0, 0],
    2: [13, 13, 13],
    3: [81, 81, 81],
    4: [84, 0, 5],
    5: [0, 0, 30],
    6: [0, 0, 255],
    7: [0, 16, 2],
    8: [5, 0, 14],
    9: [147, 0, 147],
    10: [65, 17, 8],
    11: [13, 4, 3],
    12: [81, 5, 0],
    13: [255, 0, 0],
    14: [0, 255, 0],
    15: [0, 13, 81],
    16: [255, 255, 255],
    17: [255, 255, 0],
    18: [32, 183, 255],
    19: [14, 255, 93],
    20: [255, 111, 111],
    21: [198, 105, 49],
    22: [255, 255, 32],
    23: [0, 81, 23],
    24: [91, 37, 8],
    25: [87, 91, 8],
    26: [35, 91, 8],
    27: [8, 91, 28],
    28: [8, 91, 91],
    29: [8, 35, 91],
    30: [41, 8, 91],
    31: [91, 8, 37],
}

GROUPBOX_BG_CSS = """QGroupBox {{
      background-color: rgba{color};
      border: 0px solid rgba{color};
}}"""


_mgear_version = mgear.getVersion()

PICKER_EXTRACTION_NAME = "pickerData_extraction"
ANIM_PICKER_RELATIVE_IMAGES = "ANIM_PICKER_RELATIVE_IMAGES"

"""
/animpickers/characterA/publish/pkr/charact.pkr
/animpickers/characterA/publish/pkr/../images
examples "../images", "../../images", ""
"""
# default image location is assumed same as .pkr file
DEFAULT_RELATIVE_IMAGES_PATH = ""


# =============================================================================
# Classes
# =============================================================================


class APPassthroughEventFilter(QtCore.QObject):
    """AnimPicker eventFilter for MayaMainWindow when enabling
    click passthrough for the GUI.
    """

    # Animpicker gui reference
    APUI = None

    def eventFilter(self, QObject, event):
        """Filter for changing the windowFlags on the animPicker gui"""
        modifiers = None
        if QtCompat.isValid(self.APUI):
            modifiers = QtWidgets.QApplication.queryKeyboardModifiers()
            auto_state = self.APUI.auto_opacity_btn.isChecked()
            flag_state = self.APUI.testAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents
            )
            if auto_state and modifiers == QtCore.Qt.ShiftModifier:
                # if the window is passthrough enabled
                if flag_state:
                    pos = QtGui.QCursor().pos()
                    widgetRect = self.APUI.geometry()
                    if widgetRect.contains(pos):
                        self.APUI.set_mouseEvent_passthrough(False)
                # if the window is passthrough enabled and the feature disabled
            elif flag_state and not menu.get_option_var_passthrough_state():
                self.APUI.set_mouseEvent_passthrough(False)
            else:
                pass
        else:
            try:
                self.deleteLater()
            except RuntimeError:
                pass
        return super(APPassthroughEventFilter, self).eventFilter(
            QObject, event
        )


class OrderedGraphicsScene(QtWidgets.QGraphicsScene):
    """
    Custom QGraphicsScene with x/y axis line options for origin
    feedback in edition mode
    (provides a center reference to work from, view will fit what ever
    is the content in use mode).

    Had to add z_index support since there was a little z
    conflict when "moving" items to back/front in edit mode
    """

    __DEFAULT_SCENE_WIDTH__ = 6000
    __DEFAULT_SCENE_HEIGHT__ = 6000

    def __init__(self, parent=None):
        QtWidgets.QGraphicsScene.__init__(self, parent=parent)

        self.set_default_size()
        self._z_index = 0

    def set_size(self, width, heith):
        """Will set scene size with proper center position"""
        self.setSceneRect(-width / 2, -heith / 2, width, heith)

    def set_default_size(self):
        self.set_size(
            self.__DEFAULT_SCENE_WIDTH__, self.__DEFAULT_SCENE_HEIGHT__
        )

    def get_bounding_rect(self, margin=0, selection=False):
        """
        Return scene content bounding box with specified margin
        Warning: In edit mode, will return default scene rectangle
        """
        # Return default size in edit mode
        # if __EDIT_MODE__.get():
        #     return self.sceneRect()

        # Get item boundingBox
        if selection:
            sel_items = self.get_selected_items()
            if not sel_items:
                return
            scene_rect = QtCore.QRectF()

            # init coordinates with the first element
            rec = sel_items[0].boundingRect().getCoords()
            x1 = rec[0] + sel_items[0].x()
            y1 = rec[1] + sel_items[0].y()
            x2 = rec[2] + sel_items[0].x()
            y2 = rec[3] + sel_items[0].y()

            for item in sel_items[1:]:
                rec = item.boundingRect().getCoords()
                if (rec[0] + item.x()) < x1:
                    x1 = rec[0] + item.x()
                if (rec[1] + item.y()) < y1:
                    y1 = rec[1] + item.y()
                if (rec[2] + item.x()) > x2:
                    x2 = rec[2] + item.x()
                if (rec[3] + item.y()) > y2:
                    y2 = rec[3] + item.y()
            scene_rect.setCoords(x1, y1, x2, y2)

        else:
            scene_rect = self.itemsBoundingRect()

        # Stop here if no margin
        if not margin:
            return scene_rect

        # Add margin
        scene_rect.setX(scene_rect.x() - margin)
        scene_rect.setY(scene_rect.y() - margin)
        scene_rect.setWidth(scene_rect.width() + margin)
        scene_rect.setHeight(scene_rect.height() + margin)

        return scene_rect

    def clear(self):
        """Reset default z index on clear"""
        QtWidgets.QGraphicsScene.clear(self)
        self._z_index = 0

    def set_picker_items(self, items):
        """Will set picker items"""
        self.clear()
        for item in items:
            QtWidgets.QGraphicsScene.addItem(self, item)
            self.set_z_value(item)
        self.add_axis_lines()

    def get_picker_items(self):
        """Will return all scenes' picker items"""
        picker_items = []
        # Filter picker items (from handles etc)
        for item in list(self.items()):
            if not isinstance(item, picker_widgets.PickerItem):
                continue
            picker_items.append(item)
        return picker_items

    def picker_at(self, scene_pos, transform):
        item_at = self.itemAt(scene_pos, transform)
        if isinstance(item_at, picker_widgets.PickerItem):
            return item_at
        elif item_at and not isinstance(item_at, picker_widgets.PickerItem):
            return item_at.parentItem()
        else:
            return None

    def get_picker_by_uuid(self, picker_uuid):
        """pickers have UUID's for hashing in dictionaries. search via uuid

        Args:
            picker_uuid (str): uuid

        Returns:
            PickerIteem: instance of matching picker
        """
        for picker in self.get_picker_items():
            if picker.uuid == picker_uuid:
                return picker
        return None

    def get_selected_items(self):
        return [
            item for item in self.get_picker_items() if item.polygon.selected
        ]

    def clear_picker_selection(self):
        for picker in self.get_picker_items():
            picker.set_selected_state(False)
        self.update()

    def select_picker_items(self, picker_items, event=None):
        if event is None:
            modifiers = None
        else:
            modifiers = event.modifiers()

        # Shift cases (toggle)
        if modifiers == QtCore.Qt.ShiftModifier:
            for picker in picker_items:
                picker.set_selected_state(True)

        # Controls case
        elif modifiers == QtCore.Qt.ControlModifier:
            for picker in picker_items:
                picker.set_selected_state(False)

        # Alt case (remove)
        # elif modifiers == QtCore.Qt.AltModifier:
        else:
            self.clear_picker_selection()
            for picker in picker_items:
                picker.set_selected_state(True)

    def set_z_value(self, item):
        """set proper z index for item"""
        item.setZValue(self._z_index)
        self._z_index += 1

    def addItem(self, item):
        """Overload to keep axis on top"""
        QtWidgets.QGraphicsScene.addItem(self, item)
        self.set_z_value(item)


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

        # Open GL render, to check...
        # if basic.__USE_OPENGL__:
        #     # make that view use OpenGL
        #     gl_format = QtOpenGL.QGLFormat()
        #     gl_format.setSampleBuffers(True)
        #     gl_widget = QtOpenGL.QGLWidget(gl_format)

        #     # use the GL widget for viewing
        #     self.setViewport(gl_widget)

        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

        # TODO
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
            print("# background image not found: '{}'".format(path))
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
            data["background"] = json.dumps(bg_fp).replace('"', "")
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

        # deletes existing tab group and recreates it
        if pm.objExists(tab["name"]):
            pm.delete(tab["name"])
        picker_grp = pm.group(em=True, n=tab["name"], p=grp)
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
            print(e)

    def convert_curves_to_picker(self):
        """get the information from the created picker curves and reset the
        information on the picker data node the anim picker operates on
        """
        grp = pm.PyNode(PICKER_EXTRACTION_NAME)
        new_data = {"tabs": []}

        for tab_grp in grp.listRelatives():
            new_data["tabs"].append({"name": tab_grp.name()})
            new_data["tabs"][-1]["data"] = {"items": []}
            bg_imagePlane = tab_grp.listRelatives(type="imagePlane", ad=True)

            if bg_imagePlane:
                image_name = bg_imagePlane[0].imageName.get()
                new_data["tabs"][-1]["data"]["background"] = image_name
                new_data["tabs"][-1]["data"]["background_size"] = [
                    bg_imagePlane[0].width.get(),
                    bg_imagePlane[0].height.get(),
                ]

            for item_curve in [
                ic
                for ic in tab_grp.listRelatives()
                if ic.getShape().type() != "imagePlane"
            ]:
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

        # Replace the matching dictionaries in data
        updated_data = {"tabs": []}
        updated_data["tabs"] = [
            new_data_lookup.get(d.get("name"), d) if "name" in d else d
            for d in data["tabs"]
        ]
        data_node = pm.PyNode(str(data_node))
        data_node.picker_datas.set(lock=False)
        data_node.picker_datas.set(
            json.dumps(updated_data).replace("true", "True")
        )
        data_node.picker_datas.set(lock=True)

        self.main_window.refresh()


class ContextMenuTabWidget(QtWidgets.QTabWidget):
    """Custom tab widget with specific context menu support"""

    def __init__(self, parent, main_window=None, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, parent, *args, **kwargs)
        self.main_window = main_window

    def contextMenuEvent(self, event):
        """Right click menu options"""
        # Abort out of edit mode
        if not __EDIT_MODE__.get():
            return

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Build context menu
        rename_action = QtWidgets.QAction("Rename", None)
        rename_action.triggered.connect(self.rename_event)
        menu.addAction(rename_action)

        add_action = QtWidgets.QAction("Add Tab", None)
        add_action.triggered.connect(self.add_tab_event)
        menu.addAction(add_action)

        remove_action = QtWidgets.QAction("Remove Tab", None)
        remove_action.triggered.connect(self.remove_tab_event)
        menu.addAction(remove_action)

        move_forward_action = QtWidgets.QAction("Move Tab >>>", None)
        move_forward_action.triggered.connect(self.move_forward_tab_event)
        menu.addAction(move_forward_action)

        move_back_action = QtWidgets.QAction("Move Tab <<<", None)
        move_back_action.triggered.connect(self.move_back_tab_event)
        menu.addAction(move_back_action)

        # Open context menu under mouse
        menu.exec_(self.mapToGlobal(event.pos()))

    def fit_contents(self):
        """Will resize views content to match views size"""
        for i in range(self.count()):
            widget = self.widget(i)
            if not isinstance(widget, GraphicViewWidget):
                continue
            widget.fit_scene_content()

    def move_back_tab_event(self):
        current_index = self.currentIndex()
        if current_index > 0:
            self.tabBar().moveTab(current_index, current_index - 1)
            self.setCurrentIndex(current_index - 1)

    def move_forward_tab_event(self):
        current_index = self.currentIndex()
        if current_index < self.count() - 1:
            self.tabBar().moveTab(current_index, current_index + 1)
            self.setCurrentIndex(current_index + 1)

    def rename_event(self):
        """Will open dialog to rename tab"""
        # Get current tab index
        index = self.currentIndex()

        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Tab name",
            "New name",
            QtWidgets.QLineEdit.Normal,
            self.tabText(index),
        )
        if not (ok and name):
            return

        # Update influence name
        self.setTabText(index, name)

    def add_tab_event(self):
        """Will open dialog to get tab name and create a new tab"""
        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create new tab", "Tab name", QtWidgets.QLineEdit.Normal, ""
        )
        if not (ok and name):
            return

        # Add tab
        self.addTab(GraphicViewWidget(main_window=self.main_window), name)

        # Set new tab active
        self.setCurrentIndex(self.count() - 1)

    def remove_tab_event(self):
        """Will remove tab from widget"""
        # Get current tab index
        index = self.currentIndex()

        # Open confirmation
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete",
            "Delete tab '{}'?".format(self.tabText(index)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.No:
            return

        # Remove tab
        self.removeTab(index)

    def get_namespace(self):
        """Return data_node namespace"""
        # Proper parent
        if self.main_window and isinstance(self.main_window, MainDockWindow):
            return self.main_window.get_current_namespace()

        return None

    def get_current_picker_items(self):
        """Return all picker items for current active tab"""
        return self.currentWidget().get_picker_items()

    def get_all_picker_items(self):
        """Returns all picker items for all tabs"""
        items = []
        for i in range(self.count()):
            items.extend(self.widget(i).get_picker_items())
        return items

    def get_data(self):
        """Will return all tabs data"""
        data = []
        for i in range(self.count()):
            name = str(self.tabText(i))
            tab_data = self.widget(i).get_data()
            data.append({"name": name, "data": tab_data})
        return data

    def set_data(self, data):
        """Will, set/load tabs data"""
        self.clear()
        for tab in data:
            view = GraphicViewWidget(
                namespace=self.get_namespace(), main_window=self.main_window
            )
            # changed name to default1 as maya wont let you make a group called
            # 'default' for curve extraction.
            self.addTab(view, tab.get("name", "default1"))

            tab_content = tab.get("data", None)
            if tab_content:
                view.set_data(tab_content)


class MainDockWindow(QtWidgets.QWidget):
    __OBJ_NAME__ = "ctrl_picker_window"
    __TITLE__ = ANIM_PICKER_TITLE.format(
        m_version=_mgear_version, ap_version=version.version
    )

    def __init__(self, parent=None, edit=False, dockable=False):
        super(MainDockWindow, self).__init__(parent=parent)
        self.window_parent = parent
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(QtCore.Qt.Window)
        self.ready = False

        # Window size
        # (default size to provide a 450/700 for tab area and proper img size)
        self.default_width = pyqt.dpi_scale(476)
        self.default_height = pyqt.dpi_scale(837)

        # Default vars
        self.status = False
        self.childs = []
        self.script_jobs = []

        __EDIT_MODE__.set_init(edit)
        self.is_dockable = dockable

        # Setup ui
        self.cb_manager = callbackManager.CallbackManager()
        self.setup()

        # experimental passthrough feature
        self.original_flags = self.windowFlags()
        self.passthrough_eventFilter_installed = False
        self.ap_eventFilter = APPassthroughEventFilter()
        self.ap_eventFilter.APUI = self

    def setup(self):
        """Setup interface"""
        # Main window setting
        # Setting object name makes docking not useable? da fuck
        # self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)

        # Add main widget and vertical layout
        self.main_vertical_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_vertical_layout)

        # Add window fields
        self.add_character_selector()
        self.add_tab_widget()

        # if the window is not dockable we can control the opacity
        # MayaQWidgetDockableMixin overrides setWindowsOpacity
        self.auto_opacity_btn = QtWidgets.QPushButton("")
        if not self.is_dockable:
            opacity_layout = QtWidgets.QHBoxLayout()
            self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.opacity_slider.setRange(10, 100)
            self.opacity_slider.setValue(100)
            self.opacity_slider.valueChanged.connect(self.change_opacity)
            self.auto_opacity_btn = QtWidgets.QPushButton("Auto opacity")
            self.auto_opacity_btn.setCheckable(True)
            self.auto_opacity_btn.toggled.connect(self.change_opacity)
            self.auto_opacity_btn.toggled.connect(
                self.toggle_passthrough_eventFilter
            )
            self.installEventFilter(self)
            opacity_layout.addWidget(self.opacity_slider)
            opacity_layout.addWidget(self.auto_opacity_btn)
            self.main_vertical_layout.addLayout(opacity_layout)

        self.add_overlays()
        self.resize(self.default_width, self.default_height)
        # Creating is done (workaround for signals being fired
        # off before everything is created)
        self.ready = True

    def toggle_passthrough_eventFilter(self):
        """enable the eventFilter for changing the AP gui windowFlags state"""
        # this feature is beta and is off by default
        if (
            menu.get_option_var_passthrough_state() == 0
            or not self.window_parent
        ):
            return
        if self.auto_opacity_btn.isChecked():
            self.window_parent.installEventFilter(self.ap_eventFilter)
            self.passthrough_eventFilter_installed = True
        else:
            self.window_parent.removeEventFilter(self.ap_eventFilter)
            self.passthrough_eventFilter_installed = False

    def set_mouseEvent_passthrough(self, state):
        """set the state of the passthrough feature for anim picker

        Args:
            state (bool): enable or disable
        """
        if state and self.passthrough_eventFilter_installed:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.setWindowFlags(
                self.original_flags & QtCore.Qt.WA_TransparentForMouseEvents
            )
            self.show()
        elif state and not self.passthrough_eventFilter_installed:
            self.toggle_passthrough_eventFilter()
        else:
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
            self.setWindowFlags(self.original_flags)
            self.show()

    def eventFilter(self, QObject, event):
        """event filter for general override
        current use
        -Auto opacityfilter
        -hide the GraphicsView for compatibility with MacOs

        Args:
            QObject (QObject): the object getting the event
            event (QEvent): event type

        Returns:
            bool: accepting event or not
        """
        modifiers = None
        if self.auto_opacity_btn.isChecked():
            modifiers = QtWidgets.QApplication.queryKeyboardModifiers()

        if event.type() == QtCore.QEvent.Type.Enter:
            shift_state = modifiers == QtCore.Qt.ShiftModifier
            flag_state = self.testAttribute(
                QtCore.Qt.WA_TransparentForMouseEvents
            )
            if self.auto_opacity_btn.isChecked():
                if flag_state and shift_state:
                    self.setWindowOpacity(100)
                    return True
                elif not flag_state:
                    self.setWindowOpacity(100)
                    return True
        else:
            if event.type() == QtCore.QEvent.Type.Leave:
                opacity_state = self.auto_opacity_btn.isChecked()
                flag_state = self.testAttribute(
                    QtCore.Qt.WA_TransparentForMouseEvents
                )
                if opacity_state:
                    pos = QtGui.QCursor().pos()
                    widgetRect = self.geometry()
                    if not widgetRect.contains(pos):
                        self.change_opacity()
                        # check the option var if it is enabled
                        if menu.get_option_var_passthrough_state():
                            self.set_mouseEvent_passthrough(True)
                elif flag_state and not opacity_state:
                    self.set_mouseEvent_passthrough(False)

        # QtCore.QEvent.Type.ScreenChangeInternal
        # hide main tab widget for os compatibility
        if QObject in getattr(self, "overlays", []):
            if event.type() == QtCore.QEvent.Type.Show:
                self.tab_widget.hide()
                return True
            elif event.type() == QtCore.QEvent.Type.Hide:
                self.tab_widget.show()
                return True

        return False

    def change_opacity(self):
        """Change the  windows opacity"""
        opacity_value = self.opacity_slider.value()
        self.setWindowOpacity(opacity_value / 100.0)

    def reset_default_size(self):
        """Reset window size to default"""
        self.resize(self.default_width, self.default_height)

    def toggle_character_selector(self, *args):
        """Toggle the visibility of the character select widget"""
        if self.character_box.isChecked():
            self.char_select_widget.show()
        else:
            self.char_select_widget.hide()

    def add_character_selector(self):
        """Add Character comboBox selector"""
        # Create group box
        self.character_box = QtWidgets.QGroupBox("Character Selector")
        bg_color = self.palette().color(QtGui.QPalette.Window).getRgb()
        cc_style_sheet = GROUPBOX_BG_CSS.format(color=bg_color)
        self.character_box.setStyleSheet(cc_style_sheet)
        self.character_box.setContentsMargins(0, 0, 0, 0)
        self.character_box.setMinimumHeight(0)
        self.character_box.setMaximumHeight(pyqt.dpi_scale(80))
        self.character_box.setCheckable(True)
        self.character_box.setChecked(True)
        self.character_box.clicked.connect(self.toggle_character_selector)

        self.char_select_widget = QtWidgets.QWidget()
        self.char_select_widget.setContentsMargins(0, 5, 0, 0)
        tmp_layout = QtWidgets.QHBoxLayout(self.character_box)
        tmp_layout.setSpacing(0)
        tmp_layout.addWidget(self.char_select_widget)

        # Create layout
        layout = QtWidgets.QHBoxLayout(self.char_select_widget)

        # Create character picture widget
        self.pic_widget = basic.SnapshotWidget()

        box_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(box_layout)
        layout.addWidget(self.pic_widget, QtCore.Qt.AlignCenter)

        # Add combo box
        self.char_selector_cb = basic.CallbackComboBox(
            callback=self.selector_change_event
        )
        box_layout.addWidget(self.char_selector_cb)

        # Init combo box data
        self.char_selector_cb.nodes = []

        # Add option buttons
        btns_layout = QtWidgets.QHBoxLayout()
        box_layout.addLayout(btns_layout)

        # Add horizont spacer
        spacer = QtWidgets.QSpacerItem(
            10,
            0,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum,
        )
        btns_layout.addItem(spacer)

        # sync checkbox
        self.checkbox = QtWidgets.QCheckBox("Sync Namespace")
        if not __EDIT_MODE__.get():
            btns_layout.addWidget(self.checkbox)

        # About btn
        about_btn = basic.CallbackButton(callback=self.show_about_infos)
        about_btn.setText("?")
        about_btn.setToolTip("Show help/about informations")
        btns_layout.addWidget(about_btn)

        # laod btn
        load_btn = basic.CallbackButton(callback=self.show_load_widget)
        load_btn.setText("Load")
        load_btn.setToolTip("Load from file")
        btns_layout.addWidget(load_btn)

        # Refresh button
        self.char_refresh_btn = basic.CallbackButton(callback=self.refresh)
        self.char_refresh_btn.setText("Refresh")
        btns_layout.addWidget(self.char_refresh_btn)

        # Edit buttons
        self.new_char_btn = None
        self.save_char_btn = None
        if __EDIT_MODE__.get():
            # Add New  button
            self.new_char_btn = basic.CallbackButton(
                callback=self.new_character
            )
            self.new_char_btn.setText("New")
            self.new_char_btn.setFixedWidth(pyqt.dpi_scale(40))

            btns_layout.addWidget(self.new_char_btn)

            # Add Save  button
            self.save_char_btn = basic.CallbackButton(
                callback=self.save_character
            )
            self.save_char_btn.setText("Save")
            self.save_char_btn.setFixedWidth(pyqt.dpi_scale(40))

            btns_layout.addWidget(self.save_char_btn)
        self.main_vertical_layout.addWidget(self.character_box)

    def add_tab_widget(self, name="default"):
        """Add control display field"""
        self.tab_widget = ContextMenuTabWidget(self, main_window=self)
        self.main_vertical_layout.addWidget(self.tab_widget)

        # Add default first tab
        view = GraphicViewWidget(main_window=self)
        self.tab_widget.addTab(view, name)

        # ensure the tab retains its size when hidden
        sp_retain = self.tab_widget.sizePolicy()
        sp_retain.setRetainSizeWhenHidden(True)
        self.tab_widget.setSizePolicy(sp_retain)

    def add_overlays(self):
        """Add transparent overlay widgets"""
        self.about_widget = overlay_widgets.AboutOverlayWidget(self)
        self.load_widget = overlay_widgets.LoadOverlayWidget(self)
        self.save_widget = overlay_widgets.SaveOverlayWidget(self)
        self.overlays = [self.about_widget, self.load_widget, self.save_widget]

        # specificaly hiding and showing the main layer for OS compatibility
        for layer in self.overlays:
            layer.installEventFilter(self)

    def get_picker_items(self):
        """Return picker items for current active tab"""
        return self.tab_widget.get_current_picker_items()

    def get_all_picker_items(self):
        """Return all picker items for current picker"""
        return self.tab_widget.get_all_picker_items()

    def dockCloseEventTriggered(self):
        self.close()

    def closeEvent(self, evnt):
        self.close()

    def close(self):
        """Overwriting close event to close child windows too"""
        # Delete script jobs
        self.cb_manager.removeAllManagedCB()
        # Close childs
        for child in self.childs:
            try:
                child.close()
            except Exception:
                pass

        # Close ctrls options windows
        for item in self.get_all_picker_items():
            try:
                if not item.edit_window:
                    continue
                item.edit_window.close()
            except Exception:
                pass

        try:
            self.window_parent.removeEventFilter(self.ap_eventFilter)
        except Exception:
            pass

        # Default close
        # mayaMixin bug that i need to correct for
        corrected_for_dashes = self.objectName().replace("_", "-")
        corrected_for_initial_dash = corrected_for_dashes.replace("-", "_", 1)
        work_name = "{}WorkspaceControl".format(corrected_for_initial_dash)
        try:
            cmds.workspaceControl(work_name, e=True, close=True)
        except ValueError:
            pass
        except RuntimeError:
            pass
        self.deleteLater()

    def showEvent(self, *args, **kwargs):
        """Default showEvent overload"""
        # Prevent firing this event before the window is set up
        if not self.ready:
            return

        # Default close
        super(MainDockWindow, self).showEvent(*args, **kwargs)

        # Force char load
        self.refresh()

        # Add script jobs
        self.add_callback()

    def resizeEvent(self, event):
        """Resize about overlay on resize event"""
        # Prevent firing this event before the window is set up
        if not self.ready:
            return

        size = self.size()

        self.about_widget.resize(size)

        self.save_widget.resize(size)

        self.load_widget.resize(size)

        return super(MainDockWindow, self).resizeEvent(event)

    def show_about_infos(self):
        """Open animation picker about and help infos"""
        self.about_widget.show()

    def show_load_widget(self):
        """Open animation picker about and help infos"""
        self.load_widget.show()

    # =========================================================================
    # Character selector handlers ---
    def selector_change_event(self, index):
        """Will load data node relative to selector index"""
        self.load_character()

    def populate_char_selector(self):
        """Will populate char selector combo box"""
        # Get char nodes
        nodes = picker_node.get_nodes()
        self.char_selector_cb.nodes = nodes

        # Empty combo box
        self.char_selector_cb.clear()

        # Populate
        for data_node in nodes:
            # text = data_node.get_namespace() or data_node.name
            text = data_node.name
            self.char_selector_cb.addItem(text)

        # Set elements active status
        self.set_field_status()

    def set_field_status(self):
        """Will toggle elements active status"""
        # Define status from node list
        self.status = False
        if self.char_selector_cb.count():
            self.status = True

        # Set status
        self.char_selector_cb.setEnabled(self.status)
        self.tab_widget.setEnabled(self.status)
        if self.save_char_btn:
            self.save_char_btn.setEnabled(self.status)

        # Reset tabs
        if not self.status:
            self.load_default_tabs()

    def load_default_tabs(self):
        """Will reset and load default empty tabs"""
        self.tab_widget.clear()
        self.tab_widget.addTab(GraphicViewWidget(main_window=self), "None")

    def refresh(self):
        """Refresh char selector and window"""
        # Get current active node
        current_node = None
        data_node = self.get_current_data_node()
        if data_node and data_node.exists():
            current_node = data_node.name

        # Check/abort on possible data changes
        if __EDIT_MODE__.get() and current_node:
            if not self.check_for_data_change():
                return

        # Re-populate selector
        self.populate_char_selector()

        # Set proper index
        if current_node:
            self.make_node_active(current_node)

        # Refresh selection check
        self.selection_change_event()

        # Force view resize
        self.tab_widget.fit_contents()

        # Set focus on view
        self.tab_widget.currentWidget().setFocus()

    def load_from_sel_node(self):
        """Will try to load character for selected node"""
        sel = cmds.ls(sl=True)
        if not sel:
            return
        data_node = picker_node.get_node_for_object(sel[0])
        if not data_node:
            return
        self.make_node_active(data_node.name)

    def make_node_active(self, data_node):
        """Will set character selector to specified data_node"""
        index = 0
        for i in range(len(self.char_selector_cb.nodes)):
            node = self.char_selector_cb.nodes[i]
            if not data_node == node.name or data_node == node:
                continue
            index = i
            break
        self.char_selector_cb.setCurrentIndex(index)

    def new_character(self):
        """
        Will create a new data node, and init a new window
        (edit mode only)
        """
        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "New character",
            "Node name",
            QtWidgets.QLineEdit.Normal,
            "PICKER_DATA",
        )
        if not (ok and name):
            return

        # Check for possible data changes/loss
        if not self.check_for_data_change():
            return

        # Create new data node
        data_node = picker_node.DataNode(name=str(name))
        data_node.create()
        self.refresh()
        self.make_node_active(data_node)

    # =========================================================================
    # Data ---
    def check_for_data_change(self):
        """
        Check if data changed
        If changes are detected will ask user if he wants to proceed any
        way and loose thoses changes
        Return user answer
        """
        # Get current data node
        data_node = self.get_current_data_node()
        if not (data_node and data_node.exists()):
            return True

        # Return true if no changes were detected
        if data_node == self.get_character_data():
            return True

        # Open question window
        msg = "Any changes will be lost, proceed any way ?"
        answer = QtWidgets.QMessageBox.question(
            self,
            "Changes detected",
            msg,
            buttons=QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def get_current_namespace(self):
        return self.get_current_data_node().get_namespace()

    def get_current_data_node(self):
        """Return current character data node"""
        # Empty list case
        if not self.char_selector_cb.count():
            return None

        # Return node from combo box index
        index = self.char_selector_cb.currentIndex()
        return self.char_selector_cb.nodes[index]

    def load_character(self):
        """Load currently selected data node"""
        # Get DataNode
        data_node = self.get_current_data_node()
        if not data_node:
            return
        picker_data = data_node.get_data()

        # Load snapshot
        path = picker_data.get("snapshot", None)
        self.pic_widget.set_background(path)

        # load tabs
        tabs_data = picker_data.get("tabs", {})
        self.tab_widget.set_data(tabs_data)

        # Default tab
        if not self.tab_widget.count():
            self.tab_widget.addTab(
                GraphicViewWidget(main_window=self), "default"
            )
        else:
            # Return to first tab
            self.tab_widget.setCurrentIndex(0)

        # Fit content
        self.tab_widget.fit_contents()

        # Update selection states
        self.selection_change_event()

    def save_character(self):
        """Save data to current selected data_node"""
        # Get DataNode
        data_node = self.get_current_data_node()
        assert data_node, "No data_node found/selected"

        # Block save in anim mode
        if not __EDIT_MODE__.get():
            QtWidgets.QMessageBox.warning(
                self, "Warning", "Save is not permited in anim mode"
            )
            return

        # Block save on referenced nodes
        if data_node.is_referenced():
            msg = "Save is not permited on referenced nodes"
            QtWidgets.QMessageBox.warning(self, "Warning", msg)
            return

        self.save_widget.show()

    def get_character_data(self):
        """Return window data"""
        picker_data = {}

        # Add snapshot path data
        snapshot_data = self.pic_widget.get_data()
        if snapshot_data:
            picker_data["snapshot"] = snapshot_data

        # Add tabs data
        tabs_data = self.tab_widget.get_data()
        if tabs_data:
            picker_data["tabs"] = tabs_data

        return picker_data

    # =========================================================================
    # Script jobs handling ---
    def add_callback(self):
        """Will add maya scripts job events"""
        # Clear any existing scrip jobs
        self.cb_manager.removeAllManagedCB()

        # Add selection change event
        self.cb_manager.selectionChangedCB(
            "anim_picker_selection", self.selection_change_event
        )
        # Add scene open event
        self.cb_manager.newSceneCB(
            "anim_picker_newScene", self.selection_change_event
        )

    def selection_change_event(self, *args):
        """
        Event called with a script job from maya on selection change.
        Will properly parse poly_ctrls associated node, and set border
        visible if content is selected
        """
        # Abort in Edit mode
        if __EDIT_MODE__.get():
            return

        # Update selection data
        __SELECTION__.update()

        # sync with namespce
        if not __EDIT_MODE__.get():
            sel = pm.selected()
            sync = self.checkbox.isChecked()
            if sel and sync:
                ns = sel[0].namespace()
                if ns:
                    for i, n in enumerate(self.char_selector_cb.nodes):
                        if ns in str(n):
                            self.char_selector_cb.setCurrentIndex(i)
                            break
        # Update controls for active tab
        for item in self.get_picker_items():
            item.run_selection_check()


# version of the anim picker ui that uses MayaQWidgetDockableMixin for docking
class MainDockableWindow(MayaQWidgetDockableMixin, MainDockWindow):
    def __init__(self, parent=None, edit=False, dockable=True):
        super(MainDockableWindow, self).__init__(parent=parent)


# =============================================================================
# Load user interface function
# =============================================================================
def load(edit=False, dockable=False):
    """To launch the ui and not get the same instance

    Returns:
        Anim_picker: instance

    Args:
        edit (bool, optional): Description
        dockable (bool, optional): Description

    """

    # NOTE: if instedad with set dockable to false the window doesn't get
    # parented to Maya UI
    # TODO: Dockable breaks the interface when docks. For the moment this
    # option is not available from the menu
    if dockable:
        ANIM_PKR_UI = MainDockableWindow(
            parent=None, edit=edit, dockable=dockable
        )
        ANIM_PKR_UI.show(dockable=True)
    else:
        ANIM_PKR_UI = MainDockWindow(parent=pyqt.get_main_window(), edit=edit)
        ANIM_PKR_UI.show()

    return ANIM_PKR_UI
