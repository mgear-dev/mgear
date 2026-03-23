"""Guide Template Manager - Main UI Module.

Dockable dialog for browsing, importing, and managing Shifter
guide templates (.sgt files) with metadata and thumbnails.
"""

import json
import os

import mgear
import mgear.pymaya as pm
from mgear.core import pyqt

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.shifter import io as shifter_io

from . import core
from .widgets import ImportPartialDialog
from .widgets import SourceFoldersDialog
from .widgets import TemplateInfoPanel
from .widgets import TemplateTreeWidget


class GuideTemplateManagerUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for the Guide Template Manager.

    Dockable dialog with a tree browser on the left and an info
    panel on the right.  Supports import, import-add, import-partial,
    export, viewport screenshot capture, and custom source folders.
    """

    TOOL_NAME = "GuideTemplateManager"
    TOOL_TITLE = "Guide Template Manager"

    def __init__(self, parent=None):
        super(GuideTemplateManagerUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        # State
        self._source_folders = []
        self._current_template_path = None

        # Window setup
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

        # Build UI
        self.setup_ui()

        # Load persisted settings
        self._source_folders = json.loads(
            self.settings.value(
                "templateManager/source_folders", "[]"
            )
        )

        self.user_settings = {
            "templateManager/show_defaults": (
                self.show_defaults_action,
                True,
            ),
        }
        self.load_settings()

        # Restore splitter state
        splitter_state = self.settings.value(
            "templateManager/splitter"
        )
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        self.resize(800, 500)

        # Initial population
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
            "Export Template...", self
        )
        self.refresh_action = QtWidgets.QAction(
            "Refresh List", self
        )
        self.edit_folders_action = QtWidgets.QAction(
            "Edit Source Folders...", self
        )
        self.show_defaults_action = QtWidgets.QAction(
            "Show Default Guides", self
        )
        self.show_defaults_action.setCheckable(True)
        self.show_defaults_action.setChecked(True)

    def create_widgets(self):
        """Create all UI widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.export_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.refresh_action)

        self.settings_menu = self.menu_bar.addMenu("Settings")
        self.settings_menu.addAction(self.edit_folders_action)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.show_defaults_action)

        # Search bar
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search templates...")
        self.search_input.setClearButtonEnabled(True)

        # Template tree (left panel)
        self.template_tree = TemplateTreeWidget()

        # Info panel (right panel)
        self.info_panel = TemplateInfoPanel()

        # Splitter
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
        # Menu actions
        self.export_action.triggered.connect(self.export_template)
        self.refresh_action.triggered.connect(self.refresh_templates)
        self.edit_folders_action.triggered.connect(
            self.edit_source_folders
        )
        self.show_defaults_action.toggled.connect(
            lambda *args: self.refresh_templates()
        )

        # Search
        self.search_input.textChanged.connect(self._filter_templates)

        # Tree signals
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

        # Default templates
        if self.show_defaults_action.isChecked():
            default_dir = core.get_default_templates_dir()
            if os.path.isdir(default_dir):
                folder_paths.append(default_dir)

        # Custom folders
        folder_paths.extend(self._source_folders)

        # Scan and populate
        folder_entries = core.scan_template_folders(folder_paths)

        # Set display labels
        for entry in folder_entries:
            if entry.path == core.get_default_templates_dir():
                entry.label = "Default Templates"

        self.template_tree.populate(folder_entries)

        # Auto-generate missing .sgtInfo (best effort)
        self._ensure_sgt_info_files(folder_entries)

        # Re-apply search filter
        self._filter_templates(self.search_input.text())

    def _ensure_sgt_info_files(self, folder_entries):
        """Generate missing .sgtInfo files for all templates.

        Args:
            folder_entries (list): List of FolderEntry objects.
        """
        for folder in folder_entries:
            for template in folder.templates:
                if not template.has_info:
                    core.ensure_sgt_info(template.sgt_path)
            for subfolder in folder.subfolders:
                self._ensure_sgt_info_files([subfolder])

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
        self._current_template_path = sgt_path
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
                "Please select a guide element to add to"
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
                "Could not read components from template"
            )
            return

        dialog = ImportPartialDialog(components, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return

        # Use root components only to preserve hierarchy.
        # draw_guide discovers children automatically.
        roots = dialog.get_root_components()
        if not roots:
            cmds.warning("No components selected")
            return

        # Check if there's a selection to use as parent
        init_parent = None
        selection = pm.selected()
        if selection:
            init_parent = selection[0]

        match_position = (
            dialog.get_action() == ImportPartialDialog.IMPORT_MATCH
        )

        # Store target position before import
        target_pos = None
        if match_position and init_parent:
            target_pos = cmds.xform(
                str(init_parent),
                query=True,
                worldSpace=True,
                translation=True,
            )

        # Snapshot existing roots to find the newly created one
        existing_roots = set(
            cmds.ls("*_root", type="transform", long=True)
        )

        shifter_io.import_partial_guide(
            filePath=sgt_path,
            partial=roots,
            initParent=init_parent,
        )

        # Match position: find the first new root and move it
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
                "templateManager/source_folders",
                json.dumps(self._source_folders),
            )
            self.refresh_templates()

    # =================================================================
    # WINDOW LIFECYCLE
    # =================================================================

    def close(self):
        """Clean up before closing."""
        # Save splitter state
        self.settings.setValue(
            "templateManager/splitter",
            self.splitter.saveState(),
        )
        self.save_settings()
        self.deleteLater()

    def closeEvent(self, event):
        """Handle close event."""
        self.close()

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self.close()
