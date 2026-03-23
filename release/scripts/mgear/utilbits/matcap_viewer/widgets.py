"""Matcap Viewer - Custom Qt Widgets.

MatcapGridWidget for browsing matcap thumbnails and
SourceFoldersDialog for managing matcap image directories.
"""

import os
from math import cos
from math import pi
from math import sin

from mgear.core import pyqt
from mgear.core.pyqt import dpi_scale

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

_ICON_SIZE = int(dpi_scale(16))

_STAR_COLOR = QtGui.QColor(255, 210, 50)
_ACTIVE_BORDER_COLOR = QtGui.QColor(120, 180, 100)
_ACTIVE_BORDER_WIDTH = 3

_MIN_THUMB_SIZE = 40
_MAX_THUMB_SIZE = 150
_DEFAULT_THUMB_SIZE = 72
_LABEL_HEIGHT = 16
_WHEEL_STEP = 8


# =================================================================
# MATCAP GRID WIDGET
# =================================================================


class MatcapGridWidget(QtWidgets.QWidget):
    """Thumbnail grid for browsing and selecting matcap images.

    Signals:
        matcap_clicked(str): Single click, emits image path.
        matcap_double_clicked(str): Double click, emits image path.
        matcap_current_changed(str): Arrow key navigation changed.
        toggle_menu_requested(): Context menu toggle menu bar.
        toggle_search_requested(): Context menu toggle search bar.
        toggle_material_requested(): Context menu toggle material.
        favorites_filter_changed(bool): Favorites filter toggled.
        icon_size_changed(int): Icon size changed via Ctrl+wheel.
    """

    matcap_clicked = QtCore.Signal(str)
    matcap_double_clicked = QtCore.Signal(str)
    matcap_current_changed = QtCore.Signal(str)
    toggle_menu_requested = QtCore.Signal()
    toggle_search_requested = QtCore.Signal()
    toggle_material_requested = QtCore.Signal()
    favorites_filter_changed = QtCore.Signal(bool)
    icon_size_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(MatcapGridWidget, self).__init__(parent)

        self._entries = []
        self._entry_by_path = {}
        self._base_pixmap_cache = {}
        self._resolution_cache = {}
        self._favorites = set()
        self._show_favorites_only = False
        self._show_labels = False
        self._current_matcap = None
        self._icon_size = _DEFAULT_THUMB_SIZE
        self._search_text = ""

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self):
        """Create the internal list widget."""
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setViewMode(QtWidgets.QListView.IconMode)
        self.list_widget.setResizeMode(QtWidgets.QListView.Adjust)
        self.list_widget.setMovement(QtWidgets.QListView.Static)
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setWordWrap(True)
        self.list_widget.setSpacing(0)
        self.list_widget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        self._update_grid_size()

    def _create_layout(self):
        """Arrange the list widget."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.list_widget)

    def _create_connections(self):
        """Connect internal signals."""
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(
            self._on_item_double_clicked
        )
        self.list_widget.currentItemChanged.connect(
            self._on_current_changed
        )
        self.list_widget.customContextMenuRequested.connect(
            self._on_context_menu
        )

    # ---------------------------------------------------------
    # Grid sizing
    # ---------------------------------------------------------

    def _update_grid_size(self):
        """Update icon and grid size on the list widget."""
        size = self._icon_size
        self.list_widget.setIconSize(QtCore.QSize(size, size))
        if self._show_labels:
            self.list_widget.setGridSize(
                QtCore.QSize(size, size + _LABEL_HEIGHT)
            )
        else:
            self.list_widget.setGridSize(QtCore.QSize(size, size))

    def set_icon_size(self, size):
        """Set the thumbnail icon size.

        Args:
            size (int): Icon size in pixels.
        """
        size = max(_MIN_THUMB_SIZE, min(_MAX_THUMB_SIZE, size))
        if size == self._icon_size:
            return
        self._icon_size = size
        self._update_grid_size()
        self._refresh_all_icons()

    def set_show_labels(self, show):
        """Toggle matcap name labels under thumbnails.

        Args:
            show (bool): Whether to show labels.
        """
        self._show_labels = show
        self._update_grid_size()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(QtCore.Qt.UserRole)
            entry = self._find_entry(path)
            if entry:
                item.setText(entry["name"] if show else "")

    # ---------------------------------------------------------
    # Populate and refresh
    # ---------------------------------------------------------

    def populate(self, entries):
        """Populate the grid with matcap entries.

        Args:
            entries (list): List of dicts with name, path, folder.
        """
        self.list_widget.clear()
        self._entries = entries
        self._entry_by_path = {e["path"]: e for e in entries}
        self._base_pixmap_cache.clear()
        self._resolution_cache.clear()

        for entry in entries:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, entry["path"])
            if self._show_labels:
                item.setText(entry["name"])
            else:
                item.setText("")
            item.setIcon(self._build_icon(entry["path"]))
            item.setToolTip(self._build_tooltip(entry))
            self.list_widget.addItem(item)

        self._apply_visibility()

    def _refresh_all_icons(self):
        """Rebuild all item icons (after size or state change)."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(QtCore.Qt.UserRole)
            item.setIcon(self._build_icon(path))

    def _refresh_icon(self, path):
        """Rebuild the composed icon for a specific matcap path.

        Args:
            path (str): Image file path.
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(QtCore.Qt.UserRole) == path:
                item.setIcon(self._build_icon(path))
                break

    # ---------------------------------------------------------
    # Icon rendering
    # ---------------------------------------------------------

    def _get_base_pixmap(self, path):
        """Get or load the base pixmap for an image path.

        Args:
            path (str): Image file path.

        Returns:
            QPixmap: The loaded pixmap.
        """
        if path not in self._base_pixmap_cache:
            pm = QtGui.QPixmap(path)
            if not pm.isNull():
                self._resolution_cache[path] = (
                    pm.width(),
                    pm.height(),
                )
            self._base_pixmap_cache[path] = pm
        return self._base_pixmap_cache[path]

    def _build_icon(self, path):
        """Build a composed QIcon with overlays for a matcap.

        Args:
            path (str): Image file path.

        Returns:
            QIcon: Composed icon with optional star and border.
        """
        size = self._icon_size
        base = self._get_base_pixmap(path)
        if base.isNull():
            return QtGui.QIcon()

        canvas = QtGui.QPixmap(size, size)
        canvas.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        # Draw scaled matcap image
        scaled = base.scaled(
            size,
            size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Active border
        if path == self._current_matcap:
            pen = QtGui.QPen(
                _ACTIVE_BORDER_COLOR, _ACTIVE_BORDER_WIDTH
            )
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            half = _ACTIVE_BORDER_WIDTH / 2.0
            painter.drawRect(
                QtCore.QRectF(half, half, size - half * 2, size - half * 2)
            )

        # Favorite star overlay
        if path in self._favorites:
            self._draw_star(painter, size)

        painter.end()
        return QtGui.QIcon(canvas)

    def _draw_star(self, painter, canvas_size):
        """Draw a small star in the top-right corner.

        Args:
            painter (QPainter): Active painter.
            canvas_size (int): Canvas width/height.
        """
        star_size = max(10, canvas_size // 5)
        margin = 2
        cx = canvas_size - margin - star_size // 2
        cy = margin + star_size // 2

        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(_STAR_COLOR)

        points = []
        for i in range(10):
            angle = pi / 2 + i * pi / 5
            r = star_size // 2 if i % 2 == 0 else star_size // 4
            px = cx + r * cos(angle)
            py = cy - r * sin(angle)
            points.append(QtCore.QPointF(px, py))

        painter.drawPolygon(points)
        painter.restore()

    # ---------------------------------------------------------
    # Tooltip
    # ---------------------------------------------------------

    def _build_tooltip(self, entry):
        """Build tooltip text for a matcap entry.

        Args:
            entry (dict): Matcap entry dict.

        Returns:
            str: Tooltip text.
        """
        path = entry["path"]
        res = self._resolution_cache.get(path)
        if res:
            size_str = "{}x{}".format(res[0], res[1])
        else:
            pm = self._get_base_pixmap(path)
            if not pm.isNull():
                size_str = "{}x{}".format(pm.width(), pm.height())
            else:
                size_str = "unknown"
        return "Name: {}\nSize: {}\nPath: {}".format(
            entry["name"], size_str, path
        )

    # ---------------------------------------------------------
    # Current matcap highlight
    # ---------------------------------------------------------

    def set_current(self, image_path):
        """Set the currently active matcap and update its highlight.

        Args:
            image_path (str): Path of the active matcap, or None.
        """
        old = self._current_matcap
        self._current_matcap = image_path
        if old:
            self._refresh_icon(old)
        if image_path:
            self._refresh_icon(image_path)

    # ---------------------------------------------------------
    # Favorites
    # ---------------------------------------------------------

    def set_favorites(self, favorites_set):
        """Load favorites from a set of paths.

        Args:
            favorites_set (set): Set of image file paths.
        """
        self._favorites = set(favorites_set)
        self._refresh_all_icons()
        self._apply_visibility()

    def get_favorites(self):
        """Get the current favorites set.

        Returns:
            set: Set of favorite image paths.
        """
        return set(self._favorites)

    def _toggle_favorite(self, path):
        """Toggle favorite state for a matcap.

        Args:
            path (str): Image file path.
        """
        if path in self._favorites:
            self._favorites.discard(path)
        else:
            self._favorites.add(path)
        self._refresh_icon(path)
        self._apply_visibility()

    def set_show_favorites_only(self, show):
        """Toggle the favorites-only filter.

        Args:
            show (bool): Whether to show only favorites.
        """
        self._show_favorites_only = show
        self._apply_visibility()
        self.favorites_filter_changed.emit(show)

    # ---------------------------------------------------------
    # Filtering and visibility
    # ---------------------------------------------------------

    def filter_by_text(self, text):
        """Filter items by name text.

        Args:
            text (str): Search text (case-insensitive).
        """
        self._search_text = text.lower()
        self._apply_visibility()

    def _apply_visibility(self):
        """Apply both search and favorites filter to all items."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(QtCore.Qt.UserRole)
            entry = self._find_entry(path)
            if not entry:
                item.setHidden(True)
                continue

            visible = True
            if self._show_favorites_only and path not in self._favorites:
                visible = False
            if visible and self._search_text:
                if self._search_text not in entry["name"].lower():
                    visible = False

            item.setHidden(not visible)

    def _find_entry(self, path):
        """Find the entry dict for a given path.

        Args:
            path (str): Image file path.

        Returns:
            dict: Entry dict or None.
        """
        return self._entry_by_path.get(path)

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

    def _on_item_clicked(self, item):
        """Handle single click on a matcap item.

        Args:
            item (QListWidgetItem): Clicked item.
        """
        path = item.data(QtCore.Qt.UserRole)
        if path:
            self.matcap_clicked.emit(path)

    def _on_item_double_clicked(self, item):
        """Handle double click on a matcap item.

        Args:
            item (QListWidgetItem): Double-clicked item.
        """
        path = item.data(QtCore.Qt.UserRole)
        if path:
            self.matcap_double_clicked.emit(path)

    def _on_current_changed(self, current, previous):
        """Handle arrow key navigation item change.

        Args:
            current (QListWidgetItem): Newly focused item.
            previous (QListWidgetItem): Previously focused item.
        """
        if current is None:
            return
        path = current.data(QtCore.Qt.UserRole)
        if path:
            self.matcap_current_changed.emit(path)

    def wheelEvent(self, event):
        """Handle Ctrl+wheel for thumbnail size changes.

        Args:
            event (QWheelEvent): Wheel event.
        """
        modifiers = event.modifiers()
        if modifiers & QtCore.Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                new_size = min(
                    self._icon_size + _WHEEL_STEP, _MAX_THUMB_SIZE
                )
            else:
                new_size = max(
                    self._icon_size - _WHEEL_STEP, _MIN_THUMB_SIZE
                )
            self.set_icon_size(new_size)
            self.icon_size_changed.emit(self._icon_size)
            event.accept()
        else:
            super(MatcapGridWidget, self).wheelEvent(event)

    def _on_context_menu(self, pos):
        """Show the right-click context menu.

        Args:
            pos (QPoint): Local click position.
        """
        menu = QtWidgets.QMenu(self)
        item = self.list_widget.itemAt(pos)

        # Toggle Material always first
        toggle_mat_action = menu.addAction("Toggle Material")
        menu.addSeparator()

        if item:
            path = item.data(QtCore.Qt.UserRole)
            is_fav = path in self._favorites
            fav_text = (
                "Remove from Favorites" if is_fav else "Add to Favorites"
            )
            toggle_fav_action = menu.addAction(fav_text)
            menu.addSeparator()
        else:
            toggle_fav_action = None

        show_favs_action = menu.addAction("Show Only Favorites")
        show_favs_action.setCheckable(True)
        show_favs_action.setChecked(self._show_favorites_only)
        menu.addSeparator()

        toggle_menu_action = menu.addAction("Toggle Menu Bar")
        toggle_search_action = menu.addAction("Toggle Search Bar")

        action = menu.exec_(self.list_widget.mapToGlobal(pos))
        if not action:
            return

        if action == toggle_fav_action and item:
            path = item.data(QtCore.Qt.UserRole)
            self._toggle_favorite(path)
        elif action == show_favs_action:
            self.set_show_favorites_only(show_favs_action.isChecked())
        elif action == toggle_menu_action:
            self.toggle_menu_requested.emit()
        elif action == toggle_search_action:
            self.toggle_search_requested.emit()
        elif action == toggle_mat_action:
            self.toggle_material_requested.emit()

    def get_icon_size(self):
        """Get the current icon size.

        Returns:
            int: Current icon size in pixels.
        """
        return self._icon_size


