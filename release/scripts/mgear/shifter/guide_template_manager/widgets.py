"""Guide Template Manager - Custom Qt Widgets.

TemplateTreeWidget, TemplateInfoPanel, SourceFoldersDialog,
and ImportPartialDialog for the guide template manager.
"""

import datetime
import os

from maya import cmds

from mgear.core import pyqt

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

from . import core

_ICON_SIZE = int(pyqt.dpi_scale(16))


# =================================================================
# TEMPLATE TREE WIDGET
# =================================================================


class TemplateTreeWidget(QtWidgets.QTreeWidget):
    """Tree widget displaying template folders and .sgt files.

    Supports drag-out to Maya viewport, double-click import,
    and right-click context menu for import actions.

    Signals:
        template_selected(str): Emitted when a template is clicked.
        import_requested(str): Emitted for full import.
        import_add_requested(str): Emitted for import-add to selection.
        import_partial_requested(str): Emitted for partial import.
    """

    template_selected = QtCore.Signal(str)
    import_requested = QtCore.Signal(str)
    import_add_requested = QtCore.Signal(str)
    import_partial_requested = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(TemplateTreeWidget, self).__init__(parent)

        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setMinimumWidth(int(pyqt.dpi_scale(200)))

        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.customContextMenuRequested.connect(
            self._show_context_menu
        )

    def populate(self, folder_entries):
        """Populate the tree from scan results.

        Args:
            folder_entries (list): List of FolderEntry objects.
        """
        self.clear()
        for folder_entry in folder_entries:
            self._add_folder(folder_entry, self)

    def _add_folder(self, folder_entry, parent):
        """Recursively add a folder and its contents to the tree.

        Args:
            folder_entry: FolderEntry object.
            parent: Parent tree item or tree widget.
        """
        folder_item = QtWidgets.QTreeWidgetItem(parent)
        folder_item.setText(0, folder_entry.label)
        folder_item.setIcon(
            0, QtGui.QIcon(pyqt.get_icon("mgear_folder", _ICON_SIZE))
        )
        folder_item.setData(0, QtCore.Qt.UserRole, None)
        folder_item.setExpanded(True)

        for subfolder in folder_entry.subfolders:
            self._add_folder(subfolder, folder_item)

        for template in folder_entry.templates:
            file_item = QtWidgets.QTreeWidgetItem(folder_item)
            file_item.setText(0, template.name)
            file_item.setIcon(
                0,
                QtGui.QIcon(
                    pyqt.get_icon("mgear_file-text", _ICON_SIZE)
                ),
            )
            file_item.setData(
                0, QtCore.Qt.UserRole, template.sgt_path
            )
            file_item.setToolTip(0, template.sgt_path)

            # Use cached info for tags (populated by
            # ensure_all_sgt_info before tree population)
            info = template.info
            tags = ""
            if info:
                tag_list = info.get("tags", [])
                if tag_list:
                    tags = " ".join(tag_list).lower()
            file_item.setData(
                0, QtCore.Qt.UserRole + 1, tags
            )

    def _get_selected_path(self):
        """Get the .sgt path of the currently selected item.

        Returns:
            str: File path, or None if no template is selected.
        """
        items = self.selectedItems()
        if not items:
            return None
        return items[0].data(0, QtCore.Qt.UserRole)

    def _on_item_clicked(self, item, column):
        """Handle item click.

        Args:
            item: Clicked tree item.
            column: Column index.
        """
        path = item.data(0, QtCore.Qt.UserRole)
        if path:
            self.template_selected.emit(path)

    def _on_item_double_clicked(self, item, column):
        """Handle double-click to import.

        Args:
            item: Double-clicked tree item.
            column: Column index.
        """
        path = item.data(0, QtCore.Qt.UserRole)
        if path:
            self.import_requested.emit(path)

    def _show_context_menu(self, pos):
        """Show right-click context menu.

        Args:
            pos: Mouse position in widget coordinates.
        """
        path = self._get_selected_path()
        if not path:
            return

        menu = QtWidgets.QMenu(self)

        import_action = menu.addAction("导入")
        import_action.triggered.connect(
            lambda *args: self.import_requested.emit(path)
        )

        import_add_action = menu.addAction("导入并添加到选择")
        import_add_action.triggered.connect(
            lambda *args: self.import_add_requested.emit(path)
        )

        import_partial_action = menu.addAction(
            "部分导入到选择..."
        )
        import_partial_action.triggered.connect(
            lambda *args: self.import_partial_requested.emit(path)
        )

        menu.exec_(self.mapToGlobal(pos))

    def startDrag(self, supportedActions):
        """Override drag start to create URL-based MIME data.

        Args:
            supportedActions: Supported drag actions.
        """
        path = self._get_selected_path()
        if not path:
            return

        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()
        url = QtCore.QUrl.fromLocalFile(path)
        mime_data.setUrls([url])
        drag.setMimeData(mime_data)
        drag.exec_(QtCore.Qt.CopyAction)

    def filter_by_text(self, text):
        """Show/hide items based on text search.

        Args:
            text (str): Search text (case-insensitive).
        """
        text = text.lower().strip()
        root = self.invisibleRootItem()
        self._filter_item(root, text)

    def _filter_item(self, item, text):
        """Recursively filter tree items.

        Args:
            item: Tree item.
            text (str): Search text (lowercase).

        Returns:
            bool: True if this item or any child is visible.
        """
        if not text:
            item.setHidden(False)
            for i in range(item.childCount()):
                self._filter_item(item.child(i), "")
            return True

        # Leaf item (template file)
        path = item.data(0, QtCore.Qt.UserRole)
        if path is not None:
            name_match = text in item.text(0).lower()
            tags = item.data(0, QtCore.Qt.UserRole + 1) or ""
            tag_match = text in tags
            match = name_match or tag_match
            item.setHidden(not match)
            return match

        # Folder item — visible if any child matches
        any_visible = False
        for i in range(item.childCount()):
            child_visible = self._filter_item(item.child(i), text)
            any_visible = any_visible or child_visible

        item.setHidden(not any_visible)
        if any_visible:
            item.setExpanded(True)
        return any_visible


