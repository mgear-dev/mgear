"""Remap dialog for skin import.

Shown by ``skin.importSkin`` / ``skin.importSkinPack`` with
``on_missing="ui"``, once per skin file that has missing or ambiguous
geometry or influences.
"""

import os

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtWidgets

from maya import cmds

from mgear.core import node_remap
from mgear.core import pyqt
from mgear.core import skin

SKIP_LABEL = "Skip"
UNSET_LABEL = ""
SUGGESTION_COUNT = 8
SAME_COUNT_MARK = "\u2713"

SOURCE_SKIN = 0
SOURCE_ALL = 1
SOURCE_ROOT = 2

INF_COLUMNS = ("Exported", "Used by", "Position", "Target", "Method")
TARGET_COLUMN = 3
METHOD_COLUMN = 4

PATH_ROLE = QtCore.Qt.UserRole


def _display_name(path):
    """Return the shortest unique name of a node.

    Args:
        path (str): Full DAG path.

    Returns:
        str: Shortest unique name, or the path if the node is gone.
    """
    names = cmds.ls(path)
    return names[0] if names else path


class SkinRemapDialog(QtWidgets.QDialog, pyqt.SettingsMixin):
    """Resolve the missing geometry and influences of one skin file.

    Args:
        report (skin.SkinRemapReport): The file report.
        index (int, optional): File position in a pack, from 1.
        total (int, optional): Number of files in the pack.
        session (skin.SkinRemapSession, optional): Choices made so far in
            this import. Saved mappings include them, and loaded mappings
            are added to it for the next files.
        parent (QWidget, optional): Parent widget.
    """

    def __init__(self, report, index=None, total=None, session=None, parent=None):
        super(SkinRemapDialog, self).__init__(parent)
        pyqt.SettingsMixin.__init__(self)

        self.report = report
        self.session = session or skin.SkinRemapSession()
        self.status = skin.REMAP_CANCEL
        self.influence_names = sorted(report.influences)
        self.targets = {name: None for name in self.influence_names}
        self.methods = {name: "" for name in self.influence_names}
        self.geo_rows = {geo["name"]: geo for geo in report.geometry}
        self.geo_combos = {}
        self.target_combos = {}
        self.name_rows = {name: row for row, name in enumerate(self.influence_names)}
        self.pool = []
        self.pool_rows = {}
        self.pool_positions = None
        self.pool_model = QtGui.QStandardItemModel(self)
        self.updating = False

        label = os.path.basename(report.file_path or "skin data")
        if index and total:
            label = "{} ({}/{})".format(label, index, total)
        self.setWindowTitle("Skin Import Remap - {}".format(label))
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinMaxButtonsHint
        )
        self.resize(pyqt.dpi_scale(820), pyqt.dpi_scale(560))

        self.setup_ui()

        self.user_settings = {
            "skinRemap_regex": (self.regex_chk, False),
            "skinRemap_cutoff": (self.cutoff_spin, 0.8),
            "skinRemap_tolerance": (self.tolerance_spin, 0.01),
        }
        self.load_settings()

    # =========================================================
    # UI SETUP METHODS
    # =========================================================

    def setup_ui(self):
        """Build the dialog."""
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.set_initial_state()

    def create_widgets(self):
        """Create all widgets."""
        self.info_label = QtWidgets.QLabel()
        self.info_label.setWordWrap(True)
        self.tabs = QtWidgets.QTabWidget()

        # Geometry tab
        self.geo_table = QtWidgets.QTableWidget(0, 2)
        self.geo_table.setHorizontalHeaderLabels(("Exported object", "Target"))
        self.geo_table.horizontalHeader().setStretchLastSection(True)
        self.geo_table.verticalHeader().setVisible(False)

        # Joints tab
        self.source_combo = QtWidgets.QComboBox()
        self.source_combo.addItems(
            (
                "Target skinCluster influences",
                "All scene joints",
                "Joints under selected root",
            )
        )
        self.refresh_pool_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_pool_btn.setToolTip(
            "Reload the candidates, e.g. after changing the selected root"
        )

        self.inf_table = QtWidgets.QTableWidget(0, len(INF_COLUMNS))
        self.inf_table.setHorizontalHeaderLabels(INF_COLUMNS)
        self.inf_table.verticalHeader().setVisible(False)
        self.inf_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        header = self.inf_table.horizontalHeader()
        header.setSectionResizeMode(TARGET_COLUMN, QtWidgets.QHeaderView.Stretch)

        self.search_line = QtWidgets.QLineEdit()
        self.search_line.setPlaceholderText("Search")
        self.replace_line = QtWidgets.QLineEdit()
        self.replace_line.setPlaceholderText("Replace")
        self.regex_chk = QtWidgets.QCheckBox("Regex")
        self.replace_btn = QtWidgets.QPushButton("Search/Replace")

        self.strip_line = QtWidgets.QLineEdit()
        self.strip_line.setPlaceholderText("Strip prefix")
        self.add_line = QtWidgets.QLineEdit()
        self.add_line.setPlaceholderText("Add prefix")
        self.prefix_btn = QtWidgets.QPushButton("Prefix")

        self.side_btn = QtWidgets.QPushButton("L <-> R")
        self.side_btn.setToolTip("Swap L and R side tokens")
        self.cutoff_label = QtWidgets.QLabel("Similarity")
        self.cutoff_spin = QtWidgets.QDoubleSpinBox()
        self.cutoff_spin.setRange(0.1, 1.0)
        self.cutoff_spin.setSingleStep(0.05)
        cutoff_tip = (
            "Minimum name similarity for Similar name, 0 to 1. "
            "1.0 is an identical name; lower values accept looser matches."
        )
        self.cutoff_label.setToolTip(cutoff_tip)
        self.cutoff_spin.setToolTip(cutoff_tip)
        self.similar_btn = QtWidgets.QPushButton("Similar name")
        self.tolerance_label = QtWidgets.QLabel("Tolerance")
        self.tolerance_spin = QtWidgets.QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0001, 1000.0)
        self.tolerance_spin.setDecimals(4)
        tolerance_tip = "Maximum distance for Closest position, in world units"
        self.tolerance_label.setToolTip(tolerance_tip)
        self.tolerance_spin.setToolTip(tolerance_tip)
        self.position_btn = QtWidgets.QPushButton("Closest position")
        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.setToolTip("Clear the target of the selected rows")

        # Buttons
        self.save_btn = QtWidgets.QPushButton("Save mapping...")
        self.save_btn.setToolTip(
            "Save every choice made so far in this import. The file is then "
            "updated after each remap dialog of the import."
        )
        self.save_label = QtWidgets.QLabel()
        self.load_btn = QtWidgets.QPushButton("Load mapping...")
        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.apply_btn.setToolTip("Enabled when every influence has a target")
        self.skip_unresolved_btn = QtWidgets.QPushButton("Skip unresolved")
        self.skip_unresolved_btn.setToolTip(
            "Apply the resolved items and skip the others"
        )
        self.skip_file_btn = QtWidgets.QPushButton("Skip this file")
        self.cancel_btn = QtWidgets.QPushButton("Cancel import")
        self.cancel_btn.setToolTip(
            "Stop the import. In a skin pack, the remaining files are not imported"
        )

    def create_layout(self):
        """Arrange the widgets."""
        geo_widget = QtWidgets.QWidget()
        geo_layout = QtWidgets.QVBoxLayout(geo_widget)
        geo_layout.addWidget(self.geo_table)

        source_layout = QtWidgets.QHBoxLayout()
        source_layout.addWidget(QtWidgets.QLabel("Candidates:"))
        source_layout.addWidget(self.source_combo, 1)
        source_layout.addWidget(self.refresh_pool_btn)

        replace_layout = QtWidgets.QHBoxLayout()
        replace_layout.addWidget(self.search_line)
        replace_layout.addWidget(self.replace_line)
        replace_layout.addWidget(self.regex_chk)
        replace_layout.addWidget(self.replace_btn)

        prefix_layout = QtWidgets.QHBoxLayout()
        prefix_layout.addWidget(self.strip_line)
        prefix_layout.addWidget(self.add_line)
        prefix_layout.addWidget(self.prefix_btn)

        match_layout = QtWidgets.QHBoxLayout()
        match_layout.addWidget(self.side_btn)
        match_layout.addWidget(self.cutoff_label)
        match_layout.addWidget(self.cutoff_spin)
        match_layout.addWidget(self.similar_btn)
        match_layout.addWidget(self.tolerance_label)
        match_layout.addWidget(self.tolerance_spin)
        match_layout.addWidget(self.position_btn)
        match_layout.addStretch()
        match_layout.addWidget(self.clear_btn)

        tools_box = QtWidgets.QGroupBox(
            "Match tools (selected rows, or all rows if none selected)"
        )
        tools_box.setToolTip(
            "Rows with a match get the proposed target, the other rows "
            "keep their current one."
        )
        tools_layout = QtWidgets.QVBoxLayout(tools_box)
        tools_layout.addLayout(replace_layout)
        tools_layout.addLayout(prefix_layout)
        tools_layout.addLayout(match_layout)

        inf_widget = QtWidgets.QWidget()
        inf_layout = QtWidgets.QVBoxLayout(inf_widget)
        inf_layout.addLayout(source_layout)
        inf_layout.addWidget(self.inf_table)
        inf_layout.addWidget(tools_box)

        self.tabs.addTab(geo_widget, "Geometry ({})".format(len(self.report.geometry)))
        self.tabs.addTab(inf_widget, "Joints ({})".format(len(self.influence_names)))

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.save_label)
        btn_layout.addStretch()
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.skip_unresolved_btn)
        btn_layout.addWidget(self.skip_file_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.info_label)
        main_layout.addWidget(self.tabs)
        main_layout.addLayout(btn_layout)

    def create_connections(self):
        """Connect signals."""
        self.source_combo.currentIndexChanged.connect(self.refresh_pool)
        self.refresh_pool_btn.clicked.connect(self.refresh_pool)
        self.replace_btn.clicked.connect(self.match_replace)
        self.prefix_btn.clicked.connect(self.match_prefix)
        self.side_btn.clicked.connect(self.match_side)
        self.similar_btn.clicked.connect(self.match_similar)
        self.position_btn.clicked.connect(self.match_position)
        self.clear_btn.clicked.connect(self.clear_selected)
        self.save_btn.clicked.connect(self.save_mapping)
        self.load_btn.clicked.connect(self.load_mapping)
        self.apply_btn.clicked.connect(self.accept_apply)
        self.skip_unresolved_btn.clicked.connect(self.accept_apply)
        self.skip_file_btn.clicked.connect(self.accept_skip_file)
        self.cancel_btn.clicked.connect(self.reject)

    def set_initial_state(self):
        """Fill the tables from the report."""
        self.info_label.setText(
            "{} object(s) and {} influence(s) could not be resolved "
            "automatically in <b>{}</b>.".format(
                len(self.report.geometry),
                len(self.influence_names),
                self.report.file_path or "skin data",
            )
        )
        if not self.report.influence_pool:
            self.source_combo.setCurrentIndex(SOURCE_ALL)
        self.populate_geometry()
        self.populate_influences()
        self.refresh_pool()

        has_positions = any(
            info["position"] for info in self.report.influences.values()
        )
        if not has_positions:
            tip = (
                "Unavailable: this skin file has no influence positions. "
                "Re-export it with this mGear version to enable it."
            )
            for widget in (
                self.tolerance_label,
                self.tolerance_spin,
                self.position_btn,
            ):
                widget.setEnabled(False)
                widget.setToolTip(tip)

        self.update_save_label()
        if not self.report.geometry:
            self.tabs.setCurrentIndex(1)
        self.update_buttons()

    # =========================================================
    # TABLES
    # =========================================================

    def populate_geometry(self):
        """Create one row per missing or ambiguous object."""
        self.geo_table.setRowCount(len(self.report.geometry))
        for row, geo in enumerate(self.report.geometry):
            item = QtWidgets.QTableWidgetItem(geo["name"])
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            item.setToolTip(geo.get("long_name") or geo["name"])
            self.geo_table.setItem(row, 0, item)

            combo = QtWidgets.QComboBox()
            combo.addItem(SKIP_LABEL, None)
            paths = geo["candidates"] or self.suggest_geometry(geo)
            for path in paths:
                self._add_geo_item(combo, geo, path)
            combo.setToolTip(
                "Same-name objects, or similar names when there are none. "
                "Objects marked with {} have the exported point "
                "count.".format(SAME_COUNT_MARK)
            )
            browse_btn = QtWidgets.QPushButton("...")
            browse_btn.setToolTip("Pick any mesh, NURBS surface or curve")
            browse_btn.clicked.connect(lambda _=False, g=geo: self.browse_geometry(g))
            cell = QtWidgets.QWidget()
            cell_layout = QtWidgets.QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.addWidget(combo, 1)
            cell_layout.addWidget(browse_btn)
            self.geo_table.setCellWidget(row, 1, cell)
            self.geo_combos[geo["name"]] = combo
        self.geo_table.resizeColumnToContents(0)

    def suggest_geometry(self, geo):
        """Return scene objects with a name similar to a missing object.

        Objects with the exported point count come first.

        Args:
            geo (dict): Geometry entry of the report.

        Returns:
            list: Full paths.
        """
        scene = self.session.get_scene_geometry()
        similar = node_remap.similar_names(
            geo["name"], list(scene), count=SUGGESTION_COUNT, cutoff=0.5
        )
        count = geo.get("point_count")
        return sorted(similar, key=lambda path: scene.get(path) != count)

    def _add_geo_item(self, combo, geo, path, index=None):
        """Add a target object to a geometry combo.

        Args:
            combo (QComboBox): The row combo.
            geo (dict): Geometry entry of the report.
            path (str): Object full path.
            index (int, optional): Insert position, default is the end.

        Returns:
            int: The item index.
        """
        points = self.session.get_scene_geometry().get(path)
        label = _display_name(path)
        if points is not None:
            label = "{}  ({} pts)".format(label, points)
            if points == geo.get("point_count"):
                label = "{} {}".format(label, SAME_COUNT_MARK)
        if index is None:
            index = combo.count()
        combo.insertItem(index, label, path)
        combo.setItemData(index, path, QtCore.Qt.ToolTipRole)
        return index

    def select_geometry(self, name, path):
        """Select a target object in a geometry row, adding it if needed.

        Args:
            name (str): Exported object name.
            path (str): Target object full path.
        """
        combo = self.geo_combos[name]
        index = combo.findData(path)
        if index < 0:
            index = self._add_geo_item(combo, self.geo_rows[name], path, index=1)
        combo.setCurrentIndex(index)

    def browse_geometry(self, geo):
        """Pick the target of a geometry row from all scene geometry.

        Args:
            geo (dict): Geometry entry of the report.
        """
        picker = GeometryPickerDialog(
            self.session.get_scene_geometry(),
            geo["name"],
            geo.get("point_count"),
            self,
        )
        path = picker.selected_path() if picker.exec_() else None
        picker.deleteLater()
        if path:
            self.select_geometry(geo["name"], path)

    def populate_influences(self):
        """Create one row per missing influence, with a target combo."""
        self.inf_table.setRowCount(len(self.influence_names))
        for row, name in enumerate(self.influence_names):
            info = self.report.influences[name]
            users = info["users"]
            values = (
                name,
                str(len(users)),
                "yes" if info["position"] else "no",
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.inf_table.setItem(row, column, item)
            self.inf_table.item(row, 1).setToolTip("\n".join(users))
            method = QtWidgets.QTableWidgetItem("")
            method.setFlags(method.flags() & ~QtCore.Qt.ItemIsEditable)
            self.inf_table.setItem(row, METHOD_COLUMN, method)

            combo = QtWidgets.QComboBox()
            combo.setModel(self.pool_model)
            combo.setEditable(True)
            combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
            combo.completer().setFilterMode(QtCore.Qt.MatchContains)
            combo.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            combo.currentIndexChanged.connect(
                lambda _, n=name: self.on_target_changed(n)
            )
            combo.lineEdit().editingFinished.connect(
                lambda n=name: self.on_target_edited(n)
            )
            self.inf_table.setCellWidget(row, TARGET_COLUMN, combo)
            self.target_combos[name] = combo
        self.inf_table.resizeColumnsToContents()

    def get_pool(self):
        """Return the candidate influences for the current source option.

        Returns:
            list: Full paths.
        """
        source = self.source_combo.currentIndex()
        if source == SOURCE_SKIN and self.report.influence_pool:
            return list(self.report.influence_pool)
        if source == SOURCE_ROOT:
            roots = cmds.ls(selection=True, long=True, type="transform")
            pool = []
            for root in roots:
                if cmds.nodeType(root) == "joint":
                    pool.append(root)
                pool.extend(
                    cmds.listRelatives(
                        root, allDescendents=True, type="joint", fullPath=True
                    )
                    or []
                )
            if not pool:
                cmds.warning("Select the root of the target joints")
            return list(dict.fromkeys(pool))
        return cmds.ls(type="joint", long=True)

    def refresh_pool(self, *args):
        """Reload the candidate list shared by all target combos."""
        pool = self.get_pool() + [p for p in self.targets.values() if p]
        self.pool = list(dict.fromkeys(pool))
        # Model row 0 is the empty choice.
        self.pool_rows = {path: row + 1 for row, path in enumerate(self.pool)}
        self.pool_positions = None
        items = [QtGui.QStandardItem(UNSET_LABEL)]
        items.extend(self._pool_item(path) for path in self.pool)
        self.updating = True
        try:
            self.pool_model.clear()
            # One insert: every combo and completer shares this model.
            self.pool_model.invisibleRootItem().appendRows(items)
            for name in self.influence_names:
                self._show_target(name)
        finally:
            self.updating = False

    def _pool_item(self, path):
        item = QtGui.QStandardItem(_display_name(path))
        item.setData(path, PATH_ROLE)
        item.setToolTip(path)
        return item

    def _pool_index(self, path):
        """Return the model row of a path, adding it if needed."""
        if not path:
            return 0
        if path not in self.pool_rows:
            self.pool.append(path)
            self.pool_rows[path] = len(self.pool)
            self.pool_positions = None
            self.pool_model.appendRow(self._pool_item(path))
        return self.pool_rows[path]

    def _show_target(self, name):
        combo = self.target_combos[name]
        index = self._pool_index(self.targets[name])
        combo.setCurrentIndex(index)
        # Typed text is not replaced when the index doesn't change.
        combo.setEditText(combo.itemText(index))

    def set_target(self, name, path, method, update=True):
        """Set the target of an influence row.

        Args:
            name (str): Exported influence name.
            path (str): Target full path, or None to clear.
            method (str): How the target was chosen.
            update (bool, optional): Update the dialog buttons. Batch
                callers pass False and update once at the end.
        """
        self.targets[name] = path
        self.methods[name] = method if path else ""
        self.updating = True
        try:
            self._show_target(name)
        finally:
            self.updating = False
        row = self.name_rows[name]
        self.inf_table.item(row, METHOD_COLUMN).setText(self.methods[name])
        if update:
            self.update_buttons()

    def on_target_changed(self, name):
        """Record a target picked by the user."""
        if self.updating:
            return
        path = self.target_combos[name].currentData(PATH_ROLE)
        self.set_target(name, path or None, "manual")

    def on_target_edited(self, name):
        """Match typed text to a candidate, or restore the current target.

        Args:
            name (str): Exported influence name.
        """
        combo = self.target_combos[name]
        text = combo.currentText().strip()
        index = combo.findText(text, QtCore.Qt.MatchFixedString)
        if text and index > 0:
            combo.setCurrentIndex(index)
        else:
            self._show_target(name)

    def update_buttons(self):
        """Enable Apply only when every influence has a target."""
        resolved = all(self.targets.values())
        self.apply_btn.setEnabled(resolved)

    # =========================================================
    # MATCH TOOLS
    # =========================================================

    def selected_names(self):
        """Return the influence names of the selected rows.

        Returns:
            list: Names in row order.
        """
        rows = sorted({index.row() for index in self.inf_table.selectedIndexes()})
        return [self.influence_names[row] for row in rows]

    def run_match(self, method, match):
        """Run a match tool and set the proposed targets.

        Runs on the selected rows, or every row if none selected. Rows
        without a match keep their current target.

        Args:
            method (str): Method label for the rows.
            match (callable): Takes the influence names, returns
                ``{influence: target path}``.
        """
        names = self.selected_names() or list(self.influence_names)
        matches = match(names)
        for name, path in matches.items():
            self.set_target(name, path, method, update=False)
        self.update_buttons()
        cmds.inViewMessage(
            assistMessage="{}: matched {} of {} influence(s)".format(
                method, len(matches), len(names)
            ),
            position="topCenter",
            fade=True,
        )

    def match_replace(self):
        search = self.search_line.text()
        if not search:
            return
        try:
            self.run_match(
                "replace",
                lambda names: node_remap.match_by_pattern(
                    names,
                    self.pool,
                    search,
                    self.replace_line.text(),
                    regex=self.regex_chk.isChecked(),
                ),
            )
        except Exception as e:
            cmds.warning("Invalid search pattern: {}".format(e))

    def match_prefix(self):
        self.run_match(
            "prefix",
            lambda names: node_remap.match_by_prefix(
                names,
                self.pool,
                strip=self.strip_line.text(),
                add=self.add_line.text(),
            ),
        )

    def match_side(self):
        self.run_match(
            "side swap", lambda names: node_remap.match_by_side_swap(names, self.pool)
        )

    def match_similar(self):
        self.run_match(
            "similar",
            lambda names: node_remap.match_by_similarity(
                names, self.pool, cutoff=self.cutoff_spin.value()
            ),
        )

    def match_position(self):
        if self.pool_positions is None:
            self.pool_positions = skin.get_bind_world_positions(self.pool)
        self.run_match(
            "position",
            lambda names: node_remap.match_by_position(
                {n: self.report.influences[n]["position"] for n in names},
                self.pool_positions,
                tolerance=self.tolerance_spin.value(),
            ),
        )

    def clear_selected(self):
        for name in self.selected_names():
            self.set_target(name, None, "", update=False)
        self.update_buttons()

    # =========================================================
    # MAPPING
    # =========================================================

    def get_mapping(self):
        """Return the current choices as a skin remap mapping.

        Returns:
            dict: ``{"geometry": {...}, "influences": {...}}``
        """
        geometry = {}
        for name, combo in self.geo_combos.items():
            path = combo.currentData()
            if path:
                geometry[name] = path
        influences = {name: path for name, path in self.targets.items() if path}
        return {"geometry": geometry, "influences": influences}

    def save_mapping(self):
        path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Skin Remap",
            "",
            "Skin Remap (*{})".format(skin.MAP_EXT),
        )[0]
        if not path:
            return
        if not path.endswith(skin.MAP_EXT):
            path += skin.MAP_EXT
        self.session.save_path = path
        self.session.save(self.get_mapping())
        self.update_save_label()

    def update_save_label(self):
        """Show the mapping file updated by this import, if any."""
        path = self.session.save_path
        if path:
            self.save_label.setText("Updating {}".format(os.path.basename(path)))
            self.save_label.setToolTip(path)
        else:
            self.save_label.clear()

    def load_mapping(self):
        path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Skin Remap",
            "",
            "Skin Remap (*{})".format(skin.MAP_EXT),
        )[0]
        if not path:
            return
        mapping = skin.load_skin_mapping(path)
        # The next files of the import use it too.
        self.session.add(mapping)
        for name, target in mapping["geometry"].items():
            if name in self.geo_combos:
                self.select_geometry(name, target)
        for name, target in mapping["influences"].items():
            if name in self.targets and cmds.objExists(target):
                full = cmds.ls(target, long=True)[0]
                self.set_target(name, full, "file")

    # =========================================================
    # RESULT
    # =========================================================

    def accept_apply(self):
        self.status = skin.REMAP_APPLY
        self.accept()

    def accept_skip_file(self):
        self.status = skin.REMAP_SKIP_FILE
        self.accept()


