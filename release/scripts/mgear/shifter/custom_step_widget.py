"""Custom Step Tab widget and mixin for Guide Settings."""

import datetime
import imp
import inspect
import json
import os
import shutil
import subprocess
import sys
import traceback
from functools import partial

import mgear.pymaya as pm
from mgear.core import pyqt
from mgear.core.widgets import CollapsibleWidget
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui

MGEAR_SHIFTER_CUSTOMSTEP_KEY = "MGEAR_SHIFTER_CUSTOMSTEP_PATH"

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)


# ============================================================================
# Custom Step Data Model
# ============================================================================


class CustomStepData(object):
    """Data model for a custom step entry.

    Handles parsing and serializing custom step data from/to the stored format.
    The stored format is: "name | path" or "*name | path" for deactivated steps.

    Attributes:
        name (str): The display name of the custom step (without leading *)
        path (str): The relative or absolute path to the .py file
        active (bool): Whether the step is active (True) or deactivated (False)
    """

    def __init__(self, name="", path="", active=True):
        """Initialize CustomStepData.

        Args:
            name (str): Display name of the step
            path (str): Path to the .py file
            active (bool): Whether step is active
        """
        self._name = name
        self._path = path
        self._active = active

    @property
    def name(self):
        """str: The display name of the custom step."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def path(self):
        """str: The path to the custom step file."""
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def active(self):
        """bool: Whether the step is active."""
        return self._active

    @active.setter
    def active(self, value):
        self._active = bool(value)

    @property
    def is_shared(self):
        """bool: Whether the step is a shared step (path contains '_shared')."""
        return "_shared" in self._path

    @classmethod
    def from_string(cls, data_string):
        """Create CustomStepData from stored string format.

        Args:
            data_string (str): String in format "name | path" or "*name | path"

        Returns:
            CustomStepData: Parsed data object
        """
        if not data_string or not data_string.strip():
            return cls()

        parts = data_string.split("|")
        name_part = parts[0].strip() if parts else ""
        path_part = parts[-1].strip() if len(parts) > 1 else ""

        # Check for deactivated marker
        active = True
        if name_part.startswith("*"):
            active = False
            name_part = name_part[1:]

        return cls(name=name_part, path=path_part, active=active)

    def to_string(self):
        """Convert to stored string format.

        Returns:
            str: String in format "name | path" or "*name | path"
        """
        prefix = "" if self._active else "*"
        return "{}{} | {}".format(prefix, self._name, self._path)

    def get_full_path(self):
        """Get the full filesystem path to the custom step file.

        Returns:
            str: Full path to the file
        """
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            return os.path.join(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""),
                self._path
            )
        return self._path

    def file_exists(self):
        """Check if the custom step file exists.

        Returns:
            bool: True if file exists
        """
        return os.path.exists(self.get_full_path())

    def to_dict(self):
        """Serialize to dictionary for JSON storage.

        Returns:
            dict: Dictionary representation of the step data
        """
        return {
            "type": "step",
            "name": self._name,
            "path": self._path,
            "active": self._active
        }

    @classmethod
    def from_dict(cls, data):
        """Create CustomStepData from dictionary.

        Args:
            data (dict): Dictionary with name, path, active keys

        Returns:
            CustomStepData: New instance from dictionary data
        """
        return cls(
            name=data.get("name", ""),
            path=data.get("path", ""),
            active=data.get("active", True)
        )

    def __repr__(self):
        return "CustomStepData(name={!r}, path={!r}, active={!r})".format(
            self._name, self._path, self._active
        )


# ============================================================================
# Group Data Model
# ============================================================================


class GroupData(object):
    """Data model for a custom step group.

    Groups can contain multiple CustomStepData items and can be
    collapsed/expanded and activated/deactivated as a unit.

    Attributes:
        name (str): Display name of the group
        collapsed (bool): Whether the group is visually collapsed
        active (bool): Whether the group (and all children) are active
        items (list): List of CustomStepData objects in this group
    """

    def __init__(self, name="", collapsed=False, active=True, items=None):
        """Initialize GroupData.

        Args:
            name (str): Display name of the group
            collapsed (bool): Whether group is collapsed
            active (bool): Whether group is active
            items (list): List of CustomStepData objects
        """
        self._name = name
        self._collapsed = collapsed
        self._active = active
        self._items = items if items is not None else []

    @property
    def name(self):
        """str: The display name of the group."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def collapsed(self):
        """bool: Whether the group is collapsed."""
        return self._collapsed

    @collapsed.setter
    def collapsed(self, value):
        self._collapsed = bool(value)

    @property
    def active(self):
        """bool: Whether the group is active."""
        return self._active

    @active.setter
    def active(self, value):
        self._active = bool(value)

    @property
    def items(self):
        """list: List of CustomStepData objects in this group."""
        return self._items

    def add_item(self, step_data):
        """Add a CustomStepData to this group.

        Args:
            step_data (CustomStepData): Step to add
        """
        self._items.append(step_data)

    def remove_item(self, step_data):
        """Remove a CustomStepData from this group.

        Args:
            step_data (CustomStepData): Step to remove
        """
        if step_data in self._items:
            self._items.remove(step_data)

    def insert_item(self, index, step_data):
        """Insert a CustomStepData at a specific index.

        Args:
            index (int): Index to insert at
            step_data (CustomStepData): Step to insert
        """
        self._items.insert(index, step_data)

    def get_active_items(self):
        """Get list of items that are effectively active.

        Items are only active if both the group and the item are active.

        Returns:
            list: List of active CustomStepData objects
        """
        if not self._active:
            return []
        return [item for item in self._items if item.active]

    def to_dict(self):
        """Serialize to dictionary for JSON storage.

        Returns:
            dict: Dictionary representation of the group
        """
        return {
            "type": "group",
            "name": self._name,
            "collapsed": self._collapsed,
            "active": self._active,
            "items": [item.to_dict() for item in self._items]
        }

    @classmethod
    def from_dict(cls, data):
        """Create GroupData from dictionary.

        Args:
            data (dict): Dictionary with group data

        Returns:
            GroupData: New instance from dictionary data
        """
        items = [
            CustomStepData.from_dict(item_data)
            for item_data in data.get("items", [])
        ]
        return cls(
            name=data.get("name", ""),
            collapsed=data.get("collapsed", False),
            active=data.get("active", True),
            items=items
        )

    def __repr__(self):
        return "GroupData(name={!r}, collapsed={!r}, active={!r}, items={!r})".format(
            self._name, self._collapsed, self._active, self._items
        )


# ============================================================================
# Custom Step Item Widget
# ============================================================================


