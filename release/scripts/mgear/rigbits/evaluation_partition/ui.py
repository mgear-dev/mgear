"""Evaluation Partition Tool - Main UI Module.

Provides the main dialog window for the Evaluation Partition tool.
"""

from mgear.vendor.Qt import QtWidgets, QtCore, QtGui

from mgear.core import pyqt

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from . import core
from .widgets import GroupListWidget


class EvaluationPartitionUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for Evaluation Partition Tool.

    A dockable dialog for creating and managing polygon groups on a mesh,
    visualized with colored shaders for improved parallel evaluation planning.
    """

    TOOL_NAME = "EvaluationPartition"
    TOOL_TITLE = "Evaluation Partition Tool"

    def __init__(self, parent=None):
        super(EvaluationPartitionUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        # State
        self.group_manager = None

        # Window setup
        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumWidth(350)

        # Platform-specific window flags
        if cmds.about(ntOS=True):
            flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        # Build UI
        self.setup_ui()

        # User settings definition
        self.user_settings = {}
        self.load_settings()

        # Set default size
        self.resize(380, 500)

    # =========================================================
    # UI SETUP METHODS
    # =========================================================

    def setup_ui(self):
        """Main UI setup - calls all UI construction methods in order."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.set_initial_state()

    def create_actions(self):
        """Create QActions for menus."""
        # File menu actions
        self.export_action = QtWidgets.QAction("Export Configuration...", self)
        self.export_action.setShortcut(QtGui.QKeySequence.Save)
        self.export_action.setToolTip("Export partition configuration to .evp file")

        self.import_action = QtWidgets.QAction("Import Configuration...", self)
        self.import_action.setShortcut(QtGui.QKeySequence.Open)
        self.import_action.setToolTip("Import partition configuration from .evp file")

    def create_widgets(self):
        """Create all UI widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.export_action)
        self.file_menu.addAction(self.import_action)

        # Target mesh section
        self.mesh_label = QtWidgets.QLabel("Target Mesh:")
        self.mesh_input = QtWidgets.QLineEdit()
        self.mesh_input.setPlaceholderText("Select a mesh...")
        self.mesh_btn = QtWidgets.QPushButton("<<")
        self.mesh_btn.setFixedWidth(30)
        self.mesh_btn.setToolTip("Get mesh from selection")

        self.face_count_label = QtWidgets.QLabel("Total Faces: -")
        self.face_count_label.setStyleSheet("color: #888;")

        # Group list widget
        self.group_list = GroupListWidget()

        # Action buttons
        self.apply_shaders_btn = QtWidgets.QPushButton("Apply Shaders")
        self.apply_shaders_btn.setToolTip(
            "Re-apply all shaders to visualize current groups"
        )

        self.toggle_shaders_btn = QtWidgets.QPushButton("Show Original Shaders")
        self.toggle_shaders_btn.setCheckable(True)
        self.toggle_shaders_btn.setToolTip(
            "Toggle between partition and original shaders"
        )

        self.reset_btn = QtWidgets.QPushButton("Reset All")
        self.reset_btn.setToolTip("Reset to single default group with all faces")
        self.reset_btn.setStyleSheet("background-color: #aa4444;")

        # Status label
        self.status_label = QtWidgets.QLabel("Select a mesh to begin")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")

    def create_layout(self):
        """Arrange widgets in layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Menu bar
        main_layout.setMenuBar(self.menu_bar)

        # Target mesh section
        mesh_group = QtWidgets.QGroupBox("Target Mesh")
        mesh_layout = QtWidgets.QVBoxLayout(mesh_group)

        mesh_row = QtWidgets.QHBoxLayout()
        mesh_row.addWidget(self.mesh_label)
        mesh_row.addWidget(self.mesh_input)
        mesh_row.addWidget(self.mesh_btn)
        mesh_layout.addLayout(mesh_row)

        mesh_layout.addWidget(self.face_count_label)

        main_layout.addWidget(mesh_group)

        # Polygon groups section
        groups_group = QtWidgets.QGroupBox("Polygon Groups")
        groups_layout = QtWidgets.QVBoxLayout(groups_group)
        groups_layout.addWidget(self.group_list)

        main_layout.addWidget(groups_group, stretch=1)

        # Action buttons
        actions_group = QtWidgets.QGroupBox("Actions")
        actions_layout = QtWidgets.QHBoxLayout(actions_group)
        actions_layout.addWidget(self.apply_shaders_btn)
        actions_layout.addWidget(self.toggle_shaders_btn)
        actions_layout.addWidget(self.reset_btn)

        main_layout.addWidget(actions_group)

        # Status
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Connect signals to slots."""
        # File menu actions
        self.export_action.triggered.connect(self.export_configuration)
        self.import_action.triggered.connect(self.import_configuration)

        # Mesh selection
        self.mesh_btn.clicked.connect(self.get_mesh_from_selection)
        self.mesh_input.returnPressed.connect(self.on_mesh_changed)

        # Group list
        self.group_list.group_added.connect(self.add_group_from_selection)
        self.group_list.group_removed.connect(self.on_group_removed)
        self.group_list.group_selected.connect(self.on_group_selected)
        self.group_list.color_changed.connect(self.on_color_changed)
        self.group_list.name_changed.connect(self.on_name_changed)

        # Actions
        self.apply_shaders_btn.clicked.connect(self.apply_all_shaders)
        self.toggle_shaders_btn.clicked.connect(self.toggle_shaders)
        self.reset_btn.clicked.connect(self.reset_all_groups)

    def set_initial_state(self):
        """Set initial widget states after UI is built."""
        self.export_action.setEnabled(False)
        self.apply_shaders_btn.setEnabled(False)
        self.toggle_shaders_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.group_list.add_btn.setEnabled(False)

    # =========================================================
    # MESH OPERATIONS
    # =========================================================

    def get_mesh_from_selection(self):
        """Get mesh from current Maya selection."""
        selection = cmds.ls(selection=True, long=True)
        if not selection:
            self.set_status("Please select a mesh", error=True)
            return

        mesh = None
        for obj in selection:
            # Check if it's a mesh or has a mesh shape
            shapes = cmds.listRelatives(
                obj, shapes=True, type="mesh", fullPath=True
            )
            if shapes:
                mesh = obj
                break
            elif cmds.nodeType(obj) == "mesh":
                parent = cmds.listRelatives(obj, parent=True, fullPath=True)
                if parent:
                    mesh = parent[0]
                    break

        if mesh:
            self.mesh_input.setText(mesh)
            self.on_mesh_changed()
        else:
            self.set_status("No mesh found in selection", error=True)

    def on_mesh_changed(self):
        """Handle mesh input change - initialize group manager."""
        mesh = self.mesh_input.text().strip()

        if not mesh:
            return

        if not cmds.objExists(mesh):
            self.set_status(f"Mesh '{mesh}' does not exist", error=True)
            return

        # Check if it's actually a mesh
        shapes = cmds.listRelatives(mesh, shapes=True, type="mesh")
        if not shapes:
            self.set_status(f"'{mesh}' is not a mesh", error=True)
            return

        # Clean up existing manager
        if self.group_manager:
            core.cleanup_all_shaders(self.group_manager)

        # Clear existing group items
        self.group_list.clear_all()

        # Create new manager
        self.group_manager = core.PolygonGroupManager(mesh)

        # Capture original shading before applying partition shaders
        core.capture_original_shading(self.group_manager)

        # Create default group with all faces
        default_group = core.create_default_group(self.group_manager)
        self.group_manager.groups.append(default_group)

        # Add to UI
        self.group_list.add_group_item(default_group, is_default=True)

        # Update face count
        self.update_face_count()

        # Enable buttons
        self.export_action.setEnabled(True)
        self.apply_shaders_btn.setEnabled(True)
        self.toggle_shaders_btn.setEnabled(True)
        self.toggle_shaders_btn.setChecked(False)
        self.toggle_shaders_btn.setText("Show Original Shaders")
        self.reset_btn.setEnabled(True)
        self.group_list.add_btn.setEnabled(True)

        self.set_status(f"Loaded mesh: {mesh.split('|')[-1]}")

    def update_face_count(self):
        """Update the total face count label."""
        if self.group_manager:
            total = sum(len(g.face_indices) for g in self.group_manager.groups)
            self.face_count_label.setText(f"Total Faces: {total}")
        else:
            self.face_count_label.setText("Total Faces: -")

    # =========================================================
    # GROUP OPERATIONS
    # =========================================================

    def add_group_from_selection(self):
        """Create new group from currently selected faces."""
        if not self.group_manager:
            self.set_status("Please load a mesh first", error=True)
            return

        # Get selected faces
        mesh_from_sel, selected_faces = core.get_selected_faces(
            self.group_manager.mesh
        )

        if not selected_faces:
            self.set_status("Please select some faces on the mesh", error=True)
            return

        if mesh_from_sel and not core.names_match(
            mesh_from_sel, self.group_manager.mesh
        ):
            self.set_status(
                "Selected faces are not from the target mesh", error=True
            )
            return

        # Generate unique name
        name = self.group_manager.generate_unique_name("Group")

        # Open undo chunk
        cmds.undoInfo(openChunk=True)

        try:
            # Create group
            new_group = core.create_group_from_selection(
                self.group_manager, name, selected_faces
            )

            if new_group:
                self.group_manager.groups.append(new_group)
                self.group_list.add_group_item(new_group, is_default=False)

                # Update all face counts
                self.group_list.update_all_face_counts()

                self.set_status(f"Created group: {name}")
            else:
                self.set_status("Failed to create group", error=True)

        finally:
            cmds.undoInfo(closeChunk=True)

    def on_group_removed(self, group_name):
        """Handle group removal.

        Args:
            group_name: Name of the group to remove.
        """
        if not self.group_manager:
            return

        group = self.group_manager.get_group_by_name(group_name)
        if not group:
            return

        cmds.undoInfo(openChunk=True)

        try:
            if core.remove_group(self.group_manager, group):
                self.group_list.remove_group_item(group_name)
                self.group_list.update_all_face_counts()
                self.set_status(f"Removed group: {group_name}")

        finally:
            cmds.undoInfo(closeChunk=True)

    def on_group_selected(self, group_name):
        """Handle group select button click.

        Args:
            group_name: Name of the group to select faces for.
        """
        if not self.group_manager:
            return

        group = self.group_manager.get_group_by_name(group_name)
        if not group or not group.face_indices:
            return

        # Build face list and select
        faces = [
            f"{self.group_manager.mesh}.f[{i}]"
            for i in sorted(group.face_indices)
        ]
        cmds.select(faces, replace=True)

        self.set_status(f"Selected {len(faces)} faces")

    def on_color_changed(self, group_name, new_color):
        """Handle group color change.

        Args:
            group_name: Name of the group.
            new_color: New RGB color tuple.
        """
        if not self.group_manager:
            return

        group = self.group_manager.get_group_by_name(group_name)
        if not group:
            return

        cmds.undoInfo(openChunk=True)

        try:
            core.update_group_color(group, new_color)
            self.set_status(f"Updated color for: {group_name}")

        finally:
            cmds.undoInfo(closeChunk=True)

    def on_name_changed(self, old_name, new_name):
        """Handle group name change.

        Args:
            old_name: Previous group name.
            new_name: New group name.
        """
        if not self.group_manager:
            return

        group = self.group_manager.get_group_by_name(old_name)
        if not group:
            return

        cmds.undoInfo(openChunk=True)

        try:
            if core.rename_group(self.group_manager, group, new_name):
                self.set_status(f"Renamed group: {old_name} -> {new_name}")
            else:
                self.set_status(f"Failed to rename group", error=True)

        finally:
            cmds.undoInfo(closeChunk=True)

    # =========================================================
    # FILE OPERATIONS
    # =========================================================

    def export_configuration(self):
        """Export current configuration to a .evp file."""
        if not self.group_manager:
            self.set_status("No configuration to export", error=True)
            return

        # Get save file path
        file_filter = f"Evaluation Partition (*{core.CONFIG_FILE_EXT})"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            "",
            file_filter,
        )

        if not file_path:
            return

        if core.export_configuration(file_path, self.group_manager):
            self.set_status(f"Exported: {file_path.split('/')[-1]}")
        else:
            self.set_status("Export failed", error=True)

    def import_configuration(self):
        """Import configuration from a .evp file."""
        # Get open file path
        file_filter = f"Evaluation Partition (*{core.CONFIG_FILE_EXT})"
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Configuration",
            "",
            file_filter,
        )

        if not file_path:
            return

        config = core.import_configuration(file_path)
        if not config:
            self.set_status("Import failed", error=True)
            return

        # Get mesh from config or current input
        mesh = config.get("mesh", "")
        current_mesh = self.mesh_input.text().strip()

        # If current mesh is set and different from config, ask user
        if current_mesh and mesh and not core.names_match(current_mesh, mesh):
            result = QtWidgets.QMessageBox.question(
                self,
                "Mesh Mismatch",
                f"Configuration was created for '{mesh}'.\n"
                f"Current mesh is '{current_mesh}'.\n\n"
                "Apply configuration to current mesh?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            if result == QtWidgets.QMessageBox.Yes:
                mesh = current_mesh
            else:
                return

        # Use current mesh if none in config
        if not mesh:
            mesh = current_mesh

        if not mesh:
            self.set_status("No mesh specified", error=True)
            return

        if not cmds.objExists(mesh):
            self.set_status(f"Mesh '{mesh}' does not exist", error=True)
            return

        cmds.undoInfo(openChunk=True)

        try:
            # Preserve original shading if same mesh, otherwise capture
            preserved_shading = {}
            if (
                self.group_manager
                and core.names_match(self.group_manager.mesh, mesh)
                and self.group_manager.original_shading
            ):
                preserved_shading = self.group_manager.original_shading

            # Clean up existing manager
            if self.group_manager:
                core.cleanup_all_shaders(self.group_manager)

            # Clear UI
            self.group_list.clear_all()

            # Capture original shading if not preserved
            if not preserved_shading:
                temp_manager = core.PolygonGroupManager(mesh)
                core.capture_original_shading(temp_manager)
                preserved_shading = temp_manager.original_shading

            # Apply configuration
            self.group_manager = core.apply_configuration(config, mesh=mesh)

            if not self.group_manager:
                self.set_status("Failed to apply configuration", error=True)
                return

            # Restore original shading data
            self.group_manager.original_shading = preserved_shading

            # Update mesh input
            self.mesh_input.setText(mesh)

            # Add groups to UI
            for group in self.group_manager.groups:
                is_default = group.name == core.DEFAULT_GROUP_NAME
                self.group_list.add_group_item(group, is_default=is_default)

            # Update face count
            self.update_face_count()

            # Enable buttons
            self.export_action.setEnabled(True)
            self.apply_shaders_btn.setEnabled(True)
            self.toggle_shaders_btn.setEnabled(True)
            self.toggle_shaders_btn.setChecked(False)
            self.toggle_shaders_btn.setText("Show Original Shaders")
            self.reset_btn.setEnabled(True)
            self.group_list.add_btn.setEnabled(True)

            self.set_status(f"Imported: {file_path.split('/')[-1]}")

        finally:
            cmds.undoInfo(closeChunk=True)

    def get_configuration(self):
        """Get current configuration as a dictionary.

        This can be used for scripting and automation.

        Returns:
            Configuration dictionary, or None if no manager.
        """
        if not self.group_manager:
            return None
        return core.manager_to_config(self.group_manager)

    # =========================================================
    # ACTION OPERATIONS
    # =========================================================

    def apply_all_shaders(self):
        """Re-apply all shaders to visualize current groups."""
        if not self.group_manager:
            return

        cmds.undoInfo(openChunk=True)

        try:
            core.show_partition_shaders(self.group_manager)

            # Update toggle button state
            self.toggle_shaders_btn.setChecked(False)
            self.toggle_shaders_btn.setText("Show Original Shaders")

            self.set_status("Applied all shaders")

        finally:
            cmds.undoInfo(closeChunk=True)

    def toggle_shaders(self):
        """Toggle between partition and original shaders."""
        if not self.group_manager:
            return

        if not self.group_manager.original_shading:
            self.set_status("No original shading data available", error=True)
            self.toggle_shaders_btn.setChecked(False)
            return

        cmds.undoInfo(openChunk=True)

        try:
            core.toggle_shaders(self.group_manager)

            if self.group_manager.showing_partitions:
                self.toggle_shaders_btn.setText("Show Original Shaders")
                self.toggle_shaders_btn.setChecked(False)
                self.set_status("Showing partition shaders")
            else:
                self.toggle_shaders_btn.setText("Show Partition Shaders")
                self.toggle_shaders_btn.setChecked(True)
                self.set_status("Showing original shaders")

        finally:
            cmds.undoInfo(closeChunk=True)

    def reset_all_groups(self):
        """Reset to single default group containing all polygons."""
        if not self.group_manager:
            return

        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self,
            "Reset All Groups",
            "This will remove all groups and create a single group with all faces.\n\nContinue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if result != QtWidgets.QMessageBox.Yes:
            return

        cmds.undoInfo(openChunk=True)

        try:
            # Clear UI
            self.group_list.clear_all()

            # Reset manager
            default_group = core.reset_to_default(self.group_manager)

            # Add default group to UI
            self.group_list.add_group_item(default_group, is_default=True)

            self.set_status("Reset to default group")

        finally:
            cmds.undoInfo(closeChunk=True)

    # =========================================================
    # UTILITY METHODS
    # =========================================================

    def set_status(self, message, error=False):
        """Set status message.

        Args:
            message: Status message text.
            error: If True, display as error (red text).
        """
        if error:
            self.status_label.setStyleSheet(
                "color: #ff6666; font-style: italic;"
            )
            cmds.warning(message)
        else:
            self.status_label.setStyleSheet("color: #888; font-style: italic;")

        self.status_label.setText(message)

    # =========================================================
    # MAYA INTEGRATION
    # =========================================================

    def close(self):
        """Clean up before closing."""
        self.save_settings()
        self.deleteLater()

    def closeEvent(self, event):
        """Handle close event."""
        self.close()

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self.close()
