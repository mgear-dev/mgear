"""Evaluation Partition Tool - Custom Qt Widgets.

This module contains reusable Qt widgets for the Evaluation Partition tool UI.
"""

from mgear.vendor.Qt import QtWidgets, QtCore, QtGui

from maya import cmds

from . import core


# =====================================================
# GROUP LIST ITEM WIDGET
# =====================================================


class GroupListItem(QtWidgets.QWidget):
    """Custom widget for polygon group list items.

    Displays: [ColorButton] [Name LineEdit] [Select Btn] [Remove Btn]

    Args:
        group: The PolygonGroup this item represents.
        is_default: Whether this is the default (non-removable) group.
        parent: Parent widget.

    Signals:
        color_changed(str, tuple): Emitted when color changes (group_name, new_color).
        name_changed(str, str): Emitted when name changes (old_name, new_name).
        select_clicked(str): Emitted when select button clicked (group_name).
        removed(str): Emitted when remove button clicked (group_name).
    """

    color_changed = QtCore.Signal(str, object)
    name_changed = QtCore.Signal(str, str)
    select_clicked = QtCore.Signal(str)
    removed = QtCore.Signal(str)

    def __init__(self, group, is_default=False, parent=None):
        super(GroupListItem, self).__init__(parent)

        self.group = group
        self.is_default = is_default
        self._original_name = group.name

        self._create_widgets()
        self._create_layout()
        self._create_connections()
        self._update_color_button()

    def _create_widgets(self):
        """Create all widgets."""
        # Color button (square, shows current color)
        self.color_btn = QtWidgets.QPushButton()
        self.color_btn.setFixedSize(24, 24)
        self.color_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.color_btn.setToolTip("Click to change color")

        # Editable name
        self.name_edit = QtWidgets.QLineEdit(self.group.name)
        self.name_edit.setMinimumWidth(100)
        if self.is_default:
            self.name_edit.setReadOnly(True)
            self.name_edit.setStyleSheet("color: #888;")

        # Face count label
        face_count = len(self.group.face_indices)
        self.face_count_label = QtWidgets.QLabel(f"({face_count})")
        self.face_count_label.setStyleSheet("color: #888;")
        self.face_count_label.setFixedWidth(60)

        # Select button
        self.select_btn = QtWidgets.QPushButton("Select")
        self.select_btn.setFixedWidth(50)
        self.select_btn.setToolTip("Select faces in Maya viewport")

        # Remove button
        self.remove_btn = QtWidgets.QPushButton("X")
        self.remove_btn.setFixedWidth(25)
        self.remove_btn.setToolTip("Remove this group")
        if self.is_default:
            self.remove_btn.setEnabled(False)
            self.remove_btn.setStyleSheet("background-color: #555;")
        else:
            self.remove_btn.setStyleSheet("background-color: #aa4444;")

    def _create_layout(self):
        """Arrange widgets in layout."""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        layout.addWidget(self.color_btn)
        layout.addWidget(self.name_edit)
        layout.addWidget(self.face_count_label)
        layout.addStretch()
        layout.addWidget(self.select_btn)
        layout.addWidget(self.remove_btn)

    def _create_connections(self):
        """Connect signals to slots."""
        self.color_btn.clicked.connect(self._on_color_clicked)
        self.name_edit.editingFinished.connect(self._on_name_edited)
        self.select_btn.clicked.connect(self._on_select_clicked)
        self.remove_btn.clicked.connect(self._on_remove_clicked)

    def _update_color_button(self):
        """Update the color button appearance."""
        r, g, b = self.group.color
        # Convert to 0-255 range for stylesheet
        r_int = int(r * 255)
        g_int = int(g * 255)
        b_int = int(b * 255)
        self.color_btn.setStyleSheet(
            f"background-color: rgb({r_int}, {g_int}, {b_int}); "
            "border: 1px solid #666; border-radius: 2px;"
        )

    def update_face_count(self):
        """Update the face count label."""
        face_count = len(self.group.face_indices)
        self.face_count_label.setText(f"({face_count})")

    def _on_color_clicked(self):
        """Open color dialog."""
        r, g, b = self.group.color
        initial_color = QtGui.QColor.fromRgbF(r, g, b)

        color = QtWidgets.QColorDialog.getColor(
            initial_color,
            parent=self,
            options=QtWidgets.QColorDialog.DontUseNativeDialog,
        )

        if color.isValid():
            new_color = (color.redF(), color.greenF(), color.blueF())
            self.group.color = new_color
            self._update_color_button()
            self.color_changed.emit(self.group.name, new_color)

    def _on_name_edited(self):
        """Handle name edit finished."""
        new_name = self.name_edit.text().strip()
        if not new_name:
            # Revert to original name
            self.name_edit.setText(self._original_name)
            return

        if new_name != self._original_name:
            old_name = self._original_name
            self._original_name = new_name
            self.name_changed.emit(old_name, new_name)

    def _on_select_clicked(self):
        """Handle select button click."""
        self.select_clicked.emit(self.group.name)

    def _on_remove_clicked(self):
        """Handle remove button click."""
        self.removed.emit(self.group.name)


