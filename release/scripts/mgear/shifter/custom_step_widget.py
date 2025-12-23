"""Custom Step Tab widget and mixin for Guide Settings."""

import datetime
import imp
import inspect
import json
import os
import shutil
import subprocess
import sys
import traceback
from functools import partial

import mgear.pymaya as pm
from mgear.core import pyqt
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui

MGEAR_SHIFTER_CUSTOMSTEP_KEY = "MGEAR_SHIFTER_CUSTOMSTEP_PATH"

if sys.version_info[0] == 2:
    string_types = (basestring,)
else:
    string_types = (str,)


class Ui_Form(object):
    """UI definition for Custom Step Tab."""

    def setupUi(self, Form):
        Form.resize(312, 655)

        self.mainLayout = QtWidgets.QVBoxLayout(Form)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        # Menu bar
        self.menuBar = QtWidgets.QMenuBar(Form)

        # Pre Custom Step menu
        self.preMenu = self.menuBar.addMenu("Pre")
        self.preExport_action = self.preMenu.addAction("Export")
        self.preExport_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.preImport_action = self.preMenu.addAction("Import")
        self.preImport_action.setIcon(pyqt.get_icon("mgear_log-in"))

        # Post Custom Step menu
        self.postMenu = self.menuBar.addMenu("Post")
        self.postExport_action = self.postMenu.addAction("Export")
        self.postExport_action.setIcon(pyqt.get_icon("mgear_log-out"))
        self.postImport_action = self.postMenu.addAction("Import")
        self.postImport_action.setIcon(pyqt.get_icon("mgear_log-in"))

        self.mainLayout.setMenuBar(self.menuBar)

        # Main group box
        self.groupBox = QtWidgets.QGroupBox("Custom Steps", Form)
        self.mainLayout.addWidget(self.groupBox)

        self.groupBoxLayout = QtWidgets.QVBoxLayout(self.groupBox)

        # Pre Custom Step section
        self.preCustomStep_checkBox = QtWidgets.QCheckBox(
            "Pre Custom Step", self.groupBox
        )
        self.groupBoxLayout.addWidget(self.preCustomStep_checkBox)

        self.preSearch_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.preSearch_lineEdit.setPlaceholderText("Search...")
        self.groupBoxLayout.addWidget(self.preSearch_lineEdit)

        self.preCustomStep_listWidget = QtWidgets.QListWidget(self.groupBox)
        self.preCustomStep_listWidget.setDragDropOverwriteMode(True)
        self.preCustomStep_listWidget.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )
        self.preCustomStep_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.preCustomStep_listWidget.setAlternatingRowColors(True)
        self.preCustomStep_listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.groupBoxLayout.addWidget(self.preCustomStep_listWidget)

        # Separator line
        self.line = QtWidgets.QFrame(self.groupBox)
        self.line.setLineWidth(3)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.groupBoxLayout.addWidget(self.line)

        # Post Custom Step section
        self.postCustomStep_checkBox = QtWidgets.QCheckBox(
            "Post Custom Step", self.groupBox
        )
        self.groupBoxLayout.addWidget(self.postCustomStep_checkBox)

        self.postSearch_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.postSearch_lineEdit.setPlaceholderText("Search...")
        self.groupBoxLayout.addWidget(self.postSearch_lineEdit)

        self.postCustomStep_listWidget = QtWidgets.QListWidget(self.groupBox)
        self.postCustomStep_listWidget.setDragDropOverwriteMode(True)
        self.postCustomStep_listWidget.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )
        self.postCustomStep_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.postCustomStep_listWidget.setAlternatingRowColors(True)
        self.postCustomStep_listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.groupBoxLayout.addWidget(self.postCustomStep_listWidget)

        # Info panel at bottom
        self.infoGroupBox = QtWidgets.QGroupBox("Step Info", Form)
        self.mainLayout.addWidget(self.infoGroupBox)

        self.infoLayout = QtWidgets.QFormLayout(self.infoGroupBox)
        self.infoLayout.setContentsMargins(6, 6, 6, 6)
        self.infoLayout.setSpacing(4)
        self.infoLayout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.ExpandingFieldsGrow
        )
        self.infoLayout.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)

        # Info labels
        self.info_name_label = QtWidgets.QLabel("-")
        self.info_name_label.setWordWrap(True)
        self.infoLayout.addRow("Name:", self.info_name_label)

        self.info_type_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Type:", self.info_type_label)

        self.info_status_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Status:", self.info_status_label)

        self.info_shared_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Shared:", self.info_shared_label)

        self.info_exists_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Exists:", self.info_exists_label)

        self.info_modified_label = QtWidgets.QLabel("-")
        self.infoLayout.addRow("Modified:", self.info_modified_label)

        self.info_path_label = QtWidgets.QLabel("-")
        self.info_path_label.setWordWrap(True)
        self.info_path_label.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse
        )
        self.info_path_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self.infoLayout.addRow("Path:", self.info_path_label)


