"""Custom script / menu edit dialogs for the anim picker.

Extracted from picker_widgets.py during the Phase 2 decomposition.
"""

from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

from mgear.core import pycodeeditor
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

        # Modern Python code editor (line numbers, syntax highlight, smart
        # indent) from mgear.core. Create it first so the menu bar and the
        # font/indent toolbar can bind to it.
        self.cmd_widget = pycodeeditor.PythonCodeEditor()
        self.main_layout.setMenuBar(self._build_menu_bar())
        self.main_layout.addLayout(self._build_editor_toolbar())

        if self.cmd:
            text = self.cmd
        else:
            text = SCRIPT_DOC_HEADER
        self.cmd_widget.setPlainText(text)
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

    def _build_menu_bar(self):
        """Build the File / Edit / View menu bar bound to the editor."""
        editor = self.cmd_widget
        menu_bar = QtWidgets.QMenuBar(self)

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("New", self._file_new)
        file_menu.addAction("Open...", self._file_open)
        file_menu.addAction("Save As...", self._file_save)

        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Undo", editor.undo)
        edit_menu.addAction("Redo", editor.redo)
        edit_menu.addSeparator()
        edit_menu.addAction("Cut", editor.cut)
        edit_menu.addAction("Copy", editor.copy)
        edit_menu.addAction("Paste", editor.paste)
        edit_menu.addAction("Select All", editor.selectAll)
        edit_menu.addSeparator()
        edit_menu.addAction(
            "Convert Indentation to Spaces",
            editor.convert_indentation_to_spaces,
        )

        view_menu = menu_bar.addMenu("View")
        self.show_ws_action = view_menu.addAction("Show Indentation")
        self.show_ws_action.setCheckable(True)
        self.show_ws_action.setChecked(editor.show_whitespace())
        self.show_ws_action.toggled.connect(editor.set_show_whitespace)

        return menu_bar

    def _file_new(self):
        """Reset the editor to the documentation header."""
        self.cmd_widget.setPlainText(SCRIPT_DOC_HEADER)

    def _file_open(self):
        """Load a python file into the editor."""
        path, _flt = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open script", "", "Python (*.py);;All Files (*)"
        )
        if not path:
            return
        with open(path, "r") as script_file:
            self.cmd_widget.setPlainText(script_file.read())

    def _file_save(self):
        """Write the editor contents to a python file."""
        path, _flt = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save script", "", "Python (*.py);;All Files (*)"
        )
        if not path:
            return
        with open(path, "w") as script_file:
            script_file.write(self.cmd_widget.toPlainText())

    def _build_editor_toolbar(self):
        """Build the font / indentation controls row bound to the editor."""
        editor = self.cmd_widget
        layout = QtWidgets.QHBoxLayout()

        layout.addWidget(QtWidgets.QLabel("Font"))
        self.font_combo = QtWidgets.QFontComboBox()
        self.font_combo.setFontFilters(
            QtWidgets.QFontComboBox.MonospacedFonts
        )
        self.font_combo.setCurrentFont(editor.font())
        self.font_combo.currentFontChanged.connect(self._editor_font_changed)
        layout.addWidget(self.font_combo)

        self.font_size_sb = QtWidgets.QSpinBox()
        self.font_size_sb.setRange(6, 48)
        self.font_size_sb.setValue(editor.font().pointSize())
        self.font_size_sb.valueChanged.connect(self._editor_font_changed)
        layout.addWidget(self.font_size_sb)

        layout.addSpacing(10)
        layout.addWidget(QtWidgets.QLabel("Indent"))
        self.indent_mode_cb = QtWidgets.QComboBox()
        self.indent_mode_cb.addItems(["Spaces", "Tabs"])
        self.indent_mode_cb.setCurrentIndex(
            0 if editor.use_spaces() else 1
        )
        self.indent_mode_cb.currentIndexChanged.connect(
            self._editor_indent_changed
        )
        layout.addWidget(self.indent_mode_cb)

        self.indent_width_sb = QtWidgets.QSpinBox()
        self.indent_width_sb.setRange(1, 8)
        self.indent_width_sb.setValue(editor.indent_width())
        self.indent_width_sb.valueChanged.connect(
            self._editor_indent_changed
        )
        layout.addWidget(self.indent_width_sb)

        layout.addStretch()
        return layout

    def _editor_font_changed(self, *args):
        """Apply the toolbar font family/size to the editor."""
        self.cmd_widget.set_editor_font(
            self.font_combo.currentFont().family(),
            self.font_size_sb.value(),
        )

    def _editor_indent_changed(self, *args):
        """Apply the toolbar indentation mode/width to the editor."""
        self.cmd_widget.set_use_spaces(self.indent_mode_cb.currentIndex() == 0)
        self.cmd_widget.set_indent_width(self.indent_width_sb.value())

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
