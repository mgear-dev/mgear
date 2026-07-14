"""Shape library picker dialog for the anim picker.

Two tabs -- **Polygons** (editable straight-line shapes) and **SVG** (curved
vector shapes: the bundled ``.svg`` templates plus any imported ones saved by
the user). A tile can be:

- **clicked** to apply that shape to the current selection;
- **dragged** onto the canvas to create a new item with that shape at the drop
  point;
- **right-clicked** for Apply / Create-from-selection (vertical / horizontal)
  and, for a user shape, Delete.

The current item's shape can be saved as a named custom shape; a vector item
(e.g. an imported SVG) is stored in the SVG tab, a polygon item in the Polygons
tab. Icon previews render the real geometry (curves included) via the shared
``graphics.build_vector_path``. The shape data / persistence lives in the
Qt-free ``widgets.shape_library`` module.
"""

import math
from functools import partial

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import shape_library
from mgear.anim_picker.widgets import tool_bar
from mgear.anim_picker.widgets import graphics


class ShapeLibraryDialog(QtWidgets.QDialog):
    """Tabbed grid to apply / drag-create / stamp a premade or custom shape."""

    _ICON_SIZE = 44
    _COLUMNS = 4
    _ICON_MARGIN = 6.0  # padding inside a tile's icon box, in pixels
    _TILE_W = 100  # fixed tile size so the grid aligns into clean columns
    _TILE_H = 78

    def __init__(
        self,
        parent=None,
        apply_callback=None,
        create_callback=None,
        current_shape_getter=None,
    ):
        super(ShapeLibraryDialog, self).__init__(parent)
        self.setWindowTitle("Shape Library")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.resize(460, 440)

        # apply_callback(shape): apply to selection. create_callback(shape,
        # axis): stamp one per selected control. current_shape_getter(): return
        # the active item's shape ({handles} or {subpaths, mode}) live, for
        # "Save current" -- a getter (not a snapshot) so it reflects the
        # selection even after the (modeless) dialog is already open.
        self._apply_callback = apply_callback
        self._create_callback = create_callback
        self._current_shape_getter = current_shape_getter

        self.main_layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QLabel(
            "Click: apply to selection    Drag: create on canvas    "
            "Right-click: create from selection"
        )
        hint.setStyleSheet("color: #9a9a9a;")
        self.main_layout.addWidget(hint)

        # Two tabs: editable polygons and curved vector (SVG) shapes.
        self.tabs = QtWidgets.QTabWidget()
        self.poly_grid = self._make_tab("Polygons")
        self.svg_grid = self._make_tab("SVG")
        self.main_layout.addWidget(self.tabs)

        button_row = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Save current shape...")
        # Enabled whenever a getter is wired; the live selection is checked on
        # click (so it is not stuck disabled from an empty open-time snapshot).
        self.save_button.setEnabled(current_shape_getter is not None)
        self.save_button.clicked.connect(self._save_current)
        button_row.addWidget(self.save_button)
        button_row.addStretch()
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        self.main_layout.addLayout(button_row)

        self._rebuild_grid()

    def _make_tab(self, title):
        """Add a scrollable grid tab and return its ``QGridLayout``."""
        host = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(host)
        grid.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(host)
        self.tabs.addTab(scroll, title)
        return grid

    def _rebuild_grid(self):
        """Repopulate both tab grids from the shape library, split by kind."""
        for grid in (self.poly_grid, self.svg_grid):
            while grid.count():
                item = grid.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        poly_index = 0
        svg_index = 0
        for shape in shape_library.load_shapes():
            if shape.get("kind") == shape_library.KIND_VECTOR:
                self._add_tile(self.svg_grid, svg_index, shape)
                svg_index += 1
            else:
                self._add_tile(self.poly_grid, poly_index, shape)
                poly_index += 1

    def _add_tile(self, grid, index, shape):
        """Add one shape tile to ``grid`` at the running ``index``."""
        button = tool_bar.DragTileButton(
            shape_library.SHAPE_MIME, shape["name"], icon_size=self._ICON_SIZE
        )
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        button.setIcon(self._shape_icon(shape))
        button.setIconSize(QtCore.QSize(self._ICON_SIZE, self._ICON_SIZE))
        button.setText(shape["name"])
        button.setAutoRaise(True)
        button.setFixedSize(QtCore.QSize(self._TILE_W, self._TILE_H))
        button.clicked.connect(partial(self._apply_shape, shape))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(
            partial(self._tile_menu, shape)
        )
        tip = "Click: apply   Drag: create on canvas   Right-click: more"
        if not shape["builtin"]:
            tip += "   (user shape)"
        button.setToolTip(tip)
        grid.addWidget(
            button, index // self._COLUMNS, index % self._COLUMNS
        )

    # -- icon rendering -------------------------------------------------
    def _shape_path(self, shape):
        """Build a ``QPainterPath`` for a shape (polygon or vector).

        Coordinates are the item's scene coordinates (Y-up); ``_draw_path_fit``
        fits and flips them for the icon.
        """
        if shape.get("kind") == shape_library.KIND_VECTOR:
            return graphics.build_vector_path(shape.get("subpaths", []))
        handles = shape.get("handles", [])
        path = QtGui.QPainterPath()
        if len(handles) == 2:
            # A 2-handle polygon is a native circle (center + radius point).
            (cx, cy), (rx, ry) = handles
            radius = math.hypot(rx - cx, ry - cy) or 1.0
            path.addEllipse(QtCore.QPointF(cx, cy), radius, radius)
        elif handles:
            path.moveTo(handles[0][0], handles[0][1])
            for hx, hy in handles[1:]:
                path.lineTo(hx, hy)
            path.closeSubpath()
        return path

    def _shape_icon(self, shape, size=None):
        """Render a shape (polygon or vector, real curves) into a QIcon."""
        size = size or self._ICON_SIZE
        path = self._shape_path(shape)
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor(220, 220, 220), 1.5)
        pen.setCosmetic(True)  # constant width despite the fit scale
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        self._draw_path_fit(painter, path, size)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _draw_path_fit(self, painter, path, size):
        """Draw ``path`` fit + centered in the icon box (upright)."""
        rect = path.boundingRect()
        if rect.isEmpty():
            return
        margin = self._ICON_MARGIN
        span = size - 2.0 * margin
        width = rect.width() or 1.0
        height = rect.height() or 1.0
        scale = min(span / width, span / height)
        off_x = margin + (span - width * scale) / 2.0
        off_y = margin + (span - height * scale) / 2.0
        # Flip Y (scene is Y-up, the icon Y-down) so the shape draws upright.
        transform = QtGui.QTransform()
        transform.translate(
            off_x - rect.left() * scale, off_y + rect.bottom() * scale
        )
        transform.scale(scale, -scale)
        painter.save()
        painter.setTransform(transform, True)
        painter.drawPath(path)
        painter.restore()

    # -- actions --------------------------------------------------------
    def _apply_shape(self, shape):
        if self._apply_callback is not None:
            self._apply_callback(shape)
        self.accept()

    def _tile_menu(self, shape, pos):
        """Right-click menu: apply / create-from-selection / delete (user)."""
        menu = QtWidgets.QMenu(self)
        apply_action = menu.addAction("Apply to selection")
        create_v = menu.addAction("Create from selection (vertical)")
        create_h = menu.addAction("Create from selection (horizontal)")
        delete_action = None
        if not shape["builtin"]:
            menu.addSeparator()
            delete_action = menu.addAction(
                "Delete '{}'".format(shape["name"])
            )
        chosen = menu.exec_(QtGui.QCursor.pos())
        if chosen is None:
            return
        if chosen == apply_action:
            self._apply_shape(shape)
        elif chosen in (create_v, create_h):
            if self._create_callback is not None:
                axis = "vertical" if chosen == create_v else "horizontal"
                self._create_callback(shape, axis)
        elif chosen == delete_action:
            shape_library.remove_user_shape(shape["name"])
            self._rebuild_grid()

    def _save_current(self):
        shape = None
        if self._current_shape_getter is not None:
            shape = self._current_shape_getter()
        if not shape:
            QtWidgets.QMessageBox.information(
                self, "Save shape", "Select a picker item first."
            )
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save shape", "Shape name"
        )
        if not (ok and name):
            return
        shape_library.save_user_shape(
            str(name),
            handles=shape.get("handles"),
            subpaths=shape.get("subpaths"),
            mode=shape.get("mode"),
        )
        self._rebuild_grid()
        # Show the tab the saved shape landed in (vector -> the SVG tab).
        self.tabs.setCurrentIndex(1 if shape.get("subpaths") else 0)
