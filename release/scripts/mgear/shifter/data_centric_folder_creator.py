"""Data-Centric Folder Structure Creator.

Creates a data-centric folder hierarchy on disk for Maya rigs.
Supports export/import of configurations (.dcf files), live folder
preview, drag-and-drop config loading, and persistent UI settings.

Example:
    from mgear.shifter import data_centric_folder_creator as dcfc
    dcfc.openFolderStructureCreator()
"""

import json
import os
import re

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.core import pyqt
from mgear.core import widgets
from mgear.core.pyqt import dpi_scale

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

CONFIG_FILE_EXT = ".dcf"
CONFIG_FILTER = "数据中心文件夹 (*{})".format(CONFIG_FILE_EXT)

# Characters not allowed in folder names (Windows + Unix)
_INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

DEFAULT_CONFIG = {
    "path": "",
    "custom_step_folder": "custom_steps",
    "data_folder": "data",
    "type": "char",
    "name": "",
    "variant": ["default"],
    "target": ["layout", "anim"],
}

DATA_SUB_DIRS = ("data", "assets")
CUSTOM_STEP_SUB_DIRS = ("pre", "post")

# Cached QBrush objects for preview tree coloring
_BRUSH_ROOT = QtGui.QBrush(QtGui.QColor("#e0c080"))
_BRUSH_TYPE = QtGui.QBrush(QtGui.QColor("#80c0e0"))
_BRUSH_NAME = QtGui.QBrush(QtGui.QColor("#a0e0a0"))
_BRUSH_VARIANT = QtGui.QBrush(QtGui.QColor("#c0a0e0"))
_BRUSH_SHARED = QtGui.QBrush(QtGui.QColor("#888888"))


def _iter_root_folders(config):
    """Yield (folder_name, sub_dirs) for each root folder in the config.

    Handles the case where both folder names are the same by using
    explicit sub_dirs assignment instead of identity comparison.

    Args:
        config (dict): Configuration dictionary.

    Yields:
        tuple: (folder_name, sub_dirs) pairs.
    """
    yield config["custom_step_folder"], CUSTOM_STEP_SUB_DIRS
    yield config["data_folder"], DATA_SUB_DIRS


def normalize_multi_entry(text):
    """Normalize a multi-entry text field to comma-separated values.

    Converts spaces and commas to a clean comma-separated list.
    Strips whitespace, removes empty entries, and removes duplicates
    while preserving order.

    Args:
        text (str): Raw text from a QLineEdit.

    Returns:
        list: Cleaned list of unique, non-empty strings.
    """
    parts = text.replace(",", " ").split()
    seen = set()
    result = []
    for p in parts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


class FolderStructureCreatorUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):

    toolName = "mGearDataCentricFolderCreator"
    TOOL_TITLE = "数据中心文件夹结构创建器"

    def __init__(self, parent=None):
        super(FolderStructureCreatorUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self.setObjectName(self.toolName)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAcceptDrops(True)

        if cmds.about(ntOS=True):
            flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        # Members
        self.menu_bar = None
        self.import_action = None
        self.export_action = None
        self.path_le = None
        self.path_btn = None
        self.custom_step_le = None
        self.data_folder_le = None
        self.type_le = None
        self.name_le = None
        self.variant_le = None
        self.target_le = None
        self.preview_section = None
        self.preview_tree = None
        self.create_btn = None
        self.status_label = None
        self.debounce_timer = None

        self.setup_ui()

        self.setMinimumWidth(int(dpi_scale(280)))
        self.resize(int(dpi_scale(420)), int(dpi_scale(500)))

        self.user_settings = {
            "dcfc/path": (self.path_le, ""),
            "dcfc/custom_step_folder": (
                self.custom_step_le,
                "custom_steps",
            ),
            "dcfc/data_folder": (self.data_folder_le, "data"),
            "dcfc/type": (self.type_le, "char"),
            "dcfc/name": (self.name_le, ""),
            "dcfc/variant": (self.variant_le, "default"),
            "dcfc/target": (self.target_le, "layout, anim"),
        }
        # Block signals during settings load to avoid cascading
        # save_settings and preview refreshes per field
        all_fields = (
            self.path_le,
            self.custom_step_le,
            self.data_folder_le,
            self.type_le,
            self.name_le,
            self.variant_le,
            self.target_le,
        )
        for le in all_fields:
            le.blockSignals(True)
        self.load_settings()
        for le in all_fields:
            le.blockSignals(False)
        self._do_refresh_preview()

    def setup_ui(self):
        """Orchestrate UI creation."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_actions(self):
        """Create menu actions."""
        self.import_action = QtWidgets.QAction("导入配置...", self)
        self.import_action.setShortcut(QtGui.QKeySequence.Open)

        self.export_action = QtWidgets.QAction("导出配置...", self)
        self.export_action.setShortcut(QtGui.QKeySequence.Save)

    def create_widgets(self):
        """Create all UI widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        file_menu = self.menu_bar.addMenu("文件")
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.export_action)

        # Root Path
        self.path_le = QtWidgets.QLineEdit()
        self.path_le.setPlaceholderText(
            "选择数据中心结构的根文件夹..."
        )
        self.path_btn = widgets.create_button(icon="mgear_folder", width=25)

        # Folder Settings
        self.custom_step_le = QtWidgets.QLineEdit()
        self.custom_step_le.setPlaceholderText("custom_steps")
        self.data_folder_le = QtWidgets.QLineEdit()
        self.data_folder_le.setPlaceholderText("data")

        folder_tooltip = (
            "两个文件夹可以同名。它们被分开"
            "是为了方便，这样你可以单独在"
            "custom_steps/scripts文件夹上使用Git。"
        )
        self.custom_step_le.setToolTip(folder_tooltip)
        self.data_folder_le.setToolTip(folder_tooltip)

        # Settings
        self.type_le = QtWidgets.QLineEdit()
        self.type_le.setPlaceholderText("例如：角色、道具、环境")
        self.name_le = QtWidgets.QLineEdit()
        self.name_le.setPlaceholderText(
            "例如：英雄、反派（逗号或空格分隔）"
        )
        self.variant_le = QtWidgets.QLineEdit()
        self.variant_le.setPlaceholderText(
            "例如：默认、损坏（逗号或空格分隔）"
        )
        self.target_le = QtWidgets.QLineEdit()
        self.target_le.setPlaceholderText(
            "e.g. layout, anim (comma or space separated)"
        )

        # Folder Preview
        self.preview_section = widgets.CollapsibleWidget(
            "Folder Preview", expanded=True
        )
        self.preview_tree = QtWidgets.QTreeWidget()
        self.preview_tree.setHeaderHidden(True)
        self.preview_tree.setIndentation(int(dpi_scale(16)))
        self.preview_tree.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.preview_section.addWidget(self.preview_tree)

        # Create button
        self.create_btn = QtWidgets.QPushButton("Create Folder Structure")
        self.create_btn.setMinimumHeight(int(dpi_scale(40)))
        self.create_btn.setStyleSheet(
            "QPushButton { background-color: #4a7c4e; font-weight: bold; }"
            "QPushButton:hover { background-color: #5a9c5e; }"
            "QPushButton:pressed { background-color: #3a6c3e; }"
        )

        # Status label
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet(
            "color: #888888; font-style: italic;"
        )

        # Debounce timer for preview refresh
        self.debounce_timer = QtCore.QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)

    def create_layout(self):
        """Arrange widgets in layouts."""
        m = int(dpi_scale(6))
        sp = int(dpi_scale(4))

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(m, m, m, m)
        main_layout.setSpacing(sp)
        main_layout.setMenuBar(self.menu_bar)

        # Root Path group
        root_path_group = QtWidgets.QGroupBox("Root Path")
        root_path_layout = QtWidgets.QHBoxLayout()
        root_path_layout.setContentsMargins(m, m, m, m)
        root_path_layout.addWidget(self.path_le)
        root_path_layout.addWidget(self.path_btn)
        root_path_group.setLayout(root_path_layout)

        # Folder Settings group
        folder_group = QtWidgets.QGroupBox("Folder Settings")
        folder_layout = QtWidgets.QFormLayout()
        folder_layout.setContentsMargins(m, m, m, m)
        folder_layout.setSpacing(sp)
        folder_layout.addRow("Custom Step Folder:", self.custom_step_le)
        folder_layout.addRow("Data Folder:", self.data_folder_le)
        folder_group.setLayout(folder_layout)

        # Settings group
        settings_group = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout()
        settings_layout.setContentsMargins(m, m, m, m)
        settings_layout.setSpacing(sp)
        settings_layout.addRow("Type:", self.type_le)
        settings_layout.addRow("Name:", self.name_le)
        settings_layout.addRow("Variant:", self.variant_le)
        settings_layout.addRow("Target:", self.target_le)
        settings_group.setLayout(settings_layout)

        main_layout.addWidget(root_path_group)
        main_layout.addWidget(folder_group)
        main_layout.addWidget(settings_group)
        main_layout.addWidget(self.preview_section, stretch=1)
        main_layout.addWidget(self.create_btn)
        main_layout.addWidget(self.status_label)

    def create_connections(self):
        """Wire signals to slots."""
        self.import_action.triggered.connect(self.import_config)
        self.export_action.triggered.connect(self.export_config)
        self.path_btn.clicked.connect(self._set_root_path)
        self.create_btn.clicked.connect(self.create_folder_structure)

        # Debounced preview refresh on any field change
        for le in (
            self.path_le,
            self.custom_step_le,
            self.data_folder_le,
            self.type_le,
            self.name_le,
            self.variant_le,
            self.target_le,
        ):
            le.textChanged.connect(self._refresh_preview)

        # Normalize multi-entry fields on editing finished
        for le in (
            self.type_le,
            self.name_le,
            self.variant_le,
            self.target_le,
        ):
            le.editingFinished.connect(
                lambda w=le: self._normalize_field(w)
            )

        self.debounce_timer.timeout.connect(self._do_refresh_preview)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _build_config_from_ui(self):
        """Build a config dict from current UI field values.

        Returns:
            dict: Configuration dictionary ready for folder creation
                or export.
        """
        d = DEFAULT_CONFIG
        return {
            "path": self.path_le.text().strip(),
            "custom_step_folder": (
                self.custom_step_le.text().strip()
                or d["custom_step_folder"]
            ),
            "data_folder": (
                self.data_folder_le.text().strip() or d["data_folder"]
            ),
            "type": self.type_le.text().strip() or d["type"],
            "name": normalize_multi_entry(self.name_le.text()),
            "variant": (
                normalize_multi_entry(self.variant_le.text())
                or list(d["variant"])
            ),
            "target": (
                normalize_multi_entry(self.target_le.text())
                or list(d["target"])
            ),
        }

    def _populate_ui_from_config(self, config):
        """Populate all UI fields from a config dict.

        Args:
            config (dict): Configuration dictionary.
        """
        d = DEFAULT_CONFIG
        all_fields = (
            self.path_le,
            self.custom_step_le,
            self.data_folder_le,
            self.type_le,
            self.name_le,
            self.variant_le,
            self.target_le,
        )
        # Block signals to avoid cascading saves and preview refreshes
        for le in all_fields:
            le.blockSignals(True)

        self.path_le.setText(config.get("path", d["path"]))
        self.custom_step_le.setText(
            config.get("custom_step_folder", d["custom_step_folder"])
        )
        self.data_folder_le.setText(
            config.get("data_folder", d["data_folder"])
        )
        self.type_le.setText(config.get("type", d["type"]))

        name = config.get("name", d["name"])
        if isinstance(name, list):
            name = ", ".join(name)
        self.name_le.setText(name)

        variant = config.get("variant", d["variant"])
        if isinstance(variant, list):
            variant = ", ".join(variant)
        self.variant_le.setText(variant)

        target = config.get("target", d["target"])
        if isinstance(target, list):
            target = ", ".join(target)
        self.target_le.setText(target)

        for le in all_fields:
            le.blockSignals(False)

        self.save_settings()
        self._do_refresh_preview()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self):
        """Schedule a debounced preview refresh."""
        self.debounce_timer.start()

    def _do_refresh_preview(self):
        """Rebuild the folder preview tree from current UI values."""
        self.preview_tree.clear()
        config = self._build_config_from_ui()
        names = config["name"]
        if not names:
            return

        asset_type = config["type"]
        variants = config["variant"]
        targets = config["target"]

        for folder_name, sub_dirs in _iter_root_folders(config):
            root_item = QtWidgets.QTreeWidgetItem([folder_name + "/"])
            root_item.setForeground(0, _BRUSH_ROOT)
            self.preview_tree.addTopLevelItem(root_item)
            self._add_shared_item(root_item, sub_dirs)

            type_item = QtWidgets.QTreeWidgetItem([asset_type + "/"])
            type_item.setForeground(0, _BRUSH_TYPE)
            root_item.addChild(type_item)
            self._add_shared_item(type_item, sub_dirs)

            for name in names:
                name_item = QtWidgets.QTreeWidgetItem([name + "/"])
                name_item.setForeground(0, _BRUSH_NAME)
                type_item.addChild(name_item)
                self._add_shared_item(name_item, sub_dirs)

                for variant in variants:
                    var_item = QtWidgets.QTreeWidgetItem([variant + "/"])
                    var_item.setForeground(0, _BRUSH_VARIANT)
                    name_item.addChild(var_item)
                    self._add_shared_item(var_item, sub_dirs)

                    for target in targets:
                        tgt_item = QtWidgets.QTreeWidgetItem(
                            [target + "/"]
                        )
                        var_item.addChild(tgt_item)
                        for sd in sub_dirs:
                            tgt_item.addChild(
                                QtWidgets.QTreeWidgetItem([sd + "/"])
                            )

        self.preview_tree.expandAll()

    def _add_shared_item(self, parent, sub_dirs):
        """Add a _shared/ node with sub-directories.

        Args:
            parent (QTreeWidgetItem): Parent tree item.
            sub_dirs (tuple): Sub-directory names.
        """
        shared = QtWidgets.QTreeWidgetItem(["_shared/"])
        shared.setForeground(0, _BRUSH_SHARED)
        parent.addChild(shared)
        for sd in sub_dirs:
            shared.addChild(QtWidgets.QTreeWidgetItem([sd + "/"]))

    # ------------------------------------------------------------------
    # Field normalization
    # ------------------------------------------------------------------

    def _normalize_field(self, line_edit):
        """Normalize a multi-entry QLineEdit on editing finished.

        Args:
            line_edit (QLineEdit): The field to normalize.
        """
        text = line_edit.text()
        entries = normalize_multi_entry(text)
        normalized = ", ".join(entries)
        if normalized != text:
            line_edit.setText(normalized)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def import_config(self):
        """Import configuration from a .dcf file."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Config", "", CONFIG_FILTER
        )
        if file_path:
            self._load_config_from_file(file_path)

    def export_config(self):
        """Export current UI configuration to a .dcf file."""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Config", "", CONFIG_FILTER
        )
        if file_path:
            if not file_path.endswith(CONFIG_FILE_EXT):
                file_path += CONFIG_FILE_EXT
            config = self._build_config_from_ui()
            with open(file_path, "w") as f:
                json.dump(config, f, indent=4)
            self._set_status("Config exported: {}".format(file_path))

    def _load_config_from_file(self, file_path):
        """Load a config file and populate the UI.

        Args:
            file_path (str): Path to .dcf file.
        """
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
        except (IOError, ValueError) as e:
            self._set_status("Error loading config: {}".format(e), error=True)
            cmds.warning("Failed to load config: {}".format(e))
            return

        self._populate_ui_from_config(config)
        self._set_status("Config loaded: {}".format(file_path))

    # ------------------------------------------------------------------
    # Drag and Drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        """Accept drag events for .dcf files."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(CONFIG_FILE_EXT):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event):
        """Handle dropped .dcf files."""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(CONFIG_FILE_EXT):
                self._load_config_from_file(path)
                break

    # ------------------------------------------------------------------
    # Root path
    # ------------------------------------------------------------------

    def _set_root_path(self):
        """Browse for root folder."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Root Folder"
        )
        if directory:
            self.path_le.setText(directory)

    # ------------------------------------------------------------------
    # Folder creation
    # ------------------------------------------------------------------

    def create_folder_structure(self):
        """Create the folder structure on disk from current UI values."""
        config = self._build_config_from_ui()
        base_path = config["path"]

        # Validation
        if not base_path:
            self._set_status("Root path is required.", error=True)
            cmds.warning("Root path is required.")
            return

        names = config["name"]
        if not names:
            self._set_status("At least one name is required.", error=True)
            cmds.warning("At least one name is required.")
            return

        asset_type = config["type"]
        if not asset_type:
            self._set_status("Type is required.", error=True)
            cmds.warning("Type is required.")
            return

        variants = config["variant"]
        targets = config["target"]
        custom_step = config["custom_step_folder"]
        data_folder = config["data_folder"]

        # Validate folder names for invalid characters
        all_names = (
            [custom_step, data_folder, asset_type]
            + names
            + variants
            + targets
        )
        for n in all_names:
            if _INVALID_CHARS_RE.search(n):
                msg = "Invalid characters in folder name: '{}'".format(n)
                self._set_status(msg, error=True)
                cmds.warning(msg)
                return

        def _make_leaf(path, sub_dirs):
            for sd in sub_dirs:
                os.makedirs(os.path.join(path, sd), exist_ok=True)

        for root_folder, sub_dirs in _iter_root_folders(config):
            root_shared = os.path.join(base_path, root_folder, "_shared")
            _make_leaf(root_shared, sub_dirs)

            type_shared = os.path.join(
                base_path, root_folder, asset_type, "_shared"
            )
            _make_leaf(type_shared, sub_dirs)

            for name in names:
                name_shared = os.path.join(
                    base_path, root_folder, asset_type, name, "_shared"
                )
                _make_leaf(name_shared, sub_dirs)

                for variant in variants:
                    var_shared = os.path.join(
                        base_path,
                        root_folder,
                        asset_type,
                        name,
                        variant,
                        "_shared",
                    )
                    _make_leaf(var_shared, sub_dirs)

                    for target in targets:
                        tgt_path = os.path.join(
                            base_path,
                            root_folder,
                            asset_type,
                            name,
                            variant,
                            target,
                        )
                        _make_leaf(tgt_path, sub_dirs)

        self._set_status("Folder structure created successfully.")
        QtWidgets.QMessageBox.information(
            self,
            "Success",
            "Data-Centric folder structure created successfully.",
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, message, error=False):
        """Update the status label.

        Args:
            message (str): Status message text.
            error (bool, optional): If True, show in red.
        """
        if error:
            self.status_label.setStyleSheet(
                "color: #ff6666; font-style: italic;"
            )
        else:
            self.status_label.setStyleSheet(
                "color: #88cc88; font-style: italic;"
            )
        self.status_label.setText(message)


def openFolderStructureCreator(*args):
    pyqt.showDialog(FolderStructureCreatorUI, dockable=True)


if __name__ == "__main__":
    openFolderStructureCreator()
