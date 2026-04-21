
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mgear.cfxbits.xgenboost import guide
from mgear.cfxbits.xgenboost import xgen_handler
import mgear.cfxbits.xgenboost.ui_form as ui_form


class XgenBoostUI(QtWidgets.QDialog, ui_form.Ui_Form):

    """UI Widget
    """

    def __init__(self, parent=None):
        super(XgenBoostUI, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(XgenBoostUI, self).keyPressEvent(event)


class XgenBoost(MayaQWidgetDockableMixin, QtWidgets.QDialog):

    def __init__(self, parent=None):
        self.toolName = "xgenboost"
        super(XgenBoost, self).__init__(parent)

        self.ui = XgenBoostUI()
        self.init_ui()
        self.create_layout()
        self.create_connections()

    def init_ui(self):
        self.setWindowTitle("Xgen IGS 增强")
        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)

        self.resize(250, 250)

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)

    def create_connections(self):
        self.ui.xgen_description_pushButton.clicked.connect(
            self.set_description)
        self.ui.add_curve_pushButton.clicked.connect(
            self.draw_guide)
        self.ui.move_pushButton.clicked.connect(
            self.move_guide)

        self.ui.duplicate_pushButton.clicked.connect(self.duplicate)
        self.ui.duplicate_sym_pushButton.clicked.connect(self.duplicate_sym)

        # color buttons
        self.ui.orange_pushButton.clicked.connect(self.set_orange)
        self.ui.blue_pushButton.clicked.connect(self.set_blue)
        self.ui.green_pushButton.clicked.connect(self.set_green)
        self.ui.red_pushButton.clicked.connect(self.set_red)
        self.ui.pink_pushButton.clicked.connect(self.set_pink)
        self.ui.lightblue_pushButton.clicked.connect(self.set_light_blue)
        self.ui.yellow_pushButton.clicked.connect(self.set_yellow)

        # points number
        self.ui.sections_spinBox.valueChanged.connect(self.sections_change)

        # thickness
        self.ui.thickness_spinBox.valueChanged.connect(self.thickness_change)

        # # deformers
        # self.ui.smooth_pushButton.clicked.connect(self.smooth)

        # visibility
        self.ui.vis_hair_pushButton.clicked.connect(
            self.toggle_hair_visibility)
        self.ui.vis_guides_pushButton.clicked.connect(
            self.toggle_guides_visibility)
        self.ui.vis_scalp_pushButton.clicked.connect(
            self.toggle_scalp_visibility)

        self.ui.lock_length_checkBox.toggled.connect(self.lock_length)

    # Slots
    def set_description(self):
        description = xgen_handler.get_description_from_selection()
        if description:
            self.ui.xgen_description_lineEdit.setText(description.name())
            self.ui.xgen_description_lineEdit.clearFocus()
            # TODO: update status of lock lenght and clumb to guides connetions
            self.lock_length()

    def draw_guide(self):
        guide.draw_guide_ctx(self.ui)

    def move_guide(self):
        guide.move_guide_ctx(self.ui)

    def duplicate(self):
        guide.duplicate_guide_ctx(self.ui)

    def duplicate_sym(self):
        guide.duplicate_sym(self.ui)

    def curl_crv(self):
        return

    def set_color(self, color):
        guide.guide_set_color_thickness(self.ui, color)

    def set_orange(self):
        self.set_color([1, .5, 0])

    def set_blue(self):
        self.set_color([0, 0, 1])

    def set_green(self):
        self.set_color([0, .5, 0])

    def set_red(self):
        self.set_color([.9, 0, 0])

    def set_pink(self):
        self.set_color([1, .1, 1])

    def set_light_blue(self):
        self.set_color([.1, 1, 1])

    def set_yellow(self):
        self.set_color([1, 1, 0])

    def sections_change(self):
        guide.guide_set_sections(self.ui)

    def thickness_change(self):
        guide.guide_set_color_thickness(self.ui, thickness=True)

    def smooth(self):
        guide.smooth_deform(self.ui)

    # toggle visibility
    def toggle_hair_visibility(self):
        guide.toggle_hair_visibility(self.ui)

    def toggle_guides_visibility(self):
        guide.toggle_guides_visibility(self.ui)

    def toggle_scalp_visibility(self):
        guide.toggle_scalp_visibility(self.ui)

    # lock length
    def lock_length(self):
        guide.lock_length(self.ui)


def openXgenBoost(*args):

    pyqt.showDialog(XgenBoost, dockable=False)
