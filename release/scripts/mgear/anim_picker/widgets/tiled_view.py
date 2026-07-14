"""Multi-tab tiled picker view.

``TiledPickerView`` shows every picker tab at once, tiling the *borrowed*
``GraphicViewWidget`` instances (see ``ContextMenuTabWidget.borrow_views``) in a
grid, a vertical stack, or a horizontal row. It owns no picker data -- the tab
widget stays the single source of truth -- it only re-parents the live views for
display and hands them back on demand.

The views are laid out in nested ``QSplitter``s, so the dividers are minimal and
draggable and the user configures each picker's relative space; clicking into a
view marks it the active picker so per-view actions (fit, add-item) have an
unambiguous target. The grid row/column count comes from the Qt-free
``tiled_layout.grid_shape``.
"""

from mgear.core import pyqt
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.tab_widget import tab_data_entry
from mgear.anim_picker.widgets.tiled_layout import grid_shape


# Tiled layout modes; the area adds "tabbed" (the default single-tab view).
MODE_TABBED = "tabbed"
MODE_GRID = "grid"
MODE_VERTICAL = "vertical"
MODE_HORIZONTAL = "horizontal"
TILED_MODES = (MODE_GRID, MODE_VERTICAL, MODE_HORIZONTAL)


class TiledPickerView(QtWidgets.QWidget):
    """Tiles borrowed picker views (grid / vertical / horizontal).

    The views are laid out in nested ``QSplitter``s so the dividers between
    sections are minimal and draggable -- the user resizes each picker's
    relative space directly. No per-cell title/frame is drawn (the views fill
    the splitter cells edge to edge).
    """

    # Minimal divider thickness between sections (px, dpi-scaled at use).
    _HANDLE = 3

    def __init__(self, area=None, parent=None):
        super(TiledPickerView, self).__init__(parent)
        self.area = area
        # Borrowed (name, view) pairs on display, the active view, the layout
        # mode, the grid column override (None = square), and the root splitter.
        self.pairs = []
        self.active = None
        self.mode = MODE_GRID
        self.columns = None
        self._root = None
        # Maps each view's viewport to its view so a click can set the active
        # cell before the view handles the event.
        self._viewport_to_view = {}

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    # ------------------------------------------------------------------
    def set_views(self, pairs=None, mode=MODE_GRID, columns=None):
        """Tile the views in ``mode``; ``pairs`` None re-tiles the current set.

        Args:
            pairs (list, optional): borrowed ``(name, view)`` pairs to display;
                None keeps the already-borrowed pairs (a re-layout).
            mode (str): grid / vertical / horizontal.
            columns (int, optional): grid column override (None = near-square).
        """
        if pairs is not None:
            self.pairs = list(pairs)
        self.mode = mode
        self.columns = columns
        # Keep the active view if it is still present, else default to first.
        views = [view for _name, view in self.pairs]
        if self.active not in views:
            self.active = views[0] if views else None
        self._rebuild()

    def take_views(self):
        """Detach and return the borrowed ``(name, view)`` pairs (for restore).

        The views are re-parented out of the splitters so they survive the
        teardown; the caller (the area) hands them back to the tab widget.
        """
        pairs = list(self.pairs)
        self._detach_views()
        self.pairs = []
        return pairs

    def views(self):
        """Return the borrowed views in display order."""
        return [view for _name, view in self.pairs]

    def active_view(self):
        """Return the active picker view (fallback: first, or None)."""
        if self.active is not None:
            return self.active
        return self.pairs[0][1] if self.pairs else None

    def fit_contents(self):
        """Fit every tiled view to its cell."""
        for _name, view in self.pairs:
            view.fit_scene_content()

    # ------------------------------------------------------------------
    def _columns_for_mode(self):
        """Return the fixed column count for the current mode (None = square)."""
        count = len(self.pairs)
        if self.mode == MODE_VERTICAL:
            return 1
        if self.mode == MODE_HORIZONTAL:
            return max(1, count)
        return self.columns

    def _detach_views(self):
        """Re-parent views out and drop the splitters, keeping views alive."""
        # Stop watching the viewports before the views leave (so a returned
        # view no longer routes clicks back into this tiled view).
        for viewport in self._viewport_to_view:
            viewport.removeEventFilter(self)
        self._viewport_to_view = {}
        for _name, view in self.pairs:
            view.setParent(None)
        if self._root is not None:
            self._root.setParent(None)
            self._root.deleteLater()
            self._root = None

    def _new_splitter(self, orientation):
        """Return a minimal, non-collapsible splitter."""
        splitter = QtWidgets.QSplitter(orientation)
        splitter.setHandleWidth(pyqt.dpi_scale(self._HANDLE))
        splitter.setChildrenCollapsible(False)
        return splitter

    def _add_view(self, splitter, view):
        """Add one borrowed view to ``splitter`` (shown + click-watched)."""
        view.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        view.setMinimumSize(pyqt.dpi_scale(60), pyqt.dpi_scale(60))
        splitter.addWidget(view)
        # ``removeTab`` (used to borrow it) leaves the page hidden; re-show it.
        view.show()
        viewport = view.viewport()
        self._viewport_to_view[viewport] = view
        viewport.installEventFilter(self)

    def _rebuild(self):
        """Rebuild the nested splitters from the current pairs / mode."""
        self._detach_views()
        rows, cols = grid_shape(len(self.pairs), self._columns_for_mode())
        if not cols:
            return

        if self.mode == MODE_HORIZONTAL:
            root = self._new_splitter(QtCore.Qt.Horizontal)
            for _name, view in self.pairs:
                self._add_view(root, view)
            root.setSizes([1000] * root.count())
        elif self.mode == MODE_VERTICAL:
            root = self._new_splitter(QtCore.Qt.Vertical)
            for _name, view in self.pairs:
                self._add_view(root, view)
            root.setSizes([1000] * root.count())
        else:
            # Grid: a column of rows, each row a splitter of views. Both axes
            # are draggable.
            root = self._new_splitter(QtCore.Qt.Vertical)
            for r in range(rows):
                row = self._new_splitter(QtCore.Qt.Horizontal)
                for c in range(cols):
                    index = r * cols + c
                    if index >= len(self.pairs):
                        break
                    self._add_view(row, self.pairs[index][1])
                row.setSizes([1000] * row.count())
                root.addWidget(row)
            root.setSizes([1000] * root.count())

        self._root = root
        self._layout.addWidget(root)

    def _set_active(self, view):
        """Track the active picker (used by ``active_view`` for per-view acts).

        The inline panel / tool commands are rebound by the view's own
        ``_notify_item_selection`` on the same click, so nothing else fires
        here; there is no per-cell header to highlight.
        """
        self.active = view

    def eventFilter(self, obj, event):
        """Set the active view when a tiled view's viewport is pressed."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            view = self._viewport_to_view.get(obj)
            if view is not None:
                self._set_active(view)
        return super(TiledPickerView, self).eventFilter(obj, event)


class PickerTabArea(QtWidgets.QWidget):
    """Presents the picker tabs as either the tab widget or a tiled layout.

    The ``ContextMenuTabWidget`` remains the single owner of the views and the
    serialization authority; this area only swaps between the tabbed
    presentation and a ``TiledPickerView`` that borrows the live views. All
    state-sensitive accessors (active view, all views, data, fit) are routed
    here so callers work in either mode.
    """

    def __init__(self, tab_widget, main_window=None, parent=None):
        super(PickerTabArea, self).__init__(parent)
        self.tab_widget = tab_widget
        self.main_window = main_window
        self.mode = MODE_TABBED
        self.grid_columns = None

        self.tiled = TiledPickerView(area=self)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.tab_widget)
        self.stack.addWidget(self.tiled)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

    # ------------------------------------------------------------------
    def set_view_mode(self, mode):
        """Switch between "tabbed" and the tiled modes, moving views as needed.

        Args:
            mode (str): ``tabbed`` / ``grid`` / ``vertical`` / ``horizontal``.
        """
        if mode == self.mode:
            return
        was_tiled = self.mode in TILED_MODES
        now_tiled = mode in TILED_MODES

        if not was_tiled and now_tiled:
            # Tabbed -> tiled: borrow the views into the tiled view.
            snapshot = self.tab_widget.borrow_views()
            self.tiled.set_views(snapshot, mode, self.grid_columns)
            self.stack.setCurrentWidget(self.tiled)
        elif was_tiled and now_tiled:
            # Tiled -> tiled: just re-lay the already-borrowed views.
            self.tiled.set_views(mode=mode, columns=self.grid_columns)
        elif was_tiled and not now_tiled:
            # Tiled -> tabbed: hand the views back to the tab widget.
            pairs = self.tiled.take_views()
            self.tab_widget.restore_views(pairs)
            self.stack.setCurrentWidget(self.tab_widget)

        self.mode = mode

    def ensure_tabbed(self):
        """Return to the tabbed presentation (before any data operation)."""
        if self.mode != MODE_TABBED:
            self.set_view_mode(MODE_TABBED)

    def set_grid_columns(self, columns):
        """Set the grid column override (None = near-square); re-tile if grid."""
        self.grid_columns = columns
        if self.mode == MODE_GRID:
            self.tiled.set_views(mode=MODE_GRID, columns=columns)

    # -- state-sensitive accessors (work in either mode) ----------------
    def active_view(self):
        """Return the active picker view for per-view actions."""
        if self.mode == MODE_TABBED:
            return self.tab_widget.currentWidget()
        return self.tiled.active_view()

    def all_views(self):
        """Return every picker view, wherever it currently lives."""
        if self.mode == MODE_TABBED:
            return [
                self.tab_widget.widget(i)
                for i in range(self.tab_widget.count())
            ]
        return self.tiled.views()

    def get_data(self):
        """Return the ordered tab data, built from the current presentation."""
        if self.mode == MODE_TABBED:
            return self.tab_widget.get_data()
        return [
            tab_data_entry(name, view) for name, view in self.tiled.pairs
        ]

    def set_data(self, data):
        """Load tab data (always into the tab widget)."""
        self.ensure_tabbed()
        self.tab_widget.set_data(data)

    def clear(self):
        """Clear all tabs (in the tabbed presentation)."""
        self.ensure_tabbed()
        self.tab_widget.clear()

    def count(self):
        """Return the number of picker views."""
        return len(self.all_views())

    def fit_contents(self):
        """Fit every view to its area."""
        if self.mode == MODE_TABBED:
            self.tab_widget.fit_contents()
        else:
            self.tiled.fit_contents()

    def get_all_picker_items(self):
        """Return picker items across every view."""
        items = []
        for view in self.all_views():
            items.extend(view.get_picker_items())
        return items

    def get_current_picker_items(self):
        """Return picker items for the active view."""
        view = self.active_view()
        return view.get_picker_items() if view is not None else []
