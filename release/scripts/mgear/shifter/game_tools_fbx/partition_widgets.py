import copy
import weakref

import maya.cmds as cmds

# TODO: Remove dependency
import maya.app.flux.core as fx

from mgear.vendor.Qt import QtWidgets, QtCore, QtGui

from mgear.core import pyqt, utils
from mgear.shifter.game_tools_fbx import fbx_export_node


ROW_HEIGHT = 30
LABEL_COLORS = ["red", "blue", "grey", "orange", "green", "yellow", "purple"]
COLORS = {
    "blue": [88, 165, 204],
    "grey": [189, 189, 189],
    "orange": [219, 148, 86],
    "green": [85, 171, 100],
    "yellow": [191, 178, 58],
    "purple": [174, 156, 219],
    "default": [241, 90, 91],
}


class NodeClass(object):
    def __init__(
        self, node_name, node_type, is_root, icon, enabled, network_enabled
    ):
        super(NodeClass, self).__init__()

        self._node_name = node_name
        self._node_type = node_type
        self._is_root = is_root
        self._icon = icon
        self._enabled = enabled
        self._network_enabled = network_enabled
        self._label_color = QtGui.QColor(241, 90, 91)
        color = QtGui.QColor(0, 0, 0)
        color.setNamedColor("#444444")
        if self._is_root:
            color.setNamedColor("#5d5d5d")
        self._background_color = color
        self._tooltip = None
        self._can_be_deleted = True
        self._can_be_disabled = True
        self._can_be_duplicated = True
        self._can_add_children = True

    def __repr__(self):
        return "NODE - {} {}".format(self._node_name, self._node_type)

    @property
    def node_name(self):
        return self._node_name

    @node_name.setter
    def node_name(self, value):
        self._node_name = value

    @property
    def display_name(self):
        return self.node_name.split("|")[-1]

    @property
    def node_type(self):
        return self._node_type

    @property
    def is_root(self):
        return self._is_root

    @property
    def icon(self):
        return self._icon

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, flag):
        self._enabled = flag

    @property
    def network_enabled(self):
        return self._network_enabled

    @network_enabled.setter
    def network_enabled(self, flag):
        self._network_enabled = flag

    @property
    def label_color(self):
        return self._label_color

    @label_color.setter
    def label_color(self, value):
        self._label_color = value

    @property
    def background_color(self):
        return self._background_color

    @property
    def can_be_deleted(self):
        return self._can_be_deleted

    @can_be_deleted.setter
    def can_be_deleted(self, flag):
        self._can_be_deleted = flag

    @property
    def can_be_disabled(self):
        return self._can_be_disabled

    @can_be_disabled.setter
    def can_be_disabled(self, flag):
        self._can_be_disabled = flag

    @property
    def can_be_duplicated(self):
        return self._can_be_duplicated

    @can_be_duplicated.setter
    def can_be_duplicated(self, flag):
        self._can_be_duplicated = flag

    @property
    def can_add_children(self):
        return self._can_add_children

    @can_add_children.setter
    def can_add_children(self, flag):
        self._can_add_children = flag


class OutlinerMenu(QtWidgets.QMenu):
    def __init__(self, title="", parent=None):
        super(OutlinerMenu, self).__init__(title, parent)

        self.hovered.connect(self._on_hovered)

    def _on_hovered(self, action):
        QtWidgets.QToolTip.showText(
            QtGui.QCursor.pos(),
            action.toolTip(),
            self,
            self.actionGeometry(action),
        )


class TreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, node, header, show_enabled, parent=None):
        super(TreeItem, self).__init__()

        self._node = node  # type: NodeClass
        self._header = header
        self._connected_nodes = []
        self._show_enabled = show_enabled

        self.set_parent(parent)

    @property
    def node(self):
        return self._node

    def parent(self):
        return self._parent

    def set_parent(self, parent):
        self._parent = parent

    def get_name(self):
        return self.node.node_name if self.node else self._header

    def set_name(self, name):
        self.node.node_name = name

    def get_display_name(self):
        return self.node.display_name if self.node else self.get_name()

    def get_node_type(self):
        return self.node.node_type

    def get_icon(self):
        return self.node.icon

    def set_enabled(self):
        self.node.enabled = not self.is_enabled()
        if not self.is_root():
            pass
        else:
            self.node.network_enabled = self.is_enabled()

    def get_background_color(self):
        return self.node.background_color

    def get_window_background_color(self):
        return QtGui.QColor(43, 43, 43)

    def get_inactive_color(self):
        return QtGui.QColor(150, 150, 150)

    def is_enabled(self):
        return self.node.enabled

    def network_enabled(self):
        return self.parent().node.network_enabled if self.parent() else True

    def is_root(self):
        return self.node.is_root

    def get_label_color(self):
        return self.node.label_color

    def set_label_color(self, color):
        if isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)
        self.node.label_color = color
        for i in range(self.childCount()):
            child = self.child(i)
            child.node.label_color = color

        value = [color.red(), color.green(), color.blue()]
        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return
        export_node.set_partition_color(self.node.node_name, value)

    def get_action_button_count(self):
        return 7 if self.node.is_root else 3

    def has_enable_toggle(self):
        return self._show_enabled

    def get_action_button(self, index):
        if self.node.is_root:
            if index >= 0 and index <= 6:
                return [
                    "Enabled" if self.node.can_be_disabled else None,
                    None,
                    "Add" if self.node.can_add_children else None,
                    None,
                    None,
                    None,
                    None,
                ][index]
        else:
            if index >= 0 and index <= 2:
                return [
                    "Enabled" if self.node.can_be_disabled else None,
                    None,
                    "Remove" if self.node.can_be_deleted else None,
                ][index]

        return None

    def delete_node(self):
        export_node = fbx_export_node.FbxExportNode.get()
        if not export_node:
            return

        # Partition Node
        if self.is_root():
            result = export_node.delete_skeletal_mesh_partition(
                self.get_name()
            )

            if result:
                master_item = self.parent()._master_item

                # Moves geo back to master partition
                for i in reversed(range(self.childCount())):
                    child = self.child(i)
                    master_item.addChild(child)

                # Deletes selected partition
                self.parent().takeTopLevelItem(
                    self.parent().indexOfTopLevelItem(self)
                )

                # Redraws the UI
                self.parent().reset_contents()

        # Geometry Node
        else:
            result = export_node.delete_skeletal_mesh_from_partition(
                self.parent().get_name(), self.get_name()
            )

            if result:
                # Remove child from partition node
                self.parent().takeChild(self.parent().indexOfChild(self))
                # Get master partition
                master_item = self.parent().parent()._master_item
                # Parent node under master partition
                export_node.add_skeletal_meshes_to_partition(
                    master_item.get_name(),
                    [self.get_name()]
                )

                # refresh the UI, which will redraw the geometry as it is on the Maya Node.
                self.parent().parent().reset_contents()



