from functools import partial

from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui
import mgear.pymaya as pm
from mgear import shifter


# guide info
AUTHOR = "anima inc."
URL = "www.studioanima.co.jp"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "chain_IK_spline_variable_FK_stack_01"
NAME = "chain"
DESCRIPTION = "IK chain with a spline driven joints. And variable number of \
FK controls. \nIK is master, FK Slave. With stack for IK and FK controls \n\
 WARNING: This component stack only support one level stack. This will avoid \
 complex connections and keep the component a little lighter. If the master \
 has more inputs will not move the slave of the slave. Only the direct slave"

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
        self.addDispCurve("crvRef", centers, 3)

    def addParameters(self):
        """Add the configurations settings"""

        self.pNeutralPose = self.addParam("neutralpose", "bool", True)
        self.pOverrideNegate = self.addParam("overrideNegate", "bool", False)
        self.pfkNb = self.addParam("fkNb", "long", 5, 1)

        self.pPosition = self.addParam("position", "double", 0, 0, 1)
        self.pMaxStretch = self.addParam("maxstretch", "double", 1, 1)
        self.pMaxSquash = self.addParam("maxsquash", "double", 1, 0, 1)
        self.pSoftness = self.addParam("softness", "double", 0, 0, 1)
        self.pIsGlobalMaster = self.addParam("addJoints", "bool", True)
        self.pAddJoints = self.addParam("isGlobalMaster", "bool", False)
        self.pMasterChain = self.addParam("masterChainLocal", "string", "")
        self.pMasterChain = self.addParam("masterChainGlobal", "string", "")
        self.pCnxOffset = self.addParam("cnxOffset", "long", 0, 0)

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)

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
        self.populateCheck(self.settingsTab.overrideNegate_checkBox,
                           "overrideNegate")

        self.settingsTab.fkNb_spinBox.setValue(
            self.root.attr("fkNb").get())
        self.settingsTab.softness_slider.setValue(
            int(self.root.attr("softness").get() * 100))
        self.settingsTab.position_spinBox.setValue(
            int(self.root.attr("position").get() * 100))
        self.settingsTab.position_slider.setValue(
            int(self.root.attr("position").get() * 100))
        self.settingsTab.softness_spinBox.setValue(
            int(self.root.attr("softness").get() * 100))
        self.settingsTab.maxStretch_spinBox.setValue(
            self.root.attr("maxstretch").get())
        self.settingsTab.maxSquash_spinBox.setValue(
            self.root.attr("maxsquash").get())
        self.populateCheck(self.settingsTab.addJoints_checkBox,
                           "addJoints")
        self.populateCheck(self.settingsTab.isGlobalMaster_checkBox,
                           "isGlobalMaster")
        self.settingsTab.masterLocal_lineEdit.setText(
            self.root.attr("masterChainLocal").get())
        self.settingsTab.masterGlobal_lineEdit.setText(
            self.root.attr("masterChainGlobal").get())
        self.settingsTab.cnxOffset_spinBox.setValue(
            self.root.attr("cnxOffset").get())

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        self.settingsTab.overrideNegate_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.overrideNegate_checkBox,
                    "overrideNegate"))
        self.settingsTab.fkNb_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.fkNb_spinBox,
                    "fkNb"))
        self.settingsTab.softness_slider.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.softness_slider,
                    "softness"))
        self.settingsTab.softness_spinBox.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.softness_spinBox,
                    "softness"))
        self.settingsTab.position_slider.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.position_slider,
                    "position"))
        self.settingsTab.position_spinBox.valueChanged.connect(
            partial(self.updateSlider,
                    self.settingsTab.position_spinBox,
                    "position"))
        self.settingsTab.maxStretch_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.maxStretch_spinBox,
                    "maxstretch"))
        self.settingsTab.maxSquash_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.maxSquash_spinBox,
                    "maxsquash"))
        self.settingsTab.addJoints_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.addJoints_checkBox,
                    "addJoints"))

        self.settingsTab.masterLocal_pushButton.clicked.connect(
            partial(self.updateMasterChain,
                    self.settingsTab.masterLocal_lineEdit,
                    "masterChainLocal"))

        self.settingsTab.masterGlobal_pushButton.clicked.connect(
            partial(self.updateMasterChain,
                    self.settingsTab.masterGlobal_lineEdit,
                    "masterChainGlobal"))

        self.settingsTab.cnxOffset_spinBox.valueChanged.connect(
            partial(self.updateSpinBox,
                    self.settingsTab.cnxOffset_spinBox,
                    "cnxOffset"))

        self.settingsTab.isGlobalMaster_checkBox.stateChanged.connect(
            partial(self.updateCheck,
                    self.settingsTab.isGlobalMaster_checkBox,
                    "isGlobalMaster"))

    def updateMasterChain(self, lEdit, targetAttr):
        oType = pm.nodetypes.Transform

        oSel = pm.selected()
        compatible = [TYPE]
        if oSel:
            if oSel[0] == self.root:
                pm.displayWarning("Self root can not be Master. Cycle Warning")
            else:
                if (isinstance(oSel[0], oType)
                        and oSel[0].hasAttr("comp_type")
                        and oSel[0].attr("comp_type").get() in compatible):
                    # check master chain FK segments
                    self_len = self._get_chain_segments_length(self.root)
                    master_len = self._get_chain_segments_length(oSel[0])

                    if master_len >= self_len:
                        comp_name = oSel[0].name().replace("_root", "")
                        lEdit.setText(comp_name)
                        self.root.attr(targetAttr).set(lEdit.text())
                    else:
                        pm.displayWarning(
                            "Invalid Master: {} ".format(oSel[0]) +
                            "Current chain has: {} sections".format(self_len) +
                            " But Master chain has" +
                            " less sections: {}".format(str(master_len)))
                else:
                    pm.displayWarning("The selected element is not a "
                                      "chain root or compatible chain")
                    pm.displayWarning("Complatible chain componentes"
                                      " are: {}".format(str(compatible)))
        else:
            pm.displayWarning("Nothing selected.")
            if lEdit.text():
                lEdit.clear()
                self.root.attr(targetAttr).set("")
                pm.displayWarning("The previous Master Chain have been "
                                  "cleared")

    def _get_chain_segments_length(self, chain_root):
        module = shifter.importComponentGuide(chain_root.comp_type.get())
        componentGuide = getattr(module, "Guide")
        comp_guide = componentGuide()
        comp_guide.setFromHierarchy(chain_root)
        return len(comp_guide.pos)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
