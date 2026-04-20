from . import spaceManagerUI as sui
from mgear.vendor.Qt import QtCore, QtWidgets, QtGui

from mgear.core import pyqt
from mgear.core import widgets as mwgt

from functools import partial
import maya.cmds as cmds
import string
import json as json


def import_data(path):
    with open(path, "r") as read_file:
        obj = json.load(read_file)
    return obj

def create_constraints(dataSet):
    for constDict in dataSet:
        driven = constDict["driven"]
        drivers = constDict["drivers"].replace(" ", "").split(",")
        # changing separator characters due to cmds behavior
        # making sure no illegal spaces slip in from user input
        driversString = constDict["drivers"].replace(" ", "").replace(",", ":")
        topMenuName = constDict["topMenuName"]
        menuNames = constDict["menuNames"]
        menuType = constDict["menuType"]
        constraintType = constDict["constraintType"]
        keepOffset = constDict["keepOffset"]
        uiHost = constDict["UIhost"]

        try:
            # pm.select(driven)
            cmds.select(driven)
        except:
            warning = "Driven object {0} was not defined or found in the scene".format(
                driven
            )
            cmds.confirmDialog(
                title="Creating Constraints Failed",
                message=warning,
                button=["OK"],
                defaultButton="OK",
                cancelButton="OK",
                dismissString="OK",
            )
            raise NameError(warning)

        try:
            for driver in drivers:
                cmds.select(driver)
        except:
            warning = "Driver object {0} was not defined or found in the scene".format(
                driver
            )
            cmds.confirmDialog(
                title="Creating Constraints Failed",
                message=warning,
                button=["OK"],
                defaultButton="OK",
                cancelButton="OK",
                dismissString="OK",
            )
            raise NameError(warning)

        keepOffsetBool = True
        if keepOffset == "False":
            keepOffsetBool = False

        # constraint has a special name to avoid merging with existing constraints
        constraintName = driven + "_spaceSwitch_" + constraintType
        constraint = ""
        if constraintType == "parentConstraint":
            constraint = cmds.parentConstraint(
                drivers,
                driven,
                name=constraintName,
                maintainOffset=keepOffsetBool,
            )
        elif constraintType == "pointConstraint":
            constraint = cmds.pointConstraint(
                drivers,
                driven,
                name=constraintName,
                maintainOffset=keepOffsetBool,
            )
        elif constraintType == "orientConstraint":
            constraint = cmds.orientConstraint(
                drivers,
                driven,
                name=constraintName,
                maintainOffset=keepOffsetBool,
            )
        elif constraintType == "scaleConstraint":
            constraint = cmds.scaleConstraint(
                drivers,
                driven,
                name=constraintName,
                maintainOffset=keepOffsetBool,
            )
        # getting rid of redundant list structure coming from cmds
        constraint = constraint[0]

        if uiHost == "default":
            uiHost = driven

        # checking default top menu name
        if topMenuName == "default":
            topMenuName = "{0}_{1}Space".format(driven, constraintType)

        if menuNames == "default":
            if menuType == "enum":
                menuNames = driversString
            else:
                menuNames = drivers
        # checking sub menu name
        elif not menuNames == "default":
            menuNames = menuNames.replace(",", ":")
            # if there are not enough menu names, fill the rest using driver names
            if not len(menuNames.split(":")) == len(drivers):
                # creating list of needed driver names to append the custom names with
                extensions = drivers[(len(menuNames.split(":")) - 1) : -1]
                # unicode extensions need to be added one by one to avoid ugly formatting
                for x in extensions:
                    menuNames = menuNames + ":" + x

        if menuType == "enum":
            cmds.addAttr(
                uiHost,
                longName=topMenuName,
                attributeType="enum",
                enumName=menuNames,
                keyable=True,
            )
            for index, driver in enumerate(drivers):
                # the cond node name is only a base name that may clash and get numbers
                condNodeName = str(driver) + "_spaceCondition"
                condNode = cmds.createNode("condition", name=condNodeName)
                cmds.setAttr(str(condNode) + ".colorIfFalseR", 0)
                cmds.setAttr(str(condNode) + ".colorIfTrueR", 1)
                cmds.setAttr(str(condNode) + ".secondTerm", index)

                sourceAttr = str(uiHost + "." + topMenuName)
                targetAttr = str(condNode) + ".firstTerm"
                cmds.connectAttr(sourceAttr, targetAttr)
                weightattr = constraint + "." + driver + "W" + str(index)
                cmds.connectAttr(
                    (str(condNode) + "." + "outColor.outColorR"), weightattr
                )

        if menuType == "float":
            for index, driver in enumerate(drivers):
                cmds.addAttr(
                    uiHost,
                    longName=menuNames[index],
                    attributeType="float",
                    keyable=True,
                    hasMaxValue=True,
                    hasMinValue=True,
                    maxValue=1.0,
                    minValue=0.0,
                )
                attribute = uiHost + "." + menuNames[index]
                weightattr = constraint + "." + driver + "W" + str(index)
                cmds.connectAttr(attribute, weightattr)