class OutlinerTreeView(QtWidgets.QTreeWidget):
    TREE_ITEM_CLASS = TreeItem
    NODE_CLASS = NodeClass

    EXPAND_WIDTH = 60
    TRASH_IMAGE = pyqt.get_icon("mgear_trash")
    COPY_IMAGE = pyqt.get_icon("mgear_copy")

    itemEnabledChanged = QtCore.Signal(object)
    itemAddNode = QtCore.Signal(object)
    itemRenamed = QtCore.Signal(str, str)
    itemRemoved = QtCore.Signal(str, str)
    droppedItems = QtCore.Signal(object, list, bool)

    def __init__(self, parent=None):
        super(OutlinerTreeView, self).__init__(parent=parent)

        self._last_hit_action = None
        self._selection_parent = None
        self._selection_node = None
        self._action_button_pressed = False
        self._registered_node_callbacks = []
        self._button_pressed = None

        self.setHeaderHidden(True)
        self.setIndentation(12)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.populate_items()

        self.header().setCascadingSectionResizes(False)
        self.setColumnWidth(0, 250)
        self.header().resizeSection(0, 250)
        self.resizeColumnToContents(0)
        delegate = TreeViewDelegate(self)
        self.setItemDelegate(delegate)
        self.setRootIsDecorated(False)
        self.expandAll()
        self.setExpandsOnDoubleClick(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)

        self._context_menu = OutlinerMenu(parent=self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            self._on_custom_context_menu_requested
        )

    @property
    def last_hit_action(self):
        return self._last_hit_action

    @last_hit_action.setter
    def last_hit_action(self, value):
        self._last_hit_action = value

    def mousePressEvent(self, event):
        """
        Triggers actions based on mouse press
        """

        self._button_pressed = event.button()

        if event.button() in (QtCore.Qt.LeftButton, QtCore.Qt.RightButton):
            index = self.indexAt(event.pos())
            if index.row() == -1:
                self._action_button_pressed = False
                super(OutlinerTreeView, self).mousePressEvent(event)
                self.clearSelection()
                self.window().repaint()
                return

            item = self._get_corresponding_item(index)
            action = self._get_current_action(event.pos(), item)

            if item.node.node_type != "Root":
                self._selection_parent = item.parent().get_name()
                self._selection_node = item.get_name()

            self.selectionModel().setCurrentIndex(
                index, QtCore.QItemSelectionModel.NoUpdate
            )

            if action is not None:
                self._action_button_pressed = True
                if action == "Enabled":
                    item.set_enabled()
                    self.itemEnabledChanged.emit(item)
                if action == "Add":
                    self.itemAddNode.emit(item)
                if action == "Remove":
                    if not item.is_root():
                        parent_name = item.parent().get_name()
                        item_name = item.get_name()
                        item.parent().takeChild(
                            item.parent().indexOfChild(item)
                        )
                        self.itemRemoved.emit(parent_name, item_name)
                if action == "ExpandCollapse":
                    if item.node.node_type == "Root":
                        self._toggle_expand_collapse()
            else:
                pass
            event.accept()
        elif event.button() == QtCore.Qt.MiddleButton:
            super(OutlinerTreeView, self).mousePressEvent(event)

        # self.clearSelection()
        super(OutlinerTreeView, self).mousePressEvent(event)
        self.window().repaint()

    def mouseMoveEvent(self, event):
        if not self._action_button_pressed:
            super(OutlinerTreeView, self).mouseMoveEvent(event)

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.AltModifier:
            QtWidgets.QWidget.setCursor(
                self, (QtGui.QCursor(QtCore.Qt.DragCopyCursor))
            )
        else:
            QtWidgets.QWidget.unsetCursor(self)
        self._last_hit_action = None

        # dirty the treeview so it will repaint when the mouse moves over it
        # this is needed to change the icon rollover state
        region = self.childrenRegion()
        self.setDirtyRegion(region)

    def mouseReleaseEvent(self, event):
        QtWidgets.QApplication.restoreOverrideCursor()
        if not self._action_button_pressed:
            super(OutlinerTreeView, self).mouseReleaseEvent(event)
        else:
            self._action_button_pressed = False
        self.window().repaint()

    def leaveEvent(self, event):
        self._last_hit_action = None
        self.window().repaint()

    @utils.one_undo
    def dropEvent(self, event):
        index = self.indexAt(event.pos())
        item = self.itemFromIndex(index)

        can_be_dropped = self.can_be_dropped(index)
        if not can_be_dropped:
            event.ignore()
            return

        self.droppedItems.emit(
            item,
            self.selectedItems(),
            True if self._button_pressed == QtCore.Qt.RightButton else False,
        )

        self.reset_contents()

    def can_be_dropped(self, index):
        item = self.itemFromIndex(index)
        drop_indicator_position = self.dropIndicatorPosition()

        is_invalid_position = (
            not index.isValid()
            or item.childCount() == -1
            or (
                item.parent().indexOfChild(item) == (item.childCount() - 1)
                if item.parent() != self
                else True
                and drop_indicator_position
                == QtWidgets.QAbstractItemView.BelowItem
            )
        )

        return not is_invalid_position

    def get_indent(self, index):
        indent = 0
        while index and index.parent().isValid():
            index = index.parent()
            indent += self.indentation()

        return indent

    def find_items(self):
        return {}

    def populate_items(self, add_callbacks=True):
        if add_callbacks:
            self.cleanup()

        all_items = self.find_items()

        for item_name, item_data in all_items.items():
            root_item = self._create_root_item(item_name)
            root_item.setFlags(
                root_item.flags()
                | QtCore.Qt.ItemIsEditable
                | QtCore.Qt.ItemIsDropEnabled
            )
            root_item.setFlags(
                root_item.flags() & ~QtCore.Qt.ItemIsDragEnabled
            )
            self.addTopLevelItem(root_item)

            for child_node in item_data:
                child = self._add_partition_item(child_node, root_item)
                child.setFlags(
                    child.flags()
                    | QtCore.Qt.ItemIsEditable
                    | ~QtCore.Qt.ItemIsDropEnabled
                )
                child.setFlags(
                    root_item.flags() & ~QtCore.Qt.ItemIsDragEnabled
                )
                root_item.addChild(child)
                if add_callbacks:
                    pass

    def clear_items(self):
        """
        Clear all tree widget items
        """

        # NOTE: it seems self.clear() crashes Maya
        for i in range(self.topLevelItemCount()):
            self.takeTopLevelItem(0)

    def reset_contents(self, reset_callbacks=True, expand=True):
        """
        Forces the repopulation the tree widget
        """

        self._selection_parent = None
        self._selection_node = None

        self.clear_items()
        self.populate_items(reset_callbacks)

        if expand:
            self.expandAll()

    def cleanup(self):
        self._registered_node_callbacks = []

    def _create_root_item(self, partition):
        node_icon = pyqt.get_icon("mgear_package")
        root_node = self.NODE_CLASS(
            partition, "Root", True, node_icon, True, True
        )

        item = self.TREE_ITEM_CLASS(root_node, partition, True, parent=self)

        return item

    def _add_partition_item(self, node, partition_item):
        node_icon = pyqt.get_icon("mgear_box")
        item_node = self.NODE_CLASS(
            node,
            "Geometry",
            False,
            node_icon,
            True,
            partition_item.node.network_enabled,
        )
        item_node.can_be_disabled = False

        item = self.TREE_ITEM_CLASS(item_node, "", True, partition_item)

        return item

    def _get_corresponding_item(self, index):
        return self.itemFromIndex(index) if index.isValid() else None

    def _get_current_item(self):
        return self.currentItem()

    def _get_current_action(self, point, item):
        if item:
            if item.childCount() > 0 and point.x() < self.EXPAND_WIDTH:
                return "ExpandCollapse"
            return self._last_hit_action
        return None

    def _get_label_color(self):
        item = self._get_current_item()
        return item.node.label_color

    @utils.one_undo
    def _set_label_color(self, color_label):
        color = self._get_color_from_label(color_label)
        self._get_current_item().set_label_color(color)

    def _get_color_from_label(self, color_label):
        return QtGui.QColor(
            *COLORS.get(color_label.lower(), COLORS["default"])
        )

    def _toggle_expand_collapse(self):
        """
        Expands and collaps the partition nodes
        """

        item = self.currentItem()
        self.collapseItem(item) if item.isExpanded() else self.expandItem(item)

    def _delete_node(self):
        item = self._get_current_item()
        if item is None:
            return
        response = cmds.confirmDialog(
            title="确认",
            message="确认删除",
            button=["是", "否"],
            defaultButton="是",
            cancelButton="否",
            dismissString="否",
        )
        if response == "是":
            cmds.select(clear=True)
            item.delete_node()

    def _on_custom_context_menu_requested(self, pos):
        """
        Internal callback function that rebuils the context menu from scratch
        """

        selected_indexes = self.selectedIndexes()
        num_indexes = len(selected_indexes)
        self._context_menu.clear()
        item = self._get_current_item()
        if item is None:
            return
        if item.is_root():
            if num_indexes > 0:
                pixmap = QtGui.QPixmap(100, 100)
                pixmap.fill(self._get_label_color())
                label_icon = QtGui.QIcon(pixmap)
                prev_menu = self._context_menu.addMenu(
                    label_icon, "标签颜色"
                )
                for color_label in LABEL_COLORS:
                    pixmap = QtGui.QPixmap(100, 100)
                    pixmap.fill(self._get_color_from_label(color_label))
                    label_icon = QtGui.QIcon(pixmap)
                    prev_menu.addAction(
                        label_icon,
                        color_label,
                        lambda color_label=color_label: self._set_label_color(
                            color_label
                        ),
                    )
            if item.node.can_be_duplicated:
                duplicate_action = self._context_menu.addAction(
                    self.COPY_IMAGE, "Duplicate"
                )
                duplicate_action.setEnabled(False)
            if item.node.can_be_deleted:
                self._context_menu.addAction(
                    self.TRASH_IMAGE, "Delete", self._delete_node
                )
        else:
            if item.node.can_be_deleted:
                self._context_menu.addAction(
                    self.TRASH_IMAGE, "Delete", self._delete_node
                )

        self._context_menu.popup(QtGui.QCursor.pos())
        self._context_menu.exec_(self.mapToGlobal(pos))