class CustomStepTab(QtWidgets.QDialog, Ui_Form):
    """Custom Step Tab widget."""

    def __init__(self, parent=None):
        super(CustomStepTab, self).__init__(parent)
        self.setupUi(self)


class CustomStepMixin(object):
    """Mixin providing custom step functionality for GuideSettings.

    This mixin expects the host class to have:
        - self.root: The Maya node with custom step attributes
        - self.customStepTab: A CustomStepTab instance
        - Color brushes: greenBrush, redBrush, whiteBrush, whiteDownBrush, orangeBrush
        - Helper methods: populateCheck, updateCheck, updateListAttr
    """

    # Color brushes (should be defined in host class, but provide defaults)
    greenBrush = QtGui.QColor(0, 160, 0)
    redBrush = QtGui.QColor(180, 0, 0)
    whiteBrush = QtGui.QColor(255, 255, 255)
    whiteDownBrush = QtGui.QColor(160, 160, 160)
    orangeBrush = QtGui.QColor(240, 160, 0)

    def setup_custom_step_hover_info(self):
        """Set up hover info for custom step list widgets."""
        self.pre_cs = self.customStepTab.preCustomStep_listWidget
        self.pre_cs.setMouseTracking(True)
        self.pre_cs.entered.connect(self.pre_info)

        self.post_cs = self.customStepTab.postCustomStep_listWidget
        self.post_cs.setMouseTracking(True)
        self.post_cs.entered.connect(self.post_info)

    def pre_info(self, index):
        self.hover_info_item_entered(self.pre_cs, index)

    def post_info(self, index):
        self.hover_info_item_entered(self.post_cs, index)

    def hover_info_item_entered(self, view, index):
        if index.isValid():
            info_data = self.format_info(index.data())
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(),
                info_data,
                view.viewport(),
                view.visualRect(index),
            )

    def populate_custom_step_controls(self):
        """Populate custom step tab controls from Maya attributes."""
        self.populateCheck(
            self.customStepTab.preCustomStep_checkBox, "doPreCustomStep"
        )
        for item in self.root.attr("preCustomStep").get().split(","):
            self.customStepTab.preCustomStep_listWidget.addItem(item)
        self.refreshStatusColor(self.customStepTab.preCustomStep_listWidget)

        self.populateCheck(
            self.customStepTab.postCustomStep_checkBox, "doPostCustomStep"
        )
        for item in self.root.attr("postCustomStep").get().split(","):
            self.customStepTab.postCustomStep_listWidget.addItem(item)
        self.refreshStatusColor(self.customStepTab.postCustomStep_listWidget)

    def create_custom_step_connections(self):
        """Create signal connections for custom step tab."""
        csTap = self.customStepTab

        # Pre custom step checkbox
        csTap.preCustomStep_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                csTap.preCustomStep_checkBox,
                "doPreCustomStep",
            )
        )

        # Post custom step checkbox
        csTap.postCustomStep_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                csTap.postCustomStep_checkBox,
                "doPostCustomStep",
            )
        )

        # Menu bar actions
        csTap.preExport_action.triggered.connect(self.exportCustomStep)
        csTap.preImport_action.triggered.connect(self.importCustomStep)
        csTap.postExport_action.triggered.connect(
            partial(self.exportCustomStep, False)
        )
        csTap.postImport_action.triggered.connect(
            partial(self.importCustomStep, False)
        )

        # Event filters for drag/drop
        csTap.preCustomStep_listWidget.installEventFilter(self)
        csTap.postCustomStep_listWidget.installEventFilter(self)

        # Right click context menus
        csTap.preCustomStep_listWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        csTap.preCustomStep_listWidget.customContextMenuRequested.connect(
            self.preCustomStepMenu
        )
        csTap.postCustomStep_listWidget.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu
        )
        csTap.postCustomStep_listWidget.customContextMenuRequested.connect(
            self.postCustomStepMenu
        )

        # Search highlight
        csTap.preSearch_lineEdit.textChanged.connect(self.preHighlightSearch)
        csTap.postSearch_lineEdit.textChanged.connect(self.postHighlightSearch)

        # Item click to update info panel
        csTap.preCustomStep_listWidget.itemClicked.connect(
            partial(self.updateInfoPanel, pre=True)
        )
        csTap.postCustomStep_listWidget.itemClicked.connect(
            partial(self.updateInfoPanel, pre=False)
        )

    def updateInfoPanel(self, item, pre=True):
        """Update the info panel with details about the clicked custom step."""
        if not item:
            return

        data = item.text()
        csTap = self.customStepTab

        # Parse step name
        data_parts = data.split("|")
        cs_name = data_parts[0].strip()
        if cs_name.startswith("*"):
            cs_status = "Deactivated"
            cs_name = cs_name[1:]
        else:
            cs_status = "Active"

        # Get full path
        cs_fullpath = self.get_cs_file_fullpath(data)

        # Determine step type (Pre or Post)
        cs_type = "Pre Custom Step" if pre else "Post Custom Step"

        # Check shared status
        if "_shared" in data:
            cs_shared_owner = self.shared_owner(cs_fullpath)
            cs_shared = "Yes ({})".format(cs_shared_owner)
        else:
            cs_shared = "No (Local)"

        # Check file existence and get modification time
        if os.path.exists(cs_fullpath):
            cs_exists = "Yes"
            try:
                mtime = os.path.getmtime(cs_fullpath)
                cs_modified = datetime.datetime.fromtimestamp(mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                cs_modified = "Unknown"
        else:
            cs_exists = "No (File not found)"
            cs_modified = "-"

        # Update labels
        csTap.info_name_label.setText(cs_name)
        csTap.info_type_label.setText(cs_type)
        csTap.info_status_label.setText(cs_status)
        csTap.info_shared_label.setText(cs_shared)
        csTap.info_exists_label.setText(cs_exists)
        csTap.info_modified_label.setText(cs_modified)
        csTap.info_path_label.setText(cs_fullpath)

        # Color code the status
        if cs_status == "Active":
            csTap.info_status_label.setStyleSheet("color: #00A000;")
        else:
            csTap.info_status_label.setStyleSheet("color: #B40000;")

        # Color code file existence
        if cs_exists == "Yes":
            csTap.info_exists_label.setStyleSheet("color: #00A000;")
        else:
            csTap.info_exists_label.setStyleSheet("color: #B40000;")

    def custom_step_event_filter(self, sender, event):
        """Handle custom step list widget events. Call from eventFilter."""
        if event.type() == QtCore.QEvent.ChildRemoved:
            if sender == self.customStepTab.preCustomStep_listWidget:
                self.updateListAttr(sender, "preCustomStep")
                return True
            elif sender == self.customStepTab.postCustomStep_listWidget:
                self.updateListAttr(sender, "postCustomStep")
                return True
        return False

    def get_cs_file_fullpath(self, cs_data):
        """Get full path of custom step file from list item text."""
        filepath = cs_data.split("|")[-1][1:]
        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            fullpath = os.path.join(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""), filepath
            )
        else:
            fullpath = filepath
        return fullpath

    @classmethod
    def _editFile(cls, fullpath):
        """Open file in system default editor."""
        if sys.platform.startswith("darwin"):
            subprocess.call(("open", fullpath))
        elif os.name == "nt":
            os.startfile(fullpath)
        elif os.name == "posix":
            subprocess.call(("xdg-open", fullpath))

    def editFile(self, widgetList):
        """Edit selected custom step files."""
        for cs in widgetList.selectedItems():
            try:
                cs_data = cs.text()
                fullpath = self.get_cs_file_fullpath(cs_data)

                if fullpath:
                    self._editFile(fullpath)
                else:
                    pm.displayWarning("Please select one item from the list")
            except Exception:
                pm.displayError("The step can't be find or does't exists")

    def format_info(self, data):
        """Format custom step info for tooltip display."""
        data_parts = data.split("|")
        cs_name = data_parts[0]
        if cs_name.startswith("*"):
            cs_status = "Deactivated"
            cs_name = cs_name[1:]
        else:
            cs_status = "Active"

        cs_fullpath = self.get_cs_file_fullpath(data)
        if "_shared" in data:
            cs_shared_owner = self.shared_owner(cs_fullpath)
            cs_shared_status = "Shared"
        else:
            cs_shared_status = "Local"
            cs_shared_owner = "None"

        info = '<html><head/><body><p><span style=" font-weight:600;">\
        {0}</span></p><p>------------------</p><p><span style=" \
        font-weight:600;">Status</span>: {1}</p><p><span style=" \
        font-weight:600;">Shared Status:</span> {2}</p><p><span \
        style=" font-weight:600;">Shared Owner:</span> \
        {3}</p><p><span style=" font-weight:600;">Full Path</span>: \
        {4}</p></body></html>'.format(
            cs_name, cs_status, cs_shared_status, cs_shared_owner, cs_fullpath
        )
        return info

    def shared_owner(self, cs_fullpath):
        """Get the owner of a shared custom step."""
        scan_dir = os.path.abspath(os.path.join(cs_fullpath, os.pardir))
        while not scan_dir.endswith("_shared"):
            scan_dir = os.path.abspath(os.path.join(scan_dir, os.pardir))
            if scan_dir == "/":
                break
        scan_dir = os.path.abspath(os.path.join(scan_dir, os.pardir))
        return os.path.split(scan_dir)[1]

    @classmethod
    def get_steps_dict(cls, itemsList):
        """Get dictionary of step paths and their contents."""
        stepsDict = {}
        stepsDict["itemsList"] = itemsList
        for item in itemsList:
            step = open(item, "r")
            data = step.read()
            stepsDict[item] = data
            step.close()
        return stepsDict

    @classmethod
    def runStep(cls, stepPath, customStepDic):
        """Run a custom step.

        Args:
            stepPath: Path to the custom step file
            customStepDic: Dictionary of previously run custom steps

        Returns:
            True if build should stop, False otherwise
        """
        try:
            with pm.UndoChunk():
                pm.displayInfo("EXEC: Executing custom step: %s" % stepPath)
                if sys.platform.startswith("darwin"):
                    stepPath = stepPath.replace("\\", "/")

                fileName = os.path.split(stepPath)[1].split(".")[0]

                if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                    runPath = os.path.join(
                        os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""),
                        stepPath,
                    )
                else:
                    runPath = stepPath

                customStep = imp.load_source(fileName, runPath)
                if hasattr(customStep, "CustomShifterStep"):
                    argspec = inspect.getfullargspec(
                        customStep.CustomShifterStep.__init__
                    )
                    if "stored_dict" in argspec.args:
                        cs = customStep.CustomShifterStep(customStepDic)
                        cs.setup()
                        cs.run()
                    else:
                        cs = customStep.CustomShifterStep()
                        cs.run(customStepDic)
                    customStepDic[cs.name] = cs
                    pm.displayInfo(
                        "SUCCEED: Custom Shifter Step Class: %s. "
                        "Succeed!!" % stepPath
                    )
                else:
                    pm.displayInfo(
                        "SUCCEED: Custom Step simple script: %s. "
                        "Succeed!!" % stepPath
                    )

        except Exception as ex:
            template = "An exception of type {0} occurred. "
            "Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            pm.displayError(message)
            pm.displayError(traceback.format_exc())
            cont = pm.confirmBox(
                "FAIL: Custom Step Fail",
                "The step:%s has failed. Continue with next step?" % stepPath
                + "\n\n"
                + message
                + "\n\n"
                + traceback.format_exc(),
                "Continue",
                "Stop Build",
                "Edit",
                "Try Again!",
            )
            if cont == "Stop Build":
                return True
            elif cont == "Edit":
                cls._editFile(stepPath)
            elif cont == "Try Again!":
                try:
                    pm.undo()
                except Exception:
                    pass
                pm.displayInfo("Trying again! : {}".format(stepPath))
                inception = cls.runStep(stepPath, customStepDic)
                if inception:
                    return True
            else:
                return False

    def runManualStep(self, widgetList):
        """Run selected custom steps manually."""
        selItems = widgetList.selectedItems()
        for item in selItems:
            self.runStep(item.text().split("|")[-1][1:], customStepDic={})

    def addCustomStep(self, pre=True, *args):
        """Add a new custom step.

        Args:
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        filePaths = pm.fileDialog2(
            fileMode=4,
            startingDirectory=startDir,
            okc="Add",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePaths:
            return

        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        for filePath in filePaths:
            if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                filePath = os.path.abspath(filePath)
                baseReplace = os.path.abspath(
                    os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
                )
                filePath = filePath.replace(baseReplace, "").replace("\\", "/")
                if "/" == filePath[0]:
                    filePath = filePath[1:]

            fileName = os.path.split(filePath)[1].split(".")[0]
            stepWidget.addItem(fileName + " | " + filePath)

        self.updateListAttr(stepWidget, stepAttr)
        self.refreshStatusColor(stepWidget)

    def newCustomStep(self, pre=True, *args):
        """Create a new custom step file.

        Args:
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            okc="New",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        n, e = os.path.splitext(filePath)
        stepName = os.path.split(n)[-1]

        rawString = r'''import mgear.shifter.custom_step as cstp


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{stepName}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "{stepName}"

    def run(self):
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        return'''.format(stepName=stepName)

        f = open(filePath, "w")
        f.write(rawString + "\n")
        f.close()

        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            filePath = os.path.abspath(filePath)
            baseReplace = os.path.abspath(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            )
            filePath = filePath.replace(baseReplace, "")[1:]

        fileName = os.path.split(filePath)[1].split(".")[0]
        stepWidget.addItem(fileName + " | " + filePath)
        self.updateListAttr(stepWidget, stepAttr)
        self.refreshStatusColor(stepWidget)

    def duplicateCustomStep(self, pre=True, *args):
        """Duplicate the selected custom step.

        Args:
            pre: If True, adds to pre step list; otherwise to post step list
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
        else:
            startDir = self.root.attr(stepAttr).get()

        if stepWidget.selectedItems():
            sourcePath = (
                stepWidget.selectedItems()[0].text().split("|")[-1][1:]
            )

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            okc="New",
            fileFilter="Custom Step .py (*.py)",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            sourcePath = os.path.join(startDir, sourcePath)
        shutil.copy(sourcePath, filePath)

        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            filePath = os.path.abspath(filePath)
            baseReplace = os.path.abspath(
                os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            )
            filePath = filePath.replace(baseReplace, "")[1:]

        fileName = os.path.split(filePath)[1].split(".")[0]
        stepWidget.addItem(fileName + " | " + filePath)
        self.updateListAttr(stepWidget, stepAttr)
        self.refreshStatusColor(stepWidget)

    def exportCustomStep(self, pre=True, *args):
        """Export custom steps to a JSON file.

        Args:
            pre: If True, exports from pre step list; otherwise from post
        """
        if pre:
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepWidget = self.customStepTab.postCustomStep_listWidget

        itemsList = [
            i.text() for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
        ]
        if itemsList and not itemsList[0]:
            stepWidget.takeItem(0)

        if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
            startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            itemsList = [
                os.path.join(startDir, i.text().split("|")[-1][1:])
                for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
            ]
        else:
            itemsList = [
                i.text().split("|")[-1][1:]
                for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
            ]
            if itemsList:
                startDir = os.path.split(itemsList[-1])[0]
            else:
                pm.displayWarning("No custom steps to export.")
                return

        stepsDict = self.get_steps_dict(itemsList)
        data_string = json.dumps(stepsDict, indent=4, sort_keys=True)

        filePath = pm.fileDialog2(
            fileMode=0,
            startingDirectory=startDir,
            fileFilter="Shifter Custom Steps .scs (*%s)" % ".scs",
        )
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]

        f = open(filePath, "w")
        f.write(data_string)
        f.close()

    def importCustomStep(self, pre=True, *args):
        """Import custom steps from a JSON file.

        Args:
            pre: If True, imports to pre step list; otherwise to post
        """
        if pre:
            stepAttr = "preCustomStep"
            stepWidget = self.customStepTab.preCustomStep_listWidget
        else:
            stepAttr = "postCustomStep"
            stepWidget = self.customStepTab.postCustomStep_listWidget

        option = pm.confirmDialog(
            title="Shifter Custom Step Import Style",
            message="Do you want to import only the path or"
            " unpack and import?",
            button=["Only Path", "Unpack", "Cancel"],
            defaultButton="Only Path",
            cancelButton="Cancel",
            dismissString="Cancel",
        )

        if option in ["Only Path", "Unpack"]:
            if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                startDir = os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
            else:
                startDir = pm.workspace(q=True, rootDirectory=True)

            filePath = pm.fileDialog2(
                fileMode=1,
                startingDirectory=startDir,
                fileFilter="Shifter Custom Steps .scs (*%s)" % ".scs",
            )
            if not filePath:
                return
            if not isinstance(filePath, string_types):
                filePath = filePath[0]
            stepDict = json.load(open(filePath))
            stepsList = []

        if option == "Only Path":
            for item in stepDict["itemsList"]:
                stepsList.append(item)

        elif option == "Unpack":
            unPackDir = pm.fileDialog2(fileMode=2, startingDirectory=startDir)
            if not filePath:
                return
            if not isinstance(unPackDir, string_types):
                unPackDir = unPackDir[0]

            for item in stepDict["itemsList"]:
                fileName = os.path.split(item)[1]
                fileNewPath = os.path.join(unPackDir, fileName)
                stepsList.append(fileNewPath)
                f = open(fileNewPath, "w")
                f.write(stepDict[item])
                f.close()

        if option in ["Only Path", "Unpack"]:
            for item in stepsList:
                itemsList = [
                    i.text()
                    for i in stepWidget.findItems("", QtCore.Qt.MatchContains)
                ]
                if itemsList and not itemsList[0]:
                    stepWidget.takeItem(0)

                if os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, ""):
                    item = os.path.abspath(item)
                    baseReplace = os.path.abspath(
                        os.environ.get(MGEAR_SHIFTER_CUSTOMSTEP_KEY, "")
                    )
                    item = item.replace(baseReplace, "")[1:]

                fileName = os.path.split(item)[1].split(".")[0]
                stepWidget.addItem(fileName + " | " + item)
                self.updateListAttr(stepWidget, stepAttr)

    def _customStepMenu(self, cs_listWidget, stepAttr, QPos, pre=True):
        """Right click context menu for custom step."""
        self.csMenu = QtWidgets.QMenu()
        parentPosition = cs_listWidget.mapToGlobal(QtCore.QPoint(0, 0))

        # Add/New actions (always available)
        add_action = self.csMenu.addAction("Add")
        add_action.setIcon(pyqt.get_icon("mgear_folder-plus"))
        new_action = self.csMenu.addAction("New")
        new_action.setIcon(pyqt.get_icon("mgear_file-plus"))

        self.csMenu.addSeparator()

        # Selection-dependent actions
        hasSelection = len(cs_listWidget.selectedItems()) > 0

        run_action = self.csMenu.addAction("Run Selected")
        run_action.setIcon(pyqt.get_icon("mgear_play"))
        run_action.setEnabled(hasSelection)

        edit_action = self.csMenu.addAction("Edit")
        edit_action.setIcon(pyqt.get_icon("mgear_edit"))
        edit_action.setEnabled(hasSelection)

        duplicate_action = self.csMenu.addAction("Duplicate")
        duplicate_action.setIcon(pyqt.get_icon("mgear_copy"))
        duplicate_action.setEnabled(hasSelection)

        remove_action = self.csMenu.addAction("Remove")
        remove_action.setIcon(pyqt.get_icon("mgear_trash-2"))
        remove_action.setEnabled(hasSelection)

        self.csMenu.addSeparator()

        # Toggle status actions
        toggle_action = self.csMenu.addAction("Toggle Status")
        toggle_action.setIcon(pyqt.get_icon("mgear_refresh-cw"))
        toggle_action.setEnabled(hasSelection)

        off_selected_action = self.csMenu.addAction("Turn OFF Selected")
        off_selected_action.setIcon(pyqt.get_icon("mgear_toggle-left"))
        off_selected_action.setEnabled(hasSelection)

        on_selected_action = self.csMenu.addAction("Turn ON Selected")
        on_selected_action.setIcon(pyqt.get_icon("mgear_toggle-right"))
        on_selected_action.setEnabled(hasSelection)

        self.csMenu.addSeparator()

        off_all_action = self.csMenu.addAction("Turn OFF All")
        off_all_action.setIcon(pyqt.get_icon("mgear_x-circle"))
        on_all_action = self.csMenu.addAction("Turn ON All")
        on_all_action.setIcon(pyqt.get_icon("mgear_check-circle"))

        # Connect actions
        add_action.triggered.connect(partial(self.addCustomStep, pre))
        new_action.triggered.connect(partial(self.newCustomStep, pre))
        run_action.triggered.connect(
            partial(self.runManualStep, cs_listWidget)
        )
        edit_action.triggered.connect(partial(self.editFile, cs_listWidget))
        duplicate_action.triggered.connect(
            partial(self.duplicateCustomStep, pre)
        )
        remove_action.triggered.connect(
            partial(
                self.removeSelectedFromListWidget, cs_listWidget, stepAttr
            )
        )
        toggle_action.triggered.connect(
            partial(self.toggleStatusCustomStep, cs_listWidget, stepAttr)
        )
        off_selected_action.triggered.connect(
            partial(self.setStatusCustomStep, cs_listWidget, stepAttr, False)
        )
        on_selected_action.triggered.connect(
            partial(self.setStatusCustomStep, cs_listWidget, stepAttr, True)
        )
        off_all_action.triggered.connect(
            partial(
                self.setStatusCustomStep, cs_listWidget, stepAttr, False, False
            )
        )
        on_all_action.triggered.connect(
            partial(
                self.setStatusCustomStep, cs_listWidget, stepAttr, True, False
            )
        )

        self.csMenu.move(parentPosition + QPos)
        self.csMenu.show()

    def preCustomStepMenu(self, QPos):
        """Show pre custom step context menu."""
        self._customStepMenu(
            self.customStepTab.preCustomStep_listWidget,
            "preCustomStep",
            QPos,
            pre=True,
        )

    def postCustomStepMenu(self, QPos):
        """Show post custom step context menu."""
        self._customStepMenu(
            self.customStepTab.postCustomStep_listWidget,
            "postCustomStep",
            QPos,
            pre=False,
        )

    def toggleStatusCustomStep(self, cs_listWidget, stepAttr):
        """Toggle the active status of selected custom steps."""
        items = cs_listWidget.selectedItems()
        for item in items:
            if item.text().startswith("*"):
                item.setText(item.text()[1:])
                item.setForeground(self.whiteDownBrush)
            else:
                item.setText("*" + item.text())
                item.setForeground(self.redBrush)

        self.updateListAttr(cs_listWidget, stepAttr)
        self.refreshStatusColor(cs_listWidget)

    def setStatusCustomStep(
        self, cs_listWidget, stepAttr, status=True, selected=True
    ):
        """Set the status of custom steps.

        Args:
            cs_listWidget: The list widget containing custom steps
            stepAttr: The Maya attribute name for this step list
            status: True to enable, False to disable
            selected: If True, only affect selected items; otherwise all
        """
        if selected:
            items = cs_listWidget.selectedItems()
        else:
            items = self.getAllItems(cs_listWidget)

        for item in items:
            off = item.text().startswith("*")
            if status and off:
                item.setText(item.text()[1:])
            elif not status and not off:
                item.setText("*" + item.text())
            self.setStatusColor(item)

        self.updateListAttr(cs_listWidget, stepAttr)
        self.refreshStatusColor(cs_listWidget)

    def getAllItems(self, cs_listWidget):
        """Get all items from a list widget."""
        return [cs_listWidget.item(i) for i in range(cs_listWidget.count())]

    def setStatusColor(self, item):
        """Set the color of a custom step item based on its status."""
        if item.text().startswith("*"):
            item.setForeground(self.redBrush)
        elif "_shared" in item.text():
            item.setForeground(self.greenBrush)
        else:
            item.setForeground(self.whiteDownBrush)

    def refreshStatusColor(self, cs_listWidget):
        """Refresh the colors of all items in a custom step list."""
        items = self.getAllItems(cs_listWidget)
        for i in items:
            self.setStatusColor(i)

    def _highlightSearch(self, cs_listWidget, searchText):
        """Highlight items matching search text."""
        items = self.getAllItems(cs_listWidget)
        for i in items:
            if searchText and searchText.lower() in i.text().lower():
                i.setBackground(QtGui.QColor(128, 128, 128, 255))
            else:
                i.setBackground(QtGui.QColor(255, 255, 255, 0))

    def preHighlightSearch(self):
        """Highlight pre custom step items matching search."""
        searchText = self.customStepTab.preSearch_lineEdit.text()
        self._highlightSearch(
            self.customStepTab.preCustomStep_listWidget, searchText
        )

    def postHighlightSearch(self):
        """Highlight post custom step items matching search."""
        searchText = self.customStepTab.postSearch_lineEdit.text()
        self._highlightSearch(
            self.customStepTab.postCustomStep_listWidget, searchText
        )


# Backwards compatibility alias
customStepTab = CustomStepTab

# Module-level function for external access (used by shifter build process)
runStep = CustomStepMixin.runStep
