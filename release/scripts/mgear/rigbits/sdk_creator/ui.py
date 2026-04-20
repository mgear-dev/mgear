"""SDK Creator - UI Module.

Dockable dialog with two tabs: SDK Setup and Mirror.
PySide2/PySide6 compatible via Qt.py.
"""

import os

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.core import pyqt

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore

from . import core


class SDKCreatorUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main dockable dialog for the SDK Creator tool.

    Two-tab interface: SDK Setup (pose reading and application)
    and Mirror (search/replace, negate channels, mirror apply/export).
    """

    TOOL_NAME = "SDKCreator"
    TOOL_TITLE = "SDK创建器"

    def __init__(self, parent=None):
        super(SDKCreatorUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self._closing = False

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(420, 500)

        if cmds.about(ntOS=True):
            flags = (
                self.windowFlags()
                ^ QtCore.Qt.WindowContextHelpButtonHint
            )
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.setup_ui()

        self.user_settings = {}
        self.load_settings()

        self.resize(450, 600)

    # =============================================================
    # UI SETUP
    # =============================================================

    def setup_ui(self):
        """Build the full UI."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_actions(self):
        """Create menu bar actions."""
        self.export_action = QtWidgets.QAction(
            "Export Config...", self
        )
        self.export_mirror_action = QtWidgets.QAction(
            "Export Mirror Config...", self
        )
        self.import_action = QtWidgets.QAction(
            "Import Config...", self
        )
        self.apply_file_action = QtWidgets.QAction(
            "Apply from File...", self
        )
        self.delete_setup_action = QtWidgets.QAction(
            "Delete SDK Setup from Controls", self
        )

    def create_widgets(self):
        """Create all widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.file_menu = self.menu_bar.addMenu("文件")
        self.file_menu.addAction(self.export_action)
        self.file_menu.addAction(self.export_mirror_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.import_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.apply_file_action)

        self.edit_menu = self.menu_bar.addMenu("编辑")
        self.edit_menu.addAction(self.delete_setup_action)

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()

        # --- Tab 1: SDK Setup ---
        self.setup_tab = QtWidgets.QWidget()
        self._build_setup_tab()

        # --- Tab 2: Mirror ---
        self.mirror_tab = QtWidgets.QWidget()
        self._build_mirror_tab()

        self.tab_widget.addTab(self.setup_tab, "SDK Setup")
        self.tab_widget.addTab(self.mirror_tab, "Mirror")

        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #7aad7a;")

    def _build_setup_tab(self):
        """Build the SDK Setup tab contents."""
        layout = QtWidgets.QVBoxLayout(self.setup_tab)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # UIHost row
        host_layout = QtWidgets.QHBoxLayout()
        host_layout.addWidget(QtWidgets.QLabel("UIHost:"))
        self.ui_host_edit = QtWidgets.QLineEdit()
        self.ui_host_edit.setPlaceholderText(
            "Select UIHost control..."
        )
        host_layout.addWidget(self.ui_host_edit, stretch=1)
        self.ui_host_btn = QtWidgets.QPushButton("<<")
        self.ui_host_btn.setFixedWidth(int(pyqt.dpi_scale(30)))
        self.ui_host_btn.setToolTip("Get from selection")
        host_layout.addWidget(self.ui_host_btn)
        layout.addLayout(host_layout)

        # Range row
        range_layout = QtWidgets.QHBoxLayout()
        range_layout.addWidget(QtWidgets.QLabel("Range:"))
        range_layout.addWidget(QtWidgets.QLabel("Min"))
        self.min_spin = QtWidgets.QDoubleSpinBox()
        self.min_spin.setRange(-100.0, 100.0)
        self.min_spin.setValue(0.0)
        self.min_spin.setDecimals(2)
        range_layout.addWidget(self.min_spin)
        range_layout.addWidget(QtWidgets.QLabel("Max"))
        self.max_spin = QtWidgets.QDoubleSpinBox()
        self.max_spin.setRange(-100.0, 100.0)
        self.max_spin.setValue(1.0)
        self.max_spin.setDecimals(2)
        range_layout.addWidget(self.max_spin)
        range_layout.addStretch()
        layout.addLayout(range_layout)

        # Controls group
        controls_group = QtWidgets.QGroupBox("Controls")
        controls_layout = QtWidgets.QVBoxLayout(controls_group)

        self.controls_list = QtWidgets.QListWidget()
        self.controls_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        controls_layout.addWidget(self.controls_list)

        ctl_btn_layout = QtWidgets.QHBoxLayout()
        self.add_ctl_btn = QtWidgets.QPushButton(
            "Add from Selection"
        )
        self.remove_ctl_btn = QtWidgets.QPushButton(
            "Remove Selected"
        )
        ctl_btn_layout.addWidget(self.add_ctl_btn)
        ctl_btn_layout.addWidget(self.remove_ctl_btn)
        controls_layout.addLayout(ctl_btn_layout)

        layout.addWidget(controls_group)

        # Poses group
        poses_group = QtWidgets.QGroupBox("Poses")
        poses_layout = QtWidgets.QVBoxLayout(poses_group)

        self.poses_tree = QtWidgets.QTreeWidget()
        self.poses_tree.setHeaderLabels(["框架", "Pose Name"])
        self.poses_tree.setColumnWidth(0, int(pyqt.dpi_scale(60)))
        self.poses_tree.setRootIsDecorated(False)
        poses_layout.addWidget(self.poses_tree)

        pose_btn_layout = QtWidgets.QHBoxLayout()
        self.detect_btn = QtWidgets.QPushButton("Detect Poses")
        self.refresh_btn = QtWidgets.QPushButton("刷新")
        self.remove_pose_btn = QtWidgets.QPushButton("移除")
        self.pose_up_btn = QtWidgets.QPushButton("Up")
        self.pose_down_btn = QtWidgets.QPushButton("Down")
        pose_btn_layout.addWidget(self.detect_btn)
        pose_btn_layout.addWidget(self.refresh_btn)
        pose_btn_layout.addWidget(self.remove_pose_btn)
        pose_btn_layout.addWidget(self.pose_up_btn)
        pose_btn_layout.addWidget(self.pose_down_btn)
        poses_layout.addLayout(pose_btn_layout)

        layout.addWidget(poses_group)

        # Apply button
        self.apply_btn = QtWidgets.QPushButton("应用")
        self.apply_btn.setMinimumHeight(int(pyqt.dpi_scale(40)))
        self.apply_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #4a7c4e;"
            "    font-weight: bold;"
            "    font-size: 14px;"
            "}"
        )
        layout.addWidget(self.apply_btn)

    def _build_mirror_tab(self):
        """Build the Mirror tab contents."""
        layout = QtWidgets.QVBoxLayout(self.mirror_tab)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Search / Replace
        sr_layout = QtWidgets.QHBoxLayout()
        sr_layout.addWidget(QtWidgets.QLabel("Search:"))
        self.search_edit = QtWidgets.QLineEdit("_L")
        sr_layout.addWidget(self.search_edit)
        sr_layout.addWidget(QtWidgets.QLabel("Replace:"))
        self.replace_edit = QtWidgets.QLineEdit("_R")
        sr_layout.addWidget(self.replace_edit)
        layout.addLayout(sr_layout)

        # Negate channels
        negate_group = QtWidgets.QGroupBox("Negate Channels")
        negate_layout = QtWidgets.QGridLayout(negate_group)

        self.negate_checks = {}
        defaults = core.DEFAULT_MIRROR_CHANNELS
        for i, ch in enumerate(core.TRANSFORM_CHANNELS):
            cb = QtWidgets.QCheckBox(ch)
            cb.setChecked(ch in defaults)
            self.negate_checks[ch] = cb
            negate_layout.addWidget(cb, i // 3, i % 3)

        layout.addWidget(negate_group)

        layout.addStretch()

        # Mirror buttons
        self.mirror_apply_btn = QtWidgets.QPushButton(
            "Mirror && Apply"
        )
        self.mirror_apply_btn.setMinimumHeight(
            int(pyqt.dpi_scale(40))
        )
        self.mirror_apply_btn.setStyleSheet(
            "QPushButton {"
            "    background-color: #4a6c7e;"
            "    font-weight: bold;"
            "    font-size: 14px;"
            "}"
        )
        layout.addWidget(self.mirror_apply_btn)

    def create_layout(self):
        """Arrange top-level layout."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        main_layout.setMenuBar(self.menu_bar)

        main_layout.addWidget(self.tab_widget, stretch=1)
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Connect signals to slots."""
        # Menu
        self.export_action.triggered.connect(
            self._export_config
        )
        self.export_mirror_action.triggered.connect(
            self._export_mirror_config
        )
        self.import_action.triggered.connect(
            self._import_config
        )
        self.apply_file_action.triggered.connect(
            self._apply_from_file
        )

        self.delete_setup_action.triggered.connect(
            self._delete_setup
        )

        # Setup tab
        self.ui_host_btn.clicked.connect(
            self._get_ui_host_from_selection
        )
        self.add_ctl_btn.clicked.connect(
            self._add_controls_from_selection
        )
        self.remove_ctl_btn.clicked.connect(
            self._remove_selected_controls
        )
        self.detect_btn.clicked.connect(self._detect_poses)
        self.refresh_btn.clicked.connect(self._detect_poses)
        self.remove_pose_btn.clicked.connect(self._remove_pose)
        self.pose_up_btn.clicked.connect(
            lambda: self._move_pose(-1)
        )
        self.pose_down_btn.clicked.connect(
            lambda: self._move_pose(1)
        )
        self.apply_btn.clicked.connect(self._apply_setup)

        # Selection sync
        self.controls_list.itemSelectionChanged.connect(
            self._sync_maya_selection
        )

        # Mirror tab
        self.mirror_apply_btn.clicked.connect(
            self._mirror_and_apply
        )

    # =============================================================
    # SETUP TAB SLOTS
    # =============================================================

    def _get_ui_host_from_selection(self):
        """Set UIHost from Maya selection."""
        sel = cmds.ls(selection=True)
        if sel:
            self.ui_host_edit.setText(sel[0])
        else:
            cmds.warning("SDK Creator: Nothing selected")

    def _add_controls_from_selection(self):
        """Add selected controls to the list."""
        sel = cmds.ls(selection=True, type="transform")
        if not sel:
            cmds.warning("SDK Creator: No transforms selected")
            return

        existing = set()
        for i in range(self.controls_list.count()):
            existing.add(self.controls_list.item(i).text())

        added = 0
        for ctl in sel:
            if ctl not in existing:
                self.controls_list.addItem(ctl)
                added += 1

        self._set_status("Added {} control(s)".format(added))
        self._detect_poses()

    def _remove_selected_controls(self):
        """Remove selected items from the controls list."""
        for item in self.controls_list.selectedItems():
            self.controls_list.takeItem(
                self.controls_list.row(item)
            )
        self._detect_poses()

    def _sync_maya_selection(self):
        """Sync Maya scene selection with the controls list."""
        selected = [
            item.text()
            for item in self.controls_list.selectedItems()
        ]
        if selected:
            valid = [s for s in selected if cmds.objExists(s)]
            if valid:
                cmds.select(valid, replace=True)
            else:
                cmds.select(clear=True)
        else:
            cmds.select(clear=True)

    def _remove_pose(self):
        """Remove selected pose from the list."""
        item = self.poses_tree.currentItem()
        if item:
            idx = self.poses_tree.indexOfTopLevelItem(item)
            self.poses_tree.takeTopLevelItem(idx)

    def _move_pose(self, direction):
        """Move selected pose up or down.

        Args:
            direction (int): -1 for up, +1 for down.
        """
        item = self.poses_tree.currentItem()
        if not item:
            return
        idx = self.poses_tree.indexOfTopLevelItem(item)
        new_idx = idx + direction
        if 0 <= new_idx < self.poses_tree.topLevelItemCount():
            self.poses_tree.takeTopLevelItem(idx)
            self.poses_tree.insertTopLevelItem(new_idx, item)
            self.poses_tree.setCurrentItem(item)

    def _detect_poses(self):
        """Detect keyframe poses from controls."""
        controls = self._get_controls()
        if not controls:
            cmds.warning("SDK Creator: No controls in list")
            return

        frames = core.get_keyed_frames(controls)
        if not frames:
            cmds.warning("SDK Creator: No common keyframes found")
            return

        self.poses_tree.clear()
        for i, frame in enumerate(frames):
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, str(int(frame)))
            item.setFlags(
                item.flags() | QtCore.Qt.ItemIsEditable
            )
            # Auto-generate pose name
            item.setText(1, "pose_{}".format(i + 1))
            self.poses_tree.addTopLevelItem(item)

        self._set_status(
            "Detected {} poses".format(len(frames))
        )

    def _delete_setup(self):
        """Delete SDK setup from all controls in the list."""
        controls = self._get_controls()
        if not controls:
            cmds.warning("SDK Creator: No controls in list")
            return

        result = QtWidgets.QMessageBox.question(
            self,
            "Delete SDK Setup",
            "Remove SDK setup from {} control(s)?\n"
            "This will delete _sdk transform nodes and "
            "their connections.".format(len(controls)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if result != QtWidgets.QMessageBox.Yes:
            return

        ui_host = self.ui_host_edit.text().strip()
        count = core.delete_sdk_setup(controls, ui_host)
        self._set_status(
            "Deleted SDK setup from {} control(s)".format(count)
        )

    def _apply_setup(self):
        """Collect UI state, read poses, and create SDK setup."""
        config = self._build_config_from_ui()
        if not config:
            return

        result = core.create_sdk_setup(config)
        if result:
            self._set_status(
                "Created SDK setup ({} nodes)".format(len(result))
            )
        else:
            self._set_status("SDK setup failed", error=True)

    # =============================================================
    # MIRROR TAB SLOTS
    # =============================================================

    def _mirror_and_apply(self):
        """Mirror the current config and apply."""
        config = self._build_config_from_ui()
        if not config:
            return

        search = self.search_edit.text()
        replace = self.replace_edit.text()
        negate = self._get_negate_channels()

        result = core.mirror_sdk_setup(
            config, search, replace, negate
        )
        if result:
            self._set_status(
                "Mirrored SDK setup ({} nodes)".format(len(result))
            )
        else:
            self._set_status("Mirror setup failed", error=True)

    # =============================================================
    # FILE MENU SLOTS
    # =============================================================

    def _export_config(self):
        """Export current config to file."""
        config = self._build_config_from_ui()
        if not config:
            return

        file_path = self._get_save_path()
        if file_path:
            core.export_config(file_path, config)
            self._set_status("Exported: {}".format(
                os.path.basename(file_path)
            ))

    def _export_mirror_config(self):
        """Export mirrored config to file."""
        config = self._build_config_from_ui()
        if not config:
            return

        search = self.search_edit.text()
        replace = self.replace_edit.text()
        negate = self._get_negate_channels()

        mirrored = core.mirror_config(
            config, search, replace, negate
        )

        file_path = self._get_save_path()
        if file_path:
            core.export_config(file_path, mirrored)
            self._set_status("Exported mirror: {}".format(
                os.path.basename(file_path)
            ))

    def _import_config(self):
        """Import config file and populate UI."""
        file_path = self._get_open_path()
        if not file_path:
            return

        config = core.import_config(file_path)
        if not config:
            return

        self._populate_ui_from_config(config)
        self._set_status("Imported: {}".format(
            os.path.basename(file_path)
        ))

    def _apply_from_file(self):
        """Apply config directly from file (no UI update)."""
        file_path = self._get_open_path()
        if not file_path:
            return

        result = core.apply_from_file(file_path)
        if result:
            self._set_status(
                "Applied from file ({} nodes)".format(len(result))
            )

    # =============================================================
    # HELPERS
    # =============================================================

    def _get_controls(self):
        """Get the list of controls from the UI.

        Returns:
            list: Control name strings.
        """
        return [
            self.controls_list.item(i).text()
            for i in range(self.controls_list.count())
        ]

    def _get_pose_data(self):
        """Get pose names and frames from the tree.

        Returns:
            tuple: (frames list, pose_names list).
        """
        frames = []
        names = []
        for i in range(self.poses_tree.topLevelItemCount()):
            item = self.poses_tree.topLevelItem(i)
            frames.append(float(item.text(0)))
            names.append(item.text(1))
        return frames, names

    def _get_negate_channels(self):
        """Get the list of checked negate channels.

        Returns:
            list: Channel name strings.
        """
        return [
            ch for ch, cb in self.negate_checks.items()
            if cb.isChecked()
        ]

    def _build_config_from_ui(self):
        """Build a config dict from current UI state.

        Reads pose delta values from the current scene.

        Returns:
            dict: Configuration, or None on failure.
        """
        ui_host = self.ui_host_edit.text().strip()
        if not ui_host:
            cmds.warning("SDK Creator: No UIHost specified")
            return None

        controls = self._get_controls()
        if not controls:
            cmds.warning("SDK Creator: No controls in list")
            return None

        frames, pose_names = self._get_pose_data()
        if not frames:
            cmds.warning(
                "SDK Creator: No poses detected. "
                "Click 'Detect Poses' first"
            )
            return None

        # Read fresh pose data from scene
        poses = core.collect_pose_data(controls, frames, pose_names)

        return core.build_config(
            ui_host, controls, poses,
            self.min_spin.value(), self.max_spin.value(),
        )

    def _populate_ui_from_config(self, config):
        """Populate UI fields from an imported config.

        Args:
            config (dict): Configuration dictionary.
        """
        self.ui_host_edit.setText(config.get("ui_host", ""))

        range_vals = config.get("range", [0.0, 1.0])
        self.min_spin.setValue(range_vals[0])
        self.max_spin.setValue(range_vals[1])

        self.controls_list.clear()
        for ctl in config.get("controls", []):
            self.controls_list.addItem(ctl)

        self.poses_tree.clear()
        for pose_name, pose_data in config.get("poses", {}).items():
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, str(int(pose_data.get("frame", 0))))
            item.setFlags(
                item.flags() | QtCore.Qt.ItemIsEditable
            )
            item.setText(1, pose_name)
            self.poses_tree.addTopLevelItem(item)

    def _get_save_path(self):
        """Show save file dialog for .sdkc files.

        Returns:
            str: File path, or None if cancelled.
        """
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export SDK Config",
            "",
            "SDK Creator Config (*{})".format(core.CONFIG_EXT),
        )
        return path if path else None

    def _get_open_path(self):
        """Show open file dialog for .sdkc files.

        Returns:
            str: File path, or None if cancelled.
        """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import SDK Config",
            "",
            "SDK Creator Config (*{})".format(core.CONFIG_EXT),
        )
        return path if path else None

    def _set_status(self, text, error=False):
        """Update the status label.

        Args:
            text (str): Status message.
            error (bool): If True, show in red.
        """
        color = "#cc6666" if error else "#7aad7a"
        self.status_label.setStyleSheet(
            "color: {};".format(color)
        )
        self.status_label.setText(text)

    # =============================================================
    # WINDOW LIFECYCLE
    # =============================================================

    def _save_state(self):
        """Save window state."""
        if self._closing:
            return
        self._closing = True
        self.save_settings()

    def closeEvent(self, event):
        """Handle close event."""
        self._save_state()
        super(SDKCreatorUI, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        """Handle dock close event."""
        self._save_state()
        super(SDKCreatorUI, self).dockCloseEventTriggered()
