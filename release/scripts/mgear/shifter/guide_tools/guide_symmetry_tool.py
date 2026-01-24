from __future__ import print_function

import re

from maya import cmds

from mgear.vendor.Qt import QtWidgets, QtCore
from mgear.core import pyqt
from mgear.shifter import guide_manager


def _get_shifter_roots():
    """Get all shifter component roots in the scene.

    Returns:
        list[str]: List of shifter root node names.
    """
    roots = cmds.ls("*_root", type="transform") or []
    shifter_roots = []

    for node in roots:
        if cmds.attributeQuery("isGearGuide",
                               node=node,
                               exists=True):
            shifter_roots.append(node)

    return shifter_roots


def _get_mirror_name(node):
    """Compute the mirror counterpart name for a shifter root.

    Args:
        node (str): Shifter root node name.

    Returns:
        str or None: Mirror node name or None if no side token found.
    """
    suffix = "_root"
    if not node.endswith(suffix):
        return None

    base = node[:-len(suffix)]

    idx = base.rfind("_L")
    side_char = None

    if idx != -1:
        side_char = "L"
    else:
        idx = base.rfind("_R")
        if idx != -1:
            side_char = "R"

    if side_char is None:
        return None

    other_side = "R" if side_char == "L" else "L"
    mirror_base = base[:idx] + "_" + other_side + base[idx + 2:]

    return mirror_base + suffix


def _get_component_side(node):
    """Get the side of a shifter component.

    Args:
        node (str): Shifter root node name.

    Returns:
        str or None: 'L', 'R', or None if center/no side.
    """
    suffix = "_root"
    if not node.endswith(suffix):
        return None

    base = node[:-len(suffix)]

    if "_L" in base:
        return "L"
    elif "_R" in base:
        return "R"

    return None


def _get_shifter_roots_by_side(side="R"):
    """Get all shifter component roots for a specific side.

    Args:
        side (str): 'L' for left, 'R' for right. Default is 'R'.

    Returns:
        list[str]: List of shifter root node names on the specified side.
    """
    all_roots = _get_shifter_roots()
    side_roots = []

    for node in all_roots:
        node_side = _get_component_side(node)
        if node_side == side.upper():
            side_roots.append(node)

    return side_roots


def _get_shifter_roots_under_selection(selection, side="R"):
    """Get shifter component roots under selection for a specific side.

    Args:
        selection (list[str]): List of selected nodes.
        side (str): 'L' for left, 'R' for right. Default is 'R'.

    Returns:
        list[str]: List of shifter root node names under selection.
    """
    if not selection:
        return []

    side_roots = []
    side_upper = side.upper()

    for sel_node in selection:
        if not cmds.objExists(sel_node):
            continue

        # Check if selected node itself is a shifter root on the target side
        if cmds.attributeQuery("isGearGuide", node=sel_node, exists=True):
            if sel_node.endswith("_root"):
                node_side = _get_component_side(sel_node)
                if node_side == side_upper:
                    if sel_node not in side_roots:
                        side_roots.append(sel_node)

        # Get all descendants
        descendants = cmds.listRelatives(
            sel_node,
            allDescendents=True,
            type="transform",
            fullPath=False
        ) or []

        for desc in descendants:
            if not desc.endswith("_root"):
                continue

            if not cmds.attributeQuery("isGearGuide",
                                       node=desc,
                                       exists=True):
                continue

            node_side = _get_component_side(desc)
            if node_side == side_upper:
                if desc not in side_roots:
                    side_roots.append(desc)

    return side_roots


def delete_side_components(side="R"):
    """Delete all shifter components on a specific side.

    Args:
        side (str): 'L' for left, 'R' for right. Default is 'R'.

    Returns:
        list[str]: List of deleted component names.
    """
    roots_to_delete = _get_shifter_roots_by_side(side)
    deleted = []

    for node in roots_to_delete:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
                deleted.append(node)
            except Exception as exc:
                print("Failed to delete {0}: {1}".format(node, exc))

    return deleted


