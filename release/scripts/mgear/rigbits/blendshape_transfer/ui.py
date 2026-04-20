"""Blendshape Transfer - Main UI Module.

Dockable dialog for configuring and executing multi-source
blendshape transfers with import/export of .bst configs.
"""

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore

from mgear.core import pyqt

from . import core


class BlendshapeTransferUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for the Blendshape Transfer tool.

    Provides target mesh selection, source mesh list management,
    transfer options, and import/export of .bst config files.
    """

    TOOL_NAME = "BlendshapeTransfer"
    TOOL_TITLE = "Blendshape Setup Transfer"

    def __init__(self, parent=None):
        super(BlendshapeTransferUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self._closing = False

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumWidth(int(pyqt.dpi_scale(400)))

        if cmds.about(ntOS=True):
            flags = (
                self.windowFlags()
                ^ QtCore.Qt.WindowContextHelpButtonHint
            )
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.setup_ui()
        self.resize(
            int(pyqt.dpi_scale(450)),
            int(pyqt.dpi_scale(500)),
        )

    # =================================================================
    # UI SETUP
    # =================================================================

    def setup_ui(self):
        """Build the UI layout."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_actions(self):
        """Create QActions for menus."""
        self.import_action = QtWidgets.QAction(
            "Import Config...", self
        )
        self.export_action = QtWidgets.QAction(
            "Export Config...", self
        )

    def create_widgets(self):
        """Create all UI widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        self.file_menu = self.menu_bar.addMenu("文件")
        self.file_menu.addAction(self.import_action)
        self.file_menu.addAction(self.export_action)

        # Target mesh
        self.target_label = QtWidgets.QLabel("Target Mesh:")
        self.target_edit = QtWidgets.QLineEdit()
        self.target_edit.setPlaceholderText(
            "Select target mesh"
        )
        self.target_btn = QtWidgets.QPushButton("<<")
        self.target_btn.setFixedWidth(int(pyqt.dpi_scale(30)))
        self.target_btn.setToolTip("Load from selection")

        # Source meshes
        self.source_list = QtWidgets.QListWidget()
        self.source_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.add_source_btn = QtWidgets.QPushButton(
            "Add from Selection"
        )
        self.add_source_btn.setStyleSheet(
            "background-color: #4a7c4e;"
        )
        self.remove_source_btn = QtWidgets.QPushButton("移除")
        self.remove_source_btn.setStyleSheet(
            "background-color: #7c4a4a;"
        )

        # Options
        self.bs_name_label = QtWidgets.QLabel("BS Node Name:")
        self.bs_name_edit = QtWidgets.QLineEdit()
        self.bs_name_edit.setPlaceholderText(
            "Auto: <target>_BS"
        )
        self.reconnect_check = QtWidgets.QCheckBox(
            "Reconnect connections"
        )
        self.reconnect_check.setChecked(True)

        # Execute
        self.execute_btn = QtWidgets.QPushButton(
            "Execute Transfer"
        )
        self.execute_btn.setMinimumHeight(
            int(pyqt.dpi_scale(50))
        )
        self.execute_btn.setStyleSheet(
            "background-color: #4a7c4e;"
            "font-weight: bold;"
            "font-size: 14px;"
        )

        # Status
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #888;")

    def create_layout(self):
        """Arrange widgets in layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        main_layout.setMenuBar(self.menu_bar)

        # Target mesh group
        target_group = QtWidgets.QGroupBox("Target Mesh")
        target_layout = QtWidgets.QHBoxLayout(target_group)
        target_layout.addWidget(self.target_label)
        target_layout.addWidget(self.target_edit, stretch=1)
        target_layout.addWidget(self.target_btn)
        main_layout.addWidget(target_group)

        # Source meshes group
        source_group = QtWidgets.QGroupBox("Source Meshes")
        source_layout = QtWidgets.QVBoxLayout(source_group)
        source_layout.addWidget(self.source_list)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.add_source_btn)
        btn_row.addWidget(self.remove_source_btn)
        source_layout.addLayout(btn_row)
        main_layout.addWidget(source_group, stretch=1)

        # Options group
        options_group = QtWidgets.QGroupBox("选项")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(self.bs_name_label)
        name_row.addWidget(self.bs_name_edit, stretch=1)
        options_layout.addLayout(name_row)
        options_layout.addWidget(self.reconnect_check)
        main_layout.addWidget(options_group)

        # Execute
        main_layout.addWidget(self.execute_btn)
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Connect signals to slots."""
        self.import_action.triggered.connect(
            self._import_config
        )
        self.export_action.triggered.connect(
            self._export_config
        )
        self.target_btn.clicked.connect(
            self._load_target_from_selection
        )
        self.add_source_btn.clicked.connect(
            self._add_sources_from_selection
        )
        self.remove_source_btn.clicked.connect(
            self._remove_selected_sources
        )
        self.execute_btn.clicked.connect(self._execute)

    # =================================================================
    # SELECTION HELPERS
    # =================================================================

    def _load_target_from_selection(self):
        """Set target mesh from Maya selection."""
        sel = cmds.ls(selection=True, type="transform")
        if sel:
            self.target_edit.setText(sel[0])
        else:
            cmds.warning("Select a mesh transform")

    def _add_sources_from_selection(self):
        """Add selected meshes to the source list."""
        sel = cmds.ls(selection=True, type="transform")
        if not sel:
            cmds.warning("Select mesh transforms to add")
            return

        existing = set(
            self.source_list.item(i).text()
            for i in range(self.source_list.count())
        )
        for item in sel:
            if item not in existing:
                self.source_list.addItem(item)

    def _remove_selected_sources(self):
        """Remove selected items from the source list."""
        for item in reversed(self.source_list.selectedItems()):
            row = self.source_list.row(item)
            self.source_list.takeItem(row)

    # =================================================================
    # CONFIG I/O
    # =================================================================

    def _get_sources(self):
        """Get list of source mesh names from the UI.

        Returns:
            list: Source mesh name strings.
        """
        return [
            self.source_list.item(i).text()
            for i in range(self.source_list.count())
        ]

    def _build_config(self):
        """Build config dict from current UI state.

        Returns:
            dict: Configuration dictionary.
        """
        return {
            "target_mesh": self.target_edit.text().strip(),
            "source_meshes": self._get_sources(),
            "bs_node_name": (
                self.bs_name_edit.text().strip() or ""
            ),
            "reconnect": self.reconnect_check.isChecked(),
        }

    def _populate_from_config(self, config):
        """Populate UI fields from a config dict.

        Args:
            config (dict): Configuration dictionary.
        """
        self.target_edit.setText(
            config.get("target_mesh", "")
        )
        self.source_list.clear()
        for src in config.get("source_meshes", []):
            self.source_list.addItem(src)
        self.bs_name_edit.setText(
            config.get("bs_node_name", "")
        )
        self.reconnect_check.setChecked(
            config.get("reconnect", True)
        )

        name = config.get("name", "")
        if name:
            self.status_label.setText(
                "Loaded: {}".format(name)
            )

    def _import_config(self):
        """Import a .bst config file and populate the UI."""
        filepath = cmds.fileDialog2(
            fileMode=1,
            fileFilter="Blendshape Transfer Config .bst "
            "(*{})".format(core.BST_EXT),
        )
        if not filepath:
            return

        config = core.import_config(filepath[0])
        if config:
            self._populate_from_config(config)

    def _export_config(self):
        """Export current UI state to a .bst config file."""
        filepath = cmds.fileDialog2(
            fileMode=0,
            fileFilter="Blendshape Transfer Config .bst "
            "(*{})".format(core.BST_EXT),
        )
        if not filepath:
            return

        config = self._build_config()
        metadata = {
            "name": config.get("bs_node_name", ""),
        }
        result = core.export_config(
            filepath[0],
            target=config["target_mesh"],
            sources=config["source_meshes"],
            bs_node_name=config["bs_node_name"] or None,
            reconnect=config["reconnect"],
            metadata=metadata,
        )
        if result:
            self.status_label.setText(
                "Exported: {}".format(filepath[0])
            )

    # =================================================================
    # EXECUTION
    # =================================================================

    def _execute(self):
        """Run the blendshape transfer."""
        config = self._build_config()

        if not config["target_mesh"]:
            cmds.warning("No target mesh specified")
            return
        if not config["source_meshes"]:
            cmds.warning("No source meshes specified")
            return

        self.status_label.setText("Transferring...")
        self.status_label.repaint()

        result = core.run_from_config(config)

        if result:
            self.status_label.setText(
                "Done: created {}".format(result)
            )
            self.status_label.setStyleSheet("color: #6a6;")
        else:
            self.status_label.setText(
                "No targets transferred"
            )
            self.status_label.setStyleSheet("color: #a66;")

    # =================================================================
    # WINDOW LIFECYCLE
    # =================================================================

    def _save_state(self):
        """Save window state (guarded against double calls)."""
        if self._closing:
            return
        self._closing = True
        self.save_settings()

    def closeEvent(self, event):
        """Handle close event."""
        self._save_state()
        super(BlendshapeTransferUI, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self._save_state()
        super(
            BlendshapeTransferUI, self
        ).dockCloseEventTriggered()
