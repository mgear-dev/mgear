"""Deformer IO - Shared dialog for the deformer IO tools.

Base dockable window with an Export tab (scene deformers, From Selection,
deformer order), an Import tab (file preview with a per-deformer order,
Replace existing) and a log panel. Tools such as Lattice IO and Shrink
Wrap IO subclass :class:`DeformerIOUI`, set ``FORMAT`` (their
:class:`mgear.core.deformer_io.DeformerFormat`) and the class constants,
and implement the scene hooks.

Example:
    >>> class MyIOUI(DeformerIOUI):
    ...     TOOL_NAME = "MyIO"
    ...     toolName = TOOL_NAME
    ...     FORMAT = core.FORMAT
    ...     def scene_nodes(self):
    ...         return cmds.ls(type="cluster")
"""

import os

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtWidgets

from mgear.core import deformer_io
from mgear.core import node_remap
from mgear.core import pyqt
from mgear.core import utils
from mgear.core import widgets

from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

# Item data role of the Export list: the deformer name
NODE_ROLE = QtCore.Qt.UserRole

ORDER_LABELS = (
    (deformer_io.ORDER_CURRENT, "Current (as exported)"),
    (deformer_io.ORDER_FRONT, "Front of chain"),
    (deformer_io.ORDER_LAST, "Last (append)"),
)

ORDER_TOOLTIP = (
    "Where the deformer goes in each geometry deformer stack on import.\n"
    "Current: the position it had when exported (Last if not found).\n"
    "Front of chain: before all the existing deformers.\n"
    "Last: after all the existing deformers, like a new deformer."
)


def create_order_combo(mode=deformer_io.ORDER_CURRENT):
    """Create a combo box to choose a deformer order mode.

    Args:
        mode (str, optional): Initial mode.

    Returns:
        QtWidgets.QComboBox: The combo box. The mode is the item data.
    """
    combo = QtWidgets.QComboBox()
    for value, label in ORDER_LABELS:
        combo.addItem(label, value)
    combo.setCurrentIndex(max(combo.findData(mode), 0))
    combo.setToolTip(ORDER_TOOLTIP)
    return combo


