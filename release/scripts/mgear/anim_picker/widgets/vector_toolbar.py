"""Floating toolbar and layer panel for the anim picker SVG editor.

``VectorToolbar`` is a tool window shown beside the picker while a
``vector_editor.VectorEditor`` session is active. It only talks to the editor
through its public methods and signals: tools, tool options, node and path
operations, precision fields, snapping and view toggles, the layer panel, and
the session controls (undo / redo, Cancel, Done). Closing the window ends the
session as Done.
"""

from mgear.core import pyqt
from mgear.core import vector_path
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import vector_editor
from mgear.anim_picker.widgets import vector_model
from mgear.anim_picker.widgets.tool_bar import mgear_icon

# (tool id, icon, tooltip) for the tool buttons, in display order.
_TOOLS = (
    (vector_editor.TOOL_SELECT, "mgear_mouse-pointer", "Select (V)"),
    (vector_editor.TOOL_NODE, "mgear_navigation", "Node (A)"),
    (vector_editor.TOOL_PEN, "mgear_pen-tool", "Pen (P)"),
    (vector_editor.TOOL_RECT, "mgear_square", "Rectangle (R)"),
    (vector_editor.TOOL_ELLIPSE, "mgear_circle", "Ellipse (E)"),
    (vector_editor.TOOL_POLYGON, "mgear_star", "Polygon / Star (Y)"),
    (vector_editor.TOOL_LINE, "mgear_minus", "Line (L)"),
)

_MODES = (vector_model.MODE_FILL, vector_model.MODE_STROKE)

# Layer table columns.
_COL_VISIBLE = 0
_COL_LOCK = 1
_COL_NAME = 2
_COL_MODE = 3
_COL_WIDTH = 4
_COL_COLOR = 5


def _tool_button(icon=None, text=None, tooltip=None, checkable=False):
    """Return a small QToolButton."""
    button = QtWidgets.QToolButton()
    size = int(pyqt.dpi_scale(18))
    button.setIconSize(QtCore.QSize(size, size))
    if icon:
        button.setIcon(mgear_icon(icon))
    if text:
        button.setText(text)
        if icon:
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    if tooltip:
        button.setToolTip(tooltip)
    button.setCheckable(checkable)
    button.setAutoRaise(True)
    return button


def _row(*widgets):
    """Return a horizontal layout holding ``widgets`` (None adds a stretch)."""
    layout = QtWidgets.QHBoxLayout()
    layout.setSpacing(2)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        if widget is None:
            layout.addStretch()
        elif isinstance(widget, QtWidgets.QLayout):
            layout.addLayout(widget)
        else:
            layout.addWidget(widget)
    return layout


def _section(title, layout):
    """Return a titled group box wrapping ``layout``."""
    box = QtWidgets.QGroupBox(title)
    box.setLayout(layout)
    layout.setContentsMargins(4, 2, 4, 4)
    return box


