"""Guide UI Slider 01 module"""
from functools import partial
import mgear.pymaya as pm

from mgear.shifter.component import guide
from mgear.core import transform, pyqt, attribute
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

# guide info
AUTHOR = "Jeroen Hoolmans"
URL = "www.ambassadors.com"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "ui_container_01"
NAME = "uiContainer"
DESCRIPTION = "The UI container creates a simple box " \
              "around the child ui controllers. It will " \
              "also add a controller so you can offset the " \
              "ui during animation."

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

    # =====================================================
    ##
    # @param self
    def postInit(self):
        self.save_transform = ["root", "sizeRef"]

    # =====================================================
    # Add more object to the object definition list.
    # @param self
    def addObjects(self):
        self.root = self.addRoot()
        vTemp = transform.getOffsetPosition(self.root, [0, 0, 1])
        self.sizeRef = self.addLoc("sizeRef", self.root, vTemp)
        pm.delete(self.sizeRef.getShapes())
        attribute.lockAttribute(self.sizeRef)

    # =====================================================
    # Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):
        self.pIcon = self.addParam("icon", "string", "crossarrow")

        self.pCtlSize = self.addParam("ctlSize", "double", 1, None, None)
        self.pMargin = self.addParam("margin", "double", 0.2, 0, 5)

        self.pAddController = self.addParam("addController", "bool", True)

        # These are used by Shifter by default. Do not remove
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)

    def postDraw(self):
        "Add post guide draw elements to the guide"

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
        # Delete old instances of the component settings window.
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
        self.resize(350, 520)

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
        self.populateCheck(self.settingsTab.control_checkbox,
                           "addController")
        self.settingsTab.control_size_spinbox.setValue(
            self.root.attr("ctlSize").get())
        self.settingsTab.margin_spinbox.setValue(
            self.root.attr("margin").get())

    def create_componentLayout(self):
        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        self.settingsTab.control_checkbox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.control_checkbox,
                    "addController"))
        self.settingsTab.control_size_spinbox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.control_size_spinbox,
                    "ctlSize"))
        self.settingsTab.margin_spinbox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.margin_spinbox,
                    "margin"))

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