class CustomStepItemWidget(QtWidgets.QFrame):
    """Widget for displaying a single custom step in the list.

    This widget provides:
    - Toggle button (left) to activate/deactivate the step
    - Name label (center) showing the step name
    - Edit button (right) to open the file in editor
    - Run button (right) to execute the step

    Signals:
        toggled: Emitted when the active state changes
        editRequested: Emitted when edit button is clicked
        runRequested: Emitted when run button is clicked
    """

    # Signals
    toggled = QtCore.Signal(bool)
    editRequested = QtCore.Signal()
    runRequested = QtCore.Signal()
    clicked = QtCore.Signal(object, object)  # Emitted when clicked (self, Qt.KeyboardModifiers)
    contextMenuRequested = QtCore.Signal(object, object)  # (self, QPoint global pos)
    dragStarted = QtCore.Signal(object)  # Emitted when drag starts (passes self)

    # Style constants
    SHARED_COLOR = "#2E7D32"  # Green for shared steps
    INACTIVE_COLOR = "#8B4444"  # Pale red for deactivated steps
    NORMAL_COLOR = "#3C3C3C"  # Default dark background
    SELECTED_COLOR = "#4A6B8A"  # Pale blue for selected items
    BORDER_COLOR = "#555555"  # Frame border color
    SELECTED_BORDER_COLOR = "#6A9BCA"  # Lighter blue border when selected
    BORDER_RADIUS = 4
    ICON_SIZE = 16
    BUTTON_SIZE = 20

    def __init__(self, step_data=None, parent=None):
        """Initialize the custom step item widget.

        Args:
            step_data (CustomStepData): The data for this step
            parent (QWidget): Parent widget
        """
        super(CustomStepItemWidget, self).__init__(parent)
        self._step_data = step_data or CustomStepData()
        self._selected = False
        self._group_inactive = False  # True if parent group is inactive
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
        # Enable custom context menu handling and mouse tracking
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setMouseTracking(True)
        self._setup_ui()
        self._update_appearance()

    def _setup_ui(self):
        """Set up the widget UI."""
        # Main layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(4)

        # Toggle button (left side)
        self._toggle_btn = QtWidgets.QPushButton()
        self._toggle_btn.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(self._step_data.active)
        self._toggle_btn.setToolTip("Toggle step active/inactive")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._toggle_btn)

        # Name label (center, expandable)
        self._name_label = QtWidgets.QLabel(self._step_data.name)
        self._name_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred
        )
        layout.addWidget(self._name_label)

        # Edit button
        self._edit_btn = QtWidgets.QPushButton()
        self._edit_btn.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self._edit_btn.setToolTip("Edit step file")
        self._edit_btn.setFlat(True)
        self._edit_btn.setIcon(pyqt.get_icon("mgear_edit", self.ICON_SIZE))
        self._edit_btn.clicked.connect(self.editRequested.emit)
        layout.addWidget(self._edit_btn)

        # Run button
        self._run_btn = QtWidgets.QPushButton()
        self._run_btn.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self._run_btn.setToolTip("Run step")
        self._run_btn.setFlat(True)
        self._run_btn.setIcon(pyqt.get_icon("mgear_play", self.ICON_SIZE))
        self._run_btn.clicked.connect(self.runRequested.emit)
        layout.addWidget(self._run_btn)

        self._update_toggle_icon()

    def _update_toggle_icon(self):
        """Update the toggle button icon based on state."""
        if self._step_data.active:
            icon = pyqt.get_icon("mgear_check-circle", self.ICON_SIZE)
        else:
            icon = pyqt.get_icon("mgear_x-circle", self.ICON_SIZE)
        self._toggle_btn.setIcon(icon)

    def _update_appearance(self):
        """Update the widget appearance based on step state."""
        # Update toggle icon
        self._update_toggle_icon()
        self._toggle_btn.setChecked(self._step_data.active)

        # Update name label
        self._name_label.setText(self._step_data.name)

        # Determine background and border colors based on state
        # Priority: selected > group_inactive > step_inactive > shared > normal
        if self._selected:
            bg_color = self.SELECTED_COLOR
            border_color = self.SELECTED_BORDER_COLOR
        elif self._group_inactive or not self._step_data.active:
            bg_color = self.INACTIVE_COLOR
            border_color = self.BORDER_COLOR
        elif self._step_data.is_shared:
            bg_color = self.SHARED_COLOR
            border_color = self.BORDER_COLOR
        else:
            bg_color = self.NORMAL_COLOR
            border_color = self.BORDER_COLOR

        # Apply stylesheet with rounded corners and frame
        # Also style buttons to have transparent background
        self.setStyleSheet(
            """
            CustomStepItemWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {radius}px;
                padding: 2px;
            }}
            CustomStepItemWidget QPushButton {{
                background-color: transparent;
                border: none;
            }}
            CustomStepItemWidget QPushButton:hover {{
                background-color: rgba(255, 255, 255, 30);
                border-radius: 3px;
            }}
            CustomStepItemWidget QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 50);
            }}
            CustomStepItemWidget QLabel {{
                background-color: transparent;
                border: none;
            }}
            """.format(
                bg=bg_color,
                border=border_color,
                radius=self.BORDER_RADIUS
            )
        )

    def _on_toggle_clicked(self):
        """Handle toggle button click."""
        self._step_data.active = self._toggle_btn.isChecked()
        self._update_appearance()
        self.toggled.emit(self._step_data.active)

    # Public API

    def get_step_data(self):
        """Get the step data.

        Returns:
            CustomStepData: The current step data
        """
        return self._step_data

    def set_step_data(self, step_data):
        """Set the step data and update appearance.

        Args:
            step_data (CustomStepData): New step data
        """
        self._step_data = step_data
        self._update_appearance()

    def set_active(self, active):
        """Set the active state.

        Args:
            active (bool): New active state
        """
        self._step_data.active = active
        self._update_appearance()

    def is_active(self):
        """Check if step is active.

        Returns:
            bool: True if active
        """
        return self._step_data.active

    def get_name(self):
        """Get the step name.

        Returns:
            str: Step name
        """
        return self._step_data.name

    def get_path(self):
        """Get the step path.

        Returns:
            str: Step path
        """
        return self._step_data.path

    def get_full_path(self):
        """Get the full filesystem path.

        Returns:
            str: Full path to the file
        """
        return self._step_data.get_full_path()

    def to_string(self):
        """Convert to stored string format.

        Returns:
            str: String in format "name | path" or "*name | path"
        """
        return self._step_data.to_string()

    def set_highlighted(self, highlighted):
        """Set whether this item should be highlighted (for search).

        Args:
            highlighted (bool): Whether to highlight
        """
        if highlighted:
            self._name_label.setStyleSheet("background-color: #808080;")
        else:
            self._name_label.setStyleSheet("")

    def set_selected(self, selected):
        """Set whether this item is selected.

        Args:
            selected (bool): Whether the item is selected
        """
        if self._selected != selected:
            self._selected = selected
            self._update_appearance()

    def is_selected(self):
        """Check if this item is selected.

        Returns:
            bool: True if selected
        """
        return self._selected

    def set_group_inactive(self, group_inactive):
        """Set whether this item's parent group is inactive.

        When a group is inactive, all contained steps appear dimmed.

        Args:
            group_inactive (bool): Whether the parent group is inactive
        """
        self._group_inactive = group_inactive
        self._update_appearance()

    def mousePressEvent(self, event):
        """Handle mouse press for selection and drag initiation."""
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self.clicked.emit(self, event.modifiers())
        super(CustomStepItemWidget, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag detection."""
        if event.buttons() & QtCore.Qt.LeftButton:
            if hasattr(self, '_drag_start_pos'):
                distance = (event.pos() - self._drag_start_pos).manhattanLength()
                if distance >= QtWidgets.QApplication.startDragDistance():
                    self.dragStarted.emit(self)
        super(CustomStepItemWidget, self).mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        """Handle right-click context menu.

        Emits contextMenuRequested signal. The event is only accepted if
        the widget is inside a group (has _in_group flag). For top-level items,
        we ignore the event to let it propagate to the list widget.
        """
        # Check if this widget is inside a group
        if getattr(self, '_in_group', False):
            # Inside a group - emit signal and accept event
            self.contextMenuRequested.emit(self, event.globalPos())
            event.accept()
        else:
            # Top-level item - ignore to let list widget handle it
            event.ignore()


# ============================================================================
# Group Widget
# ============================================================================


class GroupHeaderWidget(QtWidgets.QFrame):
    """Header widget for a custom step group.

    Provides:
    - Collapse/expand arrow (left)
    - Toggle button for group activation
    - Editable group name label (double-click to edit)
    - Item count indicator

    Signals:
        toggled: Emitted when active state changes
        collapseToggled: Emitted when collapse state changes
        nameChanged: Emitted when name is edited
    """

    toggled = QtCore.Signal(bool)
    collapseToggled = QtCore.Signal(bool)
    nameChanged = QtCore.Signal(str)

    # Style constants - slightly different shade for groups
    GROUP_COLOR = "#4A4A5A"  # Darker purple-gray for groups
    INACTIVE_COLOR = "#5A4444"  # Darker red for inactive groups
    SELECTED_COLOR = "#4A6B8A"  # Pale blue for selected
    BORDER_COLOR = "#666666"
    SELECTED_BORDER_COLOR = "#6A9BCA"
    BORDER_RADIUS = 4
    ICON_SIZE = 16
    BUTTON_SIZE = 20

    def __init__(self, group_data=None, parent=None):
        """Initialize the group header widget.

        Args:
            group_data (GroupData): The data for this group
            parent (QWidget): Parent widget
        """
        super(GroupHeaderWidget, self).__init__(parent)
        self._group_data = group_data or GroupData()
        self._selected = False
        self._editing = False
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
        self._setup_ui()
        self._update_appearance()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(4)

        # Collapse arrow button
        self._collapse_btn = QtWidgets.QPushButton()
        self._collapse_btn.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self._collapse_btn.setFlat(True)
        self._collapse_btn.setToolTip("Expand/Collapse group")
        self._collapse_btn.clicked.connect(self._on_collapse_clicked)
        layout.addWidget(self._collapse_btn)

        # Toggle button for group activation
        self._toggle_btn = QtWidgets.QPushButton()
        self._toggle_btn.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(self._group_data.active)
        self._toggle_btn.setToolTip("Toggle group active/inactive")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._toggle_btn)

        # Name label (editable on double-click)
        self._name_label = QtWidgets.QLabel(self._group_data.name)
        self._name_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred
        )
        font = self._name_label.font()
        font.setBold(True)
        self._name_label.setFont(font)
        layout.addWidget(self._name_label)

        # Item count label
        self._count_label = QtWidgets.QLabel()
        self._count_label.setStyleSheet("color: #888888;")
        layout.addWidget(self._count_label)

        self._update_icons()
        self._update_count()

    def _update_icons(self):
        """Update button icons based on state."""
        # Collapse icon
        if self._group_data.collapsed:
            collapse_icon = pyqt.get_icon("mgear_chevron-right", self.ICON_SIZE)
        else:
            collapse_icon = pyqt.get_icon("mgear_chevron-down", self.ICON_SIZE)
        self._collapse_btn.setIcon(collapse_icon)

        # Toggle icon
        if self._group_data.active:
            toggle_icon = pyqt.get_icon("mgear_check-circle", self.ICON_SIZE)
        else:
            toggle_icon = pyqt.get_icon("mgear_x-circle", self.ICON_SIZE)
        self._toggle_btn.setIcon(toggle_icon)

    def _update_count(self):
        """Update the item count display."""
        count = len(self._group_data.items)
        self._count_label.setText("({})".format(count))

    def _update_appearance(self):
        """Update the widget appearance based on state."""
        self._update_icons()
        self._toggle_btn.setChecked(self._group_data.active)
        self._name_label.setText(self._group_data.name)
        self._update_count()

        # Determine background and border colors
        if self._selected:
            bg_color = self.SELECTED_COLOR
            border_color = self.SELECTED_BORDER_COLOR
        elif not self._group_data.active:
            bg_color = self.INACTIVE_COLOR
            border_color = self.BORDER_COLOR
        else:
            bg_color = self.GROUP_COLOR
            border_color = self.BORDER_COLOR

        self.setStyleSheet(
            """
            GroupHeaderWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {radius}px;
                padding: 2px;
            }}
            GroupHeaderWidget QPushButton {{
                background-color: transparent;
                border: none;
            }}
            GroupHeaderWidget QPushButton:hover {{
                background-color: rgba(255, 255, 255, 30);
                border-radius: 3px;
            }}
            GroupHeaderWidget QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 50);
            }}
            GroupHeaderWidget QLabel {{
                background-color: transparent;
                border: none;
            }}
            """.format(
                bg=bg_color,
                border=border_color,
                radius=self.BORDER_RADIUS
            )
        )

    def _on_collapse_clicked(self):
        """Handle collapse button click."""
        self._group_data.collapsed = not self._group_data.collapsed
        self._update_icons()
        self.collapseToggled.emit(self._group_data.collapsed)

    def _on_toggle_clicked(self):
        """Handle toggle button click."""
        self._group_data.active = self._toggle_btn.isChecked()
        self._update_appearance()
        self.toggled.emit(self._group_data.active)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click for inline name editing."""
        if self._name_label.geometry().contains(event.pos()) and not self._editing:
            self._start_editing()
        else:
            super(GroupHeaderWidget, self).mouseDoubleClickEvent(event)

    def _start_editing(self):
        """Replace label with line edit for name editing."""
        self._editing = True

        # Create line edit
        self._edit = QtWidgets.QLineEdit(self._group_data.name)
        self._edit.selectAll()
        self._edit.editingFinished.connect(self._finish_editing)
        self._edit.installEventFilter(self)

        # Replace label with edit in layout
        layout = self.layout()
        index = layout.indexOf(self._name_label)
        self._name_label.hide()
        layout.insertWidget(index, self._edit)
        self._edit.setFocus()

    def _finish_editing(self):
        """Finish editing and restore label."""
        if not self._editing:
            return

        new_name = self._edit.text().strip()
        if new_name and new_name != self._group_data.name:
            self._group_data.name = new_name
            self._name_label.setText(new_name)
            self.nameChanged.emit(new_name)

        self._edit.deleteLater()
        self._name_label.show()
        self._editing = False

    def eventFilter(self, obj, event):
        """Handle escape key to cancel editing."""
        if obj == getattr(self, '_edit', None):
            if event.type() == QtCore.QEvent.KeyPress:
                if event.key() == QtCore.Qt.Key_Escape:
                    # Cancel editing without saving
                    self._edit.deleteLater()
                    self._name_label.show()
                    self._editing = False
                    return True
        return super(GroupHeaderWidget, self).eventFilter(obj, event)

    # Public API

    def get_group_data(self):
        """Get the group data.

        Returns:
            GroupData: The current group data
        """
        return self._group_data

    def set_group_data(self, group_data):
        """Set the group data and update appearance.

        Args:
            group_data (GroupData): New group data
        """
        self._group_data = group_data
        self._update_appearance()

    def set_selected(self, selected):
        """Set whether this header is selected.

        Args:
            selected (bool): Whether the header is selected
        """
        if self._selected != selected:
            self._selected = selected
            self._update_appearance()

    def is_selected(self):
        """Check if this header is selected.

        Returns:
            bool: True if selected
        """
        return self._selected

    def is_collapsed(self):
        """Check if the group is collapsed.

        Returns:
            bool: True if collapsed
        """
        return self._group_data.collapsed

    def set_collapsed(self, collapsed):
        """Set the collapsed state.

        Args:
            collapsed (bool): New collapsed state
        """
        self._group_data.collapsed = collapsed
        self._update_icons()