def delete_side_under_selection(side="R"):
    """Delete shifter components on a specific side under current selection.

    Supports multiple selections.

    Args:
        side (str): 'L' for left, 'R' for right. Default is 'R'.

    Returns:
        list[str]: List of deleted component names.
    """
    selection = cmds.ls(selection=True, long=False) or []

    if not selection:
        cmds.warning("No selection. Please select parent nodes.")
        return []

    roots_to_delete = _get_shifter_roots_under_selection(selection, side)
    deleted = []

    # Sort by path depth (deepest first) to avoid deleting parents first
    roots_to_delete_sorted = sorted(
        roots_to_delete,
        key=lambda x: len(cmds.ls(x, long=True)[0].split("|")) if cmds.objExists(x) else 0,
        reverse=True
    )

    for node in roots_to_delete_sorted:
        if cmds.objExists(node):
            try:
                cmds.delete(node)
                deleted.append(node)
            except Exception as exc:
                print("Failed to delete {0}: {1}".format(node, exc))

    return deleted


def get_shifter_mirror_report():
    """Get report of shifter components and their mirror status.

    Returns:
        dict: {
            "ok": list[str],
            "missing": list[tuple[str, str]]
        }
    """
    shifter_roots = _get_shifter_roots()
    ok = []
    missing = []

    for node in shifter_roots:
        mirror_name = _get_mirror_name(node)

        if mirror_name is None:
            continue

        mirror_exists = cmds.objExists(mirror_name)
        mirror_is_guide = False

        if mirror_exists:
            mirror_is_guide = cmds.attributeQuery(
                "isGearGuide",
                node=mirror_name,
                exists=True
            )

        if mirror_exists and mirror_is_guide:
            ok.append(node)
        else:
            missing.append((node, mirror_name))

    return {"ok": ok, "missing": missing}


