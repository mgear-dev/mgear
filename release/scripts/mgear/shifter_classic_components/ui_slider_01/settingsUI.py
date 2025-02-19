# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settingsUI.ui',
# licensing of 'settingsUI.ui' applies.
#
# Created: Tue Oct 22 22:39:44 2019
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
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.formLayout = QtWidgets.QFormLayout(self.groupBox)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.mirror_behaviour_checkbox = QtWidgets.QCheckBox(self.groupBox)
        self.mirror_behaviour_checkbox.setText("")
        self.mirror_behaviour_checkbox.setChecked(True)
        self.mirror_behaviour_checkbox.setObjectName("mirror_behaviour_checkbox")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.mirror_behaviour_checkbox)
        self.control_size_label = QtWidgets.QLabel(self.groupBox)
        self.control_size_label.setObjectName("control_size_label")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.control_size_label)
        self.control_size_spinbox = QtWidgets.QDoubleSpinBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.control_size_spinbox.sizePolicy().hasHeightForWidth())
        self.control_size_spinbox.setSizePolicy(sizePolicy)
        self.control_size_spinbox.setWrapping(False)
        self.control_size_spinbox.setAlignment(QtCore.Qt.AlignCenter)
        self.control_size_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.PlusMinus)
        self.control_size_spinbox.setMinimum(0.01)
        self.control_size_spinbox.setMaximum(20000.0)
        self.control_size_spinbox.setSingleStep(0.1)
        self.control_size_spinbox.setProperty("value", 0.25)
        self.control_size_spinbox.setObjectName("control_size_spinbox")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.control_size_spinbox)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.keyable_groupBox = QtWidgets.QGroupBox(Form)
        self.keyable_groupBox.setObjectName("keyable_groupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.keyable_groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.negative_label = QtWidgets.QLabel(self.keyable_groupBox)
        self.negative_label.setObjectName("negative_label")
        self.gridLayout_2.addWidget(self.negative_label, 0, 1, 1, 1)
        self.positive_label = QtWidgets.QLabel(self.keyable_groupBox)
        self.positive_label.setObjectName("positive_label")
        self.gridLayout_2.addWidget(self.positive_label, 0, 2, 1, 1)
        self.translate_x_label = QtWidgets.QLabel(self.keyable_groupBox)
        self.translate_x_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.translate_x_label.setObjectName("translate_x_label")
        self.gridLayout_2.addWidget(self.translate_x_label, 1, 0, 1, 1)
        self.translate_x_negative_checkbox = QtWidgets.QCheckBox(self.keyable_groupBox)
        self.translate_x_negative_checkbox.setText("")
        self.translate_x_negative_checkbox.setChecked(True)
        self.translate_x_negative_checkbox.setObjectName("translate_x_negative_checkbox")
        self.gridLayout_2.addWidget(self.translate_x_negative_checkbox, 1, 1, 1, 1)
        self.translate_x_positive_checkbox = QtWidgets.QCheckBox(self.keyable_groupBox)
        self.translate_x_positive_checkbox.setText("")
        self.translate_x_positive_checkbox.setChecked(True)
        self.translate_x_positive_checkbox.setObjectName("translate_x_positive_checkbox")
        self.gridLayout_2.addWidget(self.translate_x_positive_checkbox, 1, 2, 1, 1)
        self.translate_y_label = QtWidgets.QLabel(self.keyable_groupBox)
        self.translate_y_label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.translate_y_label.setObjectName("translate_y_label")
        self.gridLayout_2.addWidget(self.translate_y_label, 2, 0, 1, 1)
        self.translate_y_negative_checkbox = QtWidgets.QCheckBox(self.keyable_groupBox)
        self.translate_y_negative_checkbox.setText("")
        self.translate_y_negative_checkbox.setChecked(True)
        self.translate_y_negative_checkbox.setObjectName("translate_y_negative_checkbox")
        self.gridLayout_2.addWidget(self.translate_y_negative_checkbox, 2, 1, 1, 1)
        self.translate_y_positive_checkbox = QtWidgets.QCheckBox(self.keyable_groupBox)
        self.translate_y_positive_checkbox.setText("")
        self.translate_y_positive_checkbox.setChecked(True)
        self.translate_y_positive_checkbox.setObjectName("translate_y_positive_checkbox")
        self.gridLayout_2.addWidget(self.translate_y_positive_checkbox, 2, 2, 1, 1)
        self.gridLayout.addWidget(self.keyable_groupBox, 1, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 2, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Form", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("Form", "Mirror Behaviour L and R", None, -1))
        self.mirror_behaviour_checkbox.setToolTip(QtWidgets.QApplication.translate("Form", "<html><head/><body><p>If is active, the control will have symmetrical behaviour on Left and Right side.</p><p><br/></p><p>WARNING: There is a bug in Maya 2018 and 2018.1 that will result in an incorrect behaviour, because this option will negate one of the axis. Other Maya version should be ok.</p></body></html>", None, -1))
        self.control_size_label.setText(QtWidgets.QApplication.translate("Form", "Control Size", None, -1))
        self.keyable_groupBox.setTitle(QtWidgets.QApplication.translate("Form", "Range of Motion", None, -1))
        self.negative_label.setText(QtWidgets.QApplication.translate("Form", "Negative", None, -1))
        self.positive_label.setText(QtWidgets.QApplication.translate("Form", "Positive", None, -1))
        self.translate_x_label.setText(QtWidgets.QApplication.translate("Form", "Translate X", None, -1))
        self.translate_y_label.setText(QtWidgets.QApplication.translate("Form", "Translate Y", None, -1))

