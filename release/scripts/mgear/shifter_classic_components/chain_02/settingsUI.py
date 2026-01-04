# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Author:     Joji Nishimura
# Date:       2024 / 01 / 01

import mgear.core.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(255, 290)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.main_groupBox = QtWidgets.QGroupBox(Form)
        self.main_groupBox.setTitle("")
        self.main_groupBox.setObjectName("main_groupBox")
        self.main_gridLayout = QtWidgets.QGridLayout(self.main_groupBox)
        self.main_gridLayout.setObjectName("main_gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.ikfk_formLayout = QtWidgets.QFormLayout()
        self.ikfk_formLayout.setObjectName("ikfk_formLayout")
        self.mode_label = QtWidgets.QLabel(self.main_groupBox)
        self.mode_label.setObjectName("mode_label")
        self.ikfk_formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.mode_label)
        self.mode_comboBox = QtWidgets.QComboBox(self.main_groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.mode_comboBox.sizePolicy().hasHeightForWidth())
        self.mode_comboBox.setSizePolicy(sizePolicy)
        self.mode_comboBox.setObjectName("mode_comboBox")
        self.mode_comboBox.addItem("")
        self.mode_comboBox.addItem("")
        self.mode_comboBox.addItem("")
        self.ikfk_formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.mode_comboBox)
        self.ikfk_label = QtWidgets.QLabel(self.main_groupBox)
        self.ikfk_label.setObjectName("ikfk_label")
        self.ikfk_formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.ikfk_label)
        self.ikfk_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ikfk_horizontalLayout.setObjectName("ikfk_horizontalLayout")
        self.ikfk_slider = QtWidgets.QSlider(self.main_groupBox)
        self.ikfk_slider.setMinimumSize(QtCore.QSize(0, 15))
        self.ikfk_slider.setMaximum(100)
        self.ikfk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.ikfk_slider.setObjectName("ikfk_slider")
        self.ikfk_horizontalLayout.addWidget(self.ikfk_slider)
        self.ikfk_spinBox = QtWidgets.QSpinBox(self.main_groupBox)
        self.ikfk_spinBox.setMaximum(100)
        self.ikfk_spinBox.setObjectName("ikfk_spinBox")
        self.ikfk_horizontalLayout.addWidget(self.ikfk_spinBox)
        self.ikfk_formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.ikfk_horizontalLayout)
        self.verticalLayout.addLayout(self.ikfk_formLayout)
        self.neutralPose_checkBox = QtWidgets.QCheckBox(self.main_groupBox)
        self.neutralPose_checkBox.setObjectName("neutralPose_checkBox")
        self.verticalLayout.addWidget(self.neutralPose_checkBox)
        self.aiming_checkBox = QtWidgets.QCheckBox(self.main_groupBox)
        self.aiming_checkBox.setObjectName("aiming_checkBox")
        self.verticalLayout.addWidget(self.aiming_checkBox)
        self.mirrorBehaviour_checkBox = QtWidgets.QCheckBox(self.main_groupBox)
        self.mirrorBehaviour_checkBox.setObjectName("mirrorBehaviour_checkBox")
        self.verticalLayout.addWidget(self.mirrorBehaviour_checkBox)
        self.main_gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.main_groupBox, 0, 0, 1, 1)
        self.ikRefArray_groupBox = QtWidgets.QGroupBox(Form)
        self.ikRefArray_groupBox.setObjectName("ikRefArray_groupBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.ikRefArray_groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.ikRefArray_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ikRefArray_horizontalLayout.setObjectName("ikRefArray_horizontalLayout")
        self.ikRefArray_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.ikRefArray_verticalLayout_1.setObjectName("ikRefArray_verticalLayout_1")
        self.ikRefArray_listWidget = QtWidgets.QListWidget(self.ikRefArray_groupBox)
        self.ikRefArray_listWidget.setDragDropOverwriteMode(True)
        self.ikRefArray_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.ikRefArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.ikRefArray_listWidget.setAlternatingRowColors(True)
        self.ikRefArray_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.ikRefArray_listWidget.setSelectionRectVisible(False)
        self.ikRefArray_listWidget.setObjectName("ikRefArray_listWidget")
        self.ikRefArray_verticalLayout_1.addWidget(self.ikRefArray_listWidget)
        self.ikRefArray_horizontalLayout.addLayout(self.ikRefArray_verticalLayout_1)
        self.ikRefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.ikRefArray_verticalLayout_2.setObjectName("ikRefArray_verticalLayout_2")
        self.ikRefArrayAdd_pushButton = QtWidgets.QPushButton(self.ikRefArray_groupBox)
        self.ikRefArrayAdd_pushButton.setObjectName("ikRefArrayAdd_pushButton")
        self.ikRefArray_verticalLayout_2.addWidget(self.ikRefArrayAdd_pushButton)
        self.ikRefArrayRemove_pushButton = QtWidgets.QPushButton(self.ikRefArray_groupBox)
        self.ikRefArrayRemove_pushButton.setObjectName("ikRefArrayRemove_pushButton")
        self.ikRefArray_verticalLayout_2.addWidget(self.ikRefArrayRemove_pushButton)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.ikRefArray_verticalLayout_2.addItem(spacerItem)
        self.ikRefArray_horizontalLayout.addLayout(self.ikRefArray_verticalLayout_2)
        self.gridLayout_3.addLayout(self.ikRefArray_horizontalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.ikRefArray_groupBox, 1, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QObject.connect(self.ikfk_slider, QtCore.SIGNAL("sliderMoved(int)"), self.ikfk_spinBox.setValue)
        QtCore.QObject.connect(self.ikfk_spinBox, QtCore.SIGNAL("valueChanged(int)"), self.ikfk_slider.setValue)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.mode_label.setText(gqt.fakeTranslate("Form", "Mode:", None, -1))
        self.mode_comboBox.setItemText(0, gqt.fakeTranslate("Form", "FK", None, -1))
        self.mode_comboBox.setItemText(1, gqt.fakeTranslate("Form", "IK", None, -1))
        self.mode_comboBox.setItemText(2, gqt.fakeTranslate("Form", "FK/IK", None, -1))
        self.ikfk_label.setText(gqt.fakeTranslate("Form", "IK/FK Blend:", None, -1))
        self.neutralPose_checkBox.setText(gqt.fakeTranslate("Form", "Neutral pose", None, -1))
        self.aiming_checkBox.setText(gqt.fakeTranslate("Form", "Each segment aims at its child", None, -1))
        self.mirrorBehaviour_checkBox.setText(gqt.fakeTranslate("Form", "Mirror Behaviour L and R", None, -1))
        self.aiming_checkBox.setToolTip(gqt.fakeTranslate("Form", "<html><head/><body><p>Each segment aims at its child, so that you can translate without skewing.</p><p>It could be used in other areas like fingers.</p></body></html>", None, -1))
        self.ikRefArray_groupBox.setTitle(gqt.fakeTranslate("Form", "IK Reference Array", None, -1))
        self.ikRefArrayAdd_pushButton.setText(gqt.fakeTranslate("Form", "<<", None, -1))
        self.ikRefArrayRemove_pushButton.setText(gqt.fakeTranslate("Form", ">>", None, -1))

