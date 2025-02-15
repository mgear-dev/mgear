"""Guide Leg 2jnt freeTangent 01 module"""

from functools import partial

from mgear.shifter.component import guide
from mgear.core import transform, pyqt
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui


# guide info
AUTHOR = "Jeremie Passerin, Miquel Campos, Joji Nishimura"
URL = ", www.mcsgear.com"
EMAIL = ", "
VERSION = [1, 3, 0]
TYPE = "leg_2jnt_freeTangents_01"
NAME = "leg"
DESCRIPTION = (
    "Auto UPV. 2 bones leg with stretch, roundess, ik/fk...with "
    "classic core roll. With Knee pin and only one central tangent"
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
        self.save_transform = ["root", "knee", "ankle", "eff"]

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        vTemp = transform.getOffsetPosition(self.root, [0, -3, 0.1])
        self.knee = self.addLoc("knee", self.root, vTemp)
        vTemp = transform.getOffsetPosition(self.root, [0, -6, 0])
        self.ankle = self.addLoc("ankle", self.knee, vTemp)
        vTemp = transform.getOffsetPosition(self.root, [0, -6, 0.5])
        self.eff = self.addLoc("eff", self.ankle, vTemp)

        centers = [self.root, self.knee, self.ankle, self.eff]
        self.dispcrv = self.addDispCurve("crv", centers)

    def addParameters(self):
        """Add the configurations settings"""

        # Default Values
        self.pBlend = self.addParam("blend", "double", 1, 0, 1)
        self.pIkRefArray = self.addParam("ikrefarray", "string", "")
        self.pUpvRefArray = self.addParam("upvrefarray", "string", "")
        self.pUpvRefArray = self.addParam("pinrefarray", "string", "")
        self.pMaxStretch = self.addParam("maxstretch", "double", 1.5, 1, None)
        self.pMirrorMid = self.addParam("mirrorMid", "bool", False)
        self.pIKOrient = self.addParam("ikOri", "bool", True)

        # Divisions
        self.pDiv0 = self.addParam("div0", "long", 2, 1, None)
        self.pDiv1 = self.addParam("div1", "long", 2, 1, None)

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

        self.divisions = self.root.div0.get() + self.root.div1.get() + 4
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
        self.resize(350, 780)

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

        self.settingsTab.maxStretch_spinBox.setValue(
            self.root.attr("maxstretch").get()
        )

        self.populateCheck(self.settingsTab.mirrorMid_checkBox, "mirrorMid")
        self.populateCheck(self.settingsTab.ikOri_checkBox, "ikOri")

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

        self.settingsTab.ikOri_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.ikOri_checkBox,
                    "ikOri"))

        self.settingsTab.mirrorMid_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.mirrorMid_checkBox,
                "mirrorMid",
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
