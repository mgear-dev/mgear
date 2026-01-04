# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settingsUI.ui',
# licensing of 'settingsUI.ui' applies.
#
# Created: Tue Oct 22 22:39:38 2019
#      by: pyside2-uic  running on PySide2 5.13.1
#
# WARNING! All changes made in this file will be lost!

import mgear.core.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(412, 345)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 2, 0, 1, 1)
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.formLayout_2 = QtWidgets.QFormLayout(self.groupBox)
        self.formLayout_2.setObjectName("formLayout_2")
        self.control_size_label = QtWidgets.QLabel(self.groupBox)
        self.control_size_label.setObjectName("control_size_label")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.control_size_label)
        self.control_size_spinbox = QtWidgets.QDoubleSpinBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.control_size_spinbox.sizePolicy().hasHeightForWidth())
        self.control_size_spinbox.setSizePolicy(sizePolicy)
        self.control_size_spinbox.setAlignment(QtCore.Qt.AlignCenter)
        self.control_size_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.PlusMinus)
        self.control_size_spinbox.setMinimum(0.1)
        self.control_size_spinbox.setMaximum(10.0)
        self.control_size_spinbox.setSingleStep(0.1)
        self.control_size_spinbox.setProperty("value", 1.0)
        self.control_size_spinbox.setObjectName("control_size_spinbox")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.control_size_spinbox)
        self.control_label = QtWidgets.QLabel(self.groupBox)
        self.control_label.setObjectName("control_label")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.control_label)
        self.control_checkbox = QtWidgets.QCheckBox(self.groupBox)
        self.control_checkbox.setText("")
        self.control_checkbox.setChecked(True)
        self.control_checkbox.setObjectName("control_checkbox")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.control_checkbox)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(Form)
        self.groupBox_2.setObjectName("groupBox_2")
        self.formLayout = QtWidgets.QFormLayout(self.groupBox_2)
        self.formLayout.setObjectName("formLayout")
        self.margin_label = QtWidgets.QLabel(self.groupBox_2)
        self.margin_label.setObjectName("margin_label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.margin_label)
        self.margin_spinbox = QtWidgets.QDoubleSpinBox(self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.margin_spinbox.sizePolicy().hasHeightForWidth())
        self.margin_spinbox.setSizePolicy(sizePolicy)
        self.margin_spinbox.setWrapping(False)
        self.margin_spinbox.setAlignment(QtCore.Qt.AlignCenter)
        self.margin_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.PlusMinus)
        self.margin_spinbox.setMinimum(0.0)
        self.margin_spinbox.setMaximum(10.0)
        self.margin_spinbox.setSingleStep(0.1)
        self.margin_spinbox.setProperty("value", 0.2)
        self.margin_spinbox.setObjectName("margin_spinbox")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.margin_spinbox)
        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Form", None, -1))
        self.control_size_label.setText(QtWidgets.QApplication.translate("Form", "Control Size", None, -1))
        self.control_label.setText(QtWidgets.QApplication.translate("Form", "Create Controller", None, -1))
        self.groupBox_2.setTitle(QtWidgets.QApplication.translate("Form", "UI Settings", None, -1))
        self.margin_label.setText(QtWidgets.QApplication.translate("Form", "Border Margin", None, -1))