class GroupWidget(QtWidgets.QFrame):
    """Collapsible group container for custom steps.

    Contains a header and a body that holds CustomStepItemWidgets.

    Signals:
        toggled: Group activation changed
        collapsed: Group collapse state changed
        nameChanged: Group name changed
        dataChanged: Data in group was modified
        stepClicked: Step widget inside group was clicked (widget, group_widget)
        stepContextMenu: Step context menu requested (widget, global_pos, group_widget)
        stepDragStarted: Step drag started (widget, group_widget)
    """

    toggled = QtCore.Signal(bool)
    collapsed = QtCore.Signal(bool)
    nameChanged = QtCore.Signal(str)
    dataChanged = QtCore.Signal()
    stepClicked = QtCore.Signal(object, object, object)  # (step_widget, group_widget, modifiers)
    stepContextMenu = QtCore.Signal(object, object, object)  # (step_widget, pos, group_widget)
    stepDragStarted = QtCore.Signal(object, object)  # (step_widget, group_widget)

    # Indent for child items
    CHILD_INDENT = 20

    def __init__(self, group_data=None, parent=None):
        """Initialize the group widget.

        Args:
            group_data (GroupData): The data for this group
            parent (QWidget): Parent widget
        """
        super(GroupWidget, self).__init__(parent)
        self._group_data = group_data or GroupData()
        self._step_widgets = []
        self._selected = False
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header
        self._header = GroupHeaderWidget(self._group_data)
        self._header.toggled.connect(self._on_header_toggled)
        self._header.collapseToggled.connect(self._on_collapse_toggled)
        self._header.nameChanged.connect(self._on_name_changed)
        layout.addWidget(self._header)

        # Body container for step items
        self._body = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self._body)
        body_layout.setContentsMargins(self.CHILD_INDENT, 2, 0, 2)
        body_layout.setSpacing(2)

        # Steps container
        self._steps_container = QtWidgets.QWidget()
        self._steps_layout = QtWidgets.QVBoxLayout(self._steps_container)
        self._steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_layout.setSpacing(2)
        body_layout.addWidget(self._steps_container)

        layout.addWidget(self._body)

        # Set initial collapse state
        self._body.setVisible(not self._group_data.collapsed)

    def _populate(self):
        """Populate the group with step widgets from data."""
        for step_data in self._group_data.items:
            self._add_step_widget(step_data)
        self._update_step_appearances()

    def _add_step_widget(self, step_data):
        """Add a step widget for the given step data.

        Args:
            step_data (CustomStepData): Step data to create widget for

        Returns:
            CustomStepItemWidget: The created widget
        """
        widget = CustomStepItemWidget(step_data)
        widget._in_group = True  # Mark as being inside a group for context menu handling
        self._steps_layout.addWidget(widget)
        self._step_widgets.append(widget)

        # Connect signals
        widget.toggled.connect(self._on_step_toggled)
        widget.editRequested.connect(
            lambda w=widget: self._on_step_edit_requested(w)
        )
        widget.runRequested.connect(
            lambda w=widget: self._on_step_run_requested(w)
        )
        # Connect mouse event signals for selection/drag/context menu
        widget.clicked.connect(
            lambda w, mods, widget=widget: self.stepClicked.emit(widget, self, mods)
        )
        widget.contextMenuRequested.connect(
            lambda _, pos, wid=widget: self.stepContextMenu.emit(wid, pos, self)
        )
        widget.dragStarted.connect(
            lambda w=widget: self.stepDragStarted.emit(w, self)
        )

        return widget

    def _update_step_appearances(self):
        """Update all step widget appearances based on group state."""
        group_inactive = not self._group_data.active
        for widget in self._step_widgets:
            if hasattr(widget, 'set_group_inactive'):
                widget.set_group_inactive(group_inactive)

    def _on_header_toggled(self, active):
        """Handle header toggle."""
        self._update_step_appearances()
        self.toggled.emit(active)
        self.dataChanged.emit()

    def _on_collapse_toggled(self, is_collapsed):
        """Handle collapse toggle."""
        self._body.setVisible(not is_collapsed)
        self.collapsed.emit(is_collapsed)
        self.dataChanged.emit()

    def _on_name_changed(self, new_name):
        """Handle name change."""
        self.nameChanged.emit(new_name)
        self.dataChanged.emit()

    def _on_step_toggled(self, active):
        """Handle step toggle."""
        self.dataChanged.emit()

    def _on_step_edit_requested(self, widget):
        """Handle step edit request."""
        # Find the step data and emit with path
        step_data = widget.get_step_data()
        if step_data:
            fullpath = step_data.get_full_path()
            if fullpath:
                CustomStepMixin._editFile(fullpath)

    def _on_step_run_requested(self, widget):
        """Handle step run request."""
        step_data = widget.get_step_data()
        if step_data:
            CustomStepMixin.runStep(step_data.path, customStepDic={})

    # Public API

    def get_group_data(self):
        """Get the group data.

        Returns:
            GroupData: The current group data
        """
        return self._group_data

    def add_step(self, step_data):
        """Add a step to this group.

        Args:
            step_data (CustomStepData): Step to add
        """
        self._group_data.add_item(step_data)
        widget = self._add_step_widget(step_data)
        self._update_step_appearances()
        self._header._update_count()
        self.dataChanged.emit()
        return widget

    def remove_step(self, index):
        """Remove step at index.

        Args:
            index (int): Index of step to remove

        Returns:
            CustomStepData: The removed step data, or None
        """
        if 0 <= index < len(self._step_widgets):
            widget = self._step_widgets.pop(index)
            step_data = widget.get_step_data()
            self._steps_layout.removeWidget(widget)
            widget.deleteLater()

            if index < len(self._group_data.items):
                self._group_data.items.pop(index)

            self._header._update_count()
            self.dataChanged.emit()
            return step_data
        return None

    def remove_step_widget(self, widget):
        """Remove a specific step widget.

        Args:
            widget (CustomStepItemWidget): Widget to remove

        Returns:
            CustomStepData: The removed step data, or None
        """
        if widget in self._step_widgets:
            index = self._step_widgets.index(widget)
            return self.remove_step(index)
        return None

    def get_step_widgets(self):
        """Get all step widgets in this group.

        Returns:
            list: List of CustomStepItemWidget instances
        """
        return self._step_widgets[:]

    def clear_step_selections(self):
        """Clear selection state of all steps in this group."""
        for widget in self._step_widgets:
            widget.set_selected(False)

    def get_selected_steps(self):
        """Get all selected step widgets in this group.

        Returns:
            list: List of selected CustomStepItemWidget instances
        """
        return [w for w in self._step_widgets if w.is_selected()]

    def get_step_index(self, widget):
        """Get the index of a step widget within this group.

        Args:
            widget (CustomStepItemWidget): The widget to find

        Returns:
            int: Index of widget, or -1 if not found
        """
        if widget in self._step_widgets:
            return self._step_widgets.index(widget)
        return -1

    def insert_step(self, index, step_data):
        """Insert a step at a specific index.

        Args:
            index (int): Index to insert at
            step_data (CustomStepData): Step data to insert

        Returns:
            CustomStepItemWidget: The created widget
        """
        # Clamp index
        index = max(0, min(index, len(self._step_widgets)))

        widget = CustomStepItemWidget(step_data)
        widget._in_group = True  # Mark as being inside a group for context menu handling
        self._steps_layout.insertWidget(index, widget)
        self._step_widgets.insert(index, widget)
        self._group_data.items.insert(index, step_data)

        # Connect signals
        widget.toggled.connect(self._on_step_toggled)
        widget.editRequested.connect(
            lambda w=widget: self._on_step_edit_requested(w)
        )
        widget.runRequested.connect(
            lambda w=widget: self._on_step_run_requested(w)
        )
        widget.clicked.connect(
            lambda w, mods, widget=widget: self.stepClicked.emit(widget, self, mods)
        )
        widget.contextMenuRequested.connect(
            lambda _, pos, wid=widget: self.stepContextMenu.emit(wid, pos, self)
        )
        widget.dragStarted.connect(
            lambda w=widget: self.stepDragStarted.emit(w, self)
        )

        self._update_step_appearances()
        self._header._update_count()
        self.dataChanged.emit()
        return widget

    def move_step(self, from_index, to_index):
        """Move a step from one index to another within the group.

        Args:
            from_index (int): Current index of the step
            to_index (int): Target index for the step
        """
        if from_index == to_index:
            return
        if not (0 <= from_index < len(self._step_widgets)):
            return
        if not (0 <= to_index <= len(self._step_widgets)):
            return

        # Remove from current position
        widget = self._step_widgets.pop(from_index)
        step_data = self._group_data.items.pop(from_index)

        # Adjust target index if needed
        if to_index > from_index:
            to_index -= 1

        # Insert at new position
        self._step_widgets.insert(to_index, widget)
        self._group_data.items.insert(to_index, step_data)

        # Update layout
        self._steps_layout.removeWidget(widget)
        self._steps_layout.insertWidget(to_index, widget)

        self.dataChanged.emit()

    def get_step_count(self):
        """Get the number of steps in this group.

        Returns:
            int: Number of steps
        """
        return len(self._step_widgets)

    def set_selected(self, selected):
        """Set whether this group is selected.

        Args:
            selected (bool): Whether the group is selected
        """
        if self._selected != selected:
            self._selected = selected
            self._header.set_selected(selected)

    def is_selected(self):
        """Check if this group is selected.

        Returns:
            bool: True if selected
        """
        return self._selected

    def is_collapsed(self):
        """Check if the group is collapsed.

        Returns:
            bool: True if collapsed
        """
        return self._group_data.collapsed

    def set_collapsed(self, collapsed):
        """Set the collapsed state.

        Args:
            collapsed (bool): New collapsed state
        """
        self._group_data.collapsed = collapsed
        self._header.set_collapsed(collapsed)
        self._body.setVisible(not collapsed)

    def is_active(self):
        """Check if the group is active.

        Returns:
            bool: True if active
        """
        return self._group_data.active

    def set_active(self, active):
        """Set the active state.

        Args:
            active (bool): New active state
        """
        self._group_data.active = active
        self._header._group_data.active = active
        self._header._update_appearance()
        self._update_step_appearances()

    def highlight_matching_steps(self, search_text):
        """Highlight steps matching the search text.

        Args:
            search_text (str): Text to search for
        """
        search_lower = search_text.lower() if search_text else ""
        for widget in self._step_widgets:
            if search_lower and search_lower in widget.get_name().lower():
                widget.set_highlighted(True)
            else:
                widget.set_highlighted(False)

    def set_highlighted(self, highlighted):
        """Set whether the group header should be highlighted.

        Args:
            highlighted (bool): Whether to highlight
        """
        # Groups themselves don't get highlighted, but their name could
        pass

    def get_drop_index_at_pos(self, pos):
        """Get the insertion index for a drop at the given position.

        Args:
            pos (QPoint): Position in body coordinates

        Returns:
            int: Index where an item should be inserted
        """
        if not self._step_widgets:
            return 0

        # Get the Y position relative to the steps container
        container_pos = self._steps_container.mapFrom(self, pos)
        y = container_pos.y()

        # Find insertion point based on widget positions
        for i, widget in enumerate(self._step_widgets):
            widget_rect = widget.geometry()
            widget_center_y = widget_rect.y() + widget_rect.height() / 2
            if y < widget_center_y:
                return i

        # If past all widgets, insert at end
        return len(self._step_widgets)


