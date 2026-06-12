"""Guide Loc ori Chain 01 module"""

from functools import partial

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

import mgear.pymaya as pm


# guide info
AUTHOR = "Miquel Campos"
URL = ""
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "chain_loc_ori_01"
NAME = "chain"
DESCRIPTION = "Simple chain that takes the orienation from the locators"

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
        # self.save_blade = ["blade"]
        self.addMinMax("#_loc", 1, -1)

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        self.locs = self.addLocMulti("#_loc", self.root)
        # self.blade = self.addBlade("blade", self.root, self.locs[0])

        centers = [self.root]
        centers.extend(self.locs)
        self.dispcrv = self.addDispCurve("crv", centers)

    def addParameters(self):
        """Add the configurations settings"""

        self.pNeutralPose = self.addParam("neutralpose", "bool", True)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)
        self.pAddJoints = self.addParam("addJoints", "bool", True)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)

    def postDraw(self):
        "Add post guide draw elements to the guide"
        size = pm.xform(self.root, q=True, ws=True, scale=True)[0]
        self.add_ref_axis(self.root,
                          width=.5 / size)
        for loc in self.locs:
            size = pm.xform(loc, q=True, ws=True, scale=True)[0]
            self.add_ref_axis(loc,
                              width=.5 / size)

##########################################################
# Setting Page
##########################################################


class settingsTab(QtWidgets.QDialog, sui.Ui_Form):

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
        self.populateCheck(self.settingsTab.neutralPose_checkBox,
                           "neutralpose")
        self.populateCheck(self.settingsTab.overrideNegate_checkBox,
                           "overrideNegate")
        self.populateCheck(self.settingsTab.addJoints_checkBox,
                           "addJoints")

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.neutralPose_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.neutralPose_checkBox,
                    "neutralpose"))

        self.settingsTab.overrideNegate_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.overrideNegate_checkBox,
                    "overrideNegate"))

        self.settingsTab.addJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.addJoints_checkBox,
                    "addJoints"))

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
