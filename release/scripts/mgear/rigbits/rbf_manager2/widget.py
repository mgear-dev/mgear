# core
import maya.cmds as mc
import maya.OpenMayaUI as mui

# mgear
import mgear
from mgear.core import pyqt
from mgear.vendor.Qt import QtWidgets, QtCore, QtCompat, QtGui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.rigbits.six import PY2

__version__ = "2.0.1"
TOOL_NAME = "RBF Manager"
TOOL_TITLE = "{} v{} | mGear {}".format(
    TOOL_NAME, __version__, mgear.getVersion()
)
UI_NAME = "RBFManagerUI"
WORK_SPACE_NAME = UI_NAME + "WorkspaceControl"

MGEAR_EXTRA_ENVIRON = "MGEAR_RBF_EXTRA"
EXTRA_MODULE_DICT = "extraFunc_dict"

MIRROR_SUFFIX = "_mr"


class ClickableLineEdit(QtWidgets.QLineEdit):
    """subclass to allow for clickable lineEdit, as a button

    Attributes:
        clicked (QtCore.Signal): emitted when clicked
    """

    clicked = QtCore.Signal(str)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.text())
        else:
            super(ClickableLineEdit, self).mousePressEvent(event)


class TabBar(QtWidgets.QTabBar):
    """Subclass to get a taller tab widget, for readability"""

    def __init__(self):
        super(TabBar, self).__init__()

    def tabSizeHint(self, index):
        width = QtWidgets.QTabBar.tabSizeHint(self, index).width()
        return QtCore.QSize(width, 25)


