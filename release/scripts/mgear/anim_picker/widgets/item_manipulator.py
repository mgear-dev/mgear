"""On-canvas scale/rotate manipulator for picker items.

``ItemManipulator`` draws a bounding-box overlay with 8 scale handles and a
rotate handle around the current picker-item selection (edit mode only),
hit-tests those handles, and applies a group scale / rotate to every selected
item on drag. Moving is left to the existing item drag -- dragging a selected
item already moves the whole selection -- so the manipulator adds no body-move
(which would fight the rubber-band selection).

The selection is read live from the scene (``get_selected_items``), so this
controller stores no selection state of its own; only the drag capture. The
transform math lives in the Qt/Maya-free ``manipulator_transform`` module shared
with the background manipulator.
"""

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui

from mgear.anim_picker.widgets import manipulator_transform
from mgear.core import svg_import
from mgear.core import pyqt


class ItemManipulator(object):
    """Scale/rotate controller for the view's selected picker items."""

    HANDLE_PX = 6  # half-size of a scale handle square, screen pixels
    PICK_PX = 8  # handle pick radius, screen pixels
    ROTATE_PX = 22  # rotate handle offset past the box top, screen pixels
    ROTATE_RADIUS_PX = 6  # rotate handle circle radius, screen pixels
    COLOR = (40, 200, 255, 220)

    def __init__(self, view):
        self.view = view
        # Drag state, captured at begin_drag so transforms are from the start.
        self._drag_mode = None  # "scale" | "rotate" | None
        self._drag_handle = None
        self._drag_origin = None  # (x, y) in scene units
        # [(item, x, y, rotation, [[hx, hy], ...]), ...] at drag start
        self._orig_items = None
        self._orig_bounds = None  # (x, y, w, h); center is derived from this

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

    def selected_items(self):
        """Return the currently selected picker items (live from the scene)."""
        return self.view.scene().get_selected_items()

    def is_active(self):
        """Return True when there is a selection to manipulate."""
        return bool(self.selected_items())

    def bounds(self):
        """Return the union sceneBoundingRect of the selection as bounds.

        Returns:
            tuple: ``(x, y, w, h)`` or None when the selection is empty.
        """
        rect = None
        for item in self.selected_items():
            item_rect = item.sceneBoundingRect()
            rect = item_rect if rect is None else rect.united(item_rect)
        if rect is None:
            return None
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def _rotate_handle_point(self, bounds, px):
        """Return the rotate handle (x, y), above the box top-center.

        The scene is Y-up (the view flips Y), so the box top edge is at
        ``y + h`` and a positive offset places the handle above it on screen.

        Args:
            bounds (tuple): ``(x, y, w, h)``.
            px (float): scene units per screen pixel (precomputed by caller).
        """
        x, y, w, h = bounds
        offset = self.ROTATE_PX * px
        return (x + w / 2.0, y + h + offset)

    # -- hit testing ----------------------------------------------------
    def hit_test(self, x, y):
        """Return ("rotate",) / ("scale", id) / None for a scene point."""
        bounds = self.bounds()
        if bounds is None:
            return None
        px = self._px_to_scene()
        radius = self.PICK_PX * px

        # Rotate handle first: it sits outside the box, above top-center.
        rx, ry = self._rotate_handle_point(bounds, px)
        rot_radius = max(self.ROTATE_RADIUS_PX, self.PICK_PX) * px
        if abs(x - rx) <= rot_radius and abs(y - ry) <= rot_radius:
            return ("rotate",)

        for hid, (hx, hy) in manipulator_transform.handle_points(
            bounds
        ).items():
            if abs(x - hx) <= radius and abs(y - hy) <= radius:
                return ("scale", hid)
        return None

    # -- drag lifecycle -------------------------------------------------
    def begin_drag(self, mode, handle, x, y):
        """Capture the selection's original transforms and the group frame."""
        self._drag_mode = mode
        self._drag_handle = handle
        self._drag_origin = (x, y)
        self._orig_bounds = self.bounds()
        self._orig_items = []
        for item in self.selected_items():
            handles = [[h.x(), h.y()] for h in item.handles]
            # Capture the vector subpaths too, so a vector item scales its
            # curve (baked into the subpaths) rather than its hidden handles.
            svg_subpaths = item.get_svg_subpaths()
            self._orig_items.append(
                (item, item.x(), item.y(), item.rotation(), handles,
                 svg_subpaths)
            )

    def update_drag(self, x, y, keep_aspect=False):
        """Recompute the transform from the drag start (no cumulative drift)."""
        if self._drag_mode == "scale":
            self._update_scale(x, y, keep_aspect)
        elif self._drag_mode == "rotate":
            self._update_rotate(x, y)

    def _update_scale(self, x, y, keep_aspect):
        anchor_x, anchor_y, sx, sy = manipulator_transform.scale_factors(
            self._orig_bounds, self._drag_handle, x, y, keep_aspect
        )
        for item, ox, oy, _orot, ohandles, osvg in self._orig_items:
            item.setPos(
                anchor_x + (ox - anchor_x) * sx,
                anchor_y + (oy - anchor_y) * sy,
            )
            # Scale the body geometry in the item's own (axis-aligned) local
            # frame, rebuilt from the captured originals. A vector item scales
            # its subpaths (baked); a polygon scales its handles. Non-uniform
            # scale of a rotated item shears it (v1 limitation); uniform exact.
            if item.is_vector_shape():
                item.set_svg_subpaths(
                    svg_import.scale_subpaths(osvg, sx, sy)
                )
            else:
                for handle, (hx, hy) in zip(item.handles, ohandles):
                    handle.setPos(hx * sx, hy * sy)
            item.update()

    def _update_rotate(self, x, y):
        bx, by, bw, bh = self._orig_bounds
        cx, cy = bx + bw / 2.0, by + bh / 2.0
        angle = manipulator_transform.rotate_delta(
            cx, cy, self._drag_origin[0], self._drag_origin[1], x, y
        )
        # Rigid rotation about the group center: orbit each item's position and
        # add the same angle to its rotation. A single item's center is its own
        # bbox center, so it rotates in place.
        for item, ox, oy, orot, _ohandles, _osvg in self._orig_items:
            nx, ny = manipulator_transform.rotate_point(ox, oy, cx, cy, angle)
            item.setPos(nx, ny)
            item.setRotation(orot + angle)

    def end_drag(self):
        self._drag_mode = None
        self._drag_handle = None
        self._drag_origin = None
        self._orig_items = None
        self._orig_bounds = None

    # -- painting -------------------------------------------------------
    def paint(self, painter):
        """Draw the selection bbox, scale handles, and rotate handle."""
        bounds = self.bounds()
        if bounds is None:
            return

        x, y, w, h = bounds
        px = self._px_to_scene()
        color = QtGui.QColor(*self.COLOR)

        # Cosmetic 1px outline keeps a constant screen width at any zoom.
        pen = QtGui.QPen(color, 0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(QtCore.QRectF(x, y, w, h))

        # Rotate handle: a stalk from the top-center plus a filled circle.
        rx, ry = self._rotate_handle_point(bounds, px)
        painter.drawLine(QtCore.QLineF(x + w / 2.0, y + h, rx, ry))
        r = self.ROTATE_RADIUS_PX * px
        painter.setBrush(color)
        painter.drawEllipse(QtCore.QRectF(rx - r, ry - r, r * 2.0, r * 2.0))

        # Scale handles (constant screen size).
        half = self.HANDLE_PX * px
        for hx, hy in manipulator_transform.handle_points(bounds).values():
            painter.drawRect(
                QtCore.QRectF(hx - half, hy - half, half * 2.0, half * 2.0)
            )
