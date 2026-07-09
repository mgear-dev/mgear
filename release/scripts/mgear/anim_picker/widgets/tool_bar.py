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

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets


# Tool identifiers, also read by the view to gate the manipulator.
TOOL_SELECT = "select"
TOOL_TRANSFORM = "transform"


class PickerToolBar(QtWidgets.QWidget):
    """Vertical tool strip that drives the active picker tool."""

    _BUTTON_SIZE = 34

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

        self._add_tool(
            TOOL_SELECT,
            "Sel",
            "Select tool: click / marquee select and drag to move items",
            ":/aselect.png",
            checked=True,
        )
        self._add_tool(
            TOOL_TRANSFORM,
            "Xfrm",
            "Transform tool: show on-canvas scale / rotate handles",
            ":/move_M.png",
            checked=False,
        )

        self.main_layout.addStretch()

    def _style_button(self, button, label, tooltip, icon_resource):
        """Apply the shared strip button look, using an icon when available."""
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setFixedWidth(self._BUTTON_SIZE)
        button.setMinimumHeight(self._BUTTON_SIZE)
        # Prefer a Maya resource icon; fall back to a short text label so the
        # strip is usable even when the resource is absent.
        icon = QtGui.QIcon(icon_resource) if icon_resource else QtGui.QIcon()
        if not icon.isNull():
            button.setIcon(icon)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        else:
            button.setText(label)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)

    def _add_tool(self, name, label, tooltip, icon_resource, checked=False):
        """Add an exclusive tool toggle button."""
        button = QtWidgets.QToolButton()
        button.setCheckable(True)
        button.setChecked(checked)
        self._style_button(button, label, tooltip, icon_resource)
        button.clicked.connect(partial(self._tool_clicked, name))
        self.tool_group.addButton(button)
        self._tool_buttons[name] = button
        self.main_layout.addWidget(button)

    def add_command(self, label, tooltip, callback, icon_resource=None):
        """Add a non-exclusive quick-access command button below the tools.

        Reserved for future commands (duplicate, mirror, ...); returns the
        created button so callers can enable/disable it with the selection.

        Args:
            label (str): short button label (used when no icon is available).
            tooltip (str): hover description.
            callback (callable): invoked on click.
            icon_resource (str, optional): icon resource path.

        Returns:
            QtWidgets.QToolButton: the created button.
        """
        button = QtWidgets.QToolButton()
        self._style_button(button, label, tooltip, icon_resource)
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
