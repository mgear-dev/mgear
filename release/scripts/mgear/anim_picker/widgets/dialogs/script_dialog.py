"""Custom script / menu edit dialogs for the anim picker.

Extracted from picker_widgets.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.anim_picker.widgets import basic
from mgear.anim_picker.handlers import python_handlers


SCRIPT_DOC_HEADER = """
# Variable reference for custom script execution on pickers.
# Use the following variables in your code to access related data:
# __CONTROLS__ for picker item associated controls (will return sets and not content).
# __FLATCONTROLS__ for associated controls and control set content.
# __NAMESPACE__ for current picker namespace
# __INIT__ use 'if not' statement to avoid code execution on creation.
# __SELF__ to get access to the PickerItem() instace. (Change color, size, etc)

"""


class CustomScriptEditDialog(QtWidgets.QDialog):
    """Custom python script window (used for custom picker item
    action and context menu)
    """

    __TITLE__ = "Custom script"

    def __init__(self, parent=None, cmd=None, item=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.cmd = cmd
        self.picker_item = item

        self.apply = False
        self.setup()

    def setup(self):
        """Build/Setup the dialog window"""
        self.setWindowTitle(self.__TITLE__)

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add cmd txt field
        self.cmd_widget = QtWidgets.QTextEdit()
        if self.cmd:
            text = self.cmd
        else:
            text = SCRIPT_DOC_HEADER
        self.cmd_widget.setText(text)
        newCursor = self.cmd_widget.textCursor()
        newCursor.movePosition(QtGui.QTextCursor.End)
        self.cmd_widget.setTextCursor(newCursor)
        self.main_layout.addWidget(self.cmd_widget)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = basic.CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = basic.CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

        run_btn = basic.CallbackButton(callback=self.run_event)
        run_btn.setText("Run")
        btn_layout.addWidget(run_btn)

        self.resize(500, 600)

    def accept_event(self):
        """Accept button event"""
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        """Cancel button event"""
        self.apply = False
        self.close()

    def run_event(self):
        """Run event button"""
        cmd_str = str(self.cmd_widget.toPlainText())

        if self.picker_item:
            python_handlers.safe_code_exec(
                cmd_str, env=self.picker_item.get_exec_env()
            )
        else:
            python_handlers.safe_code_exec(cmd_str)

    def get_values(self):
        """Return dialog window result values"""
        cmd_str = str(self.cmd_widget.toPlainText())

        return cmd_str, self.apply

    @classmethod
    def get(cls, cmd=None, item=None):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls(cmd=cmd, item=item)
        win.exec_()
        win.raise_()
        return win.get_values()


class CustomMenuEditDialog(CustomScriptEditDialog):
    """Custom python script window for picker item context menu"""

    __TITLE__ = "Custom Menu"

    def __init__(self, parent=None, name=None, cmd=None, item=None):

        self.name = name
        CustomScriptEditDialog.__init__(
            self, parent=parent, cmd=cmd, item=item
        )

    def setup(self):
        """Add name field to default window setup"""
        # Run default setup
        CustomScriptEditDialog.setup(self)

        # Add name line edit
        name_layout = QtWidgets.QHBoxLayout(self)

        label = QtWidgets.QLabel()
        label.setText("Name")
        name_layout.addWidget(label)

        self.name_widget = QtWidgets.QLineEdit()
        if self.name:
            self.name_widget.setText(self.name)
        name_layout.addWidget(self.name_widget)

        self.main_layout.insertLayout(0, name_layout)

    def accept_event(self):
        """Accept button event, check for name"""
        if not self.name_widget.text():
            QtWidgets.QMessageBox.warning(
                self, "Warning", "You need to specify a menu name"
            )
            return

        self.apply = True

        self.accept()
        self.close()

    def get_values(self):
        """Return dialog window result values"""
        name_str = str(self.name_widget.text())
        cmd_str = str(self.cmd_widget.toPlainText())

        return name_str, cmd_str, self.apply

    @classmethod
    def get(cls, name=None, cmd=None, item=None):
        """
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        """
        win = cls(name=name, cmd=cmd, item=item)
        win.exec_()
        win.raise_()
        return win.get_values()
