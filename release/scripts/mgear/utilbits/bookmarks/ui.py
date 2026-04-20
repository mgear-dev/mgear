"""Bookmarks UI.

Main window for creating, managing, and recalling selection and
isolate visibility bookmarks.
"""

from maya import cmds

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtWidgets

from mgear.core import pyqt
from mgear.core.pyqt import dpi_scale

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from . import core
from .widgets import ChipButton
from .widgets import FlowLayout


LAYOUT_HORIZONTAL = 0
LAYOUT_VERTICAL = 1
LAYOUT_GRID = 2


class BookmarksUI(
    MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin
):
    """Main UI for Bookmarks Tool.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    TOOL_NAME = "Bookmarks"
    TOOL_TITLE = "Bookmarks"

    def __init__(self, parent=None):
        super(BookmarksUI, self).__init__(parent)
        self.settings = self.create_qsettings_object()

        self._bookmarks = []
        self._chip_widgets = []
        self._bookmark_counter = 0
        self._layout_index = LAYOUT_HORIZONTAL

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setMinimumHeight(int(dpi_scale(25)))

        self.setup_ui()

        self._load_layout_setting()
        self._apply_layout()

        self.resize(int(dpi_scale(300)), int(dpi_scale(75)))

        self._load_from_scene()

    def setup_ui(self):
        """Build the user interface."""
        self._create_menu_bar()
        self._create_widgets()
        self._create_layout()
        self._create_connections()

    # ---------------------------------------------------------
    # UI construction
    # ---------------------------------------------------------

    def _create_menu_bar(self):
        """Create the menu bar with File, Edit, and View menus."""
        self.menu_bar = QtWidgets.QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)
        self.menu_bar.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        file_menu = self.menu_bar.addMenu("文件")
        self.export_action = file_menu.addAction("导出...")
        self.import_action = file_menu.addAction("导入...")

        edit_menu = self.menu_bar.addMenu("编辑")
        self.add_sel_action = edit_menu.addAction("+ 选择书签")
        self.add_iso_action = edit_menu.addAction("+ 隔离书签")

        view_menu = self.menu_bar.addMenu("视图")
        self._layout_action_group = QtWidgets.QActionGroup(self)
        self._layout_action_group.setExclusive(True)
        self.layout_h_action = view_menu.addAction("水平")
        self.layout_v_action = view_menu.addAction("垂直")
        self.layout_g_action = view_menu.addAction("网格")
        for action in (
            self.layout_h_action,
            self.layout_v_action,
            self.layout_g_action,
        ):
            action.setCheckable(True)
            self._layout_action_group.addAction(action)
        self.layout_h_action.setChecked(True)

    def _create_widgets(self):
        """Create chip area widgets."""
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.chip_container = QtWidgets.QWidget()
        self.chip_layout = None
        self.scroll_area.setWidget(self.chip_container)

    def _create_layout(self):
        """Arrange widgets in the main layout."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def _create_connections(self):
        """Connect signals to slots."""
        self.add_sel_action.triggered.connect(self._on_add_selection)
        self.add_iso_action.triggered.connect(self._on_add_isolate)
        self._layout_action_group.triggered.connect(
            self._on_layout_changed
        )
        self.export_action.triggered.connect(self._on_export)
        self.import_action.triggered.connect(self._on_import)

    # ---------------------------------------------------------
    # Layout management
    # ---------------------------------------------------------

    def _get_layout_index(self):
        """Get current layout index.

        Returns:
            int: 0=horizontal, 1=vertical, 2=grid.
        """
        return self._layout_index

    def _get_layout_name(self):
        """Get current layout name string.

        Returns:
            str: Layout name for serialization.
        """
        return core.LAYOUT_NAMES[self._layout_index]

    def _apply_layout(self):
        """Apply the current layout mode to the chip container."""
        layout_index = self._get_layout_index()

        chips_to_readd = list(self._chip_widgets)
        for chip in chips_to_readd:
            chip.setParent(None)

        new_container = QtWidgets.QWidget()
        new_container.setAcceptDrops(True)
        new_container.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        new_container.customContextMenuRequested.connect(
            self._on_container_context_menu
        )
        new_container.dragEnterEvent = self._container_drag_enter
        new_container.dropEvent = self._container_drop

        spacing = int(dpi_scale(3))
        margins = int(dpi_scale(3))

        if layout_index == LAYOUT_HORIZONTAL:
            new_layout = QtWidgets.QHBoxLayout(new_container)
            new_layout.setAlignment(QtCore.Qt.AlignLeft)
        elif layout_index == LAYOUT_VERTICAL:
            new_layout = QtWidgets.QVBoxLayout(new_container)
            new_layout.setAlignment(QtCore.Qt.AlignTop)
        else:
            new_layout = FlowLayout(new_container, spacing=spacing)

        new_layout.setContentsMargins(margins, margins, margins, margins)
        if not isinstance(new_layout, FlowLayout):
            new_layout.setSpacing(spacing)

        for chip in chips_to_readd:
            chip.setParent(new_container)
            new_layout.addWidget(chip)

        if isinstance(new_layout, QtWidgets.QBoxLayout):
            new_layout.addStretch()

        self.scroll_area.setWidget(new_container)
        self.chip_container = new_container
        self.chip_layout = new_layout

    def _on_layout_changed(self, action):
        """Handle layout mode change from View menu.

        Args:
            action (QAction): The triggered layout action.
        """
        key = action.text().lower()
        if key in core.LAYOUT_MAP:
            self._layout_index = core.LAYOUT_MAP[key]
        self._apply_layout()
        self._auto_save()

    # ---------------------------------------------------------
    # Bookmark creation
    # ---------------------------------------------------------

    def _next_name(self):
        """Generate the next auto bookmark name.

        Returns:
            str: Name like "Bookmark 1", "Bookmark 2", etc.
        """
        self._bookmark_counter += 1
        return "Bookmark {}".format(self._bookmark_counter)

    def _on_add_selection(self):
        """Create a selection bookmark from current Maya selection."""
        self._add_bookmark(core.BOOKMARK_SELECTION)

    def _on_add_isolate(self):
        """Create an isolate bookmark from current Maya selection."""
        self._add_bookmark(core.BOOKMARK_ISOLATE)

    def _add_bookmark(self, bookmark_type):
        """Create a bookmark of the given type from current selection.

        Args:
            bookmark_type (str): BOOKMARK_SELECTION or BOOKMARK_ISOLATE.
        """
        bookmark = core.bookmark_from_selection(
            self._next_name(), bookmark_type
        )
        if not bookmark:
            cmds.warning("Nothing selected")
            return
        self._add_chip(bookmark)
        self._auto_save()

    # ---------------------------------------------------------
    # Chip management
    # ---------------------------------------------------------

    def _connect_chip(self, chip):
        """Connect all signals from a chip widget.

        Args:
            chip (ChipButton): The chip to connect.
        """
        chip.chip_clicked.connect(self._on_chip_clicked)
        chip.rename_requested.connect(self._on_rename)
        chip.color_change_requested.connect(self._on_change_color)
        chip.add_items_requested.connect(self._on_add_items)
        chip.remove_items_requested.connect(self._on_remove_items)
        chip.add_to_shelf_requested.connect(self._on_add_to_shelf)
        chip.delete_requested.connect(self._on_delete)
        chip.toggle_menu_requested.connect(self._toggle_menu_bar)

    def _insert_chip_widget(self, chip):
        """Insert chip widget into the current layout.

        Args:
            chip (ChipButton): The chip to insert.
        """
        if isinstance(self.chip_layout, QtWidgets.QBoxLayout):
            count = self.chip_layout.count()
            self.chip_layout.insertWidget(count - 1, chip)
        else:
            self.chip_layout.addWidget(chip)

    def _add_chip(self, bookmark):
        """Create a ChipButton and add it to the layout.

        Args:
            bookmark (dict): Bookmark data.
        """
        self._bookmarks.append(bookmark)
        chip = ChipButton(bookmark, parent=self.chip_container)
        self._connect_chip(chip)
        self._insert_chip_widget(chip)
        self._chip_widgets.append(chip)

    def _remove_chip(self, bookmark):
        """Remove a chip widget and its bookmark.

        Args:
            bookmark (dict): The bookmark to remove.
        """
        for i, bm in enumerate(self._bookmarks):
            if bm is bookmark:
                chip = self._chip_widgets[i]
                self.chip_layout.removeWidget(chip)
                chip.deleteLater()
                self._chip_widgets.pop(i)
                self._bookmarks.pop(i)
                break

    def _rebuild_chips(self):
        """Clear and rebuild all chips from self._bookmarks."""
        for chip in self._chip_widgets:
            self.chip_layout.removeWidget(chip)
            chip.deleteLater()
        self._chip_widgets.clear()

        for bookmark in list(self._bookmarks):
            chip = ChipButton(bookmark, parent=self.chip_container)
            self._connect_chip(chip)
            self._insert_chip_widget(chip)
            self._chip_widgets.append(chip)

    def _find_chip_for_bookmark(self, bookmark):
        """Find the ChipButton widget for a bookmark.

        Args:
            bookmark (dict): The bookmark reference.

        Returns:
            ChipButton: The chip widget, or None.
        """
        for i, bm in enumerate(self._bookmarks):
            if bm is bookmark:
                return self._chip_widgets[i]
        return None

    # ---------------------------------------------------------
    # Drag and drop reorder
    # ---------------------------------------------------------

    def _container_drag_enter(self, event):
        """Accept chip drag events.

        Args:
            event (QDragEnterEvent): The drag enter event.
        """
        if event.mimeData().text() == "chip_drag":
            event.acceptProposedAction()

    def _container_drop(self, event):
        """Handle chip drop for reordering.

        Args:
            event (QDropEvent): The drop event.
        """
        if event.mimeData().text() != "chip_drag":
            return

        source = event.source()
        if not isinstance(source, ChipButton):
            return

        src_idx = None
        for i, chip in enumerate(self._chip_widgets):
            if chip is source:
                src_idx = i
                break
        if src_idx is None:
            return

        drop_pos = event.pos()
        dst_idx = len(self._chip_widgets)
        for i, chip in enumerate(self._chip_widgets):
            if chip is source:
                continue
            geom = chip.geometry()
            if self._layout_index == LAYOUT_VERTICAL:
                mid = geom.center().y()
                if drop_pos.y() < mid:
                    dst_idx = i
                    break
            else:
                mid = geom.center().x()
                if drop_pos.x() < mid:
                    dst_idx = i
                    break

        if dst_idx == src_idx:
            return

        if dst_idx > src_idx:
            dst_idx -= 1

        bm = self._bookmarks.pop(src_idx)
        self._bookmarks.insert(dst_idx, bm)
        chip = self._chip_widgets.pop(src_idx)
        self._chip_widgets.insert(dst_idx, chip)

        self._apply_layout()
        self._auto_save()
        event.acceptProposedAction()

    # ---------------------------------------------------------
    # Container context menu
    # ---------------------------------------------------------

    def _on_container_context_menu(self, pos):
        """Show context menu on empty area of the chip container.

        Args:
            pos (QPoint): Local position of the click.
        """
        menu = QtWidgets.QMenu(self)
        sel_action = menu.addAction("+ 选择书签")
        iso_action = menu.addAction("+ 隔离书签")
        menu.addSeparator()
        toggle_action = menu.addAction("切换菜单栏")

        action = menu.exec_(self.chip_container.mapToGlobal(pos))
        if action == sel_action:
            self._on_add_selection()
        elif action == iso_action:
            self._on_add_isolate()
        elif action == toggle_action:
            self._toggle_menu_bar()

    def _toggle_menu_bar(self):
        """Toggle menu bar visibility."""
        self.menu_bar.setVisible(not self.menu_bar.isVisible())

    # ---------------------------------------------------------
    # Chip click handling
    # ---------------------------------------------------------

    def _on_chip_clicked(self, bookmark):
        """Handle chip click with keyboard modifiers.

        Args:
            bookmark (dict): The clicked bookmark.
        """
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if bookmark["type"] == core.BOOKMARK_SELECTION:
            cmds.undoInfo(openChunk=True)
            try:
                if modifiers & QtCore.Qt.ShiftModifier:
                    core.recall_selection(bookmark, mode="add")
                elif modifiers & QtCore.Qt.ControlModifier:
                    core.recall_selection(bookmark, mode="deselect")
                else:
                    core.recall_selection(bookmark, mode="replace")
            finally:
                cmds.undoInfo(closeChunk=True)
        elif bookmark["type"] == core.BOOKMARK_ISOLATE:
            core.toggle_isolate(bookmark)

    # ---------------------------------------------------------
    # Context menu handlers
    # ---------------------------------------------------------

    def _on_rename(self, bookmark):
        """Prompt for new name and update bookmark.

        Args:
            bookmark (dict): The bookmark to rename.
        """
        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "重命名书签",
            "新名称：",
            text=bookmark["name"],
        )
        if ok and new_name.strip():
            bookmark["name"] = new_name.strip()
            chip = self._find_chip_for_bookmark(bookmark)
            if chip:
                chip.update_bookmark(bookmark)
            self._auto_save()

    def _on_change_color(self, bookmark):
        """Open color picker and update bookmark.

        Args:
            bookmark (dict): The bookmark to recolor.
        """
        r, g, b = bookmark["color"]
        initial = QtGui.QColor.fromRgbF(r, g, b)
        color = QtWidgets.QColorDialog.getColor(
            initial,
            parent=self,
            options=QtWidgets.QColorDialog.DontUseNativeDialog,
        )
        if color.isValid():
            bookmark["color"] = [
                color.redF(),
                color.greenF(),
                color.blueF(),
            ]
            chip = self._find_chip_for_bookmark(bookmark)
            if chip:
                chip.update_bookmark(bookmark)
            self._auto_save()

    def _on_add_items(self, bookmark):
        """Add current Maya selection to bookmark.

        Args:
            bookmark (dict): The bookmark to modify.
        """
        added = core.add_selected_to_bookmark(bookmark)
        if added:
            chip = self._find_chip_for_bookmark(bookmark)
            if chip:
                chip.update_bookmark(bookmark)
            self._auto_save()
        else:
            cmds.warning("Nothing selected to add")

    def _on_remove_items(self, bookmark):
        """Remove current Maya selection from bookmark.

        Args:
            bookmark (dict): The bookmark to modify.
        """
        removed = core.remove_selected_from_bookmark(bookmark)
        if removed:
            chip = self._find_chip_for_bookmark(bookmark)
            if chip:
                chip.update_bookmark(bookmark)
            self._auto_save()
        else:
            cmds.warning("No matching items to remove")

    def _on_add_to_shelf(self, bookmark):
        """Add bookmark to Maya's current shelf.

        Args:
            bookmark (dict): The bookmark to add.
        """
        result = core.add_bookmark_to_shelf(bookmark)
        if result:
            cmds.inViewMessage(
                amg="Added <hl>{}</hl> to shelf".format(
                    bookmark["name"]
                ),
                pos="topCenter",
                fade=True,
            )

    def _on_delete(self, bookmark):
        """Delete a bookmark chip.

        Args:
            bookmark (dict): The bookmark to delete.
        """
        self._remove_chip(bookmark)
        self._auto_save()

    # ---------------------------------------------------------
    # Scene persistence
    # ---------------------------------------------------------

    def _load_layout_setting(self):
        """Restore layout choice from QSettings."""
        idx = int(
            self.settings.value("sel_bookmarks/layout", defaultValue=0)
        )
        if 0 <= idx <= LAYOUT_GRID:
            self._layout_index = idx
        actions = (
            self.layout_h_action,
            self.layout_v_action,
            self.layout_g_action,
        )
        actions[self._layout_index].setChecked(True)

    def _save_layout_setting(self):
        """Persist layout choice to QSettings."""
        self.settings.setValue(
            "sel_bookmarks/layout", self._get_layout_index()
        )
        self.settings.sync()

    def _auto_save(self):
        """Auto-save bookmarks to the scene node."""
        self._save_layout_setting()
        core.save_to_scene(self._bookmarks, self._get_layout_name())

    def _load_from_scene(self):
        """Load bookmarks from scene on startup."""
        config = core.load_from_scene()
        if not config:
            return
        bookmarks, layout = core.config_to_bookmarks(config)
        self._bookmarks = bookmarks
        self._layout_index = core.LAYOUT_MAP.get(layout, 0)
        self._apply_layout()
        self._bookmark_counter = len(bookmarks)
        self._rebuild_chips()

    # ---------------------------------------------------------
    # Export / Import
    # ---------------------------------------------------------

    def _on_export(self):
        """Export bookmarks to a .sbk file."""
        file_filter = "Bookmarks (*{})".format(core.CONFIG_FILE_EXT)
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Bookmarks", "", file_filter
        )
        if not file_path:
            return
        core.export_bookmarks(
            file_path, self._bookmarks, self._get_layout_name()
        )

    def _on_import(self):
        """Import bookmarks from a .sbk file."""
        file_filter = "Bookmarks (*{})".format(core.CONFIG_FILE_EXT)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Bookmarks", "", file_filter
        )
        if not file_path:
            return
        config = core.import_bookmarks(file_path)
        if not config:
            return

        bookmarks, layout = core.config_to_bookmarks(config)
        append = False
        if self._bookmarks:
            result = QtWidgets.QMessageBox.question(
                self,
                "Import Bookmarks",
                "Replace existing bookmarks?\n\n"
                "Yes = Replace, No = Append",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            append = result == QtWidgets.QMessageBox.No

        if append:
            for bm in bookmarks:
                self._add_chip(bm)
        else:
            self._bookmarks = bookmarks
            self._layout_index = core.LAYOUT_MAP.get(layout, 0)
            self._apply_layout()
            self._rebuild_chips()

        self._auto_save()
