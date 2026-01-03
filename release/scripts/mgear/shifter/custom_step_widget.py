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
# Helper Functions
# ============================================================================


def _resolve_source_path(source_file):
    """Resolve a source file path using the environment variable if needed.

    Args:
        source_file (str): The source file path (may be relative)

    Returns:
        str: The resolved full path
    """
    if not source_file:
        return source_file
    env_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
    if env_path and not os.path.isabs(source_file):
        # On Windows, os.path.join behaves unexpectedly with bare drive letters:
        # os.path.join("W:", "file.py") returns "W:file.py" (no backslash!)
        # We need to ensure the base path ends with a separator for proper joining
        #
        # Handle various input forms:
        # - "W:" -> "W:\"
        # - "W:\" -> "W:\" (already correct)
        # - "W:\path" -> "W:\path\" (needs separator for joining)
        # - "W:\path\" -> "W:\path\" (already correct)
        env_path = env_path.rstrip("/\\")  # Remove any trailing separators
        env_path = env_path + os.sep  # Add proper separator
        # Join and normalize the full path
        full_path = os.path.join(env_path, source_file)
        return os.path.normpath(full_path)
    return source_file


def _get_step_path_from_source_file(source_file, group_name, step_name):
    """Load a step's path from a source .scs file.

    Args:
        source_file (str): Full path to the .scs file
        group_name (str): Name of the group to find
        step_name (str): Name of the step to find

    Returns:
        str: The step's path from the source file, or None if not found
    """
    try:
        if not os.path.exists(source_file):
            return None

        with open(source_file, "r") as f:
            config_dict = json.load(f)

        # Find the group
        for item_data in config_dict.get("items", []):
            if item_data.get("type") == "group":
                if item_data.get("name") == group_name:
                    # Find the step in this group
                    for step_item in item_data.get("items", []):
                        if step_item.get("name") == step_name:
                            return step_item.get("path", "")
        return None
    except Exception as e:
        import mgear.pymaya as pm
        pm.displayWarning(
            "Error reading source file {}: {}".format(source_file, str(e))
        )
        return None


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
        env_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        if env_path and self._path:
            # Use the helper function for consistent path resolution
            return _resolve_source_path(self._path)
        elif env_path:
            # Ensure the env path is properly formatted (add separator for bare drive letters)
            env_path = env_path.rstrip("/\\") + os.sep
            return os.path.normpath(env_path)
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
        referenced (bool): Whether this is a referenced group (read-only internal structure)
        source_file (str): Path to the source .scs file if referenced
    """

    def __init__(self, name="", collapsed=False, active=True, items=None,
                 referenced=False, source_file=""):
        """Initialize GroupData.

        Args:
            name (str): Display name of the group
            collapsed (bool): Whether group is collapsed
            active (bool): Whether group is active
            items (list): List of CustomStepData objects
            referenced (bool): Whether this is a referenced group
            source_file (str): Path to source .scs file if referenced
        """
        self._name = name
        self._collapsed = collapsed
        self._active = active
        self._items = items if items is not None else []
        self._referenced = referenced
        self._source_file = source_file

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

    @property
    def referenced(self):
        """bool: Whether this is a referenced group (read-only internal structure)."""
        return self._referenced

    @referenced.setter
    def referenced(self, value):
        self._referenced = bool(value)

    @property
    def source_file(self):
        """str: Path to the source .scs file if this is a referenced group."""
        return self._source_file

    @source_file.setter
    def source_file(self, value):
        self._source_file = value

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
        result = {
            "type": "group",
            "name": self._name,
            "collapsed": self._collapsed,
            "active": self._active,
            "items": [item.to_dict() for item in self._items]
        }
        # Only include referenced fields if this is a referenced group
        if self._referenced:
            result["referenced"] = True
            result["source_file"] = self._source_file
        return result

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
            items=items,
            referenced=data.get("referenced", False),
            source_file=data.get("source_file", "")
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
        # Show inactive icon if step is inactive OR if parent group is inactive
        if self._step_data.active and not self._group_inactive:
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

    def set_edit_enabled(self, enabled):
        """Enable or disable the edit button.

        Args:
            enabled (bool): Whether the edit button should be enabled
        """
        self._edit_btn.setEnabled(enabled)
        # Also update appearance
        if not enabled:
            self._edit_btn.setToolTip("Edit disabled (referenced group)")
        else:
            self._edit_btn.setToolTip("Edit step file")

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
    runRequested = QtCore.Signal()

    # Style constants - slightly different shade for groups
    GROUP_COLOR = "#4A4A5A"  # Darker purple-gray for groups
    INACTIVE_COLOR = "#5A4444"  # Darker red for inactive groups
    SELECTED_COLOR = "#4A6B8A"  # Pale blue for selected
    REFERENCED_COLOR = "#3A5A4A"  # Greenish for referenced groups
    BORDER_COLOR = "#666666"
    SELECTED_BORDER_COLOR = "#6A9BCA"
    REFERENCED_BORDER_COLOR = "#5A8A6A"  # Greenish border for referenced
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

        # Run button to execute all steps in the group
        self._run_btn = QtWidgets.QPushButton()
        self._run_btn.setFixedSize(self.BUTTON_SIZE, self.BUTTON_SIZE)
        self._run_btn.setToolTip("Run all steps in group")
        self._run_btn.setFlat(True)
        self._run_btn.setIcon(pyqt.get_icon("mgear_play", self.ICON_SIZE))
        self._run_btn.clicked.connect(self.runRequested.emit)
        layout.addWidget(self._run_btn)

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
        elif self._group_data.referenced:
            bg_color = self.REFERENCED_COLOR
            border_color = self.REFERENCED_BORDER_COLOR
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
        # Don't allow editing for referenced groups
        if self._group_data.referenced:
            super(GroupHeaderWidget, self).mouseDoubleClickEvent(event)
            return
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
        runRequested: Run all steps in group requested
    """

    toggled = QtCore.Signal(bool)
    collapsed = QtCore.Signal(bool)
    nameChanged = QtCore.Signal(str)
    dataChanged = QtCore.Signal()
    stepClicked = QtCore.Signal(object, object, object)  # (step_widget, group_widget, modifiers)
    stepContextMenu = QtCore.Signal(object, object, object)  # (step_widget, pos, group_widget)
    stepDragStarted = QtCore.Signal(object, object)  # (step_widget, group_widget)
    runRequested = QtCore.Signal()

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
        self._header.runRequested.connect(self.runRequested.emit)
        layout.addWidget(self._header)

        # Body container for step items
        self._body = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self._body)
        # Bottom margin provides extra drop zone space for dropping as last item
        body_layout.setContentsMargins(self.CHILD_INDENT, 2, 0, 12)
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

    def _refresh_step_widgets(self):
        """Refresh step widgets from the group data.

        Clears existing step widgets and recreates them from the current
        group data items. Used when the data is updated from an external source.
        """
        # Clear existing step widgets
        for widget in self._step_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._step_widgets = []

        # Recreate step widgets from updated data
        self._populate()

        # Update the header item count
        self._header._update_count()

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

        # Disable edit button for referenced groups
        if self._group_data.referenced:
            widget.set_edit_enabled(False)

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
        # Don't allow editing for steps inside referenced groups
        if self._group_data.referenced:
            return
        # Find the step data and emit with path
        step_data = widget.get_step_data()
        if step_data:
            fullpath = step_data.get_full_path()
            if fullpath:
                CustomStepMixin._editFile(fullpath)

    def _on_step_run_requested(self, widget):
        """Handle step run request.

        For referenced groups, tries to load fresh data from the source .scs file.
        Falls back to embedded data if source file is not available.
        """
        step_data = widget.get_step_data()
        if not step_data:
            return

        step_path = step_data.path

        # For referenced groups, try to load fresh data from source file
        if self._group_data.referenced:
            source_file = self._group_data.source_file
            group_name = self._group_data.name
            step_name = step_data.name

            if source_file:
                resolved_source = _resolve_source_path(source_file)
                fresh_step_path = _get_step_path_from_source_file(
                    resolved_source, group_name, step_name
                )
                if fresh_step_path:
                    step_path = fresh_step_path
                    pm.displayInfo(
                        "Running step '{}' from source file: {}".format(
                            step_name, resolved_source
                        )
                    )
                else:
                    pm.displayWarning(
                        "Could not load '{}' from source file, "
                        "using embedded data".format(step_name)
                    )

        CustomStepMixin.runStep(step_path, customStepDic={})

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

    def move_steps(self, from_indices, to_index):
        """Move multiple steps to a new position within the group.

        The steps will be moved as a block, preserving their relative order.

        Args:
            from_indices (list): List of indices of steps to move (sorted)
            to_index (int): Target index where steps should be inserted
        """
        if not from_indices:
            return

        # Validate indices
        for idx in from_indices:
            if not (0 <= idx < len(self._step_widgets)):
                return

        # Collect widgets and data in order
        items_to_move = []
        for idx in sorted(from_indices):
            items_to_move.append((
                self._step_widgets[idx],
                self._group_data.items[idx]
            ))

        # Calculate effective target index after removal
        # Count how many items before target will be removed
        items_before_target = sum(1 for idx in from_indices if idx < to_index)
        effective_target = to_index - items_before_target

        # Remove from current positions (in reverse order to preserve indices)
        for idx in sorted(from_indices, reverse=True):
            widget = self._step_widgets.pop(idx)
            self._group_data.items.pop(idx)
            self._steps_layout.removeWidget(widget)

        # Insert at new position
        for i, (widget, step_data) in enumerate(items_to_move):
            insert_idx = effective_target + i
            self._step_widgets.insert(insert_idx, widget)
            self._group_data.items.insert(insert_idx, step_data)
            self._steps_layout.insertWidget(insert_idx, widget)

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

    def is_referenced(self):
        """Check if this is a referenced group (read-only internal structure).

        Returns:
            bool: True if this is a referenced group
        """
        return self._group_data.referenced

    def get_source_file(self):
        """Get the source file path for referenced groups.

        Returns:
            str: Path to the source .scs file, or empty string if not referenced
        """
        return self._group_data.source_file

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

        # If past all widgets or in the bottom padding zone, insert at end
        # Also check if we're in the body area (after last widget)
        if self._step_widgets:
            last_widget = self._step_widgets[-1]
            last_widget_bottom = last_widget.geometry().bottom()
            # If cursor is below the last widget, definitely add to end
            if y >= last_widget_bottom:
                return len(self._step_widgets)

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
        groupRunRequested: Emitted when run is requested for a group (row)
        orderChanged: Emitted when items are reordered
        dataChanged: Emitted when any data changes (for JSON storage)
    """

    filesDropped = QtCore.Signal(list)
    stepToggled = QtCore.Signal(int, bool)
    stepEditRequested = QtCore.Signal(int)
    stepRunRequested = QtCore.Signal(int)
    groupRunRequested = QtCore.Signal(int)
    orderChanged = QtCore.Signal()
    dataChanged = QtCore.Signal()
    groupStepClicked = QtCore.Signal(object, object)  # Emitted when step in group clicked (CustomStepData, GroupData)

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

        # Flag to prevent _on_selection_changed from clearing group step selections
        # when the selection change is triggered by clicking inside a group
        self._handling_group_step_click = False

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
        """Filter events on the viewport.

        Note: Click handling for steps inside groups is done by the widget signals
        (clicked -> stepClicked -> _on_group_step_clicked). The event filter does
        NOT intercept these clicks because they go directly to the child widgets.
        """
        return super(CustomStepListWidget, self).eventFilter(obj, event)

    def _on_selection_changed(self):
        """Handle selection change and update widget appearances."""
        # Get selected rows as a set (rows are hashable, items are not in PySide6)
        selected_rows = set(self.row(item) for item in self.selectedItems())

        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if widget and hasattr(widget, 'set_selected'):
                widget.set_selected(i in selected_rows)

        # Only clear group step selections if actual list items are selected
        # AND we're not currently handling a group step click
        # (clicking inside a group also triggers selection of the group row)
        if selected_rows and self._selected_group_steps and not self._handling_group_step_click:
            self._clear_group_step_selections()

    def _clear_all_selections(self):
        """Clear both list selections and group step selections."""
        self.clearSelection()
        self._clear_group_step_selections()

    def _clear_group_step_selections(self):
        """Clear all step selections inside groups."""
        for step_widget, _ in self._selected_group_steps:
            # Check if widget is still valid (not deleted)
            try:
                if step_widget is not None:
                    step_widget.set_selected(False)
            except RuntimeError:
                # Widget was deleted (C++ object already deleted)
                pass
        self._selected_group_steps = []

        # Also clear any selected steps in all groups (safety)
        for i in range(self.count()):
            widget = self.getItemWidget(i)
            if isinstance(widget, GroupWidget):
                widget.clear_step_selections()

    def _on_group_step_clicked(self, step_widget, group_widget, modifiers):
        """Handle click on a step inside a group (signal handler).

        This is connected to the stepClicked signal from GroupWidget.

        Args:
            step_widget (CustomStepItemWidget): The clicked step widget
            group_widget (GroupWidget): The group containing the step
            modifiers (Qt.KeyboardModifiers): Keyboard modifiers during click
        """
        self._handle_group_step_click_internal(step_widget, group_widget, modifiers)

    def _handle_group_step_click_internal(self, step_widget, group_widget, modifiers):
        """Internal handler for group step click logic.

        This contains the actual click handling logic and is called either from
        the event filter (directly) or from _on_group_step_clicked (via signal).

        Args:
            step_widget (CustomStepItemWidget): The clicked step widget
            group_widget (GroupWidget): The group containing the step
            modifiers (Qt.KeyboardModifiers): Keyboard modifiers during click
        """
        # Set flag to prevent _on_selection_changed from clearing our selections
        # This is needed because clicking inside a group also triggers Qt to select
        # the group's row, which would otherwise clear our group step selections
        self._handling_group_step_click = True

        # Clear list widget selection
        self.clearSelection()

        # Check modifiers - handle both PySide2 and PySide6 enum types
        # Always use bitwise AND to check modifiers, even when modifiers is NoModifier (0)
        # In PySide6, Qt.NoModifier is still truthy as an enum object
        try:
            ctrl_pressed = bool(modifiers & QtCore.Qt.ControlModifier)
            shift_pressed = bool(modifiers & QtCore.Qt.ShiftModifier)
        except TypeError:
            # Fallback if modifiers is None or incompatible type
            ctrl_pressed = False
            shift_pressed = False

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
            # Normal click - check if clicking on an already selected item
            # If so, preserve the selection (for drag operations)
            is_already_selected = any(
                w is step_widget for w, _ in self._selected_group_steps
            )
            if is_already_selected and len(self._selected_group_steps) > 1:
                # Keep the multi-selection intact for potential drag
                pass
            else:
                # Clear previous and select this one
                self._clear_group_step_selections()
                step_widget.set_selected(True)
                self._selected_group_steps.append((step_widget, group_widget))

        # Emit signal for info panel update
        step_data = step_widget.get_step_data()
        group_data = group_widget.get_group_data() if group_widget else None
        if step_data:
            self.groupStepClicked.emit(step_data, group_data)

        # Reset the flag after a short delay to allow any pending selection
        # change events to be processed first (Qt may fire itemSelectionChanged
        # after this handler returns)
        QtCore.QTimer.singleShot(0, self._reset_group_step_click_flag)

    def _reset_group_step_click_flag(self):
        """Reset the group step click handling flag."""
        self._handling_group_step_click = False

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

        # Check if this is a referenced group
        is_referenced = group_widget.is_referenced()

        # Get selection count for menu text
        selection_count = len(self._selected_group_steps)
        has_multi_selection = selection_count > 1

        # Create context menu - store as instance variable like main menu
        # Use self (the list widget) as parent to ensure menu stays alive
        self._group_step_menu = QtWidgets.QMenu(self)

        # Edit action - show count if multiple selected
        edit_text = "Edit" if not has_multi_selection else "Edit ({})".format(selection_count)
        edit_action = self._group_step_menu.addAction(edit_text)
        edit_action.setIcon(pyqt.get_icon("mgear_edit"))
        # Disable edit for steps in referenced groups
        edit_action.setEnabled(not is_referenced)

        # Run action - show count if multiple selected
        run_text = "Run" if not has_multi_selection else "Run ({})".format(selection_count)
        run_action = self._group_step_menu.addAction(run_text)
        run_action.setIcon(pyqt.get_icon("mgear_play"))

        self._group_step_menu.addSeparator()

        # Move to top level action - show count if multiple selected
        move_text = "Move to Top Level" if not has_multi_selection else "Move to Top Level ({})".format(selection_count)
        move_out_action = self._group_step_menu.addAction(move_text)
        move_out_action.setIcon(pyqt.get_icon("mgear_arrow-up"))
        # Disable move for steps in referenced groups
        move_out_action.setEnabled(not is_referenced)

        # Remove from group action - show count if multiple selected
        remove_text = "Remove" if not has_multi_selection else "Remove ({})".format(selection_count)
        remove_action = self._group_step_menu.addAction(remove_text)
        remove_action.setIcon(pyqt.get_icon("mgear_trash-2"))
        # Disable remove for steps in referenced groups
        remove_action.setEnabled(not is_referenced)

        # Connect actions - all use selected steps for multi-selection support
        edit_action.triggered.connect(self._edit_selected_group_steps)
        run_action.triggered.connect(self._run_selected_group_steps)
        move_out_action.triggered.connect(self._move_selected_steps_to_top_level)
        remove_action.triggered.connect(self._remove_selected_steps_from_group)

        # Show menu using exec_() which blocks until menu closes
        self._group_step_menu.exec_(global_pos)

    def _edit_group_step(self, step_widget):
        """Edit a step from a group."""
        step_data = step_widget.get_step_data()
        if step_data:
            fullpath = step_data.get_full_path()
            if fullpath:
                CustomStepMixin._editFile(fullpath)

    def _edit_selected_group_steps(self):
        """Edit all selected steps in groups."""
        for step_widget, _ in self._selected_group_steps:
            self._edit_group_step(step_widget)

    def _run_selected_group_steps(self):
        """Run all selected steps in groups."""
        customStepDic = {}
        for step_widget, group_widget in self._selected_group_steps:
            self._run_group_step(step_widget, group_widget, customStepDic)

    def _move_selected_steps_to_top_level(self):
        """Move all selected steps from groups to top level."""
        # Process in reverse order to maintain correct row indices
        # Group by group_widget to handle each group's steps together
        steps_by_group = {}
        for step_widget, group_widget in self._selected_group_steps:
            if group_widget not in steps_by_group:
                steps_by_group[group_widget] = []
            steps_by_group[group_widget].append(step_widget)

        for group_widget, step_widgets in steps_by_group.items():
            group_row = self._find_group_row(group_widget)
            if group_row < 0:
                continue

            # Collect step data and remove from group
            steps_data = []
            for step_widget in step_widgets:
                step_data = step_widget.get_step_data()
                if step_data:
                    steps_data.append(step_data)
                    group_widget.remove_step_widget(step_widget)

            # Update group item height
            self._update_group_item_height(group_row)

            # Add steps to top level after the group (in order)
            for i, step_data in enumerate(steps_data):
                self._insert_step_at_row(group_row + 1 + i, step_data)

        self._clear_group_step_selections()
        self.dataChanged.emit()

    def _remove_selected_steps_from_group(self):
        """Remove all selected steps from their groups."""
        # Group by group_widget to handle each group's steps together
        steps_by_group = {}
        for step_widget, group_widget in self._selected_group_steps:
            if group_widget not in steps_by_group:
                steps_by_group[group_widget] = []
            steps_by_group[group_widget].append(step_widget)

        for group_widget, step_widgets in steps_by_group.items():
            group_row = self._find_group_row(group_widget)
            if group_row < 0:
                continue

            # Remove each step from the group
            for step_widget in step_widgets:
                group_widget.remove_step_widget(step_widget)

            # Update group item height
            self._update_group_item_height(group_row)

        self._clear_group_step_selections()
        self.dataChanged.emit()

    def _run_group_step(self, step_widget, group_widget=None, customStepDic=None):
        """Run a step from a group.

        For referenced groups, tries to load fresh data from the source .scs file.
        Falls back to embedded data if source file is not available.

        Args:
            step_widget (CustomStepItemWidget): The step widget to run
            group_widget (GroupWidget): The parent group widget (optional)
            customStepDic (dict): Dictionary for sharing data between steps (optional)
        """
        if customStepDic is None:
            customStepDic = {}

        step_data = step_widget.get_step_data()
        if not step_data:
            return

        step_path = step_data.path

        # For referenced groups, try to load fresh data from source file
        if group_widget and group_widget.is_referenced():
            source_file = group_widget.get_source_file()
            group_name = group_widget.get_group_data().name
            step_name = step_data.name

            if source_file:
                resolved_source = _resolve_source_path(source_file)
                fresh_step_path = _get_step_path_from_source_file(
                    resolved_source, group_name, step_name
                )
                if fresh_step_path:
                    step_path = fresh_step_path
                    pm.displayInfo(
                        "Running step '{}' from source file: {}".format(
                            step_name, resolved_source
                        )
                    )
                else:
                    pm.displayWarning(
                        "Could not load '{}' from source file, "
                        "using embedded data".format(step_name)
                    )

        runStep(step_path, customStepDic)

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

        # Collect all selected steps from the same group for multi-drag
        selected_in_same_group = [
            (w, g) for w, g in self._selected_group_steps
            if g is group_widget
        ]

        if len(selected_in_same_group) > 1:
            # Multi-selection drag - include all selected steps
            steps_info = []
            for w, g in selected_in_same_group:
                step_data = w.get_step_data()
                steps_info.append({
                    "step": step_data.to_dict() if step_data else {},
                    "step_index": group_widget.get_step_index(w)
                })
            # Sort by index to preserve order
            steps_info.sort(key=lambda x: x["step_index"])

            drag_info = {
                "type": "group_steps_multi",
                "group_row": self._find_group_row(group_widget),
                "steps": steps_info
            }
        else:
            # Single step drag
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
        widget.runRequested.connect(
            lambda it=item: self.groupRunRequested.emit(self.row(it))
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
        widget.runRequested.connect(
            lambda it=item: self.groupRunRequested.emit(self.row(it))
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

        # Don't allow dropping into referenced groups
        if group_widget.is_referenced():
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
        """Handle drop of step(s) dragged from a group.

        Args:
            event: The drop event
        """
        try:
            data = event.mimeData().data("application/x-mgear-customstep")
            drag_info = json.loads(bytes(data).decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            event.ignore()
            return

        drag_type = drag_info.get("type")
        if drag_type == "group_steps_multi":
            self._handle_multi_step_drop(event, drag_info)
        elif drag_type == "group_step":
            self._handle_single_step_drop(event, drag_info)
        else:
            event.ignore()

    def _handle_single_step_drop(self, event, drag_info):
        """Handle drop of a single step from a group.

        Args:
            event: The drop event
            drag_info (dict): Parsed drag information
        """
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

        # Don't allow dragging steps out of referenced groups
        if source_group_widget.is_referenced():
            event.ignore()
            return

        # Determine drop target
        drop_pos = event.pos()
        target_item = self.itemAt(drop_pos)
        target_row = self.row(target_item) if target_item else self.count()

        # Check if dropping onto a group
        if target_item and self._get_item_type(target_item) == self.ITEM_TYPE_GROUP:
            target_group_widget = self.getGroupWidget(target_row)
            # Don't allow dropping into referenced groups
            if target_group_widget and target_group_widget.is_referenced():
                event.ignore()
                return
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

    def _handle_multi_step_drop(self, event, drag_info):
        """Handle drop of multiple steps from a group.

        Args:
            event: The drop event
            drag_info (dict): Parsed drag information with 'steps' list
        """
        source_group_row = drag_info.get("group_row", -1)
        steps_info = drag_info.get("steps", [])

        if source_group_row < 0 or not steps_info:
            event.ignore()
            return

        source_group_widget = self.getGroupWidget(source_group_row)
        if not source_group_widget:
            event.ignore()
            return

        # Don't allow dragging steps out of referenced groups
        if source_group_widget.is_referenced():
            event.ignore()
            return

        # Determine drop target
        drop_pos = event.pos()
        target_item = self.itemAt(drop_pos)
        target_row = self.row(target_item) if target_item else self.count()

        # Check if dropping onto a group
        if target_item and self._get_item_type(target_item) == self.ITEM_TYPE_GROUP:
            target_group_widget = self.getGroupWidget(target_row)
            # Don't allow dropping into referenced groups
            if target_group_widget and target_group_widget.is_referenced():
                event.ignore()
                return
            if target_group_widget and target_group_widget is not source_group_widget:
                # Move steps from one group to another
                # Remove in reverse order to preserve indices
                steps_data = []
                for info in reversed(steps_info):
                    step_data = CustomStepData.from_dict(info["step"])
                    steps_data.insert(0, step_data)
                    source_group_widget.remove_step(info["step_index"])

                # Add all steps to target group
                for step_data in steps_data:
                    target_group_widget.add_step(step_data)

                self._update_group_item_height(source_group_row)
                self._update_group_item_height(target_row)
                event.acceptProposedAction()
                self._clear_group_step_selections()
                self.dataChanged.emit()
                return
            elif target_group_widget is source_group_widget:
                # Reorder within same group
                group_local_pos = target_group_widget.mapFromGlobal(
                    self.mapToGlobal(drop_pos)
                )
                target_index = target_group_widget.get_drop_index_at_pos(group_local_pos)

                # Get sorted indices (already sorted in drag_info)
                step_indices = [info["step_index"] for info in steps_info]

                # Move steps as a block
                source_group_widget.move_steps(step_indices, target_index)
                event.acceptProposedAction()
                self._clear_group_step_selections()
                self.dataChanged.emit()
                return

        # Dropping onto top level (not a group)
        # Remove in reverse order to preserve indices, collect step data
        steps_data = []
        for info in reversed(steps_info):
            step_data = CustomStepData.from_dict(info["step"])
            steps_data.insert(0, step_data)
            source_group_widget.remove_step(info["step_index"])

        self._update_group_item_height(source_group_row)

        # Insert at target position
        if target_row < 0:
            target_row = self.count()

        # Insert all steps at target position
        for i, step_data in enumerate(steps_data):
            self.insertStepItem(target_row + i, step_data)

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
                            widget.runRequested.connect(
                                lambda it=item: self.groupRunRequested.emit(
                                    self.row(it)
                                )
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
        self.preImport_action = self.preMenu.addAction("Import (Replace)")
        self.preImport_action.setIcon(pyqt.get_icon("mgear_log-in"))
        self.preAppend_action = self.preMenu.addAction("Import (Append)")
        self.preAppend_action.setIcon(pyqt.get_icon("mgear_plus"))
        self.preReference_action = self.preMenu.addAction("Reference")
        self.preReference_action.setIcon(pyqt.get_icon("mgear_link"))

        # Post Custom Step menu
        self.postMenu = self.menuBar.addMenu("Post")
        self.postExport_action = self.postMenu.addAction("Export")
        self.postExport_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.postImport_action = self.postMenu.addAction("Import (Replace)")
        self.postImport_action.setIcon(pyqt.get_icon("mgear_log-in"))
        self.postAppend_action = self.postMenu.addAction("Import (Append)")
        self.postAppend_action.setIcon(pyqt.get_icon("mgear_plus"))
        self.postReference_action = self.postMenu.addAction("Reference")
        self.postReference_action.setIcon(pyqt.get_icon("mgear_link"))

        # Utils menu
        self.utilsMenu = self.menuBar.addMenu("Utils")
        self.printConfig_action = self.utilsMenu.addAction("Print Configuration")
        self.printConfig_action.setIcon(pyqt.get_icon("mgear_file-text"))
        self.refreshReferences_action = self.utilsMenu.addAction(
            "Refresh Referenced Groups"
        )
        self.refreshReferences_action.setIcon(pyqt.get_icon("mgear_refresh-cw"))

        # Blueprint menu (actions check if blueprint is enabled before executing)
        self.blueprintMenu = self.menuBar.addMenu("Blueprint")

        # Show blueprint custom steps (view-only)
        # Create QAction with explicit parent to prevent garbage collection
        self.showBlueprintPre_action = QtWidgets.QAction(
            "Show Blueprint Pre Custom Steps", self.blueprintMenu
        )
        self.showBlueprintPre_action.setCheckable(True)
        self.showBlueprintPre_action.setChecked(False)
        self.showBlueprintPre_action.setToolTip(
            "When checked, displays the blueprint's pre custom steps (read-only).\n"
            "Uncheck to return to local custom steps view."
        )
        self.blueprintMenu.addAction(self.showBlueprintPre_action)

        self.showBlueprintPost_action = QtWidgets.QAction(
            "Show Blueprint Post Custom Steps", self.blueprintMenu
        )
        self.showBlueprintPost_action.setCheckable(True)
        self.showBlueprintPost_action.setChecked(False)
        self.showBlueprintPost_action.setToolTip(
            "When checked, displays the blueprint's post custom steps (read-only).\n"
            "Uncheck to return to local custom steps view."
        )
        self.blueprintMenu.addAction(self.showBlueprintPost_action)

        self.blueprintMenu.addSeparator()

        # Make local actions (copy from blueprint to local)
        self.makePreLocal_action = QtWidgets.QAction(
            "Make Pre Custom Steps Local", self.blueprintMenu
        )
        self.makePreLocal_action.setToolTip(
            "Copy the blueprint's pre custom steps configuration to local,\n"
            "overriding the current local configuration."
        )
        self.blueprintMenu.addAction(self.makePreLocal_action)

        self.makePostLocal_action = QtWidgets.QAction(
            "Make Post Custom Steps Local", self.blueprintMenu
        )
        self.makePostLocal_action.setToolTip(
            "Copy the blueprint's post custom steps configuration to local,\n"
            "overriding the current local configuration."
        )
        self.blueprintMenu.addAction(self.makePostLocal_action)

        self.mainLayout.setMenuBar(self.menuBar)

        # =============================================
        # Pre Custom Step collapsible section
        # =============================================
        # Override checkbox for Pre Custom Steps
        self.override_preCustomSteps_checkBox = QtWidgets.QCheckBox(Form)
        self.override_preCustomSteps_checkBox.setObjectName("override_preCustomSteps_checkBox")
        self.override_preCustomSteps_checkBox.setText("Local Override: Pre Custom Steps")
        self.override_preCustomSteps_checkBox.setChecked(False)  # Default to inherit from blueprint
        self.mainLayout.addWidget(self.override_preCustomSteps_checkBox)

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
        # Override checkbox for Post Custom Steps
        self.override_postCustomSteps_checkBox = QtWidgets.QCheckBox(Form)
        self.override_postCustomSteps_checkBox.setObjectName("override_postCustomSteps_checkBox")
        self.override_postCustomSteps_checkBox.setText("Local Override: Post Custom Steps")
        self.override_postCustomSteps_checkBox.setChecked(False)  # Default to inherit from blueprint
        self.mainLayout.addWidget(self.override_postCustomSteps_checkBox)

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
        self.infoCollapsible = CollapsibleWidget(
            "Step Info", expanded=True, expandable=False
        )
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

        self.info_referenced_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Referenced:", self.info_referenced_label)

        self.info_exists_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Exists:", self.info_exists_label)

        self.info_modified_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Modified:", self.info_modified_label)

        self.infoCollapsible.addWidget(infoWidget)

        # Path section with form layout for better organization
        pathWidget = QtWidgets.QWidget()
        pathLayout = QtWidgets.QFormLayout(pathWidget)
        pathLayout.setContentsMargins(4, 0, 4, 2)
        pathLayout.setSpacing(4)
        pathLayout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )

        self.info_path_type_label = QtWidgets.QLabel("-")
        pathLayout.addRow("Path Type:", self.info_path_type_label)

        self.info_path_label = QtWidgets.QLabel("-")
        self.info_path_label.setWordWrap(True)
        self.info_path_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.info_path_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        pathLayout.addRow("Path:", self.info_path_label)

        # Source file (for referenced groups)
        self.info_source_label = QtWidgets.QLabel("-")
        self.info_source_label.setWordWrap(True)
        self.info_source_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.info_source_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        pathLayout.addRow("Source:", self.info_source_label)

        # Resolved path (full path when source is relative)
        self.info_resolved_label = QtWidgets.QLabel("-")
        self.info_resolved_label.setWordWrap(True)
        self.info_resolved_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.info_resolved_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        pathLayout.addRow("Resolved:", self.info_resolved_label)

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


# ============================================================================
# Group Selection Dialog
# ============================================================================


class GroupSelectionDialog(QtWidgets.QDialog):
    """Dialog for selecting groups to reference from a .scs file.

    Shows a list of groups from the file and allows the user to select
    which ones to reference.
    """

    def __init__(self, groups, source_file, parent=None):
        """Initialize the dialog.

        Args:
            groups (list): List of GroupData objects to choose from
            source_file (str): Path to the source .scs file
            parent (QWidget): Parent widget
        """
        super(GroupSelectionDialog, self).__init__(parent)
        self._groups = groups
        self._source_file = source_file
        self._selected_groups = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select Groups to Reference")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QtWidgets.QVBoxLayout(self)

        # Info label
        info_label = QtWidgets.QLabel(
            "Select the groups you want to reference from:\n{}".format(
                os.path.basename(self._source_file)
            )
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Group list with checkboxes
        self._list_widget = QtWidgets.QListWidget()
        self._list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.NoSelection
        )
        for group in self._groups:
            item = QtWidgets.QListWidgetItem()
            checkbox = QtWidgets.QCheckBox(
                "{} ({} steps)".format(group.name, len(group.items))
            )
            checkbox.setChecked(True)  # Default to selected
            item.setSizeHint(checkbox.sizeHint())
            self._list_widget.addItem(item)
            self._list_widget.setItemWidget(item, checkbox)
        layout.addWidget(self._list_widget)

        # Select all / None buttons
        btn_layout = QtWidgets.QHBoxLayout()
        select_all_btn = QtWidgets.QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        select_none_btn = QtWidgets.QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(select_none_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _select_all(self):
        """Select all groups."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            checkbox = self._list_widget.itemWidget(item)
            checkbox.setChecked(True)

    def _select_none(self):
        """Deselect all groups."""
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            checkbox = self._list_widget.itemWidget(item)
            checkbox.setChecked(False)

    def _on_accept(self):
        """Handle accept - collect selected groups."""
        self._selected_groups = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            checkbox = self._list_widget.itemWidget(item)
            if checkbox.isChecked():
                self._selected_groups.append(self._groups[i])
        self.accept()

    def get_selected_groups(self):
        """Get the list of selected groups.

        Returns:
            list: List of selected GroupData objects
        """
        return self._selected_groups


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

    def print_configuration(self):
        """Print the custom step configuration as formatted JSON."""
        pre_data = self.root.attr("preCustomStep").get()
        post_data = self.root.attr("postCustomStep").get()

        print("\n" + "=" * 60)
        print("CUSTOM STEP CONFIGURATION")
        print("=" * 60)

        print("\n--- Pre Custom Steps ---")
        if pre_data:
            try:
                # Try parsing as JSON
                if pre_data.strip().startswith("{"):
                    parsed = json.loads(pre_data)
                    print(json.dumps(parsed, indent=2))
                else:
                    # Legacy format
                    print("(Legacy format)")
                    print(pre_data)
            except (json.JSONDecodeError, ValueError):
                print(pre_data)
        else:
            print("(empty)")

        print("\n--- Post Custom Steps ---")
        if post_data:
            try:
                # Try parsing as JSON
                if post_data.strip().startswith("{"):
                    parsed = json.loads(post_data)
                    print(json.dumps(parsed, indent=2))
                else:
                    # Legacy format
                    print("(Legacy format)")
                    print(post_data)
            except (json.JSONDecodeError, ValueError):
                print(post_data)
        else:
            print("(empty)")

        print("\n" + "=" * 60)

    def shared_owner(self, fullpath):
        """Get the shared folder name that owns a step file.

        Args:
            fullpath (str): Full path to the step file

        Returns:
            str: Name of the shared folder (e.g., "_shared"), or empty string if not shared
        """
        # Normalize path separators
        normalized = fullpath.replace("\\", "/")
        # Look for _shared folder in the path
        parts = normalized.split("/")
        for part in parts:
            if part.startswith("_shared"):
                return part
        return ""

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
        csTap.preAppend_action.triggered.connect(self.appendCustomStep)
        csTap.preReference_action.triggered.connect(self.referenceCustomStep)
        csTap.postExport_action.triggered.connect(
            partial(self.exportCustomStep, False)
        )
        csTap.postImport_action.triggered.connect(
            partial(self.importCustomStep, False)
        )
        csTap.postAppend_action.triggered.connect(
            partial(self.appendCustomStep, False)
        )
        csTap.postReference_action.triggered.connect(
            partial(self.referenceCustomStep, False)
        )
        csTap.printConfig_action.triggered.connect(self.print_configuration)
        csTap.refreshReferences_action.triggered.connect(
            self.refreshReferencedGroups
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

        # Group run signals (from group header run buttons)
        csTap.preCustomStep_listWidget.groupRunRequested.connect(
            partial(self._onGroupRunRequested, pre=True)
        )
        csTap.postCustomStep_listWidget.groupRunRequested.connect(
            partial(self._onGroupRunRequested, pre=False)
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
            partial(self._onGroupStepClicked, pre=True)
        )
        csTap.postCustomStep_listWidget.groupStepClicked.connect(
            partial(self._onGroupStepClicked, pre=False)
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

    def _onGroupRunRequested(self, row, pre=True):
        """Handle run request for a group - runs all active steps in the group.

        Args:
            row (int): Row index of the group
            pre (bool): Whether this is a pre or post group
        """
        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        group_data = stepWidget.getGroupData(row)
        if not group_data:
            return

        # Only run if group is active
        if not group_data.active:
            pm.displayWarning("Group '{}' is deactivated, skipping.".format(
                group_data.name
            ))
            return

        # Run all active steps in the group
        customStepDic = {}
        steps_run = 0
        for step_data in group_data.items:
            if step_data.active:
                self.runStep(step_data.path, customStepDic)
                steps_run += 1

        pm.displayInfo("Ran {} steps from group '{}'".format(
            steps_run, group_data.name
        ))

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

        # Skip if we're handling a group step click - the groupStepClicked
        # signal handler will update the info panel instead
        if stepWidget._handling_group_step_click:
            return

        row = stepWidget.row(item)

        # Check if this is a group row
        if stepWidget.isGroupRow(row):
            group_data = stepWidget.getGroupData(row)
            if group_data:
                self._updateInfoPanelFromGroupData(group_data, pre)
            return

        step_data = stepWidget.getStepData(row)

        if not step_data:
            return

        self._updateInfoPanelFromData(step_data, pre)

    def _onGroupStepClicked(self, step_data, group_data, pre=True):
        """Handle click on a step inside a group for info panel update.

        Args:
            step_data (CustomStepData): The step data
            group_data (GroupData): The parent group data
            pre (bool): Whether this is a pre or post step
        """
        self._updateInfoPanelFromData(step_data, pre, group_data)

    def _updateInfoPanelFromData(self, step_data, pre=True, group_data=None):
        """Update the info panel from step data directly.

        Args:
            step_data (CustomStepData): The step data to display
            pre (bool): Whether this is a pre or post step
            group_data (GroupData): Optional group data if step is in a referenced group
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

        # Check referenced status (from parent group)
        if group_data and group_data.referenced:
            cs_referenced = "Yes"
            cs_source = group_data.source_file if group_data.source_file else "-"
        else:
            cs_referenced = "No"
            cs_source = "-"

        # Path info - show stored path and resolved full path
        cs_path = step_data.path if step_data.path else "-"  # The stored path (relative or absolute)
        cs_resolved = cs_fullpath if cs_fullpath else "-"  # The full resolved path (same as Edit button uses)

        # Determine path type (relative to env var or absolute)
        env_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        if os.path.isabs(cs_path):
            cs_path_type = "Absolute"
        elif env_path:
            cs_path_type = "Relative (MGEAR_SHIFTER_CUSTOMSTEP_PATH)"
        else:
            cs_path_type = "Relative"

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
        csTap.info_referenced_label.setText(cs_referenced)
        csTap.info_exists_label.setText(cs_exists)
        csTap.info_modified_label.setText(cs_modified)

        # Update path section labels
        csTap.info_path_type_label.setText(cs_path_type)
        csTap.info_path_label.setText(cs_path)
        csTap.info_source_label.setText(cs_source)
        csTap.info_resolved_label.setText(cs_resolved)

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

        # Color code referenced status
        if cs_referenced == "Yes":
            csTap.info_referenced_label.setStyleSheet("color: #5A8A6A;")
        else:
            csTap.info_referenced_label.setStyleSheet("")

    def _updateInfoPanelFromGroupData(self, group_data, pre=True):
        """Update the info panel from group data directly.

        Args:
            group_data (GroupData): The group data to display
            pre (bool): Whether this is a pre or post group
        """
        if not group_data:
            return

        csTap = self.customStepTab

        # Get group info from data model
        cs_name = group_data.name
        cs_status = "Active" if group_data.active else "Deactivated"
        cs_type = "Pre Custom Step Group" if pre else "Post Custom Step Group"
        cs_type += " ({} items)".format(len(group_data.items))

        # Groups are not shared
        cs_shared = "-"

        # Check referenced status
        if group_data.referenced:
            cs_referenced = "Yes"
            cs_source = group_data.source_file if group_data.source_file else "-"
            # Compute resolved path for source file using helper function
            if cs_source != "-":
                cs_resolved = _resolve_source_path(cs_source)
                # Determine path type
                env_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
                if os.path.isabs(cs_source):
                    cs_path_type = "Absolute"
                elif env_path:
                    cs_path_type = "Relative (MGEAR_SHIFTER_CUSTOMSTEP_PATH)"
                else:
                    cs_path_type = "Relative"
            else:
                cs_resolved = "-"
                cs_path_type = "-"
        else:
            cs_referenced = "No"
            cs_source = "-"
            cs_resolved = "-"
            cs_path_type = "-"

        # For referenced groups, show source file info
        # For non-referenced groups, path fields are not applicable
        if group_data.referenced:
            cs_path = cs_source  # Path shows the stored source path
            # Check if source file exists
            if cs_resolved != "-" and os.path.exists(cs_resolved):
                cs_exists = "Yes"
                try:
                    mtime = os.path.getmtime(cs_resolved)
                    cs_modified = datetime.datetime.fromtimestamp(mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    cs_modified = "Unknown"
            else:
                cs_exists = "No (File not found)" if cs_source != "-" else "-"
                cs_modified = "-"
        else:
            cs_path = "-"
            cs_exists = "-"
            cs_modified = "-"

        # Update labels
        csTap.info_name_label.setText(cs_name)
        csTap.info_type_label.setText(cs_type)
        csTap.info_status_label.setText(cs_status)
        csTap.info_shared_label.setText(cs_shared)
        csTap.info_referenced_label.setText(cs_referenced)
        csTap.info_exists_label.setText(cs_exists)
        csTap.info_modified_label.setText(cs_modified)

        # Update path section labels
        csTap.info_path_type_label.setText(cs_path_type)
        csTap.info_path_label.setText(cs_path)
        csTap.info_source_label.setText("-")  # Source not applicable for groups
        csTap.info_resolved_label.setText(cs_resolved)

        # Color code the status
        if cs_status == "Active":
            csTap.info_status_label.setStyleSheet("color: #00A000;")
        else:
            csTap.info_status_label.setStyleSheet("color: #B40000;")

        # Color code file existence (for referenced groups)
        if cs_exists == "Yes":
            csTap.info_exists_label.setStyleSheet("color: #00A000;")
        elif cs_exists.startswith("No"):
            csTap.info_exists_label.setStyleSheet("color: #B40000;")
        else:
            csTap.info_exists_label.setStyleSheet("")

        # Color code referenced status
        if cs_referenced == "Yes":
            csTap.info_referenced_label.setStyleSheet("color: #5A8A6A;")
        else:
            csTap.info_referenced_label.setStyleSheet("")

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
        """Run selected custom steps and groups manually."""
        selItems = widgetList.selectedItems()
        customStepDic = {}
        for item in selItems:
            row = widgetList.row(item)
            # Check if this is a group
            if widgetList.isGroupRow(row):
                group_data = widgetList.getGroupData(row)
                if group_data and group_data.active:
                    # Run all active steps in the group
                    for step_data in group_data.items:
                        if step_data.active:
                            self.runStep(step_data.path, customStepDic)
            else:
                # Regular step
                step_data = widgetList.getStepData(row)
                if step_data:
                    self.runStep(step_data.path, customStepDic)

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
        """Export custom steps configuration to a JSON file (.scs).

        Exports the current step/group configuration in the internal JSON format.

        Args:
            pre: If True, exports from pre step list; otherwise from post
        """
        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Get the JSON configuration from the widget
        json_config = stepWidget.toJson()
        if not json_config or json_config == "":
            pm.displayWarning("No custom steps to export.")
            return

        # Parse and re-serialize with nice formatting
        try:
            config_dict = json.loads(json_config)
        except json.JSONDecodeError:
            pm.displayWarning("Invalid configuration data.")
            return

        data_string = json.dumps(config_dict, indent=4)

        # Get starting directory for file dialog
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = pm.workspace(q=True, rootDirectory=True)

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            fileFilter="Shifter Custom Steps .scs (*.scs)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        # Ensure .scs extension
        if not filePath.lower().endswith(".scs"):
            filePath += ".scs"

        with open(filePath, "w") as f:
            f.write(data_string)

        pm.displayInfo("Custom steps exported to: {}".format(filePath))

    def importCustomStep(self, pre=True, *args):
        """Import custom steps configuration from a JSON file (.scs).

        Replaces the current step/group configuration with the imported one.

        Args:
            pre: If True, imports to pre step list; otherwise to post
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        # Get starting directory for file dialog
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = pm.workspace(q=True, rootDirectory=True)

        filePath = pm.fileDialog2(
            fileMode=1,
            startingDirectory=startDir,
            fileFilter="Shifter Custom Steps .scs (*.scs)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        # Load the JSON configuration
        try:
            with open(filePath, "r") as f:
                config_dict = json.load(f)
        except json.JSONDecodeError as e:
            pm.displayError("Invalid JSON file: {}".format(str(e)))
            return
        except IOError as e:
            pm.displayError("Could not read file: {}".format(str(e)))
            return

        # Validate the configuration format
        if not isinstance(config_dict, dict):
            pm.displayError("Invalid configuration format.")
            return

        # Check if it's a version 2 format or needs conversion
        if config_dict.get("version") != 2:
            pm.displayError(
                "Unsupported configuration version. Expected version 2."
            )
            return

        # Load from JSON (loadFromJson handles clearing internally)
        json_string = json.dumps(config_dict)
        stepWidget.loadFromJson(json_string)

        # Update the Maya attribute
        self._updateStepListAttr(stepWidget, stepAttr)

        pm.displayInfo("Custom steps imported from: {}".format(filePath))

    def _loadScsFile(self, filePath=None):
        """Load and validate a .scs configuration file.

        Args:
            filePath (str): Path to the .scs file, or None to show file dialog

        Returns:
            tuple: (config_dict, filePath) or (None, None) if failed
        """
        if not filePath:
            # Get starting directory for file dialog
            if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            else:
                startDir = pm.workspace(q=True, rootDirectory=True)

            filePath = pm.fileDialog2(
                fileMode=1,
                startingDirectory=startDir,
                fileFilter="Shifter Custom Steps .scs (*.scs)",
            )
            if not filePath:
                return None, None
            if not isinstance(filePath, string_types):
                filePath = filePath[0]

        # Load the JSON configuration
        try:
            with open(filePath, "r") as f:
                config_dict = json.load(f)
        except json.JSONDecodeError as e:
            pm.displayError("Invalid JSON file: {}".format(str(e)))
            return None, None
        except IOError as e:
            pm.displayError("Could not read file: {}".format(str(e)))
            return None, None

        # Validate the configuration format
        if not isinstance(config_dict, dict):
            pm.displayError("Invalid configuration format.")
            return None, None

        # Check if it's a version 2 format
        if config_dict.get("version") != 2:
            pm.displayError(
                "Unsupported configuration version. Expected version 2."
            )
            return None, None

        return config_dict, filePath

    def appendCustomStep(self, pre=True, *args):
        """Import custom steps and append to existing configuration.

        Unlike importCustomStep which replaces, this adds imported items
        to the end of the current step/group list.

        Args:
            pre: If True, appends to pre step list; otherwise to post
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        config_dict, filePath = self._loadScsFile()
        if config_dict is None:
            return

        # Parse items from the imported configuration
        items = config_dict.get("items", [])
        if not items:
            pm.displayWarning("No items found in the configuration file.")
            return

        # Add each item to the existing list
        count = 0
        for item_data in items:
            item_type = item_data.get("type")
            if item_type == "step":
                step_data = CustomStepData.from_dict(item_data)
                stepWidget.addStepItem(step_data)
                count += 1
            elif item_type == "group":
                group_data = GroupData.from_dict(item_data)
                stepWidget.addGroupItem(group_data)
                count += 1

        # Update the Maya attribute
        self._updateStepListAttr(stepWidget, stepAttr)

        pm.displayInfo(
            "Appended {} items from: {}".format(count, filePath)
        )

    def referenceCustomStep(self, pre=True, *args):
        """Reference groups from another .scs configuration file.

        Referenced groups are read-only and can be moved but not edited.
        Only groups can be referenced; standalone steps are ignored.

        Args:
            pre: If True, adds to pre step list; otherwise to post
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        config_dict, filePath = self._loadScsFile()
        if config_dict is None:
            return

        # Extract only groups from the configuration
        items = config_dict.get("items", [])
        groups = []
        for item_data in items:
            if item_data.get("type") == "group":
                group_data = GroupData.from_dict(item_data)
                groups.append(group_data)

        if not groups:
            pm.displayWarning(
                "No groups found in the configuration file. "
                "Only groups can be referenced."
            )
            return

        # If only one group, reference it directly
        if len(groups) == 1:
            selected_groups = groups
        else:
            # Show selection dialog
            dialog = GroupSelectionDialog(groups, filePath, parent=pyqt.maya_main_window())
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            selected_groups = dialog.get_selected_groups()

        if not selected_groups:
            pm.displayWarning("No groups selected.")
            return

        # Compute relative path from MGEAR_SHIFTER_CUSTOMSTEP_PATH if set
        source_path = filePath
        env_path = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        if env_path:
            # Normalize paths for comparison
            norm_file = os.path.normpath(filePath).lower()
            norm_env = os.path.normpath(env_path).lower()
            if norm_file.startswith(norm_env):
                # Store relative path
                source_path = os.path.relpath(filePath, env_path)

        # Add selected groups as referenced
        count = 0
        for group in selected_groups:
            # Mark as referenced and set source file (relative if possible)
            group.referenced = True
            group.source_file = source_path
            stepWidget.addGroupItem(group)
            count += 1

        # Update the Maya attribute
        self._updateStepListAttr(stepWidget, stepAttr)

        pm.displayInfo(
            "Referenced {} groups from: {}".format(count, filePath)
        )

    def refreshReferencedGroups(self):
        """Refresh all referenced groups from their source .scs files.

        Updates the embedded step data in referenced groups by re-reading
        their source .scs files. This affects both pre and post custom steps.
        """
        csTap = self.customStepTab
        pre_widget = csTap.preCustomStep_listWidget
        post_widget = csTap.postCustomStep_listWidget

        total_refreshed = 0
        total_failed = 0

        # Refresh pre custom step referenced groups
        pre_refreshed, pre_failed = self._refreshReferencedGroupsInWidget(
            pre_widget, "preCustomStep"
        )
        total_refreshed += pre_refreshed
        total_failed += pre_failed

        # Refresh post custom step referenced groups
        post_refreshed, post_failed = self._refreshReferencedGroupsInWidget(
            post_widget, "postCustomStep"
        )
        total_refreshed += post_refreshed
        total_failed += post_failed

        if total_refreshed > 0 or total_failed > 0:
            if total_failed == 0:
                pm.displayInfo(
                    "Refreshed {} referenced group(s) successfully.".format(
                        total_refreshed
                    )
                )
            else:
                pm.displayWarning(
                    "Refreshed {} group(s), {} failed to refresh.".format(
                        total_refreshed, total_failed
                    )
                )
        else:
            pm.displayInfo("No referenced groups found to refresh.")

    def _refreshReferencedGroupsInWidget(self, stepWidget, stepAttr):
        """Refresh referenced groups in a step widget.

        Args:
            stepWidget: The CustomStepListWidget to refresh
            stepAttr (str): The Maya attribute name ('preCustomStep' or 'postCustomStep')

        Returns:
            tuple: (number of groups refreshed, number of failures)
        """
        refreshed = 0
        failed = 0
        changed = False

        # Iterate through all items to find referenced groups
        for row in range(stepWidget.count()):
            if not stepWidget.isGroupRow(row):
                continue

            group_widget = stepWidget.getGroupWidget(row)
            if not group_widget or not group_widget.is_referenced():
                continue

            group_data = group_widget.get_group_data()
            source_file = group_data.source_file
            group_name = group_data.name

            if not source_file:
                failed += 1
                pm.displayWarning(
                    "Group '{}' has no source file path.".format(group_name)
                )
                continue

            # Resolve the source file path
            resolved_source = _resolve_source_path(source_file)

            if not os.path.exists(resolved_source):
                failed += 1
                pm.displayWarning(
                    "Source file not found for group '{}': {}".format(
                        group_name, resolved_source
                    )
                )
                continue

            # Load fresh data from source file
            try:
                with open(resolved_source, "r") as f:
                    config_dict = json.load(f)

                # Find the matching group in the source file
                source_group_data = None
                for item_data in config_dict.get("items", []):
                    if item_data.get("type") == "group":
                        if item_data.get("name") == group_name:
                            source_group_data = GroupData.from_dict(item_data)
                            break

                if not source_group_data:
                    failed += 1
                    pm.displayWarning(
                        "Group '{}' not found in source file: {}".format(
                            group_name, resolved_source
                        )
                    )
                    continue

                # Update the group's items with fresh data
                group_data._items = source_group_data.items

                # Update the group widget to reflect the new items
                group_widget._refresh_step_widgets()

                refreshed += 1
                changed = True
                pm.displayInfo(
                    "Refreshed group '{}' from: {}".format(
                        group_name, resolved_source
                    )
                )

            except json.JSONDecodeError as e:
                failed += 1
                pm.displayWarning(
                    "JSON error in source file {}: {}".format(resolved_source, str(e))
                )
            except Exception as e:
                failed += 1
                pm.displayWarning(
                    "Error refreshing group '{}': {}".format(group_name, str(e))
                )

        # Update the Maya attribute if any changes were made
        if changed:
            self._updateStepListAttr(stepWidget, stepAttr)

        return refreshed, failed

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
        selectionCount = len(selectedItems)

        isClickedGroup = clickedRow >= 0 and cs_listWidget.isGroupRow(clickedRow)
        isClickedReferenced = False
        if isClickedGroup:
            clicked_group_widget = cs_listWidget.getGroupWidget(clickedRow)
            if clicked_group_widget:
                isClickedReferenced = clicked_group_widget.is_referenced()

        # Count steps and groups separately
        stepCount = 0
        groupCount = 0
        if hasSelection:
            for item in selectedItems:
                row = cs_listWidget.row(item)
                if cs_listWidget.isGroupRow(row):
                    groupCount += 1
                else:
                    stepCount += 1

        hasStepSelection = stepCount > 0
        hasMultiSelection = selectionCount > 1

        # Run Selected - works on both steps and groups
        run_text = "Run Selected" if not hasMultiSelection else "Run Selected ({})".format(selectionCount)
        run_action = self.csMenu.addAction(run_text)
        run_action.setIcon(pyqt.get_icon("mgear_play"))
        run_action.setEnabled(hasSelection)

        # Edit - only for steps (not groups)
        edit_text = "Edit" if stepCount <= 1 else "Edit ({})".format(stepCount)
        edit_action = self.csMenu.addAction(edit_text)
        edit_action.setIcon(pyqt.get_icon("mgear_edit"))
        edit_action.setEnabled(hasStepSelection and not isClickedGroup)

        # Duplicate - only for steps (not groups)
        duplicate_text = "Duplicate" if stepCount <= 1 else "Duplicate ({})".format(stepCount)
        duplicate_action = self.csMenu.addAction(duplicate_text)
        duplicate_action.setIcon(pyqt.get_icon("mgear_copy"))
        duplicate_action.setEnabled(hasStepSelection and not isClickedGroup)

        # Remove - only for steps (not groups)
        remove_text = "Remove" if stepCount <= 1 else "Remove ({})".format(stepCount)
        remove_action = self.csMenu.addAction(remove_text)
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
            # Disable rename for referenced groups
            rename_group_action.setEnabled(not isClickedReferenced)

            ungroup_action = self.csMenu.addAction("Ungroup (Keep Items)")
            ungroup_action.setIcon(pyqt.get_icon("mgear_minimize-2"))
            # Disable ungroup for referenced groups
            ungroup_action.setEnabled(not isClickedReferenced)

            delete_group_action = self.csMenu.addAction("Delete Group...")
            delete_group_action.setIcon(pyqt.get_icon("mgear_trash-2"))

        self.csMenu.addSeparator()

        # Toggle status actions
        toggle_text = "Toggle Status" if not hasMultiSelection else "Toggle Status ({})".format(selectionCount)
        toggle_action = self.csMenu.addAction(toggle_text)
        toggle_action.setIcon(pyqt.get_icon("mgear_refresh-cw"))
        toggle_action.setEnabled(hasSelection)

        off_selected_text = "Turn OFF Selected" if not hasMultiSelection else "Turn OFF Selected ({})".format(selectionCount)
        off_selected_action = self.csMenu.addAction(off_selected_text)
        off_selected_action.setIcon(pyqt.get_icon("mgear_toggle-left"))
        off_selected_action.setEnabled(hasSelection)

        on_selected_text = "Turn ON Selected" if not hasMultiSelection else "Turn ON Selected ({})".format(selectionCount)
        on_selected_action = self.csMenu.addAction(on_selected_text)
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
