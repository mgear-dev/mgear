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


def maya_icon(resource):
    """Return a QIcon for a Maya resource path (e.g. ``:/aselect.png``)."""
    return QtGui.QIcon(resource)


def mgear_icon(name):
    """Return a QIcon for an mGear SVG icon name (from release/icons)."""
    try:
        return QtGui.QIcon(pyqt.get_icon(name))
    except Exception:
        return QtGui.QIcon()


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

    def _tool_clicked(self, name):
        if self.main_window is not None:
            self.main_window.set_active_tool(name)

    def active_tool(self):
        """Return the identifier of the currently checked tool."""
        for name, button in self._tool_buttons.items():
            if button.isChecked():
                return name
        return TOOL_SELECT
