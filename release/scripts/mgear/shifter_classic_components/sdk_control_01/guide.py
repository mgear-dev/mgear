"""Guide Control 01 module"""

from functools import partial
import mgear.pymaya as pm

from mgear.shifter.component import guide
from mgear.core import transform, pyqt, attribute
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui


# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos, Justin Pedersen"
URL = ", www.mcsgear.com, justin@tcgcape.co.za"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "sdk_control_01"
NAME = "control"
DESCRIPTION = "A controler to Set Driven Keys on"

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
        self.save_transform = ["root", "sizeRef", "pivot"]

    # =====================================================
    # Add more object to the object definition list.
    # @param self
    def addObjects(self):

        self.root = self.addRoot()
        vTemp = transform.getOffsetPosition(self.root, [0, 0, 1])
        self.sizeRef = self.addLoc("sizeRef", self.root, vTemp)
        pm.delete(self.sizeRef.getShapes())
        attribute.lockAttribute(self.sizeRef)

        vTemp = transform.getOffsetPosition(self.root, [0, 0, 0])
        self.pivot = self.addLoc("pivot", self.root, vTemp)

        centers = [self.root, self.pivot]
        self.dispcrv = self.addDispCurve("crv", centers)

    # =====================================================
    # Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):

        self.pIcon = self.addParam("icon", "string", "cube")

        self.pIkRefArray = self.addParam("ikrefarray", "string", "")

        self.pJoint = self.addParam("joint", "bool", True)
        self.pJoint = self.addParam("uniScale", "bool", False)

        for s in ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]:
            self.addParam("k_" + s, "bool", True)

        self.pDefault_RotOrder = self.addParam(
            "default_rotorder", "long", 0, 0, 5)
        self.pNeutralRotation = self.addParam("neutralRotation", "bool", False)
        self.pMirrorBehaviour = self.addParam("mirrorBehaviour", "bool", True)
        self.pCtlSize = self.addParam("ctlSize", "double", 1, None, None)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)

        self.pCustomPivot = self.addParam("customPivot", "bool", False)

        return

    def postDraw(self):
        """Add post guide draw elements to the guide"""
        # Setting custom colour
        for shape in pm.listRelatives(self.root, s=True):
            shape.overrideColor.set(14)
        # Connecting vis for custom Pivot

        shapeVisList = self.pivot.getShapes()
        shapeVisList.extend(self.dispcrv.getShapes())

        for shape in shapeVisList:
            pm.connectAttr(self.root.attr(self.pCustomPivot.scriptName), shape.visibility)


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
        self.iconsList = ['arrow',
                          'circle',
                          'compas',
                          'cross',
                          'crossarrow',
                          'cube',
                          'cubewithpeak',
                          'cylinder',
                          'diamond',
                          'flower',
                          'null',
                          'pyramid',
                          'sphere',
                          'square']

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

        self.populateCheck(self.settingsTab.joint_checkBox, "joint")
        self.populateCheck(self.settingsTab.uniScale_checkBox, "uniScale")
        self.populateCheck(self.settingsTab.neutralRotation_checkBox,
                           "neutralRotation")
        self.populateCheck(self.settingsTab.mirrorBehaviour_checkBox,
                           "mirrorBehaviour")
        self.settingsTab.ctlSize_doubleSpinBox.setValue(
            self.root.attr("ctlSize").get())
        sideIndex = self.iconsList.index(self.root.attr("icon").get())
        self.settingsTab.controlShape_comboBox.setCurrentIndex(sideIndex)

        self.populateCheck(self.settingsTab.tx_checkBox, "k_tx")
        self.populateCheck(self.settingsTab.ty_checkBox, "k_ty")
        self.populateCheck(self.settingsTab.tz_checkBox, "k_tz")
        self.populateCheck(self.settingsTab.rx_checkBox, "k_rx")
        self.populateCheck(self.settingsTab.ry_checkBox, "k_ry")
        self.populateCheck(self.settingsTab.rz_checkBox, "k_rz")
        self.populateCheck(self.settingsTab.ro_checkBox, "k_ro")
        self.populateCheck(self.settingsTab.sx_checkBox, "k_sx")
        self.populateCheck(self.settingsTab.sy_checkBox, "k_sy")
        self.populateCheck(self.settingsTab.sz_checkBox, "k_sz")

        self.settingsTab.ro_comboBox.setCurrentIndex(
            self.root.attr("default_rotorder").get())

        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)

        self.populateCheck(self.settingsTab.customPivot_checkBox, "customPivot")

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.joint_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.joint_checkBox,
                    "joint"))
        self.settingsTab.uniScale_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.uniScale_checkBox,
                    "uniScale"))
        self.settingsTab.neutralRotation_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.neutralRotation_checkBox,
                    "neutralRotation"))
        self.settingsTab.mirrorBehaviour_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.mirrorBehaviour_checkBox,
                    "mirrorBehaviour"))
        self.settingsTab.ctlSize_doubleSpinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.ctlSize_doubleSpinBox,
                    "ctlSize"))
        self.settingsTab.controlShape_comboBox.currentIndexChanged.connect(
            partial(self.updateControlShape,
                    self.settingsTab.controlShape_comboBox,
                    self.iconsList, "icon"))

        self.settingsTab.tx_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.tx_checkBox, "k_tx"))
        self.settingsTab.ty_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ty_checkBox, "k_ty"))
        self.settingsTab.tz_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.tz_checkBox, "k_tz"))
        self.settingsTab.rx_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.rx_checkBox, "k_rx"))
        self.settingsTab.ry_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ry_checkBox, "k_ry"))
        self.settingsTab.rz_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.rz_checkBox, "k_rz"))
        self.settingsTab.ro_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ro_checkBox, "k_ro"))
        self.settingsTab.sx_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.sx_checkBox, "k_sx"))
        self.settingsTab.sy_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.sy_checkBox, "k_sy"))
        self.settingsTab.sz_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.sz_checkBox, "k_sz"))

        self.settingsTab.ro_comboBox.currentIndexChanged.connect(
            partial(self.updateComboBox,
                    self.settingsTab.ro_comboBox,
                    "default_rotorder"))

        self.settingsTab.ikRefArrayAdd_pushButton.clicked.connect(
            partial(self.addItem2listWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))
        self.settingsTab.ikRefArrayRemove_pushButton.clicked.connect(
            partial(self.removeSelectedFromListWidget,
                    self.settingsTab.ikRefArray_listWidget,
                    "ikrefarray"))
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.settingsTab.customPivot_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.customPivot_checkBox, "customPivot"))

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
