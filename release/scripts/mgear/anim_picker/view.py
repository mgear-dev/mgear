"""Graphics view widget (picker canvas) for the anim picker.

Extracted from gui.py during the Phase 2 decomposition.
"""

import os
import copy
import json
import uuid
from functools import partial

from maya import cmds
import mgear.pymaya as pm

import mgear
from mgear.core import attribute
from mgear.core import string
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.scene import OrderedGraphicsScene
from mgear.anim_picker.constants import MAYA_OVERRIDE_COLOR
from mgear.anim_picker.constants import PICKER_EXTRACTION_NAME
from mgear.anim_picker.constants import ANIM_PICKER_RELATIVE_IMAGES
from mgear.anim_picker.constants import DEFAULT_RELATIVE_IMAGES_PATH
from mgear.anim_picker.widgets import basic
from mgear.anim_picker.widgets import picker_widgets
from mgear.anim_picker.widgets import background_model
from mgear.anim_picker.widgets import background_manipulator
from mgear.anim_picker.widgets import item_manipulator
from mgear.anim_picker.widgets import edit_undo
from mgear.anim_picker.widgets import shape_library
from mgear.anim_picker.widgets import tool_bar
from mgear.anim_picker.widgets import mirror
from mgear.anim_picker.widgets import overlay
from mgear.anim_picker.widgets import silhouette
from mgear.anim_picker.widgets import widget_binding
from mgear.core import svg_import
from mgear.anim_picker.handlers import __EDIT_MODE__
from mgear.anim_picker.handlers import maya_handlers


def _united_scene_rect(items):
    """Return the union of ``items`` scene bounding rects (None when empty)."""
    union = None
    for item in items:
        rect = item.sceneBoundingRect()
        union = rect if union is None else union.united(rect)
    return union


class _LoadedBackground(object):
    """View-side pairing of a ``BackgroundLayer`` model with its loaded image.

    The ``BackgroundLayer`` is the serialization authority (Qt/Maya-free); the
    ``QImage`` is runtime-only state, decoded once and reused on every repaint.
    """

    def __init__(self, layer, image):
        self.layer = layer
        self.image = image
        # Cached geometry, refreshed on layer mutation (never per paint).
        self.rect = None
        self.src_rect = None


# module clipboard shared across views (copy/paste of picker items)
_CLIPBOARD = []


