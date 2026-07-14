"""Left-side tool strip for the anim picker canvas (Photoshop-style).

``PickerToolBar`` is a thin vertical strip on the left of the picker canvas.
For now it hosts the exclusive edit *tools* that gate on-canvas behavior:

- **Select** (default): click / marquee select and drag-move items.
- **Transform**: additionally shows the on-canvas scale/rotate manipulator so
  the transform handles are opt-in rather than always drawn.

It is built to grow: future quick-access *command* buttons (duplicate, mirror,
...) attach below the tools via ``add_command`` without disturbing the tool
group.
"""

from functools import partial

from mgear.core import pyqt
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets


# Tool identifiers, also read by the view to gate the manipulator.
TOOL_SELECT = "select"
TOOL_TRANSFORM = "transform"

# Drag-and-drop mime type carrying a widget-type payload from a palette tile to
# the canvas (the view creates the item at the drop position).
WIDGET_MIME = "application/x-mgear-anim-picker-item"

# Palette payload for a backdrop container (not a widget_binding type).
BACKDROP_PAYLOAD = "backdrop"


def maya_icon(resource):
    """Return a QIcon for a Maya resource path (e.g. ``:/aselect.png``)."""
    return QtGui.QIcon(resource)


def mgear_icon(name):
    """Return a QIcon for an mGear SVG icon name (from release/icons)."""
    try:
        return QtGui.QIcon(pyqt.get_icon(name))
    except Exception:
        return QtGui.QIcon()


class DragTileButton(QtWidgets.QToolButton):
    """A draggable tile: a drag carries ``payload`` as ``mime`` to the drop.

    The drop target (the picker view) reads the payload and creates the item at
    the drop position. A plain click still emits ``clicked``; an optional
    double-click callback offers a create-at-center alternative to dragging.
    Shared by the left-strip palette tiles and the shape-library tiles.
    """

    def __init__(self, mime, payload, icon_size=22, parent=None):
        super(DragTileButton, self).__init__(parent)
        self._mime = mime
        self._payload = payload
        self._icon_size = icon_size
        self._press_pos = None
        self._double_callback = None

    def set_double_callback(self, callback):
        """Set the callback invoked on a double-click (create at center)."""
        self._double_callback = callback

    def mouseDoubleClickEvent(self, event):
        if self._double_callback is not None:
            self._double_callback()
        super(DragTileButton, self).mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press_pos = event.pos()
        super(DragTileButton, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Start the drag once the cursor has moved past the drag threshold;
        # below it, fall through so a plain click still registers.
        if (
            not (event.buttons() & QtCore.Qt.LeftButton)
            or self._press_pos is None
        ):
            super(DragTileButton, self).mouseMoveEvent(event)
            return
        moved = (event.pos() - self._press_pos).manhattanLength()
        if moved < QtWidgets.QApplication.startDragDistance():
            super(DragTileButton, self).mouseMoveEvent(event)
            return
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData(self._mime, self._payload.encode("utf-8"))
        drag.setMimeData(mime)
        icon = self.icon()
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(self._icon_size, self._icon_size))
        drag.exec_(QtCore.Qt.CopyAction)
        self._press_pos = None


class PaletteButton(DragTileButton):
    """A palette tile that creates a picker item / widget on drop.

    A thin ``DragTileButton`` carrying the widget type as ``WIDGET_MIME`` (the
    view's drop handler creates the item at the drop position).
    """

    def __init__(self, payload, parent=None):
        super(PaletteButton, self).__init__(
            WIDGET_MIME, payload, parent=parent
        )


