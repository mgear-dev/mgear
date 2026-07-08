"""Tab widget with picker context menu for the anim picker.

Extracted from gui.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.view import GraphicViewWidget
from mgear.anim_picker.handlers import __EDIT_MODE__


class ContextMenuTabWidget(QtWidgets.QTabWidget):
    """Custom tab widget with specific context menu support"""

    def __init__(self, parent, main_window=None, *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, parent, *args, **kwargs)
        self.main_window = main_window

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

    def get_data(self):
        """Will return all tabs data"""
        data = []
        for i in range(self.count()):
            name = str(self.tabText(i))
            tab_data = self.widget(i).get_data()
            data.append({"name": name, "data": tab_data})
        return data

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