class GeometryPickerDialog(QtWidgets.QDialog):
    """Pick a scene object as the target of a missing skin object.

    Args:
        geometry (dict): ``{transform full path: point count}``
        name (str): Exported object name, shown in the title.
        point_count (int, optional): Exported point count.
        parent (QWidget, optional): Parent widget.
    """

    def __init__(self, geometry, name, point_count=None, parent=None):
        super(GeometryPickerDialog, self).__init__(parent)
        self.geometry = geometry
        self.point_count = point_count
        self.items = []

        self.setWindowTitle("Pick Target for {}".format(name))
        self.resize(pyqt.dpi_scale(520), pyqt.dpi_scale(480))

        self.setup_ui()

    def setup_ui(self):
        """Build the dialog."""
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.populate()
        self.refresh()

    def create_widgets(self):
        """Create all widgets."""
        self.filter_line = QtWidgets.QLineEdit()
        self.filter_line.setPlaceholderText("Filter by name")
        self.filter_line.setClearButtonEnabled(True)
        self.same_count_chk = QtWidgets.QCheckBox(
            "Same point count only ({})".format(self.point_count)
        )
        self.same_count_chk.setEnabled(self.point_count is not None)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(("Object", "Points"))
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

    def create_layout(self):
        """Arrange the widgets."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.filter_line)
        layout.addWidget(self.same_count_chk)
        layout.addWidget(self.tree)
        layout.addWidget(self.button_box)

    def create_connections(self):
        """Connect signals."""
        self.filter_line.textChanged.connect(self.refresh)
        self.same_count_chk.toggled.connect(self.refresh)
        self.tree.itemDoubleClicked.connect(self.accept)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def populate(self):
        """Create one row per scene object."""
        for path, points in self.geometry.items():
            item = QtWidgets.QTreeWidgetItem((_display_name(path), ""))
            item.setData(0, PATH_ROLE, path)
            item.setToolTip(0, path)
            item.setData(1, QtCore.Qt.DisplayRole, points)
            self.items.append((item, path.lower(), points))
        self.tree.addTopLevelItems([item for item, _, _ in self.items])
        self.tree.resizeColumnToContents(0)

    def refresh(self, *args):
        """Show only the objects matching the filters."""
        text = self.filter_line.text().lower()
        same_count = self.same_count_chk.isChecked()
        for item, path, points in self.items:
            hidden = bool(text) and text not in path
            hidden = hidden or (same_count and points != self.point_count)
            item.setHidden(hidden)

    def visible_count(self):
        """Return the number of objects shown.

        Returns:
            int: Visible rows.
        """
        return sum(not item.isHidden() for item, _, _ in self.items)

    def selected_path(self):
        """Return the picked object.

        Returns:
            str: Full path, or None.
        """
        item = self.tree.currentItem()
        return item.data(0, PATH_ROLE) if item else None


def run_remap_dialog(report, index=None, total=None, session=None):
    """Show the remap dialog modally for one skin file report.

    Args:
        report (skin.SkinRemapReport): The file report.
        index (int, optional): File position in a pack, from 1.
        total (int, optional): Number of files in the pack.
        session (skin.SkinRemapSession, optional): Choices made so far in
            this import.

    Returns:
        tuple: (status, mapping). status is ``skin.REMAP_APPLY``,
            ``skin.REMAP_SKIP_FILE`` or ``skin.REMAP_CANCEL``; mapping is
            None unless the status is apply.
    """
    dialog = SkinRemapDialog(
        report, index, total, session=session, parent=pyqt.maya_main_window()
    )
    try:
        dialog.exec_()
        if dialog.status == skin.REMAP_APPLY:
            return dialog.status, dialog.get_mapping()
        return dialog.status, None
    finally:
        dialog.deleteLater()
