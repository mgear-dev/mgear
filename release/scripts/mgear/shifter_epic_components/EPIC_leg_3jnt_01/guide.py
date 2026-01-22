"""Guide leg 3jnt 01 module"""

from functools import partial

from mgear.shifter.component import guide
from mgear.core import transform, pyqt, attribute
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

# guide info
AUTHOR = "Miquel Campos"
URL = "www.mcsgear.com"
EMAIL = ""
VERSION = [1, 1, 0]
TYPE = "EPIC_leg_3jnt_01"
NAME = "leg"
DESCRIPTION = "Games 3 bones leg for quadrupeds and other animals"

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

    joint_names_description = [
        "femur",
        "tibia",
        "cannon",
        "femur_twist_##",
        "tibia_twist_##",
        "cannon_twist_##",
        "foot",
    ]

    def postInit(self):
        """Initialize the position for the guide"""
        self.save_transform = ["root", "knee", "ankle", "foot", "eff"]

    def addObjects(self):
        """Add the Guide Root, blade and locators"""
        lockAttrs = ["tx", "ry", "rz"]
        self.root = self.addRoot()
        vTemp = transform.getOffsetPosition(self.root, [0, -3, 0.1])
        self.knee = self.addLoc("knee", self.root, vTemp)
        attribute.lockAttribute(self.knee, lockAttrs)
        vTemp = transform.getOffsetPosition(self.root, [0, -6, 0])
        self.ankle = self.addLoc("ankle", self.knee, vTemp)
        attribute.lockAttribute(self.ankle, lockAttrs)
        vTemp = transform.getOffsetPosition(self.root, [0, -9, 0.2])
        self.foot = self.addLoc("foot", self.ankle, vTemp)
        attribute.lockAttribute(self.foot, lockAttrs)
        vTemp = transform.getOffsetPosition(self.root, [0, -9, 1])
        self.eff = self.addLoc("eff", self.foot, vTemp)

        centers = [self.root, self.knee, self.ankle, self.foot, self.eff]
        self.dispcrv = self.addDispCurve("crv1", centers)

        self.addUpvLocator(self.knee, self.ankle, self.eff)

    def addParameters(self):
        """Add the configurations settings"""

        # Default Values
        self.pBlend = self.addParam("blend", "double", 1, 0, 1)
        self.pFull3BoneIK = self.addParam("full3BonesIK", "double", 1, 0, 1)
        self.pIkRefArray = self.addParam("ikrefarray", "string", "")
        self.pUpvRefArray = self.addParam("upvrefarray", "string", "")
        self.pMaxStretch = self.addParam("maxstretch", "double", 1.5, 1, None)

        self.pleafJoints = self.addParam("leafJoints", "bool", False)

        self.pIKSolver = self.addEnumParam(
            "ikSolver", ["IK Spring", "IK Rotation Plane"], 0
        )

        self.pIKOrient = self.addParam("ikOri", "bool", True)

        # Divisions
        self.pDiv0 = self.addParam("div0", "long", 2, 0, None)
        self.pDiv1 = self.addParam("div1", "long", 2, 0, None)
        self.pDiv1 = self.addParam("div2", "long", 2, 0, None)

        # FCurves
        self.pSt_profile = self.addFCurveParam(
            "st_profile", [[0, 0], [0.5, -1], [1, 0]]
        )

        self.pSq_profile = self.addFCurveParam(
            "sq_profile", [[0, 0], [0.5, 1], [1, 0]]
        )

        self.pUseIndex = self.addParam("useIndex", "bool", False)

        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None
        )

    def get_divisions(self):
        """Returns correct segments divisions"""

        self.divisions = (
            self.root.div0.get()
            + self.root.div1.get()
            + self.root.div2.get()
            + 4
        )
        return self.divisions


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
        self.resize(350, 620)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """Populate the controls values.

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        self.settingsTab.ikfk_slider.setValue(
            int(self.root.attr("blend").get() * 100)
        )
        self.settingsTab.ikfk_spinBox.setValue(
            int(self.root.attr("blend").get() * 100)
        )
        self.settingsTab.full3BonesIK_slider.setValue(
            int(self.root.attr("full3BonesIK").get() * 100)
        )
        self.settingsTab.full3BonesIK_spinBox.setValue(
            int(self.root.attr("full3BonesIK").get() * 100)
        )
        self.settingsTab.maxStretch_spinBox.setValue(
            self.root.attr("maxstretch").get()
        )
        self.settingsTab.ikSolver_comboBox.setCurrentIndex(
            self.root.attr("ikSolver").get()
        )
        self.populateCheck(self.settingsTab.neutralRotation_checkBox, "ikOri")
        self.settingsTab.div0_spinBox.setValue(self.root.attr("div0").get())
        self.settingsTab.div1_spinBox.setValue(self.root.attr("div1").get())
        self.settingsTab.div2_spinBox.setValue(self.root.attr("div2").get())
        ikRefArrayItems = self.root.attr("ikrefarray").get().split(",")
        for item in ikRefArrayItems:
            self.settingsTab.ikRefArray_listWidget.addItem(item)
        upvRefArrayItems = self.root.attr("upvrefarray").get().split(",")
        for item in upvRefArrayItems:
            self.settingsTab.upvRefArray_listWidget.addItem(item)

        self.populateCheck(self.settingsTab.leafJoints_checkBox, "leafJoints")

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

        self.settingsTab.full3BonesIK_slider.valueChanged.connect(
            partial(
                self.updateSlider,
                self.settingsTab.full3BonesIK_slider,
                "full3BonesIK",
            )
        )

        self.settingsTab.full3BonesIK_spinBox.valueChanged.connect(
            partial(
                self.updateSlider,
                self.settingsTab.full3BonesIK_spinBox,
                "full3BonesIK",
            )
        )

        self.settingsTab.maxStretch_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.settingsTab.maxStretch_spinBox,
                "maxstretch",
            )
        )

        self.settingsTab.ikSolver_comboBox.currentIndexChanged.connect(
            partial(
                self.updateComboBox,
                self.settingsTab.ikSolver_comboBox,
                "ikSolver",
            )
        )

        self.settingsTab.neutralRotation_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.neutralRotation_checkBox,
                "ikOri",
            )
        )

        self.settingsTab.div0_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div0_spinBox, "div0")
        )

        self.settingsTab.div1_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div1_spinBox, "div1")
        )
        self.settingsTab.div2_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.div2_spinBox, "div2")
        )

        self.settingsTab.squashStretchProfile_pushButton.clicked.connect(
            self.setProfile
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

        self.settingsTab.leafJoints_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.leafJoints_checkBox,
                "leafJoints",
            )
        )

        self.settingsTab.upvRefArray_listWidget.installEventFilter(self)

    def eventFilter(self, sender, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.settingsTab.ikRefArray_listWidget:
                self.updateListAttr(sender, "ikrefarray")
            elif sender == self.settingsTab.upvRefArray_listWidget:
                self.updateListAttr(sender, "upvrefarray")
            return True
        else:
            return QtWidgets.QDialog.eventFilter(self, sender, event)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
