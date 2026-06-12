"""mGear Qt custom widgets"""

from mgear.vendor.Qt import QtCore, QtWidgets, QtGui
import maya.OpenMaya as api
from mgear.core import pyqt


#################################################
# CUSTOM WIDGETS
#################################################


class TableWidgetDragRows(QtWidgets.QTableWidget):
    """qTableWidget with drag and drop functionality"""

    def __init__(self, *args, **kwargs):
        super(TableWidgetDragRows, self).__init__(*args, **kwargs)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    def dropEvent(self, event):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = [
                [
                    QtWidgets.QTableWidgetItem(
                        self.item(row_index, column_index)
                    )
                    for column_index in range(self.columnCount())
                ]
                for row_index in rows
            ]

            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):
                row_index += drop_row
                self.insertRow(row_index)
                for column_index, column_data in enumerate(data):
                    self.setItem(row_index, column_index, column_data)
            event.accept()
            for row_index in range(len(rows_to_move)):
                for column_index in range(self.columnCount()):
                    self.item(drop_row + row_index, column_index).setSelected(
                        True
                    )

    def drop_on(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()

        return (
            index.row() + 1
            if self.is_below(event.pos(), index)
            else index.row()
        )

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        return (
            rect.contains(pos, True)
            and not (
                int(self.model().flags(index)) & QtCore.Qt.ItemIsDropEnabled
            )
            and pos.y() >= rect.center().y()
        )

    def getSelectedRowsFast(self):
        selRows = []
        for item in self.selectedItems():
            if item.row() not in selRows:
                selRows.append(item.row())
        return selRows

    def droppingOnItself(self, event, index):
        dropAction = event.dropAction()

        if self.dragDropMode() == QtWidgets.QAbstractItemView.InternalMove:
            dropAction = QtCore.Qt.MoveAction

        if (
            event.source() == self
            and event.possibleActions() & QtCore.Qt.MoveAction
            and dropAction == QtCore.Qt.MoveAction
        ):
            selectedIndexes = self.selectedIndexes()
            child = index
            while child.isValid() and child != self.rootIndex():
                if child in selectedIndexes:
                    return True
                child = child.parent()

        return False

    def dropOn(self, event):
        if event.isAccepted():
            return False, None, None, None

        index = QtWidgets.QModelIndex()
        row = -1
        col = -1

        if self.viewport().rect().contains(event.pos()):
            index = self.indexAt(event.pos())
            if not index.isValid() or not self.visualRect(index).contains(
                event.pos()
            ):
                index = self.rootIndex()

        if self.model().supportedDropActions() & event.dropAction():
            if index != self.rootIndex():
                dropIndicatorPosition = self.position(
                    event.pos(), self.visualRect(index), index
                )
                qabw = QtWidgets.QAbstractItemView
                if dropIndicatorPosition == qabw.AboveItem:
                    row = index.row()
                    col = index.column()
                elif dropIndicatorPosition == qabw.BelowItem:
                    row = index.row() + 1
                    col = index.column()
                else:
                    row = index.row()
                    col = index.column()

            if not self.droppingOnItself(event, index):
                return True, row, col, index

        return False, None, None, None

    def position(self, pos, rect, index):
        r = QtWidgets.QAbstractItemView.OnViewport
        margin = 5
        if pos.y() - rect.top() < margin:
            r = QtWidgets.QAbstractItemView.AboveItem
        elif rect.bottom() - pos.y() < margin:
            r = QtWidgets.QAbstractItemView.BelowItem
        elif rect.contains(pos, True):
            r = QtWidgets.QAbstractItemView.OnItem

        if r == QtWidgets.QAbstractItemView.OnItem and not (
            self.model().flags(index) & QtCore.Qt.ItemIsDropEnabled
        ):
            if pos.y() < rect.center().y():
                r = QtWidgets.QAbstractItemView.AboveItem
            else:
                r = QtWidgets.QAbstractItemView.BelowItem

        return r


######################################
# drag and drop QListView to Maya view
######################################


def selectFromScreenApi(x, y, x_rect=None, y_rect=None):
    """Find the object under the cursor on Maya view


    found here: http://nathanhorne.com/maya-python-selectfromscreen/
    Thanks Nathan!
    Args:
        x (int): rectable selection start x
        y (int): rectagle selection start y
        x_rect (int, optional): rectable selection end x
        y_rect (int, optional): rectagle selection end y

    Returns:
        list of str: Name of the objects under the cursor
    """
    # get current selection
    sel = api.MSelectionList()
    api.MGlobal.getActiveSelectionList(sel)

    # select from screen
    if x_rect is not None and y_rect is not None:
        api.MGlobal.selectFromScreen(
            x, y, x_rect, y_rect, api.MGlobal.kReplaceList
        )
    else:
        api.MGlobal.selectFromScreen(x, y, api.MGlobal.kReplaceList)
    objects = api.MSelectionList()
    api.MGlobal.getActiveSelectionList(objects)

    # restore selection
    api.MGlobal.setActiveSelectionList(sel, api.MGlobal.kReplaceList)

    # return the objects as strings
    fromScreen = []
    objects.getSelectionStrings(fromScreen)
    return fromScreen


class DragQListView(QtWidgets.QListView):
    """QListView with basic drop functionality

    Attributes:
        exp (int): Extend the mouse position to a rectable
        theAction (func): function triggered when drop
    """

    def __init__(self, parent):
        super(DragQListView, self).__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setDefaultDropAction(QtCore.Qt.CopyAction)
        self.exp = 3
        self.ignore_self = True

    def mouseMoveEvent(self, event):
        mimeData = QtCore.QMimeData()
        mimeData.setText("%d,%d" % (event.x(), event.y()))

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setHotSpot(event.pos())
        try:
            dropAction = drag.start(QtCore.Qt.MoveAction)  # PySide2
        except AttributeError:
            dropAction = drag.exec(QtCore.Qt.MoveAction)  # PySide6
        if not dropAction == QtCore.Qt.MoveAction:
            pos = QtGui.QCursor.pos()
            widget = QtWidgets.QApplication.widgetAt(pos)
            if self.ignore_self and (
                widget is self
                or widget.objectName() == "qt_scrollarea_viewport"
            ):
                return
            relpos = widget.mapFromGlobal(pos)
            # need to invert Y axis
            invY = widget.frameSize().height() - relpos.y()
            sel = selectFromScreenApi(
                relpos.x() - self.exp,
                invY - self.exp,
                relpos.x() + self.exp,
                invY + self.exp,
            )

            self.doAction(sel)

    def setAction(self, action):
        self.theAction = action

    def doAction(self, sel):
        self.theAction(sel)


######################################
# collapsible widget
######################################


class CollapsibleHeader(QtWidgets.QWidget):
    COLLAPSED_PIXMAP = QtGui.QPixmap(":teRightArrow.png")
    EXPANDED_PIXMAP = QtGui.QPixmap(":teDownArrow.png")

    clicked = QtCore.Signal()

    def __init__(self, text, parent=None):
        super(CollapsibleHeader, self).__init__(parent)

        self.setAutoFillBackground(True)
        self.set_background_color(None)

        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedWidth(self.COLLAPSED_PIXMAP.width())

        self.text_label = QtWidgets.QLabel()
        self.text_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.addWidget(self.icon_label)
        self.main_layout.addWidget(self.text_label)

        self.set_text(text)
        self.set_expanded(True)

    def set_text(self, text):
        self.text_label.setText("<b>{0}</b>".format(text))

    def set_background_color(self, color):
        if not color:
            color = (
                QtWidgets.QPushButton().palette().color(QtGui.QPalette.Button)
            )

        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, color)
        self.setPalette(palette)

    def is_expanded(self):
        return self._expanded

    def set_expanded(self, expanded):
        self._expanded = expanded

        if self._expanded:
            self.icon_label.setPixmap(self.EXPANDED_PIXMAP)
        else:
            self.icon_label.setPixmap(self.COLLAPSED_PIXMAP)

    def mouseReleaseEvent(self, event):
        self.clicked.emit()


