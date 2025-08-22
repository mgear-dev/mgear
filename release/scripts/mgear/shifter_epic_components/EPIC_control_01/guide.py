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
AUTHOR = "Jeremie Passerin, Miquel Campos"
URL = ", www.mcsgear.com"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "EPIC_control_01"
NAME = "control"
DESCRIPTION = "Game ready component for EPIC's UE and other Game Engines\n"\
    "Based on control_01. Joint name taken from component instance name"
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

    connectors = ["orientation"]
    ctl_names_description = ["ctl"]

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

        self.pIcon = self.addParam("icon", "string", "cube")

        self.pIkRefArray = self.addParam("ikrefarray", "string", "")
        self.pBackwardsRefJnt  = self.addParam("backwards_ref_jnt", "string", "")

        self.pJoint = self.addParam("joint", "bool", False)
        self.pUniScale = self.addParam("uniScale", "bool", False)

        self.pDescriptionName = self.addParam("descriptionName", "bool", True)

        for s in ["tx", "ty", "tz", "ro", "rx", "ry", "rz", "sx", "sy", "sz"]:
            self.addParam("k_" + s, "bool", True)

        self.pDefault_RotOrder = self.addParam(
            "default_rotorder", "long", 0, 0, 5)
        self.pNeutralRotation = self.addParam("neutralRotation", "bool", True)
        self.pMirrorBehaviour = self.addParam("mirrorBehaviour", "bool", False)
        self.pCtlSize = self.addParam("ctlSize", "double", 1, None, None)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)

        return

    def postDraw(self):
        "Add post guide draw elements to the guide"
        size = pm.xform(self.root, q=True, ws=True, scale=True)[0]
        self.add_ref_axis(self.root,
                          self.root.neutralRotation,
                          inverted=True,
                          width=.5 / size)

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


        self.populateCheck(self.settingsTab.descriptionName_checkBox, "descriptionName")

        self.settingsTab.ro_comboBox.setCurrentIndex(
            self.root.attr("default_rotorder").get())

        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)

        # populate connections in main settings
        for cnx in Guide.connectors:
            self.mainSettingsTab.connector_comboBox.addItem(cnx)
        cBox = self.mainSettingsTab.connector_comboBox
        self.connector_items = [cBox.itemText(i) for i in range(cBox.count())]
        currentConnector = self.root.attr("connector").get()
        if currentConnector not in self.connector_items:
            self.mainSettingsTab.connector_comboBox.addItem(currentConnector)
            self.connector_items.append(currentConnector)
            pm.displayWarning("The current connector: %s, is not a valid "
                              "connector for this component. "
                              "Build will Fail!!")
        comboIndex = self.connector_items.index(currentConnector)
        self.mainSettingsTab.connector_comboBox.setCurrentIndex(comboIndex)

        self.settingsTab.backwards_ref_jnt_lineEdit.setText(
            self.root.attr("backwards_ref_jnt").get())

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

        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(self.updateConnector,
                    self.mainSettingsTab.connector_comboBox,
                    self.connector_items))

        self.settingsTab.descriptionName_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.descriptionName_checkBox,
                "descriptionName",
            )
        )

        self.settingsTab.backwards_ref_jnt_pushButton.clicked.connect(
            partial(self.updateFallbackJoint,
                    self.settingsTab.backwards_ref_jnt_lineEdit,
                    "backwards_ref_jnt"))

    def updateFallbackJoint(self, lEdit, targetAttr):
        """Update line edit with selected joint name if valid.

        This method checks if the selected object is a joint and sets the
        line edit text and corresponding attribute on the root.

        Args:
            lEdit (QLineEdit): Line edit widget to populate.
            targetAttr (str): Attribute name on root to update.

        Returns:
            None
        """
        oSel = pm.selected()
        if oSel:
            node = oSel[0]
            if node == self.root:
                pm.displayWarning("Root joint cannot be used as fallback.")
                return

            if pm.nodeType(node) == "joint":
                lEdit.setText(node.name())
                self.root.attr(targetAttr).set(lEdit.text())
            else:
                pm.displayWarning("Selected element is not a joint.")
        else:
            pm.displayWarning("Nothing selected.")
            if lEdit.text():
                lEdit.clear()
                self.root.attr(targetAttr).set("")
                pm.displayWarning("Fallback joint reference has been cleared.")

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
