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

# Author:     Jeremie Passerin
# Author:     Miquel Campos           www.mcsgear.com
# Date:       2016 / 10 / 10

from mgear.core import pyqt

QtGui, QtCore, QtWidgets, wrapInstance = pyqt.qt_import()


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(255, 290)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.mode_label = QtWidgets.QLabel(self.groupBox)
        self.mode_label.setObjectName("mode_label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.mode_label)
        self.mode_comboBox = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.mode_comboBox.sizePolicy().hasHeightForWidth()
        )
        self.mode_comboBox.setSizePolicy(sizePolicy)
        self.mode_comboBox.setObjectName("mode_comboBox")
        self.mode_comboBox.addItem("")
        self.mode_comboBox.addItem("")
        self.mode_comboBox.addItem("")
        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.FieldRole, self.mode_comboBox
        )
        self.ikfk_label = QtWidgets.QLabel(self.groupBox)
        self.ikfk_label.setObjectName("ikfk_label")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.ikfk_label)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.ikfk_slider = QtWidgets.QSlider(self.groupBox)
        self.ikfk_slider.setMinimumSize(QtCore.QSize(0, 15))
        self.ikfk_slider.setMaximum(100)
        self.ikfk_slider.setOrientation(QtCore.Qt.Horizontal)
        self.ikfk_slider.setObjectName("ikfk_slider")
        self.horizontalLayout_3.addWidget(self.ikfk_slider)
        self.ikfk_spinBox = QtWidgets.QSpinBox(self.groupBox)
        self.ikfk_spinBox.setMaximum(100)
        self.ikfk_spinBox.setObjectName("ikfk_spinBox")
        self.horizontalLayout_3.addWidget(self.ikfk_spinBox)
        self.formLayout.setLayout(
            1, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_3
        )
        self.verticalLayout.addLayout(self.formLayout)
        self.neutralPose_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.neutralPose_checkBox.setObjectName("neutralPose_checkBox")
        self.verticalLayout.addWidget(self.neutralPose_checkBox)
        self.gridLayout_2.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
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
        self.ikRefArray_listWidget.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )
        self.ikRefArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.ikRefArray_listWidget.setAlternatingRowColors(True)
        self.ikRefArray_listWidget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.ikRefArray_listWidget.setSelectionRectVisible(False)
        self.ikRefArray_listWidget.setObjectName("ikRefArray_listWidget")
        self.ikRefArray_verticalLayout_1.addWidget(self.ikRefArray_listWidget)
        self.ikRefArray_horizontalLayout.addLayout(self.ikRefArray_verticalLayout_1)
        self.ikRefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.ikRefArray_verticalLayout_2.setObjectName("ikRefArray_verticalLayout_2")
        self.ikRefArrayAdd_pushButton = QtWidgets.QPushButton(self.ikRefArray_groupBox)
        self.ikRefArrayAdd_pushButton.setObjectName("ikRefArrayAdd_pushButton")
        self.ikRefArray_verticalLayout_2.addWidget(self.ikRefArrayAdd_pushButton)
        self.ikRefArrayRemove_pushButton = QtWidgets.QPushButton(
            self.ikRefArray_groupBox
        )
        self.ikRefArrayRemove_pushButton.setObjectName("ikRefArrayRemove_pushButton")
        self.ikRefArray_verticalLayout_2.addWidget(self.ikRefArrayRemove_pushButton)
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.ikRefArray_verticalLayout_2.addItem(spacerItem)
        self.ikRefArray_horizontalLayout.addLayout(self.ikRefArray_verticalLayout_2)
        self.gridLayout_3.addLayout(self.ikRefArray_horizontalLayout, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.ikRefArray_groupBox, 1, 0, 1, 1)

        self.splineIk_groupBox = QtWidgets.QGroupBox(Form)
        self.splineIk_groupBox.setObjectName("splineIk_groupBox")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.splineIk_groupBox)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.ikNb_horizontalLayout = QtWidgets.QHBoxLayout()
        self.ikNb_horizontalLayout.setObjectName("ikNb_horizontalLayout")
        self.ikNb_label = QtWidgets.QLabel(self.splineIk_groupBox)
        self.ikNb_label.setObjectName("ikNb_label")
        self.ikNb_horizontalLayout.addWidget(self.ikNb_label)
        self.ikNb_spinBox = QtWidgets.QSpinBox(self.splineIk_groupBox)
        self.ikNb_spinBox.setMinimum(2)
        self.ikNb_spinBox.setMaximum(999)
        self.ikNb_spinBox.setProperty("value", 3)
        self.ikNb_spinBox.setObjectName("ikNb_spinBox")
        self.ikNb_horizontalLayout.addWidget(self.ikNb_spinBox)
        self.gridLayout_4.addLayout(self.ikNb_horizontalLayout, 0, 0, 1, 1)
        self.twistFalloff_horizontalLayout = QtWidgets.QHBoxLayout()
        self.twistFalloff_horizontalLayout.setObjectName(
            "twistFalloff_horizontalLayout"
        )
        self.twistFalloff_label = QtWidgets.QLabel(self.splineIk_groupBox)
        self.twistFalloff_label.setObjectName("twistFalloff_label")
        self.twistFalloff_horizontalLayout.addWidget(self.twistFalloff_label)
        self.twistFalloff_spinBox = QtWidgets.QDoubleSpinBox(self.splineIk_groupBox)
        self.twistFalloff_spinBox.setMinimum(0.05)
        self.twistFalloff_spinBox.setMaximum(2.0)
        self.twistFalloff_spinBox.setSingleStep(0.05)
        self.twistFalloff_spinBox.setProperty("value", 1.0)
        self.twistFalloff_spinBox.setObjectName("twistFalloff_spinBox")
        self.twistFalloff_horizontalLayout.addWidget(self.twistFalloff_spinBox)
        self.gridLayout_4.addLayout(self.twistFalloff_horizontalLayout, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.splineIk_groupBox, 2, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QObject.connect(
            self.ikfk_slider,
            QtCore.SIGNAL("sliderMoved(int)"),
            self.ikfk_spinBox.setValue,
        )
        QtCore.QObject.connect(
            self.ikfk_spinBox,
            QtCore.SIGNAL("valueChanged(int)"),
            self.ikfk_slider.setValue,
        )
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(pyqt.fakeTranslate("Form", "Form", None, -1))
        self.mode_label.setText(pyqt.fakeTranslate("Form", "Mode:", None, -1))
        self.mode_comboBox.setItemText(0, pyqt.fakeTranslate("Form", "FK", None, -1))
        self.mode_comboBox.setItemText(1, pyqt.fakeTranslate("Form", "IK", None, -1))
        self.mode_comboBox.setItemText(2, pyqt.fakeTranslate("Form", "FK/IK", None, -1))
        self.ikfk_label.setText(pyqt.fakeTranslate("Form", "IK/FK Blend:", None, -1))
        self.neutralPose_checkBox.setText(
            pyqt.fakeTranslate("Form", "Neutral pose", None, -1)
        )
        self.ikRefArray_groupBox.setTitle(
            pyqt.fakeTranslate("Form", "IK Reference Array", None, -1)
        )
        self.ikRefArrayAdd_pushButton.setText(
            pyqt.fakeTranslate("Form", "<<", None, -1)
        )
        self.ikRefArrayRemove_pushButton.setText(
            pyqt.fakeTranslate("Form", ">>", None, -1)
        )
        self.splineIk_groupBox.setTitle(
            pyqt.fakeTranslate("Form", "Spline IK", None, -1)
        )
        self.ikNb_label.setText(pyqt.fakeTranslate("Form", "IK Controls:", None, -1))
        self.twistFalloff_label.setText(
            pyqt.fakeTranslate("Form", "Twist Falloff", None, -1)
        )
