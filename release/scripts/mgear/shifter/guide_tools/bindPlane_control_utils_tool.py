"""Guide bind-group browser for mGear guides.

"""

from __future__ import print_function

import re

from maya import cmds

from mgear.vendor.Qt import QtWidgets, QtCore, QtGui
from mgear.core import pyqt

try:
    basestring
except NameError:
    basestring = str


def find_bind_groups():
    """Find mGear bindControl guides grouped by bindGroup.

    Searches for transform nodes matching "*_root" and filters by:
      - has "isGearGuide" attribute
      - has "comp_type" attribute containing "bindControl"

    Then groups by the "bindGroup" string attribute. Empty or missing
    bindGroup values are placed in the "Empty" group.

    Returns:
        dict[str, list[str]]: Mapping:
            {bindGroup_name: [node1, node2, ...]}.
    """
    result = {}
    nodes = cmds.ls("*_root", type="transform") or []

    for node in nodes:
        if not cmds.attributeQuery("isGearGuide", node=node, exists=True):
            continue

        if not cmds.attributeQuery("comp_type", node=node, exists=True):
            continue

        comp_type = cmds.getAttr("{}.comp_type".format(node))
        if not comp_type:
            continue

        if "bindControl" not in comp_type:
            continue

        bind_group = "Empty"
        if cmds.attributeQuery("bindGroup", node=node, exists=True):
            raw_val = cmds.getAttr("{}.bindGroup".format(node))
            if isinstance(raw_val, basestring):
                stripped = raw_val.strip()
                if stripped:
                    bind_group = stripped

        if bind_group not in result:
            result[bind_group] = []
        result[bind_group].append(node)

    return result


