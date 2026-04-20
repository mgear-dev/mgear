
from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_gameTools(object):

    def setupUi(self, gameTools):
        gameTools.setObjectName("gameTools")
        gameTools.resize(284, 332)
        self.gridLayout_4 = QtWidgets.QGridLayout(gameTools)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.gameTools_groupBox = QtWidgets.QGroupBox(gameTools)
        self.gameTools_groupBox.setObjectName("gameTools_groupBox")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.gameTools_groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.assetName_frame = QtWidgets.QFrame(self.gameTools_groupBox)
        self.assetName_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.assetName_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.assetName_frame.setObjectName("assetName_frame")
        self.gridLayout = QtWidgets.QGridLayout(self.assetName_frame)
        self.gridLayout.setObjectName("gridLayout")
        self.assetName_lineEdit = QtWidgets.QLineEdit(self.assetName_frame)
        self.assetName_lineEdit.setObjectName("assetName_lineEdit")
        self.gridLayout.addWidget(self.assetName_lineEdit, 0, 2, 1, 1)
        self.assetName_label = QtWidgets.QLabel(self.assetName_frame)
        self.assetName_label.setObjectName("assetName_label")
        self.gridLayout.addWidget(self.assetName_label, 0, 1, 1, 1)
        self.gridLayout_2.addWidget(self.assetName_frame, 0, 0, 1, 2)
        self.rigNode_lineEdit = QtWidgets.QLineEdit(self.gameTools_groupBox)
        self.rigNode_lineEdit.setObjectName("rigNode_lineEdit")
        self.gridLayout_2.addWidget(self.rigNode_lineEdit, 1, 0, 1, 1)
        self.rigNode_pushButton = QtWidgets.QPushButton(
            self.gameTools_groupBox)
        self.rigNode_pushButton.setObjectName("rigNode_pushButton")
        self.gridLayout_2.addWidget(self.rigNode_pushButton, 1, 1, 1, 1)
        self.meshNode_lineEdit = QtWidgets.QLineEdit(self.gameTools_groupBox)
        self.meshNode_lineEdit.setObjectName("meshNode_lineEdit")
        self.gridLayout_2.addWidget(self.meshNode_lineEdit, 2, 0, 1, 1)
        self.meshNode_pushButton = QtWidgets.QPushButton(
            self.gameTools_groupBox)
        self.meshNode_pushButton.setObjectName("meshNode_pushButton")
        self.gridLayout_2.addWidget(self.meshNode_pushButton, 2, 1, 1, 1)
        self.path_lineEdit = QtWidgets.QLineEdit(self.gameTools_groupBox)
        self.path_lineEdit.setObjectName("path_lineEdit")
        self.gridLayout_2.addWidget(self.path_lineEdit, 3, 0, 1, 1)
        self.path_pushButton = QtWidgets.QPushButton(self.gameTools_groupBox)
        self.path_pushButton.setObjectName("path_pushButton")
        self.gridLayout_2.addWidget(self.path_pushButton, 3, 1, 1, 1)
        self.script_lineEdit = QtWidgets.QLineEdit(self.gameTools_groupBox)
        self.script_lineEdit.setObjectName("script_lineEdit")
        self.gridLayout_2.addWidget(self.script_lineEdit, 4, 0, 1, 1)
        self.script_pushButton = QtWidgets.QPushButton(self.gameTools_groupBox)
        self.script_pushButton.setObjectName("script_pushButton")
        self.gridLayout_2.addWidget(self.script_pushButton, 4, 1, 1, 1)
        self.disconnectExport_pushButton = QtWidgets.QPushButton(
            self.gameTools_groupBox)
        self.disconnectExport_pushButton.setObjectName(
            "disconnectExport_pushButton")
        self.gridLayout_2.addWidget(
            self.disconnectExport_pushButton, 5, 0, 1, 2)
        self.verticalLayout.addWidget(self.gameTools_groupBox)
        self.assembly_groupBox = QtWidgets.QGroupBox(gameTools)
        self.assembly_groupBox.setObjectName("assembly_groupBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.assembly_groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.importConnect_pushButton = QtWidgets.QPushButton(
            self.assembly_groupBox)
        self.importConnect_pushButton.setObjectName("importConnect_pushButton")
        self.gridLayout_3.addWidget(self.importConnect_pushButton, 0, 0, 1, 1)
        self.referenceConnect_pushButton = QtWidgets.QPushButton(
            self.assembly_groupBox)
        self.referenceConnect_pushButton.setObjectName(
            "referenceConnect_pushButton")
        self.gridLayout_3.addWidget(
            self.referenceConnect_pushButton, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.assembly_groupBox)
        self.gridLayout_4.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(gameTools)
        QtCore.QMetaObject.connectSlotsByName(gameTools)

    def retranslateUi(self, gameTools):
        gameTools.setWindowTitle(QtWidgets.QApplication.translate(
            "gameTools", "SHIFTER 游戏工具", None, -1))
        self.gameTools_groupBox.setTitle(
            QtWidgets.QApplication.translate("gameTools", "导出", None, -1))
        self.assetName_label.setText(QtWidgets.QApplication.translate(
            "gameTools", "资产名称", None, -1))
        self.rigNode_pushButton.setText(QtWidgets.QApplication.translate(
            "gameTools", "<<< 绑定顶层节点", None, -1))
        self.meshNode_pushButton.setText(QtWidgets.QApplication.translate(
            "gameTools", "<<< 网格顶层节点", None, -1))
        self.path_pushButton.setText(QtWidgets.QApplication.translate(
            "gameTools", "设置输出文件夹", None, -1))
        self.script_pushButton.setText(QtWidgets.QApplication.translate(
            "gameTools", "设置自定义脚本", None, -1))
        self.disconnectExport_pushButton.setText(
            QtWidgets.QApplication.translate(
                "gameTools", "断开连接并导出", None, -1))
        self.assembly_groupBox.setTitle(
            QtWidgets.QApplication.translate(
                "gameTools", "装配", None, -1))
        self.importConnect_pushButton.setText(
            QtWidgets.QApplication.translate(
                "gameTools", "导入并连接", None, -1))
        self.referenceConnect_pushButton.setText(
            QtWidgets.QApplication.translate(
                "gameTools", "引用并连接", None, -1))
