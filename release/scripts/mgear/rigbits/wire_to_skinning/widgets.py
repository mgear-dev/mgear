"""Wire to Skinning - Custom Qt widgets.

This module contains reusable Qt widgets for the Wire to Skinning tool UI.
"""

# mGear
from mgear.core import pyqt

from mgear.vendor.Qt import QtWidgets, QtCore

# Maya
from maya import cmds

# Relative imports
from . import core

ICON_SIZE = 16


class WireListItem(QtWidgets.QWidget):
    """Custom widget for wire deformer list items.

    Displays a wire deformer name with reorder, select and remove buttons.

    Signals:
        move_up(str): Emitted to move this wire up in the list.
        move_down(str): Emitted to move this wire down in the list.
        removed(str): Emitted when remove button clicked.
    """

    move_up = QtCore.Signal(str)
    move_down = QtCore.Signal(str)
    removed = QtCore.Signal(str)

    def __init__(self, wire_name, parent=None):
        super(WireListItem, self).__init__(parent)

        self.wire_name = wire_name

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # Reorder buttons
        self.up_btn = QtWidgets.QPushButton()
        self.up_btn.setIcon(pyqt.get_icon("mgear_arrow-up", ICON_SIZE))
        self.up_btn.setFixedSize(24, 24)
        self.up_btn.setToolTip("Move up in processing order")
        self.up_btn.clicked.connect(self._on_move_up)
        layout.addWidget(self.up_btn)

        self.down_btn = QtWidgets.QPushButton()
        self.down_btn.setIcon(pyqt.get_icon("mgear_arrow-down", ICON_SIZE))
        self.down_btn.setFixedSize(24, 24)
        self.down_btn.setToolTip("Move down in processing order")
        self.down_btn.clicked.connect(self._on_move_down)
        layout.addWidget(self.down_btn)

        self.label = QtWidgets.QLabel(wire_name)
        self.label.setMinimumWidth(120)
        layout.addWidget(self.label)

        layout.addStretch()

        self.select_btn = QtWidgets.QPushButton()
        self.select_btn.setIcon(
            pyqt.get_icon("mgear_mouse-pointer", ICON_SIZE)
        )
        self.select_btn.setFixedSize(28, 28)
        self.select_btn.setToolTip("Select wire curve")
        self.select_btn.clicked.connect(self._select_wire)
        layout.addWidget(self.select_btn)

        self.remove_btn = QtWidgets.QPushButton()
        self.remove_btn.setIcon(pyqt.get_icon("mgear_trash-2", ICON_SIZE))
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setToolTip("Delete wire deformer")
        self.remove_btn.clicked.connect(self._remove_wire)
        layout.addWidget(self.remove_btn)

    def _on_move_up(self):
        """Emit move up signal."""
        self.move_up.emit(self.wire_name)

    def _on_move_down(self):
        """Emit move down signal."""
        self.move_down.emit(self.wire_name)

    def _select_wire(self):
        """Select the wire curve in Maya."""
        if cmds.objExists(self.wire_name):
            wire_info = core.get_wire_deformer_info(self.wire_name)
            if wire_info["wire_curve"]:
                cmds.select(wire_info["wire_curve"])

    def _remove_wire(self):
        """Emit the removed signal."""
        self.removed.emit(self.wire_name)


class JointListWidget(QtWidgets.QWidget):
    """Widget for managing a list of joints.

    Provides Add Selected, Remove, and Clear functionality.
    """

    def __init__(self, parent=None):
        super(JointListWidget, self).__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # List widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.list_widget.setMinimumHeight(100)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add Selected")
        self.add_btn.clicked.connect(self._add_selected)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QtWidgets.QPushButton("移除")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = QtWidgets.QPushButton("清除")
        self.clear_btn.clicked.connect(self._clear_list)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

    def _add_selected(self):
        """Add selected joints from Maya to the list."""
        selection = cmds.ls(selection=True, type="joint")
        for jnt in selection:
            # Check if already in list
            items = [
                self.list_widget.item(i).text()
                for i in range(self.list_widget.count())
            ]
            if jnt not in items:
                self.list_widget.addItem(jnt)

    def _remove_selected(self):
        """Remove selected items from the list."""
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))

    def _clear_list(self):
        """Clear all items from the list."""
        self.list_widget.clear()

    def get_joints(self):
        """Get all joints in the list.

        Returns:
            list: List of joint names.
        """
        return [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
        ]

    def set_joints(self, joints):
        """Set the joints in the list.

        Args:
            joints (list): List of joint names.
        """
        self.list_widget.clear()
        for jnt in joints:
            self.list_widget.addItem(jnt)
