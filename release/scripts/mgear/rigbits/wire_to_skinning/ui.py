"""Wire to Skinning - Main UI dialog.

This module contains the main UI for the Wire to Skinning tool.
"""

# Standard library
import ast

# mGear
from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.core.widgets import CollapsibleWidget

# Maya
from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Relative imports
from . import core
from .widgets import WireListItem, JointListWidget


class WireToSkinningUI(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """Main UI for Wire to Skinning Tool."""

    TOOL_NAME = "WireToSkinning"
    TOOL_TITLE = "Wire to Skinning"

    def __init__(self, parent=None):
        super(WireToSkinningUI, self).__init__(parent)

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)

        # Set window flags
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )

        self._create_ui()
        self._create_connections()
        self._refresh_wire_list()

        # Set initial size after UI is created
        self.resize(320, 700)

    def _create_ui(self):
        """Create the UI elements."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Menu bar
        self._create_menu_bar(main_layout)

        # Content layout with margins
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        # Scroll area for content
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        # =================================================================
        # SECTION 1: CREATE WIRE
        # =================================================================
        self.create_section = CollapsibleWidget(
            "1. Create Wire Deformer", expandable=False
        )

        # Mesh input
        mesh_layout = QtWidgets.QHBoxLayout()
        mesh_layout.addWidget(QtWidgets.QLabel("Target Mesh:"))
        self.mesh_input = QtWidgets.QLineEdit()
        self.mesh_input.setPlaceholderText("Select mesh to deform")
        mesh_layout.addWidget(self.mesh_input)
        self.mesh_btn = QtWidgets.QPushButton("<<")
        self.mesh_btn.setFixedWidth(30)
        mesh_layout.addWidget(self.mesh_btn)
        self.create_section.addLayout(mesh_layout)

        # Edge input
        edge_layout = QtWidgets.QHBoxLayout()
        edge_layout.addWidget(QtWidgets.QLabel("Edge Loop:"))
        self.edge_input = QtWidgets.QLineEdit()
        self.edge_input.setPlaceholderText("Select edges for wire curve")
        edge_layout.addWidget(self.edge_input)
        self.edge_btn = QtWidgets.QPushButton("<<")
        self.edge_btn.setFixedWidth(30)
        edge_layout.addWidget(self.edge_btn)
        self.create_section.addLayout(edge_layout)

        # Number of CVs
        cv_layout = QtWidgets.QHBoxLayout()
        cv_layout.addWidget(QtWidgets.QLabel("Number of CVs:"))
        self.cv_spinbox = QtWidgets.QSpinBox()
        self.cv_spinbox.setRange(4, 100)
        self.cv_spinbox.setValue(8)
        cv_layout.addWidget(self.cv_spinbox)
        cv_layout.addStretch()
        self.create_section.addLayout(cv_layout)

        # Dropoff distance
        dropoff_layout = QtWidgets.QHBoxLayout()
        dropoff_layout.addWidget(QtWidgets.QLabel("Dropoff Distance:"))
        self.dropoff_spinbox = QtWidgets.QDoubleSpinBox()
        self.dropoff_spinbox.setRange(0.001, 1000.0)
        self.dropoff_spinbox.setValue(1.0)
        self.dropoff_spinbox.setDecimals(3)
        dropoff_layout.addWidget(self.dropoff_spinbox)
        dropoff_layout.addStretch()
        self.create_section.addLayout(dropoff_layout)

        # Wire name
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(QtWidgets.QLabel("Wire Name:"))
        self.wire_name_input = QtWidgets.QLineEdit()
        self.wire_name_input.setText("wire")
        self.wire_name_input.setPlaceholderText("Name for the wire deformer")
        name_layout.addWidget(self.wire_name_input)
        self.create_section.addLayout(name_layout)

        # Create button
        self.create_wire_btn = QtWidgets.QPushButton("Create Wire Deformer")
        self.create_wire_btn.setMinimumHeight(35)
        self.create_wire_btn.setStyleSheet("background-color: #4a7c4e;")
        self.create_section.addWidget(self.create_wire_btn)

        scroll_layout.addWidget(self.create_section)

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
        self.wire_list_section.addWidget(self.wire_list_widget)

        # Refresh button
        self.refresh_btn = QtWidgets.QPushButton("Refresh Wire List")
        self.refresh_btn.clicked.connect(self._refresh_wire_list)
        self.wire_list_section.addWidget(self.refresh_btn)

        scroll_layout.addWidget(self.wire_list_section)

        # =================================================================
        # SECTION 2: CONVERT TO SKIN
        # =================================================================
        self.convert_section = CollapsibleWidget(
            "2. Convert to Skin Cluster", expandable=False
        )

        # Wire selection
        wire_select_layout = QtWidgets.QHBoxLayout()
        wire_select_layout.addWidget(QtWidgets.QLabel("Wire Deformer:"))
        self.wire_combo = QtWidgets.QComboBox()
        self.wire_combo.setMinimumWidth(200)
        wire_select_layout.addWidget(self.wire_combo)
        wire_select_layout.addStretch()
        self.convert_section.addLayout(wire_select_layout)

        # Convert all checkbox
        self.convert_all_cb = QtWidgets.QCheckBox("Convert all wire deformers")
        self.convert_section.addWidget(self.convert_all_cb)

        # Joint creation options
        joint_group = QtWidgets.QGroupBox("Joint Options")
        joint_layout = QtWidgets.QVBoxLayout(joint_group)

        self.auto_joints_rb = QtWidgets.QRadioButton(
            "Create joints automatically at CVs"
        )
        self.auto_joints_rb.setChecked(True)
        joint_layout.addWidget(self.auto_joints_rb)

        self.custom_joints_rb = QtWidgets.QRadioButton("Use existing joints")
        joint_layout.addWidget(self.custom_joints_rb)

        # Joint prefix (for auto creation)
        prefix_layout = QtWidgets.QHBoxLayout()
        prefix_layout.addWidget(QtWidgets.QLabel("Joint Prefix:"))
        self.joint_prefix_input = QtWidgets.QLineEdit()
        self.joint_prefix_input.setText("wire_jnt")
        prefix_layout.addWidget(self.joint_prefix_input)
        joint_layout.addLayout(prefix_layout)

        # Parent joint
        parent_layout = QtWidgets.QHBoxLayout()
        parent_layout.addWidget(QtWidgets.QLabel("Parent Joint:"))
        self.parent_joint_input = QtWidgets.QLineEdit()
        self.parent_joint_input.setPlaceholderText(
            "Optional parent for created joints"
        )
        parent_layout.addWidget(self.parent_joint_input)
        self.parent_joint_btn = QtWidgets.QPushButton("<<")
        self.parent_joint_btn.setFixedWidth(30)
        parent_layout.addWidget(self.parent_joint_btn)
        joint_layout.addLayout(parent_layout)

        # Custom joint list (for existing joints)
        self.custom_joint_label = QtWidgets.QLabel(
            "Custom Joints (must match CV count):"
        )
        joint_layout.addWidget(self.custom_joint_label)

        self.joint_list = JointListWidget()
        joint_layout.addWidget(self.joint_list)

        self.convert_section.addWidget(joint_group)

        # Delete wire checkbox
        self.delete_wire_cb = QtWidgets.QCheckBox(
            "Delete wire deformer after conversion"
        )
        self.convert_section.addWidget(self.delete_wire_cb)

        # Convert button
        self.convert_btn = QtWidgets.QPushButton("Convert to Skin Cluster")
        self.convert_btn.setMinimumHeight(35)
        self.convert_btn.setStyleSheet("background-color: #4a6b8c;")
        self.convert_section.addWidget(self.convert_btn)

        scroll_layout.addWidget(self.convert_section)

        # Add stretch at the end
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        content_layout.addWidget(scroll_area)

        # Status bar
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #888888; font-style: italic;")
        content_layout.addWidget(self.status_label)

        main_layout.addLayout(content_layout)

        # Update UI state
        self._update_joint_options_ui()

    def _create_menu_bar(self, parent_layout):
        """Create the menu bar with File menu."""
        menu_bar = QtWidgets.QMenuBar()
        menu_bar.setNativeMenuBar(False)

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Export action
        export_action = file_menu.addAction("Export Configuration...")
        export_action.triggered.connect(self._export_config)

        # Import action
        import_action = file_menu.addAction("Import Configuration...")
        import_action.triggered.connect(self._import_config)

        parent_layout.addWidget(menu_bar)

    def _create_connections(self):
        """Create signal connections."""
        # Create wire section
        self.mesh_btn.clicked.connect(self._get_mesh_from_selection)
        self.edge_btn.clicked.connect(self._get_edges_from_selection)
        self.create_wire_btn.clicked.connect(self._create_wire)

        # Convert section
        self.auto_joints_rb.toggled.connect(self._update_joint_options_ui)
        self.custom_joints_rb.toggled.connect(self._update_joint_options_ui)
        self.parent_joint_btn.clicked.connect(self._get_parent_joint)
        self.convert_btn.clicked.connect(self._convert_to_skin)

        # Mesh input change
        self.mesh_input.textChanged.connect(self._refresh_wire_list)

    def _update_joint_options_ui(self):
        """Update UI based on joint option selection."""
        use_auto = self.auto_joints_rb.isChecked()

        self.joint_prefix_input.setEnabled(use_auto)
        self.parent_joint_input.setEnabled(use_auto)
        self.parent_joint_btn.setEnabled(use_auto)

        self.custom_joint_label.setEnabled(not use_auto)
        self.joint_list.setEnabled(not use_auto)

    def _get_mesh_from_selection(self):
        """Get mesh from current selection."""
        selection = cmds.ls(selection=True, transforms=True)
        if selection:
            shapes = cmds.listRelatives(selection[0], shapes=True, type="mesh")
            if shapes:
                self.mesh_input.setText(selection[0])
                self._refresh_wire_list()
            else:
                self._set_status("Selected object is not a mesh", error=True)

    def _get_edges_from_selection(self):
        """Get edges from current selection."""
        selection = cmds.ls(selection=True, flatten=True)
        edges = cmds.filterExpand(selection, selectionMask=32)
        if edges:
            self.edge_input.setText(str(edges))
        else:
            self._set_status("No edges selected", error=True)

    def _get_parent_joint(self):
        """Get parent joint from selection."""
        selection = cmds.ls(selection=True, type="joint")
        if selection:
            self.parent_joint_input.setText(selection[0])

    def _refresh_wire_list(self):
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
            item.removed.connect(self._remove_wire_deformer)
            self.wire_list_layout.addWidget(item)
            self.wire_combo.addItem(wire)

    def _remove_wire_deformer(self, wire_name):
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
                cmds.delete(wire_name)

                if wire_info["wire_curve"] and cmds.objExists(
                    wire_info["wire_curve"]
                ):
                    cmds.delete(wire_info["wire_curve"])
                if wire_info["base_curve"] and cmds.objExists(
                    wire_info["base_curve"]
                ):
                    cmds.delete(wire_info["base_curve"])

                self._refresh_wire_list()
                self._set_status("Deleted wire deformer: {}".format(wire_name))

    def _create_wire(self):
        """Create a wire deformer from the specified inputs."""
        mesh = self.mesh_input.text()
        edge_str = self.edge_input.text()
        num_cvs = self.cv_spinbox.value()
        dropoff = self.dropoff_spinbox.value()
        wire_name = self.wire_name_input.text() or "wire"

        if not mesh or not cmds.objExists(mesh):
            self._set_status("Please specify a valid mesh", error=True)
            return

        if not edge_str:
            self._set_status("Please select edges", error=True)
            return

        try:
            # Parse edge string safely using ast.literal_eval
            edges = ast.literal_eval(edge_str)
            if not isinstance(edges, list):
                edges = [edges]
        except (ValueError, SyntaxError):
            self._set_status("Invalid edge selection format", error=True)
            return

        # Get positions from edges
        positions = core.get_edges_positions(edges)

        if len(positions) < 2:
            self._set_status(
                "Not enough edge positions to create curve", error=True
            )
            return

        # Create curve
        curve_name = wire_name + "_curve"
        curve = core.create_curve_from_positions(positions, num_cvs, curve_name)

        if not curve:
            self._set_status("Failed to create curve", error=True)
            return

        # Create wire deformer
        wire = core.create_wire_deformer(mesh, curve, dropoff, wire_name)

        if wire:
            self._set_status("Created wire deformer: {}".format(wire))
            self._refresh_wire_list()
            cmds.select(curve)
        else:
            self._set_status("Failed to create wire deformer", error=True)

    def _convert_to_skin(self):
        """Convert wire deformer(s) to skin cluster."""
        mesh = self.mesh_input.text()

        if not mesh or not cmds.objExists(mesh):
            self._set_status("Please specify a valid mesh", error=True)
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
            self._set_status("No wire deformers to convert", error=True)
            return

        all_joints = []

        for wire in wires:
            if not cmds.objExists(wire):
                continue

            wire_info = core.get_wire_deformer_info(wire)

            if not wire_info:
                self._set_status(
                    "Could not get info for {}".format(wire), error=True
                )
                continue

            if not wire_info.get("wire_curve"):
                self._set_status(
                    "Could not find curve for {}".format(wire), error=True
                )
                continue

            curve_info = core.get_curve_info(wire_info["wire_curve"])

            if not curve_info:
                self._set_status(
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
                    self._set_status(
                        "Joint count ({}) doesn't match CV count ({}) "
                        "for {}".format(
                            len(joints), curve_info["num_cvs"], wire
                        ),
                        error=True,
                    )
                    continue

            # Compute weights
            self._set_status("Computing weights for {}...".format(wire))
            QtWidgets.QApplication.processEvents()

            weights, uses_static_joint = core.compute_skin_weights_deboor(
                mesh,
                curve_info,
                wire_info,
                wire_deformer=wire,
                weight_threshold=0.001,
                static_joint_name="static_jnt",
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
            self._set_status("Applying skin weights for {}...".format(wire))
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
            self._set_status("Converted {} to skin cluster".format(wire))

        if all_joints:
            self._set_status(
                "Conversion complete! Created {} joints".format(len(all_joints))
            )
            self._refresh_wire_list()

    def _export_config(self):
        """Export configuration to file."""
        mesh = self.mesh_input.text()

        if not mesh or not cmds.objExists(mesh):
            self._set_status("Please specify a valid mesh", error=True)
            return

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Wire Configuration", "", "JSON Files (*.json)"
        )

        if filepath:
            if not filepath.endswith(".json"):
                filepath += ".json"

            if core.export_configuration(mesh, filepath):
                self._set_status(
                    "Configuration exported to: {}".format(filepath)
                )
            else:
                self._set_status("Failed to export configuration", error=True)

    def _import_config(self):
        """Import configuration from file."""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Wire Configuration", "", "JSON Files (*.json)"
        )

        if filepath:
            mesh = self.mesh_input.text()
            target = mesh if mesh and cmds.objExists(mesh) else None

            result = core.import_configuration(filepath, target)

            if result:
                self._set_status(
                    "Imported {} wire deformer(s)".format(len(result))
                )
                self._refresh_wire_list()
            else:
                self._set_status("Failed to import configuration", error=True)

    def _set_status(self, message, error=False):
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
