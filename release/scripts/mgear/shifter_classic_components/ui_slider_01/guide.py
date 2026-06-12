"""Guide UI Slider 01 module"""
import math

from functools import partial
import mgear.pymaya as pm
from mgear.pymaya import datatypes

from mgear.shifter.component import guide
from mgear.core import (transform, pyqt, attribute,
                        icon, curve)
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

# guide info
AUTHOR = "Jeroen Hoolmans"
URL = "www.ambassadors.com"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "ui_slider_01"
NAME = "uiSlider"
DESCRIPTION = "Simple slider control used for building " \
              "interfaces. Useful to link with blendshapes " \
              "or setDrivenKeys."

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
        self.root = self.add2DRoot()
        vTemp = transform.getOffsetPosition(self.root, [0, 0, 1])
        self.sizeRef = self.addLoc("sizeRef", self.root, vTemp)
        pm.delete(self.sizeRef.getShapes())
        attribute.lockAttribute(self.sizeRef)

        # Now we need to show the range of the controls with
        # template curves.
        arrow_curves = [
            self.addTCurve(self.getName("up"),
                           datatypes.Vector(0, 0, 0), self.root),
            self.addTCurve(self.getName("right"),
                           datatypes.Vector(0, 0, -90), self.root),
            self.addTCurve(self.getName("down"),
                           datatypes.Vector(0, 0, 180), self.root),
            self.addTCurve(self.getName("left"),
                           datatypes.Vector(0, 0, 90), self.root)
        ]

        for [arrow_curve, param] in zip(arrow_curves, ["ty_positive",
                                                       "tx_positive",
                                                       "ty_negative",
                                                       "tx_negative"]):
            sh = arrow_curve.getShape()
            sh.template.set(1)
            self.root.attr(param) >> sh.visibility
            self.root.addChild(sh, add=True, shape=True)
        pm.delete(arrow_curves)

    # ====================================================
    # ELEMENTS

    def add2DRoot(self):
        """Add a root object to the guide.

        This method can initialize the object or draw it.
        Root object is a simple transform with a specific display and a setting
        property.

        Returns:
            dagNode: The root

        """
        if "root" not in self.tra.keys():
            self.tra["root"] = transform.getTransformFromPos(
                datatypes.Vector(0, 0, 0))

        self.root = icon.guideRootIcon2D(self.parent, self.getName(
            "root"), color=13, m=self.tra["root"])

        # Add Parameters from parameter definition list.
        for scriptName in self.paramNames:
            paramDef = self.paramDefs[scriptName]
            paramDef.create(self.root)

        return self.root

    def addTCurve(self, name, rotation=None, parent=None):
        """Creates a T shape to show the boundaries of the slider.
        """
        points = [
            datatypes.Vector(0, 0, 0),
            datatypes.Vector(0, 1, 0),
            datatypes.Vector(0.2, 1, 0),
            datatypes.Vector(-0.2, 1, 0)
        ]
        if rotation:
            rot_offset = datatypes.Vector(math.radians(rotation.x),
                                          math.radians(rotation.y),
                                          math.radians(rotation.z))
            points = icon.getPointArrayWithOffset(points,
                                                  rot_offset=rot_offset)

        t_curve = curve.addCurve(
            parent=parent,
            name=name,
            points=points,
            degree=1
        )
        return t_curve

    # =====================================================
    # Add more parameter to the parameter definition list.
    # @param self
    def addParameters(self):
        self.pIcon = self.addParam("icon", "string", "square")

        for s in ["tx_negative", "tx_positive", "ty_negative", "ty_positive"]:
            self.addParam(s, "bool", True)

        self.pMirrorBehaviour = self.addParam("mirrorBehaviour", "bool", True)
        self.pCtlSize = self.addParam("ctlSize", "double", 0.25, 0.1, 5)

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
        self.populateCheck(self.settingsTab.mirror_behaviour_checkbox,
                           "mirrorBehaviour")
        self.settingsTab.control_size_spinbox.setValue(
            self.root.attr("ctlSize").get())

        self.populateCheck(self.settingsTab.translate_x_negative_checkbox,
                           "tx_negative")
        self.populateCheck(self.settingsTab.translate_x_positive_checkbox,
                           "tx_positive")
        self.populateCheck(self.settingsTab.translate_y_negative_checkbox,
                           "ty_negative")
        self.populateCheck(self.settingsTab.translate_y_positive_checkbox,
                           "ty_positive")

    def create_componentLayout(self):
        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        self.settingsTab.mirror_behaviour_checkbox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.mirror_behaviour_checkbox,
                    "mirrorBehaviour"))
        self.settingsTab.control_size_spinbox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.control_size_spinbox,
                    "ctlSize"))

        self.settingsTab.translate_x_negative_checkbox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.translate_x_negative_checkbox,
                    "tx_negative"))
        self.settingsTab.translate_x_positive_checkbox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.translate_x_positive_checkbox,
                    "tx_positive"))
        self.settingsTab.translate_y_negative_checkbox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.translate_y_negative_checkbox,
                    "ty_negative"))
        self.settingsTab.translate_y_positive_checkbox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.translate_y_positive_checkbox,
                    "ty_positive"))

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