class ShifterMirrorCheckerDialog(QtWidgets.QDialog):
    """UI tool to inspect missing mirror shifter components."""

    WINDOW_TITLE = "Shifter Mirror Checker"

    def __init__(self, parent=None):
        """Initialize dialog."""
        if parent is None:
            parent = pyqt.maya_main_window()

        super(ShifterMirrorCheckerDialog, self).__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName("mgear_shifter_mirror_checker")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._all_missing = []

        self._create_widgets()
        self._create_layout()
        self._create_connections()
        self.refresh_data()

    def _create_widgets(self):
        """Create widgets."""
        self.filter_label = QtWidgets.QLabel("Search (regex):")

        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("arm_.*_L0_root")

        self.list_widget = QtWidgets.QTreeWidget()
        self.list_widget.setColumnCount(2)
        self.list_widget.setHeaderLabels(
            ["Component", "Expected Mirror"]
        )
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.list_widget.setAlternatingRowColors(True)

        self.dup_sym_branch_btn = QtWidgets.QPushButton(
            "Duplicate Symmetry Branch"
        )
        self.dup_sym_multi_btn = QtWidgets.QPushButton(
            "Duplicate Symmetry Multi"
        )

        # Delete side widgets
        self.delete_side_label = QtWidgets.QLabel("Side:")
        self.delete_side_combo = QtWidgets.QComboBox()
        self.delete_side_combo.addItems(["Right (R)", "Left (L)"])
        self.delete_side_combo.setFixedWidth(100)

        self.delete_side_btn = QtWidgets.QPushButton("Delete Side (All)")
        self.delete_side_btn.setToolTip(
            "Delete all components on the selected side in the entire scene"
        )

        self.delete_side_sel_btn = QtWidgets.QPushButton(
            "Delete Side (Under Selection)"
        )
        self.delete_side_sel_btn.setToolTip(
            "Delete components on the selected side that are children of "
            "the current Maya selection. Supports multiple selections."
        )

        self.refresh_btn = QtWidgets.QPushButton("Refresh")

    def _create_layout(self):
        """Create layouts."""
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_edit)

        dup_layout = QtWidgets.QHBoxLayout()
        dup_layout.addWidget(self.dup_sym_branch_btn)
        dup_layout.addWidget(self.dup_sym_multi_btn)

        # Delete side layout
        delete_group = QtWidgets.QGroupBox("Delete Side Components")
        delete_layout = QtWidgets.QHBoxLayout(delete_group)
        delete_layout.addWidget(self.delete_side_label)
        delete_layout.addWidget(self.delete_side_combo)
        delete_layout.addWidget(self.delete_side_btn)
        delete_layout.addWidget(self.delete_side_sel_btn)
        delete_layout.addStretch()

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.list_widget)
        main_layout.addLayout(dup_layout)
        main_layout.addWidget(delete_group)
        main_layout.addWidget(self.refresh_btn)

    def _create_connections(self):
        """Connect signals and slots."""
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.filter_edit.textChanged.connect(self._apply_filter)
        self.list_widget.itemSelectionChanged.connect(
            self._on_selection_changed
        )
        self.dup_sym_branch_btn.clicked.connect(
            self._on_dup_sym_branch
        )
        self.dup_sym_multi_btn.clicked.connect(
            self._on_dup_sym_multi
        )
        self.delete_side_btn.clicked.connect(
            self._on_delete_side
        )
        self.delete_side_sel_btn.clicked.connect(
            self._on_delete_side_under_selection
        )

    def _get_selected_side(self):
        """Get the currently selected side from combo box.

        Returns:
            str: 'R' or 'L'
        """
        index = self.delete_side_combo.currentIndex()
        return "R" if index == 0 else "L"

    def refresh_data(self):
        """Refresh data from scene and repopulate list."""
        report = get_shifter_mirror_report()
        self._all_missing = report["missing"]
        self._populate_list(self._all_missing)

    def _populate_list(self, missing_list):
        """Populate the list widget.

        Args:
            missing_list (list[tuple[str, str]]): Missing mirror pairs.
        """
        self.list_widget.clear()

        for src, expected in missing_list:
            item = QtWidgets.QTreeWidgetItem()
            item.setText(0, src)
            item.setText(1, expected)
            self.list_widget.addTopLevelItem(item)

        self.list_widget.resizeColumnToContents(0)
        self.list_widget.resizeColumnToContents(1)

    def _apply_filter(self):
        """Filter list using regex."""
        pattern = self.filter_edit.text().strip()

        if not pattern:
            self._populate_list(self._all_missing)
            return

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            self.list_widget.clear()
            return

        filtered = []

        for src, expected in self._all_missing:
            if regex.search(src) or regex.search(expected):
                filtered.append((src, expected))

        self._populate_list(filtered)

    def _on_selection_changed(self):
        """Select corresponding objects in Maya."""
        items = self.list_widget.selectedItems()
        if not items:
            return

        nodes = []

        for item in items:
            node = item.text(0)
            if node and cmds.objExists(node):
                nodes.append(node)

        if nodes:
            try:
                cmds.select(nodes, r=True)
            except Exception as exc:
                print("Selection error: {0}".format(exc))

    def _on_dup_sym_branch(self):
        """Run mGear duplicate_multi without symmetry."""
        guide_manager.duplicate(sym=True)
        self.refresh_data()

    def _on_dup_sym_multi(self):
        """Run mGear duplicate_multi with symmetry."""
        guide_manager.duplicate_multi(sym=True)
        self.refresh_data()

    def _on_delete_side(self):
        """Delete all components on the selected side."""
        side = self._get_selected_side()
        side_name = "Right" if side == "R" else "Left"

        # Get count for confirmation
        roots = _get_shifter_roots_by_side(side)
        count = len(roots)

        if count == 0:
            QtWidgets.QMessageBox.information(
                self,
                "Delete Side",
                "No {0} side components found.".format(side_name)
            )
            return

        # Confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete {0} {1} side component(s)?\n\n"
            "This action cannot be undone.".format(count, side_name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        deleted = delete_side_components(side)
        self.refresh_data()

        QtWidgets.QMessageBox.information(
            self,
            "Delete Complete",
            "Deleted {0} component(s).".format(len(deleted))
        )

    def _on_delete_side_under_selection(self):
        """Delete side components under current Maya selection."""
        side = self._get_selected_side()
        side_name = "Right" if side == "R" else "Left"

        selection = cmds.ls(selection=True, long=False) or []

        if not selection:
            QtWidgets.QMessageBox.warning(
                self,
                "No Selection",
                "Please select parent node(s) in Maya first."
            )
            return

        # Get count for confirmation
        roots = _get_shifter_roots_under_selection(selection, side)
        count = len(roots)

        if count == 0:
            QtWidgets.QMessageBox.information(
                self,
                "Delete Side Under Selection",
                "No {0} side components found under selection.".format(
                    side_name
                )
            )
            return

        # Confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete {0} {1} side component(s) under selection?\n\n"
            "Selection: {2}\n\n"
            "This action cannot be undone.".format(
                count,
                side_name,
                ", ".join(selection[:5]) + ("..." if len(selection) > 5 else "")
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        deleted = delete_side_under_selection(side)
        self.refresh_data()

        QtWidgets.QMessageBox.information(
            self,
            "Delete Complete",
            "Deleted {0} component(s).".format(len(deleted))
        )


def open_shifter_mirror_checker():
    """Open (or raise) the Shifter Mirror Checker UI."""
    return pyqt.showDialog(ShifterMirrorCheckerDialog)


if __name__ == "__main__":
    open_shifter_mirror_checker()