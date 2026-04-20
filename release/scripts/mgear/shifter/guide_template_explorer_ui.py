import mgear.core.pyqt as gqt
from mgear.vendor.Qt import QtCore, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(412, 394)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.explorer_treeView = QtWidgets.QTreeView(self.centralwidget)
        self.explorer_treeView.setObjectName("explorer_treeView")
        self.gridLayout.addWidget(self.explorer_treeView, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 412, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuGuide = QtWidgets.QMenu(self.menubar)
        self.menuGuide.setObjectName("menuGuide")
        MainWindow.setMenuBar(self.menubar)
        self.actionBuild = QtWidgets.QAction(MainWindow)
        self.actionBuild.setObjectName("actionBuild")
        self.actionImport = QtWidgets.QAction(MainWindow)
        self.actionImport.setObjectName("actionImport")
        self.actionImport_Partial = QtWidgets.QAction(MainWindow)
        self.actionImport_Partial.setObjectName("actionImport_Partial")
        self.actionOpen = QtWidgets.QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionLoad_Selected_Guide = QtWidgets.QAction(MainWindow)
        self.actionLoad_Selected_Guide.setObjectName(
            "actionLoad_Selected_Guide"
        )
        self.actionSave = QtWidgets.QAction(MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionSave_As = QtWidgets.QAction(MainWindow)
        self.actionSave_As.setObjectName("actionSave_As")
        self.actionClear = QtWidgets.QAction(MainWindow)
        self.actionClear.setObjectName("actionClear")
        self.actionDiff_Tool = QtWidgets.QAction(MainWindow)
        self.actionDiff_Tool.setObjectName("actionDiff_Tool")
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionLoad_Selected_Guide)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave_As)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionClear)
        self.menuGuide.addAction(self.actionBuild)
        self.menuGuide.addSeparator()
        self.menuGuide.addAction(self.actionImport)
        self.menuGuide.addAction(self.actionImport_Partial)
        self.menuGuide.addSeparator()
        self.menuGuide.addAction(self.actionDiff_Tool)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuGuide.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            gqt.fakeTranslate("MainWindow", "主窗口", None, -1)
        )
        self.menuFile.setTitle(
            gqt.fakeTranslate("MainWindow", "文件", None, -1)
        )
        self.menuGuide.setTitle(
            gqt.fakeTranslate("MainWindow", "指南", None, -1)
        )
        self.actionBuild.setText(
            gqt.fakeTranslate("MainWindow", "构建", None, -1)
        )
        self.actionImport.setText(
            gqt.fakeTranslate("MainWindow", "导入", None, -1)
        )
        self.actionImport_Partial.setText(
            gqt.fakeTranslate("MainWindow", "部分导入", None, -1)
        )
        self.actionOpen.setText(
            gqt.fakeTranslate("MainWindow", "打开", None, -1)
        )
        self.actionLoad_Selected_Guide.setText(
            gqt.fakeTranslate("MainWindow", "加载选定的指南", None, -1)
        )
        self.actionSave.setText(
            gqt.fakeTranslate("MainWindow", "保存", None, -1)
        )
        self.actionSave_As.setText(
            gqt.fakeTranslate("MainWindow", "另存为...", None, -1)
        )
        self.actionClear.setText(
            gqt.fakeTranslate("MainWindow", "清除", None, -1)
        )
        self.actionDiff_Tool.setText(
            gqt.fakeTranslate("MainWindow", "差异工具", None, -1)
        )