class BindGroupBrowser(QtWidgets.QDialog):
    """Browser UI for mGear guide bind groups."""

    def __init__(self, parent=None):
        """Initialize the browser dialog.

        Args:
            parent (QtWidgets.QWidget, optional): Parent widget.
        """
        if parent is None:
            parent = pyqt.maya_main_window()

        super(BindGroupBrowser, self).__init__(parent)
        self.setWindowTitle("Guide Bind Groups")
        self.resize(380, 600)

        self._model = QtGui.QStandardItemModel()
        self._filter_pattern = ""

        self._create_widgets()
        self._create_layout()
        self._create_connections()

        self.refresh()

    def _create_widgets(self):
        """Create UI widgets."""
        # Filter (compact)
        self.filter_label = QtWidgets.QLabel("Filter (regex):")
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText(
            "Regex, case-insensitive, objects only"
        )

        # Tree
        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setModel(self._model)
        self.tree_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )

        # EDIT frame with header + contents
        self.edit_frame = QtWidgets.QFrame()
        self.edit_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)

        self.edit_toggle_btn = QtWidgets.QToolButton()
        self.edit_toggle_btn.setText("Edit")
        self.edit_toggle_btn.setCheckable(True)
        self.edit_toggle_btn.setChecked(True)
        self.edit_toggle_btn.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.edit_toggle_btn.setArrowType(QtCore.Qt.DownArrow)

        self.edit_contents = QtWidgets.QWidget()

        self.local_ghost_chk = QtWidgets.QCheckBox()
        self.local_ghost_chk.setChecked(False)

        self.ctl_size_spin = QtWidgets.QDoubleSpinBox()
        self.ctl_size_spin.setDecimals(3)
        self.ctl_size_spin.setRange(0.0, 10000.0)
        self.ctl_size_spin.setSingleStep(0.1)
        self.ctl_size_spin.setValue(1.0)

        self.bind_size_spin = QtWidgets.QDoubleSpinBox()
        self.bind_size_spin.setDecimals(3)
        self.bind_size_spin.setRange(0.0, 10000.0)
        self.bind_size_spin.setSingleStep(0.1)
        self.bind_size_spin.setValue(0.2)

        self.bind_group_edit = QtWidgets.QLineEdit()
        self.bind_group_edit.setText("")

        self.driven_layers_spin = QtWidgets.QSpinBox()
        self.driven_layers_spin.setRange(0, 10000)
        self.driven_layers_spin.setValue(1)

        self.apply_button = QtWidgets.QPushButton("Apply")
        self.refresh_button = QtWidgets.QPushButton("Refresh")

    def _create_layout(self):
        """Create and assign layouts."""
        # Filter layout
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_edit)

        # EDIT contents layout (form)
        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(6, 6, 6, 6)
        form_layout.addRow("Local ghost", self.local_ghost_chk)
        form_layout.addRow("Control size", self.ctl_size_spin)
        form_layout.addRow("Bind size", self.bind_size_spin)
        form_layout.addRow("Bind group", self.bind_group_edit)
        form_layout.addRow("Driven layers", self.driven_layers_spin)
        form_layout.addRow(self.apply_button)
        self.edit_contents.setLayout(form_layout)

        # EDIT frame layout: header + contents
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(6, 6, 6, 0)
        header_layout.addWidget(self.edit_toggle_btn)
        header_layout.addStretch()

        edit_main_layout = QtWidgets.QVBoxLayout(self.edit_frame)
        edit_main_layout.setContentsMargins(0, 0, 0, 0)
        edit_main_layout.addLayout(header_layout)
        edit_main_layout.addWidget(self.edit_contents)

        # Bottom layout
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.refresh_button)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.tree_view)
        main_layout.addWidget(self.edit_frame)
        main_layout.addLayout(bottom_layout)

    def _create_connections(self):
        """Connect signals and slots."""
        self.refresh_button.clicked.connect(self.refresh)
        self.tree_view.clicked.connect(self._on_item_clicked)
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        self.edit_toggle_btn.toggled.connect(self._on_edit_toggled)

    # ------------------------------------------------------------------
    # Data / tree handling
    # ------------------------------------------------------------------
    def refresh(self):
        """Refresh tree data from the current Maya scene."""
        self._model.clear()
        root_item = self._model.invisibleRootItem()

        groups = find_bind_groups()
        if not groups:
            empty_item = QtGui.QStandardItem(
                "No bindControl guides found"
            )
            empty_item.setEnabled(False)
            root_item.appendRow(empty_item)
            return

        for group_name in sorted(groups.keys()):
            group_nodes = sorted(groups[group_name])

            group_item = QtGui.QStandardItem(group_name)
            group_item.setEditable(False)
            group_item.setData(group_nodes, QtCore.Qt.UserRole)
            root_item.appendRow(group_item)

            for node in group_nodes:
                child_item = QtGui.QStandardItem(node)
                child_item.setEditable(False)
                child_item.setData(node, QtCore.Qt.UserRole)
                group_item.appendRow(child_item)

        self.tree_view.expandAll()
        self._apply_filter()

    def _collect_selected_nodes(self):
        """Collect all nodes from current tree selection.

        Returns:
            list[str]: Unique node names from all selected items.
        """
        selection_model = self.tree_view.selectionModel()
        if selection_model is None:
            return []

        indexes = selection_model.selectedIndexes()
        nodes_set = set()

        for index in indexes:
            item = self._model.itemFromIndex(index)
            if item is None:
                continue

            data = item.data(QtCore.Qt.UserRole)
            if not data:
                continue

            if isinstance(data, (list, tuple)):
                for n in data:
                    if cmds.objExists(n):
                        nodes_set.add(n)
            else:
                if cmds.objExists(data):
                    nodes_set.add(data)

        return sorted(nodes_set)

    # ------------------------------------------------------------------
    # Filter handling
    # ------------------------------------------------------------------
    def _on_filter_changed(self, text):
        """Callback when filter text changes.

        Args:
            text (str): New filter pattern.
        """
        self._filter_pattern = text or ""
        self._apply_filter()

    def _apply_filter(self):
        """Apply regex filter to child items (objects only)."""
        pattern = self._filter_pattern
        regex = None

        if pattern:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                regex = None

        root_item = self._model.invisibleRootItem()

        for i in range(root_item.rowCount()):
            group_item = root_item.child(i, 0)
            if group_item is None:
                continue

            group_index = group_item.index()
            # Only children are filtered, group rows are never hidden.
            for j in range(group_item.rowCount()):
                child_item = group_item.child(j, 0)
                if child_item is None:
                    continue

                show = True
                if regex is not None:
                    name = child_item.text() or ""
                    show = bool(regex.search(name))

                self.tree_view.setRowHidden(j, group_index, not show)

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------
    def _on_edit_toggled(self, checked):
        """Collapse/expand edit area via the header button.

        Args:
            checked (bool): Button checked state.
        """
        self.edit_contents.setVisible(checked)
        arrow = QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow
        self.edit_toggle_btn.setArrowType(arrow)

    def _update_edit_from_node(self, node):
        """Update EDIT section values from a given node.

        Args:
            node (str): Node name.
        """
        if not node or not cmds.objExists(node):
            return

        if cmds.attributeQuery("local_ghost", node=node, exists=True):
            try:
                val = cmds.getAttr("{}.local_ghost".format(node))
                self.local_ghost_chk.setChecked(bool(val))
            except Exception:
                pass

        if cmds.attributeQuery("ctlSize", node=node, exists=True):
            try:
                val = cmds.getAttr("{}.ctlSize".format(node))
                if val is not None:
                    self.ctl_size_spin.setValue(float(val))
            except Exception:
                pass

        if cmds.attributeQuery("bindSize", node=node, exists=True):
            try:
                val = cmds.getAttr("{}.bindSize".format(node))
                if val is not None:
                    self.bind_size_spin.setValue(float(val))
            except Exception:
                pass

        if cmds.attributeQuery("bindGroup", node=node, exists=True):
            try:
                val = cmds.getAttr("{}.bindGroup".format(node))
                if val is None:
                    val = ""
                self.bind_group_edit.setText(
                    val if isinstance(val, basestring) else ""
                )
            except Exception:
                pass

        if cmds.attributeQuery("driven_layers", node=node, exists=True):
            try:
                val = cmds.getAttr("{}.driven_layers".format(node))
                if val is not None:
                    self.driven_layers_spin.setValue(int(val))
            except Exception:
                pass

    def _on_item_clicked(self, index):
        """Handle clicks in the tree view.

        Mirrors the union of selected items to Maya selection and updates
        the EDIT values using the last clicked item.

        Args:
            index (QtCore.QModelIndex): Clicked model index.
        """
        item = self._model.itemFromIndex(index)
        if item is None:
            return

        data = item.data(QtCore.Qt.UserRole)
        focus_node = None

        if isinstance(data, (list, tuple)):
            for n in data:
                if cmds.objExists(n):
                    focus_node = n
                    break
        elif isinstance(data, basestring):
            if cmds.objExists(data):
                focus_node = data

        nodes = self._collect_selected_nodes()
        if nodes:
            cmds.select(nodes, r=True)
        else:
            cmds.select(clear=True)

        if focus_node:
            self._update_edit_from_node(focus_node)

    def _on_apply_clicked(self):
        """Apply EDIT values to attributes on selected components."""
        sel = cmds.ls(sl=True, long=True) or []
        if not sel:
            cmds.warning("No selection. Please select guide components.")
            return

        local_ghost = self.local_ghost_chk.isChecked()
        ctl_size = self.ctl_size_spin.value()
        bind_size = self.bind_size_spin.value()
        bind_group = self.bind_group_edit.text()
        driven_layers = self.driven_layers_spin.value()

        for node in sel:
            if not cmds.objExists(node):
                continue

            if cmds.attributeQuery(
                "local_ghost", node=node, exists=True
            ):
                attr = "{}.local_ghost".format(node)
                try:
                    cmds.setAttr(attr, bool(local_ghost))
                except Exception:
                    cmds.warning("Failed to set {}".format(attr))

            if cmds.attributeQuery("ctlSize", node=node, exists=True):
                attr = "{}.ctlSize".format(node)
                try:
                    cmds.setAttr(attr, float(ctl_size))
                except Exception:
                    cmds.warning("Failed to set {}".format(attr))

            if cmds.attributeQuery("bindSize", node=node, exists=True):
                attr = "{}.bindSize".format(node)
                try:
                    cmds.setAttr(attr, float(bind_size))
                except Exception:
                    cmds.warning("Failed to set {}".format(attr))

            if cmds.attributeQuery("bindGroup", node=node, exists=True):
                attr = "{}.bindGroup".format(node)
                try:
                    cmds.setAttr(attr, bind_group, type="string")
                except Exception:
                    cmds.warning("Failed to set {}".format(attr))

            if cmds.attributeQuery(
                "driven_layers", node=node, exists=True
            ):
                attr = "{}.driven_layers".format(node)
                try:
                    cmds.setAttr(attr, int(driven_layers))
                except Exception:
                    cmds.warning("Failed to set {}".format(attr))

        self.refresh()


def show_bind_group_browser():
    """Show the guide bind-group browser dialog."""
    return pyqt.showDialog(BindGroupBrowser)