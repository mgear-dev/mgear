"""Guide Template Manager - Main UI Module.

Dockable dialog for browsing, importing, and managing Shifter
guide templates (.sgt files) with metadata and thumbnails.
"""

import json
import os

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import mgear.pymaya as pm
from mgear.core import pyqt

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore

from mgear.shifter import io as shifter_io

from . import core
from .widgets import ImportPartialDialog
from .widgets import SourceFoldersDialog
from .widgets import TemplateInfoPanel
from .widgets import TemplateTreeWidget

# Settings keys
_SK_SOURCE_FOLDERS = "templateManager/source_folders"
_SK_SPLITTER = "templateManager/splitter"
_SK_SHOW_DEFAULTS = "templateManager/show_defaults"


class GuideTemplateManagerUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for the Guide Template Manager.

    Dockable dialog with a tree browser on the left and an info
    panel on the right.  Supports import, import-add, import-partial,
    export, viewport screenshot capture, and custom source folders.
    """

    TOOL_NAME = "GuideTemplateManager"
    TOOL_TITLE = "引导模板管理器"

    def __init__(self, parent=None):
        super(GuideTemplateManagerUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self._source_folders = []
        self._closing = False

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumSize(500, 400)

        if cmds.about(ntOS=True):
            flags = (
                self.windowFlags()
                ^ QtCore.Qt.WindowContextHelpButtonHint
            )
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.setup_ui()

        self._source_folders = json.loads(
            self.settings.value(_SK_SOURCE_FOLDERS, "[]")
        )

        self.user_settings = {
            _SK_SHOW_DEFAULTS: (
                self.show_defaults_action,
                True,
            ),
        }
        self.load_settings()

        splitter_state = self.settings.value(_SK_SPLITTER)
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        self.resize(800, 500)

        self.refresh_templates()

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
        self.export_action = QtWidgets.QAction(
            "导出模板...", self
        )
        self.refresh_action = QtWidgets.QAction(
            "刷新列表", self
        )
        self.edit_folders_action = QtWidgets.QAction(
            "编辑源文件夹...", self
        )
        self.show_defaults_action = QtWidgets.QAction(
            "显示默认引导", self
        )
        self.show_defaults_action.setCheckable(True)
        self.show_defaults_action.setChecked(True)

    def create_widgets(self):
        """Create all UI widgets."""
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.file_menu = self.menu_bar.addMenu("文件")
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.refresh_action)

        self.settings_menu = self.menu_bar.addMenu("设置")
        self.settings_menu.addAction(self.edit_folders_action)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.show_defaults_action)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜索模板...")
        self.search_input.setClearButtonEnabled(True)

        self.template_tree = TemplateTreeWidget()
        self.info_panel = TemplateInfoPanel()

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.template_tree)
        self.splitter.addWidget(self.info_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

    def create_layout(self):
        """Arrange widgets in layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        main_layout.setMenuBar(self.menu_bar)

        main_layout.addWidget(self.search_input)
        main_layout.addWidget(self.splitter, stretch=1)

    def create_connections(self):
        """Connect signals to slots."""
        self.export_action.triggered.connect(self.export_template)
        self.refresh_action.triggered.connect(self.refresh_templates)
        self.edit_folders_action.triggered.connect(
            self.edit_source_folders
        )
        self.show_defaults_action.toggled.connect(
            lambda *args: self.refresh_templates()
        )

        self.search_input.textChanged.connect(self._filter_templates)

        self.template_tree.template_selected.connect(
            self._on_template_selected
        )
        self.template_tree.import_requested.connect(
            self._on_import
        )
        self.template_tree.import_add_requested.connect(
            self._on_import_add
        )
        self.template_tree.import_partial_requested.connect(
            self._on_import_partial
        )

    # =================================================================
    # TEMPLATE BROWSING
    # =================================================================

    def refresh_templates(self):
        """Rebuild the template tree from all source folders."""
        folder_paths = []

        if self.show_defaults_action.isChecked():
            default_dir = core.get_default_templates_dir()
            if os.path.isdir(default_dir):
                folder_paths.append(default_dir)

        folder_paths.extend(self._source_folders)

        folder_entries = core.scan_template_folders(folder_paths)

        for entry in folder_entries:
            if entry.path == core.get_default_templates_dir():
                entry.label = "默认模板"

        # Ensure sgtInfo and cache before populating tree
        core.ensure_all_sgt_info(folder_entries)

        self.template_tree.populate(folder_entries)

        search_text = self.search_input.text()
        if search_text:
            self.template_tree.filter_by_text(search_text)

    def _filter_templates(self, text):
        """Filter the tree by search text.

        Args:
            text (str): Search text.
        """
        self.template_tree.filter_by_text(text)

    def _on_template_selected(self, sgt_path):
        """Handle template selection in the tree.

        Args:
            sgt_path (str): Path to the selected .sgt file.
        """
        self.info_panel.set_template(sgt_path)

    # =================================================================
    # IMPORT ACTIONS
    # =================================================================

    def _on_import(self, sgt_path):
        """Import a template as a new guide.

        Args:
            sgt_path (str): Path to the .sgt file.
        """
        shifter_io.import_guide_template(filePath=sgt_path)

    def _on_import_add(self, sgt_path):
        """Import a template as a child of the selected guide element.

        Args:
            sgt_path (str): Path to the .sgt file.
        """
        selection = pm.selected()
        if not selection:
            cmds.warning(
                "请选择一个要添加到的引导元素"
            )
            return

        init_parent = selection[0]
        shifter_io.import_partial_guide(
            filePath=sgt_path, initParent=init_parent
        )

    def _on_import_partial(self, sgt_path):
        """Open the partial import dialog for component selection.

        Args:
            sgt_path (str): Path to the .sgt file.
        """
        components = core.get_components_from_template(sgt_path)
        if not components:
            cmds.warning(
                "无法从模板读取组件"
            )
            return

        dialog = ImportPartialDialog(components, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        roots = dialog.get_root_components()
        if not roots:
            cmds.warning("未选择组件")
            return

        init_parent = None
        selection = pm.selected()
        if selection:
            init_parent = selection[0]

        match_position = (
            dialog.get_action() == ImportPartialDialog.IMPORT_MATCH
        )

        target_pos = None
        if match_position and init_parent:
            target_pos = cmds.xform(
                str(init_parent),
                query=True,
                worldSpace=True,
                translation=True,
            )

        existing_roots = set(
            cmds.ls("*_root", type="transform", long=True)
        )

        shifter_io.import_partial_guide(
            filePath=sgt_path,
            partial=roots,
            initParent=init_parent,
        )

        if target_pos and match_position:
            current_roots = set(
                cmds.ls("*_root", type="transform", long=True)
            )
            new_roots = current_roots - existing_roots
            if new_roots:
                first_root = sorted(new_roots)[0]
                cmds.xform(
                    first_root,
                    worldSpace=True,
                    translation=target_pos,
                )

    # =================================================================
    # EXPORT
    # =================================================================

    def export_template(self):
        """Export the current guide as a template."""
        shifter_io.export_guide_template()

    # =================================================================
    # SOURCE FOLDERS
    # =================================================================

    def edit_source_folders(self):
        """Open the source folders management dialog."""
        dialog = SourceFoldersDialog(self._source_folders, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._source_folders = dialog.get_folders()
            self.settings.setValue(
                _SK_SOURCE_FOLDERS,
                json.dumps(self._source_folders),
            )
            self.refresh_templates()

    # =================================================================
    # WINDOW LIFECYCLE
    # =================================================================

    def _save_state(self):
        """Save window state to QSettings (guarded against double calls)."""
        if self._closing:
            return
        self._closing = True
        self.settings.setValue(
            _SK_SPLITTER,
            self.splitter.saveState(),
        )
        self.save_settings()

    def closeEvent(self, event):
        """Handle close event."""
        self._save_state()
        super(GuideTemplateManagerUI, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self._save_state()
        super(GuideTemplateManagerUI, self).dockCloseEventTriggered()