class GraphicViewWidget(QtWidgets.QGraphicsView):
    """Graphic view widget that display the "polygons" picker items"""

    __DEFAULT_SCENE_WIDTH__ = 6000
    __DEFAULT_SCENE_HEIGHT__ = 6000

    def __init__(self, namespace=None, main_window=None):
        QtWidgets.QGraphicsView.__init__(self)

        self.setScene(OrderedGraphicsScene(parent=self))

        self.namespace = namespace
        self.main_window = main_window
        self.setParent(self.main_window)

        # Scale view in Y for positive Y values (maya-like)
        self.scale(1, -1)

        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)

        # Set selection mode
        self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemBoundingRect)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.scene_mouse_origin = QtCore.QPointF()
        self.drag_active = False
        self.pan_active = False
        self.zoom_active = False
        # True while a wheel-zoom step runs, so the passthrough mask is
        # suspended (full UI back) like a drag instead of reshaped per step.
        self._wheel_zooming = False
        self.auto_frame_active = True

        # Disable scroll bars
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Accept drops from the left tool-strip palette (drag an item / widget
        # tile onto the canvas to create it at the drop position, edit mode).
        self.setAcceptDrops(True)

        # Set background color
        brush = QtGui.QBrush(QtGui.QColor(70, 70, 70, 255))
        self.setBackgroundBrush(brush)
        # Ordered list of _LoadedBackground (back-to-front). Replaces the former
        # single background_image / background_image_path state.
        self.background_layers = []
        # Cached union rect of all layers, refreshed on mutation.
        self._bounding_rect = None
        self.bg_ui = None

        # On-canvas background layer manipulation (active with the panel open).
        self.background_edit = False
        self.bg_manipulator = background_manipulator.BackgroundManipulator(self)
        self._bg_dragging = False
        self._bg_marquee_origin = None
        self._bg_marquee_current = None

        # On-canvas picker item scale/rotate manipulator (edit mode only).
        self.item_manipulator = item_manipulator.ItemManipulator(self)
        self._item_dragging = False

        # Persistent mirror relationships: the symmetry axis (scene x), a
        # guard that breaks the A -> B -> A live-mirror feedback loop, and a
        # cached "any pair linked?" flag so the per-frame paint / per-edit
        # propagation short-circuit when nothing is linked (the common case).
        self.mirror_axis_x = 0.0
        self._mirroring = False
        self._has_mirror_links = False

        # Viewport-pinned (HUD overlay) items: a cached "any pinned?" flag so
        # the reposition on every pan / zoom / resize short-circuits when
        # nothing is pinned (the common case).
        self._has_pinned_items = False

        # Conditional-visibility items: a cached "any condition?" flag so the
        # per-item show/hide evaluation on zoom / selection / time is skipped
        # when no item carries a visibility condition (the common case).
        self._has_conditional_items = False

        # Group controllers: a cached "any checkbox controls a group?" flag so
        # the group show/hide pass is skipped when no controller exists.
        self._has_group_controllers = False

        self.fit_margin = 8

        # Editor undo: one snapshot-based stack that every edit records to. A
        # snapshot is the item serialization (get_data / set_data) + z-order;
        # item identity is the per-item uuid, preserved when an item is
        # recreated so add / delete round-trip. ``_undo_baseline`` is the last
        # committed state, so each edit's "before" is implicit -- a gesture
        # (drag / manipulator) commits once at release for a single step.
        self._undo_stack = edit_undo.UndoStack()
        self._undo_baseline = None

        # Keep keyboard focus on the canvas so edit shortcuts / undo get key
        # events (an item click would otherwise not focus the view widget).
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def get_center_pos(self):
        return self.mapToScene(
            QtCore.QPoint(self.width() / 2, self.height() / 2)
        )

    def mousePressEvent(self, event):
        # Keep keyboard focus on the canvas in edit mode so the edit shortcuts
        # and undo receive key events after any click (a plain item click would
        # otherwise leave focus elsewhere and the shortcuts would not fire).
        if __EDIT_MODE__.get():
            self.setFocus()
        # Background layer manipulation intercepts left-click when active.
        if self.background_edit and self._bg_mouse_press(event):
            return
        # Item scale/rotate handle press intercepts left-click in edit mode.
        if self._item_mouse_press(event):
            return
        self.modified_select = False
        self.item_selected = False
        self.__move_prompt = False
        # Select the clicked item on press (edit mode), before the default
        # handler sets up the item drag -- so a single click selects and can
        # move in the same motion, and the drag moves the right set. Returns
        # True when the selection is finalized here (release should not re-run
        # it); modified_select carries that, matching its existing meaning.
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and __EDIT_MODE__.get()
        ):
            transform = self.viewportTransform()
            scene_pos = self.mapToScene(event.pos())
            picker_at = self.scene().picker_at(scene_pos, transform)
            picker_at = self._resolve_backdrop_pick(picker_at, scene_pos)
            if picker_at and self._select_on_press(picker_at, event):
                self.modified_select = True
        QtWidgets.QGraphicsView.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.scene_mouse_origin = self.mapToScene(event.pos())
            # Get current viewport transformation
            transform = self.viewportTransform()
            scene_pos = self.mapToScene(event.pos())
            # Clear selection if no picker item below mouse
            picker_at = self.scene().picker_at(scene_pos, transform)
            picker_at = self._resolve_backdrop_pick(picker_at, scene_pos) or []
            if picker_at:
                if __EDIT_MODE__.get():
                    self.item_selected = True
                    # An item move is committed as one undo step on release;
                    # the pre-drag state is the current undo baseline, so
                    # nothing is captured here (see mouseReleaseEvent).
                    self.__move_prompt = False
                else:
                    self.modified_select = True
                    picker_widgets.select_picker_controls([picker_at], event)
            else:
                self.modified_select = False
                if not event.modifiers():
                    self.scene().clear_picker_selection()
                    cmds.select(cl=True)

        elif event.buttons() == QtCore.Qt.MouseButton.MiddleButton:
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.pan_active = True
            self.scene_mouse_origin = self.mapToScene(event.pos())

        # zoom support added for the mouse, for those pen/tablet users
        elif (
            event.buttons() == QtCore.Qt.MouseButton.RightButton
            and event.modifiers() == QtCore.Qt.AltModifier
        ):
            self.zoom_active = True
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self.scene_mouse_origin = self.mapToGlobal(event.pos())
            cursor_pos = QtGui.QVector2D(
                self.mapToGlobal(self.scene_mouse_origin)
            )
            screen = QtWidgets.QApplication.instance().primaryScreen()
            rect = screen.availableGeometry()
            self.top_left_pos = QtGui.QVector2D(rect.topLeft())
            self.zoom_delta = self.top_left_pos.distanceToPoint(cursor_pos)
            self.setTransformationAnchor(
                QtWidgets.QGraphicsView.AnchorViewCenter
            )

    def mouseMoveEvent(self, event):
        # Background layer drag / marquee intercepts movement when active.
        if self.background_edit and self._bg_mouse_move(event):
            return
        # Item scale/rotate drag intercepts movement when active.
        if self._item_dragging and self._item_mouse_move(event):
            return
        result = QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

        if (
            event.buttons() == QtCore.Qt.MouseButton.LeftButton
            and not self.item_selected
        ):
            self.drag_active = True

        # undo ---------------------------------------------------------------
        if (
            __EDIT_MODE__.get()
            and event.buttons() == QtCore.Qt.MouseButton.LeftButton
            and self.item_selected
        ):
            # confirm undo move chunck, a picker has been moved
            self.__move_prompt = True
            # Live-mirror the moving selection to linked partners in realtime.
            self.apply_mirror_for(self.scene().get_selected_items())
        # undo ----------------------------------------------------------------

        if self.pan_active:
            current_center = self.get_center_pos()
            scene_paning = self.mapToScene(event.pos())

            new_center = current_center - (
                scene_paning - self.scene_mouse_origin
            )
            self.centerOn(new_center)
            self._update_pinned_items()

        if self.zoom_active:
            cursor_pos = QtGui.QVector2D(self.mapToGlobal(event.pos()))
            current_delta = self.top_left_pos.distanceToPoint(cursor_pos)

            factor = 1.05
            if current_delta < self.zoom_delta:
                factor = 0.95

            # Apply zoom
            self.scale(factor, factor)
            self.zoom_delta = current_delta
            self._update_pinned_items()
            # Zoom changed; re-evaluate zoom-level visibility conditions.
            self.refresh_item_visibility()

        return result

    def mouseReleaseEvent(self, event):
        """Overload to clear selection on empty area"""
        # Background layer drag / marquee release when active.
        if self.background_edit and self._bg_mouse_release(event):
            return
        # Item scale/rotate drag release when active.
        if self._item_dragging and self._item_mouse_release(event):
            return
        result = QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)
        # A left release that was NOT a drag re-selects the item under the
        # cursor (click-to-select). Skip it when a move happened
        # (``__move_prompt``): dragging a selected item moves the whole
        # selection, so re-selecting the item under the cursor would collapse
        # a multi-selection down to one.
        if (
            not self.drag_active
            and event.button() == QtCore.Qt.MouseButton.LeftButton
            and not self.modified_select
            and not self.__move_prompt
        ):
            self.modified_select = False
            scene_pos = self.mapToScene(event.pos())

            # Get current viewport transformation
            transform = self.viewportTransform()

            # Clear selection if no picker item below mouse
            picker_at = self.scene().picker_at(scene_pos, transform) or []
            if not picker_at:
                if not event.modifiers():
                    self.scene().clear_picker_selection()
                    cmds.select(cl=True)
            elif picker_at and event.modifiers() == QtCore.Qt.AltModifier:
                picker_at.select_associated_controls()
                self.scene().select_picker_items([picker_at], event)
            else:
                self.scene().select_picker_items([picker_at], event)

        # Commit an item drag-move as one undo step -------------------------
        if not self.drag_active and self.__move_prompt:
            # Live-mirror the moved selection to any linked partners (covers a
            # plain item drag-move, not just the manipulator) before the
            # snapshot, so the partners' new positions are part of the step.
            self.apply_mirror_for(self.scene().get_selected_items())
            self.commit_edit("Move items")
        self.__move_prompt = None
        # undo ----------------------------------------------------------------

        # Area selection
        if (
            self.drag_active
            and event.button() == QtCore.Qt.MouseButton.LeftButton
        ):
            scene_drag_end = self.mapToScene(event.pos())

            sel_area = QtCore.QRectF(self.scene_mouse_origin, scene_drag_end)
            transform = self.viewportTransform()
            if not sel_area.size().isNull():
                items = self.scene().items(
                    sel_area,
                    QtCore.Qt.IntersectsItemShape,
                    QtCore.Qt.AscendingOrder,
                    deviceTransform=transform,
                )

                picker_items = []
                for item in items:
                    if not isinstance(item, picker_widgets.PickerItem):
                        continue
                    picker_items.append(item)
                if __EDIT_MODE__.get():
                    self.scene().select_picker_items(picker_items)
                    if event.modifiers() == QtCore.Qt.AltModifier:
                        ctrls = []
                        for x in picker_items:
                            ctrls.extend(x.get_controls())
                        cmds.select(cmds.ls(ctrls))
                else:
                    picker_widgets.select_picker_controls(picker_items, event)

        # Middle mouse view panning
        if (
            self.pan_active
            and event.button() == QtCore.Qt.MouseButton.MiddleButton
        ):
            current_center = self.get_center_pos()
            scene_drag_end = self.mapToScene(event.pos())

            new_center = current_center - (
                scene_drag_end - self.scene_mouse_origin
            )
            self.centerOn(new_center)
            self._update_pinned_items()
            self.pan_active = False
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        # zoom support added for the mouse, for those pen/tablet users
        if (
            self.zoom_active
            and event.button() == QtCore.Qt.MouseButton.RightButton
        ):
            self.zoom_active = False
            self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        # Refresh the item manipulator overlay + inline edit panel for the new
        # selection (edit mode only; a no-op when nothing consumes it).
        if __EDIT_MODE__.get():
            self._notify_item_selection()
            self.viewport().update()

        self.drag_active = False
        # A pan / drag-zoom just ended (or an item moved) -- realign the mask.
        self._notify_passthrough()
        return result

    def wheelEvent(self, event):
        """Wheel event to add zoom support"""
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        # Run default event
        # QtWidgets.QGraphicsView.wheelEvent(self, event)

        # Define zoom factor
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 0.9

        # Apply zoom
        self.scale(factor, factor)
        # Suspend the passthrough mask for the wheel burst (re-applied once it
        # settles) so the window is not reshaped on every wheel step.
        self._wheel_zooming = True
        try:
            # Keep viewport-pinned items locked to their screen anchors.
            self._update_pinned_items()
            # Zoom changed; re-evaluate zoom-level visibility conditions.
            self.refresh_item_visibility()
        finally:
            self._wheel_zooming = False
        self._suspend_passthrough()

    # =====================================================================
    # Editor undo/redo ---
    def _item_state(self, item):
        """Return a restorable snapshot of one item (its data + z-order)."""
        return {"data": copy.deepcopy(item.get_data()), "z": item.zValue()}

    def _snapshot_items(self):
        """Return ``{uuid: item-state}`` for every picker item in the scene."""
        return {
            item.uuid: self._item_state(item)
            for item in self.scene().get_picker_items()
        }

    def _diff_snapshot(self, before, after):
        """Return a ``{"before", "after"}`` record of the items that changed.

        Only items that were added, removed, or whose state differs are kept,
        each mapped to its state (or None when absent on that side). Returns
        None when nothing changed, so a no-op edit pushes no undo step.
        """
        changed_before = {}
        changed_after = {}
        for key in set(before) | set(after):
            was = before.get(key)
            now = after.get(key)
            if was != now:
                changed_before[key] = was
                changed_after[key] = now
        if not changed_before and not changed_after:
            return None
        return {"before": changed_before, "after": changed_after}

    def _reset_undo_baseline(self):
        """Re-baseline the undo diff to the current item set."""
        self._undo_baseline = self._snapshot_items()

    def commit_edit(self, label=None):
        """Push one undo step for changes since the last commit / baseline.

        The pre-edit state is the current baseline, so a whole gesture (an item
        drag, a manipulator scale / rotate) commits once at its end for a
        single step. A commit with no change (baseline already current) is a
        harmless no-op, so redundant calls do not create empty steps.

        Args:
            label (str, optional): a human label for the step (diagnostics).
        """
        current = self._snapshot_items()
        if self._undo_baseline is None:
            self._undo_baseline = current
            return
        record = self._diff_snapshot(self._undo_baseline, current)
        self._undo_baseline = current
        if record is not None:
            record["label"] = label
            self._undo_stack.push(record)

    def record_edit(self, label, mutate_fn):
        """Run ``mutate_fn`` then commit its changes as one undo step.

        Args:
            label (str): a human label for the step.
            mutate_fn (callable): performs the edit; its return is passed back.
        """
        result = mutate_fn()
        self.commit_edit(label)
        return result

    def _recreate_item(self, item_uuid):
        """Recreate a removed item, preserving its uuid identity."""
        item = picker_widgets.PickerItem(
            main_window=self.main_window, namespace=self.namespace
        )
        item.uuid = item_uuid
        item.setParent(self)
        self.scene().addItem(item)
        return item

    def _apply_undo_snapshot(self, snapshot):
        """Restore items to ``snapshot`` (``{uuid: state-or-None}``).

        Items mapped to a state are updated in place (or recreated when
        missing); items mapped to None are removed. Only the items named in the
        snapshot are touched, so unrelated items are left alone.
        """
        # One uuid -> item map for the whole restore (get_picker_by_uuid is a
        # linear scan, so looking it up per snapshot item would be O(n*m)).
        by_uuid = {
            item.uuid: item for item in self.scene().get_picker_items()
        }
        for key, state in snapshot.items():
            item = by_uuid.get(key)
            if state is None:
                if item is not None:
                    item.remove()
            else:
                data = copy.deepcopy(state["data"])
                if item is None:
                    # A recreated item starts clean; set_data restores it.
                    item = self._recreate_item(key)
                else:
                    # set_data is partial (only sets present keys), so first
                    # clear any optional key the restored data no longer has --
                    # else undoing an *added* key would leave it behind.
                    item.clear_keys_absent_from(data)
                item.set_data(data)
                item.setZValue(state["z"])

    def undo(self):
        """Undo the last editor edit (restore its 'before' snapshot)."""
        record = self._undo_stack.undo()
        if record is None:
            return
        self._apply_undo_snapshot(record["before"])
        self._after_undo_redo()

    def redo(self):
        """Redo the next editor edit (restore its 'after' snapshot)."""
        record = self._undo_stack.redo()
        if record is None:
            return
        self._apply_undo_snapshot(record["after"])
        self._after_undo_redo()

    def _after_undo_redo(self):
        """Refresh derived state and re-baseline after an undo / redo."""
        self._reset_undo_baseline()
        self._recompute_conditional_flag()
        self.refresh_item_visibility()
        self._notify_item_selection()
        self.viewport().update()

    # =====================================================================
    # Selection / clipboard shortcuts ---
    def _selection_anchor(self):
        """Return a selected item to anchor a selection-wide op, or None."""
        items = self.scene().get_selected_items()
        return items[0] if items else None

    def select_all_items(self):
        """Select every picker item (selection is not an undo step)."""
        self.scene().select_picker_items(self.get_picker_items())
        self._notify_item_selection()
        self.viewport().update()

    def clear_selection(self):
        """Clear the picker (and Maya) selection."""
        self.scene().clear_picker_selection()
        cmds.select(cl=True)
        self._notify_item_selection()
        self.viewport().update()

    def delete_selection(self):
        """Delete the selected items as one undo step."""
        items = self.scene().get_selected_items()
        if not items:
            return
        self.record_edit(
            "Delete items", lambda: [item.remove() for item in items]
        )

    def cut_event(self):
        """Copy then delete the selection as one undo step."""
        items = self.scene().get_selected_items()
        if not items:
            return
        self.copy_event()
        self.record_edit(
            "Cut items", lambda: [item.remove() for item in items]
        )

    def duplicate_selection(self, mirror=False):
        """Duplicate the selection (optionally mirrored) as one undo step."""
        if mirror:
            # Reuse the toolbar command so the search/replace prompt and the
            # persistent mirror linking / palette coloring stay in one place.
            if self.main_window is not None:
                self.main_window._cmd_duplicate_mirror()
            return
        anchor = self._selection_anchor()
        if anchor is None:
            return
        self.record_edit("Duplicate items", anchor.duplicate_selected)

    # Arrow-key nudge distances, in scene units (Shift = the larger step).
    _NUDGE_STEP = 1.0
    _NUDGE_LARGE = 10.0

    def nudge_selection(self, key, large=False):
        """Nudge the selection one step by an arrow key (one undo step).

        The scene is Y-up (the view flips Y), so Up increases y and Down
        decreases it.
        """
        items = self.scene().get_selected_items()
        if not items:
            return
        step = self._NUDGE_LARGE if large else self._NUDGE_STEP
        dx = dy = 0.0
        if key == QtCore.Qt.Key_Left:
            dx = -step
        elif key == QtCore.Qt.Key_Right:
            dx = step
        elif key == QtCore.Qt.Key_Up:
            dy = step
        elif key == QtCore.Qt.Key_Down:
            dy = -step

        def _do():
            for item in items:
                item.setPos(item.x() + dx, item.y() + dy)
            self.apply_mirror_for(items)

        self.record_edit("Nudge items", _do)

    def keyPressEvent(self, event):
        """Editor keyboard shortcuts (only while the picker holds focus).

        Because this fires only when the view widget has keyboard focus, the
        shortcuts never leak to Maya's global hotkeys; when the picker is
        unfocused Qt routes the key elsewhere and this is not called. Most
        shortcuts act on the selection and are edit-mode only.

        Args:
            event (QtCore.QEvent): keyboard event.
        """
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & QtCore.Qt.ControlModifier)
        shift = bool(mods & QtCore.Qt.ShiftModifier)

        # Undo / redo: Ctrl+Z, Ctrl+Shift+Z (and the legacy Ctrl+Y alias).
        if ctrl and key == QtCore.Qt.Key_Z:
            self.redo() if shift else self.undo()
            event.accept()
            return
        if ctrl and key == QtCore.Qt.Key_Y:
            self.redo()
            event.accept()
            return

        if not __EDIT_MODE__.get():
            event.ignore()
            return QtWidgets.QGraphicsView.keyPressEvent(self, event)

        handled = True
        if ctrl and key == QtCore.Qt.Key_C:
            self.copy_event()
        elif ctrl and key == QtCore.Qt.Key_V:
            self.paste_event()
        elif ctrl and key == QtCore.Qt.Key_X:
            self.cut_event()
        elif ctrl and key == QtCore.Qt.Key_D:
            self.duplicate_selection(mirror=shift)
        elif ctrl and key == QtCore.Qt.Key_A:
            self.select_all_items()
        elif key in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            self.delete_selection()
        elif key in (
            QtCore.Qt.Key_Left,
            QtCore.Qt.Key_Right,
            QtCore.Qt.Key_Up,
            QtCore.Qt.Key_Down,
        ):
            self.nudge_selection(key, large=shift)
        elif key == QtCore.Qt.Key_F:
            self.fit_scene_content()
        elif key == QtCore.Qt.Key_Escape:
            self.clear_selection()
        else:
            handled = False

        if handled:
            event.accept()
        else:
            event.ignore()
            QtWidgets.QGraphicsView.keyPressEvent(self, event)

    # undo --------------------------------------------------------------------

    def contextMenuEvent(self, event, mapped_pos=None):
        """Right click menu options"""
        if event.modifiers() == QtCore.Qt.AltModifier:
            # alt may indicate zooming enabled so no menu
            return
        # Item area
        picker_item = [
            item for item in self.get_picker_items() if item._hovered
        ]
        if picker_item:
            # Run default method that call on childs
            mapped_pos = event.globalPos()
            evnt_type = QtGui.QContextMenuEvent.Mouse
            contextEvent = QtGui.QContextMenuEvent(evnt_type, mapped_pos)
            return picker_item[0].contextMenuEvent(contextEvent)

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Build Edit move options
        if __EDIT_MODE__.get():
            mapped_pos = self.mapToScene(event.pos())
            add_action = QtWidgets.QAction("Add Item", None)
            add_action.triggered.connect(
                partial(self.add_picker_item_gui, mapped_pos)
            )
            menu.addAction(add_action)

            add_action1 = QtWidgets.QAction("Add with selected", None)
            add_action1.triggered.connect(
                partial(self.add_picker_item_selected, mapped_pos)
            )
            menu.addAction(add_action1)

            add_action2 = QtWidgets.QAction("Add item per selected", None)
            add_action2.triggered.connect(
                partial(self.add_picker_item_per_selected, mapped_pos)
            )
            menu.addAction(add_action2)

            toggle_handles_action = QtWidgets.QAction(
                "Toggle all handles", None
            )
            func = self.toggle_all_handles_event
            toggle_handles_action.triggered.connect(func)
            menu.addAction(toggle_handles_action)

            menu.addSeparator()

            # this copy is currently only supported when not hovering a picker
            copy_action = QtWidgets.QAction("Copy (Multi)", None)
            copy_action.triggered.connect(self.copy_event)
            menu.addAction(copy_action)

            # this paste is only supported when not hovering
            paste_action = QtWidgets.QAction("Paste (Multi)", None)
            paste_action.triggered.connect(self.paste_event)
            menu.addAction(paste_action)

            menu.addSeparator()

            background_action = QtWidgets.QAction("Add background layer", None)
            background_action.triggered.connect(self.set_background_event)
            menu.addAction(background_action)

            background_size_action = QtWidgets.QAction(
                "Background layers...", None
            )
            background_size_action.triggered.connect(self.background_options)
            menu.addAction(background_size_action)

            reset_background_action = QtWidgets.QAction(
                "Remove all backgrounds", None
            )
            func = self.reset_background_event
            reset_background_action.triggered.connect(func)
            menu.addAction(reset_background_action)

            menu.addSeparator()

            msg = "Convert to nurbs curves"
            convert_picker_to_curves = QtWidgets.QAction(msg, None)
            func = self.convert_picker_to_curves
            convert_picker_to_curves.triggered.connect(func)
            menu.addAction(convert_picker_to_curves)

            msg = "Convert to picker data"
            convert_curves_to_picker = QtWidgets.QAction(msg, None)
            func = self.convert_curves_to_picker
            convert_curves_to_picker.triggered.connect(func)
            menu.addAction(convert_curves_to_picker)

            msg = "Delete picker nurbs curves"
            delete_extraction_grp = QtWidgets.QAction(msg, None)
            func = self.delete_extraction_grp
            delete_extraction_grp.triggered.connect(func)
            menu.addAction(delete_extraction_grp)

            menu.addSeparator()

        if __EDIT_MODE__.get_main():
            toggle_mode_action = QtWidgets.QAction("Toggle Mode", None)
            toggle_mode_action.triggered.connect(self.toggle_mode_event)
            menu.addAction(toggle_mode_action)

            menu.addSeparator()

        # Common actions
        reset_view_action = QtWidgets.QAction("Reset view", None)
        reset_view_action.triggered.connect(self.fit_scene_content)
        menu.addAction(reset_view_action)
        frame_selection_view_action = QtWidgets.QAction(
            "Frame Selection", None
        )
        frame_selection_view_action.triggered.connect(
            self.fit_selection_content
        )
        menu.addAction(frame_selection_view_action)

        auto_frame_selection_view_action = QtWidgets.QAction(
            "Auto Frame view", None
        )
        auto_frame_selection_view_action.setCheckable(True)
        auto_frame_selection_view_action.setChecked(self.auto_frame_active)
        auto_frame_selection_view_action.triggered.connect(
            self.set_auto_frame_view
        )
        menu.addAction(auto_frame_selection_view_action)

        # Open context menu under mouse
        menu.exec_(event.globalPos())
        # Commit any item change a menu action made (add / paste / trace) as
        # one editor undo step; a no-op when nothing changed.
        self.commit_edit("Edit")

    def resizeEvent(self, *args, **kwargs):
        """Overload to force scale scene content to fit view"""
        # Fit scene content to view
        if self.auto_frame_active:
            self.fit_scene_content()

        # Run default resizeEvent
        result = QtWidgets.QGraphicsView.resizeEvent(self, *args, **kwargs)
        # Re-anchor pinned items to the new viewport size (covers the case
        # where auto-frame is off and no fit happened above). Visibility is not
        # refreshed here: an auto-frame fit already did (via fit_scene_content),
        # and without a fit a resize does not change the zoom scale.
        self._update_pinned_items()
        # The canvas resized -- realign the opacity-passthrough mask.
        self._notify_passthrough()
        return result

    def fit_scene_content(self):
        """Will fit scene content to view, by scaling it"""
        scene_rect = self.scene().get_bounding_rect(margin=self.fit_margin)
        self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)
        # The fit changed the view transform; re-anchor pins + re-eval zoom.
        self._update_pinned_items()
        self.refresh_item_visibility()
        self._notify_passthrough()

    def set_auto_frame_view(self):
        """Enable auto fit when a resize event happens"""
        # Fit scene content to view
        if not self.auto_frame_active:
            self.fit_scene_content()
        self.auto_frame_active = not self.auto_frame_active

    def fit_selection_content(self):
        """Will fit the selected item to view, by scaling it"""
        scene_rect = self.scene().get_bounding_rect(
            margin=self.fit_margin, selection=True
        )
        if scene_rect:
            self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)
            self._update_pinned_items()
            self.refresh_item_visibility()

    def get_color_picker_override(self, picker, ctrl):
        """Get the maya override color and return picker equivelant

        Args:
            picker (PickerItem): pickeritem class
            ctrl (str): name of the control

        Returns:
            list: [R, G, B, Alpha]
        """
        node = ctrl
        if cmds.nodeType(ctrl) == "transform":
            node = cmds.listRelatives(ctrl, shapes=True)[0]
        if not cmds.getAttr("{}.overrideEnabled".format(node)):
            return [0, 0, 0, 255]
        if cmds.getAttr("{}.overrideRGBColors".format(node)):
            r_color = cmds.getAttr("{}.overrideColorR".format(node))
            g_color = cmds.getAttr("{}.overrideColorG".format(node))
            b_color = cmds.getAttr("{}.overrideColorB".format(node))
            return [r_color * 255, g_color * 255, b_color * 255, 255]
        else:
            override_index = cmds.getAttr("{}.overrideColor".format(node))
            color_rgb = MAYA_OVERRIDE_COLOR[override_index]
            return [color_rgb[0], color_rgb[1], color_rgb[2], 255]

    def add_picker_item(self, event=None):
        """Add new PickerItem to current view"""
        ctrl = picker_widgets.PickerItem(
            main_window=self.main_window, namespace=self.namespace
        )
        ctrl.setParent(self)
        self.scene().addItem(ctrl)

        # Move ctrl
        if event:
            ctrl.setPos(event.pos())
        else:
            ctrl.setPos(0, 0)

        return ctrl

    def add_picker_item_gui(self, mouse_pos=None):
        """Create picker item at the position of the mouse

        Args:
            mouse_pos (QPosition, optional): mouse position

        Returns:
            PickerItem: the created (and selected) item.
        """
        ctrl = self.add_picker_item()
        ctrl.setPos(mouse_pos)
        # Keep the new item selected so it can be edited immediately.
        self.scene().select_picker_items([ctrl])
        return ctrl

    def add_widget_item(self, widget_type, mouse_pos=None):
        """Create a picker item of ``widget_type`` at ``mouse_pos``.

        Used by the left-strip drag-and-drop palette. An interactive widget
        (checkbox / slider / slider2d) is created with a type-appropriate
        default shape, a default binding range, and seeded "just print"
        scripts; a plain button is created with the generic item shape.

        Args:
            widget_type (str): a value from ``widget_binding.WIDGET_TYPES``.
            mouse_pos (QPointF, optional): scene position for the new item.

        Returns:
            PickerItem: the created (and selected) item.
        """
        if widget_type == tool_bar.BACKDROP_PAYLOAD:
            return self.add_backdrop_item(mouse_pos)
        ctrl = self.add_picker_item()
        if mouse_pos is not None:
            ctrl.setPos(mouse_pos)
        if widget_binding.is_interactive(widget_type):
            # set_widget_type seeds the default binding + scripts, so only the
            # type and the type-appropriate shape are supplied here.
            data = {"widget": widget_type}
            handles = widget_binding.default_handles(widget_type)
            if handles:
                data["handles"] = handles
            ctrl.set_data(data)
        self.scene().select_picker_items([ctrl])
        return ctrl

    def add_svg_item(self, path, scene_pos=None):
        """Import an ``.svg`` file as a vector picker item.

        Parses the SVG's supported geometry (discarding and reporting
        unsupported elements), and creates one vector item at ``scene_pos``.
        Nothing is created when the file has no supported geometry; either way
        the import never raises.

        Args:
            path (str): path to the ``.svg`` file.
            scene_pos (QPointF, optional): scene position for the new item
                (defaults to the view center).

        Returns:
            PickerItem: the created (and selected) vector item, or None when the
            SVG had no supported geometry.
        """
        name = os.path.basename(path)
        try:
            with open(path, "r") as svg_file:
                text = svg_file.read()
        except IOError as exc:
            mgear.log(
                "anim_picker: could not read '{}' ({})".format(path, exc),
                mgear.sev_warning,
            )
            return None

        # flip_y: the picker view is y-up, so the SVG (y-down) is flipped to
        # import upright. mode is a suggested fill / stroke render (line-art
        # icons come back as stroke, so they are not filled to nothing).
        subpaths, dropped, mode = svg_import.parse_svg(text, flip_y=True)
        if not subpaths:
            reason = (
                "ignored unsupported: {}".format(", ".join(dropped))
                if dropped
                else "no supported geometry"
            )
            mgear.log(
                "anim_picker: '{}' imported nothing ({})".format(name, reason),
                mgear.sev_warning,
            )
            return None
        if dropped:
            mgear.log(
                "anim_picker: imported '{}'; ignored unsupported: {}".format(
                    name, ", ".join(dropped)
                ),
                mgear.sev_warning,
            )

        ctrl = self.add_picker_item()
        if scene_pos is not None:
            ctrl.setPos(scene_pos)
        ctrl.set_data(
            {"svg": {"name": name, "subpaths": subpaths, "mode": mode}}
        )
        self.scene().select_picker_items([ctrl])
        return ctrl

    def add_backdrop_item(self, mouse_pos=None, fit_items=None):
        """Create a backdrop container, sent behind the picker items.

        Args:
            mouse_pos (QPointF, optional): scene position for the backdrop
                (ignored when ``fit_items`` is given).
            fit_items (list, optional): items to enclose; the backdrop is sized
                and placed to wrap them (with padding). When omitted a small
                default backdrop is created so it does not swallow items by
                accident.

        Returns:
            PickerItem: the created (and selected) backdrop.
        """
        ctrl = self.add_picker_item()
        data = {
            "backdrop": True,
            "title": "Backdrop",
            "corner_radius": 8.0,
            "color": (70, 80, 110, 80),
        }
        if fit_items:
            union = _united_scene_rect(fit_items)
            pad = 24.0
            half_w = union.width() / 2.0 + pad
            half_h = union.height() / 2.0 + pad
            data["handles"] = [
                [-half_w, -half_h],
                [half_w, -half_h],
                [half_w, half_h],
                [-half_w, half_h],
            ]
            data["position"] = [union.center().x(), union.center().y()]
        else:
            if mouse_pos is not None:
                ctrl.setPos(mouse_pos)
            # A modest default so a dropped backdrop does not enclose nearby
            # items unintentionally.
            data["handles"] = [[-70, -45], [70, -45], [70, 45], [-70, 45]]
        ctrl.set_data(data)
        # Backdrops sit behind the picker items so the buttons stay clickable.
        # Nested-backdrop *selection* is resolved geometrically in
        # ``_resolve_backdrop_pick`` (smallest under the cursor wins), so no
        # area-based z-restack is needed here.
        ctrl.move_to_back()
        self.scene().select_picker_items([ctrl])
        return ctrl

    def _resolve_backdrop_pick(self, picker_at, scene_pos):
        """Prefer the smallest backdrop under the cursor (innermost nested one).

        A normal button drawn over the backdrops wins as usual (``picker_at``
        is returned unchanged). But when the pick is a backdrop, the
        smallest-area backdrop whose rectangle contains the point is chosen, so
        an inner nested backdrop is always selectable regardless of z-order.

        Args:
            picker_at (PickerItem): the item the scene hit-test returned.
            scene_pos (QPointF): the click position in scene coordinates.

        Returns:
            PickerItem: the resolved item (or the input when not a backdrop).
        """
        if picker_at is None or not getattr(picker_at, "backdrop", False):
            return picker_at
        best = picker_at
        best_area = self._backdrop_area(best)
        for item in self.get_picker_items():
            if item is best or not item.backdrop:
                continue
            rect = item.sceneBoundingRect()
            if rect.contains(scene_pos):
                area = rect.width() * rect.height()
                if area < best_area:
                    best = item
                    best_area = area
        return best

    @staticmethod
    def _backdrop_area(item):
        """Return an item's scene bounding-box area."""
        rect = item.sceneBoundingRect()
        return rect.width() * rect.height()

    def _is_palette_drag(self, event):
        """Return True when ``event`` is a palette-tile drag we accept."""
        return __EDIT_MODE__.get() and event.mimeData().hasFormat(
            tool_bar.WIDGET_MIME
        )

    def _is_shape_drag(self, event):
        """Return True when ``event`` is a shape tile drag we accept."""
        return __EDIT_MODE__.get() and event.mimeData().hasFormat(
            shape_library.SHAPE_MIME
        )

    def _svg_drop_paths(self, event):
        """Return the ``.svg`` local file paths in a file-URL drag (edit mode).

        Empty when not in edit mode, not a URL drag, or no dropped file is an
        ``.svg`` -- so a non-SVG file drop falls through to the default.
        """
        if not __EDIT_MODE__.get():
            return []
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        paths = []
        for url in mime.urls():
            local = url.toLocalFile()
            if local and local.lower().endswith(".svg"):
                paths.append(local)
        return paths

    def _drop_view_pos(self, event):
        """Return the drop position in view coords (Qt5 pos / Qt6 position)."""
        # Qt6 (Maya 2025+) drops pos() in favor of position(); support both.
        try:
            return event.position().toPoint()
        except AttributeError:
            return event.pos()

    def dragEnterEvent(self, event):
        """Accept a palette / shape / ``.svg`` file drag in edit mode."""
        if (
            self._is_palette_drag(event)
            or self._is_shape_drag(event)
            or self._svg_drop_paths(event)
        ):
            event.acceptProposedAction()
        else:
            QtWidgets.QGraphicsView.dragEnterEvent(self, event)

    def dragMoveEvent(self, event):
        """Keep accepting a palette / shape / ``.svg`` drag over the canvas."""
        if (
            self._is_palette_drag(event)
            or self._is_shape_drag(event)
            or self._svg_drop_paths(event)
        ):
            event.acceptProposedAction()
        else:
            QtWidgets.QGraphicsView.dragMoveEvent(self, event)

    def dropEvent(self, event):
        """Create the dropped widget / shape / SVG item at the drop (edit)."""
        if self._is_palette_drag(event):
            widget_type = bytes(
                event.mimeData().data(tool_bar.WIDGET_MIME)
            ).decode("utf-8")
            scene_pos = self.mapToScene(self._drop_view_pos(event))
            self.add_widget_item(widget_type, scene_pos)
            event.acceptProposedAction()
            return
        if self._is_shape_drag(event):
            name = bytes(
                event.mimeData().data(shape_library.SHAPE_MIME)
            ).decode("utf-8")
            shape = shape_library.get_shape(name)
            if shape is not None:
                scene_pos = self.mapToScene(self._drop_view_pos(event))
                self.create_item_with_shape(shape, scene_pos)
            event.acceptProposedAction()
            return
        svg_paths = self._svg_drop_paths(event)
        if svg_paths:
            scene_pos = self.mapToScene(self._drop_view_pos(event))
            for path in svg_paths:
                self.add_svg_item(path, scene_pos)
            event.acceptProposedAction()
            return
        QtWidgets.QGraphicsView.dropEvent(self, event)

    def add_picker_item_selected(self, mouse_pos=None):
        """Add new PickerItem to current view"""
        ctrl = self.add_picker_item()
        data = {}
        selected = cmds.ls(sl=True) or []
        data["controls"] = selected
        ctrl.set_data(data)
        ctrl.set_selected_state(True)
        if selected:
            colors_rgb = self.get_color_picker_override(ctrl, selected[0])
            ctrl.set_color(color=colors_rgb)
        if mouse_pos:
            ctrl.setPos(mouse_pos)

        return ctrl

    def add_picker_item_per_selected(self, mouse_pos=None):
        """Add new PickerItem to current view"""
        selection = cmds.ls(sl=True) or []
        if not selection:
            return
        created_ctrls = []
        if mouse_pos:
            x_start = mouse_pos.x()
            y_start = mouse_pos.y()
        else:
            x_start = 0
            y_start = 0
        y_increment = -35
        for selected in selection:
            ctrl = self.add_picker_item()
            data = {}
            data["controls"] = [selected]
            data["position"] = [x_start, y_start]
            colors_rgb = self.get_color_picker_override(ctrl, selected)
            ctrl.set_color(color=colors_rgb)
            y_start = y_start + y_increment
            ctrl.set_data(data)
            ctrl.set_selected_state(True)
            created_ctrls.append(ctrl)

        return created_ctrls

    def create_item_with_shape(self, shape, scene_pos=None):
        """Create one item carrying ``shape`` at ``scene_pos`` (drag-create).

        Args:
            shape (dict): a resolved ``shape_library`` entry.
            scene_pos (QPointF, optional): drop position (scene coords).

        Returns:
            PickerItem: the created (and selected) item.
        """

        def _do():
            ctrl = self.add_picker_item()
            if scene_pos is not None:
                ctrl.setPos(scene_pos)
            ctrl.apply_library_shape(shape)
            self.scene().select_picker_items([ctrl])
            return ctrl

        return self.record_edit("Add shape", _do)

    def create_shape_from_selection(self, shape, axis="vertical"):
        """Stamp one item with ``shape`` per selected Maya control.

        The items are laid out in a column (``axis`` "vertical") or a row
        ("horizontal"), centered on the canvas, and each is linked to (and
        colored from) its control -- reusing the trace group-centering helper.
        Fine-tune the spacing afterward with the expand / contract tools.

        Args:
            shape (dict): a resolved ``shape_library`` entry.
            axis (str): "vertical" (column) or "horizontal" (row).

        Returns:
            list: the created PickerItem instances.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            return []

        def _do():
            gap = 50.0
            created = []
            for index, ctrl in enumerate(selection):
                item = self.add_picker_item()
                item.apply_library_shape(shape)
                item.set_control_list([ctrl])
                item.set_color(
                    color=self.get_color_picker_override(item, ctrl)
                )
                # Scene is Y-up: a column stacks downward (negative y).
                if axis == "horizontal":
                    item.setPos(index * gap, 0)
                else:
                    item.setPos(0, -index * gap)
                created.append(item)
            self._center_items_on(created, self.get_center_pos())
            self.scene().select_picker_items(created)
            return created

        return self.record_edit("Create shapes from selection", _do)

    def add_picker_item_trace(self, plane="front", mouse_pos=None):
        """Create one silhouette button per selected control (trace tool).

        For each selected control the world-space shape points are projected
        onto ``plane`` (front / side / top), reduced to a 2D convex hull, and
        scaled -- with a single shared factor so the traced set keeps the rig's
        proportions (auto-fit) -- into a picker button placed at the control's
        projected position and colored from the control.

        Args:
            plane (str): projection plane (``silhouette.PLANE_*``).
            mouse_pos (QPointF, optional): canvas anchor for the traced set.

        Returns:
            list: the created PickerItem instances.
        """
        # Target canvas span (pixels) the whole traced set is auto-fit into.
        target_span = 400.0

        selection = cmds.ls(sl=True) or []
        if not selection:
            return []

        # First pass: extract + project + hull each control, and collect the
        # global bounds so one scale keeps the set's proportions.
        traced = []
        all_points = []
        for ctrl in selection:
            points_3d = maya_handlers.get_shape_points(ctrl)
            if not points_3d:
                continue
            hull = silhouette.convex_hull_2d(
                silhouette.project_to_plane(points_3d, plane)
            )
            if not hull:
                continue
            traced.append((ctrl, hull))
            all_points.extend(hull)

        if not traced:
            return []

        scale = silhouette.fit_scale(
            silhouette.bounding_box(all_points), target_span
        )
        centers = [silhouette.centroid(hull) for _ctrl, hull in traced]

        # Second pass: lay each button out at its scaled projected center
        # (relative arrangement); the group is centered on the target below.
        created = []
        item_by_ctrl = {}
        for (ctrl, hull), (center_x, center_y) in zip(traced, centers):
            handles = [
                [(hx - center_x) * scale, (hy - center_y) * scale]
                for hx, hy in hull
            ]
            # A point / edge-on projection collapses to < 3 hull points; use a
            # small box so the polygon shape stays valid and visible.
            if len(handles) < 3:
                handles = [[-8, -8], [8, -8], [8, 8], [-8, 8]]
            item = self.add_picker_item()
            item.set_data(
                {
                    "controls": [ctrl],
                    "handles": handles,
                    "position": [center_x * scale, center_y * scale],
                }
            )
            item.set_color(color=self.get_color_picker_override(item, ctrl))
            item.set_selected_state(True)
            created.append(item)
            item_by_ctrl[ctrl] = item

        # Center the whole traced group on the target by its real bounding box
        # (accounts for the button shapes, so it lands visually centered
        # regardless of asymmetric silhouettes).
        target = mouse_pos if mouse_pos is not None else self.get_center_pos()
        self._center_items_on(created, target)
        self._link_traced_mirror_pairs(item_by_ctrl)
        return created

    def _center_items_on(self, items, target):
        """Shift ``items`` as a group so their union bbox center is ``target``.

        Args:
            items (list): PickerItems to move together.
            target (QPointF): scene point the group's center should land on.
        """
        union = _united_scene_rect(items)
        if union is None:
            return
        dx = target.x() - union.center().x()
        dy = target.y() - union.center().y()
        for item in items:
            item.setPos(item.x() + dx, item.y() + dy)

    def _link_traced_mirror_pairs(self, item_by_ctrl):
        """Link traced L/R control pairs as mirror pairs.

        Detects mirror partners by the ``_L`` / ``_R`` naming convention (the
        same ``convertRLName`` logic ``pickWalk`` uses); when both sides of a
        pair were traced in this run, their buttons are linked so editing one
        mirrors to the other.

        Args:
            item_by_ctrl (dict): ``{control_name: PickerItem}`` traced this run.
        """
        linked = set()
        for ctrl, item in item_by_ctrl.items():
            if item in linked:
                continue
            try:
                mirror_name = string.convertRLName(ctrl)
            except Exception:
                mirror_name = None
            if not mirror_name or mirror_name == ctrl:
                continue
            partner = item_by_ctrl.get(mirror_name)
            if partner is None or partner is item or partner in linked:
                continue
            self.link_mirror_pair(item, partner)
            linked.add(item)
            linked.add(partner)

    def copy_event(self):
        """reset the clipboard and populate the list with picker data for paste"""
        global _CLIPBOARD
        _CLIPBOARD = []
        selected_pickers = self.scene().get_selected_items()
        for picker in selected_pickers:
            _CLIPBOARD.append(picker.get_data())

    def paste_event(self):
        """create new anim pickers based off the data in the clipboard
        Make new pickers selected
        """
        global _CLIPBOARD
        if not _CLIPBOARD:
            return

        def _do():
            [
                x.set_selected_state(False)
                for x in self.scene().get_selected_items()
            ]
            for data in _CLIPBOARD:
                ctrl = self.add_picker_item(event=None)
                ctrl.set_data(data)
                ctrl.set_selected_state(True)
            # A pasted item may carry a visibility condition copied from
            # another picker, so refresh the "any conditioned item?" gate and
            # re-apply.
            self._recompute_conditional_flag()
            self.refresh_item_visibility()

        self.record_edit("Paste items", _do)

    def toggle_all_handles_event(self, event=None):
        new_status = None
        for item in list(self.scene().items()):
            # Skip non picker items
            if not isinstance(item, picker_widgets.PickerItem):
                continue

            # Get first status
            if new_status is None:
                new_status = not item.get_edit_status()

            # Set item status
            item.set_edit_status(new_status)

    def toggle_mode_event(self, event=None):
        """Will toggle UI edition mode"""
        if not self.main_window:
            return

        # Check for possible data change/loss
        if __EDIT_MODE__.get():
            if not self.main_window.check_for_data_change():
                return

        # Toggle mode
        __EDIT_MODE__.toggle()

        # Entering edit mode starts a fresh editing session: clear the undo
        # history and baseline the diff to the current item set so the first
        # edit is recorded correctly.
        if __EDIT_MODE__.get():
            self._undo_stack.clear()
            self._reset_undo_baseline()

        # Reset size to default
        self.main_window.reset_default_size()
        self.main_window.refresh()

    def apply_background_fallback_logic(self, path):
        # test if the original path exists
        if os.path.exists(path):
            return path
        # check the data node for the "source_file_path" that is added when
        # pkr is loaded from file
        data = self.window().get_current_data_node().read_data_from_node()
        pkr_path = data.get("source_file_path", None)
        if not pkr_path or pkr_path is None:
            return path
        # looking in the neighboring directories for images dir
        pkr_dir = os.path.dirname(pkr_path)
        rel_path_token = os.environ.get(
            ANIM_PICKER_RELATIVE_IMAGES, DEFAULT_RELATIVE_IMAGES_PATH
        )
        base_name = os.path.basename(path)
        relative_image_path = os.path.realpath(
            os.path.join(pkr_dir, rel_path_token, base_name)
        )
        # only return if path exists
        if os.path.exists(relative_image_path):
            return relative_image_path
        else:
            return path

    def _load_layer_image(self, layer):
        """Resolve a layer's path and decode its (vertically mirrored) image.

        Fills the layer's natural size when unset and stores the resolved path
        back on the model so re-saves point at a valid file.

        Args:
            layer (BackgroundLayer): layer to load.

        Returns:
            QtGui.QImage: the loaded image, or None if the path is missing.
        """
        if not layer.path:
            return None
        path = os.path.abspath(r"{}".format(layer.path))
        path = self.apply_background_fallback_logic(path)
        if not (path and os.path.exists(path)):
            mgear.log(
                "anim_picker: background image not found: '{}'".format(path),
                mgear.sev_warning,
            )
            return None
        layer.path = path
        image = QtGui.QImage(path).mirrored(False, True)
        if not layer.size or not layer.size[0] or not layer.size[1]:
            layer.size = [image.width(), image.height()]
        return image

    def _layer_draw_size(self, loaded):
        """Return the (width, height) a layer is drawn at (model or natural)."""
        layer = loaded.layer
        if layer.size and layer.size[0] and layer.size[1]:
            return int(layer.size[0]), int(layer.size[1])
        if loaded.image is not None:
            return loaded.image.width(), loaded.image.height()
        return 0, 0

    def _refresh_layer_geometry(self):
        """Recompute and cache each layer's target/source rect and the union.

        Called on layer mutation (add/remove/move/resize/reposition) so the
        paint path never allocates or recomputes rects per frame.
        """
        bounding = None
        for loaded in self.background_layers:
            if loaded.image is None:
                loaded.rect = None
                loaded.src_rect = None
                continue
            width, height = self._layer_draw_size(loaded)
            cx, cy = loaded.layer.position
            loaded.rect = QtCore.QRectF(
                cx - width / 2.0, cy - height / 2.0, width, height
            )
            loaded.src_rect = QtCore.QRectF(loaded.image.rect())
            bounding = (
                loaded.rect
                if bounding is None
                else bounding.united(loaded.rect)
            )
        self._bounding_rect = bounding

    def _update_scene_rect(self):
        """Size the scene rect to all content so pan/zoom can reach it.

        The scene rect is the union of the background layers and the picker
        items (the buttons), floored at the default canvas so panning stays
        free and robust to items being moved while editing (issue #108). Only
        the pan/zoom bounds are set here; the view is not refit.
        """
        self._refresh_layer_geometry()

        # Union the background layer bounds with the picker items' extent so
        # the canvas is not clamped to the image size (buttons stay reachable).
        # Pinned HUD items are excluded so they never inflate the canvas.
        content = self._bounding_rect
        items_rect = self.scene().content_bounding_rect()
        if not items_rect.isNull():
            content = (
                items_rect
                if content is None
                else content.united(items_rect)
            )

        if content is None:
            self.scene().set_default_size()
            return

        margin = self.fit_margin
        content = content.adjusted(-margin, -margin, margin, margin)
        self.scene().set_rect(content.united(self.scene().default_rect()))

    def _update_scene_size(self):
        """Recompute the scene rect and refit the view (load / layer edits)."""
        self._update_scene_rect()
        self.fit_scene_content()
        self.viewport().update()

    def set_background(self, path=None):
        """Append a background image layer to this tab.

        Args:
            path (str): image file path.
        """
        if not path:
            return
        layer = background_model.BackgroundLayer()
        layer.path = path
        image = self._load_layer_image(layer)
        if image is None:
            return
        self.background_layers.append(_LoadedBackground(layer, image))
        self._update_scene_size()

    def set_backgrounds(self, layers):
        """Replace all layers from a list of BackgroundLayer models.

        Args:
            layers (list): list of BackgroundLayer.
        """
        self.background_layers = []
        for layer in layers:
            image = self._load_layer_image(layer)
            if image is None:
                continue
            self.background_layers.append(_LoadedBackground(layer, image))
        self._update_scene_size()

    def clear_backgrounds(self):
        """Remove all background layers and restore the default canvas."""
        self.background_layers = []
        self._update_scene_size()

    def enter_background_edit(self):
        """Activate on-canvas background layer manipulation (panel open)."""
        self.background_edit = True
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.viewport().update()

    def exit_background_edit(self):
        """Deactivate manipulation and restore normal picker interaction.

        Only manipulation state is reset here; the ``bg_ui`` panel reference is
        owned by ``background_options`` (which already tolerates a stale one).
        """
        self.background_edit = False
        self.bg_manipulator.clear()
        self._bg_dragging = False
        self._bg_marquee_origin = None
        self._bg_marquee_current = None
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.viewport().update()

    def get_selected_bg_indices(self):
        """Return the indices of the currently selected background layers."""
        return list(self.bg_manipulator.selected)

    def set_selected_bg_indices(self, indices):
        """Set the selected background layers (driven by the panel list)."""
        self.bg_manipulator.set_selected(indices)
        self.viewport().update()

    def _notify_bg_selection(self):
        """Tell the panel the canvas selection changed."""
        if self.bg_ui:
            self.bg_ui.on_canvas_selection_changed()

    def _notify_bg_fields(self):
        """Tell the panel to refresh its position/size fields."""
        if self.bg_ui:
            self.bg_ui.refresh_active_fields()

    def _bg_mouse_press(self, event):
        """Handle a background-edit left press. Return True if consumed."""
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        scene_pos = self.mapToScene(event.pos())
        x, y = scene_pos.x(), scene_pos.y()

        # Grab a handle or the body of the current selection first.
        hit = self.bg_manipulator.hit_test(x, y)
        if hit is not None:
            mode = hit[0]
            handle = hit[1] if mode == "handle" else None
            self.bg_manipulator.begin_drag(mode, handle, x, y)
            self._bg_dragging = True
            return True

        # Otherwise select the layer under the cursor, or start a marquee.
        additive = bool(event.modifiers() & QtCore.Qt.ShiftModifier)
        index = self.bg_manipulator.layer_at(x, y)
        if index is not None:
            self.bg_manipulator.select(index, additive)
            self._notify_bg_selection()
            self.viewport().update()
            return True

        if not additive:
            self.bg_manipulator.clear()
            self._notify_bg_selection()
        self._bg_marquee_origin = scene_pos
        self._bg_marquee_current = scene_pos
        self.viewport().update()
        return True

    def _bg_mouse_move(self, event):
        """Handle a background-edit drag/marquee move. Return True if used."""
        if not (event.buttons() & QtCore.Qt.MouseButton.LeftButton):
            return False
        scene_pos = self.mapToScene(event.pos())

        if self._bg_dragging:
            keep = bool(event.modifiers() & QtCore.Qt.ShiftModifier)
            self.bg_manipulator.update_drag(scene_pos.x(), scene_pos.y(), keep)
            self._refresh_layer_geometry()
            self._notify_bg_fields()
            self.viewport().update()
            return True

        if self._bg_marquee_origin is not None:
            self._bg_marquee_current = scene_pos
            self.viewport().update()
            return True

        return False

    def _bg_mouse_release(self, event):
        """Handle a background-edit release. Return True if consumed."""
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False

        if self._bg_dragging:
            self.bg_manipulator.end_drag()
            self._bg_dragging = False
            # Grow the pan bounds to the layer's final size (no view refit).
            self._update_scene_rect()
            self._notify_bg_fields()
            return True

        if self._bg_marquee_origin is not None:
            additive = bool(event.modifiers() & QtCore.Qt.ShiftModifier)
            rect = QtCore.QRectF(
                self._bg_marquee_origin, self._bg_marquee_current
            ).normalized()
            self._bg_marquee_origin = None
            self._bg_marquee_current = None
            if rect.width() > 1e-5 or rect.height() > 1e-5:
                self.bg_manipulator.select_in_rect(rect, additive)
                self._notify_bg_selection()
            self.viewport().update()
            return True

        return False

    def _transform_tool_active(self):
        """Return True when the Transform tool is active (manipulator on)."""
        active = getattr(
            self.main_window, "active_tool", tool_bar.TOOL_SELECT
        )
        return active == tool_bar.TOOL_TRANSFORM

    def _select_on_press(self, picker_at, event):
        """Select ``picker_at`` on mouse press (edit mode).

        Returns True when the selection is fully determined here (release must
        not re-handle it): Shift adds, Ctrl removes, and a plain click on an
        unselected item selects just it. Returns False for a plain click on an
        already-selected item (kept for a group drag; a release without a drag
        collapses it to one) and for Alt (control-selection handled at release).

        Args:
            picker_at (PickerItem): the item under the cursor.
            event (QMouseEvent): the press event.

        Returns:
            bool: True if the selection was finalized here.
        """
        modifiers = event.modifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            picker_at.set_selected_state(True)
        elif modifiers == QtCore.Qt.ControlModifier:
            picker_at.set_selected_state(False)
        elif (
            not modifiers
            and picker_at not in self.scene().get_selected_items()
        ):
            self.scene().clear_picker_selection()
            picker_at.set_selected_state(True)
        else:
            return False
        self._notify_item_selection()
        self.viewport().update()
        return True

    def _notify_item_selection(self):
        """Tell the inline edit panel the item selection changed (full sync)."""
        panel = getattr(self.main_window, "edit_panel", None)
        if panel is not None:
            panel.sync_from_view(self)
        update = getattr(self.main_window, "update_tool_commands", None)
        if update is not None:
            update()

    def _notify_item_transform(self):
        """Tell the panel the selection's transform changed (light refresh)."""
        panel = getattr(self.main_window, "edit_panel", None)
        if panel is not None:
            panel.refresh_transform()

    def _item_mouse_press(self, event):
        """Begin an item scale/rotate drag if a handle was pressed.

        Returns True (consuming the event) only when a manipulator handle under
        the cursor starts a drag; otherwise the event falls through to normal
        selection / move handling.
        """
        if not __EDIT_MODE__.get():
            return False
        if not self._transform_tool_active():
            return False
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        if not self.item_manipulator.is_active():
            return False
        scene_pos = self.mapToScene(event.pos())
        hit = self.item_manipulator.hit_test(scene_pos.x(), scene_pos.y())
        if hit is None:
            return False
        mode = hit[0]
        handle = hit[1] if mode == "scale" else None
        self.item_manipulator.begin_drag(
            mode, handle, scene_pos.x(), scene_pos.y()
        )
        self._item_dragging = True
        return True

    def _item_mouse_move(self, event):
        """Update an in-progress item scale/rotate drag. Return True if used."""
        if not (event.buttons() & QtCore.Qt.MouseButton.LeftButton):
            return False
        scene_pos = self.mapToScene(event.pos())
        keep = bool(event.modifiers() & QtCore.Qt.ShiftModifier)
        self.item_manipulator.update_drag(scene_pos.x(), scene_pos.y(), keep)
        # Live-mirror to linked partners in realtime (not just on release).
        self.apply_mirror_for(self.scene().get_selected_items())
        self._notify_item_transform()
        self.viewport().update()
        return True

    def _item_mouse_release(self, event):
        """Finish an item scale/rotate drag. Return True if consumed."""
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        self.item_manipulator.end_drag()
        self._item_dragging = False
        # Grow the pan bounds to the items' new extent (no view refit).
        self._update_scene_rect()
        # Live-mirror the transformed selection to any linked partners, then
        # commit the whole scale / rotate drag as a single undo step (the
        # pre-drag state is the baseline, so mid-drag frames are not recorded).
        self.apply_mirror_for(self.scene().get_selected_items())
        self.commit_edit("Transform items")
        self._notify_item_selection()
        self.viewport().update()
        return True

    # -- mirror relationships -------------------------------------------
    def get_mirror_partner(self, item):
        """Return the item linked as ``item``'s mirror partner, or None."""
        if not item.mirror_id:
            return None
        for other in self.get_picker_items():
            if other is not item and other.item_id == item.mirror_id:
                return other
        return None

    def link_mirror_pair(self, item_a, item_b):
        """Link two items as a mirror pair, minting ids as needed."""
        if not item_a.item_id:
            item_a.item_id = str(uuid.uuid4())
        if not item_b.item_id:
            item_b.item_id = str(uuid.uuid4())
        item_a.mirror_id = item_b.item_id
        item_b.mirror_id = item_a.item_id
        self._has_mirror_links = True

    def unlink_mirror(self, item):
        """Break the mirror link on ``item`` and its partner."""
        partner = self.get_mirror_partner(item)
        item.mirror_id = None
        if partner is not None:
            partner.mirror_id = None
        self._recompute_mirror_links()

    def has_mirror_links(self):
        """Return True when any item in the view is mirror-linked (cached)."""
        return self._has_mirror_links

    def _recompute_mirror_links(self):
        """Refresh the cached mirror-link flag (call on link changes / load)."""
        self._has_mirror_links = any(
            item.mirror_id for item in self.get_picker_items()
        )

    def _mirror_item_to(self, src, dst):
        """Write ``src``'s mirrored transform / shape onto ``dst``.

        Color is intentionally NOT mirrored here: L/R coloring is set
        explicitly through the color palette, so a live geometry mirror never
        overwrites a deliberately chosen side color.
        """
        axis = self.mirror_axis_x
        pos = mirror.mirror_position([src.x(), src.y()], axis)
        dst.setPos(pos[0], pos[1])
        dst.setRotation(mirror.mirror_rotation(src.rotation()))
        if src.is_vector_shape():
            dst.set_svg_shape(dict(src.get_svg_shape()))
            dst.set_svg_subpaths(
                svg_import.scale_subpaths(src.get_svg_subpaths(), -1.0, 1.0)
            )
        else:
            src_handles = [[h.x(), h.y()] for h in src.handles]
            dst.set_handles(mirror.mirror_handles(src_handles))
        dst.set_text(src.get_text())
        dst.update()

    def apply_mirror_for(self, items):
        """Mirror each linked item onto its partner (loop-guarded).

        Partners that are themselves in ``items`` are skipped so a both-sides
        edit does not fight itself. No-op when nothing is linked.
        """
        if self._mirroring or not self._has_mirror_links:
            return
        self._mirroring = True
        try:
            edited = set(items)
            for item in items:
                partner = self.get_mirror_partner(item)
                if partner is None or partner in edited:
                    continue
                self._mirror_item_to(item, partner)
        finally:
            self._mirroring = False

    def _clean_dangling_mirrors(self):
        """Drop mirror ids that no longer point at an existing item."""
        items = self.get_picker_items()
        ids = set(item.item_id for item in items if item.item_id)
        for item in items:
            if item.mirror_id and item.mirror_id not in ids:
                mgear.log(
                    "anim_picker: dropped a dangling mirror link on load",
                    mgear.sev_warning,
                )
                item.mirror_id = None
        self._recompute_mirror_links()

    # -- viewport pins (HUD overlay) ------------------------------------
    def _recompute_pinned_flag(self):
        """Refresh the cached "any pinned item?" flag (on toggle / load)."""
        self._has_pinned_items = any(
            item.pinned for item in self.get_picker_items()
        )

    def _viewport_size(self):
        """Return the viewport ``(width, height)`` for the overlay math."""
        return (self.viewport().width(), self.viewport().height())

    def _update_pinned_items(self):
        """Lock each pinned item to its viewport anchor (constant screen spot).

        A pinned item ignores the view transform for *drawing* (constant size)
        but still lives at a scene point that pans with the canvas; this maps
        its 3x3 anchor + pixel offset to the current viewport and writes the
        item's scene position, so it stays fixed to the viewport through pan /
        zoom / resize. A no-op when nothing is pinned.
        """
        if self._has_pinned_items:
            size = self._viewport_size()
            # Scene accessor (no draw-order reverse) since order is irrelevant
            # to repositioning; runs per pan / zoom frame while pins exist.
            for item in self.scene().get_picker_items():
                if not item.pinned:
                    continue
                px, py = overlay.anchor_point(size, item.anchor, item.offset)
                item.setPos(self.mapToScene(int(round(px)), int(round(py))))
        # During a pan / zoom, drop the mask so the full window shows and is
        # not reshaped every frame (avoids the glitch); re-apply it at rest.
        self._notify_or_suspend_passthrough()

    def _notify_or_suspend_passthrough(self):
        """Suspend the mask mid-gesture, else re-apply it at rest.

        During a pan / zoom / wheel the window shape is dropped (the full UI
        comes back, no per-frame reshape); when not moving (fit / resize /
        load / release) the mask is re-applied.
        """
        if self.pan_active or self.zoom_active or self._wheel_zooming:
            self._suspend_passthrough()
        else:
            self._notify_passthrough()

    def _notify_passthrough(self):
        """Ask the window to (re-)apply its click-through mask now.

        A cheap no-op when the opacity-passthrough mode is not active.
        """
        window = self.main_window
        update = getattr(window, "update_passthrough_mask", None)
        if update is not None:
            update()

    def _suspend_passthrough(self):
        """Ask the window to drop its click mask for the duration of a gesture.

        A cheap no-op when the opacity-passthrough mode is not active.
        """
        window = self.main_window
        suspend = getattr(window, "suspend_passthrough_mask", None)
        if suspend is not None:
            suspend()

    # -- conditional visibility -----------------------------------------
    def _recompute_conditional_flag(self):
        """Refresh the cached visibility gates (on edit / load).

        Two cheap flags keep ``refresh_item_visibility`` a no-op when nothing
        needs it: any item with a visibility condition, and any checkbox that
        master-controls a group.
        """
        items = self.get_picker_items()
        self._has_conditional_items = any(
            item.has_visibility_condition() for item in items
        )
        self._has_group_controllers = any(
            item.controls_group() for item in items
        )

    def _group_hidden_items(self):
        """Return the set of items a group controller currently hides.

        Resolves each group-controller checkbox to whether it shows its group
        (checked XOR invert); an item is hidden when its group is controlled
        and currently not shown. Multiple controllers for one group apply in
        item order (last-applied wins, deterministic).
        """
        if not self._has_group_controllers:
            return set()
        shown = {}
        for item in self.get_picker_items():
            target = item.controls_group()
            if target:
                shown[target] = item.group_shows()
        if not shown:
            return set()
        hidden = set()
        for item in self.get_picker_items():
            group = item.get_group()
            if group and shown.get(group) is False:
                hidden.add(item)
        return hidden

    def refresh_item_visibility(self):
        """Show / hide each item for the current zoom, rig state, and groups.

        Mirrors ``_update_pinned_items``: the view owns *when* (called from the
        zoom / pan / fit hooks, the selection / hover callbacks, and a group
        toggle) and computes the zoom + group gates once, while each item owns
        its own decision. An item is visible only when its controlling group is
        shown AND its own condition passes. A no-op when nothing is conditioned
        or group-controlled.
        """
        if not (self._has_conditional_items or self._has_group_controllers):
            return
        zoom = abs(self.viewportTransform().m11())
        hidden = self._group_hidden_items()
        for item in self.scene().get_picker_items():
            item.evaluate_visibility(zoom, item in hidden)
        # Items were shown / hidden (e.g. a checkbox group toggled) -- realign
        # the passthrough mask (or suspend it mid-zoom) so they appear at once.
        self._notify_or_suspend_passthrough()

    def refresh_widget_states(self):
        """Re-read every interactive widget's bound attribute into its display.

        The checkbox / slider / 2D-slider items re-sync their drawn state from
        the rig; ``refresh_widget_state`` is a cheap no-op on non-widget items.
        Used by the mouse-enter (hover) refresh so a manual channel change is
        reflected without a selection / time callback. Read-only, never writes.
        """
        for item in self.scene().get_picker_items():
            item.refresh_widget_state()

    def set_item_pinned(self, item, state, anchor=None):
        """Pin / unpin an item and reposition it (default anchor = its region).

        Args:
            item (PickerItem): the item to pin or unpin.
            state (bool): pin when True, unpin when False.
            anchor (str, optional): explicit anchor code; when pinning without
                one, the item's current on-screen region is used (least
                surprising) and the residual is stored as the offset.
        """
        if state:
            view_pt = self.mapFromScene(item.pos())
            size = self._viewport_size()
            point = (view_pt.x(), view_pt.y())
            if anchor is None:
                anchor = overlay.nearest_anchor(size, point)
            item.set_anchor(anchor)
            item.set_offset(overlay.offset_from_anchor(size, anchor, point))
        item.set_pinned(state)
        self._recompute_pinned_flag()
        self._update_pinned_items()
        # Pins are excluded from the canvas extent, so toggling one may shrink
        # or grow the scrollable bounds.
        self._update_scene_rect()

    def begin_pin_drag(self, item, scene_grab):
        """Record a pinned item's grab delta at the start of an offset drag."""
        grab = self.mapFromScene(scene_grab)
        anchor_pt = self.mapFromScene(item.pos())
        item._pin_drag_delta = (
            anchor_pt.x() - grab.x(),
            anchor_pt.y() - grab.y(),
        )

    def update_pin_drag(self, item, scene_pos):
        """Update a pinned item's anchor / offset from an in-progress drag."""
        grab = self.mapFromScene(scene_pos)
        px = grab.x() + item._pin_drag_delta[0]
        py = grab.y() + item._pin_drag_delta[1]
        size = self._viewport_size()
        anchor = overlay.nearest_anchor(size, (px, py))
        item.set_anchor(anchor)
        item.set_offset(overlay.offset_from_anchor(size, anchor, (px, py)))
        self._update_pinned_items()
        self._notify_item_transform()

    def _draw_bg_marquee(self, painter):
        """Draw the background-selection marquee rectangle, if active."""
        if self._bg_marquee_origin is None or self._bg_marquee_current is None:
            return
        rect = QtCore.QRectF(
            self._bg_marquee_origin, self._bg_marquee_current
        ).normalized()
        pen = QtGui.QPen(
            QtGui.QColor(255, 200, 40, 200), 0, QtCore.Qt.DashLine
        )
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(rect)

    def background_options(self):
        tabWidget = self.parent().parent()
        # Delete old window
        if self.bg_ui:
            try:
                self.bg_ui.close()
                self.bg_ui.deleteLater()
            except Exception:
                pass
        self.bg_ui = basic.BackgroundOptionsDialog(tabWidget, self)
        self.bg_ui.show()
        self.bg_ui.raise_()

    def set_background_event(self, event=None):
        """Set background image pick dialog window"""
        # Open file dialog
        img_dir = basic.get_images_folder_path()
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Pick a background", img_dir
        )

        # Filter return result (based on qt version)
        if isinstance(file_path, tuple):
            file_path = file_path[0]

        # Abort on cancel
        if not file_path:
            return

        # Set background
        self.set_background(file_path)

    def reset_background_event(self, event=None):
        """Reset background to default (clear all layers)"""
        self.clear_backgrounds()

    def remove_background_layer(self, index):
        """Remove the layer at index and refit the canvas."""
        if 0 <= index < len(self.background_layers):
            self.background_layers.pop(index)
            self._update_scene_size()

    def move_background_layer(self, index, new_index):
        """Move the layer at index to new_index (changes draw order)."""
        count = len(self.background_layers)
        if not (0 <= index < count and 0 <= new_index < count):
            return
        loaded = self.background_layers.pop(index)
        self.background_layers.insert(new_index, loaded)
        self._update_scene_size()

    def set_layer_position(self, index, x, y):
        """Set the center position of the layer at index."""
        if 0 <= index < len(self.background_layers):
            self.background_layers[index].layer.position = [x, y]
            self._update_scene_size()

    def resize_background_image(
        self, index, width, height, keepAspectRatio=False, auto_update=True
    ):
        """Resize the draw size of the layer at index.

        Args:
            index (int): layer index.
            width (int): desired width.
            height (int): desired height.
            keepAspectRatio (bool, optional): keep the image's natural aspect.
            auto_update (bool, optional): refit the scene view.
        """
        if not (0 <= index < len(self.background_layers)):
            return
        loaded = self.background_layers[index]
        if keepAspectRatio and loaded.image is not None:
            natural = loaded.image.size()
            nat_w = natural.width() or 1
            nat_h = natural.height() or 1
            current_w, current_h = self._layer_draw_size(loaded)
            if width != current_w:
                height = int(round(width * nat_h / float(nat_w)))
            elif height != current_h:
                width = int(round(height * nat_w / float(nat_h)))
        loaded.layer.size = [int(width), int(height)]
        if auto_update:
            self._update_scene_size()

    def set_background_width(self, index, width, keepAspectRatio=True):
        """Set the draw width of the layer at index."""
        if not (0 <= index < len(self.background_layers)):
            return
        _, current_height = self._layer_draw_size(self.background_layers[index])
        self.resize_background_image(
            index, width, current_height, keepAspectRatio=keepAspectRatio
        )

    def set_background_height(self, index, height, keepAspectRatio=True):
        """Set the draw height of the layer at index."""
        if not (0 <= index < len(self.background_layers)):
            return
        current_width, _ = self._layer_draw_size(self.background_layers[index])
        self.resize_background_image(
            index, current_width, height, keepAspectRatio=keepAspectRatio
        )

    def get_background_layers(self):
        """Return the ordered list of _LoadedBackground (back to front)."""
        return self.background_layers

    def get_background_size(self):
        """Return the union size of all layers as a Qt.QSize."""
        bounding = self._bounding_rect
        if bounding is None:
            return QtCore.QSize(0, 0)
        return QtCore.QSize(
            int(round(bounding.width())), int(round(bounding.height()))
        )

    def get_background(self, index):
        """Return the loaded image for the layer at index, or None."""
        if 0 <= index < len(self.background_layers):
            return self.background_layers[index].image
        return None

    def clear(self):
        """Clear view, by replacing scene with a new one"""
        old_scene = self.scene()
        self.setScene(OrderedGraphicsScene(parent=self))
        old_scene.deleteLater()
        self._has_mirror_links = False
        self._has_pinned_items = False
        self._has_conditional_items = False
        self._has_group_controllers = False

    def get_picker_items(self):
        """Return scene picker items in proper order (back to front)"""
        items = []
        for item in list(self.scene().items()):
            # Skip non picker graphic items
            if not isinstance(item, picker_widgets.PickerItem):
                continue

            # Add picker item to filtered list
            items.append(item)

        # Reverse list order (to return back to front)
        items.reverse()

        return items

    def get_data(self):
        """Return view data"""
        data = {}

        # Add background layers to data (new composite schema)
        backgrounds = background_model.layers_to_data(
            [loaded.layer for loaded in self.background_layers]
        )
        if backgrounds:
            data["backgrounds"] = backgrounds

        # Add items to data
        items = []
        for item in self.get_picker_items():
            items.append(item.get_data())
        if items:
            data["items"] = items

        return data

    def set_data(self, data):
        """Set/load view data"""
        self.clear()

        # Set background layers (accepts the new backgrounds list and the
        # legacy single background/background_size keys).
        self.set_backgrounds(background_model.layers_from_view_data(data))

        # Add items to view
        for item_data in data.get("items", []):
            item = self.add_picker_item()
            item.set_data(item_data)

        # Now that every item exists, drop any mirror link whose partner is
        # missing (resolve pairs lazily via item ids at edit time).
        self._clean_dangling_mirrors()

        # Record whether any item is pinned, then size the scene (pins are
        # excluded from the extent) and lock the pins to their anchors.
        self._recompute_pinned_flag()
        self._update_scene_size()
        self._update_pinned_items()

        # Record whether any item is conditioned, then apply the initial
        # show/hide for the loaded zoom + rig state.
        self._recompute_conditional_flag()
        self.refresh_item_visibility()

        # Baseline the undo diff to the freshly-loaded item set (a load is not
        # itself an undoable edit).
        self._reset_undo_baseline()

    def drawBackground(self, painter, rect):
        """Draw the tab's background image layers (back to front)"""
        # Run default method
        result = QtWidgets.QGraphicsView.drawBackground(self, painter, rect)

        # Draw each layer from its cached geometry, culling those outside the
        # exposed paint region. No per-paint allocation or recomputation.
        for loaded in self.background_layers:
            if loaded.image is None or loaded.rect is None:
                continue
            if not loaded.rect.intersects(rect):
                continue
            painter.drawImage(loaded.rect, loaded.image, loaded.src_rect)

        return result

    def drawForeground(self, painter, rect):
        """Default method override to draw origin axis in edit mode"""
        # Run default method
        result = QtWidgets.QGraphicsView.drawForeground(self, painter, rect)

        # Paint axis in edit mode
        if __EDIT_MODE__.get():
            self.draw_overlay_axis(painter, rect)
            # Item scale/rotate manipulator overlay: opt-in via the Transform
            # tool and suppressed while manipulating background layers.
            if not self.background_edit and self._transform_tool_active():
                self.item_manipulator.paint(painter)
            # Symmetry-axis guide + pink dotted outline on linked items,
            # shown once any mirror pair exists.
            if self.has_mirror_links():
                self._draw_mirror_axis(painter, rect)
                self._draw_mirror_links(painter)

        # Background layer manipulator overlay + selection marquee
        if self.background_edit:
            self.bg_manipulator.paint(painter)
            self._draw_bg_marquee(painter)

        return result

    def _draw_mirror_axis(self, painter, rect):
        """Draw the vertical symmetry-axis guide at ``mirror_axis_x``."""
        x = self.mirror_axis_x
        if not (rect.x() <= x <= rect.x() + rect.width()):
            return
        pen = QtGui.QPen(
            QtGui.QColor(255, 120, 180, 170), 0, QtCore.Qt.DashLine
        )
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawLine(
            QtCore.QLineF(x, rect.y(), x, rect.y() + rect.height())
        )

    def _draw_mirror_links(self, painter):
        """Draw a pink dotted outline matching each linked item's shape."""
        pen = QtGui.QPen(
            QtGui.QColor(255, 105, 180, 220), 0, QtCore.Qt.DotLine
        )
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        for item in self.get_picker_items():
            if item.mirror_id and item.polygon is not None:
                # Map the item's polygon outline into scene space so the guide
                # follows the actual shape (and its rotation), not a bbox.
                painter.drawPath(item.mapToScene(item.polygon.shape()))

    def draw_overlay_axis(self, painter, rect):
        """Draw x and y origin axis"""
        # Set Pen
        pen = QtGui.QPen(
            QtGui.QColor(160, 160, 160, 120), 1, QtCore.Qt.DashLine
        )
        painter.setPen(pen)

        # Get event rect in scene coordinates
        # Draw x line
        if rect.y() < 0 and (rect.height() - rect.y()) > 0:
            x_line = QtCore.QLine(rect.x(), 0, rect.width() + rect.x(), 0)
            painter.drawLine(x_line)

        # Draw y line
        if rect.x() < 0 and (rect.width() - rect.x()) > 0:
            y_line = QtCore.QLineF(0, rect.y(), 0, rect.height() + rect.y())
            painter.drawLine(y_line)

    def convert_picker_to_curves(self):
        """Convert the pickernodes from the view into maya curves for easier
        editing.

        Returns:
            n/a: n/a

        http://forum.mgear-framework.com/t/sharing-a-couple-of-functions-i-wrote-for-anim-picker/1717
        """
        data = self.main_window.get_character_data()

        tab_index = self.main_window.tab_widget.currentIndex()
        tab_name = self.main_window.tab_widget.tabText(tab_index)

        tab = None
        # only focus on the current tab
        for _tab in data["tabs"]:
            if _tab["name"] == tab_name:
                tab = _tab
        if not tab:
            cmds.warning("No data in picker tab: {}".format(tab_name))
            return

        # lets not create multiple picker group nodes
        if pm.objExists(PICKER_EXTRACTION_NAME):
            grp = pm.PyNode(PICKER_EXTRACTION_NAME)
        else:
            grp = pm.group(em=True, n=PICKER_EXTRACTION_NAME)
            attribute.lockAttribute(grp)

        # Delete a previous extraction group for this tab, matched by the
        # stored tab name rather than the node name: Maya may rename the group
        # (e.g. "default" -> "default1", or spaces -> "_"), so the node name is
        # not a reliable key.
        for existing in grp.listRelatives() or []:
            if (
                pm.hasAttr(existing, "tabName")
                and existing.tabName.get() == tab["name"]
            ):
                pm.delete(existing)
        picker_grp = pm.group(em=True, n=tab["name"], p=grp)
        # Store the real tab name so the round-trip does not depend on the
        # (possibly Maya-mangled) group node name.
        attribute.addAttribute(picker_grp, "tabName", "string", tab["name"])
        picker_grp.sy >> picker_grp.sx
        attribute.lockAttribute(
            picker_grp, ["tz", "rx", "ry", "rz", "sx", "sz", "v"]
        )

        # Create one image plane per background layer (composite backgrounds).
        # Accepts both the new backgrounds list and the legacy single keys.
        bg_layers = background_model.layers_from_view_data(tab["data"])
        if bg_layers:
            attribute.addAttribute(
                picker_grp,
                "backgroundAlpha",
                "float",
                0.5,
                minValue=0,
                maxValue=1,
            )
            for i, layer in enumerate(bg_layers):
                ip = pm.imagePlane(
                    n="{}_background_{}".format(tab["name"], i)
                )
                # Stack planes behind the curves and by index so the draw
                # order is recoverable on convert-back.
                ip[0].tz.set(-1 - i)
                ip[0].tx.set(layer.position[0])
                ip[0].ty.set(layer.position[1])
                ip[0].overrideEnabled.set(1)
                ip[0].overrideDisplayType.set(2)
                pm.parent(ip[0], picker_grp)

                picker_grp.backgroundAlpha >> ip[1].alphaGain
                if layer.size and layer.size[0] and layer.size[1]:
                    ip[1].width.set(layer.size[0])
                    ip[1].height.set(layer.size[1])
                ip[1].imageName.set(layer.path)

        if "items" in tab["data"]:
            for item in tab["data"]["items"]:
                handles = item["handles"]
                pos_x, pos_y = item["position"]
                rot_z = item["rotation"]

                if len(handles) > 2:
                    item_curve = pm.circle(
                        d=1, s=len(item["handles"]), ch=False
                    )[0]

                    for i, (x, y) in enumerate(handles):
                        item_curve.getShape().controlPoints[i].set(x, y, 0)
                    item_curve.getShape().controlPoints[i + 1].set(
                        handles[0][0], handles[0][1], 0
                    )

                # special case for circles
                elif len(handles) == 2:
                    item_curve = pm.curve(
                        p=[
                            [handles[0][0], handles[0][1], 0.0],
                            [handles[1][0], handles[1][1], 0.0],
                        ],
                        d=1,
                    )
                    poci = pm.createNode("pointOnCurveInfo")
                    item_curve.getShape().worldSpace >> poci.inputCurve
                    curve_len = pm.arclen(item_curve, ch=True)

                    display_curve = pm.circle(d=3, s=6, ch=False)[0]
                    pm.parent(display_curve, item_curve)
                    display_curve.getShape().overrideEnabled.set(1)
                    display_curve.getShape().overrideDisplayType.set(2)
                    display_curve.inheritsTransform.set(0)

                    curve_len.arcLength >> display_curve.sx
                    curve_len.arcLength >> display_curve.sy
                    curve_len.arcLength >> display_curve.sz
                    poci.position >> display_curve.t

                pm.parent(item_curve, picker_grp)

                q_color = QtGui.QColor(*item["color"])
                attribute.addColorAttribute(
                    item_curve, "color", q_color.getRgbF()[:3]
                )
                attribute.addAttribute(
                    item_curve,
                    "alpha",
                    "long",
                    item["color"][3],
                    minValue=0,
                    maxValue=255,
                )

                item_curve.t.set(pos_x, pos_y, 0)
                item_curve.rz.set(rot_z)
                item_curve.displayHandle.set(1)
                item_curve.getShape().dispCV.set(1)
                item_curve.overrideEnabled.set(1)
                item_curve.overrideRGBColors.set(1)
                item_curve.color >> item_curve.overrideColorRGB
                item_curve.scalePivot >> item_curve.selectHandle
                attribute.lockAttribute(
                    item_curve, ["tz", "rx", "ry", "sz", "v"]
                )

                # this will save all the data that is not needed for display
                # purposes to an attr
                ignore_list = ("position", "rotation", "handles", "color")
                item_data = {}

                for key in item.keys():
                    if key not in ignore_list:
                        item_data[key] = item[key]

                if item_data:
                    attribute.addAttribute(
                        item_curve, "itemData", "string", json.dumps(item_data)
                    )
                    item_curve.itemData.set(lock=True)

    def delete_extraction_grp(self):
        """delete extraction group"""
        try:
            pm.delete(PICKER_EXTRACTION_NAME)
        except Exception as e:
            mgear.log(
                "anim_picker: failed to delete extraction group: "
                "{}".format(e),
                mgear.sev_warning,
            )

    def convert_curves_to_picker(self):
        """get the information from the created picker curves and reset the
        information on the picker data node the anim picker operates on
        """
        grp = pm.PyNode(PICKER_EXTRACTION_NAME)
        new_data = {"tabs": []}

        for tab_grp in grp.listRelatives():
            # Recover the real tab name (the group node may have been renamed
            # by Maya, e.g. "default" -> "default1").
            if pm.hasAttr(tab_grp, "tabName"):
                tab_name = tab_grp.tabName.get()
            else:
                tab_name = tab_grp.name()
            new_data["tabs"].append({"name": tab_name})
            new_data["tabs"][-1]["data"] = {"items": []}
            # Collect all background image planes under the tab group and
            # rebuild the composite backgrounds list. Draw order is recovered
            # from the plane depth (tz), which convert_picker_to_curves stacks
            # per layer index -- robust to Maya node renames.
            bg_pairs = []
            for child in tab_grp.listRelatives() or []:
                shape = child.getShape()
                if shape is None or shape.type() != "imagePlane":
                    continue
                bg_pairs.append((child, shape))
            # index 0 (backmost) was stacked at tz = -1, index 1 at -2, ...
            bg_pairs.sort(key=lambda pair: pair[0].tz.get(), reverse=True)

            bg_layers = []
            for transform, shape in bg_pairs:
                layer = background_model.BackgroundLayer()
                layer.path = shape.imageName.get()
                layer.position = [transform.tx.get(), transform.ty.get()]
                layer.size = [shape.width.get(), shape.height.get()]
                bg_layers.append(layer)
            if bg_layers:
                new_data["tabs"][-1]["data"][
                    "backgrounds"
                ] = background_model.layers_to_data(bg_layers)

            for item_curve in tab_grp.listRelatives():
                shape = item_curve.getShape()
                if shape is None or shape.type() == "imagePlane":
                    continue

                item_data = {}

                # color
                q_color = QtGui.QColor()
                q_color.setRgbF(*item_curve.color.get())
                q_color.setAlpha(item_curve.alpha.get())
                item_data["color"] = q_color.getRgb()

                # position and rotation
                item_piv = pm.dt.Point(
                    item_curve.getPivots(worldSpace=True)[0]
                )
                piv_offset = item_piv * item_curve.worldInverseMatrix.get()
                item_pos = item_piv * tab_grp.worldInverseMatrix.get()

                item_data["position"] = [item_pos.x, item_pos.y]
                item_data["rotation"] = item_curve.rz.get()

                # handles
                handles = []
                item_scale = [item_curve.sx.get(), item_curve.sy.get()]
                for cv in item_curve.cv:
                    x, y = cv.getPosition(space="object")[:2]
                    handles.append(
                        [
                            (x - piv_offset.x) * item_scale[0],
                            (y - piv_offset.y) * item_scale[1],
                        ]
                    )

                # if the first and last points are the same then ignore the
                # last one.
                if handles[0] == handles[-1]:
                    handles = handles[:-1]
                item_data["handles"] = handles

                if pm.hasAttr(item_curve, "itemData"):
                    item_data.update(json.loads(item_curve.itemData.get()))

                new_data["tabs"][-1]["data"]["items"].append(item_data)

        data_node = self.main_window.get_current_data_node()
        if not (data_node and data_node.exists()):
            return True
        data = self.main_window.get_character_data()
        # update original data to avoid deletion of the non edited tabs
        # Create a lookup dictionary for fast matching
        new_data_lookup = {d["name"]: d for d in new_data["tabs"] if "name" in d}

        # Surface converted tabs that don't match any current picker tab, so
        # the merge below does not silently drop their edited data.
        current_names = {
            d.get("name") for d in data.get("tabs", []) if "name" in d
        }
        for converted_name in new_data_lookup:
            if converted_name not in current_names:
                mgear.log(
                    "anim_picker: converted tab '{}' has no matching tab in "
                    "the current picker; its data was not applied".format(
                        converted_name
                    ),
                    mgear.sev_warning,
                )

        # Replace the matching dictionaries in data
        updated_data = {"tabs": []}
        updated_data["tabs"] = [
            new_data_lookup.get(d.get("name"), d) if "name" in d else d
            for d in data["tabs"]
        ]
        # Write through the DataNode chokepoint (JSON + version stamp +
        # lock handling all centralized in picker_node.py)
        data_node.set_data(updated_data)
        data_node.write_data(to_node=True)

        self.main_window.refresh()
