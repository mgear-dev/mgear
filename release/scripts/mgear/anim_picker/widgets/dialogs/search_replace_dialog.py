"""Search-and-replace dialog for the anim picker.

Extracted from picker_widgets.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import basic


class SearchAndReplaceDialog(QtWidgets.QDialog):
    """Search and replace dialog window"""

    __SEARCH_STR__ = "_L"
    __REPLACE_STR__ = "_R"

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.apply = False
        self.setup()

    def setup(self):
        """Build/Setup the dialog window"""
        self.setWindowTitle("Search And Replace")

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add line edits
        self.search_widget = QtWidgets.QLineEdit()
        self.search_widget.setText(self.__SEARCH_STR__)
        self.main_layout.addWidget(self.search_widget)

        self.replace_widget = QtWidgets.QLineEdit()
        self.replace_widget.setText(self.__REPLACE_STR__)
        self.main_layout.addWidget(self.replace_widget)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = basic.CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = basic.CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

        ok_btn.setFocus()

    def accept_event(self):
        """Accept button event"""
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        """Cancel button event"""
        self.apply = False
        self.close()

    def get_values(self):
        """Return field values and button choice"""
        search_str = str(self.search_widget.text())
        replace_str = str(self.replace_widget.text())
        if self.apply:
            SearchAndReplaceDialog.__SEARCH_STR__ = search_str
            SearchAndReplaceDialog.__REPLACE_STR__ = replace_str
        return search_str, replace_str, self.apply

    @classmethod
    def get(cls):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls()
        win.exec_()
        win.raise_()
        return win.get_values()
