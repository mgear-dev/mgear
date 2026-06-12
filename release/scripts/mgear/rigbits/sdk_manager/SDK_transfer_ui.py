import os
from pprint import pprint

from mgear.vendor.Qt import QtCore
from mgear.vendor.Qt import QtWidgets
from mgear.vendor.Qt import QtGui

from mgear.vendor.Qt import QtCompat

from functools import partial

import mgear.pymaya as pm

from mgear.core import pyqt


import mgear.rigbits.sdk_manager.core as sdk_m

"""
TO DO:
    - Add source Driver Button
    - Update Driver Attr comboBox
    - Logic to Add drivers to tree widget
        - Get What Driver attrs to move. Default is all. [driver.attr]
    - Logic to Add all driven under them
    - Add Destination Driver
    - Add right click menu to remove Tree items
    - Source Children grey out when in move mode
    - Drag and Drop functionality from one tree to another
        - Posible button for this in case?


"""


class SDK_transfer(QtWidgets.QDialog):
    def __init__(self, ui_path=None, parent=pyqt.maya_main_window()):
        super(SDK_transfer, self).__init__(parent)
        self.setWindowTitle("SDK Transfer")
        bh_flag = QtCore.Qt.WindowContextHelpButtonHint
        self.setWindowFlags(self.windowFlags() ^ bh_flag)
        self.init_ui(ui_path)
        self.create_menu_bar_actions()
        self.create_layout()
        self.create_connections()

    # ============================================================== #
    # ========================= Q T _ U I ========================== #
    # ============================================================== #

    def init_ui(self, ui_path=None):
        if not ui_path:
            ui_path = "{0}/SDK_transfer.ui".format(os.path.dirname(__file__))

            self.ui = QtCompat.loadUi(uifile=ui_path)

    def create_menu_bar_actions(self):
        """
        Actions for the menu bar
        self.<>_action = QtWidgets.QAction("<>", self)
        """
        # File
        self.export_settings_action = QtWidgets.QAction(
            "Export settings", self
        )
        self.import_settings_action = QtWidgets.QAction(
            "Import settings", self
        )

    def create_menu_bar(self, parent_layout):
        """
        Creating the Main Menu bar for the tool

        Arguments:
                parent_layout (QT layout): parent to add the menu bar or
        Returns:
                None
        """
        self.menu_bar = QtWidgets.QMenuBar()
        # all menu bar tabs ===============
        # File -------------------
        file_menu = self.menu_bar.addMenu("File")
        file_menu.setTearOffEnabled(1)

        # Menu bar actions ===============
        # File
        file_menu.addAction(self.export_settings_action)
        file_menu.addAction(self.import_settings_action)

        # Adding to the Layout ===============
        parent_layout.setMenuBar(self.menu_bar)

    def create_layout(self):
        # Create a base layout and parent the .ui to it.
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.create_menu_bar(main_layout)
        main_layout.addWidget(self.ui)

    def create_connections(self):
        # Create connection hooks to the Ui.

        self.ui.addSourceDriver_pushButton.clicked.connect(
            partial(self.add_driver, self.ui.source_treeWidget, True)
        )
        self.ui.addDestinationDriver_pushButton.clicked.connect(
            partial(self.add_driver, self.ui.destination_treeWidget, False)
        )

        return

    def create_item(self, name):
        """ """
        item = QtWidgets.QTreeWidgetItem([name])
        return item

    def get_tree_item_names(self, targetTree):
        """
        Gets all the items from the tree

        Arguments:
                targetTree (QTreeWidget): Tree to Query

        Reutrns:
                list - [str]: list of item names
        """
        allTreeItems = []
        root = targetTree.invisibleRootItem()
        child_count = root.childCount()
        for i in range(child_count):
            item = root.child(i)
            itemText = item.text(0)
            allTreeItems.append(itemText)

        return allTreeItems

    # ============================================================== #
    # ==================== U I _ U P D A T E S ===================== #
    # ============================================================== #

    def add_children(self, item):
        """ """
        driverCtl = pm.PyNode(item.text(0))
        connectedSDK_ctls = sdk_m.getDrivenFromAttr(
            driverCtl.attr("translateY"), is_SDK=False
        )

        if connectedSDK_ctls:
            for SDK_ctl in connectedSDK_ctls:
                SDK_item = self.create_item(SDK_ctl)
                item.addChild(SDK_item)

        # children =

    def add_driver(self, treewidget, children=False):
        """ """
        userSel = pm.ls(sl=True)

        itemsToAdd = []
        for item in userSel:
            # filtering out SDK and tweak ctls.
            if pm.hasAttr(item, "is_SDK") == False:
                if pm.hasAttr(item, "is_tweak") == False:
                    if pm.nodeType(item) == "transform":
                        if item not in itemsToAdd:
                            itemsToAdd.append(item)

        AllTreeItems = self.get_tree_item_names(treewidget)

        if itemsToAdd:
            for item in itemsToAdd:
                if item.name() not in AllTreeItems:
                    treeItem = self.create_item(item.name())

                    # --------
                    brush = QtGui.QBrush(QtGui.QColor(60, 60, 60))
                    brush.setStyle(QtCore.Qt.SolidPattern)
                    treeItem.setBackground(0, brush)
                    treeItem.setSizeHint(0, QtCore.QSize(0, 30))

                    pprint(dir(treeItem))

                    treewidget.addTopLevelItem(treeItem)
                    if children:
                        self.add_children(treeItem)


if __name__ == "__main__":

    try:
        sdk_transfer_dialog.close()  # pylint: disable=E0601
        sdk_transfer_dialog.deleteLater()
    except:
        pass
    import mgear.rigbits.sdk_manager.SDK_manager_ui as sdkui

    path = os.path.sep.join(
        [os.path.dirname(sdkui.__file__), "SDK_transfer.ui"]
    )
    sdk_transfer_dialog = SDK_transfer(path)
    sdk_transfer_dialog.show()