class CollapsibleWidget(QtWidgets.QWidget):
    def __init__(self, text, expanded=True, expandable=True, parent=None):
        """Create a collapsible widget with header and body.

        Args:
            text: Header text
            expanded: Initial expanded state
            expandable: If True, widget expands to fill available space when
                       expanded. If False, widget stays fixed size.
            parent: Parent widget
        """
        super(CollapsibleWidget, self).__init__(parent)

        self._expandable = expandable
        self.header_wgt = CollapsibleHeader(text)
        self.header_wgt.clicked.connect(self.on_header_clicked)
        self.body_wgt = QtWidgets.QWidget()

        self.body_layout = QtWidgets.QVBoxLayout(self.body_wgt)
        self.body_layout.setContentsMargins(4, 2, 4, 2)
        self.body_layout.setSpacing(3)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.header_wgt)
        self.main_layout.addWidget(self.body_wgt)

        self.set_expanded(expanded)

    def addWidget(self, widget):
        self.body_layout.addWidget(widget)

    def addLayout(self, layout):
        self.body_layout.addLayout(layout)

    def set_expanded(self, expanded):
        self.header_wgt.set_expanded(expanded)
        self.body_wgt.setVisible(expanded)
        # Update size policy based on expanded state and expandable setting
        if expanded and self._expandable:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Expanding
            )
        else:
            self.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Fixed
            )

    def set_header_background_color(self, color):
        self.header_wgt.set_background_color(color)

    def on_header_clicked(self):
        self.set_expanded(not self.header_wgt.is_expanded())


