"""Tab widget with picker context menu for the anim picker.

Extracted from gui.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.view import GraphicViewWidget
from mgear.anim_picker.handlers import __EDIT_MODE__


def tab_data_entry(name, view):
    """Return the serialized ``{"name", "data"}`` entry for one tab view.

    The single authority for a tab's on-disk shape, so the tabbed and tiled
    presentations serialize identically.

    Args:
        name (str): the tab name.
        view (GraphicViewWidget): the tab's picker view.

    Returns:
        dict: ``{"name": str, "data": dict}``.
    """
    return {"name": str(name), "data": view.get_data()}


class ContextMenuTabWidget(QtWidgets.QTabWidget):
    """Custom tab widget with specific context menu support"""

    def __init__(self, parent, main_window=None, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, parent, *args, **kwargs)
        self.main_window = main_window
        # Drag-to-reorder tabs (edit mode only, matching the Move menu). The
        # order is the widget's own tab order, already serialized positionally
        # by get_data, so a reorder persists with no extra work.
        self.setMovable(__EDIT_MODE__.get())

    def contextMenuEvent(self, event):
        """Right click menu options"""
        # Abort out of edit mode
        if not __EDIT_MODE__.get():
            return

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Build context menu
        rename_action = QtWidgets.QAction("Rename", None)
        rename_action.triggered.connect(self.rename_event)
        menu.addAction(rename_action)

        add_action = QtWidgets.QAction("Add Tab", None)
        add_action.triggered.connect(self.add_tab_event)
        menu.addAction(add_action)

        remove_action = QtWidgets.QAction("Remove Tab", None)
        remove_action.triggered.connect(self.remove_tab_event)
        menu.addAction(remove_action)

        move_forward_action = QtWidgets.QAction("Move Tab >>>", None)
        move_forward_action.triggered.connect(self.move_forward_tab_event)
        menu.addAction(move_forward_action)

        move_back_action = QtWidgets.QAction("Move Tab <<<", None)
        move_back_action.triggered.connect(self.move_back_tab_event)
        menu.addAction(move_back_action)

        # Open context menu under mouse
        menu.exec_(self.mapToGlobal(event.pos()))

    def fit_contents(self):
        """Will resize views content to match views size"""
        for i in range(self.count()):
            widget = self.widget(i)
            if not isinstance(widget, GraphicViewWidget):
                continue
            widget.fit_scene_content()

    def move_back_tab_event(self):
        current_index = self.currentIndex()
        if current_index > 0:
            self.tabBar().moveTab(current_index, current_index - 1)
            self.setCurrentIndex(current_index - 1)

    def move_forward_tab_event(self):
        current_index = self.currentIndex()
        if current_index < self.count() - 1:
            self.tabBar().moveTab(current_index, current_index + 1)
            self.setCurrentIndex(current_index + 1)

    def rename_event(self):
        """Will open dialog to rename tab"""
        # Get current tab index
        index = self.currentIndex()

        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Tab name",
            "New name",
            QtWidgets.QLineEdit.Normal,
            self.tabText(index),
        )
        if not (ok and name):
            return

        # Update influence name
        self.setTabText(index, name)

    def add_tab_event(self):
        """Will open dialog to get tab name and create a new tab"""
        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create new tab", "Tab name", QtWidgets.QLineEdit.Normal, ""
        )
        if not (ok and name):
            return

        # Add tab
        self.addTab(GraphicViewWidget(main_window=self.main_window), name)

        # Set new tab active
        self.setCurrentIndex(self.count() - 1)

    def remove_tab_event(self):
        """Will remove tab from widget"""
        # Get current tab index
        index = self.currentIndex()

        # Open confirmation
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete",
            "Delete tab '{}'?".format(self.tabText(index)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.No:
            return

        # Remove tab
        self.removeTab(index)

    def get_namespace(self):
        """Return data_node namespace"""
        # Lazy import to avoid a circular import with main_window.py
        from mgear.anim_picker.main_window import MainDockWindow

        # Proper parent
        if self.main_window and isinstance(self.main_window, MainDockWindow):
            return self.main_window.get_current_namespace()

        return None

    def get_current_picker_items(self):
        """Return all picker items for current active tab"""
        return self.currentWidget().get_picker_items()

    def get_all_picker_items(self):
        """Returns all picker items for all tabs"""
        items = []
        for i in range(self.count()):
            items.extend(self.widget(i).get_picker_items())
        return items

    def borrow_views(self):
        """Detach every view page for temporary display elsewhere (tiled view).

        Returns an ordered ``[(name, view), ...]`` snapshot and empties the tab
        widget without deleting the views (``removeTab`` reparents them). Pair
        with :meth:`restore_views` to put them back in order.

        Returns:
            list: ``(name, GraphicViewWidget)`` pairs in tab order.
        """
        snapshot = []
        for i in range(self.count()):
            snapshot.append((str(self.tabText(i)), self.widget(i)))
        # Remove from the end so indices stay valid; views survive removeTab.
        for i in reversed(range(self.count())):
            self.removeTab(i)
        return snapshot

    def restore_views(self, snapshot):
        """Re-attach borrowed views as tabs, in order.

        Args:
            snapshot (list): ``(name, view)`` pairs from :meth:`borrow_views`.
        """
        for name, view in snapshot:
            self.addTab(view, name)

    def get_data(self):
        """Will return all tabs data"""
        return [
            tab_data_entry(self.tabText(i), self.widget(i))
            for i in range(self.count())
        ]

    def set_data(self, data):
        """Will, set/load tabs data"""
        self.clear()
        for tab in data:
            view = GraphicViewWidget(
                namespace=self.get_namespace(), main_window=self.main_window
            )
            # changed name to default1 as maya wont let you make a group called
            # 'default' for curve extraction.
            self.addTab(view, tab.get("name", "default1"))

            tab_content = tab.get("data", None)
            if tab_content:
                view.set_data(tab_content)