def create_spaces(path="无"):
    if not path == "无":
        dataSet = import_data(path)
        patched = patch_data(dataSet)
        create_constraints(patched)


def patch_data(data):
    # sanity check data for missing keys, if key is missing it gets patched with default value
    # compared keys are written as unicode to avoid clashing between two types
    supportedKeys = {
        "drivers": "",
        "driven": "",
        "topMenuName": "default",
        "menuNames": "default",
        "menuType": "enum",
        "constraintType": "parentConstraint",
        "keepOffset": "True",
        "UIhost": "default",
    }
    for dictionary in data:
        if not sorted(dictionary.keys()) == sorted(supportedKeys.keys()):
            for key in supportedKeys.keys():
                if key not in dictionary.keys():
                    print(
                        "{0} key was patched to imported smd data".format(key)
                    )
                    tempDict = {key: supportedKeys[key]}
                    dictionary.update(tempDict)
        return data


class SpaceManager(QtWidgets.QDialog):
    # class for handling interactivity of ui
    def __init__(self):
        self.setup_ui()
        self.set_ui_connections()
        self.altGrey = 52.5
        self.constraintTypes = [
            "parentConstraint",
            "pointConstraint",
            "orientConstraint",
            "scaleConstraint",
        ]
        self.menuTypes = ["enum", "float"]
        self.abcList = list(string.ascii_uppercase)

    def setup_ui(self):
        self.ui = pyqt.showDialog(sui.SpaceManagerDialog, dockable=True)

    def update_connections_table(self):
        self.dataset = []
        for i in range(self.ui.spaceTable.rowCount()):
            data = {}
            data["driven"] = []
            data["drivers"] = []
            data["constraintType"] = []
            data["keepOffset"] = []
            data["topMenuName"] = []
            data["menuNames"] = []
            data["menuType"] = []
            data["UIhost"] = []

            # driven
            if self.ui.spaceTable.item(i, 0):
                data["driven"] = self.ui.spaceTable.item(i, 0).text()
            # drivers
            if self.ui.spaceTable.item(i, 1):
                data["drivers"] = self.ui.spaceTable.item(i, 1).text()

            # connection type
            if self.ui.spaceTable.item(i, 2):
                conComboBox = self.ui.spaceTable.cellWidget(i, 2)
                index = conComboBox.currentIndex()
                data["constraintType"] = self.constraintTypes[index]
            # keep offset
            if self.ui.spaceTable.item(i, 3):
                keepOffset = "True"
                if (
                    self.ui.spaceTable.item(i, 3).checkState()
                    == QtCore.Qt.Unchecked
                ):
                    keepOffset = "False"
                data["keepOffset"] = keepOffset

            # top menu name
            if self.ui.spaceTable.item(i, 4):
                data["topMenuName"] = self.ui.spaceTable.item(i, 4).text()

            # menu names
            if self.ui.spaceTable.item(i, 5):
                data["menuNames"] = self.ui.spaceTable.item(i, 5).text()
            # menu type
            if self.ui.spaceTable.item(i, 6):
                typeComboBox = self.ui.spaceTable.cellWidget(i, 6)
                index = typeComboBox.currentIndex()
                data["menuType"] = self.menuTypes[index]

            # Ui host
            if self.ui.spaceTable.item(i, 7):
                data["UIhost"] = self.ui.spaceTable.item(i, 7).text()

            self.dataset.append(data)
        return self.dataset

    def type_changed(self):
        # we force the output of the data
        self.update_connections_table()

    def add_item_to_connections_table(
        self,
        drivers="",
        driven="",
        topMenuName="default",
        menuNames="default",
        menuType="enum",
        constraintType="parentConstraint",
        keepOffset="True",
        UIhost="default",
    ):
        # new row
        self.ui.spaceTable.insertRow(self.ui.spaceTable.rowCount())
        # driven
        item = QtWidgets.QTableWidgetItem()
        item.setText(driven)
        item.setBackground(
            QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
        )
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 0, item)
        # drivers
        item2 = QtWidgets.QTableWidgetItem()
        item2.setText(drivers)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 1, item2)

        # constraint type
        item3 = QtWidgets.QTableWidgetItem()
        conComboBox = QtWidgets.QComboBox()
        conComboBox.addItems(self.constraintTypes)
        conComboBox.setCurrentIndex(self.constraintTypes.index(constraintType))
        conComboBox.currentIndexChanged.connect(self.type_changed)
        self.ui.spaceTable.setCellWidget(
            self.ui.spaceTable.rowCount() - 1, 2, conComboBox
        )
        item3.setTextAlignment(QtCore.Qt.AlignCenter)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 2, item3)

        # keepOffset
        item4 = QtWidgets.QTableWidgetItem()
        item4.setTextAlignment(QtCore.Qt.AlignCenter)
        item4.setBackground(
            QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
        )
        item4.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        if keepOffset == "True":
            item4.setCheckState(QtCore.Qt.Checked)
        else:
            item4.setCheckState(QtCore.Qt.Unchecked)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 3, item4)

        # top menu name
        item5 = QtWidgets.QTableWidgetItem()
        item5.setText(topMenuName)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 4, item5)
        # drop down menu names
        item6 = QtWidgets.QTableWidgetItem()
        item6.setText(menuNames)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 5, item6)

        # menu type
        item7 = QtWidgets.QTableWidgetItem()
        typeComboBox = QtWidgets.QComboBox()
        typeComboBox.addItems(self.menuTypes)
        typeComboBox.setCurrentIndex(self.menuTypes.index(menuType))

        typeComboBox.currentIndexChanged.connect(self.type_changed)
        self.ui.spaceTable.setCellWidget(
            self.ui.spaceTable.rowCount() - 1, 6, typeComboBox
        )
        item7.setTextAlignment(QtCore.Qt.AlignCenter)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 6, item7)

        # custom ui host
        item8 = QtWidgets.QTableWidgetItem()
        item8.setText(UIhost)
        self.ui.spaceTable.setItem(self.ui.spaceTable.rowCount() - 1, 7, item8)

    def add_driven_click(self):
        selection = cmds.ls(sl=True)
        for eachItem in selection:
            # adds entry
            self.add_item_to_connections_table(
                drivers="",
                driven=eachItem,
                constraintType="parentConstraint",
                menuType="enum",
                keepOffset="True",
            )
            cmds.select(selection, r=True)

    def add_drivers_click(self):
        selection = cmds.ls(sl=True)
        self.add_item_to_connections_table(
            drivers=selection,
            driven="",
            constraintType="parentConstraint",
            menuType="enum",
            keepOffset="True",
        )
        cmds.select(selection, r=True)

    def add_driven_and_drivers_click(self):
        # first one selected is set to driven, rest will be considered as drivers
        selection = cmds.ls(sl=True)
        if len(selection) >= 2:
            driven = selection[0]
            drivers = ",".join(selection[1:])
            # checks that the driven item is not already set as driven
            for i in range(self.ui.spaceTable.rowCount()):
                if self.ui.spaceTable.item(i, 1).text() == driven:
                    cmds.warning(
                        "Item '{}' is already on the list as a 'driven' item.".format(
                            driven
                        )
                    )
                    return
            # if we didn't exit because the driven is already on the list then we add the entry
            self.add_item_to_connections_table(
                drivers=drivers,
                driven=driven,
                constraintType="parentConstraint",
                menuType="enum",
                keepOffset="True",
            )
        else:
            cmds.warning(
                "Need to select at least two items to add as 'drivers' and 'driven'."
            )
        cmds.select(selection, r=True)

    def add_ui_host_click(self):
        selection = cmds.ls(sl=True)
        HostItem = QtWidgets.QTableWidgetItem()
        HostItem.setText(str(selection[0]))
        selected_rows = self.ui.spaceTable.selectionModel().selectedRows()
        if selected_rows:
            for target in selected_rows:
                self.ui.spaceTable.setItem(target.row(), 7, HostItem)
        else:
            self.add_item_to_connections_table(
                drivers="",
                driven="",
                constraintType="parentConstraint",
                keepOffset="True",
                UIhost=selection[0],
            )
        cmds.select(selection, r=True)

    def clear_table(self, tablewidget):
        tablewidget.clearContents()
        tablewidget.setRowCount(0)

    def remove_row(self, widget):
        selected_rows = self.ui.spaceTable.selectionModel().selectedRows()
        if selected_rows:
            row_indices = []
            for index in selected_rows:
                row_indices.append(index.row())
            row_indices.sort(key=lambda x: -1 * x)
            for row in row_indices:  # sorted in descending order
                self.ui.spaceTable.removeRow(row)
        else:
            cmds.warning("No row selected from table.")

    def add_driven_to_row(self, widget):
        if widget.currentRow() >= 0:
            selection = cmds.ls(sl=True)
            if len(selection):
                driven = selection[0]

                # checks that the driven item is not already set as driven
                for i in range(self.ui.spaceTable.rowCount()):
                    if self.ui.spaceTable.item(i, 0).text() == driven:
                        cmds.warning(
                            "Item '{}' is already on the list as a 'driven' item.".format(
                                driven
                            )
                        )
                        return
                # if we didn't exit because the driven is already on the list then we add the driven to the entry
                dataItem = QtWidgets.QTableWidgetItem()
                dataItem.setText(driven)
                widget.setItem(widget.currentRow(), 1, dataItem)
            else:
                cmds.warning("Need to select an item to add as 'driven'.")
            cmds.select(selection, r=True)
        else:
            cmds.warning("No row selected from table.")

    def save_table_as_json(self):
        smdFilter = "Space Manager Dictionary (*.smd)"
        path = cmds.fileDialog2(
            caption="select folder",
            dialogStyle=1,
            fileMode=0,
            fileFilter=smdFilter,
            returnFilter=True,
        )
        fullpath = str(path[0])
        data = self.update_connections_table()
        with open(fullpath, "w") as write_file:
            json.dump(data, write_file, indent=4)

    def show_data_on_table(self, data):
        data = patch_data(data)
        for index, dictionary in enumerate(data):
            self.ui.spaceTable.insertRow(index)
            item = QtWidgets.QTableWidgetItem()
            item2 = QtWidgets.QTableWidgetItem()
            item3 = QtWidgets.QTableWidgetItem()
            item4 = QtWidgets.QTableWidgetItem()
            item5 = QtWidgets.QTableWidgetItem()
            item6 = QtWidgets.QTableWidgetItem()
            item7 = QtWidgets.QTableWidgetItem()
            item8 = QtWidgets.QTableWidgetItem()

            # driven
            item.setText(str(dictionary["driven"]))

            # drivers
            item2.setText(str(dictionary["drivers"]))
            item2.setBackground(
                QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
            )

            # connection types
            constraintType = str(dictionary["constraintType"])
            conComboBox = QtWidgets.QComboBox()
            conComboBox.addItems(self.constraintTypes)
            conComboBox.setCurrentIndex(
                self.constraintTypes.index(constraintType)
            )
            conComboBox.currentIndexChanged.connect(self.type_changed)
            self.ui.spaceTable.setCellWidget(index, 2, conComboBox)
            item3.setTextAlignment(QtCore.Qt.AlignCenter)

            # keepOffset
            keepOffset = str(dictionary["keepOffset"])
            item4.setBackground(
                QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
            )
            item4.setFlags(
                QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
            )
            if keepOffset == "True":
                item4.setCheckState(QtCore.Qt.Checked)
            else:
                item4.setCheckState(QtCore.Qt.Unchecked)

            # top menu name
            item5.setText(str(dictionary["topMenuName"]))
            item5.setBackground(
                QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
            )

            # menu names
            item6.setText(str(dictionary["menuNames"]))
            item6.setBackground(
                QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
            )

            # menu type
            menuType = str(dictionary["menuType"])
            typeComboBox = QtWidgets.QComboBox()
            typeComboBox.addItems(self.menuTypes)
            typeComboBox.setCurrentIndex(self.menuTypes.index(menuType))
            typeComboBox.currentIndexChanged.connect(self.type_changed)
            self.ui.spaceTable.setCellWidget(index, 6, typeComboBox)
            item7.setTextAlignment(QtCore.Qt.AlignCenter)

            # Ui host
            item8.setText(str(dictionary["UIhost"]))
            item8.setBackground(
                QtGui.QColor(self.altGrey, self.altGrey, self.altGrey)
            )

            # setting items to correct table cells
            self.ui.spaceTable.setItem(index, 0, item)
            self.ui.spaceTable.setItem(index, 1, item2)
            self.ui.spaceTable.setItem(index, 2, item3)
            self.ui.spaceTable.setItem(index, 3, item4)
            self.ui.spaceTable.setItem(index, 4, item5)
            self.ui.spaceTable.setItem(index, 5, item6)
            self.ui.spaceTable.setItem(index, 6, item7)
            self.ui.spaceTable.setItem(index, 7, item8)

    def import_data_dialog(self, debug="True"):
        # creates a prompt and shows the data in ui
        smdFilter = "Space Manager Dictionary (*.smd)"
        path = cmds.fileDialog2(
            caption="select file",
            dialogStyle=1,
            fileMode=1,
            fileFilter=smdFilter,
            returnFilter=True,
        )
        path = path[0]
        with open(path, "r") as read_file:
            # Convert JSON file to Python Types
            obj = json.load(read_file)
        data = json.dumps(obj, indent=4)
        # printing imported data for user to see
        if debug:
            print(data)
        self.show_data_on_table(obj)

    def set_ui_connections(self):
        # connecting buttons to functions
        self.ui.addDrivenBtn.clicked.connect(self.add_driven_click)
        self.ui.addBothBtn.clicked.connect(self.add_driven_and_drivers_click)
        self.ui.addUIhostBtn.clicked.connect(self.add_ui_host_click)
        self.ui.clearBtn.clicked.connect(
            partial(self.clear_table, self.ui.spaceTable)
        )
        self.ui.removeRowBtn.clicked.connect(
            partial(self.remove_row, self.ui.spaceTable)
        )
        self.ui.exportBtn.clicked.connect(self.save_table_as_json)
        self.ui.importBtn.clicked.connect(self.import_data_dialog)
        self.ui.runBtn.clicked.connect(self.run_from_ui)

    def run_from_ui(self):
        # dataset returned from function is used to generate connections
        dataset = self.update_connections_table()
        create_constraints(dataset)


def openSpaceManager(*args):
    return pyqt.showDialog(SpaceManager, dockable=True)
