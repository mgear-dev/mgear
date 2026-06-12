"""Matcap Viewer - Main UI Module.

Dockable dialog for browsing, applying, and toggling matcap
shaders on Maya meshes with thumbnail preview.
"""

import json

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.core import pyqt
from mgear.core.pyqt import dpi_scale

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

from . import core
from .widgets import MatcapGridWidget
from .widgets import SourceFoldersDialog

# Settings keys
_SK_SOURCE_FOLDERS = "matcapViewer/source_folders"
_SK_FAVORITES = "matcapViewer/favorites"
_SK_ICON_SIZE = "matcapViewer/icon_size"
_SK_LAST_TEXTURE = "matcapViewer/last_texture"
_SK_MENU_VISIBLE = "matcapViewer/menu_visible"
_SK_SEARCH_VISIBLE = "matcapViewer/search_visible"


class MatcapViewerUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for the Matcap Viewer tool.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    TOOL_NAME = "MatcapViewer"
    TOOL_TITLE = "Matcap Viewer"

    def __init__(self, parent=None):
        super(MatcapViewerUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self._source_folders = []
        self._closing = False

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumWidth(30)
        self.setMinimumHeight(int(dpi_scale(100)))

        if cmds.about(ntOS=True):
            flags = (
                self.windowFlags()
                ^ QtCore.Qt.WindowContextHelpButtonHint
            )
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.setup_ui()

        # Restore menu/search bar visibility
        menu_visible = self.settings.value(
            _SK_MENU_VISIBLE, True
        )
        if isinstance(menu_visible, str):
            menu_visible = menu_visible.lower() != "false"
        self.menu_bar.setVisible(menu_visible)

        search_visible = self.settings.value(
            _SK_SEARCH_VISIBLE, True
        )
        if isinstance(search_visible, str):
            search_visible = search_visible.lower() != "false"
        self.search_input.setVisible(search_visible)

        # Load persistent state
        self._source_folders = json.loads(
            self.settings.value(_SK_SOURCE_FOLDERS, "[]")
        )

        favorites_json = self.settings.value(_SK_FAVORITES, "[]")
        favorites = set(json.loads(favorites_json))
        self.matcap_grid.set_favorites(favorites)

        icon_size = int(
            self.settings.value(
                _SK_ICON_SIZE,
                defaultValue=int(dpi_scale(72)),
            )
        )
        self.size_slider.setValue(icon_size)

        self.user_settings = {
            "matcapViewer/show_labels": (
                self.show_labels_action,
                False,
            ),
            "matcapViewer/show_favorites": (
                self.show_favorites_action,
                False,
            ),
            "matcapViewer/apply_selected": (
                self.apply_selected_action,
                False,
            ),
        }
        self.load_settings()

        self.refresh_matcaps()

        self.resize(int(dpi_scale(400)), int(dpi_scale(450)))

    # =============================================================
    # UI SETUP
    # =============================================================

    def setup_ui(self):
        """Build the UI layout."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_actions(self):
        """Create QActions for menus."""
        # Edit menu
        self.refresh_action = QtWidgets.QAction("Refresh", self)
        self.clear_matcap_action = QtWidgets.QAction(
            "Clear Matcap", self
        )

        # Settings menu
        self.edit_folders_action = QtWidgets.QAction(
            "Edit Source Folders...", self
        )
        self.show_labels_action = QtWidgets.QAction(
            "Show Labels", self
        )
        self.show_labels_action.setCheckable(True)
        self.show_labels_action.setChecked(False)

        self.show_favorites_action = QtWidgets.QAction(
            "Show Only Favorites", self
        )
        self.show_favorites_action.setCheckable(True)
        self.show_favorites_action.setChecked(False)

        self._apply_action_group = QtWidgets.QActionGroup(self)
        self._apply_action_group.setExclusive(True)

        self.apply_all_action = QtWidgets.QAction(
            "Apply to All Meshes", self
        )
        self.apply_all_action.setCheckable(True)
        self.apply_all_action.setChecked(True)
        self._apply_action_group.addAction(self.apply_all_action)

        self.apply_selected_action = QtWidgets.QAction(
            "Apply to Selected Meshes", self
        )
        self.apply_selected_action.setCheckable(True)
        self._apply_action_group.addAction(self.apply_selected_action)

        # Help menu
        self.open_library_action = QtWidgets.QAction(
            "Matcap Library (GitHub)", self
        )

    def create_widgets(self):
        """Create all UI widgets."""
        # Menu bar
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        self.menu_bar.setContextMenuPolicy(
            QtCore.Qt.PreventContextMenu
        )

        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction(self.refresh_action)
        edit_menu.addAction(self.clear_matcap_action)

        settings_menu = self.menu_bar.addMenu("Settings")
        settings_menu.addAction(self.edit_folders_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self.show_labels_action)
        settings_menu.addAction(self.show_favorites_action)
        settings_menu.addSeparator()
        settings_menu.addAction(self.apply_all_action)
        settings_menu.addAction(self.apply_selected_action)

        help_menu = self.menu_bar.addMenu("Help")
        help_menu.addAction(self.open_library_action)

        # Search bar
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search matcaps...")
        self.search_input.setClearButtonEnabled(True)

        # Matcap grid
        self.matcap_grid = MatcapGridWidget()

        # Size slider
        self.size_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.size_slider.setMinimum(40)
        self.size_slider.setMaximum(150)
        self.size_slider.setValue(int(dpi_scale(72)))
        self.size_slider.setFixedHeight(int(dpi_scale(16)))

    def create_layout(self):
        """Arrange widgets in layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setMenuBar(self.menu_bar)

        main_layout.addWidget(self.search_input)
        main_layout.addWidget(self.matcap_grid, stretch=1)
        main_layout.addWidget(self.size_slider)

    def create_connections(self):
        """Connect signals to slots."""
        # Edit menu
        self.refresh_action.triggered.connect(self.refresh_matcaps)
        self.clear_matcap_action.triggered.connect(
            self._on_clear_matcap
        )

        # Settings menu
        self.edit_folders_action.triggered.connect(
            self.edit_source_folders
        )
        self.show_labels_action.toggled.connect(
            self.matcap_grid.set_show_labels
        )
        self.show_favorites_action.toggled.connect(
            self.matcap_grid.set_show_favorites_only
        )

        # Help menu
        self.open_library_action.triggered.connect(
            self._open_matcap_library
        )

        # Search
        self.search_input.textChanged.connect(
            self.matcap_grid.filter_by_text
        )

        # Grid signals
        self.matcap_grid.matcap_clicked.connect(
            self._on_matcap_clicked
        )
        self.matcap_grid.matcap_double_clicked.connect(
            self._on_matcap_double_clicked
        )
        self.matcap_grid.toggle_menu_requested.connect(
            self._toggle_menu_bar
        )
        self.matcap_grid.toggle_search_requested.connect(
            self._toggle_search_bar
        )
        self.matcap_grid.toggle_material_requested.connect(
            self._on_toggle_material
        )
        self.matcap_grid.icon_size_changed.connect(
            self._on_grid_size_changed
        )
        self.matcap_grid.favorites_filter_changed.connect(
            self._on_favorites_filter_changed
        )

        # Size slider
        self.size_slider.valueChanged.connect(
            self.matcap_grid.set_icon_size
        )

        # Arrow key navigation
        self.matcap_grid.matcap_current_changed.connect(
            self._on_matcap_clicked
        )

    # =============================================================
    # MATCAP BROWSING
    # =============================================================

    def refresh_matcaps(self):
        """Rescan all source folders and repopulate the grid."""
        entries = core.scan_folders(self._source_folders)
        self.matcap_grid.populate(entries)

        search_text = self.search_input.text()
        if search_text:
            self.matcap_grid.filter_by_text(search_text)

        current = core.get_current_texture()
        if current:
            self.matcap_grid.set_current(current)

    # =============================================================
    # MATCAP INTERACTION
    # =============================================================

    def _on_matcap_clicked(self, image_path):
        """Handle single click - change texture if matcap is active.

        Args:
            image_path (str): Path to the clicked matcap image.
        """
        if not core.is_matcap_active():
            return
        self._apply_texture(image_path)

    def _on_matcap_double_clicked(self, image_path):
        """Handle double click - apply matcap or change texture.

        In "Apply to Selected" mode, restores previous meshes
        and re-applies to the current selection (or clears if
        nothing is selected).

        Args:
            image_path (str): Path to the double-clicked matcap image.
        """
        if core.is_matcap_active():
            if self.apply_selected_action.isChecked():
                meshes = self._get_target_meshes()
                if meshes is not None and not meshes:
                    self._notify_empty_selection()
                    return
                # Restore old, then re-apply to new selection
                core.restore_original_materials()
                if meshes:
                    core.apply_matcap(meshes=meshes)
                    self._apply_texture(image_path)
                else:
                    self.matcap_grid.set_current(None)
            else:
                self._apply_texture(image_path)
            return

        meshes = self._get_target_meshes()
        if meshes is not None and not meshes:
            self._notify_empty_selection()
            return
        result = core.apply_matcap(meshes=meshes)
        if result:
            self._apply_texture(image_path)

    def _apply_texture(self, image_path):
        """Set texture, update grid highlight, and persist last used.

        Args:
            image_path (str): Path to the matcap image.
        """
        core.set_texture(image_path)
        self.matcap_grid.set_current(image_path)
        self.settings.setValue(_SK_LAST_TEXTURE, image_path)

    def _get_target_meshes(self):
        """Get meshes based on apply mode setting.

        Returns:
            list or None: Mesh transforms to apply to.  None means
                "apply to all meshes in the scene".  An empty list
                means "Apply to Selected" is on but nothing valid
                is selected — callers must warn and abort.
        """
        if self.apply_selected_action.isChecked():
            sel = cmds.ls(selection=True, long=True) or []
            meshes = []
            for node in sel:
                shapes = cmds.listRelatives(
                    node,
                    shapes=True,
                    fullPath=True,
                    type="mesh",
                )
                if shapes:
                    meshes.append(node)
            return meshes
        return None

    def _notify_empty_selection(self):
        """Show an in-viewport message that nothing is selected."""
        cmds.inViewMessage(
            assistMessage=(
                "Matcap Viewer: "
                "<hl>Apply to Selected</hl> is on but nothing is "
                "selected"
            ),
            pos="topCenter",
            fade=True,
        )

    # =============================================================
    # TOGGLE MATERIAL
    # =============================================================

    def _on_toggle_material(self):
        """Toggle matcap on/off.

        Toggle always uses the already-tracked meshes.  It
        never reads the current Maya selection — mesh targets
        only change on double-click.
        """
        if core.is_matcap_active():
            core.restore_original_materials()
            self.matcap_grid.set_current(None)
        else:
            last_texture = self.settings.value(_SK_LAST_TEXTURE, "")
            if last_texture and not core.get_current_texture():
                core.create_shader_graph()
                core.set_texture(last_texture)
            # Re-apply to previously tracked meshes, not
            # current selection.  Pass the tracked list or
            # None (which means all — correct for "Apply to
            # All" mode where no specific set was tracked).
            tracked = core.get_tracked_meshes()
            result = core.apply_matcap(
                meshes=tracked if tracked else None
            )
            if result:
                current = core.get_current_texture()
                self.matcap_grid.set_current(current)

    # =============================================================
    # CLEAR MATCAP
    # =============================================================

    def _on_clear_matcap(self):
        """Clear matcap without closing the UI."""
        core.cleanup()
        self.matcap_grid.set_current(None)

    # =============================================================
    # SOURCE FOLDERS
    # =============================================================

    def edit_source_folders(self):
        """Open the source folders management dialog."""
        dialog = SourceFoldersDialog(self._source_folders, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._source_folders = dialog.get_folders()
            self.settings.setValue(
                _SK_SOURCE_FOLDERS,
                json.dumps(self._source_folders),
            )
            self.refresh_matcaps()

    # =============================================================
    # UI TOGGLES
    # =============================================================

    def _toggle_menu_bar(self):
        """Toggle menu bar visibility and persist."""
        visible = not self.menu_bar.isVisible()
        self.menu_bar.setVisible(visible)
        self.settings.setValue(_SK_MENU_VISIBLE, visible)

    def _toggle_search_bar(self):
        """Toggle search bar visibility and persist."""
        visible = not self.search_input.isVisible()
        self.search_input.setVisible(visible)
        self.settings.setValue(_SK_SEARCH_VISIBLE, visible)

    def _open_matcap_library(self):
        """Open the matcap library GitHub page in browser."""
        url = QtCore.QUrl("https://github.com/nidorx/matcaps")
        QtGui.QDesktopServices.openUrl(url)

    def _on_grid_size_changed(self, size):
        """Sync slider when grid icon size changes via Ctrl+wheel.

        Args:
            size (int): New icon size.
        """
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(size)
        self.size_slider.blockSignals(False)

    def _on_favorites_filter_changed(self, show):
        """Sync Settings menu action when context menu toggles filter.

        Args:
            show (bool): New filter state.
        """
        self.show_favorites_action.blockSignals(True)
        self.show_favorites_action.setChecked(show)
        self.show_favorites_action.blockSignals(False)

    # =============================================================
    # WINDOW LIFECYCLE
    # =============================================================

    def _save_state(self):
        """Save all persistent state to QSettings."""
        if self._closing:
            return
        self._closing = True

        self.save_settings()
        self.settings.setValue(
            _SK_FAVORITES,
            json.dumps(list(self.matcap_grid.get_favorites())),
        )
        self.settings.setValue(
            _SK_ICON_SIZE, self.matcap_grid.get_icon_size()
        )
        core.cleanup()

    def closeEvent(self, event):
        """Handle close event."""
        self._save_state()
        super(MatcapViewerUI, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        """Called when docked window is closed."""
        self._save_state()
        super(MatcapViewerUI, self).dockCloseEventTriggered()
