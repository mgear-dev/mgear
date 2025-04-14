"""Guide Squash 01 module"""

from functools import partial

from mgear.shifter.component import guide
from mgear.core import transform, pyqt
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

# guide info
AUTHOR = "anima inc., Joji Nishimura"
URL = "www.studioanima.co.jp"
EMAIL = ""
VERSION = [1, 1, 0]
TYPE = "shoulder_02"
NAME = "shoulder"
DESCRIPTION = "Simple shoulder with space switch for\n the arm, and Orbit " \
              "layer for the arm " \
              "This shoulder have 3 locations so the orbit"\
              "can be separated from the tip of the control"

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
        self.save_transform = ["root", "tip", "orbit"]
        self.save_blade = ["blade"]

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        vTemp = transform.getOffsetPosition(self.root, [2, 0, 0])
        self.loc = self.addLoc("tip", self.root, vTemp)
        self.blade = self.addBlade("blade", self.root, self.loc)
        vTemp = transform.getOffsetPosition(self.root, [3, 0, 0])
        self.orbit = self.addLoc("orbit", self.root, vTemp)

        centers = [self.root, self.loc, self.orbit]
        self.dispcrv = self.addDispCurve("crv", centers)

    def addParameters(self):
        """Add the configurations settings"""

        self.pRefArray = self.addParam("refArray", "string", "")
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pMirrorBehaviour = self.addParam("mirrorBehaviour", "bool", False)

        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)


##########################################################
# Setting Page
##########################################################

class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    """The Component settings UI"""

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):
    """Create the component setting window"""

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
        """Populate the controls values.

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        if self.root.attr("mirrorBehaviour").get():
            self.settingsTab.mirrorBehaviour_checkBox.setCheckState(
                QtCore.Qt.Checked)
        else:
            self.settingsTab.mirrorBehaviour_checkBox.setCheckState(
                QtCore.Qt.Unchecked)

        # populate component settings
        refArrayItems = self.root.attr("refArray").get().split(",")
        for item in refArrayItems:
            self.settingsTab.refArray_listWidget.addItem(item)

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        self.settingsTab.mirrorBehaviour_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.mirrorBehaviour_checkBox,
                    "mirrorBehaviour"))

        self.settingsTab.refArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.refArray_listWidget,
                    "refArray"))

        self.settingsTab.refArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.refArray_listWidget,
                    "refArray"))

        self.settingsTab.refArray_listWidget.installEventFilter(self)

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.refArray_listWidget:
                self.updateListAttr(sender, "refArray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
