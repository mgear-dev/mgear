"""On-canvas move/scale manipulator for background layers.

``BackgroundManipulator`` owns the runtime selection of background layers, the
hit-testing, the overlay drawing (bounding box + 8 handles at a constant screen
size), and the drag lifecycle. The actual group-transform math lives in the
Qt/Maya-free ``background_transform`` module; this controller only bridges it to
the Qt view. It reads/writes ``BackgroundLayer`` models on the view's
``background_layers`` list and never touches persistence.
"""

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

from mgear.anim_picker.widgets import background_transform
from mgear.core import pyqt


class BackgroundManipulator(object):
    """Selection + move/scale controller for a view's background layers."""

    HANDLE_PX = 6  # half-size of a handle square, in screen pixels
    PICK_PX = 8  # handle pick radius, in screen pixels
    MIN_SIZE = 1.0
    COLOR = (255, 200, 40, 220)

    def __init__(self, view):
        self.view = view
        self.selected = []
        # Drag state, captured at begin_drag so transforms are from the start.
        self._drag_mode = None  # "body" | "handle" | None
        self._drag_handle = None
        self._drag_origin = None  # (x, y) in scene units
        self._orig_layers = None  # [(cx, cy, w, h), ...]
        self._orig_bounds = None  # (x, y, w, h)

    # -- helpers --------------------------------------------------------
    def _px_to_scene(self):
        """Return DPI-scaled scene units per screen pixel for the current zoom.

        The DPI factor (no-op at 100%) is folded in here so every screen-pixel
        handle / pick constant that multiplies this value grows on a high-DPI
        display, staying visible and hittable.
        """
        m11 = self.view.transform().m11()
        if not m11:
            return 1.0
        return pyqt.dpi_scale(1.0) / abs(m11)

    def _layers(self):
        return self.view.background_layers

    def selected_models(self):
        """Return the selected BackgroundLayer models in selection order."""
        layers = self._layers()
        return [
            layers[i].layer for i in self.selected if 0 <= i < len(layers)
        ]

    def bounds(self):
        """Return the union bounds of the selection, or None."""
        return background_transform.union_bounds(self.selected_models())

    # -- selection ------------------------------------------------------
    def clear(self):
        self.selected = []

    def set_selected(self, indices):
        count = len(self._layers())
        self.selected = [i for i in indices if 0 <= i < count]

    def select(self, index, additive=False):
        if additive:
            if index in self.selected:
                self.selected.remove(index)
            else:
                self.selected.append(index)
        else:
            self.selected = [index]

    def layer_at(self, x, y):
        """Return the front-most layer index containing (x, y), or None."""
        layers = self._layers()
        point = QtCore.QPointF(x, y)
        for i in range(len(layers) - 1, -1, -1):
            rect = layers[i].rect
            if rect is not None and rect.contains(point):
                return i
        return None

    def select_in_rect(self, rect, additive=False):
        """Select every layer whose cached rect intersects ``rect``."""
        hits = [
            i
            for i, loaded in enumerate(self._layers())
            if loaded.rect is not None and loaded.rect.intersects(rect)
        ]
        if additive:
            for i in hits:
                if i not in self.selected:
                    self.selected.append(i)
        else:
            self.selected = hits

    # -- hit testing ----------------------------------------------------
    def hit_test(self, x, y):
        """Return ("handle", id) / ("body",) / None for a scene point."""
        if not self.selected:
            return None
        bounds = self.bounds()
        if bounds is None:
            return None
        radius = self.PICK_PX * self._px_to_scene()
        for hid, (hx, hy) in background_transform.handle_points(bounds).items():
            if abs(x - hx) <= radius and abs(y - hy) <= radius:
                return ("handle", hid)
        bx, by, bw, bh = bounds
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return ("body",)
        return None

    # -- drag lifecycle -------------------------------------------------
    def begin_drag(self, mode, handle, x, y):
        self._drag_mode = mode
        self._drag_handle = handle
        self._drag_origin = (x, y)
        self._orig_layers = [
            (m.position[0], m.position[1], m.size[0], m.size[1])
            for m in self.selected_models()
        ]
        self._orig_bounds = self.bounds()

    def update_drag(self, x, y, keep_aspect=False):
        if self._drag_mode is None:
            return
        models = self.selected_models()
        # Restore originals so the transform is computed from the drag start.
        for model, orig in zip(models, self._orig_layers):
            model.position = [orig[0], orig[1]]
            model.size = [orig[2], orig[3]]

        if self._drag_mode == "body":
            dx = x - self._drag_origin[0]
            dy = y - self._drag_origin[1]
            background_transform.move_layers(models, dx, dy)
        else:
            anchor_x, anchor_y, sx, sy = background_transform.scale_factors(
                self._orig_bounds, self._drag_handle, x, y, keep_aspect
            )
            background_transform.scale_layers(
                models, anchor_x, anchor_y, sx, sy, self.MIN_SIZE
            )

    def end_drag(self):
        self._drag_mode = None
        self._drag_handle = None
        self._drag_origin = None
        self._orig_layers = None
        self._orig_bounds = None

    def is_dragging(self):
        return self._drag_mode is not None

    # -- painting -------------------------------------------------------
    def paint(self, painter):
        """Draw the selection bounding box and handles (scene coordinates)."""
        if not self.selected:
            return
        bounds = self.bounds()
        if bounds is None:
            return

        x, y, w, h = bounds
        color = QtGui.QColor(*self.COLOR)

        # Cosmetic 1px outline keeps a constant screen width at any zoom.
        pen = QtGui.QPen(color, 0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(QtCore.QRectF(x, y, w, h))

        half = self.HANDLE_PX * self._px_to_scene()
        painter.setBrush(color)
        for hx, hy in background_transform.handle_points(bounds).values():
            painter.drawRect(
                QtCore.QRectF(hx - half, hy - half, half * 2.0, half * 2.0)
            )
