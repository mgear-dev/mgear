# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:/Users/georg/OneDrive/Documents/maya/GitHub/mgear4/release/scripts/mgear/rigbits/gimmick_tool/gimmick_tool.ui',
# licensing of 'C:/Users/georg/OneDrive/Documents/maya/GitHub/mgear4/release/scripts/mgear/rigbits/gimmick_tool/gimmick_tool.ui' applies.
#
# Created: Fri Sep 22 08:36:27 2023
#      by: pyside2-uic  running on PySide2 5.12.5
#
# WARNING! All changes made in this file will be lost!

import mgear.core.pyqt as gqt
from mgear.vendor.Qt import QtCore, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(393, 365)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setTabShape(QtWidgets.QTabWidget.Rounded)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.creation_grpupBox = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.creation_grpupBox.sizePolicy().hasHeightForWidth())
        self.creation_grpupBox.setSizePolicy(sizePolicy)
        self.creation_grpupBox.setMaximumSize(QtCore.QSize(16777215, 140))
        self.creation_grpupBox.setObjectName("creation_grpupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.creation_grpupBox)
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setContentsMargins(40, 20, 40, 20)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.creation_horizontalLayout = QtWidgets.QHBoxLayout()
        self.creation_horizontalLayout.setSpacing(6)
        self.creation_horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.creation_horizontalLayout.setContentsMargins(-1, -1, -1, 0)
        self.creation_horizontalLayout.setObjectName("creation_horizontalLayout")
        self.blendJoint_pushButton = QtWidgets.QPushButton(self.creation_grpupBox)
        self.blendJoint_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.blendJoint_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    background-color: #5D5D5D;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.blendJoint_pushButton.setObjectName("blendJoint_pushButton")
        self.creation_horizontalLayout.addWidget(self.blendJoint_pushButton)
        self.supportJoint_pushButton = QtWidgets.QPushButton(self.creation_grpupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.supportJoint_pushButton.sizePolicy().hasHeightForWidth())
        self.supportJoint_pushButton.setSizePolicy(sizePolicy)
        self.supportJoint_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.supportJoint_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    background-color: #5D5D5D;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.supportJoint_pushButton.setObjectName("supportJoint_pushButton")
        self.creation_horizontalLayout.addWidget(self.supportJoint_pushButton)
        self.verticalLayout_2.addLayout(self.creation_horizontalLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.mirrorGimmick_pushButton = QtWidgets.QPushButton(self.creation_grpupBox)
        self.mirrorGimmick_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.mirrorGimmick_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    background-color: #5D5D5D;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.mirrorGimmick_pushButton.setObjectName("mirrorGimmick_pushButton")
        self.horizontalLayout.addWidget(self.mirrorGimmick_pushButton)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout.addWidget(self.creation_grpupBox)
        self.utility_groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.utility_groupBox.setFlat(False)
        self.utility_groupBox.setObjectName("utility_groupBox")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.utility_groupBox)
        self.verticalLayout_4.setSpacing(12)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.utility_verticalLayout = QtWidgets.QVBoxLayout()
        self.utility_verticalLayout.setSpacing(10)
        self.utility_verticalLayout.setObjectName("utility_verticalLayout")
        self.utility_horizontalLayout1 = QtWidgets.QHBoxLayout()
        self.utility_horizontalLayout1.setSpacing(6)
        self.utility_horizontalLayout1.setContentsMargins(-1, -1, 0, 0)
        self.utility_horizontalLayout1.setObjectName("utility_horizontalLayout1")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.utility_horizontalLayout1.addItem(spacerItem)
        self.utility_all_checkBox = QtWidgets.QCheckBox(self.utility_groupBox)
        self.utility_all_checkBox.setObjectName("utility_all_checkBox")
        self.utility_horizontalLayout1.addWidget(self.utility_all_checkBox)
        spacerItem1 = QtWidgets.QSpacerItem(5, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.utility_horizontalLayout1.addItem(spacerItem1)
        self.utility_left_checkBox = QtWidgets.QCheckBox(self.utility_groupBox)
        self.utility_left_checkBox.setChecked(True)
        self.utility_left_checkBox.setObjectName("utility_left_checkBox")
        self.utility_horizontalLayout1.addWidget(self.utility_left_checkBox)
        self.utility_center_checkBox = QtWidgets.QCheckBox(self.utility_groupBox)
        self.utility_center_checkBox.setObjectName("utility_center_checkBox")
        self.utility_horizontalLayout1.addWidget(self.utility_center_checkBox)
        self.utility_right_checkBox = QtWidgets.QCheckBox(self.utility_groupBox)
        self.utility_right_checkBox.setObjectName("utility_right_checkBox")
        self.utility_horizontalLayout1.addWidget(self.utility_right_checkBox)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.utility_horizontalLayout1.addItem(spacerItem2)
        self.utility_verticalLayout.addLayout(self.utility_horizontalLayout1)
        self.utility_horizontalLayout2 = QtWidgets.QHBoxLayout()
        self.utility_horizontalLayout2.setSpacing(6)
        self.utility_horizontalLayout2.setContentsMargins(30, -1, 30, -1)
        self.utility_horizontalLayout2.setObjectName("utility_horizontalLayout2")
        self.select_pushButton = QtWidgets.QPushButton(self.utility_groupBox)
        self.select_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.select_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    background-color: #5D5D5D;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.select_pushButton.setObjectName("select_pushButton")
        self.utility_horizontalLayout2.addWidget(self.select_pushButton)
        self.delete_pushButton = QtWidgets.QPushButton(self.utility_groupBox)
        self.delete_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.delete_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    background-color: #5D5D5D;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.delete_pushButton.setObjectName("delete_pushButton")
        self.utility_horizontalLayout2.addWidget(self.delete_pushButton)
        self.utility_verticalLayout.addLayout(self.utility_horizontalLayout2)
        self.verticalLayout_4.addLayout(self.utility_verticalLayout)
        self.flipJoint_groupBox = QtWidgets.QGroupBox(self.utility_groupBox)
        self.flipJoint_groupBox.setAlignment(QtCore.Qt.AlignCenter)
        self.flipJoint_groupBox.setFlat(False)
        self.flipJoint_groupBox.setCheckable(False)
        self.flipJoint_groupBox.setObjectName("flipJoint_groupBox")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.flipJoint_groupBox)
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setContentsMargins(0, -1, 0, -1)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.flipJoint_horizontalLayout = QtWidgets.QHBoxLayout()
        self.flipJoint_horizontalLayout.setSpacing(6)
        self.flipJoint_horizontalLayout.setContentsMargins(29, -1, 29, -1)
        self.flipJoint_horizontalLayout.setObjectName("flipJoint_horizontalLayout")
        self.flipJointX_pushButton = QtWidgets.QPushButton(self.flipJoint_groupBox)
        self.flipJointX_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.flipJointX_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    border: 2px solid #414141;\n"
"    background-color: #434343;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.flipJointX_pushButton.setFlat(True)
        self.flipJointX_pushButton.setObjectName("flipJointX_pushButton")
        self.flipJoint_horizontalLayout.addWidget(self.flipJointX_pushButton)
        self.flipJointY_pushButton = QtWidgets.QPushButton(self.flipJoint_groupBox)
        self.flipJointY_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.flipJointY_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    border: 2px solid #414141;\n"
"    background-color: #434343;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.flipJointY_pushButton.setFlat(True)
        self.flipJointY_pushButton.setObjectName("flipJointY_pushButton")
        self.flipJoint_horizontalLayout.addWidget(self.flipJointY_pushButton)
        self.flipJointZ_pushButton = QtWidgets.QPushButton(self.flipJoint_groupBox)
        self.flipJointZ_pushButton.setMinimumSize(QtCore.QSize(0, 23))
        self.flipJointZ_pushButton.setStyleSheet("QPushButton {\n"
"    border-radius: 4px;\n"
"    border: 2px solid #414141;\n"
"    background-color: #434343;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #00A6F3;\n"
"}\n"
"QPushButton:hover:!pressed {\n"
"    background-color: #707070;\n"
"}")
        self.flipJointZ_pushButton.setFlat(True)
        self.flipJointZ_pushButton.setObjectName("flipJointZ_pushButton")
        self.flipJoint_horizontalLayout.addWidget(self.flipJointZ_pushButton)
        self.verticalLayout_5.addLayout(self.flipJoint_horizontalLayout)
        self.verticalLayout_4.addWidget(self.flipJoint_groupBox)
        spacerItem3 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem3)
        self.verticalLayout.addWidget(self.utility_groupBox)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 393, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.importGimmick_menuAction = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("../../../../icons/mgear_log-in.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon.addPixmap(QtGui.QPixmap("../../../../icons/mgear_log-in.svg"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.importGimmick_menuAction.setIcon(icon)
        self.importGimmick_menuAction.setObjectName("importGimmick_menuAction")
        self.exportGimmick_menuAction = QtWidgets.QAction(MainWindow)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("../../../../icons/mgear_log-out.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        icon1.addPixmap(QtGui.QPixmap("../../../../icons/mgear_log-out.svg"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.exportGimmick_menuAction.setIcon(icon1)
        self.exportGimmick_menuAction.setObjectName("exportGimmick_menuAction")
        self.menuFile.addAction(self.importGimmick_menuAction)
        self.menuFile.addAction(self.exportGimmick_menuAction)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", "Gimmick Setup Tool", None, -1))
        self.creation_grpupBox.setTitle(QtWidgets.QApplication.translate("MainWindow", "Gimmick Creation", None, -1))
        self.blendJoint_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Blend Joint", None, -1))
        self.supportJoint_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Support Joint", None, -1))
        self.mirrorGimmick_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Mirror Gimmick", None, -1))
        self.utility_groupBox.setTitle(QtWidgets.QApplication.translate("MainWindow", "Utility", None, -1))
        self.utility_all_checkBox.setText(QtWidgets.QApplication.translate("MainWindow", "All :", None, -1))
        self.utility_left_checkBox.setText(QtWidgets.QApplication.translate("MainWindow", "Left", None, -1))
        self.utility_center_checkBox.setText(QtWidgets.QApplication.translate("MainWindow", "Center", None, -1))
        self.utility_right_checkBox.setText(QtWidgets.QApplication.translate("MainWindow", "Right", None, -1))
        self.select_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Select", None, -1))
        self.delete_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Delete", None, -1))
        self.flipJoint_groupBox.setTitle(QtWidgets.QApplication.translate("MainWindow", "Flip Joint (Support)", None, -1))
        self.flipJointX_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "X", None, -1))
        self.flipJointY_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Y", None, -1))
        self.flipJointZ_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "Z", None, -1))
        self.menuFile.setTitle(QtWidgets.QApplication.translate("MainWindow", "File", None, -1))
        self.importGimmick_menuAction.setText(QtWidgets.QApplication.translate("MainWindow", "Import Gimmick Data", None, -1))
        self.exportGimmick_menuAction.setText(QtWidgets.QApplication.translate("MainWindow", "Export Gimmick Data", None, -1))