##################
# Helper functions
##################


def create_button(
    size=17,
    text=None,
    icon=None,
    toggle_icon=None,
    icon_size=None,
    toolTip=None,
    width=None,
    setMax=True,
):
    """Create and configure a QPushButton

    Args:
        size (int, optional): Size of the button
        text (str, optional): Text of the button
        icon (str, optional): Icon name
        toggle_icon (str, optional): Toggle icon name. If exist will make
                                     the button checkable
        icon_size (int, optional): Icon size
        toolTip (str, optional): Buttom tool tip

    Returns:
        QPushButton: The reated button
    """
    button = QtWidgets.QPushButton()
    if not width:
        width = size
    button.setMinimumHeight(size)
    button.setMinimumWidth(width)
    if setMax:
        button.setMaximumHeight(size)
        button.setMaximumWidth(width)

    if toolTip:
        button.setToolTip(toolTip)

    if text:
        button.setText(text)

    if icon:
        if not icon_size:
            icon_size = size - 3
        button.setIcon(pyqt.get_icon(icon, icon_size))
        # button.setIconSize(QtCore.QSize(icon_size, icon_size))

    if toggle_icon:
        button.setCheckable(True)

        def changeIcon(
            button=button, icon=icon, toggle_icon=toggle_icon, size=icon_size
        ):
            if button.isChecked():
                button.setIcon(pyqt.get_icon(toggle_icon, size))
            else:
                button.setIcon(pyqt.get_icon(icon, size))
            # button.setIconSize(QtCore.QSize(icon_size, icon_size))

        button.clicked.connect(changeIcon)

    return button


#########################
# Widget Settings Manager
#########################


class WidgetSettingsManager(QtCore.QSettings):
    widget_map = {
        "QCheckBox": ("isChecked", "setChecked", bool, False),
        "QComboBox": ("currentIndex", "setCurrentIndex", int, 0),
        "QLineEdit": ("text", "setText", str, ""),
        "QListWidget": (None, None, str, ""),
    }

    def __init__(self, ui_name, parent=None):
        super(WidgetSettingsManager, self).__init__(parent)
        self.settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "mcsGear",
            ui_name,
        )

    def _get_listwidget_item_names(self, listwidget):
        items = [listwidget.item(i).text() for i in range(listwidget.count())]
        item_string = ",".join(items)
        return item_string

    def _add_listwidget_items(self, name, listwidget):
        value = self.settings.value(name, type=str)
        if not value or value == "0":
            return
        items = value.split(",")
        current_items = self._get_listwidget_item_names(listwidget)
        for item in items:
            if item not in current_items:
                listwidget.addItem(item)

    def save_ui_state(self, widget_dict):
        for name, widget in widget_dict.items():
            class_name = widget.__class__.__name__
            if class_name not in self.widget_map:
                continue
            if class_name == "QListWidget":
                value = self._get_listwidget_item_names(widget)
                self.settings.setValue(name, value)
                continue
            getter, _, _, _ = self.widget_map.get(class_name)
            if not getter:
                return
            get_function = getattr(widget, getter)
            value = get_function()
            if value is not None:
                self.settings.setValue(name, value)

    def load_ui_state(self, widget_dict, reset=False):
        for name, widget in widget_dict.items():
            class_name = widget.__class__.__name__
            if class_name not in self.widget_map:
                continue
            if class_name == "QListWidget":
                self._add_listwidget_items(name, widget)
                continue
            _, setter, dtype, default_value = self.widget_map.get(class_name)
            if not setter:
                return
            value = self.settings.value(name, type=dtype)
            if reset:
                value = default_value
            if value is not None:
                set_function = getattr(widget, setter)
                try:
                    set_function(value)
                except Exception as e:
                    print(e)