class VectorToolbar(QtWidgets.QWidget):
    """Tool window driving a ``VectorEditor`` session.

    Args:
        editor (VectorEditor): The editor to drive.
        parent (QWidget, optional): The picker window it floats over.
    """

    def __init__(self, editor, parent=None):
        super(VectorToolbar, self).__init__(parent, QtCore.Qt.Tool)
        self.editor = editor
        self._placed = False
        self._syncing = False
        self.setWindowTitle("SVG Edit")
        # Refresh after the current event: a layer-row widget's own signal
        # can trigger a refresh that rebuilds (deletes) that widget.
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(0)
        self._refresh_timer.timeout.connect(self.refresh)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

        editor.session_started.connect(self._on_session_started)
        editor.session_ended.connect(self.hide)
        editor.changed.connect(self._refresh_timer.start)
        editor.tool_changed.connect(self._on_tool_changed)

    # =================================================================
    # UI
    # =================================================================

    def create_widgets(self):
        """Create all widgets."""
        self.tool_group = QtWidgets.QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_buttons = {}
        for tool, icon, tooltip in _TOOLS:
            button = _tool_button(icon, tooltip=tooltip, checkable=True)
            self.tool_group.addButton(button)
            self.tool_buttons[tool] = button

        self.radius_sb = QtWidgets.QDoubleSpinBox()
        self.radius_sb.setRange(0.0, 10000.0)
        self.radius_sb.setToolTip("Rectangle corner radius")
        self.sides_sb = QtWidgets.QSpinBox()
        self.sides_sb.setRange(3, 64)
        self.sides_sb.setValue(self.editor.polygon_sides)
        self.sides_sb.setToolTip("Polygon / star sides")
        self.inner_sb = QtWidgets.QSpinBox()
        self.inner_sb.setRange(0, 95)
        self.inner_sb.setSuffix(" %")
        self.inner_sb.setToolTip("Star inner radius (0 draws a plain polygon)")
        self.arrow_start_cb = QtWidgets.QCheckBox("Start arrow")
        self.arrow_end_cb = QtWidgets.QCheckBox("End arrow")
        self.arrow_size_sb = QtWidgets.QDoubleSpinBox()
        self.arrow_size_sb.setRange(0.1, 1000.0)
        self.arrow_size_sb.setValue(self.editor.arrow_size)
        self.arrow_size_sb.setToolTip("Arrowhead length")

        # One options page per tool family; tools without options show a note.
        self.options_stack = QtWidgets.QStackedWidget()
        none_page = self._options_page(
            QtWidgets.QLabel("No options for this tool"), None
        )
        rect_page = self._options_page(
            QtWidgets.QLabel("Corner radius"), self.radius_sb, None
        )
        polygon_page = self._options_page(
            QtWidgets.QLabel("Sides"),
            self.sides_sb,
            QtWidgets.QLabel("Star"),
            self.inner_sb,
            None,
        )
        arrow_page = self._options_page(
            self.arrow_start_cb,
            self.arrow_end_cb,
            QtWidgets.QLabel("Size"),
            self.arrow_size_sb,
            None,
        )
        self._option_pages = {
            vector_editor.TOOL_RECT: rect_page,
            vector_editor.TOOL_POLYGON: polygon_page,
            vector_editor.TOOL_LINE: arrow_page,
            vector_editor.TOOL_PEN: arrow_page,
        }
        self._no_options_page = none_page

        self.add_node_btn = _tool_button(
            "mgear_plus-circle", tooltip="Add node (Alt-click a segment)"
        )
        self.delete_node_btn = _tool_button(
            "mgear_minus-circle", tooltip="Delete node (Delete)"
        )
        self.corner_btn = _tool_button(
            text="Corner", tooltip="Corner: remove the node's handles"
        )
        self.smooth_btn = _tool_button(
            text="Smooth", tooltip="Smooth: collinear handles"
        )
        self.symmetric_btn = _tool_button(
            text="Sym", tooltip="Symmetric: collinear, equal handles"
        )
        self.break_btn = _tool_button("mgear_scissors", tooltip="Break path at node")
        self.join_btn = _tool_button("mgear_link", tooltip="Join two endpoints")
        self.close_btn = _tool_button(
            text="Close/Open", tooltip="Close or open the path"
        )
        self.reverse_btn = _tool_button(
            "mgear_repeat", tooltip="Reverse path direction"
        )

        self.union_btn = _tool_button(text="Union", tooltip="Merge the selected shapes")
        self.subtract_btn = _tool_button(
            text="Subtract", tooltip="Cut the topmost selected shape from the others"
        )
        self.intersect_btn = _tool_button(
            text="Intersect", tooltip="Keep only the overlap"
        )
        self.exclude_btn = _tool_button(
            text="Exclude", tooltip="Keep everything but the overlap"
        )
        self.flip_h_btn = _tool_button(text="Flip H", tooltip="Flip horizontally")
        self.flip_v_btn = _tool_button(text="Flip V", tooltip="Flip vertically")
        self.duplicate_btn = _tool_button("mgear_copy", tooltip="Duplicate")
        self.delete_btn = _tool_button("mgear_trash-2", tooltip="Delete")

        self.x_sb = QtWidgets.QDoubleSpinBox()
        self.y_sb = QtWidgets.QDoubleSpinBox()
        for box in (self.x_sb, self.y_sb):
            box.setRange(-100000.0, 100000.0)
            box.setDecimals(2)
            box.setKeyboardTracking(False)
        self.snap_grid_cb = QtWidgets.QCheckBox("Snap grid")
        self.grid_size_sb = QtWidgets.QDoubleSpinBox()
        self.grid_size_sb.setRange(0.1, 1000.0)
        self.grid_size_sb.setValue(self.editor.grid_size)
        self.snap_nodes_cb = QtWidgets.QCheckBox("Snap nodes")
        self.outline_cb = QtWidgets.QCheckBox("Outline")
        self.grid_cb = QtWidgets.QCheckBox("Grid")

        self.layer_table = QtWidgets.QTableWidget(0, 6)
        self.layer_table.setHorizontalHeaderLabels(
            ["", "", "Layer", "Mode", "Width", "Color"]
        )
        self.layer_table.verticalHeader().setVisible(False)
        self.layer_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.layer_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        header = self.layer_table.horizontalHeader()
        header.setSectionResizeMode(_COL_NAME, QtWidgets.QHeaderView.Stretch)
        for column in (_COL_VISIBLE, _COL_LOCK, _COL_MODE, _COL_WIDTH, _COL_COLOR):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        self.layer_table.setMinimumHeight(int(pyqt.dpi_scale(110)))

        self.add_layer_btn = _tool_button("mgear_plus", tooltip="Add layer")
        self.duplicate_layer_btn = _tool_button("mgear_copy", tooltip="Duplicate layer")
        self.delete_layer_btn = _tool_button("mgear_trash-2", tooltip="Delete layer")
        self.layer_up_btn = _tool_button(
            "mgear_chevron-up", tooltip="Move layer forward"
        )
        self.layer_down_btn = _tool_button(
            "mgear_chevron-down", tooltip="Move layer back"
        )
        self.merge_btn = _tool_button(
            "mgear_git-merge", tooltip="Merge into the layer below"
        )
        self.move_sel_btn = _tool_button(
            "mgear_log-in", tooltip="Move the selection to this layer"
        )

        self.undo_btn = _tool_button("mgear_rotate-ccw", tooltip="Undo (Ctrl+Z)")
        self.redo_btn = _tool_button("mgear_rotate-cw", tooltip="Redo (Ctrl+Shift+Z)")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.done_btn = QtWidgets.QPushButton("Done")
        self.done_btn.setDefault(True)

    def create_layout(self):
        """Arrange the widgets."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        tools = [self.tool_buttons[tool] for tool, _icon, _tip in _TOOLS]
        layout.addWidget(_section("Tools", _row(*(tools + [None]))))
        options = QtWidgets.QVBoxLayout()
        options.addWidget(self.options_stack)
        layout.addWidget(_section("Tool options", options))
        layout.addWidget(
            _section(
                "Nodes",
                _row(
                    self.add_node_btn,
                    self.delete_node_btn,
                    self.corner_btn,
                    self.smooth_btn,
                    self.symmetric_btn,
                    self.break_btn,
                    self.join_btn,
                    self.close_btn,
                    self.reverse_btn,
                    None,
                ),
            )
        )
        layout.addWidget(
            _section(
                "Paths",
                _row(
                    self.union_btn,
                    self.subtract_btn,
                    self.intersect_btn,
                    self.exclude_btn,
                    self.flip_h_btn,
                    self.flip_v_btn,
                    self.duplicate_btn,
                    self.delete_btn,
                    None,
                ),
            )
        )
        precision = QtWidgets.QVBoxLayout()
        precision.addLayout(
            _row(
                QtWidgets.QLabel("X"), self.x_sb, QtWidgets.QLabel("Y"), self.y_sb, None
            )
        )
        precision.addLayout(
            _row(
                self.snap_grid_cb,
                self.grid_size_sb,
                self.snap_nodes_cb,
                self.outline_cb,
                self.grid_cb,
                None,
            )
        )
        layout.addWidget(_section("Precision and view", precision))

        layers = QtWidgets.QVBoxLayout()
        layers.addWidget(self.layer_table)
        layers.addLayout(
            _row(
                self.add_layer_btn,
                self.duplicate_layer_btn,
                self.delete_layer_btn,
                self.layer_up_btn,
                self.layer_down_btn,
                self.merge_btn,
                self.move_sel_btn,
                None,
            )
        )
        layout.addWidget(_section("Layers", layers))

        layout.addLayout(
            _row(self.undo_btn, self.redo_btn, None, self.cancel_btn, self.done_btn)
        )

    def create_connections(self):
        """Connect signals to the editor."""
        editor = self.editor
        for tool, button in self.tool_buttons.items():
            button.clicked.connect(lambda *args, t=tool: self._act(editor.set_tool, t))

        self.radius_sb.valueChanged.connect(
            lambda v: setattr(editor, "corner_radius", v)
        )
        self.sides_sb.valueChanged.connect(
            lambda v: setattr(editor, "polygon_sides", v)
        )
        self.arrow_start_cb.toggled.connect(lambda v: setattr(editor, "arrow_start", v))
        self.arrow_end_cb.toggled.connect(lambda v: setattr(editor, "arrow_end", v))
        self.arrow_size_sb.valueChanged.connect(
            lambda v: setattr(editor, "arrow_size", v)
        )
        self.inner_sb.valueChanged.connect(
            lambda v: setattr(editor, "star_inner_ratio", v / 100.0)
        )

        actions = (
            (self.add_node_btn, editor.add_nodes),
            (self.delete_node_btn, editor.delete_selection),
            (self.corner_btn, lambda: editor.set_node_type(vector_path.CORNER)),
            (self.smooth_btn, lambda: editor.set_node_type(vector_path.SMOOTH)),
            (self.symmetric_btn, lambda: editor.set_node_type(vector_path.SYMMETRIC)),
            (self.break_btn, editor.break_nodes),
            (self.join_btn, editor.join_nodes),
            (self.close_btn, editor.toggle_closed),
            (self.reverse_btn, editor.reverse_paths),
            (self.union_btn, lambda: editor.boolean(vector_editor.BOOL_UNION)),
            (self.subtract_btn, lambda: editor.boolean(vector_editor.BOOL_SUBTRACT)),
            (self.intersect_btn, lambda: editor.boolean(vector_editor.BOOL_INTERSECT)),
            (self.exclude_btn, lambda: editor.boolean(vector_editor.BOOL_EXCLUDE)),
            (self.flip_h_btn, lambda: editor.flip(True)),
            (self.flip_v_btn, lambda: editor.flip(False)),
            (self.duplicate_btn, editor.duplicate),
            (self.delete_btn, editor.delete_selection),
            (self.add_layer_btn, editor.add_layer),
            (
                self.duplicate_layer_btn,
                lambda: editor.duplicate_layer(editor.doc.current),
            ),
            (self.delete_layer_btn, lambda: editor.delete_layer(editor.doc.current)),
            (self.layer_up_btn, lambda: editor.move_layer(editor.doc.current, 1)),
            (self.layer_down_btn, lambda: editor.move_layer(editor.doc.current, -1)),
            (self.merge_btn, lambda: editor.merge_down(editor.doc.current)),
            (
                self.move_sel_btn,
                lambda: editor.move_selection_to_layer(editor.doc.current),
            ),
            (self.undo_btn, editor.undo),
            (self.redo_btn, editor.redo),
        )
        for button, fn in actions:
            button.clicked.connect(lambda *args, f=fn: self._act(f))
        self.cancel_btn.clicked.connect(editor.cancel)
        self.done_btn.clicked.connect(editor.done)

        self.x_sb.valueChanged.connect(lambda v: self._set_position(x=v))
        self.y_sb.valueChanged.connect(lambda v: self._set_position(y=v))
        self.snap_grid_cb.toggled.connect(lambda v: setattr(editor, "snap_grid", v))
        self.grid_size_sb.valueChanged.connect(self._set_grid_size)
        self.snap_nodes_cb.toggled.connect(lambda v: setattr(editor, "snap_nodes", v))
        self.outline_cb.toggled.connect(editor.set_outline)
        self.grid_cb.toggled.connect(editor.set_show_grid)

        self.layer_table.itemSelectionChanged.connect(self._on_layer_selected)
        self.layer_table.itemChanged.connect(self._on_layer_renamed)

    # =================================================================
    # EDITOR SYNC
    # =================================================================

    def _act(self, fn, *args):
        """Run a toolbar action and hand keyboard focus back to the canvas."""
        if not self.editor.is_active():
            return
        fn(*args)
        if self.editor.is_active():
            self.editor.view.activateWindow()
            self.editor.view.setFocus()

    def _on_session_started(self):
        if not self._placed:
            parent = self.parentWidget()
            if parent is not None:
                geometry = parent.frameGeometry()
                self.move(geometry.right() + 8, geometry.top())
            self._placed = True
        self.show()
        self.raise_()
        self.refresh()

    def _options_page(self, *widgets):
        """Add a row of option widgets as a page of the options stack."""
        page = QtWidgets.QWidget()
        page.setLayout(_row(*widgets))
        self.options_stack.addWidget(page)
        return page

    def _on_tool_changed(self, tool):
        button = self.tool_buttons.get(tool)
        if button is not None and not button.isChecked():
            button.setChecked(True)
        self.options_stack.setCurrentWidget(
            self._option_pages.get(tool, self._no_options_page)
        )

    def _set_position(self, x=None, y=None):
        if not self._syncing:
            self.editor.set_selection_position(x=x, y=y)

    def _set_grid_size(self, value):
        self.editor.grid_size = value
        self.editor.view.viewport().update()

    def refresh(self):
        """Sync every control with the editor state."""
        editor = self.editor
        if not editor.is_active():
            return
        self._syncing = True
        try:
            self._on_tool_changed(editor.tool)
            has_nodes = editor.has_node_selection()
            has_targets = editor.has_subpath_selection()
            for button in (
                self.add_node_btn,
                self.delete_node_btn,
                self.corner_btn,
                self.smooth_btn,
                self.symmetric_btn,
                self.break_btn,
            ):
                button.setEnabled(has_nodes)
            self.join_btn.setEnabled(editor.can_join())
            for button in (
                self.close_btn,
                self.reverse_btn,
                self.flip_h_btn,
                self.flip_v_btn,
                self.duplicate_btn,
                self.delete_btn,
            ):
                button.setEnabled(has_targets)
            can_boolean = editor.can_boolean()
            for button in (
                self.union_btn,
                self.subtract_btn,
                self.intersect_btn,
                self.exclude_btn,
            ):
                button.setEnabled(can_boolean)
            self.undo_btn.setEnabled(editor.can_undo())
            self.redo_btn.setEnabled(editor.can_redo())

            position = editor.selection_position()
            for box, value in zip((self.x_sb, self.y_sb), position or (0.0, 0.0)):
                box.setEnabled(position is not None)
                box.setValue(value)

            count = len(editor.doc.layers)
            self.delete_layer_btn.setEnabled(count > 1)
            self.merge_btn.setEnabled(editor.doc.current > 0)
            self.layer_up_btn.setEnabled(editor.doc.current < count - 1)
            self.layer_down_btn.setEnabled(editor.doc.current > 0)
            self.move_sel_btn.setEnabled(has_targets)
            self._rebuild_layers()
        finally:
            self._syncing = False

    # =================================================================
    # LAYER PANEL
    # =================================================================

    def _row_to_layer(self, row):
        """Rows list the front-most layer first."""
        return len(self.editor.doc.layers) - 1 - row

    def _rebuild_layers(self):
        table = self.layer_table
        layers = self.editor.doc.layers
        table.blockSignals(True)
        table.setRowCount(len(layers))
        for row in range(len(layers)):
            index = self._row_to_layer(row)
            layer = layers[index]

            visible = _tool_button(
                "mgear_eye" if layer["visible"] else "mgear_eye-off",
                tooltip="Show / hide layer",
            )
            visible.clicked.connect(
                lambda *args, i=index, v=layer["visible"]: self._act(
                    self.editor.set_layer_property, i, "visible", not v
                )
            )
            table.setCellWidget(row, _COL_VISIBLE, visible)

            lock = _tool_button(
                "mgear_lock" if layer["locked"] else "mgear_unlock",
                tooltip="Lock / unlock layer",
            )
            lock.clicked.connect(
                lambda *args, i=index, v=layer["locked"]: self._act(
                    self.editor.set_layer_property, i, "locked", not v
                )
            )
            table.setCellWidget(row, _COL_LOCK, lock)

            name = QtWidgets.QTableWidgetItem(layer["name"])
            table.setItem(row, _COL_NAME, name)

            mode = QtWidgets.QComboBox()
            mode.addItems(["Fill", "Stroke"])
            mode.setCurrentIndex(
                _MODES.index(layer["mode"]) if layer["mode"] in _MODES else 0
            )
            mode.currentIndexChanged.connect(
                lambda value, i=index: self.editor.set_layer_property(
                    i, "mode", _MODES[value]
                )
            )
            table.setCellWidget(row, _COL_MODE, mode)

            width = QtWidgets.QDoubleSpinBox()
            width.setRange(0.1, 100.0)
            width.setSingleStep(0.5)
            width.setValue(layer["stroke_width"])
            width.setKeyboardTracking(False)
            width.valueChanged.connect(
                lambda value, i=index: self.editor.set_layer_property(
                    i, "stroke_width", value
                )
            )
            table.setCellWidget(row, _COL_WIDTH, width)
            table.setCellWidget(row, _COL_COLOR, self._color_button(index, layer))
        current_row = len(layers) - 1 - self.editor.doc.current
        table.selectRow(current_row)
        table.blockSignals(False)

    def _color_button(self, index, layer):
        """Return the swatch button for a layer's color.

        Click picks a color for the layer; right-click resets it to the item
        color. A layer without its own color shows the item color.
        """
        button = QtWidgets.QToolButton()
        button.setAutoRaise(True)
        size = int(pyqt.dpi_scale(14))
        if layer.get("color"):
            color = QtGui.QColor(layer["color"])
            tooltip = "Layer color {} (click to change, right-click for the item "
            tooltip = tooltip.format(layer["color"]) + "color)"
        else:
            color = self.editor.item.get_color()
            tooltip = "Item color (click to give this layer its own color)"
        swatch = QtGui.QPixmap(size, size)
        swatch.fill(QtGui.QColor(color.red(), color.green(), color.blue()))
        button.setIcon(QtGui.QIcon(swatch))
        button.setToolTip(tooltip)
        button.clicked.connect(lambda *args, i=index: self._pick_layer_color(i))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, i=index, b=button: self._layer_color_menu(i, b, pos)
        )
        return button

    def _pick_layer_color(self, index):
        layer = self.editor.doc.layers[index]
        initial = (
            QtGui.QColor(layer["color"])
            if layer.get("color")
            else self.editor.item.get_color()
        )
        color = QtWidgets.QColorDialog.getColor(
            initial=initial, parent=self, title="Layer color"
        )
        if color.isValid():
            self._act(self.editor.set_layer_property, index, "color", color.name())

    def _layer_color_menu(self, index, button, pos):
        menu = QtWidgets.QMenu(button)
        reset = menu.addAction("Use item color")
        reset.setEnabled(bool(self.editor.doc.layers[index].get("color")))
        reset.triggered.connect(
            lambda *args: self._act(
                self.editor.set_layer_property, index, "color", None
            )
        )
        menu.exec_(button.mapToGlobal(pos))

    def _on_layer_selected(self):
        if self._syncing:
            return
        rows = self.layer_table.selectionModel().selectedRows()
        if rows:
            self.editor.set_current_layer(self._row_to_layer(rows[0].row()))

    def _on_layer_renamed(self, item):
        if self._syncing or item.column() != _COL_NAME:
            return
        name = item.text().strip()
        index = self._row_to_layer(item.row())
        if name:
            self.editor.set_layer_property(index, "name", name)
        else:
            self.refresh()

    def closeEvent(self, event):
        """Closing the toolbar ends the session, keeping its edits."""
        if self.editor.is_active():
            self.editor.done()
        super(VectorToolbar, self).closeEvent(event)
