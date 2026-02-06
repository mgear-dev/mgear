"""Wire to Skinning - Main UI dialog.

This module contains the main UI for the Wire to Skinning tool.
"""

# Standard library
import ast

# mGear
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.core import pyqt
from mgear.core import utils as core_utils
from mgear.core.widgets import CollapsibleWidget

# Maya
from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Relative imports
from . import core
from .widgets import WireListItem, JointListWidget


class WireToSkinningUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for Wire to Skinning Tool."""

    TOOL_NAME = "WireToSkinning"
    TOOL_TITLE = "Wire to Skinning"

    def __init__(self, parent=None):
        super(WireToSkinningUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        # Window setup
        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)

        # Platform-specific window flags
        if cmds.about(ntOS=True):
            flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        # Build UI
        self.setup_ui()

        # User settings definition (for SettingsMixin)
        # Note: Only QCheckBox, QAction, QComboBox, QLineEdit are supported
        self.user_settings = {
            "wireToSkinning_convert_all": (self.convert_all_cb, False),
            "wireToSkinning_delete_wire": (self.delete_wire_cb, False),
        }
        self.load_settings()

        # Set initial size after UI is created
        self.resize(320, 720)

    # =========================================================================
    # UI SETUP METHODS
    # =========================================================================

    def setup_ui(self):
        """Main UI setup - calls all UI construction methods in order."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.set_initial_state()

    def create_actions(self):
        """Create QActions for menus."""
        self.export_action = QtWidgets.QAction("Export Configuration...", self)
        self.import_action = QtWidgets.QAction("Import Configuration...", self)

    def create_widgets(self):
        """Create all UI widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.export_action)
        self.file_menu.addAction(self.import_action)

        # Scroll area for content
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_content = QtWidgets.QWidget()

        # =================================================================
        # SECTION 1: CREATE WIRE
        # =================================================================
        self.create_section = CollapsibleWidget(
            "1. Create Wire Deformer", expandable=False
        )

        # Mesh input
        self.mesh_label = QtWidgets.QLabel("Target Mesh:")
        self.mesh_input = QtWidgets.QLineEdit()
        self.mesh_input.setPlaceholderText("Select mesh to deform")
        self.mesh_btn = QtWidgets.QPushButton("<<")
        self.mesh_btn.setFixedWidth(30)

        # Edge input
        self.edge_label = QtWidgets.QLabel("Edge Loop:")
        self.edge_input = QtWidgets.QLineEdit()
        self.edge_input.setPlaceholderText("Select edges for wire curve")
        self.edge_btn = QtWidgets.QPushButton("<<")
        self.edge_btn.setFixedWidth(30)

        # Number of CVs
        self.cv_label = QtWidgets.QLabel("Number of CVs:")
        self.cv_spinbox = QtWidgets.QSpinBox()
        self.cv_spinbox.setRange(4, 100)
        self.cv_spinbox.setValue(8)

        # Dropoff distance
        self.dropoff_label = QtWidgets.QLabel("Dropoff Distance:")
        self.dropoff_spinbox = QtWidgets.QDoubleSpinBox()
        self.dropoff_spinbox.setRange(0.001, 1000.0)
        self.dropoff_spinbox.setValue(1.0)
        self.dropoff_spinbox.setDecimals(3)

        # Wire name
        self.wire_name_label = QtWidgets.QLabel("Wire Name:")
        self.wire_name_input = QtWidgets.QLineEdit()
        self.wire_name_input.setText("wire")
        self.wire_name_input.setPlaceholderText("Name for the wire deformer")

        # Create button
        self.create_wire_btn = QtWidgets.QPushButton("Create Wire Deformer")
        self.create_wire_btn.setMinimumHeight(35)
        self.create_wire_btn.setStyleSheet("background-color: #4a7c4e;")

        # =================================================================
        # WIRE LIST SECTION
        # =================================================================
        self.wire_list_section = CollapsibleWidget(
            "Wire Deformers on Mesh", expandable=False
        )

        self.wire_list_widget = QtWidgets.QWidget()
        self.wire_list_layout = QtWidgets.QVBoxLayout(self.wire_list_widget)
        self.wire_list_layout.setContentsMargins(0, 0, 0, 0)
        self.wire_list_layout.setSpacing(2)

        self.refresh_btn = QtWidgets.QPushButton("Refresh Wire List")

        # =================================================================
        # SECTION 2: CONVERT TO SKIN
        # =================================================================
        self.convert_section = CollapsibleWidget(
            "2. Convert to Skin Cluster", expandable=False
        )

        # Wire selection
        self.wire_select_label = QtWidgets.QLabel("Wire Deformer:")
        self.wire_combo = QtWidgets.QComboBox()
        self.wire_combo.setMinimumWidth(200)

        # Convert all checkbox
        self.convert_all_cb = QtWidgets.QCheckBox("Convert all wire deformers")

        # Joint creation options
        self.joint_group = QtWidgets.QGroupBox("Joint Options")

        self.auto_joints_rb = QtWidgets.QRadioButton(
            "Create joints automatically at CVs"
        )
        self.auto_joints_rb.setChecked(True)

        self.custom_joints_rb = QtWidgets.QRadioButton("Use existing joints")

        # Joint prefix (for auto creation)
        self.joint_prefix_label = QtWidgets.QLabel("Joint Prefix:")
        self.joint_prefix_input = QtWidgets.QLineEdit()
        self.joint_prefix_input.setText("wire_jnt")

        # Parent joint
        self.parent_joint_label = QtWidgets.QLabel("Parent Joint:")
        self.parent_joint_input = QtWidgets.QLineEdit()
        self.parent_joint_input.setPlaceholderText(
            "Optional parent for created joints"
        )
        self.parent_joint_btn = QtWidgets.QPushButton("<<")
        self.parent_joint_btn.setFixedWidth(30)

        # Custom joint list (for existing joints)
        self.custom_joint_label = QtWidgets.QLabel(
            "Custom Joints (must match CV count):"
        )
        self.joint_list = JointListWidget()

        # Delete wire checkbox
        self.delete_wire_cb = QtWidgets.QCheckBox(
            "Delete wire deformer after conversion"
        )

        # Convert button
        self.convert_btn = QtWidgets.QPushButton("Convert to Skin Cluster")
        self.convert_btn.setMinimumHeight(35)
        self.convert_btn.setStyleSheet("background-color: #4a6b8c;")

        # Status bar
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")

    def create_layout(self):
        """Arrange widgets in layouts."""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.menu_bar)

        # Content layout with margins
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        # Scroll content layout
        scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        # --- Create Wire Section ---
        mesh_layout = QtWidgets.QHBoxLayout()
        mesh_layout.addWidget(self.mesh_label)
        mesh_layout.addWidget(self.mesh_input)
        mesh_layout.addWidget(self.mesh_btn)
        self.create_section.addLayout(mesh_layout)

        edge_layout = QtWidgets.QHBoxLayout()
        edge_layout.addWidget(self.edge_label)
        edge_layout.addWidget(self.edge_input)
        edge_layout.addWidget(self.edge_btn)
        self.create_section.addLayout(edge_layout)

        cv_layout = QtWidgets.QHBoxLayout()
        cv_layout.addWidget(self.cv_label)
        cv_layout.addWidget(self.cv_spinbox)
        cv_layout.addStretch()
        self.create_section.addLayout(cv_layout)

        dropoff_layout = QtWidgets.QHBoxLayout()
        dropoff_layout.addWidget(self.dropoff_label)
        dropoff_layout.addWidget(self.dropoff_spinbox)
        dropoff_layout.addStretch()
        self.create_section.addLayout(dropoff_layout)

        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(self.wire_name_label)
        name_layout.addWidget(self.wire_name_input)
        self.create_section.addLayout(name_layout)

        self.create_section.addWidget(self.create_wire_btn)
        scroll_layout.addWidget(self.create_section)

        # --- Wire List Section ---
        self.wire_list_section.addWidget(self.wire_list_widget)
        self.wire_list_section.addWidget(self.refresh_btn)
        scroll_layout.addWidget(self.wire_list_section)

        # --- Convert Section ---
        wire_select_layout = QtWidgets.QHBoxLayout()
        wire_select_layout.addWidget(self.wire_select_label)
        wire_select_layout.addWidget(self.wire_combo)
        wire_select_layout.addStretch()
        self.convert_section.addLayout(wire_select_layout)

        self.convert_section.addWidget(self.convert_all_cb)

        # Joint group layout
        joint_layout = QtWidgets.QVBoxLayout(self.joint_group)
        joint_layout.addWidget(self.auto_joints_rb)
        joint_layout.addWidget(self.custom_joints_rb)

        prefix_layout = QtWidgets.QHBoxLayout()
        prefix_layout.addWidget(self.joint_prefix_label)
        prefix_layout.addWidget(self.joint_prefix_input)
        joint_layout.addLayout(prefix_layout)

        parent_layout = QtWidgets.QHBoxLayout()
        parent_layout.addWidget(self.parent_joint_label)
        parent_layout.addWidget(self.parent_joint_input)
        parent_layout.addWidget(self.parent_joint_btn)
        joint_layout.addLayout(parent_layout)

        joint_layout.addWidget(self.custom_joint_label)
        joint_layout.addWidget(self.joint_list)

        self.convert_section.addWidget(self.joint_group)
        self.convert_section.addWidget(self.delete_wire_cb)
        self.convert_section.addWidget(self.convert_btn)
        scroll_layout.addWidget(self.convert_section)

        # Add stretch at the end
        scroll_layout.addStretch()

        # Assemble scroll area
        self.scroll_area.setWidget(self.scroll_content)
        content_layout.addWidget(self.scroll_area)
        content_layout.addWidget(self.status_label)

        main_layout.addLayout(content_layout)

    def create_connections(self):
        """Connect signals to slots."""
        # Menu actions
        self.export_action.triggered.connect(self.export_config)
        self.import_action.triggered.connect(self.import_config)

        # Create wire section
        self.mesh_btn.clicked.connect(self.get_mesh_from_selection)
        self.edge_btn.clicked.connect(self.get_edges_from_selection)
        self.create_wire_btn.clicked.connect(self.create_wire)

        # Wire list section
        self.refresh_btn.clicked.connect(self.refresh_wire_list)

        # Convert section
        self.auto_joints_rb.toggled.connect(self.update_joint_options_ui)
        self.custom_joints_rb.toggled.connect(self.update_joint_options_ui)
        self.parent_joint_btn.clicked.connect(self.get_parent_joint)
        self.convert_btn.clicked.connect(self.convert_to_skin)

        # Mesh input change
        self.mesh_input.textChanged.connect(self.refresh_wire_list)

    def set_initial_state(self):
        """Set initial widget states after UI is built."""
        self.update_joint_options_ui()
        self.refresh_wire_list()

    # =========================================================================
    # MAYA INTEGRATION
    # =========================================================================

    def close(self):
        """Clean up before closing."""
        self.save_settings()
        self.deleteLater()

    def closeEvent(self, _event):
        """Handle close event."""
        self.close()

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self.close()

    # =========================================================================
    # UI UPDATE METHODS
    # =========================================================================

    def update_joint_options_ui(self):
        """Update UI based on joint option selection."""
        use_auto = self.auto_joints_rb.isChecked()

        self.joint_prefix_input.setEnabled(use_auto)
        self.parent_joint_input.setEnabled(use_auto)
        self.parent_joint_btn.setEnabled(use_auto)

        self.custom_joint_label.setEnabled(not use_auto)
        self.joint_list.setEnabled(not use_auto)

    def refresh_wire_list(self):
        """Refresh the list of wire deformers on the mesh."""
        # Clear existing items
        while self.wire_list_layout.count():
            item = self.wire_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear combo box
        self.wire_combo.clear()

        mesh = self.mesh_input.text()
        if not mesh or not cmds.objExists(mesh):
            no_mesh_label = QtWidgets.QLabel("No mesh specified")
            no_mesh_label.setStyleSheet("color: #888888; font-style: italic;")
            self.wire_list_layout.addWidget(no_mesh_label)
            return

        wires = core.get_mesh_wire_deformers(mesh)

        if not wires:
            no_wire_label = QtWidgets.QLabel("No wire deformers found")
            no_wire_label.setStyleSheet("color: #888888; font-style: italic;")
            self.wire_list_layout.addWidget(no_wire_label)
            return

        for wire in wires:
            item = WireListItem(wire)
            item.removed.connect(self.remove_wire_deformer)
            self.wire_list_layout.addWidget(item)
            self.wire_combo.addItem(wire)

    def set_status(self, message, error=False):
        """Set status message.

        Args:
            message (str): Status message to display.
            error (bool): Whether this is an error message.
        """
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet(
                "color: #cc6666; font-style: italic;"
            )
        else:
            self.status_label.setStyleSheet(
                "color: #66cc66; font-style: italic;"
            )

        if error:
            cmds.warning(message)
        else:
            print(message)

    # =========================================================================
    # SELECTION METHODS
    # =========================================================================

    def get_mesh_from_selection(self):
        """Get mesh from current selection."""
        selection = cmds.ls(selection=True, transforms=True)
        if selection:
            shapes = cmds.listRelatives(selection[0], shapes=True, type="mesh")
            if shapes:
                self.mesh_input.setText(selection[0])
                self.refresh_wire_list()
            else:
                self.set_status("Selected object is not a mesh", error=True)

    def get_edges_from_selection(self):
        """Get edges from current selection."""
        selection = cmds.ls(selection=True, flatten=True)
        edges = cmds.filterExpand(selection, selectionMask=32)
        if edges:
            self.edge_input.setText(str(edges))
        else:
            self.set_status("No edges selected", error=True)

    def get_parent_joint(self):
        """Get parent joint from selection."""
        selection = cmds.ls(selection=True, type="joint")
        if selection:
            self.parent_joint_input.setText(selection[0])

    # =========================================================================
    # WIRE DEFORMER OPERATIONS
    # =========================================================================

    def remove_wire_deformer(self, wire_name):
        """Remove a wire deformer."""
        result = QtWidgets.QMessageBox.question(
            self,
            "Delete Wire Deformer",
            "Are you sure you want to delete '{}'?".format(wire_name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if result == QtWidgets.QMessageBox.Yes:
            if cmds.objExists(wire_name):
                wire_info = core.get_wire_deformer_info(wire_name)
                self._delete_wire_with_undo(wire_name, wire_info)
                self.refresh_wire_list()
                self.set_status("Deleted wire deformer: {}".format(wire_name))

    @core_utils.one_undo
    def _delete_wire_with_undo(self, wire_name, wire_info):
        """Delete wire deformer and related curves in a single undo chunk."""
        cmds.delete(wire_name)

        if wire_info["wire_curve"] and cmds.objExists(wire_info["wire_curve"]):
            cmds.delete(wire_info["wire_curve"])
        if wire_info["base_curve"] and cmds.objExists(wire_info["base_curve"]):
            cmds.delete(wire_info["base_curve"])

    def create_wire(self):
        """Create a wire deformer from the specified inputs."""
        mesh = self.mesh_input.text()
        edge_str = self.edge_input.text()
        num_cvs = self.cv_spinbox.value()
        dropoff = self.dropoff_spinbox.value()
        wire_name = self.wire_name_input.text() or "wire"

        if not mesh or not cmds.objExists(mesh):
            self.set_status("Please specify a valid mesh", error=True)
            return

        if not edge_str:
            self.set_status("Please select edges", error=True)
            return

        try:
            # Parse edge string safely using ast.literal_eval
            edges = ast.literal_eval(edge_str)
            if not isinstance(edges, list):
                edges = [edges]
        except (ValueError, SyntaxError):
            self.set_status("Invalid edge selection format", error=True)
            return

        # Get positions from edges
        positions = core.get_edges_positions(edges)

        if len(positions) < 2:
            self.set_status(
                "Not enough edge positions to create curve", error=True
            )
            return

        # Create curve
        curve_name = wire_name + "_curve"
        curve = core.create_curve_from_positions(positions, num_cvs, curve_name)

        if not curve:
            self.set_status("Failed to create curve", error=True)
            return

        # Create wire deformer
        wire = core.create_wire_deformer(mesh, curve, dropoff, wire_name)

        if wire:
            self.set_status("Created wire deformer: {}".format(wire))
            self.refresh_wire_list()
            cmds.select(curve)
        else:
            self.set_status("Failed to create wire deformer", error=True)

    def convert_to_skin(self):
        """Convert wire deformer(s) to skin cluster."""
        mesh = self.mesh_input.text()

        if not mesh or not cmds.objExists(mesh):
            self.set_status("Please specify a valid mesh", error=True)
            return

        convert_all = self.convert_all_cb.isChecked()
        delete_wire = self.delete_wire_cb.isChecked()
        use_auto_joints = self.auto_joints_rb.isChecked()
        parent_joint = self.parent_joint_input.text()

        if convert_all:
            wires = core.get_mesh_wire_deformers(mesh)
        else:
            selected_wire = self.wire_combo.currentText()
            wires = [selected_wire] if selected_wire else []

        if not wires:
            self.set_status("No wire deformers to convert", error=True)
            return

        # Log processing info
        print("=" * 60)
        print("WIRE TO SKINNING CONVERSION")
        print("=" * 60)
        print("Mesh: {}".format(mesh))
        print("Wire deformers to process: {}".format(len(wires)))
        for i, w in enumerate(wires):
            print("  [{}] {}".format(i + 1, w))
        print("-" * 60)

        all_joints = []

        for wire_idx, wire in enumerate(wires):
            if not cmds.objExists(wire):
                continue

            # Log current wire being processed
            print("\n[{}/{}] Processing wire: {}".format(
                wire_idx + 1, len(wires), wire
            ))

            wire_info = core.get_wire_deformer_info(wire)

            if not wire_info:
                self.set_status(
                    "Could not get info for {}".format(wire), error=True
                )
                continue

            if not wire_info.get("wire_curve"):
                self.set_status(
                    "Could not find curve for {}".format(wire), error=True
                )
                continue

            curve_info = core.get_curve_info(wire_info["wire_curve"])

            if not curve_info:
                self.set_status(
                    "Could not get curve info for {}".format(
                        wire_info["wire_curve"]
                    ),
                    error=True,
                )
                continue

            # Get or create joints
            if use_auto_joints:
                # Use wire name as prefix for joints
                prefix = wire
                parent = (
                    parent_joint
                    if parent_joint and cmds.objExists(parent_joint)
                    else None
                )
                joints = core.create_joints_at_cvs(
                    curve_info, prefix=prefix, parent=parent
                )
            else:
                joints = self.joint_list.get_joints()
                if len(joints) != curve_info["num_cvs"]:
                    self.set_status(
                        "Joint count ({}) doesn't match CV count ({}) "
                        "for {}".format(
                            len(joints), curve_info["num_cvs"], wire
                        ),
                        error=True,
                    )
                    continue

            # Check for existing skin cluster and get weights
            existing_skin = core.get_mesh_skin_cluster(mesh)
            existing_weights = None

            if existing_skin:
                print("  Found existing skin cluster: {}".format(existing_skin))
                print("  Will blend with existing weights...")
                self.set_status(
                    "Reading existing weights for {}...".format(wire)
                )
                QtWidgets.QApplication.processEvents()
                existing_weights = core.get_existing_skin_weights(
                    mesh, existing_skin
                )
            else:
                print("  No existing skin cluster - using static joint fallback")

            # Compute weights
            self.set_status("Computing weights for {}...".format(wire))
            QtWidgets.QApplication.processEvents()

            weights, uses_static_joint = core.compute_skin_weights_deboor(
                mesh,
                curve_info,
                wire_info,
                wire_deformer=wire,
                weight_threshold=0.001,
                static_joint_name="static_jnt",
                existing_weights=existing_weights,
            )

            # Delete or disable wire
            if delete_wire:
                base_curve = wire_info.get("base_curve")
                cmds.delete(wire)
                if base_curve and cmds.objExists(base_curve):
                    cmds.delete(base_curve)
            else:
                cmds.setAttr(wire + ".envelope", 0)

            # Create or update skin cluster
            self.set_status("Applying skin weights for {}...".format(wire))
            QtWidgets.QApplication.processEvents()

            static_jnt = "static_jnt" if uses_static_joint else None
            core.create_skin_cluster(
                mesh,
                joints,
                weights,
                name=None,
                static_joint=static_jnt,
                uses_static_joint=uses_static_joint,
            )

            all_joints.extend(joints)
            if uses_static_joint and "static_jnt" not in all_joints:
                all_joints.append("static_jnt")

            print("  Completed: {}".format(wire))
            self.set_status("Converted {} to skin cluster".format(wire))

        print("\n" + "=" * 60)
        if all_joints:
            print("CONVERSION COMPLETE")
            print("Total joints created/used: {}".format(len(all_joints)))
            self.set_status(
                "Conversion complete! Created {} joints".format(len(all_joints))
            )
            self.refresh_wire_list()
        print("=" * 60)

    # =========================================================================
    # CONFIGURATION EXPORT/IMPORT
    # =========================================================================

    def _get_conversion_settings(self):
        """Get current conversion settings from UI.

        Returns:
            dict: Conversion settings dictionary.
        """
        return {
            "convert_all": self.convert_all_cb.isChecked(),
            "selected_wire": self.wire_combo.currentText(),
            "use_auto_joints": self.auto_joints_rb.isChecked(),
            "joint_prefix": self.joint_prefix_input.text(),
            "parent_joint": self.parent_joint_input.text(),
            "custom_joints": self.joint_list.get_joints(),
            "delete_wire": self.delete_wire_cb.isChecked(),
        }

    def _apply_conversion_settings(self, settings):
        """Apply conversion settings to UI.

        Args:
            settings (dict): Conversion settings dictionary.
        """
        if not settings:
            return

        # Convert all checkbox
        if "convert_all" in settings:
            self.convert_all_cb.setChecked(settings["convert_all"])

        # Selected wire in dropdown (set after wire list is refreshed)
        if "selected_wire" in settings:
            idx = self.wire_combo.findText(settings["selected_wire"])
            if idx >= 0:
                self.wire_combo.setCurrentIndex(idx)

        # Joint options
        if settings.get("use_auto_joints", True):
            self.auto_joints_rb.setChecked(True)
        else:
            self.custom_joints_rb.setChecked(True)

        if "joint_prefix" in settings:
            self.joint_prefix_input.setText(settings["joint_prefix"])

        if "parent_joint" in settings:
            self.parent_joint_input.setText(settings["parent_joint"])

        if "custom_joints" in settings:
            self.joint_list.set_joints(settings["custom_joints"])

        if "delete_wire" in settings:
            self.delete_wire_cb.setChecked(settings["delete_wire"])

        self.update_joint_options_ui()

    def export_config(self):
        """Export configuration to file."""
        mesh = self.mesh_input.text()

        if not mesh or not cmds.objExists(mesh):
            self.set_status("Please specify a valid mesh", error=True)
            return

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Wire Configuration", "", "Wire To Skinning (*.wts)"
        )

        if filepath:
            if not filepath.endswith(".wts"):
                filepath += ".wts"

            # Get current conversion settings
            conversion_settings = self._get_conversion_settings()

            if core.export_configuration(mesh, filepath, conversion_settings):
                self.set_status(
                    "Configuration exported to: {}".format(filepath)
                )
            else:
                self.set_status("Failed to export configuration", error=True)

    def import_config(self):
        """Import configuration from file."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Wire Configuration", "", "Wire To Skinning (*.wts)"
        )

        if filepath:
            mesh = self.mesh_input.text()
            target = mesh if mesh and cmds.objExists(mesh) else None

            result = core.import_configuration(filepath, target)

            if result:
                # Update mesh input if it was empty
                if not target and result.get("mesh"):
                    self.mesh_input.setText(result["mesh"])

                # Apply conversion settings if present
                if result.get("conversion_settings"):
                    self._apply_conversion_settings(result["conversion_settings"])

                wires = result.get("wires", [])
                self.set_status(
                    "Imported {} wire deformer(s)".format(len(wires))
                )
                self.refresh_wire_list()
            else:
                self.set_status("Failed to import configuration", error=True)