# =====================================================
# GROUP LIST WIDGET
# =====================================================


class GroupListWidget(QtWidgets.QWidget):
    """Widget for managing the list of polygon groups.

    Provides a scrollable list of GroupListItem widgets with an add button.

    Args:
        parent: Parent widget.

    Signals:
        group_added(): Emitted when add button is clicked.
        group_removed(str): Emitted when a group is removed (group_name).
        group_selected(str): Emitted when a group's select button is clicked (group_name).
        color_changed(str, tuple): Emitted when a group's color changes.
        name_changed(str, str): Emitted when a group's name changes.
    """

    group_added = QtCore.Signal()
    group_removed = QtCore.Signal(str)
    group_selected = QtCore.Signal(str)
    color_changed = QtCore.Signal(str, object)
    name_changed = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super(GroupListWidget, self).__init__(parent)

        self._items = {}  # group_name -> GroupListItem

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self):
        """Create all widgets."""
        # Scroll area for group items
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setMinimumHeight(150)

        # Container widget for items
        self.scroll_content = QtWidgets.QWidget()
        self.items_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(2)
        self.items_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)

        # Add group button
        self.add_btn = QtWidgets.QPushButton("Add Group from Selection")
        self.add_btn.setMinimumHeight(30)
        self.add_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #4a7c4e;"
            "    color: white;"
            "    font-weight: bold;"
            "    border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "    background-color: #5a8c5e;"
            "}"
            "QPushButton:pressed {"
            "    background-color: #3a6c3e;"
            "}"
        )

    def _create_layout(self):
        """Arrange widgets in layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.scroll_area)
        layout.addWidget(self.add_btn)

    def _create_connections(self):
        """Connect signals to slots."""
        self.add_btn.clicked.connect(self._on_add_clicked)

    def _on_add_clicked(self):
        """Handle add button click."""
        self.group_added.emit()

    def add_group_item(self, group, is_default=False):
        """Add a new group item to the list.

        Args:
            group: The PolygonGroup to add.
            is_default: Whether this is the default group.

        Returns:
            The created GroupListItem.
        """
        item = GroupListItem(group, is_default=is_default, parent=self)

        # Connect item signals
        item.color_changed.connect(self._on_item_color_changed)
        item.name_changed.connect(self._on_item_name_changed)
        item.select_clicked.connect(self._on_item_select_clicked)
        item.removed.connect(self._on_item_removed)

        # Insert before the stretch
        count = self.items_layout.count()
        self.items_layout.insertWidget(count - 1, item)

        self._items[group.name] = item

        return item

    def remove_group_item(self, group_name):
        """Remove a group item from the list.

        Args:
            group_name: Name of the group to remove.
        """
        item = self._items.get(group_name)
        if item:
            self.items_layout.removeWidget(item)
            item.deleteLater()
            del self._items[group_name]

    def clear_all(self):
        """Clear all group items."""
        for item in list(self._items.values()):
            self.items_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def get_group_items(self):
        """Get all GroupListItem widgets.

        Returns:
            List of GroupListItem widgets.
        """
        return list(self._items.values())

    def update_all_face_counts(self):
        """Update face counts for all items."""
        for item in self._items.values():
            item.update_face_count()

    def _on_item_color_changed(self, group_name, new_color):
        """Handle item color change."""
        self.color_changed.emit(group_name, new_color)

    def _on_item_name_changed(self, old_name, new_name):
        """Handle item name change."""
        # Update internal mapping
        if old_name in self._items:
            item = self._items.pop(old_name)
            self._items[new_name] = item
        self.name_changed.emit(old_name, new_name)

    def _on_item_select_clicked(self, group_name):
        """Handle item select click."""
        self.group_selected.emit(group_name)

    def _on_item_removed(self, group_name):
        """Handle item removal."""
        self.group_removed.emit(group_name)