class RBFWidget(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    def __init__(self, parent=pyqt.maya_main_window()):
        super(RBFWidget, self).__init__(parent=parent)

        # UI info -------------------------------------------------------------
        self.callBackID = None
        self.setWindowTitle(TOOL_TITLE)
        self.setObjectName(UI_NAME)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.genericWidgetHight = 24

    @staticmethod
    def deleteAssociatedWidgetsMaya(widget, attrName="associatedMaya"):
        """delete core ui items 'associated' with the provided widgets

        Args:
            widget (QWidget): Widget that has the associated attr set
            attrName (str, optional): class attr to query
        """
        if hasattr(widget, attrName):
            for t in getattr(widget, attrName):
                try:
                    mc.deleteUI(t, ctl=True)
                except Exception:
                    pass
        else:
            setattr(widget, attrName, [])

    @staticmethod
    def deleteAssociatedWidgets(widget, attrName="associated"):
        """delete widget items 'associated' with the provided widgets

        Args:
            widget (QWidget): Widget that has the associated attr set
            attrName (str, optional): class attr to query
        """
        if hasattr(widget, attrName):
            for t in getattr(widget, attrName):
                try:
                    t.deleteLater()
                except Exception:
                    pass
        else:
            setattr(widget, attrName, [])

    @staticmethod
    def _associateRBFnodeAndWidget(tabDrivenWidget, rbfNode):
        """associates the RBFNode with a widget for convenience when adding,
        deleting, editing

        Args:
            tabDrivenWidget (QWidget): tab widget
            rbfNode (RBFNode): instance to be associated
        """
        setattr(tabDrivenWidget, "rbfNode", rbfNode)

    @staticmethod
    def createCustomButton(
        label, size=(35, 27), icon=None, iconSize=None, tooltip=""
    ):
        stylesheet = (
            "QPushButton {background-color: #5D5D5D; border-radius: 4px;}"
            "QPushButton:pressed { background-color: #00A6F3;}"
            "QPushButton:hover:!pressed { background-color: #707070;}"
        )
        button = QtWidgets.QPushButton(label)
        button.setMinimumSize(QtCore.QSize(*size))
        button.setStyleSheet(stylesheet)
        button.setToolTip(tooltip)
        if icon and iconSize:
            button.setIcon(pyqt.get_icon(icon, iconSize))
        return button

    @staticmethod
    def createSetupSelector2Widget():
        rbfVLayout = QtWidgets.QVBoxLayout()
        rbfListWidget = QtWidgets.QListWidget()
        rbfVLayout.addWidget(rbfListWidget)
        return rbfVLayout, rbfListWidget

    @staticmethod
    def labelListWidget(label, attrListType, horizontal=True):
        """create the listAttribute that users can select their driver/driven
        attributes for the setup

        Args:
            label (str): to display above the listWidget
            horizontal (bool, optional): should the label be above or infront
            of the listWidget

        Returns:
            list: QLayout, QListWidget
        """
        if horizontal:
            attributeLayout = QtWidgets.QHBoxLayout()
        else:
            attributeLayout = QtWidgets.QVBoxLayout()
        attributeLabel = QtWidgets.QLabel(label)
        attributeListWidget = QtWidgets.QListWidget()
        attributeListWidget.setObjectName("{}ListWidget".format(attrListType))
        attributeLayout.addWidget(attributeLabel)
        attributeLayout.addWidget(attributeListWidget)
        return attributeLayout, attributeListWidget

    @staticmethod
    def addRemoveButtonWidget(label1, label2, horizontal=True):
        if horizontal:
            addRemoveLayout = QtWidgets.QHBoxLayout()
        else:
            addRemoveLayout = QtWidgets.QVBoxLayout()
        addAttributesButton = QtWidgets.QPushButton(label1)
        removeAttributesButton = QtWidgets.QPushButton(label2)
        addRemoveLayout.addWidget(addAttributesButton)
        addRemoveLayout.addWidget(removeAttributesButton)
        return addRemoveLayout, addAttributesButton, removeAttributesButton

    def selectNodeWidget(self, label, buttonLabel="Select"):
        """create a lout with label, lineEdit, QPushbutton for user input"""
        stylesheet = (
            "QLineEdit { background-color: #404040;"
            "border-radius: 4px;"
            "border-color: #505050;"
            "border-style: solid;"
            "border-width: 1.4px;}"
        )

        nodeLayout = QtWidgets.QHBoxLayout()
        nodeLayout.setSpacing(4)

        nodeLabel = QtWidgets.QLabel(label)
        nodeLabel.setFixedWidth(40)
        nodeLineEdit = ClickableLineEdit()
        nodeLineEdit.setStyleSheet(stylesheet)
        nodeLineEdit.setReadOnly(True)
        nodeSelectButton = self.createCustomButton(buttonLabel)
        nodeSelectButton.setFixedWidth(40)
        nodeLineEdit.setFixedHeight(self.genericWidgetHight)
        nodeSelectButton.setFixedHeight(self.genericWidgetHight)
        nodeLayout.addWidget(nodeLabel)
        nodeLayout.addWidget(nodeLineEdit, 1)
        nodeLayout.addWidget(nodeSelectButton)
        return nodeLayout, nodeLineEdit, nodeSelectButton

    def createSetupSelectorWidget(self):
        """create the top portion of the weidget, select setup + refresh

        Returns:
            list: QLayout, QCombobox, QPushButton
        """
        setRBFLayout = QtWidgets.QHBoxLayout()
        rbfLabel = QtWidgets.QLabel("Select RBF Setup:")
        rbf_cbox = QtWidgets.QComboBox()
        rbf_refreshButton = self.createCustomButton(
            "",
            (35, 25),
            icon="mgear_refresh-cw",
            iconSize=16,
            tooltip="Refresh the UI",
        )
        rbf_cbox.setFixedHeight(self.genericWidgetHight)
        rbf_refreshButton.setMaximumWidth(80)
        rbf_refreshButton.setFixedHeight(self.genericWidgetHight - 1)
        setRBFLayout.addWidget(rbfLabel)
        setRBFLayout.addWidget(rbf_cbox, 1)
        setRBFLayout.addWidget(rbf_refreshButton)
        return setRBFLayout, rbf_cbox, rbf_refreshButton

    def createDriverAttributeWidget(self):
        """widget where the user inputs information for the setups

        Returns:
            list: [of widgets]
        """
        driverControlVLayout = QtWidgets.QVBoxLayout()
        driverControlHLayout = QtWidgets.QHBoxLayout()

        # driverMainLayout.setStyleSheet("QVBoxLayout { background-color: #404040;")
        driverControlHLayout.setSpacing(3)
        #  --------------------------------------------------------------------
        (
            controlLayout,
            controlLineEdit,
            setControlButton,
        ) = self.selectNodeWidget("Control", buttonLabel="Set")
        controlLineEdit.setToolTip("The node driving the setup. (Click me!)")
        #  --------------------------------------------------------------------
        (
            driverLayout,
            driverLineEdit,
            driverSelectButton,
        ) = self.selectNodeWidget("Driver", buttonLabel="Set")
        driverLineEdit.setToolTip("The node driving the setup. (Click me!)")
        #  --------------------------------------------------------------------
        tooltipMsg = (
            "Set Control and Driver : Select exactly two objects.\n"
            "The first selected object will be set as the Control, and the second as the Driver."
        )
        allButton = self.createCustomButton(
            "", (20, 52), tooltip=tooltipMsg, icon="mgear_rewind", iconSize=15
        )

        (attributeLayout, attributeListWidget) = self.labelListWidget(
            label="Select Driver Attributes:",
            attrListType="driver",
            horizontal=False,
        )

        attributeListWidget.setToolTip("List of attributes driving setup.")
        selType = QtWidgets.QAbstractItemView.ExtendedSelection
        attributeListWidget.setSelectionMode(selType)
        attributeListWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #  --------------------------------------------------------------------
        driverControlVLayout.addLayout(controlLayout, 0)
        driverControlVLayout.addLayout(driverLayout, 0)
        driverControlHLayout.addLayout(driverControlVLayout, 0)
        driverControlHLayout.addWidget(allButton, 0)
        return [
            controlLineEdit,
            setControlButton,
            driverLineEdit,
            driverSelectButton,
            allButton,
            attributeListWidget,
            attributeLayout,
            driverControlHLayout,
        ]

    def createDrivenAttributeWidget(self):
        """the widget that displays the driven information

        Returns:
            list: [of widgets]
        """
        drivenWidget = QtWidgets.QWidget()
        drivenMainLayout = QtWidgets.QVBoxLayout()
        drivenMainLayout.setContentsMargins(0, 10, 0, 2)
        drivenMainLayout.setSpacing(9)
        drivenSetLayout = QtWidgets.QVBoxLayout()
        drivenMainLayout.addLayout(drivenSetLayout)
        drivenWidget.setLayout(drivenMainLayout)
        #  --------------------------------------------------------------------
        (
            drivenLayout,
            drivenLineEdit,
            drivenSelectButton,
        ) = self.selectNodeWidget("Driven", buttonLabel="Set")
        drivenTip = "The node being driven by setup. (Click me!)"
        drivenLineEdit.setToolTip(drivenTip)

        addDrivenButton = self.createCustomButton(
            "", (20, 25), icon="mgear_plus", iconSize=16, tooltip=""
        )
        addDrivenButton.setToolTip("Add a new driven to the current rbf node")
        #  --------------------------------------------------------------------
        (attributeLayout, attributeListWidget) = self.labelListWidget(
            label="Select Driven Attributes:",
            attrListType="driven",
            horizontal=False,
        )
        attributeListWidget.setToolTip("Attributes being driven by setup.")
        attributeLayout.setSpacing(1)
        selType = QtWidgets.QAbstractItemView.ExtendedSelection
        attributeListWidget.setSelectionMode(selType)
        attributeListWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #  --------------------------------------------------------------------
        drivenSetLayout.addLayout(drivenLayout, 0)
        drivenSetLayout.addLayout(attributeLayout, 0)
        drivenLayout.addWidget(addDrivenButton)
        drivenSetLayout.addLayout(drivenLayout, 0)
        drivenSetLayout.addLayout(attributeLayout, 0)
        drivenMainLayout.addLayout(drivenSetLayout)
        drivenWidget.setLayout(drivenMainLayout)
        return [
            drivenLineEdit,
            drivenSelectButton,
            addDrivenButton,
            attributeListWidget,
            drivenWidget,
            drivenMainLayout,
        ]

    def createDrivenWidget(self):
        """the widget that displays the driven information

        Returns:
            list: [of widgets]
        """
        drivenWidget = QtWidgets.QWidget()
        drivenMainLayout = QtWidgets.QHBoxLayout()
        drivenMainLayout.setContentsMargins(0, 0, 0, 0)
        drivenMainLayout.setSpacing(9)
        drivenWidget.setLayout(drivenMainLayout)

        tableWidget = self.createTableWidget()
        drivenMainLayout.addWidget(tableWidget, 1)
        return drivenWidget, tableWidget

    def createTableWidget(self):
        """create table widget used to display poses, set tooltips and colum

        Returns:
            QTableWidget: QTableWidget
        """
        stylesheet = """
        QTableWidget QHeaderView::section {
            background-color: #3a3b3b;
            padding: 2px;
            text-align: center;
        }
        QTableCornerButton::section {
            background-color: #3a3b3b;
            border: none;
        }
        """
        tableWidget = QtWidgets.QTableWidget()
        tableWidget.insertColumn(0)
        tableWidget.insertRow(0)
        tableWidget.setHorizontalHeaderLabels(["Pose Value"])
        tableWidget.setVerticalHeaderLabels(["Pose #0"])

        # tableWidget.setStyleSheet(stylesheet)
        tableTip = "Live connections to the RBF Node in your setup."
        tableTip = tableTip + "\nSelect the desired Pose # to recall pose."
        tableWidget.setToolTip(tableTip)
        return tableWidget

    def createTabWidget(self):
        """Tab widget to add driven widgets too. Custom TabBar so the tab is
        easier to select

        Returns:
            QTabWidget:
        """
        tabLayout = QtWidgets.QTabWidget()
        tabLayout.setContentsMargins(0, 0, 0, 0)
        tabBar = TabBar()
        tabLayout.setTabBar(tabBar)
        tabBar.setTabsClosable(True)
        return tabLayout

    def createOptionsButtonsWidget(self):
        """add, edit, delete buttons for modifying rbf setups.

        Returns:
            list: [QPushButtons]
        """
        optionsLayout = QtWidgets.QHBoxLayout()
        optionsLayout.setSpacing(5)
        addTip = "After positioning all controls in the setup, add new pose."
        addTip = addTip + "\nEnsure the driver node has a unique position."
        addPoseButton = self.createCustomButton(
            "Add Pose", size=(80, 26), tooltip=addTip
        )
        EditPoseButton = self.createCustomButton("Update Pose", size=(80, 26))
        EditPoseButton.setToolTip("Recall pose, adjust controls and Edit.")
        EditPoseValuesButton = self.createCustomButton(
            "Update Pose Values", size=(80, 26)
        )
        EditPoseValuesButton.setToolTip("Set pose based on values in table")
        deletePoseButton = self.createCustomButton(
            "Delete Pose", size=(80, 26)
        )
        deletePoseButton.setToolTip("Recall pose, then Delete")
        optionsLayout.addWidget(addPoseButton)
        optionsLayout.addWidget(EditPoseButton)
        optionsLayout.addWidget(EditPoseValuesButton)
        optionsLayout.addWidget(deletePoseButton)
        return (
            optionsLayout,
            addPoseButton,
            EditPoseButton,
            EditPoseValuesButton,
            deletePoseButton,
        )

    def createDarkContainerWidget(self):
        darkContainer = QtWidgets.QWidget()
        driverMainLayout = QtWidgets.QVBoxLayout()
        driverMainLayout.setContentsMargins(
            10, 10, 10, 10
        )  # Adjust margins as needed
        driverMainLayout.setSpacing(5)  # Adjust spacing between widgets

        # Setting the dark color (Example: dark gray)
        # darkContainer.setStyleSheet("background-color: #323232;")

        # Driver section
        (
            self.controlLineEdit,
            self.setControlButton,
            self.driverLineEdit,
            self.setDriverButton,
            self.allButton,
            self.driverAttributesWidget,
            self.driverAttributesLayout,
            driverControlLayout,
        ) = self.createDriverAttributeWidget()

        # Driven section
        (
            self.drivenLineEdit,
            self.setDrivenButton,
            self.addDrivenButton,
            self.drivenAttributesWidget,
            self.drivenWidget,
            self.drivenMainLayout,
        ) = self.createDrivenAttributeWidget()

        self.addRbfButton = self.createCustomButton("New RBF")
        self.addRbfButton.setToolTip("Select node to be driven by setup.")
        stylesheet = (
            "QPushButton {background-color: #179e83; border-radius: 4px;}"
            "QPushButton:hover:!pressed { background-color: #2ea88f;}"
        )
        self.addRbfButton.setStyleSheet(stylesheet)

        # Setting up the main layout for driver and driven sections
        driverMainLayout = QtWidgets.QVBoxLayout()
        driverMainLayout.addLayout(driverControlLayout)
        driverMainLayout.addLayout(self.driverAttributesLayout)
        driverMainLayout.addWidget(self.drivenWidget)
        driverMainLayout.addWidget(self.addRbfButton)
        darkContainer.setLayout(driverMainLayout)

        return darkContainer

    def createDriverDrivenTableWidget(self):
        tableContainer = QtWidgets.QWidget()

        # Setting up the main layout for driver and driven sections
        driverDrivenTableLayout = QtWidgets.QVBoxLayout()
        self.driverPoseTableWidget = self.createTableWidget()
        self.rbfTabWidget = self.createTabWidget()

        # Options buttons section
        (
            optionsLayout,
            self.addPoseButton,
            self.editPoseButton,
            self.editPoseValuesButton,
            self.deletePoseButton,
        ) = self.createOptionsButtonsWidget()
        self.addPoseButton.setEnabled(False)
        self.editPoseButton.setEnabled(False)
        self.editPoseValuesButton.setEnabled(False)
        self.deletePoseButton.setEnabled(False)

        driverDrivenTableLayout.addWidget(self.driverPoseTableWidget, 1)
        driverDrivenTableLayout.addWidget(self.rbfTabWidget, 1)
        driverDrivenTableLayout.addLayout(optionsLayout)
        tableContainer.setLayout(driverDrivenTableLayout)

        return tableContainer


# =============================================================================
# UI General Functions
# =============================================================================


def getControlAttrWidget(nodeAttr, label=""):
    """Create a cmds.attrControlGrp and wrap it in a qtWidget, preserving its connection
    to the specified attr

    Args:
        nodeAttr (str): node.attr, the target for the attrControlGrp
        label (str, optional): name for the attr widget

    Returns:
        QtWidget.QLineEdit: A Qt widget created from attrControlGrp
        str: The name of the created Maya attrControlGrp
    """
    mAttrFeild = mc.attrControlGrp(attribute=nodeAttr, label=label, po=True)

    # Convert the Maya control to a Qt pointer
    ptr = mui.MQtUtil.findControl(mAttrFeild)

    # Wrap the Maya control into a Qt widget, considering Python version
    controlWidget = QtCompat.wrapInstance(
        long(ptr) if PY2 else int(ptr), base=QtWidgets.QWidget
    )
    controlWidget.setContentsMargins(0, 0, 0, 0)
    controlWidget.setMinimumWidth(0)

    attrEdit = [
        wdgt
        for wdgt in controlWidget.children()
        if type(wdgt) == QtWidgets.QLineEdit
    ]
    [
        wdgt.setParent(attrEdit[0])
        for wdgt in controlWidget.children()
        if type(wdgt) == QtCore.QObject
    ]

    attrEdit[0].setParent(None)
    controlWidget.setParent(attrEdit[0])
    controlWidget.setHidden(True)
    return attrEdit[0], mAttrFeild


def HLine():
    """seporator line for widgets

    Returns:
        Qframe: line for seperating UI elements visually
    """
    seperatorLine = QtWidgets.QFrame()
    seperatorLine.setFrameShape(QtWidgets.QFrame.HLine)
    seperatorLine.setFrameShadow(QtWidgets.QFrame.Sunken)
    return seperatorLine


def VLine():
    """seporator line for widgets

    Returns:
        Qframe: line for seperating UI elements visually
    """
    seperatorLine = QtWidgets.QFrame()
    seperatorLine.setFrameShape(QtWidgets.QFrame.VLine)
    seperatorLine.setFrameShadow(QtWidgets.QFrame.Sunken)
    return seperatorLine


def genericWarning(parent, warningText):
    """generic prompt warning with the provided text

    Args:
        parent (QWidget): Qwidget to be parented under
        warningText (str): information to display to the user

    Returns:
        QtCore.Response: of what the user chose. For warnings
    """
    selWarning = QtWidgets.QMessageBox(parent)
    selWarning.setText(warningText)
    results = selWarning.exec_()
    return results


def promptAcceptance(parent, descriptionA, descriptionB):
    """Warn user, asking for permission

    Args:
        parent (QWidget): to be parented under
        descriptionA (str): info
        descriptionB (str): further info

    Returns:
        QtCore.Response: accept, deline, reject
    """
    msgBox = QtWidgets.QMessageBox(parent)
    msgBox.setText(descriptionA)
    msgBox.setInformativeText(descriptionB)
    msgBox.setStandardButtons(
        QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel
    )
    msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
    decision = msgBox.exec_()
    return decision