class TreeViewDelegate(QtWidgets.QItemDelegate):
    def __init__(self, tree_view):
        super(TreeViewDelegate, self).__init__()

        self._tree_view = weakref.ref(tree_view)

    @property
    def tree_view(self):
        return self._tree_view()

    def initStyleOption(self, option, index):
        super(TreeViewDelegate, self).initStyleOption(option, index)
        # override what you need to change in option
        if option.state & QtWidgets.QStyle.State_Selected:
            option.state &= ~QtWidgets.QStyle.State_Selected
            option.backgroundBrush = QtGui.QBrush(QtCore.Qt.red)

    def paint(self, painter, option, index):
        if not index.isValid():
            return

        item = self.tree_view.itemFromIndex(index)
        row_painter = RowPainter(painter, option, item, self.tree_view)
        row_painter.paint_row()

    def sizeHint(self, option, index):
        hint = super(TreeViewDelegate, self).sizeHint(option, index)
        hint.setHeight(ROW_HEIGHT)
        return hint

    def createEditor(self, parent, option, index):
        """
        Overrides createEditor function to create the double click editor for renaming nodes.
        """

        # only root items can be renamed
        item = self.tree_view.itemFromIndex(index)
        if not item or not item.is_root():
            return None

        editor = QtWidgets.QLineEdit(parent)
        editor.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        """
        Overrides updateEditorGeometry so a valid rectangle for the QtWidgets.QLineEditor is defined.
        """

        indent = self.tree_view.get_indent(index)
        rect = copy.deepcopy(option.rect)
        rect.setLeft(indent + 46.5)
        rect.setBottom(rect.bottom() - 4)
        rect.setRight(rect.right() - 50)
        editor.setGeometry(rect)

    def setEditorData(self, editor, index):
        item = self.tree_view.itemFromIndex(index)
        editor.setText(item.get_display_name())

    def setModelData(self, editor, model, index):
        """
        Overrides setModelData which will trigger the node renaming to run within Maya
        """

        new_value = editor.text()
        item = self.tree_view.itemFromIndex(index)
        if not item:
            return
        name = item.get_name()
        if not name or name == new_value:
            return
        item.set_name(new_value)
        self.tree_view.itemRenamed.emit(name, new_value)


