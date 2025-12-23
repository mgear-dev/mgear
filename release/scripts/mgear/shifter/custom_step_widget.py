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

    def __repr__(self):
        return "CustomStepData(name={!r}, path={!r}, active={!r})".format(
            self._name, self._path, self._active
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
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
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
        if self._selected:
            bg_color = self.SELECTED_COLOR
            border_color = self.SELECTED_BORDER_COLOR
        elif not self._step_data.active:
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


class CustomStepListWidget(QtWidgets.QListWidget):
    """QListWidget that displays custom step widgets with drag-drop support.

    This widget manages CustomStepItemWidget instances and provides:
    - External file drops (.py files)
    - Internal drag-drop reordering
    - Item widget management

    Signals:
        filesDropped: Emitted when .py files are dropped from external sources
        stepToggled: Emitted when a step's active state changes (row, active)
        stepEditRequested: Emitted when edit is requested for a step (row)
        stepRunRequested: Emitted when run is requested for a step (row)
        orderChanged: Emitted when items are reordered
    """

    filesDropped = QtCore.Signal(list)
    stepToggled = QtCore.Signal(int, bool)
    stepEditRequested = QtCore.Signal(int)
    stepRunRequested = QtCore.Signal(int)
    orderChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(CustomStepListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(False)

        # Track widgets for proper cleanup
        self._item_widgets = {}

        # Connect selection changed signal
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Handle selection change and update widget appearances."""
        # Get selected rows as a set (rows are hashable, items are not in PySide6)
        selected_rows = set(self.row(item) for item in self.selectedItems())
        for i in range(self.count()):
            widget = self.getStepWidget(i)
            if widget and hasattr(widget, 'set_selected'):
                widget.set_selected(i in selected_rows)

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

        # Store the data string in the item for compatibility
        item.setData(QtCore.Qt.UserRole, step_data.to_string())

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

    def _on_step_toggled(self, item, active):
        """Handle step toggle event."""
        widget = self.itemWidget(item)
        if widget:
            # Update the stored data
            item.setData(QtCore.Qt.UserRole, widget.to_string())
            self.stepToggled.emit(self.row(item), active)

    def _on_edit_requested(self, item):
        """Handle edit request event."""
        self.stepEditRequested.emit(self.row(item))

    def _on_run_requested(self, item):
        """Handle run request event."""
        self.stepRunRequested.emit(self.row(item))

    def getStepWidget(self, row):
        """Get the CustomStepItemWidget for a given row.

        Args:
            row (int): Row index

        Returns:
            CustomStepItemWidget or None: The widget at the row
        """
        item = self.item(row)
        if item:
            return self.itemWidget(item)
        return None

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

    def getAllStepData(self):
        """Get all step data as a list.

        Returns:
            list: List of CustomStepData objects
        """
        result = []
        for i in range(self.count()):
            data = self.getStepData(i)
            if data:
                result.append(data)
        return result

    def getStepStrings(self):
        """Get all step data as strings (for storage).

        Returns:
            list: List of step strings in storage format
        """
        result = []
        for i in range(self.count()):
            widget = self.getStepWidget(i)
            if widget:
                result.append(widget.to_string())
        return result

    def setStepActive(self, row, active):
        """Set the active state of a step.

        Args:
            row (int): Row index
            active (bool): New active state
        """
        widget = self.getStepWidget(row)
        if widget:
            widget.set_active(active)
            item = self.item(row)
            if item:
                item.setData(QtCore.Qt.UserRole, widget.to_string())

    def toggleStepActive(self, row):
        """Toggle the active state of a step.

        Args:
            row (int): Row index
        """
        widget = self.getStepWidget(row)
        if widget:
            widget.set_active(not widget.is_active())
            item = self.item(row)
            if item:
                item.setData(QtCore.Qt.UserRole, widget.to_string())

    def highlightSearch(self, search_text):
        """Highlight items matching the search text.

        Args:
            search_text (str): Text to search for
        """
        search_lower = search_text.lower() if search_text else ""
        for i in range(self.count()):
            widget = self.getStepWidget(i)
            if widget:
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
        if event.mimeData().hasUrls():
            # Check if any URL is a .py file
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".py"):
                    event.acceptProposedAction()
                    return
        # Fall back to default behavior for internal moves
        super(CustomStepListWidget, self).dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(".py"):
                    event.acceptProposedAction()
                    return
        super(CustomStepListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
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
            # Let the base class handle the move
            super(CustomStepListWidget, self).dropEvent(event)

            # Reassign widgets after move (they get detached during move)
            self._reassign_widgets()
            self.orderChanged.emit()
        else:
            super(CustomStepListWidget, self).dropEvent(event)

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
                    # Get stored data and recreate widget
                    data_string = item.data(QtCore.Qt.UserRole)
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
        for item in self.root.attr("preCustomStep").get().split(","):
            self.customStepTab.preCustomStep_listWidget.addStepItem(item)

        self.populateCheck(
            self.customStepTab.postCustomStep_checkBox, "doPostCustomStep"
        )
        for item in self.root.attr("postCustomStep").get().split(","):
            self.customStepTab.postCustomStep_listWidget.addStepItem(item)

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
        step_strings = stepWidget.getStepStrings()
        new_value = ",".join(step_strings)
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
        self.csMenu = QtWidgets.QMenu()
        parentPosition = cs_listWidget.mapToGlobal(QtCore.QPoint(0, 0))

        # Add/New actions (always available)
        add_action = self.csMenu.addAction("Add")
        add_action.setIcon(pyqt.get_icon("mgear_folder-plus"))
        new_action = self.csMenu.addAction("New")
        new_action.setIcon(pyqt.get_icon("mgear_file-plus"))

        self.csMenu.addSeparator()

        # Selection-dependent actions
        hasSelection = len(cs_listWidget.selectedItems()) > 0

        run_action = self.csMenu.addAction("Run Selected")
        run_action.setIcon(pyqt.get_icon("mgear_play"))
        run_action.setEnabled(hasSelection)

        edit_action = self.csMenu.addAction("Edit")
        edit_action.setIcon(pyqt.get_icon("mgear_edit"))
        edit_action.setEnabled(hasSelection)

        duplicate_action = self.csMenu.addAction("Duplicate")
        duplicate_action.setIcon(pyqt.get_icon("mgear_copy"))
        duplicate_action.setEnabled(hasSelection)

        remove_action = self.csMenu.addAction("Remove")
        remove_action.setIcon(pyqt.get_icon("mgear_trash-2"))
        remove_action.setEnabled(hasSelection)

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


# Backwards compatibility alias
customStepTab = CustomStepTab

# Module-level function for external access (used by shifter build process)
runStep = CustomStepMixin.runStep
