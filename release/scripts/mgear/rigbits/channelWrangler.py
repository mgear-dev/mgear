"""Channel wrangler tool, to manage user channel"""

import json

import mgear.pymaya as pm
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from mgear.vendor.Qt import QtWidgets, QtCore

import mgear.rigbits.channelWranglerUI as channelWranglerUI
from mgear.core import attribute, pyqt
string_types = str

######################################################################
# Functions
######################################################################


# apply the channel configuration from a dictionary
def _applyChannelConfig(configDic):
    tableMap = configDic["map"]
    movePolicy = configDic["movePolicy"]
    proxyPolicy = configDic["proxyPolicy"]
    for rule in tableMap:
        attr = rule[0]
        sourceNode = rule[1]
        targetNode = rule[2]
        option = rule[3]
        # proxy
        if option:
            node = pm.PyNode(sourceNode)
            sourceAttrs = node.attr(attr)
            target = pm.PyNode(targetNode)
            attribute.addProxyAttribute(sourceAttrs, target, proxyPolicy)
        # move
        else:
            attribute.moveChannel(attr, sourceNode, targetNode, movePolicy)

# apply the configuration stored in a  json file. This will be to use outside
# the interface


def applyChannelConfig(filePath):
    """Apply the configuration stored in a  json file.

    This will be to use outside the interface

    Args:
        filePath (str): Path to the  channel wrangler configuration file
    """
    configDict = json.load(open(filePath))
    _applyChannelConfig(configDict)


######################################################################
# Dialog
######################################################################