class CustomStepListWidget(QtWidgets.QListWidget):
    """QListWidget that displays custom step widgets with drag-drop support.

    This widget manages CustomStepItemWidget and GroupWidget instances and provides:
    - External file drops (.py files)
    - Internal drag-drop reordering
    - Item widget management
    - Group support for organizing steps

    Signals:
        filesDropped: Emitted when .py files are dropped from external sources
        stepToggled: Emitted when a step's active state changes (row, active)
        stepEditRequested: Emitted when edit is requested for a step (row)
        stepRunRequested: Emitted when run is requested for a step (row)
        orderChanged: Emitted when items are reordered
        dataChanged: Emitted when any data changes (for JSON storage)
    """

    filesDropped = QtCore.Signal(list)
    stepToggled = QtCore.Signal(int, bool)
    stepEditRequested = QtCore.Signal(int)
    stepRunRequested = QtCore.Signal(int)
    orderChanged = QtCore.Signal()
    dataChanged = QtCore.Signal()
    groupStepClicked = QtCore.Signal(object)  # Emitted when step in group clicked (CustomStepData)

    # Item type markers stored in UserRole
    ITEM_TYPE_STEP = "step"
    ITEM_TYPE_GROUP = "group"

    def __init__(self, parent=None):
        super(CustomStepListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(False)

        # Track widgets for proper cleanup
        self._item_widgets = {}

        # Track selected steps inside groups: list of (widget, group_widget) tuples
        self._selected_group_steps = []

        # Track drag start for group steps
        self._drag_start_pos = None
        self._drag_step_widget = None
        self._drag_group_widget = None

        # Connect selection changed signal
        self.itemSelectionChanged.connect(self._on_selection_changed)

        # Install event filter on viewport to intercept mouse events
        self.viewport().installEventFilter(self)

    def _find_step_widget_at_pos(self, pos):
        """Find a step widget inside a group at the given viewport position.

        Args:
            pos (QPoint): Position in viewport coordinates

        Returns:
            tuple: (step_widget, group_widget) or (None, None) if not found
        """
        item = self.itemAt(pos)
        if not item:
            return None, None

        row = self.row(item)
        if not self.isGroupRow(row):
            return None, None

        group_widget = self.getGroupWidget(row)
        if not group_widget:
            return None, None

        # Don't check steps if group is collapsed
        if group_widget.is_collapsed():
            return None, None

        global_pos = self.viewport().mapToGlobal(pos)
        for step_widget in group_widget.get_step_widgets():
            # Skip if widget is not visible
            if not step_widget.isVisible():
                continue
            # Get the step widget's global rectangle
            widget_global_pos = step_widget.mapToGlobal(QtCore.QPoint(0, 0))
            widget_rect = QtCore.QRect(widget_global_pos, step_widget.size())
            if widget_rect.contains(global_pos):
                return step_widget, group_widget

        return None, None

    def eventFilter(self, obj, event):
        """Filter events on the viewport to handle clicks on group steps."""
        if obj == self.viewport():
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    pos = event.pos()
                    step_widget, group_widget = self._find_step_widget_at_pos(pos)
                    if step_widget:
                        # Click is on a step inside a group
                        self._on_group_step_clicked(
                            step_widget, group_widget, event.modifiers()
                        )
                        # Track for potential drag
                        self._drag_start_pos = pos
                        self._drag_step_widget = step_widget
                        self._drag_group_widget = group_widget
                        return True  # Event handled

            elif event.type() == QtCore.QEvent.MouseMove:
                if event.buttons() & QtCore.Qt.LeftButton:
                    if self._drag_start_pos and self._drag_step_widget:
                        distance = (event.pos() - self._drag_start_pos).manhattanLength()
                        if distance >= QtWidgets.QApplication.startDragDistance():
                            # Start drag operation
                            self._on_group_step_drag_started(
                                self._drag_step_widget, self._drag_group_widget
                            )
                            # Reset drag tracking
                            self._drag_start_pos = None
                            self._drag_step_widget = None
                            self._drag_group_widget = None
                            return True

            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                # Reset drag tracking on mouse release
                self._drag_start_pos = None
                self._drag_step_widget = None
                self._drag_group_widget = None

        return super(CustomStepListWidget, self).eventFilter(obj, event)

    def _on_selection_changed(self):
        """Handle selection change and update widget appearances."""
        # Get selected rows as a set (rows are hashable, items are not in PySide6)
        selected_rows = set(self.row(item) for item in self.selectedItems())
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if widget and hasattr(widget, 'set_selected'):
                widget.set_selected(i in selected_rows)

        # Clear group step selections when list selection changes
        if self._selected_group_steps:
            self._clear_group_step_selections()

    def _clear_all_selections(self):
        """Clear both list selections and group step selections."""
        self.clearSelection()
        self._clear_group_step_selections()

    def _clear_group_step_selections(self):
        """Clear all step selections inside groups."""
        for step_widget, _ in self._selected_group_steps:
            step_widget.set_selected(False)
        self._selected_group_steps = []

        # Also clear any selected steps in all groups (safety)
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if isinstance(widget, GroupWidget):
                widget.clear_step_selections()

    def _on_group_step_clicked(self, step_widget, group_widget, modifiers):
        """Handle click on a step inside a group.

        Args:
            step_widget (CustomStepItemWidget): The clicked step widget
            group_widget (GroupWidget): The group containing the step
            modifiers (Qt.KeyboardModifiers): Keyboard modifiers during click
        """
        # Clear list widget selection
        self.clearSelection()

        ctrl_pressed = modifiers & QtCore.Qt.ControlModifier
        shift_pressed = modifiers & QtCore.Qt.ShiftModifier

        if ctrl_pressed:
            # Toggle selection of this step
            if step_widget.is_selected():
                step_widget.set_selected(False)
                self._selected_group_steps = [
                    (w, g) for w, g in self._selected_group_steps
                    if w is not step_widget
                ]
            else:
                step_widget.set_selected(True)
                self._selected_group_steps.append((step_widget, group_widget))
        elif shift_pressed and self._selected_group_steps:
            # Range selection within the same group
            last_widget, last_group = self._selected_group_steps[-1]
            if last_group is group_widget:
                # Get indices
                start_idx = group_widget.get_step_index(last_widget)
                end_idx = group_widget.get_step_index(step_widget)
                if start_idx >= 0 and end_idx >= 0:
                    min_idx = min(start_idx, end_idx)
                    max_idx = max(start_idx, end_idx)
                    # Select range
                    step_widgets = group_widget.get_step_widgets()
                    for i in range(min_idx, max_idx + 1):
                        w = step_widgets[i]
                        if not w.is_selected():
                            w.set_selected(True)
                            self._selected_group_steps.append((w, group_widget))
            else:
                # Different group - just select this one
                self._clear_group_step_selections()
                step_widget.set_selected(True)
                self._selected_group_steps.append((step_widget, group_widget))
        else:
            # Normal click - clear previous and select this one
            self._clear_group_step_selections()
            step_widget.set_selected(True)
            self._selected_group_steps.append((step_widget, group_widget))

        # Emit signal for info panel update
        step_data = step_widget.get_step_data()
        if step_data:
            self.groupStepClicked.emit(step_data)

    def _on_group_step_context_menu(self, step_widget, global_pos, group_widget):
        """Handle context menu request for a step inside a group.

        Args:
            step_widget (CustomStepItemWidget): The step widget
            global_pos (QPoint): Global position for menu
            group_widget (GroupWidget): The group containing the step
        """
        # Select the step if not already selected
        if not step_widget.is_selected():
            self._on_group_step_clicked(step_widget, group_widget, QtCore.Qt.NoModifier)

        # Create context menu - store as instance variable like main menu
        # Use self (the list widget) as parent to ensure menu stays alive
        self._group_step_menu = QtWidgets.QMenu(self)

        # Edit action
        edit_action = self._group_step_menu.addAction("Edit")
        edit_action.setIcon(pyqt.get_icon("mgear_edit"))

        # Run action
        run_action = self._group_step_menu.addAction("Run")
        run_action.setIcon(pyqt.get_icon("mgear_play"))

        self._group_step_menu.addSeparator()

        # Move to top level action
        move_out_action = self._group_step_menu.addAction("Move to Top Level")
        move_out_action.setIcon(pyqt.get_icon("mgear_arrow-up"))

        # Remove from group action
        remove_action = self._group_step_menu.addAction("Remove")
        remove_action.setIcon(pyqt.get_icon("mgear_trash-2"))

        # Connect actions using lambdas to capture current step/group
        edit_action.triggered.connect(
            lambda: self._edit_group_step(step_widget)
        )
        run_action.triggered.connect(
            lambda: self._run_group_step(step_widget)
        )
        move_out_action.triggered.connect(
            lambda: self._move_step_to_top_level(step_widget, group_widget)
        )
        remove_action.triggered.connect(
            lambda: self._remove_step_from_group(step_widget, group_widget)
        )

        # Show menu using exec_() which blocks until menu closes
        self._group_step_menu.exec_(global_pos)

    def _edit_group_step(self, step_widget):
        """Edit a step from a group."""
        step_data = step_widget.get_step_data()
        if step_data:
            fullpath = step_data.get_full_path()
            if fullpath:
                CustomStepMixin._editFile(fullpath)

    def _run_group_step(self, step_widget):
        """Run a step from a group."""
        step_data = step_widget.get_step_data()
        if step_data:
            runStep(step_data.path, customStepDic={})

    def _move_step_to_top_level(self, step_widget, group_widget):
        """Move a step from a group to the top level.

        Args:
            step_widget (CustomStepItemWidget): The step to move
            group_widget (GroupWidget): The group containing the step
        """
        step_data = step_widget.get_step_data()
        if not step_data:
            return

        # Find the group's row
        group_row = self._find_group_row(group_widget)
        if group_row < 0:
            return

        # Remove from group
        group_widget.remove_step_widget(step_widget)

        # Update group item height
        self._update_group_item_height(group_row)

        # Add to top level after the group
        self._insert_step_at_row(group_row + 1, step_data)

        self._clear_group_step_selections()
        self.dataChanged.emit()

    def _remove_step_from_group(self, step_widget, group_widget):
        """Remove a step from a group entirely.

        Args:
            step_widget (CustomStepItemWidget): The step to remove
            group_widget (GroupWidget): The group containing the step
        """
        # Find the group's row
        group_row = self._find_group_row(group_widget)
        if group_row < 0:
            return

        # Remove from group
        group_widget.remove_step_widget(step_widget)

        # Update group item height
        self._update_group_item_height(group_row)

        self._clear_group_step_selections()
        self.dataChanged.emit()

    def _find_group_row(self, group_widget):
        """Find the row index of a group widget.

        Args:
            group_widget (GroupWidget): The group to find

        Returns:
            int: Row index, or -1 if not found
        """
        for i in range(self.count()):
            if self.getItemWidget(i) is group_widget:
                return i
        return -1

    def _update_group_item_height(self, row):
        """Update the height of a group item based on its contents.

        Args:
            row (int): Row index of the group
        """
        item = self.item(row)
        widget = self.getItemWidget(row)
        if item and isinstance(widget, GroupWidget):
            group_data = widget.get_group_data()
            base_height = 32  # Header height
            if not group_data.collapsed:
                base_height += len(group_data.items) * 32 + 8
            item.setSizeHint(QtCore.QSize(0, base_height))
            # Update stored data
            item.setData(QtCore.Qt.UserRole, json.dumps(group_data.to_dict()))

    def _insert_step_at_row(self, row, step_data):
        """Insert a step at a specific row.

        Args:
            row (int): Row to insert at
            step_data (CustomStepData): Step data to insert
        """
        # Create list item
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, 32))

        # Store data
        item.setData(QtCore.Qt.UserRole, step_data.to_string())
        self._set_item_type(item, self.ITEM_TYPE_STEP)

        # Insert at position
        self.insertItem(row, item)

        # Create widget
        widget = CustomStepItemWidget(step_data)
        self.setItemWidget(item, widget)

        # Track the widget
        self._item_widgets[id(item)] = widget

        # Connect signals
        widget.toggled.connect(
            lambda active, it=item: self._on_step_toggled(it, active)
        )
        widget.editRequested.connect(
            lambda it=item: self._on_edit_requested(it)
        )
        widget.runRequested.connect(
            lambda it=item: self._on_run_requested(it)
        )

    def _on_group_step_drag_started(self, step_widget, group_widget):
        """Handle drag start from a step inside a group.

        Args:
            step_widget (CustomStepItemWidget): The step being dragged
            group_widget (GroupWidget): The group containing the step
        """
        # Select the step if not already selected
        if not step_widget.is_selected():
            self._on_group_step_clicked(
                step_widget, group_widget, QtCore.Qt.NoModifier
            )

        # Start a drag operation
        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()

        # Store information about the dragged step
        step_data = step_widget.get_step_data()
        drag_info = {
            "type": "group_step",
            "step": step_data.to_dict() if step_data else {},
            "group_row": self._find_group_row(group_widget),
            "step_index": group_widget.get_step_index(step_widget)
        }
        mime_data.setData(
            "application/x-mgear-customstep",
            json.dumps(drag_info).encode('utf-8')
        )
        drag.setMimeData(mime_data)

        # Execute drag
        result = drag.exec_(QtCore.Qt.MoveAction)

        if result == QtCore.Qt.MoveAction:
            # Drag was accepted - the drop handler will have done the move
            pass

    def _get_item_type(self, item):
        """Get the type of item (step or group).

        Args:
            item: QListWidgetItem

        Returns:
            str: 'step' or 'group'
        """
        data = item.data(QtCore.Qt.UserRole + 1)
        return data if data else self.ITEM_TYPE_STEP

    def _set_item_type(self, item, item_type):
        """Set the type of item.

        Args:
            item: QListWidgetItem
            item_type (str): 'step' or 'group'
        """
        item.setData(QtCore.Qt.UserRole + 1, item_type)

    def addStepItem(self, step_data):
        """Add a new custom step item to the list.

        Args:
            step_data (CustomStepData or str): Step data or string to parse

        Returns:
            int: The row index of the added item
        """
        if isinstance(step_data, string_types):
            step_data = CustomStepData.from_string(step_data)

        # Skip empty entries
        if not step_data.name and not step_data.path:
            return -1

        # Create list item
        item = QtWidgets.QListWidgetItem(self)
        item.setSizeHint(QtCore.QSize(0, 32))  # Height to accommodate frame and padding

        # Store the data in the item
        item.setData(QtCore.Qt.UserRole, step_data.to_string())
        self._set_item_type(item, self.ITEM_TYPE_STEP)

        # Create and set the widget
        widget = CustomStepItemWidget(step_data)
        self.setItemWidget(item, widget)

        # Track the widget
        self._item_widgets[id(item)] = widget

        # Connect signals
        widget.toggled.connect(
            lambda active, it=item: self._on_step_toggled(it, active)
        )
        widget.editRequested.connect(
            lambda it=item: self._on_edit_requested(it)
        )
        widget.runRequested.connect(
            lambda it=item: self._on_run_requested(it)
        )

        return self.row(item)

    def addGroupItem(self, group_data):
        """Add a new group item to the list.

        Args:
            group_data (GroupData): Group data to add

        Returns:
            int: The row index of the added item
        """
        if not group_data.name:
            group_data.name = "New Group"

        # Create list item
        item = QtWidgets.QListWidgetItem(self)

        # Calculate height based on group content
        base_height = 32  # Header height
        if not group_data.collapsed:
            base_height += len(group_data.items) * 32 + 8
        item.setSizeHint(QtCore.QSize(0, base_height))

        # Store data and type
        item.setData(QtCore.Qt.UserRole, json.dumps(group_data.to_dict()))
        self._set_item_type(item, self.ITEM_TYPE_GROUP)

        # Create and set the widget
        widget = GroupWidget(group_data)
        self.setItemWidget(item, widget)

        # Track the widget
        self._item_widgets[id(item)] = widget

        # Connect signals
        widget.dataChanged.connect(
            lambda it=item: self._on_group_data_changed(it)
        )
        widget.collapsed.connect(
            lambda collapsed, it=item: self._on_group_collapsed(it, collapsed)
        )
        # Connect step interaction signals
        widget.stepClicked.connect(self._on_group_step_clicked)
        widget.stepContextMenu.connect(self._on_group_step_context_menu)
        widget.stepDragStarted.connect(self._on_group_step_drag_started)

        return self.row(item)

    def _on_group_data_changed(self, item):
        """Handle group data change event."""
        widget = self.itemWidget(item)
        if widget and isinstance(widget, GroupWidget):
            # Update stored data
            item.setData(
                QtCore.Qt.UserRole,
                json.dumps(widget.get_group_data().to_dict())
            )
            self.dataChanged.emit()

    def _on_group_collapsed(self, item, collapsed):
        """Handle group collapse/expand event."""
        widget = self.itemWidget(item)
        if widget and isinstance(widget, GroupWidget):
            # Update item height
            group_data = widget.get_group_data()
            base_height = 32  # Header height
            if not collapsed:
                base_height += len(group_data.items) * 32 + 8
            item.setSizeHint(QtCore.QSize(0, base_height))

    def _on_step_toggled(self, item, active):
        """Handle step toggle event."""
        widget = self.itemWidget(item)
        if widget and hasattr(widget, 'to_string'):
            # Update the stored data
            item.setData(QtCore.Qt.UserRole, widget.to_string())
            self.stepToggled.emit(self.row(item), active)
            self.dataChanged.emit()

    def _on_edit_requested(self, item):
        """Handle edit request event."""
        self.stepEditRequested.emit(self.row(item))

    def _on_run_requested(self, item):
        """Handle run request event."""
        self.stepRunRequested.emit(self.row(item))

    def getItemWidget(self, row):
        """Get the widget for a given row (step or group).

        Args:
            row (int): Row index

        Returns:
            CustomStepItemWidget or GroupWidget or None
        """
        item = self.item(row)
        if item:
            return self.itemWidget(item)
        return None

    def getStepWidget(self, row):
        """Get the CustomStepItemWidget for a given row.

        Args:
            row (int): Row index

        Returns:
            CustomStepItemWidget or None: The widget at the row
        """
        widget = self.getItemWidget(row)
        if isinstance(widget, CustomStepItemWidget):
            return widget
        return None

    def getGroupWidget(self, row):
        """Get the GroupWidget for a given row.

        Args:
            row (int): Row index

        Returns:
            GroupWidget or None: The widget at the row
        """
        widget = self.getItemWidget(row)
        if isinstance(widget, GroupWidget):
            return widget
        return None

    def isGroupRow(self, row):
        """Check if a row contains a group.

        Args:
            row (int): Row index

        Returns:
            bool: True if row contains a group
        """
        item = self.item(row)
        if item:
            return self._get_item_type(item) == self.ITEM_TYPE_GROUP
        return False

    def getStepData(self, row):
        """Get the CustomStepData for a given row.

        Args:
            row (int): Row index

        Returns:
            CustomStepData or None: The step data at the row
        """
        widget = self.getStepWidget(row)
        if widget:
            return widget.get_step_data()
        return None

    def getGroupData(self, row):
        """Get the GroupData for a given row.

        Args:
            row (int): Row index

        Returns:
            GroupData or None: The group data at the row
        """
        widget = self.getGroupWidget(row)
        if widget:
            return widget.get_group_data()
        return None

    def getAllStepData(self):
        """Get all step data as a flat list (including steps in groups).

        Returns:
            list: List of CustomStepData objects
        """
        result = []
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if isinstance(widget, GroupWidget):
                # Add all steps from the group
                for step_data in widget.get_group_data().items:
                    result.append(step_data)
            elif isinstance(widget, CustomStepItemWidget):
                result.append(widget.get_step_data())
        return result

    def getAllActiveStepData(self):
        """Get all active step data as a flat list for building.

        Respects both group and individual step active states.

        Returns:
            list: List of active CustomStepData objects
        """
        result = []
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if isinstance(widget, GroupWidget):
                group_data = widget.get_group_data()
                if group_data.active:
                    # Add active steps from active group
                    for step_data in group_data.items:
                        if step_data.active:
                            result.append(step_data)
            elif isinstance(widget, CustomStepItemWidget):
                step_data = widget.get_step_data()
                if step_data.active:
                    result.append(step_data)
        return result

    def getStepStrings(self):
        """Get all step data as strings (for legacy storage).

        Note: This flattens groups and loses group information.
        Use toJson() for full data preservation.

        Returns:
            list: List of step strings in storage format
        """
        result = []
        for step_data in self.getAllStepData():
            result.append(step_data.to_string())
        return result

    def toJson(self):
        """Serialize all items to JSON format for storage.

        Returns:
            str: JSON string with version and items
        """
        items_list = []
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if isinstance(widget, GroupWidget):
                items_list.append(widget.get_group_data().to_dict())
            elif isinstance(widget, CustomStepItemWidget):
                items_list.append(widget.get_step_data().to_dict())

        return json.dumps({
            "version": 2,
            "items": items_list
        })

    def loadFromJson(self, json_string):
        """Load items from JSON string with backwards compatibility.

        Args:
            json_string (str): JSON string or legacy comma-separated format
        """
        self.clear()
        items = self._parseData(json_string)
        for item in items:
            if isinstance(item, GroupData):
                self.addGroupItem(item)
            elif isinstance(item, CustomStepData):
                self.addStepItem(item)

    @staticmethod
    def _parseData(data_string):
        """Parse data string and return list of items.

        Handles both JSON format (v2) and legacy comma-separated format.

        Args:
            data_string (str): Data to parse

        Returns:
            list: List of CustomStepData and GroupData objects
        """
        if not data_string or not data_string.strip():
            return []

        # Try JSON format first
        try:
            data = json.loads(data_string)
            if isinstance(data, dict) and data.get("version") == 2:
                return CustomStepListWidget._parseV2Format(data)
        except (json.JSONDecodeError, ValueError):
            pass

        # Fall back to legacy comma-separated format
        return CustomStepListWidget._parseLegacyFormat(data_string)

    @staticmethod
    def _parseV2Format(data):
        """Parse version 2 JSON format.

        Args:
            data (dict): Parsed JSON data

        Returns:
            list: List of CustomStepData and GroupData objects
        """
        items = []
        for item_data in data.get("items", []):
            if item_data.get("type") == "group":
                items.append(GroupData.from_dict(item_data))
            else:
                items.append(CustomStepData.from_dict(item_data))
        return items

    @staticmethod
    def _parseLegacyFormat(data_string):
        """Parse legacy comma-separated format.

        Args:
            data_string (str): Comma-separated step strings

        Returns:
            list: List of CustomStepData objects
        """
        items = []
        for entry in data_string.split(","):
            entry = entry.strip()
            if entry:
                step_data = CustomStepData.from_string(entry)
                if step_data.name or step_data.path:
                    items.append(step_data)
        return items

    def createGroupFromSelection(self, name="New Group"):
        """Create a group from currently selected step items.

        Args:
            name (str): Name for the new group

        Returns:
            int: Row index of the new group, or -1 if no valid selection
        """
        selected_items = self.selectedItems()
        if not selected_items:
            return -1

        # Collect step data from selected items (only steps, not groups)
        steps_to_group = []
        rows_to_remove = []
        for item in selected_items:
            row = self.row(item)
            if not self.isGroupRow(row):
                widget = self.getStepWidget(row)
                if widget:
                    steps_to_group.append(widget.get_step_data())
                    rows_to_remove.append(row)

        if not steps_to_group:
            return -1

        # Get insertion position (where first selected item was)
        insert_row = min(rows_to_remove)

        # Remove items in reverse order to preserve indices
        for row in sorted(rows_to_remove, reverse=True):
            self.takeItem(row)

        # Create group data
        group_data = GroupData(name=name, items=steps_to_group)

        # Insert group at the position
        item = QtWidgets.QListWidgetItem()
        base_height = 32 + len(steps_to_group) * 32 + 8
        item.setSizeHint(QtCore.QSize(0, base_height))
        item.setData(QtCore.Qt.UserRole, json.dumps(group_data.to_dict()))
        self._set_item_type(item, self.ITEM_TYPE_GROUP)

        self.insertItem(insert_row, item)

        widget = GroupWidget(group_data)
        self.setItemWidget(item, widget)
        self._item_widgets[id(item)] = widget

        widget.dataChanged.connect(
            lambda it=item: self._on_group_data_changed(it)
        )
        widget.collapsed.connect(
            lambda collapsed, it=item: self._on_group_collapsed(it, collapsed)
        )
        # Connect step interaction signals
        widget.stepClicked.connect(self._on_group_step_clicked)
        widget.stepContextMenu.connect(self._on_group_step_context_menu)
        widget.stepDragStarted.connect(self._on_group_step_drag_started)

        self.dataChanged.emit()
        return insert_row

    def ungroupItems(self, row, keep_items=True):
        """Remove a group, optionally keeping its items at top level.

        Args:
            row (int): Row of the group to remove
            keep_items (bool): If True, move items to top level

        Returns:
            list: List of CustomStepData that were in the group
        """
        if not self.isGroupRow(row):
            return []

        group_widget = self.getGroupWidget(row)
        if not group_widget:
            return []

        group_data = group_widget.get_group_data()
        items = list(group_data.items)

        # Remove the group
        self.takeItem(row)

        if keep_items:
            # Insert items at the group's position
            for i, step_data in enumerate(items):
                self.insertStepItem(row + i, step_data)

        self.dataChanged.emit()
        return items

    def insertStepItem(self, row, step_data):
        """Insert a step item at a specific row.

        Args:
            row (int): Row to insert at
            step_data (CustomStepData): Step data to insert

        Returns:
            int: The row index of the inserted item
        """
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, 32))
        item.setData(QtCore.Qt.UserRole, step_data.to_string())
        self._set_item_type(item, self.ITEM_TYPE_STEP)

        self.insertItem(row, item)

        widget = CustomStepItemWidget(step_data)
        self.setItemWidget(item, widget)
        self._item_widgets[id(item)] = widget

        widget.toggled.connect(
            lambda active, it=item: self._on_step_toggled(it, active)
        )
        widget.editRequested.connect(
            lambda it=item: self._on_edit_requested(it)
        )
        widget.runRequested.connect(
            lambda it=item: self._on_run_requested(it)
        )

        return row

    def setStepActive(self, row, active):
        """Set the active state of a step or group.

        Args:
            row (int): Row index
            active (bool): New active state
        """
        widget = self.getItemWidget(row)
        if isinstance(widget, CustomStepItemWidget):
            widget.set_active(active)
            item = self.item(row)
            if item:
                item.setData(QtCore.Qt.UserRole, widget.to_string())
        elif isinstance(widget, GroupWidget):
            widget.set_active(active)
            item = self.item(row)
            if item:
                item.setData(
                    QtCore.Qt.UserRole,
                    json.dumps(widget.get_group_data().to_dict())
                )
        self.dataChanged.emit()

    def toggleStepActive(self, row):
        """Toggle the active state of a step or group.

        Args:
            row (int): Row index
        """
        widget = self.getItemWidget(row)
        if widget and hasattr(widget, 'is_active'):
            self.setStepActive(row, not widget.is_active())

    def highlightSearch(self, search_text):
        """Highlight items matching the search text.

        Args:
            search_text (str): Text to search for
        """
        search_lower = search_text.lower() if search_text else ""
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if isinstance(widget, GroupWidget):
                # Search in group name and child steps
                group_match = search_lower in widget.get_group_data().name.lower()
                widget.set_highlighted(group_match)
                widget.highlight_matching_steps(search_text)
            elif isinstance(widget, CustomStepItemWidget):
                if search_lower and search_lower in widget.get_name().lower():
                    widget.set_highlighted(True)
                else:
                    widget.set_highlighted(False)

    def clear(self):
        """Clear all items and widgets."""
        self._item_widgets.clear()
        super(CustomStepListWidget, self).clear()

    # Drag and drop handling

    def dragEnterEvent(self, event):
        # Check for our custom MIME type (step dragged from group)
        if event.mimeData().hasFormat("application/x-mgear-customstep"):
            event.acceptProposedAction()
            return
        if event.mimeData().hasUrls():
            # Check if any URL is a .py file
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".py"):
                    event.acceptProposedAction()
                    return
        # Fall back to default behavior for internal moves
        super(CustomStepListWidget, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        # Check for our custom MIME type (step dragged from group)
        if event.mimeData().hasFormat("application/x-mgear-customstep"):
            event.acceptProposedAction()
            return
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".py"):
                    event.acceptProposedAction()
                    return
        super(CustomStepListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        # Handle custom MIME type (step dragged from group)
        if event.mimeData().hasFormat("application/x-mgear-customstep"):
            self._handle_group_step_drop(event)
            return

        if event.mimeData().hasUrls():
            py_files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.endswith(".py"):
                    py_files.append(file_path)
            if py_files:
                event.acceptProposedAction()
                self.filesDropped.emit(py_files)
                return

        # For internal moves, we need to handle widget reassignment
        if event.source() == self:
            # Check if we're dropping onto a group
            drop_pos = event.pos()
            target_item = self.itemAt(drop_pos)

            if target_item and self._get_item_type(target_item) == self.ITEM_TYPE_GROUP:
                # Handle drop INTO a group
                if self._handle_drop_into_group(target_item, event):
                    return

            # Standard reorder - let the base class handle it
            super(CustomStepListWidget, self).dropEvent(event)

            # Reassign widgets after move (they get detached during move)
            self._reassign_widgets()
            self.orderChanged.emit()
            self.dataChanged.emit()
        else:
            super(CustomStepListWidget, self).dropEvent(event)

    def _handle_drop_into_group(self, target_item, event):
        """Handle dropping top-level steps into a group.

        Args:
            target_item: The group QListWidgetItem being dropped onto
            event: The drop event

        Returns:
            bool: True if drop was handled, False otherwise
        """
        target_row = self.row(target_item)
        group_widget = self.getGroupWidget(target_row)
        if not group_widget:
            return False

        # Collect selected step data (only steps, not groups)
        selected_items = self.selectedItems()
        steps_to_add = []
        rows_to_remove = []

        for item in selected_items:
            row = self.row(item)
            if row == target_row:
                # Can't drop a group onto itself
                continue
            if self._get_item_type(item) == self.ITEM_TYPE_STEP:
                widget = self.getStepWidget(row)
                if widget:
                    steps_to_add.append(widget.get_step_data())
                    rows_to_remove.append(row)

        if not steps_to_add:
            return False

        # Add steps to the group
        for step_data in steps_to_add:
            group_widget.add_step(step_data)

        # Remove original items (in reverse order to preserve indices)
        for row in sorted(rows_to_remove, reverse=True):
            self.takeItem(row)

        # Update item height to reflect new content
        # Recalculate target row since items may have been removed before it
        new_target_row = target_row - len([r for r in rows_to_remove if r < target_row])
        self._update_group_item_height(new_target_row)

        event.acceptProposedAction()
        self.orderChanged.emit()
        self.dataChanged.emit()
        return True

    def _handle_group_step_drop(self, event):
        """Handle drop of a step dragged from a group.

        Args:
            event: The drop event
        """
        try:
            data = event.mimeData().data("application/x-mgear-customstep")
            drag_info = json.loads(bytes(data).decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            event.ignore()
            return

        if drag_info.get("type") != "group_step":
            event.ignore()
            return

        source_group_row = drag_info.get("group_row", -1)
        step_index = drag_info.get("step_index", -1)
        step_dict = drag_info.get("step", {})

        if source_group_row < 0 or step_index < 0:
            event.ignore()
            return

        source_group_widget = self.getGroupWidget(source_group_row)
        if not source_group_widget:
            event.ignore()
            return

        # Determine drop target
        drop_pos = event.pos()
        target_item = self.itemAt(drop_pos)
        target_row = self.row(target_item) if target_item else self.count()

        # Check if dropping onto a group
        if target_item and self._get_item_type(target_item) == self.ITEM_TYPE_GROUP:
            target_group_widget = self.getGroupWidget(target_row)
            if target_group_widget and target_group_widget is not source_group_widget:
                # Move step from one group to another
                step_data = CustomStepData.from_dict(step_dict)
                source_group_widget.remove_step(step_index)
                target_group_widget.add_step(step_data)
                self._update_group_item_height(source_group_row)
                self._update_group_item_height(target_row)
                event.acceptProposedAction()
                self._clear_group_step_selections()
                self.dataChanged.emit()
                return
            elif target_group_widget is source_group_widget:
                # Reorder within same group - determine position based on Y coordinate
                # Map the drop position to the group widget coordinates
                group_local_pos = target_group_widget.mapFromGlobal(
                    self.mapToGlobal(drop_pos)
                )
                target_index = target_group_widget.get_drop_index_at_pos(group_local_pos)

                # Adjust target index if dragging down (since we remove first)
                if target_index > step_index:
                    target_index -= 1

                if target_index != step_index:
                    target_group_widget.move_step(step_index, target_index)
                    event.acceptProposedAction()
                    self._clear_group_step_selections()
                    self.dataChanged.emit()
                else:
                    event.ignore()
                return

        # Dropping onto top level (not a group)
        step_data = CustomStepData.from_dict(step_dict)

        # Remove from source group first
        source_group_widget.remove_step(step_index)
        self._update_group_item_height(source_group_row)

        # Adjust target row if source group was before target
        if source_group_row < target_row:
            # No adjustment needed - removing from group doesn't change row count
            pass

        # Insert at target position
        if target_row < 0:
            target_row = self.count()
        self.insertStepItem(target_row, step_data)

        event.acceptProposedAction()
        self._clear_group_step_selections()
        self.dataChanged.emit()

    def _reassign_widgets(self):
        """Reassign item widgets after a drag-drop reorder.

        When items are moved via drag-drop, the widgets get detached.
        This method recreates widgets from the stored data.
        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                # Check if widget is missing or detached
                current_widget = self.itemWidget(item)
                if current_widget is None:
                    item_type = self._get_item_type(item)
                    data_string = item.data(QtCore.Qt.UserRole)

                    if item_type == self.ITEM_TYPE_GROUP:
                        # Recreate group widget
                        try:
                            group_dict = json.loads(data_string)
                            group_data = GroupData.from_dict(group_dict)
                            widget = GroupWidget(group_data)
                            self.setItemWidget(item, widget)

                            widget.dataChanged.connect(
                                lambda it=item: self._on_group_data_changed(it)
                            )
                            widget.collapsed.connect(
                                lambda c, it=item: self._on_group_collapsed(it, c)
                            )
                            # Connect step interaction signals
                            widget.stepClicked.connect(self._on_group_step_clicked)
                            widget.stepContextMenu.connect(
                                self._on_group_step_context_menu
                            )
                            widget.stepDragStarted.connect(
                                self._on_group_step_drag_started
                            )
                        except (json.JSONDecodeError, ValueError):
                            pass
                    else:
                        # Recreate step widget
                        if data_string:
                            step_data = CustomStepData.from_string(data_string)
                            widget = CustomStepItemWidget(step_data)
                            self.setItemWidget(item, widget)

                            # Reconnect signals
                            widget.toggled.connect(
                                lambda active, it=item: self._on_step_toggled(
                                    it, active
                                )
                            )
                            widget.editRequested.connect(
                                lambda it=item: self._on_edit_requested(it)
                            )
                            widget.runRequested.connect(
                                lambda it=item: self._on_run_requested(it)
                            )

    # Legacy compatibility methods

    def addItem(self, text):
        """Add item using legacy text format (for backwards compatibility).

        Args:
            text (str): Step string in format "name | path"
        """
        self.addStepItem(text)

    def findItems(self, text, flags):
        """Find items containing text (legacy compatibility).

        Note: This returns QListWidgetItems, use getStepStrings() for
        getting the actual step strings.
        """
        return super(CustomStepListWidget, self).findItems(text, flags)


class Ui_Form(object):
    """UI definition for Custom Step Tab."""

    def setupUi(self, Form):
        Form.resize(312, 655)

        self.mainLayout = QtWidgets.QVBoxLayout(Form)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # Menu bar
        self.menuBar = QtWidgets.QMenuBar(Form)

        # Pre Custom Step menu
        self.preMenu = self.menuBar.addMenu("Pre")
        self.preExport_action = self.preMenu.addAction("Export")
        self.preExport_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.preImport_action = self.preMenu.addAction("Import")
        self.preImport_action.setIcon(pyqt.get_icon("mgear_log-in"))

        # Post Custom Step menu
        self.postMenu = self.menuBar.addMenu("Post")
        self.postExport_action = self.postMenu.addAction("Export")
        self.postExport_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.postImport_action = self.postMenu.addAction("Import")
        self.postImport_action.setIcon(pyqt.get_icon("mgear_log-in"))

        self.mainLayout.setMenuBar(self.menuBar)

        # =============================================
        # Pre Custom Step collapsible section
        # =============================================
        self.preCollapsible = CollapsibleWidget("Pre Custom Step", expanded=True)
        self.mainLayout.addWidget(self.preCollapsible, 1)  # stretch factor 1

        self.preCustomStep_checkBox = QtWidgets.QCheckBox("Enable")
        self.preCollapsible.addWidget(self.preCustomStep_checkBox)

        self.preSearch_lineEdit = QtWidgets.QLineEdit()
        self.preSearch_lineEdit.setPlaceholderText("Search...")
        self.preCollapsible.addWidget(self.preSearch_lineEdit)

        self.preCustomStep_listWidget = CustomStepListWidget()
        self.preCollapsible.addWidget(self.preCustomStep_listWidget)

        # =============================================
        # Post Custom Step collapsible section
        # =============================================
        self.postCollapsible = CollapsibleWidget(
            "Post Custom Step", expanded=True
        )
        self.mainLayout.addWidget(self.postCollapsible, 1)  # stretch factor 1

        self.postCustomStep_checkBox = QtWidgets.QCheckBox("Enable")
        self.postCollapsible.addWidget(self.postCustomStep_checkBox)

        self.postSearch_lineEdit = QtWidgets.QLineEdit()
        self.postSearch_lineEdit.setPlaceholderText("Search...")
        self.postCollapsible.addWidget(self.postSearch_lineEdit)

        self.postCustomStep_listWidget = CustomStepListWidget()
        self.postCollapsible.addWidget(self.postCustomStep_listWidget)

        # =============================================
        # Step Info collapsible section
        # =============================================
        self.infoCollapsible = CollapsibleWidget("Step Info", expanded=True)
        self.mainLayout.addWidget(self.infoCollapsible, 0)  # no stretch

        infoWidget = QtWidgets.QWidget()
        self.infoLayout = QtWidgets.QFormLayout(infoWidget)
        self.infoLayout.setContentsMargins(4, 2, 4, 2)
        self.infoLayout.setSpacing(4)

        # Info labels
        self.info_name_label = QtWidgets.QLabel("-")
        self.info_name_label.setWordWrap(True)
        self.infoLayout.addRow("Name:", self.info_name_label)

        self.info_type_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Type:", self.info_type_label)

        self.info_status_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Status:", self.info_status_label)

        self.info_shared_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Shared:", self.info_shared_label)

        self.info_exists_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Exists:", self.info_exists_label)

        self.info_modified_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Modified:", self.info_modified_label)

        self.infoCollapsible.addWidget(infoWidget)

        # Path in its own layout for better display
        pathWidget = QtWidgets.QWidget()
        pathLayout = QtWidgets.QVBoxLayout(pathWidget)
        pathLayout.setContentsMargins(4, 0, 4, 2)
        pathLayout.setSpacing(0)

        pathHeaderLayout = QtWidgets.QHBoxLayout()
        pathHeaderLayout.setContentsMargins(0, 0, 0, 0)
        pathLabel = QtWidgets.QLabel("Path:")
        pathHeaderLayout.addWidget(pathLabel)
        pathHeaderLayout.addStretch()
        pathLayout.addLayout(pathHeaderLayout)

        self.info_path_label = QtWidgets.QLabel("-")
        self.info_path_label.setWordWrap(True)
        self.info_path_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.info_path_label.setStyleSheet("padding-left: 10px;")
        pathLayout.addWidget(self.info_path_label)

        self.infoCollapsible.addWidget(pathWidget)

        # Connect collapsible header clicks to update stretch factors
        self.preCollapsible.header_wgt.clicked.connect(self._updateStretchFactors)
        self.postCollapsible.header_wgt.clicked.connect(self._updateStretchFactors)
        self.infoCollapsible.header_wgt.clicked.connect(self._updateStretchFactors)

    def _updateStretchFactors(self):
        """Update layout stretch factors based on collapsed/expanded state."""
        # Get expanded states (after the click has toggled)
        pre_expanded = self.preCollapsible.header_wgt.is_expanded()
        post_expanded = self.postCollapsible.header_wgt.is_expanded()

        # Set stretch: 1 if expanded, 0 if collapsed
        # Info section always has stretch 0 (minimum height)
        self.mainLayout.setStretch(0, 1 if pre_expanded else 0)
        self.mainLayout.setStretch(1, 1 if post_expanded else 0)
        self.mainLayout.setStretch(2, 0)  # Info always minimal


class CustomStepTab(QtWidgets.QDialog, Ui_Form):
    """Custom Step Tab widget."""

    def __init__(self, parent=None):
        super(CustomStepTab, self).__init__(parent)
        self.setupUi(self)


class CustomStepMixin(object):
    """Mixin providing custom step functionality for GuideSettings.

    This mixin expects the host class to have:
        - self.root: The Maya node with custom step attributes
        - self.customStepTab: A CustomStepTab instance
        - Helper methods: populateCheck, updateCheck, updateListAttr
    """

    def setup_custom_step_hover_info(self):
        """Set up hover info for custom step list widgets."""
        self.pre_cs = self.customStepTab.preCustomStep_listWidget
        self.pre_cs.setMouseTracking(True)
        self.pre_cs.entered.connect(self.pre_info)

        self.post_cs = self.customStepTab.postCustomStep_listWidget
        self.post_cs.setMouseTracking(True)
        self.post_cs.entered.connect(self.post_info)

    def pre_info(self, index):
        self.hover_info_item_entered(self.pre_cs, index)

    def post_info(self, index):
        self.hover_info_item_entered(self.post_cs, index)

    def hover_info_item_entered(self, view, index):
        if index.isValid():
            # Get data from UserRole (the step string)
            data = index.data(QtCore.Qt.UserRole)
            if data:
                info_data = self.format_info(data)
                QtWidgets.QToolTip.showText(
                    QtGui.QCursor.pos(),
                    info_data,
                    view.viewport(),
                    view.visualRect(index),
                )

    def populate_custom_step_controls(self):
        """Populate custom step tab controls from Maya attributes."""
        self.populateCheck(
            self.customStepTab.preCustomStep_checkBox, "doPreCustomStep"
        )
        # Load pre custom steps with backwards compatibility
        pre_data = self.root.attr("preCustomStep").get()
        self.customStepTab.preCustomStep_listWidget.loadFromJson(pre_data)

        self.populateCheck(
            self.customStepTab.postCustomStep_checkBox, "doPostCustomStep"
        )
        # Load post custom steps with backwards compatibility
        post_data = self.root.attr("postCustomStep").get()
        self.customStepTab.postCustomStep_listWidget.loadFromJson(post_data)

    def create_custom_step_connections(self):
        """Create signal connections for custom step tab."""
        csTap = self.customStepTab

        # Pre custom step checkbox
        csTap.preCustomStep_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                csTap.preCustomStep_checkBox,
                "doPreCustomStep",
            )
        )

        # Post custom step checkbox
        csTap.postCustomStep_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                csTap.postCustomStep_checkBox,
                "doPostCustomStep",
            )
        )

        # Menu bar actions
        csTap.preExport_action.triggered.connect(self.exportCustomStep)
        csTap.preImport_action.triggered.connect(self.importCustomStep)
        csTap.postExport_action.triggered.connect(
            partial(self.exportCustomStep, False)
        )
        csTap.postImport_action.triggered.connect(
            partial(self.importCustomStep, False)
        )

        # Event filters for drag/drop order changes
        csTap.preCustomStep_listWidget.installEventFilter(self)
        csTap.postCustomStep_listWidget.installEventFilter(self)

        # Order changed signals (for drag-drop reorder)
        csTap.preCustomStep_listWidget.orderChanged.connect(
            partial(self._onStepOrderChanged, pre=True)
        )
        csTap.postCustomStep_listWidget.orderChanged.connect(
            partial(self._onStepOrderChanged, pre=False)
        )

        # Data changed signals (for group edits, toggles, etc.)
        csTap.preCustomStep_listWidget.dataChanged.connect(
            partial(self._onDataChanged, pre=True)
        )
        csTap.postCustomStep_listWidget.dataChanged.connect(
            partial(self._onDataChanged, pre=False)
        )

        # Step toggled signals (from widget toggle buttons)
        csTap.preCustomStep_listWidget.stepToggled.connect(
            partial(self._onStepToggled, pre=True)
        )
        csTap.postCustomStep_listWidget.stepToggled.connect(
            partial(self._onStepToggled, pre=False)
        )

        # Step edit/run signals (from widget buttons)
        csTap.preCustomStep_listWidget.stepEditRequested.connect(
            partial(self._onStepEditRequested, pre=True)
        )
        csTap.postCustomStep_listWidget.stepEditRequested.connect(
            partial(self._onStepEditRequested, pre=False)
        )
        csTap.preCustomStep_listWidget.stepRunRequested.connect(
            partial(self._onStepRunRequested, pre=True)
        )
        csTap.postCustomStep_listWidget.stepRunRequested.connect(
            partial(self._onStepRunRequested, pre=False)
        )

        # Right click context menus
        csTap.preCustomStep_listWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        csTap.preCustomStep_listWidget.customContextMenuRequested.connect(
            self.preCustomStepMenu
        )
        csTap.postCustomStep_listWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        csTap.postCustomStep_listWidget.customContextMenuRequested.connect(
            self.postCustomStepMenu
        )

        # Search highlight
        csTap.preSearch_lineEdit.textChanged.connect(self.preHighlightSearch)
        csTap.postSearch_lineEdit.textChanged.connect(self.postHighlightSearch)

        # Item click to update info panel
        csTap.preCustomStep_listWidget.itemClicked.connect(
            partial(self.updateInfoPanel, pre=True)
        )
        csTap.postCustomStep_listWidget.itemClicked.connect(
            partial(self.updateInfoPanel, pre=False)
        )

        # Group step click to update info panel
        csTap.preCustomStep_listWidget.groupStepClicked.connect(
            partial(self._updateInfoPanelFromData, pre=True)
        )
        csTap.postCustomStep_listWidget.groupStepClicked.connect(
            partial(self._updateInfoPanelFromData, pre=False)
        )

        # File drop connections
        csTap.preCustomStep_listWidget.filesDropped.connect(
            partial(self.onFilesDropped, pre=True)
        )
        csTap.postCustomStep_listWidget.filesDropped.connect(
            partial(self.onFilesDropped, pre=False)
        )

    def _onStepOrderChanged(self, pre=True):
        """Handle step order change from drag-drop."""
        if pre:
            self._updateStepListAttr(
                self.customStepTab.preCustomStep_listWidget, "preCustomStep"
            )
        else:
            self._updateStepListAttr(
                self.customStepTab.postCustomStep_listWidget, "postCustomStep"
            )

    def _onDataChanged(self, pre=True):
        """Handle data change from groups or steps."""
        if pre:
            self._updateStepListAttr(
                self.customStepTab.preCustomStep_listWidget, "preCustomStep"
            )
        else:
            self._updateStepListAttr(
                self.customStepTab.postCustomStep_listWidget, "postCustomStep"
            )

    def _onStepToggled(self, _row, _active, pre=True):
        """Handle step toggle from widget button."""
        if pre:
            self._updateStepListAttr(
                self.customStepTab.preCustomStep_listWidget, "preCustomStep"
            )
        else:
            self._updateStepListAttr(
                self.customStepTab.postCustomStep_listWidget, "postCustomStep"
            )

    def _onStepEditRequested(self, row, pre=True):
        """Handle edit request from widget button."""
        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        step_data = stepWidget.getStepData(row)
        if step_data:
            fullpath = step_data.get_full_path()
            if fullpath:
                self._editFile(fullpath)

    def _onStepRunRequested(self, row, pre=True):
        """Handle run request from widget button."""
        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        step_data = stepWidget.getStepData(row)
        if step_data:
            self.runStep(step_data.path, customStepDic={})

    def _updateStepListAttr(self, stepWidget, stepAttr):
        """Update Maya attribute from step widget contents."""
        new_value = stepWidget.toJson()
        self.root.attr(stepAttr).set(new_value)

    def updateInfoPanel(self, item, pre=True):
        """Update the info panel with details about the clicked custom step."""
        if not item:
            return

        csTap = self.customStepTab

        # Get step data from the item's UserRole or widget
        if pre:
            stepWidget = csTap.preCustomStep_listWidget
        else:
            stepWidget = csTap.postCustomStep_listWidget

        row = stepWidget.row(item)
        step_data = stepWidget.getStepData(row)

        if not step_data:
            return

        self._updateInfoPanelFromData(step_data, pre)

    def _updateInfoPanelFromData(self, step_data, pre=True):
        """Update the info panel from step data directly.

        Args:
            step_data (CustomStepData): The step data to display
            pre (bool): Whether this is a pre or post step
        """
        if not step_data:
            return

        csTap = self.customStepTab

        # Get step info from data model
        cs_name = step_data.name
        cs_status = "Active" if step_data.active else "Deactivated"
        cs_fullpath = step_data.get_full_path()

        # Determine step type (Pre or Post)
        cs_type = "Pre Custom Step" if pre else "Post Custom Step"

        # Check shared status
        if step_data.is_shared:
            cs_shared_owner = self.shared_owner(cs_fullpath)
            cs_shared = "Yes ({})".format(cs_shared_owner)
        else:
            cs_shared = "No (Local)"

        # Check file existence and get modification time
        if step_data.file_exists():
            cs_exists = "Yes"
            try:
                mtime = os.path.getmtime(cs_fullpath)
                cs_modified = datetime.datetime.fromtimestamp(mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                cs_modified = "Unknown"
        else:
            cs_exists = "No (File not found)"
            cs_modified = "-"

        # Update labels
        csTap.info_name_label.setText(cs_name)
        csTap.info_type_label.setText(cs_type)
        csTap.info_status_label.setText(cs_status)
        csTap.info_shared_label.setText(cs_shared)
        csTap.info_exists_label.setText(cs_exists)
        csTap.info_modified_label.setText(cs_modified)
        csTap.info_path_label.setText(cs_fullpath)

        # Color code the status
        if cs_status == "Active":
            csTap.info_status_label.setStyleSheet("color: #00A000;")
        else:
            csTap.info_status_label.setStyleSheet("color: #B40000;")

        # Color code file existence
        if cs_exists == "Yes":
            csTap.info_exists_label.setStyleSheet("color: #00A000;")
        else:
            csTap.info_exists_label.setStyleSheet("color: #B40000;")

    def custom_step_event_filter(self, sender, event):
        """Handle custom step list widget events. Call from eventFilter."""
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.customStepTab.preCustomStep_listWidget:
                self._updateStepListAttr(sender, "preCustomStep")
                return True
            elif sender == self.customStepTab.postCustomStep_listWidget:
                self._updateStepListAttr(sender, "postCustomStep")
                return True
        return False

    def get_cs_file_fullpath(self, cs_data):
        """Get full path of custom step file from list item text."""
        filepath = cs_data.split("|")[-1][1:]
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            fullpath = os.path.join(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""), filepath
            )
        else:
            fullpath = filepath
        return fullpath

    @classmethod
    def _editFile(cls, fullpath):
        """Open file in system default editor."""
        if sys.platform.startswith("darwin"):
            subprocess.call(("open", fullpath))
        elif os.name == "nt":
            os.startfile(fullpath)
        elif os.name == "posix":
            subprocess.call(("xdg-open", fullpath))

    def editFile(self, widgetList):
        """Edit selected custom step files."""
        for item in widgetList.selectedItems():
            try:
                row = widgetList.row(item)
                step_data = widgetList.getStepData(row)
                if step_data:
                    fullpath = step_data.get_full_path()
                    if fullpath:
                        self._editFile(fullpath)
                    else:
                        pm.displayWarning("Please select one item from the list")
                else:
                    pm.displayWarning("Please select one item from the list")
            except Exception:
                pm.displayError("The step can't be found or doesn't exist")

    def format_info(self, data):
        """Format custom step info for tooltip display."""
        data_parts = data.split("|")
        cs_name = data_parts[0]
        if cs_name.startswith("*"):
            cs_status = "Deactivated"
            cs_name = cs_name[1:]
        else:
            cs_status = "Active"

        cs_fullpath = self.get_cs_file_fullpath(data)
        if "_shared" in data:
            cs_shared_owner = self.shared_owner(cs_fullpath)
            cs_shared_status = "Shared"
        else:
            cs_shared_status = "Local"
            cs_shared_owner = "None"

        info = '<html><head/><body><p><span style=" font-weight:600;">\
        {0}</span></p><p>------------------</p><p><span style=" \
        font-weight:600;">Status</span>: {1}</p><p><span style=" \
        font-weight:600;">Shared Status:</span> {2}</p><p><span \
        style=" font-weight:600;">Shared Owner:</span> \
        {3}</p><p><span style=" font-weight:600;">Full Path</span>: \
        {4}</p></body></html>'.format(
            cs_name, cs_status, cs_shared_status, cs_shared_owner, cs_fullpath
        )
        return info

    def shared_owner(self, cs_fullpath):
        """Get the owner of a shared custom step."""
        scan_dir = os.path.abspath(os.path.join(cs_fullpath, os.pardir))
        while not scan_dir.endswith("_shared"):
            scan_dir = os.path.abspath(os.path.join(scan_dir, os.pardir))
            if scan_dir == "/":
                break
        scan_dir = os.path.abspath(os.path.join(scan_dir, os.pardir))
        return os.path.split(scan_dir)[1]

    @classmethod
    def get_steps_dict(cls, itemsList):
        """Get dictionary of step paths and their contents."""
        stepsDict = {}
        stepsDict["itemsList"] = itemsList
        for item in itemsList:
            step = open(item, "r")
            data = step.read()
            stepsDict[item] = data
            step.close()
        return stepsDict

    @classmethod
    def runStep(cls, stepPath, customStepDic):
        """Run a custom step.

        Args:
            stepPath: Path to the custom step file
            customStepDic: Dictionary of previously run custom steps

        Returns:
            True if build should stop, False otherwise
        """
        try:
            with pm.UndoChunk():
                pm.displayInfo("EXEC: Executing custom step: %s" % stepPath)
                if sys.platform.startswith("darwin"):
                    stepPath = stepPath.replace("\\", "/")

                fileName = os.path.split(stepPath)[1].split(".")[0]

                if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                    runPath = os.path.join(
                        os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""),
                        stepPath,
                    )
                else:
                    runPath = stepPath

                customStep = imp.load_source(fileName, runPath)
                if hasattr(customStep, "CustomShifterStep"):
                    argspec = inspect.getfullargspec(
                        customStep.CustomShifterStep.__init__
                    )
                    if "stored_dict" in argspec.args:
                        cs = customStep.CustomShifterStep(customStepDic)
                        cs.setup()
                        cs.run()
                    else:
                        cs = customStep.CustomShifterStep()
                        cs.run(customStepDic)
                    customStepDic[cs.name] = cs
                    pm.displayInfo(
                        "SUCCEED: Custom Shifter Step Class: %s. "
                        "Succeed!!" % stepPath
                    )
                else:
                    pm.displayInfo(
                        "SUCCEED: Custom Step simple script: %s. "
                        "Succeed!!" % stepPath
                    )

        except Exception as ex:
            template = "An exception of type {0} occurred. "
            "Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            pm.displayError(message)
            pm.displayError(traceback.format_exc())
            cont = pm.confirmBox(
                "FAIL: Custom Step Fail",
                "The step:%s has failed. Continue with next step?" % stepPath
                + "\n\n"
                + message
                + "\n\n"
                + traceback.format_exc(),
                "Continue",
                "Stop Build",
                "Edit",
                "Try Again!",
            )
            if cont == "Stop Build":
                return True
            elif cont == "Edit":
                cls._editFile(stepPath)
            elif cont == "Try Again!":
                try:
                    pm.undo()
                except Exception:
                    pass
                pm.displayInfo("Trying again! : {}".format(stepPath))
                inception = cls.runStep(stepPath, customStepDic)
                if inception:
                    return True
            else:
                return False

    def runManualStep(self, widgetList):
        """Run selected custom steps manually."""
        selItems = widgetList.selectedItems()
        for item in selItems:
            row = widgetList.row(item)
            step_data = widgetList.getStepData(row)
            if step_data:
                self.runStep(step_data.path, customStepDic={})

    def _processCustomStepPath(self, filePath):
        """Process a file path for custom step, making it relative if needed.

        Args:
            filePath: The absolute file path to process

        Returns:
            tuple: (fileName, processedPath) where processedPath is relative
                   to MGEAR_SHIFTER_CUSTOMSTEP_PATH if that env var is set
        """
        customStepPath = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")

        if customStepPath:
            # Normalize file path - handle potential leading slash from Qt URLs
            # on Windows (e.g., "/D:/path" -> "D:/path")
            if (
                sys.platform == "win32"
                and len(filePath) > 2
                and filePath[0] == "/"
                and filePath[2] == ":"
            ):
                filePath = filePath[1:]

            # Use os.path.relpath for reliable relative path calculation
            try:
                absFilePath = os.path.abspath(filePath)
                absBasePath = os.path.abspath(customStepPath)

                # Check if file is under the custom step path
                # Use normcase for case-insensitive comparison on Windows
                startswith_sep = os.path.normcase(absFilePath).startswith(
                    os.path.normcase(absBasePath + os.sep)
                )
                startswith_base = os.path.normcase(absFilePath).startswith(
                    os.path.normcase(absBasePath)
                )

                if startswith_sep or startswith_base:
                    filePath = os.path.relpath(absFilePath, absBasePath)
                    # Normalize to forward slashes for consistency
                    filePath = filePath.replace("\\", "/")
            except ValueError:
                # relpath fails if paths are on different drives on Windows
                pass

        fileName = os.path.split(filePath)[1].split(".")[0]
        return fileName, filePath

    def _addFilesToStepWidget(self, filePaths, stepWidget, stepAttr):
        """Add file paths to a custom step list widget.

        Args:
            filePaths: List of file paths to add
            stepWidget: The CustomStepListWidget to add items to
            stepAttr: The Maya attribute name to update
        """
        for filePath in filePaths:
            fileName, processedPath = self._processCustomStepPath(filePath)
            step_data = CustomStepData(
                name=fileName, path=processedPath, active=True
            )
            stepWidget.addStepItem(step_data)

        self._updateStepListAttr(stepWidget, stepAttr)

    def addCustomStep(self, pre=True, *args):
        """Add a new custom step.

        Args:
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        filePaths = pm.fileDialog2(
            fileMode=4,
            startingDirectory=startDir,
            okc="Add",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePaths:
            return

        self._addFilesToStepWidget(filePaths, stepWidget, stepAttr)

    def onFilesDropped(self, filePaths, pre=True):
        """Handle .py files dropped onto the custom step list.

        Args:
            filePaths: List of file paths that were dropped
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        self._addFilesToStepWidget(filePaths, stepWidget, stepAttr)

    def newCustomStep(self, pre=True, *args):
        """Create a new custom step file.

        Args:
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            okc="New",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        n, e = os.path.splitext(filePath)
        stepName = os.path.split(n)[-1]

        rawString = r'''import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{stepName}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "{stepName}"

    def run(self):
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        return'''.format(stepName=stepName)

        f = open(filePath, "w")
        f.write(rawString + "\n")
        f.close()

        # Process the path and add to widget
        fileName, processedPath = self._processCustomStepPath(filePath)
        step_data = CustomStepData(
            name=fileName, path=processedPath, active=True
        )
        stepWidget.addStepItem(step_data)
        self._updateStepListAttr(stepWidget, stepAttr)

    def duplicateCustomStep(self, pre=True, *args):
        """Duplicate the selected custom step.

        Args:
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        # Get source path from selected item
        sourcePath = None
        if stepWidget.selectedItems():
            item = stepWidget.selectedItems()[0]
            row = stepWidget.row(item)
            step_data = stepWidget.getStepData(row)
            if step_data:
                sourcePath = step_data.path

        if not sourcePath:
            pm.displayWarning("Please select a step to duplicate")
            return

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            okc="New",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        # Get full source path and copy
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            fullSourcePath = os.path.join(startDir, sourcePath)
        else:
            fullSourcePath = sourcePath
        shutil.copy(fullSourcePath, filePath)

        # Process the path and add to widget
        fileName, processedPath = self._processCustomStepPath(filePath)
        step_data = CustomStepData(
            name=fileName, path=processedPath, active=True
        )
        stepWidget.addStepItem(step_data)
        self._updateStepListAttr(stepWidget, stepAttr)

    def exportCustomStep(self, pre=True, *args):
        """Export custom steps to a JSON file.

        Args:
            pre: If True, exports from pre step list; otherwise from post
        """
        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Get all step data
        all_step_data = stepWidget.getAllStepData()
        if not all_step_data:
            pm.displayWarning("No custom steps to export.")
            return

        # Build list of full paths
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            itemsList = [
                os.path.join(startDir, sd.path) for sd in all_step_data
            ]
        else:
            itemsList = [sd.path for sd in all_step_data]
            if itemsList:
                startDir = os.path.split(itemsList[-1])[0]
            else:
                startDir = pm.workspace(q=True, rootDirectory=True)

        stepsDict = self.get_steps_dict(itemsList)
        data_string = json.dumps(stepsDict, indent=4, sort_keys=True)

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            fileFilter="Shifter Custom Steps .scs (*%s)" % ".scs",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        f = open(filePath, "w")
        f.write(data_string)
        f.close()

    def importCustomStep(self, pre=True, *args):
        """Import custom steps from a JSON file.

        Args:
            pre: If True, imports to pre step list; otherwise to post
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        option = pm.confirmDialog(
            title="Shifter Custom Step Import Style",
            message="Do you want to import only the path or"
            " unpack and import?",
            button=["Only Path", "Unpack", "Cancel"],
            defaultButton="Only Path",
            cancelButton="Cancel",
            dismissString="Cancel",
        )

        if option in ["Only Path", "Unpack"]:
            if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            else:
                startDir = pm.workspace(q=True, rootDirectory=True)

            filePath = pm.fileDialog2(
                fileMode=1,
                startingDirectory=startDir,
                fileFilter="Shifter Custom Steps .scs (*%s)" % ".scs",
            )
            if not filePath:
                return
            if not isinstance(filePath, string_types):
                filePath = filePath[0]
            stepDict = json.load(open(filePath))
            stepsList = []

        if option == "Only Path":
            for item in stepDict["itemsList"]:
                stepsList.append(item)

        elif option == "Unpack":
            unPackDir = pm.fileDialog2(fileMode=2, startingDirectory=startDir)
            if not filePath:
                return
            if not isinstance(unPackDir, string_types):
                unPackDir = unPackDir[0]

            for item in stepDict["itemsList"]:
                fileName = os.path.split(item)[1]
                fileNewPath = os.path.join(unPackDir, fileName)
                stepsList.append(fileNewPath)
                f = open(fileNewPath, "w")
                f.write(stepDict[item])
                f.close()

        if option in ["Only Path", "Unpack"]:
            for item in stepsList:
                # Process the path and add to widget
                fileName, processedPath = self._processCustomStepPath(item)
                step_data = CustomStepData(
                    name=fileName, path=processedPath, active=True
                )
                stepWidget.addStepItem(step_data)

            self._updateStepListAttr(stepWidget, stepAttr)

    def _customStepMenu(self, cs_listWidget, stepAttr, QPos, pre=True):
        """Right click context menu for custom step."""
        # Check if clicking on a step inside a group first
        clickedItem = cs_listWidget.itemAt(QPos)
        clickedRow = cs_listWidget.row(clickedItem) if clickedItem else -1

        if clickedRow >= 0 and cs_listWidget.isGroupRow(clickedRow):
            # Check if the click is on a step widget inside the group
            group_widget = cs_listWidget.getGroupWidget(clickedRow)
            if group_widget and not group_widget.is_collapsed():
                # Map the position to global coordinates using viewport
                global_pos = cs_listWidget.viewport().mapToGlobal(QPos)

                # Check each step widget in the group using global rect
                step_widgets = group_widget.get_step_widgets()
                for step_widget in step_widgets:
                    # Skip if widget is not visible
                    if not step_widget.isVisible():
                        continue
                    # Get the step widget's global rectangle
                    widget_global_pos = step_widget.mapToGlobal(
                        QtCore.QPoint(0, 0)
                    )
                    widget_rect = QtCore.QRect(
                        widget_global_pos, step_widget.size()
                    )
                    if widget_rect.contains(global_pos):
                        # Click is on a step inside the group - show group step menu
                        cs_listWidget._on_group_step_context_menu(
                            step_widget, global_pos, group_widget
                        )
                        return

        self.csMenu = QtWidgets.QMenu()
        parentPosition = cs_listWidget.mapToGlobal(QtCore.QPoint(0, 0))

        # Add/New actions (always available)
        add_action = self.csMenu.addAction("Add")
        add_action.setIcon(pyqt.get_icon("mgear_folder-plus"))
        new_action = self.csMenu.addAction("New")
        new_action.setIcon(pyqt.get_icon("mgear_file-plus"))

        self.csMenu.addSeparator()

        # Selection-dependent actions
        selectedItems = cs_listWidget.selectedItems()
        hasSelection = len(selectedItems) > 0

        isClickedGroup = clickedRow >= 0 and cs_listWidget.isGroupRow(clickedRow)

        # Check if selection contains only steps (no groups)
        hasStepSelection = False
        if hasSelection:
            for item in selectedItems:
                row = cs_listWidget.row(item)
                if not cs_listWidget.isGroupRow(row):
                    hasStepSelection = True
                    break

        run_action = self.csMenu.addAction("Run Selected")
        run_action.setIcon(pyqt.get_icon("mgear_play"))
        run_action.setEnabled(hasSelection)

        edit_action = self.csMenu.addAction("Edit")
        edit_action.setIcon(pyqt.get_icon("mgear_edit"))
        edit_action.setEnabled(hasSelection and not isClickedGroup)

        duplicate_action = self.csMenu.addAction("Duplicate")
        duplicate_action.setIcon(pyqt.get_icon("mgear_copy"))
        duplicate_action.setEnabled(hasSelection and not isClickedGroup)

        remove_action = self.csMenu.addAction("Remove")
        remove_action.setIcon(pyqt.get_icon("mgear_trash-2"))
        remove_action.setEnabled(hasStepSelection)

        self.csMenu.addSeparator()

        # Group actions
        create_group_action = self.csMenu.addAction("Create Group")
        create_group_action.setIcon(pyqt.get_icon("mgear_folder"))
        create_group_action.setEnabled(hasStepSelection)

        # Group-specific actions (only if clicked on a group)
        if isClickedGroup:
            rename_group_action = self.csMenu.addAction("Rename Group")
            rename_group_action.setIcon(pyqt.get_icon("mgear_edit-2"))

            ungroup_action = self.csMenu.addAction("Ungroup (Keep Items)")
            ungroup_action.setIcon(pyqt.get_icon("mgear_minimize-2"))

            delete_group_action = self.csMenu.addAction("Delete Group...")
            delete_group_action.setIcon(pyqt.get_icon("mgear_trash-2"))

        self.csMenu.addSeparator()

        # Toggle status actions
        toggle_action = self.csMenu.addAction("Toggle Status")
        toggle_action.setIcon(pyqt.get_icon("mgear_refresh-cw"))
        toggle_action.setEnabled(hasSelection)

        off_selected_action = self.csMenu.addAction("Turn OFF Selected")
        off_selected_action.setIcon(pyqt.get_icon("mgear_toggle-left"))
        off_selected_action.setEnabled(hasSelection)

        on_selected_action = self.csMenu.addAction("Turn ON Selected")
        on_selected_action.setIcon(pyqt.get_icon("mgear_toggle-right"))
        on_selected_action.setEnabled(hasSelection)

        self.csMenu.addSeparator()

        off_all_action = self.csMenu.addAction("Turn OFF All")
        off_all_action.setIcon(pyqt.get_icon("mgear_x-circle"))
        on_all_action = self.csMenu.addAction("Turn ON All")
        on_all_action.setIcon(pyqt.get_icon("mgear_check-circle"))

        # Connect actions
        add_action.triggered.connect(partial(self.addCustomStep, pre))
        new_action.triggered.connect(partial(self.newCustomStep, pre))
        run_action.triggered.connect(
            partial(self.runManualStep, cs_listWidget)
        )
        edit_action.triggered.connect(partial(self.editFile, cs_listWidget))
        duplicate_action.triggered.connect(
            partial(self.duplicateCustomStep, pre)
        )
        remove_action.triggered.connect(
            partial(
                self.removeSelectedFromListWidget, cs_listWidget, stepAttr
            )
        )

        # Group action connections
        create_group_action.triggered.connect(
            partial(self._createGroup, cs_listWidget, stepAttr)
        )
        if isClickedGroup:
            rename_group_action.triggered.connect(
                partial(self._renameGroup, cs_listWidget, clickedRow)
            )
            ungroup_action.triggered.connect(
                partial(self._ungroupItems, cs_listWidget, stepAttr, clickedRow, True)
            )
            delete_group_action.triggered.connect(
                partial(self._deleteGroupDialog, cs_listWidget, stepAttr, clickedRow)
            )

        toggle_action.triggered.connect(
            partial(self.toggleStatusCustomStep, cs_listWidget, stepAttr)
        )
        off_selected_action.triggered.connect(
            partial(self.setStatusCustomStep, cs_listWidget, stepAttr, False)
        )
        on_selected_action.triggered.connect(
            partial(self.setStatusCustomStep, cs_listWidget, stepAttr, True)
        )
        off_all_action.triggered.connect(
            partial(
                self.setStatusCustomStep, cs_listWidget, stepAttr, False, False
            )
        )
        on_all_action.triggered.connect(
            partial(
                self.setStatusCustomStep, cs_listWidget, stepAttr, True, False
            )
        )

        self.csMenu.move(parentPosition + QPos)
        self.csMenu.show()

    def _createGroup(self, cs_listWidget, stepAttr):
        """Create a group from selected items."""
        # Prompt for group name
        name, ok = QtWidgets.QInputDialog.getText(
            None,
            "Create Group",
            "Group name:",
            QtWidgets.QLineEdit.Normal,
            "New Group"
        )
        if ok and name:
            cs_listWidget.createGroupFromSelection(name)
            self._updateStepListAttr(cs_listWidget, stepAttr)

    def _renameGroup(self, cs_listWidget, row):
        """Trigger inline rename for a group."""
        group_widget = cs_listWidget.getGroupWidget(row)
        if group_widget:
            # Access the header and trigger editing
            group_widget._header._start_editing()

    def _ungroupItems(self, cs_listWidget, stepAttr, row, keep_items=True):
        """Ungroup items at the given row."""
        cs_listWidget.ungroupItems(row, keep_items)
        self._updateStepListAttr(cs_listWidget, stepAttr)

    def _deleteGroupDialog(self, cs_listWidget, stepAttr, row):
        """Show dialog for group deletion options."""
        group_widget = cs_listWidget.getGroupWidget(row)
        if not group_widget:
            return

        group_data = group_widget.get_group_data()
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Delete Group")
        msg.setText("Delete group '{}'?".format(group_data.name))
        msg.setInformativeText("What should happen to the steps inside?")

        keep_btn = msg.addButton("Keep Steps", QtWidgets.QMessageBox.AcceptRole)
        delete_btn = msg.addButton("Delete Steps", QtWidgets.QMessageBox.DestructiveRole)
        msg.addButton(QtWidgets.QMessageBox.Cancel)

        msg.exec_()

        if msg.clickedButton() == keep_btn:
            cs_listWidget.ungroupItems(row, keep_items=True)
            self._updateStepListAttr(cs_listWidget, stepAttr)
        elif msg.clickedButton() == delete_btn:
            cs_listWidget.ungroupItems(row, keep_items=False)
            self._updateStepListAttr(cs_listWidget, stepAttr)

    def preCustomStepMenu(self, QPos):
        """Show pre custom step context menu."""
        self._customStepMenu(
            self.customStepTab.preCustomStep_listWidget,
            "preCustomStep",
            QPos,
            pre=True,
        )

    def postCustomStepMenu(self, QPos):
        """Show post custom step context menu."""
        self._customStepMenu(
            self.customStepTab.postCustomStep_listWidget,
            "postCustomStep",
            QPos,
            pre=False,
        )

    def toggleStatusCustomStep(self, cs_listWidget, stepAttr):
        """Toggle the active status of selected custom steps."""
        items = cs_listWidget.selectedItems()
        for item in items:
            row = cs_listWidget.row(item)
            cs_listWidget.toggleStepActive(row)

        self._updateStepListAttr(cs_listWidget, stepAttr)

    def setStatusCustomStep(
        self, cs_listWidget, stepAttr, status=True, selected=True
    ):
        """Set the status of custom steps.

        Args:
            cs_listWidget: The list widget containing custom steps
            stepAttr: The Maya attribute name for this step list
            status: True to enable, False to disable
            selected: If True, only affect selected items; otherwise all
        """
        if selected:
            items = cs_listWidget.selectedItems()
            for item in items:
                row = cs_listWidget.row(item)
                cs_listWidget.setStepActive(row, status)
        else:
            # All items
            for i in range(cs_listWidget.count()):
                cs_listWidget.setStepActive(i, status)

        self._updateStepListAttr(cs_listWidget, stepAttr)

    def preHighlightSearch(self):
        """Highlight pre custom step items matching search."""
        searchText = self.customStepTab.preSearch_lineEdit.text()
        self.customStepTab.preCustomStep_listWidget.highlightSearch(searchText)

    def postHighlightSearch(self):
        """Highlight post custom step items matching search."""
        searchText = self.customStepTab.postSearch_lineEdit.text()
        self.customStepTab.postCustomStep_listWidget.highlightSearch(
            searchText
        )

    def removeSelectedFromListWidget(self, listWidget, targetAttr=None):
        """Remove selected items from the list widget.

        Override of HelperSlots.removeSelectedFromListWidget that handles groups
        properly - only removes individual steps, not groups.

        Args:
            listWidget: CustomStepListWidget instance
            targetAttr (str): Maya attribute name to update
        """
        if not isinstance(listWidget, CustomStepListWidget):
            # Fall back to parent implementation for non-CustomStepListWidget
            for item in listWidget.selectedItems():
                listWidget.takeItem(listWidget.row(item))
            if targetAttr:
                self.updateListAttr(listWidget, targetAttr)
            return

        # Collect selected items
        selected_items = listWidget.selectedItems()
        if not selected_items:
            return

        # Separate groups and steps
        group_rows = []
        step_rows = []
        for item in selected_items:
            row = listWidget.row(item)
            if listWidget.isGroupRow(row):
                group_rows.append(row)
            else:
                step_rows.append(row)

        # Warn if groups are selected
        if group_rows:
            pm.displayWarning(
                "Groups cannot be removed directly. Use 'Delete Group...' "
                "from the context menu to delete a group."
            )

        # Remove steps only (in reverse order to preserve indices)
        for row in sorted(step_rows, reverse=True):
            listWidget.takeItem(row)

        # Update attribute
        if targetAttr and step_rows:
            self._updateStepListAttr(listWidget, targetAttr)


# Backwards compatibility alias
customStepTab = CustomStepTab

# Module-level function for external access (used by shifter build process)
runStep = CustomStepMixin.runStep