# =================================================================
# TEMPLATE INFO PANEL
# =================================================================


class TemplateInfoPanel(QtWidgets.QWidget):
    """Right-side panel showing template metadata and thumbnail.

    Args:
        parent: Parent widget.
    """

    def __init__(self, parent=None):
        super(TemplateInfoPanel, self).__init__(parent)

        self._current_path = None

        self._create_widgets()
        self._create_layout()
        self._create_connections()

    def _create_widgets(self):
        """Create all widgets."""
        # Thumbnail
        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setAlignment(QtCore.Qt.AlignCenter)
        self.thumbnail_label.setMinimumSize(
            int(pyqt.dpi_scale(200)),
            int(pyqt.dpi_scale(200)),
        )
        self.thumbnail_label.setStyleSheet(
            "QLabel {"
            "    background-color: #2a2a2a;"
            "    border: 1px solid #555;"
            "    border-radius: 4px;"
            "}"
        )
        self._set_placeholder_thumbnail()

        # Template name
        self.name_label = QtWidgets.QLabel("未选择模板")
        self.name_label.setStyleSheet(
            "font-weight: bold; font-size: 14px;"
        )
        self.name_label.setWordWrap(True)

        # Description
        self.description_label = QtWidgets.QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #aaa;")

        # Metadata
        self.author_label = QtWidgets.QLabel("")
        self.author_label.setStyleSheet("color: #888;")
        self.date_label = QtWidgets.QLabel("")
        self.date_label.setStyleSheet("color: #888;")
        self.components_label = QtWidgets.QLabel("")
        self.components_label.setStyleSheet("color: #888;")
        self.tags_label = QtWidgets.QLabel("")
        self.tags_label.setWordWrap(True)
        self.tags_label.setStyleSheet("color: #7aa3cc;")

        # Action buttons
        self.capture_btn = QtWidgets.QPushButton("捕获截图")
        self.capture_btn.setIcon(
            QtGui.QIcon(pyqt.get_icon("mgear_camera", _ICON_SIZE))
        )
        self.capture_btn.setEnabled(False)

        self.browse_image_btn = QtWidgets.QPushButton("浏览图片...")
        self.browse_image_btn.setIcon(
            QtGui.QIcon(pyqt.get_icon("mgear_image", _ICON_SIZE))
        )
        self.browse_image_btn.setEnabled(False)

        self.edit_info_btn = QtWidgets.QPushButton("编辑信息")
        self.edit_info_btn.setIcon(
            QtGui.QIcon(pyqt.get_icon("mgear_edit", _ICON_SIZE))
        )
        self.edit_info_btn.setEnabled(False)

    def _create_layout(self):
        """Arrange widgets in layout."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self.thumbnail_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.description_label)

        # Metadata group
        meta_layout = QtWidgets.QVBoxLayout()
        meta_layout.setSpacing(2)
        meta_layout.addWidget(self.author_label)
        meta_layout.addWidget(self.date_label)
        meta_layout.addWidget(self.components_label)
        meta_layout.addWidget(self.tags_label)
        layout.addLayout(meta_layout)

        layout.addStretch()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.capture_btn)
        btn_layout.addWidget(self.browse_image_btn)
        layout.addLayout(btn_layout)
        layout.addWidget(self.edit_info_btn)

    def _create_connections(self):
        """Connect signals to slots."""
        self.capture_btn.clicked.connect(self._capture_screenshot)
        self.browse_image_btn.clicked.connect(self._browse_image)
        self.edit_info_btn.clicked.connect(self._edit_info)

    def set_template(self, sgt_path):
        """Display info for the given template.

        Args:
            sgt_path (str): Path to the .sgt file.
        """
        self._current_path = sgt_path

        # Enable buttons
        self.capture_btn.setEnabled(True)
        self.browse_image_btn.setEnabled(True)
        self.edit_info_btn.setEnabled(True)

        # Template name
        name = os.path.splitext(os.path.basename(sgt_path))[0]
        self.name_label.setText(name)

        # Load thumbnail
        thumb_path = core.get_thumbnail_path(sgt_path)
        if os.path.isfile(thumb_path):
            pixmap = QtGui.QPixmap(thumb_path)
            self.thumbnail_label.setPixmap(
                pixmap.scaled(
                    self.thumbnail_label.size(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
            )
        else:
            self._set_placeholder_thumbnail()

        # Load metadata
        info = core.read_sgt_info(sgt_path)
        if info:
            self.description_label.setText(
                info.get("description", "")
            )
            author = info.get("author", "")
            if author:
                self.author_label.setText(
                    "作者: {}".format(author)
                )
            else:
                self.author_label.setText("")

            date = info.get("date_modified") or info.get(
                "date_created", ""
            )
            if date:
                self.date_label.setText("日期: {}".format(date))
            else:
                self.date_label.setText("")

            count = info.get("components_count", 0)
            self.components_label.setText(
                "组件: {}".format(count)
            )

            tags = info.get("tags", [])
            if tags:
                self.tags_label.setText(
                    "标签: {}".format(", ".join(tags))
                )
            else:
                self.tags_label.setText("")
        else:
            self.description_label.setText("无可用元数据")
            self.author_label.setText("")
            self.date_label.setText("")
            self.components_label.setText("")
            self.tags_label.setText("")

    def clear_template(self):
        """Reset the panel to empty state."""
        self._current_path = None
        self.name_label.setText("未选择模板")
        self.description_label.setText("")
        self.author_label.setText("")
        self.date_label.setText("")
        self.components_label.setText("")
        self.tags_label.setText("")
        self._set_placeholder_thumbnail()
        self.capture_btn.setEnabled(False)
        self.browse_image_btn.setEnabled(False)
        self.edit_info_btn.setEnabled(False)

    def _set_placeholder_thumbnail(self):
        """Set a placeholder icon in the thumbnail area."""
        pixmap = pyqt.get_icon("mgear_image", 64)
        self.thumbnail_label.setPixmap(pixmap)

    def _capture_screenshot(self):
        """Capture viewport and save as thumbnail."""
        if not self._current_path:
            return

        save_path = core.get_thumbnail_path(self._current_path)
        result = core.capture_viewport_thumbnail(save_path)
        if result:
            self.set_template(self._current_path)
        else:
            cmds.warning("截取视口失败")

    def _browse_image(self):
        """Browse for a custom thumbnail image."""
        if not self._current_path:
            return

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择缩略图图片",
            "",
            "图片 (*.png *.jpg *.jpeg *.bmp)",
        )

        if not file_path:
            return

        # Copy/convert to the thumbnail location
        save_path = core.get_thumbnail_path(self._current_path)
        pixmap = QtGui.QPixmap(file_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                core.THUMBNAIL_SIZE[0],
                core.THUMBNAIL_SIZE[1],
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            scaled.save(save_path, "PNG")
            self.set_template(self._current_path)

    def _edit_info(self):
        """Open a dialog to edit the template metadata."""
        if not self._current_path:
            return

        info = core.read_sgt_info(self._current_path) or {}

        dialog = EditInfoDialog(info, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            updated = dialog.get_info()
            updated["date_modified"] = (
                datetime.datetime.now().strftime("%Y-%m-%d")
            )
            core.write_sgt_info(self._current_path, updated)
            self.set_template(self._current_path)


# =================================================================
# EDIT INFO DIALOG
# =================================================================


class EditInfoDialog(QtWidgets.QDialog):
    """Dialog for editing template metadata.

    Args:
        info (dict): Current metadata dictionary.
        parent: Parent widget.
    """

    def __init__(self, info, parent=None):
        super(EditInfoDialog, self).__init__(parent)

        self.setWindowTitle("编辑模板信息")
        self.setMinimumWidth(int(pyqt.dpi_scale(400)))

        self._info = dict(info)

        layout = QtWidgets.QVBoxLayout(self)

        # Name
        layout.addWidget(QtWidgets.QLabel("名称:"))
        self.name_edit = QtWidgets.QLineEdit(
            info.get("name", "")
        )
        layout.addWidget(self.name_edit)

        # Description
        layout.addWidget(QtWidgets.QLabel("描述:"))
        self.desc_edit = QtWidgets.QTextEdit()
        self.desc_edit.setPlainText(info.get("description", ""))
        self.desc_edit.setMaximumHeight(int(pyqt.dpi_scale(100)))
        layout.addWidget(self.desc_edit)

        # Author
        layout.addWidget(QtWidgets.QLabel("作者:"))
        self.author_edit = QtWidgets.QLineEdit(
            info.get("author", "")
        )
        layout.addWidget(self.author_edit)

        # Tags
        layout.addWidget(QtWidgets.QLabel("标签(逗号分隔):"))
        tags = info.get("tags", [])
        self.tags_edit = QtWidgets.QLineEdit(
            ", ".join(tags) if tags else ""
        )
        layout.addWidget(self.tags_edit)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_info(self):
        """Get the updated info dictionary.

        Returns:
            dict: Updated metadata.
        """
        info = dict(self._info)
        info["name"] = self.name_edit.text().strip()
        info["description"] = self.desc_edit.toPlainText().strip()
        info["author"] = self.author_edit.text().strip()

        tags_text = self.tags_edit.text().strip()
        if tags_text:
            info["tags"] = [
                t.strip() for t in tags_text.split(",") if t.strip()
            ]
        else:
            info["tags"] = []

        return info


# =================================================================
# SOURCE FOLDERS DIALOG
# =================================================================


class SourceFoldersDialog(QtWidgets.QDialog):
    """Dialog for managing custom source folders.

    Args:
        folders (list): Current list of folder paths.
        parent: Parent widget.
    """

    def __init__(self, folders, parent=None):
        super(SourceFoldersDialog, self).__init__(parent)

        self.setWindowTitle("源文件夹")
        self.setMinimumSize(
            int(pyqt.dpi_scale(500)),
            int(pyqt.dpi_scale(300)),
        )

        layout = QtWidgets.QVBoxLayout(self)

        # Folder list
        self.list_widget = QtWidgets.QListWidget()
        for folder in folders:
            self.list_widget.addItem(folder)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self.add_btn = QtWidgets.QPushButton("添加文件夹")
        self.add_btn.setIcon(
            QtGui.QIcon(
                pyqt.get_icon("mgear_folder-plus", _ICON_SIZE)
            )
        )
        self.add_btn.clicked.connect(self._add_folder)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QtWidgets.QPushButton("移除")
        self.remove_btn.setIcon(
            QtGui.QIcon(
                pyqt.get_icon("mgear_folder-minus", _ICON_SIZE)
            )
        )
        self.remove_btn.clicked.connect(self._remove_folder)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        self.up_btn = QtWidgets.QPushButton("上移")
        self.up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self.up_btn)

        self.down_btn = QtWidgets.QPushButton("下移")
        self.down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self.down_btn)

        layout.addLayout(btn_layout)

        # OK / Cancel
        dialog_btn_layout = QtWidgets.QHBoxLayout()
        dialog_btn_layout.addStretch()
        ok_btn = QtWidgets.QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("取消")
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
            self, "选择模板文件夹"
        )
        if folder:
            # Avoid duplicates
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


# =================================================================
# IMPORT PARTIAL DIALOG
# =================================================================


class ImportPartialDialog(QtWidgets.QDialog):
    """Dialog for selecting components to import partially.

    Shows the component hierarchy from a template with checkboxes
    for multi-selection. Checking a parent auto-checks children.

    Args:
        components (list): List of component info dicts from
            ``core.get_components_from_template()``.
        parent: Parent widget.
    """

    IMPORT = 1
    IMPORT_MATCH = 2

    def __init__(self, components, parent=None):
        super(ImportPartialDialog, self).__init__(parent)

        self.setWindowTitle("部分导入 - 选择组件")
        self.setMinimumSize(
            int(pyqt.dpi_scale(500)),
            int(pyqt.dpi_scale(400)),
        )

        self._components = components
        self._action = self.IMPORT

        # Build parent lookup for hierarchy filtering
        self._parent_map = {}
        for comp in components:
            self._parent_map[comp["name"]] = comp.get("parent")

        layout = QtWidgets.QVBoxLayout(self)

        # Info label
        info_label = QtWidgets.QLabel(
            "选择要导入的组件.选中组件的 "
            "子组件将自动包含."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaa;")
        layout.addWidget(info_label)

        # Component tree
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["组件", "类型"])
        self.tree.setColumnWidth(0, int(pyqt.dpi_scale(250)))
        self.tree.setStyleSheet(
            "QTreeWidget::indicator:unchecked {"
            "    border: 1px solid #888;"
            "    background-color: #333;"
            "    width: 14px;"
            "    height: 14px;"
            "}"
            "QTreeWidget::indicator:checked {"
            "    border: 1px solid #5285a6;"
            "    background-color: #5285a6;"
            "    width: 14px;"
            "    height: 14px;"
            "}"
        )
        layout.addWidget(self.tree)

        self._item_map = {}
        self._populate_tree()

        # Select All / Deselect All
        sel_layout = QtWidgets.QHBoxLayout()
        select_all_btn = QtWidgets.QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        deselect_all_btn = QtWidgets.QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self._deselect_all)
        sel_layout.addWidget(select_all_btn)
        sel_layout.addWidget(deselect_all_btn)
        sel_layout.addStretch()
        layout.addLayout(sel_layout)

        # Action buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        import_btn = QtWidgets.QPushButton("导入选中项")
        import_btn.setStyleSheet("background-color: #4a7c4e;")
        import_btn.clicked.connect(self._accept_import)
        import_match_btn = QtWidgets.QPushButton(
            "导入并匹配位置"
        )
        import_match_btn.setStyleSheet("background-color: #4a6c7e;")
        import_match_btn.setToolTip(
            "导入选中组件并将根节点位置 "
            "匹配到选中的引导元素"
        )
        import_match_btn.clicked.connect(self._accept_import_match)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(import_match_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # Connect check state changes
        self.tree.itemChanged.connect(self._on_item_changed)

    def _populate_tree(self):
        """Build the component tree with checkboxes."""
        # Build parent lookup
        children_of = {}
        for comp in self._components:
            parent = comp.get("parent")
            if parent not in children_of:
                children_of[parent] = []
            children_of[parent].append(comp)

        # Add root components (no parent)
        roots = children_of.get(None, [])
        for comp in roots:
            self._add_component(comp, self.tree, children_of)

        self.tree.expandAll()

    def _add_component(self, comp, parent_item, children_of):
        """Add a component item to the tree.

        Args:
            comp (dict): Component info dict.
            parent_item: Parent tree item or tree widget.
            children_of (dict): Children lookup dict.
        """
        item = QtWidgets.QTreeWidgetItem(parent_item)
        item.setText(0, comp["name"])
        item.setText(1, comp["comp_type"])
        item.setFlags(
            item.flags() | QtCore.Qt.ItemIsUserCheckable
        )
        item.setCheckState(0, QtCore.Qt.Unchecked)
        item.setData(0, QtCore.Qt.UserRole, comp["name"])

        self._item_map[comp["name"]] = item

        # Add children
        children = children_of.get(comp["name"], [])
        for child in children:
            self._add_component(child, item, children_of)

    def _on_item_changed(self, item, column):
        """Auto-check/uncheck children when parent changes.

        Args:
            item: Changed tree item.
            column: Column index.
        """
        if column != 0:
            return

        state = item.checkState(0)
        self.tree.blockSignals(True)
        self._set_children_state(item, state)
        self.tree.blockSignals(False)

    def _set_children_state(self, item, state):
        """Recursively set check state on children.

        Args:
            item: Parent tree item.
            state: Qt check state.
        """
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_children_state(child, state)

    def _select_all(self):
        """Check all items."""
        self._set_all_check_state(QtCore.Qt.Checked)

    def _deselect_all(self):
        """Uncheck all items."""
        self._set_all_check_state(QtCore.Qt.Unchecked)

    def _set_all_check_state(self, state):
        """Set check state on all items.

        Args:
            state: Qt check state constant.
        """
        self.tree.blockSignals(True)
        for item in self._item_map.values():
            item.setCheckState(0, state)
        self.tree.blockSignals(False)

    def _accept_import(self):
        """Accept with standard import action."""
        self._action = self.IMPORT
        self.accept()

    def _accept_import_match(self):
        """Accept with import and match position action."""
        self._action = self.IMPORT_MATCH
        self.accept()

    def get_action(self):
        """Get the chosen import action.

        Returns:
            int: IMPORT or IMPORT_MATCH constant.
        """
        return self._action

    def get_selected_components(self):
        """Get the list of checked component names.

        Returns:
            list: List of component name strings.
        """
        selected = []
        for name, item in self._item_map.items():
            if item.checkState(0) == QtCore.Qt.Checked:
                selected.append(name)
        return selected

    def get_root_components(self):
        """Get only the top-level selected components.

        Returns only components whose parents are NOT also
        selected. This ensures ``draw_guide`` receives only
        the true roots and discovers children itself, preserving
        the serialized hierarchy.

        Returns:
            list: List of root component name strings.
        """
        selected = set(self.get_selected_components())
        roots = []
        for name in selected:
            parent = self._parent_map.get(name)
            if parent not in selected:
                roots.append(name)
        return roots
