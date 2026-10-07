"""In-canvas SVG editor for anim picker vector items.

``VectorEditor`` runs one SVG edit session on one vector ``PickerItem`` at a
time, inside its picker view. It owns a ``vector_model.VectorDocument`` (the
working copy), the active tool, the drag state, and a session undo stack.
Every edit is applied to the item immediately, so the canvas always shows the
real result; ``done`` records the whole session as one picker undo step and
``cancel`` restores the item as it was.

Geometry is edited in the item's local coordinates (``mapFromScene``), so a
moved or rotated item edits correctly. The view delegates left-button mouse
events, double-clicks, keys, and foreground painting to the active editor;
middle-button pan and Alt zoom still reach the view.

All curve math lives in ``mgear.core.vector_path`` (Qt-free); this module
adds interaction, painting, and the ``QPainterPath`` boolean operations.
"""

import copy
import math

from mgear.core import pyqt
from mgear.core import vector_path
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import edit_undo
from mgear.anim_picker.widgets import manipulator_transform
from mgear.anim_picker.widgets import vector_model
from mgear.anim_picker.widgets.graphics import build_vector_path

TOOL_SELECT = "select"
TOOL_NODE = "node"
TOOL_PEN = "pen"
TOOL_RECT = "rect"
TOOL_ELLIPSE = "ellipse"
TOOL_POLYGON = "polygon"
TOOL_LINE = "line"

BOOL_UNION = "union"
BOOL_SUBTRACT = "subtract"
BOOL_INTERSECT = "intersect"
BOOL_EXCLUDE = "exclude"

# Screen-pixel sizes (DPI-scaled) for picking and drawing the overlay.
PICK_PX = 6.0
ANCHOR_PX = 4.0
HANDLE_PX = 3.0
BOX_HANDLE_PX = 4.0
ROTATE_OFFSET_PX = 18.0
MIN_GRID_PX = 6.0

# Opacity of the other items while a session is active.
DIM_OPACITY = 0.3

# Tolerance used to re-fit flattened boolean results into curves.
BOOLEAN_FIT_TOLERANCE = 0.05

_OUTLINE_COLOR = QtGui.QColor(0, 190, 255, 200)
_SELECTED_COLOR = QtGui.QColor(0, 150, 255)
_ANCHOR_FILL = QtGui.QColor(245, 245, 245)
_HANDLE_COLOR = QtGui.QColor(255, 170, 60)
_HOVER_COLOR = QtGui.QColor(255, 255, 255, 220)
_PREVIEW_COLOR = QtGui.QColor(255, 120, 180)
_GRID_COLOR = QtGui.QColor(255, 255, 255, 28)


# The one editor running a session (only one SVG session at a time).
_ACTIVE = {"editor": None}


def end_active_session():
    """End the active SVG edit session, keeping its edits (Done).

    Called when the picker switches tab, leaves edit mode, or closes.
    """
    editor = _ACTIVE["editor"]
    if editor is not None:
        editor.done()


def path_to_subpaths(path, tolerance=BOOLEAN_FIT_TOLERANCE):
    """Convert a (flattened) ``QPainterPath`` into closed fitted subpaths.

    Qt's boolean operations return polygons; each one is re-fitted into
    curves and lines with ``vector_path.fit_curves``.

    Args:
        path (QtGui.QPainterPath): The path to convert.
        tolerance (float, optional): Curve fit tolerance.

    Returns:
        list: Closed subpaths.
    """
    result = []
    for polygon in path.toSubpathPolygons():
        points = [(p.x(), p.y()) for p in polygon]
        if len(points) < 3:
            continue
        subpath = vector_path.fit_curves(points, tolerance=tolerance, closed=True)
        if subpath:
            result.append(subpath)
    return result


# Tool pointers: (icon, rotation in degrees, hotspot in 24px icon space).
# The Node tool's icon points up-right; a quarter turn makes it a pointer.
_POINTER_ICONS = {
    TOOL_SELECT: ("mgear_mouse-pointer", 0, (3, 3)),
    TOOL_NODE: ("mgear_navigation", -90, (2, 2)),
    TOOL_PEN: ("mgear_pen-tool", 0, (2, 2)),
}
# Drawing tools: a crosshair with the tool's icon as a small badge.
_BADGE_ICONS = {
    TOOL_RECT: "mgear_square",
    TOOL_ELLIPSE: "mgear_circle",
    TOOL_POLYGON: "mgear_star",
    TOOL_LINE: "mgear_minus",
}
CURSOR_PX = 24
_CURSORS = {}


def _draw_outlined(painter, pixmap, x, y):
    """Draw ``pixmap`` with a dark 1px halo so it reads on any background."""
    shadow = QtGui.QPixmap(pixmap.size())
    shadow.fill(QtCore.Qt.transparent)
    shadow_painter = QtGui.QPainter(shadow)
    shadow_painter.drawPixmap(0, 0, pixmap)
    shadow_painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    shadow_painter.fillRect(shadow.rect(), QtGui.QColor(0, 0, 0, 230))
    shadow_painter.end()
    for dx, dy in (
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (1, 1),
        (-1, 1),
        (1, -1),
    ):
        painter.drawPixmap(x + dx, y + dy, shadow)
    painter.drawPixmap(x, y, pixmap)


def tool_cursor(tool):
    """Return the mouse pointer for a tool, built from its icon (cached).

    Select, Node and Pen use their icon with the hotspot at its tip; the
    drawing tools use a crosshair with the tool icon as a badge.

    Args:
        tool (str): One of the ``TOOL_*`` ids.

    Returns:
        QtGui.QCursor: The tool's pointer.
    """
    if tool in _CURSORS:
        return _CURSORS[tool]
    size = int(pyqt.dpi_scale(CURSOR_PX))
    scale = size / 24.0
    canvas = QtGui.QPixmap(size + 2, size + 2)
    canvas.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(canvas)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    if tool in _POINTER_ICONS:
        name, angle, (hx, hy) = _POINTER_ICONS[tool]
        icon = pyqt.get_icon(name, size)
        if angle:
            icon = icon.transformed(QtGui.QTransform().rotate(angle))
        _draw_outlined(painter, icon, 1, 1)
        hotspot = (int(hx * scale) + 1, int(hy * scale) + 1)
    else:
        center = int(size * 0.35) + 1
        arm = int(size * 0.3)
        for color, width in ((QtGui.QColor(0, 0, 0, 230), 3.0), (QtCore.Qt.white, 1.0)):
            pen = QtGui.QPen(color)
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.drawLine(center - arm, center, center + arm, center)
            painter.drawLine(center, center - arm, center, center + arm)
        badge = pyqt.get_icon(_BADGE_ICONS.get(tool, "mgear_plus"), int(size * 0.45))
        _draw_outlined(painter, badge, int(size * 0.52), int(size * 0.52))
        hotspot = (center, center)
    painter.end()
    _CURSORS[tool] = QtGui.QCursor(canvas, hotspot[0], hotspot[1])
    return _CURSORS[tool]


def _snapshot_subpaths(snapshot):
    """Return the per-layer subpath lists of a document snapshot."""
    return [layer["subpaths"] for layer in snapshot["layers"]]


def _hover_key(hit):
    """Return a comparable identity for a hit-test result (None for none)."""
    if not hit:
        return None
    return (
        hit["kind"],
        hit.get("layer"),
        hit["subpath"],
        hit.get("node"),
        hit.get("which"),
        hit.get("segment"),
    )


