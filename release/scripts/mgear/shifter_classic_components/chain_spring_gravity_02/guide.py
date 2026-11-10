"""Guide Chain Spring Gravity 02 module"""

from functools import partial

import mgear.pymaya as pm
from mgear.shifter.component import chain_stack
from mgear.shifter.component import guide
from mgear.core import pyqt
from mgear.core import ui_style

from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

# guide info
AUTHOR = "Emilio Serrano, Jeremie Passerin, Miquel Campos"
URL = "milio-serrano.gumroad.com/, www.mcsgear.com"
EMAIL = ", "
VERSION = [1, 0, 0]
TYPE = "chain_spring_gravity_02"
NAME = "chainSpringGravity"
DESCRIPTION = (
    "FK chain with spring and gravity. It can be scaled, stacked as master "
    "or slave of other stack chains, and has optional extra tweak and "
    "tweak end controls."
)

# component types accepted as master chain
COMPATIBLE = (
    TYPE,
    "chain_stack_01",
    "lite_chain_stack_01",
    "lite_chain_stack_02",
    "chain_spring_lite_stack_master_01",
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

    def addParameters(self):
        """Add the configurations settings"""
        self.pMirrorBehaviour = self.addParam("mirrorBehaviour", "bool", False)
        self.pExtraTweak = self.addParam("extraTweak", "bool", False)
        self.pTweakEnd = self.addParam("tweakEnd", "bool", False)
        self.pMasterChainLocal = self.addParam("masterChainLocal", "string", "")
        self.pMasterChainGlobal = self.addParam("masterChainGlobal", "string", "")
        self.pCnxOffset = self.addParam("cnxOffset", "long", 0, 0)
        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None
        )


##########################################################
# Setting Page
##########################################################


class settingsTab(QtWidgets.QWidget):
    """Component settings tab, built in code."""

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.mirrorBehaviour_checkBox = QtWidgets.QCheckBox("Mirror Behaviour L and R")
        self.mirrorBehaviour_checkBox.setToolTip(
            "On the R side, mirror the controls so the same\n"
            "values give a mirrored pose on L and R."
        )
        self.extraTweak_checkBox = QtWidgets.QCheckBox("Extra Tweak")
        self.extraTweak_checkBox.setToolTip(
            "Add a tweak control on each segment, after the\n"
            "spring. The tweak control drives the joint."
        )
        self.tweakEnd_checkBox = QtWidgets.QCheckBox("Tweak End")
        self.tweakEnd_checkBox.setToolTip(
            "Add a control and a joint at the chain tip,\n"
            "following the last spring segment."
        )

        self.masterLocal_lineEdit = QtWidgets.QLineEdit()
        self.masterLocal_lineEdit.setReadOnly(True)
        self.masterLocal_pushButton = QtWidgets.QPushButton("<<")
        self.masterLocal_pushButton.setToolTip(
            "Select the guide root of the master chain and\n"
            "click to pick it. Click with nothing selected to\n"
            "clear it. The local master adds its motion in the\n"
            "segment space."
        )
        self.masterGlobal_lineEdit = QtWidgets.QLineEdit()
        self.masterGlobal_lineEdit.setReadOnly(True)
        self.masterGlobal_pushButton = QtWidgets.QPushButton("<<")
        self.masterGlobal_pushButton.setToolTip(
            "Select the guide root of the master chain and\n"
            "click to pick it. Click with nothing selected to\n"
            "clear it. The global master adds its motion in\n"
            "world aligned space."
        )
        self.cnxOffset_spinBox = QtWidgets.QSpinBox()
        self.cnxOffset_spinBox.setRange(0, 999)
        self.cnxOffset_spinBox.setToolTip(
            "Master segment of the first segment of this chain.\n"
            "Segments past the master end use its last segment."
        )
        compatible_label = QtWidgets.QLabel(
            "Compatible masters: {}".format(", ".join(COMPATIBLE))
        )
        compatible_label.setWordWrap(True)
        ui_style.set_role(compatible_label, "text_hint")

        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        options_layout.addWidget(self.mirrorBehaviour_checkBox)
        options_layout.addWidget(self.extraTweak_checkBox)
        options_layout.addWidget(self.tweakEnd_checkBox)

        stack_group = QtWidgets.QGroupBox("Stack")
        stack_layout = QtWidgets.QFormLayout(stack_group)
        stack_layout.addRow(
            "Master Local",
            self._pick_row(self.masterLocal_lineEdit, self.masterLocal_pushButton),
        )
        stack_layout.addRow(
            "Master Global",
            self._pick_row(self.masterGlobal_lineEdit, self.masterGlobal_pushButton),
        )
        stack_layout.addRow("Connection Offset", self.cnxOffset_spinBox)
        stack_layout.addRow(compatible_label)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(*ui_style.scaled(6))
        layout.addWidget(options_group)
        layout.addWidget(stack_group)
        layout.addStretch()

    def _pick_row(self, line_edit, button):
        """Return a layout with a line edit and its pick button.

        Args:
            line_edit (QtWidgets.QLineEdit): The master name field.
            button (QtWidgets.QPushButton): The pick button.

        Returns:
            QtWidgets.QHBoxLayout: The row layout.
        """
        button.setFixedWidth(*ui_style.scaled(32))
        row = QtWidgets.QHBoxLayout()
        row.addWidget(line_edit)
        row.addWidget(button)
        return row


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
        self.resize(*ui_style.scaled(350, 400))

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
        tab = self.settingsTab
        self.populateCheck(tab.mirrorBehaviour_checkBox, "mirrorBehaviour")
        self.populateCheck(tab.extraTweak_checkBox, "extraTweak")
        self.populateCheck(tab.tweakEnd_checkBox, "tweakEnd")
        tab.masterLocal_lineEdit.setText(self.root.attr("masterChainLocal").get())
        tab.masterGlobal_lineEdit.setText(self.root.attr("masterChainGlobal").get())
        tab.cnxOffset_spinBox.setValue(self.root.attr("cnxOffset").get())

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        tab = self.settingsTab
        for check_box, attr in (
            (tab.mirrorBehaviour_checkBox, "mirrorBehaviour"),
            (tab.extraTweak_checkBox, "extraTweak"),
            (tab.tweakEnd_checkBox, "tweakEnd"),
        ):
            check_box.stateChanged.connect(partial(self.updateCheck, check_box, attr))
        tab.masterLocal_pushButton.clicked.connect(
            partial(
                self.updateMasterChain, tab.masterLocal_lineEdit, "masterChainLocal"
            )
        )
        tab.masterGlobal_pushButton.clicked.connect(
            partial(
                self.updateMasterChain, tab.masterGlobal_lineEdit, "masterChainGlobal"
            )
        )
        tab.cnxOffset_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, tab.cnxOffset_spinBox, "cnxOffset")
        )

    def updateMasterChain(self, lEdit, targetAttr):
        """Pick the selected guide root as master chain, or clear it.

        Args:
            lEdit (QtWidgets.QLineEdit): The master name field.
            targetAttr (str): The guide param storing the master name.
        """
        oSel = pm.selected()
        if not oSel:
            if lEdit.text():
                lEdit.clear()
                self.root.attr(targetAttr).set("")
                pm.displayWarning("The previous Master Chain have been cleared")
            else:
                pm.displayWarning("Nothing selected.")
            return
        comp_name, warning = chain_stack.check_master_chain(
            self.root, oSel[0], COMPATIBLE
        )
        if warning:
            pm.displayWarning(warning)
            return
        lEdit.setText(comp_name)
        self.root.attr(targetAttr).set(comp_name)

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
