"""Guide Chain 01 module"""

from functools import partial
from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget
from . import settingsUI

# guide info
AUTHOR = "Vi Cuong Van"
URL = "www.mcsGear.com"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "EPIC_chain_spline_IK_FK_01"
NAME = "chain"
DESCRIPTION = (
    "Game ready component for EPIC's UE and other Game Engines\n"
    "Simple IK/FK chain, With IK space switch"
)

##########################################################
# CLASS
##########################################################


class Guide(guide.ComponentGuide):
    """Component Guide Class"""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    def postInit(self):
        """Initialize the position for the guide"""

        self.save_transform = ["root", "#_loc"]
        self.save_blade = ["blade"]
        self.addMinMax("#_loc", 1, -1)

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        self.locs = self.addLocMulti("#_loc", self.root)
        self.blade = self.addBlade("blade", self.root, self.locs[0])

        centers = [self.root]
        centers.extend(self.locs)
        self.dispcrv = self.addDispCurve("crv", centers)

    def addParameters(self):
        """Add the configurations settings"""

        self.pType = self.addParam("mode", "long", 0, 0)
        self.pBlend = self.addParam("blend", "double", 1, 0, 1)
        self.pNeutralPose = self.addParam("neutralpose", "bool", True)
        self.pIkRefArray = self.addParam("ikrefarray", "string", "")
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None
        )
        self.pIkNb = self.addParam("ikNb", "long", 3, 2, None)
        # Width of each IK control's twist influence, as a fraction of the
        # spacing to its neighbouring control. 1.0 = the tent reaches exactly
        # to the neighbour controls (base/tip stay put when the middle control
        # twists, and equal twist on all controls gives a uniform roll).
        # Smaller = tighter / more localized twist.
        self.pTwistFalloff = self.addParam("twistFalloff", "double", 1.0, 0.05, 2.0)


##########################################################
# Setting Page
##########################################################


class settingsTab(QtWidgets.QDialog, settingsUI.Ui_Form):

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):

    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)

        super(componentSettings, self).__init__(parent=parent)
        self.settingsTab = settingsTab()

        self.setup_componentSettingWindow()
        self.create_componentControls()
        self.populate_componentControls()
        self.create_componentLayout()
        self.create_componentConnections()

    def setup_componentSettingWindow(self):
        self.mayaMainWindow = pyqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(350, 350)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """Populate Controls

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        self.settingsTab.ikfk_slider.setValue(int(self.root.attr("blend").get() * 100))
        self.settingsTab.ikfk_spinBox.setValue(int(self.root.attr("blend").get() * 100))
        self.settingsTab.mode_comboBox.setCurrentIndex(self.root.attr("mode").get())

        if self.root.attr("neutralpose").get():
            self.settingsTab.neutralPose_checkBox.setCheckState(QtCore.Qt.Checked)
        else:
            self.settingsTab.neutralPose_checkBox.setCheckState(QtCore.Qt.Unchecked)

        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)

        self.settingsTab.ikNb_spinBox.setValue(self.root.attr("ikNb").get())
        self.settingsTab.twistFalloff_spinBox.setValue(
            self.root.attr("twistFalloff").get()
        )

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.ikfk_slider.valueChanged.connect(
            partial(self.updateSlider, self.settingsTab.ikfk_slider, "blend")
        )
        self.settingsTab.ikfk_spinBox.valueChanged.connect(
            partial(self.updateSlider, self.settingsTab.ikfk_spinBox, "blend")
        )

        self.settingsTab.mode_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox, self.settingsTab.mode_comboBox, "mode")
        )

        self.settingsTab.neutralPose_checkBox.stateChanged.connect(
            partial(
                self.updateCheck, self.settingsTab.neutralPose_checkBox, "neutralpose"
            )
        )

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(
            partial(
                self.addItem2listWidget,
                self.settingsTab.ikRefArray_listWidget,
                "ikrefarray",
            )
        )
        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(
            partial(
                self.removeSelectedFromListWidget,
                self.settingsTab.ikRefArray_listWidget,
                "ikrefarray",
            )
        )
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.settingsTab.ikNb_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.ikNb_spinBox, "ikNb")
        )

        self.settingsTab.twistFalloff_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.settingsTab.twistFalloff_spinBox,
                "twistFalloff",
            )
        )

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
