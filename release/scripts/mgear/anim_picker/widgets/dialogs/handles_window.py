"""Handle-position editor window for the anim picker.

Extracted from picker_widgets.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import basic


class HandlesPositionWindow(QtWidgets.QMainWindow):
    """Whild window to edit picker item handles local positions"""

    __OBJ_NAME__ = "picker_item_handles_window"
    __TITLE__ = "Handles positions"

    __DEFAULT_WIDTH__ = 250
    __DEFAULT_HEIGHT__ = 300

    def __init__(self, parent=None, picker_item=None):
        QtWidgets.QMainWindow.__init__(self, parent=None)

        self.picker_item = picker_item

        # Run setup
        self.setup()

    def setup(self):
        """Setup window elements"""
        # Main window setting
        self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)
        self.resize(self.__DEFAULT_WIDTH__, self.__DEFAULT_HEIGHT__)

        # Create main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        self.setCentralWidget(self.main_widget)

        # Add content
        self.add_position_table()
        self.add_option_buttons()

        # Populate table
        self.populate_table()

    def add_position_table(self):
        self.table = QtWidgets.QTableWidget(self)

        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["X", "Y"])

        self.main_layout.addWidget(self.table)

    def add_option_buttons(self):
        """Add window option buttons"""
        # Refresh button
        self.refresh_button = basic.CallbackButton(callback=self.refresh_event)
        self.refresh_button.setText("Refresh")
        self.main_layout.addWidget(self.refresh_button)

    def refresh_event(self):
        """Refresh table event"""
        self.populate_table()

    def populate_table(self):
        """Populate table with X/Y handles position items"""
        # Clear table
        while self.table.rowCount():
            self.table.removeRow(0)

        # Abort if no pickeritem specified
        if not self.picker_item:
            return

        # Parse handles
        handles = self.picker_item.get_handles()
        for i in range(len(handles)):
            self.table.insertRow(i)
            spin_box = basic.CallBackDoubleSpinBox(
                callback=handles[i].setX, value=handles[i].x(), min=-999
            )
            self.table.setCellWidget(i, 0, spin_box)

            spin_box = basic.CallBackDoubleSpinBox(
                callback=handles[i].setY, value=handles[i].y(), min=-999
            )
            self.table.setCellWidget(i, 1, spin_box)

    def display_handles_index(self, status=True):
        """Display related picker handles index"""
        for handle in self.picker_item.get_handles():
            handle.enable_index_draw(status)

    def closeEvent(self, *args, **kwargs):
        self.display_handles_index(status=False)
        # Commit the handle-position edits made here as one editor undo step
        # (handles are part of the item serialization, so the snapshot diff
        # captures the change).
        view = None
        if self.picker_item is not None:
            view = self.picker_item.scene().parent()
        if view is not None and hasattr(view, "commit_edit"):
            view.commit_edit("Edit handle positions")
        return QtWidgets.QMainWindow.closeEvent(self, *args, **kwargs)

    def show(self, *args, **kwargs):
        """Override default show function to display related picker
        handles index
        """
        self.display_handles_index(status=True)
        return QtWidgets.QMainWindow.show(self, *args, **kwargs)
