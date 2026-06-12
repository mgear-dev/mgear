from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# python
import os

# dcc
import maya.cmds as cmds

# mgear
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

# debugging
# from PySide2 import QtGui
# from PySide2 import QtCore
# from PySide2 import QtWidgets

# module
from mgear.core import pyqt
from mgear.anim_picker.handlers import __EDIT_MODE__

# =============================================================================
# generic functions
# =============================================================================


def get_module_path():
    """Return the folder path for this module"""
    return os.path.dirname(os.path.abspath(__file__))


def get_images_folder_path():
    """Return path for package images folder"""
    # Get the path to this file
    module_path = os.path.dirname(get_module_path())
    return os.path.join(module_path, "images")


def promptAcceptance(parent, descriptionA, descriptionB):
    """Warn user, asking for permission

    Args:
        parent (QWidget): to be parented under
        descriptionA (str): info
        descriptionB (str): further info

    Returns:
        QtCore.Response: accept, deline, reject
    """
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setText(descriptionA)
    msgBox.setInformativeText(descriptionB)
    msgBox.setStandardButtons(
        QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
    )
    msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
    decision = msgBox.exec_()
    return decision


# =============================================================================
# Custom Widgets ---
# =============================================================================
class CallbackButton(QtWidgets.QPushButton):
    """Dynamic callback button"""

    def __init__(self, callback=None, *args, **kwargs):
        QtWidgets.QPushButton.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Connect event
        self.clicked.connect(self.click_event)

        # Set tooltip
        if hasattr(self.callback, "__doc__") and self.callback.__doc__:
            self.setToolTip(self.callback.__doc__)

    def click_event(self):
        if not self.callback:
            return
        self.callback(*self.args, **self.kwargs)


class CallbackComboBox(QtWidgets.QComboBox):
    """Dynamic combo box object"""

    def __init__(self, callback=None, status_tip=None, *args, **kwargs):
        QtWidgets.QComboBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        if status_tip:
            self.setStatusTip(status_tip)

        self.currentIndexChanged.connect(self.index_change_event)

    def index_change_event(self, index):
        if not self.callback:
            return
        self.callback(index=index, *self.args, **self.kwargs)


class CallBackSpinBox(QtWidgets.QSpinBox):
    def __init__(self, callback, value=0, min=0, max=9999, *args, **kwargs):
        QtWidgets.QSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set properties
        self.setRange(min, max)
        self.setValue(value)

        # Signals
        self.valueChanged.connect(self.valueChangedEvent)

    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)


class CallBackDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, callback, value=0, min=0, max=9999, *args, **kwargs):
        QtWidgets.QDoubleSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set properties
        self.setRange(min, max)
        self.setValue(value)

        # Signals
        self.valueChanged.connect(self.valueChangedEvent)

    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)