class cwUI(QtWidgets.QDialog, channelWranglerUI.Ui_Form):
    """Initialize the UI"""

    def __init__(self, parent=None):
        super(cwUI, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(cwUI, self).keyPressEvent(event)


class channelWrangler(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """Channel wrangler UI"""

    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        self.toolName = "ChannelWranglerWindow"

        super(self.__class__, self).__init__(parent=parent)
        self.cwUIInst = cwUI()
        self.table = self.cwUIInst.channelMapping_tableWidget
        self.headerTable = self.table.horizontalHeader()
        # we try setSectionResizeMode for Pyside2 if attributeError
        # setResizeMode for PySide
        for i in [1, 4]:
            try:
                self.headerTable.setSectionResizeMode(
                    i, QtWidgets.QHeaderView.Stretch)
                self.headerTable.setSectionResizeMode(
                    0, QtWidgets.QHeaderView.ResizeToContents)
            except AttributeError:
                self.headerTable.setResizeMode(
                    i, QtWidgets.QHeaderView.Stretch)
                self.headerTable.setResizeMode(
                    0, QtWidgets.QHeaderView.ResizeToContents)

        self.setup_channelWranglerWindow()
        self.create_layout()
        self.create_connections()

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installEventFilter(self)

    def keyPressEvent(self, event):
        if not event.key() == QtCore.Qt.Key_Escape:
            super(channelWrangler, self).keyPressEvent(event)

    def setup_channelWranglerWindow(self):
        self.mayaMainWindow = pyqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle("通道管理")
        self.resize(750, 525)

    def create_layout(self):

        self.cw_layout = QtWidgets.QVBoxLayout()
        self.cw_layout.addWidget(self.cwUIInst)

        self.setLayout(self.cw_layout)

    ###########################
    # create connections SIGNALS
    ###########################
    def create_connections(self):
        self.cwUIInst.channel_pushButton.clicked.connect(
            self.populateChannelLineEdit)
        self.cwUIInst.target_pushButton.clicked.connect(
            self.populateTargetLineEdit)
        self.cwUIInst.setRow_pushButton.clicked.connect(
            self.setRow)
        self.cwUIInst.setMultiChannel_pushButton.clicked.connect(
            self.setMultiChannel)
        self.cwUIInst.setMultiTarget_pushButton.clicked.connect(
            self.setMultiTarget)
        self.cwUIInst.clearAll_pushButton.clicked.connect(
            self.clearAllRows)
        self.cwUIInst.clearSelectedRows_pushButton.clicked.connect(
            self.clearSelectedRows)
        self.cwUIInst.setMoveOp_pushButton.clicked.connect(
            self.setMoveOperator)
        self.cwUIInst.setProxyOp_pushButton.clicked.connect(
            self.setProxyOperator)
        self.cwUIInst.export_pushButton.clicked.connect(
            self.exportConfig)
        self.cwUIInst.import_pushButton.clicked.connect(
            self.importConfig)
        self.cwUIInst.apply_pushButton.clicked.connect(
            self.applyChannelConfig)

    ##################
    # helper functions
    ##################

    def _setRowItem(self, rowPosition, itemIndex, itemContent):
        """Set the row item

        Args:
            rowPosition (Int): Row Index
            itemIndex (Int): Item Index
            itemContent (Str): Item content

        Returns:
            QTableWidgetItem: Item
        """
        item = QtWidgets.QTableWidgetItem(itemContent)
        self.table.setItem(rowPosition, itemIndex, item)
        return item

    def _setRowChannel(self, rowPosition, channel, source):
        """The source is set at the same time as the channel"""

        self._setRowItem(rowPosition, 0, str(rowPosition).zfill(3))
        self._setRowItem(rowPosition, 1, channel)
        self._setRowItem(rowPosition, 2, source)
        return

    def _setRowTarget(self, rowPosition, target):
        """Set the row target item

        Args:
            rowPosition (int): The row position index
            target (int): the target item index
        """
        self._setRowItem(rowPosition, 3, target)

    def _addNewRow(self, channel=None, source=None, target=None):
        """Add new row to the table

        Args:
            channel (str, optional): The channel to add to the table.
            source (str, optional): The source node that has the channel
                to move.
            target (str, optional): The destionation node for the channel.

        Returns:
            int: The row position index
        """
        rowPosition = self.table.rowCount()
        self.table.insertRow(rowPosition)
        if channel and source:
            self._setRowChannel(rowPosition, channel, source)
        if target:
            self._setRowTarget(rowPosition, target)

        # adding the operation combo box
        operation_comboBox = QtWidgets.QComboBox()
        operation_comboBox.setObjectName("operation")
        operation_comboBox.addItem("Move Channel")
        operation_comboBox.addItem("Proxy Channel")
        operation_comboBox.SizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self.table.setCellWidget(rowPosition, 4, operation_comboBox)
        return rowPosition

    def _getSelectedRowsIndex(self):
        """Return a list with the selected rows index

        Returns:
            List: Selected rows index list
        """
        index_list = []
        for model_index in self.table.selectionModel().selectedRows():
            index = QtCore.QPersistentModelIndex(model_index)
            index_list.append(index)

        return index_list

    def _buildConfigDict(self):
        """build the config dictionary from the UI data

        Returns:
            dic: The channel wrangler map configuration dictionary
        """
        configDict = {}
        mapList = []

        # this list will contain only the 3 main items list to avoid
        # duplicated rules
        checkDuplicatedList = []

        for i in range(self.table.rowCount()):
            checkItems = [self.table.item(i, x + 1).text() for x in range(3)]
            if checkItems not in checkDuplicatedList:
                checkDuplicatedList.append(checkItems)
                rowItems = checkItems + [self.table.cellWidget(
                                         i, 4).currentIndex()]
                mapList.append(rowItems)

        configDict["map"] = mapList
        mpIndex = self.cwUIInst.movePolicy_comboBox.currentIndex()
        configDict["movePolicy"] = ["merge", "index", "fullName"][mpIndex]
        pxyIndex = self.cwUIInst.proxyPolicy_comboBox.currentIndex()
        configDict["proxyPolicy"] = ["index", "fullName"][pxyIndex]
        return configDict

    ###########################
    # SLOTS
    ###########################
    # buttons
    def populateChannelLineEdit(self):
        oSel = pm.selected()
        if oSel:
            chan = attribute.getSelectedChannels(True)[0]
            self.cwUIInst.channel_lineEdit.setText(
                "{}.{}".format(oSel[0].name(), chan))

    def populateTargetLineEdit(self):
        oSel = pm.selected()
        if oSel:
            self.cwUIInst.target_lineEdit.setText(oSel[0].name())

    def setRow(self):
        """Sets a new row

        Sets a new row with the information on the channel and target lineEdit
        """
        fullChanName = self.cwUIInst.channel_lineEdit.text()
        if fullChanName:
            sourceName, chanName = fullChanName.split(".")
        targetName = self.cwUIInst.target_lineEdit.text()
        if fullChanName and targetName:
            # TODO: checker for the new rule, be sure is not duplicated
            self._addNewRow(chanName, sourceName, targetName)
        else:
            pm.displayWarning("Channel and target are not set properly")

    def setMultiChannel(self):
        """sets new rows from the selectec channels. 1 channel for each row"""
        oSel = pm.selected()
        if oSel:
            channels = attribute.getSelectedChannels(True)
            if not channels:
                channels = attribute.getSelectedObjectChannels(
                    oSel[0], True, True)
            for ch in channels:
                self._addNewRow(ch, oSel[0].name(), oSel[0].name())
        else:
            pm.displayWarning("To set the source, you need to select at  "
                              "one source object")

    def setMultiTarget(self):
        """set the target colum for the selected rows

        If only one object is selected will populate all the rows with the
        same object
        If there is more that one object selected, will iterate the selection
        adding one object to each row
        """
        oSel = pm.selected()
        index_list = self._getSelectedRowsIndex()

        if len(oSel) > 1:
            if index_list:
                for index, obj in zip(index_list, oSel):
                    self._setRowTarget(index.row(), obj.name())
        elif len(oSel) == 1:
            if index_list:
                for index in index_list:
                    self._setRowTarget(index.row(), oSel[0].name())
            else:
                for i in reversed(range(self.table.rowCount())):
                    self._setRowTarget(i, oSel[0].name())
        else:
            pm.displayWarning("To set the target, you need to select at less"
                              " one target object")

    def clearSelectedRows(self):
        """Clear selected rows from the table"""

        index_list = self._getSelectedRowsIndex()
        for index in index_list:
            self.table.removeRow(index.row())

    def clearAllRows(self):
        """Clear all the rows"""

        self.table.clear()
        for i in reversed(range(self.table.rowCount())):
            self.table.removeRow(i)

    def exportConfig(self):
        """Export channelWrangler configuration"""
        configDict = self._buildConfigDict()
        data_string = json.dumps(configDict, indent=4, sort_keys=True)
        filePath = pm.fileDialog2(
            fileMode=0,
            fileFilter='Channel Wrangler Configuration .cwc (*%s)' % ".cwc")
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]
        f = open(filePath, 'w')
        f.write(data_string)
        f.close()

    def importConfig(self):
        """Import channel wrangler configuration"""

        # TODO: if import dict ask to add to the current
        # configuration or replace.
        filePath = pm.fileDialog2(
            fileMode=1,
            fileFilter='Channel Wrangler Configuration .cwc (*%s)' % ".cwc")
        if not filePath:
            return
        if not isinstance(filePath, string_types):
            filePath = filePath[0]
        configDict = json.load(open(filePath))
        # also ask for proxy and move policy if is not the same when we add to
        # the current list
        if self.table.rowCount():
            option = pm.confirmDialog(
                title='Channel Wrangler Configuration Import Style',
                message='Do you want to repace current configuration or'
                        ' add it?\n if add the move policy and proxy policy'
                        ' will not change',
                button=['Replace', '添加', '取消'],
                defaultButton='Reaplace',
                cancelButton='取消',
                dismissString='取消')
        else:
            option = "Replace"
        if option == "Replace":
            self.clearAllRows()
            # set move policy
            indexList = ["merge", "index", "fullName"]
            self.cwUIInst.movePolicy_comboBox.setCurrentIndex(
                indexList.index(configDict["movePolicy"]))

            # set proxy policy
            indexList = ["index", "fullName"]
            self.cwUIInst.proxyPolicy_comboBox.setCurrentIndex(
                indexList.index(configDict["proxyPolicy"]))

        for rule in configDict["map"]:
            row_pos = self._addNewRow(channel=rule[0],
                                      source=rule[1],
                                      target=rule[2])

            oCombo = self.table.cellWidget(row_pos, 4)
            oCombo.setCurrentIndex(rule[3])

    # apply the current configuration in the dialog
    def applyChannelConfig(self):
        with pm.UndoChunk():
            configDict = self._buildConfigDict()
            # TODO add checker to avoid error if the datas is not
            # found in the scene
            for rule in configDict["map"]:
                # proxy
                if rule[3]:
                    source = pm.PyNode("{}.{}".format(rule[1], rule[0]))
                    target = pm.PyNode(rule[2])
                    attribute.addProxyAttribute(source,
                                                target,
                                                configDict["proxyPolicy"])
                # move
                else:
                    source = pm.PyNode(rule[1])
                    target = pm.PyNode(rule[2])
                    attribute.moveChannel(rule[0],
                                          source,
                                          target,
                                          configDict["movePolicy"])

    def _setOperator(self, operator):
        """set the channel wrangle operator

        =====   ======================
        index   Operation
        =====   ======================
        0       Move the channel
        1       Create a proxy channel
        =====   ======================

        Args:
            operator (index): Operator to use
        """
        index_list = self._getSelectedRowsIndex()
        if index_list:
            for index in index_list:
                oCombo = self.table.cellWidget(index.row(), 4)
                oCombo.setCurrentIndex(operator)
        else:
            for i in reversed(range(self.table.rowCount())):
                oCombo = self.table.cellWidget(i, 4)
                oCombo.setCurrentIndex(operator)

    def setMoveOperator(self):
        """set the channel wrangler operator to Move
        """
        self._setOperator(0)

    def setProxyOperator(self):
        """set the channel wrangler operator to Proxy
        """
        self._setOperator(1)


def openChannelWrangler(*args):
    pyqt.showDialog(channelWrangler, dockable=True)

####################################


if __name__ == "__main__":
    pyqt.showDialog(channelWrangler)