# =================================================================
# SOURCE FOLDERS DIALOG
# =================================================================


class SourceFoldersDialog(QtWidgets.QDialog):
    """Dialog for managing matcap source folders.

    Args:
        folders (list): Current list of folder paths.
        parent: Parent widget.
    """

    def __init__(self, folders, parent=None):
        super(SourceFoldersDialog, self).__init__(parent)

        self.setWindowTitle("Matcap Source Folders")
        self.setMinimumSize(
            int(dpi_scale(500)),
            int(dpi_scale(300)),
        )

        layout = QtWidgets.QVBoxLayout(self)

        # Folder list
        self.list_widget = QtWidgets.QListWidget()
        for folder in folders:
            self.list_widget.addItem(folder)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("Add Folder")
        self.add_btn.setIcon(
            QtGui.QIcon(
                pyqt.get_icon("mgear_folder-plus", _ICON_SIZE)
            )
        )
        self.add_btn.clicked.connect(self._add_folder)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.remove_btn.setIcon(
            QtGui.QIcon(
                pyqt.get_icon("mgear_folder-minus", _ICON_SIZE)
            )
        )
        self.remove_btn.clicked.connect(self._remove_folder)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        self.up_btn = QtWidgets.QPushButton("Up")
        self.up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QtWidgets.QPushButton("Down")
        self.down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self.down_btn)

        layout.addLayout(btn_layout)

        # OK / Cancel
        dialog_btn_layout = QtWidgets.QHBoxLayout()
        dialog_btn_layout.addStretch()
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_btn_layout.addWidget(ok_btn)
        dialog_btn_layout.addWidget(cancel_btn)
        layout.addLayout(dialog_btn_layout)

    def get_folders(self):
        """Get the current folder list.

        Returns:
            list: List of folder path strings.
        """
        return [
            self.list_widget.item(i).text()
            for i in range(self.list_widget.count())
        ]

    def _add_folder(self):
        """Add a folder via directory browser."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Matcap Folder"
        )
        if folder:
            existing = self.get_folders()
            if folder not in existing:
                self.list_widget.addItem(folder)

    def _remove_folder(self):
        """Remove selected folder."""
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def _move_up(self):
        """Move selected folder up."""
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        """Move selected folder down."""
        row = self.list_widget.currentRow()
        if row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)