class CallbackLineEdit(QtWidgets.QLineEdit):
    def __init__(self, callback, text=None, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set properties
        if text:
            self.setText(text)

        # Signals
        self.returnPressed.connect(self.return_pressed_event)

    def return_pressed_event(self):
        """Will return text on return press"""
        self.callback(text=self.text(), *self.args, **self.kwargs)


class CallbackListWidget(QtWidgets.QListWidget):
    """Dynamic List Widget object"""

    def __init__(self, callback=None, *args, **kwargs):
        QtWidgets.QListWidget.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        self.itemDoubleClicked.connect(self.double_click_event)

        # Set selection mode to multi
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def double_click_event(self, item):
        if not self.callback:
            return
        self.callback(item=item, *self.args, **self.kwargs)


class CallbackCheckBoxWidget(QtWidgets.QCheckBox):
    """Dynamic CheckBox Widget object"""

    def __init__(
        self, callback=None, value=False, label=None, *args, **kwargs
    ):
        QtWidgets.QCheckBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set init state
        if value:
            self.setCheckState(QtCore.Qt.Checked)
        self.setText(label or "")

        self.toggled.connect(self.toggled_event)

    def toggled_event(self, value):
        if not self.callback:
            return
        self.kwargs["value"] = value
        self.callback(*self.args, **self.kwargs)


class CallbackRadioButtonWidget(QtWidgets.QRadioButton):
    """Dynamic callback radioButton"""

    def __init__(self, name_value, callback, checked=False):
        QtWidgets.QRadioButton.__init__(self)
        self.name_value = name_value
        self.callback = callback

        self.setChecked(checked)

        self.clicked.connect(self.click_event)

    def click_event(self):
        self.callback(self.name_value)


class CtrlListWidgetItem(QtWidgets.QListWidgetItem):
    """
    List widget item for influence list
    will handle checks, color feedbacks and edits
    """

    def __init__(self, index=0, text=None):
        QtWidgets.QListWidgetItem.__init__(self)

        self.index = index
        if text:
            self.setText(text)

    def setText(self, text):
        """Overwrite default setText with auto color status check"""
        # Skip if name hasn't changed
        if text == self.text():
            return None

        # Run default setText action
        QtWidgets.QListWidgetItem.setText(self, text)

        # Set color status
        self.set_color_status()

        return text

    def node(self):
        """Return a usable string for maya instead of a QString"""
        return str(self.text())

    def node_exists(self):
        """Will check that the node from "text" exists"""
        return cmds.objExists(self.node())

    def set_color_status(self):
        """Set the color to red/green based on node existence status"""
        color = QtGui.QColor()

        # Exists case
        if self.node_exists():
            # pale green
            color.setRgb(152, 251, 152)

        # Does not exists case
        else:
            # orange
            color.setRgb(255, 165, 0)

        brush = self.foreground()
        brush.setColor(color)
        self.setForeground(brush)


class BackgroundWidget(QtWidgets.QLabel):
    """QLabel widget to support background options for tabs."""

    def __init__(self, parent=None):
        QtWidgets.QLabel.__init__(self, parent)

        self.setBackgroundRole(QtGui.QPalette.Base)
        self.background = None

    def _assert_path(self, path):
        assert os.path.exists(path), "Could not find file {}".format(path)

    def resizeEvent(self, event):
        QtWidgets.QLabel.resizeEvent(self, event)
        self._set_stylesheet_background()

    def _set_stylesheet_background(self):
        """
        Will set proper sylesheet based on edit status to have
        fixed size background in edit mode and stretchable in anim mode
        """
        if not self.background:
            self.setStyleSheet("")
            return

        bg = self.background
        if __EDIT_MODE__.get():
            edit_css = "QLabel {background-image: url('{}'); background-repeat: no repeat;}".format(
                bg
            )
            self.setStyleSheet(edit_css)
        else:
            self.setStyleSheet("QLabel {border-image: url('{}');}".format(bg))

    def set_background(self, path=None):
        """Set character snapshot picture"""
        if not (path and os.path.exists(path)):
            path = None
            self.background = None
        else:
            self.background = str(path)

        # Use stylesheet rather than pixmap for proper resizing support
        self._set_stylesheet_background()

    def file_dialog(self):
        """Get file dialog window starting in default folder"""
        imgs_dir = get_images_folder_path()
        file_path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose picture", imgs_dir
        )
        # Filter return result (based on qt version)
        if isinstance(file_path, tuple):
            file_path = file_path[0]

        if not file_path:
            return

        return file_path


