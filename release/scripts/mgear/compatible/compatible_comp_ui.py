from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(236, 113)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.components_label = QtWidgets.QLabel(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.components_label.sizePolicy().hasHeightForWidth()
        )
        self.components_label.setSizePolicy(sizePolicy)
        self.components_label.setObjectName("components_label")
        self.horizontalLayout_2.addWidget(self.components_label)
        self.components_comboBox = QtWidgets.QComboBox(Dialog)
        self.components_comboBox.setObjectName("components_comboBox")
        self.horizontalLayout_2.addWidget(self.components_comboBox)
        self.gridLayout.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout.addItem(spacerItem, 4, 0, 1, 1)
        self.update_checkBox = QtWidgets.QCheckBox(Dialog)
        self.update_checkBox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.update_checkBox.setObjectName("update_checkBox")
        self.update_checkBox.setChecked(True)
        self.gridLayout.addWidget(self.update_checkBox, 1, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(
            QtWidgets.QApplication.translate("Dialog", "Dialog", None, -1)
        )
        self.components_label.setText(
            QtWidgets.QApplication.translate("Dialog", "Related components：", None, -1)
        )
        self.update_checkBox.setText(
            QtWidgets.QApplication.translate("Dialog", "Update Guide", None, -1)
        )
