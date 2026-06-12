"""
MIT License

Copyright (c) 2011-2018 Jeremie Passerin, Miquel Campos - from 2018 The mGear-Dev Organization

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from functools import partial
import mgear.pymaya as pm

from mgear.shifter.component import guide
from mgear.core import transform, pyqt
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

# guide info
AUTHOR = "Miquel Campos"
URL = "www.mcsgear.com"
EMAIL = ""
VERSION = [2, 0, 0]
TYPE = "EPIC_arm_02"
NAME = "arm"
DESCRIPTION = ""

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

    connectors = ["shoulder_01"]
    joint_names_description = [
        "upperarm",
        "lowerarm",
        "upperarm_twist_##",
        "lowerarm_twist_##",
        "hand",
    ]

    def postInit(self):
        """Initialize the position for the guide"""
        self.save_transform = ["root", "elbow", "wrist", "eff"]
        self.save_blade = ["blade"]

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()

        vTemp = transform.getOffsetPosition(self.root, [3, 0, -0.01])
        self.elbow = self.addLoc("elbow", self.root, vTemp)
        vTemp = transform.getOffsetPosition(self.root, [6, 0, 0])
        self.wrist = self.addLoc("wrist", self.elbow, vTemp)
        vTemp = transform.getOffsetPosition(self.root, [7, 0, 0])
        self.eff = self.addLoc("eff", self.wrist, vTemp)

        self.dispcrv = self.addDispCurve(
            "crv", [self.root, self.elbow, self.wrist, self.eff]
        )

        self.blade = self.addBlade("blade", self.wrist, self.eff)

        self.addUpvLocator(self.elbow, self.wrist, self.eff, float_value=0.8)

    def addParameters(self):
        """Add the configurations settings"""

        # Default Values
        self.pBlend = self.addParam("blend", "double", 0, 0, 1)
        self.pIkRefArray = self.addParam("ikrefarray", "string", "")
        self.pUpvRefArray = self.addParam("upvrefarray", "string", "")
        self.pUpvRefArray = self.addParam("pinrefarray", "string", "")
        self.pMaxStretch = self.addParam("maxstretch", "double", 1, 1, None)
        self.pIKTR = self.addParam("ikTR", "bool", False)
        self.pMirrorMid = self.addParam("mirrorMid", "bool", True)
        self.pMirrorIK = self.addParam("mirrorIK", "bool", True)
        self.pleafJoints = self.addParam("leafJoints", "bool", False)
        self.pUseBlade = self.addParam("use_blade", "bool", True)
        self.pTPoseRest = self.addParam("rest_T_Pose", "bool", False)

        # Divisions
        self.pDiv0 = self.addParam("div0", "long", 2, 0, None)
        self.pDiv1 = self.addParam("div1", "long", 2, 0, None)

        # FCurves
        self.pSt_profile = self.addFCurveParam(
            "st_profile", [[0, 0], [0.5, -0.7], [1, 0]]
        )
        self.pSq_profile = self.addFCurveParam(
            "sq_profile", [[0, 0], [0.5, 0.7], [1, 0]]
        )

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None
        )

    def get_divisions(self):
        """Returns correct segments divisions"""

        self.divisions = self.root.div0.get() + self.root.div1.get() + 4
        return self.divisions

    def postDraw(self):
        "Add post guide draw elements to the guide"
        # hide blade if not in use
        for shp in self.blade.getShapes():
            pm.connectAttr(self.root.use_blade, shp.attr("visibility"))


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
        self.resize(350, 780)

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

        self.populateCheck(
            self.settingsTab.TPoseRest_checkBox, "rest_T_Pose"
        )

        self.settingsTab.ikfk_slider.setValue(
            int(self.root.attr("blend").get() * 100)
        )
        self.settingsTab.ikfk_spinBox.setValue(
            int(self.root.attr("blend").get() * 100)
        )
        self.settingsTab.maxStretch_spinBox.setValue(
            self.root.attr("maxstretch").get()
        )
        self.populateCheck(self.settingsTab.ikTR_checkBox, "ikTR")
        self.populateCheck(self.settingsTab.mirrorMid_checkBox, "mirrorMid")
        self.populateCheck(self.settingsTab.mirrorIK_checkBox, "mirrorIK")
        self.populateCheck(self.settingsTab.leafJoints_checkBox, "leafJoints")
        self.populateCheck(self.settingsTab.useBlade_checkBox, "use_blade")
        self.settingsTab.div0_spinBox.setValue(self.root.attr("div0").get())
        self.settingsTab.div1_spinBox.setValue(self.root.attr("div1").get())
        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)
        upvRefArrayItems = self.root.attr("upvrefarray").get().split(",")
        for item in upvRefArrayItems:
            self.settingsTab.upvRefArray_listWidget.addItem(item)
        pinRefArrayItems = self.root.attr("pinrefarray").get().split(",")
        for item in pinRefArrayItems:
            self.settingsTab.pinRefArray_listWidget.addItem(item)

        # populate connections in main settings
        for cnx in Guide.connectors:
            self.mainSettingsTab.connector_comboBox.addItem(cnx)

        sll = [
            self.mainSettingsTab.connector_comboBox.itemText(i)
            for i in range(self.mainSettingsTab.connector_comboBox.count())
        ]

        self.connector_items = sll
        currentConnector = self.root.attr("connector").get()
        if currentConnector not in self.connector_items:
            self.mainSettingsTab.connector_comboBox.addItem(currentConnector)
            self.connector_items.append(currentConnector)
            pm.displayWarning(
                "The current connector: %s, is not a valid "
                "connector for this component. Build will Fail!!"
            )
        comboIndex = self.connector_items.index(currentConnector)
        self.mainSettingsTab.connector_comboBox.setCurrentIndex(comboIndex)

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

        self.settingsTab.maxStretch_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.settingsTab.maxStretch_spinBox,
                "maxstretch",
            )
        )

        self.settingsTab.div0_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div0_spinBox, "div0")
        )

        self.settingsTab.div1_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div1_spinBox, "div1")
        )

        self.settingsTab.squashStretchProfile_pushButton.clicked.connect(
            self.setProfile
        )

        self.settingsTab.ikTR_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.ikTR_checkBox, "ikTR")
        )

        self.settingsTab.mirrorMid_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.mirrorMid_checkBox,
                "mirrorMid",
            )
        )
        self.settingsTab.mirrorIK_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.mirrorIK_checkBox,
                "mirrorIK",
            )
        )
        self.settingsTab.leafJoints_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.leafJoints_checkBox,
                "leafJoints",
            )
        )

        self.settingsTab.useBlade_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.useBlade_checkBox,
                "use_blade",
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

        self.settingsTab.ikRefArray_copyRef_pushButton.clicked.connect(
            partial(
                self.copyFromListWidget,
                self.settingsTab.upvRefArray_listWidget,
                self.settingsTab.ikRefArray_listWidget,
                "ikrefarray",
            )
        )
        self.settingsTab.ikRefArray_listWidget.installEventFilter(self)

        self.settingsTab.upvRefArrayAdd_pushButton.clicked.connect(
            partial(
                self.addItem2listWidget,
                self.settingsTab.upvRefArray_listWidget,
                "upvrefarray",
            )
        )

        self.settingsTab.upvRefArrayRemove_pushButton.clicked.connect(
            partial(
                self.removeSelectedFromListWidget,
                self.settingsTab.upvRefArray_listWidget,
                "upvrefarray",
            )
        )

        self.settingsTab.upvRefArray_copyRef_pushButton.clicked.connect(
            partial(
                self.copyFromListWidget,
                self.settingsTab.ikRefArray_listWidget,
                self.settingsTab.upvRefArray_listWidget,
                "upvrefarray",
            )
        )
        self.settingsTab.upvRefArray_listWidget.installEventFilter(self)

        self.settingsTab.pinRefArrayAdd_pushButton.clicked.connect(
            partial(
                self.addItem2listWidget,
                self.settingsTab.pinRefArray_listWidget,
                "pinrefarray",
            )
        )
        self.settingsTab.pinRefArrayRemove_pushButton.clicked.connect(
            partial(
                self.removeSelectedFromListWidget,
                self.settingsTab.pinRefArray_listWidget,
                "pinrefarray",
            )
        )

        self.settingsTab.pinRefArray_copyRef_pushButton.clicked.connect(
            partial(
                self.copyFromListWidget,
                self.settingsTab.ikRefArray_listWidget,
                self.settingsTab.pinRefArray_listWidget,
                "pinrefarray",
            )
        )
        self.mainSettingsTab.connector_comboBox.currentIndexChanged.connect(
            partial(
                self.updateConnector,
                self.mainSettingsTab.connector_comboBox,
                self.connector_items,
            )
        )

        self.settingsTab.TPoseRest_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.TPoseRest_checkBox,
                "rest_T_Pose",
            )
        )

        self.settingsTab.pinRefArray_listWidget.installEventFilter(self)

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            elif sender == self.settingsTab.upvRefArray_listWidget:
                self.updateListAttr(sender, "upvrefarray")
            elif sender == self.settingsTab.pinRefArray_listWidget:
                self.updateListAttr(sender, "pinrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