class RowPainter(object):
    DISABLED_BACKGROUND_IMAGE = fx.getPixmap("out_MASH_ChevronBG")
    DISABLED_HIGHLIGHT_IMAGE = fx.getPixmap("out_MASH_ChevronBGSelected")
    EXPANDED_ARROW = (
        QtCore.QPointF(9.0, 11.0),
        QtCore.QPointF(19.0, 11.0),
        QtCore.QPointF(14.0, 16.0),
    )
    COLLAPSED_ARROW = (
        QtCore.QPointF(12.0, 8.0),
        QtCore.QPointF(17.0, 13.0),
        QtCore.QPointF(12.0, 18.0),
    )
    ARROW_COLOR = QtGui.QColor(189, 189, 189)
    ICON_PADDING = 10
    ICON_WIDTH = 20
    ICON_WIDTH_NO_DPI = 20
    ICON_TOP_OFFSET = 4
    COLOR_BAR_WIDTH = 6
    DRAG_HANDLE_IMAGE = fx.getPixmap("out_MASH_OutlinerDrag")
    LOCK_IMAGE = fx.getPixmap("out_MASH_OutlinerNoDrag")
    ACTION_BORDER = 0
    ACTION_WIDTH = 20
    ENABLED_IMAGE = fx.getPixmap("out_MASH_Enable")
    DISABLED_IMAGE = fx.getPixmap("out_MASH_Disable")
    ENABLED_SELECTED_IMAGE = fx.getPixmap("out_MASH_Enable_Selected")
    INACTIVE_ENABLED_IMAGE = fx.getPixmap("out_MASH_Inactive")
    ADD_IMAGE = pyqt.get_icon("mgear_plus")
    REMOVE_IMAGE = pyqt.get_icon("mgear_minus")

    def __init__(self, painter, option, item, parent):
        super(RowPainter, self).__init__()

        self._parent = weakref.ref(parent)
        self._painter = painter
        self._item = item  # type: TreeItem
        self._rect = copy.deepcopy(option.rect)
        self._is_highlighted = (
            option.showDecorationSelected
            and option.state & QtWidgets.QStyle.State_Selected
        )
        self._highlight_color = option.palette.color(QtGui.QPalette.Highlight)

    @property
    def item(self):
        return self._item

    @property
    def parent(self):
        return self._parent

    def paint_row(self):
        self._draw_background()
        self._draw_color_bar()
        self._draw_fill()
        self._draw_arrow_drag_lock()
        text_rect = self._draw_text()
        self._draw_icon(text_rect)
        self._add_action_icons()

    def _draw_background(self):
        """
        Internal function that draws the cell background color/image
        """

        if self.item.is_root() or self.item.network_enabled():
            color = (
                self._highlight_color
                if self._is_highlighted
                else self.item.get_background_color()
            )
            self._painter.fillRect(self._rect, color)
        else:
            pixmap = (
                self.DISABLED_HIGHLIGHT_IMAGE
                if self._is_highlighted
                else self.DISABLED_BACKGROUND_IMAGE
            )
            self._painter.drawTiledPixmap(
                self._rect, pixmap, QtCore.QPoint(self._rect.left(), 0)
            )

    def _draw_color_bar(self):
        """Draws the label color bar"""

        color = self.item.get_label_color()
        rect2 = copy.deepcopy(self._rect)
        rect2.setRight(rect2.left() + self.COLOR_BAR_WIDTH)
        self._painter.fillRect(rect2, color)

    def _draw_fill(self):
        """Draws the border of the cell"""

        rect2 = copy.deepcopy(self._rect)
        old_pen = self._painter.pen()
        self._painter.setPen(
            QtGui.QPen(self.item.get_window_background_color(), 2)
        )
        rect2.setLeft(rect2.left())
        rect2.setRight(rect2.right() - 2)
        rect2.setTop(rect2.top())
        rect2.setBottom(rect2.bottom())
        self._painter.drawRect(rect2)
        self._painter.setPen(old_pen)

    def _draw_arrow_drag_lock(self):
        """
        Draws the expansion arrow on the nodes that need it
        """

        self._painter.save()
        old_brush = self._painter.brush()
        if self.item.is_root() and self.item.childCount() > 0:
            padding = 3
            self._painter.translate(
                self._rect.left() + padding, self._rect.top() + 2
            )
            arrow = self.COLLAPSED_ARROW
            if self.item.isExpanded():
                arrow = self.EXPANDED_ARROW
            self._painter.setBrush(self.ARROW_COLOR)
            self._painter.setPen(QtCore.Qt.NoPen)
            self._painter.drawPolygon(arrow)
            self._painter.setBrush(old_brush)
        else:
            rect2 = copy.deepcopy(self._rect)
            padding = 26
            new_rect = QtCore.QRect()
            new_rect.setRight(rect2.left() + padding)
            new_rect.setLeft(new_rect.right() - self.ICON_WIDTH_NO_DPI)
            new_rect.setBottom(rect2.top() - self.ICON_WIDTH + 6)
            new_rect.setTop(new_rect.bottom() + self.ICON_WIDTH)
            icon = self.DRAG_HANDLE_IMAGE
            self._painter.drawPixmap(new_rect, icon)
        self._painter.setBrush(old_brush)
        self._painter.restore()

    def _draw_text(self):
        """
        Draws node name
        """

        old_pen = self._painter.pen()
        draw_enabled = True
        if not self.item.node.is_root and not self.item.network_enabled():
            draw_enabled = False
        if self.item.node.enabled and draw_enabled:
            self._painter.setPen(
                QtGui.QPen(self.parent().palette().text().color(), 1)
            )
        else:
            self._painter.setPen(QtGui.QPen(self.item.get_inactive_color(), 1))
        text_rect = copy.deepcopy(self._rect)
        text_rect.setBottom(text_rect.bottom() + 2)
        text_rect.setLeft(text_rect.left() + 40 + self.ICON_PADDING)
        text_rect.setRight(text_rect.right() - 11)
        self._painter.drawText(
            text_rect,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
            self.item.get_display_name(),
        )
        self._painter.setPen(old_pen)

        return text_rect

    def _draw_icon(self, text_rect):
        """
        Internal function that draws the node icon
        """

        rect2 = copy.deepcopy(text_rect)
        icon = None
        icon = self.item.get_icon()
        if icon:
            new_rect = QtCore.QRect()
            new_rect.setRight(rect2.left() - 4)
            new_rect.setLeft(new_rect.right() - self.ICON_WIDTH_NO_DPI)
            new_rect.setBottom(rect2.top() - self.ICON_WIDTH + 3)
            new_rect.setTop(new_rect.bottom() + self.ICON_WIDTH)
            draw_enabled = True
            if not self.item.node.is_root and not self.item.network_enabled():
                draw_enabled = False
            if not self.item.node.enabled or not draw_enabled:
                self._painter.setOpacity(0.5)
            self._painter.drawPixmap(new_rect, icon)

    def _draw_action(self, action_name, pixmap, left, top):
        """
        Internal function that draws the icons for this node.
        """

        if pixmap is not None:
            icon_rect = QtCore.QRect(
                left, top, self.ICON_WIDTH, self.ICON_WIDTH
            )
            p = self.parent().mapFromGlobal(QtGui.QCursor.pos())
            if not icon_rect.contains(p):
                self._painter.setOpacity(1.0)
            else:
                self.parent().last_hit_action = action_name
                pixmap = self._rollover_icon(pixmap)
            self._painter.drawPixmap(icon_rect, pixmap)
            self._painter.setOpacity(1.0)

    def _rollover_icon(self, pixmap):
        img = QtGui.QImage(
            pixmap.toImage().convertToFormat(QtGui.QImage.Format_ARGB32)
        )
        imgh = img.height()
        imgw = img.width()
        for y in range(0, imgh, 1):
            for x in range(0, imgw, 1):
                pixel = img.pixel(x, y)
                high_limit = 205
                low_limit = 30
                adjustment = 255 - high_limit
                color = QtGui.QColor(pixel)
                v = color.value()
                s = color.saturation()
                h = color.hue()
                if v > low_limit:
                    if v < high_limit:
                        v = v + adjustment
                    else:
                        v = 255
                v = color.setHsv(h, s, v)
                img.setPixel(
                    x,
                    y,
                    QtGui.qRgba(
                        color.red(),
                        color.green(),
                        color.blue(),
                        QtGui.qAlpha(pixel),
                    ),
                )

        return QtGui.QPixmap(img)

    def _add_action_icons(self):
        """
        Internal function that draws the icons, buttons and tags on the right hand side of the cell
        """

        top = self._rect.top() + self.ICON_TOP_OFFSET

        start = self.ACTION_BORDER
        count = self._item.get_action_button_count()

        for i in range(count):
            extra_padding = 0
            checked = False
            pixmap = None
            action_name = self._item.get_action_button(i)
            if action_name == "Enabled":
                show_enabled_button = self.item.has_enable_toggle()
                if not show_enabled_button:
                    start += self.ACTION_WIDTH + extra_padding
                    continue
                extra_padding = 10
                pixmap = self.ENABLED_IMAGE
                if not self.item.is_root() and not self.item.network_enabled():
                    pixmap = self.INACTIVE_ENABLED_IMAGE
                checked = self.item.is_enabled()
                if not checked:
                    pixmap = self.DISABLED_IMAGE
                if self._is_highlighted and checked:
                    pixmap = self.ENABLED_SELECTED_IMAGE
            elif action_name == "Add":
                pixmap = self.ADD_IMAGE
            elif action_name == "Remove":
                pixmap = self.REMOVE_IMAGE

            start += self.ACTION_WIDTH + extra_padding
            self._draw_action(
                action_name, pixmap, self._rect.right() - start, top
            )
