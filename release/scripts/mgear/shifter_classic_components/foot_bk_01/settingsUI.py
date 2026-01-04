import mgear.core.pyqt as gqt
QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(244, 321)
        self.gridLayout_2 = QtWidgets.QGridLayout(Form)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.useRollCtl_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.useRollCtl_checkBox.setObjectName("useRollCtl_checkBox")
        self.gridLayout.addWidget(self.useRollCtl_checkBox, 0, 0, 1, 1)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.maxStretch_label = QtWidgets.QLabel(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.maxStretch_label.sizePolicy().hasHeightForWidth())
        self.maxStretch_label.setSizePolicy(sizePolicy)
        self.maxStretch_label.setObjectName("maxStretch_label")
        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.LabelRole, self.maxStretch_label)
        self.rollAngle_spinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.rollAngle_spinBox.sizePolicy().hasHeightForWidth())
        self.rollAngle_spinBox.setSizePolicy(sizePolicy)
        self.rollAngle_spinBox.setDecimals(2)
        self.rollAngle_spinBox.setMinimum(-180.0)
        self.rollAngle_spinBox.setMaximum(180.0)
        self.rollAngle_spinBox.setSingleStep(5.0)
        self.rollAngle_spinBox.setProperty("value", -20.0)
        self.rollAngle_spinBox.setObjectName("rollAngle_spinBox")
        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.FieldRole, self.rollAngle_spinBox)
        self.gridLayout.addLayout(self.formLayout, 1, 0, 1, 1)
        self.gridLayout_2.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.useRollCtl_checkBox.setText(
            gqt.fakeTranslate("Form", "Use Roll Ctl", None, -1))
        self.maxStretch_label.setText(gqt.fakeTranslate(
            "Form", "Default Roll Angle", None, -1))