class DeformerIOUI(MayaQWidgetDockableMixin, QtWidgets.QDialog, pyqt.SettingsMixin):
    """Base dockable dialog to export and import deformer configurations.

    Subclasses set ``FORMAT`` and the class constants, and implement the
    scene hooks: :meth:`scene_nodes`, :meth:`scene_label`,
    :meth:`find_from_selection`, :meth:`select_nodes` and
    :meth:`item_extra`. File export, preview and import go through
    ``FORMAT``.
    """

    TOOL_NAME = "DeformerIO"
    toolName = TOOL_NAME
    TOOL_TITLE = "Deformer IO"
    # deformer_io.DeformerFormat of the tool
    FORMAT = None
    FILE_LABEL = "Deformer Config"
    EXTRA_FILTERS = ()
    SETTINGS_PREFIX = "deformer_io"
    NAME_COLUMN = "Deformer"
    EXTRA_COLUMN = ""

    def __init__(self, parent=None):
        """Initialize the dialog.

        Args:
            parent (QtWidgets.QWidget, optional): Parent widget.
        """
        super(DeformerIOUI, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self.setObjectName(self.TOOL_NAME)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setMinimumWidth(380)

        if cmds.about(ntOS=True):
            flags = self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
            self.setWindowFlags(flags)
        elif cmds.about(macOS=True):
            self.setWindowFlags(QtCore.Qt.Tool)

        self.setup_ui()

        # The export order is not stored: it always starts as Current
        self.user_settings = {
            self.SETTINGS_PREFIX + "_replace": (self.replace_cb, True)
        }
        self.load_settings()

        # Show the tool log, and the core modules it uses, in the log panel
        # while the window is open
        self.logger = self.FORMAT.log
        self.log_handler = pyqt.QtLogHandler(self.log_output)
        self.log_handler.attach(self.logger, deformer_io.logger, node_remap.logger)
        self.refresh_scene_list()
        self.resize(520, 600)

    # =========================================================
    # HOOKS
    # =========================================================

    def scene_nodes(self):
        """Return the deformers of the tool's type in the scene.

        Returns:
            list: Deformer names.
        """
        raise NotImplementedError

    def scene_label(self, node):
        """Return the Export list label of a scene deformer.

        Args:
            node (str): Deformer name.

        Returns:
            str: Label.
        """
        return node

    def find_from_selection(self, nodes):
        """Return the deformers related to selected nodes.

        Args:
            nodes (list): Selected node or component names.

        Returns:
            list: Deformer names.
        """
        raise NotImplementedError

    def select_nodes(self, node):
        """Return the Maya nodes to select for a deformer in the list.

        Args:
            node (str): Deformer name.

        Returns:
            list: Node names.
        """
        return [node]

    def item_extra(self, config):
        """Return the text of the tool-specific preview column.

        Args:
            config (dict): Configuration.

        Returns:
            str: Text.
        """
        return ""

    # =========================================================
    # UI SETUP
    # =========================================================

    def setup_ui(self):
        """Build the user interface."""
        self.create_actions()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_actions(self):
        """Create menu actions."""
        self.export_action = QtWidgets.QAction("Export Selected...", self)
        self.export_action.setShortcut(QtGui.QKeySequence.Save)
        self.open_action = QtWidgets.QAction("Open Configuration...", self)
        self.open_action.setShortcut(QtGui.QKeySequence.Open)

    def create_widgets(self):
        """Create all widgets."""
        self.menu_bar = QtWidgets.QMenuBar()
        self.file_menu = self.menu_bar.addMenu("File")
        self.file_menu.addAction(self.export_action)
        self.file_menu.addAction(self.open_action)
        self.recent_menu = widgets.RecentFilesMenu(
            self.SETTINGS_PREFIX + "_recent_files", parent=self.file_menu
        )
        self.file_menu.addMenu(self.recent_menu)

        self.tabs = QtWidgets.QTabWidget()

        # Export
        self.scene_list = QtWidgets.QListWidget()
        self.scene_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.from_sel_btn = QtWidgets.QPushButton("From Selection")
        self.export_order_combo = create_order_combo()
        self.export_btn = QtWidgets.QPushButton("Export Selected...")

        # Import
        self.path_le = QtWidgets.QLineEdit()
        self.path_le.setPlaceholderText("{} file".format(self.FILE_LABEL))
        self.browse_btn = QtWidgets.QPushButton("...")
        self.browse_btn.setFixedWidth(30)
        self.file_tree = QtWidgets.QTreeWidget()
        self.file_tree.setHeaderLabels(
            [self.NAME_COLUMN, "Order", self.EXTRA_COLUMN, "Geometry", "Weights"]
        )
        self.file_tree.setColumnHidden(2, not self.EXTRA_COLUMN)
        self.file_tree.setRootIsDecorated(False)
        self.replace_cb = QtWidgets.QCheckBox("Replace existing")
        self.replace_cb.setChecked(True)
        self.replace_cb.setToolTip(
            "Delete {}s with the same names before rebuilding them".format(
                self.FORMAT.label
            )
        )
        self.import_btn = QtWidgets.QPushButton("Import Checked")

        # Log
        self.log_output = QtWidgets.QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(130)

    def create_layout(self):
        """Lay out all widgets."""
        export_tab = QtWidgets.QWidget()
        export_layout = QtWidgets.QVBoxLayout(export_tab)
        export_layout.addWidget(
            QtWidgets.QLabel("Scene {}s:".format(self.FORMAT.label))
        )
        export_layout.addWidget(self.scene_list)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.from_sel_btn)
        export_layout.addLayout(btn_layout)
        order_layout = QtWidgets.QHBoxLayout()
        order_layout.addWidget(QtWidgets.QLabel("Deformer order:"))
        order_layout.addWidget(self.export_order_combo, 1)
        export_layout.addLayout(order_layout)
        export_layout.addWidget(self.export_btn)

        import_tab = QtWidgets.QWidget()
        import_layout = QtWidgets.QVBoxLayout(import_tab)
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(self.path_le)
        path_layout.addWidget(self.browse_btn)
        import_layout.addLayout(path_layout)
        import_layout.addWidget(self.file_tree)
        import_layout.addWidget(self.replace_cb)
        import_layout.addWidget(self.import_btn)

        self.tabs.addTab(export_tab, "Export")
        self.tabs.addTab(import_tab, "Import")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(QtWidgets.QLabel("Log:"))
        main_layout.addWidget(self.log_output)

    def create_connections(self):
        """Connect signals."""
        self.export_action.triggered.connect(self.export_selected)
        self.open_action.triggered.connect(self.browse_file)
        self.recent_menu.fileTriggered.connect(self.open_file)
        self.refresh_btn.clicked.connect(self.refresh_scene_list)
        self.from_sel_btn.clicked.connect(self.select_from_scene)
        self.export_btn.clicked.connect(self.export_selected)
        self.browse_btn.clicked.connect(self.browse_file)
        self.path_le.editingFinished.connect(self.load_preview)
        self.import_btn.clicked.connect(self.import_checked)
        self.scene_list.itemSelectionChanged.connect(self.sync_selection)

    # =========================================================
    # EXPORT
    # =========================================================

    def file_filter(self):
        """Return the file dialog filter.

        Returns:
            str: Qt file filter.
        """
        filters = ["{} (*{})".format(self.FILE_LABEL, self.FORMAT.ext)]
        filters += list(self.EXTRA_FILTERS)
        filters.append("All Files (*.*)")
        return ";;".join(filters)

    def refresh_scene_list(self):
        """Populate the list with the scene deformers."""
        self.scene_list.clear()
        for node in self.scene_nodes():
            item = QtWidgets.QListWidgetItem(self.scene_label(node))
            item.setData(NODE_ROLE, node)
            self.scene_list.addItem(item)

    def select_from_scene(self):
        """Select the list items matching the Maya selection."""
        nodes = self.find_from_selection(cmds.ls(selection=True))
        with pyqt.block_signals(self.scene_list):
            for i in range(self.scene_list.count()):
                item = self.scene_list.item(i)
                item.setSelected(item.data(NODE_ROLE) in nodes)

    def sync_selection(self):
        """Select the nodes of the selected list items in Maya."""
        nodes = []
        for item in self.scene_list.selectedItems():
            nodes += self.select_nodes(item.data(NODE_ROLE))
        if nodes:
            cmds.select(nodes, replace=True)

    def export_selected(self):
        """Export the selected deformers to a file."""
        nodes = [i.data(NODE_ROLE) for i in self.scene_list.selectedItems()]
        if not nodes:
            self.logger.warning("Nothing selected to export.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export {}".format(self.FILE_LABEL),
            self._start_dir(),
            self.file_filter(),
        )
        if not path:
            return
        path = self.FORMAT.file_path(path)
        try:
            self.FORMAT.export(nodes, path, self.export_order_combo.currentData())
        except Exception as err:  # noqa: BLE001 - report any failure in UI
            self.logger.error("Export failed: %s", err)
            return
        self.open_file(path)

    # =========================================================
    # IMPORT
    # =========================================================

    def browse_file(self):
        """Browse for a configuration file to import."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import {}".format(self.FILE_LABEL),
            self._start_dir(),
            self.file_filter(),
        )
        if path:
            self.open_file(path)

    def open_file(self, path):
        """Show a configuration file in the Import tab.

        Args:
            path (str): Configuration file path.
        """
        self.path_le.setText(path)
        if self.load_preview():
            self.recent_menu.add_file(path)
            self.tabs.setCurrentIndex(1)

    def load_preview(self):
        """Show the content of the configuration file in the tree.

        Returns:
            bool: True if the file was loaded.
        """
        self.file_tree.clear()
        path = self.path_le.text()
        if not path or not os.path.isfile(path):
            return False
        try:
            data = self.FORMAT.load(path)
        except (ValueError, OSError) as err:
            self.logger.error(str(err))
            return False

        for config in self.FORMAT.items(data):
            geos = [deformer_io.entry_label(g) for g in config.get("geometry", [])]
            has_weights = any(g.get("weights") for g in config.get("geometry", []))
            item = QtWidgets.QTreeWidgetItem(
                [
                    self.FORMAT.name(config),
                    "",
                    self.item_extra(config),
                    ", ".join(geos),
                    "Yes" if has_weights else "No",
                ]
            )
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(0, QtCore.Qt.Checked)
            item.setToolTip(3, "\n".join(geos))
            self.file_tree.addTopLevelItem(item)

            try:
                mode = self.FORMAT.resolve_order(config)
            except ValueError as err:
                self.logger.warning("%s, using current.", err)
                mode = deformer_io.ORDER_CURRENT
            self.file_tree.setItemWidget(item, 1, create_order_combo(mode))

        for col in range(self.file_tree.columnCount()):
            self.file_tree.resizeColumnToContents(col)
        return True

    def import_checked(self):
        """Import the checked deformers from the file."""
        path = self.path_le.text()
        if not path or not os.path.isfile(path):
            self.logger.warning("Select a valid file first.")
            return
        names = []
        order = {}
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.checkState(0) != QtCore.Qt.Checked:
                continue
            name = item.text(0)
            names.append(name)
            order[name] = self.file_tree.itemWidget(item, 1).currentData()
        if not names:
            self.logger.warning("Nothing checked to import.")
            return
        try:
            self.FORMAT.import_file(path, names, self.replace_cb.isChecked(), order)
        except Exception as err:  # noqa: BLE001 - report any failure in UI
            self.logger.error("Import failed: %s", err)
        self.refresh_scene_list()

    # =========================================================
    # MISC
    # =========================================================

    def _start_dir(self):
        """Return the starting directory for file dialogs.

        Returns:
            str: Directory path.
        """
        path = self.path_le.text()
        if path:
            return os.path.dirname(path)
        return utils.get_workspace_folder("scenes")

    def closeEvent(self, event):
        """Remove the log handler when closing.

        Args:
            event (QtGui.QCloseEvent): Close event.
        """
        self.log_handler.detach()
        super(DeformerIOUI, self).closeEvent(event)

    def dockCloseEventTriggered(self):
        """Remove the log handler when the docked window is closed."""
        self.log_handler.detach()