class VectorEditor(QtCore.QObject):
    """SVG edit session controller for one picker view.

    Args:
        view (GraphicViewWidget): The picker view the editor works in.
    """

    changed = QtCore.Signal()
    tool_changed = QtCore.Signal(str)
    session_started = QtCore.Signal()
    session_ended = QtCore.Signal()

    def __init__(self, view):
        super(VectorEditor, self).__init__(view)
        self.view = view
        self.item = None
        self.doc = None
        self.tool = TOOL_NODE
        self._undo = edit_undo.UndoStack(max_steps=200)
        self._entry_svg = None
        self._is_new = False
        self._dimmed = []

        # Tool options (set from the toolbar).
        self.corner_radius = 0.0
        self.polygon_sides = 5
        self.star_inner_ratio = 0.0
        self.snap_grid = False
        self.snap_nodes = False
        self.grid_size = 5.0
        self.show_grid = False
        self.outline = False
        self.arrow_start = False
        self.arrow_end = False
        self.arrow_size = 3.0

        # Interaction state.
        self._drag = None
        self._marquee = None
        self._hover = None
        self._cursor = None
        self._pen_nodes = []
        self._pen_dragging = False
        self._shape_drag = None
        # Scene units per screen pixel, refreshed at the start of paint().
        self._paint_scene_px = 1.0

    # =================================================================
    # SESSION
    # =================================================================

    def is_active(self):
        """Return True while a session is running.

        Returns:
            bool: Session state.
        """
        return self.item is not None

    def begin(self, item, tool=TOOL_NODE, is_new=False, flush=True):
        """Start an SVG edit session on ``item``.

        Args:
            item (PickerItem): The vector item to edit.
            tool (str, optional): The tool to start with.
            is_new (bool, optional): The item was just created for this
                session; it is removed again if it ends empty or cancelled.
            flush (bool, optional): Commit pending picker undo first, so the
                session's commit holds only the session's changes.
        """
        end_active_session()
        if flush:
            self.view.commit_edit()
        self.view.clear_selection()
        self.item = item
        self._is_new = is_new
        self._entry_svg = dict(item.get_svg_shape())
        self.doc = vector_model.VectorDocument.from_svg_data(self._entry_svg)
        self._undo.clear()
        self._reset_interaction()
        self._dim_others(True)
        item.vector_graphic.set_outline_mode(self.outline)
        _ACTIVE["editor"] = self
        self.set_tool(tool)
        self.session_started.emit()
        self.changed.emit()
        self.view.setFocus()
        self.view.viewport().update()

    def done(self):
        """End the session keeping the edits, as one picker undo step."""
        if not self.is_active():
            return
        self._finish_pen(False)
        # A drag interrupted by a tab / mode change only previewed live.
        self.apply()
        item = self.item
        remove = self._is_new and self.doc.is_empty()
        self._end_session()
        if remove:
            item.remove()
        self.view.commit_edit("Edit SVG")

    def cancel(self):
        """End the session restoring the item as it was before it."""
        if not self.is_active():
            return
        item = self.item
        item.set_svg_shape(self._entry_svg)
        remove = self._is_new
        self._end_session()
        if remove:
            item.remove()
        # The picker is back at its pre-session state: nothing to record.
        self.view._reset_undo_baseline()

    def _end_session(self):
        self.item.vector_graphic.set_outline_mode(False)
        self._dim_others(False)
        self._reset_interaction()
        self.item = None
        self.doc = None
        self._undo.clear()
        if _ACTIVE["editor"] is self:
            _ACTIVE["editor"] = None
        self.view.viewport().unsetCursor()
        self.session_ended.emit()
        self.view.viewport().update()

    def _reset_interaction(self):
        self._drag = None
        self._marquee = None
        self._hover = None
        self._pen_nodes = []
        self._pen_dragging = False
        self._shape_drag = None

    def _dim_others(self, state):
        if state:
            self._dimmed = []
            for other in self.view.get_picker_items():
                if other is self.item:
                    continue
                self._dimmed.append((other, other.opacity()))
                other.setOpacity(DIM_OPACITY)
        else:
            for other, opacity in self._dimmed:
                try:
                    other.setOpacity(opacity)
                except RuntimeError:
                    pass
            self._dimmed = []

    def apply(self, live=False):
        """Show the document on the item and repaint.

        Args:
            live (bool, optional): Only redraw the item's graphic (during a
                drag); the item's ``svg`` data is written on release.
        """
        if live:
            self.item.vector_graphic.set_layers(self.doc.layers)
        else:
            self.item.set_svg_layers(self.doc.layers)
        self.view.viewport().update()

    def _edit(self, fn):
        """Run ``fn`` on the document as one session undo step.

        Args:
            fn (callable): Mutates ``self.doc``.
        """
        before = self.doc.snapshot()
        fn()
        self._push(before)

    def _push(self, before):
        self._undo.push({"before": before, "after": self.doc.snapshot()})
        self._refresh()

    def _refresh(self):
        """Apply the document to the item and notify the toolbar."""
        self.apply()
        self.changed.emit()

    def undo(self):
        """Step back one session edit."""
        if self._pen_nodes:
            self._finish_pen(False, discard=True)
            return
        record = self._undo.undo()
        if record:
            self.doc.restore(record["before"])
            self._refresh()

    def redo(self):
        """Re-apply one undone session edit."""
        record = self._undo.redo()
        if record:
            self.doc.restore(record["after"])
            self._refresh()

    def can_undo(self):
        """Return True when there is a session edit to undo."""
        return self._undo.can_undo()

    def can_redo(self):
        """Return True when there is a session edit to redo."""
        return self._undo.can_redo()

    # =================================================================
    # TOOLS AND OPTIONS
    # =================================================================

    def set_tool(self, tool):
        """Activate a tool, finishing any path being drawn.

        Args:
            tool (str): One of the ``TOOL_*`` ids.
        """
        if self.is_active() and tool != TOOL_PEN:
            self._finish_pen(False)
        self.tool = tool
        self._drag = None
        self._shape_drag = None
        self._marquee = None
        self._hover = None
        if self.is_active():
            self.view.viewport().setCursor(tool_cursor(tool))
        self.tool_changed.emit(tool)
        self.view.viewport().update()

    def set_outline(self, state):
        """Toggle the outline (wireframe) view.

        Args:
            state (bool): Outline view on or off.
        """
        self.outline = bool(state)
        if self.is_active():
            self.item.vector_graphic.set_outline_mode(self.outline)

    def set_show_grid(self, state):
        """Toggle drawing the snap grid.

        Args:
            state (bool): Grid on or off.
        """
        self.show_grid = bool(state)
        self.view.viewport().update()

    # =================================================================
    # COORDINATES
    # =================================================================

    def _to_local(self, view_pos):
        point = self.item.mapFromScene(self.view.mapToScene(view_pos))
        return (point.x(), point.y())

    def _to_scene(self, point):
        return self.item.mapToScene(QtCore.QPointF(point[0], point[1]))

    def _px(self):
        """Return item-local units per DPI-scaled screen pixel."""
        scene_px = self._scene_px()
        a = self.item.mapFromScene(QtCore.QPointF(0.0, 0.0))
        b = self.item.mapFromScene(QtCore.QPointF(scene_px, 0.0))
        return math.hypot(b.x() - a.x(), b.y() - a.y()) or scene_px

    def _scene_px(self):
        """Return scene units per DPI-scaled screen pixel."""
        m11 = self.view.transform().m11()
        return pyqt.dpi_scale(1.0) / abs(m11) if m11 else 1.0

    def _snap(self, point, exclude=None):
        """Snap a local point to a node, then to the grid, when enabled."""
        if self.snap_nodes:
            best = None
            tolerance = PICK_PX * self._px()
            for li, layer in enumerate(self.doc.layers):
                if not layer["visible"]:
                    continue
                for si, subpath in enumerate(layer["subpaths"]):
                    nodes, _closed = vector_path.to_nodes(subpath)
                    for ni, node in enumerate(nodes):
                        if exclude and (li, si, ni) in exclude:
                            continue
                        anchor = node["anchor"]
                        d = math.hypot(anchor[0] - point[0], anchor[1] - point[1])
                        if d <= tolerance and (best is None or d < best[0]):
                            best = (d, anchor)
            if best:
                return best[1]
        if self.snap_grid and self.grid_size > 0:
            size = self.grid_size
            return (round(point[0] / size) * size, round(point[1] / size) * size)
        return point

    @staticmethod
    def _constrain_angle(origin, point):
        """Constrain ``point`` to 45-degree steps around ``origin``."""
        dx = point[0] - origin[0]
        dy = point[1] - origin[1]
        length = math.hypot(dx, dy)
        if length < vector_path.EPSILON:
            return point
        angle = round(math.atan2(dy, dx) / (math.pi / 4.0)) * (math.pi / 4.0)
        return (
            origin[0] + length * math.cos(angle),
            origin[1] + length * math.sin(angle),
        )

    # =================================================================
    # SELECTION HELPERS
    # =================================================================

    def _layer_subpaths(self, li):
        return self.doc.layers[li]["subpaths"]

    def _editable_layers_front_to_back(self):
        return [
            li for li in reversed(range(len(self.doc.layers))) if self.doc.editable(li)
        ]

    def target_subpaths(self):
        """Return the ``(layer, subpath)`` pairs the selection covers.

        Returns:
            set: Selected subpaths plus subpaths with a selected node.
        """
        result = set(self.doc.selected_subpaths)
        result.update((li, si) for li, si, _ni in self.doc.selected_nodes)
        return result

    def _handle_nodes(self, li):
        """Return the (subpath, node) addresses whose handles are shown."""
        subpaths = {si for l, si, _n in self.doc.selected_nodes if l == li}
        result = set()
        for si in subpaths:
            nodes, _closed = vector_path.to_nodes(self._layer_subpaths(li)[si])
            result.update((si, ni) for ni in range(len(nodes)))
        return result

    def _hit_nodes(self, local):
        """Hit-test anchors / handles / segments on editable layers."""
        tolerance = PICK_PX * self._px()
        for li in self._editable_layers_front_to_back():
            hit = vector_path.hit_test(
                self._layer_subpaths(li),
                local[0],
                local[1],
                tolerance,
                handle_nodes=self._handle_nodes(li),
            )
            if hit:
                hit["layer"] = li
                return hit
        return None

    def _hit_subpath(self, local):
        """Return the front-most ``(layer, subpath)`` under ``local``."""
        tolerance = PICK_PX * self._px()
        point = QtCore.QPointF(local[0], local[1])
        for li in self._editable_layers_front_to_back():
            subpaths = self._layer_subpaths(li)
            for si in reversed(range(len(subpaths))):
                subpath = subpaths[si]
                if vector_path.is_closed(subpath):
                    if build_vector_path([subpath]).contains(point):
                        return (li, si)
                if vector_path.hit_test([subpath], local[0], local[1], tolerance):
                    return (li, si)
        return None

    def selection_bounds(self):
        """Return the local bounds of the targeted subpaths, or None.

        Returns:
            tuple: (x, y, width, height).
        """
        subpaths = [
            self._layer_subpaths(li)[si] for li, si in sorted(self.target_subpaths())
        ]
        box = vector_path.bounds(subpaths)
        if box is None:
            return None
        return (box[0], box[1], box[2] - box[0], box[3] - box[1])

    def _selection_center(self):
        """Return the center of the selection bounds, or None."""
        bounds = self.selection_bounds()
        if bounds is None:
            return None
        return (bounds[0] + bounds[2] / 2.0, bounds[1] + bounds[3] / 2.0)

    # =================================================================
    # MOUSE AND KEYS (called by the view)
    # =================================================================

    def mouse_press(self, event):
        """Handle a mouse press. Returns True when consumed.

        Args:
            event (QtGui.QMouseEvent): The view's mouse event.

        Returns:
            bool: True when the editor handled the event.
        """
        if event.button() != QtCore.Qt.LeftButton:
            return False
        local = self._to_local(event.pos())
        mods = event.modifiers()
        shift = bool(mods & QtCore.Qt.ShiftModifier)
        alt = bool(mods & QtCore.Qt.AltModifier)
        if self.tool == TOOL_NODE:
            self._node_press(local, shift, alt)
        elif self.tool == TOOL_SELECT:
            self._select_press(local, shift)
        elif self.tool == TOOL_PEN:
            self._pen_press(local, shift)
        else:
            point = self._snap(local)
            self._shape_drag = {"start": point, "end": point}
        self.view.viewport().update()
        return True

    def mouse_move(self, event):
        """Handle a mouse move. Returns True when consumed.

        Only repaints when something visible changed: a drag, a marquee, a
        tool preview, or the hovered element.

        Args:
            event (QtGui.QMouseEvent): The view's mouse event.

        Returns:
            bool: True when the editor handled the event.
        """
        if event.buttons() & (QtCore.Qt.MiddleButton | QtCore.Qt.RightButton):
            return False
        # Pan / zoom resets the viewport cursor; put the tool pointer back.
        viewport = self.view.viewport()
        if viewport.cursor().shape() != QtCore.Qt.BitmapCursor:
            viewport.setCursor(tool_cursor(self.tool))
        local = self._to_local(event.pos())
        shift = bool(event.modifiers() & QtCore.Qt.ShiftModifier)
        self._cursor = local
        repaint = True
        if self._marquee is not None:
            self._marquee["end"] = local
        elif self._drag is not None:
            self._drag_move(local, shift)
        elif self._pen_dragging:
            self._pen_drag(local)
        elif self._shape_drag is not None:
            self._shape_drag["end"] = self._snap(local)
            self._shape_drag["shift"] = shift
        elif self.tool == TOOL_NODE:
            hover = self._hit_nodes(local)
            repaint = _hover_key(hover) != _hover_key(self._hover)
            self._hover = hover
        else:
            repaint = bool(self._pen_nodes)
        if repaint:
            self.view.viewport().update()
        return True

    def mouse_release(self, event):
        """Handle a mouse release. Returns True when consumed.

        Args:
            event (QtGui.QMouseEvent): The view's mouse event.

        Returns:
            bool: True when the editor handled the event.
        """
        if event.button() != QtCore.Qt.LeftButton:
            return False
        if self._marquee is not None:
            self._finish_marquee()
        elif self._drag is not None:
            before = self._drag["before"]
            moved = self._drag.get("moved")
            self._drag = None
            if moved:
                self._push(before)
        elif self._pen_dragging:
            self._pen_dragging = False
        elif self._shape_drag is not None:
            self._finish_shape()
        self.view.viewport().update()
        return True

    def mouse_double_click(self, event):
        """Finish the Pen path on double-click; swallow other double-clicks."""
        if self.tool == TOOL_PEN:
            self._finish_pen(False)
        return True

    def key_press(self, event):
        """Handle a key press. Returns True when consumed.

        Args:
            event (QtGui.QKeyEvent): The view's key event.

        Returns:
            bool: True when the editor handled the event.
        """
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & QtCore.Qt.ControlModifier)
        shift = bool(mods & QtCore.Qt.ShiftModifier)
        if ctrl and key == QtCore.Qt.Key_Z:
            self.redo() if shift else self.undo()
            return True
        if ctrl and key == QtCore.Qt.Key_Y:
            self.redo()
            return True
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self._pen_nodes:
                self._finish_pen(False)
            else:
                self.done()
            return True
        if key == QtCore.Qt.Key_Escape:
            if self._pen_nodes:
                self._finish_pen(False)
            else:
                self.doc.clear_selection()
                self.changed.emit()
            self.view.viewport().update()
            return True
        if key in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            self.delete_selection()
            return True
        arrows = {
            QtCore.Qt.Key_Left: (-1.0, 0.0),
            QtCore.Qt.Key_Right: (1.0, 0.0),
            QtCore.Qt.Key_Up: (0.0, 1.0),
            QtCore.Qt.Key_Down: (0.0, -1.0),
        }
        if key in arrows:
            step = 10.0 if shift else 1.0
            dx, dy = arrows[key]
            self.nudge(dx * step, dy * step)
            return True
        if not ctrl and not mods & QtCore.Qt.AltModifier:
            shortcuts = {
                QtCore.Qt.Key_V: TOOL_SELECT,
                QtCore.Qt.Key_A: TOOL_NODE,
                QtCore.Qt.Key_P: TOOL_PEN,
                QtCore.Qt.Key_R: TOOL_RECT,
                QtCore.Qt.Key_E: TOOL_ELLIPSE,
                QtCore.Qt.Key_Y: TOOL_POLYGON,
                QtCore.Qt.Key_L: TOOL_LINE,
            }
            if key in shortcuts:
                self.set_tool(shortcuts[key])
                return True
        # Swallow everything else so picker shortcuts never act mid-session.
        return True

    # =================================================================
    # NODE TOOL
    # =================================================================

    def _node_press(self, local, shift, alt):
        hit = self._hit_nodes(local)
        before = self.doc.snapshot()
        if hit is None:
            if not shift:
                self.doc.clear_selection()
            self._marquee = {"start": local, "end": local, "shift": shift}
            self.changed.emit()
            return
        li = hit["layer"]
        si = hit["subpath"]
        subpaths = self._layer_subpaths(li)

        if hit["kind"] == "handle":
            node = vector_path.get_node(subpaths, (si, hit["node"]))
            constraint = None if alt else vector_path.node_type(node)
            self._drag = {
                "mode": "handle",
                "before": before,
                "layer": li,
                "address": (si, hit["node"]),
                "which": hit["which"],
                "constraint": constraint,
                "orig": before["layers"][li]["subpaths"],
            }
            return

        if hit["kind"] == "segment":
            if alt:
                self._edit(lambda: self._insert_at(li, si, hit["segment"], hit["t"]))
                return
            nodes, _closed = vector_path.to_nodes(subpaths[si])
            ends = {
                (li, si, hit["segment"]),
                (li, si, (hit["segment"] + 1) % len(nodes)),
            }
            if not shift:
                self.doc.selected_nodes = set()
            self.doc.selected_nodes |= ends
            self.doc.selected_subpaths = set()
            self._begin_anchor_drag(before, local, (li, si, hit["segment"]))
            self.changed.emit()
            return

        key = (li, si, hit["node"])
        node = vector_path.get_node(subpaths, (si, hit["node"]))
        if alt and node["in"] is None and node["out"] is None:
            self.doc.selected_nodes = {key}
            self._drag = {
                "mode": "pull",
                "before": before,
                "layer": li,
                "address": (si, hit["node"]),
                "orig": before["layers"][li]["subpaths"],
            }
            self.changed.emit()
            return
        if shift:
            self.doc.selected_nodes ^= {key}
        elif key not in self.doc.selected_nodes:
            self.doc.selected_nodes = {key}
        self.doc.selected_subpaths = set()
        if key in self.doc.selected_nodes:
            self._begin_anchor_drag(before, local, key)
        self.changed.emit()

    def _insert_at(self, li, si, segment, t):
        layer = self.doc.layers[li]
        layer["subpaths"] = vector_path.insert_node(layer["subpaths"], si, segment, t)
        self.doc.selected_nodes = {(li, si, segment + 1)}

    def _begin_anchor_drag(self, before, local, primary):
        li, si, ni = primary
        anchor = vector_path.get_node(self._layer_subpaths(li), (si, ni))["anchor"]
        self._drag = {
            "mode": "anchors",
            "before": before,
            "press": local,
            "primary": anchor,
            "orig": _snapshot_subpaths(before),
        }

    def _drag_move(self, local, shift):
        drag = self._drag
        drag["moved"] = True
        mode = drag["mode"]
        if mode == "anchors":
            target = (
                drag["primary"][0] + local[0] - drag["press"][0],
                drag["primary"][1] + local[1] - drag["press"][1],
            )
            target = self._snap(target, exclude=self.doc.selected_nodes)
            dx = target[0] - drag["primary"][0]
            dy = target[1] - drag["primary"][1]
            self._apply_to_nodes(
                lambda subs, addresses: vector_path.move_anchors(
                    subs, addresses, dx, dy
                ),
                drag["orig"],
            )
        elif mode in ("handle", "pull"):
            point = self._snap(local)
            which = drag.get("which", "out")
            constraint = vector_path.SYMMETRIC if mode == "pull" else drag["constraint"]
            self.doc.layers[drag["layer"]]["subpaths"] = vector_path.move_handle(
                drag["orig"], drag["address"], which, point[0], point[1], constraint
            )
        elif mode == "move":
            point = self._snap(local)
            dx = point[0] - drag["press"][0]
            dy = point[1] - drag["press"][1]
            self._apply_to_targets(
                drag["orig"],
                lambda subs, idx: vector_path.translate(subs, dx, dy, idx),
            )
        elif mode == "scale":
            ax, ay, sx, sy = manipulator_transform.scale_factors(
                drag["bounds"], drag["handle"], local[0], local[1], shift
            )
            self._apply_to_targets(
                drag["orig"],
                lambda subs, idx: vector_path.scale(subs, sx, sy, (ax, ay), idx),
            )
        elif mode == "rotate":
            cx, cy = drag["center"]
            degrees = manipulator_transform.rotate_delta(
                cx, cy, drag["press"][0], drag["press"][1], local[0], local[1]
            )
            if shift:
                degrees = round(degrees / 15.0) * 15.0
            self._apply_to_targets(
                drag["orig"],
                lambda subs, idx: vector_path.rotate(subs, degrees, (cx, cy), idx),
            )
        self.apply(live=True)

    def _apply_to_targets(self, source_layers, fn):
        """Apply ``fn(subpaths, indices)`` to the targeted subpaths per layer.

        Args:
            source_layers (list): Per-layer subpath lists to start from.
            fn (callable): Returns the new subpaths for one layer.
        """
        targets = self.target_subpaths()
        for li, subpaths in enumerate(source_layers):
            indices = [si for l, si in targets if l == li]
            if indices:
                self.doc.layers[li]["subpaths"] = fn(subpaths, indices)

    def _apply_to_nodes(self, fn, source_layers=None):
        """Apply ``fn(subpaths, addresses)`` to the selected nodes per layer.

        Args:
            fn (callable): Returns the new subpaths for one layer.
            source_layers (list, optional): Per-layer subpath lists to start
                from; the current layers when None.
        """
        for li, addresses in self._per_layer_nodes().items():
            subpaths = (
                source_layers[li]
                if source_layers is not None
                else self.doc.layers[li]["subpaths"]
            )
            self.doc.layers[li]["subpaths"] = fn(subpaths, addresses)

    def _finish_marquee(self):
        marquee = self._marquee
        self._marquee = None
        x0, x1 = sorted((marquee["start"][0], marquee["end"][0]))
        y0, y1 = sorted((marquee["start"][1], marquee["end"][1]))
        if not marquee["shift"]:
            self.doc.clear_selection()
        for li in self._editable_layers_front_to_back():
            for si, subpath in enumerate(self._layer_subpaths(li)):
                if self.tool == TOOL_SELECT:
                    box = vector_path.bounds([subpath])
                    if (
                        box
                        and box[0] <= x1
                        and box[2] >= x0
                        and box[1] <= y1
                        and box[3] >= y0
                    ):
                        self.doc.selected_subpaths.add((li, si))
                    continue
                nodes, _closed = vector_path.to_nodes(subpath)
                for ni, node in enumerate(nodes):
                    ax, ay = node["anchor"]
                    if x0 <= ax <= x1 and y0 <= ay <= y1:
                        self.doc.selected_nodes.add((li, si, ni))
        self.changed.emit()

    # =================================================================
    # SELECT TOOL
    # =================================================================

    def _box_handle_at(self, local):
        """Return ("scale", handle_id) / ("rotate", None) under ``local``."""
        bounds = self.selection_bounds()
        if bounds is None:
            return None
        px = self._px()
        rx, ry = self._rotate_point(bounds, px)
        if math.hypot(local[0] - rx, local[1] - ry) <= PICK_PX * px:
            return ("rotate", None)
        for handle_id, (hx, hy) in manipulator_transform.handle_points(bounds).items():
            if (
                abs(local[0] - hx) <= PICK_PX * px
                and abs(local[1] - hy) <= PICK_PX * px
            ):
                return ("scale", handle_id)
        return None

    @staticmethod
    def _rotate_point(bounds, px):
        x, y, w, h = bounds
        return (x + w / 2.0, y + h + ROTATE_OFFSET_PX * px)

    def _select_press(self, local, shift):
        before = self.doc.snapshot()
        handle = self._box_handle_at(local)
        if handle is not None:
            self._drag = {
                "mode": handle[0],
                "handle": handle[1],
                "before": before,
                "press": local,
                "bounds": self.selection_bounds(),
                "center": self._selection_center(),
                "orig": _snapshot_subpaths(before),
            }
            return
        hit = self._hit_subpath(local)
        if hit is None:
            self._marquee = {"start": local, "end": local, "shift": shift}
            if not shift:
                self.doc.clear_selection()
            self.changed.emit()
            return
        if shift:
            self.doc.selected_subpaths ^= {hit}
        elif hit not in self.doc.selected_subpaths:
            self.doc.selected_subpaths = {hit}
        self.doc.selected_nodes = set()
        if hit in self.doc.selected_subpaths:
            self._drag = {
                "mode": "move",
                "before": before,
                "press": local,
                "orig": _snapshot_subpaths(before),
            }
        self.changed.emit()

    # =================================================================
    # PEN AND SHAPE TOOLS
    # =================================================================

    def _pen_press(self, local, shift):
        point = self._snap(local)
        if self._pen_nodes:
            if shift:
                point = self._constrain_angle(self._pen_nodes[-1]["anchor"], point)
            first = self._pen_nodes[0]["anchor"]
            if (
                len(self._pen_nodes) >= 2
                and math.hypot(point[0] - first[0], point[1] - first[1])
                <= PICK_PX * self._px()
            ):
                self._finish_pen(True)
                return
        self._pen_nodes.append({"anchor": point, "in": None, "out": None})
        self._pen_dragging = True

    def _pen_drag(self, local):
        node = self._pen_nodes[-1]
        anchor = node["anchor"]
        if (
            math.hypot(local[0] - anchor[0], local[1] - anchor[1])
            < PICK_PX * self._px() / 2
        ):
            node["in"] = node["out"] = None
            return
        node["out"] = local
        node["in"] = (2.0 * anchor[0] - local[0], 2.0 * anchor[1] - local[1])

    def _finish_pen(self, closed, discard=False):
        nodes = self._pen_nodes
        self._pen_nodes = []
        self._pen_dragging = False
        if discard or len(nodes) < 2 or self.doc is None:
            self.view.viewport().update()
            return
        subpath = vector_path.from_nodes(nodes, closed)
        self._add_subpaths(self._arrow_pieces(subpath))

    def _add_subpaths(self, subpaths):
        """Add drawn subpaths to the current layer and select them."""

        def add():
            li = self._drawable_layer()
            layer = self.doc.layers[li]
            start = len(layer["subpaths"])
            layer["subpaths"].extend(subpaths)
            self.doc.selected_nodes = set()
            self.doc.selected_subpaths = {
                (li, index) for index in range(start, len(layer["subpaths"]))
            }

        self._edit(add)

    def _arrow_pieces(self, subpath):
        """Return ``subpath`` with the enabled arrowheads drawn into it.

        Args:
            subpath (list): Segments of one subpath.

        Returns:
            list: One subpath (arrows are part of its own path).
        """
        return [
            vector_path.add_arrows(
                subpath, self.arrow_start, self.arrow_end, self.arrow_size
            )
        ]

    def _drawable_layer(self):
        """Return the current layer, making it visible and unlocked."""
        li = self.doc.current
        layer = self.doc.layers[li]
        layer["visible"] = True
        layer["locked"] = False
        return li

    def _finish_shape(self):
        pieces = self._shape_pieces(self._shape_drag)
        self._shape_drag = None
        if pieces:
            self._add_subpaths(pieces)

    def _shape_pieces(self, drag):
        """Return the subpaths a shape-tool drag creates (line + arrows)."""
        subpath = self._build_shape_subpath(drag)
        if not subpath:
            return []
        if self.tool == TOOL_LINE:
            return self._arrow_pieces(subpath)
        return [subpath]

    def _build_shape_subpath(self, drag):
        """Return the subpath a shape-tool drag describes, or None if tiny.

        Args:
            drag (dict): ``{"start", "end", "shift"}`` in local coordinates.

        Returns:
            list: Segments of one subpath, or None.
        """
        if drag is None:
            return None
        start = drag["start"]
        end = drag["end"]
        shift = drag.get("shift", False)
        min_size = PICK_PX * self._px() / 2.0
        w = end[0] - start[0]
        h = end[1] - start[1]
        if self.tool in (TOOL_RECT, TOOL_ELLIPSE) and shift:
            size = max(abs(w), abs(h))
            w = math.copysign(size, w or 1.0)
            h = math.copysign(size, h or 1.0)
        if self.tool == TOOL_LINE:
            if shift:
                end = self._constrain_angle(start, end)
            if math.hypot(end[0] - start[0], end[1] - start[1]) < min_size:
                return None
            return vector_path.line(start[0], start[1], end[0], end[1])
        if self.tool == TOOL_POLYGON:
            radius = math.hypot(w, h)
            if radius < min_size:
                return None
            angle = math.degrees(math.atan2(h, w))
            if shift:
                angle = round(angle / 15.0) * 15.0
            if self.star_inner_ratio > 0.0:
                return vector_path.star(
                    start[0],
                    start[1],
                    radius,
                    self.polygon_sides,
                    self.star_inner_ratio,
                    angle,
                )
            return vector_path.regular_polygon(
                start[0], start[1], radius, self.polygon_sides, angle
            )
        if abs(w) < min_size or abs(h) < min_size:
            return None
        if self.tool == TOOL_RECT:
            return vector_path.rectangle(start[0], start[1], w, h, self.corner_radius)
        return vector_path.ellipse(
            start[0] + w / 2.0, start[1] + h / 2.0, abs(w) / 2.0, abs(h) / 2.0
        )

    # =================================================================
    # NODE OPERATIONS
    # =================================================================

    def _per_layer_nodes(self):
        by_layer = {}
        for li, si, ni in self.doc.selected_nodes:
            by_layer.setdefault(li, []).append((si, ni))
        return by_layer

    def has_node_selection(self):
        """Return True when nodes are selected."""
        return self.is_active() and bool(self.doc.selected_nodes)

    def has_subpath_selection(self):
        """Return True when the selection covers any subpath."""
        return self.is_active() and bool(self.target_subpaths())

    def add_nodes(self):
        """Insert a node in the middle of each segment between selected nodes."""

        def run():
            new_selection = set()
            for li, addresses in self._per_layer_nodes().items():
                selected = set(addresses)
                subpaths = self._layer_subpaths(li)
                for si in sorted({s for s, _n in addresses}, reverse=True):
                    nodes, closed = vector_path.to_nodes(subpaths[si])
                    count = len(nodes)
                    segments = [
                        i
                        for i, *_rest in vector_path.iter_segments(nodes, closed)
                        if (si, i) in selected and (si, (i + 1) % count) in selected
                    ]
                    for segment in sorted(segments, reverse=True):
                        subpaths = vector_path.insert_node(subpaths, si, segment, 0.5)
                        new_selection.add((li, si, segment + 1))
                self.doc.layers[li]["subpaths"] = subpaths
            self.doc.selected_nodes = new_selection

        self._edit(run)

    def delete_selection(self):
        """Delete the selected nodes, or the selected subpaths."""
        if not self.is_active():
            return
        if self.doc.selected_nodes:

            def run():
                self._apply_to_nodes(vector_path.delete_nodes)
                self.doc.clear_selection()

            self._edit(run)
        elif self.doc.selected_subpaths:

            def run():
                for li, si in sorted(self.doc.selected_subpaths, reverse=True):
                    del self.doc.layers[li]["subpaths"][si]
                self.doc.clear_selection()

            self._edit(run)

    def set_node_type(self, kind):
        """Convert the selected nodes to corner, smooth, or symmetric.

        Args:
            kind (str): ``vector_path.CORNER`` / ``SMOOTH`` / ``SYMMETRIC``.
        """

        def convert(subpaths, addresses):
            for address in addresses:
                subpaths = vector_path.set_node_type(subpaths, address, kind)
            return subpaths

        self._edit(lambda: self._apply_to_nodes(convert))

    def break_nodes(self):
        """Break paths at the selected nodes."""

        def run():
            for li, addresses in self._per_layer_nodes().items():
                layer = self.doc.layers[li]
                done_closed = set()
                for si, ni in sorted(addresses, reverse=True):
                    if si in done_closed:
                        continue
                    if vector_path.is_closed(layer["subpaths"][si]):
                        done_closed.add(si)
                    layer["subpaths"] = vector_path.split_at(
                        layer["subpaths"], (si, ni)
                    )
            self.doc.clear_selection()

        self._edit(run)

    def can_join(self):
        """Return True when exactly two endpoints on one layer are selected."""
        if not self.is_active() or len(self.doc.selected_nodes) != 2:
            return False
        (la, sa, na), (lb, sb, nb) = sorted(self.doc.selected_nodes)
        if la != lb:
            return False
        subpaths = self._layer_subpaths(la)
        return vector_path.is_endpoint(subpaths, (sa, na)) and vector_path.is_endpoint(
            subpaths, (sb, nb)
        )

    def join_nodes(self):
        """Join the two selected endpoints."""
        if not self.can_join():
            return
        (li, sa, na), (_lb, sb, nb) = sorted(self.doc.selected_nodes)

        def run():
            layer = self.doc.layers[li]
            layer["subpaths"] = vector_path.join(layer["subpaths"], (sa, na), (sb, nb))
            self.doc.clear_selection()

        self._edit(run)

    def toggle_closed(self):
        """Close open targeted subpaths, or open closed ones."""

        def run():
            for li, si in self.target_subpaths():
                layer = self.doc.layers[li]
                if vector_path.is_closed(layer["subpaths"][si]):
                    layer["subpaths"] = vector_path.open_subpath(layer["subpaths"], si)
                else:
                    layer["subpaths"] = vector_path.close_subpath(layer["subpaths"], si)
            self.doc.selected_nodes = set()

        self._edit(run)

    def reverse_paths(self):
        """Reverse the direction of the targeted subpaths."""

        def run():
            for li, si in self.target_subpaths():
                layer = self.doc.layers[li]
                layer["subpaths"] = vector_path.reverse_subpath(layer["subpaths"], si)
            self.doc.selected_nodes = set()

        self._edit(run)

    def nudge(self, dx, dy):
        """Move the selected nodes, or the selected subpaths, by (dx, dy)."""
        if not self.is_active() or not self.target_subpaths():
            return

        def run():
            if self.doc.selected_nodes:
                self._apply_to_nodes(
                    lambda subs, addresses: vector_path.move_anchors(
                        subs, addresses, dx, dy
                    )
                )
            else:
                self._apply_to_targets(
                    [layer["subpaths"] for layer in self.doc.layers],
                    lambda subs, idx: vector_path.translate(subs, dx, dy, idx),
                )

        self._edit(run)

    # =================================================================
    # PATH OPERATIONS
    # =================================================================

    def can_boolean(self):
        """Return True when two or more subpaths are targeted."""
        return self.is_active() and len(self.target_subpaths()) >= 2

    def boolean(self, operation):
        """Combine the targeted subpaths with a boolean operation.

        The result replaces its inputs on the bottom-most input's layer, at
        the bottom-most input's position.

        Args:
            operation (str): ``BOOL_UNION`` / ``BOOL_SUBTRACT`` /
                ``BOOL_INTERSECT`` / ``BOOL_EXCLUDE``.
        """
        if not self.can_boolean():
            return
        targets = sorted(self.target_subpaths())
        paths = []
        for li, si in targets:
            path = build_vector_path([self._layer_subpaths(li)[si]])
            path.setFillRule(QtCore.Qt.WindingFill)
            paths.append(path)

        if operation == BOOL_SUBTRACT:
            result = paths[0]
            for path in paths[1:-1]:
                result = result.united(path)
            result = result.subtracted(paths[-1])
        else:
            result = paths[0]
            for path in paths[1:]:
                if operation == BOOL_UNION:
                    result = result.united(path)
                elif operation == BOOL_INTERSECT:
                    result = result.intersected(path)
                else:
                    result = result.united(path).subtracted(result.intersected(path))
        new_subpaths = path_to_subpaths(result.simplified())
        bottom_layer, bottom_index = targets[0]

        def run():
            for li, si in reversed(targets):
                del self.doc.layers[li]["subpaths"][si]
            removed_before = len(
                [1 for li, si in targets if li == bottom_layer and si < bottom_index]
            )
            insert_at = bottom_index - removed_before
            layer = self.doc.layers[bottom_layer]
            layer["subpaths"][insert_at:insert_at] = new_subpaths
            self.doc.clear_selection()
            self.doc.selected_subpaths = {
                (bottom_layer, insert_at + i) for i in range(len(new_subpaths))
            }

        self._edit(run)

    def flip(self, horizontal=True):
        """Mirror the targeted subpaths about their bounds center.

        Args:
            horizontal (bool, optional): Left-right when True, else
                top-bottom.
        """
        center = self._selection_center()
        if center is None:
            return
        self._edit(
            lambda: self._apply_to_targets(
                [layer["subpaths"] for layer in self.doc.layers],
                lambda subs, idx: vector_path.flip(subs, horizontal, center, idx),
            )
        )

    def duplicate(self):
        """Duplicate the targeted subpaths in place and select the copies."""
        targets = sorted(self.target_subpaths())
        if not targets:
            return

        def run():
            selection = set()
            for li, si in targets:
                layer = self.doc.layers[li]
                layer["subpaths"].append(list(layer["subpaths"][si]))
                selection.add((li, len(layer["subpaths"]) - 1))
            self.doc.clear_selection()
            self.doc.selected_subpaths = selection

        self._edit(run)

    # =================================================================
    # PRECISION
    # =================================================================

    def selection_position(self):
        """Return the selected node's position, or the selection center.

        Returns:
            tuple: (x, y), or None when nothing is selected.
        """
        if not self.is_active():
            return None
        if len(self.doc.selected_nodes) == 1:
            li, si, ni = next(iter(self.doc.selected_nodes))
            return vector_path.get_node(self._layer_subpaths(li), (si, ni))["anchor"]
        return self._selection_center()

    def set_selection_position(self, x=None, y=None):
        """Move the selection so its position becomes (x, y).

        Args:
            x (float, optional): New x; unchanged when None.
            y (float, optional): New y; unchanged when None.
        """
        current = self.selection_position()
        if current is None:
            return
        dx = 0.0 if x is None else x - current[0]
        dy = 0.0 if y is None else y - current[1]
        if dx or dy:
            self.nudge(dx, dy)

    # =================================================================
    # LAYERS
    # =================================================================

    def set_current_layer(self, index):
        """Make ``index`` the layer new drawings go onto.

        Args:
            index (int): Layer index.
        """
        if self.is_active() and 0 <= index < len(self.doc.layers):
            self.doc.current = index
            self.changed.emit()

    def add_layer(self):
        """Add an empty layer in front of the current one and make it current."""

        def run():
            names = {layer["name"] for layer in self.doc.layers}
            number = len(self.doc.layers) + 1
            while "Layer {}".format(number) in names:
                number += 1
            index = self.doc.current + 1
            self.doc.layers.insert(
                index, vector_model.new_layer("Layer {}".format(number))
            )
            self.doc.current = index
            self.doc.clear_selection()

        self._edit(run)

    def delete_layer(self, index):
        """Delete a layer; the last remaining layer cannot be deleted.

        Args:
            index (int): Layer index.
        """
        if len(self.doc.layers) <= 1:
            return

        def run():
            del self.doc.layers[index]
            self.doc.current = max(0, min(self.doc.current, len(self.doc.layers) - 1))
            self.doc.clear_selection()

        self._edit(run)

    def duplicate_layer(self, index):
        """Duplicate a layer in front of itself.

        Args:
            index (int): Layer index.
        """

        def run():
            copy_layer = copy.deepcopy(self.doc.layers[index])
            copy_layer["name"] = "{} copy".format(copy_layer["name"])
            self.doc.layers.insert(index + 1, copy_layer)
            self.doc.current = index + 1
            self.doc.clear_selection()

        self._edit(run)

    def move_layer(self, index, delta):
        """Move a layer forward (positive delta) or backward in draw order.

        Args:
            index (int): Layer index.
            delta (int): Positions to move.
        """
        target = index + delta
        if not 0 <= target < len(self.doc.layers):
            return

        def run():
            layer = self.doc.layers.pop(index)
            self.doc.layers.insert(target, layer)
            self.doc.current = target
            self.doc.clear_selection()

        self._edit(run)

    def merge_down(self, index):
        """Move a layer's subpaths into the layer below and delete it.

        Args:
            index (int): Layer index (must not be the bottom layer).
        """
        if index <= 0:
            return

        def run():
            layer = self.doc.layers.pop(index)
            self.doc.layers[index - 1]["subpaths"].extend(layer["subpaths"])
            self.doc.current = index - 1
            self.doc.clear_selection()

        self._edit(run)

    def set_layer_property(self, index, key, value):
        """Set a layer property (name, visible, locked, mode, stroke_width, color).

        Args:
            index (int): Layer index.
            key (str): Property name.
            value (object): New value.
        """
        if self.doc.layers[index].get(key) == value:
            return

        def run():
            self.doc.layers[index][key] = value
            if key in ("visible", "locked") and not self.doc.editable(index):
                self.doc.selected_subpaths = {
                    p for p in self.doc.selected_subpaths if p[0] != index
                }
                self.doc.selected_nodes = {
                    n for n in self.doc.selected_nodes if n[0] != index
                }

        self._edit(run)

    def move_selection_to_layer(self, index):
        """Move the targeted subpaths to another layer.

        Args:
            index (int): Destination layer index.
        """
        targets = sorted(self.target_subpaths())
        if not targets:
            return

        def run():
            moved = []
            for li, si in reversed(targets):
                if li == index:
                    continue
                moved.insert(0, self.doc.layers[li]["subpaths"].pop(si))
            destination = self.doc.layers[index]
            start = len(destination["subpaths"])
            destination["subpaths"].extend(moved)
            self.doc.clear_selection()
            self.doc.selected_subpaths = {(index, start + i) for i in range(len(moved))}
            self.doc.current = index

        self._edit(run)

    # =================================================================
    # PAINTING (called from the view's drawForeground)
    # =================================================================

    def paint(self, painter):
        """Draw the editing overlay in scene coordinates.

        Args:
            painter (QtGui.QPainter): The view's foreground painter.
        """
        if not self.is_active():
            return
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        # Computed once per repaint and shared by every marker.
        self._paint_scene_px = self._scene_px()
        px = self._px()
        if self.show_grid:
            self._paint_grid(painter, px)
        self._paint_outlines(painter)
        if self.tool == TOOL_SELECT:
            self._paint_box(painter, px)
        elif self.tool == TOOL_NODE:
            self._paint_nodes(painter)
        self._paint_hover(painter)
        self._paint_pen(painter)
        preview = self._shape_pieces(self._shape_drag)
        if preview:
            self._stroke_local_path(painter, preview, _PREVIEW_COLOR, 1.5)
        self._paint_marquee(painter)
        painter.restore()

    @staticmethod
    def _set_pen(painter, color, width=1.0, style=QtCore.Qt.SolidLine):
        """Set a cosmetic (constant screen width) pen."""
        pen = QtGui.QPen(color)
        pen.setWidthF(width)
        pen.setCosmetic(True)
        pen.setStyle(style)
        painter.setPen(pen)

    def _stroke_local_path(self, painter, subpaths, color, width=1.0):
        """Stroke item-local subpaths through the item's scene transform."""
        painter.save()
        painter.setWorldTransform(self.item.sceneTransform(), True)
        self._set_pen(painter, color, width)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawPath(build_vector_path(subpaths))
        painter.restore()

    def _paint_outlines(self, painter):
        targets = self.target_subpaths()
        for li, layer in enumerate(self.doc.layers):
            if not layer["visible"]:
                continue
            color = QtGui.QColor(_OUTLINE_COLOR)
            if layer["locked"]:
                color.setAlpha(80)
            self._stroke_local_path(painter, layer["subpaths"], color)
            selected = [
                sub for si, sub in enumerate(layer["subpaths"]) if (li, si) in targets
            ]
            if selected:
                self._stroke_local_path(painter, selected, _SELECTED_COLOR, 2.0)

    def _paint_marker(self, painter, point, size, square, fill, border):
        center = self._to_scene(point)
        scene_size = size * self._paint_scene_px
        rect = QtCore.QRectF(
            center.x() - scene_size,
            center.y() - scene_size,
            scene_size * 2,
            scene_size * 2,
        )
        self._set_pen(painter, border)
        painter.setBrush(QtGui.QBrush(fill))
        if square:
            painter.drawRect(rect)
        else:
            painter.drawEllipse(rect)

    def _paint_handle(self, painter, anchor, handle):
        """Draw a curve handle: a line from its anchor and a dot."""
        self._set_pen(painter, _HANDLE_COLOR)
        painter.drawLine(self._to_scene(anchor), self._to_scene(handle))
        self._paint_marker(
            painter, handle, HANDLE_PX, False, _HANDLE_COLOR, _HANDLE_COLOR
        )

    def _paint_nodes(self, painter):
        for li in range(len(self.doc.layers)):
            if not self.doc.editable(li):
                continue
            handle_nodes = self._handle_nodes(li)
            for si, subpath in enumerate(self._layer_subpaths(li)):
                nodes, closed = vector_path.to_nodes(subpath)
                for ni, _which, handle in vector_path.visible_handles(nodes, closed):
                    if (si, ni) in handle_nodes:
                        self._paint_handle(painter, nodes[ni]["anchor"], handle)
                for ni, node in enumerate(nodes):
                    selected = (li, si, ni) in self.doc.selected_nodes
                    square = vector_path.node_type(node) == vector_path.CORNER
                    self._paint_marker(
                        painter,
                        node["anchor"],
                        ANCHOR_PX,
                        square,
                        _SELECTED_COLOR if selected else _ANCHOR_FILL,
                        _SELECTED_COLOR,
                    )

    def _paint_hover(self, painter):
        hover = self._hover
        if not hover or self._drag is not None or self.tool != TOOL_NODE:
            return
        if hover["layer"] >= len(self.doc.layers):
            return
        subpaths = self._layer_subpaths(hover["layer"])
        if hover["subpath"] >= len(subpaths):
            return
        if hover["kind"] == "segment":
            self._stroke_local_path(
                painter, [subpaths[hover["subpath"]]], _HOVER_COLOR, 2.0
            )
        elif hover["kind"] == "anchor":
            nodes, _closed = vector_path.to_nodes(subpaths[hover["subpath"]])
            if hover["node"] < len(nodes):
                self._paint_marker(
                    painter,
                    nodes[hover["node"]]["anchor"],
                    ANCHOR_PX + 1.5,
                    False,
                    QtGui.QColor(0, 0, 0, 0),
                    _HOVER_COLOR,
                )

    def _paint_box(self, painter, px):
        bounds = self.selection_bounds()
        if bounds is None:
            return
        x, y, w, h = bounds
        corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        polygon = QtGui.QPolygonF([self._to_scene(c) for c in corners])
        self._set_pen(painter, _SELECTED_COLOR, style=QtCore.Qt.DashLine)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawPolygon(polygon)
        self._set_pen(painter, _SELECTED_COLOR)
        rx, ry = self._rotate_point(bounds, px)
        painter.drawLine(self._to_scene((x + w / 2.0, y + h)), self._to_scene((rx, ry)))
        self._paint_marker(
            painter, (rx, ry), BOX_HANDLE_PX, False, _ANCHOR_FILL, _SELECTED_COLOR
        )
        for point in manipulator_transform.handle_points(bounds).values():
            self._paint_marker(
                painter, point, BOX_HANDLE_PX, True, _ANCHOR_FILL, _SELECTED_COLOR
            )

    def _paint_pen(self, painter):
        if not self._pen_nodes:
            return
        nodes = vector_path.copy_nodes(self._pen_nodes)
        if self._cursor is not None and not self._pen_dragging:
            nodes.append({"anchor": self._cursor, "in": None, "out": None})
        self._stroke_local_path(
            painter, [vector_path.from_nodes(nodes, False)], _PREVIEW_COLOR, 1.5
        )
        last = self._pen_nodes[-1]
        for which in ("in", "out"):
            if last[which] is not None:
                self._paint_handle(painter, last["anchor"], last[which])
        for index, node in enumerate(self._pen_nodes):
            self._paint_marker(
                painter,
                node["anchor"],
                ANCHOR_PX + (1.5 if index == 0 else 0.0),
                True,
                _ANCHOR_FILL,
                _PREVIEW_COLOR,
            )

    def _paint_marquee(self, painter):
        if self._marquee is None:
            return
        (x0, y0), (x1, y1) = self._marquee["start"], self._marquee["end"]
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self._set_pen(painter, _SELECTED_COLOR, style=QtCore.Qt.DashLine)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 150, 255, 30)))
        painter.drawPolygon(QtGui.QPolygonF([self._to_scene(c) for c in corners]))

    def _paint_grid(self, painter, px):
        size = self.grid_size
        if size <= 0 or size / px < MIN_GRID_PX:
            return
        viewport = self.view.viewport().rect()
        corners = [
            self._to_local(point)
            for point in (
                viewport.topLeft(),
                viewport.topRight(),
                viewport.bottomLeft(),
                viewport.bottomRight(),
            )
        ]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        self._set_pen(painter, _GRID_COLOR)
        x = math.floor(min(xs) / size) * size
        while x <= max(xs):
            painter.drawLine(self._to_scene((x, min(ys))), self._to_scene((x, max(ys))))
            x += size
        y = math.floor(min(ys) / size) * size
        while y <= max(ys):
            painter.drawLine(self._to_scene((min(xs), y)), self._to_scene((max(xs), y)))
            y += size
