"""Shape library picker dialog for the anim picker.

A small popup grid of shape swatches (bundled + user shapes). Clicking a swatch
applies that shape to the current selection via the supplied callback; the
current item's shape can be saved as a named custom shape, and user shapes can
be deleted from their right-click menu. The shape data / persistence lives in
the Qt-free ``widgets.shape_library`` module.
"""

from functools import partial

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import shape_library


class ShapeLibraryDialog(QtWidgets.QDialog):
    """Popup grid to apply a premade / custom shape to the selection."""

    _ICON_SIZE = 44
    _COLUMNS = 4

    def __init__(self, parent=None, apply_callback=None, current_handles=None):
        super(ShapeLibraryDialog, self).__init__(parent)
        self.setWindowTitle("Shape Library")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self._apply_callback = apply_callback
        self._current_handles = current_handles

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.grid_host = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_host)
        self.main_layout.addWidget(self.grid_host)

        button_row = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton("Save current shape...")
        self.save_button.setEnabled(bool(current_handles))
        self.save_button.clicked.connect(self._save_current)
        button_row.addWidget(self.save_button)
        button_row.addStretch()
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(close_button)
        self.main_layout.addLayout(button_row)

        self._rebuild_grid()

    def _rebuild_grid(self):
        """Repopulate the swatch grid from the shape library."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, shape in enumerate(shape_library.load_shapes()):
            button = QtWidgets.QToolButton()
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            button.setIcon(self._shape_icon(shape["handles"]))
            button.setIconSize(QtCore.QSize(self._ICON_SIZE, self._ICON_SIZE))
            button.setText(shape["name"])
            button.setAutoRaise(True)
            button.clicked.connect(
                partial(self._apply_shape, shape["handles"])
            )
            if not shape["builtin"]:
                button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                button.customContextMenuRequested.connect(
                    partial(self._user_shape_menu, shape["name"])
                )
                button.setToolTip("User shape (right-click to delete)")
            self.grid_layout.addWidget(
                button, index // self._COLUMNS, index % self._COLUMNS
            )

    def _shape_icon(self, handles, size=None):
        """Render a shape's outline into a QIcon preview."""
        size = size or self._ICON_SIZE
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor(220, 220, 220), 1.5))

        margin = 6.0
        span = size - 2.0 * margin
        if len(handles) == 2:
            # Native circle: center + radius point -> a centered ellipse.
            painter.drawEllipse(
                QtCore.QRectF(margin, margin, span, span)
            )
        else:
            xs = [point[0] for point in handles]
            ys = [point[1] for point in handles]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            width = (max_x - min_x) or 1.0
            height = (max_y - min_y) or 1.0
            scale = min(span / width, span / height)
            # Center the scaled shape; flip Y (scene is Y-up, icon Y-down).
            off_x = margin + (span - width * scale) / 2.0
            off_y = margin + (span - height * scale) / 2.0
            polygon = QtGui.QPolygonF()
            for hx, hy in handles:
                polygon.append(
                    QtCore.QPointF(
                        off_x + (hx - min_x) * scale,
                        off_y + (max_y - hy) * scale,
                    )
                )
            painter.drawPolygon(polygon)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _apply_shape(self, handles):
        if self._apply_callback is not None:
            self._apply_callback(handles)
        self.accept()

    def _save_current(self):
        if not self._current_handles:
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save shape", "Shape name"
        )
        if not (ok and name):
            return
        shape_library.save_user_shape(str(name), self._current_handles)
        self._rebuild_grid()

    def _user_shape_menu(self, name, pos):
        menu = QtWidgets.QMenu(self)
        delete_action = menu.addAction("Delete '{}'".format(name))
        chosen = menu.exec_(QtGui.QCursor.pos())
        if chosen == delete_action:
            shape_library.remove_user_shape(name)
            self._rebuild_grid()