class SnapshotWidget(BackgroundWidget):
    """Top right character "snapshot" widget, to display character picture"""

    def __init__(self, parent=None):
        BackgroundWidget.__init__(self, parent)

        self.setFixedWidth(pyqt.dpi_scale(80))
        self.setFixedHeight(pyqt.dpi_scale(80))
        self.setScaledContents(True)

        self.set_background()

        self.setToolTip("Click here to Open About/Help window")

    def _get_default_snapshot(self, name="undefined"):
        """Return default snapshot"""
        # Define image path
        folder_path = get_images_folder_path()
        image_path = os.path.join(folder_path, "{}.png".format(name))

        # Assert path
        self._assert_path(image_path)

        return image_path

    def set_background(self, path=None):
        """Set character snapshot picture"""
        if not (path and os.path.exists(path)):
            path = self._get_default_snapshot()
            self.background = None
        else:
            self.background = path

        # Load image
        image = QtGui.QImage(path)
        self.setPixmap(QtGui.QPixmap.fromImage(image))

    def contextMenuEvent(self, event):
        """Right click menu options"""
        # Abort in non edit mode
        if not __EDIT_MODE__.get():
            return

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Add choose action
        choose_action = QtWidgets.QAction("Select Picture", None)
        choose_action.triggered.connect(self.select_image)
        menu.addAction(choose_action)

        # Add reset action
        reset_action = QtWidgets.QAction("Reset", None)
        reset_action.triggered.connect(self.reset_image)
        menu.addAction(reset_action)

        # Open context menu under mouse
        if not menu.isEmpty():
            menu.exec_(self.mapToGlobal(event.pos()))

    def select_image(self):
        """Pick/set snapshot image"""
        # Open file dialog
        file_name = self.file_dialog()

        # Abort on cancel
        if not file_name:
            return

        # Set picture
        self.set_background(file_name)

    def reset_image(self):
        """Reset snapshot image to default"""
        # Reset background
        self.set_background()

    def get_data(self):
        """Return snapshot picture path"""
        return self.background


class BackgroundOptionsDialog(QtWidgets.QDialog):
    """minimal ui for adjusting the background image"""

    def __init__(self, tabWidget, parent=None):
        super(BackgroundOptionsDialog, self).__init__(parent)
        self.setWindowTitle("Set background size")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.tabWidget = tabWidget
        self.keep_aspect_ratio = True

        if not self.tabWidget.currentWidget().get_background(0):
            cmds.warning("Current view has no background!")
            return None

        width_label = QtWidgets.QLabel("Width")
        self.width_box = QtWidgets.QSpinBox()
        self.width_box.setRange(1, 6000)
        height_label = QtWidgets.QLabel("Height")
        self.height_box = QtWidgets.QSpinBox()
        self.height_box.setRange(1, 6000)
        self.aspect_button = QtWidgets.QPushButton("Maintain Aspect Ratio")
        self.aspect_button.setCheckable(True)
        self.aspect_button.setChecked(True)
        self.reset_button = QtWidgets.QPushButton("Reset Size")

        self.main_layout = QtWidgets.QVBoxLayout(self)

        self.main_layout.addWidget(self.aspect_button)
        self.main_layout.addWidget(width_label)
        self.main_layout.addWidget(self.width_box)
        self.main_layout.addWidget(height_label)
        self.main_layout.addWidget(self.height_box)
        self.main_layout.addWidget(self.reset_button)

        self.update_ui_width_value()
        self.update_ui_height_value()

        self.connectSignals()

    def connectSignals(self):
        self.aspect_button.clicked.connect(self.toggle_aspect_value)
        self.width_box.editingFinished.connect(self.update_background_width)
        self.width_box.editingFinished.connect(self.update_ui_height_value)
        self.height_box.editingFinished.connect(self.update_background_height)
        self.height_box.editingFinished.connect(self.update_ui_width_value)
        self.reset_button.clicked.connect(self.reset_size)

    def update_ui_width_value(self, *args):
        if not self.keep_aspect_ratio:
            return
        size = self.tabWidget.currentWidget().get_background_size()
        self.width_box.setValue(size.width())

    def update_ui_height_value(self, *args):
        if not self.keep_aspect_ratio:
            return
        size = self.tabWidget.currentWidget().get_background_size()
        self.height_box.setValue(size.height())

    def update_background_width(self):
        gfx_view = self.tabWidget.currentWidget()
        gfx_view.set_background_width(
            int(self.width_box.text()), keepAspectRatio=self.keep_aspect_ratio
        )

    def update_background_height(self):
        gfx_view = self.tabWidget.currentWidget()
        gfx_view.set_background_height(
            int(self.height_box.text()), keepAspectRatio=self.keep_aspect_ratio
        )

    def toggle_aspect_value(self):
        self.keep_aspect_ratio = not self.keep_aspect_ratio

    def reset_size(self):
        path = self.tabWidget.currentWidget().background_image_path
        self.tabWidget.currentWidget().set_background(path)
        self.update_ui_width_value()
        self.update_ui_height_value()
