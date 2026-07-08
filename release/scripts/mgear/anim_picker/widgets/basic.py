# python
import os

# dcc
import maya.cmds as cmds

# mgear
from mgear.vendor.Qt import QtGui
from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets

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
    """Layer manager for a tab's composite background.

    Lists the current tab's background layers and lets the user add, remove,
    reorder, reposition, and resize each layer. No fixed size cap (issue #108).
    """

    def __init__(self, tabWidget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Background layers")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.tabWidget = tabWidget
        self.keep_aspect_ratio = True
        # Guard to avoid write-back while the fields are being populated.
        self._syncing = False

        # Layer list + list actions
        self.layer_list = QtWidgets.QListWidget()
        self.add_button = QtWidgets.QPushButton("Add Layer")
        self.remove_button = QtWidgets.QPushButton("Remove Layer")
        self.up_button = QtWidgets.QPushButton("Move Up")
        self.down_button = QtWidgets.QPushButton("Move Down")

        # Per-layer fields
        self.aspect_button = QtWidgets.QPushButton("Maintain Aspect Ratio")
        self.aspect_button.setCheckable(True)
        self.aspect_button.setChecked(True)
        self.pos_x_box = QtWidgets.QSpinBox()
        self.pos_y_box = QtWidgets.QSpinBox()
        self.width_box = QtWidgets.QSpinBox()
        self.height_box = QtWidgets.QSpinBox()
        for box in (self.pos_x_box, self.pos_y_box):
            box.setRange(-1000000, 1000000)
        for box in (self.width_box, self.height_box):
            box.setRange(1, 1000000)

        self.build_layout()
        self.connectSignals()
        self.refresh_layer_list()

    def build_layout(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.layer_list)

        list_buttons = QtWidgets.QHBoxLayout()
        list_buttons.addWidget(self.add_button)
        list_buttons.addWidget(self.remove_button)
        list_buttons.addWidget(self.up_button)
        list_buttons.addWidget(self.down_button)
        self.main_layout.addLayout(list_buttons)

        self.main_layout.addWidget(self.aspect_button)
        form = QtWidgets.QFormLayout()
        form.addRow("X", self.pos_x_box)
        form.addRow("Y", self.pos_y_box)
        form.addRow("Width", self.width_box)
        form.addRow("Height", self.height_box)
        self.main_layout.addLayout(form)

    def connectSignals(self):
        self.add_button.clicked.connect(self.add_layer)
        self.remove_button.clicked.connect(self.remove_layer)
        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)
        self.layer_list.currentRowChanged.connect(self.on_selection_changed)
        self.aspect_button.clicked.connect(self.toggle_aspect_value)
        self.pos_x_box.editingFinished.connect(self.apply_position)
        self.pos_y_box.editingFinished.connect(self.apply_position)
        self.width_box.editingFinished.connect(self.apply_width)
        self.height_box.editingFinished.connect(self.apply_height)

    def gfx_view(self):
        """Return the current tab's graphics view (or None)."""
        return self.tabWidget.currentWidget()

    def current_index(self):
        """Return the selected layer index (-1 if none)."""
        return self.layer_list.currentRow()

    def refresh_layer_list(self):
        """Rebuild the layer list from the view, preserving the selection."""
        view = self.gfx_view()
        layers = view.get_background_layers() if view else []
        keep = self.current_index()

        self._syncing = True
        self.layer_list.clear()
        for loaded in layers:
            name = os.path.basename(loaded.layer.path or "layer")
            self.layer_list.addItem(name)
        # Select inside the guard so currentRowChanged is suppressed; the
        # explicit populate_fields() below then runs exactly once.
        if layers:
            row = keep if 0 <= keep < len(layers) else 0
            self.layer_list.setCurrentRow(row)
        self._syncing = False

        self.populate_fields()

    def populate_fields(self):
        """Load the selected layer's position/size into the fields."""
        view = self.gfx_view()
        layers = view.get_background_layers() if view else []
        index = self.current_index()
        has = 0 <= index < len(layers)
        for widget in (
            self.pos_x_box,
            self.pos_y_box,
            self.width_box,
            self.height_box,
            self.remove_button,
            self.up_button,
            self.down_button,
        ):
            widget.setEnabled(has)
        if not has:
            return

        layer = layers[index].layer
        self._syncing = True
        self.pos_x_box.setValue(int(layer.position[0]))
        self.pos_y_box.setValue(int(layer.position[1]))
        self.width_box.setValue(int(layer.size[0]))
        self.height_box.setValue(int(layer.size[1]))
        self._syncing = False

    def on_selection_changed(self, *args):
        if self._syncing:
            return
        self.populate_fields()

    def add_layer(self):
        view = self.gfx_view()
        if not view:
            return
        view.set_background_event()
        self.refresh_layer_list()
        count = self.layer_list.count()
        if count:
            self.layer_list.setCurrentRow(count - 1)

    def remove_layer(self):
        index = self.current_index()
        if index < 0:
            return
        self.gfx_view().remove_background_layer(index)
        self.refresh_layer_list()

    def move_up(self):
        index = self.current_index()
        if index <= 0:
            return
        self.gfx_view().move_background_layer(index, index - 1)
        self.refresh_layer_list()
        self.layer_list.setCurrentRow(index - 1)

    def move_down(self):
        index = self.current_index()
        if index < 0 or index >= self.layer_list.count() - 1:
            return
        self.gfx_view().move_background_layer(index, index + 1)
        self.refresh_layer_list()
        self.layer_list.setCurrentRow(index + 1)

    def toggle_aspect_value(self):
        self.keep_aspect_ratio = not self.keep_aspect_ratio

    def apply_position(self):
        if self._syncing:
            return
        index = self.current_index()
        if index < 0:
            return
        self.gfx_view().set_layer_position(
            index, self.pos_x_box.value(), self.pos_y_box.value()
        )

    def apply_width(self):
        if self._syncing:
            return
        index = self.current_index()
        if index < 0:
            return
        self.gfx_view().set_background_width(
            index, self.width_box.value(), keepAspectRatio=self.keep_aspect_ratio
        )
        # Reflect an aspect-adjusted height back into the fields.
        self.populate_fields()

    def apply_height(self):
        if self._syncing:
            return
        index = self.current_index()
        if index < 0:
            return
        self.gfx_view().set_background_height(
            index,
            self.height_box.value(),
            keepAspectRatio=self.keep_aspect_ratio,
        )
        self.populate_fields()