class PickerToolBar(QtWidgets.QWidget):
    """Vertical tool strip that drives the active picker tool."""

    _BUTTON_SIZE = 34
    _ICON_SIZE = 22

    def __init__(self, main_window=None, parent=None):
        super(PickerToolBar, self).__init__(parent)
        self.main_window = main_window

        # Keep the strip at its natural (narrow) width; the canvas takes the
        # remaining space in the enclosing row.
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred
        )

        self.tool_group = QtWidgets.QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self._tool_buttons = {}

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(2)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        # Tools use the default Maya tool icons.
        self._add_tool(
            TOOL_SELECT,
            "Sel",
            "Select tool: click / marquee select and drag to move items",
            maya_icon(":/aselect.png"),
            checked=True,
        )
        self._add_tool(
            TOOL_TRANSFORM,
            "Xfrm",
            "Transform tool: show on-canvas scale / rotate handles",
            maya_icon(":/move_M.png"),
            checked=False,
        )

        self.main_layout.addStretch()

    def _style_button(self, button, label, tooltip, icon):
        """Apply the shared strip button look, using an icon when available.

        Args:
            button (QToolButton): the button to style.
            label (str): short text fallback when ``icon`` is null.
            tooltip (str): hover description.
            icon (QtGui.QIcon): icon to show, or a null icon for text.
        """
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setFixedWidth(self._BUTTON_SIZE)
        button.setMinimumHeight(self._BUTTON_SIZE)
        if icon is not None and not icon.isNull():
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(self._ICON_SIZE, self._ICON_SIZE))
            button.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        else:
            button.setText(label)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)

    def _add_tool(self, name, label, tooltip, icon, checked=False):
        """Add an exclusive tool toggle button."""
        button = QtWidgets.QToolButton()
        button.setCheckable(True)
        button.setChecked(checked)
        self._style_button(button, label, tooltip, icon)
        button.clicked.connect(partial(self._tool_clicked, name))
        self.tool_group.addButton(button)
        self._tool_buttons[name] = button
        self.main_layout.addWidget(button)

    def add_command(self, label, tooltip, callback, icon=None):
        """Add a non-exclusive quick-access command button below the tools.

        Args:
            label (str): short button label (used when ``icon`` is null).
            tooltip (str): hover description.
            callback (callable): invoked on click.
            icon (QtGui.QIcon, optional): icon to show.

        Returns:
            QtWidgets.QToolButton: the created button.
        """
        button = QtWidgets.QToolButton()
        self._style_button(button, label, tooltip, icon)
        button.clicked.connect(callback)
        # Insert before the trailing stretch.
        self.main_layout.insertWidget(self.main_layout.count() - 1, button)
        return button

    def add_separator(self):
        """Add a thin horizontal divider above the trailing stretch."""
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setStyleSheet("color: #4a4a4a;")
        self.main_layout.insertWidget(self.main_layout.count() - 1, line)
        return line

    def add_section_label(self, text):
        """Add a small centered section label above the trailing stretch."""
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = label.font()
        font.setPointSizeF(max(6.0, font.pointSizeF() - 2.0))
        label.setFont(font)
        label.setStyleSheet("color: #9a9a9a;")
        self.main_layout.insertWidget(self.main_layout.count() - 1, label)
        return label

    def add_button_grid(self, specs, columns=2):
        """Add a compact grid of icon command buttons above the stretch.

        Args:
            specs (list): ``(tooltip, callback, icon)`` per button.
            columns (int): number of columns in the grid.

        Returns:
            list: the created QToolButtons.
        """
        container = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)
        buttons = []
        for index, (tooltip, callback, icon) in enumerate(specs):
            button = QtWidgets.QToolButton()
            button.setToolTip(tooltip)
            button.setAutoRaise(True)
            button.setFixedSize(QtCore.QSize(26, 26))
            if icon is not None and not icon.isNull():
                button.setIcon(icon)
                button.setIconSize(QtCore.QSize(18, 18))
            button.clicked.connect(callback)
            grid.addWidget(button, index // columns, index % columns)
            buttons.append(button)
        self.main_layout.insertWidget(self.main_layout.count() - 1, container)
        return buttons

    def add_palette_item(
        self, label, tooltip, payload, icon=None, double_callback=None
    ):
        """Add a draggable palette tile that creates ``payload`` on drop.

        Args:
            label (str): short tile label (used when ``icon`` is null).
            tooltip (str): hover description.
            payload (str): widget-type string carried by the drag.
            icon (QtGui.QIcon, optional): icon to show.
            double_callback (callable, optional): invoked on a double-click
                (creates the item at the canvas center as an alternative to
                dragging).

        Returns:
            PaletteButton: the created draggable tile.
        """
        button = PaletteButton(payload)
        self._style_button(button, label, tooltip, icon)
        if double_callback is not None:
            button.set_double_callback(double_callback)
        self.main_layout.insertWidget(self.main_layout.count() - 1, button)
        return button

    def _tool_clicked(self, name):
        if self.main_window is not None:
            self.main_window.set_active_tool(name)

    def active_tool(self):
        """Return the identifier of the currently checked tool."""
        for name, button in self._tool_buttons.items():
            if button.isChecked():
                return name
        return TOOL_SELECT
