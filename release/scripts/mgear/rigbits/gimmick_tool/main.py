import os

import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from PySide2 import QtWidgets, QtCore
from PySide2.QtUiTools import QUiLoader

from mgear.core import pyqt
from . import core


def mainUI():
    if GimmickSetupWindow.windowExists():
        GimmickSetupWindow.closeWindow()
    pyqt.showDialog(GimmickSetupWindow)


def undoable(func):
    """
    A decorator to make the wrapped function's operations undoable in a single step in Maya.
    """

    def wrapped(*args, **kwargs):
        pm.undoInfo(openChunk=True)
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print("Error:", e)
            raise
        finally:
            pm.undoInfo(closeChunk=True)
        return result

    return wrapped


class GimmickSetupWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):

    WINDOW_NAME = "GimmickSetupWindow"

    def __init__(self, parent=None):
        super(GimmickSetupWindow, self).__init__(parent)

        self.widget = self.initUI()

        self.toolName = self.widget.windowTitle()
        self.setMenuIcon()
        self.setCentralWidget(self.widget)
        self.setWindowTitle(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, 1)
        self.setObjectName(self.WINDOW_NAME)
        self.state = False

        self.connectCommand()

    @staticmethod
    def windowExists():
        """Check if the window exists.
        """
        return pm.workspaceControl(GimmickSetupWindow.WINDOW_NAME, exists=True)

    @staticmethod
    def closeWindow():
        """Close the window if it exists.
        """
        if GimmickSetupWindow.windowExists():
            pm.deleteUI(GimmickSetupWindow.WINDOW_NAME)

    @staticmethod
    def initUI(uiPath=None):
        if not uiPath:
            dirName = os.path.dirname(__file__)
            baseName = os.path.basename(dirName)
            uiPath = "{path}/{name}.ui".format(path=dirName, name=baseName)

        f = QtCore.QFile(uiPath)
        f.open(QtCore.QFile.ReadOnly)

        widget = QUiLoader().load(f, parentWidget=None)
        return widget

    def setMenuIcon(self):
        importIcon = pyqt.get_icon("mgear_log-in")
        exportIcon = pyqt.get_icon("mgear_log-out")
        self.widget.importGimmick_menuAction.setIcon(importIcon)
        self.widget.exportGimmick_menuAction.setIcon(exportIcon)

    def connectCommand(self):
        self.widget.blendJoint_pushButton.clicked.connect(self._createBlendJointCmd)
        self.widget.supportJoint_pushButton.clicked.connect(self._createSupportJntCmd)
        self.widget.mirrorGimmick_pushButton.clicked.connect(self._mirrorCmd)
        self.widget.select_pushButton.clicked.connect(self._selectGimmickJntCmd)
        self.widget.delete_pushButton.clicked.connect(self._deleteGimmickJntCmd)
        self.widget.utility_all_checkBox.stateChanged.connect(self._changeAllStateCmd)
        self.widget.flipJointX_pushButton.clicked.connect(lambda: self._flipJoint("X"))
        self.widget.flipJointY_pushButton.clicked.connect(lambda: self._flipJoint("Y"))
        self.widget.flipJointZ_pushButton.clicked.connect(lambda: self._flipJoint("Z"))

        # menu
        self.widget.importGimmick_menuAction.triggered.connect(self._importGimmickData)
        self.widget.exportGimmick_menuAction.triggered.connect(self._exportGimmickData)

    @undoable
    def _createBlendJointCmd(self):
        gimmickJnt = core.GimmickBlend()
        gimmickJnt.create()

    @undoable
    def _createSupportJntCmd(self):
        gimmickJnt = core.GimmickSupport()
        gimmickJnt.create()

    @undoable
    def _mirrorCmd(self):
        gimmickJnt = core.GimmickBlend()
        gimmickJnt.mirror()

    @undoable
    def _flipJoint(self, axis):
        gimmickJnt = core.GimmickSupport()
        gimmickJnt.flipJointOrientation(axis)

    def _selectGimmickJntCmd(self):
        joints, sideList = [], []
        if self.widget.utility_left_checkBox.isChecked():
            sideList.append("Left")
        if self.widget.utility_right_checkBox.isChecked():
            sideList.append("Right")
        if self.widget.utility_center_checkBox.isChecked():
            sideList.append("Center")

        gimmickJnt = core.GimmickJoint()
        for sideStr in sideList:
            joints.extend(gimmickJnt.select("Blend", side=sideStr))
        pm.select(joints)
        return joints

    def _changeAllStateCmd(self):
        if not self.state:
            self.widget.utility_left_checkBox.setChecked(True)
            self.widget.utility_right_checkBox.setChecked(True)
            self.widget.utility_center_checkBox.setChecked(True)
            self.state = True
        else:
            self.widget.utility_left_checkBox.setChecked(False)
            self.widget.utility_right_checkBox.setChecked(False)
            self.widget.utility_center_checkBox.setChecked(False)
            self.state = False

    @undoable
    def _deleteGimmickJntCmd(self):
        gimmick = self._selectGimmickJntCmd()
        pm.delete(gimmick)

    @undoable
    def _importGimmickData(self):
        gimmick = core.GimmickJointIO()
        gimmick.importGimmickJoint()

    @undoable
    def _exportGimmickData(self):
        gimmick = core.GimmickJointIO()
        gimmick.exportGimmickJoint()
