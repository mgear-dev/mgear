from mgear.vendor.Qt import QtCore, QtWidgets, QtGui

import maya.cmds as cmds

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class SpaceManagerDialog(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SpaceManagerDialog, self).__init__(parent)

        self.setWindowTitle("空间管理器")
        self.setMinimumWidth(1000)
        self.setWindowFlags(
            self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint
        )
        self.create_widgets()
        self.create_layouts()

    def create_widgets(self):
        # creating widget contents
        self.addDrivenBtn = QtWidgets.QPushButton("Add driven")
        self.addBothBtn = QtWidgets.QPushButton("Add Driven and Drivers")
        self.addUIhostBtn = QtWidgets.QPushButton("Add UIhost")
        self.clearBtn = QtWidgets.QPushButton("清除")
        self.importBtn = QtWidgets.QPushButton("导入")
        self.exportBtn = QtWidgets.QPushButton("导出")
        self.runBtn = QtWidgets.QPushButton("Run")
        self.removeRowBtn = QtWidgets.QPushButton("Remove Row")
        self.spaceTable = QtWidgets.QTableWidget()
        self.spaceTable.setColumnCount(8)
        header_view = self.spaceTable.horizontalHeader()
        # setting header to stretch according to text and frame
        header_view.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header_view.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        header_view.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            4, QtWidgets.QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            5, QtWidgets.QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(6, QtWidgets.QHeaderView.Stretch)
        header_view.setSectionResizeMode(7, QtWidgets.QHeaderView.Stretch)
        # the default size only affects interactive views in this case
        header_view.setDefaultSectionSize(200)
        self.spaceTable.setHorizontalHeaderLabels(
            [
                "Driven",
                "Drivers",
                "Constraint Type",
                "Maintain Offset",
                "Top Menu Name",
                "Sub Menu Names",
                "Menu Type",
                "Custom UIhost",
            ]
        )

    def create_layouts(self):
        # creating layouts, adding content to layouts
        main_layout = QtWidgets.QVBoxLayout(self)
        editing_buttons_layout = QtWidgets.QHBoxLayout(self)
        editing_buttons_layout.addWidget(self.addDrivenBtn)
        editing_buttons_layout.addWidget(self.addBothBtn)
        editing_buttons_layout.addWidget(self.addUIhostBtn)
        editing_buttons_layout.addWidget(self.removeRowBtn)
        editing_buttons_layout.addWidget(self.clearBtn)
        file_management_layout = QtWidgets.QHBoxLayout(self)
        file_management_layout.addWidget(self.importBtn)
        file_management_layout.addWidget(self.exportBtn)
        file_management_layout.addWidget(self.runBtn)
        main_layout.addLayout(file_management_layout)
        main_layout.addWidget(self.spaceTable)
        main_layout.addLayout(editing_buttons_layout)

    def add_Row(self):
        rowPosition = self.spaceTable.rowCount()
        self.spaceTable.insertRow(rowPosition)

    def set_selections_as_item(self):
        item = self.spaceTable.currentItem()
        column = self.spaceTable.currentColumn()
        protected = [2, 3, 6]
        selected = []
        for target in cmds.ls(selection=True):
            selected.append(str(target))
        selected = ", ".join(selected)  # adds comma between each list item
        if column not in protected:
            item.setText(selected)
        else:
            print("Protected cells cannot be edited.")

    def reset_selected_item(self):
        item = self.spaceTable.currentItem()
        column = self.spaceTable.currentColumn()
        protected = [2, 3, 6]
        hasDefault = [4, 5, 7]
        isDropDown = [2, 6]
        if column not in protected:
            item.setText("")
        if column in hasDefault:
            item.setText("default")
        if column in isDropDown:
            item.setCurrentIndex(0)
        if column == 3:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            print("cell cannot be reset")

    def contextMenuEvent(self, pos):
        menu = QtWidgets.QMenu(title="add current selection")
        menu.addAction("Add Selected", self.set_selections_as_item)
        menu.addAction("Reset Selected", self.reset_selected_item)
        menu.exec_(QtGui.QCursor.pos())
